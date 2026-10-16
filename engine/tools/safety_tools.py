"""
tools/safety_tools.py - Herramientas de prevencion de errores y dependencias rotas.
Evitan ciclos de prueba y error asegurando que las dependencias existan, que no haya ciclos
y que los cambios en firmas no rompan llamadas existentes.
"""

import os
import sys
import json
import re
import ast
import difflib
import fnmatch
import subprocess
import time
from pathlib import Path
from typing import Optional, List, Set, Dict, Any, Tuple
from collections import deque

import indexer

# Modulos estandar de Node.js
NODE_BUILTINS = {
    "assert", "async_hooks", "buffer", "child_process", "cluster", "console",
    "constants", "crypto", "dgram", "diagnostics_channel", "dns", "domain",
    "events", "fs", "fs/promises", "http", "http2", "https", "inspector",
    "module", "net", "os", "path", "path/posix", "path/win32", "perf_hooks",
    "process", "punycode", "querystring", "readline", "readline/promises",
    "repl", "stream", "stream/consumers", "stream/promises", "stream/web",
    "string_decoder", "sys", "timers", "timers/promises", "tls", "trace_events",
    "tty", "url", "util", "util/types", "v8", "vm", "wasi", "worker_threads",
    "zlib", "test"
}

# Mapeo de modulos populares de Python donde el nombre importado difiere del paquete en PyPI
PYTHON_PACKAGE_MAP = {
    "dotenv": "python-dotenv",
    "yaml": "pyyaml",
    "pil": "pillow",
    "bs4": "beautifulsoup4",
    "sklearn": "scikit-learn",
    "cv2": "opencv-python",
    "dateutil": "python-dateutil",
    "jwt": "pyjwt",
    "serial": "pyserial",
}

IGNORED_WORKSPACE_DIRS = {
    "node_modules", ".git", ".venv", "venv", "__pycache__", "dist", "build",
    ".next", ".turbo", "coverage", ".cache", "target", "obj", ".idea", ".vscode",
    "pnpm-store", ".pnpm", ".pnpm-store"
}


def _resolve_project_dir(project_dir: str = "") -> Path:
    if project_dir:
        raiz = indexer.raiz_de_proyecto(project_dir)
        if raiz and raiz.is_dir():
            return raiz
        p = Path(project_dir).expanduser().resolve()
        if p.exists():
            return p if p.is_dir() else p.parent
    return Path.cwd()


def _resolve_project_dir_and_file(project_dir: str = "", desde_archivo: str = "") -> Tuple[Path, Optional[Path]]:
    p_desde = None
    if desde_archivo:
        p_d = Path(desde_archivo).expanduser()
        if p_d.is_absolute() and p_d.exists():
            p_desde = p_d.resolve()

    if project_dir:
        p_dir = Path(project_dir).expanduser()
        if p_dir.is_file():
            p_desde = p_dir.resolve()
            return _find_root(p_desde), p_desde

        raiz = indexer.raiz_de_proyecto(project_dir)
        if raiz and raiz.is_dir():
            target = raiz
        else:
            p = Path(project_dir).expanduser().resolve()
            target = p if p.is_dir() else p.parent
    else:
        target = Path.cwd()

    if p_desde is None and desde_archivo:
        cand = (target / Path(desde_archivo).expanduser()).resolve()
        if cand.exists():
            p_desde = cand

    return target, p_desde


def _find_root(path: Path) -> Path:
    curr = path if path.is_dir() else path.parent
    for _ in range(15):
        if (curr / ".git").exists() or (curr / "pyproject.toml").exists() or (curr / "package.json").exists() or (curr / "setup.py").exists() or (curr / "pnpm-workspace.yaml").exists() or (curr / "Cargo.toml").exists():
            return curr
        if curr.parent == curr:
            break
        curr = curr.parent
    return path if path.is_dir() else path.parent


_EXCLUIR_BUSQUEDA = ("node_modules", ".venv", ".git", "dist", "build")


def _archivos_de_busqueda(raiz: Path, excluir_archivos: Tuple[str, ...]):
    if raiz.is_file():
        yield raiz
        return
    for base, dirs, nombres in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in _EXCLUIR_BUSQUEDA and not d.startswith(".")]
        for n in nombres:
            if not n.startswith(".") and not any(fnmatch.fnmatch(n, g) for g in excluir_archivos):
                yield Path(base) / n


