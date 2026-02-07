"""Tests for all 4 pipeline agents with mocked LLM and Search."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from maverick.agents.pain_discovery import PainDiscoveryAgent
from maverick.agents.competitor_research import CompetitorResearchAgent
from maverick.agents.viability_analysis import ViabilityAnalysisAgent
from maverick.agents.synthesis import SynthesisAgent
from maverick.models.schemas import (
    CompetitorResearchInput,
    CompetitorResearchOutput,
    PainDiscoveryInput,
    PainDiscoveryOutput,
    SynthesisInput,
    SynthesisOutput,
    ViabilityInput,
    ViabilityOutput,
)
from maverick.services.search import SearchResult


def make_mock_services(
    llm_structured_return=None,
    llm_list_return=None,
    search_results=None,
):
    """Create mock LLM and Search services."""
    llm = MagicMock()
    search = MagicMock()

    if llm_structured_return is not None:
        llm.generate_structured = AsyncMock(return_value=llm_structured_return)
    if llm_list_return is not None:
        llm.generate_list = AsyncMock(return_value=llm_list_return)

    default_results = search_results or [
        SearchResult(
            title="Test result",
            url="https://example.com/1",
            snippet="A test snippet about the problem",
        )
    ]
    search.search = AsyncMock(return_value=default_results)
    search.search_reddit = AsyncMock(return_value=default_results)
    search.search_hackernews = AsyncMock(return_value=default_results)
    search.search_g2 = AsyncMock(return_value=default_results)
    search.search_capterra = AsyncMock(return_value=default_results)

    return llm, search


# ──────────────────────────────────────────────
# Agent 1: Pain & User Discovery
# ──────────────────────────────────────────────

class TestPainDiscoveryAgent:
    @pytest.mark.asyncio
    async def test_runs_successfully(self, sample_pain_discovery):
        llm, search = make_mock_services(
            llm_structured_return=sample_pain_discovery,
            llm_list_return=["query1", "query2", "query3"],
        )

        agent = PainDiscoveryAgent(llm, search)
        result = await agent.run(PainDiscoveryInput(idea="AI pitch deck generator"))

        assert isinstance(result, PainDiscoveryOutput)
        assert result.idea == "AI pitch deck generator"
        assert len(result.pain_points) > 0
        assert result.primary_target_user is not None

    @pytest.mark.asyncio
    async def test_generates_search_queries_first(self, sample_pain_discovery):
        llm, search = make_mock_services(
            llm_structured_return=sample_pain_discovery,
            llm_list_return=["pitch deck complaints", "pitch deck hard reddit"],
        )

        agent = PainDiscoveryAgent(llm, search)
        await agent.run(PainDiscoveryInput(idea="pitch deck generator"))

        # Should have called generate_list for query generation
        llm.generate_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_searches_multiple_sources(self, sample_pain_discovery):
        llm, search = make_mock_services(
            llm_structured_return=sample_pain_discovery,
            llm_list_return=["q1", "q2", "q3"],
        )

        agent = PainDiscoveryAgent(llm, search)
        await agent.run(PainDiscoveryInput(idea="test idea"))

        # Should search Reddit, HN, and broad
        assert search.search_reddit.call_count > 0
        assert search.search_hackernews.call_count > 0
        assert search.search.call_count > 0

    @pytest.mark.asyncio
    async def test_attaches_search_queries_to_output(self, sample_pain_discovery):
        queries = ["q1", "q2", "q3"]
        llm, search = make_mock_services(
            llm_structured_return=sample_pain_discovery,
            llm_list_return=queries,
        )

        agent = PainDiscoveryAgent(llm, search)
        result = await agent.run(PainDiscoveryInput(idea="test idea"))

        assert result.search_queries_used == queries


# ──────────────────────────────────────────────
# Agent 2: Competitor Research
# ──────────────────────────────────────────────

class TestCompetitorResearchAgent:
    @pytest.mark.asyncio
    async def test_runs_successfully(self, sample_user_segment, sample_competitor_research):
        llm, search = make_mock_services(
            llm_structured_return=sample_competitor_research,
            llm_list_return=["competitor query 1", "competitor query 2"],
        )

        agent = CompetitorResearchAgent(llm, search)
        result = await agent.run(
            CompetitorResearchInput(idea="pitch deck generator", target_user=sample_user_segment)
        )

        assert isinstance(result, CompetitorResearchOutput)
        assert len(result.competitors) > 0
        assert result.target_user.label == sample_user_segment.label

    @pytest.mark.asyncio
    async def test_searches_g2_and_capterra(self, sample_user_segment, sample_competitor_research):
        llm, search = make_mock_services(
            llm_structured_return=sample_competitor_research,
            llm_list_return=["q1"],
        )

        agent = CompetitorResearchAgent(llm, search)
        await agent.run(
            CompetitorResearchInput(idea="test", target_user=sample_user_segment)
        )

        search.search_g2.assert_called_once()
        search.search_capterra.assert_called_once()


# ──────────────────────────────────────────────
# Agent 3: Viability Analysis
# ──────────────────────────────────────────────

class TestViabilityAnalysisAgent:
    @pytest.mark.asyncio
    async def test_runs_successfully(
        self, sample_pain_discovery, sample_competitor_research, sample_viability
    ):
        llm, search = make_mock_services(llm_structured_return=sample_viability)

        agent = ViabilityAnalysisAgent(llm, search)
        result = await agent.run(
            ViabilityInput(
                idea="pitch deck generator",
                pain_discovery=sample_pain_discovery,
                competitor_research=sample_competitor_research,
            )
        )

        assert isinstance(result, ViabilityOutput)
        assert isinstance(result.people_pay, bool)
        assert 0 <= result.opportunity_score <= 1

    @pytest.mark.asyncio
    async def test_no_search_calls(
        self, sample_pain_discovery, sample_competitor_research, sample_viability
    ):
        """Viability agent should be pure LLM, no search calls."""
        llm, search = make_mock_services(llm_structured_return=sample_viability)

        agent = ViabilityAnalysisAgent(llm, search)
        await agent.run(
            ViabilityInput(
                idea="test",
                pain_discovery=sample_pain_discovery,
                competitor_research=sample_competitor_research,
            )
        )

        # Should only call LLM, not search
        llm.generate_structured.assert_called_once()
        search.search.assert_not_called()
        search.search_reddit.assert_not_called()


# ──────────────────────────────────────────────
# Agent 4: Synthesis & Verdict
# ──────────────────────────────────────────────

class TestSynthesisAgent:
    @pytest.mark.asyncio
    async def test_runs_successfully(
        self, sample_pain_discovery, sample_competitor_research, sample_viability, sample_synthesis
    ):
        llm, search = make_mock_services(llm_structured_return=sample_synthesis)

        agent = SynthesisAgent(llm, search)
        result = await agent.run(
            SynthesisInput(
                idea="pitch deck generator",
                pain_discovery=sample_pain_discovery,
                competitor_research=sample_competitor_research,
                viability=sample_viability,
            )
        )

        assert isinstance(result, SynthesisOutput)
        assert result.verdict in ["BUILD", "SKIP", "CONDITIONAL"]
        assert 0 <= result.confidence <= 1
        assert len(result.next_steps) > 0

    @pytest.mark.asyncio
    async def test_no_search_calls(
        self, sample_pain_discovery, sample_competitor_research, sample_viability, sample_synthesis
    ):
        """Synthesis agent should be pure LLM, no search calls."""
        llm, search = make_mock_services(llm_structured_return=sample_synthesis)

        agent = SynthesisAgent(llm, search)
        await agent.run(
            SynthesisInput(
                idea="test",
                pain_discovery=sample_pain_discovery,
                competitor_research=sample_competitor_research,
                viability=sample_viability,
            )
        )

        llm.generate_structured.assert_called_once()
        search.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_build_verdict_includes_mvp(
        self, sample_pain_discovery, sample_competitor_research, sample_viability, sample_synthesis
    ):
        """When verdict is BUILD, recommended_mvp should be populated."""
        llm, search = make_mock_services(llm_structured_return=sample_synthesis)

        agent = SynthesisAgent(llm, search)
        result = await agent.run(
            SynthesisInput(
                idea="test",
                pain_discovery=sample_pain_discovery,
                competitor_research=sample_competitor_research,
                viability=sample_viability,
            )
        )

        assert result.verdict == "BUILD"
        assert result.recommended_mvp is not None
