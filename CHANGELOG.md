# Cambios

## 1.5.0 (15-oct-2026)

Cada cifra sale de un guion de `benchmarks/` y tiene su fila en `CLAIMS.md`.

### Cuánto ahorra (medido)
- Sistema completo con un agente real (10 tareas de varios pasos x 2 rondas, tokens cobrados por la API): **-29,2 %**, calidad 87 % -> 90 % (fila 33). Pierde en tareas muy cortas y en 2 de 3 de Flask; varianza alta entre rondas.
- Agente real, solo ubicar (16 preguntas x 2 rondas): -11,5 %, 16/16 aciertos (fila 19).
- Encontrar y leer una función frente a grep + tramo: Flask -27 a -30 %, Hono -45 %; lenguaje natural Flask -31 % (filas 20-21).
- Documentación -22 % frente a grep; empaquetado solo con firmas -76/-84 %; salidas largas de terminal -87 a -99 % (filas 22-24).
- Costo fijo de las definiciones MCP: de ~4.150 a ~2.000 tokens por sesión (fila 26).

### Nuevo
- Localizar antes que leer: la definición sale primera y entera; el resto en una línea por resultado.
- Indexación de documentación en fragmentos de ~200 tokens, con filtro `tipo` en la búsqueda (el código va primero por defecto).
- Mapa del repo con PageRank y empaquetado comprimido (solo firmas, tipos e imports).
- Filtro de salidas largas (`configure --filtro-largas`, hook PostToolUse de Claude Code): conserva inicio, errores con contexto y final; la salida completa queda en `~/.cache/synrag/salidas`.
- Modo conciso opcional (`configure --conciso`), estilo caveman de Julius Brussee (Apache-2.0): -77 % en la salida del modelo.
- Carpetas configurables (`SYNRAG carpetas`, `~/.config/synrag/carpetas.txt` o `SYNRAG_CARPETAS`) con detección de carpetas habituales.
- Guiones de medición: `benchmarks/agente/agente.py` y `benchmarks/agente/completo.py` (agente real), `ahorro.py`, `docs.py`, `mapa.py`, `filtro.py`, `conciso.py`, `observador.py`.
- Integración continua: Linux y macOS, Python 3.10 y 3.12, instalación limpia y `tools/list` del MCP.

### Arreglado
- El instalador no copiaba `tools/` ni `argon.py` y el MCP no arrancaba en un equipo nuevo.
- El grafo de impacto nunca se compactaba (índice de 350-400 MB a 132 MB).
- Observador: una sola cola de espera, compactación periódica y recarga de carpetas sin reiniciar (2.001 -> 2 archivos de versión, 23 -> 3 hilos).
- Herramientas de contexto: detectan la IA que llama y miden su sesión; sin cifras no medidas.
- Herramientas de ejecución: detección robusta, rutas saneadas y salidas acotadas (`tail_clean_logs` dice cuántas líneas omitió).
- `verify_dependency_exists` admite monorepos y workspaces.
- El mapa ya no crea aristas falsas con imports externos (2,1 s -> 0,11 s).
- La caché ya no escribe en la tabla en cada acierto (consulta repetida 3,3-3,7 ms).

### Descartado
- LLMLingua-2: comprime ~50 % pero rompe el código y pesa 1,9-6,6 GB (`investigacion/llmlingua.md`).
