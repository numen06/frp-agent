<template>
  <div>
    <Card
      ><CardHeader
        ><h3 class="text-base font-semibold text-gray-900">FRP 安装包管理</h3>
        <div class="flex w-full flex-wrap gap-2 md:w-auto md:justify-end">
          <Button
            class="flex-1 sm:flex-none"
            type="button"
            :disabled="refreshLoading"
            @click="handleRefresh"
            variant="outline"
            size="sm"
            ><svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              stroke-width="2"
              stroke="currentColor"
              fill="none"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path stroke="none" d="M0 0h24v24H0z" fill="none" />
              <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
              <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4" />
            </svg>
            {{ refreshLoading ? "刷新中..." : "刷新" }}</Button
          ><Button
            class="flex-1 sm:flex-none"
            type="button"
            @click="showSyncDialog = true"
            variant="default"
            size="sm"
            ><svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              stroke-width="2"
              stroke="currentColor"
              fill="none"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path stroke="none" d="M0 0h24v24H0z" fill="none" />
              <path d="M3 14v4a1 1 0 0 0 1 1h4" />
              <path d="M17 3h4a1 1 0 0 1 1 1v4" />
              <path d="M16 8l-8 8" />
            </svg>
            GitHub 同步 </Button
          ><Button
            class="flex-1 sm:flex-none"
            type="button"
            @click="showUploadDialog = true"
            variant="default"
            size="sm"
            ><svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              stroke-width="2"
              stroke="currentColor"
              fill="none"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path stroke="none" d="M0 0h24v24H0z" fill="none" />
              <path d="M12 5l0 14" />
              <path d="M5 12l14 0" />
            </svg>
            手动上传 </Button
          ><Button
            class="flex-1 sm:flex-none"
            type="button"
            @click="showInstallDialog = true"
            variant="default"
            size="sm"
            ><svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              stroke-width="2"
              stroke="currentColor"
              fill="none"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path stroke="none" d="M0 0h24v24H0z" fill="none" />
              <path d="M7 8l-4 4l4 4" />
              <path d="M17 8l4 4l-4 4" />
              <path d="M14 4l-4 16" />
            </svg>
            脚本生成
          </Button>
          <div class="relative w-full sm:w-auto">
            <ActionMenu
              text="更多"
              label="更多安装包管理操作"
              variant="outline"
              :items="[
                {
                  action: 'update',
                  label: '检查更新',
                  disabled: checkUpdateLoading,
                },
                {
                  action: 'platforms',
                  label: '同步平台类型',
                  disabled: syncPlatformsLoading,
                },
                { separator: true, label: '分隔' },
                { action: 'template', label: '脚本模板编辑' },
              ]"
              @select="
                (action) => {
                  if (action === 'update') handleCheckUpdate();
                  else if (action === 'platforms') handleSyncPlatforms();
                  else showTemplateDialog = true;
                }
              "
            />
          </div></div></CardHeader
      ><CardContent
        ><div class="mb-4 flex flex-col gap-3 md:grid md:grid-cols-3">
          <Select v-model="filters.version"
            ><SelectTrigger class="w-full" aria-label="全部版本"
              ><SelectValue placeholder="全部版本"></SelectValue></SelectTrigger
            ><SelectContent
              ><SelectItem :value="null">全部版本</SelectItem
              ><SelectItem
                v-if="versionsMeta.latest_version"
                value="__latest__"
              >
                最新（{{ versionsMeta.latest_version }}） </SelectItem
              ><SelectGroup v-if="recentVersionsForUi.length"
                ><SelectLabel>最近</SelectLabel
                ><SelectItem
                  v-for="v in recentVersionsForUi"
                  :key="'rv-' + v"
                  :value="v"
                  >{{ v }}</SelectItem
                ></SelectGroup
              ><SelectGroup v-if="otherVersionsForUi.length"
                ><SelectLabel>其他版本</SelectLabel
                ><SelectItem
                  v-for="v in otherVersionsForUi"
                  :key="'ov-' + v"
                  :value="v"
                  >{{ v }}</SelectItem
                ></SelectGroup
              ></SelectContent
            ></Select
          ><Select v-model="filters.platform"
            ><SelectTrigger class="w-full" aria-label="全部平台"
              ><SelectValue placeholder="全部平台"></SelectValue></SelectTrigger
            ><SelectContent
              ><SelectItem :value="null">全部平台</SelectItem
              ><SelectItem v-for="p in platforms" :key="p" :value="p">{{
                p
              }}</SelectItem></SelectContent
            ></Select
          ><Select v-model="filters.source"
            ><SelectTrigger class="w-full" aria-label="全部来源"
              ><SelectValue placeholder="全部来源"></SelectValue></SelectTrigger
            ><SelectContent
              ><SelectItem :value="null">全部来源</SelectItem
              ><SelectItem value="github">github</SelectItem
              ><SelectItem value="upload">upload</SelectItem></SelectContent
            ></Select
          >
          <Button
            v-if="filters.version || filters.platform || filters.source"
            type="button"
            variant="ghost"
            class="md:col-span-3 md:justify-self-start"
            @click="
              Object.assign(filters, { version: '', platform: '', source: '' })
            "
            >清除筛选</Button
          >
        </div>
        <div
          v-if="listError"
          role="alert"
          class="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-destructive/30 p-3 text-sm text-destructive"
        >
          {{ listError
          }}<Button type="button" variant="outline" @click="loadPackages"
            >重试读取安装包</Button
          >
        </div>
        <div v-if="loading" class="py-8 text-center">
          <span
            class="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600 align-middle"
            role="status"
            aria-label="加载中"
          ></span
          ><span class="ml-2 align-middle text-sm text-gray-500"
            >加载中...</span
          >
        </div>
        <div v-else>
          <div class="hidden overflow-x-auto md:block">
            <Table class="w-full text-left"
              ><TableHeader
                ><TableRow
                  ><TableHead>ID</TableHead><TableHead>版本</TableHead
                  ><TableHead>平台</TableHead><TableHead>文件名</TableHead
                  ><TableHead>大小</TableHead><TableHead>来源</TableHead
                  ><TableHead>下载时间</TableHead><TableHead>SHA256</TableHead
                  ><TableHead class="whitespace-nowrap" style="min-width: 96px"
                    >操作</TableHead
                  ></TableRow
                ></TableHeader
              ><TableBody
                ><TableRow v-if="packages.length === 0 && !listError"
                  ><TableCell colspan="9" class="text-center"
                    >暂无安装包</TableCell
                  ></TableRow
                ><TableRow v-for="item in packages" :key="item.id"
                  ><TableCell>{{ item.id }}</TableCell
                  ><TableCell
                    ><span
                      class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium"
                      :class="
                        item.source === 'github'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-gray-100 text-gray-700'
                      "
                      >{{ item.version }}</span
                    ></TableCell
                  ><TableCell class="whitespace-nowrap">{{
                    item.platform
                  }}</TableCell
                  ><TableCell
                    ><span class="truncate" :title="item.filename">{{
                      item.filename
                    }}</span></TableCell
                  ><TableCell class="whitespace-nowrap">{{
                    formatSize(item.file_size)
                  }}</TableCell
                  ><TableCell
                    ><span
                      class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium"
                      :class="
                        item.source === 'github'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-gray-100 text-gray-700'
                      "
                      >{{ item.source }}</span
                    ></TableCell
                  ><TableCell class="whitespace-nowrap">{{
                    formatDate(item.downloaded_at)
                  }}</TableCell
                  ><TableCell
                    ><code class="text-xs text-gray-500"
                      >{{ item.sha256_checksum?.slice(0, 12) }}...</code
                    ></TableCell
                  ><TableCell
                    ><div class="flex flex-wrap items-center gap-1.5">
                      <Button
                        title="下载安装包"
                        type="button"
                        @click="downloadPackageFile(item)"
                        variant="ghost"
                        size="icon-sm"
                        aria-label="下载安装包"
                        tooltip="下载安装包"
                        ><svg
                          xmlns="http://www.w3.org/2000/svg"
                          class="h-4 w-4"
                          width="24"
                          height="24"
                          viewBox="0 0 24 24"
                          stroke-width="2"
                          stroke="currentColor"
                          fill="none"
                          stroke-linecap="round"
                          stroke-linejoin="round"
                        >
                          <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                          <path
                            d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-2"
                          />
                          <polyline points="7 11 12 16 17 11" />
                          <line x1="12" y1="4" x2="12" y2="16" /></svg></Button
                      ><ActionMenu
                        :items="[
                          { action: 'download', label: '复制下载命令' },
                          { action: 'install', label: '复制安装命令' },
                          { action: 'upgrade', label: '复制升级命令' },
                          { separator: true, label: '分隔' },
                          { action: 'delete', label: '删除', danger: true },
                        ]"
                        @select="
                          (action, event) =>
                            handlePackageAction(action, item, event)
                        "
                      /></div></TableCell></TableRow></TableBody
            ></Table>
          </div>
          <div class="md:hidden">
            <p
              v-if="packages.length === 0 && !listError"
              class="py-8 text-center text-gray-500"
            >
              暂无安装包
            </p>
            <ul v-else class="mobile-record-list px-0">
              <li
                v-for="item in packages"
                :key="item.id"
                class="mobile-record h-[19rem]"
              >
                <h3 class="mobile-record-title" :title="item.platform">
                  {{ item.platform }}
                </h3>
                <div class="flex min-w-0 gap-2 text-xs">
                  <span
                    class="max-w-[70%] truncate rounded-md bg-secondary px-2 py-1"
                    :title="item.version"
                    >{{ item.version }}</span
                  >
                  <span class="truncate rounded-md bg-secondary px-2 py-1">{{
                    item.source
                  }}</span>
                </div>
                <p
                  class="line-clamp-2 min-h-10 break-all text-sm text-muted-foreground"
                  :title="item.filename"
                >
                  {{ item.filename }}
                </p>
                <dl
                  class="grid min-w-0 grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs text-muted-foreground"
                >
                  <dt>大小</dt>
                  <dd class="truncate">{{ formatSize(item.file_size) }}</dd>
                  <dt>下载时间</dt>
                  <dd class="truncate">{{ formatDate(item.downloaded_at) }}</dd>
                  <dt>SHA256</dt>
                  <dd class="truncate font-mono" :title="item.sha256_checksum">
                    {{ item.sha256_checksum?.slice(0, 16) || "未记录" }}…
                  </dd>
                </dl>
                <div class="mt-auto flex gap-2 border-t pt-3">
                  <Button
                    class="flex-1"
                    type="button"
                    variant="outline"
                    aria-label="下载安装包"
                    @click="downloadPackageFile(item)"
                    >下载</Button
                  >
                  <ActionMenu
                    text="更多"
                    label="安装包操作"
                    variant="outline"
                    :items="[
                      { action: 'download', label: '复制下载命令' },
                      { action: 'install', label: '复制安装命令' },
                      { action: 'upgrade', label: '复制升级命令' },
                      { separator: true, label: '分隔' },
                      { action: 'delete', label: '删除', danger: true },
                    ]"
                    @select="
                      (action, event) =>
                        handlePackageAction(action, item, event)
                    "
                  />
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
          </div></div></CardContent></Card
    ><PackageSyncDialog
      v-model="showSyncDialog"
      :releases="syncDialogReleases"
      :loading="syncLoading"
      :progress="syncProgress"
      @submit="handleSync"
    /><PackageUploadDialog
      v-model="showUploadDialog"
      :platforms="platforms"
      :loading="uploadLoading"
      @submit="handleUpload"
      @submit-batch="handleUploadBatch"
    /><PackageInstallDialog
      v-model="showInstallDialog"
      :packages="packages"
      :latest-version="versionsMeta.latest_version"
      :loading="scriptLoading"
      :script="installScript"
      :upgrade-script="upgradeScript"
      @submit="handleGenerateScript"
      @submit-upgrade="handleGenerateUpgradeScript"
    /><ScriptTemplateDialog
      v-model="showTemplateDialog"
      :platforms="platforms"
      :templates="scriptTemplates"
      :saving="savingTemplate"
      @save="handleSaveTemplate"
    />
  </div>
