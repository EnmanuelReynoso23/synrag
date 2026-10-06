#!/usr/bin/env python3
"""
SyntaxRAG — Terminal UI & UX (v3.0)
Búsqueda por palabras (BM25) con reordenado FlashRank · Grafo de impacto
Búsqueda local · Sin APIs de pago
"""

import sys
import time
import os
from pathlib import Path
from typing import Optional

# Internal imports
sys.path.insert(0, str(Path(__file__).parent))
import indexer
import impact
import cache
import ranker
import telemetry
import server_mcp
import installer

import warnings
warnings.filterwarnings("ignore")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.syntax import Syntax
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

console = Console()

BANNER = """[#8B949E]      ╭──●     [/] [bold #FFFFFF]███████╗██╗   ██╗███╗   ██╗[/] [bold #00E5FF]██████╗   █████╗   ██████╗ [/]
[#8B949E]     ╱    ╲    [/] [bold #FFFFFF]██╔════╝╚██╗ ██╔╝████╗  ██║[/] [bold #00E5FF]██╔══██╗ ██╔══██╗ ██╔════╝ [/]
[#8B949E]    ●      [/][bold #00E5FF]◉   [/] [bold #FFFFFF]███████╗ ╚████╔╝ ██╔██╗ ██║[/] [bold #00E5FF]██████╔╝ ███████║ ██║  ███╗[/]
[#8B949E]     ╲    ╱    [/] [bold #FFFFFF]╚════██║  ╚██╔╝  ██║╚██╗██║[/] [bold #00E5FF]██╔══██╗ ██╔══██║ ██║   ██║[/]
[#8B949E]      ╰──●     [/] [bold #FFFFFF]███████║   ██║   ██║ ╚████║[/] [bold #00E5FF]██║  ██║ ██║  ██║ ╚██████╔╝[/]
               [bold #FFFFFF]╚══════╝   ╚═╝   ╚═╝  ╚═══╝[/] [bold #00E5FF]╚═╝  ╚═╝ ╚═╝  ╚═╝  ╚═════╝ [/]
                  [bold #8B949E]AST-NATIVE MCP ENGINE[/]  [dim #30363D]·[/]  [bold #00E5FF]BÚSQUEDA LOCAL[/]  [dim #30363D]·[/]  [bold #8B949E]IMPACT GRAPH[/]"""


def print_banner():
    console.print(BANNER)
    console.print()


def render_score_bar(score: float) -> str:
    pct = int(score * 100)
    bars = int(score * 10)
    filled = "█" * bars
    empty = "░" * (10 - bars)
    if score >= 0.8:
        color = "#00E5FF"
    elif score >= 0.5:
        color = "#8B949E"
    else:
        color = "#30363D"
    return f"[{color}]{pct}% {filled}{empty}[/]"


def get_kind_badge(kind: str) -> Text:
    badge_map = {
        "function": ("FN", "bold #0D1117 on #00E5FF"),
        "hook": ("HOOK", "bold #0D1117 on #58A6FF"),
        "class": ("CLASS", "bold #0D1117 on #E3B341"),
        "interface": ("TYPE", "bold #0D1117 on #79C0FF"),
        "type": ("TYPE", "bold #0D1117 on #79C0FF"),
        "variable": ("VAR", "bold #0D1117 on #D2A8FF"),
        "imports": ("IMPORT", "bold #0D1117 on #8B949E"),
        "section": ("DOC", "bold #0D1117 on #7EE787"),
    }
    label, style = badge_map.get(kind, ("CODE", "bold #0D1117 on #00E5FF"))
    return Text(f" {label} ", style=style)


