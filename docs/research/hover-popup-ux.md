# Editor hover pop-ups — what’s in the way

**Date:** 2026-10-02  
**Scope:** How this pack feeds ComfyUI’s hover help (widget `tooltip`, node `DESCRIPTION`, output tooltips, Properties, status lines). **Docs only. Do not trim, remove, or restyle those strings until Vir picks an option below.** No node changes, no `LLM*` renames, no version bump.

Write-time rules: [`provenance-and-reverification.md`](provenance-and-reverification.md). Template: [`research-note-template.md`](research-note-template.md).

Pack code read at `43319c20e8295042f9225ea51fae6705909f98d7` (`43319c2`). No ComfyUI editor was opened for this note.

---

## Summary — what we believe

- This pack does **not** draw a hover popup. There is no pack CSS, no popup element, and no hover timer in `js/`. The editor chrome is ComfyUI’s. The pack only supplies the **text**.
- The text that feels “in the way” is long policy copy on the controls Vir actually uses: **LLM Connection**’s title (`DESCRIPTION`), **Manage VRAM**, and **LLM Generate** `max_tokens` (plus `meta` on Advanced). Comfy shows that copy after a short idle hover.
- Two Comfy renderers disagree. **Classic canvas** sticks the help box to the mouse, above the cursor, so a long paragraph covers the row you paused on. **Nodes 2.0 (Vue)** puts widget help to the **left** of the row and the title help **above** the title. Vue also invents `Input: {name}` / `Output: {name}` when the pack left a slot blank, and it repeats a widget’s own value when that value is longer than 10 characters and the widget type is `combo`, `number`, `text`, or `asset`. Connection status lines are created as type `text` and are usually longer than that.
- Delay, dismiss, and z-index are Comfy settings and Comfy CSS. This pack sets none of them. Turning tooltips off, or raising **Tooltip Delay**, needs no pack change.
- Status lines are not a separate overlay. They are always-visible read-only text widgets. On Vue they can **also** become a hover popup of that same text. The JS `pointer-events: none` lock targets the classic DOM input; it does not remove the Vue row tooltip.

**Likely “off”:** content, not a custom popup. The hover slot is doing the job of a README paragraph, on the node in the intended path (Connection → Advanced Generate). Positioning that covers the target is Comfy’s classic-canvas tooltip. Extra noise on every socket and on long status strings is Comfy’s Vue tooltip, which this pack inherits by filling the usual fields and by adding type-`text` status widgets.

---

## What the pack actually ships

No file under this repo sets `z-index`, a hover delay, or a tooltip element. `js/llm_connection.js` and `js/model_dropdown.js` add read-only **text** widgets and set `pointer-events: none` on `widget.inputEl` when that element exists. `js/generate_properties.js` stores a `tooltip` string on the LiteGraph property `unload_on_interrupt`. It does not render it.

ComfyUI’s backend copies a class `DESCRIPTION` into `object_info.description` only when the attribute exists. A class docstring is **not** sent unless the node sets `DESCRIPTION = cleandoc(__doc__)`. This pack does not do that. Nodes with no `DESCRIPTION` have an empty title tooltip.

| Surface | Where the text lives | What it says | Who shows it |
|---------|----------------------|--------------|--------------|
| Node title | `DESCRIPTION` on `LLMConnection` (`nodes/providers.py`), both lifecycle nodes (`nodes/lifecycle.py`) | Multi-sentence product copy | Hover the **title** |
| Widget help | `tooltip` inside `INPUT_TYPES` | See the list below | Hover the **widget row** (Vue) or the canvas widget (classic, and only if it is not a DOM widget) |
| Output socket | `OUTPUT_TOOLTIPS` on both Generate nodes and both lifecycle nodes | `text` output is `""`; `meta` and lifecycle outputs are a sentence | Hover the **output** socket |
| Properties | `js/generate_properties.js` `addProperty(..., { tooltip })` | One sentence on interrupt unload | Stored on `properties_info`. No hover renderer was found in the frontend files checked (see below) |
| Status chrome | `node.addWidget("text", ...)` in `js/llm_connection.js` (five lines) and `js/model_dropdown.js` (backend + loaded) | The status string itself (`detected: …`, `VRAM: chat only — …`) | Always visible. Vue may **also** hover-popup the value (hypothesis, below) |

