import { app } from "../../scripts/app.js";

const PROVIDER_CONFIG = {
  LLMProviderOAICompat: {
    endpoint: "/llm-bikeshed/models/oai-compat",
    /** When true, show read-only detected_backend from the same response as models. */
    showBackendLabel: true,
    defaultUrl: "http://localhost:1234",
    /** Textgen provider widget; absent on OAI Compatible. */
    manageMemoryWidget: null,
  },
  LLMProviderTextGenWebUI: {
    endpoint: "/llm-bikeshed/models/textgen",
    showBackendLabel: true,
    defaultUrl: "http://localhost:5000",
    manageMemoryWidget: "manage_model_memory",
  },
};

/** Debounce first auto-fetch so duplicate nodeCreated does not double-hit the backend. */
const INITIAL_FETCH_DEBOUNCE_MS = 600;

/** Debounce URL edits before re-fetching models (callback + DOM listeners). */
const URL_REFETCH_DEBOUNCE_MS = 500;

/** Debounce model COMBO changes before calling ensure-loaded. */
const MODEL_LOAD_DEBOUNCE_MS = 400;

/**
 * Display-only text widgets — ComfyUI frontend ~1.39+ honors `disabled` and
 * `read_only` on STRING/text widgets (Vue node renderer). Older builds need
 * DOM enforcement (see attachReadOnlyWidget).
 */
const READ_ONLY_WIDGET_OPTIONS = {
  serialize: false,
  disabled: true,
  read_only: true,
};

const PLACEHOLDER_VALUES = new Set(["(refresh to load)", "(no models found)"]);

/** Backends where explicit load before chat is supported. */
const LOAD_ON_SELECT_BACKENDS = new Set(["text_gen_webui", "lm_studio", "llamacpp"]);

/**
 * Fetch model list from a backend endpoint.
 * @param {string} endpoint - The PromptServer route path.
 * @param {string} url - The backend base URL to query.
 * @returns {Promise<{ models: string[], backend: string | null, loadedModel: string | null | undefined }>}
 */
async function fetchModels(endpoint, url) {
  try {
    const response = await app.api.fetchApi(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    if (!response.ok) {
      return { models: [], backend: null, loadedModel: undefined };
    }
    const data = await response.json();
    let loadedModel = undefined;
    if (Object.prototype.hasOwnProperty.call(data, "loaded_model")) {
      loadedModel =
        data.loaded_model === null || data.loaded_model === undefined
          ? null
          : String(data.loaded_model);
    }
    return {
      models: data.models || [],
      backend: data.backend !== undefined ? data.backend : null,
      loadedModel,
    };
  } catch {
    return { models: [], backend: null, loadedModel: undefined };
  }
}

/**
 * Ask the pack backend to load the selected model (Textgen / LM Studio / llama.cpp).
 * @returns {Promise<{ ok: boolean, error?: string }>}
 */
async function ensureModelLoaded(url, model, backend) {
  if (!url || !model || PLACEHOLDER_VALUES.has(model)) {
    return { ok: false, error: "invalid model" };
  }
  try {
    const response = await app.api.fetchApi("/llm-bikeshed/models/ensure-loaded", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, model, backend }),
    });
    const data = await response.json();
    return { ok: Boolean(data.ok), error: data.error };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

/** Human-readable backend family (never leaves UI stuck on “detecting…”). */
function formatBackendName(backend) {
  if (backend === null || backend === undefined || backend === "") {
    return "Unknown";
  }
  return BACKEND_LABELS[backend] || String(backend);
}

/** Read-only line for the model currently loaded in VRAM (when known). */
function formatLoadedModelStatus(loadedModel) {
  if (loadedModel === undefined) {
    return "—";
  }
  if (!loadedModel) {
    return "None loaded";
  }
  return loadedModel;
}

function isRealModelName(value) {
  return Boolean(value) && !PLACEHOLDER_VALUES.has(String(value));
}

/**
 * Update a COMBO widget's options list, preserving the user's current selection.
 * @param {object} widget - The ComfyUI COMBO widget.
 * @param {string[]} models - New model list from the backend.
 * @param {string|null|undefined} savedValue - Workflow-restored value to prefer when still valid.
 */
