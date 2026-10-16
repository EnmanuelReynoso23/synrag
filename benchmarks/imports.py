#!/usr/bin/env python3
"""Precision y cobertura del grafo de impacto: los imports que extrae SynRAG frente a un oraculo.

El grafo de impacto (get_impact_radius) sale de los imports de cada archivo. Aqui se comparan, como
conjuntos de aristas (archivo, simbolo, origen), con lo que dice el analizador oficial de cada lenguaje:
  - Python: el modulo `ast` (incluye imports dentro de funciones).
  - TS/JS: el compilador de TypeScript (benchmarks/imports_ts.cjs; necesita node y `typescript`).
    Cuenta import default, `* as`, `{ a, b as c }` y los re-export `export { a } from` / `export * from`.

  cobertura = aristas del oraculo que SynRAG tambien tiene; precision = aristas de SynRAG que son reales.

Uso:
  python benchmarks/imports.py /tmp/flask /tmp/hono [--engine ruta/a/engine] [--ejemplos 3]
"""
import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
EXT_TS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}


def _indexable(p: Path, repo: Path) -> bool:
    """Mismo filtro que el indexador (sin dist/, build/, minificados...): se mide lo que se indexa."""
    try:
        import indexer
        return indexer.should_index(p, repo)
    except Exception:
        return True


def _git_ls(repo: Path):
    r = subprocess.run(["git", "-C", str(repo), "ls-files"], capture_output=True, text=True)
    for rel in r.stdout.splitlines():
        p = repo / rel
        if "node_modules" not in p.parts and p.is_file() and _indexable(p, repo):
            yield p


def oraculo_python(p: Path):
    try:
        arbol = ast.parse(p.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:
        return None
    aristas = set()
    for n in ast.walk(arbol):
        if isinstance(n, ast.Import):
            for a in n.names:
                aristas.add((a.name.split(".")[-1], a.name))
        elif isinstance(n, ast.ImportFrom):
            origen = "." * n.level + (n.module or "")
            for a in n.names:
                aristas.add((a.name, origen))
    return aristas


def oraculo_ts(rutas, raiz_node: Path):
    if not rutas:
        return {}
    r = subprocess.run(["node", str(AQUI / "imports_ts.cjs")], input="\n".join(map(str, rutas)),
                       capture_output=True, text=True, cwd=raiz_node)
    if r.returncode:
        sys.exit(f"Oraculo de TypeScript fallo (falta node o `typescript`?): {r.stderr[:300]}")
    salida = {}
    for linea in r.stdout.splitlines():
        d = json.loads(linea)
        salida[d["file"]] = {tuple(e) for e in d["edges"]}
    return salida


def _extraer(chunker, p: Path):
    texto = p.read_text(encoding="utf-8", errors="ignore")
    try:
        return chunker.extract_imports_and_exports(texto, p.suffix)[0]
    except TypeError:  # motor anterior: solo recibe el texto
        return chunker.extract_imports_and_exports(texto)[0]


def medir(repo: Path, chunker, ejemplos: int):
    py = [p for p in _git_ls(repo) if p.suffix == ".py"]
    tsr = [p for p in _git_ls(repo) if p.suffix in EXT_TS]
    oraculos = {str(p): oraculo_python(p) for p in py}
    oraculos.update(oraculo_ts(tsr, AQUI.parent))
    reales = encontradas = acertadas = 0
    faltan, sobran = [], []
    for ruta, esperado in oraculos.items():
        if esperado is None:
            continue
        p = Path(ruta)
        hallado = {(i["symbol"], i.get("source", "")) for i in _extraer(chunker, p)}
        reales += len(esperado)
        encontradas += len(hallado)
        acertadas += len(esperado & hallado)
        rel = p.relative_to(repo)
        faltan += [(rel, e) for e in sorted(esperado - hallado)]
        sobran += [(rel, e) for e in sorted(hallado - esperado)]
    cob = 100 * acertadas / max(reales, 1)
    pre = 100 * acertadas / max(encontradas, 1)
    print(f"{repo.name}: {reales} imports reales; SynRAG extrae {encontradas}; cobertura {cob:.1f} %, precision {pre:.1f} %")
    for rel, e in faltan[:ejemplos]:
        print(f"   falta  {rel}: {e[0]} <- {e[1]}")
    for rel, e in sobran[:ejemplos]:
        print(f"   sobra  {rel}: {e[0]} <- {e[1]}")
    return cob, pre


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("repos", nargs="+", type=Path)
    ap.add_argument("--engine", type=Path, default=AQUI.parent / "engine")
    ap.add_argument("--ejemplos", type=int, default=3)
    a = ap.parse_args()
    sys.path.insert(0, str(a.engine.resolve()))
    import chunker
    for repo in a.repos:
        medir(repo.resolve(), chunker, a.ejemplos)


if __name__ == "__main__":
    main()
