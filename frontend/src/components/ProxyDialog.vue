<template>
  <Dialog
    v-if="dialogVisible"
    :open="true"
    @update:open="
      (open) => {
        if (!open) {
          handleBackdropClick();
        }
      }
    "
    ><DialogContent class="sm:max-w-lg" :aria-describedby="undefined"
      ><DialogHeader
        ><DialogTitle>{{
          editingProxy ? "编辑代理" : "添加代理"
        }}</DialogTitle></DialogHeader
      >
      <div
        data-slot="dialog-body"
        class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
      >
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-gray-700"
            >代理名称 <span class="text-red-600">*</span></label
          ><Input
            type="text"
            class="block w-full"
            v-model="proxyForm.name"
            aria-label="代理名称"
            @input="handleNameInput"
            required
          ></Input
          ><small class="mt-1 block text-xs text-gray-500"
            >建议格式: 分组_服务类型（例如: dlyy_rdp）</small
          >
        </div>
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-gray-700"
            >分组名称</label
          ><Input
            type="text"
            class="block w-full"
            v-model="proxyForm.group_name"
            aria-label="分组名称"
            placeholder="留空则自动从名称解析"
          ></Input>
        </div>
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-gray-700"
            >代理类型 <span class="text-red-600">*</span></label
          ><Select v-model="proxyForm.proxy_type" required
            ><SelectTrigger aria-label="代理类型" class="w-full"
              ><SelectValue placeholder="请选择"></SelectValue></SelectTrigger
            ><SelectContent
              ><SelectItem value="tcp">TCP</SelectItem
              ><SelectItem value="udp">UDP</SelectItem
              ><SelectItem value="http">HTTP</SelectItem
              ><SelectItem value="https">HTTPS</SelectItem
              ><SelectItem value="stcp">STCP</SelectItem
              ><SelectItem value="xtcp">XTCP</SelectItem></SelectContent
            ></Select
          >
        </div>
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-gray-700"
            >本地 IP <span class="text-red-600">*</span></label
          ><Input
            type="text"
            class="block w-full"
            v-model="proxyForm.local_ip"
            required
          ></Input>
        </div>
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-gray-700"
            >本地端口 <span class="text-red-600">*</span></label
          ><Input
            type="number"
            class="block w-full"
            v-model.number="proxyForm.local_port"
            min="0"
            max="65535"
            required
          ></Input
          ><small class="mt-1 block text-xs text-gray-500"
            >输入 0 可根据名称自动识别</small
          >
        </div>
        <div class="mb-0">
          <label class="mb-1 block text-sm font-medium text-gray-700"
            >远程端口</label
          ><Input
            type="number"
            class="block w-full"
            v-model.number="proxyForm.remote_port"
            min="1"
            max="65535"
          ></Input
          ><small class="mt-1 block text-xs text-gray-500"
            >TCP/UDP 类型需要</small
          >
        </div>
      </div>
      <DialogFooter
        ><Button
          type="button"
          class="w-full sm:mr-auto sm:w-auto"
          @click="closeDialog"
          variant="outline"
          size="default"
        >
          取消 </Button
        ><Button
          type="button"
          class="w-full sm:w-auto"
          @click="handleSubmit"
          variant="default"
          size="default"
        >
          保存
        </Button></DialogFooter
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
import { Select } from "@/components/ui/select";
import { SelectContent } from "@/components/ui/select";
import { SelectItem } from "@/components/ui/select";
import { SelectTrigger } from "@/components/ui/select";
import { SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { notify } from "@/composables/useFeedback";
import { ref, reactive, watch } from "vue";
import { useProxiesStore } from "@/stores/proxies";
import { autoDetectLocalPort } from "@/utils/portDetector";

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  serverId: {
    type: Number,
    default: null,
  },
  proxy: {
    type: Object,
    default: null,
  },
  groupName: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue", "success"]);

const proxiesStore = useProxiesStore();
const dialogVisible = ref(false);
const editingProxy = ref(null);

const proxyForm = reactive({
  name: "",
  group_name: "",
  proxy_type: "tcp",
  local_ip: "127.0.0.1",
  local_port: 0,
  remote_port: null,
});

watch(
  () => props.modelValue,
  (val) => {
    dialogVisible.value = val;
    if (val) {
      if (props.proxy) {
        editingProxy.value = props.proxy;
        Object.assign(proxyForm, {
          name: props.proxy.name,
          group_name: props.proxy.group_name || "",
          proxy_type: props.proxy.proxy_type,
          local_ip: props.proxy.local_ip,
          local_port: props.proxy.local_port,
          remote_port: props.proxy.remote_port,
        });
      } else {
        resetForm();
      }
    }
  },
);

watch(dialogVisible, (val) => {
  emit("update:modelValue", val);
  if (!val) {
    resetForm();
  }
});

const closeDialog = () => {
  dialogVisible.value = false;
};

// 使用统一的模态框功能

const handleNameInput = () => {
  if (proxyForm.local_port === 0) {
    const detectedPort = autoDetectLocalPort(proxyForm.name);
    if (detectedPort > 0) {
      proxyForm.local_port = detectedPort;
    }
  }

  if (!proxyForm.group_name && proxyForm.name) {
    const parts = proxyForm.name.split("_");
    if (parts.length > 1) {
      proxyForm.group_name = parts[0];
    }
  }
};

const handleSubmit = async () => {
  if (
    !proxyForm.name ||
    !proxyForm.proxy_type ||
    !proxyForm.local_ip ||
    proxyForm.local_port === null
  ) {
    notify("请填写必填项");
    return;
  }

  if (!props.serverId) {
    notify("请先选择服务器");
    return;
  }

  try {
    const data = {
      ...proxyForm,
      frps_server_id: props.serverId,
    };

    if (editingProxy.value) {
      await proxiesStore.updateProxy(editingProxy.value.id, data);
      notify("更新成功");
    } else {
      await proxiesStore.addProxy(data);
      notify("添加成功");
    }

    dialogVisible.value = false;
    emit("success");
    resetForm();
  } catch (error) {
    notify("操作失败: " + error.message);
  }
};

const resetForm = () => {
  editingProxy.value = null;
  Object.assign(proxyForm, {
    name: "",
    group_name: props.groupName,
    proxy_type: "tcp",
    local_ip: "127.0.0.1",
    local_port: 0,
    remote_port: null,
  });
};

const handleClose = () => {
  resetForm();
};

const handleBackdropClick = () => {
  closeDialog();
};
</script>
