import { Database, FileCode, GitBranch, Search, Eye, Scissors, MessageSquareText, Package } from 'lucide-react';
import { CLAIMS } from '../data/medido';
import { Fuente, Seccion } from './ui';

const PASOS = [
  {
    icono: FileCode,
    titulo: '1. Trocea por la estructura',
    texto:
      'Tree-sitter lee el árbol sintáctico de TypeScript, TSX/JSX, JavaScript y Python y corta por funciones, hooks, clases, tipos y declaraciones completas. Las clases y los objetos grandes se parten miembro por miembro, sin dejar código fuera. La documentación (Markdown, MDX, reStructuredText, AsciiDoc) va en fragmentos de ~200 tokens con su ruta de títulos; SQL, por sentencias.',
    fila: '34',
  },
  {
    icono: Database,
    titulo: '2. Guarda todo en tu equipo',
    texto:
      'Los fragmentos van a una base LanceDB local. Reindexar 9.247 archivos (125.570 fragmentos) tarda 16,7 s y el índice ocupa 132 MB. Antes de guardar, oculta llaves y claves que encuentre en el código.',
    fila: '28, 29',
  },
  {
    icono: Search,
    titulo: '3. Busca por palabras y reordena en CPU',
    texto:
      'Candidatos por BM25 (Tantivy sobre LanceDB), reordenados con un modelo TinyBERT de FlashRank, sin GPU. Si la consulta es un nombre de símbolo, la definición exacta sale primera y entera; "objeto.miembro" o "Clase miembro" dan el miembro de esa clase. Los nombres compuestos se encuentran con palabras sueltas: esSinCupo responde a "sin cupo".',
    fila: '27, 40',
  },
  {
    icono: GitBranch,
    titulo: '4. Sabe quién depende de qué',
    texto:
      'Lee los imports del árbol (también los de varias líneas y los re-export de los barrels) y resuelve cada uno a su archivo: rutas relativas, alias del tsconfig, paquetes del monorepo y módulos de Python. Si dos paquetes definen useAuth, get_impact_radius dice qué archivos dependen de cada uno. Coincide con el compilador de TypeScript en el 100 % de los imports locales.',
    fila: '35-37',
  },
];

const EXTRAS = [
  { icono: Eye, titulo: 'Observador de cambios', texto: 'Servicio opcional que reindexa solo el archivo que guardas (~8 ms en uno pequeño, tras 0,6 s de espera). Usa unos 275-306 MB de RAM.', fila: '30' },
  { icono: Scissors, titulo: 'Filtro de salidas largas', texto: 'Opcional para Claude Code: recorta salidas enormes de la terminal y conserva todas las líneas de error. La salida completa queda en un archivo.', fila: '24' },
  { icono: MessageSquareText, titulo: 'Modo conciso', texto: 'Opcional: respuestas cortas del modelo (-77 % en su salida en 10 tareas), basado en Caveman de Julius Brussee (Apache-2.0).', fila: '31' },
  { icono: Package, titulo: 'Mapa y empaquetado', texto: 'Firmas de los archivos más importantes por PageRank dentro de un presupuesto de tokens, o el repo entero solo con firmas para pegarlo en un chat web.', fila: '23' },
];

export const ComoFunciona: React.FC = () => (
  <Seccion
    id="como-funciona"
    etiqueta="Cómo funciona"
    titulo="Cuatro piezas, todas en tu máquina"
    alterna
    intro={
      <p>
        El motor es Python y corre en CPU. Las IAs se conectan por el protocolo MCP: el instalador registra el servidor
        <code className="mx-1 text-[#E6EDF3]">desktop-lancedb</code> en cada IA que encuentre y añade a sus instrucciones un bloque corto
        que le pide buscar antes de abrir archivos. Sin ese bloque, la IA ve la herramienta pero casi nunca la elige.
      </p>
    }
  >
    <ol className="grid gap-5 md:grid-cols-2">
      {PASOS.map(({ icono: Icono, titulo, texto, fila }) => (
        <li key={titulo} className="syn-card rounded-xl p-6">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#00E5FF]/10 text-[#00E5FF]">
              <Icono className="h-5 w-5" />
            </span>
            <h3 className="font-bold text-white">{titulo}</h3>
          </div>
          <p className="mt-4 text-sm leading-relaxed text-[#8B949E]">{texto}</p>
          <div className="mt-4"><Fuente fila={fila} href={CLAIMS} /></div>
        </li>
      ))}
    </ol>
    <h3 className="mt-14 text-lg font-bold text-white">Y alrededor</h3>
    <div className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
      {EXTRAS.map(({ icono: Icono, titulo, texto, fila }) => (
        <div key={titulo} className="rounded-xl border border-[#30363D] p-5">
          <Icono className="h-5 w-5 text-[#00E5FF]" />
          <h4 className="mt-3 text-sm font-bold text-white">{titulo}</h4>
          <p className="mt-2 text-sm leading-relaxed text-[#8B949E]">{texto}</p>
          <div className="mt-3"><Fuente fila={fila} href={CLAIMS} /></div>
        </div>
      ))}
    </div>
  </Seccion>
);
