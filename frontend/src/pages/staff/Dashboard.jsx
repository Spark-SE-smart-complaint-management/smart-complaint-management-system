import React, { useEffect, useState } from 'react'
import { listComplaints } from '../../api/complaints'
import { useAuth } from '../../context/AuthContext'
import Navbar from '../../components/Navbar'
import ComplaintCard from '../../components/ComplaintCard'
import LoadingSpinner from '../../components/LoadingSpinner'
import { ClipboardList, Clock, CheckCircle } from 'lucide-react'
import toast from 'react-hot-toast'

export default function StaffDashboard() {
  const { user } = useAuth()
  const [complaints, setComplaints] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listComplaints()
      .then(r => setComplaints(r.data))
      .catch(() => toast.error('Failed to load'))
      .finally(() => setLoading(false))
  }, [])

  const mine = complaints.filter(c => c.assignee_id === user?.id)
  const active = mine.filter(c => !['Resolved', 'Closed'].includes(c.status))
  const done = mine.filter(c => ['Resolved', 'Closed'].includes(c.status))

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Staff Dashboard</h1>
          <p className="text-gray-500 mt-1">Your assigned complaints</p>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-8">
          {[
            { label: 'Total Assigned', value: mine.length, icon: ClipboardList, color: 'blue' },
            { label: 'Active', value: active.length, icon: Clock, color: 'yellow' },
            { label: 'Resolved', value: done.length, icon: CheckCircle, color: 'green' },
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

        <h2 className="text-lg font-semibold text-gray-900 mb-4">Active Complaints</h2>
        {loading ? <LoadingSpinner /> : active.length === 0 ? (
          <div className="card text-center py-12">
            <ClipboardList className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No active complaints assigned to you</p>
          </div>
        ) : (
          <div className="space-y-4">
            {active.map(c => <ComplaintCard key={c.id} complaint={c} basePath="/staff" />)}
          </div>
        )}
      </div>
    </div>
  )
}
