<script setup>
import { onMounted, onUnmounted, ref } from "vue";
import { managedHostsApi, temporaryCredentialsApi } from "@/api/managedHosts";
import { Button } from "@/components/ui/button";
import { copyDeferredText, copyText, formatCredentialExpiry, formatTemporaryCredential } from "@/composables/useClipboard";
import { notify } from "@/composables/useFeedback";
import { saveDownload } from "@/utils/saveDownload";

const props = defineProps({ credential: { type: Object, required: true } });
const emit = defineEmits(["refresh"]);
const password = ref("");
const busy = ref(false);
const expired = ref(false);
let hideTimer;
let expiryTimer;
let closed = false;

function hidePassword() {
  clearTimeout(hideTimer);
  password.value = "";
}

onMounted(() => {
  const remaining = Date.parse(props.credential.expires_at) - Date.now();
  expired.value = remaining <= 0;
  if (remaining > 0) {
    expiryTimer = setTimeout(() => {
      expired.value = true;
      hidePassword();
    }, remaining);
  }
});

onUnmounted(() => {
  closed = true;
  clearTimeout(expiryTimer);
  hidePassword();
});

async function run(task) {
  if (busy.value || expired.value) return;
  busy.value = true;
  try {
    await task();
  } catch (error) {
    hidePassword();
    notify(error.message, "error");
    emit("refresh");
  } finally {
    busy.value = false;
  }
}

function copySecret(trigger, format) {
  return run(() => copyDeferredText(() => temporaryCredentialsApi.copy(props.credential).then(format), trigger));
}

function togglePassword() {
  if (password.value) return hidePassword();
  return run(async () => {
    const data = await temporaryCredentialsApi.copy(props.credential);
    const remaining = Date.parse(data.expires_at) - Date.now();
    if (!closed && remaining > 0) {
      password.value = data.password;
      hideTimer = setTimeout(hidePassword, Math.min(remaining, 30000));
    }
  });
}

function downloadRdp() {
  return run(async () => {
    const { host_id, username } = props.credential;
    const result = await managedHostsApi.test(host_id);
    if (!result.success) throw new Error(result.stderr || "RDP 证书校验未通过，未下载连接文件");
    if (closed) return;
    const blob = await managedHostsApi.rdpFile(host_id, username);
    if (!closed) saveDownload(blob, `frp-agent-rdp-${host_id}.rdp`);
  });
}
</script>

<template>
  <div class="min-w-0 space-y-3">
    <dl class="divide-y rounded-md border px-3 text-sm">
      <div v-for="[field, label] in [['address', '地址'], ['username', '账号']]" :key="field" class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-2 py-2">
        <dt class="text-muted-foreground">{{ label }}</dt>
        <dd class="col-start-1 row-start-2 break-all font-mono">{{ credential[field] }}</dd>
        <dd class="col-start-2 row-span-2 row-start-1">
          <Button type="button" size="sm" variant="outline" class="max-sm:min-h-11" @click="copyText(credential[field], $event.currentTarget)">复制{{ label }}</Button>
        </dd>
      </div>
      <div class="space-y-2 py-2">
        <dt class="text-muted-foreground">密码</dt>
        <dd class="break-all font-mono">{{ password || "••••••••" }}</dd>
        <dd class="flex flex-wrap gap-2">
          <Button type="button" size="sm" variant="outline" class="max-sm:min-h-11" :disabled="busy || expired" @click="togglePassword">{{ password ? "隐藏密码" : "显示密码" }}</Button>
          <Button type="button" size="sm" variant="outline" class="max-sm:min-h-11" :disabled="busy || expired" @click="copySecret($event.currentTarget, (data) => data.password)">复制密码</Button>
        </dd>
      </div>
      <div class="space-y-1 py-2">
        <dt class="text-muted-foreground">有效至</dt>
        <dd>{{ formatCredentialExpiry(credential.expires_at) }}{{ credential.protocol === "vnc" ? "（仅可连接一次）" : "" }}</dd>
        <dd v-if="expired" role="status" class="text-muted-foreground">已过期，请重新生成凭据。</dd>
      </div>
    </dl>
    <div class="flex flex-wrap gap-2">
      <Button type="button" class="max-sm:min-h-11" :disabled="busy || expired" @click="copySecret($event.currentTarget, formatTemporaryCredential)">一键复制（含有效期）</Button>
      <Button v-if="credential.protocol === 'rdp'" type="button" variant="outline" class="max-sm:min-h-11" :disabled="busy || expired" @click="downloadRdp">下载 .rdp</Button>
      <Button v-else-if="!expired && credential.address?.startsWith('vnc://')" as-child variant="outline" class="max-sm:min-h-11">
        <a :href="credential.address">打开屏幕共享</a>
      </Button>
    </div>
    <p v-if="credential.protocol === 'rdp'" class="text-xs text-muted-foreground">连接文件包含地址和账号，打开后输入临时密码。</p>
  </div>
</template>
