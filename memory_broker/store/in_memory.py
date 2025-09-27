from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from .base import MemoryStore
from ..models import (
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


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


class InMemoryStore(MemoryStore):
    def __init__(self) -> None:
        self._agents: Dict[str, Agent] = {}
        self._contexts: Dict[str, ContextPool] = {}
        self._memories: Dict[str, List[MemoryItem]] = {}
        self._tasks: Dict[str, Dict[str, Task]] = {}
        self._handoffs: Dict[str, Handoff] = {}

    # Agents
    def upsert_agent(self, payload: AgentCreate) -> Agent:
        # Id by name for idempotency in hackathon setting
        key = payload.name.lower().strip().replace(" ", "_")
        agent = self._agents.get(key)
        if agent:
            return agent
        agent = Agent(id=key, name=payload.name, kind=payload.kind, metadata=payload.metadata)
        self._agents[key] = agent
        return agent

    def list_agents(self) -> List[Agent]:
        return list(self._agents.values())

    # Contexts
    def create_context(self, payload: ContextCreate) -> ContextPool:
        key = payload.name.lower().strip().replace(" ", "-")
        if key in self._contexts:
            return self._contexts[key]
        ctx = ContextPool(id=key, name=payload.name, description=payload.description, tags=payload.tags)
        self._contexts[key] = ctx
        self._memories[key] = []
        self._tasks[key] = {}
        return ctx

    def list_contexts(self) -> List[ContextPool]:
        return list(self._contexts.values())

    def link_repo(self, context_id: str, repo: RepoRef) -> ContextPool:
        ctx = self._require_context(context_id)
        ctx.repos.append(repo)
        return ctx

    # Memories
    def add_memory(self, context_id: str, payload: MemoryCreate) -> MemoryItem:
        self._require_context(context_id)
        item = MemoryItem(
            id=_id("mem"),
            context_id=context_id,
            author=payload.author,
            text=payload.text,
            tags=payload.tags,
            refs=payload.refs,
        )
        self._memories[context_id].append(item)
        return item

    def list_memories(self, context_id: str, q: Optional[str] = None) -> List[MemoryItem]:
        self._require_context(context_id)
        items = self._memories.get(context_id, [])
        if not q:
            return items
        ql = q.lower()
        return [m for m in items if ql in m.text.lower() or any(ql in t.lower() for t in m.tags)]

    # Tasks
    def add_task(self, context_id: str, payload: TaskCreate) -> Task:
        self._require_context(context_id)
        tid = _id("task")
        task = Task(
            id=tid,
            context_id=context_id,
            title=payload.title,
            description=payload.description,
            assignee=payload.assignee,
            status=payload.status,
            tags=payload.tags,
        )
        self._tasks[context_id][tid] = task
        return task

    def update_task(self, context_id: str, task_id: str, payload: TaskUpdate) -> Task:
        self._require_context(context_id)
        task = self._tasks[context_id].get(task_id)
        if not task:
            raise KeyError(f"task not found: {task_id}")
        if payload.title is not None:
            task.title = payload.title
        if payload.description is not None:
            task.description = payload.description
        if payload.assignee is not None:
            task.assignee = payload.assignee
        if payload.status is not None:
            task.status = payload.status
        if payload.tags is not None:
            task.tags = payload.tags
        # updated_at will be recalculated by model default on re-creation; here we keep it simple
        return task

    # Handoffs
    def record_handoff(self, payload: HandoffCreate) -> Handoff:
        self._require_context(payload.context)
        hid = _id("handoff")
        ho = Handoff(
            id=hid,
            from_agent=payload.from_,
            to_agent=payload.to,
            context_id=payload.context,
            task_id=payload.task,
            summary=payload.summary,
            next_steps=payload.next_steps,
        )
        self._handoffs[hid] = ho
        return ho

    # Helpers
    def _require_context(self, context_id: str) -> ContextPool:
        ctx = self._contexts.get(context_id)
        if not ctx:
            raise KeyError(f"context not found: {context_id}")
        return ctx

