<template>
  <div>
    <!-- 服务器选择 --><ServerSelector
      v-model="currentServerId"
      @test="handleTestServer"
    /><!-- 代理列表 --><Card
      ><CardHeader
        ><h3 class="text-base font-semibold text-gray-900">代理列表</h3>
        <div
          class="mobile-actions flex w-full flex-wrap items-center gap-2 md:w-auto"
        >
          <div class="relative" v-if="proxiesStore.selectedCount > 0">
            <ActionMenu
              text="批量操作"
              label="批量操作菜单"
              variant="outline"
              :items="[
                { action: 'detect', label: '批量识别端口' },
                { action: 'config', label: '生成配置' },
              ]"
              @select="
                (action) =>
                  action === 'detect'
                    ? handleBatchDetectPorts()
                    : handleGenerateConfigForSelected()
              "
            />
          </div>
          <div class="relative">
            <ActionMenu
              text="添加"
              label="添加菜单"
              variant="default"
              :disabled="!currentServerId"
              :items="[
                { action: 'add', label: '添加代理' },
                { action: 'import', label: '导入配置' },
              ]"
              @select="
                (action) => {
                  if (action === 'add') showAddProxyDialog = true;
                  else showImportConfigDialog = true;
                }
              "
            />
          </div>
          <Button
            @click="syncFromFrps"
            :disabled="proxiesStore.loading || !currentServerId"
            type="button"
            variant="default"
            size="sm"
            ><span
              v-if="proxiesStore.loading"
              class="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-white/30 border-t-white"
              role="status"
              aria-label="加载中"
            ></span
            ><svg
              v-else
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4 shrink-0"
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
            同步 </Button
          ><Button
            @click="refreshProxies"
            :disabled="proxiesStore.loading"
            type="button"
            variant="default"
            size="sm"
            ><span
              v-if="proxiesStore.loading"
              class="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-white/30 border-t-white"
              role="status"
              aria-label="加载中"
            ></span
            ><svg
              v-else
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4 shrink-0"
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
            刷新 </Button
          ><Button
            @click="handleCleanDuplicates"
            :disabled="proxiesStore.loading || !currentServerId"
            title="清理同一服务器下同名重复代理"
            type="button"
            variant="outline"
            size="sm"
            aria-label="清理同一服务器下同名重复代理"
          >
            清理重复
          </Button>
        </div></CardHeader
      ><!-- 搜索和过滤区域 -->
      <div class="border-b border-gray-200 p-3 md:p-5">
        <div
          class="flex flex-col gap-2 md:flex-row md:flex-wrap md:items-center"
        >
          <SearchField
            class="w-full md:max-w-[250px]"
            v-model="proxiesStore.filters.search"
            placeholder="搜索代理名称或分组..."
            :debounce="300"
            @search="handleSearch"
          /><ResourceCombobox
            :scope-key="currentServerId"
            v-model="proxiesStore.filters.group"
            label="全部分组"
            :fetch-options="
              (params) => groupApi.getGroupsList(currentServerId, params)
            "
            :resolve-option="(value) => value"
            allow-clear
            clear-label="全部分组"
            @select="handleFilterChange"
          /><Select
            v-model="proxiesStore.filters.status"
            @update:model-value="handleFilterChange"
            ><SelectTrigger class="w-full md:w-auto" aria-label="全部状态"
              ><SelectValue placeholder="全部状态"></SelectValue></SelectTrigger
            ><SelectContent
              ><SelectItem :value="null">全部状态</SelectItem
              ><SelectItem value="online">在线</SelectItem
              ><SelectItem value="offline">离线</SelectItem></SelectContent
            ></Select
          >
        </div>
      </div>
      <div v-if="hasFilters" class="px-4 py-2">
        <Button type="button" variant="outline" size="sm" @click="clearFilters"
          >清除筛选</Button
        >
      </div>
      <div
        v-if="proxiesStore.error"
        role="alert"
        class="flex flex-wrap items-center justify-between gap-3 border-b border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive"
      >
        <p>
          代理列表读取失败：{{ proxiesStore.error }}。{{
            proxiesStore.proxies.length
              ? "下方保留上次数据。"
              : "当前未能取得数据，并非没有代理。"
          }}
        </p>
        <Button type="button" variant="outline" @click="loadData()"
          >重试读取代理</Button
        >
      </div>
      <!-- 桌面端批量操作工具栏 -->
      <div
        v-if="proxiesStore.selectedCount > 0"
        class="hidden border-b border-gray-200 bg-blue-50 p-5 md:block"
      >
        <div
          class="rounded-lg border border-blue-200 bg-blue-50/80 px-4 py-3 text-sm text-blue-900"
        >
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="font-semibold text-blue-950">
              已选择 {{ proxiesStore.selectedCount }} 个代理
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <ResourceCombobox
                :scope-key="currentServerId"
                v-model="bulkGroupName"
                label="选择分组"
                :fetch-options="
                  (params) => groupApi.getGroupsList(currentServerId, params)
                "
                :resolve-option="(value) => value"
                allow-clear
                clear-label="选择分组"
              /><Button
                @click="handleBulkAssignGroup"
                type="button"
                variant="default"
                size="sm"
                >分配到分组</Button
              ><Button
                @click="handleGenerateConfigForSelected"
                type="button"
                variant="default"
                size="sm"
                >生成配置</Button
              ><Button
                @click="proxiesStore.clearSelection()"
                type="button"
                variant="outline"
                size="sm"
                >取消选择</Button
              >
            </div>
          </div>
        </div>
      </div>
      <!-- 桌面端表格 -->
      <div class="hidden overflow-x-auto md:block">
        <Table class="w-full text-left"
          ><TableHeader
            ><TableRow
              ><TableHead
                ><Checkbox
                  class="w-4 m-0 align-middle"
                  :model-value="
                    proxiesStore.selectedCount ===
                      proxiesStore.proxies.length &&
                    proxiesStore.proxies.length > 0
                  "
                  @update:model-value="handleSelectAll"
                  aria-label="选择记录"
                ></Checkbox></TableHead
              ><TableHead>代理名称</TableHead><TableHead>分组</TableHead
              ><TableHead>类型</TableHead><TableHead>本地IP</TableHead
              ><TableHead>本地端口</TableHead><TableHead>远程端口</TableHead
              ><TableHead>frpc 版本</TableHead
              ><TableHead>FRP 流量快照</TableHead
              ><TableHead
                class="w-[1%] whitespace-nowrap sticky right-0 bg-muted"
                >操作</TableHead
              ></TableRow
            ></TableHeader
          ><TableBody
            ><TableRow v-if="proxiesStore.loading"
              ><TableCell colspan="10" class="text-center"
                ><span
                  class="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600 align-middle"
                  role="status"
                  aria-label="加载中"
                ></span
                ><span class="ml-2 align-middle">加载中...</span></TableCell
              ></TableRow
            ><TableRow v-else-if="proxiesStore.proxies.length === 0"
              ><TableCell colspan="10" class="text-center">
                {{ emptyText }}
              </TableCell></TableRow
            ><TableRow
              v-else
              v-for="proxy in proxiesStore.proxies"
              :key="proxy.id"
              ><TableCell
                ><Checkbox
                  class="w-4 m-0 align-middle"
                  :model-value="proxiesStore.selectedProxyIds.has(proxy.id)"
                  @update:model-value="
                    proxiesStore.toggleProxySelection(proxy.id)
                  "
                  aria-label="选择记录"
                ></Checkbox></TableCell
              ><TableCell
                ><div class="max-w-full truncate" :title="proxy.name">
                  {{ proxy.name }}
                </div>
                <span
                  class="mt-1 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                  :class="
                    proxy.status === 'online'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  "
                >
                  {{ proxy.status === "online" ? "在线" : "离线" }}
                </span></TableCell
              ><TableCell
                ><a
                  v-if="proxy.group_name"
                  href="#"
                  class="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800 no-underline hover:bg-blue-200"
                  @click.prevent="navigateToGroupManage(proxy.group_name)"
                  :title="`点击查看分组 ${proxy.group_name} 的详细信息`"
                >
                  {{ proxy.group_name }} </a
                ><span class="text-sm text-gray-500" v-else>-</span></TableCell
              ><TableCell
                ><span
                  class="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700"
                  >{{ proxy.proxy_type.toUpperCase() }}</span
                ></TableCell
              ><TableCell>{{ proxy.local_ip }}</TableCell
              ><TableCell>{{ proxy.local_port || "-" }}</TableCell
              ><TableCell>{{ proxy.remote_port || "-" }}</TableCell
              ><TableCell>{{ proxy.client_version || "未知" }}</TableCell
              ><TableCell><ProxyTraffic :proxy="proxy" /></TableCell
              ><TableCell
                class="sticky right-0 w-24 min-w-24 max-w-24 bg-background shadow-[-1px_0_0_var(--border)] [&>div]:flex [&>div]:flex-nowrap [&>div]:gap-1"
                ><div class="flex items-center justify-end gap-1">
                  <Button
                    @click="editProxy(proxy)"
                    title="编辑"
                    aria-label="编辑"
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    tooltip="编辑"
                    ><svg
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
                      <path
                        d="M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1"
                      />
                      <path
                        d="M20.385 6.585a2.1 2.1 0 0 0 -2.97 -2.97l-8.415 8.385v3h3l8.385 -8.415z"
                      />
                      <path d="M16 5l3 3" /></svg></Button
                  ><ActionMenu
                    label="代理操作"
                    :items="[
                      ...(isSshCandidateProxy(proxy)
                        ? [{ action: 'upgrade', label: '客户端升级' }]
                        : []),
                      { action: 'delete', label: '删除代理', danger: true },
                    ]"
                    @select="
                      (action) =>
                        action === 'upgrade'
                          ? openClientUpgrade(proxy)
                          : deleteProxy(proxy)
                    "
                  /></div></TableCell></TableRow></TableBody
        ></Table>
      </div>
      <!-- 手机端卡片列表 -->
      <div class="md:hidden">
        <div
          v-if="!proxiesStore.loading && proxiesStore.proxies.length > 0"
          class="flex min-h-14 items-center gap-2 border-b border-gray-100 bg-gray-50 px-3 py-2"
        >
          <Checkbox
            class="w-5 shrink-0"
            :model-value="
              proxiesStore.selectedCount === proxiesStore.proxies.length &&
              proxiesStore.proxies.length > 0
            "
            @update:model-value="handleSelectAll"
            aria-label="选择记录"
          ></Checkbox
          ><span class="text-xs text-gray-600"
            >全选本页（{{ proxiesStore.proxies.length }}）</span
          >
        </div>
        <div
          v-if="proxiesStore.loading"
          class="px-3 py-8 text-center text-sm text-gray-600"
        >
          <span
            class="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600 align-middle"
            role="status"
            aria-label="加载中"
          ></span
          ><span class="ml-2 align-middle">加载中...</span>
        </div>
        <div
          v-else-if="proxiesStore.proxies.length === 0"
          class="px-3 py-8 text-center text-sm text-gray-500"
        >
          {{ emptyText }}
        </div>
        <div v-else class="grid gap-3 p-3">
          <ProxyMobileCard
            v-for="proxy in proxiesStore.proxies"
            :key="proxy.id"
            :proxy="proxy"
            selectable
            group-link
            :selected="proxiesStore.selectedProxyIds.has(proxy.id)"
            :can-upgrade="isSshCandidateProxy(proxy)"
            @toggle="proxiesStore.toggleProxySelection(proxy.id)"
            @group="navigateToGroupManage"
            @edit="editProxy(proxy)"
            @upgrade="openClientUpgrade(proxy)"
            @delete="deleteProxy(proxy)"
          />
        </div>
      </div>
      <!-- 分页 -->
      <div
        class="border-t border-gray-200 px-3 py-3 md:px-5 md:py-3.5"
        :class="{ 'pb-44 md:pb-3.5': proxiesStore.selectedCount > 0 }"
        v-if="proxiesStore.pagination.total > 0"
      >
        <TablePagination
          :total="proxiesStore.pagination.total"
          :page="proxiesStore.pagination.page"
          :page-size="proxiesStore.pagination.page_size"
          @page-change="handlePageChange"
          @page-size-change="handlePageSizeChange"
        /></div></Card
    ><!-- 手机端 sticky 批量操作条 -->
    <div
      v-if="proxiesStore.selectedCount > 0"
      class="fixed inset-x-0 bottom-0 z-40 border-t border-blue-200 bg-blue-50 px-3 py-3 shadow-[0_-4px_12px_rgba(0,0,0,0.08)] md:hidden"
    >
      <div class="mx-auto max-w-7xl">
        <div class="mb-2 text-sm font-semibold text-blue-950">
          已选择 {{ proxiesStore.selectedCount }} 个代理
        </div>
        <div class="flex flex-col gap-2">
          <ResourceCombobox
            :scope-key="currentServerId"
            v-model="bulkGroupName"
            label="选择分组"
            :fetch-options="
              (params) => groupApi.getGroupsList(currentServerId, params)
            "
            :resolve-option="(value) => value"
            allow-clear
            clear-label="选择分组"
          />
          <div class="grid grid-cols-2 gap-2">
            <Button
              @click="handleBulkAssignGroup"
              type="button"
              variant="default"
              size="sm"
              >分配到分组</Button
            ><Button
              @click="handleGenerateConfigForSelected"
              type="button"
              variant="default"
              size="sm"
              >生成配置</Button
            >
          </div>
          <Button
            class="w-full"
            @click="proxiesStore.clearSelection()"
            type="button"
            variant="outline"
            size="sm"
            >取消选择</Button
          >
        </div>
      </div>
    </div>
    <!-- 视口安全下拉菜单 --><!-- 添加代理对话框 --><ProxyDialog
      v-model="showAddProxyDialog"
      :server-id="currentServerId"
      @success="handleProxySuccess"
    /><!-- 编辑代理对话框 --><ProxyDialog
      v-model="showEditProxyDialog"
      :server-id="currentServerId"
      :proxy="editingProxy"
      @success="handleProxySuccess"
    /><!-- 导入配置对话框 --><ImportConfigDialog
      v-model="showImportConfigDialog"
      :server-id="currentServerId"
      @success="handleImportSuccess"
    /><!-- 生成配置对话框 --><ConfigGenerateDialog
      v-model="showConfigDialog"
      :server-id="currentServerId"
      :group-name="configGroupName"
      :selected-proxies="selectedProxiesList"
    /><ProxyClientUpgradeDialog
      v-model="showClientUpgradeDialog"
      :proxy="upgradeProxy"
      :server="currentServer"
      @upgraded="loadData"
    />
  </div>
