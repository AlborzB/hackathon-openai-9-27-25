import React from 'react'
import { createRoot } from 'react-dom/client'
import { Dashboard } from './routes/Dashboard'

const mount = document.getElementById('root')
if (mount) {
  const root = createRoot(mount)
  root.render(
    <React.StrictMode>
      <Dashboard />
    </React.StrictMode>
  )
}

