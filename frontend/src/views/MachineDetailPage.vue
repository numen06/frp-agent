<script setup>
import { ref, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { machinesApi, managedHostsApi } from "@/api/managedHosts";
import { usePagedList } from "@/composables/usePagedList";
import { notify, confirmAction } from "@/composables/useFeedback";
import PageHeader from "@/components/PageHeader.vue";
import TablePagination from "@/components/TablePagination.vue";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
const route = useRoute(),
  router = useRouter();
const machine = ref(null),
  admin = ref(false),
  loading = ref(false),
  error = ref(""),
  busy = ref(false);
const services = usePagedList((params) =>
  managedHostsApi.list({ ...params, machine_id: Number(route.params.id) }),
);
async function load() {
  loading.value = true;
  error.value = "";
  machine.value = null;
  try {
    const [host, context] = await Promise.all([
      machinesApi.get(route.params.id),
      managedHostsApi.context(),
    ]);
    machine.value = host;
    admin.value = context.is_admin;
    await services.load(1);
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}
async function remove() {
  if (
    busy.value ||
    !(await confirmAction(
      `确定删除主机“${machine.value.name}”？仅允许删除没有连接服务的主机。`,
      { title: "删除空主机", danger: true, confirmText: "删除主机" },
    ))
  )
    return;
  busy.value = true;
  try {
    await machinesApi.remove(machine.value.id);
    notify("主机已删除", "success");
    await router.replace("/machines");
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
const kind = (value) =>
  ({ ssh: "SSH", vnc: "VNC", rdp: "RDP", docker: "Docker" })[value] || value;
onMounted(load);
watch(() => route.params.id, load);
</script>
<template>
  <div class="space-y-4">
    <PageHeader
      class="[&_.page-title]:break-all"
      :title="machine?.name || '主机详情'"
      description="同一主机的连接服务分别配置地址、端口、凭据及授权。"
    >
      <Button variant="outline" :disabled="loading" @click="load"
        >刷新主机</Button
      >
      <template #before
        ><router-link
          to="/machines"
          class="inline-flex min-h-11 items-center text-sm text-primary"
          >← 返回主机列表</router-link
        ></template
      >
      <template v-if="machine && admin"
        ><Button as-child variant="outline"
          ><router-link :to="`/machines/${machine.id}/edit`"
            >编辑主机</router-link
          ></Button
        ><Button as-child
          ><router-link
            :to="{ path: '/hosts/new', query: { machine_id: machine.id } }"
            >添加连接服务</router-link
          ></Button
        ></template
      >
    </PageHeader>
    <Card v-if="loading" class="p-5" role="status">正在读取主机…</Card>
    <Card v-else-if="error" class="gap-3 p-5"
      ><p role="alert" class="text-sm text-destructive">{{ error }}</p>
      <Button variant="outline" @click="load">重试读取</Button></Card
    >
    <template v-else-if="machine">
      <Card class="gap-2 p-4"
        ><p class="text-sm">
          所属分组：{{
            machine.group_name
              ? `${machine.server_name} / ${machine.group_name}`
              : "未分组"
          }}
        </p>
        <p
          class="whitespace-pre-wrap break-words text-sm text-muted-foreground"
        >
          {{ machine.description || "暂无描述" }}
        </p></Card
      >
      <Card class="gap-4 p-4 sm:p-5" aria-label="主机连接服务">
        <h2 class="font-semibold">连接服务</h2>
        <p class="text-xs leading-5 text-muted-foreground">
          主机分组不会扩大服务权限。SSH 指纹仅用于 SSH；直连 VNC 无需配置 SSH。
        </p>
        <div
          v-if="services.error.value"
          role="alert"
          class="space-y-2 text-sm text-destructive"
        >
          <p>{{ services.error.value }}</p>
          <Button variant="outline" @click="services.load()"
            >重试连接列表</Button
          >
        </div>
        <p
          v-else-if="!services.items.value.length"
          class="text-sm text-muted-foreground"
        >
          尚无可见连接服务。
        </p>
        <div v-else class="grid gap-4 md:grid-cols-2">
          <Card
            v-for="service in services.items.value"
            :key="service.id"
            class="min-w-0 gap-3 p-4"
          >
            <h3 class="break-all font-medium">
              {{ kind(service.host_type) }} · {{ service.name }}
            </h3>
            <p class="break-all text-sm text-muted-foreground">
              {{ service.address }}:{{ service.port }} ·
              {{ service.is_active ? "已启用" : "已停用" }}
            </p>
            <p class="text-xs text-muted-foreground">
              {{ service.last_message || "尚未检测" }}
            </p>
            <div class="flex flex-wrap gap-2">
              <Button as-child variant="outline"
                ><router-link :to="`/hosts/${service.id}`"
                  >查看连接</router-link
                ></Button
              >
              <Button
                v-if="
                  service.is_active &&
                  service.host_type === 'vnc' &&
                  service.permissions.includes('connect')
                "
                as-child
                ><router-link :to="`/hosts/${service.id}?tab=desktop`"
                  >远程桌面</router-link
                ></Button
              >
              <Button
                v-if="
                  service.is_active &&
                  service.host_type === 'ssh' &&
                  service.permissions.includes('execute')
                "
                as-child
                ><router-link :to="`/hosts/${service.id}?tab=terminal`"
                  >Web SSH</router-link
                ></Button
              >
              <Button as-child variant="outline"
                ><router-link
                  :to="{ path: '/hosts', query: { search: service.name } }"
                  >连接操作与审计</router-link
                ></Button
              >
              <Button v-if="admin" as-child variant="outline"
                ><router-link
                  :to="{
                    path: `/hosts/${service.id}/edit`,
                    query: { machine_id: machine.id },
                  }"
                  >编辑连接</router-link
                ></Button
              >
            </div>
          </Card>
        </div>
        <TablePagination
          v-bind="{
            total: services.pagination.total,
            page: services.pagination.page,
            pageSize: services.pagination.page_size,
          }"
          @page-change="services.load"
          @page-size-change="services.resize"
        />
      </Card>
      <Button
        v-if="admin && !machine.service_count"
        variant="outline"
        :disabled="busy"
        @click="remove"
        >删除空主机</Button
      >
    </template>
  </div>
</template>