</template>

<script setup>
import { CardHeader } from "@/components/ui/card";
import ActionMenu from "@/components/ActionMenu.vue";
import { Table } from "@/components/ui/table";
import { TableBody } from "@/components/ui/table";
import { TableCell } from "@/components/ui/table";
import { TableHeader } from "@/components/ui/table";
import { TableRow } from "@/components/ui/table";
import { TableHead } from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Select } from "@/components/ui/select";
import { SelectContent } from "@/components/ui/select";
import { SelectItem } from "@/components/ui/select";
import { SelectTrigger } from "@/components/ui/select";
import { SelectValue } from "@/components/ui/select";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { notify, confirmAction } from "@/composables/useFeedback";
import ProxyTraffic from "@/components/ProxyTraffic.vue";
import ProxyMobileCard from "@/components/ProxyMobileCard.vue";
import ResourceCombobox from "@/components/ResourceCombobox.vue";
import { ref, computed, onMounted, watch, nextTick } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useServersStore } from "@/stores/servers";
import { useProxiesStore } from "@/stores/proxies";
import { useRefresh } from "@/composables/useRefresh";
import { groupApi } from "@/api/groups";
import { proxyApi } from "@/api/proxies";
import ProxyDialog from "@/components/ProxyDialog.vue";
import ImportConfigDialog from "@/components/ImportConfigDialog.vue";
import ConfigGenerateDialog from "@/components/ConfigGenerateDialog.vue";
import TablePagination from "@/components/TablePagination.vue";
import SearchField from "@/components/SearchField.vue";
import ServerSelector from "@/components/ServerSelector.vue";
import ProxyClientUpgradeDialog from "@/components/ProxyClientUpgradeDialog.vue";
import { isSshCandidateProxy } from "@/utils/sshCandidate";

