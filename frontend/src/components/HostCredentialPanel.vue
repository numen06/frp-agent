<template>
  <Card
    ><CardHeader
      ><div>
        <h2 class="font-semibold">凭证管理</h2>
        <p class="mt-1 text-xs text-gray-500">
          密码、私钥和 API Key
          加密保存，仅显示设置状态。共享凭证的修改会影响使用它的主机。
        </p>
      </div>
      <Button
        type="button"
        @click="openEditor()"
        variant="default"
        size="default"
        >新增凭证</Button
      ></CardHeader
    ><ToggleGroup
      aria-label="凭证类型"
      type="single"
      :model-value="kind"
      @update:model-value="
        (value) => {
          if (value) kind = value;
        }
      "
      variant="outline"
      class="mx-4 mt-4 max-w-[calc(100%-2rem)] flex-wrap justify-start"
      ><ToggleGroupItem
        v-for="option in kinds"
        :key="option.key"
        :value="option.key"
        >{{ option.label }}</ToggleGroupItem
      ></ToggleGroup
    >
    <form class="flex gap-2 border-b p-4 sm:p-5" @submit.prevent="list.load(1)">
      <SearchField
        v-model="list.search.value"
        placeholder="搜索凭证名称或用户名"
        label="搜索凭证"
        @search="list.load(1)"
      ></SearchField
      ><Button type="submit" variant="outline" size="default">搜索</Button>
    </form>
    <p
      v-if="list.error.value || error"
      role="alert"
      class="px-4 pb-4 text-sm text-red-600"
    >
      {{ list.error.value || error }}
    </p>
    <p v-if="notice" role="status" class="px-4 pb-4 text-sm text-emerald-700">
      {{ notice }}
    </p>
    <p
      v-if="list.loading.value"
      role="status"
      class="p-6 text-center text-sm text-gray-500"
    >
      正在加载凭证…
    </p>
    <template v-else>
      <div class="hidden overflow-x-auto md:block">
        <Table class="w-full text-left"
          ><TableHeader
            ><TableRow
              ><TableHead>名称</TableHead><TableHead>用户名</TableHead
              ><TableHead>认证方式</TableHead><TableHead>已设置内容</TableHead
              ><TableHead>操作</TableHead></TableRow
            ></TableHeader
          ><TableBody
            ><TableRow v-for="row in list.items.value" :key="row.id"
              ><TableCell class="break-all font-medium">{{
                row.name
              }}</TableCell
              ><TableCell class="break-all">{{ row.username || "—" }}</TableCell
              ><TableCell>{{ authLabel(row.auth_type) }}</TableCell
              ><TableCell>{{ savedFields(row) }}</TableCell
              ><TableCell
                ><div class="flex gap-2">
                  <Button
                    type="button"
                    @click="openEditor(row)"
                    variant="outline"
                    size="sm"
                    >编辑</Button
                  ><Button
                    type="button"
                    class="text-red-600"
                    @click="deleting = row"
                    variant="outline"
                    size="sm"
                    >删除</Button
                  >
                </div></TableCell
              ></TableRow
            ></TableBody
          ></Table
        >
      </div>
      <div class="mobile-record-list md:hidden">
        <article
          v-for="row in list.items.value"
          :key="row.id"
          class="mobile-record h-60"
        >
          <h3 class="mobile-record-title" :title="row.name">{{ row.name }}</h3>
          <p
            class="truncate text-sm text-muted-foreground"
            :title="row.username"
          >
            {{ row.username || "无用户名" }} · {{ authLabel(row.auth_type) }}
          </p>
          <p class="line-clamp-2 text-xs text-muted-foreground">
            已设置：{{ savedFields(row) }}
          </p>
          <div class="mt-auto flex gap-2 border-t pt-3">
            <Button
              type="button"
              class="flex-1"
              @click="openEditor(row)"
              variant="outline"
              size="default"
              >编辑</Button
            ><Button
              type="button"
              class="flex-1 text-red-600"
              @click="deleting = row"
              variant="outline"
              size="default"
              >删除</Button
            >
          </div>
        </article>
      </div>
      <p
        v-if="!list.items.value.length && !list.error.value && !error"
        class="p-8 text-center text-sm text-gray-500"
      >
        暂无凭证
      </p>
    </template>
    <div class="border-t border-gray-200 p-4">
      <TablePagination
        :total="list.pagination.total"
        :page="list.pagination.page"
        :page-size="list.pagination.page_size"
        @page-change="list.load"
        @page-size-change="list.resize"
      /></div></Card
  ><Dialog
    v-if="editorOpen"
    :open="true"
    @update:open="
      (open) => {
        if (!saving) {
          editorOpen = open;
        }
      }
    "
    ><DialogContent
      class="sm:max-w-2xl"
      :aria-describedby="undefined"
      :show-close-button="!saving"
      @escape-key-down="
        (e) => {
          if (saving) e.preventDefault();
        }
      "
      @interact-outside="
        (e) => {
          if (saving) e.preventDefault();
        }
      "
      ><DialogHeader
        ><DialogTitle>{{
          editing ? "编辑凭证" : "新增凭证"
        }}</DialogTitle></DialogHeader
      >
      <div
        data-slot="dialog-body"
        class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
      >
        <form
          id="host-credential-form"
          class="space-y-4"
          @submit.prevent="save"
        >
          <p class="rounded-lg bg-blue-50 p-3 text-sm text-blue-800">
            {{
              kind === "ssh"
                ? "SSH 与 RDP 共用此凭证库；RDP 仅支持密码认证。"
                : "用于连接 Portainer，不是平台 API Key。"
            }}{{ editing ? " 敏感内容不会回显，留空保留原值。" : "" }}
          </p>
          <label class="block text-sm"
            >凭证名称<Input
              v-model.trim="form.name"
              required
              maxlength="100"
              class="mt-1 w-full"
              autocomplete="off"
            ></Input></label
          ><label class="block text-sm"
            >认证方式<Select v-model="form.auth_type"
              ><SelectTrigger
                class="w-full mt-1"
                aria-label="认证方式"
                ><SelectValue placeholder="请选择"></SelectValue></SelectTrigger
              ><SelectContent
                ><SelectItem value="password">用户名 / 密码</SelectItem
                ><SelectItem v-if="kind === 'ssh'" value="private_key"
                  >SSH 私钥</SelectItem
                ><SelectItem v-else value="api_key"
                  >Portainer API Key</SelectItem
                ></SelectContent
              ></Select
            ></label
          ><label
            v-if="kind === 'ssh' || form.auth_type === 'password'"
            class="block text-sm"
            >登录用户名<Input
              v-model.trim="form.username"
              required
              maxlength="100"
              class="mt-1 w-full"
              autocomplete="off"
            ></Input
          ></label>
          <div v-for="field in secretFields" :key="field.key" class="space-y-2">
            <label class="block text-sm"
              >{{ field.label
              }}<span v-if="editing" class="ml-2 text-xs text-gray-500">{{
                editing[`has_${field.key}`] ? "已设置；留空保留" : "未设置"
              }}</span
              ><Textarea
                v-if="field.rows"
                v-model="form[field.key]"
                :rows="field.rows"
                :aria-label="field.label"
                :disabled="form.clear[field.key]"
                class="mt-1 w-full font-mono"
                autocomplete="off"
                spellcheck="false"
              ></Textarea
              ><Input
                v-else
                v-model="form[field.key]"
                type="password"
                :aria-label="field.label"
                :disabled="form.clear[field.key]"
                class="mt-1 w-full"
                autocomplete="new-password"
              ></Input> </label
            ><Button as-child variant="outline"
              ><label v-if="field.key === 'private_key'"
                >上传私钥<input
                  type="file"
                  class="sr-only"
                  aria-label="上传 SSH 私钥"
                  @change="readPrivateKey" /></label></Button
            ><label
              v-if="field.optional && editing?.[`has_${field.key}`]"
              class="flex items-center gap-2 text-sm text-gray-600"
              ><Checkbox v-model="form.clear[field.key]"></Checkbox
              >清除已保存的{{ field.label }}</label
            >
          </div>
          <p v-if="editorError" role="alert" class="text-sm text-red-600">
            {{ editorError }}
          </p>
        </form>
      </div>
      <DialogFooter
        ><Button
          type="button"
          :disabled="saving"
          @click="editorOpen = false"
          variant="outline"
          size="default"
          >取消</Button
        ><Button
          type="submit"
          form="host-credential-form"
          :disabled="saving"
          variant="default"
          size="default"
          >{{ saving ? "保存中…" : "保存凭证" }}</Button
        ></DialogFooter
      ></DialogContent
    ></Dialog
  ><Dialog
    v-if="!!deleting"
    :open="true"
    @update:open="
      (open) => {
        if (!saving) {
          ((value) => {
            if (!value) deleting = null;
          })(open);
        }
      }
    "
    ><DialogContent
      class="sm:max-w-xl"
      :aria-describedby="undefined"
      :show-close-button="!saving"
      @escape-key-down="
        (e) => {
          if (saving) e.preventDefault();
        }
      "
      @interact-outside="
        (e) => {
          if (saving) e.preventDefault();
        }
      "
      ><DialogHeader><DialogTitle>删除凭证</DialogTitle></DialogHeader>
      <div
        data-slot="dialog-body"
        class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
      >
        <p class="break-all text-sm">
          确定删除凭证“{{ deleting?.name }}”？删除后不可恢复。
        </p>
        <p class="mt-3 text-sm text-gray-500">
          正在被主机或代理客户端使用的凭证不能删除，请先更换凭证；运行中的扫描 /
          升级任务结束后才能删除。
        </p>
        <p v-if="deleteError" role="alert" class="mt-3 text-sm text-red-600">
          {{ deleteError }}
        </p>
      </div>
      <DialogFooter
        ><Button
          type="button"
          :disabled="saving"
          @click="deleting = null"
          variant="outline"
          size="default"
          >取消</Button
        ><Button
          type="button"
          :disabled="saving"
          @click="remove"
          variant="destructive"
          size="default"
          >{{ saving ? "删除中…" : "确认删除" }}</Button
        ></DialogFooter
      ></DialogContent
    ></Dialog
  >
