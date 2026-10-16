#!/usr/bin/env python3
"""
Hook UserPromptSubmit de Claude Code: pista de SYNRAG solo para mensajes de codigo.

Lee el mensaje del usuario por stdin (JSON con la clave `prompt`). Si parece trabajo
de codigo (archivos con extension, funciones, clases, errores, trazas, pruebas, imports,
codigo entre comillas invertidas, identificadores camelCase/snake_case...) devuelve una
pista corta como contexto adicional. Si no, no imprime nada.

Nunca debe romper el envio del mensaje: ante cualquier error sale con codigo 0 y sin salida.
No importa lancedb ni el resto del motor: solo biblioteca estandar.
"""

import json
import re
import sys
import unicodedata

PISTA = (
    "SYNRAG: usa search_desktop (servidor desktop-lancedb) antes de grep o de leer "
    "archivos enteros; antes de cambiar un simbolo usa get_impact_radius."
)

EXTENSIONES = (
    "py|pyi|js|jsx|mjs|cjs|ts|tsx|vue|svelte|rs|go|java|kt|kts|cs|cpp|cc|c|h|hpp|rb|php|"
    "swift|dart|scala|sh|bash|fish|ps1|sql|sqlite|json|yaml|yml|toml|ini|cfg|conf|env|lock|"
    "xml|html|htm|css|scss|md|txt|csv|log|tf|proto|graphql|lua|hs|ex|exs"
)

_PATRONES = [
    # Codigo entre comillas invertidas
    re.compile(r"`[^`\n]+`"),
    # Archivo con extension conocida (main.py, package.json, src/app.tsx)
    re.compile(r"(?<![\w.])[\w\-/\\]+\.(?:" + EXTENSIONES + r")(?!\w)"),
    # Trazas y errores
    re.compile(
        r"traceback|stack trace|excepcion|exception|segmentation fault|null pointer|"
        r"undefined is not|\b(?:typeerror|syntaxerror|referenceerror|nameerror|valueerror|"
        r"keyerror|attributeerror|importerror|modulenotfounderror|indexerror|assertionerror)\b|"
        r"\bfile \"|\bline \d+\b|\bat \S+\.\w+\(|\b(?:http|status|error|code|codigo)\s*:?\s*[45]\d\d\b"
    ),
    # Palabras de trabajo de codigo, en espanol e ingles (ya sin acentos y en minusculas)
    re.compile(
        r"\b(?:funcion|funciones|function|functions|metodo|metodos|method|methods|class|classes|"
        r"variable|variables|modulo|modulos|module|modules|import|imports|importar|"
        r"prueba|pruebas|test|tests|testing|bug|bugs|error|errores|refactor|refactorizar|"
        r"refactoriza|codigo|code|script|scripts|api|endpoint|endpoints|repo|repositorio|"
        r"commit|commits|merge|pull request|branch|compilar|compile|build|debug|debugear|"
        r"depurar|sql|query|componente|component|linter|pr)\b"
    ),
    # Llamadas tipo sumar(2, 3) o main()
    re.compile(r"\b[A-Za-z_]\w*\([^)\n]{0,60}\)"),
    # Operadores de codigo
    re.compile(r"=>|->|::|!=|==|&&|\|\|"),
    # Identificadores snake_case y dunder
    re.compile(r"\b[a-z]+(?:_[a-z0-9]+)+\b|__\w+__"),
    # Identificadores camelCase (calcularTotal, mensajeAmigable)
    re.compile(r"\b[a-z]+[A-Z][A-Za-z0-9]*\b"),
    # "clase Usuario" (con mayuscula): distinto de "la clase de manana"
    re.compile(r"\bclase\s+[A-Z_]\w*"),
]


def _normalizar(texto: str) -> str:
    """Minusculas y sin acentos, para que 'función' y 'funcion' coincidan."""
    descompuesto = unicodedata.normalize("NFD", texto)
    sin_acentos = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return sin_acentos.lower()


def es_codigo(texto: str) -> bool:
    """True si el mensaje parece trabajo de codigo."""
    if not texto or not texto.strip():
        return False
    normal = _normalizar(texto)
    # Los patrones de mayusculas (camelCase, "clase Usuario") necesitan el texto original.
    for patron in _PATRONES:
        if patron.search(normal) or patron.search(texto):
            return True
    return False


def procesar(prompt) -> dict:
    """Devuelve la respuesta del hook, o {} si no hay que agregar pista."""
    if not isinstance(prompt, str) or not es_codigo(prompt):
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": PISTA,
        }
    }


def main() -> None:
    try:
        datos = json.loads(sys.stdin.read())
        respuesta = procesar(datos.get("prompt") if isinstance(datos, dict) else None)
        if respuesta:
            sys.stdout.write(json.dumps(respuesta, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    except Exception:  # noqa: BLE001 - el hook nunca debe bloquear el mensaje
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
