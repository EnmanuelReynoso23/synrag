import { Zap, Cpu, ShieldCheck, Database, Terminal, Flame, Sparkles } from 'lucide-react';


export const Features: React.FC = () => {
  const features = [
    {
      icon: <Zap className="w-6 h-6 text-[#00e5ff]" />,
      badge: 'Hot-Reload 18ms',
      title: 'Indexado Reactivo por Ctrl+S',
      desc: 'El demonio en segundo plano (lancedb-watcher.service) escucha el sistema de archivos. En cuanto guardas un archivo, solo ese archivo se parsea por Tree-sitter y actualiza LanceDB en ~18 ms.',
      highlight: 'Contexto perpetuamente fresco sin escaneos manuales.',
      borderColor: 'hover:border-[#00e5ff]/50',
    },
    {
      icon: <Cpu className="w-6 h-6 text-[#a6e3a1]" />,
      badge: '0 Tokens · $0.00',
      title: 'Caché Semántico Local',
      desc: 'Consultas idénticas o recurrentes se resuelven en la tabla dedicada query_cache en menos de 1 ms. Evita quemar cuota de API en tus agentes Claude Code o Antigravity.',
      highlight: 'Ahorro del 100% en tokens para búsquedas repetidas.',
      borderColor: 'hover:border-[#a6e3a1]/50',
    },
    {
      icon: <ShieldCheck className="w-6 h-6 text-[#f38ba8]" />,
      badge: 'Protección Anti-Rotura',
      title: 'Grafo de Impacto de Dependencias',
      desc: 'Tree-sitter mapea imports y exports de todo el monorepo. Cuando la IA inspecciona o refactoriza una función, SyntaxRAG advierte qué componentes la consumen.',
      highlight: 'Transforma al agente de un simple buscador a un arquitecto seguro.',
      borderColor: 'hover:border-[#f38ba8]/50',
    },
    {
      icon: <Flame className="w-6 h-6 text-[#fab387]" />,
      badge: 'Inferencia en CPU',
      title: 'Reranker Neuronal FlashRank ONNX',
      desc: 'Búsqueda híbrida en dos etapas: primero filtro ultra-veloz Tantivy BM25, seguido de reranking con el modelo ms-marco-TinyBERT-L-2-v2 corriendo puramente en CPU.',
      highlight: 'Precisión profunda de Deep Learning sin gastar VRAM de GPU.',
      borderColor: 'hover:border-[#fab387]/50',
    },
    {
      icon: <Terminal className="w-6 h-6 text-[#cba6f7]" />,
      badge: 'Herdr + MCP',
      title: 'Herdr Workspace & Antigravity CLI',
      desc: 'Integración nativa con el espacio de trabajo Herdr mediante atajos directos (Ctrl+B a para Antigravity, Ctrl+B c para Claude Code). Protocolo MCP stdio listo para usar.',
      highlight: 'Flujo de trabajo fluido con cambio de agente en un solo atajo.',
      borderColor: 'hover:border-[#cba6f7]/50',
    },
    {
      icon: <Database className="w-6 h-6 text-[#89b4fa]" />,
      badge: 'Storage Columnar',
      title: 'LanceDB Almacenamiento Columnar',
      desc: 'Almacena más de 95,500 fragmentos en tan solo 49.8 MB de espacio en disco. Arquitectura columnar Lance de cero copia en memoria para lecturas instantáneas.',
      highlight: 'Ligero como SQLite, potente como un clúster de vectores.',
      borderColor: 'hover:border-[#89b4fa]/50',
    }
  ];

  return (
    <section id="innovaciones" className="py-20 md:py-32 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#181825] border border-[#313244] text-xs font-mono text-[#00e5ff] mb-4">
            <Sparkles className="w-3.5 h-3.5" />
            VENTAJAS TECNOLÓGICAS
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mb-4">
            Las Innovaciones Clave de Synrag
          </h2>
          <p className="text-sm sm:text-base text-[#a6adc8]">
            Diseñado desde cero para resolver las deficiencias críticas de los sistemas RAG tradicionales en bases de código reales.
          </p>
        </div>

        {/* Feature Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feat, idx) => (
            <div
              key={idx}
              className={`p-7 rounded-3xl bg-[#181825] border border-[#313244] ${feat.borderColor} transition-all duration-300 hover:shadow-xl hover:translate-y-[-3px] flex flex-col justify-between group`}
            >
              <div>
                <div className="flex items-center justify-between mb-5">
                  <div className="p-3 rounded-2xl bg-[#11111b] border border-[#313244] group-hover:scale-105 transition-transform">
                    {feat.icon}
                  </div>
                  <span className="text-[11px] font-mono px-2.5 py-1 rounded-full bg-[#11111b] border border-[#313244] text-[#bac2de]">
                    {feat.badge}
                  </span>
                </div>

                <h3 className="text-xl font-bold text-white mb-2.5 group-hover:text-[#00e5ff] transition-colors">
                  {feat.title}
                </h3>

                <p className="text-sm text-[#a6adc8] leading-relaxed mb-6">
                  {feat.desc}
                </p>
              </div>

              <div className="pt-4 border-t border-[#313244]/60 text-xs font-mono text-[#cdd6f4] flex items-center justify-between">
                <span className="text-[#a6e3a1]">{feat.highlight}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
