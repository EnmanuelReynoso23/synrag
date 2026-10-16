#!/usr/bin/env python3
"""
LanceDB Desktop Memory & Indexer (v3, 6-oct-2026)

Motor de código local:
  - Troceo por AST: funciones, clases, hooks e interfaces completas.
  - Reordenado FlashRank en CPU que puntúa la relevancia (0.0 a 1.0).
  - Grafo de impacto: qué archivos importan cada símbolo.
  - Caché de consultas repetidas (~9 ms).
  - Observador opcional que reindexa solo el archivo guardado.
  - Redacción de secretos: oculta patrones de secretos y credenciales antes de indexar.
"""

import os
import re
import sys
import time
import warnings
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import timedelta
import lancedb

# Módulos internos de LanceDB Hub
sys.path.insert(0, str(Path(__file__).parent))
from chunker import parse_and_chunk_file, LANG_MAP
import impact
import ranker
import cache

try:
    import synrag_crawler
    HAVE_RUST_CRAWLER = True
except ImportError:
    HAVE_RUST_CRAWLER = False

HOME = Path.home()
DB_PATH = Path(os.environ.get("SYNRAG_DB_PATH") or HOME / ".local/share/lancedb-hub/data")
TABLE_NAME = "desktop_files"

# Carpetas a indexar: (carpeta base, nombre de proyecto fijo o None). Con None, cada subcarpeta de
# primer nivel es un proyecto. Orden de prioridad:
#   1. SYNRAG_CARPETAS: rutas separadas por ":" (cada una puede llevar "=proyecto").
#   2. ~/.config/synrag/carpetas.txt: una ruta por linea, "ruta = proyecto" opcional, "#" comenta.
#   3. Deteccion: carpetas de codigo habituales que existan y la memoria de Claude Code.
CARPETAS_HABITUALES = (
    "Proyectos", "Projects", "projects", "proyectos", "code", "Code", "dev", "Dev", "src",
    "repos", "Repos", "workspace", "Workspace", "git", "GitHub", "Documents/GitHub",
    "Documentos/GitHub", "Developer",
)


def archivo_de_carpetas() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config")
    return base / "synrag" / "carpetas.txt"


def _parsear_carpeta(linea: str) -> Optional[tuple]:
    linea = linea.split("#", 1)[0].strip()
    if not linea:
        return None
    ruta, _, proyecto = linea.partition("=")
    return (Path(os.path.expandvars(ruta.strip())).expanduser(), proyecto.strip() or None)


def detectar_carpetas() -> List[tuple]:
    # en macOS el disco no distingue mayusculas: Proyectos y proyectos son la misma carpeta
    carpetas, vistas = [], set()
    for c in CARPETAS_HABITUALES:
        ruta = HOME / c
        if not ruta.is_dir():
            continue
        st = ruta.stat()
        if (st.st_dev, st.st_ino) not in vistas:
            vistas.add((st.st_dev, st.st_ino))
            carpetas.append((ruta, None))
    for memoria in sorted((HOME / ".claude" / "projects").glob("*/memory")):
        carpetas.append((memoria, "memoria-claude"))
    return carpetas


def cargar_carpetas() -> List[tuple]:
    entorno = os.environ.get("SYNRAG_CARPETAS")
    if entorno:
        lineas = entorno.split(os.pathsep)
    elif archivo_de_carpetas().is_file():
        lineas = archivo_de_carpetas().read_text(encoding="utf-8").splitlines()
    else:
        return detectar_carpetas()
    vistas, carpetas = set(), []
    for linea in lineas:
        c = _parsear_carpeta(linea)
        if c and c[0] not in vistas:
            vistas.add(c[0])
            carpetas.append(c)
    return carpetas




IGNORE_DIRS = {
    "node_modules", ".git", ".venv", "venv", "__pycache__", "dist", "build",
    ".cache", ".next", ".turbo", "target", "obj", ".idea", ".vscode",
    "coverage", ".steam", "asmp-release", "proteus_extracted",
    "dataset-universidades", "Modulegit", "Codex", "playwright-report",
    "test-results", "android", "ios", "pnpm-store", "storybook-static",
    "appwrite-dist",
}
IGNORE_DIR_SUBSTR = (".git-backup", "-backup-", ".bak", "-dist")

