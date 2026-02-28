import asyncio
import logging
from typing import Any, Awaitable, Callable, TypeVar

from anthropic import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel, ValidationError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from maviriq.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class SearchUnavailableError(Exception):
    """Raised when all search tool calls failed (e.g. bad API key, service down)."""


_ANTHROPIC_RETRY_POLICY = dict(
    stop=stop_after_attempt(6),
    wait=wait_exponential(min=2, max=120),
    retry=retry_if_exception_type(
        (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError)
    ),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)

# Google errors are imported lazily to avoid hard failure if the package isn't installed
try:
    from google.api_core.exceptions import (
        ResourceExhausted,
        ServiceUnavailable,
        TooManyRequests,
    )

    _GOOGLE_RETRY_EXCEPTIONS: tuple = (
        ResourceExhausted,
        ServiceUnavailable,
        TooManyRequests,
        ConnectionError,
    )
except ImportError:
    _GOOGLE_RETRY_EXCEPTIONS = (ConnectionError,)

_GOOGLE_RETRY_POLICY = dict(
    stop=stop_after_attempt(6),
    wait=wait_exponential(min=2, max=120),
    retry=retry_if_exception_type(_GOOGLE_RETRY_EXCEPTIONS),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)

SUBMIT_TOOL_NAME = "submit_result"


def _build_submit_tool(output_schema: type[BaseModel]) -> dict[str, Any]:
    """Build a submit_result tool schema from a Pydantic model."""
    json_schema = output_schema.model_json_schema()
    # Move $defs to top level so the model can reference nested schemas
    defs = json_schema.pop("$defs", {})
    return {
        "name": SUBMIT_TOOL_NAME,
        "description": (
            "Submit your final structured research result. "
            "Call this tool ONCE when you have gathered enough data."
        ),
        "input_schema": {
            **json_schema,
            **({"$defs": defs} if defs else {}),
        },
    }


