<template>
  <div>
    <!-- 服务器选择 -->
    <ServerSelector 
      v-model="currentServerId" 
      @change="handleServerChange"
      @test="handleTestServer"
    />

    <!-- 代理列表 -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">代理列表</h3>
        <div class="card-actions">
          <div class="d-flex gap-2">
            <div class="dropdown" v-if="proxiesStore.selectedCount > 0">
              <button 
                ref="batchActionsDropdown.triggerRef"
                class="btn btn-warning btn-sm dropdown-toggle" 
                @click.prevent="batchActionsDropdown.toggle()"
                :aria-expanded="batchActionsDropdown.isOpen.value"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="icon me-1" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                  <path d="M4 10a2 2 0 1 0 4 0a2 2 0 0 0 -4 0" />
                  <path d="M6 4v4" />
                  <path d="M6 12v8" />
                  <path d="M10 16a2 2 0 1 0 4 0a2 2 0 0 0 -4 0" />
                  <path d="M12 4v10" />
                  <path d="M12 18v2" />
                  <path d="M16 7a2 2 0 1 0 4 0a2 2 0 0 0 -4 0" />
                  <path d="M18 4v1" />
                  <path d="M18 9v11" />
                </svg>
                批量操作
              </button>
              <div 
                ref="batchActionsDropdown.dropdownRef"
                class="dropdown-menu"
                :class="{ show: batchActionsDropdown.isOpen.value }"
                @click.stop
              >
                <a class="dropdown-item" href="#" @click.prevent="handleBatchDetectPorts(); batchActionsDropdown.close()">
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon dropdown-item-icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                    <path d="M10 10m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0" />
                    <path d="M21 21l-6 -6" />
                  </svg>
                  批量识别端口
                </a>
                <a class="dropdown-item" href="#" @click.prevent="handleGenerateConfigForSelected(); batchActionsDropdown.close()">
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon dropdown-item-icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                    <path d="M14 3v4a1 1 0 0 0 1 1h4" />
                    <path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z" />
                  </svg>
                  生成配置
                </a>
              </div>
            </div>
            <div class="dropdown">
              <button 
                ref="addActionsDropdown.triggerRef"
                class="btn btn-success btn-sm dropdown-toggle" 
                @click.prevent="addActionsDropdown.toggle()"
                :aria-expanded="addActionsDropdown.isOpen.value"
                :disabled="!currentServerId"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="icon me-1" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                  <path d="M12 5l0 14" />
                  <path d="M5 12l14 0" />
                </svg>
                添加
              </button>
              <div 
                ref="addActionsDropdown.dropdownRef"
                class="dropdown-menu"
                :class="{ show: addActionsDropdown.isOpen.value }"
                @click.stop
              >
                <a class="dropdown-item" href="#" @click.prevent="showAddProxyDialog = true; addActionsDropdown.close()" :class="{ disabled: !currentServerId }">
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon dropdown-item-icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                    <path d="M12 5l0 14" />
                    <path d="M5 12l14 0" />
                  </svg>
                  添加代理
                </a>
                <a class="dropdown-item" href="#" @click.prevent="showImportConfigDialog = true; addActionsDropdown.close()" :class="{ disabled: !currentServerId }">
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon dropdown-item-icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                    <path d="M14 3v4a1 1 0 0 0 1 1h4" />
                    <path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z" />
                    <path d="M12 11v6" />
                    <path d="M9 14l3 -3l3 3" />
                  </svg>
                  导入配置
                </a>
              </div>
            </div>
            <button class="btn btn-success btn-sm" @click="syncFromFrps" :disabled="proxiesStore.loading || !currentServerId">
              <span v-if="proxiesStore.loading" class="spinner-border spinner-border-sm me-2" role="status"></span>
              <svg v-else xmlns="http://www.w3.org/2000/svg" class="icon me-1" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
                <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4" />
              </svg>
              同步
            </button>
            <button class="btn btn-primary btn-sm" @click="refreshProxies" :disabled="proxiesStore.loading">
              <span v-if="proxiesStore.loading" class="spinner-border spinner-border-sm me-2" role="status"></span>
              <svg v-else xmlns="http://www.w3.org/2000/svg" class="icon me-1" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
                <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4" />
              </svg>
              刷新
            </button>
          </div>
        </div>
      </div>
      <!-- 搜索和过滤区域 -->
      <div class="card-body border-bottom">
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
          <div class="d-flex gap-2 flex-wrap">
            <div style="width: 250px;">
              <TableSearch
                v-model="proxiesStore.filters.search"
                placeholder="搜索代理名称或分组..."
                @search="handleSearch"
              />
            </div>
            <select class="form-select form-select-sm" v-model="proxiesStore.filters.group" @change="handleFilterChange" style="width: auto;">
              <option value="">全部分组</option>
              <option v-for="group in groupOptions" :key="group" :value="group">{{ group }}</option>
            </select>
            <select class="form-select form-select-sm" v-model="proxiesStore.filters.status" @change="handleFilterChange" style="width: auto;">
              <option value="">全部状态</option>
              <option value="online">在线</option>
              <option value="offline">离线</option>
            </select>
          </div>
        </div>
      </div>
      <!-- 批量操作工具栏 -->
      <div v-if="proxiesStore.selectedCount > 0" class="card-body border-bottom">
        <div class="alert alert-info mb-0">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <div class="fw-bold">已选择 {{ proxiesStore.selectedCount }} 个代理</div>
            <div class="d-flex gap-2 flex-wrap">
              <select class="form-select form-select-sm" v-model="bulkGroupName">
                <option value="">选择目标分组...</option>
                <option v-for="group in groupOptions" :key="group" :value="group">{{ group }}</option>
              </select>
              <button class="btn btn-primary btn-sm" @click="handleBulkAssignGroup">分配到分组</button>
              <button class="btn btn-success btn-sm" @click="handleGenerateConfigForSelected">生成配置</button>
              <button class="btn btn-secondary btn-sm" @click="proxiesStore.clearSelection()">取消选择</button>
            </div>
          </div>
        </div>
      </div>
      <!-- 表格区域 -->
      <div class="table-responsive">
        <table class="table table-vcenter card-table w-100">
            <thead>
              <tr>
                <th>
                  <input class="form-check-input m-0 align-middle" type="checkbox" 
                    :checked="proxiesStore.selectedCount === proxiesStore.proxies.length && proxiesStore.proxies.length > 0"
                    @change="handleSelectAll"
                  />
                </th>
                <th>代理名称</th>
                <th>分组</th>
                <th>类型</th>
                <th>本地IP</th>
                <th>本地端口</th>
                <th>远程端口</th>
                <th>状态</th>
                <th class="w-1">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="proxiesStore.loading">
                <td colspan="9" class="text-center py-4">
                  <div class="spinner-border spinner-border-sm" role="status"></div>
                  <span class="ms-2">加载中...</span>
                </td>
              </tr>
              <tr v-else-if="proxiesStore.proxies.length === 0">
                <td colspan="9" class="text-center text-muted py-4">
                  暂无代理数据，请先添加代理或导入配置
                </td>
              </tr>
              <tr v-else v-for="proxy in proxiesStore.proxies" :key="proxy.id">
                <td>
                  <input class="form-check-input m-0 align-middle" type="checkbox" 
                    :checked="proxiesStore.selectedProxyIds.has(proxy.id)"
                    @change="proxiesStore.toggleProxySelection(proxy.id)"
                  />
                </td>
                <td>
                  <div class="text-truncate" :title="proxy.name">{{ proxy.name }}</div>
                </td>
                <td>
                  <span class="badge text-bg-primary" v-if="proxy.group_name">{{ proxy.group_name }}</span>
                  <span class="text-muted" v-else>-</span>
                </td>
                <td>
                  <span class="badge text-bg-secondary">{{ proxy.proxy_type.toUpperCase() }}</span>
                </td>
                <td>{{ proxy.local_ip }}</td>
                <td>{{ proxy.local_port || '-' }}</td>
                <td>{{ proxy.remote_port || '-' }}</td>
                <td>
                  <span class="badge" :class="proxy.status === 'online' ? 'text-bg-success' : 'text-bg-danger'">
                    {{ proxy.status === 'online' ? '在线' : '离线' }}
                  </span>
                </td>
                <td>
                  <div class="dropdown">
                    <button 
                      :ref="el => { if (el) getProxyDropdown(proxy.id).triggerRef.value = el }"
                      class="btn btn-sm dropdown-toggle" 
                      @click.prevent="getProxyDropdown(proxy.id).toggle()"
                      :aria-expanded="getProxyDropdown(proxy.id).isOpen.value"
                    >
                      操作
                    </button>
                    <div 
                      :ref="el => { if (el) getProxyDropdown(proxy.id).dropdownRef.value = el }"
                      class="dropdown-menu"
                      :class="{ show: getProxyDropdown(proxy.id).isOpen.value }"
                      @click.stop
                    >
                      <a class="dropdown-item" href="#" @click.prevent="editProxy(proxy); getProxyDropdown(proxy.id).close()">
                        <svg xmlns="http://www.w3.org/2000/svg" class="icon dropdown-item-icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                          <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                          <path d="M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1" />
                          <path d="M20.385 6.585a2.1 2.1 0 0 0 -2.97 -2.97l-8.415 8.385v3h3l8.385 -8.415z" />
                          <path d="M16 5l3 3" />
                        </svg>
                        编辑
                      </a>
                      <div class="dropdown-divider"></div>
                      <a class="dropdown-item text-danger" href="#" @click.prevent="deleteProxy(proxy); getProxyDropdown(proxy.id).close()">
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
      <div class="card-footer" v-if="proxiesStore.pagination.total > 0">
        <TablePagination
          :total="proxiesStore.pagination.total"
          :page="proxiesStore.pagination.page"
          :page-size="proxiesStore.pagination.page_size"
          @page-change="handlePageChange"
          @page-size-change="handlePageSizeChange"
        />
      </div>
    </div>


    <!-- 添加代理对话框 -->
    <ProxyDialog
      v-model="showAddProxyDialog"
      :server-id="currentServerId"
      @success="handleProxySuccess"
    />

    <!-- 编辑代理对话框 -->
    <ProxyDialog
      v-model="showEditProxyDialog"
      :server-id="currentServerId"
      :proxy="editingProxy"
      @success="handleProxySuccess"
    />

    <!-- 导入配置对话框 -->
    <ImportConfigDialog
      v-model="showImportConfigDialog"
      :server-id="currentServerId"
      @success="handleImportSuccess"
    />

    <!-- 生成配置对话框 -->
    <ConfigGenerateDialog
      v-model="showConfigDialog"
      :server-id="currentServerId"
      :group-name="configGroupName"
      :selected-proxies="selectedProxiesList"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useServersStore } from '@/stores/servers'
