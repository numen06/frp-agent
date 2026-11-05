<template>
  <Dialog
    v-if="dialogVisible"
    :open="true"
    @update:open="
      (open) => {
        if (!open) {
          handleBackdropClick();
        }
      }
    "
    ><DialogContent class="sm:max-w-6xl" :aria-describedby="undefined"
      ><DialogHeader
        ><DialogTitle class="min-w-0 pr-8"
          ><span class="line-clamp-2 break-all">
            查看代理 - {{ props.groupName || "-" }}</span
          ></DialogTitle
        ></DialogHeader
      >
      <div
        data-slot="dialog-body"
        class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
      >
        <div class="mb-3 flex flex-col gap-3">
          <div
            class="flex w-full flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center"
          >
            <div class="w-full min-w-0 sm:max-w-[250px]">
              <SearchField
                v-model="filters.search"
                placeholder="搜索代理名称..."
                label="搜索分组代理"
                @search="handleSearch"
              />
            </div>
            <Select
              v-model="filters.status"
              @update:model-value="handleFilterChange"
              ><SelectTrigger class="w-full sm:w-auto" aria-label="全部状态"
                ><SelectValue
                  placeholder="全部状态"
                ></SelectValue></SelectTrigger
              ><SelectContent
                ><SelectItem :value="null">全部状态</SelectItem
                ><SelectItem value="online">在线</SelectItem
                ><SelectItem value="offline">离线</SelectItem></SelectContent
              ></Select
            >
            <Button
              v-if="hasFilters"
              type="button"
              variant="ghost"
              @click="clearFilters"
              >清除筛选</Button
            >
          </div>
          <div class="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
            <Button
              type="button"
              class="flex-1 sm:flex-none"
              @click="showAddProxyDialog = true"
              variant="default"
              size="sm"
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
                <path d="M12 5l0 14" />
                <path d="M5 12l14 0" />
              </svg>
              添加 </Button
            ><Button
              type="button"
              class="flex-1 sm:flex-none"
              :disabled="loading || generatingDefaults"
              @click="generateStandardProxies"
              variant="outline"
              size="sm"
              ><span
                v-if="generatingDefaults"
                class="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-primary"
                role="status"
                aria-label="加载中"
              /><svg
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
              生成标准代理 </Button
            ><Button
              type="button"
              class="flex-1 sm:flex-none"
              :disabled="loading"
              @click="syncFromFrps"
              variant="outline"
              size="sm"
              ><span
                v-if="loading"
                class="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-primary"
                role="status"
                aria-label="加载中"
              /><svg
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
              同步 </Button
            ><Button
              type="button"
              class="flex-1 sm:flex-none"
              :disabled="loading"
              @click="loadData(pagination.page)"
              variant="outline"
              size="sm"
              ><span
                v-if="loading"
                class="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-primary"
                role="status"
                aria-label="加载中"
              /><svg
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
            </Button>
          </div>
        </div>
        <div
          v-if="loadError"
          role="alert"
          class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-destructive/30 p-3 text-sm text-destructive"
        >
          {{ loadError
          }}<Button
            type="button"
            variant="outline"
            @click="loadData(pagination.page)"
            >重试读取代理</Button
          >
        </div>
        <div
          v-if="!loadError"
          class="group-proxies-table-wrap hidden overflow-x-auto md:block"
        >
          <Table class="w-full text-left"
            ><TableHeader
              ><TableRow
                ><TableHead>代理名称</TableHead><TableHead>类型</TableHead
                ><TableHead>本地IP</TableHead><TableHead>本地端口</TableHead
                ><TableHead>远程端口</TableHead><TableHead>frpc 版本</TableHead
                ><TableHead>FRP 流量快照</TableHead><TableHead>状态</TableHead
                ><TableHead
                  class="w-[1%] whitespace-nowrap sticky right-0 bg-muted"
                  >操作</TableHead
                ></TableRow
              ></TableHeader
            ><TableBody
              ><TableRow v-if="loading"
                ><TableCell colspan="9" class="text-center"
                  ><span
                    class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600 align-middle"
                    role="status"
                    aria-label="加载中"
                  /><span class="ml-2 align-middle text-gray-600"
                    >加载中...</span
                  ></TableCell
                ></TableRow
              ><TableRow v-else-if="proxies.length === 0"
                ><TableCell colspan="9" class="text-center">{{
                  hasFilters
                    ? "当前分组没有符合筛选条件的代理"
                    : "当前分组暂无代理"
                }}</TableCell></TableRow
              ><TableRow v-else v-for="proxy in proxies" :key="proxy.id"
                ><TableCell
                  ><div class="max-w-[200px] truncate" :title="proxy.name">
                    {{ proxy.name }}
                  </div></TableCell
                ><TableCell
                  ><span
                    class="inline-flex rounded-md bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-800"
                    >{{ proxy.proxy_type.toUpperCase() }}</span
                  ></TableCell
                ><TableCell>{{ proxy.local_ip }}</TableCell
                ><TableCell>{{ proxy.local_port || "-" }}</TableCell
                ><TableCell>{{ proxy.remote_port || "-" }}</TableCell
                ><TableCell>{{ proxy.client_version || "未知" }}</TableCell
                ><TableCell><ProxyTraffic :proxy="proxy" /></TableCell
                ><TableCell
                  ><span
                    class="inline-flex rounded-md px-2 py-0.5 text-xs font-medium"
                    :class="
                      proxy.status === 'online'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    "
                  >
                    {{ proxy.status === "online" ? "在线" : "离线" }}
                  </span></TableCell
                ><TableCell
                  class="sticky right-0 w-24 min-w-24 max-w-24 bg-background shadow-[-1px_0_0_var(--border)] [&>div]:flex [&>div]:flex-nowrap [&>div]:gap-1"
                  ><div class="inline-flex items-center gap-2">
                    <Button
                      title="编辑"
                      aria-label="编辑"
                      @click="editProxy(proxy)"
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
                    ><Button
                      class="text-destructive hover:bg-destructive/10"
                      title="删除"
                      aria-label="删除"
                      @click="deleteProxy(proxy)"
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      tooltip="删除"
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
                        <path d="M4 7l16 0" />
                        <path d="M10 11l0 6" />
                        <path d="M14 11l0 6" />
                        <path
                          d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12"
                        />
                        <path
                          d="M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3"
                        /></svg
                    ></Button></div></TableCell></TableRow></TableBody
          ></Table>
        </div>
        <div v-if="!loadError" class="md:hidden">
          <div v-if="loading" class="py-4 text-center text-sm text-gray-600">
            <span
              class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600 align-middle"
              role="status"
              aria-label="加载中"
            /><span class="ml-2 align-middle">加载中...</span>
          </div>
          <p
            v-else-if="proxies.length === 0"
            class="py-8 text-center text-sm text-gray-500"
          >
            {{
              hasFilters ? "当前分组没有符合筛选条件的代理" : "当前分组暂无代理"
            }}
          </p>
          <div v-else class="grid gap-3">
            <ProxyMobileCard
              v-for="proxy in proxies"
              :key="proxy.id"
              :proxy="proxy"
              @edit="editProxy(proxy)"
              @delete="deleteProxy(proxy)"
            />
          </div>
        </div>
        <div v-if="pagination.total > 0 && !loadError" class="mt-3 shrink-0">
          <TablePagination
            :total="pagination.total"
            :page="pagination.page"
            :page-size="pagination.page_size"
            @page-change="handlePageChange"
            @page-size-change="handlePageSizeChange"
          />
        </div></div></DialogContent></Dialog
  ><ProxyDialog
    v-model="showEditProxyDialog"
    :server-id="props.serverId"
    :proxy="editingProxy"
    @success="handleProxyUpdated"
  /><ProxyDialog
    v-model="showAddProxyDialog"
    :server-id="props.serverId"
    :group-name="props.groupName"
    @success="handleProxyAdded"
  />
