<template>
  <SidebarProvider :default-open="true">
    <AppSidebar :role="currentUserRole" :version="appVersion" /><SidebarInset
      class="min-w-0 bg-muted/30"
    >
      <a
        href="#main-content"
        class="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:p-3"
        >跳至主要内容</a
      >
      <header
        class="app-header sticky top-0 z-30 border-b bg-background/95 backdrop-blur-sm"
      >
        <div class="app-container">
          <div
            class="flex h-14 min-h-14 items-center justify-between gap-2 sm:h-16 sm:gap-3"
          >
            <div class="flex min-w-0 items-center gap-3">
              <SidebarTrigger aria-label="切换导航菜单" /><span
                class="hidden text-sm text-muted-foreground sm:inline"
                >控制台</span
              ><span class="hidden text-border sm:inline">/</span
              ><span class="truncate text-sm font-medium">{{
                currentPageTitle
              }}</span>
            </div>
            <div class="flex shrink-0 items-center gap-1 sm:gap-3">
              <Button
                type="button"
                class="relative min-w-11 sm:min-w-0 sm:gap-1.5"
                tooltip="版本与更新"
                title="版本与更新"
                aria-label="版本与更新"
                @click="openVersionModal"
                variant="outline"
                size="sm"
                ><Tag class="h-4 w-4" /><span class="hidden sm:inline"
                  >v{{ appVersion || "…" }}</span
                ><span
                  v-if="updateStatus.hasUpdate"
                  class="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-red-500 ring-2 ring-white"
                ></span
              ></Button>
              <div
                v-if="currentUserRole === 'admin'"
                class="hidden lg:flex items-center gap-2"
              >
                <label class="text-xs text-gray-500 whitespace-nowrap"
                  >默认APPKey</label
                ><ResourceCombobox
                  :model-value="apiKeysStore.selectedKeyId"
                  @update:model-value="apiKeysStore.setDefaultKey"
                  label="选择 API Key"
                  class="w-40"
                  :fetch-options="
                    (params) =>
                      apiKeysApi.list({ ...params, available_only: true })
                  "
                  :resolve-option="apiKeysApi.get"
                />
              </div>
              <div class="relative">
                <ActionMenu
                  :items="
                    notifications.map((item) => ({
                      action: item.id,
                      label: item.title,
                    }))
                  "
                  @select="
                    (id) =>
                      handleNotificationClick(
                        notifications.find((item) => item.id === id),
                      )
                  "
                  ><template #trigger
                    ><Button
                      class="relative"
                      type="button"
                      aria-label="消息通知"
                      title="消息通知"
                      variant="ghost"
                      size="icon"
                      ><Bell class="h-5 w-5" /><span
                        v-if="unreadNotificationCount > 0"
                        class="absolute right-1 top-1 inline-flex h-2.5 w-2.5 rounded-full bg-red-500"
                      ></span></Button></template
                  ><template v-if="!notifications.length" #content
                    ><p class="p-3 text-sm text-muted-foreground">
                      暂无新消息
                    </p></template
                  ></ActionMenu
                >
              </div>
              <div class="relative">
                <ActionMenu
                  :items="[
                    { action: 'profile', label: '用户管理' },
                    { action: 'logout', label: '退出登录', danger: true },
                  ]"
                  @select="
                    (action) =>
                      action === 'profile' ? handleUserManage() : handleLogout()
                  "
                  ><template #trigger
                    ><Button
                      type="button"
                      aria-label="用户菜单"
                      title="用户菜单"
                      variant="ghost"
                      size="default"
                      ><span
                        class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 text-sm font-semibold text-blue-700"
                        aria-hidden="true"
                      >
                        {{
                          (authStore.username || "A").slice(0, 1).toUpperCase()
                        }}
                      </span>
                      <div class="hidden min-w-0 text-left xl:block">
                        <div class="truncate text-sm font-medium">
                          {{ authStore.username || "管理员" }}
                        </div>
                        <div class="text-xs text-gray-500">
                          {{
                            currentUserRole === "admin" ? "管理员" : "普通用户"
                          }}
                        </div>
                      </div></Button
                    ></template
                  ></ActionMenu
                >
              </div>
            </div>
          </div>
        </div>
      </header>
      <div
        id="main-content"
        tabindex="-1"
        class="app-main min-w-0 flex-1 py-5 sm:py-8"
      >
        <div class="app-container">
          <PageHeader
            v-if="pageIntro"
            :title="pageIntro.title"
            :description="pageIntro.description"
          /><router-view :key="route.path" />
        </div>
      </div>
      <footer class="hidden border-t border-gray-200 bg-white py-4 md:block">
        <div
          class="app-container flex flex-col gap-2 text-xs text-gray-500 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-3"
        >
          <span>FRP-AGENT v{{ appVersion || "…" }}</span
          ><span class="hidden text-gray-300 sm:inline">|</span
          ><span>Copyright &copy; {{ new Date().getFullYear() }}</span
          ><span class="hidden text-gray-300 sm:inline">|</span
          ><Button
            type="button"
            class="cursor-pointer text-left text-sm hover:underline"
            @click="openVersionModal"
            variant="ghost"
            size="default"
          >
            检查更新与发行说明
          </Button>
        </div>
      </footer> </SidebarInset
    ><BuiltinFrpsIntro
      v-if="currentUserRole === 'admin'"
      :blocked="showUserManageDialog || showVersionModal"
    /><!-- 新版本提示 --><!-- 版本与更新 --><Dialog
      v-if="showVersionModal"
      :open="true"
      @update:open="
        (open) => {
          if (!open) {
            closeVersionModal();
          }
        }
      "
      ><DialogContent class="sm:max-w-lg" :aria-describedby="undefined"
        ><DialogHeader
          ><DialogTitle
            ><svg
              class="h-5 w-5 shrink-0 text-blue-500"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
              />
            </svg>
            版本与更新
          </DialogTitle></DialogHeader
        >
        <div
          data-slot="dialog-body"
          class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
        >
          <!-- 版本对比卡片 -->
          <div class="grid grid-cols-2 gap-3 mb-4">
            <div class="rounded-lg border border-gray-200 bg-gray-50 p-3">
              <div class="text-xs font-medium text-gray-500 mb-1">当前版本</div>
              <div class="text-lg font-bold text-gray-900">
                v{{ displayCurrentVersion }}
              </div>
            </div>
            <div class="rounded-lg border border-gray-200 bg-gray-50 p-3">
              <div class="text-xs font-medium text-gray-500 mb-1">
                Gitee 最新
              </div>
              <div
                class="text-lg font-bold"
                :class="
                  updateStatus.latestVersion ? 'text-gray-900' : 'text-gray-400'
                "
              >
                {{
                  updateStatus.latestVersion
                    ? `v${updateStatus.latestVersion}`
                    : "—"
                }}
              </div>
            </div>
          </div>
          <!-- Release 名称 -->
          <div v-if="updateStatus.releaseName" class="mb-4 px-1">
            <span
              class="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 border border-blue-100"
            >
              <svg
                class="h-3.5 w-3.5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"
                />
              </svg>
              {{ updateStatus.releaseName }}
            </span>
          </div>
          <!-- 状态提示 -->
          <div
            v-if="!updateStatus.checkSuccess"
            class="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 mb-4 flex items-start gap-2.5"
          >
            <svg
              class="mt-0.5 h-5 w-5 shrink-0 text-amber-500"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <p class="text-amber-800">
              {{ updateStatus.checkMessage || "检查更新失败" }}
            </p>
          </div>
          <div
            v-else-if="updateStatus.hasUpdate"
            class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 mb-4 flex items-start gap-2.5"
          >
            <svg
              class="mt-0.5 h-5 w-5 shrink-0 text-red-500"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
            <div>
              <p class="font-medium text-red-800">
                发现新版本 v{{ updateStatus.latestVersion }}
              </p>
              <p class="text-red-700 mt-0.5 text-xs">
                请前往 Gitee Release 拉取镜像或按说明升级。
              </p>
            </div>
          </div>
          <div
            v-else-if="updateStatus.latestVersion"
            class="rounded-lg border border-green-200 bg-green-50 px-4 py-3 mb-4 flex items-start gap-2.5"
          >
            <svg
              class="mt-0.5 h-5 w-5 shrink-0 text-green-500"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p class="text-green-800">当前已是最新版本。</p>
          </div>
          <!-- 发行说明 -->
          <div v-if="updateStatus.releaseBody" class="mb-4">
            <div
              class="flex items-center gap-1.5 px-1 mb-2 text-xs font-semibold text-gray-500 uppercase tracking-wider"
            >
              <svg
                class="h-3.5 w-3.5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              发行说明
            </div>
            <pre
              class="text-xs leading-relaxed rounded-lg border border-gray-200 bg-gray-50 p-3.5 overflow-auto max-h-48 whitespace-pre-wrap text-gray-700"
              >{{ updateStatus.releaseBody }}</pre>
          </div>
          <div
            v-else-if="updateStatus.checkSuccess && updateStatus.latestVersion"
            class="text-xs text-gray-400 px-1 mb-4"
          >
            本 Release 暂无正文，可点击下方「在 Gitee 查看」。
          </div>
          <!-- 链接区 -->
          <div
            class="border-t border-gray-100 pt-3 flex flex-wrap gap-x-4 gap-y-2"
          >
            <a
              v-if="updateStatus.releaseUrl"
              :href="updateStatus.releaseUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-800 transition-colors"
            >
              <svg
                class="h-4 w-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                />
              </svg>
              在 Gitee 查看 </a
            ><a
              :href="GITEE_RELEASES_URL"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
            >
              <svg
                class="h-4 w-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M4 6h16M4 10h16M4 14h16M4 18h16"
                />
              </svg>
              全部发行版 </a
            ><a
              :href="GITEE_RELEASE_NOTES_URL"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
            >
              <svg
                class="h-4 w-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              仓库内版本说明
            </a>
          </div>
        </div>
        <DialogFooter
          ><Button
            type="button"
            :disabled="checkLoading"
            @click="closeVersionModal"
            variant="outline"
            size="default"
          >
            关闭 </Button
          ><Button
            type="button"
            :disabled="checkLoading"
            @click="refreshVersionCheck"
            variant="default"
            size="default"
            ><svg
              v-if="checkLoading"
              class="h-4 w-4 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              ></circle>
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path></svg
            ><RefreshCw v-else class="h-4 w-4" />
            刷新检查
          </Button></DialogFooter
        ></DialogContent
      ></Dialog
    ><UserManageDialog
      :show="showUserManageDialog"
      :force-mode="forcePasswordChange"
      :force-reason="forcePasswordChangeReason"
      @update:show="handleUserDialogShowChange"
      @cancel-force="handleCancelForce"
    />
  </SidebarProvider>
