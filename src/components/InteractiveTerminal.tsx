import { useState, useRef, useEffect } from 'react';
import { Terminal, Play, RotateCcw, Copy, Check, ChevronRight } from 'lucide-react';

interface CommandOutput {
  id: string;
  command: string;
  output: string[];
}

const PRESET_COMMANDS = [
  'SYNRAG "asistenciaServicio"',
  'SYNRAG --stats',
  'SYNRAG --graph "reconocimientoFacial"',
  'SYNRAG --daemon',
  'help',
];

let commandCounter = 1;

export const InteractiveTerminal: React.FC = () => {
  const [history, setHistory] = useState<CommandOutput[]>([
    {
      id: 'init-1',
      command: 'SYNRAG "asistenciaServicio"',
      output: [
        '[SYNRAG v2.4] Consultando índice AST LanceDB local en ~/proyectos/mi-monorepo...',
        '[OK] Árbol Tree-sitter parseado en 4.2ms | FlashRank ONNX Rerank: 98.4%',
        '--------------------------------------------------------------------------------',
        'ARCHIVO: apps/web/src/modulos/asistencia/asistencia.servicio.ts:35-72',
        'SÍMBOLO: export const asistenciaServicio = { ... }',
        'TOKENS: 172 tokens extraídos (ahorro: 94.6% vs archivo completo)',
        '--------------------------------------------------------------------------------',
        'ALERTA DE GRAFO DE IMPACTO (Riesgo: CRITICAL):',
        '  → apps/web/src/modulos/kiosco/TerminalBiometrico.tsx:14 (importa registrarPase)',
        '  → apps/web/src/modulos/estudiantes/hooks/useEstudiantes.ts:8 (importa validarAsistencia)',
        '  → apps/web/src/modulos/profesor/componentes/PaseDeLista.tsx:22 (importa asistenciaServicio)',
        'Estado: Listo para inyección en MCP (~18ms total).',
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
        'Comandos disponibles en SYNRAG CLI (Linux / macOS):',
        '  SYNRAG "<query>"               Busca símbolo o función sintáctica con AST + FlashRank.',
        '  SYNRAG --stats                 Muestra estadísticas de fragmentos, caché y consumo.',
        '  SYNRAG --graph "<símbolo>"     Calcula el radio de explosión (blast radius) de dependencias.',
        '  SYNRAG --daemon                Consulta el estado del demonio systemd reactivo.',
        '  SYNRAG --clear-cache           Reinicia la memoria caché de microsegundos (<1ms).',
        '  clear                          Limpia la pantalla de la terminal.',
      ];
    } else if (trimmed.includes('--stats')) {
      lines = [
        '================================================================================',
        '               MÉTRICAS DEL MOTOR SYNTAX RAG (LOCAL)                  ',
        '================================================================================',
        'Repositorios indexados:     mi-monorepo, notas-ia, proyectos',
        'Fragmentos AST totales:     95,502 bloques de código sintáctico',
        'Aristas en el grafo: 23,364 dependencias y llamadas mapeadas',
        'Latencia promedio de caché: 0.8ms (<1ms Zero-Token)',
        'Tokens ahorrados acumulados: 124,500,000 tokens',
        'Costo en API de la nube:   $0.00 USD (Inferencia 100% en CPU local)',
        'Uso de memoria residente:   12.3 MB RAM (Daemon watcher)',
      ];
    } else if (trimmed.includes('--daemon')) {
      lines = [
        '● lancedb-watcher.service - Daemon reactivo de indexación AST',
        '     Loaded: loaded (~/.config/systemd/user/lancedb-watcher.service; enabled)',
        '     Active: active (running) desde las 08:00:15 UTC',
        '   Main PID: 3239 (python3 -m synrag.daemon)',
        '      Tasks: 4 (limit: 18884)',
        '     Memory: 12.3M',
        '        CPU: 0.1% en reposo (~18ms pico al guardar con Ctrl+S)',
        '     Status: "Vigilando 2,450 archivos en ~/proyectos/mi-monorepo"',
      ];
    } else if (trimmed.includes('--graph')) {
      lines = [
        'ANALIZANDO GRAFO DE IMPACTO DIRECTO:',
        'Símbolo objetivo: reconocimientoFacial',
        'Archivo origen: apps/web/src/modulos/reconocimiento-facial/reconocimiento.servicio.ts',
        '--------------------------------------------------------------------------------',
        '[CRITICAL] apps/web/src/modulos/kiosco/TerminalBiometrico.tsx (Línea 29)',
        '[CRITICAL] apps/web/src/modulos/asistencia/asistencia.hook.ts (Línea 44)',
        '[WARNING]  apps/web/src/modulos/estudiantes/componentes/CredencialEstudiante.tsx (Línea 12)',
        '[INFO]     apps/web/src/services/telemetria/biometriaAudit.ts (Línea 5)',
        'Conclusión: Cualquier cambio en la firma de reconocimientoFacial afecta 4 archivos clave.',
      ];
    } else if (trimmed.includes('--clear-cache')) {
      lines = [
        'Vaciando tabla de caché de microsegundos en LanceDB...',
        '[OK] 4,120 entradas purgadas.',
        '[OK] Re-calentamiento completado en 14ms.',
        'Zero-Token Cache lista para recibir consultas.',
      ];
    } else {
      lines = [
        `[SYNRAG] Búsqueda AST para query: "${trimmed.replace(/^SYNRAG\s*/i, '').replace(/["']/g, '')}"`,
        '[OK] Recuperados 3 fragmentos candidatos en 6.1ms vía LanceDB.',
        '[OK] Reranker FlashRank TinyBERT ONNX aplicado (Relevancia: 95.8%).',
        '--------------------------------------------------------------------------------',
        'Coincidencia principal: apps/web/src/modulos/asistencia/asistencia.servicio.ts:35-72',
        'Fragmento extraído: Función sintáctica completa (37 líneas, 168 tokens).',
        'Consumo de red: 0 bytes | Cuota de tokens: $0.00 gastados.',
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
            Ejecuta comandos reales del motor en esta terminal interactiva. Experimenta la velocidad de respuesta, el parseo de árboles y las alertas del grafo de impacto como ocurren en tu equipo.
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
              placeholder="Escribe un comando (ej: SYNRAG --stats o SYNRAG 'asistenciaServicio') y presiona Enter..."
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
