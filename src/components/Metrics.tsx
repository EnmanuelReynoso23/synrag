import React from 'react';
import { FileCode2, Code, GitFork, Zap, Cpu, HardDrive } from 'lucide-react';
import { ECOSYSTEM_METRICS } from '../data/mockData';

export const Metrics: React.FC = () => {
  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'FileCode2':
        return <FileCode2 className="w-6 h-6 text-[#89b4fa]" />;
      case 'Code':
        return <Code className="w-6 h-6 text-[#00e5ff]" />;
      case 'GitFork':
        return <GitFork className="w-6 h-6 text-[#f38ba8]" />;
      case 'Zap':
        return <Zap className="w-6 h-6 text-[#a6e3a1]" />;
      case 'Cpu':
        return <Cpu className="w-6 h-6 text-[#cba6f7]" />;
      case 'HardDrive':
        return <HardDrive className="w-6 h-6 text-[#fab387]" />;
      default:
        return <Code className="w-6 h-6 text-[#00e5ff]" />;
    }
  };

  return (
    <section id="metricas" className="py-16 md:py-24 bg-[#11111b]/60 border-y border-[#313244]/80 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-14">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#181825] border border-[#313244] text-xs font-mono text-[#00e5ff] mb-4">
            <span className="w-2 h-2 rounded-full bg-[#00e5ff] animate-ping" />
            BENCHMARKS EN PRODUCCIÓN
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-4">
            Ecosistema en Tiempo Real
          </h2>
          <p className="text-sm sm:text-base text-[#a6adc8]">
            Métricas extraídas directamente de los proyectos activos en este equipo, indexados localmente sin servidores externos ni costos ocultos.
          </p>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {ECOSYSTEM_METRICS.map((metric, idx) => (
            <div
              key={idx}
              className="p-6 rounded-2xl bg-[#181825]/90 border border-[#313244] hover:border-[#45475a] transition-all hover:translate-y-[-2px] hover:shadow-[0_10px_30px_-10px_rgba(0,0,0,0.5)] group relative overflow-hidden"
            >
              {/* Corner accent glow */}
              <div className="absolute top-0 right-0 w-24 h-24 bg-[#00e5ff]/5 rounded-bl-full group-hover:bg-[#00e5ff]/10 transition-colors pointer-events-none" />

              <div className="flex items-center justify-between mb-4">
                <div className="p-3 rounded-xl bg-[#11111b] border border-[#313244] group-hover:border-[#00e5ff]/30 transition-colors">
                  {getIcon(metric.icon)}
                </div>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-[#313244]/60 text-[#bac2de]">
                  {metric.delta}
                </span>
              </div>

              <div className="text-3xl sm:text-4xl font-extrabold text-white mb-1 font-mono tracking-tight group-hover:text-[#00e5ff] transition-colors">
                {metric.value}
              </div>

              <div className="text-sm font-semibold text-[#cdd6f4] mb-0.5">
                {metric.label}
              </div>

              <div className="text-xs text-[#a6adc8]">
                {metric.unit}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
