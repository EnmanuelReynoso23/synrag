"""
Caché local de consultas repetidas. Guarda los resultados de una consulta
(clave: el texto normalizado en minúsculas y sin espacios sobrantes, más el proyecto)
y los devuelve sin recalcular el reordenado: ~9 ms. No es una caché semántica y se vacía al reindexar.
"""

from typing import List, Dict, Any, Optional
import hashlib
import json
import time
import lancedb

CACHE_TABLE = "query_cache"
DEFAULT_TTL = 3600 * 4  # 4 horas de validez


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


def _normalize_query(q: str) -> str:
    return " ".join(q.lower().strip().split())


def _hash_query(q: str) -> str:
    return hashlib.sha256(_normalize_query(q).encode("utf-8")).hexdigest()[:16]


def get_cached_results(
    db: lancedb.DBConnection,
    query: str,
    project: Optional[str] = None,
    ttl_seconds: int = DEFAULT_TTL,
    tipo: str = "",
) -> Optional[List[Dict[str, Any]]]:
    """Busca si la consulta ya fue resuelta recientemente."""
    if not _has_table(db, CACHE_TABLE):
        return None

    tbl = db.open_table(CACHE_TABLE)
    key = f"{tipo}:{project}:{query}" if tipo else (f"{project}:{query}" if project else query)
    q_hash = _hash_query(key)

    try:
        rows = tbl.search().where(f"query_hash = '{q_hash}'").limit(1).to_list()
        if not rows:
            return None
        r = rows[0]
        if time.time() - r["timestamp"] > ttl_seconds:
            return None
        # Sin escribir en cada acierto: una lectura no debe crear versiones de la tabla (lentitud y
        # choques con el observador). Los aciertos ya los cuenta la telemetria (cache_hit).
        data = json.loads(r["results_json"])
        return data
    except Exception:
        return None


def save_cached_results(
    db: lancedb.DBConnection,
    query: str,
    results: List[Dict[str, Any]],
    project: Optional[str] = None,
    tipo: str = "",
):
    """Guarda los resultados procesados en la caché de LanceDB."""
    if not results:
        return
    key = f"{tipo}:{project}:{query}" if tipo else (f"{project}:{query}" if project else query)
    q_hash = _hash_query(key)
    norm_q = _normalize_query(query)

    record = {
        "query_hash": q_hash,
        "query_text": norm_q,
        "results_json": json.dumps(results),
        "timestamp": time.time(),
        "hit_count": 1,
    }

    try:
        if not _has_table(db, CACHE_TABLE):
            db.create_table(CACHE_TABLE, data=[record], mode="overwrite")
        else:
            tbl = db.open_table(CACHE_TABLE)
            # Si ya existía, eliminar y reinsertar
            try:
                tbl.delete(f"query_hash = '{q_hash}'")
            except Exception:
                pass
            tbl.add([record])
    except Exception:
        pass


def clear_cache(db: lancedb.DBConnection):
    """Limpia la tabla de caché cuando se reindexa."""
    try:
        if _has_table(db, CACHE_TABLE):
            db.drop_table(CACHE_TABLE)
    except Exception:
        pass


def get_cache_stats(db: Optional[lancedb.DBConnection] = None) -> Dict[str, Any]:
    """Retorna métricas del caché: entradas, hits, tokens y dólares ahorrados."""
    if db is None:
        import os
        db_path = os.path.expanduser("~/.local/share/lancedb-hub/data")
        db = lancedb.connect(db_path)

    cache_entries = 0
    total_hits = 0
    try:
        if _has_table(db, CACHE_TABLE):
            tbl = db.open_table(CACHE_TABLE)
            df = tbl.to_pandas()
            cache_entries = len(df)
            if "hit_count" in df.columns:
                total_hits = int(df["hit_count"].sum())
            else:
                total_hits = cache_entries
    except Exception:
        pass

    tokens_saved = total_hits * 3500
    cost_saved_usd = (tokens_saved / 1_000_000) * 3.00
    return {
        "cache_entries": cache_entries,
        "total_hits": total_hits,
        "tokens_saved": tokens_saved,
        "cost_saved_usd": cost_saved_usd
    }
