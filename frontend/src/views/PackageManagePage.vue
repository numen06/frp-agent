<template>
  <div>
    <div class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <div class="flex flex-col gap-3 border-b border-gray-200 px-3 py-3 sm:px-5 sm:py-3.5 md:flex-row md:items-center md:justify-between md:gap-2">
        <h3 class="text-base font-semibold text-gray-900">FRP 安装包管理</h3>
        <div class="flex w-full flex-wrap gap-2 md:w-auto md:justify-end">
          <button
            class="btn btn-sm btn-secondary min-h-10 flex-1 sm:min-h-8 sm:flex-none"
            type="button"
            :disabled="refreshLoading"
            @click="handleRefresh"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4"/><path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4"/>
            </svg>
            {{ refreshLoading ? '刷新中...' : '刷新' }}
          </button>
          <button class="btn btn-sm btn-primary min-h-10 flex-1 sm:min-h-8 sm:flex-none" type="button" @click="showSyncDialog = true">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M3 14v4a1 1 0 0 0 1 1h4"/><path d="M17 3h4a1 1 0 0 1 1 1v4"/><path d="M16 8l-8 8"/>
            </svg>
            GitHub 同步
          </button>
          <button class="btn btn-sm btn-primary min-h-10 flex-1 sm:min-h-8 sm:flex-none" type="button" @click="showUploadDialog = true">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M12 5l0 14"/><path d="M5 12l14 0"/>
            </svg>
            手动上传
          </button>
          <button class="btn btn-sm btn-primary min-h-10 flex-1 sm:min-h-8 sm:flex-none" type="button" @click="showInstallDialog = true">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M7 8l-4 4l4 4"/><path d="M17 8l4 4l-4 4"/><path d="M14 4l-4 16"/>
            </svg>
            脚本生成
          </button>
          <div class="relative w-full sm:w-auto">
            <button
              ref="moreActionsDropdown.triggerRef"
              type="button"
              class="btn btn-sm btn-outline min-h-10 w-full gap-1 sm:min-h-8 sm:w-auto"
              @click.prevent="toggleMoreActionsMenu"
              :aria-expanded="moreActionsDropdown.isOpen.value"
            >
              更多
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M6 9l6 6l6 -6"/>
              </svg>
            </button>
            <Teleport to="body">
            <div
              v-if="moreActionsDropdown.isOpen.value"
              ref="moreActionsDropdown.dropdownRef"
              class="fixed z-50 min-w-[11rem] max-w-[calc(100vw-1rem)] rounded-lg border border-gray-200 bg-white py-1 shadow-lg"
              :style="moreActionsMenuStyle"
              @click.stop
            >
              <a
                class="flex cursor-pointer items-center px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
                href="#"
                :class="{ 'pointer-events-none opacity-50': checkUpdateLoading }"
                @click.prevent="handleMoreCheckUpdate"
              >
                {{ checkUpdateLoading ? '检查中...' : '检查更新' }}
              </a>
              <a
                class="flex cursor-pointer items-center px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
                href="#"
                :class="{ 'pointer-events-none opacity-50': syncPlatformsLoading }"
                @click.prevent="handleMoreSyncPlatforms"
              >
                {{ syncPlatformsLoading ? '同步中...' : '同步平台类型' }}
              </a>
              <div class="my-1 border-t border-gray-100"></div>
              <a
                class="flex cursor-pointer items-center px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
                href="#"
                @click.prevent="showTemplateDialog = true; moreActionsDropdown.close()"
              >
                脚本模板编辑
              </a>
            </div>
            </Teleport>
          </div>
        </div>
      </div>
      <div class="p-3 sm:p-5">
        <div class="mb-4 flex flex-col gap-3 md:grid md:grid-cols-3">
          <select v-model="filters.version" class="block min-h-10 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200">
            <option value="">全部版本</option>
            <option v-if="versionsMeta.latest_version" value="__latest__">
              最新（{{ versionsMeta.latest_version }}）
            </option>
            <optgroup v-if="recentVersionsForUi.length" label="最近">
              <option v-for="v in recentVersionsForUi" :key="'rv-' + v" :value="v">{{ v }}</option>
            </optgroup>
            <optgroup v-if="otherVersionsForUi.length" label="其他版本">
              <option v-for="v in otherVersionsForUi" :key="'ov-' + v" :value="v">{{ v }}</option>
            </optgroup>
          </select>
          <select v-model="filters.platform" class="block min-h-10 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200">
            <option value="">全部平台</option>
            <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
          </select>
          <select v-model="filters.source" class="block min-h-10 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200">
            <option value="">全部来源</option>
            <option value="github">github</option>
            <option value="upload">upload</option>
          </select>
        </div>
        <div v-if="loading" class="py-8 text-center">
          <span class="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600 align-middle" role="status" aria-label="加载中"></span>
          <span class="ml-2 align-middle text-sm text-gray-500">加载中...</span>
        </div>
        <div v-else>
          <div class="hidden overflow-x-auto md:block">
            <table class="w-full border-collapse text-left text-sm text-gray-700">
            <thead>
              <tr>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">ID</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">版本</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">平台</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">文件名</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">大小</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">来源</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">下载时间</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">SHA256</th>
                <th class="px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200 whitespace-nowrap" style="min-width:96px">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="packages.length === 0">
                <td colspan="9" class="py-8 text-center text-gray-500">暂无安装包</td>
              </tr>
              <tr v-for="item in packages" :key="item.id">
                <td class="px-4 py-3 border-b border-gray-100 align-middle">{{ item.id }}</td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle">
                  <span
                    class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium"
                    :class="item.source === 'github' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-700'"
                  >{{ item.version }}</span>
                </td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle whitespace-nowrap">{{ item.platform }}</td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle">
                  <span class="truncate" :title="item.filename">{{ item.filename }}</span>
                </td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle whitespace-nowrap">{{ formatSize(item.file_size) }}</td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle">
                  <span
                    class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium"
                    :class="item.source === 'github' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-700'"
                  >{{ item.source }}</span>
                </td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle whitespace-nowrap">{{ formatDate(item.downloaded_at) }}</td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle"><code class="text-xs text-gray-500">{{ item.sha256_checksum?.slice(0, 12) }}...</code></td>
                <td class="px-4 py-3 border-b border-gray-100 align-middle">
                  <div class="flex flex-wrap items-center gap-1.5">
                    <button class="btn btn-icon-sm btn-icon-accent" title="下载安装包" type="button" @click="downloadPackageFile(item)">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                        <path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-2"/><polyline points="7 11 12 16 17 11"/><line x1="12" y1="4" x2="12" y2="16"/>
                      </svg>
                    </button>
                    <button
                      class="btn btn-icon-sm btn-icon-muted"
                      title="更多"
                      aria-label="更多操作"
                      type="button"
                      @click.stop="togglePackageMore(item.id, $event)"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                        <circle cx="5" cy="12" r="1" fill="currentColor"/>
                        <circle cx="12" cy="12" r="1" fill="currentColor"/>
                        <circle cx="19" cy="12" r="1" fill="currentColor"/>
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          </div>
          <div class="md:hidden">
            <p v-if="packages.length === 0" class="py-8 text-center text-gray-500">暂无安装包</p>
            <ul v-else class="divide-y divide-gray-100">
              <li v-for="item in packages" :key="item.id" class="p-4">
                <div class="flex flex-wrap items-center gap-2">
                  <span
                    class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium"
                    :class="item.source === 'github' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-700'"
                  >{{ item.version }}</span>
                  <span class="text-sm font-medium text-gray-900">{{ item.platform }}</span>
                  <span
                    class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium"
                    :class="item.source === 'github' ? 'bg-blue-50 text-blue-700' : 'bg-gray-50 text-gray-600'"
                  >{{ item.source }}</span>
                </div>
                <p class="mt-1 break-all text-sm text-gray-700" :title="item.filename">{{ item.filename }}</p>
                <dl class="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-gray-500">
                  <div><dt class="inline">大小 </dt><dd class="inline text-gray-700">{{ formatSize(item.file_size) }}</dd></div>
                  <div class="col-span-2"><dt class="inline">下载 </dt><dd class="inline text-gray-700">{{ formatDate(item.downloaded_at) }}</dd></div>
                  <div class="col-span-2 break-all"><dt class="inline">SHA256 </dt><dd class="inline font-mono text-gray-600">{{ item.sha256_checksum?.slice(0, 16) }}…</dd></div>
                </dl>
                <div class="mt-3 flex flex-wrap gap-2">
                  <button class="btn btn-icon-md btn-icon-accent" title="下载安装包" aria-label="下载安装包" type="button" @click="downloadPackageFile(item)">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-2"/><polyline points="7 11 12 16 17 11"/><line x1="12" y1="4" x2="12" y2="16"/>
                    </svg>
                  </button>
                  <button
                    class="btn btn-icon-md btn-icon-muted"
                    title="更多"
                    aria-label="更多操作"
                    type="button"
                    @click.stop="togglePackageMore(item.id, $event)"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                      <circle cx="5" cy="12" r="1" fill="currentColor"/>
                      <circle cx="12" cy="12" r="1" fill="currentColor"/>
                      <circle cx="19" cy="12" r="1" fill="currentColor"/>
                    </svg>
                  </button>
                </div>
              </li>
            </ul>
          </div>
          <div class="mt-4 border-t border-gray-100 pt-4">
            <TablePagination
              :total="pagination.total"
              :page="pagination.page"
              :page-size="pagination.page_size"
              @page-change="onPackagePageChange"
              @page-size-change="onPackagePageSizeChange"
            />
          </div>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="openMorePackageId"
        class="fixed z-50 min-w-[168px] max-w-[calc(100vw-1rem)] rounded-lg border border-gray-200 bg-white py-1 shadow-lg"
        :style="packageMoreMenuStyle"
        @click.stop
      >
        <a
          class="flex cursor-pointer items-center px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-100"
          href="#"
          @click.prevent="handleMoreCopyDownload($event)"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="mr-1.5 h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
            <path d="M4 4v5h.582m15.356 2a8.001 8.001 0 0 0 -15.356 -2m15.356 2a15 15 0 0 1 2 0m-17 0a15 15 0 0 1 2 0"/>
            <path d="M4 13a8.001 8.001 0 0 0 4 0"/>
          </svg>
          复制下载命令
        </a>
        <a
          class="flex cursor-pointer items-center px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-100"
          href="#"
          @click.prevent="handleMoreCopyInstall($event)"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="mr-1.5 h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
            <path d="M12 3l0 18"/>
            <path d="M8 7l4 -4l4 4"/>
            <path d="M8 17l4 4l4 -4"/>
          </svg>
          复制安装命令
        </a>
        <a
          class="flex cursor-pointer items-center px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-100"
          href="#"
          @click.prevent="handleMoreCopyUpgrade($event)"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="mr-1.5 h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
            <path d="M12 6l0 12"/>
            <path d="M16 10l-4 -4l-4 4"/>
            <path d="M16 14l-4 4l-4 -4"/>
          </svg>
          复制升级命令
        </a>
        <div class="my-1 border-t border-gray-100"></div>
        <a
          class="flex cursor-pointer items-center px-3 py-1.5 text-sm text-red-600 transition-colors hover:bg-red-50"
          href="#"
          @click.prevent="handleMoreRemove"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="mr-1.5 h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
            <path d="M4 7l16 0"/>
            <path d="M10 11l0 6"/>
            <path d="M14 11l0 6"/>
            <path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12"/>
            <path d="M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3"/>
          </svg>
          删除
        </a>
      </div>
    </Teleport>

    <PackageSyncDialog
      v-model="showSyncDialog"
      :releases="syncDialogReleases"
      :loading="syncLoading"
      :progress="syncProgress"
      @submit="handleSync"
    />
    <PackageUploadDialog v-model="showUploadDialog" :platforms="platforms" :loading="uploadLoading" @submit="handleUpload" @submit-batch="handleUploadBatch" />
    <PackageInstallDialog
      v-model="showInstallDialog"
      :packages="installPickerPackages"
      :latest-version="versionsMeta.latest_version"
      :loading="scriptLoading"
      :script="installScript"
      :upgrade-script="upgradeScript"
      @submit="handleGenerateScript"
      @submit-upgrade="handleGenerateUpgradeScript"
    />
    <ScriptTemplateDialog
      v-model="showTemplateDialog"
      :platforms="platforms"
      :templates="scriptTemplates"
      :saving="savingTemplate"
      @save="handleSaveTemplate"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { packagesApi } from '@/api/packages'
