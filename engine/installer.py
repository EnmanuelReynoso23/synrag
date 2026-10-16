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

# Archivo donde Antigravity lee sus servidores MCP. La ruta vigente es ~/.gemini/config/mcp_config.json:
# esta escrita en el binario de su servidor de lenguaje y en el del CLI `agy`, y alli tenia cargado el MCP
# un `server_mcp.py` hijo del servidor de lenguaje (comprobado el 6-oct-2026). La ruta anterior,
# ~/.gemini/antigravity/mcp_config.json, solo se mantiene al dia si el archivo ya existe.
ANTIGRAVITY_MCP = HOME / ".gemini" / "config" / "mcp_config.json"
ANTIGRAVITY_MCP_ANTERIOR = HOME / ".gemini" / "antigravity" / "mcp_config.json"
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
## SyntaxRAG: buscar codigo local
- Primero `search_desktop` (da `ruta:linea`) y lee solo ese tramo; no listes arboles ni leas archivos enteros.
- Filtra con `project`; `get_file_outline` da el esquema; `get_impact_radius` antes de cambiar un simbolo.
- Si una herramienta falla, dilo y sigue con busqueda normal.
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
        # Con la pista por hook activa, el CLAUDE.md de Claude Code no lleva el bloque (ni por enlace).
        if os.path.realpath(real) == os.path.realpath(HOME / ".claude" / "CLAUDE.md") and _pista_activa():
            _log(OMITIDO, f"instrucciones en {path}", "pista por hook activa")
            return YA
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
    # Antigravity lee ~/.gemini/config/mcp_config.json (clave mcpServers); ver ANTIGRAVITY_MCP.
    if not _instalada(dirs=[HOME / ".gemini" / "antigravity"], binarios=["antigravity", "agy"]):
        return []
    destinos = [ANTIGRAVITY_MCP]
    if ANTIGRAVITY_MCP_ANTERIOR.is_file():
        destinos.append(ANTIGRAVITY_MCP_ANTERIOR)
    resultados = [_registrar_json(d) for d in destinos]
    i = _inyectar_instrucciones(HOME / ".gemini" / "GEMINI.md")
    return ["Google Antigravity"] if any(x in (OK, YA) for x in [*resultados, i]) else []


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


def configure_filtro() -> str:
    """Configura el hook PreToolUse en ~/.claude/settings.json de forma idempotente."""
    target = HOME / ".claude" / "settings.json"
    hook_cmd = f'"{VENV_PYTHON}" "{BASE_DIR / "hook_filtro.py"}"'

    try:
        datos: Dict[str, Any] = {}
        if target.is_file():
            try:
                datos = json.loads(target.read_text(encoding="utf-8"))
            except Exception as e:  # noqa: BLE001
                _log(OMITIDO, str(target), f"JSON ilegible ({e}); anade el hook a mano")
                return OMITIDO
        if not isinstance(datos, dict):
            datos = {}

        hooks = datos.setdefault("hooks", {})
        if not isinstance(hooks, dict):
            hooks = datos["hooks"] = {}

        pre_tool_use = hooks.setdefault("PreToolUse", [])
        if not isinstance(pre_tool_use, list):
            pre_tool_use = hooks["PreToolUse"] = []

        # Buscar si ya existe el matcher Bash
        for entrada in pre_tool_use:
            if isinstance(entrada, dict) and entrada.get("matcher") == "Bash":
                sub_hooks = entrada.setdefault("hooks", [])
                if isinstance(sub_hooks, list):
                    for h in sub_hooks:
                        if isinstance(h, dict) and "hook_filtro.py" in str(h.get("command", "")):
                            _log(YA, f"hook de filtro en {target}")
                            return YA
                    sub_hooks.append({"type": "command", "command": hook_cmd})
                    _escribir(target, json.dumps(datos, indent=2, ensure_ascii=False) + "\n")
                    _log(OK, f"hook de filtro anadido a {target}", "simulado" if DRY_RUN else "")
                    return OK

        # Si no existia matcher Bash
        pre_tool_use.append({
            "matcher": "Bash",
            "hooks": [
                {"type": "command", "command": hook_cmd}
            ]
        })
        _escribir(target, json.dumps(datos, indent=2, ensure_ascii=False) + "\n")
        _log(OK, f"hook de filtro configurado en {target}", "simulado" if DRY_RUN else "")
        return OK
    except Exception as e:  # noqa: BLE001
        _log(ERROR, str(target), str(e))
        return ERROR


