// Shared types mirroring the backend models and UI feed shapes

export type AgentKind = 'human' | 'agent'

export interface Agent {
  id: string
  name: string
  kind: AgentKind
  metadata?: Record<string, unknown>
  created_at?: string
}

export interface RepoRef {
  provider: 'github'
  owner: string
  name: string
  branch?: string | null
}

export interface ContextPool {
  id: string
  name: string
  description?: string | null
  tags?: string[]
  repos?: RepoRef[]
  created_at?: string
}

export type RefType = 'file' | 'url' | 'repo' | 'issue' | 'pr'

export interface Ref {
  type: RefType
  value: string
  meta?: Record<string, unknown>
}

export interface MemoryItem {
  id: string
  context_id: string
  author: string // agent id
  text: string
  tags: string[]
  refs: Ref[]
  created_at?: string
}

export type TaskStatus = 'todo' | 'in_progress' | 'blocked' | 'done'

export interface Task {
  id: string
  context_id: string
  title: string
  description?: string | null
  assignee?: string | null // agent id
  status: TaskStatus
  tags: string[]
  created_at?: string
  updated_at?: string
}

export interface Handoff {
  id: string
  from_agent: string
  to_agent: string
  context_id: string
  task_id: string
  summary: string
  next_steps?: string | null
  created_at?: string
}

// Notification stream from broker (mocked for now)
export type NotificationKind =
  | 'agent_created'
  | 'context_created'
  | 'repo_linked'
  | 'task_created'
  | 'task_updated'
  | 'memory_added'
  | 'handoff_recorded'
  | 'system'

export interface Notification<TPayload = unknown> {
  id: string
  ts: number
  kind: NotificationKind
  payload: TPayload
}

// UI feed event
export type FeedKind = 'user' | 'agent' | 'memory' | 'task' | 'handoff' | 'system'

export interface FeedEvent {
  id: string
  ts: number
  kind: FeedKind
  title?: string
  text?: string
  tags?: string[]
  refs?: Ref[]
  meta?: Record<string, unknown>
}

