#!/usr/bin/env bash
# ==============================================================================
# SyntaxRAG (SYNRAG) - Instalador universal y auto-configurador multi-IA
#
#   curl -sSL https://raw.githubusercontent.com/EnmanuelReynoso23/synrag/main/install.sh | bash
#   ./install.sh            (desde el repositorio clonado)
#   ./install.sh --dry-run  (muestra que IAs configuraria, sin escribir nada)
#
# Linux, macOS y Windows con WSL. Todo corre en CPU y en local, sin tokens de API.
# Si algo falla, el instalador se detiene y dice QUE fallo; nunca deja a medias en silencio.
# ==============================================================================
set -euo pipefail

REPO_RAW="${SYNRAG_RAW_URL:-https://raw.githubusercontent.com/EnmanuelReynoso23/synrag/main}"
INSTALL_DIR="${SYNRAG_HOME:-$HOME/.local/opt/lancedb-hub}"
PYTHON_CMD="${PYTHON_CMD:-python3}"
ENGINE_FILES=(cache.py chunker.py cli.py impact.py indexer.py installer.py ranker.py server_mcp.py telemetry.py watcher.py)
DEPENDENCIAS=(lancedb rich tree-sitter tree-sitter-language-pack flashrank mcp watchdog pandas)

fallo() { echo "[ERROR] $*" >&2; exit 1; }

echo "================================================================================"
echo "          INSTALANDO SYNTAXRAG (SYNRAG) - ARQUITECTURA STANDALONE"
echo "================================================================================"

# --- 0. Requisitos -----------------------------------------------------------
command -v "$PYTHON_CMD" >/dev/null 2>&1 || fallo "no encuentro $PYTHON_CMD. Instala Python 3.10 o superior."
"$PYTHON_CMD" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
    || fallo "se necesita Python 3.10 o superior (tienes $("$PYTHON_CMD" -V 2>&1))."
"$PYTHON_CMD" -c 'import venv, ensurepip' 2>/dev/null \
    || fallo "falta el modulo venv. En Debian/Ubuntu: sudo apt install python3-venv"

mkdir -p "$INSTALL_DIR" "$HOME/.local/bin"

# --- 1. Motor: desde el repo clonado o descargado ----------------------------
ORIGEN=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    [ -f "$AQUI/engine/installer.py" ] && ORIGEN="$AQUI/engine"
fi

if [ -n "$ORIGEN" ]; then
    echo "[1/4] Copiando el motor desde $ORIGEN ..."
    for f in "${ENGINE_FILES[@]}"; do
        [ -f "$ORIGEN/$f" ] || fallo "falta $ORIGEN/$f en el repositorio."
        cp "$ORIGEN/$f" "$INSTALL_DIR/$f"
    done
else
    echo "[1/4] Descargando el motor desde $REPO_RAW ..."
    command -v curl >/dev/null 2>&1 || fallo "necesito curl para descargar el motor."
    for f in "${ENGINE_FILES[@]}"; do
        curl -fsSL "$REPO_RAW/engine/$f" -o "$INSTALL_DIR/$f.tmp" \
            || { rm -f "$INSTALL_DIR/$f.tmp"; fallo "no pude descargar engine/$f desde $REPO_RAW (revisa tu conexion)."; }
        mv "$INSTALL_DIR/$f.tmp" "$INSTALL_DIR/$f"
    done
fi

# --- 2. Entorno virtual y dependencias ---------------------------------------
if [ ! -x "$INSTALL_DIR/.venv/bin/python" ]; then
    echo "[2/4] Creando entorno virtual aislado en $INSTALL_DIR/.venv ..."
    "$PYTHON_CMD" -m venv "$INSTALL_DIR/.venv" || fallo "no pude crear el entorno virtual."
fi
VENV_PY="$INSTALL_DIR/.venv/bin/python"

echo "[2/4] Instalando dependencias (primera vez puede tardar unos minutos) ..."
"$VENV_PY" -m pip install --quiet --upgrade pip setuptools wheel \
    || fallo "pip no pudo actualizarse."
"$VENV_PY" -m pip install --quiet "${DEPENDENCIAS[@]}" \
    || fallo "no se pudieron instalar las dependencias (${DEPENDENCIAS[*]}). Ejecuta sin --quiet para ver el motivo: $VENV_PY -m pip install ${DEPENDENCIAS[*]}"
"$VENV_PY" -c 'import lancedb, rich, tree_sitter, tree_sitter_language_pack, flashrank, mcp, watchdog' \
    || fallo "las dependencias se instalaron pero no se pueden importar."

# --- 3. Configurar las IAs instaladas ----------------------------------------
echo "[3/4] Configurando las IAs instaladas en este equipo ..."
"$VENV_PY" "$INSTALL_DIR/installer.py" "$@" || fallo "el auto-configurador de IAs fallo."

# --- 4. Comprobacion final ---------------------------------------------------
echo "[4/4] Comprobando la instalacion ..."
"$VENV_PY" "$INSTALL_DIR/cli.py" --stats >/dev/null 2>&1 \
    || fallo "SYNRAG se instalo pero no arranca. Prueba: $VENV_PY $INSTALL_DIR/cli.py"

case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) echo "[AVISO] ~/.local/bin no esta en tu PATH. Anade: export PATH=\"\$HOME/.local/bin:\$PATH\"" ;;
esac

echo ""
echo "[OK] SYNTAXRAG INSTALADO. Reinicia tus IAs y prueba en la terminal: SYNRAG"
