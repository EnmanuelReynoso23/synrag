import telemetry


def test_telemetria_registro_y_resumen(casa):
    # Simular resultados devueltos por una búsqueda
    resultados = [
        {
            "file_path": str(casa / "modulo.ts"),
            "content": "export function procesarDatos(x: number) { return x * 2; }",
        }
    ]

    evento = telemetry.record_search_event(
        query="procesarDatos",
        results=resultados,
        elapsed_ms=15.2,
        cache_hit=False,
        project="proyecto_prueba",
        agent="test-agent",
    )

    assert evento["tokens_retrieved"] > 0
    assert evento["tokens_saved"] > 0
    assert evento["cost_saved_usd"] >= 0.0

    stats = telemetry.get_summary_stats()

    assert stats["all_time"]["queries"] == 1
    assert stats["all_time"]["tokens_saved"] == evento["tokens_saved"]
    assert stats["all_time"]["cache_hits"] == 0
    assert stats["today"]["queries"] == 1

    top = stats["top_queries"]
    assert len(top) == 1
    assert top[0]["query"] == "procesarDatos"
    assert top[0]["count"] == 1
