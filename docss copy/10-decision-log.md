# Architecture Decision Log

## ADR-001 — Product identity

**Decision:** Code Guardian is primarily a code-risk intelligence and verification platform.

**Reason:** General code-generation and repository-level coding agents already exist.

## ADR-002 — Deterministic baseline first

**Decision:** V1 uses AST parsing, metrics, and rule-based analysis before ML/GNN.

**Reason:** We need reliable structured data and a baseline for experiments.

## ADR-003 — GNN requires validation

**Decision:** GNN is a research direction, not a guaranteed requirement.

**Reason:** It should earn its place through measurable improvement.

## ADR-004 — AI patches require verification

**Decision:** AI-generated patches remain proposals until sandbox execution, testing, and re-analysis provide sufficient evidence.

## ADR-005 — Python first

**Decision:** Initial language support is Python.

**Reason:** It enables rapid AST-based analysis and experimentation.

## ADR-006 — Documentation evolves

**Decision:** Review architecture documents whenever implementation reveals a material constraint.

**Reason:** The blueprint is a source of truth, not a substitute for empirical engineering.
