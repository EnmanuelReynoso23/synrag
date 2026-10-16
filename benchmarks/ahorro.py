#!/usr/bin/env python3
"""Cuantos tokens cuesta llegar al codigo correcto: SynRAG frente a lo que hace un agente sin SynRAG.

Para cada pregunta se simulan tres caminos y se cuenta lo que entraria al contexto del modelo:
  - archivo:  grep para encontrar el archivo y leerlo entero.
  - grep:     grep del nombre (las primeras 30 lineas de salida, como un agente prudente) y leer
              el tramo de la definicion (60 lineas o hasta su final). Si la definicion no sale en
              esas 30 lineas, se suma un segundo grep mas preciso.
  - synrag:   la salida de search_desktop tal como la recibe el modelo; si no trae el cuerpo de la
              definicion se suma leer el tramo, y si no encuentra el archivo se suma el camino grep.

Las preguntas salen de un repositorio git real: N funciones exportadas con nombre unico, elegidas
con una semilla, mas las preguntas en lenguaje natural de un archivo JSON opcional.

Tokens = caracteres / 4 (aproximacion; sirve para comparar caminos entre si, no como factura).

Uso (con el Python del entorno de SynRAG):
    git clone --depth 1 https://github.com/honojs/hono /tmp/hono
    python benchmarks/ahorro.py --repo /tmp/hono --indexar [--n 25] [--semilla 1] [--detalle]
    python benchmarks/ahorro.py --repo ~/mi-repo --proyecto nombre-en-tu-indice   # con tu indice

Indice alternativo: SYNRAG_DB_PATH=/ruta/al/indice python benchmarks/ahorro.py ...
Solo lee el indice y el repositorio; no escribe telemetria.
"""
import argparse
import json
import random
import re
import statistics
import subprocess
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

try:
    import telemetry
    telemetry.record_search_event = lambda *a, **k: None  # no ensuciar la telemetria del usuario
    import indexer
    import cache
    import server_mcp
except ImportError as e:  # pragma: no cover
    sys.exit(f"No se pudo importar el motor ({e}). Usa el Python del entorno de SynRAG.")

GREP_LINEAS = 30
TRAMO_MIN = 60
EXT = ["*.ts", "*.tsx", "*.js", "*.jsx", "*.py"]
RE_DEF = r"(function|const|let|class|interface|type|def) {nombre}\b"


def tokens(texto: str) -> int:
    return (len(texto) + 3) // 4


def git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return r.stdout


def grep(repo: Path, patron: str) -> list[str]:
    salida = git(repo, "grep", "-n", "-E", patron, "--", *EXT, ":!*node_modules*", ":!*dist/*")
    return salida.splitlines()


def fin_de_bloque(lineas: list[str], inicio: int, python: bool = False) -> int:
    """Final aproximado de la definicion que empieza en `inicio` (1-based): sangria en Python
    (y en cualquier bloque sin llaves), balance de llaves en el resto."""
    cab = lineas[inicio - 1]
    sangria = len(cab) - len(cab.lstrip())
    if python:
        ultimo = inicio
        for i in range(inicio, min(len(lineas), inicio + 400)):
            l = lineas[i]
            if l.strip():
                if len(l) - len(l.lstrip()) <= sangria and not l.lstrip().startswith((")", "]", "}")):
                    return ultimo
                ultimo = i + 1
        return ultimo
    prof, visto = 0, False
    for i in range(inicio - 1, min(len(lineas), inicio + 400)):
        l = lineas[i]
        prof += l.count("{") - l.count("}")
        visto = visto or "{" in l
        if visto and prof <= 0:
            return i + 1
    return min(len(lineas), inicio + TRAMO_MIN - 1)


def leer_tramo(repo: Path, archivo: str, inicio: int) -> str:
    lineas = (repo / archivo).read_text(errors="ignore").splitlines()
    fin = max(inicio + TRAMO_MIN - 1, fin_de_bloque(lineas, inicio, archivo.endswith(".py")))
    return "\n".join(f"{n}\t{l}" for n, l in enumerate(lineas[inicio - 1:fin], start=inicio))


