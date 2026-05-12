# Lessons & Insights — comfyui-llm-bikeshed

> Tracking insights, mistakes, non-obvious behaviors, and ideas discovered during
> development. These inform future ComfyUI node pack projects and general dev practices.

## Import System: Absolute vs Relative (Critical)

**Date discovered:** 2026-03-15
**Severity:** Breaks all functionality at runtime
**Status:** Fix in progress

All 18 cross-module imports used absolute paths (`from nodes.generation import ...`)
which resolve correctly in a local venv but collide with ComfyUI's own `nodes.py` and
`server/` modules at runtime. Every internal import must be relative (`from .nodes.generation import ...`).

**Confirmed via ComfyUI log** (`user/comfyui_7869.log`):
```
File "...\custom_nodes\comfyui-llm-bikeshed\__init__.py", line 3, in <module>
    from nodes.generation import LLMGenerate, LLMGenerateAdvanced
ModuleNotFoundError: No module named 'nodes.generation'; 'nodes' is not a package
```

The error is `'nodes' is not a package` — Python found ComfyUI's `nodes.py` (a file)
instead of our `nodes/` directory (a package). ComfyUI adds `custom_nodes/` to
`sys.path`, but ComfyUI's own directory is higher priority, so `nodes` resolves to
ComfyUI's `nodes.py` first.

**Root cause:** Development and testing happened in an isolated venv where ComfyUI's
modules weren't present. All 150 tests passed, all linting passed, all verification
commands passed — but the pack fails on first import inside ComfyUI.

**Fix scope:** 19 imports across 10 files converted to relative. `nodes/` and `server/`
collide with ComfyUI names, but ALL absolute imports of internal subpackages fail because
the pack directory isn't on `sys.path` — even non-colliding names like `config/`,
`graph/`, and `adapters/` are unreachable via absolute import. Only one absolute import
in `server/endpoints.py` (`from server import PromptServer`) stays absolute — it
correctly reaches ComfyUI's own module.

**Prevention:** For any future ComfyUI node pack, enforce relative imports from the
start. Consider a ruff rule or pre-commit hook that flags absolute imports of internal
subpackages.

---

## venv and uv.lock Should Not Ship

**Date discovered:** 2026-03-15
**Severity:** Bloat, confusion

Custom node packs run inside ComfyUI's Python environment. `.venv/` and `uv.lock` are
dev-only artifacts. They were committed to git and merged to main before being caught.

**Fix:** Added to `.gitignore`, removed `uv.lock` from tracking.

**Prevention:** Global CLAUDE.md updated with plugin/extension project exception for
venv handling.

---

## requirements.txt vs pyproject.toml

**Date discovered:** 2026-03-15
**Severity:** Install failure for end users

ComfyUI-Manager reads `requirements.txt` exclusively — it never parses `pyproject.toml`
for dependencies. The project had deps declared only in `pyproject.toml`, which meant
ComfyUI-Manager would find nothing to install.

In this project's case, all runtime deps (`requests`, `pyyaml`, `pillow`, `numpy`) are
already in ComfyUI core, so `requirements.txt` is comment-only. But if we add deps that
ComfyUI doesn't ship, they must go in `requirements.txt`.

---

## Dependency Version Constraints

**Date discovered:** 2026-03-15
**Severity:** Ecosystem awareness

Exact pins (`==`) and upper bounds (`<2`) on shared deps (especially numpy) are the most
common source of dependency conflicts across ComfyUI node packs. Our deps were already
loose/unpinned, but this is worth tracking for future deps.

Notable offenders in the wild:
- `numpy==1.26.4` (reactor-node, Boyonodes/seed-vc) — exact pin
- `numpy<2` (comfyui-sam2, layerstyle) — upper bound blocks numpy 2.x

**Rule:** Always use `>=X.Y` lower bounds, never exact pins or upper bounds.

---

## Permission Prompt Interruptions (Claude Code)

**Date documented:** 2026-03-15
**Severity:** Workflow disruption

31+ permission interruptions across ~7 sessions during autonomous spec execution.
Two contributing factors:
1. Deprecated `:*` pattern syntax in settings.local.json (should be ` *` with space)
2. Overly specific rules that didn't generalize across command variations

**Fix:** Rebuilt `.claude/settings.local.json` with correct syntax and scoped rules.
See `docs/blargh.md` for full forensics.

---

## Unit Testing Strategy Was Fundamentally Wrong

**Date discovered:** 2026-03-15
**Severity:** Wasted effort / false confidence
**Status:** Needs rethink