</template>

<script setup>
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Table } from "@/components/ui/table";
import { TableBody } from "@/components/ui/table";
import { TableCell } from "@/components/ui/table";
import { TableHeader } from "@/components/ui/table";
import { TableRow } from "@/components/ui/table";
import { TableHead } from "@/components/ui/table";
import { Select } from "@/components/ui/select";
import { SelectContent } from "@/components/ui/select";
import { SelectItem } from "@/components/ui/select";
import { SelectTrigger } from "@/components/ui/select";
import { SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { notify, confirmAction } from "@/composables/useFeedback";
import ProxyTraffic from "@/components/ProxyTraffic.vue";
import ProxyMobileCard from "@/components/ProxyMobileCard.vue";
import { computed, onUnmounted, reactive, ref, watch } from "vue";
import { proxyApi } from "@/api/proxies";
import { groupApi } from "@/api/groups";
import SearchField from "@/components/SearchField.vue";
import TablePagination from "@/components/TablePagination.vue";
import ProxyDialog from "@/components/ProxyDialog.vue";

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  serverId: {
    type: Number,
    required: true,
  },
  groupName: {
    type: String,
    default: "",
  },
});

const emit = defineEmits(["update:modelValue", "success"]);

const dialogVisible = ref(false);
const loading = ref(false);
const loadError = ref("");
let requestId = 0;
onUnmounted(() => {
  ++requestId;
});
const generatingDefaults = ref(false);
const proxies = ref([]);
const showEditProxyDialog = ref(false);
const showAddProxyDialog = ref(false);
const editingProxy = ref(null);

const filters = reactive({
  search: "",
  status: "",
});
const hasFilters = computed(() => Boolean(filters.search || filters.status));
function clearFilters() {
  filters.search = filters.status = "";
  loadData(1);
}

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0,
});

