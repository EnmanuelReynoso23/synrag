"""
tests/test_runner_tools.py - Pruebas para runner_tools.
Verifica run_test_isolated, lint_summary, run_typecheck_focus y tail_clean_logs
con proyectos minimos aislados en tmp_path sin dependencias de red ni node_modules.
"""

import sys
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from tools import runner_tools


# ==============================================================================
# Pruebas para run_test_isolated
# ==============================================================================

def test_run_test_isolated_ok(tmp_path):
    """Verifica ejecucion exitosa de pruebas con resumen corto."""
    test_file = tmp_path / "test_ok.py"
    test_file.write_text("def test_dummy(): assert True\n", encoding="utf-8")

    cmd = f'"{sys.executable}" -m pytest "{test_file}" -q'
    res = runner_tools.run_test_isolated(cmd, cwd=str(tmp_path))

    assert "[SynRAG Tests OK]" in res
    assert "passed" in res.lower()
    # No debe filtrar rutas absolutas del usuario
    assert str(tmp_path) not in res


def test_run_test_isolated_failing_preserves_name_and_error(tmp_path):
    """Verifica que un fallo de prueba conserve siempre el nombre del test y el error."""
    test_file = tmp_path / "test_fail.py"
    test_file.write_text(
        "def test_failing_sample():\n"
        "    esperado = 42\n"
        "    obtenido = 99\n"
        "    assert obtenido == esperado, 'VALOR_INCORRECTO'\n",
        encoding="utf-8"
    )

    cmd = f'"{sys.executable}" -m pytest "{test_file}" -q'
    res = runner_tools.run_test_isolated(cmd, cwd=str(tmp_path))

    assert "[SynRAG Tests FALLÓ" in res
    assert "test_failing_sample" in res
    assert "VALOR_INCORRECTO" in res or "AssertionError" in res
    assert "1 failed" in res


def test_run_test_isolated_autodetect_python(tmp_path):
    """Auto-deteccion de pytest en un proyecto Python cuando test_command esta vacio."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
    test_file = tmp_path / "test_mini.py"
    test_file.write_text("def test_mini_pass(): assert 1 == 1\n", encoding="utf-8")

    res = runner_tools.run_test_isolated("", cwd=str(tmp_path))

    assert "[SynRAG Tests OK]" in res
    assert "passed" in res.lower()


def test_run_test_isolated_node_missing_node_modules(tmp_path):
    """Un proyecto Node sin node_modules debe avisar claramente en vez de fallar raro."""
    (tmp_path / "package.json").write_text('{"name": "demo", "scripts": {"test": "vitest"}}\n', encoding="utf-8")

    res = runner_tools.run_test_isolated("", cwd=str(tmp_path))

    assert "No se detectó node_modules" in res
    assert "npm install" in res or "pnpm install" in res


def test_run_test_isolated_unknown_project(tmp_path):
    """Directorio vacio sin runner detectable debe pedir test_command."""
    res = runner_tools.run_test_isolated("", cwd=str(tmp_path))

    assert "No se detectó un ejecutor de pruebas" in res


def test_run_test_isolated_timeout(tmp_path):
    """Comandos que se cuelgan deben terminar con mensaje de timeout."""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="sleep 100", timeout=45)):
        res = runner_tools.run_test_isolated("sleep 100", cwd=str(tmp_path))
        assert "Timeout:" in res
        assert "45 segundos" in res


# ==============================================================================
# Pruebas para lint_summary
# ==============================================================================

def test_lint_summary_node_missing_node_modules(tmp_path):
    """En proyecto Node sin node_modules debe informar claramente."""
    (tmp_path / "package.json").write_text('{"name": "demo"}\n', encoding="utf-8")

    res = runner_tools.lint_summary(cwd=str(tmp_path))

    assert "No se encontró node_modules ni un linter" in res
    assert "npm install" in res or "pnpm install" in res


def test_lint_summary_no_linter_found(tmp_path):
    """Sin linter configurado en entorno debe informar."""
    with patch("tools.runner_tools._find_binary", return_value=None):
        res = runner_tools.lint_summary(cwd=str(tmp_path))
        assert "No se detectó un linter configurado" in res


def test_lint_summary_python_ruff_mock(tmp_path):
    """Simula ejecucion de ruff check devolviendo errores en formato conciso."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")

    mock_res = subprocess.CompletedProcess(
        args=["ruff"],
        returncode=1,
        stdout="src/app.py:5:1: F401 'os' imported but unused\nsrc/app.py:10:5: E711 comparison to None\n",
        stderr=""
    )

    with patch("tools.runner_tools._find_binary", return_value="/bin/ruff"), \
         patch("subprocess.run", return_value=mock_res):
        res = runner_tools.lint_summary("src/app.py", cwd=str(tmp_path))

        assert "[SynRAG Linter] Errores encontrados (2):" in res
        assert "F401 'os' imported but unused" in res
        assert "E711 comparison to None" in res


def test_lint_summary_clean(tmp_path):
    """Cuando no hay errores de lint reporta cero errores."""
    mock_res = subprocess.CompletedProcess(
        args=["ruff"],
        returncode=0,
        stdout="",
        stderr=""
    )

    with patch("tools.runner_tools._find_binary", return_value="/bin/ruff"), \
         patch("subprocess.run", return_value=mock_res):
        res = runner_tools.lint_summary(cwd=str(tmp_path))
        assert "[SynRAG Linter] Cero errores de lint" in res


# ==============================================================================
# Pruebas para run_typecheck_focus
# ==============================================================================