def format_search_ui(query: str, limit: int = 5, project: Optional[str] = None):
    t0 = time.time()
    db = indexer.get_db()

    # Check cache status
    cached = cache.get_cached_results(db, query, project=project)
    is_cache_hit = cached is not None

    results = indexer.search_desktop(query, limit=limit, project=project)
    elapsed_ms = (time.time() - t0) * 1000

    print_banner()

    # Top search summary bar
    cache_badge = "[bold #00E5FF]ACIERTO DE CACHÉ (misma consulta)[/]" if is_cache_hit else "[dim #8B949E]BM25 (Tantivy) + reordenado FlashRank[/]"
    proj_badge = f" [dim #8B949E]en [bold #00E5FF]{project}[/][/]" if project else ""
    console.print(
        Panel(
            f"[bold #FFFFFF]SYN[bold #00E5FF]RAG[/]  ·  "
            f"[bold #8B949E]Consulta:[/] [bold #FFFFFF]\"{query}\"[/]{proj_badge}  ·  "
            f"[bold #8B949E]Resultados:[/] [bold #00E5FF]{len(results)}[/]  ·  "
            f"[bold #8B949E]Latencia:[/] [bold #7EE787]{elapsed_ms:.1f}ms[/]  ·  {cache_badge}",
            border_style="#00E5FF",
            box=box.ROUNDED,
            padding=(0, 1)
        )
    )

    if not results:
        console.print(Panel(f"[bold #8B949E][AVISO] No se encontraron fragmentos para:[/] [bold #FFFFFF]\"{query}\"[/]\n[dim #8B949E]Prueba con términos alternativos o reindexa con `synrag index`.[/]", border_style="#30363D", box=box.ROUNDED))
        return

    for idx, r in enumerate(results, 1):
        rel_path = r.get("rel_path", "")
        start_line = r.get("line", 1)
        end_line = r.get("end_line", start_line)
        line_str = f"L{start_line}-{end_line}" if end_line != start_line else f"L{start_line}"
        proj = r.get("project", "")
        sym_name = r.get("symbol_name", "")
        sym_kind = r.get("symbol_kind", "code")
        score = float(r.get("score", 1.0))
        content = r.get("content", "").strip()

        # Header layout
        badge = get_kind_badge(sym_kind)
        header_text = Text()
        header_text.append(f"#{idx} ", style="bold #00E5FF")
        header_text.append("▸ ", style="bold #8B949E")
        header_text.append(f"{rel_path}", style="bold #FFFFFF underline")
        header_text.append(f":{line_str} ", style="bold #00E5FF")
        header_text.append(f"[{proj}] ", style="bold #8B949E")

        if sym_name:
            header_text.append(f" {sym_name} ", style="bold #0D1117 on #00E5FF")
        header_text.append(" ")
        header_text.append_text(badge)

        # Score bar
        score_str = render_score_bar(score)

        # Syntax highlighted snippet
        ext = r.get("extension", "").lstrip(".")
        lexer = ext if ext in ("ts", "tsx", "js", "jsx", "py", "rs", "go", "html", "css", "json", "md") else "text"
        snippet_lines = content.splitlines()[:16]
        trimmed_content = "\n".join(snippet_lines)
        if len(content.splitlines()) > 16:
            trimmed_content += "\n// ... [recortado para visualización]"

        code_renderable = Syntax(
            trimmed_content,
            lexer=lexer,
            theme="monokai",
            line_numbers=True,
            start_line=start_line,
            word_wrap=True
        )

        # Impact graph warning
        dependents = r.get("dependents", [])

        console.print(
            Panel(
                Panel.fit(code_renderable, border_style="#30363D", box=box.SQUARE),
                title=header_text,
                subtitle=f"[#8B949E]Relevancia Neuronal:[/] {score_str}  ·  [dim #8B949E]SYNRAG Engine[/]",
                border_style="#00E5FF" if idx == 1 else "#30363D",
                box=box.ROUNDED,
                padding=(0, 1)
            )
        )

        if dependents:
            deps_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
            deps_table.add_column("Bullet", style="bold #FF7B72")
            deps_table.add_column("File", style="italic #FFFFFF")
            for dep in dependents[:6]:
                deps_table.add_row("├─", dep)
            if len(dependents) > 6:
                deps_table.add_row("└─", f"... y {len(dependents) - 6} archivos más")

            target_label = sym_name if sym_name else rel_path.split('/')[-1]
            impact_panel = Panel(
                deps_table,
                title=f"[bold #FF7B72][GRAFO DE IMPACTO] '{target_label}' es consumido por {len(dependents)} archivo(s)[/]",
                subtitle="[dim #FF7B72]Precaución al modificar argumentos o tipos para evitar código roto[/]",
                border_style="#FF7B72",
                box=box.ROUNDED,
                padding=(0, 1)
            )
            console.print(impact_panel)
        console.print()

    console.print(
        Panel(
            "[dim #8B949E][bold #FFFFFF]SYN[bold #00E5FF]RAG[/] · "
            "[#00E5FF]AST-Native Engine[/] · "
            "[white]Búsqueda local, sin APIs de pago[/] · "
            "[bold #00E5FF]Modo Standalone Universal[/][/]",
            border_style="#30363D",
            box=box.ROUNDED,
            padding=(0, 1)
        )
    )


