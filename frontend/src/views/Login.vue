<template>
  <div class="page page-center">
    <div class="container container-tight py-4">
      <div class="text-center mb-4">
        <a href="/" class="login-brand">
          <div class="login-brand-icon">
            <FrpLogo :size="48" color="#206bcb" :animated="true" />
          </div>
          <div class="login-brand-text">
            <span class="brand-name">FRP</span>
            <span class="brand-suffix">-AGENT</span>
          </div>
          <div class="login-brand-subtitle">代理管理系统</div>
        </a>
      </div>
      <div class="card card-md">
        <div class="card-body">
          <h2 class="h2 text-center mb-4">登录到账户</h2>
          <div v-if="errorMessage" class="alert alert-danger" role="alert">
            {{ errorMessage }}
          </div>
          <form @submit.prevent="handleLogin" method="get" autocomplete="off" novalidate>
            <div class="mb-3">
              <label class="form-label">用户名</label>
              <input
                type="text"
                class="form-control"
                v-model="loginForm.username"
                placeholder="请输入用户名"
                autocomplete="off"
                autofocus
                required
              />
            </div>
            <div class="mb-3">
              <label class="form-label">
                密码
              </label>
              <div class="input-group input-group-flat">
                <input
                  type="password"
                  class="form-control"
                  v-model="loginForm.password"
                  placeholder="请输入密码"
                  autocomplete="off"
                  required
                  @keyup.enter="handleLogin"
                />
              </div>
            </div>
            <div class="form-footer">
              <button type="submit" class="btn btn-primary w-100" :disabled="loading">
                <span v-if="loading" class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                {{ loading ? '登录中...' : '登录' }}
              </button>
            </div>
          </form>
        </div>
      </div>
      <div class="text-center text-muted mt-3">
        FRP-AGENT v1.0 &copy; 2025
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import FrpLogo from '@/components/FrpLogo.vue'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const errorMessage = ref('')

const loginForm = reactive({
  username: '',
  password: ''
})

const handleLogin = async () => {
  if (!loginForm.username || !loginForm.password) {
    errorMessage.value = '请输入用户名和密码'
    return
  }
  
  loading.value = true
  errorMessage.value = ''
  
  try {
    const result = await authStore.login(loginForm.username, loginForm.password)
    
    // 如果需要强制修改密码，跳转到强制修改密码页面
    if (result?.requirePasswordChange) {
      router.push({
        path: '/dashboard',
        query: { forcePasswordChange: 'true', reason: result.reason }
      })
    } else {
      router.push('/dashboard')
    }
  } catch (error) {
    errorMessage.value = error.message || '登录失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-brand {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  text-decoration: none;
  margin-bottom: 1rem;
}

.login-brand-icon {
  margin-bottom: 1rem;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-5px);
  }
}

.login-brand-text {
  display: flex;
  align-items: baseline;
  font-size: 2rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-bottom: 0.5rem;
}

.login-brand-text .brand-name {
  color: #206bcb;
  font-weight: 800;
}

.login-brand-text .brand-suffix {
  color: #6c757d;
  font-weight: 600;
  margin-left: 0.1rem;
}

.login-brand-subtitle {
  font-size: 0.875rem;
  color: #6c757d;
  font-weight: 500;
  letter-spacing: 0.05em;
}
</style>