import { useProxiesStore } from '@/stores/proxies'
import { useRefresh } from '@/composables/useRefresh'
import { useDropdown } from '@/composables/useDropdown'
import { groupApi } from '@/api/groups'
import ProxyDialog from '@/components/ProxyDialog.vue'
import ImportConfigDialog from '@/components/ImportConfigDialog.vue'
import ConfigGenerateDialog from '@/components/ConfigGenerateDialog.vue'
import TablePagination from '@/components/TablePagination.vue'
import TableSearch from '@/components/TableSearch.vue'
import ServerSelector from '@/components/ServerSelector.vue'

const route = useRoute()
const serversStore = useServersStore()
const proxiesStore = useProxiesStore()
const { triggerRefresh } = useRefresh()

// 下拉菜单
const batchActionsDropdown = useDropdown()
const addActionsDropdown = useDropdown()

// 每个代理的下拉菜单（使用 Map 存储）
const proxyDropdowns = new Map()

const getProxyDropdown = (proxyId) => {
  if (!proxyDropdowns.has(proxyId)) {
    proxyDropdowns.set(proxyId, useDropdown())
  }
  return proxyDropdowns.get(proxyId)
}

const currentServerId = ref(null)
const showAddProxyDialog = ref(false)
const showEditProxyDialog = ref(false)
const editingProxy = ref(null)
const showImportConfigDialog = ref(false)
const showConfigDialog = ref(false)
const configGroupName = ref('')
const bulkGroupName = ref('')
const groupOptions = ref([])

