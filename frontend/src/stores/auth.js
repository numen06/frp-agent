import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('auth_token') || '',
    username: localStorage.getItem('username') || ''
  }),
  
  getters: {
    isAuthenticated: (state) => !!state.token
  },
  
  actions: {
    // 登录
    async login(username, password) {
      const token = btoa(`${username}:${password}`)
      
      try {
        // 使用独立的 axios 实例验证登录（避免拦截器循环依赖）
        const axios = (await import('axios')).default
        const axiosInstance = axios.create({
          baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
          timeout: 10000
        })
        
        const response = await axiosInstance.get('/servers', {
          headers: {
            'Authorization': `Basic ${token}`
          }
        })
        
        // 验证成功，保存认证信息
        this.token = token
        this.username = username
        localStorage.setItem('auth_token', token)
        localStorage.setItem('username', username)
        
        // 检查是否需要强制修改密码
        try {
          const passwordCheck = await axiosInstance.get('/settings/check-password', {
            headers: {
              'Authorization': `Basic ${token}`
            }
          })
          
          if (passwordCheck.data?.require_password_change) {
            return {
              success: true,
              requirePasswordChange: true,
              reason: passwordCheck.data.reason || '检测到使用默认密码，请立即修改'
            }
          }
        } catch (checkError) {
          // 如果检查失败，不影响登录流程
          console.warn('检查密码要求失败:', checkError)
        }
        
        return {
          success: true,
          requirePasswordChange: false
        }
      } catch (error) {
        console.error('Login error:', error)
        if (error.response?.status === 401) {
          throw new Error('用户名或密码错误')
        }
        if (!error.response || error.code === 'ERR_NETWORK' || error.code === 'ECONNABORTED') {
          throw new Error('无法连接到服务器，请检查后端服务是否启动（http://localhost:8000）')
        }
        throw new Error(error.response?.data?.detail || error.message || '登录失败')
      }
    },
    
    // 退出登录
    logout() {
      this.token = ''
      this.username = ''
      localStorage.removeItem('auth_token')
      localStorage.removeItem('username')
      localStorage.removeItem('currentServerId')
    }
  }
})