</template>

<script setup>
onMounted(async () => {
  apiKeysStore.selectedKeyId = apiKeysStore.getStoredDefaultId();
  const ran = await loadVersionsMeta();
  if (!ran) await loadPackages();
  await Promise.all([
    loadReleases(),
    loadPlatforms(),
    loadScriptTemplates(),
    apiKeysStore.loadKeys(),
  ]);
});
onUnmounted(() => stopSyncPoll());
import { CardHeader, CardContent } from "@/components/ui/card";
import ActionMenu from "@/components/ActionMenu.vue";
async function handlePackageAction(action, item, event) {
  if (action === "delete") return remove(item);
  if (action === "download") await copyDownloadCommand(item, event);
  else if (action === "install") await copyInstallCommand(item, event);
  else if (action === "upgrade") await copyUpgradeCommand(item, event);
}
import { Table } from "@/components/ui/table";
import { TableBody } from "@/components/ui/table";
import { TableCell } from "@/components/ui/table";
import { TableHeader } from "@/components/ui/table";
import { TableRow } from "@/components/ui/table";
import { TableHead } from "@/components/ui/table";
import { Select } from "@/components/ui/select";
import { SelectContent } from "@/components/ui/select";
import { SelectGroup } from "@/components/ui/select";
import { SelectLabel } from "@/components/ui/select";
import { SelectItem } from "@/components/ui/select";
import { SelectTrigger } from "@/components/ui/select";
import { SelectValue } from "@/components/ui/select";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { notify, confirmAction } from "@/composables/useFeedback";
import {
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  reactive,
  ref,
  watch,
} from "vue";
import { packagesApi } from "@/api/packages";
import { useApiKeysStore } from "@/stores/apiKeys";
import { copyText } from "@/composables/useClipboard";
import PackageSyncDialog from "@/components/PackageSyncDialog.vue";
import PackageUploadDialog from "@/components/PackageUploadDialog.vue";
import PackageInstallDialog from "@/components/PackageInstallDialog.vue";
import ScriptTemplateDialog from "@/components/ScriptTemplateDialog.vue";
import TablePagination from "@/components/TablePagination.vue";

