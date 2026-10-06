"""
Motor de Telemetria Persistente para SyntaxRAG
Registra cada consulta semantica, calcula tokens devueltos y mantiene una referencia
contrafactual frente a la lectura completa de archivos.
Almacenado en SQLite local (~/.local/share/lancedb-hub/telemetry.db).
"""

import os
import sqlite3
import subprocess
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
            cache_hit INTEGER,
            origen TEXT DEFAULT 'medido'
        )
    """)
    # Migración: comprobar si falta la columna origen
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(telemetry_events)")
    columnas = [row[1] for row in cur.fetchall()]
    if "origen" not in columnas:
        conn.execute("ALTER TABLE telemetry_events ADD COLUMN origen TEXT DEFAULT 'medido'")
        conn.commit()

    conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON telemetry_events(timestamp)")
    conn.commit()
    return conn


def etiqueta_de_cliente(nombre_proceso: str) -> str:
    """
    Normaliza el nombre de proceso del cliente MCP a una etiqueta limpia.
    Función pura y determinista.
    """
    if not nombre_proceso or not nombre_proceso.strip():
        return "desconocido"
    p = nombre_proceso.strip().lower()
    if p.startswith("claude"):
        return "claude-code"
    if p in ("language_server", "antigravity", "agy"):
        return "antigravity"
    if p.startswith("zed"):
        return "zed"
    if p.startswith("cursor"):
        return "cursor"
    if p.startswith("windsurf"):
        return "windsurf"
    if p.startswith("codex"):
        return "codex"
    if p.startswith("gemini"):
        return "gemini-cli"
    if p == "code":
        return "vscode"
    return nombre_proceso.strip()


def detectar_cliente() -> str:
    """Detecta el nombre de la IA cliente inspeccionando el proceso padre (PPID)."""
    try:
        ppid = os.getppid()
        # En Linux: leer /proc/<ppid>/comm directamente
        comm_path = Path(f"/proc/{ppid}/comm")
        if comm_path.is_file():
            comm = comm_path.read_text(encoding="utf-8").strip()
            return etiqueta_de_cliente(comm)

        # Otros sistemas / fallback con timeout de 2 segundos
        res = subprocess.run(
            ["ps", "-o", "comm=", "-p", str(ppid)],
            capture_output=True,
            text=True,
            timeout=2.0
        )
        if res.returncode == 0 and res.stdout.strip():
            return etiqueta_de_cliente(res.stdout.strip())
        return "desconocido"
    except Exception:
        return "desconocido"


def record_search_event(
    query: str,
    results: List[Dict[str, Any]],
    elapsed_ms: float,
    cache_hit: bool,
    project: Optional[str] = None,
    agent: str = "desconocido",
    origen: str = "medido"
) -> Dict[str, Any]:
    """Registra una busqueda y calcula tokens devueltos y referencia contrafactual."""
    now = time.time()
    dt_str = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")

    # Tokens recuperados por SyntaxRAG
    chars_retrieved = sum(len(r.get("content", "")) for r in results)
    tokens_retrieved = max(1, int(chars_retrieved / 3.8))

    # Estimacion contrafactual si se hubieran leido completos
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
    cost_saved = (tokens_saved / 1_000_000.0) * 3.00

    try:
        with _get_connection() as conn:
            conn.execute("""
                INSERT INTO telemetry_events (
                    timestamp, datetime_str, agent, query, project,
                    results_count, tokens_retrieved, tokens_original_file,
                    tokens_saved, cost_saved_usd, latency_ms, cache_hit, origen
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                now, dt_str, agent, query, project or "",
                len(results), tokens_retrieved, tokens_original,
                tokens_saved, cost_saved, elapsed_ms, 1 if cache_hit else 0, origen
            ))
    except Exception:
        pass

    return {
        "tokens_retrieved": tokens_retrieved,
        "tokens_saved": tokens_saved,
        "cost_saved_usd": cost_saved,
        "tokens_reference": tokens_saved,
        "origen": origen,
    }


def get_summary_stats() -> Dict[str, Any]:
    """
    Devuelve estadisticas historicas reales del acumulado.
    Filtra exclusivamente filas con origen 'medido' (o nulas pre-migracion).
    """
    ahora_dt = datetime.now()
    inicio_hoy = datetime(ahora_dt.year, ahora_dt.month, ahora_dt.day).timestamp()
    inicio_semana = inicio_hoy - (86400 * 6)

    try:
        with _get_connection() as conn:
            c = conn.cursor()

            # Totales globales (medidos)
            c.execute("""
                SELECT 
                    COUNT(*),
                    COALESCE(SUM(tokens_retrieved), 0),
                    COALESCE(SUM(tokens_saved), 0),
                    COALESCE(AVG(latency_ms), 0.0),
                    COALESCE(SUM(cache_hit), 0),
                    MIN(datetime_str)
                FROM telemetry_events
                WHERE origen = 'medido' OR origen IS NULL
            """)
            all_q, all_ret, all_sav, all_lat, all_hits, min_dt = c.fetchone()

            # Hoy (desde medianoche local 00:00)
            c.execute("""
                SELECT 
                    COUNT(*),
                    COALESCE(SUM(tokens_retrieved), 0),
                    COALESCE(SUM(tokens_saved), 0),
                    COALESCE(AVG(latency_ms), 0.0),
                    COALESCE(SUM(cache_hit), 0)
                FROM telemetry_events
                WHERE (origen = 'medido' OR origen IS NULL) AND timestamp >= ?
            """, (inicio_hoy,))
            today_q, today_ret, today_sav, today_lat, today_hits = c.fetchone()

            # Semana
            c.execute("""
                SELECT 
                    COUNT(*),
                    COALESCE(SUM(tokens_retrieved), 0),
                    COALESCE(SUM(tokens_saved), 0),
                    COALESCE(AVG(latency_ms), 0.0)
                FROM telemetry_events
                WHERE (origen = 'medido' OR origen IS NULL) AND timestamp >= ?
            """, (inicio_semana,))
            week_q, week_ret, week_sav, week_lat = c.fetchone()

            # Por cliente (agente) en filas medidas
            c.execute("""
                SELECT agent, COUNT(*)
                FROM telemetry_events
                WHERE origen = 'medido' OR origen IS NULL
                GROUP BY agent
                ORDER BY COUNT(*) DESC
            """)
            por_agente = {row[0]: row[1] for row in c.fetchall()}

            # Filas excluidas (origen != 'medido')
            c.execute("""
                SELECT COUNT(*)
                FROM telemetry_events
                WHERE origen != 'medido' AND origen IS NOT NULL
            """)
            excluidas = c.fetchone()[0]

            # Fecha de la primera medición (ISO YYYY-MM-DD)
            primera = min_dt.split()[0] if min_dt else None

            # Top consultas
            c.execute("""
                SELECT query, COUNT(*) as cnt
                FROM telemetry_events
                WHERE origen = 'medido' OR origen IS NULL
                GROUP BY query
                ORDER BY cnt DESC
                LIMIT 5
            """)
            top_queries = [{"query": r[0], "count": r[1]} for r in c.fetchall()]

            return {
                "all_time": {
                    "queries": all_q,
                    "tokens_retrieved": int(all_ret),
                    "tokens_saved": int(all_sav),
                    "avg_latency_ms": round(all_lat, 2),
                    "cache_hits": all_hits,
                },
                "today": {
                    "queries": today_q,
                    "tokens_retrieved": int(today_ret),
                    "tokens_saved": int(today_sav),
                    "avg_latency_ms": round(today_lat, 2),
                    "cache_hits": today_hits,
                    "fecha": ahora_dt.strftime("%Y-%m-%d"),
                },
                "week": {
                    "queries": week_q,
                    "tokens_retrieved": int(week_ret),
                    "tokens_saved": int(week_sav),
                    "avg_latency_ms": round(week_lat, 2),
                },
                "por_agente": por_agente,
                "excluidas": excluidas,
                "primera": primera,
                "top_queries": top_queries,
            }
    except Exception:
        return {
            "all_time": {"queries": 0, "tokens_retrieved": 0, "tokens_saved": 0, "avg_latency_ms": 0.0, "cache_hits": 0},
            "today": {"queries": 0, "tokens_retrieved": 0, "tokens_saved": 0, "avg_latency_ms": 0.0, "cache_hits": 0, "fecha": ahora_dt.strftime("%Y-%m-%d")},
            "week": {"queries": 0, "tokens_retrieved": 0, "tokens_saved": 0, "avg_latency_ms": 0.0},
            "por_agente": {},
            "excluidas": 0,
            "primera": None,
            "top_queries": [],
        }
