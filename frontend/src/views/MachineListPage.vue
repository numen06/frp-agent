<script setup>
import { ref, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { machinesApi, managedHostsApi } from "@/api/managedHosts";
import { usePagedList } from "@/composables/usePagedList";
import PageHeader from "@/components/PageHeader.vue";
import SearchField from "@/components/SearchField.vue";
import ResourceCombobox from "@/components/ResourceCombobox.vue";
import TablePagination from "@/components/TablePagination.vue";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
const route = useRoute(),
  router = useRouter();
const admin = ref(false),
  contextError = ref(""),
  group = ref(String(route.query.group_key || ""));
const list = usePagedList((params) =>
  machinesApi.list({ ...params, group_key: group.value || undefined }),
);
list.search.value = String(route.query.search || "");
async function load(page = 1) {
  await router.replace({
    query: {
      group_key: group.value || undefined,
      search: list.search.value || undefined,
      page,
    },
  });
  await list.load(page);
}
async function init() {
  contextError.value = "";
  try {
    admin.value = (await managedHostsApi.context()).is_admin;
    await list.load(Number(route.query.page) || 1);
  } catch (e) {
    contextError.value = e.message;
  }
}
onMounted(init);
watch(
  () => route.query,
  (query) => {
    const nextGroup = String(query.group_key || ""),
      search = String(query.search || "");
    if (nextGroup !== group.value || search !== list.search.value) {
      group.value = nextGroup;
      list.search.value = search;
      list.load(Number(query.page) || 1);
    }
  },
);
</script>
<template>
  <div class="space-y-4">
    <PageHeader
      title="主机资源"
      description="按组组织主机；每台主机可分别配置 SSH、VNC、RDP 和 Docker 连接服务。"
    >
      <Button as-child variant="outline"
        ><router-link to="/hosts">按连接查看</router-link></Button
      >
      <Button v-if="admin" as-child
        ><router-link to="/machines/new">添加主机</router-link></Button
      >
    </PageHeader>
    <Card class="gap-4 p-4 sm:p-5" aria-label="主机列表">
      <form class="flex flex-wrap gap-3" @submit.prevent="load(1)">
        <SearchField
          v-model="list.search.value"
          label="搜索主机"
          placeholder="主机名称或分组"
          class="min-w-0 flex-1 basis-48"
          @search="load(1)"
        />
        <ResourceCombobox
          v-model="group"
          label="筛选分组"
          allow-clear
          clear-label="全部分组"
          class="min-w-0 flex-1 basis-48"
          :fetch-options="machinesApi.groups"
          :resolve-option="
            async (id) => ({
              id,
              name:
                id === 'ungrouped'
                  ? '未分组'
                  : id.split(':').slice(1).join(':'),
            })
          "
          @select="load(1)"
        />
        <Button
          v-if="admin"
          type="button"
          variant="outline"
          @click="
            group = 'ungrouped';
            load(1);
          "
          >未分组</Button
        >
        <Button
          type="button"
          variant="outline"
          :disabled="list.loading.value"
          @click="init"
          >刷新</Button
        >
      </form>
      <div
        v-if="contextError || list.error.value"
        role="alert"
        class="space-y-3 text-sm text-destructive"
      >
        <p>{{ contextError || list.error.value }}</p>
        <Button variant="outline" @click="init">重试读取</Button>
      </div>
      <p
        v-else-if="list.loading.value"
        role="status"
        class="text-sm text-muted-foreground"
      >
        正在读取主机…
      </p>
      <p
        v-else-if="!list.items.value.length"
        class="py-6 text-sm text-muted-foreground"
      >
        暂无可见主机，请添加主机或调整筛选条件。
      </p>
      <div v-else class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Card
          v-for="machine in list.items.value"
          :key="machine.id"
          class="min-w-0 gap-3 p-4"
        >
          <router-link
            :to="`/machines/${machine.id}`"
            class="inline-flex min-h-11 items-center break-all font-semibold text-primary"
            >{{ machine.name }}</router-link
          >
          <p class="break-words text-xs text-muted-foreground">
            {{
              machine.group_name
                ? `${machine.server_name} / ${machine.group_name}`
                : "未分组"
            }}
          </p>
          <p class="text-sm">{{ machine.service_count }} 个可见连接服务</p>
          <Button as-child variant="outline"
            ><router-link :to="`/machines/${machine.id}`"
              >查看主机</router-link
            ></Button
          >
        </Card>
      </div>
      <TablePagination
        v-bind="{
          total: list.pagination.total,
          page: list.pagination.page,
          pageSize: list.pagination.page_size,
        }"
        @page-change="load"
        @page-size-change="
          (size) => {
            list.pagination.page_size = size;
            load(1);
          }
        "
      />
    </Card>
  </div>
</template>
