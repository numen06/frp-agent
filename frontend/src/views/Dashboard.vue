<template>
  <div class="space-y-5">
    <!-- 欢迎区域 --><PageHeader
      :title="`欢迎回来，${authStore.username || '管理员'}`"
      description="查看代理汇总与服务器概览，资源和连接质量请前往运行维护。"
    >
      <span
        class="rounded-full border border-gray-200 bg-white px-3 py-2 text-xs text-gray-600"
        >已接入 {{ serversStore.pagination.total }} 台服务器</span
      >
    </PageHeader>
    <div
      v-if="summaryError || statsError || serversStore.error"
      role="alert"
      class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-destructive/30 bg-card p-4 text-sm text-destructive"
    >
      <p>
        {{
          summaryError || statsError || serversStore.error
        }}。统计未能完整更新，当前数字不能视为实时结果。
      </p>
      <Button
        type="button"
        variant="outline"
        :disabled="retrying"
        @click="retryDashboard"
        >重试读取概览</Button
      >
    </div>
    <!-- 汇总统计卡片 --><Card
      ><CardHeader
        ><h3 class="text-base font-semibold text-gray-900">
          汇总统计
        </h3></CardHeader
      ><CardContent
        ><div class="grid grid-cols-2 gap-3 sm:gap-5 lg:grid-cols-4">
          <div class="min-w-0">
            <div
              class="h-full min-h-[120px] rounded-xl border border-gray-200 bg-white p-3 shadow-sm sm:min-h-[148px] sm:p-5"
            >
              <div class="mb-3 flex items-center justify-between">
                <div
                  class="mb-0 text-xs font-semibold uppercase tracking-wide text-gray-500"
                >
                  代理总数
                </div>
                <div
                  class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gray-100 text-gray-600"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-5 w-5 shrink-0"
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
                    <path d="M9 6l11 0" />
                    <path d="M9 12l11 0" />
                    <path d="M9 18l11 0" />
                    <path d="M5 6l0 .01" />
                    <path d="M5 12l0 .01" />
                    <path d="M5 18l0 .01" />
                  </svg>
                </div>
              </div>
              <div
                class="mb-0 text-2xl font-bold leading-none text-gray-900 tabular-nums sm:text-3xl"
              >
                {{ totalStats.total }}
              </div>
              <div class="mt-2 text-xs text-gray-500 sm:mt-3">
                全局代理实例数量
              </div>
            </div>
          </div>
          <div class="min-w-0">
            <div
              class="h-full min-h-[120px] rounded-xl border border-gray-200 bg-gray-50 p-3 shadow-sm sm:min-h-[148px] sm:p-5"
            >
              <div class="mb-3 flex items-center justify-between">
                <div
                  class="mb-0 text-xs font-semibold uppercase tracking-wide text-gray-500"
                >
                  在线代理
                </div>
                <div
                  class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gray-100 text-gray-600"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-5 w-5 shrink-0"
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
                    <path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0" />
                    <path d="M12 8l0 4" />
                    <path d="M12 16l.01 0" />
                  </svg>
                </div>
              </div>
              <div
                class="mb-0 text-2xl font-bold leading-none text-gray-900 tabular-nums sm:text-3xl"
              >
                {{ totalStats.online }}
              </div>
              <div class="mt-2 text-xs text-gray-600 sm:mt-3">
                在线率: {{ totalOnlineRate }}%
              </div>
              <div
                class="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-gray-200 sm:mt-3"
              >
                <div
                  class="h-full rounded-full bg-blue-600"
                  :style="`width: ${totalOnlineRate}%`"
                ></div>
              </div>
            </div>
          </div>
          <div class="min-w-0">
            <div
              class="h-full min-h-[120px] rounded-xl border border-gray-200 bg-gray-50 p-3 shadow-sm sm:min-h-[148px] sm:p-5"
            >
              <div class="mb-3 flex items-center justify-between">
                <div
                  class="mb-0 text-xs font-semibold uppercase tracking-wide text-gray-500"
                >
                  离线代理
                </div>
                <div
                  class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gray-100 text-gray-600"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-5 w-5 shrink-0"
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
                    <path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0" />
                    <path d="M12 8l0 4" />
                    <path d="M12 16l.01 0" />
                  </svg>
                </div>
              </div>
              <div
                class="mb-0 text-2xl font-bold leading-none text-gray-900 tabular-nums sm:text-3xl"
              >
                {{ totalStats.offline }}
              </div>
              <div class="mt-2 text-xs text-gray-600 sm:mt-3">
                离线率: {{ totalOfflineRate }}%
              </div>
              <div
                class="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-gray-200 sm:mt-3"
              >
                <div
                  class="h-full rounded-full bg-gray-500"
                  :style="`width: ${totalOfflineRate}%`"
                ></div>
              </div>
            </div>
          </div>
          <div class="min-w-0">
            <div
              class="h-full min-h-[120px] rounded-xl border border-gray-200 bg-white p-3 shadow-sm sm:min-h-[148px] sm:p-5"
            >
              <div class="mb-3 flex items-center justify-between">
                <div
                  class="mb-0 text-xs font-semibold uppercase tracking-wide text-gray-500"
                >
                  端口分配
                </div>
                <div
                  class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gray-100 text-gray-600"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-5 w-5 shrink-0"
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
                    <path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0" />
                    <path d="M12 6l0 6l6 -6" />
                  </svg>
                </div>
              </div>
              <div
                class="mb-0 text-2xl font-bold leading-none text-gray-900 tabular-nums sm:text-3xl"
              >
                {{ totalStats.portCount }}
              </div>
              <div class="mt-2 text-xs text-gray-600 sm:mt-3">
                去重后远端端口数量
              </div>
            </div>
          </div>
        </div></CardContent
      ></Card
    ><!-- 各服务器统计 --><Card v-if="serversStore.servers.length > 0"
      ><div
        class="flex flex-wrap items-center justify-between gap-2 border-b border-gray-200 px-3 py-3 sm:px-5 sm:py-3.5"
      >
        <h3 class="text-base font-semibold text-gray-900">服务器详情</h3>
        <Button
          type="button"
          class="gap-1.5 touch-manipulation"
          :disabled="serverStatsLoading"
          aria-label="刷新服务器统计"
          @click="reloadServerStats"
          variant="outline"
          size="sm"
          ><span
            class="inline-block h-3.5 w-3.5 shrink-0 rounded-full border-2 border-gray-300 border-t-blue-600"
            :class="{ 'animate-spin': serverStatsLoading }"
            role="status"
            aria-hidden="true"
          ></span>
          {{ serverStatsLoading ? "刷新中…" : "刷新统计" }}</Button
        >
      </div>
      <div v-if="serverStatsLoading" class="p-3 sm:p-5">
        <div
          class="flex items-center justify-center gap-2 py-4 text-center text-sm text-gray-600"
        >
          <span
            class="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600"
            role="status"
            aria-label="加载中"
          ></span
          ><span>加载中...</span>
        </div>
      </div>
      <template v-else>
        <!-- 手机端：卡片列表 -->
        <div class="space-y-3 p-3 md:hidden sm:p-5">
          <div
            v-for="server in serversStore.servers"
            :key="`card-${server.id}`"
            class="rounded-xl border border-gray-200 bg-gray-50 p-4"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0 flex-1">
                <div class="font-semibold text-gray-900">{{ server.name }}</div>
                <div class="mt-0.5 break-all text-xs text-gray-500">
                  {{ server.api_base_url }}
                </div>
              </div>
              <span
                class="inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                :class="getServerStatusBadgeClass(server)"
              >
                {{ getServerStatusText(server) }}
              </span>
            </div>
            <div class="mt-2 break-all text-sm text-gray-700">
              {{ server.server_addr }}:{{ server.server_port }}
            </div>
            <div class="mt-0.5 text-xs text-gray-500">
              {{ server.auth_username }}
            </div>
            <div class="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
              <div>
                <span class="text-gray-500">代理总数</span>
                <div class="font-semibold text-gray-900">
                  {{ getServerStats(server.id).total }}
                </div>
              </div>
              <div>
                <span class="text-gray-500">端口数</span>
                <div class="font-semibold text-gray-900">
                  {{ getServerStats(server.id).portCount }}
                </div>
              </div>
              <div>
                <span class="text-gray-500">在线</span>
                <div>
                  <span
                    class="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800"
                  >
                    {{ getServerStats(server.id).online }}
                  </span>
                </div>
              </div>
              <div>
                <span class="text-gray-500">离线</span>
                <div>
                  <span
                    class="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800"
                  >
                    {{ getServerStats(server.id).offline }}
                  </span>
                </div>
              </div>
            </div>
            <div class="mt-3 flex items-center gap-2">
              <div
                class="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-gray-200"
              >
                <div
                  class="h-full rounded-full"
                  :class="
                    getServerOnlineRate(server.id) > 0
                      ? 'bg-green-600'
                      : 'bg-gray-400'
                  "
                  :style="`width: ${getServerOnlineRate(server.id)}%`"
                  role="progressbar"
                  :aria-valuenow="getServerOnlineRate(server.id)"
                  aria-valuemin="0"
                  aria-valuemax="100"
                ></div>
              </div>
              <span class="shrink-0 text-xs text-gray-600"
                >在线率 {{ getServerOnlineRate(server.id) }}%</span
              >
            </div>
          </div>
        </div>
        <!-- 桌面端：表格 -->
        <div class="hidden overflow-x-auto md:block">
          <Table class="w-full text-left"
            ><TableHeader
              ><TableRow
                ><TableHead>服务器名称</TableHead
                ><TableHead>服务器地址</TableHead><TableHead>连接状态</TableHead
                ><TableHead>代理总数</TableHead><TableHead>在线</TableHead
                ><TableHead>离线</TableHead><TableHead>端口数</TableHead
                ><TableHead>在线率</TableHead></TableRow
              ></TableHeader
            ><TableBody
              ><TableRow
                v-for="server in serversStore.servers"
                :key="server.id"
                class="transition-colors"
                ><TableCell
                  ><div class="font-semibold text-gray-900">
                    {{ server.name }}
                  </div>
                  <div class="text-xs text-gray-500">
                    {{ server.api_base_url }}
                  </div></TableCell
                ><TableCell
                  ><div>{{ server.server_addr }}:{{ server.server_port }}</div>
                  <div class="text-xs text-gray-500">
                    {{ server.auth_username }}
                  </div></TableCell
                ><TableCell
                  ><span
                    class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                    :class="getServerStatusBadgeClass(server)"
                  >
                    {{ getServerStatusText(server) }}
                  </span></TableCell
                ><TableCell
                  ><div class="font-semibold text-gray-900">
                    {{ getServerStats(server.id).total }}
                  </div></TableCell
                ><TableCell
                  ><span
                    class="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800"
                  >
                    {{ getServerStats(server.id).online }}
                  </span></TableCell
                ><TableCell
                  ><span
                    class="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800"
                  >
                    {{ getServerStats(server.id).offline }}
                  </span></TableCell
                ><TableCell>{{ getServerStats(server.id).portCount }}</TableCell
                ><TableCell
                  ><div class="flex items-center gap-2">
                    <div
                      class="h-1.5 w-[60px] shrink-0 overflow-hidden rounded-full bg-gray-200"
                    >
                      <div
                        class="h-full rounded-full"
                        :class="
                          getServerOnlineRate(server.id) > 0
                            ? 'bg-green-600'
                            : 'bg-gray-400'
                        "
                        :style="`width: ${getServerOnlineRate(server.id)}%`"
                        role="progressbar"
                        :aria-valuenow="getServerOnlineRate(server.id)"
                        aria-valuemin="0"
                        aria-valuemax="100"
                      ></div>
                    </div>
                    <span class="text-xs text-gray-600"
                      >{{ getServerOnlineRate(server.id) }}%</span
                    >
                  </div></TableCell
                ></TableRow
              ></TableBody
            ></Table
          >
        </div>
      </template></Card
    >
    <div class="rounded-xl border border-gray-200 bg-white p-4">
      <TablePagination
        :total="serversStore.pagination.total"
        :page="serversStore.pagination.page"
        :page-size="serversStore.pagination.page_size"
        @page-change="(page) => serversStore.loadServers(page)"
        @page-size-change="serversStore.resize"
      />
    </div>
    <!-- 快速操作 --><Card
      ><CardHeader
        ><h3 class="text-base font-semibold text-gray-900">
          快速操作
        </h3></CardHeader
      ><CardContent
        ><div class="grid grid-cols-2 gap-2.5 md:grid-cols-4">
          <router-link
            to="/proxies"
            class="inline-flex min-h-11 w-full touch-manipulation flex-col items-center justify-center gap-1.5 rounded-xl border border-gray-300 bg-white px-2 py-3 text-center text-sm font-medium leading-snug text-gray-700 transition-colors hover:bg-gray-100 sm:flex-row sm:gap-2 sm:px-3 sm:py-2.5"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5 shrink-0"
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
              <path d="M9 6l11 0" />
              <path d="M9 12l11 0" />
              <path d="M9 18l11 0" />
              <path d="M5 6l0 .01" />
              <path d="M5 12l0 .01" />
              <path d="M5 18l0 .01" />
            </svg>
            代理列表 </router-link
          ><router-link
            to="/groups"
            class="inline-flex min-h-11 w-full touch-manipulation flex-col items-center justify-center gap-1.5 rounded-xl border border-gray-300 bg-white px-2 py-3 text-center text-sm font-medium leading-snug text-gray-700 transition-colors hover:bg-gray-100 sm:flex-row sm:gap-2 sm:px-3 sm:py-2.5"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5 shrink-0"
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
                d="M9 4h3l2 2h5a2 2 0 0 1 2 2v7a2 2 0 0 1 -2 2h-10a2 2 0 0 1 -2 -2v-9a2 2 0 0 1 2 -2"
              />
              <path
                d="M17 17v2a2 2 0 0 1 -2 2h-10a2 2 0 0 1 -2 -2v-9a2 2 0 0 1 2 -2h2"
              />
            </svg>
            分组管理 </router-link
          ><router-link
            to="/converter"
            class="inline-flex min-h-11 w-full touch-manipulation flex-col items-center justify-center gap-1.5 rounded-xl border border-gray-300 bg-white px-2 py-3 text-center text-sm font-medium leading-snug text-gray-700 transition-colors hover:bg-gray-100 sm:flex-row sm:gap-2 sm:px-3 sm:py-2.5"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5 shrink-0"
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
            INI 转换
          </router-link>
        </div></CardContent
      ></Card
    >
  </div>
