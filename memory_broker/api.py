from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from .models import (
    Agent,
    AgentCreate,
    ContextCreate,
    ContextPool,
    Event,
    EventCreate,
    Handoff,
    HandoffCreate,
    MemoryCreate,
    MemoryItem,
    OrchestrationCreate,
    OrchestrationRun,
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
        ctx = store.link_repo(context_id, repo)
        # emit event
        store.append_event(
            EventCreate(
                context_id=context_id,
                category="repo",
                type="repo_linked",
                actor="broker",
                repo=repo,
            )
        )
        return ctx
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/contexts/{context_id}/memories", response_model=MemoryItem)
def add_memory(context_id: str, payload: MemoryCreate, store: MemoryStore = Depends(get_store)):
    try:
        item = store.add_memory(context_id, payload)
        store.append_event(
            EventCreate(
                context_id=context_id,
                category="memory",
                type="memory_added",
                actor="broker",
                message=item.text,
                tags=item.tags,
                data={"author": item.author, "tags": item.tags},
            )
        )
        return item
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
        task = store.add_task(context_id, payload)
        store.append_event(
            EventCreate(
                context_id=context_id,
                category="task",
                type="task_created",
                actor="broker",
                agent_id=task.assignee,
                tags=task.tags or [],
                data={"task_id": task.id, "title": task.title},
            )
        )
        return task
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/contexts/{context_id}/tasks/{task_id}", response_model=Task)
def update_task(context_id: str, task_id: str, payload: TaskUpdate, store: MemoryStore = Depends(get_store)):
    try:
        task = store.update_task(context_id, task_id, payload)
        store.append_event(
            EventCreate(
                context_id=context_id,
                category="task",
                type="task_updated",
                actor="broker",
                agent_id=task.assignee,
                tags=task.tags or [],
                data={"task_id": task.id},
            )
        )
        return task
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/contexts/{context_id}/tasks", response_model=List[Task])
def list_tasks(context_id: str, store: MemoryStore = Depends(get_store)):
    try:
        return store.list_tasks(context_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/handoffs", response_model=Handoff)
def record_handoff(payload: HandoffCreate, store: MemoryStore = Depends(get_store)):
    try:
        ho = store.record_handoff(payload)
        store.append_event(
            EventCreate(
                context_id=ho.context_id,
                category="handoff",
                type="handoff_recorded",
                actor="broker",
                agent_id=ho.to_agent,
                task_id=ho.task_id,
                data={"from": ho.from_agent, "to": ho.to_agent},
            )
        )
        return ho
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/contexts/{context_id}/handoffs", response_model=List[Handoff])
def list_handoffs(context_id: str, store: MemoryStore = Depends(get_store)):
    try:
        return store.list_handoffs(context_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Orchestrations
@router.post("/orchestrations", response_model=OrchestrationRun)
def create_orchestration(payload: OrchestrationCreate, store: MemoryStore = Depends(get_store)):
    try:
        run = store.create_orchestration(payload)
        # Emit user prompt and plan placeholder events to seed the feed
        store.append_event(
            EventCreate(
                context_id=run.context_id,
                run_id=run.id,
                category="user",
                type="user_message",
                actor="user",
                message=payload.prompt,
            )
        )
        store.append_event(
            EventCreate(
                context_id=run.context_id,
                run_id=run.id,
                category="plan",
                type="plan",
                actor="broker",
                message="planning_started",
            )
        )
        return run
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/orchestrations/{run_id}", response_model=OrchestrationRun)
def get_orchestration(run_id: str, store: MemoryStore = Depends(get_store)):
    try:
        return store.get_orchestration(run_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/orchestrations/{run_id}/events", response_model=List[Event])
def list_run_events(
    run_id: str,
    agent_id: Optional[str] = None,
    type: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    limit: Optional[int] = Query(default=None, ge=0),
    after: Optional[str] = None,
    store: MemoryStore = Depends(get_store),
):
    try:
        return store.list_run_events(
            run_id,
            agent_id=agent_id,
            type=type,
            category=category,
            tag=tag,
            limit=limit,
            after=after,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/contexts/{context_id}/events", response_model=List[Event])
def list_context_events(
    context_id: str,
    agent_id: Optional[str] = None,
    type: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    limit: Optional[int] = Query(default=None, ge=0),
    after: Optional[str] = None,
    store: MemoryStore = Depends(get_store),
):
    try:
        return store.list_context_events(
            context_id,
            agent_id=agent_id,
            type=type,
            category=category,
            tag=tag,
            limit=limit,
            after=after,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
