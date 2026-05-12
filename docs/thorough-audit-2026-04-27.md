# Thorough audit — LLM Bikeshed (2026-04-27)

This document **scopes** what was reviewed, **records methodology**, and **lists findings** with follow-ups. Static review and new unit tests were executed in-repo; live ComfyUI QA remains optional.

## 1. Audit scope

| Area | In scope | Out of scope (this pass) |
|------|-----------|---------------------------|
| Graph introspection / `skip_unload` | `graph/introspection.py`, all callers in `nodes/generation.py` | Live ComfyUI with Reroute / subgraphs (manual QA) |
| Adapters / HTTP | `adapters/base.py`, `adapters/oai_compat.py` | Load testing, real WAN latency |
| Model list UX | `js/model_dropdown.js`, `server/endpoints.py` routes | Cross-version ComfyUI matrix (manual) |
| Reference vs code | `docs/reference/backend-api-parameters.md`, resolution tracker | Full OpenAPI scrape of every backend |
| Automated tests | `tests/`, `pyproject.toml` | CI pipeline configuration |

## 2. Methodology

1. **Static code review** — trace `skip_unload` from generation nodes → `has_downstream_gen_node` → adapters (`ttl` / `keep_alive` / unload).
2. **Consistency grep** — `GENERATION_CLASS_TYPES`, `_safe_post`, allowlists, endpoint auth retry paths.
3. **Automated tests** — `python -m pytest tests/ -v` from repository root.
4. **Doc cross-check** — confirm tracker references exist.

## 3. Findings (by workstream)

### A. Graph introspection and unload deferral

**Previously:** `GENERATION_CLASS_TYPES` omitted `LLMGenerateTest`, so meta chains into the test generation node did not set `skip_unload` on the upstream node.

**Fix applied:** `LLMGenerateTest` added to `GENERATION_CLASS_TYPES` (`graph/introspection.py`). Regression coverage in `tests/test_graph_introspection.py`.

**Residual risk:** Reroute / subgraph / wrapper nodes may still break direct `[source_id, output_index]` reverse-indexing. Capture a real `PROMPT` JSON if deferral misbehaves in the UI.

### B. HTTP, errors, retries

- No retry loop on generation POST (matches resolution tracker).
- OpenAI path skips local load/unload APIs (existing test).

**Fix applied:** Removed stray **warning**-level “DEBUG” log from `LLMGenerateTest.generate` (`nodes/generation.py`).

### C. Parameter allowlists

- OAI adapter filters by `BACKEND_ALLOWLISTS`; dropped keys logged at info; non-JSON-safe floats at warning.
- `docs/reference/backend-api-parameters.md` exists and aligns with API-4.

### D. Frontend model dropdown

- `nodeCreated` fetches once; **Refresh Models** refetches; changing **url** alone does not auto-refetch until refresh (current design).

**Optional later:** debounced fetch when the URL widget changes.

### E. Test suite

- `tests/test_graph_introspection.py` added for PROMPT-shape contracts.
- **Pytest note:** Running `pytest` from the repository root may still hit pytest 8+ `Package` setup that imports the ComfyUI root `__init__.py` as a plain module (relative imports fail). Prefer:

  ```bash
  PYTHONPATH=.   # or set to repo root on Windows
  python -m unittest tests.test_graph_introspection -v
  ```

  Full-suite pytest may require future work (import layout or `nodes`-compatible test imports).

## 4. Backlog (remaining)

| ID | Item | Severity |
|----|------|----------|
| AUDIT-3 | Manual QA: meta → Reroute → next gen node; capture PROMPT if deferral fails | Medium |
| AUDIT-4 | Optional JS: refetch models when URL widget changes | Low |
| AUDIT-5 | Re-validate allowlists when backend versions bump | Medium |

## 5. Sign-off

| Gate | Status |
|------|--------|
| Static review | Complete |
| Code fixes (AUDIT-1, AUDIT-2) | Applied |
| Unit tests (graph) | Added (`unittest` verified) |
| `pytest` from repo root (graph-only file) | Fails on root `__init__.py` import — use `unittest` above |
| Manual ComfyUI graph QA | Pending |
