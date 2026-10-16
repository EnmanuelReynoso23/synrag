# Guiones de medición

Todos se ejecutan con el Python del entorno de SynRAG (`~/.local/opt/lancedb-hub/.venv/bin/python`), no necesitan red y solo usan la biblioteca estándar más lo que ya instala el motor.

| Guion | Qué mide | Qué toca |
|---|---|---|
| `latencia.py` | Latencia de `search_desktop`. `--modo mcp` (por defecto) arranca el servidor por stdio como lo hace una IA; `--modo motor` llama al motor directamente. Opciones: `--consultas`, `--semilla`, `--proyecto`, `--palabras` | Lee tu índice. En modo mcp el servidor corre con un `HOME` temporal que enlaza tu índice y el modelo, así su registro de telemetría queda aparte. Vacía la caché de consultas al empezar |
| `reindex_archivo.py` | Cuánto tarda `index_single_file` (lo que hace el observador al guardar un archivo) | Trabaja en un `HOME` temporal con 30 archivos sintéticos; no toca tu índice ni tus proyectos |
| `conteos.py` | Proyectos, fragmentos, relaciones y tamaño en disco de tu índice | Solo lectura |

## Cómo se generan las consultas

`latencia.py` toma fragmentos al azar de tu propio índice (con una semilla fija) y elige de 2 a 4 palabras consecutivas que el fragmento contiene; en 4 de cada 5 consultas filtra por el proyecto del fragmento. Eso se parece a lo que envía una IA (en el uso real del autor las consultas tenían una mediana de 4 palabras y el 82 % llevaba filtro de proyecto) y garantiza que siempre hay resultados. Con la misma semilla y el mismo índice, las consultas son las mismas.

## Límites

- Los resultados dependen de tu CPU y de la carga del equipo: con todos los núcleos ocupados, una consulta nueva tarda aproximadamente el doble.
- Son medianas de pocas consultas, no un benchmark estadístico. Corre varias semillas y mira el rango, como hace `CLAIMS.md`.
- Miden velocidad, no calidad: no dicen si el primer resultado es el correcto.
- Las cifras de uso real dentro de una IA pueden ser mucho mayores que las del guion; ver la fila 6 de `CLAIMS.md`.

## Medición con agente real (`benchmarks/agente/agente.py`)

Compara el consumo de tokens y aciertos de un agente de IA autónomo (utilizando function calling de Google Gemini mediante API REST) bajo dos configuraciones idénticas:
- **Modo SIN SynRAG**: el agente dispone de herramientas tradicionales `grep` (búsqueda por patrones regex) y `read_file` (lectura de rangos de líneas).
- **Modo CON SynRAG**: el agente dispone de las mismas herramientas más `search_desktop` conectado al índice sintáctico AST y semántico de LanceDB sobre una base temporal.

Las preguntas se definen en `benchmarks/agente/preguntas.json` (16 preguntas sobre repositorios reales como Flask y Hono, mitad por nombre de símbolo y mitad en lenguaje natural, con respuesta verificable de archivo y función). Los resultados crudos y la tabla comparativa se guardan en `benchmarks/agente/resultados-AAAA-MM-DD.json`.

Uso:
```bash
~/.local/opt/lancedb-hub/.venv/bin/python benchmarks/agente/agente.py \
  --repo-flask /ruta/a/flask \
  --repo-hono /ruta/a/hono \
  [--rondas 2] [--validar] [--modelo gemini-3.5-flash-lite]
```

## Medición del sistema completo (`benchmarks/agente/completo.py`)

Un agente real (Gemini con function calling) hace tareas de varios pasos: localizar, entender (necesita el cuerpo), planear un cambio (llamadas afectadas) y correr pruebas (salidas largas). Se cuentan todos los tokens que cobra la API en cada turno (`usageMetadata`): definiciones de herramientas, historial reenviado, salidas de herramientas y texto del modelo.

- **Modo SIN**: `grep`, `read_file` y `run` con la salida en crudo (cortada a 30.000 caracteres, como hace Claude Code).
- **Modo CON**: lo mismo más `search_desktop`, `get_file_outline` y `repo_map`; la salida de `run` pasa por el filtro de salidas largas y el prompt de sistema lleva el modo conciso.

Cada tarea tiene una lista de hechos que la respuesta debe contener y se puntúa sola. La clave se lee de `GEMINI_API_KEY` y nunca se imprime ni se guarda. Una corrida completa son ~200 llamadas a la API; `--progreso archivo.jsonl` permite reanudarla tras un corte.

Uso:
```bash
git clone --depth 1 https://github.com/pallets/flask /tmp/flask
git clone --depth 1 https://github.com/honojs/hono  /tmp/hono
GEMINI_API_KEY=... python benchmarks/agente/completo.py --flask /tmp/flask --hono /tmp/hono \
  [--rondas 2] [--modelo gemini-3.5-flash-lite] [--solo id1,id2] [--progreso progreso.jsonl]
```

Resultado del 15-oct-2026: fila 33 de `CLAIMS.md`.
