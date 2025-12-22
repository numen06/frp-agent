<template>
  <div>
    <!-- 服务器列表 -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">服务器管理</h3>
        <div class="card-actions">
          <button class="btn btn-primary btn-sm" @click="showAddDialog = true">
            <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
              <path d="M12 5l0 14" />
              <path d="M5 12l14 0" />
            </svg>
            添加服务器
          </button>
        </div>
      </div>
      <div class="card-body">
        <div class="table-responsive">
          <table class="table table-vcenter card-table">
            <thead>
              <tr>
                <th>服务器名称</th>
                <th>服务器地址</th>
                <th>端口</th>
                <th>API 地址</th>
                <th>连接状态</th>
                <th class="w-1">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="serversStore.loading">
                <td colspan="6" class="text-center py-4">
                  <div class="spinner-border spinner-border-sm" role="status"></div>
                  <span class="ms-2">加载中...</span>
                </td>
              </tr>
              <tr v-else-if="serversStore.servers.length === 0">
                <td colspan="6" class="text-center text-muted py-4">暂无服务器</td>
              </tr>
              <tr v-else v-for="server in serversStore.servers" :key="server.id">
                <td>{{ server.name }}</td>
                <td>{{ server.server_addr }}</td>
                <td>{{ server.server_port }}</td>
                <td><small>{{ server.api_base_url }}</small></td>
                <td>
                  <span class="badge" :class="getServerStatusBadgeClass(server)">
                    {{ getServerStatusText(server) }}
                  </span>
                </td>
                <td>
                  <div class="dropdown dropend">
                    <button class="btn btn-sm dropdown-toggle" data-bs-toggle="dropdown">
                      操作
                    </button>
                    <div class="dropdown-menu">
                      <a class="dropdown-item" href="#" @click.prevent="editServer(server)">
                        <svg xmlns="http://www.w3.org/2000/svg" class="icon dropdown-item-icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                          <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                          <path d="M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1" />
                          <path d="M20.385 6.585a2.1 2.1 0 0 0 -2.97 -2.97l-8.415 8.385v3h3l8.385 -8.415z" />
                          <path d="M16 5l3 3" />
                        </svg>
                        编辑
                      </a>
                      <a class="dropdown-item" href="#" @click.prevent="testServer(server)">
                        <svg xmlns="http://www.w3.org/2000/svg" class="icon dropdown-item-icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                          <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                          <path d="M5 12l5 -5l10 10l-5 5z" />
                          <path d="M12 5l7 7" />
                        </svg>
                        测试连接
                      </a>
                      <div class="dropdown-divider"></div>
                      <a class="dropdown-item text-danger" href="#" @click.prevent="deleteServer(server)">
                        <svg xmlns="http://www.w3.org/2000/svg" class="icon dropdown-item-icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                          <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                          <path d="M4 7l16 0" />
                          <path d="M10 11l0 6" />
                          <path d="M14 11l0 6" />
                          <path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12" />
                          <path d="M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3" />
                        </svg>
                        删除
                      </a>
                    </div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 添加/编辑服务器对话框 -->
    <div v-if="showAddDialog" class="modal-backdrop fade show" @click="closeAddDialog"></div>
    <div class="modal modal-blur fade" :class="{ show: showAddDialog, 'd-block': showAddDialog }" tabindex="-1" role="dialog" :style="showAddDialog ? 'display: block;' : ''" @click.self="closeAddDialog">
      <div class="modal-dialog modal-dialog-centered" role="document" @click.stop>
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ editingServer ? '编辑服务器' : '添加服务器' }}</h5>
            <button type="button" class="btn-close" @click="closeAddDialog"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">服务器名称 <span class="text-danger">*</span></label>
              <input type="text" class="form-control" v-model="serverForm.name" required />
            </div>
            <div class="mb-3">
              <label class="form-label">服务器地址 <span class="text-danger">*</span></label>
              <input type="text" class="form-control" v-model="serverForm.server_addr" @change="generateApiUrl" required />
            </div>
            <div class="mb-3">
              <label class="form-label">服务器端口 <span class="text-danger">*</span></label>
              <input type="number" class="form-control" v-model.number="serverForm.server_port" min="1" max="65535" required />
            </div>
            <div class="mb-3">
              <label class="form-label">API 基础地址 <span class="text-danger">*</span></label>
              <input type="text" class="form-control" v-model="serverForm.api_base_url" required />
              <small class="form-hint">可自动生成或手动修改</small>
            </div>
            <div class="mb-3">
              <label class="form-label">认证用户名 <span class="text-danger">*</span></label>
              <input type="text" class="form-control" v-model="serverForm.auth_username" required />
            </div>
            <div class="mb-3">
              <label class="form-label">认证密码 <span class="text-danger">*</span></label>
              <input type="password" class="form-control" v-model="serverForm.auth_password" required />
            </div>
            <div class="mb-3">
              <label class="form-label">认证 Token</label>
              <input type="text" class="form-control" v-model="serverForm.auth_token" placeholder="可选，留空表示使用用户名密码认证" />
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary me-auto" @click="closeAddDialog">取消</button>
            <button type="button" class="btn btn-secondary" @click="testConnection">测试连接</button>
            <button type="button" class="btn btn-primary" @click="handleSubmit">保存</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useServersStore } from '@/stores/servers'
import { useModal } from '@/composables/useModal'

const serversStore = useServersStore()
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

onMounted(async () => {
  try {
    await serversStore.loadServers()
  } catch (error) {
    console.error('加载服务器列表失败:', error)
  }
})

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
    await serversStore.loadServers()
  } catch (error) {
    alert('删除失败: ' + error.message)
  }
}

const testServer = async (server) => {
  try {
    await serversStore.testServer(server.id)
    alert('连接测试成功')
    await serversStore.loadServers()
  } catch (error) {
    alert('连接测试失败: ' + error.message)
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

const closeAddDialog = () => {
  showAddDialog.value = false
  resetForm()
}

// 使用统一的模态框功能
useModal(showAddDialog, closeAddDialog)

const getServerStatusBadgeClass = (server) => {
  if (!server.last_test_status || server.last_test_status === 'unknown') return 'text-bg-secondary'
  return server.last_test_status === 'online' ? 'text-bg-success' : 'text-bg-danger'
}

const getServerStatusText = (server) => {
  if (!server.last_test_status || server.last_test_status === 'unknown') return '未测试'
  return server.last_test_status === 'online' ? '在线' : '离线'
}
</script>

<style scoped>
/* 确保下拉菜单在表格中正确显示 */
.table td .dropdown {
  position: static;
}

.table td .dropdown-menu {
  z-index: 1050;
}
</style>

