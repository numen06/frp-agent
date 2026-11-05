<template>
  <div>
    <Card
      ><CardHeader
        ><h3 class="text-base font-semibold text-gray-900">API Key 管理</h3>
        <div class="flex w-full flex-wrap gap-2 md:w-auto md:justify-end">
          <Button
            type="button"
            class="flex-1 sm:flex-none"
            @click.stop="openCreateDialog"
            variant="outline"
            size="sm"
            ><svg
              class="h-4 w-4 shrink-0"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M12 5v14M5 12h14"
              />
            </svg>
            创建密钥
          </Button>
        </div></CardHeader
      >
      <form
        class="flex gap-2 border-b border-gray-200 p-4"
        @submit.prevent="loadKeys(1)"
      >
        <SearchField
          v-model="apiKeysStore.search"
          placeholder="输入名称或关键词搜索"
          label="搜索列表"
          @search="loadKeys(1)"
        ></SearchField
        ><Button type="submit" variant="outline" size="default">搜索</Button>
      </form>
      <div
        v-if="apiKeysStore.error"
        role="alert"
        class="flex flex-wrap items-center justify-between gap-2 p-4 text-sm text-destructive"
      >
        {{ apiKeysStore.error }}
        <Button type="button" variant="outline" @click="loadKeys()"
          >重试读取密钥</Button
        >
      </div>
      <div v-if="apiKeysStore.loading" class="p-5">
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
        <div class="hidden overflow-x-auto md:block">
          <Table class="w-full text-left"
            ><TableHeader
              ><TableRow
                ><TableHead style="min-width: 140px">描述</TableHead
                ><TableHead style="min-width: 200px">密钥</TableHead
                ><TableHead class="whitespace-nowrap" style="min-width: 160px"
                  >过期时间</TableHead
                ><TableHead style="min-width: 70px">状态</TableHead
                ><TableHead class="whitespace-nowrap" style="min-width: 160px"
                  >创建时间</TableHead
                ><TableHead class="whitespace-nowrap" style="min-width: 160px"
                  >最后使用</TableHead
                ><TableHead class="whitespace-nowrap" style="min-width: 180px"
                  >操作</TableHead
                ></TableRow
              ></TableHeader
            ><TableBody
              ><TableRow v-if="keys.length === 0 && !apiKeysStore.error"
                ><TableCell colspan="7" class="text-center">
                  暂无 API Key，点击上方按钮创建
                </TableCell></TableRow
              ><TableRow
                v-else
                v-for="key in keys"
                :key="key.id"
                :class="rowClass(key)"
                ><TableCell
                  ><div class="flex items-center gap-2">
                    <span class="truncate" :title="key.description">{{
                      key.description
                    }}</span
                    ><span
                      v-if="apiKeysStore.selectedKeyId === key.id"
                      class="inline-flex shrink-0 items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800"
                      >默认</span
                    >
                  </div></TableCell
                ><TableCell
                  ><div class="flex items-center gap-1">
                    <code class="flex-1 truncate text-xs text-gray-600">{{
                      key.key
                    }}</code
                    ><Button
                      class="inline-flex shrink-0 items-center justify-center transition-colors"
                      title="复制完整密钥"
                      @click.stop="copyFullKey(key, $event)"
                      type="button"
                      variant="ghost"
                      size="default"
                      aria-label="复制完整密钥"
                      ><svg
                        class="h-4 w-4"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                      >
                        <rect x="9" y="9" width="13" height="13" rx="2"></rect>
                        <path
                          d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"
                        ></path></svg
                    ></Button></div></TableCell
                ><TableCell class="whitespace-nowrap"
                  ><span v-if="key.expires_at">{{
                    formatDateTime(key.expires_at)
                  }}</span
                  ><span v-else class="text-gray-400">永不过期</span></TableCell
                ><TableCell
                  ><span
                    v-if="key.is_expired"
                    class="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800"
                    >已过期</span
                  ><span
                    v-else-if="!key.is_active"
                    class="inline-flex items-center rounded-full bg-gray-200 px-2.5 py-0.5 text-xs font-medium text-gray-700"
                    >已禁用</span
                  ><span
                    v-else
                    class="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800"
                    >正常</span
                  ></TableCell
                ><TableCell class="whitespace-nowrap">{{
                  formatDateTime(key.created_at)
                }}</TableCell
                ><TableCell class="whitespace-nowrap"
                  ><span v-if="key.last_used_at">{{
                    formatDateTime(key.last_used_at)
                  }}</span
                  ><span v-else class="text-gray-400">从未使用</span></TableCell
                ><TableCell class="whitespace-nowrap"
                  ><div class="flex items-center gap-1.5">
                    <Button
                      class="inline-flex items-center justify-center text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40"
                      :class="
                        apiKeysStore.selectedKeyId === key.id
                          ? 'border-blue-200 bg-blue-50 text-blue-700'
                          : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                      "
                      :disabled="
                        !key.is_active ||
                        key.is_expired ||
                        apiKeysStore.selectedKeyId === key.id
                      "
                      title="设为默认"
                      @click="setDefaultKey(key)"
                      type="button"
                      variant="ghost"
                      size="default"
                      aria-label="设为默认"
                      >默认</Button
                    ><Button
                      class="disabled:opacity-40"
                      :disabled="key.is_expired"
                      title="编辑"
                      @click="editKey(key)"
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      aria-label="编辑"
                      tooltip="编辑"
                      ><svg
                        class="h-4 w-4"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          d="M16.862 3.487a2.25 2.25 0 1 1 3.182 3.182L8.25 18.463 4 20l1.537-4.25 11.325-11.263z"
                        ></path></svg></Button
                    ><Button
                      title="删除"
                      @click="deleteKey(key)"
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      aria-label="删除"
                      tooltip="删除"
                      ><svg
                        class="h-4 w-4"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          d="M3 6h18M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m-1 0v14a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1V6m-4 0v14a1 1 0 0 0 1 1h2"
                        ></path></svg
                    ></Button></div></TableCell></TableRow></TableBody
          ></Table>
        </div>
        <div class="md:hidden">
          <p
            v-if="keys.length === 0 && !apiKeysStore.error"
            class="px-4 py-8 text-center text-sm text-gray-500"
          >
            暂无 API Key，点击上方按钮创建
          </p>
          <ul v-else class="mobile-record-list">
            <li
              v-for="key in keys"
              :key="key.id"
              class="mobile-record h-80"
              :class="rowClass(key)"
            >
              <div class="flex items-start gap-2">
                <span
                  class="mobile-record-title flex-1"
                  :title="key.description"
                  >{{ key.description }}</span
                ><span
                  v-if="apiKeysStore.selectedKeyId === key.id"
                  class="inline-flex shrink-0 items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800"
                  >默认</span
                ><span
                  v-if="key.is_expired"
                  class="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800"
                  >已过期</span
                ><span
                  v-else-if="!key.is_active"
                  class="inline-flex items-center rounded-full bg-gray-200 px-2.5 py-0.5 text-xs font-medium text-gray-700"
                  >已禁用</span
                ><span
                  v-else
                  class="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800"
                  >正常</span
                >
              </div>
              <div class="flex min-w-0 items-center gap-1">
                <code
                  class="min-w-0 flex-1 truncate text-xs text-muted-foreground"
                  >{{ key.key }}</code
                ><Button
                  title="复制完整密钥"
                  aria-label="复制完整密钥"
                  @click.stop="copyFullKey(key, $event)"
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  tooltip="复制完整密钥"
                  ><svg
                    class="h-4 w-4"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <rect x="9" y="9" width="13" height="13" rx="2"></rect>
                    <path
                      d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"
                    ></path></svg
                ></Button>
              </div>
              <dl class="grid grid-cols-1 gap-1 text-xs text-muted-foreground">
                <div class="flex justify-between gap-2">
                  <dt>过期</dt>
                  <dd class="text-right text-gray-700">
                    <span v-if="key.expires_at">{{
                      formatDateTime(key.expires_at)
                    }}</span
                    ><span v-else class="text-gray-400">永不过期</span>
                  </dd>
                </div>
                <div class="flex justify-between gap-2">
                  <dt>创建</dt>
                  <dd class="text-right text-gray-700">
                    {{ formatDateTime(key.created_at) }}
                  </dd>
                </div>
                <div class="flex justify-between gap-2">
                  <dt>最后使用</dt>
                  <dd class="text-right text-gray-700">
                    <span v-if="key.last_used_at">{{
                      formatDateTime(key.last_used_at)
                    }}</span
                    ><span v-else class="text-gray-400">从未使用</span>
                  </dd>
                </div>
              </dl>
              <div class="mt-auto flex items-center gap-2 border-t pt-3">
                <Button
                  class="flex-1 disabled:opacity-40 sm:flex-none"
                  :class="
                    apiKeysStore.selectedKeyId === key.id
                      ? 'border-blue-200 bg-blue-50 text-blue-700'
                      : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                  "
                  :disabled="
                    !key.is_active ||
                    key.is_expired ||
                    apiKeysStore.selectedKeyId === key.id
                  "
                  @click="setDefaultKey(key)"
                  type="button"
                  variant="outline"
                  size="sm"
                  >设为默认</Button
                ><Button
                  class="disabled:opacity-40"
                  :disabled="key.is_expired"
                  title="编辑"
                  aria-label="编辑"
                  @click="editKey(key)"
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  tooltip="编辑"
                  ><svg
                    class="h-4 w-4"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      d="M16.862 3.487a2.25 2.25 0 1 1 3.182 3.182L8.25 18.463 4 20l1.537-4.25 11.325-11.263z"
                    ></path></svg></Button
                ><Button
                  title="删除"
                  aria-label="删除"
                  @click="deleteKey(key)"
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  tooltip="删除"
                  ><svg
                    class="h-4 w-4"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      d="M3 6h18M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m-1 0v14a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1V6m-4 0v14a1 1 0 0 0 1 1h2"
                    ></path></svg
                ></Button>
              </div>
            </li>
          </ul>
        </div> </template
    ></Card>
    <div class="rounded-xl border border-gray-200 bg-white p-4">
      <TablePagination
        :total="apiKeysStore.pagination.total"
        :page="apiKeysStore.pagination.page"
        :page-size="apiKeysStore.pagination.page_size"
        @page-change="loadKeys"
        @page-size-change="apiKeysStore.resize"
      />
    </div>
    <!-- 创建/编辑对话框 --><Dialog
      v-if="dialogVisible"
      :open="true"
      @update:open="
        (open) => {
          if (!open) {
            closeDialog();
          }
        }
      "
      ><DialogContent class="sm:max-w-lg" :aria-describedby="undefined"
        ><DialogHeader
          ><DialogTitle>{{
            editingKey ? "编辑 API Key" : "创建 API Key"
          }}</DialogTitle></DialogHeader
        >
        <div
          data-slot="dialog-body"
          class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
        >
          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >描述 <span class="text-red-600">*</span></label
            ><Input
              type="text"
              class="block w-full"
              v-model="formData.description"
              placeholder="请输入密钥描述，用于标识用途"
              maxlength="200"
              ref="descInput"
            ></Input>
          </div>
          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >过期时间</label
            ><Input
              type="datetime-local"
              class="mb-2 block w-full"
              v-model="formData.expires_at"
            ></Input>
            <div class="flex flex-wrap gap-1">
              <Button
                type="button"
                class="inline-flex items-center justify-center gap-1 text-xs font-medium transition-colors"
                @click="setExpiresDays(7)"
                variant="ghost"
                size="default"
                >7天</Button
              ><Button
                type="button"
                class="inline-flex items-center justify-center gap-1 text-xs font-medium transition-colors"
                @click="setExpiresDays(30)"
                variant="ghost"
                size="default"
                >30天</Button
              ><Button
                type="button"
                class="inline-flex items-center justify-center gap-1 text-xs font-medium transition-colors"
                @click="setExpiresDays(90)"
                variant="ghost"
                size="default"
                >90天</Button
              ><Button
                type="button"
                class="inline-flex items-center justify-center gap-1 text-xs font-medium transition-colors"
                @click="setExpiresDays(180)"
                variant="ghost"
                size="default"
                >180天</Button
              ><Button
                type="button"
                class="inline-flex items-center justify-center gap-1 text-xs font-medium transition-colors"
                @click="setExpiresDays(365)"
                variant="ghost"
                size="default"
                >1年</Button
              ><Button
                type="button"
                class="inline-flex items-center justify-center gap-1 text-xs font-medium transition-colors"
                @click="clearExpiresAt"
                variant="ghost"
                size="default"
                >永不过期</Button
              >
            </div>
            <small class="mt-1 block text-xs text-gray-500"
              >留空表示永不过期，或使用快捷选项</small
            >
          </div>
          <div v-if="editingKey" class="mb-0">
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >状态</label
            ><label
              class="flex cursor-pointer items-center gap-2 text-sm text-gray-700"
            >
              <Checkbox class="w-4" v-model="formData.is_active"></Checkbox
              ><span>启用</span>
            </label>
          </div>
        </div>
        <DialogFooter
          ><Button
            type="button"
            class="inline-flex w-full items-center justify-center gap-2 text-sm font-medium transition-colors sm:w-auto"
            @click="closeDialog"
            variant="ghost"
            size="default"
            >取消</Button
          ><Button
            type="button"
            class="w-full sm:w-auto"
            @click="saveKey"
            :disabled="!formData.description?.trim() || saving"
            variant="default"
            size="default"
            >{{ saving ? "保存中..." : "保存" }}</Button
          ></DialogFooter
        ></DialogContent
      ></Dialog
    ><!-- 创建成功对话框（显示完整密钥） --><Dialog
      v-if="showKeyDialog"
      :open="true"
      @update:open="
        (open) => {
          if (!open) {
            showKeyDialog = false;
          }
        }
      "
      ><DialogContent class="sm:max-w-lg" :aria-describedby="undefined"
        ><DialogHeader
          ><DialogTitle>API Key 创建成功</DialogTitle></DialogHeader
        >
        <div
          data-slot="dialog-body"
          class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
        >
          <div
            class="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
            role="alert"
          >
            <strong class="font-semibold">重要提示：</strong
            >请妥善保管此密钥，创建后将无法再次查看完整密钥！
          </div>
          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >描述</label
            >
            <p
              class="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900"
            >
              {{ createdKeyData?.description }}
            </p>
          </div>
          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >API Key</label
            >
            <div class="flex min-w-0 flex-col gap-2 sm:flex-row">
              <Input
                type="text"
                class="min-w-0 w-full font-mono sm:flex-1"
                readonly
                ref="keyInput"
                :model-value="createdKeyData?.key"
              ></Input
              ><Button
                class="w-full shrink-0 sm:w-auto"
                type="button"
                aria-label="复制 API Key"
                @click.stop="copyCreatedKey($event)"
                variant="outline"
                size="default"
                ><svg
                  class="h-4 w-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <rect x="9" y="9" width="13" height="13" rx="2"></rect>
                  <path
                    d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"
                  ></path>
                </svg>
                复制
              </Button>
            </div>
          </div>
          <div class="mb-0">
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >使用方式</label
            >
            <div class="rounded-lg border border-gray-200 bg-gray-50 p-4">
              <div class="mb-3 last:mb-0">
                <strong class="text-sm font-semibold text-gray-900"
                  >Header 认证</strong
                >
                <div class="mt-1 break-all">
                  <code class="text-xs text-gray-600"
                    >Authorization: Bearer {{ createdKeyData?.key }}</code
                  >
                </div>
              </div>
              <div>
                <strong class="text-sm font-semibold text-gray-900"
                  >URL 参数</strong
                >
                <div class="mt-1 break-all">
                  <code class="text-xs text-gray-600"
                    >?api_key={{ createdKeyData?.key }}</code
                  >
                </div>
              </div>
            </div>
          </div>
        </div>
        <DialogFooter
          ><Button
            type="button"
            class="w-full sm:w-auto"
            @click="showKeyDialog = false"
            variant="default"
            size="default"
            >我已保存</Button
          ></DialogFooter
        ></DialogContent
      ></Dialog
    ><!-- 提示消息 -->
  </div>
