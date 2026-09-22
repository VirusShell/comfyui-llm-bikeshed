import { app } from "../../scripts/app.js";

/**
 * LLM Connection face (v4).
 *
 * Q1 status chrome: labeled disabled text widgets (serialize:false) + DOM lock —
 * same pattern as model_dropdown.js (pack already uses it; DomWidget/HTML not present).
 * Q2 model widget: one Python name `model` (COMBO). Catalog modes keep COMBO;
 * string-profile modes (llama.cpp / generic) switch the same widget to free-text.
 */

const ENDPOINT = "/llm-bikeshed/models/connection";
const DEFAULT_URL = "http://localhost:1234";

const INITIAL_FETCH_DEBOUNCE_MS = 600;
const URL_REFETCH_DEBOUNCE_MS = 500;
const MODEL_LOAD_DEBOUNCE_MS = 400;

const READ_ONLY_WIDGET_OPTIONS = {
  serialize: false,
  disabled: true,
  read_only: true,
};

const PLACEHOLDER_VALUES = new Set(["(refresh to load)", "(no models found)"]);

const FACE_WIDGETS_TEXTGEN = new Set(["manage_model_memory", "ensure_load_on_select"]);
const FACE_WIDGETS_LM = new Set(["ttl", "context_length", "ensure_load_on_select"]);
const FACE_WIDGETS_ALL = new Set([
  "manage_model_memory",
  "ttl",
  "context_length",
  "ensure_load_on_select",
]);

const BACKEND_LABELS = {
  lm_studio: "LM Studio",
  text_gen_webui: "Textgen",
  openai: "OpenAI",
  llamacpp: "llama.cpp",
  ollama: "Ollama",
  generic: "Generic OAI",
  unknown: "Unknown",
};

const HOST_MODE_AUTO = "Auto (detect)";

function formatBackendName(backend) {
  if (backend === null || backend === undefined || backend === "") {
    return "Unknown";
  }
  return BACKEND_LABELS[backend] || String(backend);
}

function isRealModelName(value) {
  return Boolean(value) && !PLACEHOLDER_VALUES.has(String(value));
}

function markNodeDirty(node) {
  node.setDirtyCanvas(true, true);
  if (app.graph) {
    app.graph.setDirtyCanvas(true);
  }
}

function getWidgetUrl(urlWidget) {
  const raw = urlWidget?.value;
  if (raw === null || raw === undefined || String(raw).trim() === "") {
    return DEFAULT_URL;
  }
  return String(raw);
}

function getHostMode(node) {
  const w = node.widgets?.find((x) => x.name === "host_mode");
  return w?.value || HOST_MODE_AUTO;
}

/** Force read-only when Vue options are ignored (older ComfyUI). */
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

function setWidgetVisible(widget, visible) {
  if (!widget) {
    return;
  }
  widget.hidden = !visible;
  if (widget.element) {
    widget.element.style.display = visible ? "" : "none";
  }
  // Comfy DOM input row
  const el = widget.inputEl || widget.buttonElement;
  if (el?.closest) {
    const row = el.closest(".widget") || el.parentElement;
    if (row && row.style) {
      row.style.display = visible ? "" : "none";
    }
  }
}

function applyFaceVisibility(node, face) {
  const showTextgen = face === "text_gen_webui";
  const showLm = face === "lm_studio";
  for (const w of node.widgets || []) {
    if (!FACE_WIDGETS_ALL.has(w.name)) {
      continue;
    }
    if (FACE_WIDGETS_TEXTGEN.has(w.name) && FACE_WIDGETS_LM.has(w.name)) {
      setWidgetVisible(w, showTextgen || showLm);
    } else if (FACE_WIDGETS_TEXTGEN.has(w.name)) {
      setWidgetVisible(w, showTextgen);
    } else if (FACE_WIDGETS_LM.has(w.name)) {
      setWidgetVisible(w, showLm);
    }
  }
  markNodeDirty(node);
}

/**
 * Q2: catalog → COMBO; string profile → free-text on the same `model` widget.
 * Stores original combo type so we can restore when mode flips back.
 */
function applyModelWidgetMode(modelWidget, catalog) {
  if (!modelWidget) {
    return;
  }
  if (modelWidget.__llmConnOrigType === undefined) {
    modelWidget.__llmConnOrigType = modelWidget.type;
    modelWidget.__llmConnOrigOptions = modelWidget.options
      ? { ...modelWidget.options, values: [...(modelWidget.options.values || [])] }
      : { values: [] };
  }
  if (catalog) {
    modelWidget.type = modelWidget.__llmConnOrigType || "combo";
    if (modelWidget.options && modelWidget.__llmConnOrigOptions) {
      modelWidget.options.values =
        modelWidget.options.values?.length
          ? modelWidget.options.values
          : modelWidget.__llmConnOrigOptions.values;
    }
  } else {
    // Free-text presentation; Python still receives model: str.
    modelWidget.type = "text";
    if (!isRealModelName(modelWidget.value)) {
      modelWidget.value = "";
    }
  }
}

