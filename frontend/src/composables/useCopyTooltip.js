import { ref } from 'vue'

const TOOLTIP_DURATION = 1500

function createTooltipEl() {
  const el = document.createElement('span')
  el.textContent = '已复制'
  el.className =
    'copy-tooltip-popup'
  el.style.cssText = `
    position: fixed;
    z-index: 99999;
    padding: 4px 10px;
    font-size: 12px;
    line-height: 1.4;
    color: #fff;
    background: rgba(0,0,0,0.72);
    border-radius: 6px;
    pointer-events: none;
    white-space: nowrap;
    opacity: 0;
    transform: translateY(2px);
    transition: opacity .2s, transform .2s;
  `
  document.body.appendChild(el)
  return el
}

/**
 * 复制文本并在触发元素旁显示轻量悬浮提示 "已复制"
 * @param {string} text - 要复制的文本
 * @param {Event|HTMLElement} trigger - click 事件或 DOM 元素
 * @returns {Promise<boolean>} 是否成功
 */
export async function copyWithTooltip(text, trigger) {
  let ok = false
  try {
    await navigator.clipboard.writeText(text)
    ok = true
  } catch {
    try {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.cssText = 'position:fixed;left:-9999px;opacity:0'
      document.body.appendChild(ta)
      ta.focus()
      ta.select()
      ok = document.execCommand('copy')
      document.body.removeChild(ta)
    } catch {
      ok = false
    }
  }

  if (ok) {
    const src = trigger instanceof Event ? trigger.currentTarget || trigger.target : trigger
    if (src instanceof HTMLElement) {
      showCopyTooltip(src)
    }
  }

  return ok
}

function showCopyTooltip(anchor) {
  const el = createTooltipEl()

  const rect = anchor.getBoundingClientRect()
  el.style.left = `${rect.left + rect.width / 2}px`
  el.style.top = `${rect.top - 8}px`
  el.style.transform = 'translate(-50%, -100%)'

  requestAnimationFrame(() => {
    el.style.opacity = '1'
    el.style.transform = 'translate(-50%, -100%)'
  })

  setTimeout(() => {
    el.style.opacity = '0'
    el.style.transform = 'translate(-50%, calc(-100% - 4px))'
    setTimeout(() => el.remove(), 220)
  }, TOOLTIP_DURATION)
}
