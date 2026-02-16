# Maviriq

**AI-powered startup idea validator** — a multi-agent research system that tells you whether your idea is worth building before you write a single line of code.

Maviriq takes a business idea (e.g., "AI-powered pitch deck generator"), runs 4 specialized AI agents that search the real web for evidence, and delivers a BUILD / SKIP / MAYBE verdict backed by data — pain points from Reddit and HN, competitor analysis from G2 and Capterra, viability signals, and a final synthesis with confidence scoring.

**The problem it solves:** Founders spend weeks or months researching an idea manually. Maviriq does this in under 2 minutes, surfacing real complaints, real competitors, and real market gaps — so you can make an informed decision fast.

---

## How It Works

Maviriq orchestrates 4 AI agents via LangGraph:

```
START --> [Agent 1 + Agent 2] (parallel) --> Agent 3 --> Agent 4 --> END
```

1. **Pain & User Discovery** — Searches Reddit, Hacker News, Twitter, YouTube, and forums for real complaints. Extracts pain points with severity scores, identifies target user segments.
2. **Competitor Research** — Maps the competitive landscape using Google, G2, Capterra, Product Hunt, and Crunchbase. Scrapes pricing pages, analyzes strengths/weaknesses, finds market gaps.
3. **Viability Analysis** — Evaluates willingness to pay, user reachability, market gap size, and opportunity score based on data from agents 1 and 2.
4. **Synthesis & Verdict** — Combines all research into a BUILD/SKIP/MAYBE verdict with confidence score, reasoning, key strengths/risks, and recommended next steps.

Agents 1 and 2 run **in parallel** (saving ~15-20 seconds), then results feed into agents 3 and 4 sequentially. Each agent has automatic retry logic — if data quality is insufficient, it generates broader queries and searches again.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI (async) |
| **Frontend** | Next.js 16, React 19, Tailwind CSS 4 |
| **LLM** | Claude Sonnet 4.5 (reasoning) + Claude Haiku 4.5 (cheap tasks) via `langchain-anthropic` |
| **Orchestration** | LangGraph (parallel fan-out/fan-in, conditional retry edges) |
| **Search** | Serper API (Google, Reddit, HN, G2, Capterra, Product Hunt, Crunchbase, YouTube, Twitter, LinkedIn) |
| **Database** | Supabase (PostgreSQL + Auth) |
| **Auth** | Email/password via Supabase Auth, JWT verification |
| **Payments** | Stripe Checkout (credit packs: 5/$5, 20/$15, 50/$30) |
| **Observability** | LangSmith tracing (auto-traced via ChatAnthropic) |
| **Streaming** | Server-Sent Events (SSE) for real-time progress |

---

## Features

- **Parallel agent execution** — Agents 1 and 2 run simultaneously via LangGraph fan-out
- **Real-time streaming** — Watch each agent complete in real-time via SSE
- **Automatic retries** — Agents retry with broader queries if data is insufficient
- **Input validation** — 3-layer protection: regex (profanity + gibberish), Pydantic validators, LLM coherence check
- **Credit system** — 1 free credit on signup, purchase more via Stripe
- **Search caching** — 24-hour TTL on search results to reduce API costs
- **LangSmith tracing** — Full observability into every LLM call
- **Rate limiting** — Sliding window limiter on auth endpoints

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
  agents/
    base.py                     # BaseAgent[I, O] abstract class
    pain_discovery.py           # Agent 1: search + extract pain points
    competitor_research.py      # Agent 2: search + competitor analysis
    viability_analysis.py       # Agent 3: viability scoring
    synthesis.py                # Agent 4: final verdict
  services/
    llm.py                      # ChatAnthropic wrapper (structured output, text, lists)
    search.py                   # Serper API wrapper (10+ search types)
    input_validation.py         # Profanity blocklist + gibberish detection
  pipeline/
    runner.py                   # LangGraph state machine (parallel topology)
    events.py                   # SSE event types
    pubsub.py                   # In-memory pub/sub for live streaming
  storage/
    repository.py               # Validation CRUD + search cache (Supabase)
    user_repository.py          # User profiles + credit management
    credit_repository.py        # Credit transaction log
  api/
    routes.py                   # Validation endpoints + SSE streaming
    auth_routes.py              # Auth endpoints
    stripe_routes.py            # Stripe webhook + checkout
    rate_limit.py               # Sliding window rate limiter
    dependencies.py             # JWT verification + DI

frontend/src/
  app/
    page.tsx                    # Home — idea submission form
    login/page.tsx              # Email/password login
    register/page.tsx           # Signup with email verification
    credits/page.tsx            # Stripe credit purchase
    validations/page.tsx        # Validation history
    validations/[id]/page.tsx   # Validation detail + live progress
  components/
    idea-form.tsx               # Input with 3-layer validation
    pipeline-progress.tsx       # Real-time agent progress (parallel-aware)
    pain-points.tsx             # Pain discovery results display
    competitors.tsx             # Competitor research results display
    viability.tsx               # Viability analysis display
    verdict-badge.tsx           # BUILD/SKIP/MAYBE badge
    nav.tsx                     # Navigation bar
    error-boundary.tsx          # React error boundary
  lib/
    api.ts                      # Centralized API client
    auth-context.tsx            # Auth context (Supabase session management)
    types.ts                    # Zod schemas + TypeScript types
```

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/validations` | Start a new validation (deducts 1 credit) |
| GET | `/api/validations/:id` | Get full results |
| GET | `/api/validations/:id/stream` | Stream progress (SSE) |
| GET | `/api/validations` | List past validations |
| DELETE | `/api/validations/:id` | Delete a validation |
| POST | `/api/auth/register` | Register with email/password |
| POST | `/api/auth/login` | Login |
| GET | `/api/credits/balance` | Get credit balance |
| POST | `/api/credits/checkout` | Create Stripe checkout session |
| POST | `/api/stripe/webhook` | Stripe webhook (credit fulfillment) |
| GET | `/api/health` | Health check |

---

## Ethical Considerations

### Data Privacy
- User ideas are stored in Supabase (PostgreSQL) and only accessible to the submitting user via JWT-scoped queries. Ideas are not shared, sold, or used for model training.
- Search data is sourced from publicly available web pages via the Serper API. No private or authenticated data is accessed.
- Supabase Auth handles password hashing and session management — no raw passwords are stored.

### Bias and Fairness
- LLM verdicts may carry biases from Claude's training data. The system is designed as a research accelerator, not a definitive business oracle. Users should treat verdicts as starting points for further investigation, not final decisions.

### Content Moderation
- Input validation includes profanity blocking, gibberish detection, and an LLM coherence check to prevent misuse of the system and ensure meaningful outputs.

### Cost Transparency
- The credit system ensures users are aware of costs upfront. No hidden charges — 1 credit = 1 validation, credit packs are clearly priced.

---

## License

MIT
