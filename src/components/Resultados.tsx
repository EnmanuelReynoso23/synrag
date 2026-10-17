import { CircleX, FlaskConical, TriangleAlert } from 'lucide-react';
import { CLAIMS, MEDICIONES, NO_AFIRMADO, PIERDE, PRINCIPAL } from '../data/medido';
import { Copiable, Fuente, Seccion } from './ui';

export const Resultados: React.FC = () => (
  <Seccion
    id="resultados"
    etiqueta="Resultados"
    titulo="Medido, no prometido"
    intro={
      <p>
        Cada cifra de esta página tiene una fila en <a href={CLAIMS} target="_blank" rel="noreferrer" className="text-[#00E5FF] underline underline-offset-2">CLAIMS.md</a> con
        la fecha, el resultado y el comando para repetirla en tu equipo sobre repositorios públicos (Flask y Hono). La comparación
        justa no es contra leer archivos enteros, sino contra lo que hace un agente sin SynRAG: <code className="text-[#E6EDF3]">grep</code> y
        leer el tramo.
      </p>
    }
  >
    <div className="syn-card rounded-2xl p-6 sm:p-8">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div className="max-w-2xl">
          <p className="flex items-center gap-2 font-mono text-xs uppercase tracking-[0.18em] text-[#00E5FF]">
            <FlaskConical className="h-4 w-4" /> La prueba principal
          </p>
          <h3 className="mt-3 text-xl font-bold text-white">Un agente real resolviendo tareas de varios pasos</h3>
          <p className="mt-3 text-sm leading-relaxed text-[#8B949E]">
            Las mismas {PRINCIPAL.tareas.toLowerCase()} con y sin SynRAG: localizar código, entenderlo, planear un cambio y correr
            pruebas en Flask, Hono y el propio SynRAG. Se cuentan todos los tokens que cobra la API, no una estimación. Modelo:
            {' '}{PRINCIPAL.modelo}.
          </p>
        </div>
        <div className="text-right">
          <p className="text-5xl font-black text-[#00E5FF]">{PRINCIPAL.ahorro}</p>
          <p className="mt-1 text-sm text-[#8B949E]">tokens, {PRINCIPAL.sin} -&gt; {PRINCIPAL.con}</p>
          <p className="text-sm text-[#8B949E]">correctas {PRINCIPAL.calidadAntes} -&gt; {PRINCIPAL.calidadDespues}</p>
        </div>
      </div>
      <div className="mt-6 grid gap-4 border-t border-[#30363D] pt-6 text-sm text-[#8B949E] md:grid-cols-3">
        <p><span className="font-semibold text-white">Intervalo de confianza 95 %:</span> {PRINCIPAL.ic}. Con 10 tareas el margen es amplio, pero excluye el cero.</p>
        <p><span className="font-semibold text-white">Dónde gana más:</span> buscar métodos dentro de clases (c.json de Hono -94 %, métodos de Config -73 %) y planear un cambio (-65 %).</p>
        <p><span className="font-semibold text-white">La versión anterior:</span> la 1.5 midió -4,6 % ese mismo día. La 1.6 mejoró sobre todo al trocear clases y objetos grandes.</p>
      </div>
      <div className="mt-6">
        <Copiable texto={PRINCIPAL.comando} etiqueta="Repetirlo:" />
        <div className="mt-2"><Fuente fila={String(PRINCIPAL.fila)} href={CLAIMS} /></div>
      </div>
    </div>

    <div className="mt-8 overflow-hidden rounded-xl border border-[#30363D]">
      <table className="w-full text-left text-sm">
        <thead className="bg-[#161B22] text-xs uppercase tracking-wider text-[#8B949E]">
          <tr>
            <th className="px-4 py-3 font-semibold">Qué se midió</th>
            <th className="px-4 py-3 font-semibold">Resultado</th>
            <th className="hidden px-4 py-3 font-semibold lg:table-cell">Detalle</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#30363D]">
          {MEDICIONES.map((m) => (
            <tr key={m.que} className="align-top">
              <td className="px-4 py-4">
                <p className="font-semibold text-white">{m.que}</p>
                <p className="mt-2 text-xs text-[#8B949E] lg:hidden">{m.detalle}</p>
                <code className="mt-2 block break-all font-mono text-[11px] text-[#8B949E]">{m.comando}</code>
                <div className="mt-1"><Fuente fila={m.fila} href={CLAIMS} /></div>
              </td>
              <td className="whitespace-nowrap px-4 py-4 font-mono text-base font-bold text-[#00E5FF]">{m.resultado}</td>
              <td className="hidden px-4 py-4 text-[#8B949E] lg:table-cell">{m.detalle}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>

    <div className="mt-12 grid gap-8 lg:grid-cols-2">
      <div>
        <h3 className="flex items-center gap-2 text-lg font-bold text-white">
          <TriangleAlert className="h-5 w-5 text-[#D29922]" /> Dónde pierde
        </h3>
        <ul className="mt-4 space-y-4">
          {PIERDE.map((p) => (
            <li key={p.titulo} className="rounded-xl border border-[#D29922]/30 bg-[#D29922]/5 p-4">
              <p className="font-semibold text-white">{p.titulo}</p>
              <p className="mt-1 text-sm leading-relaxed text-[#8B949E]">{p.texto}</p>
              <div className="mt-2"><Fuente fila={p.fila} href={CLAIMS} /></div>
            </li>
          ))}
        </ul>
      </div>
      <div>
        <h3 className="flex items-center gap-2 text-lg font-bold text-white">
          <CircleX className="h-5 w-5 text-[#F85149]" /> Lo que no afirmamos
        </h3>
        <ul className="mt-4 space-y-3">
          {NO_AFIRMADO.map((t) => (
            <li key={t} className="flex gap-3 text-sm leading-relaxed text-[#8B949E]">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[#F85149]" />
              {t}
            </li>
          ))}
        </ul>
        <p className="mt-6 rounded-xl border border-[#30363D] p-4 text-sm leading-relaxed text-[#8B949E]">
          Lo que más pesa en una sesión real no es ninguna herramienta: es la longitud de la sesión, porque cada turno reenvía todo el
          historial. Por eso SynRAG trae <code className="text-[#E6EDF3]">context_budget_alert</code> y <code className="text-[#E6EDF3]">session_handoff</code>, para
          cortar a tiempo.
        </p>
      </div>
    </div>
  </Seccion>
);