def _buscar_lineas(patron: str, raiz: Path, excluir_archivos: Tuple[str, ...] = (), timeout: float = 8) -> List[str]:
    """Lineas 'ruta:linea:texto' que cumplen `patron`: con ripgrep si esta instalado y, si no, en Python."""
    globs = [a for x in _EXCLUIR_BUSQUEDA + excluir_archivos for a in ("-g", f"!{x}")]
    try:
        res = subprocess.run(["rg", "-n", "--no-heading", "-H", *globs, "-e", patron, str(raiz)],
                             capture_output=True, text=True, timeout=timeout)
        return [l for l in res.stdout.splitlines() if l.strip()]
    except FileNotFoundError:  # sin ripgrep instalado
        pass
    regex = re.compile(patron)
    limite = time.monotonic() + timeout
    lineas = []
    for f in _archivos_de_busqueda(raiz, excluir_archivos):
        if time.monotonic() > limite:
            break
        try:
            if f.stat().st_size > 5_000_000:
                continue
            datos = f.read_bytes()
        except OSError:
            continue
        if b"\0" in datos[:8192]:  # binario: ripgrep tambien lo salta
            continue
        for i, linea in enumerate(datos.decode("utf-8", errors="ignore").splitlines(), 1):
            if regex.search(linea):
                lineas.append(f"{f}:{i}:{linea}")
    return lineas


def _find_workspace_manifests(target: Path, manifest_name: str, max_depth: int = 4) -> List[Path]:
    manifests = []
    root_manifest = target / manifest_name
    if root_manifest.is_file():
        manifests.append(root_manifest)

    stack = [(target, 0)]
    while stack:
        curr, depth = stack.pop()
        if depth >= max_depth:
            continue
        try:
            with os.scandir(curr) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name not in IGNORED_WORKSPACE_DIRS and not entry.name.startswith("."):
                            stack.append((Path(entry.path), depth + 1))
                    elif entry.is_file(follow_symlinks=False) and entry.name == manifest_name:
                        p = Path(entry.path)
                        if p != root_manifest and p not in manifests:
                            manifests.append(p)
        except (PermissionError, OSError):
            continue
    return manifests


def _order_manifests(manifests: List[Path], target: Path, desde_path: Optional[Path] = None) -> List[Path]:
    if not desde_path:
        return manifests
    prioritarios = []
    curr = desde_path.parent if desde_path.is_file() else desde_path
    while curr != target.parent:
        for m in manifests:
            if m.parent == curr and m not in prioritarios:
                prioritarios.append(m)
        if curr == target or curr.parent == curr:
            break
        curr = curr.parent
    return prioritarios + [m for m in manifests if m not in prioritarios]


def _parse_jsonc(text: str) -> dict:
    """Parsea JSON permitiendo comentarios y comas finales."""
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    lineas = []
    for l in text.splitlines():
        m = re.match(r'^(.*?)(?<!:)\/\/(.*)$', l)
        if m and '"' not in m.group(2):
            lineas.append(m.group(1))
        else:
            lineas.append(l)
    limpio = "\n".join(lineas)
    limpio = re.sub(r',\s*([}\]])', r'\1', limpio)
    return json.loads(limpio)


def _buscar_alias_tsconfig(target: Path, dep: str, desde_path: Optional[Path] = None) -> Optional[str]:
    """Comprueba si dep coincide con un alias configurado en tsconfig*.json o jsconfig*.json."""
    candidatos = list(target.glob("tsconfig*.json")) + list(target.glob("jsconfig*.json"))
    if desde_path:
        curr = desde_path.parent if desde_path.is_file() else desde_path
        while curr != target.parent:
            for tc in list(curr.glob("tsconfig*.json")) + list(curr.glob("jsconfig*.json")):
                if tc not in candidatos:
                    candidatos.insert(0, tc)
            if curr == target or curr.parent == curr:
                break
            curr = curr.parent

    for tc in candidatos:
        try:
            data = _parse_jsonc(tc.read_text(encoding="utf-8", errors="replace"))
            compiler_opts = data.get("compilerOptions", {})
            paths = compiler_opts.get("paths", {})
            for pattern in paths:
                if pattern.endswith("/*"):
                    prefix = pattern[:-2]
                    if dep.startswith(prefix + "/") or dep == prefix:
                        return pattern
                elif pattern.endswith("*"):
                    prefix = pattern[:-1]
                    if dep.startswith(prefix):
                        return pattern
                elif pattern == dep:
                    return pattern
        except Exception:
            continue
    return None


