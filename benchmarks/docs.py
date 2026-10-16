#!/usr/bin/env python3
"""Comparativa de tokens para documentación: SynRAG (tipo="docs") vs alternativas.

Compara tres caminos para responder preguntas sobre la documentación:
  1. archivo:  grep para localizar el archivo y lectura del archivo de documentación entero.
  2. grep:     grep de la palabra clave (primeras 30 líneas) + leer 40 líneas del tramo relevante.
  3. synrag:   search_desktop(..., tipo="docs") tal como lo recibe el modelo; si la respuesta
               está en el primer resultado ya incluye el cuerpo; si está entre el 2.º y 5.º se
               suma leer las 40 líneas; si no aparece en el top 5 se suma el camino grep completo.

Tokens = (caracteres + 3) // 4 (aproximación estándar en benchmarks).
"""

import argparse
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys
import tempfile
import warnings

warnings.filterwarnings("ignore")
MOTOR_DIR = Path(__file__).resolve().parent.parent / "engine"
sys.path.insert(0, str(MOTOR_DIR))

try:
    import telemetry
    telemetry.record_search_event = lambda *a, **k: None  # no ensuciar telemetría
    import indexer
    import cache
    import server_mcp
except ImportError as e:
    sys.exit(f"No se pudo importar el motor ({e}). Usa el Python del entorno de SynRAG.")

DEFAULT_REPO = None  # obligatorio: --repo <clon de github.com/pallets/flask>
DEFAULT_PREGUNTAS = Path(__file__).resolve().parent / "preguntas" / "flask-docs.json"
GREP_LINEAS = 30
TRAMO_LINEAS = 40


def tokens(texto: str) -> int:
    return (len(texto) + 3) // 4


def git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return r.stdout


def grep_docs(repo: Path, patron: str) -> list[str]:
    salida = git(repo, "grep", "-n", "-E", patron, "--", "docs/*")
    return salida.splitlines()


def leer_tramo_docs(repo: Path, archivo: str, inicio: int, n_lineas: int = TRAMO_LINEAS) -> str:
    lineas = (repo / archivo).read_text(errors="ignore").splitlines()
    fin = min(len(lineas), inicio + n_lineas - 1)
    return "\n".join(f"{n}\t{l}" for n, l in enumerate(lineas[inicio - 1:fin], start=inicio))


def camino_grep(repo: Path, p: dict) -> int:
    salida = grep_docs(repo, p["grep"])
    costo = tokens("\n".join(salida[:GREP_LINEAS]))
    costo += tokens(leer_tramo_docs(repo, p["archivo"], p["linea"], TRAMO_LINEAS))
    return costo


def camino_archivo(repo: Path, p: dict) -> int:
    lista = git(repo, "grep", "-l", "-E", p["grep"], "--", "docs/*").splitlines()
    costo_grep = tokens("\n".join(lista[:GREP_LINEAS]))
    costo_archivo = tokens((repo / p["archivo"]).read_text(errors="ignore"))
    return costo_grep + costo_archivo


