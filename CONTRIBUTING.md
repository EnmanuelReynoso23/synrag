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

## Reportar problemas

Abre una incidencia con: sistema operativo, versión de Python, qué IA usas, qué esperabas y qué pasó. Para vulnerabilidades, lee `SECURITY.md`.
