#!/usr/bin/env python3
"""Latencia de search_desktop con consultas nuevas por nombre de simbolo (incluye la linea de usos).

Indexa los repositorios en un indice temporal, calienta el reordenador con una consulta y mide cada
consulta una sola vez (sin cache). Las consultas son simbolos exportados elegidos con una semilla.
Con --engine se mide otro motor (por ejemplo, un `git worktree` de la version anterior).

Uso:
  python benchmarks/latencia_usos.py /tmp/flask /tmp/hono [--n 10] [--semilla 1] [--engine ruta/a/engine]
"""
import argparse
import contextlib
import io
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

warnings.filterwarnings("ignore")
AQUI = Path(__file__).resolve().parent
RE_EXPORT = re.compile(r"^(?:export\s+(?:async\s+)?(?:function|class|const)\s+|def\s+|class\s+)([A-Za-z_][A-Za-z0-9_]{3,})", re.M)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("repos", nargs="+", type=Path)
    ap.add_argument("--n", type=int, default=10, help="consultas por repositorio")
    ap.add_argument("--semilla", type=int, default=1)
    ap.add_argument("--engine", type=Path, default=AQUI.parent / "engine")
    a = ap.parse_args()
    sys.path.insert(0, str(a.engine.resolve()))
    sys.path.append(str(AQUI))  # al final: benchmarks/mapa.py no debe tapar engine/mapa.py
    repos = {r.resolve().name: r.resolve() for r in a.repos}
    os.environ["SYNRAG_CARPETAS"] = os.pathsep.join(f"{p}={n}" for n, p in repos.items())
    import telemetry
    telemetry.record_search_event = lambda *x, **k: None
    import indexer
    import server_mcp
    from imports import _git_ls

    tmp = Path(tempfile.mkdtemp(prefix="synrag-latencia-"))
    indexer.DB_PATH = tmp / "indice"
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            indexer.index_desktop()
        rnd = random.Random(a.semilla)
        consultas = []
        for nombre, repo in repos.items():
            simbolos = sorted({m for p in _git_ls(repo) if p.suffix in (".py", ".ts", ".tsx", ".js")
                               for m in RE_EXPORT.findall(p.read_text(encoding="utf-8", errors="ignore"))})
            consultas += [(nombre, s) for s in rnd.sample(simbolos, min(a.n, len(simbolos)))]
        server_mcp.search_desktop("calentar el reordenador", project=next(iter(repos)))
        tiempos = []
        for proyecto, q in consultas:
            t = time.perf_counter()
            server_mcp.search_desktop(q, project=proyecto)
            tiempos.append((time.perf_counter() - t) * 1000)
        tiempos.sort()
        print(f"{len(tiempos)} consultas nuevas: mediana {statistics.median(tiempos):.0f} ms, "
              f"p90 {tiempos[int(len(tiempos) * 0.9)]:.0f} ms, max {tiempos[-1]:.0f} ms")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
