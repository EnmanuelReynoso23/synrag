# SynRAG plugin for Claude Code

Adds the `synrag` skill, which tells Claude to locate code with SynRAG's MCP tools (exact definition, callers, impact radius, related tests) before reading or editing files.

The plugin does not install the engine. Install it once with:

```bash
curl -sSL https://raw.githubusercontent.com/EnmanuelReynoso23/synrag/main/install.sh | bash
```

Then add the plugin:

```bash
claude plugin marketplace add EnmanuelReynoso23/synrag
claude plugin install synrag@synrag
```

More: https://github.com/EnmanuelReynoso23/synrag
