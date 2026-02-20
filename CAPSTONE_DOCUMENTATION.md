# Capstone Documentation — Case 2: AI Agent for Task Automation

> Use this file to document everything needed for your capstone submission.

---

## 1. Agent Design

**Purpose**: Maviriq is an AI-powered startup idea validator. Given a business idea, it autonomously runs a multi-agent pipeline that researches real pain points, analyzes competitors, assesses market intelligence, investigates failed startups, and synthesizes a final verdict — automating hours of manual market research into minutes.

**Capabilities**:
- Autonomous web research across multiple specialized domains
- Multi-step reasoning across 5 specialized agents
- Structured output generation (scores, verdicts, competitor maps, viability signals)
- Real-time progress streaming to the user via SSE
- Agentic tool-use loops (each agent decides what to search and when to stop)

**Architecture**:
- 5 agents orchestrated via LangGraph (fan-out/fan-in pattern)
  - Agent 1: Pain & User Discovery — finds real complaints and identifies who suffers
  - Agent 2: Competitor Research — maps the competitive landscape, pricing, and gaps
  - Agent 3: Market Intelligence — estimates TAM, distribution channels, and funding activity
  - Agent 4: Graveyard Research — finds failed startups and churn signals
  - Agent 5: Synthesis & Verdict — combines all research into a BUILD/SKIP/MAYBE verdict
- Agents 1-4 run in parallel (fan-out), then fan-in to Agent 5 (Synthesis)
- Each agent runs an autonomous tool-use loop: the LLM decides which searches to run, analyzes results, and calls more tools until it has enough data

**Agent Ownership Boundaries** (each agent has a clear lane):

| Agent | Owns | Does NOT own |
|-------|------|--------------|
| Pain Discovery | Real complaints, pain severity, user segments, willingness to pay | Pricing data, market size |
| Competitor Research | Competitor names, pricing, strengths/weaknesses, market saturation | Market size estimates, failed startups |
| Market Intelligence | TAM/market size, growth direction, distribution channels, funding signals | Competitor pricing, monetization |
| Graveyard Research | Failed startups, failure reasons, churn signals, competitor health | Active competitor analysis |
| Synthesis | Final verdict, confidence, viability assessment, recommendations | No search tools — reasoning only |

---

## 2. Tool Integration

**LLM**: Anthropic Claude (via custom `LLMService` wrapper)
- Structured output via Anthropic's native tool_use with Pydantic schema enforcement
- Sonnet model for agent reasoning (tool-use loops + synthesis)
- Haiku model for eval grading (cheap, fast quality judgments)

**Search**: Serper API (Google Search API) with site-specific methods:
- `search_web` — general Google search
- `search_reddit` — site:reddit.com queries for genuine user complaints
- `search_hackernews` — site:news.ycombinator.com for tech community discussions
- `search_twitter` — site:twitter.com (unreliable, used with guidance to try once)
- `search_news` — Google News for industry coverage
- `search_g2` — site:g2.com for software reviews
- `search_capterra` — site:capterra.com for software reviews
- `search_producthunt` — site:producthunt.com for product launches
- `search_indiehackers` — site:indiehackers.com for founder stories and revenue reports
- `search_crunchbase` — site:crunchbase.com for funding data

**Database**: Supabase (PostgreSQL)
- Stores validation runs, user accounts, credit transactions
- RPC functions for atomic credit deduction

**Payments**: Stripe Checkout
- Credit pack purchases with webhook verification

**Auth**: Supabase Auth (email/password + Google OAuth)
- JWT verification via JWKS endpoint
- Google OAuth via Supabase `signInWithOAuth`
- Password reset via Supabase email recovery flow

**Analytics**: PostHog
- Event tracking: signups, logins (email + Google), purchases, checkout starts
- User identification after authentication

**Observability**: LangSmith
- Full tracing of agent runs, LLM calls, and tool usage

---

## 3. Agent Execution — Advanced Features

