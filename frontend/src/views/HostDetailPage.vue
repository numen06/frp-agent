<script setup>
import {
  computed,
  defineAsyncComponent,
  onMounted,
  onUnmounted,
  ref,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import { managedHostsApi } from "@/api/managedHosts";
import PageHeader from "@/components/PageHeader.vue";
import HostAuditPanel from "@/components/HostAuditPanel.vue";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

const route = useRoute(),
  router = useRouter();
const host = ref(null),
  isAdmin = ref(false),
  loading = ref(true),
  error = ref("");
let disposed = false;
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
const activeTab = computed(() =>
  route.query.tab === "desktop" && canUseDesktop.value
    ? "desktop"
    : route.query.tab === "terminal" && canUseTerminal.value
      ? "terminal"
      : route.query.tab === "logs"
        ? "logs"
        : "overview",
);
const canUseTerminal = computed(
  () =>
    host.value?.host_type === "ssh" &&
    host.value.is_active &&
    host.value.permissions.includes("execute"),
);
const canUseDesktop = computed(
  () =>
    host.value?.host_type === "vnc" &&
    host.value.is_active &&
    host.value.permissions.includes("connect"),
);
const WebVncDesktop = defineAsyncComponent(
  () => import("@/components/WebVncDesktop.vue"),
);
const WebSshTerminal = defineAsyncComponent(
  () => import("@/components/WebSshTerminal.vue"),
);
function selectTab(tab) {
  router.replace({ path: route.path, query: { ...route.query, tab } });
}
async function load() {
  loading.value = true;
  error.value = "";
  try {
    const id = Number(route.params.id);
    const [context, result] = await Promise.all([
      managedHostsApi.context(),
      managedHostsApi.list({ page: 1, page_size: 1, host_id: id }),
    ]);
    if (disposed) return;
    const item = result.items.find((row) => row.id === id);
    if (!item) throw new Error("主机不存在或当前账号无权查看");
    host.value = item;
    isAdmin.value = context.is_admin;
  } catch (e) {
    if (!disposed) error.value = e.message;
  } finally {
    if (!disposed) loading.value = false;
  }
}
function date(value) {
  if (!value) return "未记录";
  return new Date(
    /(?:Z|[+-]\d\d:\d\d)$/.test(value) ? value : value + "Z",
  ).toLocaleString("zh-CN");
}
const fields = computed(() => {
  if (!host.value) return [];
  const h = host.value;
  return [
    [
      "类型",
      {
        ssh: "SSH",
        rdp: "RDP 远程桌面",
        vnc: "VNC / macOS",
        docker: "Docker / Portainer",
      }[h.host_type],
    ],
    [
      "目标地址",
      /^https?:\/\//i.test(h.address) ? h.address : `${h.address}:${h.port}`,
    ],
    ["启用状态", h.is_active ? "已启用" : "已禁用"],
    ["最近检查", date(h.last_checked_at)],
    ["系统版本", h.version_info],
    ["关联凭据", h.credential_name],
    ...(h.host_type === "vnc" ? [["SSH 通道主机 ID", h.vnc_ssh_host_id]] : []),
    ["登录账号", h.credential_username],
    ...(h.host_type === "docker"
      ? [
          ["Portainer Endpoint", h.docker_endpoint_id],
          [
            "TLS 校验",
            h.docker_use_tls
              ? h.docker_verify_tls
                ? "已启用"
                : "未启用证书校验"
              : "未使用 TLS",
          ],
        ]
      : []),
    ["目标指纹", h.host_key_fingerprint],
    ["标签", h.tags],
    ["创建时间", date(h.created_at)],
    ["更新时间", date(h.updated_at)],
  ];
});
onMounted(load);
onUnmounted(() => {
  disposed = true;
});
</script>

<template>
  <div class="space-y-4">
    <PageHeader
      :title="host?.name || '主机详情'"
      description="查阅主机信息、连接记录、操作日志与流量。"
      class="[&_.page-title]:break-all"
    >
      <template #before
        ><router-link
          :to="listLocation"
          class="mb-3 inline-flex text-sm text-muted-foreground hover:text-primary"
          >← 返回主机列表</router-link
        ></template
      >
      <Button v-if="host?.can_manage" as-child variant="outline"
        ><router-link
          :to="{ path: `/hosts/${host.id}/edit`, query: listLocation.query }"
          >编辑主机</router-link
        ></Button
      >
    </PageHeader>
    <Card v-if="loading" role="status" class="p-8 text-sm text-muted-foreground"
      >正在加载主机信息…</Card
    >
    <Card v-else-if="error" class="gap-3 p-5">
      <p role="alert" class="text-sm text-destructive">{{ error }}</p>
      <Button variant="outline" class="w-fit" @click="load"
        >重试读取主机</Button
      >
    </Card>
    <Tabs
      v-else-if="host"
      :model-value="activeTab"
      @update:model-value="selectTab"
      class="gap-4"
    >
      <Card class="px-2"
        ><TabsList
          variant="line"
          aria-label="主机详情分类"
          class="flex h-auto w-full flex-wrap justify-start"
        >
          <TabsTrigger value="overview">主机信息</TabsTrigger
          ><TabsTrigger value="logs">日志与流量</TabsTrigger>
          <TabsTrigger v-if="canUseDesktop" value="desktop"
            >远程桌面</TabsTrigger
          >
          <TabsTrigger v-if="canUseTerminal" value="terminal"
            >Web SSH</TabsTrigger
          >
        </TabsList></Card
      >
      <TabsContent :value="activeTab" force-mount>
        <div v-if="activeTab === 'overview'" class="space-y-4">
          <Card>
            <CardHeader
              ><h2 class="font-semibold">连接状态</h2>
              <Button variant="outline" size="sm" @click="selectTab('logs')"
                >查看日志</Button
              ></CardHeader
            >
            <CardContent class="space-y-2 text-sm">
              <p
                :class="
                  ['error', 'offline'].includes(host.last_status)
                    ? 'text-destructive'
                    : 'text-muted-foreground'
                "
                class="whitespace-pre-wrap break-all"
              >
                {{ host.last_message || "尚未检测" }}
              </p>
              <p
                v-if="host.host_type === 'rdp'"
                class="text-xs text-muted-foreground"
              >
                历史检查仅验证 RDP 服务与证书；是否进入桌面，请查看日志中的“RDP
                桌面已连接”。
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader
              ><h2 class="font-semibold">主机与关联信息</h2></CardHeader
            >
            <CardContent>
              <dl class="grid gap-5 sm:grid-cols-2">
                <div
                  v-for="[label, value] in fields"
                  :key="label"
                  class="min-w-0 space-y-1"
                >
                  <dt class="text-xs text-muted-foreground">{{ label }}</dt>
                  <dd class="whitespace-pre-wrap break-all text-sm">
                    {{ value ?? "未配置" }}
                  </dd>
                </div>
                <div class="min-w-0 space-y-1 sm:col-span-2">
                  <dt class="text-xs text-muted-foreground">说明</dt>
                  <dd class="whitespace-pre-wrap break-all text-sm">
                    {{ host.description || "无" }}
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>
        </div>
        <WebVncDesktop v-else-if="activeTab === 'desktop'" :host="host" />
        <WebSshTerminal v-else-if="activeTab === 'terminal'" :host="host" />
        <HostAuditPanel
          v-else
          :host-id="host.id"
          fixed-host
          :is-admin="isAdmin"
        />
      </TabsContent>
    </Tabs>
  </div>
</template>