</template>

<script setup>
import SearchField from "@/components/SearchField.vue";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { CardHeader } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { SelectContent } from "@/components/ui/select";
import { SelectItem } from "@/components/ui/select";
import { SelectTrigger } from "@/components/ui/select";
import { SelectValue } from "@/components/ui/select";
import { Table } from "@/components/ui/table";
import { TableBody } from "@/components/ui/table";
import { TableCell } from "@/components/ui/table";
import { TableHeader } from "@/components/ui/table";
import { TableRow } from "@/components/ui/table";
import { TableHead } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { computed, onMounted, reactive, ref, watch } from "vue";
import TablePagination from "./TablePagination.vue";
import { usePagedList } from "@/composables/usePagedList";
import { sshCredentialsApi } from "@/api/sshCredentials";
import { dockerCredentialsApi } from "@/api/managedHosts";

const emit = defineEmits(["changed"]);
const kinds = [
  { key: "ssh", label: "SSH / RDP" },
  { key: "docker", label: "Docker / Portainer" },
];
const kind = ref("ssh");
const sshList = usePagedList(sshCredentialsApi.list),
  dockerList = usePagedList(dockerCredentialsApi.list);
const list = computed(() => (kind.value === "ssh" ? sshList : dockerList));
const api = computed(() =>
  kind.value === "ssh" ? sshCredentialsApi : dockerCredentialsApi,
);
const editorOpen = ref(false),
  editing = ref(null),
  deleting = ref(null),
  saving = ref(false);
