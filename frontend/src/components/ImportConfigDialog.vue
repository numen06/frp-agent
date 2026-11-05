<template>
  <Dialog
    v-if="dialogVisible"
    :open="true"
    @update:open="
      (open) => {
        if (!open) {
          closeDialog();
        }
      }
    "
    ><DialogContent class="sm:max-w-lg" :aria-describedby="undefined"
      ><DialogHeader
        ><DialogTitle>导入 frpc 配置文件</DialogTitle></DialogHeader
      >
      <div
        data-slot="dialog-body"
        class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
      >
        <p class="mb-4 text-sm text-gray-600">
          上传 frpc 配置文件（INI 或 TOML 格式），系统将自动解析并导入代理信息。
        </p>
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-gray-700"
            >当前服务器</label
          ><Input
            type="text"
            class="block w-full cursor-not-allowed"
            readonly
            :model-value="currentServerName"
          ></Input>
        </div>
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-gray-700"
            >选择分组 <span class="text-red-600">*</span></label
          ><ResourceCombobox
            :scope-key="props.serverId"
            v-model="importForm.group_name"
            label="选择分组"
            :fetch-options="
              (params) => groupApi.getGroupsList(props.serverId, params)
            "
            :resolve-option="(value) => value"
            allow-clear
            clear-label="选择分组"
          /><small class="mt-1 block text-xs text-gray-500"
            >导入的代理将被分配到此分组</small
          >
        </div>
        <div class="mb-0">
          <label class="mb-1 block text-sm font-medium text-gray-700"
            >配置文件 <span class="text-red-600">*</span></label
          ><Input
            type="file"
            class="block w-full cursor-pointer file:mr-3 file:font-medium"
            @change="handleFileChange"
            accept=".ini,.toml"
            required
          ></Input
          ><small class="mt-1 block text-xs text-gray-500"
            >支持 .ini 和 .toml 格式的 frpc 配置文件</small
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
          @click="handleImport"
          :disabled="importing"
          variant="default"
          size="default"
          ><span
            v-if="importing"
            class="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-white/30 border-t-white"
            role="status"
            aria-label="导入中"
          ></span>
          开始导入
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
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { notify } from "@/composables/useFeedback";
import { groupApi } from "@/api/groups";
import ResourceCombobox from "@/components/ResourceCombobox.vue";
import { ref, reactive, computed, watch } from "vue";
import { useServersStore } from "@/stores/servers";
import { useGroupsStore } from "@/stores/groups";
import { configApi } from "@/api/config";

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  serverId: {
    type: Number,
    default: null,
  },
});

const emit = defineEmits(["update:modelValue", "success"]);

const serversStore = useServersStore();
const groupsStore = useGroupsStore();
const dialogVisible = ref(false);
const importing = ref(false);
const selectedFile = ref(null);

const importForm = reactive({
  group_name: "",
  file: null,
});

const currentServerName = computed(() => {
  const server = serversStore.currentServer;
  return server ? server.name : "";
});

const groupOptions = computed(() => {
  const groups = new Set();
  groupsStore.groups.forEach((g) => groups.add(g.group_name));
  return Array.from(groups).sort();
});

watch(
  () => props.modelValue,
  (val) => {
    dialogVisible.value = val;
    if (val && props.serverId) {
      // Options load on demand in the paged picker.
    }
  },
);

watch(dialogVisible, (val) => {
  emit("update:modelValue", val);
});

const closeDialog = () => {
  dialogVisible.value = false;
};

// 使用统一的模态框功能

const handleFileChange = (event) => {
  selectedFile.value = event.target.files[0];
  importForm.file = selectedFile.value ? selectedFile.value.name : null;
};

const handleImport = async () => {
  if (!importForm.group_name) {
    notify("请选择分组");
    return;
  }

  if (!selectedFile.value) {
    notify("请选择配置文件");
    return;
  }

  importing.value = true;

  try {
    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const content = e.target.result;
        const fileName = selectedFile.value.name;
        const format = fileName.endsWith(".toml") ? "toml" : "ini";
        const serverName = serversStore.currentServer?.name;

        if (!serverName) {
          notify("请先选择服务器");
          return;
        }

        await configApi.importConfigDirect(format, serverName, content);
        notify("导入成功");
        dialogVisible.value = false;
        emit("success");
        resetForm();
      } catch (error) {
        notify("导入失败: " + error.message);
      } finally {
        importing.value = false;
      }
    };
    reader.readAsText(selectedFile.value);
  } catch (error) {
    notify("读取文件失败: " + error.message);
    importing.value = false;
  }
};

const resetForm = () => {
  importForm.group_name = "";
  importForm.file = null;
  selectedFile.value = null;
};

const handleClose = () => {
  resetForm();
};
</script>
