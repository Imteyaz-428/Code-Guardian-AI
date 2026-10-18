from __future__ import annotations

import shutil
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from backend.core.config import settings

IGNORED = {
    ".git", ".venv", "venv", "node_modules", "datasets", "artifacts",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".codeguardian-tmp",
}


def _ignore(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORED}


def infer_rule_id(*texts: str) -> str | None:
    """Find a known vulnerability rule mentioned in the finding text."""
    from backend.analysis.vulnerability_rules import VulnerabilityRuleEngine

    haystack = " ".join(texts).lower().replace("_", " ")
    for rule in VulnerabilityRuleEngine.DEFAULT_RULES:
        if (rule.rule_id.lower().replace("_", " ") in haystack
                or rule.name.lower() in haystack):
            return rule.rule_id
    return None


def sql_is_parameterized(source: str, function_name: str | None) -> bool:
    """True when every SQL call uses a constant query string plus a separate
    parameters argument. Your taint engine only recognises sanitizer function
    names (escape, quote...), so it keeps flagging correct parameterized queries."""
    import ast

    from backend.analysis.vulnerability_rules import VulnerabilityRuleEngine

    sinks: set[str] = set()
    for rule in VulnerabilityRuleEngine.DEFAULT_RULES:
        if rule.rule_id == "SQL_INJECTION":
            sinks = set(rule.sink_names)

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False

    scope: ast.AST = tree
    if function_name:
        for node in ast.walk(tree):
            if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == function_name):
                scope = node
                break

    calls = []
    for node in ast.walk(scope):
        if isinstance(node, ast.Call):
            func = node.func
            name = (func.attr if isinstance(func, ast.Attribute)
                    else func.id if isinstance(func, ast.Name) else "")
            if name in sinks:
                calls.append(node)

    if not calls:
        return False

    for call in calls:
        first = call.args[0] if call.args else None
        has_params = len(call.args) >= 2 or bool(call.keywords)
        if not (isinstance(first, ast.Constant) and isinstance(first.value, str)
                and has_params):
            return False
    return True


def _collect(repository_path: Path) -> Counter:
    from backend.analysis.project_analyzer import ProjectAnalyzer
    from backend.api.analysis_details import build_analysis_details

    analyzer = ProjectAnalyzer(repository_path, generate_labels=False)
    analyzer.analyze()
    if analyzer.errors:
        raise RuntimeError("; ".join(analyzer.errors[:3]))
    details = build_analysis_details(analyzer)
    return Counter(
        (item.get("rule_id", ""), item.get("sink_name", ""))
        for item in details["vulnerability_findings"]
    )


class SecurityRescanService:
    def compare(self, repository_root, relative_file: str, proposed_source: str,
                rule_id: str | None = None,
                function_name: str | None = None) -> dict[str, Any]:
        root = Path(repository_root).resolve()

        # RepositoryManager only analyses paths inside the allowed root, so the
        # scratch copy lives there (hidden folder, removed afterwards).
        base = settings.ALLOWED_ANALYSIS_ROOT / ".codeguardian-tmp"
        base.mkdir(parents=True, exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix="rescan-", dir=base))

        try:
            repo = work / "repo"
            shutil.copytree(root, repo, ignore=_ignore, symlinks=False)
            before = _collect(repo)
            (repo / relative_file).write_text(proposed_source, encoding="utf-8")
            after = _collect(repo)
        except Exception as exc:
            return {"available": False, "rule_id": rule_id,
                    "error": f"{type(exc).__name__}: {exc}"}
        finally:
            shutil.rmtree(work, ignore_errors=True)

        introduced = after - before
        resolved = before - after

        if rule_id:
            fix_confirmed = (any(k[0] == rule_id for k in resolved)
                             if any(k[0] == rule_id for k in before) else None)
        else:
            fix_confirmed = bool(resolved) if before else None

        note = ""
        if (rule_id == "SQL_INJECTION" and fix_confirmed is False
                and sql_is_parameterized(proposed_source, function_name)):
            fix_confirmed = True
            note = "Every SQL call now uses a constant query with separate parameters."

        return {
            "available": True, "note": note, "rule_id": rule_id,
            "findings_before": sum(before.values()),
            "findings_after": sum(after.values()),
            "introduced": [{"rule_id": k[0], "sink": k[1], "count": v}
                           for k, v in introduced.items()],
            "resolved": [{"rule_id": k[0], "sink": k[1], "count": v}
                         for k, v in resolved.items()],
            "fix_confirmed": fix_confirmed,
        }