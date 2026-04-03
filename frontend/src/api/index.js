import axios from 'axios'
import { logRequest, logResponse, logError } from '@/utils/request'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000
})

// 开发环境启用请求日志
if (import.meta.env.DEV) {
  api.interceptors.request.use(
    (config) => {
      logRequest(config)
      return config
    },
    (error) => {
      logError(error)
      return Promise.reject(error)
    }
  )
  
  api.interceptors.response.use(
    (response) => {
      logResponse(response)
      return response
    },
    (error) => {
      logError(error)
      return Promise.reject(error)
    }
  )
}

// 请求拦截器 - 添加认证头
api.interceptors.request.use(
  (config) => {
    // 从 localStorage 直接读取 token，避免 store 未初始化的问题
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Basic ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器 - 处理错误
api.interceptors.response.use(
  (response) => {
    // 对于 text/plain 响应，直接返回 data（已经是字符串）
    // 对于 JSON 响应，返回解析后的对象
    return response.data
  },
  (error) => {
    const skipAuthRedirect = Boolean(error?.config?.skipAuthRedirect)
    if (error.response?.status === 401 && !skipAuthRedirect) {
      // 清除认证信息
      localStorage.removeItem('auth_token')
      localStorage.removeItem('username')
      localStorage.removeItem('currentServerId')
      // 跳转到登录页
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    
    // 处理 FastAPI 验证错误
    if (error.response?.status === 422 && error.response?.data?.detail) {
      const detail = error.response.data.detail
      if (Array.isArray(detail)) {
        const errorMsg = detail.map(e => 
          `${e.loc.join('.')}: ${e.msg}`
        ).join('\n')
        return Promise.reject(new Error(errorMsg))
      }
    }
    
    // 处理文本响应错误（如 PlainTextResponse）
    if (error.response?.data && typeof error.response.data === 'string') {
      return Promise.reject(new Error(error.response.data))
    }
    
    const errorMessage = error.response?.data?.detail || error.message || '请求失败'
    return Promise.reject(new Error(errorMessage))
  }
)

/** 公开版本（登录页等，无需认证） */
export function getPublicVersion() {
  return api.get('/public/version', { skipAuthRedirect: true })
}

/** 当前应用版本（需认证） */
export function getSystemVersion() {
  return api.get('/system/version')
}

/**
 * 检查 Gitee Release 更新（需认证）
 * @param {boolean} [force] 为 true 时跳过服务端缓存
 */
export function checkVersionUpdate(force = false) {
  return api.get('/system/version/check-update', {
    params: force ? { force: true } : undefined
  })
}

export default api

