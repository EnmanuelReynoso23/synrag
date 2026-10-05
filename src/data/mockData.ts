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
    project: 'asistoya-web',
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
      { file: 'apps/web/src/demo/demoData.ts', project: 'asistoya-web', risk: 'CRITICAL' },
      { file: 'apps/web/src/modulos/asistencia/asistencia.hook.ts', project: 'asistoya-web', risk: 'CRITICAL' },
      { file: 'apps/web/src/modulos/administrador/componentes/PanelAsistencia.tsx', project: 'asistoya-web', risk: 'CRITICAL' },
      { file: 'apps/web/src/modulos/kiosco/PaginaKioscoPublica.tsx', project: 'asistoya-web', risk: 'WARNING' },
      { file: 'apps/web/src/modulos/profesor/componentes/PaseDeLista.tsx', project: 'asistoya-web', risk: 'CRITICAL' },
      { file: 'apps/web/src/services/analytics/eventos.ts', project: 'asistoya-web', risk: 'INFO' },
      { file: 'apps/web/src/modulos/padre/componentes/HistorialHijo.tsx', project: 'asistoya-web', risk: 'WARNING' },
      { file: 'apps/web/src/modulos/reportes/exportadorAsistencia.ts', project: 'asistoya-web', risk: 'INFO' },
    ],
    score: 99.2,
    cacheHit: true,
    latencyMs: 0.38,
    tokensConsumed: 0,
    cost: '$0.00',
  },
  {
    id: 'reconocimiento-facial',
    query: 'reconocimientoFacial',
    label: 'Algoritmo Biométrico Escolar',
    project: 'asistoya-web',
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
      { file: 'apps/web/src/modulos/kiosco/TerminalBiometrico.tsx', project: 'asistoya-web', risk: 'CRITICAL' },
      { file: 'apps/web/src/modulos/reconocimiento-facial/componentes/CamaraCaptura.tsx', project: 'asistoya-web', risk: 'CRITICAL' },
      { file: 'apps/web/src/services/face/faceService.ts', project: 'asistoya-web', risk: 'WARNING' },
    ],
    score: 98.7,
    cacheHit: true,
    latencyMs: 0.45,
    tokensConsumed: 0,
    cost: '$0.00',
  },
  {
    id: 'use-estudiantes',
    query: 'useEstudiantes',
    label: 'Hook de Estado React',
    project: 'asistoya-web',
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
      { file: 'apps/web/src/modulos/profesor/componentes/PaseDeLista.tsx', project: 'asistoya-web', risk: 'CRITICAL' },
      { file: 'apps/web/src/modulos/calificaciones/componentes/TablaNotas.tsx', project: 'asistoya-web', risk: 'CRITICAL' },
      { file: 'apps/web/src/modulos/reportes/ReporteSeccion.tsx', project: 'asistoya-web', risk: 'WARNING' },
    ],
    score: 97.9,
    cacheHit: false,
    latencyMs: 16.4,
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
    latencyMs: 0.31,
    tokensConsumed: 0,
    cost: '$0.00',
  }
];

