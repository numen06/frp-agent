<template>
  <div>
    <p class="text-muted mb-4">
      将旧版 FRP 的 INI 格式配置文件转换为新版的 TOML 格式
    </p>
    
    <!-- Tab 导航 -->
    <div class="card">
      <div class="card-header">
        <ul class="nav nav-tabs card-header-tabs">
          <li class="nav-item">
            <a href="#" class="nav-link" :class="{ active: activeTab === 'web' }" @click.prevent="activeTab = 'web'">
              <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
                <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4" />
              </svg>
              Web 转换工具
            </a>
          </li>
          <li class="nav-item">
            <a href="#" class="nav-link" :class="{ active: activeTab === 'command' }" @click.prevent="activeTab = 'command'">
              <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M7 8l-4 4l4 4" />
                <path d="M17 8l4 4l-4 4" />
                <path d="M14 4l-4 16" />
              </svg>
              命令行工具
            </a>
          </li>
        </ul>
      </div>
      <div class="card-body">
        <div class="tab-content">
          <!-- Web 转换工具 Tab -->
          <div class="tab-pane" :class="{ active: activeTab === 'web', show: activeTab === 'web' }" id="web-converter">
            <!-- 文件上传区域 -->
            <div class="mb-4">
              <label class="form-label">上传 INI 文件</label>
              <div class="input-group">
                <input type="file" class="form-control" @change="handleFileChange" accept=".ini,.txt,.conf" />
                <button class="btn btn-outline-secondary" @click="clearInput">清空</button>
              </div>
              <small class="form-hint">支持 .ini、.txt、.conf 格式文件</small>
            </div>
            
            <div class="text-center text-muted my-3">或</div>
            
            <div class="mb-3">
              <label class="form-label">直接输入 INI 配置内容</label>
              <textarea
                class="form-control"
                v-model="iniContent"
                rows="10"
                placeholder="粘贴您的 frpc.ini 配置内容..."
                style="font-family: monospace;"
              ></textarea>
            </div>
            
            <button class="btn btn-primary mb-3" @click="convertIniToToml" :disabled="converting">
              <svg v-if="!converting" xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
                <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4" />
              </svg>
              <span v-if="converting" class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
              {{ converting ? '转换中...' : '转换为 TOML' }}
            </button>
            
            <div v-if="errorMessage" class="alert alert-danger mb-3">
              <strong>错误：</strong>{{ errorMessage }}
            </div>
            
            <div v-if="tomlContent" class="mt-4">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <label class="form-label mb-0">转换结果（TOML 格式）</label>
                <button class="btn btn-sm btn-secondary" @click="downloadToml">
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                    <path d="M14 3v4a1 1 0 0 0 1 1h4" />
                    <path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z" />
                    <path d="M12 11v6" />
                    <path d="M9 14l3 -3l3 3" />
                  </svg>
                  下载 TOML
                </button>
              </div>
              <textarea
                class="form-control"
                v-model="tomlContent"
                rows="10"
                readonly
                style="font-family: monospace; background: var(--tblr-bg-surface-tertiary);"
              ></textarea>
            </div>
          </div>
          
          <!-- 命令行工具 Tab -->
          <div class="tab-pane" :class="{ active: activeTab === 'command', show: activeTab === 'command' }" id="command-line">
            <div class="alert alert-info">
              <div class="d-flex align-items-start">
                <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-info-circle me-2" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                  <path d="M3 12a9 9 0 1 0 18 0a9 9 0 0 0 -18 0" />
                  <path d="M12 9h.01" />
                  <path d="M11 12h1v4h1" />
                </svg>
                <div class="flex-fill">
                  <strong>通过 curl 命令行工具转换：</strong>
                  <p class="text-muted mb-0 mt-1">选择 API Key 后，复制下方命令即可在终端执行</p>
                </div>
              </div>
            </div>
            
            <div class="mb-3">
              <label class="form-label">选择 API Key（可选）</label>
              <select class="form-select" v-model="selectedApiKeyId" @change="handleApiKeyChange">
                <option :value="null">不选择（使用 YOUR_API_KEY 占位符）</option>
                <option v-for="apiKey in apiKeys" :key="apiKey.id" :value="apiKey.id">
                  {{ apiKey.description }} ({{ apiKey.is_active ? '激活' : '未激活' }})
                </option>
              </select>
              <small class="form-hint">选择 API Key 后，命令中会自动填充真实的密钥</small>
            </div>
            
            <div class="mb-3">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <label class="form-label mb-0">使用示例（可直接复制执行）</label>
                <div class="d-flex align-items-center gap-2">
                  <span v-if="copySuccess" class="text-success small">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-sm" width="16" height="16" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <path d="M5 12l5 5l10 -10" />
                    </svg>
                    已复制
                  </span>
                  <button class="btn btn-sm btn-primary" @click="copyExampleCommand">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="16" height="16" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <path d="M8 8m0 2a2 2 0 0 1 2 -2h8a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2z" />
                      <path d="M16 8v-2a2 2 0 0 0 -2 -2h-8a2 2 0 0 0 -2 2v8a2 2 0 0 0 2 2h2" />
                    </svg>
                    复制命令
                  </button>
                </div>
              </div>
              <pre class="bg-dark text-light p-3 rounded" style="font-size: 0.875rem; background-color: #1a1a1a !important; color: #ffffff !important; white-space: pre-wrap; word-wrap: break-word; overflow-wrap: break-word; margin: 0;"><code class="text-light" style="color: #ffffff !important;">{{ exampleCommand }}</code></pre>
            </div>
            
            <div class="alert alert-secondary">
              <h4 class="alert-title">使用说明</h4>
              <div class="text-muted">
                <ol class="mb-0">
                  <li>将命令中的 <code>frpc.ini</code> 替换为您的实际 INI 文件路径</li>
                  <li>如果未选择 API Key，请将 <code>YOUR_API_KEY</code> 替换为您的实际 API Key</li>
                  <li>执行命令后，转换结果会保存到 <code>frpc.toml</code> 文件</li>
                </ol>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { configApi } from '@/api/config'