import { useApiKeysStore } from '@/stores/apiKeys'
import { useDropdown } from '@/composables/useDropdown'
import { copyWithTooltip } from '@/composables/useCopyTooltip'
import PackageSyncDialog from '@/components/PackageSyncDialog.vue'
import PackageUploadDialog from '@/components/PackageUploadDialog.vue'
import PackageInstallDialog from '@/components/PackageInstallDialog.vue'
import ScriptTemplateDialog from '@/components/ScriptTemplateDialog.vue'
import TablePagination from '@/components/TablePagination.vue'

const loading = ref(false)
const syncLoading = ref(false)
const syncProgress = ref({ completed: 0, total: 0, status: '' })
let syncPollTimer = null
const uploadLoading = ref(false)
const scriptLoading = ref(false)
const showSyncDialog = ref(false)
const showUploadDialog = ref(false)
const showInstallDialog = ref(false)
const showTemplateDialog = ref(false)
const checkUpdateLoading = ref(false)
const syncPlatformsLoading = ref(false)
const savingTemplate = ref(false)
const refreshLoading = ref(false)
const moreActionsDropdown = useDropdown()
const openMorePackageId = ref(null)
const packageMoreMenuPosition = ref({ top: 0, left: 0, right: 0 })
const moreActionsMenuPosition = ref({ top: 0, left: 0 })
const MENU_WIDTH = 176

