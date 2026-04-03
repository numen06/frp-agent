<template>
  <div class="min-h-screen bg-gray-50">
    <header class="border-b border-gray-200 bg-white">
      <div class="max-w-7xl mx-auto px-4">
        <div class="h-16 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <button
              class="md:hidden inline-flex items-center justify-center rounded-lg p-2 text-gray-500 hover:bg-gray-100"
              type="button"
              @click="navCollapse.toggle()"
              :aria-expanded="navCollapse.isOpen.value"
              aria-label="Toggle navigation"
            >
              <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <router-link to="/dashboard" class="flex items-center gap-2 text-blue-600">
              <FrpLogo :size="28" color="currentColor" />
              <span class="font-extrabold text-blue-600">FRP</span>
              <span class="font-semibold text-gray-500">-AGENT</span>
            </router-link>
          </div>
          <div class="flex items-center gap-3">
            <div class="hidden lg:flex items-center gap-2">
              <label class="text-xs text-gray-500 whitespace-nowrap">默认APPKey</label>
              <select
                class="form-control form-control-sm min-w-[200px]"
                :value="apiKeysStore.selectedKeyId ?? ''"
                @change="handleDefaultKeyChange"
              >
                <option value="" disabled>无可用 APPKey</option>
                <option v-for="item in apiKeysStore.availableKeys" :key="item.id" :value="item.id">
                  #{{ item.id }} {{ item.description }}
                </option>
              </select>
            </div>
            <div class="relative hidden md:block">
              <button
                ref="notifyDropdown.triggerRef"
                class="inline-flex rounded-lg p-2 text-gray-500 hover:bg-gray-100"
                type="button"
                :aria-expanded="notifyDropdown.isOpen.value"
                aria-label="消息通知"
                @click.prevent="notifyDropdown.toggle()"
              >
                <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.4-4.2A2.1 2.1 0 0016.6 11H7.4a2.1 2.1 0 00-2 1.8L4 17h5m1.5 0a1.5 1.5 0 003 0" />
                </svg>
                <span
                  v-if="unreadNotificationCount > 0"
                  class="absolute right-1 top-1 inline-flex h-2.5 w-2.5 rounded-full bg-red-500"
                ></span>
              </button>
              <div
                ref="notifyDropdown.dropdownRef"
                class="dropdown-menu w-72"
                :class="{ show: notifyDropdown.isOpen.value }"
                @click.stop
              >
                <div class="px-3 py-2 text-xs font-semibold text-gray-500">消息通知</div>
                <div class="dropdown-divider"></div>
                <template v-if="notifications.length > 0">
                  <a
                    v-for="item in notifications"
                    :key="item.id"
                    href="#"
                    class="dropdown-item"
                    @click.prevent="handleNotificationClick(item); notifyDropdown.close()"
                  >
                    <span class="inline-flex h-2 w-2 shrink-0 rounded-full bg-red-500"></span>
                    <span class="truncate">{{ item.title }}</span>
                  </a>
                </template>
                <div v-else class="px-3 py-2 text-sm text-gray-500">暂无新消息</div>
              </div>
            </div>
            <div class="relative">
              <button
                ref="userDropdown.triggerRef"
                class="inline-flex items-center gap-2 rounded-lg p-1.5 hover:bg-gray-100"
                @click.prevent="userDropdown.toggle()"
              >
                <img
                  class="h-8 w-8 rounded-full"
                  :src="`https://ui-avatars.com/api/?name=${encodeURIComponent(authStore.username || 'Admin')}&background=206bcb&color=fff`"
                  alt="avatar"
                />
                <div class="hidden xl:block text-left">
                  <div class="text-sm font-medium">{{ authStore.username || '管理员' }}</div>
                  <div class="text-xs text-gray-500">管理员</div>
                </div>
              </button>
              <div
                ref="userDropdown.dropdownRef"
                class="dropdown-menu"
                :class="{ show: userDropdown.isOpen.value }"
                @click.stop
              >
                <a href="#" class="dropdown-item" @click.prevent="handleUserManage(); userDropdown.close()">用户管理</a>
                <div class="dropdown-divider"></div>
                <a href="#" class="dropdown-item text-red-600" @click.prevent="handleLogout(); userDropdown.close()">退出登录</a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>

    <nav class="border-b border-gray-200 bg-white md:block" :class="{ hidden: !navCollapse.isOpen.value }">
      <div class="max-w-7xl mx-auto px-4">
        <ul class="flex flex-wrap gap-1 py-2">
          <li v-for="item in navItems" :key="item.path">
            <router-link
              :to="item.path"
              class="inline-flex rounded-lg px-3 py-2 text-sm font-medium"
              :class="$route.path === item.path ? 'bg-blue-50 text-blue-600' : 'text-gray-600 hover:bg-gray-100'"
            >
              {{ item.label }}
            </router-link>
          </li>
        </ul>
      </div>
    </nav>

    <div class="py-6">
      <div class="max-w-7xl mx-auto px-4">
        <router-view />
      </div>
    </div>

    <footer class="border-t border-gray-200 bg-white py-4">
      <div class="max-w-7xl mx-auto px-4 text-sm text-gray-500">
        FRP-AGENT v1.0 | Copyright &copy; 2025
      </div>
    </footer>

    <UserManageDialog
      :show="showUserManageDialog"
      :force-mode="forcePasswordChange"
      :force-reason="forcePasswordChangeReason"
      @update:show="handleUserDialogShowChange"
      @cancel-force="handleCancelForce"
    />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useApiKeysStore } from '@/stores/apiKeys'
