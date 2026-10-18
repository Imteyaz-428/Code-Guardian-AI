import os

from backend.core.config import settings

# Order matters: pehla = primary, baaki = fallback.
# .env me CODE_GUARDIAN_AI_PROVIDERS=gemini,groq,deepseek (core/config.py isko padhta hai)
AI_PROVIDERS = settings.AI_PROVIDERS

AI_MAX_RETRIES = int(os.getenv("AI_MAX_RETRIES", "2"))
AI_RETRY_DELAY = float(os.getenv("AI_RETRY_DELAY", "1.5"))