const clampFloatingMenu = (rect, menuWidth = MENU_WIDTH) => {
  const margin = 8
  const vw = window.innerWidth
  let left = rect.left
  if (left + menuWidth > vw - margin) {
    left = Math.max(margin, vw - menuWidth - margin)
  }
  left = Math.max(margin, left)
  const top = Math.max(margin, rect.top)
  return { top, left }
}

const packageMoreMenuStyle = computed(() => {
  const { top, left, right } = packageMoreMenuPosition.value
  if (left > 0) {
    return {
      top: `${top}px`,
      left: `${left}px`,
      transform: 'translateY(-100%)'
    }
  }
  return {
    top: `${top}px`,
    right: `${right}px`,
    transform: 'translateY(-100%)'
  }
})

const moreActionsMenuStyle = computed(() => ({
  top: `${moreActionsMenuPosition.value.top}px`,
  left: `${moreActionsMenuPosition.value.left}px`,
  transform: 'translateY(-100%)'
}))
/** 从服务端恢复/修正筛选条件时避免 watch 重复请求 */
const filterSyncing = ref(false)

const packages = ref([])
const installPickerPackages = ref([])
const releases = ref([])
const installScript = ref('')
const upgradeScript = ref('')
const scriptTemplates = ref({})
const apiKeysStore = useApiKeysStore()

