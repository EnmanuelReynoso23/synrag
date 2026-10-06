from pathlib import Path
import indexer
from conftest import crear_proyecto


def test_busqueda_integracion_completa(casa):
    # Generar 30 archivos .ts sintéticos con funciones identificables
    archivos = {}
    for i in range(30):
        archivos[f"mod{i}.ts"] = (
            f"export function procesar{i}(entrada: string): string {{\n"
            f"    return 'resultado_{i}_' + entrada;\n"
            f"}}\n"
        )

    # Archivo con secreto para comprobar redacción
    archivos["servicio_auth.ts"] = (
        "export function autenticarServicio(): string {\n"
        "    const api_key = 'abcdefghijklmnop1234';\n"
        "    return api_key;\n"
        "}\n"
    )

    # Archivos que deben ser excluidos
    archivos[".env"] = "VARIABLE_UNICA_DEL_ENV=valor_secreto_no_indexable\n"
    archivos["archivo_pesado.ts"] = "export const pesado = true;\n" + ("x = 1;\n" * 40000)

    proj_dir = crear_proyecto(casa, "mi_proyecto", archivos)

    # 1. Indexar todo el entorno
    indexer.index_desktop()

    # 2. Búsqueda directa sin reordenado de red
    resultados = indexer.search_desktop("procesar3", use_rerank=False)
    assert len(resultados) > 0
    assert any("mod3.ts" in r.get("rel_path", "") for r in resultados)

    # 3. Filtro de proyecto existente vs inexistente
    res_proj_ok = indexer.search_desktop("procesar3", project="mi_proyecto", use_rerank=False)
    assert len(res_proj_ok) > 0

    res_proj_vacio = indexer.search_desktop("procesar3", project="proyecto_inexistente", use_rerank=False)
    assert len(res_proj_vacio) == 0

    # 4. Segunda llamada responde desde la caché idéntico resultado
    res_cache = indexer.search_desktop("procesar3", project="mi_proyecto", use_rerank=False)
    assert res_cache == res_proj_ok

    # 5. index_single_file tras añadir nueva función la hace encontrable
    nuevo_archivo = proj_dir / "nuevo_modulo.ts"
    nuevo_archivo.write_text(
        "export function calcularDescuentoEspecial(precio: number): number {\n"
        "    return precio * 0.85;\n"
        "}\n",
        encoding="utf-8",
    )
    exito_reindex = indexer.index_single_file(nuevo_archivo)
    assert exito_reindex is True

    res_nuevo = indexer.search_desktop("calcularDescuentoEspecial", use_rerank=False)
    assert len(res_nuevo) > 0
    assert any("nuevo_modulo.ts" in r.get("rel_path", "") for r in res_nuevo)

    # 6. Exclusiones: .env y archivo mayor a 250 KB no aparecen
    res_env = indexer.search_desktop("VARIABLE_UNICA_DEL_ENV", use_rerank=False)
    assert len(res_env) == 0
    assert not any(".env" in r.get("rel_path", "") for r in indexer.search_desktop("valor_secreto", use_rerank=False))

    res_pesado = indexer.search_desktop("archivo_pesado", use_rerank=False)
    assert not any("archivo_pesado.ts" in r.get("rel_path", "") for r in res_pesado)

    # 7. Redacción de secretos: el valor real nunca aparece en el contenido indexado
    res_auth = indexer.search_desktop("autenticarServicio", use_rerank=False)
    assert len(res_auth) > 0
    contenido_auth = res_auth[0].get("content", "")
    assert "abcdefghijklmnop1234" not in contenido_auth
    assert indexer.OCULTO in contenido_auth
