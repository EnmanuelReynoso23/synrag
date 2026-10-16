import json
import io
import os
import sys
from pathlib import Path
import pytest

import filtro
import hook_filtro
import installer
import cli


def test_textos_cortos_no_cambian():
    # Menos de 40 lineas se devuelve intacto
    texto_corto = "linea 1\nlinea 2\nlinea 3\n"
    assert filtro.filtrar(texto_corto) == texto_corto

    texto_39 = "\n".join(f"linea {i}" for i in range(39)) + "\n"
    assert filtro.filtrar(texto_39) == texto_39

    # Texto vacio
    assert filtro.filtrar("") == ""


def test_errores_nunca_se_pierden():
    # Construir un texto largo (> 40 lineas) con diversos tipos de errores
    lineas = []
    # 20 lineas iniciales de ruido
    for i in range(20):
        lineas.append(f"Compiling crate_{i} v1.0.0")

    # Error en linea 20 con contexto
    lineas.append("contexto anterior 1")
    lineas.append("contexto anterior 2")
    lineas.append("error: could not compile `crate_20` due to 1 previous error")
    lineas.append("contexto posterior 1")
    lineas.append("contexto posterior 2")

    # Mas lineas con fallos y excepciones
    lineas.append("Traceback (most recent call last):")
    lineas.append('  File "app.py", line 42, in <module>')
    lineas.append("AssertionError: condition failed unexpectedly")
    lineas.append("panic: runtime error: index out of bounds")
    lineas.append("warning: field `unused` is never read")
    lineas.append("npm ERR! code ELIFECYCLE")
    lineas.append("FAILED tests/test_core.py::test_case - Exception: failed to connect")

    # Rellenar hasta tener mas de 80 lineas (las ultimas 30 seran la cola)
    for i in range(40):
        lineas.append(f"cola final linea {i}")

    texto = "\n".join(lineas) + "\n"
    assert len(lineas) >= 70

    salida = filtro.filtrar(texto, comando="cargo test")
    
    # Comprobar encabezado de reduccion
    assert salida.startswith(f"[filtrado: {len(lineas)} -> ")

    # Comprobar que NINGUNA linea de error se perdio
    assert "error: could not compile `crate_20` due to 1 previous error" in salida
    assert "contexto anterior 1" in salida
    assert "contexto anterior 2" in salida
    assert "contexto posterior 1" in salida
    assert "contexto posterior 2" in salida
    assert "Traceback (most recent call last):" in salida
    assert "AssertionError: condition failed unexpectedly" in salida
    assert "panic: runtime error: index out of bounds" in salida
    assert "warning: field `unused` is never read" in salida
    assert "npm ERR! code ELIFECYCLE" in salida
    assert "FAILED tests/test_core.py::test_case - Exception: failed to connect" in salida

    # Comprobar que las ultimas 30 lineas se conservan enteras
    ultimas_30 = lineas[-30:]
    for l in ultimas_30:
        assert l in salida


def test_progreso_con_cr_se_limpia():
    # Lineas sobreescritas con \r
    lineas = []
    for i in range(45):
        # Cada linea simula actualizacion de progreso con \r
        lineas.append(f"Descargando {i} 10%\rDescargando {i} 50%\rDescargando {i} 100%")

    texto = "\n".join(lineas) + "\n"
    salida = filtro.filtrar(texto)

    # Las etapas intermedias no deben aparecer
    assert "10%" not in salida
    assert "50%" not in salida
    # Solo el estado final 100% de cada linea
    assert "Descargando 0 100%" in salida


def test_repetidas_se_colapsan():
    lineas = []
    # 20 lineas exactamente identicas
    for _ in range(20):
        lineas.append("Conectando al servidor...")

    # 37 lineas casi iguales (mismo texto salvo numeros)
    for i in range(1, 38):
        lineas.append(f"Procesando bloque {i} de 37")

    # Cola de 30 lineas
    for i in range(30):
        lineas.append(f"resultado final {i}")

    texto = "\n".join(lineas) + "\n"
    salida = filtro.filtrar(texto)

    # Debe haber colapsado las 20 identicas
    assert "Conectando al servidor... (x20)" in salida
    # Debe haber colapsado las 37 casi iguales
    assert "(x37)" in salida


