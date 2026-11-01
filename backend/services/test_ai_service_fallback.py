import pytest

import importlib

# `backend.services.ai.ai_service` the package attribute is the AIService instance,
# so load the module itself to patch its globals.
svc = importlib.import_module("backend.services.ai.ai_service")
AIProviderError, AIService, classify_error = svc.AIProviderError, svc.AIService, svc.classify_error


class _HttpError(Exception):
    def __init__(self, status, msg="boom"):
        super().__init__(msg)
        self.status_code = status


def _provider(behaviour, calls, name):
    class P:
        def __init__(self):
            pass

        def generate(self, prompt, system_prompt=None):
            calls.append(name)
            result = behaviour()
            return result

    return P


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(svc.time, "sleep", lambda *_: None)
    monkeypatch.setattr(svc, "AI_MAX_RETRIES", 2)


def _install(monkeypatch, **providers):
    monkeypatch.setattr(svc, "PROVIDER_CLASSES", providers)


@pytest.mark.parametrize("exc,category,retryable", [
    (_HttpError(401), "authentication failed", False),
    (_HttpError(402, "Insufficient Balance"), "billing or credits exhausted", False),
    (_HttpError(429), "quota or rate limit", False),
    (_HttpError(404), "model not found", False),
    (_HttpError(503), "provider unavailable", True),
    (TimeoutError("request timed out"), "timeout", True),
    (RuntimeError("Gemini returned an empty response"), "empty response", True),
    (RuntimeError("something odd"), "unknown error", True),
])
def test_classify_error(exc, category, retryable):
    got_category, got_retryable, _ = classify_error(exc)
    assert (got_category, got_retryable) == (category, retryable)


def test_permanent_error_is_not_retried_and_next_provider_is_used(monkeypatch):
    calls = []

    def bad():
        raise _HttpError(429, "quota exceeded")

    _install(monkeypatch, a=_provider(bad, calls, "a"), b=_provider(lambda: "ok", calls, "b"))
    text, name = AIService(["a", "b"]).generate_with_info("p")
    assert (text, name) == ("ok", "b")
    assert calls == ["a", "b"]          # 'a' tried once, not twice


def test_transient_error_is_retried(monkeypatch):
    calls = []
    state = {"n": 0}

    def flaky():
        state["n"] += 1
        if state["n"] == 1:
            raise _HttpError(503)
        return "ok"

    _install(monkeypatch, a=_provider(flaky, calls, "a"))
    assert AIService(["a"]).generate_with_info("p") == ("ok", "a")
    assert calls == ["a", "a"]


def test_skip_excludes_provider(monkeypatch):
    calls = []
    _install(monkeypatch, a=_provider(lambda: "A", calls, "a"), b=_provider(lambda: "B", calls, "b"))
    assert AIService(["a", "b"]).generate_with_info("p", skip={"a"}) == ("B", "b")
    assert calls == ["b"]


def test_all_failed_error_carries_safe_summary(monkeypatch):
    calls = []

    def bad():
        raise _HttpError(401, "bad key AIzaSyAAAAAAAAAAAAAAAAAAAAAAAAAAAA")

    _install(monkeypatch, a=_provider(bad, calls, "a"))
    with pytest.raises(AIProviderError) as err:
        AIService(["a", "missing_key_provider", "b"]).generate_with_info("p")
    assert "a: authentication failed (HTTP 401)" in err.value.summary
    assert "AIza" not in err.value.summary and "AIza" not in str(err.value)


def test_unknown_provider_name_is_ignored_at_startup(monkeypatch):
    _install(monkeypatch, a=_provider(lambda: "ok", [], "a"))
    service = AIService(["a", "openai"])
    assert service.provider_names == ["a"]
    assert service.generate_with_info("p") == ("ok", "a")


def test_provider_that_cannot_init_is_reported_as_not_configured(monkeypatch):
    class NoKey:
        def __init__(self):
            raise ValueError("GROQ_API_KEY is missing")

    _install(monkeypatch, groq=NoKey)
    with pytest.raises(AIProviderError) as err:
        AIService(["groq"]).generate_with_info("p")
    assert err.value.summary == "groq: not configured"
