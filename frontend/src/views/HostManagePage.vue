<template>
  <Tabs v-model="tab" class="gap-0"
    ><div class="space-y-4">
      <PageHeader
        title="连接服务、授权与审计"
        description="分别管理每台主机的协议连接、凭据、服务授权与访问记录。"
      >
        <Button
          v-if="context.is_admin"
          variant="outline"
          @click="discoveryOpen = true"
          >代理导入</Button
        >
        <Button
          v-if="context.is_admin"
          @click="openAiHostPrompt"
          type="button"
          variant="outline"
          size="default"
          >AI / curl 添加提示词</Button
        ><Button
          v-if="context.is_admin"
          @click="openHostEditor()"
          type="button"
          variant="default"
          size="default"
          >添加连接服务</Button
        > </PageHeader
      ><Card class="gap-0 py-0 px-2"
        ><TabsList
          variant="line"
          aria-label="主机管理分类"
          class="grid h-auto w-full grid-cols-2 min-[380px]:grid-cols-3 md:flex md:flex-wrap"
          ><TabsTrigger
            v-for="item in tabs"
            :key="item.key"
            :value="item.key"
            >{{ item.label }}</TabsTrigger
          ></TabsList
        ></Card
      ><TabsContent :value="tab" force-mount
        ><Card v-if="tab === 'hosts'"
          ><form
            class="grid grid-cols-2 items-center gap-3 border-b p-4 sm:p-5 lg:flex lg:flex-wrap"
            @submit.prevent="loadHostPage(1)"
          >
            <SearchField
              v-model="hostList.search.value"
              placeholder="搜索连接名称、地址或标签"
              class="col-span-2 min-w-0 lg:min-w-[12rem] lg:flex-1"
              label="搜索主机"
              @search="loadHostPage(1)"
            />
            <Select
              v-model="hostFilters.type"
              @update:model-value="loadHostPage(1)"
            >
              <SelectTrigger aria-label="主机类型" class="w-full lg:w-36"
                ><SelectValue placeholder="全部类型"
              /></SelectTrigger>
              <SelectContent
                ><SelectItem value="all">全部类型</SelectItem
                ><SelectItem value="ssh">SSH</SelectItem
                ><SelectItem value="vnc">VNC / macOS</SelectItem
                ><SelectItem value="rdp">RDP</SelectItem
                ><SelectItem value="docker">Docker</SelectItem></SelectContent
              >
            </Select>
            <Select
              v-model="hostFilters.status"
              @update:model-value="loadHostPage(1)"
            >
              <SelectTrigger aria-label="主机状态" class="w-full lg:w-44"
                ><SelectValue placeholder="全部状态"
              /></SelectTrigger>
              <SelectContent
                ><SelectItem value="all">全部状态</SelectItem
                ><SelectItem value="online">最近检查通过</SelectItem
                ><SelectItem value="abnormal">检查异常</SelectItem
                ><SelectItem value="unknown">未检查</SelectItem
                ><SelectItem value="pending">未激活</SelectItem
                ><SelectItem value="disabled">已禁用</SelectItem></SelectContent
              >
            </Select>
            <div class="col-span-2 flex gap-2">
              <Button
                type="submit"
                variant="outline"
                class="flex-1 lg:flex-none"
                >查询</Button
              ><Button
                v-if="hasHostFilters"
                type="button"
                variant="ghost"
                class="flex-1 lg:flex-none"
                @click="clearHostFilters"
                >清除筛选</Button
              >
            </div>
          </form>
          <p
            v-if="hostList.error.value"
            role="alert"
            class="p-4 text-sm text-red-600"
          >
            {{ hostList.error.value }}
          </p>
          <div
            v-if="loading || (hostList.loading.value && !hosts.length)"
            class="p-10 text-center text-sm text-gray-500"
          >
            加载中...
          </div>
          <div
            v-else-if="hosts.length === 0 && !hostList.error.value"
            class="p-10 text-center text-sm text-gray-500"
          >
            {{
              hasHostFilters
                ? "没有符合筛选条件的主机，请调整或清除筛选。"
                : "暂无可访问的主机资源"
            }}
          </div>
          <div v-else class="grid gap-3 p-3 md:grid-cols-2 xl:grid-cols-3">
            <article
              v-for="host in hosts"
              :key="host.id"
              class="flex h-[19rem] min-w-0 flex-col gap-2 rounded-xl border bg-card p-4"
            >
              <div class="flex min-w-0 items-center justify-between gap-2">
                <h2 class="min-w-0 truncate font-semibold" :title="host.name">
                  <router-link
                    :to="hostDetailsLocation(host)"
                    class="hover:text-primary hover:underline"
                    >{{ host.name }}</router-link
                  >
                </h2>
                <div class="ml-auto flex shrink-0 items-center gap-1">
                  <Button
                    as-child
                    variant="ghost"
                    size="icon-sm"
                    aria-label="查看主机日志"
                  >
                    <router-link :to="hostDetailsLocation(host, 'logs')"
                      ><FileClock class="size-4"
                    /></router-link>
                  </Button>
                  <ActionMenu
                    label="主机操作"
                    :items="[
                      { action: 'audit', label: '流量与审计' },
                      ...(host.can_manage
                        ? [
                            { action: 'edit', label: '编辑连接' },
                            { action: 'clone', label: '克隆连接' },
                            { separator: true, label: '分隔' },
                            {
                              action: 'delete',
                              label: '删除连接服务',
                              danger: true,
                              disabled: deletingHostId === host.id,
                            },
                          ]
                        : []),
                    ]"
                    @select="(action) => runHostAction(action, host)"
                  />
                </div>
              </div>
              <div class="min-w-0">
                <div class="flex items-center gap-2 text-xs">
                  <span
                    class="shrink-0 rounded-md bg-muted px-2 py-1 font-medium"
                    >{{
                      { ssh: "SSH", docker: "Docker", rdp: "RDP", vnc: "VNC" }[
                        host.host_type
                      ]
                    }}</span
                  >
                  <span
                    class="truncate rounded-md px-2 py-1"
                    :class="
                      !host.is_active
                        ? 'bg-muted text-muted-foreground'
                        : host.last_status === 'online'
                          ? 'bg-emerald-50 text-emerald-700'
                          : ['offline', 'error'].includes(host.last_status)
                            ? 'bg-destructive/10 text-destructive'
                            : 'bg-muted text-muted-foreground'
                    "
                    >{{
                      host.activation_pending
                        ? "未激活"
                        : !host.is_active
                          ? "已禁用"
                          : host.last_status === "online"
                            ? host.host_type === "rdp"
                              ? "上次校验通过"
                              : "连接正常"
                            : ["offline", "error"].includes(host.last_status)
                              ? "连接异常"
                              : "未检测"
                    }}</span
                  >
                </div>
                <p
                  class="mt-1 truncate font-mono text-xs text-muted-foreground"
                  :title="hostAddress(host)"
                >
                  {{ hostAddress(host) }}
                </p>
              </div>
              <dl class="space-y-1.5 text-xs">
                <div class="flex min-w-0 gap-3">
                  <dt class="w-12 shrink-0 text-muted-foreground">凭据</dt>
                  <dd class="min-w-0 flex-1 truncate">
                    {{ host.credential_name || "未配置"
                    }}{{
                      host.credential_username
                        ? ` / ${host.credential_username}`
                        : ""
                    }}
                  </dd>
                </div>
                <div class="flex min-w-0 gap-3">
                  <dt class="w-12 shrink-0 text-muted-foreground">系统版本</dt>
                  <dd
                    class="min-w-0 flex-1 truncate"
                    :title="host.version_info"
                  >
                    {{ host.version_info || "未采集" }}
                  </dd>
                </div>
                <div class="flex min-w-0 gap-3">
                  <dt class="w-12 shrink-0 text-muted-foreground">最近状态</dt>
                  <dd
                    class="min-w-0 flex-1 truncate"
                    :class="
                      ['offline', 'error'].includes(host.last_status)
                        ? 'text-destructive'
                        : ''
                    "
                    :title="host.last_message"
                  >
                    {{
                      checkingHosts.has(host.id)
                        ? "检查中…"
                        : host.host_type === "rdp" &&
                            host.last_status === "online"
                          ? "RDP 服务／证书检查通过"
                          : host.last_message || "尚未检测"
                    }}
                  </dd>
                </div>
              </dl>
              <p
                class="h-4 truncate text-xs text-muted-foreground"
                :title="host.tags"
              >
                {{ host.tags || "无标签" }}
              </p>
              <div class="mt-auto flex items-center gap-2 border-t pt-3">
                <Button
                  v-if="host.activation_pending && host.can_manage"
                  class="min-w-0 flex-1"
                  size="sm"
                  @click="openHostEditor(host)"
                  >配置主机</Button
                >
                <Button
                  v-else-if="
                    host.host_type === 'vnc' &&
                    host.permissions.includes('connect')
                  "
                  class="min-w-0 flex-1"
                  size="sm"
                  :disabled="!host.is_active"
                  @click="router.push(hostDetailsLocation(host, 'desktop'))"
                  ><Monitor class="size-4" />远程桌面</Button
                >
                <Button
                  v-else-if="
                    !host.activation_pending &&
                    host.host_type === 'rdp' &&
                    host.permissions.includes('connect')
                  "
                  class="min-w-0 flex-1"
                  variant="default"
                  size="sm"
                  aria-label="下载远程桌面连接"
                  :disabled="
                    !host.is_active ||
                    !gatewayInfo.rdp_gateway?.running ||
                    operating ||
                    checkingHosts.has(host.id)
                  "
                  @click="downloadRdpFile(host)"
                  ><Monitor class="size-4" />远程桌面</Button
                >
                <Button
                  v-else-if="
                    host.host_type === 'ssh' &&
                    host.permissions.includes('execute')
                  "
                  class="min-w-0 flex-1"
                  variant="default"
                  size="sm"
                  :disabled="!host.is_active"
                  @click="router.push(hostDetailsLocation(host, 'terminal'))"
                  ><Terminal class="size-4" />Web SSH</Button
                >
                <Button
                  v-else-if="
                    host.host_type === 'docker' &&
                    host.permissions.includes('docker')
                  "
                  class="min-w-0 flex-1"
                  variant="default"
                  size="sm"
                  :disabled="!host.is_active"
                  @click="openDocker(host)"
                  ><Boxes class="size-4" />容器管理</Button
                >
                <Button
                  v-else-if="host.permissions.includes('connect')"
                  class="min-w-0 flex-1"
                  variant="default"
                  size="sm"
                  @click="openConnectionDetails(host)"
                  >连接详情</Button
                >
                <span v-else class="flex-1 text-xs text-muted-foreground"
                  >无连接权限</span
                >
                <Button
                  v-if="host.permissions.includes('connect')"
                  aria-label="连接测试"
                  variant="outline"
                  size="icon-sm"
                  :disabled="
                    (!host.is_active && !host.activation_pending) ||
                    checkingHosts.has(host.id)
                  "
                  @click="testHost(host)"
                  ><PlugZap class="size-4"
                /></Button>
                <Button
                  aria-label="连接详情"
                  tooltip="连接详情与说明"
                  variant="outline"
                  size="icon-sm"
                  @click="openConnectionDetails(host)"
                  ><Info class="size-4"
                /></Button>
              </div>
            </article>
          </div>
          <div class="border-t border-gray-200 p-4">
            <TablePagination
              :total="hostList.pagination.total"
              :page="hostList.pagination.page"
              :page-size="hostList.pagination.page_size"
              @page-change="loadHostPage"
              @page-size-change="resizeHostPage"
            /></div></Card
        ><HostCredentialPanel
          v-else-if="tab === 'credentials' && context.is_admin"
          @changed="loadHosts"
        />
        <section
          v-else-if="tab === 'access' && context.is_admin"
          class="space-y-4"
        >
          <div class="rounded-xl border bg-card p-4 sm:p-5">
            <h2 class="font-semibold text-gray-900">添加访问授权</h2>
            <form
              class="mt-3 grid items-end gap-3 sm:grid-cols-2 xl:grid-cols-3"
              @submit.prevent="saveGrant"
            >
              <ResourceCombobox
                v-model="grantForm.host_id"
                label="选择连接服务"
                :fetch-options="managedHostsApi.list"
                :resolve-option="
                  async (id) =>
                    (await managedHostsApi.list({ page: 1, host_id: id }))
                      .items[0]
                "
              /><ResourceCombobox
                v-model="grantForm.subject"
                label="选择用户或 API Key"
                :fetch-options="
                  (params) =>
                    managedHostsApi.subjects({ ...params, active_only: true })
                "
                :resolve-option="
                  async (selected) =>
                    (await managedHostsApi.subjects({ page: 1, selected }))
                      .items[0]
                "
                :get-value="(item) => `${item.subject_type}:${item.id}`"
                :get-label="
                  (item) =>
                    `${item.subject_type === 'user' ? '用户' : 'API Key'} · ${item.name}`
                "
              /><label
                class="flex min-h-11 items-center gap-2 rounded-lg bg-gray-50 px-3 text-sm md:min-h-9 md:bg-transparent md:px-0"
                ><Checkbox v-model="grantForm.can_connect"></Checkbox>连接 / RDP
                访问</label
              ><label
                class="flex min-h-11 items-center gap-2 rounded-lg bg-gray-50 px-3 text-sm md:min-h-9 md:bg-transparent md:px-0"
                ><Checkbox v-model="grantForm.can_execute"></Checkbox>SSH
                命令</label
              ><label
                class="flex min-h-11 items-center gap-2 rounded-lg bg-gray-50 px-3 text-sm md:min-h-9 md:bg-transparent md:px-0"
                ><Checkbox v-model="grantForm.can_manage_docker"></Checkbox
                >Docker 操作</label
              ><Button
                class="sm:col-span-2 xl:col-span-3 sm:w-fit"
                type="submit"
                variant="default"
                size="default"
                >保存授权</Button
              >
            </form>
          </div>
          <form
            class="flex gap-2 rounded-xl border bg-card p-4 sm:p-5"
            @submit.prevent="grantList.load(1)"
          >
            <SearchField
              v-model="grantList.search.value"
              placeholder="搜索授权的连接名称"
              label="搜索授权主机"
              @search="grantList.load(1)"
            ></SearchField
            ><Button type="submit" variant="outline" size="default"
              >搜索</Button
            >
          </form>
          <div
            class="hidden overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm md:block"
          >
            <Table class="w-full min-w-[760px] text-left"
              ><TableHeader
                ><TableRow
                  ><TableHead>主机</TableHead><TableHead>主体</TableHead
                  ><TableHead>权限</TableHead><TableHead>状态</TableHead
                  ><TableHead>操作</TableHead></TableRow
                ></TableHeader
              ><TableBody
                ><TableRow v-for="grant in grants" :key="grant.id"
                  ><TableCell>{{ grant.host_name }}</TableCell
                  ><TableCell
                    >{{ grant.subject_type === "user" ? "用户" : "API Key" }} ·
                    {{ grant.subject_name }}</TableCell
                  ><TableCell>{{ grantPermissions(grant) }}</TableCell
                  ><TableCell>{{
                    grant.is_active && !grant.is_expired ? "有效" : "无效"
                  }}</TableCell
                  ><TableCell
                    ><Button
                      class="text-xs text-red-600"
                      @click="removeGrant(grant)"
                      type="button"
                      variant="ghost"
                      size="default"
                      >撤销</Button
                    ></TableCell
                  ></TableRow
                ><TableRow v-if="grants.length === 0 && !grantList.error.value"
                  ><TableCell colspan="5" class="text-center"
                    >暂无授权</TableCell
                  ></TableRow
                ></TableBody
              ></Table
            >
          </div>
          <Card class="gap-0 py-0 md:hidden"
            ><p
              v-if="grants.length === 0 && !grantList.error.value"
              class="px-4 py-8 text-center text-sm text-gray-400"
            >
              暂无授权
            </p>
            <ul v-else class="mobile-record-list">
              <li
                v-for="grant in grants"
                :key="grant.id"
                class="mobile-record h-56"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <div class="mobile-record-title" :title="grant.host_name">
                      {{ grant.host_name }}
                    </div>
                    <div
                      class="mt-1 truncate text-sm text-muted-foreground"
                      :title="grant.subject_name"
                    >
                      {{ grant.subject_type === "user" ? "用户" : "API Key" }} ·
                      {{ grant.subject_name }}
                    </div>
                  </div>
                  <span
                    class="shrink-0 rounded-full px-2 py-1 text-xs"
                    :class="
                      grant.is_active && !grant.is_expired
                        ? 'bg-emerald-50 text-emerald-700'
                        : 'bg-gray-100 text-gray-500'
                    "
                  >
                    {{ grant.is_active && !grant.is_expired ? "有效" : "无效" }}
                  </span>
                </div>
                <div class="line-clamp-2 text-xs text-muted-foreground">
                  权限：{{ grantPermissions(grant) }}
                </div>
                <Button
                  class="mt-auto w-full touch-manipulation text-destructive"
                  @click="removeGrant(grant)"
                  type="button"
                  variant="outline"
                  size="sm"
                  >撤销授权</Button
                >
              </li>
            </ul></Card
          >
          <div class="rounded-xl border border-gray-200 bg-white p-4">
            <p
              v-if="grantList.error.value"
              role="alert"
              class="mb-3 text-sm text-red-600"
            >
              {{ grantList.error.value }}
            </p>
            <TablePagination
              :total="grantList.pagination.total"
              :page="grantList.pagination.page"
              :page-size="grantList.pagination.page_size"
              @page-change="grantList.load"
              @page-size-change="grantList.resize"
            />
          </div>
        </section>
        <section
          v-else-if="tab === 'users' && context.is_admin"
          class="grid gap-4 lg:grid-cols-[360px_1fr]"
        >
          <form
            class="rounded-xl border bg-card p-4 sm:p-5"
            @submit.prevent="createUser"
          >
            <h2 class="font-semibold text-gray-900">创建系统用户</h2>
            <div class="mt-4 space-y-3">
              <Input
                v-model.trim="userForm.username"
                class="w-full"
                placeholder="用户名"
                required
                minlength="2"
              ></Input
              ><Input
                v-model="userForm.password"
                type="password"
                class="w-full"
                placeholder="初始密码（至少 8 位）"
                required
                minlength="8"
              ></Input
              ><Textarea
                v-model.trim="userForm.ssh_public_key"
                rows="3"
                class="w-full font-mono"
                placeholder="SSH 公钥（可选，ssh-ed25519 / ssh-rsa）"
              ></Textarea
              ><Select v-model="userForm.role"
                ><SelectTrigger class="w-full" aria-label="请选择"
                  ><SelectValue
                    placeholder="请选择"
                  ></SelectValue></SelectTrigger
                ><SelectContent
                  ><SelectItem value="user">普通用户</SelectItem
                  ><SelectItem value="admin">管理员</SelectItem></SelectContent
                ></Select
              ><Button
                class="w-full"
                type="submit"
                variant="default"
                size="default"
                >创建用户</Button
              >
            </div>
          </form>
          <div class="rounded-xl border border-gray-200 bg-white shadow-sm">
            <div class="border-b border-gray-200 px-4 py-3 font-semibold">
              系统用户
            </div>
            <form
              class="flex gap-2 border-b p-4 sm:p-5"
              @submit.prevent="userList.load(1)"
            >
              <SearchField
                v-model="userList.search.value"
                placeholder="搜索用户名"
                label="搜索系统用户"
                @search="userList.load(1)"
              ></SearchField
              ><Button type="submit" variant="outline" size="default"
                >搜索</Button
              >
            </form>
            <div class="mobile-record-list md:gap-0 md:p-0">
              <div
                v-for="user in userSubjects"
                :key="user.id"
                class="mobile-record h-48 md:h-auto md:flex-row md:items-center md:justify-between md:rounded-none md:border-x-0 md:border-t-0"
              >
                <div class="min-w-0">
                  <div
                    class="mobile-record-title md:min-h-0"
                    :title="user.name"
                  >
                    {{ user.name }}
                  </div>
                  <div class="text-xs text-gray-400">
                    {{ user.role === "admin" ? "管理员" : "普通用户" }} ·
                    {{
                      user.has_ssh_public_key
                        ? "已配置 SSH 证书"
                        : "未配置 SSH 证书"
                    }}
                  </div>
                </div>
                <div
                  class="mt-auto flex shrink-0 gap-2 border-t pt-3 md:mt-0 md:border-0 md:pt-0"
                >
                  <Button
                    class="flex-1 touch-manipulation md:flex-none"
                    @click="setUserPublicKey(user)"
                    type="button"
                    variant="outline"
                    size="sm"
                    >证书</Button
                  ><Button
                    class="flex-1 touch-manipulation md:flex-none"
                    @click="toggleUser(user)"
                    type="button"
                    variant="outline"
                    size="sm"
                    >{{ user.is_active ? "禁用" : "启用" }}</Button
                  >
                </div>
              </div>
            </div>
            <div class="border-t border-gray-200 p-4">
              <p
                v-if="userList.error.value"
                role="alert"
                class="mb-3 text-sm text-red-600"
              >
                {{ userList.error.value }}
              </p>
              <TablePagination
                :total="userList.pagination.total"
                :page="userList.pagination.page"
                :page-size="userList.pagination.page_size"
                @page-change="userList.load"
                @page-size-change="userList.resize"
              />
            </div>
          </div>
        </section>
        <HostAuditPanel
          v-else-if="tab === 'audit'"
          ref="auditPanel"
          :is-admin="context.is_admin"
        />
        <section
          v-else-if="tab === 'guide'"
          class="rounded-xl border border-gray-200 bg-white p-3 shadow-sm sm:p-5"
        >
          <h2 class="font-semibold text-gray-900">统一网关访问</h2>
          <p class="mt-2 text-sm text-gray-600">
            系统用户使用自己的登录密码，API 调用方使用已授权 API
            Key；两者都不会接触目标主机真实凭据。
          </p>
          <h3 class="mt-5 text-sm font-semibold text-gray-800">
            SSH 跳板端口 {{ gatewayInfo.port || 2222 }}
          </h3>
          <p
            v-if="gatewayInfo.host_key_fingerprint"
            class="mt-1 break-all font-mono text-xs text-gray-500"
          >
            主机指纹：{{ gatewayInfo.host_key_fingerprint }}
          </p>
          <pre
            class="mt-2 max-w-full overflow-x-auto rounded-lg bg-gray-950 p-3 text-[11px] text-gray-100 sm:p-4 sm:text-xs"
          >
