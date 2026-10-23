<template>
  <section class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-gray-200 p-4">
      <h2 class="font-semibold">访问审计与流量统计</h2>
      <div class="flex flex-wrap gap-2">
        <button type="button" class="btn btn-sm btn-outline" :disabled="list.loading.value" @click="reload">刷新</button>
        <button v-if="isAdmin" type="button" class="btn btn-sm btn-outline text-red-600" :disabled="!selected.length || maintaining" @click="removeSelected">删除所选（{{ selected.length }}）</button>
        <button v-if="isAdmin" type="button" class="btn btn-sm btn-outline" @click="cleanupOpen = true">清理旧日志</button>
      </div>
    </div>
    <form class="grid gap-2 border-b border-gray-200 p-4 sm:grid-cols-2 xl:grid-cols-4" @submit.prevent="applyFilters">
      <input v-model="list.search.value" aria-label="搜索审计日志" placeholder="主机 / 操作者 / IP / 命令" class="min-w-0 rounded-lg border border-gray-300 px-3 py-2 text-sm">
      <RemoteSelect v-model="filters.host_id" label="筛选主机" :fetch-options="managedHostsApi.list" :resolve-option="resolveHost" allow-clear clear-label="全部主机" />
      <AppSelect v-model="filters.action" aria-label="审计动作"><option value="">全部动作</option><option v-for="(label, key) in actions" :key="key" :value="key">{{ label }}</option></AppSelect>
      <AppSelect v-model="filters.status" aria-label="审计结果"><option value="">全部结果</option><option value="success">成功</option><option value="failed">失败</option></AppSelect>
      <label class="min-w-0 text-xs text-gray-500">开始时间<input v-model="filters.start_time" type="datetime-local" aria-label="审计开始时间" class="mt-1 block w-full min-w-0 rounded-lg border border-gray-300 px-3 py-2"></label>
      <label class="min-w-0 text-xs text-gray-500">结束时间<input v-model="filters.end_time" type="datetime-local" aria-label="审计结束时间" class="mt-1 block w-full min-w-0 rounded-lg border border-gray-300 px-3 py-2"></label>
      <div class="flex items-end gap-2"><button type="submit" class="btn btn-md btn-primary" :disabled="list.loading.value">查询</button><button type="button" class="btn btn-md btn-outline" @click="resetFilters">重置</button></div>
    </form>
    <div v-if="summary" class="border-b border-gray-200 p-4">
      <dl class="grid gap-3 text-sm sm:grid-cols-3">
        <div class="rounded-lg bg-blue-50 p-3"><dt class="text-xs text-gray-500">发送到主机</dt><dd class="mt-1 text-lg font-semibold">{{ formatBytes(summary.bytes_sent) }}</dd></div>
        <div class="rounded-lg bg-emerald-50 p-3"><dt class="text-xs text-gray-500">从主机接收</dt><dd class="mt-1 text-lg font-semibold">{{ formatBytes(summary.bytes_received) }}</dd></div>
        <div class="rounded-lg bg-gray-50 p-3"><dt class="text-xs text-gray-500">已采集的访问 / 操作</dt><dd class="mt-1 text-lg font-semibold">{{ summary.measured_count }} 次</dd></div>
      </dl>
      <p class="mt-3 text-xs leading-5 text-gray-500">累计当前筛选条件下所有保留记录，连接或操作结束后入账；清理日志会同步减少统计。发送/接收按平台到主机方向，SSH/RDP 统计应用数据（不含加密开销），Docker 统计请求/响应正文。旧记录及未采集的操作显示“未采集”。</p>
    </div>
    <p v-if="list.error.value || error" role="alert" class="p-4 text-sm text-red-600">{{ list.error.value || error }}</p>
    <p v-if="notice" role="status" class="px-4 py-2 text-sm text-emerald-700">{{ notice }}</p>
    <p v-if="list.loading.value" role="status" class="p-6 text-center text-sm text-gray-500">正在加载日志…</p>
    <template v-else>
      <div class="hidden overflow-x-auto md:block">
        <table class="w-full min-w-[1000px] text-left text-sm">
          <thead class="bg-gray-50 text-xs text-gray-500"><tr>
            <th v-if="isAdmin" class="px-4 py-3"><input type="checkbox" aria-label="选择本页日志" :checked="allSelected" @change="toggleAll"></th>
            <th class="px-4 py-3">时间</th><th class="px-4 py-3">操作者</th><th class="px-4 py-3">主机</th><th class="px-4 py-3">动作</th><th class="px-4 py-3">目标/命令</th><th class="px-4 py-3">结果</th><th class="px-4 py-3">发送 / 接收</th><th class="px-4 py-3">来源 IP</th><th class="px-4 py-3">详情</th>
          </tr></thead>
          <tbody><tr v-for="log in list.items.value" :key="log.id" class="border-t border-gray-100">
            <td v-if="isAdmin" class="px-4 py-3"><input v-model="selected" type="checkbox" :value="log.id" :aria-label="`选择日志 ${log.id}`"></td>
            <td class="whitespace-nowrap px-4 py-3 text-xs">{{ date(log.created_at) }}</td><td class="px-4 py-3">{{ log.actor_name }}</td><td class="px-4 py-3">{{ log.host_name }}</td><td class="px-4 py-3">{{ actions[log.action] || log.action }}</td>
            <td class="max-w-xs truncate px-4 py-3 font-mono text-xs" :title="log.command || log.target">{{ log.command || log.target || '-' }}</td>
            <td class="px-4 py-3" :class="log.status === 'success' ? 'text-emerald-600' : 'text-red-600'">{{ log.status }}</td><td class="whitespace-nowrap px-4 py-3 text-xs">{{ formatBytes(log.bytes_sent) }} / {{ formatBytes(log.bytes_received) }}</td><td class="px-4 py-3 text-xs">{{ log.client_ip || '-' }}</td>
            <td class="px-4 py-3"><button type="button" class="btn btn-sm btn-outline" @click="showDetail(log.id)">详情</button></td>
          </tr></tbody>
        </table>
      </div>
      <div class="divide-y divide-gray-100 md:hidden">
        <article v-for="log in list.items.value" :key="log.id" class="space-y-2 p-4">
          <div class="flex items-start justify-between gap-2"><label class="flex min-w-0 items-center gap-2"><input v-if="isAdmin" v-model="selected" type="checkbox" :value="log.id" :aria-label="`选择日志 ${log.id}`"><span class="break-all font-medium">{{ log.host_name }}</span></label><span class="shrink-0 text-sm" :class="log.status === 'success' ? 'text-emerald-600' : 'text-red-600'">{{ log.status }}</span></div>
          <p class="text-xs text-gray-500">{{ log.actor_name }} · {{ date(log.created_at) }}</p>
          <p class="text-sm">{{ actions[log.action] || log.action }}</p>
          <p class="text-xs text-gray-600">发送 {{ formatBytes(log.bytes_sent) }} · 接收 {{ formatBytes(log.bytes_received) }}</p>
          <pre v-if="log.command || log.target" class="overflow-auto rounded-lg bg-gray-50 p-2 text-xs">{{ log.command || log.target }}</pre>
          <div class="flex flex-wrap items-center justify-between gap-2"><span class="break-all text-xs text-gray-500">来源：{{ log.client_ip || '-' }}</span><button type="button" class="btn btn-sm btn-outline" @click="showDetail(log.id)">详情</button></div>
        </article>
      </div>
      <p v-if="!list.items.value.length" class="p-8 text-center text-sm text-gray-500">暂无审计记录</p>
    </template>
    <div class="border-t border-gray-200 p-4"><TablePagination :total="list.pagination.total" :page="list.pagination.page" :page-size="list.pagination.page_size" @page-change="changePage" @page-size-change="resize" /></div>
  </section>
  <AppDialog v-model="detailOpen" title="审计日志详情">
    <p v-if="!detail" class="text-sm text-gray-500">正在加载详情…</p>
    <template v-else>
      <dl class="grid grid-cols-[auto_1fr] gap-3 text-sm"><dt>时间</dt><dd>{{ date(detail.created_at) }}</dd><dt>主机</dt><dd class="break-all">{{ detail.host_name }}</dd><dt>操作者</dt><dd>{{ detail.actor_name }}（{{ detail.actor_type }}）</dd><dt>动作</dt><dd>{{ actions[detail.action] || detail.action }}</dd><dt>来源 IP</dt><dd>{{ detail.client_ip || '-' }}</dd><dt>结果</dt><dd>{{ detail.status }} · 退出码 {{ detail.exit_code ?? '-' }} · {{ detail.duration_ms ?? '-' }}ms</dd></dl>
      <div v-for="field in detailFields" :key="field.key" class="mt-4"><h3 class="mb-1 text-sm font-medium">{{ field.label }}</h3><pre class="max-h-64 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-gray-50 p-3 text-xs">{{ detail[field.key] || '-' }}</pre></div>
      <p class="mt-4 text-sm">发送到主机 {{ formatBytes(detail.bytes_sent) }} · 从主机接收 {{ formatBytes(detail.bytes_received) }}</p>
    </template>
    <template #footer><button type="button" class="btn btn-md btn-outline" @click="detailOpen = false">关闭详情</button></template>
  </AppDialog>
  <AppDialog v-model="cleanupOpen" title="清理旧日志" :busy="maintaining" panel-class="max-w-xl">
    <p class="mb-4 text-sm text-gray-600">仅删除超过保留天数的日志。{{ filters.host_id ? '范围：当前筛选主机。' : '范围：全部主机。' }}该操作会保留新的清理审计记录。</p>
    <label class="text-sm">保留最近天数<input v-model.number="keepDays" :disabled="maintaining" type="number" min="1" max="3650" class="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2"></label>
    <p v-if="preview !== null" class="mt-4 text-sm text-red-600">预计删除 {{ preview }} 条旧日志，删除后不可恢复。</p>
    <p v-if="error" role="alert" class="mt-3 text-sm text-red-600">{{ error }}</p>
    <template #footer><button type="button" class="btn btn-md btn-outline" :disabled="maintaining" @click="previewCleanup">预览影响数量</button><button type="button" class="btn btn-md btn-danger" :disabled="!preview || maintaining" @click="cleanup">确认清理</button></template>
  </AppDialog>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import AppDialog from './AppDialog.vue'