</template>

<script setup>
import ActionMenu from "@/components/ActionMenu.vue";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { confirmAction, notify } from "@/composables/useFeedback";
import BuiltinFrpsIntro from "@/components/BuiltinFrpsIntro.vue";
import { apiKeysApi } from "@/api/apiKeys";
import ResourceCombobox from "@/components/ResourceCombobox.vue";
import { ref, watch, onMounted, computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useApiKeysStore } from "@/stores/apiKeys";
import AppSidebar from "@/components/AppSidebar.vue";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { Bell, Tag, RefreshCw } from "@lucide/vue";
import PageHeader from "@/components/PageHeader.vue";
import UserManageDialog from "@/components/UserManageDialog.vue";
import { settingsApi } from "@/api/settings";
import { getSystemVersion, checkVersionUpdate } from "@/api/index";

/** 与后端 app/version.py 中 Gitee 仓库一致 */
const GITEE_REPO_URL = "https://gitee.com/numen06/frp-agent";
const GITEE_RELEASES_URL = `${GITEE_REPO_URL}/releases`;
const GITEE_RELEASE_NOTES_URL = `${GITEE_REPO_URL}/tree/dev/release-notes`;

const router = useRouter();
const route = useRoute();
const pageIntros = {
  "/proxies": {
    title: "代理列表",
    description: "查看代理状态、管理端口与分组，按需生成配置或升级客户端。",
  },
  "/groups": {
    title: "分组管理",
    description: "按业务组织代理，统一交付配置、安装脚本与客户端升级任务。",
  },
  "/tunnel-services": {
    title: "穿透服务",
    description: "管理 FRP 服务器节点，配置本实例的内置服务。",
  },
  "/packages": {
    title: "安装包管理",
    description: "同步或上传多平台 frpc 安装包，统一维护版本与部署脚本。",
  },
  "/api-keys": {
    title: "密钥管理",
    description: "管理自动化访问密钥，为配置分发、脚本部署和主机访问提供认证。",
  },
  "/converter": {
    title: "配置转换",
    description: "将旧版 INI 配置迁移到 TOML，预览转换结果并下载使用。",
  },
};
const pageIntro = computed(() => pageIntros[route.path]);
const authStore = useAuthStore();
const apiKeysStore = useApiKeysStore();

