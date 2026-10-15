from abc import ABC, abstractmethod
from typing import List
import math
import hashlib
import re
import httpx
from app.core.config import settings

class EmbeddingProvider(ABC):
    """Abstract base class for text embedding generation."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the vector dimension of generated embeddings."""
        pass

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """Generate an embedding for a single search query."""
        pass

    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of document chunks."""
        pass

class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic, offline embedding provider for development and automated testing."""

    def __init__(self, dimension: int = 1536):
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    def _generate_vector(self, text: str) -> List[float]:
        """Generate a deterministic unit-normalized vector with semantic term hashing."""
        vec = [0.0] * self._dim
        if not text:
            vec[0] = 1.0
            return vec

        # Tokenize words to enable keyword-overlap semantic similarity
        words = re.findall(r"\w+", text.lower())
        if not words:
            words = [text.lower()]

        for i, word in enumerate(words):
            # Compute hash of word and positional weight
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dim
            # Higher weight for distinct words
            weight = 1.0 + (1.0 / (1.0 + math.log(1.0 + len(word))))
            vec[idx] += weight

            # Also spread a small harmonic frequency to adjacent indices for smoothing
            adj_idx = (idx + (h >> 8)) % self._dim
            vec[adj_idx] += 0.25 * weight

        # Apply L2 normalization
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        else:
            vec[0] = 1.0
        return vec

    async def embed_query(self, text: str) -> List[float]:
        return self._generate_vector(text)

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._generate_vector(t) for t in texts]

class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI Embeddings API client."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small", dimension: int = 1536):
        self.api_key = api_key
        self.model = model
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed_query(self, text: str) -> List[float]:
        res = await self.embed_documents([text])
        return res[0]

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if not self.api_key or self.api_key.startswith("sk-placeholder") or self.api_key == "sk-test":
            # Graceful fallback to mock if placeholder key is passed
            fallback = MockEmbeddingProvider(dimension=self._dim)
            return await fallback.embed_documents(texts)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": texts,
                    "model": self.model,
                },
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]

def get_embedding_provider() -> EmbeddingProvider:
    """Factory for selecting the active embedding provider based on configuration."""
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    app_env = getattr(settings, "APP_ENV", "development")
    
    # If in test mode, or if key is placeholder/empty, return MockEmbeddingProvider
    if app_env == "test" or not api_key or api_key.startswith("sk-placeholder") or api_key == "sk-test":
        return MockEmbeddingProvider(dimension=1536)

    return OpenAIEmbeddingProvider(api_key=api_key)
