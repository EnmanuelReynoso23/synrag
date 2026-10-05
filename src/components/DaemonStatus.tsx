import { useState } from 'react';
import { Zap, Check, Terminal } from 'lucide-react';

interface WatcherLog {
  id: string;
  time: string;
  file: string;
  project: string;
  latencyMs: number;
  chunksUpdated: number;
}

const INITIAL_LOGS: WatcherLog[] = [
  {
    id: '1',
    time: '08:04:12',
    file: 'apps/web/src/modulos/asistencia/asistencia.servicio.ts',
    project: 'asistoya-web',
    latencyMs: 18.2,
    chunksUpdated: 6,
  },
  {
    id: '2',
    time: '08:04:38',
    file: 'apps/web/src/modulos/reconocimiento-facial/reconocimiento.servicio.ts',
    project: 'asistoya-web',
    latencyMs: 17.5,
    chunksUpdated: 4,
  },
  {
    id: '3',
    time: '08:05:02',
    file: 'apps/web/src/modulos/profesor/componentes/PaseDeLista.tsx',
    project: 'asistoya-web',
    latencyMs: 19.1,
    chunksUpdated: 3,
  },
];

export const DaemonStatus: React.FC = () => {
  const [logs, setLogs] = useState<WatcherLog[]>(INITIAL_LOGS);

  const simulateSave = () => {
    const candidates = [
      { file: 'apps/web/src/modulos/asistencia/asistencia.hook.ts', project: 'asistoya-web' },
      { file: 'apps/web/src/modulos/estudiantes/hooks/useEstudiantes.ts', project: 'asistoya-web' },
      { file: 'apps/web/src/modulos/kiosco/TerminalBiometrico.tsx', project: 'asistoya-web' },
      { file: 'apps/web/src/services/analytics/eventos.ts', project: 'asistoya-web' },
    ];
    const pick = candidates[Math.floor(Math.random() * candidates.length)];
    const now = new Date();
    const timeStr = now.toTimeString().split(' ')[0];

    const newLog: WatcherLog = {
      id: Date.now().toString(),
      time: timeStr,
      file: pick.file,
      project: pick.project,
      latencyMs: +(16 + Math.random() * 4).toFixed(1),
      chunksUpdated: Math.floor(Math.random() * 5) + 1,
    };

    setLogs((prev) => [newLog, ...prev.slice(0, 7)]);
  };

  return (
    <section id="demonio" className="border-b border-[#30363D] bg-[#0D1117] py-16 sm:py-24 relative overflow-hidden">
      {/* Glow ambiental */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-[#00E5FF]/5 blur-[120px] rounded-full pointer-events-none" />

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Encabezado */}
        <div className="text-center max-w-3xl mx-auto">
          <p className="text-xs font-black uppercase tracking-[0.2em] text-[#00E5FF] flex items-center justify-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00E5FF] animate-pulse"></span>
            DEMONIO REACTIVO · SYSTEMD WATCHER
          </p>
          <h2 className="mt-3 text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight text-white">
            Hot-Reload AST en Tiempo Real (~18ms)
          </h2>
          <p className="mt-3 text-sm sm:text-base text-[#8B949E]">
            Cada vez que guardas con <kbd className="px-2 py-0.5 rounded bg-[#161B22] border border-[#30363D] text-[#00E5FF] font-mono text-xs">Ctrl+S</kbd> en tu editor, el servicio <strong className="text-white font-semibold">lancedb-watcher.service</strong> detecta la modificación y re-parsea quirúrgicamente el archivo afectado en memoria.
          </p>
        </div>

        {/* Panel del Demonio */}
        <div className="mt-12 max-w-4xl mx-auto rounded-2xl border border-[#30363D] bg-[#161B22] shadow-2xl overflow-hidden">
          {/* Barra superior de estado */}
          <div className="p-4 sm:p-5 bg-[#161B22] border-b border-[#30363D] flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#7EE787] opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-[#7EE787]"></span>
              </span>
              <span className="font-mono text-xs sm:text-sm font-bold text-white">
                lancedb-watcher.service
              </span>
              <span className="inline-flex px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#238636]/20 border border-[#238636]/50 text-[#7EE787]">
                Active · Running
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={simulateSave}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-[#00E5FF] hover:bg-[#00c8e0] text-[#0D1117] text-xs font-black transition-all shadow-lg shadow-[#00E5FF]/20 cursor-pointer active:scale-95"
              >
                <Zap className="w-3.5 h-3.5 fill-[#0D1117]" />
                Simular Ctrl+S (Watcher AST)
              </button>
            </div>
          </div>

          {/* Consola de Eventos */}
          <div className="p-4 sm:p-5 bg-[#0D1117] text-[#C9D1D9] font-mono text-xs overflow-x-auto min-h-[220px]">
            <div className="text-[#8B949E] mb-2 pb-2 border-b border-[#21262D] text-[11px] flex justify-between">
              <span>EVENTOS REACTIVOS EN VIVO (Ctrl+S)</span>
              <span className="text-[#00E5FF]">LANCE_DB_ENGINE · AST_HOTRELOAD</span>
            </div>

            <div className="space-y-2">
              {logs.map((log) => (
                <div key={log.id} className="flex flex-wrap items-center gap-2 sm:gap-3 text-[#8B949E] py-1 border-b border-[#21262D]/50 last:border-none">
                  <span className="text-[#6E7681]">[{log.time}]</span>
                  <span className="text-[#00E5FF] font-bold flex items-center gap-1">
                    <Zap className="w-3 h-3 fill-[#00E5FF]" />
                    HOT-RELOAD AST
                  </span>
                  <span className="text-white font-semibold truncate max-w-xs sm:max-w-md">
                    {log.file}
                  </span>
                  <span className="text-[#8B949E] text-[11px]">
                    ({log.chunksUpdated} fragmentos en <strong className="text-[#7EE787] font-bold">{log.latencyMs}ms</strong>)
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Pie del Panel */}
          <div className="p-4 bg-[#161B22] border-t border-[#30363D] flex flex-wrap items-center justify-between text-xs text-[#8B949E] font-medium gap-3">
            <div className="flex items-center gap-2">
              <Check className="w-4 h-4 text-[#7EE787]" />
              <span>Memoria del daemon: <strong className="text-white">12.3 MB RAM</strong> (CPU: 0.1% reposo)</span>
            </div>
            <div className="flex items-center gap-1.5 font-mono text-[#58A6FF]">
              <Terminal className="w-3.5 h-3.5" />
              <span>journalctl --user -u lancedb-watcher.service -f</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
