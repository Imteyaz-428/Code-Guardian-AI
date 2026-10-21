from __future__ import annotations
import re
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from backend.analysis.risk_engine import RiskEngine

SEVERITY_SCORE = {"CRITICAL": 95, "HIGH": 80, "MEDIUM": 55, "LOW": 30}
CLASS_WEIGHTS = (0.0, 0.35, 0.70, 1.0)   # LOW, MEDIUM, HIGH, CRITICAL
GNN_LABELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")

SCORE_NOTE = (
    "risk_percent is a heuristic 0-100 risk score, not a calibrated "
    "probability that the function contains a vulnerability."
)


def static_weight() -> float:
    try:
        value = float(os.getenv("CODE_GUARDIAN_FUSION_STATIC_WEIGHT", "0.6"))
    except ValueError:
        value = 0.6
    return min(max(value, 0.0), 1.0)


def level_for(score: float) -> str:
    return RiskEngine._get_risk_level(int(score))


# ------------------------------------------------------------------
# GNN: node probabilities -> per-function probabilities
# ------------------------------------------------------------------

def aggregate_probabilities(
    node_probabilities: list[list[float]],
    node_metadata: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Average the node probabilities of every node that belongs to a function
    (the function node plus its CFG / definition / use / taint nodes)."""
    groups: dict[str, list[list[float]]] = defaultdict(list)

    for probs, meta in zip(node_probabilities, node_metadata):
        function_id = meta.get("function_id")
        if function_id:
            groups[function_id].append(probs)

    result: dict[str, dict[str, Any]] = {}

    for function_id, rows in groups.items():
        mean = [sum(col) / len(rows) for col in zip(*rows)]
        score = 100.0 * sum(p * w for p, w in zip(mean, CLASS_WEIGHTS))
        result[function_id] = {
            "score": round(score, 1),
            "label": GNN_LABELS[max(range(len(mean)), key=mean.__getitem__)],
            "probabilities": {
                GNN_LABELS[i]: round(p, 4) for i, p in enumerate(mean)
            },
            "nodes": len(rows),
        }

    return result


def gnn_function_scores(
    gnn_service, analyzer
) -> tuple[dict[str, dict[str, Any]] | None, str]:
    """Run the node-level GNN once and return per-function scores.

    Returns (None, reason) when the model/torch/graph is unavailable so the
    pipeline can continue with static analysis only.
    """
    try:
        import torch

        from backend.analysis.graph_dataset import GraphDatasetBuilder

        if analyzer.unified_code_graph is None:
            return None, "no unified code graph was produced"

        gnn_service.load_model()

        graph = GraphDatasetBuilder.from_graph(analyzer.unified_code_graph)
        graph.validate()

        if graph.num_nodes == 0 or graph.num_features != 23:
            return None, "graph is empty or has an unexpected feature size"

        x = torch.tensor(graph.node_features, dtype=torch.float32)
        edge_index = torch.tensor(graph.edge_index, dtype=torch.long)

        with torch.no_grad():
            probs = torch.softmax(gnn_service.model(x, edge_index), dim=1)

        return aggregate_probabilities(probs.tolist(), graph.node_metadata), ""

    except Exception as exc:  # model missing, torch missing, bad graph ...
        return None, f"{type(exc).__name__}: {exc}"


# ------------------------------------------------------------------
# Static side: attribute rule-matched taint findings to functions
# ------------------------------------------------------------------

def attribute_vulnerabilities(
    analyzer, root: Path
) -> tuple[dict[str, list[dict[str, Any]]], int]:
    """Map each vulnerability to the innermost function containing its sink.

    The taint findings carry no file/function, so a finding is attributed to
    a function when the sink line lies inside it AND that source line really
    contains the sink name (prevents cross-file line-number collisions).
    """
    taint = getattr(analyzer, "taint_results", None)
    vulns = list(getattr(taint, "vulnerabilities", []) or [])
    functions = getattr(analyzer, "functions", {}) or {}

    line_cache: dict[str, list[str]] = {}

    def lines_of(file_rel: str) -> list[str]:
        if file_rel not in line_cache:
            try:
                text = (root / file_rel).read_text(encoding="utf-8")
                line_cache[file_rel] = text.splitlines()
            except (OSError, UnicodeDecodeError):
                line_cache[file_rel] = []
        return line_cache[file_rel]

    by_function: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unattributed = 0

    for v in vulns:
        # The taint engine now records the exact function (file::name) that
        # contains the sink, so use it when it is a known function.
        direct = getattr(v, "function_id", "")
        if direct and direct in functions:
            by_function[direct].append({
                "rule_id": v.rule_id,
                "name": v.name,
                "severity": str(v.severity).upper(),
                "source": f"{v.source_name} (line {v.source_line})",
                "sink": f"{v.sink_name} (line {v.sink_line})",
                "variable": v.variable,
                "description": v.description,
            })
            continue

        best: tuple[int, int, str] | None = None  # (-has_variable, span, id)
        sink_short = str(v.sink_name).split(".")[-1]

        for function_id, node in functions.items():
            start = getattr(node, "lineno", None)
            end = getattr(node, "end_lineno", None)

            if start is None or end is None:
                continue
            if not (start <= v.sink_line <= end):
                continue

            file_rel = function_id.split("::", 1)[0]
            source = lines_of(file_rel)

            if not (0 < v.sink_line <= len(source)):
                continue
            if sink_short not in source[v.sink_line - 1]:
                continue

            # Prefer the function whose sink line also mentions the tainted
            # variable, then the innermost function.
            has_variable = int(bool(v.variable) and re.search(
                rf"\b{re.escape(v.variable)}\b", source[v.sink_line - 1]
            ) is not None)
            key = (-has_variable, end - start, function_id)
            if best is None or key < best:
                best = key

        if best is None:
            unattributed += 1
            continue

        by_function[best[2]].append({
            "rule_id": v.rule_id,
            "name": v.name,
            "severity": str(v.severity).upper(),
            "source": f"{v.source_name} (line {v.source_line})",
            "sink": f"{v.sink_name} (line {v.sink_line})",
            "variable": v.variable,
            "description": v.description,
        })

    return dict(by_function), unattributed


def structural_weight() -> float:
    """How much complexity-only signals count as SECURITY risk (0-1).

    Size/nesting/branch counts show a function is hard to maintain, not that it
    is exploitable, so without taint evidence they are scaled down."""
    try:
        value = float(os.getenv("CODE_GUARDIAN_STRUCTURAL_WEIGHT", "0.5"))
    except ValueError:
        value = 0.5
    return min(max(value, 0.0), 1.0)


def fuse(
    structural: float,
    vulnerability: float,
    gnn: float | None,
    weight: float | None = None,
) -> dict[str, Any]:
    w = static_weight() if weight is None else weight
    static = max(structural * structural_weight(), vulnerability)

    if gnn is None:
        final = static
        basis = "static_only"
    else:
        final = w * static + (1 - w) * gnn
        basis = "static+gnn"

    if vulnerability:
        final = max(final, 0.9 * vulnerability)

    final = round(min(final, 100.0), 1)

    return {
        "final_risk_percent": final,
        "level": level_for(final),
        "static_risk_percent": round(static, 1),
        "basis": basis,
    }

def _finding_text(vulns: list[dict[str, Any]], reasons: list[str]) -> str:
    if vulns:
        v = max(vulns, key=lambda x: SEVERITY_SCORE.get(x["severity"], 0))
        return (
            f"{v['name']}: untrusted data from {v['source']} reaches "
            f"{v['sink']} through variable '{v['variable']}'. "
            f"{v['description']}"
        ).strip()

    if reasons:
        return "Structural risk signals: " + ", ".join(reasons) + "."

    return "Function was flagged as risky by static analysis."


def function_source(analyzer, function_id: str, root: Path) -> str:
    node = (getattr(analyzer, "functions", {}) or {}).get(function_id)
    if node is None:
        return ""
    file_rel = function_id.split("::", 1)[0]
    try:
        lines = (root / file_rel).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return ""
    start = min(
        [node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])]
    )
    return "\n".join(lines[start - 1: node.end_lineno])


def build_scan(
    analyzer,
    results,
    root: Path,
    *,
    gnn_service=None,
    explainer=None,
    repo_ref: dict[str, str],
    top_n: int = 15,
    explain_top: int = 3,
    min_final_risk: float = 0.0,
) -> dict[str, Any]:
    """Rank every function by fused risk and attach explanations."""
    root = Path(root).resolve()
    engine = RiskEngine(repository_path=root)

    vuln_map, unattributed = attribute_vulnerabilities(analyzer, root)

    gnn_scores, gnn_note = (None, "GNN not requested")
    if gnn_service is not None:
        gnn_scores, gnn_note = gnn_function_scores(gnn_service, analyzer)

    by_position = {
        (fid.split("::", 1)[0], getattr(node, "lineno", None)): fid
        for fid, node in (analyzer.functions or {}).items()
    }

    rows: list[dict[str, Any]] = []
    files = 0

    for result in results:
        files += 1
        try:
            rel = Path(result.file_path).resolve().relative_to(root).as_posix()
        except ValueError:
            rel = str(result.file_path)

        for metrics in result.metrics:
            risk = engine.calculate_function_risk(metrics)
            function_id = by_position.get(
                (rel, risk["line"]), f"{rel}::{risk['name']}"
            )

            vulns = vuln_map.get(function_id, [])
            vuln_score = max(
                (SEVERITY_SCORE.get(v["severity"], 30) for v in vulns),
                default=0,
            )
            gnn = (gnn_scores or {}).get(function_id)

            fused = fuse(
                risk["score"], vuln_score, gnn["score"] if gnn else None
            )

            top_vuln = max(
                vulns, key=lambda x: SEVERITY_SCORE.get(x["severity"], 0),
                default=None,
            )
            finding = _finding_text(vulns, risk["reasons"])

            rows.append({
                "file": rel,
                "function": risk["name"],
                "function_id": function_id,
                "line": risk["line"],
                **fused,
                "structural_score": risk["score"],
                "vulnerability_score": vuln_score,
                "gnn_risk_percent": gnn["score"] if gnn else None,
                "gnn_label": gnn["label"] if gnn else None,
                "reasons": risk["reasons"],
                "vulnerabilities": vulns,
                "explanation": None,
                "fix_request": {
                    **repo_ref,
                    "file_path": rel,
                    "function_name": risk["name"],
                    "finding": finding,
                    "severity": fused["level"].lower(),
                    "explanation": "; ".join(risk["reasons"]),
                    "rule_id": top_vuln["rule_id"] if top_vuln else None,
                },
            })

    rows.sort(key=lambda r: r["final_risk_percent"], reverse=True)
    rows = [r for r in rows if r["final_risk_percent"] >= min_final_risk]
    flagged_total = len(rows)
    rows = rows[:top_n]

    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank

    if explainer is not None:
        for row in rows[:explain_top]:
            code = function_source(analyzer, row["function_id"], root)
            if not code:
                continue
            fix = row["fix_request"]
            exp = explainer.explain(
                file_path=row["file"],
                function_name=row["function"],
                code=code,
                severity=fix["severity"],
                finding=fix["finding"],
                static_explanation=fix["explanation"],
            )
            row["explanation"] = exp.to_dict() if exp else None

    return {
        "summary": {
            "files_analyzed": files,
            "functions_analyzed": len(analyzer.functions or {}),
            "functions_returned": len(rows),
            "functions_above_threshold": flagged_total,
            "gnn_available": gnn_scores is not None,
            "unattributed_vulnerabilities": unattributed,
        },
        "gnn_note": gnn_note,
        "score_note": SCORE_NOTE,
        "functions": rows,
    }
    