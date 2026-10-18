---
name: synrag
description: Cut the tokens your coding agent spends by locating code with SynRAG (a free, local MCP server) instead of listing folders and reading whole files. Use it whenever you need to find a function, class, method, type or doc section in the user's local projects, check who uses a symbol and what breaks before editing it, onboard to a new repo, run only the relevant tests, or keep a long session from bloating.
---

# SynRAG token saver

SynRAG is a free, open-source (MIT) MCP server that runs on the user's machine: https://github.com/EnmanuelReynoso23/synrag
It indexes local projects by their syntax tree (Tree-sitter), retrieves with BM25 over LanceDB and reranks on CPU, and resolves imports into a dependency impact graph. This skill is the playbook that tells you **when and how** to use its tools so you read only what you need.

Measured with a real agent (10 multi-step tasks × 2 rounds, tokens billed by the API): -63.9 % tokens, correct answers 87 % → 94 %. On very short tasks it can cost more than plain `grep` (see "When not to use it").

## 1. Check that SynRAG is available

Look for these tools (often prefixed `mcp__desktop-lancedb__`): `search_desktop`, `get_file_outline`, `get_impact_radius`.

- Only `search_desktop` and `synrag_mas` present → the `bajo_demanda` profile is on. Call `synrag_mas` once when you need anything beyond search.
- None present → SynRAG is not installed. Follow `references/setup.md` with the user (one-line installer, no API keys), then continue with normal search until it is ready.

## 2. The core loop: locate, read the range, act

1. **Locate.** `search_desktop(query, project=...)`
   - A symbol name: `useAuth`, `open_session`
   - A member: `Config.from_envvar` or `Config from_envvar`
   - Plain words: "load config from environment variables"
   - `tipo="docs"` for documentation, `tipo="codigo"` for code only.
   The exact definition comes back first and whole, with a usage line (`sessions.py:324 open_session, :373 save_session; imported by 3 files`) and, for big classes, the member list with lines. Other hits are one line: `path:lines kind name | signature`.
2. **Read only that range.** Open the file at the lines returned. Do not list directory trees or read whole files to orient yourself.
3. **Need the shape of a file?** `get_file_outline(file_path)`: signatures and line ranges, including members of large classes and objects.
4. **Act** with the playbook that fits the task (`references/workflows.md`).

Use `list_projects` to get names for the `project` filter. If the user just created or moved files and a search misses them, call `reindex_desktop`.

## 3. Before you change anything

- `get_impact_radius(symbol)` → which files depend on it. If two files define the same name, it separates them; pass `archivo=` to pick one.
- `check_breaking_callsites(file_path, function_name, new_params)` before changing a signature.
- `find_related_tests(file_or_symbol)` → then `run_test_isolated(test_command)` on just those, which returns only the summary and the failures.

## 4. Keep long sessions lean

Every turn resends the whole history, so session length costs more than any tool. When a session grows, call `context_budget_alert`; before stopping or switching, `session_handoff` writes a short summary of branch, commits and changes to continue from.

## 5. When not to use it

- The user already gave you the exact file and lines.
- A one-line lookup in a known file where `grep` returns a single line.
- A trivial task where the tool definitions cost more than the work. Suggest `SYNRAG configure --perfil bajo_demanda` (159 tokens per turn) if the user runs many short tasks.
- A tool errors: say so in one line and fall back to normal search.

## References

- `references/workflows.md`: step-by-step playbooks (find and fix a bug, safe refactor, review a PR, onboard to a repo, add a feature without duplicates, debug failing tests).
- `references/tools.md`: all 28 tools with their parameters and when to use each.
- `references/setup.md`: install, choose folders and profile, verify, uninstall.
- `references/troubleshooting.md`: common problems and their fixes.
