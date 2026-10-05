"""
Grafo de Impacto y Dependencias para LanceDB Hub
Registra qué archivos importan cada símbolo (función, clase, interface, hook)
para alertar a las IAs antes de que modifiquen funciones que romperían otros módulos.
"""

from typing import List, Dict, Any, Optional
import lancedb

IMPACT_TABLE = "impact_graph"


def get_impact_table(db: lancedb.DBConnection):
    """Obtiene o inicializa la tabla del grafo de impacto."""
    if IMPACT_TABLE in db.table_names():
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
    if IMPACT_TABLE not in db.table_names() or not symbol_name:
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
