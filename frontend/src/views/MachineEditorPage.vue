<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { machinesApi } from "@/api/managedHosts";
import { confirmAction, notify } from "@/composables/useFeedback";
import PageHeader from "@/components/PageHeader.vue";
import ResourceCombobox from "@/components/ResourceCombobox.vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
const route = useRoute(),
  router = useRouter(),
  id = computed(() => Number(route.params.id) || null);
const form = reactive({ name: "", group_key: null, description: "" });
const loading = ref(false),
  busy = ref(false),
  error = ref(""),
  original = ref("");
const dirty = computed(
  () => original.value && original.value !== JSON.stringify(form),
);
async function load() {
  loading.value = true;
  original.value = "";
  error.value = "";
  try {
    if (id.value) {
      const value = await machinesApi.get(id.value);
      Object.assign(form, {
        name: value.name,
        group_key: value.group_key,
        description: value.description || "",
      });
    } else Object.assign(form, { name: "", group_key: null, description: "" });
    original.value = JSON.stringify(form);
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}
async function save() {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    const value = id.value
      ? await machinesApi.update(id.value, form)
      : await machinesApi.create(form);
    original.value = JSON.stringify(form);
    notify("主机已保存", "success");
    await router.replace(`/machines/${value.id}`);
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
function beforeUnload(event) {
  if (dirty.value) {
    event.preventDefault();
    event.returnValue = "";
  }
}
function canLeave() {
  return (
    !dirty.value ||
    confirmAction("主机信息尚未保存，确定放弃修改？", {
      confirmText: "放弃修改",
    })
  );
}
onBeforeRouteLeave(canLeave);
onBeforeRouteUpdate((to, from) => to.path === from.path || canLeave());
watch(() => route.params.id, load);
onMounted(() => {
  load();
  window.addEventListener("beforeunload", beforeUnload);
});
onUnmounted(() => window.removeEventListener("beforeunload", beforeUnload));
</script>
<template>
  <div class="space-y-4">
    <PageHeader
      :title="id ? '编辑主机' : '添加主机'"
      description="主机代表一台设备。保存后可独立添加 SSH、VNC、RDP 等连接服务。"
    />
    <Card v-if="loading" class="p-5" role="status">正在读取主机…</Card>
    <form v-else class="space-y-4" @submit.prevent="save">
      <Card class="gap-4 p-4 sm:p-5">
        <label class="space-y-2 text-sm"
          >主机名称<Input
            v-model.trim="form.name"
            required
            maxlength="100"
            :disabled="busy"
        /></label>
        <label class="space-y-2 text-sm"
          >所属分组<ResourceCombobox
            v-model="form.group_key"
            label="选择分组（可选）"
            allow-clear
            clear-label="未分组"
            :fetch-options="machinesApi.groups"
            :resolve-option="
              async (key) => ({
                id: key,
                name: key.split(':').slice(1).join(':'),
              })
            "
            :disabled="busy"
        /></label>
        <label class="space-y-2 text-sm"
          >描述<Textarea
            v-model="form.description"
            maxlength="2000"
            :disabled="busy"
        /></label>
      </Card>
      <div v-if="error" role="alert" class="space-y-3 text-sm text-destructive">
        <p>{{ error }}</p>
        <Button v-if="!original" type="button" variant="outline" @click="load"
          >重试读取</Button
        >
      </div>
      <Card class="flex-row flex-wrap justify-end gap-2 p-4"
        ><Button as-child variant="outline"
          ><router-link :to="id ? `/machines/${id}` : '/machines'"
            >取消</router-link
          ></Button
        ><Button type="submit" :disabled="busy || !original">{{
          busy ? "保存中…" : "保存主机"
        }}</Button></Card
      >
    </form>
  </div>
</template>
