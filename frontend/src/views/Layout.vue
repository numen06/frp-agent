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
              <FrpLogo :size="40" color="currentColor" />
              <span class="font-extrabold text-blue-600">FRP</span>
              <span class="font-semibold text-gray-500">-AGENT</span>
            </router-link>
          </div>
          <div class="flex items-center gap-3">
            <button
              type="button"
              class="relative inline-flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
              title="版本与更新"
              @click="openVersionModal"
            >
              <svg class="h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
                />
              </svg>
              <span class="hidden sm:inline">v{{ appVersion || '…' }}</span>
              <span
                v-if="updateStatus.hasUpdate"
                class="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-red-500 ring-2 ring-white"
              ></span>
            </button>
            <div class="hidden lg:flex items-center gap-2">
              <label class="text-xs text-gray-500 whitespace-nowrap">默认APPKey</label>
              <select
                class="block min-w-[200px] rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-xs text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
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
                <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M15 17h5l-1.405-4.215A2 2 0 0016.646 11H7.354a2 2 0 00-1.973 1.788L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                  />
                </svg>
                <span
                  v-if="unreadNotificationCount > 0"
                  class="absolute right-1 top-1 inline-flex h-2.5 w-2.5 rounded-full bg-red-500"
                ></span>
              </button>
              <div
                ref="notifyDropdown.dropdownRef"
                class="absolute right-0 z-50 mt-2 w-72 rounded-lg border border-gray-200 bg-white py-1 shadow-lg"
                :class="notifyDropdown.isOpen.value ? 'block' : 'hidden'"
                @click.stop
              >
                <div class="px-3 py-2 text-xs font-semibold text-gray-500">消息通知</div>
                <div class="my-1 border-t border-gray-200"></div>
                <template v-if="notifications.length > 0">
                  <a
                    v-for="item in notifications"
                    :key="item.id"
                    href="#"
                    class="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
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
                class="absolute right-0 z-50 mt-2 min-w-[10rem] rounded-lg border border-gray-200 bg-white py-1 shadow-lg"
                :class="userDropdown.isOpen.value ? 'block' : 'hidden'"
                @click.stop
              >
                <a href="#" class="block px-3 py-2 text-sm text-gray-700 hover:bg-gray-100" @click.prevent="handleUserManage(); userDropdown.close()">用户管理</a>
                <div class="my-1 border-t border-gray-200"></div>
                <a href="#" class="block px-3 py-2 text-sm text-red-600 hover:bg-red-50" @click.prevent="handleLogout(); userDropdown.close()">退出登录</a>
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
      <div class="max-w-7xl mx-auto px-4 text-sm text-gray-500 flex flex-wrap items-center gap-x-2 gap-y-1">
        <span>FRP-AGENT v{{ appVersion || '…' }}</span>
        <span class="text-gray-300">|</span>
        <span>Copyright &copy; 2025</span>
        <span class="text-gray-300">|</span>
        <button
          type="button"
          class="text-blue-600 hover:underline p-0 border-0 bg-transparent cursor-pointer text-sm"
          @click="openVersionModal"
        >
          检查更新与发行说明
        </button>
      </div>
    </footer>

    <!-- 新版本提示 -->
    <Transition name="toast">
      <div
        v-if="updateToastVisible"
        class="fixed bottom-5 left-1/2 z-1100 w-[min(92vw,30rem)] -translate-x-1/2 rounded-xl border border-blue-500/30 bg-linear-to-r from-blue-600 to-blue-700 px-5 py-3.5 text-sm text-white shadow-xl shadow-blue-500/20"
        role="status"
      >
        <div class="flex items-start gap-3">
          <svg class="mt-0.5 h-5 w-5 shrink-0 text-blue-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p class="flex-1 whitespace-pre-wrap leading-relaxed">{{ updateToastText }}</p>
          <button
            type="button"
            class="shrink-0 rounded-md p-1 text-blue-200 hover:bg-white/10 hover:text-white transition-colors"
            aria-label="关闭"
            @click="updateToastVisible = false"
          >
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </Transition>

    <!-- 版本与更新 -->
    <Teleport to="body">
      <div
        v-if="showVersionModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="version-modal-title"
        tabindex="-1"
        @click.self="closeVersionModal"
      >
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" aria-hidden="true" @click="closeVersionModal"></div>
        <div
          class="relative z-10 flex max-h-[min(90vh,640px)] w-full max-w-lg flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-xl"
          @click.stop
        >
          <div class="flex shrink-0 items-center justify-between gap-3 border-b border-gray-200 px-5 py-3.5">
            <h2 id="version-modal-title" class="flex items-center gap-2 text-lg font-semibold text-gray-900">
              <svg class="h-5 w-5 shrink-0 text-blue-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
              </svg>
              版本与更新
            </h2>
            <button
              type="button"
              class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800"
              aria-label="关闭"
              @click="closeVersionModal"
            >
              <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="min-h-0 flex-1 overflow-y-auto px-5 py-4 text-sm">
            <!-- 版本对比卡片 -->
            <div class="grid grid-cols-2 gap-3 mb-4">
              <div class="rounded-lg border border-gray-200 bg-gray-50 p-3">
                <div class="text-xs font-medium text-gray-500 mb-1">当前版本</div>
                <div class="text-lg font-bold text-gray-900">v{{ displayCurrentVersion }}</div>
              </div>
              <div class="rounded-lg border border-gray-200 bg-gray-50 p-3">
                <div class="text-xs font-medium text-gray-500 mb-1">Gitee 最新</div>
                <div class="text-lg font-bold" :class="updateStatus.latestVersion ? 'text-gray-900' : 'text-gray-400'">
                  {{ updateStatus.latestVersion ? `v${updateStatus.latestVersion}` : '—' }}
                </div>
              </div>
            </div>

            <!-- Release 名称 -->
            <div v-if="updateStatus.releaseName" class="mb-4 px-1">
              <span class="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 border border-blue-100">
                <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                </svg>
                {{ updateStatus.releaseName }}
              </span>
            </div>

            <!-- 状态提示 -->
            <div v-if="!updateStatus.checkSuccess" class="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 mb-4 flex items-start gap-2.5">
              <svg class="mt-0.5 h-5 w-5 shrink-0 text-amber-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <p class="text-amber-800">{{ updateStatus.checkMessage || '检查更新失败' }}</p>
            </div>
            <div v-else-if="updateStatus.hasUpdate" class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 mb-4 flex items-start gap-2.5">
              <svg class="mt-0.5 h-5 w-5 shrink-0 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <div>
                <p class="font-medium text-red-800">发现新版本 v{{ updateStatus.latestVersion }}</p>
                <p class="text-red-700 mt-0.5 text-xs">请前往 Gitee Release 拉取镜像或按说明升级。</p>
              </div>
            </div>
            <div v-else-if="updateStatus.latestVersion" class="rounded-lg border border-green-200 bg-green-50 px-4 py-3 mb-4 flex items-start gap-2.5">
              <svg class="mt-0.5 h-5 w-5 shrink-0 text-green-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p class="text-green-800">当前已是最新版本。</p>
            </div>

            <!-- 发行说明 -->
            <div v-if="updateStatus.releaseBody" class="mb-4">
              <div class="flex items-center gap-1.5 px-1 mb-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                发行说明
              </div>
              <pre class="text-xs leading-relaxed rounded-lg border border-gray-200 bg-gray-50 p-3.5 overflow-auto max-h-48 whitespace-pre-wrap text-gray-700">{{ updateStatus.releaseBody }}</pre>
            </div>
            <div
              v-else-if="updateStatus.checkSuccess && updateStatus.latestVersion"
              class="text-xs text-gray-400 px-1 mb-4"
            >
              本 Release 暂无正文，可点击下方「在 Gitee 查看」。
            </div>

            <!-- 链接区 -->
            <div class="border-t border-gray-100 pt-3 flex flex-wrap gap-x-4 gap-y-2">
              <a
                v-if="updateStatus.releaseUrl"
                :href="updateStatus.releaseUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-800 transition-colors"
              >
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                在 Gitee 查看
              </a>
              <a :href="GITEE_RELEASES_URL" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors">
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                </svg>
                全部发行版
              </a>
              <a :href="GITEE_RELEASE_NOTES_URL" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors">
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                仓库内版本说明
              </a>
            </div>
          </div>
          <div class="flex shrink-0 flex-wrap items-center justify-end gap-2 border-t border-gray-200 bg-gray-50 px-5 py-3.5">
            <button type="button" class="inline-flex items-center justify-center gap-2 rounded-lg bg-gray-200 px-4 py-2 text-sm font-medium text-gray-800 transition-colors hover:bg-gray-300" :disabled="checkLoading" @click="closeVersionModal">
              关闭
            </button>
            <button type="button" class="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50" :disabled="checkLoading" @click="refreshVersionCheck">
              <svg v-if="checkLoading" class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <svg v-else class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              刷新检查
            </button>
          </div>
        </div>
      </div>
    </Teleport>

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
import { getSystemVersion, checkVersionUpdate } from '@/api/index'
import { useDropdown } from '@/composables/useDropdown'
import { useCollapse } from '@/composables/useCollapse'
import { useModal } from '@/composables/useModal'

