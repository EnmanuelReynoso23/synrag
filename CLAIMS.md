# Verifiable claims

[Español](CLAIMS.es.md) · English

Every number and claim in the README or on the website has its date, method and reproducing command here. Anything that could not be measured is listed as "not claimed". Last reviewed: Oct 16, 2026 (rows 1-9 are from Oct 6 unless noted).

Measurement machine: CachyOS (Linux), 12 cores, CPU only; index of ~76 projects, 96,318 chunks and 23,721 relations. Latency figures depend on your machine and its load: run the scripts on yours.

## Measured

| # | Claim | Result (Oct 6, 2026) | How to reproduce |
|---|---|---|---|
| 1 | New query, end to end over MCP, idle machine | Median ~90 ms (medians from 67 to 91 ms across 6 seeds; p90 from 105 to 121 ms). Queries of 2 to 4 words, 4 out of 5 with a project filter | `python benchmarks/latencia.py --modo mcp --semilla N` |
| 2 | First query after starting the MCP server | 118 to 201 ms; the server takes ~1.4 s to start up to `initialize` | same as row 1 |
| 3 | Repeated query (same query ignoring case and whitespace) | Median 8.3 to 8.9 ms (p90 ~10 ms) | same as row 1 |
| 4 | Engine only, without MCP | New: medians from 61 to 91 ms (5 seeds). Repeated: 6.1 to 7.8 ms | `python benchmarks/latencia.py --modo motor --semilla N` |
| 5 | With the CPU saturated (12 processes on 12 cores) | New: median ~192 ms (p90 241 ms) versus ~94 ms without load; repeated: ~16 ms. Engine mode, project of 23 thousand chunks, 3 to 6 words | `python benchmarks/latencia.py --modo motor --proyecto <el_mayor> --palabras 3-6 --semilla 7`, with no load and with 12 processes occupying the CPU at the same time |
| 6 | Real use inside Claude Code (with other tasks running) | 355 to 707 ms in 5 of 6 searches and 52 ms in one. **The difference from row 1 has not been explained** | `latency_ms` column of `~/.local/share/lancedb-hub/telemetry.db` |
| 7 | Reindexing a small file (`index_single_file`) | Median 8.0 to 8.6 ms (p90 ~9.3 ms; 3 runs of 15 tests), plus the 0.6 s wait the watcher uses to group saves | `python benchmarks/reindex_archivo.py` |
| 8 | Memory of the optional watcher | 257 MB after 1 h 54 min and 320 MB after 2 h 15 min; **it grows over time**. Average CPU ~0.3% | `ps -o rss=,etime= -p $(systemctl --user show lancedb-watcher.service -p MainPID --value)` |
| 9 | Size of the author's index | ~76 projects, 96,318 chunks, 23,721 relations, 62 MB on disk. Changes with every reindex | `python benchmarks/conteos.py` |

## Verified in the code

| # | Claim | Where |
|---|---|---|
| 10 | Candidates are retrieved by keywords (BM25, Tantivy FTS over LanceDB) and reranked with FlashRank `ms-marco-TinyBERT-L-2-v2` | `engine/indexer.py` (`search_desktop`), `engine/ranker.py` |
| 11 | The cache only hits on the same normalized query (lowercase and whitespace), lasts 4 hours and is cleared on reindex. It is not a semantic cache | `engine/cache.py`, `engine/indexer.py`; tested in `engine/tests/test_cache.py` |
| 12 | Chunking is AST-based for TypeScript, TSX/JSX, JavaScript and Python; Markdown is chunked by sections and SQL by statements; blocks over 2,400 characters are split | `engine/chunker.py` (`LANG_MAP`, `MAX_CHUNK_CHARS`) |
| 13 | The impact graph stores which files import each symbol in a LanceDB table; it does not use NetworkX | `engine/impact.py` |
| 14 | Hidden folders, files over 250 KB and credential files are excluded, and secret patterns are redacted | `engine/indexer.py`; tested in `engine/tests/test_secretos.py` and `engine/tests/test_busqueda.py` |
| 15 | The engine makes no network calls except for the two optional Gemini tools, which are only registered if the user configures their own `GEMINI_API_KEY` | `grep -rln urllib engine/` only shows `engine/argon.py`; `server_mcp.py` registers its tools only if `argon.disponible()` |
| 16 | 28 MCP tools (26 without a Gemini key), with no `outputSchema` and no `title` in the parameters | `python scripts/ci/mcp_tools_list.py` (fails if any has `outputSchema`) |

