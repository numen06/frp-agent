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
