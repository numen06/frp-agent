<template>
  <div class="space-y-1 text-xs text-gray-600" title="FRP 服务端统计：入站/出站按 frps 方向，流量为采集时 frps 当日计数；重启可能清零。连接数为采集时快照。">
    <p class="whitespace-nowrap">入 {{ formatBytes(proxy.today_traffic_in) }} · 出 {{ formatBytes(proxy.today_traffic_out) }}</p>
    <p>连接 {{ proxy.cur_conns ?? '未采集' }}</p>
    <p v-if="proxy.traffic_updated_at" class="text-gray-400">采集 {{ sampledAt }}</p>
    <p v-else class="text-gray-400">同步后更新</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatBytes } from '@/utils/traffic'
const props = defineProps({ proxy: { type: Object, required: true } })
const sampledAt = computed(() => {
  const value = props.proxy.traffic_updated_at
  if (!value) return ''
  return new Date(/[Zz]$|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`).toLocaleString('zh-CN')
})
</script>
