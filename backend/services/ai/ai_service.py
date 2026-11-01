import logging
import re
import time
from typing import Iterable, Iterator, Optional

from .config import AI_MAX_RETRIES, AI_PROVIDERS, AI_RETRY_DELAY
from .providers.deepseek_provider import DeepSeekProvider
from .providers.gemini_provider import GeminiProvider
from .providers.groq_provider import GroqProvider

logger = logging.getLogger("codeguardian.ai")

PROVIDER_CLASSES = {
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "deepseek": DeepSeekProvider,
}

_SECRET_RE = re.compile(
    r"(AIza[0-9A-Za-z_\-]{20,}|gsk_[0-9A-Za-z]{20,}|sk-[0-9A-Za-z_\-]{16,}"
    r"|Bearer\s+\S+|(?i:key)=[^&\s]+)"
)


def _redact(text: str, limit: int = 300) -> str:
    """Raw provider messages may echo keys/URLs: strip them before logging."""
    return _SECRET_RE.sub("<redacted>", str(text))[:limit]


def _status_code(exc: Exception) -> Optional[int]:
    for holder in (exc, getattr(exc, "response", None)):
        for attr in ("status_code", "code"):
            value = getattr(holder, attr, None)
            if isinstance(value, int) and 100 <= value <= 599:
                return value
    return None


def classify_error(exc: Exception) -> tuple[str, bool, Optional[int]]:
    """Return (category, retryable, http_status).

    Retry only what can fix itself (timeouts, 5xx, empty reply). Auth, billing,
    quota/rate-limit and missing-model errors will not change in 1.5 seconds,
    so we move straight to the next provider instead of wasting time.
    """
    status = _status_code(exc)
    text = f"{type(exc).__name__} {exc}".lower()

    if status in (401, 403) or any(k in text for k in ("unauthorized", "permission denied", "api_key_invalid", "invalid api key", "api key not valid")):
        return "authentication failed", False, status
    if status == 402 or any(k in text for k in ("insufficient balance", "billing", "payment required")):
        return "billing or credits exhausted", False, status
    if status == 429 or any(k in text for k in ("quota", "rate limit", "rate_limit", "resource_exhausted")):
        return "quota or rate limit", False, status
    if status == 404 or any(k in text for k in ("model not found", "not_found", "decommissioned", "does not exist")):
        return "model not found", False, status
    if status == 400:
        return "bad request", False, status
    if "timeout" in text or "timed out" in text:
        return "timeout", True, status
    if (status is not None and status >= 500) or any(k in text for k in ("overloaded", "unavailable", "internal error")):
        return "provider unavailable", True, status
    if "empty response" in text:
        return "empty response", True, status
    return "unknown error", True, status


class AIProviderError(Exception):
    """Raised when every AI provider fails (or none is left to try).

    `attempts` holds one dict per failure: provider, category, retryable, status.
    `summary` is safe to put in an API response (no raw provider messages).
    """

    def __init__(self, message: str = "", attempts: Optional[list[dict]] = None):
        super().__init__(message)
        self.attempts = attempts or []

    @property
    def summary(self) -> str:
        latest: dict[str, str] = {}
        for a in self.attempts:
            label = a["category"] + (f" (HTTP {a['status']})" if a.get("status") else "")
            latest[a["provider"]] = label
        return "; ".join(f"{p}: {c}" for p, c in latest.items())


class AIService:
    def __init__(self, provider_names: Optional[list[str]] = None):
        requested = provider_names or AI_PROVIDERS
        unknown = [n for n in requested if n not in PROVIDER_CLASSES]
        if unknown:
            logger.warning(
                "Ignoring unknown AI provider(s) %s. Supported: %s",
                unknown, sorted(PROVIDER_CLASSES),
            )
        self.provider_names = [n for n in requested if n in PROVIDER_CLASSES]
        self._providers = {}

    def _get_provider(self, name: str):
        if name in self._providers:
            return self._providers[name]

        provider_class = PROVIDER_CLASSES.get(name)
        if provider_class is None:
            raise ValueError(f"Unknown AI provider: {name}")

        provider = provider_class()
        self._providers[name] = provider
        return provider

    def generate_with_info(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        skip: Optional[Iterable[str]] = None,
    ) -> tuple[str, str]:
        """Return (text, provider_name) from the first provider that succeeds.

        `skip` lets a caller exclude providers whose output it already rejected
        (e.g. unparsable reply), so the next call really falls back to another one.
        """
        skipped = set(skip or ())
        attempts: list[dict] = []
        details: list[str] = []

        for name in self.provider_names:
            if name in skipped:
                continue

            try:
                provider = self._get_provider(name)
            except Exception as e:
                logger.warning("Provider %s unavailable: %s", name, _redact(e))
                attempts.append({"provider": name, "category": "not configured", "retryable": False, "status": None})
                details.append(f"{name}: not configured ({_redact(e, 120)})")
                continue

            for attempt in range(1, AI_MAX_RETRIES + 1):
                try:
                    result = provider.generate(prompt, system_prompt)
                    logger.info("AI response generated by %s", name)
                    return result, name
                except Exception as e:
                    category, retryable, status = classify_error(e)
                    logger.warning(
                        "%s failed (attempt %d/%d) [%s%s]: %s: %s",
                        name, attempt, AI_MAX_RETRIES, category,
                        f", HTTP {status}" if status else "", type(e).__name__, _redact(e),
                    )
                    attempts.append({"provider": name, "category": category, "retryable": retryable, "status": status})
                    details.append(f"{name}: {category}")
                    if not retryable:
                        break
                    if attempt < AI_MAX_RETRIES:
                        time.sleep(AI_RETRY_DELAY * attempt)

        if not attempts:
            raise AIProviderError("No AI provider left to try", attempts)

        logger.error("All AI providers failed: %s", " | ".join(details))
        raise AIProviderError("All AI providers failed: " + " | ".join(details), attempts)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        return self.generate_with_info(prompt, system_prompt)[0]

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Iterator[str]:
        """
        Fallback sirf tab hota hai jab provider pehla token dene se pehle fail ho.
        Agar beech stream me fail ho jaye to dusre provider pe switch nahi karte
        (warna answer aadha-aadha mix ho jayega).
        """
        attempts: list[dict] = []
        details: list[str] = []

        for name in self.provider_names:
            started = False
            try:
                provider = self._get_provider(name)
                logger.info("Streaming with %s", name)

                for token in provider.stream(prompt, system_prompt):
                    started = True
                    yield token
                return

            except Exception as e:
                category, retryable, status = classify_error(e)
                logger.warning("%s stream failed [%s]: %s", name, category, _redact(e))
                attempts.append({"provider": name, "category": category, "retryable": retryable, "status": status})
                details.append(f"{name}: {category}")

                if started:
                    raise AIProviderError(
                        f"{name} failed mid-stream: {category}", attempts
                    ) from e

        logger.error("All AI providers failed (stream): %s", " | ".join(details))
        raise AIProviderError("All AI providers failed: " + " | ".join(details), attempts)
