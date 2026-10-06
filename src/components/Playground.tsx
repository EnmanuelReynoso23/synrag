import { useState, useMemo } from 'react';
import { SAMPLE_QUERIES, type ASTResult } from '../data/mockData';
import { Search, ShieldAlert, Check, Copy, FileCode2, Network, GitFork, Info } from 'lucide-react';

type ViewMode = 'code' | 'ast-tree' | 'impact-graph';

interface ASTNode {
  type: string;
  name?: string;
  lines: string;
  tokens: number;
  depth: number;
  children?: ASTNode[];
}

export const Playground: React.FC = () => {
  const [selectedResult, setSelectedResult] = useState<ASTResult>(SAMPLE_QUERIES[0]);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('code');
  const [copied, setCopied] = useState(false);
  const [selectedGraphNode, setSelectedGraphNode] = useState<string | null>(null);

  // Filtrado reactivo de consultas
  const filteredQueries = useMemo(() => {
    if (!searchQuery.trim()) return SAMPLE_QUERIES;
    const q = searchQuery.toLowerCase();
    return SAMPLE_QUERIES.filter(
      (item) =>
        item.query.toLowerCase().includes(q) ||
        item.symbol.toLowerCase().includes(q) ||
        item.file.toLowerCase().includes(q) ||
        item.label.toLowerCase().includes(q)
    );
  }, [searchQuery]);

  const handleSelectQuery = (item: ASTResult) => {
    setSelectedResult(item);
    setSelectedGraphNode(null);
  };

  const copyCode = () => {
    navigator.clipboard.writeText(selectedResult.code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Mock de arbol sintactico Tree-sitter para el simbolo activo
  const astTreeNodes: ASTNode[] = useMemo(() => {
    return [
      {
        type: 'Program',
        lines: selectedResult.lines,
        tokens: 184,
        depth: 0,
        children: [
          {
            type: 'ExportNamedDeclaration',
            name: 'export',
            lines: selectedResult.lines,
            tokens: 172,
            depth: 1,
            children: [
              {
                type: 'VariableDeclaration',
                name: 'const',
                lines: selectedResult.lines,
                tokens: 168,
                depth: 2,
                children: [
                  {
                    type: 'VariableDeclarator',
                    name: selectedResult.symbol,
                    lines: selectedResult.lines,
                    tokens: 165,
                    depth: 3,
                    children: [
                      {
                        type: 'ObjectExpression',
                        name: '{ ... }',
                        lines: selectedResult.lines,
                        tokens: 160,
                        depth: 4,
                        children: [
                          {
                            type: 'MethodDefinition',
                            name: 'registrarPase()',
                            lines: '36-43',
                            tokens: 95,
                            depth: 5,
                          },
                          {
                            type: 'MethodDefinition',
                            name: 'obtenerResumenDiario()',
                            lines: '44-48',
                            tokens: 65,
                            depth: 5,
                          },
                        ],
                      },
                    ],
                  },
                ],
              },
            ],
          },
        ],
      },
    ];
  }, [selectedResult]);

  return (
    <section id="playground" className="scroll-mt-20 border-b border-[#30363D] bg-[#0D1117] py-16 sm:py-24 relative overflow-hidden">
      {/* Background radial glow */}
      <div className="absolute top-1/4 right-1/3 w-[600px] h-[350px] bg-[#00E5FF]/5 blur-[140px] rounded-full pointer-events-none" />

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Encabezado */}
        <div className="text-center max-w-3xl mx-auto">
          <p className="text-xs font-mono font-bold uppercase tracking-[0.2em] text-[#00E5FF] flex items-center justify-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00E5FF] animate-pulse" />
            SIMULADOR INTERACTIVO · DATOS DE EJEMPLO
          </p>
          <h2 className="mt-3 text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight text-white">
            Explorador AST y Grafo de Impacto
          </h2>
          <p className="mt-3 text-sm sm:text-base text-[#8B949E]">
            Comprueba cómo el motor Tree-sitter descompone quirúrgicamente el código en bloques sintácticos, analiza el árbol de tipos y calcula el blast radius de dependencias antes de inyectar contexto a los agentes.
          </p>
        </div>

        {/* Barra de Búsqueda y Filtros de Consulta */}
        <div className="mt-10 max-w-3xl mx-auto space-y-4">
          {/* Input de búsqueda interactiva */}
          <div className="relative flex items-center rounded-2xl border border-[#30363D] bg-[#161B22] p-2 shadow-xl focus-within:border-[#00E5FF] focus-within:ring-2 focus-within:ring-[#00E5FF]/20 transition-all">
            <Search className="w-5 h-5 text-[#8B949E] ml-3 shrink-0" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar función, hook, clase o módulo en el monorepo (ej: asistencia, facial, hook)..."
              className="w-full bg-transparent px-3 py-2 text-sm font-mono text-white placeholder-[#8B949E] focus:outline-none"
            />
            <span className="hidden sm:inline-flex items-center px-2.5 py-1 rounded-lg bg-[#21262D] text-xs font-mono font-bold text-[#00E5FF] mr-1 border border-[#30363D]">
              LanceDB Index
            </span>
          </div>

          {/* Selector de consultas de ejemplo */}
          <div className="flex flex-wrap items-center justify-center gap-2">
            <span className="text-xs font-mono text-[#8B949E] mr-1">Módulos disponibles:</span>
            {filteredQueries.map((item) => (
              <button
                key={item.id}
                onClick={() => handleSelectQuery(item)}
                className={`px-3 py-1.5 rounded-xl text-xs font-mono font-bold transition-all cursor-pointer ${
                  selectedResult.id === item.id
                    ? 'bg-[#00E5FF] text-[#0D1117] shadow-[0_0_15px_-3px_rgba(0,229,255,0.4)]'
                    : 'bg-[#161B22] border border-[#30363D] text-[#8B949E] hover:text-white hover:border-[#8B949E]'
                }`}
              >
                {item.query}
              </button>
            ))}
          </div>
        </div>

        {/* Panel Dividido: Visor AST y Alerta de Grafo */}
        <div className="mt-10 grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Lado Izquierdo: Visor con 3 Pestañas (7 Cols) */}
          <div className="lg:col-span-7 rounded-2xl border border-[#30363D] bg-[#161B22] shadow-2xl overflow-hidden flex flex-col">
            {/* Cabecera del archivo con Selector de Vistas */}
            <div className="p-4 bg-[#0D1117] border-b border-[#30363D] flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <FileCode2 className="w-5 h-5 text-[#00E5FF]" />
                <div>
                  <h4 className="font-mono text-xs sm:text-sm font-bold text-white">
                    {selectedResult.file}
                  </h4>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[11px] font-mono text-[#8B949E]">
                      Líneas {selectedResult.lines}
                    </span>
                    <span className="text-[#30363D]">·</span>
                    <span className="text-[11px] font-mono text-[#00E5FF]">
                      {selectedResult.symbol}
                    </span>
                  </div>
                </div>
              </div>

              {/* Selector de Modos de Vista */}
              <div className="flex rounded-xl bg-[#161B22] p-1 border border-[#30363D]">
                <button
                  onClick={() => setViewMode('code')}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono font-bold transition-all cursor-pointer ${
                    viewMode === 'code'
                      ? 'bg-[#21262D] text-[#00E5FF] border border-[#00E5FF]/40 shadow-sm'
                      : 'text-[#8B949E] hover:text-white'
                  }`}
                >
                  <FileCode2 className="w-3.5 h-3.5" />
                  <span>Código</span>
                </button>

                <button
                  onClick={() => setViewMode('ast-tree')}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono font-bold transition-all cursor-pointer ${
                    viewMode === 'ast-tree'
                      ? 'bg-[#21262D] text-[#00E5FF] border border-[#00E5FF]/40 shadow-sm'
                      : 'text-[#8B949E] hover:text-white'
                  }`}
                >
                  <Network className="w-3.5 h-3.5" />
                  <span>Árbol AST</span>
                </button>

                <button
                  onClick={() => setViewMode('impact-graph')}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono font-bold transition-all cursor-pointer ${
                    viewMode === 'impact-graph'
                      ? 'bg-[#21262D] text-[#00E5FF] border border-[#00E5FF]/40 shadow-sm'
                      : 'text-[#8B949E] hover:text-white'
                  }`}
                >
                  <GitFork className="w-3.5 h-3.5" />
                  <span>Grafo SVG</span>
                </button>
              </div>
            </div>

            {/* Contenedor del Cuerpo según Pestaña */}
            <div className="relative min-h-[360px] bg-[#0D1117]">
              {/* VISTA 1: Codigo Fuente */}
              {viewMode === 'code' && (
                <div className="p-4 sm:p-5 text-slate-100 overflow-x-auto">
                  <button
                    onClick={copyCode}
                    className="absolute top-4 right-4 flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#21262D] hover:bg-[#30363D] text-[#8B949E] hover:text-white text-xs font-mono font-bold border border-[#30363D] transition-colors cursor-pointer"
                    title="Copiar bloque de código AST"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-[#7EE787]" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? 'Copiado' : 'Copiar'}</span>
                  </button>

                  <pre className="font-mono text-xs sm:text-sm leading-relaxed text-slate-200 pr-16">
                    <code>{selectedResult.code}</code>
                  </pre>
                </div>
              )}

              {/* VISTA 2: Arbol AST Tree-sitter */}
              {viewMode === 'ast-tree' && (
                <div className="p-5 font-mono text-xs space-y-3 overflow-x-auto">
                  <div className="text-[11px] text-[#8B949E] pb-2 border-b border-[#21262D] flex justify-between">
                    <span>JERARQUÍA DE NODOS TREE-SITTER</span>
                    <span className="text-[#00E5FF]">TS-GRAMMAR v0.20</span>
                  </div>

                  {/* Renderizado de Arbol Jerarquico */}
                  <div className="space-y-2">
                    {function renderNode(node: ASTNode, key: string): React.ReactNode {
                      return (
                        <div key={key} style={{ paddingLeft: `${node.depth * 18}px` }} className="space-y-1">
                          <div className="flex items-center gap-2 py-1 px-2 rounded-lg bg-[#161B22]/80 border border-[#30363D]/60 hover:border-[#00E5FF]/50 transition-colors">
                            <span className="text-[#00E5FF] font-bold">└─</span>
                            <span className="text-[#58A6FF] font-bold">{node.type}</span>
                            {node.name && (
                              <span className="text-[#7EE787] bg-[#21262D] px-1.5 py-0.5 rounded text-[10px]">
                                {node.name}
                              </span>
                            )}
                            <span className="text-[#8B949E] text-[10px] ml-auto">
                              Líneas {node.lines} · {node.tokens} tok
                            </span>
                          </div>
                          {node.children && node.children.map((child, idx) => renderNode(child, `${key}-${idx}`))}
                        </div>
                      );
                    }(astTreeNodes[0], 'root')}
                  </div>
                </div>
              )}

              {/* VISTA 3: Grafo Visual SVG */}
              {viewMode === 'impact-graph' && (
                <div className="p-6 flex flex-col items-center justify-center min-h-[360px]">
                  <div className="text-xs font-mono text-[#8B949E] mb-3 text-center">
                    MAPA DE DEPENDENCIAS DIRECTAS · CLICK EN UN NODO PARA DETALLE
                  </div>

                  <svg viewBox="0 0 500 240" className="w-full max-w-lg h-auto overflow-visible">
                    {/* Lineas de conexion */}
                    <line x1="250" y1="120" x2="80" y2="40" stroke="#FF7B72" strokeWidth="2" strokeDasharray="3 3" opacity="0.8" />
                    <line x1="250" y1="120" x2="420" y2="40" stroke="#FF7B72" strokeWidth="2" strokeDasharray="3 3" opacity="0.8" />
                    <line x1="250" y1="120" x2="80" y2="200" stroke="#E3B341" strokeWidth="2" strokeDasharray="3 3" opacity="0.8" />
                    <line x1="250" y1="120" x2="420" y2="200" stroke="#58A6FF" strokeWidth="2" strokeDasharray="3 3" opacity="0.8" />

                    {/* Nodo Central (Símbolo consultado) */}
                    <g className="cursor-pointer" onClick={() => setSelectedGraphNode(selectedResult.symbol)}>
                      <circle cx="250" cy="120" r="28" fill="#0D1117" stroke="#00E5FF" strokeWidth="3" />
                      <circle cx="250" cy="120" r="34" fill="none" stroke="#00E5FF" strokeWidth="1.5" strokeDasharray="4 4" opacity="0.6" />
                      <text x="250" y="124" textAnchor="middle" fill="#FFFFFF" fontSize="10" fontWeight="bold" fontFamily="monospace">
                        ORIGEN
                      </text>
                    </g>

                    {/* Nodo 1: Critico Superior Izq */}
                    <g className="cursor-pointer" onClick={() => setSelectedGraphNode(selectedResult.impactConsumers[0]?.file || 'Consumer 1')}>
                      <circle cx="80" cy="40" r="18" fill="#161B22" stroke="#FF7B72" strokeWidth="2" />
                      <text x="80" y="44" textAnchor="middle" fill="#FF7B72" fontSize="9" fontWeight="bold" fontFamily="monospace">
                        CRIT
                      </text>
                    </g>

                    {/* Nodo 2: Critico Superior Der */}
                    <g className="cursor-pointer" onClick={() => setSelectedGraphNode(selectedResult.impactConsumers[1]?.file || 'Consumer 2')}>
                      <circle cx="420" cy="40" r="18" fill="#161B22" stroke="#FF7B72" strokeWidth="2" />
                      <text x="420" y="44" textAnchor="middle" fill="#FF7B72" fontSize="9" fontWeight="bold" fontFamily="monospace">
                        CRIT
                      </text>
                    </g>

                    {/* Nodo 3: Advertencia Inferior Izq */}
                    <g className="cursor-pointer" onClick={() => setSelectedGraphNode(selectedResult.impactConsumers[2]?.file || 'Consumer 3')}>
                      <circle cx="80" cy="200" r="18" fill="#161B22" stroke="#E3B341" strokeWidth="2" />
                      <text x="80" y="204" textAnchor="middle" fill="#E3B341" fontSize="9" fontWeight="bold" fontFamily="monospace">
                        WARN
                      </text>
                    </g>

                    {/* Nodo 4: Info Inferior Der */}
                    <g className="cursor-pointer" onClick={() => setSelectedGraphNode(selectedResult.impactConsumers[3]?.file || 'Consumer 4')}>
                      <circle cx="420" cy="200" r="18" fill="#161B22" stroke="#58A6FF" strokeWidth="2" />
                      <text x="420" y="204" textAnchor="middle" fill="#58A6FF" fontSize="9" fontWeight="bold" fontFamily="monospace">
                        INFO
                      </text>
                    </g>
                  </svg>

                  {selectedGraphNode && (
                    <div className="mt-3 p-2.5 rounded-xl bg-[#161B22] border border-[#30363D] text-xs font-mono text-center">
                      <span className="text-[#8B949E]">Nodo seleccionado: </span>
                      <span className="text-[#00E5FF] font-bold">{selectedGraphNode}</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Barra de métricas inferiores */}
            <div className="p-4 bg-[#0D1117] border-t border-[#30363D] flex flex-wrap items-center justify-between text-xs font-mono font-bold text-[#8B949E] gap-3">
              <div className="flex items-center gap-2">
                <span>Puntuación FlashRank (ejemplo):</span>
                <span className="text-[#00E5FF]">{selectedResult.score}%</span>
                <div className="w-16 bg-[#21262D] rounded-full h-1.5 overflow-hidden">
                  <div className="bg-[#00E5FF] h-1.5 rounded-full" style={{ width: `${selectedResult.score}%` }} />
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[#7EE787] bg-[#7EE787]/10 px-2 py-0.5 rounded border border-[#7EE787]/20">
                  {`${selectedResult.latencyMs} ms${selectedResult.cacheHit ? ' (caché)' : ''}`}
                </span>
                <span className="text-[#8B949E]">
                  Costo de la búsqueda: $0.00
                </span>
              </div>
            </div>
          </div>

          {/* Lado Derecho: Alerta de Grafo de Impacto (5 Cols) */}
          <div className="lg:col-span-5 space-y-4">
            {/* Tarjeta de Advertencia Preventiva */}
            <div className="rounded-2xl border border-[#FF7B72]/30 bg-[#FF7B72]/10 p-5 shadow-xl">
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-xl bg-[#FF7B72]/20 text-[#FF7B72] shrink-0">
                  <ShieldAlert className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="font-bold text-sm text-white">
                    Alerta del Grafo de Impacto
                  </h4>
                  <p className="mt-1 text-xs text-[#8B949E] leading-relaxed">
                    {selectedResult.impactConsumers.length} archivo(s) en <span className="font-mono text-white font-bold">{selectedResult.project}</span> dependen directamente de este símbolo. Si el agente o programador modifica su firma, se inyectan advertencias inmediatas antes de romper el monorepo.
                  </p>
                </div>
              </div>
            </div>

            {/* Lista de Consumidores con Nivel de Riesgo */}
            <div className="rounded-2xl border border-[#30363D] bg-[#161B22] p-5 shadow-xl">
              <div className="flex items-center justify-between mb-3">
                <h5 className="text-xs font-mono font-bold uppercase tracking-wider text-[#8B949E]">
                  Consumidores Mapeados ({selectedResult.impactConsumers.length}):
                </h5>
                <span className="text-[11px] font-mono text-[#00E5FF] flex items-center gap-1">
                  <Info className="w-3 h-3" />
                  Mapa de dependencias
                </span>
              </div>

              <ul className="space-y-2 max-h-[260px] overflow-y-auto pr-1">
                {selectedResult.impactConsumers.map((consumer, idx) => (
                  <li 
                    key={idx}
                    className="flex items-center justify-between p-2.5 rounded-xl bg-[#0D1117] border border-[#30363D] hover:border-[#8B949E] transition-colors"
                  >
                    <span className="font-mono text-xs text-slate-300 truncate pr-2">
                      {consumer.file}
                    </span>
                    <span className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded-full shrink-0 ${
                      consumer.risk === 'CRITICAL'
                        ? 'bg-[#FF7B72]/15 text-[#FF7B72] border border-[#FF7B72]/30'
                        : consumer.risk === 'WARNING'
                          ? 'bg-[#E3B341]/15 text-[#E3B341] border border-[#E3B341]/30'
                          : 'bg-[#58A6FF]/15 text-[#58A6FF] border border-[#58A6FF]/30'
                    }`}>
                      {consumer.risk}
                    </span>
                  </li>
                ))}
              </ul>

              <div className="mt-4 pt-3 border-t border-[#30363D] flex items-center justify-between text-xs font-mono text-[#8B949E]">
                <span>Relaciones en el índice del autor:</span>
                <span className="text-white font-bold">23,704 (6-oct-2026)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
