import React from 'react';
import { Check, X } from 'lucide-react';

const CRITERIOS = [
  {
    criterio: 'Estrategia de Troceado',
    tradicional: 'Ventanas fijas (ej. 500 tokens o 50 líneas)',
    synrag: 'Troceo por AST (Tree-sitter, por nodos reales)',
    ventaja: 'Prioriza funciones y clases completas; solo se dividen los bloques de más de 2.400 caracteres',
  },
  {
    criterio: 'Integridad del Contexto',
    tradicional: 'Fragmentos sin la firma completa ni los tipos',
    synrag: 'Bloques con docstrings, firmas e interfaces',
    ventaja: 'Suele bastar para entender la función sin abrir el archivo completo',
  },
  {
    criterio: 'Actualización del Índice',
    tradicional: 'Reescaneo global del proyecto',
    synrag: 'Reindexado completo programado (timer) y observador opcional por archivo (~8 ms por archivo pequeño, tras 0,6 s de espera)',
    ventaja: 'Cifra medida por el autor el 6-oct-2026; el observador usa 300 MB o más de RAM',
  },
  {
    criterio: 'Costo por Consulta',
    tradicional: 'Embeddings o LLM por API en cada consulta ($ y cuota)',
    synrag: 'Búsqueda y reordenado en CPU local, sin APIs de pago; caché local para la misma consulta (~9 ms)',
    ventaja: 'Los resultados igualmente cuestan tokens al modelo que los lee',
  },
  {
    criterio: 'Seguridad de Modificación',
    tradicional: 'Sin noción de qué archivos dependen de un símbolo',
    synrag: 'Grafo de impacto de dependientes (23.704 relaciones en el índice del autor)',
    ventaja: 'Avisa qué archivos importan el símbolo antes de editarlo',
  },
  {
    criterio: 'Dependencia de Infraestructura',
    tradicional: 'Servicios remotos, vector DB en la nube o GPU',
    synrag: 'Todo local en CPU (LanceDB + TinyBERT ONNX)',
    ventaja: 'Necesita internet solo para instalar y descargar el modelo la primera vez',
  },
];

export const Comparison: React.FC = () => {
  return (
    <section id="comparativa" className="scroll-mt-20 border-b border-[#30363D] bg-[#0D1117] py-16 sm:py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Encabezado */}
        <div className="text-center max-w-3xl mx-auto">
          <p className="text-xs font-mono font-bold uppercase tracking-[0.18em] text-[#00E5FF]">
            Comparación de Enfoques
          </p>
          <h2 className="mt-3 text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight text-white">
            RAG Clásico vs SyntaxRAG
          </h2>
          <p className="mt-3 text-sm sm:text-base text-[#8B949E]">
            Compara el enfoque de SyntaxRAG con un RAG genérico de ventanas fijas. No es un benchmark contra otras herramientas: otras también usan AST. Las cifras de SyntaxRAG las midió el autor en su equipo.
          </p>
        </div>

        {/* Tabla Comparativa */}
        <div className="mt-12 overflow-hidden rounded-2xl border border-[#30363D] bg-[#161B22] shadow-2xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs sm:text-sm">
              <thead className="bg-[#0D1117] border-b border-[#30363D] text-white font-bold">
                <tr>
                  <th className="py-4 px-5 sm:px-6">Capacidad Técnica</th>
                  <th className="py-4 px-5 sm:px-6 text-[#8B949E]">RAG clásico (ventanas fijas)</th>
                  <th className="py-4 px-5 sm:px-6 text-[#00E5FF] bg-[#00E5FF]/5">SyntaxRAG (AST Native)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#30363D] font-medium text-slate-300">
                {CRITERIOS.map((item, idx) => (
                  <tr key={idx} className="hover:bg-[#21262D]/60 transition-colors">
                    <td className="py-4 px-5 sm:px-6 font-bold text-white">
                      {item.criterio}
                      <span className="block text-[11px] font-normal text-[#8B949E] mt-0.5">
                        {item.ventaja}
                      </span>
                    </td>
                    <td className="py-4 px-5 sm:px-6 text-[#8B949E]">
                      <div className="flex items-start gap-2">
                        <X className="w-4 h-4 text-[#FF7B72] shrink-0 mt-0.5" />
                        <span>{item.tradicional}</span>
                      </div>
                    </td>
                    <td className="py-4 px-5 sm:px-6 text-white font-bold bg-[#00E5FF]/5">
                      <div className="flex items-start gap-2">
                        <Check className="w-4 h-4 text-[#7EE787] shrink-0 mt-0.5" />
                        <span className="text-[#00E5FF]">{item.synrag}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
};