watch(
  () => props.modelValue,
  async (value) => {
    dialogVisible.value = value;
    if (value) {
      pagination.page = 1;
      await loadData(1);
    }
  },
);

watch(dialogVisible, (value) => {
  emit("update:modelValue", value);
  if (!value) {
    resetState();
  }
});

watch(
  () => [props.serverId, props.groupName],
  async () => {
    if (dialogVisible.value) {
      filters.search = filters.status = "";
      proxies.value = [];
      pagination.page = 1;
      await loadData(1);
    }
  },
);

const closeDialog = () => {
  dialogVisible.value = false;
};

const loadData = async (page = 1, sync = false) => {
  const request = ++requestId;
  if (!dialogVisible.value || !props.serverId || !props.groupName) {
    proxies.value = [];
    pagination.total = 0;
    return;
  }

  loading.value = true;
  loadError.value = "";
  pagination.page = page;
  try {
    const response = await proxyApi.getProxies({
      frps_server_id: props.serverId,
      group_name: props.groupName,
      status_filter: filters.status || undefined,
      search: filters.search || undefined,
      page,
      page_size: pagination.page_size,
      ...(sync ? { sync_from_frps: true } : {}),
    });
    if (request !== requestId || !dialogVisible.value) return;
    const lastPage = Math.max(
      1,
      Math.ceil(response.total / pagination.page_size),
    );
    if (page > lastPage) return await loadData(lastPage);
    proxies.value = response.items || [];
    pagination.page = response.page || page;
    pagination.page_size = response.page_size || pagination.page_size;
    pagination.total = response.total || 0;
    return response;
  } catch (error) {
    if (request === requestId && dialogVisible.value) {
      loadError.value = "加载分组代理失败: " + error.message;
      proxies.value = [];
    }
  } finally {
    if (request === requestId) loading.value = false;
  }
};

const handleSearch = () => {
  pagination.page = 1;
  loadData(1);
};

const handleFilterChange = () => {
  pagination.page = 1;
  loadData(1);
};

const handlePageChange = (newPage) => {
  loadData(newPage);
};

const handlePageSizeChange = (newPageSize) => {
  pagination.page_size = newPageSize;
  pagination.page = 1;
  loadData(1);
};

const editProxy = (proxy) => {
  editingProxy.value = proxy;
  showEditProxyDialog.value = true;
};

const handleProxyUpdated = async () => {
  showEditProxyDialog.value = false;
  editingProxy.value = null;
  await loadData(pagination.page);
  emit("success");
};

const deleteProxy = async (proxy) => {
  if (!(await confirmAction(`确定删除代理 "${proxy.name}" 吗？`))) {
    return;
  }

  try {
    await proxyApi.deleteProxy(proxy.id);
    notify("删除成功");
    const isLastItemOnPage = proxies.value.length === 1 && pagination.page > 1;
    const targetPage = isLastItemOnPage ? pagination.page - 1 : pagination.page;
    await loadData(targetPage);
    emit("success");
  } catch (error) {
    notify("删除失败: " + error.message);
  }
};

const generateStandardProxies = async () => {
  if (!props.serverId || !props.groupName) {
    return;
  }

  generatingDefaults.value = true;
  try {
    const result = await groupApi.generateDefaults(
      props.groupName,
      props.serverId,
    );
    const msg = [
      result.message || "生成完成",
      "",
      `新建：${result.created ?? 0} 个`,
      `跳过（已存在）：${result.skipped ?? 0} 个`,
    ].join("\n");
    notify(msg);
    await loadData(pagination.page);
    emit("success");
  } catch (error) {
    notify(
      "生成标准代理失败: " + (error.response?.data?.detail || error.message),
    );
  } finally {
    generatingDefaults.value = false;
  }
};

const syncFromFrps = async () => {
  if (loading.value || generatingDefaults.value) return;
  const response = await loadData(1, true);
  if (!response) return;
  if (response.analysis) {
    const a = response.analysis;
    notify(
      `同步完成（当前分组及筛选）\n数据库代理：${a.total_in_db ?? 0}\nfrps 代理：${a.total_in_frps ?? 0}\n状态变化：${a.status_changed?.length || 0}`,
    );
  } else notify("同步成功");
  emit("success");
};

const handleProxyAdded = async () => {
  showAddProxyDialog.value = false;
  await loadData(pagination.page);
  emit("success");
};

const resetState = () => {
  ++requestId;
  loading.value = false;
  loadError.value = "";
  filters.search = "";
  filters.status = "";
  proxies.value = [];
  pagination.page = 1;
  pagination.page_size = 20;
  pagination.total = 0;
  showEditProxyDialog.value = false;
  showAddProxyDialog.value = false;
  editingProxy.value = null;
  generatingDefaults.value = false;
};

const handleBackdropClick = () => {
  closeDialog();
};
</script>