const route = useRoute();
const router = useRouter();
const serversStore = useServersStore();
const proxiesStore = useProxiesStore();
const { triggerRefresh } = useRefresh();

// 下拉菜单

const currentServerId = ref(null);
const hasFilters = computed(() =>
  Boolean(
    proxiesStore.filters.group ||
    proxiesStore.filters.status ||
    proxiesStore.filters.search,
  ),
);
const emptyText = computed(() =>
  proxiesStore.error
    ? "代理数据暂时无法显示，请重试。"
    : !currentServerId.value
      ? "请先选择服务器"
      : hasFilters.value
        ? "没有符合当前筛选条件的代理，请清除筛选后重试。"
        : "当前服务器暂无代理数据",
);
function clearFilters() {
  proxiesStore.setFilters({ group: "", status: "", search: "" });
  handleFilterChange();
}
const showAddProxyDialog = ref(false);
const showEditProxyDialog = ref(false);
const editingProxy = ref(null);
const showImportConfigDialog = ref(false);
const showConfigDialog = ref(false);
const configGroupName = ref("");
const bulkGroupName = ref("");
const groupOptions = ref([]);
const showClientUpgradeDialog = ref(false);
const upgradeProxy = ref(null);

const currentServer = computed(
  () =>
    serversStore.servers.find((s) => s.id === currentServerId.value) ||
    serversStore.currentServer,
);

