"""Que SynRAG sirva en cualquier equipo: sin carpetas del autor escritas en el codigo."""
import importlib

import indexer
from conftest import crear_proyecto


def _recargar():
    importlib.reload(indexer)
    return indexer


def test_usuario_nuevo_sin_configuracion_detecta_sus_carpetas(casa, monkeypatch):
    monkeypatch.delenv("SYNRAG_CARPETAS", raising=False)
    (casa / "Projects" / "tienda").mkdir(parents=True)
    (casa / "Projects" / "tienda" / "carrito.py").write_text("def total_del_carrito(items):\n    return sum(items)\n")
    (casa / ".claude" / "projects" / "-home-ana" / "memory").mkdir(parents=True)
    ix = _recargar()
    assert (casa / "Projects", None) in ix.cargar_carpetas()
    assert (casa / ".claude" / "projects" / "-home-ana" / "memory", "memoria-claude") in ix.cargar_carpetas()
    assert not any("AsistoYA" in str(r) for r, _ in ix.cargar_carpetas())

    ix.index_desktop()
    res = ix.search_desktop("total_del_carrito", use_rerank=False)
    assert res and res[0]["project"] == "tienda"



def test_misma_carpeta_con_otro_nombre_se_indexa_una_vez(casa, monkeypatch):
    """En macOS ~/Proyectos y ~/proyectos son la misma carpeta (disco sin mayusculas); aqui con un enlace."""
    monkeypatch.delenv("SYNRAG_CARPETAS", raising=False)
    (casa / "Proyectos" / "tienda").mkdir(parents=True)
    (casa / "proyectos").symlink_to(casa / "Proyectos")
    ix = _recargar()
    assert [r for r, _ in ix.cargar_carpetas()] == [casa / "Proyectos"]


def test_archivo_de_carpetas_y_variable_de_entorno(casa, monkeypatch):
    monkeypatch.delenv("SYNRAG_CARPETAS", raising=False)
    otra = casa / "trabajo"
    otra.mkdir()
    cfg = casa / ".config" / "synrag" / "carpetas.txt"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("# comentario\n~/trabajo = cliente-x\n\n~/trabajo\n")
    ix = _recargar()
    assert ix.cargar_carpetas() == [(otra, "cliente-x")]  # repetidas se ignoran

    monkeypatch.setenv("SYNRAG_CARPETAS", f"{casa}/a:{casa}/b=bee")
    ix = _recargar()
    assert ix.cargar_carpetas() == [(casa / "a", None), (casa / "b", "bee")]