const PKG_FILTER_KEY = 'fm_package_list_filters_v1'
const PKG_PAGE_SIZE_KEY = 'fm_package_list_page_size_v1'

function readSavedPageSize() {
  try {
    const raw = localStorage.getItem(PKG_PAGE_SIZE_KEY)
    const n = raw ? parseInt(raw, 10) : 10
    if ([10, 20, 50, 100].includes(n)) return n
  } catch {
    /* ignore */
  }
  return 10
}

function readSavedFilters() {
  try {
    const raw = localStorage.getItem(PKG_FILTER_KEY)
    if (raw) {
      const o = JSON.parse(raw)
      if (o && typeof o === 'object') {
        return {
          version: typeof o.version === 'string' ? o.version : '',
          platform: typeof o.platform === 'string' ? o.platform : '',
          source: typeof o.source === 'string' ? o.source : ''
        }
      }
    }
  } catch {
    /* ignore */
  }
  return { version: '', platform: '', source: '' }
}

const platforms = ref([])
const filters = reactive(readSavedFilters())
const pagination = reactive({
  page: 1,
  page_size: readSavedPageSize(),
  total: 0
})
const versionsMeta = ref({
  versions: [],
  latest_version: '',
  recent_versions: [],
  synced_at: null
})

const recentVersionsForUi = computed(() => {
  const recent = versionsMeta.value.recent_versions || []
  const lv = versionsMeta.value.latest_version
  return recent.filter((v) => v && v !== lv)
})

const otherVersionsForUi = computed(() => {
  const merged = versionsMeta.value.versions || []
  const recent = new Set(versionsMeta.value.recent_versions || [])
  const lv = versionsMeta.value.latest_version
  return merged.filter((v) => v && !recent.has(v) && v !== lv)
})

const syncDialogReleases = computed(() => {
  const byVersion = new Map()
  for (const item of releases.value || []) {
    if (item?.version) {
      byVersion.set(item.version, {
        ...item,
        platforms: item.platforms || []
      })
    }
  }
  const localVersions = versionsMeta.value.versions || []
  const latest = versionsMeta.value.latest_version
  for (const version of localVersions) {
    if (!version || byVersion.has(version)) continue
    byVersion.set(version, {
      version,
      name: version,
      platforms: version === latest ? platforms.value : [],
      source: 'local-cache'
    })
  }
  return Array.from(byVersion.values())
})

