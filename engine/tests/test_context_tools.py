"""
engine/tests/test_context_tools.py - Pruebas para tools/context_tools.py.

Verifica:
1. context_budget_alert: rutas de Claude Code (carpeta codificada), Antigravity CLI,
   Codex, niveles de alerta (VERDE, AMARILLO, ROJO), conteo sin imprimir contenido,
   y salida de 3 a 5 lineas.
2. session_handoff y git_staged_overview: fuera de git, rutas inexistentes, repos
   sin commits, cambios staged y sin stage, archivos untracked, rama con y sin upstream,
   HEAD desacoplado y truncado de salidas largas.
3. Descripciones de UNA linea en todas las herramientas.
"""

import os
import sqlite3
import subprocess
import time
from pathlib import Path
import pytest

from tools import context_tools


def _configurar_git(repo: Path):
    """Inicializa un repo git con configuracion de usuario minima para pruebas."""
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "SynRAG Tester"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "tester@synrag.local"], cwd=repo, capture_output=True, check=True)


# ==============================================================================
# PRUEBAS PARA context_budget_alert
# ==============================================================================

def test_context_budget_alert_claude_code(casa, monkeypatch):
    """Busca sesiones de Claude Code usando el directorio actual codificado."""
    proj = casa / "mi-proyecto"
    proj.mkdir()
    monkeypatch.chdir(proj)
    monkeypatch.setattr("telemetry.detectar_cliente", lambda: "claude-code")

    enc = str(proj.resolve()).replace(os.sep, "-").replace("/", "-")
    claude_dir = casa / ".claude" / "projects" / enc
    claude_dir.mkdir(parents=True)

    jsonl_file = claude_dir / "sesion_activa.jsonl"
    lineas = ['{"event": "user", "text": "linea ' + str(i) + '"}\n' for i in range(15)]
    jsonl_file.write_text("".join(lineas), encoding="utf-8")

    res = context_tools.context_budget_alert()
    lineas_res = res.splitlines()

    # Formato: 3 a 5 lineas
    assert 3 <= len(lineas_res) <= 5
    assert "sesion_activa.jsonl" in res
    assert "~15 eventos" in res
    assert "VERDE" in res
    # No debe imprimir el contenido interno del jsonl
    assert "linea 0" not in res
    assert "linea 14" not in res


def test_context_budget_alert_niveles_semaforo(casa, tmp_path):
    """Verifica los umbrales VERDE, AMARILLO y ROJO sin cifras no medidas."""
    sesiones_dir = tmp_path / "sesiones"
    sesiones_dir.mkdir()

    # 1. VERDE: <25 turnos y <300 KB
    verde_file = sesiones_dir / "verde.jsonl"
    verde_file.write_text("\n".join(['{"k": "v"}'] * 10) + "\n", encoding="utf-8")
    res_verde = context_tools.context_budget_alert(str(sesiones_dir))
    assert "VERDE" in res_verde
    assert "~10 eventos" in res_verde

    # 2. AMARILLO: 30 turnos y <800 KB
    amarillo_file = sesiones_dir / "amarillo.jsonl"
    amarillo_file.write_text("\n".join(['{"k": "v"}'] * 30) + "\n", encoding="utf-8")
    os.utime(amarillo_file, (time.time() + 10, time.time() + 10))
    res_amarillo = context_tools.context_budget_alert(str(sesiones_dir))
    assert "AMARILLO" in res_amarillo
    assert "~30 eventos" in res_amarillo

    # 3. ROJO: >45 turnos
    rojo_file = sesiones_dir / "rojo.jsonl"
    rojo_file.write_text("\n".join(['{"k": "v"}'] * 50) + "\n", encoding="utf-8")
    os.utime(rojo_file, (time.time() + 20, time.time() + 20))
    res_rojo = context_tools.context_budget_alert(str(sesiones_dir))
    assert "ROJO" in res_rojo
    assert "~50 eventos" in res_rojo
    # Sin cifras no medidas
    assert "60-70%" not in res_rojo
    assert "session_handoff" in res_rojo