IGNORE_FILES = {
    "pnpm-lock.yaml", "package-lock.json", "yarn.lock", "bun.lock",
    "composer.lock", "Cargo.lock", "poetry.lock",
}

ALLOWED_EXTENSIONS = {
    ".py", ".js", ".mjs", ".cjs", ".ts", ".jsx", ".tsx", ".lua", ".sh", ".bash",
    ".zsh", ".md", ".json", ".yaml", ".yml", ".toml", ".txt", ".html", ".css",
    ".scss", ".conf", ".sql", ".qml", ".desktop", ".rst", ".mdx", ".adoc",
}

DOC_EXTENSIONS = {".md", ".mdx", ".rst", ".adoc", ".txt"}


def _es_doc(r: dict) -> bool:
    ext = (r.get("extension") or "").lower()
    if not ext:
        ext = Path(r.get("rel_path", "")).suffix.lower()
    return ext in DOC_EXTENSIONS


# Credenciales por nombre de archivo
RE_ARCHIVO_SENSIBLE = re.compile(
    r"(?i)(credential|secret|service[-_]?account|adminsdk|google-services|"
    r"\.pem$|\.key$|id_rsa|keystore|\.p12$|\.env)"
)

# Ocultamiento de secretos dentro de contenido
OCULTO = "[SECRETO-OCULTO]"
# Solo una llave de verdad (cabecera + cuerpo base64): mencionar la cabecera en un comentario no
# debe borrar el resto del archivo.
RE_PEM = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----\s*(?:[A-Za-z0-9+/=]{16,}\s*)+(?:-----END [A-Z ]*PRIVATE KEY-----)?"
)
RE_TOKENS = re.compile(
    r"\b(?:sk-[A-Za-z0-9_\-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"
    r"|xox[bpoas]-[A-Za-z0-9\-]{20,}|AIza[0-9A-Za-z_\-]{30,}|AKIA[0-9A-Z]{16}"
    r"|standard_[a-f0-9]{40,}|re_[A-Za-z0-9]{20,}|AQ\.[A-Za-z0-9_\-]{40,})\b"
)
RE_ASIGNACION = re.compile(
    r"""(?i)((?:api[_-]?key|secret|passw(?:or)?d|token|private[_-]?key|client[_-]?secret)"""
    r"""[A-Za-z0-9_]*["']?\s*[:=]\s*["']?)([A-Za-z0-9_\-\./+=]{16,})"""
)

MAX_FILE_SIZE = 250 * 1024  # 250 KB


RE_PALABRA_COMPUESTA = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+|[a-z0-9]+(?:[A-Z][a-z0-9]*)+|[A-Z]{2,}[a-z]+[A-Za-z0-9]*")
RE_PARTES = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")


def terminos_de_busqueda(contenido: str, symbol_name: str = "", archivo: str = "") -> str:
    """Texto que indexa el FTS: el contenido mas las palabras de los nombres compuestos
    (`esSinCupo` -> `es sin cupo`, `listar_todos` -> `listar todos`) y del nombre del archivo,
    para que una consulta en lenguaje normal encuentre identificadores."""
    extra = []
    vistos = set()
    for ident in RE_PALABRA_COMPUESTA.findall(f"{symbol_name} {archivo} {contenido}"):
        if ident in vistos:
            continue
        vistos.add(ident)
        extra.append(" ".join(p.lower() for p in RE_PARTES.findall(ident)))
    if not extra:
        return contenido
    return contenido + "\n" + " ".join(extra)


