import { BrokerHttpClient } from '../api/client'
import { BrokerAPI } from '../api/mockBackend'
import { Event, FeedEvent, FeedKind, Notification } from '../api/types'

type Listener = (state: Readonly<FeedEvent[]>) => void

export class FeedStore {
  private feed: FeedEvent[] = []
  private listeners: Set<Listener> = new Set()
  private unsubscribeFn: (() => void) | null = null
  private pollTimer: number | null = null
  private lastCursor: string | null = null
  private liveClient: BrokerHttpClient | null = null
  private liveContextId: string | null = null
  private isFetching = false
  private liveFetcher: (() => Promise<void>) | null = null

  getState() {
    return this.feed
  }

  subscribe(fn: Listener) {
    this.listeners.add(fn)
    fn(this.getState()) // initial snapshot
    return () => this.listeners.delete(fn)
  }

  private set(next: FeedEvent[]) {
    this.feed = next
    for (const l of this.listeners) l(this.feed)
  }

  private transformNotification(n: Notification): FeedEvent {
    const base = { id: n.id, ts: n.ts }
    switch (n.kind) {
      case 'agent_created':
        return { ...base, kind: 'system', title: 'Agent created', text: (n.payload as any).name }
      case 'context_created':
        return { ...base, kind: 'system', title: 'Context created', text: (n.payload as any).name }
      case 'repo_linked':
        return { ...base, kind: 'system', title: 'Repo linked', text: `${(n.payload as any).repo.owner}/${(n.payload as any).repo.name}` }
      case 'task_created':
        return { ...base, kind: 'task', title: 'Task created', text: (n.payload as any).title }
      case 'task_updated':
        return { ...base, kind: 'task', title: 'Task updated', text: `${(n.payload as any).title} → ${(n.payload as any).status}` }
      case 'memory_added': {
        const mem = n.payload as any
        return { ...base, kind: 'memory', title: 'Memory', text: mem.text, tags: mem.tags, refs: mem.refs }
      }
      case 'handoff_recorded': {
        const ho = n.payload as any
        return { ...base, kind: 'handoff', title: 'Handoff', text: ho.summary }
      }
      default:
        return { ...base, kind: 'system', text: 'Event' }
    }
  }

  private transformEvent(evt: Event): FeedEvent {
    const ts = evt.created_at ? new Date(evt.created_at).getTime() : Date.now()
    const base: FeedEvent = {
      id: evt.id,
      ts,
      kind: 'system',
      text: evt.message ?? evt.type,
      tags: evt.tags,
      meta: { raw: evt },
    }

    const categoryMap: Record<Event['category'], FeedKind> = {
      user: 'user',
      memory: 'memory',
      task: 'task',
      handoff: 'handoff',
      agent: 'agent',
      broker: 'system',
      repo: 'system',
      orchestration: 'system',
      plan: 'system',
      system: 'system',
    }
    base.kind = categoryMap[evt.category]

    switch (evt.category) {
      case 'user':
        base.title = evt.actor === 'user' ? 'User Prompt' : 'User Event'
        break
      case 'memory':
        base.title = 'Memory'
        break
      case 'task':
        base.title = evt.type === 'task_updated' ? 'Task Updated' : 'Task Created'
        break
      case 'handoff':
        base.title = 'Handoff'
        break
      case 'repo':
        base.title = 'Repo Linked'
        break
      case 'plan':
        base.title = 'Plan'
        break
      case 'orchestration':
        base.title = 'Orchestration'
        break
      case 'agent':
        base.title = 'Agent Event'
        break
      default:
        base.title = evt.type.replace('_', ' ')
    }

    if (!base.text) base.text = evt.type
    return base
  }

  private cleanup() {
    if (this.unsubscribeFn) {
      this.unsubscribeFn()
      this.unsubscribeFn = null
    }
    if (this.pollTimer !== null) {
      clearInterval(this.pollTimer)
      this.pollTimer = null
    }
    this.liveClient = null
    this.liveContextId = null
    this.lastCursor = null
    this.liveFetcher = null
    this.isFetching = false
  }

  startMock(broker: BrokerAPI) {
    this.cleanup()
    this.set([])
    this.unsubscribeFn = broker.subscribe((n) => {
      const evt = this.transformNotification(n)
      this.set([...this.feed, evt])
    })
    broker.startScenario()
  }

  startLive(client: BrokerHttpClient, contextId: string, intervalMs = 2000) {
    this.cleanup()
    this.set([])
    this.liveClient = client
    this.liveContextId = contextId

    const fetchEvents = async () => {
      if (!this.liveClient || !this.liveContextId) return
      if (this.isFetching) return
      this.isFetching = true
      try {
        const events = await this.liveClient.listContextEvents(this.liveContextId, {
          after: this.lastCursor ?? undefined,
          limit: this.lastCursor ? 100 : 250,
        })
        if (events.length > 0) {
          const next = events.map((e) => this.transformEvent(e))
          const merged = [...this.feed, ...next]
          this.lastCursor = events[events.length - 1].id
          this.set(merged)
        }
      } catch (err) {
        console.error('Failed to fetch events', err)
      } finally {
        this.isFetching = false
      }
    }

    this.liveFetcher = fetchEvents
    fetchEvents()
    this.pollTimer = window.setInterval(fetchEvents, intervalMs)
  }

  async refresh() {
    if (this.liveFetcher) {
      await this.liveFetcher()
    }
  }

  appendLocal(evt: FeedEvent) {
    this.set([...this.feed, evt])
  }

  stop() {
    this.cleanup()
  }
}

export const feedStore = new FeedStore()
