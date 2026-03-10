# Ecosystem Analysis — LLM Node Packs

> **Last updated:** 2026-03-09
> **Purpose:** Patterns to borrow and anti-patterns to avoid from existing ComfyUI LLM node packs

---

## comfyui-ollama (stavsap)

**Repo:** https://github.com/stavsap/comfyui-ollama

### Patterns to Borrow

1. **Custom type flow:** `OLLAMA_CONNECTIVITY` -> `OLLAMA_OPTIONS` -> `OLLAMA_META`
   - Clean separation of concerns
   - Our equivalent: `LLM_PROVIDER` -> `LLM_OPTIONS` -> `LLM_META`

2. **Toggle-based Options (V2):** Each parameter has a BOOLEAN enable toggle. Only enabled params included in API calls. `get_request_options()` method iterates toggles. This is the pattern for our Options nodes (A-3).

3. **Meta passthrough:** GenerateV2 accepts either direct connectivity/options or inherits via meta. Explicit inputs override meta values.

4. **Dynamic model dropdown:** Custom PromptServer endpoint (`POST /ollama/get_models`) queries Ollama. Frontend JS populates COMBO widget.

### Anti-Patterns to Avoid

- **SDK dependency:** Uses `ollama` Python SDK. Breaks when SDK has breaking changes. We use `requests` directly.
- **V1/V2 node coexistence:** Both old monolithic and new modular nodes exist, creating user confusion. Ship only the modular design.
- **Very tall Options node:** Toggle + value pair per parameter makes the node visually unwieldy. Consider collapsible sections or smarter defaults.

---

## comfyui-ollama-describer (alisson-anjos)

**Repo:** https://github.com/alisson-anjos/ComfyUI-Ollama-Describer

### Patterns to Borrow

- **Compact inline parameters:** Self-contained nodes with temperature, top_k, top_p, repeat_penalty, seed, num_ctx directly on the node. Model for our Basic generation node.
- **Structured output:** Accepts JSON schema as input, passes to Ollama's `format` parameter.
- **Uses `requests` directly:** No SDK dependency. Matches our approach.

### Anti-Patterns to Avoid

- **Hardcoded model list:** Static list that may trigger unwanted model downloads
- **No provider abstraction:** Locked to Ollama only
- **No model memory management:** No keep_alive control

---

## Key Takeaways for Our Design

| Decision | Rationale |
|----------|-----------|
| Per-provider Options nodes with toggles | Borrows comfyui-ollama's toggle pattern but avoids its extreme height by only showing each backend's supported params |
| `requests` over SDK | Avoids comfyui-ollama's SDK coupling issue |
| Dynamic model dropdown via JS + PromptServer | Proven pattern from comfyui-ollama |
| Basic + Advanced generation nodes | Combines comfyui-ollama-describer's compact approach with comfyui-ollama's modular approach |
| Meta passthrough | Directly borrowed from comfyui-ollama V2 |
| Preset Loader as separate node | Avoids inline COMBO→STRING JS complexity for v1 |

---

## Sources

- [ComfyUI-Ollama (DeepWiki)](https://deepwiki.com/stavsap/comfyui-ollama/1-overview)
- [ComfyUI-Ollama source](https://github.com/stavsap/comfyui-ollama)
- [ComfyUI-Ollama-Describer source](https://github.com/alisson-anjos/ComfyUI-Ollama-Describer)
