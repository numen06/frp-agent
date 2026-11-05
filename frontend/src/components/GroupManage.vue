<template>
  <div>
    <div
      v-if="groupsStore.error"
      role="alert"
      class="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-destructive/30 p-3 text-sm text-destructive"
    >
      {{ groupsStore.error
      }}<Button variant="outline" size="sm" @click="loadGroups()"
        >重试读取分组</Button
      >
    </div>
    <p
      v-if="groupNotice"
      role="status"
      class="mb-3 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800"
    >
      {{ groupNotice }}
    </p>
    <div
      class="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-2"
    >
      <p class="mb-0 text-sm text-gray-500">
        管理所有代理分组，支持重命名和快速生成配置
      </p>
      <div class="flex w-full flex-wrap gap-2 sm:w-auto sm:justify-end">
        <Button
          type="button"
          class="flex-1 sm:flex-none"
          @click="showCreateDialog = true"
          variant="default"
          size="sm"
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
          新增分组 </Button
        ><Button
          type="button"
          class="flex-1 sm:flex-none"
          @click="openImportOrganizeDialog"
          variant="outline"
          size="sm"
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
            <path d="M4 13h5l2-3h2l2 3h5" />
            <path d="M4 17h5l2-3h2l2 3h5" />
            <path d="M4 9l16 0" />
          </svg>
          导入/整理
        </Button>
      </div>
    </div>
    <Card
      ><div class="p-3 sm:p-6">
        <div class="mb-3">
          <div
            class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
          >
            <div class="w-full min-w-0 sm:max-w-[250px]">
              <SearchField
                v-model="groupsStore.filters.search"
                placeholder="搜索分组名称..."
                :debounce="300"
                @search="handleSearch"
              />
            </div>
          </div>
        </div>
        <div class="hidden overflow-x-auto md:block">
          <Table class="w-full text-left"
            ><TableHeader
              ><TableRow
                ><TableHead>分组名称</TableHead><TableHead>代理数量</TableHead
                ><TableHead>在线</TableHead><TableHead>离线</TableHead
                ><TableHead
                  class="w-[1%] whitespace-nowrap sticky right-0 bg-muted"
                  >操作</TableHead
                ></TableRow
              ></TableHeader
            ><TableBody
              ><TableRow v-if="groupsStore.loading"
                ><TableCell colspan="5" class="text-center"
                  ><span
                    class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600 align-middle"
                    role="status"
                    aria-label="加载中"
                  /><span class="ml-2 align-middle text-gray-600"
                    >加载中...</span
                  ></TableCell
                ></TableRow
              ><TableRow
                v-else-if="
                  groupsStore.groups.length === 0 && !groupsStore.error
                "
                ><TableCell colspan="5" class="text-center"
                  >暂无分组，请先创建分组或导入配置</TableCell
                ></TableRow
              ><TableRow
                v-else
                v-for="group in groupsStore.groups"
                :key="group.group_name"
                :data-group-name="group.group_name"
                :class="{
                  'bg-amber-50': props.highlightGroup === group.group_name,
                }"
                ><TableCell
                  ><strong
                    class="font-semibold"
                    :class="
                      props.highlightGroup === group.group_name
                        ? 'text-amber-600'
                        : 'text-blue-600'
                    "
                    >{{ group.group_name }}</strong
                  ></TableCell
                ><TableCell>{{ group.total_count }}</TableCell
                ><TableCell
                  ><span
                    class="inline-flex rounded-md bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800"
                    >{{ group.online_count }}</span
                  ></TableCell
                ><TableCell
                  ><span
                    class="inline-flex rounded-md bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800"
                    >{{ group.offline_count }}</span
                  ></TableCell
                ><TableCell
                  ><div class="flex items-center justify-end gap-1">
                    <Button
                      type="button"
                      title="查看代理"
                      aria-label="查看代理"
                      @click="viewGroupProxies(group.group_name)"
                      variant="ghost"
                      size="icon-sm"
                      tooltip="查看代理"
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
                        <path d="M10 10m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0" />
                        <path d="M21 21l-6 -6" /></svg></Button
                    ><ActionMenu
                      label="更多操作"
                      :items="[
                        { action: 'deploy', label: '一键部署' },
                        { action: 'config', label: '生成配置' },
                        { action: 'import', label: '导入配置' },
                        { action: 'upgrade', label: '客户端升级' },
                        { action: 'rename', label: '重命名' },
                        { separator: true, label: '分隔' },
                        { action: 'delete', label: '删除分组', danger: true },
                      ]"
                      @select="(action) => runMoreAction(action, group)"
                    /></div></TableCell></TableRow></TableBody
          ></Table>
        </div>
        <div class="md:hidden">
          <div
            v-if="groupsStore.loading"
            class="py-4 text-center text-sm text-gray-600"
          >
            <span
              class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600 align-middle"
              role="status"
              aria-label="加载中"
            /><span class="ml-2 align-middle">加载中...</span>
          </div>
          <p
            v-else-if="groupsStore.groups.length === 0 && !groupsStore.error"
            class="py-8 text-center text-sm text-gray-500"
          >
            暂无分组，请先创建分组或导入配置
          </p>
          <ul v-else class="grid gap-3">
            <li
              v-for="group in groupsStore.groups"
              :key="group.group_name"
              :data-group-name="group.group_name"
              class="flex h-52 min-w-0 flex-col gap-3 rounded-xl border bg-card p-4"
              :class="{
                'border-primary bg-primary/5':
                  props.highlightGroup === group.group_name,
              }"
            >
              <h3
                class="line-clamp-2 min-h-10 min-w-0 break-all text-sm font-semibold leading-5"
                :title="group.group_name"
              >
                {{ group.group_name }}
              </h3>
              <dl class="grid grid-cols-3 gap-3 text-xs">
                <div class="min-w-0">
                  <dt class="text-muted-foreground">代理总数</dt>
                  <dd class="mt-1 truncate text-lg font-semibold">
                    {{ group.total_count }}
                  </dd>
                </div>
                <div class="min-w-0">
                  <dt class="text-muted-foreground">在线</dt>
                  <dd
                    class="mt-1 truncate text-lg font-semibold text-emerald-700"
                  >
                    {{ group.online_count }}
                  </dd>
                </div>
                <div class="min-w-0">
                  <dt class="text-muted-foreground">离线</dt>
                  <dd
                    class="mt-1 truncate text-lg font-semibold"
                    :class="
                      group.offline_count
                        ? 'text-destructive'
                        : 'text-muted-foreground'
                    "
                  >
                    {{ group.offline_count }}
                  </dd>
                </div>
              </dl>
              <div class="mt-auto flex items-center gap-2 border-t pt-3">
                <Button
                  variant="outline"
                  size="sm"
                  class="flex-1"
                  aria-label="查看代理"
                  @click="viewGroupProxies(group.group_name)"
                  >查看代理</Button
                >
                <ActionMenu
                  text="更多"
                  variant="outline"
                  label="更多操作"
                  :items="[
                    { action: 'deploy', label: '一键部署' },
                    { action: 'config', label: '生成配置' },
                    { action: 'import', label: '导入配置' },
                    { action: 'upgrade', label: '客户端升级' },
                    { action: 'rename', label: '重命名' },
                    { separator: true, label: '分隔' },
                    { action: 'delete', label: '删除分组', danger: true },
                  ]"
                  @select="(action) => runMoreAction(action, group)"
                />
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
        </div></div></Card
    ><!-- 创建分组对话框 --><Dialog
      v-if="showCreateDialog"
      :open="true"
      @update:open="
        (open) => {
          if (!open) {
            closeCreateDialog();
          }
        }
      "
      ><DialogContent class="sm:max-w-md" :aria-describedby="undefined"
        ><DialogHeader><DialogTitle>新增分组</DialogTitle></DialogHeader>
        <div
          data-slot="dialog-body"
          class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
        >
          <label class="mb-1 block text-sm font-medium text-gray-700">
            分组名称 <span class="text-red-600">*</span> </label
          ><Input
            v-model="createForm.group_name"
            type="text"
            class="w-full transition-colors"
            placeholder="例如: dlyy"
            required
          ></Input>
        </div>
        <div class="px-6 pb-4">
          <label class="flex items-center gap-2 text-sm"
            ><Checkbox
              v-model="createForm.create_defaults"
              :disabled="creating"
            ></Checkbox
            >生成 SSH / HTTP / Docker 标准代理并打开配置</label
          >
          <p v-if="createError" role="alert" class="mt-2 text-sm text-red-600">
            {{ createError }}
          </p>
        </div>
        <DialogFooter
          ><Button
            type="button"
            class="mr-auto inline-flex items-center justify-center text-sm font-medium transition-colors"
            @click="closeCreateDialog"
            variant="ghost"
            size="default"
          >
            取消 </Button
          ><Button
            type="button"
            @click="handleCreateGroup"
            :disabled="creating"
            variant="default"
            size="default"
            >{{ creating ? "创建中…" : "创建并使用" }}</Button
          ></DialogFooter
        ></DialogContent
      ></Dialog
    ><!-- 导入/整理对话框 --><Dialog
      v-if="showImportDialog"
      :open="true"
      @update:open="
        (open) => {
          if (!open) {
            closeImportDialog();
          }
        }
      "
      ><DialogContent class="sm:max-w-xl" :aria-describedby="undefined"
        ><DialogHeader><DialogTitle>导入/整理</DialogTitle></DialogHeader>
        <div
          data-slot="dialog-body"
          class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
        >
          <!-- 自动分析分组 -->
          <div class="rounded-lg border border-green-200 bg-green-50 p-4">
            <p class="text-sm font-medium text-green-900">自动分析分组</p>
            <p class="mt-1 text-xs text-green-800">
              从代理名称自动识别分组，仅对分组为「其他」或空的代理进行分析，不会覆盖已有分组。
            </p>
            <Button
              type="button"
              :disabled="analyzeLoading"
              class="mt-3"
              @click="handleAutoAnalyze"
              variant="outline"
              size="default"
              ><span
                v-if="analyzeLoading"
                class="mr-1 inline-block h-3 w-3 animate-spin rounded-full border-2 border-white/30 border-t-white"
              />
              开始自动分析
            </Button>
            <div
              v-if="analyzeSummary"
              class="mt-3 rounded-lg border border-green-300 bg-white p-3 text-xs text-green-900"
            >
              <p v-if="analyzeSummary.error" class="font-medium text-red-700">
                {{ analyzeSummary.error }}
              </p>
              <template v-else>
                <p class="font-medium">分析摘要</p>
                <p class="mt-1">
                  总代理数 {{ analyzeSummary.total }}，更新
                  {{ analyzeSummary.updated }}，跳过
                  {{ analyzeSummary.skipped }}，未变化
                  {{ analyzeSummary.unchanged }}
                </p>
                <p v-if="analyzeSummary.new_groups?.length" class="mt-1">
                  新识别分组：{{ analyzeSummary.new_groups.join("、") }}
                </p>
              </template>
            </div>
          </div>
          <div class="border-t border-gray-100 pt-1">
            <p class="mb-3 text-sm font-medium text-gray-800">配置导入</p>
          </div>
          <!-- 导入方式选择 -->
          <div>
            <label class="mb-2 block text-sm font-medium text-gray-700"
              >导入方式</label
            ><ToggleGroup
              type="single"
              :model-value="importForm.mode"
              @update:model-value="
                (value) => {
                  if (value) importForm.mode = value;
                }
              "
              variant="outline"
              class="flex w-full flex-wrap justify-start"
              ><ToggleGroupItem :value="'command'">
                生成命令（推荐） </ToggleGroupItem
              ><ToggleGroupItem :value="'paste'">
                粘贴配置内容
              </ToggleGroupItem></ToggleGroup
            >
          </div>
          <!-- 分组名称 -->
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">
              分组名称 <span class="text-red-600">*</span> </label
            ><Input
              v-model="importForm.group_name"
              type="text"
              class="w-full transition-colors"
              placeholder="例如: dlyy"
              required
            ></Input>
          </div>
          <!-- 生成命令模式 --><template v-if="importForm.mode === 'command'">
            <!-- 扫描路径 -->
            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700">
                目标服务器扫描路径 </label
              ><Input
                v-model="importForm.config_path"
                type="text"
                class="w-full font-mono transition-colors"
                placeholder="/opt/frp"
              ></Input>
              <p class="mt-1 text-xs text-gray-400">
                指定<strong>文件</strong>则只读该文件；指定<strong>目录</strong>且其中有
                .ini/.toml
                时<strong>只使用该目录</strong>，不与当前目录合并。仅当指定目录下没有这些文件时，才退回到<strong>执行命令时的当前目录</strong>扫描。
              </p>
            </div>
            <!-- 覆盖选项 -->
            <div class="flex items-center gap-2">
              <Checkbox
                id="import-overwrite-cmd"
                v-model="importForm.overwrite"
                class="w-4 text-orange-500"
                aria-label="import-overwrite-cmd"
              ></Checkbox
              ><label for="import-overwrite-cmd" class="text-sm text-gray-700">
                覆盖已存在的同名代理（默认开启）
              </label>
            </div>
            <!-- 自动生成命令展示 -->
            <div
              v-if="importPreview.loading"
              class="flex items-center gap-2 text-sm text-gray-500"
            >
              <span
                class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-orange-500"
              />
              正在生成导入命令预览…
            </div>
            <div
              v-else-if="importPreview.missing_requirements.length"
              class="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-3"
            >
              <p
                v-for="item in importPreview.missing_requirements"
                :key="item.code"
                class="text-sm text-amber-800"
              >
                {{ item.message }}
              </p>
            </div>
            <div v-else-if="importDisplayCommand" class="space-y-2">
              <div
                v-if="importPreview.warnings.length"
                class="rounded-lg border border-amber-100 bg-amber-50 px-3 py-2 text-xs text-amber-800"
              >
                <p v-for="(warning, idx) in importPreview.warnings" :key="idx">
                  {{ warning }}
                </p>
              </div>
              <div class="rounded-lg bg-gray-900 p-3">
                <div class="mb-2 flex items-center justify-between">
                  <span class="text-xs font-medium text-gray-400"
                    >复制到目标服务器执行（一条命令即可）：</span
                  ><Button
                    type="button"
                    class="text-xs text-orange-400 transition-colors hover:text-orange-300"
                    @click="copyImportCommand"
                    variant="ghost"
                    size="default"
                    >复制</Button
                  >
                </div>
                <pre
                  class="overflow-x-auto whitespace-pre-wrap break-all text-xs text-green-400"
                  >{{ importDisplayCommand }}</pre>
              </div>
              <details
                v-if="importCommandDetail"
                class="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-600"
              >
                <summary
                  class="cursor-pointer font-medium text-gray-700 hover:text-gray-900"
                >
                  详情说明
                </summary>
                <p
                  class="mt-2 whitespace-pre-wrap border-t border-gray-200 pt-2 text-gray-500"
                >
                  {{ importCommandDetail }}
                </p>
              </details>
            </div>
            <p
              v-else-if="!importForm.group_name.trim()"
              class="text-sm text-gray-500"
            >
              填写分组名称后将自动生成导入命令。
            </p> </template
          ><!-- 粘贴导入模式 --><template v-if="importForm.mode === 'paste'">
            <!-- 配置格式 -->
            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700"
                >配置格式</label
              ><Select v-model="importForm.config_format"
                ><SelectTrigger
                  class="w-full transition-colors"
                  aria-label="配置格式"
                  ><SelectValue
                    placeholder="请选择"
                  ></SelectValue></SelectTrigger
                ><SelectContent
                  ><SelectItem value="auto">自动检测</SelectItem
                  ><SelectItem value="ini">INI 格式</SelectItem
                  ><SelectItem value="toml"
                    >TOML 格式</SelectItem
                  ></SelectContent
                ></Select
              >
            </div>
            <!-- 粘贴配置内容 -->
            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700">
                配置内容 <span class="text-red-600">*</span> </label
              ><Textarea
                v-model="importForm.config_content"
                rows="10"
                class="w-full font-mono transition-colors"
                placeholder="粘贴 frpc.ini 或 frpc.toml 的内容..."
              ></Textarea>
            </div>
            <!-- 覆盖选项 -->
            <div class="flex items-center gap-2">
              <Checkbox
                id="import-overwrite-paste"
                v-model="importForm.overwrite"
                class="w-4 text-orange-500"
                aria-label="import-overwrite-paste"
              ></Checkbox
              ><label
                for="import-overwrite-paste"
                class="text-sm text-gray-700"
              >
                覆盖已存在的同名代理
              </label>
            </div>
            <!-- 导入结果 -->
            <div
              v-if="importResult"
              class="rounded-lg border p-3 text-sm"
              :class="
                importResult.success
                  ? 'border-green-200 bg-green-50'
                  : 'border-red-200 bg-red-50'
              "
            >
              <p
                class="font-medium"
                :class="
                  importResult.success ? 'text-green-800' : 'text-red-800'
                "
              >
                {{ importResult.message }}
              </p>
              <div
                v-if="importResult.details && importResult.details.length > 0"
                class="mt-2 max-h-40 overflow-y-auto text-xs"
              >
                <div
                  v-for="(item, idx) in importDetails.items.value"
                  :key="idx"
                  class="flex items-center gap-1 py-0.5"
                  :class="{
                    'text-green-700': item.action === 'created',
                    'text-blue-700': item.action === 'updated',
                    'text-gray-500': item.action === 'skipped',
                  }"
                >
                  <span class="font-mono">{{
                    item.action === "created"
                      ? "+"
                      : item.action === "updated"
                        ? "~"
                        : "-"
                  }}</span
                  ><span class="font-mono font-medium">{{ item.name }}</span
                  ><span class="text-gray-400" v-if="item.type"
                    >({{ item.type }})</span
                  ><span class="text-gray-400" v-if="item.local_port"
                    >:{{ item.local_port }}</span
                  ><span class="text-gray-400" v-if="item.remote_port"
                    >->{{ item.remote_port }}</span
                  ><span v-if="item.reason" class="text-gray-400"
                    >— {{ item.reason }}</span
                  >
                </div>
              </div>
            </div>
            <div v-if="importDetails.pagination.total" class="py-3">
              <TablePagination
                :total="importDetails.pagination.total"
                :page="importDetails.pagination.page"
                :page-size="importDetails.pagination.page_size"
                @page-change="importDetails.load"
                @page-size-change="importDetails.resize"
              />
            </div>
            <!-- 导入按钮 --><Button
              type="button"
              :disabled="importLoading"
              class="w-full"
              @click="handleImport"
              variant="default"
              size="default"
              ><span
                v-if="importLoading"
                class="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white/30 border-t-white mr-1"
              />
              导入
            </Button>
          </template>
        </div>
        <DialogFooter
          ><Button
            type="button"
            class="inline-flex items-center justify-center text-sm font-medium transition-colors"
            @click="closeImportDialog"
            variant="ghost"
            size="default"
          >
            关闭
          </Button></DialogFooter
        ></DialogContent
      ></Dialog
    ><!-- 一键部署（Linux） --><Dialog
      v-if="showDeployDialog"
      :open="true"
      @update:open="
        (open) => {
          if (!open) {
            closeDeployDialog();
          }
        }
      "
      ><DialogContent class="sm:max-w-xl" :aria-describedby="undefined"
        ><DialogHeader
          ><DialogTitle>一键部署（Linux）</DialogTitle></DialogHeader
        >
        <div
          data-slot="dialog-body"
          class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
        >
          <p class="text-sm text-gray-600">
            在目标 Linux 服务器上执行下方命令。首次安装会自动下载
            frpc、拉取本分组配置并注册
            <code class="rounded bg-gray-100 px-1 text-xs">systemd</code>（需
            <code class="rounded bg-gray-100 px-1 text-xs">sudo</code
            >）。部署结束后可轮询 frp-agent
            校验本分组代理在线数；不通过时会尝试用备份回退二进制与配置（需目标机可访问
            frp-agent 且已安装
            <code class="rounded bg-gray-100 px-1 text-xs">python3</code>）。
          </p>
          <div
            class="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800"
          >
            如果你是通过当前 frpc 隧道 SSH 到目标机执行部署，重启 frpc 会中断
            SSH。请让命令在目标机本地完整执行；关闭部署后校验时，断联后无法可靠证明代理已恢复。
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >分组</label
            ><Input
              v-model="deployForm.group_name"
              type="text"
              readonly
              class="w-full cursor-not-allowed"
            ></Input>
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >安装目录</label
            ><Input
              v-model="deployForm.install_path"
              type="text"
              class="w-full font-mono transition-colors"
              placeholder="/opt/frp"
            ></Input>
          </div>
          <details class="rounded-lg border border-gray-100 bg-gray-50 p-3">
            <summary class="cursor-pointer text-sm font-medium text-gray-800">
              高级选项
            </summary>
            <div class="mt-3 flex flex-col gap-3">
              <div class="flex items-center gap-2">
                <Checkbox
                  id="deploy-upgrade"
                  v-model="deployForm.upgrade"
                  class="w-4 text-emerald-600"
                  aria-label="deploy-upgrade"
                ></Checkbox
                ><label for="deploy-upgrade" class="text-sm text-gray-800">
                  升级 frpc 二进制（已安装时下载并替换新版本）
                </label>
              </div>
              <div class="flex items-center gap-2">
                <Checkbox
                  id="deploy-force-config"
                  v-model="deployForm.force_config"
                  class="w-4 text-emerald-600"
                  aria-label="deploy-force-config"
                ></Checkbox
                ><label for="deploy-force-config" class="text-sm text-gray-800">
                  覆盖配置文件（强制重新拉取 frpc.toml）
                </label>
              </div>
              <div class="flex items-center gap-2">
                <Checkbox
                  id="deploy-verify"
                  v-model="deployForm.verify_after_deploy"
                  class="w-4 text-emerald-600"
                  aria-label="deploy-verify"
                ></Checkbox
                ><label for="deploy-verify" class="text-sm text-gray-800">
                  部署后校验代理在线（失败则自动回退已备份的 frpc / frpc.toml）
                </label>
              </div>
            </div>
          </details>
          <div
            v-if="deployPreview.loading"
            class="flex items-center gap-2 text-sm text-gray-500"
          >
            <span
              class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-emerald-500"
            />
            正在生成部署命令预览…
          </div>
          <div
            v-else-if="deployPreview.missing_requirements.length"
            class="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-3"
          >
            <p
              v-for="item in deployPreview.missing_requirements"
              :key="item.code"
              class="text-sm text-amber-800"
            >
              {{ item.message }}
            </p>
          </div>
          <div v-else-if="deployDisplayCommand" class="space-y-2">
            <div
              v-if="deployPreview.warnings.length"
              class="rounded-lg border border-amber-100 bg-amber-50 px-3 py-2 text-xs text-amber-800"
            >
              <p v-for="(warning, idx) in deployPreview.warnings" :key="idx">
                {{ warning }}
              </p>
            </div>
            <div class="rounded-lg bg-gray-900 p-3">
              <div class="mb-2 flex items-center justify-between">
                <span class="text-xs font-medium text-gray-400"
                  >复制到目标机执行：</span
                ><Button
                  type="button"
                  class="text-xs text-emerald-400 transition-colors hover:text-emerald-300"
                  @click="copyDeployCommand"
                  variant="ghost"
                  size="default"
                  >复制</Button
                >
              </div>
              <pre
                class="overflow-x-auto whitespace-pre-wrap break-all text-xs text-green-400"
                >{{ deployDisplayCommand }}</pre>
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
        <DialogFooter
          ><Button
            type="button"
            class="inline-flex items-center justify-center text-sm font-medium transition-colors"
            @click="closeDeployDialog"
            variant="ghost"
            size="default"
          >
            关闭
          </Button></DialogFooter
        ></DialogContent
      ></Dialog
    ><!-- 重命名分组对话框 --><Dialog
      v-if="showRenameDialog"
      :open="true"
      @update:open="
        (open) => {
          if (!open) {
            closeRenameDialog();
          }
        }
      "
      ><DialogContent class="sm:max-w-md" :aria-describedby="undefined"
        ><DialogHeader><DialogTitle>重命名分组</DialogTitle></DialogHeader>
        <div
          data-slot="dialog-body"
          class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
        >
          <label class="mb-1 block text-sm font-medium text-gray-700">
            新分组名称 <span class="text-red-600">*</span> </label
          ><Input
            v-model="renameForm.new_name"
            type="text"
            class="w-full transition-colors"
            required
          ></Input>
        </div>
        <DialogFooter
          ><Button
            type="button"
            class="mr-auto inline-flex items-center justify-center text-sm font-medium transition-colors"
            @click="closeRenameDialog"
            variant="ghost"
            size="default"
          >
            取消 </Button
          ><Button
            type="button"
            @click="handleRenameGroup"
            variant="default"
            size="default"
          >
            保存
          </Button></DialogFooter
        ></DialogContent
      ></Dialog
    ><!-- 行级更多菜单 --><Dialog
      v-if="deleteOpen"
      :open="true"
      @update:open="
        (open) => {
          if (!deleting) {
            deleteOpen = open;
          }
        }
      "
      ><DialogContent
        class="sm:max-w-xl"
        :aria-describedby="undefined"
        :show-close-button="!deleting"
        @escape-key-down="
          (e) => {
            if (deleting) e.preventDefault();
          }
        "
        @interact-outside="
          (e) => {
            if (deleting) e.preventDefault();
          }
        "
        ><DialogHeader><DialogTitle>删除分组</DialogTitle></DialogHeader>
        <div
          data-slot="dialog-body"
          class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
        >
          <p
            v-if="!deletePreview && !deleteError"
            class="text-sm text-gray-500"
          >
            正在确认分组数据…
          </p>
          <div v-if="deletePreview" class="space-y-3 text-sm">
            <p class="break-all">
              分组：<strong>{{ deletingGroup.group_name }}</strong>
            </p>
            <p>
              包含 {{ deletePreview.proxy_count }} 条代理配置，将释放
              {{ deletePreview.port_count }} 个端口。
            </p>
            <p class="text-red-600">
              确认后将删除整个分组、代理配置及关联扫描状态，不会移动到“其他”分组。已运行的
              frpc 客户端仍需单独停止或更新配置。
            </p>
            <label v-if="deleteStage === 2" class="block"
              >二次确认：输入分组名称
              <strong class="break-all">{{ deletingGroup.group_name }}</strong
              ><Input
                v-model="deleteName"
                :disabled="deleting"
                aria-label="确认删除的分组名称"
                class="mt-2 w-full"
                autocomplete="off"
              ></Input
            ></label>
          </div>
          <p v-if="deleteError" role="alert" class="mt-3 text-sm text-red-600">
            {{ deleteError }}
          </p>
        </div>
        <DialogFooter
          ><Button
            type="button"
            :disabled="deleting"
            @click="deleteOpen = false"
            variant="outline"
            size="default"
            >取消</Button
          ><Button
            type="button"
            :disabled="
              deleting ||
              !deletePreview ||
              (deleteStage === 2 && deleteName !== deletingGroup.group_name)
            "
            @click="confirmDeleteGroup"
            variant="destructive"
            size="default"
            >{{
              deleting
                ? "删除中…"
                : deletePreview?.proxy_count && deleteStage === 1
                  ? "继续删除"
                  : "确认全部删除"
            }}</Button
          ></DialogFooter
        ></DialogContent
      ></Dialog
    ><GroupProxiesDialog
      v-model="showGroupProxiesDialog"
      :server-id="props.serverId"
      :group-name="selectedGroupForProxies"
      @success="handleGroupProxiesChanged"
    /><GroupClientUpgradeDialog
      v-model="showClientUpgradeDialog"
      :group-name="clientUpgradeGroupName"
      :frps-server-id="props.serverId"
      @upgraded="loadGroupsForCurrentState"
    />
  </div>
