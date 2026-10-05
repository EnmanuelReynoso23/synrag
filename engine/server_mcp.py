#!/usr/bin/env python3
"""
SyntaxRAG Desktop Context MCP Server (Universal Edition)
Motor AST nativo de código y memoria local para cualquier agente de IA.
- search_desktop: busqueda semantica con AST + FlashRank neural en CPU.
- get_file_outline: esquema sintactico de cualquier archivo en ~50 tokens.
- get_impact_radius: calculo preventivo de dependencias y blast radius.
- find_related_tests: mapeo directo de pruebas unitarias asociadas.
- get_savings_report: metricas persistentes de tokens y costos ahorrados.
- list_projects & reindex_desktop: gestion del indice.
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

# MCP 2.x support
try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer

sys.path.insert(0, str(Path(__file__).parent))
import indexer
import impact
import chunker
import telemetry

mcp = MCPServer("desktop-lancedb")
SNIPPET = 800  # caracteres maximos por resultado en busqueda normal


@mcp.tool()
def search_desktop(query: str, limit: int = 5, project: str = "") -> str:
    """
    Busca codigo o conceptos en todos los proyectos (AsistoYA incluido), memoria de
    Claude y configuracion. Devuelve `ruta:linea_inicio-linea_fin` y un
    bloque sintactico completo (funcion, hook, interface) con ranking neural FlashRank.
    Si el simbolo encontrado tiene archivos dependientes, incluye una advertencia de
    Grafo de Impacto para evitar roturas de codigo.
    `project` filtra por proyecto (p. ej. "asistoya-web", "memoria-claude").
    """
    t0 = time.time()
    results = indexer.search_desktop(query, limit=min(max(limit, 1), 10), project=project or None)
    elapsed_ms = (time.time() - t0) * 1000

    # Registrar evento en telemetria persistente
    telemetry.record_search_event(
        query=query,
        results=results,
        elapsed_ms=elapsed_ms,
        cache_hit=False,
        project=project,
        agent="mcp-client"
    )

    if not results:
        return f"[SyntaxRAG] Sin resultados para '{query}'" + (f" en el proyecto '{project}'." if project else ".")

    out = [f"[SyntaxRAG] {len(results)} resultado(s) para '{query}' (AST + FlashRank ONNX):"]
    for r in results:
        sym_info = f" [{r['symbol_kind']} {r['symbol_name']}]" if r.get('symbol_name') else ""
        score_info = f" (relevancia: {r['score']:.2f})" if 'score' in r else ""
        start_l = r.get('line', '?')
        end_l = r.get('end_line', start_l)
        range_str = f"{start_l}-{end_l}" if end_l != start_l else f"{start_l}"
        out.append(f"\n▸ {r.get('rel_path')}:{range_str}  [{r.get('project')}]{sym_info}{score_info}")
        out.append(r.get("content", "").strip()[:SNIPPET])
        if r.get("impact_warning"):
            out.append(r["impact_warning"])
    return "\n".join(out)


@mcp.tool()
def get_file_outline(file_path: str, project: str = "") -> str:
    """
    Devuelve unicamente el esquema sintactico (firmas, nombres de funciones, tipos, clases
    y rangos de lineas) de un archivo sin volcar el codigo completo.
    Consumo tipico: ~40-60 tokens (en lugar de 3,000+ tokens de leer el archivo entero).
    Usa esta herramienta cuando solo necesites saber que funciones o componentes existen en un archivo.
    """
    # Intentar resolver ruta absoluta o relativa en proyectos
    resolved_path: Optional[Path] = None
    target_p = Path(file_path).expanduser()

    if target_p.is_file():
        resolved_path = target_p
    else:
        # Buscar en SCAN_DIRECTORIES
        for base, proj_name in indexer.SCAN_DIRECTORIES:
            candidate = base / file_path
            if candidate.is_file():
                resolved_path = candidate
                break
            # buscar por subruta
            if not resolved_path:
                matches = list(base.glob(f"**/{file_path}"))
                if matches and matches[0].is_file():
                    resolved_path = matches[0]
                    break

    if not resolved_path or not resolved_path.is_file():
        return f"[SyntaxRAG Outline] No se encontro el archivo '{file_path}' en los proyectos indexados."

    try:
        content = resolved_path.read_text(encoding="utf-8", errors="replace")
        total_lines = len(content.splitlines())
        chunks, _, _ = chunker.parse_and_chunk_file(resolved_path, content)

        symbols = []
        for ch in chunks:
            s_name = ch.get("symbol_name") or ch.get("title") or "bloque"
            s_kind = ch.get("symbol_kind") or "code"
            s_line = ch.get("line", 1)
            s_end = ch.get("end_line", s_line)
            symbols.append(f"  - L{s_line}-{s_end} [{s_kind}] {s_name}")

        out = [
            f"[SyntaxRAG Outline] {resolved_path.name} ({total_lines} lineas, {len(symbols)} simbolos detectados):",
            f"Ruta: {resolved_path}"
        ]
        if symbols:
            out.extend(symbols)
        else:
            out.append("  (Archivo plano o sin simbolos exportados de alto nivel)")
        return "\n".join(out)
    except Exception as e:
        return f"[SyntaxRAG Outline] Error al parsear archivo: {e}"


@mcp.tool()
def get_impact_radius(symbol: str, project: str = "") -> str:
    """
    Calcula el radio de impacto (blast radius) de un simbolo o funcion antes de editarlo.
    Devuelve la lista de archivos que dependen directamente o importan este simbolo,
    con su nivel de criticidad (CRITICAL, WARNING, INFO).
    """
    try:
        db = indexer.get_db()
        if impact.IMPACT_TABLE not in db.table_names():
            return "[SyntaxRAG Grafo] Tabla de impacto no disponible. Ejecuta reindex_desktop."

        tbl = db.open_table(impact.IMPACT_TABLE)
        escaped_sym = symbol.replace("'", "")
        filter_expr = f"symbol = '{escaped_sym}'"
        if project:
            clean_proj = project.replace("'", "")
            filter_expr += f" AND project = '{clean_proj}'"

        rows = tbl.search().where(filter_expr).limit(30).to_list()

        if not rows:
            # Buscar por contencion de subcadena
            rows = tbl.search().where(f"symbol LIKE '%{escaped_sym}%'").limit(30).to_list()

        dependents = [r["imported_by"] for r in rows if r.get("imported_by") and r["imported_by"] != "__init__"]

        if not dependents:
            return f"[SyntaxRAG Grafo] No se registraron dependencias entrantes para el simbolo '{symbol}'."

        out = [
            f"[SyntaxRAG Grafo] Radio de Impacto para '{symbol}':",
            f"Total archivos consumidores directos: {len(dependents)}"
        ]
        for dep in sorted(set(dependents))[:20]:
            out.append(f"  - [CONSUMIDOR] {dep}")

        if len(dependents) > 20:
            out.append(f"  ... y {len(dependents) - 20} dependientes mas.")

        return "\n".join(out)
    except Exception as e:
        return f"[SyntaxRAG Grafo] Error al consultar dependencias: {e}"


@mcp.tool()
def find_related_tests(file_or_symbol: str) -> str:
    """
    Localiza los archivos de pruebas unitarias o de integracion asociados a un archivo o simbolo.
    Permite correr exclusivamente los tests relevantes tras modificar una funcion sin ejecutar toda la suite.
    """
    stem = Path(file_or_symbol).stem.replace(".test", "").replace(".spec", "")
    try:
        db = indexer.get_db()
        tbl = db.open_table(indexer.TABLE_NAME)
        # Buscar archivos con patron de test que contengan el stem
        escaped_stem = stem.replace("'", "''")
        query = f"file_path LIKE '%{escaped_stem}%.test.%' OR file_path LIKE '%{escaped_stem}%.spec.%' OR file_path LIKE '%test_{escaped_stem}%.py'"
        rows = tbl.search().where(query).limit(10).to_list()

        if not rows:
            return f"[SyntaxRAG Tests] No se encontraron pruebas especificas con patron para '{file_or_symbol}'."

        test_files = set()
        for r in rows:
            test_files.add((r.get("rel_path", ""), r.get("project", "")))

        out = [f"[SyntaxRAG Tests] Archivos de prueba asociados a '{file_or_symbol}':"]
        for tf, proj in test_files:
            out.append(f"  - [{proj}] {tf}")
        return "\n".join(out)
    except Exception as e:
        return f"[SyntaxRAG Tests] Error al buscar pruebas: {e}"


@mcp.tool()
def get_savings_report() -> str:
    """
    Devuelve el reporte historico persistente de tokens y costos ahorrados por SyntaxRAG
    en esta maquina (acumulado de hoy, semanal y global).
    """
    stats = telemetry.get_summary_stats()
    today = stats["today"]
    all_time = stats["all_time"]

    out = [
        "================================================================================",
        "               REPORTE HISTORICO DE AHORRO DE TOKENS (SYNTAX RAG)               ",
        "================================================================================",
        f"Ahorro de Hoy:       {today['tokens_saved']:,} tokens ahorrados (USD ${today['cost_saved_usd']:.2f})",
        f"Consultas de Hoy:    {today['queries']} consultas (Latencia media: {today['avg_latency_ms']:.1f}ms)",
        "--------------------------------------------------------------------------------",
        f"Ahorro Acumulado:    {all_time['tokens_saved']:,} tokens ahorrados (USD ${all_time['cost_saved_usd']:.2f})",
        f"Consultas Totales:   {all_time['queries']} consultas atendidas localmente",
        f"Costo en la nube:    $0.00 USD (Inferencia 100% en CPU local)",
        "================================================================================"
    ]
    return "\n".join(out)


@mcp.tool()
def list_projects() -> str:
    """Lista los proyectos indexados y cuantos fragmentos AST tiene cada uno."""
    try:
        db = indexer.get_db()
        df = db.open_table(indexer.TABLE_NAME).to_pandas()[["project"]]
        cuentas = df.groupby("project").size().sort_values(ascending=False)
        return "[SyntaxRAG] Proyectos indexados (fragmentos AST):\n" + "\n".join(f"- {p}: {n}" for p, n in cuentas.items())
    except Exception as e:
        return f"[SyntaxRAG] Indice no disponible: {e}. Ejecuta reindex_desktop."


@mcp.tool()
def reindex_desktop() -> str:
    """Vuelve a indexar todo con AST y Grafo de Impacto (unos segundos)."""
    try:
        indexer.index_desktop()
        return "[OK] Reindexado completo exitoso (Tree-sitter AST + Grafo de Impacto + Cache reseteada)."
    except Exception as e:
        return f"[ERROR] Error al reindexar: {e}"


if __name__ == "__main__":
    mcp.run()