def test_context_budget_alert_claude_ignora_antigravity_mas_reciente(casa, monkeypatch):
    """Si el cliente es Claude Code, no debe elegir un transcript mas reciente de Antigravity."""
    proj = casa / "proyecto-activo"
    proj.mkdir()
    monkeypatch.chdir(proj)
    monkeypatch.setattr("telemetry.detectar_cliente", lambda: "claude-code")

    # Sesion de Claude Code
    enc = str(proj.resolve()).replace(os.sep, "-").replace("/", "-")
    claude_dir = casa / ".claude" / "projects" / enc
    claude_dir.mkdir(parents=True)
    claude_file = claude_dir / "claude_activa.jsonl"
    claude_file.write_text("c1\nc2\n", encoding="utf-8")
    os.utime(claude_file, (time.time() - 200, time.time() - 200))

    # Transcript de Antigravity mucho mas reciente
    agy_dir = casa / ".gemini" / "antigravity-cli" / "conversations"
    agy_dir.mkdir(parents=True)
    agy_file = agy_dir / "antigravity_paralelo.jsonl"
    agy_file.write_text("a1\na2\na3\n", encoding="utf-8")
    os.utime(agy_file, (time.time() + 500, time.time() + 500))

    res = context_tools.context_budget_alert()
    assert "claude_activa.jsonl" in res
    assert "antigravity_paralelo.jsonl" not in res


def test_context_budget_alert_antigravity_cli_jsonl(casa, monkeypatch):
    """Detecta sesiones en ~/.gemini/antigravity-cli/conversations/*.jsonl cuando el cliente es Antigravity."""
    monkeypatch.setattr("telemetry.detectar_cliente", lambda: "antigravity")
    agy_dir = casa / ".gemini" / "antigravity-cli" / "conversations"
    agy_dir.mkdir(parents=True)

    sesion = agy_dir / "sesion_gemini.jsonl"
    sesion.write_text("\n".join(['{"step": 1}'] * 20) + "\n", encoding="utf-8")

    res = context_tools.context_budget_alert()
    assert "sesion_gemini.jsonl" in res
    assert "~20 eventos" in res
    assert "VERDE" in res


def test_context_budget_alert_antigravity_cli_sqlite_db(casa, monkeypatch):
    """Detecta sesiones SQLite en ~/.gemini/antigravity-cli/conversations/*.db para Antigravity."""
    monkeypatch.setattr("telemetry.detectar_cliente", lambda: "antigravity")
    agy_dir = casa / ".gemini" / "antigravity-cli" / "conversations"
    agy_dir.mkdir(parents=True)

    db_path = agy_dir / "conversacion.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE steps (id INTEGER PRIMARY KEY, msg TEXT)")
        for i in range(35):
            conn.execute("INSERT INTO steps (msg) VALUES (?)", (f"paso {i}",))

    res = context_tools.context_budget_alert()
    assert "conversacion.db" in res
    assert "~35 eventos" in res
    assert "AMARILLO" in res


def test_context_budget_alert_codex(casa, monkeypatch):
    """Detecta sesiones en ~/.codex/sessions/ cuando el cliente es Codex."""
    monkeypatch.setattr("telemetry.detectar_cliente", lambda: "codex")
    codex_dir = casa / ".codex" / "sessions"
    codex_dir.mkdir(parents=True)

    codex_file = codex_dir / "codex_turnos.jsonl"
    codex_file.write_text("\n".join(['{"codex": true}'] * 18) + "\n", encoding="utf-8")

    res = context_tools.context_budget_alert()
    assert "codex_turnos.jsonl" in res
    assert "~18 eventos" in res


