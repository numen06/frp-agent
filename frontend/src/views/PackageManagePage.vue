<template>
  <div>
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">FRP 安装包管理</h3>
        <div class="card-actions flex flex-wrap gap-2 items-center">
          <button
            class="inline-flex items-center justify-center gap-2 rounded-lg bg-gray-200 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-300 disabled:cursor-not-allowed disabled:opacity-50"
            type="button"
            :disabled="refreshLoading"
            @click="handleRefresh"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4"/><path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4"/>
            </svg>
            {{ refreshLoading ? '刷新中...' : '刷新' }}
          </button>
          <button class="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700" type="button" @click="showSyncDialog = true">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M3 14v4a1 1 0 0 0 1 1h4"/><path d="M17 3h4a1 1 0 0 1 1 1v4"/><path d="M16 8l-8 8"/>
            </svg>
            GitHub 同步
          </button>
          <button class="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700" type="button" @click="showUploadDialog = true">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M12 5l0 14"/><path d="M5 12l14 0"/>
            </svg>
            手动上传
          </button>
          <button class="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700" type="button" @click="showInstallDialog = true">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M7 8l-4 4l4 4"/><path d="M17 8l4 4l-4 4"/><path d="M14 4l-4 16"/>
            </svg>
            脚本生成
          </button>
          <div class="dropdown">
            <button
              ref="moreActionsDropdown.triggerRef"
              type="button"
              class="inline-flex items-center justify-center gap-1 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
              @click.prevent="moreActionsDropdown.toggle()"
              :aria-expanded="moreActionsDropdown.isOpen.value"
            >
              更多
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M6 9l6 6l6 -6"/>
              </svg>
            </button>
            <div
              ref="moreActionsDropdown.dropdownRef"
              class="dropdown-menu"
              :class="{ show: moreActionsDropdown.isOpen.value }"
              @click.stop
            >
              <a
                class="dropdown-item"
                href="#"
                :class="{ 'opacity-50 pointer-events-none': checkUpdateLoading }"
                @click.prevent="handleMoreCheckUpdate"
              >
                {{ checkUpdateLoading ? '检查中...' : '检查更新' }}
              </a>
              <a
                class="dropdown-item"
                href="#"
                :class="{ 'opacity-50 pointer-events-none': syncPlatformsLoading }"
                @click.prevent="handleMoreSyncPlatforms"
              >
                {{ syncPlatformsLoading ? '同步中...' : '同步平台类型' }}
              </a>
              <div class="dropdown-divider"></div>
              <a
                class="dropdown-item"
                href="#"
                @click.prevent="showTemplateDialog = true; moreActionsDropdown.close()"
              >
                脚本模板编辑
              </a>
            </div>
          </div>
        </div>
      </div>
      <div class="card-body">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
          <select v-model="filters.version" class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200">
            <option value="">全部版本</option>
            <option v-if="versionsMeta.latest_version" value="__latest__">
              最新（{{ versionsMeta.latest_version }}）
            </option>
            <optgroup v-if="recentVersionsForUi.length" label="最近">
              <option v-for="v in recentVersionsForUi" :key="'rv-' + v" :value="v">{{ v }}</option>
            </optgroup>
            <optgroup v-if="otherVersionsForUi.length" label="其他版本">
              <option v-for="v in otherVersionsForUi" :key="'ov-' + v" :value="v">{{ v }}</option>
            </optgroup>
          </select>
          <select v-model="filters.platform" class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200">
            <option value="">全部平台</option>
            <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
          </select>
          <select v-model="filters.source" class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200">
            <option value="">全部来源</option>
            <option value="github">github</option>
            <option value="upload">upload</option>
          </select>
        </div>
        <div v-if="loading" class="text-center py-8">
          <div class="spinner-border spinner-border-sm" role="status"></div>
          <span class="ms-2 text-muted">加载中...</span>
        </div>
        <div v-else class="overflow-x-auto">
          <table class="w-full border-collapse text-left text-sm text-gray-700">
            <thead>
              <tr>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">ID</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">版本</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">平台</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">文件名</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">大小</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">来源</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">下载时间</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">SHA256</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200 whitespace-nowrap" style="min-width:220px">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="packages.length === 0">
                <td colspan="9" class="text-center text-muted py-8">暂无安装包</td>
              </tr>
              <tr v-for="item in packages" :key="item.id">
                <td class="px-4 py-3 border-b border-gray-100 align-middle">{{ item.id }}</td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle">
                  <span class="badge" :class="item.source === 'github' ? 'bg-blue' : 'bg-secondary'">{{ item.version }}</span>
                </td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle whitespace-nowrap">{{ item.platform }}</td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle">
                  <span class="truncate" :title="item.filename">{{ item.filename }}</span>
                </td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle whitespace-nowrap">{{ formatSize(item.file_size) }}</td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle">
                  <span class="badge" :class="item.source === 'github' ? 'bg-blue' : 'bg-secondary'">{{ item.source }}</span>
                </td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle whitespace-nowrap">{{ formatDate(item.downloaded_at) }}</td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle"><code class="text-xs text-gray-500">{{ item.sha256_checksum?.slice(0, 12) }}...</code></td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle">
                  <div class="flex flex-wrap items-center gap-1.5">
                    <button class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gray-100 text-gray-600 transition-colors hover:bg-gray-200" title="复制下载命令" @click="copyDownloadCommand(item, $event)">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                        <path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M4 4v5h.582m15.356 2a8.001 8.001 0 0 0 -15.356 -2m15.356 2a15 15 0 0 1 2 0m-17 0a15 15 0 0 1 2 0"/><path d="M4 13a8.001 8.001 0 0 0 4 0"/>
                      </svg>
                    </button>
                    <button class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-violet-50 text-violet-700 transition-colors hover:bg-violet-100" title="下载安装包" type="button" @click="downloadPackageFile(item)">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                        <path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-2"/><polyline points="7 11 12 16 17 11"/><line x1="12" y1="4" x2="12" y2="16"/>
                      </svg>
                    </button>
                    <button class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-blue-700 transition-colors hover:bg-blue-100" title="复制安装命令" @click="copyInstallCommand(item, $event)">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                        <path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M12 3l0 18"/><path d="M8 7l4 -4l4 4"/><path d="M8 17l4 4l4 -4"/>
                      </svg>
                    </button>
                    <button class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-green-50 text-green-700 transition-colors hover:bg-green-100" title="复制升级命令" @click="copyUpgradeCommand(item, $event)">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                        <path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M12 6l0 12"/><path d="M16 10l-4 -4l-4 4"/><path d="M16 14l-4 4l-4 -4"/>
                      </svg>
                    </button>
                    <button class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-red-50 text-red-600 transition-colors hover:bg-red-100" title="删除" @click="remove(item)">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                        <path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M4 7l16 0"/><path d="M10 11l0 6"/><path d="M14 11l0 6"/><path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12"/><path d="M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3"/>
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <PackageSyncDialog v-model="showSyncDialog" :releases="releases" :loading="syncLoading" @submit="handleSync" />
    <PackageUploadDialog v-model="showUploadDialog" :platforms="platforms" :loading="uploadLoading" @submit="handleUpload" />
    <PackageInstallDialog
      v-model="showInstallDialog"
      :packages="packages"
      :latest-version="versionsMeta.latest_version"
      :loading="scriptLoading"
      :script="installScript"
      :upgrade-script="upgradeScript"
      @submit="handleGenerateScript"
      @submit-upgrade="handleGenerateUpgradeScript"
    />
    <ScriptTemplateDialog
      v-model="showTemplateDialog"
      :platforms="platforms"
      :templates="scriptTemplates"
      :saving="savingTemplate"
      @save="handleSaveTemplate"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { packagesApi } from '@/api/packages'
