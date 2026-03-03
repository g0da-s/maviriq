import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from maviriq.agents.competitor_research import CompetitorResearchAgent
from maviriq.agents.context_research import ContextResearchAgent
from maviriq.agents.graveyard_research import GraveyardResearchAgent
from maviriq.agents.market_intelligence import MarketIntelligenceAgent
from maviriq.agents.pain_discovery import PainDiscoveryAgent
from maviriq.agents.synthesis import SynthesisAgent
from maviriq.config import settings
from maviriq.agents.base import BaseAgent
from maviriq.models.schemas import (
    CompetitorResearchInput,
    CompetitorResearchOutput,
    ContextResearchInput,
    ContextResearchOutput,
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
from difflib import SequenceMatcher
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


def _deduplicate_graveyard(
    competitors: CompetitorResearchOutput | None,
    graveyard: GraveyardResearchOutput | None,
) -> GraveyardResearchOutput | None:
    """Remove graveyard entries that fuzzy-match an active competitor name.

    Prevents the same company from appearing in both the competitor list
    and the failed startups list (e.g. a company still operating being
    wrongly listed as dead).
    """
    if not graveyard or not competitors or not competitors.competitors:
        return graveyard

    competitor_names = {c.name.strip().lower() for c in competitors.competitors}

    def _matches_competitor(attempt_name: str) -> bool:
        normalized = attempt_name.strip().lower()
        if normalized in competitor_names:
            return True
        for comp_name in competitor_names:
            if SequenceMatcher(None, normalized, comp_name).ratio() > 0.85:
                return True
        return False

    original_count = len(graveyard.previous_attempts)
    graveyard.previous_attempts = [
        a for a in graveyard.previous_attempts if not _matches_competitor(a.name)
    ]
    removed = original_count - len(graveyard.previous_attempts)
    if removed:
        logger.info(
            "Removed %d graveyard entries that matched active competitors", removed
        )

    return graveyard


# ──────────────────────────────────────────────
# LangGraph State
# ──────────────────────────────────────────────


class PipelineState(TypedDict):
    idea: str
    user_id: str | None
    run_id: str
    language: str
    target_market: str | None
    context_research: ContextResearchOutput | None
    context_briefing: str | None
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
        self.agent0 = ContextResearchAgent(self.llm, self.search)
        self.agent1 = PainDiscoveryAgent(self.llm, self.search)
        self.agent2 = CompetitorResearchAgent(self.llm, self.search)
        self.agent3 = MarketIntelligenceAgent(self.llm, self.search)
        self.agent4 = GraveyardResearchAgent(self.llm, self.search)
        self.agent5 = SynthesisAgent(self.llm, self.search)

        self.graph = self._build_graph()

    def _build_graph(self) -> CompiledStateGraph:
        builder = StateGraph(PipelineState)

        # Add nodes
        builder.add_node("context_research", self._context_research_node)
        builder.add_node("pain_discovery", self._pain_discovery_node)
        builder.add_node("competitor_research", self._competitor_node)
        builder.add_node("market_intelligence", self._market_intelligence_node)
        builder.add_node("graveyard_research", self._graveyard_research_node)
        builder.add_node("synthesis", self._synthesis_node)

        # START → context research (runs first)
        builder.add_edge(START, "context_research")

        # context research → parallel fan-out to all 4 research agents
        builder.add_edge("context_research", "pain_discovery")
        builder.add_edge("context_research", "competitor_research")
        builder.add_edge("context_research", "market_intelligence")
        builder.add_edge("context_research", "graveyard_research")

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

        language = state.get("language", "en")
        result = await asyncio.wait_for(
            agent.run(input_data, language=language),
            timeout=settings.agent_timeout,
        )

        run = await self.repository.get(run_id)
        setattr(run, state_key, result)
        await self.repository.update(run)
        writer(AgentCompletedEvent.create(agent_num, result.model_dump()).model_dump())

        return {state_key: result}

    async def _context_research_node(self, state: PipelineState) -> dict:
        """Run context research agent (agent 0) and format briefing."""
        writer = get_stream_writer()
        run_id = state["run_id"]

        run = await self.repository.get(run_id)
        run.current_agent = 0
        await self.repository.update(run)
        writer(AgentStartedEvent.create(0).model_dump())

        result = await asyncio.wait_for(
            self.agent0.run(
                ContextResearchInput(
                    idea=state["idea"],
                    target_market=state.get("target_market"),
                ),
                max_iterations=4,
            ),
            timeout=settings.agent_timeout,
        )

        run = await self.repository.get(run_id)
        run.context_research = result
        await self.repository.update(run)
        writer(AgentCompletedEvent.create(0, result.model_dump()).model_dump())

        briefing = (
            f"IDEA ANALYSIS:\n{result.idea_analysis}\n\n"
            f"CURRENT LANDSCAPE:\n{result.current_landscape}\n\n"
            f"KEY PLAYERS:\n{result.key_players}\n\n"
            f"RECENT DEVELOPMENTS:\n{result.recent_developments}"
        )

        return {"context_research": result, "context_briefing": briefing}

    async def _pain_discovery_node(self, state: PipelineState) -> dict:
        return await self._run_research_node(
            state,
            1,
            self.agent1,
            PainDiscoveryInput(
                idea=state["idea"],
                target_market=state.get("target_market"),
                context_briefing=state.get("context_briefing"),
            ),
            "pain_discovery",
        )

    async def _competitor_node(self, state: PipelineState) -> dict:
        return await self._run_research_node(
            state,
            2,
            self.agent2,
            CompetitorResearchInput(
                idea=state["idea"],
                target_market=state.get("target_market"),
                context_briefing=state.get("context_briefing"),
            ),
            "competitor_research",
        )

    async def _market_intelligence_node(self, state: PipelineState) -> dict:
        return await self._run_research_node(
            state,
            3,
            self.agent3,
            MarketIntelligenceInput(
                idea=state["idea"],
                target_market=state.get("target_market"),
                context_briefing=state.get("context_briefing"),
            ),
            "market_intelligence",
        )

    async def _graveyard_research_node(self, state: PipelineState) -> dict:
        return await self._run_research_node(
            state,
            4,
            self.agent4,
            GraveyardResearchInput(
                idea=state["idea"],
                target_market=state.get("target_market"),
                context_briefing=state.get("context_briefing"),
            ),
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

        # Cross-validate: remove graveyard entries that match active competitors
        graveyard = _deduplicate_graveyard(competitor, state["graveyard_research"])

        # Emit agent_started
        run = await self.repository.get(run_id)
        run.current_agent = 5
        # Ensure all results are persisted
        run.pain_discovery = pain
        run.competitor_research = competitor
        run.market_intelligence = state["market_intelligence"]
        run.graveyard_research = graveyard
        await self.repository.update(run)
        writer(AgentStartedEvent.create(5).model_dump())

        # Run agent — pass language for localized output
        language = state.get("language", "en")
        result = await asyncio.wait_for(
            self.agent5.run(
                SynthesisInput(
                    idea=state["idea"],
                    target_market=state.get("target_market"),
                    pain_discovery=state["pain_discovery"],
                    competitor_research=state["competitor_research"],
                    market_intelligence=state["market_intelligence"],
                    graveyard_research=graveyard,
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

    async def run(
        self,
        run_id: str,
        idea: str,
        user_id: str | None = None,
        language: str = "en",
        target_market: str | None = None,
    ) -> None:
        """Run the full pipeline, publishing SSE events to pubsub."""
        run = ValidationRun(
            id=run_id, idea=idea, status=ValidationStatus.RUNNING, user_id=user_id,
            language=language, target_market=target_market,
        )
        run.started_at = datetime.now(timezone.utc)
        await self.repository.create(run)

        initial_state: PipelineState = {
            "idea": idea,
            "user_id": user_id,
            "run_id": run_id,
            "language": language,
            "target_market": target_market,
            "context_research": None,
            "context_briefing": None,
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
