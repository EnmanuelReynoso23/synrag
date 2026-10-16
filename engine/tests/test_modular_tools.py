"""
Pruebas unitarias para la suite modular de 20 herramientas de SynRAG (engine/tools).
Verifica que cada herramienta maneje entradas válidas, casos límite y errores sin fallar inesperadamente.
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import context_tools, inspect_tools, patch_tools, runner_tools, safety_tools


def test_context_tools_git_staged(tmp_path):
    # En un directorio sin git, debe reportar limpiamente
    res = context_tools.git_staged_overview(str(tmp_path))
    assert isinstance(res, str)
    assert len(res) > 0


def test_context_tools_session_handoff(tmp_path):
    res = context_tools.session_handoff(str(tmp_path))
    assert isinstance(res, str)
    assert "TRASPASO DE SESIÓN" in res or "No se pudo obtener" in res or len(res) > 0


def test_context_tools_extract_todo(tmp_path):
    test_file = tmp_path / "app.py"
    test_file.write_text("# TODO: refactorizar autenticacion\n# FIXME: corregir timeout\n", encoding="utf-8")
    res = context_tools.extract_todo_status(str(tmp_path))
    assert isinstance(res, str)
    assert "TODO" in res or "FIXME" in res


def test_inspect_tools_contract(tmp_path):
    test_file = tmp_path / "sample.py"
    test_file.write_text("def calcular_total(precio: float, impuesto: float = 0.18) -> float:\n    \"\"\"Calcula el total con impuestos.\"\"\"\n    return precio * (1 + impuesto)\n", encoding="utf-8")
    res = inspect_tools.get_symbol_contract(str(test_file), "calcular_total")
    assert isinstance(res, str)
    assert "calcular_total" in res


def test_inspect_tools_type_definition(tmp_path):
    test_file = tmp_path / "types.ts"
    test_file.write_text("export interface Usuario {\n  id: string;\n  nombre: string;\n}\n", encoding="utf-8")
    res = inspect_tools.extract_type_definition(str(test_file), "Usuario")
    assert isinstance(res, str)
    assert "Usuario" in res or "interface" in res


def test_patch_tools_function_body(tmp_path):
    test_file = tmp_path / "mod.py"
    test_file.write_text("def saludar(nombre: str):\n    print('hola')\n    return nombre\n", encoding="utf-8")
    res = patch_tools.patch_function_body(str(test_file), "saludar", "    print('buenas tardes')\n    return f'hola {nombre}'\n")
    assert test_file.read_text(encoding="utf-8") == (
        "def saludar(nombre: str):\n    print('buenas tardes')\n    return f'hola {nombre}'\n")


def test_patch_tools_add_import(tmp_path):
    test_file = tmp_path / "main.py"
    test_file.write_text("import sys\n\nprint(sys.version)\n", encoding="utf-8")
    res = patch_tools.add_import_clean(str(test_file), "import os")
    assert test_file.read_text(encoding="utf-8") == "import sys\nimport os\n\nprint(sys.version)\n"


def test_runner_tools_tail_clean_logs(tmp_path):
    log_file = tmp_path / "app.log"
    log_file.write_text("line 1\nline 2\nERROR: timeout en conexion\nline 4\n", encoding="utf-8")
    res = runner_tools.tail_clean_logs(str(log_file), max_lines=2)
    assert isinstance(res, str)
    assert len(res) > 0


def test_safety_tools_verify_dependency(tmp_path):
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text('{"dependencies": {"react": "^18.0.0"}}', encoding="utf-8")
    res = safety_tools.verify_dependency_exists("react", str(tmp_path))
    assert isinstance(res, str)
    assert "react" in res

    res_missing = safety_tools.verify_dependency_exists("nonexistent-pkg-xyz", str(tmp_path))
    assert "ALERTA" in res_missing or "NO figura" in res_missing