const openClientUpgrade = (proxy) => {
  upgradeProxy.value = proxy;
  showClientUpgradeDialog.value = true;
};

// 加载分组列表
const loadGroupOptions = async () => {
  groupOptions.value = [];
};

onMounted(async () => {
  // ServerSelector 组件会自动加载服务器列表并设置默认值
  // 这里只需要等待服务器列表加载完成
  try {
    if (serversStore.servers.length === 0) {
      await serversStore.loadServers();
    }
    // 如果 ServerSelector 设置了值，watch 会自动触发 loadData
  } catch (error) {
    console.error("Load servers error:", error);
  }
});

watch(currentServerId, async (newId, oldId) => {
  if (newId) {
    if (oldId !== undefined && newId !== oldId) {
      proxiesStore.clearSelection();
      proxiesStore.setPagination({ page: 1 });
      if (oldId) proxiesStore.setFilters({ group: "" });
    }
    await loadGroupOptions();
    await loadData();
  } else {
    groupOptions.value = [];
    proxiesStore.clearSelection();
  }
});

// 处理路由查询参数，用于从分组管理页面跳转过来时自动过滤
watch(
  () => route.query.group,
  (groupName) => {
    if (groupName) {
      proxiesStore.setFilters({ group: groupName });
      proxiesStore.setPagination({ page: 1 });
      proxiesStore.clearSelection();
      if (currentServerId.value) {
        loadData(1);
      }
    }
  },
  { immediate: true },
);

