#!/usr/bin/env python3
"""
benchmarks/agente/agente.py - Medicion de consumo de tokens con agente real y function calling.

Compara dos modos sobre las mismas preguntas en condiciones justas:
  - "sin": herramientas grep(patron) y read_file(ruta, desde, hasta)
  - "con": grep, read_file y search_desktop (indice LanceDB AST en memoria/temporal)

Uso:
  python benchmarks/agente/agente.py --repo-flask /ruta/a/flask --repo-hono /ruta/a/hono [--validar] [--rondas 2]
"""

import argparse
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "engine"))

try:
    import telemetry
    telemetry.record_search_event = lambda *a, **k: None  # no alterar la telemetria real
    import argon
    import indexer
    import server_mcp
except ImportError as err:
    sys.exit(f"No se pudo importar el motor de SynRAG ({err}). Ejecuta con el Python del entorno.")


SYSTEM_PROMPT_SIN = (
    "Eres un asistente de programacion que localiza codigo en repositorios.\n"
    "Tu objetivo es responder indicando con precision la ruta del archivo y el nombre de la funcion o simbolo que implementa o responde a lo solicitado.\n"
    "Dispones de herramientas para inspeccionar el repositorio: grep y read_file.\n"
    "En tu respuesta final, nombra explicitamente el archivo y la funcion o metodo correspondientes."
)

SYSTEM_PROMPT_CON = (
    "Eres un asistente de programacion que localiza codigo en repositorios.\n"
    "Tu objetivo es responder indicando con precision la ruta del archivo y el nombre de la funcion o simbolo que implementa o responde a lo solicitado.\n"
    "Dispones de herramientas para inspeccionar el repositorio: grep y read_file.\n"
    "Tambien dispones de search_desktop para buscar en el indice del repositorio por palabras clave o nombre de simbolo.\n"
    "En tu respuesta final, nombra explicitamente el archivo y la funcion o metodo correspondientes."
)

TOOLS_SIN = [
    {
        "function_declarations": [
            {
                "name": "grep",
                "description": "Busca un patron regex en los archivos de codigo del repositorio. Devuelve lineas en formato 'archivo:linea:contenido'.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "patron": {
                            "type": "STRING",
                            "description": "Patron regex a buscar (ej: 'def from_envvar' o 'getColorEnabled')."
                        }
                    },
                    "required": ["patron"]
                }
            },
            {
                "name": "read_file",
                "description": "Lee un rango de lineas de un archivo del repositorio.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "ruta": {
                            "type": "STRING",
                            "description": "Ruta relativa del archivo dentro del repositorio (ej: 'src/flask/config.py')."
                        },
                        "desde": {
                            "type": "INTEGER",
                            "description": "Numero de linea inicial (1-based, por defecto 1)."
                        },
                        "hasta": {
                            "type": "INTEGER",
                            "description": "Numero de linea final (1-based, por defecto 80)."
                        }
                    },
                    "required": ["ruta"]
                }
            }
        ]
    }
]

TOOLS_CON = [
    {
        "function_declarations": TOOLS_SIN[0]["function_declarations"] + [
            {
                "name": "search_desktop",
                "description": "Busca en el indice semantico y sintactico AST del repositorio por palabras clave o nombre exacto de simbolo.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "consulta": {
                            "type": "STRING",
                            "description": "Terminos de busqueda o nombre exacto del simbolo."
                        }
                    },
                    "required": ["consulta"]
                }
            }
        ]
    }
]