def uninstall_filtro() -> str:
    """Quita el hook PreToolUse de ~/.claude/settings.json conservando otros hooks y configuraciones."""
    target = HOME / ".claude" / "settings.json"
    if not target.is_file():
        _log(YA, f"hook de filtro no estaba (no existe {target})")
        return YA

    try:
        datos = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(datos, dict):
            return YA
        hooks = datos.get("hooks")
        if not isinstance(hooks, dict):
            return YA
        pre_tool_use = hooks.get("PreToolUse")
        if not isinstance(pre_tool_use, list):
            return YA

        modificado = False
        nuevas_entradas = []
        for entrada in pre_tool_use:
            if isinstance(entrada, dict) and entrada.get("matcher") == "Bash":
                sub_hooks = entrada.get("hooks", [])
                if isinstance(sub_hooks, list):
                    nuevos_sub = [
                        h for h in sub_hooks
                        if not (isinstance(h, dict) and "hook_filtro.py" in str(h.get("command", "")))
                    ]
                    if len(nuevos_sub) != len(sub_hooks):
                        modificado = True
                    if nuevos_sub:
                        entrada["hooks"] = nuevos_sub
                        nuevas_entradas.append(entrada)
                else:
                    nuevas_entradas.append(entrada)
            else:
                nuevas_entradas.append(entrada)

        if not modificado:
            _log(YA, f"hook de filtro no estaba en {target}")
            return YA

        if nuevas_entradas:
            hooks["PreToolUse"] = nuevas_entradas
        else:
            del hooks["PreToolUse"]
            if not hooks:
                del datos["hooks"]

        _escribir(target, json.dumps(datos, indent=2, ensure_ascii=False) + "\n")
        _log(OK, f"hook de filtro quitado de {target}", "simulado" if DRY_RUN else "")
        return OK
    except Exception as e:  # noqa: BLE001
        _log(ERROR, str(target), str(e))
        return ERROR


def configure_filtro_largas() -> str:
    """Configura el hook PostToolUse para filtrar salidas largas en ~/.claude/settings.json de forma idempotente."""
    target = HOME / ".claude" / "settings.json"
    hook_cmd = f'"{VENV_PYTHON}" "{BASE_DIR / "hook_filtro.py"}"'

    try:
        datos: Dict[str, Any] = {}
        if target.is_file():
            try:
                datos = json.loads(target.read_text(encoding="utf-8"))
            except Exception as e:  # noqa: BLE001
                _log(OMITIDO, str(target), f"JSON ilegible ({e}); anade el hook a mano")
                return OMITIDO
        if not isinstance(datos, dict):
            datos = {}

        hooks = datos.setdefault("hooks", {})
        if not isinstance(hooks, dict):
            hooks = datos["hooks"] = {}

        post_tool_use = hooks.setdefault("PostToolUse", [])
        if not isinstance(post_tool_use, list):
            post_tool_use = hooks["PostToolUse"] = []

        # Buscar si ya existe el matcher Bash
        for entrada in post_tool_use:
            if isinstance(entrada, dict) and entrada.get("matcher") == "Bash":
                sub_hooks = entrada.setdefault("hooks", [])
                if isinstance(sub_hooks, list):
                    for h in sub_hooks:
                        if isinstance(h, dict) and "hook_filtro.py" in str(h.get("command", "")):
                            _log(YA, f"hook de filtro largas en {target}")
                            return YA
                    sub_hooks.append({"type": "command", "command": hook_cmd})
                    _escribir(target, json.dumps(datos, indent=2, ensure_ascii=False) + "\n")
                    _log(OK, f"hook de filtro largas anadido a {target}", "simulado" if DRY_RUN else "")
                    return OK

        # Si no existia matcher Bash en PostToolUse
        post_tool_use.append({
            "matcher": "Bash",
            "hooks": [
                {"type": "command", "command": hook_cmd}
            ]
        })
        _escribir(target, json.dumps(datos, indent=2, ensure_ascii=False) + "\n")
        _log(OK, f"hook de filtro largas configurado en {target}", "simulado" if DRY_RUN else "")
        return OK
    except Exception as e:  # noqa: BLE001
        _log(ERROR, str(target), str(e))
        return ERROR


def _archivo_perfil() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config") / "synrag" / "perfil"


