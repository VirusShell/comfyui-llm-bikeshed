import { app } from "../../scripts/app.js";

/**
 * Interrupt/unload policy for Generate nodes (Vir Q5).
 *
 * This is a LiteGraph node property (right-click Properties), not a face
 * widget. Python reads it from extra_pnginfo.workflow at queue time
 * (nodes/generation.py). Default off. Manage VRAM OFF embeds no lifecycle,
 * so the flag cannot unload in that case.
 *
 * The pack has no other node-property pattern; this uses ComfyUI's
 * addProperty, which is the Properties panel. API prompts that omit the
 * workflow blob keep the default.
 */

const GENERATE_NODES = new Set(["LLMGenerate", "LLMGenerateAdvanced"]);
const PROP = "unload_on_interrupt";

function ensureUnloadProperty(node) {
  if (!node.properties) {
    node.properties = {};
  }
  const info = node.properties_info || [];
  const exists = info.some((entry) => entry && entry.name === PROP);
  if (exists) {
    return;
  }
  node.addProperty(PROP, false, "boolean", {
    label: "Unload on interrupt",
    tooltip:
      "After Cancel, unload the model only if Manage VRAM or a legacy " +
      "lifecycle is managing it. Off by default. Does nothing when " +
      "Manage VRAM is off.",
  });
}

app.registerExtension({
  name: "llm-bikeshed.generateProperties",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (!GENERATE_NODES.has(nodeData?.name)) {
      return;
    }
    const onCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = onCreated?.apply(this, arguments);
      ensureUnloadProperty(this);
      return result;
    };
  },
});
