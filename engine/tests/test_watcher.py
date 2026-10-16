"""Pruebas del observador reactivo (watcher.py)."""

import importlib
import threading
import time
from datetime import timedelta
from pathlib import Path
from watchdog.observers import Observer

import indexer
import watcher
from conftest import crear_proyecto


def _recargar():
    importlib.reload(indexer)
    importlib.reload(watcher)
    return watcher


def test_debounce_agrupa_guardados_y_actualiza(casa, monkeypatch):
    """Verifica que rafagas de guardados en un mismo archivo se agrupen y actualicen LanceDB."""
    w = _recargar()
    proj = crear_proyecto(
        casa,
        "app",
        {
            "src/servicio.py": "def calcular(x):\n    \"\"\"Calcula el total con documentacion.\"\"\"\n    return x * 10\n",
        },
    )
    indexer.index_desktop()

    archivo = proj / "src" / "servicio.py"
    handler = w.ReactiveIndexHandler(debounce_delay=0.08, optimizar_cada=10)
    handler.actualizar_carpetas([proj.parent])

    try:
        # Generar 15 guardados rapidos
        for i in range(15):
            archivo.write_text(
                f"def calcular(x):\n    \"\"\"Calcula el total con documentacion.\"\"\"\n    return x * {i + 1}\n",
                encoding="utf-8",
            )
            handler._schedule_update(str(archivo))
            time.sleep(0.005)

        # Esperar a que el worker procese el debounce
        assert handler.wait_idle(timeout=3.0)

        # Comprobar que LanceDB tiene la ultima version
        db = indexer.get_db()
        tbl = db.open_table(indexer.TABLE_NAME)
        filas = tbl.search().where("rel_path = 'Proyectos/app/src/servicio.py'").to_list()
        assert len(filas) == 1
        assert "x * 15" in filas[0]["content"]
    finally:
        handler.stop()


def test_sin_fuga_de_hilos_en_rafaga(casa):
    """Verifica que cientos de eventos no creen cientos de hilos (solo 1 worker persistente)."""
    w = _recargar()
    proj = crear_proyecto(casa, "demo", {"a.py": "x = 1\n"})
    archivo = proj / "a.py"

    hilos_antes = threading.active_count()
    handler = w.ReactiveIndexHandler(debounce_delay=0.1)
    handler.actualizar_carpetas([proj.parent])

    try:
        assert threading.active_count() == hilos_antes + 1  # Solo el hilo synrag-watcher-worker

        for i in range(200):
            handler._schedule_update(str(archivo))

        # En ningun momento debe dispararse el conteo de hilos del proceso
        assert threading.active_count() <= hilos_antes + 2
    finally:
        handler.stop()


def test_sincronizar_carpetas_agrega_y_elimina(casa, monkeypatch):
    """Verifica que el observador detecte nuevas carpetas agregadas y descarte las eliminadas."""
    w = _recargar()
    monkeypatch.delenv("SYNRAG_CARPETAS", raising=False)

    p1 = casa / "Proyectos" / "p1"
    p1.mkdir(parents=True)
    p2 = casa / "Proyectos" / "p2"
    p2.mkdir(parents=True)

    cfg = casa / ".config" / "synrag" / "carpetas.txt"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(f"{p1}\n", encoding="utf-8")

    observer = Observer()
    handler = w.ReactiveIndexHandler(debounce_delay=0.1)
    watched = {}

    try:
        # Sincronizacion inicial: solo p1
        nuevas, elim = w.sincronizar_carpetas(observer, handler, watched)
        assert nuevas == 1
        assert elim == 0
        assert p1.resolve() in watched
        assert p2.resolve() not in watched

        # El usuario agrega p2 a la configuracion
        cfg.write_text(f"{p1}\n{p2}\n", encoding="utf-8")
        nuevas, elim = w.sincronizar_carpetas(observer, handler, watched)
        assert nuevas == 1
        assert elim == 0
        assert p1.resolve() in watched
        assert p2.resolve() in watched

        # El usuario retira p1
        cfg.write_text(f"{p2}\n", encoding="utf-8")
        nuevas, elim = w.sincronizar_carpetas(observer, handler, watched)
        assert nuevas == 0
        assert elim == 1
        assert p1.resolve() not in watched
        assert p2.resolve() in watched
    finally:
        handler.stop()
        observer.stop()


def test_optimizar_tablas_compacta_y_limpia_versiones(casa, monkeypatch):
    """Verifica que optimizar_tablas compacte fragmentos y reduzca archivos de versiones."""
    w = _recargar()
    monkeypatch.setattr(w, "CONSERVAR_VERSIONES_MINUTOS", 0)  # sin margen: limpia todo
    proj = crear_proyecto(
        casa, "demo", {"mod.py": "def hola(x):\n    \"\"\"Funcion de prueba con docstring.\"\"\"\n    return x\n"}
    )
    indexer.index_desktop()

    f = proj / "mod.py"
    for i in range(1, 15):
        f.write_text(
            f"def hola_{i}(x):\n    \"\"\"Funcion de prueba con docstring {i}.\"\"\"\n    return x + {i}\n",
            encoding="utf-8",
        )
        indexer.index_single_file(f)

    db_dir = casa / ".local" / "share" / "lancedb-hub" / "data" / "desktop_files.lance"
    manifests_antes = len(list((db_dir / "_versions").glob("*.manifest")))
    assert manifests_antes > 10

    ok = w.optimizar_tablas()
    assert ok is True

    manifests_despues = len(list((db_dir / "_versions").glob("*.manifest")))
    assert manifests_despues <= 2


def test_ignora_archivos_no_indexables(casa):
    """Archivos ocultos o en carpetas ignoradas no deben encolarse."""
    w = _recargar()
    proj = crear_proyecto(casa, "demo", {"mod.py": "x = 1\n"})
    handler = w.ReactiveIndexHandler(debounce_delay=0.1)
    handler.actualizar_carpetas([proj.parent])

    try:
        ignorado = proj / "node_modules" / "pkg" / "index.js"
        ignorado.parent.mkdir(parents=True)
        ignorado.write_text("console.log(1);", encoding="utf-8")

        handler._schedule_update(str(ignorado))
        assert handler.pending_count == 0

        # Archivo temporal que no existe
        no_existe = proj / "fantasma.tmp"
        handler._schedule_update(str(no_existe))
        assert handler.pending_count == 0
    finally:
        handler.stop()
