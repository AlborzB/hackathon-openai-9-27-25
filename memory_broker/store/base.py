from __future__ import annotations

from typing import List, Optional

from ..models import (
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

    def list_tasks(self, context_id: str) -> List[Task]:  # pragma: no cover
        raise NotImplementedError

    def record_handoff(self, payload: HandoffCreate) -> Handoff:  # pragma: no cover
        raise NotImplementedError

    def list_handoffs(self, context_id: str) -> List[Handoff]:  # pragma: no cover
        raise NotImplementedError

    # Orchestrations
    def create_orchestration(self, payload: OrchestrationCreate) -> OrchestrationRun:  # pragma: no cover
        raise NotImplementedError

    def get_orchestration(self, run_id: str) -> OrchestrationRun:  # pragma: no cover
        raise NotImplementedError

    def update_orchestration_status(self, run_id: str, status: str) -> OrchestrationRun:  # pragma: no cover
        raise NotImplementedError

    # Events
    def append_event(self, payload: EventCreate) -> Event:  # pragma: no cover
        raise NotImplementedError

    def list_run_events(
        self,
        run_id: str,
        *,
        agent_id: Optional[str] = None,
        type: Optional[str] = None,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
    ) -> List[Event]:  # pragma: no cover
        raise NotImplementedError

    def list_context_events(
        self,
        context_id: str,
        *,
        agent_id: Optional[str] = None,
        type: Optional[str] = None,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
    ) -> List[Event]:  # pragma: no cover
        raise NotImplementedError