Widget `tooltip` strings in this pack:

- **Connection** (`nodes/providers.py`): `timeout` (advanced; hidden unless advanced is open), `manage_model_memory` (the long Manage VRAM paragraph), `ttl`, `context_length`. `url`, `host_mode`, and `model` have **no** tooltip string.
- **Generate** (`nodes/generation.py`): shared `max_tokens` paragraph on Basic and Advanced. Advanced `meta` has a two-sentence tooltip. Prompts, temperature, and seed have none.
- **Lifecycle** (`nodes/lifecycle.py`): `ttl`, `context_length`, `manage_model_memory`.
- **Options** (`nodes/options_openai.py`, `options_lm_studio.py`, `options_text_gen_webui.py`): only the token fields. One short line each. The `enable_*` toggles have no tooltip. The tooltip dict is copied onto the value widget, not the toggle.

Generate `OUTPUT_TOOLTIPS` first entry is an empty string on purpose. Classic canvas treats that as “no tooltip”. Vue treats an empty string as missing and substitutes `Output: text` (see Comfy behavior).

---

## How Comfy shows it

Two frontends. Which one Vir has depends on **Modern Node Design (Nodes 2.0)** (`Comfy.VueNodes.Enabled`). In frontend `861da8a9` the plain `defaultValue` is `false`. If `Comfy.InstalledVersion` is at least `1.41.0`, `settingStore.ts` uses `defaultsByInstallVersion['1.41.0']`, which is `isCloud || isDesktop` (true on the desktop and cloud builds, false on a build where both flags are false). This note does not know which renderer this machine uses.

### Shared settings

| Setting id | Name in the schema | Default | Range |
|------------|--------------------|---------|--------|
| `Comfy.EnableTooltips` | Enable Tooltips | `true` | on / off |
| `LiteGraph.Node.TooltipDelay` | Tooltip Delay | `500` ms | min 100, max 3000, step 50 |

