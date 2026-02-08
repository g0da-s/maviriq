export type ValidationStatus = "pending" | "running" | "completed" | "failed";
export type Verdict = "BUILD" | "SKIP" | "MAYBE";
export type WillingnessToPay = "high" | "medium" | "low";
export type MarketSaturation = "low" | "medium" | "high";
export type GapSize = "large" | "medium" | "small" | "none";
export type SignalDirection = "positive" | "negative" | "neutral";
export type Reachability = "easy" | "moderate" | "hard";
export type ReviewSentiment = "positive" | "mixed" | "negative";

export interface PainPoint {
  source: string;
  source_url: string;
  quote: string;
  author_context: string;
  pain_severity: number;
  date: string | null;
}

export interface UserSegment {
  label: string;
  description: string;
  frequency: number;
  willingness_to_pay: WillingnessToPay;
}

export interface PainDiscoveryOutput {
  idea: string;
  pain_points: PainPoint[];
  user_segments: UserSegment[];
  primary_target_user: UserSegment;
  pain_summary: string;
  search_queries_used: string[];
  data_quality: "full" | "partial";
}

export interface CompetitorPricing {
  plan_name: string;
  price: string;
  features: string[];
}

export interface Competitor {
  name: string;
  url: string;
  one_liner: string;
  pricing: CompetitorPricing[];
  strengths: string[];
  weaknesses: string[];
  review_sentiment: ReviewSentiment;
  review_count: number;
  source: string;
}

export interface CompetitorResearchOutput {
  target_user: UserSegment;
  competitors: Competitor[];
  market_saturation: MarketSaturation;
  avg_price_point: string;
  common_complaints: string[];
  underserved_needs: string[];
  data_quality: "full" | "partial";
}

export interface ViabilitySignal {
  signal: string;
  direction: SignalDirection;
  confidence: number;
  source: string;
}

export interface ViabilityOutput {
  people_pay: boolean;
  people_pay_reasoning: string;
  reachability: Reachability;
  reachability_reasoning: string;
  market_gap: string;
  gap_size: GapSize;
  signals: ViabilitySignal[];
  risk_factors: string[];
  opportunity_score: number;
}

export interface SynthesisOutput {
  verdict: Verdict;
  confidence: number;
  one_line_summary: string;
  reasoning: string;
  key_strengths: string[];
  key_risks: string[];
  recommended_mvp: string | null;
  recommended_positioning: string | null;
  target_user_summary: string;
  estimated_market_size: string;
  next_steps: string[];
}

export interface ValidationRun {
  id: string;
  idea: string;
  status: ValidationStatus;
  current_agent: number;
  started_at: string | null;
  completed_at: string | null;
  pain_discovery: PainDiscoveryOutput | null;
  competitor_research: CompetitorResearchOutput | null;
  viability: ViabilityOutput | null;
  synthesis: SynthesisOutput | null;
  error: string | null;
  total_cost_cents: number;
}

export interface CreateValidationResponse {
  id: string;
  idea: string;
  status: ValidationStatus;
  stream_url: string;
}

export interface ValidationListItem {
  id: string;
  idea: string;
  status: ValidationStatus;
  verdict: Verdict | null;
  confidence: number | null;
  created_at: string | null;
}

export interface ValidationListResponse {
  items: ValidationListItem[];
  total: number;
  page: number;
  per_page: number;
}

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