def ejecutar_grep(repo_dir: Path, patron: str, max_lineas: int = 35) -> str:
    if not patron or not patron.strip():
        return "Error: patron vacio."
    try:
        cmd = [
            "git", "-C", str(repo_dir), "grep", "-n", "-E", patron.strip(),
            "--", "*.ts", "*.tsx", "*.js", "*.jsx", "*.py",
            ":!*node_modules*", ":!*dist/*"
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            if r.stderr and "fatal:" in r.stderr:
                return f"Error en grep: {r.stderr.strip()}"
            return "No se encontraron coincidencias."
        lineas = [l for l in r.stdout.splitlines() if l.strip()]
        if not lineas:
            return "No se encontraron coincidencias."
        if len(lineas) > max_lineas:
            return "\n".join(lineas[:max_lineas]) + f"\n... [{len(lineas) - max_lineas} coincidencias adicionales omitidas]"
        return "\n".join(lineas)
    except subprocess.TimeoutExpired:
        return "Error: grep supero el tiempo limite."
    except Exception as e:
        return f"Error al ejecutar grep: {e}"


def ejecutar_read_file(repo_dir: Path, ruta: str, desde: int = 1, hasta: int = 80, max_lineas: int = 120) -> str:
    try:
        desde = max(1, int(desde or 1))
        hasta = max(desde, int(hasta or (desde + 79)))
        if hasta - desde + 1 > max_lineas:
            hasta = desde + max_lineas - 1

        limpia = ruta.strip().lstrip("/")
        if limpia.startswith(f"{repo_dir.name}/"):
            limpia = limpia[len(repo_dir.name) + 1:]

        target = (repo_dir / limpia).resolve()
        if not str(target).startswith(str(repo_dir.resolve())):
            return f"Error: ruta fuera del repositorio: {ruta}"
        if not target.is_file():
            candidatos = list(repo_dir.rglob(Path(limpia).name))
            if len(candidatos) == 1 and candidatos[0].is_file():
                target = candidatos[0]
            else:
                return f"Error: archivo '{ruta}' no encontrado en el repositorio."

        lineas = target.read_text(encoding="utf-8", errors="ignore").splitlines()
        total = len(lineas)
        if desde > total:
            return f"Error: linea inicial {desde} excede el total de lineas ({total})."

        fin = min(hasta, total)
        seleccion = lineas[desde - 1:fin]
        return "\n".join(f"{num}\t{lin}" for num, lin in enumerate(seleccion, start=desde))
    except Exception as e:
        return f"Error al leer archivo '{ruta}': {e}"


def ejecutar_search_desktop(repo_name: str, consulta: str) -> str:
    if not consulta or not consulta.strip():
        return "Error: consulta vacia."
    try:
        salida = server_mcp.search_desktop(consulta.strip(), limit=5, project=repo_name)
        return salida or "Sin resultados."
    except Exception as e:
        return f"Error en search_desktop: {e}"


def verificar_acierto(texto: str, q: Dict[str, Any]) -> bool:
    texto_min = (texto or "").lower()
    simbolo_min = str(q.get("simbolo", "")).lower()
    archivo_min = str(q.get("archivo", "")).lower()
    nombre_archivo = Path(q.get("archivo", "")).name.lower()

    simbolo_ok = bool(simbolo_min and simbolo_min in texto_min)
    archivo_ok = bool(
        archivo_min in texto_min
        or (archivo_min.replace("src/", "") in texto_min)
        or (nombre_archivo in texto_min)
    )
    return bool(simbolo_ok and archivo_ok)


def llamar_gemini(
    modelo: str,
    body: Dict[str, Any],
    api_key: str,
    max_reintentos: int = 5,
    pausa_base: float = 3.0
) -> Dict[str, Any]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
    data = json.dumps(body).encode("utf-8")

    for intento in range(max_reintentos):
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8", errors="ignore")
            except Exception:
                pass
            if e.code in (429, 503, 500, 504):
                tiempo_espera = pausa_base * (2 ** intento)
                sys.stderr.write(f"[HTTP {e.code}] Reintentando en {tiempo_espera:.1f}s (intento {intento + 1}/{max_reintentos})...\n")
                time.sleep(tiempo_espera)
                continue
            raise RuntimeError(f"Error HTTP {e.code}: {err_body or e.reason}")
        except urllib.error.URLError as e:
            tiempo_espera = pausa_base * (intento + 1)
            sys.stderr.write(f"[URLError {e.reason}] Reintentando en {tiempo_espera:.1f}s...\n")
            time.sleep(tiempo_espera)
            continue

    raise RuntimeError(f"Agotados los {max_reintentos} reintentos contra Gemini API.")


def ejecutar_agente(
    pregunta: Dict[str, Any],
    modo: str,
    repo_dir: Path,
    repo_name: str,
    modelo: str,
    api_key: str,
    max_turnos: int = 12,
    pausa_turno: float = 1.0,
    detalle: bool = False
) -> Dict[str, Any]:
    herramientas = TOOLS_CON if modo == "con" else TOOLS_SIN
    system_prompt = SYSTEM_PROMPT_CON if modo == "con" else SYSTEM_PROMPT_SIN

    contents: List[Dict[str, Any]] = [
        {"role": "user", "parts": [{"text": pregunta["pregunta"]}]}
    ]

    tokens_entrada = 0
    tokens_salida = 0
    tokens_total = 0
    turnos = 0
    texto_final = ""
    herramientas_usadas: List[Dict[str, Any]] = []

    for t in range(max_turnos):
        body = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": contents,
            "tools": herramientas,
            "generationConfig": {"temperature": 0.0}
        }

        res = llamar_gemini(modelo, body, api_key)
        turnos += 1

        usage = res.get("usageMetadata", {})
        prompt_cnt = usage.get("promptTokenCount", 0)
        cand_cnt = usage.get("candidatesTokenCount", 0)
        tot_cnt = usage.get("totalTokenCount", prompt_cnt + cand_cnt)

        tokens_entrada += prompt_cnt
        tokens_salida += cand_cnt
        tokens_total += tot_cnt

        candidates = res.get("candidates", [])
        if not candidates:
            break

        cand = candidates[0]
        content = cand.get("content", {})
        parts = content.get("parts", [])
        contents.append(content)

        function_calls = [p["functionCall"] for p in parts if "functionCall" in p]

        if not function_calls:
            texto_final = "\n".join(p.get("text", "") for p in parts if "text" in p).strip()
            if detalle:
                print(f"    [Turno {turnos}] Respuesta final recibida ({cand_cnt} tokens)")
            break

        respuestas_funciones = []
        for fc in function_calls:
            fn_name = fc.get("name", "")
            fn_args = fc.get("args", {})
            call_id = fc.get("id")

            herramientas_usadas.append({"nombre": fn_name, "args": fn_args, "turno": turnos})

            if detalle:
                print(f"    [Turno {turnos}] Llamada: {fn_name}({fn_args})")

            if fn_name == "grep":
                salida_fn = ejecutar_grep(repo_dir, str(fn_args.get("patron", "")))
            elif fn_name == "read_file":
                salida_fn = ejecutar_read_file(
                    repo_dir,
                    str(fn_args.get("ruta", "")),
                    fn_args.get("desde", 1),
                    fn_args.get("hasta", 80)
                )
            elif fn_name == "search_desktop":
                salida_fn = ejecutar_search_desktop(repo_name, str(fn_args.get("consulta", "")))
            else:
                salida_fn = f"Error: herramienta '{fn_name}' no disponible."

            part_resp: Dict[str, Any] = {
                "functionResponse": {
                    "name": fn_name,
                    "response": {"output": salida_fn}
                }
            }
            if call_id:
                part_resp["functionResponse"]["id"] = call_id
            respuestas_funciones.append(part_resp)

        contents.append({"role": "user", "parts": respuestas_funciones})

        if pausa_turno > 0:
            time.sleep(pausa_turno)

    if not texto_final and turnos >= max_turnos:
        texto_final = "(Limite de turnos alcanzado)"

    acerto = verificar_acierto(texto_final, pregunta)

    return {
        "pregunta_id": pregunta["id"],
        "repo": pregunta["repo"],
        "tipo": pregunta["tipo"],
        "modo": modo,
        "turnos": turnos,
        "tokens_entrada": tokens_entrada,
        "tokens_salida": tokens_salida,
        "tokens_total": tokens_total,
        "acerto": acerto,
        "respuesta_final": texto_final,
        "llamadas_herramientas": herramientas_usadas
    }


