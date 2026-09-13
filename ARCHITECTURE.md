# AI Mock Interview Platform — Architecture

## 1. Product Overview
A web platform where a user uploads a resume (and optionally a job description), configures an interview
(type, role, experience level, difficulty, question count, resume-based vs general), and is interviewed
one question at a time by an LLM-driven interviewer. Every answer is scored and critiqued immediately.
At the end, the user gets a full report: scores, strengths/weaknesses, study plan, and resume/JD alignment
notes. The system is RAG-grounded: questions and evaluations are generated from retrieved chunks of the
user's actual resume/JD/role-knowledge rather than the whole document being stuffed into every prompt, and
rather than the LLM inventing facts.

## 2. Feature List
- Auth: register/login/logout, hashed passwords, rotating JWT refresh tokens in an httpOnly cookie,
  in-memory access tokens, rate-limited login/register, protected routes.
- Light/dark mode with system-preference detection, persisted choice, and no flash-of-wrong-theme on load.
- An AI interview-prep assistant: a persistent chat widget (RAG-grounded in the user's latest resume/JD
  when available) for open-ended coaching questions, separate from the structured scored mock interview.
- Resume upload (PDF/DOCX) → text extraction → cleaning → chunking → embeddings → pgvector storage.
- JD upload/paste → same pipeline, tagged `document_type=jd`.
- Resume analysis: skills, education, experience, projects, certifications, achievements, gaps.
- ATS analysis: 0–100 score vs a specific JD, keyword match/miss, structure/readability issues.
- JD analysis: role, required/preferred skills, experience band, responsibilities, tech, keywords.
- Interview creation with full configuration (type/role/level/count/difficulty/mode).
- Turn-by-turn interview loop: ask → answer → immediate scored feedback → next (adaptive) question,
  including follow-up probing on weak answers and a difficulty ramp based on running performance.
- 6 interview types: HR, Technical, Aptitude, Behavioral, GD, Mixed.
- Per-answer evaluation (correctness, relevance, technical accuracy, completeness, communication).
- Aggregate scoring (per-question, per-category, overall) with a documented formula.
- Final report: overall score, strengths/weaknesses, question-by-question breakdown, study plan, tips.
- Performance history across interviews.
- Per-user data isolation everywhere (DB row-level ownership + query filters + vector metadata filter).
- Pluggable LLM layer (Anthropic / OpenAI / a rule-based mock for zero-config demo use) and pluggable
  embedding provider (local / OpenAI).
- Automatic, transparent fallback to demo-mode content (clearly labeled, never silent) when no LLM API
  key is configured, so the whole app runs end to end out of the box.

## 3. Tech Stack
- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic-style `create_all` bootstrap.
- **DB + Vector store**: PostgreSQL 15+ with the `pgvector` extension (one database, no separate vector service).
- **Auth**: `passlib[bcrypt]` for hashing, `python-jose` for JWT.
- **Document parsing**: `pypdf` (PDF), `python-docx` (DOCX).
- **Embeddings**: pluggable — `sentence-transformers` (local, free, default) or OpenAI `text-embedding-3-small`.
- **LLM**: pluggable — Anthropic Claude or OpenAI GPT, behind one `LLMProvider` interface.
- **Frontend**: React + Vite + Tailwind CSS, React Router, fetch-based API client, JWT stored in memory + refresh cookie pattern.
- **Infra**: Docker Compose (`api` + `postgres` with pgvector image).

## 4. System Architecture

```
[React SPA] --HTTPS--> [FastAPI]
                            |-- /auth        --> Auth service --> users table (bcrypt + JWT)
                            |-- /resumes     --> Document processor --> chunker --> embedder --> pgvector
                            |-- /jd          --> same pipeline, document_type=jd
                            |-- /ats         --> ATS analyzer (retrieval + LLM scoring, JSON schema)
                            |-- /interviews  --> Interview engine --> Retriever --> LLM (question gen)
                            |-- /answers     --> Evaluator --> LLM (structured eval) --> Scoring service
                            |-- /reports     --> Report generator --> aggregates DB rows --> LLM (narrative)
                            |
                      [Postgres + pgvector]  (users, documents, chunks+embeddings, interviews,
                                               questions, answers, feedback, reports)
```

