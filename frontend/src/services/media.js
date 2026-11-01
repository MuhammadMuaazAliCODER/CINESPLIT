import api from './api.js'

export const getAdminMedia = (type, id, config = {}) => api.get(`/admin/media/${encodeURIComponent(type)}/${encodeURIComponent(id)}/`, config)
export const uploadAdminMedia = (type, id, role, file, onUploadProgress) => {
  const body = new FormData()
  body.append('file', file)
  return api.post(`/admin/media/${encodeURIComponent(type)}/${encodeURIComponent(id)}/${encodeURIComponent(role)}/`, body, {
    timeout: 15 * 60 * 1000,
    onUploadProgress,
  })
}