def test_ruido_agrupado():
    lineas = []
    # npm WARN deprecated
    for i in range(15):
        lineas.append(f"npm WARN deprecated paquete-{i}@1.0.0: este paquete esta desfasado")

    # pip Collecting / Downloading
    for i in range(10):
        lineas.append(f"Collecting dep-{i}==1.0")
        lineas.append(f"  Downloading dep_{i}-1.0-py3-none-any.whl (50 kB)")

    # cargo Compiling
    for i in range(12):
        lineas.append(f"   Compiling crate_{i} v0.1.0")

    # Cola de 30 lineas
    for i in range(30):
        lineas.append(f"fin {i}")

    texto = "\n".join(lineas) + "\n"
    salida = filtro.filtrar(texto)

    assert "[npm WARN deprecated: 15 avisos]" in salida
    assert "[pip: 20 operaciones de descarga/recoleccion]" in salida
    assert "[cargo: 12 crates compilados]" in salida


def test_hook_envuelve_npm_install_y_no_toca_ls_ni_pipe_tail():
    # 1. npm install debe ser envuelto
    res_npm = hook_filtro.procesar_hook({
        "tool_name": "Bash",
        "tool_input": {"command": "npm install"},
    })
    assert "hookSpecificOutput" in res_npm
    nuevo_cmd = res_npm["hookSpecificOutput"]["updatedInput"]["command"]
    assert nuevo_cmd == "( set -o pipefail; ( npm install ) 2>&1 | synrag-filtrar )"
    # No decide el permiso por su cuenta
    assert "permissionDecision" not in res_npm["hookSpecificOutput"]

    # 2. ls -la no debe tocarse
    res_ls = hook_filtro.procesar_hook({
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"},
    })
    assert res_ls == {}

    # 3. npm test | tail no debe tocarse
    res_tail = hook_filtro.procesar_hook({
        "tool_name": "Bash",
        "tool_input": {"command": "npm test | tail -n 20"},
    })
    assert res_tail == {}

    # 4. Otros comandos ruidosos que si deben envolverse
    for cmd in ["pnpm test", "cargo build --release", "pytest -q", "pip install flask", "uv sync", "docker build ."]:
        res = hook_filtro.procesar_hook({"tool_name": "Bash", "tool_input": {"command": cmd}})
        assert "hookSpecificOutput" in res
        assert "synrag-filtrar" in res["hookSpecificOutput"]["updatedInput"]["command"]

    # 5. Comandos con redireccion a archivo o tuberias no deben tocarse
    for cmd in ["pytest > salida.txt", "npm test | grep FAIL", "cargo build 2>&1 | rg error"]:
        res = hook_filtro.procesar_hook({"tool_name": "Bash", "tool_input": {"command": cmd}})
        assert res == {}

    # 6. Idempotencia: si ya esta envuelto por synrag-filtrar, no volver a envolver
    res_ya = hook_filtro.procesar_hook({
        "tool_name": "Bash",
        "tool_input": {"command": "( set -o pipefail; ( npm install ) 2>&1 | synrag-filtrar )"},
    })
    assert res_ya == {}


