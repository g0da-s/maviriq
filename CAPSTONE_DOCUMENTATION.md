# Capstone Documentation — Case 2: AI Agent for Task Automation

> Use this file to document everything needed for your capstone submission.
> Fill in each section as you go. Sections marked [TODO] still need your input.

---

## 1. Agent Design

**Purpose**: Maviriq is an AI-powered startup idea validator. Given a business idea, it autonomously runs a multi-agent pipeline that researches real pain points, analyzes competitors, evaluates market viability, and synthesizes a final verdict — automating hours of manual market research into minutes.

**Capabilities**:
- Autonomous web research (pain discovery, competitor analysis)
- Multi-step reasoning across 4 specialized agents
- Structured output generation (scores, verdicts, competitor maps)
- Real-time progress streaming to the user via SSE

**Architecture**:
- 4 agents orchestrated via LangGraph (fan-out/fan-in pattern)
  - Agent 1: Pain & User Discovery
  - Agent 2: Competitor Research
  - Agents 1 & 2 run in parallel, then fan-in to:
  - Agent 3: Viability Analysis
  - Agent 4: Synthesis & Verdict
- Retry logic: Agents 1 & 2 retry with broader queries if data quality is "partial"

[TODO: Add a diagram of the agent pipeline if needed for your presentation]

---

## 2. Tool Integration

**LLM**: Anthropic Claude (via LangChain's `ChatAnthropic`)
- Structured output via `.with_structured_output()` (Pydantic models)
- Cheap model used for query generation and input validation
- Full model used for analysis and synthesis

**Search**: Serper API (Google search + news search)
- Multi-query parallel search with deduplication
- Retry with exponential backoff

**Database**: Supabase (PostgreSQL)
- Stores validation runs, user accounts, credit transactions
- RPC functions for atomic credit deduction

**Payments**: Stripe Checkout
- Credit pack purchases with webhook verification

**Auth**: Supabase Auth (email/password)
- JWT verification via JWKS endpoint

[TODO: Note any other external APIs or tools you want to highlight]

---

## 3. Agent Execution — Advanced Features

**Multi-step reasoning**:
- Each agent performs: query generation → web search → result analysis → structured output
- Agent 3 (Viability) reasons across outputs from Agents 1 & 2
- Agent 4 (Synthesis) reasons across all three previous outputs to produce a final verdict

**Orchestration (LangGraph)**:
- StateGraph with conditional edges for retry logic
- Fan-out parallelism (Agents 1 & 2 run simultaneously)
- Fan-in synchronization (Agent 3 waits for both)
- Stream mode for real-time SSE event publishing

**Input validation (3-layer)**:
- Layer 1: Frontend regex (profanity + gibberish detection)
- Layer 2: Backend Pydantic validator (same checks server-side)
- Layer 3: LLM coherence check (cheap model, before credit deduction)

**Error handling**:
- Generic error messages to clients (no internal details leaked)
- Detailed logging server-side for debugging
- Timeout handling per agent with configurable thresholds

[TODO: Add notes on anything else you consider "advanced" — e.g., rate limiting, credit system]

---

## 4. Interactive Prototyping

**Frontend**: Next.js 16 + React 19 + Tailwind CSS 4
- Real-time pipeline progress via Server-Sent Events (SSE)
- Step-by-step agent progress indicator
- Results page with structured sections (pain points, competitors, viability, verdict)
- Auth flow (signup, login, credit purchase)

**Backend**: FastAPI
- REST endpoints for validation CRUD, auth, credits
- SSE streaming endpoint for real-time progress
- Stripe webhook endpoint for payment processing

**Deployment**: [TODO: Note where you deployed — e.g., Vercel + Railway, or local demo]

---

## 5. Evaluation

[TODO: Document your testing and evaluation]

**Suggested areas to cover**:
- How accurate are the agent outputs? (Try 3-5 diverse business ideas and assess quality)
- How responsive is the system? (Average pipeline completion time)
- User testing feedback (if any)
- Edge cases tested (gibberish input, very niche ideas, non-English input)
- Known limitations (e.g., search API rate limits, LLM hallucination potential)

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

**Cost & Access**:
- Credit system gates access — free tier (1 credit) allows trial
- Input validation prevents wasting credits on gibberish

[TODO: Add any other ethical considerations relevant to your submission]

### Technical Decisions Log

| Decision | Rationale |
|----------|-----------|
| Anthropic Claude over OpenAI | Better structured output, less hallucination in analysis tasks |
| LangGraph over raw asyncio | Built-in state management, conditional routing, stream support |
| Supabase over raw PostgreSQL | Auth, RPC, real-time features out of the box |
| SSE over WebSockets | Simpler for unidirectional server→client streaming |
| Credit system over subscription | Lower barrier to entry, pay-per-use model |

[TODO: Add more decisions as needed]

---

## 7. Presentation Notes

**Framework**: Use SCR (Situation, Complication, Resolution) or SMART as recommended.

**SCR outline**:
- **Situation**: Aspiring founders spend days manually researching whether their idea is viable
- **Complication**: Manual research is slow, biased, and often incomplete — people skip it and build the wrong thing
- **Resolution**: Maviriq automates this with a multi-agent AI pipeline that delivers structured market validation in minutes

[TODO: Flesh out your presentation talking points]

---

## 8. README Checklist

Per the capstone requirements, your README.md must include:
- [ ] Clear description of the project's purpose
- [ ] What problem it solves
- [ ] How it works (high-level architecture)

[TODO: Create or update your README.md before submission]
