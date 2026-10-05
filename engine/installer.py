#!/usr/bin/env python3
"""
Instalador Universal y Auto-Configurador Multi-IA de SyntaxRAG (SYNRAG)

Detecta las IAs que de verdad estan instaladas en la maquina (Claude Code,
Google Antigravity, Gemini CLI, Codex CLI, Cursor, Windsurf, Cline / Roo Code,
Zed) y, en cada una, hace DOS cosas:

  1. Registra el servidor MCP `desktop-lancedb` (sus herramientas).
  2. Anade a sus instrucciones globales un bloque corto que le dice que use
     `search_desktop` ANTES de listar carpetas o leer archivos enteros. Sin
     esto la IA ve la herramienta pero casi nunca la elige.

Reglas de seguridad:
  - Solo toca lo que existe: nunca crea la carpeta de una IA que no esta instalada.
  - Hace copia `.bak-AAAAMMDD-HHMMSS` antes de modificar un archivo existente.
  - Si un archivo JSON no se puede leer (comentarios, formato raro) NO lo
    sobrescribe: lo omite y muestra que anadir a mano.
  - Es idempotente: ejecutarlo dos veces no duplica nada.
  - `--dry-run` muestra lo que haria sin escribir nada.

Funciona en Linux, macOS y Windows con WSL (el lanzador es un script bash).
"""

import os
import sys
import json
import shutil
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

HOME = Path.home()
OS_NAME = platform.system().lower()
BASE_DIR = Path(__file__).parent.resolve()
VENV_PYTHON = BASE_DIR / ".venv" / "bin" / "python"
if not VENV_PYTHON.exists():
    VENV_PYTHON = BASE_DIR / ".venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = Path(sys.executable)

SERVER_MCP_PY = BASE_DIR / "server_mcp.py"
SERVER_NAME = "desktop-lancedb"
DRY_RUN = "--dry-run" in sys.argv
STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")

MCP_SERVER_CONFIG: Dict[str, Any] = {
    "command": str(VENV_PYTHON),
    "args": [str(SERVER_MCP_PY)],
    "env": {"PYTHONUNBUFFERED": "1"},
}

BLOQUE_INI = "<!-- SYNRAG:BEGIN -->"
BLOQUE_FIN = "<!-- SYNRAG:END -->"
BLOQUE_INSTRUCCIONES = f"""{BLOQUE_INI}
## SyntaxRAG (SYNRAG): buscar codigo sin gastar tokens
- Para ubicar codigo, notas o configuracion usa PRIMERO la herramienta MCP `search_desktop`
  (servidor `{SERVER_NAME}`). Devuelve `ruta:linea` y el bloque sintactico completo. Despues lee
  SOLO ese tramo. No listes arboles de carpetas ni leas archivos enteros para "orientarte".
- Filtra con `project` cuando sepas el proyecto. Usa `get_file_outline` para ver el esquema de un
  archivo y `get_impact_radius` antes de cambiar un simbolo que otros archivos importan.
- Si la herramienta falla o no devuelve nada, dilo y sigue con busqueda normal; no la ignores en silencio.
{BLOQUE_FIN}
"""

# Resultado de cada intento de configuracion
OK, YA, OMITIDO, ERROR = "configurado", "ya estaba", "omitido", "error"


def _log(estado: str, que: str, detalle: str = "") -> None:
    marca = {OK: "[OK]", YA: "[=]", OMITIDO: "[--]", ERROR: "[ERROR]"}[estado]
    extra = f" ({detalle})" if detalle else ""
    print(f"  {marca} {que}{extra}")


def _escribir(path: Path, contenido: str) -> None:
    """Escribe con copia de seguridad previa (si el archivo ya existia)."""
    if DRY_RUN:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        shutil.copy2(path, path.with_name(f"{path.name}.bak-{STAMP}"))
    path.write_text(contenido, encoding="utf-8")


def _instalada(*, dirs: List[Path] = (), binarios: List[str] = ()) -> bool:
    """Una IA cuenta como instalada si existe su carpeta de configuracion o su comando."""
    return any(d.exists() for d in dirs) or any(shutil.which(b) for b in binarios)


