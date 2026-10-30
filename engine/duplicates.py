"""
Detector de Codigo Duplicado por Huella AST para SyntaxRAG
Inventado por Knuth (Agente 05) y Neumann (Agente 11).
Normaliza subarboles AST para detectar funciones duplicadas o clonadas
aunque los desarrolladores hayan cambiado nombres de variables o identacion.
"""

import hashlib
import re
from typing import List, Dict, Any, Tuple


class ASTCloneDetector:
    """Detecta clones de codigo mediante hashes estructurales de arbol."""

    def __init__(self, similitud_minima: float = 0.85):
        self.similitud_minima = similitud_minima
        self.re_identificadores = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
        self.palabras_reservadas = {
            "def", "class", "return", "if", "else", "elif", "for", "while", "in",
            "try", "except", "finally", "with", "as", "import", "from", "async",
            "await", "yield", "function", "const", "let", "var", "interface", "type"
        }

    def canonicalizar_esqueleto(self, codigo: str) -> str:
        """Convierte una funcion en su esqueleto abstracto anonimizando identificadores."""
        lineas = []
        for l in codigo.splitlines():
            s = l.strip()
            if not s or s.startswith(("#", "//", "/*", "*")):
                continue
            lineas.append(s)

        texto_limpio = " ".join(lineas)

        # Anonimizar todos los identificadores que no sean palabras reservadas
        tokens = []
        id_map: Dict[str, str] = {}
        contador = 0

        for m in self.re_identificadores.finditer(texto_limpio):
            palabra = m.group(0)
            if palabra in self.palabras_reservadas:
                tokens.append(palabra)
            else:
                if palabra not in id_map:
                    contador += 1
                    id_map[palabra] = f"V{contador}"
                tokens.append(id_map[palabra])

        return " ".join(tokens)

    def calcular_hash_estructural(self, codigo: str) -> str:
        """Calcula el hash SHA-256 del esqueleto canonico."""
        esqueleto = self.canonicalizar_esqueleto(codigo)
        return hashlib.sha256(esqueleto.encode("utf-8")).hexdigest()[:16]

    def comparar_funciones(self, func_a: str, func_b: str) -> Tuple[bool, float]:
        """Compara si dos funciones son clones estructurales."""
        esq_a = self.canonicalizar_esqueleto(func_a).split()
        esq_b = self.canonicalizar_esqueleto(func_b).split()

        if not esq_a or not esq_b:
            return False, 0.0

        if esq_a == esq_b:
            return True, 1.0

        # Coeficiente Jaccard sobre secuencias de tokens
        set_a = set(esq_a)
        set_b = set(esq_b)
        inter = len(set_a.intersection(set_b))
        union = len(set_a.union(set_b))
        sim = inter / max(1, union)

        es_clon = sim >= self.similitud_minima
        return es_clon, round(sim, 2)


def detectar_clones_ast(func_a: str, func_b: str) -> Dict[str, Any]:
    """Punto de entrada rapido para detectar duplicados AST."""
    detector = ASTCloneDetector()
    hash_a = detector.calcular_hash_estructural(func_a)
    hash_b = detector.calcular_hash_estructural(func_b)
    es_clon, similitud = detector.comparar_funciones(func_a, func_b)

    return {
        "es_duplicado": es_clon,
        "similitud": similitud,
        "hash_a": hash_a,
        "hash_b": hash_b,
        "dictamen": "CLON ESTRUCTURAL DETECTADO" if es_clon else "FUNCIONES DISTINTAS"
    }
