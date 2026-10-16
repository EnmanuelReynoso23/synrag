# Contribuir a SyntaxRAG (SYNRAG)

Gracias por querer ayudar. Esto es lo que necesitas para empezar y las reglas que mantienen el proyecto creíble.

## Preparar el entorno

**Web** (React 19 + Vite + Tailwind 4):

```bash
pnpm install
pnpm dev        # http://localhost:5173
pnpm lint
pnpm build      # tsc -b && vite build
```

**Motor** (Python 3.10 o superior): `./install.sh` crea el entorno aislado en `~/.local/opt/lancedb-hub` con las dependencias `lancedb rich tree-sitter tree-sitter-language-pack flashrank mcp watchdog pandas`. Para trabajar sobre el repositorio, usa el Python de ese entorno y los archivos de `engine/`.

## Reglas

1. **Ninguna cifra sin evidencia.** Todo número que aparezca en el README o en la web (latencias, conteos, porcentajes, ahorros) tiene que estar en `CLAIMS.md` con su fecha, su método y el comando que lo reproduce. Si no se puede medir, no se afirma. Las demostraciones con datos de ejemplo se rotulan como simulación.
2. **Mide antes de comparar.** Si comparas con otra herramienta, cita la fuente y la fecha, y di qué mediste tú y qué dicen ellos.
3. **Compatibilidad.** Una IA solo figura como compatible si alguien la probó de verdad. Si pruebas una de las que aún no están probadas (Gemini CLI, Codex CLI, Cursor, Windsurf, Cline/Roo Code, Zed, macOS, WSL), abre una incidencia con el resultado.
4. **Commits y PRs pequeños**, con el mensaje en español, sin emojis, explicando el porqué.
5. **Privacidad.** No subas rutas personales, nombres de proyectos privados ni consultas reales. Los ejemplos usan datos ficticios.

## Medir

Los guiones de `benchmarks/` miden contra tu propio índice o en un equipo temporal. Mira `benchmarks/README.md` para usarlos y para entender sus límites.

## Integración continua y verificación local

El repositorio cuenta con integración continua en GitHub Actions (`.github/workflows/pruebas.yml`):

- **Job `pruebas`**: se ejecuta en `ubuntu-latest` y `macos-latest` con Python 3.10 y 3.12. Instala las dependencias del motor (`DEPENDENCIAS` de `install.sh`) más `pytest` (sin compilar Rust) y ejecuta la suite con `cd engine && python -m pytest -q`. Usa caché de pip.
- **Job `instalacion-limpia`**: se ejecuta en `ubuntu-latest` y `macos-latest`. Corre `bash install.sh` en un `$HOME` temporal limpio, crea un proyecto de prueba en `$HOME/Projects`, indexa con `SYNRAG index`, realiza una búsqueda CLI comprobando que localice el símbolo, y levanta el servidor MCP por stdio mediante `scripts/ci/mcp_tools_list.py` para verificar que responda a `tools/list` y que ninguna herramienta incluya `outputSchema` (requisito estricto para no inflar el consumo de tokens en cada sesión).

Para validar tus cambios localmente antes de abrir un PR:

```bash
# 1. Pruebas unitarias del motor
cd engine && ~/.local/opt/lancedb-hub/.venv/bin/python -m pytest -q

# 2. Prueba completa de instalacion limpia y servidor MCP
bash scripts/ci/test_clean_install.sh

# O manualmente en un entorno sin variables heredadas:
TMP_HOME=$(mktemp -d)
env -i HOME="$TMP_HOME" PATH=/usr/bin:/bin bash install.sh
```

## Reportar problemas

Abre una incidencia con: sistema operativo, versión de Python, qué IA usas, qué esperabas y qué pasó. Para vulnerabilidades, lee `SECURITY.md`.
