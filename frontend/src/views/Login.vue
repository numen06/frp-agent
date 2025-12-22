<template>
  <div class="page page-center">
    <div class="container container-tight py-4">
      <div class="text-center mb-4">
        <a href="/" class="navbar-brand navbar-brand-autodark">
          <span class="navbar-brand-icon">
            <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
              <path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0" />
              <path d="M12 3a9 9 0 0 0 9 9" />
              <path d="M12 21a9 9 0 0 1 -9 -9" />
            </svg>
          </span>
          <span class="navbar-brand-text">frp-agent</span>
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
        frp-agent v1.0 &copy; 2025
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

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
    await authStore.login(loginForm.username, loginForm.password)
    router.push('/dashboard')
  } catch (error) {
    errorMessage.value = error.message || '登录失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

