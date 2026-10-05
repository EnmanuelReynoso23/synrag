export interface ASTResult {
  id: string;
  query: string;
  project: string;
  file: string;
  lines: string;
  symbol: string;
  kind: 'Hook' | 'Function' | 'Class' | 'Component' | 'Middleware';
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
    project: 'asistoya-web',
    file: 'src/services/asistenciaServicio.ts',
    lines: '45-89',
    symbol: 'useAsistenciaServicio',
    kind: 'Hook',
    language: 'typescript',
    code: `export const useAsistenciaServicio = (institucionId: string) => {
  const [registros, setRegistros] = useState<AsistenciaRecord[]>([]);
  const [cargando, setCargando] = useState(false);

  const registrarAsistencia = useCallback(async (datos: PayloadAsistencia) => {
    // Procesa el pase de lista con validación biométrica facial
    const resultado = await api.post(\`/asistencias/\${institucionId}\`, datos);
    setRegistros(prev => [resultado.data, ...prev]);
    return resultado.status === 200;
  }, [institucionId]);

  return { registros, cargando, registrarAsistencia };
};`,
    impactConsumers: [
      { file: 'src/features/asistencia/PaseDeLista.tsx', project: 'asistoya-web', risk: 'CRITICAL' },
      { file: 'src/components/KioskoBiometrico.tsx', project: 'asistoya-web', risk: 'CRITICAL' },
      { file: 'src/pages/ReportesMensuales.tsx', project: 'asistoya-web', risk: 'WARNING' },
      { file: 'src/features/monitor/MonitorTiempoReal.tsx', project: 'asistoya-web', risk: 'WARNING' },
      { file: 'src/hooks/useAuditoriaPase.ts', project: 'asistoya-web', risk: 'INFO' },
      { file: 'src/routes/AulaRouter.tsx', project: 'asistoya-web', risk: 'INFO' },
    ],
    score: 98.7,
    cacheHit: true,
    latencyMs: 0.38,
    tokensConsumed: 0,
    cost: '$0.00',
  },
  {
    id: 'chunker-ast',
    query: 'chunkerTreeSitter',
    project: 'syntaxrag-core',
    file: 'chunker.py',
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
      { file: 'test_chunker.py', project: 'syntaxrag-core', risk: 'INFO' },
      { file: 'cli.py', project: 'syntaxrag-core', risk: 'WARNING' },
    ],
    score: 99.4,
    cacheHit: true,
    latencyMs: 0.42,
    tokensConsumed: 0,
    cost: '$0.00',
  },
  {
    id: 'pase-lista',
    query: 'paseDeLista',
    project: 'asistoya-web',
    file: 'src/features/asistencia/PaseDeLista.tsx',
    lines: '18-52',
    symbol: 'PaseDeListaModal',
    kind: 'Component',
    language: 'typescript',
    code: `export const PaseDeListaModal: React.FC<PaseProps> = ({ aulaId, grupo }) => {
  const { registrarAsistencia, cargando } = useAsistenciaServicio(grupo.institucionId);
  const [estudiantes, setEstudiantes] = useState<Estudiante[]>([]);

  const handleMarcado = async (estudianteId: string, estado: AsistenciaEstado) => {
    await registrarAsistencia({ estudianteId, aulaId, estado, fecha: new Date() });
  };

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/90 p-6">
      <AsistenciaHeader grupo={grupo} />
      <AsistenciaTable data={estudiantes} onStatusChange={handleMarcado} loading={cargando} />
    </div>
  );
};`,
    impactConsumers: [
      { file: 'src/pages/DashboardProfesor.tsx', project: 'asistoya-web', risk: 'CRITICAL' },
      { file: 'src/features/aulas/AulaDetalleView.tsx', project: 'asistoya-web', risk: 'WARNING' },
      { file: 'src/routes/DocenteRoutes.tsx', project: 'asistoya-web', risk: 'INFO' },
    ],
    score: 96.8,
    cacheHit: false,
    latencyMs: 14.2,
    tokensConsumed: 0,
    cost: '$0.00',
  },
  {
    id: 'impact-graph',
    query: 'ImpactGraph',
    project: 'syntaxrag-core',
    file: 'impact.py',
    lines: '32-68',
    symbol: 'ImpactGraph',
    kind: 'Class',
    language: 'python',
    code: `class ImpactGraph:
    """Mapea la red de importaciones y llamadas entre módulos para prevenir código roto."""
    def __init__(self, db_path: Path):
        self.graph = nx.DiGraph()
        self._load_dependency_matrix(db_path)

    def find_consumers(self, symbol: str, file_path: str) -> list[ImpactWarning]:
        node_key = f"{file_path}:{symbol}"
        if node_key not in self.graph:
            return []
        dependents = list(self.graph.predecessors(node_key))
        return [
            ImpactWarning(
                caller=dep,
                risk="CRITICAL" if len(dependents) > 3 else "WARNING"
            )
            for dep in dependents
        ]`,
    impactConsumers: [
      { file: 'server_mcp.py', project: 'syntaxrag-core', risk: 'CRITICAL' },
      { file: 'cli.py', project: 'syntaxrag-core', risk: 'CRITICAL' },
      { file: 'indexer.py', project: 'syntaxrag-core', risk: 'WARNING' },
    ],
    score: 98.1,
    cacheHit: true,
    latencyMs: 0.29,
    tokensConsumed: 0,
    cost: '$0.00',
  },
  {
    id: 'auth-middleware',
    query: 'authMiddleware',
    project: 'asistoya-api',
    file: 'src/middleware/auth.ts',
    lines: '14-46',
    symbol: 'verifySessionToken',
    kind: 'Middleware',
    language: 'typescript',
    code: `export const verifySessionToken = async (req: Request, res: Response, next: NextFunction) => {
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) {
    return res.status(401).json({ error: 'No autorizado: Token ausente' });
  }
  
  try {
    const claims = await jwtVerifier.verify(token);
    req.user = { id: claims.sub, rol: claims.rol, institucionId: claims.tenant };
    next();
  } catch (err) {
    return res.status(403).json({ error: 'Token inválido o expirado' });
  }
};`,
    impactConsumers: [
      { file: 'src/routes/asistencias.ts', project: 'asistoya-api', risk: 'CRITICAL' },
      { file: 'src/routes/alumnos.ts', project: 'asistoya-api', risk: 'CRITICAL' },
      { file: 'src/routes/docentes.ts', project: 'asistoya-api', risk: 'CRITICAL' },
      { file: 'src/routes/reportes.ts', project: 'asistoya-api', risk: 'WARNING' },
    ],
    score: 97.4,
    cacheHit: false,
    latencyMs: 16.8,
    tokensConsumed: 0,
    cost: '$0.00',
  }
];

