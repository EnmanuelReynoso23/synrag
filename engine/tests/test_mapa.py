import pytest
from pathlib import Path

import indexer
import mapa
import empaquetar
import server_mcp


def test_pagerank_mas_importado(casa, helper_crear_proyecto):
    """PageRank pone primero al archivo más importado."""
    archivos = {
        "core.py": (
            "def servicio_central():\n"
            "    return 'central'\n"
        ),
        "modulo_a.py": (
            "from core import servicio_central\n\n"
            "def tarea_a():\n"
            "    return servicio_central()\n"
        ),
        "modulo_b.py": (
            "from core import servicio_central\n\n"
            "def tarea_b():\n"
            "    return servicio_central()\n"
        ),
        "modulo_c.py": (
            "from core import servicio_central\n\n"
            "def tarea_c():\n"
            "    return servicio_central()\n"
        ),
    }
    helper_crear_proyecto(casa, "test-pr", archivos)
    indexer.index_desktop()

    res = mapa.mapa_del_repo("test-pr")
    assert "core.py" in res
    assert "modulo_a.py" in res

    pos_core = res.find("core.py")
    pos_a = res.find("modulo_a.py")
    pos_b = res.find("modulo_b.py")
    pos_c = res.find("modulo_c.py")

    assert pos_core < pos_a
    assert pos_core < pos_b
    assert pos_core < pos_c


def test_foco_cambia_orden(casa, helper_crear_proyecto):
    """El parámetro foco altera el ranking hacia el archivo o símbolo enfocado."""
    archivos = {
        "core.py": (
            "def servicio_central():\n"
            "    return 'central'\n"
        ),
        "modulo_a.py": (
            "from core import servicio_central\n\n"
            "def tarea_a():\n"
            "    return servicio_central()\n"
        ),
        "modulo_b.py": (
            "from core import servicio_central\n\n"
            "def tarea_b():\n"
            "    return servicio_central()\n"
        ),
        "modulo_c.py": (
            "from core import servicio_central\n\n"
            "def tarea_c():\n"
            "    return servicio_central()\n"
        ),
    }
    helper_crear_proyecto(casa, "test-foco", archivos)
    indexer.index_desktop()

    # Sin foco, core.py es el primero
    res_sin = mapa.mapa_del_repo("test-foco")
    assert res_sin.find("core.py") < res_sin.find("modulo_c.py")

    # Con foco en modulo_c.py, modulo_c.py pasa al primer puesto
    res_con_foco = mapa.mapa_del_repo("test-foco", foco="modulo_c.py")
    assert res_con_foco.find("modulo_c.py") < res_con_foco.find("core.py")

    # Con foco en un símbolo de modulo_b.py
    res_foco_sym = mapa.mapa_del_repo("test-foco", foco="tarea_b")
    assert res_foco_sym.find("modulo_b.py") < res_foco_sym.find("modulo_a.py")


def test_presupuesto_se_respeta(casa, helper_crear_proyecto):
    """El presupuesto en tokens se respeta estrictamente."""
    archivos = {
        "mod1.py": "\n".join(f"def func_{i}():\n    return {i}\n" for i in range(15)),
        "mod2.py": "\n".join(f"def otra_{i}():\n    return {i}\n" for i in range(15)),
        "mod3.py": "\n".join(f"def extra_{i}():\n    return {i}\n" for i in range(15)),
    }
    helper_crear_proyecto(casa, "test-budget", archivos)
    indexer.index_desktop()

    for limite in (30, 60, 120):
        salida = mapa.mapa_del_repo("test-budget", tokens=limite)
        toks = (len(salida) + 3) // 4
        assert toks <= limite


def test_comprimido_no_contiene_cuerpos_pero_si_firmas(casa, helper_crear_proyecto):
    """El empaquetado comprimido no incluye los cuerpos de funciones, pero sí sus firmas."""
    archivos = {
        "servicio.py": (
            "import math\n\n"
            "def calcular_impuesto(base: float, tasa: float) -> float:\n"
            "    coeficiente_privado = 1.05\n"
            "    calculo_interno = base * tasa * coeficiente_privado\n"
            "    return calculo_interno\n"
        ),
        "cliente.ts": (
            "import { api } from './api';\n\n"
            "export interface UserSession {\n"
            "    id: string;\n"
            "    token: string;\n"
            "}\n\n"
            "export function autenticar(usuario: string): boolean {\n"
            "    const comprobacion_secreta = usuario.length > 5;\n"
            "    return comprobacion_secreta;\n"
            "}\n"
        ),
    }
    proj_dir = helper_crear_proyecto(casa, "test-comp", archivos)

    texto_comp, stats_comp = empaquetar.empaquetar(proj_dir, comprimir=True)
    texto_full, stats_full = empaquetar.empaquetar(proj_dir, comprimir=False)

    # Firmas e interfaces conservadas en el comprimido
    assert "def calcular_impuesto(base: float, tasa: float) -> float:" in texto_comp
    assert "export function autenticar(usuario: string): boolean" in texto_comp
    assert "export interface UserSession {" in texto_comp
    assert "import math" in texto_comp
    assert "import { api } from './api';" in texto_comp

    # Cuerpos de funciones ausentes en el comprimido
    assert "coeficiente_privado = 1.05" not in texto_comp
    assert "calculo_interno = base * tasa" not in texto_comp
    assert "comprobacion_secreta" not in texto_comp

    # Cuerpos presentes en el empaquetado completo
    assert "coeficiente_privado = 1.05" in texto_full
    assert "comprobacion_secreta" in texto_full

    # El comprimido debe requerir menos tokens
    assert stats_comp["tokens"] < stats_full["tokens"]