import { useApiKeysStore } from '@/stores/apiKeys'
import { useDropdown } from '@/composables/useDropdown'
import { copyWithTooltip } from '@/composables/useCopyTooltip'
import PackageSyncDialog from '@/components/PackageSyncDialog.vue'
import PackageUploadDialog from '@/components/PackageUploadDialog.vue'
import PackageInstallDialog from '@/components/PackageInstallDialog.vue'
import ScriptTemplateDialog from '@/components/ScriptTemplateDialog.vue'

const loading = ref(false)
const syncLoading = ref(false)
const uploadLoading = ref(false)
const scriptLoading = ref(false)
const showSyncDialog = ref(false)
const showUploadDialog = ref(false)
const showInstallDialog = ref(false)
const showTemplateDialog = ref(false)
const checkUpdateLoading = ref(false)
const syncPlatformsLoading = ref(false)
const savingTemplate = ref(false)
const refreshLoading = ref(false)
const moreActionsDropdown = useDropdown()
/** 从服务端恢复/修正筛选条件时避免 watch 重复请求 */
const filterSyncing = ref(false)

const packages = ref([])
const releases = ref([])
const installScript = ref('')
const upgradeScript = ref('')
const scriptTemplates = ref({})
const apiKeysStore = useApiKeysStore()

