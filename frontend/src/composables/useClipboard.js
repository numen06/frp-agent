import { notify } from "./useFeedback";

function copyWithSelection(text, trigger) {
  const active = document.activeElement;
  const source = trigger?.currentTarget || trigger?.target || trigger;
  // Keep the temporary field inside the current modal's native focus scope.
  const container =
    active?.closest?.('[role="dialog"], [role="alertdialog"]') ||
    source?.closest?.('[role="dialog"], [role="alertdialog"]') ||
    document.body;
  const selection = document.getSelection();
  const ranges = selection
    ? Array.from({ length: selection.rangeCount }, (_, i) =>
        selection.getRangeAt(i).cloneRange(),
      )
    : [];
  const field = document.createElement("textarea");
  field.value = text;
  field.readOnly = true;
  field.tabIndex = -1;
  field.setAttribute("data-clipboard-copy", "");
  field.setAttribute("aria-hidden", "true");
  field.style.cssText =
    "position:fixed;top:0;left:0;width:1px;height:1px;padding:0;border:0;opacity:0;font-size:16px;pointer-events:none";
  try {
    container.appendChild(field);
    field.focus({ preventScroll: true });
    field.select();
    field.setSelectionRange(0, text.length);
    return document.execCommand("copy");
  } finally {
    field.remove();
    if (active?.isConnected) active.focus({ preventScroll: true });
    if (selection) {
      selection.removeAllRanges();
      for (const range of ranges) selection.addRange(range);
    }
  }
}

export async function copyText(text, trigger) {
  const value = text == null ? "" : String(text);
  if (!value) {
    notify("没有可复制的内容", "error");
    return false;
  }
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      notify("已复制", "success");
      return true;
    }
  } catch {
    // HTTP pages and restricted Clipboard API permissions can still allow selection copying.
  }
  try {
    if (copyWithSelection(value, trigger)) {
      notify("已复制", "success");
      return true;
    }
  } catch {
    // Report failure only after both browser copy methods have failed.
  }
  notify("复制失败，请选中文字后手动复制", "error");
  return false;
}

export function formatCredentialExpiry(value) {
  return value ? new Date(value).toLocaleString("zh-CN", { timeZoneName: "short" }) : "—";
}

export function formatTemporaryCredential(credential) {
  const isVnc = credential.protocol === "vnc";
  const protocol = isVnc ? "VNC（Mac 屏幕共享）" : "RDP（Windows 远程桌面）";
  const target = credential.target.replace(/\s+/g, " ").trim();
  return [
    `连接类型：${protocol}`,
    `连接名称：${target}`,
    `地址：${credential.address}`,
    `账号：${credential.username}`,
    `密码：${credential.password}`,
    `有效至：${formatCredentialExpiry(credential.expires_at)}${isVnc ? "（仅可连接一次）" : ""}`,
  ].join("\n");
}

export async function copyDeferredText(load, trigger) {
  const value = load();
  if (navigator.clipboard?.write && typeof ClipboardItem !== "undefined") {
    try {
      // Safari requires starting the clipboard write inside the click handler.
      const item = new ClipboardItem({
        "text/plain": value.then((text) => new Blob([text], { type: "text/plain" })),
      });
      await navigator.clipboard.write([item]);
      notify("已复制", "success");
      return true;
    } catch {
      // Try the normal clipboard fallbacks or propagate the API error.
    }
  }
  return copyText(await value, trigger);
}
