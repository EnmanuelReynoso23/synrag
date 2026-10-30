import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from duplicates import ASTCloneDetector, detectar_clones_ast


def test_detector_clones_identicos_con_variables_renombradas():
    # Funcion Original
    fn_original = """def calcular_precio_final(precio: float, impuesto: float) -> float:
    base = precio * (1.0 + impuesto)
    if base > 1000:
        return base * 0.95
    return base
"""
    # Funcion Clonada (copypaste donde cambiaron nombres de variables)
    fn_copiada = """def obtener_costo_total(monto: float, tasa: float) -> float:
    subtotal = monto * (1.0 + tasa)
    if subtotal > 1000:
        return subtotal * 0.95
    return subtotal
"""
    res = detectar_clones_ast(fn_original, fn_copiada)
    assert res["es_duplicado"] is True
    assert res["similitud"] == 1.0
    assert res["hash_a"] == res["hash_b"]
    assert res["dictamen"] == "CLON ESTRUCTURAL DETECTADO"


def test_detector_funciones_distintas():
    fn_a = """def sumar(a, b):
    return a + b
"""
    fn_b = """def conectar_socket(host, puerto):
    sock = socket.create_connection((host, puerto))
    sock.settimeout(5.0)
    return sock
"""
    res = detectar_clones_ast(fn_a, fn_b)
    assert res["es_duplicado"] is False
    assert res["hash_a"] != res["hash_b"]
