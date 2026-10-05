import { useState } from 'react';
import { Copy, Check, Menu, X, Sparkles } from 'lucide-react';
import { CONFIG_SNIPPETS } from '../data/mockData';


export const Navbar: React.FC = () => {
  const [copied, setCopied] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const copyMCP = () => {
    navigator.clipboard.writeText(CONFIG_SNIPPETS.claude);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <header className="sticky top-0 z-50 backdrop-blur-xl bg-[#0d1117]/85 border-b border-[#30363d]/80 transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand / Logo */}
        <a href="#" className="flex items-center gap-3 group">
          <div className="relative flex items-center justify-center">
            <img 
              src="/synrag-logo.svg" 
              alt="Synrag Logo" 
              className="h-9 w-auto object-contain transition-transform group-hover:scale-105"
            />
            <div className="absolute -inset-1 bg-[#00e5ff]/20 rounded-lg blur-md -z-10 group-hover:bg-[#00e5ff]/35 transition-all"></div>
          </div>
        </a>

        {/* Desktop Nav Links */}
        <nav className="hidden md:flex items-center gap-7 text-sm font-medium text-[#cdd6f4]/80">
          <a href="#innovaciones" className="hover:text-[#00e5ff] transition-colors">
            Innovaciones
          </a>
          <a href="#arquitectura" className="hover:text-[#00e5ff] transition-colors">
            Arquitectura
          </a>
          <a href="#playground" className="hover:text-[#00e5ff] transition-colors flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00e5ff] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#00e5ff]"></span>
            </span>
            Simulador AST
          </a>
          <a href="#metricas" className="hover:text-[#00e5ff] transition-colors">
            Métricas
          </a>
          <a href="#integracion" className="hover:text-[#00e5ff] transition-colors">
            Integración MCP
          </a>
        </nav>

        {/* Right Action & Daemon Indicator */}
        <div className="hidden lg:flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#161b22] border border-[#30363d] text-xs text-[#a6e3a1]">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#a6e3a1] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#a6e3a1]"></span>
            </span>
            <span className="font-mono font-medium text-slate-300">Watcher:</span> 18ms reactivo
          </div>

          <button
            onClick={copyMCP}
            className="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-[#00e5ff]/10 hover:bg-[#00e5ff]/20 border border-[#00e5ff]/40 text-[#00e5ff] text-xs font-semibold tracking-wide transition-all shadow-[0_0_15px_-3px_rgba(0,229,255,0.3)] hover:shadow-[0_0_20px_0px_rgba(0,229,255,0.5)] cursor-pointer"
            title="Copiar configuración de servidor desktop-lancedb para Claude Code y Antigravity"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? '¡Copiado a portapapeles!' : 'Copiar MCP'}
          </button>
        </div>

        {/* Mobile menu button */}
        <div className="flex md:hidden items-center gap-2">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 focus:outline-none"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-slate-800 bg-[#0d1117] px-4 pt-2 pb-6 space-y-3">
          <a
            href="#innovaciones"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-medium text-slate-300 hover:text-[#00e5ff]"
          >
            Innovaciones
          </a>
          <a
            href="#arquitectura"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-medium text-slate-300 hover:text-[#00e5ff]"
          >
            Arquitectura
          </a>
          <a
            href="#playground"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-medium text-[#00e5ff] flex items-center gap-2"
          >
            <Sparkles className="w-4 h-4" /> Simulador AST
          </a>
          <a
            href="#metricas"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-medium text-slate-300 hover:text-[#00e5ff]"
          >
            Métricas del Ecosistema
          </a>
          <a
            href="#integracion"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-medium text-slate-300 hover:text-[#00e5ff]"
          >
            Integración MCP
          </a>
          <div className="pt-2 flex flex-col gap-2">
            <button
              onClick={copyMCP}
              className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-lg bg-[#00e5ff]/15 border border-[#00e5ff]/40 text-[#00e5ff] text-sm font-medium"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              {copied ? 'Copiado' : 'Copiar MCP Config'}
            </button>
          </div>
        </div>
      )}
    </header>
  );
};