const currentMorePackage = computed(() => {
  if (!openMorePackageId.value) return null
  return packages.value.find((item) => item.id === openMorePackageId.value) || null
})

const formatDate = (v) => (v ? new Date(v).toLocaleString('zh-CN') : '')
const formatSize = (s) => {
  if (!s) return '0 B'
  if (s < 1024) return `${s} B`
  if (s < 1024 * 1024) return `${(s / 1024).toFixed(1)} KB`
  return `${(s / 1024 / 1024).toFixed(1)} MB`
}

const resolveVersionForApi = () => {
  const v = filters.version
  if (!v) return undefined
  if (v === '__latest__') {
    const lv = versionsMeta.value.latest_version
    return lv || undefined
  }
  return v
}

const persistFilters = () => {
  try {
    localStorage.setItem(PKG_FILTER_KEY, JSON.stringify({ ...filters }))
  } catch {
    /* ignore */
  }
}

const loadVersionsMeta = async () => {
  let ranLoadPackages = false
  try {
    const data = await packagesApi.getVersions()
    versionsMeta.value = {
      versions: data.versions || [],
      latest_version: data.latest_version || '',
      recent_versions: data.recent_versions || [],
      synced_at: data.synced_at
    }
    const sel = filters.version
    const merged = versionsMeta.value.versions || []
    const latest = versionsMeta.value.latest_version
    if (sel === '__latest__' && !latest) {
      filterSyncing.value = true
      filters.version = ''
      filterSyncing.value = false
      persistFilters()
      pagination.page = 1
      await loadPackages()
      ranLoadPackages = true
    } else if (sel && sel !== '__latest__' && merged.length && !merged.includes(sel)) {
      filterSyncing.value = true
      filters.version = ''
      filterSyncing.value = false
      persistFilters()
      pagination.page = 1
      await loadPackages()
      ranLoadPackages = true
    }
  } catch (e) {
    console.warn('获取版本列表失败', e)
    versionsMeta.value = {
      versions: [],
      latest_version: '',
      recent_versions: [],
      synced_at: null
    }
  }
  return ranLoadPackages
}

const persistPageSize = () => {
  try {
    localStorage.setItem(PKG_PAGE_SIZE_KEY, String(pagination.page_size))
  } catch {
    /* ignore */
  }
}

const buildListParams = (page, pageSize) => {
  const params = {
    version: resolveVersionForApi(),
    platform: filters.platform || undefined,
    source: filters.source || undefined,
    page,
    page_size: pageSize
  }
  return Object.fromEntries(Object.entries(params).filter(([, val]) => val !== undefined && val !== ''))
}

const loadPackages = async () => {
  loading.value = true
  try {
    const clean = buildListParams(pagination.page, pagination.page_size)
    const res = await packagesApi.list(clean)
    const items = res.items || []
    const total = res.total ?? 0
    pagination.total = total
    if (items.length === 0 && total > 0 && pagination.page > 1) {
      pagination.page = Math.max(1, Math.ceil(total / pagination.page_size) || 1)
      const clean2 = buildListParams(pagination.page, pagination.page_size)
      const res2 = await packagesApi.list(clean2)
      packages.value = res2.items || []
      pagination.total = res2.total ?? total
      return
    }
    packages.value = items
  } catch (e) {
    alert(`加载失败: ${e.message}`)
  } finally {
    loading.value = false
  }
}

const onPackagePageChange = (p) => {
  pagination.page = p
  loadPackages()
}

const onPackagePageSizeChange = (ps) => {
  pagination.page_size = ps
  pagination.page = 1
  persistPageSize()
  loadPackages()
}

/** 弹窗打开时加载完整候选列表（多页合并） */
const loadInstallDialogPackages = async () => {
  try {
    const base = {
      version: resolveVersionForApi(),
      platform: filters.platform || undefined,
      source: filters.source || undefined
    }
    const cleanBase = Object.fromEntries(Object.entries(base).filter(([, val]) => val !== undefined && val !== ''))
    const merged = []
    let page = 1
    const page_size = 200
    let total = 0
    for (let guard = 0; guard < 50; guard += 1) {
      const res = await packagesApi.list({ ...cleanBase, page, page_size })
      total = res.total ?? 0
      const chunk = res.items || []
      merged.push(...chunk)
      if (merged.length >= total || chunk.length === 0) break
      page += 1
    }
    installPickerPackages.value = merged
  } catch (e) {
    console.warn('加载安装包候选列表失败', e)
    installPickerPackages.value = []
  }
}

