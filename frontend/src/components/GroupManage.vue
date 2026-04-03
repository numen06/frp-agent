<template>
  <div>
    <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
      <p class="mb-0 text-sm text-gray-500">管理所有代理分组，支持重命名和快速生成配置</p>
      <div class="flex flex-wrap gap-2">
        <button
          type="button"
          class="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700"
          @click="showCreateDialog = true"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none" />
            <path d="M12 5l0 14" />
            <path d="M5 12l14 0" />
          </svg>
          新增分组
        </button>
        <button
          type="button"
          class="inline-flex items-center justify-center gap-2 rounded-lg bg-green-600 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-green-700"
          @click="handleAutoAnalyze"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none" />
            <path d="M10 10m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0" />
            <path d="M21 21l-6 -6" />
          </svg>
          自动分析分组
        </button>
      </div>
    </div>

    <div class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <div class="p-6">
        <div class="mb-3">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="w-full max-w-[250px] min-w-[200px]">
              <TableSearch
                v-model="groupsStore.filters.search"
                placeholder="搜索分组名称..."
                @search="handleSearch"
              />
            </div>
          </div>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full border-collapse text-left text-sm text-gray-700">
            <thead>
              <tr>
                <th class="border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">分组名称</th>
                <th class="border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">代理数量</th>
                <th class="border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">在线</th>
                <th class="border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">离线</th>
                <th class="w-[1%] whitespace-nowrap border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="groupsStore.loading">
                <td colspan="5" class="py-4 text-center">
                  <span class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600 align-middle" role="status" aria-label="加载中" />
                  <span class="ml-2 align-middle text-gray-600">加载中...</span>
                </td>
              </tr>
              <tr v-else-if="groupsStore.groups.length === 0">
                <td colspan="5" class="py-4 text-center text-gray-500">暂无分组，请先创建分组或导入配置</td>
              </tr>
              <tr
                v-else
                v-for="group in groupsStore.groups"
                :key="group.group_name"
                :data-group-name="group.group_name"
                :class="{ 'bg-amber-50': props.highlightGroup === group.group_name }"
              >
                <td class="border-b border-gray-100 px-4 py-3 align-middle">
                  <strong
                    class="font-semibold"
                    :class="props.highlightGroup === group.group_name ? 'text-amber-600' : 'text-blue-600'"
                  >{{ group.group_name }}</strong>
                </td>
                <td class="border-b border-gray-100 px-4 py-3 align-middle">{{ group.total_count }}</td>
                <td class="border-b border-gray-100 px-4 py-3 align-middle">
                  <span class="inline-flex rounded-md bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">{{ group.online_count }}</span>
                </td>
                <td class="border-b border-gray-100 px-4 py-3 align-middle">
                  <span class="inline-flex rounded-md bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">{{ group.offline_count }}</span>
                </td>
                <td class="border-b border-gray-100 px-4 py-3 align-middle">
                  <div class="inline-flex items-center gap-2">
                    <button
                      class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-blue-700 transition-colors hover:bg-blue-100"
                      title="查看代理"
                      aria-label="查看代理"
                      @click="viewGroupProxies(group.group_name)"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                        <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                        <path d="M10 10m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0" />
                        <path d="M21 21l-6 -6" />
                      </svg>
                    </button>
                    <button
                      class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-green-50 text-green-700 transition-colors hover:bg-green-100"
                      title="一键安装"
                      aria-label="一键安装"
                      @click="handleOneClickInstall(group, $event)"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                        <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                        <path d="M12 3l0 18" />
                        <path d="M8 7l4 -4l4 4" />
                        <path d="M8 17l4 4l4 -4" />
                      </svg>
                    </button>
                    <button
                      class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-purple-50 text-purple-700 transition-colors hover:bg-purple-100"
                      title="一键下载"
                      aria-label="一键下载"
                      @click="handleOneClickDownload(group, $event)"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                        <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                        <path d="M8 8m0 2a2 2 0 0 1 2 -2h8a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2z" />
                        <path d="M16 8v-2a2 2 0 0 0 -2 -2h-8a2 2 0 0 0 -2 2v8a2 2 0 0 0 2 2h2" />
                      </svg>
                    </button>
                    <div class="relative">
                      <button
                        type="button"
                        class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gray-100 text-gray-700 transition-colors hover:bg-gray-200"
                        title="更多"
                        aria-label="更多操作"
                        @click.stop="toggleGroupMore(group.group_name)"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                          <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                          <circle cx="5" cy="12" r="1" fill="currentColor" />
                          <circle cx="12" cy="12" r="1" fill="currentColor" />
                          <circle cx="19" cy="12" r="1" fill="currentColor" />
                        </svg>
                      </button>
                      <div
                        v-if="openMoreGroupName === group.group_name"
                        class="absolute right-0 top-full z-50 mt-1 min-w-[140px] rounded-lg border border-gray-200 bg-white py-1 shadow-lg"
                        @click.stop
                      >
                        <a
                          class="flex cursor-pointer items-center px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-100"
                          href="#"
                          @click.prevent="editGroup(group); openMoreGroupName = ''"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" class="mr-1.5 h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                            <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                            <path d="M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1" />
                            <path d="M20.385 6.585a2.1 2.1 0 0 0 -2.97 -2.97l-8.415 8.385v3h3l8.385 -8.415z" />
                            <path d="M16 5l3 3" />
                          </svg>
                          修改
                        </a>
                        <a
                          class="flex cursor-pointer items-center px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-100"
                          href="#"
                          @click.prevent="generateGroupConfig(group.group_name); openMoreGroupName = ''"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" class="mr-1.5 h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                            <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                            <path d="M14 3v4a1 1 0 0 0 1 1h4" />
                            <path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z" />
                          </svg>
                          生成配置
                        </a>
                        <div class="my-1 border-t border-gray-100"></div>
                        <a
                          class="flex cursor-pointer items-center px-3 py-1.5 text-sm text-red-600 transition-colors hover:bg-red-50"
                          href="#"
                          @click.prevent="deleteGroup(group); openMoreGroupName = ''"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" class="mr-1.5 h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                            <path stroke="none" d="M0 0h24v24H0z" fill="none" />
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
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="groupsStore.pagination.total > 0" class="mt-3">
          <TablePagination
            :total="groupsStore.pagination.total"
            :page="groupsStore.pagination.page"
            :page-size="groupsStore.pagination.page_size"
            @page-change="handlePageChange"
            @page-size-change="handlePageSizeChange"
          />
        </div>
      </div>
    </div>

    <!-- 创建分组对话框 -->
    <Teleport to="body">
      <div
        v-if="showCreateDialog"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
      >
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="closeCreateDialog" />
        <div
          class="relative z-10 w-full max-w-md rounded-xl border border-gray-200 bg-white p-0 shadow-xl"
          @click.stop
        >
          <div class="flex items-center justify-between border-b border-gray-200 px-6 py-4">
            <h2 class="text-lg font-semibold text-gray-900">新增分组</h2>
            <button
              type="button"
              class="inline-flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800"
              aria-label="关闭"
              @click="closeCreateDialog"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                <path d="M18 6l-12 12" />
                <path d="M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="px-6 py-4">
            <label class="mb-1 block text-sm font-medium text-gray-700">
              分组名称 <span class="text-red-600">*</span>
            </label>
            <input
              v-model="createForm.group_name"
              type="text"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm transition-colors focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              placeholder="例如: dlyy"
              required
            />
          </div>
          <div class="flex flex-wrap items-center justify-end gap-2 border-t border-gray-200 bg-gray-50 px-6 py-4">
            <button
              type="button"
              class="mr-auto inline-flex items-center justify-center rounded-lg bg-gray-200 px-3 py-2 text-sm font-medium text-gray-800 transition-colors hover:bg-gray-300"
              @click="closeCreateDialog"
            >
              取消
            </button>
            <button
              type="button"
              class="inline-flex items-center justify-center rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
              @click="handleCreateGroup"
            >
              创建
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 重命名分组对话框 -->
    <Teleport to="body">
      <div
        v-if="showRenameDialog"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
      >
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="closeRenameDialog" />
        <div
          class="relative z-10 w-full max-w-md rounded-xl border border-gray-200 bg-white p-0 shadow-xl"
          @click.stop
        >
          <div class="flex items-center justify-between border-b border-gray-200 px-6 py-4">
            <h2 class="text-lg font-semibold text-gray-900">重命名分组</h2>
            <button
              type="button"
              class="inline-flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800"
              aria-label="关闭"
              @click="closeRenameDialog"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                <path d="M18 6l-12 12" />
                <path d="M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="px-6 py-4">
            <label class="mb-1 block text-sm font-medium text-gray-700">
              新分组名称 <span class="text-red-600">*</span>
            </label>
            <input
              v-model="renameForm.new_name"
              type="text"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm transition-colors focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              required
            />
          </div>
          <div class="flex flex-wrap items-center justify-end gap-2 border-t border-gray-200 bg-gray-50 px-6 py-4">
            <button
              type="button"
              class="mr-auto inline-flex items-center justify-center rounded-lg bg-gray-200 px-3 py-2 text-sm font-medium text-gray-800 transition-colors hover:bg-gray-300"
              @click="closeRenameDialog"
            >
              取消
            </button>
            <button
              type="button"
              class="inline-flex items-center justify-center rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
              @click="handleRenameGroup"
            >
              保存
            </button>
          </div>
        </div>
      </div>
    </Teleport>
    <GroupProxiesDialog
      v-model="showGroupProxiesDialog"
      :server-id="props.serverId"
      :group-name="selectedGroupForProxies"
      @success="handleGroupProxiesChanged"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, nextTick, onUnmounted } from 'vue'
