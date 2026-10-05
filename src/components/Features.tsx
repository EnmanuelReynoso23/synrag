import React from 'react';
import { Code, Zap, Cpu, GitFork, ShieldAlert, Check } from 'lucide-react';

const INNOVACIONES = [
  {
    id: 'tree-sitter',
    titulo: 'Parser Sintáctico Tree-sitter',
    estado: 'activo',
    icono: Code,
    descripcion: 'A diferencia de los RAG convencionales que parten texto por líneas arbitrarias o tokens fijos, SyntaxRAG desciende al Árbol de Sintaxis Abstracta (AST) para extraer únicamente funciones, clases, hooks e interfaces completas.',
    beneficio: '0 fragmentos partidos por la mitad; conserva firmas, parámetros y docstrings.',
    lenguajes: 'TypeScript, TSX, JavaScript, JSX, Python',
  },
  {
    id: 'zero-token-cache',
    titulo: 'Zero-Token Semantic Cache',
    estado: 'activo',
    icono: Zap,
    descripcion: 'Almacena resultados en la tabla query_cache de LanceDB. Si tú o un agente realizan una consulta semánticamente equivalente, se responde en memoria en menos de 1 milisegundo a costo cero.',
    beneficio: 'Ahorro del 100% de costos de cuota de API en tareas repetitivas de desarrollo.',
    lenguajes: 'LanceDB local · < 1 ms',
  },
  {
    id: 'reactive-watcher',
    titulo: 'Hot-Reload Reactivo (~18ms)',
    estado: 'activo',
    icono: Cpu,
    descripcion: 'Un demonio en segundo plano (lancedb-watcher.service) monitorea los archivos del monorepo. Cada vez que guardas con Ctrl+S en VSCode, Cursor o terminal, el archivo se re-parsea e indexa al vuelo.',
    beneficio: 'Elimina las reindexaciones completas de 30 segundos. El índice siempre está al día.',
    lenguajes: 'Demonio systemd in-memory',
  },
  {
    id: 'impact-graph',
    titulo: 'Grafo de Impacto Bidireccional',
    estado: 'activo',
    icono: GitFork,
    descripcion: 'Construye una red estática de dependencias con 23,364 aristas que mapea qué archivos importan y consumen cada componente o servicio del proyecto.',
    beneficio: 'Alerta antes de modificar firmas exportadas, previniendo regresiones silenciosas.',
    lenguajes: 'NetworkX + Matriz de Aristas',
  },
  {
    id: 'flashrank-onnx',
    titulo: 'Reranker Neuronal FlashRank',
    estado: 'activo',
    icono: ShieldAlert,
    descripcion: 'Reordena los candidatos recuperados por búsqueda BM25 de Tantivy usando un modelo transformador compacto (ms-marco-TinyBERT-L-2-v2) optimizado con ONNX Runtime.',
    beneficio: 'Precisión semántica superior con scoring continuo (0-100%) sin requerir GPU dedicada.',
    lenguajes: 'ONNX Runtime en CPU pura',
  },
];

export const Features: React.FC = () => {
  return (
    <section id="innovaciones" className="scroll-mt-20 border-b border-[#30363D] bg-[#0D1117] py-16 sm:py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Encabezado */}
        <div className="text-center max-w-3xl mx-auto">
          <p className="text-xs font-mono font-bold uppercase tracking-[0.18em] text-[#00E5FF]">
            Innovaciones Tecnológicas
          </p>
          <h2 className="mt-3 text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight text-white">
            Los 5 Pilares de Ingeniería de SyntaxRAG
          </h2>
          <p className="mt-3 text-sm sm:text-base text-[#8B949E]">
            Diseñados para eliminar los cuellos de botella de indexación y saturación de contexto que sufren los desarrolladores y agentes de IA.
          </p>
        </div>

        {/* Grid de Tarjetas */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {INNOVACIONES.map((item) => {
            const Icon = item.icono;
            return (
              <div
                key={item.id}
                className="group rounded-2xl border border-[#30363D] bg-[#161B22] p-6 hover:border-[#00E5FF]/50 hover:shadow-xl transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div className="p-2.5 rounded-xl bg-[#21262D] text-[#00E5FF] group-hover:bg-[#00E5FF] group-hover:text-[#0D1117] transition-colors">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-mono font-bold uppercase tracking-wide bg-[#7EE787]/15 text-[#7EE787] border border-[#7EE787]/30">
                      <Check className="w-3 h-3" />
                      Activo
                    </span>
                  </div>

                  <h3 className="text-lg font-bold text-white group-hover:text-[#00E5FF] transition-colors">
                    {item.titulo}
                  </h3>

                  <p className="mt-2.5 text-xs sm:text-sm leading-relaxed text-[#8B949E]">
                    {item.descripcion}
                  </p>
                </div>

                <div className="mt-6 pt-4 border-t border-[#30363D]">
                  <p className="text-xs font-bold text-slate-200 flex items-start gap-1.5">
                    <span className="text-[#00E5FF] font-black">▸</span>
                    <span>{item.beneficio}</span>
                  </p>
                  <span className="mt-2 inline-block text-[11px] font-mono text-[#8B949E]">
                    {item.lenguajes}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
