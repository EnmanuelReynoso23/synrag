import { Check, X, Zap } from 'lucide-react';


export const Comparison: React.FC = () => {
  const comparisonItems = [
    {
      feature: 'Segmentación de Código',
      traditional: 'Cortes ciegos por número fijo de líneas o caracteres (fragmenta funciones a la mitad)',
      synrag: 'Bloques sintácticos íntegros parseados con Tree-sitter AST (funciones, hooks, interfaces)',
      isHighlight: true,
    },
    {
      feature: 'Velocidad de Actualización',
      traditional: 'Reindexación manual pesada (3 a 5 minutos bloqueando el entorno)',
      synrag: 'Hot-Reload Reactivo en ~18 ms por archivo al presionar Ctrl+S',
      isHighlight: true,
    },
    {
      feature: 'Costo de Consultas Repetidas',
      traditional: 'Gasto recurrente de tokens de API ($$$) en cada consulta similar',
      synrag: 'Caché semántico local: < 1 ms de latencia, 0 tokens gastados y $0.00 de costo',
      isHighlight: true,
    },
    {
      feature: 'Protección Anti-Rotura',
      traditional: 'Ciego: El agente modifica una función sin saber quién la importa en el monorepo',
      synrag: 'Grafo de Impacto: Alerta en vivo sobre qué módulos consumen el símbolo',
      isHighlight: true,
    },
    {
      feature: 'Requisitos de Hardware',
      traditional: 'Requiere clústeres vectoriales en la nube o GPU dedicada con alto consumo de VRAM',
      synrag: 'Inferencia ligera ONNX en CPU pura (ms-marco-TinyBERT-L-2-v2) con LanceDB columnar',
      isHighlight: false,
    },
    {
      feature: 'Integración con IAs',
      traditional: 'Endpoints REST personalizados o scripts ad-hoc dependientes de wrappers',
      synrag: 'Model Context Protocol (MCP) estándar vía stdio para Claude Code, Antigravity y Cursor',
      isHighlight: false,
    },
  ];

  return (
    <section className="py-20 md:py-32 bg-[#11111b]/50 border-t border-[#313244]/80 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#181825] border border-[#313244] text-xs font-mono text-[#a6e3a1] mb-4">
            <Zap className="w-3.5 h-3.5" />
            BENCHMARK COMPARATIVO
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mb-4">
            RAG Tradicional vs. Synrag
          </h2>
          <p className="text-sm sm:text-base text-[#a6adc8]">
            Por qué los RAGs convencionales fallan con código fuente y cómo Synrag ofrece precisión estructural quirúrgica.
          </p>
        </div>

        {/* Comparison Table Container */}
        <div className="rounded-3xl border border-[#313244] bg-[#181825] overflow-hidden shadow-2xl">
          <div className="grid grid-cols-1 md:grid-cols-12 border-b border-[#313244] bg-[#161b22] text-xs font-mono uppercase tracking-wider font-semibold">
            <div className="md:col-span-4 p-4 text-[#8b949e]">Característica</div>
            <div className="md:col-span-4 p-4 text-[#f38ba8] border-t md:border-t-0 md:border-l border-[#313244]">
              RAG Tradicional
            </div>
            <div className="md:col-span-4 p-4 text-[#00e5ff] border-t md:border-t-0 md:border-l border-[#313244] bg-[#00e5ff]/5">
              ⚡ Synrag (SyntaxRAG)
            </div>
          </div>

          <div className="divide-y divide-[#313244]">
            {comparisonItems.map((item, idx) => (
              <div
                key={idx}
                className="grid grid-cols-1 md:grid-cols-12 text-sm hover:bg-[#1e1e2e]/50 transition-colors"
              >
                {/* Feature Name */}
                <div className="md:col-span-4 p-4 sm:p-5 flex items-center font-medium text-white">
                  {item.feature}
                </div>

                {/* Traditional RAG */}
                <div className="md:col-span-4 p-4 sm:p-5 flex items-start gap-2.5 text-[#a6adc8] border-t md:border-t-0 md:border-l border-[#313244] bg-[#11111b]/40">
                  <X className="w-4 h-4 text-[#f38ba8] shrink-0 mt-0.5" />
                  <span className="text-xs sm:text-sm">{item.traditional}</span>
                </div>

                {/* Synrag */}
                <div className="md:col-span-4 p-4 sm:p-5 flex items-start gap-2.5 text-[#cdd6f4] border-t md:border-t-0 md:border-l border-[#313244] bg-[#00e5ff]/5">
                  <Check className="w-4 h-4 text-[#00e5ff] shrink-0 mt-0.5 font-bold" />
                  <span className="text-xs sm:text-sm font-medium text-white">{item.synrag}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
