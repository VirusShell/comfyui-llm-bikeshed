# Tasks: ComfyUI LLM Bikeshed

## Phase 1: Make It Work (POC)

Focus: Vertical slice — LM Studio end-to-end first, then layer in remaining backends, options, advanced gen, and utilities. Skip tests, accept shortcuts.

### 1A: Project Scaffold

- [x] 1.1 Create project scaffold files
  - **Do**:
    1. Create `version.py` with `__version__ = "0.1.0"`
    2. Create `pyproject.toml` with project metadata, `dependencies = ["pyyaml>=6.0", "requests>=2.28.0"]`, `[tool.comfy]` section, `[tool.ruff]` section with `select = ["E", "F", "W", "I"]` and `target-version = "py310"`
    3. Create `.gitignore` with `config.yaml`, `__pycache__/`, `*.pyc`, `.ruff_cache/`, `.pytest_cache/`, `*.egg-info/`
  - **Files**: `version.py`, `pyproject.toml`, `.gitignore`
  - **Done when**: All three files exist with correct content
  - **Verify**: `python -c "exec(open('version.py').read()); print(__version__)"` prints `0.1.0`
  - **Commit**: `feat(scaffold): add pyproject.toml, version.py, and .gitignore`
  - _Requirements: NFR-4, NFR-8_

- [x] 1.2 [P] Create package directory structure and __init__ stubs
  - **Do**:
    1. Create directories: `nodes/`, `adapters/`, `config/`, `graph/`, `server/`, `js/`, `presets/`, `tests/`
    2. Create `__init__.py` stubs in `nodes/`, `adapters/`, `config/`, `graph/`, `server/`, `tests/`
    3. Create `presets/README.txt` with placeholder text
  - **Files**: All `__init__.py` stubs, `presets/README.txt`
  - **Done when**: All directories and stubs exist
  - **Verify**: `python -c "import os; dirs=['nodes','adapters','config','graph','server','tests']; assert all(os.path.isfile(d+'/__init__.py') for d in dirs)"`
  - **Commit**: `feat(scaffold): create package directories and __init__ stubs`
  - _Design: Directory Structure_

- [x] 1.3 [P] Create config.example.yaml
  - **Do**:
    1. Create `config.example.yaml` with `providers:` section containing `ollama`, `lm_studio`, `text_gen_webui` entries
    2. Each entry has `url` and `timeout: 120`
    3. LM Studio and text-gen-webui have commented-out `api_key`/`admin_key` fields
  - **Files**: `config.example.yaml`
  - **Done when**: YAML file parses correctly and contains all three provider sections
  - **Verify**: `python -c "import yaml; d=yaml.safe_load(open('config.example.yaml')); assert all(k in d['providers'] for k in ['ollama','lm_studio','text_gen_webui'])"`
  - **Commit**: `feat(config): add config.example.yaml with provider defaults`
  - _Requirements: AC-12.1, FR-10_

- [x] 1.4 [VERIFY] Quality checkpoint: ruff check
  - **Do**: Install ruff, run lint on project
  - **Verify**: `pip install ruff && ruff check . && echo PASS`
  - **Done when**: No lint errors
  - **Commit**: `chore(scaffold): pass quality checkpoint` (if fixes needed)

### 1B: Config System

- [x] 1.5 Create deep_merge utility
  - **Do**:
    1. Implement `deep_merge(base, override) -> dict` in `config/merge.py`
    2. Uses `copy.deepcopy` for immutability
    3. Recursively merges nested dicts; override values win for non-dict values
  - **Files**: `config/merge.py`
  - **Done when**: Function handles nested dicts, non-dict overrides, and disjoint keys
  - **Verify**: `python -c "from config.merge import deep_merge; r=deep_merge({'a':{'b':1,'c':2}},{'a':{'b':99}}); assert r=={'a':{'b':99,'c':2}}; print('PASS')"`
  - **Commit**: `feat(config): add deep_merge utility`
  - _Requirements: AC-12.3, AC-12.4_
  - _Design: Config Module_

- [x] 1.6 Create config module (load_config, get_config, get_api_key)
  - **Do**:
    1. Implement `load_config()` in `config/__init__.py` — reads `config.example.yaml`, deep-merges with `config.yaml` if present, caches in module-level `_config`
    2. Implement `get_config()` — returns cached config, calls `load_config()` on first access
    3. Implement `get_api_key(provider)` — checks config, then env var `LLM_BIKESHED_{PROVIDER}_API_KEY`
    4. Implement `get_admin_key(provider)` — checks `admin_key`, falls back to `api_key`, then env var
    5. Use `yaml.safe_load()` only
    6. Set up `logging.getLogger("llm-bikeshed")`
  - **Files**: `config/__init__.py`
  - **Done when**: Config loads from example file, merges user overrides, resolves API keys
  - **Verify**: `python -c "from config import get_config; c=get_config(); assert c['providers']['ollama']['url']=='http://localhost:11434'; print('PASS')"`
  - **Commit**: `feat(config): implement config module with merge-on-load and API key resolution`
  - _Requirements: FR-10, AC-12.1 through AC-12.7, AC-4.2_
  - _Design: Config Module_

- [x] 1.7 [VERIFY] Quality checkpoint: ruff check
  - **Do**: Run lint on project
  - **Verify**: `ruff check . && echo PASS`
  - **Done when**: No lint errors
  - **Commit**: `chore(config): pass quality checkpoint` (if fixes needed)

### 1C: Adapter Layer (OAI-Compat for LM Studio POC)

- [x] 1.8 Create adapter base protocol
  - **Do**:
    1. Define `LLMAdapter` Protocol class in `adapters/base.py`
    2. Single method: `generate(provider, messages, options, skip_unload) -> str`
    3. Add `_raise_on_error(response, backend, url)` shared helper
  - **Files**: `adapters/base.py`
  - **Done when**: Protocol class and error helper defined with type hints
  - **Verify**: `python -c "from adapters.base import LLMAdapter, _raise_on_error; print('PASS')"`
  - **Commit**: `feat(adapters): add base adapter protocol and error helper`
  - _Requirements: NFR-2, NFR-3_
  - _Design: Adapters — base.py_

- [x] 1.9 Create OAI-compatible adapter
  - **Do**:
    1. Implement `OAICompatAdapter` in `adapters/oai_compat.py`
    2. Add `BACKEND_ALLOWLISTS` dict with `lm_studio` and `text_gen_webui` param sets
    3. Add `NAME_MAPS` dict for per-backend param name mapping
    4. Implement `generate()` — builds payload, maps/filters options, adds auth headers, calls `POST {url}/v1/chat/completions`, extracts `choices[0].message.content`
    5. Handle LM Studio TTL (top-level `ttl` param, extended mid-chain)
    6. Add `stream: False` to all requests
  - **Files**: `adapters/oai_compat.py`
  - **Done when**: Adapter builds correct payloads for LM Studio backend with allowlist filtering
  - **Verify**: `python -c "from adapters.oai_compat import OAICompatAdapter; a=OAICompatAdapter(); assert 'temperature' in a.BACKEND_ALLOWLISTS['lm_studio']; print('PASS')"`
  - **Commit**: `feat(adapters): implement OAI-compatible adapter for LM Studio`
  - _Requirements: FR-6, FR-7, FR-18_
  - _Design: Adapters — oai_compat.py_

