"""FastAPI application entry point."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import drafts, history, offers, profile, users

app = FastAPI(title="Job Agent API", version="1.0.0")

# CORS — allow the Vercel dashboard origin (env-driven, defaults to localhost dev).
_cors_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(drafts.router)
app.include_router(history.router)
app.include_router(offers.router)
app.include_router(profile.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}
