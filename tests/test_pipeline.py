"""Tests for pipeline events and PipelineGraph construction."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from maviriq.models.schemas import (
    CompetitorResearchOutput,
    GraveyardResearchOutput,
    MarketIntelligenceOutput,
    PainDiscoveryOutput,
    SynthesisOutput,
    ValidationStatus,
)
from maviriq.pipeline.events import (
    AgentCompletedEvent,
    AgentStartedEvent,
    PipelineCompletedEvent,
    PipelineErrorEvent,
)


class TestPipelineGraph:
    def test_graph_initializes_5_agents(self):
        with patch("maviriq.pipeline.runner.LLMService"), \
             patch("maviriq.pipeline.runner.SerperService"):
            from maviriq.pipeline.runner import PipelineGraph
            graph = PipelineGraph()

        assert hasattr(graph, "agent1")  # Pain Discovery
        assert hasattr(graph, "agent2")  # Competitor Research
        assert hasattr(graph, "agent3")  # Market Intelligence
        assert hasattr(graph, "agent4")  # Graveyard Research
        assert hasattr(graph, "agent5")  # Synthesis

    def test_graph_compiles_successfully(self):
        with patch("maviriq.pipeline.runner.LLMService"), \
             patch("maviriq.pipeline.runner.SerperService"):
            from maviriq.pipeline.runner import PipelineGraph
            graph = PipelineGraph()

        assert graph.graph is not None


class TestSSEEvents:
    def test_agent_started_event(self):
        event = AgentStartedEvent.create(1)
        assert event.event == "agent_started"
        assert event.data["agent"] == 1
        assert "timestamp" in event.data

    def test_agent_completed_event(self):
        event = AgentCompletedEvent.create(2, {"key": "value"})
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