def valor_de_perfil(args: List[str]) -> str:
    """`--perfil esencial` o `--perfil=esencial` -> "esencial" ("" si no viene)."""
    for i, a in enumerate(args):
        if a.startswith("--perfil="):
            return a.split("=", 1)[1].strip().lower()
        if a == "--perfil" and i + 1 < len(args):
            return args[i + 1].strip().lower()
    return ""


def configure_perfil(valor: str) -> str:
    """Elige que herramientas MCP expone el servidor: `esencial` (5) o `completo` (todas)."""
    if valor not in ("esencial", "completo"):
        _log(ERROR, "perfil", f"'{valor}' no existe; usa esencial o completo")
        return ERROR
    destino = _archivo_perfil()
    try:
        if destino.is_file() and destino.read_text(encoding="utf-8").strip() == valor:
            _log(YA, f"perfil de herramientas {valor} en {destino}")
            return YA
        if not DRY_RUN:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(valor + "\n", encoding="utf-8")
        _log(OK, f"perfil de herramientas {valor} en {destino}", "simulado" if DRY_RUN else "reinicia la IA para que lo cargue")
        return OK
    except Exception as e:  # noqa: BLE001
        _log(ERROR, str(destino), str(e))
        return ERROR


def uninstall_perfil() -> str:
    """Vuelve al perfil completo (todas las herramientas)."""
    destino = _archivo_perfil()
    if not destino.is_file():
        _log(YA, "perfil de herramientas completo (no habia archivo de perfil)")
        return YA
    if not DRY_RUN:
        destino.unlink()
    _log(OK, f"perfil de herramientas: quitado {destino} (vuelve a completo)", "simulado" if DRY_RUN else "")
    return OK


def uninstall_filtro_largas() -> str:
    """Quita el hook PostToolUse de ~/.claude/settings.json conservando otros hooks y configuraciones."""
    target = HOME / ".claude" / "settings.json"
    if not target.is_file():
        _log(YA, f"hook de filtro largas no estaba (no existe {target})")
        return YA

    try:
        datos = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(datos, dict):
            return YA
        hooks = datos.get("hooks")
        if not isinstance(hooks, dict):
            return YA
        post_tool_use = hooks.get("PostToolUse")
        if not isinstance(post_tool_use, list):
            return YA

        modificado = False
        nuevas_entradas = []
        for entrada in post_tool_use:
            if isinstance(entrada, dict) and entrada.get("matcher") == "Bash":
                sub_hooks = entrada.get("hooks", [])
                if isinstance(sub_hooks, list):
                    nuevos_sub = [
                        h for h in sub_hooks
                        if not (isinstance(h, dict) and "hook_filtro.py" in str(h.get("command", "")))
                    ]
                    if len(nuevos_sub) != len(sub_hooks):
                        modificado = True
                    if nuevos_sub:
                        entrada["hooks"] = nuevos_sub
                        nuevas_entradas.append(entrada)
                else:
                    nuevas_entradas.append(entrada)
            else:
                nuevas_entradas.append(entrada)

        if not modificado:
            _log(YA, f"hook de filtro largas no estaba en {target}")
            return YA

        if nuevas_entradas:
            hooks["PostToolUse"] = nuevas_entradas
        else:
            del hooks["PostToolUse"]
            if not hooks:
                del datos["hooks"]

        _escribir(target, json.dumps(datos, indent=2, ensure_ascii=False) + "\n")
        _log(OK, f"hook de filtro largas quitado de {target}", "simulado" if DRY_RUN else "")
        return OK
    except Exception as e:  # noqa: BLE001
        _log(ERROR, str(target), str(e))
        return ERROR


PISTA_EVENTO = "UserPromptSubmit"


def _es_hook_pista(h: Any) -> bool:
    return isinstance(h, dict) and "hook_pista.py" in str(h.get("command", ""))


def _pista_activa() -> bool:
    """True si el hook de pista esta en ~/.claude/settings.json (en ese caso el bloque SYNRAG no va al CLAUDE.md)."""
    target = HOME / ".claude" / "settings.json"
    try:
        datos = json.loads(target.read_text(encoding="utf-8")) if target.is_file() else {}
    except Exception:  # noqa: BLE001
        return False
    hooks = datos.get("hooks") if isinstance(datos, dict) else None
    entradas = hooks.get(PISTA_EVENTO) if isinstance(hooks, dict) else None
    if not isinstance(entradas, list):
        return False
    return any(
        isinstance(e, dict) and any(_es_hook_pista(h) for h in (e.get("hooks") or []))
        for e in entradas
    )


