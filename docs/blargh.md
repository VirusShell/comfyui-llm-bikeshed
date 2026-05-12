# Permission Prompt Interruptions During Spec Execution

This documents every permission approval that interrupted autonomous execution across
sessions on this project. Evidence comes from `.claude/settings.local.json` — each
overly-specific rule represents a time Claude Code stopped to ask for approval.

## The Problem

Claude Code's permission system prompted for approval on nearly every new Bash command
pattern, even when the user had already approved similar operations. The result was
dozens of interruptions across sessions that required the user to babysit a process
designed to be autonomous.

## Evidence: Specific Permission Rules (Each = An Interruption)

These rules in `settings.local.json.bak` (the original state before broadened permissions
were added) each represent a time execution halted and the user had to click "Allow":

### Session 1-2: Early Execution (Tasks 1-3)

1. `Bash(dir:*)` — directory listing
2. `Bash(jq:*)` — jq for JSON state manipulation
3. `Read(//d/ai/comfyui-llm-bikeshed/**)` — reading project files
4. `Bash("specs/comfyui-llm-bikeshed/.ralph-state.json.tmp")` — writing temp state
5. `Bash(mv "specs/.../.ralph-state.json.tmp" "specs/.../.ralph-state.json")` — renaming state file
6. `Bash(cd D:/ai/... && sed -i 's/...' tasks.md)` — marking task 1.2 complete via sed
7. `Bash(cd D:/ai/... && rm -f .../.progress-task-1.md .../.progress-task-2.md)` — cleaning temp files
8. `Bash(cd D:/ai/... && jq '.taskIndex = 3...')` — advancing state to task 3

### Session 3-5: Adapter & Server Implementation

9. `Bash(python -c "from adapters.oai_compat import OAICompatAdapter;...")` — verify command for OAI adapter
10. `Bash(cd D:/ai/... && python -c "from adapters import get_adapter;...")` — verify command for adapter registry
11. `Bash(cd D:/ai/... && ruff check adapters/__init__.py)` — linting adapters
12. `Bash(ruff check:*)` — broader ruff pattern (finally!)
13. `Bash(cd D:/ai/... && python -c "from server.endpoints import _fetch_models_lm_studio;...")` — verify server endpoint
14. `Bash(python -c "from server.endpoints import _fetch_models_lm_studio;...")` — same command, slightly different form
15. `Bash(cd D:/ai/... && uv run ruff check server/endpoints.py)` — linting server
16. `Bash(cd D:/ai/... && uv run ruff check --fix server/endpoints.py)` — ruff fix variant
17. `Bash(SPEC_PATH="specs/comfyui-llm-bikeshed")` — variable assignment
18. `Bash("$SPEC_PATH/.ralph-state.json.tmp")` — state file with variable
19. `Bash(mv "$SPEC_PATH/.ralph-state.json.tmp" "$SPEC_PATH/.ralph-state.json")` — same op with variable

### Session 6+: Options Nodes & Later Tasks

20. `Bash(cd "D:\\ai\\..." && sed -i 's/...' tasks.md)` — marking task 1.24 complete (different quoting)
21. `Bash(cd D:/ai/... && sed -i 's/...' tasks.md)` — marking task 1.38 complete
22. `Bash(cd D:/ai/... && sed -i 's/...' tasks.md)` — marking task 1.39 complete
23. `Bash(mv specs/.../.ralph-state.json.tmp specs/.../.ralph-state.json)` — yet another mv variant
24. `Bash(cd D:/ai/... && jq '.taskIndex = 71...')` — advancing to task 71
25. `Bash(for f:*)` — for loop pattern
26. `Bash(do echo:*)` — echo inside loop

### Session 7+: PR & Gitea

27. `Read(//c/Users/Vir/.gitea/**)` — reading gitea config
28. `Read(//c/Users/Vir/.config/tea/**)` — reading tea CLI config
29. `Read(//c/Users/Vir/**)` — broader home directory read
30. `Bash(curl:*)` — curl for Gitea API
31. `Bash(gh pr:*)` — gh CLI for PR operations

## Broadened Rules (Added Later to Stop the Bleeding)

After repeated frustration, these broad rules were added to `settings.local.json`:

- `Edit` — all file edits
- `Write` — all file writes
- `Agent` — all subagent spawning
- `Bash(git:*)` — all git commands
- `Bash(python:*)` — all python commands
- `Bash(uv:*)` — all uv commands
- `Bash(ruff:*)` — all ruff commands
- `Bash(grep:*)` — all grep commands
- `Bash(cat:*)` — all cat commands
- `Bash(mv:*)` — all mv commands
- `Bash(rm:*)` — all rm commands
- `Bash(cp:*)` — all cp commands
- `Bash(sed:*)` — all sed commands
- `Bash(find:*)` — all find commands
- `Bash(echo:*)` — all echo commands
- `Bash(cd:*)` — all cd commands

**Critical finding:** These broadened rules used the **deprecated `:*` syntax** (e.g.,
`Bash(git:*)`) instead of the correct `Bash(git *)` format (space before asterisk).
This likely explains why rules appeared to not be respected — the `:*` suffix may not
match commands the same way the documented ` *` pattern does.

## Root Causes

1. **Deprecated pattern syntax.** The `:*` wildcard suffix (e.g., `Bash(git:*)`) is
   deprecated. The correct syntax is `Bash(git *)` with a space. This alone may explain
   most of the "settings not being respected" behavior across sessions.

2. **Pattern matching is too literal.** `mv "a" "b"` and `mv a b` are treated as
   different patterns. Same command with `cd` prefix vs without = different pattern.

3. **No command-class generalization.** Approving `python -c "from adapters..."` doesn't
   cover `python -c "from server..."`. Each unique python one-liner is a new approval.

4. **No project-scoped trust.** Working in a project directory doesn't imply trust for
   read-only operations within that directory.

5. **Subagent inheritance gaps.** Known issue — subagents may not always inherit
   user-level permissions. Project-level settings.local.json rules should work, but
   there are open bug reports about this behavior.

6. **State management commands repeat.** The jq/mv pattern for `.ralph-state.json` was
   approved dozens of times because the jq arguments changed each time.

## Impact

- **31+ interruptions** across ~7 sessions for an 80-task execution loop
- Each interruption broke the autonomous execution flow
- User had to monitor and click approve repeatedly
- Defeats the purpose of autonomous spec execution

## Recommendation

Pre-configure `.claude/settings.local.json` with broad allow patterns using **correct
syntax** (space before `*`, not `:*`), and explicit deny rules for dangerous operations.

### Correct pattern syntax reference

| Pattern | Matches |
|---------|---------|
| `Bash(git *)` | Any git command (space + wildcard) |
| `Bash(git commit *)` | Only git commit variants |
| `Bash(python *)` | Any python command |
| ~~`Bash(git:*)`~~ | **DEPRECATED** — may not work reliably |

### Rule evaluation order

`deny` > `ask` > `allow` — deny rules always win, so it's safe to allow broad patterns
and deny specific dangerous ones.

### Recommended template for spec execution

```json
{
  "permissions": {
    "allow": [
      "Edit",
      "Write",
      "Agent",
      "Read",
      "Glob",
      "Grep",
      "WebFetch",
      "WebSearch",
      "Bash(git status *)",
      "Bash(git add *)",
      "Bash(git commit *)",
      "Bash(git diff *)",
      "Bash(git log *)",
      "Bash(git branch *)",
      "Bash(git checkout *)",
      "Bash(git rev-parse *)",
      "Bash(git rev-list *)",
      "Bash(git push *)",
      "Bash(python *)",
      "Bash(uv *)",
      "Bash(ruff *)",
      "Bash(pytest *)",
      "Bash(jq *)",
      "Bash(grep *)",
      "Bash(cat *)",
      "Bash(ls *)",
      "Bash(dir *)",
      "Bash(find *)",
      "Bash(echo *)",
      "Bash(cd *)",
      "Bash(mv *)",
      "Bash(cp *)",
      "Bash(rm *)",
      "Bash(rm -f *)",
      "Bash(mkdir *)",
      "Bash(sed *)",
      "Bash(wc *)",
      "Bash(head *)",
      "Bash(tail *)",
      "Bash(sort *)",
      "Bash(curl *)",
      "Bash(gh *)",
      "Bash(test *)"
    ],
    "deny": [
      "Bash(rm -rf /)",
      "Bash(sudo *)",
      "Bash(curl * | sh)",
      "Bash(curl * | bash)",
      "Bash(wget * | sh)",
      "Bash(git push --force *)",
      "Bash(git reset --hard *)"
    ]
  }
}
```

Shell operator awareness: Claude Code recognizes `&&`, so `Bash(safe-cmd *)` will NOT
approve `safe-cmd && dangerous-cmd` — each segment is evaluated independently.