const PKG_FILTER_KEY = 'fm_package_list_filters_v1'

function readSavedFilters() {
  try {
    const raw = localStorage.getItem(PKG_FILTER_KEY)
    if (raw) {
      const o = JSON.parse(raw)
      if (o && typeof o === 'object') {
        return {
          version: typeof o.version === 'string' ? o.version : '',
          platform: typeof o.platform === 'string' ? o.platform : '',
          source: typeof o.source === 'string' ? o.source : ''
        }
      }
    }
  } catch {
    /* ignore */
  }
  return { version: '', platform: '', source: '' }
}

const platforms = ref([])
const filters = reactive(readSavedFilters())
const versionsMeta = ref({
  versions: [],
  latest_version: '',
  recent_versions: [],
  synced_at: null
})

const recentVersionsForUi = computed(() => {
  const recent = versionsMeta.value.recent_versions || []
  const lv = versionsMeta.value.latest_version
  return recent.filter((v) => v && v !== lv)
})

const otherVersionsForUi = computed(() => {
  const merged = versionsMeta.value.versions || []
  const recent = new Set(versionsMeta.value.recent_versions || [])
  const lv = versionsMeta.value.latest_version
  return merged.filter((v) => v && !recent.has(v) && v !== lv)
})

const formatDate = (v) => (v ? new Date(v).toLocaleString('zh-CN') : '')
const formatSize = (s) => {
  if (!s) return '0 B'
  if (s < 1024) return `${s} B`
  if (s < 1024 * 1024) return `${(s / 1024).toFixed(1)} KB`
  return `${(s / 1024 / 1024).toFixed(1)} MB`
}

const resolveVersionForApi = () => {
  const v = filters.version
  if (!v) return undefined
  if (v === '__latest__') {
    const lv = versionsMeta.value.latest_version
    return lv || undefined
  }
  return v
}

const persistFilters = () => {
  try {
    localStorage.setItem(PKG_FILTER_KEY, JSON.stringify({ ...filters }))
  } catch {
    /* ignore */
  }
}

const loadVersionsMeta = async () => {
  let ranLoadPackages = false
  try {
    const data = await packagesApi.getVersions()
    versionsMeta.value = {
      versions: data.versions || [],
      latest_version: data.latest_version || '',
      recent_versions: data.recent_versions || [],
      synced_at: data.synced_at
    }
    const sel = filters.version
    const merged = versionsMeta.value.versions || []
    const latest = versionsMeta.value.latest_version
    if (sel === '__latest__' && !latest) {
      filterSyncing.value = true
      filters.version = ''
      filterSyncing.value = false
      persistFilters()
      await loadPackages()
      ranLoadPackages = true
    } else if (sel && sel !== '__latest__' && merged.length && !merged.includes(sel)) {
      filterSyncing.value = true
      filters.version = ''
      filterSyncing.value = false
      persistFilters()
      await loadPackages()
      ranLoadPackages = true
    }
  } catch (e) {
    console.warn('获取版本列表失败', e)
    versionsMeta.value = {
      versions: [],
      latest_version: '',
      recent_versions: [],
      synced_at: null
    }
  }
  return ranLoadPackages
}