</template>

<script setup>
import { copyText } from "@/composables/useClipboard";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import ActionMenu from "@/components/ActionMenu.vue";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Card } from "@/components/ui/card";
import { Table } from "@/components/ui/table";
import { TableBody } from "@/components/ui/table";
import { TableCell } from "@/components/ui/table";
import { TableHeader } from "@/components/ui/table";
import { TableRow } from "@/components/ui/table";
import { TableHead } from "@/components/ui/table";
import { notify, confirmAction } from "@/composables/useFeedback";
import { ref, reactive, computed, onMounted, watch, nextTick } from "vue";
import { useGroupsStore } from "@/stores/groups";
import { useServersStore } from "@/stores/servers";
import { useApiKeysStore } from "@/stores/apiKeys";
import { groupApi } from "@/api/groups";
import TablePagination from "@/components/TablePagination.vue";
import { useLocalPagination } from "@/composables/useLocalPagination";
import SearchField from "@/components/SearchField.vue";
import GroupProxiesDialog from "@/components/GroupProxiesDialog.vue";
import GroupClientUpgradeDialog from "@/components/GroupClientUpgradeDialog.vue";

const emit = defineEmits(["generate-config"]);

const props = defineProps({
  serverId: {
    type: Number,
    required: true,
  },
  highlightGroup: {
    type: String,
    default: "",
  },
});