const handleRefresh = async () => {
  refreshLoading.value = true
  try {
    const ran = await loadVersionsMeta()
    if (!ran) {
      await loadPackages()
    }
    await Promise.all([loadReleases(), loadPlatforms(), loadScriptTemplates(), apiKeysStore.loadKeys()])
  } finally {
    refreshLoading.value = false
  }
}

const handleMoreCheckUpdate = () => {
  if (checkUpdateLoading.value) return
  moreActionsDropdown.close()
  handleCheckUpdate()
}

const handleMoreSyncPlatforms = () => {
  if (syncPlatformsLoading.value) return
  moreActionsDropdown.close()
  handleSyncPlatforms()
}

const toggleMoreActionsMenu = () => {
  const willOpen = !moreActionsDropdown.isOpen.value
  moreActionsDropdown.toggle()
  if (!willOpen) return
  nextTick(() => {
    const button = moreActionsDropdown.triggerRef.value
    if (!button) return
    const rect = button.getBoundingClientRect()
    const pos = clampFloatingMenu(rect)
    moreActionsMenuPosition.value = { top: pos.top, left: pos.left }
  })
}

const togglePackageMore = (packageId, event) => {
  if (openMorePackageId.value === packageId) {
    openMorePackageId.value = null
    return
  }
  openMorePackageId.value = packageId
  nextTick(() => {
    const button = event.currentTarget
    const rect = button.getBoundingClientRect()
    if (window.innerWidth < 768) {
      const pos = clampFloatingMenu(rect)
      packageMoreMenuPosition.value = { top: pos.top, left: pos.left, right: 0 }
    } else {
      packageMoreMenuPosition.value = {
        top: rect.top,
        left: 0,
        right: window.innerWidth - rect.right
      }
    }
  })
}

const closePackageMoreOnOutsideClick = (event) => {
  if (
    openMorePackageId.value &&
    !event.target.closest('[aria-label="更多操作"]') &&
    !event.target.closest('.fixed.z-50')
  ) {
    openMorePackageId.value = null
  }
}

const loadReleases = async () => {
  try {
    releases.value = await packagesApi.getReleases()
  } catch (e) {
    console.warn('获取 release 失败', e)
    releases.value = []
  }
}

const loadPlatforms = async () => {
  try {
    const data = await packagesApi.getPlatforms()
    platforms.value = data.platforms || []
  } catch (e) {
    console.warn('获取平台列表失败', e)
    platforms.value = []
  }
}

const loadScriptTemplates = async () => {
  try {
    scriptTemplates.value = await packagesApi.getScriptTemplates()
  } catch (e) {
    console.warn('获取脚本模板失败', e)
    scriptTemplates.value = {}
  }
}

const resolvePreferredApiKey = async () => {
  return apiKeysStore.resolveDefaultFullKey()
}

const handleSaveTemplate = async ({ platform, content }) => {
  savingTemplate.value = true
  try {
    await packagesApi.updateScriptTemplate(platform, content)
    alert('脚本模板保存成功')
    await loadScriptTemplates()
  } catch (e) {
    alert(`保存失败: ${e.message}`)
  } finally {
    savingTemplate.value = false
  }
}

const stopSyncPoll = () => {
  if (syncPollTimer) {
    clearInterval(syncPollTimer)
    syncPollTimer = null
  }
}

const pollSyncJob = (jobId) => {
  stopSyncPoll()
  return new Promise((resolve, reject) => {
    const tick = async () => {
      try {
        const job = await packagesApi.getSyncJob(jobId)
        syncProgress.value = {
          completed: job.completed ?? 0,
          total: job.total ?? 0,
          status: job.status || ''
        }
        if (job.status !== 'running' && job.status !== 'queued') {
          stopSyncPoll()
          resolve(job)
        }
      } catch (e) {
        stopSyncPoll()
        reject(e)
      }
    }
    tick()
    syncPollTimer = setInterval(tick, 1500)
  })
}