def verify_dependency_exists(dependency_name: str, project_dir: str = "", desde_archivo: str = "") -> str:
    """Comprueba si un paquete o dependencia existe en el proyecto o workspace antes de importarlo."""
    target, p_desde = _resolve_project_dir_and_file(project_dir, desde_archivo)
    clean_dep = dependency_name.strip().strip("'\"")
    if not clean_dep:
        return "[SynRAG Dep ALERTA] Nombre de dependencia vacío."

    has_node = (target / "package.json").is_file() or (target / "pnpm-workspace.yaml").is_file() or clean_dep.startswith("node:") or clean_dep.startswith("@")
    has_py = (target / "pyproject.toml").is_file() or (target / "requirements.txt").is_file() or (target / "setup.py").is_file() or (target / "setup.cfg").is_file()

    # Si es claramente un proyecto Python y no Node, evaluar Python primero
    priorizar_python = has_py and not (target / "package.json").is_file() and not (target / "pnpm-workspace.yaml").is_file()

    if priorizar_python:
        res_py = _check_python_dependency(clean_dep, target, p_desde)
        if res_py:
            return res_py

    # Evaluar Node.js builtins
    dep_lower = clean_dep.lower()
    if dep_lower.startswith("node:"):
        mod = dep_lower[5:]
        if mod in NODE_BUILTINS or "/" in mod:
            return f"[SynRAG Dep OK] '{clean_dep}' es un módulo estándar de Node.js (builtin)."
    if dep_lower in NODE_BUILTINS and not priorizar_python:
        return f"[SynRAG Dep OK] '{clean_dep}' es un módulo estándar de Node.js (builtin)."

    # Extraer paquete raiz para subpaths (@scope/pkg/sub -> @scope/pkg, lodash/get -> lodash)
    if clean_dep.startswith("@"):
        partes = clean_dep.split("/")
        root_pkg = "/".join(partes[:2]) if len(partes) >= 2 else clean_dep
    else:
        root_pkg = clean_dep.split("/")[0]

    # Buscar en manifiestos de Node.js (monorepo / workspaces: pnpm, npm, yarn)
    all_pkg_jsons = _find_workspace_manifests(target, "package.json")
    ordered_pkg_jsons = _order_manifests(all_pkg_jsons, target, p_desde)

    if ordered_pkg_jsons:
        for pkg_file in ordered_pkg_jsons:
            try:
                data = json.loads(pkg_file.read_text(encoding="utf-8"))
                for seccion in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                    deps = data.get(seccion, {})
                    rel_path = pkg_file.relative_to(target)
                    if clean_dep in deps:
                        return f"[SynRAG Dep OK] '{clean_dep}' encontrada en {rel_path} ({seccion}: {deps[clean_dep]})."
                    if root_pkg != clean_dep and root_pkg in deps:
                        return f"[SynRAG Dep OK] '{clean_dep}' pertenece al paquete '{root_pkg}' declarado en {rel_path} ({seccion}: {deps[root_pkg]})."
            except Exception:
                continue

        # Comprobar node_modules (raiz y de cada paquete del workspace)
        for pkg_file in ordered_pkg_jsons:
            node_mods = pkg_file.parent / "node_modules" / clean_dep
            node_mods_root = pkg_file.parent / "node_modules" / root_pkg
            if node_mods.exists() or node_mods_root.exists():
                found_nm = node_mods if node_mods.exists() else node_mods_root
                rel_nm = found_nm.relative_to(target)
                return f"[SynRAG Dep OK] '{clean_dep}' está instalada en {rel_nm}."

        alias = _buscar_alias_tsconfig(target, clean_dep, p_desde)
        if alias:
            return f"[SynRAG Dep OK] '{clean_dep}' resuelto mediante alias de tsconfig ('{alias}')."

        total_pkgs = len(ordered_pkg_jsons)
        extra_info = f" (revisados {total_pkgs} paquetes del workspace)" if total_pkgs > 1 else ""
        return f"[SynRAG Dep ALERTA] '{clean_dep}' NO figura en package.json ni en node_modules de '{target.name}'{extra_info}. Debe instalarse antes de importarla."

    alias = _buscar_alias_tsconfig(target, clean_dep, p_desde)
    if alias:
        return f"[SynRAG Dep OK] '{clean_dep}' resuelto mediante alias de tsconfig ('{alias}')."

    # Si no se priorizo antes, evaluar Python ahora
    if not priorizar_python:
        res_py = _check_python_dependency(clean_dep, target, p_desde)
        if res_py:
            return res_py

    # Comprobar Cargo (Rust workspace)
    all_cargo = _find_workspace_manifests(target, "Cargo.toml")
    if all_cargo:
        ordered_cargo = _order_manifests(all_cargo, target, p_desde)
        for c in ordered_cargo:
            try:
                content = c.read_text(encoding="utf-8", errors="replace")
                if re.search(rf'^\s*{re.escape(clean_dep)}\s*=', content, re.MULTILINE | re.IGNORECASE):
                    rel_path = c.relative_to(target)
                    return f"[SynRAG Dep OK] Paquete Rust '{clean_dep}' declarado en {rel_path}."
            except Exception:
                pass

    return f"[SynRAG Dep] No se encontró manifest de dependencias (package.json/requirements.txt) en '{target}'."


