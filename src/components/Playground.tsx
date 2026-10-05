import { useState } from 'react';
import { Search, Zap, ShieldAlert, Cpu, Sparkles, Copy, Check, CornerDownRight, RefreshCw, Terminal } from 'lucide-react';
import { SAMPLE_QUERIES, type ASTResult } from '../data/mockData';



export const Playground: React.FC = () => {
  const [selectedResult, setSelectedResult] = useState<ASTResult>(SAMPLE_QUERIES[0]);
  const [searchTerm, setSearchTerm] = useState(SAMPLE_QUERIES[0].query);
  const [selectedProject, setSelectedProject] = useState<string>('todos');
  const [forceCache, setForceCache] = useState<boolean>(true);
  const [copiedCode, setCopiedCode] = useState<boolean>(false);
  const [inspectingCaller, setInspectingCaller] = useState<string | null>(null);

  const handleSelectQuery = (item: ASTResult) => {
    setSelectedResult(item);
    setSearchTerm(item.query);
    setInspectingCaller(null);
  };

  const copyResultCode = () => {
    navigator.clipboard.writeText(selectedResult.code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  // Filter queries based on selected project
  const filteredSamples = SAMPLE_QUERIES.filter(item => {
    if (selectedProject === 'todos') return true;
    return item.project === selectedProject;
  });

  return (
    <section id="playground" className="py-20 md:py-32 relative">
      {/* Background neon accents */}
      <div className="absolute top-1/3 right-10 w-96 h-96 bg-[#00e5ff]/10 blur-[130px] rounded-full pointer-events-none -z-10" />
      <div className="absolute bottom-10 left-10 w-80 h-80 bg-[#cba6f7]/10 blur-[120px] rounded-full pointer-events-none -z-10" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#181825] border border-[#313244] text-xs font-mono text-[#00e5ff] mb-4">
            <Sparkles className="w-3.5 h-3.5" />
            PLAYGROUND INTERACTIVO
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mb-4">
            Simulador de Búsqueda AST y Grafo de Impacto
          </h2>
          <p className="text-sm sm:text-base text-[#a6adc8]">
            Prueba cómo interactúa un agente de IA con SyntaxRAG. Observa la extracción quirúrgica de fragmentos, el caché semántico instantáneo y la red de protección de dependencias.
          </p>
        </div>

        {/* Search Controls Card */}
        <div className="p-4 sm:p-6 rounded-2xl bg-[#181825] border border-[#313244] mb-8 shadow-lg">
          <div className="flex flex-col md:flex-row items-center gap-4">
            {/* Search Input */}
            <div className="relative flex-1 w-full">
              <Search className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-[#8b949e]" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Escribe un símbolo (ej: asistenciaServicio, ImpactGraph)..."
                className="w-full pl-11 pr-4 py-3 rounded-xl bg-[#11111b] border border-[#313244] focus:border-[#00e5ff] focus:outline-none text-sm font-mono text-white placeholder-[#585b70] transition-colors"
              />
            </div>

            {/* Project Filter */}
            <div className="w-full md:w-56">
              <select
                value={selectedProject}
                onChange={(e) => setSelectedProject(e.target.value)}
                className="w-full px-3.5 py-3 rounded-xl bg-[#11111b] border border-[#313244] focus:border-[#00e5ff] text-xs font-mono text-[#cdd6f4] focus:outline-none transition-colors"
              >
                <option value="todos">Todos los proyectos</option>
                <option value="asistoya-web">asistoya-web</option>
                <option value="syntaxrag-core">syntaxrag-core</option>
                <option value="asistoya-api">asistoya-api</option>
              </select>
            </div>

            {/* Cache Toggle */}
            <div className="w-full md:w-auto flex items-center justify-between md:justify-start gap-3 px-4 py-2.5 rounded-xl bg-[#11111b] border border-[#313244]">
              <span className="text-xs font-mono text-[#a6adc8]">Caché Semántico:</span>
              <button
                onClick={() => setForceCache(!forceCache)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors cursor-pointer ${
                  forceCache ? 'bg-[#00e5ff]' : 'bg-[#313244]'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    forceCache ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>

          {/* Quick Query Pills */}
          <div className="mt-4 pt-4 border-t border-[#313244]/60 flex flex-wrap items-center gap-2">
            <span className="text-xs text-[#585b70] font-mono mr-1">Consultas rápidas:</span>
            {filteredSamples.map((item) => (
              <button
                key={item.id}
                onClick={() => handleSelectQuery(item)}
                className={`px-3 py-1 rounded-lg text-xs font-mono transition-all cursor-pointer flex items-center gap-1.5 ${
                  selectedResult.id === item.id
                    ? 'bg-[#00e5ff]/20 text-[#00e5ff] border border-[#00e5ff]/50 font-medium shadow-[0_0_10px_-2px_rgba(0,229,255,0.4)]'
                    : 'bg-[#11111b] text-[#a6adc8] border border-[#313244] hover:text-white hover:border-[#45475a]'
                }`}
              >
                <Terminal className="w-3 h-3" />
                <span>{item.query}</span>
                <span className="text-[10px] text-[#585b70] font-sans">({item.project})</span>
              </button>
            ))}
          </div>
        </div>

        {/* Results Layout: 2 Columns on Desktop */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Code & AST Chunk (7 cols) */}
          <div className="lg:col-span-7 flex flex-col rounded-2xl bg-[#11111b] border border-[#313244] overflow-hidden shadow-xl">
            {/* Terminal Header Bar */}
            <div className="px-4 py-3 bg-[#181825] border-b border-[#313244] flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-[#f38ba8]/90"></span>
                <span className="w-3 h-3 rounded-full bg-[#f9e2af]/90"></span>
                <span className="w-3 h-3 rounded-full bg-[#a6e3a1]/90"></span>
                <span className="ml-2 font-mono text-xs text-[#89b4fa]">
                  {selectedResult.project} / {selectedResult.file}
                </span>
                <span className="font-mono text-xs text-[#585b70]">:{selectedResult.lines}</span>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#313244] text-[#cba6f7]">
                  {selectedResult.kind}
                </span>
                <button
                  onClick={copyResultCode}
                  className="p-1.5 rounded-md hover:bg-[#313244] text-[#a6adc8] hover:text-white transition-colors cursor-pointer"
                  title="Copiar fragmento AST"
                >
                  {copiedCode ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            {/* Performance telemetry pill */}
            <div className="px-4 py-2.5 bg-[#161b22] border-b border-[#30363d] flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
              <div className="flex items-center gap-3">
                {forceCache ? (
                  <span className="flex items-center gap-1.5 text-[#00e5ff] font-bold">
                    <Zap className="w-3.5 h-3.5" /> CACHE HIT
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5 text-[#fab387]">
                    <RefreshCw className="w-3.5 h-3.5" /> TANTIVY + FLASHRANK
                  </span>
                )}
                <span className="text-[#a6adc8]">
                  Latencia: <strong className="text-white">{forceCache ? selectedResult.latencyMs : (selectedResult.latencyMs * 18).toFixed(1)} ms</strong>
                </span>
              </div>

              <div className="flex items-center gap-3 text-[#a6adc8]">
                <span>Tokens: <strong className="text-[#a6e3a1]">0</strong></span>
                <span>Costo: <strong className="text-[#a6e3a1]">$0.00</strong></span>
                <span className="text-[#f9e2af]">Neural: <strong>{selectedResult.score}%</strong></span>
              </div>
            </div>

            {/* Code Block */}
            <div className="p-4 sm:p-6 overflow-x-auto font-mono text-xs sm:text-sm leading-relaxed text-[#cdd6f4] flex-1 bg-[#0d1117]">
              <pre className="overflow-x-auto">
                <code>
                  {selectedResult.code.split('\n').map((line, idx) => (
                    <div key={idx} className="flex gap-4 hover:bg-slate-800/30 px-1 py-0.5 rounded">
                      <span className="text-[#585b70] select-none w-6 text-right shrink-0">
                        {parseInt(selectedResult.lines.split('-')[0]) + idx}
                      </span>
                      <span className="text-[#cdd6f4]">{line}</span>
                    </div>
                  ))}
                </code>
              </pre>
            </div>
          </div>

          {/* Right Column: Impact Graph & Risk Inspector (5 cols) */}
          <div className="lg:col-span-5 flex flex-col gap-5">
            {/* Impact Warning Card */}
            <div className="p-5 rounded-2xl bg-[#181825] border border-[#f38ba8]/30 shadow-lg relative overflow-hidden">
              <div className="flex items-start gap-3 mb-3">
                <div className="p-2 rounded-xl bg-red-950/60 border border-red-500/30 text-red-400 shrink-0">
                  <ShieldAlert className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                    Grafo de Impacto Activo
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-500/20 text-red-300 font-mono">
                      {selectedResult.impactConsumers.length} Consumidores
                    </span>
                  </h3>
                  <p className="text-xs text-[#a6adc8] mt-1">
                    Tree-sitter mapeó estas importaciones cruzadas en el monorepo. Si la IA modifica la firma de{' '}
                    <code className="text-[#00e5ff] font-mono">{selectedResult.symbol}</code>, estos archivos se verán afectados.
                  </p>
                </div>
              </div>

              {/* Consumer List */}
              <div className="space-y-2 mt-4 max-h-[310px] overflow-y-auto pr-1">
                {selectedResult.impactConsumers.map((consumer, idx) => (
                  <div
                    key={idx}
                    onClick={() => setInspectingCaller(consumer.file)}
                    className={`p-3 rounded-xl border text-xs font-mono transition-all cursor-pointer flex items-center justify-between ${
                      inspectingCaller === consumer.file
                        ? 'bg-[#313244] border-[#00e5ff]'
                        : 'bg-[#11111b] border-[#313244] hover:border-[#45475a] hover:bg-[#161b22]'
                    }`}
                  >
                    <div className="flex items-center gap-2 overflow-hidden">
                      <CornerDownRight className="w-3.5 h-3.5 text-[#585b70] shrink-0" />
                      <div className="truncate">
                        <span className="text-white font-medium">{consumer.file}</span>
                      </div>
                    </div>

                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-bold shrink-0 ml-2 ${
                        consumer.risk === 'CRITICAL'
                          ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                          : consumer.risk === 'WARNING'
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                      }`}
                    >
                      {consumer.risk}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Neural Reranker Explanation */}
            <div className="p-5 rounded-2xl bg-[#181825] border border-[#313244]">
              <div className="flex items-center gap-2.5 mb-2">
                <Cpu className="w-4 h-4 text-[#cba6f7]" />
                <h4 className="text-xs font-bold text-white tracking-wide uppercase font-mono">
                  Reranker FlashRank ONNX en CPU
                </h4>
              </div>
              <p className="text-xs text-[#a6adc8] leading-relaxed mb-3">
                Modelo: <strong className="text-slate-200">ms-marco-TinyBERT-L-2-v2</strong>. Realiza inferencia de reordenamiento semántico profundo en CPU sin necesidad de GPUs Nvidia ni llamadas a APIs de OpenAI o Cohere.
              </p>
              <div className="flex items-center justify-between p-2.5 rounded-lg bg-[#11111b] border border-[#313244] text-xs font-mono">
                <span className="text-[#a6adc8]">Score de Relevancia:</span>
                <span className="text-[#a6e3a1] font-bold text-sm">{selectedResult.score}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