**Agentic Tool-Use Loops**:
- Each research agent (1-4) runs an autonomous loop: the LLM receives a system prompt and tools, decides what to search, processes results, and calls more tools until satisfied
- The agent calls `submit_result` with structured Pydantic output when done
- This is NOT simple chain-of-thought — the agent makes real decisions about what to search next based on what it finds

**Multi-step reasoning**:
- Pain Discovery searches for problems (not solutions), using multiple query phrasings across Reddit, HackerNews, Twitter, and Google News
- Competitor Research maps the full landscape using G2, Capterra, Product Hunt, Indie Hackers, and Crunchbase
- Market Intelligence estimates TAM by narrowing broad market numbers to the specific niche (with explicit instructions to show the narrowing math)
- Graveyard Research finds failed startups and extracts lessons learned
- Synthesis reasons across ALL agent outputs to produce a final verdict with calibrated confidence

**Orchestration (LangGraph)**:
- StateGraph with fan-out parallelism (Agents 1-4 run simultaneously)
- Fan-in synchronization (Agent 5 waits for all four)
- Stream mode for real-time SSE event publishing (user sees progress per agent)

**Prompt Engineering Techniques Applied**:
- Evidence-driven assessment: "Be evidence-driven, not pessimistic or optimistic. Let the data speak." (replaced earlier "Bias toward skepticism" after eval showed systematic pessimism — see Phase 6)
- Confidence calibration: explicit scale (0.85+ = overwhelming evidence, 0.25-0.44 = weak case) with few-shot anchor examples to prevent clustering around 0.30-0.35
- Few-shot severity calibration: 5 diverse `<example>` tags in Pain Discovery showing mild/moderate/high ratings to prevent central tendency bias (see Phase 6)
- Market saturation threshold criteria: explicit competitor-count and revenue thresholds to eliminate subjective saturation ratings (see Phase 6)
- Dynamic date injection: Pain Discovery prompt uses `{current_year}` and `{previous_year}` to ensure recency (not hardcoded dates)
- Twitter reliability guidance: "try it once but if it returns no results, move on. Do not retry."
- TAM narrowing: "Search results will give you BROAD market numbers. Always narrow down: the broad market is $XB, but this idea targets [specific niche], which is roughly X% = $Y."
- Anti-fabrication: "Do NOT fabricate quotes, URLs, or statistics. Only report what you find in search results."
- Thin evidence handling: "If the idea addresses no real problem, it is OK to find few or zero pain points. Do NOT stretch weak signals."

**Input validation (3-layer)**:
- Layer 1: Frontend regex (profanity + gibberish detection)
- Layer 2: Backend Pydantic validator (same checks server-side)
- Layer 3: LLM coherence check (cheap model, before credit deduction)

**Error handling**:
- Generic error messages to clients (no internal details leaked)
- Detailed logging server-side for debugging
- Pydantic field validators normalize LLM output (e.g., "Medium to High" → "medium")

---

## 4. Interactive Prototyping

**Frontend**: Next.js 16 + React 19 + Tailwind CSS 4
- Real-time pipeline progress via Server-Sent Events (SSE)
- Step-by-step agent progress indicator
- Results page with structured sections:
  - Pain points with quotes, sources, and severity scores
  - Competitor map with pricing, strengths, weaknesses
  - Market intelligence with TAM, growth direction, distribution channels, funding signals
  - Graveyard research with failed startups and lessons learned
  - Viability dashboard (opportunity signals, risk factors, reachability, market gap)
  - Final verdict (BUILD/SKIP/MAYBE) with confidence, reasoning, and next steps
- Auth flow (signup, login, Google OAuth, password reset, credit purchase)

**Backend**: FastAPI
- REST endpoints for validation CRUD, auth (`GET /me`), credits
- SSE streaming endpoint for real-time progress with single-use stream tokens
- Stripe webhook endpoint for payment processing
- Public stats endpoint (`GET /api/stats`)

