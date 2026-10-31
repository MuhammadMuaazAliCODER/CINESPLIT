import api from './api.js'

export function getPublicChapters(movieSlug, config = {}) {
  return api.get(`/movies/${encodeURIComponent(movieSlug)}/chapters/`, config)
}

export function getAdminChapters(movieId, config = {}) {
  return api.get(`/admin/movies/${encodeURIComponent(movieId)}/chapters/`, config)
}

export function createAdminChapter(movieId, data) {
  return api.post(`/admin/movies/${encodeURIComponent(movieId)}/chapters/`, data)
}

export function updateAdminChapter(movieId, chapterId, data) {
  return api.patch(`/admin/movies/${encodeURIComponent(movieId)}/chapters/${encodeURIComponent(chapterId)}/`, data)
}

export function deleteAdminChapter(movieId, chapterId) {
  return api.delete(`/admin/movies/${encodeURIComponent(movieId)}/chapters/${encodeURIComponent(chapterId)}/`)
}

export function reorderAdminChapters(movieId, chapterIds) {
  return api.post(`/admin/movies/${encodeURIComponent(movieId)}/chapters/reorder/`, { chapter_ids: chapterIds })
}