export const ARCHITECTURE_PIPELINE = [
  {
    id: 'agent',
    step: '01',
    name: 'Editor / Agente IA',
    tech: 'Claude Code · Antigravity CLI · Cursor',
    file: 'Entorno de Desarrollo',
    role: 'Envía peticiones de búsqueda semántica o diagnóstico de código mediante MCP stdio.',
    desc: 'El agente necesita conocer el contexto de una función o componente sin leer cientos de archivos ni saturar la ventana de contexto.',
    badge: 'Consumidor',
    color: '#89b4fa',
  },
  {
    id: 'mcp',
    step: '02',
    name: 'Servidor MCP Stdio',
    tech: 'desktop-lancedb (JSON-RPC)',
    file: 'server_mcp.py',
    role: 'Punto de entrada de alta velocidad que expone search_desktop y list_projects.',
    desc: 'Protocolo Model Context Protocol estándar. Gestiona llamadas atómicas, valida filtros de proyecto y entrega respuestas estructuradas al agente.',
    badge: 'Protocolo',
    color: '#cba6f7',
  },
  {
    id: 'cache',
    step: '03',
    name: 'Caché Semántico Local',
    tech: 'LanceDB query_cache (<1ms)',
    file: 'cache.py',
    role: 'Evalúa si la consulta ya fue resuelta previamente.',
    desc: 'Si hay coincidencia, retorna los fragmentos exactos en <1ms sin disparar re-indexación ni gastar un solo token ($0.00).',
    badge: '0 Tokens',
    color: '#00e5ff',
  },
  {
    id: 'ast',
    step: '04',
    name: 'Tree-sitter AST Chunker',
    tech: 'Gramáticas nativas TS, TSX, PY, Rust',
    file: 'chunker.py',
    role: 'Extracción semántica quirúrgica de funciones, hooks, clases e interfaces.',
    desc: 'A diferencia de los RAGs tradicionales que cortan texto por líneas arbitrarias, SyntaxRAG extrae únicamente bloques sintácticos íntegros.',
    badge: 'AST Native',
    color: '#a6e3a1',
  },
  {
    id: 'impact',
    step: '05',
    name: 'Grafo de Impacto',
    tech: 'NetworkX + LanceDB Edge Matrix',
    file: 'impact.py',
    role: 'Rastreo bidireccional de dependencias e importaciones.',
    desc: 'Identifica qué archivos consumen el símbolo encontrado. Si el agente intenta refactorizar, SyntaxRAG inyecta advertencias de riesgo para evitar código roto.',
    badge: 'Prevención',
    color: '#f38ba8',
  },
  {
    id: 'vector',
    step: '06',
    name: 'LanceDB Columnar Store',
    tech: 'LanceDB 0.25 Columnar (~49.8 MB)',
    file: 'indexer.py',
    role: 'Base de datos vectorial y relacional local de ultra-baja latencia.',
    desc: 'Almacena 95,597+ fragmentos con compresión columnar en disco, permitiendo búsquedas vectoriales y BM25 sin servidor externo ni consumo de RAM.',
    badge: 'Storage',
    color: '#fab387',
  },
  {
    id: 'ranker',
    step: '07',
    name: 'Reranker FlashRank ONNX',
    tech: 'ms-marco-TinyBERT-L-2-v2 (CPU)',
    file: 'ranker.py',
    role: 'Reordenamiento neural de alta precisión en CPU pura.',
    desc: 'Aplica inferencia de modelos transformadores compactos en milisegundos directamente en el procesador, sin requerir GPUs dedicadas.',
    badge: 'CPU Neural',
    color: '#f9e2af',
  },
];

