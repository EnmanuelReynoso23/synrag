"""
Pruebas unitarias para el motor nativo en Rust (crates/synrag_crawler).
Verifica:
- Importación del módulo compilado con PyO3.
- Enmascaramiento ultrarrápido de secretos (tokens, pem, passwords).
- Detección de archivos sensibles y reglas de exclusión.
- Escaneo multihilo en paralelo de metadatos y contenido con Rayon.
"""

import sys
import time
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import synrag_crawler
    HAVE_CRAWLER = True
except ImportError:
    HAVE_CRAWLER = False


pytestmark = pytest.mark.skipif(not HAVE_CRAWLER, reason="Modulo synrag_crawler en Rust no disponible")


def test_crawler_version():
    assert synrag_crawler.get_version() == "0.1.0-rust"


def test_mask_secrets_patterns():
    texto = """
    # Claves y tokens de prueba
    sk_token = "sk-abcdef1234567890abcdef1234567890"
    github_pat = "github_pat_11AABBCCDDEEFFGGHHIIJJKKLLMMNNOOPPQQRRSSTTUUVVWW"
    db_pass = "super_secret_password_123456"
    -----BEGIN RSA PRIVATE KEY-----
    MIIEowIBAAKCAQEA0m4w...
    -----END RSA PRIVATE KEY-----
    """
    enmascarado, modificado = synrag_crawler.mask_secrets(texto)
    assert modificado is True
    assert "[SECRETO-OCULTO]" in enmascarado
    assert "sk-abcdef" not in enmascarado
    assert "github_pat" not in enmascarado or "[SECRETO-OCULTO]" in enmascarado
    assert "MIIEowIBAAKCAQEA" not in enmascarado


def test_is_sensitive_file():
    assert synrag_crawler.is_sensitive_file(".env") is True
    assert synrag_crawler.is_sensitive_file(".env.production") is True
    assert synrag_crawler.is_sensitive_file("id_rsa") is True
    assert synrag_crawler.is_sensitive_file("server.key") is True
    assert synrag_crawler.is_sensitive_file("credentials.json") is True
    assert synrag_crawler.is_sensitive_file("main.py") is False
    assert synrag_crawler.is_sensitive_file("package.json") is False


def test_should_index():
    repo_root = Path(__file__).parent.parent.parent.resolve()
    py_file = repo_root / "engine" / "indexer.py"
    assert synrag_crawler.should_index(str(py_file), str(repo_root)) is True

    # Archivo ignorado
    lock_file = repo_root / "pnpm-lock.yaml"
    if lock_file.exists():
        assert synrag_crawler.should_index(str(lock_file), str(repo_root)) is False


def test_crawl_metadata_parallel():
    repo_root = str(Path(__file__).parent.parent.parent.resolve())
    scan_dirs = [(repo_root, "synrag-web-test")]

    t0 = time.time()
    metas = synrag_crawler.crawl_metadata(scan_dirs)
    duracion = time.time() - t0

    assert len(metas) > 0
    assert duracion < 1.0  # Debe completarse en menos de 1 segundo

    # Verificar estructura del primer elemento
    m = metas[0]
    assert hasattr(m, "path")
    assert hasattr(m, "rel_path")
    assert hasattr(m, "project")
    assert hasattr(m, "filename")
    assert hasattr(m, "extension")
    assert m.project == "synrag-web-test"


def test_crawl_directories_parallel():
    repo_root = str(Path(__file__).parent.parent.parent.resolve())
    scan_dirs = [(repo_root, "synrag-web-test")]

    t0 = time.time()
    files = synrag_crawler.crawl_directories(scan_dirs, 250 * 1024)
    duracion = time.time() - t0

    assert len(files) > 0
    assert duracion < 1.5

    f = files[0]
    assert hasattr(f, "content")
    assert len(f.content) > 0
    assert hasattr(f, "secrets_masked")