def _check_python_dependency(clean_dep: str, target: Path, desde_path: Optional[Path] = None) -> Optional[str]:
    dep_root = clean_dep.split(".")[0]
    stdlib_modules = getattr(sys, "stdlib_module_names", None)
    if stdlib_modules is None:
        stdlib_modules = {
            "os", "sys", "re", "json", "ast", "math", "time", "datetime", "pathlib",
            "typing", "collections", "itertools", "functools", "subprocess", "shutil",
            "tempfile", "io", "string", "hashlib", "random", "logging", "threading",
            "multiprocessing", "queue", "socket", "http", "urllib", "email", "unittest",
            "doctest", "difflib", "inspect", "importlib", "traceback", "gc", "contextlib",
            "csv", "sqlite3", "copy", "struct", "pickle", "gzip", "tarfile", "zipfile",
        }
    if dep_root.lower() in {m.lower() for m in stdlib_modules}:
        return f"[SynRAG Dep OK] '{clean_dep}' es un módulo estándar de Python (stdlib)."

    manifests = []
    for m_name in ("pyproject.toml", "requirements.txt", "setup.cfg", "setup.py", "Pipfile", "uv.lock", "poetry.lock"):
        manifests.extend(_find_workspace_manifests(target, m_name))
    manifests.extend(list(target.glob("*requirements*.txt")))

    ordered_manifests = _order_manifests(manifests, target, desde_path)
    manifests_existentes = [m for m in ordered_manifests if m.is_file()]

    if manifests_existentes:
        candidatos_nombres = {clean_dep.lower(), dep_root.lower()}
        norm_dep = re.sub(r"[-_.]+", "-", clean_dep).lower()
        norm_root = re.sub(r"[-_.]+", "-", dep_root).lower()
        candidatos_nombres.add(norm_dep)
        candidatos_nombres.add(norm_root)
        candidatos_nombres.add(norm_dep.replace("-", "_"))
        candidatos_nombres.add(norm_root.replace("-", "_"))
        if dep_root.lower() in PYTHON_PACKAGE_MAP:
            mapped = PYTHON_PACKAGE_MAP[dep_root.lower()]
            candidatos_nombres.add(mapped)
            candidatos_nombres.add(re.sub(r"[-_.]+", "-", mapped))

        encontrada = False
        fuente = ""
        for m in manifests_existentes:
            try:
                contenido = m.read_text(encoding="utf-8", errors="replace")
                for c in candidatos_nombres:
                    if re.search(rf'["\'\s]?\b{re.escape(c)}\b(?:[=><~\[;]|\s*["\']|\s*$)', contenido, re.IGNORECASE | re.MULTILINE):
                        encontrada = True
                        fuente = str(m.relative_to(target))
                        break
                if encontrada:
                    break
            except Exception:
                continue

        if not encontrada:
            if (target / dep_root).is_dir() or (target / "src" / dep_root).is_dir() or (target / f"{dep_root}.py").is_file():
                return f"[SynRAG Dep OK] '{clean_dep}' es un módulo local del proyecto '{target.name}'."

        if encontrada:
            return f"[SynRAG Dep OK] Paquete Python '{clean_dep}' declarado en {fuente}."
        return f"[SynRAG Dep ALERTA] Paquete Python '{clean_dep}' NO figura en requirements.txt ni pyproject.toml."

    return None


