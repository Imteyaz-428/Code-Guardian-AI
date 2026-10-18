import os
from typing import Iterator, Optional

from dotenv import load_dotenv

from .base_provider import BaseProvider, build_messages

load_dotenv()


class DeepSeekProvider(BaseProvider):
    name = "deepseek"

    def __init__(self, model: Optional[str] = None):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is missing")

        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=build_messages(prompt, system_prompt),
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("DeepSeek returned an empty response")
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