const groupsStore = useGroupsStore();
const serversStore = useServersStore();
const apiKeysStore = useApiKeysStore();

const groupsMounted = ref(false);

// 加载分组数据
const loadGroups = async (page = 1) => {
  if (!props.serverId) return;
  try {
    await groupsStore.loadGroups(props.serverId, {
      page,
      page_size: groupsStore.pagination.page_size,
      search: groupsStore.filters.search || undefined,
    });
  } catch (error) {
    console.error("加载分组数据失败:", error);
  }
};

const scrollToHighlightedGroup = async () => {
  if (!props.highlightGroup) return;
  await nextTick();
  const row = document.querySelector(
    `tr[data-group-name="${props.highlightGroup}"]`,
  );
  if (row) {
    row.scrollIntoView({ behavior: "smooth", block: "center" });
  }
};

const loadGroupsForCurrentState = async ({ resetPage = false } = {}) => {
  if (!props.serverId) return;
  if (props.highlightGroup) {
    groupsStore.setFilters({ search: props.highlightGroup });
    groupsStore.setPagination({ page: 1 });
    await loadGroups(1);
    await scrollToHighlightedGroup();
    return;
  }
  if (resetPage) {
    groupsStore.setPagination({ page: 1 });
  }
  await loadGroups(groupsStore.pagination.page);
};

