<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed inset-0 z-50 flex items-end justify-center p-2 sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      @click.self.prevent.stop="close"
    >
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" aria-hidden="true" @click.prevent.stop="close"></div>
      <div
        class="relative z-10 flex h-[calc(100dvh-1rem)] max-h-[calc(100dvh-1rem)] w-full max-w-lg flex-col overflow-hidden rounded-t-xl border border-gray-200 bg-white shadow-xl will-change-transform sm:h-auto sm:max-h-[min(92vh,720px)] sm:rounded-xl"
        @click.stop
      >
        <div class="sticky top-0 z-10 flex shrink-0 items-center justify-between gap-3 border-b border-gray-200 bg-white px-4 py-3.5 sm:px-5">
          <h2 class="text-lg font-semibold text-gray-900">{{ forceMode ? '强制修改密码' : '用户管理' }}</h2>
          <button
            type="button"
            class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800"
            aria-label="关闭"
            @click.prevent.stop="close"
          >
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4 text-sm sm:px-5">
          <div v-if="forceMode" class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-800" role="alert">
            <p class="mb-1 font-semibold">安全提示</p>
            <div class="text-sm">{{ forceReason || '检测到您使用的是默认密码，为了账户安全，请立即修改密码。修改完成后才能继续使用系统。' }}</div>
          </div>

          <div v-if="!forceMode" class="mb-4 overflow-hidden rounded-xl border border-gray-200 bg-gray-50/50">
            <div class="border-b border-gray-200 bg-white px-4 py-3">
              <h3 class="text-sm font-semibold text-gray-900">账号信息</h3>
            </div>
            <div class="px-4 py-3">
              <div class="text-xs text-gray-500">用户名</div>
              <div class="mt-0.5 font-semibold text-gray-900">{{ userSettings.username }}</div>
            </div>
          </div>

          <div class="overflow-hidden rounded-xl border border-gray-200 bg-white">
            <div class="border-b border-gray-200 px-4 py-3">
              <h3 class="text-sm font-semibold text-gray-900">修改密码</h3>
            </div>
            <div class="px-4 py-4">
              <form id="user-password-form" @submit.prevent="handleChangePassword" class="space-y-4">
                <div>
                  <label class="mb-1 block text-sm font-medium text-gray-700">当前密码 <span class="text-red-600">*</span></label>
                  <input
                    type="password"
                    class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                    v-model="passwordForm.old_password"
                    required
                  />
                </div>

                <div>
                  <label class="mb-1 block text-sm font-medium text-gray-700">新密码 <span class="text-red-600">*</span></label>
                  <input
                    type="password"
                    class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                    v-model="passwordForm.new_password"
                    required
                    minlength="6"
                  />
                  <small class="mt-1 block text-xs text-gray-500">密码长度至少 6 位</small>
                </div>

                <div>
                  <label class="mb-1 block text-sm font-medium text-gray-700">确认新密码 <span class="text-red-600">*</span></label>
                  <input
                    type="password"
                    class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                    v-model="passwordForm.confirm_password"
                    required
                  />
                </div>
              </form>
            </div>
          </div>

          <div class="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-amber-900" role="alert">
            <p class="mb-2 font-semibold">注意事项</p>
            <ul class="mb-0 list-inside list-disc space-y-1 text-sm text-amber-900/90">
              <li>修改密码后需要重新登录</li>
              <li>请妥善保管新密码，避免泄露</li>
              <li>建议使用强密码（包含字母、数字和特殊字符）</li>
            </ul>
          </div>
        </div>
        <div class="sticky bottom-0 z-10 flex shrink-0 flex-col gap-2 border-t border-gray-200 bg-gray-50 px-4 py-3.5 sm:flex-row sm:flex-wrap sm:items-center sm:justify-end sm:gap-2 sm:px-5">
          <button
            type="button"
            class="btn btn-md btn-outline w-full sm:mr-auto sm:w-auto"
            @click.prevent.stop="close"
          >
            取消
          </button>
          <button
            type="submit"
            form="user-password-form"
            class="btn btn-md btn-primary w-full sm:w-auto"
          >
            保存修改
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { settingsApi } from '@/api/settings'
import { useModal } from '@/composables/useModal'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  forceMode: {
    type: Boolean,
    default: false
  },
  forceReason: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:show', 'cancel-force'])

const router = useRouter()
const authStore = useAuthStore()
const localHidden = ref(false)

const userSettings = reactive({
  username: ''
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

watch(() => props.show, async (newVal) => {
  if (newVal) {
    localHidden.value = false
    await loadUserSettings()
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
  }
})

const visible = computed(() => props.show && !localHidden.value)

const loadUserSettings = async () => {
  try {
    const settings = await settingsApi.getUserSettings()
    userSettings.username = settings.username || authStore.username
  } catch (error) {
    alert('加载用户设置失败: ' + error.message)
  }
}

const handleChangePassword = async () => {
  if (!passwordForm.old_password || !passwordForm.new_password || !passwordForm.confirm_password) {
    alert('请填写所有字段')
    return
  }

  if (passwordForm.new_password.length < 6) {
    alert('新密码长度至少 6 位')
    return
  }

  if (passwordForm.new_password !== passwordForm.confirm_password) {
    alert('两次输入的新密码不一致')
    return
  }

  try {
    await settingsApi.changePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password
    })

    if (props.forceMode) {
      alert('密码修改成功！请重新登录')
      router.replace({ query: {} })
    } else {
      alert('密码修改成功，请重新登录')
    }

    authStore.logout()
    router.push('/login')
  } catch (error) {
    alert('修改失败: ' + error.message)
  }
}

const close = () => {
  localHidden.value = true
  if (props.forceMode) {
    emit('cancel-force')
    router.replace({ query: {} })
  }
  emit('update:show', false)
}

const showRef = computed(() => visible.value)
useModal(showRef, close)
</script>
