---

# Day 08 — Risk Engine

`docs/Project Progress/Day-08.md`

```md
# Day 08 — Risk Engine

## Objective

The eighth day focused on converting structural metrics and dependency
information into deterministic risk scores.

---

## 1. Risk Engine

`RiskEngine` was implemented to calculate risk at multiple levels:

- Function
- File
- Project

---

## 2. Function Risk

Function risk uses structural signals such as:

- Cyclomatic complexity
- Lines of code
- Number of parameters
- Nesting depth
- Branches
- Loops
- Function calls

Each signal contributes to the overall risk score.

---

## 3. Risk Levels

Risk scores are converted into four levels:

| Score | Level |
|---|---|
| 0–19 | LOW |
| 20–39 | MEDIUM |
| 40–69 | HIGH |
| 70–100 | CRITICAL |

---

## 4. Explainable Reasons

The engine does not only return a score.

It also produces human-readable reasons.

Examples include:

- High cyclomatic complexity
- Large function
- Many parameters
- Deep nesting
- Several branches
- Many function calls

This makes the risk result explainable.

---

## 5. File Risk

File risk combines function-level risk with dependency information.

Additional factors include:

- Number of dependent files
- Circular dependency participation
- Number of functions

A file containing a highly risky function can therefore receive a higher
file-level risk score.

---

## 6. Project Risk

The engine can calculate risk for all analyzed files and return a project-wide
collection of file risk results.

---

## 7. Score Limiting

Risk scores are capped at `100`.

This keeps the risk scale predictable for both the backend and frontend.

---

## Result

Code Guardian AI gained its first complete deterministic risk-analysis
layer.

The system could now explain not only what code exists, but which parts of
the codebase appear structurally risky and why.