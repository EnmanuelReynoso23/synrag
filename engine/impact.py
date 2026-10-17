"""
Grafo de Impacto y Dependencias para LanceDB Hub
Registra qué archivos importan cada símbolo (función, clase, interface, hook)
para alertar a las IAs antes de que modifiquen funciones que romperían otros módulos.
"""

from typing import List, Dict, Any, Optional
import lancedb

IMPACT_TABLE = "impact_graph"


def _has_table(db: lancedb.DBConnection, table_name: str) -> bool:
    try:
        res = db.list_tables()
        tables = res.tables if hasattr(res, "tables") else res
        return table_name in tables
    except Exception:
        try:
            return table_name in db.table_names()
        except Exception:
            return False


def get_impact_table(db: lancedb.DBConnection):
    """Obtiene o inicializa la tabla del grafo de impacto."""
    if _has_table(db, IMPACT_TABLE):
        return db.open_table(IMPACT_TABLE)
    return None


def init_impact_table(db: lancedb.DBConnection, records: List[Dict[str, Any]]):
    """Crea la tabla impact_graph con los registros iniciales."""
    if not records:
        records = [{
            "symbol": "__init__",
            "imported_by": "__init__",
            "source": "__init__",
            "project": "__init__",
        }]
    return db.create_table(IMPACT_TABLE, data=records, mode="overwrite")


def get_dependents(db: lancedb.DBConnection, symbol_name: str, project: Optional[str] = None) -> List[str]:
    """Devuelve los archivos que importan el símbolo especificado."""
    if not _has_table(db, IMPACT_TABLE) or not symbol_name:
        return []
    tbl = db.open_table(IMPACT_TABLE)
    try:
        clean_sym = symbol_name.replace("'", "")
        filter_expr = f"symbol = '{clean_sym}'"
        if project:
            clean_proj = project.replace("'", "")
            filter_expr += f" AND project = '{clean_proj}'"
        rows = tbl.search().where(filter_expr).limit(25).to_list()
        dependents = list(set(r["imported_by"] for r in rows if r["imported_by"] != "__init__"))
        return dependents
    except Exception:
        return []


def format_impact_warning(dependents: List[str], symbol_name: str) -> str:
    """Genera la advertencia de arquitectura para inyectar al contexto del LLM."""
    if not dependents:
        return ""
    deps_list = "\n".join(f"  • {d}" for d in dependents[:6])
    more = f"\n  ... y {len(dependents) - 6} más" if len(dependents) > 6 else ""
    return (
        f"\n[GRAFO DE IMPACTO] El símbolo '{symbol_name}' es importado por {len(dependents)} archivo(s):\n"
        f"{deps_list}{more}\n"
        f"Verifica la compatibilidad de tipos y firmas antes de modificarlo."
    )


# ------------------------------------------------------------------------------------------------
# Consumidores resueltos: que archivos dependen de ESTA definicion del simbolo (no de cualquiera
# que se llame igual), siguiendo alias de tsconfig, paquetes del monorepo y barrels.
# ------------------------------------------------------------------------------------------------
PROFUNDIDAD_BARRELS = 6


def destino_final(simbolo: str, archivo: str, definidores: set, reexports_de, resolutor, profundidad: int = 0) -> Optional[str]:
    """Archivo que define `simbolo` llegando desde `archivo`: el mismo si lo define; si es un barrel
    (`export { x } from`, `export * from`, `from .mod import x` en un __init__.py), sigue la cadena."""
    if archivo in definidores:
        return archivo
    if profundidad >= PROFUNDIDAD_BARRELS:
        return None
    for src in reexports_de(archivo, simbolo):
        destino = resolutor.resolver(src, archivo)
        if destino and destino != archivo:
            final = destino_final(simbolo, destino, definidores, reexports_de, resolutor, profundidad + 1)
            if final:
                return final
    return None


def agrupar_consumidores(simbolo: str, definidores: set, importaciones: List[tuple], reexports_de, resolutor) -> Dict[str, Any]:
    """importaciones: [(archivo_que_importa, origen)] de `simbolo`, con rutas absolutas.
    Devuelve {"por_definicion": {definidor: [archivos]}, "externos": {origen: n}, "sin_resolver": [(archivo, origen)]}."""
    por_def: Dict[str, List[str]] = {d: [] for d in definidores}
    externos: Dict[str, int] = {}
    sin_resolver: List[tuple] = []
    for archivo, origen in importaciones:
        destino = resolutor.resolver(origen, archivo)
        if destino is None:
            if origen.startswith("."):  # relativo que no resuelve: archivo no indexado
                sin_resolver.append((archivo, origen))
            else:
                externos[origen] = externos.get(origen, 0) + 1
            continue
        final = destino_final(simbolo, destino, definidores, reexports_de, resolutor)
        if final:
            if archivo not in por_def[final]:
                por_def[final].append(archivo)
        else:
            sin_resolver.append((archivo, origen))
    return {"por_definicion": por_def, "externos": externos, "sin_resolver": sin_resolver}