Source: `src/platform/settings/constants/coreSettings.ts` at frontend `861da8a9`. The public settings page also describes these two controls: [LiteGraph settings](https://docs.comfy.org/interface/settings/lite-graph). That page says delay `0` means immediate. The schema’s minimum is **100**, so the in-app slider cannot store 0. Trust the schema for what the control allows.

Node help text is the `tooltip` field on an input (and `DESCRIPTION` / `output_tooltips` on the node). The node-def JSON schema includes `tooltip` on inputs: [Node Definition JSON](https://docs.comfy.org/specs/nodedef_json). Backend copy into `/object_info`: `server.py` at ComfyUI `fa98a189` sets `description` from `DESCRIPTION` or `''`, and copies `OUTPUT_TOOLTIPS` when present. `comfy/comfy_types/node_typing.py` at the same commit says `DESCRIPTION` is “shown as a tooltip when hovering over the node.”

In-repo [`docs/reference/ecosystem-patterns.md`](../reference/ecosystem-patterns.md) and [`docs/reference/comfyui-platform-findings.md`](../reference/comfyui-platform-findings.md) do not describe hover chrome. The pattern this pack uses is the Comfy fields above, not a custom-node popup library.

### Nodes 2.0 (Vue) — `861da8a9`

File: `src/renderer/extensions/vueNodes/composables/useNodeTooltips.ts`.

| Piece | Trigger | Delay | Dismiss | Place | Content |
|-------|---------|-------|---------|-------|---------|
| Title | Hover the title (`NodeHeader.vue`, `v-tooltip.top`) | `LiteGraph.Node.TooltipDelay` | `hideDelay: 0` on leave. `pointerdown` and `wheel` dispatch `mouseleave` so a visible tip closes. Not a focus trigger | Above the title | `object_info.description` |
| Widget row | Hover the row (`WidgetGrid.vue`, `v-tooltip.left`) | same | same | Left of the row (PrimeVue may flip) | Help text, then if the value qualifies, a blank line and the value |
| Input socket | Hover the socket (`InputSlot.vue`, `v-tooltip.left`) | same | same | Left | Pack tooltip, or else the locale string `Input: {name}` (`g.inputTooltip` in `src/locales/en/main.json`) |
| Output socket | Hover the socket (`OutputSlot.vue`, `v-tooltip.right`) | same | same | Right | Pack tooltip, or else the literal ``Output: ${name}`` |

Value echo is in `processedWidgetRenderModel.ts`: types `asset`, `combo`, `number`, and `text` only, and only when `String(value).length > 10`. The row tooltip is `help + "\n\n" + value`, trimmed. Empty result disables the tooltip. The text box uses `max-w-96` (384px at 16px root) and `whitespace-pre-line`. A browser test at the same commit (`browser_tests/tests/vueNodes/widgets/widgetTooltip.spec.ts`) locks that width and the blank line. The same tree’s `tooltips.spec.ts` still expects a 5-digit seed to appear in `.p-tooltip-text`. That disagrees with the length check. This note follows the renderer. The test was not run.

`useNodeTooltips.ts` does not set a z-index. The canvas tooltip does (below). PrimeVue mounts `.p-tooltip` as an overlay; this note does not cite a numeric Vue z-index.

A same-commit comment in `useNodeTooltips.ts` says the “temporarily disabled” flag does not hide a tip that is already open; the pointer-down path hides by sending `mouseleave`.

### Classic canvas — same frontend commit

File: `src/components/graph/NodeTooltip.vue`.

- **Trigger:** `mousemove` whose target is the canvas. After `LiteGraph.Node.TooltipDelay` with no further move, `onIdle` runs. Not focus.
- **Dismiss:** every `mousemove` clears the text and restarts the timer. `click` hides it. So the box stays only while the pointer is still.
- **Place:** `left` / `top` at the canvas mouse, then `transform: translate(5px, calc(-100% - 5px))` (just above the cursor). If it would leave the window, it flips left or down. `pointer-events: none` (it covers pixels; it does not eat the click). `max-width: 30vw`. **`z-index: 99999`.**
- **Content:** title band → description. Input slot → that input’s tooltip. Output slot → `output_tooltips[index]`. Canvas widget → `widget.tooltip`, else the node-def tooltip. **DOM widgets are skipped** (“these use native browser tooltips”). Empty text is not shown. There is **no** `Input:` / `Output:` fallback on this path.

Classic link hover is separate (`LGraphCanvas.drawLinkTooltip`): hovering a link’s center draws a small canvas label from `link.data`, truncated to 30 characters, above the link. This pack does not set `toToolTip()` on its dicts. That label is Comfy’s, and it is not the widget help.

### Properties

`generate_properties.js` passes `tooltip` into `addProperty`, which copies it onto `properties_info` (`LGraphNode.ts` `addProperty`). `src/core/schemas/parseNodePropertyArray.ts` and the right-side panel files inspected (`TabSettings.vue`, `NodeSettings.vue`, `WidgetItem.vue`) do not read that field. **Do not treat the interrupt sentence as a canvas popup** until someone sees it on screen. The control itself is right-click Properties, which is a panel, not a hover.

### Status lines vs the Vue value rule

`addWidget("text", ...)` leaves LiteGraph `widget.type === "text"`. That string is one of the four types Vue echoes. The widget registry aliases `"text"` to the string **component** (`widgetRegistry.ts`); the tooltip check uses the raw type **before** that alias. After a status fetch, Connection lines such as `detected: LM Studio` and the llama.cpp VRAM sentence are longer than 10 characters. `"(refresh to load)"` and `"Auto (detect)"` / `"OpenAI / OAI-compat"` are also longer than 10; `"llama.cpp"` is not. So the same hover rule is uneven across host modes.

**Hypothesis, not seen in a browser:** on Vue, pausing on a Connection status row opens a left-side popup of that row’s text. Falsifier: hover those rows with tooltips enabled and no `.p-tooltip` appears, or the live widget type is no longer `"text"`.

The classic path skips DOM text widgets, and this pack never sets a `title` attribute, so those rows should **not** pop on classic canvas. The `pointer-events: none` lock is for that DOM input (`js/llm_connection.js`). It does not edit Vue’s row tooltip.

---

## Judgment

| Feeling | Fits? | Why |
|---------|-------|-----|
| Too eager | Partly Comfy, partly our copy | Default delay is 500 ms and tooltips start **on**. That is Comfy’s default, not a pack timer. The pack makes the wait feel worse because the box is a paragraph, not a label |
| Covers the target | Yes on classic canvas | The box is anchored to the cursor and drawn above it (`z-index: 99999`). A Connection `DESCRIPTION` or a `max_tokens` paragraph sits on the node. Vue aims the widget tip **left** of the row so it covers the neighbor, not the control, unless PrimeVue flips it |
| Noisy | Yes, and it is mixed | Spine widgets carry essays. Vue adds `Input:` / `Output:` on sockets the pack left blank (including every Options toggle socket, and `Output: text` despite `""`). Vue also repeats long combo/text values, which Connection status rows and many model ids are |
| Pack-specific vs inherited | The **chrome is inherited**. The **bulk is pack copy** | Core nodes with a one-line `tooltip` get a one-line box. This pack put README policy into `tooltip` and `DESCRIPTION` on the front-door node. Status widgets are pack-added type `text`, so they opt into Vue’s value echo without a help string |

Nothing here is a broken popup implementation inside the pack. Shortening or removing strings is a product choice. Disabling or delaying is already a Comfy setting.

---

## Ask-first options (do not implement from this note)

All four are reversible. None of them is started.

1. **Leave the pack alone. Use Comfy’s controls.** Settings → Enable Tooltips off, or Tooltip Delay toward 3000 ms. No commit. This is the “follow Comfy default” option: the pack keeps supplying text; Comfy decides whether and when to show it. Re-enable the same way.
2. **Trim the long strings to one line.** Connection `DESCRIPTION`, Manage VRAM, `ttl`, `context_length`, `timeout`, Generate `max_tokens`, Advanced `meta`, and the two lifecycle `DESCRIPTION`s. Keep the policy in the README. Widget behavior stays Comfy’s. Revert is restoring the strings.
3. **Quiet the intended spine only.** Remove the `tooltip` keys on Connection’s face widgets and on Generate `max_tokens` / `meta`, and shorten Connection `DESCRIPTION` to one line so the title hover (and the node-library help, which reads `description`) stays short. Leave lifecycle and Options lines. Revert is putting the keys back.
4. **If a live check shows the status rows are the popup,** shorten those status strings or stop using widget type `text` for them. Do this only after the falsifier above fails (the popup really appears). Do not change status copy as a guess. Help-string options 2 and 3 do not depend on it.

Option 1 is the one that needs no review of node copy. Options 2–4 change strings Vir already approved as product text, so they stay ask-first.

---

## Verification

| Topic | Source | Access date | Status / commit | Verified how |
|-------|--------|-------------|-----------------|--------------|
| Pack tooltip / DESCRIPTION / output tips | `nodes/providers.py`, `nodes/generation.py`, `nodes/lifecycle.py`, `nodes/options_*.py` | 2026-10-02 | pack `43319c2` | `code read` |
| Status widgets and DOM lock | `js/llm_connection.js`, `js/model_dropdown.js` | 2026-10-02 | pack `43319c2` | `code read` |
| Properties tooltip stored, not drawn here | `js/generate_properties.js` | 2026-10-02 | pack `43319c2` | `code read` |
| `DESCRIPTION` → `object_info.description` | https://github.com/comfyanonymous/ComfyUI/blob/fa98a189b4271c76f66210e15f81790b555eb610/server.py | 2026-10-02 | `fa98a189` | `code read` |
| `DESCRIPTION` is the hover text | https://github.com/comfyanonymous/ComfyUI/blob/fa98a189b4271c76f66210e15f81790b555eb610/comfy/comfy_types/node_typing.py | 2026-10-02 | `fa98a189` | `code read` |
| Vue tooltip delay, place, fallbacks, value echo | https://github.com/Comfy-Org/ComfyUI_frontend/blob/861da8a9db817949dc1ea5e95c76b3fd64e8f077/src/renderer/extensions/vueNodes/composables/useNodeTooltips.ts and `processedWidgetRenderModel.ts`, `WidgetGrid.vue`, `InputSlot.vue`, `OutputSlot.vue`, `NodeHeader.vue` | 2026-10-02 | `861da8a9` | `code read` |
| Classic canvas tooltip | https://github.com/Comfy-Org/ComfyUI_frontend/blob/861da8a9db817949dc1ea5e95c76b3fd64e8f077/src/components/graph/NodeTooltip.vue | 2026-10-02 | `861da8a9` | `code read` |
| Setting defaults | https://github.com/Comfy-Org/ComfyUI_frontend/blob/861da8a9db817949dc1ea5e95c76b3fd64e8f077/src/platform/settings/constants/coreSettings.ts | 2026-10-02 | `861da8a9` | `code read` |
| Versioned Vue-nodes default | https://github.com/Comfy-Org/ComfyUI_frontend/blob/861da8a9db817949dc1ea5e95c76b3fd64e8f077/src/platform/settings/settingStore.ts (`getVersionedDefaultValue`) | 2026-10-02 | `861da8a9` | `code read` |
| Settings page names the same controls | https://docs.comfy.org/interface/settings/lite-graph | 2026-10-02 | live docs | `docs only` |
| Live editor (which renderer, whether status rows pop) | — | — | — | **not done** |

---

## Applies to

- **Files:** `nodes/providers.py`, `nodes/generation.py`, `nodes/lifecycle.py`, `nodes/options_openai.py`, `nodes/options_lm_studio.py`, `nodes/options_text_gen_webui.py`, `js/llm_connection.js`, `js/model_dropdown.js`, `js/generate_properties.js`
- **Features:** Connection title and Manage VRAM hover, Generate `max_tokens` / `meta` hover, status lines, Properties interrupt sentence

---

## Falsifiers — what would prove this wrong

- A pack file this note missed creates its own hover element, timer, or `z-index`.
- On Vir’s editor, Enable Tooltips is already off and a popup still appears (then it is not this Comfy tooltip).
- Hovering Connection status rows on Nodes 2.0 does not show `.p-tooltip`, or the widget type is not `text` (the value-echo hypothesis is wrong).
- Frontend after `861da8a9` stops echoing values, drops the `Input:` / `Output:` fallback, or stops using `TooltipDelay` for node tips.
- ComfyUI backend stops publishing `DESCRIPTION` / input `tooltip` / `OUTPUT_TOOLTIPS`.

---

## Re-check triggers

- [ ] Editing any `tooltip`, `DESCRIPTION`, or `OUTPUT_TOOLTIPS` string, or the status widgets in `js/llm_connection.js` / `js/model_dropdown.js`
- [ ] A ComfyUI frontend release that changes `useNodeTooltips.ts`, `NodeTooltip.vue`, or `LiteGraph.Node.TooltipDelay`
- [ ] Vir confirms which renderer is on (Nodes 2.0 vs classic) or that a status row does or does not pop
- [ ] Someone chooses an ask-first option and changes copy
