export interface ASTResult {
  id: string;
  query: string;
  label: string;
  project: string;
  file: string;
  lines: string;
  symbol: string;
  kind: 'Hook' | 'Function' | 'Class' | 'Component' | 'Type';
  language: 'typescript' | 'python';
  code: string;
  impactConsumers: Array<{ file: string; project: string; risk: 'CRITICAL' | 'WARNING' | 'INFO' }>;
  score: number;
  cacheHit: boolean;
  latencyMs: number;
  tokensConsumed: number;
  cost: string;
}

export const SAMPLE_QUERIES: ASTResult[] = [
  {
    id: 'asistencia-servicio',
    query: 'asistenciaServicio',
    label: 'Servicio Central de Asistencia',
    project: 'mi-monorepo',
    file: 'apps/web/src/modulos/asistencia/asistencia.servicio.ts',
    lines: '35-72',
    symbol: 'asistenciaServicio',
    kind: 'Function',
    language: 'typescript',
    code: `export const asistenciaServicio = {
  async registrarPase(payload: RegistroAsistenciaDTO): Promise<ResultadoAsistencia> {
    // Valida sesión activa, biometría facial y políticas del centro
    const validacion = await validarPoliticaCentro(payload.escuelaId, payload.estudianteId);
    if (!validacion.permitido) {
      throw new Error(\`Registro denegado: \${validacion.motivo}\`);
    }

    const registro = await persistirAsistenciaLocal(payload);
    emitirEventoRealtime('asistencia:registrada', registro);
    return { exito: true, timestamp: Date.now(), registroId: registro.id };
  },

  async obtenerResumenDiario(escuelaId: string, fecha: string): Promise<ResumenAula> {
    return await consultarResumenEscolar(escuelaId, fecha);
  }
};`,
    impactConsumers: [
      { file: 'apps/web/src/demo/demoData.ts', project: 'mi-monorepo', risk: 'CRITICAL' },
      { file: 'apps/web/src/modulos/asistencia/asistencia.hook.ts', project: 'mi-monorepo', risk: 'CRITICAL' },
      { file: 'apps/web/src/modulos/administrador/componentes/PanelAsistencia.tsx', project: 'mi-monorepo', risk: 'CRITICAL' },
      { file: 'apps/web/src/modulos/kiosco/PaginaKioscoPublica.tsx', project: 'mi-monorepo', risk: 'WARNING' },
      { file: 'apps/web/src/modulos/profesor/componentes/PaseDeLista.tsx', project: 'mi-monorepo', risk: 'CRITICAL' },
      { file: 'apps/web/src/services/analytics/eventos.ts', project: 'mi-monorepo', risk: 'INFO' },
      { file: 'apps/web/src/modulos/padre/componentes/HistorialHijo.tsx', project: 'mi-monorepo', risk: 'WARNING' },
      { file: 'apps/web/src/modulos/reportes/exportadorAsistencia.ts', project: 'mi-monorepo', risk: 'INFO' },
    ],
    score: 99.2,
    cacheHit: true,
    latencyMs: 8.7,
    tokensConsumed: 0,
    cost: '$0.00',
  },
  {
    id: 'reconocimiento-facial',
    query: 'reconocimientoFacial',
    label: 'Algoritmo Biométrico Escolar',
    project: 'mi-monorepo',
    file: 'apps/web/src/modulos/reconocimiento-facial/reconocimiento.servicio.ts',
    lines: '18-54',
    symbol: 'procesarDescriptorFacial',
    kind: 'Function',
    language: 'typescript',
    code: `export async function procesarDescriptorFacial(
  descriptor: Float32Array,
  descriptoresConocidos: DescriptorEstudiante[]
): Promise<CoincidenciaFacial | null> {
  let mejorDistancia = UMBRAL_DISTANCIA_MINERD; // 0.42 estricto
  let mejorMatch: CoincidenciaFacial | null = null;

  for (const conocido of descriptoresConocidos) {
    const distancia = distanciaEuclidiana(descriptor, conocido.vector);
    if (distancia < mejorDistancia) {
      mejorDistancia = distancia;
      mejorMatch = { estudianteId: conocido.estudianteId, confianza: 1 - distancia };
    }
  }

  return mejorMatch;
}`,
    impactConsumers: [
      { file: 'apps/web/src/modulos/kiosco/TerminalBiometrico.tsx', project: 'mi-monorepo', risk: 'CRITICAL' },
      { file: 'apps/web/src/modulos/reconocimiento-facial/componentes/CamaraCaptura.tsx', project: 'mi-monorepo', risk: 'CRITICAL' },
      { file: 'apps/web/src/services/face/faceService.ts', project: 'mi-monorepo', risk: 'WARNING' },
    ],
    score: 98.7,
    cacheHit: true,
    latencyMs: 9.1,
    tokensConsumed: 0,
    cost: '$0.00',
  },
  {
    id: 'use-estudiantes',
    query: 'useEstudiantes',
    label: 'Hook de Estado React',
    project: 'mi-monorepo',
    file: 'apps/web/src/modulos/estudiantes/hooks/useEstudiantes.ts',
    lines: '14-48',
    symbol: 'useEstudiantes',
    kind: 'Hook',
    language: 'typescript',
    code: `export const useEstudiantes = (seccionId: string) => {
  const [estudiantes, setEstudiantes] = useState<Estudiante[]>([]);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let cancelado = false;
    async function sincronizar() {
      setCargando(true);
      const data = await estudianteServicio.listarPorSeccion(seccionId);
      if (!cancelado) {
        setEstudiantes(data);
        setCargando(false);
      }
    }
    sincronizar();
    return () => { cancelado = true; };
  }, [seccionId]);

  return { estudiantes, cargando, total: estudiantes.length };
};`,
    impactConsumers: [
      { file: 'apps/web/src/modulos/profesor/componentes/PaseDeLista.tsx', project: 'mi-monorepo', risk: 'CRITICAL' },
      { file: 'apps/web/src/modulos/calificaciones/componentes/TablaNotas.tsx', project: 'mi-monorepo', risk: 'CRITICAL' },
      { file: 'apps/web/src/modulos/reportes/ReporteSeccion.tsx', project: 'mi-monorepo', risk: 'WARNING' },
    ],
    score: 97.9,
    cacheHit: false,
    latencyMs: 91.3,
    tokensConsumed: 0,
    cost: '$0.00',
  },
  {
    id: 'chunker-ast',
    query: 'chunkerTreeSitter',
    label: 'Parser Sintáctico AST en Python',
    project: 'syntaxrag-core',
    file: '~/.local/opt/lancedb-hub/chunker.py',
    lines: '118-154',
    symbol: 'extract_ast_blocks',
    kind: 'Function',
    language: 'python',
    code: `def extract_ast_blocks(source_code: str, language: str) -> list[ASTChunk]:
    parser = get_tree_sitter_parser(language)
    tree = parser.parse(bytes(source_code, "utf8"))
    query = get_language_query(language)
    
    chunks = []
    for pattern_idx, match in enumerate(query.matches(tree.root_node)):
        node = match[1]['target_node']
        chunks.append(ASTChunk(
            symbol=get_node_identifier(node),
            kind=node.type,
            lines=(node.start_point[0], node.end_point[0]),
            code=source_code[node.start_byte:node.end_byte]
        ))
    return chunks`,
    impactConsumers: [
      { file: 'indexer.py', project: 'syntaxrag-core', risk: 'CRITICAL' },
      { file: 'watcher.py', project: 'syntaxrag-core', risk: 'CRITICAL' },
      { file: 'cli.py', project: 'syntaxrag-core', risk: 'WARNING' },
    ],
    score: 99.5,
    cacheHit: true,
    latencyMs: 9.4,
    tokensConsumed: 0,
    cost: '$0.00',
  }
];

