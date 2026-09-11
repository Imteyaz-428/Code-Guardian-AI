# Day 01 — Project Baseline & Architecture

## Objective

The first day was focused on understanding the existing Code Guardian AI
project before making major changes.

The goal was to establish a clean baseline and understand how the current
backend, frontend, analysis modules, and project structure work together.

---

## 1. Project Review

The existing project structure was reviewed before making modifications.

The main areas identified were:

- Backend
- Frontend
- Analysis modules
- Parsing modules
- Repository management
- Models
- Tests
- Configuration

The existing implementation was kept as the foundation instead of replacing
the complete project.

---

## 2. Development Strategy

A file-by-file improvement strategy was selected.

Instead of replacing the entire project folder, individual files would be
updated, tested, and verified before moving to the next file.

This approach provides:

- Easier debugging
- Smaller changes
- Better understanding of the codebase
- Lower risk of breaking existing functionality
- Easier Git commits

---

## 3. Initial Architecture

The initial analysis flow was identified as:

Repository
    ↓
Repository Manager
    ↓
Python File Detection
    ↓
AST Parser
    ↓
Code Extraction
    ↓
Metrics Analysis
    ↓
Dependency Analysis
    ↓
Graph Analysis
    ↓
Risk Engine

The frontend consumes the resulting analysis information and presents it
through a dashboard.

---

## 4. Baseline Audit

The project was reviewed to identify the existing capabilities and the areas
that needed improvement.

The main existing capabilities included:

- Python source analysis
- AST-based parsing
- Function detection
- Class detection
- Import detection
- Basic code metrics
- Dependency graph support
- Risk scoring
- Frontend dashboard

The project was therefore treated as a working foundation rather than a
greenfield application.

---

## 5. Development Principles

The following principles were established:

### Backend

- Keep analysis deterministic where possible.
- Prefer AST-based analysis over simple text parsing.
- Keep analysis modules separated by responsibility.
- Handle invalid files without crashing the complete project analysis.
- Validate repository paths before analysis.

### Frontend

- Keep the interface professional and minimal.
- Use a limited color palette.
- Avoid unnecessary visual effects.
- Improve components incrementally.

### Development

- Modify one file at a time.
- Test after important changes.
- Keep existing working functionality.
- Commit stable changes to Git.

---

## Result

The baseline architecture and development strategy were established.

The project was ready for structured backend refinement and incremental
implementation.