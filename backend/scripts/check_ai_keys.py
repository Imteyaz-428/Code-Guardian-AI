"""Quick AI provider health check.

Create this file at:  backend/scripts/check_ai_keys.py   (also create an empty backend/scripts/__init__.py)
Run from the project root (Code-Guadian-AI/):

    python -m backend.scripts.check_ai_keys

Sends one tiny prompt to each provider and prints the real reason for any failure.
Keys are never printed in full.
"""
import os

from backend.core.config import settings  # loads backend/.env
from backend.services.ai.ai_service import PROVIDER_CLASSES, classify_error

HINTS = {
    "authentication failed": "Key is invalid/revoked/wrong type. Create a NEW key and paste it in backend/.env.",
    "billing or credits exhausted": "Account has no balance. Top up, or remove this provider.",
    "quota or rate limit": "Free-tier limit hit. Wait, or use another key/model.",
    "model not found": "Model name is wrong/retired. Fix the *_MODEL value in .env.",
}


def mask(value: str) -> str:
    return f"{value[:4]}...{value[-3:]} (len {len(value)})" if value else "MISSING"


def main() -> None:
    print("Provider order:", settings.AI_PROVIDERS)
    for name in settings.AI_PROVIDERS:
        env_key = f"{name.upper()}_API_KEY"
        print(f"\n[{name}] {env_key} = {mask(os.getenv(env_key, ''))}")
        cls = PROVIDER_CLASSES.get(name)
        if cls is None:
            print("  -> unsupported provider name, remove it from CODE_GUARDIAN_AI_PROVIDERS")
            continue
        try:
            provider = cls()
            print("  model:", provider.model)
            out = provider.generate("Reply with the single word: OK")
            print("  OK ->", out.strip()[:40])
        except Exception as exc:
            category, _, status = classify_error(exc)
            print(f"  FAILED: {category} (HTTP {status})")
            print("  raw:", str(exc)[:200].replace(os.getenv(env_key, "x#x"), "<key>"))
            if category in HINTS:
                print("  fix:", HINTS[category])


if __name__ == "__main__":
    main()