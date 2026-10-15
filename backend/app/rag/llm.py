from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import httpx
import re
from app.core.config import settings

class LLMProvider(ABC):
    """Abstract base class for Large Language Model text generation."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier."""
        pass

    @abstractmethod
    async def generate_answer(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a response for a prompt with optional system prompt."""
        pass

class MockLLMProvider(LLMProvider):
    """Mock LLM provider generating grounded, citation-aware responses offline."""

    def __init__(self, model_name: str = "mock-llm-rag"):
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate_answer(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        # Extract question and context from prompt if present
        question_match = re.search(r"Question:\s*(.+?)(?:\n|$)", prompt, re.IGNORECASE)
        question = question_match.group(1).strip() if question_match else "your question"

        # Check if context was provided in prompt
        context_match = re.search(r"Context:\s*([\s\S]+?)(?:\n\nQuestion:|$)", prompt, re.IGNORECASE)
        context = context_match.group(1).strip() if context_match else ""

        if not context or "No relevant context found" in context:
            return f"I could not find specific documentation answering '{question}'. Please refer to your organization's internal handbook."

        # Synthesize a clear, grounded response with document citations
        # Extract snippet summaries from context
        snippets = [s.strip() for s in context.split("\n\n---\n\n") if s.strip()]
        if not snippets:
            snippets = [context]

        response_paragraphs = []
        response_paragraphs.append(f"Based on the provided organizational policies regarding '{question}':")
        
        for i, snippet in enumerate(snippets[:3]):
            # Clean snippet header if present
            cleaned_snip = re.sub(r"^\[Source:[^\]]+\]\s*", "", snippet).strip()
            # Extract first 1-2 key sentences
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned_snip) if s.strip()]
            key_info = " ".join(sentences[:2]) if sentences else cleaned_snip[:200]
            response_paragraphs.append(f"• {key_info}")

        response_paragraphs.append("Please verify any specific departmental exceptions with your team supervisor or HR representative.")
        return "\n\n".join(response_paragraphs)

class OpenAILLMProvider(LLMProvider):
    """OpenAI Chat Completions API provider."""

    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini", temperature: float = 0.1):
        self.api_key = api_key
        self._model_name = model_name
        self.temperature = temperature

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate_answer(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.api_key or self.api_key.startswith("sk-placeholder") or self.api_key == "sk-test":
            mock = MockLLMProvider(model_name=f"mock-{self._model_name}")
            return await mock.generate_answer(prompt, system_prompt)

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model_name,
                    "messages": messages,
                    "temperature": self.temperature,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

def get_llm_provider() -> LLMProvider:
    """Factory for obtaining the configured LLM provider."""
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    app_env = getattr(settings, "APP_ENV", "development")

    if app_env == "test" or not api_key or api_key.startswith("sk-placeholder") or api_key == "sk-test":
        return MockLLMProvider()

    return OpenAILLMProvider(api_key=api_key)
