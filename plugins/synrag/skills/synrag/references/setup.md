# Setup

SynRAG is free and open source (MIT). It runs on CPU, needs Python 3.10+, and never sends code anywhere (two optional tools use Gemini only if the user sets their own `GEMINI_API_KEY`). Tested on Linux; macOS and WSL should work but are not tested yet.

## Installing is the user's job, not yours

This skill never installs, downloads or deletes anything, and you should not either. If SynRAG is missing:

1. Tell the user that this skill needs the SynRAG MCP server and that it is free.
2. Point them to the installation section of the project's README: https://github.com/EnmanuelReynoso23/synrag#readme. Suggest they read the installer first and preview it with its dry-run option, which shows what it would change without writing anything.
3. Ask them to restart their agent once it is installed, then continue with your normal search tools in the meantime.

What the installer does, so you can answer questions about it: it places the engine in `~/.local/opt/lancedb-hub` inside an isolated Python virtualenv, adds the `SYNRAG` command in `~/.local/bin`, and configures only the AI tools that are present. For each one it registers the MCP server `desktop-lancedb` and adds a short usage block to its global instructions. It backs up every file it changes, never overwrites a JSON it cannot parse, and running it twice changes nothing.

| Agent | MCP config file | Status |
|---|---|---|
| Claude Code | `~/.claude.json` | Tested |
| Google Antigravity | `~/.gemini/config/mcp_config.json` | Tested |
| Gemini CLI | `~/.gemini/settings.json` | Configured, not tested |
| Codex CLI | `~/.codex/config.toml` | Configured, not tested |
| Cursor | `~/.cursor/mcp.json` | Configured, not tested |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | Configured, not tested |
| Cline / Roo Code | VS Code `cline_mcp_settings.json` | Configured, not tested |
| Zed | `~/.config/zed/settings.json` (pure JSON only) | Configured, not tested |

## Settings the user can change

Suggest these to the user; they run them in their own terminal.

**What gets indexed.** By default SynRAG detects common folders such as `~/Projects`, `~/code` or `~/dev`. The user manages the list with `SYNRAG carpetas` (show), `SYNRAG agregar <path> [name]` (add) and `SYNRAG quitar <path>` (remove), then `SYNRAG index` to reindex. The list is stored in `~/.config/synrag/carpetas.txt`. From the agent you can refresh the index with the `reindex_desktop` tool.

**Tool profile.** Many clients resend tool definitions every turn, so fewer tools means fewer fixed tokens:

| Profile | Command | Tools | Fixed cost per turn |
|---|---|---|---|
| Full (default) | `SYNRAG uninstall --perfil` | 28 | ~2,068 tokens |
| Essential | `SYNRAG configure --perfil esencial` | 5 | ~412 tokens |
| On demand | `SYNRAG configure --perfil bajo_demanda` | 2, then `synrag_mas` adds the rest | ~159 tokens |

Claude Code loads tool definitions on demand, so it does not need a profile.

## Verify from the agent

- `list_projects` lists the indexed projects.
- `search_desktop` with a function name the user knows returns its definition first.

## Removing it

The user removes SynRAG with `SYNRAG uninstall` (it only removes what the installer added; `SYNRAG uninstall --dry-run` previews it). Deleting the engine folder afterwards is optional and up to them; the README explains it.

## Network access

This skill makes no network calls. The only URL it mentions is the project's GitHub page, for the user to read the README and the source. SynRAG itself runs locally and only reaches the network if the user configures the optional Gemini tools with their own key.