**Deployment**: [TODO: Note where you deployed — e.g., Vercel + Railway, or local demo]

---

## 5. Evaluation

### Eval Framework Architecture

Built a comprehensive evaluation system with 25 golden test cases and automated grading.

**Golden Test Cases** (25 cases across 5 categories):

| Category | Count | Expected Verdict | Purpose |
|----------|-------|-----------------|---------|
| `obviously_bad` | 5 | SKIP | Ideas with no real pain (e.g., "social network for pets") |
| `saturated` | 5 | SKIP or MAYBE | Crowded markets (e.g., "another todo app") |
| `niche_viable` | 5 | MAYBE or BUILD | Underserved niches with real pain |
| `obviously_good` | 5 | BUILD or MAYBE | Strong pain signals and viable market |
| `already_failed` | 5 | SKIP | Ideas where startups have already failed |

Each case specifies: expected verdict, minimum pain points, minimum competitors, known competitor names (substring match), expected market saturation, confidence range window.

**Three Types of Graders**:

1. **Code Graders** (21 deterministic checks, no API calls):
   - Pain Discovery: minimum pain point count, source diversity, severity range, primary target user quality
   - Competitor Research: minimum competitor count, known competitor detection, saturation match
   - Market Intelligence: TAM present, distribution channels found, growth direction valid
   - Graveyard Research: failure reasons found, previous attempts found
   - Synthesis: verdict matches expected, confidence in expected range, MVP present for BUILD, key risks present for SKIP, reasoning length adequate

2. **Model Graders** (6 LLM-as-judge checks using Haiku):
   - Pain groundedness: are pain points backed by real evidence?
   - Target user quality: is the primary user well-defined?
   - Competitor relevance: are competitors actually relevant to the idea?
   - TAM quality: is the market size estimate reasonable and narrowed?
   - Reasoning quality: does the synthesis reasoning cite the data?
   - Skepticism calibration: is the verdict appropriately skeptical?

3. **Consistency Graders** (2 checks, for multi-trial runs):
   - Verdict consistency: do all k trials produce the same verdict? (Pass^k metric)
   - Confidence consistency: is the spread across trials ≤ 0.25?

**Running Evals**:
```bash
# Full suite (25 cases, real API calls):
export ANTHROPIC_API_KEY="..."
export SERPER_API_KEY="..."
.venv/bin/python -m pytest tests/evals/test_eval_pipeline.py::TestEvalSuite -v

# Single case:
.venv/bin/python -m pytest tests/evals/ -v --eval-case=ai-pitch-deck-generator

# Category only:
.venv/bin/python -m pytest tests/evals/ -v --category=obviously_bad

# Skip model graders (faster, cheaper):
.venv/bin/python -m pytest tests/evals/ -v --skip-model

# Multi-trial consistency check:
.venv/bin/python -m pytest tests/evals/ -v --trials=3
```

**Unit Tests**: 91 tests (all mocked, no API calls) covering schemas, agents, API endpoints, and frontend components.

### Known Limitations

- **Search API dependency**: All research quality depends on Serper/Google search results. If search returns poor results, agent output will be poor.
- **LLM non-determinism**: Same idea can produce different verdicts across runs. Consistency graders measure this.
- **Twitter search unreliable**: Serper's Twitter search often returns no results. Agent is instructed to try once and move on.
- **Western market bias**: Search results and LLM training data skew toward English-speaking/Western markets.
- **TAM estimation is approximate**: Market size comes from search snippets, not financial databases. The prompt instructs narrowing but the numbers are rough.

---

## 6. Documentation & Ethical Considerations

### Ethical Considerations

**Data Privacy**:
- User ideas are stored in a database — users should be informed
- No idea data is shared with third parties beyond the LLM provider (Anthropic) and search API (Serper)
- JWT-based auth ensures users only access their own data

