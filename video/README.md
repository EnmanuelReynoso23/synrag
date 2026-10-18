# Video de presentación

Video de 68 s en 1080x1350 (4:5, el formato que más ocupa en el feed de LinkedIn en el móvil), sin voz: todo el mensaje va en pantalla porque LinkedIn reproduce los videos sin sonido.

La música es original, sintetizada con numpy en `musica.py` (sin muestras ni canciones de terceros, así que no hay derechos que reclamar): La menor a 100 BPM, colchón y bajo desde el principio, arpegio desde "Cómo funciona", batería en las demos y los resultados, tecleo sincronizado con los comandos, un barrido en cada cambio de escena y un golpe grave cuando aparece el -63,9 %. Volumen final: -14 LUFS.

| Seg. | Escena | De dónde sale |
|---|---|---|
| 0-5,6 | Gancho: el agente lee archivos enteros; SynRAG le da la definición exacta | README |
| 5,6-12,4 | El problema: bloques fijos que parten funciones; AST = 1 función, 1 fragmento | `flask/sessions.py` |
| 12,4-20,6 | Cómo funciona: Tree-sitter, BM25 en LanceDB, FlashRank en CPU, grafo de impacto, MCP | README |
| 20,6-33 | Demo: `SYNRAG index` y `SYNRAG --project flask "SecureCookieSessionInterface open_session"` | salida real (`terminal.json`) |
| 33-40,4 | Demo: `SYNRAG impact HTTPException` sobre Hono | salida real (`terminal.json`) |
| 40,4-49,6 | Resultados: -63,9 % de tokens, 87 -> 94 %, 59-89 ms, -76/-84 %, 159 tokens | `src/data/medido.ts`, CLAIMS filas 23, 27-28, 40-42 |
| 49,6-55,6 | Dónde pierde (+117 % en tareas cortas) y pruebas | CLAIMS fila 41, `pytest`, `scripts/ci` |
| 55,6-61,2 | XERJ (Corpus Hub) y Agensi.io | correos recibidos en oct-2026 |
| 61,2-68 | Cierre: instalación en una línea y enlace al repo | |

Si cambia una cifra en `CLAIMS.md`, se cambia también en `escenas.html` antes de volver a renderizar.

## Regenerarlo

```bash
# 1. Salidas reales del CLI con color (con Flask y Hono indexados en ~/Projects)
FORCE_COLOR=1 COLUMNS=78 SYNRAG --project flask "SecureCookieSessionInterface open_session" > ansi/miembro.ansi
FORCE_COLOR=1 COLUMNS=78 SYNRAG impact HTTPException > ansi/impact.ansi
python video/ansi2html.py ansi '[["miembro", 8, 36], ["impact", 0, 20]]' > video/terminal.json

# 2. Fotogramas sueltos para revisar, y el video completo (Chromium + ffmpeg, ~4 min)
node video/render.cjs revisar/ 5 12 20 32 40 49 55 60 67
node video/render.cjs synrag.mp4

# 3. Música y mezcla final a -14 LUFS (el estándar de las redes)
python video/musica.py musica.wav
ffmpeg -i synrag.mp4 -i musica.wav -map 0:v -map 1:a -c:v copy -af "loudnorm=I=-14:TP=-1.5:LRA=11" \
  -ar 48000 -c:a aac -b:a 192k -movflags +faststart -shortest synrag-final.mp4
```

`render.cjs` usa Playwright; si está instalado de forma global, se le pasa con `NODE_PATH=<ruta>/node_modules`. Para verlo en el navegador basta con abrir `escenas.html` y llamar a `render(t)` desde la consola (sin `terminal.json` las terminales salen vacías).
