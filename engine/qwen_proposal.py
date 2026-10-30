# =====================================================================
# SYNTAXRAG - PROPUESTA GENERADA AUTONOMAMENTE POR QWEN 2.5 CODER
# =====================================================================
# Origen: Inferencia real ejecutada en Google Cloud (Kaggle Notebook)
# Modelo: Qwen/Qwen2.5-Coder-1.5B-Instruct
# Prompt de usuario: "trabajen en synrag y haganlo mejor comprueben que sea verdadero que funcione y que sea bien de verdad"
# Salida bruta: /kaggle/working/qwen_raw_output.txt
# Tiempo de inferencia: 372.65 segundos (1,024 tokens generados)
# =====================================================================

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

RE_PRESCINDIBLE = re.compile(
    r"(?i)(copyright|\(c\)|©|all\s+rights\s+reserved|todos\s+los\s+derechos|spdx-license|licensed?\s+under|mozilla\s+public\s+license|apache\s+license|"
    r"mit\s+license|bsd\s+license|gnu\s+(?:general|lesser|affero)|"
    r"@author|@license|@copyright|@fileoverview)"
)
RE_BANNER = re.compile(r"^[/\*#\s\-=~*]{6,}$", re.M)
RE_DOC_PY = re.compile(r'("""|\'\'\')(.*?)\1', re.DOTALL)
RE_JSDOC = re.compile(r'/\*\*([\s\S]*?)\*/')

def limpiar_contenido_chunk(content: str, ext: str = "") -> str:
    """Poda comentarios de licencia, banners decorativos y docstrings redundantes para ahorrar tokens."""
    if not content:
        return ""

    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line_str = lines[i].strip()
        if (line_str.startswith(("//", "#", "/*", "*")) and RE_PRESCINDIBLE.search(line_str)) or RE_BANNER.match(line_str):
            i += 1
            continue
        break

    if i > 0 and i < len(lines):
        if lines[i - 1].strip().endswith("*/"):
            lines = lines[i:]
        elif not lines[i].strip().startswith(("*", "*/")):
            lines = lines[i:]

    return "\n".join(lines).strip()
