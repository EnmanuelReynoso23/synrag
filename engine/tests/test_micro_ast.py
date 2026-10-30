import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from micro_ast import MicroASTCompressor, comprimir_a_micro_ast


def test_micro_ast_compresion_python():
    codigo = """def procesar_pedido(cliente_id: int, total: float) -> bool:
    \"\"\"Calcula descuentos, valida stock y persiste transaccion en base de datos.\"\"\"
    # Validacion inicial de parametros
    print(f"Iniciando pedido para cliente {cliente_id}")
    if total <= 0:
        return False

    logger.info("Verificando balance")
    descuento = 0.10 if total > 100 else 0.0
    self.saldo_actual = total - (total * descuento)

    try:
        resultado = ejecutar_pago(cliente_id, self.saldo_actual)
        return True
    except Exception as e:
        print(f"Error procesando: {e}")
        return False
"""
    res = comprimir_a_micro_ast(codigo)
    assert res["caracteres_comprimido"] < res["caracteres_original"]
    assert res["ahorro_estimado_pct"] > 35.0
    # Firmas y control clave preservados
    assert "def procesar_pedido" in res["micro_ast"]
    assert "if total <= 0:" in res["micro_ast"]
    assert "return False" in res["micro_ast"]
    assert "return True" in res["micro_ast"]
    # Logs y comentarios podados
    assert "print(" not in res["micro_ast"]
    assert "logger.info" not in res["micro_ast"]
    assert "Validacion inicial" not in res["micro_ast"]


def test_micro_ast_compresion_typescript():
    codigo = """export async function authenticateUser(token: string): Promise<User> {
    // Validar token en redis
    console.log("Validating token...");
    if (!token) {
        throw new Error("Token missing");
    }
    const session = await db.sessions.find(token);
    if (!session) {
        return null;
    }
    return session.user;
}"""
    compresor = MicroASTCompressor()
    salida = compresor.comprimir_funcion(codigo)
    assert "export async function authenticateUser" in salida
    assert "if (!token)" in salida
    assert "throw new Error" in salida
    assert "console.log" not in salida
    assert "Validar token" not in salida