# 系统用户密码
ssh -p {{ gatewayInfo.port || 2222 }} '系统用户#SSH主机名'@平台地址

# 系统用户 SSH 私钥
ssh -i ~/.ssh/id_ed25519 -p {{
              gatewayInfo.port || 2222
            }} '系统用户#SSH主机名'@平台地址

# API Key 作为 SSH 密码
ssh -p {{ gatewayInfo.port || 2222 }} 'SSH主机名'@平台地址</pre>
          <h3 class="mt-5 text-sm font-semibold text-gray-800">
            Docker HTTPS 网关端口
            {{ gatewayInfo.docker_gateway?.port || 23750 }}
          </h3>
          <p
            v-if="gatewayInfo.docker_gateway?.certificate_fingerprint"
            class="mt-1 break-all font-mono text-xs text-gray-500"
          >
            证书指纹：{{ gatewayInfo.docker_gateway.certificate_fingerprint }}
          </p>
          <pre
            class="mt-2 max-w-full overflow-x-auto rounded-lg bg-gray-950 p-3 text-[11px] text-gray-100 sm:p-4 sm:text-xs"
          >
# 下载并信任网关 CA
curl -u '系统用户#Docker主机名:系统用户密码' \
  --cacert frp-agent-docker-gateway-ca.pem \
  https://平台地址:{{
              gatewayInfo.docker_gateway?.port || 23750
            }}/containers/json?all=true

