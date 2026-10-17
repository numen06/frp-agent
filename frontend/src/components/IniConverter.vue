<template>
  <div>
    <p class="mb-4 text-gray-700">
      将旧版 FRP 的 INI 格式配置文件转换为新版的 TOML 格式
    </p>

    <div class="-mx-1 flex overflow-x-auto border-b border-gray-200">
      <button
        type="button"
        class="inline-flex min-h-11 shrink-0 touch-manipulation items-center gap-2 border-b-2 px-3 py-3 text-sm font-medium transition-colors sm:px-4"
        :class="
          activeTab === 'web'
            ? 'border-blue-600 text-blue-600'
            : 'border-transparent text-gray-600 hover:text-gray-900'
        "
        @click="activeTab = 'web'"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
          <path stroke="none" d="M0 0h24v24H0z" fill="none" />
          <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
          <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4" />
        </svg>
        Web 转换工具
      </button>
      <button
        type="button"
        class="inline-flex min-h-11 shrink-0 touch-manipulation items-center gap-2 border-b-2 px-3 py-3 text-sm font-medium transition-colors sm:px-4"
        :class="
          activeTab === 'command'
            ? 'border-blue-600 text-blue-600'
            : 'border-transparent text-gray-600 hover:text-gray-900'
        "
        @click="activeTab = 'command'"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
          <path stroke="none" d="M0 0h24v24H0z" fill="none" />
          <path d="M7 8l-4 4l4 4" />
          <path d="M17 8l4 4l-4 4" />
          <path d="M14 4l-4 16" />
        </svg>
        命令行工具
      </button>
    </div>

    <div class="pt-5">
      <div v-show="activeTab === 'web'">
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-gray-700">上传 INI 文件</label>
          <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
            <fwb-file-input
              v-model="uploadedIniFile"
              accept=".ini,.txt,.conf"
              size="md"
              class="min-w-0 flex-1"
            />
            <button
              type="button"
              class="btn btn-md btn-outline min-h-11 w-full shrink-0 touch-manipulation sm:w-auto"
              aria-label="清空输入"
              @click="clearInput"
            >
              清空
            </button>
          </div>
          <p class="mt-1 text-xs text-gray-500">支持 .ini、.txt、.conf 格式文件</p>
        </div>

        <div class="my-3 text-center text-sm text-gray-500">或</div>

        <div class="mb-3">
          <label class="mb-1 block text-sm font-medium text-gray-700">直接输入 INI 配置内容</label>
          <CodeEditor
            v-model="iniContent"
            language="javascript"
            :height="editorHeight"
            :line-wrapping="true"
            placeholder="粘贴您的 frpc.ini 配置内容..."
          />
        </div>

        <button
          type="button"
          class="btn btn-md btn-primary mb-3 min-h-11 w-full touch-manipulation sm:w-auto"
          aria-label="将 INI 转换为 TOML"
          @click="convertIniToToml"
          :disabled="converting"
        >
          <svg
            v-if="!converting"
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4 shrink-0"
            viewBox="0 0 24 24"
            stroke-width="2"
            stroke="currentColor"
            fill="none"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path stroke="none" d="M0 0h24v24H0z" fill="none" />
            <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
            <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4" />
          </svg>
          <span
            v-if="converting"
            class="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-white/30 border-t-white"
            role="status"
            aria-hidden="true"
          />
          {{ converting ? '转换中...' : '转换为 TOML' }}
        </button>

        <div v-if="errorMessage" class="mb-3 rounded-lg border border-red-200 bg-red-50 p-3 text-red-800">
          <strong>错误：</strong>{{ errorMessage }}
        </div>

        <div v-if="tomlContent" class="mt-4 flex flex-col gap-3">
          <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <span class="text-sm font-medium text-gray-700">转换结果（TOML 格式）</span>
            <div class="grid grid-cols-2 gap-2 sm:flex sm:shrink-0">
              <button
                type="button"
                class="btn btn-md btn-outline min-h-11 touch-manipulation"
                aria-label="复制 TOML 结果"
                @click="copyTomlResult($event)"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                  <path d="M8 8m0 2a2 2 0 0 1 2 -2h8a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2z" />
                  <path d="M16 8v-2a2 2 0 0 0 -2 -2h-8a2 2 0 0 0 -2 2v8a2 2 0 0 0 2 2h2" />
                </svg>
                复制
              </button>
              <button
                type="button"
                class="btn btn-md btn-outline min-h-11 touch-manipulation"
                aria-label="下载 TOML 文件"
                @click="downloadToml"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                  <path d="M14 3v4a1 1 0 0 0 1 1h4" />
                  <path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z" />
                  <path d="M12 11v6" />
                  <path d="M9 14l3 -3l3 3" />
                </svg>
                下载
              </button>
            </div>
          </div>
          <CodeEditor
            v-model="tomlContent"
            language="yaml"
            :height="editorHeight"
            :line-wrapping="true"
            :readonly="true"
          />
        </div>
      </div>

      <div v-show="activeTab === 'command'">
        <div class="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-3 text-blue-900">
          <div class="flex items-start gap-3">
            <svg xmlns="http://www.w3.org/2000/svg" class="mt-0.5 h-4 w-4 shrink-0 text-blue-600" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none" />
              <path d="M3 12a9 9 0 1 0 18 0a9 9 0 0 0 -18 0" />
              <path d="M12 9h.01" />
              <path d="M11 12h1v4h1" />
            </svg>
            <div class="min-w-0 flex-1">
              <strong class="font-semibold">通过 curl 命令行工具转换：</strong>
              <p class="mt-1 text-sm text-blue-800/90">选择 API Key 后，复制下方命令即可在终端执行</p>
            </div>
          </div>
        </div>

        <div class="mb-3">
          <label class="mb-1 block text-sm font-medium text-gray-700">选择 API Key</label>
          <AppSelect class="w-full" :number="true" v-model="selectedApiKeyId" @change="handleApiKeyChange">
            <option v-for="apiKey in apiKeysStore.availableKeys" :key="apiKey.id" :value="apiKey.id">
              {{ apiKey.description }} ({{ apiKey.is_active ? '激活' : '未激活' }})
            </option>
          </AppSelect>
          <p class="mt-1 text-xs text-gray-500">默认使用全局 APPKey，可按需临时切换</p>
        </div>

        <div class="mb-3">
          <div class="mb-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <span class="text-sm font-medium text-gray-700">使用示例（可直接复制执行）</span>
            <button
              type="button"
              class="btn btn-md btn-primary min-h-11 w-full shrink-0 touch-manipulation sm:w-auto"
              aria-label="复制 curl 命令"
              @click="copyExampleCommand($event)"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                <path d="M8 8m0 2a2 2 0 0 1 2 -2h8a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2z" />
                <path d="M16 8v-2a2 2 0 0 0 -2 -2h-8a2 2 0 0 0 -2 2v8a2 2 0 0 0 2 2h2" />
              </svg>
              复制命令
            </button>
          </div>
          <pre class="m-0 rounded-lg bg-gray-900 p-3 text-sm whitespace-pre-wrap wrap-break-word text-gray-100"><code class="text-gray-100">{{ exampleCommand }}</code></pre>
        </div>

        <div class="rounded-lg border border-gray-200 bg-gray-50 p-3 text-gray-700">
          <h4 class="mb-2 text-sm font-semibold text-gray-900">使用说明</h4>
          <ol class="list-decimal space-y-1 pl-5 text-sm text-gray-600">
            <li>将命令中的 <code class="rounded bg-gray-200 px-1 py-0.5 text-gray-800">frpc.ini</code> 替换为您的实际 INI 文件路径</li>
            <li>如果未选择 API Key，请将 <code class="rounded bg-gray-200 px-1 py-0.5 text-gray-800">YOUR_API_KEY</code> 替换为您的实际 API Key</li>
            <li>执行命令后，转换结果会保存到 <code class="rounded bg-gray-200 px-1 py-0.5 text-gray-800">frpc.toml</code> 文件</li>
          </ol>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { FwbFileInput } from 'flowbite-vue'
