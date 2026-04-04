import api from './index'

export const packagesApi = {
  list(params = {}) {
    return api.get('/packages', { params })
  },

  upload(formData) {
    // 勿手动设置 multipart Content-Type，否则缺少 boundary，服务端无法解析表单
    return api.post('/packages/upload', formData)
  },

  sync(data) {
    return api.post('/packages/sync', data)
  },

  getReleases() {
    return api.get('/packages/releases')
  },

  checkUpdate() {
    return api.post('/packages/sync/check')
  },

  delete(id) {
    return api.delete(`/packages/${id}`)
  },

  getDownloadUrl(id, apiKey) {
    const encoded = encodeURIComponent(apiKey)
    return `/api/packages/${id}/download?api_key=${encoded}`
  },

  getInstallScriptUrl(params) {
    const query = new URLSearchParams()
    query.set('package_id', params.package_id)
    if (params.install_path) query.set('install_path', params.install_path)
    if (params.config_url) query.set('config_url', params.config_url)
    if (params.api_key) query.set('api_key', params.api_key)
    return `/api/packages/install-script?${query.toString()}`
  },

  getInstallScript(params) {
    // 生成脚本场景下即使 401 也应保留当前页面，由调用方提示错误
    return api.get('/packages/install-script', { params, skipAuthRedirect: true })
  },

  getPlatforms(params = {}) {
    return api.get('/packages/platforms', { params })
  },

  getVersions(params = {}) {
    return api.get('/packages/versions', { params })
  },

  syncPlatforms(params = {}) {
    return api.post('/packages/platforms/sync', null, { params })
  },

  getScriptTemplates() {
    return api.get('/packages/script-templates')
  },

  updateScriptTemplate(platform, script_template) {
    return api.put(`/packages/script-templates/${platform}`, { script_template })
  },

  getUpgradeScriptUrl(params) {
    const query = new URLSearchParams()
    query.set('package_id', params.package_id)
    if (params.install_path) query.set('install_path', params.install_path)
    if (params.api_key) query.set('api_key', params.api_key)
    return `/api/packages/upgrade-script?${query.toString()}`
  },

  getUpgradeScript(params) {
    return api.get('/packages/upgrade-script', { params, skipAuthRedirect: true })
  }
}