# 主机名 + API Key
curl -u 'Docker主机名:API_KEY' \
  --cacert frp-agent-docker-gateway-ca.pem \
  https://平台地址:{{
              gatewayInfo.docker_gateway?.port || 23750
            }}/containers/json?all=true</pre>
          <Button
            class="mt-2 inline-flex items-center text-sm font-medium touch-manipulation hover:underline"
            @click="downloadDockerCa"
            type="button"
            variant="ghost"
            size="default"
            >下载 Docker 网关 CA 证书</Button
          >
          <h3 class="mt-5 text-sm font-semibold text-gray-800">
            管理 REST API
          </h3>
          <pre
            class="mt-4 max-w-full overflow-x-auto rounded-lg bg-gray-950 p-3 text-[11px] text-gray-100 sm:p-4 sm:text-xs"
          >
curl -H "Authorization: Bearer &lt;API_KEY&gt;" \
  {{ origin }}/api/managed-hosts

curl -X POST -H "Authorization: Bearer &lt;API_KEY&gt;" \
  -H "Content-Type: application/json" \
  -d '{"command":"uptime","timeout":30}' \
  {{ origin }}/api/managed-hosts/&lt;HOST_ID&gt;/commands</pre>
        </section></TabsContent
      >
    </div>
    <Dialog
      v-if="rdpProblemHost"
      :open="true"
      @update:open="
        (open) => {
          if (!open) rdpProblemHost = null;
        }
      "
      ><DialogContent class="sm:max-w-xl" :aria-describedby="undefined"
        ><DialogHeader
          ><DialogTitle
            >{{ rdpProblemHost.name }} · RDP 连接未通过</DialogTitle
          ></DialogHeader
        >
        <div data-slot="dialog-body" class="min-h-0 flex-1 overflow-y-auto p-5">
          <RdpConnectionStatus
            :host="rdpProblemHost"
            :result="rdpChecks[rdpProblemHost.id]"
            :checking="checkingHosts.has(rdpProblemHost.id)"
            :can-manage="context.is_admin && rdpProblemHost.can_manage"
            @check="testHost(rdpProblemHost)"
            @edit="openHostEditor(rdpProblemHost)"
          />
          <p class="mt-3 text-xs leading-5 text-muted-foreground">
            本次未下载连接文件。排除问题后重新下载再连接；不要直接跳过证书验证。
          </p>
        </div>
        <DialogFooter
          ><Button
            type="button"
            variant="outline"
            @click="rdpProblemHost = null"
            >关闭</Button
          ></DialogFooter
        ></DialogContent
      ></Dialog
    >
    <Dialog
      v-if="aiPromptOpen"
      :open="true"
      @update:open="
        (open) => {
          if (!open) {
            aiPromptOpen = false;
          }
        }
      "
      ><DialogContent class="sm:max-w-2xl" :aria-describedby="undefined"
        ><DialogHeader
          ><div>
            <DialogTitle>AI curl 添加主机提示词</DialogTitle>
            <p class="mt-0.5 text-xs text-gray-500">
              填写公开连接信息，生成通过 API 添加主机的安全提示词。
            </p>
          </div></DialogHeader
        >
        <div
          data-slot="dialog-body"
          class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
        >
          <ToggleGroup
            type="single"
            :model-value="aiPromptForm.host_type"
            @update:model-value="
              (value) => {
                if (value) setAiPromptType(value);
              }
            "
            variant="outline"
            class="grid grid-cols-2"
            ><ToggleGroupItem value="ssh">SSH 主机</ToggleGroupItem
            ><ToggleGroupItem value="docker"
              >Docker 主机</ToggleGroupItem
            ></ToggleGroup
          >
          <div class="grid gap-3 sm:grid-cols-2">
            <label class="text-sm"
              >主机名称<Input
                v-model.trim="aiPromptForm.name"
                class="mt-1 w-full"
                placeholder="例如：生产服务器"
              ></Input></label
            ><label class="text-sm"
              >地址<Input
                v-model.trim="aiPromptForm.address"
                class="mt-1 w-full"
                placeholder="域名或 IP"
              ></Input></label
            ><label class="text-sm"
              >端口<Input
                v-model.number="aiPromptForm.port"
                type="number"
                min="1"
                max="65535"
                class="mt-1 w-full"
              ></Input></label
            ><label v-if="aiPromptForm.host_type === 'docker'" class="text-sm"
              >Portainer Endpoint ID<Input
                v-model.number="aiPromptForm.docker_endpoint_id"
                type="number"
                min="1"
                class="mt-1 w-full"
              ></Input
            ></label>
          </div>
          <p
            class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800"
          >
            提示词不会包含密码、私钥或 API Key；需要凭据时，AI
            会要求你在安全表单中输入或上传。
          </p>
          <div>
            <div class="mb-1.5 text-sm font-medium text-gray-700">
              生成的提示词
            </div>
            <Textarea
              readonly
              rows="15"
              class="w-full resize-none font-mono leading-5"
              :model-value="aiHostPrompt"
            ></Textarea>
          </div>
        </div>
        <DialogFooter
          ><Button
            class="touch-manipulation"
            @click="aiPromptOpen = false"
            type="button"
            variant="outline"
            size="default"
            >关闭</Button
          ><Button
            class="touch-manipulation"
            @click="copyAiHostPrompt($event.currentTarget)"
            type="button"
            variant="default"
            size="default"
            >复制提示词</Button
          ></DialogFooter
        ></DialogContent
      ></Dialog
    ><Dialog
      v-if="connectionHost"
      :open="true"
      @update:open="
        (open) => {
          if (!open) {
            connectionHost = null;
          }
        }
      "
      ><DialogContent class="sm:max-w-2xl" :aria-describedby="undefined"
        ><DialogHeader
          ><div class="min-w-0">
            <DialogTitle class="break-all"
              >{{ connectionHost.name }} · 连接详情</DialogTitle
            >
            <p class="mt-0.5 text-xs text-gray-500">
              {{
                {
                  ssh: "SSH 跳板连接",
                  docker: "Docker HTTPS 网关",
                  rdp: "RDP 平台账号代登录",
                  vnc: "VNC 远程桌面",
                }[connectionHost.host_type]
              }}
            </p>
          </div></DialogHeader
        >
        <div
          data-slot="dialog-body"
          class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
        >
          <dl class="grid gap-2 text-sm sm:grid-cols-[7rem_minmax(0,1fr)]">
            <dt class="text-muted-foreground">{{ connectionHost.host_type === 'vnc' && connectionHost.vnc_ssh_host_id ? 'Mac 回环地址' : '目标地址' }}</dt>
            <dd class="min-w-0 break-all font-mono text-xs">
              {{ hostAddress(connectionHost) }}
            </dd>
            <dt class="text-muted-foreground">访问凭据</dt>
            <dd class="min-w-0 break-all">
              {{ connectionHost.credential_name || "未配置"
              }}{{
                connectionHost.credential_username
                  ? ` / ${connectionHost.credential_username}`
                  : ""
              }}
            </dd>
            <dt class="text-muted-foreground">系统版本</dt>
            <dd class="min-w-0 break-words">
              {{ connectionHost.version_info || "未采集" }}
            </dd>
            <dt class="text-muted-foreground">最近状态</dt>
            <dd class="min-w-0 whitespace-pre-wrap break-all">
              {{ connectionHost.last_message || "尚未检测" }}
            </dd>
            <template v-if="connectionHost.host_key_fingerprint"
              ><dt class="text-muted-foreground">目标指纹</dt>
              <dd class="min-w-0 break-all font-mono text-xs">
                {{ connectionHost.host_key_fingerprint }}
              </dd></template
            >
            <dt class="text-muted-foreground">标签</dt>
            <dd class="min-w-0 break-all">
              {{ connectionHost.tags || "无标签" }}
            </dd>
          </dl>
          <dl
            class="grid gap-2 rounded-xl border border-gray-200 bg-gray-50 p-3 text-sm sm:grid-cols-[7rem_1fr]"
          >
            <dt class="text-gray-500">{{ connectionHost.host_type === 'vnc' ? '平台地址' : '网关地址' }}</dt>
            <dd class="flex min-w-0 items-center gap-2">
              <code class="min-w-0 flex-1 break-all text-xs text-gray-900">{{
                connectionInfo.gateway
              }}</code
              ><Button
                class="touch-manipulation"
                :aria-label="connectionHost.host_type === 'vnc' ? '复制平台地址' : '复制网关地址'"
                :title="connectionHost.host_type === 'vnc' ? '复制平台地址' : '复制网关地址'"
                @click="
                  copyCredentialValue(
                    connectionInfo.gateway,
                    $event.currentTarget,
                  )
                "
                type="button"
                variant="outline"
                size="icon"
                ><svg
                  class="h-4 w-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <rect x="9" y="9" width="13" height="13" rx="2"></rect>
                  <path
                    d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"
                  ></path></svg
              ></Button>
            </dd>
            <dt class="text-gray-500">{{ connectionHost.host_type === 'vnc' ? '当前平台账号' : '登录用户名' }}</dt>
            <dd class="flex min-w-0 items-center gap-2">
              <code class="min-w-0 flex-1 break-all text-xs text-gray-900">{{
                connectionInfo.loginName
              }}</code
              ><Button
                class="touch-manipulation"
                :aria-label="connectionHost.host_type === 'vnc' ? '复制平台账号' : '复制登录用户名'"
                :title="connectionHost.host_type === 'vnc' ? '复制平台账号' : '复制登录用户名'"
                @click="
                  copyCredentialValue(
                    connectionInfo.loginName,
                    $event.currentTarget,
                  )
                "
                type="button"
                variant="outline"
                size="icon"
                ><svg
                  class="h-4 w-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <rect x="9" y="9" width="13" height="13" rx="2"></rect>
                  <path
                    d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"
                  ></path></svg
              ></Button>
            </dd>
            <dt class="text-gray-500">认证</dt>
            <dd class="text-gray-900">{{ connectionInfo.passwordHint }}</dd>
            <template
              v-if="
                connectionHost.host_type === 'ssh' &&
                gatewayInfo.host_key_fingerprint
              "
            >
              <dt class="text-gray-500">网关指纹</dt>
              <dd class="flex min-w-0 items-center gap-2">
                <code class="min-w-0 flex-1 break-all text-xs text-gray-900">{{
                  gatewayInfo.host_key_fingerprint
                }}</code
                ><Button
                  class="touch-manipulation"
                  aria-label="复制网关指纹"
                  title="复制网关指纹"
                  @click="
                    copyCredentialValue(
                      gatewayInfo.host_key_fingerprint,
                      $event.currentTarget,
                    )
                  "
                  type="button"
                  variant="outline"
                  size="icon"
                  ><svg
                    class="h-4 w-4"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <rect x="9" y="9" width="13" height="13" rx="2"></rect>
                    <path
                      d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"
                    ></path></svg
                ></Button>
              </dd>
            </template>
          </dl>
          <section
            v-if="connectionHost.host_type === 'rdp'"
            class="rounded-lg bg-muted/40 p-3 text-xs leading-5 text-muted-foreground"
          >
            <h3 class="mb-1 font-medium text-foreground">远程桌面连接说明</h3>
            <p>
              {{
                gatewayInfo.rdp_gateway?.running
                  ? "使用 mstsc 或 Windows App 连接网关地址，填写“平台账号#主机名”和平台密码，客户端的网关设置留空。首次使用或修改密码后，请先用平台密码登录网页一次；也可下载连接文件。"
                  : "RDP 网关未运行，请管理员配置公网地址、TLS 证书并启用网关。"
              }}
            </p>
          </section>
          <RdpConnectionStatus
            v-if="connectionHost.host_type === 'rdp'"
            :host="connectionHost"
            :result="rdpChecks[connectionHost.id]"
            :checking="checkingHosts.has(connectionHost.id)"
            :can-manage="context.is_admin && connectionHost.can_manage"
            @check="testHost(connectionHost)"
            @edit="openHostEditor(connectionHost)"
          />
          <p
            v-if="connectionHost.host_type === 'rdp'"
            class="rounded-lg bg-muted/40 p-3 text-xs leading-5 text-muted-foreground"
          >
            若客户端快速断开，先重新校验证书，再查看审计记录。“平台认证通过”仅代表网关授权；只有“RDP
            桌面已连接”才表示进入桌面。网关填写平台账号密码，Windows
            密码由管理员在凭据库维护。
          </p>
          <p v-if="connectionHost.host_type === 'vnc'" class="text-xs leading-5 text-muted-foreground">
            在浏览器中打开桌面链接。目标 VNC 密码由服务端代用；直连使用可信网络入口，SSH 隧道仅在该连接启用时使用。
          </p>
          <div>
            <div class="mb-1.5 text-sm font-medium text-gray-700">{{ connectionHost.host_type === 'vnc' ? '桌面链接' : '终端命令' }}</div>
            <pre
              class="max-h-48 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-gray-950 p-3 text-xs text-gray-100"
              >{{ connectionInfo.command }}</pre>
          </div>
          <p
            v-if="connectionHost.host_type === 'docker'"
            class="text-xs leading-5 text-gray-500"
          >
            Docker 网关命令需要先下载 CA 证书，并将证书保存为
            <code>frp-agent-docker-gateway-ca.pem</code>。
          </p>
        </div>
        <DialogFooter
          ><Button
            v-if="connectionHost.host_type === 'vnc'"
            :disabled="!connectionHost.is_active || !connectionHost.permissions.includes('connect')"
            @click="router.push(hostDetailsLocation(connectionHost, 'desktop'))"
            type="button"
            >打开远程桌面</Button
          ><Button
            v-if="connectionHost.host_type === 'docker'"
            class="touch-manipulation"
            @click="downloadDockerCa"
            type="button"
            variant="outline"
            size="default"
            >下载 CA 证书</Button
          ><Button
            v-if="
              connectionHost.host_type === 'docker' &&
              gatewayInfo.docker_gateway?.client_certificate_available
            "
            class="touch-manipulation"
            @click="downloadDockerClientCert"
            type="button"
            variant="outline"
            size="default"
            >下载客户端证书</Button
          ><Button
            class="touch-manipulation"
            @click="copyConnectionCommand(connectionHost, $event.currentTarget)"
            type="button"
            :variant="connectionHost.host_type === 'vnc' ? 'outline' : 'default'"
            size="default"
            >{{ connectionHost.host_type === 'vnc' ? '复制链接' : '复制命令' }}</Button
          ></DialogFooter
        ></DialogContent
      ></Dialog
    ><Dialog
      v-if="dockerHost"
      :open="true"
      @update:open="
        (open) => {
          if (!open) {
            dockerHost = null;
          }
        }
      "
      ><DialogContent class="sm:max-w-4xl" :aria-describedby="undefined"
        ><DialogHeader
          ><DialogTitle>{{ dockerHost.name }} · 容器</DialogTitle></DialogHeader
        >
        <div
          data-slot="dialog-body"
          class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
        >
          <div v-if="operating" class="py-8 text-center text-sm text-gray-500">
            正在通过 Portainer API 读取容器...
          </div>
          <div v-else class="space-y-2">
            <div
              v-for="container in containers"
              :key="container.Id"
              class="flex flex-col gap-2 rounded-lg border p-3 sm:flex-row sm:items-center"
            >
              <div class="min-w-0 flex-1">
                <div class="font-medium">
                  {{
                    (container.Names || []).join(", ").replaceAll("/", "") ||
                    container.Id?.slice(0, 12)
                  }}
                </div>
                <div class="truncate text-xs text-gray-500">
                  {{ container.Image }} · {{ container.Status }}
                </div>
              </div>
              <div class="grid grid-cols-3 gap-2 sm:flex">
                <Button
                  v-for="action in ['start', 'stop', 'restart']"
                  :key="action"
                  class="touch-manipulation"
                  @click="dockerAction(container, action)"
                  type="button"
                  variant="outline"
                  size="sm"
                  >{{
                    { start: "启动", stop: "停止", restart: "重启" }[action]
                  }}</Button
                >
              </div>
            </div>
            <div
              v-if="containers.length === 0"
              class="py-8 text-center text-sm text-gray-400"
            >
              暂无容器
            </div>
          </div>
        </div>
        <DialogFooter
          ><div class="w-full">
            <p
              v-if="containerList.error.value"
              role="alert"
              class="mb-2 text-sm text-red-600"
            >
              {{ containerList.error.value }}
            </p>
            <TablePagination
              :total="containerList.pagination.total"
              :page="containerList.pagination.page"
              :page-size="containerList.pagination.page_size"
              @page-change="containerList.load"
              @page-size-change="containerList.resize"
            /></div></DialogFooter></DialogContent></Dialog
    ><HostDiscoveryDialog
      v-if="context.is_admin"
      v-model:open="discoveryOpen"
      @imported="loadHosts"
  /></Tabs>
