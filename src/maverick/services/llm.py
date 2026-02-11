import logging
from typing import TypeVar

from anthropic import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from maverick.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_RETRY_POLICY = dict(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10),
    retry=retry_if_exception_type((APIConnectionError, APITimeoutError, InternalServerError, RateLimitError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)


class LLMService:
    def __init__(self) -> None:
        self.model = ChatAnthropic(
            model=settings.reasoning_model,
            max_tokens=4096,
        )
        self.cheap_model = ChatAnthropic(
            model=settings.cheap_model,
            max_tokens=4096,
        )

    def _get_model(self, use_cheap_model: bool = False) -> ChatAnthropic:
        return self.cheap_model if use_cheap_model else self.model

    @retry(**_RETRY_POLICY)
    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: type[T],
        use_cheap_model: bool = False,
    ) -> T:
        model = self._get_model(use_cheap_model)
        structured_model = model.with_structured_output(output_schema)

        result = await structured_model.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        return result

    @retry(**_RETRY_POLICY)
    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        use_cheap_model: bool = False,
    ) -> str:
        model = self._get_model(use_cheap_model)

        response = await model.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        return response.content

    @retry(**_RETRY_POLICY)
    async def generate_list(
        self,
        system_prompt: str,
        user_prompt: str,
        use_cheap_model: bool = True,
    ) -> list[str]:
        """Generate a list of strings (e.g., search queries). Uses cheap model by default."""

        class ListOutput(BaseModel):
            items: list[str]

        result = await self.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=ListOutput,
            use_cheap_model=use_cheap_model,
        )
        return result.items
