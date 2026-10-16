#!/usr/bin/env python3
"""Ahorro COMPLETO del sistema: un agente real hace tareas de varios pasos con y sin SynRAG.

Se cuentan TODOS los tokens que cobra la API en cada turno (usageMetadata: prompt + respuesta +
razonamiento), es decir: las definiciones de las herramientas, el historial que se reenvia en cada
turno, las salidas de las herramientas y lo que escribe el modelo.

  - "sin": grep, read_file y run (terminal) con la salida en crudo (cortada a 30.000 caracteres,
           como hace Claude Code).
  - "con": lo mismo MAS search_desktop, get_file_outline y repo_map; la salida de run pasa por el
           filtro de salidas largas de SynRAG; y el prompt de sistema lleva el modo conciso.

Las tareas mezclan lo que hace un agente de verdad: localizar, entender (necesita el cuerpo),
planear un cambio (llamadas afectadas) y correr pruebas (salidas largas). Cada tarea tiene una lista
de hechos que la respuesta debe contener; se puntua automaticamente.

La clave se lee de GEMINI_API_KEY (o de engine/argon.py get_api_key) y nunca se imprime ni se guarda.

Uso:
  git clone --depth 1 https://github.com/pallets/flask /tmp/flask
  git clone --depth 1 https://github.com/honojs/hono  /tmp/hono
  GEMINI_API_KEY=... python benchmarks/agente/completo.py --flask /tmp/flask --hono /tmp/hono [--rondas 2]
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
sys.path.insert(0, str(RAIZ / "engine"))
sys.path.insert(0, str(AQUI))

import telemetry  # noqa: E402
telemetry.record_search_event = lambda *a, **k: None
import argon  # noqa: E402
import conciso  # noqa: E402
import filtro  # noqa: E402
import indexer  # noqa: E402
import server_mcp  # noqa: E402
from agente import ejecutar_grep, ejecutar_read_file, llamar_gemini  # noqa: E402

LIMITE_CLAUDE_CODE = 30000
PROHIBIDO = re.compile(r"\b(rm|sudo|curl|wget|ssh|scp|dd|mkfs|shutdown|reboot)\b|git\s+push|>\s*/")

TAREAS: List[Dict[str, Any]] = [
    {"id": "synrag_pruebas_filtro", "repo": "synrag", "tipo": "correr pruebas",
     "pregunta": "Corre las pruebas de engine/tests/test_filtro.py con pytest (desde la carpeta engine) y dime cuantas pasan y si alguna falla.",
     "hechos": ["18", "pas|passed"]},
    {"id": "synrag_suite_v", "repo": "synrag", "tipo": "correr pruebas (salida larga)",
     "pregunta": "Corre la suite completa del motor en modo detallado: `cd engine && python -m pytest -v`. Dime cuantas pruebas pasan, cuantas fallan y cual es la que se marca como xfail.",
     "hechos": ["181", "xfail", "test_"]},
    {"id": "synrag_orden_busqueda", "repo": "synrag", "tipo": "entender",
     "pregunta": "Explica como decide search_desktop (engine/indexer.py) el orden de los resultados cuando la consulta es un nombre de simbolo exacto.",
     "hechos": ["buscar_definiciones", "exact|exacto", "PRIORIDAD_KIND|function|funcion", "export"]},
    {"id": "synrag_observador", "repo": "synrag", "tipo": "entender",
     "pregunta": "En engine/watcher.py: ¿que hace el observador para no crear una version de tabla por cada guardado, cada cuantas actualizaciones compacta y cuantos minutos conserva las versiones viejas?",
     "hechos": ["optimiz", "50", "5"]},
    {"id": "synrag_cambio_firma", "repo": "synrag", "tipo": "planear cambio",
     "pregunta": "Quiero agregar un parametro obligatorio `idioma` a la funcion terminos_de_busqueda. ¿Que llamadas habria que cambiar? Dame archivo y funcion de cada una.",
     "hechos": ["_con_terminos", "indexer.py"]},
    {"id": "flask_from_envvar", "repo": "flask", "tipo": "entender",
     "pregunta": "¿Como carga Flask la configuracion desde una variable de entorno que apunta a un archivo? Nombra el metodo y di que pasa si la variable no existe.",
     "hechos": ["from_envvar", "silent", "RuntimeError"]},
    {"id": "flask_firma_sesion", "repo": "flask", "tipo": "entender",
     "pregunta": "¿Donde y como se firma la cookie de sesion en Flask? Nombra el metodo, la clase del serializador y de donde sale la clave.",
     "hechos": ["get_signing_serializer", "URLSafeTimedSerializer", "secret_key"]},
    {"id": "flask_metodos_config", "repo": "flask", "tipo": "orientarse",
     "pregunta": "Lista todos los metodos publicos de la clase Config de Flask que sirven para cargar configuracion.",
     "hechos": ["from_envvar", "from_pyfile", "from_object", "from_file", "from_mapping", "from_prefixed_env"]},
    {"id": "hono_compose", "repo": "hono", "tipo": "localizar y entender",
     "pregunta": "¿Como compone Hono los middlewares? Nombra la funcion, el archivo y explica en dos frases como avanza de un middleware al siguiente.",
     "hechos": ["compose", "compose.ts", "next"]},
    {"id": "hono_c_json", "repo": "hono", "tipo": "entender",
     "pregunta": "¿Que hace el metodo json del contexto de Hono (c.json)? Di el archivo y que cabecera pone.",
     "hechos": ["context.ts", "application/json"]},
]

BASE = ("Eres un asistente de programacion trabajando en el repositorio '{repo}' (la raiz del repositorio es el "
        "directorio actual de las herramientas). Investiga con las herramientas; no inventes. Cuando tengas la "
        "respuesta, contestala directamente sin llamar mas herramientas.")
EXTRA_CON = ("\nPara localizar codigo usa primero search_desktop (con un nombre de simbolo devuelve la definicion "
             "entera), get_file_outline para ver la estructura de un archivo y repo_map para orientarte en el "
             "proyecto; usa grep o read_file solo si eso no basta.\n")


def _decl(nombre, desc, props, req):
    return {"name": nombre, "description": desc,
            "parameters": {"type": "OBJECT", "properties": props, "required": req}}


S = {"type": "STRING"}
I = {"type": "INTEGER"}
TOOLS_BASE = [
    _decl("grep", "Busca un patron (regex) en los archivos del repositorio con git grep; devuelve ruta:linea:texto.", {"patron": S}, ["patron"]),
    _decl("read_file", "Lee un tramo de un archivo (lineas desde-hasta, maximo 120).", {"ruta": S, "desde": I, "hasta": I}, ["ruta"]),
    _decl("run", "Ejecuta un comando de terminal en la raiz del repositorio y devuelve su salida.", {"comando": S}, ["comando"]),
]
TOOLS_SYNRAG = [
    _decl("search_desktop", "Localiza codigo por palabras o por nombre de simbolo (definicion exacta primero y entera); tipo='docs' o 'codigo' filtra.", {"consulta": S, "tipo": S}, ["consulta"]),
    _decl("get_file_outline", "Esquema de un archivo: simbolos con sus lineas y metodos de clases grandes, sin el codigo.", {"ruta": S}, ["ruta"]),
    _decl("repo_map", "Firmas de los archivos mas importantes del proyecto (PageRank) dentro de un presupuesto de tokens.", {"foco": S, "tokens": I}, []),
]


def ejecutar_run(repo_dir: Path, comando: str, con_filtro: bool, venv_bin: str) -> str:
    if PROHIBIDO.search(comando):
        return "Error: comando no permitido en esta prueba."
    env = dict(os.environ, PATH=f"{venv_bin}:{os.environ.get('PATH', '')}")
    env.pop("GEMINI_API_KEY", None)  # los comandos del agente no ven la clave
    try:
        r = subprocess.run(["bash", "-c", comando], cwd=repo_dir, capture_output=True, text=True, timeout=240, env=env)
        salida = (r.stdout or "") + (r.stderr or "")
        salida = salida[:LIMITE_CLAUDE_CODE] + (f"\n(codigo de salida {r.returncode})" if r.returncode else "")
    except subprocess.TimeoutExpired:
        return "Error: el comando supero el tiempo limite."
    return filtro.filtrar_salida_larga(salida) if con_filtro else salida


def puntuar(texto: str, hechos: List[str]) -> float:
    t = texto.lower()
    return sum(any(alt.lower() in t for alt in h.split("|")) for h in hechos) / len(hechos)


def ejecutar(tarea, modo, repos, modelo, clave, venv_bin, max_turnos=15, pausa=0.4) -> Dict[str, Any]:
    con = modo == "con"
    repo_dir = repos[tarea["repo"]]
    sistema = BASE.format(repo=tarea["repo"])
    if con:
        bloque = conciso.BLOQUE_CONCISO_INSTRUCCIONES.replace(conciso.BLOQUE_CONCISO_INI, "").replace(conciso.BLOQUE_CONCISO_FIN, "")
        sistema += EXTRA_CON + bloque
    tools = [{"functionDeclarations": TOOLS_BASE + (TOOLS_SYNRAG if con else [])}]
    contents: List[Dict[str, Any]] = [{"role": "user", "parts": [{"text": tarea["pregunta"]}]}]
    tok = {"prompt": 0, "salida": 0, "razonamiento": 0}
    llamadas: List[str] = []
    final, turnos = "", 0
    for _ in range(max_turnos):
        res = llamar_gemini(modelo, {"system_instruction": {"parts": [{"text": sistema}]}, "contents": contents,
                                     "tools": tools, "generationConfig": {"temperature": 0.0}}, clave)
        turnos += 1
        u = res.get("usageMetadata", {})
        tok["prompt"] += u.get("promptTokenCount", 0)
        tok["salida"] += u.get("candidatesTokenCount", 0)
        tok["razonamiento"] += u.get("thoughtsTokenCount", 0)
        cand = (res.get("candidates") or [{}])[0].get("content") or {"role": "model", "parts": []}
        cand.setdefault("role", "model")
        contents.append(cand)
        partes = cand.get("parts", [])
        fcs = [p["functionCall"] for p in partes if "functionCall" in p]
        textos = "".join(p.get("text", "") for p in partes if "text" in p)
        if not fcs:
            final = textos
            break
        respuestas = []
        for fc in fcs:
            n, a = fc.get("name", ""), fc.get("args", {}) or {}
            llamadas.append(n)
            if n == "grep":
                out = ejecutar_grep(repo_dir, str(a.get("patron", "")))
            elif n == "read_file":
                out = ejecutar_read_file(repo_dir, str(a.get("ruta", "")), int(a.get("desde", 1) or 1), int(a.get("hasta", 80) or 80))
            elif n == "run":
                out = ejecutar_run(repo_dir, str(a.get("comando", "")), con, venv_bin)
            elif con and n == "search_desktop":
                out = server_mcp.search_desktop(str(a.get("consulta", "")), limit=5, project=tarea["repo"], tipo=str(a.get("tipo", "") or ""))
            elif con and n == "get_file_outline":
                out = server_mcp.get_file_outline(str(a.get("ruta", "")), project=tarea["repo"])
            elif con and n == "repo_map":
                out = server_mcp.repo_map(tarea["repo"], foco=str(a.get("foco", "") or ""), tokens=int(a.get("tokens", 800) or 800))
            else:
                out = f"Error: herramienta '{n}' no disponible."
            r = {"functionResponse": {"name": n, "response": {"output": out}}}
            if fc.get("id"):
                r["functionResponse"]["id"] = fc["id"]
            respuestas.append(r)
        contents.append({"role": "user", "parts": respuestas})
        time.sleep(pausa)
    total = tok["prompt"] + tok["salida"] + tok["razonamiento"]
    return {"tarea": tarea["id"], "tipo": tarea["tipo"], "modo": modo, "turnos": turnos, **tok, "total": total,
            "calidad": puntuar(final, tarea["hechos"]), "llamadas": llamadas, "respuesta": final[:1500]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--flask", required=True, type=Path)
    ap.add_argument("--hono", required=True, type=Path)
    ap.add_argument("--rondas", type=int, default=2)
    ap.add_argument("--modelo", default="gemini-3.5-flash-lite")
    ap.add_argument("--solo", default="", help="ids de tareas separados por coma")
    ap.add_argument("--progreso", type=Path, help="JSONL donde se guarda cada ejecucion; al relanzar se salta lo ya hecho")
    a = ap.parse_args()
    clave = os.environ.get("GEMINI_API_KEY") or argon.get_api_key()
    if not clave:
        sys.exit("Falta GEMINI_API_KEY.")

    tmp = Path(tempfile.mkdtemp(prefix="synrag-completo-"))
    synrag = tmp / "synrag"
    subprocess.run(["git", "clone", "-q", "--local", "--no-hardlinks", str(RAIZ), str(synrag)], check=True)
    repos = {"synrag": synrag, "flask": a.flask.resolve(), "hono": a.hono.resolve()}
    indexer.DB_PATH = tmp / "indice"
    os.environ["SYNRAG_CARPETAS"] = os.pathsep.join(f"{p}={n}" for n, p in repos.items())
    indexer.index_desktop()
    venv_bin = str(Path(sys.executable).parent)

    tareas = [t for t in TAREAS if not a.solo or t["id"] in a.solo.split(",")]
    filas = []
    if a.progreso and a.progreso.exists():
        filas = [f for f in map(json.loads, a.progreso.read_text().splitlines()) if f.get("modelo") == a.modelo]
        print(f"[progreso] {len(filas)} ejecuciones ya hechas en {a.progreso}", flush=True)
    hechas = {(f["ronda"], f["tarea"], f["modo"]) for f in filas}
    for ronda in range(1, a.rondas + 1):
        for t in tareas:
            for modo in ("sin", "con"):
                if (ronda, t["id"], modo) in hechas:
                    continue
                r = ejecutar(t, modo, repos, a.modelo, clave, venv_bin)
                r["ronda"] = ronda
                r["modelo"] = a.modelo
                filas.append(r)
                if a.progreso:
                    with a.progreso.open("a") as fp:
                        fp.write(json.dumps(r, ensure_ascii=False) + "\n")
                print(f"r{ronda} {t['id']:<24} {modo:<3} total {r['total']:>7}  turnos {r['turnos']:>2}  calidad {r['calidad']:.0%}  {','.join(r['llamadas'])[:70]}", flush=True)

    print("\n== Resumen por tarea (media de las rondas)")
    tot = {"sin": 0, "con": 0}; cal = {"sin": [], "con": []}
    for t in tareas:
        m = {}
        for modo in ("sin", "con"):
            fs = [f for f in filas if f["tarea"] == t["id"] and f["modo"] == modo]
            m[modo] = sum(f["total"] for f in fs) / len(fs)
            tot[modo] += sum(f["total"] for f in fs)
            cal[modo] += [f["calidad"] for f in fs]
        print(f"  {t['id']:<24} {t['tipo']:<30} sin {m['sin']:>8.0f}  con {m['con']:>8.0f}  {100 * (m['con'] - m['sin']) / m['sin']:+.0f} %")
    ahorro = 100 * (tot["con"] - tot["sin"]) / tot["sin"]
    print(f"\n== TOTAL: sin {tot['sin']}  con {tot['con']}  -> {ahorro:+.1f} %")
    print(f"   calidad media: sin {sum(cal['sin']) / len(cal['sin']):.0%}  con {sum(cal['con']) / len(cal['con']):.0%}")
    salida = AQUI / f"completo-resultados-{datetime.date.today()}.json"
    salida.write_text(json.dumps({"modelo": a.modelo, "rondas": a.rondas, "filas": filas,
                                  "total_sin": tot["sin"], "total_con": tot["con"], "ahorro_pct": ahorro}, ensure_ascii=False, indent=1))
    print(f"   resultados: {salida}")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
