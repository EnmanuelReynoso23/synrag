import React from 'react';
import { PROYECTOS_DISTRIBUCION } from '../data/mockData';
import { HardDrive } from 'lucide-react';

export const Metrics: React.FC = () => {
  return (
    <section id="metricas" className="scroll-mt-20 border-b border-[#30363D] bg-[#0D1117] py-16 sm:py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Encabezado */}
        <div className="text-center max-w-3xl mx-auto">
          <p className="text-xs font-mono font-bold uppercase tracking-[0.18em] text-[#00E5FF]">
            Ejemplo medido · monorepo real
          </p>
          <h2 className="mt-3 text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight text-white">
            Así rinde en un monorepo grande
          </h2>
          <p className="mt-3 text-sm sm:text-base text-[#8B949E]">
            Cifras medidas por el autor en su equipo con ~95 mil fragmentos indexados. En el tuyo variarán según el tamaño de tus proyectos y tu CPU.
          </p>
        </div>

        {/* Franja de 4 Grandes Cifras */}
        <dl className="mt-12 grid grid-cols-2 gap-x-6 gap-y-10 sm:gap-x-8 lg:grid-cols-4 border-b border-[#30363D] pb-14">
          <div className="text-center sm:text-left">
            <dt className="text-4xl font-black tracking-tight text-[#00E5FF] sm:text-[2.75rem]">
              95,502
            </dt>
            <dd className="mt-2 text-base font-bold leading-snug text-white">
              Fragmentos AST Únicos
            </dd>
            <dd className="mt-1 text-xs text-[#8B949E] font-medium">
              Funciones, clases y hooks troceados íntegramente
            </dd>
          </div>

          <div className="text-center sm:text-left">
            <dt className="text-4xl font-black tracking-tight text-[#00E5FF] sm:text-[2.75rem]">
              &lt; 1 ms
            </dt>
            <dd className="mt-2 text-base font-bold leading-snug text-white">
              Latencia en Caché
            </dd>
            <dd className="mt-1 text-xs text-[#8B949E] font-medium">
              Respuestas instantáneas en memoria sin red
            </dd>
          </div>

          <div className="text-center sm:text-left">
            <dt className="text-4xl font-black tracking-tight text-[#7EE787] sm:text-[2.75rem]">
              100% $0.00
            </dt>
            <dd className="mt-2 text-base font-bold leading-snug text-white">
              Ahorro de Cuota de API
            </dd>
            <dd className="mt-1 text-xs text-[#8B949E] font-medium">
              0 tokens de LLM consumidos en re-búsquedas
            </dd>
          </div>

          <div className="text-center sm:text-left">
            <dt className="text-4xl font-black tracking-tight text-[#58A6FF] sm:text-[2.75rem]">
              23,364
            </dt>
            <dd className="mt-2 text-base font-bold leading-snug text-white">
              Aristas de Dependencias
            </dd>
            <dd className="mt-1 text-xs text-[#8B949E] font-medium">
              Mapeadas en el Grafo de Impacto bidireccional
            </dd>
          </div>
        </dl>

        {/* Distribución por Repositorios */}
        <div className="mt-12">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
            <div>
              <h3 className="text-lg font-bold text-white">
                Distribución de Fragmentos por Repositorio
              </h3>
              <p className="text-xs text-[#8B949E] mt-0.5 font-medium">
                Proporción de código analizado por el motor sintáctico Tree-sitter
              </p>
            </div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#161B22] border border-[#30363D] text-xs font-mono text-[#00E5FF]">
              <HardDrive className="w-3.5 h-3.5 text-[#00E5FF]" />
              <span>LanceDB: ~49.8 MB en disco</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {PROYECTOS_DISTRIBUCION.slice(0, 6).map((item) => (
              <div 
                key={item.nombre}
                className="rounded-xl border border-[#30363D] bg-[#161B22] p-4 hover:border-[#00E5FF]/40 hover:shadow-lg transition-all"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-sm font-bold text-white">
                    {item.nombre}
                  </span>
                  <span className="text-xs font-mono font-bold text-[#00E5FF] bg-[#00E5FF]/10 px-2 py-0.5 rounded-full border border-[#00E5FF]/30">
                    {item.porcentaje}%
                  </span>
                </div>

                <p className="text-xs text-[#8B949E] line-clamp-1 mb-3">
                  {item.descripcion}
                </p>

                {/* Barra de progreso con gradiente neón */}
                <div className="w-full bg-[#0D1117] rounded-full h-2 overflow-hidden border border-[#30363D]">
                  <div 
                    className="bg-gradient-to-r from-[#00E5FF] to-[#58A6FF] h-2 rounded-full transition-all duration-500" 
                    style={{ width: `${item.porcentaje * 2.5}%` }}
                  />
                </div>

                <div className="mt-2.5 flex items-center justify-between text-[11px] font-mono text-[#8B949E]">
                  <span>Fragmentos AST:</span>
                  <span className="text-white font-bold">{item.chunks.toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
