# Afirmaciones verificables

Cada cifra y cada afirmación que aparece en el README o en la web tiene aquí su fecha, su método y el comando que la reproduce. Lo que no se pudo medir figura como "no afirmado". Última revisión: 16-oct-2026 (las filas 1-9 son del 6-oct salvo donde se indica).

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
| 11 | La caché solo acierta con la misma consulta normalizada (minúsculas y espacios), con 4 horas de vigencia, y se vacía al reindexar. No es una caché semántica | `engine/cache.py`, `engine/indexer.py`; probado en `engine/tests/test_cache.py` |
| 12 | El troceo es por AST para TypeScript, TSX/JSX, JavaScript y Python; Markdown se trocea por secciones y SQL por sentencias; los bloques de más de 2.400 caracteres se dividen | `engine/chunker.py` (`LANG_MAP`, `MAX_CHUNK_CHARS`) |
| 13 | El grafo de impacto guarda qué archivos importan cada símbolo en una tabla de LanceDB; no usa NetworkX | `engine/impact.py` |
| 14 | Se excluyen carpetas ocultas, archivos de más de 250 KB y archivos de credenciales, y se redactan patrones de secretos | `engine/indexer.py`; probado en `engine/tests/test_secretos.py` y `engine/tests/test_busqueda.py` |
| 15 | El motor no hace llamadas de red salvo las dos herramientas opcionales de Gemini, que solo se registran si el usuario configura su propia `GEMINI_API_KEY` | `grep -rln urllib engine/` solo muestra `engine/argon.py`; `server_mcp.py` registra sus herramientas solo si `argon.disponible()` |
| 16 | 28 herramientas MCP (26 sin clave de Gemini), sin `outputSchema` y sin `title` en los parámetros | `python scripts/ci/mcp_tools_list.py` (falla si alguna trae `outputSchema`) |

## Probado

| # | Afirmación | Cómo |
|---|---|---|
| 17 | Con Claude Code y Antigravity el MCP queda cargado | En el equipo del autor hay un proceso `server_mcp.py` hijo de cada IA; Antigravity lee `~/.gemini/config/mcp_config.json` (la ruta está en su binario y en el del CLI `agy`) |
| 18 | El instalador funciona en un equipo limpio, es idempotente, conserva servidores ajenos y se desinstala | Probado con un `HOME` falso el 6-oct-2026: instalación, segunda pasada, ruta anterior de Antigravity y `--uninstall`; automatizado en `engine/tests/test_instalador.py` |

## Medido el 15-oct-2026

Equipo del autor, en reposo salvo donde se indica. Repos públicos clonados con `git clone --depth 1` (Flask `d086db8`, Hono `588ec13`); los guiones indexan solo ese repo en un índice temporal (`--indexar`). Tokens = caracteres/4 salvo en las filas 19 y 33 (contador real de la API).

