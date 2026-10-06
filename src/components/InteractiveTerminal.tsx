import { useState, useRef, useEffect } from 'react';
import { Terminal, Play, RotateCcw, Copy, Check, ChevronRight } from 'lucide-react';

interface CommandOutput {
  id: string;
  command: string;
  output: string[];
}

const PRESET_COMMANDS = [
  'SYNRAG "asistenciaServicio"',
  'SYNRAG stats',
  'SYNRAG impact reconocimientoFacial',
  'SYNRAG watch',
  'help',
];

let commandCounter = 1;

export const InteractiveTerminal: React.FC = () => {
  const [history, setHistory] = useState<CommandOutput[]>([
    {
      id: 'init-1',
      command: 'SYNRAG "asistenciaServicio"',
      output: [
        '[SIMULACIÓN] Salida de ejemplo con datos ficticios; la tuya dependerá de tu índice.',
        '[OK] Candidatos por palabras (BM25) reordenados con FlashRank | consulta nueva: ~90 ms (mediana medida)',
        '--------------------------------------------------------------------------------',
        'ARCHIVO: apps/web/src/modulos/asistencia/asistencia.servicio.ts:35-72',
        'SÍMBOLO: export const asistenciaServicio = { ... }',
        'FRAGMENTO: función completa; el modelo lo lee y cuesta tokens como cualquier texto',
        '--------------------------------------------------------------------------------',
        'ALERTA DE GRAFO DE IMPACTO (Riesgo: CRITICAL):',
        '  → apps/web/src/modulos/kiosco/TerminalBiometrico.tsx:14 (importa registrarPase)',
        '  → apps/web/src/modulos/estudiantes/hooks/useEstudiantes.ts:8 (importa validarAsistencia)',
        '  → apps/web/src/modulos/profesor/componentes/PaseDeLista.tsx:22 (importa asistenciaServicio)',
        'Costo de la búsqueda: $0.00 en APIs de pago.',
      ],
    },
  ]);

  const [inputVal, setInputVal] = useState('');
  const [copied, setCopied] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const executeCommand = (cmdToRun: string) => {
    const trimmed = cmdToRun.trim();
    if (!trimmed) return;

    let lines: string[] = [];

    if (trimmed.toLowerCase() === 'clear') {
      setHistory([]);
      setInputVal('');
      return;
    } else if (trimmed.toLowerCase() === 'help') {
      lines = [
        '[SIMULACIÓN] Comandos reales de SYNRAG; en esta página solo se simulan:',
        '  SYNRAG "<consulta>"                 Busca por palabras y reordena con FlashRank.',
        '  SYNRAG --project <p> "<consulta>"   Limita la búsqueda a un proyecto.',
        '  SYNRAG outline <archivo>            Esquema del archivo (firmas y rangos de línea).',
        '  SYNRAG impact <símbolo>             Qué archivos importan ese símbolo.',
        '  SYNRAG tests <archivo|símbolo>      Pruebas relacionadas.',
        '  SYNRAG stats                        Estadísticas del índice y de las búsquedas.',
        '  SYNRAG index                        Reindexa todo.',
        '  SYNRAG watch                        Log del observador de cambios (opcional).',
        '  SYNRAG configure                    Configura el MCP en tus IAs instaladas.',
        '  clear                               Limpia la pantalla.',
      ];
    } else if (/\bstats\b|--stats/.test(trimmed)) {
      lines = [
        '[SIMULACIÓN] Formato aproximado, con cifras de ejemplo del autor (6-oct-2026).',
        '--------------------------------------------------------------------------------',
        'Proyectos indexados:        74',
        'Fragmentos AST:             ~96 mil',
        'Relaciones en el grafo:     23,704',
        'Consulta nueva (mediana):   ~90 ms en CPU local',
        'Consulta repetida:          ~9 ms (caché local)',
        'Costo de la búsqueda:       $0.00 en APIs de pago',
      ];
    } else if (/\bwatch\b|--daemon/.test(trimmed)) {
      lines = [
        '[SIMULACIÓN] journalctl --user -u lancedb-watcher.service -f',
        'Servicio opcional: reindexa el archivo guardado tras 0,6 s sin nuevos cambios.',
        'Reindexar un archivo pequeño: ~8 ms (mediana medida por el autor).',
        'Memoria del proceso en el equipo del autor: 300 MB o más de RAM.',
      ];
    } else if (/\bimpact\b|--graph/.test(trimmed)) {
      lines = [
        '[SIMULACIÓN] Archivos de ejemplo; el comando real lista los que importan el símbolo en tu índice.',
        'Símbolo: reconocimientoFacial',
        '--------------------------------------------------------------------------------',
        '  apps/web/src/modulos/kiosco/TerminalBiometrico.tsx (línea 29)',
        '  apps/web/src/modulos/asistencia/asistencia.hook.ts (línea 44)',
        '  apps/web/src/modulos/estudiantes/componentes/CredencialEstudiante.tsx (línea 12)',
        '  apps/web/src/services/telemetria/biometriaAudit.ts (línea 5)',
        'Un cambio en la firma de reconocimientoFacial afectaría a esos 4 archivos.',
      ];
    } else if (trimmed.includes('--clear-cache')) {
      lines = [
        '[SIMULACIÓN] Ese comando no existe en el CLI real. La caché se vacía sola al reindexar.',
      ];
    } else {
      lines = [
        `[SIMULACIÓN] Búsqueda de ejemplo para: "${trimmed.replace(/^SYNRAG\s*/i, '').replace(/["']/g, '')}"`,
        '[OK] Candidatos recuperados por palabras (BM25) y reordenados con FlashRank.',
        'Consulta nueva: ~90 ms (mediana medida por el autor); si repites la misma consulta: ~9 ms.',
        '--------------------------------------------------------------------------------',
        'Coincidencia principal: apps/web/src/modulos/asistencia/asistencia.servicio.ts:35-72',
        'Fragmento: función completa (37 líneas). El modelo lo lee y cuesta tokens como cualquier texto.',
        'Costo de la búsqueda: $0.00 en APIs de pago.',
      ];
    }

    const newEntry: CommandOutput = {
      id: `cmd-${++commandCounter}`,
      command: trimmed,
      output: lines,
    };

    setHistory((prev) => [...prev, newEntry]);
    setInputVal('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      executeCommand(inputVal);
    }
  };

  const resetTerminal = () => {
    setHistory([]);
  };

  const copyAll = () => {
    const text = history.map((h) => `$ ${h.command}\n${h.output.join('\n')}`).join('\n\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history]);

  return (
    <section id="terminal-cli" className="scroll-mt-20 border-b border-[#30363D] bg-[#0D1117] py-16 sm:py-24 relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute top-1/2 right-1/4 -translate-y-1/2 w-[600px] h-[350px] bg-[#58A6FF]/5 blur-[130px] rounded-full pointer-events-none" />

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Encabezado */}
        <div className="text-center max-w-3xl mx-auto">
          <p className="text-xs font-mono font-bold uppercase tracking-[0.2em] text-[#00E5FF] flex items-center justify-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00E5FF] animate-pulse" />
            CONSOLA INTERACTIVA DE DESARROLLADOR
          </p>
          <h2 className="mt-3 text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight text-white">
            Simulador de Terminal SYNRAG CLI
          </h2>
          <p className="mt-3 text-sm sm:text-base text-[#8B949E]">
            Esta terminal es una simulación en el navegador con datos ficticios: no ejecuta nada en tu equipo. Sirve para ver la forma de la salida de cada comando; las cifras que muestra son las medidas por el autor el 6-oct-2026.
          </p>
        </div>

        {/* Botones de Comandos Rápidos */}
        <div className="mt-8 flex flex-wrap items-center justify-center gap-2 max-w-4xl mx-auto">
          <span className="text-xs font-mono text-[#8B949E] mr-1">Comandos rápidos:</span>
          {PRESET_COMMANDS.map((cmd) => (
            <button
              key={cmd}
              onClick={() => executeCommand(cmd)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#161B22] border border-[#30363D] hover:border-[#00E5FF] text-[#8B949E] hover:text-white font-mono text-xs font-bold transition-all cursor-pointer active:scale-95"
            >
              <Play className="w-3 h-3 text-[#00E5FF]" />
              {cmd}
            </button>
          ))}
        </div>

        {/* Ventana de Terminal */}
        <div className="mt-8 max-w-5xl mx-auto rounded-2xl border border-[#30363D] bg-[#0D1117] shadow-2xl overflow-hidden font-mono">
          {/* Barra Superior estilo macOS */}
          <div className="p-3.5 bg-[#161B22] border-b border-[#30363D] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#FF7B72]/80 inline-block" />
              <span className="w-3 h-3 rounded-full bg-[#E3B341]/80 inline-block" />
              <span className="w-3 h-3 rounded-full bg-[#7EE787]/80 inline-block" />
              <span className="ml-2 text-xs font-bold text-white flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-[#00E5FF]" />
                dev@equipo: ~/proyectos/mi-monorepo
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={copyAll}
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#21262D] hover:bg-[#30363D] text-xs text-[#8B949E] hover:text-white transition-all cursor-pointer"
                title="Copiar salida de terminal"
              >
                {copied ? <Check className="w-3 h-3 text-[#7EE787]" /> : <Copy className="w-3 h-3" />}
                <span>{copied ? 'Copiado' : 'Copiar'}</span>
              </button>

              <button
                onClick={resetTerminal}
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#21262D] hover:bg-[#30363D] text-xs text-[#8B949E] hover:text-white transition-all cursor-pointer"
                title="Reiniciar terminal"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Limpiar</span>
              </button>
            </div>
          </div>

          {/* Área de Historial de Comandos */}
          <div className="p-4 sm:p-6 text-xs sm:text-sm text-[#C9D1D9] min-h-[320px] max-h-[460px] overflow-y-auto space-y-4 leading-relaxed">
            {history.map((item) => (
              <div key={item.id} className="space-y-1.5">
                <div className="flex items-center gap-2 text-white font-bold">
                  <span className="text-[#00E5FF]">dev@equipo</span>
                  <span className="text-[#8B949E]">:</span>
                  <span className="text-[#58A6FF]">~</span>
                  <span className="text-[#8B949E]">$</span>
                  <span className="text-[#7EE787]">{item.command}</span>
                </div>
                <div className="pl-4 space-y-0.5 text-slate-300">
                  {item.output.map((line, idx) => (
                    <div 
                      key={idx} 
                      className={
                        line.startsWith('ALERTA') || line.includes('[CRITICAL]') 
                          ? 'text-[#FF7B72] font-semibold' 
                          : line.startsWith('[OK]') || line.includes('Active: active')
                            ? 'text-[#7EE787]'
                            : line.startsWith('[SYNRAG]') || line.includes('SYNTAX RAG')
                              ? 'text-[#00E5FF] font-bold'
                              : line.includes('[WARNING]')
                                ? 'text-[#E3B341]'
                                : 'text-[#8B949E]'
                      }
                    >
                      {line}
                    </div>
                  ))}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Línea de Input Activo */}
          <div className="p-3.5 bg-[#161B22] border-t border-[#30363D] flex items-center gap-2">
            <span className="text-[#00E5FF] font-bold text-xs sm:text-sm flex items-center gap-1">
              <ChevronRight className="w-4 h-4" />
            </span>
            <input
              type="text"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Escribe un comando (ej: SYNRAG stats o SYNRAG 'asistenciaServicio') y presiona Enter..."
              className="w-full bg-transparent text-xs sm:text-sm font-mono text-white placeholder-[#8B949E] focus:outline-none"
            />
            <button
              onClick={() => executeCommand(inputVal)}
              className="px-3 py-1.5 rounded-lg bg-[#00E5FF] hover:bg-[#00c8e0] text-[#0D1117] text-xs font-black transition-all cursor-pointer shrink-0"
            >
              Ejecutar
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};