def _con_terminos(registros: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for r in registros:
        r["terms"] = terminos_de_busqueda(r["content"], r.get("symbol_name", ""), r.get("filename", ""))
    return registros


def _has_table(db: lancedb.DBConnection, table_name: str) -> bool:
    try:
        res = db.list_tables()
        tables = res.tables if hasattr(res, "tables") else res
        return table_name in tables
    except Exception:
        try:
            return table_name in db.table_names()
        except Exception:
            return False


def get_db():
    DB_PATH.mkdir(parents=True, exist_ok=True)
    return lancedb.connect(str(DB_PATH))


def ocultar_secretos(texto: str) -> str:
    if HAVE_RUST_CRAWLER:
        return synrag_crawler.mask_secrets(texto)[0]
    texto = RE_PEM.sub(OCULTO, texto)
    texto = RE_TOKENS.sub(OCULTO, texto)
    return RE_ASIGNACION.sub(lambda m: m.group(1) + OCULTO, texto)


def should_index(file_path: Path, base_dir: Path) -> bool:
    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False

    if HAVE_RUST_CRAWLER:
        if synrag_crawler.should_index(str(file_path), str(base_dir)):
            return True
        if file_path.suffix.lower() not in {".rst", ".mdx", ".adoc"}:
            return False

    try:
        rel = file_path.relative_to(base_dir)
    except ValueError:
        return False

    for part in rel.parts[:-1]:
        if part in IGNORE_DIRS or part.startswith("."):
            return False
        if any(s in part for s in IGNORE_DIR_SUBSTR):
            return False

    if file_path.name in IGNORE_FILES or RE_ARCHIVO_SENSIBLE.search(file_path.name):
        return False

    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False

    try:
        if file_path.stat().st_size > MAX_FILE_SIZE:
            return False
    except OSError:
        return False

    return True



def index_desktop():
    """Indexa por completo todos los proyectos con Tree-sitter AST y Grafo de Impacto."""
    engine_tipo = "v3 AST + Rust Crawler + FlashRank + Grafo de Impacto" if HAVE_RUST_CRAWLER else "v3 AST + FlashRank + Grafo de Impacto"
    print(f"[INFO] Indexando en LanceDB Hub ({engine_tipo})...")
    t0 = time.time()
    db = get_db()
    records = []
    impact_records = []
    files_indexed = 0
    ocultos = 0

    if HAVE_RUST_CRAWLER:
        scan_configs = [(str(b_dir), f_proj) for b_dir, f_proj in cargar_carpetas() if b_dir.exists()]
        scanned_files = synrag_crawler.crawl_directories(scan_configs, MAX_FILE_SIZE)
        for sf in scanned_files:
            full = Path(sf.path)
            content = sf.content
            if sf.secrets_masked:
                ocultos += 1

            rel_home = sf.rel_path
            project = sf.project
            mtime = sf.mtime

            try:
                # Tree-sitter AST semantic chunking + dependency extraction
                chunks, imports, _ = parse_and_chunk_file(full, content)
                if not chunks:
                    continue

                for i, chk in enumerate(chunks):
                    records.append({
                        "id": f"{rel_home}#{i}",
                        "file_path": sf.path,
                        "rel_path": str(rel_home),
                        "project": project,
                        "filename": sf.filename,
                        "extension": sf.extension,
                        "chunk_index": i,
                        "line": int(chk.get("line", 1)),
                        "end_line": int(chk.get("end_line", chk.get("line", 1))),
                        "symbol_name": str(chk.get("symbol_name") or ""),
                        "symbol_kind": str(chk.get("symbol_kind") or "code"),
                        "content": chk["content"],
                        "mtime": float(mtime),
                    })

                # Registrar dependencias en el grafo de impacto
                for imp in imports:
                    impact_records.append({
                        "symbol": imp["symbol"],
                        "imported_by": str(rel_home),
                        "source": imp.get("source", ""),
                        "project": project,
                    })

                files_indexed += 1
            except Exception:
                pass

        scanned_paths = {sf.path for sf in scanned_files}
        for base_dir, fixed_project in cargar_carpetas():
            if not base_dir.exists():
                continue
            for root, dirs, names in os.walk(base_dir):
                dirs[:] = [
                    d for d in dirs
                    if d not in IGNORE_DIRS and not d.startswith(".")
                    and not any(s in d for s in IGNORE_DIR_SUBSTR)
                ]
                if Path(root) == base_dir:
                    dirs[:] = [d for d in dirs if not (base_dir / d / ".git").is_file()]

                for name in names:
                    full = Path(root) / name
                    if str(full) in scanned_paths or not should_index(full, base_dir):
                        continue

                    try:
                        raw = full.read_text(encoding="utf-8", errors="ignore").strip()
                        if len(raw) < 10:
                            continue
                        content = ocultar_secretos(raw)
                        if content != raw:
                            ocultos += 1

                        try:
                            rel_home = full.relative_to(HOME)
                        except ValueError:
                            rel_home = full
                        rel_base = full.relative_to(base_dir)
                        project = fixed_project or (rel_base.parts[0] if len(rel_base.parts) > 1 else base_dir.name)
                        mtime = full.stat().st_mtime

                        chunks, imports, _ = parse_and_chunk_file(full, content)
                        if not chunks:
                            continue

                        for i, chk in enumerate(chunks):
                            records.append({
                                "id": f"{rel_home}#{i}",
                                "file_path": str(full),
                                "rel_path": str(rel_home),
                                "project": project,
                                "filename": full.name,
                                "extension": full.suffix.lower(),
                                "chunk_index": i,
                                "line": int(chk.get("line", 1)),
                                "end_line": int(chk.get("end_line", chk.get("line", 1))),
                                "symbol_name": str(chk.get("symbol_name") or ""),
                                "symbol_kind": str(chk.get("symbol_kind") or "code"),
                                "content": chk["content"],
                                "mtime": float(mtime),
                            })

                        for imp in imports:
                            impact_records.append({
                                "symbol": imp["symbol"],
                                "imported_by": str(rel_home),
                                "source": imp.get("source", ""),
                                "project": project,
                            })

                        files_indexed += 1
                    except Exception:
                        pass
    else:
        for base_dir, fixed_project in cargar_carpetas():
            if not base_dir.exists():
                continue
            for root, dirs, names in os.walk(base_dir):
                dirs[:] = [
                    d for d in dirs
                    if d not in IGNORE_DIRS and not d.startswith(".")
                    and not any(s in d for s in IGNORE_DIR_SUBSTR)
                ]
                if Path(root) == base_dir:
                    # Worktrees de git tienen `.git` como archivo: evitar duplicación
                    dirs[:] = [d for d in dirs if not (base_dir / d / ".git").is_file()]

                for name in names:
                    full = Path(root) / name
                    if not should_index(full, base_dir):
                        continue

                    try:
                        raw = full.read_text(encoding="utf-8", errors="ignore").strip()
                        if len(raw) < 10:
                            continue
                        content = ocultar_secretos(raw)
                        if content != raw:
                            ocultos += 1

                        try:
                            rel_home = full.relative_to(HOME)
                        except ValueError:
                            rel_home = full
                        rel_base = full.relative_to(base_dir)
                        project = fixed_project or (rel_base.parts[0] if len(rel_base.parts) > 1 else base_dir.name)
                        mtime = full.stat().st_mtime

                        # Tree-sitter AST semantic chunking + dependency extraction
                        chunks, imports, _ = parse_and_chunk_file(full, content)
                        if not chunks:
                            continue

                        for i, chk in enumerate(chunks):
                            records.append({
                                "id": f"{rel_home}#{i}",
                                "file_path": str(full),
                                "rel_path": str(rel_home),
                                "project": project,
                                "filename": full.name,
                                "extension": full.suffix.lower(),
                                "chunk_index": i,
                                "line": int(chk.get("line", 1)),
                                "end_line": int(chk.get("end_line", chk.get("line", 1))),
                                "symbol_name": str(chk.get("symbol_name") or ""),
                                "symbol_kind": str(chk.get("symbol_kind") or "code"),
                                "content": chk["content"],
                                "mtime": float(mtime),
                            })

                        # Registrar dependencias en el grafo de impacto
                        for imp in imports:
                            impact_records.append({
                                "symbol": imp["symbol"],
                                "imported_by": str(rel_home),
                                "source": imp.get("source", ""),
                                "project": project,
                            })

                        files_indexed += 1
                    except Exception:
                        pass


    print(f"[METRICAS] Archivos: {files_indexed} | Fragmentos AST: {len(records)} | Vinculos de Dependencia: {len(impact_records)}")
    if not records:
        print("[AVISO] Nada que indexar.")
        return

    # Guardar tabla principal de fragmentos
    tbl = db.create_table(TABLE_NAME, data=_con_terminos(records), mode="overwrite")
    try:
        from lancedb.index import FTS
        tbl.create_index("terms", config=FTS(), replace=True)
    except Exception:
        try:
            tbl.create_fts_index("terms", replace=True)
        except Exception as e:
            print(f"Nota: FTS index {e}")


    # Inicializar grafo de impacto
    impact.init_impact_table(db, impact_records)

    # Compactar las DOS tablas (antes el grafo de impacto nunca se compactaba: 7.836 versiones y
    # 148 MB en el equipo del autor tras unas semanas de observador)
    for nombre in (TABLE_NAME, impact.IMPACT_TABLE):
        try:
            if _has_table(db, nombre):
                db.open_table(nombre).optimize(cleanup_older_than=timedelta(seconds=0))
        except Exception as e:
            print(f"Nota: limpieza de versiones de {nombre}: {e}")

    # Limpiar caché de consultas antiguas
    cache.clear_cache(db)

    print(f"[OK] Listo en {time.time() - t0:.1f}s -> {DB_PATH}")


def index_single_file(file_path: Path) -> bool:
    """
    Reindexado de un solo archivo:
    Actualiza de forma atómica un único archivo modificado (~8 ms).
    """
    full = file_path.resolve()
    base_dir = None
    fixed_proj = None

    for b_dir, f_proj in cargar_carpetas():
        try:
            if full.is_relative_to(b_dir):
                base_dir = b_dir
                fixed_proj = f_proj
                break
        except Exception:
            continue

    if not base_dir or not should_index(full, base_dir):
        return False

    try:
        if not full.exists():
            # Si el archivo fue borrado, eliminar de LanceDB
            db = get_db()
            try:
                rel_home = str(full.relative_to(HOME))
            except ValueError:
                rel_home = str(full)
            if _has_table(db, TABLE_NAME):
                db.open_table(TABLE_NAME).delete(f"rel_path = '{rel_home}'")
            if _has_table(db, impact.IMPACT_TABLE):
                db.open_table(impact.IMPACT_TABLE).delete(f"imported_by = '{rel_home}'")
            return True

        raw = full.read_text(encoding="utf-8", errors="ignore").strip()
        if len(raw) < 10:
            return False

        content = ocultar_secretos(raw)
        try:
            rel_home = full.relative_to(HOME)
        except ValueError:
            rel_home = full
        rel_base = full.relative_to(base_dir)
        project = fixed_proj or (rel_base.parts[0] if len(rel_base.parts) > 1 else base_dir.name)
        mtime = full.stat().st_mtime

        chunks, imports, _ = parse_and_chunk_file(full, content)
        if not chunks:
            return False

        new_records = []
        for i, chk in enumerate(chunks):
            new_records.append({
                "id": f"{rel_home}#{i}",
                "file_path": str(full),
                "rel_path": str(rel_home),
                "project": project,
                "filename": full.name,
                "extension": full.suffix.lower(),
                "chunk_index": i,
                "line": int(chk.get("line", 1)),
                "end_line": int(chk.get("end_line", chk.get("line", 1))),
                "symbol_name": str(chk.get("symbol_name") or ""),
                "symbol_kind": str(chk.get("symbol_kind") or "code"),
                "content": chk["content"],
                "mtime": float(mtime),
            })

        db = get_db()
        # Actualizar tabla de código
        if TABLE_NAME in db.table_names():
            tbl = db.open_table(TABLE_NAME)
            try:
                tbl.delete(f"rel_path = '{str(rel_home)}'")
            except Exception:
                pass
            tbl.add(_con_terminos(new_records) if "terms" in tbl.schema.names else new_records)

        # Actualizar tabla de grafo de impacto
        if impact.IMPACT_TABLE in db.table_names():
            imp_tbl = db.open_table(impact.IMPACT_TABLE)
            try:
                imp_tbl.delete(f"imported_by = '{str(rel_home)}'")
            except Exception:
                pass
            if imports:
                imp_records = [{
                    "symbol": imp["symbol"],
                    "imported_by": str(rel_home),
                    "source": imp.get("source", ""),
                    "project": project,
                } for imp in imports]
                imp_tbl.add(imp_records)

        return True
    except Exception as e:
        return False


RE_IDENTIFICADOR = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]{2,}$")
PRIORIDAD_KIND = {"function": 0, "hook": 0, "method": 1, "class": 2, "interface": 3, "type": 3, "enum": 3, "variable": 4}


