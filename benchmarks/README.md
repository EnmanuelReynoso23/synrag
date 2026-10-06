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
