import pytest

from backend.services import ai_correction_provider as m
from backend.services.ai_correction import CorrectionInput

FUNC = 'def search():\n    term = request.args.get("q")\n    cur.execute("SELECT * FROM t WHERE n = ?", (term,))\n    return cur.fetchall()'
REQ = CorrectionInput(file_path="app.py", function_name="search", original_code="def search(): pass",
                      finding="sqli", severity="critical", explanation="")


@pytest.mark.parametrize("raw", [
    f"<corrected_code>\n{FUNC}\n</corrected_code>\n<explanation>param query</explanation>",
    f"<corrected_code>\n{FUNC}\n</explanation>",                                  # wrong closing tag
    f"<corrected_code>\n{FUNC}\n",                                                  # truncated, no closing tag
    f"<corrected_code>\n```python\n{FUNC}\n```\n</corrected_code>",                 # fence inside tags
    f"Here is the fix:\n```python\n{FUNC}\n```\nI used a parameterised query.",     # plain markdown
    '{"corrected_code": ' + __import__("json").dumps(FUNC) + ', "explanation": "param"}',
    FUNC,                                                                           # bare code
])
def test_formats_are_accepted(raw):
    out = m.parse_correction(raw)
    assert "cur.execute" in out.corrected_code and out.corrected_code.startswith("def search")
    assert "```" not in out.corrected_code


@pytest.mark.parametrize("raw", ["", "Sorry, I cannot help with that.", "<corrected_code>\nreturn 1\n</corrected_code>",
                                 "<corrected_code>\ndef f(:\n  pass\n</corrected_code>"])
def test_unusable_replies_are_rejected(raw):
    with pytest.raises(m.CorrectionFormatError):
        m.parse_correction(raw)


def test_retries_with_format_reminder_then_succeeds(monkeypatch):
    replies = iter(["I would use a parameterised query.", f"<corrected_code>\n{FUNC}\n</corrected_code>"])
    seen = []

    class Fake:
        def generate_with_info(self, prompt, system_prompt=None):
            seen.append(prompt)
            return next(replies), "stub"

    monkeypatch.setattr(m, "ai_service", Fake())
    out = m.FallbackCorrectionProvider().generate_correction(REQ)
    assert out.corrected_code.startswith("def search") and len(seen) == 2
    assert "could not be parsed" in seen[1] and "could not be parsed" not in seen[0]


def test_gives_up_after_max_attempts(monkeypatch):
    class Fake:
        def generate_with_info(self, prompt, system_prompt=None):
            return "no code here", "stub"

    monkeypatch.setattr(m, "ai_service", Fake())
    with pytest.raises(RuntimeError, match="after 3 attempts"):
        m.FallbackCorrectionProvider().generate_correction(REQ)
