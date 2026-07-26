<template>
  <div class="space-y-4">
    <div class="rounded-xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 class="text-lg font-semibold text-gray-900">主机资源</h1>
          <p class="mt-1 text-sm text-gray-500">
            SSH 主机与 Portainer Docker 环境独立纳管，共用用户/API Key 授权与访问审计。
          </p>
        </div>
        <div v-if="context.is_admin" class="grid w-full grid-cols-2 gap-2 sm:flex sm:w-auto">
          <button class="btn btn-md btn-outline-primary min-h-11 touch-manipulation sm:min-h-9" @click="openAiHostPrompt">
            AI / curl 添加提示词
          </button>
          <button class="btn btn-md btn-primary min-h-11 touch-manipulation sm:min-h-9" @click="openHostEditor()">
            添加主机
          </button>
        </div>
      </div>
      <div class="-mx-1 mt-4 flex snap-x gap-1 overflow-x-auto border-b border-gray-200 px-1">
        <button
          v-for="item in tabs"
          :key="item.key"
          class="min-h-11 shrink-0 snap-start border-b-2 px-3 py-2 text-sm font-medium touch-manipulation sm:min-h-9"
          :class="tab === item.key ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-800'"
          @click="tab = item.key"
        >{{ item.label }}</button>
      </div>
    </div>

    <section v-if="tab === 'hosts'" class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <div v-if="loading" class="p-10 text-center text-sm text-gray-500">加载中...</div>
      <div v-else-if="hosts.length === 0" class="p-10 text-center text-sm text-gray-500">
        暂无可访问的主机资源
      </div>
      <div v-else class="grid gap-3 p-3 md:grid-cols-2 xl:grid-cols-3">
        <article v-for="host in hosts" :key="host.id" class="min-w-0 rounded-xl border border-gray-200 p-3 sm:p-4">
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <h2 class="truncate font-semibold text-gray-900">{{ host.name }}</h2>
                <span
                  class="rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="host.host_type === 'ssh' ? 'bg-blue-50 text-blue-700' : 'bg-violet-50 text-violet-700'"
                >{{ host.host_type === 'ssh' ? 'SSH' : 'Docker / Portainer' }}</span>
              </div>
              <p class="mt-1 break-all font-mono text-xs text-gray-500">
                {{ host.host_type === 'docker' ? (host.docker_use_tls ? 'https://' : 'http://') : '' }}{{ host.address }}:{{ host.port }}
              </p>
            </div>
            <span class="h-2.5 w-2.5 shrink-0 rounded-full" :class="statusDot(host.last_status)" :title="host.last_status"></span>
          </div>
          <dl class="mt-3 space-y-1.5 text-xs text-gray-600">
            <div class="flex justify-between gap-3"><dt class="text-gray-400">访问凭据</dt><dd class="truncate">{{ host.credential_name }}<span v-if="host.credential_username"> / {{ host.credential_username }}</span></dd></div>
            <div v-if="host.host_type === 'ssh'" class="flex justify-between gap-3"><dt class="text-gray-400">主机指纹</dt><dd class="max-w-[70%] truncate font-mono" :title="host.host_key_fingerprint">{{ host.host_key_fingerprint || '首次测试时记录' }}</dd></div>
            <div class="flex justify-between gap-3"><dt class="text-gray-400">最近状态</dt><dd class="truncate">{{ host.last_message || '尚未检测' }}</dd></div>
            <div v-if="host.version_info" class="flex justify-between gap-3"><dt class="shrink-0 text-gray-400">版本信息</dt><dd class="max-w-[72%] break-words text-right" :title="host.version_info">{{ host.version_info }}</dd></div>
          </dl>
          <div v-if="host.tags" class="mt-3 text-xs text-gray-400">{{ host.tags }}</div>
          <div class="mt-4 grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
            <button v-if="host.permissions.includes('connect')" class="btn btn-sm btn-outline min-h-11 touch-manipulation sm:min-h-8" @click="testHost(host)">连接测试</button>
            <button v-if="host.permissions.includes('connect')" class="btn btn-sm btn-outline-primary min-h-11 touch-manipulation sm:min-h-8" @click="openConnectionDetails(host)">
              连接凭证
            </button>
            <button v-if="host.host_type === 'ssh' && host.permissions.includes('execute')" class="btn btn-sm btn-outline-primary min-h-11 touch-manipulation sm:min-h-8" @click="openConsole(host)">命令终端</button>
            <button v-if="host.host_type === 'docker' && host.permissions.includes('docker')" class="btn btn-sm min-h-11 touch-manipulation border border-violet-300 bg-white text-violet-700 hover:bg-violet-50 sm:min-h-8" @click="openDocker(host)">容器管理</button>
            <button v-if="host.can_manage" class="btn btn-sm btn-ghost hidden text-gray-500 sm:inline-flex sm:min-h-8" @click="openHostEditor(host)">编辑</button>
            <button v-if="host.can_manage" class="btn btn-sm hidden text-red-500 hover:bg-red-50 sm:inline-flex sm:min-h-8" @click="removeHost(host)">删除</button>
            <details v-if="host.can_manage" class="group col-span-2 rounded-lg border border-gray-200 bg-gray-50 sm:hidden">
              <summary class="flex min-h-11 cursor-pointer list-none items-center justify-center gap-1 text-sm font-medium text-gray-500 touch-manipulation">
                更多管理操作
                <span class="transition-transform group-open:rotate-180">⌄</span>
              </summary>
              <div class="grid grid-cols-2 gap-2 border-t border-gray-200 p-2">
                <button class="btn btn-sm btn-outline min-h-11 touch-manipulation" @click="openHostEditor(host)">编辑主机</button>
                <button class="btn btn-sm min-h-11 touch-manipulation border border-red-200 bg-white text-red-600 hover:bg-red-50" @click="removeHost(host)">删除主机</button>
              </div>
            </details>
          </div>
        </article>
      </div>
    </section>

    <section v-else-if="tab === 'access' && context.is_admin" class="space-y-4">
      <div class="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <h2 class="font-semibold text-gray-900">添加访问授权</h2>
        <form class="mt-3 grid gap-3 md:grid-cols-5" @submit.prevent="saveGrant">
          <select v-model.number="grantForm.host_id" class="min-h-11 rounded-lg border border-gray-300 px-3 py-2 text-sm md:min-h-9" required>
            <option :value="0" disabled>选择主机</option>
            <option v-for="host in hosts" :key="host.id" :value="host.id">{{ host.name }}（{{ host.host_type.toUpperCase() }}）</option>
          </select>
          <select v-model="grantForm.subject" class="min-h-11 rounded-lg border border-gray-300 px-3 py-2 text-sm md:min-h-9" required>
            <option value="" disabled>选择用户或 API Key</option>
            <option v-for="subject in activeSubjects" :key="subject.subject_type + subject.id" :value="`${subject.subject_type}:${subject.id}`">
              {{ subject.subject_type === 'user' ? '用户' : 'API Key' }} · {{ subject.name }}
            </option>
          </select>
          <label class="flex min-h-11 items-center gap-2 rounded-lg bg-gray-50 px-3 text-sm md:min-h-9 md:bg-transparent md:px-0"><input v-model="grantForm.can_connect" type="checkbox">连接测试</label>
          <label class="flex min-h-11 items-center gap-2 rounded-lg bg-gray-50 px-3 text-sm md:min-h-9 md:bg-transparent md:px-0"><input v-model="grantForm.can_execute" type="checkbox">SSH 命令</label>
          <label class="flex min-h-11 items-center gap-2 rounded-lg bg-gray-50 px-3 text-sm md:min-h-9 md:bg-transparent md:px-0"><input v-model="grantForm.can_manage_docker" type="checkbox">Docker 操作</label>
          <button class="btn btn-md btn-primary min-h-11 md:col-span-1 md:min-h-9" type="submit">保存授权</button>
        </form>
      </div>
      <div class="hidden overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm md:block">
        <table class="w-full min-w-[760px] text-left text-sm">
          <thead class="bg-gray-50 text-xs text-gray-500"><tr><th class="px-4 py-3">主机</th><th class="px-4 py-3">主体</th><th class="px-4 py-3">权限</th><th class="px-4 py-3">状态</th><th class="px-4 py-3">操作</th></tr></thead>
          <tbody>
            <tr v-for="grant in grants" :key="grant.id" class="border-t border-gray-100">
              <td class="px-4 py-3">{{ grant.host_name }}</td>
              <td class="px-4 py-3">{{ grant.subject_type === 'user' ? '用户' : 'API Key' }} · {{ grant.subject_name }}</td>
              <td class="px-4 py-3 text-xs">{{ grantPermissions(grant) }}</td>
              <td class="px-4 py-3">{{ grant.is_active && !grant.is_expired ? '有效' : '无效' }}</td>
              <td class="px-4 py-3"><button class="text-xs text-red-600" @click="removeGrant(grant)">撤销</button></td>
            </tr>
            <tr v-if="grants.length === 0"><td colspan="5" class="px-4 py-8 text-center text-gray-400">暂无授权</td></tr>
          </tbody>
        </table>
      </div>
      <div class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm md:hidden">
        <p v-if="grants.length === 0" class="px-4 py-8 text-center text-sm text-gray-400">暂无授权</p>
        <ul v-else class="divide-y divide-gray-100">
          <li v-for="grant in grants" :key="grant.id" class="p-4">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="truncate font-medium text-gray-900">{{ grant.host_name }}</div>
                <div class="mt-1 text-sm text-gray-600">{{ grant.subject_type === 'user' ? '用户' : 'API Key' }} · {{ grant.subject_name }}</div>
              </div>
              <span class="shrink-0 rounded-full px-2 py-1 text-xs" :class="grant.is_active && !grant.is_expired ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-500'">
                {{ grant.is_active && !grant.is_expired ? '有效' : '无效' }}
              </span>
            </div>
            <div class="mt-2 text-xs text-gray-500">权限：{{ grantPermissions(grant) }}</div>
            <button class="btn btn-sm mt-3 min-h-11 w-full touch-manipulation border border-red-200 text-red-600 hover:bg-red-50" @click="removeGrant(grant)">撤销授权</button>
          </li>
        </ul>
      </div>
    </section>

    <section v-else-if="tab === 'users' && context.is_admin" class="grid gap-4 lg:grid-cols-[360px_1fr]">
      <form class="rounded-xl border border-gray-200 bg-white p-4 shadow-sm" @submit.prevent="createUser">
        <h2 class="font-semibold text-gray-900">创建系统用户</h2>
        <div class="mt-4 space-y-3">
          <input v-model.trim="userForm.username" class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="用户名" required minlength="2">
          <input v-model="userForm.password" type="password" class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="初始密码（至少 8 位）" required minlength="8">
          <select v-model="userForm.role" class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"><option value="user">普通用户</option><option value="admin">管理员</option></select>
          <button class="btn btn-md btn-primary w-full">创建用户</button>
        </div>
      </form>
      <div class="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div class="border-b border-gray-200 px-4 py-3 font-semibold">系统用户</div>
        <div class="divide-y divide-gray-100">
          <div v-for="user in userSubjects" :key="user.id" class="flex items-center justify-between gap-3 px-4 py-3">
            <div><div class="font-medium">{{ user.name }}</div><div class="text-xs text-gray-400">{{ user.role === 'admin' ? '管理员' : '普通用户' }}</div></div>
            <button class="btn btn-sm btn-outline min-h-11 touch-manipulation sm:min-h-8" @click="toggleUser(user)">{{ user.is_active ? '禁用' : '启用' }}</button>
          </div>
        </div>
      </div>
    </section>

    <section v-else-if="tab === 'audit'" class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <div class="flex items-center justify-between border-b border-gray-200 px-4 py-3">
        <h2 class="font-semibold">访问审计</h2>
        <button class="btn btn-sm btn-outline min-h-11 touch-manipulation sm:min-h-8" @click="loadAudit">刷新</button>
      </div>
      <div class="hidden overflow-x-auto md:block">
      <table class="w-full min-w-[900px] text-left text-sm">
        <thead class="bg-gray-50 text-xs text-gray-500"><tr><th class="px-4 py-3">时间</th><th class="px-4 py-3">操作者</th><th class="px-4 py-3">主机</th><th class="px-4 py-3">动作</th><th class="px-4 py-3">目标/命令</th><th class="px-4 py-3">结果</th><th class="px-4 py-3">来源 IP</th></tr></thead>
        <tbody>
          <tr v-for="log in auditLogs" :key="log.id" class="border-t border-gray-100">
            <td class="whitespace-nowrap px-4 py-3 text-xs">{{ formatDate(log.created_at) }}</td><td class="px-4 py-3">{{ log.actor_name }}</td><td class="px-4 py-3">{{ log.host_name }}</td><td class="px-4 py-3">{{ actionLabel(log.action) }}</td>
            <td class="max-w-xs truncate px-4 py-3 font-mono text-xs" :title="log.command || log.target">{{ log.command || log.target || '-' }}</td>
            <td class="px-4 py-3" :class="log.status === 'success' ? 'text-emerald-600' : 'text-red-600'">{{ log.status }}<span v-if="log.exit_code !== null"> ({{ log.exit_code }})</span></td><td class="px-4 py-3 text-xs">{{ log.client_ip || '-' }}</td>
          </tr>
          <tr v-if="auditLogs.length === 0"><td colspan="7" class="px-4 py-8 text-center text-gray-400">暂无审计记录</td></tr>
        </tbody>
      </table>
      </div>
      <div class="md:hidden">
        <p v-if="auditLogs.length === 0" class="px-4 py-8 text-center text-sm text-gray-400">暂无审计记录</p>
        <ul v-else class="divide-y divide-gray-100">
          <li v-for="log in auditLogs" :key="log.id" class="p-4">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <span class="font-medium text-gray-900">{{ log.host_name }}</span>
                  <span class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{{ actionLabel(log.action) }}</span>
                </div>
                <div class="mt-1 text-xs text-gray-500">{{ log.actor_name }} · {{ formatDate(log.created_at) }}</div>
              </div>
              <span class="shrink-0 text-sm font-medium" :class="log.status === 'success' ? 'text-emerald-600' : 'text-red-600'">
                {{ log.status }}
              </span>
            </div>
            <div v-if="log.command || log.target" class="mt-3 break-all rounded-lg bg-gray-50 p-2 font-mono text-xs text-gray-600">{{ log.command || log.target }}</div>
            <div class="mt-2 text-xs text-gray-400">来源：{{ log.client_ip || '-' }}<span v-if="log.exit_code !== null"> · exit {{ log.exit_code }}</span></div>
          </li>
        </ul>
      </div>
    </section>

    <section v-else-if="tab === 'guide'" class="rounded-xl border border-gray-200 bg-white p-3 shadow-sm sm:p-5">
      <h2 class="font-semibold text-gray-900">统一网关访问</h2>
      <p class="mt-2 text-sm text-gray-600">系统用户使用自己的登录密码，API 调用方使用已授权 API Key；两者都不会接触目标主机真实凭据。</p>
      <h3 class="mt-5 text-sm font-semibold text-gray-800">SSH 跳板端口 {{ gatewayInfo.port || 2222 }}</h3>
      <p v-if="gatewayInfo.host_key_fingerprint" class="mt-1 break-all font-mono text-xs text-gray-500">主机指纹：{{ gatewayInfo.host_key_fingerprint }}</p>
      <pre class="mt-2 max-w-full overflow-x-auto rounded-lg bg-gray-950 p-3 text-[11px] text-gray-100 sm:p-4 sm:text-xs"># 系统用户密码
