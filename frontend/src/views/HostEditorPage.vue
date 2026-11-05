<template>
  <div>
    <PageHeader
      :title="title"
      description="维护主机连接、访问凭据与信任指纹，保存后返回主机列表。"
    >
      <template #before
        ><router-link
          :to="listLocation"
          class="mb-3 inline-flex text-sm text-gray-500 hover:text-blue-700"
          >← 返回主机列表</router-link
        ></template
      ><Button
        type="button"
        :disabled="savingHost"
        @click="router.push(listLocation)"
        variant="outline"
        size="default"
        >取消</Button
      ><Button
        v-if="!loading && !loadError"
        type="submit"
        form="host-editor-form"
        :disabled="
          savingHost || fetchingRdpFingerprint || savingDockerCredential
        "
        variant="default"
        size="default"
        >{{ savingHost ? "保存中…" : "保存主机" }}</Button
      > </PageHeader
    ><Card
      v-if="loading"
      role="status"
      class="gap-0 py-0 p-10 text-center text-sm text-gray-500"
      >正在加载主机信息…</Card
    ><Card v-else-if="loadError" class="gap-0 py-0 space-y-4 p-6"
      ><p role="alert" class="text-sm text-red-700">{{ loadError }}</p>
      <Button @click="load" type="button" variant="outline" size="default"
        >重试</Button
      ></Card
    >
    <form
      v-else
      id="host-editor-form"
      class="space-y-5"
      @submit.prevent="saveHost"
    >
      <p
        v-if="cloningHostId"
        class="rounded-lg border border-blue-100 bg-blue-50 p-4 text-sm text-blue-800"
      >
        克隆会复用所选凭据并清空目标指纹。请核对新主机的名称、地址和证书。
      </p>
      <p
        v-if="activationPending"
        role="status"
        class="rounded-lg border bg-muted/30 p-3 text-sm"
      >
        此主机尚未激活。保存凭据等配置后，请返回主机列表进行连接测试，通过后自动启用。
      </p>
      <fieldset :disabled="savingHost" class="min-w-0 space-y-5">
        <Card
          ><CardHeader
            ><h2 class="text-base font-semibold">基本信息</h2></CardHeader
          ><CardContent class="space-y-4">
            <ToggleGroup
              type="single"
              :model-value="hostForm.host_type"
              @update:model-value="
                (value) => {
                  if (value) setHostType(value);
                }
              "
              variant="outline"
              class="grid w-full grid-cols-3"
              ><ToggleGroupItem
                v-for="kind in ['ssh', 'docker', 'rdp']"
                :key="kind"
                :value="kind"
                :aria-label="
                  (kind === 'docker' ? 'Docker' : kind.toUpperCase()) + ' 主机'
                "
                >{{
                  kind === "docker" ? "Docker" : kind.toUpperCase()
                }}</ToggleGroupItem
              ></ToggleGroup
            >
            <div class="grid gap-3 sm:grid-cols-2">
              <label class="text-sm"
                >主机名称<Input
                  v-model.trim="hostForm.name"
                  class="mt-1 w-full"
                  required
                ></Input></label
              ><label class="text-sm"
                >连接地址<Input
                  v-model.trim="hostForm.address"
                  class="mt-1 w-full"
                  :placeholder="
                    hostForm.host_type === 'docker'
                      ? '主机名，或 http://host/docker/'
                      : '主机名或 IP'
                  "
                  required
                ></Input></label
              ><label class="text-sm"
                >端口<Input
                  v-model.number="hostForm.port"
                  type="number"
                  min="1"
                  max="65535"
                  class="mt-1 w-full"
                  required
                ></Input></label
              ><label
                v-if="!activationPending"
                class="flex items-center gap-2 pt-6 text-sm"
                ><Checkbox v-model="hostForm.is_active"></Checkbox
                >启用资源</label
              >
            </div></CardContent
          ></Card
        ><Card
          ><CardHeader
            ><h2 class="text-base font-semibold">连接与认证</h2></CardHeader
          ><CardContent class="space-y-4">
            <template v-if="hostForm.host_type === 'ssh'">
              <SshCredentialForm v-model="hostForm.credential_id" /><label
                class="block text-sm"
                >SSH 主机指纹（可选）<Input
                  v-model.trim="hostForm.host_key_fingerprint"
                  class="mt-1 w-full font-mono"
                  placeholder="SHA256:..."
                ></Input
                ><span class="mt-1 block text-xs text-gray-400"
                  >留空时首次连接自动记录，后续严格校验。</span
                ></label
              > </template
            ><template v-else-if="hostForm.host_type === 'docker'">
              <div class="rounded-lg border border-gray-200 bg-gray-50 p-3">
                <label class="text-sm"
                  >Portainer 凭据<ResourceCombobox
                    v-model="hostForm.docker_credential_id"
                    label="选择 Portainer 凭据"
                    :fetch-options="dockerCredentialsApi.list"
                    :resolve-option="dockerCredentialsApi.get" /></label
                ><Button
                  type="button"
                  class="mt-2"
                  @click="dockerCredentialEditor = !dockerCredentialEditor"
                  variant="outline"
                  size="sm"
                  >+ 新建 Docker 凭据</Button
                >
                <div
                  v-if="dockerCredentialEditor"
                  class="mt-3 space-y-2 border-t border-violet-100 pt-3"
                >
                  <Input
                    v-model.trim="dockerCredForm.name"
                    class="w-full"
                    aria-label="Docker 凭据名称"
                    placeholder="凭据名称"
                  ></Input
                  ><Select v-model="dockerCredForm.auth_type"
                    ><SelectTrigger class="w-full" aria-label="请选择"
                      ><SelectValue
                        placeholder="请选择"
                      ></SelectValue></SelectTrigger
                    ><SelectContent
                      ><SelectItem value="api_key">Portainer API Key</SelectItem
                      ><SelectItem value="password"
                        >用户名/密码</SelectItem
                      ></SelectContent
                    ></Select
                  ><Input
                    v-if="dockerCredForm.auth_type === 'api_key'"
                    v-model="dockerCredForm.api_key"
                    type="password"
                    class="w-full"
                    placeholder="ptr_..."
                  ></Input
                  ><template v-else
                    ><Input
                      v-model.trim="dockerCredForm.username"
                      class="w-full"
                      placeholder="Portainer 用户名"
                    ></Input
                    ><Input
                      v-model="dockerCredForm.password"
                      type="password"
                      class="w-full"
                      placeholder="Portainer 密码"
                    ></Input></template
                  ><Textarea
                    v-model="dockerCredForm.ca_cert"
                    rows="3"
                    class="w-full font-mono"
                    placeholder="自定义 CA 证书（可选）"
                  ></Textarea
                  ><Button
                    type="button"
                    :disabled="savingDockerCredential"
                    @click="saveDockerCredential"
                    variant="outline"
                    size="sm"
                    >{{
                      savingDockerCredential ? "保存中…" : "保存 Docker 凭据"
                    }}</Button
                  >
                </div>
              </div>
              <div class="grid gap-3 sm:grid-cols-2">
                <label class="text-sm"
                  >Portainer Endpoint ID<Input
                    v-model.number="hostForm.docker_endpoint_id"
                    type="number"
                    min="1"
                    class="mt-1 w-full"
                    placeholder="例如 1"
                    required
                  ></Input
                ></label>
                <div
                  v-if="!hasUrlScheme(hostForm.address)"
                  class="space-y-2 pt-1"
                >
                  <label class="flex items-center gap-2 text-sm"
                    ><Checkbox v-model="hostForm.docker_use_tls"></Checkbox>使用
                    HTTPS（通常端口 9443）</label
                  ><label
                    v-if="hostForm.docker_use_tls"
                    class="flex items-center gap-2 text-sm"
                    ><Checkbox v-model="hostForm.docker_verify_tls"></Checkbox
                    >校验 Portainer TLS 证书</label
                  >
                </div>
                <p v-else class="pt-1 text-xs leading-5 text-gray-500">
                  协议、端口和反向代理路径按完整 URL 自动识别。
                </p>
              </div> </template
            ><template v-if="hostForm.host_type === 'rdp'">
              <SshCredentialForm
                :key="hostForm.host_type"
                v-model="hostForm.credential_id"
                password-only
              />
              <div class="text-sm">
                <label for="rdp-fingerprint"
                  >Windows RDP 证书 SHA256 指纹</label
                >
                <div class="mt-1 flex flex-wrap gap-2">
                  <Input
                    id="rdp-fingerprint"
                    v-model.trim="hostForm.host_key_fingerprint"
                    class="min-w-0 flex-1 font-mono"
                    placeholder="留空时保存自动获取"
                  ></Input
                  ><Button
                    type="button"
                    :disabled="
                      fetchingRdpFingerprint ||
                      savingHost ||
                      !hostForm.address ||
                      !hostForm.port
                    "
                    @click="fetchRdpFingerprint"
                    variant="outline"
                    size="sm"
                    >{{
                      fetchingRdpFingerprint ? "获取中…" : "获取指纹"
                    }}</Button
                  >
                </div>
                <p class="mt-1 text-xs leading-5 text-gray-500">
                  首次获取后保存指纹，后续证书变化会拒绝连接。更新已有指纹时，核对目标机器后点击“获取指纹”并保存。
                </p>
              </div>
              <p
                class="rounded-lg bg-blue-50 p-3 text-sm leading-6 text-blue-800"
              >
                绑定 Windows
                密码凭据后，用户使用“平台账号#主机名”和平台密码连接公网
                13389，网关自动代登录。Windows
                密码加密保存，不会出现在连接文件中。
              </p>
            </template></CardContent
          ></Card
        ><Card
          ><CardHeader
            ><h2 class="text-base font-semibold">备注信息</h2></CardHeader
          ><CardContent class="space-y-4">
            <label class="block text-sm"
              >标签<Input
                v-model.trim="hostForm.tags"
                class="mt-1 w-full"
                placeholder="生产, 华东"
              ></Input></label
            ><label class="block text-sm"
              >描述<Textarea
                v-model.trim="hostForm.description"
                rows="2"
                class="mt-1 w-full"
              ></Textarea></label></CardContent
        ></Card>
      </fieldset>
      <p
        v-if="error"
        role="alert"
        class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700"
      >
        {{ error }}
      </p>
      <Card class="flex-row flex-wrap justify-end gap-2 p-4"
        ><Button
          type="button"
          :disabled="savingHost"
          @click="router.push(listLocation)"
          variant="outline"
          size="default"
          >取消</Button
        ><Button
          type="submit"
          :disabled="
            savingHost || fetchingRdpFingerprint || savingDockerCredential
          "
          variant="default"
          size="default"
          >{{ savingHost ? "保存中…" : "保存主机" }}</Button
        ></Card
      >
    </form>
  </div>
