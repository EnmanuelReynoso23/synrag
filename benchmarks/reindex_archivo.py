#!/usr/bin/env python3
"""Mide cuanto tarda `index_single_file` (lo que hace el observador al guardar un archivo).

Trabaja en un HOME temporal con 30 archivos TypeScript sinteticos: no toca tu indice ni tus proyectos.
No incluye la espera de 0,6 s con la que el observador agrupa guardados (DEBOUNCE_SECONDS en watcher.py).

Uso (con el Python del entorno de SynRAG):
    python benchmarks/reindex_archivo.py [--pruebas 15]
"""
import argparse
import os
import shutil
import statistics
import sys
import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pruebas", type=int, default=15)
    a = ap.parse_args()

    casa = Path(tempfile.mkdtemp(prefix="synrag-reindex-"))
    try:
        src = casa / "Proyectos" / "demo" / "src"
        src.mkdir(parents=True)
        for i in range(30):
            (src / f"mod{i}.ts").write_text(
                f"import {{ util{i} }} from './util{i}';\n"
                f"export interface Datos{i} {{ id: number; nombre: string }}\n"
                f"export function procesar{i}(d: Datos{i}) {{ return util{i}(d.id) + d.nombre.length; }}\n"
                f"export const servicio{i} = {{ ejecutar: (x: number) => procesar{i}({{ id: x, nombre: 'a' }}) }};\n",
                encoding="utf-8",
            )
        # El motor calcula sus rutas desde HOME al importarse: hay que fijarlo antes.
        os.environ["HOME"] = str(casa)
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))
        import indexer  # noqa: E402

        indexer.index_desktop()
        tiempos = []
        for i in range(a.pruebas):
            f = src / f"mod{i % 30}.ts"
            f.write_text(f.read_text(encoding="utf-8") + f"\nexport const extra{i} = {i};\n", encoding="utf-8")
            import time
            t = time.perf_counter()
            ok = indexer.index_single_file(f)
            tiempos.append((time.perf_counter() - t) * 1000)
            if not ok:
                sys.exit("index_single_file devolvio False: algo no funciona.")
        tiempos.sort()
        print(f"Reindexar un archivo pequeno, {len(tiempos)} pruebas: mediana {statistics.median(tiempos):.1f} ms, "
              f"p90 {tiempos[int(len(tiempos) * 0.9) - 1]:.1f} ms, max {tiempos[-1]:.1f} ms")
    finally:
        shutil.rmtree(casa, ignore_errors=True)


if __name__ == "__main__":
    main()
