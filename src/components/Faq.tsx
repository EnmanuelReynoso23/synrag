import { ChevronDown } from 'lucide-react';

const PREGUNTAS: { p: string; r: React.ReactNode }[] = [
  {
    p: '¿Mi código sale de mi equipo?',
    r: 'No. El análisis (Tree-sitter), la base vectorial (LanceDB) y el reordenamiento (FlashRank) corren en tu CPU. SYNRAG no envía tu código a ningún servicio. Solo la instalación descarga dependencias y, la primera vez, el modelo pequeño del reordenador.',
  },
  {
    p: '¿Con qué IAs funciona?',
    r: 'Claude Code, Google Antigravity, Gemini CLI, Codex CLI, Cursor, Windsurf, Cline / Roo Code y Zed. Cualquier otra que hable MCP puede usar el servidor desktop-lancedb.',
  },
  {
    p: '¿Qué cambia en mi equipo?',
    r: (
      <>
        Crea <code className="text-[#00E5FF]">~/.local/opt/lancedb-hub</code>, los comandos{' '}
        <code className="text-[#00E5FF]">SYNRAG</code> / <code className="text-[#00E5FF]">synrag</code> en{' '}
        <code className="text-[#00E5FF]">~/.local/bin</code> y, en cada IA instalada, una entrada MCP y un bloque entre
        las marcas <code className="text-[#00E5FF]">SYNRAG:BEGIN</code> / <code className="text-[#00E5FF]">SYNRAG:END</code>.
        Antes de modificar un archivo hace una copia <code className="text-[#00E5FF]">.bak-fecha</code>.
      </>
    ),
  },
  {
    p: '¿Cómo lo desinstalo?',
    r: (
      <>
        Ejecuta <code className="text-[#00E5FF]">SYNRAG uninstall</code>: quita la entrada MCP y el bloque de
        instrucciones de cada IA y borra los comandos. No toca nada más de tus archivos. Si también quieres borrar el
        motor y su índice: <code className="text-[#00E5FF]">rm -rf ~/.local/opt/lancedb-hub</code>.
      </>
    ),
  },
  {
    p: '¿Cuánto cuesta?',
    r: 'Nada. Es de código abierto con licencia MIT y no usa tokens de ninguna API.',
  },
  {
    p: '¿Funciona en Windows?',
    r: 'Con WSL sí. El lanzador es un script bash, así que no hay versión nativa de Windows por ahora.',
  },
  {
    p: '¿Las cifras de esta página son reales?',
    r: 'Las métricas son un ejemplo medido por el autor en su propio monorepo (~95 mil fragmentos). El simulador, la terminal y el hot-reload son demostraciones con datos de ejemplo, no tu código. La calculadora estima el ahorro con los precios y el uso que tú ajustas: es una estimación, no una garantía.',
  },
];

export const Faq: React.FC = () => (
  <section id="faq" className="scroll-mt-20 border-b border-[#30363D] bg-[#0D1117] py-16 sm:py-20">
    <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
      <div className="text-center">
        <p className="text-xs font-black uppercase tracking-[0.2em] text-[#00E5FF]">Preguntas frecuentes</p>
        <h2 className="mt-3 text-2xl font-black tracking-tight text-white sm:text-3xl">Antes de instalarlo</h2>
      </div>
      <div className="mt-8 divide-y divide-[#30363D] rounded-2xl border border-[#30363D] bg-[#161B22]">
        {PREGUNTAS.map(({ p, r }) => (
          <details key={p} className="group px-5 py-4">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-sm font-bold text-white [&::-webkit-details-marker]:hidden">
              {p}
              <ChevronDown className="h-4 w-4 shrink-0 text-[#8B949E] transition-transform group-open:rotate-180" aria-hidden="true" />
            </summary>
            <p className="mt-3 text-sm leading-relaxed text-[#8B949E]">{r}</p>
          </details>
        ))}
      </div>
    </div>
  </section>
);
