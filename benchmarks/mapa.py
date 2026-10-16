#!/usr/bin/env python3
"""Benchmark de ahorro: empaquetado completo vs comprimido (Repomix --compress)
y mapa del repo (Aider RepoMap) dentro de presupuestos de 1024 y 2048 tokens.
"""

import argparse
import os
import shutil
import sys
import tempfile
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

try:
    import telemetry
    telemetry.record_search_event = lambda *a, **k: None
    import indexer
    import mapa
    import empaquetar
except ImportError as e:
    sys.exit(f"No se pudo importar el motor ({e}). Usa el Python del entorno de SynRAG.")


def tokens(texto: str) -> int:
    return (len(texto) + 3) // 4


def benchmark_repo(repo: Path, proyecto: str = ""):
    repo = repo.expanduser().resolve()
    if not repo.is_dir():
        sys.exit(f"No existe el directorio {repo}")

    # Indexar en índice temporal (reproducible, sin tocar el índice del usuario)
    temp_dir = Path(tempfile.mkdtemp(prefix="synrag-bench-mapa-"))
    old_db = indexer.DB_PATH
    old_carpetas = os.environ.get("SYNRAG_CARPETAS")
    try:
        indexer.DB_PATH = temp_dir
        proj_nombre = proyecto or repo.name
        os.environ["SYNRAG_CARPETAS"] = f"{repo}={proj_nombre}"
        t0_idx = time.time()
        indexer.index_desktop()
        t_idx = time.time() - t0_idx

        # 1. Empaquetado completo vs comprimido
        t0 = time.time()
        txt_full, stats_full = empaquetar.empaquetar(repo, comprimir=False)
        t_full = time.time() - t0

        t0 = time.time()
        txt_comp, stats_comp = empaquetar.empaquetar(repo, comprimir=True)
        t_comp = time.time() - t0

        tok_full = stats_full["tokens"]
        tok_comp = stats_comp["tokens"]
        ahorro_pct = 100.0 * (tok_comp - tok_full) / tok_full if tok_full else 0.0

        # 2. Mapa del repo con presupuestos
        t0 = time.time()
        mapa_1024 = mapa.mapa_del_repo(proj_nombre, tokens=1024)
        t_1024 = time.time() - t0
        tok_1024 = tokens(mapa_1024)

        t0 = time.time()
        mapa_2048 = mapa.mapa_del_repo(proj_nombre, tokens=2048)
        t_2048 = time.time() - t0
        tok_2048 = tokens(mapa_2048)

        print(f"\n==================================================================")
        print(f"Benchmark SynRAG: {proj_nombre} ({repo})")
        print(f"==================================================================")
        print(f"Archivos indexados: {stats_full['total_archivos']} ({stats_full['num_omitidos']} omitidos) en {t_idx:.2f}s")
        print(f"\n1. Empaquetado (Repomix):")
        print(f"  - Completo:   {tok_full:>10,} tokens ({t_full:.2f}s)")
        print(f"  - Comprimido: {tok_comp:>10,} tokens ({t_comp:.2f}s)")
        print(f"  - Reducción:  {ahorro_pct:>+10.1f} %")
        print(f"\n2. Mapa del Repo (Aider RepoMap):")
        print(f"  - Presupuesto 1024: {tok_1024:>6} tokens obtenidos ({t_1024:.2f}s)")
        print(f"  - Presupuesto 2048: {tok_2048:>6} tokens obtenidos ({t_2048:.2f}s)")
        print(f"==================================================================\n")

        return {
            "proyecto": proj_nombre,
            "archivos": stats_full["total_archivos"],
            "omitidos": stats_full["num_omitidos"],
            "empaquetado_completo": tok_full,
            "empaquetado_comprimido": tok_comp,
            "reduccion_pct": ahorro_pct,
            "mapa_1024": tok_1024,
            "mapa_2048": tok_2048,
        }

    finally:
        indexer.DB_PATH = old_db
        if old_carpetas is not None:
            os.environ["SYNRAG_CARPETAS"] = old_carpetas
        else:
            os.environ.pop("SYNRAG_CARPETAS", None)
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True, type=Path, help="Ruta al repositorio a evaluar")
    ap.add_argument("--proyecto", help="Nombre del proyecto (por defecto el nombre de la carpeta)")
    a = ap.parse_args()
    benchmark_repo(a.repo, a.proyecto)


if __name__ == "__main__":
    main()
