"""
Mapa del repositorio basado en firmas y PageRank sobre el grafo de dependencias (Aider RepoMap).
Calcula la relevancia estructural de cada archivo del proyecto iterando potencias en Python puro.
"""

from pathlib import Path
from typing import List, Tuple, Dict, Set, Optional
import os
import re

import chunker
import impact
import indexer
import resolver

try:
    from tools.inspect_tools import _alias_locales
except Exception:
    def _alias_locales(f: Path) -> List[str]:
        return []


def firmas_de_archivo(ruta: Path) -> List[Tuple[int, str, str, str]]:
    """Extrae las firmas sintácticas de un archivo de código.
    Devuelve lista de (linea, tipo, nombre, firma).
    """
    if not ruta.is_file():
        return []

    try:
        content = ruta.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    chunks, _, _ = chunker.parse_and_chunk_file(ruta, content)
    resultado: List[Tuple[int, str, str, str]] = []

    for chk in chunks:
        tipo = str(chk.get("symbol_kind") or "code")
        nombre = str(chk.get("symbol_name") or "").strip()

        if tipo in ("imports", "section", "text") or nombre == "imports":
            continue

        chunk_content = chk.get("content", "")
        sin_comentarios = chunker._sin_comentarios_iniciales(chunk_content)
        lineas_sin = sin_comentarios.splitlines()
        if not lineas_sin:
            continue

        firma = lineas_sin[0].strip()
        if not firma:
            continue

        lineas_chunk = chunk_content.splitlines()
        offset = len(lineas_chunk) - len(lineas_sin)
        linea = int(chk.get("line", 1)) + offset

        if not nombre:
            m_nom, m_kind = chunker.extract_symbol_and_kind(sin_comentarios, "")
            if m_nom:
                nombre = m_nom
                tipo = m_kind
            else:
                continue

        # Evitar duplicar firmas en fragmentos contiguos del mismo símbolo largo
        if resultado and resultado[-1][2] == nombre and resultado[-1][1] == tipo:
            continue

        resultado.append((linea, tipo, nombre, firma))

    return resultado


def resolver_definidor_local(
    source: str,
    fp_imp_str: str,
    definidores: Set[str],
    archivos_map_norm: Dict[str, str],
    alias_cache: Optional[Dict[str, List[str]]] = None,
    raiz_norm: Optional[str] = None,
) -> Optional[str]:
    """Resuelve la fuente de un import a un archivo local del proyecto que define el símbolo.
    Si la fuente es un paquete externo (vitest, react, etc.) o no se puede resolver unívocamente,
    devuelve None para evitar aristas falsas.
    Usa normalización de cadenas pura para máxima velocidad sin llamadas al sistema de archivos.
    """
    if not source or not definidores:
        return None

    es_python = fp_imp_str.endswith(".py")
    dir_imp = os.path.dirname(fp_imp_str)

    # Caso 1: Import relativo explícito (./ o ../ en JS/TS, . en Python)
    if source.startswith("."):
        if es_python:
            num_dots = len(source) - len(source.lstrip("."))
            resto = source.lstrip(".")
            base = dir_imp
            for _ in range(num_dots - 1):
                base = os.path.dirname(base)
            part_path = resto.replace(".", "/") if resto else ""
            target = os.path.normpath(os.path.join(base, part_path)).replace("\\", "/")
            cands = {target, target + ".py", target + "/__init__.py"}
        else:
            target = os.path.normpath(os.path.join(dir_imp, source)).replace("\\", "/")
            cands = {target}
            for ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".d.ts"):
                cands.add(target + ext)
                cands.add(target + "/index" + ext)

        coincs = [d for d in definidores if archivos_map_norm.get(d) in cands]
        if len(coincs) == 1:
            return coincs[0]
        if len(coincs) > 1:
            return coincs[0]
        return None

    # Caso 2: Alias de tsconfig/jsconfig (@/, ~/, #/ o paths) en JS/TS
    if not es_python:
        if alias_cache is not None:
            alias_list = alias_cache.get(dir_imp)
            if alias_list is None:
                alias_list = _alias_locales(Path(fp_imp_str)) or []
                alias_cache[dir_imp] = alias_list
        else:
            alias_list = _alias_locales(Path(fp_imp_str)) or []

        prefijos = [a for a in alias_list if a] + ["@/", "~/", "#/"]
        es_alias = False
        sub_src = ""
        for p in prefijos:
            if p and source.startswith(p):
                es_alias = True
                sub_src = source[len(p):].strip("/")
                break
            elif p.endswith("/") and source.startswith(p.rstrip("/")):
                es_alias = True
                sub_src = source[len(p.rstrip("/")):].strip("/")
                break

        if es_alias and sub_src:
            sub_norm = sub_src.replace("\\", "/").lower()
            sub_stem = os.path.splitext(sub_norm)[0]
            coincs = []
            for d in definidores:
                d_fp = archivos_map_norm.get(d, "").lower()
                d_stem = os.path.splitext(d_fp)[0]
                if d_stem.endswith(sub_stem) or d_fp.endswith(sub_norm):
                    coincs.append(d)
            if len(coincs) == 1:
                return coincs[0]
            return None

        # Si en JS/TS no empieza con . ni es alias, es un paquete externo (vitest, react, etc.)
        return None

    # Caso 3: En Python, import no relativo (from paquete.modulo import x o import paquete.modulo)
    # Solo es local si paquete/modulo.py o paquete/modulo/__init__.py existe dentro del proyecto
    if es_python:
        part_path = source.replace(".", "/")
        coincs = []
        for d in definidores:
            d_fp = archivos_map_norm.get(d, "")
            if d_fp.endswith("/" + part_path + ".py") or d_fp.endswith("/" + part_path + "/__init__.py") or d_fp.endswith(part_path + ".py"):
                coincs.append(d)
        if len(coincs) == 1:
            return coincs[0]
        elif len(coincs) > 1 and raiz_norm:
            filtradas = [
                d for d in coincs
                if archivos_map_norm.get(d, "").startswith(raiz_norm)
                and (archivos_map_norm.get(d, "")[len(raiz_norm):].lstrip("/") in (part_path + ".py", part_path + "/__init__.py"))
            ]
            if len(filtradas) == 1:
                return filtradas[0]
        return None

    return None