const showUserManageDialog = ref(false);
const forcePasswordChange = ref(false);
const forcePasswordChangeReason = ref("");
const suppressForcePasswordPrompt = ref(false);
const currentUserRole = ref("user");
const currentPageTitle = computed(() => {
  if (route.name === "HostDetail") return "主机详情";
  if (route.name === "HostEdit") return "编辑主机";
  if (route.name === "HostClone") return "克隆主机";
  if (route.name === "HostCreate") return "添加主机";
  return (
    pageIntro.value?.title ||
    { "/dashboard": "仪表盘", "/operations": "运行维护", "/hosts": "主机资源" }[
      route.path
    ] ||
    "控制台"
  );
});

// 下拉菜单和折叠功能

const appVersion = ref("");
const showVersionModal = ref(false);
const checkLoading = ref(false);

const updateStatus = ref({
  hasUpdate: false,
  latestVersion: null,
  releaseUrl: null,
  releaseName: null,
  releaseBodySummary: null,
  currentVersion: null,
  releaseBody: null,
  checkSuccess: true,
  checkMessage: "",
});

const displayCurrentVersion = computed(() => {
  return updateStatus.value.currentVersion || appVersion.value || "—";
});

async function loadSystemVersion() {
  if (!authStore.isAuthenticated) return;
  try {
    const res = await getSystemVersion();
    if (res?.success && res.version) {
      appVersion.value = res.version;
    }
  } catch (e) {
    console.error("获取系统版本失败:", e);
  }
}

