# [Topic] — verified / partial / stale

**Date:** YYYY-MM-DD  
**Scope:** [What this note covers — routes, platform behavior, parameter surface, etc.]

Copy this file when starting new research under `docs/research/`. Gold reference: [`textgen-lifecycle-verified.md`](textgen-lifecycle-verified.md). Write-time rules: [`provenance-and-reverification.md`](provenance-and-reverification.md).

---

## Summary — what we believe

- [Bullet: claim in plain language]
- [Separate confirmed facts from hypotheses]

---

## Verification

| Topic | Source URL | Access date | Status / commit | Verified how |
|-------|------------|-------------|-----------------|--------------|
| | | YYYY-MM-DD | open / closed / `main` @ SHA | `code read` / `empirical` / `docs only` |

**Verified how** meanings:

- `code read` — upstream source at pinned branch/commit (or local repo file)
- `empirical` — reproduced on live backend or ComfyUI run in target environment
- `docs only` — exploration only; **not** sufficient alone for `Confirmed` tracker rows or behavior-critical code

---

## Applies to

- **Files:** `path/to/file.py`, …
- **Tracker:** A-XX, API-YY, P-ZZ
- **Features:** [node name, adapter path, UX behavior]

---

## Falsifiers — what would prove this wrong

- [Observable outcome that contradicts the claim — e.g. different HTTP status, route removed, auth gate changed]
- [Upstream commit or release that renames/moves the cited API]

---

## Re-check triggers

Re-open this note when any of these occur:

- [ ] Touching code or docs listed in **Applies to**
- [ ] Upstream release or default branch change for cited repo
- [ ] Empirical failure that matches a falsifier
- [ ] Tracker row promotion (`Assumed` → `Confirmed`) for this topic
- [ ] [Topic-specific trigger — e.g. Textgen rename, ComfyUI version bump]

---

## Confirmed behavior

- …

## Partially confirmed / operational

- …

## Unknown / version-sensitive

- …
