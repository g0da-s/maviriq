from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


# ──────────────────────────────────────────────
# Shared Literal normalizer
# ──────────────────────────────────────────────
# LLMs return inconsistent casing and verbose strings (e.g. "Medium to High").
# This helper normalizes to the exact Literal value Pydantic expects.
#
# How it works:
#   1. Non-strings pass through (Pydantic raises its own error)
#   2. Exact match against allowed values
#   3. Substring match in order (first match wins)
#   4. Falls back to default


def _normalize_literal(v: object, allowed: tuple[str, ...], default: str) -> object:
    if not isinstance(v, str):
        return v
    v_lower = v.lower().strip()
    if v_lower in allowed:
        return v_lower
    for option in allowed:
        if option in v_lower:
            return option
    return default


# ──────────────────────────────────────────────
# Agent 1: Pain & User Discovery
# ──────────────────────────────────────────────


class PainPoint(BaseModel):
    source: str
    source_url: str
    quote: str
    author_context: str
    pain_severity: Literal["high", "moderate", "mild"]
    date: str | None = None

    @field_validator("pain_severity", mode="before")
    @classmethod
    def normalize_pain_severity(cls, v: object) -> object:
        # Backward compat: old DB rows stored severity as 1-5 int
        if isinstance(v, int):
            if v >= 4:
                return "high"
            if v >= 3:
                return "moderate"
            return "mild"
        if not isinstance(v, str):
            return v
        v_lower = v.lower().strip()
        if v_lower in ("high", "moderate", "mild"):
            return v_lower
        if any(
            k in v_lower for k in ("critical", "existential", "major", "significant")
        ):
            return "high"
        if any(k in v_lower for k in ("moderate", "recurring")):
            return "moderate"
        return "mild"


class UserSegment(BaseModel):
    label: str
    description: str
    frequency: int
    willingness_to_pay: Literal["high", "medium", "low"]

    @field_validator("willingness_to_pay", mode="before")
    @classmethod
    def normalize_willingness(cls, v: object) -> object:
        return _normalize_literal(v, ("high", "medium", "low"), "medium")


class PainDiscoveryInput(BaseModel):
    idea: str


class PainDiscoveryOutput(BaseModel):
    idea: str
    pain_points: list[PainPoint]
    user_segments: list[UserSegment]
    primary_target_user: UserSegment
    pain_summary: str
    search_queries_used: list[str] = []


# ──────────────────────────────────────────────
# Agent 2: Competitor Research
# ──────────────────────────────────────────────


class CompetitorPricing(BaseModel):
    plan_name: str
    price: str
    features: list[str]


class Competitor(BaseModel):
    name: str
    url: str
    one_liner: str
    competitor_type: Literal["direct", "indirect", "potential"]
    pricing: list[CompetitorPricing]
    strengths: list[str]
    weaknesses: list[str]
    review_sentiment: Literal["positive", "mixed", "negative"]
    review_count: int | None = None
    source: str

    @field_validator("competitor_type", mode="before")
    @classmethod
    def normalize_competitor_type(cls, v: object) -> object:
        return _normalize_literal(v, ("direct", "indirect", "potential"), "potential")

    @field_validator("review_sentiment", mode="before")
    @classmethod
    def normalize_sentiment(cls, v: object) -> object:
        return _normalize_literal(v, ("positive", "negative", "mixed"), "mixed")


class CompetitorResearchInput(BaseModel):
    idea: str
    target_user: UserSegment | None = None


class CompetitorResearchOutput(BaseModel):
    target_user: UserSegment
    competitors: list[Competitor]
    market_saturation: Literal["low", "medium", "high"]
    avg_price_point: str
    common_complaints: list[str]
    underserved_needs: list[str]

    @field_validator("market_saturation", mode="before")
    @classmethod
    def normalize_saturation(cls, v: object) -> object:
        return _normalize_literal(v, ("high", "medium", "low"), "medium")