export const ARCHITECTURE_PIPELINE = [
  {
    id: 'agent',
    step: '01',
    name: 'Editor / Agente IA',
    tech: 'Claude Code · Antigravity (probados) · otras IAs con MCP',
    file: 'Entorno de Desarrollo',
    role: 'Petición de búsqueda o contexto mediante protocolo MCP stdio.',
    desc: 'El agente o programador consulta funciones sin leer archivos enteros ni desbordar la ventana de contexto.',
    badge: 'Consumidor',
    color: '#00E5FF',
  },
  {
    id: 'mcp',
    step: '02',
    name: 'Servidor MCP Stdio',
    tech: 'desktop-lancedb (JSON-RPC)',
    file: '~/.local/opt/lancedb-hub/server_mcp.py',
    role: 'Exposición estándar de search_desktop y list_projects.',
    desc: 'Protocolo MCP por stdio que conecta al agente con el índice local.',
    badge: 'Protocolo',
    color: '#58A6FF',
  },
  {
    id: 'cache',
    step: '03',
    name: 'Caché Local de Consultas',
    tech: 'LanceDB query_cache (misma consulta, ~9 ms)',
    file: 'cache.py',
    role: 'Devuelve los resultados de consultas idénticas recientes.',
    desc: 'Si repites la misma consulta (sin distinguir mayúsculas ni espacios) se responde desde la tabla local sin recalcular; con otras palabras se vuelve a buscar. Se vacía al reindexar.',
    badge: 'Sin APIs',
    color: '#7EE787',
  },
  {
    id: 'ast',
    step: '04',
    name: 'Tree-sitter AST Chunker',
    tech: 'Gramáticas Tree-sitter: TS, TSX, JS, Python, Rust, Go',
    file: 'chunker.py',
    role: 'Extracción sintáctica de funciones, hooks, clases y tipos.',
    desc: 'Conserva firmas completas, cuerpo de código y docstrings; solo los bloques de más de 2.400 caracteres se dividen.',
    badge: 'AST Native',
    color: '#00E5FF',
  },
  {
    id: 'impact',
    step: '05',
    name: 'Grafo de Impacto de Dependencias',
    tech: 'Tabla impact_graph en LanceDB (23,704 relaciones)',
    file: 'impact.py',
    role: 'Mapeo estático de imports y dependientes.',
    desc: 'Inyecta advertencias sobre qué archivos consumen el símbolo consultado para evitar roturas antes de editar.',
    badge: 'Prevención',
    color: '#FF7B72',
  },
  {
    id: 'vector',
    step: '06',
    name: 'LanceDB Hub Columnar Store',
    tech: 'LanceDB 0.39 (disco columnar ~65 MB en el índice del autor)',
    file: 'indexer.py',
    role: 'Almacenamiento e indexación local.',
    desc: 'Almacena ~96 mil fragmentos con compresión columnar y búsqueda de texto BM25 (Tantivy).',
    badge: 'Storage',
    color: '#8B949E',
  },
  {
    id: 'ranker',
    step: '07',
    name: 'Reranker Neuronal FlashRank',
    tech: 'ms-marco-TinyBERT-L-2-v2 en CPU (ONNX)',
    file: 'ranker.py',
    role: 'Scoring continuo de relevancia en procesador local.',
    desc: 'Reordena los candidatos recuperados por palabras con un modelo transformador compacto en CPU, sin requerir GPU.',
    badge: 'CPU Neural',
    color: '#00E5FF',
  },
];