def indexar_repos_temporal(repos: Dict[str, Path]) -> Path:
    import tempfile
    temp_dir = Path(tempfile.mkdtemp(prefix="synrag-bench-agente-"))
    indexer.DB_PATH = temp_dir
    os.environ["SYNRAG_CARPETAS"] = ":".join(f"{path}={name}" for name, path in repos.items())
    indexer.index_desktop()
    return temp_dir


def generar_tabla_resumen(ejecuciones: List[Dict[str, Any]], preguntas: List[Dict[str, Any]]) -> str:
    lineas = []
    lineas.append("\n" + "=" * 94)
    lineas.append(f"{'ID':<12} {'Tipo':<8} {'Repo':<6} | {'Tok Con':>8} {'Tok Sin':>8} {'Dif %':>7} | {'Tur C':>5} {'Tur S':>5} | {'Ok C':>4} {'Ok S':>4} | {'Gana'}")
    lineas.append("-" * 94)

    por_pregunta: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for ej in ejecuciones:
        pid = ej["pregunta_id"]
        por_pregunta.setdefault(pid, {}).setdefault(ej["modo"], []).append(ej)

    preg_map = {p["id"]: p for p in preguntas}

    total_tok_con = 0
    total_tok_sin = 0
    total_in_con = 0
    total_in_sin = 0
    total_out_con = 0
    total_out_sin = 0
    aciertos_con = 0
    aciertos_sin = 0
    ganadas_con = 0
    ganadas_sin = 0
    empates = 0

    filas_ordenadas = sorted(por_pregunta.keys(), key=lambda x: (preg_map.get(x, {}).get("repo", ""), x))

    for pid in filas_ordenadas:
        p = preg_map.get(pid, {})
        runs_con = por_pregunta[pid].get("con", [])
        runs_sin = por_pregunta[pid].get("sin", [])

        if not runs_con or not runs_sin:
            continue

        tok_c = int(round(sum(r["tokens_total"] for r in runs_con) / len(runs_con)))
        tok_s = int(round(sum(r["tokens_total"] for r in runs_sin) / len(runs_sin)))
        in_c = int(round(sum(r["tokens_entrada"] for r in runs_con) / len(runs_con)))
        in_s = int(round(sum(r["tokens_entrada"] for r in runs_sin) / len(runs_sin)))
        out_c = int(round(sum(r["tokens_salida"] for r in runs_con) / len(runs_con)))
        out_s = int(round(sum(r["tokens_salida"] for r in runs_sin) / len(runs_sin)))

        tur_c = round(sum(r["turnos"] for r in runs_con) / len(runs_con), 1)
        tur_s = round(sum(r["turnos"] for r in runs_sin) / len(runs_sin), 1)

        ok_c = all(r["acerto"] for r in runs_con)
        ok_s = all(r["acerto"] for r in runs_sin)

        total_tok_con += tok_c
        total_tok_sin += tok_s
        total_in_con += in_c
        total_in_sin += in_s
        total_out_con += out_c
        total_out_sin += out_s

        if ok_c:
            aciertos_con += 1
        if ok_s:
            aciertos_sin += 1

        dif_pct = ((tok_c - tok_s) / tok_s * 100) if tok_s else 0

        if tok_c < tok_s:
            ganador = "SynRAG"
            ganadas_con += 1
        elif tok_c > tok_s:
            ganador = "Sin"
            ganadas_sin += 1
        else:
            ganador = "Empate"
            empates += 1

        tipo = p.get("tipo", "")[:7]
        repo = p.get("repo", "")[:6]
        c_str = "si" if ok_c else "NO"
        s_str = "si" if ok_s else "NO"

        lineas.append(f"{pid:<12} {tipo:<8} {repo:<6} | {tok_c:>8} {tok_s:>8} {dif_pct:>+6.1f}% | {tur_c:>5.1f} {tur_s:>5.1f} | {c_str:>4} {s_str:>4} | {ganador}")

    lineas.append("-" * 94)
    total_dif = ((total_tok_con - total_tok_sin) / total_tok_sin * 100) if total_tok_sin else 0
    lineas.append(f"{'TOTAL':<12} {'':<8} {'':<6} | {total_tok_con:>8} {total_tok_sin:>8} {total_dif:>+6.1f}% | {'':>5} {'':>5} | {aciertos_con:>4} {aciertos_sin:>4} | Con:{ganadas_con} Sin:{ganadas_sin}")
    lineas.append("=" * 94)

    lineas.append(f"\nResumen global:")
    lineas.append(f"  Tokens totales:          Con SynRAG = {total_tok_con:,} | Sin SynRAG = {total_tok_sin:,} (Diferencia: {total_dif:+.1f} %)")
    lineas.append(f"  Tokens entrada:          Con = {total_in_con:,} | Sin = {total_in_sin:,}")
    lineas.append(f"  Tokens salida:           Con = {total_out_con:,} | Sin = {total_out_sin:,}")
    lineas.append(f"  Aciertos (nombra ambos): Con = {aciertos_con}/{len(por_pregunta)} | Sin = {aciertos_sin}/{len(por_pregunta)}")
    lineas.append(f"  Preguntas donde gana:    SynRAG gana en {ganadas_con} | Sin gana en {ganadas_sin} | Empatan {empates}")

    return "\n".join(lineas)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Medicion de tokens con agente y function calling de Gemini.")
    ap.add_argument("--repo-flask", type=Path, help="Ruta al repositorio flask")
    ap.add_argument("--repo-hono", type=Path, help="Ruta al repositorio hono")
    ap.add_argument("--repos-dir", type=Path, help="Directorio que contiene subcarpetas flask y hono")
    ap.add_argument("--modelo", default="gemini-3.5-flash-lite", help="Modelo de Gemini (defecto: gemini-3.5-flash-lite)")
    ap.add_argument("--preguntas", type=Path, default=Path(__file__).parent / "preguntas.json", help="Ruta al archivo preguntas.json")
    ap.add_argument("--salida", type=Path, help="Ruta al archivo de salida JSON")
    ap.add_argument("--rondas", type=int, default=2, help="Numero de rondas por pregunta y modo (defecto: 2)")
    ap.add_argument("--validar", action="store_true", help="Corre solo 2 preguntas (1 de flask y 1 de hono) para validar conexion y herramientas")
    ap.add_argument("--pregunta-id", type=str, help="Filtra a una sola pregunta por ID")
    ap.add_argument("--pausa", type=float, default=1.5, help="Pausa en segundos entre llamadas para respetar cuota (defecto: 1.5)")
    ap.add_argument("--max-turnos", type=int, default=12, help="Maximo de turnos por ejecucion (defecto: 12)")
    ap.add_argument("--detalle", action="store_true", help="Muestra trazas de turnos y llamadas a herramientas")
    return ap.parse_args()


