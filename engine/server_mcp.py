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
    from mcp.server.mcpserver import MCPServer, Context
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer, Context

sys.path.insert(0, str(Path(__file__).parent))
import indexer
import impact
import chunker
import telemetry
import mapa

mcp = MCPServer("desktop-lancedb")


PERFIL = indexer.perfil_herramientas()
# Perfil esencial: lo que usa un agente casi siempre. Cada definicion se paga en cada turno en los
# clientes que no cargan las herramientas bajo demanda (SYNRAG configure --perfil esencial).
ESENCIALES = {"search_desktop", "get_file_outline", "get_impact_radius", "repo_map", "run_test_isolated"}
# Perfil bajo_demanda: arranca solo con search_desktop y synrag_mas; el resto se registra al llamar
# synrag_mas y el servidor avisa con notifications/tools/list_changed.
INICIALES_BAJO_DEMANDA = {"search_desktop"}
_pendientes = []  # funciones que el perfil bajo_demanda aun no registra
_activas = []  # nombres ya registrados por synrag_mas (no se repiten)


def _registrar(fn):
    try:
        return mcp.tool(structured_output=False)(fn)
    except TypeError:  # versiones del SDK sin ese parametro
        return mcp.tool()(fn)


def herramienta():
    """Registra una herramienta sin outputSchema: todas devuelven texto, y ese esquema repetido
    costaba ~170 caracteres por herramienta en cada sesion del agente. Con el perfil esencial, las
    que no estan en ESENCIALES no se registran (siguen siendo funciones normales). Con bajo_demanda
    se guardan en _pendientes hasta que synrag_mas las active."""
    def registrar(fn):
        if PERFIL == "esencial" and fn.__name__ not in ESENCIALES:
            return fn
        if PERFIL == "bajo_demanda" and fn.__name__ not in INICIALES_BAJO_DEMANDA:
            _pendientes.append(fn)
            return fn
        return _registrar(fn)
    return registrar
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
    """Localiza codigo, notas o config por palabras. Un nombre de simbolo exacto da su definicion entera primero. Salida `ruta:lineas tipo nombre | firma`. project filtra; tipo='docs' o 'codigo'; detalle=true trae el codigo."""
    t0 = time.time()
    results = indexer.search_desktop(query, limit=min(max(limit, 1), 10), project=project or None, tipo=tipo,
                                     check_impact=False)
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
            if i == 0 and r.get("exacto") and r.get("symbol_kind") in ("class", "variable"):
                miembros = _linea_de_miembros(r)
                if miembros:
                    out.append(miembros)
            if i == 0 and r.get("exacto"):
                usos = _linea_de_usos(r)
                if usos:
                    out.append(usos)
            if not detalle and len(results) > 1:
                out.append("\nOtros:")
        else:
            out.append(f"- {_ubicacion(r)} | {_firma(r.get('content', ''))}")
    return "\n".join(out)


MAX_USOS = 6  # sitios en la linea de usos del primer resultado: los suficientes para planear un cambio


MAX_MIEMBROS = 40


def _linea_de_miembros(r: dict) -> str:
    """Clase u objeto grande: el bloque devuelto es solo su cabecera (cada miembro es su propio
    fragmento), asi que se listan los miembros con su linea para no tener que abrir el archivo."""
    try:
        miembros = chunker.miembros_de_definicion(Path(r.get("file_path", "")), int(r.get("line", 1)))
    except Exception:
        return ""
    miembros = [m for m in miembros if m[0] > int(r.get("end_line", 0))]
    if not miembros:
        return ""
    partes = [f"{n}:{ln}" for ln, n, _ in miembros[:MAX_MIEMBROS]]
    resto = f" (y {len(miembros) - MAX_MIEMBROS} mas)" if len(miembros) > MAX_MIEMBROS else ""
    return f"Miembros ({len(miembros)}): " + ", ".join(partes) + resto


def _linea_de_usos(r: dict) -> str:
    """Una linea con donde se usa la definicion exacta (llamadas en su archivo y en los que la importan,
    resueltos): ahorra el grep que el agente haria despues para planear un cambio."""
    try:
        u = indexer.usos_de(r.get("symbol_name", ""), r.get("file_path", ""), r.get("project", ""),
                            rango_def=(int(r.get("line", 0)), int(r.get("end_line", 0))))
    except Exception:
        return ""
    sitios = u["sitios"]
    if not sitios and not u["importadores"]:
        return "Usos: ninguno fuera de su definicion."
    proyecto = r.get("project", "")
    codigo = [s for s in sitios if not indexer._es_prueba(s[0])]
    mostrados = codigo[:MAX_USOS]
    nombres = {os.path.basename(a) for a, _, _ in mostrados}
    ambiguo = len(nombres) < len({a for a, _, _ in mostrados})
    partes, previo = [], None
    for a, n, s in mostrados:  # sessions.py:324 open_session, :373 save_session
        archivo = "" if a == previo else (_ruta_corta(a, proyecto) if ambiguo else os.path.basename(a))
        partes.append(f"{archivo}:{n}" + (f" {s}" if s else ""))
        previo = a
    texto = "Usos: " + (", ".join(partes) if partes else "ninguno en el codigo")
    if len(codigo) > MAX_USOS:
        texto += f" (y {len(codigo) - MAX_USOS} mas)"
    if u["importadores"]:
        texto += f"; lo importan {u['importadores']} archivo(s)" + (f", {u['pruebas']} de pruebas" if u["pruebas"] else "")
    return texto


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
    """Esquema de un archivo: simbolos con sus lineas y metodos de clases grandes, sin codigo. Acepta ruta o solo el nombre."""
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