const loadPackages = async () => {
  loading.value = true
  try {
    const params = {
      version: resolveVersionForApi(),
      platform: filters.platform || undefined,
      source: filters.source || undefined
    }
    const clean = Object.fromEntries(
      Object.entries(params).filter(([, val]) => val !== undefined && val !== '')
    )
    packages.value = await packagesApi.list(clean)
  } catch (e) {
    alert(`加载失败: ${e.message}`)
  } finally {
    loading.value = false
  }
}

const handleRefresh = async () => {
  refreshLoading.value = true
  try {
    const ran = await loadVersionsMeta()
    if (!ran) {
      await loadPackages()
    }
    await Promise.all([loadReleases(), loadPlatforms(), loadScriptTemplates(), apiKeysStore.loadKeys()])
  } finally {
    refreshLoading.value = false
  }
}

const handleMoreCheckUpdate = () => {
  if (checkUpdateLoading.value) return
  moreActionsDropdown.close()
  handleCheckUpdate()
}

const handleMoreSyncPlatforms = () => {
  if (syncPlatformsLoading.value) return
  moreActionsDropdown.close()
  handleSyncPlatforms()
}

const loadReleases = async () => {
  try {
    releases.value = await packagesApi.getReleases()
  } catch (e) {
    console.warn('获取 release 失败', e)
  }
}

const loadPlatforms = async () => {
  try {
    const data = await packagesApi.getPlatforms()
    platforms.value = data.platforms || []
  } catch (e) {
    console.warn('获取平台列表失败', e)
    platforms.value = []
  }
}

const loadScriptTemplates = async () => {
  try {
    scriptTemplates.value = await packagesApi.getScriptTemplates()
  } catch (e) {
    console.warn('获取脚本模板失败', e)
    scriptTemplates.value = {}
  }
}

const resolvePreferredApiKey = async () => {
  return apiKeysStore.resolveDefaultFullKey()
}

const handleSaveTemplate = async ({ platform, content }) => {
  savingTemplate.value = true
  try {
    await packagesApi.updateScriptTemplate(platform, content)
    alert('脚本模板保存成功')
    await loadScriptTemplates()
  } catch (e) {
    alert(`保存失败: ${e.message}`)
  } finally {
    savingTemplate.value = false
  }
}

const handleSync = async (payload) => {
  syncLoading.value = true
  try {
    await packagesApi.sync(payload)
    alert('同步成功')
    showSyncDialog.value = false
    const ran = await loadVersionsMeta()
    if (!ran) {
      await loadPackages()
    }
    await Promise.all([loadPlatforms(), loadScriptTemplates()])
  } catch (e) {
    alert(`同步失败: ${e.message}`)
  } finally {
    syncLoading.value = false
  }
}

const handleUpload = async (payload) => {
  uploadLoading.value = true
  try {
    const fd = new FormData()
    if (payload.version) fd.append('version', payload.version)
    if (payload.platform) fd.append('platform', payload.platform)
    fd.append('package_file', payload.file)
    await packagesApi.upload(fd)
    alert('上传成功')
    showUploadDialog.value = false
    const ran = await loadVersionsMeta()
    if (!ran) {
      await loadPackages()
    }
  } catch (e) {
    alert(`上传失败: ${e.message}`)
  } finally {
    uploadLoading.value = false
  }
}

const remove = async (item) => {
  if (!confirm(`确认删除 ${item.filename} ?`)) return
  try {
    await packagesApi.delete(item.id)
    const ran = await loadVersionsMeta()
    if (!ran) {
      await loadPackages()
    }
  } catch (e) {
    alert(`删除失败: ${e.message}`)
  }
}

const handleCheckUpdate = async () => {
  checkUpdateLoading.value = true
  try {
    const result = await packagesApi.checkUpdate()
    if (result.has_update) {
      alert(`检测到新版本: ${result.latest_version}（本地：${result.local_version || '无'}）`)
    } else {
      alert(`当前已是最新版本: ${result.latest_version || '未知'}`)
    }
  } catch (e) {
    alert(`检查失败: ${e.message}`)
  } finally {
    checkUpdateLoading.value = false
  }
}