import FrpLogo from '@/components/FrpLogo.vue'
import UserManageDialog from '@/components/UserManageDialog.vue'
import { settingsApi } from '@/api/settings'
import { useDropdown } from '@/composables/useDropdown'
import { useCollapse } from '@/composables/useCollapse'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const apiKeysStore = useApiKeysStore()

const showUserManageDialog = ref(false)
const forcePasswordChange = ref(false)
const forcePasswordChangeReason = ref('')
const suppressForcePasswordPrompt = ref(false)
const navItems = [
  { path: '/dashboard', label: '仪表板' },
  { path: '/proxies', label: '代理列表' },
  { path: '/groups', label: '分组管理' },
  { path: '/converter', label: 'INI 转换' },
  { path: '/servers', label: '服务器管理' },
  { path: '/api-keys', label: '密钥管理' },
  { path: '/packages', label: '安装包管理' }
]

// 下拉菜单和折叠功能
const userDropdown = useDropdown()
const notifyDropdown = useDropdown()
const navCollapse = useCollapse()

const notifications = computed(() => {
  const items = []
  if (forcePasswordChange.value) {
    items.push({
      id: 'force-password-change',
      type: 'forcePasswordChange',
      title: forcePasswordChangeReason.value || '检测到使用默认密码，请立即修改'
    })
  }
  return items
})

const unreadNotificationCount = computed(() => notifications.value.length)

// 检查是否需要强制修改密码
const checkPasswordRequirement = async () => {
  if (!authStore.isAuthenticated) return
  
  try {
    const result = await settingsApi.checkPasswordRequirement()
    if (result?.require_password_change && !suppressForcePasswordPrompt.value) {
      forcePasswordChange.value = true
      forcePasswordChangeReason.value = result.reason || '检测到使用默认密码，请立即修改'
      showUserManageDialog.value = true
    }
  } catch (error) {
    console.warn('检查密码要求失败:', error)
  }
}

// 监听路由查询参数
watch(() => route.query, (newQuery) => {
  if (newQuery.forcePasswordChange === 'true' && !suppressForcePasswordPrompt.value) {
    forcePasswordChange.value = true
    forcePasswordChangeReason.value = newQuery.reason || '检测到使用默认密码，请立即修改'
    showUserManageDialog.value = true
    return
  }

  // 路由不再要求强制改密时，恢复普通用户管理模式
  forcePasswordChange.value = false
  forcePasswordChangeReason.value = ''
}, { immediate: true })

// 组件挂载时检查
onMounted(() => {
  apiKeysStore.init()
  if (route.query.forcePasswordChange === 'true') {
    checkPasswordRequirement()
  }
})

const handleDefaultKeyChange = (event) => {
  const nextId = Number(event.target.value)
  if (Number.isInteger(nextId) && nextId > 0) {
    apiKeysStore.setDefaultKey(nextId)
  }
}

const handleUserManage = () => {
  // 手动打开用户管理时始终使用普通模式，避免遗留强制状态导致信息被隐藏
  forcePasswordChange.value = false
  forcePasswordChangeReason.value = ''
  showUserManageDialog.value = true
}

const handleCancelForce = () => {
  // 当前会话内可跳过，避免关闭后立即再次弹出
  suppressForcePasswordPrompt.value = true
}

const handleUserDialogShowChange = (visible) => {
  showUserManageDialog.value = visible
  if (!visible) {
    if (route.query.forcePasswordChange === 'true') {
      router.replace({ query: {} })
    }
    // 关闭弹窗后恢复普通状态，防止残留状态导致再次拉起
    forcePasswordChange.value = false
    forcePasswordChangeReason.value = ''
  }
}

const handleLogout = async () => {
  if (confirm('确定要退出登录吗？')) {
    authStore.logout()
    router.push('/login')
  }
}

const handleNotificationClick = (notification) => {
  if (notification.type === 'forcePasswordChange') {
    forcePasswordChange.value = true
    forcePasswordChangeReason.value = notification.title
    showUserManageDialog.value = true
  }
}
</script>