- [x] 1.10 Create adapter registry
  - **Do**:
    1. In `adapters/__init__.py`, import `OAICompatAdapter`
    2. Create `_ADAPTERS` dict with `"oai_compat": OAICompatAdapter()` (singleton)
    3. Implement `get_adapter(adapter_type) -> LLMAdapter`
    4. Leave `ollama_native` key for later
  - **Files**: `adapters/__init__.py`
  - **Done when**: `get_adapter("oai_compat")` returns adapter instance
  - **Verify**: `python -c "from adapters import get_adapter; a=get_adapter('oai_compat'); print('PASS')"`
  - **Commit**: `feat(adapters): add adapter registry with OAI-compat singleton`
  - _Design: Adapter Registry_

- [x] 1.11 [VERIFY] Quality checkpoint: ruff check
  - **Do**: Run lint on project
  - **Verify**: `ruff check . && echo PASS`
  - **Done when**: No lint errors
  - **Commit**: `chore(adapters): pass quality checkpoint` (if fixes needed)

### 1D: Graph Introspection

- [x] 1.12 Implement graph introspection module
  - **Do**:
    1. Implement `find_downstream_nodes(prompt, node_id, output_index)` in `graph/introspection.py`
    2. Implement `has_downstream_gen_node(prompt, node_id, meta_output_index)` — checks if any downstream node is in `GENERATION_CLASS_TYPES`
    3. Define `GENERATION_CLASS_TYPES = {"LLMGenerate", "LLMGenerateAdvanced"}`
  - **Files**: `graph/introspection.py`, `graph/__init__.py`
  - **Done when**: Functions correctly reverse-index PROMPT dict to find downstream gen nodes
  - **Verify**: `python -c "from graph.introspection import has_downstream_gen_node; p={'1':{'class_type':'LLMGenerate','inputs':{'meta':['2',1]}},'2':{'class_type':'LLMGenerate','inputs':{}}}; assert has_downstream_gen_node(p,'2',1)==True; print('PASS')"`
  - **Commit**: `feat(graph): implement graph introspection for unload deferral`
  - _Requirements: FR-9, AC-7.2, AC-7.3, AC-7.4_
  - _Design: Graph Introspection_

### 1E: LM Studio Provider Node

- [x] 1.13 Create LM Studio Provider node
  - **Do**:
    1. Implement `LLMProviderLMStudio` class in `nodes/providers.py`
    2. `INPUT_TYPES`: `url` (STRING, default `http://localhost:1234`), `model` (COMBO `["(refresh to load)"]`), `ttl` (INT, default 30), optional `model_fallback` (STRING, `defaultInput: True`)
    3. `RETURN_TYPES = ("LLM_PROVIDER",)`, `FUNCTION = "build_provider"`
    4. `CATEGORY = "LLM Bikeshed/providers"`
    5. `build_provider()` resolves model (fallback overrides COMBO), gets config, builds provider dict with `adapter: "oai_compat"`, `backend: "lm_studio"`, `memory: {"ttl": ttl, "keep_alive": None}`
    6. Import `get_config`, `get_api_key` from config module
  - **Files**: `nodes/providers.py`
  - **Done when**: Node class has correct INPUT_TYPES, RETURN_TYPES, and build_provider method
  - **Verify**: `python -c "from nodes.providers import LLMProviderLMStudio; n=LLMProviderLMStudio(); p=n.build_provider('http://localhost:1234','test-model',30); assert p[0]['adapter']=='oai_compat'; print('PASS')"`
  - **Commit**: `feat(nodes): add LM Studio Provider node`
  - _Requirements: FR-1, AC-1.1 through AC-1.9, FR-21_
  - _Design: Provider Nodes — LM Studio_

- [x] 1.14 [VERIFY] Quality checkpoint: ruff check
  - **Do**: Run lint on project
  - **Verify**: `ruff check . && echo PASS`
  - **Done when**: No lint errors
  - **Commit**: `chore(nodes): pass quality checkpoint` (if fixes needed)

### 1F: Basic Generation Node

- [x] 1.15 Create _build_messages helper
  - **Do**:
    1. Add `_build_messages(system_prompt, prompt) -> list[dict]` in `nodes/generation.py`
    2. System prompt added as `role: "system"` only if non-empty
    3. User prompt always added as `role: "user"`
  - **Files**: `nodes/generation.py`
  - **Done when**: Helper builds correct message list with and without system prompt
  - **Verify**: `python -c "from nodes.generation import _build_messages; m=_build_messages('sys','user'); assert len(m)==2 and m[0]['role']=='system'; m2=_build_messages('','user'); assert len(m2)==1; print('PASS')"`
  - **Commit**: `feat(generation): add _build_messages helper`
  - _Design: Generation Nodes — shared helper_

- [x] 1.16 Create Basic Generation node (LLMGenerate)
  - **Do**:
    1. Implement `LLMGenerate` class in `nodes/generation.py`
    2. `INPUT_TYPES`: required `provider` (LLM_PROVIDER), `prompt` (STRING, multiline); optional `system_prompt` (STRING, multiline), `temperature` (FLOAT, default 0.7, 0.0-2.0), `max_tokens` (INT, default 1024), `seed` (INT, default -1)
    3. Hidden inputs: `"prompt": "PROMPT"`, `"unique_id": "UNIQUE_ID"`
    4. `RETURN_TYPES = ("STRING", "LLM_META")`, `FUNCTION = "generate"`
    5. `IS_CHANGED` returns `float("NaN")`
    6. `generate()`: build inline options (skip sentinels), get adapter, check downstream, call adapter, build meta, return tuple
  - **Files**: `nodes/generation.py`
  - **Done when**: Node class has all required widgets, hidden inputs, and generation logic
  - **Verify**: `python -c "from nodes.generation import LLMGenerate; it=LLMGenerate.INPUT_TYPES(); assert 'provider' in it['required']; assert 'prompt' in it['hidden']; print('PASS')"`
  - **Commit**: `feat(generation): implement Basic Generation node (LLMGenerate)`
  - _Requirements: FR-2, AC-5.1 through AC-5.8, FR-17_
  - _Design: Generation Nodes — Basic_

- [x] 1.17 [VERIFY] Quality checkpoint: ruff check
  - **Do**: Run lint on project
  - **Verify**: `ruff check . && echo PASS`
  - **Done when**: No lint errors
  - **Commit**: `chore(generation): pass quality checkpoint` (if fixes needed)

### 1G: PromptServer Endpoints (LM Studio)

- [x] 1.18 Create LM Studio model fetch helper
  - **Do**:
    1. Implement `_fetch_models_lm_studio(url, api_key, timeout)` in `server/endpoints.py`
    2. `GET {url}/v1/models`, auth header if api_key provided
    3. Returns list of model IDs from `response.json()["data"]`
    4. Import `requests`, `logging`
  - **Files**: `server/endpoints.py`
  - **Done when**: Function correctly extracts model IDs from LM Studio response format
  - **Verify**: `python -c "from server.endpoints import _fetch_models_lm_studio; print('PASS')"`
  - **Commit**: `feat(server): add LM Studio model fetch helper`
  - _Requirements: FR-13, AC-1.2_
  - _Design: PromptServer — _fetch_models_lm_studio_

