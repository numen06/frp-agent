import { readonly, ref } from "vue";
import { toast } from "vue-sonner";

const current = ref(null);
const queue = [];

function request(kind, message, options) {
  return new Promise((resolve) => {
    queue.push({ kind, message, ...options, resolve });
    advance();
  });
}
function advance() {
  if (!current.value) current.value = queue.shift() || null;
}
export function finishFeedback(value) {
  const item = current.value;
  if (!item) return;
  current.value = null;
  item?.resolve(value);
  queueMicrotask(advance);
}
export function confirmAction(message, options = {}) {
  return request("confirm", message, {
    title: "确认操作",
    confirmText: "确认",
    danger: /删除|清理|撤销|停止/.test(message),
    ...options,
  });
}
export function promptText(message, value = "") {
  return request("prompt", message, {
    title: "编辑信息",
    confirmText: "保存",
    value,
  });
}
export function notify(
  message,
  type = /失败|错误|异常|无法/.test(message) ? "error" : "info",
) {
  const method = ["success", "error", "warning", "info"].includes(type)
    ? type
    : "info";
  toast[method](String(message), {
    duration: String(message).length > 180 ? Infinity : 7000,
  });
}
export const feedback = readonly(current);
