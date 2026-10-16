"""
Empaquetado de repositorios con compresión AST (Repomix --compress / code2prompt).
Genera un único contexto de texto con solo firmas, tipos, interfaces e imports para código.
"""

from pathlib import Path
from typing import Tuple, Dict, List, Optional
import os
import re

import chunker
import indexer

EXTENSIONES_CODIGO = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".rs",
}


def tokens_count(texto: str) -> int:
    """Aproximación de tokens estándar: (caracteres + 3) // 4."""
    return (len(texto) + 3) // 4


def comprimir_fallback(code_str: str, sufijo: str = "") -> str:
    """Compresión simple por líneas para lenguajes sin soporte AST especializado."""
    lineas = code_str.splitlines()
    out: List[str] = []
    for l in lineas:
        l_str = l.strip()
        if not l_str:
            continue
        if l_str.startswith(("import ", "from ", "require(", "export *", "export {")):
            out.append(l_str)
            continue
        if l_str.startswith((
            "def ", "class ", "interface ", "type ", "enum ",
            "export interface ", "export type ", "export enum ",
            "export class ", "export function ", "function "
        )):
            if "{" in l_str:
                sig = l_str.split("{")[0].strip() + " { /* ... */ }"
                out.append(sig)
            elif l_str.endswith(":"):
                out.append(l_str + " ...")
            else:
                out.append(l_str)
    return "\n".join(out)


def comprimir_python(code_str: str) -> str:
    """Comprime código Python dejando únicamente imports, clases y firmas de métodos/funciones."""
    parser = chunker.get_parser_for_lang("python")
    if not parser:
        return comprimir_fallback(code_str, ".py")

    code_bytes = code_str.encode("utf-8", errors="replace")
    try:
        tree = parser.parse(code_bytes)
    except Exception:
        return comprimir_fallback(code_str, ".py")

    def _procesar(nodo, indent=""):
        out = []
        for hijo in nodo.children:
            t = hijo.type
            if t in ("import_statement", "import_from_statement", "future_import_statement"):
                out.append(code_bytes[hijo.start_byte:hijo.end_byte].decode("utf-8", errors="replace").strip())
            elif t in ("type_alias_statement",):
                out.append(indent + code_bytes[hijo.start_byte:hijo.end_byte].decode("utf-8", errors="replace").strip())
            elif t in ("expression_statement", "assignment"):
                txt = code_bytes[hijo.start_byte:hijo.end_byte].decode("utf-8", errors="replace").strip()
                if any(k in txt for k in (":", "=", "__all__")) and len(txt) < 300:
                    out.append(indent + txt)
            elif t in ("function_definition", "async_function_definition"):
                body = hijo.child_by_field_name("body")
                if body:
                    sig = code_bytes[hijo.start_byte:body.start_byte].decode("utf-8", errors="replace").strip()
                    out.append(indent + sig + " ...")
                else:
                    out.append(indent + code_bytes[hijo.start_byte:hijo.end_byte].decode("utf-8", errors="replace").strip())
            elif t == "decorated_definition":
                dec_def = hijo.child_by_field_name("definition")
                if dec_def:
                    dec = code_bytes[hijo.start_byte:dec_def.start_byte].decode("utf-8", errors="replace").strip()
                    if dec_def.type in ("function_definition", "async_function_definition"):
                        body = dec_def.child_by_field_name("body")
                        sig = code_bytes[dec_def.start_byte:body.start_byte].decode("utf-8", errors="replace").strip() if body else code_bytes[dec_def.start_byte:dec_def.end_byte].decode("utf-8", errors="replace").strip()
                        out.append(indent + dec + "\n" + indent + sig + " ...")
                    elif dec_def.type == "class_definition":
                        body = dec_def.child_by_field_name("body")
                        if body:
                            sig = code_bytes[dec_def.start_byte:body.start_byte].decode("utf-8", errors="replace").strip()
                            out.append(indent + dec + "\n" + indent + sig)
                            sub = _procesar(body, indent + "    ")
                            out.extend(sub if sub else [indent + "    ..."])
                        else:
                            out.append(indent + code_bytes[hijo.start_byte:hijo.end_byte].decode("utf-8", errors="replace").strip())
                    else:
                        out.append(indent + code_bytes[hijo.start_byte:hijo.end_byte].decode("utf-8", errors="replace").strip())
                else:
                    out.append(indent + code_bytes[hijo.start_byte:hijo.end_byte].decode("utf-8", errors="replace").strip())
            elif t == "class_definition":
                body = hijo.child_by_field_name("body")
                if body:
                    sig = code_bytes[hijo.start_byte:body.start_byte].decode("utf-8", errors="replace").strip()
                    out.append(indent + sig)
                    sub = _procesar(body, indent + "    ")
                    out.extend(sub if sub else [indent + "    ..."])
                else:
                    out.append(indent + code_bytes[hijo.start_byte:hijo.end_byte].decode("utf-8", errors="replace").strip())
        return out

    lineas = _procesar(tree.root_node)
    return "\n".join(lineas)


