import { useState } from 'react';
import { Check, Copy, FolderCheck, ShieldCheck, Wand2 } from 'lucide-react';

const INSTALAR =
  'curl -sSL https://raw.githubusercontent.com/EnmanuelReynoso23/synrag/main/install.sh | bash';
const SIMULAR =
  'git clone https://github.com/EnmanuelReynoso23/synrag.git && cd synrag && ./install.sh --dry-run';

const PASOS = [
  {
    icono: FolderCheck,
    titulo: 'Detecta tus IAs',
    texto:
      'Busca Claude Code, Antigravity, Gemini CLI, Codex, Cursor, Windsurf, Cline y Zed. Solo toca las que de verdad tienes instaladas.',
  },
  {
    icono: Wand2,
    titulo: 'Las conecta y les dice que lo usen',
    texto:
      'Registra el servidor MCP y añade a sus instrucciones globales un bloque corto: usar search_desktop antes de leer archivos enteros.',
  },
  {
    icono: ShieldCheck,
    titulo: 'No rompe nada',
    texto:
      'Copia de seguridad antes de modificar, no sobrescribe archivos que no pueda leer y se puede repetir sin duplicar. Si algo falla, se detiene y lo dice.',
  },
];

function Comando({ texto, etiqueta }: { texto: string; etiqueta: string }) {
  const [copiado, setCopiado] = useState(false);
  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      /* Sin permiso de portapapeles: el comando sigue visible. */
    }
  };
  return (
    <div className="rounded-xl border border-[#30363D] bg-[#0D1117]">
      <div className="flex items-center justify-between gap-3 border-b border-[#30363D] px-4 py-2">
        <span className="text-[11px] font-bold uppercase tracking-wider text-[#8B949E]">{etiqueta}</span>
        <button
          onClick={copiar}
          aria-label={`Copiar: ${etiqueta}`}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[#30363D] bg-[#21262D] px-2.5 py-1 text-xs font-bold text-white transition-colors hover:bg-[#30363D] cursor-pointer"
        >
          {copiado ? <Check className="h-3.5 w-3.5 text-[#7EE787]" /> : <Copy className="h-3.5 w-3.5 text-[#8B949E]" />}
          {copiado ? 'Copiado' : 'Copiar'}
        </button>
      </div>
      <pre className="overflow-x-auto px-4 py-3 font-mono text-xs leading-relaxed text-[#C9D1D9] sm:text-sm">
        <code>{texto}</code>
      </pre>
    </div>
  );
}

export const Install: React.FC = () => (
  <section id="instalar" className="scroll-mt-20 border-b border-[#30363D] bg-[#0D1117] py-16 sm:py-20">
    <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
      <div className="text-center">
        <p className="text-xs font-black uppercase tracking-[0.2em] text-[#00E5FF]">Instalación</p>
        <h2 className="mt-3 text-2xl font-black tracking-tight text-white sm:text-3xl lg:text-4xl">
          Instálalo en un minuto
        </h2>
        <p className="mx-auto mt-3 max-w-2xl text-sm text-[#8B949E] sm:text-base">
          Un solo comando. Necesitas Python 3.10 o superior en Linux, macOS o Windows con WSL. La primera vez descarga
          las dependencias y un modelo pequeño que corre en tu CPU.
        </p>
      </div>

      <div className="mt-10 space-y-4">
        <Comando etiqueta="Instalar" texto={INSTALAR} />
        <Comando etiqueta="Ver qué haría, sin escribir nada" texto={SIMULAR} />
      </div>

      <ul className="mt-10 grid gap-4 md:grid-cols-3">
        {PASOS.map(({ icono: Icono, titulo, texto }) => (
          <li key={titulo} className="rounded-2xl border border-[#30363D] bg-[#161B22] p-5">
            <Icono className="h-5 w-5 text-[#00E5FF]" aria-hidden="true" />
            <h3 className="mt-3 text-sm font-black text-white">{titulo}</h3>
            <p className="mt-1.5 text-xs leading-relaxed text-[#8B949E]">{texto}</p>
          </li>
        ))}
      </ul>
    </div>
  </section>
);
