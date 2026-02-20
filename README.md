# Maviriq

**AI-powered startup idea validator** — a multi-agent research system that tells you whether your idea is worth building before you write a single line of code.

Maviriq takes a business idea (e.g., "AI-powered pitch deck generator"), runs 5 specialized AI agents that search the real web for evidence, and delivers a BUILD / SKIP / MAYBE verdict backed by data — pain points from Reddit and HN, competitor maps from G2 and Capterra, market sizing, failed startup analysis, and a final synthesis with calibrated confidence scoring.

**The problem it solves:** Founders spend weeks or months researching an idea manually — scanning Reddit for complaints, Googling competitors, estimating market size, checking if someone already tried and failed. Maviriq automates all of this in under 2 minutes, surfacing real complaints, real competitors, and real market gaps — so you can make an informed decision fast.

---

## How It Works

Maviriq orchestrates 5 AI agents via LangGraph in a fan-out/fan-in pattern:

```
            ┌─ Agent 1: Pain Discovery ────────┐
            ├─ Agent 2: Competitor Research ────┤
START ──────┤                                   ├──── Agent 5: Synthesis ──── END
            ├─ Agent 3: Market Intelligence ────┤
            └─ Agent 4: Graveyard Research ─────┘
```

1. **Pain & User Discovery** — Searches Reddit, Hacker News, Twitter, and Google News for real complaints. Extracts pain points with severity scores, identifies the primary target user.
2. **Competitor Research** — Maps the competitive landscape using Google, G2, Capterra, Product Hunt, Indie Hackers, and Crunchbase. Analyzes pricing, strengths/weaknesses, and market saturation.
3. **Market Intelligence** — Estimates TAM (with explicit narrowing from broad market to specific niche), growth direction, distribution channels, and funding signals.
4. **Graveyard Research** — Finds failed startups in the same space, extracts failure reasons, and identifies churn signals.
5. **Synthesis & Verdict** — Combines all research into a BUILD/SKIP/MAYBE verdict with calibrated confidence score, reasoning, key strengths/risks, and recommended next steps.

Agents 1–4 run **in parallel** (fan-out), cutting pipeline time by ~70%. All four results then fan-in to Agent 5 (Synthesis). Each research agent runs an autonomous tool-use loop — the LLM decides what to search, analyzes results, and calls more tools until it has enough data.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI (async) |
| **Frontend** | Next.js 16, React 19, Tailwind CSS 4 |
| **LLM** | Claude Sonnet (reasoning + tool-use loops) + Claude Haiku (eval grading, cheap tasks) via `langchain-anthropic` |
| **Orchestration** | LangGraph (parallel fan-out/fan-in StateGraph) |
| **Search** | Serper API (Google, Reddit, HN, G2, Capterra, Product Hunt, Crunchbase, Indie Hackers, Twitter, Google News) |
| **Database** | Supabase (PostgreSQL + Auth) |
| **Auth** | Supabase Auth (email/password + Google OAuth), password reset, JWT verification |
| **Analytics** | PostHog (event tracking for signups, logins, purchases) |
| **Payments** | Stripe Checkout (credit packs: 5/$5, 20/$15, 50/$30) |
| **Observability** | LangSmith tracing (auto-traced via ChatAnthropic) |
| **Streaming** | Server-Sent Events (SSE) for real-time progress |

---

## Features

- **Parallel agent execution** — Agents 1–4 run simultaneously via LangGraph fan-out, cutting pipeline time by ~70%
- **Agentic tool-use loops** — Each research agent autonomously decides what to search and when to stop (not hardcoded query lists)
- **Real-time streaming** — Watch each agent complete in real-time via SSE
- **Calibrated prompts** — Few-shot examples, severity calibration, saturation thresholds, and debiased synthesis to prevent systematic pessimism
- **Input validation** — 3-layer protection: regex (profanity + gibberish), Pydantic validators, LLM coherence check
- **Google OAuth** — Sign in with Google via Supabase OAuth, alongside email/password
- **Password reset** — Forgot password flow via Supabase email recovery
- **Credit system** — 1 free credit on signup, purchase more via Stripe
- **Search caching** — 24-hour TTL on search results to reduce API costs
- **LangSmith tracing** — Full observability into every LLM call and tool usage
- **Rate limiting** — Sliding window limiter on auth endpoints
- **Analytics** — PostHog event tracking for signups, logins, and purchases
- **Eval framework** — 25 golden test cases with 29 automated graders (code + LLM-as-judge + consistency)

