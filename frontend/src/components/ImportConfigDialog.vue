<template>
  <Teleport to="body">
    <div
      v-if="dialogVisible"
      class="fixed inset-0 z-50 flex items-end justify-center p-2 sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      @click.self="closeDialog"
    >
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" aria-hidden="true" @click="closeDialog"></div>
      <div
        class="relative z-10 flex h-[calc(100dvh-1rem)] max-h-[calc(100dvh-1rem)] w-full max-w-lg flex-col overflow-hidden rounded-t-xl border border-gray-200 bg-white shadow-xl will-change-transform sm:h-auto sm:max-h-[min(90vh,560px)] sm:rounded-xl"
        @click.stop
      >
        <div class="sticky top-0 z-10 flex shrink-0 items-center justify-between gap-3 border-b border-gray-200 bg-white px-4 py-3.5 sm:px-5">
          <h2 class="text-lg font-semibold text-gray-900">导入 frpc 配置文件</h2>
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
        <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4 text-sm sm:px-5">
          <p class="mb-4 text-sm text-gray-600">
            上传 frpc 配置文件（INI 或 TOML 格式），系统将自动解析并导入代理信息。
          </p>

          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700">当前服务器</label>
            <input
              type="text"
              class="block w-full cursor-not-allowed rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-800"
              :value="currentServerName"
              readonly
            />
          </div>

          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700">选择分组 <span class="text-red-600">*</span></label>
            <AppSelect v-model="importForm.group_name" required>
              <option value="">请选择分组...</option>
              <option v-for="group in groupOptions" :key="group" :value="group">{{ group }}</option>
            </AppSelect>
            <small class="mt-1 block text-xs text-gray-500">导入的代理将被分配到此分组</small>
          </div>

          <div class="mb-0">
            <label class="mb-1 block text-sm font-medium text-gray-700">配置文件 <span class="text-red-600">*</span></label>
            <input
              type="file"
              class="block w-full cursor-pointer rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 file:mr-3 file:rounded-md file:border-0 file:bg-blue-50 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-blue-700 hover:file:bg-blue-100"
              @change="handleFileChange"
              accept=".ini,.toml"
              required
            />
            <small class="mt-1 block text-xs text-gray-500">支持 .ini 和 .toml 格式的 frpc 配置文件</small>
          </div>
        </div>
        <div class="sticky bottom-0 z-10 flex shrink-0 flex-col gap-2 border-t border-gray-200 bg-gray-50 px-4 py-3.5 sm:flex-row sm:flex-wrap sm:items-center sm:justify-end sm:gap-2 sm:px-5">
          <button
            type="button"
            class="inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-3.5 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 sm:mr-auto sm:w-auto"
            @click="closeDialog"
          >
            取消
          </button>
          <button
            type="button"
            class="inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-3.5 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
            @click="handleImport"
            :disabled="importing"
          >
            <span
              v-if="importing"
              class="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-white/30 border-t-white"
              role="status"
              aria-label="导入中"
            ></span>
            开始导入
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useServersStore } from '@/stores/servers'
import { useGroupsStore } from '@/stores/groups'
import { configApi } from '@/api/config'
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

