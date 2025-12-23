<template>
  <div>
    <!-- 快捷新建分组功能说明（可展开/收起） -->
    <div v-if="showQuickSetupHelp" class="card mb-3 border-info">
      <div class="card-header bg-info bg-opacity-10">
        <div class="d-flex align-items-center justify-content-between">
          <div class="d-flex align-items-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="icon text-info me-2" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
              <path d="M12 9v2m0 4v.01" />
              <path d="M5 19h14a2 2 0 0 0 1.84 -2.75l-7.1 -12.25a2 2 0 0 0 -3.5 0l-7.1 12.25a2 2 0 0 0 1.75 2.75" />
            </svg>
            <h5 class="card-title mb-0 text-info">快捷新建分组功能</h5>
          </div>
          <button class="btn btn-sm btn-ghost-primary" @click="showQuickSetupHelp = false">
            <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
              <path d="M18 6l-12 12" />
              <path d="M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
      <div class="card-body">
        <p class="mb-2">
          <strong>功能说明：</strong>客户机器可以通过 API Key 认证，直接访问接口自动创建分组并获取默认配置。
        </p>
        <div class="mb-2">
          <strong>接口地址：</strong>
          <code class="ms-2">GET /api/frpc/config/{server}/{group}</code>
        </div>
        <div class="mb-2">
          <strong>功能特点：</strong>
          <ul class="mb-0 mt-1">
            <li>支持 API Key 认证（URL 参数 <code>api_key</code>）</li>
            <li>服务器和分组都在路径中，更直观易用</li>
            <li>支持可选参数：<code>format</code>（ini/toml，默认ini）、<code>client_name</code>（客户端名称）</li>
            <li>服务器参数可以是服务器名称或服务器ID</li>
          </ul>
        </div>
        <div class="mb-2">
          <strong>选择 API Key（可选）：</strong>
          <select class="form-select form-select-sm mt-1" v-model="selectedApiKeyId" style="max-width: 300px;" @change="handleApiKeyChange">
            <option :value="null">不选择（使用 YOUR_API_KEY 占位符）</option>
            <option v-for="apiKey in apiKeys" :key="apiKey.id" :value="apiKey.id">
              {{ apiKey.description }} ({{ apiKey.is_active ? '激活' : '未激活' }})
            </option>
          </select>
        </div>
        <div class="mb-0">
          <div class="d-flex justify-content-between align-items-center mb-1">
            <strong>使用示例（可直接复制执行）：</strong>
            <button class="btn btn-sm btn-primary" @click="copyExampleCommand">
              <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="16" height="16" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M8 8m0 2a2 2 0 0 1 2 -2h8a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2z" />
                <path d="M16 8v-2a2 2 0 0 0 -2 -2h-8a2 2 0 0 0 -2 2v8a2 2 0 0 0 2 2h2" />
              </svg>
              复制命令
            </button>
          </div>
          <pre class="bg-dark text-light p-2 rounded mt-1 mb-0" style="font-size: 0.875rem; position: relative; background-color: #1a1a1a !important; color: #ffffff !important; white-space: pre-wrap; word-wrap: break-word; overflow-wrap: break-word;"><code class="text-light" id="exampleCommand" style="color: #ffffff !important;">{{ exampleCommand }}</code></pre>
        </div>
      </div>
    </div>

    <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
      <p class="text-muted mb-0">管理所有代理分组，支持重命名和快速生成配置</p>
      <div class="d-flex gap-2">
        <button class="btn btn-info btn-sm" @click="showQuickSetupHelp = !showQuickSetupHelp">
          <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
            <path d="M12 9v2m0 4v.01" />
            <path d="M5 19h14a2 2 0 0 0 1.84 -2.75l-7.1 -12.25a2 2 0 0 0 -3.5 0l-7.1 12.25a2 2 0 0 0 1.75 2.75" />
          </svg>
          {{ showQuickSetupHelp ? '隐藏' : '快捷功能' }}
        </button>
        <button class="btn btn-primary btn-sm" @click="showCreateDialog = true">
          <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
            <path d="M12 5l0 14" />
            <path d="M5 12l14 0" />
          </svg>
          新增分组
        </button>
        <button class="btn btn-success btn-sm" @click="handleAutoAnalyze">
          <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
            <path d="M10 10m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0" />
            <path d="M21 21l-6 -6" />
          </svg>
          自动分析分组
        </button>
      </div>
    </div>
    
    <div class="card">
      <!-- 搜索和过滤区域 -->
      <div class="card-body border-bottom">
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
          <div style="width: 250px;">
            <TableSearch
              v-model="groupsStore.filters.search"
              placeholder="搜索分组名称..."
              @search="handleSearch"
            />
          </div>
        </div>
      </div>
      <!-- 表格区域 -->
      <div class="table-responsive">
        <table class="table table-vcenter card-table w-100">
        <thead>
          <tr>
            <th>分组名称</th>
            <th>代理数量</th>
            <th>在线</th>
            <th>离线</th>
            <th class="w-1">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="groupsStore.loading">
            <td colspan="5" class="text-center py-4">
              <div class="spinner-border spinner-border-sm" role="status"></div>
              <span class="ms-2">加载中...</span>
            </td>
          </tr>
          <tr v-else-if="groupsStore.groups.length === 0">
            <td colspan="5" class="text-center text-muted py-4">暂无分组，请先创建分组或导入配置</td>
          </tr>
          <tr v-else v-for="group in groupsStore.groups" :key="group.group_name">
            <td>
              <strong class="text-primary">{{ group.group_name }}</strong>
            </td>
            <td>{{ group.total_count }}</td>
            <td>
              <span class="badge text-bg-success">{{ group.online_count }}</span>
            </td>
            <td>
              <span class="badge text-bg-danger">{{ group.offline_count }}</span>
            </td>
            <td>
              <div class="dropdown">
                <button 
                  :ref="el => { if (el) getGroupDropdown(group.group_name).triggerRef.value = el }"
                  class="btn btn-sm dropdown-toggle" 
                  @click.prevent="getGroupDropdown(group.group_name).toggle()"
                  :aria-expanded="getGroupDropdown(group.group_name).isOpen.value"
                >
                  操作
                </button>
                <div 
                  :ref="el => { if (el) getGroupDropdown(group.group_name).dropdownRef.value = el }"
                  class="dropdown-menu"
                  :class="{ show: getGroupDropdown(group.group_name).isOpen.value }"
                  @click.stop
                >
                  <a class="dropdown-item" href="#" @click.prevent="viewGroupProxies(group.group_name); getGroupDropdown(group.group_name).close()">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon dropdown-item-icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <path d="M10 10m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0" />
                      <path d="M21 21l-6 -6" />
                    </svg>
                    查看代理
                  </a>
                  <a class="dropdown-item" href="#" @click.prevent="editGroup(group); getGroupDropdown(group.group_name).close()">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon dropdown-item-icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <path d="M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1" />
                      <path d="M20.385 6.585a2.1 2.1 0 0 0 -2.97 -2.97l-8.415 8.385v3h3l8.385 -8.415z" />
                      <path d="M16 5l3 3" />
                    </svg>
                    重命名
                  </a>
                  <a class="dropdown-item" href="#" @click.prevent="generateGroupConfig(group.group_name); getGroupDropdown(group.group_name).close()">
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon dropdown-item-icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <path d="M14 3v4a1 1 0 0 0 1 1h4" />
                      <path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z" />
                    </svg>
                    生成配置
                  </a>
                  <div class="dropdown-divider"></div>
                  <a class="dropdown-item text-danger" href="#" @click.prevent="deleteGroup(group); getGroupDropdown(group.group_name).close()">
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
      <!-- 分页 -->
      <div class="card-footer" v-if="groupsStore.pagination.total > 0">
        <TablePagination
          :total="groupsStore.pagination.total"
          :page="groupsStore.pagination.page"
          :page-size="groupsStore.pagination.page_size"
          @page-change="handlePageChange"
          @page-size-change="handlePageSizeChange"
        />
      </div>
    </div>

    <!-- 创建分组对话框 -->
    <div v-if="showCreateDialog" class="modal-backdrop fade show" @click="closeCreateDialog"></div>
    <div class="modal modal-blur fade" :class="{ show: showCreateDialog, 'd-block': showCreateDialog }" tabindex="-1" role="dialog" :style="showCreateDialog ? 'display: block;' : ''" @click.self="closeCreateDialog">
      <div class="modal-dialog modal-dialog-centered" role="document" @click.stop>
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">新增分组</h5>
            <button type="button" class="btn-close" @click="closeCreateDialog"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">分组名称 <span class="text-danger">*</span></label>
              <input type="text" class="form-control" v-model="createForm.group_name" placeholder="例如: dlyy" required />
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary me-auto" @click="closeCreateDialog">取消</button>
            <button type="button" class="btn btn-primary" @click="handleCreateGroup">创建</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 重命名分组对话框 -->
    <div v-if="showRenameDialog" class="modal-backdrop fade show" @click="closeRenameDialog"></div>
    <div class="modal modal-blur fade" :class="{ show: showRenameDialog, 'd-block': showRenameDialog }" tabindex="-1" role="dialog" :style="showRenameDialog ? 'display: block;' : ''" @click.self="closeRenameDialog">
      <div class="modal-dialog modal-dialog-centered" role="document" @click.stop>
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">重命名分组</h5>
            <button type="button" class="btn-close" @click="closeRenameDialog"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">新分组名称 <span class="text-danger">*</span></label>
              <input type="text" class="form-control" v-model="renameForm.new_name" required />
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary me-auto" @click="closeRenameDialog">取消</button>
            <button type="button" class="btn btn-primary" @click="handleRenameGroup">保存</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useGroupsStore } from '@/stores/groups'