</template>

<script setup>
import { CardHeader, CardContent } from "@/components/ui/card";
import { Table } from "@/components/ui/table";
import { TableBody } from "@/components/ui/table";
import { TableCell } from "@/components/ui/table";
import { TableHeader } from "@/components/ui/table";
import { TableRow } from "@/components/ui/table";
import { TableHead } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import PageHeader from "@/components/PageHeader.vue";
import TablePagination from "@/components/TablePagination.vue";
import { ref, computed, onMounted, watch } from "vue";
import { useAuthStore } from "@/stores/auth";
import { useServersStore } from "@/stores/servers";
import { proxyApi } from "@/api/proxies";
import { useRefresh } from "@/composables/useRefresh";

const authStore = useAuthStore();
const serversStore = useServersStore();
const { refreshEvent } = useRefresh();

/** 仅「服务器详情」表格：与首屏汇总统计分离加载 */
const serverStatsLoading = ref(false);
const summaryError = ref(""),
  statsError = ref(""),
  retrying = ref(false);
async function retryDashboard() {
  if (retrying.value) return;
  retrying.value = true;
  try {
    await serversStore.loadServers();
    await Promise.all([loadDashboardSummary(), loadDashboardServerStats()]);
  } catch {
    /* The stores retain their retryable error. */
  } finally {
    retrying.value = false;
  }
}