def raiz_de_proyecto(nombre_o_ruta: str) -> Optional[Path]:
    """Carpeta de un proyecto, dada su ruta o su nombre en el indice (`mi-proyecto`)."""
    if not nombre_o_ruta:
        return None
    p = Path(nombre_o_ruta).expanduser()
    if p.is_dir():
        return p.resolve()
    for base, fijo in cargar_carpetas():
        if fijo == nombre_o_ruta and base.is_dir():
            return base
        if fijo is None and (base / nombre_o_ruta).is_dir():
            return base / nombre_o_ruta
    return None


def resolver_archivo(file_path: str, project: str | None = None) -> tuple[Optional[Path], List[str]]:
    """Ruta absoluta de un archivo dado por ruta completa, relativa o solo su final
    (`asistencia.servicio.ts`, `src/x/y.ts`). Busca en el indice, no recorre el disco, y respeta
    `project`. Devuelve (ruta o None, otras coincidencias para avisar de la ambiguedad)."""
    p = Path(file_path).expanduser()
    if p.is_absolute() and p.is_file():
        return p.resolve(), []
    if (Path.cwd() / p).is_file() and not project:
        return (Path.cwd() / p).resolve(), []
    db = get_db()
    if TABLE_NAME not in db.table_names():
        return None, []
    sufijo = str(p).lstrip("./").replace("'", "")
    filtro = f"(rel_path = '{sufijo}' OR rel_path LIKE '%/{sufijo}')"
    if project:
        filtro += f" AND project = '{project.replace(chr(39), '')}'"
    try:
        filas = db.open_table(TABLE_NAME).search().where(filtro).select(["file_path", "project"]).limit(400).to_list()
    except Exception:
        return None, []
    rutas = sorted({f["file_path"] for f in filas if Path(f["file_path"]).is_file()}, key=lambda r: (len(r), r))
    if not rutas:
        return None, []
    return Path(rutas[0]), rutas[1:6]


