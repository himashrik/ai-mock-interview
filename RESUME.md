# Using this project on your resume

A couple of honest notes first: no README can guarantee a shortlist — that depends on the role, the
recruiter, and how you talk about it in an interview. What actually helps is being able to speak
specifically and correctly about design decisions when asked, since interviewers usually probe exactly
there. Everything below is meant to give you accurate, specific language to adapt — not to be pasted
verbatim without understanding it, because that's exactly what falls apart in a follow-up question.

## One-line summary
Full-stack, RAG-based AI mock-interview platform (FastAPI + PostgreSQL/pgvector + React) with adaptive,
LLM-driven interview questions grounded in the user's resume and target job description.

## Resume bullet points (pick 3–4, adapt to your voice and what you actually built/changed)

- Designed and built a full-stack RAG (Retrieval-Augmented Generation) platform in Python/FastAPI and
  React that grounds AI-generated interview questions and feedback in a user's resume and job description,
  using PostgreSQL with the `pgvector` extension as a combined relational + vector store.
- Implemented a complete RAG pipeline — sentence-aware text chunking, embedding generation, and
  cosine-similarity retrieval — with strict per-user data isolation enforced at the SQL query level, not
  just the application layer.
- Built an adaptive interview engine that generates follow-up questions in response to weak answers and
  adjusts question difficulty in real time based on a candidate's running performance score.
- Designed a transparent, auditable scoring system (category-weighted rubrics, e.g. technical vs.
  behavioral) computed in pure Python rather than delegated to the LLM, with unit tests asserting the
  scoring weights are internally consistent.
- Built a pluggable LLM abstraction layer supporting both Anthropic Claude and OpenAI, and a pluggable
  embeddings layer supporting a free local model (`sentence-transformers`) or OpenAI embeddings, behind a
  single interface each — swappable via a config flag with no code changes elsewhere.
- Wrote a Pytest suite (85+ tests) covering scoring correctness, RAG chunking, JWT/auth security, LLM-JSON
  response validation with retry-on-malformed-output handling, file-upload validation, and cross-user
  authorization (verifying resource access returns 404, not 403, to avoid leaking existence).
- Implemented secure authentication: bcrypt password hashing, short-lived JWTs with rotating refresh
  tokens delivered via httpOnly cookies, and per-IP rate limiting on login/registration endpoints.
- Authored hand-written Alembic migrations (rather than autogenerate) to reliably manage a custom
  Postgres vector column type across schema changes.
- Set up a GitHub Actions CI pipeline that runs the automated test suite, builds the frontend, and
  applies database migrations against a real Postgres+pgvector service container on every push.
- Designed the LLM integration to degrade gracefully rather than fail outright: with no API key
  configured, the backend automatically falls back to a rule-based mock provider (transparently labeled
  as demo content in the UI) so the entire application — including the RAG pipeline and adaptive
  interview loop — is runnable and demonstrable with zero external setup.
- Validated the system against a real PostgreSQL + pgvector instance rather than relying solely on
  mocked tests — this caught and fixed two real bugs in a previously-untested integration test (a
  foreign-key constraint SQLite doesn't enforce by default, and a Postgres-only column-width mismatch),
  and confirmed the schema, migrations, RAG storage, and full auth flow all work correctly end to end.

## Technology / keyword list (for ATS-style resume parsing and the skills section)
Python, FastAPI, PostgreSQL, pgvector, SQLAlchemy, Alembic, Pydantic, RAG (Retrieval-Augmented Generation),
LLM integration (Anthropic Claude, OpenAI), prompt engineering, JWT authentication, bcrypt, REST API
design, React, Vite, Tailwind CSS, Docker, Pytest, TDD-adjacent testing practices, rate limiting,
vector embeddings, semantic search.

## If asked "walk me through this project" in an interview
A good structure: (1) the problem — practicing interviews is hard to do meaningfully alone; (2) the core
idea — ground the AI in the candidate's actual resume/JD via RAG so questions and feedback aren't generic;
(3) one technical decision you can defend in depth — e.g. *why* scores are computed in Python instead of
by the LLM (auditability, no drift, testable), or *why* pgvector in the same Postgres instance instead of
a separate vector DB (simpler ops, one source of truth, fine at this scale); (4) one thing you'd do
differently at larger scale (e.g. move the in-memory rate limiter to Redis, add a real approximate-nearest-
-neighbor index tuning pass, add a JWT revocation denylist). Being able to explain trade-offs, not just
list features, is what actually reads as strong in an interview.

## Before you list it as "production" or "shipped"
Be accurate about what's true for your situation: this is a solid reference implementation with real
tests and real security practices, but it has not been load-tested, has no production monitoring/alerting,
and a few items are explicitly flagged as next steps in `README.md` (JWT revocation denylist, Redis-backed
rate limiting). Saying "built a production-grade reference implementation" or "designed with production
security practices" is defensible; saying "in production serving users" implies something that isn't true
unless you've actually deployed and used it. Interviewers who ask a couple of follow-up questions will
find the gap either way, and overclaiming costs you more credibility than a precise, honest description
would.
