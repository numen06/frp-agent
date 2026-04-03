<template>
  <div>
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">FRP 安装包管理</h3>
        <div class="card-actions flex flex-wrap gap-2 items-center">
          <button
            class="btn btn-outline-primary"
            type="button"
            :disabled="refreshLoading"
            @click="handleRefresh"
          >
            {{ refreshLoading ? '刷新中...' : '刷新' }}
          </button>
          <button class="btn btn-primary" type="button" @click="showSyncDialog = true">GitHub 同步</button>
          <button class="btn btn-primary" type="button" @click="showUploadDialog = true">手动上传</button>
          <button class="btn btn-primary" type="button" @click="showInstallDialog = true">生成安装脚本</button>
          <div class="dropdown">
            <button
              ref="moreActionsDropdown.triggerRef"
              type="button"
              class="btn btn-outline-primary dropdown-toggle"
              @click.prevent="moreActionsDropdown.toggle()"
              :aria-expanded="moreActionsDropdown.isOpen.value"
            >
              更多
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
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
          <select v-model="filters.version" class="form-control">
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
          <select v-model="filters.platform" class="form-control">
            <option value="">全部平台</option>
            <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
          </select>
          <select v-model="filters.source" class="form-control">
            <option value="">全部来源</option>
            <option value="github">github</option>
            <option value="upload">upload</option>
          </select>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full border-collapse text-left text-sm text-gray-700">
            <thead>
              <tr>
                <th class="px-4 py-3 bg-gray-50 border-b">ID</th>
                <th class="px-4 py-3 bg-gray-50 border-b">版本</th>
                <th class="px-4 py-3 bg-gray-50 border-b">平台</th>
                <th class="px-4 py-3 bg-gray-50 border-b">文件名</th>
                <th class="px-4 py-3 bg-gray-50 border-b">大小</th>
                <th class="px-4 py-3 bg-gray-50 border-b">来源</th>
                <th class="px-4 py-3 bg-gray-50 border-b">下载时间</th>
                <th class="px-4 py-3 bg-gray-50 border-b">SHA256</th>
                <th class="px-4 py-3 bg-gray-50 border-b">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td colspan="9" class="text-center py-4">加载中...</td>
              </tr>
              <tr v-else-if="packages.length === 0">
                <td colspan="9" class="text-center py-4">暂无安装包</td>
              </tr>
              <tr v-for="item in packages" :key="item.id">
                <td class="px-4 py-3 border-b">{{ item.id }}</td>
                <td class="px-4 py-3 border-b">{{ item.version }}</td>
                <td class="px-4 py-3 border-b">{{ item.platform }}</td>
                <td class="px-4 py-3 border-b">{{ item.filename }}</td>
                <td class="px-4 py-3 border-b">{{ formatSize(item.file_size) }}</td>
                <td class="px-4 py-3 border-b">{{ item.source }}</td>
                <td class="px-4 py-3 border-b">{{ formatDate(item.downloaded_at) }}</td>
                <td class="px-4 py-3 border-b"><code>{{ item.sha256_checksum?.slice(0, 12) }}...</code></td>
                <td class="px-4 py-3 border-b">
                  <button class="btn btn-sm btn-outline-primary me-1" @click="copyDownloadCommand(item, $event)">复制下载命令</button>
                  <button class="btn btn-sm btn-outline-primary me-1" @click="copyInstallCommand(item, $event)">复制安装命令</button>
                  <button class="btn btn-sm btn-outline-danger" @click="remove(item)">删除</button>
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
      @submit="handleGenerateScript"
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
    fd.append('version', payload.version)
    fd.append('platform', payload.platform)
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
