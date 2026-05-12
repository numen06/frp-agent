<template>
  <div>
    <!-- 服务器选择 -->
    <ServerSelector 
      v-model="currentServerId" 
      @change="handleServerChange"
      @test="handleTestServer"
    />

    <!-- 代理列表 -->
    <div class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <div class="flex flex-wrap items-center justify-between gap-2 border-b border-gray-200 px-5 py-3.5">
        <h3 class="text-base font-semibold text-gray-900">代理列表</h3>
        <div class="flex flex-wrap items-center gap-2">
            <div class="relative" v-if="proxiesStore.selectedCount > 0">
              <button 
                ref="batchActionsDropdown.triggerRef"
                class="inline-flex items-center justify-center gap-2 rounded-lg bg-amber-500 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-amber-600" 
                @click.prevent="batchActionsDropdown.toggle()"
                :aria-expanded="batchActionsDropdown.isOpen.value"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
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
                class="absolute right-0 z-50 mt-2 min-w-[11rem] rounded-lg border border-gray-200 bg-white py-1 shadow-lg"
                :class="batchActionsDropdown.isOpen.value ? 'block' : 'hidden'"
                @click.stop
              >
                <a class="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100" href="#" @click.prevent="handleBatchDetectPorts(); batchActionsDropdown.close()">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                    <path d="M10 10m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0" />
                    <path d="M21 21l-6 -6" />
                  </svg>
                  批量识别端口
                </a>
                <a class="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100" href="#" @click.prevent="handleGenerateConfigForSelected(); batchActionsDropdown.close()">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                    <path d="M14 3v4a1 1 0 0 0 1 1h4" />
                    <path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z" />
                  </svg>
                  生成配置
                </a>
              </div>
            </div>
            <div class="relative">
              <button 
                ref="addActionsDropdown.triggerRef"
                class="inline-flex items-center justify-center gap-2 rounded-lg bg-green-600 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50" 
                @click.prevent="addActionsDropdown.toggle()"
                :aria-expanded="addActionsDropdown.isOpen.value"
                :disabled="!currentServerId"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                  <path d="M12 5l0 14" />
                  <path d="M5 12l14 0" />
                </svg>
                添加
              </button>
              <div 
                ref="addActionsDropdown.dropdownRef"
                class="absolute right-0 z-50 mt-2 min-w-[11rem] rounded-lg border border-gray-200 bg-white py-1 shadow-lg"
                :class="addActionsDropdown.isOpen.value ? 'block' : 'hidden'"
                @click.stop
              >
                <a class="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100" href="#" @click.prevent="showAddProxyDialog = true; addActionsDropdown.close()" :class="{ 'pointer-events-none opacity-50': !currentServerId }">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                    <path d="M12 5l0 14" />
                    <path d="M5 12l14 0" />
                  </svg>
                  添加代理
                </a>
                <a class="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100" href="#" @click.prevent="showImportConfigDialog = true; addActionsDropdown.close()" :class="{ 'pointer-events-none opacity-50': !currentServerId }">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
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
            <button class="inline-flex items-center justify-center gap-2 rounded-lg bg-green-600 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50" @click="syncFromFrps" :disabled="proxiesStore.loading || !currentServerId">
              <span v-if="proxiesStore.loading" class="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-white/30 border-t-white" role="status" aria-label="加载中"></span>
              <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
                <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4" />
              </svg>
              同步
            </button>
            <button class="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50" @click="refreshProxies" :disabled="proxiesStore.loading">
              <span v-if="proxiesStore.loading" class="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-white/30 border-t-white" role="status" aria-label="加载中"></span>
              <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
                <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4" />
              </svg>
              刷新
            </button>
            <button class="inline-flex items-center justify-center gap-2 rounded-lg border border-amber-500 px-2.5 py-1.5 text-xs font-medium text-amber-600 transition-colors hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-50" @click="handleCleanDuplicates" :disabled="proxiesStore.loading || !currentServerId" title="清理同一服务器下同名重复代理">
              清理重复
            </button>
          </div>
        </div>
      <!-- 搜索和过滤区域 -->
      <div class="border-b border-gray-200 p-5">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex flex-wrap items-center gap-2">
            <div style="width: 250px;">
              <TableSearch
                v-model="proxiesStore.filters.search"
                placeholder="搜索代理名称或分组..."
                @search="handleSearch"
              />
            </div>
            <AppSelect class="w-auto" size="sm" v-model="proxiesStore.filters.group" @change="handleFilterChange">
              <option value="">全部分组</option>
              <option v-for="group in groupOptions" :key="group" :value="group">{{ group }}</option>
            </AppSelect>
            <AppSelect class="w-auto" size="sm" v-model="proxiesStore.filters.status" @change="handleFilterChange">
              <option value="">全部状态</option>
              <option value="online">在线</option>
              <option value="offline">离线</option>
            </AppSelect>
          </div>
        </div>
      </div>
      <!-- 批量操作工具栏 -->
      <div v-if="proxiesStore.selectedCount > 0" class="border-b border-gray-200 bg-blue-50 p-5">
        <div class="rounded-lg border border-blue-200 bg-blue-50/80 px-4 py-3 text-sm text-blue-900">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="font-semibold text-blue-950">已选择 {{ proxiesStore.selectedCount }} 个代理</div>
            <div class="flex flex-wrap items-center gap-2">
              <AppSelect class="w-auto" size="sm" v-model="bulkGroupName">
                <option value="">选择目标分组...</option>
                <option v-for="group in groupOptions" :key="group" :value="group">{{ group }}</option>
              </AppSelect>
              <button class="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700" @click="handleBulkAssignGroup">分配到分组</button>
              <button class="inline-flex items-center justify-center gap-2 rounded-lg bg-green-600 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-green-700" @click="handleGenerateConfigForSelected">生成配置</button>
              <button class="inline-flex items-center justify-center gap-2 rounded-lg bg-gray-200 px-2.5 py-1.5 text-xs font-medium text-gray-800 transition-colors hover:bg-gray-300" @click="proxiesStore.clearSelection()">取消选择</button>
            </div>
          </div>
        </div>
      </div>
      <!-- 表格区域 -->
      <div class="overflow-x-auto">
        <table class="w-full border-collapse text-left text-sm text-gray-700">
            <thead>
              <tr>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">
                  <input class="h-4 w-4 rounded border border-gray-300 m-0 align-middle" type="checkbox" 
                    :checked="proxiesStore.selectedCount === proxiesStore.proxies.length && proxiesStore.proxies.length > 0"
                    @change="handleSelectAll"
                  />
                </th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">代理名称</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">分组</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">类型</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">本地IP</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">本地端口</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">远程端口</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">状态</th>
                <th class="w-[1%] whitespace-nowrap px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="proxiesStore.loading">
                <td colspan="9" class="py-4 text-center text-sm text-gray-600">
                  <span class="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600 align-middle" role="status" aria-label="加载中"></span>
                  <span class="ml-2 align-middle">加载中...</span>
                </td>
              </tr>
              <tr v-else-if="proxiesStore.proxies.length === 0">
                <td colspan="9" class="py-4 text-center text-sm text-gray-500">
                  暂无代理数据，请先添加代理或导入配置
                </td>
              </tr>
              <tr v-else v-for="proxy in proxiesStore.proxies" :key="proxy.id">
                <td class="px-4 py-3 border-b border-gray-100 align-middle">
                  <input class="h-4 w-4 rounded border border-gray-300 m-0 align-middle" type="checkbox" 
                    :checked="proxiesStore.selectedProxyIds.has(proxy.id)"
                    @change="proxiesStore.toggleProxySelection(proxy.id)"
                  />
                </td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle">
                  <div class="max-w-full truncate" :title="proxy.name">{{ proxy.name }}</div>
                </td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle">
                  <a 
                    v-if="proxy.group_name" 
                    href="#" 
                    class="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800 no-underline hover:bg-blue-200"
                    @click.prevent="navigateToGroupManage(proxy.group_name)"
                    :title="`点击查看分组 ${proxy.group_name} 的详细信息`"
                  >
                    {{ proxy.group_name }}
                  </a>
                  <span class="text-sm text-gray-500" v-else>-</span>
                </td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle">
                  <span class="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700">{{ proxy.proxy_type.toUpperCase() }}</span>
                </td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle">{{ proxy.local_ip }}</td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle">{{ proxy.local_port || '-' }}</td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle">{{ proxy.remote_port || '-' }}</td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle">
                  <span
                    class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                    :class="proxy.status === 'online' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'"
                  >
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
      <!-- 分页 -->
      <div class="border-t border-gray-200 px-5 py-3.5" v-if="proxiesStore.pagination.total > 0">
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
import { useRoute, useRouter } from 'vue-router'
import { useServersStore } from '@/stores/servers'
import { useProxiesStore } from '@/stores/proxies'
import { useRefresh } from '@/composables/useRefresh'
import { useDropdown } from '@/composables/useDropdown'
import { groupApi } from '@/api/groups'
import { proxyApi } from '@/api/proxies'
import ProxyDialog from '@/components/ProxyDialog.vue'
import ImportConfigDialog from '@/components/ImportConfigDialog.vue'
import ConfigGenerateDialog from '@/components/ConfigGenerateDialog.vue'
import TablePagination from '@/components/TablePagination.vue'
import TableSearch from '@/components/TableSearch.vue'
import AppSelect from '@/components/AppSelect.vue'
import ServerSelector from '@/components/ServerSelector.vue'

const route = useRoute()
const router = useRouter()
const serversStore = useServersStore()
const proxiesStore = useProxiesStore()
const { triggerRefresh } = useRefresh()

// 下拉菜单
const batchActionsDropdown = useDropdown()
const addActionsDropdown = useDropdown()

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

const handleCleanDuplicates = async () => {
  if (!currentServerId.value) return
  if (!confirm('确定要清理当前服务器下的重复代理吗？同名代理只保留最新的一条。')) return
  try {
    const res = await proxyApi.cleanDuplicates(currentServerId.value)
    alert(res.message || '清理完成')
    await loadData()
  } catch (error) {
    alert('清理失败: ' + (error.message || '未知错误'))
  }
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
  serversStore.markRefreshNeeded()
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

const navigateToGroupManage = (groupName) => {
  if (!currentServerId.value) {
    alert('请先选择服务器')
    return
  }
  
  // 跳转到分组管理页面，并传递服务器ID和分组名称
  router.push({
    path: '/groups',
    query: {
      server_id: currentServerId.value,
      group: groupName
    }
  })
}
</script>