</template>

<script setup>
import SearchField from "@/components/SearchField.vue";
import { CardHeader } from "@/components/ui/card";
import ActionMenu from "@/components/ActionMenu.vue";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { Table } from "@/components/ui/table";
import { TableBody } from "@/components/ui/table";
import { TableCell } from "@/components/ui/table";
import { TableHeader } from "@/components/ui/table";
import { TableRow } from "@/components/ui/table";
import { TableHead } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { confirmAction } from "@/composables/useFeedback";
import TablePagination from "@/components/TablePagination.vue";
import { ref, computed, onMounted, nextTick } from "vue";
import { apiKeysApi } from "@/api/apiKeys";
import { useApiKeysStore } from "@/stores/apiKeys";
import { copyText } from "@/composables/useClipboard";

const apiKeysStore = useApiKeysStore();
const loading = ref(false);
const saving = ref(false);
const showCreateDialog = ref(false);
const showEditDialog = ref(false);
const showKeyDialog = ref(false);
const editingKey = ref(null);
const createdKeyData = ref(null);
const keyInput = ref(null);
const descInput = ref(null);

const formData = ref({
  description: "",
  expires_at: "",
  is_active: true,
});

const keys = computed(() => apiKeysStore.keys || []);

const dialogVisible = computed(
  () => showCreateDialog.value || showEditDialog.value,
);

