<template>
  <section v-if="isAdmin" id="builtin-frps" class="rounded-xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div><h2 class="font-semibold text-gray-900">内置 FRP 服务端</h2><p class="mt-1 text-xs text-gray-500">镜像已包含官方 frps，启用后自动加入服务器列表，复用代理管理和流量统计。</p></div>
      <span v-if="status" class="rounded-full px-3 py-1 text-xs" :class="status.running ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-600'">{{ status.running ? '运行中' : status.enabled ? '已启用，未运行' : '未启用' }}{{ status.version ? ` · ${status.version}` : '' }}</span>
    </div>
    <p v-if="error" role="alert" class="mt-3 text-sm text-red-600">{{ error }}</p>
    <p v-if="notice" role="status" class="mt-3 text-sm text-emerald-700">{{ notice }}</p>
    <p v-if="!status" class="mt-4 text-sm text-gray-500">正在读取配置…</p>
    <form v-else class="mt-4 space-y-4" @submit.prevent="save">
      <label class="flex min-h-10 items-center gap-3 text-sm font-medium"><input v-model="form.enabled" type="checkbox" :disabled="busy">启用内置 FRP</label>
      <p v-if="!status.available" class="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">当前环境未安装 frps。请使用包含 FRP 的新版镜像；本地开发可通过 BUILTIN_FRPS_BINARY 指定程序路径。</p>
      <label class="block max-w-lg text-sm">公网 IP / 域名<input v-model="form.public_addr" :required="form.enabled" :disabled="busy" maxlength="255" placeholder="客户端访问的服务器地址" class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2"></label>
      <div class="flex flex-wrap gap-2 border-b border-gray-200 pb-3" role="tablist" aria-label="内置 FRP 配置分类">
        <button v-for="item in tabs" :key="item.key" type="button" role="tab" :aria-selected="activeTab === item.key" :disabled="busy" class="btn btn-sm" :class="activeTab === item.key ? 'btn-primary' : 'btn-outline'" @click="selectTab(item.key)">{{ item.label }}</button>
      </div>
      <fieldset v-if="activeTab === 'basic'" :disabled="busy" class="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
        <label>监听地址<input v-model="form.bind_addr" class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2"></label>
        <label>代理监听地址<input v-model="form.proxy_bind_addr" placeholder="留空与监听地址相同" class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2"></label>
        <label v-for="field in ports" :key="field.key">{{ field.label }}<input v-model.number="form[field.key]" type="number" required :min="field.min ?? 1" max="65535" class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2"></label>
        <label>日志级别<select v-model="form.log_level" aria-label="日志级别" class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2"><option v-for="level in ['info', 'warn', 'error', 'debug', 'trace']" :key="level">{{ level }}</option></select></label>
      </fieldset>
      <fieldset v-else-if="activeTab === 'security'" :disabled="busy" class="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
        <label>连接 Token<input v-model="form.auth_token" type="password" autocomplete="new-password" minlength="16" maxlength="255" placeholder="默认自动生成，可填写新 Token 修改" aria-describedby="builtin-frps-token-help" class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2"></label>
        <label class="flex items-center gap-2"><input v-model="form.tls_force" type="checkbox">仅允许 TLS 加密的客户端连接</label>
        <label>每客户端最大代理端口数<input v-model.number="form.max_ports_per_client" type="number" min="0" max="65535" placeholder="0 表示不额外限制" class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2"></label>
        <label v-for="field in certificates" :key="field.key">{{ field.label }}<input v-model="form[field.key]" maxlength="1024" placeholder="可选，填写容器内文件路径" class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2"></label>
        <div class="space-y-2"><p>额外 Token 校验</p><label v-for="scope in scopes" :key="scope.value" class="flex items-center gap-2"><input v-model="form.auth_additional_scopes" type="checkbox" :value="scope.value">{{ scope.label }}</label></div>
        <p class="text-xs leading-5 text-gray-500 sm:col-span-2 lg:col-span-3">默认无需原始配置：自动生成随机 Token、启用 TLS、限制代理端口，内部管理接口只监听回环地址。证书路径为容器内路径，证书和私钥须配对；填写客户端 CA 后需给客户端配置相应证书。额外校验选项会同步写入本平台生成的客户端配置。</p>
      </fieldset>
      <fieldset v-else-if="activeTab === 'plugins'" :disabled="busy" class="space-y-3">
        <p class="text-xs leading-5 text-gray-500">配置 frps HTTP 回调插件（httpPlugins）。插件服务独立运行；同一 Docker 网络可用服务名:端口，127.0.0.1 指本容器。HTTPS 插件默认校验证书。保存基础设置会保留插件和其他高级参数。</p>
        <p v-if="!form.http_plugins.length" class="rounded-lg bg-gray-50 p-4 text-sm text-gray-500">未启用插件，默认配置无需插件服务。</p>
        <article v-for="(plugin, index) in form.http_plugins" :key="index" class="space-y-3 rounded-lg border border-gray-200 p-3">
          <div class="grid gap-3 text-sm sm:grid-cols-3"><label>插件名称<input v-model="plugin.name" required maxlength="100" class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2"></label><label>插件地址<input v-model="plugin.addr" required placeholder="plugin-service:9000" class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2"></label><label>回调路径<input v-model="plugin.path" required placeholder="/handler" class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2"></label></div>
          <div class="flex flex-wrap gap-3 text-xs"><label v-for="op in pluginOperations" :key="op" class="flex items-center gap-1.5"><input v-model="plugin.ops" type="checkbox" :value="op">{{ op }}</label></div>
          <div class="flex flex-wrap items-center justify-between gap-3 text-sm"><label class="flex items-center gap-2"><input v-model="plugin.tls_verify" type="checkbox">校验 HTTPS 插件证书</label><button type="button" class="btn btn-sm btn-outline text-red-600" @click="form.http_plugins.splice(index, 1)">删除此插件</button></div>
        </article>
        <button type="button" class="btn btn-sm btn-outline" @click="addPlugin">添加插件</button>
      </fieldset>
      <div v-else-if="activeTab === 'raw'" class="space-y-3">
        <p class="text-xs leading-5 text-gray-500">直接编辑完整 frps.toml，包含连接凭据，仅管理员可见。保存原始文件保留文本及注释；表单修改会保留插件和高级参数，必要时整理 TOML 格式。管理接口须保留 127.0.0.1 和内部认证，客户端认证使用 Token。</p>
        <p v-if="rawDirty" role="status" class="text-xs text-amber-700">原始配置有未保存的修改。校验不会启动服务；保存成功后才会应用配置。</p>
        <div class="min-w-0" role="group" aria-label="frps.toml 原始配置"><CodeEditor v-model="rawContent" language="toml" height="420px" :readonly="busy" :line-wrapping="true" /></div>
        <div class="flex flex-wrap gap-2"><button type="button" class="btn btn-sm btn-outline" :disabled="busy || !status.available" @click="validateRaw">仅校验原始配置</button><button type="button" class="btn btn-sm btn-outline" :disabled="busy" @click="readRaw">{{ rawDirty ? '放弃草稿并读取已保存配置' : '读取已保存配置' }}</button></div>
      </div>
      <p v-if="activeTab === 'security'" id="builtin-frps-token-help" class="text-xs leading-5 text-gray-500">连接 Token 默认自动生成，可查看和复制。留空保留已有值；填写新 Token（至少 16 个字符）并保存即可修改，客户端配置也需同步更新。</p>
      <p class="text-xs leading-5 text-gray-500">管理 API 只监听容器内部 127.0.0.1。Docker 默认映射 7000 和 6000–6099（TCP/UDP）；修改端口、扩大范围或启用 HTTP/HTTPS 后，需要同时调整 Docker 端口映射及防火墙。保存启用配置会重启内置 FRP，现有连接会短暂断开。</p>
      <p v-if="status.error" role="alert" class="text-sm text-red-600">{{ status.error }}</p>
      <div class="flex flex-wrap gap-2">
        <button class="btn btn-md btn-primary" :disabled="busy || (form.enabled && !status.available)">{{ busy ? '正在应用…' : '保存并应用' }}</button>
        <button type="button" class="btn btn-md btn-outline" :disabled="busy || !status.enabled || rawDirty" @click="restart">重启服务</button>
        <button type="button" class="btn btn-md btn-outline" :disabled="busy" @click="load(true)">重新读取</button>
        <button type="button" class="btn btn-md btn-outline" :disabled="busy" @click="showToken">{{ token ? '隐藏 Token' : '查看连接 Token' }}</button>
      </div>
      <div v-if="token" class="flex flex-wrap items-center gap-2 rounded-lg bg-gray-50 p-3"><code class="break-all text-xs">{{ token }}</code><button type="button" class="btn btn-sm btn-outline" @click="copyToken">复制 Token</button></div>
      <details v-if="status.logs?.length" class="text-xs text-gray-500"><summary class="cursor-pointer py-2">最近运行日志</summary><pre class="max-h-48 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-gray-950 p-3 text-gray-100">{{ status.logs.join('\n') }}</pre></details>
    </form>
  </section>
