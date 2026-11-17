import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  getComplaint, getHistory, listComments, addComment,
  listAttachments, uploadAttachment, reopenComplaint
} from '../../api/complaints'
import Navbar from '../../components/Navbar'
import { StatusBadge, PriorityBadge, SLABadge } from '../../components/StatusBadge'
import LoadingSpinner from '../../components/LoadingSpinner'
import toast from 'react-hot-toast'
import { ArrowLeft, MessageSquare, Paperclip, RefreshCw, Send, Upload } from 'lucide-react'
import { format } from 'date-fns'
import clsx from 'clsx'

export default function CitizenComplaintDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [complaint, setComplaint] = useState(null)
  const [history, setHistory] = useState([])
  const [comments, setComments] = useState([])
  const [attachments, setAttachments] = useState([])
  const [comment, setComment] = useState('')
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('history')

  const load = useCallback(async () => {
    try {
      setLoading(true)
      const [c, h, cm, att] = await Promise.all([
        getComplaint(id), getHistory(id), listComments(id), listAttachments(id),
      ])
      setComplaint(c.data); setHistory(h.data); setComments(cm.data); setAttachments(att.data)
    } catch { toast.error('Failed to load'); navigate(-1) }
    finally { setLoading(false) }
  }, [id, navigate])

  useEffect(() => { load() }, [load])

  const handleComment = async (e) => {
    e.preventDefault()
    if (!comment.trim()) return
    try {
      await addComment(id, { content: comment.trim() })
      setComment(''); toast.success('Comment added'); load()
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed') }
  }

  const handleUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    try { await uploadAttachment(id, file); toast.success('File uploaded'); load() }
    catch (err) { toast.error(err.response?.data?.detail || 'Upload failed') }
  }

  const handleReopen = async () => {
    try { await reopenComplaint(id, { reason: 'Reopened by citizen' }); toast.success('Complaint reopened'); load() }
    catch (err) { toast.error(err.response?.data?.detail || 'Cannot reopen') }
  }

  if (loading) return <div className="min-h-screen bg-gray-50"><Navbar /><LoadingSpinner /></div>
  if (!complaint) return null

  const tabs = [
    { key: 'history', label: 'History', icon: RefreshCw },
    { key: 'comments', label: `Comments (${comments.length})`, icon: MessageSquare },
    { key: 'attachments', label: `Files (${attachments.length})`, icon: Paperclip },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-4xl mx-auto px-4 py-8">
        <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-gray-500 hover:text-blue-600 mb-6">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>

        <div className="card mb-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <span className="text-xs font-mono text-blue-600 bg-blue-50 px-2 py-0.5 rounded">{complaint.reference_id}</span>
                <StatusBadge status={complaint.status} />
                <PriorityBadge priority={complaint.priority} />
                <SLABadge state={complaint.sla_breach_state} />
              </div>
              <h1 className="text-xl font-bold text-gray-900">{complaint.title}</h1>
              <p className="text-gray-500 mt-2">{complaint.description}</p>
            </div>
            {complaint.status === 'Closed' && (
              <button onClick={handleReopen} className="btn-secondary flex items-center gap-2 shrink-0">
                <RefreshCw className="w-4 h-4" /> Reopen
              </button>
            )}
          </div>
          <div className="mt-4 pt-4 border-t border-gray-50 text-sm text-gray-400">
            Submitted {format(new Date(complaint.created_at), 'dd MMM yyyy, HH:mm')}
            {complaint.sla_deadline && (
              <span className="ml-4">SLA: {format(new Date(complaint.sla_deadline), 'dd MMM yyyy, HH:mm')}</span>
            )}
          </div>
        </div>

        <div className="flex gap-1 mb-4 bg-white rounded-xl p-1 border border-gray-100 shadow-sm w-fit">
          {tabs.map(({ key, label, icon: Icon }) => (
            <button key={key} onClick={() => setTab(key)}
              className={clsx('flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                tab === key ? 'bg-gradient-to-r from-blue-600 to-violet-600 text-white shadow' : 'text-gray-600 hover:text-blue-600')}>
              <Icon className="w-3.5 h-3.5" />{label}
            </button>
          ))}
        </div>

        {tab === 'history' && (
          <div className="card space-y-3">
            {history.length === 0 ? <p className="text-gray-400 text-sm text-center py-6">No history yet</p>
              : history.map(h => (
                <div key={h.id} className="flex gap-3 items-start py-2 border-b border-gray-50 last:border-0">
                  <div className="w-2 h-2 rounded-full bg-blue-400 mt-1.5 shrink-0" />
                  <div>
                    <span className="text-sm font-medium text-gray-900">{h.action.replace(/_/g, ' ')}</span>
                    {h.from_value && h.to_value && <span className="text-sm text-gray-500"> · {h.from_value} → {h.to_value}</span>}
                    {h.reason && <p className="text-xs text-gray-400 mt-0.5">{h.reason}</p>}
                    <p className="text-xs text-gray-400">{format(new Date(h.timestamp), 'dd MMM yyyy, HH:mm')}</p>
                  </div>
                </div>
              ))}
          </div>
        )}

        {tab === 'comments' && (
          <div className="space-y-4">
            <div className="card space-y-4">
              {comments.length === 0 ? <p className="text-gray-400 text-sm text-center py-4">No comments yet</p>
                : comments.map(c => (
                  <div key={c.id} className="border-b border-gray-50 last:border-0 pb-3">
                    <p className="text-xs text-gray-400 mb-1">{format(new Date(c.created_at), 'dd MMM yyyy, HH:mm')}</p>
                    <p className="text-sm text-gray-700">{c.content}</p>
                  </div>
                ))}
            </div>
            <form onSubmit={handleComment} className="card flex gap-3">
              <textarea className="input-field flex-1 resize-none" rows={2} placeholder="Add a comment..."
                value={comment} onChange={(e) => setComment(e.target.value)} />
              <button type="submit" disabled={!comment.trim()} className="btn-primary flex items-center gap-1 self-end">
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        )}

        {tab === 'attachments' && (
          <div className="card space-y-4">
            <label className="flex items-center gap-2 btn-secondary cursor-pointer w-fit">
              <Upload className="w-4 h-4" /> Upload File
              <input type="file" className="hidden" accept=".pdf,.jpg,.jpeg,.png" onChange={handleUpload} />
            </label>
            <p className="text-xs text-gray-400">Allowed: PDF, JPEG, PNG</p>
            {attachments.length === 0 ? <p className="text-gray-400 text-sm">No attachments yet</p>
              : attachments.map(a => (
                <div key={a.id} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                  <Paperclip className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-700 flex-1">{a.filename || a.original_filename}</span>
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  )
}
