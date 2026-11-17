import React from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useComplaints } from '../../hooks/useComplaints'
import Navbar from '../../components/Navbar'
import ComplaintCard from '../../components/ComplaintCard'
import LoadingSpinner from '../../components/LoadingSpinner'
import { Plus, FileText, CheckCircle, Clock, AlertTriangle } from 'lucide-react'

export default function CitizenDashboard() {
  const { user } = useAuth()
  const { complaints, loading } = useComplaints()

  const stats = {
    total: complaints.length,
    open: complaints.filter(c => !['Resolved','Closed'].includes(c.status)).length,
    resolved: complaints.filter(c => ['Resolved','Closed'].includes(c.status)).length,
    escalated: complaints.filter(c => c.status === 'Escalated').length,
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Welcome back, {user?.name?.split(' ')[0]} 👋
            </h1>
            <p className="text-gray-500 mt-1">Track and manage your complaints</p>
          </div>
          <Link to="/citizen/submit" className="btn-primary flex items-center gap-2">
            <Plus className="w-4 h-4" /> New Complaint
          </Link>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Total', value: stats.total, icon: FileText, color: 'blue' },
            { label: 'Active', value: stats.open, icon: Clock, color: 'yellow' },
            { label: 'Resolved', value: stats.resolved, icon: CheckCircle, color: 'green' },
            { label: 'Escalated', value: stats.escalated, icon: AlertTriangle, color: 'red' },
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

        <h2 className="text-lg font-semibold text-gray-900 mb-4">Your Complaints</h2>
        {loading ? <LoadingSpinner /> : complaints.length === 0 ? (
          <div className="card text-center py-16">
            <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 mb-4">No complaints yet</p>
            <Link to="/citizen/submit" className="btn-primary">Submit your first complaint</Link>
          </div>
        ) : (
          <div className="space-y-4">
            {complaints.map(c => <ComplaintCard key={c.id} complaint={c} basePath="/citizen" />)}
          </div>
        )}
      </div>
    </div>
  )
}
