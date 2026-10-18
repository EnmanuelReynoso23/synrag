# Setup

SynRAG is free and open source (MIT). It runs on CPU, needs Python 3.10+, and never sends code anywhere (the two optional Gemini tools only work if the user sets their own `GEMINI_API_KEY`). Tested on Linux; macOS and WSL should work but are not tested yet.

## Install (one line)

Ask the user before running it, then:

```bash
curl -sSL https://raw.githubusercontent.com/EnmanuelReynoso23/synrag/main/install.sh | bash
```

Or from a clone: `git clone https://github.com/EnmanuelReynoso23/synrag.git && cd synrag && ./install.sh`.

What it does: copies the engine to `~/.local/opt/lancedb-hub`, creates an isolated virtualenv, installs the `SYNRAG` / `synrag` commands in `~/.local/bin`, and configures **only the AI tools that are installed**: it registers the MCP server `desktop-lancedb` and adds a short usage block to their global instructions. It backs up each file it changes (`.bak-YYYYMMDD-HHMMSS`), never overwrites a JSON it cannot parse, and is idempotent. Preview without writing anything: `./install.sh --dry-run`.

| Agent | MCP config | Status |
|---|---|---|
| Claude Code | `~/.claude.json` | Tested |
| Google Antigravity | `~/.gemini/config/mcp_config.json` | Tested |
| Gemini CLI | `~/.gemini/settings.json` | Configured, not tested |
| Codex CLI | `~/.codex/config.toml` | Configured, not tested |
| Cursor | `~/.cursor/mcp.json` | Configured, not tested |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | Configured, not tested |
| Cline / Roo Code | VS Code `cline_mcp_settings.json` | Configured, not tested |
| Zed | `~/.config/zed/settings.json` (pure JSON only) | Configured, not tested |

Restart the agent after installing so it loads the new MCP server.

## Choose what gets indexed

By default it detects common folders such as `~/Projects`, `~/code` or `~/dev`.

```bash
SYNRAG carpetas                       # what is indexed and where the list comes from
SYNRAG agregar ~/work/my-app my-app   # add a folder (optional project name)
SYNRAG quitar ~/work/old-app          # stop indexing a folder
SYNRAG index                          # reindex everything
```

The list lives in `~/.config/synrag/carpetas.txt` (or the `SYNRAG_CARPETAS` environment variable).

## Choose a tool profile

Tool definitions are resent every turn in many clients, so fewer tools means fewer fixed tokens.

```bash
SYNRAG configure --perfil esencial      # 5 tools, ~412 tokens of definitions
SYNRAG configure --perfil bajo_demanda  # starts with 2 tools, ~159 tokens; synrag_mas adds the rest
SYNRAG uninstall --perfil               # back to all 28 (~2,068 tokens)
```

Claude Code loads tool definitions on demand, so it does not need a profile.

## Verify

```bash
SYNRAG "some_function_name"   # search from the terminal
SYNRAG stats                  # index size, latency and usage
```

In the agent, `list_projects` should list the indexed projects.

## Uninstall

```bash
SYNRAG uninstall                    # removes the MCP entry, the instruction block and the commands
rm -rf ~/.local/opt/lancedb-hub     # optional: engine and index
```

`SYNRAG uninstall --dry-run` shows what it would remove. It only removes what the installer added.
