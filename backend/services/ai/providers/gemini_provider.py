import os
from typing import Iterator, Optional

from dotenv import load_dotenv

from .base_provider import BaseProvider

load_dotenv()


class GeminiProvider(BaseProvider):
    name = "gemini"

    def __init__(self, model: Optional[str] = None):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing")

        from google import genai
        from google.genai import types

        self._types = types
        self.client = genai.Client(api_key=api_key)
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def _config(self, system_prompt: Optional[str]):
        if not system_prompt:
            return None
        return self._types.GenerateContentConfig(system_instruction=system_prompt)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=self._config(system_prompt),
        )
        if not response.text:
            raise RuntimeError("Gemini returned an empty response")
        return response.text

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Iterator[str]:
        response = self.client.models.generate_content_stream(
            model=self.model,
            contents=prompt,
            config=self._config(system_prompt),
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text