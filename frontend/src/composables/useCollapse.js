import { ref } from 'vue'

/**
 * Tabler 折叠组件组合式函数
 * 用于导航栏折叠功能
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

