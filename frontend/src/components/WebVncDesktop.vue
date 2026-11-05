<script setup>
import { ref, onBeforeUnmount } from "vue";
import { onBeforeRouteLeave, onBeforeRouteUpdate } from "vue-router";
import RFB from "@novnc/novnc";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { confirmAction } from "@/composables/useFeedback";
const props = defineProps({ host: { type: Object, required: true } });
const screen = ref(null), status = ref("未连接"), error = ref("");
let socket, rfb;
function disconnect() {
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
          status.value = "已断开";
          if (!e.detail.clean) error.value = "连接已结束，请检查授权、SSH 指纹和网络后重试";
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
onBeforeRouteLeave(canLeave);
onBeforeRouteUpdate((to, from) => (to.path === from.path && to.query.tab === from.query.tab) || canLeave());
onBeforeUnmount(disconnect);
</script>
<template>
  <Card class="min-w-0 gap-3 p-3">
    <div class="flex flex-wrap items-center gap-2">
      <span role="status" class="mr-auto text-sm">{{ status }}</span>
      <Button :disabled="status === '已连接' || status === '连接中…'" @click="connect">连接桌面</Button>
      <Button variant="outline" :disabled="!socket" @click="disconnect">断开</Button>
    </div>
    <p v-if="error" role="alert" class="text-sm text-destructive">{{ error }}</p>
    <p class="text-xs text-muted-foreground">通过已核验的 SSH 通道访问 Mac；会话最长 1 小时，授权撤销后自动断开。关闭页面会结束连接。</p>
    <div ref="screen" class="h-[65vh] min-h-64 w-full min-w-0 overflow-hidden rounded-md bg-black" aria-label="VNC 远程桌面" />
  </Card>
</template>
