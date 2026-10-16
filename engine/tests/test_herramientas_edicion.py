"""Las herramientas que modifican archivos no deben romper nada de lo que no se les pidio."""
from pathlib import Path

from tools import context_tools, patch_tools


def test_patch_conserva_crlf_sangria_anidada_y_no_deja_bak(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "estado"))
    f = tmp_path / "m.ts"
    original = "export function f(x: number) {\r\n  return x;\r\n}\r\n\r\nexport const otra = 1;\r\n"
    f.write_bytes(original.encode())
    res = patch_tools.patch_function_body(str(f), "f", "if (x > 0) {\n  return x * 2;\n}\nreturn 0;")
    assert "reemplazado" in res, res
    nuevo = f.read_bytes().decode()
    assert nuevo == ("export function f(x: number) {\r\n  if (x > 0) {\r\n    return x * 2;\r\n  }\r\n"
                     "  return 0;\r\n}\r\n\r\nexport const otra = 1;\r\n")
    assert list(tmp_path.glob("*.bak")) == []
    assert len(list((tmp_path / "estado" / "synrag" / "respaldos").iterdir())) == 1


def test_patch_python_respeta_bloques_y_lineas_en_blanco(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "estado"))
    f = tmp_path / "m.py"
    f.write_text("def a(x):\n    return x\n\n\ndef b():\n    pass\n")
    patch_tools.patch_function_body(str(f), "a", "if x:\n    return 1\nreturn 2")
    assert f.read_text() == "def a(x):\n    if x:\n        return 1\n    return 2\n\n\ndef b():\n    pass\n"


def test_patch_rechaza_funcion_de_una_linea(tmp_path):
    f = tmp_path / "m.ts"
    f.write_text("const g = () => { return 1 };\n")
    assert "misma linea" in patch_tools.patch_function_body(str(f), "g", "return 2;")
    assert f.read_text() == "const g = () => { return 1 };\n"


def test_import_nuevo_va_despues_de_un_import_de_varias_lineas(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "estado"))
    f = tmp_path / "m.ts"
    f.write_text("import {\n  a,\n  b,\n} from './x';\n\nconsole.log(a, b);\n")
    patch_tools.add_import_clean(str(f), "import { c } from './c';")
    assert f.read_text() == "import {\n  a,\n  b,\n} from './x';\nimport { c } from './c';\n\nconsole.log(a, b);\n"


def test_quita_imports_sin_usar_con_llaves_y_por_defecto(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "estado"))
    f = tmp_path / "m.tsx"
    f.write_text(
        "import React from 'react';\n"
        "import { useState, useEffect as efecto, type Props } from 'react';\n"
        "import Sobrante from './sobrante';\n"
        "import './estilos.css';\n"
        "export function C(p: Props) { const [s] = useState(0); return <div>{s}</div>; }\n"
    )
    res = patch_tools.remove_unused_imports(str(f))
    assert "Sobrante" in res and "efecto" in res and "React" in res
    assert f.read_text() == (
        "import { useState, type Props } from 'react';\n"
        "import './estilos.css';\n"
        "export function C(p: Props) { const [s] = useState(0); return <div>{s}</div>; }\n"
    )


def test_todos_solo_en_comentarios(tmp_path):
    (tmp_path / "a.ts").write_text("const x = { invalidarTodo: 1 };\n// TODO: revisar esto\n")
    res = context_tools.extract_todo_status(str(tmp_path))
    assert "revisar esto" in res and "invalidarTodo" not in res
