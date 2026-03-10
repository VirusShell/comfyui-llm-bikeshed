# comfyui-llm-bikeshed — Concept Document

> **Phase:** Conceptual / Early Ideation
> **Date:** 2025-02-18
> **Status:** Exploring ideas — nothing here is locked in stone

---

## What Is This?

A custom node pack for ComfyUI that connects workflows to LLMs — both local
servers and cloud APIs — through a small set of purpose-built nodes.

The name is `comfyui-llm-bikeshed`, chosen by spinning wheel, and we're
keeping it because it's memorable, unique, and honestly kind of perfect.

## Why Does This Need to Exist?

The existing options for LLM integration in ComfyUI each have friction points:

- **comfyui-ollama** has clean architecture and great features (system prompts,
  vision, structured output), but it's locked to Ollama. No cloud APIs, no
  other local backends.

- **comfyui-llm-toolkit** supports many providers on paper, but has critical
  gaps: system prompts are hardcoded (not user-configurable), local backends
  like LM Studio and text-gen-webui aren't actually wired up for text
  generation, and it carries heavy baggage (image gen, video gen, music gen,
  speech synthesis — stuff that has nothing to do with LLM text).

What we actually want is pretty simple: send a prompt (with a customizable
system prompt) to whichever LLM backend happens to be running, and get text
back. Do the same with images for vision models. Have a chat mode. Maybe get
structured data out. That's it.

## Core Ideas

### The Node Lineup

We're thinking about four main nodes, roughly in order of how important they
feel right now:

**LLM Text Generate** — The workhorse. Takes a system prompt and a user prompt,
sends them to whatever LLM is configured, returns text. System prompt is a
first-class visible input, not buried in settings or hardcoded. This is the
whole reason the project exists.

**LLM Image Describe** — Vision-focused. Takes an image (or batch), sends it
to a vision-capable model with a prompt, returns a description. Ships with
preset description styles (detailed, training caption, art critique, etc.) so
you can get useful output without writing a custom system prompt every time.
Still has the system prompt field for full control when you want it.

**LLM Chat** — Multi-turn conversation. Same core idea as Text Generate, but
maintains conversation history across executions. History flows through an
optional dedicated socket, so you can visually chain chat nodes and see the
conversation state moving through your workflow.

**LLM Structured Output** — Returns data in a specific shape (JSON matching a
schema) instead of freeform text. Useful when LLM output needs to feed into
other nodes that expect specific data formats. Different providers handle this
differently under the hood, but from the user's perspective it's just "give me
JSON that looks like this."

Plus supporting nodes:

**LLM Provider** — Configure which backend and model to use. One node, dropdown
to pick the backend, model selection that adapts to what's available. Not every
backend needs its own node — one provider node covers everything.

**LLM Options (Base)** — Common inference parameters (temperature, max tokens,
top_p, stop sequences). Connect it for control, leave it disconnected and the
model uses its own defaults. Simple.

**LLM Options (Backend-Specific)** — Dedicated options nodes for backends that
have unique parameters. Ollama's mirostat settings, keep_alive, num_ctx, etc.
Only needed if you want to tweak those specific knobs. This approach keeps the
common case clean while still exposing the full power of each backend.

### Provider Coverage

The backends we want to support, roughly grouped by how they'd be handled:

**OpenAI-compatible** (most of these expose the same API shape):
- text-generation-webui (local, actively used)
- LM Studio (local, actively used)
- Ollama (local, via its OpenAI-compat endpoint for basic use)
- vLLM (local)
- OpenAI (cloud)
- OpenRouter (cloud)
- Grok / xAI (cloud)

**Native API — Ollama:**
- Ollama also gets a dedicated adapter for its native API, which unlocks
  features the OpenAI-compat endpoint doesn't expose (keep_alive, context
  arrays, model management, mirostat, etc.)

**Native API — Anthropic:**
- Claude models via Anthropic's own API format

**Native API — Google Gemini:**
- Gemini models via Google's own API format

The key architectural insight here is that most backends speak OpenAI's API
format (or close to it), so one adapter covers roughly 80% of the targets.
Then just two or three more adapters cover the rest. This keeps the codebase
small and maintainable.

### System Prompt Philosophy

This is the heart of the project. Every generation node has a visible,
editable system prompt field. It's not hidden in config, not locked to presets,
not hardcoded.

On top of that, nodes ship with preset dropdowns for common use cases. Pick
"Detailed Scene Description" on the Image Describe node and you get a solid
default system prompt without writing anything. But the system prompt field is
right there if you want to customize or replace it entirely.

This "preset + override" pattern gives you approachability for casual use and
full control for power users. Both matter.

All major LLM providers (local and cloud) natively support system prompts as a
dedicated API parameter, so there's no awkward workaround needed — it just
works everywhere.

### Preset Ideas (Early Brainstorm)

These are rough starting points, not a final list.

**For Image Describe:**
- Detailed Scene Description
- Training Caption (tag-style / booru-style)
- Art Critique (composition, technique, style)
- Accessibility Alt-Text
- Technical Composition Analysis
- Simple / Casual Description
- Character Description

**For Text Generate:**
- Prompt Enhancer (expand terse prompts into detailed ones)
- Creative Writer
- Technical Editor
- Summarizer
- Rewriter / Paraphraser

