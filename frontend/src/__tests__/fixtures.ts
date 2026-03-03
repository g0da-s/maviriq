import type {
  ValidationRun,
  ValidationListResponse,
  ContextResearchOutput,
  PainDiscoveryOutput,
  CompetitorResearchOutput,
  MarketIntelligenceOutput,
  GraveyardResearchOutput,
  ViabilityOutput,
  SynthesisOutput,
} from "@/lib/types";

export const mockContextResearch: ContextResearchOutput = {
  idea_analysis: "AI meeting scheduler targets a common pain in tech teams.",
  current_landscape: "Several general-purpose schedulers exist but none AI-first.",
  key_players: "Calendly, SavvyCal, Cal.com, Reclaim.ai",
  recent_developments: "AI scheduling is a growing trend.",
  search_queries_used: ["AI meeting scheduler market", "meeting scheduling tools"],
};

export const mockPainDiscovery: PainDiscoveryOutput = {
  idea: "AI meeting scheduler",
  pain_points: [
    {
      source: "Reddit",
      source_url: "https://reddit.com/r/test",
      quote: "Scheduling meetings is a nightmare",
      author_context: "Engineering manager",
      pain_severity: "high",
      date: "2024-01-15",
    },
    {
      source: "Hacker News",
      source_url: "https://news.ycombinator.com",
      quote: "I spend 2 hours a week just scheduling",
      author_context: "Startup founder",
      pain_severity: "moderate",
      date: "2024-02-01",
    },
  ],
  user_segments: [
    {
      label: "Engineering Managers",
      description: "Mid-level managers at tech companies",
      frequency: 85,
      willingness_to_pay: "high",
    },
    {
      label: "Startup Founders",
      description: "Early-stage founders wearing many hats",
      frequency: 60,
      willingness_to_pay: "medium",
    },
  ],
  primary_target_user: {
    label: "Engineering Managers",
    description: "Mid-level managers at tech companies",
    frequency: 85,
    willingness_to_pay: "high",
  },
  pain_summary: "Meeting scheduling is a significant pain point for tech professionals.",
  search_queries_used: ["meeting scheduling pain", "calendar management frustration"],
};

export const mockCompetitorResearch: CompetitorResearchOutput = {
  target_user: {
    label: "Engineering Managers",
    description: "Mid-level managers at tech companies",
    frequency: 85,
    willingness_to_pay: "high",
  },
  competitors: [
    {
      name: "Calendly",
      url: "https://calendly.com",
      one_liner: "Simple scheduling ahead",
      pricing: [
        { plan_name: "Free", price: "$0/mo", features: ["Basic scheduling"] },
        { plan_name: "Pro", price: "$10/mo", features: ["Advanced features"] },
      ],
      strengths: ["Easy to use", "Well-known brand"],
      weaknesses: ["Limited AI features", "No team coordination"],
      review_sentiment: "positive",
      review_count: 450,
      source: "G2",
    },
  ],
  market_saturation: "high",
  avg_price_point: "$12/mo",
  common_complaints: ["Too expensive", "Poor integration"],
  underserved_needs: ["AI-powered scheduling", "Team coordination"],
};

export const mockMarketIntelligence: MarketIntelligenceOutput = {
  market_size_estimate: "$2.5B",
  growth_direction: "growing",
  growth_evidence: "Increasing adoption of AI tools in enterprise.",
  tam_reasoning: "Based on enterprise scheduling tool spend.",
  distribution_channels: [
    { channel: "Product Hunt", reach_estimate: "50k", effort: "low" },
  ],
  funding_signals: [{ description: "Reclaim.ai raised $10M Series A", source_url: null }],
  search_queries_used: ["meeting scheduling market size"],
};

export const mockGraveyardResearch: GraveyardResearchOutput = {
  previous_attempts: [
    {
      name: "Clara Labs",
      url: "https://claralabs.com",
      what_they_did: "AI scheduling assistant via email",
      shutdown_reason: "Burned through funding, couldn't scale human-in-the-loop",
      year: "2021",
      source: "TechCrunch",
    },
  ],
  failure_reasons: [],
  lessons_learned: "",
  churn_signals: [],
  search_queries_used: ["failed AI scheduling startups"],
};

export const mockViability: ViabilityOutput = {
  people_pay: true,
  people_pay_reasoning: "Strong willingness to pay observed across multiple segments",
  reachability: "moderate",
  reachability_reasoning: "Can reach through tech communities and LinkedIn",
  market_gap: "No AI-first scheduler exists for engineering teams",
  gap_size: "medium",
  signals: [
    {
      signal: "Growing demand for AI tools",
      direction: "positive",
      confidence: 0.85,
      source: "Market research",
    },
    {
      signal: "Enterprise budgets tightening",
      direction: "negative",
      confidence: 0.6,
      source: "Industry reports",
    },
  ],
  risk_factors: ["Competitive market", "Enterprise sales cycle"],
  opportunity_score: 0.72,
};

