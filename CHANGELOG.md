# Cambios

## 1.6.0 (16-oct-2026)

Cada cifra sale de un guion de `benchmarks/` y tiene su fila en `CLAIMS.md` (filas 34-40). Aún sin medir con un agente real: ver "No afirmado".

### Arreglado
- Clases y objetos grandes perdían código: solo se guardaban los `method_definition`, y los campos con función flecha (`json = () => {}` en el `Context` de Hono) y lo que había entre ellos quedaban fuera del índice. Hono: 441 -> 226 líneas de código fuera de todo fragmento (`src/context.ts` 92 -> 0). Los objetos literales grandes (`const servicio = { listar() {}, crear: async () => {} }`) se trocean por miembro: +663 símbolos con nombre en un monorepo TS real (`benchmarks/cobertura.py`).
- El grafo de impacto no veía los imports de varias líneas, `import D, { a } from` ni los re-export, y tomaba texto de docstrings como imports. Ahora salen del AST: cobertura 100 % y precisión 100 % frente al compilador de TypeScript y `ast` de Python (antes Hono 75 %, un monorepo TS real 48 %) (`benchmarks/imports.py`).
- `get_impact_radius` cortaba en 30 filas y mezclaba los consumidores de símbolos con el mismo nombre.

### Nuevo
- Resolución de imports (`engine/resolver.py`): rutas relativas, `paths` y `baseUrl` del tsconfig con `extends` y el `tsconfig.app.json` de Vite, paquetes del monorepo por su `package.json` y módulos de Python con `src/`; sigue los barrels hasta la definición. Mismo archivo que TypeScript en el 100 % de los imports locales (`benchmarks/resolucion.py`).
- `get_impact_radius` separa las definiciones (`archivo=` elige una). Precisión en símbolos con nombre repetido: 15-18 % -> 93-100 %, cobertura 100 %. `repo_map` usa la misma resolución.
- `search_desktop`: línea de usos bajo la definición exacta (llamadas en su archivo y en los que la importan, primero el código); `objeto.miembro` y `Clase miembro` dan la definición del miembro; las pruebas van detrás del código salvo que la consulta las pida. Costo de la línea de usos en búsquedas por nombre: Flask -37/-39 % -> -36/-38 %, Hono -54 % -> -52 %.
- Perfil esencial (`SYNRAG configure --perfil esencial`): 5 herramientas MCP, definiciones de ~2.000 a ~445 tokens.

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
- `check_breaking_callsites` y `find_code_duplicates` fallaban si ripgrep (`rg`) no estaba instalado; ahora buscan en Python.
- En macOS (disco que no distingue mayúsculas) `~/Proyectos` y `~/proyectos` se indexaban dos veces.
- El grafo de impacto nunca se compactaba (índice de 350-400 MB a 132 MB).
- Observador: una sola cola de espera, compactación periódica y recarga de carpetas sin reiniciar (2.001 -> 2 archivos de versión, 23 -> 3 hilos).
- Herramientas de contexto: detectan la IA que llama y miden su sesión; sin cifras no medidas.
- Herramientas de ejecución: detección robusta, rutas saneadas y salidas acotadas (`tail_clean_logs` dice cuántas líneas omitió).
- `verify_dependency_exists` admite monorepos y workspaces.
- El mapa ya no crea aristas falsas con imports externos (2,1 s -> 0,11 s).
- La caché ya no escribe en la tabla en cada acierto (consulta repetida 3,3-3,7 ms).

### Descartado
- LLMLingua-2: comprime ~50 % pero rompe el código y pesa 1,9-6,6 GB (`investigacion/llmlingua.md`).