const formatSyncResultMessage = (job) => {
  const results = job.results || []
  const successCount = results.filter((r) => r.status === 'success').length
  const skippedCount = results.filter((r) => r.status === 'skipped').length
  const failCount = results.filter((r) => r.status === 'failed').length
  if (job.status === 'failed' && successCount === 0) {
    const detail = results.find((r) => r.status === 'failed')?.message
    return job.error || detail || '同步失败'
  }
  if (failCount > 0) {
    const failedNames = results
      .filter((r) => r.status === 'failed')
      .map((r) => r.platform || r.filename)
      .join('、')
    return `同步完成：成功 ${successCount} 个，失败 ${failCount} 个${failedNames ? `\n失败平台：${failedNames}` : ''}`
  }
  if (skippedCount > 0 && successCount === 0) {
    return `安装包已存在，已跳过 ${skippedCount} 个平台`
  }
  if (skippedCount > 0) {
    return `同步完成：成功 ${successCount} 个，跳过 ${skippedCount} 个`
  }
  return `同步成功，共 ${successCount} 个安装包`
}

const handleSync = async (payload) => {
  syncLoading.value = true
  syncProgress.value = { completed: 0, total: 0, status: 'queued' }
  try {
    const created = await packagesApi.sync(payload)
    syncProgress.value = {
      completed: created.completed ?? 0,
      total: created.total ?? 0,
      status: created.status || 'queued'
    }
    const job = await pollSyncJob(created.job_id)
    const message = formatSyncResultMessage(job)
    if (job.status === 'failed' && !(job.results || []).some((r) => r.status === 'success')) {
      alert(`同步失败: ${message}`)
    } else {
      alert(message)
      showSyncDialog.value = false
    }
    const ran = await loadVersionsMeta()
    if (!ran) {
      await loadPackages()
    }
    await Promise.all([loadPlatforms(), loadScriptTemplates()])
  } catch (e) {
    alert(`同步失败: ${e.message}`)
  } finally {
    stopSyncPoll()
    syncLoading.value = false
    syncProgress.value = { completed: 0, total: 0, status: '' }
  }
}

const handleUpload = async (payload) => {
  uploadLoading.value = true
  try {
    const fd = new FormData()
    if (payload.version) fd.append('version', payload.version)
    if (payload.platform) fd.append('platform', payload.platform)
    fd.append('package_file', payload.file)
    await packagesApi.upload(fd)
    alert('上传成功')
    showUploadDialog.value = false
    const ran = await loadVersionsMeta()
    if (!ran) {
      await loadPackages()
    }
  } catch (e) {
    alert(`上传失败: ${e.message}`)
  } finally {
    uploadLoading.value = false
  }
}

const handleUploadBatch = async ({ files }) => {
  uploadLoading.value = true
  try {
    const fd = new FormData()
    for (const f of files) {
      fd.append('package_files', f)
    }
    const result = await packagesApi.uploadBatch(fd)
    const { success_count, fail_count, errors } = result
    if (fail_count > 0) {
      const errorDetails = errors.map(e => `${e.filename}: ${e.detail}`).join('\n')
      alert(`上传完成：成功 ${success_count} 个，失败 ${fail_count} 个\n\n失败详情：\n${errorDetails}`)
    } else {
      alert(`批量上传成功，共 ${success_count} 个文件`)
    }
    showUploadDialog.value = false
    const ran = await loadVersionsMeta()
    if (!ran) {
      await loadPackages()
    }
  } catch (e) {
    alert(`批量上传失败: ${e.message}`)
  } finally {
    uploadLoading.value = false
  }
}

const remove = async (item) => {
  if (!confirm(`确认删除 ${item.filename} ?`)) return
  try {
    await packagesApi.delete(item.id)
    const ran = await loadVersionsMeta()
    if (!ran) {
      await loadPackages()
    }
  } catch (e) {
    alert(`删除失败: ${e.message}`)
  }
}

const handleMoreCopyDownload = async (event) => {
  if (!currentMorePackage.value) return
  await copyDownloadCommand(currentMorePackage.value, event)
  openMorePackageId.value = null
}

const handleMoreCopyInstall = async (event) => {
  if (!currentMorePackage.value) return
  await copyInstallCommand(currentMorePackage.value, event)
  openMorePackageId.value = null
}

const handleMoreCopyUpgrade = async (event) => {
  if (!currentMorePackage.value) return
  await copyUpgradeCommand(currentMorePackage.value, event)
  openMorePackageId.value = null
}

const handleMoreRemove = async () => {
  if (!currentMorePackage.value) return
  const item = currentMorePackage.value
  openMorePackageId.value = null
  await remove(item)
}

const handleCheckUpdate = async () => {
  checkUpdateLoading.value = true
  try {
    const result = await packagesApi.checkUpdate()
    if (result.has_update) {
      alert(`检测到新版本: ${result.latest_version}（本地：${result.local_version || '无'}）`)
    } else {
      alert(`当前已是最新版本: ${result.latest_version || '未知'}`)
    }
  } catch (e) {
    alert(`检查失败: ${e.message}`)
  } finally {
    checkUpdateLoading.value = false
  }
}

