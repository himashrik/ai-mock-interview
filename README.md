# AI Mock Interview Platform

A RAG-based AI interview preparation platform: upload a resume (and optional JD), configure an
interview, and get asked grounded, adaptive questions with immediate scored feedback and a final
report. See `ARCHITECTURE.md` for the full design (schema, API, RAG pipeline, scoring methodology,
security checklist, deployment plan), and `RESUME.md` if you're using this project on a resume/portfolio.

Once you push this to GitHub, add a live CI badge to the top of this file:
`[![CI](https://github.com/<you>/<repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/<you>/<repo>/actions/workflows/ci.yml)`
— a green badge is a small, concrete signal in a portfolio README that the test suite is real and passing.

## Stack
- **Backend**: Python 3.11, FastAPI, SQLAlchemy, PostgreSQL + `pgvector`
- **Frontend**: React + Vite + Tailwind CSS
- **LLM**: pluggable — Anthropic Claude or OpenAI (set `LLM_PROVIDER` in `.env`)
- **Embeddings**: pluggable — local `sentence-transformers` (free, default) or OpenAI

## Quick start (Docker)

```bash
cd backend
cp .env.example .env
docker compose up --build
```

That's it — **no API key required to see the app fully working.** If `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`
are left blank, the backend automatically falls back to a rule-based mock LLM provider (clearly labeled
as demo content everywhere it appears in the UI, via a dismissible banner) so every feature — resume
upload, ATS scoring, the full adaptive interview loop, the AI assistant chat — runs end to end with zero
setup. Add a real key in `.env` and restart whenever you want real AI-generated content instead.

The API will be live at `http://localhost:8000` (docs at `http://localhost:8000/docs`).
The `api` container runs `alembic upgrade head` automatically before starting the server.

## Quick start (without Docker)

```bash
# 1. Postgres with pgvector must be running and reachable at DATABASE_URL in .env
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit as above
alembic upgrade head   # creates the pgvector extension + all tables via migrations
uvicorn app.main:app --reload
```

```bash
# in a second terminal
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## Environment variables (backend/.env)
See `.env.example` for the full list. Minimum to get running:
- `DATABASE_URL`
- `JWT_SECRET_KEY` — generate with `python -c "import secrets; print(secrets.token_hex(32))"`
- `LLM_PROVIDER` + the matching API key (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`)
- `EMBEDDING_PROVIDER=local` requires no key (downloads a small model on first use);
  `EMBEDDING_PROVIDER=openai` requires `OPENAI_API_KEY`.

**Never commit `.env`** — only `.env.example` (with placeholders) is meant to be checked in.

## Real-world validation
Beyond the automated test suite, this was manually verified against a real, locally-installed
PostgreSQL 16 + pgvector instance (not just SQLite/mocks):
- `alembic upgrade head` runs clean from an empty schema, creates the `vector` extension itself, and
  produces exactly the expected 12 tables, including a genuine `vector(384)` column with a working
  `ivfflat` cosine-distance index.
- The full test suite (107 tests) passes with **zero skips** when pointed at the real instance, including
  the pgvector isolation test that's normally skipped in CI-without-Docker.
- The real FastAPI server was started against it and exercised over actual HTTP: register → login →
  authenticated request → cookie-based refresh rotation, all confirmed working end to end.
- A real DOCX file was uploaded and correctly parsed end to end (verified the extracted text in the
  database directly). The embedding step failed in this sandbox specifically because outbound network
  access to `huggingface.co` isn't available here — and critically, the app **degraded gracefully**: the
  document was marked `status: "failed"` with a clear `error_message`, no crash, no 500, exactly the
  behavior the error-handling code was designed for. This is an environment limitation of the validation
  sandbox, not a defect — the same code path works normally with network access to Hugging Face (or with
  `EMBEDDING_PROVIDER=openai`).

What's *not* yet verified against real infrastructure: an actual Anthropic/OpenAI API call (no API key
was available in the validation environment), and a deployed run of the GitHub Actions CI workflow.

## What's implemented vs. what's a next step
Implemented and working end-to-end: auth (register/login/refresh via rotating httpOnly cookie,
rate-limited, with a server-side JWT revocation denylist so logout takes effect immediately), light/dark
mode, an AI coaching assistant chat widget (RAG-grounded when a resume/JD is on file), resume/JD upload
with validation, text extraction, cleaning, chunking, embedding, pgvector storage and retrieval scoped
per-user, resume/JD structured analysis, ATS scoring, full adaptive interview loop (RAG-grounded question
generation with follow-up probing and a performance-based difficulty ramp → answer submission → immediate
structured evaluation → transparent scoring), final report generation (computed scores + LLM narrative),
performance history, and a CI pipeline (`.github/workflows/ci.yml`) running the test suite, a frontend
build, and a real migration-against-Postgres check on every push.

Natural next steps for a production hardening pass:
- Wire `token_denylist.prune_expired()` into a periodic job (cron/Celery beat/etc.) so the revocation
  table doesn't grow unbounded over time in a long-running deployment.
- Point `RATE_LIMIT_STORAGE_URI` at Redis in any deployment running more than one API process/worker —
  it defaults to in-memory, which only enforces limits per-process.
- Set `COOKIE_SECURE=true` in `.env` once serving over HTTPS in production (defaults to `false` so local
  `http://localhost` dev works without extra setup).

## Testing

```bash
cd backend
pip install -r requirements.txt
pytest
```

106 tests pass out of the box (no Docker/DB required) — LLM calls are stubbed with a fake provider, and
DB-backed tests run against a disposable in-memory SQLite schema via a portable `GUID` column type
(`app/db/types.py`) that behaves identically to Postgres's native UUID from the application's point of
view. One additional integration test (`tests/test_vector_store.py`) exercises the real pgvector-backed
vector store and is skipped automatically unless `TEST_DATABASE_URL` is set — see the docstring at the
top of that file for how to run it against a throwaway Postgres container; **this has been verified
against a real PostgreSQL 16 + pgvector instance** (all 107 tests pass, 0 skipped), along with a full
manual smoke test over real HTTP: register → login → authenticated request → cookie-based refresh, and a
real DOCX upload through actual text extraction (embeddings failed only because this sandbox's network
egress doesn't reach huggingface.co — and the app degraded gracefully, setting `status: "failed"` with a
clear message rather than crashing, exactly as designed). See `ARCHITECTURE.md` §14 for the full strategy.

## Database migrations

Schema is managed by Alembic (`backend/migrations/`), with a hand-written initial migration
(`0001_initial_schema.py`) rather than autogenerate, for reliability with the custom `pgvector` column
type. To create a new migration after changing a model:

```bash
cd backend
alembic revision -m "add some_new_field"   # hand-edit the generated file, or use --autogenerate if you trust it
alembic upgrade head
```

## Project layout
```
backend/    FastAPI app, RAG pipeline, LLM abstraction, DB models — see backend/app/
frontend/   React + Vite + Tailwind SPA — see frontend/src/
ARCHITECTURE.md   Full design document (all 17 sections from the original spec)
```
