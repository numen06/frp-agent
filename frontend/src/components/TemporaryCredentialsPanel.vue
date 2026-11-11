<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { temporaryCredentialsApi } from "@/api/managedHosts";
import { copyDeferredText, formatCredentialExpiry, formatTemporaryCredential } from "@/composables/useClipboard";
import { confirmAction, notify } from "@/composables/useFeedback";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import TablePagination from "@/components/TablePagination.vue";
import TemporaryCredentialDetails from "@/components/TemporaryCredentialDetails.vue";

const protocol = ref("all");
const rows = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const busy = ref(false);
const error = ref("");
const action = ref("");
const selected = ref(null);
const detail = computed(() => rows.value.find((row) => row.can_copy &&
  row.protocol === selected.value?.protocol && row.username === selected.value?.username));
const states = { active: "有效", used: "已使用", expired: "已过期", revoked: "已失效" };
let requestNumber = 0;
let timer;
let detailTrigger;
const formatDate = (value) => value ? new Date(value).toLocaleString("zh-CN") : "—";

function openDetail(row, trigger) {
  detailTrigger = trigger;
  selected.value = row;
}

function restoreDetailFocus(event) {
  if (!detailTrigger?.isConnected) return;
  event.preventDefault();
  detailTrigger.focus();
}

async function load(nextPage = page.value) {
  const number = ++requestNumber;
  busy.value = true;
  try {
    const result = await temporaryCredentialsApi.list({
      protocol: protocol.value === "all" ? undefined : protocol.value,
      page: nextPage,
      page_size: pageSize.value,
    });
    if (number !== requestNumber) return;
    rows.value = result.items;
    total.value = result.total;
    page.value = nextPage;
    error.value = "";
  } catch (err) {
    if (number === requestNumber) error.value = err.message;
  } finally {
    if (number === requestNumber) busy.value = false;
  }
}

async function copy(row, trigger) {
  action.value = row.username;
  try {
    await copyDeferredText(
      () => temporaryCredentialsApi.copy(row).then(formatTemporaryCredential),
      trigger,
    );
  } catch (err) {
    notify(err.message, "error");
    await load();
  } finally {
    action.value = "";
  }
}

async function revoke(row) {
  if (!(await confirmAction(`撤销“${row.target}”的这组临时凭据？`, { title: "撤销临时凭据", confirmText: "撤销", danger: true }))) return;
  action.value = row.username;
  try {
    await temporaryCredentialsApi.revoke(row);
    await load();
    notify("临时凭据已撤销", "success");
  } catch (err) {
    notify(err.message, "error");
  } finally {
    action.value = "";
  }
}

onMounted(() => {
  load();
  timer = setInterval(() => {
    if (!document.hidden && !busy.value && !action.value) load();
  }, 15000);
});
onUnmounted(() => {
  clearInterval(timer);
  ++requestNumber;
});
</script>