def test_configure_filtro_idempotente_y_uninstall_conserva_ajenos(casa):
    # Simular settings.json existente con otros ajustes y hooks ajenos
    dir_claude = casa / ".claude"
    dir_claude.mkdir(parents=True, exist_ok=True)
    settings_file = dir_claude / "settings.json"

    config_inicial = {
        "theme": "dark",
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Edit",
                    "hooks": [{"type": "command", "command": "/usr/local/bin/check-lint"}]
                },
                {
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": "/usr/local/bin/log-bash"}]
                }
            ]
        }
    }
    settings_file.write_text(json.dumps(config_inicial, indent=2), encoding="utf-8")

    # 1. configure_filtro anade el hook de synrag
    res1 = installer.configure_filtro()
    assert res1 == installer.OK

    datos1 = json.loads(settings_file.read_text(encoding="utf-8"))
    assert datos1["theme"] == "dark"
    # El hook ajeno de Edit sigue ahi
    edit_entry = next(e for e in datos1["hooks"]["PreToolUse"] if e["matcher"] == "Edit")
    assert edit_entry["hooks"][0]["command"] == "/usr/local/bin/check-lint"

    # El matcher Bash ahora tiene ambos hooks
    bash_entry = next(e for e in datos1["hooks"]["PreToolUse"] if e["matcher"] == "Bash")
    cmds = [h["command"] for h in bash_entry["hooks"]]
    assert "/usr/local/bin/log-bash" in cmds
    assert any("hook_filtro.py" in c for c in cmds)

    # 2. Segunda llamada: idempotente
    res2 = installer.configure_filtro()
    assert res2 == installer.YA
    datos2 = json.loads(settings_file.read_text(encoding="utf-8"))
    assert datos2 == datos1

    # 3. uninstall_filtro quita SOLO el hook de synrag
    res_un = installer.uninstall_filtro()
    assert res_un == installer.OK

    datos_un = json.loads(settings_file.read_text(encoding="utf-8"))
    assert datos_un["theme"] == "dark"
    edit_entry_un = next(e for e in datos_un["hooks"]["PreToolUse"] if e["matcher"] == "Edit")
    assert edit_entry_un["hooks"][0]["command"] == "/usr/local/bin/check-lint"

    bash_entry_un = next(e for e in datos_un["hooks"]["PreToolUse"] if e["matcher"] == "Bash")
    cmds_un = [h["command"] for h in bash_entry_un["hooks"]]
    assert "/usr/local/bin/log-bash" in cmds_un
    assert not any("hook_filtro.py" in c for c in cmds_un)

    # 4. Segunda desinstalacion: idempotente
    res_un2 = installer.uninstall_filtro()
    assert res_un2 == installer.YA


def test_install_cli_binaries_crea_synrag_filtrar(casa):
    local_bin = casa / ".local" / "bin"
    assert not (local_bin / "synrag-filtrar").exists()

    installer.install_cli_binaries()
    filtrar_bin = local_bin / "synrag-filtrar"
    assert filtrar_bin.is_file()
    assert os.access(filtrar_bin, os.X_OK)
    contenido = filtrar_bin.read_text(encoding="utf-8")
    assert "SyntaxRAG Terminal Filter Launcher" in contenido
    assert "cli.py" in contenido
    assert "filtrar" in contenido

    installer.run_uninstall()
    assert not filtrar_bin.exists()


def test_cli_subcomando_filtrar(monkeypatch, capsys):
    texto = "\n".join(f"linea de prueba {i}" for i in range(50)) + "\n"
    monkeypatch.setattr(sys, "argv", ["cli.py", "filtrar", "--comando", "pytest"])
    monkeypatch.setattr(sys, "stdin", io.StringIO(texto))

    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0

    capturado = capsys.readouterr()
    assert "[filtrado: 50 -> " in capturado.out


