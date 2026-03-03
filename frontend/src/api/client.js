/**
 * Axios instance for the backend API.
 * 
 * SIMPLE APPROACH:
 * - No auto-refresh interceptor (was causing infinite loops)
 * - 401 on /auth/me at startup = not logged in (normal, no retry)
 * - 401 on other requests = redirect to login
 * - CSRF token attached to mutating requests
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

// ── CSRF token ────────────────────────────────────────────────────────────────
let csrfToken = null

export async function fetchCsrfToken() {
  try {
    const res = await fetch('/api/csrf-token', { credentials: 'include' })
    const data = await res.json()
    csrfToken = data.csrf_token
  } catch (e) {
    console.warn('Could not fetch CSRF token', e)
  }
}

api.interceptors.request.use(async (config) => {
  const mutating = ['post', 'put', 'patch', 'delete']
  if (mutating.includes(config.method)) {
    if (!csrfToken) await fetchCsrfToken()
    config.headers['x-csrf-token'] = csrfToken
  }
  return config
})

// ── 401 handler: redirect to /login (except during initial session check) ────
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const url = err.config?.url || ''
    const status = err.response?.status

    // On 401, just reject — AuthContext or the component decides what to do
    // We do NOT auto-retry or auto-redirect here to avoid loops
    if (status === 401) {
      // Only redirect if it's NOT the initial session check (/auth/me on load)
      // The AuthContext marks that call with _isSessionCheck
      if (!err.config?._isSessionCheck) {
        csrfToken = null  // reset CSRF on auth failure
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  },
)

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (email, username, password) =>
    api.post('/auth/register', { email, username, password }),

  login: (email, password) =>
    api.post('/auth/login', { email, password }),

  logout: () => api.post('/auth/logout'),

  // Mark this call as a session check so 401 won't redirect
  me: () => api.get('/auth/me', { _isSessionCheck: true }),
}

// ─── Convert ─────────────────────────────────────────────────────────────────
export const convertApi = {
  upload: (file, onProgress) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/convert', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress) onProgress(Math.round((e.loaded * 100) / e.total))
      },
    })
  },
  status: (taskId) => api.get(`/convert/${taskId}`),
  history: () => api.get('/convert/history'),
  downloadUrl: (filename) => `/api/download/${filename}`,
}

export default api
