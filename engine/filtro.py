#!/usr/bin/env python3
"""
Filtro de salida de terminal para SyntaxRAG (SYNRAG).

Reduce ruido de comandos largos (compilacion, dependencias, pruebas) conservando
de forma estricta los errores, advertencias y las ultimas lineas de salida.
Determinista y sin red.
"""

import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set, Tuple

ANSI_RE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# Palabras clave de error/fallo/advertencia que NUNCA deben perderse
RE_ERROR = re.compile(
    r'(?:\b(?:error|errors|fail|failed|failure|failures|failing|exception|exceptions|traceback|panic|warning|warnings|warn|warns|assert|assertion)\b'
    r'|AssertionError|TypeError|ValueError|RuntimeError|KeyError|AttributeError|npm\s+ERR!)',
    re.IGNORECASE,
)

# Patrones de progreso en una sola linea
RE_PROGRESS_BAR = re.compile(
    r'^\s*(?:\[[\s=\-#\*>]*\]\s*\d+%|\d+%\s*\[[\s=\-#\*>]*\]|\d+/\d+\s*\[[\s=\-#\*>]*\]|\s*\|\s*[\#=█\s]+\|\s*\d+%|[━╸─=\-#\*█]{3,}\s+.*)'
)


def quitar_ansi(texto: str) -> str:
    """Elimina secuencias de escape ANSI de una cadena."""
    return ANSI_RE.sub('', texto)


def _es_ruido_npm(linea: str) -> bool:
    l = linea.strip().lower()
    return l.startswith("npm warn deprecated") or l.startswith("npm error deprecated")


def _es_ruido_pip(linea: str) -> bool:
    l = linea.strip().lower()
    if l.startswith("collecting ") and not l.startswith("collecting ..."):
        return True
    if l.startswith("downloading ") or l.startswith("using cached ") or l.startswith("requirement already satisfied:"):
        return True
    if re.match(r'^[━╸─=\-#\*█]{3,}\s+.*', linea.strip()):
        return True
    return False


def _es_ruido_cargo(linea: str) -> bool:
    l = linea.strip().lower()
    return bool(re.match(r'^(?:compiling|downloaded|checking)\s+[\w\-_]+', l))


def _es_ruido_agrupado(linea: str) -> bool:
    """Detecta lineas que pertenecen a categorias de ruido agrupable."""
    return _es_ruido_npm(linea) or _es_ruido_pip(linea) or _es_ruido_cargo(linea)


def _patron_cuasi_igual(linea: str) -> str:
    """Normaliza una linea reemplazando secuencias de numeros por comodin."""
    return re.sub(r'\d+', '#', linea.strip())


def _limpiar_lineas_raw(texto: str) -> List[str]:
    """
    Normaliza saltos de linea y resuelve sobreescrituras por '\\r'.
    Para lineas con '\\r', conserva el ultimo segmento no vacio.
    """
    texto_sin_ansi = quitar_ansi(texto)
    norm = texto_sin_ansi.replace('\r\n', '\n')
    chunks = norm.split('\n')
    
    # Si termina en salto de linea, el split produce un ultimo string vacio extra
    if chunks and chunks[-1] == "":
        chunks.pop()

    lineas_limpias: List[str] = []
    for chunk in chunks:
        if '\r' in chunk:
            partes = [p for p in chunk.split('\r') if p.strip()]
            if partes:
                lineas_limpias.append(partes[-1])
        else:
            lineas_limpias.append(chunk)

    return lineas_limpias