def main():
    args = parse_args()

    api_key = argon.get_api_key()
    if not api_key:
        sys.exit("Falta GEMINI_API_KEY. Configurala en el entorno o en .env.")

    flask_path: Optional[Path] = args.repo_flask
    hono_path: Optional[Path] = args.repo_hono

    if args.repos_dir:
        if not flask_path and (args.repos_dir / "flask").is_dir():
            flask_path = args.repos_dir / "flask"
        if not hono_path and (args.repos_dir / "hono").is_dir():
            hono_path = args.repos_dir / "hono"

    # Verificacion de existencia
    if not flask_path or not flask_path.is_dir():
        sys.exit("Falta --repo-flask o no es un directorio valido.")
    if not hono_path or not hono_path.is_dir():
        sys.exit("Falta --repo-hono o no es un directorio valido.")

    repos = {
        "flask": flask_path.resolve(),
        "hono": hono_path.resolve()
    }

    if not args.preguntas.is_file():
        sys.exit(f"Archivo de preguntas no encontrado: {args.preguntas}")

    todas_preguntas: List[Dict[str, Any]] = json.loads(args.preguntas.read_text(encoding="utf-8"))

    if args.pregunta_id:
        todas_preguntas = [p for p in todas_preguntas if p["id"] == args.pregunta_id]
        if not todas_preguntas:
            sys.exit(f"No se encontro ninguna pregunta con ID '{args.pregunta_id}'")

    if args.validar:
        print("[VALIDACION] Modo activado: seleccionando 2 preguntas (1 flask, 1 hono)...")
        p_flask = next((p for p in todas_preguntas if p["repo"] == "flask"), None)
        p_hono = next((p for p in todas_preguntas if p["repo"] == "hono"), None)
        todas_preguntas = [p for p in (p_flask, p_hono) if p is not None]
        args.rondas = 1

    print(f"[INFO] Indexando repositorios ({', '.join(repos.keys())}) en indice temporal...")
    temp_db = indexar_repos_temporal(repos)
    print(f"[INFO] Indice temporal listo en: {temp_db}")

    fecha_hoy = datetime.date.today().isoformat()
    salida_path = args.salida or (Path(__file__).parent / f"resultados-{fecha_hoy}.json")

    ejecuciones: List[Dict[str, Any]] = []

    total_pruebas = len(todas_preguntas) * 2 * args.rondas
    contador = 0

    print(f"\nIniciando benchmark con modelo '{args.modelo}': {len(todas_preguntas)} preguntas, 2 modos, {args.rondas} ronda(s) = {total_pruebas} ejecuciones.")

    try:
        for ronda in range(1, args.rondas + 1):
            print(f"\n--- RONDA {ronda} de {args.rondas} ---")
            for p in todas_preguntas:
                repo_name = p["repo"]
                repo_dir = repos[repo_name]

                for modo in ("con", "sin"):
                    contador += 1
                    print(f"[{contador}/{total_pruebas}] Ronda {ronda} | {p['id']} ({p['tipo']}, {repo_name}) | Modo: {modo.upper()} ... ", end="", flush=True)

                    t0 = time.time()
                    try:
                        res = ejecutar_agente(
                            pregunta=p,
                            modo=modo,
                            repo_dir=repo_dir,
                            repo_name=repo_name,
                            modelo=args.modelo,
                            api_key=api_key,
                            max_turnos=args.max_turnos,
                            pausa_turno=args.pausa,
                            detalle=args.detalle
                        )
                        elapsed = time.time() - t0
                        res["ronda"] = ronda
                        res["duracion_segundos"] = round(elapsed, 2)
                        ejecuciones.append(res)

                        ok_str = "OK" if res["acerto"] else "FALLO"
                        print(f"{ok_str} en {res['turnos']} turnos, {res['tokens_total']} tokens ({elapsed:.1f}s)")
                    except Exception as e:
                        print(f"ERROR: {e}")
                        ejecuciones.append({
                            "ronda": ronda,
                            "pregunta_id": p["id"],
                            "repo": repo_name,
                            "tipo": p["tipo"],
                            "modo": modo,
                            "error": str(e),
                            "acerto": False,
                            "tokens_total": 0,
                            "turnos": 0
                        })

                    if args.pausa > 0:
                        time.sleep(args.pausa)

    except KeyboardInterrupt:
        print("\n[AVISO] Interrupcion por teclado. Guardando resultados parciales...")

    # Generar resumen
    tabla = generar_tabla_resumen(ejecuciones, todas_preguntas)
    print(tabla)

    datos_guardar = {
        "fecha": fecha_hoy,
        "modelo": args.modelo,
        "rondas": args.rondas,
        "preguntas": todas_preguntas,
        "ejecuciones": ejecuciones,
        "tabla_resumen": tabla
    }

    salida_path.write_text(json.dumps(datos_guardar, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResultados guardados en: {salida_path}")


if __name__ == "__main__":
    main()
