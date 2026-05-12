<template>
  <Teleport to="body">
    <div
      v-if="dialogVisible"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      @click.self="handleBackdropClick"
    >
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" aria-hidden="true" @click="handleBackdropClick"></div>
      <div
        class="relative z-10 flex max-h-[min(90vh,640px)] w-full max-w-lg flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-xl"
        @click.stop
      >
        <div class="flex shrink-0 items-center justify-between gap-3 border-b border-gray-200 px-5 py-3.5">
          <h2 class="text-lg font-semibold text-gray-900">{{ editingProxy ? '编辑代理' : '添加代理' }}</h2>
          <button
            type="button"
            class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800"
            aria-label="关闭"
            @click="closeDialog"
          >
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto px-5 py-4 text-sm">
          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700">代理名称 <span class="text-red-600">*</span></label>
            <input
              type="text"
              class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              v-model="proxyForm.name"
              @input="handleNameInput"
              required
            />
            <small class="mt-1 block text-xs text-gray-500">建议格式: 分组_服务类型（例如: dlyy_rdp）</small>
          </div>

          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700">分组名称</label>
            <input
              type="text"
              class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              v-model="proxyForm.group_name"
              placeholder="留空则自动从名称解析"
            />
          </div>

          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700">代理类型 <span class="text-red-600">*</span></label>
            <AppSelect v-model="proxyForm.proxy_type" required>
              <option value="tcp">TCP</option>
              <option value="udp">UDP</option>
              <option value="http">HTTP</option>
              <option value="https">HTTPS</option>
              <option value="stcp">STCP</option>
              <option value="xtcp">XTCP</option>
            </AppSelect>
          </div>

          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700">本地 IP <span class="text-red-600">*</span></label>
            <input
              type="text"
              class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              v-model="proxyForm.local_ip"
              required
            />
          </div>

          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700">本地端口 <span class="text-red-600">*</span></label>
            <input
              type="number"
              class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              v-model.number="proxyForm.local_port"
              min="0"
              max="65535"
              required
            />
            <small class="mt-1 block text-xs text-gray-500">输入 0 可根据名称自动识别</small>
          </div>

          <div class="mb-0">
            <label class="mb-1 block text-sm font-medium text-gray-700">远程端口</label>
            <input
              type="number"
              class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              v-model.number="proxyForm.remote_port"
              min="1"
              max="65535"
            />
            <small class="mt-1 block text-xs text-gray-500">TCP/UDP 类型需要</small>
          </div>
        </div>
        <div class="flex shrink-0 flex-wrap items-center justify-end gap-2 border-t border-gray-200 bg-gray-50 px-5 py-3.5">
          <button
            type="button"
            class="mr-auto inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-3.5 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
            @click="closeDialog"
          >
            取消
          </button>
          <button
            type="button"
            class="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-3.5 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
            @click="handleSubmit"
          >
            保存
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { useProxiesStore } from '@/stores/proxies'
import { autoDetectLocalPort } from '@/utils/portDetector'
import { useModal } from '@/composables/useModal'
import AppSelect from '@/components/AppSelect.vue'

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

