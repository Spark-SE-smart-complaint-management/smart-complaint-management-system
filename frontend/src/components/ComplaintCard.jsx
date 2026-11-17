import React from 'react'
import { Link } from 'react-router-dom'
import { StatusBadge, PriorityBadge, SLABadge } from './StatusBadge'
import { Clock, ExternalLink } from 'lucide-react'
import { format } from 'date-fns'

export default function ComplaintCard({ complaint, basePath = '/citizen' }) {
  return (
    <div className="card hover:shadow-md transition-shadow group">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="text-xs font-mono text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
              {complaint.reference_id}
            </span>
            <StatusBadge status={complaint.status} />
            <PriorityBadge priority={complaint.priority} />
          </div>
          <h3 className="font-semibold text-gray-900 truncate group-hover:text-blue-600 transition-colors">
            {complaint.title}
          </h3>
          <p className="text-sm text-gray-500 mt-1 line-clamp-2">{complaint.description}</p>
        </div>
        <Link to={`${basePath}/complaint/${complaint.id}`}
          className="shrink-0 p-2 hover:bg-blue-50 rounded-lg text-gray-400 hover:text-blue-600 transition-colors">
          <ExternalLink className="w-4 h-4" />
        </Link>
      </div>
      <div className="flex items-center gap-4 mt-4 pt-4 border-t border-gray-50">
        <div className="flex items-center gap-1 text-xs text-gray-400">
          <Clock className="w-3 h-3" />
          {format(new Date(complaint.created_at), 'dd MMM yyyy, HH:mm')}
        </div>
        {complaint.sla_breach_state && <SLABadge state={complaint.sla_breach_state} />}
      </div>
    </div>
  )
}
