#!/usr/bin/env python3
"""
Benchmark del filtro de terminal (SYNRAG filtrar).

Mide reduccion en lineas y tokens aproximados (caracteres / 4) en salidas de
comandos habituales (pip install, pytest con fallo provocado, npm install, cargo build).
Verifica de forma estricta que TODAS las lineas de error sigan presentes tras el filtrado.

Uso:
    python benchmarks/filtro.py [--real]
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

MOTOR = Path(__file__).resolve().parent.parent / "engine"
sys.path.insert(0, str(MOTOR))

try:
    import filtro
except ImportError as e:
    sys.exit(f"No se pudo importar filtro.py ({e}). Ejecuta con el entorno virtual del motor.")

LOGS_DIR = Path(__file__).resolve().parent / "logs"

# Palabras clave para verificar preservacion de errores
PATRON_ERROR = re.compile(
    r'(?:\b(?:error|fail|failed|failure|exception|traceback|panic|warning|assert)\b|npm\s+ERR!)',
    re.IGNORECASE,
)


def tokens(texto: str) -> int:
    """Aproximacion estandar en SynRAG: 4 caracteres por token."""
    return (len(texto) + 3) // 4


def extraer_lineas_criticas(texto: str) -> List[str]:
    """Extrae lineas de error que deben estar garantizadas en la salida."""
    criticas: List[str] = []
    for l in texto.splitlines():
        # Excluir avisos de deprecacion agrupables de npm
        if "npm warn deprecated" in l.lower():
            continue
        if PATRON_ERROR.search(l):
            criticas.append(l.strip())
    return criticas


def generar_salida_pytest_real() -> str:
    """Genera una salida real de pytest provocando un fallo en directorio temporal."""
    with tempfile.TemporaryDirectory() as tmp:
        dir_t = Path(tmp)
        test_file = dir_t / "test_ejemplo.py"
        test_file.write_text(
            """
def test_ok_1(): assert True
def test_ok_2(): assert 1 + 1 == 2
def test_fallo_provocado():
    valor_esperado = 100
    valor_obtenido = 42
    assert valor_obtenido == valor_esperado, "Fallo intencional para medir preservacion"
