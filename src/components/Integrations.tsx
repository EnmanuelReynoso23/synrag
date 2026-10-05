import { useState } from 'react';
import { Check, Copy, Cpu, Layers, Sparkles, Terminal } from 'lucide-react';
import { CONFIG_SNIPPETS } from '../data/mockData';

type Pestana = 'synrag' | 'claude' | 'antigravity' | 'codex';

const PESTANAS: {
  id: Pestana;
  titulo: string;
  icono: typeof Terminal;
  nota: React.ReactNode;
}[] = [
  {
    id: 'synrag',
    titulo: 'Comando SYNRAG',
    icono: Terminal,
    nota: (
      <>
        El comando <strong className="text-white">SYNRAG</strong> (también{' '}
        <code className="text-[#00E5FF]">synrag</code>) queda en{' '}
        <code className="text-[#58A6FF]">~/.local/bin</code>. Sin argumentos
        muestra el panel del motor; con una consulta busca en tus proyectos
        indexados.
      </>
    ),
  },
  {
    id: 'claude',
    titulo: 'Claude Code',
    icono: Cpu,
    nota: (
      <>
        Registra el servidor MCP <code className="text-[#58A6FF]">desktop-lancedb</code>{' '}
        en <code className="text-[#58A6FF]">~/.claude.json</code> y añade a{' '}
        <code className="text-[#58A6FF]">CLAUDE.md</code> la indicación de usar{' '}
        <strong className="text-white">search_desktop</strong> antes de leer
        archivos enteros.
      </>
    ),
  },
  {
    id: 'antigravity',
    titulo: 'Google Antigravity',
    icono: Sparkles,
    nota: (
      <>
        Antigravity lee{' '}
        <code className="text-[#58A6FF]">~/.gemini/antigravity/mcp_config.json</code>.
        Las instrucciones van en <code className="text-[#58A6FF]">~/.gemini/GEMINI.md</code>,
        que también usa Gemini CLI.
      </>
    ),
  },
  {
    id: 'codex',
    titulo: 'Codex CLI',
    icono: Layers,
    nota: (
      <>
        Codex usa TOML: se añade una tabla a{' '}
        <code className="text-[#58A6FF]">~/.codex/config.toml</code> y el bloque
        de instrucciones a <code className="text-[#58A6FF]">~/.codex/AGENTS.md</code>.
      </>
    ),
  },
];

export const Integrations: React.FC = () => {
  const [activa, setActiva] = useState<Pestana>('synrag');
  const [copiado, setCopiado] = useState(false);
  const pestana = PESTANAS.find((p) => p.id === activa) ?? PESTANAS[0];

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(CONFIG_SNIPPETS[activa]);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      /* Sin permiso de portapapeles: el texto sigue visible para copiarlo a mano. */
    }
  };

  return (
    <section
      id="integracion"
      className="scroll-mt-20 border-b border-[#30363D] bg-[#0D1117] py-16 sm:py-24 relative overflow-hidden"
    >
      <div className="absolute top-1/3 right-1/4 w-[500px] h-[300px] bg-[#00E5FF]/5 blur-[120px] rounded-full pointer-events-none" />

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto">
          <p className="text-xs font-black uppercase tracking-[0.2em] text-[#00E5FF]">
            Integración · MCP y CLI
          </p>
          <h2 className="mt-3 text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight text-white">
            Una instalación, todas tus IAs
          </h2>
          <p className="mt-3 text-sm sm:text-base text-[#8B949E]">
            El instalador detecta las IAs que tienes, las conecta por MCP y les
            indica que usen SYNRAG primero. Esto es lo que escribe en cada una
            (puedes verlo antes con <code className="text-[#00E5FF]">--dry-run</code>).
          </p>
        </div>

        <div className="mt-12 max-w-4xl mx-auto rounded-2xl border border-[#30363D] bg-[#161B22] shadow-2xl overflow-hidden">
          <div
            role="tablist"
            aria-label="Herramienta de IA"
            className="p-3 bg-[#161B22] border-b border-[#30363D] flex flex-wrap gap-2"
          >
            {PESTANAS.map(({ id, titulo, icono: Icono }) => {
              const seleccionada = id === activa;
              return (
                <button
                  key={id}
                  role="tab"
                  aria-selected={seleccionada}
                  onClick={() => setActiva(id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all cursor-pointer border ${
                    seleccionada
                      ? 'bg-[#21262D] text-white border-[#00E5FF]/40 shadow-sm shadow-[#00E5FF]/10'
                      : 'text-[#8B949E] hover:text-white hover:bg-[#21262D]/50 border-transparent'
                  }`}
                >
                  <Icono className={`w-4 h-4 ${seleccionada ? 'text-[#00E5FF]' : 'text-[#8B949E]'}`} />
                  {titulo}
                </button>
              );
            })}
          </div>

          <div className="relative p-5 bg-[#0D1117] text-[#C9D1D9] overflow-x-auto min-h-[160px]">
            <button
              onClick={copiar}
              aria-label="Copiar configuración"
              className="absolute top-4 right-4 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#21262D] hover:bg-[#30363D] text-white text-xs font-bold border border-[#30363D] transition-colors cursor-pointer"
            >
              {copiado ? <Check className="w-4 h-4 text-[#7EE787]" /> : <Copy className="w-4 h-4 text-[#8B949E]" />}
              <span>{copiado ? 'Copiado' : 'Copiar'}</span>
            </button>
            <pre className="font-mono text-xs sm:text-sm leading-relaxed pr-24 text-[#C9D1D9]">
              <code>{CONFIG_SNIPPETS[activa]}</code>
            </pre>
          </div>

          <div className="p-4 bg-[#161B22] border-t border-[#30363D] text-xs text-[#8B949E] font-medium leading-relaxed">
            <p>{pestana.nota}</p>
          </div>
        </div>
      </div>
    </section>
  );
};
