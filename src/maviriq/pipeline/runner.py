import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from maviriq.agents.competitor_research import CompetitorResearchAgent
from maviriq.agents.graveyard_research import GraveyardResearchAgent
from maviriq.agents.market_intelligence import MarketIntelligenceAgent
from maviriq.agents.pain_discovery import PainDiscoveryAgent
from maviriq.agents.synthesis import SynthesisAgent
from maviriq.config import settings
from maviriq.agents.base import BaseAgent
from maviriq.models.schemas import (
    CompetitorResearchInput,
    CompetitorResearchOutput,
    GraveyardResearchInput,
    GraveyardResearchOutput,
    MarketIntelligenceInput,
    MarketIntelligenceOutput,
    PainDiscoveryInput,
    PainDiscoveryOutput,
    SynthesisInput,
    ValidationRun,
    ValidationStatus,
)
from maviriq.pipeline.events import (
    AgentCompletedEvent,
    AgentStartedEvent,
    PipelineCompletedEvent,
    PipelineErrorEvent,
    SSEEvent,
)
from maviriq.pipeline import pubsub
from maviriq.services.llm import LLMService, SearchUnavailableError
from maviriq.services.search import SerperService
from maviriq.storage.repository import ValidationRepository

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# LangGraph State
# ──────────────────────────────────────────────


class PipelineState(TypedDict):
    idea: str
    user_id: str | None
    run_id: str
    language: str
    pain_discovery: PainDiscoveryOutput | None
    competitor_research: CompetitorResearchOutput | None
    market_intelligence: MarketIntelligenceOutput | None
    graveyard_research: GraveyardResearchOutput | None
    synthesis: None  # Always None in state; final result goes to run


# ──────────────────────────────────────────────
# Pipeline Graph
# ──────────────────────────────────────────────


