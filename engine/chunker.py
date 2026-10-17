"""
Tree-sitter AST Chunker + Dependency Extractor para LanceDB Hub
- Divide código en unidades sintácticas completas (funciones, clases, interfaces, hooks).
- Extrae grafo de dependencias (imports y exports) para prevenir roturas de código.
- Divide markdown por encabezados (# y ##).
"""

from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import re

try:
    from tree_sitter import Parser, Language
    import tree_sitter_language_pack as tslp
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

_LANG_CACHE: Dict[str, Any] = {}

def get_parser_for_lang(lang_name: str) -> Optional[Any]:
    if not TREE_SITTER_AVAILABLE:
        return None
    try:
        if lang_name not in _LANG_CACHE:
            _LANG_CACHE[lang_name] = tslp.get_language(lang_name)
        return Parser(_LANG_CACHE[lang_name])
    except Exception:
        return None

# Solo gramáticas de código real (JSON, YAML, HTML, CSS usan chunking limpio por bloques/líneas)
LANG_MAP = {
    ".ts": "typescript",
    ".tsx": "tsx",
    ".jsx": "tsx",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".py": "python",
    ".rs": "rust",
    ".go": "go",
}

MAX_CHUNK_CHARS = 2400
MAX_DOC_CHARS = 800
MIN_CHUNK_CHARS = 35

RE_TS_SYM = re.compile(r"(?:export\s+(?:default\s+)?)?(?:async\s+)?(?:function\*?|class|interface|type|enum|const|let|var)\s+([A-Za-z0-9_$]+)")
RE_PY_SYM = re.compile(r"(?:async\s+)?(?:def|class)\s+([A-Za-z0-9_]+)")
RE_IMPORT_TS = re.compile(r"""import\s+(?:type\s+)?(?:([A-Za-z0-9_$]+)|\{([^}]+)\}|\*\s+as\s+([A-Za-z0-9_$]+))\s+from\s+['"]([^'"]+)['"]""")
RE_IMPORT_PY = re.compile(r"""(?:from\s+([A-Za-z0-9_.]+)\s+import\s+([^#\n]+)|import\s+([A-Za-z0-9_.]+))""")


RE_DECL = re.compile(
    r"^\s*(?:export\s+(?:default\s+)?)?(?:declare\s+)?(?:abstract\s+)?(?:async\s+)?"
    r"(function\*?|class|interface|type|enum|const|let|var|def)\s+([A-Za-z0-9_$]+)(.*)$",
    re.M,
)
RE_ARROW = re.compile(r"=\s*(?:async\s*)?(?:function\b|\([^)]*\)?\s*(?::[^=]*)?=>|[A-Za-z0-9_$]+\s*=>|\(|<)")


def _sin_comentarios_iniciales(texto: str) -> str:
    """Quita el JSDoc, los comentarios y los decoradores que preceden a la declaracion."""
    lineas = texto.splitlines()
    i, en_bloque = 0, False
    while i < len(lineas):
        l = lineas[i].strip()
        if en_bloque:
            en_bloque = "*/" not in l
        elif l.startswith("/*"):
            en_bloque = "*/" not in l
        elif not (l == "" or l.startswith(("//", "#", "@"))):
            break
        i += 1
    return "\n".join(lineas[i:])


def extract_symbol_and_kind(node_text: str, ntype: str) -> Tuple[Optional[str], str]:
    """Extrae el nombre del símbolo y clasifica su tipo sintáctico."""
    cuerpo = _sin_comentarios_iniciales(node_text)
    primeras = "\n".join(cuerpo.splitlines()[:3])
    m = RE_DECL.search(primeras)
    if not m:
        kind = "code"
        if "declaration" in ntype or "statement" in ntype:
            kind = "variable"
        return None, kind

    palabra, name, resto = m.group(1), m.group(2), m.group(3)
    es_hook = name.startswith("use") and len(name) > 3 and name[3].isupper()
    if palabra in ("function", "function*", "def"):
        kind = "hook" if es_hook else "function"
    elif palabra in ("class", "interface", "type", "enum"):
        kind = palabra
    else:
        kind = "hook" if es_hook else ("function" if RE_ARROW.search(resto) else "variable")
    return name, kind


PY_CONTENEDORES = {
    "module", "block", "function_definition", "class_definition", "decorated_definition",
    "if_statement", "elif_clause", "else_clause", "try_statement", "except_clause", "except_group_clause",
    "finally_clause", "with_statement", "for_statement", "while_statement", "match_statement", "case_clause",
}


def _texto(nodo) -> str:
    return nodo.text.decode("utf-8", errors="ignore") if nodo is not None else ""