function updateModelWidget(widget, models, savedValue) {
  const options = [...models];
  const current = widget.value;

  const pickPreferred = () => {
    if (isRealModelName(current) && options.includes(current)) {
      return current;
    }
    if (
      savedValue !== undefined &&
      isRealModelName(savedValue) &&
      options.includes(savedValue)
    ) {
      return savedValue;
    }
    if (isRealModelName(current) && !options.includes(current) && models.length === 0) {
      options.push(current);
      return current;
    }
    return options[0] ?? "(no models found)";
  };

  if (options.length === 0) {
    options.push("(no models found)");
  }

  widget.options.values = options;
  const next = pickPreferred();
  if (widget.value !== next) {
    widget.value = next;
  }
  if (typeof widget.callback === "function") {
    widget.callback(widget.value);
  }
}

/** Backend display names for the indicator widget. */
const BACKEND_LABELS = {
  lm_studio: "LM Studio",
  text_gen_webui: "Textgen",
  openai: "OpenAI",
  llamacpp: "llama.cpp",
  ollama: "Ollama",
  generic: "Generic",
  unknown: "Unknown",
};

function markNodeDirty(node) {
  node.setDirtyCanvas(true, true);
  if (app.graph) {
    app.graph.setDirtyCanvas(true);
  }
}

/** Current URL from the widget (callback `value` arg can be stale with multiple providers). */
function getWidgetUrl(urlWidget, defaultUrl) {
  const raw = urlWidget?.value;
  if (raw === null || raw === undefined || String(raw).trim() === "") {
    return defaultUrl;
  }
  return String(raw);
}

function shouldLoadOnSelect(node, config, backend) {
  if (!LOAD_ON_SELECT_BACKENDS.has(backend)) {
    return false;
  }
  const memName = config.manageMemoryWidget;
  if (!memName) {
    return backend === "text_gen_webui";
  }
  const memWidget = node.widgets?.find((w) => w.name === memName);
  return memWidget ? Boolean(memWidget.value) : true;
}

/**
 * DOM listeners on the STRING input — backup when `urlWidget.callback` does not fire
 * (observed with multiple provider nodes on one graph, ComfyUI frontend 1.39–1.45).
 */
function attachUrlInputListeners(urlWidget, onChange) {
  if (!urlWidget || urlWidget.__llmBikeshedUrlListenersAttached) {
    return;
  }

  const tryAttach = (attempt = 0) => {
    const inputEl = urlWidget.inputEl;
    if (!inputEl) {
      if (attempt < 20) {
        requestAnimationFrame(() => tryAttach(attempt + 1));
      }
      return;
    }
    if (urlWidget.__llmBikeshedUrlListenersAttached) {
      return;
    }
    urlWidget.__llmBikeshedUrlListenersAttached = true;
    const handler = () => onChange();
    inputEl.addEventListener("input", handler);
    inputEl.addEventListener("change", handler);
  };

  tryAttach();
}

/** Force read-only on status widgets when Vue options are ignored (older ComfyUI). */
function attachReadOnlyWidget(widget) {
  if (!widget || widget.__llmBikeshedReadOnlyAttached) {
    return;
  }

  const apply = () => {
    const el = widget.inputEl;
    if (!el) {
      return false;
    }
    el.readOnly = true;
    el.disabled = true;
    el.tabIndex = -1;
    el.setAttribute("aria-readonly", "true");
    el.style.pointerEvents = "none";
    el.style.cursor = "default";
    return true;
  };

  const tryAttach = (attempt = 0) => {
    if (apply()) {
      widget.__llmBikeshedReadOnlyAttached = true;
      return;
    }
    if (attempt < 25) {
      requestAnimationFrame(() => tryAttach(attempt + 1));
    }
  };

  tryAttach();
}

function applyProviderStatus(node, backendWidget, loadedWidget, backend, loadedModel) {
  if (backendWidget) {
    backendWidget.value = formatBackendName(backend);
    attachReadOnlyWidget(backendWidget);
  }
  if (loadedWidget) {
    loadedWidget.value = formatLoadedModelStatus(loadedModel);
    attachReadOnlyWidget(loadedWidget);
  }
  markNodeDirty(node);
}

