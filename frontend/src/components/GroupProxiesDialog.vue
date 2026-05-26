<template>
  <Teleport to="body">
    <div
      v-if="dialogVisible"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
    >
      <div
        class="absolute inset-0 bg-black/40 backdrop-blur-sm"
        aria-hidden="true"
        @click="handleBackdropClick"
      />
      <div
        class="group-proxies-dialog relative z-10 flex max-h-[min(82vh,700px)] w-full flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-xl will-change-transform"
        role="document"
        @click.stop
      >
        <div class="flex shrink-0 items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 class="text-lg font-semibold text-gray-900">
            查看代理 - {{ props.groupName || '-' }}
          </h2>
          <button
            type="button"
            class="inline-flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800"
            aria-label="关闭"
            @click="closeDialog"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none" />
              <path d="M18 6l-12 12" />
              <path d="M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="group-proxies-body min-h-0 flex-1 px-6 py-4">
          <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div class="flex flex-wrap items-center gap-2">
              <div class="w-[250px] min-w-[200px]">
                <TableSearch
                  v-model="filters.search"
                  placeholder="搜索代理名称..."
                  @search="handleSearch"
                />
              </div>
              <AppSelect class="w-auto" size="sm" v-model="filters.status" @change="handleFilterChange">
                <option value="">全部状态</option>
                <option value="online">在线</option>
                <option value="offline">离线</option>
              </AppSelect>
            </div>
            <div class="flex flex-wrap gap-2">
              <button
                type="button"
                class="inline-flex items-center justify-center gap-2 rounded-lg bg-green-600 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
                @click="showAddProxyDialog = true"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                  <path d="M12 5l0 14" />
                  <path d="M5 12l14 0" />
                </svg>
                添加
              </button>
              <button
                type="button"
                class="inline-flex items-center justify-center gap-2 rounded-lg bg-amber-500 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="loading || generatingDefaults"
                @click="generateStandardProxies"
              >
                <span
                  v-if="generatingDefaults"
                  class="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white"
                  role="status"
                  aria-label="加载中"
                />
                <svg
                  v-else
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-4 w-4"
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  stroke-width="2"
                  stroke="currentColor"
                  fill="none"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                  <path d="M12 3l0 18" />
                  <path d="M7 12l5 5l5 -5" />
                </svg>
                生成标准代理
              </button>
              <button
                type="button"
                class="inline-flex items-center justify-center gap-2 rounded-lg bg-green-600 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="loading"
                @click="syncFromFrps"
              >
                <span
                  v-if="loading"
                  class="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white"
                  role="status"
                  aria-label="加载中"
                />
                <svg
                  v-else
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-4 w-4"
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  stroke-width="2"
                  stroke="currentColor"
                  fill="none"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                  <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
                  <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4" />
                </svg>
                同步
              </button>
              <button
                type="button"
                class="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="loading"
                @click="loadData(pagination.page)"
              >
                <span
                  v-if="loading"
                  class="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white"
                  role="status"
                  aria-label="加载中"
                />
                <svg
                  v-else
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-4 w-4"
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  stroke-width="2"
                  stroke="currentColor"
                  fill="none"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                  <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
                  <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4" />
                </svg>
                刷新
              </button>
            </div>
          </div>

          <div class="group-proxies-table-wrap overflow-x-auto">
            <table class="w-full border-collapse text-left text-sm text-gray-700">
              <thead>
                <tr>
                  <th class="border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">代理名称</th>
                  <th class="border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">类型</th>
                  <th class="border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">本地IP</th>
                  <th class="border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">本地端口</th>
                  <th class="border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">远程端口</th>
                  <th class="border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">frpc 版本</th>
                  <th class="border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">状态</th>
                  <th class="w-[1%] whitespace-nowrap border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="loading">
                  <td colspan="8" class="py-4 text-center">
                    <span class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600 align-middle" role="status" aria-label="加载中" />
                    <span class="ml-2 align-middle text-gray-600">加载中...</span>
                  </td>
                </tr>
                <tr v-else-if="proxies.length === 0">
                  <td colspan="8" class="py-4 text-center text-gray-500">当前分组暂无代理</td>
                </tr>
                <tr v-else v-for="proxy in proxies" :key="proxy.id">
                  <td class="border-b border-gray-100 px-4 py-3 align-middle">
                    <div class="max-w-[200px] truncate" :title="proxy.name">{{ proxy.name }}</div>
                  </td>
                  <td class="border-b border-gray-100 px-4 py-3 align-middle">
                    <span class="inline-flex rounded-md bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-800">{{ proxy.proxy_type.toUpperCase() }}</span>
                  </td>
                  <td class="border-b border-gray-100 px-4 py-3 align-middle">{{ proxy.local_ip }}</td>
                  <td class="border-b border-gray-100 px-4 py-3 align-middle">{{ proxy.local_port || '-' }}</td>
                  <td class="border-b border-gray-100 px-4 py-3 align-middle">{{ proxy.remote_port || '-' }}</td>
                  <td class="border-b border-gray-100 px-4 py-3 align-middle text-gray-600">{{ proxy.client_version || '未知' }}</td>
                  <td class="border-b border-gray-100 px-4 py-3 align-middle">
                    <span
                      class="inline-flex rounded-md px-2 py-0.5 text-xs font-medium"
                      :class="proxy.status === 'online' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'"
                    >
                      {{ proxy.status === 'online' ? '在线' : '离线' }}
                    </span>
                  </td>
                  <td class="border-b border-gray-100 px-4 py-3 align-middle">
                    <div class="inline-flex items-center gap-2">
                      <button
                        class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gray-100 text-gray-700 transition-colors hover:bg-gray-200"
                        title="编辑"
                        aria-label="编辑"
                        @click="editProxy(proxy)"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                          <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                          <path d="M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1" />
                          <path d="M20.385 6.585a2.1 2.1 0 0 0 -2.97 -2.97l-8.415 8.385v3h3l8.385 -8.415z" />
                          <path d="M16 5l3 3" />
                        </svg>
                      </button>
                      <button
                        class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-red-50 text-red-700 transition-colors hover:bg-red-100"
                        title="删除"
                        aria-label="删除"
                        @click="deleteProxy(proxy)"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                          <path stroke="none" d="M0 0h24v24H0z" fill="none" />
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

          <div v-if="pagination.total > 0" class="mt-3">
            <TablePagination
              :total="pagination.total"
              :page="pagination.page"
              :page-size="pagination.page_size"
              @page-change="handlePageChange"
              @page-size-change="handlePageSizeChange"
            />
          </div>
        </div>
      </div>
    </div>

    <ProxyDialog
      v-model="showEditProxyDialog"
      :server-id="props.serverId"
      :proxy="editingProxy"
      @success="handleProxyUpdated"
    />

    <ProxyDialog
      v-model="showAddProxyDialog"
      :server-id="props.serverId"
      @success="handleProxyAdded"
    />
  </Teleport>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { proxyApi } from '@/api/proxies'
