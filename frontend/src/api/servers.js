import api from './index'

export const serverApi = {
  // 获取服务器列表
  getServers(params = {}) {
    return api.get('/servers', { params })
  },
  
  // 获取服务器详情
  getServer(id) {
    return api.get(`/servers/${id}`)
  },
  
  // 创建服务器
  createServer(data) {
    return api.post('/servers', data)
  },
  
  // 更新服务器
  updateServer(id, data) {
    return api.put(`/servers/${id}`, data)
  },
  
  // 删除服务器
  deleteServer(id) {
    return api.delete(`/servers/${id}`)
  },
  
  // 测试服务器连接
  testServer(id) {
    return api.post(`/servers/${id}/test`)
  }
}



