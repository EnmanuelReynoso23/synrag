"""Los trozos indexados deben ser copia exacta del archivo.

En 2.0.0 una "poda" trataba cualquier cadena de triple comilla como docstring y
la dejaba en su primera línea: el agente veía `sql = \"\"\"SELECT id, nombre\"\"\"`.
"""
from pathlib import Path

import chunker

CODIGO = '''def consulta(db):
    """Devuelve los alumnos activos.

    Usa la tabla alumnos.
    """
    # Licencia: MIT (este comentario también debe quedar)
    sql = """
    SELECT id, nombre
    FROM alumnos
    WHERE activo = 1
    """
    return db.execute(sql)
'''


def test_cadena_triple_comilla_queda_entera():
    chunks = chunker.chunk_file(Path("consulta.py"), CODIGO)
    texto = "\n".join(c["content"] for c in chunks)
    assert "FROM alumnos" in texto
    assert "WHERE activo = 1" in texto
    assert "Usa la tabla alumnos." in texto
    assert "# Licencia: MIT" in texto


def test_trozo_es_copia_exacta_de_sus_lineas():
    lineas = CODIGO.splitlines()
    for c in chunker.chunk_file(Path("consulta.py"), CODIGO):
        original = "\n".join(lineas[c["line"] - 1 : c["end_line"]])
        assert c["content"].strip() in original or original.strip() in c["content"]
