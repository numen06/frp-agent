<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed inset-0 z-50 flex items-end justify-center p-2 sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      @click.self="close"
    >
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="close" />
      <div
        class="relative z-10 flex h-[calc(100dvh-1rem)] max-h-[calc(100dvh-1rem)] w-full max-w-4xl flex-col overflow-hidden rounded-t-xl border border-gray-200 bg-white shadow-xl sm:h-auto sm:max-h-[min(92vh,800px)] sm:rounded-xl"
        @click.stop
      >
        <div class="sticky top-0 z-10 flex shrink-0 items-center justify-between gap-3 border-b border-gray-200 bg-white px-4 py-3.5 sm:px-5">
          <h2 class="min-w-0 truncate text-lg font-semibold text-gray-900">分组客户端升级 — {{ groupName }}</h2>
          <button
            type="button"
            class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800"
            aria-label="关闭"
            @click="close"
          >
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4 text-sm sm:px-5">
          <SshCredentialForm v-model="credentialId" />

          <div class="mt-3">
            <label class="mb-1 block text-xs font-medium text-gray-600">frpc 安装路径</label>
            <input v-model="installPath" type="text" class="w-full rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm sm:max-w-md" />
          </div>

          <div class="mt-3 space-y-2">
            <label class="block text-xs font-medium text-gray-600">验证模式</label>
            <select v-model="verifyMode" class="w-full rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm sm:max-w-md">
              <option value="agent_callback">回调验证（推荐）</option>
              <option value="skip">跳过远程验证</option>
            </select>
            <p v-if="verifyMode === 'skip'" class="text-xs text-amber-600">
              跳过远程验证将无法确认 frps 端连接状态，可能导致无法自动回滚
            </p>
          </div>

          <div v-if="jobSummary" class="mt-3 rounded-lg bg-blue-50 p-3 text-blue-900">
            {{ jobSummary }}
          </div>

          <div v-if="results.length" class="mt-4 overflow-x-auto">
            <table class="w-full border-collapse text-left text-xs">
              <thead>
                <tr class="border-b border-gray-200 bg-gray-50">
                  <th class="px-2 py-2">
                    <input
                      type="checkbox"
                      :checked="allUpgradeableSelected"
                      @change="toggleSelectAllUpgradeable"
                    />
                  </th>
                  <th class="px-2 py-2">代理</th>
                  <th class="px-2 py-2">SSH 端点</th>
                  <th class="px-2 py-2">当前版本</th>
                  <th class="px-2 py-2">目标版本</th>
                  <th class="px-2 py-2">配置</th>
                  <th class="px-2 py-2">状态</th>
                  <th class="px-2 py-2">回滚</th>
                  <th class="px-2 py-2">说明</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in results" :key="row.proxy_id" class="border-b border-gray-100">
                  <td class="px-2 py-2">
                    <input
                      v-if="row.upgradeable && row.rollback_capable"
                      type="checkbox"
                      :checked="selectedIds.includes(row.proxy_id)"
                      @change="toggleSelect(row.proxy_id)"
                    />
                  </td>
                  <td class="px-2 py-2">{{ row.proxy_name || row.proxy_id }}</td>
                  <td class="break-all px-2 py-2 font-mono">{{ row.ssh_target || '-' }}</td>
                  <td class="px-2 py-2">{{ row.current_version || '-' }}</td>
                  <td class="px-2 py-2">{{ row.target_version || '-' }}</td>
                  <td class="px-2 py-2">
                    <span v-if="row.config_path" class="font-mono">{{ row.config_format }}</span>
                    <span v-else>-</span>
                    <span v-if="row.has_ini" class="ml-1 text-purple-600">ini</span>
                    <span v-if="row.has_toml" class="ml-1 text-blue-600">toml</span>
                  </td>
                  <td class="px-2 py-2">
                    <span :class="statusClass(row.status)">{{ statusLabel(row.status) }}</span>
                  </td>
                  <td class="px-2 py-2">
                    <span v-if="row.rollback_capable" class="text-green-600">支持</span>
                    <span v-else-if="row.rollback_capable === false" class="text-amber-600">不支持</span>
                    <span v-else>-</span>
                  </td>
                  <td class="px-2 py-2 text-gray-500">{{ row.message || '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else-if="!scanning" class="mt-4 text-gray-500">扫描后将显示分组内 SSH 候选代理及结果。</p>
        </div>
        <div class="sticky bottom-0 z-10 flex shrink-0 flex-col gap-2 border-t border-gray-200 bg-gray-50 px-4 py-3.5 sm:flex-row sm:flex-wrap sm:items-center sm:justify-end sm:gap-2 sm:px-5">
          <button
            type="button"
            class="btn btn-md btn-primary w-full disabled:opacity-50 sm:w-auto"
            :disabled="!credentialId || !frpsServerId || scanning"
            @click="runGroupScan"
          >
            {{ scanning ? '扫描中...' : '扫描分组' }}
          </button>
          <button
            type="button"
            class="btn btn-md btn-success w-full disabled:opacity-50 sm:w-auto"
            aria-label="升级所选客户端"
            :disabled="!credentialId || !frpsServerId || selectedIds.length === 0 || upgrading"
            @click="runGroupUpgrade"
          >
            {{ upgrading ? '升级中...' : `升级所选 (${selectedIds.length})` }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import SshCredentialForm from '@/components/SshCredentialForm.vue'
import { clientUpgradeApi } from '@/api/clientUpgrade'

const props = defineProps({
  modelValue: Boolean,
  groupName: { type: String, default: '' },
  frpsServerId: { type: Number, default: null }
})

const emit = defineEmits(['update:modelValue', 'upgraded'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})

const credentialId = ref(0)
const installPath = ref('/opt/frp')
const verifyMode = ref('agent_callback')
const scanning = ref(false)
const upgrading = ref(false)
const results = ref([])
const selectedIds = ref([])
const jobSummary = ref('')
let pollTimer = null

const STATUS_LABELS = {
  upgradeable: '可升级',
  latest: '已最新',
  unreachable: '不可达',
  auth_failed: '认证失败',
  permission_denied: '权限不足',
  not_ssh: '非 SSH',
  unsupported_platform: '不支持的平台',
  no_package: '无安装包',
  upgraded: '已升级',
  rolled_back: '已回滚',
  upgrade_failed: '升级失败'
}

function statusLabel(s) {
  return STATUS_LABELS[s] || s || '-'
}

function statusClass(s) {
  if (s === 'upgradeable') return 'text-green-700'
  if (s === 'latest' || s === 'upgraded') return 'text-blue-700'
  if (s === 'rolled_back') return 'text-amber-700'
  return 'text-amber-700'
}

const upgradeableIds = computed(() =>
  results.value.filter((r) => r.upgradeable && r.rollback_capable).map((r) => r.proxy_id)
)

const allUpgradeableSelected = computed(
  () =>
    upgradeableIds.value.length > 0 &&
    upgradeableIds.value.every((id) => selectedIds.value.includes(id))
)

watch(visible, (v) => {
  if (!v) {
    stopPoll()
    results.value = []
    selectedIds.value = []
    jobSummary.value = ''
  }
})

function close() {
  visible.value = false
}

function toggleSelect(id) {
  const idx = selectedIds.value.indexOf(id)
  if (idx >= 0) selectedIds.value = selectedIds.value.filter((x) => x !== id)
  else selectedIds.value = [...selectedIds.value, id]
}

function toggleSelectAllUpgradeable() {
  if (allUpgradeableSelected.value) {
    selectedIds.value = []
  } else {
    selectedIds.value = [...upgradeableIds.value]
  }
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function pollJob(jobId) {
  stopPoll()
  return new Promise((resolve) => {
    const tick = async () => {
      try {
        const data = await clientUpgradeApi.getJobResults(jobId)
        const job = data.job
        if (job.status !== 'running' && job.status !== 'queued') {
          stopPoll()
          results.value = data.results || []
          jobSummary.value = job.summary || ''
          selectedIds.value = results.value.filter((r) => r.upgradeable && r.rollback_capable).map((r) => r.proxy_id)
          resolve(data)
          return
        }
        jobSummary.value = job.summary || '任务执行中...'
      } catch (e) {
        console.error(e)
      }
    }
    tick()
    pollTimer = setInterval(tick, 1500)
  })
}

async function runGroupScan() {
  if (!props.groupName || !props.frpsServerId || !credentialId.value) return
  scanning.value = true
  jobSummary.value = ''
  results.value = []
  try {
    const job = await clientUpgradeApi.scanGroup(props.groupName, props.frpsServerId, {
      credential_id: credentialId.value,
      install_path: installPath.value
    })
    await pollJob(job.id)
  } catch (e) {
    alert(e.message || '扫描失败')
  } finally {
    scanning.value = false
  }
}

async function runGroupUpgrade() {
  if (!selectedIds.value.length) return
  const warnMsg = `将备份选中的 ${selectedIds.value.length} 个客户端的 frpc 二进制和现有配置文件。若升级后代理无法重新上线，目标主机上的升级脚本会自动回退。\n\n确认升级？`
  if (!confirm(warnMsg)) return
  upgrading.value = true
  try {
    const job = await clientUpgradeApi.upgradeGroup(props.groupName, props.frpsServerId, {
      credential_id: credentialId.value,
      install_path: installPath.value,
      proxy_ids: selectedIds.value,
      verify_mode: verifyMode.value,
      skip_remote_verify: verifyMode.value === 'skip'
    })
    await pollJob(job.id)
    emit('upgraded')
  } catch (e) {
    alert(e.message || '升级失败')
  } finally {
    upgrading.value = false
  }
}
</script>