watch(
  () => props.serverId,
  async (newId, oldId) => {
    if (!groupsMounted.value || !newId || newId === oldId) return;
    if (!props.highlightGroup) {
      groupsStore.setFilters({ search: "" });
    }
    await loadGroupsForCurrentState({ resetPage: true });
  },
);

onMounted(async () => {
  if (serversStore.servers.length === 0) {
    try {
      await serversStore.loadServers();
    } catch (error) {
      console.error("加载服务器列表失败:", error);
    }
  }
  await loadApiKeys();
  await loadGroupsForCurrentState({ resetPage: true });
  groupsMounted.value = true;
});

watch(
  () => props.highlightGroup,
  async (groupName, oldGroup) => {
    if (!groupsMounted.value) return;
    if (groupName === oldGroup) return;
    if (oldGroup === undefined && groupName) return;
    if (!groupName && oldGroup) {
      groupsStore.setFilters({ search: "" });
    }
    await loadGroupsForCurrentState({ resetPage: true });
  },
);

const showCreateDialog = ref(false);
const showRenameDialog = ref(false);
const showImportDialog = ref(false);
const showDeployDialog = ref(false);
const showClientUpgradeDialog = ref(false);
const clientUpgradeGroupName = ref("");
const showGroupProxiesDialog = ref(false);
const importLoading = ref(false);
const importResult = ref(null);
const importDetails = useLocalPagination(
  computed(() => importResult.value?.details || []),
);
const analyzeLoading = ref(false);
const analyzeSummary = ref(null);
const deployPreview = reactive({
  loading: false,
  command: "",
  script_url: "",
  warnings: [],
  missing_requirements: [],
  effective_options: null,
});
const importPreview = reactive({
  loading: false,
  command: "",
  script_url: "",
  warnings: [],
  missing_requirements: [],
  effective_options: null,
});
const currentGroup = ref(null);
const selectedGroupForProxies = ref("");
const selectedApiKeyId = computed({
  get: () => apiKeysStore.selectedKeyId,
  set: (id) => apiKeysStore.setDefaultKey(id),
});

