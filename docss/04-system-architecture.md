# System Architecture

```text
GitHub / Local Repository
          ↓
Repository Manager
          ↓
Static Analyzer
(AST / CFG / Calls / Data Flow / Metrics)
          ↓
Code Graph
     ↙          ↘
Rules          ML/GNN
     ↘          ↙
       Risk Engine
           ↓
     Explainability
           ↓
      Repair Agent
           ↓
     Sandbox Runner
           ↓
    Tests + Re-analysis
        ↙          ↘
   VERIFIED      REJECTED
```

## Components

- Repository Manager: acquisition and file discovery
- Parser: language-specific parsing
- Analyzer: structural/static analysis
- Graph Builder: code graph construction
- Risk Engine: deterministic + learned risk
- Explanation: human-readable evidence
- Repair Agent: patch generation
- Sandbox: isolated execution
- Verification: tests and post-patch analysis
- API: orchestration interface
- Frontend: visualization

## Initial backend layout

```text
backend/
├── api/
├── repository/
├── parsing/
├── analysis/
├── graph/
├── risk/
├── repair/
├── sandbox/
├── verification/
├── models/
└── tests/
```