export const ECOSYSTEM_METRICS = [
  { label: 'Fragmentos AST Indexados', value: '~96 mil', unit: 'bloques sintácticos', delta: 'Índice del autor, 6-oct-2026' },
  { label: 'Consulta Nueva', value: '~90 ms', unit: 'mediana en CPU local', delta: 'p90 ~110 ms; primera consulta ~180 ms' },
  { label: 'Consulta Repetida', value: '~9 ms', unit: 'misma consulta, caché local', delta: 'Sin APIs de pago' },
  { label: 'Relaciones en Grafo de Impacto', value: '23,704', unit: 'dependencias mapeadas', delta: 'Qué archivos importan cada símbolo' },
  { label: 'Reindexar un Archivo', value: '~8 ms', unit: 'archivo pequeño, tras 0,6 s de espera', delta: 'Observador opcional (300 MB o más de RAM)' },
  { label: 'Proyectos Indexados', value: '~75', unit: 'carpetas de código y notas', delta: 'Equipo del autor' },
];

export const PROYECTOS_DISTRIBUCION = [
  { nombre: 'mi-monorepo', chunks: 22923, porcentaje: 24.0, descripcion: 'Monorepo principal (Portal Web, Kiosco y Módulos)' },
  { nombre: 'servicios-locales', chunks: 16157, porcentaje: 16.9, descripcion: 'Servicios de sincronización y base local' },
  { nombre: 'scripts-soporte', chunks: 11075, porcentaje: 11.6, descripcion: 'Componentes y scripts de soporte' },
  { nombre: 'juego-demo', chunks: 10365, porcentaje: 10.8, descripcion: 'Ecosistema de juegos y gamificación' },
  { nombre: 'libs-base', chunks: 7462, porcentaje: 7.8, descripcion: 'Servicios legados y librerías base' },
  { nombre: 'portal-empresas', chunks: 5856, porcentaje: 6.1, descripcion: 'Portal de empresas y proveedores' },
  { nombre: 'Vision-Humana', chunks: 3758, porcentaje: 3.9, descripcion: 'Motor de biometría y visión artificial' },
];