</template>

<script setup>
import HostDiscoveryDialog from "@/components/HostDiscoveryDialog.vue";
import ActionMenu from "@/components/ActionMenu.vue";
import {
  Boxes,
  FileClock,
  Info,
  Monitor,
  PlugZap,
  Terminal,
} from "@lucide/vue";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import SearchField from "@/components/SearchField.vue";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Select } from "@/components/ui/select";
import { SelectContent } from "@/components/ui/select";
import { SelectItem } from "@/components/ui/select";
import { SelectTrigger } from "@/components/ui/select";
import { SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Table } from "@/components/ui/table";
import { TableBody } from "@/components/ui/table";
import { TableCell } from "@/components/ui/table";
import { TableHeader } from "@/components/ui/table";
import { TableRow } from "@/components/ui/table";
import { TableHead } from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { notify, confirmAction, promptText } from "@/composables/useFeedback";
import PageHeader from "@/components/PageHeader.vue";
import HostAuditPanel from "@/components/HostAuditPanel.vue";
import HostCredentialPanel from "@/components/HostCredentialPanel.vue";
import ResourceCombobox from "@/components/ResourceCombobox.vue";
import TablePagination from "@/components/TablePagination.vue";
import { usePagedList } from "@/composables/usePagedList";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { managedHostsApi } from "@/api/managedHosts";
import RdpConnectionStatus from "@/components/RdpConnectionStatus.vue";
import { copyText } from "@/composables/useClipboard";
import { useRouter, useRoute } from "vue-router";

