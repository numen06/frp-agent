import api from './index'

export const syncApi = {
  // 手动同步（使用对比分析接口）
  async compare(frpsServerId, autoUpdate = true) {
    return api.post('/analysis/compare', null, {
      params: {
        frps_server_id: frpsServerId,
        auto_update: autoUpdate
      }
    })
  }
}



