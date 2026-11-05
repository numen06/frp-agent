<template>
  <div class="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-3">
    <div class="flex flex-wrap items-end gap-2">
      <div class="min-w-[140px] flex-1">
        <label class="mb-1 block text-xs font-medium text-gray-600">凭据</label
        ><ResourceCombobox
          v-model="selectedId"
          label="选择凭据"
          allow-clear
          clear-label="新建凭据（不使用现有）"
          :fetch-options="
            (params) =>
              sshCredentialsApi.list({
                ...params,
                auth_type: passwordOnly ? 'password' : undefined,
              })
          "
          :resolve-option="resolveCredential"
          :get-label="(item) => `${item.name} (${item.username})`"
          @select="selectCredential"
        />
      </div>
      <Button
        type="button"
        @click="showEditor = !showEditor"
        :disabled="credentialLoading || saving"
        variant="outline"
        size="sm"
        >{{ showEditor ? "收起" : editingId ? "编辑凭据" : "新建凭据" }}</Button
      >
    </div>
    <div v-if="showEditor" class="space-y-2 border-t border-gray-200 pt-3">
      <div class="grid gap-2 sm:grid-cols-2">
        <div>
          <label class="mb-1 block text-xs font-medium text-gray-600"
            >名称</label
          ><Input v-model="form.name" type="text" class="w-full"></Input>
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-gray-600"
            >用户名</label
          ><Input v-model="form.username" type="text" class="w-full"></Input>
        </div>
      </div>
      <div>
        <label class="mb-1 block text-xs font-medium text-gray-600"
          >认证方式</label
        ><Select v-model="form.auth_type"
          ><SelectTrigger class="w-full" aria-label="认证方式"
            ><SelectValue placeholder="请选择"></SelectValue></SelectTrigger
          ><SelectContent
            ><SelectItem value="password">密码</SelectItem
            ><SelectItem v-if="!passwordOnly" value="private_key"
              >私钥</SelectItem
            ></SelectContent
          ></Select
        >
      </div>
      <div v-if="form.auth_type === 'password'">
        <label class="mb-1 block text-xs font-medium text-gray-600">
          密码 {{ editingId ? "（留空不修改）" : "" }} </label
        ><Input v-model="form.password" type="password" class="w-full"></Input>
      </div>
      <template v-else>
        <div>
          <div class="mb-1 flex flex-wrap items-center justify-between gap-2">
            <label class="block text-xs font-medium text-gray-600">
              私钥 {{ editingId ? "（留空不修改）" : "" }} </label
            ><label
              class="inline-flex min-h-9 cursor-pointer items-center gap-1.5 rounded-lg border border-blue-200 bg-white px-2.5 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-50"
            >
              <svg
                class="h-4 w-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path d="M12 16V4"></path>
                <path d="m7 9 5-5 5 5"></path>
                <path d="M20 15v4a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-4"></path>
              </svg>
              {{ privateKeyFileName ? "重新选择" : "上传证书/私钥" }}
              <input type="file" class="sr-only" @change="loadPrivateKeyFile" />
            </label>
          </div>
          <p
            v-if="privateKeyFileName"
            class="mb-1 truncate text-xs text-green-700"
            :title="privateKeyFileName"
          >
            已读取：{{ privateKeyFileName }}
          </p>
          <Textarea
            v-model="form.private_key"
            rows="4"
            class="w-full font-mono"
            placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"
          ></Textarea>
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-gray-600"
            >私钥口令（可选）</label
          ><Input
            v-model="form.passphrase"
            type="password"
            class="w-full"
          ></Input>
        </div>
      </template>
      <div v-if="!passwordOnly">
        <label class="mb-1 block text-xs font-medium text-gray-600">
          sudo 密码（可选）{{ editingId ? "（留空不修改）" : "" }} </label
        ><Input
          v-model="form.sudo_password"
          type="password"
          class="w-full"
        ></Input>
        <p class="mt-1 text-xs text-gray-400">
          仅管理员明确点击“提权执行”时使用，加密保存且不会显示。
        </p>
      </div>
      <div class="flex gap-2">
        <Button
          type="button"
          :disabled="saving"
          @click="saveCredential"
          variant="default"
          size="sm"
          >{{ saving ? "保存中..." : "保存凭据" }}</Button
        ><Button
          v-if="editingId"
          type="button"
          @click="deleteCredential"
          variant="outline"
          size="sm"
        >
          删除
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { SelectContent } from "@/components/ui/select";
import { SelectItem } from "@/components/ui/select";
import { SelectTrigger } from "@/components/ui/select";
import { SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { notify, confirmAction } from "@/composables/useFeedback";
import ResourceCombobox from "@/components/ResourceCombobox.vue";
import { ref, watch } from "vue";
import { sshCredentialsApi } from "@/api/sshCredentials";

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  passwordOnly: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const credentials = ref([]);
const selectedId = ref(props.modelValue || 0);
const showEditor = ref(false);
const saving = ref(false);
const credentialLoading = ref(false);
let resolveRequest = 0;
const editingId = ref(null);
const privateKeyFileName = ref("");

const form = ref({
  name: "",
  username: props.passwordOnly ? "administrator" : "root",
  auth_type: "password",
  password: "",
  private_key: "",
  passphrase: "",
  sudo_password: "",
});

watch(
  () => props.modelValue,
  (v) => {
    selectedId.value = v || 0;
    if (!v) resetForm();
  },
);

function resetForm() {
  form.value = {
    name: "",
    username: props.passwordOnly ? "administrator" : "root",
    auth_type: "password",
    password: "",
    private_key: "",
    passphrase: "",
    sudo_password: "",
  };
  editingId.value = null;
  privateKeyFileName.value = "";
}

async function loadPrivateKeyFile(event) {
  const file = event.target.files?.[0];
  event.target.value = "";
  if (!file) return;
  if (file.size > 1024 * 1024) return notify("私钥文件不能超过 1MB");
  try {
    const content = await file.text();
    if (
      !/-----BEGIN (?:OPENSSH |RSA |EC |ENCRYPTED )?PRIVATE KEY-----/.test(
        content,
      )
    ) {
      return notify(
        "文件中未找到可用的 SSH 私钥，请选择私钥文件而不是公钥文件",
      );
    }
    form.value.private_key = `${content.trim()}\n`;
    privateKeyFileName.value = file.name;
  } catch {
    notify("读取私钥文件失败，请重新选择");
  }
}

async function loadCredentials() {
  const id = selectedId.value;
  try {
    const rows = id ? [await sshCredentialsApi.get(id)] : [];
    if (selectedId.value !== id) return;
    credentials.value = rows;
    if (id) onSelect();
  } catch (e) {
    console.error(e);
  }
}

async function resolveCredential(id) {
  const request = ++resolveRequest;
  credentialLoading.value = true;
  try {
    const row = await sshCredentialsApi.get(id);
    if (selectedId.value === id && request === resolveRequest) {
      credentials.value = [row];
      onSelect();
    }
    return row;
  } finally {
    if (request === resolveRequest) credentialLoading.value = false;
  }
}
function selectCredential(row) {
  credentials.value = row ? [row] : [];
  if (!row) {
    selectedId.value = 0;
    resetForm();
    showEditor.value = true;
  }
  onSelect();
}

function onSelect() {
  emit("update:modelValue", selectedId.value);
  const c = credentials.value.find((x) => x.id === selectedId.value);
  if (c) {
    editingId.value = c.id;
    form.value.name = c.name;
    form.value.username = c.username;
    form.value.auth_type = c.auth_type;
    form.value.password = "";
    form.value.private_key = "";
    form.value.passphrase = "";
    form.value.sudo_password = "";
    privateKeyFileName.value = "";
  }
}

async function saveCredential() {
  if (saving.value) return;
  saving.value = true;
  try {
    const payload = {
      name: form.value.name,
      username: form.value.username,
      auth_type: form.value.auth_type,
    };
    if (form.value.auth_type === "password" && form.value.password) {
      payload.password = form.value.password;
    }
    if (form.value.auth_type === "private_key") {
      if (form.value.private_key) payload.private_key = form.value.private_key;
      if (form.value.passphrase) payload.passphrase = form.value.passphrase;
    }
    if (form.value.sudo_password)
      payload.sudo_password = form.value.sudo_password;
    if (editingId.value) {
      await sshCredentialsApi.update(editingId.value, payload);
    } else {
      if (form.value.auth_type === "password" && !form.value.password) {
        throw new Error("请填写密码");
      }
      if (form.value.auth_type === "private_key" && !form.value.private_key) {
        throw new Error("请填写私钥");
      }
      const created = await sshCredentialsApi.create({
        ...payload,
        password: form.value.password,
        private_key: form.value.private_key,
        passphrase: form.value.passphrase || undefined,
        sudo_password: form.value.sudo_password || undefined,
      });
      selectedId.value = created.id;
      emit("update:modelValue", created.id);
    }
    await loadCredentials();
    showEditor.value = false;
  } catch (e) {
    notify(e.message || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function deleteCredential() {
  if (!editingId.value || !(await confirmAction("确定删除该 SSH 凭据？")))
    return;
  try {
    await sshCredentialsApi.remove(editingId.value);
    if (selectedId.value === editingId.value) {
      selectedId.value = 0;
      emit("update:modelValue", 0);
    }
    await loadCredentials();
    resetForm();
    showEditor.value = false;
  } catch (e) {
    notify(e.message || "删除失败");
  }
}

defineExpose({ loadCredentials });
</script>
