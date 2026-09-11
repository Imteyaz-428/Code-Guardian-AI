# Day 07 — Graph Analyzer

## Objective

The seventh day focused on analyzing the dependency graph created during the
previous stage.

---

## 1. Graph Normalization

`GraphAnalyzer` was designed to work with multiple graph representations.

Supported formats include:

- `DependencyGraph`
- Dictionary containing nodes and edges
- `(nodes, edges)` collection

This makes the analyzer less dependent on one specific graph
implementation.

---

## 2. File Nodes

The analyzer can identify file nodes from the graph.

It supports both dictionary-based and list-based node representations.

---

## 3. Import Edges

Import edges are extracted from the graph.

Only valid edges containing source and target information are considered.

---

## 4. Adjacency List

The graph is converted into an adjacency representation.

Example:

```text
main.py -> [utils.py, services/user.py]
utils.py -> []
services/user.py -> []