- [x] 1.19 Create LM Studio PromptServer endpoint
  - **Do**:
    1. Add `@PromptServer.instance.routes.post("/llm-bikeshed/models/lm-studio")` async handler
    2. Extracts `url` from request JSON
    3. Tries without auth first, retries with key on 401/403
    4. Returns `{"models": [...]}` or `{"models": []}` on failure
    5. Uses `asyncio.to_thread()` for sync HTTP call
    6. Import `PromptServer` from `server`, `web` from `aiohttp`, `asyncio`
    7. Guard the import with try/except for standalone testing
  - **Files**: `server/endpoints.py`
  - **Done when**: Endpoint registered with auth-first-then-key pattern
  - **Verify**: `python -c "from server.endpoints import _fetch_models_lm_studio; print('PASS')"` (endpoint registration requires ComfyUI runtime)
  - **Commit**: `feat(server): add LM Studio model list endpoint`
  - _Requirements: FR-13, AC-1.2, AC-1.9_
  - _Design: PromptServer Endpoints_

- [x] 1.20 [VERIFY] Quality checkpoint: ruff check
  - **Do**: Run lint on project
  - **Verify**: `ruff check . && echo PASS`
  - **Done when**: No lint errors
  - **Commit**: `chore(server): pass quality checkpoint` (if fixes needed)

### 1H: Frontend JS

- [x] 1.21 Create model_dropdown.js frontend extension
  - **Do**:
    1. Create `js/model_dropdown.js`
    2. Import `app` from ComfyUI scripts
    3. Define `PROVIDER_CONFIG` mapping node class names to endpoints and default URLs
    4. Implement `fetchModels(endpoint, url)` async helper
    5. Register extension `llm-bikeshed.model-dropdown` with `nodeCreated` hook
    6. In hook: find model/url widgets, add refresh button, initial model fetch
    7. Handle saved model persistence and offline fallback
  - **Files**: `js/model_dropdown.js`
  - **Done when**: JS extension file exists with all three provider configs and fetch/refresh logic
  - **Verify**: `grep -q "llm-bikeshed.model-dropdown" js/model_dropdown.js && grep -q "PROVIDER_CONFIG" js/model_dropdown.js && echo PASS`
  - **Commit**: `feat(js): implement model dropdown frontend extension`
  - _Requirements: FR-11, AC-13.1 through AC-13.6_
  - _Design: Frontend JS_

### 1I: Node Registration (__init__.py) — POC Vertical Slice

- [x] 1.22 Create root __init__.py with LM Studio POC registration
  - **Do**:
    1. Import `LLMProviderLMStudio` from `nodes.providers`
    2. Import `LLMGenerate` from `nodes.generation`
    3. Import `server` module (triggers endpoint registration)
    4. Set `NODE_CLASS_MAPPINGS` with POC nodes
    5. Set `NODE_DISPLAY_NAME_MAPPINGS` with display names
    6. Set `WEB_DIRECTORY = "./js"`
    7. Set `__all__` with required exports
  - **Files**: `__init__.py`
  - **Done when**: Root init imports POC nodes and sets all required ComfyUI exports
  - **Verify**: `python -c "import importlib.util; spec=importlib.util.spec_from_file_location('pkg','__init__.py'); print('PASS')"` (full import needs ComfyUI)
  - **Commit**: `feat(init): register LM Studio + Basic Gen POC nodes`
  - _Design: Node Registration_

- [x] 1.23 [VERIFY] Quality checkpoint: ruff check
  - **Do**: Run lint on project
  - **Verify**: `ruff check . && echo PASS`
  - **Done when**: No lint errors
  - **Commit**: `chore: pass POC vertical slice quality checkpoint` (if fixes needed)

### 1J: Remaining Providers

- [x] 1.24 Add Ollama Native adapter
  - **Do**:
    1. Implement `OllamaAdapter` in `adapters/ollama.py`
    2. `ALLOWED_OPTIONS` set with all Ollama `options` field params
    3. `NAME_MAP` with `max_tokens` -> `num_predict`
    4. `generate()`: maps/filters options into `options` object, sets `keep_alive` top-level, sets `stream: False`, calls `POST {url}/api/chat`, extracts `message.content`
    5. Mid-chain: use `"5m"` keep_alive; last node: use provider's keep_alive
  - **Files**: `adapters/ollama.py`
  - **Done when**: Adapter builds correct Ollama payload with options nested under `options` key
  - **Verify**: `python -c "from adapters.ollama import OllamaAdapter; a=OllamaAdapter(); assert 'num_predict' in a.ALLOWED_OPTIONS; assert a.NAME_MAP.get('max_tokens')=='num_predict'; print('PASS')"`
  - **Commit**: `feat(adapters): implement Ollama Native adapter`
  - _Requirements: FR-5, FR-7_
  - _Design: Adapters — ollama.py_

- [x] 1.25 Register Ollama adapter in registry
  - **Do**:
    1. Import `OllamaAdapter` in `adapters/__init__.py`
    2. Add `"ollama_native": OllamaAdapter()` to `_ADAPTERS` dict
  - **Files**: `adapters/__init__.py`
  - **Done when**: `get_adapter("ollama_native")` returns OllamaAdapter instance
  - **Verify**: `python -c "from adapters import get_adapter; a=get_adapter('ollama_native'); print(type(a).__name__)"` prints `OllamaAdapter`
  - **Commit**: `feat(adapters): register Ollama adapter`
  - _Design: Adapter Registry_

- [x] 1.26 Add text-gen-webui lifecycle methods to OAI adapter
  - **Do**:
    1. Add `_ensure_model_loaded(provider, model)` to `OAICompatAdapter` — checks `GET /v1/internal/model/info`, loads via `POST /v1/internal/model/load` if needed
    2. Add `_unload_model(provider)` — `POST /v1/internal/model/unload`, swallows exceptions with warning log
    3. Add `_admin_headers(provider)` — uses admin_key, falls back to api_key
    4. Wire lifecycle calls into `generate()`: call `_ensure_model_loaded` before generation, call `_unload_model` after generation when `not skip_unload` and `backend == "text_gen_webui"`
  - **Files**: `adapters/oai_compat.py`
  - **Done when**: text-gen-webui lifecycle (check -> load -> generate -> unload) is wired in
  - **Verify**: `python -c "from adapters.oai_compat import OAICompatAdapter; a=OAICompatAdapter(); assert hasattr(a,'_ensure_model_loaded'); assert hasattr(a,'_unload_model'); print('PASS')"`
  - **Commit**: `feat(adapters): add text-gen-webui model lifecycle management`
  - _Requirements: FR-16, FR-19_
  - _Design: Adapters — text-gen-webui lifecycle_

