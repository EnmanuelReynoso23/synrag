import importlib
import sys
from pathlib import Path
from typing import Dict

import pytest

MOTOR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MOTOR))


@pytest.fixture
def casa(tmp_path, monkeypatch):
    """HOME temporal. Devuelve la ruta; los modulos del motor quedan recargados con ese HOME."""
    monkeypatch.setenv("HOME", str(tmp_path))
    for nombre in ("indexer", "cache", "impact", "telemetry", "installer"):
        if nombre in sys.modules:
            importlib.reload(sys.modules[nombre])
        else:
            importlib.import_module(nombre)
    return tmp_path


def crear_proyecto(casa: Path, nombre: str, archivos: Dict[str, str]) -> Path:
    """Helper que escribe archivos bajo casa / 'Proyectos' / nombre."""
    proj_dir = casa / "Proyectos" / nombre
    for rel_path, contenido in archivos.items():
        destino = proj_dir / rel_path
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")
    return proj_dir


@pytest.fixture
def helper_crear_proyecto():
    """Fixture que expone crear_proyecto a los tests."""
    return crear_proyecto
