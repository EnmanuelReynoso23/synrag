import { useState, type ReactNode } from 'react';
import { Check, Copy } from 'lucide-react';

export const Seccion: React.FC<{ id: string; etiqueta: string; titulo: string; intro?: ReactNode; children: ReactNode; alterna?: boolean }> = ({
  id,
  etiqueta,
  titulo,
  intro,
  children,
  alterna,
}) => (
  <section id={id} className={`scroll-mt-20 border-b border-[#30363D] py-16 sm:py-20 ${alterna ? 'bg-[#0A0D12]' : ''}`}>
    <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-[#00E5FF]">{etiqueta}</p>
      <h2 className="mt-3 text-2xl font-black tracking-tight text-white sm:text-3xl">{titulo}</h2>
      {intro && <div className="mt-4 max-w-3xl text-base leading-relaxed text-[#8B949E]">{intro}</div>}
      <div className="mt-10">{children}</div>
    </div>
  </section>
);

export const Copiable: React.FC<{ texto: string; etiqueta?: string }> = ({ texto, etiqueta }) => {
  const [copiado, setCopiado] = useState(false);
  const copiar = () => {
    navigator.clipboard?.writeText(texto).then(() => {
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    });
  };
  return (
    <div className="group flex items-center gap-3 rounded-lg border border-[#30363D] bg-[#0D1117] px-4 py-3 font-mono text-sm">
      {etiqueta && <span className="shrink-0 text-[#8B949E]">{etiqueta}</span>}
      <span className="shrink-0 text-[#00E5FF]">$</span>
      <code className="min-w-0 flex-1 overflow-x-auto whitespace-nowrap text-[#E6EDF3]">{texto}</code>
      <button
        type="button"
        onClick={copiar}
        aria-label={copiado ? 'Copiado' : 'Copiar comando'}
        className="shrink-0 rounded-md p-1.5 text-[#8B949E] transition hover:bg-[#161B22] hover:text-white"
      >
        {copiado ? <Check className="h-4 w-4 text-[#3FB950]" /> : <Copy className="h-4 w-4" />}
      </button>
    </div>
  );
};

/** Enlace a la fila de CLAIMS.md que respalda una cifra. */
export const Fuente: React.FC<{ fila: string; href: string }> = ({ fila, href }) => (
  <a href={href} target="_blank" rel="noreferrer" className="font-mono text-[11px] text-[#8B949E] underline decoration-dotted underline-offset-2 hover:text-[#00E5FF]">
    CLAIMS {fila === '-' ? 'sin fila' : `fila ${fila}`}
  </a>
);

export const IconoGitHub: React.FC<{ className?: string }> = ({ className }) => (
  <svg viewBox="0 0 16 16" aria-hidden="true" className={className} fill="currentColor">
    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
  </svg>
);
