"""JSON-safe, evidence-rich summaries from the static-analysis pipeline.

This module deliberately keeps data-flow/code-quality findings separate from
rule-matched vulnerability findings. A data-flow warning is not automatically
a confirmed security vulnerability.
"""
from __future__ import annotations

from typing import Any


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        result = value.to_dict()
        return result if isinstance(result, dict) else {}
    if isinstance(value, dict):
        return value
    return {}


def _function_parts(function_id: str) -> tuple[str, str]:
    parts = str(function_id).split("::")
    file_path = parts[0] if parts else ""
    function_name = "::".join(parts[1:]) if len(parts) > 1 else "<module>"
    return file_path, function_name


def build_analysis_details(analyzer: Any) -> dict[str, Any]:
    """Collect the completed analyzer's summary and actionable findings."""
    details: dict[str, Any] = {
        "analysis_summary": {},
        "data_flow_findings": [],
        "dead_definition_findings": [],
        "taint_findings": [],
        "vulnerability_findings": [],
    }

    try:
        summary = analyzer.get_analysis_summary()
        if isinstance(summary, dict):
            details["analysis_summary"] = summary
    except Exception as exc:  # keep analysis response available on summary failure
        details["analysis_summary"] = {"summary_error": str(exc)}

    for function_id, result in getattr(analyzer, "use_before_definition", {}).items():
        file_path, function_name = _function_parts(function_id)
        for finding in getattr(result, "findings", []):
            item = _as_dict(finding)
            details["data_flow_findings"].append({
                "kind": "use_before_definition",
                "severity": "MEDIUM",
                "file": file_path,
                "function": function_name,
                **item,
            })

    for function_id, result in getattr(analyzer, "dead_definitions", {}).items():
        file_path, function_name = _function_parts(function_id)
        for finding in getattr(result, "findings", []):
            item = _as_dict(finding)
            details["dead_definition_findings"].append({
                "kind": "dead_definition",
                "severity": "LOW",
                "file": file_path,
                "function": function_name,
                **item,
            })

    taint_result = getattr(analyzer, "taint_results", None)
    if taint_result is not None:
        for finding in getattr(taint_result, "findings", []):
            item = _as_dict(finding)
            details["taint_findings"].append({
                "kind": "taint_flow",
                "scope": "project",
                **item,
            })
        for finding in getattr(taint_result, "vulnerabilities", []):
            item = _as_dict(finding)
            details["vulnerability_findings"].append({
                "kind": "rule_matched_taint_flow",
                "scope": "project",
                **item,
            })

    # Stable ordering makes reports reproducible and diffs readable.
    for key in (
        "data_flow_findings",
        "dead_definition_findings",
        "taint_findings",
        "vulnerability_findings",
    ):
        details[key].sort(
            key=lambda item: (
                str(item.get("file", "")),
                int(item.get("line", item.get("sink_line", 0)) or 0),
                str(item.get("kind", "")),
                str(item.get("variable", "")),
            )
        )

    details["finding_counts"] = {
        "data_flow": len(details["data_flow_findings"]),
        "dead_definitions": len(details["dead_definition_findings"]),
        "taint_flows": len(details["taint_findings"]),
        "rule_matched_vulnerabilities": len(details["vulnerability_findings"]),
    }
    return details