ssh -p {{ gatewayInfo.port || 2222 }} '系统用户#SSH主机名'@平台地址

# API Key 作为 SSH 密码
ssh -p {{ gatewayInfo.port || 2222 }} 'SSH主机名'@平台地址</pre>
      <h3 class="mt-5 text-sm font-semibold text-gray-800">Docker HTTPS 网关端口 {{ gatewayInfo.docker_gateway?.port || 23750 }}</h3>
      <p v-if="gatewayInfo.docker_gateway?.certificate_fingerprint" class="mt-1 break-all font-mono text-xs text-gray-500">证书指纹：{{ gatewayInfo.docker_gateway.certificate_fingerprint }}</p>
      <pre class="mt-2 max-w-full overflow-x-auto rounded-lg bg-gray-950 p-3 text-[11px] text-gray-100 sm:p-4 sm:text-xs"># 下载并信任网关 CA
curl -u '系统用户#Docker主机名:系统用户密码' \
  --cacert frp-agent-docker-gateway-ca.pem \
  https://平台地址:{{ gatewayInfo.docker_gateway?.port || 23750 }}/containers/json?all=true

# 主机名 + API Key
curl -u 'Docker主机名:API_KEY' \
  --cacert frp-agent-docker-gateway-ca.pem \
  https://平台地址:{{ gatewayInfo.docker_gateway?.port || 23750 }}/containers/json?all=true</pre>
      <button class="mt-2 inline-flex min-h-11 items-center text-sm font-medium text-blue-600 touch-manipulation hover:underline" @click="downloadDockerCa">下载 Docker 网关 CA 证书</button>
      <h3 class="mt-5 text-sm font-semibold text-gray-800">管理 REST API</h3>
      <pre class="mt-4 max-w-full overflow-x-auto rounded-lg bg-gray-950 p-3 text-[11px] text-gray-100 sm:p-4 sm:text-xs">curl -H "Authorization: Bearer &lt;API_KEY&gt;" \
  {{ origin }}/api/managed-hosts

