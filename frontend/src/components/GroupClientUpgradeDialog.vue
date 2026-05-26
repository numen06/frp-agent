<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      @click.self="close"
    >
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="close" />
      <div
        class="relative z-10 flex max-h-[min(92vh,800px)] w-full max-w-3xl flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-xl"
        @click.stop
      >
        <div class="flex shrink-0 items-center justify-between border-b border-gray-200 px-5 py-3.5">
          <h2 class="text-lg font-semibold text-gray-900">分组客户端升级 — {{ groupName }}</h2>
          <button type="button" class="rounded-lg p-2 text-gray-500 hover:bg-gray-100" aria-label="关闭" @click="close">×</button>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto px-5 py-4 text-sm">
          <SshCredentialForm v-model="credentialId" />

          <div class="mt-3">
            <label class="mb-1 block text-xs font-medium text-gray-600">frpc 安装路径</label>
            <input v-model="installPath" type="text" class="w-full max-w-md rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm" />
          </div>

          <div class="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              class="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              :disabled="!credentialId || !frpsServerId || scanning"
              @click="runGroupScan"
            >
              {{ scanning ? '扫描中...' : '扫描分组' }}
            </button>
            <button
              type="button"
              class="rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50"
              :disabled="!credentialId || !frpsServerId || selectedIds.length === 0 || upgrading"
              @click="runGroupUpgrade"
            >
              {{ upgrading ? '升级中...' : `升级所选 (${selectedIds.length})` }}
            </button>
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
                  <th class="px-2 py-2">状态</th>
                  <th class="px-2 py-2">当前版本</th>
                  <th class="px-2 py-2">目标版本</th>
                  <th class="px-2 py-2">说明</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in results" :key="row.proxy_id" class="border-b border-gray-100">
                  <td class="px-2 py-2">
                    <input
                      v-if="row.upgradeable"
                      type="checkbox"
                      :checked="selectedIds.includes(row.proxy_id)"
                      @change="toggleSelect(row.proxy_id)"
                    />
                  </td>
                  <td class="px-2 py-2">{{ row.proxy_name || row.proxy_id }}</td>
                  <td class="px-2 py-2">{{ statusLabel(row.status) }}</td>
                  <td class="px-2 py-2">{{ row.current_version || '-' }}</td>
                  <td class="px-2 py-2">{{ row.target_version || '-' }}</td>
                  <td class="px-2 py-2 text-gray-500">{{ row.message || '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else-if="!scanning" class="mt-4 text-gray-500">扫描后将显示分组内 SSH 候选代理及结果。</p>
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
  upgrade_failed: '升级失败'
}

function statusLabel(s) {
  return STATUS_LABELS[s] || s || '-'
}

const upgradeableIds = computed(() =>
  results.value.filter((r) => r.upgradeable).map((r) => r.proxy_id)
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
          selectedIds.value = results.value.filter((r) => r.upgradeable).map((r) => r.proxy_id)
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
  if (!confirm(`确认升级选中的 ${selectedIds.value.length} 个客户端？`)) return
  upgrading.value = true
  try {
    const job = await clientUpgradeApi.upgradeGroup(props.groupName, props.frpsServerId, {
      credential_id: credentialId.value,
      install_path: installPath.value,
      proxy_ids: selectedIds.value
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