const handleSyncPlatforms = async () => {
  syncPlatformsLoading.value = true
  try {
    const data = await packagesApi.syncPlatforms()
    platforms.value = data.platforms || []
    const ran = await loadVersionsMeta()
    if (!ran) {
      await loadPackages()
    }
    await loadScriptTemplates()
    alert(`平台类型已同步到后台（${data.version || 'unknown'}）`)
  } catch (e) {
    alert(`同步平台类型失败: ${e.message}`)
  } finally {
    syncPlatformsLoading.value = false
  }
}

const copyDownloadCommand = async (item, event) => {
  const apiKey = await resolvePreferredApiKey()
  if (!apiKey) {
    alert('无法获取默认 API Key，请先在 API Key 页面创建或复制一次完整密钥')
    return
  }
  const cmd = `curl -L "${window.location.origin}${packagesApi.getDownloadUrl(item.id, apiKey)}" -o ${item.filename}`
  await copyWithTooltip(cmd, event)
}

/** 浏览器直接下载（接口仅认 API Key，与复制下载命令相同依赖默认密钥） */
const downloadPackageFile = async (item) => {
  const apiKey = await resolvePreferredApiKey()
  if (!apiKey) {
    alert('无法获取默认 API Key，请先在 API Key 页面创建或复制一次完整密钥')
    return
  }
  const path = packagesApi.getDownloadUrl(item.id, apiKey)
  const url = `${window.location.origin}${path}`
  const a = document.createElement('a')
  a.href = url
  a.setAttribute('download', item.filename || 'frp-package')
  a.rel = 'noopener noreferrer'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

const copyInstallCommand = async (item, event) => {
  const apiKey = await resolvePreferredApiKey()
  if (!apiKey) {
    alert('无法获取默认 API Key，请先在 API Key 页面创建或复制一次完整密钥')
    return
  }
  const url = packagesApi.getInstallScriptUrl({ package_id: item.id, api_key: apiKey })
  const cmd = `curl -sL "${window.location.origin}${url}" | bash`
  await copyWithTooltip(cmd, event)
}

const copyUpgradeCommand = async (item, event) => {
  const apiKey = await resolvePreferredApiKey()
  if (!apiKey) {
    alert('无法获取默认 API Key，请先在 API Key 页面创建或复制一次完整密钥')
    return
  }
  const url = packagesApi.getUpgradeScriptUrl({ package_id: item.id, api_key: apiKey })
  const cmd = `curl -sL "${window.location.origin}${url}" | bash`
  await copyWithTooltip(cmd, event)
}

const handleGenerateScript = async (payload) => {
  scriptLoading.value = true
  try {
    installScript.value = await packagesApi.getInstallScript({
      package_id: payload.package_id,
      install_path: payload.install_path,
      config_url: payload.config_url || undefined,
      api_key: payload.api_key
    })
  } catch (e) {
    alert(`生成脚本失败: ${e.message}`)
  } finally {
    scriptLoading.value = false
  }
}

const handleGenerateUpgradeScript = async (payload) => {
  scriptLoading.value = true
  try {
    upgradeScript.value = await packagesApi.getUpgradeScript({
      package_id: payload.package_id,
      install_path: payload.install_path,
      api_key: payload.api_key
    })
  } catch (e) {
    alert(`生成升级脚本失败: ${e.message}`)
  } finally {
    scriptLoading.value = false
  }
}

watch(
  filters,
  () => {
    if (filterSyncing.value) return
    persistFilters()
    pagination.page = 1
    loadPackages()
  },
  { deep: true }
)

watch(showInstallDialog, (open) => {
  if (open) {
    loadInstallDialogPackages()
  }
})

onMounted(async () => {
  document.addEventListener('click', closePackageMoreOnOutsideClick)
  apiKeysStore.selectedKeyId = apiKeysStore.getStoredDefaultId()
  const ran = await loadVersionsMeta()
  if (!ran) {
    await loadPackages()
  }
  await Promise.all([loadReleases(), loadPlatforms(), loadScriptTemplates(), apiKeysStore.loadKeys()])
})

onUnmounted(() => {
  document.removeEventListener('click', closePackageMoreOnOutsideClick)
  stopSyncPoll()
})
</script>
