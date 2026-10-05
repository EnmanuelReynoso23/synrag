#!/usr/bin/env python3
"""
LanceDB Hub Reactive Watcher (v3 Hot-Reload Daemon)
Vigila en tiempo real los proyectos de código y actualiza quirúrgicamente en LanceDB
el AST, fragmentos y grafo de impacto en cuanto el usuario presiona Ctrl+S.
"""

import sys
import time
import signal
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

sys.path.insert(0, str(Path(__file__).parent))
import indexer

DEBOUNCE_SECONDS = 0.6


class ReactiveIndexHandler(FileSystemEventHandler):
    def __init__(self, debounce_delay: float = DEBOUNCE_SECONDS):
        super().__init__()
        self.debounce_delay = debounce_delay
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def _trigger_update(self, path_str: str):
        with self._lock:
            self._timers.pop(path_str, None)

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
                print(f"[HOT-RELOAD AST] Actualizado: ~/{rel} ({elapsed_ms}ms)", flush=True)
        except Exception as e:
            print(f"[ERROR] Error en hot-reload para {path}: {e}", flush=True)

    def _schedule_update(self, path_str: str):
        path = Path(path_str)

        # Buscar el directorio base al que pertenece
        base_dir = None
        for b_dir, _ in indexer.SCAN_DIRECTORIES:
            try:
                if path.is_relative_to(b_dir):
                    base_dir = b_dir
                    break
            except Exception:
                continue

        if not base_dir:
            return

        if path.exists() and not indexer.should_index(path, base_dir):
            return

        with self._lock:
            existing = self._timers.get(path_str)
            if existing:
                existing.cancel()
            timer = threading.Timer(self.debounce_delay, self._trigger_update, args=[path_str])
            self._timers[path_str] = timer
            timer.start()

    def on_modified(self, event):
        if not event.is_directory:
            self._schedule_update(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self._schedule_update(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._schedule_update(event.src_path)


def start_watcher():
    print("[INFO] Iniciando demonio reactivo de LanceDB Hub (Hot-Reload AST)...", flush=True)
    handler = ReactiveIndexHandler()
    observer = Observer()
    observed_count = 0

    for base_dir, _ in indexer.SCAN_DIRECTORIES:
        if base_dir.exists() and base_dir.is_dir():
            observer.schedule(handler, str(base_dir), recursive=True)
            print(f"   [WATCH] Vigilando: {base_dir}", flush=True)
            observed_count += 1

    if observed_count == 0:
        print("[ERROR] No se encontraron directorios validos para vigilar.", flush=True)
        return

    observer.start()
    print("[OK] Demonio activo. El AST y LanceDB se actualizaran automaticamente con cada guardado.", flush=True)

    def stop_signal(signum, frame):
        print("\n[STOP] Deteniendo demonio reactivo...", flush=True)
        observer.stop()
        observer.join()
        sys.exit(0)

    signal.signal(signal.SIGINT, stop_signal)
    signal.signal(signal.SIGTERM, stop_signal)

    try:
        while observer.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        stop_signal(None, None)


if __name__ == "__main__":
    start_watcher()
