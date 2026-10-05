import { useState } from 'react';
import { CONFIG_SNIPPETS } from '../data/mockData';
import { Terminal, Copy, Check, Sparkles, Cpu, Layers } from 'lucide-react';

export const Integrations: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'synrag' | 'claude' | 'antigravity' | 'fish'>('synrag');
  const [copied, setCopied] = useState(false);

  const getActiveCode = () => {
    switch (activeTab) {
      case 'synrag':
        return CONFIG_SNIPPETS.synrag;
      case 'claude':
        return CONFIG_SNIPPETS.claude;
      case 'antigravity':
        return CONFIG_SNIPPETS.antigravity;
      case 'fish':
        return CONFIG_SNIPPETS.fish;
    }
  };

  const copySnippet = () => {
    navigator.clipboard.writeText(getActiveCode());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section id="integracion" className="scroll-mt-20 border-b border-[#30363D] bg-[#0D1117] py-16 sm:py-24 relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute top-1/3 right-1/4 w-[500px] h-[300px] bg-[#00E5FF]/5 blur-[120px] rounded-full pointer-events-none" />

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Encabezado */}
        <div className="text-center max-w-3xl mx-auto">
          <p className="text-xs font-black uppercase tracking-[0.2em] text-[#00E5FF] flex items-center justify-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00E5FF] animate-pulse"></span>
            INTEGRACIÓN DIRECTA · PROTOCOLO MCP & CLI
          </p>
          <h2 className="mt-3 text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight text-white">
            Comando Único SYNRAG & Protocolo MCP
          </h2>
          <p className="mt-3 text-sm sm:text-base text-[#8B949E]">
            Ejecuta el binario unificado en CachyOS para consultar en microsegundos o conéctalo vía MCP a Claude Code y Google Antigravity para dotar a tus agentes de memoria semántica con cero consumo de tokens.
          </p>
        </div>

        {/* Contenedor de Configuración */}
        <div className="mt-12 max-w-4xl mx-auto rounded-2xl border border-[#30363D] bg-[#161B22] shadow-2xl overflow-hidden">
          {/* Pestañas de Selección */}
          <div className="p-3 bg-[#161B22] border-b border-[#30363D] flex flex-wrap gap-2">
            <button
              onClick={() => setActiveTab('synrag')}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all cursor-pointer ${
                activeTab === 'synrag'
                  ? 'bg-[#21262D] text-white border border-[#00E5FF]/40 shadow-sm shadow-[#00E5FF]/10'
                  : 'text-[#8B949E] hover:text-white hover:bg-[#21262D]/50 border border-transparent'
              }`}
            >
              <Terminal className={`w-4 h-4 ${activeTab === 'synrag' ? 'text-[#00E5FF]' : 'text-[#8B949E]'}`} />
              Comando Maestro SYNRAG
            </button>

            <button
              onClick={() => setActiveTab('claude')}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all cursor-pointer ${
                activeTab === 'claude'
                  ? 'bg-[#21262D] text-white border border-[#00E5FF]/40 shadow-sm shadow-[#00E5FF]/10'
                  : 'text-[#8B949E] hover:text-white hover:bg-[#21262D]/50 border border-transparent'
              }`}
            >
              <Cpu className={`w-4 h-4 ${activeTab === 'claude' ? 'text-[#00E5FF]' : 'text-[#8B949E]'}`} />
              Claude Code MCP
            </button>

            <button
              onClick={() => setActiveTab('antigravity')}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all cursor-pointer ${
                activeTab === 'antigravity'
                  ? 'bg-[#21262D] text-white border border-[#00E5FF]/40 shadow-sm shadow-[#00E5FF]/10'
                  : 'text-[#8B949E] hover:text-white hover:bg-[#21262D]/50 border border-transparent'
              }`}
            >
              <Sparkles className={`w-4 h-4 ${activeTab === 'antigravity' ? 'text-[#00E5FF]' : 'text-[#8B949E]'}`} />
              Google Antigravity
            </button>

            <button
              onClick={() => setActiveTab('fish')}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all cursor-pointer ${
                activeTab === 'fish'
                  ? 'bg-[#21262D] text-white border border-[#00E5FF]/40 shadow-sm shadow-[#00E5FF]/10'
                  : 'text-[#8B949E] hover:text-white hover:bg-[#21262D]/50 border border-transparent'
              }`}
            >
              <Layers className={`w-4 h-4 ${activeTab === 'fish' ? 'text-[#00E5FF]' : 'text-[#8B949E]'}`} />
              Fish Shell Abreviaturas
            </button>
          </div>

          {/* Bloque de Código con botón de copia */}
          <div className="relative p-5 bg-[#0D1117] text-[#C9D1D9] overflow-x-auto min-h-[160px]">
            <button
              onClick={copySnippet}
              className="absolute top-4 right-4 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#21262D] hover:bg-[#30363D] text-white text-xs font-bold border border-[#30363D] hover:border-[#00E5FF]/50 transition-all cursor-pointer active:scale-95"
            >
              {copied ? <Check className="w-4 h-4 text-[#7EE787]" /> : <Copy className="w-4 h-4 text-[#8B949E]" />}
              <span>{copied ? '¡Copiado!' : 'Copiar'}</span>
            </button>

            <pre className="font-mono text-xs sm:text-sm leading-relaxed pr-24 text-[#C9D1D9]">
              <code>{getActiveCode()}</code>
            </pre>
          </div>

          {/* Descripción contextual inferior */}
          <div className="p-4 bg-[#161B22] border-t border-[#30363D] text-xs text-[#8B949E] font-medium">
            {activeTab === 'synrag' && (
              <p>
                El comando <strong className="text-white">SYNRAG</strong> (o <code className="bg-[#0D1117] px-1.5 py-0.5 rounded border border-[#30363D] text-[#00E5FF]">synrag</code>) está registrado globalmente en <code className="text-[#58A6FF]">~/.local/bin/SYNRAG</code>. Al ejecutarse sin argumentos abre el workspace multitarea enriquecido con métricas de ahorro y árbol AST en vivo.
              </p>
            )}
            {activeTab === 'claude' && (
              <p>
                Permite a Claude Code invocar la herramienta <strong className="text-white">search_desktop</strong> para consultar los 95,502 fragmentos sintácticos sin exceder límites de lectura de disco ni gastar tokens de contexto.
              </p>
            )}
            {activeTab === 'antigravity' && (
              <p>
                Configurado en <code className="text-[#58A6FF]">~/.gemini/antigravity/mcp/desktop-lancedb</code> para el agente de codificación de Google DeepMind en esta máquina.
              </p>
            )}
            {activeTab === 'fish' && (
              <p>
                Abreviaturas disponibles en tu shell CachyOS: <code className="text-white font-bold">srag</code> (buscar), <code className="text-white font-bold">sstats</code> (métricas de ahorro), <code className="text-white font-bold">swatch</code> (log reactivo).
              </p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};
