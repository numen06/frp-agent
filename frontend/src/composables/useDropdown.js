import { ref, onMounted, onUnmounted } from 'vue'

/**
 * 下拉菜单组合式函数
 * 纯 Vue 实现，不依赖任何 UI 框架
 */
export function useDropdown() {
  const isOpen = ref(false)
  const dropdownRef = ref(null)
  const triggerRef = ref(null)

  const toggle = () => {
    isOpen.value = !isOpen.value
  }

  const open = () => {
    isOpen.value = true
  }

  const close = () => {
    isOpen.value = false
  }

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
    document.removeEventListener('click', handleClickOutside)
  })

  return {
    isOpen,
    dropdownRef,
    triggerRef,
    toggle,
    open,
    close
  }
}