def _resolve_py_module(mod_name: str, dir_path: Path, project_root: Path) -> Optional[Path]:
    if not mod_name:
        return None
    partes = mod_name.split(".")
    bases = [dir_path, project_root, project_root / "src"]
    for base in bases:
        cand_file = base.joinpath(*partes).with_suffix(".py")
        if cand_file.is_file():
            return cand_file.resolve()
        cand_init = base.joinpath(*partes) / "__init__.py"
        if cand_init.is_file():
            return cand_init.resolve()
    return None


def _get_python_imports(file_path: Path, project_root: Path) -> Set[Path]:
    imported_files = set()
    dir_path = file_path.parent
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(file_path))
    except Exception:
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r'^\s*(?:from\s+([.\w]+)\s+import|import\s+([\w.]+))', content, re.MULTILINE):
                mod = m.group(1) or m.group(2)
                if mod:
                    r = _resolve_py_module(mod.lstrip("."), dir_path, project_root)
                    if r:
                        imported_files.add(r)
        except Exception:
            pass
        return imported_files

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                r = _resolve_py_module(alias.name, dir_path, project_root)
                if r:
                    imported_files.add(r)
        elif isinstance(node, ast.ImportFrom):
            level = node.level or 0
            module = node.module or ""
            if level > 0:
                base_dir = dir_path
                for _ in range(level - 1):
                    base_dir = base_dir.parent
                if module:
                    mod_path = base_dir.joinpath(*module.split("."))
                    cand = mod_path.with_suffix(".py")
                    if cand.is_file():
                        imported_files.add(cand.resolve())
                    elif (mod_path / "__init__.py").is_file():
                        imported_files.add((mod_path / "__init__.py").resolve())
                else:
                    for alias in node.names:
                        cand = (base_dir / alias.name).with_suffix(".py")
                        if cand.is_file():
                            imported_files.add(cand.resolve())
                        cand_init = base_dir / alias.name / "__init__.py"
                        if cand_init.is_file():
                            imported_files.add(cand_init.resolve())
            else:
                r = _resolve_py_module(module, dir_path, project_root)
                if r:
                    imported_files.add(r)
                else:
                    for alias in node.names:
                        sub = f"{module}.{alias.name}" if module else alias.name
                        r_sub = _resolve_py_module(sub, dir_path, project_root)
                        if r_sub:
                            imported_files.add(r_sub)
    return imported_files


