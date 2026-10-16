#!/usr/bin/env python3
"""
SyntaxRAG Desktop Context MCP Server (Universal Edition)
Motor AST nativo de código y memoria local para cualquier agente de IA.
- search_desktop: busqueda por palabras (BM25) con reordenado FlashRank en CPU.
- get_file_outline: esquema sintactico (firmas y rangos de linea) de un archivo.
- get_impact_radius: calculo preventivo de dependencias y blast radius.
- find_related_tests: mapeo directo de pruebas unitarias asociadas.
- get_savings_report: registro de uso del buscador y una referencia (no es un ahorro medido).
- list_projects & reindex_desktop: gestion del indice.
"""

import os
import sys
import re
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
import mapa

mcp = MCPServer("desktop-lancedb")


def herramienta():
    """Registra una herramienta sin outputSchema: todas devuelven texto, y ese esquema repetido
    costaba ~170 caracteres por herramienta en cada sesion del agente."""
    try:
        return mcp.tool(structured_output=False)
    except TypeError:  # versiones del SDK sin ese parametro
        return mcp.tool()
SNIPPET = 800  # caracteres maximos por resultado con detalle=true
SNIPPET_PRIMERO = 2400  # el primer resultado va completo (un bloque AST mide como mucho 2.400)
SNIPPET_EXACTO = 8000  # definicion exacta unida desde varios trozos: entera salvo que sea enorme


def _firma(contenido: str) -> str:
    """Primera linea de codigo del bloque (sin JSDoc ni comentarios), recortada."""
    for linea in chunker._sin_comentarios_iniciales(contenido).splitlines():
        if linea.strip():
            return linea.strip()[:110]
    return ""


def _ubicacion(r: dict) -> str:
    ini = r.get("line", "?")
    fin = r.get("end_line", ini)
    rango = f"{ini}-{fin}" if fin != ini else f"{ini}"
    sym = f" {r['symbol_kind']} {r['symbol_name']}" if r.get("symbol_name") else ""
    ruta = str(r.get("rel_path", ""))
    ruta = ruta if ruta.startswith("/") else f"~/{ruta}"  # rel_path es relativa al HOME salvo fuera de el
    return f"{ruta}:{rango}{sym}"


@herramienta()
def search_desktop(query: str, limit: int = 5, project: str = "", detalle: bool = False, tipo: str = "") -> str:
    """Localiza codigo, notas o config por palabras. Con un nombre de simbolo exacto da su definicion primero y entera; el resto sale como `ruta:lineas tipo nombre | firma`. detalle=true trae el codigo de todos. project filtra; tipo filtra por 'docs' o 'codigo'."""
    t0 = time.time()
    results = indexer.search_desktop(query, limit=min(max(limit, 1), 10), project=project or None, tipo=tipo)
    elapsed_ms = (time.time() - t0) * 1000

    telemetry.record_search_event(
        query=query,
        results=results,
        elapsed_ms=elapsed_ms,
        cache_hit=getattr(indexer.search_desktop, "ultima_desde_cache", False),
        project=project,
        agent=telemetry.detectar_cliente()
    )

    if not results:
        donde = f" en '{project}'" if project else ""
        return (f"Sin resultados para '{query}'{donde}. Solo encuentra palabras escritas en el codigo: "
                "prueba con un nombre de simbolo o usa grep; repetir variantes rara vez ayuda.")

    out = []
    for i, r in enumerate(results):
        if i == 0 or detalle:
            out.append(("\n" if i else "") + _ubicacion(r))
            tope = (SNIPPET_EXACTO if r.get("exacto") else SNIPPET_PRIMERO) if i == 0 else SNIPPET
            texto = r.get("content", "").strip()
            out.append(texto[:tope])
            if len(texto) > tope:
                out.append(f"[... recortado; el bloque llega hasta la linea {r.get('end_line')}]")
            deps = r.get("dependents") or []
            if deps and i == 0:
                out.append(f"(importado en {len(deps)} archivo(s); detalles: get_impact_radius)")
            if not detalle and len(results) > 1:
                out.append("\nOtros:")
        else:
            out.append(f"- {_ubicacion(r)} | {_firma(r.get('content', ''))}")
    return "\n".join(out)


RE_MIEMBRO = re.compile(
    r"^(\s+)(?:public\s+|private\s+|protected\s+|static\s+|readonly\s+|override\s+)*(?:async\s+)?(?:get\s+|set\s+)?"
    r"\*?([A-Za-z_$][A-Za-z0-9_$]*)\s*(?:\(|:\s*(?:async\s*)?(?:function\b|\([^)]*\)?\s*(?::[^=]*)?=>|[A-Za-z0-9_$]+\s*=>)|=\s*(?:async\s*)?\()"
)
NO_MIEMBRO = {"if", "for", "while", "switch", "catch", "return", "function", "await", "new", "typeof"}