const router = useRouter(),
  route = useRoute();
const hostFilters = reactive({
  type: String(route.query.host_type || "all"),
  status: String(route.query.host_status || "all"),
});
const hostList = usePagedList((params) =>
  managedHostsApi.list({
    ...params,
    host_type: hostFilters.type === "all" ? undefined : hostFilters.type,
    host_status: hostFilters.status === "all" ? undefined : hostFilters.status,
  }),
);
const hasHostFilters = computed(() =>
  Boolean(
    hostList.search.value ||
    hostFilters.type !== "all" ||
    hostFilters.status !== "all",
  ),
);
hostList.search.value =
  typeof route.query.search === "string" ? route.query.search : "";
hostList.pagination.page = Math.max(1, Number(route.query.page) || 1);
hostList.pagination.page_size = [10, 20, 50, 100].includes(
  Number(route.query.page_size),
)
  ? Number(route.query.page_size)
  : 20;
function hostListQuery(page = hostList.pagination.page) {
  return {
    page: String(page),
    page_size: String(hostList.pagination.page_size),
    search: hostList.search.value || undefined,
    host_type: hostFilters.type === "all" ? undefined : hostFilters.type,
    host_status: hostFilters.status === "all" ? undefined : hostFilters.status,
  };
}
async function loadHostPage(page = 1) {
  hostList.pagination.page = page;
  await router.replace({ path: "/hosts", query: hostListQuery(page) });
  await hostList.load(page);
}
function resizeHostPage(size) {
  hostList.pagination.page_size = size;
  return loadHostPage(1);
}
function clearHostFilters() {
  hostFilters.type = hostFilters.status = "all";
  hostList.search.value = "";
  return loadHostPage(1);
}
watch(
  () => route.query,
  (query) => {
    const type = String(query.host_type || "all"),
      status = String(query.host_status || "all"),
      search = String(query.search || ""),
      page = Math.max(1, Number(query.page) || 1),
      size = [10, 20, 50, 100].includes(Number(query.page_size))
        ? Number(query.page_size)
        : 20;
    if (
      type === hostFilters.type &&
      status === hostFilters.status &&
      search === hostList.search.value &&
      page === hostList.pagination.page &&
      size === hostList.pagination.page_size
    )
      return;
    Object.assign(hostFilters, { type, status });
    hostList.search.value = search;
    hostList.pagination.page = page;
    hostList.pagination.page_size = size;
    hostList.load(page);
  },
);
const grantList = usePagedList(managedHostsApi.grants);
const userList = usePagedList((params) =>
  managedHostsApi.subjects({ ...params, subject_type: "user" }),
);
const hosts = hostList.items;
const auditPanel = ref(null);
const context = reactive({
  is_admin: false,
  actor_type: "user",
  actor_name: "",
});
const gatewayInfo = ref({});
const grants = grantList.items;

