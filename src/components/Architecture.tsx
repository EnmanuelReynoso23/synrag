import React from 'react';
import { ARCHITECTURE_PIPELINE } from '../data/mockData';
import { Cpu } from 'lucide-react';

export const Architecture: React.FC = () => {
  return (
    <section id="arquitectura" className="scroll-mt-20 border-b border-[#30363D] bg-[#0D1117] py-16 sm:py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Encabezado */}
        <div className="text-center max-w-3xl mx-auto">
          <p className="text-xs font-mono font-bold uppercase tracking-[0.18em] text-[#00E5FF]">
            Arquitectura de Sistema
          </p>
          <h2 className="mt-3 text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight text-white">
            Pipeline de 7 Fases de Alta Velocidad
          </h2>
          <p className="mt-3 text-sm sm:text-base text-[#8B949E]">
            Flujo end-to-end desde que el agente o desarrollador solicita contexto hasta que se devuelve el bloque de código con scoring semántico y alertas de dependencias.
          </p>
        </div>

        {/* Pipeline Cards Grid */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {ARCHITECTURE_PIPELINE.map((stage, index) => (
            <div
              key={stage.id}
              className="relative rounded-2xl border border-[#30363D] bg-[#161B22] p-5 hover:border-[#00E5FF]/40 hover:shadow-xl transition-all flex flex-col justify-between"
            >
              <div>
                {/* Paso número y badge */}
                <div className="flex items-center justify-between mb-3">
                  <span className="font-mono text-2xl font-black text-[#00E5FF]">
                    {stage.step}
                  </span>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-mono font-bold uppercase bg-[#00E5FF]/10 text-[#00E5FF] border border-[#00E5FF]/30">
                    {stage.badge}
                  </span>
                </div>

                <h3 className="text-base font-bold text-white">
                  {stage.name}
                </h3>

                <p className="mt-1 text-xs font-mono font-bold text-[#8B949E]">
                  {stage.tech}
                </p>

                <p className="mt-3 text-xs leading-relaxed text-slate-300">
                  {stage.desc}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-[#30363D] flex items-center justify-between text-[11px] text-[#8B949E] font-mono">
                <span>{stage.file}</span>
                {index < ARCHITECTURE_PIPELINE.length - 1 && (
                  <span className="text-[#00E5FF] font-black text-sm">→</span>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Resumen del Flujo */}
        <div className="mt-10 rounded-2xl border border-[#30363D] bg-[#161B22] p-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-[#00E5FF] text-[#0D1117]">
              <Cpu className="w-6 h-6" />
            </div>
            <div>
              <h4 className="font-bold text-sm text-white">
                Inferencia Local en CPU sin dependencias de GPU
              </h4>
              <p className="text-xs text-[#8B949E] mt-0.5">
                Todo el pipeline se ejecuta localmente en esta máquina (CachyOS x86_64). Sin llamadas de red lentas ni cuotas agotadas.
              </p>
            </div>
          </div>
          <span className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#0D1117] border border-[#30363D] text-xs font-mono font-bold text-[#00E5FF] shrink-0">
            Latencia total: ~18ms
          </span>
        </div>
      </div>
    </section>
  );
};