def show_stats_ui():
    print_banner()
    db = indexer.get_db()
    if indexer.TABLE_NAME not in db.table_names():
        console.print("[yellow][AVISO] La base de datos aún no ha sido indexada. Ejecuta `syntaxrag index`.[/]")
        return

    tbl = db.open_table(indexer.TABLE_NAME)
    df = tbl.to_pandas()
    total_chunks = len(df)
    total_files = df["file_path"].nunique()

    # Impact table
    imp_links = 0
    if impact.IMPACT_TABLE in db.table_names():
        imp_tbl = db.open_table(impact.IMPACT_TABLE)
        imp_links = len(imp_tbl.to_pandas())

    # Size on disk
    size_mb = sum(f.stat().st_size for f in indexer.DB_PATH.glob("**/*") if f.is_file()) / (1024 * 1024)

    # Cache table & savings
    cache_entries = 0
    total_hits = 0
    if cache.CACHE_TABLE in db.table_names():
        try:
            cache_tbl = db.open_table(cache.CACHE_TABLE)
            cache_df = cache_tbl.to_pandas()
            cache_entries = len(cache_df)
            if "hit_count" in cache_df.columns:
                total_hits = int(cache_df["hit_count"].sum())
            else:
                total_hits = cache_entries
        except Exception:
            pass

    # Telemetria persistente historica (SQLite)
    t_stats = telemetry.get_summary_stats()
    today_t = t_stats["today"]
    all_t = t_stats["all_time"]
    por_agente = t_stats.get("por_agente", {})
    excluidas = t_stats.get("excluidas", 0)
    primera_fecha = t_stats.get("primera") or today_t.get("fecha", "")

    savings_table = Table(title="[bold #a6e3a1]Uso del buscador y referencia (persistente)[/]", box=box.ROUNDED, border_style="#a6e3a1")
    savings_table.add_column("Dato", style="bold white")
    savings_table.add_column("Valor", style="bold green", justify="right")
    savings_table.add_row("Consultas hoy", f"{today_t['queries']} (latencia media {today_t['avg_latency_ms']:.0f} ms)")
    savings_table.add_row("Tokens devueltos hoy", f"{today_t.get('tokens_retrieved', 0):,}")
    savings_table.add_row("Consultas registradas (histórico)", f"{all_t['queries']}")
    if primera_fecha:
        savings_table.add_row("Medido desde", primera_fecha)
    savings_table.add_row("Tokens devueltos (histórico)", f"{all_t.get('tokens_retrieved', 0):,}")
    if por_agente:
        str_agentes = " | ".join(f"{k}: {v}" for k, v in por_agente.items())
        savings_table.add_row("Por cliente", str_agentes)
    savings_table.add_row("Referencia: tamaño de los archivos devueltos menos lo devuelto", f"{all_t['tokens_saved']:,} tokens (NO es un ahorro medido)")
    if excluidas > 0:
        savings_table.add_row("Filas excluidas (no medidas)", f"{excluidas:,}")
    savings_table.add_row("Entradas en la caché de consultas", f"{cache_entries:,}")
    savings_table.add_row("Aciertos de caché registrados", f"{total_hits:,}")
    console.print(savings_table)
    console.print()

    # Projects breakdown
    proj_counts = df.groupby("project").size().sort_values(ascending=False)
    proj_table = Table(title="[bold bright_magenta]Proyectos Indexados por Fragmentos AST[/]", box=box.ROUNDED, border_style="bright_magenta")
    proj_table.add_column("Proyecto", style="bold cyan")
    proj_table.add_column("Fragmentos AST", justify="right", style="green")
    proj_table.add_column("Porcentaje", justify="right", style="yellow")

    for proj, count in proj_counts.head(15).items():
        pct = (count / total_chunks) * 100
        proj_table.add_row(str(proj), f"{count:,}", f"{pct:.1f}%")

    if len(proj_counts) > 15:
        proj_table.add_row(f"... y {len(proj_counts) - 15} proyectos más", "", "")

    console.print(proj_table)