**Bias & Fairness**:
- LLM outputs may reflect training data biases (e.g., favoring Western markets)
- Search results are limited to what Google indexes — underrepresented markets may get poorer analysis
- The "verdict" is an AI opinion, not financial advice — this should be clearly disclaimed

**Transparency**:
- Users see which agent is running and its progress in real-time
- Results are structured and sourced (search queries used are visible)
- Pain points include direct quotes with source URLs

**Cost & Access**:
- Credit system gates access — free tier (1 credit) allows trial
- Input validation prevents wasting credits on gibberish

### Technical Decisions Log

| Decision | Rationale |
|----------|-----------|
| Anthropic Claude over OpenAI | Better structured output, less hallucination in analysis tasks |
| LangGraph over raw asyncio | Built-in state management, conditional routing, stream support |
| Supabase over raw PostgreSQL | Auth, RPC, real-time features out of the box |
| SSE over WebSockets | Simpler for unidirectional server-to-client streaming |
| Credit system over subscription | Lower barrier to entry, pay-per-use model |
| 5 agents (expanded from 4) | Added Market Intelligence and Graveyard Research for deeper analysis; removed separate Viability agent (absorbed into Synthesis) |
| Fan-out parallelism for agents 1-4 | Agents are independent — running them in parallel cuts pipeline time by ~70% |
| Funding signals instead of monetization signals | Monetization signals overlapped with Competitor Research pricing data. Funding signals (VC activity, acquisitions) are unique to Market Intelligence |
| Removed `data_quality` field | LLM defaulted to "full" regardless — actual data counts (pain point count, competitor count) are more reliable quality indicators |
| Removed redundant Synthesis fields | `key_risks` already captures risks (removed `risk_factors`); `confidence` already captures assessment (removed `opportunity_score`). Redundant fields caused inconsistencies |
| Added Indie Hackers search | Indie Hackers posts about revenue reveal actual competitors; founder stories provide competitive intelligence |
| Dynamic date injection in prompts | Hardcoded years go stale. `{current_year}` / `{previous_year}` are injected at runtime via `datetime.now()` |
| Twitter search kept with guidance | Serper's Twitter search is unreliable but occasionally useful. Prompt says "try once, don't retry" instead of removing it |

---

## 7. Iteration Log — Agent Improvements

This section documents the systematic agent improvements made during development.

### Phase 1: Architecture Expansion (4 agents to 5 agents)

**Before**: 4 agents — Pain Discovery, Competitor Research, Viability Analysis, Synthesis
**After**: 5 agents — Pain Discovery, Competitor Research, Market Intelligence, Graveyard Research, Synthesis

- **Added Market Intelligence agent**: Handles TAM estimation, growth direction, distribution channels, and funding signals. Previously this was either missing or crammed into Viability.
- **Added Graveyard Research agent**: Searches for failed startups, churn signals, and competitor health. Gives Synthesis critical "why did this fail before?" context.
- **Removed standalone Viability agent**: Its responsibilities were split — viability assessment absorbed into Synthesis, market data moved to Market Intelligence.
- **Changed orchestration**: From sequential (1→2→3→4) to parallel fan-out (1,2,3,4 run simultaneously → 5 synthesizes).

### Phase 2: Ownership Boundary Cleanup