def comprimir_ts_js(code_str: str, lang: str = "typescript") -> str:
    """Comprime código TypeScript/JavaScript conservando interfaces, tipos, imports y firmas."""
    parser = chunker.get_parser_for_lang(lang)
    if not parser:
        return comprimir_fallback(code_str, lang)

    code_bytes = code_str.encode("utf-8", errors="replace")
    try:
        tree = parser.parse(code_bytes)
    except Exception:
        return comprimir_fallback(code_str, lang)

    def _procesar(nodo, indent=""):
        out = []
        for hijo in nodo.children:
            t = hijo.type
            if t in ("import_statement", "import_alias", "import_require_clause"):
                out.append(code_bytes[hijo.start_byte:hijo.end_byte].decode("utf-8", errors="replace").strip())
            elif t in ("interface_declaration", "type_alias_declaration", "enum_declaration", "ambient_declaration"):
                out.append(indent + code_bytes[hijo.start_byte:hijo.end_byte].decode("utf-8", errors="replace").strip())
            elif t in ("function_declaration", "generator_function_declaration"):
                body = hijo.child_by_field_name("body")
                if body:
                    sig = code_bytes[hijo.start_byte:body.start_byte].decode("utf-8", errors="replace").strip()
                    out.append(indent + sig + " { /* ... */ }")
                else:
                    out.append(indent + code_bytes[hijo.start_byte:hijo.end_byte].decode("utf-8", errors="replace").strip())
            elif t == "class_declaration":
                body = hijo.child_by_field_name("body")
                if body:
                    sig = code_bytes[hijo.start_byte:body.start_byte].decode("utf-8", errors="replace").strip()
                    out.append(indent + sig + " {")
                    out.extend(_procesar(body, indent + "    "))
                    out.append(indent + "}")
                else:
                    out.append(indent + code_bytes[hijo.start_byte:hijo.end_byte].decode("utf-8", errors="replace").strip())
            elif t in ("method_definition", "abstract_method_signature"):
                body = hijo.child_by_field_name("body")
                if body:
                    sig = code_bytes[hijo.start_byte:body.start_byte].decode("utf-8", errors="replace").strip()
                    out.append(indent + sig + " { /* ... */ }")
                else:
                    out.append(indent + code_bytes[hijo.start_byte:hijo.end_byte].decode("utf-8", errors="replace").strip())
            elif t in ("field_definition", "public_field_definition", "property_signature"):
                out.append(indent + code_bytes[hijo.start_byte:hijo.end_byte].decode("utf-8", errors="replace").strip())
            elif t == "export_statement":
                decl = hijo.child_by_field_name("declaration")
                if decl:
                    prefix = code_bytes[hijo.start_byte:decl.start_byte].decode("utf-8", errors="replace").strip()
                    dt = decl.type
                    if dt in ("interface_declaration", "type_alias_declaration", "enum_declaration"):
                        out.append(indent + code_bytes[hijo.start_byte:hijo.end_byte].decode("utf-8", errors="replace").strip())
                    elif dt in ("function_declaration", "generator_function_declaration"):
                        body = decl.child_by_field_name("body")
                        if body:
                            sig = code_bytes[decl.start_byte:body.start_byte].decode("utf-8", errors="replace").strip()
                            out.append(indent + prefix + " " + sig + " { /* ... */ }")
                        else:
                            out.append(indent + code_bytes[hijo.start_byte:hijo.end_byte].decode("utf-8", errors="replace").strip())
                    elif dt == "class_declaration":
                        body = decl.child_by_field_name("body")
                        if body:
                            sig = code_bytes[decl.start_byte:body.start_byte].decode("utf-8", errors="replace").strip()
                            out.append(indent + prefix + " " + sig + " {")
                            out.extend(_procesar(body, indent + "    "))
                            out.append(indent + "}")
                        else:
                            out.append(indent + code_bytes[hijo.start_byte:hijo.end_byte].decode("utf-8", errors="replace").strip())
                    elif dt == "lexical_declaration":
                        txt = code_bytes[decl.start_byte:decl.end_byte].decode("utf-8", errors="replace").strip()
                        if "=>" in txt:
                            sig = txt.split("=>")[0].strip() + " => { /* ... */ };"
                            out.append(indent + prefix + " " + sig)
                        else:
                            out.append(indent + prefix + " " + txt)
                    else:
                        out.append(indent + code_bytes[hijo.start_byte:hijo.end_byte].decode("utf-8", errors="replace").strip())
                else:
                    out.append(indent + code_bytes[hijo.start_byte:hijo.end_byte].decode("utf-8", errors="replace").strip())
        return out

    lineas = _procesar(tree.root_node)
    return "\n".join(lineas)


