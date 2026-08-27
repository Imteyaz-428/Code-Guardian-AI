# Product Specification

## V1 — Repository Analyzer

Input: local Python repository.

Output:
- files analyzed
- functions/classes/imports
- basic complexity metrics
- initial rule-based findings
- risk score/report

## V2 — Structural Intelligence

Add AST enrichment, control-flow graph, call graph, data-flow relationships, dependency extraction, and change-impact analysis.

## V3 — ML/GNN

Build a reproducible classical-ML baseline first, then investigate graph representations and GNNs. GNNs must be justified experimentally.

## V4 — AI Repair

For a selected finding, provide structured evidence/context to an LLM and generate a patch proposal.

## V5 — Verification

Original → Patch → Isolated sandbox → Tests/static analysis → Re-analysis → Risk comparison → Accept/Reject.

## V6 — Developer Product

Potential features: GitHub import, pull-request analysis, dashboard, risk trends, change-impact visualization, repair history, and reports.
