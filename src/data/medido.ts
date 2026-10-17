// Todas las cifras de la web salen de CLAIMS.md (columna "fila"). Si una cambia alli, se cambia aqui
// el mismo dia. Nada de esta pagina es una proyeccion.

export const VERSION = '1.6.0';
export const REPO = 'https://github.com/EnmanuelReynoso23/synrag';
export const CLAIMS = `${REPO}/blob/main/CLAIMS.md`;
export const CHANGELOG = `${REPO}/blob/main/CHANGELOG.md`;
export const INSTALAR = 'curl -sSL https://raw.githubusercontent.com/EnmanuelReynoso23/synrag/main/install.sh | bash';

/** La medición principal: agente real, tareas de varios pasos (CLAIMS fila 41). */
export const PRINCIPAL = {
  ahorro: '-63,9 %',
  sin: '305.736',
  con: '110.338',
  ic: '-83 % a -24 %',
  calidadAntes: '87 %',
  calidadDespues: '94 %',
  fecha: '16-oct-2026',
  tareas: '10 tareas de varios pasos x 2 rondas',
  modelo: 'Gemini 3.5 Flash-Lite con function calling',
  comando: 'python benchmarks/agente/completo.py --flask <ruta> --hono <ruta> --rondas 2',
  fila: 41,
};

export interface Medicion {
  que: string;
  resultado: string;
  detalle: string;
  comando: string;
  fila: string;
}

export const MEDICIONES: Medicion[] = [
  {
    que: 'Agente real, solo ubicar',
    resultado: '-11,5 %',
    detalle: '16 preguntas x 2 rondas, 16/16 aciertos con y sin SynRAG. Gana en 7 de 16: es el peor caso, porque SynRAG entrega la definición entera y la pregunta solo pide la ubicación.',
    comando: 'python benchmarks/agente/agente.py',
    fila: '19',
  },
  {
    que: 'Encontrar y leer una función por su nombre',
    resultado: '-36 a -52 %',
    detalle: 'Frente a grep + leer el tramo. Flask -36 a -38 % (3 semillas, 25 funciones), Hono -52 % (16 funciones). La definición sale primera en 23-25 de 25 y 16 de 16.',
    comando: 'python benchmarks/ahorro.py --repo <repo> --indexar --semilla N',
    fila: '38',
  },
  {
    que: 'Preguntas en lenguaje natural',
    resultado: '-37 %',
    detalle: 'Flask, 12 preguntas. La respuesta queda en el top 5 en 11 de 12.',
    comando: 'python benchmarks/ahorro.py --repo flask --indexar --n 0 --naturales benchmarks/preguntas/flask.json',
    fila: '21, 38',
  },
  {
    que: 'Documentación',
    resultado: '-22 %',
    detalle: 'Fragmentos de ~200 tokens con su ruta de títulos. -22 % frente a grep + 40 líneas y -91 % frente a leer el archivo entero; respuesta en el top 5 en 10 de 10.',
    comando: 'python benchmarks/docs.py --repo flask',
    fila: '22',
  },
  {
    que: 'Empaquetar un repo solo con firmas',
    resultado: '-76 a -84 %',
    detalle: 'Firmas, tipos e imports para pegar en un chat web. Flask 160.514 -> 38.882 tokens, Hono 756.316 -> 118.669.',
    comando: 'python benchmarks/mapa.py --repo <repo>',
    fila: '23',
  },
  {
    que: 'Salidas largas de la terminal (opcional)',
    resultado: '-87 a -99 %',
    detalle: 'find: 178.449 -> 1.249 tokens; journalctl: 59.248 -> 7.444. Conserva todas las líneas de error y deja la salida completa en un archivo.',
    comando: 'python benchmarks/filtro.py',
    fila: '24',
  },
  {
    que: 'Imports del grafo de impacto',
    resultado: '100 %',
    detalle: 'Cobertura y precisión frente al compilador de TypeScript y el módulo ast de Python (13.688 imports en un monorepo real). Antes: Hono 75 %, monorepo 48 %.',
    comando: 'python benchmarks/imports.py <repos>',
    fila: '35, 36',
  },
  {
    que: 'Quién depende de cada definición',
    resultado: '15-18 % -> 93-100 %',
    detalle: 'Precisión de get_impact_radius cuando dos archivos definen un símbolo con el mismo nombre (por ejemplo useAuth en dos paquetes). Cobertura 100 %.',
    comando: 'python benchmarks/resolucion.py <repos>',
    fila: '37',
  },
  {
    que: 'Velocidad de una búsqueda',
    resultado: '59-89 ms',
    detalle: 'Mediana de una consulta nueva en el índice del autor (125.570 fragmentos), en CPU. Repetida: 3,3-3,7 ms desde la caché. Reindexar todo: 16,7 s para 9.247 archivos.',
    comando: 'python benchmarks/latencia.py --modo motor --semilla N',
    fila: '27, 28, 40',
  },
];