curl -X POST -H "Authorization: Bearer &lt;API_KEY&gt;" \
  -H "Content-Type: application/json" \
  -d '{"command":"uptime","timeout":30}' \
  {{ origin }}/api/managed-hosts/&lt;HOST_ID&gt;/commands</pre>
    </section>
  </div>

  <Teleport to="body">
    <div v-if="aiPromptOpen" class="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-3">
      <div class="absolute inset-0 bg-black/50" @click="aiPromptOpen = false"></div>
      <div class="relative z-10 flex max-h-[94dvh] w-full max-w-2xl flex-col overflow-hidden rounded-t-2xl bg-white shadow-xl sm:max-h-[90vh] sm:rounded-xl">
        <div class="flex shrink-0 items-center justify-between border-b px-4 py-3 sm:px-5 sm:py-4">
          <div>
            <h2 class="font-semibold">AI curl 添加主机提示词</h2>
            <p class="mt-0.5 text-xs text-gray-500">填写公开连接信息，生成通过 API 添加主机的安全提示词。</p>
          </div>
          <button class="btn btn-icon btn-ghost min-h-11 min-w-11 shrink-0 touch-manipulation sm:min-h-9 sm:min-w-9" aria-label="关闭" @click="aiPromptOpen = false">✕</button>
        </div>
        <div class="min-h-0 space-y-4 overflow-y-auto p-4 pb-[max(1rem,env(safe-area-inset-bottom))] sm:p-5">
          <div class="grid grid-cols-2 gap-2 rounded-lg bg-gray-100 p-1">
            <button type="button" class="min-h-10 rounded-md px-3 py-2 text-sm" :class="aiPromptForm.host_type === 'ssh' ? 'bg-white font-medium text-blue-700 shadow-sm' : 'text-gray-500'" @click="setAiPromptType('ssh')">SSH 主机</button>
            <button type="button" class="min-h-10 rounded-md px-3 py-2 text-sm" :class="aiPromptForm.host_type === 'docker' ? 'bg-white font-medium text-violet-700 shadow-sm' : 'text-gray-500'" @click="setAiPromptType('docker')">Docker 主机</button>
          </div>
          <div class="grid gap-3 sm:grid-cols-2">
            <label class="text-sm">主机名称<input v-model.trim="aiPromptForm.name" class="mt-1 min-h-11 w-full rounded-lg border border-gray-300 px-3 py-2" placeholder="例如：生产服务器"></label>
            <label class="text-sm">地址<input v-model.trim="aiPromptForm.address" class="mt-1 min-h-11 w-full rounded-lg border border-gray-300 px-3 py-2" placeholder="域名或 IP"></label>
            <label class="text-sm">端口<input v-model.number="aiPromptForm.port" type="number" min="1" max="65535" class="mt-1 min-h-11 w-full rounded-lg border border-gray-300 px-3 py-2"></label>
            <label v-if="aiPromptForm.host_type === 'docker'" class="text-sm">Portainer Endpoint ID<input v-model.number="aiPromptForm.docker_endpoint_id" type="number" min="1" class="mt-1 min-h-11 w-full rounded-lg border border-gray-300 px-3 py-2"></label>
          </div>
          <p class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">
            提示词不会包含密码、私钥或 API Key；需要凭据时，AI 会要求你在安全表单中输入或上传。
          </p>
          <div>
            <div class="mb-1.5 text-sm font-medium text-gray-700">生成的提示词</div>
            <textarea :value="aiHostPrompt" readonly rows="15" class="w-full resize-none rounded-lg border border-gray-300 bg-gray-50 p-3 font-mono text-xs leading-5 text-gray-700"></textarea>
          </div>
          <div class="grid grid-cols-2 gap-2 sm:flex sm:justify-end">
            <button class="btn btn-md btn-outline min-h-11 touch-manipulation sm:min-h-9" @click="aiPromptOpen = false">关闭</button>
            <button class="btn btn-md btn-primary min-h-11 touch-manipulation sm:min-h-9" @click="copyAiHostPrompt($event.currentTarget)">复制提示词</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="connectionHost" class="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-3">
      <div class="absolute inset-0 bg-black/50" @click="connectionHost = null"></div>
      <div class="relative z-10 w-full max-w-2xl rounded-t-2xl bg-white shadow-xl sm:rounded-xl">
        <div class="flex items-center justify-between border-b px-4 py-3 sm:px-5 sm:py-4">
          <div class="min-w-0">
            <h2 class="truncate font-semibold">{{ connectionHost.name }} · 连接凭证</h2>
            <p class="mt-0.5 text-xs text-gray-500">{{ connectionHost.host_type === 'ssh' ? 'SSH 跳板连接' : 'Docker HTTPS 网关' }}</p>
          </div>
          <button class="btn btn-icon btn-ghost min-h-11 min-w-11 shrink-0 touch-manipulation sm:min-h-9 sm:min-w-9" aria-label="关闭" @click="connectionHost = null">✕</button>
        </div>
        <div class="space-y-4 p-4 pb-[max(1rem,env(safe-area-inset-bottom))] sm:p-5">
          <dl class="grid gap-2 rounded-xl border border-gray-200 bg-gray-50 p-3 text-sm sm:grid-cols-[7rem_1fr]">
            <dt class="text-gray-500">网关地址</dt>
            <dd class="flex min-w-0 items-center gap-2">
              <code class="min-w-0 flex-1 break-all text-xs text-gray-900">{{ connectionInfo.gateway }}</code>
              <button class="btn btn-icon-md btn-outline touch-manipulation sm:h-8 sm:w-8 sm:min-h-8 sm:min-w-8" aria-label="复制网关地址" title="复制网关地址" @click="copyCredentialValue(connectionInfo.gateway, $event.currentTarget)">
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>
            </dd>
            <dt class="text-gray-500">登录用户名</dt>
            <dd class="flex min-w-0 items-center gap-2">
              <code class="min-w-0 flex-1 break-all text-xs text-gray-900">{{ connectionInfo.loginName }}</code>
              <button class="btn btn-icon-md btn-outline-primary touch-manipulation sm:h-8 sm:w-8 sm:min-h-8 sm:min-w-8" aria-label="复制登录用户名" title="复制登录用户名" @click="copyCredentialValue(connectionInfo.loginName, $event.currentTarget)">
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>
            </dd>
            <dt class="text-gray-500">密码</dt>
            <dd class="text-gray-900">{{ connectionInfo.passwordHint }}</dd>
            <template v-if="connectionHost.host_type === 'ssh' && gatewayInfo.host_key_fingerprint">
              <dt class="text-gray-500">网关指纹</dt>
              <dd class="flex min-w-0 items-center gap-2">
                <code class="min-w-0 flex-1 break-all text-xs text-gray-900">{{ gatewayInfo.host_key_fingerprint }}</code>
                <button class="btn btn-icon-md btn-outline touch-manipulation sm:h-8 sm:w-8 sm:min-h-8 sm:min-w-8" aria-label="复制网关指纹" title="复制网关指纹" @click="copyCredentialValue(gatewayInfo.host_key_fingerprint, $event.currentTarget)">
                  <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                </button>
              </dd>
            </template>
          </dl>
          <div>
            <div class="mb-1.5 text-sm font-medium text-gray-700">终端命令</div>
            <pre class="max-h-48 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-gray-950 p-3 text-xs text-gray-100">{{ connectionInfo.command }}</pre>
          </div>
          <p v-if="connectionHost.host_type === 'docker'" class="text-xs leading-5 text-gray-500">
            Docker 网关命令需要先下载 CA 证书，并将证书保存为 <code>frp-agent-docker-gateway-ca.pem</code>。
          </p>
          <div class="grid gap-2 sm:flex sm:justify-end">
            <button v-if="connectionHost.host_type === 'docker'" class="btn btn-md btn-outline min-h-11 touch-manipulation sm:min-h-9" @click="downloadDockerCa">下载 CA 证书</button>
            <button class="btn btn-md btn-primary min-h-11 touch-manipulation sm:min-h-9" @click="copyConnectionCommand(connectionHost, $event.currentTarget)">复制命令</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="hostEditor" class="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-4">
      <div class="absolute inset-0 bg-black/40" @click="hostEditor = false"></div>
      <div class="relative z-10 flex max-h-[94dvh] w-full max-w-2xl flex-col overflow-hidden rounded-t-2xl bg-white shadow-xl sm:max-h-[92vh] sm:rounded-xl">
        <div class="flex shrink-0 items-center justify-between border-b px-4 py-3 sm:px-5 sm:py-4"><h2 class="font-semibold">{{ editingHostId ? '编辑主机' : '添加主机' }}</h2><button class="btn btn-icon btn-ghost min-h-11 min-w-11 touch-manipulation sm:min-h-9 sm:min-w-9" aria-label="关闭" @click="hostEditor = false">✕</button></div>
        <form class="min-h-0 space-y-4 overflow-y-auto p-4 pb-[max(1rem,env(safe-area-inset-bottom))] sm:p-5" @submit.prevent="saveHost">
          <div class="grid grid-cols-2 gap-2 rounded-lg bg-gray-100 p-1">
            <button type="button" class="rounded-md px-3 py-2 text-sm" :class="hostForm.host_type === 'ssh' ? 'bg-white font-medium text-blue-700 shadow-sm' : 'text-gray-500'" @click="setHostType('ssh')">SSH 主机</button>
            <button type="button" class="rounded-md px-3 py-2 text-sm" :class="hostForm.host_type === 'docker' ? 'bg-white font-medium text-violet-700 shadow-sm' : 'text-gray-500'" @click="setHostType('docker')">Docker 主机</button>
          </div>
          <div class="grid gap-3 sm:grid-cols-2">
            <label class="text-sm">名称<input v-model.trim="hostForm.name" class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" required></label>
            <label class="text-sm">地址<input v-model.trim="hostForm.address" class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" placeholder="主机名或 IP" required></label>
            <label class="text-sm">端口<input v-model.number="hostForm.port" type="number" min="1" max="65535" class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" required></label>
            <label class="flex items-center gap-2 pt-6 text-sm"><input v-model="hostForm.is_active" type="checkbox">启用资源</label>
          </div>
          <template v-if="hostForm.host_type === 'ssh'">
            <SshCredentialForm v-model="hostForm.credential_id" />
            <label class="block text-sm">SSH 主机指纹（可选）<input v-model.trim="hostForm.host_key_fingerprint" class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-xs" placeholder="SHA256:..."><span class="mt-1 block text-xs text-gray-400">留空时首次连接自动记录，后续严格校验。</span></label>
          </template>
          <template v-else>
            <div class="rounded-lg border border-violet-100 bg-violet-50/40 p-3">
              <label class="text-sm">Portainer 凭据<select v-model.number="hostForm.docker_credential_id" class="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2" required><option :value="0" disabled>请选择凭据</option><option v-for="cred in dockerCredentials" :key="cred.id" :value="cred.id">{{ cred.name }}（{{ cred.auth_type === 'api_key' ? 'API Key' : '用户名/密码' }}）</option></select></label>
              <button type="button" class="mt-2 text-xs font-medium text-violet-700" @click="dockerCredentialEditor = !dockerCredentialEditor">+ 新建 Docker 凭据</button>
              <div v-if="dockerCredentialEditor" class="mt-3 space-y-2 border-t border-violet-100 pt-3">
                <input v-model.trim="dockerCredForm.name" class="w-full rounded-lg border px-3 py-2 text-sm" placeholder="凭据名称">
                <select v-model="dockerCredForm.auth_type" class="w-full rounded-lg border px-3 py-2 text-sm"><option value="api_key">Portainer API Key</option><option value="password">用户名/密码</option></select>
                <input v-if="dockerCredForm.auth_type === 'api_key'" v-model="dockerCredForm.api_key" type="password" class="w-full rounded-lg border px-3 py-2 text-sm" placeholder="ptr_...">
                <template v-else><input v-model.trim="dockerCredForm.username" class="w-full rounded-lg border px-3 py-2 text-sm" placeholder="Portainer 用户名"><input v-model="dockerCredForm.password" type="password" class="w-full rounded-lg border px-3 py-2 text-sm" placeholder="Portainer 密码"></template>
                <textarea v-model="dockerCredForm.ca_cert" rows="3" class="w-full rounded-lg border px-3 py-2 font-mono text-xs" placeholder="自定义 CA 证书（可选）"></textarea>
                <button type="button" class="btn btn-sm border border-violet-300 bg-white text-violet-700" @click="saveDockerCredential">保存 Docker 凭据</button>
              </div>
            </div>
            <div class="grid gap-3 sm:grid-cols-2">
              <label class="text-sm">Portainer Endpoint ID<input v-model.number="hostForm.docker_endpoint_id" type="number" min="1" class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" placeholder="例如 1" required></label>
              <div class="space-y-2 pt-1">
                <label class="flex items-center gap-2 text-sm"><input v-model="hostForm.docker_use_tls" type="checkbox">使用 HTTPS（通常端口 9443）</label>
                <label v-if="hostForm.docker_use_tls" class="flex items-center gap-2 text-sm"><input v-model="hostForm.docker_verify_tls" type="checkbox">校验 Portainer TLS 证书</label>
              </div>
            </div>
          </template>
          <label class="block text-sm">标签<input v-model.trim="hostForm.tags" class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" placeholder="生产, 华东"></label>
          <label class="block text-sm">描述<textarea v-model.trim="hostForm.description" rows="2" class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2"></textarea></label>
          <div class="grid grid-cols-2 gap-2 border-t pt-4 sm:flex sm:justify-end"><button type="button" class="btn btn-md btn-outline min-h-11 touch-manipulation sm:min-h-9" @click="hostEditor = false">取消</button><button class="btn btn-md btn-primary min-h-11 touch-manipulation sm:min-h-9">保存</button></div>
        </form>
      </div>
    </div>

    <div v-if="consoleHost" class="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-3">
      <div class="absolute inset-0 bg-black/50" @click="consoleHost = null"></div>
      <div class="relative z-10 w-full max-w-3xl rounded-t-2xl bg-white shadow-xl sm:rounded-xl">
        <div class="flex items-center justify-between border-b px-4 py-3 sm:px-5 sm:py-4"><h2 class="min-w-0 truncate font-semibold">{{ consoleHost.name }} · 命令终端</h2><button class="btn btn-icon btn-ghost min-h-11 min-w-11 shrink-0 touch-manipulation sm:min-h-9 sm:min-w-9" aria-label="关闭" @click="consoleHost = null">✕</button></div>
        <form class="p-4 pb-[max(1rem,env(safe-area-inset-bottom))] sm:p-5" @submit.prevent="runCommand">
          <div class="grid gap-2 sm:flex"><input v-model="command" class="min-h-11 min-w-0 flex-1 rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm sm:min-h-9" placeholder="uptime" required><button class="btn btn-md btn-primary min-h-11 touch-manipulation sm:min-h-9" :disabled="operating">执行</button></div>
          <pre class="mt-4 min-h-44 max-h-[50dvh] overflow-auto whitespace-pre-wrap break-all rounded-lg bg-gray-950 p-3 text-xs text-gray-100 sm:max-h-96 sm:p-4">{{ commandOutput || '等待执行…' }}</pre>
        </form>
      </div>
    </div>

    <div v-if="dockerHost" class="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-3">
      <div class="absolute inset-0 bg-black/50" @click="dockerHost = null"></div>
      <div class="relative z-10 flex max-h-[94dvh] w-full max-w-4xl flex-col overflow-hidden rounded-t-2xl bg-white shadow-xl sm:max-h-[90vh] sm:rounded-xl">
        <div class="flex shrink-0 items-center justify-between border-b px-4 py-3 sm:px-5 sm:py-4"><h2 class="min-w-0 truncate font-semibold">{{ dockerHost.name }} · 容器</h2><button class="btn btn-icon btn-ghost min-h-11 min-w-11 shrink-0 touch-manipulation sm:min-h-9 sm:min-w-9" aria-label="关闭" @click="dockerHost = null">✕</button></div>
        <div class="min-h-0 overflow-y-auto p-3 pb-[max(1rem,env(safe-area-inset-bottom))] sm:p-4">
          <div v-if="operating" class="py-8 text-center text-sm text-gray-500">正在通过 Portainer API 读取容器...</div>
          <div v-else class="space-y-2">
            <div v-for="container in containers" :key="container.Id" class="flex flex-col gap-2 rounded-lg border p-3 sm:flex-row sm:items-center">
              <div class="min-w-0 flex-1"><div class="font-medium">{{ (container.Names || []).join(', ').replaceAll('/', '') || container.Id?.slice(0, 12) }}</div><div class="truncate text-xs text-gray-500">{{ container.Image }} · {{ container.Status }}</div></div>
              <div class="grid grid-cols-3 gap-2 sm:flex"><button v-for="action in ['start','stop','restart']" :key="action" class="btn btn-sm btn-outline min-h-11 touch-manipulation sm:min-h-8" @click="dockerAction(container, action)">{{ {start:'启动',stop:'停止',restart:'重启'}[action] }}</button></div>
            </div>
            <div v-if="containers.length === 0" class="py-8 text-center text-sm text-gray-400">暂无容器</div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import SshCredentialForm from '@/components/SshCredentialForm.vue'