def imports_del_arbol(raiz, lang: str) -> List[Dict[str, str]]:
    """Imports leidos del AST: los de varias lineas, `import D, { a } from`, los re-export de los
    barrels (`export { a } from`, `export * from`) y, en Python, los de parentesis, los separados por
    coma y los de dentro de funciones. Nunca toma texto de comentarios ni de cadenas."""
    imps: List[Dict[str, str]] = []

    def agregar(simbolo: str, origen: str):
        simbolo, origen = simbolo.strip("'\"`"), origen.strip("'\"`")
        if simbolo and origen:
            imps.append({"symbol": simbolo, "source": origen})

    if lang == "python":
        pila = [raiz]
        while pila:
            n = pila.pop()
            if n.type == "import_statement":
                for h in n.children_by_field_name("name"):
                    ruta = _texto(h.child_by_field_name("name") if h.type == "aliased_import" else h)
                    agregar(ruta.split(".")[-1], ruta)
            elif n.type in ("import_from_statement", "future_import_statement"):
                modulo = _texto(n.child_by_field_name("module_name")) or "__future__"
                if any(h.type == "wildcard_import" for h in n.children):
                    agregar("*", modulo)
                for h in n.children_by_field_name("name"):
                    agregar(_texto(h.child_by_field_name("name") if h.type == "aliased_import" else h), modulo)
            elif n.type in PY_CONTENEDORES:
                pila.extend(n.children)
        return imps

    for n in raiz.children:  # TS/JS: imports y re-exports solo existen en el nivel superior
        fuente = n.child_by_field_name("source") if n.type in ("import_statement", "export_statement") else None
        if fuente is None:
            continue
        origen = _texto(fuente)
        for h in n.children:
            if h.type == "import_clause":
                for c in h.children:
                    if c.type == "identifier":
                        agregar(_texto(c), origen)
                    elif c.type == "namespace_import":
                        agregar(next((_texto(i) for i in c.children if i.type == "identifier"), ""), origen)
                    elif c.type == "named_imports":
                        for spec in c.children:
                            if spec.type == "import_specifier":
                                agregar(_texto(spec.child_by_field_name("name")), origen)
            elif h.type == "export_clause":
                for spec in h.children:
                    if spec.type == "export_specifier":
                        agregar(_texto(spec.child_by_field_name("name")), origen)
            elif h.type == "namespace_export":
                agregar(next((_texto(i) for i in h.children if i.type == "identifier"), ""), origen)
            elif h.type == "*" and n.type == "export_statement":
                agregar("*", origen)
    return imps


def extract_imports_and_exports(text: str, ext: str = "") -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """Imports y exports de un archivo. Con la extension de un lenguaje con gramatica, los imports
    salen del AST (imports_del_arbol); si no, de expresiones regulares linea por linea."""
    lang = LANG_MAP.get(ext.lower()) if ext else None
    parser = get_parser_for_lang(lang) if lang in ("typescript", "tsx", "javascript", "python") else None
    if parser is not None:
        try:
            imps = imports_del_arbol(parser.parse(text.encode("utf-8", errors="ignore")).root_node, lang)
            return imps, _imports_y_exports_por_lineas(text)[1]
        except Exception:
            pass
    return _imports_y_exports_por_lineas(text)


def _imports_y_exports_por_lineas(text: str) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """Respaldo sin gramatica: un import por linea (no ve los de varias lineas)."""
    imports = []
    exports = []

    for line in text.splitlines():
        line_str = line.strip()
        if not line_str or line_str.startswith("//") or line_str.startswith("#"):
            continue

        # TS/JS Imports
        m_ts = RE_IMPORT_TS.search(line_str)
        if m_ts:
            def_imp, named, star, src = m_ts.groups()
            if def_imp:
                imports.append({"symbol": def_imp, "source": src})
            if star:
                imports.append({"symbol": star, "source": src})
            if named:
                for s in named.split(","):
                    sym = s.strip().split(" as ")[0].strip()
                    if sym:
                        imports.append({"symbol": sym, "source": src})
            continue

        # Python Imports
        m_py = RE_IMPORT_PY.search(line_str)
        if m_py:
            mod, items, direct_imp = m_py.groups()
            if direct_imp:
                imports.append({"symbol": direct_imp.split(".")[-1].strip(), "source": direct_imp.strip()})
            elif mod and items:
                for s in items.split(","):
                    sym = s.strip().split(" as ")[0].strip()
                    if sym:
                        imports.append({"symbol": sym, "source": mod.strip()})
            continue

        # Exports
        if line_str.startswith("export "):
            m_exp = RE_TS_SYM.search(line_str)
            if m_exp:
                exports.append({"symbol": m_exp.group(1), "kind": "export"})

    return imports, exports