def show_info_ui():
    print_banner()
    from rich.columns import Columns

    p1 = Panel(
        "[bold #FFFFFF]Tree-sitter AST Chunker[/]\n"
        "[#8B949E]• Troceado por AST: funciones, clases, hooks y tipos\n"
        "• Lenguajes: TypeScript, TSX, JavaScript, JSX, Python\n"
        "• Conserva firmas y docstrings; los bloques de más de 2.400 caracteres se dividen[/]",
        title="[bold #00E5FF]1. Parser Sintáctico AST[/]",
        border_style="#00E5FF",
        box=box.ROUNDED,
    )
    p2 = Panel(
        "[bold #FFFFFF]Observador de cambios (opcional)[/]\n"
        "[#8B949E]• Demonio systemd: [bold #FFFFFF]lancedb-watcher.service[/]\n"
        "• Monitoreo in-memory con librería [bold #FFFFFF]watchdog[/]\n"
        "• Reindexa solo el archivo guardado: ~8 ms, tras 0,6 s de espera para agrupar guardados[/]",
        title="[bold #00E5FF]2. Observador de Cambios[/]",
        border_style="#00E5FF",
        box=box.ROUNDED,
    )
    p3 = Panel(
        "[bold #FFFFFF]Caché Local de Consultas[/]\n"
        "[#8B949E]• Tabla LanceDB: [bold #FFFFFF]query_cache[/]\n"
        "• La misma consulta (sin distinguir mayúsculas ni espacios) se responde en ~9 ms\n"
        "• La búsqueda no usa APIs de pago; los resultados igualmente cuestan tokens al modelo[/]",
        title="[bold #00E5FF]3. Caché de Consultas[/]",
        border_style="#00E5FF",
        box=box.ROUNDED,
    )
    p4 = Panel(
        "[bold #FFFFFF]Grafo de Impacto de Dependencias[/]\n"
        "[#8B949E]• Tabla LanceDB: [bold #FFFFFF]impact_graph[/] (relaciones símbolo ← archivo que lo importa)\n"
        "• Mapea qué archivos importan cada símbolo\n"
        "• Previene bugs inyectando dependientes antes de editar código[/]",
        title="[bold #00E5FF]4. Prevención de Roturas[/]",
        border_style="#00E5FF",
        box=box.ROUNDED,
    )
    p5 = Panel(
        "[bold #FFFFFF]Reranker Neuronal FlashRank[/]\n"
        "[#8B949E]• Motor ONNX optimizado en CPU (ms-marco-TinyBERT)\n"
        "• Rerankea los candidatos BM25 de Tantivy\n"
        "• Puntuación continua de relevancia (0-100%)[/]",
        title="[bold #00E5FF]5. Reranking Neural[/]",
        border_style="#00E5FF",
        box=box.ROUNDED,
    )
    p6 = Panel(
        "[bold #FFFFFF]Standalone Agent Hub[/]\n"
        "[#8B949E]• Probado con Claude Code y Antigravity; las demás IAs se configuran sin probar\n"
        "• CLI integrado: [bold #FFFFFF]SYNRAG agy[/] (Antigravity)\n"
        "• CLI integrado: [bold #FFFFFF]SYNRAG claude[/] (Claude Code)\n"
        "• Protocolo MCP: [bold #FFFFFF]desktop-lancedb[/][/]",
        title="[bold #00E5FF]6. Entorno de Agentes Autónomo[/]",
        border_style="#00E5FF",
        box=box.ROUNDED,
    )

    console.print(Columns([p1, p2], equal=True))
    console.print(Columns([p3, p4], equal=True))
    console.print(Columns([p5, p6], equal=True))
    console.print()

    paths_table = Table(title="[bold #FFFFFF]Arquitectura del Ecosistema [/][bold #00E5FF]SYNRAG[/]", box=box.ROUNDED, border_style="#30363D")
    paths_table.add_column("Componente", style="bold #00E5FF")
    paths_table.add_column("Ruta en el Sistema", style="#FFFFFF")
    paths_table.add_column("Rol en el Ecosistema", style="#8B949E")

    paths_table.add_row("Comando Maestro", "~/.local/bin/SYNRAG  (o synrag)", "Lanzador unificado (Búsqueda AST + Agentes + Telemetría)")
    paths_table.add_row("Wrapper MCP/Legacy", "~/.local/bin/ai-search", "Alias compatible con herramientas existentes")
    paths_table.add_row("Base de Datos", "~/.local/share/lancedb-hub/data", "LanceDB (chunks, impact_graph, query_cache)")
    paths_table.add_row("Código Central", "~/.local/opt/lancedb-hub/", "chunker.py, impact.py, cache.py, ranker.py, indexer.py")
    paths_table.add_row("Servicio Watcher", "~/.config/systemd/user/lancedb-watcher.service", "Observador opcional: reindexa el archivo guardado")
    paths_table.add_row("Configuración MCP", "~/.gemini/config/mcp_config.json  (Claude Code: ~/.claude.json)", "Dónde Antigravity y Claude Code cargan el servidor MCP")
    paths_table.add_row("Antigravity CLI", "~/.local/bin/agy", "CLI oficial de Google Antigravity en CachyOS")
    paths_table.add_row("Claude Code CLI", "~/.local/bin/claude", "CLI oficial de Anthropic Claude Code en CachyOS")

    console.print(paths_table)