def test_filtro_largas_umbrales_y_env_vars(casa, monkeypatch):
    # Por debajo del umbral pasa intacta
    texto_corto = "\n".join(f"linea {i}" for i in range(100)) + "\n"
    res_corto = filtro.filtrar_salida_larga(texto_corto)
    assert res_corto == texto_corto
    cache_dir = casa / ".cache" / "synrag" / "salidas"
    assert not cache_dir.exists() or len(list(cache_dir.glob("*.log"))) == 0

    # Por encima de 200 lineas se filtra
    texto_largo = "\n".join(f"evento de log {i}" for i in range(250)) + "\n"
    res_largo = filtro.filtrar_salida_larga(texto_largo)
    assert "[synrag: " in res_largo
    assert "completa en" in res_largo
    assert len(res_largo.splitlines()) < 250

    # Variables de entorno SYNRAG_FILTRO_UMBRAL_LINEAS / _CARACTERES
    monkeypatch.setenv("SYNRAG_FILTRO_UMBRAL_LINEAS", "50")
    texto_150 = "\n".join(f"linea reducida {i}" for i in range(150)) + "\n"
    res_150 = filtro.filtrar_salida_larga(texto_150)
    assert "[synrag: " in res_150
    assert len(res_150.splitlines()) < 150

    monkeypatch.setenv("SYNRAG_FILTRO_UMBRAL_CARACTERES", "500")
    texto_chars = "\n".join("x" * 200 for _ in range(150)) + "\n"
    res_chars = filtro.filtrar_salida_larga(texto_chars)
    assert "[synrag: " in res_chars


def test_filtro_largas_archivo_completo_y_limpieza_24h(casa):
    cache_dir = casa / ".cache" / "synrag" / "salidas"
    texto_300 = "\n".join(f"salida linea {i}" for i in range(300)) + "\n"
    salida = filtro.filtrar_salida_larga(texto_300)
    assert "[synrag: " in salida

    # Comprobar que el archivo se guardo con la salida original completa
    logs = list(cache_dir.glob("*.log"))
    assert len(logs) == 1
    assert logs[0].read_text(encoding="utf-8") == texto_300

    # Probar limpieza de archivos mayores a 24 horas
    viejo_log = cache_dir / "salida_20261014_100000_deadbeef.log"
    viejo_log.write_text("salida antigua de ayer", encoding="utf-8")
    import time
    t_viejo = time.time() - (30 * 3600)  # 30 horas atras
    os.utime(viejo_log, (t_viejo, t_viejo))

    eliminados = filtro.limpiar_salidas_antiguas(cache_dir, max_edad_segundos=86400)
    assert eliminados == 1
    assert not viejo_log.exists()
    assert logs[0].exists()


def test_filtro_largas_primeras_40_ultimas_60_y_errores_con_contexto(casa):
    lineas = []
    # Primeras 40
    for i in range(40):
        lineas.append(f"inicio {i}")
    # Relleno 40..199
    for i in range(40, 200):
        lineas.append(f"normal {i}")
    # Error intercalado en 200 con +/- 2 contexto
    lineas.append("Traceback (most recent call last):")
    lineas.append('  File "modulo.py", line 42, in ejecutar')
    lineas.append("ValueError: parametro invalido")
    lineas.append("warning: buffer casi lleno")
    # Relleno 204..439
    for i in range(204, 440):
        lineas.append(f"medio {i}")
    # Ultimas 60 (440..499)
    for i in range(440, 500):
        lineas.append(f"fin cola {i}")

    texto = "\n".join(lineas) + "\n"
    salida = filtro.filtrar_salida_larga(texto)

    # Primeras 40 lineas presentes
    for i in range(40):
        assert f"inicio {i}" in salida

    # Error y su contexto presentes
    assert "Traceback (most recent call last):" in salida
    assert '  File "modulo.py", line 42, in ejecutar' in salida
    assert "ValueError: parametro invalido" in salida
    assert "warning: buffer casi lleno" in salida
    assert "normal 198" in salida
    assert "normal 199" in salida

    # Ultimas 60 lineas presentes
    for i in range(440, 500):
        assert f"fin cola {i}" in salida

    # Marcadores de omision
    assert "[synrag: " in salida
    assert "completa en" in salida


