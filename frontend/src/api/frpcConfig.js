import api from './index'

export const frpcConfigApi = {
  getConfigByGroupQuick(groupName, params = {}) {
    return api.get(`/frpc/config/group/${encodeURIComponent(groupName)}`, {
      params,
      responseType: 'text'
    })
  },

  generateConfigByProxies(data) {
    return api.post('/frpc/config/by-proxies', data)
  }
}