import { configApi } from '@/api/config'
import { useApiKeysStore } from '@/stores/apiKeys'
import { copyWithTooltip } from '@/composables/useCopyTooltip'
import AppSelect from '@/components/AppSelect.vue'
import CodeEditor from '@/components/CodeEditor.vue'

/** 手机端用 dvh 限制高度，桌面端保持 280px */
const editorHeight = 'clamp(200px, 38dvh, 280px)'

const activeTab = ref('web') // 当前激活的 tab: 'web' 或 'command'
const iniContent = ref('')
const tomlContent = ref('')
const converting = ref(false)
const errorMessage = ref('')
const apiKeysStore = useApiKeysStore()
const selectedApiKeyId = computed({
  get: () => apiKeysStore.selectedKeyId,
  set: (id) => apiKeysStore.setDefaultKey(id)
})
const selectedApiKeyFullKey = ref(null)
const uploadedIniFile = ref(null)

// 获取 API 基础 URL
const apiBaseUrl = computed(() => {
  const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'
  // 如果是相对路径，则使用当前域名
  if (baseURL.startsWith('/')) {
    return `${window.location.origin}${baseURL}`
  }
  return baseURL
})

// 更新完整密钥的函数
const updateFullKey = async () => {
  if (selectedApiKeyId.value) {
    const id = selectedApiKeyId.value
    const fullKey = await apiKeysStore.resolveFullKey(id)
    
    if (fullKey) {
      selectedApiKeyFullKey.value = fullKey
    } else {
      selectedApiKeyFullKey.value = null
    }
  } else {
    selectedApiKeyFullKey.value = null
  }
}