const loading = ref(true);
const deletingHostId = ref(null);
const operating = ref(false);
const tab = ref("hosts");
const aiPromptOpen = ref(false);
const discoveryOpen = ref(false);
const connectionHost = ref(null);
const rdpProblemHost = ref(null);
const rdpChecks = reactive({});
const checkingHosts = reactive(new Set());
const dockerHost = ref(null);
const containerList = usePagedList((params) =>
  managedHostsApi.containers(dockerHost.value.id, params),
);
const containers = containerList.items;
const origin = window.location.origin;

const tabs = computed(() => [
  { key: "hosts", label: "连接服务" },
  ...(context.is_admin
    ? [
        { key: "credentials", label: "凭证管理" },
        { key: "access", label: "访问授权" },
        { key: "users", label: "系统用户" },
      ]
    : []),
  { key: "audit", label: "审计与流量" },
  { key: "guide", label: "API 访问" },
]);
const userSubjects = userList.items;
const connectionInfo = computed(() =>
  connectionHost.value ? buildConnectionInfo(connectionHost.value) : {},
);
const aiHostPrompt = computed(() => {
  const type = aiPromptForm.host_type === "ssh" ? "SSH" : "Docker / Portainer";
  const name = aiPromptForm.name || "<请先向我确认主机名称>";
  const address = aiPromptForm.address || "<请先向我确认域名或 IP>";
  const common = [
    `请优先使用 curl 调用 API，把下面的 ${type} 主机安全地接入 FRP-AGENT 主机管理系统。`,
    "",
    `平台 API 地址：${origin}/api`,
    `资源类型：${type}`,
    `主机名称：${name}`,
    `目标地址：${address}`,
    `目标端口：${aiPromptForm.port}`,
    ...(aiPromptForm.host_type === "docker"
      ? [`Portainer Endpoint ID：${aiPromptForm.docker_endpoint_id}`]
      : []),
    "",
    "执行要求：",
    "1. 全程优先使用 curl 调用 REST API，不要通过浏览器表单添加；请求失败时输出 HTTP 状态和已脱敏的错误信息。",
    "2. SSH 主机与 Docker 主机是两种独立资源类型，不得混用凭据或字段。",
    '3. 管理接口需要管理员身份。使用我预先准备并设置为 0600 权限的 curl 配置文件：curl --config "$FRP_CURL_CONFIG"；不得索取、猜测或输出管理员密码，也不得把密码放入 URL、命令行参数或聊天记录。',
    "4. 先用 GET /api/managed-hosts 和对应凭据接口查询现有数据。如果同名主机或凭据已存在，展示脱敏后的差异并征得我确认，不要直接覆盖或删除。",
    '5. 需要新凭据时，让我把凭据 JSON 保存到仅当前用户可读的本地文件，再使用 curl --data-binary @"$CREDENTIAL_JSON" 上传；不要读取后回显密码、私钥、私钥口令或 Portainer API Key。',
  ];
  const specific =
    aiPromptForm.host_type === "ssh"
      ? [
          '6. SSH 凭据接口为 /api/ssh-credentials；目标用户需要 sudo 密码时，可在凭据 JSON 中加入 sudo_password。取得 credential_id 后，POST /api/managed-hosts，JSON 中使用 host_type="ssh"、credential_id、名称、地址和端口。',
          "7. 从创建响应取得主机 id，再 POST /api/managed-hosts/{id}/test。首次连接返回服务器指纹时先让我核对；测试成功后只报告主机状态、登录用户和指纹。",
        ]
      : [
          '6. Portainer 凭据接口为 /api/docker-credentials。取得 docker_credential_id 后，POST /api/managed-hosts，JSON 中使用 host_type="docker"、docker_credential_id、docker_endpoint_id、docker_use_tls、docker_verify_tls、名称、地址和端口。',
          "7. 从创建响应取得主机 id，再 POST /api/managed-hosts/{id}/test，并 GET /api/managed-hosts/{id}/docker/containers。只报告 Endpoint 状态和容器数量，不要执行启动、停止、重启或删除操作。",
        ];
  return [
    ...common,
    ...specific,
    "8. 每次 curl 都使用 --fail-with-body --silent --show-error。完成后只汇报调用过的接口、新增或更新的资源、测试结果和需要我处理的事项。",
  ].join("\n");
});