const loading = ref(false);
const listError = ref("");
let listRequest = 0;
const syncLoading = ref(false);
const syncProgress = ref({ completed: 0, total: 0, status: "" });
let syncPollTimer = null;
const uploadLoading = ref(false);
const scriptLoading = ref(false);
const showSyncDialog = ref(false);
const showUploadDialog = ref(false);
const showInstallDialog = ref(false);
const showTemplateDialog = ref(false);
const checkUpdateLoading = ref(false);
const syncPlatformsLoading = ref(false);
const savingTemplate = ref(false);
const refreshLoading = ref(false);

/** 从服务端恢复/修正筛选条件时避免 watch 重复请求 */
const filterSyncing = ref(false);

const packages = ref([]);
const releases = ref([]);
const installScript = ref("");
const upgradeScript = ref("");
const scriptTemplates = ref({});
const apiKeysStore = useApiKeysStore();

const PKG_FILTER_KEY = "fm_package_list_filters_v1";
const PKG_PAGE_SIZE_KEY = "fm_package_list_page_size_v1";

function readSavedPageSize() {
  try {
    const raw = localStorage.getItem(PKG_PAGE_SIZE_KEY);
    const n = raw ? parseInt(raw, 10) : 20;
    if ([10, 20, 50, 100].includes(n)) return n;
  } catch {
    /* ignore */
  }
  return 20;
}