function updateModelCombo(widget, models, savedValue) {
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

  if (!widget.options) {
    widget.options = {};
  }
  widget.options.values = options;
  const next = pickPreferred();
  if (widget.value !== next) {
    widget.value = next;
  }
}

function vramPolicyLine(face, node) {
  if (face === "text_gen_webui") {
    const mem = node.widgets?.find((w) => w.name === "manage_model_memory");
    const on = mem ? Boolean(mem.value) : true;
    if (on) {
      return "VRAM: load before gen, unload after chain";
    }
    return "VRAM: pack will not load/unload (manage memory off)";
  }
  if (face === "lm_studio") {
    const ttlW = node.widgets?.find((w) => w.name === "ttl");
    const ttl = ttlW != null ? ttlW.value : 30;
    return `VRAM: TTL ${ttl}s (LM Studio)`;
  }
  return "VRAM: pack will not load (host has no pack load path)";
}

function loadedStatusLine(catalog, loadedModel, face) {
  if (face === "openai" || (!catalog && face !== "lm_studio" && face !== "text_gen_webui")) {
    if (loadedModel === undefined || loadedModel === null || loadedModel === "") {
      return face === "openai" ? "loaded: n/a" : "loaded: n/a";
    }
  }
  if (loadedModel === undefined) {
    return "loaded: —";
  }
  if (!loadedModel) {
    return "loaded: (none)";
  }
  return `loaded: ${loadedModel}`;
}

async function fetchConnection(url, hostMode) {
  try {
    const response = await app.api.fetchApi(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, host_mode: hostMode }),
    });
    if (!response.ok) {
      return null;
    }
    return await response.json();
  } catch {
    return null;
  }
}

async function ensureModelLoaded(url, model, backend) {
  if (!url || !model || PLACEHOLDER_VALUES.has(model)) {
    return { ok: false };
  }
  try {
    const response = await app.api.fetchApi("/llm-bikeshed/models/ensure-loaded", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, model, backend }),
    });
    const data = await response.json();
    return { ok: Boolean(data.ok) };
  } catch {
    return { ok: false };
  }
}

function shouldEnsureLoadOnSelect(node, face) {
  if (face !== "text_gen_webui" && face !== "lm_studio") {
    return false;
  }
  const w = node.widgets?.find((x) => x.name === "ensure_load_on_select");
  return w ? Boolean(w.value) : false;
}

