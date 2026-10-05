import React from 'react';
import { Check, X } from 'lucide-react';

const CRITERIOS = [
  {
    criterio: 'Estrategia de Troceado',
    tradicional: 'Ventanas fijas (ej. 500 tokens o 50 líneas ciegas)',
    synrag: 'Parser AST sintáctico (Tree-sitter por nodos reales)',
    ventaja: 'Nunca parte una función ni corta parámetros de hooks',
  },
  {
    criterio: 'Integridad del Contexto',
    tradicional: 'Fragmentos huérfanos sin firma completa ni tipos',
    synrag: 'Bloques íntegros con docstrings, firmas e interfaces',
    ventaja: 'El agente o desarrollador entiende la función sin releer el archivo',
  },
  {
    criterio: 'Tiempo de Re-indexación',
    tradicional: 'Re-escaneo global pesado (30 a 90 segundos)',
    synrag: 'Hot-Reload reactivo in-memory (~18 ms ante Ctrl+S)',
    ventaja: 'Cada guardado en el editor actualiza LanceDB instantáneamente',
  },
  {
    criterio: 'Costo de Consultas Repetidas',
    tradicional: 'Llamada externa a embeddings o LLM ($$$ y cuota agotable)',
    synrag: 'Zero-Token Semantic Cache local ($0.00 y 0 tokens)',
    ventaja: 'Respuestas semánticas idénticas o afines en < 1 ms',
  },
  {
    criterio: 'Seguridad de Modificación',
    tradicional: 'Ninguna noción de dependencias o impacto de imports',
    synrag: 'Grafo de Impacto bidireccional (23,364 aristas)',
    ventaja: 'Advierte qué archivos consumen la función antes de editar',
  },
  {
    criterio: 'Dependencia de Infraestructura',
    tradicional: 'Servidores remotos, vector DBs en la nube, GPUs caras',
    synrag: '100% Local en CPU (LanceDB columnar + TinyBERT ONNX)',
    ventaja: 'Opera offline sin internet y sin gastar RAM del sistema',
  },
];

export const Comparison: React.FC = () => {
  return (
    <section id="comparativa" className="scroll-mt-20 border-b border-[#30363D] bg-[#0D1117] py-16 sm:py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Encabezado */}
        <div className="text-center max-w-3xl mx-auto">
          <p className="text-xs font-mono font-bold uppercase tracking-[0.18em] text-[#00E5FF]">
            Benchmark Comparativo
          </p>
          <h2 className="mt-3 text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight text-white">
            RAG Tradicional vs SyntaxRAG
          </h2>
          <p className="mt-3 text-sm sm:text-base text-[#8B949E]">
            Descubre por qué las herramientas de RAG genéricas fallan en código de monorepos y cómo el enfoque AST-Native supera cada limitación.
          </p>
        </div>

        {/* Tabla Comparativa */}
        <div className="mt-12 overflow-hidden rounded-2xl border border-[#30363D] bg-[#161B22] shadow-2xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs sm:text-sm">
              <thead className="bg-[#0D1117] border-b border-[#30363D] text-white font-bold">
                <tr>
                  <th className="py-4 px-5 sm:px-6">Capacidad Técnica</th>
                  <th className="py-4 px-5 sm:px-6 text-[#8B949E]">RAG Tradicional (Líneas fijas)</th>
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
