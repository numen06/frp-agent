<template>
  <Teleport to="body">
    <div v-if="dialogVisible" class="modal-backdrop fade show" @click="handleBackdropClick"></div>
    <div class="modal modal-blur fade" :class="{ show: dialogVisible }" tabindex="-1" role="dialog" @click.self="handleBackdropClick">
      <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable group-proxies-dialog" role="document" @click.stop>
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">查看代理 - {{ props.groupName || '-' }}</h5>
            <button type="button" class="btn-close" @click="closeDialog" aria-label="关闭">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M18 6l-12 12" />
                <path d="M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="modal-body group-proxies-body">
            <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
              <div class="d-flex gap-2 align-items-center flex-wrap">
                <div style="width: 250px;">
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
              <div class="d-flex gap-2">
                <button class="inline-flex items-center justify-center gap-2 rounded-lg bg-green-600 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50" @click="showAddProxyDialog = true">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                    <path d="M12 5l0 14" />
                    <path d="M5 12l14 0" />
                  </svg>
                  添加
                </button>
                <button class="inline-flex items-center justify-center gap-2 rounded-lg bg-green-600 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50" @click="syncFromFrps" :disabled="loading">
                  <span v-if="loading" class="spinner-border spinner-border-sm me-2" role="status"></span>
                  <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                    <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
                    <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4" />
                  </svg>
                  同步
                </button>
                <button class="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50" @click="loadData(pagination.page)" :disabled="loading">
                  <span v-if="loading" class="spinner-border spinner-border-sm me-2" role="status"></span>
                  <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                    <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
                    <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4" />
                  </svg>
                  刷新
                </button>
              </div>
            </div>

            <div class="overflow-x-auto group-proxies-table-wrap">
              <table class="w-full border-collapse text-left text-sm text-gray-700">
                <thead>
                  <tr>
                    <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">代理名称</th>
                    <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">类型</th>
                    <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">本地IP</th>
                    <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">本地端口</th>
                    <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">远程端口</th>
                    <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">状态</th>
                    <th class="w-[1%] whitespace-nowrap px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="loading">
                    <td colspan="7" class="text-center py-4">
                      <div class="spinner-border spinner-border-sm" role="status"></div>
                      <span class="ms-2">加载中...</span>
                    </td>
                  </tr>
                  <tr v-else-if="proxies.length === 0">
                    <td colspan="7" class="text-center text-muted py-4">当前分组暂无代理</td>
                  </tr>
                  <tr v-else v-for="proxy in proxies" :key="proxy.id">
                    <td class="px-4 py-3 border-b border-gray-100 align-middle">
                      <div class="text-truncate" :title="proxy.name">{{ proxy.name }}</div>
                    </td>
                    <td class="px-4 py-3 border-b border-gray-100 align-middle">
                      <span class="badge text-bg-secondary">{{ proxy.proxy_type.toUpperCase() }}</span>
                    </td>
                    <td class="px-4 py-3 border-b border-gray-100 align-middle">{{ proxy.local_ip }}</td>
                    <td class="px-4 py-3 border-b border-gray-100 align-middle">{{ proxy.local_port || '-' }}</td>
                    <td class="px-4 py-3 border-b border-gray-100 align-middle">{{ proxy.remote_port || '-' }}</td>
                    <td class="px-4 py-3 border-b border-gray-100 align-middle">
                      <span class="badge" :class="proxy.status === 'online' ? 'text-bg-success' : 'text-bg-danger'">
                        {{ proxy.status === 'online' ? '在线' : '离线' }}
                      </span>
                    </td>
                    <td class="px-4 py-3 border-b border-gray-100 align-middle">
                      <div class="inline-flex items-center gap-2">
                        <button
                          class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gray-100 text-gray-700 transition-colors hover:bg-gray-200"
                          @click="editProxy(proxy)"
                          title="编辑"
                          aria-label="编辑"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                            <path d="M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1" />
                            <path d="M20.385 6.585a2.1 2.1 0 0 0 -2.97 -2.97l-8.415 8.385v3h3l8.385 -8.415z" />
                            <path d="M16 5l3 3" />
                          </svg>
                        </button>
                        <button
                          class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-red-50 text-red-700 transition-colors hover:bg-red-100"
                          @click="deleteProxy(proxy)"
                          title="删除"
                          aria-label="删除"
                        >
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

            <div class="mt-3" v-if="pagination.total > 0">
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
      let msg = `同步完成\n\n`
      msg += `数据库代理: ${a.total_in_db}\n`
      msg += `frps 在线代理: ${a.total_in_frps}\n`
      if (a.missing_in_frps?.length) msg += `\n仅数据库有(${a.missing_in_frps.length}): ${a.missing_in_frps.map(p => p.name).join(', ')}\n`
      if (a.only_in_frps?.length) msg += `\n仅 frps 有(${a.only_in_frps.length}): ${a.only_in_frps.map(p => p.name).join(', ')}\n`
      if (a.status_changed?.length) msg += `\n状态变化(${a.status_changed.length}): ${a.status_changed.map(p => p.name).join(', ')}\n`
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
}

const handleBackdropClick = () => {
  closeDialog()
}
</script>

<style scoped>
.group-proxies-dialog {
  max-width: min(1200px, 88vw);
}

.group-proxies-dialog .modal-content {
  min-height: min(700px, 82vh);
  display: flex;
  flex-direction: column;
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
