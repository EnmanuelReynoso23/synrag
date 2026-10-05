#!/usr/bin/env python3
"""
Instalador Universal y Auto-Configurador Multi-IA de SyntaxRAG (SYNRAG)
Detecta automaticamente todas las IAs instaladas en la maquina
(Claude Code, Google Antigravity, Cursor, Windsurf, Cline / VS Code, Zed)
e inyecta el servidor MCP desktop-lancedb en cada una sin configuracion manual.
Funciona de forma transparente en Linux, macOS y Windows (WSL/nativo).
"""

import os
import sys
import json
import shutil
import platform
from pathlib import Path
from typing import Dict, Any, List, Tuple

HOME = Path.home()
OS_NAME = platform.system().lower()
BASE_DIR = Path(__file__).parent.resolve()
VENV_PYTHON = BASE_DIR / ".venv" / "bin" / "python"
if not VENV_PYTHON.exists():
    VENV_PYTHON = BASE_DIR / ".venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = Path(sys.executable)

SERVER_MCP_PY = BASE_DIR / "server_mcp.py"

MCP_SERVER_CONFIG = {
    "command": str(VENV_PYTHON),
    "args": [str(SERVER_MCP_PY)],
    "env": {
        "PYTHONUNBUFFERED": "1"
    }
}


def _update_json_config(file_path: Path, root_key: str = "mcpServers") -> bool:
    """Inyecta desktop-lancedb de forma segura en un archivo JSON."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        data: Dict[str, Any] = {}
        if file_path.is_file():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}

        if root_key not in data or not isinstance(data[root_key], dict):
            data[root_key] = {}

        data[root_key]["desktop-lancedb"] = MCP_SERVER_CONFIG
        file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return True
    except Exception as e:
        print(f"[ERROR] No se pudo configurar {file_path}: {e}")
        return False


def configure_claude_code() -> List[str]:
    """Configura Claude Code en ~/.claude.json y ~/.claude/settings.json."""
    configured = []
    targets = [
        HOME / ".claude.json",
        HOME / ".claude" / "settings.json",
    ]
    for target in targets:
        if _update_json_config(target, "mcpServers"):
            configured.append(f"Claude Code ({target.name})")
    return configured


def configure_antigravity() -> List[str]:
    """Configura Google Antigravity en ~/.gemini/antigravity."""
    configured = []
    ag_mcp_dir = HOME / ".gemini" / "antigravity" / "mcp" / "desktop-lancedb"
    ag_mcp_dir.mkdir(parents=True, exist_ok=True)

    # Actualizar o crear tool schemas si no existen
    tools_def = {
        "search_desktop": {
            "name": "search_desktop",
            "description": "Busca codigo o conceptos con Tree-sitter AST y FlashRank neural en CPU.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Consulta de busqueda"},
                    "limit": {"type": "integer", "default": 5},
                    "project": {"type": "string", "default": ""}
                },
                "required": ["query"]
            }
        },
        "get_file_outline": {
            "name": "get_file_outline",
            "description": "Devuelve el esquema sintactico de un archivo en ~50 tokens.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "project": {"type": "string", "default": ""}
                },
                "required": ["file_path"]
            }
        },
        "get_impact_radius": {
            "name": "get_impact_radius",
            "description": "Calcula el radio de impacto y dependencias antes de editar codigo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "project": {"type": "string", "default": ""}
                },
                "required": ["symbol"]
            }
        },
        "find_related_tests": {
            "name": "find_related_tests",
            "description": "Localiza los archivos de pruebas asociados a un archivo o simbolo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_or_symbol": {"type": "string"}
                },
                "required": ["file_or_symbol"]
            }
        },
        "get_savings_report": {
            "name": "get_savings_report",
            "description": "Devuelve el reporte historico de ahorro de tokens y costos.",
            "parameters": {"type": "object", "properties": {}}
        }
    }

    for name, schema in tools_def.items():
        schema_file = ag_mcp_dir / f"{name}.json"
        schema_file.write_text(json.dumps(schema, indent=2), encoding="utf-8")

    configured.append("Google Antigravity (~/.gemini/antigravity/mcp/desktop-lancedb)")
    return configured


def configure_cursor() -> List[str]:
    """Configura Cursor IDE."""
    configured = []
    targets = [
        HOME / ".cursor" / "mcp.json",
        HOME / ".config" / "Cursor" / "User" / "globalStorage" / "mcp.json",
        HOME / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "mcp.json",
    ]
    for target in targets:
        if target.parent.exists() or target.exists():
            if _update_json_config(target, "mcpServers"):
                configured.append(f"Cursor IDE ({target})")
    return configured


def configure_windsurf() -> List[str]:
    """Configura Windsurf / Codeium."""
    configured = []
    targets = [
        HOME / ".codeium" / "windsurf" / "mcp_config.json",
        HOME / ".config" / "Windsurf" / "mcp_config.json",
    ]
    for target in targets:
        if target.parent.exists() or target.exists():
            if _update_json_config(target, "mcpServers"):
                configured.append(f"Windsurf ({target})")
    return configured


def configure_cline_vscode() -> List[str]:
    """Configura Cline, Roo Code y extensiones MCP de VS Code."""
    configured = []
    targets = [
        HOME / ".config" / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json",
        HOME / ".config" / "Code" / "User" / "globalStorage" / "rooveterinaryinc.roo-cline" / "settings" / "cline_mcp_settings.json",
        HOME / ".vscode" / "mcp.json",
    ]
    for target in targets:
        if target.parent.exists() or target.exists():
            if _update_json_config(target, "mcpServers"):
                configured.append(f"VS Code / Cline ({target.name})")
    return configured


def configure_zed() -> List[str]:
    """Configura Zed Editor."""
    configured = []
    target = HOME / ".config" / "zed" / "settings.json"
    if target.parent.exists() or target.exists():
        if _update_json_config(target, "context_servers"):
            configured.append("Zed Editor (~/.config/zed/settings.json)")
    return configured


def install_cli_binaries() -> bool:
    """Crea los binarios globales SYNRAG y synrag en ~/.local/bin."""
    local_bin = HOME / ".local" / "bin"
    local_bin.mkdir(parents=True, exist_ok=True)

    synrag_script = f"""#!/usr/bin/env bash
