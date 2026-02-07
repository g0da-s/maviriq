# Maverick

**Idea validation pipeline** — A 4-agent research system that automatically validates business ideas.

Submit an idea (e.g., "AI-powered pitch deck generator"), and Maverick runs sequential research to deliver a BUILD/SKIP/CONDITIONAL verdict with confidence scoring.

---

## How It Works

Maverick runs 4 agents sequentially:

1. **Pain & User Discovery** — Searches Reddit, Hacker News, forums for complaints. Extracts 10-15 pain points, identifies target users.
2. **Competitor Research** — Maps the competitive landscape. Finds 8-10 competitors, pricing, strengths/weaknesses, market gaps.
3. **Viability Analysis** — Analyzes willingness to pay, user reachability, market gaps.
4. **Synthesis & Verdict** — Combines all research into a BUILD/SKIP/CONDITIONAL verdict with reasoning.

**Estimated cost per validation:** ~$0.30-0.50 (Serper + Claude API calls)

---

## Setup

### 1. Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- API keys:
  - **Anthropic** (Claude) — [Get key](https://console.anthropic.com/)
  - **Serper** (Google search) — [Get free tier](https://serper.dev/) (2,500 queries)

### 2. Install

```bash
# Clone and navigate
cd maverick

# Install dependencies
uv sync

# Create .env file
cp .env.example .env
```

### 3. Configure

Edit `.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-...
SERPER_API_KEY=...
```

### 4. Run

```bash
# Activate virtual environment
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Start the server
python -m maverick.main
```

Server runs at `http://localhost:8000`

OpenAPI docs: `http://localhost:8000/docs`

---

## API Usage

### Start a validation

```bash
curl -X POST http://localhost:8000/api/validations \
  -H "Content-Type: application/json" \
  -d '{"idea": "AI-powered pitch deck generator"}'
```

Response:
```json
{
  "id": "val_abc123",
  "idea": "AI-powered pitch deck generator",
  "status": "running",
  "stream_url": "/api/validations/val_abc123/stream"
}
```

### Stream progress (SSE)

```bash
curl -N http://localhost:8000/api/validations/val_abc123/stream
```

You'll receive events as each agent completes:
```
event: agent_completed
data: {"agent": 1, "name": "Pain & User Discovery", "output": {...}}

event: agent_completed
data: {"agent": 2, "name": "Competitor Research", "output": {...}}

...

event: pipeline_completed
data: {"id": "val_abc123", "verdict": "BUILD", "confidence": 0.78}
```

### Get full results

```bash
curl http://localhost:8000/api/validations/val_abc123
```

Returns the complete `ValidationRun` object with all agent outputs.

### List past validations

```bash
curl http://localhost:8000/api/validations
```

---

## Project Structure

```
src/maverick/
├── main.py                    # FastAPI entry point
├── config.py                  # Settings (API keys, models)
├── models/
│   └── schemas.py             # Pydantic models (data contracts)
├── agents/
│   ├── base.py                # BaseAgent abstract class
│   ├── pain_discovery.py      # Agent 1
│   ├── competitor_research.py # Agent 2
│   ├── viability_analysis.py  # Agent 3
│   └── synthesis.py           # Agent 4
├── services/
│   ├── llm.py                 # Claude API wrapper
│   └── search.py              # Serper search wrapper
├── pipeline/
│   ├── runner.py              # Sequential orchestrator
│   └── events.py              # SSE event types
├── storage/
│   ├── database.py            # SQLite setup
│   └── repository.py          # CRUD operations
└── api/
    ├── routes.py              # API endpoints
    └── dependencies.py        # FastAPI DI
```

---

## Tech Stack

- **Language:** Python 3.12
- **Framework:** FastAPI (async, OpenAPI docs)
- **LLM:** Claude Sonnet 4 (reasoning) + Haiku 4.5 (cheap tasks)
- **Search:** Serper (Google + Reddit via `site:reddit.com`)
- **Database:** SQLite (via aiosqlite)
- **Streaming:** SSE (Server-Sent Events)

---

## Configuration

Edit `src/maverick/config.py` to customize:

- LLM models (Sonnet vs Haiku)
- Search rate limits
- Cache TTL
- Max queries per agent
- Max pain points/competitors

---

## Next Steps

1. **Sign up for API keys:**
   - Anthropic: https://console.anthropic.com/
   - Serper: https://serper.dev/ (free tier: 2,500 queries)

2. **Test with a real idea:**
   ```bash
   curl -X POST http://localhost:8000/api/validations \
     -H "Content-Type: application/json" \
     -d '{"idea": "pitch deck generator for technical founders"}'
   ```

3. **Build the frontend** (React/Next.js recommended):
   - Connect to `POST /api/validations`
   - Use `EventSource` to stream from `/stream` endpoint
   - Display results with verdict, reasoning, pain points, competitors

4. **Deploy:**
   - Backend: Railway, Render, or Fly.io
   - Database: Migrate SQLite → PostgreSQL for production
   - Add authentication (optional)

---

## Troubleshooting

**"ModuleNotFoundError: No module named 'maverick'"**
- Run `uv sync` to install dependencies
- Activate venv: `source .venv/bin/activate`

**"anthropic_api_key field required"**
- Create `.env` file with your API keys

**Search returns no results**
- Check Serper API key is valid
- Verify you have remaining quota (free tier: 2,500 queries)

**Database locked errors**
- SQLite only supports one writer at a time
- For production, migrate to PostgreSQL

---

## License

MIT
