import api from './index'

export const apiKeysApi = {
  // 获取 API Key 列表
  list(skip = 0, limit = 100) {
    return api.get('/api-keys', {
      params: { skip, limit }
    })
  },

  // 获取单个 API Key
  get(id, params = {}) {
    return api.get(`/api-keys/${id}`, { params })
  },

  // 创建 API Key
  create(data) {
    return api.post('/api-keys', data)
  },

  // 更新 API Key
  update(id, data) {
    return api.put(`/api-keys/${id}`, data)
  },

  // 删除 API Key
  delete(id) {
    return api.delete(`/api-keys/${id}`)
  }
}