import { useServersStore } from '@/stores/servers'
import { useModal } from '@/composables/useModal'
import { useDropdown } from '@/composables/useDropdown'
import { apiKeysApi } from '@/api/apiKeys'
import TablePagination from '@/components/TablePagination.vue'
import TableSearch from '@/components/TableSearch.vue'

const emit = defineEmits(['view-group', 'generate-config'])

const props = defineProps({
  serverId: {
    type: Number,
    required: true
  }
})

const groupsStore = useGroupsStore()
const serversStore = useServersStore()

// 每个分组的下拉菜单（使用 Map 存储）
const groupDropdowns = new Map()

const getGroupDropdown = (groupName) => {
  if (!groupDropdowns.has(groupName)) {
    groupDropdowns.set(groupName, useDropdown())
  }
  return groupDropdowns.get(groupName)
}

// 加载分组数据
const loadGroups = async (page = 1) => {
  if (props.serverId) {
    try {
      await groupsStore.loadGroups(props.serverId, {
        page,
        page_size: groupsStore.pagination.page_size,
        search: groupsStore.filters.search || undefined
      })
    } catch (error) {
      console.error('加载分组数据失败:', error)
    }
  }
}

// 组件挂载时加载数据
onMounted(async () => {
  // 确保服务器列表已加载
  if (serversStore.servers.length === 0) {
    try {
      await serversStore.loadServers()
    } catch (error) {
      console.error('加载服务器列表失败:', error)
    }
  }
  loadGroups()
})