def test_filtro_largas_nunca_mas_largo_que_original(casa):
    # Si la salida producida fuese mas larga o igual, debe devolverse el texto original
    # Construimos un caso donde cada linea es un error
    lineas_err = [f"error linea {i}: fallo critico" for i in range(205)]
    texto = "\n".join(lineas_err) + "\n"
    salida = filtro.filtrar_salida_larga(texto)
    assert len(salida) <= len(texto)
    assert len(salida.splitlines()) <= len(texto.splitlines())


def test_exclusiones_de_envoltura_exhaustivo():
    # 1. Comandos que cambian estado de la shell -> excluidos
    assert hook_filtro.debe_excluir_de_envoltura("cd x && ls") is True
    assert hook_filtro.debe_excluir_de_envoltura("cd /tmp") is True
    assert hook_filtro.debe_excluir_de_envoltura("export VAR=1 && pytest") is True
    assert hook_filtro.debe_excluir_de_envoltura("source venv/bin/activate") is True
    assert hook_filtro.debe_excluir_de_envoltura(". venv/bin/activate") is True
    assert hook_filtro.debe_excluir_de_envoltura("alias ll='ls -la'") is True
    assert hook_filtro.debe_excluir_de_envoltura("ulimit -n 4096") is True
    assert hook_filtro.debe_excluir_de_envoltura("set -e") is True

    # 2. Paginadores y filtros ya presentes -> excluidos
    assert hook_filtro.debe_excluir_de_envoltura("cat file | head -n 10") is True
    assert hook_filtro.debe_excluir_de_envoltura("git log | tail") is True
    assert hook_filtro.debe_excluir_de_envoltura("cat file | less") is True

    # 3. Redirecciones a archivo y heredoc -> excluidos
    assert hook_filtro.debe_excluir_de_envoltura("pytest > out.txt") is True
    assert hook_filtro.debe_excluir_de_envoltura("npm test >> out.log") is True
    assert hook_filtro.debe_excluir_de_envoltura("cat << EOF\nhello\nEOF") is True

    # 4. Segundo plano y nohup -> excluidos
    assert hook_filtro.debe_excluir_de_envoltura("sleep 10 &") is True
    assert hook_filtro.debe_excluir_de_envoltura("nohup python worker.py &") is True

    # 5. Editores y REPL interactivos -> excluidos
    assert hook_filtro.debe_excluir_de_envoltura("vim file.py") is True
    assert hook_filtro.debe_excluir_de_envoltura("nano file.py") is True
    assert hook_filtro.debe_excluir_de_envoltura("top") is True
    assert hook_filtro.debe_excluir_de_envoltura("python") is True
    assert hook_filtro.debe_excluir_de_envoltura("python3") is True
    assert hook_filtro.debe_excluir_de_envoltura("node") is True
    assert hook_filtro.debe_excluir_de_envoltura("ssh host") is True
    assert hook_filtro.debe_excluir_de_envoltura("ssh user@192.168.1.10") is True
    assert hook_filtro.debe_excluir_de_envoltura("ssh -i ~/.ssh/key user@host") is True

    # 6. Comandos que SI deben envolverse
    # ssh con comando remoto
    assert hook_filtro.debe_excluir_de_envoltura("ssh host 'cmd'") is False
    assert hook_filtro.debe_excluir_de_envoltura("ssh user@host \"cat /var/log/syslog\"") is False
    assert hook_filtro.debe_excluir_de_envoltura("ssh -p 22 host uptime") is False

    # Scripts y comandos habituales
    assert hook_filtro.debe_excluir_de_envoltura("python script.py") is False
    assert hook_filtro.debe_excluir_de_envoltura("python -c \"print('test')\"") is False
    assert hook_filtro.debe_excluir_de_envoltura("node server.js") is False
    assert hook_filtro.debe_excluir_de_envoltura("find / -maxdepth 3") is False
    assert hook_filtro.debe_excluir_de_envoltura("cat /var/log/messages") is False


