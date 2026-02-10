import asyncio
import logging
from datetime import datetime, timezone
from typing import TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from maverick.agents.competitor_research import (
    RETRY_COMPETITOR_QUERIES_PROMPT,
    CompetitorResearchAgent,
)
from maverick.agents.pain_discovery import (
    RETRY_QUERY_GENERATION_PROMPT,
    PainDiscoveryAgent,
)
from maverick.agents.synthesis import SynthesisAgent
from maverick.agents.viability_analysis import ViabilityAnalysisAgent
from maverick.config import settings
from maverick.models.schemas import (
    CompetitorResearchInput,
    CompetitorResearchOutput,
    PainDiscoveryInput,
    PainDiscoveryOutput,
    SynthesisInput,
    ValidationRun,
    ValidationStatus,
    ViabilityInput,
    ViabilityOutput,
)
from maverick.pipeline.events import (
    AgentCompletedEvent,
    AgentStartedEvent,
    PipelineCompletedEvent,
    PipelineErrorEvent,
    SSEEvent,
)
from maverick.pipeline import pubsub
from maverick.services.llm import LLMService
from maverick.services.search import SerperService
from maverick.storage.repository import ValidationRepository

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# LangGraph State
# ──────────────────────────────────────────────

class PipelineState(TypedDict):
    idea: str
    user_id: str | None
    run_id: str
    pain_discovery: PainDiscoveryOutput | None
    competitor_research: CompetitorResearchOutput | None
    viability: ViabilityOutput | None
    synthesis: None  # Always None in state; final result goes to run
    agent1_attempts: int
    agent2_attempts: int


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
        self.agent3 = ViabilityAnalysisAgent(self.llm, self.search)
        self.agent4 = SynthesisAgent(self.llm, self.search)

        self.graph = self._build_graph()

    def _build_graph(self) -> CompiledStateGraph:
        builder = StateGraph(PipelineState)

        # Add nodes
        builder.add_node("pain_discovery", self._pain_discovery_node)
        builder.add_node("pain_discovery_retry", self._pain_retry_node)
        builder.add_node("competitor_research", self._competitor_node)
        builder.add_node("competitor_research_retry", self._competitor_retry_node)
        builder.add_node("viability", self._viability_node)
        builder.add_node("synthesis", self._synthesis_node)

        # START → parallel fan-out to both agents
        builder.add_edge(START, "pain_discovery")
        builder.add_edge(START, "competitor_research")

        # pain_discovery → retry or viability
        builder.add_conditional_edges(
            "pain_discovery",
            self._should_retry_pain,
            {"retry": "pain_discovery_retry", "continue": "viability"},
        )
        builder.add_edge("pain_discovery_retry", "viability")

        # competitor_research → retry or viability
        builder.add_conditional_edges(
            "competitor_research",
            self._should_retry_competitor,
            {"retry": "competitor_research_retry", "continue": "viability"},
        )
        builder.add_edge("competitor_research_retry", "viability")

        # viability → synthesis → END
        builder.add_edge("viability", "synthesis")
        builder.add_edge("synthesis", END)

        return builder.compile()

    # ──────────────────────────────────────────
    # Routing functions
    # ──────────────────────────────────────────

    def _should_retry_pain(self, state: PipelineState) -> str:
        pain = state["pain_discovery"]
        if (
            pain is not None
            and pain.data_quality == "partial"
            and state["agent1_attempts"] < 2
        ):
            logger.info("Pain discovery returned partial data — retrying with broader queries")
            return "retry"
        return "continue"

    def _should_retry_competitor(self, state: PipelineState) -> str:
        comp = state["competitor_research"]
        if (
            comp is not None
            and comp.data_quality == "partial"
            and state["agent2_attempts"] < 2
        ):
            logger.info("Competitor research returned partial data — retrying with broader queries")
            return "retry"
        return "continue"

    # ──────────────────────────────────────────
    # Node functions
    # ──────────────────────────────────────────

    async def _pain_discovery_node(self, state: PipelineState) -> dict:
        writer = get_stream_writer()
        run_id = state["run_id"]

        # Emit agent_started
        run = await self.repository.get(run_id)
        run.current_agent = 1
        await self.repository.update(run)
        writer(AgentStartedEvent.create(1, self.agent1.name).model_dump())

        # Run agent
        result = await asyncio.wait_for(
            self.agent1.run(PainDiscoveryInput(idea=state["idea"])),
            timeout=settings.agent_timeout,
        )

        # Persist result to DB
        run = await self.repository.get(run_id)
        run.pain_discovery = result
        await self.repository.update(run)
        writer(AgentCompletedEvent.create(1, self.agent1.name, result.model_dump()).model_dump())

        return {
            "pain_discovery": result,
            "agent1_attempts": state["agent1_attempts"] + 1,
        }

    async def _pain_retry_node(self, state: PipelineState) -> dict:
        writer = get_stream_writer()
        run_id = state["run_id"]
        previous = state["pain_discovery"]

        # Emit agent_started for retry
        run = await self.repository.get(run_id)
        run.current_agent = 1
        await self.repository.update(run)
        writer(AgentStartedEvent.create(1, f"{self.agent1.name} (retry)").model_dump())

        # Generate broader retry queries
        retry_queries = await self.llm.generate_list(
            system_prompt=RETRY_QUERY_GENERATION_PROMPT,
            user_prompt=(
                f"Idea: {state['idea']}\n"
                f"Previous queries (do NOT repeat): {previous.search_queries_used}\n"
                f"Pain summary so far: {previous.pain_summary}"
            ),
            use_cheap_model=True,
        )

        # Run agent with retry inputs
        result = await asyncio.wait_for(
            self.agent1.run(PainDiscoveryInput(
                idea=state["idea"],
                retry_queries=retry_queries,
                previous_result=previous,
            )),
            timeout=settings.agent_timeout,
        )

        # Persist
        run = await self.repository.get(run_id)
        run.pain_discovery = result
        await self.repository.update(run)
        writer(AgentCompletedEvent.create(1, self.agent1.name, result.model_dump()).model_dump())

        return {
            "pain_discovery": result,
            "agent1_attempts": state["agent1_attempts"] + 1,
        }

    async def _competitor_node(self, state: PipelineState) -> dict:
        writer = get_stream_writer()
        run_id = state["run_id"]

        # Emit agent_started
        run = await self.repository.get(run_id)
        run.current_agent = 2
        await self.repository.update(run)
        writer(AgentStartedEvent.create(2, self.agent2.name).model_dump())

        # First attempt runs without target_user (parallel with pain discovery)
        result = await asyncio.wait_for(
            self.agent2.run(CompetitorResearchInput(idea=state["idea"])),
            timeout=settings.agent_timeout,
        )

        # Persist result to DB
        run = await self.repository.get(run_id)
        run.competitor_research = result
        await self.repository.update(run)
        writer(AgentCompletedEvent.create(2, self.agent2.name, result.model_dump()).model_dump())

        return {
            "competitor_research": result,
            "agent2_attempts": state["agent2_attempts"] + 1,
        }

    async def _competitor_retry_node(self, state: PipelineState) -> dict:
        writer = get_stream_writer()
        run_id = state["run_id"]
        pain = state["pain_discovery"]
        previous = state["competitor_research"]

        # Retry has access to pain discovery results (parallel phase is done)
        target_user = pain.primary_target_user if pain else None

        # Emit agent_started for retry
        run = await self.repository.get(run_id)
        run.current_agent = 2
        await self.repository.update(run)
        writer(AgentStartedEvent.create(2, f"{self.agent2.name} (retry)").model_dump())

        # Generate broader retry queries
        target_label = target_user.label if target_user else "general users"
        retry_queries = await self.llm.generate_list(
            system_prompt=RETRY_COMPETITOR_QUERIES_PROMPT,
            user_prompt=(
                f"Idea: {state['idea']}\n"
                f"Target user: {target_label}\n"
                f"Previously found {len(previous.competitors)} competitors. Need more."
            ),
            use_cheap_model=True,
        )

        # Run agent with retry inputs (now with target_user from pain discovery)
        result = await asyncio.wait_for(
            self.agent2.run(CompetitorResearchInput(
                idea=state["idea"],
                target_user=target_user,
                retry_queries=retry_queries,
                previous_result=previous,
            )),
            timeout=settings.agent_timeout,
        )

        # Persist
        run = await self.repository.get(run_id)
        run.competitor_research = result
        await self.repository.update(run)
        writer(AgentCompletedEvent.create(2, self.agent2.name, result.model_dump()).model_dump())

        return {
            "competitor_research": result,
            "agent2_attempts": state["agent2_attempts"] + 1,
        }

    async def _viability_node(self, state: PipelineState) -> dict:
        writer = get_stream_writer()
        run_id = state["run_id"]
        pain = state["pain_discovery"]
        competitor = state["competitor_research"]

        # Backfill target_user on competitor output if it was run without one
        if competitor and not competitor.target_user and pain:
            competitor.target_user = pain.primary_target_user

        # Emit agent_started
        run = await self.repository.get(run_id)
        run.current_agent = 3
        # Ensure both results are persisted (in case of parallel write timing)
        run.pain_discovery = pain
        run.competitor_research = competitor
        await self.repository.update(run)
        writer(AgentStartedEvent.create(3, self.agent3.name).model_dump())

        # Run agent
        result = await asyncio.wait_for(
            self.agent3.run(ViabilityInput(
                idea=state["idea"],
                pain_discovery=pain,
                competitor_research=competitor,
            )),
            timeout=settings.agent_timeout,
        )

        # Persist
        run = await self.repository.get(run_id)
        run.viability = result
        await self.repository.update(run)
        writer(AgentCompletedEvent.create(3, self.agent3.name, result.model_dump()).model_dump())

        return {
            "viability": result,
            "competitor_research": competitor,  # persist backfilled target_user
        }

    async def _synthesis_node(self, state: PipelineState) -> dict:
        writer = get_stream_writer()
        run_id = state["run_id"]

        # Emit agent_started
        run = await self.repository.get(run_id)
        run.current_agent = 4
        await self.repository.update(run)
        writer(AgentStartedEvent.create(4, self.agent4.name).model_dump())

        # Run agent
        result = await asyncio.wait_for(
            self.agent4.run(SynthesisInput(
                idea=state["idea"],
                pain_discovery=state["pain_discovery"],
                competitor_research=state["competitor_research"],
                viability=state["viability"],
            )),
            timeout=settings.agent_timeout,
        )

        # Persist
        run = await self.repository.get(run_id)
        run.synthesis = result
        await self.repository.update(run)
        writer(AgentCompletedEvent.create(4, self.agent4.name, result.model_dump()).model_dump())

        return {}

    # ──────────────────────────────────────────
    # Public interface
    # ──────────────────────────────────────────

    async def run(self, run_id: str, idea: str, user_id: str | None = None) -> None:
        """Run the full pipeline, publishing SSE events to pubsub."""
        run = ValidationRun(id=run_id, idea=idea, status=ValidationStatus.RUNNING, user_id=user_id)
        run.started_at = datetime.now(timezone.utc)
        await self.repository.create(run)

        initial_state: PipelineState = {
            "idea": idea,
            "user_id": user_id,
            "run_id": run_id,
            "pain_discovery": None,
            "competitor_research": None,
            "viability": None,
            "synthesis": None,
            "agent1_attempts": 0,
            "agent2_attempts": 0,
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
            msg = f"Agent {agent_num} timed out after {settings.agent_timeout}s"
            logger.error(f"Pipeline failed for run {run_id}: {msg}")
            if run:
                run.status = ValidationStatus.FAILED
                run.error = msg
                run.completed_at = datetime.now(timezone.utc)
                await self.repository.update(run)
            pubsub.publish(run_id, PipelineErrorEvent.create(agent_num, msg))

        except Exception as e:
            logger.exception(f"Pipeline failed for run {run_id}")
            run = await self.repository.get(run_id)
            agent_num = run.current_agent if run else 0
            if run:
                run.status = ValidationStatus.FAILED
                run.error = str(e)
                run.completed_at = datetime.now(timezone.utc)
                await self.repository.update(run)
            pubsub.publish(run_id, PipelineErrorEvent.create(agent_num, str(e)))

        finally:
            pubsub.publish(run_id, None)  # Signal stream end