const rowClass = (key) => {
  if (key.is_expired) return "bg-red-50/40";
  if (!key.is_active) return "bg-gray-50/50";
  return "";
};

const formatDateTime = (dateStr) => {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
};

// Toast

// 加载列表
const loadKeys = async (page = apiKeysStore.pagination.page) => {
  loading.value = true;
  try {
    await apiKeysStore.loadKeys(page);
  } catch (e) {
    console.error("加载 API Key 列表失败:", e);
    notify("加载失败", "error");
  } finally {
    loading.value = false;
  }
};

// 复制完整密钥（从列表）
const copyFullKey = async (key, event) => {
  try {
    const fullKey = await apiKeysStore.resolveFullKey(key.id);
    if (!fullKey) {
      notify("无法获取完整密钥", "error");
      return;
    }
    await copyText(fullKey, event);
  } catch (e) {
    notify("复制失败: " + (e.response?.data?.detail || e.message), "error");
  }
};

// 复制创建后的密钥
const copyCreatedKey = async (event) => {
  if (createdKeyData.value?.key) {
    await copyText(createdKeyData.value.key, event);
  }
};

// 设为默认
const setDefaultKey = (key) => {
  if (!key.is_active || key.is_expired) return;
  apiKeysStore.setDefaultKey(key.id);
  notify(`已将 "${key.description}" 设为默认`, "success");
};

