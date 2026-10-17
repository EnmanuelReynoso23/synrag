import { CHANGELOG, CLAIMS, REPO, VERSION } from '../data/medido';
import { IconoGitHub } from './ui';

export const Footer: React.FC = () => (
  <footer className="bg-[#0D1117]">
    <div className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-12 sm:px-6 md:flex-row md:items-start md:justify-between lg:px-8">
      <div className="max-w-sm">
        <div className="flex items-center gap-2.5">
          <img src="/synrag-logo.svg" alt="" className="h-7 w-7" />
          <span className="font-black text-white">SyntaxRAG (SYNRAG)</span>
        </div>
        <p className="mt-3 text-sm leading-relaxed text-[#8B949E]">
          Motor local de búsqueda de código para agentes de IA. Versión {VERSION}. Licencia MIT. Hecho por{' '}
          <a href="https://github.com/EnmanuelReynoso23" target="_blank" rel="noreferrer" className="text-white hover:text-[#00E5FF]">Enmanuel Reynoso</a>.
        </p>
      </div>
      <nav className="grid grid-cols-2 gap-x-12 gap-y-2 text-sm" aria-label="Pie de página">
        <a href={REPO} target="_blank" rel="noreferrer" className="flex items-center gap-2 text-[#8B949E] hover:text-white"><IconoGitHub className="h-4 w-4" /> Código</a>
        <a href={CLAIMS} target="_blank" rel="noreferrer" className="text-[#8B949E] hover:text-white">Cifras y límites</a>
        <a href={CHANGELOG} target="_blank" rel="noreferrer" className="text-[#8B949E] hover:text-white">Cambios</a>
        <a href={`${REPO}/issues`} target="_blank" rel="noreferrer" className="text-[#8B949E] hover:text-white">Incidencias</a>
        <a href={`${REPO}/blob/main/SECURITY.md`} target="_blank" rel="noreferrer" className="text-[#8B949E] hover:text-white">Seguridad</a>
        <a href={`${REPO}/blob/main/CONTRIBUTING.md`} target="_blank" rel="noreferrer" className="text-[#8B949E] hover:text-white">Contribuir</a>
      </nav>
    </div>
    <p className="border-t border-[#30363D] py-5 text-center text-xs text-[#8B949E]">
      El modo conciso se basa en Caveman de Julius Brussee (Apache-2.0). LanceDB, Tree-sitter y FlashRank son proyectos de sus autores.
    </p>
  </footer>
);
