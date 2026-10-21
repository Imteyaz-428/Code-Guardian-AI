from __future__ import annotations

import sys
from pathlib import Path

# Support execution from the project root:
# python -m uvicorn backend.api.main:app --reload
#
# Also support execution from inside backend:
# uvicorn api.main:app --reload

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import (
    analysis,
    correction,
    health,
    pipeline,
    pipeline_run,
    verified_fix,
)


from backend.core.config import settings


# ---------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
)


# ---------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Register API Routers
# ---------------------------------------------------------

# Health check
app.include_router(health.router)

# Existing static code analysis
app.include_router(analysis.router)

# Advanced scanning:
# POST /pipeline/scan
app.include_router(pipeline.router)

# Full analysis and correction pipeline:
# POST /pipeline/run
app.include_router(pipeline_run.router)

# Correction proposals, approval and apply:
# POST /correction/propose, /verify, /propose-and-verify, /apply, /{proposal_id}/approve
# GET  /correction/history
app.include_router(correction.router)

# AI explanations and verified code corrections:
# POST /correction/explain
# POST /correction/fix-verified
app.include_router(verified_fix.router)


# ---------------------------------------------------------
# Root Endpoint
# ---------------------------------------------------------

@app.get("/", tags=["root"])
def root():
    return {
        "name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }