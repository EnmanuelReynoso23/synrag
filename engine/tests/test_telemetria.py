import os
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import pytest
import telemetry
import indexer
import server_mcp
from conftest import crear_proyecto


def test_telemetria_migracion_esquema_antiguo(casa):
    # Crear base previa sin columna 'origen'
    telemetry.DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(telemetry.DB_PATH))
    conn.execute("""
        CREATE TABLE telemetry_events (
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
    conn.execute("""
        INSERT INTO telemetry_events (
            timestamp, datetime_str, agent, query, project,
            results_count, tokens_retrieved, tokens_original_file,
            tokens_saved, cost_saved_usd, latency_ms, cache_hit
        ) VALUES (
            1000.0, '2026-10-04 12:00:00', 'claude-code', 'consulta_antigua', 'p',
            1, 200, 1000, 800, 0.0024, 10.0, 0
        )
    """)
    conn.commit()
    conn.close()

    # Al consultar stats, se ejecuta _get_connection y la migracion
    stats = telemetry.get_summary_stats()

    # Comprobar que la columna existe ahora
    conn = sqlite3.connect(str(telemetry.DB_PATH))
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(telemetry_events)")
    columnas = [r[1] for r in cur.fetchall()]
    conn.close()

    assert "origen" in columnas
    # La fila previa sin origen cuenta como medida
    assert stats["all_time"]["queries"] == 1
    assert stats["all_time"]["tokens_retrieved"] == 200
    assert stats["all_time"]["tokens_saved"] == 800


def test_telemetria_filas_sembradas_excluidas(casa):
    # Insertar una fila con origen='sembrado' y otra con origen='medido'
    telemetry.record_search_event(
        query="q_sembrada",
        results=[{"file_path": str(casa / "a.ts"), "content": "func()"}],
        elapsed_ms=10.0,
        cache_hit=False,
        agent="claude-code",
        origen="sembrado",
    )

    telemetry.record_search_event(
        query="q_medida",
        results=[{"file_path": str(casa / "b.ts"), "content": "func()"}],
        elapsed_ms=12.0,
        cache_hit=False,
        agent="claude-code",
        origen="medido",
    )

    stats = telemetry.get_summary_stats()

    assert stats["excluidas"] == 1
    assert stats["all_time"]["queries"] == 1
    assert stats["today"]["queries"] == 1
    assert stats["por_agente"] == {"claude-code": 1}


def test_telemetria_today_desde_medianoche_local(casa):
    ahora_dt = datetime.now()
    inicio_hoy = datetime(ahora_dt.year, ahora_dt.month, ahora_dt.day).timestamp()

    # Evento de ayer (antes de la medianoche local)
    conn = telemetry._get_connection()
    conn.execute("""
        INSERT INTO telemetry_events (
            timestamp, datetime_str, agent, query, project,
            results_count, tokens_retrieved, tokens_original_file,
            tokens_saved, cost_saved_usd, latency_ms, cache_hit, origen
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        inicio_hoy - 3600, "2026-10-05 23:00:00", "antigravity", "ayer", "p",
        1, 100, 500, 400, 0.001, 8.0, 0, "medido"
    ))
    # Evento de hoy (despues de la medianoche local)
    conn.execute("""
        INSERT INTO telemetry_events (
            timestamp, datetime_str, agent, query, project,
            results_count, tokens_retrieved, tokens_original_file,
            tokens_saved, cost_saved_usd, latency_ms, cache_hit, origen
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        inicio_hoy + 10, "2026-10-06 00:00:10", "antigravity", "hoy", "p",
        1, 150, 600, 450, 0.001, 9.0, 0, "medido"
    ))
    conn.commit()

    stats = telemetry.get_summary_stats()

    assert stats["all_time"]["queries"] == 2
    assert stats["today"]["queries"] == 1
    assert stats["today"]["tokens_retrieved"] == 150


def test_etiqueta_de_cliente():
    casos = {
        "claude": "claude-code",
        "claude-code": "claude-code",
        "language_server": "antigravity",
        "antigravity": "antigravity",
        "agy": "antigravity",
        "zed": "zed",
        "zed-editor": "zed",
        "cursor": "cursor",
        "windsurf": "windsurf",
        "codex": "codex",
        "gemini": "gemini-cli",
        "gemini-cli": "gemini-cli",
        "code": "vscode",
        "": "desconocido",
        "   ": "desconocido",
        None: "desconocido",
        "otro_proceso_custom": "otro_proceso_custom",
    }
    for entrada, esperada in casos.items():
        assert telemetry.etiqueta_de_cliente(entrada) == esperada, f"Fallo en {entrada}"


def test_detectar_cliente(monkeypatch, tmp_path):
    # Simular lectura de /proc/<ppid>/comm
    falso_comm = tmp_path / "comm"
    falso_comm.write_text("language_server\n", encoding="utf-8")

    monkeypatch.setattr(os, "getppid", lambda: 12345)
    monkeypatch.setattr(telemetry, "Path", lambda p: falso_comm if "/proc/12345/comm" in str(p) else Path(p))

    cliente = telemetry.detectar_cliente()
    assert cliente == "antigravity"


def test_search_desktop_ultima_desde_cache(casa):
    archivos = {
        "app.ts": "export function operacionMatematica(a: number, b: number) { return a + b; }\n"
    }
    crear_proyecto(casa, "demo", archivos)
    indexer.index_desktop()

    # Primera llamada: no viene de la caché
    res1 = indexer.search_desktop("operacionMatematica", use_rerank=False)
    assert len(res1) > 0
    assert indexer.search_desktop.ultima_desde_cache is False

    # Segunda llamada: idéntica consulta, acierta en caché
    res2 = indexer.search_desktop("operacionMatematica", use_rerank=False)
    assert len(res2) > 0
    assert indexer.search_desktop.ultima_desde_cache is True


def test_get_savings_report_formato_y_honestidad(casa):
    # Registrar evento medido
    telemetry.record_search_event(
        query="buscar_clave",
        results=[{"file_path": str(casa / "modulo.ts"), "content": "export const x = 1;"}],
        elapsed_ms=14.5,
        cache_hit=False,
        agent="claude-code",
        origen="medido",
    )

    reporte = server_mcp.get_savings_report()

    # Formato general
    assert "REGISTRO DE USO DEL BUSCADOR (SYNTAX RAG)" in reporte
    assert "REFERENCIA (no es un ahorro medido):" in reporte
    assert "Costo de la busqueda en APIs de pago: $0.00" in reporte
    assert "claude-code: 1" in reporte

    # No contiene 'ahorrad' (salvo 'no es un ahorro medido')
    assert "ahorrad" not in reporte.lower()

    # El símbolo '$' solo debe aparecer como '$0.00'
    posiciones_dolar = [m.start() for m in re.finditer(r"\$", reporte)]
    for pos in posiciones_dolar:
        assert reporte[pos:pos + 5] == "$0.00", f"Encontrado $ indebido en: {reporte[pos:pos + 10]}"
