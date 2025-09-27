Frontend Plan

Goals
- Real-time, comprehensible view of agent activity and outcomes.
- Chat-first UX for prompting, steering, and reviewing work.
- Clear mapping from events/memories to files, tasks, repos, and handoffs.

Layout (high-level)
- Left Sidebar: Context switcher, active agents list, quick filters (tags, repos, threads).
- Main Stream: Chat + event feed mixed chronologically (user prompts, agent replies, memory updates, status changes).
- Right Panel: Contextual details for the selected item (agent, task, memory), with actions (filter by tag, open refs, fork task).
- Top Bar: Project/context name, run status, search.
- Bottom Composer: Chat input with slash-commands (e.g., /assign, /handoff, /tag) and attachment for file refs.

Key Views
- Dashboard: Global feed across agents with filters (time, agent, tag, repo, type).
- Context Detail: Focused on a context; shows tasks, memories, linked repos, handoffs.
- Agent Detail: Agent timeline, current tasks, memory contributions.
- Handoff Center: Pending and historical handoffs with summaries and next steps.

Event Types (rendered in feed)
- User message, Agent message, Memory item (with tags+refs), Task update, Repo link, Handoff event, System notice.

Proposed File Structure (framework-agnostic)
- src/
  - routes/
    - Dashboard.tsx (feed + filters)
    - ContextView.tsx (context summary + tasks + memories)
    - AgentView.tsx (agent detail)
    - Handoffs.tsx (handoff list/detail)
  - components/
    - chat/
      - ChatInput.tsx
      - MessageList.tsx
      - MessageItem.tsx
    - feed/
      - EventList.tsx
      - EventItem.tsx
      - MemoryCard.tsx
    - agents/
      - AgentBadge.tsx
      - AgentList.tsx
    - tasks/
      - TaskCard.tsx
      - TaskList.tsx
    - shell/
      - Sidebar.tsx
      - Topbar.tsx
      - RightPanel.tsx
  - lib/api/
    - client.ts (HTTP calls to broker)
    - types.ts (mirrors backend models)
    - transform.ts (adapters to UI shapes)
  - lib/state/
    - store.ts (query cache, subscriptions, polling/SSE)
  - styles/
    - tokens.css
    - globals.css

Data Flow
- Polling first (GET endpoints) with lightweight cache; upgrade to SSE/WebSocket for push updates later.
- Normalize events into a single feed model with type tags (decision, incident, progress) inferred from MemoryItem.tags.
- Each feed item links to refs (files/PRs/URLs) for quick navigation.

MVP Interactions
- Send prompt, see agent plan and progress as memory updates.
- Filter feed by agent, type, tag, repo; quick search by substring.
- Click memory to open detail in Right Panel; jump to related items via tags.
- Handoff alert shows summary and next steps; accept and filter context automatically.

Next Steps
- Pick framework (Next.js or Vite+React) and scaffold minimal runtime.
- Implement lib/api/types.ts aligned with backend models.
- Build read-only Dashboard feed with polling; add ChatInput stub.

Mock Backend (for early UI wiring)
- Located under `src/lib/api/mockBackend.ts` and implements `BrokerAPI` with:
  - `listAgents()`, `listContexts()`, `listMemories()`, `listTasks()`, `listHandoffs()`
  - `subscribe(fn)`: push notifications for new events
  - `startScenario()`: runs a scripted timeline emitting notifications (agents, context, repo link, task, memories, handoff)
- UI consumes notifications via `src/lib/state/store.ts`, which transforms them into feed events for rendering.

Local structure (scaffolded)
- `src/lib/api/types.ts` – shared types for API + UI feed
- `src/lib/api/mockBackend.ts` – in-memory mock broker with a pre-scripted sequence
- `src/lib/state/store.ts` – minimal feed store that subscribes to notifications
- `src/components/feed/EventItem.tsx` – presentational component for events
- `src/components/feed/EventList.tsx` – renders a list of events
- `src/components/chat/ChatInput.tsx` – chat input stub that can emit user events locally
- `src/routes/Dashboard.tsx` – composes feed + chat; wires store to mock backend
