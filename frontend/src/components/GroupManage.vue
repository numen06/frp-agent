<template>
  <div>
    <div class="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-2">
      <p class="mb-0 text-sm text-gray-500">管理所有代理分组，支持重命名和快速生成配置</p>
      <div class="flex w-full flex-wrap gap-2 sm:w-auto sm:justify-end">
        <button
          type="button"
          class="btn btn-sm btn-primary min-h-10 flex-1 sm:min-h-8 sm:flex-none"
          @click="showCreateDialog = true"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none" />
            <path d="M12 5l0 14" />
            <path d="M5 12l14 0" />
          </svg>
          新增分组
        </button>
        <button
          type="button"
          class="btn btn-sm btn-warning min-h-10 flex-1 sm:min-h-8 sm:flex-none"
          @click="openImportOrganizeDialog"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none" />
            <path d="M4 13h5l2-3h2l2 3h5" />
            <path d="M4 17h5l2-3h2l2 3h5" />
            <path d="M4 9l16 0" />
          </svg>
          导入/整理
        </button>
      </div>
    </div>

    <div class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <div class="p-3 sm:p-6">
        <div class="mb-3">
          <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div class="w-full min-w-0 sm:max-w-[250px]">
              <TableSearch
                v-model="groupsStore.filters.search"
                placeholder="搜索分组名称..."
                :debounce="300"
                @search="handleSearch"
              />
            </div>
          </div>
        </div>
        <div class="hidden overflow-x-auto md:block">
          <table class="w-full border-collapse text-left text-sm text-gray-700">
            <thead>
              <tr>
                <th class="border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">分组名称</th>
                <th class="border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">代理数量</th>
                <th class="border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">在线</th>
                <th class="border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">离线</th>
                <th class="w-[1%] whitespace-nowrap border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="groupsStore.loading">
                <td colspan="5" class="py-4 text-center">
                  <span class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600 align-middle" role="status" aria-label="加载中" />
                  <span class="ml-2 align-middle text-gray-600">加载中...</span>
                </td>
              </tr>
              <tr v-else-if="groupsStore.groups.length === 0">
                <td colspan="5" class="py-4 text-center text-gray-500">暂无分组，请先创建分组或导入配置</td>
              </tr>
              <tr
                v-else
                v-for="group in groupsStore.groups"
                :key="group.group_name"
                :data-group-name="group.group_name"
                :class="{ 'bg-amber-50': props.highlightGroup === group.group_name }"
              >
                <td class="border-b border-gray-100 px-4 py-3 align-middle">
                  <strong
                    class="font-semibold"
                    :class="props.highlightGroup === group.group_name ? 'text-amber-600' : 'text-blue-600'"
                  >{{ group.group_name }}</strong>
                </td>
                <td class="border-b border-gray-100 px-4 py-3 align-middle">{{ group.total_count }}</td>
                <td class="border-b border-gray-100 px-4 py-3 align-middle">
                  <span class="inline-flex rounded-md bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">{{ group.online_count }}</span>
                </td>
                <td class="border-b border-gray-100 px-4 py-3 align-middle">
                  <span class="inline-flex rounded-md bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">{{ group.offline_count }}</span>
                </td>
                <td class="border-b border-gray-100 px-4 py-3 align-middle">
                  <div class="inline-flex items-center gap-1.5">
                    <button
                      type="button"
                      class="btn btn-icon-sm btn-icon-primary"
                      title="查看代理"
                      aria-label="查看代理"
                      @click="viewGroupProxies(group.group_name)"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                        <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                        <path d="M10 10m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0" />
                        <path d="M21 21l-6 -6" />
                      </svg>
                    </button>
                    <button
                      type="button"
                      class="btn btn-icon-sm btn-icon-success"
                      title="一键部署"
                      aria-label="一键部署"
                      @click="openDeployDialog(group)"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                        <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                        <path d="M12 3l0 18" />
                        <path d="M8 7l4 -4l4 4" />
                        <path d="M8 17l4 4l4 -4" />
                      </svg>
                    </button>
                    <button
                      type="button"
                      class="btn btn-icon-sm btn-icon-accent"
                      title="客户端升级"
                      aria-label="客户端升级"
                      @click="openClientUpgradeDialog(group)"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                        <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                        <path d="M12 3l0 18" />
                        <path d="M8 7l4 -4l4 4" />
                        <path d="M8 17l4 4l4 -4" />
                      </svg>
                    </button>
                    <button
                      type="button"
                      class="btn btn-icon-sm btn-icon-muted"
                      title="更多"
                      aria-label="更多操作"
                      @click.stop="toggleGroupMore(group.group_name, $event)"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                        <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                        <circle cx="5" cy="12" r="1" fill="currentColor" />
                        <circle cx="12" cy="12" r="1" fill="currentColor" />
                        <circle cx="19" cy="12" r="1" fill="currentColor" />
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="md:hidden">
          <div v-if="groupsStore.loading" class="py-4 text-center text-sm text-gray-600">
            <span class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600 align-middle" role="status" aria-label="加载中" />
            <span class="ml-2 align-middle">加载中...</span>
          </div>
          <p v-else-if="groupsStore.groups.length === 0" class="py-8 text-center text-sm text-gray-500">暂无分组，请先创建分组或导入配置</p>
          <ul v-else class="divide-y divide-gray-100">
            <li
              v-for="group in groupsStore.groups"
              :key="group.group_name"
              :data-group-name="group.group_name"
              class="p-4"
              :class="{ 'bg-amber-50': props.highlightGroup === group.group_name }"
            >
              <div class="flex flex-wrap items-center gap-2">
                <strong
                  class="text-base font-semibold"
                  :class="props.highlightGroup === group.group_name ? 'text-amber-600' : 'text-blue-600'"
                >{{ group.group_name }}</strong>
                <span class="text-xs text-gray-500">共 {{ group.total_count }} 个</span>
              </div>
              <div class="mt-2 flex flex-wrap gap-2 text-xs">
                <span class="inline-flex rounded-md bg-green-100 px-2 py-0.5 font-medium text-green-800">在线 {{ group.online_count }}</span>
                <span class="inline-flex rounded-md bg-red-100 px-2 py-0.5 font-medium text-red-800">离线 {{ group.offline_count }}</span>
              </div>
              <div class="mt-3 grid grid-cols-3 gap-2">
                <button
                  type="button"
                  class="btn btn-sm btn-icon-primary min-h-10 gap-1.5 px-2"
                  title="查看代理"
                  aria-label="查看代理"
                  @click="viewGroupProxies(group.group_name)"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                    <path d="M10 10m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0" />
                    <path d="M21 21l-6 -6" />
                  </svg>
                  <span class="text-xs font-medium">代理</span>
                </button>
                <button
                  type="button"
                  class="btn btn-sm btn-icon-success min-h-10 gap-1.5 px-2"
                  title="一键部署"
                  aria-label="一键部署"
                  @click="openDeployDialog(group)"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                    <path d="M12 3l0 18" />
                    <path d="M8 7l4 -4l4 4" />
                    <path d="M8 17l4 4l4 -4" />
                  </svg>
                  <span class="text-xs font-medium">部署</span>
                </button>
                <button
                  type="button"
                  class="btn btn-sm btn-icon-muted min-h-10 gap-1.5 px-2"
                  title="更多"
                  aria-label="更多操作"
                  @click.stop="toggleGroupMore(group.group_name, $event)"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                    <circle cx="5" cy="12" r="1" fill="currentColor" />
                    <circle cx="12" cy="12" r="1" fill="currentColor" />
                    <circle cx="19" cy="12" r="1" fill="currentColor" />
                  </svg>
                  <span class="text-xs font-medium">更多</span>
                </button>
              </div>
            </li>
          </ul>
        </div>
        <div v-if="groupsStore.pagination.total > 0" class="mt-3">
          <TablePagination
            :total="groupsStore.pagination.total"
            :page="groupsStore.pagination.page"
            :page-size="groupsStore.pagination.page_size"
            @page-change="handlePageChange"
            @page-size-change="handlePageSizeChange"
          />
        </div>
      </div>
    </div>

    <!-- 创建分组对话框 -->
    <Teleport to="body">
      <div
        v-if="showCreateDialog"
        class="fixed inset-0 z-50 flex items-end justify-center p-2 sm:items-center sm:p-4"
        role="dialog"
        aria-modal="true"
      >
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="closeCreateDialog" />
        <div
          class="relative z-10 flex h-[calc(100dvh-1rem)] max-h-[calc(100dvh-1rem)] w-full max-w-md flex-col overflow-hidden rounded-t-xl border border-gray-200 bg-white shadow-xl will-change-transform sm:h-auto sm:max-h-[min(90vh,640px)] sm:rounded-xl"
          @click.stop
        >
          <div class="flex shrink-0 items-center justify-between border-b border-gray-200 px-6 py-4">
            <h2 class="text-lg font-semibold text-gray-900">新增分组</h2>
            <button
              type="button"
              class="inline-flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800"
              aria-label="关闭"
              @click="closeCreateDialog"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                <path d="M18 6l-12 12" />
                <path d="M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="min-h-0 flex-1 overflow-y-auto px-6 py-4">
            <label class="mb-1 block text-sm font-medium text-gray-700">
              分组名称 <span class="text-red-600">*</span>
            </label>
            <input
              v-model="createForm.group_name"
              type="text"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm transition-colors focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              placeholder="例如: dlyy"
              required
            />
          </div>
          <div class="flex shrink-0 flex-wrap items-center justify-end gap-2 border-t border-gray-200 bg-gray-50 px-6 py-4">
            <button
              type="button"
              class="mr-auto inline-flex items-center justify-center rounded-lg bg-gray-200 px-3 py-2 text-sm font-medium text-gray-800 transition-colors hover:bg-gray-300"
              @click="closeCreateDialog"
            >
              取消
            </button>
            <button
              type="button"
              class="inline-flex items-center justify-center rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
              @click="handleCreateGroup"
            >
              创建
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 导入/整理对话框 -->
    <Teleport to="body">
      <div
        v-if="showImportDialog"
        class="fixed inset-0 z-50 flex items-end justify-center p-2 sm:items-center sm:p-4"
        role="dialog"
        aria-modal="true"
      >
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="closeImportDialog" />
        <div
          class="relative z-10 flex h-[calc(100dvh-1rem)] max-h-[calc(100dvh-1rem)] w-full max-w-xl flex-col overflow-hidden rounded-t-xl border border-gray-200 bg-white shadow-xl will-change-transform sm:h-auto sm:max-h-[min(92vh,720px)] sm:rounded-xl"
          @click.stop
        >
          <div class="flex shrink-0 items-center justify-between border-b border-gray-200 px-6 py-4">
            <h2 class="text-lg font-semibold text-gray-900">导入/整理</h2>
            <button
              type="button"
              class="inline-flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800"
              aria-label="关闭"
              @click="closeImportDialog"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                <path d="M18 6l-12 12" />
                <path d="M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="min-h-0 flex-1 overflow-y-auto px-6 py-4 space-y-4">
            <!-- 自动分析分组 -->
            <div class="rounded-lg border border-green-200 bg-green-50 p-4">
              <p class="text-sm font-medium text-green-900">自动分析分组</p>
              <p class="mt-1 text-xs text-green-800">
                从代理名称自动识别分组，仅对分组为「其他」或空的代理进行分析，不会覆盖已有分组。
              </p>
              <button
                type="button"
                :disabled="analyzeLoading"
                class="mt-3 inline-flex items-center justify-center rounded-lg bg-green-600 px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-green-700 disabled:opacity-50"
                @click="handleAutoAnalyze"
              >
                <span v-if="analyzeLoading" class="mr-1 inline-block h-3 w-3 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                开始自动分析
              </button>
              <div v-if="analyzeSummary" class="mt-3 rounded-lg border border-green-300 bg-white p-3 text-xs text-green-900">
                <p v-if="analyzeSummary.error" class="font-medium text-red-700">{{ analyzeSummary.error }}</p>
                <template v-else>
                  <p class="font-medium">分析摘要</p>
                  <p class="mt-1">总代理数 {{ analyzeSummary.total }}，更新 {{ analyzeSummary.updated }}，跳过 {{ analyzeSummary.skipped }}，未变化 {{ analyzeSummary.unchanged }}</p>
                  <p v-if="analyzeSummary.new_groups?.length" class="mt-1">新识别分组：{{ analyzeSummary.new_groups.join('、') }}</p>
                </template>
              </div>
            </div>

            <div class="border-t border-gray-100 pt-1">
              <p class="mb-3 text-sm font-medium text-gray-800">配置导入</p>
            </div>

            <!-- 导入方式选择 -->
            <div>
              <label class="mb-2 block text-sm font-medium text-gray-700">导入方式</label>
              <div class="flex gap-2">
                <button
                  type="button"
                  :class="importForm.mode === 'command' ? 'bg-orange-500 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'"
                  class="flex-1 rounded-lg px-3 py-2 text-xs font-medium transition-colors"
                  @click="importForm.mode = 'command'"
                >
                  生成命令（推荐）
                </button>
                <button
                  type="button"
                  :class="importForm.mode === 'paste' ? 'bg-orange-500 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'"
                  class="flex-1 rounded-lg px-3 py-2 text-xs font-medium transition-colors"
                  @click="importForm.mode = 'paste'"
                >
                  粘贴配置内容
                </button>
              </div>
            </div>

            <!-- 分组名称 -->
            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700">
                分组名称 <span class="text-red-600">*</span>
              </label>
              <input
                v-model="importForm.group_name"
                type="text"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm transition-colors focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                placeholder="例如: dlyy"
                required
              />
            </div>

            <!-- 生成命令模式 -->
            <template v-if="importForm.mode === 'command'">
              <!-- 扫描路径 -->
              <div>
                <label class="mb-1 block text-sm font-medium text-gray-700">
                  目标服务器扫描路径
                </label>
                <input
                  v-model="importForm.config_path"
                  type="text"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono text-gray-900 shadow-sm transition-colors focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  placeholder="/opt/frp"
                />
                <p class="mt-1 text-xs text-gray-400">
                  指定<strong>文件</strong>则只读该文件；指定<strong>目录</strong>且其中有 .ini/.toml 时<strong>只使用该目录</strong>，不与当前目录合并。仅当指定目录下没有这些文件时，才退回到<strong>执行命令时的当前目录</strong>扫描。
                </p>
              </div>

              <!-- 覆盖选项 -->
              <div class="flex items-center gap-2">
                <input
                  id="import-overwrite-cmd"
                  v-model="importForm.overwrite"
                  type="checkbox"
                  class="h-4 w-4 rounded border-gray-300 text-orange-500 focus:ring-orange-500"
                />
                <label for="import-overwrite-cmd" class="text-sm text-gray-700">
                  覆盖已存在的同名代理（默认开启）
                </label>
              </div>

              <!-- 自动生成命令展示 -->
              <div v-if="importPreview.loading" class="flex items-center gap-2 text-sm text-gray-500">
                <span class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-orange-500" />
                正在生成导入命令预览…
              </div>
              <div v-else-if="importPreview.missing_requirements.length" class="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
                <p
                  v-for="item in importPreview.missing_requirements"
                  :key="item.code"
                  class="text-sm text-amber-800"
                >
                  {{ item.message }}
                </p>
              </div>
              <div v-else-if="importDisplayCommand" class="space-y-2">
                <div v-if="importPreview.warnings.length" class="rounded-lg border border-amber-100 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                  <p v-for="(warning, idx) in importPreview.warnings" :key="idx">{{ warning }}</p>
                </div>
                <div class="rounded-lg bg-gray-900 p-3">
                  <div class="mb-2 flex items-center justify-between">
                    <span class="text-xs font-medium text-gray-400">复制到目标服务器执行（一条命令即可）：</span>
                    <button
                      type="button"
                      class="text-xs text-orange-400 transition-colors hover:text-orange-300"
                      @click="copyImportCommand"
                    >
                      {{ importCopied ? '已复制' : '复制' }}
                    </button>
                  </div>
                  <pre class="overflow-x-auto whitespace-pre-wrap break-all text-xs text-green-400">{{ importDisplayCommand }}</pre>
                </div>
                <details v-if="importCommandDetail" class="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-600">
                  <summary class="cursor-pointer font-medium text-gray-700 hover:text-gray-900">详情说明</summary>
                  <p class="mt-2 whitespace-pre-wrap border-t border-gray-200 pt-2 text-gray-500">{{ importCommandDetail }}</p>
                </details>
              </div>
              <p v-else-if="!importForm.group_name.trim()" class="text-sm text-gray-500">
                填写分组名称后将自动生成导入命令。
              </p>
            </template>

            <!-- 粘贴导入模式 -->
            <template v-if="importForm.mode === 'paste'">
              <!-- 配置格式 -->
              <div>
                <label class="mb-1 block text-sm font-medium text-gray-700">配置格式</label>
                <select
                  v-model="importForm.config_format"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm transition-colors focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                >
                  <option value="auto">自动检测</option>
                  <option value="ini">INI 格式</option>
                  <option value="toml">TOML 格式</option>
                </select>
              </div>

              <!-- 粘贴配置内容 -->
              <div>
                <label class="mb-1 block text-sm font-medium text-gray-700">
                  配置内容 <span class="text-red-600">*</span>
                </label>
                <textarea
                  v-model="importForm.config_content"
                  rows="10"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-xs text-gray-900 shadow-sm transition-colors focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  placeholder="粘贴 frpc.ini 或 frpc.toml 的内容..."
                />
              </div>

              <!-- 覆盖选项 -->
              <div class="flex items-center gap-2">
                <input
                  id="import-overwrite-paste"
                  v-model="importForm.overwrite"
                  type="checkbox"
                  class="h-4 w-4 rounded border-gray-300 text-orange-500 focus:ring-orange-500"
                />
                <label for="import-overwrite-paste" class="text-sm text-gray-700">
                  覆盖已存在的同名代理
                </label>
              </div>

              <!-- 导入结果 -->
              <div v-if="importResult" class="rounded-lg border p-3 text-sm" :class="importResult.success ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'">
                <p class="font-medium" :class="importResult.success ? 'text-green-800' : 'text-red-800'">{{ importResult.message }}</p>
                <div v-if="importResult.details && importResult.details.length > 0" class="mt-2 max-h-40 overflow-y-auto text-xs">
                  <div
                    v-for="(item, idx) in importResult.details"
                    :key="idx"
                    class="flex items-center gap-1 py-0.5"
                    :class="{
                      'text-green-700': item.action === 'created',
                      'text-blue-700': item.action === 'updated',
                      'text-gray-500': item.action === 'skipped'
                    }"
                  >
                    <span class="font-mono">{{ item.action === 'created' ? '+' : item.action === 'updated' ? '~' : '-' }}</span>
                    <span class="font-mono font-medium">{{ item.name }}</span>
                    <span class="text-gray-400" v-if="item.type">({{ item.type }})</span>
                    <span class="text-gray-400" v-if="item.local_port">:{{ item.local_port }}</span>
                    <span class="text-gray-400" v-if="item.remote_port">->{{ item.remote_port }}</span>
                    <span v-if="item.reason" class="text-gray-400">— {{ item.reason }}</span>
                  </div>
                </div>
              </div>

              <!-- 导入按钮 -->
              <button
                type="button"
                :disabled="importLoading"
                class="w-full rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-orange-600 disabled:opacity-50"
                @click="handleImport"
              >
                <span v-if="importLoading" class="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white/30 border-t-white mr-1" />
                导入
              </button>
            </template>
          </div>
          <div class="flex shrink-0 items-center justify-end border-t border-gray-200 bg-gray-50 px-6 py-3.5">
            <button
              type="button"
              class="inline-flex items-center justify-center rounded-lg bg-gray-200 px-3 py-2 text-sm font-medium text-gray-800 transition-colors hover:bg-gray-300"
              @click="closeImportDialog"
            >
              关闭
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 一键部署（Linux） -->
    <Teleport to="body">
      <div
        v-if="showDeployDialog"
        class="fixed inset-0 z-50 flex items-end justify-center p-2 sm:items-center sm:p-4"
        role="dialog"
        aria-modal="true"
      >
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="closeDeployDialog" />
        <div
          class="relative z-10 flex h-[calc(100dvh-1rem)] max-h-[calc(100dvh-1rem)] w-full max-w-xl flex-col overflow-hidden rounded-t-xl border border-gray-200 bg-white shadow-xl will-change-transform sm:h-auto sm:max-h-[min(92vh,720px)] sm:rounded-xl"
          @click.stop
        >
          <div class="flex shrink-0 items-center justify-between border-b border-gray-200 px-6 py-4">
            <h2 class="text-lg font-semibold text-gray-900">一键部署（Linux）</h2>
            <button
              type="button"
              class="inline-flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800"
              aria-label="关闭"
              @click="closeDeployDialog"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                <path d="M18 6l-12 12" />
                <path d="M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="min-h-0 flex-1 space-y-4 overflow-y-auto px-6 py-4">
            <p class="text-sm text-gray-600">
              在目标 Linux 服务器上执行下方命令。首次安装会自动下载 frpc、拉取本分组配置并注册 <code class="rounded bg-gray-100 px-1 text-xs">systemd</code>（需 <code class="rounded bg-gray-100 px-1 text-xs">sudo</code>）。部署结束后可轮询 frp-agent 校验本分组代理在线数；不通过时会尝试用备份回退二进制与配置（需目标机可访问 frp-agent 且已安装 <code class="rounded bg-gray-100 px-1 text-xs">python3</code>）。
            </p>
            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700">分组</label>
              <input
                v-model="deployForm.group_name"
                type="text"
                readonly
                class="w-full cursor-not-allowed rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-800"
              />
            </div>
            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700">安装目录</label>
              <input
                v-model="deployForm.install_path"
                type="text"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm text-gray-900 shadow-sm transition-colors focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                placeholder="/opt/frp"
              />
            </div>
            <details class="rounded-lg border border-gray-100 bg-gray-50 p-3">
              <summary class="cursor-pointer text-sm font-medium text-gray-800">高级选项</summary>
              <div class="mt-3 flex flex-col gap-3">
                <div class="flex items-center gap-2">
                  <input
                    id="deploy-upgrade"
                    v-model="deployForm.upgrade"
                    type="checkbox"
                    class="h-4 w-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                  />
                  <label for="deploy-upgrade" class="text-sm text-gray-800">
                    升级 frpc 二进制（已安装时下载并替换新版本）
                  </label>
                </div>
                <div class="flex items-center gap-2">
                  <input
                    id="deploy-force-config"
                    v-model="deployForm.force_config"
                    type="checkbox"
                    class="h-4 w-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                  />
                  <label for="deploy-force-config" class="text-sm text-gray-800">
                    覆盖配置文件（强制重新拉取 frpc.toml）
                  </label>
                </div>
                <div class="flex items-center gap-2">
                  <input
                    id="deploy-verify"
                    v-model="deployForm.verify_after_deploy"
                    type="checkbox"
                    class="h-4 w-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                  />
                  <label for="deploy-verify" class="text-sm text-gray-800">
                    部署后校验代理在线（失败则自动回退已备份的 frpc / frpc.toml）
                  </label>
                </div>
              </div>
            </details>
            <div v-if="deployPreview.loading" class="flex items-center gap-2 text-sm text-gray-500">
              <span class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-emerald-500" />
              正在生成部署命令预览…
            </div>
            <div v-else-if="deployPreview.missing_requirements.length" class="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
              <p
                v-for="item in deployPreview.missing_requirements"
                :key="item.code"
                class="text-sm text-amber-800"
              >
                {{ item.message }}
              </p>
            </div>
            <div v-else-if="deployDisplayCommand" class="space-y-2">
              <div v-if="deployPreview.warnings.length" class="rounded-lg border border-amber-100 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                <p v-for="(warning, idx) in deployPreview.warnings" :key="idx">{{ warning }}</p>
              </div>
              <div class="rounded-lg bg-gray-900 p-3">
                <div class="mb-2 flex items-center justify-between">
                  <span class="text-xs font-medium text-gray-400">复制到目标机执行：</span>
                  <button
                    type="button"
                    class="text-xs text-emerald-400 transition-colors hover:text-emerald-300"
                    @click="copyDeployCommand"
                  >
                    {{ deployCopied ? '已复制' : '复制' }}
                  </button>
                </div>
                <pre class="overflow-x-auto whitespace-pre-wrap break-all text-xs text-green-400">{{ deployDisplayCommand }}</pre>
              </div>
            </div>
            <p class="text-xs text-gray-500">
              兼容：仍可使用
              <code class="rounded bg-gray-100 px-1">/quick-install</code>
              、
              <code class="rounded bg-gray-100 px-1">/quick-download</code>
              端点（行为与旧版一致）。
            </p>
          </div>
          <div class="flex shrink-0 items-center justify-end border-t border-gray-200 bg-gray-50 px-6 py-3.5">
            <button
              type="button"
              class="inline-flex items-center justify-center rounded-lg bg-gray-200 px-3 py-2 text-sm font-medium text-gray-800 transition-colors hover:bg-gray-300"
              @click="closeDeployDialog"
            >
              关闭
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 重命名分组对话框 -->
    <Teleport to="body">
      <div
        v-if="showRenameDialog"
        class="fixed inset-0 z-50 flex items-end justify-center p-2 sm:items-center sm:p-4"
        role="dialog"
        aria-modal="true"
      >
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="closeRenameDialog" />
        <div
          class="relative z-10 flex h-[calc(100dvh-1rem)] max-h-[calc(100dvh-1rem)] w-full max-w-md flex-col overflow-hidden rounded-t-xl border border-gray-200 bg-white shadow-xl will-change-transform sm:h-auto sm:max-h-[min(90vh,640px)] sm:rounded-xl"
          @click.stop
        >
          <div class="flex shrink-0 items-center justify-between border-b border-gray-200 px-6 py-4">
            <h2 class="text-lg font-semibold text-gray-900">重命名分组</h2>
            <button
              type="button"
              class="inline-flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800"
              aria-label="关闭"
              @click="closeRenameDialog"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                <path d="M18 6l-12 12" />
                <path d="M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="min-h-0 flex-1 overflow-y-auto px-6 py-4">
            <label class="mb-1 block text-sm font-medium text-gray-700">
              新分组名称 <span class="text-red-600">*</span>
            </label>
            <input
              v-model="renameForm.new_name"
              type="text"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm transition-colors focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              required
            />
          </div>
          <div class="flex shrink-0 flex-wrap items-center justify-end gap-2 border-t border-gray-200 bg-gray-50 px-6 py-4">
            <button
              type="button"
              class="mr-auto inline-flex items-center justify-center rounded-lg bg-gray-200 px-3 py-2 text-sm font-medium text-gray-800 transition-colors hover:bg-gray-300"
              @click="closeRenameDialog"
            >
              取消
            </button>
            <button
              type="button"
              class="inline-flex items-center justify-center rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
              @click="handleRenameGroup"
            >
              保存
            </button>
          </div>
        </div>
      </div>
    </Teleport>
    <!-- 行级更多菜单 -->
    <Teleport to="body">
      <div
        v-if="openMoreGroupName"
        class="group-more-menu fixed z-50 min-w-[160px] rounded-lg border border-gray-200 bg-white py-1 shadow-lg"
        :style="{
          top: `${moreMenuPosition.top}px`,
          right: `${moreMenuPosition.right}px`,
          transform: moreMenuPosition.transform
        }"
        @click.stop
      >
        <button
          type="button"
          class="flex w-full cursor-pointer items-center px-3 py-2 text-left text-sm text-gray-700 transition-colors hover:bg-gray-100 md:hidden"
          @click="runMoreAction('upgrade')"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="mr-2 h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none" />
            <path d="M12 3l0 18" />
            <path d="M8 7l4 -4l4 4" />
            <path d="M8 17l4 4l4 -4" />
          </svg>
          客户端升级
        </button>
        <button
          type="button"
          class="flex w-full cursor-pointer items-center px-3 py-2 text-left text-sm text-gray-700 transition-colors hover:bg-gray-100"
          @click="runMoreAction('config')"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="mr-2 h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none" />
            <path d="M14 3v4a1 1 0 0 0 1 1h4" />
            <path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z" />
          </svg>
          生成配置
        </button>
        <button
          type="button"
          class="flex w-full cursor-pointer items-center px-3 py-2 text-left text-sm text-gray-700 transition-colors hover:bg-gray-100"
          @click="runMoreAction('import')"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="mr-2 h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none" />
            <path d="M4 13h5l2-3h2l2 3h5" />
            <path d="M4 17h5l2-3h2l2 3h5" />
            <path d="M4 9l16 0" />
          </svg>
          导入配置
        </button>
        <button
          type="button"
          class="flex w-full cursor-pointer items-center px-3 py-2 text-left text-sm text-gray-700 transition-colors hover:bg-gray-100"
          @click="runMoreAction('rename')"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="mr-2 h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none" />
            <path d="M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1" />
            <path d="M20.385 6.585a2.1 2.1 0 0 0 -2.97 -2.97l-8.415 8.385v3h3l8.385 -8.415z" />
            <path d="M16 5l3 3" />
          </svg>
          重命名
        </button>
        <div class="my-1 border-t border-gray-100" />
        <button
          type="button"
          class="flex w-full cursor-pointer items-center px-3 py-2 text-left text-sm text-red-600 transition-colors hover:bg-red-50"
          @click="runMoreAction('delete')"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="mr-2 h-4 w-4 shrink-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none" />
            <path d="M4 7l16 0" />
            <path d="M10 11l0 6" />
            <path d="M14 11l0 6" />
            <path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12" />
            <path d="M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3" />
          </svg>
          删除
        </button>
      </div>
    </Teleport>

    <GroupProxiesDialog
      v-model="showGroupProxiesDialog"
      :server-id="props.serverId"
      :group-name="selectedGroupForProxies"
      @success="handleGroupProxiesChanged"
    />

    <GroupClientUpgradeDialog
      v-model="showClientUpgradeDialog"
      :group-name="clientUpgradeGroupName"
      :frps-server-id="props.serverId"
      @upgraded="loadGroupsForCurrentState"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useGroupsStore } from '@/stores/groups'
