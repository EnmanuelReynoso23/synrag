#!/usr/bin/env python3
"""
Benchmark del observador de cambios (watcher.py).
Reproduce y mide la afirmacion de CLAIMS.md fila 8 (crecimiento de memoria del observador).

Trabaja en un HOME temporal con archivos sinteticos: no toca tu indice ni tus proyectos.
Ejecuta miles de guardados continuos y mide el consumo de memoria RSS, numero de versiones
en LanceDB y comportamiento de hilos antes y despues de la solucion.

Uso:
    python benchmarks/observador.py [--guardados 2000] [--archivos 10] [--modo ambos]
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import timedelta
from pathlib import Path

MOTOR = Path(__file__).resolve().parent.parent / "engine"
sys.path.insert(0, str(MOTOR))


def leer_rss_mb() -> float:
    """Devuelve la memoria residente (RSS) del proceso actual en megabytes."""
    try:
        with open("/proc/self/status") as s:
            for line in s:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except Exception:
        return 0.0
    return 0.0


def contar_manifests(db_dir: Path) -> int:
    """Cuenta los archivos .manifest generados en LanceDB para desktop_files."""
    versions_dir = db_dir / "desktop_files.lance" / "_versions"
    if not versions_dir.exists():
        return 0
    return len(list(versions_dir.glob("*.manifest")))


def crear_entorno_prueba(casa: Path, num_archivos: int) -> list[Path]:
    """Crea una carpeta de proyecto y archivos sinteticos validos para indexar."""
    proj = casa / "Proyectos" / "benchmark_demo" / "src"
    proj.mkdir(parents=True, exist_ok=True)
    archivos = []
    for i in range(num_archivos):
        f = proj / f"modulo_{i}.ts"
        f.write_text(
            f"export interface Modelo{i} {{\n"
            f"    id: number;\n"
            f"    nombre: string;\n"
            f"}}\n\n"
            f"export function procesar_modulo_{i}(entrada: Modelo{i}): string {{\n"
            f"    return 'resultado_' + entrada.id + '_' + entrada.nombre;\n"
            f"}}\n",
            encoding="utf-8",
        )
        archivos.append(f)
    return archivos


def ejecutar_modo_interno(modo: str, guardados: int, num_archivos: int, intervalo: float, debounce: float):
    """Ejecuta la simulacion dentro de un proceso hijo aislado."""
    casa = Path(tempfile.mkdtemp(prefix=f"synrag-bench-{modo}-"))
    os.environ["HOME"] = str(casa)
    for var in ("SYNRAG_DB_PATH", "SYNRAG_CARPETAS", "XDG_CONFIG_HOME"):
        if var in os.environ:
            del os.environ[var]

    import indexer

    try:
        archivos = crear_entorno_prueba(casa, num_archivos)
        indexer.index_desktop()

        rss_inicial = leer_rss_mb()
        db_dir = casa / ".local" / "share" / "lancedb-hub" / "data"

        puntos_control = {}
        intervalos_chequeo = [
            int(guardados * 0.25),
            int(guardados * 0.50),
            int(guardados * 0.75),
            guardados,
        ]

        if modo == "antes":
            # Simulacion del comportamiento anterior:
            # 1. Cada evento crea un threading.Timer
            # 2. Reindexado sin optimizacion de tablas (acumulacion de fragmentos/manifests)
            timers: dict[str, threading.Timer] = {}
            lock = threading.Lock()
            max_hilos = 0

            def trigger_antes(path_str: str):
                with lock:
                    timers.pop(path_str, None)
                indexer.index_single_file(Path(path_str))

            def schedule_antes(path_str: str):
                with lock:
                    prev = timers.get(path_str)
                    if prev:
                        prev.cancel()
                    t = threading.Timer(debounce, trigger_antes, args=[path_str])
                    timers[path_str] = t
                    t.start()

            for paso in range(1, guardados + 1):
                f = archivos[paso % num_archivos]
                f.write_text(
                    f"export interface Modelo{paso % num_archivos} {{\n"
                    f"    id: number;\n"
                    f"    version: number;\n"
                    f"}}\n\n"
                    f"export function procesar_{paso % num_archivos}(x: number): number {{\n"
                    f"    return x + {paso};\n"
                    f"}}\n",
                    encoding="utf-8",
                )
                schedule_antes(str(f))
                max_hilos = max(max_hilos, threading.active_count())

                # Breve pausa para dar oportunidad a que transcurran eventos de debounce
                if paso % (num_archivos * 2) == 0:
                    time.sleep(debounce + 0.02)

                if paso in intervalos_chequeo:
                    puntos_control[f"{paso}"] = round(leer_rss_mb(), 2)

            time.sleep(debounce + 0.2)
            # Asegurar que se procesen los pendientes
            with lock:
                activos = list(timers.values())
            for t in activos:
                t.join(timeout=1.0)

            rss_final = round(leer_rss_mb(), 2)
            manifests = contar_manifests(db_dir)

            resultado = {
                "modo": "antes",
                "rss_inicial": round(rss_inicial, 2),
                "puntos_control": puntos_control,
                "rss_final": rss_final,
                "manifests": manifests,
                "max_hilos": max_hilos,
            }

        else:
            # Comportamiento nuevo reparado:
            # 1. Cola de worker persistente (1 solo hilo)
            # 2. Compactacion y optimizacion periodica de LanceDB
            import watcher

            handler = watcher.ReactiveIndexHandler(
                debounce_delay=debounce, optimizar_cada=50
            )
            handler.actualizar_carpetas([casa / "Proyectos"])
            max_hilos = 0

            for paso in range(1, guardados + 1):
                f = archivos[paso % num_archivos]
                f.write_text(
                    f"export interface Modelo{paso % num_archivos} {{\n"
                    f"    id: number;\n"
                    f"    version: number;\n"
                    f"}}\n\n"
                    f"export function procesar_{paso % num_archivos}(x: number): number {{\n"
                    f"    return x + {paso};\n"
                    f"}}\n",
                    encoding="utf-8",
                )
                handler._schedule_update(str(f))
                max_hilos = max(max_hilos, threading.active_count())

                if paso % (num_archivos * 2) == 0:
                    time.sleep(debounce + 0.02)

                if paso in intervalos_chequeo:
                    puntos_control[f"{paso}"] = round(leer_rss_mb(), 2)

            handler.wait_idle(timeout=5.0)
            watcher.optimizar_tablas()
            handler.stop()

            rss_final = round(leer_rss_mb(), 2)
            manifests = contar_manifests(db_dir)

            resultado = {
                "modo": "despues",
                "rss_inicial": round(rss_inicial, 2),
                "puntos_control": puntos_control,
                "rss_final": rss_final,
                "manifests": manifests,
                "max_hilos": max_hilos,
            }

        print("RESULTADO_JSON:" + json.dumps(resultado))
    finally:
        shutil.rmtree(casa, ignore_errors=True)


def ejecutar_subproceso(modo: str, guardados: int, num_archivos: int, intervalo: float, debounce: float) -> dict:
    """Ejecuta una medicion en un subproceso aislado para obtener mediciones limpias de memoria."""
    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--modo-interno",
        modo,
        "--guardados",
        str(guardados),
        "--archivos",
        str(num_archivos),
        "--intervalo",
        str(intervalo),
        "--debounce",
        str(debounce),
    ]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    if proc.returncode != 0:
        print(f"Error ejecutando subproceso para modo {modo}:", file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        sys.exit(1)

    for line in proc.stdout.splitlines():
        if line.startswith("RESULTADO_JSON:"):
            return json.loads(line.partition("RESULTADO_JSON:")[2])

    print("No se encontro salida JSON en el subproceso:", file=sys.stderr)
    print(proc.stdout, file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--guardados", type=int, default=2000, help="Numero de guardados sinteticos (default: 2000)")
    parser.add_argument("--archivos", type=int, default=10, help="Numero de archivos rotados (default: 10)")
    parser.add_argument("--intervalo", type=float, default=0.002, help="Pausa entre escrituras (default: 0.002s)")
    parser.add_argument("--debounce", type=float, default=0.05, help="Ventana de debounce (default: 0.05s)")
    parser.add_argument("--modo", choices=["ambos", "antes", "despues"], default="ambos", help="Modo a evaluar")
    parser.add_argument("--modo-interno", type=str, default="", help=argparse.SUPPRESS)

    args = parser.parse_args()

    if args.modo_interno:
        ejecutar_modo_interno(
            args.modo_interno,
            args.guardados,
            args.archivos,
            args.intervalo,
            args.debounce,
        )
        return

    print("================================================================================")
    print("SynRAG: Benchmark de Memoria y Rendimiento del Observador (watcher.py)")
    print(f"Configuracion: {args.guardados} guardados, {args.archivos} archivos, debounce={args.debounce}s")
    print("================================================================================\n")

    res_antes = None
    res_despues = None

    if args.modo in ("ambos", "antes"):
        print("[1/2] Ejecutando medicion 'ANTES' (hilos Timer continuos, sin compactacion de LanceDB)...")
        res_antes = ejecutar_subproceso("antes", args.guardados, args.archivos, args.intervalo, args.debounce)
        print(f"      Completado. RSS final: {res_antes['rss_final']} MB, manifests: {res_antes['manifests']}\n")

    if args.modo in ("ambos", "despues"):
        print("[2/2] Ejecutando medicion 'DESPUES' (cola worker con condition, compactacion periodica)...")
        res_despues = ejecutar_subproceso("despues", args.guardados, args.archivos, args.intervalo, args.debounce)
        print(f"      Completado. RSS final: {res_despues['rss_final']} MB, manifests: {res_despues['manifests']}\n")

    if res_antes and res_despues:
        print("================================================================================")
        print("TABLA COMPARATIVA: ANTES vs DESPUES")
        print("================================================================================")
        print(f"{'Metrica / Punto de control':<35} | {'Antes':<12} | {'Despues':<12} | {'Diferencia':<15}")
        print("-" * 82)
        print(f"{'RSS inicial':<35} | {res_antes['rss_inicial']:>9.2f} MB | {res_despues['rss_inicial']:>9.2f} MB | {res_despues['rss_inicial'] - res_antes['rss_inicial']:>+12.2f} MB")

        claves = sorted(res_antes["puntos_control"].keys(), key=lambda k: int(k))
        for k in claves:
            va = res_antes["puntos_control"][k]
            vd = res_despues["puntos_control"].get(k, 0.0)
            dif = vd - va
            porc = (dif / va) * 100 if va > 0 else 0
            etiqueta = f"Guardados = {k}"
            print(f"{etiqueta:<35} | {va:>9.2f} MB | {vd:>9.2f} MB | {dif:>+9.2f} MB ({porc:>+5.1f}%)")

        dif_fin = res_despues["rss_final"] - res_antes["rss_final"]
        porc_fin = (dif_fin / res_antes["rss_final"]) * 100
        print("-" * 82)
        print(f"{'RSS final tras reposo':<35} | {res_antes['rss_final']:>9.2f} MB | {res_despues['rss_final']:>9.2f} MB | {dif_fin:>+9.2f} MB ({porc_fin:>+5.1f}%)")
        print(f"{'Archivos manifest (.manifest)':<35} | {res_antes['manifests']:>12} | {res_despues['manifests']:>12} | {res_despues['manifests'] - res_antes['manifests']:>+15}")
        print(f"{'Hilos maximos observados':<35} | {res_antes['max_hilos']:>12} | {res_despues['max_hilos']:>12} | {res_despues['max_hilos'] - res_antes['max_hilos']:>+15}")
        print("================================================================================\n")
    elif res_despues:
        print("Resultados modo DESPUES:")
        print(json.dumps(res_despues, indent=2))
    elif res_antes:
        print("Resultados modo ANTES:")
        print(json.dumps(res_antes, indent=2))


if __name__ == "__main__":
    main()
