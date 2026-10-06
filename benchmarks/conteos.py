#!/usr/bin/env python3
"""Cuenta lo que hay en TU indice: proyectos, fragmentos, relaciones del grafo de impacto y tamano en disco.

Uso (con el Python del entorno de SynRAG):
    python benchmarks/conteos.py
"""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

try:
    import impact
    import indexer
except ImportError as e:  # pragma: no cover
    sys.exit(f"No se pudo importar el motor ({e}). Usa el Python del entorno de SynRAG.")


def tamano(carpeta: Path) -> int:
    return sum(f.stat().st_size for f in carpeta.rglob("*") if f.is_file())


def main():
    db = indexer.get_db()
    nombres = db.table_names()
    if indexer.TABLE_NAME not in nombres:
        sys.exit("Aun no hay indice. Ejecuta: SYNRAG index")
    fragmentos = db.open_table(indexer.TABLE_NAME)
    proyectos = fragmentos.search().select(["project"]).limit(10_000_000).to_pandas()["project"].nunique()
    relaciones = db.open_table(impact.IMPACT_TABLE).count_rows() if impact.IMPACT_TABLE in nombres else 0
    ruta = Path(db.uri) if hasattr(db, "uri") else None
    print(f"Proyectos indexados:    {proyectos}")
    print(f"Fragmentos AST:         {fragmentos.count_rows():,}")
    print(f"Relaciones de impacto:  {relaciones:,}")
    if ruta and ruta.exists():
        print(f"Tamano en disco:        {tamano(ruta) / 1e6:.0f} MB ({ruta})")


if __name__ == "__main__":
    main()
