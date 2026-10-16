"""Resolucion de imports (alias de tsconfig, paquetes del monorepo, barrels, Python) y el grafo de
impacto que separa dos definiciones con el mismo nombre."""
import json
from pathlib import Path

import resolver
from conftest import crear_proyecto


def _resolutor(raiz: Path) -> resolver.Resolutor:
    return resolver.Resolutor(raiz, [str(p) for p in raiz.rglob("*") if p.is_file()])


def test_relativos_alias_extends_y_tsconfig_app_de_vite(tmp_path):
    raiz = tmp_path / "web"
    for rel in ("src/utils/fecha.ts", "src/modulos/index.ts", "src/x.ts", "src/componentes/Boton.tsx"):
        (raiz / rel).parent.mkdir(parents=True, exist_ok=True)
        (raiz / rel).write_text("export const a = 1\n")
    # Vite: tsconfig.json solo con references; los paths estan en tsconfig.app.json, que hereda la base
    (raiz / "tsconfig.json").write_text('{ "files": [], "references": [{ "path": "./tsconfig.app.json" }] }')
    (raiz / "tsconfig.base.json").write_text('{\n  // comentario\n  "compilerOptions": { "paths": { "@/*": ["./src/*"], }, },\n}')
    (raiz / "tsconfig.app.json").write_text('{ "extends": "./tsconfig.base.json", "compilerOptions": { "strict": true } }')
    r = _resolutor(raiz)
    imp = str(raiz / "src" / "x.ts")
    assert r.resolver("./utils/fecha", imp) == str(raiz / "src/utils/fecha.ts")
    assert r.resolver("./utils/fecha.js", imp) == str(raiz / "src/utils/fecha.ts")  # ESM con TypeScript
    assert r.resolver("@/modulos", imp) == str(raiz / "src/modulos/index.ts")
    assert r.resolver("@/componentes/Boton", imp) == str(raiz / "src/componentes/Boton.tsx")
    assert r.resolver("react", imp) is None


def test_paquete_del_monorepo_por_su_nombre(tmp_path):
    raiz = tmp_path / "mono"
    (raiz / "packages/auth/src/hooks").mkdir(parents=True)
    (raiz / "packages/auth/src/index.ts").write_text("export * from './hooks/useAuth'\n")
    (raiz / "packages/auth/src/hooks/useAuth.ts").write_text("export function useAuth() {}\n")
    (raiz / "packages/auth/package.json").write_text(json.dumps({"name": "@mono/auth", "main": "dist/index.js"}))
    (raiz / "apps/web/src").mkdir(parents=True)
    (raiz / "apps/web/src/App.tsx").write_text("import { useAuth } from '@mono/auth'\n")
    r = _resolutor(raiz)
    imp = str(raiz / "apps/web/src/App.tsx")
    assert r.resolver("@mono/auth", imp) == str(raiz / "packages/auth/src/index.ts")  # dist/ no se indexa
    assert r.resolver("@mono/auth/hooks/useAuth", imp) == str(raiz / "packages/auth/src/hooks/useAuth.ts")


def test_python_relativo_absoluto_y_src(tmp_path):
    raiz = tmp_path / "py"
    for rel in ("src/paquete/__init__.py", "src/paquete/app.py", "src/paquete/sub/mod.py", "scripts/util.py", "scripts/run.py"):
        (raiz / rel).parent.mkdir(parents=True, exist_ok=True)
        (raiz / rel).write_text("x = 1\n")
    r = _resolutor(raiz)
    assert r.resolver(".app", str(raiz / "src/paquete/__init__.py")) == str(raiz / "src/paquete/app.py")
    assert r.resolver("..app", str(raiz / "src/paquete/sub/mod.py")) == str(raiz / "src/paquete/app.py")
    assert r.resolver("paquete.sub.mod", str(raiz / "scripts/run.py")) == str(raiz / "src/paquete/sub/mod.py")
    assert r.resolver("paquete", str(raiz / "scripts/run.py")) == str(raiz / "src/paquete/__init__.py")
    assert r.resolver("util", str(raiz / "scripts/run.py")) == str(raiz / "scripts/util.py")
    assert r.resolver("json", str(raiz / "scripts/run.py")) is None


def test_impacto_separa_definiciones_y_sigue_barrels(casa):
    crear_proyecto(casa, "mono", {
        "tsconfig.json": '{"compilerOptions": {"paths": {"@/*": ["./web/*"]}}}',
        "web/hooks/useAuth.ts": "export function useAuth() {\n  return 1\n}\n",
        "web/Home.tsx": "import { useAuth } from '@/hooks/useAuth'\nexport function Home() {\n  return useAuth()\n}\n",
        "auth/src/useAuth.ts": "export function useAuth() {\n  return 2\n}\n",
        "auth/src/index.ts": "export { useAuth } from './useAuth'\n",
        "auth/package.json": '{"name": "@mono/auth"}',
        "web/Panel.tsx": "import {\n  useAuth,\n} from '@mono/auth'\nexport const Panel = () => useAuth()\n",
        "web/Otro.tsx": "import { useAuth } from 'libreria-externa'\nexport const Otro = 1\n",
    })
    import indexer
    import server_mcp
    indexer._RESOLUTORES.clear()
    indexer.index_desktop()
    datos = indexer.consumidores("useAuth", "mono")
    defs = {Path(d).relative_to(casa / "Proyectos/mono").as_posix(): sorted(Path(u).name for u in v)
            for d, v in datos["definiciones"].items()}
    # el barrel (index.ts) tambien depende: si se renombra useAuth, se rompe
    assert defs == {"web/hooks/useAuth.ts": ["Home.tsx"], "auth/src/useAuth.ts": ["Panel.tsx", "index.ts"]}
    assert datos["externos"] == {"libreria-externa": 1}

    salida = server_mcp.get_impact_radius("useAuth", "mono", archivo="auth/src/useAuth.ts")
    assert "Panel.tsx" in salida and "Home.tsx" not in salida

    busqueda = server_mcp.search_desktop("useAuth", project="mono")
    usos = next(l for l in busqueda.splitlines() if l.startswith("Usos"))
    assert "lo importan 1 archivo(s)" in usos or "lo importan 2 archivo(s)" in usos
    assert ("Home.tsx:3 Home" in usos) != ("Panel.tsx:4 Panel" in usos)  # solo los de SU definicion
    assert "Panel.tsx:2" not in usos  # la linea `  useAuth,` del import de varias lineas no es un uso
