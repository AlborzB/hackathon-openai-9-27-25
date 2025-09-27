from __future__ import annotations

from typing import List, Optional

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


class MemoryStore:
    def upsert_agent(self, payload: AgentCreate) -> Agent:  # pragma: no cover
        raise NotImplementedError

    def list_agents(self) -> List[Agent]:  # pragma: no cover
        raise NotImplementedError

    def create_context(self, payload: ContextCreate) -> ContextPool:  # pragma: no cover
        raise NotImplementedError

    def list_contexts(self) -> List[ContextPool]:  # pragma: no cover
        raise NotImplementedError

    def link_repo(self, context_id: str, repo: RepoRef) -> ContextPool:  # pragma: no cover
        raise NotImplementedError

    def add_memory(self, context_id: str, payload: MemoryCreate) -> MemoryItem:  # pragma: no cover
        raise NotImplementedError

    def list_memories(self, context_id: str, q: Optional[str] = None) -> List[MemoryItem]:  # pragma: no cover
        raise NotImplementedError

    def add_task(self, context_id: str, payload: TaskCreate) -> Task:  # pragma: no cover
        raise NotImplementedError

    def update_task(self, context_id: str, task_id: str, payload: TaskUpdate) -> Task:  # pragma: no cover
        raise NotImplementedError

    def record_handoff(self, payload: HandoffCreate) -> Handoff:  # pragma: no cover
        raise NotImplementedError

