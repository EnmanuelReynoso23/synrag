import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

import hook_pista
import installer

MOTOR = Path(__file__).resolve().parent.parent
HOOK = MOTOR / "hook_pista.py"

CODIGO = [
    "El test tests/test_login.py falla con AssertionError en la linea 40",
    "Hay un bug en la función calcularTotal del carrito",
    "Refactoriza el modulo de pagos para usar mensaje_amigable",
    "como hago un import de pandas en el script de limpieza?",
    "Revisa `main.rs` y dime que hace",
    "necesito un endpoint para listar escuelas",
]

CHARLA = [
    "Hola, buenos dias",
    "Cual es la capital de Francia?",
    "Escribeme un poema corto sobre el mar",
    "Gracias, eso me sirvio mucho",
    "Dame ideas para el nombre de mi perro",
    "Traduceme 'buenos dias' al ingles",
]


def _ejecutar_hook(entrada: str):
    """Ejecuta el hook como lo hace Claude Code: JSON por stdin, codigo de salida y stdout."""
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=entrada,
        capture_output=True,
        text=True,
        timeout=10,
    )


def _entrada(prompt: str) -> str:
    return json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": prompt}, ensure_ascii=False)


@pytest.mark.parametrize("mensaje", CODIGO)
def test_mensaje_de_codigo_recibe_pista(mensaje):
    assert hook_pista.procesar(mensaje) == {
        "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": hook_pista.PISTA}
    }
    res = _ejecutar_hook(_entrada(mensaje))
    assert res.returncode == 0
    assert json.loads(res.stdout) == hook_pista.procesar(mensaje)


@pytest.mark.parametrize("mensaje", CHARLA)
def test_charla_no_recibe_pista(mensaje):
    assert hook_pista.procesar(mensaje) == {}
    res = _ejecutar_hook(_entrada(mensaje))
    assert res.returncode == 0
    assert res.stdout == ""


