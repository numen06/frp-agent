<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from "vue";
import { onBeforeRouteLeave, onBeforeRouteUpdate } from "vue-router";
import { Maximize2, Minimize2 } from "@lucide/vue";
import RFB from "@novnc/novnc";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { confirmAction } from "@/composables/useFeedback";
const props = defineProps({ host: { type: Object, required: true } });
const screen = ref(null), status = ref("未连接"), error = ref("");
const keyboardText = ref("");
const maximized = ref(false);
let previousOverflow;
let socket, rfb;

watch(maximized, (active) => {
  if (active) {
    previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
  } else if (previousOverflow !== undefined) {
    document.body.style.overflow = previousOverflow;
    previousOverflow = undefined;
  }
});
function handleEscape(event) {
  if (maximized.value && event.key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    maximized.value = false;
  }
}

function sendKeyboardText() {
  if (!rfb || status.value !== "已连接" || !keyboardText.value) return;
  const text = keyboardText.value;
  keyboardText.value = "";
  for (const character of text) {
    const point = character.codePointAt(0);
    const latin1 =
      (point >= 0x20 && point <= 0x7e) || (point >= 0xa0 && point <= 0xff);
    rfb.sendKey(latin1 ? point : 0x01000000 + point);
  }
  rfb.sendKey(0xff0d); // X11 Return
  rfb.focus({ preventScroll: true });
}

function disconnect() {
  keyboardText.value = "";
  const old = socket;
  socket = null;
  rfb?.disconnect();
  rfb = null;
  old?.close();
  status.value = "已断开";
}
function connect() {
  disconnect();
  error.value = "";
  if (window.location.protocol !== "https:") {
    error.value = "远程桌面需要 HTTPS，请通过平台的 HTTPS 地址访问";
    return;
  }
  const token = localStorage.getItem("auth_token");
  if (!token) { error.value = "登录已失效，请重新登录"; return; }
  const base = new URL(import.meta.env.VITE_API_BASE_URL || "/api", window.location.origin);
  base.pathname = base.pathname.replace(/\/$/, "") + `/managed-hosts/${props.host.id}/vnc`;
  base.protocol = "wss:";
  base.search = "";
  status.value = "连接中…";
  const ws = new WebSocket(base);
  socket = ws;
  ws.binaryType = "arraybuffer";
  ws.onopen = () => ws.send(JSON.stringify({ type: "auth", authorization: `Basic ${token}` }));
  ws.onmessage = (event) => {
    if (socket !== ws) return;
    try {
      const packet = JSON.parse(event.data);
      if (packet.type === "error") {
        error.value = packet.message;
        disconnect();
      } else if (packet.type === "ready") {
        rfb = new RFB(screen.value, ws, { shared: true });
        rfb.scaleViewport = true;
        rfb.resizeSession = false;
        rfb.addEventListener("connect", () => { status.value = "已连接"; });
        rfb.addEventListener("disconnect", (e) => {
          if (socket !== ws) return;
          keyboardText.value = "";
          status.value = "已断开";
          if (!e.detail.clean) error.value = "连接已结束，请检查当前连接的授权、凭据和网络后重试";
          socket = null;
          rfb = null;
        });
        rfb.addEventListener("credentialsrequired", () => {
          error.value = "服务端认证未完成，请联系管理员检查 VNC 配置";
          disconnect();
        });
      }
    } catch {
      error.value = "远程桌面响应无效";
      disconnect();
    }
  };
  ws.onerror = () => { if (socket === ws) error.value = "VNC 连接失败，请检查 HTTPS 与 WebSocket 代理配置"; };
  ws.onclose = () => { if (socket === ws) { status.value = "已断开"; socket = null; } };
}
function canLeave() {
  return !socket || confirmAction("离开后将断开当前远程桌面，确定离开？", { title: "断开 VNC", confirmText: "断开并离开" });
}
function beforeUnload(event) {
  if (socket) {
    event.preventDefault();
    event.returnValue = "";
  }
}
onBeforeRouteLeave(canLeave);
onBeforeRouteUpdate((to, from) => (to.path === from.path && to.query.tab === from.query.tab) || canLeave());
onMounted(() => {
  window.addEventListener("beforeunload", beforeUnload);
  window.addEventListener("keydown", handleEscape, true);
});
onBeforeUnmount(() => {
  window.removeEventListener("beforeunload", beforeUnload);
  window.removeEventListener("keydown", handleEscape, true);
  if (previousOverflow !== undefined) document.body.style.overflow = previousOverflow;
  disconnect();
});
</script>
<template>
  <Card
    class="min-w-0 gap-3 p-3"
    :class="{ 'fixed inset-0 z-[65] h-dvh overflow-auto rounded-none': maximized }"
  >
    <div class="flex flex-wrap items-center gap-2">
      <span role="status" class="mr-auto text-sm">{{ status }}</span>
      <Button :disabled="status === '已连接' || status === '连接中…'" @click="connect">连接桌面</Button>
      <Button type="button" variant="outline" :aria-pressed="maximized" @click="maximized = !maximized">
        <Minimize2 v-if="maximized" aria-hidden="true" />
        <Maximize2 v-else aria-hidden="true" />
        {{ maximized ? "还原窗口" : "最大化" }}
      </Button>
      <Button variant="outline" :disabled="!socket" @click="disconnect">断开</Button>
    </div>
    <p v-if="error" role="alert" class="text-sm text-destructive">{{ error }}</p>
    <form
      v-if="status === '已连接'"
      class="space-y-1"
      @submit.prevent="sendKeyboardText"
    >
      <div class="flex items-center gap-2">
        <Input
          v-model="keyboardText"
          type="password"
          aria-label="远程键盘输入"
          placeholder="点此打开手机键盘"
          autocomplete="off"
          autocapitalize="none"
          autocorrect="off"
          enterkeyhint="send"
          :spellcheck="false"
          maxlength="256"
          class="min-h-11"
        />
        <Button
          type="submit"
          variant="outline"
          class="min-h-11 shrink-0"
          :disabled="!keyboardText"
          >发送并回车</Button
        >
      </div>
      <p class="text-xs text-muted-foreground">
        先点远程画面的密码框，再在这里输入。
      </p>
    </form>
    <p class="text-xs text-muted-foreground">{{ host.vnc_ssh_host_id ? '通过已核验指纹的 SSH 隧道连接。' : '通过配置的可信网络入口直连 VNC。' }}会话最长 1 小时，授权撤销后自动断开。关闭页面会结束连接。</p>
    <div
      ref="screen"
      class="w-full min-w-0 overflow-hidden rounded-md bg-black"
      :class="maximized ? 'min-h-32 flex-1' : 'h-[65vh] min-h-64'"
      aria-label="VNC 远程桌面"
    />
  </Card>
</template>
