import { ref } from 'vue'

// 全局刷新事件状态
const refreshEvent = ref(0)

/**
 * 用于触发和监听全局刷新事件的 composable
 * 主要用于在同步操作后通知 Dashboard 刷新统计数据
 */
export function useRefresh() {
  /**
   * 触发刷新事件
   */
  const triggerRefresh = () => {
    refreshEvent.value = Date.now()
  }

  /**
   * 获取当前刷新事件的时间戳
   * 可以在 watch 中监听这个值的变化来触发刷新
   */
  const getRefreshEvent = () => {
    return refreshEvent.value
  }

  return {
    triggerRefresh,
    getRefreshEvent,
    refreshEvent
  }
}