app.registerExtension({
  name: "llm-bikeshed.model-dropdown",

  nodeCreated(node) {
    const config = PROVIDER_CONFIG[node.comfyClass];
    if (!config) {
      return;
    }

    const { endpoint, defaultUrl, showBackendLabel } = config;

    const modelWidget = node.widgets?.find((w) => w.name === "model");
    const urlWidget = node.widgets?.find((w) => w.name === "url");

    if (!modelWidget) {
      return;
    }

    let backendWidget = null;
    let loadedModelWidget = null;
    if (showBackendLabel) {
      backendWidget = node.addWidget(
        "text",
        "detected_backend",
        "detecting…",
        () => {},
        READ_ONLY_WIDGET_OPTIONS,
      );
      loadedModelWidget = node.addWidget(
        "text",
        "loaded_model_status",
        "—",
        () => {},
        READ_ONLY_WIDGET_OPTIONS,
      );
      attachReadOnlyWidget(backendWidget);
      attachReadOnlyWidget(loadedModelWidget);
    }

    let lastBackend = null;
    let modelLoadTimer = null;

    const refreshLoadedStatus = (url, backend) => {
      fetchModels(endpoint, url).then(({ loadedModel }) => {
        if (loadedModelWidget) {
          loadedModelWidget.value = formatLoadedModelStatus(loadedModel);
          attachReadOnlyWidget(loadedModelWidget);
        }
        markNodeDirty(node);
      });
    };

    const scheduleModelLoad = (url, model, backend) => {
      if (!shouldLoadOnSelect(node, config, backend) || !isRealModelName(model)) {
        return;
      }
      clearTimeout(modelLoadTimer);
      modelLoadTimer = setTimeout(async () => {
        const { ok } = await ensureModelLoaded(url, model, backend);
        if (ok) {
          refreshLoadedStatus(url, backend);
        }
      }, MODEL_LOAD_DEBOUNCE_MS);
    };

    /** @param {unknown} [initialSavedModel] if set, restore COMBO to this after fetch */
    const runFetch = (url, initialSavedModel) => {
      fetchModels(endpoint, url).then(({ models, backend, loadedModel }) => {
        lastBackend = backend;
        const saved =
          initialSavedModel !== undefined ? initialSavedModel : modelWidget.value;
        updateModelWidget(modelWidget, models, saved);
        applyProviderStatus(node, backendWidget, loadedModelWidget, backend, loadedModel);
      });
    };

    let initialFetchTimer = null;
    const scheduleInitialFetch = () => {
      if (initialFetchTimer !== null) {
        clearTimeout(initialFetchTimer);
      }
      initialFetchTimer = setTimeout(() => {
        initialFetchTimer = null;
        runFetch(getWidgetUrl(urlWidget, defaultUrl), modelWidget.value);
      }, INITIAL_FETCH_DEBOUNCE_MS);
    };

    scheduleInitialFetch();
    node.__llmBikeshedScheduleProviderFetch = scheduleInitialFetch;

    let urlRefetchTimer = null;

    const beginUrlRefetchUi = () => {
      if (showBackendLabel && backendWidget) {
        backendWidget.value = "detecting…";
      }
      if (showBackendLabel && loadedModelWidget) {
        loadedModelWidget.value = "—";
      }
      markNodeDirty(node);
    };

    const scheduleUrlRefetch = () => {
      beginUrlRefetchUi();
      clearTimeout(urlRefetchTimer);
      urlRefetchTimer = setTimeout(() => {
        runFetch(getWidgetUrl(urlWidget, defaultUrl), undefined);
      }, URL_REFETCH_DEBOUNCE_MS);
    };

    if (urlWidget) {
      const origCallback = urlWidget.callback;
      urlWidget.callback = function (_value) {
        if (origCallback) {
          origCallback.call(this, _value);
        }
        scheduleUrlRefetch();
      };
      attachUrlInputListeners(urlWidget, scheduleUrlRefetch);
    }

    const origModelCallback = modelWidget.callback;
    modelWidget.callback = function (value) {
      if (origModelCallback) {
        origModelCallback.call(this, value);
      }
      markNodeDirty(node);
      const url = getWidgetUrl(urlWidget, defaultUrl);
      scheduleModelLoad(url, value, lastBackend);
    };

    node.addWidget("button", "Refresh Models", null, () => {
      const url = getWidgetUrl(urlWidget, defaultUrl);
      beginUrlRefetchUi();
      runFetch(url, modelWidget.value);
    });
  },

  loadedGraphNode(node) {
    if (!PROVIDER_CONFIG[node.comfyClass]) {
      return;
    }
    node.__llmBikeshedScheduleProviderFetch?.();
  },
});