// 存储选中的 API Key 完整密钥
const selectedApiKeyFullKey = ref(null);

// 更新完整密钥的函数 - 先从 localStorage 读取，如果没有则从后端接口获取
const updateFullKey = async () => {
  if (selectedApiKeyId.value) {
    // 先尝试从 localStorage 读取
    const id = selectedApiKeyId.value;
    const fullKey = await apiKeysStore.resolveFullKey(id);
    if (fullKey) {
      // 找到了有效的完整密钥
      selectedApiKeyFullKey.value = fullKey;
    } else {
      // 没找到或无效，清空
      selectedApiKeyFullKey.value = null;
    }
  } else {
    selectedApiKeyFullKey.value = null;
  }
};

// 监听 selectedApiKeyId 变化，更新完整密钥
watch(
  selectedApiKeyId,
  () => {
    updateFullKey();
  },
  { immediate: true },
);

// 获取当前服务器名称或ID
const currentServerName = computed(() => {
  if (!props.serverId) {
    return "server_name";
  }
  // 从 stores 获取服务器信息
  const server =
    serversStore.servers.find((s) => s.id === props.serverId) ||
    serversStore.currentServer;
  if (server && server.name) {
    return encodeURIComponent(server.name);
  }
  // 如果没有找到，返回服务器ID
  return String(props.serverId);
});

