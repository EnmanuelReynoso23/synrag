#!/usr/bin/env python3
"""
benchmarks/costo_fijo.py - Cuanto cuesta en tokens, en CADA turno, lo que SYNRAG inyecta al agente.

Piezas medidas:
  (a) definiciones de herramientas MCP que el servidor entrega por tools/list, en el perfil
      `completo` y en el `esencial` (SYNRAG_PERFIL);
  (b) engine/installer.py BLOQUE_INSTRUCCIONES (instruccion de uso);
  (c) engine/conciso.py BLOQUE_CONCISO_INSTRUCCIONES (modo conciso, con sus marcadores);
  (d) benchmarks/agente/completo.py TOOLS_SYNRAG y EXTRA_CON (solo se leen, no se importa el modulo).

Metodo: tokens(peticion base + pieza) - tokens(peticion base), con el endpoint countTokens de Gemini
(modelo gemini-3.5-flash-lite). La clave sale de GEMINI_API_KEY o de engine/argon.py get_api_key() y
nunca se imprime. Sin clave: caracteres / 4, marcado como aproximado.

Uso:
  python benchmarks/costo_fijo.py                 # motor de este repositorio
  python benchmarks/costo_fijo.py --engine RUTA   # otro directorio engine/ (p. ej. otra version)
  python benchmarks/costo_fijo.py --sin-api       # fuerza la estimacion caracteres / 4
"""

import argparse
import ast
import json
import os
import select
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
MODELO = "gemini-3.5-flash-lite"
URL_COUNT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:countTokens"
PERFILES = ("completo", "esencial", "bajo_demanda")
CLAVES_NO_GEMINI = ("title", "default", "additionalProperties", "$schema", "$defs", "definitions")


# --------------------------------------------------------------------------
# Lectura de las piezas (sin ejecutar el benchmark ni importarlo)
# --------------------------------------------------------------------------

def _leer_constante_completo(ruta: Path) -> Dict[str, Any]:
    """Evalua solo S, I, _decl, TOOLS_SYNRAG y EXTRA_CON de completo.py (sin importar el modulo)."""
    fuente = ruta.read_text(encoding="utf-8")
    arbol = ast.parse(fuente)
    nodos = []
    for nodo in arbol.body:
        if isinstance(nodo, ast.FunctionDef) and nodo.name == "_decl":
            nodos.append(nodo)
        elif isinstance(nodo, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id in ("S", "I", "TOOLS_SYNRAG", "EXTRA_CON") for t in nodo.targets
        ):
            nodos.append(nodo)
    espacio: Dict[str, Any] = {}
    exec(compile(ast.Module(body=nodos, type_ignores=[]), str(ruta), "exec"), espacio)  # noqa: S102
    return {"TOOLS_SYNRAG": espacio["TOOLS_SYNRAG"], "EXTRA_CON": espacio["EXTRA_CON"]}


def _cargar_motor(engine: Path):
    sys.path.insert(0, str(engine))
    import conciso  # noqa: E402
    import installer  # noqa: E402
    return installer, conciso


def _clave() -> str:
    clave = os.environ.get("GEMINI_API_KEY", "").strip()
    if clave:
        return clave
    try:
        sys.path.insert(0, str(RAIZ / "engine"))
        import argon  # noqa: E402
        return (argon.get_api_key() or "").strip()
    except Exception:  # noqa: BLE001
        return ""


# --------------------------------------------------------------------------
# tools/list por stdio, igual que lo recibe un cliente MCP
# --------------------------------------------------------------------------

def _mensaje(proc: subprocess.Popen, id_esperado: int, limite_s: float = 40.0) -> Dict[str, Any]:
    fin = time.time() + limite_s
    while time.time() < fin:
        if proc.poll() is not None:
            raise RuntimeError(f"el servidor MCP termino con codigo {proc.returncode}")
        listos, _, _ = select.select([proc.stdout], [], [], 0.5)
        if not listos:
            continue
        linea = proc.stdout.readline()
        if not linea.strip():
            continue
        try:
            msg = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if msg.get("id") == id_esperado:
            return msg
    raise TimeoutError("sin respuesta del servidor MCP")


