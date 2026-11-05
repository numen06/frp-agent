<template>
  <Dialog
    v-if="visible"
    :open="true"
    @update:open="
      (open) => {
        if (!open) {
          close();
        }
      }
    "
    ><DialogContent class="sm:max-w-4xl" :aria-describedby="undefined"
      ><DialogHeader
        ><DialogTitle
          >分组客户端升级 — {{ groupName }}</DialogTitle
        ></DialogHeader
      >
      <div
        data-slot="dialog-body"
        class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
      >
        <SshCredentialForm v-model="credentialId" />
        <div class="mt-3">
          <label class="mb-1 block text-xs font-medium text-gray-600"
            >frpc 安装路径</label
          ><Input
            v-model="installPath"
            type="text"
            class="w-full sm:max-w-md"
          ></Input>
        </div>
        <div class="mt-3 space-y-2">
          <label class="block text-xs font-medium text-gray-600">验证模式</label
          ><Select v-model="verifyMode"
            ><SelectTrigger class="w-full sm:max-w-md" aria-label="验证模式"
              ><SelectValue placeholder="请选择"></SelectValue></SelectTrigger
            ><SelectContent
              ><SelectItem value="agent_callback">回调验证（推荐）</SelectItem
              ><SelectItem value="skip">跳过远程验证</SelectItem></SelectContent
            ></Select
          >
          <div
            class="rounded-lg border border-blue-100 bg-blue-50 p-3 text-xs text-blue-900"
          >
            升级任务会上传到每台目标机后脱离 SSH 会话执行。若 SSH 连接本身走
            frpc 隧道，重启 frpc
            时连接中断属于预期，目标机本地脚本会继续校验并在失败时回滚。
          </div>
          <p v-if="verifyMode === 'skip'" class="text-xs text-amber-600">
            跳过远程验证将无法确认 frps 端连接状态，可能导致无法自动回滚
          </p>
        </div>
        <div
          v-if="jobSummary"
          class="mt-3 rounded-lg bg-blue-50 p-3 text-blue-900"
        >
          {{ jobSummary }}
        </div>
        <div v-if="results.length" class="mt-4 overflow-x-auto">
          <Table class="w-full text-left"
            ><TableHeader
              ><TableRow
                ><TableHead
                  ><Checkbox
                    :model-value="allUpgradeableSelected"
                    @update:model-value="toggleSelectAllUpgradeable"
                    aria-label="选择记录"
                  ></Checkbox></TableHead
                ><TableHead>代理</TableHead><TableHead>SSH 端点</TableHead
                ><TableHead>当前版本</TableHead><TableHead>目标版本</TableHead
                ><TableHead>配置</TableHead><TableHead>状态</TableHead
                ><TableHead>回滚</TableHead><TableHead>远端任务</TableHead
                ><TableHead>说明</TableHead></TableRow
              ></TableHeader
            ><TableBody
              ><TableRow v-for="row in results" :key="row.proxy_id"
                ><TableCell
                  ><Checkbox
                    v-if="row.upgradeable && row.rollback_capable"
                    :model-value="selectedIds.includes(row.proxy_id)"
                    @update:model-value="toggleSelect(row.proxy_id)"
                    aria-label="选择记录"
                  ></Checkbox></TableCell
                ><TableCell>{{ row.proxy_name || row.proxy_id }}</TableCell
                ><TableCell class="break-all font-mono">{{
                  row.ssh_target || "-"
                }}</TableCell
                ><TableCell>{{ row.current_version || "-" }}</TableCell
                ><TableCell>{{ row.target_version || "-" }}</TableCell
                ><TableCell
                  ><span v-if="row.config_path" class="font-mono">{{
                    row.config_format
                  }}</span
                  ><span v-else>-</span
                  ><span v-if="row.has_ini" class="ml-1 text-purple-600"
                    >ini</span
                  ><span v-if="row.has_toml" class="ml-1 text-blue-600"
                    >toml</span
                  ></TableCell
                ><TableCell
                  ><span :class="statusClass(row.status)">{{
                    statusLabel(row.status)
                  }}</span></TableCell
                ><TableCell
                  ><span v-if="row.rollback_capable" class="text-green-600"
                    >支持</span
                  ><span
                    v-else-if="row.rollback_capable === false"
                    class="text-amber-600"
                    >不支持</span
                  ><span v-else>-</span></TableCell
                ><TableCell class="break-all"
                  ><div v-if="row.execution_mode">{{ row.execution_mode }}</div>
                  <div v-if="row.remote_task_id">{{ row.remote_task_id }}</div>
                  <div v-if="row.remote_result_path">
                    {{ row.remote_result_path }}
                  </div>
                  <div
                    v-if="
                      !row.execution_mode &&
                      !row.remote_task_id &&
                      !row.remote_result_path
                    "
                  >
                    -
                  </div></TableCell
                ><TableCell>{{ row.message || "-" }}</TableCell></TableRow
              ></TableBody
            ></Table
          >
        </div>
        <p v-else-if="!scanning" class="mt-4 text-gray-500">
          扫描后将显示分组内 SSH 候选代理及结果。
        </p>
      </div>
      <div v-if="resultPagination.total" class="px-4 py-3">
        <TablePagination
          :total="resultPagination.total"
          :page="resultPagination.page"
          :page-size="resultPagination.page_size"
          @page-change="loadResultPage"
          @page-size-change="resizeResults"
        />
      </div>
      <DialogFooter
        ><Button
          type="button"
          class="w-full disabled:opacity-50 sm:w-auto"
          :disabled="!credentialId || !frpsServerId || scanning"
          @click="runGroupScan"
          variant="default"
          size="default"
          >{{ scanning ? "扫描中..." : "扫描分组" }}</Button
        ><Button
          type="button"
          class="w-full disabled:opacity-50 sm:w-auto"
          aria-label="升级所选客户端"
          :disabled="
            !credentialId ||
            !frpsServerId ||
            selectedIds.length === 0 ||
            upgrading
          "
          @click="runGroupUpgrade"
          variant="default"
          size="default"
          >{{
            upgrading ? "升级中..." : `升级所选 (${selectedIds.length})`
          }}</Button
        ></DialogFooter
      ></DialogContent
    ></Dialog
  >
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
import { Checkbox } from "@/components/ui/checkbox";
import { Select } from "@/components/ui/select";
import { SelectContent } from "@/components/ui/select";
import { SelectItem } from "@/components/ui/select";
import { SelectTrigger } from "@/components/ui/select";
import { SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { notify, confirmAction } from "@/composables/useFeedback";
import { ref, computed, watch } from "vue";
import TablePagination from "@/components/TablePagination.vue";
import SshCredentialForm from "@/components/SshCredentialForm.vue";
import { clientUpgradeApi } from "@/api/clientUpgrade";

const props = defineProps({
  modelValue: Boolean,
  groupName: { type: String, default: "" },
  frpsServerId: { type: Number, default: null },
});

const emit = defineEmits(["update:modelValue", "upgraded"]);

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});

