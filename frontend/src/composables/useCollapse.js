import { ref } from 'vue'

/**
 * 折叠面板开关（如侧栏/导航），与具体 UI 库无关。
 */
export function useCollapse() {
  const isOpen = ref(false)

  const toggle = () => {
    isOpen.value = !isOpen.value
  }

  const open = () => {
    isOpen.value = true
  }

  const close = () => {
    isOpen.value = false
  }

  return {
    isOpen,
    toggle,
    open,
    close
  }
}

