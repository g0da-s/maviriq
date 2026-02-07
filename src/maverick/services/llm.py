import json
import logging
from typing import TypeVar

import anthropic
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from maverick.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMService:
    def __init__(self) -> None:
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: type[T],
        use_cheap_model: bool = False,
    ) -> T:
        model = settings.cheap_model if use_cheap_model else settings.reasoning_model

        # Build JSON schema from Pydantic model for tool use
        schema = output_schema.model_json_schema()

        response = await self.client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[
                {
                    "name": "structured_output",
                    "description": f"Return the analysis as a {output_schema.__name__}",
                    "input_schema": schema,
                }
            ],
            tool_choice={"type": "tool", "name": "structured_output"},
        )

        # Extract the tool use block
        for block in response.content:
            if block.type == "tool_use":
                return output_schema.model_validate(block.input)

        raise ValueError("LLM did not return a tool_use block")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        use_cheap_model: bool = False,
    ) -> str:
        model = settings.cheap_model if use_cheap_model else settings.reasoning_model

        response = await self.client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        return response.content[0].text

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
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
