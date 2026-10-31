import api, { refreshAccessToken, setCsrfToken } from './api'

export async function initializeCsrf() {
  const { data } = await api.get('/auth/csrf/')
  setCsrfToken(data.csrf_token)
}

export async function registerAccount(data) {
  await initializeCsrf()
  return api.post('/auth/register/', data)
}

export async function verifyEmail(data) {
  await initializeCsrf()
  return api.post('/auth/verify-email/', data)
}

export async function resendVerification(data) {
  await initializeCsrf()
  return api.post('/auth/resend-verification/', data)
}

export async function loginAccount(data) {
  await initializeCsrf()
  return api.post('/auth/login/', data)
}

export async function refreshSession() {
  await initializeCsrf()
  return refreshAccessToken().then((access_token) => ({ data: { access_token } }))
}

export async function logoutAccount() {
  await initializeCsrf()
  return api.post('/auth/logout/')
}

export function getCurrentUser() {
  return api.get('/auth/me/')
}

export function updateCurrentUser(data) {
  return api.patch('/auth/me/', data)
}

export function changeAccountPassword(data) {
  return api.post('/auth/change-password/', data)
}