</template>

<script setup>
import { computed, defineAsyncComponent, onMounted, onUnmounted, reactive, ref } from 'vue'
import { builtinFrpsApi } from '@/api/builtinFrps'
import { settingsApi } from '@/api/settings'
import { copyWithTooltip } from '@/composables/useCopyTooltip'

const emit = defineEmits(['changed'])
const CodeEditor = defineAsyncComponent(() => import('./CodeEditor.vue'))
const isAdmin = ref(false), status = ref(null), error = ref(''), notice = ref(''), busy = ref(false), token = ref('')
const form = reactive({ enabled: false, public_addr: '', bind_port: 7000, dashboard_port: 7500, proxy_port_start: 6000, proxy_port_end: 6099, vhost_http_port: 0, vhost_https_port: 0, tls_force: true, auth_token: '', bind_addr: '0.0.0.0', proxy_bind_addr: '', kcp_bind_port: 0, quic_bind_port: 0, tls_cert_file: '', tls_key_file: '', tls_trusted_ca_file: '', auth_additional_scopes: [], max_ports_per_client: 0, log_level: 'info', http_plugins: [], allowed_port_ranges: null })
const tabs = [{ key: 'basic', label: '基础配置' }, { key: 'security', label: '安全设置' }, { key: 'plugins', label: '插件' }, { key: 'raw', label: '原始配置文件' }]
const activeTab = ref('basic'), rawContent = ref(''), rawBaseline = ref(''), rawRevision = ref(null), previewDirty = ref(false)
const rawDirty = computed(() => previewDirty.value || rawContent.value !== rawBaseline.value)
const pluginOperations = ['Login', 'NewProxy', 'CloseProxy', 'Ping', 'NewWorkConn', 'NewUserConn']
const scopes = [{ value: 'HeartBeats', label: '心跳认证' }, { value: 'NewWorkConns', label: '工作连接认证' }]
const certificates = [{ key: 'tls_cert_file', label: '服务端 TLS 证书' }, { key: 'tls_key_file', label: '服务端 TLS 私钥' }, { key: 'tls_trusted_ca_file', label: '客户端证书 CA' }]
const ports = [
  { key: 'bind_port', label: '客户端控制端口' }, { key: 'dashboard_port', label: '内部管理端口' },
  { key: 'proxy_port_start', label: '允许的代理起始端口' }, { key: 'proxy_port_end', label: '允许的代理结束端口' },
  { key: 'vhost_http_port', label: 'HTTP 代理端口（0 关闭）', min: 0 }, { key: 'vhost_https_port', label: 'HTTPS 代理端口（0 关闭）', min: 0 },
  { key: 'kcp_bind_port', label: 'KCP UDP 端口（0 关闭）', min: 0 }, { key: 'quic_bind_port', label: 'QUIC UDP 端口（0 关闭）', min: 0 }
]
let timer, requestId = 0, disposed = false
function updateForm(data) {
  for (const key of Object.keys(form)) if (key !== 'auth_token' && data[key] !== undefined) form[key] = JSON.parse(JSON.stringify(data[key]))
  form.public_addr ||= window.location.hostname
  form.auth_token = ''; token.value = ''
}
const payload = () => ({ ...form, auth_token: form.auth_token || null })
const rawPayload = () => ({ enabled: form.enabled, public_addr: form.public_addr, content: rawContent.value, revision: rawRevision.value })
function setRaw(data) { rawContent.value = data.content; rawBaseline.value = data.content; rawRevision.value = data.revision; previewDirty.value = Boolean(data.changed) }
async function selectTab(key) {
  if (rawDirty.value && key !== 'raw') { error.value = '请先保存原始配置，或放弃草稿并读取已保存配置后再切换。'; return }
  error.value = ''; notice.value = ''
  if (key === 'raw' && activeTab.value !== 'raw') {
    busy.value = true
    try { setRaw(await builtinFrpsApi.preview(payload())) } catch (e) { error.value = e.message; return } finally { busy.value = false }
  }
  activeTab.value = key
}
async function readRaw() {
  busy.value = true; error.value = ''
  try { setRaw(await builtinFrpsApi.raw()); notice.value = '已读取保存的原始配置。' } catch (e) { error.value = e.message } finally { busy.value = false }
}
async function validateRaw() {
  busy.value = true; error.value = ''; notice.value = ''
  try { await builtinFrpsApi.validateRaw(rawPayload()); notice.value = '原始配置校验通过，尚未应用。' } catch (e) { error.value = e.message } finally { busy.value = false }
}
function addPlugin() { form.http_plugins.push({ name: `plugin-${form.http_plugins.length + 1}`, addr: '', path: '/handler', ops: ['Login', 'NewProxy'], tls_verify: true }) }
async function load(reset = false) {
  const id = ++requestId
  try {
    const data = await builtinFrpsApi.get()
    if (id !== requestId || disposed) return
    status.value = data
    if (reset) {
      updateForm(data)
      if (activeTab.value === 'raw') await readRaw()
      error.value = ''
    }
  } catch (e) { if (id === requestId && !disposed) error.value = e.message }
}
async function apply(action) {
  busy.value = true; error.value = ''; notice.value = ''; ++requestId
  try {
    status.value = await action()
    updateForm(status.value)
    if (activeTab.value === 'raw') { rawBaseline.value = rawContent.value; previewDirty.value = false; setRaw(await builtinFrpsApi.raw()) }
    notice.value = status.value.running ? '内置 FRP 已启动，已加入服务器列表。' : '配置已保存，内置 FRP 已关闭。'
    emit('changed')
  } catch (e) { error.value = e.message } finally { busy.value = false }
}
const save = () => apply(() => activeTab.value === 'raw' ? builtinFrpsApi.saveRaw(rawPayload()) : builtinFrpsApi.save(payload()))
const restart = () => apply(builtinFrpsApi.restart)
async function showToken() {
  if (token.value) { token.value = ''; return }
  try { token.value = (await builtinFrpsApi.token()).auth_token } catch (e) { error.value = e.message }
}
async function copyToken(event) {
  if (!await copyWithTooltip(token.value, event.currentTarget)) error.value = '复制失败，请手动复制 Token'
}
onMounted(async () => {
  try {
    isAdmin.value = (await settingsApi.getUserSettings()).role === 'admin'
    if (isAdmin.value && !disposed) {
      await load(true)
      if (!disposed) timer = setInterval(() => { if (!busy.value) load() }, 5000)
    }
  } catch (e) { error.value = e.message }
})
onUnmounted(() => { disposed = true; ++requestId; clearInterval(timer); token.value = '' })
</script>
