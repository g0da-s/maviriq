from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


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
    willingness_to_pay: str  # "high", "medium", "low"


class PainDiscoveryInput(BaseModel):
    idea: str


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
    review_sentiment: str  # "positive", "mixed", "negative"
    review_count: int | None = None
    source: str  # "google", "g2", "capterra"


class CompetitorResearchInput(BaseModel):
    idea: str
    target_user: UserSegment


class CompetitorResearchOutput(BaseModel):
    target_user: UserSegment
    competitors: list[Competitor]
    market_saturation: str  # "low", "medium", "high"
    avg_price_point: str
    common_complaints: list[str]
    underserved_needs: list[str]
    data_quality: str = "full"


# ──────────────────────────────────────────────
# Agent 3: Viability Analysis
# ──────────────────────────────────────────────

class ViabilitySignal(BaseModel):
    signal: str
    direction: str  # "positive", "negative", "neutral"
    confidence: float = Field(ge=0.0, le=1.0)
    source: str


class ViabilityInput(BaseModel):
    idea: str
    pain_discovery: PainDiscoveryOutput
    competitor_research: CompetitorResearchOutput


class ViabilityOutput(BaseModel):
    people_pay: bool
    people_pay_reasoning: str
    reachability: str  # "easy", "moderate", "hard"
    reachability_reasoning: str
    market_gap: str
    gap_size: str  # "large", "medium", "small", "none"
    signals: list[ViabilitySignal]
    risk_factors: list[str]
    opportunity_score: float = Field(ge=0.0, le=1.0)


# ──────────────────────────────────────────────
# Agent 4: Synthesis & Verdict
# ──────────────────────────────────────────────

class Verdict(str, Enum):
    BUILD = "BUILD"
    SKIP = "SKIP"
    CONDITIONAL = "CONDITIONAL"


class SynthesisInput(BaseModel):
    idea: str
    pain_discovery: PainDiscoveryOutput
    competitor_research: CompetitorResearchOutput
    viability: ViabilityOutput


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


# ──────────────────────────────────────────────
# API Models
# ──────────────────────────────────────────────

class CreateValidationRequest(BaseModel):
    idea: str = Field(min_length=3, max_length=500)


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
