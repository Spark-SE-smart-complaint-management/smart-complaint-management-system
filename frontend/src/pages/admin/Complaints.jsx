import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listComplaints, assignComplaint, autoAssign } from '../../api/complaints'
import { listUsers } from '../../api/admin'
import Navbar from '../../components/Navbar'
import { StatusBadge, PriorityBadge, SLABadge } from '../../components/StatusBadge'
import LoadingSpinner from '../../components/LoadingSpinner'
import toast from 'react-hot-toast'
import { Search, Zap } from 'lucide-react'
import { format } from 'date-fns'

export default function AdminComplaints() {
  const [complaints, setComplaints] = useState([])
  const [staff, setStaff] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [selectedStaff, setSelectedStaff] = useState({})

  const reload = async () => {
    const res = await listComplaints()
    setComplaints(res.data)
  }

  useEffect(() => {
    Promise.all([listComplaints(), listUsers()])
      .then(([c, u]) => { setComplaints(c.data); setStaff(u.data.filter(u => u.role === 'Staff' && u.is_active)) })
      .catch(() => toast.error('Failed to load'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = complaints.filter(c => {
    const matchSearch = !search || c.title.toLowerCase().includes(search.toLowerCase()) || c.reference_id.includes(search)
    const matchStatus = !filterStatus || c.status === filterStatus
    return matchSearch && matchStatus
  })

  const handleAssign = async (complaintId) => {
    const staffId = selectedStaff[complaintId]
    if (!staffId) return
    try {
      await assignComplaint(complaintId, { staff_id: parseInt(staffId) })
      toast.success('Assigned!'); reload()
    } catch (err) { toast.error(err.response?.data?.detail || 'Assignment failed') }
  }

  const handleAutoAssign = async (complaintId) => {
    try { await autoAssign(complaintId, {}); toast.success('Auto-assigned!'); reload() }
    catch (err) { toast.error(err.response?.data?.detail || 'Auto-assign failed') }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">All Complaints</h1>

        <div className="flex gap-3 mb-6">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input className="input-field pl-9" placeholder="Search by title or reference..."
              value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          <select className="input-field w-48" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
            <option value="">All statuses</option>
            {['New','Assigned','In Progress','Escalated','Resolved','Closed','Reopened'].map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>

        {loading ? <LoadingSpinner /> : (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  {['Reference', 'Title', 'Status', 'Priority', 'SLA', 'Assign To', 'Date'].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {filtered.map(c => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <Link to={`/admin/complaint/${c.id}`} className="text-blue-600 hover:underline font-mono text-xs">{c.reference_id}</Link>
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-900 max-w-[160px] truncate">{c.title}</td>
                    <td className="px-4 py-3"><StatusBadge status={c.status} /></td>
                    <td className="px-4 py-3"><PriorityBadge priority={c.priority} /></td>
                    <td className="px-4 py-3"><SLABadge state={c.sla_breach_state} /></td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1 items-center">
                        <select className="text-xs border border-gray-200 rounded px-2 py-1 max-w-[120px]"
                          value={selectedStaff[c.id] || ''}
                          onChange={e => setSelectedStaff({ ...selectedStaff, [c.id]: e.target.value })}>
                          <option value="">Staff</option>
                          {staff.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                        </select>
                        <button onClick={() => handleAssign(c.id)} disabled={!selectedStaff[c.id]}
                          className="text-xs bg-blue-600 text-white px-2 py-1 rounded disabled:opacity-40 hover:bg-blue-700">Go</button>
                        <button onClick={() => handleAutoAssign(c.id)} title="Auto-assign"
                          className="text-xs bg-violet-100 text-violet-700 px-2 py-1 rounded hover:bg-violet-200 flex items-center gap-0.5">
                          <Zap className="w-3 h-3" />
                        </button>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{format(new Date(c.created_at), 'dd MMM')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