## Tested

| # | Claim | How |
|---|---|---|
| 17 | With Claude Code and Antigravity the MCP server stays loaded | On the author's machine there is one `server_mcp.py` process as a child of each AI; Antigravity reads `~/.gemini/config/mcp_config.json` (the path is in its binary and in that of the `agy` CLI) |
| 18 | The installer works on a clean machine, is idempotent, keeps other servers and uninstalls | Tested with a fake `HOME` on Oct 6, 2026: install, second pass, previous Antigravity path and `--uninstall`; automated in `engine/tests/test_instalador.py` |

## Measured on Oct 15, 2026

Author's machine, idle except where noted. Public repos cloned with `git clone --depth 1` (Flask `d086db8`, Hono `588ec13`); the scripts index only that repo in a temporary index (`--indexar`). Tokens = characters/4 except in rows 19 and 33 (real API counter).

| # | Claim | Result | How to reproduce |
|---|---|---|---|
| 19 | With a real agent, SynRAG spends fewer tokens than grep + reading files | -11.5% (72,533 versus 81,996 tokens; 16 questions x 2 rounds, Gemini 3.5 Flash-Lite); 16/16 correct in both modes; wins on 7 of 16. The questions only ask for the location, the worst case for SynRAG (it delivers the whole definition) | `python benchmarks/agente/agente.py` |
| 20 | Finding and reading a function by name costs less than grep (30 lines) + reading the section | Flask -27 to -30% (3 seeds, 25 functions), Hono -45% (16 functions); definition first in 23-25 of 25 and 16 of 16 | `python benchmarks/ahorro.py --repo <repo> --indexar --semilla N` |
| 21 | The same with natural-language questions | Flask -31% (12 questions, `benchmarks/preguntas/flask.json`); definition first 8 of 12, in the top 5 11 of 12 | `python benchmarks/ahorro.py --repo flask --indexar --n 0 --naturales benchmarks/preguntas/flask.json` |
| 22 | Documentation in chunks of ~200 tokens | -22% versus grep + 40 lines, -91% versus the whole file (10 questions on the Flask docs); answer in the top 5 10 of 10 | `python benchmarks/docs.py --repo flask` |
| 23 | Compressed packaging (signatures, types and imports only) | Flask 160,514 -> 38,882 tokens (-76%), Hono 756,316 -> 118,669 (-84%) | `python benchmarks/mapa.py --repo <repo>` |
| 24 | Long-output filter (`configure --filtro-largas`) | find: 178,449 -> 1,249 tokens; 5,000-line script: 73,088 -> 1,738; journalctl: 59,248 -> 7,444; all error lines kept. Claude Code hands the hook at most 30,000 characters: above that, SynRAG summarizes that piece and notes that Claude Code keeps the full output | `python benchmarks/filtro.py` |
| 25 | Noisy-command filter (`configure --filtro`) | 31-55% less on pytest, pip, npm and cargo (fixtures of 42-79 lines) | `python benchmarks/filtro.py` |
| 26 | Fixed cost of the MCP definitions | ~2,000 tokens (7,981 characters) with 28 tools; previously ~4,150 with 27 | `python scripts/ci/mcp_tools_list.py` |
| 27 | Latency on the author's index (125,570 chunks) | New query: medians from 61 to 89 ms (3 seeds); repeated: 3.3-3.7 ms (previously 6-8 ms: it no longer writes to the cache on every hit) | `python benchmarks/latencia.py --modo motor --semilla N` |
| 28 | Reindexing everything | 16.7 s for 9,247 files and 125,570 chunks | `SYNRAG index` |
| 29 | Index size after reindexing | 132 MB (previously 350-400 MB: the impact graph was never compacted and had piled up 7,836 versions) | `du -sh ~/.local/share/lancedb-hub/data` |
| 30 | Watcher: versions and threads | 2,000 synthetic saves: 2,001 -> 2 version files, 23 -> 3 threads, memory -10% (306 -> 275 MB); memory still grows somewhat | `python benchmarks/observador.py --guardados 2000` |
| 31 | Concise mode (`configure --conciso`) | -77% in model output over 10 tasks; key facts 28/30 versus 29/30; valid code 10/10. In the author's sessions, model text is ~9% of the content | `python benchmarks/conciso.py` |
| 32 | Clean install in an empty `HOME` (Linux) | Installs, detects `~/Projects`, indexes, searches and starts the MCP server with 28 tools | `bash scripts/ci/test_clean_install.sh` |
| 33 | Full system (search + long-output filter + concise mode) with a real agent on multi-step tasks | -29.2% of tokens billed by the API (191,567 versus 270,717; 10 tasks x 2 rounds, Gemini 3.5 Flash-Lite); quality (expected facts in the answer) 87% -> 90%. By type: planning a change -81%, tests with long output -38%, orientation -29%, locating and understanding -23%, understanding -20%. Loses on tests with short output (+124%, ~900 tokens of definitions per turn) and on 2 of 3 Flask tasks (+10% and +30%; on the latter quality drops from 100% to 83%). Round 1 -15%, round 2 -48%: with 2 rounds the margin of error is wide. Raw rows in `benchmarks/agente/completo-resultados-2026-10-15.json` | `python benchmarks/agente/completo.py --flask <ruta> --hono <ruta> --rondas 2` |