def _miembros(lineas: list, ini: int, fin: int) -> list:
    """Metodos y funciones de primer nivel dentro de un objeto o clase (lineas ini..fin, 1-based)."""
    hallados = []
    for n in range(ini, min(fin, len(lineas))):
        m = RE_MIEMBRO.match(lineas[n])
        if m and m.group(2) not in NO_MIEMBRO:
            hallados.append((len(m.group(1).expandtabs(4)), n + 1, m.group(2)))
    if not hallados:
        return []
    nivel = min(h[0] for h in hallados)
    return [(ln, nombre) for ind, ln, nombre in hallados if ind == nivel][:60]


@herramienta()
def get_file_outline(file_path: str, project: str = "") -> str:
    """Esquema de un archivo: simbolos con sus lineas y los metodos de objetos/clases grandes, sin el codigo. Acepta ruta o solo el nombre del archivo."""
    resolved_path, otras = indexer.resolver_archivo(file_path, project or None)
    if not resolved_path:
        return f"No se encontro '{file_path}' en los proyectos indexados" + (f" ('{project}')." if project else ".")

    try:
        content = resolved_path.read_text(encoding="utf-8", errors="replace")
        total_lines = len(content.splitlines())
        chunks, _, _ = chunker.parse_and_chunk_file(resolved_path, content)

        symbols = []
        for ch in chunks:
            s_name = ch.get("symbol_name") or ch.get("title") or "bloque"
            s_kind = ch.get("symbol_kind") or "code"
            texto = ch.get("content", "")
            # linea de la declaracion, no la del JSDoc que la precede
            s_line = ch.get("line", 1) + len(texto.splitlines()) - len(chunker._sin_comentarios_iniciales(texto).splitlines())
            s_end = ch.get("end_line", s_line)
            if symbols and symbols[-1][2] == s_name and s_name != "bloque":
                symbols[-1][1] = s_end  # trozos de un mismo bloque largo: un solo rango
                continue
            symbols.append([s_line, s_end, s_name, s_kind])
        lineas_archivo = content.splitlines()
        salida_sym = []
        for a, b, n, k in symbols:
            salida_sym.append(f"  L{a}-{b} {k} {n}")
            if k in ("class", "variable") and b - a > 30:  # objeto o clase grande: sus metodos
                salida_sym.extend(f"    L{ln} {m}" for ln, m in _miembros(lineas_archivo, a, b))
        symbols = salida_sym

        out = [f"{resolved_path} ({total_lines} lineas, {len(symbols)} simbolos)"]
        if otras:
            out.append("Otros archivos con ese nombre: " + ", ".join(otras) + " (usa `project` o la ruta completa)")
        if symbols:
            out.extend(symbols)
        else:
            out.append("  (Archivo plano o sin simbolos exportados de alto nivel)")
        return "\n".join(out)
    except Exception as e:
        return f"[SyntaxRAG Outline] Error al parsear archivo: {e}"


@herramienta()
def get_impact_radius(symbol: str, project: str = "") -> str:
    """Archivos que importan un simbolo (que se rompe si lo cambias)."""
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


@herramienta()
def find_related_tests(file_or_symbol: str) -> str:
    """Pruebas asociadas a un archivo o simbolo."""
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


@herramienta()
def get_savings_report() -> str:
    """Uso registrado del buscador por cliente (no es un ahorro medido)."""
    stats = telemetry.get_summary_stats()
    today = stats["today"]
    all_time = stats["all_time"]
    por_agente = stats.get("por_agente", {})
    excluidas = stats.get("excluidas", 0)
    primera_fecha = stats.get("primera") or today.get("fecha", datetime.now().strftime("%Y-%m-%d"))

    str_por_agente = " | ".join(f"{k}: {v}" for k, v in por_agente.items()) if por_agente else "(sin consultas registradas)"

    out = [
        "================================================================================",
        "        REGISTRO DE USO DEL BUSCADOR (SYNTAX RAG)",
        "================================================================================",
        f"Hoy ({today.get('fecha', '')}):     {today['queries']} consultas | latencia media {today['avg_latency_ms']:.0f} ms | tokens devueltos {today.get('tokens_retrieved', 0):,}",
        f"Medido desde {primera_fecha}: {all_time['queries']} consultas | tokens devueltos {all_time.get('tokens_retrieved', 0):,}",
        f"Por cliente:          {str_por_agente}",
        "--------------------------------------------------------------------------------",
        f"REFERENCIA (no es un ahorro medido): {all_time['tokens_saved']:,} tokens.",
        "Es el tamaño completo de los archivos devueltos menos lo devuelto. Supone que sin",
        "SyntaxRAG se habrian leido enteros todos esos archivos y no resta las lecturas",
        "posteriores. Los resultados igualmente cuestan tokens al modelo que los lee.",
        f"Filas excluidas por no ser mediciones (sembradas o importadas): {excluidas}",
        "Costo de la busqueda en APIs de pago: $0.00",
        "================================================================================",
    ]
    return "\n".join(out)


