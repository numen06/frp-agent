<template>
  <section class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
    <div class="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 p-4">
      <div><h2 class="font-semibold">凭证管理</h2><p class="mt-1 text-xs text-gray-500">密码、私钥和 API Key 加密保存，仅显示设置状态。共享凭证的修改会影响使用它的主机。</p></div>
      <button type="button" class="btn btn-md btn-primary" @click="openEditor()">新增凭证</button>
    </div>
    <div class="flex flex-wrap gap-2 px-4 pt-4" role="group" aria-label="凭证类型">
      <button v-for="option in kinds" :key="option.key" type="button" class="btn btn-md" :class="kind === option.key ? 'btn-primary' : 'btn-outline'" :aria-pressed="kind === option.key" @click="kind = option.key">{{ option.label }}</button>
    </div>
    <form class="flex gap-2 p-4" @submit.prevent="list.load(1)"><input v-model="list.search.value" aria-label="搜索凭证" placeholder="搜索凭证名称或用户名" class="min-w-0 flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"><button class="btn btn-md btn-outline">搜索</button></form>
    <p v-if="list.error.value || error" role="alert" class="px-4 pb-4 text-sm text-red-600">{{ list.error.value || error }}</p>
    <p v-if="notice" role="status" class="px-4 pb-4 text-sm text-emerald-700">{{ notice }}</p>
    <p v-if="list.loading.value" role="status" class="p-6 text-center text-sm text-gray-500">正在加载凭证…</p>
    <template v-else>
      <div class="hidden overflow-x-auto md:block"><table class="w-full text-left text-sm">
        <thead class="bg-gray-50 text-xs text-gray-500"><tr><th class="px-4 py-3">名称</th><th class="px-4 py-3">用户名</th><th class="px-4 py-3">认证方式</th><th class="px-4 py-3">已设置内容</th><th class="px-4 py-3">操作</th></tr></thead>
        <tbody><tr v-for="row in list.items.value" :key="row.id" class="border-t border-gray-100"><td class="break-all px-4 py-3 font-medium">{{ row.name }}</td><td class="break-all px-4 py-3">{{ row.username || '—' }}</td><td class="px-4 py-3">{{ authLabel(row.auth_type) }}</td><td class="px-4 py-3 text-xs text-gray-500">{{ savedFields(row) }}</td><td class="px-4 py-3"><div class="flex gap-2"><button type="button" class="btn btn-sm btn-outline" @click="openEditor(row)">编辑</button><button type="button" class="btn btn-sm btn-outline text-red-600" @click="deleting = row">删除</button></div></td></tr></tbody>
      </table></div>
      <div class="divide-y divide-gray-100 md:hidden"><article v-for="row in list.items.value" :key="row.id" class="space-y-3 p-4">
        <h3 class="break-all font-medium">{{ row.name }}</h3><p class="break-all text-sm text-gray-600">{{ row.username || '无用户名' }} · {{ authLabel(row.auth_type) }}</p><p class="text-xs text-gray-500">已设置：{{ savedFields(row) }}</p>
        <div class="flex gap-2"><button type="button" class="btn btn-md btn-outline flex-1" @click="openEditor(row)">编辑</button><button type="button" class="btn btn-md btn-outline flex-1 text-red-600" @click="deleting = row">删除</button></div>
      </article></div>
      <p v-if="!list.items.value.length" class="p-8 text-center text-sm text-gray-500">暂无凭证</p>
    </template>
    <div class="border-t border-gray-200 p-4"><TablePagination :total="list.pagination.total" :page="list.pagination.page" :page-size="list.pagination.page_size" @page-change="list.load" @page-size-change="list.resize" /></div>
  </section>
  <AppDialog v-model="editorOpen" :title="editing ? '编辑凭证' : '新增凭证'" :busy="saving" panel-class="max-w-2xl">
    <form id="host-credential-form" class="space-y-4" @submit.prevent="save">
      <p class="rounded-lg bg-blue-50 p-3 text-sm text-blue-800">{{ kind === 'ssh' ? 'SSH 与 RDP 共用此凭证库；RDP 仅支持密码认证。' : '用于连接 Portainer，不是平台 API Key。' }}{{ editing ? ' 敏感内容不会回显，留空保留原值。' : '' }}</p>
      <label class="block text-sm">凭证名称<input v-model.trim="form.name" required maxlength="100" class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" autocomplete="off"></label>
      <label class="block text-sm">认证方式<select v-model="form.auth_type" class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2"><option value="password">用户名 / 密码</option><option v-if="kind === 'ssh'" value="private_key">SSH 私钥</option><option v-else value="api_key">Portainer API Key</option></select></label>
      <label v-if="kind === 'ssh' || form.auth_type === 'password'" class="block text-sm">登录用户名<input v-model.trim="form.username" required maxlength="100" class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" autocomplete="off"></label>
      <div v-for="field in secretFields" :key="field.key" class="space-y-2">
        <label class="block text-sm">{{ field.label }}<span v-if="editing" class="ml-2 text-xs text-gray-500">{{ editing[`has_${field.key}`] ? '已设置；留空保留' : '未设置' }}</span>
          <textarea v-if="field.rows" v-model="form[field.key]" :rows="field.rows" :aria-label="field.label" :disabled="form.clear[field.key]" class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-xs" autocomplete="off" spellcheck="false" />
          <input v-else v-model="form[field.key]" type="password" :aria-label="field.label" :disabled="form.clear[field.key]" class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" autocomplete="new-password">
        </label>
        <label v-if="field.key === 'private_key'" class="btn btn-sm btn-outline cursor-pointer">上传私钥<input type="file" class="sr-only" aria-label="上传 SSH 私钥" @change="readPrivateKey"></label>
        <label v-if="field.optional && editing?.[`has_${field.key}`]" class="flex items-center gap-2 text-sm text-gray-600"><input v-model="form.clear[field.key]" type="checkbox">清除已保存的{{ field.label }}</label>
      </div>
      <p v-if="editorError" role="alert" class="text-sm text-red-600">{{ editorError }}</p>
    </form>
    <template #footer><button type="button" class="btn btn-md btn-outline" :disabled="saving" @click="editorOpen = false">取消</button><button type="submit" form="host-credential-form" class="btn btn-md btn-primary" :disabled="saving">{{ saving ? '保存中…' : '保存凭证' }}</button></template>
  </AppDialog>
  <AppDialog :model-value="!!deleting" title="删除凭证" :busy="saving" panel-class="max-w-xl" @update:model-value="value => { if (!value) deleting = null }">
    <p class="break-all text-sm">确定删除凭证“{{ deleting?.name }}”？删除后不可恢复。</p><p class="mt-3 text-sm text-gray-500">正在被主机或代理客户端使用的凭证不能删除，请先更换凭证；运行中的扫描 / 升级任务结束后才能删除。</p><p v-if="deleteError" role="alert" class="mt-3 text-sm text-red-600">{{ deleteError }}</p>
    <template #footer><button type="button" class="btn btn-md btn-outline" :disabled="saving" @click="deleting = null">取消</button><button type="button" class="btn btn-md btn-danger" :disabled="saving" @click="remove">{{ saving ? '删除中…' : '确认删除' }}</button></template>
  </AppDialog>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import AppDialog from './AppDialog.vue'
