import importlib
import json
import sys
from pathlib import Path
import installer


def test_instalador_antigravity_idempotente(casa):
    # Simular Antigravity instalado
    (casa / ".gemini" / "antigravity").mkdir(parents=True, exist_ok=True)

    # 1. Primera llamada: crea config/mcp_config.json
    res1 = installer.configure_antigravity()
    assert res1 == ["Google Antigravity"]

    target = casa / ".gemini" / "config" / "mcp_config.json"
    assert target.is_file()
    datos1 = json.loads(target.read_text(encoding="utf-8"))
    assert "desktop-lancedb" in datos1["mcpServers"]
    mtime1 = target.stat().st_mtime

    # 2. Segunda llamada: idempotente ("ya estaba"), no altera el archivo
    res2 = installer.configure_antigravity()
    assert res2 == ["Google Antigravity"]
    datos2 = json.loads(target.read_text(encoding="utf-8"))
    assert datos2 == datos1


def test_instalador_conserva_ajenos_y_actualiza_ruta_anterior(casa):
    # Simular existencia previa de la ruta anterior y servidores ajenos
    dir_anterior = casa / ".gemini" / "antigravity"
    dir_anterior.mkdir(parents=True, exist_ok=True)
    archivo_anterior = dir_anterior / "mcp_config.json"
    archivo_anterior.write_text(
        json.dumps({"mcpServers": {"servidor_externo": {"command": "node", "args": ["srv.js"]}}}),
        encoding="utf-8",
    )

    dir_config = casa / ".gemini" / "config"
    dir_config.mkdir(parents=True, exist_ok=True)
    archivo_vigente = dir_config / "mcp_config.json"
    archivo_vigente.write_text(
        json.dumps({"mcpServers": {"otro_servidor": {"command": "python", "args": ["app.py"]}}}),
        encoding="utf-8",
    )

    installer.configure_antigravity()

    # Ambas rutas deben estar actualizadas
    datos_ant = json.loads(archivo_anterior.read_text(encoding="utf-8"))
    assert "servidor_externo" in datos_ant["mcpServers"]
    assert "desktop-lancedb" in datos_ant["mcpServers"]

    datos_vig = json.loads(archivo_vigente.read_text(encoding="utf-8"))
    assert "otro_servidor" in datos_vig["mcpServers"]
    assert "desktop-lancedb" in datos_vig["mcpServers"]

    # Debe haberse creado copia .bak al modificar archivos existentes
    baks_ant = list(dir_anterior.glob("mcp_config.json.bak-*"))
    assert len(baks_ant) >= 1

    baks_vig = list(dir_config.glob("mcp_config.json.bak-*"))
    assert len(baks_vig) >= 1


def test_instalador_json_ilegible_no_sobrescribe(casa):
    archivo_roto = casa / "invalido.json"
    contenido_original = "{ este json no tiene formato valido"
    archivo_roto.write_text(contenido_original, encoding="utf-8")

    resultado = installer._registrar_json(archivo_roto)
    assert resultado == installer.OMITIDO
    assert archivo_roto.read_text(encoding="utf-8") == contenido_original


def test_instalador_run_uninstall(casa):
    (casa / ".gemini" / "antigravity").mkdir(parents=True, exist_ok=True)
    installer.configure_antigravity()

    vigente = casa / ".gemini" / "config" / "mcp_config.json"
    gemini_md = casa / ".gemini" / "GEMINI.md"

    assert "desktop-lancedb" in json.loads(vigente.read_text(encoding="utf-8"))["mcpServers"]
    assert installer.BLOQUE_INI in gemini_md.read_text(encoding="utf-8")

    installer.run_uninstall()

    datos_despues = json.loads(vigente.read_text(encoding="utf-8"))
    assert "desktop-lancedb" not in datos_despues.get("mcpServers", {})
    assert installer.BLOQUE_INI not in gemini_md.read_text(encoding="utf-8")


def test_instalador_dry_run_no_escribe_nada(casa, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["installer.py", "--dry-run"])
    importlib.reload(installer)
    assert installer.DRY_RUN is True

    try:
        (casa / ".gemini" / "antigravity").mkdir(parents=True, exist_ok=True)
        installer.configure_antigravity()

        target = casa / ".gemini" / "config" / "mcp_config.json"
        assert not target.exists()

        gemini_md = casa / ".gemini" / "GEMINI.md"
        assert not gemini_md.exists()
    finally:
        # Restaurar sys.argv y reload de installer
        monkeypatch.setattr(sys, "argv", ["pytest"])
        importlib.reload(installer)
