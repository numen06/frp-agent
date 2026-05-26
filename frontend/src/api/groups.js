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
    // 对应后端: POST /api/groups/create
    return api.post('/groups/create', data)
  },

  // 更新分组（重命名）
  updateGroup(oldName, newName, params = {}) {
    // 对应后端: POST /api/groups/rename
    return api.post('/groups/rename', {
      old_name: oldName,
      new_name: newName,
      ...params
    })
  },

  // 删除分组
  deleteGroup(groupName, frpsServerId, reassignGroup = '') {
    // 对应后端: DELETE /api/groups/{group_name}?frps_server_id=...
    return api.delete(`/groups/${encodeURIComponent(groupName)}`, {
      params: {
        frps_server_id: frpsServerId,
        reassign_group: reassignGroup || undefined
      }
    })
  },

  // 自动分析分组
  autoAnalyzeGroups(frpsServerId) {
    return api.post('/groups/auto-analyze', { frps_server_id: frpsServerId })
  },

  // 重新生成分组中所有代理的远端端口
  regenerateGroupPorts(groupName, frpsServerId) {
    return api.post(`/groups/${encodeURIComponent(groupName)}/regenerate-ports`, null, {
      params: {
        frps_server_id: frpsServerId
      }
    })
  },

  // 为分组生成标准代理（http:80, docker:9000, ssh:22）
  generateDefaults(groupName, frpsServerId) {
    return api.post(`/groups/${encodeURIComponent(groupName)}/generate-defaults`, null, {
      params: {
        frps_server_id: frpsServerId
      }
    })
  },

  // 一键安装脚本 URL
  getQuickInstallUrl(params) {
    const query = new URLSearchParams()
    query.set('server_name', params.server_name)
    if (params.api_key) query.set('api_key', params.api_key)
    if (params.install_path) query.set('install_path', params.install_path)
    return `/api/groups/${encodeURIComponent(params.group_name)}/quick-install?${query.toString()}`
  },

  // 一键下载脚本 URL
  getQuickDownloadUrl(params) {
    const query = new URLSearchParams()
    query.set('server_name', params.server_name)
    if (params.api_key) query.set('api_key', params.api_key)
    if (params.install_path) query.set('install_path', params.install_path)
    return `/api/groups/${encodeURIComponent(params.group_name)}/quick-download?${query.toString()}`
  },

  // 统一部署脚本 URL（Linux）：可选 upgrade / force_config
  getDeployScriptUrl(params) {
    const query = new URLSearchParams()
    query.set('server_name', params.server_name)
    if (params.platform) query.set('platform', params.platform)
    if (params.install_path) query.set('install_path', params.install_path)
    if (params.upgrade) query.set('upgrade', 'true')
    if (params.force_config) query.set('force_config', 'true')
    if (params.verify === false) query.set('verify', 'false')
    if (params.min_online != null && params.min_online !== '') {
      const n = Number(params.min_online)
      if (!Number.isNaN(n) && n !== 1) query.set('min_online', String(n))
    }
    if (params.verify_attempts != null && params.verify_attempts !== 18) {
      query.set('verify_attempts', String(params.verify_attempts))
    }
    if (params.verify_interval != null && params.verify_interval !== 5) {
      query.set('verify_interval', String(params.verify_interval))
    }
    if (params.api_key) query.set('api_key', params.api_key)
    return `/api/groups/${encodeURIComponent(params.group_name)}/deploy?${query.toString()}`
  },

  // 从配置内容导入分组和代理
  importConfig(data) {
    return api.post('/groups/import-config', data)
  },

  // 配置导入脚本 URL（目标机 curl -sL "url" | bash）
  getImportScriptUrl(params) {
    const query = new URLSearchParams()
    query.set('frps_server_id', params.frps_server_id)
    query.set('group_name', params.group_name)
    if (params.config_path) query.set('config_path', params.config_path)
    if (params.config_format) query.set('config_format', params.config_format)
    if (params.overwrite === false) query.set('overwrite', 'false')
    if (params.api_key) query.set('api_key', params.api_key)
    return `/api/groups/import-script?${query.toString()}`
  }
}