import { z } from "zod";

// ── Enums ──

const ValidationStatusSchema = z.enum(["pending", "running", "completed", "failed"]);
const VerdictSchema = z.enum(["BUILD", "SKIP", "MAYBE"]);
const WillingsToPaySchema = z.enum(["high", "medium", "low"]);
const MarketSaturationSchema = z.enum(["low", "medium", "high"]);
const GapSizeSchema = z.enum(["large", "medium", "small", "none"]);
const SignalDirectionSchema = z.enum(["positive", "negative", "neutral"]);
const ReachabilitySchema = z.enum(["easy", "moderate", "hard"]);
const ReviewSentimentSchema = z.enum(["positive", "mixed", "negative"]);

export type ValidationStatus = z.infer<typeof ValidationStatusSchema>;
export type Verdict = z.infer<typeof VerdictSchema>;
export type WillingnessToPay = z.infer<typeof WillingsToPaySchema>;
export type MarketSaturation = z.infer<typeof MarketSaturationSchema>;
export type GapSize = z.infer<typeof GapSizeSchema>;
export type SignalDirection = z.infer<typeof SignalDirectionSchema>;
export type Reachability = z.infer<typeof ReachabilitySchema>;
export type ReviewSentiment = z.infer<typeof ReviewSentimentSchema>;

// ── Pain Discovery ──

const PainPointSchema = z.object({
  source: z.string(),
  source_url: z.string(),
  quote: z.string(),
  author_context: z.string(),
  pain_severity: z.number(),
  date: z.string().nullable(),
});

const UserSegmentSchema = z.object({
  label: z.string(),
  description: z.string(),
  frequency: z.number(),
  willingness_to_pay: WillingsToPaySchema,
});

const PainDiscoveryOutputSchema = z.object({
  idea: z.string(),
  pain_points: z.array(PainPointSchema),
  user_segments: z.array(UserSegmentSchema),
  primary_target_user: UserSegmentSchema,
  pain_summary: z.string(),
  search_queries_used: z.array(z.string()),
});

export type PainPoint = z.infer<typeof PainPointSchema>;
export type UserSegment = z.infer<typeof UserSegmentSchema>;
export type PainDiscoveryOutput = z.infer<typeof PainDiscoveryOutputSchema>;

// ── Competitor Research ──

const CompetitorPricingSchema = z.object({
  plan_name: z.string(),
  price: z.string(),
  features: z.array(z.string()),
});

const CompetitorSchema = z.object({
  name: z.string(),
  url: z.string(),
  one_liner: z.string(),
  pricing: z.array(CompetitorPricingSchema),
  strengths: z.array(z.string()),
  weaknesses: z.array(z.string()),
  review_sentiment: ReviewSentimentSchema,
  review_count: z.number().nullable(),
  source: z.string(),
});

const CompetitorResearchOutputSchema = z.object({
  target_user: UserSegmentSchema,
  competitors: z.array(CompetitorSchema),
  market_saturation: MarketSaturationSchema,
  avg_price_point: z.string(),
  common_complaints: z.array(z.string()),
  underserved_needs: z.array(z.string()),
});

export type CompetitorPricing = z.infer<typeof CompetitorPricingSchema>;
export type Competitor = z.infer<typeof CompetitorSchema>;
export type CompetitorResearchOutput = z.infer<typeof CompetitorResearchOutputSchema>;

// ── Market Intelligence (NEW) ──

const EffortSchema = z.enum(["low", "medium", "high"]);
const GrowthDirectionSchema = z.enum(["growing", "stable", "shrinking", "unknown"]);
const ChurnSeveritySchema = z.enum(["high", "medium", "low"]);

const DistributionChannelSchema = z.object({
  channel: z.string(),
  reach_estimate: z.string(),
  effort: EffortSchema,
});

const MarketIntelligenceOutputSchema = z.object({
  market_size_estimate: z.string(),
  growth_direction: GrowthDirectionSchema,
  tam_reasoning: z.string(),
  distribution_channels: z.array(DistributionChannelSchema),
  funding_signals: z.array(z.string()).default([]),
  search_queries_used: z.array(z.string()),
});

export type DistributionChannel = z.infer<typeof DistributionChannelSchema>;
export type GrowthDirection = z.infer<typeof GrowthDirectionSchema>;
export type MarketIntelligenceOutput = z.infer<typeof MarketIntelligenceOutputSchema>;

// ── Graveyard Research (NEW) ──

const PreviousAttemptSchema = z.object({
  name: z.string(),
  url: z.string().nullable(),
  what_they_did: z.string(),
  shutdown_reason: z.string(),
  year: z.string().nullable(),
  source: z.string(),
});

const ChurnSignalSchema = z.object({
  signal: z.string(),
  source: z.string(),
  severity: ChurnSeveritySchema,
});

