from pathlib import Path
import indexer


def test_ocultar_secretos_patrones_conocidos():
    # Bloque PEM de clave privada
    pem_bloque = (
        "header\n"
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA0Y1o2X3k9mQ1\n"
        "-----END RSA PRIVATE KEY-----\n"
        "footer"
    )
    redactado_pem = indexer.ocultar_secretos(pem_bloque)
    assert "-----BEGIN RSA PRIVATE KEY-----" not in redactado_pem
    assert indexer.OCULTO in redactado_pem

    # Token GitHub (ghp_ + 36)
    ghp_token = "token = 'ghp_123456789012345678901234567890123456';"
    assert indexer.ocultar_secretos(ghp_token) == f"token = '{indexer.OCULTO}';"

    # Clave AWS (AKIA + 16)
    aws_key = "const aws = 'AKIAIOSFODNN7EXAMPLE';"
    assert indexer.ocultar_secretos(aws_key) == f"const aws = '{indexer.OCULTO}';"

    # Token OpenAI (sk- + 24)
    sk_token = "api_secret = 'sk-123456789012345678901234';"
    assert indexer.ocultar_secretos(sk_token) == f"api_secret = '{indexer.OCULTO}';"

    # Asignación genérica de clave
    asignacion = 'api_key = "abcdefghijklmnop1234"'
    redactado_asig = indexer.ocultar_secretos(asignacion)
    assert "abcdefghijklmnop1234" not in redactado_asig
    assert indexer.OCULTO in redactado_asig


def test_ocultar_secretos_texto_normal_sin_cambios():
    normal = (
        "function calcularSuma(a: number, b: number): number {\n"
        "    const total = a + b;\n"
        "    return total;\n"
        "}\n"
    )
    assert indexer.ocultar_secretos(normal) == normal


def test_ocultar_secretos_falso_positivo_referencia_env():
    # Falso positivo conocido de RE_ASIGNACION: referencias a variables de entorno
    # como `process.env.API_KEY` tienen mas de 16 caracteres y se redactan hoy.
    codigo_env = 'const api_key = process.env.API_KEY;'
    redactado = indexer.ocultar_secretos(codigo_env)
    assert "process.env.API_KEY" not in redactado
    assert indexer.OCULTO in redactado


def test_should_index_archivos_excluidos_y_admitidos(tmp_path):
    base = tmp_path / "proyecto"
    base.mkdir()

    # Archivos excluidos por nombre o extension sensible
    archivos_excluidos = [
        base / ".env",
        base / "credentials.json",
        base / "id_rsa",
        base / "x.pem",
        base / "package-lock.json",
        base / "imagen.png",
    ]

    for p in archivos_excluidos:
        p.write_text("datos de prueba")
        assert indexer.should_index(p, base) is False, f"{p.name} debio ser excluido"

    # Carpeta oculta
    dir_oculto = base / ".config"
    dir_oculto.mkdir()
    f_oculto = dir_oculto / "app.ts"
    f_oculto.write_text("console.log(1);")
    assert indexer.should_index(f_oculto, base) is False

    # node_modules
    nm = base / "node_modules" / "paquete"
    nm.mkdir(parents=True)
    f_nm = nm / "index.ts"
    f_nm.write_text("export const x = 1;")
    assert indexer.should_index(f_nm, base) is False

    # Archivo mayor a 250 KB
    f_grande = base / "archivo_grande.ts"
    f_grande.write_bytes(b"a" * (251 * 1024))
    assert indexer.should_index(f_grande, base) is False

    # Archivo de codigo valido permitido
    src = base / "src"
    src.mkdir()
    f_valido = src / "app.ts"
    f_valido.write_text("export function iniciar(): void { console.log('ok'); }")
    assert indexer.should_index(f_valido, base) is True
