"""
Pruebas unitarias para benchmarks/agente/agente.py (sin llamadas a red).
"""

import json
from pathlib import Path
import pytest
import sys

BASE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE / "engine"))
sys.path.insert(0, str(BASE / "benchmarks" / "agente"))

import agente


def test_verificar_acierto_positivo():
    q = {
        "archivo": "src/flask/ctx.py",
        "simbolo": "copy_current_request_context"
    }
    texto = "La funcion copy_current_request_context esta en src/flask/ctx.py linea 154."
    assert agente.verificar_acierto(texto, q) is True


def test_verificar_acierto_solo_nombre_archivo():
    q = {
        "archivo": "src/flask/ctx.py",
        "simbolo": "copy_current_request_context"
    }
    texto = "Se define dentro de ctx.py bajo copy_current_request_context."
    assert agente.verificar_acierto(texto, q) is True


def test_verificar_acierto_simbolo_incorrecto():
    q = {
        "archivo": "src/flask/ctx.py",
        "simbolo": "copy_current_request_context"
    }
    texto = "Se define en ctx.py bajo after_this_request."
    assert agente.verificar_acierto(texto, q) is False


def test_verificar_acierto_archivo_incorrecto():
    q = {
        "archivo": "src/flask/ctx.py",
        "simbolo": "copy_current_request_context"
    }
    texto = "Se define en app.py bajo copy_current_request_context."
    assert agente.verificar_acierto(texto, q) is False


def test_prompts_difieren_en_una_sola_linea():
    lineas_sin = agente.SYSTEM_PROMPT_SIN.strip().splitlines()
    lineas_con = agente.SYSTEM_PROMPT_CON.strip().splitlines()
    assert len(lineas_con) == len(lineas_sin) + 1
    # La linea extra es la que menciona search_desktop
    assert any("search_desktop" in l for l in lineas_con)
    assert not any("search_desktop" in l for l in lineas_sin)


def test_declaracion_de_herramientas():
    nombres_sin = [f["name"] for f in agente.TOOLS_SIN[0]["function_declarations"]]
    nombres_con = [f["name"] for f in agente.TOOLS_CON[0]["function_declarations"]]
    assert set(nombres_sin) == {"grep", "read_file"}
    assert set(nombres_con) == {"grep", "read_file", "search_desktop"}


def test_ejecutar_read_file(tmp_path):
    f = tmp_path / "prueba.py"
    f.write_text("linea 1\nlinea 2\nlinea 3\nlinea 4\nlinea 5\n", encoding="utf-8")
    salida = agente.ejecutar_read_file(tmp_path, "prueba.py", desde=2, hasta=4)
    lineas = salida.splitlines()
    assert len(lineas) == 3
    assert lineas[0] == "2\tlinea 2"
    assert lineas[2] == "4\tlinea 4"


def test_ejecutar_read_file_fuera_de_repo(tmp_path):
    salida = agente.ejecutar_read_file(tmp_path, "../../etc/passwd")
    assert "Error: ruta fuera del repositorio" in salida


def test_generar_tabla_resumen():
    preguntas = [
        {"id": "p1", "repo": "flask", "tipo": "simbolo", "archivo": "a.py", "simbolo": "f1"},
        {"id": "p2", "repo": "flask", "tipo": "natural", "archivo": "b.py", "simbolo": "f2"}
    ]
    ejecuciones = [
        {"pregunta_id": "p1", "modo": "con", "tokens_total": 500, "tokens_entrada": 400, "tokens_salida": 100, "turnos": 2, "acerto": True},
        {"pregunta_id": "p1", "modo": "sin", "tokens_total": 800, "tokens_entrada": 650, "tokens_salida": 150, "turnos": 3, "acerto": True},
        {"pregunta_id": "p2", "modo": "con", "tokens_total": 700, "tokens_entrada": 600, "tokens_salida": 100, "turnos": 3, "acerto": True},
        {"pregunta_id": "p2", "modo": "sin", "tokens_total": 600, "tokens_entrada": 500, "tokens_salida": 100, "turnos": 2, "acerto": True},
    ]
    tabla = agente.generar_tabla_resumen(ejecuciones, preguntas)
    assert "SynRAG" in tabla
    assert "p1" in tabla
    assert "p2" in tabla