150 unit tests were built assuming the code runs as standalone Python packages in an
isolated venv. This assumption was wrong — the code runs as a plugin inside ComfyUI's
environment, loaded via `spec_from_file_location` with a parent package context.

Once imports were corrected to relative (the runtime-correct form), the tests couldn't
run anymore because relative imports like `from ..adapters` require a parent package
context that doesn't exist in the venv.

**Research findings:** Other ComfyUI node packs generally don't do isolated unit testing.
They either:
- Integration test inside the full ComfyUI runtime (nunchaku, ultimatesdupscale)
- Build elaborate ComfyUI module mocks in conftest.py (lora-manager — complex, fragile)
- Don't test at all (most packs)

Attempting to shim a synthetic parent package in conftest.py failed — Python's import
machinery re-imports from the filesystem and ignores `sys.modules` aliases when resolving
dotted names like `from nodes.generation import ...`.

**The test logic itself is sound** — what's wrong is the execution environment. The
testing strategy needs to be rethought to match how the code actually runs.

**Options to evaluate:**
1. Run tests inside ComfyUI's Python with its `sys.path` (integration approach)
2. Restructure the project so there's one top-level package (e.g., `llm_bikeshed/`)
   that contains all subpackages — tests import from `llm_bikeshed.nodes.generation`
3. Accept that unit tests require a conftest.py shim and invest in getting it right
4. Some combination — unit test pure logic (adapters, config, merge) separately,
   integration test the node classes inside ComfyUI

---

## Insight: Host-Environment Smoke Test (Proposed)

**Date:** 2026-03-15
**Status:** Idea — not yet implemented

A standard verification step for any ComfyUI node pack: test imports using ComfyUI's
embedded Python rather than the dev venv. This catches naming collisions, missing deps,
and runtime-only failures that local tests miss.

**Possible implementations (lightest to heaviest):**

1. **Smoke test script** — A `scripts/test_comfyui_compat.py` that runs under ComfyUI's
   embedded Python and tries importing every node class. Run manually or as a pre-PR step.
   Needs ComfyUI path configured (env var or config).

2. **Spec task template** — For future Smart-Ralph specs on ComfyUI projects, add a
   standard `[VERIFY]` task: "Test all imports under ComfyUI's embedded Python." Would
   catch issues before the PR phase.

3. **Post-mortem step** — After a spec completes, do a "did anything fail at runtime
   that tests didn't catch?" review and update lessons-learned. Lowest effort, highest
   chance of being skipped.

**Decision:** Holding for now. If option 1 proves useful on this project, consider
proposing option 2 as a Smart-Ralph enhancement for ComfyUI specs.

---

## Resolved: Reverse Collision on `server` Module — Not a Problem

**Date:** 2026-03-15
**Status:** Resolved — no action needed

