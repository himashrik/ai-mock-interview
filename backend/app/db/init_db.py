# --- Database bootstrap ---
# For quick local dev/testing without Alembic, this create_all-based bootstrap still works,
# but the source of truth for schema is now `migrations/` (Alembic). Prefer:
#   alembic upgrade head
from sqlalchemy import text

from app.db.base import Base, engine

# Import all models so they're registered on Base.metadata before create_all.
from app.models import user, document, interview, assistant, revoked_token  # noqa: F401


def init_db() -> None:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database initialized (pgvector extension + tables created).")
