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
  upload: (input, conversionType, onProgress) => {
    const form = new FormData()
    const files = Array.isArray(input) ? input : [input]
    if (files.length > 1) {
      files.forEach((file) => form.append('files', file))
    } else if (files[0]) {
      form.append('file', files[0])
    }
    form.append('conversion_type', conversionType)
    return api.post('/convert', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress) onProgress(Math.round((e.loaded * 100) / e.total))
      },
    })
  },
  status: (taskId) => api.get(`/convert/${taskId}`),
  history: (page = 1, pageSize = 10, conversionType = '') =>
    api.get('/convert/history', {
      params: {
        limit: pageSize,
        offset: Math.max(0, (page - 1) * pageSize),
        conversion_type: conversionType || undefined,
      },
    }),
  deleteTask: (taskId) => api.delete(`/convert/${taskId}`),
  downloadUrl: (filename) => `/api/download/${filename}`,
}

export default api
