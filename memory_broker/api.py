from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from .models import (
    Agent,
    AgentCreate,
    ContextCreate,
    ContextPool,
    Handoff,
    HandoffCreate,
    MemoryCreate,
    MemoryItem,
    RepoRef,
    Task,
    TaskCreate,
    TaskUpdate,
)
from .store.base import MemoryStore


def get_store(store: MemoryStore = Depends()) -> MemoryStore:
    # FastAPI resolves this via app dependency overrides set in main.py
    return store


router = APIRouter()


@router.get("/agents", response_model=List[Agent])
def list_agents(store: MemoryStore = Depends(get_store)):
    return store.list_agents()


@router.post("/agents", response_model=Agent)
def upsert_agent(payload: AgentCreate, store: MemoryStore = Depends(get_store)):
    return store.upsert_agent(payload)


@router.get("/contexts", response_model=List[ContextPool])
def list_contexts(store: MemoryStore = Depends(get_store)):
    return store.list_contexts()


@router.post("/contexts", response_model=ContextPool)
def create_context(payload: ContextCreate, store: MemoryStore = Depends(get_store)):
    return store.create_context(payload)


@router.post("/contexts/{context_id}/repos", response_model=ContextPool)
def link_repo(context_id: str, repo: RepoRef, store: MemoryStore = Depends(get_store)):
    try:
        return store.link_repo(context_id, repo)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/contexts/{context_id}/memories", response_model=MemoryItem)
def add_memory(context_id: str, payload: MemoryCreate, store: MemoryStore = Depends(get_store)):
    try:
        return store.add_memory(context_id, payload)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/contexts/{context_id}/memories", response_model=List[MemoryItem])
def list_memories(
    context_id: str,
    q: Optional[str] = Query(default=None, description="basic substring search over text and tags"),
    store: MemoryStore = Depends(get_store),
):
    try:
        return store.list_memories(context_id, q=q)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/contexts/{context_id}/tasks", response_model=Task)
def add_task(context_id: str, payload: TaskCreate, store: MemoryStore = Depends(get_store)):
    try:
        return store.add_task(context_id, payload)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/contexts/{context_id}/tasks/{task_id}", response_model=Task)
def update_task(context_id: str, task_id: str, payload: TaskUpdate, store: MemoryStore = Depends(get_store)):
    try:
        return store.update_task(context_id, task_id, payload)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/handoffs", response_model=Handoff)
def record_handoff(payload: HandoffCreate, store: MemoryStore = Depends(get_store)):
    try:
        return store.record_handoff(payload)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