// 加载 API Key 列表
const loadApiKeys = async () => {
  if (apiKeysStore.selectedKeyId === null) {
    apiKeysStore.selectedKeyId = apiKeysStore.getStoredDefaultId();
  }
  await apiKeysStore.loadKeys();
  if (selectedApiKeyId.value) {
    await updateFullKey();
  }
};

const createForm = reactive({ group_name: "", create_defaults: true });
const creating = ref(false),
  createError = ref(""),
  groupNotice = ref("");
const deleteOpen = ref(false),
  deleting = ref(false),
  deleteStage = ref(1),
  deleteName = ref(""),
  deletePreview = ref(null),
  deleteError = ref("");
const deletingGroup = ref(null);

const renameForm = reactive({
  new_name: "",
});

const importForm = reactive({
  mode: "command",
  group_name: "",
  config_content: "",
  config_path: "/opt/frp",
  config_format: "auto",
  overwrite: true,
});

const deployForm = reactive({
  group_name: "",
  install_path: "/opt/frp",
  platform: "linux_amd64",
  upgrade: false,
  force_config: false,
  verify_after_deploy: true,
});

const deployCurlCommand = computed(() => {
  if (!deployForm.group_name?.trim() || !selectedApiKeyFullKey.value) {
    return "";
  }
  const path = groupApi.getDeployScriptUrl({
    group_name: deployForm.group_name.trim(),
    server_name: currentServerName.value,
    api_key: selectedApiKeyFullKey.value,
    install_path: deployForm.install_path?.trim() || "/opt/frp",
    platform: deployForm.platform,
    upgrade: deployForm.upgrade,
    force_config: deployForm.force_config,
    verify: deployForm.verify_after_deploy,
  });
  return `curl -sL "${window.location.origin}${path}" | sudo bash`;
});

const deployDisplayCommand = computed(() => {
  if (deployPreview.loading) return "";
  if (deployPreview.command) return deployPreview.command;
  if (showDeployDialog.value && deployPreview.missing_requirements.length)
    return "";
  return deployCurlCommand.value;
});

const importDisplayCommand = computed(() => {
  if (importPreview.loading) return "";
  if (importPreview.command) return importPreview.command;
  if (showImportDialog.value && importPreview.missing_requirements.length)
    return "";
  return importCurlCommand.value;
});

const importCurlCommand = computed(() => {
  if (importForm.mode !== "command") return "";
  if (!importForm.group_name?.trim() || !selectedApiKeyFullKey.value) return "";
  const path = groupApi.getImportScriptUrl({
    frps_server_id: props.serverId,
    group_name: importForm.group_name.trim(),
    config_path: importForm.config_path.trim() || "/opt/frp",
    config_format: importForm.config_format,
    overwrite: importForm.overwrite,
    api_key: selectedApiKeyFullKey.value,
  });
  return `curl -sL "${window.location.origin}${path}" | bash`;
});

const resetDeployPreview = () => {
  deployPreview.loading = false;
  deployPreview.command = "";
  deployPreview.script_url = "";
  deployPreview.warnings = [];
  deployPreview.missing_requirements = [];
  deployPreview.effective_options = null;
};