function readSavedFilters() {
  try {
    const raw = localStorage.getItem(PKG_FILTER_KEY);
    if (raw) {
      const o = JSON.parse(raw);
      if (o && typeof o === "object") {
        return {
          version: typeof o.version === "string" ? o.version : "",
          platform: typeof o.platform === "string" ? o.platform : "",
          source: typeof o.source === "string" ? o.source : "",
        };
      }
    }
  } catch {
    /* ignore */
  }
  return { version: "", platform: "", source: "" };
}

const platforms = ref([]);
const filters = reactive(readSavedFilters());
const pagination = reactive({
  page: 1,
  page_size: readSavedPageSize(),
  total: 0,
});
const versionsMeta = ref({
  versions: [],
  latest_version: "",
  recent_versions: [],
  synced_at: null,
});

const recentVersionsForUi = computed(() => {
  const recent = versionsMeta.value.recent_versions || [];
  const lv = versionsMeta.value.latest_version;
  return recent.filter((v) => v && v !== lv);
});

const otherVersionsForUi = computed(() => {
  const merged = versionsMeta.value.versions || [];
  const recent = new Set(versionsMeta.value.recent_versions || []);
  const lv = versionsMeta.value.latest_version;
  return merged.filter((v) => v && !recent.has(v) && v !== lv);
});

