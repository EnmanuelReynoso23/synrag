#!/usr/bin/env python3
"""
benchmarks/conciso.py - Medicion de ahorro y calidad: Normal vs Caveman (Conciso)

Compara las respuestas de un asistente de codigo convencional frente al modo
conciso (Caveman voice: respuesta directa, sin cortesias, sin emojis, codigo completo)
sobre 10 tareas tipicas de desarrollo con Google Gemini.

Metricas medidas:
  1. Tokens de salida (usageMetadata de Gemini o estimacion).
  2. Retencion de hechos tecnicos clave (3 a 5 hechos objetivos por tarea).
  3. Correccion y completitud del codigo producido.

Uso:
  python benchmarks/conciso.py            # ejecuta las llamadas con Gemini
  python benchmarks/conciso.py --leer     # muestra la tabla de los resultados guardados
  python benchmarks/conciso.py --bloque A.txt --salida B.json   # compara otro texto conciso (p. ej. el viejo y el nuevo)
"""

import ast
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

try:
    import argon
except ImportError:
    argon = None

ARCHIVO_RESULTADOS = Path(__file__).resolve().parent / "conciso-resultados.json"

CAVEMAN_SYSTEM_PROMPT = """Responde siguiendo estrictamente el modo conciso (Caveman):
- Responde de forma directa, breve y tecnica: primero la solucion o respuesta directa, luego la justificacion si hace falta.
- Sin relleno: elimina introducciones, saludos, disculpas, cortesias ("Claro", "Por supuesto", "Espero que esto ayude") y despedidas.
- Cero emojis: nunca uses emojis.
- Cero teatro: no uses lenguaje artificialmente roto ni fingas cavernicola. Si una frase clara y normal es corta, usala.
- CODIGO, COMANDOS, RUTAS, MENSAJES DE ERROR Y NOMBRES DE SIMBOLOS: SIEMPRE COMPLETOS Y LITERALES (nunca resumir, omitir ni truncar fragmentos funcionales).
- PREGUNTAS AL USUARIO Y AVISOS DE SEGURIDAD O DESTRUCTIVOS: SIEMPRE EN ORACIONES COMPLETAS Y CLARAS.
"""

