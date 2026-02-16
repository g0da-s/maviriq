"""Tests for all 5 pipeline agents with mocked LLM and Search."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from maviriq.agents.pain_discovery import PainDiscoveryAgent, TOOL_NAMES as PAIN_TOOLS
from maviriq.agents.competitor_research import CompetitorResearchAgent, TOOL_NAMES as COMP_TOOLS
from maviriq.agents.market_intelligence import MarketIntelligenceAgent, TOOL_NAMES as MARKET_TOOLS
from maviriq.agents.graveyard_research import GraveyardResearchAgent, TOOL_NAMES as GRAVE_TOOLS
from maviriq.agents.synthesis import SynthesisAgent
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
    SynthesisOutput,
)
from maviriq.services.search import SearchResult


def make_mock_services(
    run_tool_loop_return=None,
    llm_structured_return=None,
):
    """Create mock LLM and Search services for the new agentic architecture."""
    llm = MagicMock()
    search = MagicMock()

    if run_tool_loop_return is not None:
        llm.run_tool_loop = AsyncMock(return_value=run_tool_loop_return)
    if llm_structured_return is not None:
        llm.generate_structured = AsyncMock(return_value=llm_structured_return)

    # Mock all search methods so build_tools_for_agent can reference them
    default_results = [
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
    search.search_news = AsyncMock(return_value=default_results)
    search.search_producthunt = AsyncMock(return_value=default_results)
    search.search_crunchbase = AsyncMock(return_value=default_results)
    search.search_twitter = AsyncMock(return_value=default_results)
    search.search_youtube = AsyncMock(return_value=default_results)
    search.search_linkedin_jobs = AsyncMock(return_value=default_results)

    return llm, search


# ──────────────────────────────────────────────
# Agent 1: Pain & User Discovery
# ──────────────────────────────────────────────

class TestPainDiscoveryAgent:
    @pytest.mark.asyncio
    async def test_runs_successfully(self, sample_pain_discovery):
        llm, search = make_mock_services(run_tool_loop_return=sample_pain_discovery)

        agent = PainDiscoveryAgent(llm, search)
        result = await agent.run(PainDiscoveryInput(idea="AI pitch deck generator"))

        assert isinstance(result, PainDiscoveryOutput)
        assert result.idea == "AI pitch deck generator"
        assert len(result.pain_points) > 0
        assert result.primary_target_user is not None

    @pytest.mark.asyncio
    async def test_passes_correct_tools(self, sample_pain_discovery):
        llm, search = make_mock_services(run_tool_loop_return=sample_pain_discovery)

        agent = PainDiscoveryAgent(llm, search)
        await agent.run(PainDiscoveryInput(idea="test idea"))

        # run_tool_loop should have been called with the right tools
        llm.run_tool_loop.assert_called_once()
        call_kwargs = llm.run_tool_loop.call_args
        tools = call_kwargs.kwargs.get("tools") or call_kwargs[1].get("tools") if call_kwargs[1] else None
        if tools is None:
            # positional args: system_prompt, user_prompt, tools, ...
            tools = call_kwargs[0][2] if len(call_kwargs[0]) > 2 else llm.run_tool_loop.call_args.kwargs["tools"]
        tool_names = [t["name"] for t in tools]
        for expected in PAIN_TOOLS:
            assert expected in tool_names

    @pytest.mark.asyncio
    async def test_passes_correct_output_schema(self, sample_pain_discovery):
        llm, search = make_mock_services(run_tool_loop_return=sample_pain_discovery)

        agent = PainDiscoveryAgent(llm, search)
        await agent.run(PainDiscoveryInput(idea="test idea"))

        call_kwargs = llm.run_tool_loop.call_args.kwargs
        assert call_kwargs["output_schema"] is PainDiscoveryOutput

    @pytest.mark.asyncio
    async def test_post_process_sets_idea(self, sample_pain_discovery):
        llm, search = make_mock_services(run_tool_loop_return=sample_pain_discovery)

        agent = PainDiscoveryAgent(llm, search)
        result = await agent.run(PainDiscoveryInput(idea="my specific idea"))

        assert result.idea == "my specific idea"


# ──────────────────────────────────────────────
# Agent 2: Competitor Research
# ──────────────────────────────────────────────

class TestCompetitorResearchAgent:
    @pytest.mark.asyncio
    async def test_runs_successfully(self, sample_user_segment, sample_competitor_research):
        llm, search = make_mock_services(run_tool_loop_return=sample_competitor_research)

        agent = CompetitorResearchAgent(llm, search)
        result = await agent.run(
            CompetitorResearchInput(idea="pitch deck generator", target_user=sample_user_segment)
        )

        assert isinstance(result, CompetitorResearchOutput)
        assert len(result.competitors) > 0
        assert result.target_user.label == sample_user_segment.label

    @pytest.mark.asyncio
    async def test_passes_correct_tools(self, sample_user_segment, sample_competitor_research):
        llm, search = make_mock_services(run_tool_loop_return=sample_competitor_research)

        agent = CompetitorResearchAgent(llm, search)
        await agent.run(
            CompetitorResearchInput(idea="test", target_user=sample_user_segment)
        )

        call_kwargs = llm.run_tool_loop.call_args.kwargs
        tool_names = [t["name"] for t in call_kwargs["tools"]]
        for expected in COMP_TOOLS:
            assert expected in tool_names

    @pytest.mark.asyncio
    async def test_post_process_sets_target_user(self, sample_user_segment, sample_competitor_research):
        llm, search = make_mock_services(run_tool_loop_return=sample_competitor_research)

        agent = CompetitorResearchAgent(llm, search)
        result = await agent.run(
            CompetitorResearchInput(idea="test", target_user=sample_user_segment)
        )

        assert result.target_user.label == sample_user_segment.label


# ──────────────────────────────────────────────
# Agent 3: Market Intelligence
# ──────────────────────────────────────────────

class TestMarketIntelligenceAgent:
    @pytest.mark.asyncio
    async def test_runs_successfully(self, sample_market_intelligence):
        llm, search = make_mock_services(run_tool_loop_return=sample_market_intelligence)

        agent = MarketIntelligenceAgent(llm, search)
        result = await agent.run(MarketIntelligenceInput(idea="AI pitch deck generator"))

        assert isinstance(result, MarketIntelligenceOutput)
        assert result.market_size_estimate is not None
        assert result.growth_direction in ("growing", "stable", "shrinking", "unknown")
        assert len(result.distribution_channels) > 0

    @pytest.mark.asyncio
    async def test_passes_correct_tools(self, sample_market_intelligence):
        llm, search = make_mock_services(run_tool_loop_return=sample_market_intelligence)

        agent = MarketIntelligenceAgent(llm, search)
        await agent.run(MarketIntelligenceInput(idea="test idea"))

        call_kwargs = llm.run_tool_loop.call_args.kwargs
        tool_names = [t["name"] for t in call_kwargs["tools"]]
        for expected in MARKET_TOOLS:
            assert expected in tool_names

    @pytest.mark.asyncio
    async def test_passes_correct_output_schema(self, sample_market_intelligence):
        llm, search = make_mock_services(run_tool_loop_return=sample_market_intelligence)

        agent = MarketIntelligenceAgent(llm, search)
        await agent.run(MarketIntelligenceInput(idea="test idea"))

        call_kwargs = llm.run_tool_loop.call_args.kwargs
        assert call_kwargs["output_schema"] is MarketIntelligenceOutput


# ──────────────────────────────────────────────
# Agent 4: Graveyard Research
# ──────────────────────────────────────────────

class TestGraveyardResearchAgent:
    @pytest.mark.asyncio
    async def test_runs_successfully(self, sample_graveyard_research):
        llm, search = make_mock_services(run_tool_loop_return=sample_graveyard_research)

        agent = GraveyardResearchAgent(llm, search)
        result = await agent.run(GraveyardResearchInput(idea="AI pitch deck generator"))

        assert isinstance(result, GraveyardResearchOutput)
        assert len(result.previous_attempts) > 0
        assert len(result.failure_reasons) > 0
        assert result.lessons_learned is not None

    @pytest.mark.asyncio
    async def test_passes_correct_tools(self, sample_graveyard_research):
        llm, search = make_mock_services(run_tool_loop_return=sample_graveyard_research)

        agent = GraveyardResearchAgent(llm, search)
        await agent.run(GraveyardResearchInput(idea="test idea"))

        call_kwargs = llm.run_tool_loop.call_args.kwargs
        tool_names = [t["name"] for t in call_kwargs["tools"]]
        for expected in GRAVE_TOOLS:
            assert expected in tool_names

    @pytest.mark.asyncio
    async def test_passes_correct_output_schema(self, sample_graveyard_research):
        llm, search = make_mock_services(run_tool_loop_return=sample_graveyard_research)

        agent = GraveyardResearchAgent(llm, search)
        await agent.run(GraveyardResearchInput(idea="test idea"))

        call_kwargs = llm.run_tool_loop.call_args.kwargs
        assert call_kwargs["output_schema"] is GraveyardResearchOutput


# ──────────────────────────────────────────────
# Agent 5: Synthesis & Verdict
# ──────────────────────────────────────────────

class TestSynthesisAgent:
    """Synthesis agent uses two LLM passes: viability analysis then verdict."""

    @staticmethod
    def _make_two_pass_mocks(sample_synthesis):
        """Build mock returns for the two-pass synthesis architecture.

        Pass 1 returns _ViabilityAnalysis, Pass 2 returns _VerdictStrategy.
        We import the private schemas here so tests can construct proper mocks.
        """
        from maviriq.agents.synthesis import _ViabilityAnalysis, _VerdictStrategy

        viability_mock = _ViabilityAnalysis(
            people_pay=sample_synthesis.people_pay,
            people_pay_reasoning=sample_synthesis.people_pay_reasoning,
            reachability=sample_synthesis.reachability,
            reachability_reasoning=sample_synthesis.reachability_reasoning,
            market_gap=sample_synthesis.market_gap,
            gap_size=sample_synthesis.gap_size,
            signals=sample_synthesis.signals,
            estimated_market_size=sample_synthesis.estimated_market_size,
        )
        verdict_mock = _VerdictStrategy(
            verdict=sample_synthesis.verdict,
            confidence=sample_synthesis.confidence,
            one_line_summary=sample_synthesis.one_line_summary,
            reasoning=sample_synthesis.reasoning,
            key_strengths=sample_synthesis.key_strengths,
            key_risks=sample_synthesis.key_risks,
            recommended_mvp=sample_synthesis.recommended_mvp,
            recommended_positioning=sample_synthesis.recommended_positioning,
            target_user_summary=sample_synthesis.target_user_summary,
            next_steps=sample_synthesis.next_steps,
            differentiation_strategy=sample_synthesis.differentiation_strategy,
            previous_attempts_summary=sample_synthesis.previous_attempts_summary,
            lessons_from_failures=sample_synthesis.lessons_from_failures,
        )
        return viability_mock, verdict_mock

    @pytest.mark.asyncio
    async def test_runs_successfully(
        self, sample_pain_discovery, sample_competitor_research,
        sample_market_intelligence, sample_graveyard_research, sample_synthesis,
    ):
        viability_mock, verdict_mock = self._make_two_pass_mocks(sample_synthesis)
        llm, search = make_mock_services()
        llm.generate_structured = AsyncMock(side_effect=[viability_mock, verdict_mock])

        agent = SynthesisAgent(llm, search)
        result = await agent.run(
            SynthesisInput(
                idea="pitch deck generator",
                pain_discovery=sample_pain_discovery,
                competitor_research=sample_competitor_research,
                market_intelligence=sample_market_intelligence,
                graveyard_research=sample_graveyard_research,
            )
        )

        assert isinstance(result, SynthesisOutput)
        assert result.verdict in ["BUILD", "SKIP", "MAYBE"]
        assert 0 <= result.confidence <= 1
        assert len(result.next_steps) > 0

    @pytest.mark.asyncio
    async def test_two_pass_calls(
        self, sample_pain_discovery, sample_competitor_research,
        sample_market_intelligence, sample_graveyard_research, sample_synthesis,
    ):
        """Verify synthesis makes exactly 2 LLM calls with the correct schemas."""
        from maviriq.agents.synthesis import _ViabilityAnalysis, _VerdictStrategy

        viability_mock, verdict_mock = self._make_two_pass_mocks(sample_synthesis)
        llm, search = make_mock_services()
        llm.generate_structured = AsyncMock(side_effect=[viability_mock, verdict_mock])

        agent = SynthesisAgent(llm, search)
        await agent.run(
            SynthesisInput(
                idea="test",
                pain_discovery=sample_pain_discovery,
                competitor_research=sample_competitor_research,
                market_intelligence=sample_market_intelligence,
                graveyard_research=sample_graveyard_research,
            )
        )

        assert llm.generate_structured.call_count == 2

        # Pass 1 should use _ViabilityAnalysis
        pass1_kwargs = llm.generate_structured.call_args_list[0].kwargs
        assert pass1_kwargs["output_schema"] is _ViabilityAnalysis

        # Pass 2 should use _VerdictStrategy
        pass2_kwargs = llm.generate_structured.call_args_list[1].kwargs
        assert pass2_kwargs["output_schema"] is _VerdictStrategy

        # Pass 2 context should contain viability results
        assert "VIABILITY ANALYSIS" in pass2_kwargs["user_prompt"]

    @pytest.mark.asyncio
    async def test_no_search_calls(
        self, sample_pain_discovery, sample_competitor_research,
        sample_market_intelligence, sample_graveyard_research, sample_synthesis,
    ):
        """Synthesis agent should be pure LLM, no search calls."""
        viability_mock, verdict_mock = self._make_two_pass_mocks(sample_synthesis)
        llm, search = make_mock_services()
        llm.generate_structured = AsyncMock(side_effect=[viability_mock, verdict_mock])

        agent = SynthesisAgent(llm, search)
        await agent.run(
            SynthesisInput(
                idea="test",
                pain_discovery=sample_pain_discovery,
                competitor_research=sample_competitor_research,
                market_intelligence=sample_market_intelligence,
                graveyard_research=sample_graveyard_research,
            )
        )

        assert llm.generate_structured.call_count == 2
        search.search.assert_not_called()
        search.search_reddit.assert_not_called()

    @pytest.mark.asyncio
    async def test_build_verdict_includes_mvp(
        self, sample_pain_discovery, sample_competitor_research,
        sample_market_intelligence, sample_graveyard_research, sample_synthesis,
    ):
        """When verdict is BUILD, recommended_mvp should be populated."""
        viability_mock, verdict_mock = self._make_two_pass_mocks(sample_synthesis)
        llm, search = make_mock_services()
        llm.generate_structured = AsyncMock(side_effect=[viability_mock, verdict_mock])

        agent = SynthesisAgent(llm, search)
        result = await agent.run(
            SynthesisInput(
                idea="test",
                pain_discovery=sample_pain_discovery,
                competitor_research=sample_competitor_research,
                market_intelligence=sample_market_intelligence,
                graveyard_research=sample_graveyard_research,
            )
        )

        assert result.verdict == "BUILD"
        assert result.recommended_mvp is not None

    @pytest.mark.asyncio
    async def test_works_without_optional_agents(
        self, sample_pain_discovery, sample_competitor_research, sample_synthesis,
    ):
        """Synthesis should still work if market_intelligence and graveyard_research are None."""
        viability_mock, verdict_mock = self._make_two_pass_mocks(sample_synthesis)
        llm, search = make_mock_services()
        llm.generate_structured = AsyncMock(side_effect=[viability_mock, verdict_mock])

        agent = SynthesisAgent(llm, search)
        result = await agent.run(
            SynthesisInput(
                idea="test",
                pain_discovery=sample_pain_discovery,
                competitor_research=sample_competitor_research,
            )
        )

        assert isinstance(result, SynthesisOutput)
        assert llm.generate_structured.call_count == 2