const handleSyncPlatforms = async () => {
  syncPlatformsLoading.value = true
  try {
    const data = await packagesApi.syncPlatforms()
    platforms.value = data.platforms || []
    const ran = await loadVersionsMeta()
    if (!ran) {
      await loadPackages()
    }
    await loadScriptTemplates()
    alert(`平台类型已同步到后台（${data.version || 'unknown'}）`)
  } catch (e) {
    alert(`同步平台类型失败: ${e.message}`)
  } finally {
    syncPlatformsLoading.value = false
  }
}

const copyDownloadCommand = async (item, event) => {
  const apiKey = await resolvePreferredApiKey()
  if (!apiKey) {
    alert('无法获取默认 API Key，请先在 API Key 页面创建或复制一次完整密钥')
    return
  }
  const cmd = `curl -L "${window.location.origin}${packagesApi.getDownloadUrl(item.id, apiKey)}" -o ${item.filename}`
  await copyWithTooltip(cmd, event)
}

/** 浏览器直接下载（接口仅认 API Key，与复制下载命令相同依赖默认密钥） */
const downloadPackageFile = async (item) => {
  const apiKey = await resolvePreferredApiKey()
  if (!apiKey) {
    alert('无法获取默认 API Key，请先在 API Key 页面创建或复制一次完整密钥')
    return
  }
  const path = packagesApi.getDownloadUrl(item.id, apiKey)
  const url = `${window.location.origin}${path}`
  const a = document.createElement('a')
  a.href = url
  a.setAttribute('download', item.filename || 'frp-package')
  a.rel = 'noopener noreferrer'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

const copyInstallCommand = async (item, event) => {
  const apiKey = await resolvePreferredApiKey()
  if (!apiKey) {
    alert('无法获取默认 API Key，请先在 API Key 页面创建或复制一次完整密钥')
    return
  }
  const url = packagesApi.getInstallScriptUrl({ package_id: item.id, api_key: apiKey })
  const cmd = `curl -sL "${window.location.origin}${url}" | bash`
  await copyWithTooltip(cmd, event)
}

const copyUpgradeCommand = async (item, event) => {
  const apiKey = await resolvePreferredApiKey()
  if (!apiKey) {
    alert('无法获取默认 API Key，请先在 API Key 页面创建或复制一次完整密钥')
    return
  }
  const url = packagesApi.getUpgradeScriptUrl({ package_id: item.id, api_key: apiKey })
  const cmd = `curl -sL "${window.location.origin}${url}" | bash`
  await copyWithTooltip(cmd, event)
}

const handleGenerateScript = async (payload) => {
  scriptLoading.value = true
  try {
    installScript.value = await packagesApi.getInstallScript({
      package_id: payload.package_id,
      install_path: payload.install_path,
      config_url: payload.config_url || undefined,
      api_key: payload.api_key
    })
  } catch (e) {
    alert(`生成脚本失败: ${e.message}`)
  } finally {
    scriptLoading.value = false
  }
}

const handleGenerateUpgradeScript = async (payload) => {
  scriptLoading.value = true
  try {
    upgradeScript.value = await packagesApi.getUpgradeScript({
      package_id: payload.package_id,
      install_path: payload.install_path,
      api_key: payload.api_key
    })
  } catch (e) {
    alert(`生成升级脚本失败: ${e.message}`)
  } finally {
    scriptLoading.value = false
  }
}

watch(
  filters,
  () => {
    if (filterSyncing.value) return
    persistFilters()
    loadPackages()
  },
  { deep: true }
)

onMounted(async () => {
  apiKeysStore.selectedKeyId = apiKeysStore.getStoredDefaultId()
  const ran = await loadVersionsMeta()
  if (!ran) {
    await loadPackages()
  }
  await Promise.all([loadReleases(), loadPlatforms(), loadScriptTemplates(), apiKeysStore.loadKeys()])
})
</script>