def filtrar(texto: str, comando: str = "") -> str:
    """
    Filtra la salida de terminal reduciendo ruido repetitivo y barras de progreso.
    
    Reglas:
      1. Si el texto tiene menos de 40 lineas (segun lineas originales), se devuelve igual.
      2. Quita codigos ANSI y limpia progreso sobreescrito con '\\r'.
      3. Siempre conserva las ultimas 30 lineas de la salida.
      4. NUNCA quita lineas de error, fail, failed, exception, traceback, panic, warning/warn
         (excepto npm WARN deprecated), assert, ni las 2 lineas anteriores y posteriores.
      5. Agrupa ruido conocido (npm WARN deprecated, pip Collecting/Downloading, cargo Compiling).
      6. Colapsa lineas repetidas o casi iguales (mismo texto salvo numeros) en una con '(xN)'.
      7. Agrega encabezado: '[filtrado: M -> N lineas]'.
    """
    if not texto:
        return ""

    lineas_raw = texto.splitlines()
    orig_line_count = len(lineas_raw)

    if orig_line_count < 40:
        return texto

    lineas = _limpiar_lineas_raw(texto)
    n = len(lineas)

    # 1. Identificar lineas protegidas
    protegidas: Set[int] = set()

    # Siempre conserva las ultimas 30 lineas
    for i in range(max(0, n - 30), n):
        protegidas.add(i)

    # Proteger errores, fallos y advertencias legitimas junto a +/- 2 lineas
    for i, linea in enumerate(lineas):
        if not _es_ruido_agrupado(linea) and RE_ERROR.search(linea):
            for offset in (-2, -1, 0, 1, 2):
                idx = i + offset
                if 0 <= idx < n:
                    protegidas.add(idx)

    # 2. Procesar el texto respetando lineas protegidas y colapsando/agrupando el resto
    resultado: List[str] = []
    i = 0
    while i < n:
        if i in protegidas:
            resultado.append(lineas[i])
            i += 1
            continue

        # Iniciar tramo no protegido
        inicio_tramo = i
        while i < n and i not in protegidas:
            i += 1
        fin_tramo = i  # rango [inicio_tramo, fin_tramo)

        k = inicio_tramo
        while k < fin_tramo:
            linea_act = lineas[k]
            linea_lower = linea_act.strip().lower()

            # Grupo: npm WARN deprecated
            if _es_ruido_npm(linea_act):
                conteo = 1
                while k + conteo < fin_tramo:
                    if _es_ruido_npm(lineas[k + conteo]):
                        conteo += 1
                    else:
                        break
                resultado.append(f"[npm WARN deprecated: {conteo} avisos]")
                k += conteo
                continue

            # Grupo: pip Collecting / Downloading
            if _es_ruido_pip(linea_act):
                conteo = 1
                while k + conteo < fin_tramo:
                    if _es_ruido_pip(lineas[k + conteo]):
                        conteo += 1
                    else:
                        break
                resultado.append(f"[pip: {conteo} operaciones de descarga/recoleccion]")
                k += conteo
                continue

            # Grupo: cargo Compiling / Downloaded
            if _es_ruido_cargo(linea_act):
                conteo = 1
                while k + conteo < fin_tramo:
                    if _es_ruido_cargo(lineas[k + conteo]):
                        conteo += 1
                    else:
                        break
                resultado.append(f"[cargo: {conteo} crates compilados]")
                k += conteo
                continue

            # Descartar barras de progreso aisladas
            if RE_PROGRESS_BAR.match(linea_act):
                k += 1
                continue

            # Colapso de lineas repetidas o casi iguales (mismo texto salvo numeros)
            patron_act = _patron_cuasi_igual(linea_act)
            conteo = 1
            while k + conteo < fin_tramo:
                sig = lineas[k + conteo]
                if _patron_cuasi_igual(sig) == patron_act:
                    conteo += 1
                else:
                    break

            if conteo > 1:
                if linea_act.strip() == "":
                    resultado.append("")
                else:
                    # Mostrar la linea colapsada con el sufijo (xN)
                    resultado.append(f"{linea_act.rstrip()} (x{conteo})")
                k += conteo
            else:
                resultado.append(linea_act)
                k += 1

    encabezado = f"[filtrado: {orig_line_count} -> {len(resultado)} lineas]"
    cuerpo = "\n".join(resultado)
    return f"{encabezado}\n{cuerpo}\n"


def obtener_umbrales() -> Tuple[int, int]:
    """Obtiene los umbrales de lineas y caracteres para el filtro de salidas largas."""
    try:
        lineas = int(os.environ.get("SYNRAG_FILTRO_UMBRAL_LINEAS", "200"))
    except ValueError:
        lineas = 200
    try:
        caracteres = int(os.environ.get("SYNRAG_FILTRO_UMBRAL_CARACTERES", "12000"))
    except ValueError:
        caracteres = 12000
    return lineas, caracteres


