"""
FlashRank Cross-Encoder Reranker para LanceDB Hub
Puntúa la intención semántica del usuario frente al código en <3ms usando ONNX en CPU.
Filtra candidatos irrelevantes de BM25 y aísla los 3-5 bloques exactos.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import os

try:
    from flashrank import Ranker, RerankRequest
    FLASHRANK_AVAILABLE = True
except ImportError:
    FLASHRANK_AVAILABLE = False

_RANKER_INSTANCE = None
CACHE_DIR = Path.home() / ".cache" / "flashrank"


def get_ranker(model_name: str = "ms-marco-TinyBERT-L-2-v2") -> Optional[Any]:
    """Instancia singleton de FlashRank (carga rápida en frío)."""
    global _RANKER_INSTANCE
    if not FLASHRANK_AVAILABLE:
        return None
    if _RANKER_INSTANCE is None:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            _RANKER_INSTANCE = Ranker(model_name=model_name, cache_dir=str(CACHE_DIR))
        except Exception:
            _RANKER_INSTANCE = None
    return _RANKER_INSTANCE


def rerank_snippets(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = 4,
    score_threshold: float = 0.001
) -> List[Dict[str, Any]]:
    """
    Toma candidatos brutos de Tantivy BM25 y los reordena por relevancia semántica real.
    Devuelve hasta top_k fragmentos con su score normalizado (0.0 a 1.0).
    """
    if not candidates:
        return []
    if len(candidates) <= 1 or not FLASHRANK_AVAILABLE:
        return candidates[:top_k]

    ranker = get_ranker()
    if not ranker:
        return candidates[:top_k]

    passages = []
    for idx, c in enumerate(candidates):
        header = f"[{c.get('symbol_kind', '')} {c.get('symbol_name', '')}] " if c.get('symbol_name') else ""
        text = f"{header}{c.get('content', '')}"
        passages.append({
            "id": str(idx),
            "text": text[:1500],
            "meta": idx,
        })

    try:
        req = RerankRequest(query=query, passages=passages)
        ranked = ranker.rerank(req)
        salida = []
        for r in ranked:
            orig_idx = r["meta"]
            item = dict(candidates[orig_idx])
            item["score"] = float(r.get("score", 0.0))
            if item["score"] >= score_threshold or not salida:
                salida.append(item)
            if len(salida) >= top_k:
                break
        return salida if salida else candidates[:top_k]
    except Exception:
        return candidates[:top_k]
