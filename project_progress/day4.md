# Day 04 — Code Metrics & Structural Analysis

## Objective

The fourth day focused on calculating structural metrics for individual
functions and methods.

---

## 1. Metrics Analyzer

`MetricsAnalyzer` was implemented using AST traversal.

Metrics are calculated for every function and method in a Python file.

---

## 2. Metrics Collected

The analyzer calculates:

- Lines of code
- Parameter count
- Branch count
- Loop count
- Function call count
- Nesting depth
- Cyclomatic complexity

---

## 3. Cyclomatic Complexity

Cyclomatic complexity is calculated from decision points.

The implementation considers structural constructs such as:

- `if`
- loops
- exception handlers
- conditional expressions
- boolean expressions
- pattern matching

The basic calculation is:

`complexity = 1 + decision_points`

---

## 4. Nesting Depth

The analyzer tracks nested control-flow structures.

Supported nesting structures include:

- `if`
- `for`
- `while`
- `try`
- `with`
- `match`

The maximum nesting depth is stored as a function metric.

---

## 5. Nested Functions

Nested functions and lambdas are prevented from incorrectly inflating the
metrics of their enclosing function.

Each function receives its own structural analysis.

---

## 6. Parameter Analysis

The analyzer supports:

- Positional-only parameters
- Normal parameters
- Keyword-only parameters
- `*args`
- `**kwargs`

---

## Result

Code Guardian AI could now quantify structural complexity at the function
level.

These metrics later became the primary inputs for deterministic risk scoring.