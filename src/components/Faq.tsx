import { ChevronDown } from 'lucide-react';

const PREGUNTAS: { p: string; r: React.ReactNode }[] = [
  {
    p: '¿Mi código sale de mi equipo?',
    r: 'No. El análisis (Tree-sitter), la base vectorial (LanceDB) y el reordenamiento (FlashRank) corren en tu CPU. SYNRAG no envía tu código a ningún servicio. Solo la instalación descarga dependencias y, la primera vez, el modelo pequeño del reordenador.',
  },
  {
    p: '¿Con qué IAs funciona?',
    r: 'Probado en la práctica con Claude Code y Google Antigravity. El instalador también las configura para Gemini CLI, Codex CLI, Cursor, Windsurf, Cline / Roo Code y Zed según su documentación, pero esas no se han probado. Cualquier otra que hable MCP puede usar el servidor desktop-lancedb.',
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
    r: 'Nada: es de código abierto (licencia MIT) y la búsqueda no usa APIs de pago. Ojo: los resultados que recibe tu IA igualmente cuestan tokens al modelo que la alimenta.',
  },
  {
    p: '¿Funciona en Windows?',
    r: 'Solo se ha probado en Linux. macOS y Windows con WSL deberían funcionar (el lanzador es un script bash), pero no están probados; no hay versión nativa de Windows.',
  },
  {
    p: '¿Las cifras de esta página son reales?',
    r: 'Las cifras marcadas como medidas (~90 ms por consulta nueva, ~9 ms si se repite, ~8 ms por archivo reindexado, 300 MB o más del observador, 96 mil fragmentos y 23,7 mil relaciones) las midió el autor en su equipo el 6-oct-2026, con ~75 proyectos indexados; en el tuyo variarán. El simulador, la terminal y el observador de la página son simulaciones con datos de ejemplo, no tu código. La calculadora es un escenario hipotético con supuestos que tú ajustas. Cada afirmación y cómo reproducirla está en CLAIMS.md del repositorio.',
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
