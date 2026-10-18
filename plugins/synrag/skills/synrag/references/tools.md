# Tool reference (SynRAG 1.6)

28 tools with the full profile. The `esencial` profile keeps 5 (marked ★). The `bajo_demanda` profile starts with `search_desktop` and `synrag_mas`; calling `synrag_mas` registers the rest.

## Search and orient

| Tool | Parameters | Use it to |
|---|---|---|
| ★ `search_desktop` | `query`, `limit=5`, `project=""`, `detalle=False`, `tipo=""` (`"docs"` / `"codigo"`) | Find a definition, member or doc section. Exact definition first and whole, with its usage line |
| ★ `get_file_outline` | `file_path`, `project=""` | Signatures and line ranges of a file, including members of large classes and objects |
| ★ `repo_map` | `project`, `foco=""`, `tokens=1024` | Most important signatures of a repo (PageRank over imports) within a token budget |
| `list_projects` | none | Project names for the `project` filter |
| `reindex_desktop` | none | Refresh the index after creating or moving files |
| `synrag_mas` | none | Only in `bajo_demanda`: registers the remaining tools |

## Before editing

| Tool | Parameters | Use it to |
|---|---|---|
| ★ `get_impact_radius` | `symbol`, `project=""`, `archivo=""` | Files that depend on a symbol, separated per definition when the name repeats |
| `find_related_tests` | `file_or_symbol` | Test files associated with a file or symbol |
| `find_callers_exact` | `symbol_name`, `project_path=""` | Real `symbol(` calls, without definitions or imports |
| `get_symbol_contract` | `file_path`, `symbol_name` | Signature, parameters, return and docstring, without the body |
| `extract_type_definition` | `file_path`, `type_name` | Only the definition of an interface, type or enum |
| `get_import_graph` | `file_path`, `project=""` | A file's imports: local (relative or tsconfig alias) and external packages |
| `check_breaking_callsites` | `file_path`, `function_name`, `new_params`, `project_dir=""` | Existing calls that would break with new parameters |
| `check_circular_imports` | `file_a`, `file_b` | Whether importing `file_b` from `file_a` creates a direct or indirect cycle |
| `verify_dependency_exists` | `dependency_name`, `project_dir=""`, `desde_archivo=""` | Whether a package exists in the project or workspace before importing it |
| `find_code_duplicates` | `symbol_name`, `project_dir=""` | Symbols with the same or similar names, to avoid duplicates |

## Edit (keep line endings and indentation; never touch an ambiguous file name; backup outside the repo)

| Tool | Parameters | Use it to |
|---|---|---|
| `patch_function_body` | `file_path`, `symbol_name`, `new_body`, `project=""` | Replace only a function's body |
| `add_import_clean` | `file_path`, `import_statement`, `project=""` | Add an import after the header's last one, if missing |
| `rename_symbol_scoped` | `file_path`, `old_name`, `new_name`, `project=""` | Rename a whole-word identifier in one file |
| `remove_unused_imports` | `file_path`, `project=""` | Remove imports the file does not use |

## Run with short output

| Tool | Parameters | Use it to |
|---|---|---|
| ★ `run_test_isolated` | `test_command=""`, `cwd=""` | Run tests, return only the summary and failures |
| `lint_summary` | `files=""`, `cwd=""` | Linter errors only, grouped (oxlint, eslint, biome, ruff or flake8) |
| `run_typecheck_focus` | `files=""`, `cwd=""` | `tsc --noEmit` or pyright errors for the given files only |
| `tail_clean_logs` | `log_path`, `max_lines=40` | End of a log without repeated lines |

## Session

| Tool | Parameters | Use it to |
|---|---|---|
| `session_handoff` | `repo_path=""` | Short summary of branch, commits and changes to continue elsewhere |
| `context_budget_alert` | `transcript_dir=""` | Warn when recent agent sessions grow too much |
| `git_staged_overview` | `repo_path=""` | Staged changes, one line per file |
| `extract_todo_status` | `project=""` | TODO / FIXME / PENDIENTE / HACK comments |
| `get_savings_report` | none | Local usage report from SynRAG's telemetry |

## Optional (only with the user's own `GEMINI_API_KEY`; otherwise the engine makes no network calls)

| Tool | Parameters | Use it to |
|---|---|---|
| `ask_synrag_architect` | `query`, `project=""` | Architecture question answered by Gemini with the relevant local code |
| `explain_blast_radius` | `symbol`, `project=""`, `archivo=""` | Gemini explains the risk of changing a symbol from its dependents |
