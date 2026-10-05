import { useState } from 'react';
import { Zap, ShieldAlert, Sparkles, ArrowRight, Check, Copy, Layers } from 'lucide-react';


export const Hero: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'cli' | 'mcp' | 'impact'>('cli');
  const [commandCopied, setCommandCopied] = useState(false);

  const copyCommand = (cmd: string) => {
    navigator.clipboard.writeText(cmd);
    setCommandCopied(true);
    setTimeout(() => setCommandCopied(false), 2000);
  };

  return (
    <section className="relative pt-12 pb-20 md:pt-20 md:pb-32 overflow-hidden">
      {/* Background glow meshes */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[650px] h-[350px] bg-gradient-to-tr from-[#00e5ff]/15 via-[#cba6f7]/10 to-transparent blur-[120px] rounded-full pointer-events-none -z-10" />
      <div className="absolute top-12 left-10 w-72 h-72 bg-[#89b4fa]/10 blur-[90px] rounded-full pointer-events-none -z-10" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Top Badges */}
        <div className="flex flex-wrap items-center justify-center gap-3 mb-6">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#181825] border border-[#313244] shadow-sm text-xs font-mono text-[#cdd6f4]">
            <span className="flex h-2 w-2 rounded-full bg-[#00e5ff] animate-pulse"></span>
            <span className="text-[#00e5ff] font-semibold">SYNTAX RAG v1.2</span>
            <span className="text-[#585b70]">|</span>
            <span>AST-Native MCP Engine</span>
          </div>

          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-950/40 border border-emerald-500/30 text-emerald-400 text-xs font-mono">
            <Zap className="w-3.5 h-3.5 text-emerald-400" />
            <span>Hot-Reload ~18ms por Ctrl+S</span>
          </div>
        </div>

        {/* Main Headline */}
        <div className="text-center max-w-4xl mx-auto mb-8">
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white mb-6 leading-[1.12]">
            Inteligencia de Código Local para{' '}
            <span className="bg-gradient-to-r from-[#00e5ff] via-[#89b4fa] to-[#cba6f7] bg-clip-text text-transparent">
              Agentes y Desarrolladores
            </span>
          </h1>
          <p className="text-lg sm:text-xl text-[#a6adc8] max-w-2xl mx-auto leading-relaxed">
            Elimina reindexaciones lentas y lecturas ciegas de archivos enteros. Synrag analiza bloques
            sintácticos completos con <span className="text-white font-medium">Tree-sitter</span>, protege tus cambios con un{' '}
            <span className="text-[#f38ba8] font-medium">Grafo de Impacto</span> preventivo y responde en{' '}
            <span className="text-[#00e5ff] font-medium">&lt; 1 ms</span> a costo <span className="text-[#a6e3a1] font-medium">$0.00</span>.
          </p>
        </div>

        {/* Action Buttons & Quick Command */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-14">
          <a
            href="#playground"
            className="w-full sm:w-auto px-7 py-3.5 rounded-xl bg-gradient-to-r from-[#00e5ff] to-[#89b4fa] text-[#11111b] font-bold text-sm tracking-wide shadow-[0_0_30px_-5px_rgba(0,229,255,0.4)] hover:shadow-[0_0_40px_0px_rgba(0,229,255,0.6)] hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-2 cursor-pointer"
          >
            <Sparkles className="w-4 h-4" />
            Probar Simulador AST en Vivo
            <ArrowRight className="w-4 h-4 ml-1" />
          </a>

          <a
            href="#arquitectura"
            className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-[#1e1e2e]/80 hover:bg-[#313244] border border-[#45475a] text-white font-medium text-sm transition-all flex items-center justify-center gap-2 hover:border-[#89b4fa]/50"
          >
            <Layers className="w-4 h-4 text-[#cba6f7]" />
            Ver Arquitectura (7 Fases)
          </a>

          {/* Quick copy command snippet */}
          <div className="w-full sm:w-auto flex items-center justify-between sm:justify-start gap-3 px-4 py-3 rounded-xl bg-[#11111b] border border-[#313244] font-mono text-xs text-[#a6adc8]">
            <span className="text-[#00e5ff]">$</span>
            <span className="text-slate-200">syntaxrag "asistenciaServicio"</span>
            <button
              onClick={() => copyCommand('syntaxrag "asistenciaServicio"')}
              className="p-1 hover:text-white transition-colors cursor-pointer"
              title="Copiar comando"
            >
              {commandCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        {/* Hero Interactive Terminal Window (Catppuccin Mocha aesthetic) */}
        <div className="max-w-4xl mx-auto rounded-2xl border border-[#313244] bg-[#11111b]/95 shadow-[0_20px_60px_-15px_rgba(0,0,0,0.8)] overflow-hidden transition-all">
          {/* Terminal Window Header */}
          <div className="px-4 py-3 bg-[#181825] border-b border-[#313244] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#f38ba8]/90"></span>
              <span className="w-3 h-3 rounded-full bg-[#f9e2af]/90"></span>
              <span className="w-3 h-3 rounded-full bg-[#a6e3a1]/90"></span>
              <span className="ml-3 font-mono text-xs text-[#585b70]">syntaxrag-node · cachyos-x86_64</span>
            </div>

            {/* Terminal Tab Switchers */}
            <div className="flex items-center gap-1.5 p-1 bg-[#11111b] rounded-lg border border-[#313244]/60 text-xs font-mono">
              <button
                onClick={() => setActiveTab('cli')}
                className={`px-3 py-1 rounded-md transition-all cursor-pointer ${
                  activeTab === 'cli' ? 'bg-[#313244] text-[#00e5ff] font-bold shadow-sm' : 'text-[#a6adc8] hover:text-white'
                }`}
              >
                CLI Output
              </button>
              <button
                onClick={() => setActiveTab('mcp')}
                className={`px-3 py-1 rounded-md transition-all cursor-pointer ${
                  activeTab === 'mcp' ? 'bg-[#313244] text-[#cba6f7] font-bold shadow-sm' : 'text-[#a6adc8] hover:text-white'
                }`}
              >
                MCP Protocol
              </button>
              <button
                onClick={() => setActiveTab('impact')}
                className={`px-3 py-1 rounded-md transition-all cursor-pointer ${
                  activeTab === 'impact' ? 'bg-[#313244] text-[#f38ba8] font-bold shadow-sm' : 'text-[#a6adc8] hover:text-white'
                }`}
              >
                Grafo de Impacto
              </button>
            </div>
          </div>

          {/* Terminal Body */}
          <div className="p-5 font-mono text-xs sm:text-sm leading-relaxed overflow-x-auto text-[#cdd6f4]">
            {activeTab === 'cli' && (
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-[#a6adc8]">
                  <span className="text-[#a6e3a1]">reyno@cachyos</span>
                  <span className="text-[#585b70]">:</span>
                  <span className="text-[#89b4fa]">~</span>
                  <span className="text-[#cba6f7]">$</span>
                  <span className="text-white font-medium">syntaxrag "useAsistenciaServicio" --project asistoya-web</span>
                </div>

                {/* Instant Cache Hit badge */}
                <div className="flex flex-wrap items-center gap-3 p-2.5 rounded-lg bg-[#181825] border border-[#313244]">
                  <div className="inline-flex items-center gap-1.5 text-xs font-bold text-[#00e5ff]">
                    <Zap className="w-3.5 h-3.5" />
                    <span>⚡ CACHE HIT</span>
                  </div>
                  <span className="text-xs text-[#a6adc8]">
                    Latencia: <strong className="text-white">0.38 ms</strong> · Costo: <strong className="text-[#a6e3a1]">$0.00</strong> · Tokens: <strong className="text-[#a6e3a1]">0</strong>
                  </span>
                  <span className="ml-auto text-xs px-2 py-0.5 rounded bg-[#313244] text-[#f9e2af]">
                    FlashRank Neural: 98.7%
                  </span>
                </div>

                {/* Code block output */}
                <div className="rounded-lg bg-[#0d1117] border border-[#30363d] p-3 text-xs overflow-x-auto">
                  <div className="flex items-center justify-between text-[#8b949e] border-b border-[#30363d] pb-2 mb-2 font-mono">
                    <span className="text-[#89b4fa]">asistoya-web/src/services/asistenciaServicio.ts:45-62</span>
                    <span className="text-[#cba6f7]">[Hook AST]</span>
                  </div>
                  <pre className="text-[#cdd6f4] leading-5">
                    <code>
                      <span className="text-[#f38ba8]">export const</span> <span className="text-[#89b4fa]">useAsistenciaServicio</span> = (<span className="text-[#fab387]">institucionId</span>: <span className="text-[#f9e2af]">string</span>) =&gt; &#123;{'\n'}
                      {'  '}<span className="text-[#f38ba8]">const</span> [registros, setRegistros] = <span className="text-[#89b4fa]">useState</span>&lt;<span className="text-[#f9e2af]">AsistenciaRecord</span>[]&gt;([]);{'\n'}
                      {'  '}<span className="text-[#f38ba8]">const</span> [cargando, setCargando] = <span className="text-[#89b4fa]">useState</span>(<span className="text-[#fab387]">false</span>);{'\n'}
                      {'\n'}
                      {'  '}<span className="text-[#585b70]">// Validación biométrica y registro en tiempo real</span>{'\n'}
                      {'  '}<span className="text-[#f38ba8]">const</span> <span className="text-[#89b4fa]">registrarAsistencia</span> = <span className="text-[#89b4fa]">useCallback</span>(<span className="text-[#f38ba8]">async</span> (<span className="text-[#fab387]">datos</span>) =&gt; &#123;{'\n'}
                      {'    '}<span className="text-[#f38ba8]">const</span> res = <span className="text-[#f38ba8]">await</span> api.<span className="text-[#89b4fa]">post</span>(<span className="text-[#a6e3a1]">`/asistencias/$&#123;institucionId&#125;`</span>, datos);{'\n'}
                      {'    '}setRegistros(prev =&gt; [res.data, ...prev]);{'\n'}
                      {'    '}<span className="text-[#f38ba8]">return</span> res.status === <span className="text-[#fab387]">200</span>;{'\n'}
                      {'  '}&#125;, [institucionId]);{'\n'}
                      {'  '}<span className="text-[#f38ba8]">return</span> &#123; registros, cargando, registrarAsistencia &#125;;{'\n'}
                      &#125;;
                    </code>
                  </pre>
                </div>

                {/* Impact Graph warning */}
                <div className="flex items-start gap-2.5 p-3 rounded-lg bg-[#f38ba8]/10 border border-[#f38ba8]/30 text-xs text-[#f38ba8]">
                  <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
                  <div>
                    <strong className="font-semibold">⚠️ GRAFO DE IMPACTO:</strong> Este hook es consumido activamente por{' '}
                    <span className="underline font-bold">14 archivos</span> en el monorepo (incluyendo{' '}
                    <code>PaseDeLista.tsx</code> y <code>KioskoBiometrico.tsx</code>). Cualquier cambio de firma romperá componentes dependientes.
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'mcp' && (
              <div className="space-y-3">
                <div className="text-[#8b949e]">// Protocolo Model Context Protocol (stdio JSON-RPC)</div>
                <div className="text-[#00e5ff] font-bold">--&gt; Request: tools/call</div>
                <pre className="p-3 bg-[#0d1117] rounded-lg border border-[#30363d] text-xs text-[#a6adc8]">
{`{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "search_desktop",
    "arguments": {
      "query": "useAsistenciaServicio",
      "project": "asistoya-web",
      "limit": 1
    }
  },
  "id": "agy-call-492"
}`}
                </pre>
                <div className="text-[#a6e3a1] font-bold">&lt;-- Response: desktop-lancedb (0.38 ms)</div>
                <pre className="p-3 bg-[#0d1117] rounded-lg border border-[#30363d] text-xs text-[#a6e3a1]">
{`{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "⚡ [SyntaxRAG] 1 resultado exacto con Grafo de Impacto:\n\nsrc/services/asistenciaServicio.ts:45-62\n⚠️ GRAFO DE IMPACTO: 'useAsistenciaServicio' es consumido por 14 archivos."
      }
    ]
  },
  "id": "agy-call-492"
}`}
                </pre>
              </div>
            )}

            {activeTab === 'impact' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-[#a6adc8] pb-1 border-b border-[#313244]">
                  <span className="text-white font-semibold">Red de Consumidores Directos para `useAsistenciaServicio`:</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-red-950/60 text-red-400 border border-red-500/30">14 dependencias detectadas</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <div className="p-2.5 rounded-lg bg-[#181825] border border-red-500/40 flex items-center justify-between">
                    <div>
                      <div className="text-white font-medium">PaseDeLista.tsx</div>
                      <div className="text-[#8b949e]">src/features/asistencia/</div>
                    </div>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-300 font-bold">CRÍTICO</span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-[#181825] border border-red-500/40 flex items-center justify-between">
                    <div>
                      <div className="text-white font-medium">KioskoBiometrico.tsx</div>
                      <div className="text-[#8b949e]">src/components/</div>
                    </div>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-300 font-bold">CRÍTICO</span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-[#181825] border border-amber-500/40 flex items-center justify-between">
                    <div>
                      <div className="text-white font-medium">ReportesMensuales.tsx</div>
                      <div className="text-[#8b949e]">src/pages/</div>
                    </div>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold">MODERADO</span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-[#181825] border border-blue-500/40 flex items-center justify-between">
                    <div>
                      <div className="text-white font-medium">useAuditoriaPase.ts</div>
                      <div className="text-[#8b949e]">src/hooks/</div>
                    </div>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold">INFORMATIVO</span>
                  </div>
                </div>
                <p className="text-[11px] text-[#a6adc8] italic">
                  * El Grafo de Impacto se recalcula en segundo plano vía AST cada vez que guardas un archivo con Ctrl+S (~18ms).
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};