def herramientas_mcp(engine: Path, perfil: str) -> List[Dict[str, Any]]:
    """Definiciones (name, description, inputSchema) que el servidor expone en ese perfil."""
    env = dict(os.environ, SYNRAG_PERFIL=perfil, PYTHONUNBUFFERED="1")
    with tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(
            [sys.executable, str(engine / "server_mcp.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err,
            text=True, env=env, cwd=str(engine),
        )
        try:
            def enviar(msg: Dict[str, Any]) -> None:
                proc.stdin.write(json.dumps(msg) + "\n")
                proc.stdin.flush()

            enviar({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "costo_fijo", "version": "1"}}})
            _mensaje(proc, 1)
            enviar({"jsonrpc": "2.0", "method": "notifications/initialized"})
            enviar({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
            resp = _mensaje(proc, 2)
            if "error" in resp:
                raise RuntimeError(f"tools/list devolvio error: {resp['error']}")
            return resp["result"]["tools"]
        except Exception as e:  # noqa: BLE001
            err.seek(0)
            detalle = err.read().decode("utf-8", errors="replace")[-400:]
            raise RuntimeError(f"{e}. stderr: {detalle}") from e
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


def _a_gemini(nodo: Any) -> Any:
    """Schema JSON de MCP -> Schema de Gemini (tipos en mayusculas, sin claves que Gemini no admite)."""
    if isinstance(nodo, dict):
        salida = {}
        for k, v in nodo.items():
            if k in CLAVES_NO_GEMINI:
                continue
            salida[k] = v.upper() if (k == "type" and isinstance(v, str)) else _a_gemini(v)
        return salida
    if isinstance(nodo, list):
        return [_a_gemini(x) for x in nodo]
    return nodo


def declaraciones_desde_mcp(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    decls = []
    for t in tools:
        d: Dict[str, Any] = {"name": t["name"], "description": t.get("description", "")}
        esquema = _a_gemini(t.get("inputSchema") or {})
        if esquema.get("properties"):
            d["parameters"] = esquema
        decls.append(d)
    return decls


# --------------------------------------------------------------------------
# countTokens
# --------------------------------------------------------------------------

def contar(clave: str, sistema: Optional[str] = None, tools: Optional[List[Dict[str, Any]]] = None) -> int:
    peticion: Dict[str, Any] = {
        "model": f"models/{MODELO}",
        "contents": [{"role": "user", "parts": [{"text": "Hola"}]}],
    }
    if sistema:
        peticion["systemInstruction"] = {"parts": [{"text": sistema}]}
    if tools:
        peticion["tools"] = tools
    cuerpo = json.dumps({"generateContentRequest": peticion}).encode("utf-8")
    req = urllib.request.Request(URL_COUNT, data=cuerpo, headers={
        "Content-Type": "application/json", "x-goog-api-key": clave})
    for intento in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return int(json.loads(resp.read().decode("utf-8"))["totalTokens"])
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and intento < 3:
                time.sleep(3 * (intento + 1))
                continue
            raise RuntimeError(f"countTokens HTTP {e.code}") from None
    raise RuntimeError("countTokens sin respuesta")


def estimar(texto_o_json: str) -> int:
    return (len(texto_o_json) + 3) // 4


def medir(clave: Optional[str], tipo: str, valor: Any) -> Tuple[int, str]:
    """Devuelve (tokens, metodo). tipo: 'sistema' (texto) o 'tools' (lista de declaraciones)."""
    if clave:
        if tipo == "sistema":
            base = contar(clave)
            return contar(clave, sistema=valor) - base, "countTokens exacto"
        base = contar(clave)
        return contar(clave, tools=[{"functionDeclarations": valor}]) - base, "countTokens exacto"
    if tipo == "sistema":
        return estimar(valor), "caracteres/4 (aprox.)"
    return estimar(json.dumps(valor, ensure_ascii=False)), "caracteres/4 (aprox.)"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", type=Path, default=RAIZ / "engine", help="directorio engine/ a medir")
    ap.add_argument("--sin-api", action="store_true", help="no llamar a countTokens; caracteres / 4")
    args = ap.parse_args(argv)

    engine = args.engine.resolve()
    if not (engine / "server_mcp.py").is_file():
        print(f"No hay server_mcp.py en {engine}", file=sys.stderr)
        return 2

    clave = None if args.sin_api else (_clave() or None)
    if not clave and not args.sin_api:
        print("Aviso: sin clave de Gemini; cifras aproximadas (caracteres / 4).")

    installer, conciso = _cargar_motor(engine)
    completo = _leer_constante_completo(AQUI / "agente" / "completo.py")

    filas: List[Tuple[str, int, str]] = []
    for perfil in PERFILES:
        decls = declaraciones_desde_mcp(herramientas_mcp(engine, perfil))
        tokens, metodo = medir(clave, "tools", decls)
        filas.append((f"(a) herramientas MCP perfil {perfil} ({len(decls)} herramientas)", tokens, metodo))

    piezas = [
        ("(b) installer.BLOQUE_INSTRUCCIONES", installer.BLOQUE_INSTRUCCIONES),
        ("(c) conciso.BLOQUE_CONCISO_INSTRUCCIONES", conciso.BLOQUE_CONCISO_INSTRUCCIONES),
        ("(d) completo.EXTRA_CON", completo["EXTRA_CON"]),
    ]
    for nombre, texto in piezas:
        tokens, metodo = medir(clave, "sistema", texto)
        filas.append((nombre, tokens, metodo))
    tokens, metodo = medir(clave, "tools", completo["TOOLS_SYNRAG"])
    filas.append((f"(d) completo.TOOLS_SYNRAG ({len(completo['TOOLS_SYNRAG'])} herramientas)", tokens, metodo))

    ancho = max(len(f[0]) for f in filas)
    print(f"Motor: {engine}")
    print(f"Modelo de conteo: {MODELO}")
    print(f"{'pieza'.ljust(ancho)}  tokens  metodo")
    for nombre, tokens, metodo in filas:
        print(f"{nombre.ljust(ancho)}  {tokens:>6}  {metodo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