def _leer_lineas(ruta: str, ini: int, fin: int) -> str:
    try:
        with open(ruta, encoding="utf-8", errors="ignore") as f:
            lineas = f.read().splitlines()
        return ocultar_secretos("\n".join(lineas[ini - 1:fin]))
    except Exception:
        return ""


def buscar_definiciones(tbl, query: str, project: str | None = None, limit: int = 5, tipo: str = "") -> List[Dict[str, Any]]:
    """Si la consulta es un nombre de simbolo, devuelve sus definiciones (coincidencia exacta del nombre)."""
    nombre = query.strip()
    if not RE_IDENTIFICADOR.match(nombre):
        return []
    filtro = f"symbol_name = '{nombre}'"
    if project:
        filtro += f" AND project = '{project.replace(chr(39), '')}'"
    if tipo == "docs":
        exts_sql = ", ".join(f"'{e}'" for e in DOC_EXTENSIONS)
        filtro += f" AND extension IN ({exts_sql})"
    elif tipo == "codigo":
        exts_sql = ", ".join(f"'{e}'" for e in DOC_EXTENSIONS)
        filtro += f" AND extension NOT IN ({exts_sql})"
    try:
        filas = tbl.search().where(filtro).limit(max(limit * 4, 20)).to_list()
    except Exception:
        return []
    # Un bloque largo queda partido en varios trozos con el mismo nombre: se unen en uno y el texto
    # se lee del archivo (cubre la definicion entera y esta al dia aunque el indice no).
    grupos: Dict[tuple, List[Dict[str, Any]]] = {}
    for r in filas:
        grupos.setdefault((r.get("rel_path"), r.get("symbol_name")), []).append(r)
    salida = []
    for trozos in grupos.values():
        trozos.sort(key=lambda r: r.get("chunk_index", 0))
        r = dict(trozos[0])
        r.pop("vector", None)
        r["line"] = min(int(t.get("line", 1)) for t in trozos)
        r["end_line"] = max(int(t.get("end_line", t.get("line", 1))) for t in trozos)
        if len(trozos) > 1:
            r["content"] = _leer_lineas(r.get("file_path", ""), r["line"], r["end_line"]) or \
                "\n".join(t.get("content", "") for t in trozos)
        r["exacto"] = True
        salida.append(r)
    salida.sort(key=lambda r: (PRIORIDAD_KIND.get(r.get("symbol_kind"), 5),
                               "test" in r.get("rel_path", "").lower(),
                               not re.search(rf"\bexport\b[^\n]*\b{re.escape(nombre)}\b", r.get("content", "")),
                               len(r.get("rel_path", ""))))
    if tipo == "docs":
        salida = [r for r in salida if _es_doc(r)]
    elif tipo == "codigo":
        salida = [r for r in salida if not _es_doc(r)]
    return salida[:limit]


