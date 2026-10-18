# Playbooks

Each playbook is the shortest path that keeps the agent from reading files it does not need. Tool names may carry the `mcp__desktop-lancedb__` prefix in your client.

## Find and fix a bug

1. `search_desktop("<error message words or function name>", project=...)`. Read only the definition it returns.
2. `find_callers_exact(symbol_name, project_path)` if you need to see how it is called (real `symbol(` calls, without definitions or imports).
3. Fix with your normal edit tool, or with `patch_function_body(file_path, symbol_name, new_body)` to replace only the body (keeps signature, indentation and line endings; makes a backup outside the repo).
4. `find_related_tests(symbol)` → `run_test_isolated("<command for those tests>")`.

## Safe refactor or signature change

1. `search_desktop(symbol)` to get the definition and its usage line.
2. `get_impact_radius(symbol)`: every file that imports it. If the name exists in several files, use `archivo=` for the one you are changing.
3. `check_breaking_callsites(file_path, function_name, new_params)`: call sites that would break with the new parameters.
4. Rename inside one file with `rename_symbol_scoped(file_path, old_name, new_name)`; for other files, edit only the call sites listed in step 3.
5. `remove_unused_imports(file_path)` on the files you touched, then `run_typecheck_focus(files)` and `lint_summary(files)` (both return only the errors).
6. Run the related tests with `run_test_isolated`.

## Review a change or PR without reading the repo

1. `git_staged_overview(repo_path)`: one line per staged file.
2. For each changed symbol: `get_symbol_contract(file_path, symbol_name)` (signature, parameters, return and docstring, no body) and `get_impact_radius(symbol)`.
3. `check_circular_imports(file_a, file_b)` when the change adds an import between modules.
4. Read full bodies only where the contract or the impact looks risky.

## Onboard to a new repository

1. `list_projects` to confirm it is indexed (if not, see `setup.md`: `SYNRAG agregar <path> <name>`).
2. `repo_map(project, tokens=1024)`: signatures of the most important files, ranked by PageRank over imports, within a token budget. Add `foco="file.ts,function"` to center the map on what you are working on.
3. `search_desktop(..., tipo="docs")` for README and docs sections (~200-token chunks with their heading path).
4. `get_file_outline` on the two or three files that matter.

## Add a feature without duplicating code

1. `find_code_duplicates(symbol_name, project_dir)`: functions, classes or symbols with the same or similar names already in the project.
2. `verify_dependency_exists(dependency_name, project_dir)` before importing a package (understands monorepos and workspaces).
3. `extract_type_definition(file_path, type_name)` to reuse an existing interface, type or enum instead of reading the whole file.
4. `add_import_clean(file_path, import_statement)` adds the import after the last one in the header, only if missing.

## Debug failing tests or a noisy build

1. `run_test_isolated(test_command)`: summary and failures only.
2. `tail_clean_logs(log_path, max_lines=40)`: the end of a log without repeated lines.
3. `search_desktop` the failing function or assertion text, then read only that range.

## Hand off a long session

1. `context_budget_alert`: warns when recent agent sessions are growing too much.
2. `session_handoff(repo_path)`: short summary of branch, commits and changes. Start a new session with it instead of dragging the whole history.
3. `extract_todo_status(project)` to list pending TODO/FIXME/HACK comments for the next session.
