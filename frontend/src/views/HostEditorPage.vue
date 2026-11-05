<template>
  <div>
    <PageHeader
      :title="title"
      description="为所属主机配置一种连接服务；各协议的地址、端口、凭据与授权独立。"
    >
      <template #before
        ><router-link
          :to="listLocation"
          class="mb-3 inline-flex text-sm text-gray-500 hover:text-blue-700"
          >← 返回所属主机</router-link
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
          savingHost ||
          fetchingRdpFingerprint ||
          savingDockerCredential ||
          testingVncSsh
        "
        variant="default"
        size="default"
        >{{ savingHost ? "保存中…" : "保存连接服务" }}</Button
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
      <fieldset
        :disabled="savingHost || testingVncSsh"
        class="min-w-0 space-y-5"
      >
        <Card
          ><CardHeader
            ><h2 class="text-base font-semibold">
              所属主机与连接协议
            </h2></CardHeader
          ><CardContent class="space-y-4">
            <label class="block text-sm"
              >所属主机<ResourceCombobox
                v-model="hostForm.machine_id"
                label="选择所属主机"
                :fetch-options="machinesApi.list"
                :resolve-option="resolveMachine"
                :get-label="(item) => `${item.name} (#${item.id})`"
                @select="selectMachine"
            /></label>
            <ToggleGroup
              type="single"
              :model-value="hostForm.host_type"
              @update:model-value="
                (value) => {
                  if (value) setHostType(value);
                }
              "
              variant="outline"
              class="grid w-full grid-cols-2 sm:grid-cols-4"
              ><ToggleGroupItem
                v-for="kind in ['ssh', 'docker', 'rdp', 'vnc']"
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
                >连接名称<Input
                  v-model.trim="hostForm.name"
                  class="mt-1 w-full"
                  required
                ></Input></label
              ><label class="text-sm"
                >{{ hostForm.host_type === "vnc" ? "VNC 地址" : "连接地址"
                }}<Input
                  v-model.trim="hostForm.address"
                  :readonly="hostForm.host_type === 'vnc' && vncUseSsh"
                  class="mt-1 w-full"
                  :placeholder="
                    hostForm.host_type === 'docker'
                      ? '主机名，或 http://host/docker/'
                      : '主机名或 IP'
                  "
                  required
                ></Input></label
              ><label class="text-sm"
                >{{
                  hostForm.host_type === "vnc"
                    ? "VNC 端口"
                    : hostForm.host_type === "ssh"
                      ? "SSH 端口"
                      : "端口"
                }}<Input
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
            ><template v-if="hostForm.host_type === 'vnc'">
              <p class="text-sm text-muted-foreground">
                填写 VNC 服务本身的地址、端口和专用密码。直连 VNC 无需 SSH
                凭据或 SSH 指纹。
              </p>
              <label class="flex min-h-11 items-center gap-2 text-sm"
                ><Checkbox
                  :model-value="vncUseSsh"
                  @update:model-value="setVncTransport"
                />使用 SSH 隧道（可选）</label
              >
              <template v-if="vncUseSsh">
                <label class="block text-sm"
                  >用于隧道的 SSH 连接
                  <ResourceCombobox
                    v-model="hostForm.vnc_ssh_host_id"
                    label="选择 SSH 隧道连接"
                    :fetch-options="
                      (params) =>
                        managedHostsApi.list({
                          ...params,
                          host_type: 'ssh',
                          machine_id: hostForm.machine_id || undefined,
                        })
                    "
                    :resolve-option="resolveVncSsh"
                    @select="selectVncSsh"
                  />
                </label>
                <div v-if="vncSshHost" class="space-y-3 rounded-lg border p-3">
                  <p
                    v-if="!vncSshHost.is_active"
                    class="text-sm text-amber-700"
                  >
                    关联 SSH 主机已停用，请先启用并配置凭据。
                  </p>
                  <p
                    v-else-if="!vncSshHost.credential_id"
                    class="text-sm text-amber-700"
                  >
                    关联 SSH 主机尚未配置凭据，请先完成配置。
                  </p>
                  <p v-else class="text-sm text-muted-foreground">
                    {{
                      vncSshHost.host_key_fingerprint
                        ? "已记录 SSH 指纹；连接时会严格校验。"
                        : "尚未记录 SSH 指纹，点击下方检测，无需手动输入。"
                    }}
                  </p>
                  <p class="break-all text-sm">
                    SSH 地址：{{ vncSshHost.address }} · SSH 端口：{{
                      vncSshHost.port
                    }}
                  </p>
                  <code
                    v-if="vncSshHost.host_key_fingerprint"
                    class="block break-all text-xs"
                    >{{ vncSshHost.host_key_fingerprint }}</code
                  >
                  <div class="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      :disabled="
                        testingVncSsh ||
                        !vncSshHost.is_active ||
                        !vncSshHost.credential_id
                      "
                      @click="testVncSsh"
                    >
                      {{
                        testingVncSsh
                          ? "SSH 检测中…"
                          : vncSshHost.host_key_fingerprint
                            ? "重新检测 SSH"
                            : "检测并记录 SSH 指纹"
                      }}
                    </Button>
                    <Button as-child variant="outline"
                      ><router-link :to="`/hosts/${vncSshHost.id}/edit`"
                        >配置 SSH 连接</router-link
                      ></Button
                    >
                  </div>
                  <p class="text-xs leading-5 text-muted-foreground">
                    检测使用这台 SSH
                    主机已有的凭据。首次成功连接会记录指纹，请与 Mac
                    本机核对一次；已有指纹不匹配时会拒绝连接，不会覆盖。
                  </p>
                  <p
                    v-if="vncSshMessage"
                    role="status"
                    class="text-sm text-emerald-700"
                  >
                    {{ vncSshMessage }}
                  </p>
                  <p
                    v-if="vncSshError"
                    role="alert"
                    class="break-words text-sm text-destructive"
                  >
                    {{ vncSshError }}
                  </p>
                </div>
                <p v-else class="text-xs text-muted-foreground">
                  选择所属主机的 SSH 连接，可在此检测指纹；VNC 端口仍单独配置。
                </p>
              </template>
              <SshCredentialForm
                v-model="hostForm.credential_id"
                password-only
              />
              <p class="text-sm text-muted-foreground">
                使用专用 VNC 密码凭据（1–8 位 ASCII；用户名可填写
                vnc，仅作标识）。在 Mac 开启“屏幕共享”，启用 VNC 密码控制。传统
                VNC 直连不提供传输加密，仅允许可信内网、VPN 或 FRP
                内部/回环入口。选择 SSH 隧道时，VNC 地址固定为 Mac 的
                127.0.0.1，VNC 端口与 SSH 端口分别配置。浏览器连接必须使用
                HTTPS。
              </p> </template
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
            savingHost ||
            fetchingRdpFingerprint ||
            savingDockerCredential ||
            testingVncSsh
          "
          variant="default"
          size="default"
          >{{ savingHost ? "保存中…" : "保存连接服务" }}</Button
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
import {
  dockerCredentialsApi,
  managedHostsApi,
  machinesApi,
} from "@/api/managedHosts";
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
    ? "编辑连接服务"
    : cloningHostId.value
      ? "克隆连接服务"
      : "添加连接服务",
);
const listLocation = computed(() => ({
  path: returnMachine.value ? `/machines/${returnMachine.value}` : "/hosts",
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
  machine_id: null,
  name: "",
  address: "",
  port: 22,
  host_type: "ssh",
  vnc_ssh_host_id: null,
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
const vncSshHost = ref(null),
  testingVncSsh = ref(false),
  vncSshMessage = ref(""),
  vncSshError = ref("");
const vncUseSsh = ref(false),
  directAddress = ref(""),
  machineName = ref(""),
  returnMachine = ref(Number(route.query.machine_id) || null);
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
      vncUseSsh.value = Boolean(host.vnc_ssh_host_id);
      if (cloningHostId.value) {
        hostForm.name = `${host.name} 副本`;
        hostForm.host_key_fingerprint = "";
      }
    }
    if (!id && returnMachine.value) {
      hostForm.machine_id = returnMachine.value;
      await resolveMachine(returnMachine.value);
    }
    if (!id && ["ssh", "vnc", "rdp", "docker"].includes(route.query.protocol))
      setHostType(route.query.protocol);
    original.value = JSON.stringify(hostForm);
  } catch (e) {
    loadError.value = e.message;
  } finally {
    loading.value = false;
  }
}
function setHostType(type) {
  if (hostForm.host_type === type) return;
  selectVncSsh(null);
  const defaultName =
    machineName.value && `${machineName.value}-${hostForm.host_type}`;
  if (hostForm.name === defaultName)
    hostForm.name = `${machineName.value}-${type}`;
  vncUseSsh.value = false;
  Object.assign(hostForm, {
    host_type: type,
    address: hostForm.vnc_ssh_host_id ? "" : hostForm.address,
    port: { ssh: 22, docker: 9443, rdp: 3389, vnc: 5900 }[type],
    vnc_ssh_host_id: null,
    credential_id: 0,
    docker_credential_id: 0,
    host_key_fingerprint: "",
  });
}
async function saveHost() {
  if (
    savingHost.value ||
    fetchingRdpFingerprint.value ||
    savingDockerCredential.value ||
    testingVncSsh.value
  )
    return;
  error.value = "";
  if (!hostForm.machine_id) {
    error.value = "请选择所属主机；可先到主机资源添加设备，再补充连接服务";
    return;
  }
  if (
    hostForm.host_type === "vnc" &&
    vncUseSsh.value &&
    !hostForm.vnc_ssh_host_id
  ) {
    error.value = "请选择用于隧道的 SSH 连接，或关闭可选 SSH 隧道使用 VNC 直连";
    return;
  }
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
      credential_id: ["ssh", "rdp", "vnc"].includes(hostForm.host_type)
        ? hostForm.credential_id
        : null,
      docker_credential_id:
        hostForm.host_type === "docker" ? hostForm.docker_credential_id : null,
      host_key_fingerprint: hostForm.host_key_fingerprint || null,
    };
    const saved = editingHostId.value
      ? await managedHostsApi.update(editingHostId.value, payload)
      : await managedHostsApi.create(payload);
    original.value = JSON.stringify(hostForm);
    notify("连接服务已保存", "success");
    await router.replace(
      returnMachine.value && saved.machine_id
        ? `/machines/${saved.machine_id}`
        : listLocation.value,
    );
  } catch (e) {
    error.value = e.message;
  } finally {
    savingHost.value = false;
  }
}
function selectMachine(machine) {
  machineName.value = machine?.name || "";
  if (machine && !hostForm.name)
    hostForm.name = `${machine.name}-${hostForm.host_type}`;
}
async function resolveMachine(id) {
  const machine = await machinesApi.get(id);
  if (!disposed && hostForm.machine_id === id) selectMachine(machine);
  return machine;
}
function setVncTransport(value) {
  vncUseSsh.value = Boolean(value);
  if (value) {
    directAddress.value = hostForm.address;
    hostForm.address = "127.0.0.1";
  } else {
    hostForm.address = directAddress.value;
    hostForm.vnc_ssh_host_id = null;
    selectVncSsh(null);
  }
}
function selectVncSsh(host) {
  vncSshHost.value = host;
  vncSshMessage.value = "";
  vncSshError.value = "";
}
async function resolveVncSsh(id) {
  const host = (
    await managedHostsApi.list({ host_id: id, page: 1, page_size: 1 })
  ).items[0];
  if (!disposed && hostForm.vnc_ssh_host_id === id) selectVncSsh(host);
  return host;
}
async function testVncSsh() {
  if (testingVncSsh.value || !hostForm.vnc_ssh_host_id) return;
  const id = hostForm.vnc_ssh_host_id;
  testingVncSsh.value = true;
  error.value = "";
  vncSshMessage.value = "";
  vncSshError.value = "";
  try {
    const result = await managedHostsApi.test(id);
    if (disposed || hostForm.vnc_ssh_host_id !== id) return;
    if (!result.success)
      throw new Error(result.stderr || "SSH 检测失败，请检查连接及凭据");
    await resolveVncSsh(id);
    if (!disposed && hostForm.vnc_ssh_host_id === id) {
      if (
        !vncSshHost.value?.is_active ||
        !vncSshHost.value?.credential_id ||
        !vncSshHost.value?.host_key_fingerprint
      )
        throw new Error("SSH 主机配置已变化，请核对启用状态、凭据和指纹后重试");
      vncSshMessage.value = "SSH 检测通过，可保存 VNC 主机。";
      error.value = "";
    }
  } catch (e) {
    if (!disposed && hostForm.vnc_ssh_host_id === id)
      vncSshError.value = e.message || "SSH 检测失败，请重试";
  } finally {
    testingVncSsh.value = false;
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
    confirmAction("连接信息尚未保存，确定放弃修改并离开？", {
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