def test_envoltura_conserva_codigo_de_salida_pipefail(casa, monkeypatch):
    import subprocess
    installer.install_cli_binaries()
    local_bin = casa / ".local" / "bin"
    monkeypatch.setenv("PATH", f"{local_bin}:{os.environ.get('PATH', '')}")

    # 1. Envoltura estandar
    cmd = hook_filtro.envolver_comando("exit 42")
    res = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
    assert res.returncode == 42

    # 2. Envoltura larga
    cmd_largo = hook_filtro.envolver_comando_largo("exit 37")
    res_largo = subprocess.run(["bash", "-c", cmd_largo], capture_output=True, text=True)
    assert res_largo.returncode == 37


def test_configure_uninstall_filtro_largas_idempotentes(casa):
    dir_claude = casa / ".claude"
    dir_claude.mkdir(parents=True, exist_ok=True)
    settings_file = dir_claude / "settings.json"

    config_inicial = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": "/usr/local/bin/hook-pre"}]
                }
            ]
        }
    }
    settings_file.write_text(json.dumps(config_inicial, indent=2), encoding="utf-8")

    # 1. configure_filtro_largas anade PostToolUse sin tocar PreToolUse
    res1 = installer.configure_filtro_largas()
    assert res1 == installer.OK

    datos1 = json.loads(settings_file.read_text(encoding="utf-8"))
    # PreToolUse intacto
    assert len(datos1["hooks"]["PreToolUse"]) == 1
    assert datos1["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == "/usr/local/bin/hook-pre"

    # PostToolUse creado con Bash
    post_bash = next(e for e in datos1["hooks"]["PostToolUse"] if e["matcher"] == "Bash")
    assert any("hook_filtro.py" in h["command"] for h in post_bash["hooks"])

    # 2. Idempotente
    res2 = installer.configure_filtro_largas()
    assert res2 == installer.YA

    # 3. uninstall_filtro_largas quita PostToolUse sin tocar PreToolUse
    res_un = installer.uninstall_filtro_largas()
    assert res_un == installer.OK

    datos_un = json.loads(settings_file.read_text(encoding="utf-8"))
    assert "PostToolUse" not in datos_un["hooks"]
    assert len(datos_un["hooks"]["PreToolUse"]) == 1

    # 4. Segunda desinstalacion idempotente
    res_un2 = installer.uninstall_filtro_largas()
    assert res_un2 == installer.YA


def test_post_tool_use_hook_remplaza_salida_bash(casa):
    # Por debajo del umbral pasa intacta (hook devuelve {})
    res_baja = hook_filtro.procesar_hook({
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "echo hola"},
        "tool_response": {"stdout": "salida corta\n", "stderr": "", "interrupted": False, "isImage": False}
    })
    assert res_baja == {}

    # Por encima del umbral reemplaza mediante updatedToolOutput
    lineas_300 = "\n".join(f"linea log {i}" for i in range(300)) + "\n"
    res_alta = hook_filtro.procesar_hook({
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "cat salida.log"},
        "tool_response": {"stdout": lineas_300, "stderr": "", "interrupted": False, "isImage": False}
    })
    assert "hookSpecificOutput" in res_alta
    especifico = res_alta["hookSpecificOutput"]
    assert especifico["hookEventName"] == "PostToolUse"
    assert "updatedToolOutput" in especifico
    out = especifico["updatedToolOutput"]
    assert "[synrag: " in out["stdout"]
    assert len(out["stdout"].splitlines()) < 300
    assert out["stderr"] == ""
    assert out["interrupted"] is False



def test_filtro_largas_no_llama_completa_a_una_salida_ya_cortada_por_claude_code(casa):
    import importlib, filtro
    importlib.reload(filtro)
    texto = "".join(f"linea {i}\n" for i in range(5000))[: filtro.LIMITE_CLAUDE_CODE]
    res = filtro.filtrar_salida_larga(texto)
    primera = res.splitlines()[0]
    assert "copia parcial" in primera and "completa en" not in primera
    assert res.count("/synrag/salidas/") == 1  # la ruta va una sola vez, no en cada hueco
