import { useState } from 'react';
import { Layers, FileCode, CheckCircle2, Zap } from 'lucide-react';
import { ARCHITECTURE_PIPELINE } from '../data/mockData';


export const Architecture: React.FC = () => {
  const [activeStep, setActiveStep] = useState<number>(0);
  const current = ARCHITECTURE_PIPELINE[activeStep];

  return (
    <section id="arquitectura" className="py-20 md:py-32 bg-[#11111b]/80 border-t border-[#313244]/80 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#181825] border border-[#313244] text-xs font-mono text-[#cba6f7] mb-4">
            <Layers className="w-3.5 h-3.5" />
            DIAGRAMA DE COMPONENTES
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mb-4">
            Arquitectura de 7 Fases en Pipeline
          </h2>
          <p className="text-sm sm:text-base text-[#a6adc8]">
            Desde la solicitud del agente de IA hasta el reranking neural en CPU. Haz clic en cualquier etapa para inspeccionar su rol técnico y archivo del motor.
          </p>
        </div>

        {/* Pipeline Steps Tracker / Horizontal flow */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5 mb-10">
          {ARCHITECTURE_PIPELINE.map((stage, idx) => (
            <button
              key={stage.id}
              onClick={() => setActiveStep(idx)}
              className={`p-3 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between ${
                activeStep === idx
                  ? 'bg-[#181825] border-[#00e5ff] shadow-[0_0_20px_-5px_rgba(0,229,255,0.3)] translate-y-[-2px]'
                  : 'bg-[#11111b] border-[#313244] hover:border-[#45475a] opacity-80 hover:opacity-100'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-[10px] text-[#585b70]">FASE {stage.step}</span>
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: stage.color }}
                />
              </div>
              <div className="font-semibold text-xs text-white truncate mb-1">
                {stage.name}
              </div>
              <div className="text-[10px] font-mono text-[#8b949e] truncate">
                {stage.tech}
              </div>
            </button>
          ))}
        </div>

        {/* Selected Stage Detail Card */}
        <div className="p-6 sm:p-8 rounded-3xl bg-[#181825] border border-[#313244] shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-br from-[#00e5ff]/10 to-transparent rounded-bl-full pointer-events-none" />

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            {/* Left Info (7 cols) */}
            <div className="lg:col-span-7 space-y-4">
              <div className="flex items-center gap-3">
                <span
                  className="px-2.5 py-1 rounded-md text-xs font-mono font-bold"
                  style={{ backgroundColor: `${current.color}20`, color: current.color, border: `1px solid ${current.color}40` }}
                >
                  FASE {current.step} · {current.badge}
                </span>
                <span className="text-xs font-mono text-[#a6adc8] flex items-center gap-1.5">
                  <FileCode className="w-3.5 h-3.5 text-[#00e5ff]" />
                  <span>/home/reyno/.local/opt/lancedb-hub/{current.file}</span>
                </span>
              </div>

              <h3 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                {current.name}
              </h3>

              <p className="text-base text-[#cdd6f4] font-medium leading-relaxed">
                {current.role}
              </p>

              <p className="text-sm text-[#a6adc8] leading-relaxed">
                {current.desc}
              </p>

              <div className="pt-2 flex flex-wrap items-center gap-4 text-xs font-mono">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#11111b] border border-[#313244] text-[#a6e3a1]">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Sin costo de API ($0.00)</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#11111b] border border-[#313244] text-[#89b4fa]">
                  <Zap className="w-3.5 h-3.5" />
                  <span>Latencia garantizada</span>
                </div>
              </div>
            </div>

            {/* Right Visual / Technical Spec (5 cols) */}
            <div className="lg:col-span-5 rounded-2xl bg-[#0d1117] border border-[#30363d] p-5 font-mono text-xs text-[#cdd6f4] shadow-inner space-y-3">
              <div className="flex items-center justify-between text-[#8b949e] border-b border-[#30363d] pb-2 text-[11px]">
                <span>Pipeline Inspector</span>
                <span className="text-[#00e5ff]">READY</span>
              </div>

              <div className="space-y-1.5 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-[#585b70]">Subcomponente:</span>
                  <span className="text-white">{current.tech}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#585b70]">Archivo en Core:</span>
                  <span className="text-[#89b4fa]">{current.file}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#585b70]">Consumo de Tokens:</span>
                  <span className="text-[#a6e3a1]">0 Tokens (Local)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#585b70]">Inferencia:</span>
                  <span className="text-[#f9e2af]">CPU Nativa (ONNX)</span>
                </div>
              </div>

              <div className="pt-3 border-t border-[#30363d]/80 flex justify-between items-center">
                <button
                  onClick={() => setActiveStep((prev) => (prev > 0 ? prev - 1 : ARCHITECTURE_PIPELINE.length - 1))}
                  className="px-3 py-1 rounded bg-[#181825] hover:bg-[#313244] text-[#cdd6f4] transition-colors cursor-pointer text-xs"
                >
                  ← Anterior
                </button>
                <span className="text-[#585b70] text-xs">{activeStep + 1} de {ARCHITECTURE_PIPELINE.length}</span>
                <button
                  onClick={() => setActiveStep((prev) => (prev < ARCHITECTURE_PIPELINE.length - 1 ? prev + 1 : 0))}
                  className="px-3 py-1 rounded bg-[#181825] hover:bg-[#313244] text-[#00e5ff] transition-colors cursor-pointer text-xs flex items-center gap-1"
                >
                  Siguiente →
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
