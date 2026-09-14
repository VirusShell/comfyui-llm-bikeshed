# Presets (LLM Preset Loader)

Drop UTF-8 `.txt` files in this directory. **LLM Preset Loader** lists them in a COMBO and outputs file contents as a STRING (wire to `system_prompt` or `prompt` on a generate node).

## Rules

- Only `*.txt` files appear in the dropdown.
- `README.txt` is ignored by the loader (this file).
- Filenames are basename-only; path traversal is rejected.
- Restart ComfyUI or re-open the node after adding files so INPUT_TYPES refreshes.

## Example shipped

- `llamacpp_oai_system.txt` — short system prompt for llama.cpp / other OAI-compatible local servers via **LLM Provider: OAI Compatible**.

## Adding your own

1. Create `presets/my_prompt.txt` with the system (or user) text.
2. In the graph: **LLM Preset Loader** → select `my_prompt.txt` → connect `text` to generate.
3. Keep presets free of secrets (no API keys).

This pack does not ship large preset packs; add what you need locally.