- [x] 1.27 [VERIFY] Quality checkpoint: ruff check
  - **Do**: Run lint on project
  - **Verify**: `ruff check . && echo PASS`
  - **Done when**: No lint errors
  - **Commit**: `chore(adapters): pass quality checkpoint` (if fixes needed)

- [x] 1.28 Add Ollama Provider node
  - **Do**:
    1. Add `LLMProviderOllama` class to `nodes/providers.py`
    2. `INPUT_TYPES`: `url` (default `http://localhost:11434`), `model` (COMBO), `keep_alive` (STRING, default `"30s"`), optional `model_fallback`
    3. `build_provider()`: adapter `"ollama_native"`, backend `"ollama"`, no api_key
    4. Memory: `{"keep_alive": keep_alive, "ttl": None}`
  - **Files**: `nodes/providers.py`
  - **Done when**: Ollama Provider node builds correct provider dict
  - **Verify**: `python -c "from nodes.providers import LLMProviderOllama; n=LLMProviderOllama(); p=n.build_provider('http://localhost:11434','llama3','30s'); assert p[0]['adapter']=='ollama_native'; print('PASS')"`
  - **Commit**: `feat(nodes): add Ollama Provider node`
  - _Requirements: FR-1, AC-3.1 through AC-3.7_
  - _Design: Provider Nodes — Ollama_

- [x] 1.29 Add text-gen-webui Provider node
  - **Do**:
    1. Add `LLMProviderTextGenWebUI` class to `nodes/providers.py`
    2. `INPUT_TYPES`: `url` (default `http://localhost:5000`), `model` (COMBO), optional `model_fallback`
    3. No memory widget (uses explicit unload)
    4. `build_provider()`: adapter `"oai_compat"`, backend `"text_gen_webui"`, resolves both `api_key` and `admin_key`
  - **Files**: `nodes/providers.py`
  - **Done when**: text-gen-webui Provider node builds correct provider dict with both keys
  - **Verify**: `python -c "from nodes.providers import LLMProviderTextGenWebUI; n=LLMProviderTextGenWebUI(); p=n.build_provider('http://localhost:5000','model1'); assert p[0]['backend']=='text_gen_webui'; print('PASS')"`
  - **Commit**: `feat(nodes): add text-gen-webui Provider node`
  - _Requirements: FR-1, AC-2.1 through AC-2.10_
  - _Design: Provider Nodes — text-gen-webui_

- [x] 1.30 [VERIFY] Quality checkpoint: ruff check
  - **Do**: Run lint on project
  - **Verify**: `ruff check . && echo PASS`
  - **Done when**: No lint errors
  - **Commit**: `chore(nodes): pass quality checkpoint` (if fixes needed)

### 1K: Remaining PromptServer Endpoints

- [x] 1.31 [P] Add Ollama model fetch helper and endpoint
  - **Do**:
    1. Add `_fetch_models_ollama(url, timeout)` in `server/endpoints.py`
    2. `GET {url}/api/tags`, extracts `models[].name`
    3. Add `@PromptServer.instance.routes.post("/llm-bikeshed/models/ollama")` async handler
    4. Same pattern as LM Studio endpoint (asyncio.to_thread, graceful degradation)
  - **Files**: `server/endpoints.py`
  - **Done when**: Ollama endpoint registered with correct model extraction
  - **Verify**: `python -c "from server.endpoints import _fetch_models_ollama; print('PASS')"`
  - **Commit**: `feat(server): add Ollama model list endpoint`
  - _Requirements: FR-13, AC-3.2_

- [x] 1.32 [P] Add text-gen-webui model fetch helper and endpoint
  - **Do**:
    1. Add `_fetch_models_text_gen_webui(url, admin_key, timeout)` in `server/endpoints.py`
    2. `GET {url}/v1/internal/model/list`, uses admin key, extracts `model_names`
    3. Add `@PromptServer.instance.routes.post("/llm-bikeshed/models/text-gen-webui")` async handler
    4. Auth-first pattern (try without, retry with key on 401/403)
  - **Files**: `server/endpoints.py`
  - **Done when**: text-gen-webui endpoint registered with admin key handling
  - **Verify**: `python -c "from server.endpoints import _fetch_models_text_gen_webui; print('PASS')"`
  - **Commit**: `feat(server): add text-gen-webui model list endpoint`
  - _Requirements: FR-13, AC-2.2, AC-2.10_

- [x] 1.33 Add config reload endpoint
  - **Do**:
    1. Add `@PromptServer.instance.routes.post("/llm-bikeshed/reload-config")` async handler
    2. Calls `load_config()` and returns `{"status": "ok"}`
  - **Files**: `server/endpoints.py`
  - **Done when**: Reload endpoint registered
  - **Verify**: `grep -q "reload-config" server/endpoints.py && echo PASS`
  - **Commit**: `feat(server): add config reload endpoint`
  - _Requirements: FR-14, AC-12.6_

- [x] 1.34 [VERIFY] Quality checkpoint: ruff check
  - **Do**: Run lint on project
  - **Verify**: `ruff check . && echo PASS`
  - **Done when**: No lint errors
  - **Commit**: `chore(server): pass quality checkpoint` (if fixes needed)

### 1L: Advanced Generation Node

- [x] 1.35 Create Advanced Generation node (LLMGenerateAdvanced)
  - **Do**:
    1. Implement `LLMGenerateAdvanced` class in `nodes/generation.py`
    2. `INPUT_TYPES`: required `prompt` (STRING, multiline, `defaultInput: True`); optional `provider` (LLM_PROVIDER), `system_prompt` (STRING, multiline, `defaultInput: True`), `options` (LLM_OPTIONS), `meta` (LLM_META)
    3. Hidden inputs: `"prompt": "PROMPT"`, `"unique_id": "UNIQUE_ID"`
    4. `RETURN_TYPES = ("STRING", "LLM_META")`
    5. `IS_CHANGED` returns `float("NaN")`
    6. `VALIDATE_INPUTS` returns True
    7. `generate()`: resolve provider from explicit input or meta, resolve options from explicit or meta, check downstream, call adapter, build meta, return tuple
    8. Raise `ValueError` if no provider available
  - **Files**: `nodes/generation.py`
  - **Done when**: Advanced node resolves provider/options from meta with correct precedence
  - **Verify**: `python -c "from nodes.generation import LLMGenerateAdvanced; it=LLMGenerateAdvanced.INPUT_TYPES(); assert 'meta' in it['optional']; assert 'options' in it['optional']; print('PASS')"`
  - **Commit**: `feat(generation): implement Advanced Generation node (LLMGenerateAdvanced)`
  - _Requirements: FR-3, AC-6.1 through AC-6.11, FR-17_
  - _Design: Generation Nodes — Advanced_

- [x] 1.36 [VERIFY] Quality checkpoint: ruff check
  - **Do**: Run lint on project
  - **Verify**: `ruff check . && echo PASS`
  - **Done when**: No lint errors
  - **Commit**: `chore(generation): pass quality checkpoint` (if fixes needed)

### 1M: Options Nodes