CLASES = {"class_definition", "class_declaration", "abstract_class_declaration", "class"}
METODOS = {"function_definition", "decorated_definition", "method_definition"}


VALORES_FUNCION = {"arrow_function", "function_expression", "function", "generator_function"}
ENVOLTORIOS = {"as_expression", "satisfies_expression", "parenthesized_expression", "non_null_expression"}


def _cuerpo_con_miembros(nodo):
    """Cuerpo de una clase (`class X {}`) o de un objeto literal (`const x = { ... }`), o None."""
    if nodo.type in ("export_statement", "decorated_definition"):
        nodo = nodo.child_by_field_name("declaration") or nodo.child_by_field_name("definition")
    if nodo is None:
        return None
    if nodo.type in CLASES:
        return nodo.child_by_field_name("body")
    if nodo.type in ("lexical_declaration", "variable_declaration"):
        declaradores = [h for h in nodo.named_children if h.type == "variable_declarator"]
        valor = declaradores[0].child_by_field_name("value") if len(declaradores) == 1 else None
        while valor is not None and valor.type in ENVOLTORIOS and valor.named_children:
            valor = valor.named_children[0]
        if valor is not None and valor.type == "object":
            return valor
    return None


def _nombre_miembro(hijo) -> Tuple[Optional[str], bool]:
    """(nombre, es_funcion) de un miembro de clase u objeto."""
    nodo = hijo.child_by_field_name("definition") if hijo.type == "decorated_definition" else hijo
    if nodo is None:
        return None, False
    if nodo.type in METODOS:
        nombre = nodo.child_by_field_name("name")
        return (nombre.text.decode("utf-8", errors="ignore") if nombre is not None else None), True
    if nodo.type in ("public_field_definition", "field_definition", "pair"):
        nombre = nodo.child_by_field_name("name") or nodo.child_by_field_name("property") or nodo.child_by_field_name("key")
        valor = nodo.child_by_field_name("value")
        texto = nombre.text.decode("utf-8", errors="ignore").strip("'\"`") if nombre is not None else None
        return texto, valor is not None and valor.type in VALORES_FUNCION
    return None, False


def _miembros_de_clase(nodo) -> List[Tuple[int, int, str, str]]:
    """(inicio, fin, nombre, tipo) de los miembros de una clase u objeto literal grande, con su
    comentario pegado. Cada metodo (tambien `json = () => {}` y `listar: async () => {}`) va solo;
    los campos y atributos entre metodos se agrupan para que ningun tramo del cuerpo se pierda. Lo
    que hay antes del primer metodo queda en la cabecera."""
    cuerpo = _cuerpo_con_miembros(nodo)
    if cuerpo is None:
        return []
    miembros: List[Tuple[int, int, str, str]] = []
    grupo: List[Any] = []  # [inicio, fin, nombres]
    comentario = None

    def cerrar_grupo():
        if grupo and miembros:  # antes del primer metodo: cabecera
            nombres = grupo[2]
            miembros.append((grupo[0], grupo[1], nombres[0] if len(nombres) == 1 else "", "field"))
        grupo.clear()

    for hijo in cuerpo.named_children:
        if hijo.type == "comment":
            comentario = comentario if comentario is not None else int(hijo.start_byte)
            continue
        inicio = comentario if comentario is not None else int(hijo.start_byte)
        comentario = None
        nombre, es_funcion = _nombre_miembro(hijo)
        if es_funcion and nombre:
            cerrar_grupo()
            miembros.append((inicio, int(hijo.end_byte), nombre, "method"))
        elif grupo:
            grupo[1] = int(hijo.end_byte)
            if nombre:
                grupo[2].append(nombre)
        else:
            grupo.extend([inicio, int(hijo.end_byte), [nombre] if nombre else []])
    cerrar_grupo()
    return miembros


def miembros_de_definicion(file_path: Path, linea: int) -> List[Tuple[int, str, str]]:
    """(linea, nombre, tipo) de los miembros de la clase u objeto grande que empieza en `linea`
    (o justo despues, si `linea` es la de su JSDoc). Vacio si ahi no hay una clase u objeto."""
    lang = LANG_MAP.get(file_path.suffix.lower())
    parser = get_parser_for_lang(lang) if lang else None
    if parser is None:
        return []
    try:
        code_bytes = file_path.read_bytes()
        raiz = parser.parse(code_bytes).root_node
    except Exception:
        return []
    for nodo in raiz.children:
        if nodo.type == "comment" or nodo.end_point[0] + 1 < linea:
            continue
        if nodo.start_point[0] + 1 > linea + 40:  # JSDoc largo como mucho
            break
        return [(code_bytes.count(b"\n", 0, ini) + 1, nombre, tipo)
                for ini, _, nombre, tipo in _miembros_de_clase(nodo) if nombre]
    return []