/** 与后端 app/version.py 中 Gitee 仓库一致 */
const GITEE_REPO_URL = 'https://gitee.com/numen06/frp-agent'
const GITEE_RELEASES_URL = `${GITEE_REPO_URL}/releases`
const GITEE_RELEASE_NOTES_URL = `${GITEE_REPO_URL}/tree/master/release-notes`

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

const appVersion = ref('')
const showVersionModal = ref(false)
const checkLoading = ref(false)
const updateToastVisible = ref(false)
const updateToastText = ref('')
let updateToastTimer = null

const updateStatus = ref({
  hasUpdate: false,
  latestVersion: null,
  releaseUrl: null,
  releaseName: null,
  releaseBodySummary: null,
  currentVersion: null,
  releaseBody: null,
  checkSuccess: true,
  checkMessage: ''
})

const displayCurrentVersion = computed(() => {
  return updateStatus.value.currentVersion || appVersion.value || '—'
})

async function loadSystemVersion() {
  if (!authStore.isAuthenticated) return
  try {
    const res = await getSystemVersion()
    if (res?.success && res.version) {
      appVersion.value = res.version
    }
  } catch (e) {
    console.error('获取系统版本失败:', e)
  }
}

function showUpdateToastOnce(resData) {
  const key = `frp-agent-update-notified-${resData.latest_version || 'unknown'}`
  if (sessionStorage.getItem(key)) return
  sessionStorage.setItem(key, '1')
  const summary = resData.release_body_summary ? `\n${resData.release_body_summary}` : ''
  updateToastText.value = `当前 ${resData.current_version || '-'}，最新 ${resData.latest_version || '-'}${summary}`
  updateToastVisible.value = true
  if (updateToastTimer) clearTimeout(updateToastTimer)
  updateToastTimer = setTimeout(() => {
    updateToastVisible.value = false
  }, 12000)
}