<template>
  <Card class="min-w-0 space-y-3 p-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h2 class="font-semibold">临时凭据</h2>
      <div class="flex items-center gap-2">
        <Select v-model="protocol" @update:model-value="load(1)">
          <SelectTrigger class="w-32" aria-label="筛选协议"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部协议</SelectItem>
            <SelectItem value="rdp">RDP</SelectItem>
            <SelectItem value="vnc">VNC</SelectItem>
          </SelectContent>
        </Select>
        <Button type="button" variant="outline" :disabled="busy" @click="load()">刷新</Button>
      </div>
    </div>
    <p v-if="error" role="alert" class="text-sm text-destructive">{{ error }}</p>
    <p v-else-if="!rows.length" role="status" class="text-sm text-muted-foreground">
      {{ busy ? "正在读取…" : "当前没有临时凭据记录。" }}
    </p>
    <ul v-if="rows.length" class="divide-y">
      <li v-for="row in rows" :key="`${row.protocol}:${row.username}`" class="grid min-w-0 gap-3 py-3 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)_auto]">
        <div class="min-w-0 space-y-1">
          <div class="flex flex-wrap items-center gap-2">
            <span class="font-medium break-all">{{ row.target }}</span>
            <span class="text-xs text-muted-foreground">{{ row.protocol.toUpperCase() }}</span>
            <span class="rounded border px-1.5 py-0.5 text-xs" :class="{ 'text-green-700 dark:text-green-400': row.status === 'active' }">{{ states[row.status] }}</span>
          </div>
          <p class="break-all text-xs"><span class="text-muted-foreground">地址 </span><code>{{ row.address }}</code></p>
          <p class="break-all text-xs"><span class="text-muted-foreground">账号 </span><code>{{ row.username }}</code></p>
          <p class="break-all text-xs text-muted-foreground">签发人 {{ row.owner }}</p>
        </div>
        <dl class="space-y-1 text-xs text-muted-foreground">
          <div><dt class="inline">有效至 </dt><dd class="inline">{{ formatCredentialExpiry(row.expires_at) }}</dd></div>
          <div v-if="row.invalidated_at"><dt class="inline">失效于 </dt><dd class="inline">{{ formatCredentialExpiry(row.invalidated_at) }}</dd></div>
          <div><dt class="inline">使用 </dt><dd class="inline">{{ row.uses }} 次 · 最近 {{ formatDate(row.last_used_at) }}</dd></div>
        </dl>
        <div class="flex flex-wrap items-center gap-2">
          <Button v-if="row.can_copy" type="button" size="sm" variant="outline" class="max-sm:min-h-11" @click="openDetail(row, $event.currentTarget)">连接详情</Button>
          <Button v-if="row.can_copy" type="button" size="sm" variant="outline" class="max-sm:min-h-11" :disabled="!!action" @click="copy(row, $event.currentTarget)">一键复制（含有效期）</Button>
          <Button v-if="row.status === 'active'" type="button" size="sm" variant="ghost" class="max-sm:min-h-11" :disabled="!!action" @click="revoke(row)">撤销</Button>
        </div>
      </li>
    </ul>
    <TablePagination :total="total" :page="page" :page-size="pageSize" @page-change="load" @page-size-change="(size) => { pageSize = size; load(1); }" />
    <Dialog :open="!!detail" @update:open="(open) => { if (!open) selected = null; }">
      <DialogContent v-if="detail" class="sm:h-[min(34rem,85dvh)] sm:max-w-lg" @close-auto-focus="restoreDetailFocus">
        <DialogHeader>
          <DialogTitle>临时凭据</DialogTitle>
          <DialogDescription class="break-words">{{ detail.protocol.toUpperCase() }} · {{ detail.target }}</DialogDescription>
        </DialogHeader>
        <Tabs default-value="credential" :unmount-on-hide="true" class="min-h-0 flex-1 gap-0">
          <div class="shrink-0 border-b px-4 sm:px-5">
            <TabsList variant="line" aria-label="临时凭据详情" class="flex h-auto w-full justify-start p-0">
              <TabsTrigger value="credential" class="flex-1 sm:flex-none">连接凭据</TabsTrigger>
              <TabsTrigger value="usage" class="flex-1 sm:flex-none">使用记录</TabsTrigger>
            </TabsList>
          </div>
          <TabsContent value="credential" data-slot="dialog-body" class="min-h-0 min-w-0 overflow-y-auto overscroll-contain p-4 sm:p-5">
            <TemporaryCredentialDetails :credential="detail" @refresh="load()" />
          </TabsContent>
          <TabsContent value="usage" data-slot="dialog-body" class="min-h-0 min-w-0 overflow-y-auto overscroll-contain p-4 sm:p-5">
            <dl class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-3 text-sm">
              <dt class="text-muted-foreground">状态</dt><dd>{{ states[detail.status] }}</dd>
              <dt class="text-muted-foreground">签发人</dt><dd class="break-all">{{ detail.owner }}</dd>
              <dt class="text-muted-foreground">签发时间</dt><dd>{{ formatDate(detail.issued_at) }}</dd>
              <dt class="text-muted-foreground">使用次数</dt><dd>{{ detail.uses }} 次</dd>
              <dt class="text-muted-foreground">最近使用</dt><dd>{{ formatDate(detail.last_used_at) }}</dd>
            </dl>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  </Card>
</template>