Every table with user-owned data has a `user_id` foreign key with `ON DELETE CASCADE`; every query in the
service layer filters by the authenticated user's id — there is no endpoint that accepts an arbitrary
resource id without an ownership check (`services/authz.py::assert_owner`).

## 5. RAG Architecture (detail)

1. **Extract**: `pypdf`/`python-docx` pull raw text from the uploaded file (validated by content-sniffing,
   not just extension, and size-capped).
2. **Clean/normalize**: strip control chars, collapse whitespace, de-hyphenate line-wrapped words, drop
   boilerplate (page numbers, repeated headers).
3. **Chunk**: sentence-aware recursive splitter, ~250–400 tokens per chunk with ~15% overlap, chunk
   metadata = `{user_id, document_id, document_type, section_hint}`.
4. **Embed**: `EmbeddingProvider.embed(texts) -> list[vector]`; vectors stored in `document_chunks.embedding`
   (`pgvector` column, cosine distance index `ivfflat`).
5. **Retrieve**: for a given need (e.g. "generate next technical question"), build a query string from the
   interview config + conversation state, embed it, run `SELECT ... ORDER BY embedding <=> :q LIMIT k`
   **filtered by `user_id` and `document_type`** — this is the isolation boundary, enforced in SQL, not
   just in application logic.
6. **Augment**: retrieved chunks + retrieved "already-asked questions" (to avoid repeats) + interview
   config are assembled into a structured prompt.
7. **Generate**: LLM produces the next question (or an evaluation) as **strict JSON**, validated against a
   Pydantic schema before being trusted; on validation failure the service retries once with the error fed
   back to the model, then falls back to a template question.
8. **Ground**: the interviewer prompt explicitly instructs the model to only assert resume facts that
   appear in the retrieved context, and to say "general knowledge question" vs "based on your resume" in
   its internal tags so the UI can label which is which.

## 6. Database Schema (see `backend/app/models/*.py` for SQLAlchemy source of truth)

- `users(id, email UNIQUE, hashed_password, full_name, created_at)`
- `documents(id, user_id FK, type[resume|jd], filename, raw_text, parsed_json, status, created_at)`
- `document_chunks(id, document_id FK, user_id FK, content, embedding VECTOR(384|1536), chunk_index, metadata JSONB)`
- `ats_reports(id, user_id FK, resume_document_id FK, jd_document_id FK, score, matching_keywords JSONB, missing_keywords JSONB, strengths JSONB, weaknesses JSONB, suggestions JSONB, created_at)`
- `interviews(id, user_id FK, resume_document_id FK NULL, jd_document_id FK NULL, type, target_role, experience_level, difficulty, mode, num_questions, status[in_progress|completed], overall_score, created_at, completed_at)`
- `questions(id, interview_id FK, index, category, text, difficulty, source[resume|jd|general|followup], grounding_chunk_ids JSONB, created_at)`
- `answers(id, question_id FK, interview_id FK, user_id FK, text, submitted_at)`
- `feedback(id, answer_id FK UNIQUE, score, correctness, relevance, technical_accuracy, completeness, communication, strengths JSONB, weaknesses JSONB, suggestions JSONB, sample_answer, created_at)`
- `reports(id, interview_id FK UNIQUE, overall_score, category_scores JSONB, strongest_areas JSONB, weakest_areas JSONB, common_mistakes JSONB, study_plan JSONB, tips JSONB, next_difficulty, resume_alignment_notes, created_at)`
- `assistant_messages(id, user_id FK, role[user|assistant], content, created_at)` — the AI coaching
  assistant's chat history, isolated per user; intentionally separate from the scored interview tables
  since it's free-form coaching, not a graded interview turn.

