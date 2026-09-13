# AI Mock Interview Platform


This project is a full-stack AI interview preparation platform built to help job seekers practice interviews with real, personalized feedback.

Users upload their resume, optionally add a job description, and the app turns that information into a guided mock interview experience. Instead of generic AI questions, the app retrieves relevant context from the user’s actual resume and job requirements and uses that to generate adaptive interview questions, evaluate answers, and provide actionable improvement suggestions.

This project combines AI, retrieval, scoring, and web application development into a complete product-like workflow that feels like a real interview coaching tool.

## Why this project matters

Most interview prep tools are either static question banks or generic chatbots. This project goes further by making the interview experience personalized:

- it uses the candidate’s actual resume as input
- it aligns questions to a target job role
- it checks how well the candidate matches the role
- it adapts difficulty and follow-up questions based on performance
- it gives structured feedback instead of vague AI responses

## Features

- Resume upload and parsing (PDF/DOCX)
- Optional job description upload or paste
- ATS-style analysis against a target job description
- AI-powered mock interview flow
- Adaptive question generation based on previous answers
- Real-time answer evaluation and scoring
- Final interview report with strengths, weak areas, and improvement tips
- Persistent AI coaching assistant for follow-up questions
- Light/dark mode
- Authenticated user flows with protected routes and cookie-based refresh
- Demo mode that works without API keys when using the mock provider

## Tech stack

- Backend: Python, FastAPI, SQLAlchemy, PostgreSQL + pgvector
- Frontend: React, Vite, Tailwind CSS
- LLM: Anthropic / OpenAI integration with a mock fallback provider
- Embeddings: local sentence-transformers or OpenAI embeddings
- Data layer: PostgreSQL with vector search support

## Project structure

```text
.
├── backend/
│   ├── app/
│   ├── migrations/
│   ├── tests/
│   ├── requirements.txt
│   ├── docker-compose.yml
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── ARCHITECTURE.md
├── README.md
├── RESUME.md
└── .gitignore
```

## Quick start

### Option 1: Docker

```bash
cd backend
copy .env.example .env
docker compose up --build
```

This starts the API and Postgres/pgvector setup automatically. The backend API runs on:

- http://localhost:8000
- Swagger docs: http://localhost:8000/docs

### Option 2: Local development

#### Backend

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

#### Frontend

Open a second terminal and run:

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on:

- http://localhost:5173

## Environment configuration

The backend expects a `.env` file based on `.env.example`.

At minimum, configure:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `LLM_PROVIDER`
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` if using a real provider
- `EMBEDDING_PROVIDER`

If no API keys are configured, the app can still run in demo/mock mode.

## Demo mode

A mock LLM provider is included so the app can work without API credentials. This lets you explore the full interview flow, upload documents, generate ATS insights, and test the coaching experience without setting up external services.

## Development notes

- The backend is built with FastAPI and structured routing for auth, resume/JD handling, ATS analysis, interviews, reports, and assistant chat.
- The system stores embeddings and retrieved context in PostgreSQL via pgvector.
- The app enforces user-level data isolation so one user cannot access another user’s documents or interview history.
- The architecture details and design decisions are documented in [ARCHITECTURE.md](ARCHITECTURE.md).

## Testing

```bash
cd backend
pip install -r requirements.txt
pytest
```

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — system design, RAG flow, scoring logic, auth model, and architecture notes
- [RESUME.md](RESUME.md) — resume/portfolio-focused summary for showcasing the project

## License

This project is intended for educational and portfolio use. Add a license file if you plan to publish it publicly.


## Contributing

Pull requests and improvements are welcome. If you plan to extend the app, consider adding:

- stronger validation for uploaded documents
- improved interview analytics
- CI/CD workflow improvements
- production-grade deployment setup
- Redis-backed rate limiting for multi-instance deployments

## Status

This project is a working AI interview assistant and portfolio-ready application with full-stack functionality, built to demonstrate practical use of generative AI, retrieval, scoring, and interview simulation.

## Demo

The app can run entirely in demo mode without external API keys, making it easy to showcase the full interview workflow locally. This is especially useful for portfolio demos, internal reviews, and early feature validation.

## Project outcome

The goal of this project is to turn resume-driven preparation into a guided, intelligent interview experience: upload a resume, match it against a target role, simulate interviews, evaluate responses, and provide structured next steps for improvement.