const syncDialogReleases = computed(() => {
  const byVersion = new Map();
  for (const item of releases.value || []) {
    if (item?.version) {
      byVersion.set(item.version, {
        ...item,
        platforms: item.platforms || [],
      });
    }
  }
  const localVersions = versionsMeta.value.versions || [];
  const latest = versionsMeta.value.latest_version;
  for (const version of localVersions) {
    if (!version || byVersion.has(version)) continue;
    byVersion.set(version, {
      version,
      name: version,
      platforms: version === latest ? platforms.value : [],
      source: "local-cache",
    });
  }
  return Array.from(byVersion.values());
});

const formatDate = (v) => (v ? new Date(v).toLocaleString("zh-CN") : "");
const formatSize = (s) => {
  if (!s) return "0 B";
  if (s < 1024) return `${s} B`;
  if (s < 1024 * 1024) return `${(s / 1024).toFixed(1)} KB`;
  return `${(s / 1024 / 1024).toFixed(1)} MB`;
};

const resolveVersionForApi = () => {
  const v = filters.version;
  if (!v) return undefined;
  if (v === "__latest__") {
    const lv = versionsMeta.value.latest_version;
    return lv || undefined;
  }
  return v;
};

const persistFilters = () => {
  try {
    localStorage.setItem(PKG_FILTER_KEY, JSON.stringify({ ...filters }));
  } catch {
    /* ignore */
  }
};

const loadVersionsMeta = async () => {
  let ranLoadPackages = false;
  try {
    const data = await packagesApi.getVersions();
    versionsMeta.value = {
      versions: data.versions || [],
      latest_version: data.latest_version || "",
      recent_versions: data.recent_versions || [],
      synced_at: data.synced_at,
    };
    const sel = filters.version;
    const merged = versionsMeta.value.versions || [];
    const latest = versionsMeta.value.latest_version;
    if (sel === "__latest__" && !latest) {
      filterSyncing.value = true;
      filters.version = "";
      filterSyncing.value = false;
      persistFilters();
      pagination.page = 1;
      await loadPackages();
      ranLoadPackages = true;
    } else if (
      sel &&
      sel !== "__latest__" &&
      merged.length &&
      !merged.includes(sel)
    ) {
      filterSyncing.value = true;
      filters.version = "";
      filterSyncing.value = false;
      persistFilters();
      pagination.page = 1;
      await loadPackages();
      ranLoadPackages = true;
    }
  } catch (e) {
    console.warn("获取版本列表失败", e);
    versionsMeta.value = {
      versions: [],
      latest_version: "",
      recent_versions: [],
      synced_at: null,
    };
  }
  return ranLoadPackages;
};

const persistPageSize = () => {
  try {
    localStorage.setItem(PKG_PAGE_SIZE_KEY, String(pagination.page_size));
  } catch {
    /* ignore */
  }
};

