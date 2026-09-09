# Code Guardian AI — Backend

## Run locally

From the project root:

```bash
cd "code guadian"
python -m uvicorn backend.api.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

You can also start it from inside `backend/`:

```bash
cd backend
python -m uvicorn api.main:app --reload
```

## Endpoints

- `GET /health` — backend health check
- `POST /analyze` — analyze a Python repository
- `GET /docs` — FastAPI Swagger UI

### Analyze request

```json
{
  "repository_path": "tests/sample_project"
}
```

The path must resolve inside `CODE_GUARDIAN_ANALYSIS_ROOT`. By default that is the project root.

To analyze a different development directory, set:

```bash
export CODE_GUARDIAN_ANALYSIS_ROOT="/absolute/path/to/workspace"
```

## Current analysis pipeline

1. Repository path validation
2. Python file discovery
3. Python AST parsing
4. Function/class/import extraction
5. Function metrics
6. Deterministic risk scoring
7. JSON response for the React frontend

Syntax/encoding errors in individual Python files are reported in `errors` instead of crashing the entire analysis.