def chunk_with_tree_sitter(file_path: Path, text: str, lang: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]], List[Dict[str, str]]]:
    """Trocea código con AST de Tree-sitter."""
    code_bytes = text.encode("utf-8", errors="ignore")
    try:
        parser = get_parser_for_lang(lang)
        if not parser:
            fallback_chunks = chunk_fallback(text)
            imps, exps = extract_imports_and_exports(text)
            return fallback_chunks, imps, exps

        tree = parser.parse(code_bytes)
        imps_arbol = imports_del_arbol(tree.root_node, lang) if lang in ("typescript", "tsx", "javascript", "python") else None
        raw_nodes = [
            (str(n.type), int(n.start_byte), int(n.end_byte))
            for n in tree.root_node.children
        ]
        miembros_por_nodo = {
            int(n.start_byte): _miembros_de_clase(n)
            for n in tree.root_node.children
            if int(n.end_byte) - int(n.start_byte) > MAX_CHUNK_CHARS
        }
        del tree
    except Exception:
        fallback_chunks = chunk_fallback(text)
        imps, exps = extract_imports_and_exports(text)
        return fallback_chunks, imps, exps

    if not raw_nodes:
        fallback_chunks = chunk_fallback(text)
        imps, exps = extract_imports_and_exports(text)
        return fallback_chunks, imps, exps

    imps, exps = _imports_y_exports_por_lineas(text)
    if imps_arbol is not None:
        imps = imps_arbol

    chunks = []
    import_nodes_coords = []
    prev_comment = None

    for ntype, s_byte, e_byte in raw_nodes:
        # 1. Imports contiguos agrupados
        if "import" in ntype:
            import_nodes_coords.append((s_byte, e_byte))
            prev_comment = None
            continue
        elif import_nodes_coords:
            c_start = import_nodes_coords[0][0]
            c_end = import_nodes_coords[-1][1]
            content = code_bytes[c_start:c_end].decode("utf-8", errors="ignore").strip()
            if len(content) >= MIN_CHUNK_CHARS:
                start_l = code_bytes.count(b"\n", 0, c_start) + 1
                end_l = start_l + code_bytes.count(b"\n", c_start, c_end)
                chunks.append({
                    "line": start_l,
                    "end_line": end_l,
                    "symbol_name": "imports",
                    "symbol_kind": "imports",
                    "content": content,
                })
            import_nodes_coords = []

        # 2. Comentario de nivel superior
        if ntype == "comment":
            prev_comment = (s_byte, e_byte)
            continue

        # 3. Adjuntar comentario previo si es JSDoc o docstring pegado
        start_byte = s_byte
        if prev_comment:
            gap = code_bytes[prev_comment[1]:s_byte]
            if gap.count(b"\n") <= 2:
                start_byte = prev_comment[0]
            prev_comment = None

        chunk_text = code_bytes[start_byte:e_byte].decode("utf-8", errors="ignore").strip()
        if len(chunk_text) < MIN_CHUNK_CHARS:
            continue

        name, kind = extract_symbol_and_kind(chunk_text, ntype)
        if not name and start_byte != s_byte:
            name, kind = extract_symbol_and_kind(code_bytes[s_byte:e_byte].decode("utf-8", errors="ignore"), ntype)
        start_line = code_bytes.count(b"\n", 0, start_byte) + 1
        end_line = start_line + code_bytes.count(b"\n", start_byte, e_byte)

        miembros = miembros_por_nodo.get(s_byte)
        if miembros:
            # Clase grande: cabecera + un fragmento por metodo, en vez de cortes ciegos por tamano
            cabecera = code_bytes[start_byte:miembros[0][0]].decode("utf-8", errors="ignore").strip()
            ultimo = None  # (fragmento, byte de inicio): donde se pegan los miembros diminutos
            if len(cabecera) > MAX_CHUNK_CHARS:
                chunks.extend(chunk_fallback(cabecera, start_offset_line=start_line, symbol_name=name or "", symbol_kind=kind))
            elif len(cabecera) >= MIN_CHUNK_CHARS or (name and cabecera):  # `export const x = {` lleva el nombre
                chunks.append({"line": start_line,
                               "end_line": code_bytes.count(b"\n", 0, miembros[0][0]),
                               "symbol_name": name or "", "symbol_kind": kind, "content": cabecera})
                ultimo = (chunks[-1], start_byte)
            for m_ini, m_fin, m_nombre, m_tipo in miembros:
                texto_m = code_bytes[m_ini:m_fin].decode("utf-8", errors="ignore")
                linea_m = code_bytes.count(b"\n", 0, m_ini) + 1
                if len(texto_m.strip()) < MIN_CHUNK_CHARS:
                    # `LIMITE: 50,` o `private constructor() {}`: va con el fragmento anterior
                    if ultimo and m_fin - ultimo[1] <= MAX_CHUNK_CHARS:
                        ultimo[0]["content"] = code_bytes[ultimo[1]:m_fin].decode("utf-8", errors="ignore").strip()
                        ultimo[0]["end_line"] = linea_m + texto_m.count("\n")
                    continue
                if len(texto_m) > MAX_CHUNK_CHARS:
                    chunks.extend(chunk_fallback(texto_m, start_offset_line=linea_m, symbol_name=m_nombre, symbol_kind=m_tipo))
                    ultimo = None
                else:
                    chunks.append({"line": linea_m, "end_line": linea_m + texto_m.count("\n"),
                                   "symbol_name": m_nombre, "symbol_kind": m_tipo, "content": texto_m.rstrip()})
                    ultimo = (chunks[-1], m_ini)
            continue

        if len(chunk_text) > MAX_CHUNK_CHARS:
            sub = chunk_fallback(chunk_text, start_offset_line=start_line, symbol_name=name or "", symbol_kind=kind)
            chunks.extend(sub)
        else:
            chunks.append({
                "line": start_line,
                "end_line": end_line,
                "symbol_name": name or "",
                "symbol_kind": kind,
                "content": chunk_text,
            })

    if import_nodes_coords:
        c_start = import_nodes_coords[0][0]
        c_end = import_nodes_coords[-1][1]
        content = code_bytes[c_start:c_end].decode("utf-8", errors="ignore").strip()
        if len(content) >= MIN_CHUNK_CHARS:
            start_l = code_bytes.count(b"\n", 0, c_start) + 1
            end_l = start_l + code_bytes.count(b"\n", c_start, c_end)
            chunks.append({
                "line": start_l,
                "end_line": end_l,
                "symbol_name": "imports",
                "symbol_kind": "imports",
                "content": content,
            })

    return (chunks if chunks else chunk_fallback(text)), imps, exps


