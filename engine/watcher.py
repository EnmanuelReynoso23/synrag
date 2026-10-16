#!/usr/bin/env python3
"""
LanceDB Hub Watcher (Observador de cambios)
Vigila en tiempo real los proyectos de codigo y actualiza en LanceDB
el AST, fragmentos y grafo de impacto al guardar archivos.
"""

import gc
import signal
import sys
import threading
import time
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

sys.path.insert(0, str(Path(__file__).parent))
import indexer

DEBOUNCE_SECONDS = 0.6
INTERVALO_CARPETAS_SEGUNDOS = 60.0
OPTIMIZAR_CADA_ACTUALIZACIONES = 50


CONSERVAR_VERSIONES_MINUTOS = 5


def optimizar_tablas() -> bool:
    """Compacta fragmentos, elimina versiones antiguas de LanceDB y libera memoria."""
    try:
        db = indexer.get_db()
        optimizado = False
        for nombre in (indexer.TABLE_NAME, indexer.impact.IMPACT_TABLE):
            if indexer._has_table(db, nombre):
                try:
                    tbl = db.open_table(nombre)
                    # Conservar unos minutos las versiones viejas: un servidor MCP puede estar
                    # leyendo una de ellas y fallaria si se borra en ese momento.
                    tbl.optimize(cleanup_older_than=timedelta(minutes=CONSERVAR_VERSIONES_MINUTOS))
                    optimizado = True
                except Exception:
                    pass
        del db
        gc.collect()
        return optimizado
    except Exception:
        return False


