"""
Pruebas unitarias para el coprocesador de IA (engine/argon.py).
Verifica la obtención de API key, la llamada con fallback transparente y el formateo de respuestas.
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import argon


def test_sin_clave_no_hay_herramientas_ni_red(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(argon.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(argon, "__file__", str(tmp_path / "engine" / "argon.py"))
    assert argon.get_api_key() == ""
    assert argon.disponible() is False
    assert argon.call_gemini_model("hola")["success"] is False


def test_clave_por_variable_de_entorno(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "  clave-de-prueba  ")
    assert argon.get_api_key() == "clave-de-prueba"


@pytest.mark.skipif(not argon.get_api_key(), reason="Sin GEMINI_API_KEY: prueba con red opcional")
def test_call_gemini_model_execution():
    # Verifica que la llamada responda con éxito utilizando fallback si Argon tiene cuota 0 en Free Tier
    res = argon.call_gemini_model("Di exactamente la palabra: TEST_PASSED")
    if not res.get("success") and ("429" in str(res.get("error")) or "503" in str(res.get("error")) or "timed out" in str(res.get("error")).lower() or "timeout" in str(res.get("error")).lower()):
        pytest.skip("API externa de Google temporalmente saturada, cuota excedida o timeout")
    assert res.get("success") is True
    assert "TEST_PASSED" in res.get("text")
    assert res.get("model") in argon.modelos()


def test_explain_blast_radius_empty():
    res = argon.explain_blast_radius("simbolo_inexistente_xyz_12345")
    assert "no tiene dependientes" in res


def test_explain_blast_radius_usa_los_dependientes_de_una_definicion(casa, monkeypatch):
    from conftest import crear_proyecto
    crear_proyecto(casa, "mono", {
        "web/hooks/useAuth.ts": "export function useAuth() {\n  return 1\n}\n",
        "web/Home.tsx": "import { useAuth } from './hooks/useAuth'\nexport const Home = () => useAuth()\n",
        "auth/useAuth.ts": "export function useAuth() {\n  return 2\n}\n",
        "auth/Panel.tsx": "import { useAuth } from './useAuth'\nexport const Panel = () => useAuth()\n",
    })
    import indexer
    indexer._RESOLUTORES.clear()
    indexer.index_desktop()
    prompts = []
    monkeypatch.setattr(argon, "call_gemini_model", lambda p: prompts.append(p) or {"success": True, "text": "ok", "model": "x"})
    argon.explain_blast_radius("useAuth", "mono", archivo="auth/useAuth.ts")
    assert "auth/Panel.tsx" in prompts[0] and "Home.tsx" not in prompts[0]
    assert "DEFINIDO EN:" in prompts[0] and "auth/useAuth.ts" in prompts[0]
