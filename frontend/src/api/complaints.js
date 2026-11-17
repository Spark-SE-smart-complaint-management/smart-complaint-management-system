import api from './client'

export const listComplaints = () => api.get('/complaints')
export const getComplaint = (id) => api.get(`/complaints/${id}`)
export const createComplaint = (data) => api.post('/complaints', data)
export const updateStatus = (id, data) => api.patch(`/complaints/${id}/status`, data)
export const getHistory = (id) => api.get(`/complaints/${id}/history`)
export const reopenComplaint = (id, data) => api.post(`/complaints/${id}/reopen`, data)
export const listCategories = () => api.get('/categories')
export const listComments = (id) => api.get(`/complaints/${id}/comments`)
export const addComment = (id, data) => api.post(`/complaints/${id}/comments`, data)
export const assignComplaint = (id, data) => api.post(`/complaints/${id}/assign`, data)
export const autoAssign = (id, data) => api.post(`/complaints/${id}/auto-assign`, data)
export const uploadAttachment = (id, file) => {
  const form = new FormData()
  form.append('file', file)
  return api.post(`/complaints/${id}/attachments`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export const listAttachments = (id) => api.get(`/complaints/${id}/attachments`)