import { apiKeysApi } from '@/api/apiKeys'

const activeTab = ref('web') // 当前激活的 tab: 'web' 或 'command'
const iniContent = ref('')
const tomlContent = ref('')
const converting = ref(false)
const errorMessage = ref('')
const apiKeys = ref([])
const selectedApiKeyId = ref(null)
const selectedApiKeyFullKey = ref(null)
const loadingApiKeys = ref(false)
const copySuccess = ref(false) // 复制成功提示

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
    // 先尝试从 localStorage 读取
    const id = selectedApiKeyId.value
    const possibleKeys = [
      `api_key_${id}`,
      `api_key_${Number(id)}`,
      `api_key_${String(id)}`
    ]
    
    let fullKey = null
    for (const key of possibleKeys) {
      const value = localStorage.getItem(key)
      if (value && value.trim()) {
        const trimmedValue = value.trim()
        if (trimmedValue !== String(id) && trimmedValue !== String(Number(id)) && trimmedValue.length > 20) {
          fullKey = trimmedValue
          break
        }
      }
    }
    
    // 如果 localStorage 中没有，尝试从后端接口获取
    if (!fullKey) {
      try {
        const response = await apiKeysApi.get(id, { include_full_key: true })
        if (response.key && response.key.length > 20) {
          fullKey = response.key
          // 保存到 localStorage 以便下次使用
          const storageKey = `api_key_${Number(id)}`
          localStorage.setItem(storageKey, fullKey)
          localStorage.setItem(`api_key_${String(id)}`, fullKey)
        }
      } catch (error) {
        console.warn('无法从后端获取完整密钥:', error)
      }
    }
    
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
  return `curl -X POST -H "Content-Type: text/plain" --data-binary "@frpc.ini" "${baseUrl}/frpc/convert/ini-to-toml/direct?api_key=${apiKey}" -o frpc.toml`
})

// 加载 API Key 列表
const loadApiKeys = async () => {
  loadingApiKeys.value = true
  try {
    const keys = await apiKeysApi.list(0, 100)
    // 只显示激活的密钥
    apiKeys.value = keys.filter(k => k.is_active && !k.is_expired)
    
    // 如果列表不为空且当前没有选中密钥，默认选择第一个
    if (apiKeys.value.length > 0 && selectedApiKeyId.value === null) {
      selectedApiKeyId.value = apiKeys.value[0].id
    }
    
    // 如果已经有选中的密钥，重新加载完整密钥
    if (selectedApiKeyId.value) {
      updateFullKey()
    }
  } catch (error) {
    console.error('加载 API Key 列表失败:', error)
    apiKeys.value = []
  } finally {
    loadingApiKeys.value = false
  }
}

// 复制示例命令到剪贴板
const copyExampleCommand = async () => {
  if (!exampleCommand.value) return
  
  try {
    await navigator.clipboard.writeText(exampleCommand.value)
    // 显示复制成功提示
    copySuccess.value = true
    setTimeout(() => {
      copySuccess.value = false
    }, 2000) // 2秒后自动隐藏
  } catch (error) {
    // 降级方案：使用传统方法
    const textArea = document.createElement('textarea')
    textArea.value = exampleCommand.value
    textArea.style.position = 'fixed'
    textArea.style.left = '-999999px'
    document.body.appendChild(textArea)
    textArea.select()
    try {
      document.execCommand('copy')
      // 显示复制成功提示
      copySuccess.value = true
      setTimeout(() => {
        copySuccess.value = false
      }, 2000) // 2秒后自动隐藏
    } catch (err) {
      alert('复制失败，请手动复制')
    }
    document.body.removeChild(textArea)
  }
}

// 组件挂载时加载 API Key 列表
onMounted(() => {
  loadApiKeys()
})

const handleFileChange = (event) => {
  const file = event.target.files[0]
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

const clearInput = () => {
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

