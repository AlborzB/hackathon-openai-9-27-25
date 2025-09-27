import { FeedEvent, Notification } from '../api/types'
import { BrokerAPI } from '../api/mockBackend'

type Listener = (state: Readonly<FeedEvent[]>) => void

export class FeedStore {
  private feed: FeedEvent[] = []
  private listeners: Set<Listener> = new Set()
  private unsubscribeFn: (() => void) | null = null

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

  private transform(n: Notification): FeedEvent {
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

  connect(broker: BrokerAPI) {
    if (this.unsubscribeFn) this.unsubscribeFn()
    this.unsubscribeFn = broker.subscribe((n) => {
      const evt = this.transform(n)
      this.set([...this.feed, evt])
    })
  }

  start(broker: BrokerAPI) {
    this.connect(broker)
    broker.startScenario()
  }

  appendLocal(evt: FeedEvent) {
    this.set([...this.feed, evt])
  }
}

export const feedStore = new FeedStore()
