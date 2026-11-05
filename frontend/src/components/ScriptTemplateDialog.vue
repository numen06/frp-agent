<template>
  <Dialog
    v-if="visible"
    :open="true"
    @update:open="
      (open) => {
        if (!open) {
          closeDialog();
        }
      }
    "
    ><DialogContent class="sm:max-w-5xl" :aria-describedby="undefined"
      ><DialogHeader><DialogTitle>平台脚本模板编辑</DialogTitle></DialogHeader>
      <div
        data-slot="dialog-body"
        class="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
      >
        <div class="grid gap-4">
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700"
              >目标平台</label
            ><Select v-model="platform"
              ><SelectTrigger class="w-full" aria-label="目标平台"
                ><SelectValue
                  placeholder="请选择平台"
                ></SelectValue></SelectTrigger
              ><SelectContent
                ><SelectItem :value="null">请选择平台</SelectItem
                ><SelectItem v-for="p in platforms" :key="p" :value="p">{{
                  p
                }}</SelectItem></SelectContent
              ></Select
            >
          </div>
          <div class="code-editor-wrapper min-h-[200px] overflow-x-auto">
            <CodeEditor
              v-model="content"
              language="shell"
              :height="editorHeight"
              placeholder="可用变量：{{filename}} {{download_url}} {{install_path}} {{config_line}} {{platform}} {{version}}"
            />
          </div>
        </div>
      </div>
      <DialogFooter
        ><Button
          type="button"
          class="w-full sm:w-auto"
          @click="loadTemplate"
          variant="outline"
          size="default"
        >
          加载模板 </Button
        ><Button
          type="button"
          class="w-full sm:w-auto"
          :disabled="saving"
          @click="saveTemplate"
          variant="default"
          size="default"
          >{{ saving ? "保存中..." : "保存模板" }}</Button
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
import { Select } from "@/components/ui/select";
import { SelectContent } from "@/components/ui/select";
import { SelectItem } from "@/components/ui/select";
import { SelectTrigger } from "@/components/ui/select";
import { SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { notify } from "@/composables/useFeedback";
import { ref, watch, onMounted, onUnmounted } from "vue";
import CodeEditor from "@/components/CodeEditor.vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  platforms: { type: Array, default: () => [] },
  templates: { type: Object, default: () => ({}) },
  saving: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue", "save"]);
const visible = ref(false);
const platform = ref("");
const content = ref("");
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

watch(
  () => props.modelValue,
  (val) => {
    visible.value = val;
  },
);
watch(visible, (val) => emit("update:modelValue", val));

const closeDialog = () => {
  visible.value = false;
};

const loadTemplate = () => {
  if (!platform.value) {
    notify("请先选择平台");
    return;
  }
  content.value = props.templates[platform.value] || "";
};

const saveTemplate = () => {
  if (!platform.value || !content.value.trim()) {
    notify("请选择平台并填写脚本内容");
    return;
  }
  emit("save", { platform: platform.value, content: content.value });
};
</script>
