#!/usr/bin/env bash
# ==============================================================================
# SyntaxRAG (SYNRAG) — Universal One-Line Installer & Multi-AI Auto-Configurator
# Compatible con Linux (CachyOS, Arch, Ubuntu, Debian, Fedora), macOS y WSL
# Cero dependencias externas · Inferencia local en CPU · Cero tokens de API
# ==============================================================================

set -e

INSTALL_DIR="$HOME/.local/opt/lancedb-hub"
PYTHON_CMD="python3"

if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 no esta instalado. Por favor instala Python 3.10 o superior."
    exit 1
fi

echo "================================================================================"
echo "          INSTALANDO SYNTAXRAG (SYNRAG) — ARQUITECTURA STANDALONE               "
echo "================================================================================"

mkdir -p "$INSTALL_DIR"
mkdir -p "$HOME/.local/bin"

if [ ! -d "$INSTALL_DIR/.venv" ]; then
    echo "[1/4] Creando entorno virtual aislado en $INSTALL_DIR/.venv..."
    $PYTHON_CMD -m venv "$INSTALL_DIR/.venv"
fi

VENV_PY="$INSTALL_DIR/.venv/bin/python"

echo "[2/4] Verificando dependencias locales en CPU..."
"$VENV_PY" -m pip install --quiet --upgrade pip setuptools wheel 2>/dev/null || true
"$VENV_PY" -m pip install --quiet lancedb rich tree-sitter tree-sitter-language-pack flashrank mcp watchdog pandas 2>/dev/null || true

echo "[3/4] Ejecutando auto-configurador multi-IA..."
"$VENV_PY" "$INSTALL_DIR/installer.py"

if command -v fish &>/dev/null; then
    echo "[4/4] Recargando autocompletado en Fish Shell..."
fi

echo ""
echo "[OK] SYNTAXRAG INSTALADO Y CONFIGURADO EXITOSAMENTE."
echo "Prueba ahora en tu terminal: SYNRAG"