class LLMService:
    def __init__(self) -> None:
        # Anthropic models — used for synthesis + cheap tasks
        self.model = ChatAnthropic(
            model=settings.reasoning_model,
            max_tokens=4096,
        )
        self.cheap_model = ChatAnthropic(
            model=settings.cheap_model,
            max_tokens=4096,
        )
        # Deterministic model for viability scoring (Pass 1) — temperature=0
        # ensures categorical outputs (gap_size, reachability, etc.) are stable
        self.scoring_model = ChatAnthropic(
            model=settings.reasoning_model,
            max_tokens=4096,
            temperature=0,
        )
        # Low-temperature model for verdict prose (Pass 2) — 0.3 keeps
        # text natural while reducing verdict flip-flopping
        self.synthesis_model = ChatAnthropic(
            model=settings.reasoning_model,
            max_tokens=4096,
            temperature=0.3,
        )

        # Gemini model — used for research agent tool loops
        self.research_model = None
        if settings.google_api_key:
            from langchain_google_genai import ChatGoogleGenerativeAI

            self.research_model = ChatGoogleGenerativeAI(
                model=settings.research_model,
                google_api_key=settings.google_api_key,
                max_output_tokens=4096,
            )
            logger.info("Research agents will use Gemini (%s)", settings.research_model)
        else:
            logger.info(
                "No GOOGLE_API_KEY set — research agents will use Anthropic (%s)",
                settings.reasoning_model,
            )

    def _get_model(
        self,
        use_cheap_model: bool = False,
        use_synthesis_model: bool = False,
        use_scoring_model: bool = False,
    ) -> ChatAnthropic:
        if use_scoring_model:
            return self.scoring_model
        if use_synthesis_model:
            return self.synthesis_model
        return self.cheap_model if use_cheap_model else self.model

    @retry(**_ANTHROPIC_RETRY_POLICY)
    async def _generate_structured_anthropic(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: type[T],
        use_cheap_model: bool = False,
        use_synthesis_model: bool = False,
        use_scoring_model: bool = False,
    ) -> T:
        model = self._get_model(
            use_cheap_model,
            use_synthesis_model=use_synthesis_model,
            use_scoring_model=use_scoring_model,
        )
        structured_model = model.with_structured_output(output_schema)
        return await structured_model.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )

    @retry(**_GOOGLE_RETRY_POLICY)
    async def _generate_structured_google(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: type[T],
    ) -> T:
        structured_model = self.research_model.with_structured_output(output_schema)
        return await structured_model.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: type[T],
        use_cheap_model: bool = False,
        use_research_model: bool = False,
        use_synthesis_model: bool = False,
        use_scoring_model: bool = False,
    ) -> T:
        """Generate structured output.

        Uses Gemini when use_research_model=True and a Google API key is configured,
        otherwise falls back to Anthropic (Sonnet or Haiku).
        use_scoring_model=True uses temperature=0 for deterministic categorical outputs.
        use_synthesis_model=True uses temperature=0.3 for natural verdict prose.
        """
        if use_research_model and self.research_model is not None:
            return await self._generate_structured_google(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=output_schema,
            )
        return await self._generate_structured_anthropic(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_schema,
            use_cheap_model=use_cheap_model,
            use_synthesis_model=use_synthesis_model,
            use_scoring_model=use_scoring_model,
        )

    @retry(**_ANTHROPIC_RETRY_POLICY)
    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        use_cheap_model: bool = False,
    ) -> str:
        model = self._get_model(use_cheap_model)

        response = await model.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )

        return response.content

    @retry(**_GOOGLE_RETRY_POLICY)
    async def _invoke_research(self, model: Any, messages: list) -> AIMessage:
        """Invoke the Gemini research model with Google-specific retry logic."""
        return await model.ainvoke(messages)

    @retry(**_ANTHROPIC_RETRY_POLICY)
    async def _invoke_anthropic(self, model: Any, messages: list) -> AIMessage:
        """Invoke an Anthropic model with Anthropic-specific retry logic."""
        return await model.ainvoke(messages)

    async def run_tool_loop(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict[str, Any]],
        tool_executors: dict[str, Callable[[str], Awaitable[str]]],
        output_schema: type[T],
        max_iterations: int = 10,
        min_searches: int = 0,
        recommended_searches: int = 0,
    ) -> T:
        """Run an agentic tool-use loop.

        Uses Gemini Flash for research when available,
        falls back to Anthropic Sonnet if no Google API key is set.
        """
        submit_tool = _build_submit_tool(output_schema)
        all_tools = tools + [submit_tool]

        # Pick the model: Gemini for research, Anthropic as fallback
        if self.research_model is not None:
            base_model = self.research_model
            invoke_fn = self._invoke_research
        else:
            base_model = self.model
            invoke_fn = self._invoke_anthropic

        model_with_tools = base_model.bind_tools(all_tools)

        # Inject search budget context into the system prompt
        effective_prompt = system_prompt
        if min_searches > 0:
            effective_prompt += (
                f"\n\n## SEARCH BUDGET\n"
                f"- Minimum searches before you can submit: {min_searches}\n"
                f"- Recommended searches for thorough research: {recommended_searches}\n"
                f"- Strategy: first turns → WIDE net, diverse queries across different tools. "
                f"Later turns → drill deeper into promising leads.\n"
                f"- DO NOT submit until you have met the minimum. Aim for the recommended number."
            )

        messages: list = [
            SystemMessage(content=effective_prompt),
            HumanMessage(content=user_prompt),
        ]

        search_successes = 0
        search_failures = 0

        for iteration in range(max_iterations):
            logger.debug("Tool loop iteration %d/%d", iteration + 1, max_iterations)

            # On last iteration, force the model to call submit_result
            if iteration == max_iterations - 1:
                forced_model = base_model.bind_tools(
                    [submit_tool], tool_choice=SUBMIT_TOOL_NAME
                )
                response: AIMessage = await invoke_fn(forced_model, messages)
            else:
                response = await invoke_fn(model_with_tools, messages)

            messages.append(response)

            # No tool calls — force submit on next turn
            if not response.tool_calls:
                forced_model = base_model.bind_tools(
                    [submit_tool], tool_choice=SUBMIT_TOOL_NAME
                )
                forced_response: AIMessage = await invoke_fn(forced_model, messages)
                messages.append(forced_response)
                if forced_response.tool_calls:
                    response = forced_response
                else:
                    break

            # Separate search calls from submit calls
            search_calls = []
            submit_call = None
            for tc in response.tool_calls:
                if tc["name"] == SUBMIT_TOOL_NAME:
                    submit_call = tc
                else:
                    search_calls.append(tc)

            if search_calls:
                logger.info(
                    "Iteration %d: %d search calls [%s]",
                    iteration + 1,
                    len(search_calls),
                    ", ".join(
                        f"{tc['name']}({(tc['args'].get('query') or tc['args'].get('url', ''))[:50]})"
                        for tc in search_calls
                    ),
                )
            if submit_call is not None:
                logger.info("Iteration %d: submit_result called", iteration + 1)

            # Block early submission if minimum searches not met
            if (
                submit_call is not None
                and iteration < max_iterations - 1
                and search_successes < min_searches
            ):
                logger.info(
                    "Blocking early submit: %d/%d minimum searches completed",
                    search_successes,
                    min_searches,
                )
                messages.append(
                    ToolMessage(
                        content=(
                            f"Cannot submit yet. You have completed {search_successes}/{min_searches} "
                            f"minimum searches. Continue researching — try different query phrasings "
                            f"and tools you haven't used yet."
                        ),
                        tool_call_id=submit_call["id"],
                    )
                )
                submit_call = None

            # Execute all search calls in parallel
            if search_calls:

                async def _exec(tc: dict) -> ToolMessage:
                    nonlocal search_successes, search_failures
                    name = tc["name"]
                    # Most tools use "query", scrape_url uses "url"
                    arg = tc["args"].get("query") or tc["args"].get("url", "")
                    executor = tool_executors.get(name)
                    if executor is None:
                        search_failures += 1
                        content = f"Error: unknown tool '{name}'"
                    else:
                        try:
                            content = await executor(arg)
                            search_successes += 1
                        except Exception as e:
                            search_failures += 1
                            logger.warning("Tool %s failed: %s", name, e)
                            content = f"Search failed: {e}"
                    return ToolMessage(content=content, tool_call_id=tc["id"])

                tool_messages = await asyncio.gather(
                    *[_exec(tc) for tc in search_calls]
                )
                messages.extend(tool_messages)

            # Handle submit_result
            if submit_call is not None:
                try:
                    result = output_schema.model_validate(submit_call["args"])
                    if search_failures > 0 and search_successes == 0:
                        raise SearchUnavailableError(
                            f"All {search_failures} search calls failed. Results would be based on general knowledge, not real research."
                        )
                    return result
                except ValidationError as e:
                    error_msg = f"Validation error in submit_result: {e}"
                    logger.warning(error_msg)
                    messages.append(
                        ToolMessage(
                            content=error_msg,
                            tool_call_id=submit_call["id"],
                        )
                    )
                    # Continue loop so the model can fix and resubmit

        # Check if all searches failed before falling back
        if search_failures > 0 and search_successes == 0:
            raise SearchUnavailableError(
                f"All {search_failures} search calls failed. Results would be based on general knowledge, not real research."
            )

        # Absolute fallback: use structured output to force a result
        logger.warning(
            "Tool loop exhausted %d iterations, using structured output fallback",
            max_iterations,
        )
        structured_model = base_model.with_structured_output(output_schema)
        result = await invoke_fn(structured_model, messages)
        return result