import { sshCredentialsApi } from '@/api/sshCredentials'
import { dockerCredentialsApi, managedHostsApi } from '@/api/managedHosts'
import { copyWithTooltip } from '@/composables/useCopyTooltip'

const hosts = ref([])
const context = reactive({ is_admin: false, actor_type: 'user', actor_name: '' })
const gatewayInfo = ref({})
const subjects = ref([])
const grants = ref([])
const auditLogs = ref([])
const dockerCredentials = ref([])
const loading = ref(true)
const operating = ref(false)
const tab = ref('hosts')
const aiPromptOpen = ref(false)
const hostEditor = ref(false)
const dockerCredentialEditor = ref(false)
const editingHostId = ref(null)
const connectionHost = ref(null)
const consoleHost = ref(null)
const dockerHost = ref(null)
const containers = ref([])
const command = ref('uptime')
const commandOutput = ref('')
const origin = window.location.origin

const tabs = computed(() => [
  { key: 'hosts', label: '主机列表' },
  ...(context.is_admin ? [{ key: 'access', label: '访问授权' }, { key: 'users', label: '系统用户' }] : []),
  { key: 'audit', label: '访问审计' },
  { key: 'guide', label: 'API 访问' }
])
const activeSubjects = computed(() => subjects.value.filter(item => item.is_active))
const userSubjects = computed(() => subjects.value.filter(item => item.subject_type === 'user'))
const connectionInfo = computed(() => connectionHost.value ? buildConnectionInfo(connectionHost.value) : {})
const aiHostPrompt = computed(() => {
  const type = aiPromptForm.host_type === 'ssh' ? 'SSH' : 'Docker / Portainer'
  const name = aiPromptForm.name || '<请先向我确认主机名称>'
  const address = aiPromptForm.address || '<请先向我确认域名或 IP>'
  const common = [
    `请优先使用 curl 调用 API，把下面的 ${type} 主机安全地接入 FRP-AGENT 主机管理系统。`,
    '',
    `平台 API 地址：${origin}/api`,
    `资源类型：${type}`,
    `主机名称：${name}`,
    `目标地址：${address}`,
    `目标端口：${aiPromptForm.port}`,
    ...(aiPromptForm.host_type === 'docker' ? [`Portainer Endpoint ID：${aiPromptForm.docker_endpoint_id}`] : []),
    '',
    '执行要求：',
    '1. 全程优先使用 curl 调用 REST API，不要通过浏览器表单添加；请求失败时输出 HTTP 状态和已脱敏的错误信息。',
    '2. SSH 主机与 Docker 主机是两种独立资源类型，不得混用凭据或字段。',
    '3. 管理接口需要管理员身份。使用我预先准备并设置为 0600 权限的 curl 配置文件：curl --config "$FRP_CURL_CONFIG"；不得索取、猜测或输出管理员密码，也不得把密码放入 URL、命令行参数或聊天记录。',
    '4. 先用 GET /api/managed-hosts 和对应凭据接口查询现有数据。如果同名主机或凭据已存在，展示脱敏后的差异并征得我确认，不要直接覆盖或删除。',
    '5. 需要新凭据时，让我把凭据 JSON 保存到仅当前用户可读的本地文件，再使用 curl --data-binary @"$CREDENTIAL_JSON" 上传；不要读取后回显密码、私钥、私钥口令或 Portainer API Key。',
  ]
  const specific = aiPromptForm.host_type === 'ssh'
    ? [
        '6. SSH 凭据接口为 /api/ssh-credentials。取得 credential_id 后，POST /api/managed-hosts，JSON 中使用 host_type="ssh"、credential_id、名称、地址和端口。',
        '7. 从创建响应取得主机 id，再 POST /api/managed-hosts/{id}/test。首次连接返回服务器指纹时先让我核对；测试成功后只报告主机状态、登录用户和指纹。',
      ]
    : [
        '6. Portainer 凭据接口为 /api/docker-credentials。取得 docker_credential_id 后，POST /api/managed-hosts，JSON 中使用 host_type="docker"、docker_credential_id、docker_endpoint_id、docker_use_tls、docker_verify_tls、名称、地址和端口。',
        '7. 从创建响应取得主机 id，再 POST /api/managed-hosts/{id}/test，并 GET /api/managed-hosts/{id}/docker/containers。只报告 Endpoint 状态和容器数量，不要执行启动、停止、重启或删除操作。',
      ]
  return [...common, ...specific, '8. 每次 curl 都使用 --fail-with-body --silent --show-error。完成后只汇报调用过的接口、新增或更新的资源、测试结果和需要我处理的事项。'].join('\n')
})

