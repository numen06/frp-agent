<template>
  <div class="space-y-4">
    <Card
      ><CardHeader
        ><h3 class="text-base font-semibold text-gray-900">服务节点</h3>
        <Button type="button" variant="default" @click="showAddDialog = true"
          ><svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4 shrink-0"
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
          添加服务器
        </Button></CardHeader
      >
      <form
        class="flex gap-2 border-b border-gray-200 p-4"
        @submit.prevent="loadServers(1)"
      >
        <SearchField
          v-model="serversStore.search"
          placeholder="输入名称或关键词搜索"
          label="搜索列表"
          @search="loadServers(1)"
        ></SearchField
        ><Button type="submit" variant="outline" size="default">搜索</Button>
      </form>
      <div
        v-if="serversStore.error"
        role="alert"
        class="flex flex-wrap items-center justify-between gap-2 p-4 text-sm text-destructive"
      >
        {{ serversStore.error }}
        <Button type="button" variant="outline" @click="loadServers()"
          >重试读取节点</Button
        >
      </div>
      <div v-if="serversStore.loading" class="p-5">
        <div
          class="flex items-center justify-center gap-2 py-4 text-center text-sm text-gray-600"
        >
          <span
            class="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600"
            role="status"
            aria-label="加载中"
          ></span
          ><span>加载中...</span>
        </div>
      </div>
      <template v-else>
        <div class="hidden overflow-x-auto md:block">
          <Table class="w-full text-left"
            ><TableHeader
              ><TableRow
                ><TableHead>服务器名称</TableHead
                ><TableHead>服务器地址</TableHead><TableHead>端口</TableHead
                ><TableHead>API 地址</TableHead><TableHead>连接状态</TableHead
                ><TableHead>frps 版本</TableHead
                ><TableHead
                  class="w-[1%] whitespace-nowrap sticky right-0 bg-muted"
                  >操作</TableHead
                ></TableRow
              ></TableHeader
            ><TableBody
              ><TableRow
                v-if="serversStore.servers.length === 0 && !serversStore.error"
                ><TableCell colspan="7" class="text-center"
                  >暂无服务器</TableCell
                ></TableRow
              ><TableRow
                v-else
                v-for="server in serversStore.servers"
                :key="server.id"
                ><TableCell>{{ server.name }}</TableCell
                ><TableCell>{{ server.server_addr }}</TableCell
                ><TableCell>{{ server.server_port }}</TableCell
                ><TableCell
                  ><span class="text-xs text-gray-600">{{
                    server.api_base_url
                  }}</span></TableCell
                ><TableCell
                  ><span
                    class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                    :class="getServerStatusBadgeClass(server)"
                  >
                    {{ getServerStatusText(server) }}
                  </span></TableCell
                ><TableCell
                  ><Button
                    type="button"
                    class="text-sm hover:underline"
                    :title="server.last_version_check_message || ''"
                    @click="showVersionDetail(server)"
                    variant="ghost"
                    size="default"
                    >{{ server.server_version || "未知" }}</Button
                  ></TableCell
                ><TableCell
                  class="sticky right-0 w-36 min-w-36 max-w-36 bg-background shadow-[-1px_0_0_var(--border)] [&>div]:flex [&>div]:flex-nowrap [&>div]:gap-1"
                  ><div class="flex items-center justify-end gap-1">
                    <Button
                      @click="testServer(server)"
                      title="测试连接"
                      aria-label="测试连接"
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      tooltip="测试连接"
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
                        <path d="M5 12l5 -5l10 10l-5 5z" />
                        <path d="M12 5l7 7" /></svg></Button
                    ><Button
                      v-if="!server.is_builtin"
                      @click="editServer(server)"
                      title="编辑"
                      aria-label="编辑"
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      tooltip="编辑"
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
                          d="M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1"
                        />
                        <path
                          d="M20.385 6.585a2.1 2.1 0 0 0 -2.97 -2.97l-8.415 8.385v3h3l8.385 -8.415z"
                        />
                        <path d="M16 5l3 3" /></svg></Button
                    ><ActionMenu
                      label="服务器操作"
                      :items="[
                        {
                          action: 'version',
                          label: '刷新 FRP 版本',
                          disabled: versionRefreshingId === server.id,
                        },
                        ...(!server.is_builtin
                          ? [
                              { separator: true, label: '分隔' },
                              {
                                action: 'delete',
                                label: '删除服务器',
                                danger: true,
                              },
                            ]
                          : [{ action: 'builtin', label: '配置内置服务' }]),
                      ]"
                      @select="
                        (action) =>
                          action === 'version'
                            ? refreshFrpVersion(server)
                            : action === 'builtin'
                              ? router.push('/tunnel-services?tab=builtin')
                              : deleteServer(server)
                      "
                    /></div></TableCell></TableRow></TableBody
          ></Table>
        </div>
        <div class="md:hidden">
          <p
            v-if="serversStore.servers.length === 0 && !serversStore.error"
            class="px-4 py-8 text-center text-sm text-gray-500"
          >
            暂无服务器
          </p>
          <ul v-else class="mobile-record-list">
            <li
              v-for="server in serversStore.servers"
              :key="server.id"
              class="mobile-record h-60"
            >
              <div class="flex items-start justify-between gap-2">
                <div class="min-w-0 flex-1">
                  <div class="flex items-start gap-2">
                    <span
                      class="mobile-record-title flex-1"
                      :title="server.name"
                      >{{ server.name }}</span
                    ><span
                      class="inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                      :class="getServerStatusBadgeClass(server)"
                    >
                      {{ getServerStatusText(server) }}
                    </span>
                  </div>
                  <p
                    class="mt-1 truncate text-sm text-muted-foreground"
                    :title="`${server.server_addr}:${server.server_port}`"
                  >
                    {{ server.server_addr }}:{{ server.server_port }}
                  </p>
                  <p
                    class="mt-1 truncate text-xs text-muted-foreground"
                    :title="server.api_base_url"
                  >
                    {{ server.api_base_url }}
                  </p>
                </div>
                <Button
                  type="button"
                  class="max-w-24 shrink-0 overflow-hidden text-sm hover:underline"
                  aria-label="查看 FRP 版本详情"
                  tooltip="查看 FRP 版本详情"
                  :title="server.last_version_check_message || ''"
                  @click="showVersionDetail(server)"
                  variant="ghost"
                  size="default"
                  ><span class="truncate">{{
                    server.server_version || "未知"
                  }}</span></Button
                >
              </div>
              <div class="mt-auto flex items-center gap-2 border-t pt-3">
                <Button
                  @click="testServer(server)"
                  title="测试连接"
                  aria-label="测试连接"
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  tooltip="测试连接"
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
                    <path d="M5 12l5 -5l10 10l-5 5z" />
                    <path d="M12 5l7 7" /></svg></Button
                ><Button
                  v-if="!server.is_builtin"
                  @click="editServer(server)"
                  title="编辑"
                  aria-label="编辑"
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  tooltip="编辑"
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
                      d="M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1"
                    />
                    <path
                      d="M20.385 6.585a2.1 2.1 0 0 0 -2.97 -2.97l-8.415 8.385v3h3l8.385 -8.415z"
                    />
                    <path d="M16 5l3 3" /></svg></Button
                ><ActionMenu
                  label="服务器操作"
                  :items="[
                    {
                      action: 'version',
                      label: '刷新 FRP 版本',
                      disabled: versionRefreshingId === server.id,
                    },
                    ...(!server.is_builtin
                      ? [
                          { separator: true, label: '分隔' },
                          {
                            action: 'delete',
                            label: '删除服务器',
                            danger: true,
                          },
                        ]
                      : [{ action: 'builtin', label: '配置内置服务' }]),
                  ]"
                  @select="
                    (action) =>
                      action === 'version'
                        ? refreshFrpVersion(server)
                        : action === 'builtin'
                          ? router.push('/tunnel-services?tab=builtin')
                          : deleteServer(server)
                  "
                />
              </div>
            </li>
          </ul>
        </div> </template
    ></Card>
    <div class="rounded-xl border border-gray-200 bg-white p-4">
      <TablePagination
        :total="serversStore.pagination.total"
        :page="serversStore.pagination.page"
        :page-size="serversStore.pagination.page_size"
        @page-change="loadServers"
        @page-size-change="serversStore.resize"
      />
    </div>
    <Dialog
      v-if="showAddDialog"
      :open="true"
      @update:open="
        (open) => {
          if (!open && !saving) {
            closeAddDialog();
          }
        }
      "
      ><DialogContent
        class="sm:max-w-lg"
        :aria-describedby="undefined"
        :show-close-button="!saving"
        ><DialogHeader
          ><DialogTitle>{{
            editingServer ? "编辑服务器" : "添加服务器"
          }}</DialogTitle></DialogHeader
        >
        <div
          data-slot="dialog-body"
          class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
        >
          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >服务器名称 <span class="text-red-600">*</span></label
            ><Input
              type="text"
              class="block w-full"
              v-model="serverForm.name"
              aria-label="服务器名称"
              required
            ></Input>
          </div>
          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >服务器地址 <span class="text-red-600">*</span></label
            ><Input
              type="text"
              class="block w-full"
              v-model="serverForm.server_addr"
              aria-label="服务器地址"
              @change="generateApiUrl"
              required
            ></Input>
          </div>
          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >服务器端口 <span class="text-red-600">*</span></label
            ><Input
              type="number"
              class="block w-full"
              v-model.number="serverForm.server_port"
              min="1"
              max="65535"
              required
            ></Input>
          </div>
          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >API 基础地址 <span class="text-red-600">*</span></label
            ><Input
              type="text"
              class="block w-full"
              v-model="serverForm.api_base_url"
              aria-label="API 基础地址"
              required
            ></Input
            ><small class="mt-1 block text-xs text-gray-500"
              >可自动生成或手动修改</small
            >
          </div>
          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >认证用户名 <span class="text-red-600">*</span></label
            ><Input
              type="text"
              class="block w-full"
              v-model="serverForm.auth_username"
              aria-label="认证用户名"
              required
            ></Input>
          </div>
          <div class="mb-4">
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >认证密码 <span class="text-red-600">*</span></label
            ><Input
              type="password"
              class="block w-full"
              v-model="serverForm.auth_password"
              aria-label="认证密码"
              :required="!editingServer"
              :placeholder="
                editingServer ? '留空保留已保存密码' : '请输入认证密码'
              "
              autocomplete="new-password"
            ></Input>
          </div>
          <div class="mb-0">
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >认证 Token</label
            ><Input
              type="password"
              class="block w-full"
              v-model="serverForm.auth_token"
              aria-label="认证 Token"
              :placeholder="
                editingServer
                  ? '留空保留已保存 Token'
                  : '可选，留空使用用户名密码认证'
              "
              autocomplete="new-password"
            ></Input>
          </div>
          <p
            v-if="saveError"
            role="alert"
            class="mt-3 text-sm text-destructive"
          >
            {{ saveError }}
          </p>
        </div>
        <DialogFooter
          ><Button
            type="button"
            class="inline-flex w-full items-center justify-center gap-2 text-sm font-medium transition-colors sm:mr-auto sm:w-auto"
            @click="closeAddDialog"
            :disabled="saving"
            variant="ghost"
            size="default"
            >取消</Button
          ><Button
            type="button"
            class="inline-flex w-full items-center justify-center gap-2 text-sm font-medium transition-colors sm:w-auto"
            @click="testConnection"
            :disabled="saving"
            variant="ghost"
            size="default"
            >测试连接</Button
          ><Button
            type="button"
            class="w-full sm:w-auto"
            @click="handleSubmit"
            :disabled="saving"
            variant="default"
            size="default"
            >{{ saving ? "保存中…" : "保存" }}</Button
          ></DialogFooter
        ></DialogContent
      ></Dialog
    ><Dialog
      v-if="versionDetailServer"
      :open="true"
      @update:open="
        (open) => {
          if (!open) {
            closeVersionDetail();
          }
        }
      "
      ><DialogContent class="sm:max-w-md" :aria-describedby="undefined"
        ><div
          data-slot="dialog-body"
          class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
        >
          <div class="mb-4 flex items-center justify-between">
            <h3>FRP 版本 - {{ versionDetailServer.name }}</h3>
          </div>
          <div
            v-if="versionDetailLoading"
            class="py-6 text-center text-sm text-gray-500"
          >
            加载中...
          </div>
          <div v-else-if="versionDetail" class="space-y-4 text-sm">
            <div>
              <div class="font-medium text-gray-700">frps</div>
              <div class="mt-1 text-gray-900">
                {{ versionDetail.server.server_version || "未知" }}
              </div>
              <div
                v-if="versionDetail.server.last_version_check_time"
                class="mt-1 text-xs text-gray-500"
              >
                最近检查：{{
                  formatDateTime(versionDetail.server.last_version_check_time)
                }}
              </div>
              <div
                v-if="versionDetail.server.last_version_check_message"
                class="mt-0.5 text-xs text-gray-500"
              >
                {{ versionDetail.server.last_version_check_message }}
              </div>
            </div>
            <div>
              <div class="font-medium text-gray-700">frpc 分布</div>
              <ul class="mt-2 space-y-1">
                <li
                  v-for="item in versionDetail.clients.versions"
                  :key="item.client_version"
                  class="flex justify-between text-gray-800"
                >
                  <span>{{ item.client_version }}</span
                  ><span class="text-gray-500">{{ item.count }} 个代理</span>
                </li>
                <li
                  v-if="versionDetail.clients.unknown_version_count > 0"
                  class="flex justify-between text-gray-500"
                >
                  <span>未知</span
                  ><span
                    >{{
                      versionDetail.clients.unknown_version_count
                    }}
                    个代理</span
                  >
                </li>
                <li
                  v-if="versionDetail.clients.total_proxies === 0"
                  class="text-gray-500"
                >
                  暂无代理
                </li>
              </ul>
            </div>
          </div>
        </div>
        <DialogFooter
          ><Button
            type="button"
            class="w-full text-sm font-medium sm:w-auto"
            @click="closeVersionDetail"
            variant="ghost"
            size="default"
            >关闭</Button
          ><Button
            type="button"
            class="w-full sm:w-auto"
            :disabled="versionRefreshingId === versionDetailServer?.id"
            @click="refreshFrpVersion(versionDetailServer)"
            variant="outline"
            size="default"
          >
            刷新版本
          </Button></DialogFooter
        ></DialogContent
      ></Dialog
    >
  </div>
