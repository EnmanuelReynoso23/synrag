"""
Pruebas unitarias para las herramientas de seguridad (engine/tools/safety_tools.py).
Cubre verify_dependency_exists, check_circular_imports, check_breaking_callsites
y find_code_duplicates sobre proyectos mínimos aislados en tmp_path y casa.
"""

import json
from pathlib import Path
import pytest

from tools import safety_tools


# ==============================================================================
# 1. verify_dependency_exists
# ==============================================================================

def test_verify_dependency_node_real_and_missing(tmp_path):
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text(json.dumps({
        "name": "my-node-app",
        "dependencies": {"express": "^4.18.2"},
        "devDependencies": {"typescript": "^5.0.0", "@types/node": "^20.0.0"}
    }), encoding="utf-8")

    # Dependencia directa
    res_real = safety_tools.verify_dependency_exists("express", str(tmp_path))
    assert "[SynRAG Dep OK]" in res_real
    assert "express" in res_real
    assert "dependencies" in res_real

    # DevDependency
    res_dev = safety_tools.verify_dependency_exists("typescript", str(tmp_path))
    assert "[SynRAG Dep OK]" in res_dev
    assert "devDependencies" in res_dev

    # Subpath de dependencia existente (e.g. @types/node/child_process)
    res_sub = safety_tools.verify_dependency_exists("@types/node/assert", str(tmp_path))
    assert "[SynRAG Dep OK]" in res_sub
    assert "@types/node" in res_sub

    # Dependencia inexistente
    res_missing = safety_tools.verify_dependency_exists("paquete_inexistente_xyz_123", str(tmp_path))
    assert "[SynRAG Dep ALERTA]" in res_missing
    assert "NO figura" in res_missing


def test_verify_dependency_node_builtins(tmp_path):
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text(json.dumps({"name": "app"}), encoding="utf-8")

    # Builtin estandar
    res_fs = safety_tools.verify_dependency_exists("fs", str(tmp_path))
    assert "[SynRAG Dep OK]" in res_fs
    assert "módulo estándar de Node.js" in res_fs

    # Builtin con prefijo node:
    res_node_crypto = safety_tools.verify_dependency_exists("node:crypto", str(tmp_path))
    assert "[SynRAG Dep OK]" in res_node_crypto
    assert "módulo estándar de Node.js" in res_node_crypto


def test_verify_dependency_tsconfig_alias(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"name": "ts-project"}), encoding="utf-8")
    (tmp_path / "tsconfig.json").write_text("""{
        "compilerOptions": {
            "baseUrl": ".",
            "paths": {
                "@/*": ["src/*"],
                "~/*": ["app/*"],
                "@components/*": ["src/components/*"],
                "@utils": ["src/utils/index.ts"]
            }
        }
    }""", encoding="utf-8")

    # Import que coincide con alias @/*
    res_alias = safety_tools.verify_dependency_exists("@/services/auth", str(tmp_path))
    assert "[SynRAG Dep OK]" in res_alias
    assert "alias de tsconfig" in res_alias

    # Import que coincide con alias @components/*
    res_comp = safety_tools.verify_dependency_exists("@components/Button", str(tmp_path))
    assert "[SynRAG Dep OK]" in res_comp
    assert "alias de tsconfig" in res_comp

    # Import que coincide exactamente con @utils
    res_utils = safety_tools.verify_dependency_exists("@utils", str(tmp_path))
    assert "[SynRAG Dep OK]" in res_utils
    assert "alias de tsconfig" in res_utils

    # Import no cubierto por los alias
    res_uncovered = safety_tools.verify_dependency_exists("random-external-pkg", str(tmp_path))
    assert "[SynRAG Dep ALERTA]" in res_uncovered