const resetImportPreview = () => {
  importPreview.loading = false;
  importPreview.command = "";
  importPreview.script_url = "";
  importPreview.warnings = [];
  importPreview.missing_requirements = [];
  importPreview.effective_options = null;
};

const getCurrentServerRawName = () => {
  const server =
    serversStore.servers.find((s) => s.id === props.serverId) ||
    serversStore.currentServer;
  return server?.name || "";
};

const refreshDeployPreview = async () => {
  if (!showDeployDialog.value || !deployForm.group_name?.trim()) {
    resetDeployPreview();
    return;
  }
  deployPreview.loading = true;
  try {
    const result = await groupApi.previewDeploy(deployForm.group_name.trim(), {
      frps_server_id: props.serverId,
      server_name: getCurrentServerRawName(),
      install_path: deployForm.install_path?.trim() || "/opt/frp",
      platform: deployForm.platform,
      upgrade: deployForm.upgrade,
      force_config: deployForm.force_config,
      verify: deployForm.verify_after_deploy,
      api_key: selectedApiKeyFullKey.value || undefined,
    });
    deployPreview.command = result.command || "";
    deployPreview.script_url = result.script_url || "";
    deployPreview.warnings = result.warnings || [];
    deployPreview.missing_requirements = result.missing_requirements || [];
    deployPreview.effective_options = result.effective_options || null;
  } catch {
    resetDeployPreview();
  } finally {
    deployPreview.loading = false;
  }
};

const refreshImportPreview = async () => {
  if (
    !showImportDialog.value ||
    importForm.mode !== "command" ||
    !importForm.group_name?.trim()
  ) {
    resetImportPreview();
    return;
  }
  importPreview.loading = true;
  try {
    const result = await groupApi.previewImport({
      frps_server_id: props.serverId,
      group_name: importForm.group_name.trim(),
      config_path: importForm.config_path.trim() || "/opt/frp",
      config_format: importForm.config_format,
      overwrite: importForm.overwrite,
      api_key: selectedApiKeyFullKey.value || undefined,
    });
    importPreview.command = result.command || "";
    importPreview.script_url = result.script_url || "";
    importPreview.warnings = result.warnings || [];
    importPreview.missing_requirements = result.missing_requirements || [];
    importPreview.effective_options = result.effective_options || null;
  } catch {
    resetImportPreview();
  } finally {
    importPreview.loading = false;
  }
};

watch(
  () => [
    showDeployDialog.value,
    deployForm.install_path,
    deployForm.upgrade,
    deployForm.force_config,
    deployForm.verify_after_deploy,
    selectedApiKeyFullKey.value,
  ],
  () => {
    if (showDeployDialog.value) {
      refreshDeployPreview();
    }
  },
);

watch(
  () => [
    showImportDialog.value,
    importForm.mode,
    importForm.group_name,
    importForm.config_path,
    importForm.config_format,
    importForm.overwrite,
    selectedApiKeyFullKey.value,
  ],
  () => {
    if (showImportDialog.value && importForm.mode === "command") {
      refreshImportPreview();
    }
  },
);

const importCommandDetail = computed(() => {
  if (importForm.mode !== "command" || !importForm.group_name?.trim())
    return "";
  return [
    `分组名称：${importForm.group_name.trim()}`,
    `扫描路径：${importForm.config_path.trim() || "/opt/frp"}（目录内有配置则只用该目录；目录内没有时才扫当前目录）`,
    `配置格式：${importForm.config_format}`,
    `覆盖同名代理：${importForm.overwrite ? "是（默认）" : "否"}`,
    "",
    "执行后脚本会：拉取 bash → 按规则读取本地配置（目录有则用目录，否则用当前目录）→ POST 导入。",
  ].join("\n");
});

const handleCreateGroup = async () => {
  const groupName = createForm.group_name.trim();
  if (!groupName || creating.value) {
    createError.value = "请输入分组名称";
    return;
  }
  creating.value = true;
  createError.value = "";
  try {
    const result = await groupsStore.createGroup({
      group_name: groupName,
      frps_server_id: props.serverId,
      create_defaults: createForm.create_defaults,
    });
    showCreateDialog.value = false;
    createForm.group_name = "";
    groupsStore.setFilters({ search: groupName });
    groupsStore.setPagination({ page: 1 });
    await loadGroups(1);
    groupNotice.value = `分组 ${groupName} 创建成功，已生成 ${result.created_proxies || 0} 条标准代理配置。`;
    if (createForm.create_defaults) emit("generate-config", groupName);
    else viewGroupProxies(groupName);
  } catch (error) {
    createError.value = `创建失败：${error.message}`;
  } finally {
    creating.value = false;
  }
};

const editGroup = (group) => {
  currentGroup.value = group;
  renameForm.new_name = group.group_name;
  showRenameDialog.value = true;
};

const handleRenameGroup = async () => {
  if (!renameForm.new_name || !currentGroup.value) {
    notify("请输入新分组名称");
    return;
  }

  try {
    await groupsStore.updateGroup(
      currentGroup.value.group_name,
      renameForm.new_name,
      props.serverId,
    );
    notify("重命名成功");
    showRenameDialog.value = false;
    // 刷新分组列表，保持当前页
    await loadGroups(groupsStore.pagination.page);
  } catch (error) {
    notify("重命名失败: " + error.message);
  }
};