| # | Afirmación | Resultado | Cómo reproducirlo |
|---|---|---|---|
| 19 | Con un agente real, SynRAG gasta menos tokens que grep + leer archivos | -11,5 % (72.533 frente a 81.996 tokens; 16 preguntas x 2 rondas, Gemini 3.5 Flash-Lite); 16/16 aciertos en ambos modos; gana en 7 de 16. Las preguntas solo piden la ubicación, el peor caso para SynRAG (entrega la definición entera) | `python benchmarks/agente/agente.py` |
| 20 | Encontrar y leer una función por su nombre cuesta menos que grep (30 líneas) + leer el tramo | Flask -27 a -30 % (3 semillas, 25 funciones), Hono -45 % (16 funciones); definición primera en 23-25 de 25 y 16 de 16 | `python benchmarks/ahorro.py --repo <repo> --indexar --semilla N` |
| 21 | Lo mismo con preguntas en lenguaje natural | Flask -31 % (12 preguntas, `benchmarks/preguntas/flask.json`); definición primera 8 de 12, en el top 5 11 de 12 | `python benchmarks/ahorro.py --repo flask --indexar --n 0 --naturales benchmarks/preguntas/flask.json` |
| 22 | Documentación en fragmentos de ~200 tokens | -22 % frente a grep + 40 líneas, -91 % frente al archivo entero (10 preguntas sobre la doc de Flask); respuesta en el top 5 10 de 10 | `python benchmarks/docs.py --repo flask` |
| 23 | Empaquetado comprimido (solo firmas, tipos e imports) | Flask 160.514 -> 38.882 tokens (-76 %), Hono 756.316 -> 118.669 (-84 %) | `python benchmarks/mapa.py --repo <repo>` |
| 24 | Filtro de salidas largas (`configure --filtro-largas`) | find: 178.449 -> 1.249 tokens; script de 5.000 líneas: 73.088 -> 1.738; journalctl: 59.248 -> 7.444; todas las líneas de error conservadas. Claude Code entrega al hook como mucho 30.000 caracteres: por encima de eso SynRAG resume ese trozo y avisa que la completa la guarda Claude Code | `python benchmarks/filtro.py` |
| 25 | Filtro de comandos ruidosos (`configure --filtro`) | 31-55 % menos en pytest, pip, npm y cargo (fixtures de 42-79 líneas) | `python benchmarks/filtro.py` |
| 26 | Costo fijo de las definiciones MCP | ~2.000 tokens (7.981 caracteres) con 28 herramientas; antes ~4.150 con 27 | `python scripts/ci/mcp_tools_list.py` |
| 27 | Latencia en el índice del autor (125.570 fragmentos) | Consulta nueva: medianas de 61 a 89 ms (3 semillas); repetida: 3,3-3,7 ms (antes 6-8 ms: ya no escribe en la caché en cada acierto) | `python benchmarks/latencia.py --modo motor --semilla N` |
| 28 | Reindexar todo | 16,7 s para 9.247 archivos y 125.570 fragmentos | `SYNRAG index` |
| 29 | Tamaño del índice tras reindexar | 132 MB (antes 350-400 MB: el grafo de impacto nunca se compactaba y acumuló 7.836 versiones) | `du -sh ~/.local/share/lancedb-hub/data` |
| 30 | Observador: versiones y hilos | 2.000 guardados sintéticos: 2.001 -> 2 archivos de versión, 23 -> 3 hilos, memoria -10 % (306 -> 275 MB); la memoria todavía crece algo | `python benchmarks/observador.py --guardados 2000` |
| 31 | Modo conciso (`configure --conciso`) | -77 % en la salida del modelo en 10 tareas; datos clave 28/30 frente a 29/30; código válido 10/10. En las sesiones del autor el texto del modelo es ~9 % del contenido | `python benchmarks/conciso.py` |
| 32 | Instalación limpia en un `HOME` vacío (Linux) | Instala, detecta `~/Projects`, indexa, busca y arranca el MCP con 28 herramientas | `bash scripts/ci/test_clean_install.sh` |
| 33 | Sistema completo (búsqueda + filtro de salidas largas + modo conciso) con un agente real en tareas de varios pasos | -29,2 % de tokens cobrados por la API (191.567 frente a 270.717; 10 tareas x 2 rondas, Gemini 3.5 Flash-Lite); calidad (hechos esperados en la respuesta) 87 % -> 90 %. Por tipo: planear un cambio -81 %, pruebas con salida larga -38 %, orientarse -29 %, localizar y entender -23 %, entender -20 %. Pierde en pruebas con salida corta (+124 %, ~900 tokens de definiciones por turno) y en 2 de 3 tareas de Flask (+10 % y +30 %; en esta la calidad baja de 100 % a 83 %). Ronda 1 -15 %, ronda 2 -48 %: con 2 rondas el margen de error es amplio. Filas crudas en `benchmarks/agente/completo-resultados-2026-10-15.json` | `python benchmarks/agente/completo.py --flask <ruta> --hono <ruta> --rondas 2` |

## Medido el 16-oct-2026 (versión 1.6)

Mismo equipo. Flask `d086db8`, Hono `08807ce` (`git clone --depth 1`) y, como monorepo TypeScript real, el del autor (pnpm, ~1.800 archivos indexables, no público). "v1.5.0" es `origin/main` medido el mismo día con los mismos guiones. Los guiones de las filas 34-37 no usan ningún modelo: comparan contra el compilador de TypeScript (`typescript` de `node_modules`) y el módulo `ast` de Python, que hacen de oráculo.

