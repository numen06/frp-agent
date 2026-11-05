import { cva } from "class-variance-authority";

export { default as Tabs } from "./Tabs.vue";
export { default as TabsContent } from "./TabsContent.vue";
export { default as TabsList } from "./TabsList.vue";
export { default as TabsTrigger } from "./TabsTrigger.vue";

export const tabsListVariants = cva(
  "rounded-lg p-1 min-h-11 group/tabs-list inline-flex w-fit items-center justify-start text-muted-foreground group-data-vertical/tabs:h-fit group-data-vertical/tabs:flex-col",
  {
    variants: {
      variant: {
        default: "bg-muted",
        line: "w-full gap-1 rounded-none border-b bg-background px-1 py-1 overflow-x-auto",
      },
    },
    defaultVariants: { variant: "default" },
  },
);
