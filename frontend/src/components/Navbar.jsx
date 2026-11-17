import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Bell, LogOut, Menu, X, AlertCircle } from 'lucide-react'
import clsx from 'clsx'

export default function Navbar({ unreadCount = 0 }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const roleGradient = {
    Complainant: 'from-blue-500 to-cyan-500',
    Staff: 'from-green-500 to-teal-500',
    Administrator: 'from-violet-500 to-purple-500',
  }[user?.role] || 'from-blue-500 to-violet-500'

  const links = {
    Complainant: [
      { to: '/citizen/dashboard', label: 'My Complaints' },
      { to: '/citizen/submit', label: 'Submit Complaint' },
      { to: '/citizen/notifications', label: 'Notifications' },
    ],
    Staff: [
      { to: '/staff/dashboard', label: 'Dashboard' },
      { to: '/staff/assigned', label: 'Assigned' },
    ],
    Administrator: [
      { to: '/admin/dashboard', label: 'Dashboard' },
      { to: '/admin/complaints', label: 'Complaints' },
      { to: '/admin/users', label: 'Users' },
      { to: '/admin/reports', label: 'Reports' },
    ],
  }[user?.role] || []

  return (
    <nav className="bg-white border-b border-gray-100 shadow-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <Link to="/" className="flex items-center gap-2">
            <div className={clsx('w-8 h-8 rounded-lg bg-gradient-to-br flex items-center justify-center', roleGradient)}>
              <AlertCircle className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-gray-900 hidden sm:block">Smart CMS</span>
          </Link>

          <div className="hidden md:flex items-center gap-1">
            {links.map((l) => (
              <Link key={l.to} to={l.to}
                className="text-sm font-medium text-gray-600 hover:text-blue-600 px-3 py-2 rounded-lg hover:bg-blue-50 transition-colors">
                {l.label}
              </Link>
            ))}
          </div>

          <div className="flex items-center gap-3">
            {user?.role === 'Complainant' && (
              <Link to="/citizen/notifications" className="relative p-2 rounded-lg hover:bg-gray-100 transition-colors">
                <Bell className="w-5 h-5 text-gray-600" />
                {unreadCount > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </Link>
            )}
            <div className="flex items-center gap-2">
              <div className={clsx('w-8 h-8 rounded-full bg-gradient-to-br flex items-center justify-center text-white text-xs font-bold', roleGradient)}>
                {user?.name?.[0]?.toUpperCase()}
              </div>
              <span className="text-sm font-medium text-gray-700 hidden sm:block">{user?.name}</span>
            </div>
            <button onClick={handleLogout}
              className="p-2 rounded-lg hover:bg-red-50 text-gray-500 hover:text-red-600 transition-colors" title="Logout">
              <LogOut className="w-4 h-4" />
            </button>
            <button className="md:hidden p-2" onClick={() => setOpen(!open)}>
              {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {open && (
        <div className="md:hidden border-t border-gray-100 bg-white px-4 py-2 space-y-1">
          {links.map((l) => (
            <Link key={l.to} to={l.to} onClick={() => setOpen(false)}
              className="block text-sm font-medium text-gray-600 hover:text-blue-600 px-3 py-2 rounded-lg hover:bg-blue-50">
              {l.label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  )
}