const buildListParams = (page, pageSize) => {
  const params = {
    version: resolveVersionForApi(),
    platform: filters.platform || undefined,
    source: filters.source || undefined,
    page,
    page_size: pageSize,
  };
  return Object.fromEntries(
    Object.entries(params).filter(([, val]) => val !== undefined && val !== ""),
  );
};

const loadPackages = async () => {
  const request = ++listRequest;
  loading.value = true;
  listError.value = "";
  try {
    const clean = buildListParams(pagination.page, pagination.page_size);
    const res = await packagesApi.list(clean);
    if (request !== listRequest) return;
    const items = res.items || [];
    const total = res.total ?? 0;
    pagination.total = total;
    if (items.length === 0 && total > 0 && pagination.page > 1) {
      pagination.page = Math.max(
        1,
        Math.ceil(total / pagination.page_size) || 1,
      );
      const clean2 = buildListParams(pagination.page, pagination.page_size);
      const res2 = await packagesApi.list(clean2);
      if (request !== listRequest) return;
      packages.value = res2.items || [];
      pagination.total = res2.total ?? total;
      return;
    }
    packages.value = items;
  } catch (e) {
    if (request === listRequest)
      listError.value = e.message || "安装包读取失败，请重试";
  } finally {
    if (request === listRequest) loading.value = false;
  }
};

const onPackagePageChange = (p) => {
  pagination.page = p;
  loadPackages();
};

const onPackagePageSizeChange = (ps) => {
  pagination.page_size = ps;
  pagination.page = 1;
  persistPageSize();
  loadPackages();
};

const handleRefresh = async () => {
  refreshLoading.value = true;
  try {
    const ran = await loadVersionsMeta();
    if (!ran) {
      await loadPackages();
    }
    await Promise.all([
      loadReleases(),
      loadPlatforms(),
      loadScriptTemplates(),
      apiKeysStore.loadKeys(),
    ]);
  } finally {
    refreshLoading.value = false;
  }
};

const loadReleases = async () => {
  try {
    releases.value = await packagesApi.getReleases();
  } catch (e) {
    console.warn("获取 release 失败", e);
    releases.value = [];
  }
};

const loadPlatforms = async () => {
  try {
    const data = await packagesApi.getPlatforms();
    platforms.value = data.platforms || [];
  } catch (e) {
    console.warn("获取平台列表失败", e);
    platforms.value = [];
  }
};

const loadScriptTemplates = async () => {
  try {
    scriptTemplates.value = await packagesApi.getScriptTemplates();
  } catch (e) {
    console.warn("获取脚本模板失败", e);
    scriptTemplates.value = {};
  }
};

const resolvePreferredApiKey = async () => {
  return apiKeysStore.resolveDefaultFullKey();
};

const handleSaveTemplate = async ({ platform, content }) => {
  savingTemplate.value = true;
  try {
    await packagesApi.updateScriptTemplate(platform, content);
    notify("脚本模板保存成功");
    await loadScriptTemplates();
  } catch (e) {
    notify(`保存失败: ${e.message}`);
  } finally {
    savingTemplate.value = false;
  }
};

const stopSyncPoll = () => {
  if (syncPollTimer) {
    clearInterval(syncPollTimer);
    syncPollTimer = null;
  }
};

const pollSyncJob = (jobId) => {
  stopSyncPoll();
  return new Promise((resolve, reject) => {
    const tick = async () => {
      try {
        const job = await packagesApi.getSyncJob(jobId);
        syncProgress.value = {
          completed: job.completed ?? 0,
          total: job.total ?? 0,
          status: job.status || "",
        };
        if (job.status !== "running" && job.status !== "queued") {
          stopSyncPoll();
          resolve(job);
        }
      } catch (e) {
        stopSyncPoll();
        reject(e);
      }
    };
    tick();
    syncPollTimer = setInterval(tick, 1500);
  });
};

