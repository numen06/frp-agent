<script setup>
import { computed, ref, watch } from "vue";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import SearchField from "@/components/SearchField.vue";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { managedHostsApi } from "@/api/managedHosts";
const props = defineProps({ open: Boolean });
const emit = defineEmits(["update:open", "imported"]);
const rows = ref([]),
  selected = ref([]),
  busy = ref(false),
  importing = ref(false),
  error = ref(""),
  scanned = ref(false),
  search = ref(""),
  filter = ref("available"),
  notice = ref("");
let requestId = 0;
const visible = computed(() =>
  rows.value.filter(
    (r) =>
      (filter.value === "all" ||
        (filter.value === "available"
          ? r.available && !r.existing_host_id
          : Boolean(r.existing_host_id))) &&
      `${r.name} ${r.server_name} ${r.address} ${r.host_type}`
        .toLowerCase()
        .includes(search.value.toLowerCase()),
  ),
);
const selectable = computed(() =>
  visible.value.filter((r) => r.available && !r.existing_host_id),
);
const allSelected = computed(
  () =>
    selectable.value.length > 0 &&
    selectable.value.every((r) => selected.value.includes(r.proxy_id)),
);
const availableCount = computed(
  () => rows.value.filter((r) => r.available && !r.existing_host_id).length,
);
function toggle(id, checked) {
  if (checked && selected.value.length >= 100 && !selected.value.includes(id)) {
    error.value = "单次最多加入 100 台，请分批操作";
    return;
  }
  selected.value = checked
    ? [...new Set([...selected.value, id])]
    : selected.value.filter((v) => v !== id);
}
function toggleVisible(checked) {
  for (const r of selectable.value) toggle(r.proxy_id, checked);
}
async function scan() {
  const id = ++requestId;
  busy.value = true;
  error.value = "";
  selected.value = [];
  rows.value = [];
  scanned.value = false;
  try {
    const result = await managedHostsApi.discover();
    if (id === requestId && props.open) {
      rows.value = result.items;
      scanned.value = true;
    }
  } catch (e) {
    if (id === requestId && props.open) error.value = e.message;
  } finally {
    if (id === requestId) busy.value = false;
  }
}
async function importSelected() {
  if (busy.value || importing.value || !selected.value.length) return;
  importing.value = true;
  error.value = "";
  try {
    const result = await managedHostsApi.importDiscovered(selected.value);
    for (const r of rows.value)
      if (selected.value.includes(r.proxy_id)) {
        r.existing_host_id = true;
        r.available = false;
        r.message = "已加入，未激活";
      }
    selected.value = [];
    notice.value = `已导入 ${result.created_ids.length} 台未激活主机${result.existing_ids.length ? `，跳过 ${result.existing_ids.length} 台已有主机` : ""}。请在主机列表配置凭据，再进行连接测试。`;
    emit("imported");
  } catch (e) {
    error.value = e.message;
  } finally {
    importing.value = false;
  }
}
function close(open) {
  if (importing.value) return;
  emit("update:open", open);
}
watch(
  () => props.open,
  (open) => {
    if (open) {
      notice.value = "";
      search.value = "";
      filter.value = "available";
      scan();
    } else {
      ++requestId;
      busy.value = false;
    }
  },
);
</script>
<template>
  <Dialog :open="open" @update:open="close"
    ><DialogContent class="sm:max-w-4xl" :show-close-button="!importing">
      <DialogHeader
        ><DialogTitle>代理导入</DialogTitle
        ><DialogDescription
          >检测已登记 TCP 代理的实际 SSH、RDP 或 Portainer
          协议，不按名称或端口号判断。导入后为“未激活”，配置凭据并通过测试才启用；不会自动授权用户。同一入口自动去重，单次最多导入
          100 台。</DialogDescription
        ></DialogHeader
      >
      <div class="min-h-0 flex-1 space-y-3 overflow-y-auto p-4 sm:p-5">
        <form class="grid grid-cols-2 gap-2 sm:flex" @submit.prevent>
          <SearchField
            v-model="search"
            label="搜索检测结果"
            placeholder="名称、节点或地址"
            class="col-span-2 min-w-0 sm:flex-1"
          /><Select v-model="filter"
            ><SelectTrigger aria-label="检测结果状态" class="w-full sm:w-40"
              ><SelectValue /></SelectTrigger
            ><SelectContent
              ><SelectItem value="available">可加入</SelectItem
              ><SelectItem value="all">全部结果</SelectItem
              ><SelectItem value="existing">已加入</SelectItem></SelectContent
            ></Select
          ><Button variant="outline" :disabled="busy || importing" @click="scan"
            >重新检测</Button
          >
        </form>
        <p
          v-if="error"
          role="alert"
          class="break-words text-sm text-destructive"
        >
          {{ error }}
        </p>
        <p
          v-if="notice"
          role="status"
          class="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800"
        >
          {{ notice }}
        </p>
        <p
          v-if="busy"
          role="status"
          class="py-8 text-center text-sm text-muted-foreground"
        >
          正在检查穿透服务器、代理及服务协议，请稍候…
        </p>
        <template v-else-if="scanned">
          <div
            class="flex flex-wrap items-center justify-between gap-2 text-sm"
          >
            <span
              >共 {{ rows.length }} 条候选 · {{ availableCount }} 条可加入</span
            ><label class="flex min-h-11 items-center gap-2"
              ><Checkbox
                :model-value="allSelected"
                :disabled="!selectable.length || importing"
                @update:model-value="toggleVisible"
              />选择当前筛选结果</label
            >
          </div>
          <div class="space-y-2">
            <article
              v-for="row in visible"
              :key="row.proxy_id"
              class="flex min-w-0 gap-3 rounded-lg border p-3"
              :data-discovery-id="row.proxy_id"
            >
              <Checkbox
                class="mt-1 shrink-0"
                :aria-label="`选择 ${row.name}`"
                :disabled="
                  !row.available || Boolean(row.existing_host_id) || importing
                "
                :model-value="selected.includes(row.proxy_id)"
                @update:model-value="(checked) => toggle(row.proxy_id, checked)"
              />
              <div class="min-w-0 flex-1 space-y-1">
                <div class="flex items-start justify-between gap-2">
                  <h3
                    class="line-clamp-2 break-all text-sm font-medium"
                    :title="row.name"
                  >
                    {{ row.name }}
                  </h3>
                  <span class="shrink-0 text-xs text-muted-foreground">{{
                    row.existing_host_id
                      ? "已加入"
                      : row.available
                        ? "可加入"
                        : "不可用"
                  }}</span>
                </div>
                <p class="break-all text-xs text-muted-foreground">
                  {{
                    { ssh: "SSH", rdp: "RDP", docker: "Portainer" }[
                      row.host_type
                    ] || "未确认"
                  }}
                  · {{ row.server_name }} · {{ row.address }}:{{ row.port }}
                </p>
                <p
                  class="break-words text-xs"
                  :class="
                    !row.available && !row.existing_host_id
                      ? 'text-destructive'
                      : 'text-muted-foreground'
                  "
                >
                  {{ row.message }}
                </p>
              </div>
            </article>
          </div>
          <p
            v-if="!visible.length"
            class="py-8 text-center text-sm text-muted-foreground"
          >
            {{
              rows.length
                ? "当前筛选下没有结果，可切换“全部结果”查看原因。"
                : "没有可检测的 TCP 代理。"
            }}
          </p>
        </template>
      </div>
      <DialogFooter class="flex-wrap border-t pt-3"
        ><Button variant="outline" :disabled="importing" @click="close(false)"
          >关闭</Button
        ><Button
          :disabled="busy || importing || !selected.length"
          @click="importSelected"
          >{{
            importing
              ? "正在加入…"
              : `批量导入${selected.length ? `（${selected.length}）` : ""}`
          }}</Button
        ></DialogFooter
      >
    </DialogContent></Dialog
  >
</template>
