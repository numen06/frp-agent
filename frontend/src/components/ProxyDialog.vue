<template>
  <div v-if="dialogVisible" class="modal-backdrop fade show" @click="handleBackdropClick"></div>
  <div class="modal modal-blur fade" :class="{ show: dialogVisible, 'd-block': dialogVisible }" tabindex="-1" role="dialog" :style="dialogVisible ? 'display: block;' : ''" @click.self="handleBackdropClick">
    <div class="modal-dialog modal-dialog-centered" role="document" @click.stop>
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">{{ editingProxy ? '编辑代理' : '添加代理' }}</h5>
          <button type="button" class="btn-close" @click="closeDialog"></button>
        </div>
        <div class="modal-body">
          <div class="mb-3">
            <label class="form-label">代理名称 <span class="text-danger">*</span></label>
            <input type="text" class="form-control" v-model="proxyForm.name" @input="handleNameInput" required />
            <small class="form-hint">建议格式: 分组_服务类型（例如: dlyy_rdp）</small>
          </div>
          
          <div class="mb-3">
            <label class="form-label">分组名称</label>
            <input type="text" class="form-control" v-model="proxyForm.group_name" placeholder="留空则自动从名称解析" />
          </div>
          
          <div class="mb-3">
            <label class="form-label">代理类型 <span class="text-danger">*</span></label>
            <select class="form-select" v-model="proxyForm.proxy_type" required>
              <option value="tcp">TCP</option>
              <option value="udp">UDP</option>
              <option value="http">HTTP</option>
              <option value="https">HTTPS</option>
              <option value="stcp">STCP</option>
              <option value="xtcp">XTCP</option>
            </select>
          </div>
          
          <div class="mb-3">
            <label class="form-label">本地 IP <span class="text-danger">*</span></label>
            <input type="text" class="form-control" v-model="proxyForm.local_ip" required />
          </div>
          
          <div class="mb-3">
            <label class="form-label">本地端口 <span class="text-danger">*</span></label>
            <input type="number" class="form-control" v-model.number="proxyForm.local_port" min="0" max="65535" required />
            <small class="form-hint">输入 0 可根据名称自动识别</small>
          </div>
          
          <div class="mb-3">
            <label class="form-label">远程端口</label>
            <input type="number" class="form-control" v-model.number="proxyForm.remote_port" min="1" max="65535" />
            <small class="form-hint">TCP/UDP 类型需要</small>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn me-auto" @click="closeDialog">取消</button>
          <button type="button" class="btn btn-primary" @click="handleSubmit">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { useProxiesStore } from '@/stores/proxies'
import { autoDetectLocalPort } from '@/utils/portDetector'
import { useModal } from '@/composables/useModal'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  serverId: {
    type: Number,
    default: null
  },
  proxy: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'success'])

const proxiesStore = useProxiesStore()
const dialogVisible = ref(false)
const editingProxy = ref(null)

const proxyForm = reactive({
  name: '',
  group_name: '',
  proxy_type: 'tcp',
  local_ip: '127.0.0.1',
  local_port: 0,
  remote_port: null
})

watch(() => props.modelValue, (val) => {
  dialogVisible.value = val
  if (val) {
    if (props.proxy) {
      editingProxy.value = props.proxy
      Object.assign(proxyForm, {
        name: props.proxy.name,
        group_name: props.proxy.group_name || '',
        proxy_type: props.proxy.proxy_type,
        local_ip: props.proxy.local_ip,
        local_port: props.proxy.local_port,
        remote_port: props.proxy.remote_port
      })
    } else {
      resetForm()
    }
  }
})

watch(dialogVisible, (val) => {
  emit('update:modelValue', val)
  if (!val) {
    resetForm()
  }
})

const closeDialog = () => {
  dialogVisible.value = false
}

// 使用统一的模态框功能
useModal(dialogVisible, closeDialog)

const handleNameInput = () => {
  if (proxyForm.local_port === 0) {
    const detectedPort = autoDetectLocalPort(proxyForm.name)
    if (detectedPort > 0) {
      proxyForm.local_port = detectedPort
    }
  }
  
  if (!proxyForm.group_name && proxyForm.name) {
    const parts = proxyForm.name.split('_')
    if (parts.length > 1) {
      proxyForm.group_name = parts[0]
    }
  }
}

const handleSubmit = async () => {
  if (!proxyForm.name || !proxyForm.proxy_type || !proxyForm.local_ip || proxyForm.local_port === null) {
    alert('请填写必填项')
    return
  }
  
  if (!props.serverId) {
    alert('请先选择服务器')
    return
  }
  
  try {
    const data = {
      ...proxyForm,
      frps_server_id: props.serverId
    }
    
    if (editingProxy.value) {
      await proxiesStore.updateProxy(editingProxy.value.id, data)
      alert('更新成功')
    } else {
      await proxiesStore.addProxy(data)
      alert('添加成功')
    }
    
    dialogVisible.value = false
    emit('success')
    resetForm()
  } catch (error) {
    alert('操作失败: ' + error.message)
  }
}

const resetForm = () => {
  editingProxy.value = null
  Object.assign(proxyForm, {
    name: '',
    group_name: '',
    proxy_type: 'tcp',
    local_ip: '127.0.0.1',
    local_port: 0,
    remote_port: null
  })
}

const handleClose = () => {
  resetForm()
}

const handleBackdropClick = () => {
  closeDialog()
}
</script>

