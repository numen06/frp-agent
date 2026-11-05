<script setup>
import { onMounted, ref } from "vue";
import { Button } from "@/components/ui/button";
import api from "@/api";
const data = ref(null),
  gateway = ref(null),
  error = ref(""),
  busy = ref(false);
async function refresh() {
  if (busy.value) return;
  busy.value = true;
  try {
    const result = await Promise.all([
      api.get("/managed-hosts/ssh-protection"),
      api.get("/managed-hosts/gateway/info"),
    ]);
    [data.value, gateway.value] = result;
    error.value = "";
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
function date(t) {
  return new Date(t * 1000).toLocaleString("zh-CN");
}
onMounted(refresh);
</script>
<template>
  <section class="space-y-4" aria-label="SSH 防护状态">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h3 class="font-semibold">SSH 网关与 Web SSH 防护</h3>
      <Button variant="outline" :disabled="busy" @click="refresh">{{
        busy ? "读取中…" : "刷新防护状态"
      }}</Button>
    </div>
    <p v-if="error" role="alert" class="break-words text-sm text-destructive">
      {{ error }}。请重试，下方如有数据为上次读取结果。
    </p>
    <p v-else-if="!data" role="status" class="text-sm text-muted-foreground">
      正在读取 SSH 防护状态…
    </p>
    <template v-if="data"
      ><p class="text-xs text-muted-foreground">
        读取于 {{ date(data.collected_at) }} · 仅覆盖通过平台网关或 Web SSH
        发起的连接。直接访问 FRP 暴露端口及服务器系统 SSH（如 22
        端口）由目标系统自行防护。
      </p>
      <div class="rounded-lg border p-4">
        <div class="flex flex-wrap justify-between gap-2">
          <h4 class="text-sm font-medium">平台 SSH 网关</h4>
          <span class="text-xs"
            >{{
              !gateway.enabled
                ? "未启用"
                : gateway.running
                  ? "运行中"
                  : "未运行"
            }}
            · {{ gateway.port }} 端口</span
          >
        </div>
        <dl class="mt-3 grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt class="text-muted-foreground">当前临时封禁来源</dt>
            <dd class="mt-1 text-xl font-semibold">{{ data.bans.length }}</dd>
          </div>
          <div>
            <dt class="text-muted-foreground">认证失败累计次数</dt>
            <dd class="mt-1 text-xl font-semibold">
              {{
                data.native_metrics
                  ? data.native_metrics.counts.auth_failures || 0
                  : "等待采集"
              }}
            </dd>
          </div>
        </dl>
        <p
          v-if="data.metrics_error"
          role="alert"
          class="mt-3 text-sm text-destructive"
        >
          {{ data.metrics_error }}
        </p>
        <p
          v-if="data.native_metrics"
          class="mt-3 text-xs leading-5 text-muted-foreground"
        >
          按可用网关日志累计，自
          {{
            new Date(
              data.native_metrics.first_log_at ||
                data.native_metrics.started_at,
            ).toLocaleString("zh-CN")
          }}
          起，每分钟更新；最近采集
          {{
            date(data.native_metrics.collected_at)
          }}。仅统计密码和公钥认证失败，不含正常的认证方式探测、Web SSH
          或上游主机登录失败。
        </p>
        <dl
          v-if="data.native_metrics"
          class="mt-3 grid grid-cols-2 gap-4 text-sm"
        >
          <div>
            <dt class="text-muted-foreground">认证成功</dt>
            <dd class="mt-1 text-xl font-semibold">
              {{ data.native_metrics.counts.auth_successes || 0 }}
            </dd>
          </div>
          <div>
            <dt class="text-muted-foreground">连接处理异常</dt>
            <dd class="mt-1 text-xl font-semibold">
              {{ data.native_metrics.counts.connection_errors || 0 }}
            </dd>
          </div>
        </dl>
        <p class="mt-3 text-xs leading-6 text-muted-foreground">
          单连接最多 {{ data.policy.max_auth_attempts }} 次认证尝试；同一来源
          {{ data.policy.window_seconds / 60 }} 分钟内失败
          {{ data.policy.ban_threshold }} 次，封禁
          {{ data.policy.ban_seconds / 60 }} 分钟。封禁名单持久保存。全局最多
          {{ data.policy.max_sessions }} 个连接，每个来源最多
          {{ data.policy.max_sessions_per_ip }} 个；握手限时
          {{ data.policy.handshake_timeout }} 秒，认证限时
          {{ data.policy.auth_timeout }}
          秒。目标主机指纹校验及访问授权仍然生效。
        </p>
        <ul v-if="data.bans.length" class="mt-3 space-y-2">
          <li
            v-for="ban in data.bans"
            :key="ban.ip"
            class="flex flex-wrap justify-between gap-2 rounded-md bg-muted p-2 text-xs"
          >
            <span class="break-all font-mono">{{ ban.ip }}</span
            ><span>至 {{ date(ban.until) }}</span>
          </li>
        </ul>
        <p v-else class="mt-3 text-xs text-muted-foreground">
          当前没有有效的临时封禁记录。
        </p>
      </div>
      <div class="rounded-lg border p-4">
        <h4 class="text-sm font-medium">Web SSH</h4>
        <p class="mt-3 text-sm">
          当前终端连接：{{ data.webssh.active }} /
          {{ data.webssh.max_sessions }}
        </p>
        <p class="mt-2 text-xs leading-6 text-muted-foreground">
          每个账号最多 {{ data.webssh.max_per_user }} 个终端；空闲
          {{ data.webssh.idle_timeout / 60 }} 分钟断开，单次最长
          {{ data.webssh.max_age / 3600 }}
          小时。必须具备主机执行权限，使用已保存的目标指纹校验，定期复核授权；连接不在
          URL 中携带凭据。Web SSH 与原生 SSH 网关使用各自的连接限制。
        </p>
      </div></template
    >
  </section>
</template>