- [x] 1.37 Create Ollama Core Options node
  - **Do**:
    1. Implement `LLMOptionsOllamaCore` in `nodes/options_ollama.py`
    2. Sentinel-value pattern with `SENTINELS` class dict
    3. 7 params: `temperature` (-1.0), `top_k` (-1), `top_p` (-1.0), `seed` (-1), `num_predict` (-1), `num_ctx` (-1), `stop` ("")
    4. Optional `options_in` (LLM_OPTIONS) for chaining from Extra node
    5. `build_options()`: start from `options_in` if present, add non-sentinel values, return dict
  - **Files**: `nodes/options_ollama.py`
  - **Done when**: Sentinel values correctly excluded, non-sentinel values included
  - **Verify**: `python -c "from nodes.options_ollama import LLMOptionsOllamaCore; n=LLMOptionsOllamaCore(); o=n.build_options(temperature=0.5, top_k=-1, top_p=-1.0, seed=-1, num_predict=-1, num_ctx=-1, stop=''); assert o[0]=={'temperature':0.5}; print('PASS')"`
  - **Commit**: `feat(options): implement Ollama Core Options node with sentinel pattern`
  - _Requirements: FR-4, AC-8.1 through AC-8.4_
  - _Design: Options Nodes — Ollama Core_

- [x] 1.38 Create Ollama Extra Options node
  - **Do**:
    1. Implement `LLMOptionsOllamaExtra` in `nodes/options_ollama.py`
    2. Toggle pattern with `PARAMS` list (10 params)
    3. Each param has `enable_{name}` BOOLEAN toggle and value widget
    4. `mirostat` uses COMBO `[0, 1, 2]` instead of INT widget
    5. Optional `options_in` (LLM_OPTIONS)
    6. `build_options()`: only include toggled-on params
  - **Files**: `nodes/options_ollama.py`
  - **Done when**: Toggle-enabled params included, toggle-disabled excluded
  - **Verify**: `python -c "from nodes.options_ollama import LLMOptionsOllamaExtra; n=LLMOptionsOllamaExtra(); o=n.build_options(enable_mirostat=True, mirostat=2, enable_repeat_penalty=False, repeat_penalty=1.1); assert o[0]=={'mirostat':2}; print('PASS')"`
  - **Commit**: `feat(options): implement Ollama Extra Options node with toggle pattern`
  - _Requirements: FR-4, AC-8.5 through AC-8.9_
  - _Design: Options Nodes — Ollama Extra_

- [x] 1.39 [VERIFY] Quality checkpoint: ruff check
  - **Do**: Run lint on project
  - **Verify**: `ruff check . && echo PASS`
  - **Done when**: No lint errors
  - **Commit**: `chore(options): pass quality checkpoint` (if fixes needed)

- [x] 1.40 [P] Create LM Studio Options node
  - **Do**:
    1. Implement `LLMOptionsLMStudio` in `nodes/options_lm_studio.py`
    2. Toggle pattern, 9 params: temperature, top_p, max_tokens, seed, stop, top_k, repeat_penalty, presence_penalty, frequency_penalty
    3. Same structure as Ollama Extra (BOOLEAN toggle per param)
    4. `CATEGORY = "LLM Bikeshed/options"`
  - **Files**: `nodes/options_lm_studio.py`
  - **Done when**: Node builds options dict with only toggled-on params
  - **Verify**: `python -c "from nodes.options_lm_studio import LLMOptionsLMStudio; n=LLMOptionsLMStudio(); it=n.INPUT_TYPES(); assert 'enable_temperature' in it.get('optional',it.get('required',{})); print('PASS')"`
  - **Commit**: `feat(options): implement LM Studio Options node`
  - _Requirements: FR-4, AC-9.1 through AC-9.5_
  - _Design: Options Nodes — LM Studio_

- [x] 1.41 [P] Create text-gen-webui Options node
  - **Do**:
    1. Implement `LLMOptionsTextGenWebUI` in `nodes/options_text_gen_webui.py`
    2. Toggle pattern, 12 params: temperature, top_p, max_tokens, seed, stop, top_k, min_p, repeat_penalty, presence_penalty, frequency_penalty, typical_p, tfs
    3. Same structure as LM Studio Options
  - **Files**: `nodes/options_text_gen_webui.py`
  - **Done when**: Node builds options dict with only toggled-on params
  - **Verify**: `python -c "from nodes.options_text_gen_webui import LLMOptionsTextGenWebUI; n=LLMOptionsTextGenWebUI(); it=n.INPUT_TYPES(); assert 'enable_tfs' in it.get('optional',it.get('required',{})); print('PASS')"`
  - **Commit**: `feat(options): implement text-gen-webui Options node`
  - _Requirements: FR-4, AC-10.1 through AC-10.5_
  - _Design: Options Nodes — text-gen-webui_

- [x] 1.42 [VERIFY] Quality checkpoint: ruff check
  - **Do**: Run lint on project
  - **Verify**: `ruff check . && echo PASS`
  - **Done when**: No lint errors
  - **Commit**: `chore(options): pass quality checkpoint` (if fixes needed)

### 1N: Utility Nodes

- [x] 1.43 [P] Create Preset Loader node
  - **Do**:
    1. Implement `LLMPresetLoader` in `nodes/utils.py`
    2. `INPUT_TYPES`: COMBO listing `.txt` files from `presets/` directory
    3. Fallback entry `"(no presets found)"` if directory empty
    4. `load_preset()`: reads file content, returns as STRING
    5. `CATEGORY = "LLM Bikeshed/utils"`
  - **Files**: `nodes/utils.py`
  - **Done when**: Node lists preset files and returns content as string
  - **Verify**: `python -c "from nodes.utils import LLMPresetLoader; it=LLMPresetLoader.INPUT_TYPES(); assert 'preset' in it['required']; print('PASS')"`
  - **Commit**: `feat(utils): implement Preset Loader node`
  - _Requirements: FR-12, AC-11.1 through AC-11.5_
  - _Design: Utility Nodes — Preset Loader_

- [x] 1.44 [P] Create Load Text File node
  - **Do**:
    1. Implement `LLMLoadTextFile` in `nodes/utils.py`
    2. `INPUT_TYPES`: COMBO listing `.txt` files from ComfyUI input directory
    3. Use `folder_paths.get_input_directory()` with try/except fallback for standalone testing
    4. Fallback entry `"(no .txt files found)"` if empty
    5. `load_file()`: reads file content, returns as STRING
  - **Files**: `nodes/utils.py`
  - **Done when**: Node lists text files and returns content
  - **Verify**: `python -c "from nodes.utils import LLMPresetLoader; print('PASS')"` (LLMLoadTextFile needs folder_paths)
  - **Commit**: `feat(utils): implement Load Text File node`
  - _Requirements: FR-20, AC-14.1 through AC-14.5_
  - _Design: Utility Nodes — Load Text File_

- [x] 1.45 [VERIFY] Quality checkpoint: ruff check
  - **Do**: Run lint on project
  - **Verify**: `ruff check . && echo PASS`
  - **Done when**: No lint errors
  - **Commit**: `chore(utils): pass quality checkpoint` (if fixes needed)

### 1O: Full Node Registration