const loadData = async (page = 1) => {
  if (!currentServerId.value) return;

  try {
    await proxiesStore.loadProxies(currentServerId.value, {
      page,
      page_size: proxiesStore.pagination.page_size,
      group_name: proxiesStore.filters.group || undefined,
      status_filter: proxiesStore.filters.status || undefined,
      search: proxiesStore.filters.search || undefined,
    });
  } catch (error) {
    console.error("Load data error:", error);
  }
};

const handleFilterChange = () => {
  proxiesStore.clearSelection();
  proxiesStore.setPagination({ page: 1 });
  loadData(1);
};

const handleSearch = () => {
  proxiesStore.clearSelection();
  proxiesStore.setPagination({ page: 1 });
  loadData(1);
};

const handlePageChange = (newPage) => {
  proxiesStore.clearSelection();
  loadData(newPage);
};

const handlePageSizeChange = (newPageSize) => {
  proxiesStore.clearSelection();
  proxiesStore.setPagination({ page_size: newPageSize, page: 1 });
  loadData(1);
};

const handleSelectAll = (checked) => {
  if (checked) {
    proxiesStore.toggleSelectAll(proxiesStore.proxies.map((p) => p.id));
  } else {
    proxiesStore.clearSelection();
  }
};

const refreshProxies = async () => {
  await loadData();
};

