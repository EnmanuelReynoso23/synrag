"""
tools/runner_tools.py - Herramientas de ejecucion y filtrado de consola.
Eliminan los volcados masivos de terminal (builds, tests, linters, logs) transformandolos en resumenes quirurgicos.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple


def _resolve_cwd(cwd: str = "") -> Path:
    if cwd:
        p = Path(cwd).expanduser().resolve()
        if p.exists():
            return p if p.is_dir() else p.parent
    return Path.cwd()


def _sanitize_output(text: str, target_dir: Path) -> str:
    """Elimina rutas absolutas locales y del usuario para portabilidad y privacidad."""
    s_dir = str(target_dir)
    if s_dir in text:
        text = text.replace(s_dir + "/", "").replace(s_dir, ".")
    home = str(Path.home())
    if home in text and home != "/":
        text = text.replace(home, "~")
    return text


def _find_binary(name: str, target_dir: Path, is_node: bool = False) -> Optional[str]:
    """Busca un ejecutable en entornos virtuales locales, node_modules o PATH."""
    if is_node:
        local_bin = target_dir / "node_modules" / ".bin" / name
        if local_bin.is_file() and os.access(local_bin, os.X_OK):
            return str(local_bin)
        which = shutil.which(name)
        if which:
            return which
        return None

    # Entornos virtuales locales de Python
    for venv_name in (".venv", "venv", "env"):
        cand = target_dir / venv_name / "bin" / name
        if cand.is_file() and os.access(cand, os.X_OK):
            return str(cand)

    # PATH general
    which = shutil.which(name)
    if which:
        return which

    # Entorno del ejecutable Python actual (e.g. SynRAG venv)
    synrag_bin = Path(sys.executable).parent / name
    if synrag_bin.is_file() and os.access(synrag_bin, os.X_OK):
        return str(synrag_bin)

    return None


def _resolve_test_command(test_command: str, target_dir: Path) -> Tuple[str, Optional[str]]:
    """Resuelve o auto-detecta el comando de pruebas a ejecutar."""
    cmd = test_command.strip()
    if cmd:
        tokens = cmd.split()
        first = tokens[0]
        # Si el comando invoca pytest pero no esta en PATH global, buscar en venv
        if first == "pytest" and not shutil.which("pytest"):
            bin_path = _find_binary("pytest", target_dir)
            if bin_path:
                tokens[0] = f'"{bin_path}"'
                return " ".join(tokens), None
            else:
                tokens[0] = f'"{sys.executable}" -m pytest'
                return " ".join(tokens), None
        elif first in ("vitest", "jest") and not shutil.which(first):
            bin_path = _find_binary(first, target_dir, is_node=True)
            if bin_path:
                tokens[0] = f'"{bin_path}"'
                return " ".join(tokens), None
            elif not (target_dir / "node_modules").is_dir():
                return "", f"[SynRAG Tests] No se detectó node_modules ni {first} instalado. Ejecuta 'npm install' o 'pnpm install' primero."
        return cmd, None

    # Auto-deteccion cuando test_command viene vacio
    is_node = (target_dir / "package.json").exists()
    is_py = (
        (target_dir / "pyproject.toml").exists()
        or (target_dir / "setup.cfg").exists()
        or (target_dir / "setup.py").exists()
        or (target_dir / "pytest.ini").exists()
        or (target_dir / "tests").is_dir()
        or any(target_dir.glob("test_*.py"))
    )

    if is_py:
        bin_path = _find_binary("pytest", target_dir)
        if bin_path:
            return f'"{bin_path}" -q', None
        return f'"{sys.executable}" -m pytest -q', None

    if is_node:
        vitest_bin = _find_binary("vitest", target_dir, is_node=True)
        if vitest_bin:
            return f'"{vitest_bin}" run', None
        jest_bin = _find_binary("jest", target_dir, is_node=True)
        if jest_bin:
            return f'"{jest_bin}"', None
        if not (target_dir / "node_modules").is_dir():
            return "", "[SynRAG Tests] No se detectó node_modules ni un ejecutor (vitest/jest) instalado. Ejecuta 'npm install' o 'pnpm install' primero."
        return "", "[SynRAG Tests] Se detectó package.json pero no vitest ni jest en dependencias locales."

    return "", "[SynRAG Tests] No se detectó un ejecutor de pruebas (pytest, vitest, jest) en este directorio. Especifica 'test_command'."


def _extract_test_failures(salida: str) -> List[str]:
    """Extrae quirúrgicamente nombres de tests fallidos, causa y resumen."""
    lineas = salida.splitlines()
    relevantes = []

    resumen_fallos = []
    for l in lineas:
        l_strip = l.strip()
        if re.match(r"^(FAILED|FAIL|ERROR)\s+", l_strip) or re.match(r"^✕\s+", l_strip):
            resumen_fallos.append(l_strip)

    patrones_fallo = [
        re.compile(r"^_{3,}\s+.*\s+_{3,}$"),          # ___ test_name ___
        re.compile(r"^\s*>\s+"),                       # >   assert ...
        re.compile(r"^\s*E\s+"),                       # E   AssertionError ...
        re.compile(r"AssertionError"),
        re.compile(r"Error:"),
        re.compile(r"Expected:"),
        re.compile(r"Received:"),
        re.compile(r"ModuleNotFoundError:"),
        re.compile(r"ImportError:"),
        re.compile(r"SyntaxError:"),
        re.compile(r"^FAIL\s+"),
        re.compile(r"^\s*●\s+"),
        re.compile(r"^\s*❯\s+"),
    ]

    bloque = []
    for idx, line in enumerate(lineas):
        if any(p.search(line) for p in patrones_fallo):
            inicio = max(0, idx - 1)
            fin = min(len(lineas), idx + 4)
            for c in lineas[inicio:fin]:
                c_strip = c.strip()
                if c_strip and c_strip not in bloque and not c_strip.startswith("==="):
                    bloque.append(c_strip)

    resumen_final = ""
    for l in reversed(lineas):
        l_low = l.lower()
        if ("failed" in l_low or "errors" in l_low or "failures" in l_low) and not l.strip().startswith("==="):
            resumen_final = l.strip()
            break
        elif "===" in l and ("failed" in l_low or "passed" in l_low):
            resumen_final = l.strip("= ").strip()
            break

    vistos = set()
    for f in resumen_fallos:
        if f not in vistos:
            relevantes.append(f)
            vistos.add(f)

    for b in bloque:
        if b not in vistos:
            relevantes.append(b)
            vistos.add(b)

    if not relevantes:
        relevantes = [l.strip() for l in lineas[-15:] if l.strip()]

    resultado = relevantes[:25]
    if resumen_final and resumen_final not in resultado:
        resultado.append(resumen_final)

    return resultado


def run_test_isolated(test_command: str = "", cwd: str = "") -> str:
    """Corre un comando de pruebas y devuelve solo el resumen y los fallos."""
    target_dir = _resolve_cwd(cwd)
    try:
        cmd, error_msg = _resolve_test_command(test_command, target_dir)
        if error_msg:
            return error_msg

        res = subprocess.run(
            cmd,
            shell=True,
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=45
        )

        salida = _sanitize_output((res.stdout + "\n" + res.stderr).strip(), target_dir)

        if res.returncode == 0:
            resumen = "Tests pasaron exitosamente."
            for l in reversed(salida.splitlines()):
                if any(w in l.lower() for w in ["passed", "ok", "success", "suites"]):
                    resumen = l.strip("= ").strip()
                    break
            return f"[SynRAG Tests OK] {resumen}"

        errores_relevantes = _extract_test_failures(salida)

        out = [
            f"[SynRAG Tests FALLÓ (código {res.returncode})]:",
            "--------------------------------------------------------------------------------",
        ]
        out.extend(errores_relevantes[:25])
        out.append("--------------------------------------------------------------------------------")
        return "\n".join(out)

    except subprocess.TimeoutExpired:
        return "[SynRAG Tests] Timeout: La prueba tardó más de 45 segundos en responder."
    except Exception as e:
        return f"[SynRAG Tests] Error al ejecutar tests: {e}"


def lint_summary(files: str = "", cwd: str = "") -> str:
    """Corre el linter y devuelve solo los errores, agrupados."""
    target_dir = _resolve_cwd(cwd)
    try:
        is_node_project = (target_dir / "package.json").exists()
        oxlint_bin = _find_binary("oxlint", target_dir, is_node=True)
        eslint_bin = _find_binary("eslint", target_dir, is_node=True)
        biome_bin = _find_binary("biome", target_dir, is_node=True)

        is_py_project = (
            (target_dir / "pyproject.toml").exists()
            or (target_dir / "setup.cfg").exists()
            or (target_dir / "setup.py").exists()
            or any(target_dir.glob("*.py"))
            or (target_dir / "src").is_dir()
        )
        ruff_bin = _find_binary("ruff", target_dir)
        flake8_bin = _find_binary("flake8", target_dir)

        comando = ""
        if oxlint_bin:
            comando = f'"{oxlint_bin}" --format unix {files}'.strip()
        elif eslint_bin:
            comando = f'"{eslint_bin}" --format unix {files or "."}'.strip()
        elif biome_bin:
            comando = f'"{biome_bin}" lint {files}'.strip()
        elif ruff_bin:
            comando = f'"{ruff_bin}" check --output-format=concise --no-fix {files or "."}'.strip()
        elif flake8_bin:
            comando = f'"{flake8_bin}" {files or "."}'.strip()
        elif is_node_project and not (target_dir / "node_modules").is_dir():
            return "[SynRAG Linter] No se encontró node_modules ni un linter instalado localmente. Ejecuta 'npm install' o 'pnpm install' primero."
        else:
            return "[SynRAG Linter] No se detectó un linter configurado (oxlint, eslint, ruff, flake8) en este entorno."

        res = subprocess.run(
            comando,
            shell=True,
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=25
        )

        salida = _sanitize_output((res.stdout + "\n" + res.stderr).strip(), target_dir)

        lineas_raw = [
            l.strip() for l in salida.splitlines()
            if l.strip()
            and not l.startswith("Rule:")
            and not l.startswith("Finished in")
            and not l.startswith("Found ")
            and not l.startswith("All checks passed")
        ]

        if res.returncode == 0 and not lineas_raw:
            return f"[SynRAG Linter] Cero errores de lint en '{files or target_dir.name}'."

        if not lineas_raw and res.returncode != 0:
            lineas_raw = [salida] if salida else [f"Linter terminó con código {res.returncode}"]

        out = [f"[SynRAG Linter] Errores encontrados ({len(lineas_raw)}):"]
        out.extend(lineas_raw[:25])
        if len(lineas_raw) > 25:
            out.append(f"  ... y {len(lineas_raw) - 25} errores más.")
        return "\n".join(out)

    except subprocess.TimeoutExpired:
        return "[SynRAG Linter] Timeout: El linter tardó más de 25 segundos en responder."
    except Exception as e:
        return f"[SynRAG Linter] Error al ejecutar linter: {e}"


def run_typecheck_focus(files: str = "", cwd: str = "") -> str:
    """Corre tsc --noEmit o pyright y devuelve solo los errores de los archivos indicados."""
    target_dir = _resolve_cwd(cwd)
    try:
        filtro_nombres = [Path(f.strip()).name for f in files.split(",") if f.strip()]
        filtro_rutas = [f.strip() for f in files.split(",") if f.strip()]

        is_ts_project = (
            (target_dir / "tsconfig.json").exists()
            or (target_dir / "tsconfig.base.json").exists()
            or (target_dir / "package.json").exists()
        )
        tsc_bin = _find_binary("tsc", target_dir, is_node=True)

        is_py_project = (
            (target_dir / "pyproject.toml").exists()
            or (target_dir / "setup.cfg").exists()
            or any(target_dir.glob("*.py"))
            or (target_dir / "src").is_dir()
        )
        pyright_bin = _find_binary("pyright", target_dir)
        mypy_bin = _find_binary("mypy", target_dir)

        comando = ""
        if is_ts_project and tsc_bin:
            comando = f'"{tsc_bin}" --noEmit --pretty false'
        elif pyright_bin and (is_py_project or not is_ts_project):
            comando = f'"{pyright_bin}" {files}'.strip() if files else f'"{pyright_bin}"'
        elif mypy_bin and (is_py_project or not is_ts_project):
            comando = f'"{mypy_bin}" --no-error-summary {files}'.strip() if files else f'"{mypy_bin}" --no-error-summary .'
        elif is_ts_project and not (target_dir / "node_modules").is_dir():
            return "[SynRAG Typecheck] No se encontró node_modules ni tsc instalado. Ejecuta 'npm install' o 'pnpm install' primero."
        elif is_ts_project:
            return "[SynRAG Typecheck] No se encontró tsc instalado en node_modules ni en el PATH. Ejecuta 'npm install typescript'."
        else:
            return "[SynRAG Typecheck] No se detectó un comprobador de tipos (tsc, pyright, mypy) en este entorno."

        res = subprocess.run(
            comando,
            shell=True,
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=35
        )

        salida = _sanitize_output((res.stdout + "\n" + res.stderr).strip(), target_dir)
        if res.returncode == 0:
            return f"[SynRAG Typecheck] Tipos verificados con éxito sin errores en '{target_dir.name}'."

        lineas = salida.splitlines()
        filtradas = []
        for l in lineas:
            l_strip = l.strip()
            if not l_strip:
                continue
            # Filtrar lineas relevantes de error
            es_error = any(ind in l_strip for ind in ("error TS", "- error:", ": error:", "error:"))
            if not es_error and not any(p in l_strip for p in filtro_nombres):
                continue

            if filtro_nombres:
                if any(fn in l_strip for fn in filtro_nombres) or any(fr in l_strip for fr in filtro_rutas):
                    filtradas.append(l_strip)
            else:
                filtradas.append(l_strip)

        if not filtradas and filtro_nombres:
            return f"[SynRAG Typecheck] Los archivos indicados ({', '.join(filtro_rutas)}) no contienen errores de tipos (se ignoraron otros archivos no relacionados)."

        if not filtradas:
            filtradas = [l.strip() for l in lineas if l.strip()][:25]

        out = [
            f"[SynRAG Typecheck] Errores de tipos enfocados ({len(filtradas[:25])} de {len(filtradas)} reportados):",
            "--------------------------------------------------------------------------------",
        ]
        out.extend(filtradas[:25])
        if len(filtradas) > 25:
            out.append(f"  ... y {len(filtradas) - 25} errores más.")
        out.append("--------------------------------------------------------------------------------")
        return "\n".join(out)

    except subprocess.TimeoutExpired:
        return "[SynRAG Typecheck] Timeout: El comprobador de tipos tardó más de 35 segundos en responder."
    except Exception as e:
        return f"[SynRAG Typecheck] Error al ejecutar typecheck: {e}"


def tail_clean_logs(log_path: str, max_lines: int = 40) -> str:
    """Final de un log sin lineas repetidas."""
    if max_lines <= 0:
        max_lines = 40

    p = Path(log_path).expanduser().resolve()
    if not p.is_file():
        return f"[SynRAG Logs] No se encontró el archivo de log '{log_path}'."

    try:
        size = p.stat().st_size
        if size == 0:
            return f"[SynRAG Logs] El archivo de log '{p.name}' está vacío."

        # Leer hasta 256 KB desde el final del archivo
        max_bytes = 256 * 1024
        with open(p, "rb") as f:
            if size > max_bytes:
                f.seek(size - max_bytes)
                raw = f.read()
                idx = raw.find(b"\n")
                if idx != -1:
                    raw = raw[idx + 1:]
            else:
                raw = f.read()

        texto = raw.decode("utf-8", errors="replace")
        lineas = [l.rstrip() for l in texto.splitlines() if l.strip()]

        if not lineas:
            return f"[SynRAG Logs] El archivo de log '{p.name}' está vacío."

        ultimas = lineas[-300:]

        patrones_ruido = [
            "/health",
            "GET /favicon.ico",
            "heartbeat",
            "200 OK - /api/ping",
            "/metrics",
            "GET /robots.txt",
        ]

        re_timestamp = re.compile(
            r"^\s*(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?|\b\d{2}:\d{2}:\d{2}(?:\.\d+)?\b|[A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2})\s*"
        )
        re_pid = re.compile(r"\[\d+\]\s*")

        def normalizar(linea: str) -> str:
            norm = re_timestamp.sub("", linea)
            norm = re_pid.sub("", norm)
            return norm.strip()

        limpias = []
        ultima_normalizada = ""
        repeticiones = 1

        omitidas_ruido = 0
        for l in ultimas:
            if any(ign in l for ign in patrones_ruido):
                omitidas_ruido += 1
                continue

            norm = normalizar(l)
            if norm and norm == ultima_normalizada:
                repeticiones += 1
            else:
                if repeticiones > 1:
                    limpias.append(f"  ... [repetido {repeticiones} veces]")
                limpias.append(l)
                ultima_normalizada = norm
                repeticiones = 1

        if repeticiones > 1:
            limpias.append(f"  ... [repetido {repeticiones} veces]")

        finales = limpias[-max_lines:]
        # Decir siempre que se quito: la IA no debe creer que vio el log entero
        notas = []
        if len(lineas) > len(ultimas):
            notas.append(f"solo se revisaron las ultimas {len(ultimas)} de {len(lineas)} lineas")
        if omitidas_ruido:
            notas.append(f"{omitidas_ruido} lineas de ruido omitidas (health, favicon, metrics, ping)")
        if len(limpias) > len(finales):
            notas.append(f"{len(limpias) - len(finales)} lineas anteriores no mostradas")
        nota = f" ({'; '.join(notas)})" if notas else ""
        return f"[SynRAG Logs] Últimas líneas depuradas de '{p.name}'{nota}:\n" + "\n".join(finales)

    except Exception as e:
        return f"[SynRAG Logs] Error al leer logs: {e}"


def shutil_which(cmd: str) -> bool:
    return shutil.which(cmd) is not None