const error = ref(""),
  editorError = ref(""),
  deleteError = ref(""),
  notice = ref("");
let editorRequest = 0;
const form = reactive({
  name: "",
  username: "",
  auth_type: "",
  password: "",
  private_key: "",
  passphrase: "",
  sudo_password: "",
  api_key: "",
  ca_cert: "",
  clear: {},
});
const labels = {
  password: "密码",
  private_key: "私钥",
  passphrase: "私钥口令",
  sudo_password: "sudo 密码",
  api_key: "API Key",
  ca_cert: "CA 证书",
};
const secretFields = computed(() => {
  const keys = [
    form.auth_type === "password"
      ? "password"
      : kind.value === "ssh"
        ? "private_key"
        : "api_key",
  ];
  if (kind.value === "ssh") {
    if (form.auth_type === "private_key") keys.push("passphrase");
    keys.push("sudo_password");
  } else keys.push("ca_cert");
  return keys.map((key) => ({
    key,
    label: labels[key],
    rows: ["private_key", "ca_cert"].includes(key) ? 5 : 0,
    optional: ["passphrase", "sudo_password", "ca_cert"].includes(key),
  }));
});
const authLabel = (type) =>
  ({
    password: "用户名 / 密码",
    private_key: "SSH 私钥",
    api_key: "Portainer API Key",
  })[type] || type;
