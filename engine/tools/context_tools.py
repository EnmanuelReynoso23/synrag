"""
tools/context_tools.py - Herramientas para la gestion de contexto, sesiones y traspasos.
Atacan el principal sumidero de tokens: la longitud de las sesiones (>40 turnos).
"""

import os
import subprocess
from pathlib import Path
from typing import Optional


def _resolve_repo_path(repo_path: str = "") -> Path:
    if repo_path:
        p = Path(repo_path).expanduser().resolve()
        if p.is_file():
            return p.parent
        return p
    return Path.cwd()


def session_handoff(repo_path: str = "") -> str:
    """Resumen corto de la rama, commits y cambios para continuar en otra sesion."""
    target_dir = _resolve_repo_path(repo_path)
    try:
        if not target_dir.exists():
            return f"[SynRAG Handoff] La ruta '{target_dir}' no existe."
        if not target_dir.is_dir():
            return f"[SynRAG Handoff] '{target_dir}' no es un directorio válido."

        # Verificar si es un repo git
        res_git = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=5
        )
        if res_git.returncode != 0:
            return f"[SynRAG Handoff] '{target_dir}' no es un repositorio Git válido."

        # Rama actual
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=5
        ).stdout.strip() or "HEAD desacoplado"

        # Upstream remoto y estado de sincronizacion
        res_up = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "@{upstream}"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=5
        )
        if res_up.returncode == 0:
            up = res_up.stdout.strip()
            res_ab = subprocess.run(
                ["git", "rev-list", "--left-right", "--count", f"HEAD...{up}"],
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            if res_ab.returncode == 0 and res_ab.stdout.strip():
                partes = res_ab.stdout.strip().split()
                if len(partes) == 2:
                    ahead, behind = int(partes[0]), int(partes[1])
                    detalles = []
                    if ahead > 0:
                        detalles.append(f"{ahead} por subir")
                    if behind > 0:
                        detalles.append(f"{behind} por bajar")
                    info_upstream = f" ({up}: {', '.join(detalles)})" if detalles else f" (al día con {up})"
                else:
                    info_upstream = f" (upstream: {up})"
            else:
                info_upstream = f" (upstream: {up})"
        else:
            info_upstream = " (sin upstream remoto)"

        # Ultimo commit
        ultimo_commit = subprocess.run(
            ["git", "log", "-1", "--oneline"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=5
        ).stdout.strip() or "Sin commits todavía"

        # Archivos modificados y estado
        status_raw = subprocess.run(
            ["git", "status", "-s"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=5
        ).stdout.strip()

        # Resumen de cambios en diffstat (HEAD para staged + unstaged si hay commits, fallback si no)
        res_diff = subprocess.run(
            ["git", "diff", "HEAD", "--stat"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=5
        )
        if res_diff.returncode != 0:
            res_diff = subprocess.run(
                ["git", "diff", "--stat"],
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
        diffstat = res_diff.stdout.strip()

        lineas_status = [l for l in status_raw.splitlines() if l.strip()]
        total_modificados = len(lineas_status)

        out = [
            f"[SynRAG Handoff] TRASPASO DE SESIÓN: {target_dir.name} ({target_dir})",
            f"Rama activa: {branch}{info_upstream}",
            f"Último commit: {ultimo_commit}",
            f"Archivos tocados ({total_modificados}):",
        ]

        if lineas_status:
            for l in lineas_status[:15]:
                out.append(f"  {l}")
            if len(lineas_status) > 15:
                out.append(f"  ... y {len(lineas_status) - 15} archivos más.")
        else:
            out.append("  (Árbol de trabajo limpio sin cambios pendientes)")

        if diffstat:
            out.append("Resumen de cambios:")
            for l in diffstat.splitlines()[-4:]:
                out.append(f"  {l}")

        out.append(f"Continuación: continúa en '{target_dir.name}'. Revisa el último commit y archivos pendientes.")
        return "\n".join(out)

    except Exception as e:
        return f"[SynRAG Handoff] Error al generar punto de control: {e}"


def context_budget_alert(transcript_dir: str = "") -> str:
    """Avisa si las sesiones recientes del agente estan creciendo demasiado."""
    try:
        home = Path.home()
        candidatos = []

        if transcript_dir:
            td = Path(transcript_dir).expanduser().resolve()
            if not td.exists():
                return "[SynRAG Presupuesto] No se encontró directorio de transcripts en la ruta indicada."
            if td.is_file():
                candidatos = [td]
            else:
                archivos = [f for f in td.glob("*.jsonl") if f.is_file()]
                if not archivos:
                    # Quizas se paso la raiz de un proyecto: buscar su transcript en Claude Code
                    enc = str(td).replace(os.sep, "-").replace("/", "-")
                    claude_proj = home / ".claude" / "projects" / enc
                    if claude_proj.is_dir():
                        archivos = [f for f in claude_proj.glob("*.jsonl") if f.is_file()]
                if not archivos:
                    return "[SynRAG Presupuesto] No hay sesiones activas registradas para analizar."
                candidatos = archivos
        else:
            import telemetry
            cliente = telemetry.detectar_cliente()
            cwd = Path.cwd().resolve()

            if cliente == "claude-code":
                # Para Claude Code: la carpeta del proyecto del directorio actual y el .jsonl mas reciente directamente dentro (no en subcarpetas)
                claude_base = home / ".claude" / "projects"
                if claude_base.is_dir():
                    rutas = [cwd] + list(cwd.parents)
                    for r in rutas:
                        enc = str(r).replace(os.sep, "-").replace("/", "-")
                        pdir = claude_base / enc
                        if pdir.is_dir():
                            files = [f for f in pdir.glob("*.jsonl") if f.is_file()]
                            if files:
                                candidatos = files
                                break
                if not candidatos:
                    return f"[SynRAG Presupuesto] No se encontraron sesiones activas de Claude Code para '{cwd.name}'."

            elif cliente in ("antigravity", "gemini-cli"):
                # Antigravity CLI: ~/.gemini/antigravity-cli/conversations/
                agy_conv = home / ".gemini" / "antigravity-cli" / "conversations"
                if agy_conv.is_dir():
                    candidatos = [
                        f for f in agy_conv.iterdir()
                        if f.is_file() and not f.name.endswith(("-wal", "-shm"))
                    ]
                if not candidatos:
                    return "[SynRAG Presupuesto] No se encontraron sesiones activas de Antigravity CLI."

            elif cliente == "codex":
                # Codex: ~/.codex/sessions/
                codex_dir = home / ".codex" / "sessions"
                if codex_dir.is_dir():
                    candidatos = [
                        f for f in codex_dir.glob("*.jsonl") if f.is_file()
                    ] + [
                        f for f in codex_dir.glob("*.json") if f.is_file()
                    ]
                if not candidatos:
                    return "[SynRAG Presupuesto] No se encontraron sesiones activas de Codex."

            else:
                return f"[SynRAG Presupuesto] No se pudo identificar el cliente de IA actual ('{cliente}'). Especifica transcript_dir para analizar una sesión."

        if not candidatos:
            return "[SynRAG Presupuesto] No hay sesiones activas registradas para analizar."

        # Seleccionar la mas reciente por fecha de modificacion dentro del cliente
        candidatos.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        ultimo = candidatos[0]

        tam_bytes = ultimo.stat().st_size
        tam_kb = tam_bytes / 1024
        total_lineas = 0

        if ultimo.suffix == ".db":
            try:
                import sqlite3
                with sqlite3.connect(ultimo) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT count(*) FROM steps")
                    row = cur.fetchone()
                    if row:
                        total_lineas = int(row[0])
            except Exception:
                total_lineas = max(1, int(tam_kb // 20))
        else:
            # Lee los jsonl SOLO para contar; no imprimas su contenido.
            with open(ultimo, "r", encoding="utf-8", errors="ignore") as f:
                for _ in f:
                    total_lineas += 1

        # Estimacion de nivel de advertencia
        if total_lineas < 25 and tam_kb < 300:
            estado = "VERDE (Sesión ligera)"
            recomendacion = "El contexto acumulado es bajo. Puedes continuar normalmente."
        elif total_lineas < 45 and tam_kb < 800:
            estado = "AMARILLO (Atención: contexto moderado)"
            recomendacion = "La sesión comienza a acumular peso. Planifica cerrar esta tarea en los próximos turnos."
        else:
            estado = "ROJO (Alerta: sesión sobrecargada)"
            recomendacion = "La sesión supera los 45 turnos o 800 KB; cada turno reenvía todo el historial acumulado. Haz commit, ejecuta 'session_handoff' y abre una sesión nueva para partir de cero."

        out = [
            f"[SynRAG Presupuesto de Contexto] Sesión actual: {ultimo.name}",
            f"Turnos acumulados: ~{total_lineas} eventos ({tam_kb:.1f} KB)",
            f"Estado del semáforo: {estado}",
            f"Recomendación: {recomendacion}",
        ]
        return "\n".join(out)

    except Exception as e:
        return f"[SynRAG Presupuesto] Error al evaluar presupuesto de sesión: {e}"


def git_staged_overview(repo_path: str = "") -> str:
    """Cambios en stage, una linea por archivo."""
    target_dir = _resolve_repo_path(repo_path)
    try:
        if not target_dir.exists():
            return f"[SynRAG Git Staged] La ruta '{target_dir}' no existe."
        if not target_dir.is_dir():
            return f"[SynRAG Git Staged] '{target_dir}' no es un directorio válido."

        res_git = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=5
        )
        if res_git.returncode != 0:
            return f"[SynRAG Git Staged] '{target_dir}' no es un repositorio Git válido."

        res = subprocess.run(
            ["git", "diff", "--staged", "--compact-summary"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=5
        )
        if res.returncode != 0:
            # Fallback a --stat
            res = subprocess.run(
                ["git", "diff", "--staged", "--stat"],
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=5
            )

        salida = res.stdout.strip()
        if not salida:
            return f"[SynRAG Git Staged] No hay cambios en stage (git add) en '{target_dir.name}'."

        lineas = [l for l in salida.splitlines() if l.strip()]
        if len(lineas) > 20:
            if "changed" in lineas[-1]:
                archivos_lineas = lineas[:-1]
                resumen_final = lineas[-1]
            else:
                archivos_lineas = lineas
                resumen_final = ""

            if len(archivos_lineas) > 20:
                sobrantes = len(archivos_lineas) - 20
                partes = archivos_lineas[:20] + [f"  ... y {sobrantes} archivos más en stage."]
                if resumen_final:
                    partes.append(resumen_final)
                cuerpo = "\n".join(partes)
            else:
                cuerpo = salida
        else:
            cuerpo = salida

        return f"[SynRAG Git Staged] Cambios listos para commit en '{target_dir.name}':\n{cuerpo}"
    except Exception as e:
        return f"[SynRAG Git Staged] Error al obtener staged summary: {e}"


def extract_todo_status(project: str = "") -> str:
    """TODO/FIXME/PENDIENTE/HACK en comentarios de un proyecto (nombre o ruta)."""
    import indexer
    target_dir = indexer.raiz_de_proyecto(project) if project else Path.cwd()
    if not target_dir:
        return f"No se encontro el proyecto '{project}'."
    # solo marcas en mayusculas dentro de un comentario: `invalidarTodo:` no es una tarea
    patron = r"(//|#|/\*|^\s*\*|<!--)\s*(TODO|FIXME|PENDIENTE|HACK)\b"
    try:
        try:
            res = subprocess.run(["rg", "-n", "--no-heading", "--max-count", "5", "-e", patron, str(target_dir)],
                                 capture_output=True, text=True, timeout=15)
            salida = res.stdout
        except FileNotFoundError:
            salida = subprocess.run(["grep", "-rnIE", "--exclude-dir=.git", "--exclude-dir=node_modules",
                                     "--exclude-dir=dist", patron, str(target_dir)],
                                    capture_output=True, text=True, timeout=15).stdout
    except Exception as e:
        return f"Error al buscar TODOs: {e}"
    lineas = [l for l in salida.splitlines() if l.strip()]
    if not lineas:
        return f"Sin TODO/FIXME/PENDIENTE en {target_dir}."
    out = [f"{len(lineas)} pendiente(s) en {target_dir}:"]
    for l in lineas[:30]:
        partes = l.split(":", 2)
        if len(partes) == 3:
            out.append(f"  {os.path.relpath(partes[0], target_dir)}:{partes[1]}  {partes[2].strip()[:90]}")
    if len(lineas) > 30:
        out.append(f"  ... y {len(lineas) - 30} mas")
    return "\n".join(out)