// 加载分组列表
const loadGroupOptions = async () => {
  if (!currentServerId.value) {
    groupOptions.value = []
    return
  }
  
  try {
    const response = await groupApi.getGroupsList(currentServerId.value)
    groupOptions.value = response.groups || []
  } catch (error) {
    console.error('加载分组列表失败:', error)
    groupOptions.value = []
  }
}

onMounted(async () => {
  // ServerSelector 组件会自动加载服务器列表并设置默认值
  // 这里只需要等待服务器列表加载完成
  try {
    if (serversStore.servers.length === 0) {
      await serversStore.loadServers()
    }
    // 如果 ServerSelector 设置了值，watch 会自动触发 loadData
  } catch (error) {
    console.error('Load servers error:', error)
  }
})

watch(currentServerId, async (newId) => {
  if (newId) {
    await loadGroupOptions()
    await loadData()
  } else {
    groupOptions.value = []
  }
})

// 处理路由查询参数，用于从分组管理页面跳转过来时自动过滤
watch(() => route.query.group, (groupName) => {
  if (groupName) {
    proxiesStore.setFilters({ group: groupName })
    proxiesStore.setPagination({ page: 1 })
    if (currentServerId.value) {
      loadData(1)
    }
  }
}, { immediate: true })

const loadData = async (page = 1) => {
  if (!currentServerId.value) return
  
  try {
    await proxiesStore.loadProxies(currentServerId.value, {
      page,
      page_size: proxiesStore.pagination.page_size,
      group_name: proxiesStore.filters.group || undefined,
      status_filter: proxiesStore.filters.status || undefined,
      search: proxiesStore.filters.search || undefined
    })
  } catch (error) {
    console.error('Load data error:', error)
  }
}