def obtener_carpeta_salidas() -> Path:
    """Devuelve la ruta a ~/.cache/synrag/salidas/ (o $XDG_CACHE_HOME)."""
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else (Path.home() / ".cache")
    carpeta = base / "synrag" / "salidas"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def limpiar_salidas_antiguas(carpeta: Path, max_edad_segundos: float = 86400) -> int:
    """Elimina archivos .log con mas de 24 horas (o max_edad_segundos)."""
    if not carpeta.is_dir():
        return 0
    ahora = time.time()
    eliminados = 0
    for arch in carpeta.glob("*.log"):
        try:
            if ahora - arch.stat().st_mtime > max_edad_segundos:
                arch.unlink(missing_ok=True)
                eliminados += 1
        except Exception:
            pass
    return eliminados


def guardar_salida_completa(texto: str, prefijo: str = "salida") -> Path:
    """Guarda la salida completa sin recortar en la carpeta de cache y limpia logs viejos."""
    carpeta = obtener_carpeta_salidas()
    limpiar_salidas_antiguas(carpeta)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    rand_suffix = uuid.uuid4().hex[:8]
    archivo = carpeta / f"{prefijo}_{stamp}_{rand_suffix}.log"
    archivo.write_text(texto, encoding="utf-8", errors="replace")
    return archivo


LIMITE_CLAUDE_CODE = 30000  # caracteres que Claude Code entrega al hook PostToolUse


def filtrar_salida_larga(texto: str, comando: str = "") -> str:
    """
    Filtra salidas que superan el umbral (por defecto 200 lineas o 12.000 caracteres).

    Conserva:
      - Las primeras 40 lineas.
      - TODAS las lineas de error/warning/traceback con 2 lineas de contexto (+/- 2).
      - Las ultimas 60 lineas.
      - En cada hueco omitido: '[synrag: N lineas omitidas; salida completa en <ruta>]'.

    Guarda la salida completa en ~/.cache/synrag/salidas/ (o $XDG_CACHE_HOME).
    Por debajo del umbral devuelve el texto intacto.
    Comprueba de forma estricta que lo devuelto nunca sea mas largo que la salida original.
    """
    if not texto:
        return ""

    umbral_lineas, umbral_chars = obtener_umbrales()
    lineas = texto.splitlines()
    total_lineas = len(lineas)
    total_chars = len(texto)

    if total_lineas <= umbral_lineas and total_chars <= umbral_chars:
        return texto

    # Supero el umbral: guardar salida completa
    archivo_salida = guardar_salida_completa(texto)
    ruta_str = str(archivo_salida.resolve())

    # Identificar indices a incluir
    incluir: Set[int] = set()

    # Primeras 40 lineas
    for i in range(min(40, total_lineas)):
        incluir.add(i)

    # Ultimas 60 lineas
    for i in range(max(0, total_lineas - 60), total_lineas):
        incluir.add(i)

    # Lineas de error / warning / traceback con +/- 2 lineas de contexto
    for i, l in enumerate(lineas):
        l_limpia = quitar_ansi(l)
        if RE_ERROR.search(l_limpia):
            for offset in (-2, -1, 0, 1, 2):
                idx = i + offset
                if 0 <= idx < total_lineas:
                    incluir.add(idx)

    # Reconstruir salida con marcadores de omision
    resultado_lineas: List[str] = []
    i = 0
    while i < total_lineas:
        if i in incluir:
            resultado_lineas.append(lineas[i])
            i += 1
        else:
            inicio_gap = i
            while i < total_lineas and i not in incluir:
                i += 1
            cant_omitidas = i - inicio_gap
            resultado_lineas.append(f"[synrag: {cant_omitidas} lineas omitidas]")

    # Aviso una sola vez (antes la ruta se repetia en cada hueco). Claude Code pasa al hook la
    # salida ya cortada a 30.000 caracteres y guarda la completa por su cuenta: entonces esta
    # copia NO es la salida completa y no se dice que lo sea.
    if total_chars >= LIMITE_CLAUDE_CODE:
        aviso = (f"[synrag: salida recortada. Claude Code ya la habia cortado a {LIMITE_CLAUDE_CODE:,} caracteres "
                 f"y guarda la completa; copia parcial en {ruta_str}]")
    else:
        aviso = f"[synrag: salida recortada; completa en {ruta_str}]"
    resultado_lineas.insert(0, aviso)

    resultado = "\n".join(resultado_lineas)
    if texto.endswith("\n"):
        resultado += "\n"

    # Regla 4: Lo devuelto nunca es mas largo que la salida original
    if len(resultado) >= total_chars or len(resultado_lineas) >= total_lineas:
        try:
            archivo_salida.unlink(missing_ok=True)
        except Exception:
            pass
        return texto

    return resultado

