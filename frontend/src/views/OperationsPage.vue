<template>
  <Tabs v-model="activeTab" class="gap-0"
    ><div>
      <PageHeader
        title="运行维护"
        :description="`本实例资源与连接质量 · ${latest?.scope === 'container' ? '容器统计含内置 FRP 和 RDP 子进程' : '应用资源按主进程统计'}`"
      >
        <template #status
          ><span
            class="ml-2 inline-block rounded-full px-2.5 py-1 align-middle text-xs font-medium tracking-normal"
            :class="
              attention
                ? 'bg-amber-50 text-amber-800'
                : 'bg-blue-50 text-blue-700'
            "
            >{{ healthText }}</span
          ></template
        ><Button
          type="button"
          :disabled="loading"
          @click="refresh"
          variant="outline"
          size="default"
          >{{ loading ? "读取中…" : "刷新运行数据" }}</Button
        > </PageHeader
      ><Card role="region" aria-label="运行维护"
        ><TabsList
          variant="line"
          aria-label="运行维护分类"
          class="grid h-auto w-full grid-cols-2 sm:flex sm:justify-start"
          ><TabsTrigger
            v-for="item in tabs"
            :key="item.key"
            :value="item.key"
            >{{ item.label }}</TabsTrigger
          ></TabsList
        >
        <div class="space-y-5 p-4 sm:p-5">
          <p v-if="latest" class="text-xs text-gray-500">
            采集于 {{ date(latest.collected_at)
            }}<strong v-if="stale" class="ml-1 font-medium text-amber-700"
              >（已过期）</strong
            >
          </p>
          <p
            v-if="error"
            role="alert"
            class="rounded-lg bg-amber-50 p-3 text-sm text-amber-800"
          >
            读取失败：{{ error }}。下方保留上次数据，请核对采集时间。
          </p>
          <p v-else-if="!latest" role="status" class="text-sm text-gray-500">
            正在等待首次资源采样，暂无数据。
          </p>
          <TabsContent
            v-show="activeTab === 'resources'"
            class="space-y-5"
            value="resources"
            force-mount
            ><template v-if="latest">
              <div class="grid grid-cols-2 gap-3 xl:grid-cols-4">
                <article
                  v-for="card in cards"
                  :key="card.title"
                  class="min-w-0 rounded-xl border border-gray-200 bg-gray-50/60 p-3 sm:p-4"
                >
                  <div
                    class="flex items-center justify-between gap-2 text-xs text-gray-500"
                  >
                    <h3>{{ card.title }}</h3>
                    <span>{{ card.tag }}</span>
                  </div>
                  <div
                    class="mt-3 break-words text-xl font-semibold tabular-nums text-gray-900 sm:text-2xl"
                  >
                    {{ card.value }}
                  </div>
                  <p
                    class="mt-2 min-h-5 break-words text-xs leading-5 text-gray-600"
                  >
                    {{ card.detail }}
                  </p>
                  <div
                    v-if="card.percent != null"
                    role="meter"
                    :aria-label="card.title"
                    :aria-valuenow="card.percent"
                    aria-valuemin="0"
                    aria-valuemax="100"
                    class="mt-3 h-1.5 overflow-hidden rounded-full bg-gray-200"
                  >
                    <div
                      class="h-full rounded-full"
                      :class="
                        card.percent >= 90
                          ? 'bg-red-500'
                          : card.percent >= 80
                            ? 'bg-amber-500'
                            : 'bg-blue-500'
                      "
                      :style="{ width: `${Math.min(100, card.percent)}%` }"
                    />
                  </div>
                </article>
              </div>
              <div class="flex flex-wrap gap-x-5 gap-y-2 text-xs text-gray-500">
                <span>应用已运行 {{ duration(latest.uptime_seconds) }}</span
                ><span
                  >系统负载
                  {{
                    latest.host.load_average
                      ?.map((n) => n.toFixed(2))
                      .join(" / ") || "未采集"
                  }}</span
                >
              </div>
            </template>
            <div class="rounded-xl border border-gray-200 p-4">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <h3 class="text-sm font-semibold text-gray-900">
                  近 24 小时资源趋势
                </h3>
                <span class="text-xs text-gray-500"
                  >每 30 分钟峰值 · 保留
                  {{ data?.retention_days ?? 7 }} 天采样</span
                >
              </div>
              <div
                class="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs text-gray-500"
              >
                <span class="text-blue-600">● 应用 CPU</span
                ><span class="text-violet-600">● 容器内存</span
                ><span class="text-emerald-600">● 系统内存</span>
              </div>
              <p
                v-if="!hasTrend"
                class="py-7 text-center text-sm text-gray-500"
              >
                趋势等待采样积累，未采集的数据不按零处理。
              </p>
              <div v-else class="relative mt-3 pl-9">
                <div
                  class="absolute inset-y-0 left-0 flex flex-col justify-between pb-6 pt-0.5 text-xs text-gray-400"
                  aria-hidden="true"
                >
                  <span>100%</span><span>50%</span><span>0%</span>
                </div>
                <svg
                  class="h-40 w-full"
                  viewBox="30 0 680 135"
                  preserveAspectRatio="none"
                  role="img"
                  aria-label="近24小时应用CPU、容器内存及系统内存占用峰值趋势，断线表示缺少采样"
                >
                  <g v-for="n in [0, 50, 100]" :key="n">
                    <line
                      x1="30"
                      x2="710"
                      :y1="130 - n * 1.2"
                      :y2="130 - n * 1.2"
                      stroke="#e5e7eb"
                      stroke-dasharray="4 4"
                    />
                  </g>
                  <g v-for="series in chart" :key="series.key">
                    <path
                      v-for="(path, i) in series.paths"
                      :key="i"
                      :d="path"
                      :stroke="series.color"
                      fill="none"
                      stroke-width="2"
                      vector-effect="non-scaling-stroke"
                    />
                  </g>
                </svg>
                <div class="mt-1 flex justify-between text-xs text-gray-400">
                  <span>24 小时前</span><span>现在</span>
                </div>
              </div>
            </div></TabsContent
          ><TabsContent
            v-show="activeTab === 'connections'"
            class="space-y-5"
            value="connections"
            force-mount
            ><div class="min-w-0 rounded-xl border border-gray-200 p-4">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <h3 class="text-sm font-semibold text-gray-900">连接健康</h3>
                <span class="text-xs text-gray-500"
                  >状态 {{ data?.sync_interval_seconds ?? "—" }} 秒 / SSH 检查
                  {{ data?.probe_interval_seconds ?? "—" }} 秒</span
                >
              </div>
              <p class="mt-2 text-xs leading-5 text-gray-500">
                从本实例检查 SSH 握手，不验证登录。内置 FRP
                走本机监听地址，不代表公网入口可达；其他协议暂不主动探测。
              </p>
              <div class="mt-3 divide-y divide-gray-100">
                <div
                  v-for="server in data?.servers || []"
                  :key="server.id"
                  class="flex items-start justify-between gap-3 py-2.5 text-sm"
                >
                  <div class="min-w-0">
                    <div class="break-all font-medium text-gray-800">
                      {{ server.name }}
                    </div>
                    <div class="mt-1 text-xs text-gray-500">
                      最近成功 {{ date(server.succeeded_at) }}
                    </div>
                    <p
                      v-if="server.status === 'failed'"
                      class="mt-1 break-words text-xs text-amber-800"
                    >
                      {{ server.message }}
                    </p>
                  </div>
                  <div class="shrink-0 text-right">
                    <span
                      :class="
                        server.status === 'success'
                          ? 'text-emerald-700'
                          : 'text-amber-700'
                      "
                      >{{ syncLabels[server.status] }}</span
                    >
                    <div
                      v-if="server.duration_ms != null"
                      class="mt-1 text-xs text-gray-500"
                    >
                      {{ server.duration_ms }} ms
                    </div>
                  </div>
                </div>
              </div>
              <p
                v-if="data?.servers.some((s) => s.status === 'failed')"
                class="mt-2 text-xs text-amber-800"
              >
                部分节点采集失败，代理保留上次状态，不代表当前在线。
              </p>
              <p class="mt-3 text-xs leading-5 text-gray-600">
                SSH 握手：{{ healthyProbes }} 正常 ·
                {{ failedProbes.length }} 异常 · {{ staleProbes }} 过期；共检查
                {{ data?.probes.length ?? 0 }} 条。
              </p>
              <div
                v-for="probe in failedProbes.slice(0, 4)"
                :key="`${probe.server}-${probe.name}`"
                class="mt-2 rounded-lg bg-amber-50 p-2.5 text-xs leading-5 text-amber-900"
              >
                <div class="break-all font-medium">
                  {{ probe.server }} / {{ probe.name }}
                </div>
                <div>{{ probe.message }}</div>
                <div class="text-amber-700">{{ date(probe.checked_at) }}</div>
              </div>
              <details v-if="failedProbes.length > 4" class="mt-3 text-xs">
                <summary class="cursor-pointer py-2 text-amber-800">
                  查看其余 {{ failedProbes.length - 4 }} 条异常
                </summary>
                <div
                  v-for="probe in failedProbes.slice(4)"
                  :key="`${probe.server}-${probe.name}`"
                  class="mt-2 break-words rounded-lg bg-amber-50 p-2.5 leading-5 text-amber-900"
                >
                  {{ probe.server }} / {{ probe.name }}：{{ probe.message }} ·
                  {{ date(probe.checked_at) }}
                </div>
              </details>
              <p v-if="!data?.probes.length" class="mt-2 text-xs text-gray-500">
                尚无 SSH 握手检查记录。
              </p>
            </div>
            <div
              v-if="data?.events.length"
              class="rounded-xl border border-gray-200 p-4"
            >
              <h3 class="text-sm font-semibold text-gray-900">近期连接变化</h3>
              <div class="mt-3 divide-y divide-gray-100">
                <div
                  v-for="(event, i) in data.events.slice(0, 6)"
                  :key="i"
                  class="flex flex-wrap justify-between gap-2 py-2 text-xs"
                >
                  <span class="break-all text-gray-700"
                    >{{
                      data.servers.find((s) => s.id === event.server_id)
                        ?.name || "历史节点"
                    }}
                    / {{ event.name }}
                    <span
                      :class="
                        event.action === 'offline'
                          ? 'text-amber-700'
                          : 'text-emerald-700'
                      "
                      >{{ eventLabels[event.action] }}</span
                    ></span
                  ><time class="text-gray-500">{{ date(event.at) }}</time>
                </div>
              </div>
              <p class="mt-2 text-xs text-gray-500">
                按采集发现时间记录，短于采集间隔的断线可能未被发现。
              </p>
            </div></TabsContent
          ><TabsContent
            v-show="activeTab === 'rdp'"
            class="space-y-5"
            value="rdp"
            force-mount
            ><div class="min-w-0 rounded-xl border border-gray-200 p-4">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <h3 class="text-sm font-semibold text-gray-900">
                  RDP 异常与防护
                </h3>
                <span
                  class="text-xs"
                  :class="rdp?.running ? 'text-emerald-700' : 'text-gray-500'"
                  >{{
                    rdp == null
                      ? "未采集"
                      : !rdp.enabled
                        ? "未启用"
                        : rdp.running
                          ? "运行中"
                          : "未运行"
                  }}</span
                >
              </div>
              <p class="mt-2 text-xs leading-5 text-gray-500">
                计数自本次应用启动累计；握手错误按连接计数，原生日志按错误行计数。
              </p>
              <dl v-if="rdp" class="mt-4 grid grid-cols-2 gap-4">
                <div v-for="item in rdpItems" :key="item.label">
                  <dt class="text-xs text-gray-500">{{ item.label }}</dt>
                  <dd
                    class="mt-1 text-xl font-semibold tabular-nums text-gray-900"
                  >
                    {{ item.value }}
                  </dd>
                </div>
              </dl>
              <p
                class="mt-4 rounded-lg bg-gray-50 p-3 text-xs leading-5 text-gray-600"
              >
                同一来源 5 分钟累计 10 次握手或认证失败，临时限制新连接 30
                分钟。已授权会话继续运行；重复错误每分钟汇总。
              </p>
            </div></TabsContent
          >
          <TabsContent v-if="activeTab === 'vnc'" value="vnc">
            <VncProtectionPanel :snapshot="data?.vnc" />
          </TabsContent>
          <TabsContent v-if="activeTab === 'ssh'" value="ssh"
            ><SshProtectionPanel
          /></TabsContent></div
      ></Card></div
  ></Tabs>
