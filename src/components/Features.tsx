import React from 'react';
import { Code, Zap, Cpu, GitFork, ShieldAlert, Check } from 'lucide-react';

const INNOVACIONES = [
  {
    id: 'tree-sitter',
    titulo: 'Parser Sintáctico Tree-sitter',
    estado: 'activo',
    icono: Code,
    descripcion: 'A diferencia de un RAG que parte el texto por líneas o tokens fijos, SyntaxRAG desciende al Árbol de Sintaxis Abstracta (AST) para extraer funciones, clases, hooks e interfaces completas.',
    beneficio: 'Conserva firmas, parámetros y docstrings; solo los bloques de más de 2.400 caracteres se dividen.',
    lenguajes: 'TypeScript, TSX, JavaScript, JSX, Python (Markdown y SQL por secciones y sentencias)',
  },
  {
    id: 'local-query-cache',
    titulo: 'Caché Local de Consultas',
    estado: 'activo',
    icono: Zap,
    descripcion: 'Guarda los resultados en la tabla query_cache de LanceDB. Si repites la misma consulta (sin distinguir mayúsculas ni espacios), se responde desde esa tabla sin recalcular el reordenado. Con otras palabras se vuelve a buscar, y la caché se vacía al reindexar.',
    beneficio: 'La búsqueda no usa APIs de pago. Los resultados siguen costando tokens al modelo que los lee.',
    lenguajes: 'LanceDB local · ~9 ms si se repite',
  },
  {
    id: 'reactive-watcher',
    titulo: 'Observador de Cambios (opcional)',
    estado: 'opcional',
    icono: Cpu,
    descripcion: 'Un servicio opcional (lancedb-watcher.service) vigila tus proyectos y, tras 0,6 s sin nuevos guardados, vuelve a parsear e indexar solo el archivo modificado. Reindexar un archivo pequeño tarda ~8 ms (mediana medida).',
    beneficio: 'Evita reindexar todo el proyecto en cada guardado. Consume memoria constante: 300 MB o más de RAM medidos en el equipo del autor.',
    lenguajes: 'Servicio systemd de usuario (Linux)',
  },
  {
    id: 'impact-graph',
    titulo: 'Grafo de Impacto de Dependencias',
    estado: 'activo',
    icono: GitFork,
    descripcion: 'Guarda en una tabla de LanceDB qué archivos importan cada símbolo (23.704 relaciones en el índice del autor, 6-oct-2026), para avisar qué archivos dependen de lo que vas a modificar.',
    beneficio: 'Avisa antes de modificar firmas exportadas. Detecta imports; no sigue llamadas dinámicas.',
    lenguajes: 'Tabla impact_graph en LanceDB',
  },
  {
    id: 'flashrank-onnx',
    titulo: 'Reranker Neuronal FlashRank',
    estado: 'activo',
    icono: ShieldAlert,
    descripcion: 'Los candidatos se recuperan por palabras (búsqueda BM25 de Tantivy) y se reordenan con un modelo transformador compacto (ms-marco-TinyBERT-L-2-v2) en ONNX Runtime. Si la consulta no comparte palabras con el código, la búsqueda no lo encuentra.',
    beneficio: 'Reordena en CPU, sin GPU. El modelo se descarga una vez la primera vez que se usa.',
    lenguajes: 'ONNX Runtime en CPU',
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
            Diseñados para aliviar los cuellos de botella de indexación y de contexto que sufren los desarrolladores y los agentes de IA. Cada cifra de esta página indica si es medida o de ejemplo.
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
                      {item.estado === 'opcional' ? 'Opcional' : 'Activo'}
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