Our `server/endpoints.py` imports ComfyUI's `PromptServer` via `from server import
PromptServer`. Concern was that this would resolve to our own `server/` package instead.

**Finding:** Python only uses relative import resolution with explicit `.` prefix.
`from server import PromptServer` (no dot) resolves to ComfyUI's top-level `server.py`
even when called from inside our `server/` subpackage. Confirmed by checking
ComfyUI-Crystools, which has the exact same pattern (`server/` subpackage + absolute
`from server import PromptServer` inside it) and works correctly.

**Rule:** Absolute imports reach ComfyUI's modules. Relative imports (with `.`) reach
our own subpackages. Both can coexist in the same file.

---

## Resolved: Naming Collision Check for `config/`, `graph/`, `adapters/`

**Date:** 2026-03-15
**Status:** Resolved — no collisions

Checked ComfyUI's top-level namespace. None of these names exist:
- `config` — no collision (ComfyUI uses `comfy_config/` instead)
- `graph` — no collision
- `adapters` — no collision

Despite no name collisions, these subpackages still cannot use absolute imports because
the pack directory isn't on `sys.path` at runtime. All internal imports must be relative
regardless of whether the name collides with a ComfyUI module.

---

## Confirmed Collision Scope

**Date:** 2026-03-15

Only two of our subpackage names collide with ComfyUI modules:

| Our package | ComfyUI module | Collision? |
|-------------|---------------|------------|
| `nodes/` | `nodes.py` | **YES** |
| `server/` | `server.py` | **YES** |
| `config/` | (none) | No |
| `graph/` | (none) | No |
| `adapters/` | (none) | No |

**Verified against other node packs:** Crystools, Addoor, nunchaku, and others all have
`nodes/` and/or `server/` subpackages and solve this with relative imports (`from .nodes.xxx`).

**Pattern confirmed across ecosystem:** `from .nodes.xxx` for internal, `from server import
PromptServer` for ComfyUI's modules. No pack uses absolute imports for its own subpackages.

**Fix scope:** 19 imports across 10 files converted to relative. See the "Import
System: Absolute vs Relative" entry above for the full details.

## Textgen model list 401 retry used wrong config key

**Date:** 2026-04-27  
**Severity:** Moderate — admin-only model refresh never received the configured key  
**What happened:** The PromptServer route for Textgen (`/llm-bikeshed/models/text-gen-webui`) retried `GET /v1/internal/model/list` after 401/403 using `get_api_key("text_gen_webui_admin")`, but config and [`get_admin_key("text_gen_webui")`](config/__init__.py) only define `providers.text_gen_webui.admin_key` and env `LLM_BIKESHED_TEXT_GEN_WEBUI_ADMIN_KEY`. The retry path almost always saw `None`.  
**Root cause:** Key name drift — provider code used the documented admin resolution API; the endpoint used a non-existent provider slug.  
**Fix:** Retry with `get_admin_key("text_gen_webui")` (same as [`LLMProviderTextGenWebUI`](nodes/providers.py)).  
**Prevention:** Reuse the same `get_api_key` / `get_admin_key` helper and provider slug everywhere a backend needs secrets; grep for duplicate string keys when adding endpoints.

## Graph unload deferral omitted `LLMGenerateTest`

**Date:** 2026-04-27  
**Severity:** Moderate — wrong `skip_unload` when chaining meta into/out of test generation nodes  
**What happened:** `GENERATION_CLASS_TYPES` in `graph/introspection.py` listed only `LLMGenerate` and `LLMGenerateAdvanced`. `LLMGenerateTest` still called `has_downstream_gen_node` for meta output index 1, but downstream test nodes were never recognized, so upstream nodes could unload or shorten TTL while a chained test generation still needed the model.  
**Root cause:** Whitelist drift — a new generation `class_type` was added without updating the introspection set.  
**Fix:** Add `LLMGenerateTest` to `GENERATION_CLASS_TYPES`; add `tests/test_graph_introspection.py`; document in `docs/thorough-audit-2026-04-27.md`. Remove stray `logger.warning` debug block from `LLMGenerateTest.generate`.  
**Prevention:** Whenever a new node outputs `LLM_META` and participates in unload chains, extend `GENERATION_CLASS_TYPES` (or centralize a single registry keyed by node class). Run / extend graph introspection tests.

## Pytest vs ComfyUI root `__init__.py`

**Date:** 2026-04-27  
**Severity:** Low — local test ergonomics only  
**What happened:** `python -m pytest tests/test_graph_introspection.py` from the repo root fails during collection/setup because pytest imports the pack root `__init__.py` without a parent package, so relative imports in that file raise `ImportError: attempted relative import with no known parent package`. The same tests pass with `PYTHONPATH=<repo>` and `python -m unittest tests.test_graph_introspection`.  
**Root cause:** ComfyUI custom node layout (root `__init__.py` as entrypoint) conflicts with pytest 8+ directory/package collection that loads that file as a normal module.  
**Fix (2026-05-02):** Wrapped all imports in `__init__.py` in `try/except ImportError` — when pytest imports it standalone, the relative imports fail silently and `NODE_CLASS_MAPPINGS` / `NODE_DISPLAY_NAME_MAPPINGS` default to empty dicts. ComfyUI loads it as part of `custom_nodes/` with a proper parent package, so the imports work normally. Approaches that did NOT work: `collect_ignore` in root conftest (pytest imports `__init__.py` as package init, not as a collected test), `--import-mode=importlib` (still triggers the same import), `--rootdir=tests` (pytest still discovers root `__init__.py`).  
**Prevention:** For new packs, plan test entrypoints (editable install, `src/` layout, or `unittest`) before relying on bare `pytest` from the pack root.

## Lifecycle-gated model management changes test fixture requirements

**Date:** 2026-05-02  
**Severity:** Low — test-only  
**What happened:** After switching from `provider["memory"]` to `provider["lifecycle"]` for model management gating, existing adapter tests that used inline LM Studio provider dicts with lifecycle data started failing. The tests only mocked `adapters.base.requests.post` but not `requests.get`, so `_ensure_model_loaded_lm_studio` made real HTTP calls that failed silently, then the mocked POST captured the load request payload instead of the generate payload.  
**Root cause:** Tests for allowlist filtering and TTL behavior didn't need model management, but their provider dicts had `lifecycle` set, which now triggers the load/unload path.  
**Fix:** Set `lifecycle: None` on provider dicts in tests that only verify allowlist filtering, auth headers, and payload structure (these don't need model management). For TTL tests that DO need lifecycle, added `requests.get` mocks that return "model already loaded" responses.  
**Prevention:** When a provider dict field gates significant behavior (like model management), test helpers should default to the disabled state unless the test specifically exercises that behavior.

## ComfyUI node with no INPUT_TYPES widgets shows no body

**Date:** 2026-05-02  
**Severity:** Medium — node appears broken (title + output only)  
**What happened:** `LLMLifecycleTextGenWebUI` used `INPUT_TYPES` with ``"required": {}`` so the graph editor showed the display name and output pin but no inputs, unlike `LLMLifecycleLMStudio` which has TTL/context widgets.  
**Root cause:** The ComfyUI client does not reliably draw the widget strip for nodes with zero inputs.  
**Fix:** Add a BOOLEAN widget (e.g. `manage_model_memory`, default ON). When OFF, return an empty dict `{}` for `LLM_LIFECYCLE` so the adapter treats it as no lifecycle (falsy).  
**Prevention:** Never ship a node with an empty `required` and `optional` widget set; add a minimal control or a static label-style widget if a “presence only” node is required.

## Imported helper module missing from repository

**Date:** 2026-05-11  
**Severity:** High — runtime ``ImportError`` or incomplete installs hide the real bug until runtime  
**What happened:** `server/endpoints.py` imported `../model_list.py`, but `model_list.py` was untracked and never committed, so installs from git did not include Textgen’s internal model list path. The dropdown fell back to behavior that did not list Textgen’s on-disk models correctly.  
**Root cause:** The file was added locally and wired up without adding it to version control in the same change.  
**Fix:** Commit `model_list.py`; release **v0.2.2** documents the recovery.  
**Prevention:** After adding imports from new modules, `git status` must show those paths tracked before merging; optional: CI assert `model_list.py` exists when `server/endpoints.py` references it.

## Textgen model dropdown: `/v1/models` vs internal list + stale COMBO merge

**Date:** 2026-05-10  
**Severity:** Medium — wrong model list and a workflow value that never clears  
**What happened:** With the OAI-compat provider URL pointed at text-generation-webui, `detected_backend` showed Textgen, but the model COMBO kept an LM Studio model id from another node/workflow, and refresh/restart did not fix it.  
**Root cause:** (1) Textgen’s OpenAI-compatible `GET /v1/models` often does not expose the same model inventory as the UI; the supported list is `GET /v1/internal/model/list` (`model_names`). The dropdown fetch only used `/v1/models`, so it returned empty or useless ids. (2) Frontend `updateModelWidget` always appended the serialized “saved” model to the COMBO when it was missing from the fetch result, then re-selected it — so a stale id looked like a valid default forever.  
**Fix:** Resolve Textgen first: after `detect_backend` returns `text_gen_webui`, fetch `/v1/internal/model/list` with optional admin/api keys, then fall back to `/v1/models`. In `model_dropdown.js`, only merge the saved value into options when the backend returned **no** models (offline / error), not when it returned a non-empty list.  
**Prevention:** For backends with a “compat” surface and a richer internal API, fingerprint in detection should drive which list endpoint to call; don’t assume one OAI route fits all. When populating dynamic COMBOs, don’t resurrect workflow-only values on top of a successful fresh list.

**Addendum (same day):** Textgen enforces the same ``--api-key`` on ``/v1/chat/completions`` and internal routes, but the provider node stored that secret under ``admin_key`` while chat only sent ``api_key``, producing HTTP 401 on generate. ``_auth_headers`` now falls back to ``admin_key`` for ``text_gen_webui`` (still preferring ``api_key`` when both are set).

**Addendum — 2026-05-12 correction:** Upstream ``oobabooga/textgen`` splits auth by route: ``GET /v1/internal/model/info`` uses the **API** key; ``GET /v1/internal/model/list`` and model load/unload use the **admin** key when each flag is set. The blanket “same key on chat and internal routes” line above is **not** accurate for current Textgen — see ``docs/research/textgen-lifecycle-verified.md`` and the lessons-learned entry “Textgen API vs admin Bearer by HTTP route”.

**Addendum — Textgen 401 with key in ``oai_compat`` only:** Detection returns ``text_gen_webui`` but ``build_provider`` only read ``get_api_key("text_gen_webui")`` and ``get_admin_key("text_gen_webui")``, not ``providers.oai_compat``. Users who set a single key under ``oai_compat`` for the OAI-compat node got no credentials on the provider dict and on the model-list fetch. **Fix:** ``get_textgen_auth_keys()`` merges ``text_gen_webui`` and ``oai_compat`` (and mirrors a single secret onto both ``api_key`` and ``admin_key``).

**Addendum — ``detected_backend`` stuck on Unknown:** The frontend maps any non-OK response to the label ``Unknown``. ``server/endpoints.py`` used one ``try`` for both ``from ..config`` and ``from ..detection``; if config import failed, ``detect_backend`` was set to ``None`` and the detect handler crashed when calling it → 500 → Unknown. **Fix:** import config and detection in separate ``try`` blocks; return HTTP 200 with ``generic`` when the handler degrades; load ``model_list`` only inside ``HAS_SERVER``. **Fix:** ``model_list`` tries ``from .detection`` then ``from detection import`` so it works as a package submodule (ComfyUI) and as a flat test import; same pattern for ``get_admin_key`` / ``get_api_key`` via ``.config`` then ``config``.

## Provider UI: ``detected_backend`` stuck on “detecting…” (2026-05-12)

**Severity:** Medium — operator thinks detection failed while the server already logged a match  
**What happened:** After `POST /llm-bikeshed/models/oai-compat` returned, the read-only `detected_backend` text widget sometimes stayed on ``detecting…`` even though Python logged Textgen/LM Studio.  
**Root cause:** The frontend only assigned ``backendWidget.value`` when ``backend != null``. Any response shape that yielded a null/omitted ``backend`` (transient error, race, or older handler) never cleared the placeholder; ``setDirtyCanvas(true)`` alone did not always repaint text widgets in some Comfy builds.  
**Fix:** Always set a terminal label (``formatBackendName`` → ``Unknown`` when missing); add ``loaded_model_status``; call ``setDirtyCanvas(true, true)`` and ``app.graph.setDirtyCanvas(true)`` after updates; drop the null-only gate.  
**Prevention:** Treat async refresh UI as “must reach a terminal state”; never gate label updates on optional JSON fields without a fallback; after mutating extension-added widgets, mark both node and graph dirty.

## Options merge: ``options_in`` ignored in toggle builder

**Date:** 2026-05-12  
**Severity:** Medium — chained Options nodes dropped upstream keys  
**What happened:** LM Studio / Textgen tests expected ``options_in`` to merge into the output dict; ``build_toggle_options`` accepted an ``options_in`` parameter but callers only passed ``kwargs``, so upstream dicts were discarded unless the third argument was passed explicitly.  
**Root cause:** ``options_in`` was not read from ``kwargs`` when the positional argument was omitted.  
**Fix:** When ``options_in`` is ``None``, use ``kwargs.get("options_in")`` if it is a dict, then merge toggled params on top.  
**Prevention:** For helpers called as ``fn(params, kwargs)``, merge dict inputs from ``kwargs`` explicitly or document a single entrypoint; regression-test option chaining.

## Textgen API vs admin Bearer by HTTP route (upstream split)

**Date:** 2026-05-12  
**Severity:** Medium — wrong header on ``GET /v1/internal/model/info`` when ``--api-key`` and ``--admin-key`` differ breaks “already loaded” detection and can force redundant loads  
**What happened:** ``OAICompatAdapter._ensure_model_loaded`` sent admin-priority ``Authorization`` to ``/v1/internal/model/info``. Comments implied one Textgen secret covered chat and all ``/v1/internal/*`` routes.  
**Root cause:** Assumption from informal docs without reading ``oobabooga/textgen`` ``modules/api/script.py``, where ``model/info`` uses ``check_key`` (API key) and ``model/list``, ``model/load``, ``model/unload`` use ``check_admin_key``.  
**Fix:** Use ``_auth_headers`` for ``model/info`` and ``_admin_headers`` for load/unload; extend model refresh to call ``model/info`` for Textgen and show the loaded name in the UI; record citations in ``docs/research/textgen-lifecycle-verified.md``.  
**Prevention:** For “OpenAI-compatible” servers with extra internal routes, verify each route’s ``Depends`` in source; add tests with **distinct** API and admin bearer values when both exist.

## ``nodes/providers.py``: pytest import vs package-relative imports (2026-05-12)

**Severity:** Low — breaks test collection only  
**What happened:** New tests imported ``nodes.providers`` while the module used only ``from ..config`` / ``from ..detection``; under pytest ``nodes`` is treated as a top-level package, so ``..`` raised *attempted relative import beyond top-level package*.  
**Root cause:** Same dual-context pattern already handled in ``nodes/generation.py`` (Comfy loads the repo as a subpackage; tests add ``nodes`` on ``sys.path``).  
**Fix:** Wrap provider imports in ``try: relative except ImportError: absolute`` like ``generation.py``.  
**Prevention:** Any new ``nodes/*.py`` that pytest imports directly should use the try/except import pattern or be tested only via the pack root package.