def test_context_budget_alert_prioriza_mas_reciente_dentro_del_cliente(casa, monkeypatch):
    """Dentro del mismo cliente, escoge la sesion con st_mtime mas reciente."""
    proj = casa / "proyecto"
    proj.mkdir()
    monkeypatch.chdir(proj)
    monkeypatch.setattr("telemetry.detectar_cliente", lambda: "claude-code")

    enc = str(proj.resolve()).replace(os.sep, "-").replace("/", "-")
    claude_dir = casa / ".claude" / "projects" / enc
    claude_dir.mkdir(parents=True)

    f_antiguo = claude_dir / "antiguo.jsonl"
    f_antiguo.write_text("linea1\n", encoding="utf-8")
    os.utime(f_antiguo, (time.time() - 500, time.time() - 500))

    f_reciente = claude_dir / "reciente.jsonl"
    f_reciente.write_text("linea1\nlinea2\n", encoding="utf-8")
    os.utime(f_reciente, (time.time() + 100, time.time() + 100))

    res = context_tools.context_budget_alert()
    assert "reciente.jsonl" in res


def test_context_budget_alert_cliente_desconocido(casa, monkeypatch):
    """Si no se puede identificar el cliente, informa en la salida en vez de adivinar."""
    monkeypatch.setattr("telemetry.detectar_cliente", lambda: "desconocido")
    res = context_tools.context_budget_alert()
    assert "[SynRAG Presupuesto]" in res
    assert "No se pudo identificar el cliente de IA actual" in res


def test_context_budget_alert_sin_sesiones(casa, monkeypatch):
    """Informa limpiamente si no existen sesiones activas para el cliente detectado."""
    monkeypatch.setattr("telemetry.detectar_cliente", lambda: "antigravity")
    res = context_tools.context_budget_alert()
    assert "[SynRAG Presupuesto]" in res
    assert "No se encontraron sesiones activas" in res


def test_context_budget_alert_ruta_inexistente(casa):
    """Informa limpiamente si la ruta de transcripts pasada no existe."""
    res = context_tools.context_budget_alert(str(casa / "inexistente"))
    assert "[SynRAG Presupuesto]" in res
    assert "No se encontró directorio" in res


# ==============================================================================
# PRUEBAS PARA session_handoff
# ==============================================================================

def test_session_handoff_fuera_de_repo(tmp_path):
    """Fuera de un repo git, reporta que no es valido sin fallar."""
    res = context_tools.session_handoff(str(tmp_path))
    assert "[SynRAG Handoff]" in res
    assert "no es un repositorio Git válido" in res


def test_session_handoff_ruta_inexistente(tmp_path):
    """Ruta inexistente reporta error claro."""
    res = context_tools.session_handoff(str(tmp_path / "carpeta_que_no_existe"))
    assert "[SynRAG Handoff]" in res
    assert "no existe" in res


def test_session_handoff_sin_commits(tmp_path):
    """Repo nuevo sin commits."""
    _configurar_git(tmp_path)
    res = context_tools.session_handoff(str(tmp_path))
    assert "[SynRAG Handoff]" in res
    assert "TRASPASO DE SESIÓN" in res
    assert "Sin commits todavía" in res
    assert "(Árbol de trabajo limpio" in res


def test_session_handoff_con_commits_y_cambios(tmp_path):
    """Repo con commits, archivos modificados y archivos untracked."""
    _configurar_git(tmp_path)

    # Commit inicial
    f1 = tmp_path / "modulo.py"
    f1.write_text("def inicio(): pass\n", encoding="utf-8")
    subprocess.run(["git", "add", "modulo.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "feat: commit inicial"], cwd=tmp_path, check=True)

    # Modificacion sin stage
    f1.write_text("def inicio(): return 42\n", encoding="utf-8")

    # Archivo nuevo sin stage (untracked)
    f2 = tmp_path / "nuevo.txt"
    f2.write_text("untracked\n", encoding="utf-8")

    res = context_tools.session_handoff(str(tmp_path))
    assert "feat: commit inicial" in res
    assert "Archivos tocados (2):" in res
    assert "M modulo.py" in res
    assert "?? nuevo.txt" in res
    assert "Resumen de cambios:" in res
    assert "modulo.py" in res


def test_session_handoff_rama_sin_upstream(tmp_path):
    """Repo local sin servidor remoto ni upstream configurado."""
    _configurar_git(tmp_path)
    f = tmp_path / "base.txt"
    f.write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True)

    res = context_tools.session_handoff(str(tmp_path))
    assert "Rama activa: main (sin upstream remoto)" in res


def test_session_handoff_rama_con_upstream_y_commits_por_subir(tmp_path):
    """Repo sincronizado con upstream remoto que tiene commits locales por subir."""
    remoto = tmp_path / "remoto.git"
    subprocess.run(["git", "init", "--bare", str(remoto)], check=True)

    local = tmp_path / "local"
    subprocess.run(["git", "clone", str(remoto), str(local)], check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=local, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=local, check=True)

    # Primer commit sincronizado
    f = local / "f.txt"
    f.write_text("v1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=local, check=True)
    subprocess.run(["git", "commit", "-m", "c1"], cwd=local, check=True)
    subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=local, check=True)

    # Segundo commit local no subido
    f.write_text("v2\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-am", "c2 local"], cwd=local, check=True)

    res = context_tools.session_handoff(str(local))
    assert "por subir" in res