def run_index_ui():
    print_banner()
    with Progress(
        SpinnerColumn("dots", style="#00E5FF"),
        TextColumn("[bold #00E5FF]{task.description}[/]"),
        console=console
    ) as progress:
        task = progress.add_task("Indexando repositorios con Tree-sitter AST y Grafo de Impacto...", total=None)
        t0 = time.time()
        indexer.index_desktop()
        elapsed = time.time() - t0
        progress.update(task, description=f"[bold #00E5FF][OK] Indexación completada en {elapsed:.1f}s![/]")


def run_watch_ui():
    print_banner()
    import subprocess
    console.print(Panel("[bold #00E5FF]Monitor del Observador de Cambios[/]\n[#8B949E]Vigilando cambios en tus proyectos. Cada archivo guardado se reindexa tras 0,6 s sin nuevos cambios.[/]", border_style="#00E5FF", box=box.ROUNDED))
    try:
        subprocess.run(["journalctl", "--user", "-u", "lancedb-watcher.service", "-f", "--no-pager"])
    except KeyboardInterrupt:
        console.print("\n[dim]Monitor finalizado.[/]")


def _estado_observador() -> str:
    import shutil, subprocess
    if not shutil.which("systemctl"):
        return "sin systemd"
    try:
        r = subprocess.run(["systemctl", "--user", "is-active", "lancedb-watcher.service"],
                           capture_output=True, text=True, timeout=3)
    except Exception:
        return "desconocido"
    return {"active": "activo", "inactive": "inactivo", "failed": "con fallo"}.get(r.stdout.strip(), "no instalado")


def _contar_relaciones() -> int:
    try:
        db = indexer.get_db()
        return db.open_table(impact.IMPACT_TABLE).count_rows() if impact.IMPACT_TABLE in db.table_names() else 0
    except Exception:
        return 0


def _entradas_cache() -> int:
    try:
        db = indexer.get_db()
        return db.open_table(cache.CACHE_TABLE).count_rows() if cache.CACHE_TABLE in db.table_names() else 0
    except Exception:
        return 0


def _ias_con_synrag() -> list:
    h = Path.home()
    rutas = (("Claude Code", h / ".claude.json"),
             ("Antigravity", h / ".gemini" / "config" / "mcp_config.json"),
             ("Antigravity (ruta anterior)", h / ".gemini" / "antigravity" / "mcp_config.json"),
             ("Gemini CLI", h / ".gemini" / "settings.json"), ("Cursor", h / ".cursor" / "mcp.json"),
             ("Windsurf", h / ".codeium" / "windsurf" / "mcp_config.json"),
             ("Zed", h / ".config" / "zed" / "settings.json"), ("Codex CLI", h / ".codex" / "config.toml"))
    return [n for n, p in rutas if p.is_file() and "desktop-lancedb" in p.read_text(encoding="utf-8", errors="ignore")]


