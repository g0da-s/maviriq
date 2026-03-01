from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, ClassVar, Generic, TypeVar

from pydantic import BaseModel

from maviriq.config import settings
from maviriq.services.llm import LLMService
from maviriq.services.search import SerperService

TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound=BaseModel)

ToolSchemas = list[dict[str, Any]]
ToolExecutors = dict[str, Callable[[str], Awaitable[str]]]


class BaseAgent(ABC, Generic[TInput, TOutput]):
    """Base class for agentic research agents.

    Subclasses define prompts, tools, and an output schema. The ``run``
    method drives an agentic tool-use loop via ``LLMService.run_tool_loop``.

    The synthesis agent overrides ``run`` directly since it doesn't use tools.
    """

    name: str
    description: str
    output_schema: ClassVar[type[BaseModel]]
    min_searches: int = 0
    recommended_searches: int = 0

    def __init__(self, llm: LLMService, search: SerperService) -> None:
        self.llm = llm
        self.search = search

    @abstractmethod
    def get_system_prompt(self, input_data: TInput) -> str: ...

    @abstractmethod
    def get_user_prompt(self, input_data: TInput) -> str: ...

    @abstractmethod
    def get_tools_and_executors(self) -> tuple[ToolSchemas, ToolExecutors]: ...

    def post_process(self, input_data: TInput, result: TOutput) -> TOutput:
        """Optional fixups after the tool loop returns (e.g., setting result.idea)."""
        return result

    # Free-text fields per agent that should be translated.
    # Subclasses can override this to list the JSON field names that contain
    # user-facing prose (not enum values or URLs).
    translatable_fields: ClassVar[list[str]] = []

    async def run(
        self,
        input_data: TInput,
        max_iterations: int | None = None,
        language: str = "en",
    ) -> TOutput:
        system_prompt = self.get_system_prompt(input_data)

        if language == "lt" and self.translatable_fields:
            fields = ", ".join(self.translatable_fields)
            system_prompt += (
                "\n\nLANGUAGE REQUIREMENT: Write ALL user-facing text in Lithuanian "
                "(lietuvių kalba). This includes these fields: "
                f"{fields}. "
                "Keep enum values (high/moderate/mild, direct/indirect/potential, "
                "positive/negative/neutral, strong/moderate/weak, low/medium/high, "
                "growing/stable/shrinking) in English — only translate the free-text prose."
            )

        tools, executors = self.get_tools_and_executors()
        result = await self.llm.run_tool_loop(
            system_prompt=system_prompt,
            user_prompt=self.get_user_prompt(input_data),
            tools=tools,
            tool_executors=executors,
            output_schema=self.output_schema,
            max_iterations=max_iterations or settings.agent_max_iterations,
            min_searches=self.min_searches,
            recommended_searches=self.recommended_searches,
        )
        return self.post_process(input_data, result)
