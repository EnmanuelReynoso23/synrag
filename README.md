# SyntaxRAG (SYNRAG)

**AST-Native MCP Engine · Búsqueda de código local · Dependency Impact Graph**

Motor local de búsqueda de código para agentes de IA, por el protocolo MCP. Probado con Claude Code y Google Antigravity; el instalador también lo configura para Gemini CLI, Codex CLI, Cursor, Windsurf, Cline/Roo Code y Zed (sin probar).

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![LanceDB](https://img.shields.io/badge/LanceDB-Vector%20Store-00E5FF.svg)](https://lancedb.com/)
[![Tree--sitter](https://img.shields.io/badge/Tree--sitter-AST%20Parser-green.svg)](https://tree-sitter.github.io/)
[![FlashRank](https://img.shields.io/badge/FlashRank-ONNX%20Reranker-orange.svg)](https://github.com/PrithivirajDamodaran/FlashRank)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)
[![Tailwind](https://img.shields.io/badge/Tailwind%20CSS-v4-38B2AC.svg)](https://tailwindcss.com/)
[![Protocol](https://img.shields.io/badge/MCP-Protocol%202.0-purple.svg)](https://modelcontextprotocol.io/)

---

## Que es SyntaxRAG (SYNRAG)

Un RAG de ventanas fijas para código corta los archivos en bloques de, por ejemplo, 500 tokens que pueden partir funciones a la mitad y no entienden jerarquías de tipos, y los agentes terminan leyendo archivos completos para orientarse. Otras herramientas modernas también trocean por AST; SyntaxRAG es una opción local y abierta, y publica cómo se mide cada cifra (ver `CLAIMS.md`).

**SyntaxRAG (SYNRAG)** resuelve este problema analizando el árbol sintáctico abstracto (AST) del código en tu máquina local:

- **Tree-sitter AST Chunker:** Trocea por funciones, hooks, clases, tipos y declaraciones completas (TypeScript, TSX/JSX, JavaScript y Python; Markdown se trocea por secciones y SQL por sentencias); los bloques de más de 2.400 caracteres se dividen.
- **Búsqueda por palabras con reordenado neuronal:** Recupera candidatos con BM25 (Tantivy sobre LanceDB) y los reordena en CPU con un modelo TinyBERT local (FlashRank). Si la consulta no comparte palabras con el código, no lo encuentra. Mediana medida: ~90 ms por consulta nueva.
- **Grafo de Impacto de Dependencias:** Guarda en una tabla de LanceDB qué archivos importan cada símbolo, para avisar a los agentes de qué depende de lo que van a editar. Detecta imports; no sigue llamadas dinámicas.
- **Caché de consultas repetidas:** Si repites la misma consulta (sin distinguir mayúsculas ni espacios) se responde desde una tabla local (~9 ms). No es una caché semántica y se vacía al reindexar. La búsqueda no usa APIs de pago; los resultados igualmente cuestan tokens al modelo que los lee.
- **Observador de cambios (opcional):** Un servicio de systemd de usuario (`lancedb-watcher.service`) reindexa solo el archivo que guardas: ~8 ms por archivo pequeño (mediana medida), tras 0,6 s de espera para agrupar guardados. Usa 300 MB o más de RAM.

---

## Instalacion Universal en 1 Linea

Probado en **Linux (CachyOS)**. Debería funcionar en otras distribuciones, macOS y Windows con WSL, pero no están probados:

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
| **Google Antigravity** | `~/.gemini/config/mcp_config.json` (si ya existe `~/.gemini/antigravity/mcp_config.json`, también lo mantiene al día) | `~/.gemini/GEMINI.md` |
| **Gemini CLI** | `~/.gemini/settings.json` | `~/.gemini/GEMINI.md` |
| **Codex CLI** | `~/.codex/config.toml` | `~/.codex/AGENTS.md` |
| **Cursor** | `~/.cursor/mcp.json` | (se añade a mano en Settings > Rules) |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` | `~/.codeium/windsurf/memories/global_rules.md` |
| **Cline / Roo Code** | `cline_mcp_settings.json` de VS Code | n/a |
| **Zed** | `~/.config/zed/settings.json` (solo si es JSON puro; con comentarios muestra qué añadir) | n/a |

Garantías del instalador: no crea la carpeta de una IA que no está instalada, hace una copia `.bak-AAAAMMDD-HHMMSS` antes de modificar un archivo existente, nunca sobrescribe un JSON que no pueda leer y es idempotente (ejecutarlo dos veces no duplica nada).

Estado de compatibilidad (6-oct-2026): **probado en la práctica con Claude Code y Google Antigravity.** Gemini CLI, Codex CLI, Cursor, Windsurf, Cline/Roo Code y Zed se configuran según su documentación, pero no se han probado. Si usas alguna, abre una incidencia con el resultado.

---

## Desinstalar

```bash
SYNRAG uninstall            # quita la entrada MCP y el bloque de instrucciones de cada IA y los comandos
rm -rf ~/.local/opt/lancedb-hub   # opcional: borra tambien el motor y su indice
```

`SYNRAG uninstall --dry-run` muestra que quitaria sin escribir nada. Solo elimina lo que el instalador anadio.

---

---

## Herramientas MCP para Agentes de IA

Cualquier agente conectado a SyntaxRAG tiene acceso a 7 herramientas nativas:

1. `search_desktop(query, limit, project)`: Búsqueda por palabras (BM25) con reordenado neuronal en CPU y advertencia de impacto.
2. `get_file_outline(file_path)`: Esquema sintáctico de un archivo (firmas y rangos de línea) sin volcar el código fuente. Suele pesar mucho menos que el archivo completo; el ahorro real depende de la tarea.
3. `get_impact_radius(symbol)`: Cálculo del blast radius preventivo antes de editar una función.
4. `find_related_tests(file_or_symbol)`: Mapeo de archivos `.test.ts`, `.spec.ts` asociados para correr solo las pruebas necesarias.
5. `get_savings_report()`: Registro de uso del buscador: tokens devueltos y una referencia contrafactual (tamaño completo de los archivos devueltos). La referencia no es un ahorro medido; ver `CLAIMS.md`.
6. `list_projects()`: Resumen de proyectos indexados y recuento de fragmentos.
7. `reindex_desktop()`: Re-indexación completa del árbol AST y grafo de impacto.

---

## Comandos del CLI (`SYNRAG`)

SyntaxRAG cuenta con un binario autónomo para terminal:

```bash
# Panel de control y estado operativo
SYNRAG

# Búsqueda por palabras con reordenado neuronal
SYNRAG "asistenciaServicio"

# Búsqueda filtrada por proyecto
SYNRAG --project asistoya-web "useEstudiantes"

# Esquema sintáctico de un archivo (firmas y rangos de línea)
SYNRAG outline apps/web/src/modulos/asistencia/asistencia.servicio.ts

# Radio de impacto y archivos dependientes
SYNRAG impact asistenciaServicio

# Localizar tests asociados
SYNRAG tests asistenciaServicio

# Estadísticas del índice y registro de búsquedas
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

### Telemetría local y bases de datos existentes

SyntaxRAG registra el uso local en SQLite (`~/.local/share/lancedb-hub/telemetry.db`). Los datos separan las consultas medidas en tiempo real de filas que no corresponden a mediciones reales (columna `origen = 'medido'`).

Si vienes de una base antigua con datos sembrados o de pruebas, puedes marcarlos para que no se sumen a las métricas del informe:

```sql
-- hacer antes una copia de seguridad de telemetry.db
UPDATE telemetry_events SET origen = 'sembrado'
WHERE tokens_retrieved = 631 AND tokens_original_file = 2500 AND results_count = 3 AND latency_ms = 6.2;
```

---

## Web Dashboard & Simulador Interactivo

El repositorio incluye la aplicación web oficial (`synrag-web`), diseñada bajo el tema Dark Mode (`#0D1117`) y Neón Cyan (`#00E5FF`):

- **Simulador AST en Vivo:** Visualización en 3 modos: Código fuente, Árbol jerárquico Tree-sitter y Grafo de Dependencias SVG interactivo.
- **Calculadora de Escenarios de Tokens:** Deslizadores para estimar un escenario hipotético con supuestos que tú ajustas; no es una medición ni una promesa de ahorro.
- **Simulador de Terminal CLI:** Simulación en el navegador, con datos ficticios, de la salida de los comandos de SYNRAG.
- **Métricas medidas por el autor (6-oct-2026, ~75 proyectos indexados):** ~96 mil fragmentos AST, ~90 ms por consulta nueva (mediana en reposo; p90 ~110 ms), ~9 ms si se repite la consulta y 23.704 relaciones en el grafo de impacto.

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
│   ├── chunker.py                # Tree-sitter AST Chunker (TS, TSX, JS y Python; también Markdown y SQL)
│   ├── ranker.py                 # FlashRank ONNX Cross-Encoder Reranker
│   ├── impact.py                 # Grafo de dependientes en LanceDB
│   ├── cache.py                  # Caché de consultas repetidas (LanceDB)
│   ├── telemetry.py              # Telemetría persistente en SQLite
│   ├── server_mcp.py             # Servidor MCP 2.0 (FastMCP / MCPServer)
│   ├── indexer.py                # Indexador incremental de repositorios
│   ├── installer.py              # Auto-configurador multi-IA multiplataforma
│   ├── cli.py                    # Interfaz rica de terminal (Rich + Dark Mode)
│   └── watcher.py                # Observador opcional de cambios (Watchdog)
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
