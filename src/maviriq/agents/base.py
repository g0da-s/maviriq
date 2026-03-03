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
                "\n\nLANGUAGE REQUIREMENT — STRICT:"
                "\nWrite ALL user-facing text in Lithuanian (lietuvių kalba)."
                f"\nThis applies to these fields: {fields}."
                "\n"
                "\nCRITICAL RULES:"
                "\n- Do NOT mix English words into Lithuanian sentences. Translate EVERYTHING."
                "\n- English jargon MUST be translated or replaced with a natural Lithuanian equivalent."
                "\n  BAD: 'Padaryk landing page su email signup'"
                "\n  GOOD: 'Sukurk pristatymo puslapį su el. pašto registracija'"
                "\n  BAD: 'Naudok content marketing strategiją'"
                "\n  GOOD: 'Naudok turinio rinkodaros strategiją'"
                "\n- Use correct Lithuanian grammar: proper noun cases (kilmininkas, galininkas, etc.),"
                "\n  adjective-noun agreement, and natural Lithuanian word order."
                "\n  Do NOT calque English sentence structure — write as a native Lithuanian speaker would."
                "\n  BAD: 'Tai yra didelis rinkos galimybė' (English word order calque)"
                "\n  GOOD: 'Tai didelė rinkos galimybė' (correct gender agreement + natural order)"
                "\n  BAD: 'reikalauja tobulos vykdymo' (wrong adjective ending — vykdymas is masculine)"
                "\n  GOOD: 'reikalauja tobulo vykdymo' (correct masculine genitive agreement)"
                "\n  BAD: 'aukštos kokybės produktas' when referring to masculine noun"
                "\n  GOOD: 'aukštos kokybės produktas' is correct (kokybė is feminine genitive)"
                "\n  Always match adjective endings to the gender AND case of the noun they modify."
                "\n- ACCUSATIVE CASE — common source of errors with feminine nouns:"
                "\n  Lithuanian adjectives MUST match the gender AND case of their noun."
                "\n  Common feminine nouns: rizika, galimybė, problema, rinka, strategija, platforma, grėsmė."
                "\n  Their accusative adjectives end in -ę (didelę, mažą, naują), NOT masculine -į."
                "\n  BAD: 'kelia didelį riziką' (masculine -į with feminine rizika)"
                "\n  GOOD: 'kelia didelę riziką' (correct feminine accusative)"
                "\n  BAD: 'turi didelį galimybę' (masculine ending)"
                "\n  GOOD: 'turi didelę galimybę' (correct feminine accusative)"
                "\n  BAD: 'sukuria naują problemą' — this IS correct (naują works for both genders in acc.)"
                "\n  BAD: 'mato didelį grėsmę' (masculine -į with feminine grėsmė)"
                "\n  GOOD: 'mato didelę grėsmę' (correct feminine accusative)"
                "\n- For well-known product/company names (Reddit, GitHub, Slack, etc.) keep the"
                "\n  name but translate everything around it into proper Lithuanian."
                "\n- For pricing fields: translate descriptive prices like 'Free' → 'Nemokama',"
                "\n  'Unknown' → 'Nežinoma', 'Contact sales' → 'Susisiekite su pardavimais'."
                "\n  Keep numeric prices as-is (e.g., '$19/mo' stays '$19/mėn.')."
                "\n- For funding signals and investor descriptions: translate ALL prose into Lithuanian."
                "\n  Do NOT copy-paste English descriptions from sources. Rewrite them in Lithuanian."
                "\n  BAD: 'Simb is a multi-banking app for families who want to get control over their finances'"
                "\n  GOOD: 'Simb yra daugiabankė programėlė šeimoms, norinčioms valdyti savo finansus'"
                "\n- Keep enum values (high/moderate/mild, direct/indirect/potential, "
                "positive/negative/neutral, strong/moderate/weak, low/medium/high, "
                "growing/stable/shrinking) in English — only these stay in English."
            )

            if "pain_points[].quote" in self.translatable_fields:
                system_prompt += (
                    "\n\nQUOTE TRANSLATION — ABSOLUTELY MANDATORY:"
                    "\nThe pain point quotes you find will be in English from Reddit, HN, etc."
                    "\nYou MUST translate EVERY quote into natural Lithuanian while preserving"
                    "\nthe original meaning, emotion, and tone. Do NOT leave ANY quote in English."
                    "\n"
                    "\nExample — BEFORE (English original from Reddit):"
                    '\n  "I\'ve been looking for a good parental control app but they all suck"'
                    "\nExample — AFTER (translated to Lithuanian):"
                    '\n  "Ieškojau geros tėvų kontrolės programėlės, bet visos yra prastos"'
                    "\n"
                    "\nExample — BEFORE:"
                    '\n  "The biggest problem is that no tool integrates with our existing workflow"'
                    "\nExample — AFTER:"
                    '\n  "Didžiausia problema ta, kad joks įrankis neintegruojasi su mūsų esamu darbo procesu"'
                    "\n"
                    "\nThe source and source_url fields stay in English (they are identifiers, not prose)."
                    "\nWARNING: If ANY quote in your output is still in English, your response will be REJECTED."
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