These would be baked into the nodes as dropdown selections — zero configuration
needed to get useful results.

### API Key Security

**Hard requirement:** API keys must never be stored in the workflow graph.

ComfyUI serializes widget values into workflow JSON files. If someone shares a
workflow that has an API key as a text widget, that key ships with it. This is
unacceptable.

The approach: keys come from a config file or environment variables, both of
which live outside the workflow entirely. The Provider node can show a status
indicator ("Anthropic key: ✓ configured" / "✗ missing") but never exposes the
actual value. This is a non-negotiable safety constraint.

### Parameter Compatibility

Not every backend accepts the same inference parameters. Research so far shows:

**Universal** (every backend accepts these):
- temperature, max_tokens, top_p, stop sequences

**Widely supported** (most backends):
- top_k (Anthropic, Gemini, Ollama, vLLM, text-gen-webui — but NOT OpenAI)
- seed (OpenAI, vLLM, Ollama — but NOT Anthropic or Gemini)

**Backend-specific:**
- Ollama: num_ctx, mirostat, mirostat_tau, mirostat_eta, keep_alive
- text-gen-webui: typical_p, and various sampler-specific params
- repeat_penalty vs frequency_penalty (different naming, different behavior)

This is exactly why we're splitting options into a base node (universal params)
plus backend-specific extras. The base node handles what works everywhere. If
you need mirostat tuning for Ollama, connect the Ollama Options node. If you
don't, everything just works with sensible defaults.

Unsupported parameters sent to a backend that doesn't recognize them should be
silently ignored rather than erroring. We know Anthropic does this; need to
confirm behavior for other backends.

### Technical Leanings

These aren't final decisions, but directions we're leaning based on research:

- **Raw HTTP via aiohttp** rather than provider-specific SDKs (openai, anthropic,
  google-genai libraries). Keeps dependencies minimal, avoids version conflicts
  with ComfyUI or other node packs, and means all adapters follow the same
  pattern. The tradeoff is manually constructing API payloads, but these are
  well-documented REST APIs.

- **YAML for configuration** (API keys, host overrides, defaults). Familiar,
  human-readable, already a dependency in ComfyUI's ecosystem.

- **Target V1 node spec** for now. The V3 spec is still in active development
  and not stable. Build on V1 patterns with awareness of where V3 is heading,
  so migration isn't painful later.

- **Frontend JS** will be needed for dynamic model dropdowns (querying running
  backends for their model list). The `js/` directory convention is the current
  standard.

## Design Patterns Worth Borrowing

Ideas observed in existing node packs that seem worth carrying forward:

**From comfyui-ollama (V2 architecture):**
- The Connectivity → Options → Generate decomposition
- Meta passthrough for chaining nodes without re-specifying provider config
- System prompt as a required, visible input
- Image → base64 conversion pipeline for vision
- Enable/disable toggles for individual options (though we're adapting this
  into the base + extras split instead)

**From comfyui-llm-toolkit:**
- The general concept of a provider dispatcher (one entry point, routes to
  the right backend)
- API key resolution chain (direct → config → env vars)

**From JoyCaption:**
- Preset dropdown for caption/description types
- Simple node + Advanced node pattern (basic use vs. full control)
- Extra Options as a separate connectable node

## What We're Not Doing

Worth stating explicitly:

- Not building image generation nodes (DALL-E, Imagen, etc.)
- Not building video, music, or speech synthesis nodes
- Not bundling transformers, torch, or other heavy ML libraries
- Not trying to be a general-purpose AI toolkit
- Not hardcoding system prompts or locking users into presets

This is an LLM text interface. It connects ComfyUI workflows to language
models. That's the scope.

## Open Questions

Things we haven't figured out yet:

- **How should presets interact with the system prompt field?** Does picking a
  preset overwrite the system prompt text? Append to it? Or does the dropdown
  control a hidden template and the text field acts as additional instructions?

- **Model selection UX for cloud providers** — Local backends can be queried
  for their model list. Cloud providers have hundreds of models. Do we
  dynamically fetch the full list? Use a curated subset? Free-text input?

- **Error handling philosophy** — When a backend is unreachable or returns an
  error, what should the node output? An error string? A special error type?
  Should it halt the workflow or pass through a fallback value?

- **Batch behavior for Image Describe** — When given a batch of images, does
  it describe each one separately (returning multiple strings) or describe
  them collectively? How does this interact with ComfyUI's batch/list handling?

- **Config file location** — In the node pack's own directory? In ComfyUI's
  root? In a user data directory? Each has tradeoffs for portability, updates,
  and multi-user setups.

- **`.env` file support** — Worth adding alongside YAML + env vars? Adds a
  dependency but is a familiar pattern. Or is it redundant?

- **ComfyUI Registry / Manager publishing** — What's needed to make installation
  smooth through the standard channels? requirements.txt, pyproject.toml,
  install.py lifecycle scripts?

- **How do other backends handle unexpected parameters?** — We know Anthropic
  silently ignores unknown params. Need to verify this for text-gen-webui,
  LM Studio, vLLM, Ollama, OpenAI, and the others to confirm our "send and
  let the adapter figure it out" approach is safe.

---

> This document is a snapshot of early thinking. It captures the "what" and
> "why" — the actual "how" comes later once we're confident in the direction.
> Everything here is open to revision as we learn more.