# SyntaxRAG Universal CLI Launcher
exec "{VENV_PYTHON}" "{BASE_DIR / 'cli.py'}" "$@"
"""

    for name in ["SYNRAG", "synrag", "syntaxrag"]:
        target = local_bin / name
        target.write_text(synrag_script, encoding="utf-8")
        target.chmod(0o755)

    return True


def install_fish_completions() -> bool:
    """Instala autocompletado en Fish Shell."""
    fish_dir = HOME / ".config" / "fish" / "completions"
    fish_dir.mkdir(parents=True, exist_ok=True)

    completion_content = """# Autocompletado para SyntaxRAG (SYNRAG)
complete -c synrag -c SYNRAG -f

# Subcomandos principales
complete -c synrag -c SYNRAG -n "__fish_use_subcommand" -a "stats" -d "Metricas de ahorro de tokens y latencia"
complete -c synrag -c SYNRAG -n "__fish_use_subcommand" -a "info" -d "Dashboard de arquitectura y rutas"
complete -c synrag -c SYNRAG -n "__fish_use_subcommand" -a "index" -d "Reindexar repositorios con Tree-sitter"
complete -c synrag -c SYNRAG -n "__fish_use_subcommand" -a "watch" -d "Ver log del demonio reactivo"
complete -c synrag -c SYNRAG -n "__fish_use_subcommand" -a "outline" -d "Esquema sintactico de un archivo en ~50 tokens"
complete -c synrag -c SYNRAG -n "__fish_use_subcommand" -a "impact" -d "Consultar grafo de impacto de un simbolo"
complete -c synrag -c SYNRAG -n "__fish_use_subcommand" -a "configure" -d "Auto-configurar todas las IAs del sistema"
complete -c synrag -c SYNRAG -n "__fish_use_subcommand" -a "claude" -d "Lanzar Claude Code con MCP integrado"
complete -c synrag -c SYNRAG -n "__fish_use_subcommand" -a "agy" -d "Lanzar Antigravity CLI con MCP integrado"

# Opciones
complete -c synrag -c SYNRAG -l project -d "Filtrar por proyecto especifico"
complete -c synrag -c SYNRAG -l help -s h -d "Mostrar ayuda"
"""

    (fish_dir / "synrag.fish").write_text(completion_content, encoding="utf-8")
    (fish_dir / "SYNRAG.fish").write_text(completion_content, encoding="utf-8")
    return True


def run_full_installation() -> None:
    """Ejecuta la instalacion completa y auto-configuracion multi-IA."""
    print("================================================================================")
    print("         INSTALADOR UNIVERSAL & AUTO-CONFIGURADOR MULTI-IA (SYNTAX RAG)         ")
    print("================================================================================")
    print(f"Sistema Operativo: {platform.system()} ({platform.machine()})")
    print(f"Python Runtime:    {VENV_PYTHON}")
    print(f"Directorio Core:   {BASE_DIR}")
    print("--------------------------------------------------------------------------------")

    # 1. Instalar binarios globales
    install_cli_binaries()
    print("[OK] Binarios CLI instalados en ~/.local/bin (SYNRAG, synrag, syntaxrag)")

    # 2. Instalar autocompletado en Fish
    install_fish_completions()
    print("[OK] Autocompletado instalado en ~/.config/fish/completions")

    # 3. Detectar y auto-configurar IAs instaladas
    print("\nDetectando y configurando IAs instaladas en este equipo:")
    all_configured = []

    all_configured.extend(configure_claude_code())
    all_configured.extend(configure_antigravity())
    all_configured.extend(configure_cursor())
    all_configured.extend(configure_windsurf())
    all_configured.extend(configure_cline_vscode())
    all_configured.extend(configure_zed())

    for app in all_configured:
        print(f"  [OK] Integrado exitosamente: {app}")

    print("\n--------------------------------------------------------------------------------")
    print("INSTALACION COMPLETADA EXITOSAMENTE:")
    print(f"Total IAs configuradas automaticamente: {len(all_configured)}")
    print("Cada vez que abras Claude Code, Antigravity, Cursor o Windsurf,")
    print("utilizaran SyntaxRAG de forma nativa con cero consumo de tokens de API.")
    print("================================================================================")


if __name__ == "__main__":
    run_full_installation()