// 汇总统计 - 直接从后端返回
const totalStats = computed(() => {
  return (
    statsData.value.total || { total: 0, online: 0, offline: 0, portCount: 0 }
  );
});

const totalOnlineRate = computed(() => {
  if (totalStats.value.total === 0) return 0;
  return Math.round((totalStats.value.online / totalStats.value.total) * 100);
});

const totalOfflineRate = computed(() => {
  if (totalStats.value.total === 0) return 0;
  return Math.round((totalStats.value.offline / totalStats.value.total) * 100);
});

const statsData = ref({
  total: { total: 0, online: 0, offline: 0, portCount: 0 },
  server_stats: {},
});

// 获取指定服务器的统计数据
const getServerStats = (serverId) => {
  return (
    statsData.value.server_stats[serverId] || {
      total: 0,
      online: 0,
      offline: 0,
      portCount: 0,
    }
  );
};

// 获取指定服务器的在线率
const getServerOnlineRate = (serverId) => {
  const stats = getServerStats(serverId);
  if (stats.total === 0) return 0;
  return Math.round((stats.online / stats.total) * 100);
};

const mergeServerStats = (server_stats) => {
  statsData.value = {
    ...statsData.value,
    server_stats: server_stats || {},
  };
};

/** 首屏：仅汇总数字（快速） */
const loadDashboardSummary = async () => {
  summaryError.value = "";
  try {
    const response = await proxyApi.getDashboardSummary();
    statsData.value = {
      ...statsData.value,
      total: response.total || statsData.value.total,
    };
  } catch (error) {
    summaryError.value = "汇总统计读取失败：" + error.message;
    console.error("加载汇总统计失败:", error);
  }
};

