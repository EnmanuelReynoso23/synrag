#!/usr/bin/env python3
"""
Verificador de arranque del servidor MCP SyntaxRAG por stdio y comprobacion de tools/list.

Regla:
  - El servidor debe arrancar y responder a initialize y tools/list sin colgarse.
  - Ninguna herramienta puede definir outputSchema (coste innecesario de tokens).
"""

import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path


def resolver_rutas():
    # 1. Argumentos CLI si se pasan
    if len(sys.argv) >= 3:
        return sys.argv[1], sys.argv[2]
    if len(sys.argv) == 2:
        return sys.argv[1], None

    # 2. Variables de entorno
    python_env = os.environ.get("VENV_PYTHON")
    server_env = os.environ.get("SERVER_MCP_PY")

    # 3. Ubicaciones por defecto (instalacion limpia ~/.local/opt/lancedb-hub)
    home = Path.home()
    default_venv_py = home / ".local" / "opt" / "lancedb-hub" / ".venv" / "bin" / "python"
    default_server = home / ".local" / "opt" / "lancedb-hub" / "server_mcp.py"

    py_cmd = python_env or (str(default_venv_py) if default_venv_py.is_file() else sys.executable)
    server_py = server_env or (str(default_server) if default_server.is_file() else None)

    if not server_py:
        # Buscar en repo local (directorio relativo)
        repo_server = Path(__file__).resolve().parent.parent.parent / "engine" / "server_mcp.py"
        if repo_server.is_file():
            server_py = str(repo_server)

    return py_cmd, server_py


def leer_mensaje_json(proc, timeout_segundos=15):
    inicio = time.time()
    while time.time() - inicio < timeout_segundos:
        if proc.poll() is not None:
            err = proc.stderr.read() if proc.stderr else ""
            raise RuntimeError(f"El servidor MCP termino inesperadamente (codigo {proc.returncode}). stderr: {err}")

        # Comprobar si hay datos disponibles en stdout
        rlist, _, _ = select.select([proc.stdout], [], [], 0.5)
        if not rlist:
            continue

        linea = proc.stdout.readline()
        if not linea:
            continue
        linea = linea.strip()
        if not linea:
            continue

        try:
            return json.loads(linea)
        except json.JSONDecodeError:
            # Ignorar salidas que no sean JSON (p. ej. banners de inicio si hubiera)
            continue

    raise TimeoutError(f"Tiempo de espera agotado ({timeout_segundos}s) esperando mensaje del servidor MCP.")


def esperar_respuesta_id(proc, req_id, timeout_segundos=20):
    inicio = time.time()
    while time.time() - inicio < timeout_segundos:
        msg = leer_mensaje_json(proc, timeout_segundos=max(1, int(timeout_segundos - (time.time() - inicio))))
        if isinstance(msg, dict) and msg.get("id") == req_id:
            return msg
    raise TimeoutError(f"No se recibio respuesta con id={req_id} dentro del tiempo limite.")


def main():
    py_cmd, server_py = resolver_rutas()

    if not server_py or not Path(server_py).is_file():
        print(f"[ERROR] No se encontro server_mcp.py en: {server_py}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Probando servidor MCP:")
    print(f"  Python: {py_cmd}")
    print(f"  Server: {server_py}")

    cmd = [py_cmd, server_py]
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    try:
        # Paso 1: initialize
        req_init = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ci-verifier", "version": "1.0.0"},
            },
        }
        proc.stdin.write(json.dumps(req_init) + "\n")
        proc.stdin.flush()

        resp_init = esperar_respuesta_id(proc, 1, timeout_segundos=15)
        if "error" in resp_init:
            print(f"[ERROR] Error en initialize: {resp_init['error']}", file=sys.stderr)
            sys.exit(1)

        server_info = resp_init.get("result", {}).get("serverInfo", {})
        print(f"[OK] MCP inicializado correctamente: {server_info.get('name', 'desconocido')}")

        # Paso 2: notifications/initialized
        notif = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        proc.stdin.write(json.dumps(notif) + "\n")
        proc.stdin.flush()

        # Paso 3: tools/list
        req_tools = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }
        proc.stdin.write(json.dumps(req_tools) + "\n")
        proc.stdin.flush()

        resp_tools = esperar_respuesta_id(proc, 2, timeout_segundos=15)
        if "error" in resp_tools:
            print(f"[ERROR] Error en tools/list: {resp_tools['error']}", file=sys.stderr)
            sys.exit(1)

        result = resp_tools.get("result", {})
        tools = result.get("tools")
        if tools is None or not isinstance(tools, list) or len(tools) == 0:
            print("[ERROR] tools/list no devolvio herramientas.", file=sys.stderr)
            sys.exit(1)

        # Paso 4: Validar que ninguna herramienta traiga outputSchema
        con_output_schema = []
        for t in tools:
            nombre = t.get("name", "<sin_nombre>")
            if "outputSchema" in t:
                con_output_schema.append((nombre, t["outputSchema"]))

        if con_output_schema:
            print(f"[ERROR] {len(con_output_schema)} herramienta(s) incluyen outputSchema:", file=sys.stderr)
            for nombre, esquema in con_output_schema:
                print(f"  - {nombre}: {esquema}", file=sys.stderr)
            print("[ERROR] Regla incumplida: ninguna herramienta MCP debe tener outputSchema.", file=sys.stderr)
            sys.exit(1)

        print(f"[OK] Total herramientas verificadas: {len(tools)}")
        print(f"[OK] Ninguna herramienta incluye outputSchema (ahorro de tokens verificado).")

    finally:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

    sys.exit(0)


if __name__ == "__main__":
    main()