def test_verify_dependency_python_real_and_missing(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
[project]
name = "my-flask-app"
dependencies = [
    "click>=8.0",
    "flask_login>=0.6.0",
    "python-dotenv",
]
""", encoding="utf-8")

    # Paquete real
    res_click = safety_tools.verify_dependency_exists("click", str(tmp_path))
    assert "[SynRAG Dep OK]" in res_click
    assert "click" in res_click

    # Normalización de nombres PEP 503 (flask-login vs flask_login)
    res_norm = safety_tools.verify_dependency_exists("flask-login", str(tmp_path))
    assert "[SynRAG Dep OK]" in res_norm

    # Mapeo de nombre importado (dotenv -> python-dotenv)
    res_map = safety_tools.verify_dependency_exists("dotenv", str(tmp_path))
    assert "[SynRAG Dep OK]" in res_map

    # Paquete inexistente
    res_missing = safety_tools.verify_dependency_exists("fake_package_xyz_999", str(tmp_path))
    assert "[SynRAG Dep ALERTA]" in res_missing


def test_verify_dependency_python_stdlib(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")

    for mod in ("os", "sys", "json", "pathlib", "subprocess", "ast"):
        res = safety_tools.verify_dependency_exists(mod, str(tmp_path))
        assert "[SynRAG Dep OK]" in res
        assert "módulo estándar de Python" in res


def test_verify_dependency_project_by_name(casa, helper_crear_proyecto):
    helper_crear_proyecto(casa, "servicio-auth", {
        "package.json": json.dumps({"dependencies": {"jsonwebtoken": "^9.0.0"}})
    })
    # Debe resolverse pasando únicamente el nombre del proyecto
    res = safety_tools.verify_dependency_exists("jsonwebtoken", "servicio-auth")
    assert "[SynRAG Dep OK]" in res
    assert "jsonwebtoken" in res


# ==============================================================================
# 2. check_circular_imports
# ==============================================================================

def test_check_circular_imports_two_files_python(tmp_path):
    fa = tmp_path / "modulo_a.py"
    fb = tmp_path / "modulo_b.py"

    fa.write_text("# Modulo A\n", encoding="utf-8")
    fb.write_text("import modulo_a\n", encoding="utf-8")

    # Si modulo_a intenta importar modulo_b, se crea un ciclo directo A -> B -> A
    res = safety_tools.check_circular_imports(str(fa), str(fb))
    assert "[SynRAG Circular DETECTADO]" in res
    assert "'modulo_a.py' -> 'modulo_b.py' -> 'modulo_a.py'" in res


def test_check_circular_imports_three_files_python(tmp_path):
    fa = tmp_path / "a.py"
    fb = tmp_path / "b.py"
    fc = tmp_path / "c.py"

    fa.write_text("# a.py\n", encoding="utf-8")
    fb.write_text("import c\n", encoding="utf-8")
    fc.write_text("import a\n", encoding="utf-8")

    # b importa c, c importa a -> importar b en a crea A -> B -> C -> A
    res = safety_tools.check_circular_imports(str(fa), str(fb))
    assert "[SynRAG Circular DETECTADO]" in res
    assert "'a.py' -> 'b.py' -> 'c.py' -> 'a.py'" in res


def test_check_circular_imports_relative_imports(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    fa = pkg / "base.py"
    fb = pkg / "derived.py"

    fa.write_text("# base\n", encoding="utf-8")
    fb.write_text("from .base import BaseClass\n", encoding="utf-8")

    # base -> derived crearía un ciclo con derived -> base
    res = safety_tools.check_circular_imports(str(fa), str(fb))
    assert "[SynRAG Circular DETECTADO]" in res
    assert "'base.py' -> 'derived.py' -> 'base.py'" in res


def test_check_circular_imports_safe_and_false_positive_prevention(tmp_path):
    fa = tmp_path / "app.py"
    fb = tmp_path / "config.py"

    fa.write_text("# app\n", encoding="utf-8")
    # Texto y comentarios que contienen la palabra 'app', pero NO es un import
    fb.write_text("""
# Configuration for the application
APP_NAME = "my awesome app"
DEFAULT_HOST = "localhost"
""", encoding="utf-8")

    res = safety_tools.check_circular_imports(str(fa), str(fb))
    assert "[SynRAG Circular OK]" in res
    assert "Seguro:" in res


def test_check_circular_imports_js_ts(tmp_path):
    fa = tmp_path / "a.ts"
    fb = tmp_path / "b.ts"
    fc = tmp_path / "c.ts"

    fa.write_text("export const a = 1;\n", encoding="utf-8")
    fb.write_text("import { c } from './c';\nexport const b = 2;\n", encoding="utf-8")
    fc.write_text("import { a } from './a';\nexport const c = 3;\n", encoding="utf-8")

    res = safety_tools.check_circular_imports(str(fa), str(fb))
    assert "[SynRAG Circular DETECTADO]" in res
    assert "'a.ts' -> 'b.ts' -> 'c.ts' -> 'a.ts'" in res


def test_check_circular_imports_edge_cases(tmp_path):
    fa = tmp_path / "self_import.py"
    fa.write_text("x = 1\n", encoding="utf-8")

    # Autociclo
    res_self = safety_tools.check_circular_imports(str(fa), str(fa))
    assert "[SynRAG Circular DETECTADO]" in res_self
    assert "no puede importarse a sí mismo" in res_self

    # Archivo inexistente
    res_missing = safety_tools.check_circular_imports(str(fa), str(tmp_path / "no_existe.py"))
    assert "[SynRAG Circular]" in res_missing
    assert "no existen" in res_missing


# ==============================================================================
# 3. check_breaking_callsites
# ==============================================================================

def test_check_breaking_callsites_new_required_param(tmp_path):
    mod = tmp_path / "calculator.py"
    caller = tmp_path / "caller.py"

    mod.write_text("def calculate(amount):\n    return amount * 1.1\n", encoding="utf-8")
    caller.write_text("from calculator import calculate\nres = calculate(100)\n", encoding="utf-8")

    # Nueva firma con parámetro obligatorio adicional
    res = safety_tools.check_breaking_callsites(str(mod), "calculate", "amount, tax_rate")
    assert "[SynRAG Breaking ALERTA]" in res
    assert "falta parámetro obligatorio 'tax_rate'" in res
    assert "calculate(100)" in res


def test_check_breaking_callsites_removed_param(tmp_path):
    mod = tmp_path / "formatter.py"
    caller = tmp_path / "caller.py"

    mod.write_text("def format_text(text, prefix, suffix):\n    return f'{prefix}{text}{suffix}'\n", encoding="utf-8")
    caller.write_text("from formatter import format_text\nformat_text('hello', '[', ']')\n", encoding="utf-8")

    # Nueva firma con menos parámetros (se eliminó suffix)
    res = safety_tools.check_breaking_callsites(str(mod), "format_text", "text, prefix")
    assert "[SynRAG Breaking ALERTA]" in res
    assert "demasiados argumentos posicionales" in res


def test_check_breaking_callsites_keyword_args_python(tmp_path):
    mod = tmp_path / "mailer.py"
    caller = tmp_path / "caller.py"

    mod.write_text("def send_mail(to, subject, cc=None):\n    pass\n", encoding="utf-8")
    caller.write_text("from mailer import send_mail\nsend_mail('a@b.com', 'hola', cc='c@d.com')\n", encoding="utf-8")

    # Se renombra cc a copy_to -> la llamada con cc='c@d.com' romperá en Python
    res = safety_tools.check_breaking_callsites(str(mod), "send_mail", "to, subject, copy_to=None")
    assert "[SynRAG Breaking ALERTA]" in res
    assert "argumento con nombre 'cc' no existe en la nueva firma" in res


def test_check_breaking_callsites_compatible_changes(tmp_path):
    mod = tmp_path / "processor.py"
    caller = tmp_path / "caller.py"

    mod.write_text("def run_task(task_id):\n    return task_id\n", encoding="utf-8")
    caller.write_text("from processor import run_task\nrun_task('t1')\n", encoding="utf-8")

    # Agregar parámetro opcional con default no debe romper llamadas existentes
    res = safety_tools.check_breaking_callsites(str(mod), "run_task", "task_id, retries: int = 3, timeout: int = 30")
    assert "[SynRAG Breaking OK]" in res
    assert "compatibles con la nueva firma" in res


def test_check_breaking_callsites_multiline_call(tmp_path):
    mod = tmp_path / "api.py"
    caller = tmp_path / "caller.py"

    mod.write_text("def query_data(endpoint, auth_token=None):\n    pass\n", encoding="utf-8")
    caller.write_text("""
from api import query_data

result = query_data(
    "/users",
    auth_token="token_123"
)
""", encoding="utf-8")

    # Se quita auth_token de la firma
    res = safety_tools.check_breaking_callsites(str(mod), "query_data", "endpoint, api_key=None")
    assert "[SynRAG Breaking ALERTA]" in res
    assert "argumento con nombre 'auth_token' no existe en la nueva firma" in res


def test_check_breaking_callsites_no_callers(tmp_path):
    mod = tmp_path / "unused.py"
    mod.write_text("def unused_fn(x, y):\n    return x + y\n", encoding="utf-8")

    res = safety_tools.check_breaking_callsites(str(mod), "unused_fn", "x, y, z")
    assert "[SynRAG Breaking OK]" in res
    assert "No se encontraron llamadas" in res


# ==============================================================================
# 4. find_code_duplicates
# ==============================================================================

def test_find_code_duplicates_similar_names(tmp_path):
    src = tmp_path / "user_service.py"
    src.write_text("""
def get_user_id(username: str) -> int:
    return 42

def find_user_by_email(email: str):
    pass
""", encoding="utf-8")

    # Búsqueda de get_user_by_id debe encontrar get_user_id por superposición de tokens
    res = safety_tools.find_code_duplicates("get_user_by_id", str(tmp_path))
    assert "[SynRAG Duplicados]" in res
    assert "get_user_id" in res


def test_find_code_duplicates_plural_and_typo(tmp_path):
    src = tmp_path / "billing.py"
    src.write_text("""
def calculate_totals(items):
    return sum(items)
""", encoding="utf-8")

    # calculate_total debe encontrar calculate_totals
    res = safety_tools.find_code_duplicates("calculate_total", str(tmp_path))
    assert "[SynRAG Duplicados]" in res
    assert "calculate_totals" in res


def test_find_code_duplicates_classes_and_async(tmp_path):
    src = tmp_path / "handlers.py"
    src.write_text("""
class UserSessionManager:
    pass

async def fetch_user_profile(user_id: str):
    pass
""", encoding="utf-8")

    # Debe encontrar definiciones de clase
    res_class = safety_tools.find_code_duplicates("UserSession", str(tmp_path))
    assert "[SynRAG Duplicados]" in res_class
    assert "UserSessionManager" in res_class

    # Debe encontrar funciones async def
    res_async = safety_tools.find_code_duplicates("fetch_user", str(tmp_path))
    assert "[SynRAG Duplicados]" in res_async
    assert "fetch_user_profile" in res_async


def test_find_code_duplicates_project_by_name(casa, helper_crear_proyecto):
    helper_crear_proyecto(casa, "finanzas-app", {
        "invoice.py": "def process_invoice_payment(invoice_id):\n    pass\n"
    })

    # Búsqueda pasando únicamente el nombre del proyecto
    res = safety_tools.find_code_duplicates("process_invoice", "finanzas-app")
    assert "[SynRAG Duplicados]" in res
    assert "process_invoice_payment" in res


def test_find_code_duplicates_none_found(tmp_path):
    src = tmp_path / "math.py"
    src.write_text("def sum_numbers(a, b): return a + b\n", encoding="utf-8")

    res = safety_tools.find_code_duplicates("completely_unrelated_xyz", str(tmp_path))
    assert "No se detectaron símbolos similares" in res


# ==============================================================================
# 5. Monorepos y Workspaces
# ==============================================================================

def test_verify_dependency_pnpm_workspace(tmp_path):
    # Raíz del monorepo con pnpm-workspace.yaml y package.json sin la dependencia
    (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - 'apps/*'\n  - 'packages/*'\n", encoding="utf-8")
    (tmp_path / "package.json").write_text(json.dumps({"name": "mi-monorepo"}), encoding="utf-8")

    # apps/web con appwrite
    apps_web = tmp_path / "apps" / "web"
    apps_web.mkdir(parents=True)
    (apps_web / "package.json").write_text(json.dumps({
        "name": "@mi-monorepo/web",
        "dependencies": {"appwrite": "^22.4.1"}
    }), encoding="utf-8")

    # packages/auth con jose
    pkgs_auth = tmp_path / "packages" / "auth"
    pkgs_auth.mkdir(parents=True)
    (pkgs_auth / "package.json").write_text(json.dumps({
        "name": "@mi-monorepo/auth",
        "dependencies": {"jose": "^5.0.0"}
    }), encoding="utf-8")

    # 1. Búsqueda sin desde_archivo: encuentra appwrite en apps/web/package.json
    res_appwrite = safety_tools.verify_dependency_exists("appwrite", str(tmp_path))
    assert "[SynRAG Dep OK]" in res_appwrite
    assert "apps/web/package.json" in res_appwrite
    assert "^22.4.1" in res_appwrite

    # 2. Búsqueda con desde_archivo: prioriza el package.json más cercano
    archivo_web = apps_web / "src" / "lib" / "client.ts"
    archivo_web.parent.mkdir(parents=True)
    archivo_web.write_text("export const x = 1;\n", encoding="utf-8")
    res_web = safety_tools.verify_dependency_exists("appwrite", str(tmp_path), desde_archivo="apps/web/src/lib/client.ts")
    assert "[SynRAG Dep OK]" in res_web
    assert "apps/web/package.json" in res_web

    # 3. Búsqueda de jose en packages/auth
    res_jose = safety_tools.verify_dependency_exists("jose", str(tmp_path))
    assert "[SynRAG Dep OK]" in res_jose
    assert "packages/auth/package.json" in res_jose

    # 4. Paquete inexistente: alerta indicando número de paquetes revisados
    res_missing = safety_tools.verify_dependency_exists("paquete_fantasma_xyz", str(tmp_path))
    assert "[SynRAG Dep ALERTA]" in res_missing
    assert "revisados 3 paquetes del workspace" in res_missing


def test_verify_dependency_npm_workspaces(tmp_path):
    # Raíz con workspaces de npm/yarn
    (tmp_path / "package.json").write_text(json.dumps({
        "name": "npm-monorepo",
        "workspaces": ["packages/*"]
    }), encoding="utf-8")

    # packages/ui con react
    pkgs_ui = tmp_path / "packages" / "ui"
    pkgs_ui.mkdir(parents=True)
    (pkgs_ui / "package.json").write_text(json.dumps({
        "name": "@npm-monorepo/ui",
        "dependencies": {"react": "^18.2.0"}
    }), encoding="utf-8")

    res_react = safety_tools.verify_dependency_exists("react", str(tmp_path))
    assert "[SynRAG Dep OK]" in res_react
    assert "packages/ui/package.json" in res_react
    assert "^18.2.0" in res_react


def test_verify_dependency_python_monorepo(tmp_path):
    # Monorepo Python con servicios independientes
    service_api = tmp_path / "services" / "api"
    service_api.mkdir(parents=True)
    (service_api / "pyproject.toml").write_text("""
[project]
name = "api-service"
dependencies = ["fastapi>=0.100.0"]
""", encoding="utf-8")

    res_fastapi = safety_tools.verify_dependency_exists("fastapi", str(tmp_path))
    assert "[SynRAG Dep OK]" in res_fastapi
    assert "services/api/pyproject.toml" in res_fastapi


def test_verify_dependency_workspace_installed_node_modules(tmp_path):
    (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - 'apps/*'\n", encoding="utf-8")
    (tmp_path / "package.json").write_text(json.dumps({"name": "repo"}), encoding="utf-8")

    apps_web = tmp_path / "apps" / "web"
    apps_web.mkdir(parents=True)
    (apps_web / "package.json").write_text(json.dumps({"name": "web"}), encoding="utf-8")

    # Instalado directamente en node_modules del paquete web
    nm_pkg = apps_web / "node_modules" / "local-helper"
    nm_pkg.mkdir(parents=True)

    res_helper = safety_tools.verify_dependency_exists("local-helper", str(tmp_path))
    assert "[SynRAG Dep OK]" in res_helper
    assert "apps/web/node_modules/local-helper" in res_helper



def test_busqueda_sin_ripgrep_da_lo_mismo(tmp_path, monkeypatch):
    """Sin rg instalado, check_breaking_callsites y find_code_duplicates usan la busqueda en Python."""
    (tmp_path / "calculator.py").write_text("def calculate(amount):\n    return amount * 1.1\n", encoding="utf-8")
    (tmp_path / "caller.py").write_text("from calculator import calculate\nres = calculate(100)\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "otro.py").write_text("calculate(1, 2, 3)\n", encoding="utf-8")
    (tmp_path / "datos.bin").write_bytes(b"\0calculate(9)\n")

    run_original = safety_tools.subprocess.run

    def sin_rg(cmd, *a, **k):
        if cmd and cmd[0] == "rg":
            raise FileNotFoundError(2, "No such file or directory: 'rg'")
        return run_original(cmd, *a, **k)

    monkeypatch.setattr(safety_tools.subprocess, "run", sin_rg)
    lineas = safety_tools._buscar_lineas(r"\bcalculate\s*\(", tmp_path)
    assert sorted(Path(l.split(":", 2)[0]).name for l in lineas) == ["calculator.py", "caller.py"]

    res = safety_tools.check_breaking_callsites(str(tmp_path / "calculator.py"), "calculate", "amount, tax_rate")
    assert "[SynRAG Breaking ALERTA]" in res and "calculate(100)" in res

    res = safety_tools.find_code_duplicates("calculate_total", str(tmp_path))
    assert "calculate" in res and "Error" not in res
