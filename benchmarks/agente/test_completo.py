"""
Pruebas offline para benchmarks/agente/completo.py (sin llamadas a Gemini ni a red).
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE / "engine"))
sys.path.insert(0, str(BASE / "benchmarks" / "agente"))

import completo  # noqa: E402

ENTORNO_GIT = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t.t",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t.t")


def _git(cwd, *args):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True, env=ENTORNO_GIT)
    return r.stdout.strip()


def test_clonar_synrag_deja_el_commit_fijo(tmp_path):
    origen = tmp_path / "origen"
    origen.mkdir()
    _git(origen, "init", "-q")
    (origen / "f.txt").write_text("version 1\n", encoding="utf-8")
    _git(origen, "add", "f.txt")
    _git(origen, "commit", "-q", "-m", "primera")
    fijo = _git(origen, "rev-parse", "HEAD")
    (origen / "f.txt").write_text("version 2\n", encoding="utf-8")
    _git(origen, "add", "f.txt")
    _git(origen, "commit", "-q", "-m", "segunda")

    destino = tmp_path / "clon"
    completo.clonar_synrag(origen, destino, fijo)

    assert _git(destino, "rev-parse", "HEAD") == fijo
    assert (destino / "f.txt").read_text(encoding="utf-8") == "version 1\n"


def test_clonar_synrag_rechaza_commit_inexistente(tmp_path):
    origen = tmp_path / "origen"
    origen.mkdir()
    _git(origen, "init", "-q")
    (origen / "f.txt").write_text("x\n", encoding="utf-8")
    _git(origen, "add", "f.txt")
    _git(origen, "commit", "-q", "-m", "unica")

    with pytest.raises(ValueError, match="no existe"):
        completo.clonar_synrag(origen, tmp_path / "clon", "0123456789abcdef0123456789abcdef01234567")


PARES = [(100, 50), (200, 150), (100, 90), (300, 120)]


def test_bootstrap_contiene_el_punto_y_es_determinista():
    punto = 100 * (sum(c for _, c in PARES) - sum(s for s, _ in PARES)) / sum(s for s, _ in PARES)
    bajo, alto = completo.ic_bootstrap_ahorro(PARES)
    assert bajo <= punto <= alto
    assert (bajo, alto) == completo.ic_bootstrap_ahorro(PARES)


def test_bootstrap_tareas_identicas_da_intervalo_degenerado():
    bajo, alto = completo.ic_bootstrap_ahorro([(100, 50)] * 5)
    assert bajo == pytest.approx(-50.0)
    assert alto == pytest.approx(-50.0)


def test_bootstrap_sin_tareas_falla():
    with pytest.raises(ValueError):
        completo.ic_bootstrap_ahorro([])


def test_cache_se_registra_por_fila(tmp_path, monkeypatch):
    (tmp_path / "nota.txt").write_text("uno\ndos\n", encoding="utf-8")
    respuestas = [
        {"candidates": [{"content": {"role": "model", "parts": [
            {"functionCall": {"name": "read_file", "args": {"ruta": "nota.txt", "desde": 1, "hasta": 2}}}]}}],
         "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 10,
                           "thoughtsTokenCount": 5, "cachedContentTokenCount": 80}},
        {"candidates": [{"content": {"role": "model", "parts": [{"text": "respuesta final"}]}}],
         "usageMetadata": {"promptTokenCount": 150, "candidatesTokenCount": 20,
                           "cachedContentTokenCount": 120}},
    ]
    llamadas = []

    def falso_gemini(modelo, cuerpo, clave):
        llamadas.append(cuerpo)
        return respuestas[len(llamadas) - 1]

    monkeypatch.setattr(completo, "llamar_gemini", falso_gemini)
    tarea = {"id": "t", "repo": "flask", "tipo": "conversacion corta", "pregunta": "hola", "hechos": ["final"]}
    fila = completo.ejecutar(tarea, "con", {"flask": tmp_path}, "modelo", "clave", "", pausa=0)

    assert fila["turnos"] == 2
    assert fila["cache"] == 200
    assert fila["prompt"] == 250
    assert fila["total"] == 250 + 30 + 5
    assert fila["calidad"] == 1.0


def test_tareas_nuevas_tienen_formato_correcto():
    ids = [t["id"] for t in completo.TAREAS]
    assert len(ids) == len(set(ids)) == 18
    assert sum(t["tipo"] == "conversacion corta" for t in completo.TAREAS) == 4
    for t in completo.TAREAS:
        assert t["repo"] in {"synrag", "flask", "hono"}
        assert t["hechos"]
