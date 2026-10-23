import api from './index'

export const builtinFrpsApi = {
  get: () => api.get('/builtin-frps'),
  save: data => api.put('/builtin-frps', data, { timeout: 30000 }),
  restart: () => api.post('/builtin-frps/restart', null, { timeout: 30000 }),
  acknowledge: () => api.post('/builtin-frps/onboarding-seen'),
  token: () => api.post('/builtin-frps/token'),
  raw: () => api.get('/builtin-frps/raw-config'),
  preview: data => api.post('/builtin-frps/raw-config/preview', data),
  validateRaw: data => api.post('/builtin-frps/raw-config/validate', data, { timeout: 30000 }),
  saveRaw: data => api.put('/builtin-frps/raw-config', data, { timeout: 30000 })
}