// 监听 serverId 变化，重新加载数据
watch(() => props.serverId, (newId) => {
  if (newId) {
    loadGroups()
  }
})

// 监听服务器列表变化，确保示例命令能正确获取服务器名称
watch(() => serversStore.servers, () => {
  // 当服务器列表更新时，computed 属性会自动重新计算
}, { deep: true })

const showCreateDialog = ref(false)
const showRenameDialog = ref(false)
const showQuickSetupHelp = ref(false)
const currentGroup = ref(null)
const apiKeys = ref([])
const selectedApiKeyId = ref(null)
const loadingApiKeys = ref(false)

// 计算当前 API 基础 URL
const apiBaseUrl = computed(() => {
  const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'
  // 如果是相对路径，则使用当前域名
  if (baseURL.startsWith('/')) {
    return `${window.location.origin}${baseURL}`
  }
  // 如果是绝对路径，直接返回
  return baseURL
})

// 存储选中的 API Key 完整密钥
const selectedApiKeyFullKey = ref(null)

// 获取选中的 API Key 信息
const selectedApiKey = computed(() => {
  if (!selectedApiKeyId.value) {
    return null
  }
  const selectedKey = apiKeys.value.find(k => k.id === selectedApiKeyId.value)
  if (!selectedKey) {
    return null
  }
  
  return selectedKey
})

