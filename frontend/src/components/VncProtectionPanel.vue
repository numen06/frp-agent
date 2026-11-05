<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h3 class="text-sm font-semibold text-gray-900">VNC 会话与防护</h3>
      <Button as-child variant="outline"><RouterLink to="/hosts?host_type=vnc">管理 VNC 连接</RouterLink></Button>
    </div>
    <p v-if="!snapshot" role="status" class="text-sm text-gray-500">VNC 运行数据尚不可用，请刷新重试。</p>
    <template v-else>
      <p class="text-xs leading-5 text-gray-500">读取于 {{ date(snapshot.collected_at) }}。近 24 小时按审计记录汇总；流量仅包含已结束会话，不表示当前在线人数。刷新失败时保留上次数据。</p>
      <dl class="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <div v-for="item in metrics" :key="item.label" class="min-w-0 rounded-xl border border-gray-200 p-4">
          <dt class="text-xs text-gray-500">{{ item.label }}</dt>
          <dd class="mt-2 break-words text-xl font-semibold tabular-nums text-gray-900">{{ item.value }}</dd>
        </div>
      </dl>
      <div class="rounded-xl border border-gray-200 p-4">
        <h4 class="text-sm font-semibold text-gray-900">连接安全策略</h4>
        <p class="mt-2 text-sm leading-6 text-gray-600">浏览器必须通过同源 WSS，平台校验连接权限。VNC 直连限可信内网、VPN 或 FRP 内部入口；可选 SSH 隧道核验固定指纹后访问回环地址。VNC 密码由服务器代填，拒绝无密码服务。</p>
        <p class="mt-2 text-xs leading-5 text-gray-500">每个工作进程最多 16 个会话，每个账号最多 2 个；最长 60 分钟，客户端无数据 15 分钟结束。每 5 秒复核授权和凭据变化；桌面轮询也计为客户端数据。</p>
      </div>
      <div class="rounded-xl border border-gray-200 p-4">
        <h4 class="text-sm font-semibold text-gray-900">VNC 服务配置与上次检查</h4>
        <p class="mt-2 text-xs leading-5 text-gray-500">配置检查不连接目标或尝试密码。上次手动检查结果仅反映当时状态；进入主机详情可重新测试并查看审计。</p>
        <p v-if="!snapshot.hosts.length" class="mt-4 text-sm text-gray-500">尚未添加 VNC 连接服务。</p>
        <ul v-else class="mt-3 divide-y divide-gray-100">
          <li v-for="host in snapshot.hosts" :key="host.id" class="flex min-w-0 flex-wrap items-start justify-between gap-3 py-3">
            <div class="min-w-0 flex-1 basis-48 break-words">
              <p class="font-medium text-gray-900">{{ host.name }}<span v-if="!host.enabled" class="ml-2 text-xs font-normal text-gray-500">已停用</span></p>
              <p class="mt-1 text-xs text-gray-500">{{ host.transport === 'direct' ? 'VNC 直连（可信网络）' : `SSH 隧道：${host.ssh_name || '未关联'}` }}</p>
              <p v-if="host.issues.length" class="mt-1 text-sm text-amber-700">{{ host.issues.join('；') }}</p>
              <p v-else class="mt-1 text-sm text-emerald-700">必要配置齐全</p>
              <p class="mt-1 text-xs text-gray-500">{{ checkLabels[host.check_status] || '尚未检测' }} · {{ date(host.checked_at) }}</p>
            </div>
            <Button as-child variant="outline"><RouterLink :to="`/hosts/${host.id}`" :aria-label="`查看 ${host.name}`">查看详情</RouterLink></Button>
          </li>
        </ul>
        <p v-if="snapshot.truncated" class="mt-2 text-xs text-gray-500">仅展示前 100 台，完整列表请进入主机管理。</p>
      </div>
      <div class="rounded-xl border border-gray-200 p-4">
        <h4 class="text-sm font-semibold text-gray-900">近期异常结束</h4>
        <p v-if="!snapshot.failures.length" class="mt-3 text-sm text-gray-500">近 24 小时暂无异常会话审计记录。</p>
        <ul v-else class="mt-3 space-y-2">
          <li v-for="(item, index) in snapshot.failures" :key="index" class="flex min-w-0 flex-wrap items-center justify-between gap-2 text-sm">
            <RouterLink :to="`/hosts/${item.host_id}?tab=logs`" class="inline-flex min-h-11 min-w-0 items-center break-all text-blue-600 underline">{{ item.name }}</RouterLink>
            <span class="text-xs text-gray-500">{{ date(item.at) }}</span>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import { Button } from '@/components/ui/button';
const props = defineProps({ snapshot: { type: Object, default: null } });
const date = (value) => value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '尚无记录';
const checkLabels = { online: '上次检查通过', offline: '上次检查失败', error: '上次检查失败', unknown: '尚未检测' };
function bytes(value) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KiB`;
  if (value < 1024 ** 3) return `${(value / 1024 ** 2).toFixed(1)} MiB`;
  return `${(value / 1024 ** 3).toFixed(1)} GiB`;
}
const metrics = computed(() => props.snapshot ? [
  { label: '已启用 / 全部 VNC 服务', value: `${props.snapshot.enabled} / ${props.snapshot.total}` },
  { label: '启用服务配置隐患', value: props.snapshot.needs_attention },
  { label: '24 小时桌面连接成功', value: props.snapshot.connected },
  { label: '24 小时异常结束', value: props.snapshot.failed },
  { label: '24 小时已结束会话', value: props.snapshot.ended },
  { label: '已结束会话上传', value: bytes(props.snapshot.bytes_sent) },
  { label: '已结束会话下载', value: bytes(props.snapshot.bytes_received) },
] : []);
</script>