def test_formato_exacto_de_la_salida():
    res = _ejecutar_hook(_entrada("Hay un bug en calcularTotal"))
    assert res.returncode == 0
    assert res.stdout.endswith("\n") and res.stdout.count("\n") == 1
    datos = json.loads(res.stdout)
    assert list(datos.keys()) == ["hookSpecificOutput"]
    assert list(datos["hookSpecificOutput"].keys()) == ["hookEventName", "additionalContext"]
    assert datos["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"


def test_pista_corta_y_nombra_las_herramientas():
    texto = hook_pista.PISTA
    assert len(texto) / 4 <= 40  # caracteres/4 = tokens aproximados
    assert "search_desktop" in texto and "desktop-lancedb" in texto
    assert "get_impact_radius" in texto


@pytest.mark.parametrize("entrada", ["", "   ", "no es json", "[]", "{}", '{"prompt": 5}', '{"prompt": null}'])
def test_entrada_rara_sale_limpio(entrada):
    res = _ejecutar_hook(entrada)
    assert res.returncode == 0
    assert res.stdout == ""


def test_rendimiento_de_la_funcion():
    mensaje = "Revisa el archivo src/app.py y el metodo calcularTotal. " * 40
    inicio = time.perf_counter()
    for _ in range(500):
        hook_pista.procesar(mensaje)
    por_llamada_ms = (time.perf_counter() - inicio) / 500 * 1000
    assert por_llamada_ms < 5


def test_rendimiento_del_proceso_completo():
    inicio = time.perf_counter()
    res = _ejecutar_hook(_entrada("Hay un bug en calcularTotal"))
    duracion = time.perf_counter() - inicio
    assert res.returncode == 0
    assert duracion < 2  # el medido real va en el informe; aqui solo se vigila que no se dispare


def _hook_pista_en(settings: Path) -> int:
    datos = json.loads(settings.read_text(encoding="utf-8"))
    return sum(
        1
        for e in datos.get("hooks", {}).get("UserPromptSubmit", [])
        for h in e.get("hooks", [])
        if "hook_pista.py" in h.get("command", "")
    )


def test_configure_y_uninstall_pista_son_idempotentes_y_reversibles(casa):
    dir_claude = casa / ".claude"
    dir_claude.mkdir(parents=True, exist_ok=True)
    settings = dir_claude / "settings.json"
    claude_md = dir_claude / "CLAUDE.md"

    settings_original = {
        "theme": "dark",
        "hooks": {
            "PreToolUse": [
                {"matcher": "Edit", "hooks": [{"type": "command", "command": "/usr/local/bin/check-lint"}]}
            ]
        },
    }
    settings.write_text(json.dumps(settings_original, indent=2) + "\n", encoding="utf-8")
    md_original = "Mis notas\n\n" + installer.BLOQUE_INSTRUCCIONES
    claude_md.write_text(md_original, encoding="utf-8")

    # 1. Activar: hook agregado una sola vez y bloque SYNRAG quitado del CLAUDE.md (con copias .bak)
    assert installer.configure_pista() == installer.OK
    assert _hook_pista_en(settings) == 1
    datos = json.loads(settings.read_text(encoding="utf-8"))
    assert datos["theme"] == "dark"
    assert datos["hooks"]["PreToolUse"] == settings_original["hooks"]["PreToolUse"]
    assert installer.BLOQUE_INI not in claude_md.read_text(encoding="utf-8")
    assert "Mis notas" in claude_md.read_text(encoding="utf-8")
    assert list(dir_claude.glob("settings.json.bak-*"))
    assert list(dir_claude.glob("CLAUDE.md.bak-*"))

    # 2. Segunda activacion: no duplica el hook
    settings_tras_activar = settings.read_text(encoding="utf-8")
    assert installer.configure_pista() == installer.YA
    assert _hook_pista_en(settings) == 1
    assert settings.read_text(encoding="utf-8") == settings_tras_activar

    # 3. Con la pista activa, un configure completo no vuelve a poner el bloque (ni por GEMINI.md enlazado)
    installer.configure_claude_code()
    assert installer.BLOQUE_INI not in claude_md.read_text(encoding="utf-8")
    dir_gemini = casa / ".gemini"
    dir_gemini.mkdir(parents=True, exist_ok=True)
    os.symlink(claude_md, dir_gemini / "GEMINI.md")
    installer._inyectar_instrucciones(dir_gemini / "GEMINI.md")
    assert installer.BLOQUE_INI not in claude_md.read_text(encoding="utf-8")

    # 4. Desactivar: hook quitado, bloque devuelto y archivos como estaban
    assert installer.uninstall_pista() == installer.OK
    assert json.loads(settings.read_text(encoding="utf-8")) == settings_original
    assert claude_md.read_text(encoding="utf-8") == md_original
    assert installer.uninstall_pista() == installer.YA
    assert json.loads(settings.read_text(encoding="utf-8")) == settings_original


def test_pista_en_instalacion_limpia_no_deja_rastro(casa):
    dir_claude = casa / ".claude"
    dir_claude.mkdir(parents=True, exist_ok=True)
    settings = dir_claude / "settings.json"

    assert installer.configure_pista() == installer.OK
    assert _hook_pista_en(settings) == 1

    assert installer.uninstall_pista() == installer.OK
    assert json.loads(settings.read_text(encoding="utf-8")) == {}
    assert installer.BLOQUE_INI in (dir_claude / "CLAUDE.md").read_text(encoding="utf-8")


def test_cli_configure_y_uninstall_con_pista(casa, monkeypatch):
    import cli

    dir_claude = casa / ".claude"
    dir_claude.mkdir(parents=True, exist_ok=True)
    settings = dir_claude / "settings.json"
    (dir_claude / "CLAUDE.md").write_text("Mis notas\n", encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["SYNRAG", "configure", "--pista"])
    cli.main()
    assert _hook_pista_en(settings) == 1
    assert installer.BLOQUE_INI not in (dir_claude / "CLAUDE.md").read_text(encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["SYNRAG", "uninstall", "--pista"])
    cli.main()
    assert _hook_pista_en(settings) == 0
    assert installer.BLOQUE_INI in (dir_claude / "CLAUDE.md").read_text(encoding="utf-8")


def test_desinstalacion_completa_quita_la_pista(casa):
    dir_claude = casa / ".claude"
    dir_claude.mkdir(parents=True, exist_ok=True)
    settings = dir_claude / "settings.json"
    (dir_claude / "CLAUDE.md").write_text("Mis notas\n", encoding="utf-8")
    installer.configure_pista()
    assert _hook_pista_en(settings) == 1

    installer.run_uninstall()

    assert _hook_pista_en(settings) == 0
    assert installer.BLOQUE_INI not in (dir_claude / "CLAUDE.md").read_text(encoding="utf-8")


def test_la_pista_va_una_sola_vez_por_sesion(casa):
    """Lo que agrega el hook se reenvia en cada turno: repetirla costaria mas que el bloque fijo."""
    import hook_pista
    codigo = "Hay un bug en la funcion calcularTotal de factura.ts"
    assert hook_pista.procesar(codigo, "sesion-1")
    assert hook_pista.procesar(codigo, "sesion-1") == {}
    assert hook_pista.procesar("otro error en main.py", "sesion-1") == {}
    assert hook_pista.procesar(codigo, "sesion-2")  # otra sesion si la recibe
    assert hook_pista.procesar("Hola, buenos dias", "sesion-3") == {}  # la charla no gasta la marca
    assert hook_pista.procesar(codigo, "sesion-3")
    assert hook_pista.procesar(codigo, "../../etc")  # id raro: no se usa como ruta
    assert not (casa / "etc").exists()
