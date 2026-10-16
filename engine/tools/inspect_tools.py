"""
tools/inspect_tools.py - Herramientas de lectura e inspeccion quirurgica de codigo.
Permiten a la IA consultar interfaces, tipos y llamadas sin leer archivos completos de miles de lineas.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any


def _resolve_file(file_path: str, project: str = "") -> Optional[Path]:
    import indexer
    return indexer.resolver_archivo(file_path, project or None)[0]


def get_symbol_contract(file_path: str, symbol_name: str) -> str:
    """Firma, parametros, retorno y JSDoc/docstring de una funcion, sin su cuerpo."""
    f = _resolve_file(file_path)
    if not f:
        return f"[SynRAG Contrato] No se encontró el archivo '{file_path}'."

    try:
        content = f.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()

        # Regex para funciones TS/JS y Python
        escaped = re.escape(symbol_name)
        pattern_ts = re.compile(rf"(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+{escaped}\s*(?:<[^>]+>)?\s*\((.*?)\)(?:\s*:\s*([^\{{;]+))?", re.DOTALL)
        pattern_arrow = re.compile(rf"(?:export\s+)?(?:const|let)\s+{escaped}\s*=\s*(?:async\s+)?(?:\((.*?)\)|([A-Za-z0-9_$]+))\s*(?::\s*([^=]+))?\s*=>", re.DOTALL)
        pattern_py = re.compile(rf"(?:async\s+)?def\s+{escaped}\s*\((.*?)\)(?:\s*->\s*([^:]+))?:", re.DOTALL)
        pattern_class = re.compile(rf"(?:export\s+)?class\s+{escaped}(?:\s+extends\s+[A-Za-z0-9_$]+)?(?:\s+implements\s+[A-Za-z0-9_$,\s]+)?", re.DOTALL)

        found_idx = -1
        signature = ""

        for idx, line in enumerate(lines):
            if symbol_name in line:
                block = "\n".join(lines[idx:min(idx + 10, len(lines))])
                m = pattern_ts.search(block) or pattern_arrow.search(block) or pattern_py.search(block) or pattern_class.search(block)
                if m:
                    found_idx = idx
                    # Tomar la firma hasta la apertura del cuerpo
                    raw_match = m.group(0).strip()
                    signature = raw_match.rstrip("{").rstrip(":").strip()
                    break

        if found_idx == -1:
            return f"[SynRAG Contrato] Símbolo '{symbol_name}' no encontrado como función/clase en '{f.name}'."

        # Extraer comentarios o JSDoc anteriores si existen
        doc_lines = []
        cur = found_idx - 1
        while cur >= 0:
            l = lines[cur].strip()
            if l.endswith("*/") or l.startswith("*") or l.startswith("/**") or l.startswith("//") or l.startswith("#"):
                doc_lines.insert(0, lines[cur])
                cur -= 1
            elif not l:
                break
            else:
                break

        out = [
            f"[SynRAG Contrato] {f.name}:{found_idx + 1} -> '{symbol_name}':",
        ]
        if doc_lines:
            out.append("\n".join(doc_lines[-8:]))
        out.append(f"{signature} {{ ... cuerpo omitido ... }}")
        return "\n".join(out)

    except Exception as e:
        return f"[SynRAG Contrato] Error al extraer contrato: {e}"


def extract_type_definition(file_path: str, type_name: str) -> str:
    """Solo la definicion de una interface, type o enum."""
    f = _resolve_file(file_path)
    if not f:
        return f"[SynRAG Tipos] No se encontró el archivo '{file_path}'."

    try:
        content = f.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()

        escaped = re.escape(type_name)
        pattern_start = re.compile(rf"^\s*(?:export\s+)?(?:interface|type|enum)\s+{escaped}\b")
        pattern_class = re.compile(rf"^\s*(?:@dataclass\s*\n\s*)?(?:class)\s+{escaped}\b")

        start_line = -1
        for idx, line in enumerate(lines):
            if pattern_start.search(line) or pattern_class.search(line):
                start_line = idx
                break

        if start_line == -1:
            return f"[SynRAG Tipos] Tipo o interfaz '{type_name}' no encontrado en '{f.name}'."

        # Recoger el bloque del tipo
        extracted = []
        brace_count = 0
        started_braces = False

        for idx in range(start_line, min(start_line + 80, len(lines))):
            l = lines[idx]
            extracted.append(l)
            brace_count += l.count("{") - l.count("}")
            if "{" in l:
                started_braces = True

            # Para type aliases simples que terminan en punto y coma (type X = 'a' | 'b';)
            if not started_braces and l.strip().endswith(";"):
                break
            # Para interfaces/enums que cierran sus llaves
            if started_braces and brace_count <= 0:
                break

        return f"[SynRAG Tipos] Definición de '{type_name}' en {f.name}:{start_line + 1}:\n" + "\n".join(extracted)

    except Exception as e:
        return f"[SynRAG Tipos] Error al extraer tipo: {e}"


RE_IMPORT_JS = re.compile(
    r"""(?:^|[;\n])\s*(?:import|export)\b[^;'"]*?\bfrom\s*['"]([^'"]+)['"]"""
    r"""|(?:^|[;\n])\s*import\s*['"]([^'"]+)['"]"""
    r"""|\brequire\(\s*['"]([^'"]+)['"]\s*\)|\bimport\(\s*['"]([^'"]+)['"]\s*\)""",
    re.S,
)
RE_IMPORT_PY = re.compile(r"^\s*(?:from\s+([A-Za-z0-9_.]+)\s+import\b|import\s+([A-Za-z0-9_.]+))", re.M)


