from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/ai_interview"

    JWT_SECRET_KEY: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_COOKIE_NAME: str = "refresh_token"
    # Cookies must be Secure over HTTPS in production. Defaults to False so local
    # http://localhost dev works out of the box; set COOKIE_SECURE=true in production.
    COOKIE_SECURE: bool = False

    LLM_PROVIDER: str = "anthropic"  # "anthropic" | "openai" | "mock"
    # If LLM_PROVIDER is "anthropic"/"openai" but the matching API key is empty, the app
    # automatically falls back to the "mock" provider (template content, clearly labeled as such)
    # instead of failing every AI-dependent request -- see app/llm/factory.py.
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    EMBEDDING_PROVIDER: str = "local"  # "local" | "openai"
    EMBEDDING_MODEL_LOCAL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM_LOCAL: int = 384
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_EMBEDDING_DIM: int = 1536

    MAX_UPLOAD_MB: int = 8
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # slowapi/limits storage backend for rate limiting. Defaults to in-memory, which is fine for
    # a single-process deployment but does NOT share limits across multiple workers/instances.
    # Set to a Redis URI (e.g. "redis://localhost:6379") in any multi-process production deployment.
    RATE_LIMIT_STORAGE_URI: str = "memory://"

    @property
    def embedding_dim(self) -> int:
        return self.EMBEDDING_DIM_LOCAL if self.EMBEDDING_PROVIDER == "local" else self.OPENAI_EMBEDDING_DIM


settings = Settings()