// 更新完整密钥的函数 - 先从 localStorage 读取，如果没有则从后端接口获取
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
        // 验证：确保不是 ID 本身（API Key 应该是一个长字符串，不会是单个数字）
        // API Key 通常是 64 字符（32字节的 base64url 编码），至少应该大于 20 字符
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
      // 找到了有效的完整密钥
      selectedApiKeyFullKey.value = fullKey
    } else {
      // 没找到或无效，清空
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

// 获取当前服务器名称或ID
const currentServerName = computed(() => {
  if (!props.serverId) {
    return 'server_name'
  }
  // 从 stores 获取服务器信息
  const server = serversStore.servers.find(s => s.id === props.serverId)
  if (server && server.name) {
    return encodeURIComponent(server.name)
  }
  // 如果没有找到，返回服务器ID
  return String(props.serverId)
})

// 获取示例分组名称（使用第一个分组或默认值）
const exampleGroupName = computed(() => {
  if (groupsStore.groups.length > 0) {
    return encodeURIComponent(groupsStore.groups[0].group_name)
  }
  return 'test'
})

// 计算示例命令 - 从 localStorage 读取的密钥或使用占位符
const exampleCommand = computed(() => {
  // 使用从 localStorage 读取的密钥，如果没有则使用占位符
  // 确保响应式更新：直接使用 selectedApiKeyFullKey.value
  let apiKey = 'YOUR_API_KEY'
  if (selectedApiKeyFullKey.value) {
    const trimmed = selectedApiKeyFullKey.value.trim()
    // 确保不是空字符串且长度足够
    if (trimmed && trimmed.length > 20) {
      apiKey = trimmed
    }
  }
  const baseUrl = apiBaseUrl.value
  const serverName = currentServerName.value
  const groupName = exampleGroupName.value
  // 生成单行命令（更易复制执行）- 使用新的端点格式，服务器和分组都在路径中
  return `curl "${baseUrl}/frpc/config/${serverName}/${groupName}?format=toml&api_key=${apiKey}" -o frpc.toml`
})

// 获取选中的 API Key 描述
const selectedApiKeyDescription = computed(() => {
  return selectedApiKey.value ? selectedApiKey.value.description : null
})

// 加载 API Key 列表
const loadApiKeys = async () => {
  loadingApiKeys.value = true
  try {
    const keys = await apiKeysApi.list(0, 100)
    // 只显示激活的密钥
    apiKeys.value = keys.filter(k => k.is_active && !k.is_expired)
    
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
    // 静默复制，不显示提示
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
    } catch (err) {
      // 静默失败
    }
    document.body.removeChild(textArea)
  }
}

// 当展开说明时加载 API Key 列表
watch(showQuickSetupHelp, (newVal) => {
  if (newVal && apiKeys.value.length === 0) {
    loadApiKeys()
  }
})

const createForm = reactive({
  group_name: ''
})

const renameForm = reactive({
  new_name: ''
})

