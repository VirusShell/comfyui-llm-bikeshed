# Quality of Life Backlog

Tracked UX/polish improvements that aren't blocking v1 but should be addressed.

## Pending

### Provider UX

- [ ] **Multi-provider URL change → model refresh (P-11)**
  Editing `url` on **LLM Provider: Textgen** may not refresh dropdown/status until **Refresh Models** when OAI Compatible is also on the graph. Likely fix in `js/model_dropdown.js` — use `urlWidget.value` in debounced handler; consider `input`/`change` listeners. See [`user-feedback-2026-06-17.md`](research/user-feedback-2026-06-17.md).

- [ ] **`detected_backend` / `loaded_model_status` read-only (P-12)**
  JS `text` widgets are editable; should be disabled or non-interactive. Consider clearer label for `loaded_model_status` (e.g. `loaded_model`).

- [ ] **Provider architecture clarity (A-25 / D-2)**
  Document or redesign overlap between OAI Compatible, Textgen provider, and lifecycle nodes.

### Tooltips / Hints

*(All tooltip items completed — see Completed section.)*

### Node Layout

- [ ] **LLM Options: text-gen-webui — evaluate node height**
  24 toggle widgets may be too tall. Implement as single node first, split only if it looks bad in the UI.
  *(Noted in design_review_update_2026-03-10.md, lines 122-127)*

- [ ] **LLM Options: LM Studio — evaluate node height**
  18 toggle widgets is borderline. Don't split unless it looks bad during testing.
  *(Noted in design_review_update_2026-03-10.md, lines 118-119)*

### Preset UX

- [ ] **Inline preset dropdown on generation nodes**
  Current v1 uses a separate Preset Loader node (known-working). An inline COMBO that populates system_prompt directly would be better UX but is fragile on workflow load. Deferred to post-v1.
  *(Resolution tracker A-6; concept doc lines 105-113)*

## Future / research

- **Cooperative interrupt for reasoning models (llama.cpp)** — llama.cpp can interrupt long reasoning chains without killing the full inference session; evaluate whether generation nodes should expose a cancel/stop path for chained reasoning without unloading the model.

## Completed

- [x] **LLM Lifecycle: LM Studio — `ttl` widget unit tooltip** (seconds, per LM Studio API)
- [x] **LLM Generate (Basic) — `meta` output tooltip**
- [x] **LLM Generate (Advanced) — `meta` input and output tooltips**
