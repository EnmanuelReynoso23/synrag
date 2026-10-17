import { ChevronDown } from 'lucide-react';
import { CLAIMS } from '../data/medido';
import { Seccion } from './ui';

const PREGUNTAS = [
  {
    p: '¿Mi código sale de mi computadora?',
    r: 'No. El índice, la búsqueda y el reordenado corren en tu equipo, en CPU. El motor solo usa la red si tú configuras tu propia GEMINI_API_KEY para las dos herramientas opcionales de Gemini. Lo que SynRAG devuelve sí lo lee tu IA, igual que leería el archivo: eso lo decide la IA que uses, no SynRAG.',
  },
  {
    p: '¿Cuánto voy a ahorrar yo?',
    r: 'Depende de tus tareas, tu modelo y lo largas que sean tus sesiones. Lo medido: -63,9 % de tokens en 10 tareas de varios pasos con Gemini 3.5 Flash-Lite, con un intervalo de -83 % a -24 %. En tareas muy cortas puede gastar más. No hay una medición con Claude ni de sesiones largas: no la prometemos.',
  },
  {
    p: '¿En qué se diferencia de un RAG normal para código?',
    r: 'Un RAG de ventanas fijas corta los archivos en bloques de, por ejemplo, 500 tokens, que pueden partir una función por la mitad. SynRAG corta por la estructura del lenguaje y, si preguntas por un nombre, entrega la definición entera y primero. Otras herramientas también trocean por AST: SynRAG es una opción local y abierta que publica cómo se mide cada cifra.',
  },
  {
    p: '¿Necesito GPU o una API de pago?',
    r: 'No. La búsqueda es BM25 sobre LanceDB y el reordenado es un modelo TinyBERT pequeño en CPU. Una consulta nueva tarda 59-89 ms de mediana en un índice de 125.570 fragmentos; repetida, 3-4 ms.',
  },
  {
    p: '¿Qué lenguajes entiende?',
    r: 'TypeScript, TSX/JSX, JavaScript y Python por su árbol sintáctico; Markdown, MDX, reStructuredText y AsciiDoc como documentación; SQL por sentencias. Rust y Go todavía no se indexan.',
  },
  {
    p: '¿Y si mi IA no usa la herramienta?',
    r: 'Pasa: sin instrucciones, una IA casi nunca elige una herramienta nueva. Por eso el instalador añade un bloque corto a sus instrucciones globales (CLAUDE.md, GEMINI.md, AGENTS.md...) entre las marcas SYNRAG:BEGIN y SYNRAG:END. En Claude Code también puedes usar --pista: un aviso que aparece una sola vez por sesión y solo en mensajes de código.',
  },
  {
    p: '¿Qué es lo que más gasta tokens en una sesión?',
    r: 'La longitud de la sesión. Cada turno reenvía todo el historial, así que lo que se leyó al principio se paga en cada mensaje. SynRAG reduce lo que entra, pero cortar a tiempo (context_budget_alert, session_handoff) sigue siendo lo que más ahorra.',
  },
  {
    p: '¿Por qué tanta insistencia en medir?',
    r: 'Porque es fácil escribir "-50 %" en una web. Cada cifra de esta página tiene su fila en CLAIMS.md con el comando para repetirla, y si una deja de cumplirse se cambia o se quita el mismo día. También publicamos dónde pierde.',
  },
];

export const Faq: React.FC = () => (
  <Seccion id="preguntas" etiqueta="Preguntas" titulo="Preguntas frecuentes" alterna>
    <div className="divide-y divide-[#30363D] rounded-xl border border-[#30363D]">
      {PREGUNTAS.map(({ p, r }) => (
        <details key={p} className="group px-5 py-4 [&_summary::-webkit-details-marker]:hidden">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold text-white">
            {p}
            <ChevronDown className="h-4 w-4 shrink-0 text-[#8B949E] transition group-open:rotate-180" />
          </summary>
          <p className="mt-3 text-sm leading-relaxed text-[#8B949E]">{r}</p>
        </details>
      ))}
    </div>
    <p className="mt-6 text-sm text-[#8B949E]">
      ¿Algo que no cuadra? Todas las cifras y sus límites están en{' '}
      <a href={CLAIMS} target="_blank" rel="noreferrer" className="text-[#00E5FF] underline underline-offset-2">CLAIMS.md</a>.
    </p>
  </Seccion>
);
