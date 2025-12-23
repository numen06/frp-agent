import api from './index'

export const settingsApi = {
  // 获取用户设置
  getUserSettings() {
    return api.get('/settings/user')
  },
  
  // 检查是否需要强制修改密码
  checkPasswordRequirement() {
    return api.get('/settings/check-password')
  },
  
  // 修改密码
  changePassword(data) {
    return api.post('/settings/password', data)
  }
}