def configure_pista() -> str:
    """Activa la pista por hook (UserPromptSubmit) y quita el bloque SYNRAG de ~/.claude/CLAUDE.md. Idempotente."""
    target = HOME / ".claude" / "settings.json"
    hook_cmd = f'"{VENV_PYTHON}" "{BASE_DIR / "hook_pista.py"}"'

    try:
        datos: Dict[str, Any] = {}
        if target.is_file():
            try:
                datos = json.loads(target.read_text(encoding="utf-8"))
            except Exception as e:  # noqa: BLE001
                _log(OMITIDO, str(target), f"JSON ilegible ({e}); anade el hook a mano")
                return OMITIDO
        if not isinstance(datos, dict):
            datos = {}

        hooks = datos.setdefault("hooks", {})
        if not isinstance(hooks, dict):
            hooks = datos["hooks"] = {}
        entradas = hooks.setdefault(PISTA_EVENTO, [])
        if not isinstance(entradas, list):
            entradas = hooks[PISTA_EVENTO] = []

        if _pista_activa():
            estado_hook = YA
            _log(YA, f"hook de pista en {target}")
        else:
            entradas.append({"hooks": [{"type": "command", "command": hook_cmd}]})
            _escribir(target, json.dumps(datos, indent=2, ensure_ascii=False) + "\n")
            estado_hook = OK
            _log(OK, f"hook de pista anadido a {target}", "simulado" if DRY_RUN else "")

        estado_bloque = _quitar_bloque(HOME / ".claude" / "CLAUDE.md")
        if ERROR in (estado_hook, estado_bloque):
            return ERROR
        return OK if OK in (estado_hook, estado_bloque) else YA
    except Exception as e:  # noqa: BLE001
        _log(ERROR, str(target), str(e))
        return ERROR


def _quitar_hook_pista() -> str:
    """Quita solo el hook de pista de ~/.claude/settings.json, conservando el resto."""
    target = HOME / ".claude" / "settings.json"
    if not target.is_file():
        _log(YA, f"hook de pista no estaba (no existe {target})")
        return YA

    try:
        datos = json.loads(target.read_text(encoding="utf-8"))
        hooks = datos.get("hooks") if isinstance(datos, dict) else None
        entradas = hooks.get(PISTA_EVENTO) if isinstance(hooks, dict) else None
        if not isinstance(entradas, list):
            _log(YA, f"hook de pista no estaba en {target}")
            return YA

        modificado = False
        nuevas_entradas = []
        for entrada in entradas:
            sub_hooks = entrada.get("hooks") if isinstance(entrada, dict) else None
            if not isinstance(sub_hooks, list) or not any(_es_hook_pista(h) for h in sub_hooks):
                nuevas_entradas.append(entrada)
                continue
            modificado = True
            restantes = [h for h in sub_hooks if not _es_hook_pista(h)]
            if restantes:
                entrada["hooks"] = restantes
                nuevas_entradas.append(entrada)

        if not modificado:
            _log(YA, f"hook de pista no estaba en {target}")
            return YA

        if nuevas_entradas:
            hooks[PISTA_EVENTO] = nuevas_entradas
        else:
            del hooks[PISTA_EVENTO]
            if not hooks:
                del datos["hooks"]

        _escribir(target, json.dumps(datos, indent=2, ensure_ascii=False) + "\n")
        _log(OK, f"hook de pista quitado de {target}", "simulado" if DRY_RUN else "")
        return OK
    except Exception as e:  # noqa: BLE001
        _log(ERROR, str(target), str(e))
        return ERROR


def uninstall_pista() -> str:
    """Desactiva la pista: quita el hook y vuelve a poner el bloque SYNRAG en ~/.claude/CLAUDE.md."""
    estado_hook = _quitar_hook_pista()
    estado_bloque = YA
    if (HOME / ".claude").is_dir():
        estado_bloque = _inyectar_instrucciones(HOME / ".claude" / "CLAUDE.md")
    if ERROR in (estado_hook, estado_bloque):
        return ERROR
    return OK if OK in (estado_hook, estado_bloque) else YA


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

    filtrar_script = f"""#!/usr/bin/env bash
# SyntaxRAG Terminal Filter Launcher
exec "{VENV_PYTHON}" "{BASE_DIR / 'cli.py'}" filtrar "$@"
"""
    for name in ["synrag-filtrar", "SYNRAG-filtrar"]:
        target = local_bin / name
        target.write_text(filtrar_script, encoding="utf-8")
        target.chmod(0o755)

    return True


