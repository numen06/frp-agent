import api from './index'

export const managedHostsApi = {
  context: () => api.get('/managed-hosts/context'),
  gatewayInfo: () => api.get('/managed-hosts/gateway/info'),
  dockerGatewayCa: () => api.get('/managed-hosts/gateway/docker-ca', { responseType: 'blob' }),
  list: () => api.get('/managed-hosts'),
  create: (data) => api.post('/managed-hosts', data),
  update: (id, data) => api.put(`/managed-hosts/${id}`, data),
  remove: (id) => api.delete(`/managed-hosts/${id}`),
  test: (id) => api.post(`/managed-hosts/${id}/test`),
  execute: (id, data) => api.post(`/managed-hosts/${id}/commands`, data),
  containers: (id) => api.get(`/managed-hosts/${id}/docker/containers`),
  dockerAction: (id, data) => api.post(`/managed-hosts/${id}/docker/actions`, data),
  subjects: () => api.get('/managed-hosts/access/subjects'),
  createUser: (data) => api.post('/managed-hosts/access/users', data),
  updateUser: (id, data) => api.put(`/managed-hosts/access/users/${id}`, data),
  grants: () => api.get('/managed-hosts/access/grants'),
  createGrant: (data) => api.post('/managed-hosts/access/grants', data),
  updateGrant: (id, data) => api.put(`/managed-hosts/access/grants/${id}`, data),
  removeGrant: (id) => api.delete(`/managed-hosts/access/grants/${id}`),
  audit: (params) => api.get('/managed-hosts/audit/logs', { params })
}

export const dockerCredentialsApi = {
  list: () => api.get('/docker-credentials'),
  create: (data) => api.post('/docker-credentials', data),
  update: (id, data) => api.put(`/docker-credentials/${id}`, data),
  remove: (id) => api.delete(`/docker-credentials/${id}`)
}
