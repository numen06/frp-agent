<template>
  <!-- 服务器管理对话框 -->
  <Teleport to="body">
    <div
      v-if="dialogVisible"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      @click.self="closeDialog"
    >
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" aria-hidden="true" @click="closeDialog"></div>
      <div
        class="relative z-10 flex max-h-[min(90vh,85vh)] w-full max-w-5xl flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-xl"
        @click.stop
      >
        <div class="flex shrink-0 items-center justify-between gap-3 border-b border-gray-200 px-5 py-3.5">
          <h2 class="text-lg font-semibold text-gray-900">服务器管理</h2>
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
          <div class="mb-3">
            <button class="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700" @click="showAddDialog = true">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M12 5l0 14" />
                <path d="M5 12l14 0" />
              </svg>
              添加服务器
            </button>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full border-collapse text-left text-sm text-gray-700">
              <thead>
                <tr>
                  <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">服务器名称</th>
                  <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">服务器地址</th>
                  <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">端口</th>
                  <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">API 地址</th>
                  <th class="w-[1%] whitespace-nowrap px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="serversStore.loading">
                  <td colspan="5" class="py-4">
                    <div class="flex items-center justify-center gap-2 text-center text-sm text-gray-600">
                      <span class="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" role="status" aria-label="加载中"></span>
                      <span>加载中...</span>
                    </div>
                  </td>
                </tr>
                <tr v-else-if="serversStore.servers.length === 0">
                  <td colspan="5" class="py-4 text-center text-sm text-gray-500">暂无服务器</td>
                </tr>
                <tr v-else v-for="server in serversStore.servers" :key="server.id">
                  <td class="px-4 py-3 border-b border-gray-100 align-middle">{{ server.name }}</td>
                  <td class="px-4 py-3 border-b border-gray-100 align-middle">{{ server.server_addr }}</td>
                  <td class="px-4 py-3 border-b border-gray-100 align-middle">{{ server.server_port }}</td>
                  <td class="px-4 py-3 border-b border-gray-100 align-middle"><span class="text-xs text-gray-600">{{ server.api_base_url }}</span></td>
                  <td class="px-4 py-3 border-b border-gray-100 align-middle">
                    <div class="inline-flex items-center gap-2">
                      <button class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gray-100 text-gray-700 transition-colors hover:bg-gray-200" @click="editServer(server)" title="编辑" aria-label="编辑">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                          <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                          <path d="M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1" />
                          <path d="M20.385 6.585a2.1 2.1 0 0 0 -2.97 -2.97l-8.415 8.385v3h3l8.385 -8.415z" />
                          <path d="M16 5l3 3" />
                        </svg>
                      </button>
                      <button class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-red-50 text-red-700 transition-colors hover:bg-red-100" @click="deleteServer(server)" title="删除" aria-label="删除">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                          <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                          <path d="M4 7l16 0" />
                          <path d="M10 11l0 6" />
                          <path d="M14 11l0 6" />
                          <path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12" />
                          <path d="M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- 添加/编辑服务器对话框 -->
  <Teleport to="body">
    <div
      v-if="showAddDialog"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      @click.self="closeAddDialog"
    >
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" aria-hidden="true" @click="closeAddDialog"></div>
      <div
        class="relative z-10 flex max-h-[min(90vh,640px)] w-full max-w-lg flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-xl"
        @click.stop
      >
        <div class="flex shrink-0 items-center justify-between gap-3 border-b border-gray-200 px-5 py-3.5">
          <h2 class="text-lg font-semibold text-gray-900">{{ editingServer ? '编辑服务器' : '添加服务器' }}</h2>
          <button
            type="button"
            class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800"
            aria-label="关闭"
            @click="closeAddDialog"
          >
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto px-5 py-4 text-sm">
          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700">服务器名称 <span class="text-red-600">*</span></label>
            <input type="text" class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200" v-model="serverForm.name" required />
          </div>
          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700">服务器地址 <span class="text-red-600">*</span></label>
            <input type="text" class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200" v-model="serverForm.server_addr" @change="generateApiUrl" required />
          </div>
          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700">服务器端口 <span class="text-red-600">*</span></label>
            <input type="number" class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200" v-model.number="serverForm.server_port" min="1" max="65535" required />
          </div>
          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700">API 基础地址 <span class="text-red-600">*</span></label>
            <input type="text" class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200" v-model="serverForm.api_base_url" required />
            <span class="mt-1 block text-xs text-gray-500">可自动生成或手动修改</span>
          </div>
          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700">认证用户名 <span class="text-red-600">*</span></label>
            <input type="text" class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200" v-model="serverForm.auth_username" required />
          </div>
          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700">认证密码 <span class="text-red-600">*</span></label>
            <input type="password" class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200" v-model="serverForm.auth_password" required />
          </div>
          <div class="mb-0">
            <label class="mb-1 block text-sm font-medium text-gray-700">认证 Token</label>
            <input type="text" class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200" v-model="serverForm.auth_token" placeholder="可选，留空表示使用用户名密码认证" />
          </div>
        </div>
        <div class="flex shrink-0 flex-wrap items-center justify-end gap-2 border-t border-gray-200 bg-gray-50 px-5 py-3.5">
          <button type="button" class="mr-auto inline-flex items-center justify-center gap-2 rounded-lg bg-gray-200 px-3 py-2 text-sm font-medium text-gray-800 transition-colors hover:bg-gray-300" @click="closeAddDialog">取消</button>
          <button type="button" class="inline-flex items-center justify-center gap-2 rounded-lg bg-gray-200 px-3 py-2 text-sm font-medium text-gray-800 transition-colors hover:bg-gray-300" @click="testConnection">测试连接</button>
          <button type="button" class="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700" @click="handleSubmit">保存</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { useServersStore } from '@/stores/servers'
