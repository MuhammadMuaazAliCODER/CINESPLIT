import api from './api.js'

export function getMovies(params = {}, config = {}) {
  return api.get('/movies/', { ...config, params })
}

export function getFeaturedMovies(params = {}, config = {}) {
  return api.get('/movies/featured/', { ...config, params })
}

export function getMovieGenres(config = {}) {
  return api.get('/movies/genres/', config)
}

export function getMovie(slug, config = {}) {
  return api.get(`/movies/${encodeURIComponent(slug)}/`, config)
}

export function getAdminMovies(params = {}, config = {}) {
  return api.get('/admin/movies/', { ...config, params })
}

export function createAdminMovie(data) {
  return api.post('/admin/movies/', data)
}

export function updateAdminMovie(movieId, data) {
  return api.patch(`/admin/movies/${encodeURIComponent(movieId)}/`, data)
}

export function deleteAdminMovie(movieId, slug) {
  return api.delete(`/admin/movies/${encodeURIComponent(movieId)}/`, { data: { confirmation: slug } })
}