class PipelineGraph:
    def __init__(self) -> None:
        self.llm = LLMService()
        self.search = SerperService()
        self.repository = ValidationRepository()

        # Initialize agents
        self.agent1 = PainDiscoveryAgent(self.llm, self.search)
        self.agent2 = CompetitorResearchAgent(self.llm, self.search)
        self.agent3 = MarketIntelligenceAgent(self.llm, self.search)
        self.agent4 = GraveyardResearchAgent(self.llm, self.search)
        self.agent5 = SynthesisAgent(self.llm, self.search)

        self.graph = self._build_graph()

    def _build_graph(self) -> CompiledStateGraph:
        builder = StateGraph(PipelineState)

        # Add nodes
        builder.add_node("pain_discovery", self._pain_discovery_node)
        builder.add_node("competitor_research", self._competitor_node)
        builder.add_node("market_intelligence", self._market_intelligence_node)
        builder.add_node("graveyard_research", self._graveyard_research_node)
        builder.add_node("synthesis", self._synthesis_node)

        # START → parallel fan-out to all 4 research agents
        builder.add_edge(START, "pain_discovery")
        builder.add_edge(START, "competitor_research")
        builder.add_edge(START, "market_intelligence")
        builder.add_edge(START, "graveyard_research")

        # All 4 research agents → synthesis (fan-in)
        builder.add_edge("pain_discovery", "synthesis")
        builder.add_edge("competitor_research", "synthesis")
        builder.add_edge("market_intelligence", "synthesis")
        builder.add_edge("graveyard_research", "synthesis")

        # synthesis → END
        builder.add_edge("synthesis", END)

        return builder.compile()

    # ──────────────────────────────────────────
    # Node functions
    # ──────────────────────────────────────────

    async def _run_research_node(
        self,
        state: PipelineState,
        agent_num: int,
        agent: BaseAgent,
        input_data: Any,
        state_key: str,
    ) -> dict:
        """Shared logic for all 4 research agent nodes."""
        writer = get_stream_writer()
        run_id = state["run_id"]

        run = await self.repository.get(run_id)
        run.current_agent = agent_num
        await self.repository.update(run)
        writer(AgentStartedEvent.create(agent_num).model_dump())

        result = await asyncio.wait_for(
            agent.run(input_data),
            timeout=settings.agent_timeout,
        )

        run = await self.repository.get(run_id)
        setattr(run, state_key, result)
        await self.repository.update(run)
        writer(AgentCompletedEvent.create(agent_num, result.model_dump()).model_dump())

        return {state_key: result}

    async def _pain_discovery_node(self, state: PipelineState) -> dict:
        return await self._run_research_node(
            state,
            1,
            self.agent1,
            PainDiscoveryInput(idea=state["idea"]),
            "pain_discovery",
        )

    async def _competitor_node(self, state: PipelineState) -> dict:
        return await self._run_research_node(
            state,
            2,
            self.agent2,
            CompetitorResearchInput(idea=state["idea"]),
            "competitor_research",
        )

    async def _market_intelligence_node(self, state: PipelineState) -> dict:
        return await self._run_research_node(
            state,
            3,
            self.agent3,
            MarketIntelligenceInput(idea=state["idea"]),
            "market_intelligence",
        )

    async def _graveyard_research_node(self, state: PipelineState) -> dict:
        return await self._run_research_node(
            state,
            4,
            self.agent4,
            GraveyardResearchInput(idea=state["idea"]),
            "graveyard_research",
        )

    async def _synthesis_node(self, state: PipelineState) -> dict:
        writer = get_stream_writer()
        run_id = state["run_id"]
        pain = state["pain_discovery"]
        competitor = state["competitor_research"]

        # Backfill target_user on competitor output if it was run without one
        if competitor and not competitor.target_user and pain:
            competitor.target_user = pain.primary_target_user

        # Emit agent_started
        run = await self.repository.get(run_id)
        run.current_agent = 5
        # Ensure all results are persisted
        run.pain_discovery = pain
        run.competitor_research = competitor
        run.market_intelligence = state["market_intelligence"]
        run.graveyard_research = state["graveyard_research"]
        await self.repository.update(run)
        writer(AgentStartedEvent.create(5).model_dump())

        # Run agent — pass language for localized output
        language = state.get("language", "en")
        result = await asyncio.wait_for(
            self.agent5.run(
                SynthesisInput(
                    idea=state["idea"],
                    pain_discovery=state["pain_discovery"],
                    competitor_research=state["competitor_research"],
                    market_intelligence=state["market_intelligence"],
                    graveyard_research=state["graveyard_research"],
                ),
                language=language,
            ),
            timeout=settings.agent_timeout,
        )

        # Persist
        run = await self.repository.get(run_id)
        run.synthesis = result
        await self.repository.update(run)
        writer(AgentCompletedEvent.create(5, result.model_dump()).model_dump())

        return {"competitor_research": competitor}

    # ──────────────────────────────────────────
    # Public interface
    # ──────────────────────────────────────────

    async def run(self, run_id: str, idea: str, user_id: str | None = None, language: str = "en") -> None:
        """Run the full pipeline, publishing SSE events to pubsub."""
        run = ValidationRun(
            id=run_id, idea=idea, status=ValidationStatus.RUNNING, user_id=user_id
        )
        run.started_at = datetime.now(timezone.utc)
        await self.repository.create(run)

        initial_state: PipelineState = {
            "idea": idea,
            "user_id": user_id,
            "run_id": run_id,
            "language": language,
            "pain_discovery": None,
            "competitor_research": None,
            "market_intelligence": None,
            "graveyard_research": None,
            "synthesis": None,
        }

        try:
            async for mode, chunk in self.graph.astream(
                initial_state,
                stream_mode=["custom", "updates"],
            ):
                if mode == "custom":
                    # chunk is a dict from SSEEvent.model_dump()
                    event = SSEEvent(**chunk)
                    pubsub.publish(run_id, event)

            # Pipeline completed — get final state from DB
            run_final = await self.repository.get(run_id)
            if run_final and run_final.synthesis:
                run_final.status = ValidationStatus.COMPLETED
                run_final.completed_at = datetime.now(timezone.utc)
                await self.repository.update(run_final)
                pubsub.publish(
                    run_id,
                    PipelineCompletedEvent.create(
                        run_id,
                        run_final.synthesis.verdict.value,
                        run_final.synthesis.confidence,
                    ),
                )

        except asyncio.TimeoutError:
            run = await self.repository.get(run_id)
            agent_num = run.current_agent if run else 0
            internal_msg = (
                f"Agent {agent_num} timed out after {settings.agent_timeout}s"
            )
            logger.error("Pipeline failed for run %s: %s", run_id, internal_msg)
            if run:
                run.status = ValidationStatus.FAILED
                run.error = internal_msg
                run.completed_at = datetime.now(timezone.utc)
                await self.repository.update(run)
            pubsub.publish(
                run_id,
                PipelineErrorEvent.create(
                    agent_num, "Processing timed out. Please try again."
                ),
            )

        except SearchUnavailableError as e:
            run = await self.repository.get(run_id)
            agent_num = run.current_agent if run else 0
            logger.error(
                "Search unavailable for run %s (agent %s): %s", run_id, agent_num, e
            )
            if run:
                run.status = ValidationStatus.FAILED
                run.error = str(e)
                run.completed_at = datetime.now(timezone.utc)
                await self.repository.update(run)
            pubsub.publish(
                run_id,
                PipelineErrorEvent.create(
                    agent_num,
                    "Our research tools are temporarily unavailable. Please try again in a few minutes.",
                ),
            )

        except Exception as e:
            run = await self.repository.get(run_id)
            agent_num = run.current_agent if run else 0
            logger.exception("Pipeline failed for run %s (agent %s)", run_id, agent_num)
            if run:
                run.status = ValidationStatus.FAILED
                run.error = str(e)
                run.completed_at = datetime.now(timezone.utc)
                await self.repository.update(run)
            pubsub.publish(
                run_id,
                PipelineErrorEvent.create(
                    agent_num, "Processing failed. Please try again."
                ),
            )

        finally:
            pubsub.publish(run_id, None)  # Signal stream end
