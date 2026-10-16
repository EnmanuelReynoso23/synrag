from pathlib import Path
import pytest
import chunker
import indexer
import server_mcp
from conftest import crear_proyecto


def test_fragmentos_limite_caracteres():
    # Párrafo extenso que excede 800 caracteres
    parrafo_largo = "Esta es una explicacion detallada sobre la configuracion del sistema distribuido. " * 25
    doc_md = f"""# Documentacion de Rendimiento

{parrafo_largo}

## Subseccion de Memoria

{parrafo_largo}
"""
    chunks, imps, exps = chunker.chunk_markdown(doc_md)
    assert len(chunks) >= 4
    for c in chunks:
        assert len(c["content"]) <= chunker.MAX_DOC_CHARS
        assert c["line"] <= c["end_line"]
        assert c["symbol_kind"] == "section"
        assert c["content"].startswith("# Documentacion de Rendimiento")


def test_bloque_codigo_cercado_no_se_parte():
    codigo = (
        "def procesar_lote_elementos(items):\n"
        "    # Bloque de codigo cercado con multiples lineas\n"
        "    resultado = []\n"
        "    for item in items:\n"
        "        resultado.append(item * 2)\n"
        "    return resultado\n"
    )
    texto_antes = "Texto de introduccion antes del bloque de codigo. " * 8
    texto_despues = "Texto de explicacion posterior al bloque de codigo. " * 8
    doc = f"""# Guia de Implementacion

{texto_antes}

```python
{codigo}```

{texto_despues}
"""
    chunks, _, _ = chunker.chunk_markdown(doc)
    # Ningun fragmento debe cortar el bloque cercado
    code_chunks = [c for c in chunks if "def procesar_lote_elementos" in c["content"]]
    assert len(code_chunks) == 1
    assert "return resultado\n```" in code_chunks[0]["content"]
    assert code_chunks[0]["content"].startswith("# Guia de Implementacion")


def test_ruta_titulos_en_cada_fragmento():
    doc = """# Manual Principal
Introduccion al manual del sistema.

## Modulo de Facturacion
Detalles sobre pagos y cargos.

### Pasarela de Pagos
Integracion con proveedores externos de cobro.
"""
    chunks, _, _ = chunker.chunk_markdown(doc)
    assert len(chunks) == 3

    assert chunks[0]["symbol_name"] == "Manual Principal"
    assert chunks[0]["content"].startswith("# Manual Principal\n\nIntroduccion")

    assert chunks[1]["symbol_name"] == "Modulo de Facturacion"
    assert chunks[1]["content"].startswith("# Manual Principal > ## Modulo de Facturacion\n\nDetalles")

    assert chunks[2]["symbol_name"] == "Pasarela de Pagos"
    assert chunks[2]["content"].startswith("# Manual Principal > ## Modulo de Facturacion > ### Pasarela de Pagos\n\nIntegracion")


def test_rst_troceado_por_titulos():
    doc_rst = """Guia de Inicio
==============

Esta es la seccion principal de bienvenida.

Instalacion Basica
------------------

Ejecuta el gestor de paquetes para comenzar.

Opciones Avanzadas
~~~~~~~~~~~~~~~~~~

Configuraciones adicionales de bajo nivel.
"""
    chunks, imps, exps = chunker.chunk_rst(doc_rst)
    assert len(chunks) == 3
    assert imps == []
    assert exps == []

    assert chunks[0]["symbol_name"] == "Guia de Inicio"
    assert chunks[0]["content"].startswith("Guia de Inicio\n\nEsta es la seccion")
    assert chunks[0]["symbol_kind"] == "section"

    assert chunks[1]["symbol_name"] == "Instalacion Basica"
    assert chunks[1]["content"].startswith("Guia de Inicio > Instalacion Basica\n\nEjecuta el gestor")
    assert chunks[1]["symbol_kind"] == "section"

    assert chunks[2]["symbol_name"] == "Opciones Avanzadas"
    assert chunks[2]["content"].startswith("Guia de Inicio > Instalacion Basica > Opciones Avanzadas\n\nConfiguraciones")
    assert chunks[2]["symbol_kind"] == "section"