- [x] 1.46 Update __init__.py with all 11 node registrations
  - **Do**:
    1. Import all node classes: 3 providers, 2 generation, 4 options (Ollama Core/Extra, LM Studio, text-gen-webui), 2 utils
    2. Import `server` module for endpoint registration
    3. Complete `NODE_CLASS_MAPPINGS` with all 11 entries
    4. Complete `NODE_DISPLAY_NAME_MAPPINGS` with display names
    5. Keep `WEB_DIRECTORY = "./js"` and `__all__`
  - **Files**: `__init__.py`
  - **Done when**: All 11 nodes registered in both mappings
  - **Verify**: `python -c "exec(open('__init__.py').read().split('from .server')[0]); print('skip server import')" || grep -c "LLM" __init__.py | python -c "import sys; n=int(sys.stdin.read()); assert n>=22; print('PASS')"` (verify at least 22 LLM references in file — 11 class + 11 display)
  - **Commit**: `feat(init): register all 11 node classes`
  - _Design: Node Registration_

- [x] 1.47 [VERIFY] Quality checkpoint: ruff check
  - **Do**: Run lint on project
  - **Verify**: `ruff check . && echo PASS`
  - **Done when**: No lint errors
  - **Commit**: `chore: pass full registration quality checkpoint` (if fixes needed)

- [x] 1.48 POC Checkpoint
  - **Do**:
    1. Verify all 11 node classes importable (without ComfyUI runtime)
    2. Verify config system works (load, merge, API key resolution)
    3. Verify adapter registry has both adapters
    4. Verify graph introspection works with sample PROMPT data
    5. Verify JS file has all three provider configs
    6. Count files: should have ~28 source files
  - **Done when**: All core modules importable and functional without ComfyUI
  - **Verify**: `python -c "from config import get_config; from adapters import get_adapter; from graph.introspection import has_downstream_gen_node; get_config(); get_adapter('oai_compat'); get_adapter('ollama_native'); print('POC PASS')"` && `grep -c "LLMProvider" js/model_dropdown.js`
  - **Commit**: `feat(poc): complete POC — all nodes, adapters, config, and frontend JS`

---

## Phase 2: Refactoring

Focus: Clean up code, add error handling, improve structure.

