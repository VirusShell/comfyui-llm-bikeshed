import { app } from "../../scripts/app.js";

const PROVIDER_CONFIG = {
  LLMProviderOAICompat: {
    endpoint: "/llm-bikeshed/models/oai-compat",
    /** When true, show read-only detected_backend from the same response as models. */
    showBackendLabel: true,
    defaultUrl: "http://localhost:1234",
  },
  LLMProviderOllama: {
    endpoint: "/llm-bikeshed/models/ollama",
    defaultUrl: "http://localhost:11434",
  },
};

/**
 * Fetch model list from a backend endpoint.
 * @param {string} endpoint - The PromptServer route path.
 * @param {string} url - The backend base URL to query.
 * @returns {Promise<{ models: string[], backend: string | null }>}
 */
async function fetchModels(endpoint, url) {
  try {
    const response = await app.api.fetchApi(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    if (!response.ok) {
      return { models: [], backend: null };
    }
    const data = await response.json();
    return {
      models: data.models || [],
      backend: data.backend !== undefined ? data.backend : null,
    };
  } catch {
    return { models: [], backend: null };
  }
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

    // Add detected backend indicator (OAI-compat only)
    let backendWidget = null;
    if (showBackendLabel) {
      backendWidget = node.addWidget(
        "text",
        "detected_backend",
        "detecting...",
        () => {},
        { serialize: false },
      );
    }

    // Defer fetch until after workflow/widget restore so COMBO keeps saved model id.
    queueMicrotask(() => {
      const savedModel = modelWidget.value || null;
      const currentUrl = urlWidget?.value || defaultUrl;

      fetchModels(endpoint, currentUrl).then(({ models, backend }) => {
        updateModelWidget(modelWidget, models, savedModel);
        if (showBackendLabel && backendWidget && backend != null) {
          backendWidget.value = BACKEND_LABELS[backend] || backend;
        }
        node.setDirtyCanvas(true);
      });
    });

    // Debounce timer for URL change detection
    let detectTimer = null;

    // Re-fetch models and re-detect on URL change
    if (urlWidget) {
      const origCallback = urlWidget.callback;
      urlWidget.callback = function (value) {
        if (origCallback) {
          origCallback.call(this, value);
        }
        clearTimeout(detectTimer);
        if (showBackendLabel && backendWidget) {
          backendWidget.value = "detecting...";
        }
        detectTimer = setTimeout(() => {
          fetchModels(endpoint, value).then(({ models, backend }) => {
            updateModelWidget(modelWidget, models, modelWidget.value);
            if (showBackendLabel && backendWidget && backend != null) {
              backendWidget.value = BACKEND_LABELS[backend] || backend;
            }
            node.setDirtyCanvas(true);
          });
        }, 500);
      };
    }

    // Add refresh button widget
    node.addWidget("button", "Refresh Models", null, () => {
      const url = urlWidget?.value || defaultUrl;
      if (showBackendLabel && backendWidget) {
        backendWidget.value = "detecting...";
      }
      fetchModels(endpoint, url).then(({ models, backend }) => {
        updateModelWidget(modelWidget, models, modelWidget.value);
        if (showBackendLabel && backendWidget && backend != null) {
          backendWidget.value = BACKEND_LABELS[backend] || backend;
        }
        node.setDirtyCanvas(true);
      });
    });
  },
});
