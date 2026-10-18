# Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| The agent never calls SynRAG | The MCP server is not loaded, or the agent has no instruction to prefer it | Restart the agent after installing. Check the MCP config file for `desktop-lancedb` (see `setup.md`). Rerun `SYNRAG configure` to restore the instruction block |
| No SynRAG tools at all | Not installed, or the client was open during install | Ask the user to install it from the project's README, then restart the client |
| Only `search_desktop` and `synrag_mas` | `bajo_demanda` profile | Call `synrag_mas` once, or switch profile with `SYNRAG uninstall --perfil` |
| A search misses a file you just created | The index is not up to date | Call `reindex_desktop` (or `SYNRAG index`). The optional watcher service reindexes on save |
| A project is missing from `list_projects` | Its folder is not indexed | `SYNRAG agregar <path> <name>`, then `SYNRAG index` |
| `get_impact_radius` mixes two definitions | Same symbol name in several files | Pass `archivo=` with the file you mean |
| Results from tests come before code | The query reads like a test query | Add "codigo" context or use `tipo="codigo"`; tests come after code unless the query asks for them |
| Rust or Go files are not found | Not supported yet | Use normal search for those languages. Supported: TypeScript, TSX, JavaScript, Python, Markdown/MDX/RST/AsciiDoc and SQL |
| First search after a restart is slow | The reranker model loads on first use | Later queries are fast (median 59-89 ms for a new query, ~3-4 ms when repeated) |
| JSON config was skipped during install | The file has comments or is not pure JSON | The installer prints the exact block to add by hand; it never rewrites such files |
| `lint_summary` says no linter was found | No local linter in the project | Install one (oxlint, eslint, biome, ruff or flake8) or run the project's own lint command |

Still stuck: open an issue at https://github.com/EnmanuelReynoso23/synrag/issues with the agent, the OS and what happened.
