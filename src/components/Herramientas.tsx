import { CircleCheck, Info } from 'lucide-react';
import { CLAIMS, HERRAMIENTAS, INTEGRACIONES, PERFILES } from '../data/medido';
import { Fuente, Seccion } from './ui';

export const Herramientas: React.FC = () => (
  <Seccion
    id="herramientas"
    etiqueta="Herramientas MCP"
    titulo="28 herramientas para el agente, y tú eliges cuántas carga"
    alterna
    intro={
      <p>
        Cualquier IA conectada ve estas herramientas. Cada definición cuesta tokens en cada turno en los clientes que las cargan todas
        de entrada, así que hay tres perfiles. Se cambia con <code className="text-[#E6EDF3]">SYNRAG configure --perfil &lt;nombre&gt;</code>.
      </p>
    }
  >
    <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
      {HERRAMIENTAS.map((g) => (
        <div key={g.nombre} className="syn-card rounded-xl p-5">
          <h3 className="font-bold text-white">{g.nombre}</h3>
          <p className="mt-1 text-sm text-[#8B949E]">{g.para}</p>
          <ul className="mt-4 flex flex-wrap gap-2">
            {g.herramientas.map((h) => (
              <li key={h} className="rounded-md border border-[#30363D] bg-[#0D1117] px-2 py-1 font-mono text-[11.5px] text-[#E6EDF3]">
                {h}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>

    <h3 className="mt-14 text-lg font-bold text-white">Perfiles</h3>
    <div className="mt-5 overflow-hidden rounded-xl border border-[#30363D]">
      <table className="w-full text-left text-sm">
        <thead className="bg-[#161B22] text-xs uppercase tracking-wider text-[#8B949E]">
          <tr>
            <th className="px-4 py-3">Perfil</th>
            <th className="px-4 py-3">Herramientas</th>
            <th className="px-4 py-3">Costo fijo</th>
            <th className="hidden px-4 py-3 md:table-cell">Cuándo usarlo</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#30363D]">
          {PERFILES.map((p) => (
            <tr key={p.nombre} className="align-top">
              <td className="px-4 py-3 font-mono text-[#00E5FF]">{p.nombre}</td>
              <td className="px-4 py-3 text-white">{p.herramientas}</td>
              <td className="px-4 py-3 text-white">
                {p.costo}
                <div><Fuente fila={p.fila} href={CLAIMS} /></div>
              </td>
              <td className="hidden px-4 py-3 text-[#8B949E] md:table-cell">{p.cuando}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>

    <h3 id="integraciones" className="mt-14 scroll-mt-20 text-lg font-bold text-white">Con qué IAs funciona</h3>
    <p className="mt-2 max-w-3xl text-sm text-[#8B949E]">
      El instalador solo toca las IAs que tienes instaladas, respalda cada archivo antes de modificarlo
      (<code className="text-[#E6EDF3]">.bak-AAAAMMDD-HHMMSS</code>), nunca sobrescribe un JSON que no pueda leer y se puede ejecutar dos
      veces sin duplicar nada.
    </p>
    <div className="mt-5 overflow-x-auto rounded-xl border border-[#30363D]">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="bg-[#161B22] text-xs uppercase tracking-wider text-[#8B949E]">
          <tr>
            <th className="px-4 py-3">IA</th>
            <th className="px-4 py-3">Estado</th>
            <th className="px-4 py-3">Servidor MCP</th>
            <th className="px-4 py-3">Instrucciones</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#30363D]">
          {INTEGRACIONES.map((i) => (
            <tr key={i.ia}>
              <td className="px-4 py-3 font-semibold text-white">{i.ia}</td>
              <td className="px-4 py-3">
                {i.estado === 'probado' ? (
                  <span className="inline-flex items-center gap-1.5 text-[#3FB950]"><CircleCheck className="h-4 w-4" /> probado</span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 text-[#8B949E]"><Info className="h-4 w-4" /> sin probar</span>
                )}
              </td>
              <td className="px-4 py-3 font-mono text-xs text-[#8B949E]">{i.mcp}</td>
              <td className="px-4 py-3 font-mono text-xs text-[#8B949E]">{i.reglas}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    <p className="mt-3 text-xs text-[#8B949E]">"Sin probar" quiere decir que se configura según la documentación de esa IA pero nadie lo ha comprobado todavía. Si la usas, abre una incidencia con el resultado.</p>
  </Seccion>
);