def comprimir_codigo(file_path: Path, content: str) -> str:
    """Aplica la compresión AST adecuada según el tipo de archivo."""
    sufijo = file_path.suffix.lower()
    if sufijo == ".py":
        return comprimir_python(content)
    elif sufijo in (".ts", ".tsx"):
        return comprimir_ts_js(content, lang="typescript" if sufijo == ".ts" else "tsx")
    elif sufijo in (".js", ".jsx", ".mjs", ".cjs"):
        return comprimir_ts_js(content, lang="javascript" if sufijo != ".jsx" else "tsx")
    else:
        return comprimir_fallback(content, sufijo)


def empaquetar(ruta: Path, comprimir: bool = True) -> Tuple[str, dict]:
    """Recorre la carpeta con las reglas de exclusión del indexador y empaqueta los archivos.
    Si `comprimir` es True, los archivos de código se reducen a firmas, tipos, interfaces e imports.
    Devuelve (texto_completo, estadisticas).
    """
    base_dir = ruta.expanduser().resolve()
    if not base_dir.exists():
        return "", {
            "tokens": 0,
            "tokens_totales": 0,
            "por_archivo": {},
            "archivos_omitidos": [],
            "num_omitidos": 0,
            "total_archivos": 0,
        }

    archivos_procesados: List[Tuple[str, str]] = []
    archivos_omitidos: List[str] = []
    por_archivo: Dict[str, int] = {}

    for root, dirs, files in os.walk(base_dir):
        # Exclusión de directorios ignorados
        dirs[:] = sorted([
            d for d in dirs
            if d not in indexer.IGNORE_DIRS
            and not d.startswith(".")
            and not any(s in d for s in indexer.IGNORE_DIR_SUBSTR)
        ])
        files.sort()

        for f in files:
            full = Path(root) / f
            try:
                rel = full.relative_to(base_dir)
            except ValueError:
                rel = Path(f)

            if not indexer.should_index(full, base_dir):
                archivos_omitidos.append(str(rel))
                continue

            try:
                raw = full.read_text(encoding="utf-8", errors="replace")
            except Exception:
                archivos_omitidos.append(str(rel))
                continue

            # Ocultar secretos según reglas del indexador
            content = indexer.ocultar_secretos(raw)

            if comprimir and full.suffix.lower() in EXTENSIONES_CODIGO:
                content = comprimir_codigo(full, content)

            toks = tokens_count(content)
            rel_str = str(rel)
            por_archivo[rel_str] = toks
            archivos_procesados.append((rel_str, content))

    separador = "=" * 64
    bloques = [
        f"{separador}\nFile: {rel}\n{separador}\n{contenido}"
        for rel, contenido in archivos_procesados
    ]
    texto_final = "\n\n".join(bloques)
    total_tokens = tokens_count(texto_final)

    stats = {
        "tokens": total_tokens,
        "tokens_totales": total_tokens,
        "por_archivo": por_archivo,
        "archivos_omitidos": archivos_omitidos,
        "num_omitidos": len(archivos_omitidos),
        "total_archivos": len(por_archivo),
    }

    return texto_final, stats
