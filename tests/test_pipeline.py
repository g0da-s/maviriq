"""Integration tests for the pipeline runner with mocked agents."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from maverick.models.schemas import (
    CompetitorResearchOutput,
    PainDiscoveryOutput,
    SynthesisOutput,
    ValidationStatus,
    ViabilityOutput,
)
from maverick.pipeline.events import (
    AgentCompletedEvent,
    AgentStartedEvent,
    PipelineCompletedEvent,
    PipelineErrorEvent,
)
from maverick.pipeline.runner import PipelineRunner


class TestPipelineRunner:
    @pytest.fixture
    def runner(
        self,
        sample_pain_discovery,
        sample_competitor_research,
        sample_viability,
        sample_synthesis,
    ):
        """Create a pipeline runner with all agents and repository mocked."""
        with patch("maverick.pipeline.runner.LLMService"), \
             patch("maverick.pipeline.runner.SerperService"):
            runner = PipelineRunner()

        runner.agent1.run = AsyncMock(return_value=sample_pain_discovery)
        runner.agent2.run = AsyncMock(return_value=sample_competitor_research)
        runner.agent3.run = AsyncMock(return_value=sample_viability)
        runner.agent4.run = AsyncMock(return_value=sample_synthesis)
        runner.repository = MagicMock()
        runner.repository.create = AsyncMock()
        runner.repository.update = AsyncMock()

        return runner

    @pytest.mark.asyncio
    async def test_full_pipeline_emits_correct_events(self, runner):
        events = []
        async for event in runner.run("val_pipeline001", "test idea"):
            events.append(event)

        # Should have: 4x started + 4x completed + 1x pipeline_completed = 9 events
        assert len(events) == 9

        event_types = [e.event for e in events]
        assert event_types.count("agent_started") == 4
        assert event_types.count("agent_completed") == 4
        assert event_types.count("pipeline_completed") == 1

    @pytest.mark.asyncio
    async def test_events_in_correct_order(self, runner):
        events = []
        async for event in runner.run("val_order001", "test idea"):
            events.append(event)

        # Verify interleaved start/complete pattern
        assert events[0].event == "agent_started"
        assert events[0].data["agent"] == 1
        assert events[1].event == "agent_completed"
        assert events[1].data["agent"] == 1

        assert events[2].event == "agent_started"
        assert events[2].data["agent"] == 2
        assert events[3].event == "agent_completed"
        assert events[3].data["agent"] == 2

        assert events[4].event == "agent_started"
        assert events[4].data["agent"] == 3
        assert events[5].event == "agent_completed"
        assert events[5].data["agent"] == 3

        assert events[6].event == "agent_started"
        assert events[6].data["agent"] == 4
        assert events[7].event == "agent_completed"
        assert events[7].data["agent"] == 4

        assert events[8].event == "pipeline_completed"

    @pytest.mark.asyncio
    async def test_pipeline_saves_state_to_db(self, runner):
        events = []
        async for event in runner.run("val_dbsave001", "test idea"):
            events.append(event)

        # Verify the repository was called to save state
        # create is called once + update is called multiple times (each agent start + complete + final)
        assert runner.repository.create.call_count == 1
        assert runner.repository.update.call_count >= 8  # At least 2 per agent + final

    @pytest.mark.asyncio
    async def test_pipeline_passes_data_between_agents(self, runner, sample_pain_discovery):
        events = []
        async for event in runner.run("val_chain001", "test idea"):
            events.append(event)

        # Agent 2 should receive the target user from Agent 1
        agent2_call = runner.agent2.run.call_args[0][0]
        assert agent2_call.target_user.label == sample_pain_discovery.primary_target_user.label

        # Agent 3 should receive outputs from Agent 1 and 2
        agent3_call = runner.agent3.run.call_args[0][0]
        assert agent3_call.pain_discovery is not None
        assert agent3_call.competitor_research is not None

        # Agent 4 should receive all prior outputs
        agent4_call = runner.agent4.run.call_args[0][0]
        assert agent4_call.pain_discovery is not None
        assert agent4_call.competitor_research is not None
        assert agent4_call.viability is not None

    @pytest.mark.asyncio
    async def test_pipeline_handles_agent_failure(self, runner):
        # Make agent 2 fail
        runner.agent2.run = AsyncMock(side_effect=RuntimeError("Serper API is down"))

        events = []
        async for event in runner.run("val_fail001", "test idea"):
            events.append(event)

        # Should have: agent1 start + complete, agent2 start, then error
        error_events = [e for e in events if e.event == "pipeline_error"]
        assert len(error_events) == 1
        assert "Serper API is down" in error_events[0].data["error"]

    @pytest.mark.asyncio
    async def test_pipeline_completed_event_has_verdict(self, runner, sample_synthesis):
        events = []
        async for event in runner.run("val_verdict001", "test idea"):
            events.append(event)

        completed = [e for e in events if e.event == "pipeline_completed"][0]
        assert completed.data["verdict"] == sample_synthesis.verdict.value
        assert completed.data["confidence"] == sample_synthesis.confidence

    @pytest.mark.asyncio
    async def test_agents_called_sequentially(self, runner):
        """Verify agents are called in order 1 -> 2 -> 3 -> 4."""
        call_order = []

        a1_rv = runner.agent1.run.return_value
        a2_rv = runner.agent2.run.return_value
        a3_rv = runner.agent3.run.return_value
        a4_rv = runner.agent4.run.return_value

        async def track1(*a):
            call_order.append(1)
            return a1_rv

        async def track2(*a):
            call_order.append(2)
            return a2_rv

        async def track3(*a):
            call_order.append(3)
            return a3_rv

        async def track4(*a):
            call_order.append(4)
            return a4_rv

        runner.agent1.run = track1
        runner.agent2.run = track2
        runner.agent3.run = track3
        runner.agent4.run = track4

        async for _ in runner.run("val_seq001", "test idea"):
            pass

        assert call_order == [1, 2, 3, 4]


class TestSSEEvents:
    def test_agent_started_event(self):
        event = AgentStartedEvent.create(1, "Pain Discovery")
        assert event.event == "agent_started"
        assert event.data["agent"] == 1
        assert event.data["name"] == "Pain Discovery"
        assert "timestamp" in event.data

    def test_agent_completed_event(self):
        event = AgentCompletedEvent.create(2, "Competitor Research", {"key": "value"})
        assert event.event == "agent_completed"
        assert event.data["agent"] == 2
        assert event.data["output"] == {"key": "value"}

    def test_pipeline_completed_event(self):
        event = PipelineCompletedEvent.create("val_test", "BUILD", 0.85)
        assert event.event == "pipeline_completed"
        assert event.data["id"] == "val_test"
        assert event.data["verdict"] == "BUILD"
        assert event.data["confidence"] == 0.85

    def test_pipeline_error_event(self):
        event = PipelineErrorEvent.create(2, "Something broke")
        assert event.event == "pipeline_error"
        assert event.data["agent"] == 2
        assert event.data["error"] == "Something broke"