import { groupApi } from '@/api/groups'
import { useModal } from '@/composables/useModal'
import TableSearch from '@/components/TableSearch.vue'
import TablePagination from '@/components/TablePagination.vue'
import ProxyDialog from '@/components/ProxyDialog.vue'
import AppSelect from '@/components/AppSelect.vue'

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
  }
})

const emit = defineEmits(['update:modelValue', 'success'])

const dialogVisible = ref(false)
const loading = ref(false)
const generatingDefaults = ref(false)
const proxies = ref([])
const showEditProxyDialog = ref(false)
const showAddProxyDialog = ref(false)
const editingProxy = ref(null)

const filters = reactive({
  search: '',
  status: ''
})

const pagination = reactive({
  page: 1,
  page_size: 10,
  total: 0
})

watch(() => props.modelValue, async (value) => {
  dialogVisible.value = value
  if (value) {
    pagination.page = 1
    await loadData(1)
  }
})

watch(dialogVisible, (value) => {
  emit('update:modelValue', value)
  if (!value) {
    resetState()
  }
})

watch(() => props.groupName, async () => {
  if (dialogVisible.value) {
    pagination.page = 1
    await loadData(1)
  }
})

const closeDialog = () => {
  dialogVisible.value = false
}

useModal(dialogVisible, closeDialog)