def test_run_typecheck_focus_ts_missing_node_modules(tmp_path, monkeypatch):
    """Proyecto TypeScript sin node_modules debe avisar claramente."""
    (tmp_path / "tsconfig.json").write_text('{}\n', encoding="utf-8")
    # los runners de GitHub traen tsc global: aqui simulamos un equipo sin el
    monkeypatch.setattr(runner_tools.shutil, "which", lambda *a, **k: None)

    res = runner_tools.run_typecheck_focus(cwd=str(tmp_path))

    assert "No se encontró node_modules ni tsc instalado" in res
    assert "npm install" in res or "pnpm install" in res


def test_run_typecheck_focus_filtering_files(tmp_path):
    """Filtra errores dejando solo los archivos solicitados en 'files'."""
    (tmp_path / "tsconfig.json").write_text('{}\n', encoding="utf-8")

    mock_stdout = (
        "src/app.ts(12,5): error TS2322: Type 'string' is not assignable to type 'number'.\n"
        "src/other.ts(45,9): error TS2339: Property 'foo' does not exist on type 'Bar'.\n"
    )
    mock_res = subprocess.CompletedProcess(
        args=["tsc"],
        returncode=1,
        stdout=mock_stdout,
        stderr=""
    )

    with patch("tools.runner_tools._find_binary", side_effect=lambda name, td, is_node=False: "/bin/tsc" if name == "tsc" else None), \
         patch("subprocess.run", return_value=mock_res):

        # 1. Filtrando por app.ts: solo debe mostrar app.ts
        res_app = runner_tools.run_typecheck_focus("src/app.ts", cwd=str(tmp_path))
        assert "src/app.ts(12,5): error TS2322" in res_app
        assert "src/other.ts" not in res_app

        # 2. Filtrando por archivo sin errores
        res_clean = runner_tools.run_typecheck_focus("src/clean.ts", cwd=str(tmp_path))
        assert "no contienen errores de tipos" in res_clean


def test_run_typecheck_focus_python_pyright(tmp_path):
    """Deteccion de pyright en proyecto Python."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")

    mock_stdout = "src/demo.py:10:5 - error: Type mismatch (reportGeneralTypeIssues)\n"
    mock_res = subprocess.CompletedProcess(
        args=["pyright"],
        returncode=1,
        stdout=mock_stdout,
        stderr=""
    )

    with patch("tools.runner_tools._find_binary", side_effect=lambda name, td, is_node=False: "/bin/pyright" if name == "pyright" else None), \
         patch("subprocess.run", return_value=mock_res):
        res = runner_tools.run_typecheck_focus("src/demo.py", cwd=str(tmp_path))
        assert "[SynRAG Typecheck] Errores de tipos enfocados" in res
        assert "src/demo.py:10:5 - error: Type mismatch" in res


def test_run_typecheck_focus_all_clean(tmp_path):
    """Typecheck sin errores devuelve mensaje exitoso."""
    (tmp_path / "tsconfig.json").write_text('{}\n', encoding="utf-8")
    mock_res = subprocess.CompletedProcess(args=["tsc"], returncode=0, stdout="", stderr="")

    with patch("tools.runner_tools._find_binary", side_effect=lambda name, td, is_node=False: "/bin/tsc" if name == "tsc" else None), \
         patch("subprocess.run", return_value=mock_res):
        res = runner_tools.run_typecheck_focus(cwd=str(tmp_path))
        assert "[SynRAG Typecheck] Tipos verificados con éxito sin errores" in res


# ==============================================================================
# Pruebas para tail_clean_logs
# ==============================================================================

def test_tail_clean_logs_nonexistent(tmp_path):
    """Log inexistente informa error claro."""
    res = runner_tools.tail_clean_logs(str(tmp_path / "no_existe.log"))
    assert "No se encontró el archivo de log" in res


def test_tail_clean_logs_empty(tmp_path):
    """Log vacio reporta vacio."""
    vacio = tmp_path / "vacio.log"
    vacio.touch()
    res = runner_tools.tail_clean_logs(str(vacio))
    assert "está vacío" in res


def test_tail_clean_logs_collapsing_repeated_and_noise(tmp_path):
    """Colapsa lineas repetidas con timestamps variables y filtra ruido."""
    log_file = tmp_path / "test.log"
    lineas = [
        "2026-10-15 10:00:00 [worker-1] Inicio de servidor",
        "2026-10-15 10:00:01 GET /health 200",
        "2026-10-15 10:00:02 GET /favicon.ico 404",
        "2026-10-15 10:00:03 [worker-1] Peticion procesada id=42",
        "2026-10-15 10:00:04 [worker-1] Peticion procesada id=42",
        "2026-10-15 10:00:05 [worker-1] Peticion procesada id=42",
        "2026-10-15 10:00:06 [worker-1] ERROR: timeout al conectar con upstream",
    ]
    log_file.write_text("\n".join(lineas), encoding="utf-8")

    res = runner_tools.tail_clean_logs(str(log_file), max_lines=10)

    assert "Inicio de servidor" in res
    assert "/health" not in res
    assert "/favicon.ico" not in res
    assert "[repetido 3 veces]" in res
    assert "ERROR: timeout al conectar con upstream" in res


def test_tail_clean_logs_large_file(tmp_path):
    """Archivo de log grande (>256KB) lee solo el final eficientemente."""
    log_file = tmp_path / "large.log"
    with open(log_file, "w", encoding="utf-8") as f:
        # Generar ~300KB de texto
        for i in range(6000):
            f.write(f"2026-10-15 10:00:00 linea de log {i}\n")
        f.write("2026-10-15 10:00:00 ULTIMA_LINEA_CRITICA\n")

    res = runner_tools.tail_clean_logs(str(log_file), max_lines=5)

    assert "ULTIMA_LINEA_CRITICA" in res
    assert len(res.splitlines()) <= 8