TAREAS: List[Dict[str, Any]] = [
    {
        "id": "traceback_keyerror",
        "titulo": "Explicar error con traceback",
        "prompt": (
            "Explica el siguiente traceback de Python, que lo causa y como solucionarlo:\n"
            "Traceback (most recent call last):\n"
            "  File \"app.py\", line 42, in process_user\n"
            "    role = user_data['profile']['role']\n"
            "KeyError: 'role'"
        ),
        "hechos": [
            ("acceso_anidado", ["user_data", "profile", "role"]),
            ("clave_inexistente", ["keyerror", "no existe", "no se encuentra", "ausente", "missing"]),
            ("solucion_get_o_in", [".get", " in ", "get(", "verificar"]),
        ],
        "requiere_codigo": True,
        "lenguaje_codigo": "python",
    },
    {
        "id": "arreglo_zerodivision",
        "titulo": "Proponer arreglo con codigo",
        "prompt": (
            "Esta funcion falla con ZeroDivisionError si la lista esta vacia o no tiene numeros positivos. "
            "Propon el arreglo con el codigo corregido completo:\n"
            "def calcular_promedio_positivos(valores: list[float]) -> float:\n"
            "    positivos = [v for v in valores if v > 0]\n"
            "    return sum(positivos) / len(positivos)"
        ),
        "hechos": [
            ("causa_zerodivision", ["zerodivisionerror", "division por cero", "división por cero", "len(positivos)", "vacia", "vacía"]),
            ("guard_clause_o_if", ["if not positivos", "len(positivos) == 0", "if len", "if positivos"]),
            ("retorno_seguro", ["return 0", "return none", "raise"]),
        ],
        "requiere_codigo": True,
        "lenguaje_codigo": "python",
    },
    {
        "id": "resumir_diff",
        "titulo": "Resumir un diff de git",
        "prompt": (
            "Resume este diff de git explicando el cambio y la razon de seguridad:\n"
            "diff --git a/auth.py b/auth.py\n"
            "--- a/auth.py\n"
            "+++ b/auth.py\n"
            "@@ -10,3 +10,4 @@ def verify_token(token: str) -> bool:\n"
            "-    if token == SECRET_KEY:\n"
            "+    if hmac.compare_digest(token, SECRET_KEY):\n"
            "+        log_auth_success()\n"
            "         return True"
        ),
        "hechos": [
            ("cambio_hmac", ["hmac", "compare_digest"]),
            ("timing_attacks", ["timing", "temporizacion", "temporización", "tiempo constante", "fuerza bruta"]),
            ("auditoria_log", ["log_auth_success", "log", "registro", "auditoria", "auditoría"]),
        ],
        "requiere_codigo": False,
        "lenguaje_codigo": "",
    },
    {
        "id": "arquitectura_sse_vs_ws",
        "titulo": "Pregunta de arquitectura (SSE vs WS)",
        "prompt": (
            "Cuando conviene usar Server-Sent Events (SSE) en lugar de WebSockets en una aplicacion web?"
        ),
        "hechos": [
            ("unidireccional_vs_bidireccional", ["unidireccional", "servidor a cliente", "bidireccional", "full-duplex"]),
            ("sobre_http_reconexion", ["http", "reconexion", "reconexión", "proxies", "firewall"]),
            ("casos_uso_adecuados", ["streaming", "notificaciones", "llm", "feed", "eventos"]),
        ],
        "requiere_codigo": False,
        "lenguaje_codigo": "",
    },
    {
        "id": "revision_fetch_concurrencia",
        "titulo": "Revisar funcion asincrona",
        "prompt": (
            "Revisa la siguiente funcion TypeScript y senala los problemas principales:\n"
            "async function fetchUsers(ids: string[]) {\n"
            "    const results = [];\n"
            "    for (const id of ids) {\n"
            "        const res = await fetch(`/api/users/${id}`);\n"
            "        results.push(await res.json());\n"
            "    }\n"
            "    return results;\n"
            "}"
        ),
        "hechos": [
            ("llamadas_secuenciales", ["secuencial", "serie", "promise.all", "concurren", "cascada", "waterfall"]),
            ("falta_res_ok", ["res.ok", "status", "http", "ok"]),
            ("falta_manejo_errores", ["try", "catch", "error", "excepcion", "excepción", "fallo"]),
        ],
        "requiere_codigo": True,
        "lenguaje_codigo": "typescript",
    },
    {
        "id": "optimizar_n_mas_uno",
        "titulo": "Optimizar consulta BD (N+1)",
        "prompt": (
            "En Django ORM, la siguiente vista tarda segundos porque ejecuta decenas de consultas:\n"
            "libros = Libro.objects.all()\n"
            "for l in libros:\n"
            "    print(l.autor.nombre)\n"
            "Cual es la causa exacta y como se optimiza en una sola linea de codigo?"
        ),
        "hechos": [
            ("problema_n_mas_uno", ["n+1", "n + 1", "consulta por cada"]),
            ("tecnica_select_related", ["select_related", "join"]),
            ("linea_optimizada", ["select_related('autor')", "select_related(\"autor\")"]),
        ],
        "requiere_codigo": True,
        "lenguaje_codigo": "python",
    },
    {
        "id": "diagnostico_jwt",
        "titulo": "Diagnosticar error JWT",
        "prompt": (
            "Un microservicio lanza 'jwt.exceptions.InvalidSignatureError: Signature verification failed' "
            "al validar un token. Cuales son las 3 causas mas habituales y como verificarlas?"
        ),
        "hechos": [
            ("clave_incorrecta", ["clave", "secret", "key", "publica", "pública", "privada"]),
            ("algoritmo_discordante", ["algoritmo", "hs256", "rs256", "alg"]),
            ("token_alterado", ["alterado", "modificado", "payload", "truncado", "header", "firma"]),
        ],
        "requiere_codigo": False,
        "lenguaje_codigo": "",
    },
    {
        "id": "refactorizar_guard_clauses",
        "titulo": "Refactorizar con guard clauses",
        "prompt": (
            "Refactoriza esta funcion en Python eliminando el anidamiento profundo con clausulas de guarda (guard clauses). "
            "Devuelve el codigo corregido completo:\n"
            "def procesar_pago(usuario, monto):\n"
            "    if usuario is not None:\n"
            "        if usuario.is_active:\n"
            "            if monto > 0:\n"
            "                if usuario.saldo >= monto:\n"
            "                    usuario.saldo -= monto\n"
            "                    return True\n"
            "    return False"
        ),
        "hechos": [
            ("guard_clauses", ["guard", "guarda", "retorno temprano", "early return", "return false"]),
            ("eliminacion_anidamiento", ["anidamiento", "indentacion", "indentación", "plano"]),
            ("preservacion_saldo", ["saldo -= monto", "saldo >= monto", "return true"]),
        ],
        "requiere_codigo": True,
        "lenguaje_codigo": "python",
    },
    {
        "id": "implementar_debounce",
        "titulo": "Implementar debounce en TypeScript",
        "prompt": (
            "Implementa una funcion `debounce` en TypeScript que posponga la llamada a una funcion `fn` "
            "hasta que pasen `delay` milisegundos sin nuevas invocaciones. Muestra el codigo completo con tipos."
        ),
        "hechos": [
            ("clear_set_timeout", ["settimeout", "cleartimeout"]),
            ("clausura_timer", ["return", "timer", "timeout"]),
            ("paso_de_argumentos", ["args", "apply", "...args", "fn("]),
        ],
        "requiere_codigo": True,
        "lenguaje_codigo": "typescript",
    },
    {
        "id": "typescript_strict_null",
        "titulo": "Resolver error strictNullChecks",
        "prompt": (
            "En TypeScript con strictNullChecks: const apiKey: string = process.env.API_KEY da el error "
            "'Type string | undefined is not assignable to type string'. "
            "Explica por que ocurre y muestra las 3 formas habituales de resolverlo en codigo."
        ),
        "hechos": [
            ("variable_undefined_en_env", ["undefined", "process.env", "entorno"]),
            ("incompatibilidad_de_tipos", ["strictnullchecks", "incompatible", "no asignable", "undefined"]),
            ("tres_soluciones", ["??", "!", "if", "throw"]),
        ],
        "requiere_codigo": True,
        "lenguaje_codigo": "typescript",
    },
]


