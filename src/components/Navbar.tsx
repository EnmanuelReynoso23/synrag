import { useState } from 'react';
import { Check, Menu, X, Terminal } from 'lucide-react';

export const Navbar: React.FC = () => {
  const [copied, setCopied] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const copyCommand = () => {
    navigator.clipboard.writeText('SYNRAG "asistenciaServicio"');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <header className="sticky top-0 z-50 bg-[#0D1117]/90 backdrop-blur-md border-b border-[#30363D] transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-18 flex items-center justify-between">
        {/* Brand / Logo Oficial SYNRAG */}
        <a href="#" className="flex items-center gap-3 group">
          <img 
            src="/synrag-logo.svg" 
            alt="SYNRAG Logo" 
            className="h-9 sm:h-10 w-auto object-contain transition-transform group-hover:scale-105"
          />
        </a>

        {/* Desktop Nav Links */}
        <nav className="hidden lg:flex items-center gap-7 text-xs sm:text-sm font-semibold text-[#8B949E]">
          <a href="#playground" className="hover:text-[#00E5FF] transition-colors flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00E5FF] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#00E5FF]"></span>
            </span>
            Simulador AST
          </a>
          <a href="#calculadora" className="hover:text-[#00E5FF] transition-colors">
            Calculadora
          </a>
          <a href="#terminal-cli" className="hover:text-[#00E5FF] transition-colors">
            Terminal CLI
          </a>
          <a href="#metricas" className="hover:text-[#00E5FF] transition-colors">
            Métricas
          </a>
          <a href="#innovaciones" className="hover:text-[#00E5FF] transition-colors">
            5 Pilares
          </a>
          <a href="#arquitectura" className="hover:text-[#00E5FF] transition-colors">
            Arquitectura
          </a>
          <a href="#comparativa" className="hover:text-[#00E5FF] transition-colors">
            Benchmark RAG
          </a>
          <a href="#integracion" className="hover:text-[#00E5FF] transition-colors">
            CLI & MCP
          </a>
        </nav>

        {/* Right Action & Watcher Pill */}
        <div className="hidden sm:flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#161B22] border border-[#30363D] text-xs font-mono text-[#7EE787]">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#7EE787] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#7EE787]"></span>
            </span>
            <span className="text-[#8B949E]">Watcher:</span> ~18ms reactivo
          </div>

          <button
            onClick={copyCommand}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#00E5FF] hover:bg-[#00E5FF]/90 text-[#0D1117] text-xs font-black tracking-wide shadow-[0_0_20px_-3px_rgba(0,229,255,0.4)] transition-all cursor-pointer active:scale-95"
            title="Copiar comando de ejecución de terminal"
          >
            {copied ? <Check className="w-3.5 h-3.5" /> : <Terminal className="w-3.5 h-3.5" />}
            {copied ? '¡Copiado!' : 'Copiar SYNRAG'}
          </button>
        </div>

        {/* Mobile menu button */}
        <div className="flex lg:hidden items-center gap-2">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-xl text-[#8B949E] hover:text-white hover:bg-[#161B22] focus:outline-none"
            aria-label="Abrir menú de navegación"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-b border-[#30363D] bg-[#0D1117] px-4 pt-3 pb-6 space-y-3 shadow-2xl">
          <a
            href="#playground"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-semibold text-[#8B949E] hover:text-[#00E5FF]"
          >
            Simulador AST en Vivo
          </a>
          <a
            href="#calculadora"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-semibold text-[#8B949E] hover:text-[#00E5FF]"
          >
            Calculadora de Ahorro
          </a>
          <a
            href="#terminal-cli"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-semibold text-[#8B949E] hover:text-[#00E5FF]"
          >
            Terminal CLI Simulador
          </a>
          <a
            href="#metricas"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-semibold text-[#8B949E] hover:text-[#00E5FF]"
          >
            Métricas Reales
          </a>
          <a
            href="#innovaciones"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-semibold text-[#8B949E] hover:text-[#00E5FF]"
          >
            5 Pilares Tecnológicos
          </a>
          <a
            href="#arquitectura"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-semibold text-[#8B949E] hover:text-[#00E5FF]"
          >
            Arquitectura de 7 Fases
          </a>
          <a
            href="#comparativa"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-semibold text-[#8B949E] hover:text-[#00E5FF]"
          >
            Benchmark RAG
          </a>
          <a
            href="#integracion"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-semibold text-[#8B949E] hover:text-[#00E5FF]"
          >
            Comandos CLI & MCP
          </a>
          <div className="pt-3 border-t border-[#30363D] flex flex-col gap-2">
            <button
              onClick={copyCommand}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-[#00E5FF] text-[#0D1117] text-xs font-black shadow-md shadow-cyan-500/20"
            >
              {copied ? '¡Copiado!' : 'Copiar comando SYNRAG'}
            </button>
          </div>
        </div>
      )}
    </header>
  );
};
