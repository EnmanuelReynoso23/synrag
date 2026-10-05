import { useState } from 'react';
import { ArrowRight, Check, Copy, Sparkles, Terminal, ShieldAlert, Zap, Gauge } from 'lucide-react';

export const Hero: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'ast' | 'impact' | 'cache'>('ast');
  const [commandCopied, setCommandCopied] = useState(false);

  const copyCommand = (cmd: string) => {
    navigator.clipboard.writeText(cmd);
    setCommandCopied(true);
    setTimeout(() => setCommandCopied(false), 2000);
  };

  return (
    <section className="relative overflow-hidden border-b border-[#30363D] bg-[#0D1117] bg-ast-grid pt-12 pb-16 sm:pt-16 sm:pb-24 lg:pt-20 lg:pb-28">
      {/* Luz ambiental radial Neón Cian y Azul Eléctrico */}
      <div 
        aria-hidden="true" 
        className="pointer-events-none absolute -top-32 left-1/2 -translate-x-1/2 w-[850px] h-[450px] bg-gradient-to-b from-[#00E5FF]/15 via-[#58A6FF]/10 to-transparent blur-3xl -z-10" 
      />

      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid items-center gap-10 lg:grid-cols-12 lg:gap-12">
          {/* Columna Izquierda: Mensaje Central */}
          <div className="lg:col-span-7 text-center lg:text-left">
            {/* Eyebrow badge */}
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#161B22] border border-[#30363D] text-xs font-mono text-[#00E5FF] mb-5">
              <span className="flex h-2 w-2 rounded-full bg-[#00E5FF] animate-pulse"></span>
              <span>AST-Native MCP Engine · Zero-Token Cache</span>
            </div>

            {/* Titular Principal */}
            <h1 className="text-3xl font-black leading-[1.08] tracking-tight text-white sm:text-4xl md:text-5xl lg:text-[2.85rem] xl:text-[3.25rem]">
              <span className="block">Búsqueda Semántica en Código</span>
              <span className="block bg-gradient-to-r from-white via-[#00E5FF] to-[#58A6FF] bg-clip-text text-transparent">
                con 0 Tokens de API
              </span>
              <span className="block text-[#8B949E] text-2xl sm:text-3xl lg:text-3xl font-bold mt-1">
                y respuesta local en &lt; 1 ms
              </span>
            </h1>

            {/* Descripción técnica */}
            <p className="mt-5 max-w-2xl mx-auto lg:mx-0 text-sm leading-6 text-[#8B949E] sm:text-base sm:leading-7 font-normal">
              Olvídate de partir funciones por la mitad o saturar ventanas de contexto. SyntaxRAG analiza quirúrgicamente el <strong className="font-bold text-white">Árbol de Sintaxis Abstracta (AST)</strong> con <strong className="font-bold text-[#00E5FF]">Tree-sitter</strong>, previene código roto con un <strong className="font-bold text-[#FF7B72]">Grafo de Impacto de 23,364 aristas</strong> y responde en milisegundos a costo <strong className="font-bold text-[#7EE787]">$0.00</strong> desde LanceDB local.
            </p>

            {/* Botones de acción principales */}
            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-3.5">
              <a
                href="#playground"
                className="w-full sm:w-auto inline-flex min-h-[3.25rem] items-center justify-center gap-2.5 rounded-xl bg-[#00E5FF] px-7 text-base font-black text-[#0D1117] shadow-[0_0_25px_-5px_rgba(0,229,255,0.4)] transition-all duration-200 hover:bg-[#00E5FF]/90 hover:shadow-[0_0_35px_rgba(0,229,255,0.6)] cursor-pointer active:scale-95"
              >
                <Sparkles className="h-4 w-4" />
                Probar Simulador AST en Vivo
                <ArrowRight className="h-4 w-4" />
              </a>

              <a
                href="#metricas"
                className="w-full sm:w-auto inline-flex min-h-[3.25rem] items-center justify-center gap-2 rounded-xl border border-[#30363D] bg-[#161B22] px-6 text-sm font-bold text-white shadow-sm transition-all duration-200 hover:border-[#8B949E] hover:bg-[#21262D] cursor-pointer"
              >
                Ver Métricas Reales
              </a>

              {/* Botón rápido de copia de terminal */}
              <div className="w-full sm:w-auto inline-flex min-h-[3.25rem] items-center justify-between gap-3 rounded-xl border border-[#30363D] bg-[#161B22] px-4 py-2 font-mono text-xs text-[#8B949E]">
                <div className="flex items-center gap-1.5">
                  <Terminal className="h-3.5 w-3.5 text-[#00E5FF]" />
                  <span className="font-bold text-white">SYNRAG</span>
                  <span className="text-[#8B949E]">asistenciaServicio</span>
                </div>
                <button
                  onClick={() => copyCommand('SYNRAG "asistenciaServicio"')}
                  className="p-1 hover:text-[#00E5FF] transition-colors cursor-pointer"
                  title="Copiar comando"
                >
                  {commandCopied ? <Check className="h-3.5 w-3.5 text-[#7EE787]" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
              </div>
            </div>

            {/* Badges de métricas inferiores */}
            <div className="mt-8 pt-6 border-t border-[#30363D] grid grid-cols-3 gap-4 text-center lg:text-left">
              <div>
                <dt className="text-xl sm:text-2xl font-black text-white">95.5k</dt>
                <dd className="text-xs font-bold text-[#8B949E]">Fragmentos AST</dd>
              </div>
              <div>
                <dt className="text-xl sm:text-2xl font-black text-[#00E5FF]">&lt; 1 ms</dt>
                <dd className="text-xs font-bold text-[#8B949E]">Caché Semántica</dd>
              </div>
              <div>
                <dt className="text-xl sm:text-2xl font-black text-[#7EE787]">$0.00</dt>
                <dd className="text-xs font-bold text-[#8B949E]">0 Tokens Gastados</dd>
              </div>
            </div>
          </div>

          {/* Columna Derecha: Tarjeta Visual Interactiva Dark Mode */}
          <div className="lg:col-span-5 flex justify-center">
            <div className="w-full max-w-lg rounded-2xl sm:rounded-3xl border border-[#30363D] bg-[#161B22] p-5 sm:p-6 shadow-2xl shadow-black/80">
              {/* Header de la tarjeta */}
              <div className="flex items-center justify-between pb-4 border-b border-[#30363D]">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1.5">
                    <span className="w-3 h-3 rounded-full bg-[#FF5F56]"></span>
                    <span className="w-3 h-3 rounded-full bg-[#FFBD2E]"></span>
                    <span className="w-3 h-3 rounded-full bg-[#27C93F]"></span>
                  </div>
                  <span className="ml-2 font-mono text-xs font-bold text-[#8B949E]">
                    asistoya-web/asistencia.servicio.ts
                  </span>
                </div>
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-black uppercase bg-[#7EE787]/15 text-[#7EE787] border border-[#7EE787]/30">
                  <Zap className="w-3 h-3" /> 0 Tokens
                </span>
              </div>

              {/* Selector de Pestañas de Inspección */}
              <div className="flex gap-1.5 mt-4 p-1 rounded-xl bg-[#0D1117] text-xs font-bold text-[#8B949E]">
                <button
                  onClick={() => setActiveTab('ast')}
                  className={`flex-1 py-1.5 rounded-lg transition-all flex items-center justify-center gap-1.5 ${
                    activeTab === 'ast' ? 'bg-[#21262D] text-[#00E5FF] font-black shadow-sm' : 'hover:text-white'
                  }`}
                >
                  <Zap className="w-3.5 h-3.5" />
                  Bloque AST
                </button>
                <button
                  onClick={() => setActiveTab('impact')}
                  className={`flex-1 py-1.5 rounded-lg transition-all flex items-center justify-center gap-1.5 ${
                    activeTab === 'impact' ? 'bg-[#21262D] text-[#FF7B72] font-black shadow-sm' : 'hover:text-white'
                  }`}
                >
                  <ShieldAlert className="w-3.5 h-3.5" />
                  Grafo (9)
                </button>
                <button
                  onClick={() => setActiveTab('cache')}
                  className={`flex-1 py-1.5 rounded-lg transition-all flex items-center justify-center gap-1.5 ${
                    activeTab === 'cache' ? 'bg-[#21262D] text-[#7EE787] font-black shadow-sm' : 'hover:text-white'
                  }`}
                >
                  <Gauge className="w-3.5 h-3.5" />
                  Métricas
                </button>
              </div>

              {/* Contenido según pestaña */}
              <div className="mt-4">
                {activeTab === 'ast' && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-xs font-mono text-[#8B949E]">
                      <span className="font-bold text-[#00E5FF]">export const asistenciaServicio = ...</span>
                      <span className="bg-[#21262D] text-slate-300 px-2 py-0.5 rounded font-bold">Líneas 35-72</span>
                    </div>

                    <pre className="p-3.5 rounded-xl bg-[#0D1117] border border-[#30363D] text-slate-100 font-mono text-xs leading-relaxed overflow-x-auto">
                      <code>{`export const asistenciaServicio = {
  async registrarPase(payload) {
    // Validación de centro y biometría
    await validarPoliticaCentro(payload);
    return await persistirAsistencia(payload);
  }
};`}</code>
                    </pre>

                    <div className="flex items-center justify-between p-2.5 rounded-xl bg-[#00E5FF]/10 border border-[#00E5FF]/20 text-xs text-[#00E5FF]">
                      <span className="font-bold">Tree-sitter Chunker:</span>
                      <span className="font-medium text-slate-200">Conserva docstrings y firma íntegra</span>
                    </div>
                  </div>
                )}

                {activeTab === 'impact' && (
                  <div className="space-y-2.5">
                    <div className="flex items-center gap-2 p-2.5 rounded-xl bg-[#FF7B72]/15 border border-[#FF7B72]/30 text-[#FF7B72] text-xs font-bold">
                      <ShieldAlert className="w-4 h-4 shrink-0" />
                      <span>9 archivos consumen este servicio en asistoya-web</span>
                    </div>

                    <ul className="space-y-1.5 text-xs font-mono text-slate-300">
                      <li className="flex items-center justify-between p-2 rounded-lg bg-[#0D1117] border border-[#30363D]">
                        <span className="truncate">apps/web/src/demo/demoData.ts</span>
                        <span className="text-[#FF7B72] font-bold ml-2">CRITICAL</span>
                      </li>
                      <li className="flex items-center justify-between p-2 rounded-lg bg-[#0D1117] border border-[#30363D]">
                        <span className="truncate">apps/web/src/modulos/kiosco/PaginaKiosco.tsx</span>
                        <span className="text-[#FF7B72] font-bold ml-2">CRITICAL</span>
                      </li>
                      <li className="flex items-center justify-between p-2 rounded-lg bg-[#0D1117] border border-[#30363D]">
                        <span className="truncate">apps/web/src/modulos/profesor/PaseDeLista.tsx</span>
                        <span className="text-[#E3B341] font-bold ml-2">WARNING</span>
                      </li>
                    </ul>

                    <p className="text-[11px] text-[#8B949E] font-medium italic text-center">
                      Previene bugs inyectando dependientes antes de refactorizar.
                    </p>
                  </div>
                )}

                {activeTab === 'cache' && (
                  <div className="space-y-3 py-1">
                    <div className="grid grid-cols-2 gap-3 text-center">
                      <div className="p-3 rounded-xl bg-[#0D1117] border border-[#30363D]">
                        <span className="text-xs font-bold text-[#8B949E] block">Latencia Media</span>
                        <span className="text-xl font-black text-white">0.38 ms</span>
                      </div>
                      <div className="p-3 rounded-xl bg-[#00E5FF]/10 border border-[#00E5FF]/20">
                        <span className="text-xs font-bold text-[#00E5FF] block">Tokens de API</span>
                        <span className="text-xl font-black text-[#00E5FF]">0 Tokens</span>
                      </div>
                    </div>

                    <div className="p-3 rounded-xl bg-[#7EE787]/10 border border-[#7EE787]/20 text-xs text-[#7EE787] font-medium">
                      <p className="font-bold mb-1">Caché Semántica Vectorial:</p>
                      <p className="text-slate-300">Consultas semánticamente equivalentes devuelven resultados idénticos sin recalcular ni llamar a OpenAI/Gemini.</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
