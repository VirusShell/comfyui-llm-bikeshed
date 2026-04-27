import { app } from "../../scripts/app.js";

const PROVIDER_CONFIG = {
  LLMProviderLMStudio: {
    endpoint: "/llm-bikeshed/models/lm-studio",
    defaultUrl: "http://localhost:1234",
  },
  LLMProviderOpenAI: {
    endpoint: "/llm-bikeshed/models/openai",
    defaultUrl: "https://api.openai.com",
  },
  LLMProviderOllama: {
    endpoint: "/llm-bikeshed/models/ollama",
    defaultUrl: "http://localhost:11434",
  },
  LLMProviderTextGenWebUI: {
    endpoint: "/llm-bikeshed/models/text-gen-webui",
    defaultUrl: "http://localhost:5000",
  },
};

/**
 * Fetch model list from a backend endpoint.
 * @param {string} endpoint - The PromptServer route path.
 * @param {string} url - The backend base URL to query.
 * @returns {Promise<string[]>} Array of model ID strings.
 */
async function fetchModels(endpoint, url) {
  try {
    const response = await app.api.fetchApi(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    if (!response.ok) {
      return [];
    }
    const data = await response.json();
    return data.models || [];
  } catch {
    return [];
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

  // Keep the saved value in the list so it isn't lost — but not placeholders
  const isSavedReal = savedValue && !PLACEHOLDER_VALUES.has(savedValue);
  if (isSavedReal && !options.includes(savedValue)) {
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

app.registerExtension({
  name: "llm-bikeshed.model-dropdown",

  nodeCreated(node) {
    const config = PROVIDER_CONFIG[node.comfyClass];
    if (!config) {
      return;
    }

    const { endpoint, defaultUrl } = config;

    // Find the model and url widgets
    const modelWidget = node.widgets?.find((w) => w.name === "model");
    const urlWidget = node.widgets?.find((w) => w.name === "url");

    if (!modelWidget) {
      return;
    }

    // Store saved model value before we overwrite options
    const savedModel = modelWidget.value || null;

    // Initial fetch using current URL or default
    const currentUrl = urlWidget?.value || defaultUrl;
    fetchModels(endpoint, currentUrl).then((models) => {
      updateModelWidget(modelWidget, models, savedModel);
    });

    // Add refresh button widget
    node.addWidget("button", "Refresh Models", null, () => {
      const url = urlWidget?.value || defaultUrl;
      fetchModels(endpoint, url).then((models) => {
        updateModelWidget(modelWidget, models, modelWidget.value);
        node.setDirtyCanvas(true);
      });
    });
  },
});
