import { useState } from 'react';
import { Activity, Play, RefreshCw } from 'lucide-react';


interface WatcherLog {
  timestamp: string;
  stage: string;
  message: string;
  duration: string;
  status: 'info' | 'success' | 'warn';
}

export const DaemonStatus: React.FC = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState<WatcherLog[]>([
    {
      timestamp: '22:14:02.115',
      stage: 'DAEMON',
      message: 'lancedb-watcher.service activo y monitoreando 7,536 archivos en monorepo',
      duration: '0.0ms',
      status: 'info',
    },
    {
      timestamp: '22:14:18.420',
      stage: 'CTRL+S',
      message: 'Guardado detectado en asistoya-web/src/services/asistenciaServicio.ts',
      duration: '0.2ms',
      status: 'info',
    },
    {
      timestamp: '22:14:18.423',
      stage: 'AST',
      message: 'Tree-sitter extrajo quirúrgicamente hook useAsistenciaServicio()',
      duration: '2.8ms',
      status: 'success',
    },
    {
      timestamp: '22:14:18.428',
      stage: 'IMPACT',
      message: 'Actualizado grafo de 14 consumidores en networkx',
      duration: '4.6ms',
      status: 'warn',
    },
    {
      timestamp: '22:14:18.438',
      stage: 'LANCEDB',
      message: 'Upsert columnar completado en ~/.local/share/lancedb-hub',
      duration: '10.4ms',
      status: 'success',
    },
    {
      timestamp: '22:14:18.438',
      stage: 'TOTAL',
      message: '⚡ Hot-Reload reactivo completado con éxito (Cero caída de servicio)',
      duration: '18.0ms',
      status: 'success',
    }
  ]);

  const simulateCtrlS = () => {
    if (isRunning) return;
    setIsRunning(true);

    const now = new Date();
    const timeStr = () => {
      const h = String(now.getHours()).padStart(2, '0');
      const m = String(now.getMinutes()).padStart(2, '0');
      const s = String(now.getSeconds()).padStart(2, '0');
      const ms = String(Math.floor(Math.random() * 900 + 100));
      return `${h}:${m}:${s}.${ms}`;
    };

    const newLogs: WatcherLog[] = [
      {
        timestamp: timeStr(),
        stage: 'CTRL+S',
        message: 'Guardado detectado: asistoya-web/src/features/asistencia/PaseDeLista.tsx',
        duration: '0.1ms',
        status: 'info',
      },
      {
        timestamp: timeStr(),
        stage: 'AST',
        message: 'Tree-sitter parseó componente PaseDeListaModal (TSX)',
        duration: '2.4ms',
        status: 'success',
      },
      {
        timestamp: timeStr(),
        stage: 'IMPACT',
        message: 'Mapeadas 8 referencias cruzadas en el monorepo',
        duration: '3.1ms',
        status: 'warn',
      },
      {
        timestamp: timeStr(),
        stage: 'LANCEDB',
        message: 'Escritura columnar de 1 fragmento completada en disco',
        duration: '12.2ms',
        status: 'success',
      },
      {
        timestamp: timeStr(),
        stage: 'TOTAL',
        message: '⚡ Hot-Reload completado en ~17.8ms. Contexto al día para agentes IA.',
        duration: '17.8ms',
        status: 'success',
      },
    ];

    setLogs(newLogs);
    setTimeout(() => {
      setIsRunning(false);
    }, 600);
  };

  return (
    <section className="py-16 md:py-24 bg-[#11111b]/40 border-t border-[#313244]/80 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto rounded-3xl bg-[#181825] border border-[#313244] p-6 sm:p-8 shadow-2xl">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6 pb-6 border-b border-[#313244]">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-2xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-400">
                <Activity className="w-6 h-6 animate-pulse" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                  Demonio Reactivo en Vivo
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-mono font-medium">
                    lancedb-watcher.service ACTIVO
                  </span>
                </h3>
                <p className="text-xs text-[#a6adc8] mt-0.5 font-mono">
                  Escuchando eventos de guardado mediante inotify / watchdog
                </p>
              </div>
            </div>

            <button
              onClick={simulateCtrlS}
              disabled={isRunning}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#00e5ff] hover:bg-[#00e5ff]/90 text-[#11111b] font-bold text-xs tracking-wide transition-all cursor-pointer disabled:opacity-50 shadow-[0_0_15px_-3px_rgba(0,229,255,0.4)]"
            >
              {isRunning ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
              <span>Simular Guardado (Ctrl+S)</span>
            </button>
          </div>

          {/* Logs Terminal */}
          <div className="rounded-2xl bg-[#0d1117] border border-[#30363d] p-4 sm:p-5 font-mono text-xs text-[#cdd6f4] space-y-2.5 overflow-x-auto">
            <div className="flex items-center justify-between text-[#8b949e] border-b border-[#30363d] pb-2 text-[11px]">
              <span>systemd journalctl -u lancedb-watcher.service -f</span>
              <span className="text-[#a6e3a1]">STREAMING</span>
            </div>

            {logs.map((log, idx) => (
              <div key={idx} className="flex items-start gap-3 hover:bg-[#161b22] px-2 py-1 rounded">
                <span className="text-[#585b70] shrink-0">{log.timestamp}</span>
                <span
                  className={`px-1.5 py-0.2 rounded text-[10px] font-bold shrink-0 ${
                    log.status === 'success'
                      ? 'bg-emerald-500/20 text-emerald-300'
                      : log.status === 'warn'
                      ? 'bg-amber-500/20 text-amber-300'
                      : 'bg-blue-500/20 text-blue-300'
                  }`}
                >
                  [{log.stage}]
                </span>
                <span className="flex-1 text-slate-200">{log.message}</span>
                <span className="text-[#585b70] shrink-0">{log.duration}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
