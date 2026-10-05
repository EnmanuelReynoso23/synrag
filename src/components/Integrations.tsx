import { useState } from 'react';
import { Terminal, Copy, Check, Sparkles, Monitor, Bot, Wrench } from 'lucide-react';
import { CONFIG_SNIPPETS } from '../data/mockData';


export const Integrations: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'claude' | 'antigravity' | 'cli' | 'systemd' | 'herdr'>('claude');
  const [copied, setCopied] = useState<boolean>(false);

  const getActiveCode = () => {
    switch (activeTab) {
      case 'claude':
        return CONFIG_SNIPPETS.claude;
      case 'antigravity':
        return CONFIG_SNIPPETS.antigravity;
      case 'cli':
        return CONFIG_SNIPPETS.cli;
      case 'systemd':
        return CONFIG_SNIPPETS.systemd;
      case 'herdr':
        return `# Atajos nativos configurados en ~/.config/herdr/herdr.conf
#
# Panel Antigravity CLI (Google Gemini):
Ctrl+B  ->  a

# Panel Claude Code (Anthropic):
Ctrl+B  ->  c

# Hot-Reload automático de LanceDB al guardar en cualquier panel:
Ctrl+S  ->  Tree-sitter parse (~18 ms)`;
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(getActiveCode());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section id="integracion" className="py-20 md:py-32 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#181825] border border-[#313244] text-xs font-mono text-[#00e5ff] mb-4">
            <Wrench className="w-3.5 h-3.5" />
            INTEGRACIÓN Y CONFIGURACIÓN
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mb-4">
            Conecta Synrag a tus Herramientas
          </h2>
          <p className="text-sm sm:text-base text-[#a6adc8]">
            Configura el servidor MCP en segundos o utiliza el comando CLI global directamente desde tu terminal en CachyOS / Linux.
          </p>
        </div>

        {/* Tab Controls */}
        <div className="flex flex-wrap items-center justify-center gap-2 mb-8">
          <button
            onClick={() => setActiveTab('claude')}
            className={`px-4 py-2.5 rounded-xl font-mono text-xs font-medium transition-all cursor-pointer flex items-center gap-2 ${
              activeTab === 'claude'
                ? 'bg-[#00e5ff]/20 text-[#00e5ff] border border-[#00e5ff]/50 shadow-[0_0_15px_-3px_rgba(0,229,255,0.4)]'
                : 'bg-[#181825] text-[#a6adc8] border border-[#313244] hover:text-white hover:border-[#45475a]'
            }`}
          >
            <Bot className="w-4 h-4" />
            Claude Code (~/.claude.json)
          </button>

          <button
            onClick={() => setActiveTab('antigravity')}
            className={`px-4 py-2.5 rounded-xl font-mono text-xs font-medium transition-all cursor-pointer flex items-center gap-2 ${
              activeTab === 'antigravity'
                ? 'bg-[#cba6f7]/20 text-[#cba6f7] border border-[#cba6f7]/50 shadow-[0_0_15px_-3px_rgba(203,166,247,0.4)]'
                : 'bg-[#181825] text-[#a6adc8] border border-[#313244] hover:text-white hover:border-[#45475a]'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            Antigravity CLI (mcp.json)
          </button>

          <button
            onClick={() => setActiveTab('cli')}
            className={`px-4 py-2.5 rounded-xl font-mono text-xs font-medium transition-all cursor-pointer flex items-center gap-2 ${
              activeTab === 'cli'
                ? 'bg-[#a6e3a1]/20 text-[#a6e3a1] border border-[#a6e3a1]/50 shadow-[0_0_15px_-3px_rgba(166,227,161,0.4)]'
                : 'bg-[#181825] text-[#a6adc8] border border-[#313244] hover:text-white hover:border-[#45475a]'
            }`}
          >
            <Terminal className="w-4 h-4" />
            CLI (~/.local/bin/syntaxrag)
          </button>

          <button
            onClick={() => setActiveTab('systemd')}
            className={`px-4 py-2.5 rounded-xl font-mono text-xs font-medium transition-all cursor-pointer flex items-center gap-2 ${
              activeTab === 'systemd'
                ? 'bg-[#fab387]/20 text-[#fab387] border border-[#fab387]/50 shadow-[0_0_15px_-3px_rgba(250,179,135,0.4)]'
                : 'bg-[#181825] text-[#a6adc8] border border-[#313244] hover:text-white hover:border-[#45475a]'
            }`}
          >
            <Wrench className="w-4 h-4" />
            Servicio Systemd Watcher
          </button>

          <button
            onClick={() => setActiveTab('herdr')}
            className={`px-4 py-2.5 rounded-xl font-mono text-xs font-medium transition-all cursor-pointer flex items-center gap-2 ${
              activeTab === 'herdr'
                ? 'bg-[#f38ba8]/20 text-[#f38ba8] border border-[#f38ba8]/50 shadow-[0_0_15px_-3px_rgba(243,139,168,0.4)]'
                : 'bg-[#181825] text-[#a6adc8] border border-[#313244] hover:text-white hover:border-[#45475a]'
            }`}
          >
            <Monitor className="w-4 h-4" />
            Atajos en Herdr
          </button>
        </div>

        {/* Code Box */}
        <div className="max-w-4xl mx-auto rounded-3xl bg-[#11111b] border border-[#313244] overflow-hidden shadow-2xl">
          <div className="px-5 py-3.5 bg-[#181825] border-b border-[#313244] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#f38ba8]/90"></span>
              <span className="w-3 h-3 rounded-full bg-[#f9e2af]/90"></span>
              <span className="w-3 h-3 rounded-full bg-[#a6e3a1]/90"></span>
              <span className="ml-3 font-mono text-xs text-[#89b4fa]">
                {activeTab === 'claude' && '~/.claude.json'}
                {activeTab === 'antigravity' && '~/.gemini/antigravity-cli/mcp.json'}
                {activeTab === 'cli' && 'syntaxrag CLI commands'}
                {activeTab === 'systemd' && 'lancedb-watcher.service'}
                {activeTab === 'herdr' && 'Herdr Multiplexer Shortcuts'}
              </span>
            </div>

            <button
              onClick={handleCopy}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#313244]/60 hover:bg-[#313244] text-xs font-mono text-[#cdd6f4] transition-all cursor-pointer"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? '¡Copiado!' : 'Copiar bloque'}
            </button>
          </div>

          <div className="p-6 font-mono text-xs sm:text-sm text-[#cdd6f4] bg-[#0d1117] overflow-x-auto leading-relaxed">
            <pre>
              <code>{getActiveCode()}</code>
            </pre>
          </div>
        </div>
      </div>
    </section>
  );
};