def llamar_gemini(prompt: str, key: str, max_retries: int = 4) -> Dict[str, Any]:
    """Llama a Gemini probando la cadena de modelos y manejando reintentos ante 429/503."""
    modelos = ["gemini-2.5-flash", "gemini-3.5-flash-lite"]
    ultimo_error = ""

    for modelo in modelos:
        for intento in range(max_retries):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            try:
                t0 = time.time()
                with urllib.request.urlopen(req, timeout=35) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    cand = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    meta = data.get("usageMetadata", {})
                    tokens = meta.get("candidatesTokenCount", (len(cand) + 3) // 4)
                    return {
                        "text": cand,
                        "tokens": tokens,
                        "model": modelo,
                        "latency": round(time.time() - t0, 2),
                    }
            except urllib.error.HTTPError as e:
                ultimo_error = f"HTTP {e.code}"
                if e.code in (429, 503):
                    espera = 3 * (intento + 1)
                    time.sleep(espera)
                    continue
                break
            except Exception as e:
                ultimo_error = str(e)
                time.sleep(2)
                continue

    raise RuntimeError(f"Fallo en Gemini tras reintentos: {ultimo_error}")


def evaluar_hechos(texto: str, lista_hechos: List[Tuple[str, List[str]]]) -> Tuple[int, int, List[str]]:
    """Evalua si los hechos requeridos estan presentes en la respuesta."""
    texto_lower = texto.lower()
    encontrados = []
    for clave, variantes in lista_hechos:
        if any(v.lower() in texto_lower for v in variantes):
            encontrados.append(clave)
    return len(encontrados), len(lista_hechos), encontrados


def evaluar_codigo(texto: str, lenguaje: str, requiere: bool) -> Tuple[bool, str]:
    """Evalua si el codigo presente en la respuesta es sintacticamente valido y completo."""
    if not requiere:
        return True, "n/a"

    # Extraer bloques de codigo markdown
    bloques = re.findall(r"```(?:[a-zA-Z0-9_-]+)?\n(.*?)```", texto, re.DOTALL)
    # Extraer fragmentos inline `codigo`
    inlines = re.findall(r"`([^`\n]+)`", texto)
    candidatos = bloques + [i for i in inlines if any(k in i for k in ("def ", "=", "select_related", "return", "const ", "await "))]

    if not candidatos:
        lineas_codigo = [l for l in texto.splitlines() if l.strip().startswith(("def ", "const ", "let ", "function "))]
        if lineas_codigo:
            candidatos = ["\n".join(lineas_codigo)]
        else:
            return False, "sin codigo detectado"

    truncamientos = ["<completar>", "... resto del codigo ...", "TODO: implement"]

    if lenguaje == "python":
        for c in candidatos:
            if any(t in c for t in truncamientos):
                continue
            try:
                ast.parse(c)
                return True, "valido"
            except SyntaxError:
                pass
        return False, "sintaxis python invalida o truncada"

    elif lenguaje == "typescript":
        for c in candidatos:
            if any(t in c for t in truncamientos):
                continue
            if c.count("{") == c.count("}") and c.count("(") == c.count(")") and len(c.strip()) > 5:
                return True, "valido"
        return False, "sintaxis typescript invalida"

    return True, "valido"


def ejecutar_benchmark(sistema: str = CAVEMAN_SYSTEM_PROMPT, salida: Path = ARCHIVO_RESULTADOS) -> Dict[str, Any]:
    if not argon:
        sys.exit("No se pudo importar argon. Revisa que engine/ este en sys.path.")
    key = argon.get_api_key()
    if not key:
        sys.exit("Falta GEMINI_API_KEY. No se puede ejecutar el benchmark.")

    resultados = []
    print(f"Ejecutando medicion con {len(TAREAS)} tareas tipicas...")

    for i, t in enumerate(TAREAS, start=1):
        tid = t["id"]
        titulo = t["titulo"]
        prompt = t["prompt"]
        hechos_spec = t["hechos"]
        req_cod = t["requiere_codigo"]
        leng = t["lenguaje_codigo"]

        print(f"[{i:02d}/{len(TAREAS):02d}] {titulo} ...", end="", flush=True)

        # 1. Normal
        r_normal = llamar_gemini(prompt, key)
        time.sleep(2.5)

        # 2. Caveman
        prompt_caveman = f"{sistema}\n\nConsulta:\n{prompt}"
        r_cave = llamar_gemini(prompt_caveman, key)
        time.sleep(2.5)

        # Evaluaciones
        h_norm_ok, h_norm_total, h_norm_lista = evaluar_hechos(r_normal["text"], hechos_spec)
        h_cave_ok, h_cave_total, h_cave_lista = evaluar_hechos(r_cave["text"], hechos_spec)

        c_norm_ok, c_norm_msg = evaluar_codigo(r_normal["text"], leng, req_cod)
        c_cave_ok, c_cave_msg = evaluar_codigo(r_cave["text"], leng, req_cod)

        tok_norm = r_normal["tokens"]
        tok_cave = r_cave["tokens"]
        ahorro_pct = round(((tok_norm - tok_cave) / tok_norm) * 100, 1) if tok_norm > 0 else 0.0

        item = {
            "id": tid,
            "titulo": titulo,
            "prompt": prompt,
            "normal": {
                "tokens": tok_norm,
                "latencia_s": r_normal["latency"],
                "modelo": r_normal["model"],
                "hechos_conservados": f"{h_norm_ok}/{h_norm_total}",
                "hechos_lista": h_norm_lista,
                "codigo_valido": c_norm_ok,
                "codigo_detalle": c_norm_msg,
                "texto": r_normal["text"],
            },
            "caveman": {
                "tokens": tok_cave,
                "latencia_s": r_cave["latency"],
                "modelo": r_cave["model"],
                "hechos_conservados": f"{h_cave_ok}/{h_cave_total}",
                "hechos_lista": h_cave_lista,
                "codigo_valido": c_cave_ok,
                "codigo_detalle": c_cave_msg,
                "texto": r_cave["text"],
            },
            "ahorro_tokens_pct": ahorro_pct,
        }
        resultados.append(item)
        print(f" Normal: {tok_norm} tok | Caveman: {tok_cave} tok ({ahorro_pct:+.1f}%)")

    datos_finales = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_tareas": len(resultados),
        "total_tokens_normal": sum(r["normal"]["tokens"] for r in resultados),
        "total_tokens_caveman": sum(r["caveman"]["tokens"] for r in resultados),
        "ahorro_total_pct": round(
            (
                (sum(r["normal"]["tokens"] for r in resultados) - sum(r["caveman"]["tokens"] for r in resultados))
                / sum(r["normal"]["tokens"] for r in resultados)
            )
            * 100,
            1,
        ),
        "tareas": resultados,
    }

    datos_finales["sistema_caveman_sha256"] = hashlib.sha256(sistema.encode("utf-8")).hexdigest()[:12]
    salida.write_text(json.dumps(datos_finales, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nResultados guardados en: {salida}")
    return datos_finales


def mostrar_tabla(datos: Dict[str, Any]) -> None:
    tareas = datos.get("tareas", [])
    print("\n" + "=" * 90)
    print("  BENCHMARK: MODO NORMAL VS MODO CONCISO (CAVEMAN) CON GEMINI")
    print("=" * 90)
    print(f"{'Tarea':<32} | {'Normal':<8} | {'Caveman':<8} | {'Ahorro':<8} | {'Hechos N':<8} | {'Hechos C':<8} | {'Cod OK'}")
    print("-" * 90)

    for t in tareas:
        tit = t["titulo"][:32]
        tn = t["normal"]["tokens"]
        tc = t["caveman"]["tokens"]
        ah = f"{t['ahorro_tokens_pct']:+.1f}%"
        hn = t["normal"]["hechos_conservados"]
        hc = t["caveman"]["hechos_conservados"]
        cn = "SI" if t["normal"]["codigo_valido"] else "NO"
        cc = "SI" if t["caveman"]["codigo_valido"] else "NO"
        cod_str = f"N:{cn}/C:{cc}"
        print(f"{tit:<32} | {tn:<8} | {tc:<8} | {ah:<8} | {hn:<8} | {hc:<8} | {cod_str}")

    print("-" * 90)
    tot_n = datos.get("total_tokens_normal", 0)
    tot_c = datos.get("total_tokens_caveman", 0)
    tot_ah = datos.get("ahorro_total_pct", 0)
    print(f"{'TOTAL':<32} | {tot_n:<8} | {tot_c:<8} | {tot_ah:+.1f}% |")
    print("=" * 90)


def _valor_de(opcion: str) -> Optional[str]:
    if opcion not in sys.argv:
        return None
    i = sys.argv.index(opcion)
    if i + 1 >= len(sys.argv):
        sys.exit(f"Falta el valor de {opcion}.")
    return sys.argv[i + 1]


def main():
    if "--leer" in sys.argv:
        if not ARCHIVO_RESULTADOS.is_file():
            sys.exit(f"No existe {ARCHIVO_RESULTADOS}. Ejecuta primero sin --leer.")
        datos = json.loads(ARCHIVO_RESULTADOS.read_text(encoding="utf-8"))
        mostrar_tabla(datos)
    else:
        # --bloque ARCHIVO: usa ese texto (sin marcadores) como modo conciso en vez del prompt fijo.
        # --salida ARCHIVO: guarda en ese archivo y no en conciso-resultados.json.
        bloque = _valor_de("--bloque")
        salida = _valor_de("--salida")
        sistema = CAVEMAN_SYSTEM_PROMPT
        if bloque:
            texto = Path(bloque).read_text(encoding="utf-8")
            sistema = texto.replace("<!-- SYNRAG-CONCISO:BEGIN -->", "").replace("<!-- SYNRAG-CONCISO:END -->", "").strip() + "\n"
        datos = ejecutar_benchmark(sistema, Path(salida) if salida else ARCHIVO_RESULTADOS)
        mostrar_tabla(datos)


if __name__ == "__main__":
    main()