import { useServersStore } from '@/stores/servers'
import { useModal } from '@/composables/useModal'
import { useApiKeysStore } from '@/stores/apiKeys'
import { groupApi } from '@/api/groups'
import TablePagination from '@/components/TablePagination.vue'
import TableSearch from '@/components/TableSearch.vue'
import GroupProxiesDialog from '@/components/GroupProxiesDialog.vue'
import GroupClientUpgradeDialog from '@/components/GroupClientUpgradeDialog.vue'

const emit = defineEmits(['generate-config'])

const props = defineProps({
  serverId: {
    type: Number,
    required: true
  },
  highlightGroup: {
    type: String,
    default: ''
  }
})

const groupsStore = useGroupsStore()
const serversStore = useServersStore()
const apiKeysStore = useApiKeysStore()

const openMoreGroupName = ref('')
const moreMenuPosition = ref({ top: 0, right: 0, transform: 'translateY(-100%)' })

const currentMoreGroup = computed(() => {
  if (!openMoreGroupName.value) return null
  return groupsStore.groups.find(g => g.group_name === openMoreGroupName.value) || null
})

const groupsMounted = ref(false)

// 加载分组数据
const loadGroups = async (page = 1) => {
  if (!props.serverId) return
  try {
    await groupsStore.loadGroups(props.serverId, {
      page,
      page_size: groupsStore.pagination.page_size,
      search: groupsStore.filters.search || undefined
    })
  } catch (error) {
    console.error('加载分组数据失败:', error)
  }
}

