"""La CI instala lo que dice scripts/ci/requirements.txt y los usuarios lo que dice install.sh:
si las listas se separan, la CI pasaria en verde con una instalacion real rota."""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def test_dependencias_de_install_sh_y_de_la_ci_coinciden():
    m = re.search(r"^DEPENDENCIAS=\(([^)]*)\)", (RAIZ / "install.sh").read_text(), re.M)
    instalador = set(m.group(1).split())
    ci = {l.strip() for l in (RAIZ / "scripts/ci/requirements.txt").read_text().splitlines()
          if l.strip() and not l.startswith("#")}
    assert instalador == ci - {"pytest"}


def test_install_sh_copia_todos_los_modulos_del_motor():
    """Si se agrega un modulo al motor y no a ENGINE_FILES, en un equipo nuevo no arranca."""
    m = re.search(r"^ENGINE_FILES=\(([^)]*)\)", (RAIZ / "install.sh").read_text(), re.M | re.S)
    copiados = set(m.group(1).split())
    motor = {p.name for p in (RAIZ / "engine").glob("*.py")} - {"benchmark_real_savings.py"}
    herramientas = {f"tools/{p.name}" for p in (RAIZ / "engine/tools").glob("*.py")}
    faltan = (motor | herramientas) - copiados
    assert not faltan, f"faltan en ENGINE_FILES de install.sh: {sorted(faltan)}"
