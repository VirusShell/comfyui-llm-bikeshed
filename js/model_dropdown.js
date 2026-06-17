import { app } from "../../scripts/app.js";

const PROVIDER_CONFIG = {
  LLMProviderOAICompat: {
    endpoint: "/llm-bikeshed/models/oai-compat",
    /** When true, show read-only detected_backend from the same response as models. */
    showBackendLabel: true,
    defaultUrl: "http://localhost:1234",
  },
  LLMProviderTextGenWebUI: {
    endpoint: "/llm-bikeshed/models/textgen",
    showBackendLabel: true,
    defaultUrl: "http://localhost:5000",
  },
};

/** Debounce first auto-fetch so duplicate nodeCreated does not double-hit the backend. */
const INITIAL_FETCH_DEBOUNCE_MS = 600;

/** Debounce URL edits before re-fetching models (callback + DOM listeners). */
const URL_REFETCH_DEBOUNCE_MS = 500;

/**
 * Display-only text widgets — ComfyUI frontend ~1.39+ honors `disabled` and
 * `read_only` on STRING/text widgets (Vue node renderer).
 */
const READ_ONLY_WIDGET_OPTIONS = {
  serialize: false,
  disabled: true,
  read_only: true,
};

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

/** Human-readable backend family (never leaves UI stuck on “detecting…”). */
function formatBackendName(backend) {
  if (backend === null || backend === undefined || backend === "") {
    return "Unknown";
  }
  return BACKEND_LABELS[backend] || String(backend);
}

/** Read-only line for currently loaded model (Textgen); other backends N/A. */
function formatLoadedModelStatus(backend, loadedModel) {
  if (backend !== "text_gen_webui") {
    return "—";
  }
  if (loadedModel === undefined) {
    return "—";
  }
  if (!loadedModel) {
    return "None loaded";
  }
  return loadedModel;
}

/**
 * Update a COMBO widget's options list, preserving the saved/current value.
 * @param {object} widget - The ComfyUI COMBO widget.
 * @param {string[]} models - New model list from the backend.
 * @param {string|null} savedValue - Previously saved model value to preserve.
 */
const PLACEHOLDER_VALUES = new Set(["(refresh to load)", "(no models found)"]);

function updateModelWidget(widget, models, savedValue) {
  const options = [...models];

  // Keep the saved value in the list so it isn't lost — but not placeholders.
  // If the backend returned real models, do not inject a stale workflow value
  // (e.g. an LM Studio id when the URL now points at Textgen).
  const isSavedReal = savedValue && !PLACEHOLDER_VALUES.has(savedValue);
  const backendReturnedModels = models.length > 0;
  if (isSavedReal && !options.includes(savedValue) && !backendReturnedModels) {
    options.push(savedValue);
  }

  // Fallback: ensure at least one option exists
  if (options.length === 0) {
    options.push("(no models found)");
  }

  widget.options.values = options;

  // Restore saved value if it's a real model, otherwise use first option
  if (isSavedReal && options.includes(savedValue)) {
    widget.value = savedValue;
  } else if (!widget.value || !options.includes(widget.value)) {
    widget.value = options[0];
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

function applyProviderStatus(node, backendWidget, loadedWidget, backend, loadedModel) {
  if (backendWidget) {
    backendWidget.value = formatBackendName(backend);
  }
  if (loadedWidget) {
    loadedWidget.value = formatLoadedModelStatus(backend, loadedModel);
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

    // Find the model and url widgets
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
    }

    /** @param {unknown} [initialSavedModel] if set, restore COMBO to this after fetch */
    const runFetch = (url, initialSavedModel) => {
      fetchModels(endpoint, url).then(({ models, backend, loadedModel }) => {
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

    // Defer + debounce fetch until after workflow/widget restore so COMBO keeps saved model id.
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

    // Re-fetch models and re-detect on URL change (callback + DOM backup).
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

    // Add refresh button widget
    node.addWidget("button", "Refresh Models", null, () => {
      const url = getWidgetUrl(urlWidget, defaultUrl);
      beginUrlRefetchUi();
      runFetch(url, undefined);
    });
  },

  loadedGraphNode(node) {
    if (!PROVIDER_CONFIG[node.comfyClass]) {
      return;
    }
    // Widget values are restored after nodeCreated; refetch all provider nodes on load.
    node.__llmBikeshedScheduleProviderFetch?.();
  },
});