def _split_long_paragraph(text: str, max_len: int) -> List[str]:
    """Divide un párrafo extenso por oraciones o palabras para no exceder el presupuesto."""
    if len(text) <= max_len:
        return [text]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    pieces, curr, curr_len = [], [], 0
    for s in sentences:
        s_len = len(s)
        if curr and curr_len + 1 + s_len > max_len:
            pieces.append(" ".join(curr))
            curr, curr_len = [], 0
        if s_len > max_len:
            words = s.split(" ")
            w_curr, w_len = [], 0
            for w in words:
                if w_curr and w_len + 1 + len(w) > max_len:
                    pieces.append(" ".join(w_curr))
                    w_curr, w_len = [], 0
                w_curr.append(w)
                w_len += (1 if w_curr else 0) + len(w)
            if w_curr:
                curr = w_curr
                curr_len = w_len
        else:
            curr.append(s)
            curr_len += (1 if len(curr) > 1 else 0) + s_len
    if curr:
        pieces.append(" ".join(curr))
    return pieces


def chunk_doc_generic(text: str, fmt: str = "md") -> Tuple[List[Dict[str, Any]], List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Divide documentos estructurados (Markdown, RST, AsciiDoc) en fragmentos de hasta ~800 caracteres:
    - Corta por títulos y luego por párrafos.
    - Nunca parte un bloque de código cercado (```, ----, .. code-block::).
    - Cada fragmento comienza con la ruta jerárquica de títulos (# Guía > ## Instalación).
    - symbol_name = título más cercano, symbol_kind = 'section'.
    """
    if not text or not text.strip():
        return [], [], []

    lines = text.splitlines()
    n = len(lines)

    # 1. Identificar líneas que pertenecen a bloques de código (para no cortarlos ni interpretar títulos dentro)
    is_code = [False] * n
    in_fence = False
    fence_char = ""
    fence_len = 0

    i = 0
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not in_fence:
            if fmt in ("md", "mdx"):
                m = re.match(r"^\s*(`{3,}|~{3,})", line)
                if m:
                    in_fence = True
                    fence_char = m.group(1)[0]
                    fence_len = len(m.group(1))
                    is_code[i] = True
            elif fmt == "adoc":
                m = re.match(r"^\s*(-{4,}|\.{4,}|`{3,}|~{3,})", line)
                if m:
                    in_fence = True
                    fence_char = m.group(1)[0]
                    fence_len = len(m.group(1))
                    is_code[i] = True
            elif fmt == "rst":
                m_dir = re.match(r"^(\s*)\.\.\s+(?:code-block|code)::", line)
                if m_dir:
                    indent = len(m_dir.group(1))
                    is_code[i] = True
                    j = i + 1
                    while j < n:
                        if not lines[j].strip():
                            is_code[j] = True
                            j += 1
                            continue
                        line_indent = len(lines[j]) - len(lines[j].lstrip())
                        if line_indent > indent:
                            is_code[j] = True
                            j += 1
                        else:
                            break
                    i = j - 1
                elif line.rstrip().endswith("::") and not line.strip().startswith(".."):
                    base_indent = len(line) - len(line.lstrip())
                    j = i + 1
                    while j < n and not lines[j].strip():
                        j += 1
                    if j < n and len(lines[j]) - len(lines[j].lstrip()) > base_indent:
                        code_indent = len(lines[j]) - len(lines[j].lstrip())
                        while j < n:
                            if not lines[j].strip():
                                is_code[j] = True
                                j += 1
                                continue
                            if len(lines[j]) - len(lines[j].lstrip()) >= code_indent:
                                is_code[j] = True
                                j += 1
                            else:
                                break
                        i = j - 1
        else:
            is_code[i] = True
            if stripped.startswith(fence_char * fence_len):
                in_fence = False
        i += 1

    # 2. Identificar encabezados fuera de bloques de código
    headings = []
    i = 0
    while i < n:
        if is_code[i]:
            i += 1
            continue
        line = lines[i]
        stripped = line.strip()
        if fmt in ("md", "mdx"):
            m = re.match(r"^(#{1,6})\s+(.+)$", stripped)
            if m:
                level = len(m.group(1))
                clean = m.group(2).strip()
                hashes = "#" * level
                headings.append({
                    "start_line": i + 1,
                    "end_line": i + 1,
                    "level": level,
                    "marker": f"{hashes} {clean}",
                    "clean_title": clean,
                })
            elif i + 1 < n and not is_code[i + 1]:
                next_str = lines[i + 1].strip()
                if stripped and (re.match(r"^={3,}\s*$", next_str) or re.match(r"^-{3,}\s*$", next_str)):
                    level = 1 if next_str[0] == "=" else 2
                    hashes = "#" * level
                    headings.append({
                        "start_line": i + 1,
                        "end_line": i + 2,
                        "level": level,
                        "marker": f"{hashes} {stripped}",
                        "clean_title": stripped,
                    })
                    i += 1
        elif fmt == "adoc":
            m = re.match(r"^(={1,5})\s+(.+)$", stripped)
            if m:
                level = len(m.group(1))
                clean = m.group(2).strip()
                eqs = "=" * level
                headings.append({
                    "start_line": i + 1,
                    "end_line": i + 1,
                    "level": level,
                    "marker": f"{eqs} {clean}",
                    "clean_title": clean,
                })
        elif fmt == "rst":
            m_under = re.match(r"^([=\-~^\"`#])\1{2,}\s*$", stripped)
            if m_under and i > 0 and not is_code[i - 1]:
                prev_str = lines[i - 1].strip()
                if prev_str and not prev_str.startswith("..") and not re.match(r"^([=\-~^\"`#])\1{2,}\s*$", prev_str):
                    char = m_under.group(1)
                    level_map = {"=": 1, "-": 2, "~": 3, "`": 3, "^": 4, "\"": 5, "#": 1}
                    level = level_map.get(char, 2)
                    start_l = i
                    if i >= 2 and re.match(r"^([=\-~^\"`#])\1{2,}\s*$", lines[i - 2].strip()):
                        start_l = i - 1
                    headings.append({
                        "start_line": start_l,
                        "end_line": i + 1,
                        "level": level,
                        "marker": prev_str,
                        "clean_title": prev_str,
                    })
        i += 1

    # 3. Particionar el documento en secciones basadas en encabezados
    sections = []
    first_h_line = headings[0]["start_line"] if headings else n + 1
    if first_h_line > 1:
        pre_lines = [(idx + 1, lines[idx], is_code[idx]) for idx in range(first_h_line - 1)]
        if any(l[1].strip() for l in pre_lines):
            sections.append({
                "start_line": 1,
                "end_line": first_h_line - 1,
                "route": "Documento",
                "clean_title": "Documento",
                "body_lines": pre_lines,
            })

    stack = []
    for idx_h, h in enumerate(headings):
        while stack and stack[-1]["level"] >= h["level"]:
            stack.pop()
        stack.append(h)

        if fmt in ("md", "mdx", "adoc"):
            route = " > ".join(item["marker"] for item in stack)
        else:
            route = " > ".join(item["clean_title"] for item in stack)

        clean_title = stack[-1]["clean_title"]
        start_body = h["end_line"]
        end_body = (headings[idx_h + 1]["start_line"] - 1) if idx_h + 1 < len(headings) else n
        body_lines = [(line_idx + 1, lines[line_idx], is_code[line_idx]) for line_idx in range(start_body, end_body)]

        sections.append({
            "start_line": h["start_line"],
            "end_line": end_body,
            "route": route,
            "clean_title": clean_title,
            "body_lines": body_lines,
        })

    if not sections and not headings:
        # Documento sin títulos
        all_lines = [(idx + 1, lines[idx], is_code[idx]) for idx in range(n)]
        sections.append({
            "start_line": 1,
            "end_line": n,
            "route": "Documento",
            "clean_title": "Documento",
            "body_lines": all_lines,
        })

    # 4. Convertir cada sección en fragmentos de hasta ~800 caracteres
    chunks = []
    for sec in sections:
        route = sec["route"]
        clean_title = sec["clean_title"]
        prefix = route + "\n\n"
        prefix_len = len(prefix)

        blocks = []
        b_lines = sec["body_lines"]
        bi = 0
        while bi < len(b_lines):
            line_no, l_text, l_is_code = b_lines[bi]
            if not l_text.strip():
                bi += 1
                continue
            if l_is_code:
                c_start = line_no
                c_text = [l_text]
                bi += 1
                while bi < len(b_lines):
                    l_no2, l_t2, l_c2 = b_lines[bi]
                    if l_c2:
                        c_text.append(l_t2)
                        bi += 1
                    elif not l_t2.strip() and bi + 1 < len(b_lines) and b_lines[bi + 1][2]:
                        c_text.append(l_t2)
                        bi += 1
                    else:
                        break
                blocks.append({
                    "is_code": True,
                    "text": "\n".join(c_text),
                    "start_line": c_start,
                    "end_line": b_lines[bi - 1][0],
                })
            else:
                p_start = line_no
                p_text = [l_text]
                bi += 1
                while bi < len(b_lines):
                    l_no2, l_t2, l_c2 = b_lines[bi]
                    if l_c2 or not l_t2.strip():
                        break
                    p_text.append(l_t2)
                    bi += 1
                blocks.append({
                    "is_code": False,
                    "text": "\n".join(p_text),
                    "start_line": p_start,
                    "end_line": b_lines[bi - 1][0],
                })

        if not blocks:
            chunks.append({
                "line": sec["start_line"],
                "end_line": sec["end_line"],
                "symbol_name": clean_title,
                "symbol_kind": "section",
                "content": route,
            })
            continue

        curr_blocks = []
        curr_len = prefix_len
        curr_start_line = sec["start_line"]

        for b in blocks:
            b_text = b["text"]
            b_len = len(b_text)
            sep_len = 2 if curr_blocks else 0

            if curr_blocks and (curr_len + sep_len + b_len > MAX_DOC_CHARS):
                content = prefix + "\n\n".join(blk["text"] for blk in curr_blocks)
                chunks.append({
                    "line": curr_start_line,
                    "end_line": curr_blocks[-1]["end_line"],
                    "symbol_name": clean_title,
                    "symbol_kind": "section",
                    "content": content,
                })
                curr_blocks = []
                curr_len = prefix_len
                curr_start_line = b["start_line"]
                sep_len = 0

            if not b["is_code"] and (prefix_len + b_len > MAX_DOC_CHARS):
                pieces = _split_long_paragraph(b_text, MAX_DOC_CHARS - prefix_len)
                line_offset = b["start_line"]
                for piece in pieces:
                    piece_lines = piece.count("\n")
                    piece_end = line_offset + piece_lines
                    content = prefix + piece
                    chunks.append({
                        "line": curr_start_line if curr_start_line is not None else line_offset,
                        "end_line": piece_end,
                        "symbol_name": clean_title,
                        "symbol_kind": "section",
                        "content": content,
                    })
                    line_offset = piece_end + 1
                    curr_start_line = None
                curr_blocks = []
                curr_len = prefix_len
            else:
                curr_blocks.append(b)
                curr_len += sep_len + b_len
                if curr_start_line is None:
                    curr_start_line = b["start_line"]

        if curr_blocks:
            content = prefix + "\n\n".join(blk["text"] for blk in curr_blocks)
            chunks.append({
                "line": curr_start_line if curr_start_line is not None else curr_blocks[0]["start_line"],
                "end_line": curr_blocks[-1]["end_line"],
                "symbol_name": clean_title,
                "symbol_kind": "section",
                "content": content,
            })

    return chunks, [], []


def chunk_markdown(text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]], List[Dict[str, str]]]:
    """Divide archivos Markdown respetando encabezados (# y ##) y fragmentos de hasta ~800 caracteres."""
    return chunk_doc_generic(text, fmt="md")


