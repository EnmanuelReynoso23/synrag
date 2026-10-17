#!/usr/bin/env python3
"""
engine/conciso.py - Modo conciso (Caveman) opcional para SyntaxRAG

Inyecta o retira un bloque de instrucciones en los archivos globales de las IAs
instaladas (CLAUDE.md, GEMINI.md, AGENTS.md, etc.) para que respondan de forma
directa, tecnica y sin relleno, conservando siempre el codigo y comandos completos.

Basado en el enfoque y reglas de Caveman por Julius Brussee (licencia Apache-2.0).
https://github.com/JuliusBrussee/caveman
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import installer

BLOQUE_CONCISO_INI = "<!-- SYNRAG-CONCISO:BEGIN -->"
BLOQUE_CONCISO_FIN = "<!-- SYNRAG-CONCISO:END -->"

# Bloque de instrucciones concisas. Reglas obligatorias:
# 1. Codigo, comandos, rutas y mensajes de error completos y exactos.
# 2. Preguntas al usuario y avisos de seguridad en oraciones completas.
# 3. Sin emojis.
BLOQUE_CONCISO_INSTRUCCIONES = f"""{BLOQUE_CONCISO_INI}
## Modo conciso (estilo Caveman de Julius Brussee, Apache-2.0)
- Directo: respuesta primero
- Sin relleno, saludos ni disculpas
- Cero emojis
- Cero teatro: habla normal
- Codigo, comandos, rutas, errores y nombres de simbolos: completos y literales
- Preguntas al usuario y avisos de seguridad o acciones destructivas: oraciones completas
{BLOQUE_CONCISO_FIN}
"""


def _get_home() -> Path:
    return Path(os.environ.get("HOME", str(Path.home())))


def destinos_instrucciones() -> List[Tuple[str, Path]]:
    """Detecta las IAs instaladas y devuelve las tuplas (nombre_ia, ruta_archivo_instrucciones)."""
    home = _get_home()
    destinos: List[Tuple[str, Path]] = []

    # Claude Code
    if installer._instalada(dirs=[home / ".claude"], binarios=["claude"]):
        destinos.append(("Claude Code", home / ".claude" / "CLAUDE.md"))

    # Google Antigravity
    if installer._instalada(dirs=[home / ".gemini" / "antigravity"], binarios=["antigravity", "agy"]):
        destinos.append(("Google Antigravity", home / ".gemini" / "GEMINI.md"))

    # Gemini CLI (solo si no fue cubierto por Antigravity con el mismo archivo)
    if (installer._instalada(binarios=["gemini"]) or (home / ".gemini" / "settings.json").exists()):
        ruta_gemini = home / ".gemini" / "GEMINI.md"
        if not any(r == ruta_gemini for _, r in destinos):
            destinos.append(("Gemini CLI", ruta_gemini))

    # Codex CLI
    if installer._instalada(dirs=[home / ".codex"], binarios=["codex"]):
        destinos.append(("Codex CLI", home / ".codex" / "AGENTS.md"))

    # Windsurf
    if installer._instalada(dirs=[home / ".codeium" / "windsurf", home / ".config" / "Windsurf"], binarios=["windsurf"]):
        destinos.append(("Windsurf", home / ".codeium" / "windsurf" / "memories" / "global_rules.md"))

    return destinos


def todas_las_rutas_posibles() -> List[Path]:
    """Lista de todas las rutas de instrucciones soportadas para limpieza segura."""
    home = _get_home()
    return [
        home / ".claude" / "CLAUDE.md",
        home / ".gemini" / "GEMINI.md",
        home / ".codex" / "AGENTS.md",
        home / ".codeium" / "windsurf" / "memories" / "global_rules.md",
    ]


def inyectar_conciso(path: Path, dry_run: bool = False) -> str:
    """Inserta o actualiza el bloque de modo conciso entre marcas, sin tocar el resto del archivo."""
    try:
        real = path.resolve() if path.is_symlink() else path
        texto = real.read_text(encoding="utf-8") if real.is_file() else ""

        if BLOQUE_CONCISO_INI in texto and BLOQUE_CONCISO_FIN in texto:
            ini = texto.index(BLOQUE_CONCISO_INI)
            fin = texto.index(BLOQUE_CONCISO_FIN) + len(BLOQUE_CONCISO_FIN)
            nuevo = texto[:ini] + BLOQUE_CONCISO_INSTRUCCIONES.rstrip("\n") + texto[fin:]
        else:
            nuevo = texto.rstrip("\n") + ("\n\n" if texto.strip() else "") + BLOQUE_CONCISO_INSTRUCCIONES

        if nuevo == texto:
            installer._log(installer.YA, f"modo conciso en {path}")
            return installer.YA

        if not dry_run:
            installer._escribir(real, nuevo)
        installer._log(installer.OK, f"modo conciso en {path}", "simulado" if dry_run else "")
        return installer.OK
    except Exception as e:
        installer._log(installer.ERROR, f"modo conciso en {path}", str(e))
        return installer.ERROR


def quitar_conciso(path: Path, dry_run: bool = False) -> str:
    """Quita el bloque de modo conciso entre marcas, dejando intacto el resto del archivo."""
    try:
        real = path.resolve() if path.is_symlink() else path
        if not real.is_file():
            return installer.YA
        texto = real.read_text(encoding="utf-8")
        if BLOQUE_CONCISO_INI not in texto or BLOQUE_CONCISO_FIN not in texto:
            return installer.YA

        ini = texto.index(BLOQUE_CONCISO_INI)
        fin = texto.index(BLOQUE_CONCISO_FIN) + len(BLOQUE_CONCISO_FIN)
        nuevo = (texto[:ini].rstrip("\n") + "\n" + texto[fin:].lstrip("\n")).strip("\n")

        if not dry_run:
            installer._escribir(real, (nuevo + "\n") if nuevo else "")
        installer._log(installer.OK, f"modo conciso quitado de {path}", "simulado" if dry_run else "")
        return installer.OK
    except Exception as e:
        installer._log(installer.ERROR, f"modo conciso en {path}", str(e))
        return installer.ERROR


def activar(dry_run: Optional[bool] = None) -> List[str]:
    """Activa el modo conciso en todas las IAs instaladas en el sistema."""
    is_dry = installer.DRY_RUN if dry_run is None else dry_run
    print("=" * 80)
    print("   ACTIVANDO MODO CONCISO EN TUS IAS (INSPIRADO EN CAVEMAN)" + ("  [SIMULACION]" if is_dry else ""))
    print("=" * 80)

    destinos = destinos_instrucciones()
    activadas: List[str] = []

    for nombre_ia, ruta in destinos:
        res = inyectar_conciso(ruta, dry_run=is_dry)
        if res in (installer.OK, installer.YA):
            activadas.append(nombre_ia)

    print("-" * 80)
    if activadas:
        print(f"Modo conciso activo ({len(activadas)}): {', '.join(sorted(set(activadas)))}")
        print("Las IAs responderan de forma corta y directa, manteniendo codigo y comandos completos.")
    else:
        print("No se encontraron IAs instaladas para configurar el modo conciso.")
    print("=" * 80)
    return activadas


def desactivar(dry_run: Optional[bool] = None) -> List[str]:
    """Desactiva el modo conciso retirando el bloque de instrucciones de las IAs."""
    is_dry = installer.DRY_RUN if dry_run is None else dry_run
    print("=" * 80)
    print("   DESACTIVANDO MODO CONCISO EN TUS IAS" + ("  [SIMULACION]" if is_dry else ""))
    print("=" * 80)

    desactivadas: List[str] = []
    rutas = todas_las_rutas_posibles()

    for ruta in rutas:
        real = ruta.resolve() if ruta.is_symlink() else ruta
        if real.is_file() and BLOQUE_CONCISO_INI in real.read_text(encoding="utf-8", errors="ignore"):
            res = quitar_conciso(ruta, dry_run=is_dry)
            if res == installer.OK:
                desactivadas.append(ruta.name)

    print("-" * 80)
    print("Modo conciso retirado. Las IAs volveran a su estilo de respuesta habitual.")
    print("=" * 80)
    return desactivadas


def estado() -> Dict[str, bool]:
    """Reporta el estado del modo conciso por archivo de instrucciones."""
    res: Dict[str, bool] = {}
    for ruta in todas_las_rutas_posibles():
        real = ruta.resolve() if ruta.is_symlink() else ruta
        if real.is_file():
            res[str(ruta)] = BLOQUE_CONCISO_INI in real.read_text(encoding="utf-8", errors="ignore")
    return res


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        desactivar()
    else:
        activar()
