import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listComplaints } from '../../api/complaints'
import { listUsers } from '../../api/admin'
import Navbar from '../../components/Navbar'
import LoadingSpinner from '../../components/LoadingSpinner'
import { StatusBadge, PriorityBadge, SLABadge } from '../../components/StatusBadge'
import { FileText, Users, AlertTriangle, CheckCircle, Clock, TrendingUp } from 'lucide-react'
import { format } from 'date-fns'
import toast from 'react-hot-toast'

export default function AdminDashboard() {
  const [complaints, setComplaints] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([listComplaints(), listUsers()])
      .then(([c, u]) => { setComplaints(c.data); setUsers(u.data) })
      .catch(() => toast.error('Failed to load dashboard'))
      .finally(() => setLoading(false))
  }, [])

  const stats = {
    total: complaints.length,
    open: complaints.filter(c => !['Resolved','Closed'].includes(c.status)).length,
    escalated: complaints.filter(c => c.status === 'Escalated').length,
    resolved: complaints.filter(c => ['Resolved','Closed'].includes(c.status)).length,
    citizens: users.filter(u => u.role === 'Complainant').length,
    staff: users.filter(u => u.role === 'Staff').length,
    breached: complaints.filter(c => c.sla_breach_state === 'Breached').length,
    rate: complaints.length ? Math.round(complaints.filter(c => ['Resolved','Closed'].includes(c.status)).length / complaints.length * 100) : 0,
  }

  const recent = [...complaints].sort((a,b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 6)

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
          <p className="text-gray-500 mt-1">System overview</p>
        </div>

        {loading ? <LoadingSpinner /> : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              {[
                { label: 'Total Complaints', value: stats.total, icon: FileText, color: 'blue' },
                { label: 'Open', value: stats.open, icon: Clock, color: 'yellow' },
                { label: 'Escalated', value: stats.escalated, icon: AlertTriangle, color: 'red' },
                { label: 'Resolved', value: stats.resolved, icon: CheckCircle, color: 'green' },
                { label: 'Citizens', value: stats.citizens, icon: Users, color: 'indigo' },
                { label: 'Staff Members', value: stats.staff, icon: Users, color: 'violet' },
                { label: 'SLA Breached', value: stats.breached, icon: AlertTriangle, color: 'red' },
                { label: 'Resolution Rate', value: `${stats.rate}%`, icon: TrendingUp, color: 'green' },
              ].map(({ label, value, icon: Icon, color }) => (
                <div key={label} className="card">
                  <div className={`w-10 h-10 rounded-xl bg-${color}-100 flex items-center justify-center mb-3`}>
                    <Icon className={`w-5 h-5 text-${color}-600`} />
                  </div>
                  <p className="text-2xl font-bold text-gray-900">{value}</p>
                  <p className="text-sm text-gray-500">{label}</p>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
              {[
                { to: '/admin/complaints', label: 'Manage Complaints' },
                { to: '/admin/users', label: 'Manage Users' },
                { to: '/admin/reports', label: 'View Reports' },
              ].map(({ to, label }) => (
                <Link key={to} to={to} className="btn-secondary text-center text-sm py-3">{label}</Link>
              ))}
            </div>

            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Complaints</h2>
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b border-gray-100">
                    <tr>
                      {['Reference', 'Title', 'Status', 'Priority', 'SLA', 'Date'].map(h => (
                        <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {recent.map(c => (
                      <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-3">
                          <Link to={`/admin/complaint/${c.id}`} className="text-blue-600 hover:underline font-mono text-xs">{c.reference_id}</Link>
                        </td>
                        <td className="px-4 py-3 font-medium text-gray-900 max-w-[180px] truncate">{c.title}</td>
                        <td className="px-4 py-3"><StatusBadge status={c.status} /></td>
                        <td className="px-4 py-3"><PriorityBadge priority={c.priority} /></td>
                        <td className="px-4 py-3"><SLABadge state={c.sla_breach_state} /></td>
                        <td className="px-4 py-3 text-gray-400 text-xs">{format(new Date(c.created_at), 'dd MMM yyyy')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