All FKs cascade on delete; `document_chunks`, `answers`, `questions` all carry (directly or via join)
`user_id` so authorization checks never need more than one indexed filter.

## 7. API Design (summary — see `backend/app/api/routes/*.py`)

```
POST   /auth/register
POST   /auth/login
POST   /auth/refresh
POST   /auth/logout

POST   /resumes                 (multipart upload)
GET    /resumes/{id}
GET    /resumes/{id}/analysis
DELETE /resumes/{id}

POST   /job-descriptions        (file OR raw text)
GET    /job-descriptions/{id}
GET    /job-descriptions/{id}/analysis

POST   /ats/analyze             {resume_id, jd_id}
GET    /ats/{id}

POST   /interviews              {config...} -> creates interview, returns interview_id
GET    /interviews
GET    /interviews/{id}
POST   /interviews/{id}/next-question   -> returns the next question (generates if needed)
POST   /interviews/{id}/answers         {question_id, text} -> returns immediate feedback
POST   /interviews/{id}/complete        -> finalizes, triggers report generation
GET    /interviews/{id}/report

GET    /me/performance-history

GET    /assistant/messages          -> full chat history for this user
POST   /assistant/messages          {message} -> assistant's reply, RAG-grounded if resume/JD exist
```

Every route (except `/auth/register`, `/auth/login`) requires `Authorization: Bearer <access_token>` and
resolves `current_user` via a dependency; handlers never trust a `user_id` in the request body.

## 8. Authentication Design
- Passwords hashed with bcrypt (`passlib`), never logged, never returned.
- On login: short-lived JWT access token (15 min, returned in the JSON body, kept in memory only on
  the frontend — never persisted, so a page reload always re-derives it) + longer-lived refresh token
  (7 days, set as an **httpOnly, SameSite=Lax cookie** scoped to `/auth`, never exposed to JS). Every
  token carries a unique `jti` claim (a hook for a future server-side revocation denylist) in addition
  to `sub`/`type`/`iat`/`exp`.
- `/auth/refresh` reads the refresh token from the cookie (not the request body) and **rotates** it —
  every successful refresh sets a new cookie value, so a stolen-but-superseded cookie value stops working.
- `get_current_user` dependency decodes+verifies the JWT, loads the user, 401s on any failure.
- `/auth/login` and `/auth/register` are rate-limited (10/min and 5/min respectively, per client IP, via
  `slowapi`) to blunt credential-stuffing and account-enumeration attempts.
- CORS is locked to `FRONTEND_ORIGIN` with `allow_credentials=True` (required for the cookie to be sent
  cross-origin between the Vite dev server and the API in local development).

## 9. Frontend Structure
```
frontend/src/
  api/client.js            fetch wrapper, attaches auth header, handles 401 -> cookie-based refresh
  context/AuthContext.jsx  login/register/logout state
  context/ThemeContext.jsx light/dark mode, persisted + system-preference default
  pages/
    Login.jsx / Register.jsx
    Dashboard.jsx
    ResumeUpload.jsx
    JobDescription.jsx
    AtsReport.jsx
    InterviewSetup.jsx
    InterviewChat.jsx
    InterviewReport.jsx
    PerformanceHistory.jsx
  components/
    Navbar.jsx (includes the theme toggle), ProtectedRoute.jsx, ScoreBadge.jsx, ProgressBar.jsx,
    FeedbackPanel.jsx, QuestionCard.jsx, FileDropzone.jsx, AiAssistant.jsx (floating chat widget)
```

Dark mode is implemented via Tailwind's `class` strategy plus CSS custom properties: color tokens
(`ink`, `slate`, `canvas`, `surface`, `border`, `accentSoft`) are defined as `rgb(var(--...) / <alpha-value>)`
in `tailwind.config.js` and given light/dark values in `index.css` under `:root` / `.dark`. This means
components use ordinary utility classes (`bg-surface`, `text-ink`, `border-border/10`) and get correct
theming for free — no `dark:` variant needed on every element. A small inline script in `index.html`
applies the `dark` class before React mounts, avoiding a flash of the wrong theme on load.

