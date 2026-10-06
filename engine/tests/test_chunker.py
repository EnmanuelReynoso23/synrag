from pathlib import Path
import pytest
import chunker


def test_chunker_typescript():
    codigo = """import { useState, useEffect } from "react";
import { apiCliente } from "./api/cliente";

export interface Usuario {
    id: string;
    nombre: string;
    activo: boolean;
}

export function obtenerUsuario(id: string): Usuario {
    const usuario = apiCliente.get(id);
    return usuario;
}

export const servicio = {
    obtener: obtenerUsuario,
    version: "1.0.0",
};
"""
    chunks = chunker.chunk_file(Path("usuario.ts"), codigo)
    assert len(chunks) >= 3

    # Fragmento de imports
    import_chunks = [c for c in chunks if c["symbol_name"] == "imports"]
    assert len(import_chunks) == 1
    assert "import { useState" in import_chunks[0]["content"]

    # Fragmento de interfaz
    interface_chunks = [c for c in chunks if c["symbol_name"] == "Usuario"]
    assert len(interface_chunks) == 1
    assert interface_chunks[0]["symbol_kind"] == "interface"
    assert interface_chunks[0]["line"] <= interface_chunks[0]["end_line"]
    assert "export interface Usuario" in interface_chunks[0]["content"]

    # Fragmento de función
    func_chunks = [c for c in chunks if c["symbol_name"] == "obtenerUsuario"]
    assert len(func_chunks) == 1
    fc = func_chunks[0]
    assert "function obtenerUsuario" in fc["content"]
    assert "return usuario;" in fc["content"]
    assert fc["line"] <= fc["end_line"]

    # Fragmento de const servicio
    srv_chunks = [c for c in chunks if c["symbol_name"] == "servicio"]
    assert len(srv_chunks) == 1
    assert "export const servicio" in srv_chunks[0]["content"]


def test_chunker_python():
    codigo = """class GestorCuentas:
    def __init__(self, saldo_inicial: float):
        self.saldo = saldo_inicial

    def depositar(self, monto: float) -> float:
        self.saldo += monto
        return self.saldo


def calcular_interes(monto: float, tasa: float) -> float:
    return monto * (tasa / 100.0)
"""
    chunks = chunker.chunk_file(Path("cuentas.py"), codigo)
    assert len(chunks) == 2

    nombres = {c["symbol_name"] for c in chunks}
    assert "GestorCuentas" in nombres
    assert "calcular_interes" in nombres

    for c in chunks:
        assert c["line"] <= c["end_line"]
        assert len(c["content"]) >= chunker.MIN_CHUNK_CHARS


def test_chunker_funcion_larga_produce_multiples_fragmentos():
    lineas = ["def funcion_extensa():"]
    lineas.extend([f"    variable_{i} = 'valor_largo_de_prueba_para_rellenar_{i}'" for i in range(120)])
    codigo = "\n".join(lineas)
    assert len(codigo) > chunker.MAX_CHUNK_CHARS

    chunks = chunker.chunk_file(Path("extenso.py"), codigo)
    assert len(chunks) >= 2
    for c in chunks:
        assert c["symbol_name"] == "funcion_extensa"


def test_chunker_markdown():
    doc = """# Documento de Arquitectura
Este es el resumen general de la arquitectura del sistema distribuido.

## Modulo de Autenticacion
Detalles tecnicos sobre el protocolo de autenticacion y sesiones.

## Modulo de Base de Datos
Esquemas de almacenamiento local y politicas de retencion de datos.
"""
    chunks, imps, exps = chunker.chunk_markdown(doc)
    assert len(chunks) == 3
    assert imps == []
    assert exps == []

    titulos = [c["symbol_name"] for c in chunks]
    assert titulos == ["Documento de Arquitectura", "Modulo de Autenticacion", "Modulo de Base de Datos"]
    for c in chunks:
        assert c["symbol_kind"] == "section"
        assert c["line"] <= c["end_line"]


def test_chunker_sql():
    sql = """
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE usuarios ADD COLUMN correo VARCHAR(255);
"""
    chunks, imps, exps = chunker.chunk_sql(sql)
    assert len(chunks) == 2
    assert imps == []
    assert exps == []

    assert chunks[0]["symbol_name"] == "usuarios"
    assert chunks[0]["symbol_kind"] == "sql"
    assert "CREATE TABLE usuarios" in chunks[0]["content"]

    assert chunks[1]["symbol_name"] == "usuarios"
    assert chunks[1]["symbol_kind"] == "sql"
    assert "ALTER TABLE usuarios" in chunks[1]["content"]


def test_chunker_extension_sin_gramatica():
    texto = (
        "Este es un archivo de notas plano sin soporte de gramatica en Tree-sitter.\n"
        "El motor debe recurrir al algoritmo de fallback de lineas limpias sin fallar.\n"
        "Verificamos que devuelva al menos un fragmento valido con tipo de simbolo de texto plano."
    )
    chunks = chunker.chunk_file(Path("notas.txt"), texto)
    assert len(chunks) >= 1
    assert chunks[0]["symbol_kind"] == "text"
    assert len(chunks[0]["content"]) >= chunker.MIN_CHUNK_CHARS


def test_chunker_rust_y_go_comportamiento_actual():
    # Comportamiento documentado actual: devuelven fragmentos pero con symbol_name vacio
    codigo_rs = """
fn calcular_total(a: i32, b: i32) -> i32 {
    a + b
}
"""
    chunks_rs = chunker.chunk_file(Path("lib.rs"), codigo_rs)
    assert len(chunks_rs) >= 1
    assert chunks_rs[0]["symbol_name"] == ""

    codigo_go = """
func CalcularTotal(a int, b int) int {
    return a + b
}
"""
    chunks_go = chunker.chunk_file(Path("main.go"), codigo_go)
    assert len(chunks_go) >= 1
    assert chunks_go[0]["symbol_name"] == ""


@pytest.mark.xfail(reason="Issue #17: Rust y Go devuelven fragmentos sin nombre de simbolo (LANG_MAP no extrae simbolos)")
def test_chunker_rust_y_go_extraccion_simbolos():
    codigo_rs = """
fn calcular_total(a: i32, b: i32) -> i32 {
    a + b
}
"""
    chunks_rs = chunker.chunk_file(Path("lib.rs"), codigo_rs)
    assert chunks_rs[0]["symbol_name"] == "calcular_total"

    codigo_go = """
func CalcularTotal(a int, b int) int {
    return a + b
}
"""
    chunks_go = chunker.chunk_file(Path("main.go"), codigo_go)
    assert chunks_go[0]["symbol_name"] == "CalcularTotal"