def install_fish_completions() -> bool:
    """Instala autocompletado en Fish Shell."""
    fish_dir = HOME / ".config" / "fish" / "completions"
    fish_dir.mkdir(parents=True, exist_ok=True)

    completion_content = """# Autocompletado para SyntaxRAG (SYNRAG)
complete -c synrag -c SYNRAG -f

# Subcomandos principales
complete -c synrag -c SYNRAG -n "__fish_use_subcommand" -a "stats" -d "Uso del buscador, latencia y fragmentos"
complete -c synrag -c SYNRAG -n "__fish_use_subcommand" -a "info" -d "Dashboard de arquitectura y rutas"
complete -c synrag -c SYNRAG -n "__fish_use_subcommand" -a "index" -d "Reindexar repositorios con Tree-sitter"
complete -c synrag -c SYNRAG -n "__fish_use_subcommand" -a "watch" -d "Ver el log del observador de cambios"
complete -c synrag -c SYNRAG -n "__fish_use_subcommand" -a "outline" -d "Esquema sintactico (firmas y rangos de linea)"
complete -c synrag -c SYNRAG -n "__fish_use_subcommand" -a "impact" -d "Consultar grafo de impacto de un simbolo"
complete -c synrag -c SYNRAG -n "__fish_use_subcommand" -a "configure" -d "Auto-configurar todas las IAs del sistema"
complete -c synrag -c SYNRAG -n "__fish_use_subcommand" -a "filtrar" -d "Filtrar salida de terminal ruidosa"
complete -c synrag -c SYNRAG -n "__fish_use_subcommand" -a "claude" -d "Lanzar Claude Code con MCP integrado"
complete -c synrag -c SYNRAG -n "__fish_use_subcommand" -a "agy" -d "Lanzar Antigravity CLI con MCP integrado"

# Opciones
complete -c synrag -c SYNRAG -l project -d "Filtrar por proyecto especifico"
complete -c synrag -c SYNRAG -l help -s h -d "Mostrar ayuda"
"""

    (fish_dir / "synrag.fish").write_text(completion_content, encoding="utf-8")
    (fish_dir / "SYNRAG.fish").write_text(completion_content, encoding="utf-8")
    return True


# --------------------------------------------------------------------------
# Desinstalacion: deshace solo lo que escribio este instalador
# --------------------------------------------------------------------------

def _quitar_json(path: Path, raiz: str = "mcpServers") -> str:
    try:
        if not path.is_file():
            return YA
        datos = json.loads(path.read_text(encoding="utf-8"))
        bloque = datos.get(raiz) if isinstance(datos, dict) else None
        if not isinstance(bloque, dict) or SERVER_NAME not in bloque:
            return YA
        del bloque[SERVER_NAME]
        _escribir(path, json.dumps(datos, indent=2, ensure_ascii=False) + "\n")
        _log(OK, f"quitado de {path}")
        return OK
    except Exception as e:  # noqa: BLE001 - JSON ilegible: no se toca
        _log(OMITIDO, str(path), f"no se pudo leer ({e}); quita '{SERVER_NAME}' a mano")
        return OMITIDO


def _quitar_toml_codex(path: Path) -> str:
    try:
        if not path.is_file():
            return YA
        lineas = path.read_text(encoding="utf-8").split("\n")
        tabla = f"[mcp_servers.{SERVER_NAME}]"
        if tabla not in lineas:
            return YA
        i = lineas.index(tabla)
        j = i + 1
        while j < len(lineas) and not lineas[j].startswith("["):
            j += 1
        nuevo = lineas[:i] + lineas[j:]
        while len(nuevo) > 1 and nuevo[i - 1:i] == [""] and (i >= len(nuevo) or nuevo[i:i + 1] == [""]):
            del nuevo[i - 1]
            i -= 1
        _escribir(path, "\n".join(nuevo).rstrip("\n") + "\n")
        _log(OK, f"quitado de {path}")
        return OK
    except Exception as e:  # noqa: BLE001
        _log(ERROR, str(path), str(e))
        return ERROR


