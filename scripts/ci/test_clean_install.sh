#!/usr/bin/env bash
# ==============================================================================
# Prueba de instalacion limpia de SyntaxRAG (SYNRAG)
#
# Ejecuta install.sh en un HOME temporal vacio, crea un proyecto de ejemplo
# en $HOME/Projects, indexa el codigo, realiza una busqueda CLI y valida
# el servidor MCP por stdio mediante scripts/ci/mcp_tools_list.py.
# ==============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# Configurar entorno temporal aislado para que no herede configuracion del sistema
TMP_HOME="${CLEAN_HOME:-$(mktemp -d)}"
echo "[INFO] Usando HOME temporal aislado: $TMP_HOME"

export HOME="$TMP_HOME"
export XDG_CONFIG_HOME="$TMP_HOME/.config"
export XDG_DATA_HOME="$TMP_HOME/.local/share"
unset SYNRAG_CARPETAS || true
unset SYNRAG_DB_PATH || true

cleanup() {
    if [ -z "${PRESERVE_CLEAN_HOME:-}" ] && [ -d "$TMP_HOME" ]; then
        echo "[INFO] Limpiando directorio temporal $TMP_HOME ..."
        rm -rf "$TMP_HOME"
    fi
}
trap cleanup EXIT

# 1. Ejecutar instalacion
echo "================================================================================"
echo "[1/4] Ejecutando install.sh en HOME temporal ..."
echo "================================================================================"
bash "$REPO_ROOT/install.sh"

export PATH="$TMP_HOME/.local/bin:$PATH"

# 2. Crear proyecto de ejemplo en $HOME/Projects
echo "================================================================================"
echo "[2/4] Creando proyecto de ejemplo en $TMP_HOME/Projects/ejemplo ..."
echo "================================================================================"
mkdir -p "$TMP_HOME/Projects/ejemplo"
cat << 'EOF' > "$TMP_HOME/Projects/ejemplo/calc.py"
def calcular_suma(a: int, b: int) -> int:
    """Suma dos numeros enteros."""
    return a + b

def calcular_producto(a: int, b: int) -> int:
    """Multiplica dos numeros enteros."""
    return a * b
EOF

# 3. Indexar y buscar
echo "================================================================================"
echo "[3/4] Indexando proyecto de ejemplo con SYNRAG index ..."
echo "================================================================================"
INDEX_OUT="$("$TMP_HOME/.local/bin/SYNRAG" index 2>&1)"
echo "$INDEX_OUT"

if echo "$INDEX_OUT" | grep -q "Nada que indexar"; then
    echo "[ERROR] SYNRAG index no encontro archivos para indexar en $TMP_HOME/Projects." >&2
    exit 1
fi

echo "================================================================================"
echo "[3/4] Buscando funcion 'calcular_suma' por CLI ..."
echo "================================================================================"
SEARCH_OUT="$("$TMP_HOME/.local/bin/SYNRAG" calcular_suma 2>&1)"
echo "$SEARCH_OUT"

# Comprobamos que el resultado contenga la definicion real y el archivo, no solo la cabecera
if echo "$SEARCH_OUT" | grep -q "calc.py" && echo "$SEARCH_OUT" | grep -q "def calcular_suma"; then
    echo "[OK] Busqueda CLI encontro la definicion de 'calcular_suma' en calc.py correctamente."
else
    echo "[ERROR] La busqueda CLI no devolvio el resultado esperado para 'calcular_suma'." >&2
    exit 1
fi

# 4. Validar MCP por stdio
echo "================================================================================"
echo "[4/4] Verificando servidor MCP por stdio (tools/list sin outputSchema) ..."
echo "================================================================================"
python3 "$REPO_ROOT/scripts/ci/mcp_tools_list.py" \
    "$TMP_HOME/.local/opt/lancedb-hub/.venv/bin/python" \
    "$TMP_HOME/.local/opt/lancedb-hub/server_mcp.py"

echo "================================================================================"
echo "[OK] Verificacion de instalacion limpia completada con exito."
echo "================================================================================"
