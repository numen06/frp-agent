<template>
  <div>
    <div class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <div class="flex flex-col gap-3 border-b border-gray-200 px-3 py-3 sm:px-5 sm:py-3.5 md:flex-row md:items-center md:justify-between md:gap-2">
        <h3 class="text-base font-semibold text-gray-900">API Key 管理</h3>
        <div class="flex w-full flex-wrap gap-2 md:w-auto md:justify-end">
          <button
            type="button"
            class="btn btn-sm btn-primary min-h-10 flex-1 sm:min-h-8 sm:flex-none"
            @click.stop="openCreateDialog"
          >
            <svg class="h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14M5 12h14" />
            </svg>
            创建密钥
          </button>
        </div>
      </div>
      <div v-if="loading" class="p-5">
        <div class="flex items-center justify-center gap-2 py-4 text-center text-sm text-gray-600">
          <span class="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" role="status" aria-label="加载中"></span>
          <span>加载中...</span>
        </div>
      </div>
      <template v-else>
      <div class="hidden overflow-x-auto md:block">
        <table class="w-full border-collapse text-left text-sm text-gray-700">
          <thead>
            <tr>
              <th class="border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500" style="min-width:140px">描述</th>
              <th class="border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500" style="min-width:200px">密钥</th>
              <th class="whitespace-nowrap border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500" style="min-width:160px">过期时间</th>
              <th class="border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500" style="min-width:70px">状态</th>
              <th class="whitespace-nowrap border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500" style="min-width:160px">创建时间</th>
              <th class="whitespace-nowrap border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500" style="min-width:160px">最后使用</th>
              <th class="whitespace-nowrap border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500" style="min-width:180px">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="keys.length === 0">
              <td colspan="7" class="py-4 text-center text-sm text-gray-500">
                暂无 API Key，点击上方按钮创建
              </td>
            </tr>
            <tr v-else v-for="key in keys" :key="key.id" :class="rowClass(key)">
              <td class="border-b border-gray-100 px-4 py-3 align-middle">
                <div class="flex items-center gap-2">
                  <span class="truncate" :title="key.description">{{ key.description }}</span>
                  <span
                    v-if="apiKeysStore.selectedKeyId === key.id"
                    class="inline-flex shrink-0 items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800"
                  >默认</span>
                </div>
              </td>
              <td class="border-b border-gray-100 px-4 py-3 align-middle">
                <div class="flex items-center gap-1">
                  <code class="flex-1 truncate text-xs text-gray-600">{{ key.key }}</code>
                  <button
                    class="inline-flex shrink-0 items-center justify-center rounded p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
                    title="复制完整密钥"
                    @click.stop="copyFullKey(key, $event)"
                  >
                    <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <rect x="9" y="9" width="13" height="13" rx="2"></rect>
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                  </button>
                </div>
              </td>
              <td class="whitespace-nowrap border-b border-gray-100 px-4 py-3 align-middle">
                <span v-if="key.expires_at">{{ formatDateTime(key.expires_at) }}</span>
                <span v-else class="text-gray-400">永不过期</span>
              </td>
              <td class="border-b border-gray-100 px-4 py-3 align-middle">
                <span v-if="key.is_expired" class="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">已过期</span>
                <span v-else-if="!key.is_active" class="inline-flex items-center rounded-full bg-gray-200 px-2.5 py-0.5 text-xs font-medium text-gray-700">已禁用</span>
                <span v-else class="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800">正常</span>
              </td>
              <td class="whitespace-nowrap border-b border-gray-100 px-4 py-3 align-middle">{{ formatDateTime(key.created_at) }}</td>
              <td class="whitespace-nowrap border-b border-gray-100 px-4 py-3 align-middle">
                <span v-if="key.last_used_at">{{ formatDateTime(key.last_used_at) }}</span>
                <span v-else class="text-gray-400">从未使用</span>
              </td>
              <td class="whitespace-nowrap border-b border-gray-100 px-4 py-3 align-middle">
                <div class="flex items-center gap-1.5">
                  <button
                    class="inline-flex h-8 items-center justify-center rounded-lg border px-2.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40"
                    :class="apiKeysStore.selectedKeyId === key.id ? 'border-blue-200 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-600 hover:bg-gray-50'"
                    :disabled="!key.is_active || key.is_expired || apiKeysStore.selectedKeyId === key.id"
                    title="设为默认"
                    @click="setDefaultKey(key)"
                  >默认</button>
                  <button
                    class="btn btn-icon-sm btn-icon-muted disabled:opacity-40"
                    :disabled="key.is_expired"
                    title="编辑"
                    @click="editKey(key)"
                  >
                    <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M16.862 3.487a2.25 2.25 0 1 1 3.182 3.182L8.25 18.463 4 20l1.537-4.25 11.325-11.263z"></path>
                    </svg>
                  </button>
                  <button
                    class="btn btn-icon-sm btn-icon-danger"
                    title="删除"
                    @click="deleteKey(key)"
                  >
                    <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M3 6h18M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m-1 0v14a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1V6m-4 0v14a1 1 0 0 0 1 1h2"></path>
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="md:hidden">
        <p v-if="keys.length === 0" class="px-4 py-8 text-center text-sm text-gray-500">
          暂无 API Key，点击上方按钮创建
        </p>
        <ul v-else class="divide-y divide-gray-100">
          <li
            v-for="key in keys"
            :key="key.id"
            class="p-4"
            :class="rowClass(key)"
          >
            <div class="flex flex-wrap items-center gap-2">
              <span class="min-w-0 flex-1 truncate font-medium text-gray-900" :title="key.description">{{ key.description }}</span>
              <span
                v-if="apiKeysStore.selectedKeyId === key.id"
                class="inline-flex shrink-0 items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800"
              >默认</span>
              <span v-if="key.is_expired" class="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">已过期</span>
              <span v-else-if="!key.is_active" class="inline-flex items-center rounded-full bg-gray-200 px-2.5 py-0.5 text-xs font-medium text-gray-700">已禁用</span>
              <span v-else class="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800">正常</span>
            </div>
            <div class="mt-2 flex min-w-0 items-start gap-1">
              <code class="min-w-0 flex-1 break-all text-xs text-gray-600">{{ key.key }}</code>
              <button
                class="btn btn-icon-md btn-ghost text-gray-400 hover:text-gray-600"
                title="复制完整密钥"
                aria-label="复制完整密钥"
                @click.stop="copyFullKey(key, $event)"
              >
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>
            </div>
            <dl class="mt-2 grid grid-cols-1 gap-1 text-xs text-gray-500">
              <div class="flex justify-between gap-2">
                <dt>过期</dt>
                <dd class="text-right text-gray-700">
                  <span v-if="key.expires_at">{{ formatDateTime(key.expires_at) }}</span>
                  <span v-else class="text-gray-400">永不过期</span>
                </dd>
              </div>
              <div class="flex justify-between gap-2">
                <dt>创建</dt>
                <dd class="text-right text-gray-700">{{ formatDateTime(key.created_at) }}</dd>
              </div>
              <div class="flex justify-between gap-2">
                <dt>最后使用</dt>
                <dd class="text-right text-gray-700">
                  <span v-if="key.last_used_at">{{ formatDateTime(key.last_used_at) }}</span>
                  <span v-else class="text-gray-400">从未使用</span>
                </dd>
              </div>
            </dl>
            <div class="mt-3 flex flex-wrap gap-2">
              <button
                class="btn btn-sm min-h-10 flex-1 disabled:opacity-40 sm:min-h-8 sm:flex-none"
                :class="apiKeysStore.selectedKeyId === key.id ? 'border-blue-200 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-600 hover:bg-gray-50'"
                :disabled="!key.is_active || key.is_expired || apiKeysStore.selectedKeyId === key.id"
                @click="setDefaultKey(key)"
              >设为默认</button>
              <button
                class="btn btn-icon-md btn-icon-muted disabled:opacity-40"
                :disabled="key.is_expired"
                title="编辑"
                aria-label="编辑"
                @click="editKey(key)"
              >
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M16.862 3.487a2.25 2.25 0 1 1 3.182 3.182L8.25 18.463 4 20l1.537-4.25 11.325-11.263z"></path>
                </svg>
              </button>
              <button
                class="btn btn-icon-md btn-icon-danger"
                title="删除"
                aria-label="删除"
                @click="deleteKey(key)"
              >
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3 6h18M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m-1 0v14a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1V6m-4 0v14a1 1 0 0 0 1 1h2"></path>
                </svg>
              </button>
            </div>
          </li>
        </ul>
      </div>
      </template>
    </div>

    <Teleport to="body">
      <!-- 创建/编辑对话框 -->
      <div
        v-if="dialogVisible"
        class="fixed inset-0 z-50 flex items-end justify-center p-2 sm:items-center sm:p-4"
        role="dialog"
        aria-modal="true"
        tabindex="-1"
        @click.self="closeDialog"
      >
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" aria-hidden="true" @click="closeDialog"></div>
        <div
          class="relative z-10 flex h-[calc(100dvh-1rem)] max-h-[min(90vh,640px)] w-full max-w-lg flex-col overflow-hidden rounded-t-xl border border-gray-200 bg-white shadow-xl will-change-transform sm:h-auto sm:rounded-xl"
          @click.stop
        >
          <div class="flex shrink-0 items-center justify-between gap-3 border-b border-gray-200 px-4 py-3.5 sm:px-5">
            <h2 class="text-lg font-semibold text-gray-900">{{ editingKey ? '编辑 API Key' : '创建 API Key' }}</h2>
            <button
              type="button"
              class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800"
              aria-label="关闭"
              @click="closeDialog"
            >
              <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="min-h-0 flex-1 overflow-y-auto px-5 py-4 text-sm">
            <div class="mb-4">
              <label class="mb-1 block text-sm font-medium text-gray-700">描述 <span class="text-red-600">*</span></label>
              <input
                type="text"
                class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                v-model="formData.description"
                placeholder="请输入密钥描述，用于标识用途"
                maxlength="200"
                ref="descInput"
              />
            </div>
            <div class="mb-4">
              <label class="mb-1 block text-sm font-medium text-gray-700">过期时间</label>
              <input
                type="datetime-local"
                class="mb-2 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                v-model="formData.expires_at"
              />
              <div class="flex flex-wrap gap-1">
                <button
                  type="button"
                  class="inline-flex items-center justify-center gap-1 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                  @click="setExpiresDays(7)"
                >7天</button>
                <button
                  type="button"
                  class="inline-flex items-center justify-center gap-1 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                  @click="setExpiresDays(30)"
                >30天</button>
                <button
                  type="button"
                  class="inline-flex items-center justify-center gap-1 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                  @click="setExpiresDays(90)"
                >90天</button>
                <button
                  type="button"
                  class="inline-flex items-center justify-center gap-1 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                  @click="setExpiresDays(180)"
                >180天</button>
                <button
                  type="button"
                  class="inline-flex items-center justify-center gap-1 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                  @click="setExpiresDays(365)"
                >1年</button>
                <button
                  type="button"
                  class="inline-flex items-center justify-center gap-1 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                  @click="clearExpiresAt"
                >永不过期</button>
              </div>
              <small class="mt-1 block text-xs text-gray-500">留空表示永不过期，或使用快捷选项</small>
            </div>
            <div v-if="editingKey" class="mb-0">
              <label class="mb-1 block text-sm font-medium text-gray-700">状态</label>
              <label class="flex cursor-pointer items-center gap-2 text-sm text-gray-700">
                <input type="checkbox" class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" v-model="formData.is_active" />
                <span>启用</span>
              </label>
            </div>
          </div>
          <div class="flex shrink-0 flex-col-reverse gap-2 border-t border-gray-200 bg-gray-50 px-4 py-3.5 sm:flex-row sm:flex-wrap sm:items-center sm:justify-end sm:px-5">
            <button type="button" class="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-gray-200 px-3 py-2.5 text-sm font-medium text-gray-800 transition-colors hover:bg-gray-300 sm:w-auto sm:py-2" @click="closeDialog">取消</button>
            <button type="button" class="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto sm:py-2" @click="saveKey" :disabled="!formData.description?.trim() || saving">
              {{ saving ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 创建成功对话框（显示完整密钥） -->
      <div
        v-if="showKeyDialog"
        class="fixed inset-0 z-50 flex items-end justify-center p-2 sm:items-center sm:p-4"
        role="dialog"
        aria-modal="true"
        tabindex="-1"
        @click.self="showKeyDialog = false"
      >
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" aria-hidden="true" @click="showKeyDialog = false"></div>
        <div
          class="relative z-10 flex h-[calc(100dvh-1rem)] max-h-[min(90vh,720px)] w-full max-w-lg flex-col overflow-hidden rounded-t-xl border border-gray-200 bg-white shadow-xl will-change-transform sm:h-auto sm:rounded-xl"
          @click.stop
        >
          <div class="flex shrink-0 items-center justify-between gap-3 border-b border-gray-200 px-4 py-3.5 sm:px-5">
            <h2 class="text-lg font-semibold text-gray-900">API Key 创建成功</h2>
            <button
              type="button"
              class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800"
              aria-label="关闭"
              @click="showKeyDialog = false"
            >
              <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="min-h-0 flex-1 overflow-y-auto px-5 py-4 text-sm">
            <div class="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900" role="alert">
              <strong class="font-semibold">重要提示：</strong>请妥善保管此密钥，创建后将无法再次查看完整密钥！
            </div>
            <div class="mb-4">
              <label class="mb-1 block text-sm font-medium text-gray-700">描述</label>
              <p class="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900">{{ createdKeyData?.description }}</p>
            </div>
            <div class="mb-4">
              <label class="mb-1 block text-sm font-medium text-gray-700">API Key</label>
              <div class="flex min-w-0 flex-col gap-2 sm:flex-row">
                <input
                  type="text"
                  class="min-w-0 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 font-mono text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 sm:flex-1 sm:rounded-l-lg sm:rounded-r-none sm:border-r-0"
                  :value="createdKeyData?.key"
                  readonly
                  ref="keyInput"
                />
                <button
                  class="btn btn-md btn-outline w-full shrink-0 sm:w-auto sm:rounded-l-none sm:rounded-r-lg"
                  type="button"
                  aria-label="复制 API Key"
                  @click.stop="copyCreatedKey($event)"
                >
                  <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                  复制
                </button>
              </div>
            </div>
            <div class="mb-0">
              <label class="mb-1 block text-sm font-medium text-gray-700">使用方式</label>
              <div class="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <div class="mb-3 last:mb-0">
                  <strong class="text-sm font-semibold text-gray-900">Header 认证</strong>
                  <div class="mt-1 break-all">
                    <code class="text-xs text-gray-600">Authorization: Bearer {{ createdKeyData?.key }}</code>
                  </div>
                </div>
                <div>
                  <strong class="text-sm font-semibold text-gray-900">URL 参数</strong>
                  <div class="mt-1 break-all">
                    <code class="text-xs text-gray-600">?api_key={{ createdKeyData?.key }}</code>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="flex shrink-0 border-t border-gray-200 bg-gray-50 px-4 py-3.5 sm:px-5">
            <button type="button" class="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 sm:w-auto sm:py-2" @click="showKeyDialog = false">我已保存</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 提示消息 -->
    <div
      v-if="toastMessage"
      class="fixed left-3 right-3 top-4 z-60 flex max-w-sm items-start gap-3 rounded-lg border px-4 py-3 text-sm shadow-lg sm:left-auto sm:right-4 sm:min-w-[280px]"
      :class="toastType === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-red-200 bg-red-50 text-red-900'"
      role="status"
    >
      <span class="flex-1 pt-0.5">{{ toastMessage }}</span>
      <button
        type="button"
        class="btn btn-icon-sm shrink-0 text-current opacity-70 transition-opacity hover:bg-black/5 hover:opacity-100"
        aria-label="关闭"
        @click="toastMessage = ''"
      >
        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { apiKeysApi } from '@/api/apiKeys'
import { useApiKeysStore } from '@/stores/apiKeys'
import { useModal } from '@/composables/useModal'
import { copyWithTooltip } from '@/composables/useCopyTooltip'

const apiKeysStore = useApiKeysStore()
const loading = ref(false)
const saving = ref(false)
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const showKeyDialog = ref(false)
const editingKey = ref(null)
const createdKeyData = ref(null)
const keyInput = ref(null)
const descInput = ref(null)

const formData = ref({
  description: '',
  expires_at: '',
  is_active: true
})

const keys = computed(() => apiKeysStore.keys || [])

const dialogVisible = computed(() => showCreateDialog.value || showEditDialog.value)

const rowClass = (key) => {
  if (key.is_expired) return 'bg-red-50/40'
  if (!key.is_active) return 'bg-gray-50/50'
  return ''
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Toast
const toastMessage = ref('')
const toastType = ref('success')
let toastTimer = null

const showToast = (message, type = 'success') => {
  toastMessage.value = message
  toastType.value = type
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastMessage.value = ''; toastTimer = null }, 3000)
}

// 加载列表
const loadKeys = async () => {
  loading.value = true
  try {
    await apiKeysStore.loadKeys()
  } catch (e) {
    console.error('加载 API Key 列表失败:', e)
    showToast('加载失败', 'error')
  } finally {
    loading.value = false
  }
}

// 复制完整密钥（从列表）
const copyFullKey = async (key, event) => {
  try {
    const fullKey = await apiKeysStore.resolveFullKey(key.id)
    if (!fullKey) {
      showToast('无法获取完整密钥', 'error')
      return
    }
    await copyWithTooltip(fullKey, event)
  } catch (e) {
    showToast('复制失败: ' + (e.response?.data?.detail || e.message), 'error')
  }
}

// 复制创建后的密钥
const copyCreatedKey = async (event) => {
  if (createdKeyData.value?.key) {
    await copyWithTooltip(createdKeyData.value.key, event)
  }
}

// 设为默认
const setDefaultKey = (key) => {
  if (!key.is_active || key.is_expired) return
  apiKeysStore.setDefaultKey(key.id)
  showToast(`已将 "${key.description}" 设为默认`, 'success')
}

// 过期时间
const setExpiresDays = (days) => {
  const d = new Date()
  d.setDate(d.getDate() + days)
  const pad = (n) => String(n).padStart(2, '0')
  formData.value.expires_at = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const clearExpiresAt = () => {
  formData.value.expires_at = ''
}

// 对话框操作
const openCreateDialog = () => {
  showCreateDialog.value = true
  nextTick(() => descInput.value?.focus())
}

const closeDialog = () => {
  showCreateDialog.value = false
  showEditDialog.value = false
  editingKey.value = null
  formData.value = { description: '', expires_at: '', is_active: true }
}

const editKey = (key) => {
  editingKey.value = key
  formData.value = {
    description: key.description,
    expires_at: key.expires_at ? new Date(key.expires_at).toISOString().slice(0, 16) : '',
    is_active: key.is_active
  }
  showEditDialog.value = true
  nextTick(() => descInput.value?.focus())
}

// 保存
const saveKey = async () => {
  if (!formData.value.description?.trim()) return
  saving.value = true
  try {
    const data = {
      description: formData.value.description.trim(),
      expires_at: formData.value.expires_at ? new Date(formData.value.expires_at).toISOString() : null
    }

    if (editingKey.value) {
      data.is_active = formData.value.is_active
      await apiKeysApi.update(editingKey.value.id, data)
      await loadKeys()
      closeDialog()
      showToast('更新成功')
    } else {
      const result = await apiKeysApi.create(data)
      if (!result?.id || !result?.key) {
        showToast('创建失败：服务器返回数据不完整', 'error')
        return
      }
      const keyValue = String(result.key).trim()
      const idNum = Number(result.id)
      if (keyValue === String(idNum) || keyValue.length < 20) {
        showToast('创建失败：服务器返回数据异常', 'error')
        return
      }
      localStorage.setItem(`api_key_${idNum}`, keyValue)
      localStorage.setItem(`api_key_${String(idNum)}`, keyValue)

      createdKeyData.value = result
      closeDialog()
      showKeyDialog.value = true
      if (!apiKeysStore.selectedKeyId) {
        apiKeysStore.setDefaultKey(idNum)
        showToast('已自动设为默认密钥')
      }
      await loadKeys()
    }
  } catch (e) {
    console.error('保存失败:', e)
    showToast('保存失败: ' + e.message, 'error')
  } finally {
    saving.value = false
  }
}

// 删除
const deleteKey = async (key) => {
  if (!confirm(`确定要删除密钥 "${key.description}" 吗？此操作不可恢复。`)) return
  try {
    await apiKeysApi.delete(key.id)
    if (apiKeysStore.selectedKeyId === key.id) {
      apiKeysStore.setDefaultKey(null)
    }
    await loadKeys()
    showToast('删除成功')
  } catch (e) {
    showToast('删除失败: ' + e.message, 'error')
  }
}

useModal(dialogVisible, closeDialog)
useModal(showKeyDialog, () => { showKeyDialog.value = false })

onMounted(() => {
  loadKeys()
})
</script>