def _alias_locales(f: Path) -> List[str]:
    """Prefijos de alias (`@/`, `@modulos/`...) de los `paths` del tsconfig/jsconfig mas cercano."""
    import json
    for carpeta in [f.parent, *f.parents][:8]:
        for nombre in ("tsconfig.json", "jsconfig.json", "tsconfig.app.json"):
            cfg = carpeta / nombre
            if cfg.is_file():
                try:
                    texto = re.sub(r"(?m)^\s*//.*$|/\*.*?\*/", "", cfg.read_text(errors="ignore"), flags=re.S)
                    paths = json.loads(re.sub(r",(\s*[}\]])", r"\1", texto)).get("compilerOptions", {}).get("paths", {})
                    return [k.rstrip("*") for k in paths]
                except Exception:
                    return []
    return []


def get_import_graph(file_path: str, project: str = "") -> str:
    """Imports de un archivo: locales (relativos o alias del tsconfig) y paquetes externos."""
    f = _resolve_file(file_path, project)
    if not f:
        return f"No se encontro el archivo '{file_path}'."
    try:
        content = f.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"No se pudo leer '{f}': {e}"

    if f.suffix == ".py":
        fuentes = [a or b for a, b in RE_IMPORT_PY.findall(content)]
    else:
        sin_comentarios = re.sub(r"/\*.*?\*/|(?<![:'\"])//[^\n]*", "", content, flags=re.S)
        fuentes = [next(g for g in m if g) for m in RE_IMPORT_JS.findall(sin_comentarios)]

    alias = _alias_locales(f) or ["@/", "~/", "#"]
    internos, externos = [], []
    for src in dict.fromkeys(fuentes):
        local = src.startswith((".", "/")) or any(src.startswith(a) for a in alias if a)
        (internos if local else externos).append(src)

    out = [f"{f}", f"Locales ({len(internos)}):"]
    out += [f"  {i}" for i in internos[:25]]
    if len(internos) > 25:
        out.append(f"  ... y {len(internos) - 25} mas")
    out.append(f"Externos ({len(externos)}):")
    out += [f"  {e}" for e in externos[:20]]
    return "\n".join(out)


def find_callers_exact(symbol_name: str, project_path: str = "") -> str:
    """Llamadas reales `simbolo(` sin definiciones ni imports. project_path: ruta o nombre del proyecto."""
    import indexer
    target_dir = indexer.raiz_de_proyecto(project_path) if project_path else Path.cwd()
    if not target_dir:
        return f"No se encontro el proyecto '{project_path}'."
    nombre = re.escape(symbol_name)
    patron = rf"\b{nombre}\s*\("
    definicion = re.compile(
        rf"(function\*?\s+{nombre}\b|\bdef\s+{nombre}\b|\b(const|let|var)\s+{nombre}\s*[=:]"
        rf"|^\s*(public\s+|private\s+|static\s+|async\s+)*{nombre}\s*\([^)]*\)\s*(:[^{{]*)?\{{\s*$)"
    )
    try:
        cmd = ["rg", "-n", "--no-heading", "--max-count", "5", "-e", patron, str(target_dir)]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            salida = res.stdout
        except FileNotFoundError:  # sin ripgrep instalado
            cmd = ["grep", "-rnI", "--exclude-dir=.git", "--exclude-dir=node_modules", "--exclude-dir=dist",
                   "-E", patron, str(target_dir)]
            salida = subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout
    except Exception as e:
        return f"Error al buscar llamadas: {e}"

    llamadas = []
    for linea in salida.splitlines():
        partes = linea.split(":", 2)
        if len(partes) < 3 or definicion.search(partes[2]) or re.match(r"\s*(import|export\s*\{)", partes[2]):
            continue
        rel = os.path.relpath(partes[0], target_dir)
        llamadas.append(f"  {rel}:{partes[1]}  {partes[2].strip()[:90]}")

    if not llamadas:
        return f"Sin llamadas a {symbol_name}() en {target_dir}."
    out = [f"{len(llamadas)} llamada(s) a {symbol_name}() en {target_dir}:"] + llamadas[:25]
    if len(llamadas) > 25:
        out.append(f"  ... y {len(llamadas) - 25} mas")
    return "\n".join(out)
