<script setup>
import { onMounted, onBeforeUnmount, ref } from "vue";
import { onBeforeRouteLeave, onBeforeRouteUpdate } from "vue-router";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { confirmAction } from "@/composables/useFeedback";

const props = defineProps({ host: { type: Object, required: true } });
const container = ref(null),
  status = ref("connecting"),
  error = ref("");
let term,
  fit,
  socket,
  observer,
  disposed = false;
function send(packet) {
  if (socket?.readyState === WebSocket.OPEN)
    socket.send(JSON.stringify(packet));
}
function disconnect() {
  const old = socket;
  socket = null;
  if (old) {
    old.onclose = old.onmessage = old.onerror = old.onopen = null;
    old.close(1000, "用户断开");
  }
  status.value = "closed";
}
function connect() {
  disconnect();
  error.value = "";
  const token = localStorage.getItem("auth_token");
  if (!token) {
    error.value = "登录已失效，请重新登录";
    return;
  }
  status.value = "connecting";
  term.reset();
  fit.fit();
  const base = new URL(
    import.meta.env.VITE_API_BASE_URL || "/api",
    window.location.origin,
  );
  base.pathname =
    base.pathname.replace(/\/$/, "") +
    `/managed-hosts/${props.host.id}/terminal`;
  base.protocol = base.protocol === "https:" ? "wss:" : "ws:";
  base.search = "";
  const ws = new WebSocket(base);
  socket = ws;
  ws.binaryType = "arraybuffer";
  ws.onopen = () => {
    if (socket !== ws) return;
    send({
      type: "auth",
      authorization: `Basic ${token}`,
      cols: term.cols,
      rows: term.rows,
    });
  };
  ws.onmessage = (event) => {
    if (socket !== ws || disposed) return;
    if (event.data instanceof ArrayBuffer) {
      term.write(new Uint8Array(event.data), () => {
        if (socket === ws) send({ type: "ack" });
      });
      return;
    }
    try {
      const packet = JSON.parse(event.data);
      if (packet.type === "ready") {
        status.value = "connected";
        fit.fit();
        send({ type: "resize", cols: term.cols, rows: term.rows });
        term.focus();
      } else if (packet.type === "error") {
        error.value = packet.message;
        status.value = "error";
      } else if (packet.type === "exit") status.value = "closed";
    } catch {
      error.value = "终端响应异常，请断开后重新连接";
    }
  };
  ws.onerror = () => {
    if (socket === ws) {
      error.value = "Web SSH 连接失败，请检查网络或联系管理员";
      status.value = "error";
    }
  };
  ws.onclose = () => {
    if (socket !== ws) return;
    if (status.value === "connecting" && !error.value)
      error.value = "终端服务未连接，请重试或联系管理员";
    status.value = error.value ? "error" : "closed";
    socket = null;
  };
}
function canLeave() {
  return (
    !["connected", "connecting"].includes(status.value) ||
    confirmAction("离开后将断开当前 SSH 会话，确定离开？", {
      title: "断开 Web SSH",
      confirmText: "断开并离开",
    })
  );
}
function beforeUnload(event) {
  if (["connected", "connecting"].includes(status.value)) {
    event.preventDefault();
    event.returnValue = "";
  }
}
onBeforeRouteLeave(canLeave);
onBeforeRouteUpdate(
  (to, from) =>
    (to.path === from.path && to.query.tab === from.query.tab) || canLeave(),
);
onMounted(async () => {
  term = new Terminal({
    cursorBlink: true,
    fontSize: 14,
    fontFamily: 'Consolas, "Liberation Mono", monospace',
    scrollback: 3000,
    theme: { background: "#090f1e", foreground: "#e2e8f0", cursor: "#93c5fd" },
    allowProposedApi: false,
  });
  fit = new FitAddon();
  term.loadAddon(fit);
  term.open(container.value);
  term.onData((data) => {
    if (status.value !== "connected") return;
    for (const chunk of data.match(/.{1,4096}/gsu) || [])
      send({ type: "input", data: chunk });
  });
  term.onResize((size) => {
    if (status.value === "connected") send({ type: "resize", ...size });
  });
  observer = new ResizeObserver(() => {
    if (!disposed && container.value?.clientWidth) fit.fit();
  });
  observer.observe(container.value);
  window.addEventListener("beforeunload", beforeUnload);
  await document.fonts.ready;
  if (!disposed) connect();
});
onBeforeUnmount(() => {
  disposed = true;
  disconnect();
  observer?.disconnect();
  term?.dispose();
  window.removeEventListener("beforeunload", beforeUnload);
});
</script>

<template>
  <Card class="min-w-0">
    <div
      class="flex flex-wrap items-center justify-between gap-3 border-b p-3 sm:p-4"
    >
      <div class="flex min-w-0 items-center gap-2 text-sm">
        <h2 class="font-semibold">Web SSH</h2>
        <span role="status" class="text-xs text-muted-foreground">{{
          {
            connecting: "连接中…",
            connected: "已连接",
            closed: "已断开",
            error: "连接失败",
          }[status]
        }}</span>
      </div>
      <div class="flex flex-wrap gap-2">
        <Button
          variant="outline"
          size="sm"
          :disabled="status !== 'connected'"
          @click="send({ type: 'input', data: '\u0003' })"
          >Ctrl+C</Button
        >
        <Button
          variant="outline"
          size="sm"
          :disabled="status !== 'connected'"
          @click="
            send({ type: 'input', data: '\t' });
            term.focus();
          "
          class="min-w-11"
          >Tab</Button
        >
        <Button
          v-if="status === 'connected' || status === 'connecting'"
          variant="outline"
          size="sm"
          @click="disconnect"
          >断开</Button
        >
        <Button v-else variant="default" size="sm" @click="connect"
          >重新连接</Button
        >
      </div>
    </div>
    <p
      v-if="error"
      role="alert"
      class="break-words border-b p-3 text-sm text-destructive"
    >
      {{ error }}
    </p>
    <div
      ref="container"
      role="region"
      aria-label="SSH 交互终端"
      class="h-[65dvh] min-h-64 min-w-0 bg-[#090f1e] p-2 [&_.xterm-helper-textarea]:text-base"
    />
    <p class="border-t px-3 py-2 text-xs leading-5 text-muted-foreground">
      支持实时输入、方向键与
      Ctrl+C。会话结束后记录连接与流量，不录制终端输入和输出。
    </p>
  </Card>
</template>