const savedFields = (row) =>
  Object.entries(labels)
    .filter(([key]) => row[`has_${key}`])
    .map(([, label]) => label)
    .join("、") || "未设置";
function openEditor(row = null) {
  editorRequest++;
  editing.value = row;
  editorError.value = "";
  notice.value = "";
  Object.assign(form, {
    name: row?.name || "",
    username: row?.username || (kind.value === "ssh" ? "root" : ""),
    auth_type:
      row?.auth_type || (kind.value === "ssh" ? "password" : "api_key"),
    password: "",
    private_key: "",
    passphrase: "",
    sudo_password: "",
    api_key: "",
    ca_cert: "",
    clear: {},
  });
  editorOpen.value = true;
}
async function save() {
  if (saving.value) return;
  editorError.value = "";
  const primary =
    form.auth_type === "password"
      ? "password"
      : kind.value === "ssh"
        ? "private_key"
        : "api_key";
  if (!form[primary] && !editing.value?.[`has_${primary}`]) {
    editorError.value = `请填写${labels[primary]}`;
    return;
  }
  const payload = { name: form.name, auth_type: form.auth_type };
  if (kind.value === "ssh" || form.auth_type === "password")
    payload.username = form.username;
  for (const field of secretFields.value) {
    if (field.optional && form.clear[field.key]) payload[field.key] = "";
    else if (form[field.key]) payload[field.key] = form[field.key];
  }
  saving.value = true;
  try {
    if (editing.value) await api.value.update(editing.value.id, payload);
    else await api.value.create(payload);
    editorOpen.value = false;
    notice.value = "凭证已保存";
    await list.value.load();
    emit("changed");
  } catch (e) {
    editorError.value = e.message;
  } finally {
    saving.value = false;
  }
}
async function remove() {
  if (!deleting.value || saving.value) return;
  saving.value = true;
  deleteError.value = "";
  try {
    await api.value.remove(deleting.value.id);
    deleting.value = null;
    notice.value = "凭证已删除";
    await list.value.load();
    emit("changed");
  } catch (e) {
    deleteError.value = e.message;
  } finally {
    saving.value = false;
  }
}
async function readPrivateKey(event) {
  const request = editorRequest;
  const file = event.target.files?.[0];
  event.target.value = "";
  if (!file) return;
  if (file.size > 1024 * 1024) {
    editorError.value = "私钥文件不能超过 1MB";
    return;
  }
  try {
    const content = await file.text();
    if (
      !/-----BEGIN (?:OPENSSH |RSA |EC |ENCRYPTED )?PRIVATE KEY-----/.test(
        content,
      )
    )
      throw new Error("请选择 SSH 私钥文件，不是公钥文件");
    if (editorOpen.value && request === editorRequest)
      form.private_key = `${content.trim()}\n`;
  } catch (e) {
    editorError.value = e.message;
  }
}
watch(editorOpen, (visible) => {
  if (!visible) for (const key of Object.keys(labels)) form[key] = "";
});
watch(deleting, () => {
  deleteError.value = "";
});
watch(kind, () => {
  error.value = "";
  notice.value = "";
  list.value.load();
});
onMounted(() => list.value.load(1));
</script>