import TablePagination from './TablePagination.vue'
import { usePagedList } from '@/composables/usePagedList'
import { sshCredentialsApi } from '@/api/sshCredentials'
import { dockerCredentialsApi } from '@/api/managedHosts'

const emit = defineEmits(['changed'])
const kinds = [{ key: 'ssh', label: 'SSH / RDP' }, { key: 'docker', label: 'Docker / Portainer' }]
const kind = ref('ssh')
const sshList = usePagedList(sshCredentialsApi.list), dockerList = usePagedList(dockerCredentialsApi.list)
const list = computed(() => kind.value === 'ssh' ? sshList : dockerList)
const api = computed(() => kind.value === 'ssh' ? sshCredentialsApi : dockerCredentialsApi)
const editorOpen = ref(false), editing = ref(null), deleting = ref(null), saving = ref(false)
const error = ref(''), editorError = ref(''), deleteError = ref(''), notice = ref('')
let editorRequest = 0
const form = reactive({ name: '', username: '', auth_type: '', password: '', private_key: '', passphrase: '', sudo_password: '', api_key: '', ca_cert: '', clear: {} })
const labels = { password: '密码', private_key: '私钥', passphrase: '私钥口令', sudo_password: 'sudo 密码', api_key: 'API Key', ca_cert: 'CA 证书' }
const secretFields = computed(() => {
  const keys = [form.auth_type === 'password' ? 'password' : kind.value === 'ssh' ? 'private_key' : 'api_key']
  if (kind.value === 'ssh') { if (form.auth_type === 'private_key') keys.push('passphrase'); keys.push('sudo_password') }
  else keys.push('ca_cert')
  return keys.map(key => ({ key, label: labels[key], rows: ['private_key', 'ca_cert'].includes(key) ? 5 : 0, optional: ['passphrase', 'sudo_password', 'ca_cert'].includes(key) }))
})
const authLabel = type => ({ password: '用户名 / 密码', private_key: 'SSH 私钥', api_key: 'Portainer API Key' }[type] || type)
const savedFields = row => Object.entries(labels).filter(([key]) => row[`has_${key}`]).map(([, label]) => label).join('、') || '未设置'
function openEditor(row = null) {
  editorRequest++
  editing.value = row; editorError.value = ''; notice.value = ''
  Object.assign(form, { name: row?.name || '', username: row?.username || (kind.value === 'ssh' ? 'root' : ''), auth_type: row?.auth_type || (kind.value === 'ssh' ? 'password' : 'api_key'), password: '', private_key: '', passphrase: '', sudo_password: '', api_key: '', ca_cert: '', clear: {} })
  editorOpen.value = true
}
async function save() {
  if (saving.value) return
  editorError.value = ''
  const primary = form.auth_type === 'password' ? 'password' : kind.value === 'ssh' ? 'private_key' : 'api_key'
  if (!form[primary] && !editing.value?.[`has_${primary}`]) { editorError.value = `请填写${labels[primary]}`; return }
  const payload = { name: form.name, auth_type: form.auth_type }
  if (kind.value === 'ssh' || form.auth_type === 'password') payload.username = form.username
  for (const field of secretFields.value) {
    if (field.optional && form.clear[field.key]) payload[field.key] = ''
    else if (form[field.key]) payload[field.key] = form[field.key]
  }
  saving.value = true
  try {
    if (editing.value) await api.value.update(editing.value.id, payload)
    else await api.value.create(payload)
    editorOpen.value = false; notice.value = '凭证已保存'; await list.value.load(); emit('changed')
  } catch (e) { editorError.value = e.message } finally { saving.value = false }
}
async function remove() {
  if (!deleting.value || saving.value) return
  saving.value = true; deleteError.value = ''
  try { await api.value.remove(deleting.value.id); deleting.value = null; notice.value = '凭证已删除'; await list.value.load(); emit('changed') } catch (e) { deleteError.value = e.message } finally { saving.value = false }
}
async function readPrivateKey(event) {
  const request = editorRequest
  const file = event.target.files?.[0]; event.target.value = ''; if (!file) return
  if (file.size > 1024 * 1024) { editorError.value = '私钥文件不能超过 1MB'; return }
  try {
    const content = await file.text()
    if (!/-----BEGIN (?:OPENSSH |RSA |EC |ENCRYPTED )?PRIVATE KEY-----/.test(content)) throw new Error('请选择 SSH 私钥文件，不是公钥文件')
    if (editorOpen.value && request === editorRequest) form.private_key = `${content.trim()}\n`
  } catch (e) { editorError.value = e.message }
}
watch(editorOpen, visible => { if (!visible) for (const key of Object.keys(labels)) form[key] = '' })
watch(deleting, () => { deleteError.value = '' })
watch(kind, () => { error.value = ''; notice.value = ''; list.value.load() })
onMounted(() => list.value.load(1))
</script>
