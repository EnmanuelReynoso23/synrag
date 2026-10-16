"""
engine/argon.py - Coprocesador Inteligente para SynRAG
Conecta el grafo y fragmentos AST locales con la API de Google Gemini. OPCIONAL: sus herramientas solo
se registran si el usuario pone su propia GEMINI_API_KEY; es lo unico del motor que usa la red.
"""

import os
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Dict, Any, Optional



def get_api_key() -> str:
    """Obtiene la clave de API desde variable de entorno o archivo .env local."""
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"].strip()

    env_paths = [
        Path.home() / ".local" / "opt" / "lancedb-hub" / ".env",
        Path(__file__).parent.parent / ".env",
    ]
    for p in env_paths:
        if p.is_file():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip()

    return ""


MODELOS_POR_DEFECTO = "gemini-4-argon,gemini-3.5-flash,gemini-3.5-flash-lite"


def modelos() -> List[str]:
    """Cadena de modelos a probar en orden; se cambia con SYNRAG_GEMINI_MODELOS (separados por coma)."""
    return [m.strip() for m in (os.environ.get("SYNRAG_GEMINI_MODELOS") or MODELOS_POR_DEFECTO).split(",") if m.strip()]


def disponible() -> bool:
    """Las herramientas de Gemini solo se registran si el usuario configuro su propia clave."""
    return bool(get_api_key())


def call_gemini_model(prompt: str, preferred_model: str = "") -> Dict[str, Any]:
    """Llama a Gemini probando la cadena de modelos; pasa al siguiente si uno no tiene cuota, esta
    saturado o no existe para esa clave (429, 503, 404)."""
    key = get_api_key()
    if not key:
        return {"success": False, "error": "Falta GEMINI_API_KEY (variable de entorno o .env).", "model": ""}
    models_to_try = modelos()
    if preferred_model:
        models_to_try = [preferred_model] + [m for m in models_to_try if m != preferred_model]
    preferred_model = models_to_try[0]

    last_error = ""
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 4096
            }
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return {
                    "success": True,
                    "model": model_name,
                    "fallback_used": model_name != preferred_model,
                    "text": text
                }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            last_error = f"HTTP {e.code}: {err_body}"
            # Si es cuota (429) y estamos probando argon, continuamos al fallback
            if e.code in (404, 429, 503):
                continue
            return {"success": False, "error": last_error, "model": model_name}
        except Exception as e:
            return {"success": False, "error": str(e), "model": model_name}

    return {"success": False, "error": last_error, "model": preferred_model}


def ask_synrag_architect(query: str, project: str = "") -> str:
    """Pregunta de arquitectura respondida por Gemini con el codigo local relevante (requiere GEMINI_API_KEY)."""
    import indexer

    # 1. Recuperar contexto quirúrgico local
    results = indexer.search_desktop(query, limit=5, project=project or None)
    if not results:
        return f"[SynRAG Architect] No se encontraron componentes locales para '{query}'."

    context_lines = []
    for r in results:
        p = r.get("rel_path", "?")
        l_start = r.get("line", "?")
        l_end = r.get("end_line", l_start)
        sym = r.get("symbol_name") or r.get("title") or "bloque"
        kind = r.get("symbol_kind", "code")
        code = r.get("content", "").strip()[:600]
        context_lines.append(f"--- Archivo: {p} (L{l_start}-L{l_end}) [{kind}: {sym}] ---\n{code}\n")

    context_str = "\n".join(context_lines)

    prompt = f"""Eres el Coprocesador Arquitectónico de SynRAG (SyntaxRAG).
Tu objetivo es resolver la siguiente consulta técnica del usuario basándote en los fragmentos sintácticos reales extraídos del código local:

CONSULTA:
{query}

FRAGMENTOS AST RECUPERADOS (0 tokens de lectura innecesaria):
{context_str}

INSTRUCCIONES:
1. Explica directamente la arquitectura o flujo involucrado basándote en el código.
2. Identifica puntos de extensión o refactorización recomendados.
3. Señala posibles riesgos o dependencias críticas.
4. Sé conciso y directo, sin introducciones vacías ni emojis.
"""

    res = call_gemini_model(prompt)
    if not res.get("success"):
        return f"[SynRAG Architect Error] {res.get('error')}"

    notice = ""
    if res.get("fallback_used"):
        notice = "\n[Nota: Gemini 4 Argon requiere facturación en Google AI Studio (limit: 0 en Free Tier). Respuesta generada con Gemini 2.5 Flash]\n"

    return f"================================================================================\n" \
           f"        SYNTAX RAG ARCHITECT ({res.get('model').upper()})\n" \
           f"================================================================================\n" \
           f"{notice}\n{res.get('text')}\n" \
           f"================================================================================"


def explain_blast_radius(symbol: str, project: str = "", archivo: str = "") -> str:
    """Gemini explica el riesgo de cambiar un simbolo segun sus dependientes (requiere GEMINI_API_KEY); archivo= elige la definicion."""
    import indexer
    import impact
    from tools import inspect_tools

    # Dependientes de UNA definicion (imports resueltos), no de todo lo que se llame igual
    definidor, otras = "", 0
    try:
        datos = indexer.consumidores(symbol, project or None)
    except Exception:
        datos = None
    defs = (datos or {}).get("definiciones") or {}
    if archivo:
        defs = {d: v for d, v in defs.items() if d.endswith(archivo.lstrip("./"))}
    if defs:
        definidor, dependents = max(defs.items(), key=lambda kv: len(kv[1]))
        otras = len(defs) - 1
    else:
        dependents = impact.get_dependents(indexer.get_db(), symbol, project or None)

    if not dependents:
        return f"[SynRAG Grafo] El símbolo '{symbol}' no tiene dependientes registrados en el grafo local."

    corta = lambda r: os.path.relpath(r, Path.home()) if r.startswith(str(Path.home())) else r  # noqa: E731
    dependents = sorted(corta(d) for d in dependents)
    contract_info = inspect_tools.get_symbol_contract(definidor or symbol, symbol)
    donde = f"DEFINIDO EN: {corta(definidor)}" + (
        f" (hay {otras} definicion(es) mas con el mismo nombre; esta es la de mas dependientes)" if otras else ""
    ) + "\n" if definidor else ""

    prompt = f"""Eres el Analista de Riesgo e Impacto de SynRAG.
Analiza el impacto de modificar el siguiente símbolo en el proyecto:

SÍMBOLO: {symbol}
{donde}CONTRATO / DEFINICIÓN:
{contract_info}

ARCHIVOS QUE DEPENDEN DIRECTAMENTE DE ESTE SÍMBOLO ({len(dependents)} archivos):
{json.dumps(dependents[:15], indent=2)}

INSTRUCCIONES:
1. Clasifica el nivel de riesgo de refactorización (BAJO, MEDIO, CRÍTICO).
2. Enumera los posibles fallos colaterales (cambios en firmas, tipos, parámetros opcionales).
3. Entrega una lista de recomendaciones antes de aplicar cambios.
4. Cero emojis, sé conciso y técnico.
"""

    res = call_gemini_model(prompt)
    if not res.get("success"):
        return f"[SynRAG Blast Radius Error] {res.get('error')}"

    notice = ""
    if res.get("fallback_used"):
        notice = "\n[Nota: Respuesta generada con Gemini 2.5 Flash por cuota Free Tier de Argon]\n"

    return f"================================================================================\n" \
           f"        SYNTAX RAG - ANÁLISIS DE RIESGO: {symbol.upper()}\n" \
           f"================================================================================\n" \
           f"{notice}\n{res.get('text')}\n" \
           f"================================================================================"
