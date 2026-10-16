#!/usr/bin/env python3
"""
Hook para Bash en Claude Code (soporta PreToolUse y PostToolUse).

Modos:
  1. PostToolUse (recomendado para salidas largas):
     Inspecciona la salida devuelta por Bash. Si supera el umbral configurado
     (por defecto 200 lineas o 12.000 caracteres), la reemplaza mediante
     `updatedToolOutput` por la version compactada (primeras 40 lineas, errores con
     +/- 2 de contexto, ultimas 60 lineas y ruta a la salida completa en cache).
     Por debajo del umbral pasa intacta.

  2. PreToolUse:
     Para modo ruidosos o envoltura previa, envuelve con `set -o pipefail`
     excluyendo de forma estricta comandos interactivos o que cambian el estado
     de la shell (cd, export, source, editores, ssh sin comando remoto, etc.).
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent))
import filtro

PATRONES_RUIDOSOS = [
    # npm / pnpm / yarn / bun (install, build, test, ci, add, run build, run test)
    r'\b(?:npm|pnpm|yarn|bun)\s+(?:install|i|add|ci|build|test|run\s+(?:build|test))\b',
    # pip / pip3 / python -m pip
    r'\b(?:pip|pip3)\s+(?:install|sync)\b',
    r'\bpython(?:\d+(?:\.\d+)?)?\s+-m\s+pip\s+install\b',
    # uv
    r'\buv\s+(?:sync|pip\s+install|run\s+pytest|run\s+cargo)\b',
    # cargo
    r'\bcargo\s+(?:build|test|run|check)\b',
    # pytest / python -m pytest
    r'\bpytest\b',
    r'\bpython(?:\d+(?:\.\d+)?)?\s+-m\s+pytest\b',
    # tsc
    r'\btsc\b',
    # docker build / docker-compose build
    r'\bdocker\s+(?:build|buildx\s+build)\b',
    r'\bdocker-compose\s+build\b',
    # make / gradle / mvn
    r'\bmake\b',
    r'\b(?:\./)?gradlew?\b',
    r'\b(?:\./)?mvnw?\b',
]

RE_SHELL_STATE_BUILTINS = re.compile(
    r'(?:^|[;&|\n]\s*)(?:cd|export|source|\.|alias|ulimit|set)(?:\s+|$)'
)

RE_PIPES_PAGING = re.compile(
    r'\|\s*(?:head|tail|less)\b'
)

RE_FILE_REDIRECTION = re.compile(
    r'(?:>>|&>|(?<![0-9&])>|[0-9]+>(?!&))\s*[\w\.\/~-]'
)

RE_HEREDOC = re.compile(
    r'<<'
)

RE_BACKGROUND = re.compile(
    r'&\s*$'
)

RE_NOHUP = re.compile(
    r'(?:^|[;&|\n]\s*)nohup\b'
)

RE_INTERACTIVE_EDITORS = re.compile(
    r'(?:^|[;&|\n]\s*)(?:vim|vi|nano|less|top|htop|man)\b'
)


def es_comando_ruidoso(cmd: str) -> bool:
    """Comprueba si el comando pertenece a la lista de herramientas ruidosas."""
    return any(re.search(pat, cmd, re.IGNORECASE) for pat in PATRONES_RUIDOSOS)


def ya_esta_filtrado_o_redirigido(cmd: str) -> bool:
    """
    Comprueba si el comando ya incluye filtros de salida (| head, | tail, | grep, | rg,
    synrag-filtrar) o redireccion a archivo (> o >>).
    """
    if re.search(r'\|\s*(?:head|tail|grep|rg|synrag-filtrar|SYNRAG\s+filtrar)\b', cmd):
        return True

    if re.search(r'(?:>>|(?<!&)>)\s*[\w\.\/~-]', cmd):
        return True

    return False


def es_ssh_sin_comando_remoto(cmd: str) -> bool:
    """Determina si un comando ssh no incluye un comando remoto a ejecutar."""
    import shlex
    try:
        tokens = shlex.split(cmd.strip())
    except Exception:
        tokens = cmd.strip().split()
    if not tokens:
        return False
    primer = Path(tokens[0]).name
    if primer != "ssh":
        return False

    ssh_opts_with_arg = {
        "-b", "-c", "-D", "-E", "-e", "-F", "-I", "-i", "-J", "-L", "-l",
        "-m", "-O", "-o", "-p", "-Q", "-R", "-S", "-W", "-w"
    }
    i = 1
    destino = None
    while i < len(tokens):
        tok = tokens[i]
        if tok == "--":
            i += 1
            if i < len(tokens):
                destino = tokens[i]
                i += 1
            break
        if tok.startswith("-"):
            opt = tok[:2]
            if opt in ssh_opts_with_arg:
                if len(tok) == 2:
                    i += 2
                else:
                    i += 1
            else:
                i += 1
        else:
            destino = tok
            i += 1
            break

    if destino is None or i >= len(tokens):
        return True
    return False


def es_repl_sin_argumentos(cmd: str) -> bool:
    """Detecta llamadas interactivas a python o node sin script ni flags ejecutables."""
    import shlex
    try:
        tokens = shlex.split(cmd.strip())
    except Exception:
        tokens = cmd.strip().split()
    if not tokens:
        return False
    primer = Path(tokens[0]).name
    if primer in ("python", "python3", "python2", "node"):
        resto = tokens[1:]
        if not resto:
            return True
        tiene_ejecutable = False
        for arg in resto:
            if not arg.startswith("-") or arg.startswith(("-c", "-m", "-e")):
                tiene_ejecutable = True
                break
        if not tiene_ejecutable:
            return True
    return False


def debe_excluir_de_envoltura(cmd: str) -> bool:
    """
    Comprueba si un comando debe ser excluido de ser envuelto.
    Excluye:
      - Comandos que cambian estado de shell: cd, export, source, ., alias, ulimit, set
      - Filtros/paginadores existentes: | head, | tail, | less
      - Redireccion a archivo (> o >>) y heredoc (<<)
      - Segundo plano (& final) y nohup
      - Editores o REPL: vim, nano, less, top, python/node sin argumentos, ssh sin comando remoto
    """
    c = cmd.strip()
    if not c:
        return True
    if RE_SHELL_STATE_BUILTINS.search(c):
        return True
    if RE_PIPES_PAGING.search(c):
        return True
    if RE_FILE_REDIRECTION.search(c):
        return True
    if RE_HEREDOC.search(c):
        return True
    if RE_BACKGROUND.search(c):
        return True
    if RE_NOHUP.search(c):
        return True
    if RE_INTERACTIVE_EDITORS.search(c):
        return True
    if es_repl_sin_argumentos(c):
        return True
    if es_ssh_sin_comando_remoto(c):
        return True
    return False


def envolver_comando(cmd: str) -> str:
    """Envuelve el comando conservando el codigo de salida con pipefail."""
    return f"( set -o pipefail; ( {cmd} ) 2>&1 | synrag-filtrar )"


def envolver_comando_largo(cmd: str) -> str:
    """Envuelve el comando para salidas largas conservando el codigo de salida con pipefail."""
    return f"( set -o pipefail; ( {cmd} ) 2>&1 | synrag-filtrar --largas )"


def procesar_hook(datos: Dict[str, Any]) -> Dict[str, Any]:
    """
    Procesa la carga util de eventos PreToolUse o PostToolUse.
    Devuelve diccionario con hookSpecificOutput si se modifica, o vacio si pasa intacto.
    """
    hook_event = str(datos.get("hook_event_name") or datos.get("hookEventName") or "")
    tool_name = str(datos.get("tool_name") or datos.get("toolName") or datos.get("tool") or "")

    if tool_name and tool_name.lower() not in ("bash", ""):
        return {}

    tool_input = datos.get("tool_input") or datos.get("toolInput") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    comando = str(tool_input.get("command") or tool_input.get("cmd") or "")

    # Evento PostToolUse: inspecciona la salida real tras la ejecucion
    if hook_event.lower() == "posttooluse":
        tool_response = datos.get("tool_response") or datos.get("toolResponse")
        if tool_response is None:
            return {}

        if isinstance(tool_response, dict):
            stdout_orig = str(tool_response.get("stdout", ""))
        elif isinstance(tool_response, str):
            stdout_orig = tool_response
        else:
            return {}

        umbral_lineas, umbral_chars = filtro.obtener_umbrales()
        num_lineas = len(stdout_orig.splitlines())
        num_chars = len(stdout_orig)

        if num_lineas <= umbral_lineas and num_chars <= umbral_chars:
            return {}

        stdout_filtrado = filtro.filtrar_salida_larga(stdout_orig, comando=comando)
        if stdout_filtrado == stdout_orig:
            return {}

        if isinstance(tool_response, dict):
            updated_output: Dict[str, Any] = dict(tool_response)
            updated_output["stdout"] = stdout_filtrado
            updated_output.setdefault("stderr", "")
            updated_output.setdefault("interrupted", False)
            updated_output.setdefault("isImage", False)
        else:
            updated_output = {
                "stdout": stdout_filtrado,
                "stderr": "",
                "interrupted": False,
                "isImage": False,
            }

        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "updatedToolOutput": updated_output,
            }
        }

    # Evento PreToolUse: envoltura de comandos antes de ejecutar
    if not comando:
        return {}

    if os.environ.get("SYNRAG_FILTRO_MODO") == "largas":
        if debe_excluir_de_envoltura(comando):
            return {}
        comando_envuelto = envolver_comando_largo(comando)
        nuevo_input = dict(tool_input)
        nuevo_input["command"] = comando_envuelto
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "updatedInput": nuevo_input,
            }
        }

    # Modo por defecto para PreToolUse: comandos ruidosos
    if not es_comando_ruidoso(comando):
        return {}

    if ya_esta_filtrado_o_redirigido(comando):
        return {}

    comando_envuelto = envolver_comando(comando)
    nuevo_input = dict(tool_input)
    nuevo_input["command"] = comando_envuelto

    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": nuevo_input,
        }
    }


def main() -> None:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)
        datos = json.loads(raw)
    except Exception:
        sys.exit(0)

    respuesta = procesar_hook(datos)
    if respuesta:
        sys.stdout.write(json.dumps(respuesta, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    sys.exit(0)


if __name__ == "__main__":
    main()

