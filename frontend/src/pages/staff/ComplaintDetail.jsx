import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getComplaint, getHistory, listComments, addComment, updateStatus } from '../../api/complaints'
import Navbar from '../../components/Navbar'
import { StatusBadge, PriorityBadge, SLABadge } from '../../components/StatusBadge'
import LoadingSpinner from '../../components/LoadingSpinner'
import toast from 'react-hot-toast'
import { ArrowLeft, Send, RefreshCw } from 'lucide-react'
import { format } from 'date-fns'

const NEXT_STATUSES = {
  'New': ['Assigned', 'In Progress', 'Escalated'],
  'Assigned': ['In Progress', 'Escalated'],
  'In Progress': ['Escalated', 'Resolved'],
  'Escalated': ['In Progress', 'Resolved'],
  'Resolved': ['Closed'],
  'Reopened': ['In Progress', 'Escalated'],
}

export default function StaffComplaintDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [complaint, setComplaint] = useState(null)
  const [history, setHistory] = useState([])
  const [comments, setComments] = useState([])
  const [comment, setComment] = useState('')
  const [status, setStatus] = useState('')
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      const [c, h, cm] = await Promise.all([getComplaint(id), getHistory(id), listComments(id)])
      setComplaint(c.data); setHistory(h.data); setComments(cm.data)
    } catch { toast.error('Failed to load'); navigate(-1) }
    finally { setLoading(false) }
  }, [id, navigate])

  useEffect(() => { load() }, [load])

  const handleStatusUpdate = async () => {
    if (!status) return
    setSubmitting(true)
    try {
      await updateStatus(id, { status, reason: reason || undefined })
      toast.success(`Status updated to ${status}`)
      setStatus(''); setReason(''); load()
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed') }
    finally { setSubmitting(false) }
  }

  const handleComment = async (e) => {
    e.preventDefault()
    if (!comment.trim()) return
    try {
      await addComment(id, { content: comment.trim() })
      setComment(''); toast.success('Comment added'); load()
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed') }
  }

  if (loading) return <div className="min-h-screen bg-gray-50"><Navbar /><LoadingSpinner /></div>
  if (!complaint) return null

  const nextStatuses = NEXT_STATUSES[complaint.status] || []

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-4xl mx-auto px-4 py-8">
        <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-gray-500 hover:text-blue-600 mb-6">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>

        <div className="grid md:grid-cols-3 gap-6">
          <div className="md:col-span-2 space-y-6">
            <div className="card">
              <div className="flex flex-wrap gap-2 mb-3">
                <span className="text-xs font-mono text-blue-600 bg-blue-50 px-2 py-0.5 rounded">{complaint.reference_id}</span>
                <StatusBadge status={complaint.status} />
                <PriorityBadge priority={complaint.priority} />
                <SLABadge state={complaint.sla_breach_state} />
              </div>
              <h1 className="text-xl font-bold text-gray-900 mb-2">{complaint.title}</h1>
              <p className="text-gray-600">{complaint.description}</p>
              <div className="mt-4 pt-4 border-t border-gray-50 text-sm text-gray-400">
                Submitted {format(new Date(complaint.created_at), 'dd MMM yyyy, HH:mm')}
              </div>
            </div>

            <div className="card">
              <h3 className="font-semibold text-gray-900 mb-4">Comments</h3>
              <div className="space-y-3 mb-4">
                {comments.length === 0 ? <p className="text-sm text-gray-400">No comments yet</p>
                  : comments.map(c => (
                    <div key={c.id} className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs text-gray-400 mb-1">{format(new Date(c.created_at), 'dd MMM yyyy, HH:mm')}</p>
                      <p className="text-sm text-gray-700">{c.content}</p>
                    </div>
                  ))}
              </div>
              <form onSubmit={handleComment} className="flex gap-2">
                <textarea className="input-field flex-1 resize-none" rows={2} placeholder="Add a comment..."
                  value={comment} onChange={e => setComment(e.target.value)} />
                <button type="submit" disabled={!comment.trim()} className="btn-primary self-end flex items-center gap-1">
                  <Send className="w-4 h-4" />
                </button>
              </form>
            </div>
          </div>

          <div className="space-y-4">
            {nextStatuses.length > 0 && (
              <div className="card">
                <h3 className="font-semibold text-gray-900 mb-3">Update Status</h3>
                <select className="input-field mb-3" value={status} onChange={e => setStatus(e.target.value)}>
                  <option value="">Select new status</option>
                  {nextStatuses.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
                <textarea className="input-field resize-none mb-3" rows={2} placeholder="Reason (optional)"
                  value={reason} onChange={e => setReason(e.target.value)} />
                <button onClick={handleStatusUpdate} disabled={!status || submitting} className="btn-primary w-full flex items-center justify-center gap-2">
                  <RefreshCw className="w-4 h-4" /> Update
                </button>
              </div>
            )}

            <div className="card">
              <h3 className="font-semibold text-gray-900 mb-3">History</h3>
              <div className="space-y-2">
                {history.map(h => (
                  <div key={h.id} className="text-xs border-l-2 border-blue-200 pl-3 py-1">
                    <span className="font-medium text-gray-700">{h.action.replace(/_/g, ' ')}</span>
                    {h.to_value && <span className="text-gray-500"> → {h.to_value}</span>}
                    <div className="text-gray-400">{format(new Date(h.timestamp), 'dd MMM, HH:mm')}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
