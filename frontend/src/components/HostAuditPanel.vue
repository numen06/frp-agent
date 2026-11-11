<template>
  <Card
    ><CardHeader
      ><h2 class="font-semibold">访问审计与流量统计</h2>
      <div class="flex flex-wrap gap-2">
        <Button
          type="button"
          :disabled="list.loading.value"
          @click="reload"
          variant="outline"
          size="sm"
          >刷新</Button
        ><Button
          v-if="isAdmin"
          type="button"
          class="text-red-600"
          :disabled="!selected.length || maintaining"
          @click="removeSelected"
          variant="outline"
          size="sm"
          >删除所选（{{ selected.length }}）</Button
        ><Button
          v-if="isAdmin"
          type="button"
          @click="cleanupOpen = true"
          variant="outline"
          size="sm"
          >清理旧日志</Button
        >
      </div></CardHeader
    >
    <p
      v-if="fixedHost"
      class="border-b px-4 py-3 text-xs text-muted-foreground"
    >
      日志与流量范围固定为当前主机。{{
        isAdmin ? "" : "仅显示你本人的访问与操作记录。"
      }}
    </p>
    <form
      class="grid items-end gap-3 border-b p-4 sm:grid-cols-2 sm:p-5 xl:grid-cols-4"
      @submit.prevent="applyFilters"
    >
      <SearchField
        v-model="list.search.value"
        placeholder="主机 / 操作者 / IP / 命令"
        label="搜索审计日志"
        @search="applyFilters"
      ></SearchField
      ><ResourceCombobox
        v-if="!fixedHost"
        v-model="filters.host_id"
        label="筛选主机"
        :fetch-options="managedHostsApi.list"
        :resolve-option="resolveHost"
        allow-clear
        clear-label="全部主机"
      /><Select v-model="filters.action"
        ><SelectTrigger aria-label="审计动作" class="w-full"
          ><SelectValue placeholder="全部动作"></SelectValue></SelectTrigger
        ><SelectContent
          ><SelectItem :value="null">全部动作</SelectItem
          ><SelectItem
            v-for="(label, key) in actions"
            :key="key"
            :value="key"
            >{{ label }}</SelectItem
          ></SelectContent
        ></Select
      ><Select v-model="filters.status"
        ><SelectTrigger aria-label="审计结果" class="w-full"
          ><SelectValue placeholder="全部结果"></SelectValue></SelectTrigger
        ><SelectContent
          ><SelectItem :value="null">全部结果</SelectItem
          ><SelectItem value="success">成功</SelectItem
          ><SelectItem value="failed">失败</SelectItem></SelectContent
        ></Select
      ><label class="min-w-0 text-xs text-gray-500"
        >开始时间<Input
          v-model="filters.start_time"
          type="datetime-local"
          aria-label="审计开始时间"
          class="mt-1 block w-full min-w-0"
        ></Input></label
      ><label class="min-w-0 text-xs text-gray-500"
        >结束时间<Input
          v-model="filters.end_time"
          type="datetime-local"
          aria-label="审计结束时间"
          class="mt-1 block w-full min-w-0"
        ></Input
      ></label>
      <div class="flex items-end gap-2">
        <Button
          type="submit"
          :disabled="list.loading.value"
          variant="default"
          size="default"
          >查询</Button
        ><Button
          type="button"
          @click="resetFilters"
          variant="outline"
          size="default"
          >重置</Button
        >
      </div>
    </form>
    <div v-if="summary" class="border-b border-gray-200 p-4">
      <dl class="grid gap-3 text-sm sm:grid-cols-3">
        <div class="rounded-lg bg-blue-50 p-3">
          <dt class="text-xs text-gray-500">发送到主机</dt>
          <dd class="mt-1 text-lg font-semibold">
            {{ formatBytes(summary.bytes_sent) }}
          </dd>
        </div>
        <div class="rounded-lg bg-emerald-50 p-3">
          <dt class="text-xs text-gray-500">从主机接收</dt>
          <dd class="mt-1 text-lg font-semibold">
            {{ formatBytes(summary.bytes_received) }}
          </dd>
        </div>
        <div class="rounded-lg bg-gray-50 p-3">
          <dt class="text-xs text-gray-500">已采集的访问 / 操作</dt>
          <dd class="mt-1 text-lg font-semibold">
            {{ summary.measured_count }} 次
          </dd>
        </div>
      </dl>
      <p class="mt-3 text-xs leading-5 text-gray-500">
        累计当前筛选条件下所有保留记录，连接或操作结束后入账；清理日志会同步减少统计。发送/接收按平台到主机方向，SSH/RDP
        统计应用数据（不含加密开销），Docker
        统计请求/响应正文。旧记录及未采集的操作显示“未采集”。
      </p>
    </div>
    <p
      v-if="list.error.value || error"
      role="alert"
      class="p-4 text-sm text-red-600"
    >
      {{ list.error.value || error }}
    </p>
    <p v-if="notice" role="status" class="px-4 py-2 text-sm text-emerald-700">
      {{ notice }}
    </p>
    <p
      v-if="list.loading.value"
      role="status"
      class="p-6 text-center text-sm text-gray-500"
    >
      正在加载日志…
    </p>
    <template v-else>
      <div class="hidden overflow-x-auto md:block">
        <Table class="w-full min-w-[1000px] text-left"
          ><TableHeader
            ><TableRow
              ><TableHead v-if="isAdmin"
                ><Checkbox
                  aria-label="选择本页日志"
                  :model-value="allSelected"
                  @update:model-value="toggleAll"
                ></Checkbox></TableHead
              ><TableHead>时间</TableHead><TableHead>操作者</TableHead
              ><TableHead>主机</TableHead><TableHead>动作</TableHead
              ><TableHead>目标/命令</TableHead><TableHead>结果</TableHead
              ><TableHead>发送 / 接收</TableHead><TableHead>来源 IP</TableHead
              ><TableHead>详情</TableHead></TableRow
            ></TableHeader
          ><TableBody
            ><TableRow v-for="log in list.items.value" :key="log.id"
              ><TableCell v-if="isAdmin"
                ><Checkbox
                  :aria-label="`选择日志 ${log.id}`"
                  :model-value="selected.includes(log.id)"
                  @update:model-value="
                    (checked) => {
                      selected = checked
                        ? [...selected, log.id]
                        : selected.filter((value) => value !== log.id);
                    }
                  "
                ></Checkbox></TableCell
              ><TableCell class="whitespace-nowrap">{{
                date(log.created_at)
              }}</TableCell
              ><TableCell>{{ log.actor_name }}</TableCell
              ><TableCell>{{ log.host_name }}</TableCell
              ><TableCell>{{ actions[log.action] || log.action }}</TableCell
              ><TableCell
                class="max-w-xs truncate font-mono"
                :title="log.command || log.target"
                >{{ log.command || log.target || "-" }}</TableCell
              ><TableCell :class="statusClass(log)">{{
                statusLabel(log)
              }}</TableCell
              ><TableCell class="whitespace-nowrap"
                >{{ formatBytes(log.bytes_sent) }} /
                {{ formatBytes(log.bytes_received) }}</TableCell
              ><TableCell>{{ log.client_ip || "-" }}</TableCell
              ><TableCell
                ><Button
                  type="button"
                  @click="showDetail(log.id)"
                  variant="outline"
                  size="sm"
                  >详情</Button
                ></TableCell
              ></TableRow
            ></TableBody
          ></Table
        >
      </div>
      <div class="mobile-record-list md:hidden">
        <article
          v-for="log in list.items.value"
          :key="log.id"
          class="mobile-record h-80"
        >
          <div class="flex items-start justify-between gap-2">
            <label class="flex min-h-11 min-w-0 items-center gap-3"
              ><Checkbox
                v-if="isAdmin"
                :aria-label="`选择日志 ${log.id}`"
                :model-value="selected.includes(log.id)"
                @update:model-value="
                  (checked) => {
                    selected = checked
                      ? [...selected, log.id]
                      : selected.filter((value) => value !== log.id);
                  }
                "
              ></Checkbox
              ><span class="mobile-record-title" :title="log.host_name">{{
                log.host_name
              }}</span></label
            ><span class="shrink-0 text-sm" :class="statusClass(log)">{{
              statusLabel(log)
            }}</span>
          </div>
          <p
            class="truncate text-xs text-muted-foreground"
            :title="log.actor_name"
          >
            {{ log.actor_name }} · {{ date(log.created_at) }}
          </p>
          <p class="line-clamp-2 min-h-10 text-sm">
            {{ actions[log.action] || log.action }}
          </p>
          <p class="text-xs text-gray-600">
            发送 {{ formatBytes(log.bytes_sent) }} · 接收
            {{ formatBytes(log.bytes_received) }}
          </p>
          <pre
            v-if="log.command || log.target"
            class="max-h-12 min-w-0 overflow-auto rounded-lg bg-muted p-2 text-xs"
            >{{ log.command || log.target }}</pre>
          <div
            class="mt-auto flex items-center justify-between gap-2 border-t pt-3"
          >
            <span
              class="min-w-0 truncate text-xs text-muted-foreground"
              :title="log.client_ip"
              >来源：{{ log.client_ip || "-" }}</span
            ><Button
              type="button"
              @click="showDetail(log.id)"
              variant="outline"
              size="sm"
              >详情</Button
            >
          </div>
        </article>
      </div>
      <p
        v-if="!list.items.value.length && !list.error.value && !error"
        class="p-8 text-center text-sm text-gray-500"
      >
        暂无审计记录
      </p>
    </template>
    <div class="border-t border-gray-200 p-4">
      <TablePagination
        :total="list.pagination.total"
        :page="list.pagination.page"
        :page-size="list.pagination.page_size"
        @page-change="changePage"
        @page-size-change="resize"
      /></div></Card
  ><Dialog
    v-if="detailOpen"
    :open="true"
    @update:open="
      (open) => {
        if (!false) {
          detailOpen = open;
        }
      }
    "
    ><DialogContent
      class="sm:max-w-3xl"
      :aria-describedby="undefined"
      :show-close-button="!false"
      @escape-key-down="
        (e) => {
          if (false) e.preventDefault();
        }
      "
      @interact-outside="
        (e) => {
          if (false) e.preventDefault();
        }
      "
      ><DialogHeader><DialogTitle>审计日志详情</DialogTitle></DialogHeader>
      <div
        data-slot="dialog-body"
        class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
      >
        <p v-if="!detail" class="text-sm text-gray-500">正在加载详情…</p>
        <template v-else>
          <dl class="grid grid-cols-[auto_1fr] gap-3 text-sm">
            <dt>时间</dt>
            <dd>{{ date(detail.created_at) }}</dd>
            <dt>主机</dt>
            <dd class="break-all">{{ detail.host_name }}</dd>
            <dt>操作者</dt>
            <dd>{{ detail.actor_name }}（{{ detail.actor_type }}）</dd>
            <dt>动作</dt>
            <dd>{{ actions[detail.action] || detail.action }}</dd>
            <dt>来源 IP</dt>
            <dd>{{ detail.client_ip || "-" }}</dd>
            <dt>结果</dt>
            <dd>
              {{ statusLabel(detail) }} · 退出码 {{ detail.exit_code ?? "-" }} ·
              {{ detail.duration_ms ?? "-" }}ms
            </dd>
          </dl>
          <div v-for="field in detailFields" :key="field.key" class="mt-4">
            <h3 class="mb-1 text-sm font-medium">{{ field.label }}</h3>
            <pre
              class="max-h-64 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-gray-50 p-3 text-xs"
              >{{ detail[field.key] || "-" }}</pre>
          </div>
          <p class="mt-4 text-sm">
            发送到主机 {{ formatBytes(detail.bytes_sent) }} · 从主机接收
            {{ formatBytes(detail.bytes_received) }}
          </p>
        </template>
      </div>
      <DialogFooter
        ><Button
          type="button"
          @click="detailOpen = false"
          variant="outline"
          size="default"
          >关闭详情</Button
        ></DialogFooter
      ></DialogContent
    ></Dialog
  ><Dialog
    v-if="cleanupOpen"
    :open="true"
    @update:open="
      (open) => {
        if (!maintaining) {
          cleanupOpen = open;
        }
      }
    "
    ><DialogContent
      class="sm:max-w-xl"
      :aria-describedby="undefined"
      :show-close-button="!maintaining"
      @escape-key-down="
        (e) => {
          if (maintaining) e.preventDefault();
        }
      "
      @interact-outside="
        (e) => {
          if (maintaining) e.preventDefault();
        }
      "
      ><DialogHeader><DialogTitle>清理旧日志</DialogTitle></DialogHeader>
      <div
        data-slot="dialog-body"
        class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
      >
        <p class="mb-4 text-sm text-gray-600">
          仅删除超过保留天数的日志。{{
            filters.host_id ? "范围：当前筛选主机。" : "范围：全部主机。"
          }}该操作会保留新的清理审计记录。
        </p>
        <label class="text-sm"
          >保留最近天数<Input
            v-model.number="keepDays"
            :disabled="maintaining"
            type="number"
            min="1"
            max="3650"
            class="mt-2 w-full"
          ></Input
        ></label>
        <p v-if="preview !== null" class="mt-4 text-sm text-red-600">
          预计删除 {{ preview }} 条旧日志，删除后不可恢复。
        </p>
        <p v-if="error" role="alert" class="mt-3 text-sm text-red-600">
          {{ error }}
        </p>
      </div>
      <DialogFooter
        ><Button
          type="button"
          :disabled="maintaining"
          @click="previewCleanup"
          variant="outline"
          size="default"
          >预览影响数量</Button
        ><Button
          type="button"
          :disabled="!preview || maintaining"
          @click="cleanup"
          variant="destructive"
          size="default"
          >确认清理</Button
        ></DialogFooter
      ></DialogContent
    ></Dialog
  >
