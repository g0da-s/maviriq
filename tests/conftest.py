import os
import pytest
import pytest_asyncio

# Point DB to a test-specific file before any maverick imports
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("SERPER_API_KEY", "test-key")

from maverick.models.schemas import (
    Competitor,
    CompetitorPricing,
    CompetitorResearchOutput,
    PainDiscoveryOutput,
    PainPoint,
    SynthesisOutput,
    UserSegment,
    Verdict,
    ViabilityOutput,
    ViabilitySignal,
)
from maverick.storage import database as db_module
from maverick.storage.database import init_db


# ──────────────────────────────────────────────
# Database fixture — use a temp file per test session
# ──────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def setup_test_db(tmp_path_factory):
    """Use a temporary SQLite database for each test session."""
    tmp = tmp_path_factory.mktemp("db")
    test_db = str(tmp / "test_maverick.db")
    db_module.DB_PATH = test_db
    await init_db()
    yield
    # cleanup happens when tmp_path is removed


# ──────────────────────────────────────────────
# Realistic mock data factories
# ──────────────────────────────────────────────

@pytest.fixture
def sample_user_segment() -> UserSegment:
    return UserSegment(
        label="Early-stage startup founders",
        description="Technical founders at pre-seed/seed stage struggling with pitch decks",
        frequency=8,
        willingness_to_pay="high",
    )


@pytest.fixture
def sample_pain_discovery(sample_user_segment) -> PainDiscoveryOutput:
    return PainDiscoveryOutput(
        idea="AI pitch deck generator",
        pain_points=[
            PainPoint(
                source="reddit",
                source_url="https://reddit.com/r/startups/abc",
                quote="Spent 15 hours on my deck and it still looks terrible",
                author_context="Technical founder, pre-seed startup",
                pain_severity=4,
                date="2025-01-10",
            ),
            PainPoint(
                source="hackernews",
                source_url="https://news.ycombinator.com/item?id=123",
                quote="I'm an engineer, not a designer. Why is making slides so painful?",
                author_context="Software engineer building a startup",
                pain_severity=5,
            ),
            PainPoint(
                source="reddit",
                source_url="https://reddit.com/r/Entrepreneur/def",
                quote="Paid a freelancer $500 for a deck that was mediocre",
                author_context="Solo founder, bootstrapped",
                pain_severity=3,
            ),
        ],
        user_segments=[
            sample_user_segment,
            UserSegment(
                label="Solo consultants",
                description="Independent consultants pitching for contracts",
                frequency=3,
                willingness_to_pay="medium",
            ),
        ],
        primary_target_user=sample_user_segment,
        pain_summary="Founders consistently struggle with pitch deck design, spending 10-20 hours on decks that still look unprofessional. Technical founders feel this most acutely.",
        search_queries_used=["pitch deck frustrating", "pitch deck hard reddit"],
        data_quality="full",
    )


@pytest.fixture
def sample_competitor_research(sample_user_segment) -> CompetitorResearchOutput:
    return CompetitorResearchOutput(
        target_user=sample_user_segment,
        competitors=[
            Competitor(
                name="Slidebean",
                url="https://slidebean.com",
                one_liner="AI-powered pitch deck builder for startups",
                pricing=[
                    CompetitorPricing(plan_name="Starter", price="$29/mo", features=["AI design", "Templates"]),
                    CompetitorPricing(plan_name="Premium", price="$49/mo", features=["AI design", "Analytics", "Custom branding"]),
                ],
                strengths=["Good AI layout engine", "Startup-focused templates"],
                weaknesses=["Generic templates", "Limited customization"],
                review_sentiment="mixed",
                review_count=120,
                source="google",
            ),
            Competitor(
                name="Beautiful.ai",
                url="https://beautiful.ai",
                one_liner="Smart presentation software with design rules",
                pricing=[
                    CompetitorPricing(plan_name="Pro", price="$12/mo", features=["Smart templates", "Export"]),
                ],
                strengths=["Clean design output", "Easy to use"],
                weaknesses=["Not startup-focused", "No AI content generation"],
                review_sentiment="positive",
                review_count=250,
                source="g2",
            ),
        ],
        market_saturation="medium",
        avg_price_point="$20-50/mo",
        common_complaints=["Templates feel generic", "AI doesn't understand startup context"],
        underserved_needs=["Data-driven decks for technical founders", "Integration with metrics dashboards"],
        data_quality="full",
    )


@pytest.fixture
def sample_viability() -> ViabilityOutput:
    return ViabilityOutput(
        people_pay=True,
        people_pay_reasoning="Slidebean has 50k+ users at $29-49/mo. Beautiful.ai has 250+ G2 reviews. Clear willingness to pay.",
        reachability="easy",
        reachability_reasoning="Target users are active on r/startups, Indie Hackers, and YC communities",
        market_gap="No tool specifically builds data-focused pitch decks for technical founders",
        gap_size="medium",
        signals=[
            ViabilitySignal(signal="Multiple competitors with paying users", direction="positive", confidence=0.9, source="competitor_pricing"),
            ViabilitySignal(signal="Active online communities for target user", direction="positive", confidence=0.85, source="pain_discovery"),
            ViabilitySignal(signal="Market has established players", direction="negative", confidence=0.6, source="competitor_count"),
        ],
        risk_factors=["Established competitors with funding", "AI commoditization could erode moat"],
        opportunity_score=0.72,
    )


@pytest.fixture
def sample_synthesis() -> SynthesisOutput:
    return SynthesisOutput(
        verdict=Verdict.BUILD,
        confidence=0.75,
        one_line_summary="Strong pain signal from technical founders; medium market gap in data-driven pitch decks",
        reasoning="The research shows genuine pain among technical founders who struggle with pitch deck design. While competitors exist, none specifically target the data-focused approach that technical founders need.",
        key_strengths=["Clear pain point", "Reachable target users", "Willingness to pay proven"],
        key_risks=["Established competitors", "AI commoditization"],
        recommended_mvp="A pitch deck generator that pulls metrics from Stripe/Analytics and auto-generates data slides",
        recommended_positioning="The pitch deck tool built for technical founders who think in data, not design",
        target_user_summary="Early-stage technical founders (engineers) at pre-seed/seed stage",
        estimated_market_size="$500M-1B (presentation software market segment)",
        next_steps=["Build MVP with 3 templates", "Launch on Indie Hackers", "Get 10 beta users"],
    )