const formatSyncResultMessage = (job) => {
  const results = job.results || [];
  const successCount = results.filter((r) => r.status === "success").length;
  const skippedCount = results.filter((r) => r.status === "skipped").length;
  const failCount = results.filter((r) => r.status === "failed").length;
  if (job.status === "failed" && successCount === 0) {
    const detail = results.find((r) => r.status === "failed")?.message;
    return job.error || detail || "同步失败";
  }
  if (failCount > 0) {
    const failedNames = results
      .filter((r) => r.status === "failed")
      .map((r) => r.platform || r.filename)
      .join("、");
    return `同步完成：成功 ${successCount} 个，失败 ${failCount} 个${failedNames ? `\n失败平台：${failedNames}` : ""}`;
  }
  if (skippedCount > 0 && successCount === 0) {
    return `安装包已存在，已跳过 ${skippedCount} 个平台`;
  }
  if (skippedCount > 0) {
    return `同步完成：成功 ${successCount} 个，跳过 ${skippedCount} 个`;
  }
  return `同步成功，共 ${successCount} 个安装包`;
};

const handleSync = async (payload) => {
  syncLoading.value = true;
  syncProgress.value = { completed: 0, total: 0, status: "queued" };
  try {
    const created = await packagesApi.sync(payload);
    syncProgress.value = {
      completed: created.completed ?? 0,
      total: created.total ?? 0,
      status: created.status || "queued",
    };
    const job = await pollSyncJob(created.job_id);
    const message = formatSyncResultMessage(job);
    if (
      job.status === "failed" &&
      !(job.results || []).some((r) => r.status === "success")
    ) {
      notify(`同步失败: ${message}`);
    } else {
      notify(message);
      showSyncDialog.value = false;
    }
    const ran = await loadVersionsMeta();
    if (!ran) {
      await loadPackages();
    }
    await Promise.all([loadPlatforms(), loadScriptTemplates()]);
  } catch (e) {
    notify(`同步失败: ${e.message}`);
  } finally {
    stopSyncPoll();
    syncLoading.value = false;
    syncProgress.value = { completed: 0, total: 0, status: "" };
  }
};

const handleUpload = async (payload) => {
  uploadLoading.value = true;
  try {
    const fd = new FormData();
    if (payload.version) fd.append("version", payload.version);
    if (payload.platform) fd.append("platform", payload.platform);
    fd.append("package_file", payload.file);
    await packagesApi.upload(fd);
    notify("上传成功");
    showUploadDialog.value = false;
    const ran = await loadVersionsMeta();
    if (!ran) {
      await loadPackages();
    }
  } catch (e) {
    notify(`上传失败: ${e.message}`);
  } finally {
    uploadLoading.value = false;
  }
};

const handleUploadBatch = async ({ files }) => {
  uploadLoading.value = true;
  try {
    const fd = new FormData();
    for (const f of files) {
      fd.append("package_files", f);
    }
    const result = await packagesApi.uploadBatch(fd);
    const { success_count, fail_count, errors } = result;
    if (fail_count > 0) {
      const errorDetails = errors
        .map((e) => `${e.filename}: ${e.detail}`)
        .join("\n");
      notify(
        `上传完成：成功 ${success_count} 个，失败 ${fail_count} 个\n\n失败详情：\n${errorDetails}`,
      );
    } else {
      notify(`批量上传成功，共 ${success_count} 个文件`);
    }
    showUploadDialog.value = false;
    const ran = await loadVersionsMeta();
    if (!ran) {
      await loadPackages();
    }
  } catch (e) {
    notify(`批量上传失败: ${e.message}`);
  } finally {
    uploadLoading.value = false;
  }
};

const remove = async (item) => {
  if (!(await confirmAction(`确认删除 ${item.filename} ?`))) return;
  try {
    await packagesApi.delete(item.id);
    const ran = await loadVersionsMeta();
    if (!ran) {
      await loadPackages();
    }
  } catch (e) {
    notify(`删除失败: ${e.message}`);
  }
};