</template>

<script setup>
import SearchField from "@/components/SearchField.vue";
import { CardHeader } from "@/components/ui/card";
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
import { Checkbox } from "@/components/ui/checkbox";
import { Select } from "@/components/ui/select";
import { SelectContent } from "@/components/ui/select";
import { SelectItem } from "@/components/ui/select";
import { SelectTrigger } from "@/components/ui/select";
import { SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { confirmAction } from "@/composables/useFeedback";
import { computed, onMounted, reactive, ref, watch } from "vue";
import ResourceCombobox from "./ResourceCombobox.vue";
import TablePagination from "./TablePagination.vue";
import { managedHostsApi } from "@/api/managedHosts";
import { usePagedList } from "@/composables/usePagedList";
import { formatBytes } from "@/utils/traffic";
function statusLabel(log) {
  if (log.status !== "success") return "失败";
  if (log.action === "rdp_gateway_authorized") return "仅认证通过";
  if (log.action === "rdp_gateway_closed") return "已结束";
  if (log.action === "rdp_desktop_connected") return "桌面已连接";
  return "成功";
}
function statusClass(log) {
  if (log.status !== "success") return "text-destructive";
  if (log.action === "rdp_gateway_closed") return "text-muted-foreground";
  if (log.action === "rdp_gateway_authorized") return "text-blue-700";
  return "text-emerald-700";
}
const props = defineProps({
  isAdmin: Boolean,
  hostId: { type: [Number, String], default: "" },
  fixedHost: Boolean,
});
const filters = reactive({
  host_id: props.hostId,
  action: "",
  status: "",
  start_time: "",
  end_time: "",
});
let applied = props.hostId ? { host_id: props.hostId } : {};
const summary = ref(null);
let requestId = 0;
const list = usePagedList(async (params) => {
  const id = ++requestId;
  summary.value = null;
  const query = {
    ...params,
    ...applied,
    ...(props.fixedHost ? { host_id: props.hostId } : {}),
  };
  const [data, traffic] = await Promise.all([
    managedHostsApi.audit(query),
    managedHostsApi.traffic(query),
  ]);
  if (id === requestId) summary.value = traffic;
  return data;
});
const selected = ref([]),
  error = ref(""),
  notice = ref(""),
  maintaining = ref(false);
const detailOpen = ref(false),
  detail = ref(null),
  cleanupOpen = ref(false),
  keepDays = ref(90),
  preview = ref(null);
const detailFields = [
  { key: "target", label: "目标" },
  { key: "command", label: "命令" },
  { key: "stdout", label: "标准输出" },
  { key: "stderr", label: "错误输出" },
];
const actions = {
  connection_test: "连接测试",
  execute_command: "执行命令",
  execute_sudo_command: "提权执行",
  ssh_gateway_session: "SSH 跳板会话",
  vnc_connected: "VNC 桌面已连接",
  vnc_session: "VNC 会话结束",
  webssh_connected: "Web SSH 已连接",
  webssh_session: "Web SSH 会话结束",
  docker_gateway_request: "Docker 网关请求",
  docker_list: "查询容器",
  docker_start: "启动容器",
  docker_stop: "停止容器",
  docker_restart: "重启容器",
  rdp_file_downloaded: "下载 RDP 连接",
  rdp_ticket_issued: "签发 RDP 临时凭据",
  rdp_desktop_connected: "RDP 桌面已连接",
  rdp_gateway_authorized: "RDP 平台认证通过（尚未进入桌面）",
  rdp_gateway_closed: "RDP 会话结束（不代表桌面成功）",
  audit_logs_deleted: "清理审计日志",
};
const allSelected = computed(
  () =>
    list.items.value.length > 0 &&
    list.items.value.every((row) => selected.value.includes(row.id)),
);
const date = (value) =>
  value
    ? new Date(
        value.endsWith("Z") || /[+-]\d\d:\d\d$/.test(value)
          ? value
          : `${value}Z`,
      ).toLocaleString("zh-CN")
    : "-";
const resolveHost = async (id) =>
  (await managedHostsApi.list({ page: 1, host_id: id })).items[0];
const reload = () => list.load();
async function changePage(page) {
  selected.value = [];
  await list.load(page);
}
async function resize(size) {
  selected.value = [];
  await list.resize(size);
}
function toggleAll() {
  selected.value = allSelected.value
    ? []
    : list.items.value.map((row) => row.id);
}
async function applyFilters() {
  error.value = "";
  if (
    filters.start_time &&
    filters.end_time &&
    filters.start_time > filters.end_time
  ) {
    error.value = "开始时间不能晚于结束时间";
    return;
  }
  applied = Object.fromEntries(
    Object.entries(filters)
      .filter(([, value]) => value !== "")
      .map(([key, value]) => [
        key,
        key.endsWith("_time") ? new Date(value).toISOString() : value,
      ]),
  );
  await changePage(1);
}
function resetFilters() {
  Object.keys(filters).forEach((key) => (filters[key] = ""));
  if (props.fixedHost) filters.host_id = props.hostId;
  list.search.value = "";
  applyFilters();
}
async function showDetail(id) {
  detail.value = null;
  detailOpen.value = true;
  try {
    detail.value = await managedHostsApi.auditDetail(id);
  } catch (e) {
    error.value = e.message;
    detailOpen.value = false;
  }
}
async function removeSelected() {
  if (
    !selected.value.length ||
    !(await confirmAction(
      `确定删除所选 ${selected.value.length} 条日志？删除后不可恢复。`,
    ))
  )
    return;
  maintaining.value = true;
  error.value = "";
  try {
    const result = await managedHostsApi.deleteAudit(selected.value);
    notice.value = `已删除 ${result.deleted} 条日志`;
    selected.value = [];
    await list.load();
  } catch (e) {
    error.value = e.message;
  } finally {
    maintaining.value = false;
  }
}
watch([keepDays, () => filters.host_id, cleanupOpen], () => {
  preview.value = null;
  error.value = "";
});
async function previewCleanup() {
  if (
    !Number.isInteger(keepDays.value) ||
    keepDays.value < 1 ||
    keepDays.value > 3650
  ) {
    error.value = "保留天数必须为 1–3650 的整数";
    return;
  }
  maintaining.value = true;
  error.value = "";
  try {
    const result = await managedHostsApi.cleanupAudit({
      keep_days: keepDays.value,
      host_id: (props.fixedHost ? props.hostId : filters.host_id) || undefined,
      dry_run: true,
    });
    preview.value = result.count;
  } catch (e) {
    error.value = e.message;
  } finally {
    maintaining.value = false;
  }
}
async function cleanup() {
  if (
    !preview.value ||
    !(await confirmAction(
      `确定清理超过 ${keepDays.value} 天的旧日志（预计 ${preview.value} 条）？`,
    ))
  )
    return;
  maintaining.value = true;
  error.value = "";
  try {
    const result = await managedHostsApi.cleanupAudit({
      keep_days: keepDays.value,
      host_id: (props.fixedHost ? props.hostId : filters.host_id) || undefined,
      dry_run: false,
    });
    notice.value = `已清理 ${result.deleted} 条旧日志`;
    cleanupOpen.value = false;
    selected.value = [];
    await list.load();
  } catch (e) {
    error.value = e.message;
  } finally {
    maintaining.value = false;
  }
}
defineExpose({ load: reload });
watch(
  () => props.hostId,
  (value) => {
    filters.host_id = value;
    applyFilters();
  },
);
onMounted(() => list.load(1));
</script>
