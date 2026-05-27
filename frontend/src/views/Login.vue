<template>
  <div class="flex min-h-screen items-center justify-center bg-gray-50 px-3 py-8 sm:px-4 sm:py-10">
    <div class="w-full max-w-md">
      <div class="mb-6 text-center">
        <a href="/" class="inline-flex flex-col items-center no-underline">
          <div class="mb-3 animate-float text-blue-600">
            <FrpLogo :size="72" color="currentColor" :animated="true" />
          </div>
          <div class="flex items-baseline text-3xl font-bold tracking-tight">
            <span class="text-blue-600 font-extrabold">FRP</span>
            <span class="text-gray-500 font-semibold ml-0.5">-AGENT</span>
          </div>
          <div class="mt-1 text-sm font-medium tracking-wide text-gray-500">代理管理系统</div>
        </a>
      </div>

      <div class="rounded-xl border border-gray-200 bg-white p-4 shadow-sm sm:p-6">
        <h2 class="mb-5 text-center text-xl font-semibold text-gray-900 sm:text-2xl">登录到账户</h2>
        <div v-if="errorMessage" class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
          {{ errorMessage }}
        </div>
        <form @submit.prevent="handleLogin" autocomplete="off" novalidate class="space-y-4">
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">用户名</label>
            <input
              type="text"
              class="block min-h-10 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              v-model="loginForm.username"
              placeholder="请输入用户名"
              autocomplete="off"
              autofocus
              required
            />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">密码</label>
            <input
              type="password"
              class="block min-h-10 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              v-model="loginForm.password"
              placeholder="请输入密码"
              autocomplete="off"
              required
              @keyup.enter="handleLogin"
            />
          </div>
          <button
            type="submit"
            class="btn btn-md btn-primary min-h-11 w-full"
            :disabled="loading"
          >
            <span
              v-if="loading"
              class="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-white/30 border-t-white"
              role="status"
              aria-hidden="true"
            ></span>
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