def _resolve_js_file(base: Path) -> Optional[Path]:
    for ext in ("", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
        cand = base if not ext else base.with_suffix(ext)
        if cand.is_file():
            return cand.resolve()
    for index_name in ("index.ts", "index.tsx", "index.js", "index.jsx"):
        cand = base / index_name
        if cand.is_file():
            return cand.resolve()
    return None


def _resolve_tsconfig_path(project_root: Path, specifier: str) -> Optional[Path]:
    candidatos = list(project_root.glob("tsconfig*.json")) + list(project_root.glob("jsconfig*.json"))
    for tc in candidatos:
        try:
            data = _parse_jsonc(tc.read_text(encoding="utf-8", errors="replace"))
            compiler_opts = data.get("compilerOptions", {})
            paths = compiler_opts.get("paths", {})
            for pattern, targets in paths.items():
                if pattern.endswith("/*"):
                    prefix = pattern[:-2]
                    if specifier.startswith(prefix + "/"):
                        sub = specifier[len(prefix) + 1:]
                        for t in targets:
                            t_clean = t.replace("/*", "")
                            cand_base = (tc.parent / t_clean / sub).resolve()
                            res = _resolve_js_file(cand_base)
                            if res:
                                return res
                elif pattern == specifier:
                    for t in targets:
                        cand_base = (tc.parent / t).resolve()
                        res = _resolve_js_file(cand_base)
                        if res:
                            return res
        except Exception:
            continue
    return None


def _get_js_ts_imports(file_path: Path, project_root: Path) -> Set[Path]:
    imported_files = set()
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return imported_files

    content_clean = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    content_clean = re.sub(r'//.*$', '', content_clean, flags=re.MULTILINE)

    patterns = [
        r'(?:import|export)\s+(?:.*?from\s+)?[\'"]([^\'"]+)[\'"]',
        r'require\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
        r'import\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
    ]
    specifiers = set()
    for pat in patterns:
        for m in re.finditer(pat, content_clean):
            specifiers.add(m.group(1))

    for spec in specifiers:
        if spec.startswith("."):
            cand_base = (file_path.parent / spec).resolve()
            res = _resolve_js_file(cand_base)
            if res:
                imported_files.add(res)
        else:
            res_alias = _resolve_tsconfig_path(project_root, spec)
            if res_alias:
                imported_files.add(res_alias)
    return imported_files


def _get_file_imports(file_path: Path, project_root: Path) -> Set[Path]:
    suffix = file_path.suffix.lower()
    if suffix in (".py", ".pyw"):
        return _get_python_imports(file_path, project_root)
    if suffix in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
        return _get_js_ts_imports(file_path, project_root)
    return set()


def check_circular_imports(file_a: str, file_b: str) -> str:
    """Comprueba si importar file_b desde file_a crearía un ciclo de dependencias directo o indirecto."""
    p_a = Path(file_a).resolve()
    p_b = Path(file_b).resolve()

    if not p_a.is_file():
        cand, _ = indexer.resolver_archivo(file_a)
        if cand and cand.is_file():
            p_a = cand
    if not p_b.is_file():
        cand, _ = indexer.resolver_archivo(file_b)
        if cand and cand.is_file():
            p_b = cand

    if not p_a.is_file() or not p_b.is_file():
        return f"[SynRAG Circular] Uno o ambos archivos no existen: '{file_a}', '{file_b}'."

    if p_a == p_b:
        return f"[SynRAG Circular DETECTADO] '{p_a.name}' no puede importarse a sí mismo (autociclo)."

    project_root = _find_root(p_a)

    try:
        queue = deque([(p_b, [p_b])])
        visited = {p_b}
        found_cycle_path = None

        while queue:
            curr, path = queue.popleft()
            if len(path) > 15:
                continue
            imports = _get_file_imports(curr, project_root)
            if p_a in imports:
                found_cycle_path = [p_a] + path + [p_a]
                break
            for imp in imports:
                if imp not in visited:
                    visited.add(imp)
                    queue.append((imp, path + [imp]))

        if found_cycle_path:
            secuencia = " -> ".join([f"'{f.name}'" for f in found_cycle_path])
            return (
                f"[SynRAG Circular DETECTADO] Ciclo detectado: {secuencia}. "
                f"Importar '{p_b.name}' dentro de '{p_a.name}' causará un ciclo de dependencias circular."
            )

        return f"[SynRAG Circular OK] Seguro: '{p_b.name}' no tiene referencias directas ni indirectas a '{p_a.name}'. No genera ciclo."

    except Exception as e:
        return f"[SynRAG Circular] Error al evaluar dependencia circular: {e}"


def _split_balanced(text: str, delimiter: str = ",") -> List[str]:
    """Divide un texto por un delimitador respetando parentesis, corchetes, llaves y comillas."""
    parts = []
    curr = []
    stack = []
    in_quote = None
    for char in text:
        if in_quote:
            curr.append(char)
            if char == in_quote:
                in_quote = None
        elif char in ('"', "'"):
            in_quote = char
            curr.append(char)
        elif char in ('(', '[', '{'):
            stack.append(char)
            curr.append(char)
        elif char == ')' and stack and stack[-1] == '(':
            stack.pop()
            curr.append(char)
        elif char == ']' and stack and stack[-1] == '[':
            stack.pop()
            curr.append(char)
        elif char == '}' and stack and stack[-1] == '{':
            stack.pop()
            curr.append(char)
        elif char == delimiter and not stack:
            parts.append("".join(curr).strip())
            curr = []
        else:
            curr.append(char)
    if curr:
        parts.append("".join(curr).strip())
    return [p for p in parts if p]


def _parse_params(new_params: str) -> Tuple[List[str], Set[str], int, int, bool, bool, bool]:
    """
    Parsea la nueva firma.
    Devuelve: (nombres_parametros, obligatorios, min_requeridos, max_posicionales, tiene_varargs, tiene_kwargs, es_metodo)
    """
    param_tokens = _split_balanced(new_params, ",")
    param_names = []
    required_names = set()
    has_varargs = False
    has_kwargs = False
    is_method = False

    for i, token in enumerate(param_tokens):
        t_no_type = re.sub(r':.*?(?==|$)', '', token).strip()
        has_default = "=" in t_no_type
        is_opt_ts = "?" in token

        if t_no_type.startswith("**") or token.startswith("**"):
            has_kwargs = True
            name = t_no_type.lstrip("*").strip()
            if name:
                param_names.append(name)
            continue
        if t_no_type.startswith("*") or t_no_type.startswith("...") or token.startswith("..."):
            has_varargs = True
            name = t_no_type.lstrip(".*").strip()
            if name:
                param_names.append(name)
            continue

        name = t_no_type.split("=")[0].strip().rstrip("?")
        name = re.sub(r'[{}]', '', name).strip()
        if not name:
            continue

        if i == 0 and name in ("self", "cls"):
            is_method = True
            continue

        param_names.append(name)
        if not has_default and not is_opt_ts:
            required_names.add(name)

    min_required = len(required_names)
    max_positional = 9999 if has_varargs else len(param_names)
    return param_names, required_names, min_required, max_positional, has_varargs, has_kwargs, is_method


def _extract_call_args(line_content: str, lineno: str, src_file: Path, function_name: str) -> str:
    m_call = re.search(rf"\b{re.escape(function_name)}\s*\((.*)", line_content)
    if not m_call:
        return ""
    rest = m_call.group(1)
    args_str = ""
    stack = 1
    for ch in rest:
        if ch == '(':
            stack += 1
        elif ch == ')':
            stack -= 1
            if stack == 0:
                break
        args_str += ch

    if stack > 0 and src_file.is_file():
        try:
            lines = src_file.read_text(encoding="utf-8", errors="replace").splitlines()
            start_idx = int(lineno)
            for extra_line in lines[start_idx:start_idx + 25]:
                for ch in extra_line:
                    if ch == '(':
                        stack += 1
                    elif ch == ')':
                        stack -= 1
                        if stack == 0:
                            break
                    args_str += ch
                if stack == 0:
                    break
                args_str += " "
        except Exception:
            pass
    return args_str


def check_breaking_callsites(file_path: str, function_name: str, new_params: str, project_dir: str = "") -> str:
    """Detecta llamadas existentes que romperían al cambiar los parámetros de una función."""
    p = Path(file_path).resolve()
    if not p.is_file():
        cand, _ = indexer.resolver_archivo(file_path)
        if cand and cand.is_file():
            p = cand
        else:
            return f"[SynRAG Breaking] Archivo '{file_path}' no encontrado."

    project_root = _resolve_project_dir(project_dir) if project_dir else _find_root(p)

    try:
        param_names, required_names, min_required, max_pos, has_varargs, has_kwargs, is_method = _parse_params(new_params)
        allowed_kw = set(param_names)

        lineas = _buscar_lineas(rf"\b{re.escape(function_name)}\s*\(", project_root)

        total_llamadas = 0
        rotas = []

        for l in lineas:
            partes = l.split(":", 2)
            if len(partes) < 3:
                continue
            src_file = Path(partes[0]).resolve()
            lineno = partes[1]
            line_content = partes[2].strip()

            if re.search(rf"\b(def|function\*?|class)\s+{re.escape(function_name)}\b", line_content):
                continue

            total_llamadas += 1

            args_str = _extract_call_args(line_content, lineno, src_file, function_name)
            passed_args = _split_balanced(args_str, ",")
            pos_count = 0
            kw_passed = set()
            for arg in passed_args:
                arg_clean = arg.strip()
                if not arg_clean:
                    continue
                m_kw = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=(?!=)', arg_clean)
                if m_kw:
                    kw_passed.add(m_kw.group(1))
                else:
                    pos_count += 1

            motivo = None

            if not has_kwargs:
                desconocidos = kw_passed - allowed_kw
                if desconocidos:
                    motivo = f"argumento con nombre '{list(desconocidos)[0]}' no existe en la nueva firma"

            if not motivo and not has_varargs and pos_count > max_pos:
                motivo = f"demasiados argumentos posicionales (pasa {pos_count}, nueva firma acepta máx {max_pos})"

            if not motivo:
                for idx, p_name in enumerate(param_names):
                    if p_name in required_names:
                        if idx < pos_count or p_name in kw_passed:
                            continue
                        motivo = f"falta parámetro obligatorio '{p_name}'"
                        break

            if motivo:
                rotas.append({
                    "file": src_file.name,
                    "line": lineno,
                    "reason": motivo,
                    "code": line_content[:80]
                })

        if not total_llamadas:
            return f"[SynRAG Breaking OK] No se encontraron llamadas a '{function_name}' en el proyecto."

        if not rotas:
            return f"[SynRAG Breaking OK] Seguro: todas las llamadas ({total_llamadas}) son compatibles con la nueva firma de '{function_name}'."

        out = [
            f"[SynRAG Breaking ALERTA] '{function_name}': {len(rotas)} de {total_llamadas} llamadas romperían con la nueva firma.",
            f"Nueva firma define {min_required} argumentos obligatorios: {', '.join(required_names) if required_names else 'ninguno'}.",
            "Llamadas incompatibles:",
        ]
        for r in rotas[:10]:
            out.append(f"  - {r['file']}:{r['line']}: {r['reason']} -> {r['code']}")

        return "\n".join(out)

    except Exception as e:
        return f"[SynRAG Breaking] Error al verificar llamadas: {e}"


def _tokenize(name: str) -> List[str]:
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name)
    return [t.lower() for t in re.split(r'[^A-Za-z0-9]+', s) if t]