</template>

<script setup>
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import SshProtectionPanel from "@/components/SshProtectionPanel.vue";
import VncProtectionPanel from "@/components/VncProtectionPanel.vue";
import PageHeader from "@/components/PageHeader.vue";
import { computed, onMounted, onUnmounted, ref } from "vue";
import api from "@/api";
import { useRoute, useRouter } from "vue-router";

const loading = ref(false),
  data = ref(null),
  error = ref("");
const route = useRoute(),
  router = useRouter();
const tabs = [
  { key: "resources", label: "资源监控" },
  { key: "connections", label: "连接检查" },
  { key: "rdp", label: "RDP 防护" },
  { key: "ssh", label: "SSH 防护" },
  { key: "vnc", label: "VNC 防护" },
];
const activeTab = computed({
  get: () =>
    tabs.some((t) => t.key === route.query.tab) ? route.query.tab : "resources",
  set: (tab) => router.replace({ query: { ...route.query, tab } }),
});
let timer,
  disposed = false;
const latest = computed(() => data.value?.latest);
const rdp = computed(() => latest.value?.rdp);
const stale = computed(() => Boolean(error.value) || data.value?.sample_stale);
const failedProbes = computed(
  () => data.value?.probes.filter((p) => p.status === "failed") || [],
);
const healthyProbes = computed(
  () => data.value?.probes.filter((p) => p.status === "healthy").length || 0,
);
const staleProbes = computed(
  () => data.value?.probes.filter((p) => p.status === "stale").length || 0,
);
const attention = computed(
  () =>
    stale.value ||
    failedProbes.value.length ||
    staleProbes.value ||
    data.value?.servers.some((s) => s.status !== "success") ||
    rdp.value?.blocked_sources ||
    (rdp.value?.enabled && !rdp.value.running) ||
    data.value?.vnc?.needs_attention ||
    cards.value.some((c) => c.percent >= 90),
);
const healthText = computed(() =>
  !latest.value
    ? "等待采样"
    : stale.value
      ? "数据待更新"
      : attention.value
        ? "需关注"
        : "采集正常",
);
const syncLabels = {
  success: "采集正常",
  failed: "采集失败",
  stale: "数据过期",
  unknown: "尚未采集",
};
const eventLabels = { online: "上线", offline: "下线", discovered: "首次发现" };
const percent = (n) => (n == null ? "未采集" : `${n.toFixed(1)}%`);
function bytes(n) {
  if (n == null) return "未采集";
  const units = ["B", "KiB", "MiB", "GiB", "TiB"];
  let i = 0;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i++;
  }
  return `${n.toFixed(i ? 1 : 0)} ${units[i]}`;
}
function date(value) {
  return value
    ? new Date(value).toLocaleString("zh-CN", { hour12: false })
    : "尚无记录";
}
function duration(n) {
  return n == null
    ? "未采集"
    : `${Math.floor(n / 86400)} 天 ${Math.floor((n % 86400) / 3600)} 小时 ${Math.floor((n % 3600) / 60)} 分钟`;
}
const cards = computed(() => {
  if (!latest.value) return [];
  const { app, host, disk, scope } = latest.value;
  return [
    {
      title: scope === "container" ? "本容器 CPU" : "应用主进程 CPU",
      tag: `可用 ${app.cpu_cores} 核`,
      value: app.cpu_percent == null ? "等待采样" : percent(app.cpu_percent),
      percent: app.cpu_percent,
      detail: `按可用核数归一化；系统 CPU ${percent(host.cpu_percent)}`,
    },
    {
      title: scope === "container" ? "本容器内存" : "应用主进程内存",
      tag:
        app.memory_percent == null
          ? "未采集占比"
          : `已用 ${percent(app.memory_percent)}`,
      value: bytes(app.memory_used_bytes),
      percent: app.memory_percent,
      detail: app.memory_limit_bytes
        ? `限额 ${bytes(app.memory_limit_bytes)}；已扣除可回收文件缓存`
        : scope === "container"
          ? "无独立限额或限制信息不可读取"
          : "主进程驻留内存，不含子进程",
    },
    {
      title: "系统可见内存",
      tag:
        host.memory_percent == null
          ? "未采集"
          : `已用 ${percent(host.memory_percent)}`,
      value: bytes(host.memory_available_bytes),
      percent: host.memory_percent,
      detail: `当前可用 / 总计 ${bytes(host.memory_total_bytes)}`,
    },
    {
      title: "数据盘空间",
      tag: disk?.percent == null ? "未采集" : `已用 ${percent(disk.percent)}`,
      value: bytes(disk?.free_bytes),
      percent: disk?.percent,
      detail: `当前可用 / 总计 ${bytes(disk?.total_bytes)}；按数据目录所在文件系统统计`,
    },
  ];
});
const rdpItems = computed(() => [
  { label: "当前连接", value: rdp.value.active },
  { label: "临时限制来源", value: rdp.value.blocked_sources },
  { label: "握手失败", value: rdp.value.counts.handshake_failures || 0 },
  { label: "已拦截新连接", value: rdp.value.counts.rejected || 0 },
  { label: "认证失败", value: rdp.value.counts.auth_failures || 0 },
  { label: "桌面连接成功", value: rdp.value.counts.desktop_connected || 0 },
  { label: "网关上游异常", value: rdp.value.counts.upstream_errors || 0 },
  { label: "原生日志错误行", value: rdp.value.counts.native_error_lines || 0 },
]);
const hasTrend = computed(() => data.value?.history.length >= 2);
const chart = computed(() => {
  const origin = Date.parse(data.value?.now) - 86400000;
  return [
    { key: "cpu_percent", color: "#2563eb" },
    { key: "memory_percent", color: "#8b5cf6" },
    { key: "host_memory_percent", color: "#059669" },
  ].map((series) => {
    const paths = [];
    let current = "",
      previous = null;
    for (const point of data.value?.history || []) {
      const at = Date.parse(point.at),
        value = point[series.key];
      if (value == null || (previous != null && at - previous > 1800000)) {
        if (current) paths.push(current);
        current = "";
      }
      if (value != null) {
        const x = Math.max(
            30,
            Math.min(710, 30 + ((at - origin) / 86400000) * 680),
          ),
          y = 130 - Math.min(100, value) * 1.2;
        current += `${current ? " L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
      }
      previous = at;
    }
    if (current) paths.push(current);
    return { ...series, paths };
  });
});
async function refresh() {
  if (loading.value || disposed) return;
  loading.value = true;
  try {
    data.value = await api.get("/system/overview");
    error.value = "";
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}
async function poll() {
  if (disposed) return;
  if (!document.hidden) await refresh();
  if (!disposed) timer = setTimeout(poll, 30000);
}
function visible() {
  if (!document.hidden) refresh();
}
onMounted(async () => {
  document.addEventListener("visibilitychange", visible);
  await poll();
});
onUnmounted(() => {
  disposed = true;
  clearTimeout(timer);
  document.removeEventListener("visibilitychange", visible);
});
</script>