**Problem**: Agents overlapped — Market Intelligence was finding "monetization signals" that were really just competitor pricing data (Competitor Research's job).

**Fix**: Removed `monetization_signals` from Market Intelligence entirely. Replaced with `funding_signals: list[str]` — evidence of VC activity, acquisitions, and investment trends. Added explicit prompt note: "You do NOT need to assess monetization or pricing — the Competitor Research agent handles that separately."

**Problem**: Market Intelligence was using `search_reddit` which found user complaints (Pain Discovery's job).

**Fix**: Removed `search_reddit` from Market Intelligence tool list. It now uses: `search_web`, `search_news`, `search_producthunt`, `search_crunchbase`.

### Phase 3: TAM Fabrication Prevention

**Problem**: Market Intelligence would find broad market numbers (e.g., "$50B project management market") and report them as the TAM for a niche idea.

**Fix**: Added TAM narrowing instructions to the prompt:
> "Search results will give you BROAD market numbers. That is NOT the TAM for the founder's specific idea. Always narrow down: the broad [category] market is $XB, but this idea targets [specific niche], which is roughly X% of that = $Y."

### Phase 4: Prompt Reliability Improvements

1. **Dynamic recency dates**: Pain Discovery's prompt now uses `{current_year}` and `{previous_year}` (injected at runtime via `datetime.now()`) instead of hardcoded years.

2. **Twitter search guidance**: Added explicit step: "Search Twitter/X for complaints and rants. Note: Twitter search is unreliable — try it once but if it returns no results, move on. Do not retry."

3. **Removed unreliable `data_quality` field**: All 4 research agents had a `data_quality: str = "full"` field. The LLM almost always defaulted to "full" even with sparse data. Removed from all schemas and prompts — actual data counts are more reliable.

4. **Removed redundant Synthesis fields**:
   - `risk_factors: list[str]` — duplicate of `key_risks: list[str]`
   - `opportunity_score: float` — duplicate of `confidence: float`
   - These caused inconsistencies (risk_factors might say "no risks" while key_risks listed 3 items)

5. **Added Indie Hackers search**: Added `search_indiehackers` to Competitor Research. Indie Hackers posts about revenue are competitive intelligence, not generic "monetization signals."

### Phase 5: Eval Framework

Built a comprehensive evaluation system:
- 25 golden test cases across 5 categories
- 21 deterministic code graders + 6 LLM-as-judge model graders + 2 consistency graders
- Results saved as JSON for before/after comparison
- Configurable: `--skip-model` for cheaper runs, `--trials=N` for consistency, `--category` for targeted testing

### Phase 6: Eval-Driven Prompt Fixes (Post-Eval Run `eval_20260218_111357`)

Ran full eval suite (25 cases, 1 trial each). Results: **20% pass rate** (5/25). Average score was high (0.90) but a single failed grader per trial causes a full trial failure. Diagnosed 4 systemic root causes and applied targeted prompt engineering fixes informed by [Anthropic's multishot prompting best practices](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/multishot-prompting) and [LLM calibration research](https://learnprompting.org/docs/reliability/calibration).

**Root Cause Analysis:**

| Root Cause | Failures Caused | Agent | Technique Applied |
|---|---|---|---|
| Pain severity central tendency bias | 14/20 | Pain Discovery | Few-shot examples + sharper boundary definitions + explicit calibration instruction |
| Market saturation undefined criteria | 6/20 | Competitor Research | Explicit threshold criteria with concrete examples |
| Synthesis double-pessimism cascade | 6/20 | Synthesis (both passes) | Removed skepticism bias from viability pass; added calibration anchor examples to verdict pass |
| Known competitor detection gaps | 5/20 | Competitor Research | Reordered search strategy to prioritize incumbents first |

**Fix 1 — Pain Severity Distribution** (`pain_discovery.py`):
- **Problem**: LLM rated every pain point "moderate" (14/20 cases). This is classic [central tendency bias](https://learnprompting.org/docs/reliability/debiasing) — the model defaults to the safe middle option when category boundaries are vague.
- **Technique**: Applied Anthropic's recommended [few-shot prompting](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/multishot-prompting) with 5 diverse examples (2 mild, 1 moderate, 2 high) wrapped in `<example>` tags. Added sharper boundary definitions that eliminate overlap between levels. Added explicit calibration instruction: "You MUST use the full range of severity levels."
- **Why few-shot**: Anthropic's docs state "Examples are your secret weapon...particularly effective for tasks that require structured outputs." The 5 examples are diverse (covering different severities), relevant (using real-world complaint patterns), and balanced (not skewed toward one label — addressing [majority label bias](https://learnprompting.org/docs/reliability/calibration)).
- **Why sharper boundaries**: Old "moderate" definition ("recurring time or money drain, significant business impact") covered 90% of real complaints. New definitions use concrete decision rules: "If the person just wishes something were better → mild; If they describe spending time/money but managing → moderate; If they describe it as blocking, costly, or existential → high."

**Fix 2 — Market Saturation Criteria** (`competitor_research.py`):
- **Problem**: Agent had zero guidance for what constitutes low/medium/high saturation. The prompt said only "Synthesize market saturation: ONLY low, medium, or high" — no definitions, no examples.
- **Technique**: Added explicit threshold-based criteria with concrete examples. "low" = 0-2 direct competitors, no dominant player. "medium" = 3-6 direct competitors, some funded. "high" = 7+ competitors OR any competitor with >$100M revenue or millions of users. Each level includes a real-world example.
- **Why thresholds**: Without criteria, the LLM was inferring saturation from vibes. Email marketing (Mailchimp with 13M+ users) was rated "medium" because the agent found only 3-4 competitors in its search results, ignoring the massive scale of incumbents. The threshold "any competitor with >$100M revenue or millions of users → high" catches this.

**Fix 3 — Synthesis Pessimism Bias** (`synthesis.py`):
- **Problem**: All 5 "obviously_good" ideas and 3/5 "niche_viable" ideas got SKIP instead of BUILD/MAYBE. Confidence clustered at 0.32.
- **Root cause**: Double-pessimism cascade. Pass 1 (Viability) was instructed "Bias toward skepticism." Pass 2 (Verdict) was told "Be critical" and "Use the viability analysis as established facts." So Pass 2 built on an already-deflated assessment. Additionally, the upstream pain severity bug fed "0 of N high-impact" into synthesis, making even strong ideas appear weak.
- **Technique 1**: Replaced "Bias toward skepticism" in the viability prompt with "Be evidence-driven, not pessimistic or optimistic. Let the data speak." This is the [prompt debiasing](https://learnprompting.org/docs/reliability/debiasing) principle — removing directional bias from instructions.
- **Technique 2**: Added "Competition VALIDATES demand" and "If research found 5+ real pain points with high-impact severity, funded competitors, and growing market, that is strong BUILD evidence" to the verdict prompt. This counteracts the natural LLM tendency to list risks as reasons to SKIP.
- **Technique 3**: Added 5 verdict calibration anchor examples (few-shot) spanning the full BUILD/SKIP/MAYBE spectrum with specific confidence scores. This applies Anthropic's recommendation to "include 3-5 diverse, relevant examples" and addresses [confidence calibration](https://learnprompting.org/docs/reliability/calibration) by showing the model what different verdicts look like with real data patterns.

**Fix 4 — Known Competitor Detection** (`competitor_research.py`):
- **Problem**: Agent missed household-name competitors (WeWork for office space, Mailchimp for email, Outreach for SDR tools) while finding niche players from Product Hunt.
- **Technique**: Reordered search strategy to start with "FIRST: Search for obvious market leaders and incumbents" before deep-diving into niche tools. Added explicit instruction: "Missing a household name like Salesforce in CRM or Mailchimp in email marketing is a critical error."
- **Why reorder**: The agent's search budget is limited. By searching niche sources first, it consumed search turns on small players and ran out of budget before finding the obvious incumbents. Frontloading incumbent search ensures the most important competitors are always found.

**Prompt Engineering Principles Applied** (summary):
1. **Few-shot examples with balanced label distribution** — prevents central tendency bias by showing the model all categories are valid and expected (Anthropic multishot prompting + calibration research)
2. **Explicit boundary definitions** — eliminates ambiguity that causes the model to default to safe middle values
3. **Directional debiasing** — removing words like "skepticism" and "bias toward" that compound across multi-pass prompts
4. **Calibration anchors** — concrete input→output examples that establish the expected scoring range
5. **Search strategy reordering** — ensuring the most critical information (market leaders) is gathered first within limited tool-use budgets

---

## 8. Presentation Notes

**Framework**: SCR (Situation, Complication, Resolution)

**SCR outline**:
- **Situation**: Aspiring founders spend days manually researching whether their idea is viable — searching Reddit, checking competitors, estimating market size
- **Complication**: Manual research is slow, biased, and often incomplete — people skip it and build the wrong thing, wasting months
- **Resolution**: Maviriq automates this with a 5-agent AI pipeline that delivers structured market validation in minutes, complete with evidence, competitor maps, and a calibrated BUILD/SKIP/MAYBE verdict

**Key talking points**:
1. **Agentic architecture**: Not just "ask GPT a question" — 5 specialized agents with tool-use loops that autonomously decide what to search
2. **Fan-out parallelism**: Agents 1-4 run simultaneously, cutting pipeline time by ~70%
3. **Evidence-driven calibration**: The system uses few-shot examples, calibration anchors, and explicit boundary definitions to produce accurate verdicts — not biased toward SKIP or BUILD
4. **Iterative improvement**: Systematic prompt engineering based on eval results (ownership boundaries, TAM narrowing, redundancy removal, severity calibration, pessimism debiasing)
5. **Evaluation framework**: 25 golden test cases with automated grading — not just "it looks right," but measurable pass/fail criteria

**Demo flow suggestion**:
1. Show the idea input
2. Show agents running in parallel (SSE progress)
3. Walk through results: pain points with real quotes → competitor map → market intelligence → graveyard → final verdict
4. Show an obviously bad idea getting SKIP vs a good idea getting BUILD
5. Briefly show the eval framework (golden cases, graders)

---

## 9. README Checklist

Per the capstone requirements, your README.md must include:
- [ ] Clear description of the project's purpose
- [ ] What problem it solves
- [ ] How it works (high-level architecture)

---

## 10. File Reference

Key files for understanding the codebase:

**Agent implementations**:
- `src/maviriq/agents/pain_discovery.py` — Pain & User Discovery agent
- `src/maviriq/agents/competitor_research.py` — Competitor Research agent
- `src/maviriq/agents/market_intelligence.py` — Market Intelligence agent
- `src/maviriq/agents/graveyard_research.py` — Graveyard Research agent
- `src/maviriq/agents/synthesis.py` — Synthesis & Verdict agent
- `src/maviriq/agents/base.py` — BaseAgent class (tool-use loop)
- `src/maviriq/agents/tools.py` — Tool catalog and builder

**Schemas**:
- `src/maviriq/models/schemas.py` — All Pydantic models for agent I/O

**Services**:
- `src/maviriq/services/search.py` — SerperService with site-specific search methods
- `src/maviriq/services/llm.py` — LLMService wrapper for Anthropic API

**Pipeline**:
- `src/maviriq/pipeline/graph.py` — LangGraph state graph definition

**Evaluation**:
- `tests/evals/cases/golden_cases.yaml` — 25 test cases
- `tests/evals/harness.py` — Eval harness and pipeline runner
- `tests/evals/graders/code_graders.py` — 21 deterministic graders
- `tests/evals/graders/model_graders.py` — 6 LLM-as-judge graders
- `tests/evals/graders/consistency.py` — 2 consistency graders
- `tests/evals/test_eval_pipeline.py` — Main eval test file

**Frontend**:
- `frontend/src/lib/types.ts` — TypeScript types (mirrors Pydantic schemas)
- `frontend/src/lib/auth-context.tsx` — Auth context (Supabase session + Google OAuth)
- `frontend/src/lib/posthog.tsx` — PostHog analytics provider
- `frontend/src/app/forgot-password/page.tsx` — Password reset request page
- `frontend/src/app/reset-password/page.tsx` — Set new password page
- `frontend/src/components/` — Result display components