/** Donde pierde: se publica igual que donde gana. */
export const PIERDE = [
  {
    titulo: 'Tareas muy cortas',
    texto: 'En pruebas con salida corta gasta +117 %: las definiciones de las herramientas pesan más que la tarea. Por eso existen los perfiles esencial y bajo demanda.',
    fila: '41',
  },
  {
    titulo: 'Una tarea de Flask',
    texto: 'Al pedir la firma de la sesión de Flask gasta +38 %. Con grep alcanza con una línea y SynRAG entrega el bloque completo.',
    fila: '41',
  },
  {
    titulo: 'La varianza entre días',
    texto: 'La misma v1.5 midió -29,2 % el 15-oct y -4,6 % el 16-oct. Con 10 tareas y 2 rondas el margen es amplio: la cifra principal tiene un intervalo de -83 % a -24 %.',
    fila: '33, 41',
  },
];

export const NO_AFIRMADO = [
  'Ahorro en dinero ni en sesiones largas de trabajo: lo medido son tareas acotadas.',
  'Que valga igual para cualquier modelo: todo lo del agente está medido con Gemini 3.5 Flash-Lite, no con Claude.',
  'Que la mejora de la v1.6 sobre la v1.5 sea general: sale de 2 de 10 tareas y su intervalo incluye el cero.',
  'Rust y Go: el troceador los lee pero no se indexan.',
  'Cursor, Windsurf, Gemini CLI, Codex CLI, Cline, Roo Code y Zed: se configuran según su documentación, pero no se han probado.',
  'macOS y Windows con WSL: deberían funcionar, solo está probado en Linux.',
];

export interface Grupo {
  nombre: string;
  herramientas: string[];
  para: string;
}

export const HERRAMIENTAS: Grupo[] = [
  { nombre: 'Buscar y orientarse', para: 'Encontrar lo que hace falta sin listar carpetas ni abrir archivos enteros.', herramientas: ['search_desktop', 'get_file_outline', 'repo_map', 'list_projects', 'reindex_desktop'] },
  { nombre: 'Antes de editar', para: 'Saber qué se rompe antes de tocar un símbolo.', herramientas: ['get_impact_radius', 'find_related_tests', 'find_callers_exact', 'get_symbol_contract', 'extract_type_definition', 'get_import_graph', 'check_breaking_callsites', 'check_circular_imports', 'verify_dependency_exists', 'find_code_duplicates'] },
  { nombre: 'Editar', para: 'Cambios quirúrgicos que conservan sangría y saltos de línea, con respaldo fuera del repo.', herramientas: ['patch_function_body', 'add_import_clean', 'rename_symbol_scoped', 'remove_unused_imports'] },
  { nombre: 'Ejecutar con salida corta', para: 'Pruebas, lint y logs resumidos: solo lo que importa vuelve al modelo.', herramientas: ['run_test_isolated', 'lint_summary', 'run_typecheck_focus', 'tail_clean_logs'] },
  { nombre: 'Sesión', para: 'Cortar a tiempo: lo que más pesa en una sesión real es su longitud.', herramientas: ['session_handoff', 'context_budget_alert', 'git_staged_overview', 'extract_todo_status', 'get_savings_report'] },
  { nombre: 'Opcional con tu clave de Gemini', para: 'Solo aparecen si configuras GEMINI_API_KEY; sin ella el motor no usa la red.', herramientas: ['ask_synrag_architect', 'explain_blast_radius'] },
];

export const PERFILES = [
  { nombre: 'completo', herramientas: '28 (30 con Gemini)', costo: '~2.000 tokens por turno', cuando: 'Clientes que cargan las herramientas bajo demanda, como Claude Code.', fila: '26' },
  { nombre: 'esencial', herramientas: '5', costo: '~445 tokens por turno', cuando: 'Clientes que cobran todas las definiciones en cada turno.', fila: '39' },
  { nombre: 'bajo_demanda', herramientas: '1 + synrag_mas', costo: 'sin medir todavía', cuando: 'Arranca solo con search_desktop; el resto se activa cuando el agente lo pide.', fila: '-' },
];

export const INTEGRACIONES = [
  { ia: 'Claude Code', estado: 'probado', mcp: '~/.claude.json', reglas: '~/.claude/CLAUDE.md' },
  { ia: 'Google Antigravity', estado: 'probado', mcp: '~/.gemini/config/mcp_config.json', reglas: '~/.gemini/GEMINI.md' },
  { ia: 'Gemini CLI', estado: 'sin probar', mcp: '~/.gemini/settings.json', reglas: '~/.gemini/GEMINI.md' },
  { ia: 'Codex CLI', estado: 'sin probar', mcp: '~/.codex/config.toml', reglas: '~/.codex/AGENTS.md' },
  { ia: 'Cursor', estado: 'sin probar', mcp: '~/.cursor/mcp.json', reglas: 'a mano en Settings > Rules' },
  { ia: 'Windsurf', estado: 'sin probar', mcp: '~/.codeium/windsurf/mcp_config.json', reglas: 'global_rules.md' },
  { ia: 'Cline / Roo Code', estado: 'sin probar', mcp: 'cline_mcp_settings.json', reglas: '-' },
  { ia: 'Zed', estado: 'sin probar', mcp: '~/.config/zed/settings.json', reglas: '-' },
];
