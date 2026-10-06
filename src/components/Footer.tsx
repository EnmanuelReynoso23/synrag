import { ArrowUp } from 'lucide-react';

export const Footer: React.FC = () => {
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <footer className="bg-[#0D1117] text-[#8B949E] pt-16 pb-12 border-t border-[#30363D] relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute bottom-0 left-1/3 w-[600px] h-[200px] bg-[#00E5FF]/5 blur-[120px] rounded-full pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-10 pb-12 border-b border-[#30363D]">
          {/* Columna Principal Marca SYNRAG (2 Cols) */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center gap-3">
              <img 
                src="/synrag-logo.svg" 
                alt="SYNRAG Logo" 
                className="h-9 sm:h-10 w-auto object-contain"
              />
            </div>

            <p className="text-xs sm:text-sm text-[#8B949E] leading-relaxed max-w-sm">
              Motor local de búsqueda de código para IAs: troceo por AST, búsqueda por palabras con reordenado neuronal y grafo de impacto, sin APIs de pago. Probado con Claude Code y Google Antigravity.
            </p>

            <div className="flex items-center gap-3 pt-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#161B22] text-[#7EE787] border border-[#30363D]">
                <span className="w-2 h-2 rounded-full bg-[#7EE787] animate-pulse"></span>
                Código abierto · MIT
              </span>
            </div>
          </div>

          {/* Columna 1: Subsistemas */}
          <div className="space-y-3">
            <h4 className="text-xs font-black uppercase tracking-wider text-white">
              Tecnologías Clave
            </h4>
            <ul className="space-y-2 text-xs font-medium text-[#8B949E]">
              <li className="hover:text-[#00E5FF] transition-colors cursor-pointer">Tree-sitter AST Chunker</li>
              <li className="hover:text-[#00E5FF] transition-colors cursor-pointer">LanceDB Columnar Store</li>
              <li className="hover:text-[#00E5FF] transition-colors cursor-pointer">FlashRank TinyBERT ONNX</li>
              <li className="hover:text-[#00E5FF] transition-colors cursor-pointer">Grafo de Impacto de dependencias</li>
              <li className="hover:text-[#00E5FF] transition-colors cursor-pointer">Caché local de consultas (<span className="text-[#7EE787] font-bold">~9 ms</span>)</li>
            </ul>
          </div>

          {/* Columna 2: Repositorios */}
          <div className="space-y-3">
            <h4 className="text-xs font-black uppercase tracking-wider text-white">
              Repositorios Indexados
            </h4>
            <ul className="space-y-2 text-xs font-medium text-[#8B949E]">
              <li className="hover:text-[#00E5FF] transition-colors cursor-pointer">mi-monorepo (Monorepo pnpm)</li>
              <li className="hover:text-[#00E5FF] transition-colors cursor-pointer">apps/web (Kiosco & Portal)</li>
              <li className="hover:text-[#00E5FF] transition-colors cursor-pointer">notas-ia</li>
              <li className="hover:text-[#00E5FF] transition-colors cursor-pointer">Proyectos locales (~/proyectos)</li>
              <li className="hover:text-[#00E5FF] transition-colors cursor-pointer">Configuración global de IAs</li>
            </ul>
          </div>

          {/* Columna 3: Herramientas */}
          <div className="space-y-3">
            <h4 className="text-xs font-black uppercase tracking-wider text-white">
              Herramientas & Agentes
            </h4>
            <ul className="space-y-2 text-xs font-medium text-[#8B949E]">
              <li className="hover:text-[#00E5FF] transition-colors cursor-pointer">Comando Maestro <strong className="text-white">SYNRAG</strong></li>
              <li className="hover:text-[#00E5FF] transition-colors cursor-pointer">Google Antigravity CLI (agy)</li>
              <li className="hover:text-[#00E5FF] transition-colors cursor-pointer">Claude Code (MCP Protocol)</li>
              <li className="hover:text-[#00E5FF] transition-colors cursor-pointer">lancedb-watcher.service</li>
              <li className="hover:text-[#00E5FF] transition-colors cursor-pointer">Codex CLI (MCP)</li>
            </ul>
          </div>
        </div>

        {/* Barra Inferior de Copyright y Retorno */}
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#8B949E] font-medium">
          <p>
            © 2026 SyntaxRAG (SYNRAG). Motor AST-Native de Código Local. Código abierto bajo licencia MIT. Hecho por Enmanuel Reynoso.
          </p>

          <button
            onClick={scrollToTop}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#161B22] hover:bg-[#21262D] text-white text-xs font-bold border border-[#30363D] hover:border-[#00E5FF]/50 transition-all cursor-pointer"
          >
            <span>Volver arriba</span>
            <ArrowUp className="w-3.5 h-3.5 text-[#00E5FF]" />
          </button>
        </div>
      </div>
    </footer>
  );
};
