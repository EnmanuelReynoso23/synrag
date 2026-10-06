#!/usr/bin/env python3
"""Mide la latencia de `search_desktop` como la vive una IA: consultas de varias palabras, casi siempre
con filtro de proyecto, y de punta a punta por MCP.

Modos
  --modo mcp    (por defecto) arranca `server_mcp.py` por stdio, igual que lo hace una IA, y mide cada
                llamada a la herramienta `search_desktop`, incluida la primera tras arrancar el servidor.
  --modo motor  llama directamente a `indexer.search_desktop` (sin MCP): lo que cuesta el motor solo.

Consultas: se generan con una semilla fija a partir de TU propio indice. Para cada una se toma un fragmento
al azar y se eligen de 2 a 4 palabras consecutivas suyas (las que de verdad contiene); en 4 de cada 5 se
filtra por el proyecto de ese fragmento. Se parecen a lo que envia una IA y siempre encuentran algo.

Que toca: el modo mcp arranca el servidor con un HOME temporal que enlaza tu indice y el modelo del
reordenado, asi su registro de telemetria queda aparte y no ensucia el tuyo. La cache de consultas se vacia
al empezar (se recrea sola) para que "nueva" y "repetida" signifiquen lo que dicen.

Uso (con el Python del entorno de SynRAG, p. ej. ~/.local/opt/lancedb-hub/.venv/bin/python):
    python benchmarks/latencia.py [--modo mcp|motor] [--consultas 15] [--semilla 42]
                                  [--proyecto NOMBRE] [--palabras 2-4]
"""
import argparse
import asyncio
import os
import random
import re
import shutil
import statistics
import sys
import tempfile
import time
import warnings
from pathlib import Path

MOTOR = Path(__file__).resolve().parent.parent / "engine"
sys.path.insert(0, str(MOTOR))
warnings.filterwarnings("ignore")

try:
    import cache
    import indexer
except ImportError as e:  # pragma: no cover - mensaje de ayuda
    sys.exit(f"No se pudo importar el motor ({e}). Usa el Python del entorno de SynRAG: "
             "~/.local/opt/lancedb-hub/.venv/bin/python benchmarks/latencia.py")

# Palabras de sintaxis que no sirven como consulta
VACIAS = {
    "function", "return", "const", "import", "export", "from", "class", "interface", "string", "number",
    "boolean", "await", "async", "default", "undefined", "null", "true", "false", "this", "self", "while",
    "else", "catch", "throw", "typeof", "public", "private", "static", "extends", "implements", "super",
}
PALABRA = re.compile(r"[A-Za-z_][A-Za-z0-9_]{4,}")


def percentil(valores, p):
    orden = sorted(valores)
    return orden[max(0, min(len(orden) - 1, int(round(p * len(orden) + 0.5)) - 1))]


def resumen(nombre, valores):
    print(f"{nombre:38s} n={len(valores):2d}  mediana {statistics.median(valores):7.1f} ms  "
          f"p90 {percentil(valores, 0.9):7.1f} ms  min {min(valores):7.1f}  max {max(valores):7.1f}")


def generar_consultas(db, cuantas, semilla, solo_proyecto="", palabras_rango=(2, 4)):
    """[(consulta, proyecto_o_vacio)], reproducible con la misma semilla e indice."""
    tabla = db.open_table(indexer.TABLE_NAME)
    datos = tabla.search().select(["project", "content"]).limit(tabla.count_rows()).to_arrow().to_pylist()
    if solo_proyecto:
        datos = [f for f in datos if f["project"] == solo_proyecto]
        if not datos:
            sys.exit(f"El proyecto '{solo_proyecto}' no esta en el indice (mira SYNRAG stats).")
    rng = random.Random(semilla)
    rng.shuffle(datos)
    consultas = []
    for fila in datos:
        palabras = [w for w in dict.fromkeys(PALABRA.findall(fila["content"] or "")) if w.lower() not in VACIAS]
        k = rng.randint(*palabras_rango)
        if len(palabras) < k + 2:
            continue
        i = rng.randrange(0, len(palabras) - k + 1)
        proyecto = fila["project"] if len(consultas) % 5 != 4 else ""
        consultas.append((" ".join(palabras[i:i + k]), proyecto))
        if len(consultas) == cuantas:
            break
    if len(consultas) < cuantas:
        sys.exit("El indice tiene muy poco contenido para medir. Indexa algun proyecto primero (SYNRAG index).")
    return consultas