def _registrar_json(path: Path, raiz: str = "mcpServers", entrada: Optional[Dict[str, Any]] = None) -> str:
    """Anade `desktop-lancedb` a un JSON de MCP sin pisar nada ajeno."""
    entrada = entrada or MCP_SERVER_CONFIG
    try:
        datos: Dict[str, Any] = {}
        if path.is_file():
            texto = path.read_text(encoding="utf-8")
            if texto.strip():
                try:
                    datos = json.loads(texto)
                except Exception:
                    # JSON con comentarios u otro formato: no se reescribe jamas.
                    _log(OMITIDO, str(path), "no es JSON puro; anade a mano: " + json.dumps({raiz: {SERVER_NAME: entrada}}))
                    return OMITIDO
            if not isinstance(datos, dict):
                _log(OMITIDO, str(path), "formato inesperado")
                return OMITIDO
        bloque = datos.get(raiz)
        if bloque is not None and not isinstance(bloque, dict):
            _log(OMITIDO, str(path), f"'{raiz}' no es un objeto")
            return OMITIDO
        if isinstance(bloque, dict) and bloque.get(SERVER_NAME) == entrada:
            _log(YA, str(path))
            return YA
        datos.setdefault(raiz, {})[SERVER_NAME] = entrada
        _escribir(path, json.dumps(datos, indent=2, ensure_ascii=False) + "\n")
        _log(OK, str(path), "simulado" if DRY_RUN else "")
        return OK
    except Exception as e:  # noqa: BLE001 - un fallo en una IA no debe frenar a las demas
        _log(ERROR, str(path), str(e))
        return ERROR


def _registrar_toml_codex(path: Path) -> str:
    """Codex CLI usa TOML: se anade una tabla `[mcp_servers.desktop-lancedb]` al final."""
    try:
        tabla = f"[mcp_servers.{SERVER_NAME}]"
        texto = path.read_text(encoding="utf-8") if path.is_file() else ""
        if tabla in texto:
            _log(YA, str(path))
            return YA
        nuevo = (
            texto.rstrip("\n") + ("\n\n" if texto.strip() else "")
            + f"{tabla}\ncommand = {json.dumps(str(VENV_PYTHON))}\n"
            + f"args = [{json.dumps(str(SERVER_MCP_PY))}]\n"
            + 'env = { PYTHONUNBUFFERED = "1" }\n'
        )
        _escribir(path, nuevo)
        _log(OK, str(path), "simulado" if DRY_RUN else "")
        return OK
    except Exception as e:  # noqa: BLE001
        _log(ERROR, str(path), str(e))
        return ERROR


def _inyectar_instrucciones(path: Path) -> str:
    """Inserta o actualiza el bloque SYNRAG entre marcas, sin tocar el resto del archivo."""
    try:
        real = path.resolve() if path.is_symlink() else path  # GEMINI.md suele ser enlace a CLAUDE.md
        texto = real.read_text(encoding="utf-8") if real.is_file() else ""
        if BLOQUE_INI in texto and BLOQUE_FIN in texto:
            ini = texto.index(BLOQUE_INI)
            fin = texto.index(BLOQUE_FIN) + len(BLOQUE_FIN)
            nuevo = texto[:ini] + BLOQUE_INSTRUCCIONES.rstrip("\n") + texto[fin:]
        else:
            nuevo = texto.rstrip("\n") + ("\n\n" if texto.strip() else "") + BLOQUE_INSTRUCCIONES
        if nuevo == texto:
            _log(YA, f"instrucciones en {path}")
            return YA
        _escribir(real, nuevo)
        _log(OK, f"instrucciones en {path}", "simulado" if DRY_RUN else "")
        return OK
    except Exception as e:  # noqa: BLE001
        _log(ERROR, f"instrucciones en {path}", str(e))
        return ERROR


# --------------------------------------------------------------------------
# Una funcion por IA. Cada una devuelve el nombre de la IA si quedo usando SYNRAG.
# --------------------------------------------------------------------------

def configure_claude_code() -> List[str]:
    if not _instalada(dirs=[HOME / ".claude"], binarios=["claude"]):
        return []
    # El MCP de usuario de Claude Code vive en ~/.claude.json (no en settings.json).
    r = _registrar_json(HOME / ".claude.json")
    i = _inyectar_instrucciones(HOME / ".claude" / "CLAUDE.md")
    return ["Claude Code"] if OK in (r, i) or YA in (r, i) else []


def configure_antigravity() -> List[str]:
    # Antigravity lee ~/.gemini/antigravity/mcp_config.json (clave mcpServers).
    if not _instalada(dirs=[HOME / ".gemini" / "antigravity"], binarios=["antigravity", "agy"]):
        return []
    r = _registrar_json(HOME / ".gemini" / "antigravity" / "mcp_config.json")
    i = _inyectar_instrucciones(HOME / ".gemini" / "GEMINI.md")
    return ["Google Antigravity"] if OK in (r, i) or YA in (r, i) else []


