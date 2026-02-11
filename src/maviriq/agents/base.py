from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

from maviriq.services.llm import LLMService
from maviriq.services.search import SerperService

TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound=BaseModel)


class BaseAgent(ABC, Generic[TInput, TOutput]):
    name: str
    description: str

    def __init__(self, llm: LLMService, search: SerperService) -> None:
        self.llm = llm
        self.search = search

    @abstractmethod
    async def run(self, input_data: TInput) -> TOutput: ...
