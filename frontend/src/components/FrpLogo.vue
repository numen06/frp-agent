<template>
  <svg 
    xmlns="http://www.w3.org/2000/svg" 
    :class="iconClass" 
    :width="size" 
    :height="size" 
    viewBox="0 0 48 48" 
    :style="{ color: color }"
  >
    <!-- 左侧节点 -->
    <circle cx="8" cy="24" r="4" :fill="color" opacity="0.9"/>
    <circle cx="8" cy="24" r="6" :fill="none" :stroke="color" stroke-width="1.5" opacity="0.3"/>
    
    <!-- 右侧节点 -->
    <circle cx="40" cy="24" r="4" :fill="color" opacity="0.9"/>
    <circle cx="40" cy="24" r="6" :fill="none" :stroke="color" stroke-width="1.5" opacity="0.3"/>
    
    <!-- 隧道/连接线 -->
    <path 
      d="M 14 24 Q 24 16, 34 24 Q 24 32, 14 24" 
      :fill="none" 
      :stroke="color" 
      stroke-width="2.5" 
      stroke-linecap="round"
      opacity="0.8"
    />
    
    <!-- 数据流动效果 -->
    <circle 
      v-if="animated" 
      class="data-flow"
      cx="14" 
      cy="24" 
      r="2" 
      :fill="color"
      opacity="0.9"
    />
    
    <!-- 装饰性连接点 -->
    <circle cx="24" cy="20" r="1.5" :fill="color" opacity="0.6"/>
    <circle cx="24" cy="28" r="1.5" :fill="color" opacity="0.6"/>
  </svg>
</template>

<script setup>
defineProps({
  size: {
    type: [Number, String],
    default: 24
  },
  color: {
    type: String,
    default: 'currentColor'
  },
  iconClass: {
    type: String,
    default: 'icon'
  },
  animated: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.data-flow {
  animation: flow 2s ease-in-out infinite;
}

@keyframes flow {
  0% {
    transform: translate(0, 0);
    opacity: 0.9;
  }
  25% {
    transform: translate(10px, -8px);
    opacity: 0.7;
  }
  50% {
    transform: translate(20px, 0);
    opacity: 0.9;
  }
  75% {
    transform: translate(10px, 8px);
    opacity: 0.7;
  }
  100% {
    transform: translate(0, 0);
    opacity: 0.9;
  }
}
</style>

