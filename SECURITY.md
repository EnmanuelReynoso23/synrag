# Seguridad y privacidad

Qué hace SyntaxRAG (SYNRAG) con tus datos y con tus archivos de configuración, y cómo reportar un problema.

## Qué se indexa y dónde se guarda

- Indexa en tu equipo los archivos de texto y de código de las carpetas que el motor escanea (`SCAN_DIRECTORIES` en `engine/indexer.py`: por defecto `~/Proyectos` y `~/AsistoYA/Proyectos`). El índice vive en `~/.local/share/lancedb-hub/` y nunca sale de tu equipo.
- **Excluye** carpetas ocultas, `.git`, `node_modules`, carpetas de compilación, archivos de más de 250 KB y archivos cuyo nombre sugiere credenciales (`.env`, `credential`, `secret`, `*.pem`, `*.key`, `id_rsa`, `keystore`, entre otros). Los patrones exactos están en `engine/indexer.py`.
- **Redacta** dentro del contenido los patrones de claves de API, contraseñas y tokens (`[SECRETO-OCULTO]`). La redacción se basa en patrones: no garantiza detectar todo secreto. No guardes secretos en archivos que se indexen.

## Qué se envía fuera de tu equipo

- El motor no hace llamadas de red: no importa ninguna biblioteca de red ni envía datos a servidores (se puede comprobar con `grep -rniE "requests|urllib|httpx|socket" engine/*.py`, que no devuelve nada).
- Las únicas conexiones son las de la instalación y el primer uso: `pip` descarga las dependencias, `install.sh` descarga los archivos del motor desde `raw.githubusercontent.com`, y la biblioteca FlashRank descarga el modelo de reordenado la primera vez que se usa.
- El registro de búsquedas (`~/.local/share/lancedb-hub/telemetry.db`) es local: guarda la consulta, el proyecto, tamaños y latencia. No se envía a ningún sitio.

## Qué modifica el instalador

- Añade el servidor MCP `desktop-lancedb` al archivo de configuración de cada IA instalada y un bloque entre las marcas `<!-- SYNRAG:BEGIN -->` y `<!-- SYNRAG:END -->` en sus instrucciones globales.
- Antes de modificar un archivo existente guarda una copia `.bak-AAAAMMDD-HHMMSS`; no pisa un JSON que no pueda leer; no usa `sudo`; es idempotente.
- `SYNRAG uninstall` quita lo que añadió (`SYNRAG uninstall --dry-run` muestra qué quitaría sin escribir nada).

## Instalar con `curl | bash`

Ese comando ejecuta un script descargado de GitHub. Si prefieres revisarlo antes: `curl -sSL https://raw.githubusercontent.com/EnmanuelReynoso23/synrag/main/install.sh | less`, o clona el repositorio y ejecuta `./install.sh`. Pendiente: publicar la suma `sha256` de `install.sh` en cada versión.

## Cómo reportar una vulnerabilidad

Usa la pestaña **Security** del repositorio (Report a vulnerability) si está habilitada. Si no, abre una incidencia que no incluya detalles explotables y pide un contacto privado. Se atiende con el mejor esfuerzo posible; no hay un plazo garantizado.
