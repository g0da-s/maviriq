import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

from maverick.agents.competitor_research import CompetitorResearchAgent
from maverick.agents.pain_discovery import PainDiscoveryAgent
from maverick.agents.synthesis import SynthesisAgent
from maverick.agents.viability_analysis import ViabilityAnalysisAgent
from maverick.models.schemas import (
    CompetitorResearchInput,
    PainDiscoveryInput,
    SynthesisInput,
    ValidationRun,
    ValidationStatus,
    ViabilityInput,
)
from maverick.pipeline.events import (
    AgentCompletedEvent,
    AgentStartedEvent,
    PipelineCompletedEvent,
    PipelineErrorEvent,
    SSEEvent,
)
from maverick.services.llm import LLMService
from maverick.services.search import SerperService
from maverick.storage.repository import ValidationRepository

logger = logging.getLogger(__name__)


class PipelineRunner:
    def __init__(self) -> None:
        self.llm = LLMService()
        self.search = SerperService()
        self.repository = ValidationRepository()

        # Initialize agents
        self.agent1 = PainDiscoveryAgent(self.llm, self.search)
        self.agent2 = CompetitorResearchAgent(self.llm, self.search)
        self.agent3 = ViabilityAnalysisAgent(self.llm, self.search)
        self.agent4 = SynthesisAgent(self.llm, self.search)

    async def run(self, run_id: str, idea: str) -> AsyncGenerator[SSEEvent, None]:
        """Run the full 4-agent pipeline, streaming progress via SSE."""
        run = ValidationRun(id=run_id, idea=idea, status=ValidationStatus.RUNNING)
        run.started_at = datetime.now(timezone.utc)
        await self.repository.create(run)

        try:
            # ═══ Agent 1: Pain & User Discovery ═══
            run.current_agent = 1
            await self.repository.update(run)
            yield AgentStartedEvent.create(1, self.agent1.name)

            run.pain_discovery = await self.agent1.run(PainDiscoveryInput(idea=idea))
            await self.repository.update(run)
            yield AgentCompletedEvent.create(
                1, self.agent1.name, run.pain_discovery.model_dump()
            )

            # ═══ Agent 2: Competitor Research ═══
            run.current_agent = 2
            await self.repository.update(run)
            yield AgentStartedEvent.create(2, self.agent2.name)

            run.competitor_research = await self.agent2.run(
                CompetitorResearchInput(
                    idea=idea, target_user=run.pain_discovery.primary_target_user
                )
            )
            await self.repository.update(run)
            yield AgentCompletedEvent.create(
                2, self.agent2.name, run.competitor_research.model_dump()
            )

            # ═══ Agent 3: Viability Analysis ═══
            run.current_agent = 3
            await self.repository.update(run)
            yield AgentStartedEvent.create(3, self.agent3.name)

            run.viability = await self.agent3.run(
                ViabilityInput(
                    idea=idea,
                    pain_discovery=run.pain_discovery,
                    competitor_research=run.competitor_research,
                )
            )
            await self.repository.update(run)
            yield AgentCompletedEvent.create(
                3, self.agent3.name, run.viability.model_dump()
            )

            # ═══ Agent 4: Synthesis & Verdict ═══
            run.current_agent = 4
            await self.repository.update(run)
            yield AgentStartedEvent.create(4, self.agent4.name)

            run.synthesis = await self.agent4.run(
                SynthesisInput(
                    idea=idea,
                    pain_discovery=run.pain_discovery,
                    competitor_research=run.competitor_research,
                    viability=run.viability,
                )
            )
            await self.repository.update(run)
            yield AgentCompletedEvent.create(
                4, self.agent4.name, run.synthesis.model_dump()
            )

            # ═══ Pipeline Complete ═══
            run.status = ValidationStatus.COMPLETED
            run.completed_at = datetime.now(timezone.utc)
            await self.repository.update(run)

            yield PipelineCompletedEvent.create(
                run.id, run.synthesis.verdict.value, run.synthesis.confidence
            )

        except Exception as e:
            logger.exception(f"Pipeline failed for run {run_id}")
            run.status = ValidationStatus.FAILED
            run.error = str(e)
            run.completed_at = datetime.now(timezone.utc)
            await self.repository.update(run)
            yield PipelineErrorEvent.create(run.current_agent, str(e))
