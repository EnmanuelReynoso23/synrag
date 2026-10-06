import lancedb
import cache


def test_cache_guardar_y_recuperar(tmp_path):
    db = lancedb.connect(str(tmp_path))
    resultados = [{"rel_path": "src/modelo.ts", "content": "class Modelo {}"}]

    cache.save_cached_results(db, "buscar modelo", resultados, project="mi_proyecto")
    recuperados = cache.get_cached_results(db, "buscar modelo", project="mi_proyecto")

    assert recuperados == resultados


def test_cache_normalizacion_mayusculas_y_espacios(tmp_path):
    db = lancedb.connect(str(tmp_path))
    resultados = [{"rel_path": "src/util.ts", "content": "export function util() {}"}]

    cache.save_cached_results(db, "Foo  Bar", resultados, project="mi_proyecto")

    # Acierta con minusculas y espacios simples normalizados
    hit = cache.get_cached_results(db, "foo bar", project="mi_proyecto")
    assert hit == resultados

    # No acierta con otras palabras
    miss_palabras = cache.get_cached_results(db, "foo baz", project="mi_proyecto")
    assert miss_palabras is None

    # Mismo texto con otro proyecto no acierta
    miss_proyecto = cache.get_cached_results(db, "foo bar", project="otro_proyecto")
    assert miss_proyecto is None


def test_cache_expiracion_ttl_y_limpieza(tmp_path):
    db = lancedb.connect(str(tmp_path))
    resultados = [{"rel_path": "src/servicio.ts", "content": "const s = 1;"}]

    cache.save_cached_results(db, "servicio", resultados)

    # Con ttl_seconds=0 expira de inmediato
    expirado = cache.get_cached_results(db, "servicio", ttl_seconds=0)
    assert expirado is None

    # clear_cache elimina la tabla por completo
    cache.clear_cache(db)
    assert cache.CACHE_TABLE not in db.table_names()