const loadData = async (page = 1) => {
  if (!props.serverId || !props.groupName) {
    proxies.value = []
    pagination.total = 0
    return
  }

  loading.value = true
  try {
    const response = await proxyApi.getProxies({
      frps_server_id: props.serverId,
      group_name: props.groupName,
      status_filter: filters.status || undefined,
      search: filters.search || undefined,
      page,
      page_size: pagination.page_size
    })

    proxies.value = response.items || []
    pagination.page = response.page || page
    pagination.page_size = response.page_size || pagination.page_size
    pagination.total = response.total || 0
  } catch (error) {
    alert('加载分组代理失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  loadData(1)
}

const handleFilterChange = () => {
  pagination.page = 1
  loadData(1)
}

const handlePageChange = (newPage) => {
  loadData(newPage)
}

const handlePageSizeChange = (newPageSize) => {
  pagination.page_size = newPageSize
  pagination.page = 1
  loadData(1)
}

const editProxy = (proxy) => {
  editingProxy.value = proxy
  showEditProxyDialog.value = true
}

const handleProxyUpdated = async () => {
  showEditProxyDialog.value = false
  editingProxy.value = null
  await loadData(pagination.page)
  emit('success')
}

const deleteProxy = async (proxy) => {
  if (!confirm(`确定删除代理 "${proxy.name}" 吗？`)) {
    return
  }

  try {
    await proxyApi.deleteProxy(proxy.id)
    alert('删除成功')
    const isLastItemOnPage = proxies.value.length === 1 && pagination.page > 1
    const targetPage = isLastItemOnPage ? pagination.page - 1 : pagination.page
    await loadData(targetPage)
    emit('success')
  } catch (error) {
    alert('删除失败: ' + error.message)
  }
}

const generateStandardProxies = async () => {
  if (!props.serverId || !props.groupName) {
    return
  }

  generatingDefaults.value = true
  try {
    const result = await groupApi.generateDefaults(props.groupName, props.serverId)
    const msg = [
      result.message || '生成完成',
      '',
      `新建：${result.created ?? 0} 个`,
      `跳过（已存在）：${result.skipped ?? 0} 个`
    ].join('\n')
    alert(msg)
    await loadData(pagination.page)
    emit('success')
  } catch (error) {
    alert('生成标准代理失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    generatingDefaults.value = false
  }
}

const syncFromFrps = async () => {
  loading.value = true
  try {
    const response = await proxyApi.getProxies({
      frps_server_id: props.serverId,
      group_name: props.groupName,
      status_filter: filters.status || undefined,
      search: filters.search || undefined,
      sync_from_frps: true,
      page: 1,
      page_size: pagination.page_size
    })

    proxies.value = response.items || []
    pagination.page = response.page || 1
    pagination.page_size = response.page_size || pagination.page_size
    pagination.total = response.total || 0

    if (response.analysis) {
      const a = response.analysis
      const msg = [
        '同步完成（当前筛选口径）',
        '',
        `数据库代理：${a.total_in_db ?? 0}`,
        `frps 代理：${a.total_in_frps ?? 0}`,
        `状态变化：${a.status_changed?.length || 0}`,
        `仅数据库有：${a.missing_in_frps?.length || 0}`,
        `仅 frps 有：${a.only_in_frps?.length || 0}`
      ].join('\n')
      alert(msg)
    } else {
      alert('同步成功')
    }
    emit('success')
  } catch (error) {
    alert('同步失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const handleProxyAdded = async () => {
  showAddProxyDialog.value = false
  await loadData(pagination.page)
  emit('success')
}

const resetState = () => {
  filters.search = ''
  filters.status = ''
  proxies.value = []
  pagination.page = 1
  pagination.page_size = 10
  pagination.total = 0
  showEditProxyDialog.value = false
  showAddProxyDialog.value = false
  editingProxy.value = null
  generatingDefaults.value = false
}

const handleBackdropClick = () => {
  closeDialog()
}
</script>

<style scoped>
.group-proxies-dialog {
  max-width: min(1200px, 88vw);
  min-height: min(700px, 82vh);
}

.group-proxies-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.group-proxies-table-wrap {
  flex: 1;
  overflow: auto;
}
</style>