## 10. Backend Folder Structure
```
backend/
  app/
    core/       config.py, security.py, deps.py, prompts.py
    db/         base.py, init_db.py
    models/     user.py, document.py, interview.py
    schemas/    (Pydantic request/response models, mirrors models/)
    llm/        base.py, anthropic_provider.py, openai_provider.py, factory.py
    services/   document_processor.py, embeddings.py, vector_store.py, rag_pipeline.py,
                ats_analyzer.py, jd_analyzer.py, interview_engine.py, evaluator.py,
                scoring.py, report_generator.py, authz.py
    api/        router.py, routes/*.py
    main.py
  requirements.txt
  docker-compose.yml
  .env.example
```

## 11. AI Prompt Design (see `backend/app/core/prompts.py`)
Two system prompt families:
1. **Interviewer** — receives: interview config, retrieved resume/JD chunks (labeled), prior Q&A summary,
   category. Instructed to output strict JSON `{question, category, difficulty, source, grounded_on}` and
   to never state a resume fact not present in the provided chunks; if no relevant chunk exists it must
   fall back to a general-knowledge question and set `source="general"`.
2. **Evaluator** — receives: the question, the answer, the grounding chunks, interview type. Instructed to
   output strict JSON matching the `Feedback` schema, referencing the specific answer content (the prompt
   forbids generic boilerplate feedback and requires at least one direct reference to the candidate's
   wording).
A third, lighter prompt generates the final narrative sections of the report from the aggregated
structured data (never re-deriving scores — scores are computed in Python, not by the LLM).

**Adaptivity** (`services/interview_engine.py`) is not just prompt-level — the routing decisions are made
in Python and then instructed to the LLM, so they hold even if the model ignores the instruction:
- **Follow-up detection**: after each answer, if the previous question was in a follow-up-eligible
  category (HR, Technical, Behavioral — not Aptitude/GD, which are self-contained), scored below 55, and
  the evaluator identified a specific weakness, the next turn is forced into a follow-up on that exact gap
  rather than rotating to a new topic. A follow-up is never chained twice in a row — one probe, then move
  on regardless of the follow-up's outcome.
- **Difficulty ramp**: rather than asking every question at the interview's configured starting difficulty,
  each question's difficulty is recomputed from the running average of scores so far
  (`services/scoring.py::suggest_next_difficulty`) — a strong run escalates toward `hard`, a weak run eases
  toward `easy`.
