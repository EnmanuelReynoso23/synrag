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

- **Tree-sitter AST Chunker:** Trocea por funciones, hooks, clases (las grandes, método por método), tipos y declaraciones completas (TypeScript, TSX/JSX, JavaScript y Python). La documentación (Markdown, MDX, reStructuredText, AsciiDoc) se trocea en fragmentos de ~200 tokens con su ruta de títulos; SQL por sentencias.
- **Localizar antes que leer:** Con un nombre de símbolo devuelve su definición primero y entera; el resto de resultados ocupa una línea (`ruta:líneas tipo nombre | firma`). Los nombres compuestos se indexan también partidos (`esSinCupo` se encuentra con "sin cupo"). Candidatos por BM25 (Tantivy sobre LanceDB) reordenados en CPU con TinyBERT (FlashRank). Mediana medida: 61-89 ms por consulta nueva.
- **Grafo de Impacto de Dependencias:** Guarda en una tabla de LanceDB qué archivos importan cada símbolo, para avisar a los agentes de qué depende de lo que van a editar. Detecta imports; no sigue llamadas dinámicas.
- **Caché de consultas repetidas:** Si repites la misma consulta (sin distinguir mayúsculas ni espacios) se responde desde una tabla local (~3-4 ms). No es una caché semántica y se vacía al reindexar. La búsqueda no usa APIs de pago; los resultados igualmente cuestan tokens al modelo que los lee.
- **Observador de cambios (opcional):** Un servicio de systemd de usuario (`lancedb-watcher.service`) reindexa solo el archivo que guardas: ~8 ms por archivo pequeño (mediana medida), tras 0,6 s de espera para agrupar guardados. Usa unos 250-300 MB de RAM; compacta la base cada cierto número de cambios y detecta carpetas nuevas sin reiniciar.


## Cuánto ahorra (medido, no prometido)

Cada cifra sale de un guion de `benchmarks/` que cualquiera puede repetir en su equipo sobre repositorios públicos (Flask y Hono). La comparación honesta no es contra leer archivos enteros, sino contra lo que hace un agente sin SynRAG: `grep` y leer el tramo.

| Qué | Resultado | Guion |
|---|---|---|
| Sistema completo con un agente real (Gemini con function calling): 10 tareas de varios pasos (localizar, entender, planear un cambio, correr pruebas) x 2 rondas, contando todos los tokens que cobra la API | **-29,2 % tokens** (191.567 frente a 270.717), calidad 87 % -> 90 %; gana en 7 de 10 (planear un cambio -81 %, pruebas con salida larga -38 %, entender -20 %); pierde en tareas muy cortas (+124 %: las definiciones de las herramientas pesan más que la tarea) y en 2 de 3 de Flask (+10 % y +30 %). Varianza alta: ronda 1 -15 %, ronda 2 -48 % | `benchmarks/agente/completo.py` |
| Agente real, solo ubicar: 16 preguntas x 2 rondas, con y sin SynRAG | **-11,5 % tokens**, 16/16 aciertos en ambos modos; gana en 7 de 16 (hasta -79 % en lenguaje natural en un repo grande; pierde con nombres exactos en un repo chico, donde `grep` devuelve una línea) | `benchmarks/agente/agente.py` |
| Encontrar y leer una función por su nombre, frente a grep + leer el tramo | Flask -27 a -30 %, Hono -45 %; la definición sale primera en el 92-100 % | `benchmarks/ahorro.py --indexar` |
| Lo mismo con preguntas en lenguaje natural | Flask -31 % | `benchmarks/ahorro.py --naturales` |
| Documentación (fragmentos de ~200 tokens) | -22 % frente a grep, -91 % frente al archivo entero | `benchmarks/docs.py` |
| Empaquetar un repo solo con firmas (como Repomix `--compress`) | Flask -76 %, Hono -84 % frente al repo completo | `benchmarks/mapa.py` |
| Salidas largas de terminal (filtro opcional) | -87 a -99 % conservando todas las líneas de error; la salida completa queda en un archivo | `benchmarks/filtro.py` |
| Costo fijo: definiciones de las 28 herramientas MCP | ~2.000 tokens por sesión | `scripts/ci/mcp_tools_list.py` |

Lo que más pesa en una sesión real no es ninguna herramienta: es la longitud de la sesión, porque cada turno reenvía todo el historial. `context_budget_alert` y `session_handoff` ayudan a cortar a tiempo. Detalle y límites de cada cifra: `CLAIMS.md`.

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

Cualquier agente conectado a SyntaxRAG tiene 28 herramientas (las dos de Gemini solo aparecen si configuras tu propia `GEMINI_API_KEY`; sin ella el motor no usa la red):

- **Buscar y orientarse:** `search_desktop` (con `tipo="docs"` o `"codigo"`), `get_file_outline` (incluye los métodos de objetos y clases grandes), `repo_map` (firmas de los archivos más importantes por PageRank, dentro de un presupuesto de tokens), `list_projects`, `reindex_desktop`.
- **Antes de editar:** `get_impact_radius`, `find_related_tests`, `find_callers_exact`, `get_symbol_contract`, `extract_type_definition`, `get_import_graph`, `check_breaking_callsites`, `check_circular_imports`, `verify_dependency_exists` (entiende monorepos y workspaces), `find_code_duplicates`.
- **Editar:** `patch_function_body`, `add_import_clean`, `rename_symbol_scoped`, `remove_unused_imports` (conservan saltos de línea y sangría; si el nombre del archivo es ambiguo no tocan nada; respaldo fuera del repo).
- **Ejecutar con salida corta:** `run_test_isolated`, `lint_summary`, `run_typecheck_focus`, `tail_clean_logs`.
- **Sesión:** `session_handoff`, `context_budget_alert`, `git_staged_overview`, `extract_todo_status`, `get_savings_report`.
- **Opcional con Gemini:** `ask_synrag_architect`, `explain_blast_radius`.

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

# Qué carpetas se indexan (por defecto se detectan ~/Projects, ~/code, ~/dev...; se guardan en
# ~/.config/synrag/carpetas.txt o en la variable SYNRAG_CARPETAS)
SYNRAG carpetas
SYNRAG agregar ~/trabajo [nombre-del-proyecto]
SYNRAG quitar ~/trabajo

# Reindexar todo con Tree-sitter AST
SYNRAG index

# Mapa del repo: firmas de los archivos más importantes (PageRank) en un presupuesto de tokens
SYNRAG mapa mi-proyecto --tokens 1024 [--foco archivo.ts,funcion]

# Empaquetar un repo solo con firmas, tipos e imports (para pegarlo en un chat web)
SYNRAG empaquetar ~/mi-proyecto --salida paquete.md [--sin-comprimir]

# Opcionales (se quitan con "SYNRAG uninstall --<lo-mismo>"):
SYNRAG configure --filtro-largas   # recorta salidas largas de la terminal en Claude Code (hook PostToolUse)
SYNRAG configure --filtro          # resume salidas de instalar/compilar/probar
SYNRAG configure --conciso         # respuestas cortas (basado en Caveman de Julius Brussee, Apache-2.0)

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
