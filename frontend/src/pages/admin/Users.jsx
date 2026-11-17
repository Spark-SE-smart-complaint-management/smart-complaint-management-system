import React, { useEffect, useState } from 'react'
import { listUsers, createUser, updateUser } from '../../api/admin'
import Navbar from '../../components/Navbar'
import LoadingSpinner from '../../components/LoadingSpinner'
import toast from 'react-hot-toast'
import { UserPlus, Shield, User, Wrench } from 'lucide-react'
import clsx from 'clsx'

export default function AdminUsers() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', password: '', role: 'Staff', department: '', phone: '' })

  const load = () => {
    listUsers().then(r => setUsers(r.data)).catch(() => toast.error('Failed')).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    try {
      await createUser(form)
      toast.success('User created!')
      setShowForm(false)
      setForm({ name: '', email: '', password: '', role: 'Staff', department: '', phone: '' })
      load()
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to create user') }
  }

  const toggleActive = async (user) => {
    try {
      await updateUser(user.id, { is_active: !user.is_active })
      toast.success(`User ${user.is_active ? 'deactivated' : 'activated'}`)
      load()
    } catch { toast.error('Failed to update user') }
  }

  const roleIcon = { Complainant: User, Staff: Wrench, Administrator: Shield }
  const roleColor = { Complainant: 'blue', Staff: 'green', Administrator: 'violet' }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
          <button onClick={() => setShowForm(!showForm)} className="btn-primary flex items-center gap-2">
            <UserPlus className="w-4 h-4" /> Add User
          </button>
        </div>

        {showForm && (
          <div className="card mb-6">
            <h3 className="font-semibold text-gray-900 mb-4">Create Staff / Admin Account</h3>
            <form onSubmit={handleCreate} className="grid grid-cols-2 gap-4">
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                <input className="input-field" value={form.name} onChange={e => setForm({...form, name: e.target.value})} required /></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input type="email" className="input-field" value={form.email} onChange={e => setForm({...form, email: e.target.value})} required /></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input type="password" className="input-field" value={form.password} onChange={e => setForm({...form, password: e.target.value})} required /></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
                <select className="input-field" value={form.role} onChange={e => setForm({...form, role: e.target.value})}>
                  <option value="Staff">Staff</option>
                  <option value="Administrator">Administrator</option>
                </select></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Department</label>
                <input className="input-field" value={form.department} onChange={e => setForm({...form, department: e.target.value})} /></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                <input className="input-field" value={form.phone} onChange={e => setForm({...form, phone: e.target.value})} /></div>
              <div className="col-span-2 flex gap-3">
                <button type="submit" className="btn-primary">Create User</button>
                <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">Cancel</button>
              </div>
            </form>
          </div>
        )}

        {loading ? <LoadingSpinner /> : (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  {['Name', 'Email', 'Role', 'Department', 'Status', 'Actions'].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {users.map(u => {
                  const Icon = roleIcon[u.role] || User
                  const color = roleColor[u.role] || 'blue'
                  return (
                    <tr key={u.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className={`w-7 h-7 rounded-full bg-${color}-100 flex items-center justify-center`}>
                            <Icon className={`w-3.5 h-3.5 text-${color}-600`} />
                          </div>
                          <span className="font-medium text-gray-900">{u.name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-500">{u.email}</td>
                      <td className="px-4 py-3">
                        <span className={`badge bg-${color}-100 text-${color}-700`}>{u.role}</span>
                      </td>
                      <td className="px-4 py-3 text-gray-500">{u.department || '—'}</td>
                      <td className="px-4 py-3">
                        <span className={clsx('badge', u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600')}>
                          {u.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <button onClick={() => toggleActive(u)}
                          className={clsx('text-xs px-3 py-1 rounded-lg font-medium transition-colors',
                            u.is_active ? 'bg-red-50 text-red-600 hover:bg-red-100' : 'bg-green-50 text-green-600 hover:bg-green-100')}>
                          {u.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
