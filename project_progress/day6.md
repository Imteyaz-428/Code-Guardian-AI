# Day 06 — Dependency Analyzer & Dependency Graph

## Objective

The sixth day focused on understanding relationships between files through
Python imports.

---

## 1. Dependency Analyzer

`DependencyAnalyzer` was developed to analyze Python imports and identify
local dependencies.

It supports:

- Normal imports
- `from ... import ...`
- Relative imports

---

## 2. Local Dependency Resolution

The analyzer attempts to resolve imported modules to files inside the
repository.

It supports:

- `.py` modules
- Python packages through `__init__.py`
- Relative imports

Only dependencies that can be resolved to local repository files are added
to the local dependency graph.

External libraries are not treated as local repository dependencies.

---

## 3. File Metadata

Metadata was added for analyzed files.

The graph can contain information such as:

- Language
- Lines
- Functions
- Methods
- Classes
- Imports
- Function details
- Method details
- Class details

---

## 4. DependencyGraph

`DependencyGraph` was created to represent relationships between project
elements.

It supports:

- File nodes
- Function nodes
- Class nodes
- Method nodes
- Import edges
- Node metadata

---

## 5. Duplicate Prevention

The graph prevents duplicate nodes and duplicate edges.

This keeps the resulting graph consistent and easier to consume by later
analysis components.

---

## Result

Code Guardian AI gained a repository-level dependency representation.

The project was no longer analyzed only as independent files; relationships
between files could now be examined.