from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import settings


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def embed_one(self, text: str) -> list[float]:
        raise NotImplementedError


class LocalEmbeddingProvider(EmbeddingProvider):
    """Free, offline embeddings via sentence-transformers. No API key required."""

    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL_LOCAL)

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [v.tolist() for v in vectors]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self):
        from openai import OpenAI
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_EMBEDDING_MODEL

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    if settings.EMBEDDING_PROVIDER == "openai":
        return OpenAIEmbeddingProvider()
    return LocalEmbeddingProvider()