- Both decisions are made before the LLM call and passed in as instructions; the persisted `Question.source`
  is set from the Python decision (not blindly trusted from the LLM's response) specifically so the
  no-chained-follow-ups guarantee can't be defeated by the model forgetting to echo `source="followup"`.

## 12. Scoring Methodology
- Each answer gets 5 sub-scores (0–100): correctness, relevance, technical_accuracy, completeness,
  communication. `technical_accuracy` is weighted 0 for HR/Behavioral/GD categories.
- Per-question score = weighted average, weights depend on interview type (see `services/scoring.py`
  `WEIGHTS` table) — e.g. Technical: correctness .35, technical_accuracy .30, completeness .15,
  relevance .10, communication .10; HR/Behavioral: relevance .30, communication .30, completeness .20,
  correctness .20, technical_accuracy 0.
- Category score = mean of that category's question scores.
- Overall interview score = mean of per-question scores (not category scores, so question count per
  category doesn't need to be balanced).
- All formulas are pure Python, unit-testable, and returned in the report response so the UI can show
  "how this was calculated."

## 13. Step-by-Step Implementation Plan
1. Bootstrap FastAPI app, config, DB connection, `pgvector` extension creation.
2. Models + `create_all` bootstrap (or Alembic in production).
3. Auth (register/login/refresh/current-user dependency) + tests.
4. Document upload + extraction + chunking + embedding + storage; per-user isolation tests.
5. Retrieval service + resume/JD analysis (structured LLM call over retrieved chunks).
6. ATS analyzer.
7. Interview creation + question-generation loop (RAG + LLM, JSON-validated).
8. Answer submission + evaluator + scoring.
9. Interview completion + report generator.
10. Performance history endpoint.
11. Frontend: auth pages → dashboard → upload → setup → chat → report → history.
12. Hardening pass: file validation, rate limits, error handling, logging without secrets.

## 14. Testing Strategy
Implemented in `backend/tests/` (run with `pytest` from `backend/`):
- **Unit**: password hashing/JWT (`test_security.py`), chunking (`test_chunking.py`), scoring formulas
  including the weight-sum-to-1.0 guard (`test_scoring.py`), the LLM-JSON validator's retry-on-malformed
  path (`test_llm_json.py`), file upload validation via magic-byte sniffing (`test_document_processor.py`).
- **Service-level**: adaptive question generation, including the follow-up-on-weak-answer logic and
  running-average difficulty adjustment (`test_interview_engine.py`); answer evaluation and its scoring
  integration (`test_evaluator.py`); report generation and its narrative fallback (`test_report_generator.py`).
  These use a `FakeLLMProvider` (canned JSON responses) — no real API calls in the test suite.
- **Isolation / security**: cross-user access to documents and interviews returns 404 (never 403), both at
  the service layer and through the live API with two real registered users (`test_isolation.py`).
- **Auth API**: register/login/refresh/duplicate-email/wrong-password/expired-or-garbage-token paths
  (`test_auth_api.py`).
- **Integration (Postgres+pgvector required)**: `test_vector_store.py` exercises the real vector store and
  its per-user isolation guarantee; it's automatically skipped unless `TEST_DATABASE_URL` is set, so the
  default `pytest` run never requires Docker.

Fast tests (everything except `test_vector_store.py`) run against an in-memory SQLite database. Because
`sqlalchemy.dialects.postgresql.UUID(as_uuid=True)` behaves differently under SQLite (it requires bind
values to already be `uuid.UUID` instances, breaking on plain strings like a JWT subject claim), all
models use a portable `GUID` `TypeDecorator` (`app/db/types.py`) instead: native `uuid` on Postgres,
`CHAR(32)` on everything else, with a uniform `uuid.UUID` interface either way. The Alembic migration
still uses Postgres's native UUID type directly, since that's the real production schema.

## 15. Security Checklist
- [x] Passwords bcrypt-hashed, never logged/returned.
- [x] JWT access (in-memory on the client) + rotating refresh token in an httpOnly, SameSite=Lax cookie.
- [x] `/auth/login` and `/auth/register` rate-limited per client IP.
- [x] Every protected route behind `get_current_user`.
- [x] Every DB query scoped by `user_id`; ownership re-checked in the service layer, not just the route.
- [x] File type validated by magic-byte sniffing + extension; size cap enforced before reading into memory.
- [x] API keys read from environment only (`.env`, never committed; `.env.example` has placeholders only).
- [x] No API key or secret ever sent to the frontend.
- [x] CORS locked to the configured frontend origin.
- [x] Input validation via Pydantic on every endpoint.
- [x] Errors return generic messages to the client; details logged server-side only.
- [x] No fabricated ATS scores — analyzer always runs the real retrieval+LLM path or returns an explicit
      "insufficient data" state rather than a placeholder number.

## 16. Deployment Plan
- `docker-compose up` for local dev (Postgres w/ pgvector + API).
- Production: containerize API, run behind a reverse proxy (Nginx/Caddy) with TLS; managed Postgres with
  pgvector extension enabled (e.g. Supabase, Neon, or RDS + the pgvector extension); frontend built and
  served as static assets (Vercel/Netlify/S3+CloudFront) hitting the API's public URL; secrets injected via
  the platform's secret manager, never baked into the image.