import { useGroupsStore } from '@/stores/groups'
import { useServersStore } from '@/stores/servers'
import { useModal } from '@/composables/useModal'
import { useApiKeysStore } from '@/stores/apiKeys'
import { copyWithTooltip } from '@/composables/useCopyTooltip'
import { groupApi } from '@/api/groups'
import TablePagination from '@/components/TablePagination.vue'
import TableSearch from '@/components/TableSearch.vue'
import GroupProxiesDialog from '@/components/GroupProxiesDialog.vue'

const emit = defineEmits(['generate-config'])

const props = defineProps({
  serverId: {
    type: Number,
    required: true
  },
  highlightGroup: {
    type: String,
    default: ''
  }
})

const groupsStore = useGroupsStore()
const serversStore = useServersStore()
const apiKeysStore = useApiKeysStore()

// 更多下拉菜单状态
const openMoreGroupName = ref('')

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
  loadApiKeys()
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

// 监听高亮分组变化，自动设置搜索框并滚动到对应位置
watch(() => props.highlightGroup, async (groupName) => {
  if (groupName) {
    // 自动设置搜索框的值，这样就能筛选到对应的分组
    groupsStore.setFilters({ search: groupName })
    groupsStore.setPagination({ page: 1 })
    await loadGroups(1)

    await nextTick()
    // 查找对应的表格行并滚动到该位置
    const row = document.querySelector(`tr[data-group-name="${groupName}"]`)
    if (row) {
      row.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }
}, { immediate: true })

// 监听分组列表变化，如果有高亮分组则滚动到对应位置
watch(() => groupsStore.groups, async () => {
  if (props.highlightGroup && groupsStore.groups.length > 0) {
    await nextTick()
    const row = document.querySelector(`tr[data-group-name="${props.highlightGroup}"]`)
    if (row) {
      row.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }
})

const showCreateDialog = ref(false)
const showRenameDialog = ref(false)
const showGroupProxiesDialog = ref(false)
const currentGroup = ref(null)
const selectedGroupForProxies = ref('')
const selectedApiKeyId = computed({
  get: () => apiKeysStore.selectedKeyId,
  set: (id) => apiKeysStore.setDefaultKey(id)
})

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

// 更新完整密钥的函数 - 先从 localStorage 读取，如果没有则从后端接口获取
const updateFullKey = async () => {
  if (selectedApiKeyId.value) {
    // 先尝试从 localStorage 读取
    const id = selectedApiKeyId.value
    const fullKey = await apiKeysStore.resolveFullKey(id)
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
watch(selectedApiKeyId, () => {
  updateFullKey()
}, { immediate: true })

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

// 根据分组名称生成 curl 命令
const buildGroupCommand = (groupName) => {
  let apiKey = 'YOUR_API_KEY'
  if (selectedApiKeyFullKey.value) {
    const trimmed = selectedApiKeyFullKey.value.trim()
    if (trimmed && trimmed.length > 20) {
      apiKey = trimmed
    }
  }
  const baseUrl = apiBaseUrl.value
  const serverName = currentServerName.value
  const encodedGroupName = encodeURIComponent(groupName)
  return `mkdir -p /opt/frp && curl "${baseUrl}/frpc/config/${serverName}/${encodedGroupName}?format=toml&api_key=${encodeURIComponent(apiKey)}" -o /opt/frp/frpc.toml`
}

// 复制分组命令到剪贴板
const copyGroupCommand = async (groupName, event) => {
  const command = buildGroupCommand(groupName)
  await copyWithTooltip(command, event)
}

// 加载 API Key 列表
const loadApiKeys = async () => {
  if (apiKeysStore.selectedKeyId === null) {
    apiKeysStore.selectedKeyId = apiKeysStore.getStoredDefaultId()
  }
  await apiKeysStore.loadKeys()
  if (selectedApiKeyId.value) {
    await updateFullKey()
  }
}


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
  // 确保 serverId 存在且有效
  if (!props.serverId) {
    alert('服务器ID无效，无法删除分组')
    return
  }

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
  selectedGroupForProxies.value = groupName
  showGroupProxiesDialog.value = true
}

const generateGroupConfig = (groupName) => {
  emit('generate-config', groupName)
}

const handleGroupProxiesChanged = async () => {
  await loadGroups(groupsStore.pagination.page)
}

const closeCreateDialog = () => {
  showCreateDialog.value = false
  createForm.group_name = ''
}

const closeRenameDialog = () => {
  showRenameDialog.value = false
  renameForm.new_name = ''
}

// 一键安装：后端生成完整安装脚本，前端只复制一条短命令
const handleOneClickInstall = async (group, event) => {
  try {
    let apiKey = selectedApiKeyFullKey.value
    if (!apiKey) {
      await updateFullKey()
      apiKey = selectedApiKeyFullKey.value
    }
    if (!apiKey) {
      alert('无法获取有效的 API Key，请先在密钥管理中创建或设置默认密钥')
      return
    }

    const serverName = currentServerName.value
    const url = groupApi.getQuickInstallUrl({
      group_name: group.group_name,
      server_name: serverName,
      api_key: apiKey,
      install_path: '/opt/frp'
    })
    const cmd = `curl -sL "${window.location.origin}${url}" | bash`

    await copyWithTooltip(cmd, event)
  } catch (error) {
    console.error('一键安装失败:', error)
    alert('一键安装失败: ' + error.message)
  }
}

// 更多下拉菜单切换
const toggleGroupMore = (groupName) => {
  openMoreGroupName.value = openMoreGroupName.value === groupName ? '' : groupName
}

// 点击页面其他区域关闭更多菜单
const closeMoreOnOutsideClick = (e) => {
  if (openMoreGroupName.value && !e.target.closest('.relative')) {
    openMoreGroupName.value = ''
  }
}
onMounted(() => document.addEventListener('click', closeMoreOnOutsideClick))
onUnmounted(() => document.removeEventListener('click', closeMoreOnOutsideClick))

// 一键下载：后端生成完整下载脚本，前端只复制一条短命令
const handleOneClickDownload = async (group, event) => {
  try {
    let apiKey = selectedApiKeyFullKey.value
    if (!apiKey) {
      await updateFullKey()
      apiKey = selectedApiKeyFullKey.value
    }
    if (!apiKey) {
      alert('无法获取有效的 API Key，请先在密钥管理中创建或设置默认密钥')
      return
    }

    const serverName = currentServerName.value
    const url = groupApi.getQuickDownloadUrl({
      group_name: group.group_name,
      server_name: serverName,
      api_key: apiKey,
      install_path: '/opt/frp'
    })
    const cmd = `curl -sL "${window.location.origin}${url}" | bash`

    await copyWithTooltip(cmd, event)
  } catch (error) {
    console.error('一键下载失败:', error)
    alert('一键下载失败: ' + error.message)
  }
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
