<template>
  <Dialog
    v-if="pending && !blocked"
    :open="true"
    @update:open="
      (open) => {
        if (!busy) {
          dismiss(open);
        }
      }
    "
    ><DialogContent
      class="sm:max-w-lg"
      :aria-describedby="undefined"
      :show-close-button="!busy"
      @escape-key-down="
        (e) => {
          if (busy) e.preventDefault();
        }
      "
      @interact-outside="
        (e) => {
          if (busy) e.preventDefault();
        }
      "
      ><DialogHeader><DialogTitle>选择 FRP 部署方式</DialogTitle></DialogHeader>
      <div
        data-slot="dialog-body"
        class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
      >
        <p class="text-sm leading-6 text-gray-600">
          本项目镜像已内置官方 FRP 服务端，无需再单独部署
          frps。你可以前往“穿透服务 →
          内置服务”配置并启用，也可以继续使用已有的外部 FRP 服务器。
        </p>
        <p class="mt-3 text-xs text-gray-500">
          内置 FRP
          默认关闭。此提示在本实例首次由管理员登录时出现，选择后不再重复弹出；以后可在穿透服务的“内置服务”Tab
          自行切换。
        </p>
        <p v-if="error" role="alert" class="mt-3 text-sm text-red-600">
          {{ error }}
        </p>
      </div>
      <DialogFooter
        ><Button
          type="button"
          :disabled="busy"
          @click="choose(false)"
          variant="outline"
          size="default"
          >暂不启用</Button
        ><Button
          type="button"
          :disabled="busy"
          @click="choose(true)"
          variant="default"
          size="default"
          >前往配置</Button
        ></DialogFooter
      ></DialogContent
    ></Dialog
  >
</template>

<script setup>
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { builtinFrpsApi } from "@/api/builtinFrps";
defineProps({ blocked: Boolean });
const router = useRouter(),
  pending = ref(false),
  busy = ref(false),
  error = ref("");
onMounted(async () => {
  try {
    pending.value = !(await builtinFrpsApi.get()).onboarding_seen;
  } catch (e) {
    error.value = e.message;
  }
});
async function choose(configure) {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    await builtinFrpsApi.acknowledge();
    pending.value = false;
    if (configure) await router.push("/tunnel-services?tab=builtin");
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
function dismiss(value) {
  if (!value && pending.value) choose(false);
}
</script>
