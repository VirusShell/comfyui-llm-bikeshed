# Versioning

This pack uses [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

## Source of truth

- **`pyproject.toml`** — `[project].version` is the canonical release version (ComfyUI Registry reads this file).
- **`version.py`** — `__version__` must match `pyproject.toml` for runtime and support diagnostics.

## When to bump

| Change | Bump |
|--------|------|
| Breaking workflow/node API (removed nodes, incompatible `LLM_PROVIDER` shape, required new config) | **MAJOR** |
| New nodes, backends, or user-visible features; non-breaking behavior improvements | **MINOR** |
| Bug fixes, docs-only, internal refactors with no user-visible contract change | **PATCH** |

Pre-1.0 history (0.1.0–0.3.0) reflected early development and the Ollama removal at 0.3.0. **1.0.0** marks the first public GitHub and ComfyUI Registry release with the current provider, lifecycle, generation, and cancel-interrupt surface.

## Release checklist

1. Move `[Unreleased]` entries in [`CHANGELOG.md`](../CHANGELOG.md) into a new `## [X.Y.Z] - YYYY-MM-DD` section.
2. Bump `version` in `pyproject.toml` and `__version__` in `version.py` to the same value.
3. Commit with a clear message (e.g. `chore: release v1.0.0`).
4. Tag `vX.Y.Z` on the release commit and push the tag to GitHub.
5. Push to **`master`** (default branch). The [Publish to Comfy registry](.github/workflows/publish_registry.yml) workflow runs on pushes to `master` or `main` when `pyproject.toml` changes.


**CI note:** Any push that changes pyproject.toml on master/main triggers the publish workflow, but the job **skips** unless project.version changed in that commit (or you run **workflow_dispatch** manually). Packaging-only edits must either bump semver or use manual dispatch after a version bump.


Registry publishing requires the repository secret `REGISTRY_ACCESS_TOKEN` (or `COMFY_REGISTRY_API_KEY`). A version already on the registry is not overwritten; each release needs a new semver.

## Contributors

For day-to-day PRs, add user-visible notes under `[Unreleased]` in `CHANGELOG.md` (see [`CONTRIBUTING.md`](../CONTRIBUTING.md)).