def find_code_duplicates(symbol_name: str, project_dir: str = "") -> str:
    """Encuentra funciones, clases o símbolos con nombres iguales o parecidos para evitar duplicados."""
    target = _resolve_project_dir(project_dir)
    clean_sym = symbol_name.strip()
    if not clean_sym:
        return f"[SynRAG Duplicados] No se especificó símbolo para buscar."

    try:
        query_lower = clean_sym.lower()
        query_tokens = _tokenize(clean_sym)
        query_sig = {t for t in query_tokens if len(t) >= 2 and t not in {"by", "to", "for", "of", "in", "on", "at", "a", "an", "the"}}
        if not query_sig:
            query_sig = set(query_tokens)

        lines = _buscar_lineas(
            r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:def|class|function\*?|const|let|var|interface|type)\s+([A-Za-z0-9_$]+)",
            target, excluir_archivos=("*.min.js", "*.lock"),
        )

        candidatos = []
        vistos = set()

        for l in lines:
            partes = l.split(":", 2)
            if len(partes) < 3:
                continue
            f_path = Path(partes[0])
            lineno = partes[1]
            code = partes[2].strip()

            m_sym = re.search(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:def|class|function\*?|const|let|var|interface|type)\s+([A-Za-z0-9_$]+)", code)
            if not m_sym:
                continue
            cand_sym = m_sym.group(1)
            cand_lower = cand_sym.lower()

            key = (str(f_path), cand_sym)
            if key in vistos:
                continue

            if cand_lower == query_lower:
                score = 1.0
            else:
                seq_score = difflib.SequenceMatcher(None, query_lower, cand_lower).ratio()
                cand_tokens = _tokenize(cand_sym)
                cand_sig = {t for t in cand_tokens if len(t) >= 2 and t not in {"by", "to", "for", "of", "in", "on", "at", "a", "an", "the"}}
                if not cand_sig:
                    cand_sig = set(cand_tokens)

                inter = query_sig & cand_sig
                union = query_sig | cand_sig
                token_jaccard = (len(inter) / max(1, len(union))) if union else 0.0

                is_substr = (len(query_lower) >= 4 and len(cand_lower) >= 4 and (query_lower in cand_lower or cand_lower in query_lower))

                score = max(seq_score, token_jaccard, 0.85 if is_substr else 0.0)

                if score < 0.65 and not (token_jaccard >= 0.50 and len(inter) >= 2):
                    continue

            vistos.add(key)
            candidatos.append({
                "file": f_path.name,
                "line": lineno,
                "symbol": cand_sym,
                "score": score,
                "code": code[:85]
            })

        candidatos.sort(key=lambda x: x["score"], reverse=True)

        if not candidatos:
            return f"[SynRAG Duplicados] No se detectaron símbolos similares a '{clean_sym}' en '{target.name}'."

        out = [f"[SynRAG Duplicados] Funciones o símbolos con nombres similares a '{clean_sym}':"]
        for c in candidatos[:12]:
            sim_str = f"{c['score']:.0%}"
            out.append(f"  - {c['file']} (L{c['line']}, similitud {sim_str}): {c['code']}")
        return "\n".join(out)

    except Exception as e:
        return f"[SynRAG Duplicados] Error al buscar duplicados: {e}"