const handleCheckUpdate = async () => {
  checkUpdateLoading.value = true;
  try {
    const result = await packagesApi.checkUpdate();
    if (result.has_update) {
      notify(
        `检测到新版本: ${result.latest_version}（本地：${result.local_version || "无"}）`,
      );
    } else {
      notify(`当前已是最新版本: ${result.latest_version || "未知"}`);
    }
  } catch (e) {
    notify(`检查失败: ${e.message}`);
  } finally {
    checkUpdateLoading.value = false;
  }
};

const handleSyncPlatforms = async () => {
  syncPlatformsLoading.value = true;
  try {
    const data = await packagesApi.syncPlatforms();
    platforms.value = data.platforms || [];
    const ran = await loadVersionsMeta();
    if (!ran) {
      await loadPackages();
    }
    await loadScriptTemplates();
    notify(`平台类型已同步到后台（${data.version || "unknown"}）`);
  } catch (e) {
    notify(`同步平台类型失败: ${e.message}`);
  } finally {
    syncPlatformsLoading.value = false;
  }
};

const copyDownloadCommand = async (item, event) => {
  const apiKey = await resolvePreferredApiKey();
  if (!apiKey) {
    notify("无法获取默认 API Key，请先在 API Key 页面创建或复制一次完整密钥");
    return;
  }
  const cmd = `curl -L "${window.location.origin}${packagesApi.getDownloadUrl(item.id, apiKey)}" -o ${item.filename}`;
  await copyText(cmd, event);
};

/** 浏览器直接下载（接口仅认 API Key，与复制下载命令相同依赖默认密钥） */
const downloadPackageFile = async (item) => {
  const apiKey = await resolvePreferredApiKey();
  if (!apiKey) {
    notify("无法获取默认 API Key，请先在 API Key 页面创建或复制一次完整密钥");
    return;
  }
  const path = packagesApi.getDownloadUrl(item.id, apiKey);
  const url = `${window.location.origin}${path}`;
  const a = document.createElement("a");
  a.href = url;
  a.setAttribute("download", item.filename || "frp-package");
  a.rel = "noopener noreferrer";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
};

const copyInstallCommand = async (item, event) => {
  const apiKey = await resolvePreferredApiKey();
  if (!apiKey) {
    notify("无法获取默认 API Key，请先在 API Key 页面创建或复制一次完整密钥");
    return;
  }
  const url = packagesApi.getInstallScriptUrl({
    package_id: item.id,
    api_key: apiKey,
  });
  const cmd = `curl -sL "${window.location.origin}${url}" | bash`;
  await copyText(cmd, event);
};

const copyUpgradeCommand = async (item, event) => {
  const apiKey = await resolvePreferredApiKey();
  if (!apiKey) {
    notify("无法获取默认 API Key，请先在 API Key 页面创建或复制一次完整密钥");
    return;
  }
  const url = packagesApi.getUpgradeScriptUrl({
    package_id: item.id,
    api_key: apiKey,
  });
  const cmd = `curl -sL "${window.location.origin}${url}" | bash`;
  await copyText(cmd, event);
};

const handleGenerateScript = async (payload) => {
  scriptLoading.value = true;
  try {
    installScript.value = await packagesApi.getInstallScript({
      package_id: payload.package_id,
      install_path: payload.install_path,
      config_url: payload.config_url || undefined,
      api_key: payload.api_key,
    });
  } catch (e) {
    notify(`生成脚本失败: ${e.message}`);
  } finally {
    scriptLoading.value = false;
  }
};

const handleGenerateUpgradeScript = async (payload) => {
  scriptLoading.value = true;
  try {
    upgradeScript.value = await packagesApi.getUpgradeScript({
      package_id: payload.package_id,
      install_path: payload.install_path,
      api_key: payload.api_key,
    });
  } catch (e) {
    notify(`生成升级脚本失败: ${e.message}`);
  } finally {
    scriptLoading.value = false;
  }
};

watch(
  filters,
  () => {
    if (filterSyncing.value) return;
    persistFilters();
    pagination.page = 1;
    loadPackages();
  },
  { deep: true },
);
</script>