def _ruta_corta(ruta: str, proyecto: str = "") -> str:
    """Ruta relativa a la raiz de su proyecto (o al HOME): lo que el agente necesita, sin prefijos largos."""
    raiz = indexer.raiz_de_proyecto(proyecto) if proyecto else None
    for base in ([str(raiz)] if raiz else []) + [str(indexer.HOME)]:
        if ruta.startswith(base.rstrip("/") + "/"):
            return ruta[len(base.rstrip("/")) + 1:]
    return ruta


def _impacto_resuelto(symbol: str, project: str, archivo: str) -> Optional[str]:
    datos = indexer.consumidores(symbol, project or None)
    if datos is None:
        return None
    defs = datos["definiciones"]
    if archivo:
        defs = {d: v for d, v in defs.items() if d.endswith(archivo.lstrip("./"))}
    if not defs and not datos["externos"]:
        return None
    out = []
    total = len({f for v in defs.values() for f in v})
    if len(defs) > 1:
        out.append(f"'{symbol}': {len(defs)} definiciones; cada una con los archivos que dependen de ELLA.")
    for d, usuarios in sorted(defs.items(), key=lambda kv: -len(kv[1])):
        proyecto = datos["proyectos"].get(d, project)
        out.append(f"{_ruta_corta(d, proyecto)} -> {len(usuarios)} archivo(s) lo importan" + (":" if usuarios else ""))
        out += [f"  {_ruta_corta(u, proyecto)}" for u in sorted(usuarios)[:15]]
        if len(usuarios) > 15:
            out.append(f"  ... y {len(usuarios) - 15} mas")
    if datos["externos"]:
        ext = sorted(datos["externos"].items(), key=lambda kv: -kv[1])[:5]
        out.append("Con el mismo nombre, de paquetes externos: " + ", ".join(f"{o} ({n})" for o, n in ext))
    if datos["sin_resolver"]:
        sr = datos["sin_resolver"]
        out.append(f"Sin resolver ({len(sr)}): " + ", ".join(f"{_ruta_corta(a)} <- '{o}'" for a, o in sr[:5]))
    if not total and not datos["sin_resolver"]:
        out.append("Ningun archivo local lo importa.")
    return "\n".join(out)


@herramienta()
def get_impact_radius(symbol: str, project: str = "", archivo: str = "") -> str:
    """Archivos que dependen de un simbolo (se rompen si lo cambias), por definicion; archivo= elige una."""
    try:
        resuelto = _impacto_resuelto(symbol, project, archivo)
        if resuelto:
            return resuelto
    except Exception:
        pass  # sin resolucion: la busqueda por nombre de siempre
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
    """Mapa de firmas del proyecto por relevancia (PageRank) en un presupuesto de tokens."""
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


async def synrag_mas(ctx: Context) -> str:
    """Activa el resto de herramientas de SynRAG: impacto, esquema, mapa, pruebas, edicion."""
    nuevas = []
    while _pendientes:
        fn = _pendientes.pop(0)
        _registrar(fn)
        _activas.append(fn.__name__)
        nuevas.append(fn.__name__)
    if not nuevas:
        return f"Ya estaban activas {len(_activas)} herramientas: {', '.join(_activas)}."
    _compactar_esquemas()
    await ctx.session.send_tool_list_changed()
    return f"Activadas {len(nuevas)} herramientas: {', '.join(nuevas)}."


def _anunciar_list_changed():
    """MCPServer no expone NotificationOptions: el initialize sale de create_initialization_options()
    sin argumentos, asi que esa llamada fija tools_changed=True (tools.listChanged en el initialize)."""
    from mcp.server.lowlevel.server import NotificationOptions
    original = mcp._lowlevel_server.create_initialization_options

    def con_cambios(notification_options=None, *args, **kwargs):
        return original(notification_options or NotificationOptions(tools_changed=True), *args, **kwargs)

    mcp._lowlevel_server.create_initialization_options = con_cambios


if PERFIL == "bajo_demanda":
    _registrar(synrag_mas)
    _anunciar_list_changed()


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