const handleServerChange = () => {
  loadData()
}

const handleFilterChange = () => {
  // 过滤器变化时，重置到第一页并重新加载
  proxiesStore.setPagination({ page: 1 })
  loadData(1)
}

const handleSearch = () => {
  // 搜索时，重置到第一页并重新加载
  proxiesStore.setPagination({ page: 1 })
  loadData(1)
}

const handlePageChange = (newPage) => {
  loadData(newPage)
}

const handlePageSizeChange = (newPageSize) => {
  proxiesStore.setPagination({ page_size: newPageSize, page: 1 })
  loadData(1)
}

const handleSelectAll = (event) => {
  if (event.target.checked) {
    proxiesStore.toggleSelectAll(proxiesStore.proxies.map(p => p.id))
  } else {
    proxiesStore.clearSelection()
  }
}

const refreshProxies = async () => {
  await loadData()
}

const syncFromFrps = async () => {
  if (!currentServerId.value) return
  
  try {
    await proxiesStore.loadProxies(currentServerId.value, {
      page: 1,
      page_size: proxiesStore.pagination.page_size,
      syncFromFrps: true, // 启用同步
      group_name: proxiesStore.filters.group || undefined,
      status_filter: proxiesStore.filters.status || undefined,
      search: proxiesStore.filters.search || undefined
    })
    // 同步完成后触发 Dashboard 刷新
    triggerRefresh()
    alert('同步完成，统计数据已更新')
  } catch (error) {
    console.error('同步失败:', error)
    alert('同步失败: ' + (error.message || '未知错误'))
  }
}

const handleTestServer = async () => {
  alert('连接测试成功')
  await serversStore.loadServers()
}

const handleBatchDetectPorts = async () => {
  if (proxiesStore.selectedCount === 0) {
    alert('请先选择要识别的代理')
    return
  }
  
  try {
    await proxiesStore.batchDetectPorts(Array.from(proxiesStore.selectedProxyIds))
    alert('批量识别端口成功')
    await loadData()
  } catch (error) {
    alert('批量识别端口失败: ' + error.message)
  }
}

const selectedProxiesList = computed(() => {
  return proxiesStore.proxies.filter(p => 
    proxiesStore.selectedProxyIds.has(p.id)
  )
})

const handleBulkAssignGroup = async () => {
  if (!bulkGroupName.value) {
    alert('请选择目标分组')
    return
  }
  
  if (proxiesStore.selectedCount === 0) {
    alert('请先选择要分配的代理')
    return
  }
  
  try {
    await proxiesStore.bulkUpdateGroup(
      Array.from(proxiesStore.selectedProxyIds),
      bulkGroupName.value
    )
    alert('批量分配分组成功')
    await loadGroupOptions()
    await loadData()
    proxiesStore.clearSelection()
    bulkGroupName.value = ''
  } catch (error) {
    alert('批量分配分组失败: ' + error.message)
  }
}

const handleGenerateConfigForSelected = () => {
  if (proxiesStore.selectedCount === 0) {
    alert('请先选择要生成配置的代理')
    return
  }
  
  configGroupName.value = ''
  showConfigDialog.value = true
}

const editProxy = (proxy) => {
  editingProxy.value = proxy
  showEditProxyDialog.value = true
}

const deleteProxy = async (proxy) => {
  if (!confirm(`确定要删除代理 "${proxy.name}" 吗？`)) {
    return
  }
  
  try {
    await proxiesStore.deleteProxy(proxy.id)
    alert('删除成功')
    await loadData()
  } catch (error) {
    alert('删除失败: ' + error.message)
  }
}

const handleProxySuccess = () => {
  showAddProxyDialog.value = false
  showEditProxyDialog.value = false
  editingProxy.value = null
  loadGroupOptions()
  loadData()
}

const handleImportSuccess = () => {
  loadGroupOptions()
  loadData()
}
</script>

