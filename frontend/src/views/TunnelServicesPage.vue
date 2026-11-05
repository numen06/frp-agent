<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { settingsApi } from "@/api/settings";
import { useServersStore } from "@/stores/servers";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import ServerManagePage from "@/views/ServerManagePage.vue";
import BuiltinFrpsPanel from "@/components/BuiltinFrpsPanel.vue";

const route = useRoute(),
  router = useRouter();
const serversStore = useServersStore();
const role = ref(null),
  error = ref("");
const activeTab = computed(() =>
  route.query.tab === "builtin" && role.value === "admin"
    ? "builtin"
    : "servers",
);
function selectTab(tab) {
  router.replace({ path: "/tunnel-services", query: { ...route.query, tab } });
}
async function loadRole() {
  error.value = "";
  try {
    role.value = (await settingsApi.getUserSettings()).role;
  } catch (e) {
    error.value = e.message || "读取访问权限失败";
  }
}
watch([role, () => route.query.tab], ([value, tab]) => {
  if (
    value !== null &&
    tab &&
    (tab !== "builtin" || value !== "admin") &&
    tab !== "servers"
  )
    selectTab("servers");
});
onMounted(loadRole);
</script>

<template>
  <Card v-if="error" class="gap-3 p-4">
    <p role="alert" class="text-sm text-destructive">{{ error }}</p>
    <Button class="w-fit" variant="outline" @click="loadRole"
      >重试读取权限</Button
    >
  </Card>
  <p
    v-else-if="role === null"
    role="status"
    class="p-4 text-sm text-muted-foreground"
  >
    正在读取访问权限…
  </p>
  <Tabs
    v-else
    :model-value="activeTab"
    @update:model-value="selectTab"
    class="gap-4"
  >
    <Card class="px-2">
      <TabsList
        variant="line"
        aria-label="穿透服务分类"
        class="grid h-auto w-full grid-cols-2 sm:flex sm:justify-start"
      >
        <TabsTrigger value="servers">服务节点</TabsTrigger>
        <TabsTrigger v-if="role === 'admin'" value="builtin"
          >内置服务</TabsTrigger
        >
      </TabsList>
    </Card>
    <TabsContent :value="activeTab" force-mount>
      <ServerManagePage v-if="activeTab === 'servers'" />
      <BuiltinFrpsPanel v-else @changed="serversStore.loadServers(1)" />
    </TabsContent>
  </Tabs>
</template>