""",
            encoding="utf-8",
        )
        res = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-v"],
            capture_output=True,
            text=True,
            cwd=str(dir_t),
        )
        return res.stdout + res.stderr


def cargar_casos(usar_reales: bool = False) -> List[Tuple[str, str, str]]:
    """Devuelve tuplas (nombre, comando, texto_log)."""
    casos: List[Tuple[str, str, str]] = []

    # 1. pytest con fallo provocado
    log_pytest = LOGS_DIR / "pytest_fallo.log"
    texto_pytest = ""
    if usar_reales:
        try:
            texto_pytest = generar_salida_pytest_real()
        except Exception:
            pass
    if not texto_pytest and log_pytest.is_file():
        texto_pytest = log_pytest.read_text(encoding="utf-8")
    if texto_pytest:
        casos.append(("pytest (con fallo)", "pytest -v", texto_pytest))

    # 2. pip install
    log_pip = LOGS_DIR / "pip_install.log"
    if log_pip.is_file():
        casos.append(("pip install (dependencias)", "pip install requests pytest", log_pip.read_text(encoding="utf-8")))

    # 3. npm install
    log_npm = LOGS_DIR / "npm_install.log"
    if log_npm.is_file():
        casos.append(("npm install (paquetes)", "npm install", log_npm.read_text(encoding="utf-8")))

    # 4. cargo build
    log_cargo = LOGS_DIR / "cargo_build.log"
    if log_cargo.is_file():
        casos.append(("cargo build (compilacion)", "cargo build", log_cargo.read_text(encoding="utf-8")))

    return casos


def ejecutar_benchmark(usar_reales: bool = False) -> None:
    casos = cargar_casos(usar_reales=usar_reales)
    if not casos:
        sys.exit("No se encontraron logs de prueba en benchmarks/logs/ ni se pudieron generar en vivo.")

    filas: List[Dict[str, str]] = []

    for nombre, cmd, texto in casos:
        lineas_antes = len(texto.splitlines())
        tok_antes = tokens(texto)

        filtrado = filtro.filtrar(texto, comando=cmd)

        lineas_despues = len(filtrado.splitlines())
        tok_despues = tokens(filtrado)

        ahorro_lin = (1.0 - (lineas_despues / max(1, lineas_antes))) * 100.0
        ahorro_tok = (1.0 - (tok_despues / max(1, tok_antes))) * 100.0

        # Verificacion estricta: todos los errores presentes
        criticas = extraer_lineas_criticas(texto)
        errores_ok = True
        for err in criticas:
            if err not in filtrado:
                errores_ok = False
                break

        filas.append({
            "caso": nombre,
            "lin_ant": str(lineas_antes),
            "lin_des": str(lineas_despues),
            "ahorro_lin": f"{ahorro_lin:+.1f} %",
            "tok_ant": str(tok_antes),
            "tok_des": str(tok_despues),
            "ahorro_tok": f"{ahorro_tok:+.1f} %",
            "errores": f"100 % ({len(criticas)}/{len(criticas)})" if errores_ok else "ERROR FALTANTE",
        })

    # Imprimir tabla en Markdown
    print("\n# Benchmark de reduccion de ruido en terminal (SYNRAG filtrar - comandos ruidosos)\n")
    print("| Caso | Lineas antes | Lineas despues | Ahorro lineas | Tokens antes | Tokens despues | Ahorro tokens | Errores preservados |")
    print("|---|---|---|---|---|---|---|---|")
    for f in filas:
        print(f"| {f['caso']} | {f['lin_ant']} | {f['lin_des']} | {f['ahorro_lin']} | {f['tok_ant']} | {f['tok_des']} | {f['ahorro_tok']} | {f['errores']} |")
    print()


def generar_salidas_largas_reales() -> List[Tuple[str, str, str]]:
    """Genera 3 salidas largas reales del sistema para medir reduccion y preservacion de errores."""
    casos: List[Tuple[str, str, str]] = []

    # 1. find / -maxdepth 3 2>/dev/null
    try:
        p1 = subprocess.run(["find", "/", "-maxdepth", "3"], capture_output=True, text=True, errors="replace")
        s1 = p1.stdout
        if len(s1.splitlines()) > 200:
            casos.append(("find / -maxdepth 3", "find / -maxdepth 3 2>/dev/null", s1))
    except Exception:
        pass

    # 2. python 5000 lineas con errores y warnings intercalados
    script_5000 = (
        'import sys\n'
        'for i in range(5000):\n'
        '    if i == 500:\n'
        '        print("Traceback (most recent call last):")\n'
        '        print(\'  File "worker.py", line 42, in process\')\n'
        '        print("ValueError: Invalid configuration payload")\n'
        '    elif i == 1800:\n'
        '        print("WARNING: Disk buffer reaching threshold (85%)")\n'
        '    elif i == 3400:\n'
        '        print("ERROR: Failed to connect to replica node: connection refused")\n'
        '    else:\n'
        '        print(f"Line {i}: standard log event processing transaction {i*7}")\n'
    )
    p2 = subprocess.run([sys.executable, "-c", script_5000], capture_output=True, text=True)
    s2 = p2.stdout
    casos.append(("python (5.000 lineas con errores)", "python -c <script 5k lineas>", s2))

    # 3. journalctl --user -n 2000 --no-pager
    s3 = ""
    try:
        p3 = subprocess.run(["journalctl", "--user", "-n", "2000", "--no-pager"], capture_output=True, text=True, errors="replace")
        if p3.returncode == 0 and len(p3.stdout.splitlines()) > 200:
            s3 = p3.stdout
    except Exception:
        pass
    if not s3:
        # Fallback si journalctl esta vacio o restringido: dmesg o find en /usr
        p_fb = subprocess.run(["find", "/usr", "-maxdepth", "3"], capture_output=True, text=True, errors="replace")
        s3 = p_fb.stdout
        casos.append(("find /usr -maxdepth 3 (fallback logs)", "find /usr -maxdepth 3", s3))
    else:
        casos.append(("journalctl --user (logs sistema)", "journalctl --user -n 2000 --no-pager", s3))

    return casos


def ejecutar_benchmark_largas() -> None:
    casos = generar_salidas_largas_reales()
    filas: List[Dict[str, str]] = []

    for nombre, cmd, texto in casos:
        lineas_antes = len(texto.splitlines())
        tok_antes = tokens(texto)

        filtrado = filtro.filtrar_salida_larga(texto, comando=cmd)

        lineas_despues = len(filtrado.splitlines())
        tok_despues = tokens(filtrado)

        ahorro_lin = (1.0 - (lineas_despues / max(1, lineas_antes))) * 100.0
        ahorro_tok = (1.0 - (tok_despues / max(1, tok_antes))) * 100.0

        criticas = extraer_lineas_criticas(texto)
        errores_ok = True
        for err in criticas:
            if err not in filtrado:
                errores_ok = False
                break

        filas.append({
            "caso": nombre,
            "lin_ant": str(lineas_antes),
            "lin_des": str(lineas_despues),
            "ahorro_lin": f"{ahorro_lin:+.1f} %",
            "tok_ant": str(tok_antes),
            "tok_des": str(tok_despues),
            "ahorro_tok": f"{ahorro_tok:+.1f} %",
            "errores": f"100 % ({len(criticas)}/{len(criticas)})" if errores_ok else f"ERROR FALTANTE ({len(criticas)})",
        })

    print("\n# Benchmark de filtro de salidas largas (SYNRAG configure --filtro-largas)\n")
    print("| Caso | Lineas antes | Lineas despues | Ahorro lineas | Tokens antes | Tokens despues | Ahorro tokens | Errores preservados |")
    print("|---|---|---|---|---|---|---|---|")
    for f in filas:
        print(f"| {f['caso']} | {f['lin_ant']} | {f['lin_des']} | {f['ahorro_lin']} | {f['tok_ant']} | {f['tok_des']} | {f['ahorro_tok']} | {f['errores']} |")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark del filtro de terminal")
    parser.add_argument("--real", action="store_true", help="Genera ejecuciones vivas en temp")
    parser.add_argument("--largas-only", action="store_true", help="Solo mide salidas largas")
    args = parser.parse_args()
    if not args.largas_only:
        ejecutar_benchmark(usar_reales=args.real)
    ejecutar_benchmark_largas()

