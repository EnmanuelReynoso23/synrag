"""
Motor de Telemetria Persistente de Ahorro para SyntaxRAG
Registra cada consulta semantica y calcula los tokens reales ahorrados
frente a la lectura completa de archivos. Almacenado en SQLite local (~/.local/share/lancedb-hub/telemetry.db).
"""

import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

DB_DIR = Path.home() / ".local/share/lancedb-hub"
DB_PATH = DB_DIR / "telemetry.db"


def _get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            datetime_str TEXT,
            agent TEXT,
            query TEXT,
            project TEXT,
            results_count INTEGER,
            tokens_retrieved INTEGER,
            tokens_original_file INTEGER,
            tokens_saved INTEGER,
            cost_saved_usd REAL,
            latency_ms REAL,
            cache_hit INTEGER
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON telemetry_events(timestamp)")
    conn.commit()
    return conn


def record_search_event(
    query: str,
    results: List[Dict[str, Any]],
    elapsed_ms: float,
    cache_hit: bool,
    project: Optional[str] = None,
    agent: str = "ai-agent"
) -> Dict[str, Any]:
    """Registra una busqueda y calcula tokens ahorrados."""
    now = time.time()
    dt_str = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")

    # Tokens recuperados por SyntaxRAG
    chars_retrieved = sum(len(r.get("content", "")) for r in results)
    tokens_retrieved = max(1, int(chars_retrieved / 3.8))

    # Estimacion de archivos originales si se hubieran leido completos
    tokens_original = 0
    unique_paths = set()
    for r in results:
        fp = r.get("file_path") or r.get("path")
        if fp and fp not in unique_paths:
            unique_paths.add(fp)
            try:
                p = Path(fp)
                if p.is_file():
                    tokens_original += int(p.stat().st_size / 3.8)
                else:
                    tokens_original += 2500  # fallback promedio por archivo
            except Exception:
                tokens_original += 2500

    if tokens_original == 0:
        tokens_original = max(tokens_retrieved * 6, len(results) * 2200)

    tokens_saved = max(0, tokens_original - tokens_retrieved)
    # Claude 3.5 Sonnet: $3.00 USD por millon de tokens
    cost_saved = (tokens_saved / 1_000_000.0) * 3.00

    try:
        with _get_connection() as conn:
            conn.execute("""
                INSERT INTO telemetry_events (
                    timestamp, datetime_str, agent, query, project,
                    results_count, tokens_retrieved, tokens_original_file,
                    tokens_saved, cost_saved_usd, latency_ms, cache_hit
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                now, dt_str, agent, query, project or "",
                len(results), tokens_retrieved, tokens_original,
                tokens_saved, cost_saved, elapsed_ms, 1 if cache_hit else 0
            ))
    except Exception:
        pass

    return {
        "tokens_retrieved": tokens_retrieved,
        "tokens_saved": tokens_saved,
        "cost_saved_usd": cost_saved,
    }


def get_summary_stats() -> Dict[str, Any]:
    """Devuelve estadisticas historicas reales del acumulado."""
    now = time.time()
    day_start = now - 86400
    week_start = now - (86400 * 7)

    try:
        with _get_connection() as conn:
            c = conn.cursor()

            # Totales globales
            c.execute("""
                SELECT 
                    COUNT(*),
                    COALESCE(SUM(tokens_saved), 0),
                    COALESCE(SUM(cost_saved_usd), 0.0),
                    COALESCE(AVG(latency_ms), 0.0),
                    COALESCE(SUM(cache_hit), 0)
                FROM telemetry_events
            """)
            all_queries, all_tokens, all_cost, all_lat, all_hits = c.fetchone()

            # Hoy
            c.execute("""
                SELECT 
                    COUNT(*),
                    COALESCE(SUM(tokens_saved), 0),
                    COALESCE(SUM(cost_saved_usd), 0.0),
                    COALESCE(AVG(latency_ms), 0.0)
                FROM telemetry_events
                WHERE timestamp >= ?
            """, (day_start,))
            today_queries, today_tokens, today_cost, today_lat = c.fetchone()

            # Semana
            c.execute("""
                SELECT 
                    COUNT(*),
                    COALESCE(SUM(tokens_saved), 0),
                    COALESCE(SUM(cost_saved_usd), 0.0)
                FROM telemetry_events
                WHERE timestamp >= ?
            """, (week_start,))
            week_queries, week_tokens, week_cost = c.fetchone()

            # Top consultas
            c.execute("""
                SELECT query, COUNT(*) as cnt
                FROM telemetry_events
                GROUP BY query
                ORDER BY cnt DESC
                LIMIT 5
            """)
            top_queries = [{"query": r[0], "count": r[1]} for r in c.fetchall()]

            return {
                "all_time": {
                    "queries": all_queries,
                    "tokens_saved": int(all_tokens),
                    "cost_saved_usd": round(all_cost, 2),
                    "avg_latency_ms": round(all_lat, 2),
                    "cache_hits": all_hits,
                },
                "today": {
                    "queries": today_queries,
                    "tokens_saved": int(today_tokens),
                    "cost_saved_usd": round(today_cost, 2),
                    "avg_latency_ms": round(today_lat, 2),
                },
                "week": {
                    "queries": week_queries,
                    "tokens_saved": int(week_tokens),
                    "cost_saved_usd": round(week_cost, 2),
                },
                "top_queries": top_queries,
            }
    except Exception:
        return {
            "all_time": {"queries": 0, "tokens_saved": 0, "cost_saved_usd": 0.0, "avg_latency_ms": 0.0, "cache_hits": 0},
            "today": {"queries": 0, "tokens_saved": 0, "cost_saved_usd": 0.0, "avg_latency_ms": 0.0},
            "week": {"queries": 0, "tokens_saved": 0, "cost_saved_usd": 0.0},
            "top_queries": [],
        }