| # | Afirmación | Resultado | Cómo reproducirlo |
|---|---|---|---|
| 34 | El troceador ya no deja código fuera en clases y objetos grandes | Líneas de código (sin comentarios) fuera de todo fragmento: Hono 441 -> 226 (`src/context.ts` 92 -> 0, donde vivían `c.json`, `c.text` y `c.header`); Flask 50 -> 39; monorepo 1.175 -> 1.149. Símbolos con nombre propio en el monorepo: 12.841 -> 13.504 (los métodos de los objetos servicio) | `python benchmarks/cobertura.py <repos> [--engine <motor viejo>]` |
| 35 | Los imports del grafo de impacto coinciden con los del compilador | Cobertura / precisión de las aristas (archivo, símbolo, origen): Flask 100 % / 96,0 % -> 100 % / 100 %; Hono 74,7 % / 93,9 % -> 100 % / 100 %; monorepo 48,0 % / 94,3 % -> 100 % / 100 % (13.688 imports). Mismo tiempo de troceo (1,49 -> 1,48 s en 1.805 archivos) | `python benchmarks/imports.py <repos> [--engine <motor viejo>]` |
| 36 | Cada import se resuelve al mismo archivo que TypeScript | 100 % de los imports locales (Hono 960, monorepo 3.564). Resuelve de más 46 en Hono (paquetes del propio monorepo que TypeScript no encontró porque el clon no tenía `node_modules`) y 2 en el monorepo | `python benchmarks/resolucion.py <repos>` |
| 37 | `get_impact_radius` separa las definiciones con el mismo nombre | Precisión de los consumidores de cada definición, símbolos con nombre repetido: por nombre (v1.5.0) Hono 18,4 %, monorepo 15,4 %; resuelto (v1.6) 93,2 % y 99,9 %. Todos los símbolos: 38,8 / 43,7 % -> 96,9 / 100 %. Cobertura 100 % en todos los casos. Ejemplo: `useAuth` definido en dos paquetes, 54 y 21 consumidores; v1.5.0 decía 30 (cortaba en 30 filas) | `python benchmarks/resolucion.py <repos>` |
| 38 | Costo de la línea de usos en las búsquedas por nombre | Encontrar y leer una función frente a grep + tramo, 3 semillas: Flask -37 a -39 % (v1.5.0) -> -36 a -38 % (v1.6); Hono -54 % -> -52 %; lenguaje natural Flask -37 % en ambas. Definición primera en 23-25 de 25 y 16 de 16 en ambas | `python benchmarks/ahorro.py --repo <repo> --indexar --semilla N` |
| 39 | Perfil esencial de herramientas MCP | 5 herramientas, 1.781 caracteres (~445 tokens); el perfil completo, 30 con las dos de Gemini, 8.139 caracteres (~2.034 tokens) | `SYNRAG_PERFIL=esencial python scripts/ci/mcp_tools_list.py` |
| 40 | La línea de usos no hace más lenta la búsqueda | 30 consultas nuevas por nombre (10 símbolos al azar por repo: Flask, Hono y el monorepo; semilla 1): mediana 59 ms (v1.5.0) frente a 60 ms (v1.6), p90 82 frente a 86 ms. `get_impact_radius` resuelto: 18-42 ms (5 símbolos). La primera consulta de cada proyecto carga la lista de sus archivos y la guarda 60 s | `python benchmarks/latencia_usos.py <repos> [--engine <motor viejo>]` |

Descartado con mediciones: LLMLingua-2 (comprime ~50 % pero rompe el código, borra resultados de pruebas en logs y pesa 1,9-6,6 GB). Ver `investigacion/llmlingua.md`.

## No afirmado

- **Ahorro en dinero o en sesiones completas de trabajo.** Lo medido son tareas acotadas (filas 19-25 y 33). No hay una medición de sesiones largas reales con y sin SynRAG. `get_savings_report` sigue mostrando una referencia contrafactual, no un ahorro medido.
- **Cuánto cambia la fila 33 con la versión 1.6.** Las filas 34-40 miden piezas sueltas; el sistema completo con un agente real no se ha vuelto a medir (hace falta una clave de Gemini válida: `benchmarks/agente/completo.py`). La tarea `hono_c_json`, que falló al 0 % en ambos modos, ahora encuentra `c.json` con la búsqueda, pero eso no está medido con el agente.
- **Que la fila 33 valga para cualquier agente.** Son 10 tareas, un solo modelo (Gemini 3.5 Flash-Lite) y 2 rondas con mucha varianza. No está medido con Claude ni en sesiones largas.
- **Rust y Go.** El chunker trae sus gramáticas y devuelve fragmentos, pero sin nombre de símbolo (probado el 6-oct-2026) y `ALLOWED_EXTENSIONS` de `engine/indexer.py` no incluye `.rs` ni `.go`, así que esos archivos no se indexan. No están soportados.
- **Compatibilidad** con Gemini CLI, Codex CLI, Cursor, Windsurf, Cline/Roo Code, Zed, macOS y Windows con WSL. Se configuran según su documentación, pero no se han probado. La integración continua (`.github/workflows/pruebas.yml`) prueba Linux y macOS cuando se suba a GitHub.
- **Las demos de la web** (explorador, terminal, observador) son simulaciones con datos de ejemplo.

## Cómo añadir o cambiar una afirmación

1. Mide con un comando que otra persona pueda ejecutar (o cita el archivo y la línea del código).
2. Añade una fila aquí con la fecha, el resultado y el comando.
3. Solo entonces escribe la cifra en el README o en la web.
4. Si una cifra deja de cumplirse, cámbiala o quítala el mismo día.