# ──────────────────────────────────────────────
# Agent 3: Market Intelligence
# ──────────────────────────────────────────────


class MonetizationSignal(BaseModel):
    signal: str
    source: str
    strength: Literal["strong", "moderate", "weak"]

    @field_validator("strength", mode="before")
    @classmethod
    def normalize_strength(cls, v: object) -> object:
        return _normalize_literal(v, ("strong", "moderate", "weak"), "moderate")


class DistributionChannel(BaseModel):
    channel: str
    reach_estimate: str
    effort: Literal["low", "medium", "high"]

    @field_validator("effort", mode="before")
    @classmethod
    def normalize_effort(cls, v: object) -> object:
        return _normalize_literal(v, ("high", "medium", "low"), "medium")


class FundingSignal(BaseModel):
    description: str
    source_url: str | None = None


class MarketIntelligenceInput(BaseModel):
    idea: str


class MarketIntelligenceOutput(BaseModel):
    market_size_estimate: str
    growth_direction: Literal["growing", "stable", "shrinking", "unknown"]
    growth_evidence: str = ""
    tam_reasoning: str
    distribution_channels: list[DistributionChannel]
    funding_signals: list[str | FundingSignal] = []
    search_queries_used: list[str] = []

    @field_validator("growth_direction", mode="before")
    @classmethod
    def normalize_growth_direction(cls, v: object) -> object:
        if not isinstance(v, str):
            return v
        v_lower = v.lower().strip()
        if v_lower in ("growing", "stable", "shrinking", "unknown"):
            return v_lower
        # "growth" is a synonym the LLM uses for "growing"
        if "growing" in v_lower or "growth" in v_lower:
            return "growing"
        if "shrinking" in v_lower or "declining" in v_lower:
            return "shrinking"
        if "stable" in v_lower:
            return "stable"
        return "unknown"


# ──────────────────────────────────────────────
# Agent 4: Graveyard Research
# ──────────────────────────────────────────────


class PreviousAttempt(BaseModel):
    name: str
    url: str | None = None
    what_they_did: str
    shutdown_reason: str
    year: str | None = None
    source: str


class ChurnSignal(BaseModel):
    signal: str
    source: str
    severity: Literal["high", "medium", "low"]

    @field_validator("severity", mode="before")
    @classmethod
    def normalize_severity(cls, v: object) -> object:
        return _normalize_literal(v, ("high", "medium", "low"), "medium")


class GraveyardResearchInput(BaseModel):
    idea: str


class GraveyardResearchOutput(BaseModel):
    previous_attempts: list[PreviousAttempt]
    failure_reasons: list[str] = []  # deprecated, kept for old DB rows
    lessons_learned: str = ""  # deprecated, kept for old DB rows
    churn_signals: list[ChurnSignal] = []  # deprecated, kept for old DB rows
    search_queries_used: list[str] = []


# ──────────────────────────────────────────────
# Viability (kept for backward compat with old DB rows)
# ──────────────────────────────────────────────


class ViabilitySignal(BaseModel):
    signal: str
    direction: Literal["positive", "negative", "neutral"]
    confidence: float = Field(ge=0.0, le=1.0)
    source: str

    @field_validator("direction", mode="before")
    @classmethod
    def normalize_direction(cls, v: object) -> object:
        return _normalize_literal(v, ("positive", "negative", "neutral"), "neutral")


class ViabilityOutput(BaseModel):
    people_pay: bool
    people_pay_reasoning: str
    reachability: Literal["easy", "moderate", "hard"]
    reachability_reasoning: str
    market_gap: str
    gap_size: Literal["large", "medium", "small", "none"]
    signals: list[ViabilitySignal]
    risk_factors: list[str]
    opportunity_score: float = Field(ge=0.0, le=1.0)

    @field_validator("reachability", mode="before")
    @classmethod
    def normalize_reachability(cls, v: object) -> object:
        return _normalize_literal(v, ("easy", "moderate", "hard"), "moderate")

    @field_validator("gap_size", mode="before")
    @classmethod
    def normalize_gap_size(cls, v: object) -> object:
        return _normalize_literal(v, ("large", "medium", "small", "none"), "medium")


