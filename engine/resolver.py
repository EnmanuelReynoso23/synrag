"""
A que archivo apunta cada import: rutas relativas, alias de tsconfig/jsconfig (`paths` y `baseUrl`,
con `extends` y el tsconfig.app.json de Vite), paquetes del propio monorepo (package.json con
`name`) y modulos de Python (relativos, absolutos y con carpeta src/).

Sirve para que el grafo de impacto distinga dos simbolos con el mismo nombre y siga los barrels
(`index.ts` que re-exporta, `__init__.py`). No toca la red ni ejecuta nada: lee los tsconfig y
package.json del proyecto y comprueba contra la lista de archivos indexados.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

EXTS_JS = (".ts", ".tsx", ".d.ts", ".js", ".jsx", ".mjs", ".cjs")
CONFIGS_TS = ("tsconfig.json", "tsconfig.app.json", "jsconfig.json")


def _leer_json(ruta: Path) -> dict:
    """JSON con comentarios y comas finales (tsconfig); {} si no se puede leer."""
    try:
        texto = ruta.read_text(encoding="utf-8", errors="ignore")
        texto = re.sub(r'("(?:\\.|[^"\\])*")|//[^\n]*|/\*.*?\*/', lambda m: m.group(1) or "", texto, flags=re.S)
        return json.loads(re.sub(r",(\s*[}\]])", r"\1", texto)) or {}
    except Exception:
        return {}


class Resolutor:
    """Resuelve imports dentro de un proyecto. `archivos`: rutas absolutas de los archivos indexados."""

    def __init__(self, raiz: Path, archivos: Iterable[str]):
        self.raiz = os.path.normpath(str(raiz))
        self.archivos = {os.path.normpath(a) for a in archivos}
        self._cfg: Dict[str, Optional[Tuple[str, Dict[str, List[str]], bool]]] = {}
        self._paquetes: Optional[Dict[str, Tuple[str, dict]]] = None

    # ---------- utilidades ----------
    def _probar(self, base: str) -> Optional[str]:
        """El archivo que TypeScript/Node elegiria para `base`: tal cual, con extension o index."""
        base = os.path.normpath(base)
        if base in self.archivos:
            return base
        raiz, ext = os.path.splitext(base)
        if ext in (".js", ".jsx", ".mjs", ".cjs"):  # ESM con TypeScript: './x.js' es x.ts
            for e in (".ts", ".tsx", ".mts", ".cts"):
                if raiz + e in self.archivos:
                    return raiz + e
        for e in EXTS_JS:
            if base + e in self.archivos:
                return base + e
        for e in EXTS_JS:
            cand = os.path.join(base, "index" + e)
            if cand in self.archivos:
                return cand
        return None

    def _config_de(self, carpeta: str) -> Optional[Tuple[str, Dict[str, List[str]], bool]]:
        """(base de los paths, paths, hay_baseUrl) del tsconfig/jsconfig mas cercano hasta la raiz."""
        if carpeta in self._cfg:
            return self._cfg[carpeta]
        res = None
        for nombre in CONFIGS_TS:
            ruta = Path(carpeta) / nombre
            if ruta.is_file():
                res = self._opciones(ruta, 0)
                if res and res[1]:
                    break
        if res is None or not (res[1] or res[2]):
            padre = os.path.dirname(carpeta)
            sube = carpeta != self.raiz and padre != carpeta and padre.startswith(self.raiz)
            res = self._config_de(padre) if sube else None
        self._cfg[carpeta] = res
        return res

    def _opciones(self, ruta: Path, nivel: int) -> Optional[Tuple[str, Dict[str, List[str]], bool]]:
        cfg = _leer_json(ruta)
        opciones = cfg.get("compilerOptions") or {}
        heredado = None
        ext = cfg.get("extends")
        if isinstance(ext, str) and ext.startswith(".") and nivel < 4:
            destino = (ruta.parent / ext)
            destino = destino if destino.suffix == ".json" else destino.with_name(destino.name + ".json")
            if destino.is_file():
                heredado = self._opciones(destino, nivel + 1)
        paths = opciones.get("paths")
        base_url = opciones.get("baseUrl")
        if paths is None and heredado:
            # Hereda paths con su base original
            return heredado if not base_url else (os.path.normpath(str(ruta.parent / base_url)), heredado[1], True)
        if paths is None and base_url is None:
            return heredado
        base = os.path.normpath(str(ruta.parent / base_url)) if base_url else str(ruta.parent)
        return base, {k: v for k, v in (paths or {}).items() if isinstance(v, list)}, base_url is not None

    def _paquetes_locales(self) -> Dict[str, Tuple[str, dict]]:
        """Paquetes del monorepo por su `name` (apps/*, packages/*...): nombre -> (carpeta, package.json)."""
        if self._paquetes is None:
            self._paquetes = {}
            for patron in ("package.json", "*/package.json", "*/*/package.json", "*/*/*/package.json"):
                for pj in Path(self.raiz).glob(patron):
                    if "node_modules" in pj.parts:
                        continue
                    datos = _leer_json(pj)
                    if isinstance(datos.get("name"), str):
                        self._paquetes.setdefault(datos["name"], (str(pj.parent), datos))
        return self._paquetes

    def _entrada_paquete(self, carpeta: str, datos: dict, sub: str) -> Optional[str]:
        exports = datos.get("exports")
        clave = "./" + sub if sub else "."
        if isinstance(exports, dict) and clave in exports:
            destino = exports[clave]
            if isinstance(destino, dict):
                destino = destino.get("types") or destino.get("import") or destino.get("default") or ""
            if isinstance(destino, str):
                encontrado = self._probar(os.path.join(carpeta, destino))
                if encontrado:
                    return encontrado
        if isinstance(exports, str) and not sub:
            encontrado = self._probar(os.path.join(carpeta, exports))
            if encontrado:
                return encontrado
        if not sub:
            for campo in ("types", "typings", "module", "main"):
                if isinstance(datos.get(campo), str):
                    encontrado = self._probar(os.path.join(carpeta, datos[campo]))
                    if encontrado:
                        return encontrado
            # dist/ no se indexa: la fuente suele estar en src/index
            return self._probar(os.path.join(carpeta, "src", "index")) or self._probar(os.path.join(carpeta, "index"))
        return self._probar(os.path.join(carpeta, sub)) or self._probar(os.path.join(carpeta, "src", sub))

    # ---------- resolucion ----------
    def resolver(self, source: str, importador: str) -> Optional[str]:
        """Ruta absoluta del archivo local al que apunta `source` importado desde `importador`,
        o None si es un paquete externo o no se puede resolver."""
        if not source:
            return None
        importador = os.path.normpath(importador)
        if importador.endswith(".py"):
            return self._resolver_python(source, importador)
        carpeta = os.path.dirname(importador)
        if source.startswith("."):
            return self._probar(os.path.join(carpeta, source))
        cfg = self._config_de(carpeta)
        if cfg:
            base, paths, hay_base_url = cfg
            for patron, destinos in paths.items():
                if "*" in patron:
                    pre, _, suf = patron.partition("*")
                    if not (source.startswith(pre) and source.endswith(suf) and len(source) >= len(pre) + len(suf)):
                        continue
                    estrella = source[len(pre):len(source) - len(suf)]
                elif source == patron:
                    estrella = ""
                else:
                    continue
                for d in destinos:
                    encontrado = self._probar(os.path.join(base, d.replace("*", estrella)))
                    if encontrado:
                        return encontrado
            if hay_base_url:
                encontrado = self._probar(os.path.join(base, source))
                if encontrado:
                    return encontrado
        partes = source.split("/")
        nombre = "/".join(partes[:2]) if source.startswith("@") else partes[0]
        paquete = self._paquetes_locales().get(nombre)
        if paquete:
            return self._entrada_paquete(paquete[0], paquete[1], source[len(nombre):].strip("/"))
        return None

    def _resolver_python(self, source: str, importador: str) -> Optional[str]:
        def probar_py(base: str) -> Optional[str]:
            for cand in (base + ".py", os.path.join(base, "__init__.py")):
                if os.path.normpath(cand) in self.archivos:
                    return os.path.normpath(cand)
            return None

        if source.startswith("."):
            puntos = len(source) - len(source.lstrip("."))
            base = os.path.dirname(importador)
            for _ in range(puntos - 1):
                base = os.path.dirname(base)
            resto = source.lstrip(".")
            return probar_py(os.path.join(base, *resto.split("."))) if resto else probar_py(base)
        ruta = os.path.join(*source.split("."))
        raices = [self.raiz, os.path.join(self.raiz, "src")]
        carpeta = os.path.dirname(importador)
        while carpeta.startswith(self.raiz) and carpeta not in raices:  # scripts que importan a sus vecinos
            raices.append(carpeta)
            carpeta = os.path.dirname(carpeta)
        for r in raices:
            encontrado = probar_py(os.path.join(r, ruta))
            if encontrado:
                return encontrado
        return None