def chunk_rst(text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]], List[Dict[str, str]]]:
    """Divide archivos reStructuredText (.rst) respetando encabezados subrayados (===, ---, ~~~)."""
    return chunk_doc_generic(text, fmt="rst")


def chunk_adoc(text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]], List[Dict[str, str]]]:
    """Divide archivos AsciiDoc (.adoc) respetando encabezados (=, ==, ===)."""
    return chunk_doc_generic(text, fmt="adoc")


def chunk_fallback(
    text: str,
    chunk_size: int = 1400,
    overlap: int = 150,
    start_offset_line: int = 1,
    symbol_name: str = "",
    symbol_kind: str = "text",
) -> List[Dict[str, Any]]:
    """Fallback por líneas limpias sin cortar palabras."""
    chunks = []
    lines = text.splitlines(keepends=True)
    if not lines:
        return chunks

    cur_chunk_lines = []
    cur_chunk_len = 0
    cur_start_line = start_offset_line

    for i, line in enumerate(lines):
        line_num = start_offset_line + i
        cur_chunk_lines.append(line)
        cur_chunk_len += len(line)

        if cur_chunk_len >= chunk_size:
            chunk_content = "".join(cur_chunk_lines).strip()
            if len(chunk_content) >= MIN_CHUNK_CHARS:
                chunks.append({
                    "line": cur_start_line,
                    "end_line": line_num,
                    "symbol_name": symbol_name,
                    "symbol_kind": symbol_kind,
                    "content": chunk_content,
                })
            overlap_lines = max(1, int(len(cur_chunk_lines) * (overlap / chunk_size)))
            cur_chunk_lines = cur_chunk_lines[-overlap_lines:]
            cur_chunk_len = sum(len(l) for l in cur_chunk_lines)
            cur_start_line = line_num - len(cur_chunk_lines) + 1

    if cur_chunk_lines:
        chunk_content = "".join(cur_chunk_lines).strip()
        if len(chunk_content) >= MIN_CHUNK_CHARS:
            chunks.append({
                "line": cur_start_line,
                "end_line": start_offset_line + len(lines),
                "symbol_name": symbol_name,
                "symbol_kind": symbol_kind,
                "content": chunk_content,
            })

    return chunks


