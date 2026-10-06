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

HOME = Path.home()
DB_PATH = HOME / ".local/share/lancedb-hub/data"
TABLE_NAME = "desktop_files"

# Directorios a escanear (carpeta base, nombre de proyecto fijo o None)
SCAN_DIRECTORIES = [
    (HOME / "AsistoYA" / "Proyectos", None),
    (HOME / "Proyectos", None),
    (HOME / "Documentos" / "AsistoYA", "documentos-asistoya"),
    (HOME / ".claude" / "projects" / "-home-reyno" / "memory", "memoria-claude"),
    (HOME / ".config" / "hypr", "hypr"),
    (HOME / ".config" / "caelestia", "caelestia"),
    (HOME / ".config" / "quickshell", "quickshell"),
]

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
    ".scss", ".conf", ".sql", ".qml", ".desktop",
}

# Credenciales por nombre de archivo
RE_ARCHIVO_SENSIBLE = re.compile(
    r"(?i)(credential|secret|service[-_]?account|adminsdk|google-services|"
    r"\.pem$|\.key$|id_rsa|keystore|\.p12$|\.env)"
)

# Ocultamiento de secretos dentro de contenido
OCULTO = "[SECRETO-OCULTO]"
RE_PEM = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)",
    re.S,
)
RE_TOKENS = re.compile(
    r"\b(?:sk-[A-Za-z0-9_\-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"
    r"|xox[bpoas]-[A-Za-z0-9\-]{20,}|AIza[0-9A-Za-z_\-]{30,}|AKIA[0-9A-Z]{16}"
    r"|standard_[a-f0-9]{40,}|re_[A-Za-z0-9]{20,})\b"
)
RE_ASIGNACION = re.compile(
    r"""(?i)((?:api[_-]?key|secret|passw(?:or)?d|token|private[_-]?key|client[_-]?secret)"""
    r"""[A-Za-z0-9_]*["']?\s*[:=]\s*["']?)([A-Za-z0-9_\-\./+=]{16,})"""
)

MAX_FILE_SIZE = 250 * 1024  # 250 KB


def get_db():
    DB_PATH.mkdir(parents=True, exist_ok=True)
    return lancedb.connect(str(DB_PATH))


def ocultar_secretos(texto: str) -> str:
    texto = RE_PEM.sub(OCULTO, texto)
    texto = RE_TOKENS.sub(OCULTO, texto)
    return RE_ASIGNACION.sub(lambda m: m.group(1) + OCULTO, texto)


def should_index(file_path: Path, base_dir: Path) -> bool:
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
    print("[INFO] Indexando en LanceDB Hub (v3 AST + FlashRank + Grafo de Impacto)...")
    t0 = time.time()
    db = get_db()
    records = []
    impact_records = []
    files_indexed = 0
    ocultos = 0

    for base_dir, fixed_project in SCAN_DIRECTORIES:
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

                    rel_home = full.relative_to(HOME)
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
    tbl = db.create_table(TABLE_NAME, data=records, mode="overwrite")
    try:
        from lancedb.index import FTS
        tbl.create_index(vector_column_name=None, config=FTS(), replace=True)
    except Exception:
        try:
            tbl.create_fts_index("content", replace=True)
        except Exception as e:
            print(f"Nota: FTS index {e}")

    try:
        tbl.optimize(cleanup_older_than=timedelta(seconds=0))
    except Exception as e:
        print(f"Nota: limpieza de versiones {e}")

    # Inicializar grafo de impacto
    impact.init_impact_table(db, impact_records)

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

    for b_dir, f_proj in SCAN_DIRECTORIES:
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
            rel_home = str(full.relative_to(HOME))
            if TABLE_NAME in db.table_names():
                db.open_table(TABLE_NAME).delete(f"rel_path = '{rel_home}'")
            if impact.IMPACT_TABLE in db.table_names():
                db.open_table(impact.IMPACT_TABLE).delete(f"imported_by = '{rel_home}'")
            return True

        raw = full.read_text(encoding="utf-8", errors="ignore").strip()
        if len(raw) < 10:
            return False

        content = ocultar_secretos(raw)
        rel_home = full.relative_to(HOME)
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
            tbl.add(new_records)

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


def search_desktop(
    query: str,
    limit: int = 5,
    project: str | None = None,
    use_rerank: bool = True,
    check_impact: bool = True
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
    db = get_db()
    if TABLE_NAME not in db.table_names():
        print("[AVISO] Aun sin indice. Ejecuta: ai-search --index")
        return []

    # 1. Caché de consultas
    cached = cache.get_cached_results(db, query, project=project)
    if cached is not None:
        return cached[:limit]

    tbl = db.open_table(TABLE_NAME)
    candidates = []

    try:
        q = tbl.search(query, query_type="fts")
        if project:
            clean_proj = project.replace(chr(39), "")
            q = q.where(f"project = '{clean_proj}'")
        candidates = q.limit(max(limit * 5, 25)).to_pandas().to_dict(orient="records")
    except Exception:
        try:
            q = tbl.search(query)
            if project:
                clean_proj = project.replace(chr(39), "")
                q = q.where(f"project = '{clean_proj}'")
            candidates = q.limit(max(limit * 5, 25)).to_pandas().to_dict(orient="records")
        except Exception:
            return []

    if not candidates:
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

    # 4. Guardar en caché
    try:
        cache.save_cached_results(db, query, reranked, project=project)
    except Exception:
        pass

    return reranked


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
