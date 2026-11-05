// Fail if a Vue page silently falls back to an unresolved custom HTML tag.
import { readFileSync, readdirSync } from "node:fs";
import { parse, compileScript } from "@vue/compiler-sfc";
import { parse as parseTemplate } from "@vue/compiler-dom";
const builtins = new Set([
  "Transition",
  "TransitionGroup",
  "Teleport",
  "KeepAlive",
  "Suspense",
  "RouterView",
  "RouterLink",
]);
const missing = [];
for (const directory of ["src/views", "src/components"]) {
  for (const file of readdirSync(directory).filter((name) =>
    name.endsWith(".vue"),
  )) {
    const path = `${directory}/${file}`;
    const { descriptor } = parse(readFileSync(path, "utf8"));
    if (!descriptor.template || !descriptor.scriptSetup) continue;
    const bindings = compileScript(descriptor, { id: path }).bindings;
    const used = new Set();
    function walk(node) {
      if (node.tag === "Button") {
        const value = (name) =>
          node.props?.find((prop) => prop.type === 6 && prop.name === name)
            ?.value?.content;
        if (
          value("variant") === "ghost" &&
          /\btext-white\b/.test(value("class") || "")
        )
          missing.push(
            `${path}: white text on a transparent Button; use its semantic variant`,
          );
      }
      if (/^[A-Z]/.test(node.tag || "") && !builtins.has(node.tag))
        used.add(node.tag);
      for (const child of node.children || []) walk(child);
    }
    walk(parseTemplate(descriptor.template.content));
    for (const tag of used) if (!bindings[tag]) missing.push(`${path}: ${tag}`);
  }
}
if (missing.length)
  throw new Error(`Unresolved UI components:\n${missing.join("\n")}`);
console.log(
  "All business Vue components are explicitly bound; no unresolved UI tags.",
);