const scrollToHighlightedGroup = async () => {
  if (!props.highlightGroup) return
  await nextTick()
  const row = document.querySelector(`tr[data-group-name="${props.highlightGroup}"]`)
  if (row) {
    row.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

const loadGroupsForCurrentState = async ({ resetPage = false } = {}) => {
  if (!props.serverId) return
  if (props.highlightGroup) {
    groupsStore.setFilters({ search: props.highlightGroup })
    groupsStore.setPagination({ page: 1 })
    await loadGroups(1)
    await scrollToHighlightedGroup()
    return
  }
  if (resetPage) {
    groupsStore.setPagination({ page: 1 })
  }
  await loadGroups(groupsStore.pagination.page)
}

onMounted(async () => {
  document.addEventListener('click', closeMoreOnOutsideClick)
  if (serversStore.servers.length === 0) {
    try {
      await serversStore.loadServers()
    } catch (error) {
      console.error('加载服务器列表失败:', error)
    }
  }
  await loadApiKeys()
  await loadGroupsForCurrentState({ resetPage: true })
  groupsMounted.value = true
})

onUnmounted(() => {
  document.removeEventListener('click', closeMoreOnOutsideClick)
})

watch(() => props.serverId, async (newId, oldId) => {
  if (!groupsMounted.value || !newId || newId === oldId) return
  if (!props.highlightGroup) {
    groupsStore.setFilters({ search: '' })
  }
  await loadGroupsForCurrentState({ resetPage: true })
})

watch(() => serversStore.servers, () => {}, { deep: true })

watch(() => props.highlightGroup, async (groupName, oldGroup) => {
  if (!groupsMounted.value) return
  if (groupName === oldGroup) return
  if (oldGroup === undefined && groupName) return
  if (!groupName && oldGroup) {
    groupsStore.setFilters({ search: '' })
  }
  await loadGroupsForCurrentState({ resetPage: true })
})

const showCreateDialog = ref(false)
const showRenameDialog = ref(false)
const showImportDialog = ref(false)
const showDeployDialog = ref(false)
const showClientUpgradeDialog = ref(false)
const clientUpgradeGroupName = ref('')
const deployCopied = ref(false)
const showGroupProxiesDialog = ref(false)
const importLoading = ref(false)
const importResult = ref(null)
const importCopied = ref(false)
const analyzeLoading = ref(false)
const analyzeSummary = ref(null)
const deployPreview = reactive({
  loading: false,
  command: '',
  script_url: '',
  warnings: [],
  missing_requirements: [],
  effective_options: null
})
const importPreview = reactive({
  loading: false,
  command: '',
  script_url: '',
  warnings: [],
  missing_requirements: [],
  effective_options: null
})
const currentGroup = ref(null)
const selectedGroupForProxies = ref('')
const selectedApiKeyId = computed({
  get: () => apiKeysStore.selectedKeyId,
  set: (id) => apiKeysStore.setDefaultKey(id)
})

// 存储选中的 API Key 完整密钥
const selectedApiKeyFullKey = ref(null)

// 更新完整密钥的函数 - 先从 localStorage 读取，如果没有则从后端接口获取
const updateFullKey = async () => {
  if (selectedApiKeyId.value) {
    // 先尝试从 localStorage 读取
    const id = selectedApiKeyId.value
    const fullKey = await apiKeysStore.resolveFullKey(id)
    if (fullKey) {
      // 找到了有效的完整密钥
      selectedApiKeyFullKey.value = fullKey
    } else {
      // 没找到或无效，清空
      selectedApiKeyFullKey.value = null
    }
  } else {
    selectedApiKeyFullKey.value = null
  }
}

// 监听 selectedApiKeyId 变化，更新完整密钥
watch(selectedApiKeyId, () => {
  updateFullKey()
}, { immediate: true })

// 获取当前服务器名称或ID
const currentServerName = computed(() => {
  if (!props.serverId) {
    return 'server_name'
  }
  // 从 stores 获取服务器信息
  const server = serversStore.servers.find(s => s.id === props.serverId)
  if (server && server.name) {
    return encodeURIComponent(server.name)
  }
  // 如果没有找到，返回服务器ID
  return String(props.serverId)
})

// 加载 API Key 列表
const loadApiKeys = async () => {
  if (apiKeysStore.selectedKeyId === null) {
    apiKeysStore.selectedKeyId = apiKeysStore.getStoredDefaultId()
  }
  await apiKeysStore.loadKeys()
  if (selectedApiKeyId.value) {
    await updateFullKey()
  }
}

const createForm = reactive({
  group_name: ''
})

const renameForm = reactive({
  new_name: ''
})

const importForm = reactive({
  mode: 'command',
  group_name: '',
  config_content: '',
  config_path: '/opt/frp',
  config_format: 'auto',
  overwrite: true
})

const deployForm = reactive({
  group_name: '',
  install_path: '/opt/frp',
  platform: 'linux_amd64',
  upgrade: false,
  force_config: false,
  verify_after_deploy: true
})

const deployCurlCommand = computed(() => {
  if (!deployForm.group_name?.trim() || !selectedApiKeyFullKey.value) {
    return ''
  }
  const path = groupApi.getDeployScriptUrl({
    group_name: deployForm.group_name.trim(),
    server_name: currentServerName.value,
    api_key: selectedApiKeyFullKey.value,
    install_path: deployForm.install_path?.trim() || '/opt/frp',
    platform: deployForm.platform,
    upgrade: deployForm.upgrade,
    force_config: deployForm.force_config,
    verify: deployForm.verify_after_deploy
  })
  return `curl -sL "${window.location.origin}${path}" | sudo bash`
})

const deployDisplayCommand = computed(() => {
  if (deployPreview.loading) return ''
  if (deployPreview.command) return deployPreview.command
  if (showDeployDialog.value && deployPreview.missing_requirements.length) return ''
  return deployCurlCommand.value
})

const importDisplayCommand = computed(() => {
  if (importPreview.loading) return ''
  if (importPreview.command) return importPreview.command
  if (showImportDialog.value && importPreview.missing_requirements.length) return ''
  return importCurlCommand.value
})

const importCurlCommand = computed(() => {
  if (importForm.mode !== 'command') return ''
  if (!importForm.group_name?.trim() || !selectedApiKeyFullKey.value) return ''
  const path = groupApi.getImportScriptUrl({
    frps_server_id: props.serverId,
    group_name: importForm.group_name.trim(),
    config_path: importForm.config_path.trim() || '/opt/frp',
    config_format: importForm.config_format,
    overwrite: importForm.overwrite,
    api_key: selectedApiKeyFullKey.value
  })
  return `curl -sL "${window.location.origin}${path}" | bash`
})

const resetDeployPreview = () => {
  deployPreview.loading = false
  deployPreview.command = ''
  deployPreview.script_url = ''
  deployPreview.warnings = []
  deployPreview.missing_requirements = []
  deployPreview.effective_options = null
}

const resetImportPreview = () => {
  importPreview.loading = false
  importPreview.command = ''
  importPreview.script_url = ''
  importPreview.warnings = []
  importPreview.missing_requirements = []
  importPreview.effective_options = null
}

const getCurrentServerRawName = () => {
  const server = serversStore.servers.find(s => s.id === props.serverId)
  return server?.name || ''
}

const refreshDeployPreview = async () => {
  if (!showDeployDialog.value || !deployForm.group_name?.trim()) {
    resetDeployPreview()
    return
  }
  deployPreview.loading = true
  try {
    const result = await groupApi.previewDeploy(deployForm.group_name.trim(), {
      frps_server_id: props.serverId,
      server_name: getCurrentServerRawName(),
      install_path: deployForm.install_path?.trim() || '/opt/frp',
      platform: deployForm.platform,
      upgrade: deployForm.upgrade,
      force_config: deployForm.force_config,
      verify: deployForm.verify_after_deploy,
      api_key: selectedApiKeyFullKey.value || undefined
    })
    deployPreview.command = result.command || ''
    deployPreview.script_url = result.script_url || ''
    deployPreview.warnings = result.warnings || []
    deployPreview.missing_requirements = result.missing_requirements || []
    deployPreview.effective_options = result.effective_options || null
  } catch {
    resetDeployPreview()
  } finally {
    deployPreview.loading = false
  }
}

const refreshImportPreview = async () => {
  if (!showImportDialog.value || importForm.mode !== 'command' || !importForm.group_name?.trim()) {
    resetImportPreview()
    return
  }
  importPreview.loading = true
  try {
    const result = await groupApi.previewImport({
      frps_server_id: props.serverId,
      group_name: importForm.group_name.trim(),
      config_path: importForm.config_path.trim() || '/opt/frp',
      config_format: importForm.config_format,
      overwrite: importForm.overwrite,
      api_key: selectedApiKeyFullKey.value || undefined
    })
    importPreview.command = result.command || ''
    importPreview.script_url = result.script_url || ''
    importPreview.warnings = result.warnings || []
    importPreview.missing_requirements = result.missing_requirements || []
    importPreview.effective_options = result.effective_options || null
  } catch {
    resetImportPreview()
  } finally {
    importPreview.loading = false
  }
}

watch(
  () => [
    showDeployDialog.value,
    deployForm.install_path,
    deployForm.upgrade,
    deployForm.force_config,
    deployForm.verify_after_deploy,
    selectedApiKeyFullKey.value
  ],
  () => {
    if (showDeployDialog.value) {
      refreshDeployPreview()
    }
  }
)

watch(
  () => [
    showImportDialog.value,
    importForm.mode,
    importForm.group_name,
    importForm.config_path,
    importForm.config_format,
    importForm.overwrite,
    selectedApiKeyFullKey.value
  ],
  () => {
    if (showImportDialog.value && importForm.mode === 'command') {
      refreshImportPreview()
    }
  }
)

const importCommandDetail = computed(() => {
  if (importForm.mode !== 'command' || !importForm.group_name?.trim()) return ''
  return [
    `分组名称：${importForm.group_name.trim()}`,
    `扫描路径：${importForm.config_path.trim() || '/opt/frp'}（目录内有配置则只用该目录；目录内没有时才扫当前目录）`,
    `配置格式：${importForm.config_format}`,
    `覆盖同名代理：${importForm.overwrite ? '是（默认）' : '否'}`,
    '',
    '执行后脚本会：拉取 bash → 按规则读取本地配置（目录有则用目录，否则用当前目录）→ POST 导入。'
  ].join('\n')
})

const handleCreateGroup = async () => {
  if (!createForm.group_name) {
    alert('请输入分组名称')
    return
  }

  const groupName = createForm.group_name.trim()

  try {
    await groupsStore.createGroup({
      group_name: groupName,
      frps_server_id: props.serverId
    })

    let defaultsMessage = ''
    try {
      const defaultsResult = await groupApi.generateDefaults(groupName, props.serverId)
      defaultsMessage = `\n\n已生成标准代理：新建 ${defaultsResult.created ?? 0} 个，跳过 ${defaultsResult.skipped ?? 0} 个`
    } catch (defaultsError) {
      defaultsMessage = `\n\n标准代理生成失败: ${defaultsError.response?.data?.detail || defaultsError.message}`
    }

    alert(`创建分组成功${defaultsMessage}`)
    showCreateDialog.value = false
    createForm.group_name = ''
    // 刷新分组列表，重置到第一页
    groupsStore.setPagination({ page: 1 })
    await loadGroups(1)
  } catch (error) {
    alert('创建分组失败: ' + error.message)
  }
}

const editGroup = (group) => {
  currentGroup.value = group
  renameForm.new_name = group.group_name
  showRenameDialog.value = true
}

const handleRenameGroup = async () => {
  if (!renameForm.new_name || !currentGroup.value) {
    alert('请输入新分组名称')
    return
  }

  try {
    await groupsStore.updateGroup(
      currentGroup.value.group_name,
      renameForm.new_name,
      props.serverId
    )
    alert('重命名成功')
    showRenameDialog.value = false
    // 刷新分组列表，保持当前页
    await loadGroups(groupsStore.pagination.page)
  } catch (error) {
    alert('重命名失败: ' + error.message)
  }
}

const deleteGroup = async (group) => {
  // 确保 serverId 存在且有效
  if (!props.serverId) {
    alert('服务器ID无效，无法删除分组')
    return
  }

  const reassignGroup = prompt(
    `确定要删除分组 "${group.group_name}" 吗？该分组下有 ${group.total_count} 个代理。\n请输入目标分组名称（留空则移动到"其他"分组）：`
  )

  if (reassignGroup === null) {
    return
  }

  try {
    await groupsStore.deleteGroup(group.group_name, reassignGroup || '', props.serverId)
    alert('删除成功')
    // 刷新分组列表，保持当前页
    await loadGroups(groupsStore.pagination.page)
  } catch (error) {
    alert('删除失败: ' + error.message)
  }
}

const handleAutoAnalyze = async () => {
  if (!confirm('将从代理名称中自动分析分组。\n\n注意：仅对分组为"其他"或空的代理进行分析，不会覆盖已有的分组。\n\n是否继续？')) {
    return
  }

  analyzeLoading.value = true
  analyzeSummary.value = null
  try {
    const result = await groupsStore.autoAnalyzeGroups(props.serverId)
    if (result?.analysis) {
      analyzeSummary.value = result.analysis
    }
    groupsStore.setPagination({ page: 1 })
    await loadGroups(1)
  } catch (error) {
    analyzeSummary.value = {
      total: 0,
      updated: 0,
      skipped: 0,
      unchanged: 0,
      error: error.message || '自动分析失败'
    }
  } finally {
    analyzeLoading.value = false
  }
}

const viewGroupProxies = (groupName) => {
  selectedGroupForProxies.value = groupName
  showGroupProxiesDialog.value = true
}

const generateGroupConfig = (groupName) => {
  emit('generate-config', groupName)
}

const handleGroupImportConfig = async (groupName) => {
  importForm.mode = 'command'
  importForm.group_name = groupName
  importForm.config_path = '/opt/frp'
  importForm.overwrite = true
  importResult.value = null
  importCopied.value = false
  analyzeSummary.value = null
  resetImportPreview()
  await updateFullKey()
  showImportDialog.value = true
}

const openImportOrganizeDialog = async () => {
  importForm.mode = 'command'
  importForm.group_name = ''
  importForm.config_content = ''
  importForm.config_path = '/opt/frp'
  importForm.config_format = 'auto'
  importForm.overwrite = true
  importResult.value = null
  importCopied.value = false
  analyzeSummary.value = null
  resetImportPreview()
  await updateFullKey()
  showImportDialog.value = true
}

const closeMoreMenu = () => {
  openMoreGroupName.value = ''
}

const toggleGroupMore = (groupName, event) => {
  if (openMoreGroupName.value === groupName) {
    closeMoreMenu()
    return
  }
  openMoreGroupName.value = groupName
  nextTick(() => {
    const button = event.currentTarget
    const rect = button.getBoundingClientRect()
    const menuHeight = 220
    const openAbove = rect.top - 8 >= menuHeight
    moreMenuPosition.value = {
      top: openAbove ? rect.top - 8 : rect.bottom + 8,
      right: Math.max(8, window.innerWidth - rect.right),
      transform: openAbove ? 'translateY(-100%)' : 'none'
    }
  })
}

const runMoreAction = (action) => {
  const group = currentMoreGroup.value
  if (!group) return
  closeMoreMenu()
  switch (action) {
    case 'config':
      generateGroupConfig(group.group_name)
      break
    case 'import':
      handleGroupImportConfig(group.group_name)
      break
    case 'upgrade':
      openClientUpgradeDialog(group)
      break
    case 'rename':
      editGroup(group)
      break
    case 'delete':
      deleteGroup(group)
      break
    default:
      break
  }
}

const closeMoreOnOutsideClick = (e) => {
  if (
    openMoreGroupName.value
    && !e.target.closest('[aria-label="更多操作"]')
    && !e.target.closest('.group-more-menu')
  ) {
    closeMoreMenu()
  }
}

const handleGroupProxiesChanged = async () => {
  groupsStore.setPagination({ page: 1 })
  await loadGroups(1)
}

const closeCreateDialog = () => {
  showCreateDialog.value = false
  createForm.group_name = ''
}

const closeRenameDialog = () => {
  showRenameDialog.value = false
  renameForm.new_name = ''
}

const closeImportDialog = () => {
  showImportDialog.value = false
  importForm.mode = 'command'
  importForm.group_name = ''
  importForm.config_content = ''
  importForm.config_path = '/opt/frp'
  importForm.config_format = 'auto'
  importForm.overwrite = true
  importResult.value = null
  importCopied.value = false
  analyzeSummary.value = null
  resetImportPreview()
}

const closeDeployDialog = () => {
  showDeployDialog.value = false
  deployForm.group_name = ''
  deployForm.install_path = '/opt/frp'
  deployForm.platform = 'linux_amd64'
  deployForm.upgrade = false
  deployForm.force_config = false
  deployForm.verify_after_deploy = true
  deployCopied.value = false
  resetDeployPreview()
}

const openClientUpgradeDialog = (group) => {
  clientUpgradeGroupName.value = group.group_name
  showClientUpgradeDialog.value = true
}

const openDeployDialog = async (group) => {
  deployForm.group_name = group.group_name
  deployForm.install_path = '/opt/frp'
  deployForm.platform = 'linux_amd64'
  deployForm.upgrade = false
  deployForm.force_config = false
  deployForm.verify_after_deploy = true
  deployCopied.value = false
  resetDeployPreview()
  await updateFullKey()
  showDeployDialog.value = true
}

const copyDeployCommand = async () => {
  const cmd = deployDisplayCommand.value
  if (!cmd) return
  try {
    await navigator.clipboard.writeText(cmd)
    deployCopied.value = true
    setTimeout(() => { deployCopied.value = false }, 2000)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = cmd
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    deployCopied.value = true
    setTimeout(() => { deployCopied.value = false }, 2000)
  }
}

const handleImport = async () => {
  if (!importForm.group_name.trim()) {
    alert('请输入分组名称')
    return
  }

  if (!importForm.config_content.trim()) {
    alert('请输入配置内容')
    return
  }

  importLoading.value = true
  importResult.value = null

  try {
    const result = await groupsStore.importConfig({
      frps_server_id: props.serverId,
      group_name: importForm.group_name.trim(),
      config_content: importForm.config_content,
      config_format: importForm.config_format,
      overwrite: importForm.overwrite
    })
    importResult.value = result
    if (result.success) {
      groupsStore.setPagination({ page: 1 })
      await loadGroups(1)
    }
  } catch (error) {
    importResult.value = {
      success: false,
      message: '导入失败: ' + (error.response?.data?.detail || error.message)
    }
  } finally {
    importLoading.value = false
  }
}

const copyImportCommand = async () => {
  const cmd = importDisplayCommand.value
  if (!cmd) return
  try {
    await navigator.clipboard.writeText(cmd)
    importCopied.value = true
    setTimeout(() => { importCopied.value = false }, 2000)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = cmd
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    importCopied.value = true
    setTimeout(() => { importCopied.value = false }, 2000)
  }
}

// 使用统一的模态框功能
useModal(showCreateDialog, closeCreateDialog)
useModal(showRenameDialog, closeRenameDialog)
useModal(showImportDialog, closeImportDialog)
useModal(showDeployDialog, closeDeployDialog)

// 分页处理
const handlePageChange = (newPage) => {
  loadGroups(newPage)
}

const handlePageSizeChange = (newPageSize) => {
  groupsStore.setPagination({ page_size: newPageSize, page: 1 })
  loadGroups(1)
}

// 搜索处理
const handleSearch = () => {
  groupsStore.setPagination({ page: 1 })
  loadGroups(1)
}
</script>
