import api from './index'

export const clientUpgradeApi = {
  scanProxy(proxyId, body) {
    return api.post(`/proxies/${proxyId}/ssh-upgrade/scan`, body)
  },

  upgradeProxy(proxyId, body) {
    return api.post(`/proxies/${proxyId}/ssh-upgrade`, body)
  },

  verifyProxy(proxyId, expectedVersion) {
    return api.get(`/proxies/${proxyId}/ssh-upgrade/verify`, {
      params: { expected_version: expectedVersion }
    })
  },

  scanGroup(groupName, frpsServerId, body) {
    return api.post(`/groups/${encodeURIComponent(groupName)}/ssh-upgrade/scan`, body, {
      params: { frps_server_id: frpsServerId }
    })
  },

  upgradeGroup(groupName, frpsServerId, body) {
    return api.post(`/groups/${encodeURIComponent(groupName)}/ssh-upgrade`, body, {
      params: { frps_server_id: frpsServerId }
    })
  },

  getJob(jobId) {
    return api.get(`/client-upgrade/jobs/${jobId}`)
  },

  getJobResults(jobId) {
    return api.get(`/client-upgrade/jobs/${jobId}/results`)
  }
}
