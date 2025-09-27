import React from 'react'
import { FeedEvent } from '../../lib/api/types'
import { EventItem } from './EventItem'

export function EventList({ events }: { events: FeedEvent[] }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {events.map((e) => (
        <EventItem key={e.id} evt={e} />
      ))}
    </div>
  )
}

