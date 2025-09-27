import React from 'react'
import { FeedEvent } from '../../lib/api/types'

export function EventItem({ evt }: { evt: FeedEvent }) {
  const date = new Date(evt.ts)
  return (
    <div style={{ padding: '8px 12px', borderBottom: '1px solid #eee' }}>
      <div style={{ fontSize: 12, color: '#777' }}>
        {date.toLocaleTimeString()} · {evt.kind.toUpperCase()}
      </div>
      {evt.title && <div style={{ fontWeight: 600 }}>{evt.title}</div>}
      {evt.text && <div>{evt.text}</div>}
      {evt.tags && evt.tags.length > 0 && (
        <div style={{ marginTop: 4 }}>
          {evt.tags.map((t) => (
            <span key={t} style={{ fontSize: 12, background: '#f3f4f6', padding: '2px 6px', marginRight: 6, borderRadius: 4 }}>
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