def print_help_menu():
    print_banner()

    cmd_table = Table(title="[bold #FFFFFF]Comandos del Ecosistema [/][bold #00E5FF]SYNRAG[/]", box=box.ROUNDED, border_style="#30363D")
    cmd_table.add_column("Comando", style="bold #00E5FF")
    cmd_table.add_column("Descripción", style="#FFFFFF")
    cmd_table.add_column("Ejemplo", style="#8B949E")

    cmd_table.add_row("SYNRAG", "Muestra este panel de control y resumen del motor", "SYNRAG")
    cmd_table.add_row("SYNRAG <consulta>", "Búsqueda por palabras (BM25) + reordenado FlashRank", "SYNRAG asistenciaServicio")
    cmd_table.add_row("SYNRAG --project <p> <q>", "Filtrar por proyecto específico", "SYNRAG --project asistoya-web webhook")
    cmd_table.add_row("SYNRAG outline <archivo>", "Esquema sintáctico (firmas y rangos de línea)", "SYNRAG outline asistencia.servicio.ts")
    cmd_table.add_row("SYNRAG impact <símbolo>", "Radio de impacto y dependientes de una función", "SYNRAG impact asistenciaServicio")
    cmd_table.add_row("SYNRAG tests <símbolo>", "Localiza los tests asociados a un símbolo", "SYNRAG tests asistenciaServicio")
    cmd_table.add_row("SYNRAG configure", "Auto-configura todas las IAs del sistema (MCP)", "SYNRAG configure")
    cmd_table.add_row("SYNRAG uninstall", "Quita SYNRAG de todas tus IAs (no borra el motor)", "SYNRAG uninstall")
    cmd_table.add_row("SYNRAG stats", "Uso del buscador, latencia y fragmentos", "SYNRAG stats")
    cmd_table.add_row("SYNRAG info", "Dashboard de arquitectura, subsistemas y rutas", "SYNRAG info")
    cmd_table.add_row("SYNRAG index", "Reindexar repositorios con Tree-sitter AST", "SYNRAG index")
    cmd_table.add_row("SYNRAG watch", "Ver el log del observador de cambios (opcional)", "SYNRAG watch")
    cmd_table.add_row("SYNRAG agy | claude", "Lanzar Antigravity CLI o Claude Code directamente", "SYNRAG agy")

    console.print(cmd_table)
    console.print()

    status_panel = Panel(
        f"[bold #8B949E]Observador de cambios:[/] [bold #00E5FF]{_estado_observador()}[/]  ·  "
        f"[bold #8B949E]Caché de consultas:[/] [bold #00E5FF]{_entradas_cache():,} entradas[/]\n"
        f"[bold #8B949E]Grafo de Impacto:[/] [bold #58A6FF]{_contar_relaciones():,} relaciones[/]  ·  "
        "[bold #8B949E]Reordenado:[/] [bold #00E5FF]FlashRank ONNX en CPU[/]\n"
        f"[bold #8B949E]IAs con SYNRAG configurado:[/] [bold #FFFFFF]{', '.join(_ias_con_synrag()) or 'ninguna (ejecuta SYNRAG configure)'}[/]",
        title="[bold #00E5FF]ESTADO DEL SISTEMA (comprobado ahora)[/]",
        border_style="#00E5FF",
        box=box.ROUNDED,
        padding=(0, 1),
    )
    console.print(status_panel)


def main():
    if len(sys.argv) == 1:
        print_help_menu()
        sys.exit(0)

    arg1 = sys.argv[1]
    if arg1 in ("help", "--help", "-h"):
        print_help_menu()
        sys.exit(0)
    elif arg1 in ("info", "--info", "about", "--about", "arch"):
        show_info_ui()
    elif arg1 in ("stats", "--stats", "-s"):
        show_stats_ui()
    elif arg1 in ("index", "--index", "-i"):
        run_index_ui()
    elif arg1 in ("watch", "--watch", "-w"):
        run_watch_ui()
    elif arg1 in ("configure", "install", "--configure"):
        installer.run_full_installation()
    elif arg1 in ("uninstall", "--uninstall"):
        installer.run_uninstall()
    elif arg1 in ("outline", "--outline") and len(sys.argv) > 2:
        file_arg = sys.argv[2]
        console.print(Panel(server_mcp.get_file_outline(file_arg), border_style="#00E5FF", box=box.ROUNDED))
    elif arg1 in ("impact", "--impact", "blast") and len(sys.argv) > 2:
        sym_arg = sys.argv[2]
        console.print(Panel(server_mcp.get_impact_radius(sym_arg), border_style="#FF7B72", box=box.ROUNDED))
    elif arg1 in ("tests", "--tests", "test") and len(sys.argv) > 2:
        test_arg = sys.argv[2]
        console.print(Panel(server_mcp.find_related_tests(test_arg), border_style="#7EE787", box=box.ROUNDED))
    elif arg1 == "--project" and len(sys.argv) > 3:
        proj = sys.argv[2]
        query = " ".join(sys.argv[3:])
        format_search_ui(query, project=proj)
    else:
        query = " ".join(sys.argv[1:])
        format_search_ui(query)


if __name__ == "__main__":
    main()