def calcular_pagerank(
    archivos: List[str],
    out_links: Dict[str, Set[str]],
    in_links: Dict[str, Set[str]],
    foco: str = "",
    simbolos_por_archivo: Optional[Dict[str, Set[str]]] = None,
    d: float = 0.85,
    max_iter: int = 100,
    tol: float = 1e-6,
) -> Tuple[List[str], Dict[str, float]]:
    """PageRank por iteración de potencias en Python puro.
    Permite personalización hacia los nodos que coincidan con `foco`.
    """
    n = len(archivos)
    if n == 0:
        return [], {}
    if n == 1:
        return list(archivos), {archivos[0]: 1.0}

    foco_nodes: Set[str] = set()
    if foco:
        terminos = [t.strip().lower() for t in foco.split(",") if t.strip()]
        for f in archivos:
            f_norm = f.lower()
            f_name = Path(f).name.lower()
            syms = {s.lower() for s in (simbolos_por_archivo or {}).get(f, set())}
            for t in terminos:
                if t == f_name or t in f_norm or (t in syms):
                    foco_nodes.add(f)
                    break

    if foco_nodes:
        p = {v: (1.0 / len(foco_nodes) if v in foco_nodes else 0.0) for v in archivos}
    else:
        p = {v: 1.0 / n for v in archivos}

    r = dict(p)

    for _ in range(max_iter):
        dangling_sum = sum(r[u] for u in archivos if not out_links.get(u))
        r_new = {}
        for v in archivos:
            incoming = sum(r[u] / len(out_links[u]) for u in in_links.get(v, set()) if out_links.get(u))
            r_new[v] = (1.0 - d) * p[v] + d * dangling_sum * p[v] + d * incoming

        diff = sum(abs(r_new[v] - r[v]) for v in archivos)
        r = r_new
        if diff < tol:
            break

    ordenados = sorted(archivos, key=lambda v: (r[v], v), reverse=True)
    return ordenados, r