app.registerExtension({
  name: "llm-bikeshed.llm-connection",

  nodeCreated(node) {
    if (node.comfyClass !== "LLMConnection") {
      return;
    }

    const modelWidget = node.widgets?.find((w) => w.name === "model");
    const urlWidget = node.widgets?.find((w) => w.name === "url");
    const hostModeWidget = node.widgets?.find((w) => w.name === "host_mode");
    if (!modelWidget) {
      return;
    }

    const statusDetected = node.addWidget(
      "text",
      "status_detected",
      "detected: —",
      () => {},
      READ_ONLY_WIDGET_OPTIONS,
    );
    const statusEffective = node.addWidget(
      "text",
      "status_effective",
      "using: —",
      () => {},
      READ_ONLY_WIDGET_OPTIONS,
    );
    const statusLoaded = node.addWidget(
      "text",
      "status_loaded",
      "loaded: —",
      () => {},
      READ_ONLY_WIDGET_OPTIONS,
    );
    const statusAuth = node.addWidget(
      "text",
      "status_auth",
      "auth: —",
      () => {},
      READ_ONLY_WIDGET_OPTIONS,
    );
    const statusVram = node.addWidget(
      "text",
      "status_vram_policy",
      "VRAM: —",
      () => {},
      READ_ONLY_WIDGET_OPTIONS,
    );
    for (const w of [
      statusDetected,
      statusEffective,
      statusLoaded,
      statusAuth,
      statusVram,
    ]) {
      attachReadOnlyWidget(w);
    }

    let lastFace = null;
    let lastEffective = null;
    let modelLoadTimer = null;

    const applyStatus = (data) => {
      const detected = data?.detected;
      const effective = data?.effective || data?.backend;
      const face = data?.face || effective;
      const catalog = Boolean(data?.catalog);
      const hostMode = getHostMode(node);
      const override = hostMode !== HOST_MODE_AUTO;

      statusDetected.value = `detected: ${formatBackendName(detected)}`;
      if (override) {
        statusEffective.value = `using: ${formatBackendName(effective)} (override)`;
      } else {
        statusEffective.value = `using: ${formatBackendName(effective)} (auto)`;
      }
      statusLoaded.value = loadedStatusLine(catalog, data?.loaded_model, face);
      statusAuth.value = data?.auth_status || "auth: —";
      statusVram.value = vramPolicyLine(face, node);

      for (const w of [
        statusDetected,
        statusEffective,
        statusLoaded,
        statusAuth,
        statusVram,
      ]) {
        attachReadOnlyWidget(w);
      }

      lastFace = face;
      lastEffective = effective;
      applyFaceVisibility(node, face);
      applyModelWidgetMode(modelWidget, catalog);
      markNodeDirty(node);
    };

    const runFetch = async (initialSavedModel) => {
      const url = getWidgetUrl(urlWidget);
      const hostMode = getHostMode(node);
      const data = await fetchConnection(url, hostMode);
      if (!data) {
        applyStatus({
          detected: null,
          effective: "generic",
          face: "generic",
          catalog: false,
          loaded_model: undefined,
          auth_status: "auth: —",
        });
        applyModelWidgetMode(modelWidget, false);
        return;
      }
      applyStatus(data);
      if (data.catalog) {
        const saved =
          initialSavedModel !== undefined ? initialSavedModel : modelWidget.value;
        updateModelCombo(modelWidget, data.models || [], saved);
      }
      // URL change must never ensure-load (Vir lock).
    };

    let initialFetchTimer = null;
    const scheduleInitialFetch = () => {
      if (initialFetchTimer !== null) {
        clearTimeout(initialFetchTimer);
      }
      initialFetchTimer = setTimeout(() => {
        initialFetchTimer = null;
        runFetch(modelWidget.value);
      }, INITIAL_FETCH_DEBOUNCE_MS);
    };

    scheduleInitialFetch();
    node.__llmBikeshedScheduleConnectionFetch = scheduleInitialFetch;

    let urlRefetchTimer = null;
    const beginBusyStatus = () => {
      statusDetected.value = "detected: …";
      statusEffective.value = "using: …";
      statusLoaded.value = "loaded: —";
      markNodeDirty(node);
    };

    const scheduleUrlRefetch = () => {
      // URL change never ensure-loads — only refetch list/status.
      beginBusyStatus();
      clearTimeout(urlRefetchTimer);
      urlRefetchTimer = setTimeout(() => {
        runFetch(undefined);
      }, URL_REFETCH_DEBOUNCE_MS);
    };

    if (urlWidget) {
      const orig = urlWidget.callback;
      urlWidget.callback = function (_value) {
        if (orig) {
          orig.call(this, _value);
        }
        scheduleUrlRefetch();
      };
      attachUrlInputListeners(urlWidget, scheduleUrlRefetch);
    }

    if (hostModeWidget) {
      const orig = hostModeWidget.callback;
      hostModeWidget.callback = function (value) {
        if (orig) {
          orig.call(this, value);
        }
        beginBusyStatus();
        runFetch(modelWidget.value);
      };
    }

    const scheduleModelLoad = (url, model, backend) => {
      if (!shouldEnsureLoadOnSelect(node, lastFace) || !isRealModelName(model)) {
        return;
      }
      clearTimeout(modelLoadTimer);
      modelLoadTimer = setTimeout(async () => {
        const { ok } = await ensureModelLoaded(url, model, backend);
        if (ok) {
          runFetch(model);
        }
      }, MODEL_LOAD_DEBOUNCE_MS);
    };

    const origModelCallback = modelWidget.callback;
    modelWidget.callback = function (value) {
      if (origModelCallback) {
        origModelCallback.call(this, value);
      }
      markNodeDirty(node);
      statusVram.value = vramPolicyLine(lastFace, node);
      scheduleModelLoad(getWidgetUrl(urlWidget), value, lastEffective);
    };

    // Refresh face VRAM line when manage/ttl/ensure toggles change.
    for (const name of FACE_WIDGETS_ALL) {
      const w = node.widgets?.find((x) => x.name === name);
      if (!w) {
        continue;
      }
      const orig = w.callback;
      w.callback = function (value) {
        if (orig) {
          orig.call(this, value);
        }
        statusVram.value = vramPolicyLine(lastFace, node);
        markNodeDirty(node);
      };
    }

    node.addWidget("button", "Refresh Models", null, () => {
      beginBusyStatus();
      runFetch(modelWidget.value);
    });

    // Initial face hide based on default Auto until first fetch returns.
    applyFaceVisibility(node, null);
  },

  loadedGraphNode(node) {
    if (node.comfyClass !== "LLMConnection") {
      return;
    }
    node.__llmBikeshedScheduleConnectionFetch?.();
  },
});