export const CONFIG_SNIPPETS = {
  synrag: `# Abrir el espacio de trabajo completo (Dark Mode + Live Stats)
SYNRAG

# Búsqueda por palabras con reordenado neuronal (usa palabras que estén escritas en el código)
SYNRAG "asistenciaServicio"

# Búsqueda acotada a un proyecto del monorepo
SYNRAG --project mi-monorepo "reconocimientoFacial"

# Ver estadísticas del índice y el registro de búsquedas
SYNRAG stats

# Ver log reactivo ante Ctrl+S
SYNRAG watch`,

  claude: `// ~/.claude.json  (el instalador lo escribe solo con: SYNRAG configure)
// Cambia TU_USUARIO por tu nombre de usuario.
{
  "mcpServers": {
    "desktop-lancedb": {
      "command": "/home/TU_USUARIO/.local/opt/lancedb-hub/.venv/bin/python",
      "args": ["/home/TU_USUARIO/.local/opt/lancedb-hub/server_mcp.py"],
      "env": { "PYTHONUNBUFFERED": "1" }
    }
  }
}`,

  antigravity: `// ~/.gemini/config/mcp_config.json  (SYNRAG configure lo escribe solo)
// Cambia TU_USUARIO por tu nombre de usuario.
{
  "mcpServers": {
    "desktop-lancedb": {
      "command": "/home/TU_USUARIO/.local/opt/lancedb-hub/.venv/bin/python",
      "args": ["/home/TU_USUARIO/.local/opt/lancedb-hub/server_mcp.py"],
      "env": { "PYTHONUNBUFFERED": "1" }
    }
  }
}`,

  codex: `# ~/.codex/config.toml  (SYNRAG configure lo escribe solo)
# Cambia TU_USUARIO por tu nombre de usuario.
[mcp_servers.desktop-lancedb]
command = "/home/TU_USUARIO/.local/opt/lancedb-hub/.venv/bin/python"
args = ["/home/TU_USUARIO/.local/opt/lancedb-hub/server_mcp.py"]
env = { PYTHONUNBUFFERED = "1" }`
};