def configure_gemini_cli() -> List[str]:
    if not _instalada(binarios=["gemini"]) and not (HOME / ".gemini" / "settings.json").exists():
        return []
    r = _registrar_json(HOME / ".gemini" / "settings.json")
    i = _inyectar_instrucciones(HOME / ".gemini" / "GEMINI.md")
    return ["Gemini CLI"] if OK in (r, i) or YA in (r, i) else []


def configure_codex() -> List[str]:
    if not _instalada(dirs=[HOME / ".codex"], binarios=["codex"]):
        return []
    r = _registrar_toml_codex(HOME / ".codex" / "config.toml")
    i = _inyectar_instrucciones(HOME / ".codex" / "AGENTS.md")
    return ["Codex CLI"] if OK in (r, i) or YA in (r, i) else []


def configure_cursor() -> List[str]:
    if not _instalada(dirs=[HOME / ".cursor", HOME / ".config" / "Cursor"], binarios=["cursor"]):
        return []
    return ["Cursor"] if _registrar_json(HOME / ".cursor" / "mcp.json") in (OK, YA) else []


def configure_windsurf() -> List[str]:
    if not _instalada(dirs=[HOME / ".codeium" / "windsurf", HOME / ".config" / "Windsurf"], binarios=["windsurf"]):
        return []
    r = _registrar_json(HOME / ".codeium" / "windsurf" / "mcp_config.json")
    i = _inyectar_instrucciones(HOME / ".codeium" / "windsurf" / "memories" / "global_rules.md")
    return ["Windsurf"] if OK in (r, i) or YA in (r, i) else []


def configure_cline_vscode() -> List[str]:
    base = HOME / ".config" / "Code" / "User" / "globalStorage"
    hecho: List[str] = []
    for ext, nombre in (("saoudrizwan.claude-dev", "Cline"), ("rooveterinaryinc.roo-cline", "Roo Code")):
        if (base / ext).exists():
            if _registrar_json(base / ext / "settings" / "cline_mcp_settings.json") in (OK, YA):
                hecho.append(nombre)
    return hecho


def configure_zed() -> List[str]:
    if not _instalada(dirs=[HOME / ".config" / "zed"], binarios=["zed"]):
        return []
    entrada = {"command": {"path": str(VENV_PYTHON), "args": [str(SERVER_MCP_PY)], "env": {"PYTHONUNBUFFERED": "1"}}}
    # settings.json de Zed admite comentarios: si los tiene, _registrar_json lo omite y avisa.
    return ["Zed"] if _registrar_json(HOME / ".config" / "zed" / "settings.json", "context_servers", entrada) in (OK, YA) else []


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
    """Instalacion completa: lanzadores, autocompletado y una pasada por cada IA instalada."""
    print("=" * 80)
    print("   INSTALADOR UNIVERSAL & AUTO-CONFIGURADOR MULTI-IA (SYNTAX RAG)" + ("  [SIMULACION]" if DRY_RUN else ""))
    print("=" * 80)
    print(f"Sistema:      {platform.system()} ({platform.machine()})")
    print(f"Python:       {VENV_PYTHON}")
    print(f"Directorio:   {BASE_DIR}")
    print("-" * 80)

    if not DRY_RUN:
        install_cli_binaries()
        install_fish_completions()
        print("[OK] Lanzadores SYNRAG / synrag / syntaxrag en ~/.local/bin y autocompletado de Fish")
    else:
        print("[SIMULACION] No se crean lanzadores ni autocompletado.")

    print("\nIAs detectadas en este equipo:")
    configuradas: List[str] = []
    for configurar in (
        configure_claude_code, configure_antigravity, configure_gemini_cli, configure_codex,
        configure_cursor, configure_windsurf, configure_cline_vscode, configure_zed,
    ):
        configuradas.extend(configurar())

    print("\n" + "-" * 80)
    if configuradas:
        print(f"Usan SYNRAG ({len(configuradas)}): {', '.join(sorted(set(configuradas)))}")
        print("Reinicia cada IA para que cargue la herramienta `search_desktop`.")
    else:
        print("No se encontro ninguna IA compatible instalada. Instala una y ejecuta: SYNRAG configure")
    print("Para ver los cambios sin aplicarlos: SYNRAG configure --dry-run")
    print("=" * 80)


if __name__ == "__main__":
    run_full_installation()
