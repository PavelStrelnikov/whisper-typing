import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a speech-to-text post-processor. Clean up the transcribed text:\n"
    "- Fix grammar and sentence structure\n"
    "- Remove filler words, false starts, repetitions, stammering\n"
    "- Keep the original meaning and tone\n"
    "- Keep the same language as the input\n"
    "- Return ONLY the cleaned text, nothing else"
)


class TextNormalizer(ABC):
    @abstractmethod
    def normalize(self, raw_text: str, language: Optional[str] = None) -> str:
        ...


class OpenAINormalizer(TextNormalizer):
    """Text normalization using OpenAI GPT."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)

    def normalize(self, raw_text: str, language: Optional[str] = None) -> str:
        self._ensure_client()

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": raw_text},
        ]

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=len(raw_text) * 2 + 100,
        )

        result = response.choices[0].message.content.strip()
        logger.info(f"Normalized ({self.model}): '{raw_text[:60]}...' → '{result[:60]}...'")
        return result


class GeminiNormalizer(TextNormalizer):
    """Text normalization using Google Gemini."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)

    def normalize(self, raw_text: str, language: Optional[str] = None) -> str:
        self._ensure_client()

        prompt = f"{SYSTEM_PROMPT}\n\n{raw_text}"

        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        result = response.text.strip()
        logger.info(f"Normalized ({self.model}): '{raw_text[:60]}...' → '{result[:60]}...'")
        return result


def create_normalizer(
    provider: str,
    openai_api_key: str = "",
    openai_model: str = "gpt-4o-mini",
    gemini_api_key: str = "",
    gemini_model: str = "gemini-2.0-flash",
) -> Optional[TextNormalizer]:
    """Factory: create the right normalizer based on provider setting."""
    if provider == "openai":
        if not openai_api_key:
            logger.warning("OpenAI API key not set, normalizer unavailable")
            return None
        return OpenAINormalizer(api_key=openai_api_key, model=openai_model)
    elif provider == "gemini":
        if not gemini_api_key:
            logger.warning("Gemini API key not set, normalizer unavailable")
            return None
        return GeminiNormalizer(api_key=gemini_api_key, model=gemini_model)
    else:
        logger.warning(f"Unknown normalizer provider: {provider}")
        return None