export const ARCHITECTURE_PIPELINE = [
  {
    id: 'agent',
    step: '01',
    name: 'Editor / Agente IA',
    tech: 'Antigravity CLI · Claude Code · Herdr Hub',
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
    desc: 'Protocolo nativo que conecta al agente con la base vectorial local a velocidad casi instantánea.',
    badge: 'Protocolo',
    color: '#58A6FF',
  },
  {
    id: 'cache',
    step: '03',
    name: 'Zero-Token Semantic Cache',
    tech: 'LanceDB query_cache (<1ms)',
    file: 'cache.py',
    role: 'Retorno instantáneo de consultas previas a costo $0.',
    desc: 'Detecta consultas semánticamente equivalentes y responde en menos de 1ms, ahorrando 100% de tokens de API.',
    badge: '0 Tokens',
    color: '#7EE787',
  },
  {
    id: 'ast',
    step: '04',
    name: 'Tree-sitter AST Chunker',
    tech: 'Gramáticas nativas TS, TSX, JS, Python',
    file: 'chunker.py',
    role: 'Extracción sintáctica de funciones, hooks, clases y tipos.',
    desc: '0 fragmentos partidos a ciegas; conserva firmas completas, cuerpo de código y docstrings sin recortar.',
    badge: 'AST Native',
    color: '#00E5FF',
  },
  {
    id: 'impact',
    step: '05',
    name: 'Grafo de Impacto Bidireccional',
    tech: 'NetworkX + Matriz de Dependencias (23,364 aristas)',
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
    tech: 'LanceDB 0.25 (Disco columnar ~49.8 MB)',
    file: 'indexer.py',
    role: 'Almacenamiento e indexación local ultra-rápida.',
    desc: 'Almacena 95,502 fragmentos sintácticos con compresión columnar y búsqueda BM25 sin consumir memoria RAM.',
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
    desc: 'Reordena semánticamente los candidatos con modelos transformadores compactos en CPU sin requerir GPU.',
    badge: 'CPU Neural',
    color: '#00E5FF',
  },
];

export const ECOSYSTEM_METRICS = [
  { label: 'Fragmentos AST Indexados', value: '95,502', unit: 'bloques sintácticos íntegros', delta: 'Funciones, hooks y clases' },
  { label: 'Latencia en Caché Semántica', value: '< 1 ms', unit: 'tiempo de respuesta local', delta: '0 Tokens · $0.00 gasto' },
  { label: 'Ahorro de Cuota de API', value: '100% $0', unit: 'evitado en consultas repetidas', delta: 'Zero-Token Cache activo' },
  { label: 'Aristas en Grafo de Impacto', value: '23,364', unit: 'dependencias mapeadas', delta: 'Prevención de roturas' },
  { label: 'Hot-Reload por Guardado', value: '~18 ms', unit: 're-indexado reactivo (Ctrl+S)', delta: 'Demonio systemd activo' },
  { label: 'Archivos Monitoreados', value: '7,536+', unit: 'código fuente en monorepo', delta: 'asistoya-web y satélites' },
];

export const PROYECTOS_DISTRIBUCION = [
  { nombre: 'asistoya-web', chunks: 22923, porcentaje: 24.0, descripcion: 'Monorepo principal (Portal Web, Kiosco y Módulos)' },
  { nombre: 'asistoya-local', chunks: 16157, porcentaje: 16.9, descripcion: 'Servicios de sincronización y base local' },
  { nombre: 'respaldo-personal', chunks: 11075, porcentaje: 11.6, descripcion: 'Componentes y scripts de soporte' },
  { nombre: 'jev-mario64', chunks: 10365, porcentaje: 10.8, descripcion: 'Ecosistema de juegos y gamificación' },
  { nombre: 'AsistoYa', chunks: 7462, porcentaje: 7.8, descripcion: 'Servicios legados y librerías base' },
  { nombre: 'asistoya-empresas', chunks: 5856, porcentaje: 6.1, descripcion: 'Portal de empresas y proveedores' },
  { nombre: 'Vision-Humana', chunks: 3758, porcentaje: 3.9, descripcion: 'Motor de biometría y visión artificial' },
];

export const CONFIG_SNIPPETS = {
  synrag: `# Abrir el espacio de trabajo completo (Dark Mode + Live Stats)
SYNRAG

# Búsqueda semántica AST inteligente
SYNRAG "asistenciaServicio"

# Búsqueda acotada al monorepo de AsistoYA
SYNRAG --project asistoya-web "reconocimientoFacial"

# Ver métricas de ahorro y tokens evitados
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

  antigravity: `// ~/.gemini/antigravity/mcp_config.json  (SYNRAG configure lo escribe solo)
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

  fish: `# Abreviaturas rápidas en tu terminal Fish:
srag "asistenciaServicio"    # Búsqueda rápida
sstats                      # Métricas de ahorro
swatch                      # Log en vivo
sinfo                       # Dashboard de arquitectura`
};
