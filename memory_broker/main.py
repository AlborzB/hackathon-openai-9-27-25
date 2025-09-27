from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router as api_router
from .store.base import MemoryStore
from .store.in_memory import InMemoryStore


def create_store() -> MemoryStore:
    backend = os.getenv("MEMORY_BROKER_STORAGE", "memory").lower()
    # For hackathon: only in-memory by default; json backend could be added here
    if backend == "memory":
        return InMemoryStore()
    # Fallback to memory
    return InMemoryStore()


def create_app() -> FastAPI:
    app = FastAPI(title="Agent Memory Broker", version="0.1.0")

    # CORS for local dev + Codex CLI calls
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    store = create_store()

    # inject store instance for dependency resolution
    app.dependency_overrides = {}

    from fastapi import Depends
    from .api import get_store

    app.dependency_overrides[get_store] = lambda: store

    app.include_router(api_router)
    return app


app = create_app()

