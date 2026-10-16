"""Perfil bajo_demanda: el servidor arranca con 2 herramientas, synrag_mas activa el resto y avisa con
notifications/tools/list_changed. La prueba habla con el servidor real por stdio, con HOME temporal."""
import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

RAIZ_ENGINE = Path(__file__).resolve().parents[1]
NOTIFICACION = "notifications/tools/list_changed"


def _entorno(casa: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in ("GEMINI_API_KEY", "SYNRAG_PERFIL")}
    env.update({
        "HOME": str(casa),
        "XDG_CONFIG_HOME": str(casa / ".config"),
        "XDG_CACHE_HOME": str(casa / ".cache"),
        "XDG_STATE_HOME": str(casa / ".state"),
        "SYNRAG_DB_PATH": str(casa / "db"),
        "SYNRAG_PERFIL": "bajo_demanda",
    })
    return env


async def _sesion(casa: Path):
    notificaciones = []

    async def al_recibir(msg):
        if isinstance(msg, Exception):
            return
        metodo = getattr(getattr(msg, "root", msg), "method", "")
        if metodo:
            notificaciones.append(metodo)

    params = StdioServerParameters(
        command=sys.executable, args=[str(RAIZ_ENGINE / "server_mcp.py")], env=_entorno(casa)
    )
    async with stdio_client(params) as (lectura, escritura):
        async with ClientSession(lectura, escritura, message_handler=al_recibir) as sesion:
            init = await sesion.initialize()
            inicial = [t.name for t in (await sesion.list_tools()).tools]
            primera = await sesion.call_tool("synrag_mas", {})
            for _ in range(100):
                if NOTIFICACION in notificaciones:
                    break
                await asyncio.sleep(0.05)
            tras_primera = [t.name for t in (await sesion.list_tools()).tools]
            segunda = await sesion.call_tool("synrag_mas", {})
            await asyncio.sleep(0.3)
            tras_segunda = [t.name for t in (await sesion.list_tools()).tools]
    return {
        "list_changed": init.capabilities.tools.list_changed if init.capabilities.tools else None,
        "inicial": inicial,
        "primera": primera,
        "tras_primera": tras_primera,
        "segunda": segunda,
        "tras_segunda": tras_segunda,
        "notificaciones": notificaciones,
    }


def test_bajo_demanda_punta_a_punta_por_stdio(casa):
    r = asyncio.run(asyncio.wait_for(_sesion(casa), timeout=240))

    assert r["list_changed"] is True
    assert len(r["inicial"]) == 2
    assert set(r["inicial"]) == {"search_desktop", "synrag_mas"}

    assert not r["primera"].is_error
    assert "Activadas" in r["primera"].content[0].text
    assert r["notificaciones"].count(NOTIFICACION) == 1
    assert len(r["tras_primera"]) >= 26
    assert "synrag_mas" in r["tras_primera"]

    # llamarla otra vez no duplica nada ni vuelve a avisar
    assert "Ya estaban activas" in r["segunda"].content[0].text
    assert r["notificaciones"].count(NOTIFICACION) == 1
    assert len(r["tras_segunda"]) == len(r["tras_primera"])
    assert len(set(r["tras_segunda"])) == len(r["tras_segunda"])


def test_configure_acepta_bajo_demanda(casa):
    import importlib
    import installer
    importlib.reload(installer)
    import indexer
    assert installer.configure_perfil("bajo_demanda") == installer.OK
    assert indexer.perfil_herramientas() == "bajo_demanda"
    assert installer.configure_perfil("otro") == installer.ERROR


async def _nombres_del_perfil(casa: Path, perfil: str) -> list:
    env = _entorno(casa)
    env["SYNRAG_PERFIL"] = perfil
    params = StdioServerParameters(
        command=sys.executable, args=[str(RAIZ_ENGINE / "server_mcp.py")], env=env
    )
    async with stdio_client(params) as (lectura, escritura):
        async with ClientSession(lectura, escritura) as sesion:
            await sesion.initialize()
            return [t.name for t in (await sesion.list_tools()).tools]


def test_bajo_demanda_activa_lo_mismo_que_completo(casa):
    completo = asyncio.run(asyncio.wait_for(_nombres_del_perfil(casa, "completo"), timeout=240))
    casa_bajo = casa / "bajo"
    casa_bajo.mkdir()
    r = asyncio.run(asyncio.wait_for(_sesion(casa_bajo), timeout=240))
    assert set(r["tras_primera"]) == set(completo) | {"synrag_mas"}
    assert len(completo) >= 26
