<template>
  <div>
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">FRP 安装包管理</h3>
        <div class="card-actions flex gap-2">
          <button class="btn btn-outline-primary" @click="handleCheckUpdate">检查更新</button>
          <button class="btn btn-primary" @click="showSyncDialog = true">GitHub 同步</button>
          <button class="btn btn-primary" @click="showUploadDialog = true">手动上传</button>
          <button class="btn btn-outline-primary" @click="showInstallDialog = true">生成安装脚本</button>
        </div>
      </div>
      <div class="card-body">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
          <input v-model="filters.version" class="form-control" placeholder="版本过滤，如 v0.61.1" />
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
        <div class="card mb-3">
          <div class="card-header">
            <h4 class="card-title">平台脚本模板（可手动编辑）</h4>
          </div>
          <div class="card-body">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
              <select v-model="scriptEditor.platform" class="form-control">
                <option value="">请选择平台</option>
                <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
              </select>
              <button class="btn btn-outline-primary" @click="loadTemplateToEditor">加载模板</button>
              <button class="btn btn-primary" :disabled="savingTemplate" @click="saveTemplate">
                {{ savingTemplate ? '保存中...' : '保存模板' }}
              </button>
            </div>
            <textarea
              v-model="scriptEditor.content"
              class="form-control font-monospace"
              rows="10"
              placeholder="可用变量：{{filename}} {{download_url}} {{install_path}} {{config_line}} {{platform}} {{version}}"
            />
          </div>
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
                  <button class="btn btn-sm btn-outline-primary me-2" @click="copyDownloadCommand(item)">复制下载命令</button>
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
      :loading="scriptLoading"
      :script="installScript"
      @submit="handleGenerateScript"
    />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { packagesApi } from '@/api/packages'
import PackageSyncDialog from '@/components/PackageSyncDialog.vue'
import PackageUploadDialog from '@/components/PackageUploadDialog.vue'
import PackageInstallDialog from '@/components/PackageInstallDialog.vue'

const loading = ref(false)
const syncLoading = ref(false)
const uploadLoading = ref(false)
const scriptLoading = ref(false)
const showSyncDialog = ref(false)
const showUploadDialog = ref(false)
const showInstallDialog = ref(false)
const savingTemplate = ref(false)

const packages = ref([])
const releases = ref([])
const installScript = ref('')
const scriptTemplates = ref({})

const platforms = ref([])
const filters = reactive({
  version: '',
  platform: '',
  source: ''
})
const scriptEditor = reactive({
  platform: '',
  content: ''
})

const formatDate = (v) => (v ? new Date(v).toLocaleString('zh-CN') : '')
const formatSize = (s) => {
  if (!s) return '0 B'
  if (s < 1024) return `${s} B`
  if (s < 1024 * 1024) return `${(s / 1024).toFixed(1)} KB`
  return `${(s / 1024 / 1024).toFixed(1)} MB`
}

const loadPackages = async () => {
  loading.value = true
  try {
    packages.value = await packagesApi.list(filters)
  } catch (e) {
    alert(`加载失败: ${e.message}`)
  } finally {
    loading.value = false
  }
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

const loadTemplateToEditor = () => {
  if (!scriptEditor.platform) {
    alert('请先选择平台')
    return
  }
  scriptEditor.content = scriptTemplates.value[scriptEditor.platform] || ''
}

const saveTemplate = async () => {
  if (!scriptEditor.platform || !scriptEditor.content.trim()) {
    alert('请选择平台并填写脚本内容')
    return
  }
  savingTemplate.value = true
  try {
    await packagesApi.updateScriptTemplate(scriptEditor.platform, scriptEditor.content)
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
    await loadPackages()
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
    await loadPackages()
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
    await loadPackages()
  } catch (e) {
    alert(`删除失败: ${e.message}`)
  }
}

const handleCheckUpdate = async () => {
  try {
    const result = await packagesApi.checkUpdate()
    if (result.has_update) {
      alert(`检测到新版本: ${result.latest_version}（本地：${result.local_version || '无'}）`)
    } else {
      alert(`当前已是最新版本: ${result.latest_version || '未知'}`)
    }
  } catch (e) {
    alert(`检查失败: ${e.message}`)
  }
}

const copyDownloadCommand = async (item) => {
  const apiKey = prompt('请输入用于远程下载的 API Key：')
  if (!apiKey) return
  const cmd = `curl -L "${window.location.origin}${packagesApi.getDownloadUrl(item.id, apiKey)}" -o ${item.filename}`
  await navigator.clipboard.writeText(cmd)
  alert('下载命令已复制')
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

watch(filters, loadPackages, { deep: true })

onMounted(async () => {
  await Promise.all([loadPackages(), loadReleases(), loadPlatforms(), loadScriptTemplates()])
})
</script>
