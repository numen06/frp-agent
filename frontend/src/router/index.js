import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue')
      },
      {
        path: 'servers',
        name: 'ServerManage',
        component: () => import('@/views/ServerManagePage.vue')
      },
      {
        path: 'proxies',
        name: 'ProxyList',
        component: () => import('@/views/ProxyList.vue')
      },
      {
        path: 'groups',
        name: 'GroupManage',
        component: () => import('@/views/GroupManagePage.vue')
      },
      {
        path: 'converter',
        name: 'IniConverter',
        component: () => import('@/views/IniConverterPage.vue')
      },
      {
        path: 'api-keys',
        name: 'ApiKeys',
        component: () => import('@/views/ApiKeysPage.vue')
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    // 如果已登录，检查是否需要强制修改密码
    const checkPassword = async () => {
      try {
        const axios = (await import('axios')).default
        const token = localStorage.getItem('auth_token')
        
        if (token) {
          const axiosInstance = axios.create({
            baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
            timeout: 5000
          })
          
          const result = await axiosInstance.get('/settings/check-password', {
            headers: { 'Authorization': `Basic ${token}` }
          })
          
          if (result.data?.require_password_change) {
            next({
              path: '/dashboard',
              query: { forcePasswordChange: 'true', reason: result.data.reason }
            })
            return
          }
        }
      } catch (error) {
        // 检查失败不影响正常登录流程
        console.warn('检查密码要求失败:', error)
      }
      
      next('/dashboard')
    }
    
    checkPassword()
  } else {
    // 如果访问需要认证的页面，检查是否需要强制修改密码
    if (to.meta.requiresAuth && authStore.isAuthenticated && to.path !== '/dashboard' && !to.query.forcePasswordChange) {
      const checkPassword = async () => {
        try {
          const axios = (await import('axios')).default
          const token = localStorage.getItem('auth_token')
          
          if (token) {
            const axiosInstance = axios.create({
              baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
              timeout: 5000
            })
            
            const result = await axiosInstance.get('/settings/check-password', {
              headers: { 'Authorization': `Basic ${token}` }
            })
            
            if (result.data?.require_password_change) {
              next({
                path: '/dashboard',
                query: { forcePasswordChange: 'true', reason: result.data.reason }
              })
              return
            }
          }
        } catch (error) {
          // 检查失败不影响正常访问
          console.warn('检查密码要求失败:', error)
        }
        
        next()
      }
      
      checkPassword()
    } else {
      next()
    }
  }
})

export default router



