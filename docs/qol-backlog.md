# Quality of Life Backlog

Tracked UX/polish improvements that aren't blocking v1 but should be addressed.

## Pending

### Tooltips / Hints

- [ ] **LLM Provider: LM Studio — `ttl` widget needs unit tooltip**
  TTL is in minutes but the widget is a bare INT with no indication. Add tooltip: "Time-to-live in minutes — how long LM Studio keeps the model loaded after the request. 0 = unload immediately."

- [ ] **LLM Generate (Basic) — `meta` output needs tooltip**
  Users won't know what `LLM_META` carries. Add tooltip: "Carries provider + options for chaining to downstream generation nodes."
  *(Flagged in concept doc, line 103)*

- [ ] **LLM Generate (Advanced) — `meta` input and output need tooltips**
  Same as above for the output; the input also needs: "Accepts provider + options from an upstream generation node. Explicit provider/options inputs override meta values."
  *(Flagged in concept doc, line 127)*

### Node Layout

- [ ] **LLM Options: text-gen-webui — evaluate node height**
  24 toggle widgets may be too tall. Implement as single node first, split only if it looks bad in the UI.
  *(Noted in design_review_update_2026-03-10.md, lines 122-127)*

- [ ] **LLM Options: LM Studio — evaluate node height**
  18 toggle widgets is borderline. Don't split unless it looks bad during testing.
  *(Noted in design_review_update_2026-03-10.md, lines 118-119)*

### Preset UX

- [ ] **Inline preset dropdown on generation nodes**
  Current v1 uses a separate Preset Loader node (known-working). An inline COMBO that populates system_prompt directly would be better UX but is fragile on workflow load. Deferred to post-v1.
  *(Resolution tracker A-6; concept doc lines 105-113)*

## Completed

*(none yet)*