def preguntas_de_simbolos(repo: Path, n: int, semilla: int) -> list[dict]:
    """Funciones con nombre unico en el repo: exportadas en JS/TS y de primer nivel en Python."""
    por_nombre: dict[str, list[tuple[str, int]]] = {}
    for patron, extraer in (
        (r"export (default )?(async )?function [A-Za-z0-9_$]+", r"([^:]+):(\d+):.*function ([A-Za-z0-9_$]+)"),
        (r"^(async )?def [A-Za-z][A-Za-z0-9_]*\(", r"([^:]+):(\d+):(?:async )?def ([A-Za-z][A-Za-z0-9_]*)"),
    ):
        for d in grep(repo, patron):
            m = re.match(extraer, d)
            if m and not re.search(r"(^|/)(tests?|__tests__|spec)/|\.(test|spec)\.|test_", m.group(1)):
                por_nombre.setdefault(m.group(3), []).append((m.group(1), int(m.group(2))))
    unicos = sorted((k, v[0]) for k, v in por_nombre.items() if len(v) == 1 and len(k) > 3)
    elegidos = random.Random(semilla).sample(unicos, min(n, len(unicos)))
    return [{"tipo": "simbolo", "consulta": k, "grep": rf"\b{k}\b", "archivo": a, "linea": l, "simbolo": k}
            for k, (a, l) in elegidos]


def camino_grep(repo: Path, p: dict) -> tuple[int, bool]:
    salida = grep(repo, p["grep"])
    costo = tokens("\n".join(salida[:GREP_LINEAS]))
    if not any(s.startswith(f"{p['archivo']}:{p['linea']}:") for s in salida[:GREP_LINEAS]):
        segundo = grep(repo, RE_DEF.format(nombre=re.escape(p["simbolo"])))
        costo += tokens("\n".join(segundo[:GREP_LINEAS]))
    return costo + tokens(leer_tramo(repo, p["archivo"], p["linea"])), True


def camino_archivo(repo: Path, p: dict) -> int:
    lista = git(repo, "grep", "-l", "-E", p["grep"], "--", *EXT).splitlines()
    return tokens("\n".join(lista[:GREP_LINEAS])) + tokens((repo / p["archivo"]).read_text(errors="ignore"))