</template>

<script setup>
import ActionMenu from "@/components/ActionMenu.vue";
import SearchField from "@/components/SearchField.vue";
import { CardHeader } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Table } from "@/components/ui/table";
import { TableBody } from "@/components/ui/table";
import { TableCell } from "@/components/ui/table";
import { TableHeader } from "@/components/ui/table";
import { TableRow } from "@/components/ui/table";
import { TableHead } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { notify, confirmAction } from "@/composables/useFeedback";
import TablePagination from "@/components/TablePagination.vue";
import { ref, reactive, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useServersStore } from "@/stores/servers";
import { serverApi } from "@/api/servers";

const serversStore = useServersStore();
async function loadServers(page = serversStore.pagination.page) {
  try {
    await serversStore.loadServers(page);
  } catch {
    /* Store retains the retryable error. */
  }
}
const router = useRouter();
const showAddDialog = ref(false);
const saving = ref(false),
  saveError = ref("");
const editingServer = ref(null);
const versionRefreshingId = ref(null);
const versionDetailServer = ref(null);
const versionDetail = ref(null);
const versionDetailLoading = ref(false);

const serverForm = reactive({
  name: "",
  server_addr: "",
  server_port: 7000,
  api_base_url: "",
  auth_username: "admin",
  auth_password: "",
  auth_token: "",
});