</template>

<script setup>
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { SelectContent } from "@/components/ui/select";
import { SelectItem } from "@/components/ui/select";
import { SelectTrigger } from "@/components/ui/select";
import { SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import {
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
  useRoute,
  useRouter,
} from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import ResourceCombobox from "@/components/ResourceCombobox.vue";
import SshCredentialForm from "@/components/SshCredentialForm.vue";
import { dockerCredentialsApi, managedHostsApi } from "@/api/managedHosts";
import { confirmAction, notify } from "@/composables/useFeedback";

const route = useRoute(),
  router = useRouter();
const editingHostId = computed(() =>
  route.name === "HostEdit" ? Number(route.params.id) : null,
);
const cloningHostId = computed(() =>
  route.name === "HostClone" ? Number(route.params.id) : null,
);
const title = computed(() =>
  editingHostId.value
    ? "编辑主机"
    : cloningHostId.value
      ? "克隆主机"
      : "添加主机",
);
const listLocation = computed(() => ({
  path: "/hosts",
  query: {
    page: route.query.page,
    page_size: route.query.page_size,
    search: route.query.search,
    host_type: route.query.host_type,
    host_status: route.query.host_status,
  },
}));
const activationPending = ref(false);
const hostForm = reactive({
  name: "",
  address: "",
  port: 22,
  host_type: "ssh",
  credential_id: 0,
  docker_credential_id: 0,
  docker_use_tls: true,
  docker_verify_tls: true,
  docker_endpoint_id: 1,
  host_key_fingerprint: "",
  tags: "",
  description: "",
  is_active: true,
});
const loading = ref(true),
  loadError = ref(""),
  error = ref(""),
  savingHost = ref(false),
  fetchingRdpFingerprint = ref(false);
const dockerCredentialEditor = ref(false),
  savingDockerCredential = ref(false);
const dockerCredForm = reactive({
  name: "",
  auth_type: "api_key",
  username: "",
  password: "",
  api_key: "",
  ca_cert: "",
});
const original = ref("");
let disposed = false;
const dirty = computed(
  () => Boolean(original.value) && JSON.stringify(hostForm) !== original.value,
);
const hasUrlScheme = (value) => /^https?:\/\//i.test(value || "");

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    const id = editingHostId.value || cloningHostId.value;
    if (id) {
      const result = await managedHostsApi.list({
        page: 1,
        page_size: 1,
        host_id: id,
      });
      if (disposed) return;
      const host = result.items.find((item) => item.id === id);
      activationPending.value = Boolean(
        host?.activation_pending && !cloningHostId.value,
      );
      if (!host?.can_manage) throw new Error("主机不存在或当前账号无权编辑");
      for (const key of Object.keys(hostForm))
        if (host[key] != null) hostForm[key] = host[key];
      if (cloningHostId.value) {
        hostForm.name = `${host.name} 副本`;
        hostForm.host_key_fingerprint = "";
      }
    }
    original.value = JSON.stringify(hostForm);
  } catch (e) {
    loadError.value = e.message;
  } finally {
    loading.value = false;
  }
}
function setHostType(type) {
  if (hostForm.host_type === type) return;
  Object.assign(hostForm, {
    host_type: type,
    port: { ssh: 22, docker: 9443, rdp: 3389 }[type],
    credential_id: 0,
    docker_credential_id: 0,
    host_key_fingerprint: "",
  });
}
async function saveHost() {
  if (
    savingHost.value ||
    fetchingRdpFingerprint.value ||
    savingDockerCredential.value
  )
    return;
  error.value = "";
  if (
    !(hostForm.host_type === "docker"
      ? hostForm.docker_credential_id
      : hostForm.credential_id)
  ) {
    error.value = "请选择并保存访问凭据";
    return;
  }
  savingHost.value = true;
  try {
    const payload = {
      ...hostForm,
      credential_id: ["ssh", "rdp"].includes(hostForm.host_type)
        ? hostForm.credential_id
        : null,
      docker_credential_id:
        hostForm.host_type === "docker" ? hostForm.docker_credential_id : null,
      host_key_fingerprint: hostForm.host_key_fingerprint || null,
    };
    if (editingHostId.value)
      await managedHostsApi.update(editingHostId.value, payload);
    else await managedHostsApi.create(payload);
    original.value = JSON.stringify(hostForm);
    notify("主机已保存", "success");
    await router.replace(listLocation.value);
  } catch (e) {
    error.value = e.message;
  } finally {
    savingHost.value = false;
  }
}
async function fetchRdpFingerprint() {
  const { address, port } = hostForm;
  fetchingRdpFingerprint.value = true;
  error.value = "";
  try {
    const result = await managedHostsApi.rdpFingerprint({ address, port });
    if (
      !disposed &&
      hostForm.host_type === "rdp" &&
      hostForm.address === address &&
      hostForm.port === port
    )
      hostForm.host_key_fingerprint = result.fingerprint;
  } catch (e) {
    error.value = e.message;
  } finally {
    fetchingRdpFingerprint.value = false;
  }
}
async function saveDockerCredential() {
  if (savingDockerCredential.value) return;
  if (
    !dockerCredForm.name.trim() ||
    !(dockerCredForm.auth_type === "api_key"
      ? dockerCredForm.api_key
      : dockerCredForm.username && dockerCredForm.password)
  ) {
    error.value = "请填写凭据名称和认证信息";
    return;
  }
  savingDockerCredential.value = true;
  error.value = "";
  try {
    const created = await dockerCredentialsApi.create({ ...dockerCredForm });
    if (disposed) return;
    hostForm.docker_credential_id = created.id;
    dockerCredentialEditor.value = false;
    Object.assign(dockerCredForm, {
      name: "",
      auth_type: "api_key",
      username: "",
      password: "",
      api_key: "",
      ca_cert: "",
    });
    notify("Docker 凭据已保存", "success");
  } catch (e) {
    error.value = e.message;
  } finally {
    savingDockerCredential.value = false;
  }
}
function canLeave() {
  if (savingHost.value) return !dirty.value;
  return (
    !dirty.value ||
    confirmAction("主机信息尚未保存，确定放弃修改并离开？", {
      title: "放弃未保存的修改",
      confirmText: "放弃修改",
    })
  );
}
function beforeUnload(event) {
  if (dirty.value) {
    event.preventDefault();
    event.returnValue = "";
  }
}
onBeforeRouteLeave(canLeave);
onBeforeRouteUpdate((to, from) => to.path === from.path || canLeave());
onMounted(() => {
  window.addEventListener("beforeunload", beforeUnload);
  load();
});
onUnmounted(() => {
  disposed = true;
  window.removeEventListener("beforeunload", beforeUnload);
});
</script>