// 过期时间
const setExpiresDays = (days) => {
  const d = new Date();
  d.setDate(d.getDate() + days);
  const pad = (n) => String(n).padStart(2, "0");
  formData.value.expires_at = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

const clearExpiresAt = () => {
  formData.value.expires_at = "";
};

// 对话框操作
const openCreateDialog = () => {
  showCreateDialog.value = true;
  nextTick(() => descInput.value?.$el?.focus());
};

const closeDialog = () => {
  showCreateDialog.value = false;
  showEditDialog.value = false;
  editingKey.value = null;
  formData.value = { description: "", expires_at: "", is_active: true };
};

const editKey = (key) => {
  editingKey.value = key;
  formData.value = {
    description: key.description,
    expires_at: key.expires_at
      ? new Date(key.expires_at).toISOString().slice(0, 16)
      : "",
    is_active: key.is_active,
  };
  showEditDialog.value = true;
  nextTick(() => descInput.value?.$el?.focus());
};

// 保存
const saveKey = async () => {
  if (!formData.value.description?.trim()) return;
  saving.value = true;
  try {
    const data = {
      description: formData.value.description.trim(),
      expires_at: formData.value.expires_at
        ? new Date(formData.value.expires_at).toISOString()
        : null,
    };

    if (editingKey.value) {
      data.is_active = formData.value.is_active;
      await apiKeysApi.update(editingKey.value.id, data);
      await loadKeys();
      closeDialog();
      notify("更新成功");
    } else {
      const result = await apiKeysApi.create(data);
      if (!result?.id || !result?.key) {
        notify("创建失败：服务器返回数据不完整", "error");
        return;
      }
      const keyValue = String(result.key).trim();
      const idNum = Number(result.id);
      if (keyValue === String(idNum) || keyValue.length < 20) {
        notify("创建失败：服务器返回数据异常", "error");
        return;
      }
      localStorage.setItem(`api_key_${idNum}`, keyValue);
      localStorage.setItem(`api_key_${String(idNum)}`, keyValue);

      createdKeyData.value = result;
      closeDialog();
      showKeyDialog.value = true;
      if (!apiKeysStore.selectedKeyId) {
        apiKeysStore.setDefaultKey(idNum);
        notify("已自动设为默认密钥");
      }
      await loadKeys();
    }
  } catch (e) {
    console.error("保存失败:", e);
    notify("保存失败: " + e.message, "error");
  } finally {
    saving.value = false;
  }
};

// 删除
const deleteKey = async (key) => {
  if (
    !(await confirmAction(
      `确定要删除密钥 "${key.description}" 吗？此操作不可恢复。`,
    ))
  )
    return;
  try {
    await apiKeysApi.delete(key.id);
    if (apiKeysStore.selectedKeyId === key.id) {
      apiKeysStore.setDefaultKey(null);
    }
    await loadKeys();
    notify("删除成功");
  } catch (e) {
    notify("删除失败: " + e.message, "error");
  }
};

onMounted(() => {
  loadKeys();
});
</script>
