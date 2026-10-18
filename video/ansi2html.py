"""Convierte salidas reales del CLI (capturadas con color) en lineas HTML para el video.

    python video/ansi2html.py <carpeta_con_.ansi> '[["miembro", 8, 52], ["impact", 0, 20]]' > video/terminal.json

Cada .ansi es la salida tal cual de un comando SYNRAG con FORCE_COLOR=1; aqui solo se recorta y se pasa a <span>.
"""
import html
import json
import sys
from pathlib import Path

from rich.style import Style
from rich.text import Text


def _css(st: Style) -> str:
    css = []
    if st.color:
        tr = st.color.triplet or st.color.get_truecolor()
        css.append(f"color:rgb({tr.red},{tr.green},{tr.blue})")
    if st.bold:
        css.append("font-weight:700")
    if st.dim:
        css.append("opacity:.6")
    if st.italic:
        css.append("font-style:italic")
    return ";".join(css)


def linea_html(t: Text) -> str:
    plain = t.plain
    estilos = [Style()] * len(plain)
    for sp in t.spans:
        st = sp.style if isinstance(sp.style, Style) else Style.parse(str(sp.style))
        for i in range(sp.start, min(sp.end, len(plain))):
            estilos[i] = estilos[i] + st
    out, i = [], 0
    while i < len(plain):
        j = i
        while j < len(plain) and estilos[j] == estilos[i]:
            j += 1
        txt, css = html.escape(plain[i:j]), _css(estilos[i])
        out.append(f'<span style="{css}">{txt}</span>' if css else txt)
        i = j
    return "".join(out)


def main() -> None:
    res = {}
    for nombre, desde, hasta in json.loads(sys.argv[2]):
        lineas = Path(sys.argv[1], nombre + ".ansi").read_text(encoding="utf-8").split("\n")[desde:hasta]
        res[nombre] = [linea_html(Text.from_ansi(l)) for l in lineas]
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