---

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- [uv](https://github.com/astral-sh/uv) package manager
- API keys: Anthropic, Serper, Supabase, Stripe

### 1. Install

```bash
cd maviriq

# Backend
uv sync

# Frontend
cd frontend && npm install && cd ..
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Run

```bash
# Backend (terminal 1)
uv run uvicorn maviriq.main:app --reload --app-dir src

# Frontend (terminal 2)
cd frontend && npm run dev
```

Backend: `http://localhost:8000` | Frontend: `http://localhost:3000`

---

## Project Structure

```
src/maviriq/
  main.py                       # FastAPI entry point + CORS
  config.py                     # pydantic-settings config + LangSmith env propagation
  supabase_client.py            # Async Supabase client
  models/
    schemas.py                  # All Pydantic models (agents, API, validation)
    auth.py                     # Auth request/response models
  agents/
    base.py                     # BaseAgent[I, O] abstract class
    tools.py                    # Tool catalog and builder for agent tool-use
    pain_discovery.py           # Agent 1: search + extract pain points
    competitor_research.py      # Agent 2: search + competitor analysis
    market_intelligence.py      # Agent 3: TAM, growth, distribution, funding signals
    graveyard_research.py       # Agent 4: failed startups + churn signals
    synthesis.py                # Agent 5: final verdict (reasoning only, no search tools)
  services/
    llm.py                      # LLMService wrapper (ChatAnthropic, structured output, tool-use loops)
    search.py                   # SerperService with 10+ site-specific search methods
    input_validation.py         # Profanity blocklist + gibberish detection
  pipeline/
    runner.py                   # LangGraph StateGraph (fan-out/fan-in topology)
    graph.py                    # Entry point for LangGraph Studio
    events.py                   # SSE event types
    pubsub.py                   # In-memory pub/sub for live streaming
  storage/
    repository.py               # Validation CRUD + search cache (Supabase)
    user_repository.py          # User profiles + credit management
    credit_repository.py        # Credit transaction log
  api/
    routes.py                   # Validation endpoints + SSE streaming
    auth_routes.py              # Auth endpoint (GET /me)
    stripe_routes.py            # Stripe webhook + checkout
    stream_tokens.py            # SSE token streaming
    rate_limit.py               # Sliding window rate limiter
    dependencies.py             # JWT verification + DI

frontend/src/
  app/
    page.tsx                    # Home — idea submission form
    login/page.tsx              # Email/password + Google OAuth login
    register/page.tsx           # Signup with email verification + Google OAuth
    forgot-password/page.tsx    # Password reset request
    reset-password/page.tsx     # Set new password (from email link)
    credits/page.tsx            # Stripe credit purchase
    validations/page.tsx        # Validation history
    validations/[id]/page.tsx   # Validation detail + live progress
  components/
    idea-form.tsx               # Input with 3-layer validation
    pipeline-progress.tsx       # Real-time agent progress (parallel-aware)
    pain-points.tsx             # Pain discovery results display
    competitors.tsx             # Competitor research results display
    market-intelligence.tsx     # Market intelligence results display
    graveyard-research.tsx      # Graveyard research results display
    viability.tsx               # Viability dashboard display
    verdict-badge.tsx           # BUILD/SKIP/MAYBE badge
    detail-section.tsx          # Reusable section wrapper
    confirm-modal.tsx           # Confirmation dialog
    nav.tsx                     # Navigation bar
    offline-banner.tsx          # Offline state indicator
    providers.tsx               # React context providers
    error-boundary.tsx          # React error boundary
  lib/
    api.ts                      # Centralized API client
    auth-context.tsx            # Auth context (Supabase session + Google OAuth)
    posthog.tsx                 # PostHog analytics provider
    supabase.ts                 # Supabase client config
    types.ts                    # Zod schemas + TypeScript types

tests/evals/
  cases/golden_cases.yaml       # 25 golden test cases across 5 categories
  harness.py                    # Eval harness and pipeline runner
  graders/
    code_graders.py             # 21 deterministic graders
    model_graders.py            # 6 LLM-as-judge graders
    consistency.py              # 2 consistency graders
  test_eval_pipeline.py         # Main eval test file
```

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/validations` | Start a new validation (deducts 1 credit) |
| GET | `/api/validations/:id` | Get full results |
| GET | `/api/validations/:id/stream` | Stream progress (SSE) |
| POST | `/api/validations/:id/stream-token` | Issue single-use stream token |
| GET | `/api/validations` | List past validations |
| DELETE | `/api/validations/:id` | Delete a validation |
| GET | `/api/auth/me` | Get authenticated user profile |
| POST | `/api/stripe/checkout` | Create Stripe checkout session |
| POST | `/api/stripe/webhook` | Stripe webhook (credit fulfillment) |
| GET | `/api/health` | Health check |
| GET | `/api/stats` | Public stats (total validations) |

---

## Ethical Considerations

### Data Privacy
- User ideas are stored in Supabase (PostgreSQL) and only accessible to the submitting user via JWT-scoped queries. Ideas are not shared, sold, or used for model training.
- Search data is sourced from publicly available web pages via the Serper API. No private or authenticated data is accessed.
- Supabase Auth handles password hashing, session management, and OAuth — no raw passwords are stored.

### Bias and Fairness
- LLM verdicts may carry biases from Claude's training data. The system is designed as a research accelerator, not a definitive business oracle. Users should treat verdicts as starting points for further investigation, not final decisions.

### Content Moderation
- Input validation includes profanity blocking, gibberish detection, and an LLM coherence check to prevent misuse of the system and ensure meaningful outputs.

### Cost Transparency
- The credit system ensures users are aware of costs upfront. No hidden charges — 1 credit = 1 validation, credit packs are clearly priced.

---

## License

MIT
