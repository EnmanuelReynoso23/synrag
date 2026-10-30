"""
Micro-AST Compressor para SyntaxRAG
Inventado por Shannon (Agente 03) y Turing (Agente 01).
Comprime bloques de codigo en representaciones sintacticas ultradensas
que preservan firmas, control de flujo y retornos mientras recortan ruido de tokens.
"""

import re
from typing import Dict, Any, List, Optional


class MicroASTCompressor:
    """Comprime codigo fuente en un formato Micro-AST compacto para LLMs."""

    def __init__(self):
        self.re_decorador = re.compile(r"^\s*@[\w\(\)]+")
        self.re_comentarios = re.compile(r"^\s*(//|#|/\*|\*)")
        self.re_logs = re.compile(r"^\s*(console\.log|logger\.|print\(|logging\.)")
        self.re_espacios = re.compile(r"\s+")

    def comprimir_funcion(self, codigo: str) -> str:
        """Extrae el esqueleto estructural minimo de una funcion o metodo."""
        if not codigo or not codigo.strip():
            return ""

        lineas = codigo.splitlines()
        salida: List[str] = []
        en_docstring = False

        for l in lineas:
            strip_l = l.strip()
            if not strip_l:
                continue

            # Detectar y saltar docstrings multilineas
            if '"""' in strip_l or "'''" in strip_l or "/*" in strip_l:
                if strip_l.count('"""') == 1 or strip_l.count("'''") == 1 or "/*" in strip_l:
                    en_docstring = not en_docstring
                continue
            if en_docstring:
                if '"""' in strip_l or "'''" in strip_l or "*/" in strip_l:
                    en_docstring = False
                continue

            # Omitir comentarios de una linea y logs de depuracion
            if self.re_comentarios.match(strip_l) or self.re_logs.match(strip_l):
                continue

            # Conservar firmas, estructuras de control, retornos y asignaciones de estado
            if any(strip_l.startswith(k) for k in (
                "def ", "async def ", "class ", "function ", "export ", "public ", "private ",
                "if ", "elif ", "else:", "for ", "while ", "try:", "except ", "catch ", "finally:",
                "return ", "yield ", "throw ", "raise ", "interface ", "type "
            )) or "=" in strip_l and any(k in strip_l for k in ("self.", "this.", "const ", "let ")):
                # Normalizar multiples espacios para ahorrar tokens
                linea_limpia = self.re_espacios.sub(" ", strip_l)
                salida.append(linea_limpia)

        if not salida:
            return codigo.strip()[:140]

        return "\n".join(salida)

    def calcular_ratio_compresion(self, original: str, comprimido: str) -> float:
        """Calcula el porcentaje de reduccion en caracteres."""
        if not original:
            return 0.0
        return max(0.0, 100.0 * (1.0 - (len(comprimido) / len(original))))


def comprimir_a_micro_ast(codigo: str) -> Dict[str, Any]:
    """Punto de entrada rapido para el compresor Micro-AST."""
    compresor = MicroASTCompressor()
    resultado = compresor.comprimir_funcion(codigo)
    ratio = compresor.calcular_ratio_compresion(codigo, resultado)
    return {
        "micro_ast": resultado,
        "caracteres_original": len(codigo),
        "caracteres_comprimido": len(resultado),
        "ahorro_estimado_pct": round(ratio, 2)
    }