const credentialId = ref(0);
const installPath = ref("/opt/frp");
const verifyMode = ref("agent_callback");
const scanning = ref(false);
const upgrading = ref(false);
const results = ref([]);
const resultJobId = ref(null);
const resultPagination = ref({ page: 1, page_size: 20, total: 0 });
async function loadResultPage(page = resultPagination.value.page) {
  if (!resultJobId.value) return;
  try {
    const data = await clientUpgradeApi.getJobResults(resultJobId.value, {
      page,
      page_size: resultPagination.value.page_size,
    });
    results.value = data.results || [];
    Object.assign(resultPagination.value, {
      page: data.page,
      page_size: data.page_size,
      total: data.total,
    });
  } catch (e) {
    notify("加载升级结果失败：" + e.message);
  }
}
async function resizeResults(size) {
  resultPagination.value.page_size = size;
  await loadResultPage(1);
}

const selectedIds = ref([]);
const jobSummary = ref("");
let pollTimer = null;

const STATUS_LABELS = {
  upgradeable: "可升级",
  latest: "已最新",
  unreachable: "不可达",
  auth_failed: "认证失败",
  permission_denied: "权限不足",
  not_ssh: "非 SSH",
  unsupported_platform: "不支持的平台",
  no_package: "无安装包",
  upgraded: "已升级",
  rolled_back: "已回滚",
  upgrade_failed: "升级失败",
  running_detached: "本地执行中",
  unknown_disconnected: "等待恢复",
};

