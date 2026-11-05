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
    ><DialogContent class="sm:max-w-3xl" :aria-describedby="undefined"
      ><DialogHeader
        ><DialogTitle>{{ title }}</DialogTitle></DialogHeader
      >
      <div
        data-slot="dialog-body"
        class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
      >
        <div v-if="showClientName" class="mb-4">
          <label class="mb-1 block text-sm font-medium text-gray-700"
            >配置名称</label
          ><Input
            v-model="form.client_name"
            type="text"
            class="w-full transition-colors"
            placeholder="留空则使用分组名称"
          ></Input>
        </div>
        <div class="mb-4">
          <span class="mb-2 block text-sm font-medium text-gray-700"
            >配置格式</span
          ><RadioGroup
            class="grid grid-cols-1 gap-3 sm:grid-cols-2"
            v-model="form.format"
            ><label
              class="flex cursor-pointer rounded-xl border-2 p-4 transition-colors"
              :class="
                form.format === 'ini'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              "
            >
              <RadioGroupItem value="ini" class="sr-only"></RadioGroupItem>
              <div>
                <div class="font-semibold text-gray-900">INI 格式</div>
                <div class="mt-0.5 text-sm text-gray-500">兼容旧版本 FRP</div>
              </div> </label
            ><label
              class="flex cursor-pointer rounded-xl border-2 p-4 transition-colors"
              :class="
                form.format === 'toml'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              "
            >
              <RadioGroupItem value="toml" class="sr-only"></RadioGroupItem>
              <div>
                <div class="font-semibold text-gray-900">TOML 格式</div>
                <div class="mt-0.5 text-sm text-gray-500">推荐，新版本 FRP</div>
              </div>
            </label></RadioGroup
          >
        </div>
        <div
          v-if="selectedProxies.length > 0"
          class="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900"
        >
          <strong class="font-semibold">已选择的代理：</strong>
          <div class="mt-2 flex flex-wrap gap-1.5">
            <span
              v-for="proxy in selectedProxies"
              :key="proxy.id"
              class="inline-flex rounded-md bg-blue-600 px-2 py-0.5 text-xs font-medium text-white"
            >
              {{ proxy.name }}
            </span>
          </div>
        </div>
        <div v-if="configContent" class="border-t border-gray-200 pt-4">
          <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
            <span class="text-sm font-medium text-gray-700">配置内容</span>
            <div
              class="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:flex-wrap"
            >
              <Button
                v-if="props.groupName"
                type="button"
                class="w-full gap-1.5 sm:w-auto"
                aria-label="重新生成远端端口"
                :disabled="regeneratingPorts"
                @click="handleRegeneratePorts"
                variant="outline"
                size="sm"
                ><span
                  v-if="regeneratingPorts"
                  class="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white"
                  role="status"
                  aria-label="加载中"
                /><svg
                  v-else
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-4 w-4 shrink-0"
                  viewBox="0 0 24 24"
                  stroke-width="2"
                  stroke="currentColor"
                  fill="none"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                  <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4" />
                  <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4" />
                </svg>
                重新生成远端端口 </Button
              ><Button
                type="button"
                class="w-full gap-1.5 sm:w-auto"
                @click="downloadConfig"
                variant="outline"
                size="sm"
                ><svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-4 w-4 shrink-0"
                  viewBox="0 0 24 24"
                  stroke-width="2"
                  stroke="currentColor"
                  fill="none"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                  <path d="M14 3v4a1 1 0 0 0 1 1h4" />
                  <path
                    d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z"
                  />
                  <path d="M12 11v6" />
                  <path d="M9 14l3 -3l3 3" />
                </svg>
                下载配置
              </Button>
            </div>
          </div>
          <div class="min-h-[200px] overflow-x-auto">
            <CodeEditor
              v-model="configContent"
              language="yaml"
              :height="editorHeight"
              :readonly="true"
            />
          </div>
        </div>
      </div>
      <DialogFooter
        ><Button
          type="button"
          class="w-full sm:mr-auto sm:w-auto"
          @click="closeDialog"
          variant="ghost"
          size="default"
        >
          关闭 </Button
        ><Button
          type="button"
          class="w-full sm:w-auto"
          :disabled="generating"
          @click="handleGenerate"
          variant="default"
          size="default"
          ><span
            v-if="generating"
            class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
            role="status"
            aria-label="加载中"
          /><svg
            v-else
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4 shrink-0"
            viewBox="0 0 24 24"
            stroke-width="2"
            stroke="currentColor"
            fill="none"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path stroke="none" d="M0 0h24v24H0z" fill="none" />
            <path d="M14 3v4a1 1 0 0 0 1 1h4" />
            <path
              d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z"
            />
          </svg>
          生成配置文件
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
import { RadioGroup } from "@/components/ui/radio-group";
import { RadioGroupItem } from "@/components/ui/radio-group";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { notify, confirmAction } from "@/composables/useFeedback";
import { ref, reactive, computed, watch, onMounted, onUnmounted } from "vue";
import { frpcConfigApi } from "@/api/frpcConfig";
import { groupApi } from "@/api/groups";
import CodeEditor from "@/components/CodeEditor.vue";

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  serverId: {
    type: Number,
    required: true,
  },
  groupName: {
    type: String,
    default: "",
  },
  selectedProxies: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(["update:modelValue"]);

