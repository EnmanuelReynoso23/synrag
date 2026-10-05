export const Footer: React.FC = () => {

  return (
    <footer className="border-t border-[#313244] bg-[#0d1117] text-[#a6adc8] py-14">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-8 pb-12 border-b border-[#30363d]">
          {/* Logo & description */}
          <div className="space-y-3 max-w-md">
            <div className="flex items-center gap-3">
              <img src="/synrag-logo.svg" alt="Synrag" className="h-8 w-auto" />
            </div>
            <p className="text-xs sm:text-sm text-[#8b949e] leading-relaxed">
              Motor de inteligencia de código local nativo AST. Diseñado para potenciar agentes de IA como Claude Code y Antigravity CLI con cero costos de tokens y máxima precisión estructural.
            </p>
          </div>

          {/* Quick specs list */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-6 text-xs font-mono">
            <div>
              <div className="text-white font-bold mb-2">Motor RAG</div>
              <div className="space-y-1 text-[#8b949e]">
                <div>LanceDB 0.25</div>
                <div>Tree-sitter AST</div>
                <div>FlashRank ONNX</div>
              </div>
            </div>

            <div>
              <div className="text-white font-bold mb-2">Protocolo</div>
              <div className="space-y-1 text-[#8b949e]">
                <div>Model Context Protocol</div>
                <div>desktop-lancedb (stdio)</div>
                <div>JSON-RPC 2.0</div>
              </div>
            </div>

            <div>
              <div className="text-white font-bold mb-2">Entorno</div>
              <div className="space-y-1 text-[#8b949e]">
                <div>CachyOS Linux x86_64</div>
                <div>Herdr 0.9.3</div>
                <div>Catppuccin Mocha</div>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom copyright & local path */}
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono text-[#585b70]">
          <div>
            Ubicación del core: <span className="text-[#89b4fa]">/home/reyno/.local/opt/lancedb-hub</span>
          </div>
          <div>
            ⚡ SyntaxRAG · Desarrollado para el ecosistema de Reyno & AsistoYA
          </div>
        </div>
      </div>
    </footer>
  );
};