const deleteGroup = async (group) => {
  if (!props.serverId) return;
  deletingGroup.value = group;
  deleteOpen.value = true;
  deleteStage.value = 1;
  deleteName.value = "";
  deleteError.value = "";
  deletePreview.value = null;
  try {
    deletePreview.value = await groupApi.previewDelete(
      group.group_name,
      props.serverId,
    );
  } catch (e) {
    deleteError.value = e.message;
  }
};
const confirmDeleteGroup = async () => {
  const group = deletingGroup.value;
  if (!group || !deletePreview.value || deleting.value) return;
  if (deletePreview.value.proxy_count && deleteStage.value === 1) {
    deleteStage.value = 2;
    return;
  }
  if (deletePreview.value.proxy_count && deleteName.value !== group.group_name)
    return;
  deleting.value = true;
  deleteError.value = "";
  try {
    const result = await groupsStore.deleteGroup(
      group.group_name,
      {
        delete_proxies: true,
        expected_proxy_count: deletePreview.value.proxy_count,
      },
      props.serverId,
    );
    deleteOpen.value = false;
    groupNotice.value = result.message;
    groupsStore.setFilters({ search: "" });
    const lastPage = Math.max(
      1,
      Math.ceil(
        (groupsStore.pagination.total - 1) / groupsStore.pagination.page_size,
      ),
    );
    await loadGroups(Math.min(groupsStore.pagination.page, lastPage));
  } catch (e) {
    deleteError.value = e.message;
    deleteStage.value = 1;
    deleteName.value = "";
    try {
      deletePreview.value = await groupApi.previewDelete(
        group.group_name,
        props.serverId,
      );
    } catch {
      deletePreview.value = null;
    }
  } finally {
    deleting.value = false;
  }
};

const handleAutoAnalyze = async () => {
  if (
    !(await confirmAction(
      '将从代理名称中自动分析分组。\n\n注意：仅对分组为"其他"或空的代理进行分析，不会覆盖已有的分组。\n\n是否继续？',
    ))
  ) {
    return;
  }

  analyzeLoading.value = true;
  analyzeSummary.value = null;
  try {
    const result = await groupsStore.autoAnalyzeGroups(props.serverId);
    if (result?.analysis) {
      analyzeSummary.value = result.analysis;
    }
    groupsStore.setPagination({ page: 1 });
    await loadGroups(1);
  } catch (error) {
    analyzeSummary.value = {
      total: 0,
      updated: 0,
      skipped: 0,
      unchanged: 0,
      error: error.message || "自动分析失败",
    };
  } finally {
    analyzeLoading.value = false;
  }
};

const viewGroupProxies = (groupName) => {
  selectedGroupForProxies.value = groupName;
  showGroupProxiesDialog.value = true;
};

const generateGroupConfig = (groupName) => {
  emit("generate-config", groupName);
};

const handleGroupImportConfig = async (groupName) => {
  importForm.mode = "command";
  importForm.group_name = groupName;
  importForm.config_path = "/opt/frp";
  importForm.overwrite = true;
  importResult.value = null;
  analyzeSummary.value = null;
  resetImportPreview();
  await updateFullKey();
  showImportDialog.value = true;
};

const openImportOrganizeDialog = async () => {
  importForm.mode = "command";
  importForm.group_name = "";
  importForm.config_content = "";
  importForm.config_path = "/opt/frp";
  importForm.config_format = "auto";
  importForm.overwrite = true;
  importResult.value = null;
  analyzeSummary.value = null;
  resetImportPreview();
  await updateFullKey();
  showImportDialog.value = true;
};

const runMoreAction = (action, group) => {
  switch (action) {
    case "deploy":
      openDeployDialog(group);
      break;
    case "config":
      generateGroupConfig(group.group_name);
      break;
    case "import":
      handleGroupImportConfig(group.group_name);
      break;
    case "upgrade":
      openClientUpgradeDialog(group);
      break;
    case "rename":
      editGroup(group);
      break;
    case "delete":
      deleteGroup(group);
      break;
    default:
      break;
  }
};

const handleGroupProxiesChanged = async () => {
  groupsStore.setPagination({ page: 1 });
  await loadGroups(1);
};

const closeCreateDialog = () => {
  if (creating.value) return;
  createError.value = "";
  showCreateDialog.value = false;
  createForm.group_name = "";
};

const closeRenameDialog = () => {
  showRenameDialog.value = false;
  renameForm.new_name = "";
};

const closeImportDialog = () => {
  showImportDialog.value = false;
  importForm.mode = "command";
  importForm.group_name = "";
  importForm.config_content = "";
  importForm.config_path = "/opt/frp";
  importForm.config_format = "auto";
  importForm.overwrite = true;
  importResult.value = null;
  analyzeSummary.value = null;
  resetImportPreview();
};

const closeDeployDialog = () => {
  showDeployDialog.value = false;
  deployForm.group_name = "";
  deployForm.install_path = "/opt/frp";
  deployForm.platform = "linux_amd64";
  deployForm.upgrade = false;
  deployForm.force_config = false;
  deployForm.verify_after_deploy = true;
  resetDeployPreview();
};

const openClientUpgradeDialog = (group) => {
  clientUpgradeGroupName.value = group.group_name;
  showClientUpgradeDialog.value = true;
};

const openDeployDialog = async (group) => {
  deployForm.group_name = group.group_name;
  deployForm.install_path = "/opt/frp";
  deployForm.platform = "linux_amd64";
  deployForm.upgrade = false;
  deployForm.force_config = false;
  deployForm.verify_after_deploy = true;
  resetDeployPreview();
  await updateFullKey();
  showDeployDialog.value = true;
};

const copyDeployCommand = async () => {
  if (deployDisplayCommand.value) await copyText(deployDisplayCommand.value);
};

const handleImport = async () => {
  if (!importForm.group_name.trim()) {
    notify("请输入分组名称");
    return;
  }

  if (!importForm.config_content.trim()) {
    notify("请输入配置内容");
    return;
  }

  importLoading.value = true;
  importResult.value = null;

  try {
    const result = await groupsStore.importConfig({
      frps_server_id: props.serverId,
      group_name: importForm.group_name.trim(),
      config_content: importForm.config_content,
      config_format: importForm.config_format,
      overwrite: importForm.overwrite,
    });
    importResult.value = result;
    if (result.success) {
      groupsStore.setPagination({ page: 1 });
      await loadGroups(1);
    }
  } catch (error) {
    importResult.value = {
      success: false,
      message: "导入失败: " + (error.response?.data?.detail || error.message),
    };
  } finally {
    importLoading.value = false;
  }
};

const copyImportCommand = async () => {
  if (importDisplayCommand.value) await copyText(importDisplayCommand.value);
};

// 分页处理
const handlePageChange = (newPage) => {
  loadGroups(newPage);
};

const handlePageSizeChange = (newPageSize) => {
  groupsStore.setPagination({ page_size: newPageSize, page: 1 });
  loadGroups(1);
};

// 搜索处理
const handleSearch = () => {
  groupsStore.setPagination({ page: 1 });
  loadGroups(1);
};
</script>