const dialogVisible = ref(false);
const generating = ref(false);
const regeneratingPorts = ref(false);
const configContent = ref("");
const editorHeight = ref("420px");

const updateEditorHeight = () => {
  editorHeight.value = window.matchMedia("(max-width: 639px)").matches
    ? "240px"
    : "420px";
};

onMounted(() => {
  updateEditorHeight();
  window.addEventListener("resize", updateEditorHeight);
});

onUnmounted(() => {
  window.removeEventListener("resize", updateEditorHeight);
});

const form = reactive({
  client_name: "",
  format: "toml",
});

const showClientName = computed(() => !!props.groupName);

const title = computed(() => {
  if (props.groupName) {
    return `生成分组配置 - ${props.groupName}`;
  } else if (props.selectedProxies.length > 0) {
    return `生成配置（已选择 ${props.selectedProxies.length} 个代理）`;
  }
  return "生成配置";
});

watch(
  () => props.modelValue,
  (val) => {
    dialogVisible.value = val;
    if (val) {
      form.client_name = props.groupName || "";
      form.format = "toml";
      configContent.value = "";
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

const handleGenerate = async () => {
  generating.value = true;
  configContent.value = "";

  try {
    if (props.groupName) {
      // 优先使用新接口（支持自动创建分组）
      const params = {
        format: form.format,
      };
      if (props.serverId) {
        params.server_id = props.serverId;
      }
      if (form.client_name) {
        params.client_name = form.client_name;
      }

      const content = await frpcConfigApi.getConfigByGroupQuick(
        props.groupName,
        params,
      );
      configContent.value = content;
    } else if (props.selectedProxies.length > 0) {
      const result = await frpcConfigApi.generateConfigByProxies({
        proxy_ids: props.selectedProxies.map((p) => p.id),
        format: form.format,
      });
      configContent.value = result.config;

      if (result.note) {
        notify(result.note);
      }
    } else {
      notify("请选择代理或分组");
      return;
    }

    notify("配置生成成功");
  } catch (error) {
    notify("生成配置失败: " + error.message);
  } finally {
    generating.value = false;
  }
};

const downloadConfig = () => {
  if (!configContent.value) {
    notify("请先生成配置");
    return;
  }

  const blob = new Blob([configContent.value], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const filename = props.groupName
    ? `frpc_${props.groupName}.${form.format}`
    : `frpc.${form.format}`;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
};

const handleRegeneratePorts = async () => {
  if (!props.groupName) {
    notify("仅支持为分组重新生成远端端口");
    return;
  }

  if (
    !(await confirmAction(
      "确定要重新生成该分组中所有代理的远端端口吗？\n\n这将释放旧端口并分配新端口。",
    ))
  ) {
    return;
  }

  regeneratingPorts.value = true;

  try {
    const result = await groupApi.regenerateGroupPorts(
      props.groupName,
      props.serverId,
    );

    let message = result.message || "重新生成远端端口成功";
    if (result.proxies && result.proxies.length > 0) {
      message += "\n\n已重新分配的代理：\n";
      result.proxies.forEach((p) => {
        message += `  • ${p.name}: ${p.old_port || "无"} → ${p.new_port}\n`;
      });
    }
    if (result.failed_proxies && result.failed_proxies.length > 0) {
      message += "\n\n失败的代理：\n";
      result.failed_proxies.forEach((p) => {
        message += `  • ${p.name}: ${p.error}\n`;
      });
    }

    notify(message);

    // 重新生成配置以显示新的端口
    await handleGenerate();
  } catch (error) {
    notify("重新生成远端端口失败: " + error.message);
  } finally {
    regeneratingPorts.value = false;
  }
};
</script>