def camino_synrag(repo: Path, p: dict, proyecto: str) -> dict:
    salida = server_mcp.search_desktop(p["consulta"], limit=5, project=proyecto)
    costo = tokens(salida)
    # Cada resultado empieza en una linea de ubicacion ("▸ ruta" en el formato antiguo, "~/ruta" o
    # "- ~/ruta" en el nuevo); su bloque llega hasta la siguiente.
    bloques, actual = [], None
    for linea in salida.splitlines():
        if re.match(r"(▸ |- )?~?/\S*:\d+", linea):  # "ruta:lineas", no un "/**" de JSDoc
            actual = [linea]
            bloques.append(actual)
        elif actual is not None:
            actual.append(linea)
    bloques = ["\n".join(b) for b in bloques]
    def es_la_respuesta(cabecera: str) -> bool:
        # el archivo correcto Y un rango de lineas que contiene la definicion (no otra funcion del archivo)
        m = re.search(re.escape(p["archivo"]) + r":(\d+)(?:-(\d+))?", cabecera)
        return bool(m) and int(m.group(1)) <= p["linea"] <= int(m.group(2) or m.group(1))
    pos = next((i for i, b in enumerate(bloques) if es_la_respuesta(b.split("\n", 1)[0])), None)
    if pos is None:
        g, _ = camino_grep(repo, p)
        return {"tokens": costo + g, "salida": costo, "pos": None, "con_cuerpo": False}
    cuerpo = bloques[pos]
    definicion = re.search(RE_DEF.format(nombre=re.escape(p["simbolo"])), cuerpo) if p.get("simbolo") else None
    lineas = (repo / p["archivo"]).read_text(errors="ignore").splitlines()
    # la ultima linea con contenido real del bloque (una "}" suelta no prueba nada)
    fin = fin_de_bloque(lineas, p["linea"], p["archivo"].endswith(".py")) if p.get("linea") else 0
    ultima = next((l.strip() for l in reversed(lineas[p.get("linea", 1) - 1:fin]) if len(l.strip()) > 3), "")
    con_cuerpo = bool(definicion) and (not ultima or ultima in cuerpo)
    if not con_cuerpo:
        costo += tokens(leer_tramo(repo, p["archivo"], p["linea"]))
    return {"tokens": costo, "salida": tokens(salida), "pos": pos + 1, "con_cuerpo": con_cuerpo}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--proyecto", help="nombre del proyecto en tu indice (list_projects); con --indexar no hace falta")
    ap.add_argument("--indexar", action="store_true",
                    help="indexa solo --repo en un indice temporal (no toca el tuyo): reproducible en cualquier equipo")
    ap.add_argument("--n", type=int, default=25)
    ap.add_argument("--semilla", type=int, default=1)
    ap.add_argument("--naturales", type=Path, help="JSON con preguntas en lenguaje natural")
    ap.add_argument("--detalle", action="store_true")
    a = ap.parse_args()
    repo = a.repo.expanduser().resolve()
    if a.indexar:
        import os
        import tempfile
        indexer.DB_PATH = Path(tempfile.mkdtemp(prefix="synrag-bench-"))
        os.environ["SYNRAG_CARPETAS"] = f"{repo}={repo.name}"
        a.proyecto = repo.name
        indexer.index_desktop()
    elif not a.proyecto:
        ap.error("falta --proyecto (o usa --indexar)")

    preguntas = preguntas_de_simbolos(repo, a.n, a.semilla)
    if a.naturales:
        preguntas += [dict(q, tipo="natural") for q in json.loads(a.naturales.read_text())]

    try:
        cache.clear_cache(indexer.get_db())
    except Exception:
        pass

    filas = []
    for p in preguntas:
        g, _ = camino_grep(repo, p)
        f = camino_archivo(repo, p)
        s = camino_synrag(repo, p, a.proyecto)
        filas.append({"p": p, "grep": g, "archivo": f, **{f"s_{k}": v for k, v in s.items()}})
        if a.detalle:
            pos = s["pos"] or "-"
            print(f"{p['tipo'][:3]} {p['consulta'][:42]:42} grep {g:6} archivo {f:6} synrag {s['tokens']:6} "
                  f"(salida {s['salida']}, puesto {pos}, cuerpo {'si' if s['con_cuerpo'] else 'no'})")

    for tipo in ("simbolo", "natural"):
        fs = [x for x in filas if x["p"]["tipo"] == tipo]
        if not fs:
            continue
        tg, tf, ts = (sum(x[k] for x in fs) for k in ("grep", "archivo", "s_tokens"))
        gana = sum(x["s_tokens"] < x["grep"] for x in fs)
        top1 = sum(x["s_pos"] == 1 for x in fs)
        encontro = sum(x["s_pos"] is not None for x in fs)
        print(f"\n== {tipo}: {len(fs)} preguntas")
        print(f"  tokens totales  grep+tramo {tg:7}   archivo entero {tf:7}   synrag {ts:7}")
        print(f"  synrag vs grep: {100 * (ts - tg) / tg:+.0f} %   vs archivo: {100 * (ts - tf) / tf:+.0f} %")
        print(f"  synrag gana a grep en {gana}/{len(fs)}; definicion 1.a en {top1}/{len(fs)}; "
              f"archivo en el top 5 en {encontro}/{len(fs)}")
        print(f"  mediana por pregunta: grep {statistics.median(x['grep'] for x in fs):.0f}, "
              f"synrag {statistics.median(x['s_tokens'] for x in fs):.0f}")


if __name__ == "__main__":
    main()
