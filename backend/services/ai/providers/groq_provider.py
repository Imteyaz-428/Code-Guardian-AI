import os
from typing import Iterator, Optional

from dotenv import load_dotenv

from .base_provider import BaseProvider, build_messages

load_dotenv()


class GroqProvider(BaseProvider):
    name = "groq"

    def __init__(self, model: Optional[str] = None):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is missing")

        from groq import Groq

        self.client = Groq(api_key=api_key)
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=build_messages(prompt, system_prompt),
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Groq returned an empty response")
        return content

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Iterator[str]:
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=build_messages(prompt, system_prompt),
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content