import sys
from pathlib import Path

import pytest

import conciso
import installer
import server_mcp

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "benchmarks"))
import costo_fijo  # noqa: E402


def test_bloque_conciso_conserva_reglas_credito_y_marcadores():
    bloque = conciso.BLOQUE_CONCISO_INSTRUCCIONES
    assert bloque.startswith(conciso.BLOQUE_CONCISO_INI)
    assert bloque.rstrip("\n").endswith(conciso.BLOQUE_CONCISO_FIN)
    assert "Julius Brussee, Apache-2.0" in bloque
    vinetas = [linea for linea in bloque.splitlines() if linea.startswith("- ")]
    assert len(vinetas) == 6
    assert "Cero emojis" in bloque
    assert "completos y literales" in bloque
    assert "Preguntas y avisos" in bloque
    # Presupuesto: <= 100 tokens. Sin clave no se cuenta exacto; caracteres / 4 es solo una guarda.
    assert costo_fijo.estimar(bloque) <= 100


def test_bloque_instrucciones_conserva_las_pautas_clave():
    bloque = installer.BLOQUE_INSTRUCCIONES
    for termino in ("search_desktop", "project", "get_file_outline", "get_impact_radius", "dilo y sigue"):
        assert termino in bloque
    assert installer.BLOQUE_INI in bloque and installer.BLOQUE_FIN in bloque
    assert costo_fijo.estimar(bloque) <= 112  # 60 % de los 188 tokens medidos antes del recorte


def test_docstrings_de_las_esenciales_conservan_lo_necesario():
    assert server_mcp.ESENCIALES == {"search_desktop", "get_file_outline", "get_impact_radius",
                                     "repo_map", "run_test_isolated"}
    sd = server_mcp.search_desktop.__doc__
    assert "project" in sd and "detalle" in sd and "tipo" in sd and "definicion" in sd
    assert "archivo=" in server_mcp.get_impact_radius.__doc__
    assert "tokens" in server_mcp.repo_map.__doc__


def test_a_gemini_pasa_tipos_a_mayusculas_y_quita_claves_ajenas():
    esquema = {"type": "object", "title": "X", "properties": {"n": {"type": "integer", "default": 3}}}
    limpio = costo_fijo._a_gemini(esquema)
    assert limpio == {"type": "OBJECT", "properties": {"n": {"type": "INTEGER"}}}


def test_declaraciones_omiten_parametros_si_no_hay_propiedades():
    tools = [
        {"name": "lista", "description": "d", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "busca", "description": "e", "inputSchema": {"type": "object",
                                                              "properties": {"q": {"type": "string"}}}},
    ]
    decls = costo_fijo.declaraciones_desde_mcp(tools)
    assert "parameters" not in decls[0]
    assert decls[1]["parameters"]["properties"]["q"] == {"type": "STRING"}


def test_completo_se_lee_sin_importarlo():
    datos = costo_fijo._leer_constante_completo(RAIZ / "benchmarks" / "agente" / "completo.py")
    nombres = {d["name"] for d in datos["TOOLS_SYNRAG"]}
    assert nombres == {"search_desktop", "get_file_outline", "repo_map"}
    assert "search_desktop" in datos["EXTRA_CON"]


def test_costo_fijo_sin_api_imprime_tabla(casa, monkeypatch, capsys):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    codigo = costo_fijo.main(["--sin-api"])
    salida = capsys.readouterr().out
    assert codigo == 0
    assert "perfil completo" in salida and "perfil esencial" in salida
    assert "installer.BLOQUE_INSTRUCCIONES" in salida
    assert "conciso.BLOQUE_CONCISO_INSTRUCCIONES" in salida
    assert "caracteres/4 (aprox.)" in salida