## Measured on Oct 16, 2026 (version 1.6)

Same machine. Flask `d086db8`, Hono `08807ce` (`git clone --depth 1`) and, as a real TypeScript monorepo, the author's own (pnpm, ~1,800 indexable files, not public). "v1.5.0" is `origin/main` measured the same day with the same scripts. The scripts in rows 34-37 use no model: they compare against the TypeScript compiler (`typescript` from `node_modules`) and Python's `ast` module, which act as the oracle.

| # | Claim | Result | How to reproduce |
|---|---|---|---|
| 34 | The chunker no longer leaves code out in large classes and objects | Lines of code (excluding comments) outside every chunk: Hono 441 -> 226 (`src/context.ts` 92 -> 0, where `c.json`, `c.text` and `c.header` lived); Flask 50 -> 39; monorepo 1,175 -> 1,149. Symbols with their own name in the monorepo: 12,841 -> 13,504 (the methods of service objects) | `python benchmarks/cobertura.py <repos> [--engine <motor viejo>]` |
| 35 | The impact graph's imports match the compiler's | Coverage / precision of the edges (file, symbol, source): Flask 100% / 96.0% -> 100% / 100%; Hono 74.7% / 93.9% -> 100% / 100%; monorepo 48.0% / 94.3% -> 100% / 100% (13,688 imports). Same chunking time (1.49 -> 1.48 s on 1,805 files) | `python benchmarks/imports.py <repos> [--engine <motor viejo>]` |
| 36 | Each import resolves to the same file as TypeScript | 100% of local imports (Hono 960, monorepo 3,564). Over-resolves 46 in Hono (packages of the monorepo itself that TypeScript did not find because the clone had no `node_modules`) and 2 in the monorepo | `python benchmarks/resolucion.py <repos>` |
| 37 | `get_impact_radius` separates definitions with the same name | Precision of each definition's consumers, symbols with a repeated name: by name (v1.5.0) Hono 18.4%, monorepo 15.4%; resolved (v1.6) 93.2% and 99.9%. All symbols: 38.8 / 43.7% -> 96.9 / 100%. Coverage 100% in all cases. Example: `useAuth` defined in two packages, 54 and 21 consumers; v1.5.0 said 30 (it cut off at 30 rows) | `python benchmarks/resolucion.py <repos>` |
| 38 | Cost of the usages line in searches by name | Finding and reading a function versus grep + section, 3 seeds: Flask -37 to -39% (v1.5.0) -> -36 to -38% (v1.6); Hono -54% -> -52%; natural language Flask -37% in both. Definition first in 23-25 of 25 and 16 of 16 in both | `python benchmarks/ahorro.py --repo <repo> --indexar --semilla N` |
| 39 | Essential MCP tool profile | 5 tools, 1,781 characters (~445 tokens); the full profile, 30 with the two Gemini ones, 8,139 characters (~2,034 tokens) | `SYNRAG_PERFIL=esencial python scripts/ci/mcp_tools_list.py` |
| 40 | The usages line does not slow down search | 30 new queries by name (10 random symbols per repo: Flask, Hono and the monorepo; seed 1): median 59 ms (v1.5.0) versus 60 ms (v1.6), p90 82 versus 86 ms. Resolved `get_impact_radius`: 18-42 ms (5 symbols). The first query for each project loads its file list and keeps it for 60 s | `python benchmarks/latencia_usos.py <repos> [--engine <motor viejo>]` |
| 41 | Full system with a real agent, v1.6 versus v1.5 on the same day | Same 10 tasks x 2 rounds as row 33, Gemini 3.5 Flash-Lite, tokens billed by the API. **v1.6: -63.9%** versus not using SynRAG (305,736 -> 110,338; 95% CI by task -83% to -24%), quality 87% -> 94%; rounds -67% and -61%. **v1.5 on the same day: -4.6%** (232,681 -> 222,035; 95% CI -34% to +15%), quality 87% -> 92% (Oct 15 measured -29.2%: it varies a lot between days). With SynRAG, v1.6 spends 50% less than v1.5 (110,338 versus 222,035), but the 95% CI runs from -80% to +29%: the difference comes from 2 tasks (`hono_c_json` -94%, which v1.6 solves and v1.5 fails in one of two rounds; `Config` methods -76%, thanks to the member list); on the other 8 they are similar. It still loses on tests with short output (+117%, fixed cost per turn) and on the Flask session signature (+38%). The 4 tasks on SynRAG's own repo are not a clean comparison (each version asks about its own code). Raw rows: `benchmarks/agente/completo-resultados-2026-10-16-v1.6.json` and `-v1.5.json` | `python benchmarks/agente/completo.py --flask <ruta> --hono <ruta> --rondas 2`, on this version and in a `git worktree` of the previous one |
| 42 | Fixed cost per turn after trimming and with the bajo_demanda profile (Oct 17, 2026) | Tokens counted with Gemini 3.5 Flash-Lite's `countTokens`, before trimming (`12155ec`) versus `main`: full-profile definitions 2,091 -> 2,068, essential 435 -> 412, **bajo_demanda 159** (2 tools; did not exist); usage instruction 188 -> 108; concise block 248 -> 115. Full + instruction + concise: 2,527 -> 2,291 per turn; with bajo_demanda, 382. This is a fixed cost, not a saving on a task: the agent benchmark uses its own 3 tools and does not reflect it | `python benchmarks/costo_fijo.py [--engine <motor viejo>]` |

