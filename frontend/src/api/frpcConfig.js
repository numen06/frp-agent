import api from './index'

export const frpcConfigApi = {
  // 根据分组生成配置
  generateConfigByGroup(data) {
    return api.post('/frpc/config/by-group', data, {
      responseType: 'text'
    })
  },
  
  // 根据代理ID列表生成配置
  generateConfigByProxies(data) {
    return api.post('/frpc/config/by-proxies', data)
  },
  
  // 获取分组配置（GET方式）
  getConfigByGroup(groupName, params = {}) {
    return api.get(`/frpc/config/by-group/${encodeURIComponent(groupName)}`, {
      params,
      responseType: 'text'
    })
  }
}

