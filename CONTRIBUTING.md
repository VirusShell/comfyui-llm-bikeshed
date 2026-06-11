# Contributing

Thanks for your interest in **comfyui-llm-bikeshed**.

## Scope

This pack covers **LLM text generation** for ComfyUI (LM Studio, Textgen, OpenAI-compatible hosts). Out of scope: image/video generation, native Ollama, chat history nodes, and additional cloud APIs unless explicitly scoped in the tracker.

## Getting started

1. Clone into `ComfyUI/custom_nodes/comfyui-llm-bikeshed`.
2. Install dev dependencies: `pip install -e ".[dev]"`
3. Copy `config.example.yaml` to `config.yaml` for local backend URLs and keys (never commit `config.yaml`).

## Before you open a PR

- Run tests: `python -m pytest -q`
- Run lint: `ruff check .`
- Do not commit API keys, `config.yaml`, or private host URLs.
- For behavior backed by external docs or issues, follow the provenance rules in [`docs/research/provenance-and-reverification.md`](docs/research/provenance-and-reverification.md).

## Pull requests

1. Branch from `master`.
2. Keep changes focused; match existing code style and relative imports used for ComfyUI runtime.
3. Update [`CHANGELOG.md`](CHANGELOG.md) under `[Unreleased]` for user-visible changes.
4. Add a [`docs/lessons-learned.md`](docs/lessons-learned.md) entry when a fix reveals a non-obvious ComfyUI or backend quirk.

## Issues

Use GitHub Issues for bugs, backend compatibility problems, and feature requests within pack scope. Include ComfyUI version, backend (LM Studio / Textgen / OpenAI), and relevant log excerpts when reporting runtime problems.
