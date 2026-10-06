# Afirmaciones verificables

Cada cifra y cada afirmación que aparece en el README o en la web tiene aquí su fecha, su método y el comando que la reproduce. Lo que no se pudo medir figura como "no afirmado". Última revisión: 6-oct-2026.

Equipo de las mediciones: CachyOS (Linux), 12 núcleos, solo CPU; índice de ~76 proyectos, 96.318 fragmentos y 23.721 relaciones. Las cifras de latencia dependen de tu equipo y de la carga que tenga: ejecuta los guiones en el tuyo.

## Medido

| # | Afirmación | Resultado (6-oct-2026) | Cómo reproducirlo |
|---|---|---|---|
| 1 | Consulta nueva, de punta a punta por MCP, equipo en reposo | Mediana ~90 ms (medianas de 67 a 91 ms en 6 semillas; p90 de 105 a 121 ms). Consultas de 2 a 4 palabras, 4 de cada 5 con filtro de proyecto | `python benchmarks/latencia.py --modo mcp --semilla N` |
| 2 | Primera consulta tras arrancar el servidor MCP | 118 a 201 ms; el servidor tarda ~1,4 s en arrancar hasta `initialize` | igual que la fila 1 |
| 3 | Consulta repetida (misma consulta sin distinguir mayúsculas ni espacios) | Mediana 8,3 a 8,9 ms (p90 ~10 ms) | igual que la fila 1 |
| 4 | Solo el motor, sin MCP | Nueva: medianas de 61 a 91 ms (5 semillas). Repetida: 6,1 a 7,8 ms | `python benchmarks/latencia.py --modo motor --semilla N` |
| 5 | Con la CPU saturada (12 procesos en 12 núcleos) | Nueva: mediana ~192 ms (p90 241 ms) frente a ~94 ms sin carga; repetida: ~16 ms. Modo motor, proyecto de 23 mil fragmentos, 3 a 6 palabras | `python benchmarks/latencia.py --modo motor --proyecto <el_mayor> --palabras 3-6 --semilla 7`, sin carga y con 12 procesos ocupando la CPU a la vez |
| 6 | Uso real dentro de Claude Code (con otras tareas en marcha) | 355 a 707 ms en 5 de 6 búsquedas y 52 ms en una. **No se ha explicado la diferencia con la fila 1** | columna `latency_ms` de `~/.local/share/lancedb-hub/telemetry.db` |
| 7 | Reindexar un archivo pequeño (`index_single_file`) | Mediana 8,0 a 8,6 ms (p90 ~9,3 ms; 3 corridas de 15 pruebas), más 0,6 s de espera con la que el observador agrupa guardados | `python benchmarks/reindex_archivo.py` |
| 8 | Memoria del observador opcional | 257 MB tras 1 h 54 min y 320 MB tras 2 h 15 min; **crece con el tiempo**. CPU media ~0,3 % | `ps -o rss=,etime= -p $(systemctl --user show lancedb-watcher.service -p MainPID --value)` |
| 9 | Tamaño del índice del autor | ~76 proyectos, 96.318 fragmentos, 23.721 relaciones, 62 MB en disco. Cambia con cada reindexado | `python benchmarks/conteos.py` |

## Verificado en el código

| # | Afirmación | Dónde |
|---|---|---|
| 10 | Los candidatos se recuperan por palabras (BM25, Tantivy FTS sobre LanceDB) y se reordenan con FlashRank `ms-marco-TinyBERT-L-2-v2` | `engine/indexer.py` (`search_desktop`), `engine/ranker.py` |
| 11 | La caché solo acierta con la misma consulta normalizada (minúsculas y espacios), con 4 horas de vigencia, y se vacía al reindexar. No es una caché semántica | `engine/cache.py`, `engine/indexer.py` |
| 12 | El troceo es por AST para TypeScript, TSX/JSX, JavaScript y Python; Markdown se trocea por secciones y SQL por sentencias; los bloques de más de 2.400 caracteres se dividen | `engine/chunker.py` (`LANG_MAP`, `MAX_CHUNK_CHARS`) |
| 13 | El grafo de impacto guarda qué archivos importan cada símbolo en una tabla de LanceDB; no usa NetworkX | `engine/impact.py` |
| 14 | Se excluyen carpetas ocultas, archivos de más de 250 KB y archivos de credenciales, y se redactan patrones de secretos | `engine/indexer.py` |
| 15 | El motor no hace llamadas de red | `grep -rniE "requests\|urllib\|httpx\|socket" engine/*.py` no devuelve nada |
| 16 | Siete herramientas MCP: `search_desktop`, `get_file_outline`, `get_impact_radius`, `find_related_tests`, `get_savings_report`, `list_projects`, `reindex_desktop` | `engine/server_mcp.py` |

## Probado

| # | Afirmación | Cómo |
|---|---|---|
| 17 | Con Claude Code y Antigravity el MCP queda cargado | En el equipo del autor hay un proceso `server_mcp.py` hijo de cada IA; Antigravity lee `~/.gemini/config/mcp_config.json` (la ruta está en su binario y en el del CLI `agy`) |
| 18 | El instalador funciona en un equipo limpio, es idempotente, conserva servidores ajenos y se desinstala | Probado con un `HOME` falso el 6-oct-2026: instalación, segunda pasada, ruta anterior de Antigravity y `--uninstall` |

## No afirmado

- **Ahorro de tokens o de dinero.** No hay una medición pública. `get_savings_report` muestra una referencia contrafactual (tamaño completo de los archivos devueltos), no un ahorro medido, y la web ya no promete ninguno. Los resultados de una búsqueda igualmente cuestan tokens al modelo que los lee. Una prueba pareada reproducible está pendiente.
- **Calidad de la búsqueda** (qué porcentaje de las veces el resultado correcto está entre los primeros). No medida.
- **Rust y Go.** El chunker trae sus gramáticas y devuelve fragmentos, pero sin nombre de símbolo (probado el 6-oct-2026) y `ALLOWED_EXTENSIONS` de `engine/indexer.py` no incluye `.rs` ni `.go`, así que esos archivos no se indexan. No están soportados.
- **Compatibilidad** con Gemini CLI, Codex CLI, Cursor, Windsurf, Cline/Roo Code, Zed, macOS y Windows con WSL. Se configuran según su documentación, pero no se han probado.
- **Las demos de la web** (explorador, terminal, observador) son simulaciones con datos de ejemplo.

## Cómo añadir o cambiar una afirmación

1. Mide con un comando que otra persona pueda ejecutar (o cita el archivo y la línea del código).
2. Añade una fila aquí con la fecha, el resultado y el comando.
3. Solo entonces escribe la cifra en el README o en la web.
4. Si una cifra deja de cumplirse, cámbiala o quítala el mismo día.
