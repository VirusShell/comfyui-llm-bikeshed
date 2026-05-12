# The Archive

Structured research captures for this project.

## Purpose

`docs/the-archive/` stores durable, timestamped findings from external docs, issue threads, and custom node code investigations so future decisions can reference exact evidence instead of memory.

## Entry Requirements (Per Entry)

Each archived entry should include:

- `entry_id`: Stable ID (for example `R-2026-05-11-001`)
- `topic`: One-line scope
- `captured_at`: When we fetched or reviewed the source (ISO-like format)
- `source_posted_at`: When the source was posted/updated, if known (`unknown` if not available)
- `source_url`: Exact URL captured
- `source_type`: `official_docs`, `github_issue`, `github_code`, `local_mirror`, etc.
- `finding`: What the source says
- `implication_for_project`: Why it matters here
- `confidence`: `high`, `medium`, `low`

## File Naming

Use dated files:

- `YYYY-MM-DD-<short-topic>.md`

Example:

- `2026-05-11-comfyui-input-validation-and-connection-patterns.md`

## Source Integrity Rules

- Prefer canonical URLs (official docs, GitHub issue/page, raw file links).
- If using local mirrors, also include the upstream URL when available.
- Quote or summarize faithfully; clearly mark interpretation as interpretation.
- If a claim does not have a direct source yet, log it as an open hypothesis.

