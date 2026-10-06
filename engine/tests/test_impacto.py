import lancedb
import impact


def test_impacto_tabla_y_dependientes(tmp_path):
    db = lancedb.connect(str(tmp_path))
    registros = [
        {"symbol": "calcularTotal", "imported_by": "src/factura.ts", "source": "./calculos", "project": "tienda"},
        {"symbol": "calcularTotal", "imported_by": "src/reportes.ts", "source": "./calculos", "project": "tienda"},
        {"symbol": "calcularTotal", "imported_by": "src/otro.ts", "source": "./calculos", "project": "otro_proj"},
    ]
    impact.init_impact_table(db, registros)

    # Consulta sin filtro de proyecto: devuelve todos los archivos que lo importan
    deps_todos = impact.get_dependents(db, "calcularTotal")
    assert sorted(deps_todos) == ["src/factura.ts", "src/otro.ts", "src/reportes.ts"]

    # Consulta con filtro de proyecto: limita a los del proyecto especificado
    deps_tienda = impact.get_dependents(db, "calcularTotal", project="tienda")
    assert sorted(deps_tienda) == ["src/factura.ts", "src/reportes.ts"]

    # Símbolo inexistente devuelve lista vacía
    deps_inexistente = impact.get_dependents(db, "simboloInexistente")
    assert deps_inexistente == []


def test_impacto_format_impact_warning():
    dependientes = ["src/modulo_a.ts", "src/modulo_b.ts"]
    warning = impact.format_impact_warning(dependientes, "calcularTotal")

    assert "calcularTotal" in warning
    assert "2 archivo(s)" in warning
    assert "src/modulo_a.ts" in warning
    assert "src/modulo_b.ts" in warning

    # Lista vacía no genera advertencia
    assert impact.format_impact_warning([], "calcularTotal") == ""
