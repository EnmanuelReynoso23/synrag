"""Lo que hace que SynRAG cueste menos que grep: definicion exacta primero, bloque entero y
nombres compuestos encontrables con palabras sueltas."""
import pytest

import chunker
import indexer
from conftest import crear_proyecto


def test_mencionar_la_cabecera_pem_no_borra_el_resto(monkeypatch):
    texto = (
        "/** Acepta la privada en PEM (`-----BEGIN PRIVATE KEY-----`) o en base64. */\n"
        "export function cargarLlave(texto) {}\n"
        "export function construirPayload() {}\n"
    )
    for rust in {False, indexer.HAVE_RUST_CRAWLER}:
        monkeypatch.setattr(indexer, "HAVE_RUST_CRAWLER", rust)
        salida = indexer.ocultar_secretos(texto)
        assert "construirPayload" in salida, f"rust={rust}"
        assert indexer.OCULTO not in salida


def test_llave_pem_real_y_clave_de_google_se_ocultan(monkeypatch):
    llave = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASC\nBKcwggSjAgEAAoIBAQC7\n-----END PRIVATE KEY-----\nresto"
    google = "const k = 'AQ.Ab8CLAVEFALSADEPRUEBA0000000000000000000000000000'"
    for rust in {False, indexer.HAVE_RUST_CRAWLER}:
        monkeypatch.setattr(indexer, "HAVE_RUST_CRAWLER", rust)
        oculto = indexer.ocultar_secretos(llave)
        assert "MIIEvQ" not in oculto and oculto.endswith("resto")
        assert "AQ.Ab8" not in indexer.ocultar_secretos(google)


@pytest.mark.parametrize("codigo, esperado", [
    ("/**\n * Comentario\n */\nexport function soportadas(): boolean {", ("soportadas", "function")),
    ("// el type of algo\nexport const f = async (x) => x", ("f", "function")),
    ("@dataclass\nclass Punto:", ("Punto", "class")),
    ("export const useSesion = () => {}", ("useSesion", "hook")),
    ("export const LIMITE = 100;", ("LIMITE", "variable")),
    ("export interface Props {", ("Props", "interface")),
])
def test_nombre_del_simbolo_ignora_comentarios_previos(codigo, esperado):
    assert chunker.extract_symbol_and_kind(codigo, "export_statement") == esperado


def test_definicion_exacta_primero_y_entera(casa):
    cuerpo = "\n".join(f"  const paso{i} = calcular({i}) + ajustar({i}, 'texto de relleno');" for i in range(80))
    archivos = {
        # muchas menciones: BM25 lo pondria por delante de la definicion
        "uso.ts": "import { objetivoFinal } from './def';\n" + "objetivoFinal();\n" * 40,
        "def.ts": f"/** Hace el trabajo. */\nexport function objetivoFinal() {{\n{cuerpo}\n  return 'ULTIMA_LINEA';\n}}\n",
    }
    crear_proyecto(casa, "demo", archivos)
    indexer.index_desktop()

    res = indexer.search_desktop("objetivoFinal", project="demo", use_rerank=False)
    assert res[0]["rel_path"].endswith("def.ts")
    assert res[0]["exacto"] is True
    assert res[0]["line"] == 1 and "ULTIMA_LINEA" in res[0]["content"]  # trozos unidos


def test_palabras_sueltas_encuentran_nombres_compuestos(casa):
    crear_proyecto(casa, "demo", {
        "lecturas.ts": "export function esSinCupo(error: unknown): boolean {\n  return String(error).includes('429');\n}\n",
        "otro.ts": "export function sumar(a: number, b: number) {\n  return a + b;\n}\n",
    })
    indexer.index_desktop()
    res = indexer.search_desktop("sin cupo", project="demo", use_rerank=False)
    assert res and res[0]["rel_path"].endswith("lecturas.ts")
