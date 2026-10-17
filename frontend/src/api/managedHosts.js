import api from './index'

export const managedHostsApi = {
  context: () => api.get('/managed-hosts/context'),
  gatewayInfo: () => api.get('/managed-hosts/gateway/info'),
  dockerGatewayCa: () => api.get('/managed-hosts/gateway/docker-ca', { responseType: 'blob' }),
  dockerClientCert: (id) => api.get(`/managed-hosts/${id}/docker-client-cert`, { responseType: 'blob' }),
  list: (params = {}) => api.get('/managed-hosts', { params }),
  create: (data) => api.post('/managed-hosts', data),
  update: (id, data) => api.put(`/managed-hosts/${id}`, data),
  remove: (id) => api.delete(`/managed-hosts/${id}`),
  test: (id) => api.post(`/managed-hosts/${id}/test`),
  rdpFile: (id) => api.post(`/managed-hosts/${id}/rdp-file`, null, { responseType: 'blob' }),
  rdpFingerprint: (data) => api.post('/managed-hosts/rdp/fingerprint', data),
  execute: (id, data) => api.post(`/managed-hosts/${id}/commands`, data),
  containers: (id, params = {}) => api.get(`/managed-hosts/${id}/docker/containers`, { params }),
  dockerAction: (id, data) => api.post(`/managed-hosts/${id}/docker/actions`, data),
  subjects: (params = {}) => api.get('/managed-hosts/access/subjects', { params }),
  createUser: (data) => api.post('/managed-hosts/access/users', data),
  updateUser: (id, data) => api.put(`/managed-hosts/access/users/${id}`, data),
  grants: (params = {}) => api.get('/managed-hosts/access/grants', { params }),
  createGrant: (data) => api.post('/managed-hosts/access/grants', data),
  updateGrant: (id, data) => api.put(`/managed-hosts/access/grants/${id}`, data),
  removeGrant: (id) => api.delete(`/managed-hosts/access/grants/${id}`),
  auditDetail: (id) => api.get(`/managed-hosts/audit/logs/${id}`),
  deleteAudit: (ids) => api.post('/managed-hosts/audit/delete', { ids }),
  cleanupAudit: (data) => api.post('/managed-hosts/audit/cleanup', data),
  audit: (params) => api.get('/managed-hosts/audit/logs', { params })
}

export const dockerCredentialsApi = {
  list: (params = {}) => api.get('/docker-credentials', { params }),
  get: (id) => api.get(`/docker-credentials/${id}`),
  create: (data) => api.post('/docker-credentials', data),
  update: (id, data) => api.put(`/docker-credentials/${id}`, data),
  remove: (id) => api.delete(`/docker-credentials/${id}`)
}
