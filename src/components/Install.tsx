import { INSTALAR, REPO } from '../data/medido';
import { Copiable, Seccion } from './ui';

const PASOS = [
  { titulo: 'Instalar', comando: INSTALAR, nota: 'Copia el motor a ~/.local/opt/lancedb-hub, crea un entorno virtual aislado en CPU, instala los comandos SYNRAG y synrag en ~/.local/bin, indexa tus carpetas de proyectos y configura tus IAs. Para ver qué haría sin escribir nada: ./install.sh --dry-run.' },
  { titulo: 'Elegir qué se indexa', comando: 'SYNRAG agregar ~/trabajo mi-proyecto', nota: 'Detecta ~/Projects, ~/code, ~/dev y similares. La lista queda en ~/.config/synrag/carpetas.txt (o en la variable SYNRAG_CARPETAS).' },
  { titulo: 'Probar una búsqueda', comando: 'SYNRAG "useEstudiantes"', nota: 'Lo mismo que hará tu IA por MCP. También: SYNRAG outline <archivo>, SYNRAG impact <símbolo>, SYNRAG tests <símbolo>.' },
  { titulo: 'Opcionales', comando: 'SYNRAG configure --filtro-largas', nota: 'Uno por vez: --filtro-largas (salidas largas de la terminal en Claude Code), --filtro (instalar, compilar y probar), --conciso (respuestas cortas), --pista (aviso de usar SynRAG solo en mensajes de código) o --perfil esencial. Cada uno se quita con SYNRAG uninstall --<lo-mismo>.' },
  { titulo: 'Desinstalar', comando: 'SYNRAG uninstall', nota: 'Quita la entrada MCP, el bloque de instrucciones de cada IA y los comandos; solo lo que el instalador añadió. El índice se borra aparte con rm -rf ~/.local/opt/lancedb-hub.' },
];

export const Install: React.FC = () => (
  <Seccion
    id="instalar"
    etiqueta="Instalar"
    titulo="Una línea, y se deshace igual de fácil"
    intro={
      <p>
        Requisitos: Python 3.10 o superior con el módulo venv, y curl. Probado en Linux (CachyOS); macOS y Windows con WSL deberían funcionar, pero no están
        probados. La integración continua corre las pruebas del motor en Linux y macOS con Python 3.10 y 3.12.
      </p>
    }
  >
    <ol className="space-y-6">
      {PASOS.map((p, i) => (
        <li key={p.titulo} className="grid gap-3 md:grid-cols-12 md:gap-6">
          <div className="md:col-span-3">
            <p className="font-mono text-xs text-[#00E5FF]">paso {i + 1}</p>
            <p className="font-bold text-white">{p.titulo}</p>
          </div>
          <div className="md:col-span-9">
            <Copiable texto={p.comando} />
            <p className="mt-2 text-sm leading-relaxed text-[#8B949E]">{p.nota}</p>
          </div>
        </li>
      ))}
    </ol>
    <p className="mt-10 text-sm text-[#8B949E]">
      ¿Prefieres revisar antes de ejecutar? Clona el repositorio y lee <code className="text-[#E6EDF3]">install.sh</code>:{' '}
      <a href={REPO} target="_blank" rel="noreferrer" className="text-[#00E5FF] underline underline-offset-2">{REPO.replace('https://', '')}</a>.
    </p>
  </Seccion>
);
