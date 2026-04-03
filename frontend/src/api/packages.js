import api from './index'

export const packagesApi = {
  list(params = {}) {
    return api.get('/packages', { params })
  },

  upload(formData) {
    return api.post('/packages/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
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

  getInstallScript(params) {
    return api.get('/packages/install-script', { params })
  },

  getPlatforms(params = {}) {
    return api.get('/packages/platforms', { params })
  },

  getScriptTemplates() {
    return api.get('/packages/script-templates')
  },

  updateScriptTemplate(platform, script_template) {
    return api.put(`/packages/script-templates/${platform}`, { script_template })
  }
}