RE_SQL_STMT = re.compile(
    r"^\s*(CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW|FUNCTION|PROCEDURE|TRIGGER|INDEX)|ALTER\s+TABLE)\s+([A-Za-z0-9_.\"]+)",
    re.IGNORECASE | re.MULTILINE
)


def chunk_sql(text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]], List[Dict[str, str]]]:
    """Divide archivos SQL por sentencias DDL/DML principales."""
    chunks = []
    matches = list(RE_SQL_STMT.finditer(text))
    if not matches:
        return chunk_fallback(text, symbol_kind="sql"), [], []

    for i, m in enumerate(matches):
        start_char = m.start()
        end_char = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start_char:end_char].strip()
        name = m.group(2).replace('"', '').strip()
        start_line = text[:start_char].count('\n') + 1
        end_line = start_line + block.count('\n')
        chunks.append({
            "line": start_line,
            "end_line": end_line,
            "symbol_name": name,
            "symbol_kind": "sql",
            "content": block[:MAX_CHUNK_CHARS],
        })
    return chunks, [], []


def parse_and_chunk_file(file_path: Path, text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]], List[Dict[str, str]]]:
    """Función de entrada: devuelve (chunks, imports, exports)."""
    suffix = file_path.suffix.lower()

    if suffix in (".md", ".mdx"):
        return chunk_markdown(text)

    if suffix == ".rst":
        return chunk_rst(text)

    if suffix == ".adoc":
        return chunk_adoc(text)

    if suffix == ".sql":
        return chunk_sql(text)

    if TREE_SITTER_AVAILABLE and suffix in LANG_MAP:
        lang = LANG_MAP[suffix]
        try:
            return chunk_with_tree_sitter(file_path, text, lang)
        except Exception:
            fallback_chunks = chunk_fallback(text)
            imps, exps = extract_imports_and_exports(text)
            return fallback_chunks, imps, exps

    fallback_chunks = chunk_fallback(text)
    imps, exps = extract_imports_and_exports(text)
    return fallback_chunks, imps, exps


def chunk_file(file_path: Path, text: str) -> List[Dict[str, Any]]:
    """Devuelve únicamente la lista de chunks para compatibilidad."""
    chunks, _, _ = parse_and_chunk_file(file_path, text)
    return chunks
