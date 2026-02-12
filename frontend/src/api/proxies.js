import api from './index'

export const proxyApi = {
  // 获取代理列表
  getProxies(params = {}) {
    return api.get('/proxies', { params })
  },
  
  // 获取代理详情
  getProxy(id) {
    return api.get(`/proxies/${id}`)
  },
  
  // 创建代理
  createProxy(data) {
    return api.post('/proxies', data)
  },
  
  // 更新代理
  updateProxy(id, data) {
    return api.put(`/proxies/${id}`, data)
  },
  
  // 批量更新代理分组
  async bulkUpdateGroup(proxyIds, groupName) {
    // 逐个更新代理分组
    const promises = proxyIds.map(id => 
      api.put(`/proxies/${id}`, { group_name: groupName })
    )
    return Promise.all(promises)
  },
  
  // 删除代理
  deleteProxy(id) {
    return api.delete(`/proxies/${id}`)
  },
  
  // 批量识别端口
  batchDetectPorts(proxyIds) {
    return api.post('/proxies/batch-detect-ports', { proxy_ids: proxyIds })
  },

  // 清理重复代理（同一服务器下同名代理只保留一条）
  cleanDuplicates(frpsServerId = null) {
    const params = frpsServerId ? { frps_server_id: frpsServerId } : {}
    return api.post('/proxies/clean-duplicates', null, { params })
  }
}
