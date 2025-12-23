import api from './index'

export const groupApi = {
  // 获取分组列表（分页）
  getGroups(params = {}) {
    return api.get('/groups', { params })
  },
  
  // 获取所有分组名称列表（用于下拉选择）
  getGroupsList(frpsServerId = null) {
    const params = {}
    if (frpsServerId) {
      params.frps_server_id = frpsServerId
    }
    return api.get('/groups/list', { params })
  },
  
  // 创建分组
  createGroup(data) {
    return api.post('/groups', data)
  },
  
  // 更新分组（重命名）
  updateGroup(oldName, newName, params = {}) {
    return api.put(`/groups/${encodeURIComponent(oldName)}`, {
      new_name: newName,
      ...params
    })
  },
  
  // 删除分组
  deleteGroup(groupName, reassignGroup = '') {
    return api.delete(`/groups/${encodeURIComponent(groupName)}`, {
      params: { reassign_group: reassignGroup }
    })
  },
  
  // 自动分析分组
  autoAnalyzeGroups(frpsServerId) {
    return api.post('/groups/auto-analyze', { frps_server_id: frpsServerId })
  }
}