const handleCleanDuplicates = async () => {
  if (!currentServerId.value) return;
  if (
    !(await confirmAction(
      "确定要清理当前服务器下的重复代理吗？同名代理只保留最新的一条。",
    ))
  )
    return;
  try {
    const res = await proxyApi.cleanDuplicates(currentServerId.value);
    notify(res.message || "清理完成");
    await loadData();
  } catch (error) {
    notify("清理失败: " + (error.message || "未知错误"));
  }
};

const syncFromFrps = async () => {
  if (!currentServerId.value) return;

  try {
    await proxiesStore.loadProxies(currentServerId.value, {
      page: 1,
      page_size: proxiesStore.pagination.page_size,
      syncFromFrps: true, // 启用同步
      group_name: proxiesStore.filters.group || undefined,
      status_filter: proxiesStore.filters.status || undefined,
      search: proxiesStore.filters.search || undefined,
    });
    // 同步完成后触发 Dashboard 刷新
    triggerRefresh();
    notify("同步完成，统计数据已更新");
  } catch (error) {
    console.error("同步失败:", error);
    notify("同步失败: " + (error.message || "未知错误"));
  }
};

const handleTestServer = async () => {
  notify("连接测试成功");
  serversStore.markRefreshNeeded();
  await serversStore.loadServers();
};

const handleBatchDetectPorts = async () => {
  if (proxiesStore.selectedCount === 0) {
    notify("请先选择要识别的代理");
    return;
  }

  try {
    await proxiesStore.batchDetectPorts(
      Array.from(proxiesStore.selectedProxyIds),
    );
    notify("批量识别端口成功");
    await loadData();
  } catch (error) {
    notify("批量识别端口失败: " + error.message);
  }
};

const selectedProxiesList = computed(() => {
  return proxiesStore.proxies.filter((p) =>
    proxiesStore.selectedProxyIds.has(p.id),
  );
});

const handleBulkAssignGroup = async () => {
  if (!bulkGroupName.value) {
    notify("请选择目标分组");
    return;
  }

  if (proxiesStore.selectedCount === 0) {
    notify("请先选择要分配的代理");
    return;
  }

  try {
    await proxiesStore.bulkUpdateGroup(
      Array.from(proxiesStore.selectedProxyIds),
      bulkGroupName.value,
    );
    notify("批量分配分组成功");
    await loadGroupOptions();
    await loadData();
    proxiesStore.clearSelection();
    bulkGroupName.value = "";
  } catch (error) {
    notify("批量分配分组失败: " + error.message);
  }
};

const handleGenerateConfigForSelected = () => {
  if (proxiesStore.selectedCount === 0) {
    notify("请先选择要生成配置的代理");
    return;
  }

  configGroupName.value = "";
  showConfigDialog.value = true;
};

const editProxy = (proxy) => {
  editingProxy.value = proxy;
  showEditProxyDialog.value = true;
};

const deleteProxy = async (proxy) => {
  if (!(await confirmAction(`确定要删除代理 "${proxy.name}" 吗？`))) {
    return;
  }

  try {
    await proxiesStore.deleteProxy(proxy.id);
    notify("删除成功");
    await loadData();
  } catch (error) {
    notify("删除失败: " + error.message);
  }
};

const handleProxySuccess = () => {
  showAddProxyDialog.value = false;
  showEditProxyDialog.value = false;
  editingProxy.value = null;
  loadGroupOptions();
  loadData();
};

const handleImportSuccess = () => {
  loadGroupOptions();
  loadData();
};

const navigateToGroupManage = (groupName) => {
  if (!currentServerId.value) {
    notify("请先选择服务器");
    return;
  }

  // 跳转到分组管理页面，并传递服务器ID和分组名称
  router.push({
    path: "/groups",
    query: {
      server_id: currentServerId.value,
      group: groupName,
    },
  });
};
</script>