import AppSelect from './AppSelect.vue'
import RemoteSelect from './RemoteSelect.vue'
import TablePagination from './TablePagination.vue'
import { managedHostsApi } from '@/api/managedHosts'
import { usePagedList } from '@/composables/usePagedList'
import { formatBytes } from '@/utils/traffic'
const props = defineProps({ isAdmin: Boolean, hostId: { type: [Number, String], default: '' } })
const filters = reactive({ host_id: props.hostId, action: '', status: '', start_time: '', end_time: '' })
let applied = props.hostId ? { host_id: props.hostId } : {}
const summary = ref(null)
let requestId = 0
const list = usePagedList(async params => {
  const id = ++requestId
  summary.value = null
  const query = { ...params, ...applied }
  const [data, traffic] = await Promise.all([managedHostsApi.audit(query), managedHostsApi.traffic(query)])
  if (id === requestId) summary.value = traffic
  return data
})
const selected = ref([]), error = ref(''), notice = ref(''), maintaining = ref(false)
const detailOpen = ref(false), detail = ref(null), cleanupOpen = ref(false), keepDays = ref(90), preview = ref(null)
const detailFields = [{ key: 'target', label: '目标' }, { key: 'command', label: '命令' }, { key: 'stdout', label: '标准输出' }, { key: 'stderr', label: '错误输出' }]
const actions = { connection_test: '连接测试', execute_command: '执行命令', execute_sudo_command: '提权执行', ssh_gateway_session: 'SSH 跳板会话', docker_gateway_request: 'Docker 网关请求', docker_list: '查询容器', docker_start: '启动容器', docker_stop: '停止容器', docker_restart: '重启容器', rdp_file_downloaded: '下载 RDP 连接', rdp_desktop_connected: 'RDP 桌面已连接', rdp_gateway_authorized: 'RDP 网关授权', rdp_gateway_closed: 'RDP 网关断开', audit_logs_deleted: '清理审计日志' }
const allSelected = computed(() => list.items.value.length > 0 && list.items.value.every(row => selected.value.includes(row.id)))
const date = value => value ? new Date(value.endsWith('Z') || /[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`).toLocaleString('zh-CN') : '-'
const resolveHost = async id => (await managedHostsApi.list({ page: 1, host_id: id })).items[0]
const reload = () => list.load()
async function changePage(page) { selected.value = []; await list.load(page) }
async function resize(size) { selected.value = []; await list.resize(size) }
function toggleAll() { selected.value = allSelected.value ? [] : list.items.value.map(row => row.id) }
async function applyFilters() {
  error.value = ''
  if (filters.start_time && filters.end_time && filters.start_time > filters.end_time) { error.value = '开始时间不能晚于结束时间'; return }
  applied = Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== '').map(([key, value]) => [key, key.endsWith('_time') ? new Date(value).toISOString() : value]))
  await changePage(1)
}
function resetFilters() { Object.keys(filters).forEach(key => filters[key] = ''); list.search.value = ''; applyFilters() }
async function showDetail(id) {
  detail.value = null; detailOpen.value = true
  try { detail.value = await managedHostsApi.auditDetail(id) } catch (e) { error.value = e.message; detailOpen.value = false }
}
async function removeSelected() {
  if (!selected.value.length || !confirm(`确定删除所选 ${selected.value.length} 条日志？删除后不可恢复。`)) return
  maintaining.value = true; error.value = ''
  try { const result = await managedHostsApi.deleteAudit(selected.value); notice.value = `已删除 ${result.deleted} 条日志`; selected.value = []; await list.load() } catch (e) { error.value = e.message } finally { maintaining.value = false }
}
watch([keepDays, () => filters.host_id, cleanupOpen], () => { preview.value = null; error.value = '' })
async function previewCleanup() {
  if (!Number.isInteger(keepDays.value) || keepDays.value < 1 || keepDays.value > 3650) { error.value = '保留天数必须为 1–3650 的整数'; return }
  maintaining.value = true; error.value = ''
  try { const result = await managedHostsApi.cleanupAudit({ keep_days: keepDays.value, host_id: filters.host_id || undefined, dry_run: true }); preview.value = result.count } catch (e) { error.value = e.message } finally { maintaining.value = false }
}
async function cleanup() {
  if (!preview.value || !confirm(`确定清理超过 ${keepDays.value} 天的旧日志（预计 ${preview.value} 条）？`)) return
  maintaining.value = true; error.value = ''
  try { const result = await managedHostsApi.cleanupAudit({ keep_days: keepDays.value, host_id: filters.host_id || undefined, dry_run: false }); notice.value = `已清理 ${result.deleted} 条旧日志`; cleanupOpen.value = false; selected.value = []; await list.load() } catch (e) { error.value = e.message } finally { maintaining.value = false }
}
defineExpose({ load: reload })
watch(() => props.hostId, value => { filters.host_id = value; applyFilters() })
onMounted(() => list.load(1))
</script>