class ReactiveIndexHandler(FileSystemEventHandler):
    """Manejador reactivo de eventos de archivos con debounce mediante un solo hilo trabajador,
    evitando la creacion masiva de hilos threading.Timer y compactando LanceDB periodicamente."""

    def __init__(
        self,
        debounce_delay: float = DEBOUNCE_SECONDS,
        optimizar_cada: int = OPTIMIZAR_CADA_ACTUALIZACIONES,
    ):
        super().__init__()
        self.debounce_delay = debounce_delay
        self.optimizar_cada = optimizar_cada
        self.base_dirs: List[Path] = []

        self._pending: Dict[str, float] = {}
        self._en_proceso = 0  # sacados de la cola pero aun indexandose
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._updates_count = 0
        self._running = True

        self._worker = threading.Thread(
            target=self._worker_loop, name="synrag-watcher-worker", daemon=True
        )
        self._worker.start()

    @property
    def _timers(self) -> Dict[str, float]:
        """Compatibilidad con codigo o pruebas que inspeccionen _timers."""
        with self._lock:
            return dict(self._pending)

    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    @property
    def updates_count(self) -> int:
        with self._lock:
            return self._updates_count

    def reset_updates_count(self) -> int:
        with self._lock:
            prev = self._updates_count
            self._updates_count = 0
            return prev

    def actualizar_carpetas(self, carpetas: List[Path]):
        with self._lock:
            self.base_dirs = [c.resolve() for c in carpetas]

    def _encontrar_base_dir(self, path: Path) -> Optional[Path]:
        with self._lock:
            dirs = list(self.base_dirs)

        if not dirs:
            dirs = [b.resolve() for b, _ in indexer.cargar_carpetas() if b.exists()]
            with self._lock:
                self.base_dirs = dirs

        for b_dir in dirs:
            try:
                if path.is_relative_to(b_dir):
                    return b_dir
            except Exception:
                continue
        return None

    def _trigger_update(self, path_str: str):
        path = Path(path_str)
        t0 = time.time()
        try:
            ok = indexer.index_single_file(path)
            if ok:
                elapsed_ms = int((time.time() - t0) * 1000)
                try:
                    rel = path.relative_to(Path.home())
                except Exception:
                    rel = path.name
                print(f"[OBSERVADOR AST] Actualizado: ~/{rel} ({elapsed_ms}ms)", flush=True)

                with self._lock:
                    self._updates_count += 1
                    debe_optimizar = (
                        self.optimizar_cada > 0
                        and self._updates_count >= self.optimizar_cada
                    )
                    if debe_optimizar:
                        self._updates_count = 0

                if debe_optimizar:
                    optimizar_tablas()
        except Exception as e:
            print(f"[ERROR] Error al reindexar {path}: {e}", flush=True)

    def _schedule_update(self, path_str: str):
        path = Path(path_str)

        base_dir = self._encontrar_base_dir(path)
        if not base_dir:
            return

        if path.suffix.lower() not in indexer.ALLOWED_EXTENSIONS:
            return

        try:
            rel = path.relative_to(base_dir)
            if any(
                part in indexer.IGNORE_DIRS
                or part.startswith(".")
                or any(s in part for s in indexer.IGNORE_DIR_SUBSTR)
                for part in rel.parts[:-1]
            ):
                return
        except ValueError:
            return

        if path.name in indexer.IGNORE_FILES or indexer.RE_ARCHIVO_SENSIBLE.search(path.name):
            return

        if path.exists() and not indexer.should_index(path, base_dir):
            return

        with self._cond:
            self._pending[path_str] = time.monotonic() + self.debounce_delay
            self._cond.notify()

    def _worker_loop(self):
        while True:
            with self._cond:
                while self._running and not self._pending:
                    self._cond.wait(timeout=1.0)

                if not self._running and not self._pending:
                    break

                now = time.monotonic()
                earliest_path, earliest_deadline = min(
                    self._pending.items(), key=lambda item: item[1]
                )

                if earliest_deadline > now:
                    espera = earliest_deadline - now
                    self._cond.wait(timeout=espera)
                    continue

                self._pending.pop(earliest_path, None)
                self._en_proceso += 1

            try:
                self._trigger_update(earliest_path)
            finally:
                with self._cond:
                    self._en_proceso -= 1
                    self._cond.notify_all()

    def stop(self, timeout: float = 2.0):
        with self._cond:
            self._running = False
            self._cond.notify_all()
        if self._worker.is_alive():
            self._worker.join(timeout=timeout)

    def wait_idle(self, timeout: float = 5.0) -> bool:
        """Espera a que se procesen todas las actualizaciones pendientes."""
        limite = time.monotonic() + timeout
        while time.monotonic() < limite:
            with self._cond:
                # vacio de verdad: nada en cola y nada indexandose (antes devolvia True entre el
                # borrado de la fila vieja y el alta de la nueva)
                if not self._pending and self._en_proceso == 0:
                    return True
            time.sleep(0.02)
        return False

    def on_modified(self, event):
        if not event.is_directory:
            self._schedule_update(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self._schedule_update(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._schedule_update(event.src_path)


def sincronizar_carpetas(
    observer: Observer,
    handler: ReactiveIndexHandler,
    watched: Dict[Path, Any],
) -> Tuple[int, int]:
    """Relee las carpetas configuradas (indexer.cargar_carpetas),
    agrega observadores para rutas nuevas y retira las que ya no esten.
    Devuelve (nuevas_agregadas, eliminadas)."""
    nuevas = 0
    eliminadas = 0

    carpetas_cfg = indexer.cargar_carpetas()
    actuales: Dict[Path, Path] = {}
    for base_dir, _ in carpetas_cfg:
        try:
            res = base_dir.resolve()
            if base_dir.exists() and base_dir.is_dir():
                actuales[res] = base_dir
        except Exception:
            continue

    # Desprogramar rutas eliminadas
    for res_dir in list(watched.keys()):
        if res_dir not in actuales:
            watch = watched.pop(res_dir)
            try:
                observer.unschedule(watch)
                eliminadas += 1
                print(f"   [UNWATCH] Dejando de vigilar: {res_dir}", flush=True)
            except Exception:
                pass

    # Programar rutas nuevas
    for res_dir, base_dir in actuales.items():
        if res_dir not in watched:
            try:
                watch = observer.schedule(handler, str(base_dir), recursive=True)
                watched[res_dir] = watch
                nuevas += 1
                print(f"   [WATCH] Vigilando: {base_dir}", flush=True)
            except Exception as e:
                print(f"   [AVISO] No se pudo vigilar {base_dir}: {e}", flush=True)

    handler.actualizar_carpetas(list(actuales.values()))
    return (nuevas, eliminadas)


def start_watcher(
    debounce_delay: float = DEBOUNCE_SECONDS,
    intervalo_carpetas: float = INTERVALO_CARPETAS_SEGUNDOS,
    optimizar_cada: int = OPTIMIZAR_CADA_ACTUALIZACIONES,
    max_iteraciones: Optional[int] = None,
):
    print("[INFO] Iniciando observador de cambios de LanceDB Hub...", flush=True)
    handler = ReactiveIndexHandler(
        debounce_delay=debounce_delay, optimizar_cada=optimizar_cada
    )
    observer = Observer()
    watched: Dict[Path, Any] = {}

    sincronizar_carpetas(observer, handler, watched)

    if not watched:
        print("[ERROR] No se encontraron directorios validos para vigilar.", flush=True)
        handler.stop()
        return

    observer.start()
    print("[OK] Observador activo. LanceDB se actualizara con cada archivo guardado.", flush=True)

    running = True

    def stop_signal(signum, frame):
        nonlocal running
        print("\n[STOP] Deteniendo observador...", flush=True)
        running = False
        observer.stop()
        handler.stop()
        try:
            observer.join(timeout=3.0)
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, stop_signal)
    signal.signal(signal.SIGTERM, stop_signal)

    ultimo_chequeo_carpetas = time.time()
    iteracion = 0
    try:
        while running and observer.is_alive():
            time.sleep(1)
            iteracion += 1
            if max_iteraciones is not None and iteracion >= max_iteraciones:
                break

            ahora = time.time()
            if ahora - ultimo_chequeo_carpetas >= intervalo_carpetas:
                ultimo_chequeo_carpetas = ahora
                sincronizar_carpetas(observer, handler, watched)
                if handler.pending_count == 0 and handler.updates_count > 0:
                    handler.reset_updates_count()
                    optimizar_tablas()
    except KeyboardInterrupt:
        stop_signal(None, None)
    finally:
        observer.stop()
        handler.stop()
        try:
            observer.join(timeout=2.0)
        except Exception:
            pass


if __name__ == "__main__":
    start_watcher()
