import React from 'react'
import clsx from 'clsx'

const STATUS_STYLES = {
  'New':          'bg-blue-100 text-blue-700',
  'Assigned':     'bg-indigo-100 text-indigo-700',
  'In Progress':  'bg-yellow-100 text-yellow-700',
  'Escalated':    'bg-red-100 text-red-700',
  'Resolved':     'bg-green-100 text-green-700',
  'Closed':       'bg-gray-100 text-gray-600',
  'Reopened':     'bg-orange-100 text-orange-700',
}

const PRIORITY_STYLES = {
  'Low':      'bg-green-100 text-green-700',
  'Medium':   'bg-yellow-100 text-yellow-700',
  'High':     'bg-orange-100 text-orange-700',
  'Critical': 'bg-red-100 text-red-800',
}

export function StatusBadge({ status }) {
  return (
    <span className={clsx('badge', STATUS_STYLES[status] || 'bg-gray-100 text-gray-600')}>
      {status}
    </span>
  )
}

export function PriorityBadge({ priority }) {
  if (!priority) return <span className="badge bg-gray-100 text-gray-400">—</span>
  return (
    <span className={clsx('badge', PRIORITY_STYLES[priority] || 'bg-gray-100 text-gray-600')}>
      {priority}
    </span>
  )
}

export function SLABadge({ state }) {
  const styles = {
    'On Track': 'bg-green-100 text-green-700',
    'At Risk':  'bg-yellow-100 text-yellow-800',
    'Breached': 'bg-red-100 text-red-700',
  }
  if (!state) return null
  return (
    <span className={clsx('badge', styles[state] || 'bg-gray-100 text-gray-500')}>
      {state}
    </span>
  )
}