def test_exclusion_env_y_secretos(casa, helper_crear_proyecto):
    """Archivos .env o sensibles son omitidos y las claves en contenido se enmascaran."""
    archivos = {
        ".env": "DB_PASSWORD=super_secret_password_123\nAPI_KEY=xyz",
        "secret.key": "mi_clave_privada_super_secreta",
        "app.py": (
            "TOKEN = 'ghp_123456789012345678901234567890'\n\n"
            "def ejecutar():\n"
            "    return True\n"
        ),
    }
    proj_dir = helper_crear_proyecto(casa, "test-sec", archivos)

    texto, stats = empaquetar.empaquetar(proj_dir, comprimir=True)

    # .env y secret.key no deben aparecer en el empaquetado
    assert ".env" not in texto
    assert "super_secret_password_123" not in texto
    assert "secret.key" not in texto
    assert "mi_clave_privada" not in texto

    # Tokens en código deben estar enmascarados
    assert "ghp_123456789012345678901234567890" not in texto
    assert "[SECRETO-OCULTO]" in texto

    # .env debe constar en archivos omitidos
    assert any(".env" in f for f in stats["archivos_omitidos"])


def test_firmas_de_archivo_unitario(tmp_path):
    """Prueba unitaria de extracción de firmas con líneas y tipos."""
    archivo = tmp_path / "modulo.py"
    archivo.write_text(
        "import os\n\n"
        "# Comentario previo\n"
        "def suma(a: int, b: int) -> int:\n"
        "    return a + b\n\n"
        "class Calculadora:\n"
        "    def multiplicar(self, x, y):\n"
        "        return x * y\n",
        encoding="utf-8",
    )

    firmas = mapa.firmas_de_archivo(archivo)
    nombres = [f[2] for f in firmas]
    assert "suma" in nombres
    assert "Calculadora" in nombres

    firma_suma = next(f for f in firmas if f[2] == "suma")
    assert firma_suma[0] == 4  # Línea 4 en 1-based
    assert firma_suma[1] == "function"
    assert "def suma(a: int, b: int) -> int:" in firma_suma[3]


def test_repo_map_mcp(casa, helper_crear_proyecto):
    """Prueba la invocación de repo_map a través del servidor MCP."""
    archivos = {
        "index.ts": "export function iniciar() { return 1; }\n",
    }
    helper_crear_proyecto(casa, "test-mcp", archivos)
    indexer.index_desktop()

    res = server_mcp.repo_map(project="test-mcp", tokens=512)
    assert "index.ts:" in res
    assert "iniciar" in res


def test_no_aristas_falsas_por_imports_externos(casa, helper_crear_proyecto):
    """Varios archivos hacen import { test } from 'vitest' y un archivo local define test();
    ese archivo NO debe quedar primero ni recibir aristas de vitest.
    """
    archivos = {
        "auth.ts": (
            "export function login(usuario: string) {\n"
            "    return 'token';\n"
            "}\n"
        ),
        "test-report.ts": (
            "export function test(nombre: string, fn: any) {\n"
            "    return fn();\n"
            "}\n"
        ),
        "test_a.ts": (
            "import { test } from 'vitest';\n"
            "import { login } from './auth';\n\n"
            "test('prueba a', () => login('a'));\n"
        ),
        "test_b.ts": (
            "import { test } from 'vitest';\n"
            "import { login } from './auth';\n\n"
            "test('prueba b', () => login('b'));\n"
        ),
        "test_c.ts": (
            "import { test } from 'vitest';\n"
            "import { login } from './auth';\n\n"
            "test('prueba c', () => login('c'));\n"
        ),
    }
    helper_crear_proyecto(casa, "test-vitest", archivos)
    indexer.index_desktop()

    res = mapa.mapa_del_repo("test-vitest")
    assert "Raiz:" in res
    assert "auth.ts" in res
    assert "test-report.ts" in res

    pos_auth = res.find("auth.ts")
    pos_report = res.find("test-report.ts")

    # auth.ts es importado localmente por 3 archivos; test-report.ts por ninguno (vitest es externo)
    assert pos_auth < pos_report

    # test-report.ts no debe quedar en primer lugar
    lineas = [l.strip() for l in res.splitlines() if l.strip() and not l.startswith("Raiz:")]
    assert not lineas[0].startswith("test-report.ts")

