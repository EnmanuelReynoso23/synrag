#!/usr/bin/env python3
"""Resolucion de imports y precision del grafo de impacto, frente al compilador de TypeScript.

A) Cada import de TS/JS (archivo, origen) se resuelve con engine/resolver.py y con TypeScript
   (benchmarks/resolucion_ts.cjs: tsconfig mas cercano con extends, paths, baseUrl y paquetes del
   monorepo enlazados en node_modules). Se cuenta en cuantos coinciden.

B) Para cada simbolo definido en un archivo D: que archivos dependen de ESA definicion.
   - "por nombre" (lo que hacia get_impact_radius): todos los que importan algo con ese nombre.
   - "resuelto": engine/impact.agrupar_consumidores (resolver + barrels).
   La verdad sale de la resolucion de TypeScript siguiendo los re-export. Se mide en los simbolos
   con nombre repetido en el proyecto (donde importa) y en todos.

Uso:
  python benchmarks/resolucion.py ~/mi-monorepo /tmp/hono [--engine ruta/a/engine]
"""
import argparse
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

AQUI = Path(__file__).resolve().parent
EXT_TS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}


class Verdad:
    """Resolutor que responde con lo que dijo TypeScript."""

    def __init__(self, mapa):
        self.mapa = mapa

    def resolver(self, origen, archivo):
        return self.mapa.get((archivo, origen)) or None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("repos", nargs="+", type=Path)
    ap.add_argument("--engine", type=Path, default=AQUI.parent / "engine")
    ap.add_argument("--ejemplos", type=int, default=3)
    a = ap.parse_args()
    sys.path.insert(0, str(a.engine.resolve()))
    sys.path.append(str(AQUI))  # al final: benchmarks/mapa.py no debe tapar engine/mapa.py
    import chunker
    import impact
    import resolver
    from imports import _git_ls

    for repo in a.repos:
        repo = repo.resolve()
        archivos = [p for p in _git_ls(repo) if p.suffix in EXT_TS]
        todos = {str(p) for p in _git_ls(repo)}
        aristas = []  # (archivo, simbolo, origen)
        definidores = defaultdict(set)
        for p in archivos:
            texto = p.read_text(encoding="utf-8", errors="ignore")
            chunks, imps, _ = chunker.parse_and_chunk_file(p, texto)
            aristas += [(str(p), i["symbol"], i["source"]) for i in imps]
            for c in chunks:
                if c.get("symbol_name") and c.get("symbol_kind") not in ("imports", "method", "field"):
                    definidores[c["symbol_name"]].add(str(p))

        pares = sorted({(f, o) for f, _, o in aristas})
        r = subprocess.run(["node", str(AQUI / "resolucion_ts.cjs")], input="\n".join(f"{f}\t{o}" for f, o in pares),
                           capture_output=True, text=True, cwd=AQUI.parent)
        if r.returncode:
            sys.exit(f"Oraculo de TypeScript fallo: {r.stderr[:300]}")
        verdad = {}
        for linea in r.stdout.splitlines():
            f, o, d = (linea.split("\t") + ["", ""])[:3]
            verdad[(f, o)] = d if d in todos else ""
        nuestro = resolver.Resolutor(repo, todos)

        # A) resolucion
        locales = iguales = falsos = 0
        malos = []
        for f, o in pares:
            v, n = verdad.get((f, o), ""), nuestro.resolver(o, f)
            if v:
                locales += 1
                iguales += n == v
                if n != v:
                    malos.append((f, o, n, v))
            elif n:
                falsos += 1
        print(f"{repo.name}: {len(pares)} imports distintos, {locales} locales segun TypeScript; "
              f"mismo archivo {100 * iguales / max(locales, 1):.1f} %; "
              f"resueltos de mas (TS dice externo): {falsos}")
        for f, o, n, v in malos[:a.ejemplos]:
            print(f"   {Path(f).relative_to(repo)}: '{o}' -> nuestro {n and Path(n).relative_to(repo)} | TS {Path(v).relative_to(repo)}")

        # B) precision del grafo de impacto
        reexports = defaultdict(list)
        por_simbolo = defaultdict(list)
        for f, s, o in aristas:
            reexports[(f, s)].append(o)
            por_simbolo[s].append((f, o))

        def reexports_de(archivo, simbolo):
            return reexports.get((archivo, simbolo), []) + reexports.get((archivo, "*"), [])

        tv = Verdad(verdad)
        cuentas = {k: {"nombre": [0, 0, 0], "resuelto": [0, 0, 0]} for k in ("repetidos", "todos")}  # [aciertos, predichos, reales]
        for s, defs in definidores.items():
            imps = por_simbolo.get(s, [])
            if not imps:
                continue
            real = impact.agrupar_consumidores(s, defs, imps, reexports_de, tv)["por_definicion"]
            pred = impact.agrupar_consumidores(s, defs, imps, reexports_de, nuestro)["por_definicion"]
            por_nombre = {f for f, _ in imps}
            for d in defs:
                rv = set(real[d])
                for grupo in (["todos", "repetidos"] if len(defs) > 1 else ["todos"]):
                    for modo, pr in (("nombre", por_nombre - {d}), ("resuelto", set(pred[d]))):
                        c = cuentas[grupo][modo]
                        c[0] += len(pr & rv)
                        c[1] += len(pr)
                        c[2] += len(rv)
        for grupo in ("repetidos", "todos"):
            partes = []
            for modo in ("nombre", "resuelto"):
                ac, pr, re_ = cuentas[grupo][modo]
                partes.append(f"{modo}: precision {100 * ac / max(pr, 1):.1f} %, cobertura {100 * ac / max(re_, 1):.1f} %")
            print(f"   impacto, simbolos {grupo:<9} | " + " | ".join(partes))


if __name__ == "__main__":
    main()
