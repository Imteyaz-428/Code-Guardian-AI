# Technology Stack

## Initial stack

### Backend
- Python
- FastAPI
- Pydantic
- pytest

### Code analysis
Start with Python's built-in `ast` module. Evaluate richer parsers/CFG/call-graph/data-flow tooling later.

### ML
- scikit-learn for baselines
- PyTorch for neural models
- PyTorch Geometric or another graph-learning framework if justified

### Frontend
- React
- TypeScript

### Data and execution
- PostgreSQL for application metadata when needed
- Docker for isolated verification
- Git/GitHub for collaboration and CI/CD

## Technology-selection rule

Every major dependency must have a clear responsibility, rationale, testable integration, and practical fallback where possible.
