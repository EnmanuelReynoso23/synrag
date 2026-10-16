# synrag_crawler

Módulo nativo en Rust con bindings PyO3 para SynRAG.

## Propósito
Acelera el escaneo masivo de monorepos y codebases (>100.000 archivos) mediante:
- Recorrido paralelo de directorios con `ignore` (motor de ripgrep), respetando `.gitignore` y podando `node_modules`, `target`, `.git` y worktrees sin entrar en ellos.
- Lectura en paralelo concurrente sin contención de GIL utilizando el pool de hilos de `rayon`.
- Anonimización ultrarrápida de secretos en memoria usando expresiones regulares compiladas en Rust (`regex::RegexSet` y `LazyLock`).
- Detección precisa de archivos sensibles y validación instantánea de tipos de archivo admitidos.

## Compilación e Instalación

### Con Maturin:
```bash
# Compilar e instalar directamente en el entorno virtual
VIRTUAL_ENV=$HOME/.local/opt/lancedb-hub/.venv maturin develop --release
```

### Pruebas unitarias:
```bash
pytest engine/tests/test_rust_crawler.py
```
