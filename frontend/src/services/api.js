import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'


const api = axios.create({
  baseURL: `${API_BASE_URL.replace(/\/+$/, '')}/api`,
  headers: { Accept: 'application/json' },
  timeout: 10000,
  withCredentials: true,
  withXSRFToken: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
})

let accessToken = null
let csrfToken = null
let refreshPromise = null

export function setAccessToken(token) {
  accessToken = token
}

export function setCsrfToken(token) {
  csrfToken = token
}

export function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = api.post('/auth/refresh/').then(({ data }) => {
      setAccessToken(data.access_token)
      return data.access_token
    }).finally(() => { refreshPromise = null })
  }
  return refreshPromise
}

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  if (csrfToken && !['get', 'head', 'options'].includes((config.method || 'get').toLowerCase())) {
    config.headers['X-CSRFToken'] = csrfToken
  }
  return config
})

api.interceptors.response.use((response) => response, async (error) => {
  const request = error.config
  const url = request?.url || ''
  const authFlowRequest = /\/auth\/(login|register|verify-email|resend-verification|refresh|logout|csrf)\//.test(url)
  if (error.response?.status !== 401 || !request || request._retried || authFlowRequest) {
    return Promise.reject(error)
  }

  request._retried = true
  try {
    const token = await refreshAccessToken()
    request.headers.Authorization = `Bearer ${token}`
    return api(request)
  } catch (refreshError) {
    setAccessToken(null)
    window.dispatchEvent(new Event('cinesplit:auth-expired'))
    return Promise.reject(refreshError)
  }
})

export default api