export const ECOSYSTEM_METRICS = [
  { label: 'Archivos Indexados', value: '7,536+', unit: 'código fuente', icon: 'FileCode2', delta: '+100% monorepo' },
  { label: 'Fragmentos AST', value: '95,597+', unit: 'funciones y hooks', icon: 'Code', delta: 'Bloques íntegros' },
  { label: 'Vínculos de Impacto', value: '23,364+', unit: 'dependencias cruzadas', icon: 'GitFork', delta: 'Prevención de roturas' },
  { label: 'Hot-Reload (Ctrl+S)', value: '~18 ms', unit: 'por guardado reactivo', icon: 'Zap', delta: 'Demonio systemd' },
  { label: 'Caché Hit Latencia', value: '< 1 ms', unit: 'tiempo de respuesta', icon: 'Cpu', delta: '0 Tokens · $0.00' },
  { label: 'Tamaño en Disco', value: '~49.8 MB', unit: 'LanceDB columnar', icon: 'HardDrive', delta: 'Cero overhead' },
];

export const CONFIG_SNIPPETS = {
  claude: `{
  "mcpServers": {
    "desktop-lancedb": {
      "type": "stdio",
      "command": "/home/reyno/.local/bin/lancedb-mcp",
      "args": [],
      "env": {}
    }
  }
}`,
  antigravity: `{
  "mcpServers": {
    "desktop-lancedb": {
      "command": "/home/reyno/.local/bin/lancedb-mcp",
      "args": []
    }
  }
}`,
  cli: `# Búsqueda semántica AST directa
syntaxrag "asistenciaServicio"

# Filtrar por un proyecto del monorepo
syntaxrag --project asistoya-web "paseDeLista"

# Diagnóstico de arquitectura y métricas
syntaxrag info
syntaxrag stats

# Monitor en vivo del demonio de guardado (Ctrl+S)
syntaxrag watch`,
  systemd: `# Estado del monitor reactivo en segundo plano
systemctl --user status lancedb-watcher.service

# Ver logs de eventos reactivos en tiempo real
journalctl --user -u lancedb-watcher.service -f`,
};
