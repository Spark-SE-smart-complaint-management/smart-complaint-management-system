import api from './client'

export const listNotifications = () => api.get('/notifications')
export const markRead = (id) => api.patch(`/notifications/${id}/read`)
export const markAllRead = () => api.patch('/notifications/read-all')
export const getPreferences = () => api.get('/notifications/preferences')
export const setPreferences = (data) => api.put('/notifications/preferences', data)
