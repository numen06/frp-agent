<template>
  <div v-if="dialogVisible" class="modal-backdrop fade show" @click="closeDialog"></div>
  <div class="modal modal-blur fade" :class="{ show: dialogVisible, 'd-block': dialogVisible }" tabindex="-1" role="dialog" :style="dialogVisible ? 'display: block;' : ''" @click.self="closeDialog">
    <div class="modal-dialog modal-dialog-centered" role="document" @click.stop>
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">导入 frpc 配置文件</h5>
          <button type="button" class="btn-close" @click="closeDialog"></button>
        </div>
        <div class="modal-body">
          <p class="text-muted mb-3">
            上传 frpc 配置文件（INI 或 TOML 格式），系统将自动解析并导入代理信息。
          </p>
          
          <div class="mb-3">
            <label class="form-label">当前服务器</label>
            <input type="text" class="form-control" :value="currentServerName" readonly />
          </div>
          
          <div class="mb-3">
            <label class="form-label">选择分组 <span class="text-danger">*</span></label>
            <select class="form-select" v-model="importForm.group_name" required>
              <option value="">请选择分组...</option>
              <option v-for="group in groupOptions" :key="group" :value="group">{{ group }}</option>
            </select>
            <small class="form-hint">导入的代理将被分配到此分组</small>
          </div>
          
          <div class="mb-3">
            <label class="form-label">配置文件 <span class="text-danger">*</span></label>
            <input type="file" class="form-control" @change="handleFileChange" accept=".ini,.toml" required />
            <small class="form-hint">支持 .ini 和 .toml 格式的 frpc 配置文件</small>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn me-auto" @click="closeDialog">取消</button>
          <button type="button" class="btn btn-primary" @click="handleImport" :disabled="importing">
            <span v-if="importing" class="spinner-border spinner-border-sm me-2" role="status"></span>
            开始导入
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useServersStore } from '@/stores/servers'
import { useGroupsStore } from '@/stores/groups'
import { configApi } from '@/api/config'
import { useModal } from '@/composables/useModal'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  serverId: {
    type: Number,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'success'])

const serversStore = useServersStore()
const groupsStore = useGroupsStore()
const dialogVisible = ref(false)
const importing = ref(false)
const selectedFile = ref(null)

const importForm = reactive({
  group_name: '',
  file: null
})

const currentServerName = computed(() => {
  const server = serversStore.currentServer
  return server ? server.name : ''
})

const groupOptions = computed(() => {
  const groups = new Set()
  groupsStore.groups.forEach(g => groups.add(g.group_name))
  return Array.from(groups).sort()
})

watch(() => props.modelValue, (val) => {
  dialogVisible.value = val
  if (val && props.serverId) {
    groupsStore.loadGroups(props.serverId)
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

const handleFileChange = (event) => {
  selectedFile.value = event.target.files[0]
  importForm.file = selectedFile.value ? selectedFile.value.name : null
}

const handleImport = async () => {
  if (!importForm.group_name) {
    alert('请选择分组')
    return
  }
  
  if (!selectedFile.value) {
    alert('请选择配置文件')
    return
  }
  
  importing.value = true
  
  try {
    const reader = new FileReader()
    reader.onload = async (e) => {
      try {
        const content = e.target.result
        const fileName = selectedFile.value.name
        const format = fileName.endsWith('.toml') ? 'toml' : 'ini'
        const serverName = serversStore.currentServer?.name
        
        if (!serverName) {
          alert('请先选择服务器')
          return
        }
        
        await configApi.importConfigDirect(format, serverName, content)
        alert('导入成功')
        dialogVisible.value = false
        emit('success')
        resetForm()
      } catch (error) {
        alert('导入失败: ' + error.message)
      } finally {
        importing.value = false
      }
    }
    reader.readAsText(selectedFile.value)
  } catch (error) {
    alert('读取文件失败: ' + error.message)
    importing.value = false
  }
}

const resetForm = () => {
  importForm.group_name = ''
  importForm.file = null
  selectedFile.value = null
}

const handleClose = () => {
  resetForm()
}
</script>