const emptyHost = () => ({ name: '', address: '', port: 22, host_type: 'ssh', credential_id: 0, docker_credential_id: 0, docker_use_tls: true, docker_verify_tls: true, docker_endpoint_id: 1, host_key_fingerprint: '', tags: '', description: '', is_active: true })
const hostForm = reactive(emptyHost())
const dockerCredForm = reactive({ name: '', auth_type: 'api_key', username: '', password: '', api_key: '', ca_cert: '' })
const grantForm = reactive({ host_id: 0, subject: '', can_connect: true, can_execute: false, can_manage_docker: false })
const userForm = reactive({ username: '', password: '', role: 'user' })
const aiPromptForm = reactive({ host_type: 'ssh', name: '', address: '', port: 22, docker_endpoint_id: 1 })

async function loadHosts() { hosts.value = await managedHostsApi.list() }
async function loadAdminData() {
  if (!context.is_admin) return
  ;[subjects.value, grants.value, dockerCredentials.value] = await Promise.all([managedHostsApi.subjects(), managedHostsApi.grants(), dockerCredentialsApi.list()])
}
async function loadAudit() { auditLogs.value = await managedHostsApi.audit({ limit: 200 }) }
async function load() {
  loading.value = true
  try {
    Object.assign(context, await managedHostsApi.context())
    const [, , gateway] = await Promise.all([loadHosts(), loadAudit(), managedHostsApi.gatewayInfo()])
    gatewayInfo.value = gateway || {}
    await loadAdminData()
  } catch (e) { alert(e.message) } finally { loading.value = false }
}