def search_desktop(
    query: str,
    limit: int = 5,
    project: str | None = None,
    detalle: bool = False,
    tipo: str = "",
    use_rerank: bool = True,
    check_impact: bool = True,
    **kwargs: Any,
) -> List[Dict[str, Any]]:
    """
    Búsqueda por palabras con reordenado:
    1. Revisa la caché de consultas (~9 ms).
    2. Tantivy BM25 FTS sobre LanceDB para 25 candidatos brutos.
    3. FlashRank Cross-Encoder en CPU para reordenar por relevancia (0.0 a 1.0).
    4. Grafo de impacto para inyectar advertencias de dependencias.
    5. Guarda en caché para futuras consultas idénticas.
    """
    warnings.filterwarnings("ignore")
    search_desktop.ultima_desde_cache = False
    db = get_db()
    if TABLE_NAME not in db.table_names():
        print("[AVISO] Aun sin indice. Ejecuta: ai-search --index")
        return []

    # 1. Caché de consultas
    cached = cache.get_cached_results(db, query, project=project, tipo=tipo)
    if cached is not None:
        search_desktop.ultima_desde_cache = True
        return cached[:limit]

    tbl = db.open_table(TABLE_NAME)
    candidates = []
    exactos = buscar_definiciones(tbl, query, project=project, limit=limit, tipo=tipo)

    condiciones = []
    if project:
        clean_proj = project.replace(chr(39), "")
        condiciones.append(f"project = '{clean_proj}'")
    if tipo == "docs":
        exts_sql = ", ".join(f"'{e}'" for e in DOC_EXTENSIONS)
        condiciones.append(f"extension IN ({exts_sql})")
    elif tipo == "codigo":
        exts_sql = ", ".join(f"'{e}'" for e in DOC_EXTENSIONS)
        condiciones.append(f"extension NOT IN ({exts_sql})")
    where_clause = " AND ".join(condiciones) if condiciones else None

    try:
        columna = "terms" if "terms" in tbl.schema.names else "content"
        q = tbl.search(query, query_type="fts", fts_columns=columna)
        if where_clause:
            q = q.where(where_clause)
        candidates = q.limit(max(limit * 5, 25)).to_pandas().to_dict(orient="records")
    except Exception:
        try:
            q = tbl.search(query)
            if where_clause:
                q = q.where(where_clause)
            candidates = q.limit(max(limit * 5, 25)).to_pandas().to_dict(orient="records")
        except Exception:
            candidates = []

    if tipo == "docs":
        exactos = [r for r in exactos if _es_doc(r)]
        candidates = [r for r in candidates if _es_doc(r)]
    elif tipo == "codigo":
        exactos = [r for r in exactos if not _es_doc(r)]
        candidates = [r for r in candidates if not _es_doc(r)]

    if not candidates and not exactos:
        return []

    # Diversidad: máximo 2 por archivo salvo símbolo relevante
    por_archivo = {}
    candidatos_filtrados = []
    for r in candidates:
        rel = r.get("rel_path", "")
        n = por_archivo.get(rel, 0)
        has_symbol_match = bool(r.get("symbol_name") and r["symbol_name"].lower() in query.lower())
        if n >= 2 and not has_symbol_match:
            continue
        por_archivo[rel] = n + 1
        candidatos_filtrados.append(r)

    # 2. FlashRank Cross-Encoder Reranking
    if use_rerank and ranker.FLASHRANK_AVAILABLE:
        reranked = ranker.rerank_snippets(query, candidatos_filtrados, top_k=limit)
    else:
        reranked = candidatos_filtrados[:limit]

    # Las definiciones exactas del simbolo buscado van primero
    if exactos:
        ids = {r["id"] for r in exactos}
        reranked = (exactos + [r for r in reranked if r.get("id") not in ids])[:limit]

    # Sin tipo, el codigo va antes que la documentacion: la doc repite las palabras de la pregunta y
    # ganaba al codigo (Flask, lenguaje natural: -36 % -> -16 %). Solo reordena; en un proyecto de
    # notas no cambia nada. Para buscar solo en docs: tipo="docs".
    if not tipo:
        reranked = [r for r in reranked if not _es_doc(r)] + [r for r in reranked if _es_doc(r)]

    # 3. Grafo de Impacto
    if check_impact:
        query_sym = query.strip() if re.match(r"^[A-Za-z0-9_$]+$", query.strip()) else None
        for r in reranked:
            sym = r.get("symbol_name") or (query_sym if query_sym and query_sym in r.get("content", "") else None)
            if sym and sym not in ("imports", "Documento", ""):
                dependents = impact.get_dependents(db, sym, project=r.get("project"))
                if dependents:
                    r["dependents"] = dependents
                    r["impact_warning"] = impact.format_impact_warning(dependents, sym)

    if tipo == "docs":
        reranked = [r for r in reranked if _es_doc(r)]
    elif tipo == "codigo":
        reranked = [r for r in reranked if not _es_doc(r)]

    # 4. Guardar en caché
    try:
        cache.save_cached_results(db, query, reranked, project=project, tipo=tipo)
    except Exception:
        pass

    return reranked


search_desktop.ultima_desde_cache = False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--search":
        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "asistencia"
        results = search_desktop(query, limit=5)
        for r in results:
            sym_str = f" [{r['symbol_kind']} {r['symbol_name']}]" if r.get("symbol_name") else ""
            score_str = f" (score: {r['score']:.3f})" if "score" in r else ""
            print(f"[DOC] {r['rel_path']}:{r.get('line', '?')}-{r.get('end_line', r.get('line', '?'))} (proyecto: {r['project']}){sym_str}{score_str}")
            print(f"   {r['content'][:180].replace(chr(10), ' ')}...")
            if r.get("impact_warning"):
                print(r["impact_warning"])
            print()
    elif len(sys.argv) > 1 and sys.argv[1] == "--file":
        target = Path(sys.argv[2])
        ok = index_single_file(target)
        print(f"Reindexado para {target}: {'[OK] Exito' if ok else '[FAIL] Ignorado/Error'}")
    else:
        index_desktop()
