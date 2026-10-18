---
name: synrag
description: Use SynRAG's MCP tools to find code instead of listing folders or reading whole files. Use whenever you need to locate a function, class, method, type or doc section in the user's local projects, see who uses a symbol, check what breaks before editing it, or find the tests for it.
---

# SynRAG: locate before you read

SynRAG is a local MCP server (`desktop-lancedb`) that indexes the user's projects by their syntax tree. It returns whole definitions with their file and line range, so you can read only what you need.

## Check that it is available

Look for the tools `search_desktop`, `get_file_outline` and `get_impact_radius` (they may be prefixed with `mcp__desktop-lancedb__`). With the `bajo_demanda` profile only `search_desktop` and `synrag_mas` are present: call `synrag_mas` once when you need the rest.

If none of them exist, tell the user SynRAG is not installed and point them to the one-line installer, then continue with your normal search:

```bash
curl -sSL https://raw.githubusercontent.com/EnmanuelReynoso23/synrag/main/install.sh | bash
```

## How to work with it

1. **Find first.** Call `search_desktop(query, project=...)` with a symbol name (`useAuth`), a member (`Config.from_envvar` or `Config from_envvar`) or plain words ("load config from env"). The exact definition comes first and whole, with a line of callers under it; the other hits are one line each (`path:lines kind name | signature`). Use `tipo="docs"` for documentation and `tipo="codigo"` for code only.
2. **Read only the range it gave you.** Open the file at those lines instead of reading the whole file. Do not list directory trees to orient yourself.
3. **Get the shape of a file** with `get_file_outline(file_path)`: signatures and line ranges, including the members of large classes and objects.
4. **Before changing a symbol**, call `get_impact_radius(symbol)` to see which files import it. If two files define the same name, pass `archivo=` to pick one.
5. **Find its tests** with `find_related_tests(file_or_symbol)` and run only those.
6. **New repository?** `repo_map(project, tokens=1024)` gives the signatures of its most important files within a token budget.

Use `list_projects` to see project names for the `project` filter. If the user just created or moved files and a search misses them, `reindex_desktop` refreshes the index.

## When not to use it

- The user already gave you the exact file and lines.
- A one-line answer where `grep` on a known file is enough.
- A tool returns an error: say so briefly and fall back to normal search.