def mapa_del_repo(proyecto: str, foco: str = "", tokens: int = 1024) -> str:
    """Genera el mapa del repo con las firmas más relevantes según PageRank
    sobre el grafo de dependencias, dentro del presupuesto de tokens especificado.
    """
    db = indexer.get_db()
    tbl_name = indexer.TABLE_NAME

    has_tbl = False
    try:
        tables = db.list_tables()
        has_tbl = tbl_name in (tables.tables if hasattr(tables, "tables") else tables)
    except Exception:
        has_tbl = False

    if not has_tbl:
        return f"No hay proyectos indexados. Usa SYNRAG index primero."

    clean_proj = proyecto.replace("'", "")
    tbl_files = db.open_table(tbl_name)

    # Optimización: solo proyectar columnas necesarias (ahorro de E/S y memoria)
    filas_archivos = (
        tbl_files.search()
        .where(f"project = '{clean_proj}'")
        .select(["rel_path", "file_path", "symbol_name"])
        .limit(100000)
        .to_list()
    )
    if not filas_archivos:
        return f"No se encontraron archivos para el proyecto '{proyecto}'."

    archivos_map: Dict[str, str] = {}
    archivos_map_norm: Dict[str, str] = {}
    simbolos_a_archivos: Dict[str, Set[str]] = {}
    archivo_a_simbolos: Dict[str, Set[str]] = {}

    for row in filas_archivos:
        rel = row.get("rel_path")
        fp = row.get("file_path")
        sym = row.get("symbol_name")
        if rel and fp:
            archivos_map[rel] = fp
            archivos_map_norm[rel] = os.path.normpath(fp).replace("\\", "/")
            if sym:
                simbolos_a_archivos.setdefault(sym, set()).add(rel)
                archivo_a_simbolos.setdefault(rel, set()).add(sym)

    # Identificar la raíz del proyecto
    raiz = indexer.raiz_de_proyecto(proyecto)
    if not raiz and archivos_map:
        try:
            rutas_existentes = [str(Path(fp).resolve()) for fp in archivos_map.values() if Path(fp).is_file()]
            if rutas_existentes:
                comun = os.path.commonpath(rutas_existentes)
                if comun and os.path.isdir(comun):
                    raiz = Path(comun)
        except Exception:
            pass

    raiz_norm = os.path.normpath(str(raiz.resolve())).replace("\\", "/") if raiz else None

    archivos_lista = list(archivos_map.keys())
    out_links: Dict[str, Set[str]] = {v: set() for v in archivos_lista}
    in_links: Dict[str, Set[str]] = {v: set() for v in archivos_lista}
    alias_cache: Dict[str, List[str]] = {}

    has_impact = False
    try:
        tables = db.list_tables()
        has_impact = impact.IMPACT_TABLE in (tables.tables if hasattr(tables, "tables") else tables)
    except Exception:
        has_impact = False

    if has_impact:
        tbl_impact = db.open_table(impact.IMPACT_TABLE)
        filas_impact = (
            tbl_impact.search()
            .where(f"project = '{clean_proj}'")
            .select(["imported_by", "symbol", "source"])
            .limit(100000)
            .to_list()
        )
        # Resolucion como la de get_impact_radius (tsconfig, paquetes del monorepo, barrels); si no
        # llega a una definicion, la heuristica por nombre de archivo de siempre.
        resolutor = resolver.Resolutor(Path(raiz_norm) if raiz_norm else Path("/"), archivos_map_norm.values())
        abs_a_rel = {v: k for k, v in archivos_map_norm.items()}
        reexports: Dict[tuple, List[str]] = {}
        for r in filas_impact:
            reexports.setdefault((archivos_map_norm.get(r.get("imported_by")), r.get("symbol")), []).append(r.get("source", ""))

        def reexports_de(archivo: str, simbolo: str) -> List[str]:
            return reexports.get((archivo, simbolo), []) + reexports.get((archivo, "*"), [])

        for r in filas_impact:
            imported_by = r.get("imported_by")
            sym = r.get("symbol")
            source = r.get("source", "")
            if not imported_by or not sym or imported_by not in archivos_map_norm:
                continue

            definidores = simbolos_a_archivos.get(sym, set())
            if not definidores:
                continue

            fp_imp_str = archivos_map_norm[imported_by]
            definidor = None
            destino = resolutor.resolver(source, fp_imp_str)
            if destino:
                final = impact.destino_final(sym, destino, {archivos_map_norm[d] for d in definidores},
                                             reexports_de, resolutor)
                definidor = abs_a_rel.get(final) if final else None
            if definidor is None:
                definidor = resolver_definidor_local(
                    source=source,
                    fp_imp_str=fp_imp_str,
                    definidores=definidores,
                    archivos_map_norm=archivos_map_norm,
                    alias_cache=alias_cache,
                    raiz_norm=raiz_norm,
                )

            if definidor and definidor != imported_by:
                out_links[imported_by].add(definidor)
                in_links[definidor].add(imported_by)

    archivos_ordenados, _ = calcular_pagerank(
        archivos_lista,
        out_links=out_links,
        in_links=in_links,
        foco=foco,
        simbolos_por_archivo=archivo_a_simbolos,
    )

    lineas_salida: List[str] = []

    if raiz:
        linea_raiz = f"Raiz: {raiz.resolve()}"
        if (len(linea_raiz) + 3) // 4 <= tokens:
            lineas_salida.append(linea_raiz)

    for rel in archivos_ordenados:
        fp = archivos_map[rel]
        path_obj = Path(fp)
        if not path_obj.is_file():
            path_alt = Path.home() / rel
            if path_alt.is_file():
                path_obj = path_alt

        firmas = firmas_de_archivo(path_obj)
        if not firmas:
            continue

        if raiz:
            try:
                disp = str(path_obj.resolve().relative_to(raiz.resolve()))
            except Exception:
                disp = rel
        else:
            disp = rel
            for prefijo in (f"Proyectos/{proyecto}/", f"{proyecto}/"):
                if disp.startswith(prefijo):
                    disp = disp[len(prefijo):]
                    break

        bloque = [f"{disp}:"]
        for linea, _, _, firma in firmas:
            bloque.append(f"  L{linea} {firma}")

        bloque_incluido: List[str] = []
        for l in bloque:
            candidato = "\n".join(lineas_salida + bloque_incluido + [l])
            toks = (len(candidato) + 3) // 4
            if toks > tokens:
                break
            bloque_incluido.append(l)

        # Si solo entra la cabecera del archivo sin ninguna firma, omitirla
        if len(bloque_incluido) == 1 and len(bloque) > 1:
            break

        lineas_salida.extend(bloque_incluido)
        if len(bloque_incluido) < len(bloque):
            # Presupuesto alcanzado
            break

    return "\n".join(lineas_salida)