const grantForm = reactive({
  host_id: 0,
  subject: "",
  can_connect: true,
  can_execute: false,
  can_manage_docker: false,
});
const userForm = reactive({
  username: "",
  password: "",
  role: "user",
  ssh_public_key: "",
});
const aiPromptForm = reactive({
  host_type: "ssh",
  name: "",
  address: "",
  port: 22,
  docker_endpoint_id: 1,
});

async function loadHosts() {
  await hostList.load();
}
async function loadAdminData() {
  if (!context.is_admin) return;
  if (tab.value === "access") await grantList.load();
  else if (tab.value === "users") await userList.load();
}
async function loadAudit() {
  await auditPanel.value?.load();
}
async function load() {
  loading.value = true;
  try {
    Object.assign(context, await managedHostsApi.context());
    const [, , gateway] = await Promise.all([
      loadHosts(),
      loadAudit(),
      managedHostsApi.gatewayInfo(),
    ]);
    gatewayInfo.value = gateway || {};
    await loadAdminData();
  } catch (e) {
    notify(e.message);
  } finally {
    loading.value = false;
  }
}

function setAiPromptType(type) {
  aiPromptForm.host_type = type;
  aiPromptForm.port = type === "ssh" ? 22 : 9000;
}
function openAiHostPrompt() {
  Object.assign(aiPromptForm, {
    host_type: "ssh",
    name: "",
    address: "",
    port: 22,
    docker_endpoint_id: 1,
  });
  aiPromptOpen.value = true;
}
async function copyAiHostPrompt(trigger) {
  await copyText(aiHostPrompt.value, trigger);
}
function openHostEditor(host = null, clone = false) {
  rdpProblemHost.value = null;
  router.push({
    path: host ? `/hosts/${host.id}/${clone ? "clone" : "edit"}` : "/hosts/new",
    query: hostListQuery(),
  });
}
async function removeHost(host) {
  if (deletingHostId.value) return;
  deletingHostId.value = host.id;
  try {
    if (
      !(await confirmAction(
        `确定删除连接服务“${host.name}”（${host.address}:${host.port}）？\n该服务的授权与审计记录也会删除，所属主机和其他连接服务保留。此操作不可恢复。`,
        { title: "删除连接服务", confirmText: "删除连接", danger: true },
      ))
    )
      return;
    await managedHostsApi.remove(host.id);
    await loadHosts();
    await loadAdminData();
    notify("连接服务已删除", "success");
  } catch (e) {
    notify(e.message, "error");
  } finally {
    deletingHostId.value = null;
  }
}
async function testHost(host) {
  if (checkingHosts.has(host.id)) return false;
  checkingHosts.add(host.id);
  try {
    const result = await managedHostsApi.test(host.id);
    if (host.host_type === "rdp") {
      rdpChecks[host.id] = {
        success: result.success,
        message: result.stderr || result.stdout,
        checkedAt: new Date().toISOString(),
      };
      if (!result.success) rdpProblemHost.value = host;
      else if (rdpProblemHost.value?.id === host.id)
        rdpProblemHost.value = null;
    } else
      notify(
        result.success ? `连接成功（${result.duration_ms}ms）` : result.stderr,
      );
    await loadHosts();
    await loadAudit();
    return result.success;
  } catch (e) {
    if (host.host_type === "rdp") {
      rdpChecks[host.id] = {
        success: false,
        message: e.message,
        checkedAt: new Date().toISOString(),
      };
      rdpProblemHost.value = host;
    } else notify(e.message);
    return false;
  } finally {
    checkingHosts.delete(host.id);
  }
}
async function downloadRdpFile(host) {
  if (operating.value || checkingHosts.has(host.id)) return;
  operating.value = true;
  try {
    if (!(await testHost(host))) return;
    const blob = await managedHostsApi.rdpFile(host.id);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `frp-agent-rdp-${host.id}.rdp`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    await loadAudit();
  } catch (e) {
    notify(e.message);
  } finally {
    operating.value = false;
  }
}
async function openDocker(host) {
  dockerHost.value = host;
  containerList.pagination.page = 1;
  await loadContainers();
}
async function loadContainers() {
  operating.value = true;
  try {
    await containerList.load();
  } catch (e) {
    notify(e.message);
  } finally {
    operating.value = false;
    loadAudit();
  }
}
async function dockerAction(container, action) {
  const name = (container.Names || [container.Id])[0].replace("/", "");
  if (
    !(await confirmAction(
      `确定${{ start: "启动", stop: "停止", restart: "重启" }[action]}容器 ${name}？`,
    ))
  )
    return;
  try {
    await managedHostsApi.dockerAction(dockerHost.value.id, {
      action,
      container: name,
      timeout: 30,
    });
    await loadContainers();
  } catch (e) {
    notify(e.message);
  }
}
async function saveGrant() {
  if (!grantForm.host_id || !grantForm.subject)
    return notify("请选择连接服务和授权主体");
  const [subject_type, rawId] = grantForm.subject.split(":");
  try {
    await managedHostsApi.createGrant({
      host_id: grantForm.host_id,
      subject_type,
      subject_id: Number(rawId),
      can_connect: grantForm.can_connect,
      can_execute: grantForm.can_execute,
      can_manage_docker: grantForm.can_manage_docker,
    });
    await grantList.load();
  } catch (e) {
    notify(e.message);
  }
}
async function removeGrant(grant) {
  if (await confirmAction("确定撤销该授权？")) {
    try {
      await managedHostsApi.removeGrant(grant.id);
      await grantList.load();
    } catch (e) {
      notify(e.message);
    }
  }
}
async function createUser() {
  try {
    await managedHostsApi.createUser({
      ...userForm,
      ssh_public_key: userForm.ssh_public_key || null,
    });
    Object.assign(userForm, {
      username: "",
      password: "",
      role: "user",
      ssh_public_key: "",
    });
    await userList.load();
  } catch (e) {
    notify(e.message);
  }
}
async function toggleUser(user) {
  try {
    await managedHostsApi.updateUser(user.id, { is_active: !user.is_active });
    await userList.load();
  } catch (e) {
    notify(e.message);
  }
}
async function setUserPublicKey(user) {
  const value = await promptText(
    `设置 ${user.name} 的 OpenSSH 公钥；留空并确认将删除现有证书。`,
    "",
  );
  if (value === null) return;
  try {
    await managedHostsApi.updateUser(user.id, {
      ssh_public_key: value.trim() || null,
    });
    await userList.load();
  } catch (e) {
    notify(e.message);
  }
}
function grantPermissions(g) {
  return (
    [
      g.can_connect && "连接",
      g.can_execute && "SSH 命令",
      g.can_manage_docker && "Docker",
    ]
      .filter(Boolean)
      .join("、") || "无"
  );
}
function hasUrlScheme(value) {
  return /^https?:\/\//i.test(value || "");
}
function hostAddress(host) {
  if (host.host_type !== "docker") return `${host.address}:${host.port}`;
  return hasUrlScheme(host.address)
    ? host.address
    : `${host.docker_use_tls ? "https" : "http"}://${host.address}:${host.port}`;
}
function formatDate(value) {
  return value ? new Date(value).toLocaleString("zh-CN") : "-";
}
function shellQuote(value) {
  return `'${String(value).replaceAll("'", "'\\''")}'`;
}
function buildConnectionInfo(host) {
  const gatewayHost = window.location.hostname || "平台地址";
  const isApiKey = context.actor_type === "api_key";
  const loginName = isApiKey ? host.name : `${context.actor_name}#${host.name}`;
  if (host.host_type === "vnc")
    return {
      gateway: window.location.origin,
      loginName: context.actor_name,
      passwordHint: "平台连接授权；目标 VNC 密码由服务端代用",
      command: new URL(`/hosts/${host.id}?tab=desktop`, window.location.origin)
        .href,
    };
  if (host.host_type === "rdp") {
    const gateway =
      gatewayInfo.value.rdp_gateway?.public_address ||
      `${gatewayHost}:${gatewayInfo.value.rdp_gateway?.port || 13389}`;
    return {
      gateway,
      loginName,
      passwordHint: isApiKey
        ? "已授权的 API Key"
        : "平台账号密码（自动代登录 Windows）",
      command: `mstsc /v:${gateway}`,
    };
  }
  const port =
    host.host_type === "ssh"
      ? gatewayInfo.value.port || 2222
      : gatewayInfo.value.docker_gateway?.port || 23750;
  const useClientCertificate =
    host.host_type === "docker" &&
    !isApiKey &&
    gatewayInfo.value.docker_gateway?.client_certificate_available;
  const clientCertificate = `frp-agent-docker-client-${host.id}.pem`;
  return {
    gateway: `${gatewayHost}:${port}`,
    loginName,
    passwordHint: isApiKey
      ? "已授权的 API Key"
      : useClientCertificate
        ? "已登记 SSH 私钥 + Docker 客户端证书"
        : "系统用户密码",
    command:
      host.host_type === "ssh"
        ? `ssh -p ${port} ${shellQuote(loginName)}@${gatewayHost}`
        : useClientCertificate
          ? `docker --tlsverify --tlscacert frp-agent-docker-gateway-ca.pem --tlscert ${clientCertificate} --tlskey ~/.ssh/jbm_rsa -H tcp://${gatewayHost}:${port} ps`
          : `curl -u ${shellQuote(loginName)} --cacert frp-agent-docker-gateway-ca.pem ${shellQuote(`https://${gatewayHost}:${port}/containers/json?all=true`)}`,
  };
}
function runHostAction(action, host) {
  if (action === "audit") {
    router.push(hostDetailsLocation(host, "logs"));
  } else if (action === "edit") openHostEditor(host);
  else if (action === "clone") openHostEditor(host, true);
  else if (action === "delete") removeHost(host);
}
function hostDetailsLocation(host, tab = "overview") {
  return {
    path: `/hosts/${host.id}`,
    query: {
      ...hostListQuery(),
      tab,
    },
  };
}
function openConnectionDetails(host) {
  connectionHost.value = host;
}
async function copyCredentialValue(value, trigger) {
  await copyText(value, trigger);
}
async function copyConnectionCommand(host, trigger) {
  await copyText(buildConnectionInfo(host).command, trigger);
}
async function downloadDockerCa() {
  try {
    const blob = await managedHostsApi.dockerGatewayCa();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "frp-agent-docker-gateway-ca.pem";
    link.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    notify(e.message);
  }
}
async function downloadDockerClientCert() {
  try {
    const blob = await managedHostsApi.dockerClientCert(
      connectionHost.value.id,
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `frp-agent-docker-client-${connectionHost.value.id}.pem`;
    link.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    notify(e.message);
  }
}

watch(tab, (value) => {
  if (value === "hosts") loadHosts();
  else if (value !== "audit") loadAdminData();
});
onMounted(load);
</script>