function setHostType(type) {
  if (hostForm.host_type !== type) {
    hostForm.host_type = type
    hostForm.port = type === 'ssh' ? 22 : 9443
  }
}
function setAiPromptType(type) {
  aiPromptForm.host_type = type
  aiPromptForm.port = type === 'ssh' ? 22 : 9000
}
function openAiHostPrompt() {
  Object.assign(aiPromptForm, { host_type: 'ssh', name: '', address: '', port: 22, docker_endpoint_id: 1 })
  aiPromptOpen.value = true
}
async function copyAiHostPrompt(trigger) {
  if (!await copyWithTooltip(aiHostPrompt.value, trigger)) alert('复制失败，请手动选择提示词')
}
function openHostEditor(host = null) {
  Object.assign(hostForm, emptyHost())
  editingHostId.value = host?.id || null
  if (host) Object.assign(hostForm, {
    name: host.name, address: host.address, port: host.port, host_type: host.host_type,
    credential_id: host.credential_id || 0, docker_credential_id: host.docker_credential_id || 0,
    docker_use_tls: host.docker_use_tls, docker_verify_tls: host.docker_verify_tls,
    docker_endpoint_id: host.docker_endpoint_id || 1, host_key_fingerprint: host.host_key_fingerprint || '',
    tags: host.tags || '', description: host.description || '', is_active: host.is_active
  })
  hostEditor.value = true
}
async function saveHost() {
  const payload = { ...hostForm, credential_id: hostForm.host_type === 'ssh' ? hostForm.credential_id : null, docker_credential_id: hostForm.host_type === 'docker' ? hostForm.docker_credential_id : null, host_key_fingerprint: hostForm.host_key_fingerprint || null }
  try {
    if (editingHostId.value) await managedHostsApi.update(editingHostId.value, payload)
    else await managedHostsApi.create(payload)
    hostEditor.value = false
    await loadHosts()
  } catch (e) { alert(e.message) }
}
async function removeHost(host) {
  if (!confirm(`确定删除主机“${host.name}”及其授权、审计记录？`)) return
  try { await managedHostsApi.remove(host.id); await loadHosts(); await loadAdminData() } catch (e) { alert(e.message) }
}
async function testHost(host) {
  try { const result = await managedHostsApi.test(host.id); alert(result.success ? `连接成功（${result.duration_ms}ms）` : result.stderr); await loadHosts(); await loadAudit() } catch (e) { alert(e.message) }
}
function openConsole(host) { consoleHost.value = host; command.value = 'uptime'; commandOutput.value = '' }
async function runCommand() {
  operating.value = true
  try { const result = await managedHostsApi.execute(consoleHost.value.id, { command: command.value, timeout: 30 }); commandOutput.value = [`exit_code=${result.exit_code}`, result.stdout, result.stderr].filter(Boolean).join('\n') } catch (e) { commandOutput.value = e.message } finally { operating.value = false; loadAudit() }
}
async function openDocker(host) { dockerHost.value = host; await loadContainers() }
async function loadContainers() {
  operating.value = true
  try { containers.value = (await managedHostsApi.containers(dockerHost.value.id)).containers || [] } catch (e) { alert(e.message) } finally { operating.value = false; loadAudit() }
}
async function dockerAction(container, action) {
  const name = (container.Names || [container.Id])[0].replace('/', '')
  if (!confirm(`确定${{start:'启动',stop:'停止',restart:'重启'}[action]}容器 ${name}？`)) return
  try { await managedHostsApi.dockerAction(dockerHost.value.id, { action, container: name, timeout: 30 }); await loadContainers() } catch (e) { alert(e.message) }
}
async function saveDockerCredential() {
  try {
    const created = await dockerCredentialsApi.create({ ...dockerCredForm })
    dockerCredentials.value = await dockerCredentialsApi.list()
    hostForm.docker_credential_id = created.id
    dockerCredentialEditor.value = false
    Object.assign(dockerCredForm, { name: '', auth_type: 'api_key', username: '', password: '', api_key: '', ca_cert: '' })
  } catch (e) { alert(e.message) }
}
async function saveGrant() {
  const [subject_type, rawId] = grantForm.subject.split(':')
  try {
    await managedHostsApi.createGrant({ host_id: grantForm.host_id, subject_type, subject_id: Number(rawId), can_connect: grantForm.can_connect, can_execute: grantForm.can_execute, can_manage_docker: grantForm.can_manage_docker })
    grants.value = await managedHostsApi.grants()
  } catch (e) { alert(e.message) }
}
async function removeGrant(grant) { if (confirm('确定撤销该授权？')) { try { await managedHostsApi.removeGrant(grant.id); grants.value = await managedHostsApi.grants() } catch (e) { alert(e.message) } } }
async function createUser() {
  try { await managedHostsApi.createUser({ ...userForm }); Object.assign(userForm, { username: '', password: '', role: 'user' }); subjects.value = await managedHostsApi.subjects() } catch (e) { alert(e.message) }
}
async function toggleUser(user) {
  try { await managedHostsApi.updateUser(user.id, { is_active: !user.is_active }); subjects.value = await managedHostsApi.subjects() } catch (e) { alert(e.message) }
}
function grantPermissions(g) { return [g.can_connect && '连接', g.can_execute && 'SSH 命令', g.can_manage_docker && 'Docker'].filter(Boolean).join('、') || '无' }
function statusDot(s) { return s === 'online' ? 'bg-emerald-500' : s === 'offline' || s === 'error' ? 'bg-red-500' : 'bg-gray-300' }
function formatDate(value) { return value ? new Date(value).toLocaleString('zh-CN') : '-' }
function actionLabel(value) { return ({ connection_test: '连接测试', execute_command: '执行命令', ssh_gateway_session: 'SSH 跳板会话', docker_gateway_request: 'Docker 网关请求', docker_list: '查询容器', docker_start: '启动容器', docker_stop: '停止容器', docker_restart: '重启容器' })[value] || value }
function shellQuote(value) { return `'${String(value).replaceAll("'", "'\\''")}'` }
function buildConnectionInfo(host) {
  const gatewayHost = window.location.hostname || '平台地址'
  const isApiKey = context.actor_type === 'api_key'
  const loginName = isApiKey ? host.name : `${context.actor_name}#${host.name}`
  const port = host.host_type === 'ssh'
    ? (gatewayInfo.value.port || 2222)
    : (gatewayInfo.value.docker_gateway?.port || 23750)
  return {
    gateway: `${gatewayHost}:${port}`,
    loginName,
    passwordHint: isApiKey ? '已授权的 API Key' : '当前系统用户的登录密码',
    command: host.host_type === 'ssh'
      ? `ssh -p ${port} ${shellQuote(loginName)}@${gatewayHost}`
      : `curl -u ${shellQuote(loginName)} --cacert frp-agent-docker-gateway-ca.pem ${shellQuote(`https://${gatewayHost}:${port}/containers/json?all=true`)}`
  }
}
function openConnectionDetails(host) { connectionHost.value = host }
async function copyCredentialValue(value, trigger) {
  if (!await copyWithTooltip(value, trigger)) alert('复制失败，请手动选择该字段')
}
async function copyConnectionCommand(host, trigger) {
  if (!await copyWithTooltip(buildConnectionInfo(host).command, trigger)) alert('复制失败，请在“API 访问”页手动复制连接命令')
}
async function downloadDockerCa() {
  try {
    const blob = await managedHostsApi.dockerGatewayCa()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'frp-agent-docker-gateway-ca.pem'
    link.click()
    URL.revokeObjectURL(url)
  } catch (e) { alert(e.message) }
}

watch(tab, value => { if (value === 'audit') loadAudit() })
onMounted(load)
</script>
