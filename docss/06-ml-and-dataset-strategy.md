# ML and Dataset Strategy

## Goal

Predict code/component risk using structural and historical evidence.

## Feature candidates

### Code-level
- lines of code
- cyclomatic complexity
- nesting depth
- branches
- exception handling
- function length
- parameters
- imports/dependencies

### Graph-level
- in-degree/out-degree
- centrality
- call depth
- dependency count
- neighborhood structure

### Historical
- changed files
- bug-fixing commits
- change frequency
- code churn
- previous defect locations

## Model progression

Dataset → Feature extraction → Rule baseline → Classical ML → Graph representation → GNN

## Evaluation

Potential metrics include precision, recall, F1, ROC-AUC where appropriate, PR-AUC for imbalanced data, calibration, false-positive rate, and top-k risk localization.

## Research questions

1. Do graph features improve over conventional metrics?
2. Does a GNN improve defect localization over classical ML?
3. Which structural features contribute most?
4. Can risk scores be calibrated?
5. Does risk-aware repair reduce risk without increasing regressions?