def camino_synrag(repo: Path, p: dict, proyecto: str) -> dict:
    salida = server_mcp.search_desktop(p["consulta"], limit=5, project=proyecto, tipo="docs")
    costo = tokens(salida)

    # Detectar bloques de resultados en la salida
    bloques, actual = [], None
    for linea in salida.splitlines():
        if re.match(r"(?:- )?~?/\S*:\d+", linea):
            actual = [linea]
            bloques.append(actual)
        elif actual is not None:
            actual.append(linea)
    bloques_str = ["\n".join(b) for b in bloques]

    def contiene_respuesta(cabecera: str) -> bool:
        m = re.search(re.escape(p["archivo"]) + r":(\d+)(?:-(\d+))?", cabecera)
        return bool(m) and int(m.group(1)) <= p["linea"] <= int(m.group(2) or m.group(1))

    pos = next((i for i, b in enumerate(bloques_str) if contiene_respuesta(b.split("\n", 1)[0])), None)

    if pos is None:
        # No encontrado en top 5: fallback a grep
        g = camino_grep(repo, p)
        return {"tokens": costo + g, "salida": costo, "pos": None, "con_cuerpo": False}

    if pos == 0:
        # El 1.er resultado ya incluye el cuerpo del fragmento
        return {"tokens": costo, "salida": costo, "pos": 1, "con_cuerpo": True}
    else:
        # Resultados 2 a 5 solo traen la firma: el agente lee las 40 líneas
        costo_tramo = tokens(leer_tramo_docs(repo, p["archivo"], p["linea"], TRAMO_LINEAS))
        return {"tokens": costo + costo_tramo, "salida": costo, "pos": pos + 1, "con_cuerpo": False}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", type=Path, required=True, help="clon de github.com/pallets/flask")
    ap.add_argument("--preguntas", type=Path, default=DEFAULT_PREGUNTAS)
    ap.add_argument("--proyecto", help="Nombre del proyecto en LanceDB")
    ap.add_argument("--indexar", action="store_true", default=True,
                    help="Crea un índice temporal de LanceDB para el benchmark (por defecto True)")
    ap.add_argument("--detalle", action="store_true", help="Muestra detalles por cada pregunta")
    a = ap.parse_args()

    repo = a.repo.expanduser().resolve()
    if not repo.exists():
        sys.exit(f"No existe el repositorio: {repo}")

    if a.indexar or not a.proyecto:
        import os
        tmp_db = Path(tempfile.mkdtemp(prefix="synrag-bench-docs-"))
        indexer.DB_PATH = tmp_db
        os.environ["SYNRAG_CARPETAS"] = f"{repo}={repo.name}"
        a.proyecto = repo.name
        print(f"[INFO] Indexando repositorio {repo.name} en índice temporal {tmp_db}...")
        indexer.index_desktop()

    preguntas = json.loads(a.preguntas.read_text(encoding="utf-8"))

    try:
        cache.clear_cache(indexer.get_db())
    except Exception:
        pass

    filas = []
    for p in preguntas:
        g = camino_grep(repo, p)
        f = camino_archivo(repo, p)
        s = camino_synrag(repo, p, a.proyecto)
        filas.append({"p": p, "grep": g, "archivo": f, **{f"s_{k}": v for k, v in s.items()}})

    print("\n| Pregunta | Grep + 40 líns | Archivo entero | SynRAG | Puesto | Ahorro vs grep | Ahorro vs arch |")
    print("|---|---|---|---|---|---|---|")
    for row in filas:
        p = row["p"]
        g = row["grep"]
        f = row["archivo"]
        st = row["s_tokens"]
        pos = row["s_pos"] if row["s_pos"] is not None else "-"
        ah_g = 100 * (st - g) / g
        ah_f = 100 * (st - f) / f
        consulta_corta = p["consulta"][:45] + ("..." if len(p["consulta"]) > 45 else "")
        print(f"| {consulta_corta} | {g} | {f} | {st} | {pos} | {ah_g:+.1f} % | {ah_f:+.1f} % |")

    tg = sum(r["grep"] for r in filas)
    tf = sum(r["archivo"] for r in filas)
    ts = sum(r["s_tokens"] for r in filas)
    gana = sum(r["s_tokens"] < r["grep"] for r in filas)
    top1 = sum(r["s_pos"] == 1 for r in filas)
    encontro = sum(r["s_pos"] is not None for r in filas)

    ah_total_g = 100 * (ts - tg) / tg
    ah_total_f = 100 * (ts - tf) / tf

    print(f"\n== Resumen ({len(filas)} preguntas sobre documentacion de Flask)")
    print(f"  Tokens totales:  Grep+40 líns: {tg}   Archivo entero: {tf}   SynRAG: {ts}")
    print(f"  SynRAG vs Grep + 40 líns: {ah_total_g:+.1f} %")
    print(f"  SynRAG vs Archivo entero: {ah_total_f:+.1f} %")
    print(f"  Definición/sección 1.a en: {top1}/{len(filas)}")
    print(f"  Respuesta en el top 5 en: {encontro}/{len(filas)}")
    print(f"  SynRAG gana a grep en: {gana}/{len(filas)}")
    print(f"  Mediana por pregunta: Grep {statistics.median(r['grep'] for r in filas):.0f}, "
          f"SynRAG {statistics.median(r['s_tokens'] for r in filas):.0f}")


if __name__ == "__main__":
    main()
