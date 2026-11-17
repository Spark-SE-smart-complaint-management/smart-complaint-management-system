import React, { useEffect, useState } from 'react'
import Navbar from '../../components/Navbar'
import { listNotifications, markAllRead, markRead } from '../../api/notifications'
import toast from 'react-hot-toast'
import { Bell, BellOff, Check } from 'lucide-react'
import { format } from 'date-fns'
import clsx from 'clsx'

export default function Notifications() {
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const res = await listNotifications()
      setNotifications(res.data)
    } catch { toast.error('Failed to load notifications') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const handleMarkAllRead = async () => {
    await markAllRead(); toast.success('All marked as read'); load()
  }

  const handleMarkOne = async (id) => {
    await markRead(id)
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n))
  }

  const unread = notifications.filter(n => !n.is_read).length

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar unreadCount={unread} />
      <div className="max-w-2xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
            <p className="text-gray-500 text-sm mt-1">{unread} unread</p>
          </div>
          {unread > 0 && (
            <button onClick={handleMarkAllRead} className="btn-secondary flex items-center gap-2 text-sm">
              <Check className="w-4 h-4" /> Mark all read
            </button>
          )}
        </div>

        {!loading && notifications.length === 0 ? (
          <div className="card text-center py-16">
            <BellOff className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No notifications yet</p>
          </div>
        ) : (
          <div className="space-y-2">
            {notifications.map(n => (
              <div key={n.id}
                className={clsx('card cursor-pointer hover:shadow-md transition-all', !n.is_read && 'border-l-4 border-l-blue-500')}
                onClick={() => !n.is_read && handleMarkOne(n.id)}>
                <div className="flex items-start gap-3">
                  <div className={clsx('w-8 h-8 rounded-full flex items-center justify-center shrink-0', !n.is_read ? 'bg-blue-100' : 'bg-gray-100')}>
                    <Bell className={clsx('w-4 h-4', !n.is_read ? 'text-blue-600' : 'text-gray-400')} />
                  </div>
                  <div className="flex-1">
                    <p className={clsx('text-sm', !n.is_read ? 'font-semibold text-gray-900' : 'text-gray-600')}>{n.message}</p>
                    <p className="text-xs text-gray-400 mt-1">{format(new Date(n.created_at), 'dd MMM yyyy, HH:mm')}</p>
                  </div>
                  {!n.is_read && <div className="w-2 h-2 rounded-full bg-blue-500 mt-1.5 shrink-0" />}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
