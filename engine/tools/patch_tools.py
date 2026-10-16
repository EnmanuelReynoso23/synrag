"""
tools/patch_tools.py - Herramientas de modificacion sintactica y edicion quirurgica.
Permiten a la IA aplicar cambios directos en funciones e imports sin emitir volcados gigantes ni diffs destructivos.

Reglas comunes:
- El archivo se lee y se escribe en bytes: se conservan los saltos de linea (LF o CRLF) y el final del archivo.
- Si el nombre del archivo coincide con varios del indice, no se toca ninguno.
- El respaldo va a ~/.local/state/synrag/respaldos, nunca junto al archivo (no ensucia el repositorio).
"""

import os
import re
import shutil
import textwrap
import time
from pathlib import Path
from typing import List, Optional, Tuple


def _resolve_file(file_path: str, project: str = "") -> Optional[Path]:
    """Para modificar no se adivina: si el nombre coincide con varios archivos, no se toca ninguno."""
    import indexer
    ruta, otras = indexer.resolver_archivo(file_path, project or None)
    return None if otras else ruta


def _leer(f: Path) -> Tuple[List[str], str, bool]:
    texto = f.read_bytes().decode("utf-8", errors="replace")
    nl = "\r\n" if "\r\n" in texto else "\n"
    return texto.split(nl)[:-1] if texto.endswith(nl) else texto.split(nl), nl, texto.endswith(nl)


def _respaldar(f: Path) -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    destino = base / "synrag" / "respaldos" / f"{time.strftime('%Y%m%d-%H%M%S')}-{f.name}"
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(f, destino)
    return destino


def _escribir(f: Path, lineas: List[str], nl: str, final: bool) -> Path:
    respaldo = _respaldar(f)
    f.write_bytes((nl.join(lineas) + (nl if final else "")).encode("utf-8"))
    return respaldo


