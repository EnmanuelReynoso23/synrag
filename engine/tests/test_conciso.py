import importlib
import sys
from pathlib import Path

import conciso
import installer
import cli


def test_conciso_no_se_activa_con_instalacion_normal(casa):
    # Simular Claude Code instalado
    claude_dir = casa / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    claude_md = claude_dir / "CLAUDE.md"
    claude_md.write_text("# Instrucciones de usuario previas\n", encoding="utf-8")

    # Ejecutar la instalacion normal de Claude Code
    res = installer.configure_claude_code()
    assert "Claude Code" in res

    contenido = claude_md.read_text(encoding="utf-8")
    # El bloque normal de SYNRAG debe estar presente
    assert installer.BLOQUE_INI in contenido
    assert installer.BLOQUE_FIN in contenido

    # El bloque conciso NO debe estar presente tras instalacion normal
    assert conciso.BLOQUE_CONCISO_INI not in contenido
    assert conciso.BLOQUE_CONCISO_FIN not in contenido


def test_conciso_activar_idempotente(casa):
    claude_dir = casa / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    claude_md = claude_dir / "CLAUDE.md"
    original = "# Mis reglas previas\n- Regla 1: mantener arquitectura limpia.\n"
    claude_md.write_text(original, encoding="utf-8")

    # 1. Primera llamada a activar
    activadas1 = conciso.activar()
    assert "Claude Code" in activadas1

    texto1 = claude_md.read_text(encoding="utf-8")
    assert original.strip() in texto1
    assert conciso.BLOQUE_CONCISO_INI in texto1
    assert conciso.BLOQUE_CONCISO_FIN in texto1
    # Reglas obligatorias presentes
    assert "Cero emojis" in texto1
    assert "Apache-2.0" in texto1
    assert "completos y literales" in texto1

    # 2. Segunda llamada: debe ser idempotente y no duplicar el bloque
    activadas2 = conciso.activar()
    assert "Claude Code" in activadas2

    texto2 = claude_md.read_text(encoding="utf-8")
    assert texto2.count(conciso.BLOQUE_CONCISO_INI) == 1
    assert texto2.count(conciso.BLOQUE_CONCISO_FIN) == 1
    assert texto2 == texto1


def test_conciso_desactivar_deja_resto_intacto(casa):
    claude_dir = casa / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    claude_md = claude_dir / "CLAUDE.md"

    parte_usuario = "# Reglas de usuario\n- No tocar la configuracion de red.\n"
    parte_synrag = f"{installer.BLOQUE_INI}\n## SyntaxRAG\n{installer.BLOQUE_FIN}\n"
    claude_md.write_text(f"{parte_usuario}\n{parte_synrag}", encoding="utf-8")

    # Activar conciso
    conciso.activar()
    texto_activo = claude_md.read_text(encoding="utf-8")
    assert conciso.BLOQUE_CONCISO_INI in texto_activo
    assert parte_usuario.strip() in texto_activo
    assert installer.BLOQUE_INI in texto_activo

    # Desactivar conciso
    desactivadas = conciso.desactivar()
    assert "CLAUDE.md" in desactivadas

    texto_final = claude_md.read_text(encoding="utf-8")
    # El bloque conciso se elimino
    assert conciso.BLOQUE_CONCISO_INI not in texto_final
    assert conciso.BLOQUE_CONCISO_FIN not in texto_final
    # El resto del archivo quedo intacto
    assert parte_usuario.strip() in texto_final
    assert installer.BLOQUE_INI in texto_final
    assert installer.BLOQUE_FIN in texto_final


def test_conciso_desactivar_idempotente(casa):
    claude_dir = casa / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    claude_md = claude_dir / "CLAUDE.md"
    claude_md.write_text("# Archivo sin conciso\n", encoding="utf-8")

    # Desactivar cuando no estaba activo no debe fallar
    desactivadas = conciso.desactivar()
    assert desactivadas == []
    assert claude_md.read_text(encoding="utf-8") == "# Archivo sin conciso\n"


def test_conciso_dry_run(casa):
    claude_dir = casa / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    claude_md = claude_dir / "CLAUDE.md"
    claude_md.write_text("# Archivo previo\n", encoding="utf-8")

    # Activar en modo dry_run
    conciso.activar(dry_run=True)
    assert conciso.BLOQUE_CONCISO_INI not in claude_md.read_text(encoding="utf-8")


def test_conciso_symlink_resolucion(casa):
    # Simular setup donde GEMINI.md es enlace simbolico a CLAUDE.md
    claude_dir = casa / ".claude"
    gemini_dir = casa / ".gemini"
    claude_dir.mkdir(parents=True, exist_ok=True)
    gemini_dir.mkdir(parents=True, exist_ok=True)

    claude_md = claude_dir / "CLAUDE.md"
    claude_md.write_text("# Fuente compartida\n", encoding="utf-8")

    gemini_md = gemini_dir / "GEMINI.md"
    gemini_md.symlink_to(claude_md)

    # Activar conciso
    conciso.activar()

    # El enlace se mantiene y el contenido real tiene el bloque
    assert gemini_md.is_symlink()
    assert conciso.BLOQUE_CONCISO_INI in claude_md.read_text(encoding="utf-8")
    assert conciso.BLOQUE_CONCISO_INI in gemini_md.read_text(encoding="utf-8")

    # Desactivar conciso
    conciso.desactivar()
    assert gemini_md.is_symlink()
    assert conciso.BLOQUE_CONCISO_INI not in claude_md.read_text(encoding="utf-8")
    assert conciso.BLOQUE_CONCISO_INI not in gemini_md.read_text(encoding="utf-8")


def test_cli_configure_uninstall_conciso(casa, monkeypatch):
    claude_dir = casa / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    claude_md = claude_dir / "CLAUDE.md"
    claude_md.write_text("# Reglas de prueba\n", encoding="utf-8")

    # Probar SYNRAG configure --conciso
    monkeypatch.setattr(sys, "argv", ["SYNRAG", "configure", "--conciso"])
    cli.main()
    assert conciso.BLOQUE_CONCISO_INI in claude_md.read_text(encoding="utf-8")

    # Probar SYNRAG uninstall --conciso
    monkeypatch.setattr(sys, "argv", ["SYNRAG", "uninstall", "--conciso"])
    cli.main()
    assert conciso.BLOQUE_CONCISO_INI not in claude_md.read_text(encoding="utf-8")
