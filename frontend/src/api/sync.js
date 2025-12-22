import api from './index'

export const syncApi = {
  // 手动同步
  sync(frpsServerId) {
    return api.post('/sync', { frps_server_id: frpsServerId })
  }
}