/** 表格：各服务器统计（可与汇总并行或稍后） */
const loadDashboardServerStats = async () => {
  statsError.value = "";
  serverStatsLoading.value = true;
  try {
    const response = await proxyApi.getDashboardServerStats(
      serversStore.servers.map((server) => server.id),
    );
    mergeServerStats(response.server_stats);
  } catch (error) {
    statsError.value = "节点统计读取失败：" + error.message;
    console.error("加载各服务器统计失败:", error);
  } finally {
    serverStatsLoading.value = false;
  }
};

watch(
  () => serversStore.servers.map((server) => server.id).join(","),
  () => loadDashboardServerStats(),
);

const reloadServerStats = () => loadDashboardServerStats();

// 监听刷新事件，当同步操作完成后自动刷新统计数据
watch(refreshEvent, () => {
  if (refreshEvent.value > 0) {
    loadDashboardSummary();
    loadDashboardServerStats();
  }
});

onMounted(async () => {
  try {
    if (serversStore.servers.length === 0) {
      await serversStore.loadServers();
    }
    // 先拉汇总（首屏数字），再拉各服务器统计（表格）
    await loadDashboardSummary();
    loadDashboardServerStats();
  } catch (error) {
    console.error("初始化失败:", error);
  }
});

const getServerStatusBadgeClass = (server) => {
  if (!server.last_test_status || server.last_test_status === "unknown")
    return "bg-gray-100 text-gray-800";
  return server.last_test_status === "online"
    ? "bg-green-100 text-green-800"
    : "bg-red-100 text-red-800";
};

const getServerStatusText = (server) => {
  if (!server.last_test_status || server.last_test_status === "unknown")
    return "未测试";
  return server.last_test_status === "online" ? "在线" : "离线";
};
</script>