async function loadUpdateCheck({ showLoading = false, force = false } = {}) {
  if (!authStore.isAuthenticated) return
  if (showLoading) checkLoading.value = true
  try {
    const d = await checkVersionUpdate(force)
    updateStatus.value = {
      hasUpdate: !!d.has_update,
      latestVersion: d.latest_version || null,
      releaseUrl: d.release_url || null,
      releaseName: d.release_name || null,
      releaseBodySummary: d.release_body_summary || null,
      currentVersion: d.current_version || null,
      releaseBody: d.release_body || null,
      checkSuccess: !!d.success,
      checkMessage: d.message || ''
    }
    if (d.success && d.has_update) {
      showUpdateToastOnce(d)
    }
  } catch (e) {
    const prev = updateStatus.value.currentVersion
    updateStatus.value = {
      hasUpdate: false,
      latestVersion: null,
      releaseUrl: null,
      releaseName: null,
      releaseBodySummary: null,
      currentVersion: prev || appVersion.value || null,
      releaseBody: null,
      checkSuccess: false,
      checkMessage: e?.message || '检查失败'
    }
  } finally {
    if (showLoading) checkLoading.value = false
  }
}

function openVersionModal() {
  showVersionModal.value = true
  loadUpdateCheck({ showLoading: true })
}

function closeVersionModal() {
  showVersionModal.value = false
}

function refreshVersionCheck() {
  loadUpdateCheck({ showLoading: true, force: true })
}

useModal(showVersionModal, closeVersionModal)

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
onMounted(async () => {
  apiKeysStore.init()
  if (route.query.forcePasswordChange === 'true') {
    checkPasswordRequirement()
  }
  await loadSystemVersion()
  await loadUpdateCheck()
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

<style scoped>
.toast-enter-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.toast-leave-active {
  transition: all 0.2s ease-in;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(-50%) translateY(1rem);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(0.5rem);
}
</style>
