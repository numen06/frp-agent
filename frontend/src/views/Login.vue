<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-10">
    <div class="w-full max-w-md">
      <div class="mb-6 text-center">
        <a href="/" class="inline-flex flex-col items-center no-underline">
          <div class="mb-3 animate-float text-blue-600">
            <FrpLogo :size="48" color="currentColor" :animated="true" />
          </div>
          <div class="flex items-baseline text-3xl font-bold tracking-tight">
            <span class="text-blue-600 font-extrabold">FRP</span>
            <span class="text-gray-500 font-semibold ml-0.5">-AGENT</span>
          </div>
          <div class="mt-1 text-sm font-medium tracking-wide text-gray-500">代理管理系统</div>
        </a>
      </div>

      <div class="rounded-xl border border-gray-200 bg-white shadow-sm p-6">
        <h2 class="mb-5 text-center text-2xl font-semibold text-gray-900">登录到账户</h2>
        <div v-if="errorMessage" class="alert alert-danger mb-4" role="alert">
          {{ errorMessage }}
        </div>
        <form @submit.prevent="handleLogin" autocomplete="off" novalidate class="space-y-4">
          <div>
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
          <div>
            <label class="form-label">密码</label>
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
          <button type="submit" class="btn btn-primary w-full" :disabled="loading">
            <span v-if="loading" class="spinner-border mr-2" role="status" aria-hidden="true"></span>
            {{ loading ? '登录中...' : '登录' }}
          </button>
        </form>
      </div>

      <div class="mt-4 text-center text-sm text-gray-500">
        FRP-AGENT
        <template v-if="appVersion"> v{{ appVersion }}</template>
        <template v-else> …</template>
        &copy; 2025
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import FrpLogo from '@/components/FrpLogo.vue'
import { getPublicVersion } from '@/api/index'

const router = useRouter()
const authStore = useAuthStore()
const appVersion = ref('')

const loading = ref(false)
const errorMessage = ref('')

const loginForm = reactive({
  username: '',
  password: ''
})

onMounted(async () => {
  try {
    const res = await getPublicVersion()
    if (res?.success && res.version) {
      appVersion.value = res.version
    }
  } catch {
    // 版本展示非关键
  }
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
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}

.animate-float {
  animation: float 3s ease-in-out infinite;
}
</style>

