<script setup>
import { computed } from "vue";
import { ShieldAlert, ShieldCheck, Info } from "@lucide/vue";
import { Button } from "@/components/ui/button";
const props = defineProps({
  host: { type: Object, required: true },
  result: Object,
  checking: Boolean,
  canManage: Boolean,
});
defineEmits(["check", "edit"]);
const message = computed(
  () => props.result?.message || props.host.last_message || "",
);
const failed = computed(() =>
  props.result
    ? !props.result.success
    : ["error", "offline"].includes(props.host.last_status),
);
const upstreamFailed = computed(
  () => failed.value && /穿透服务器|代理“|代理.*离线/.test(message.value),
);
const certificateChanged = computed(
  () =>
    failed.value &&
    /指纹.*不匹配|证书.*变化|certificate.*mismatch/i.test(message.value),
);
const title = computed(() =>
  props.checking
    ? "正在检查 RDP 连接"
    : upstreamFailed.value
      ? "上游穿透连接异常"
      : certificateChanged.value
        ? "RDP 证书已变化，连接被阻止"
        : failed.value
          ? "RDP 连接检查未通过"
          : props.result?.success
            ? "TLS／证书校验通过"
            : "RDP 连接说明",
);
const checkedAt = computed(
  () => props.result?.checkedAt || props.host.last_checked_at,
);
function formatTime(value) {
  const date = new Date(
    /(?:Z|[+-]\d\d:\d\d)$/.test(value) ? value : value + "Z",
  );
  return Number.isNaN(date.getTime())
    ? "未知时间"
    : date.toLocaleString("zh-CN");
}
</script>

<template>
  <section
    :role="failed ? 'alert' : 'status'"
    :aria-label="title"
    class="mt-3 space-y-2 rounded-lg border p-3 text-xs leading-5"
    :class="
      failed
        ? 'border-destructive/30 bg-destructive/5 text-destructive'
        : 'border-border bg-muted/30 text-muted-foreground'
    "
  >
    <div class="flex items-start gap-2">
      <ShieldAlert v-if="failed" class="mt-0.5 size-4 shrink-0" /><ShieldCheck
        v-else-if="result?.success"
        class="mt-0.5 size-4 shrink-0"
      /><Info v-else class="mt-0.5 size-4 shrink-0" /><strong
        class="text-sm font-medium"
        >{{ title }}</strong
      >
    </div>
    <template v-if="certificateChanged">
      <p>
        目标证书与已保存指纹不一致，可能由 Windows
        续签或重建证书引起，与登录密码是否修改无关。
      </p>
      <p>
        {{
          canManage
            ? "先核实目标机器，再到“编辑主机 → 连接与认证”获取新指纹并保存，然后重新校验。"
            : "请联系管理员核实目标机器并更新证书指纹，再重新连接。"
        }}
      </p>
    </template>
    <p v-else-if="failed" class="break-words">
      {{
        message ||
        "暂时无法完成检测，请重试；持续失败时检查目标服务、网络和代理连接。"
      }}
    </p>
    <Button
      v-if="upstreamFailed && canManage"
      variant="outline"
      size="sm"
      as-child
      ><RouterLink to="/tunnel-services">检查穿透服务</RouterLink></Button
    >
    <p v-if="!failed">
      此检查仅验证 RDP 服务与证书，不验证 Windows
      账号登录。证书以后变化时仍需核实并更新指纹。
    </p>
    <p v-if="checkedAt">
      {{ result ? "本次检查" : "上次检查" }}：{{ formatTime(checkedAt)
      }}{{ result ? "" : "（历史结果）" }}
    </p>
    <div class="flex flex-wrap gap-2">
      <Button
        type="button"
        variant="outline"
        size="sm"
        :disabled="checking"
        @click="$emit('check')"
        >{{ checking ? "检查中…" : "重新校验 RDP" }}</Button
      ><Button
        v-if="failed && !upstreamFailed && canManage"
        type="button"
        variant="outline"
        size="sm"
        @click="$emit('edit')"
        >核验并编辑主机</Button
      >
    </div>
  </section>
</template>
