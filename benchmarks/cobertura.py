#!/usr/bin/env python3
"""Cobertura del troceador: que parte del codigo queda dentro de algun fragmento del indice.

Una linea de codigo que no cae en ningun fragmento no se puede encontrar con search_desktop. Se
cuentan las lineas de codigo (sin comentarios) de los archivos .py/.ts/.tsx/.js/.jsx/.mjs de cada repositorio y cuantas
quedan fuera; tambien los archivos que pierden mas del 10 % y cuantos simbolos tienen nombre propio
(los que search_desktop devuelve enteros y primero al buscarlos por su nombre).

Uso:
  python benchmarks/cobertura.py /tmp/flask /tmp/hono [--engine ruta/a/engine] [--peores 5]
"""
import argparse
import subprocess
import sys
from pathlib import Path

EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs"}


def _es_codigo(linea: str) -> bool:
    """Linea con codigo: ni vacia, ni solo llaves, ni comentario."""
    s = linea.strip()
    return bool(s.strip("{}[]();,")) and not s.startswith(("//", "/*", "*", "#"))


def _indexable(p: Path, repo: Path) -> bool:
    """Mismo filtro que el indexador (sin dist/, build/, minificados...): se mide lo que se indexa."""
    try:
        import indexer
        return indexer.should_index(p, repo)
    except Exception:
        return True


def archivos(repo: Path):
    r = subprocess.run(["git", "-C", str(repo), "ls-files"], capture_output=True, text=True)
    for rel in r.stdout.splitlines():
        p = repo / rel
        if p.suffix in EXTS and "node_modules" not in p.parts and p.is_file() and _indexable(p, repo):
            yield p


def medir(repo: Path, chunker, peores: int):
    total = fuera = 0
    simbolos = set()
    malos = []
    for p in archivos(repo):
        texto = p.read_text(encoding="utf-8", errors="ignore")
        try:
            chunks, _, _ = chunker.parse_and_chunk_file(p, texto)
        except Exception:
            continue
        cubiertas = set()
        for c in chunks:
            if c.get("symbol_name") and c.get("symbol_kind") not in ("imports", "Documento"):
                simbolos.add((str(p), c["symbol_name"]))
            cubiertas.update(range(int(c.get("line", 1)), int(c.get("end_line", c.get("line", 1))) + 1))
        lineas = [i for i, l in enumerate(texto.splitlines(), 1) if _es_codigo(l)]
        perdidas = [i for i in lineas if i not in cubiertas]
        total += len(lineas)
        fuera += len(perdidas)
        if lineas and len(perdidas) / len(lineas) > 0.10:
            malos.append((len(perdidas), p.relative_to(repo)))
    malos.sort(reverse=True)
    print(f"{repo.name}: {total} lineas de codigo, {fuera} fuera de todo fragmento "
          f"({100 * fuera / max(total, 1):.1f} %); archivos que pierden > 10 %: {len(malos)}; "
          f"simbolos con nombre (encontrables por nombre exacto): {len(simbolos)}")
    for n, rel in malos[:peores]:
        print(f"   {n:>5} lineas  {rel}")
    return total, fuera


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("repos", nargs="+", type=Path)
    ap.add_argument("--engine", type=Path, default=Path(__file__).resolve().parent.parent / "engine")
    ap.add_argument("--peores", type=int, default=5)
    a = ap.parse_args()
    sys.path.insert(0, str(a.engine.resolve()))
    import chunker
    for repo in a.repos:
        medir(repo.resolve(), chunker, a.peores)


if __name__ == "__main__":
    main()