def medir_motor(consultas):
    def una(q, p):
        t = time.perf_counter()
        indexer.search_desktop(q, limit=5, project=p or None)
        return (time.perf_counter() - t) * 1000
    nuevas = [una(q, p) for q, p in consultas]
    repetidas = [una(q, p) for q, p in consultas]
    return {"arranque": None, "nuevas": nuevas, "repetidas": repetidas}


async def medir_mcp(consultas):
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError as e:  # pragma: no cover
        sys.exit(f"Falta el cliente MCP ({e}). Usa el Python del entorno de SynRAG.")

    real_home = Path.home()
    casa = Path(tempfile.mkdtemp(prefix="synrag-lat-"))
    try:
        # El servidor usa ~/.local/share/lancedb-hub/{data,telemetry.db} y ~/.cache/flashrank:
        # se enlaza lo que hay que leer y la telemetria queda en el HOME temporal.
        (casa / ".local" / "share" / "lancedb-hub").mkdir(parents=True)
        (casa / ".cache").mkdir(parents=True)
        (casa / ".local" / "share" / "lancedb-hub" / "data").symlink_to(indexer.DB_PATH)
        flash = real_home / ".cache" / "flashrank"
        if flash.exists():
            (casa / ".cache" / "flashrank").symlink_to(flash)
        entorno = {**os.environ, "HOME": str(casa), "PYTHONUNBUFFERED": "1"}
        params = StdioServerParameters(command=sys.executable, args=[str(MOTOR / "server_mcp.py")], env=entorno)

        t0 = time.perf_counter()
        async with stdio_client(params) as (leer, escribir):
            async with ClientSession(leer, escribir) as sesion:
                await sesion.initialize()
                arranque = (time.perf_counter() - t0) * 1000

                async def una(q, p):
                    t = time.perf_counter()
                    await sesion.call_tool("search_desktop", {"query": q, "limit": 5, "project": p})
                    return (time.perf_counter() - t) * 1000

                nuevas = [await una(q, p) for q, p in consultas]
                repetidas = [await una(q, p) for q, p in consultas]
        return {"arranque": arranque, "nuevas": nuevas, "repetidas": repetidas}
    finally:
        shutil.rmtree(casa, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--modo", choices=("mcp", "motor"), default="mcp")
    ap.add_argument("--consultas", type=int, default=15)
    ap.add_argument("--semilla", type=int, default=42)
    ap.add_argument("--proyecto", default="", help="mide solo consultas dentro de ese proyecto (p. ej. el mas grande)")
    ap.add_argument("--palabras", default="2-4", help="rango de palabras por consulta, p. ej. 2-4 o 3-8")
    a = ap.parse_args()

    db = indexer.get_db()
    if indexer.TABLE_NAME not in db.table_names():
        sys.exit("Aun no hay indice. Ejecuta: SYNRAG index")
    lo, hi = (int(x) for x in a.palabras.split("-"))
    consultas = generar_consultas(db, a.consultas, a.semilla, a.proyecto, (lo, hi))
    try:
        cache.clear_cache(db)
    except Exception:
        pass

    r = medir_motor(consultas) if a.modo == "motor" else asyncio.run(medir_mcp(consultas))
    con_filtro = sum(1 for _, p in consultas if p)
    print(f"Modo {a.modo} | semilla {a.semilla} | {len(consultas)} consultas ({con_filtro} con filtro de proyecto) "
          f"| ejemplo: \"{consultas[0][0]}\"")
    if r["arranque"] is not None:
        print(f"Arranque del servidor MCP (hasta initialize): {r['arranque']:.0f} ms")
    print(f"Primera consulta (en frio):            {r['nuevas'][0]:.1f} ms")
    resumen("Consultas nuevas, en caliente", r["nuevas"][1:])
    resumen("Mismas consultas (cache)", r["repetidas"])


if __name__ == "__main__":
    main()