@herramienta()
def list_projects() -> str:
    """Proyectos indexados y cuantos fragmentos tiene cada uno."""
    try:
        db = indexer.get_db()
        df = db.open_table(indexer.TABLE_NAME).to_pandas()[["project"]]
        cuentas = df.groupby("project").size().sort_values(ascending=False)
        return "[SyntaxRAG] Proyectos indexados (fragmentos AST):\n" + "\n".join(f"- {p}: {n}" for p, n in cuentas.items())
    except Exception as e:
        return f"[SyntaxRAG] Indice no disponible: {e}. Ejecuta reindex_desktop."


@herramienta()
def reindex_desktop() -> str:
    """Reindexa todas las carpetas configuradas (segundos)."""
    try:
        indexer.index_desktop()
        return "[OK] Reindexado completo exitoso (Tree-sitter AST + Grafo de Impacto + Cache reseteada)."
    except Exception as e:
        return f"[ERROR] Error al reindexar: {e}"


@herramienta()
def repo_map(project: str, foco: str = "", tokens: int = 1024) -> str:
    """Mapa de firmas del proyecto ordenado por relevancia (PageRank) dentro de un presupuesto de tokens."""
    return mapa.mapa_del_repo(proyecto=project, foco=foco, tokens=tokens)


# ==============================================================================
# REGISTRO DE SUITE MODULAR DE HERRAMIENTAS (OPTIMIZACION DE TOKENS Y SEGURIDAD)
# ==============================================================================
import tools.context_tools as context_tools
import tools.inspect_tools as inspect_tools
import tools.runner_tools as runner_tools
import tools.patch_tools as patch_tools
import tools.safety_tools as safety_tools

# Bloque 1: Gestión de contexto y sesiones
herramienta()(context_tools.session_handoff)
herramienta()(context_tools.context_budget_alert)
herramienta()(context_tools.git_staged_overview)
herramienta()(context_tools.extract_todo_status)

# Bloque 2: Lectura e inspección quirúrgica
herramienta()(inspect_tools.get_symbol_contract)
herramienta()(inspect_tools.extract_type_definition)
herramienta()(inspect_tools.get_import_graph)
herramienta()(inspect_tools.find_callers_exact)

# Bloque 3: Ejecución y filtrado de consola
herramienta()(runner_tools.run_test_isolated)
herramienta()(runner_tools.lint_summary)
herramienta()(runner_tools.run_typecheck_focus)
herramienta()(runner_tools.tail_clean_logs)

# Bloque 4: Modificación sintáctica y parches
herramienta()(patch_tools.patch_function_body)
herramienta()(patch_tools.add_import_clean)
herramienta()(patch_tools.rename_symbol_scoped)
herramienta()(patch_tools.remove_unused_imports)

# Bloque 5: Prevención de errores y dependencias rotas
herramienta()(safety_tools.verify_dependency_exists)
herramienta()(safety_tools.check_circular_imports)
herramienta()(safety_tools.check_breaking_callsites)
herramienta()(safety_tools.find_code_duplicates)

# Bloque 6 (opcional): coprocesador con Gemini. Solo si el usuario configuro su GEMINI_API_KEY;
# sin clave no se registran y el motor no usa la red.
import argon
if argon.disponible():
    herramienta()(argon.ask_synrag_architect)
    herramienta()(argon.explain_blast_radius)


def _compactar_esquemas():
    """Quita los "title" que el SDK genera solos en cada parametro ("File Path" para file_path):
    repiten el nombre y se pagan en cada sesion. Si el SDK cambia su interna, no pasa nada."""
    def limpiar(nodo):
        if isinstance(nodo, dict):
            nodo.pop("title", None)
            for v in nodo.values():
                limpiar(v)
    try:
        for t in mcp._tool_manager.list_tools():
            limpiar(t.parameters)
    except Exception:
        pass


_compactar_esquemas()

if __name__ == "__main__":
    mcp.run()