onMounted(async () => {
  try {
    await serversStore.loadServers();
  } catch (error) {
    console.error("加载服务器列表失败:", error);
  }
});

const generateApiUrl = () => {
  if (serverForm.server_addr && !serverForm.api_base_url) {
    const addr = serverForm.server_addr.replace(/^https?:\/\//, "");
    serverForm.api_base_url = `http://${addr}/api`;
  }
};

const handleSubmit = async () => {
  if (saving.value) return;
  if (
    !serverForm.name ||
    !serverForm.server_addr ||
    !serverForm.api_base_url ||
    !serverForm.auth_username ||
    (!editingServer.value && !serverForm.auth_password)
  ) {
    notify("请填写必填项");
    return;
  }

  saving.value = true;
  saveError.value = "";
  try {
    const payload = { ...serverForm };
    if (editingServer.value) {
      for (const key of ["auth_password", "auth_token"])
        if (!payload[key]) delete payload[key];
      await serversStore.updateServer(editingServer.value.id, payload);
      notify("更新成功");
    } else {
      await serversStore.addServer(payload);
      notify("添加成功");
    }
    showAddDialog.value = false;
    resetForm();
    serversStore.markRefreshNeeded();
  } catch (error) {
    saveError.value = "操作失败: " + error.message;
  } finally {
    saving.value = false;
  }
};

const editServer = (server) => {
  editingServer.value = server;
  for (const key of Object.keys(serverForm))
    serverForm[key] = server[key] ?? serverForm[key];
  serverForm.auth_password = "";
  serverForm.auth_token = "";
  saveError.value = "";
  showAddDialog.value = true;
};

const deleteServer = async (server) => {
  if (!(await confirmAction(`确定要删除服务器 "${server.name}" 吗？`))) {
    return;
  }

  try {
    await serversStore.deleteServer(server.id);
    notify("删除成功");
    serversStore.markRefreshNeeded();
  } catch (error) {
    notify("删除失败: " + error.message);
  }
};

const testServer = async (server) => {
  try {
    await serversStore.testServer(server.id);
    notify("连接测试成功");
    serversStore.markRefreshNeeded();
  } catch (error) {
    notify("连接测试失败: " + error.message);
  }
};

const testConnection = async () => {
  if (editingServer.value) {
    try {
      await serversStore.testServer(editingServer.value.id);
      notify("连接测试成功");
      serversStore.markRefreshNeeded();
    } catch (error) {
      notify("连接测试失败: " + error.message);
    }
  } else {
    notify("请先保存服务器信息");
  }
};

const resetForm = () => {
  saveError.value = "";
  editingServer.value = null;
  Object.assign(serverForm, {
    name: "",
    server_addr: "",
    server_port: 7000,
    api_base_url: "",
    auth_username: "admin",
    auth_password: "",
    auth_token: "",
  });
};

const closeAddDialog = () => {
  showAddDialog.value = false;
  resetForm();
};

// 使用统一的模态框功能

const getServerStatusBadgeClass = (server) => {
  if (!server.last_test_status || server.last_test_status === "unknown")
    return "bg-gray-100 text-gray-800";
  return server.last_test_status === "online"
    ? "bg-green-100 text-green-800"
    : "bg-red-100 text-red-800";
};

const getServerStatusText = (server) => {
  if (!server.last_test_status || server.last_test_status === "unknown")
    return "未测试";
  return server.last_test_status === "online" ? "在线" : "离线";
};

const formatDateTime = (value) => {
  if (!value) return "";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString();
};

const showVersionDetail = async (server) => {
  versionDetailServer.value = server;
  versionDetailLoading.value = true;
  versionDetail.value = null;
  try {
    versionDetail.value = await serverApi.getFrpVersion(server.id);
  } catch (error) {
    notify("获取版本信息失败: " + error.message);
    versionDetailServer.value = null;
  } finally {
    versionDetailLoading.value = false;
  }
};

const closeVersionDetail = () => {
  versionDetailServer.value = null;
  versionDetail.value = null;
};

const refreshFrpVersion = async (server) => {
  versionRefreshingId.value = server.id;
  try {
    const result = await serversStore.refreshFrpVersion(server.id, {
      refresh_proxies: true,
    });
    if (versionDetailServer.value?.id === server.id) {
      versionDetail.value = result;
    }
    notify("FRP 版本已刷新");
  } catch (error) {
    notify("刷新失败: " + error.message);
  } finally {
    versionRefreshingId.value = null;
  }
};
</script>