function showUpdateToastOnce(resData) {
  const key = "frp-agent-update-notified-" + resData.latest_version;
  if (sessionStorage.getItem(key)) return;
  sessionStorage.setItem(key, "1");
  notify(
    "发现新版本 " + resData.latest_version + "，可在版本与更新中查看发行说明。",
  );
}

async function loadUpdateCheck({ showLoading = false, force = false } = {}) {
  if (!authStore.isAuthenticated) return;
  if (showLoading) checkLoading.value = true;
  try {
    const d = await checkVersionUpdate(force);
    updateStatus.value = {
      hasUpdate: !!d.has_update,
      latestVersion: d.latest_version || null,
      releaseUrl: d.release_url || null,
      releaseName: d.release_name || null,
      releaseBodySummary: d.release_body_summary || null,
      currentVersion: d.current_version || null,
      releaseBody: d.release_body || null,
      checkSuccess: !!d.success,
      checkMessage: d.message || "",
    };
    if (d.success && d.has_update) {
      showUpdateToastOnce(d);
    }
  } catch (e) {
    const prev = updateStatus.value.currentVersion;
    updateStatus.value = {
      hasUpdate: false,
      latestVersion: null,
      releaseUrl: null,
      releaseName: null,
      releaseBodySummary: null,
      currentVersion: prev || appVersion.value || null,
      releaseBody: null,
      checkSuccess: false,
      checkMessage: e?.message || "检查失败",
    };
  } finally {
    if (showLoading) checkLoading.value = false;
  }
}

