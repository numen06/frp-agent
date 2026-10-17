import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'

/**
 * 下拉菜单组合式函数
 * 纯 Vue 实现，不依赖任何 UI 框架
 */
export function useDropdown({ floating = false } = {}) {
  const isOpen = ref(false)
  const dropdownRef = ref(null)
  const triggerRef = ref(null)
  const floatingStyle = ref({})

  const position = () => {
    if (!floating || !triggerRef.value) return
    const rect = triggerRef.value.getBoundingClientRect()
    const viewport = window.visualViewport
    const left = viewport?.offsetLeft || 0
    const top = viewport?.offsetTop || 0
    const width = viewport?.width || window.innerWidth
    const height = viewport?.height || window.innerHeight
    const menu = dropdownRef.value?.getBoundingClientRect()
    const menuWidth = Math.min(menu?.width || 176, width - 16)
    const below = top + height - rect.bottom - 16
    const above = rect.top - top - 16
    const useAbove = (menu?.height || 96) > below && above > below
    const maxHeight = Math.max(44, useAbove ? above : below)
    const menuHeight = Math.min(menu?.height || 96, maxHeight)
    floatingStyle.value = {
      left: `${Math.max(left + 8, Math.min(rect.left, left + width - menuWidth - 8))}px`,
      top: `${Math.max(top + 8, useAbove ? rect.top - menuHeight - 8 : rect.bottom + 8)}px`,
      maxWidth: `${width - 16}px`, maxHeight: `${maxHeight}px`, overflowY: 'auto',
    }
  }

  const toggle = () => {
    if (isOpen.value) close()
    else open()
  }

  const open = () => {
    if (floating && !triggerRef.value) return
    position()
    isOpen.value = true
  }

  const close = () => {
    isOpen.value = false
  }

  const escape = event => { if (event.key === 'Escape') close() }
  const listen = active => {
    const method = active ? 'addEventListener' : 'removeEventListener'
    window[method]('resize', position)
    window[method]('scroll', position, true)
    window.visualViewport?.[method]('resize', position)
    window.visualViewport?.[method]('scroll', position)
    document[method]('keydown', escape)
  }
  watch(isOpen, async value => {
    listen(value)
    if (value) { await nextTick(); position() }
  })

  const handleClickOutside = (event) => {
    if (
      dropdownRef.value &&
      triggerRef.value &&
      !dropdownRef.value.contains(event.target) &&
      !triggerRef.value.contains(event.target)
    ) {
      close()
    }
  }

  onMounted(() => {
    document.addEventListener('click', handleClickOutside)
  })

  onUnmounted(() => {
    listen(false)
    document.removeEventListener('click', handleClickOutside)
  })

  return {
    isOpen,
    dropdownRef,
    triggerRef,
    floatingStyle,
    toggle,
    open,
    close
  }
}
