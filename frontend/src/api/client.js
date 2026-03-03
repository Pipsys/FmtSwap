/**
 * Axios instance for the backend API.
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

let csrfToken = null

export async function fetchCsrfToken() {
  try {
    const res = await fetch('/api/csrf-token', { credentials: 'include' })
    const data = await res.json()
    csrfToken = data.csrf_token
  } catch (e) {
    console.warn('Не удалось получить CSRF-токен', e)
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

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      csrfToken = null
    }
    return Promise.reject(err)
  },
)

export const authApi = {
  register: (email, username, password) =>
    api.post('/auth/register', { email, username, password }),

  login: (email, password) => api.post('/auth/login', { email, password }),

  logout: () => api.post('/auth/logout'),

  me: () => api.get('/auth/me', { _isSessionCheck: true }),
}

export const convertApi = {
  upload: (file, conversionType, onProgress) => {
    const form = new FormData()
    form.append('file', file)
    form.append('conversion_type', conversionType)
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
