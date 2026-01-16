<template>
  <div v-if="dialogVisible" class="modal-backdrop fade show" @click="closeDialog"></div>
  <div class="modal modal-blur fade" :class="{ show: dialogVisible, 'd-block': dialogVisible }" tabindex="-1" role="dialog" :style="dialogVisible ? 'display: block;' : ''" @click.self="closeDialog">
    <div class="modal-dialog modal-lg modal-dialog-centered" role="document" @click.stop>
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">{{ title }}</h5>
          <button type="button" class="btn-close" @click="closeDialog"></button>
        </div>
        <div class="modal-body">
          <div class="mb-3" v-if="showClientName">
            <label class="form-label">配置名称</label>
            <input type="text" class="form-control" v-model="form.client_name" placeholder="留空则使用分组名称" />
          </div>
          
          <div class="mb-3">
            <label class="form-label">配置格式</label>
            <div class="form-selectgroup form-selectgroup-boxes d-flex flex-column">
              <label class="form-selectgroup-item">
                <input type="radio" name="format" value="ini" class="form-selectgroup-input" v-model="form.format" />
                <div class="form-selectgroup-label d-flex align-items-center p-3">
                  <div>
                    <strong>INI 格式</strong>
                    <div class="text-muted">兼容旧版本 FRP</div>
                  </div>
                </div>
              </label>
              <label class="form-selectgroup-item">
                <input type="radio" name="format" value="toml" class="form-selectgroup-input" v-model="form.format" />
                <div class="form-selectgroup-label d-flex align-items-center p-3">
                  <div>
                    <strong>TOML 格式</strong>
                    <div class="text-muted">推荐，新版本 FRP</div>
                  </div>
                </div>
              </label>
            </div>
          </div>
          
          <div v-if="selectedProxies.length > 0" class="alert alert-info mb-3">
            <strong>已选择的代理：</strong>
            <div class="mt-2">
              <span class="badge text-bg-primary me-1 mb-1" v-for="proxy in selectedProxies" :key="proxy.id">
                {{ proxy.name }}
              </span>
            </div>
          </div>
        </div>
        
        <div v-if="configContent" class="modal-body border-top">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <label class="form-label mb-0">配置内容</label>
            <div class="d-flex gap-2">
              <button 
                v-if="props.groupName" 
                class="btn btn-sm btn-warning" 
                @click="handleRegeneratePorts"
                :disabled="regeneratingPorts"
              >
                <span v-if="regeneratingPorts" class="spinner-border spinner-border-sm me-1" role="status"></span>
                <svg v-else xmlns="http://www.w3.org/2000/svg" class="icon" width="16" height="16" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                  <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
                  <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4" />
                </svg>
                重新生成远端端口
              </button>
              <button class="btn btn-sm btn-secondary" @click="downloadConfig">
                <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                  <path d="M14 3v4a1 1 0 0 0 1 1h4" />
                  <path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z" />
                  <path d="M12 11v6" />
                  <path d="M9 14l3 -3l3 3" />
                </svg>
                下载配置
              </button>
            </div>
          </div>
          <textarea
            class="form-control"
            v-model="configContent"
            rows="15"
            readonly
            style="font-family: monospace;"
          ></textarea>
        </div>
        
        <div class="modal-footer">
          <button type="button" class="btn me-auto" @click="closeDialog">关闭</button>
          <button type="button" class="btn btn-primary" @click="handleGenerate" :disabled="generating">
            <span v-if="generating" class="spinner-border spinner-border-sm me-2" role="status"></span>
            <svg v-else xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
              <path d="M14 3v4a1 1 0 0 0 1 1h4" />
              <path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z" />
            </svg>
            生成配置文件
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { frpcConfigApi } from '@/api/frpcConfig'
import { groupApi } from '@/api/groups'
import { useModal } from '@/composables/useModal'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  serverId: {
    type: Number,
    required: true
  },
  groupName: {
    type: String,
    default: ''
  },
  selectedProxies: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue'])

const dialogVisible = ref(false)
const generating = ref(false)
const regeneratingPorts = ref(false)
const configContent = ref('')

const form = reactive({
  client_name: '',
  format: 'toml'
})

const showClientName = computed(() => !!props.groupName)

const title = computed(() => {
  if (props.groupName) {
    return `生成分组配置 - ${props.groupName}`
  } else if (props.selectedProxies.length > 0) {
    return `生成配置（已选择 ${props.selectedProxies.length} 个代理）`
  }
  return '生成配置'
})

watch(() => props.modelValue, (val) => {
  dialogVisible.value = val
  if (val) {
    form.client_name = props.groupName || ''
    form.format = 'toml'
    configContent.value = ''
  }
})

watch(dialogVisible, (val) => {
  emit('update:modelValue', val)
})

const closeDialog = () => {
  dialogVisible.value = false
}

// 使用统一的模态框功能
useModal(dialogVisible, closeDialog)

const handleGenerate = async () => {
  generating.value = true
  configContent.value = ''
  
  try {
    if (props.groupName) {
      // 优先使用新接口（支持自动创建分组）
      const params = {
        format: form.format
      }
      if (props.serverId) {
        params.server_id = props.serverId
      }
      if (form.client_name) {
        params.client_name = form.client_name
      }
      
      const content = await frpcConfigApi.getConfigByGroupQuick(props.groupName, params)
      configContent.value = content
    } else if (props.selectedProxies.length > 0) {
      const result = await frpcConfigApi.generateConfigByProxies({
        proxy_ids: props.selectedProxies.map(p => p.id),
        format: form.format
      })
      configContent.value = result.config
      
      if (result.note) {
        alert(result.note)
      }
    } else {
      alert('请选择代理或分组')
      return
    }
    
    alert('配置生成成功')
  } catch (error) {
    alert('生成配置失败: ' + error.message)
  } finally {
    generating.value = false
  }
}

const downloadConfig = () => {
  if (!configContent.value) {
    alert('请先生成配置')
    return
  }
  
  const blob = new Blob([configContent.value], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const filename = props.groupName 
    ? `frpc_${props.groupName}.${form.format}`
    : `frpc.${form.format}`
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

const handleRegeneratePorts = async () => {
  if (!props.groupName) {
    alert('仅支持为分组重新生成远端端口')
    return
  }
  
  if (!confirm('确定要重新生成该分组中所有代理的远端端口吗？\n\n这将释放旧端口并分配新端口。')) {
    return
  }
  
  regeneratingPorts.value = true
  
  try {
    const result = await groupApi.regenerateGroupPorts(props.groupName, props.serverId)
    
    let message = result.message || '重新生成远端端口成功'
    if (result.proxies && result.proxies.length > 0) {
      message += '\n\n已重新分配的代理：\n'
      result.proxies.forEach(p => {
        message += `  • ${p.name}: ${p.old_port || '无'} → ${p.new_port}\n`
      })
    }
    if (result.failed_proxies && result.failed_proxies.length > 0) {
      message += '\n\n失败的代理：\n'
      result.failed_proxies.forEach(p => {
        message += `  • ${p.name}: ${p.error}\n`
      })
    }
    
    alert(message)
    
    // 重新生成配置以显示新的端口
    await handleGenerate()
  } catch (error) {
    alert('重新生成远端端口失败: ' + error.message)
  } finally {
    regeneratingPorts.value = false
  }
}

const handleClose = () => {
  configContent.value = ''
  form.client_name = ''
  form.format = 'toml'
}
</script>