export const mockSynthesis: SynthesisOutput = {
  verdict: "BUILD",
  confidence: 0.78,
  one_line_summary: "Strong pain point with viable market gap despite competition",
  reasoning: "The data shows clear pain in meeting scheduling for engineering teams.",
  key_strengths: ["Strong user pain", "Viable market gap"],
  key_risks: ["Competitive market", "Enterprise sales cycle"],
  recommended_mvp: "AI scheduling assistant for engineering standups",
  recommended_positioning: "The AI-first scheduler built for engineering teams",
  target_user_summary: "Engineering managers at mid-size tech companies",
  estimated_market_size: "$2.5B",
  next_steps: ["Build MVP", "Get 10 beta users", "Validate pricing"],
  people_pay: true,
  people_pay_reasoning: "Strong willingness to pay observed across multiple segments",
  reachability: "moderate",
  reachability_reasoning: "Can reach through tech communities and LinkedIn",
  market_gap: "No AI-first scheduler exists for engineering teams",
  gap_size: "medium",
  signals: [
    {
      signal: "Growing demand for AI tools",
      direction: "positive",
      confidence: 0.85,
      source: "Market research",
    },
  ],
};

export const mockCompletedRun: ValidationRun = {
  id: "run-123",
  idea: "AI meeting scheduler for engineering teams",
  status: "completed",
  current_agent: 5,
  started_at: "2024-01-15T10:00:00Z",
  completed_at: "2024-01-15T10:05:00Z",
  context_research: mockContextResearch,
  pain_discovery: mockPainDiscovery,
  competitor_research: mockCompetitorResearch,
  market_intelligence: mockMarketIntelligence,
  graveyard_research: mockGraveyardResearch,
  viability: mockViability,
  synthesis: mockSynthesis,
  error: null,
  total_cost_cents: 150,
  user_id: "u1",
  language: "en",
  target_market: null,
};

export const mockRunningRun: ValidationRun = {
  id: "run-456",
  idea: "AI meeting scheduler for engineering teams",
  status: "running",
  current_agent: 0,
  started_at: "2024-01-15T10:00:00Z",
  completed_at: null,
  context_research: null,
  pain_discovery: null,
  competitor_research: null,
  market_intelligence: null,
  graveyard_research: null,
  viability: null,
  synthesis: null,
  error: null,
  total_cost_cents: 0,
  user_id: "u1",
  language: "en",
  target_market: null,
};

export const mockFailedRun: ValidationRun = {
  id: "run-789",
  idea: "AI meeting scheduler for engineering teams",
  status: "failed",
  current_agent: 2,
  started_at: "2024-01-15T10:00:00Z",
  completed_at: null,
  context_research: mockContextResearch,
  pain_discovery: mockPainDiscovery,
  competitor_research: null,
  market_intelligence: null,
  graveyard_research: null,
  viability: null,
  synthesis: null,
  error: "Pipeline failed at competitor research",
  total_cost_cents: 50,
  user_id: "u1",
  language: "en",
  target_market: null,
};

/** A running run with agent 0 and 1 already completed — simulates mid-pipeline reconnect. */
export const mockMidPipelineRun: ValidationRun = {
  id: "run-mid",
  idea: "AI meeting scheduler for engineering teams",
  status: "running",
  current_agent: 2,
  started_at: "2024-01-15T10:00:00Z",
  completed_at: null,
  context_research: mockContextResearch,
  pain_discovery: mockPainDiscovery,
  competitor_research: null,
  market_intelligence: null,
  graveyard_research: null,
  viability: null,
  synthesis: null,
  error: null,
  total_cost_cents: 30,
  user_id: "u1",
  language: "en",
  target_market: null,
};

export const mockValidationList: ValidationListResponse = {
  items: [
    {
      id: "run-1",
      idea: "AI meeting scheduler",
      status: "completed",
      verdict: "BUILD",
      confidence: 0.78,
      created_at: "2024-01-15T10:00:00Z",
    },
    {
      id: "run-2",
      idea: "Blockchain pet food tracker",
      status: "completed",
      verdict: "SKIP",
      confidence: 0.92,
      created_at: "2024-01-14T10:00:00Z",
    },
    {
      id: "run-3",
      idea: "Developer tool for code review",
      status: "completed",
      verdict: "MAYBE",
      confidence: 0.55,
      created_at: "2024-01-13T10:00:00Z",
    },
  ],
  total: 3,
  page: 1,
  per_page: 20,
};