// 监听 selectedApiKeyId 变化，更新完整密钥
watch(selectedApiKeyId, (newId) => {
  updateFullKey()
}, { immediate: true })

// 处理 API Key 选择变化
const handleApiKeyChange = () => {
  apiKeysStore.setDefaultKey(selectedApiKeyId.value)
  updateFullKey()
}

// 计算示例命令
const exampleCommand = computed(() => {
  let apiKey = 'YOUR_API_KEY'
  if (selectedApiKeyFullKey.value) {
    const trimmed = selectedApiKeyFullKey.value.trim()
    if (trimmed && trimmed.length > 20) {
      apiKey = trimmed
    }
  }
  const baseUrl = apiBaseUrl.value
  // 生成单行命令（更易复制执行）
  // baseUrl 已经包含了 /api，所以只需要拼接 /frpc/...
  return `curl -X POST -H "Content-Type: text/plain" --data-binary "@frpc.ini" "${baseUrl}/frpc/convert/ini-to-toml/direct?api_key=${encodeURIComponent(apiKey)}" -o frpc.toml`
})

// 加载 API Key 列表
const loadApiKeys = async () => {
  if (apiKeysStore.selectedKeyId === null) {
    apiKeysStore.selectedKeyId = apiKeysStore.getStoredDefaultId()
  }
  await apiKeysStore.loadKeys()
  if (selectedApiKeyId.value) {
    await updateFullKey()
  }
}

// 复制示例命令到剪贴板
const copyExampleCommand = async (event) => {
  if (!exampleCommand.value) return
  await copyWithTooltip(exampleCommand.value, event)
}

// 组件挂载时加载 API Key 列表
onMounted(() => {
  loadApiKeys()
})

const handleFileChange = (file) => {
  if (file) {
    const reader = new FileReader()
    reader.onload = (e) => {
      iniContent.value = e.target.result
      errorMessage.value = ''
    }
    reader.onerror = () => {
      errorMessage.value = '读取文件失败'
    }
    reader.readAsText(file)
  }
}

watch(uploadedIniFile, (file) => {
  handleFileChange(file)
})

const clearInput = () => {
  uploadedIniFile.value = null
  iniContent.value = ''
  tomlContent.value = ''
  errorMessage.value = ''
}

const convertIniToToml = async () => {
  if (!iniContent.value.trim()) {
    errorMessage.value = '请输入 INI 配置内容'
    return
  }
  
  converting.value = true
  errorMessage.value = ''
  tomlContent.value = ''
  
  try {
    const result = await configApi.convertIniToToml(iniContent.value)
    // 确保结果是字符串
    tomlContent.value = typeof result === 'string' ? result : String(result)
    errorMessage.value = ''
  } catch (error) {
    errorMessage.value = error.message || '转换失败，请检查 INI 配置格式是否正确'
    tomlContent.value = ''
  } finally {
    converting.value = false
  }
}

const copyTomlResult = async (event) => {
  if (!tomlContent.value) return
  await copyWithTooltip(tomlContent.value, event)
}

const downloadToml = () => {
  if (!tomlContent.value) return
  
  const blob = new Blob([tomlContent.value], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'frpc.toml'
  a.click()
  URL.revokeObjectURL(url)
}
</script>