def _sin_cadenas(linea: str) -> str:
    """La linea sin literales de texto ni comentario final, para contar llaves sin engaños."""
    linea = re.sub(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`(?:\\.|[^`\\])*`", "''", linea)
    return re.sub(r"//.*$", "", linea)


def _sangrar(cuerpo: str, sangria: str) -> List[str]:
    """Pone el cuerpo nuevo a la sangria dada conservando su sangria relativa interna."""
    limpio = textwrap.dedent(cuerpo.strip("\n"))
    return [f"{sangria}{l}" if l.strip() else "" for l in limpio.splitlines()]


def patch_function_body(file_path: str, symbol_name: str, new_body: str, project: str = "") -> str:
    """Reemplaza el cuerpo de una funcion conservando firma, sangria y saltos de linea. Respaldo fuera del repo."""
    f = _resolve_file(file_path, project)
    if not f:
        return f"No se encontro '{file_path}' o coincide con varios archivos (usa la ruta completa)."
    try:
        lineas, nl, final = _leer(f)
        nombre = re.escape(symbol_name)
        firma = re.compile(
            rf"(function\*?\s+{nombre}\b|\bdef\s+{nombre}\b|\b(const|let|var)\s+{nombre}\s*[=:]"
            rf"|^\s*(?:public\s+|private\s+|protected\s+|static\s+|async\s+)*{nombre}\s*\()"
        )
        inicio = next((i for i, l in enumerate(lineas) if firma.search(l)), -1)
        if inicio == -1:
            return f"No se encontro la definicion de '{symbol_name}' en {f}."

        if f.suffix == ".py":
            dos_puntos = next((i for i in range(inicio, min(inicio + 15, len(lineas)))
                               if _sin_cadenas(lineas[i]).split("#")[0].rstrip().endswith(":")), -1)
            if dos_puntos == -1:
                return f"No se encontro el ':' que abre '{symbol_name}'."
            base = len(lineas[inicio]) - len(lineas[inicio].lstrip())
            fin = len(lineas)
            for i in range(dos_puntos + 1, len(lineas)):
                if lineas[i].strip() and len(lineas[i]) - len(lineas[i].lstrip()) <= base:
                    fin = i
                    break
            while fin - 1 > dos_puntos and not lineas[fin - 1].strip():
                fin -= 1  # las lineas en blanco entre funciones no son del cuerpo
            primera = next((l for l in lineas[dos_puntos + 1:fin] if l.strip()), " " * (base + 4))
            sangria = primera[:len(primera) - len(primera.lstrip())]
            nuevas = lineas[:dos_puntos + 1] + _sangrar(new_body, sangria) + lineas[fin:]
            rango = (dos_puntos + 2, fin)
        else:
            apertura = next((i for i in range(inicio, min(inicio + 15, len(lineas)))
                             if "{" in _sin_cadenas(lineas[i])), -1)
            if apertura == -1:
                return f"No se encontro la llave que abre '{symbol_name}'."
            prof, cierre = 0, -1
            for i in range(apertura, len(lineas)):
                limpia = _sin_cadenas(lineas[i])
                prof += limpia.count("{") - limpia.count("}")
                if prof <= 0:
                    cierre = i
                    break
            if cierre == -1:
                return f"No se encontro la llave que cierra '{symbol_name}'."
            if cierre == apertura:
                return f"'{symbol_name}' abre y cierra en la misma linea ({apertura + 1}); editala directamente."
            primera = next((l for l in lineas[apertura + 1:cierre] if l.strip()), None)
            if primera is None:
                cab = lineas[apertura]
                primera = cab[:len(cab) - len(cab.lstrip())] + "  "
            sangria = primera[:len(primera) - len(primera.lstrip())]
            nuevas = lineas[:apertura + 1] + _sangrar(new_body, sangria) + lineas[cierre:]
            rango = (apertura + 2, cierre)

        respaldo = _escribir(f, nuevas, nl, final)
        return f"Cuerpo de '{symbol_name}' reemplazado en {f} (antes L{rango[0]}-{rango[1]}). Respaldo: {respaldo}"
    except Exception as e:
        return f"Error al reemplazar el cuerpo: {e}"


RE_IMPORT_JS = re.compile(
    r"""^(?:import|export)\b[^;'"]*?\bfrom\s*['"][^'"]+['"][ \t]*;?|^import\s*['"][^'"]+['"][ \t]*;?""",
    re.M | re.S,
)
RE_IMPORT_PY = re.compile(r"^(?:from\s+\S+\s+import\s+(?:\([^)]*\)|[^\n]+)|import\s+[^\n]+)", re.M)


def _fin_de_imports(texto: str, es_py: bool) -> int:
    """Numero de linea (0-based) donde termina el ultimo import de la cabecera, o -1."""
    patron = RE_IMPORT_PY if es_py else RE_IMPORT_JS
    fin = -1
    for m in patron.finditer(texto):
        fin = texto.count("\n", 0, m.end())
    return fin


def add_import_clean(file_path: str, import_statement: str, project: str = "") -> str:
    """Agrega un import tras el ultimo de la cabecera si no existe."""
    f = _resolve_file(file_path, project)
    if not f:
        return f"No se encontro '{file_path}' o coincide con varios archivos (usa la ruta completa)."
    try:
        stmt = import_statement.strip()
        lineas, nl, final = _leer(f)
        texto = "\n".join(lineas)
        if stmt in texto:
            return f"El import ya existe en {f}; sin cambios."
        fin = _fin_de_imports(texto, f.suffix == ".py")
        lineas.insert(fin + 1, stmt)
        _escribir(f, lineas, nl, final)
        return f"Import agregado en {f} (linea {fin + 2}): {stmt}"
    except Exception as e:
        return f"Error al agregar el import: {e}"


def rename_symbol_scoped(file_path: str, old_name: str, new_name: str, project: str = "") -> str:
    """Renombra un identificador (palabra completa) en UN archivo."""
    f = _resolve_file(file_path, project)
    if not f:
        return f"No se encontro '{file_path}' o coincide con varios archivos (usa la ruta completa)."
    if not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", new_name):
        return f"'{new_name}' no es un identificador valido."
    try:
        texto = f.read_bytes().decode("utf-8", errors="replace")
        patron = re.compile(rf"(?<![A-Za-z0-9_$]){re.escape(old_name)}(?![A-Za-z0-9_$])")
        n = len(patron.findall(texto))
        if n == 0:
            return f"'{old_name}' no aparece como palabra completa en {f}."
        respaldo = _respaldar(f)
        f.write_bytes(patron.sub(new_name, texto).encode("utf-8"))
        return (f"'{old_name}' -> '{new_name}' en {f} ({n} cambios). Respaldo: {respaldo}. "
                "Otros archivos que lo importen no se cambiaron (find_callers_exact los lista).")
    except Exception as e:
        return f"Error al renombrar: {e}"


RE_ESPECIFICADORES = re.compile(
    r"^import\s+(?P<tipo>type\s+)?(?P<def>[A-Za-z_$][\w$]*)?\s*,?\s*"
    r"(?:\*\s*as\s+(?P<ns>[A-Za-z_$][\w$]*)|\{(?P<llaves>[^}]*)\})?\s*from\s*(?P<src>['\"][^'\"]+['\"])\s*;?$",
    re.S,
)


def _nombre_local(spec: str) -> str:
    spec = re.sub(r"^type\s+", "", spec.strip())
    return spec.split(" as ")[-1].strip()


def remove_unused_imports(file_path: str, project: str = "") -> str:
    """Quita los imports que el archivo no usa."""
    f = _resolve_file(file_path, project)
    if not f:
        return f"No se encontro '{file_path}' o coincide con varios archivos (usa la ruta completa)."
    try:
        lineas, nl, final = _leer(f)
        texto = "\n".join(lineas)
        es_py = f.suffix == ".py"
        sentencias = list((RE_IMPORT_PY if es_py else RE_IMPORT_JS).finditer(texto))
        cuerpo = texto
        for m in reversed(sentencias):
            cuerpo = cuerpo[:m.start()] + cuerpo[m.end():]
        usado = lambda n: re.search(rf"(?<![\w$]){re.escape(n)}(?![\w$])", cuerpo) is not None

        quitados, nuevo = [], texto
        for m in reversed(sentencias):
            original = m.group(0)
            reemplazo = original
            if es_py:
                mp = re.match(r"from\s+(\S+)\s+import\s+\(?([^)]*?)\)?\s*$", original, re.S)
                if mp and mp.group(2).strip() != "*":
                    specs = [s.strip() for s in mp.group(2).replace("\n", " ").split(",") if s.strip()]
                    vivos = [s for s in specs if usado(_nombre_local(s))]
                    quitados += [_nombre_local(s) for s in specs if s not in vivos]
                    reemplazo = f"from {mp.group(1)} import {', '.join(vivos)}" if vivos else ""
                elif original.startswith("import ") and "," not in original:
                    alias = _nombre_local(original[7:]).split(".")[0]
                    if not usado(alias):
                        quitados.append(alias)
                        reemplazo = ""
            else:
                mj = RE_ESPECIFICADORES.match(original)
                if not mj:
                    continue  # import de efecto ('./estilos.css') o forma rara: no se toca
                defecto = mj.group("def") if mj.group("def") and usado(mj.group("def")) else None
                ns = mj.group("ns") if mj.group("ns") and usado(mj.group("ns")) else None
                llaves = [s.strip() for s in (mj.group("llaves") or "").split(",") if s.strip()]
                vivas = [s for s in llaves if usado(_nombre_local(s))]
                quitados += [n for n in (mj.group("def"), mj.group("ns")) if n and n not in (defecto, ns)]
                quitados += [_nombre_local(s) for s in llaves if s not in vivas]
                partes = [p for p in (defecto, f"* as {ns}" if ns else None, "{ " + ", ".join(vivas) + " }" if vivas else None) if p]
                if len(partes) == (bool(mj.group("def")) + bool(mj.group("ns")) + bool(llaves)) and len(vivas) == len(llaves):
                    continue  # todo se usa
                tipo = mj.group("tipo") or ""
                fin = ";" if original.rstrip().endswith(";") else ""
                reemplazo = f"import {tipo}{', '.join(partes)} from {mj.group('src')}{fin}" if partes else ""
            if reemplazo != original:
                fin_m = m.end() + (1 if not reemplazo and nuevo[m.end():m.end() + 1] == "\n" else 0)
                nuevo = nuevo[:m.start()] + reemplazo + nuevo[fin_m:]

        if not quitados:
            return f"Sin imports sin usar en {f}."
        _escribir(f, nuevo.split("\n"), nl, final)
        return f"Quitados de {f}: {', '.join(reversed(quitados))}"
    except Exception as e:
        return f"Error al limpiar imports: {e}"
