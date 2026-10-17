<template>
  <div class="flex min-h-screen items-center justify-center bg-gray-50 px-3 py-8 sm:px-4 sm:py-10">
    <div class="w-full max-w-md">
      <div class="mb-6 text-center">
        <a href="/" class="inline-flex flex-col items-center no-underline">
          <div class="mb-3 animate-float text-blue-600">
            <FrpLogo :size="72" color="currentColor" :animated="true" />
          </div>
          <div class="flex items-baseline whitespace-nowrap text-3xl font-bold tracking-tight">
            <span class="text-blue-600 font-extrabold">FRP</span>
            <span class="text-gray-500 font-semibold">-AGENT</span>
          </div>
          <div class="mt-1 text-sm font-medium tracking-wide text-gray-500">代理配置 · 主机访问 · 统一运维</div>
        </a>
      </div>

      <div class="rounded-xl border border-gray-200 bg-white p-4 shadow-sm sm:p-6">
        <h2 class="mb-5 text-center text-xl font-semibold text-gray-900 sm:text-2xl">登录到账户</h2>
        <div v-if="errorMessage" class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
          {{ errorMessage }}
        </div>
        <form @submit.prevent="handleLogin" class="space-y-4">
          <div>
            <label for="login-username" class="mb-1 block text-sm font-medium text-gray-700">用户名</label>
            <input
              id="login-username"
              type="text"
              class="block min-h-10 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              v-model="loginForm.username"
              placeholder="请输入用户名"
              autocomplete="username"
              autofocus
              required
            />
          </div>
          <div>
            <label for="login-password" class="mb-1 block text-sm font-medium text-gray-700">密码</label>
            <input
              id="login-password"
              type="password"
              class="block min-h-10 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              v-model="loginForm.password"
              placeholder="请输入密码"
              autocomplete="current-password"
              required
            />
          </div>
          <div>
            <label for="login-captcha" class="mb-1 block text-sm font-medium text-gray-700">验证码</label>
            <div class="grid grid-cols-[minmax(0,1fr)_140px] items-center gap-3">
              <input id="login-captcha" v-model="captchaAnswer" inputmode="numeric" autocomplete="off"
                maxlength="5" pattern="[0-9]{5}" required placeholder="5 位数字"
                class="min-h-11 min-w-0 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
              <button type="button" class="flex h-11 items-center justify-center overflow-hidden rounded-lg border border-blue-100 bg-blue-50 text-xs text-blue-700"
                :disabled="captchaLoading" aria-label="刷新验证码" @click="loadCaptcha">
                <img v-if="captchaImage && !captchaLoading" :src="captchaImage" alt="登录验证码，点击可更换" class="h-full w-full object-contain">
                <span v-else>{{ captchaLoading ? '加载中…' : '点击重新获取' }}</span>
              </button>
            </div>
            <p class="mt-1.5 text-xs text-gray-500">看不清可点击图片更换，验证码 2 分钟内有效。</p>
            <p v-if="captchaError" role="alert" class="mt-1.5 text-xs text-red-600">{{ captchaError }}</p>
          </div>
          <p v-if="retrySeconds > 0" role="status" aria-live="polite" class="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
            请等待 {{ retrySeconds }} 秒后重试
          </p>
          <button
            type="submit"
            class="btn btn-md btn-primary min-h-11 w-full"
            :disabled="loading || captchaLoading || !challengeId || retrySeconds > 0"
          >
            <span
              v-if="loading"
              class="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-white/30 border-t-white"
              role="status"
              aria-hidden="true"
            ></span>
            {{ loading ? '登录中...' : retrySeconds > 0 ? `${retrySeconds} 秒后重试` : '登录' }}
          </button>
        </form>
      </div>

      <div class="mt-4 text-center text-sm text-gray-500">
        FRP-AGENT
        <template v-if="appVersion"> v{{ appVersion }}</template>
        <template v-else> …</template>
        &copy; {{ new Date().getFullYear() }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import FrpLogo from '@/components/FrpLogo.vue'
import { getPublicVersion } from '@/api/index'

const router = useRouter()
const authStore = useAuthStore()
const appVersion = ref('')

const loading = ref(false)
const errorMessage = ref('')
const captchaAnswer = ref('')
const challengeId = ref('')
const captchaImage = ref('')
const captchaLoading = ref(false)
const captchaError = ref('')
const retrySeconds = ref(0)
let retryUntil = 0
let retryTimer

async function loadCaptcha() {
  if (captchaLoading.value) return
  captchaLoading.value = true
  challengeId.value = ''
  captchaAnswer.value = ''
  captchaError.value = ''
  try {
    const { data } = await axios.get(`${import.meta.env.VITE_API_BASE_URL || '/api'}/auth/captcha`, { timeout: 10000 })
    challengeId.value = data.challenge_id
    captchaImage.value = data.image
  } catch {
    captchaImage.value = ''
    captchaError.value = '验证码获取失败，请稍后点击重试'
  } finally {
    captchaLoading.value = false
  }
}

function startBackoff(seconds) {
  clearInterval(retryTimer)
  retryUntil = Date.now() + seconds * 1000
  const tick = () => {
    retrySeconds.value = Math.max(0, Math.ceil((retryUntil - Date.now()) / 1000))
    if (!retrySeconds.value) clearInterval(retryTimer)
  }
  tick()
  if (seconds > 0) retryTimer = setInterval(tick, 250)
}

onUnmounted(() => clearInterval(retryTimer))

const loginForm = reactive({
  username: '',
  password: ''
})

onMounted(async () => {
  loadCaptcha()
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
  if (loading.value || captchaLoading.value || retrySeconds.value > 0) return
  if (!loginForm.username || !loginForm.password) {
    errorMessage.value = '请输入用户名和密码'
    return
  }
  if (!challengeId.value || !/^\d{5}$/.test(captchaAnswer.value)) {
    errorMessage.value = '请输入图片中的 5 位验证码'
    return
  }
  
  loading.value = true
  errorMessage.value = ''
  
  try {
    const result = await authStore.login(loginForm.username, loginForm.password, challengeId.value, captchaAnswer.value)
    
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
    startBackoff(error.retryAfter || 0)
    await loadCaptcha()
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

