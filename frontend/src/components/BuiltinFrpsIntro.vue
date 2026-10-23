<template>
  <AppDialog :model-value="pending && !blocked" title="选择 FRP 部署方式" :busy="busy" panel-class="max-w-lg" @update:model-value="dismiss">
    <p class="text-sm leading-6 text-gray-600">本项目镜像已内置官方 FRP 服务端，无需再单独部署 frps。你可以前往“服务器管理”配置并启用，也可以继续使用已有的外部 FRP 服务器。</p>
    <p class="mt-3 text-xs text-gray-500">内置 FRP 默认关闭。此提示在本实例首次由管理员登录时出现，选择后不再重复弹出；以后可在服务器管理页自行切换。</p>
    <p v-if="error" role="alert" class="mt-3 text-sm text-red-600">{{ error }}</p>
    <template #footer><button type="button" class="btn btn-md btn-outline" :disabled="busy" @click="choose(false)">暂不启用</button><button type="button" class="btn btn-md btn-primary" :disabled="busy" @click="choose(true)">前往配置</button></template>
  </AppDialog>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppDialog from './AppDialog.vue'
import { builtinFrpsApi } from '@/api/builtinFrps'
defineProps({ blocked: Boolean })
const router = useRouter(), pending = ref(false), busy = ref(false), error = ref('')
onMounted(async () => {
  try { pending.value = !(await builtinFrpsApi.get()).onboarding_seen } catch (e) { error.value = e.message }
})
async function choose(configure) {
  if (busy.value) return
  busy.value = true; error.value = ''
  try {
    await builtinFrpsApi.acknowledge()
    pending.value = false
    if (configure) await router.push('/servers#builtin-frps')
  } catch (e) { error.value = e.message } finally { busy.value = false }
}
function dismiss(value) { if (!value && pending.value) choose(false) }
</script>