function openVersionModal() {
  showVersionModal.value = true;
  loadUpdateCheck({ showLoading: true });
}

function closeVersionModal() {
  showVersionModal.value = false;
}

function refreshVersionCheck() {
  loadUpdateCheck({ showLoading: true, force: true });
}

const notifications = computed(() => {
  const items = [];
  if (forcePasswordChange.value) {
    items.push({
      id: "force-password-change",
      type: "forcePasswordChange",
      title:
        forcePasswordChangeReason.value || "检测到使用默认密码，请立即修改",
    });
  }
  return items;
});

const unreadNotificationCount = computed(() => notifications.value.length);

// 检查是否需要强制修改密码
const checkPasswordRequirement = async () => {
  if (!authStore.isAuthenticated) return;

  try {
    const result = await settingsApi.checkPasswordRequirement();
    if (result?.require_password_change && !suppressForcePasswordPrompt.value) {
      forcePasswordChange.value = true;
      forcePasswordChangeReason.value =
        result.reason || "检测到使用默认密码，请立即修改";
      showUserManageDialog.value = true;
    }
  } catch (error) {
    console.warn("检查密码要求失败:", error);
  }
};

// 监听路由查询参数
watch(
  () => route.query,
  (newQuery) => {
    if (
      newQuery.forcePasswordChange === "true" &&
      !suppressForcePasswordPrompt.value
    ) {
      forcePasswordChange.value = true;
      forcePasswordChangeReason.value =
        newQuery.reason || "检测到使用默认密码，请立即修改";
      showUserManageDialog.value = true;
      return;
    }

    // 路由不再要求强制改密时，恢复普通用户管理模式
    forcePasswordChange.value = false;
    forcePasswordChangeReason.value = "";
  },
  { immediate: true },
);

// 组件挂载时检查
onMounted(async () => {
  try {
    const userSettings = await settingsApi.getUserSettings();
    currentUserRole.value = userSettings.role || "user";
  } catch (error) {
    console.warn("获取当前用户角色失败:", error);
  }
  if (currentUserRole.value === "admin") {
    apiKeysStore.init();
  }
  if (route.query.forcePasswordChange === "true") {
    checkPasswordRequirement();
  }
  await loadSystemVersion();
  await loadUpdateCheck();
});

const handleUserManage = () => {
  // 手动打开用户管理时始终使用普通模式，避免遗留强制状态导致信息被隐藏
  forcePasswordChange.value = false;
  forcePasswordChangeReason.value = "";
  showUserManageDialog.value = true;
};

const handleCancelForce = () => {
  // 当前会话内可跳过，避免关闭后立即再次弹出
  suppressForcePasswordPrompt.value = true;
};

const handleUserDialogShowChange = (visible) => {
  showUserManageDialog.value = visible;
  if (!visible) {
    if (route.query.forcePasswordChange === "true") {
      router.replace({ query: {} });
    }
    // 关闭弹窗后恢复普通状态，防止残留状态导致再次拉起
    forcePasswordChange.value = false;
    forcePasswordChangeReason.value = "";
  }
};

const handleLogout = async () => {
  if (await confirmAction("确定要退出登录吗？")) {
    authStore.logout();
    router.push("/login");
  }
};

const handleNotificationClick = (notification) => {
  if (notification.type === "forcePasswordChange") {
    forcePasswordChange.value = true;
    forcePasswordChangeReason.value = notification.title;
    showUserManageDialog.value = true;
  }
};
</script>