# ──────────────────────────────────────────────
# Agent 5: Synthesis & Verdict
# ──────────────────────────────────────────────


class Verdict(str, Enum):
    BUILD = "BUILD"
    SKIP = "SKIP"
    MAYBE = "MAYBE"


class SynthesisInput(BaseModel):
    idea: str
    pain_discovery: PainDiscoveryOutput
    competitor_research: CompetitorResearchOutput
    market_intelligence: MarketIntelligenceOutput | None = None
    graveyard_research: GraveyardResearchOutput | None = None


class SynthesisOutput(BaseModel):
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    one_line_summary: str
    reasoning: str
    key_strengths: list[str]
    key_risks: list[str]
    recommended_mvp: str | None = None
    recommended_positioning: str | None = None
    target_user_summary: str
    estimated_market_size: str
    next_steps: list[str]

    # Absorbed from old Viability agent
    people_pay: bool
    people_pay_reasoning: str
    reachability: Literal["easy", "moderate", "hard"]
    reachability_reasoning: str
    market_gap: str
    gap_size: Literal["large", "medium", "small", "none"]
    signals: list[ViabilitySignal]

    # From graveyard research synthesis
    differentiation_strategy: str | None = None
    previous_attempts_summary: str | None = None
    lessons_from_failures: str | None = None

    @field_validator("verdict", mode="before")
    @classmethod
    def normalize_verdict(cls, v: object) -> object:
        if isinstance(v, str) and v.upper().strip() == "CONDITIONAL":
            return "MAYBE"
        return v

    @field_validator("reachability", mode="before")
    @classmethod
    def normalize_reachability(cls, v: object) -> object:
        return _normalize_literal(v, ("easy", "moderate", "hard"), "moderate")

    @field_validator("gap_size", mode="before")
    @classmethod
    def normalize_gap_size(cls, v: object) -> object:
        return _normalize_literal(v, ("large", "medium", "small", "none"), "medium")


# ──────────────────────────────────────────────
# Pipeline State
# ──────────────────────────────────────────────


class ValidationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ValidationRun(BaseModel):
    id: str = Field(default_factory=lambda: f"val_{uuid4().hex[:12]}")
    idea: str
    status: ValidationStatus = ValidationStatus.PENDING
    current_agent: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    pain_discovery: PainDiscoveryOutput | None = None
    competitor_research: CompetitorResearchOutput | None = None
    market_intelligence: MarketIntelligenceOutput | None = None
    graveyard_research: GraveyardResearchOutput | None = None
    viability: ViabilityOutput | None = None  # kept for old DB rows
    synthesis: SynthesisOutput | None = None
    error: str | None = None
    total_cost_cents: int = 0
    user_id: str | None = None


# ──────────────────────────────────────────────
# API Models
# ──────────────────────────────────────────────


class CreateValidationRequest(BaseModel):
    idea: str = Field(min_length=10, max_length=500)
    language: str = "lt"

    @field_validator("idea")
    @classmethod
    def validate_idea_quality(cls, v: str) -> str:
        words = v.strip().split()
        if len(words) < 3:
            raise ValueError("please describe your idea in at least a few words")
        from maviriq.services.input_validation import validate_idea_input

        error = validate_idea_input(v)
        if error:
            raise ValueError(error)
        return v


class CreateValidationResponse(BaseModel):
    id: str
    idea: str
    status: ValidationStatus
    stream_url: str


class ValidationListItem(BaseModel):
    id: str
    idea: str
    status: ValidationStatus
    verdict: Verdict | None = None
    confidence: float | None = None
    created_at: datetime


class ValidationListResponse(BaseModel):
    items: list[ValidationListItem]
    total: int
    page: int
    per_page: int
