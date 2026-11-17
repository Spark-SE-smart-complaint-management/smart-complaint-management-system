import api from './client'

export const listUsers = () => api.get('/users')
export const createUser = (data) => api.post('/users', data)
export const updateUser = (id, data) => api.patch(`/users/${id}`, data)
export const exportCSV = (params) => api.get('/reports/export/csv', { params, responseType: 'blob' })
export const exportPDF = (params) => api.get('/reports/export/pdf', { params, responseType: 'blob' })
export const listNotificationHistory = (params) => api.get('/notifications/history', { params })
