import { onUnmounted, watch } from 'vue'

// 全局计数器，跟踪打开的模态框数量
let modalCount = 0
// 存储所有活动的模态框处理器
const activeModals = []

/**
 * 统一的模态框组合式函数
 * 提供 ESC 退出功能和遮罩层管理
 * 
 * @param {Ref} visible - 模态框可见性状态
 * @param {Function} onClose - 关闭回调函数
 */
export function useModal(visible, onClose) {
  // 创建模态框处理器对象
  const modalHandler = {
    visible,
    onClose
  }

  // 全局 ESC 键监听器
  const globalEscapeHandler = (event) => {
    if (event.key === 'Escape') {
      // 找到最上层的可见模态框并关闭它（从后往前查找）
      for (let i = activeModals.length - 1; i >= 0; i--) {
        const handler = activeModals[i]
        if (handler.visible && handler.visible.value && handler.onClose) {
          handler.onClose()
          break
        }
      }
    }
  }

  // 监听 visible 变化，动态添加/移除 ESC 监听器
  watch(visible, (isVisible) => {
    if (isVisible) {
      modalCount++
      // 添加当前处理器到数组
      activeModals.push(modalHandler)
      
      // 只在第一个模态框打开时添加全局监听器
      if (modalCount === 1) {
        document.addEventListener('keydown', globalEscapeHandler)
      }
      
      // 防止背景滚动
      document.body.style.overflow = 'hidden'
    } else {
      modalCount--
      // 移除当前处理器
      const index = activeModals.indexOf(modalHandler)
      if (index > -1) {
        activeModals.splice(index, 1)
      }
      
      // 当所有模态框都关闭时，移除全局监听器并恢复滚动
      if (modalCount === 0) {
        document.removeEventListener('keydown', globalEscapeHandler)
        document.body.style.overflow = ''
      }
    }
  }, { immediate: true })

  // 组件卸载时清理
  onUnmounted(() => {
    if (visible.value) {
      modalCount--
      const index = activeModals.indexOf(modalHandler)
      if (index > -1) {
        activeModals.splice(index, 1)
      }
      
      if (modalCount === 0) {
        document.removeEventListener('keydown', globalEscapeHandler)
        document.body.style.overflow = ''
      }
    }
  })

  return {
    handleEscape: globalEscapeHandler
  }
}

