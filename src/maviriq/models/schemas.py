from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


# ──────────────────────────────────────────────
# Agent 1: Pain & User Discovery
# ──────────────────────────────────────────────

class PainPoint(BaseModel):
    source: str  # "reddit", "hackernews", "forum", "blog"
    source_url: str
    quote: str
    author_context: str  # Who is this person (role, industry)
    pain_severity: int = Field(ge=1, le=5)
    date: str | None = None


class UserSegment(BaseModel):
    label: str  # e.g., "early-stage startup founders"
    description: str
    frequency: int  # How many pain points mention this segment
    willingness_to_pay: Literal["high", "medium", "low"]

    @field_validator("willingness_to_pay", mode="before")
    @classmethod
    def normalize_willingness(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        v_lower = v.lower().strip()
        if v_lower in ("high", "medium", "low"):
            return v_lower
        # LLM sometimes returns verbose strings like "Medium to High - ..."
        if "high" in v_lower:
            return "high"
        if "medium" in v_lower:
            return "medium"
        if "low" in v_lower:
            return "low"
        return v  # let Pydantic raise the validation error


class PainDiscoveryInput(BaseModel):
    idea: str
    retry_queries: list[str] | None = None
    previous_result: PainDiscoveryOutput | None = None


class PainDiscoveryOutput(BaseModel):
    idea: str
    pain_points: list[PainPoint]
    user_segments: list[UserSegment]
    primary_target_user: UserSegment
    pain_summary: str
    search_queries_used: list[str]
    data_quality: str = "full"  # "full" or "partial"


# ──────────────────────────────────────────────
# Agent 2: Competitor Research
# ──────────────────────────────────────────────

class CompetitorPricing(BaseModel):
    plan_name: str
    price: str  # "$29/mo", "Free", "Custom"
    features: list[str]


class Competitor(BaseModel):
    name: str
    url: str
    one_liner: str
    pricing: list[CompetitorPricing]
    strengths: list[str]
    weaknesses: list[str]
    review_sentiment: Literal["positive", "mixed", "negative"]
    review_count: int | None = None
    source: str  # "google", "g2", "capterra"

    @field_validator("review_sentiment", mode="before")
    @classmethod
    def normalize_sentiment(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        v_lower = v.lower().strip()
        if v_lower in ("positive", "mixed", "negative"):
            return v_lower
        if "positive" in v_lower:
            return "positive"
        if "negative" in v_lower:
            return "negative"
        return "mixed"


class CompetitorResearchInput(BaseModel):
    idea: str
    target_user: UserSegment | None = None
    retry_queries: list[str] | None = None
    previous_result: CompetitorResearchOutput | None = None


class CompetitorResearchOutput(BaseModel):
    target_user: UserSegment
    competitors: list[Competitor]
    market_saturation: Literal["low", "medium", "high"]
    avg_price_point: str
    common_complaints: list[str]
    underserved_needs: list[str]
    data_quality: str = "full"

    @field_validator("market_saturation", mode="before")
    @classmethod
    def normalize_saturation(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        v_lower = v.lower().strip()
        if v_lower in ("low", "medium", "high"):
            return v_lower
        if "high" in v_lower:
            return "high"
        if "medium" in v_lower:
            return "medium"
        if "low" in v_lower:
            return "low"
        return v


# ──────────────────────────────────────────────
# Agent 3: Viability Analysis
# ──────────────────────────────────────────────

class ViabilitySignal(BaseModel):
    signal: str
    direction: Literal["positive", "negative", "neutral"]
    confidence: float = Field(ge=0.0, le=1.0)
    source: str

    @field_validator("direction", mode="before")
    @classmethod
    def normalize_direction(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        v_lower = v.lower().strip()
        if v_lower in ("positive", "negative", "neutral"):
            return v_lower
        if "positive" in v_lower:
            return "positive"
        if "negative" in v_lower:
            return "negative"
        return "neutral"


class ViabilityInput(BaseModel):
    idea: str
    pain_discovery: PainDiscoveryOutput
    competitor_research: CompetitorResearchOutput


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
    def normalize_reachability(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        v_lower = v.lower().strip()
        if v_lower in ("easy", "moderate", "hard"):
            return v_lower
        if "easy" in v_lower:
            return "easy"
        if "hard" in v_lower:
            return "hard"
        return "moderate"

    @field_validator("gap_size", mode="before")
    @classmethod
    def normalize_gap_size(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        v_lower = v.lower().strip()
        if v_lower in ("large", "medium", "small", "none"):
            return v_lower
        if "large" in v_lower:
            return "large"
        if "small" in v_lower:
            return "small"
        if "none" in v_lower:
            return "none"
        return "medium"


# ──────────────────────────────────────────────
# Agent 4: Synthesis & Verdict
# ──────────────────────────────────────────────

class Verdict(str, Enum):
    BUILD = "BUILD"
    SKIP = "SKIP"
    MAYBE = "MAYBE"


class SynthesisInput(BaseModel):
    idea: str
    pain_discovery: PainDiscoveryOutput
    competitor_research: CompetitorResearchOutput
    viability: ViabilityOutput


class SynthesisOutput(BaseModel):
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("verdict", mode="before")
    @classmethod
    def normalize_verdict(cls, v: str) -> str:
        if isinstance(v, str) and v.upper().strip() == "CONDITIONAL":
            return "MAYBE"
        return v
    one_line_summary: str
    reasoning: str
    key_strengths: list[str]
    key_risks: list[str]
    recommended_mvp: str | None = None
    recommended_positioning: str | None = None
    target_user_summary: str
    estimated_market_size: str
    next_steps: list[str]


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
    viability: ViabilityOutput | None = None
    synthesis: SynthesisOutput | None = None
    error: str | None = None
    total_cost_cents: int = 0
    user_id: str | None = None


# ──────────────────────────────────────────────
# API Models
# ──────────────────────────────────────────────

class CreateValidationRequest(BaseModel):
    idea: str = Field(min_length=10, max_length=500)

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
