<template>
  <div>
    <h3 class="mb-3">INI 转 TOML 工具</h3>
    <p class="text-muted mb-4">
      将旧版 FRP 的 INI 格式配置文件转换为新版的 TOML 格式
    </p>
    
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
    
    <button class="btn btn-primary mb-3" @click="convertIniToToml">
      <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
        <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4" />
      </svg>
      转换为 TOML
    </button>
    
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
</template>

<script setup>
import { ref } from 'vue'
import { configApi } from '@/api/config'

const iniContent = ref('')
const tomlContent = ref('')

const handleFileChange = (event) => {
  const file = event.target.files[0]
  if (file) {
    const reader = new FileReader()
    reader.onload = (e) => {
      iniContent.value = e.target.result
    }
    reader.readAsText(file)
  }
}

const clearInput = () => {
  iniContent.value = ''
  tomlContent.value = ''
}

const convertIniToToml = async () => {
  if (!iniContent.value.trim()) {
    alert('请输入 INI 配置内容')
    return
  }
  
  try {
    tomlContent.value = await configApi.convertIniToToml(iniContent.value)
    alert('转换成功')
  } catch (error) {
    alert('转换失败: ' + error.message)
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

