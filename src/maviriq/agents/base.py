from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, ClassVar, Generic, TypeVar

from pydantic import BaseModel

from maviriq.config import settings
from maviriq.services.llm import LLMService
from maviriq.services.search import SerperService

TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound=BaseModel)


class BaseAgent(ABC, Generic[TInput, TOutput]):
    """Base class for agentic research agents.

    Subclasses define prompts, tools, and an output schema. The ``run``
    method drives an agentic tool-use loop via ``LLMService.run_tool_loop``.

    The synthesis agent overrides ``run`` directly since it doesn't use tools.
    """

    name: str
    description: str
    output_schema: ClassVar[type[BaseModel]]

    def __init__(self, llm: LLMService, search: SerperService) -> None:
        self.llm = llm
        self.search = search

    @abstractmethod
    def get_system_prompt(self, input_data: TInput) -> str: ...

    @abstractmethod
    def get_user_prompt(self, input_data: TInput) -> str: ...

    @abstractmethod
    def get_tools(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_tool_executors(self) -> dict[str, Callable[[str], Awaitable[str]]]: ...

    def post_process(self, input_data: TInput, result: TOutput) -> TOutput:
        """Optional fixups after the tool loop returns (e.g., setting result.idea)."""
        return result

    async def run(self, input_data: TInput) -> TOutput:
        result = await self.llm.run_tool_loop(
            system_prompt=self.get_system_prompt(input_data),
            user_prompt=self.get_user_prompt(input_data),
            tools=self.get_tools(),
            tool_executors=self.get_tool_executors(),
            output_schema=self.output_schema,
            max_iterations=settings.agent_max_iterations,
        )
        return self.post_process(input_data, result)