def test_adoc_troceado_por_titulos():
    doc_adoc = """= Manual AsciiDoc

Informacion general del documento.

== Seccion de Configuracion

Parametros del entorno de ejecucion.

=== Parametros de Red

Puertos y direcciones IP permitidas.
"""
    chunks, imps, exps = chunker.chunk_adoc(doc_adoc)
    assert len(chunks) == 3
    assert imps == []
    assert exps == []

    assert chunks[0]["symbol_name"] == "Manual AsciiDoc"
    assert chunks[0]["content"].startswith("= Manual AsciiDoc\n\nInformacion")
    assert chunks[0]["symbol_kind"] == "section"

    assert chunks[1]["symbol_name"] == "Seccion de Configuracion"
    assert chunks[1]["content"].startswith("= Manual AsciiDoc > == Seccion de Configuracion\n\nParametros")
    assert chunks[1]["symbol_kind"] == "section"

    assert chunks[2]["symbol_name"] == "Parametros de Red"
    assert chunks[2]["content"].startswith("= Manual AsciiDoc > == Seccion de Configuracion > === Parametros de Red\n\nPuertos")
    assert chunks[2]["symbol_kind"] == "section"


def test_busqueda_tipo_docs_y_codigo(casa):
    archivos = {
        # Código
        "src/servicio.py": (
            "class GestorServicio:\n"
            "    def ejecutar_tarea(self, nombre: str) -> bool:\n"
            "        return True\n"
        ),
        "src/cliente.ts": (
            "export function conectarServicio(url: string): boolean {\n"
            "    return true;\n"
            "}\n"
        ),
        # Documentación
        "docs/manual.md": (
            "# Manual de Administracion\n"
            "Instrucciones para ejecutar_tarea y conectarServicio en el cluster.\n"
        ),
        "docs/instalacion.rst": (
            "Guia de Instalacion\n"
            "===================\n\n"
            "Pasos para instalar y configurar el servicio.\n"
        ),
        "docs/arquitectura.adoc": (
            "= Arquitectura del Sistema\n\n"
            "Detalles de conexion del cliente y ejecucion de tareas.\n"
        ),
        "notas.txt": (
            "Notas de despliegue rapido para ejecutar_tarea.\n"
        ),
    }

    crear_proyecto(casa, "demo_docs", archivos)
    indexer.index_desktop()

    doc_exts = {".md", ".mdx", ".rst", ".adoc", ".txt"}

    # 1. Búsqueda con tipo='docs' devuelve solo documentación
    res_docs = indexer.search_desktop("ejecutar_tarea", tipo="docs", use_rerank=False)
    assert len(res_docs) > 0
    for r in res_docs:
        ext = Path(r["rel_path"]).suffix.lower()
        assert ext in doc_exts, f"Se esperaba extension de docs, recibido: {ext} en {r['rel_path']}"

    # 2. Búsqueda con tipo='codigo' excluye la documentación
    res_cod = indexer.search_desktop("ejecutar_tarea", tipo="codigo", use_rerank=False)
    assert len(res_cod) > 0
    for r in res_cod:
        ext = Path(r["rel_path"]).suffix.lower()
        assert ext not in doc_exts, f"Se esperaba codigo, recibido doc: {ext} en {r['rel_path']}"

    # 3. Búsqueda en MCP server con tipo='docs'
    salida_mcp_docs = server_mcp.search_desktop("Instalacion", tipo="docs")
    assert "instalacion.rst" in salida_mcp_docs or "manual.md" in salida_mcp_docs

    # 4. Búsqueda en MCP server con tipo='codigo'
    salida_mcp_cod = server_mcp.search_desktop("GestorServicio", tipo="codigo")
    assert "servicio.py" in salida_mcp_cod
    assert ".md" not in salida_mcp_cod and ".rst" not in salida_mcp_cod


def test_sin_tipo_el_codigo_va_antes_que_la_documentacion(casa):
    crear_proyecto(casa, "mixto", {
        "app.py": "def log_exception(exc_info):\n    logger.error('unhandled exception', exc_info=exc_info)\n",
        "docs/errores.md": "# Errores\n\nTo log an unhandled exception, log the unhandled exception with the logger. "
                           "Unhandled exception logging: every unhandled exception is logged.\n",
    })
    indexer.index_desktop()
    res = indexer.search_desktop("log an unhandled exception", project="mixto", use_rerank=False)
    assert res[0]["rel_path"].endswith("app.py")
    docs = indexer.search_desktop("log an unhandled exception", project="mixto", tipo="docs", use_rerank=False)
    assert docs and all(r["rel_path"].endswith(".md") for r in docs)