Discarded after measuring: LLMLingua-2 (compresses ~50% but breaks code, deletes test results from logs and weighs 1.9-6.6 GB). See `investigacion/llmlingua.md`.

## Not claimed

- **Savings in money or over full work sessions.** What was measured are bounded tasks (rows 19-25 and 33). There is no measurement of real long sessions with and without SynRAG. `get_savings_report` still shows a counterfactual reference, not a measured saving.
- **That the improvement between versions in row 41 is general.** It comes from 2 of 10 tasks and the confidence interval includes zero; with a single model and 2 rounds. The saving of v1.6 versus not using SynRAG does exclude zero (95% CI -83% to -24%).
- **That row 33 holds for any agent.** It is 10 tasks, a single model (Gemini 3.5 Flash-Lite) and 2 rounds with high variance. It has not been measured with Claude or on long sessions.
- **Rust and Go.** The chunker ships their grammars and returns chunks, but without a symbol name (tested on Oct 6, 2026), and `ALLOWED_EXTENSIONS` in `engine/indexer.py` does not include `.rs` or `.go`, so those files are not indexed. They are not supported.
- **Compatibility** with Gemini CLI, Codex CLI, Cursor, Windsurf, Cline/Roo Code, Zed, macOS and Windows with WSL. They are configured according to their documentation, but they have not been tested. Continuous integration (`.github/workflows/pruebas.yml`) tests Linux and macOS once pushed to GitHub.
- **The website** no longer has simulated demos (Oct 17, 2026). Its numbers come from `src/data/medido.ts`, which copies rows from this file; the search example is real output on Flask `d086db8`.

## How to add or change a claim

1. Measure with a command someone else can run (or cite the file and line of code).
2. Add a row here with the date, result and command, and the same row in `CLAIMS.es.md`.
3. Only then write the number in the README or on the website.
4. If a number stops holding, change or remove it the same day.
