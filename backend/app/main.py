import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.limiter import limiter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_interview_platform")

app = FastAPI(title="AI Mock Interview Platform", version="1.0.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NOTE: schema is managed by Alembic (see backend/migrations). Run
# `alembic upgrade head` before starting the app (docker-compose does this
# automatically via the `api` service command). We intentionally do NOT
# call Base.metadata.create_all() here in production — that's dev-only,
# available via `python -m app.db.init_db` for a quick local smoke test.


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never leak internals (stack traces, secrets) to the client; log server-side only.
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(status_code=500, content={"detail": "An internal error occurred."})


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(api_router)
