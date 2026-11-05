<script setup>
import { ref, watch } from "vue";
import { useRoute } from "vue-router";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Toaster } from "@/components/ui/sonner";
import { feedback, finishFeedback } from "@/composables/useFeedback";

const route = useRoute(),
  value = ref("");
watch(feedback, (request) => {
  value.value = request?.value || "";
});
function close() {
  finishFeedback(feedback.value?.kind === "prompt" ? null : false);
}
watch(
  () => route.path,
  () => {
    if (feedback.value) close();
  },
);
</script>

<template>
  <Toaster
    position="top-right"
    close-button
    rich-colors
    container-aria-label="操作反馈"
  /><AlertDialog
    :open="feedback?.kind === 'confirm'"
    @update:open="
      (open) => {
        if (!open) close();
      }
    "
  >
    <AlertDialogContent>
      <AlertDialogHeader
        ><AlertDialogTitle>{{ feedback?.title }}</AlertDialogTitle
        ><AlertDialogDescription class="whitespace-pre-wrap break-words">{{
          feedback?.message
        }}</AlertDialogDescription></AlertDialogHeader
      ><AlertDialogFooter
        ><AlertDialogCancel>取消</AlertDialogCancel
        ><AlertDialogAction
          :variant="feedback?.danger ? 'destructive' : 'default'"
          @click.capture="finishFeedback(true)"
          >{{ feedback?.confirmText }}</AlertDialogAction
        ></AlertDialogFooter
      >
    </AlertDialogContent> </AlertDialog
  ><Dialog
    :open="feedback?.kind === 'prompt'"
    @update:open="
      (open) => {
        if (!open) close();
      }
    "
  >
    <DialogContent class="sm:max-w-lg"
      ><DialogHeader
        ><DialogTitle>{{ feedback?.title }}</DialogTitle
        ><DialogDescription>{{
          feedback?.message
        }}</DialogDescription></DialogHeader
      >
      <div data-slot="dialog-body" class="min-h-0 flex-1 overflow-y-auto p-5">
        <Textarea v-model="value" aria-label="内容" rows="5" />
      </div>
      <DialogFooter
        ><Button type="button" variant="outline" @click="close">取消</Button
        ><Button type="button" @click="finishFeedback(value)"
          >保存</Button
        ></DialogFooter
      ></DialogContent
    >
  </Dialog>
</template>