function statusLabel(s) {
  return STATUS_LABELS[s] || s || "-";
}

function statusClass(s) {
  if (s === "upgradeable") return "text-green-700";
  if (s === "latest" || s === "upgraded" || s === "running_detached")
    return "text-blue-700";
  if (s === "rolled_back") return "text-amber-700";
  return "text-amber-700";
}

const upgradeableIds = computed(() =>
  results.value
    .filter((r) => r.upgradeable && r.rollback_capable)
    .map((r) => r.proxy_id),
);

const allUpgradeableSelected = computed(
  () =>
    upgradeableIds.value.length > 0 &&
    upgradeableIds.value.every((id) => selectedIds.value.includes(id)),
);

watch(visible, (v) => {
  if (!v) {
    stopPoll();
    resultJobId.value = null;
    resultPagination.value = { page: 1, page_size: 20, total: 0 };
    results.value = [];
    selectedIds.value = [];
    jobSummary.value = "";
  }
});

function close() {
  visible.value = false;
}

function toggleSelect(id) {
  const idx = selectedIds.value.indexOf(id);
  if (idx >= 0) selectedIds.value = selectedIds.value.filter((x) => x !== id);
  else selectedIds.value = [...selectedIds.value, id];
}

function toggleSelectAllUpgradeable() {
  if (allUpgradeableSelected.value) {
    selectedIds.value = [];
  } else {
    selectedIds.value = [...upgradeableIds.value];
  }
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function pollJob(jobId) {
  stopPoll();
  return new Promise((resolve) => {
    const tick = async () => {
      try {
        const data = await clientUpgradeApi.getJobResults(jobId, {
          page: 1,
          page_size: resultPagination.value.page_size,
        });
        const job = data.job;
        if (job.status !== "running" && job.status !== "queued") {
          stopPoll();
          resultJobId.value = jobId;
          Object.assign(resultPagination.value, {
            page: data.page,
            page_size: data.page_size,
            total: data.total,
          });
          results.value = data.results || [];
          jobSummary.value = job.summary || "";
          selectedIds.value = results.value
            .filter((r) => r.upgradeable && r.rollback_capable)
            .map((r) => r.proxy_id);
          resolve(data);
          return;
        }
        jobSummary.value = job.summary || "任务执行中...";
      } catch (e) {
        console.error(e);
      }
    };
    tick();
    pollTimer = setInterval(tick, 1500);
  });
}

async function runGroupScan() {
  if (!props.groupName || !props.frpsServerId || !credentialId.value) return;
  scanning.value = true;
  jobSummary.value = "";
  results.value = [];
  try {
    const job = await clientUpgradeApi.scanGroup(
      props.groupName,
      props.frpsServerId,
      {
        credential_id: credentialId.value,
        install_path: installPath.value,
      },
    );
    await pollJob(job.id);
  } catch (e) {
    notify(e.message || "扫描失败");
  } finally {
    scanning.value = false;
  }
}

async function runGroupUpgrade() {
  if (!selectedIds.value.length) return;
  const warnMsg = `将备份选中的 ${selectedIds.value.length} 个客户端的 frpc 二进制和现有配置文件，并在每台目标机本地脱离 SSH 会话执行升级。若 SSH 走 frpc 隧道，重启期间断联属于预期；目标机脚本会继续校验并在失败时回滚。${verifyMode.value === "skip" ? "\n\n注意：已跳过远程回调校验，断联后无法可靠证明代理已恢复。" : ""}\n\n确认升级？`;
  if (!(await confirmAction(warnMsg))) return;
  upgrading.value = true;
  try {
    const job = await clientUpgradeApi.upgradeGroup(
      props.groupName,
      props.frpsServerId,
      {
        credential_id: credentialId.value,
        install_path: installPath.value,
        proxy_ids: selectedIds.value,
        verify_mode: verifyMode.value,
        skip_remote_verify: verifyMode.value === "skip",
      },
    );
    await pollJob(job.id);
    emit("upgraded");
  } catch (e) {
    notify(e.message || "升级失败");
  } finally {
    upgrading.value = false;
  }
}
</script>