def test_session_handoff_muchos_archivos_truncado(tmp_path):
    """Si hay mas de 15 archivos modificados, trunca la lista para no inflar contexto."""
    _configurar_git(tmp_path)
    (tmp_path / "base.txt").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=tmp_path, check=True)

    for i in range(25):
        (tmp_path / f"archivo_{i:02d}.txt").write_text(f"contenido {i}\n", encoding="utf-8")

    res = context_tools.session_handoff(str(tmp_path))
    assert "Archivos tocados (25):" in res
    assert "... y 10 archivos más." in res


# ==============================================================================
# PRUEBAS PARA git_staged_overview
# ==============================================================================

def test_git_staged_overview_fuera_de_repo(tmp_path):
    """Fuera de un repo git, reporta que no es repositorio valido."""
    res = context_tools.git_staged_overview(str(tmp_path))
    assert "[SynRAG Git Staged]" in res
    assert "no es un repositorio Git válido" in res


def test_git_staged_overview_ruta_inexistente(tmp_path):
    """Ruta inexistente reporta error claro."""
    res = context_tools.git_staged_overview(str(tmp_path / "no_existe"))
    assert "[SynRAG Git Staged]" in res
    assert "no existe" in res


def test_git_staged_overview_sin_staged(tmp_path):
    """Repo limpio o con cambios sin stage reporta que no hay nada en stage."""
    _configurar_git(tmp_path)
    (tmp_path / "archivo.txt").write_text("sin stage\n", encoding="utf-8")

    res = context_tools.git_staged_overview(str(tmp_path))
    assert "[SynRAG Git Staged]" in res
    assert "No hay cambios en stage" in res


def test_git_staged_overview_con_staged(tmp_path):
    """Archivos en stage aparecen en la salida."""
    _configurar_git(tmp_path)
    f = tmp_path / "staged.py"
    f.write_text("print(1)\n", encoding="utf-8")
    subprocess.run(["git", "add", "staged.py"], cwd=tmp_path, check=True)

    res = context_tools.git_staged_overview(str(tmp_path))
    assert "[SynRAG Git Staged]" in res
    assert "Cambios listos para commit" in res
    assert "staged.py" in res


def test_git_staged_overview_muchos_archivos_staged(tmp_path):
    """Si hay mas de 20 archivos en stage, trunca para no saturar tokens."""
    _configurar_git(tmp_path)
    for i in range(25):
        (tmp_path / f"staged_{i:02d}.txt").write_text(f"data {i}\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)

    res = context_tools.git_staged_overview(str(tmp_path))
    assert "Cambios listos para commit" in res
    assert "... y 5 archivos más en stage." in res


# ==============================================================================
# PRUEBAS PARA DESCRIPCIONES DE UNA LINEA
# ==============================================================================

def test_herramientas_contexto_docstring_una_linea():
    """Todas las herramientas deben tener una descripcion de UNA sola linea."""
    for fn in (
        context_tools.session_handoff,
        context_tools.context_budget_alert,
        context_tools.git_staged_overview,
        context_tools.extract_todo_status,
    ):
        doc = fn.__doc__
        assert doc is not None, f"{fn.__name__} no tiene docstring"
        assert "\n" not in doc.strip(), f"{fn.__name__} tiene mas de una linea en su docstring: {doc}"