- [x] 2.1 Add VALIDATE_INPUTS to generation nodes
  - **Do**:
    1. Add `VALIDATE_INPUTS` classmethod to `LLMGenerate` — validate URL format in provider
    2. Update `VALIDATE_INPUTS` in `LLMGenerateAdvanced` — check that either `provider` or `meta` will be available (return True since connection values aren't available at validation time)
  - **Files**: `nodes/generation.py`
  - **Done when**: VALIDATE_INPUTS methods present on both generation nodes
  - **Verify**: `python -c "from nodes.generation import LLMGenerate, LLMGenerateAdvanced; assert hasattr(LLMGenerate, 'VALIDATE_INPUTS'); print('PASS')"`
  - **Commit**: `refactor(generation): add VALIDATE_INPUTS for pre-execution checks`
  - _Requirements: FR-15_

- [x] 2.2 Add structured error messages to adapters
  - **Do**:
    1. Ensure `_raise_on_error` includes backend name, URL, HTTP status, and response body (truncated to 500 chars)
    2. Add timeout handling — catch `requests.Timeout` and re-raise with descriptive message including backend name and URL
    3. Add connection error handling — catch `requests.ConnectionError` with backend offline message
  - **Files**: `adapters/base.py`, `adapters/oai_compat.py`, `adapters/ollama.py`
  - **Done when**: All error paths produce messages with backend name, URL, and status
  - **Verify**: `python -c "from adapters.base import _raise_on_error; print('PASS')"` && `grep -q "ConnectionError" adapters/oai_compat.py && echo PASS`
  - **Commit**: `refactor(adapters): improve error messages with backend context`
  - _Requirements: NFR-2, NFR-3_

- [x] 2.3 [VERIFY] Quality checkpoint: ruff check
  - **Do**: Run lint on project
  - **Verify**: `ruff check . && echo PASS`
  - **Done when**: No lint errors
  - **Commit**: `chore(refactor): pass quality checkpoint` (if fixes needed)

- [x] 2.4 Add logging throughout modules
  - **Do**:
    1. Add `logger = logging.getLogger("llm-bikeshed")` to all modules that need it
    2. Add info-level log for param filtering in adapters
    3. Add info-level log for config load/reload
    4. Add warning-level log for text-gen-webui unload failure
    5. Add info-level log for model fetch failures in PromptServer
  - **Files**: `adapters/ollama.py`, `adapters/oai_compat.py`, `config/__init__.py`, `server/endpoints.py`
  - **Done when**: All log points use `llm-bikeshed` logger with appropriate levels
  - **Verify**: `grep -r "getLogger" adapters/ config/ server/ | grep -c "llm-bikeshed"` shows >= 4
  - **Commit**: `refactor: add consistent logging across modules`
  - _Requirements: NFR-9_

- [x] 2.5 Extract toggle-based options builder to shared helper
  - **Do**:
    1. Create a reusable `build_toggle_options(params, kwargs, options_in)` function in `nodes/options_base.py`
    2. Refactor `LLMOptionsOllamaExtra`, `LLMOptionsLMStudio`, `LLMOptionsTextGenWebUI` to use it
    3. Keep `LLMOptionsOllamaCore` using sentinel pattern (different logic)
  - **Files**: `nodes/options_base.py`, `nodes/options_ollama.py`, `nodes/options_lm_studio.py`, `nodes/options_text_gen_webui.py`
  - **Done when**: All three toggle-based nodes use shared builder, reducing code duplication
  - **Verify**: `python -c "from nodes.options_base import build_toggle_options; print('PASS')"` && `ruff check .`
  - **Commit**: `refactor(options): extract shared toggle options builder`
  - _Design: Options Nodes_

- [x] 2.6 [VERIFY] Quality checkpoint: ruff check
  - **Do**: Run lint on project
  - **Verify**: `ruff check . && echo PASS`
  - **Done when**: No lint errors
  - **Commit**: `chore(refactor): pass quality checkpoint` (if fixes needed)

- [x] 2.7 Add type hints to all public functions
  - **Do**:
    1. Ensure all public functions in adapters, config, graph, server modules have full type annotations
    2. Add return type annotations to all FUNCTION methods on nodes
    3. Use `dict` not `Dict`, `list` not `List` (Python 3.10+)
  - **Files**: All `.py` files in `adapters/`, `config/`, `graph/`, `nodes/`, `server/`
  - **Done when**: All public functions have parameter and return type hints
  - **Verify**: `ruff check . --select ANN && echo PASS || echo "ANN check done"` (informational)
  - **Commit**: `refactor: add comprehensive type hints`
  - _Requirements: NFR-8_

- [x] 2.8 Create CHANGELOG.md and README.md
  - **Do**:
    1. Create `CHANGELOG.md` with v0.1.0 section listing all features
    2. Create `README.md` with project description, installation, configuration, usage, and node descriptions
  - **Files**: `CHANGELOG.md`, `README.md`
  - **Done when**: Both docs exist with correct content
  - **Verify**: `test -f CHANGELOG.md && test -f README.md && grep -q "0.1.0" CHANGELOG.md && echo PASS`
  - **Commit**: `docs: add CHANGELOG.md and README.md for v0.1.0`

- [x] 2.9 [VERIFY] Quality checkpoint: ruff check
  - **Do**: Run lint on project
  - **Verify**: `ruff check . && echo PASS`
  - **Done when**: No lint errors
  - **Commit**: `chore(refactor): pass final refactoring quality checkpoint` (if fixes needed)

---

## Phase 3: Testing

Focus: Add unit tests with mocked HTTP for internal logic.

- [x] 3.1 Set up pytest and test infrastructure
  - **Do**:
    1. Add `[project.optional-dependencies] dev = ["pytest>=7.0", "ruff>=0.4.0"]` to `pyproject.toml`
    2. Add `[tool.pytest.ini_options]` with `testpaths = ["tests"]`
    3. Create `tests/conftest.py` with shared fixtures (sample provider dicts, mock responses)
  - **Files**: `pyproject.toml`, `tests/conftest.py`
  - **Done when**: `pytest --collect-only` succeeds
  - **Verify**: `pip install pytest && pytest --collect-only && echo PASS`
  - **Commit**: `test(setup): configure pytest and create test fixtures`

- [x] 3.2 [P] Test config deep_merge
  - **Do**:
    1. Create `tests/test_config.py`
    2. Test: nested merge, override wins, disjoint keys preserved, empty override, empty base
  - **Files**: `tests/test_config.py`
  - **Done when**: All merge edge cases tested
  - **Verify**: `pytest tests/test_config.py -v && echo PASS`
  - **Commit**: `test(config): add deep_merge unit tests`

- [ ] 3.3 [P] Test config load and API key resolution
  - **Do**:
    1. Add tests to `tests/test_config.py`
    2. Test: load_config returns merged dict, get_api_key from config, get_api_key from env var, get_admin_key fallback chain
    3. Use `tmp_path` fixture and `monkeypatch` for env vars
  - **Files**: `tests/test_config.py`
  - **Done when**: Config loading and key resolution fully tested
  - **Verify**: `pytest tests/test_config.py -v && echo PASS`
  - **Commit**: `test(config): add config load and API key resolution tests`
  - _Requirements: AC-4.2, AC-12.3_

- [ ] 3.4 [VERIFY] Quality checkpoint: ruff + pytest
  - **Do**: Run lint and tests
  - **Verify**: `ruff check . && pytest tests/ -v && echo PASS`
  - **Done when**: No lint errors, all tests pass
  - **Commit**: `chore(tests): pass quality checkpoint` (if fixes needed)

- [ ] 3.5 [P] Test Ollama adapter
  - **Do**:
    1. Create `tests/test_adapters.py`
    2. Test: name mapping (`max_tokens` -> `num_predict`), allowlist filtering, payload structure (`options` nested), `keep_alive` top-level, mid-chain keep_alive = "5m"
    3. Mock `requests.post` using `monkeypatch`
  - **Files**: `tests/test_adapters.py`
  - **Done when**: All Ollama adapter behaviors tested with mocked HTTP
  - **Verify**: `pytest tests/test_adapters.py -v -k "ollama" && echo PASS`
  - **Commit**: `test(adapters): add Ollama adapter unit tests`

- [ ] 3.6 [P] Test OAI-compat adapter (LM Studio path)
  - **Do**:
    1. Add tests to `tests/test_adapters.py`
    2. Test: LM Studio allowlist filtering, TTL in payload, auth headers, mid-chain TTL extension
    3. Mock `requests.post`
  - **Files**: `tests/test_adapters.py`
  - **Done when**: LM Studio path through OAI adapter fully tested
  - **Verify**: `pytest tests/test_adapters.py -v -k "lm_studio" && echo PASS`
  - **Commit**: `test(adapters): add OAI-compat adapter LM Studio tests`

- [ ] 3.7 [VERIFY] Quality checkpoint: ruff + pytest
  - **Do**: Run lint and tests
  - **Verify**: `ruff check . && pytest tests/ -v && echo PASS`
  - **Done when**: No lint errors, all tests pass
  - **Commit**: `chore(tests): pass quality checkpoint` (if fixes needed)

- [ ] 3.8 Test OAI-compat adapter (text-gen-webui path)
  - **Do**:
    1. Add tests to `tests/test_adapters.py`
    2. Test: text-gen-webui allowlist, model lifecycle sequence (check -> load -> generate -> unload), admin key headers, unload skipped mid-chain, unload failure non-fatal
    3. Mock all `requests` calls
  - **Files**: `tests/test_adapters.py`
  - **Done when**: text-gen-webui lifecycle fully tested including error paths
  - **Verify**: `pytest tests/test_adapters.py -v -k "text_gen" && echo PASS`
  - **Commit**: `test(adapters): add OAI-compat adapter text-gen-webui lifecycle tests`
  - _Requirements: FR-16, FR-19_

- [ ] 3.9 Test _raise_on_error helper
  - **Do**:
    1. Add tests to `tests/test_adapters.py`
    2. Test: raises on 4xx with message containing backend name, URL, status; raises on 5xx; truncates long response bodies; passes on 200
  - **Files**: `tests/test_adapters.py`
  - **Done when**: Error helper tested with various status codes
  - **Verify**: `pytest tests/test_adapters.py -v -k "raise_on_error" && echo PASS`
  - **Commit**: `test(adapters): add _raise_on_error tests`
  - _Requirements: NFR-2_

- [ ] 3.10 [VERIFY] Quality checkpoint: ruff + pytest
  - **Do**: Run lint and tests
  - **Verify**: `ruff check . && pytest tests/ -v && echo PASS`
  - **Done when**: No lint errors, all tests pass
  - **Commit**: `chore(tests): pass quality checkpoint` (if fixes needed)

- [ ] 3.11 Test graph introspection
  - **Do**:
    1. Create `tests/test_graph.py`
    2. Test: find downstream nodes with connections, no downstream, multiple downstream, generation node detection, non-generation downstream
    3. Use sample PROMPT dicts as test data
  - **Files**: `tests/test_graph.py`
  - **Done when**: All graph introspection paths tested
  - **Verify**: `pytest tests/test_graph.py -v && echo PASS`
  - **Commit**: `test(graph): add graph introspection unit tests`
  - _Requirements: FR-9_

- [ ] 3.12 [P] Test options nodes (sentinel pattern)
  - **Do**:
    1. Create `tests/test_options.py`
    2. Test Ollama Core: sentinel values excluded, non-sentinel included, chaining from options_in, options_in key collision (Core wins)
  - **Files**: `tests/test_options.py`
  - **Done when**: Sentinel pattern fully tested
  - **Verify**: `pytest tests/test_options.py -v -k "core" && echo PASS`
  - **Commit**: `test(options): add Ollama Core Options sentinel pattern tests`
  - _Requirements: AC-8.1, AC-8.2_

- [ ] 3.13 [P] Test options nodes (toggle pattern)
  - **Do**:
    1. Add tests to `tests/test_options.py`
    2. Test Ollama Extra: toggle ON includes param, toggle OFF excludes, mirostat COMBO, chaining
    3. Test LM Studio: toggle pattern, all 9 params
    4. Test text-gen-webui: toggle pattern, all 12 params
  - **Files**: `tests/test_options.py`
  - **Done when**: Toggle pattern tested for all three nodes
  - **Verify**: `pytest tests/test_options.py -v -k "toggle or extra or lm_studio or text_gen" && echo PASS`
  - **Commit**: `test(options): add toggle-based Options node tests`
  - _Requirements: AC-8.5, AC-9.1, AC-10.1_

- [ ] 3.14 [VERIFY] Quality checkpoint: ruff + pytest
  - **Do**: Run lint and all tests
  - **Verify**: `ruff check . && pytest tests/ -v && echo PASS`
  - **Done when**: No lint errors, all tests pass
  - **Commit**: `chore(tests): pass quality checkpoint` (if fixes needed)

- [ ] 3.15 Test generation node message building and inline options
  - **Do**:
    1. Create `tests/test_generation.py`
    2. Test `_build_messages`: with system prompt, without system prompt
    3. Test LLMGenerate inline options: sentinel exclusion (seed=-1 excluded, temperature=0.7 included)
    4. Test LLMGenerateAdvanced meta precedence: explicit provider wins over meta, explicit options wins over meta
  - **Files**: `tests/test_generation.py`
  - **Done when**: Message building and option resolution tested
  - **Verify**: `pytest tests/test_generation.py -v && echo PASS`
  - **Commit**: `test(generation): add generation node unit tests`
  - _Requirements: AC-5.1, AC-6.8_

- [ ] 3.16 [VERIFY] Quality checkpoint: ruff + pytest (all tests)
  - **Do**: Run lint and full test suite
  - **Verify**: `ruff check . && pytest tests/ -v && echo PASS`
  - **Done when**: No lint errors, all tests pass
  - **Commit**: `chore(tests): pass final testing quality checkpoint` (if fixes needed)

---

## Phase 4: Quality Gates

- [ ] V4 [VERIFY] Full local CI: ruff check && pytest
  - **Do**: Run complete local quality suite
  - **Verify**: `ruff check . && pytest tests/ -v && echo V4_PASS`
  - **Done when**: All lint and tests pass
  - **Commit**: `chore: pass local CI` (if fixes needed)

- [ ] 4.1 Create PR and verify CI
  - **Do**:
    1. Verify current branch is feature branch: `git branch --show-current`
    2. If on default branch, STOP and alert user
    3. Push branch: `git push -u origin feat/comfyui-llm-bikeshed`
    4. Create PR using gh CLI with summary of all changes
  - **Verify**: `gh pr checks` shows all green (or no CI configured)
  - **Done when**: PR created, CI passing
  - **Commit**: None (PR creation, not code change)

- [ ] V5 [VERIFY] CI pipeline passes
  - **Do**: Verify GitHub Actions/CI passes after push
  - **Verify**: `gh pr checks` shows all green (if CI exists)
  - **Done when**: CI pipeline passes or no CI configured
  - **Commit**: None

- [ ] V6 [VERIFY] AC checklist
  - **Do**: Programmatically verify each acceptance criterion:
    1. AC-1.x: LM Studio Provider node exists with correct widgets
    2. AC-2.x: text-gen-webui Provider node exists with correct widgets
    3. AC-3.x: Ollama Provider node exists with correct widgets
    4. AC-4.x: No API key widgets on any provider node
    5. AC-5.x: Basic Generation node has all required inputs/outputs
    6. AC-6.x: Advanced Generation node has all required inputs/outputs
    7. AC-7.x: Graph introspection functions exist
    8. AC-8.x: Ollama Core/Extra Options nodes exist with correct params
    9. AC-9.x: LM Studio Options node exists
    10. AC-10.x: text-gen-webui Options node exists
    11. AC-11.x: Preset Loader node exists
    12. AC-12.x: Config system works with merge-on-load
    13. AC-13.x: Frontend JS has model dropdown logic
    14. AC-14.x: Load Text File node exists
  - **Verify**: `python -c "
from nodes.providers import LLMProviderOllama, LLMProviderLMStudio, LLMProviderTextGenWebUI
from nodes.generation import LLMGenerate, LLMGenerateAdvanced
from nodes.options_ollama import LLMOptionsOllamaCore, LLMOptionsOllamaExtra
from nodes.options_lm_studio import LLMOptionsLMStudio
from nodes.options_text_gen_webui import LLMOptionsTextGenWebUI
from nodes.utils import LLMPresetLoader
from config import get_config
from adapters import get_adapter
from graph.introspection import has_downstream_gen_node
# AC-4: no api_key in any provider INPUT_TYPES
for P in [LLMProviderOllama, LLMProviderLMStudio, LLMProviderTextGenWebUI]:
    it = P.INPUT_TYPES()
    assert 'api_key' not in it.get('required',{}), f'{P} has api_key widget'
    assert 'api_key' not in it.get('optional',{}), f'{P} has api_key widget'
print('ALL AC CHECKS PASS')
"`
  - **Done when**: All acceptance criteria verified
  - **Commit**: None

---

## Phase 5: PR Lifecycle

- [ ] 5.1 Monitor CI and fix failures
  - **Do**:
    1. Check PR status: `gh pr checks`
    2. If failures, read logs, fix locally, push
    3. Re-verify: `gh pr checks`
  - **Verify**: `gh pr checks` all green
  - **Done when**: CI passes consistently
  - **Commit**: `fix: address CI failures` (if needed)

- [ ] 5.2 Address review comments
  - **Do**:
    1. Check for PR review comments: `gh pr view --comments`
    2. Address each comment with code changes
    3. Push fixes and re-verify CI
  - **Verify**: `gh pr checks` all green after fixes
  - **Done when**: All review comments addressed
  - **Commit**: `fix: address PR review feedback` (if needed)

- [ ] 5.3 Final validation
  - **Do**:
    1. Verify zero test regressions: `pytest tests/ -v`
    2. Verify lint clean: `ruff check .`
    3. Verify all 11 node classes importable
    4. Verify config system functional
    5. Verify JS file present and complete
  - **Verify**: `ruff check . && pytest tests/ -v && python -c "from config import get_config; get_config(); print('FINAL PASS')"`
  - **Done when**: All quality criteria met, PR ready for merge
  - **Commit**: None (verification only)

---

## Notes

- **POC shortcuts taken**: PromptServer endpoints use try/except guard for `PromptServer` import (allows standalone testing without ComfyUI). Load Text File node uses try/except for `folder_paths` import.
- **Production TODOs**: Toast notifications for unsupported params (JS side), actual ComfyUI integration testing, empirical testing of unknown param handling on LM Studio/text-gen-webui.
- **Total tasks**: 53
- **Phase distribution**: Phase 1 = 30 tasks (57%), Phase 2 = 9 tasks (17%), Phase 3 = 12 tasks (23%), Phase 4-5 = 8 tasks (15%)
