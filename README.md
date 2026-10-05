# SyntaxRAG (SYNRAG)

**AST-Native MCP Engine · Zero-Token Cache · Dependency Impact Graph**

Motor de inteligencia de código local de alto rendimiento y arquitectura semántica universal para cualquier agente de IA (Claude Code, Google Antigravity, Cursor, Windsurf, Cline, VS Code, Zed).

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![LanceDB](https://img.shields.io/badge/LanceDB-Vector%20Store-00E5FF.svg)](https://lancedb.com/)
[![Tree--sitter](https://img.shields.io/badge/Tree--sitter-AST%20Parser-green.svg)](https://tree-sitter.github.io/)
[![FlashRank](https://img.shields.io/badge/FlashRank-ONNX%20Reranker-orange.svg)](https://github.com/PrithivirajDamodaran/FlashRank)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)
[![Tailwind](https://img.shields.io/badge/Tailwind%20CSS-v4-38B2AC.svg)](https://tailwindcss.com/)
[![Protocol](https://img.shields.io/badge/MCP-Protocol%202.0-purple.svg)](https://modelcontextprotocol.io/)

---

## Que es SyntaxRAG (SYNRAG)

El RAG tradicional (Retrieval-Augmented Generation) para código está roto: corta archivos en bloques ciegos de 500 tokens que parten funciones a la mitad, no entienden jerarquías de tipos y obligan a los modelos de lenguaje a gastar millones de tokens leyendo archivos completos solo para orientarse.

**SyntaxRAG (SYNRAG)** resuelve este problema analizando el árbol sintáctico abstracto (AST) del código en tu máquina local:

- **Tree-sitter AST Chunker:** Trocea quirúrgicamente por funciones, hooks, clases, tipos y declaraciones completas.
- **FlashRank ONNX Reranker:** Re-ordena los resultados semánticos en CPU en menos de 3 ms con modelos neurales TinyBERT locales.
- **Grafo de Impacto de Dependencias (NetworkX):** Mapea imports y exports bidireccionales para advertir a los agentes si una edición rompería otros módulos.
- **Zero-Token Cache:** Tabla de caché de microsegundos (<1 ms) con 0 consumo de tokens y $0 costo en APIs.
- **Hot-Reload Reactivo (~18 ms):** Demonio systemd/launchd que actualiza LanceDB en memoria cada vez que guardas con Ctrl+S en tu editor.

---

## Instalacion Universal en 1 Linea

Funciona en **Linux (CachyOS, Arch, Ubuntu, Debian, Fedora), macOS y Windows con WSL**:

```bash
curl -sSL https://raw.githubusercontent.com/EnmanuelReynoso23/synrag/main/install.sh | bash
```

O desde el repositorio clonado:

```bash
git clone https://github.com/EnmanuelReynoso23/synrag.git
cd synrag
./install.sh
```

El instalador copia o descarga el motor, crea un entorno virtual aislado en CPU, instala los lanzadores `SYNRAG` / `synrag` en `~/.local/bin` y configura **solo las IAs que de verdad tengas instaladas**. Si algo falla, se detiene y dice qué falló. Para ver qué haría sin escribir nada: `./install.sh --dry-run` (o `SYNRAG configure --dry-run`).

---

## Auto-Configuracion Multi-IA

Al instalarse o al ejecutar `SYNRAG configure`, SyntaxRAG hace dos cosas en cada IA detectada: registra el servidor MCP `desktop-lancedb` y añade a sus instrucciones globales un bloque corto (entre las marcas `<!-- SYNRAG:BEGIN -->` y `<!-- SYNRAG:END -->`) que le indica usar `search_desktop` antes de listar carpetas o leer archivos enteros. Sin ese bloque la IA ve la herramienta pero casi nunca la elige.

| Herramienta / Agente | MCP (servidor) | Instrucciones globales |
|---|---|---|
| **Claude Code** | `~/.claude.json` | `~/.claude/CLAUDE.md` |
| **Google Antigravity** | `~/.gemini/antigravity/mcp_config.json` | `~/.gemini/GEMINI.md` |
| **Gemini CLI** | `~/.gemini/settings.json` | `~/.gemini/GEMINI.md` |
| **Codex CLI** | `~/.codex/config.toml` | `~/.codex/AGENTS.md` |
| **Cursor** | `~/.cursor/mcp.json` | (se añade a mano en Settings > Rules) |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` | `~/.codeium/windsurf/memories/global_rules.md` |
| **Cline / Roo Code** | `cline_mcp_settings.json` de VS Code | n/a |
| **Zed** | `~/.config/zed/settings.json` (solo si es JSON puro; con comentarios muestra qué añadir) | n/a |

Garantías del instalador: no crea la carpeta de una IA que no está instalada, hace una copia `.bak-AAAAMMDD-HHMMSS` antes de modificar un archivo existente, nunca sobrescribe un JSON que no pueda leer y es idempotente (ejecutarlo dos veces no duplica nada).

---|---|
| **Claude Code** | `~/.claude.json` y `~/.claude/settings.json` |
| **Google Antigravity** | `~/.gemini/antigravity/mcp/desktop-lancedb` |
| **Cursor IDE** | `~/.cursor/mcp.json` / `globalStorage` |
| **Windsurf / Codeium** | `~/.codeium/windsurf/mcp_config.json` |
| **VS Code / Cline / Roo Code** | `cline_mcp_settings.json` / `~/.vscode/mcp.json` |
| **Zed Editor** | `~/.config/zed/settings.json` |

---

## Herramientas MCP para Agentes de IA

Cualquier agente conectado a SyntaxRAG tiene acceso a 7 herramientas nativas:

1. `search_desktop(query, limit, project)`: Búsqueda semántica AST con FlashRank neural en CPU y advertencia de impacto.
2. `get_file_outline(file_path)`: Esquema sintáctico de un archivo en ~50 tokens (firmas y rangos de línea sin volcar el código fuente). Ahorro de 98% en contexto.
3. `get_impact_radius(symbol)`: Cálculo del blast radius preventivo antes de editar una función.
4. `find_related_tests(file_or_symbol)`: Mapeo de archivos `.test.ts`, `.spec.ts` asociados para correr solo las pruebas necesarias.
5. `get_savings_report()`: Reporte persistente de ahorro acumulado en tokens y dólares.
6. `list_projects()`: Resumen de proyectos indexados y recuento de fragmentos.
7. `reindex_desktop()`: Re-indexación completa del árbol AST y grafo de impacto.

---

## Comandos del CLI (`SYNRAG`)

SyntaxRAG cuenta con un binario autónomo para terminal:

```bash
# Panel de control y estado operativo
SYNRAG

# Búsqueda semántica AST instantánea
SYNRAG "asistenciaServicio"

# Búsqueda filtrada por proyecto
SYNRAG --project asistoya-web "useEstudiantes"

# Esquema sintáctico de un archivo en ~50 tokens
SYNRAG outline apps/web/src/modulos/asistencia/asistencia.servicio.ts

# Radio de impacto y archivos dependientes
SYNRAG impact asistenciaServicio

# Localizar tests asociados
SYNRAG tests asistenciaServicio

# Métricas persistentes de ahorro histórico y tokens
SYNRAG stats

# Re-escanear y auto-configurar todas las IAs instaladas
SYNRAG configure

# Reindexar todo con Tree-sitter AST
SYNRAG index

# Ver log en vivo del demonio reactivo (Ctrl+S)
SYNRAG watch

# Lanzar agentes directamente con el entorno MCP listo
SYNRAG claude
SYNRAG agy
```

---

## Web Dashboard & Simulador Interactivo

El repositorio incluye la aplicación web oficial (`synrag-web`), diseñada bajo el tema Dark Mode (`#0D1117`) y Neón Cyan (`#00E5FF`):

- **Simulador AST en Vivo:** Visualización en 3 modos: Código fuente, Árbol jerárquico Tree-sitter y Grafo de Dependencias SVG interactivo.
- **Calculadora de Ahorro Económico:** Deslizadores en tiempo real para proyectar ahorro en dólares y tokens según tarifas de Claude 3.5 Sonnet, GPT-4o o Gemini.
- **Simulador de Terminal CLI:** Consola interactiva en el navegador que emula comandos de terminal CachyOS en vivo.
- **Métricas Reales del Monorepo:** 95,502 fragmentos AST, <1 ms de latencia y 23,364 aristas en el grafo de impacto.

### Levantar la Web en Desarrollo

```bash
pnpm install
pnpm dev
```

La web estará disponible en `http://localhost:5173`.

---

## Estructura del Repositorio

```
synrag/
├── engine/                       # Motor Central de Inteligencia Local (Python)
│   ├── chunker.py                # Tree-sitter AST Chunker (TS, JS, PY, SQL, MD)
│   ├── ranker.py                 # FlashRank ONNX Cross-Encoder Reranker
│   ├── impact.py                 # Grafo de dependencias e impacto (NetworkX)
│   ├── cache.py                  # Zero-Token Cache (<1ms en LanceDB)
│   ├── telemetry.py              # Telemetría persistente en SQLite
│   ├── server_mcp.py             # Servidor MCP 2.0 (FastMCP / MCPServer)
│   ├── indexer.py                # Indexador incremental de repositorios
│   ├── installer.py              # Auto-configurador multi-IA multiplataforma
│   ├── cli.py                    # Interfaz rica de terminal (Rich + Dark Mode)
│   └── watcher.py                # Demonio reactivo in-memory (Watchdog)
├── src/                          # Aplicación Web y Simulador (React 19 + Tailwind 4)
│   ├── components/               # Hero, Playground, Calculator, Terminal, Metrics...
│   ├── data/mockData.ts          # Modelos de datos del ecosistema
│   └── index.css                 # Sistema de diseño (#0D1117 + Neón Cyan)
├── public/                       # Assets públicos, logos vectoriales e install.sh
├── install.sh                    # Script universal de instalación en 1 línea
└── README.md                     # Documentación oficial
```

---

## Licencia

Distribuido bajo la Licencia MIT. Desarrollado por [Enmanuel Reynoso](https://github.com/EnmanuelReynoso23).
