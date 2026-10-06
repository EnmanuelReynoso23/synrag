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
MIN_CHUNK_CHARS = 35

RE_TS_SYM = re.compile(r"(?:export\s+(?:default\s+)?)?(?:async\s+)?(?:function\*?|class|interface|type|enum|const|let|var)\s+([A-Za-z0-9_$]+)")
RE_PY_SYM = re.compile(r"(?:async\s+)?(?:def|class)\s+([A-Za-z0-9_]+)")
RE_IMPORT_TS = re.compile(r"""import\s+(?:type\s+)?(?:([A-Za-z0-9_$]+)|\{([^}]+)\}|\*\s+as\s+([A-Za-z0-9_$]+))\s+from\s+['"]([^'"]+)['"]""")
RE_IMPORT_PY = re.compile(r"""(?:from\s+([A-Za-z0-9_.]+)\s+import\s+([^#\n]+)|import\s+([A-Za-z0-9_.]+))""")


def extract_symbol_and_kind(node_text: str, ntype: str) -> Tuple[Optional[str], str]:
    """Extrae el nombre del símbolo y clasifica su tipo sintáctico."""
    name = None
    first_lines = "\n".join(node_text.splitlines()[:3])

    m = RE_TS_SYM.search(first_lines) or RE_PY_SYM.search(first_lines)
    if m:
        name = m.group(1)

    kind = "code"
    if "function" in ntype or "method" in ntype or "def " in first_lines:
        kind = "function"
        if name and name.startswith("use") and len(name) > 3 and name[3].isupper():
            kind = "hook"
    elif "class" in ntype or "struct" in ntype or "class " in first_lines:
        kind = "class"
    elif "interface" in ntype or "interface " in first_lines:
        kind = "interface"
    elif "type" in ntype or "type " in first_lines:
        kind = "type"
    elif "enum" in ntype or "enum " in first_lines:
        kind = "enum"
    elif "declaration" in ntype or "statement" in ntype:
        kind = "variable"
        if name and name.startswith("use") and len(name) > 3 and name[3].isupper():
            kind = "hook"

    return name, kind


def extract_imports_and_exports(text: str) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """Extrae dependencias de importación y exportación de forma rápida y segura."""
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
        raw_nodes = [
            (str(n.type), int(n.start_byte), int(n.end_byte))
            for n in tree.root_node.children
        ]
        del tree
    except Exception:
        fallback_chunks = chunk_fallback(text)
        imps, exps = extract_imports_and_exports(text)
        return fallback_chunks, imps, exps

    if not raw_nodes:
        fallback_chunks = chunk_fallback(text)
        imps, exps = extract_imports_and_exports(text)
        return fallback_chunks, imps, exps

    imps, exps = extract_imports_and_exports(text)

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
        start_line = code_bytes.count(b"\n", 0, start_byte) + 1
        end_line = start_line + code_bytes.count(b"\n", start_byte, e_byte)

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


def chunk_markdown(text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]], List[Dict[str, str]]]:
    """Divide archivos Markdown respetando los encabezados (# y ##)."""
    lines = text.splitlines()
    chunks = []
    current_title = "Documento"
    current_lines = []
    start_line = 1

    re_header = re.compile(r"^(#{1,3})\s+(.+)$")

    for idx, line in enumerate(lines, start=1):
        m = re_header.match(line.strip())
        if m and current_lines:
            chunk_content = "\n".join(current_lines).strip()
            if len(chunk_content) >= MIN_CHUNK_CHARS:
                chunks.append({
                    "line": start_line,
                    "end_line": idx - 1,
                    "symbol_name": current_title,
                    "symbol_kind": "section",
                    "content": chunk_content,
                })
            current_lines = [line]
            current_title = m.group(2).strip()
            start_line = idx
        else:
            if not current_lines:
                start_line = idx
                if m:
                    current_title = m.group(2).strip()
            current_lines.append(line)

    if current_lines:
        chunk_content = "\n".join(current_lines).strip()
        if len(chunk_content) >= MIN_CHUNK_CHARS:
            chunks.append({
                "line": start_line,
                "end_line": len(lines),
                "symbol_name": current_title,
                "symbol_kind": "section",
                "content": chunk_content,
            })

    return (chunks if chunks else chunk_fallback(text)), [], []


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

    if suffix == ".md":
        return chunk_markdown(text)

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