const GraveyardResearchOutputSchema = z.object({
  previous_attempts: z.array(PreviousAttemptSchema),
  failure_reasons: z.array(z.string()),
  lessons_learned: z.string(),
  churn_signals: z.array(ChurnSignalSchema),
  search_queries_used: z.array(z.string()),
});

export type PreviousAttempt = z.infer<typeof PreviousAttemptSchema>;
export type ChurnSignal = z.infer<typeof ChurnSignalSchema>;
export type GraveyardResearchOutput = z.infer<typeof GraveyardResearchOutputSchema>;

// ── Viability (kept for old runs) ──

const ViabilitySignalSchema = z.object({
  signal: z.string(),
  direction: SignalDirectionSchema,
  confidence: z.number(),
  source: z.string(),
});

const ViabilityOutputSchema = z.object({
  people_pay: z.boolean(),
  people_pay_reasoning: z.string(),
  reachability: ReachabilitySchema,
  reachability_reasoning: z.string(),
  market_gap: z.string(),
  gap_size: GapSizeSchema,
  signals: z.array(ViabilitySignalSchema),
  risk_factors: z.array(z.string()),
  opportunity_score: z.number(),
});

export type ViabilitySignal = z.infer<typeof ViabilitySignalSchema>;
export type ViabilityOutput = z.infer<typeof ViabilityOutputSchema>;

// ── Synthesis ──

const SynthesisOutputSchema = z.object({
  verdict: VerdictSchema,
  confidence: z.number(),
  one_line_summary: z.string(),
  reasoning: z.string(),
  key_strengths: z.array(z.string()),
  key_risks: z.array(z.string()),
  recommended_mvp: z.string().nullable(),
  recommended_positioning: z.string().nullable(),
  target_user_summary: z.string(),
  estimated_market_size: z.string(),
  next_steps: z.array(z.string()),
  // Absorbed from old Viability agent
  people_pay: z.boolean(),
  people_pay_reasoning: z.string(),
  reachability: ReachabilitySchema,
  reachability_reasoning: z.string(),
  market_gap: z.string(),
  gap_size: GapSizeSchema,
  signals: z.array(ViabilitySignalSchema),
  // New fields from new agents
  differentiation_strategy: z.string().nullable().optional(),
  previous_attempts_summary: z.string().nullable().optional(),
  lessons_from_failures: z.string().nullable().optional(),
});

export type SynthesisOutput = z.infer<typeof SynthesisOutputSchema>;

// ── API Responses ──

export const ValidationRunSchema = z.object({
  id: z.string(),
  idea: z.string(),
  status: ValidationStatusSchema,
  current_agent: z.number(),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  pain_discovery: PainDiscoveryOutputSchema.nullable(),
  competitor_research: CompetitorResearchOutputSchema.nullable(),
  market_intelligence: MarketIntelligenceOutputSchema.nullable(),
  graveyard_research: GraveyardResearchOutputSchema.nullable(),
  viability: ViabilityOutputSchema.nullable(),  // kept for old runs
  synthesis: SynthesisOutputSchema.nullable(),
  error: z.string().nullable(),
  total_cost_cents: z.number(),
  user_id: z.string().nullable().optional(),
});

export const CreateValidationResponseSchema = z.object({
  id: z.string(),
  idea: z.string(),
  status: ValidationStatusSchema,
  stream_url: z.string(),
});

export const ValidationListItemSchema = z.object({
  id: z.string(),
  idea: z.string(),
  status: ValidationStatusSchema,
  verdict: VerdictSchema.nullable(),
  confidence: z.number().nullable(),
  created_at: z.string().nullable(),
});

export const ValidationListResponseSchema = z.object({
  items: z.array(ValidationListItemSchema),
  total: z.number(),
  page: z.number(),
  per_page: z.number(),
});

export type ValidationRun = z.infer<typeof ValidationRunSchema>;
export type CreateValidationResponse = z.infer<typeof CreateValidationResponseSchema>;
export type ValidationListItem = z.infer<typeof ValidationListItemSchema>;
export type ValidationListResponse = z.infer<typeof ValidationListResponseSchema>;

// ── Auth ──

export const UserResponseSchema = z.object({
  id: z.string(),
  email: z.string(),
  credits: z.number(),
  created_at: z.string(),
});

export const CheckoutResponseSchema = z.object({
  checkout_url: z.string(),
});

export type UserResponse = z.infer<typeof UserResponseSchema>;
export type CheckoutResponse = z.infer<typeof CheckoutResponseSchema>;

// ── SSE Events ──

export interface AgentCompletedEvent {
  agent: number;
  name: string;
  output: Record<string, unknown>;
}

export interface PipelineCompletedEvent {
  id: string;
  verdict: Verdict;
  confidence: number;
}

export interface PipelineErrorEvent {
  error: string;
}