def _quitar_bloque(path: Path) -> str:
    try:
        real = path.resolve() if path.is_symlink() else path
        if not real.is_file():
            return YA
        texto = real.read_text(encoding="utf-8")
        if BLOQUE_INI not in texto or BLOQUE_FIN not in texto:
            return YA
        ini = texto.index(BLOQUE_INI)
        fin = texto.index(BLOQUE_FIN) + len(BLOQUE_FIN)
        nuevo = (texto[:ini].rstrip("\n") + "\n" + texto[fin:].lstrip("\n")).strip("\n")
        _escribir(real, nuevo + "\n" if nuevo else "")
        _log(OK, f"instrucciones quitadas de {path}")
        return OK
    except Exception as e:  # noqa: BLE001
        _log(ERROR, f"instrucciones en {path}", str(e))
        return ERROR


def run_uninstall() -> None:
    """Quita el servidor MCP, el bloque de instrucciones y los lanzadores. No borra el motor."""
    print("=" * 80)
    print("   DESINSTALANDO SYNRAG DE TUS IAs" + ("  [SIMULACION]" if DRY_RUN else ""))
    print("=" * 80)
    cline = HOME / ".config" / "Code" / "User" / "globalStorage"
    for ruta, raiz in (
        (HOME / ".claude.json", "mcpServers"),
        (ANTIGRAVITY_MCP, "mcpServers"),
        (ANTIGRAVITY_MCP_ANTERIOR, "mcpServers"),
        (HOME / ".gemini" / "settings.json", "mcpServers"),
        (HOME / ".cursor" / "mcp.json", "mcpServers"),
        (HOME / ".codeium" / "windsurf" / "mcp_config.json", "mcpServers"),
        (cline / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json", "mcpServers"),
        (cline / "rooveterinaryinc.roo-cline" / "settings" / "cline_mcp_settings.json", "mcpServers"),
        (HOME / ".config" / "zed" / "settings.json", "context_servers"),
    ):
        _quitar_json(ruta, raiz)
    _quitar_toml_codex(HOME / ".codex" / "config.toml")
    for ruta in (
        HOME / ".claude" / "CLAUDE.md",
        HOME / ".gemini" / "GEMINI.md",
        HOME / ".codex" / "AGENTS.md",
        HOME / ".codeium" / "windsurf" / "memories" / "global_rules.md",
    ):
        _quitar_bloque(ruta)
    uninstall_filtro()
    uninstall_filtro_largas()
    _quitar_hook_pista()
    if not DRY_RUN:
        for nombre in ("SYNRAG", "synrag", "syntaxrag"):
            lanzador = HOME / ".local" / "bin" / nombre
            if lanzador.is_file() and "SyntaxRAG Universal CLI Launcher" in lanzador.read_text(encoding="utf-8", errors="ignore"):
                lanzador.unlink()
        for nombre in ("synrag-filtrar", "SYNRAG-filtrar"):
            lanzador = HOME / ".local" / "bin" / nombre
            if lanzador.is_file() and "SyntaxRAG Terminal Filter Launcher" in lanzador.read_text(encoding="utf-8", errors="ignore"):
                lanzador.unlink()
        for nombre in ("synrag.fish", "SYNRAG.fish"):
            comp = HOME / ".config" / "fish" / "completions" / nombre
            if comp.is_file() and "Autocompletado para SyntaxRAG" in comp.read_text(encoding="utf-8", errors="ignore"):
                comp.unlink()
    print("-" * 80)
    print("Listo. Reinicia tus IAs. Para borrar tambien el motor y su indice:")
    print(f"  rm -rf {BASE_DIR}")
    print("=" * 80)


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
    if any(a == "--perfil" or a.startswith("--perfil=") for a in sys.argv):
        if "--uninstall" in sys.argv or "uninstall" in sys.argv:
            uninstall_perfil()
        else:
            configure_perfil(valor_de_perfil(sys.argv))
    elif "--conciso" in sys.argv:
        import conciso
        if "--uninstall" in sys.argv or "uninstall" in sys.argv:
            conciso.desactivar()
        else:
            conciso.activar()
    elif "--filtro-largas" in sys.argv:
        if "--uninstall" in sys.argv or "uninstall" in sys.argv:
            uninstall_filtro_largas()
        else:
            configure_filtro_largas()
    elif "--filtro" in sys.argv or "--filtro-terminal" in sys.argv:
        if "--uninstall" in sys.argv or "uninstall" in sys.argv:
            uninstall_filtro()
        else:
            configure_filtro()
    elif "--pista" in sys.argv:
        if "--uninstall" in sys.argv or "uninstall" in sys.argv:
            uninstall_pista()
        else:
            configure_pista()
    elif "--uninstall" in sys.argv:
        run_uninstall()
    else:
        run_full_installation()

