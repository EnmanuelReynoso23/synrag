import { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { REPO, VERSION } from '../data/medido';
import { IconoGitHub } from './ui';

const ENLACES = [
  { href: '#problema', texto: 'Por qué' },
  { href: '#como-funciona', texto: 'Cómo funciona' },
  { href: '#resultados', texto: 'Resultados' },
  { href: '#herramientas', texto: 'Herramientas' },
  { href: '#instalar', texto: 'Instalar' },
  { href: '#preguntas', texto: 'Preguntas' },
];

export const Navbar: React.FC = () => {
  const [abierto, setAbierto] = useState(false);
  return (
    <header className="sticky top-0 z-50 border-b border-[#30363D] bg-[#0D1117]/90 backdrop-blur">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8" aria-label="Principal">
        <a href="#inicio" className="flex items-center gap-2.5">
          <img src="/synrag-logo.svg" alt="" className="h-7 w-7" />
          <span className="font-black tracking-tight text-white">SYNRAG</span>
          <span className="rounded-full border border-[#30363D] px-2 py-0.5 font-mono text-[10px] text-[#8B949E]">v{VERSION}</span>
        </a>
        <div className="hidden items-center gap-6 md:flex">
          {ENLACES.map((e) => (
            <a key={e.href} href={e.href} className="text-sm text-[#8B949E] transition hover:text-white">
              {e.texto}
            </a>
          ))}
          <a href={REPO} target="_blank" rel="noreferrer" className="flex items-center gap-2 rounded-lg border border-[#30363D] px-3 py-1.5 text-sm text-white transition hover:border-[#00E5FF]/60">
            <IconoGitHub className="h-4 w-4" /> GitHub
          </a>
        </div>
        <button type="button" className="rounded-md p-2 text-[#8B949E] md:hidden" onClick={() => setAbierto(!abierto)} aria-label="Menú" aria-expanded={abierto}>
          {abierto ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </nav>
      {abierto && (
        <div className="border-t border-[#30363D] px-4 py-3 md:hidden">
          {ENLACES.map((e) => (
            <a key={e.href} href={e.href} onClick={() => setAbierto(false)} className="block py-2 text-sm text-[#8B949E] hover:text-white">
              {e.texto}
            </a>
          ))}
          <a href={REPO} target="_blank" rel="noreferrer" className="mt-1 flex items-center gap-2 py-2 text-sm text-white">
            <IconoGitHub className="h-4 w-4" /> GitHub
          </a>
        </div>
      )}
    </header>
  );
};