import { useModal } from '@/composables/useModal'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'server-selected'])

const serversStore = useServersStore()
const dialogVisible = ref(false)
const showAddDialog = ref(false)
const editingServer = ref(null)

const serverForm = reactive({
  name: '',
  server_addr: '',
  server_port: 7000,
  api_base_url: '',
  auth_username: 'admin',
  auth_password: '',
  auth_token: ''
})

watch(() => props.modelValue, (val) => {
  dialogVisible.value = val
  if (val) {
    serversStore.loadServers()
  }
})

watch(dialogVisible, (val) => {
  emit('update:modelValue', val)
})

const closeDialog = () => {
  dialogVisible.value = false
}

const closeAddDialog = () => {
  showAddDialog.value = false
  resetForm()
}

// 使用统一的模态框功能
useModal(dialogVisible, closeDialog)
useModal(showAddDialog, closeAddDialog)

const generateApiUrl = () => {
  if (serverForm.server_addr && !serverForm.api_base_url) {
    const addr = serverForm.server_addr.replace(/^https?:\/\//, '')
    serverForm.api_base_url = `http://${addr}/api`
  }
}

const handleSubmit = async () => {
  if (!serverForm.name || !serverForm.server_addr || !serverForm.api_base_url || !serverForm.auth_username || !serverForm.auth_password) {
    alert('请填写必填项')
    return
  }
  
  try {
    if (editingServer.value) {
      await serversStore.updateServer(editingServer.value.id, serverForm)
      alert('更新成功')
    } else {
      await serversStore.addServer(serverForm)
      alert('添加成功')
    }
    showAddDialog.value = false
    resetForm()
    await serversStore.loadServers()
  } catch (error) {
    alert('操作失败: ' + error.message)
  }
}

const editServer = (server) => {
  editingServer.value = server
  Object.assign(serverForm, server)
  serverForm.auth_password = ''
  showAddDialog.value = true
}

const deleteServer = async (server) => {
  if (!confirm(`确定要删除服务器 "${server.name}" 吗？`)) {
    return
  }
  
  try {
    await serversStore.deleteServer(server.id)
    alert('删除成功')
  } catch (error) {
    alert('删除失败: ' + error.message)
  }
}

const testConnection = async () => {
  if (editingServer.value) {
    try {
      await serversStore.testServer(editingServer.value.id)
      alert('连接测试成功')
      await serversStore.loadServers()
    } catch (error) {
      alert('连接测试失败: ' + error.message)
    }
  } else {
    alert('请先保存服务器信息')
  }
}

const resetForm = () => {
  editingServer.value = null
  Object.assign(serverForm, {
    name: '',
    server_addr: '',
    server_port: 7000,
    api_base_url: '',
    auth_username: 'admin',
    auth_password: '',
    auth_token: ''
  })
}

const handleClose = () => {
  resetForm()
  showAddDialog.value = false
}
</script>