const handleCreateGroup = async () => {
  if (!createForm.group_name) {
    alert('请输入分组名称')
    return
  }
  
  try {
    await groupsStore.createGroup({
      group_name: createForm.group_name,
      frps_server_id: props.serverId
    })
    alert('创建分组成功')
    showCreateDialog.value = false
    createForm.group_name = ''
    // 刷新分组列表，重置到第一页
    groupsStore.setPagination({ page: 1 })
    await loadGroups(1)
  } catch (error) {
    alert('创建分组失败: ' + error.message)
  }
}

const editGroup = (group) => {
  currentGroup.value = group
  renameForm.new_name = group.group_name
  showRenameDialog.value = true
}

const handleRenameGroup = async () => {
  if (!renameForm.new_name || !currentGroup.value) {
    alert('请输入新分组名称')
    return
  }
  
  try {
    await groupsStore.updateGroup(
      currentGroup.value.group_name,
      renameForm.new_name,
      props.serverId
    )
    alert('重命名成功')
    showRenameDialog.value = false
    // 刷新分组列表，保持当前页
    await loadGroups(groupsStore.pagination.page)
  } catch (error) {
    alert('重命名失败: ' + error.message)
  }
}

const deleteGroup = async (group) => {
  const reassignGroup = prompt(
    `确定要删除分组 "${group.group_name}" 吗？该分组下有 ${group.total_count} 个代理。\n请输入目标分组名称（留空则移动到"其他"分组）：`
  )
  
  if (reassignGroup === null) {
    return
  }
  
  try {
    await groupsStore.deleteGroup(group.group_name, reassignGroup || '', props.serverId)
    alert('删除成功')
    // 刷新分组列表，保持当前页
    await loadGroups(groupsStore.pagination.page)
  } catch (error) {
    alert('删除失败: ' + error.message)
  }
}

const handleAutoAnalyze = async () => {
  if (!confirm('将从代理名称中自动分析分组。\n\n注意：仅对分组为"其他"或空的代理进行分析，不会覆盖已有的分组。\n\n是否继续？')) {
    return
  }
  
  try {
    const result = await groupsStore.autoAnalyzeGroups(props.serverId)
    // 显示详细结果
    if (result && result.analysis) {
      const analysis = result.analysis
      let message = `✓ 分析完成！\n\n`
      message += `总代理数: ${analysis.total}\n`
      message += `更新数量: ${analysis.updated}\n`
      message += `跳过数量: ${analysis.skipped} (已有分组)\n`
      message += `未变化: ${analysis.unchanged}\n\n`
      
      if (Object.keys(analysis.groups_found).length > 0) {
        message += `发现的分组:\n`
        Object.entries(analysis.groups_found).sort().forEach(([group, count]) => {
          message += `  • ${group}: ${count} 个代理\n`
        })
      }
      
      if (analysis.new_groups && analysis.new_groups.length > 0) {
        message += `\n新识别的分组: ${analysis.new_groups.join(', ')}`
      }
      
      alert(message)
    } else {
      alert('自动分析分组成功')
    }
    // 刷新分组列表，重置到第一页
    groupsStore.setPagination({ page: 1 })
    await loadGroups(1)
  } catch (error) {
    alert('自动分析失败: ' + error.message)
  }
}

const viewGroupProxies = (groupName) => {
  emit('view-group', groupName)
}

const generateGroupConfig = (groupName) => {
  emit('generate-config', groupName)
}

const closeCreateDialog = () => {
  showCreateDialog.value = false
  createForm.group_name = ''
}

const closeRenameDialog = () => {
  showRenameDialog.value = false
  renameForm.new_name = ''
}

// 使用统一的模态框功能
useModal(showCreateDialog, closeCreateDialog)
useModal(showRenameDialog, closeRenameDialog)

// 分页处理
const handlePageChange = (newPage) => {
  loadGroups(newPage)
}

const handlePageSizeChange = (newPageSize) => {
  groupsStore.setPagination({ page_size: newPageSize, page: 1 })
  loadGroups(1)
}

// 搜索处理
const handleSearch = () => {
  groupsStore.setPagination({ page: 1 })
  loadGroups(1)
}
</script>

