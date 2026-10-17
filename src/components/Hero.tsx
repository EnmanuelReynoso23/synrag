import { ArrowRight, Lock, ShieldCheck, Cpu } from 'lucide-react';
import { CLAIMS, INSTALAR, PRINCIPAL } from '../data/medido';
import { Copiable } from './ui';

export const Hero: React.FC = () => (
  <section id="inicio" className="relative overflow-hidden border-b border-[#30363D] bg-ast-grid">
    <div aria-hidden="true" className="pointer-events-none absolute -top-40 left-1/2 -z-10 h-[460px] w-[900px] -translate-x-1/2 bg-gradient-to-b from-[#00E5FF]/15 via-[#58A6FF]/10 to-transparent blur-3xl" />
    <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 sm:py-20 lg:grid-cols-12 lg:px-8">
      <div className="lg:col-span-7">
        <p className="inline-flex items-center gap-2 rounded-full border border-[#30363D] bg-[#161B22] px-3.5 py-1.5 font-mono text-xs text-[#00E5FF]">
          <span className="h-2 w-2 animate-pulse rounded-full bg-[#00E5FF]" />
          Motor MCP local · código abierto · licencia MIT
        </p>
        <h1 className="mt-6 text-4xl font-black leading-[1.05] tracking-tight text-white sm:text-5xl">
          Tu IA encuentra el código
          <span className="block bg-gradient-to-r from-white via-[#00E5FF] to-[#58A6FF] bg-clip-text text-transparent">sin leerse el repo entero</span>
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-relaxed text-[#8B949E]">
          SynRAG indexa tus proyectos en tu propia máquina, trocea el código por su estructura (funciones, clases, tipos) y se lo
          entrega a Claude Code, Antigravity y otros agentes por el protocolo MCP: la definición exacta, quién la usa y qué se rompe
          si la cambias. Sin APIs de pago y sin que tu código salga de tu equipo.
        </p>
        <div className="mt-8 max-w-2xl">
          <Copiable texto={INSTALAR} />
          <p className="mt-2 text-xs text-[#8B949E]">Probado en Linux. Configura solo las IAs que tengas instaladas y respalda cada archivo antes de tocarlo.</p>
        </div>
        <div className="mt-8 flex flex-wrap gap-3">
          <a href="#resultados" className="inline-flex items-center gap-2 rounded-lg bg-[#00E5FF] px-5 py-2.5 text-sm font-bold text-[#0D1117] transition hover:bg-[#5CF0FF]">
            Ver cómo se midió <ArrowRight className="h-4 w-4" />
          </a>
          <a href="#como-funciona" className="inline-flex items-center gap-2 rounded-lg border border-[#30363D] px-5 py-2.5 text-sm font-semibold text-white transition hover:border-[#00E5FF]/60">
            Cómo funciona
          </a>
        </div>
        <ul className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-[#8B949E]">
          <li className="flex items-center gap-2"><Lock className="h-4 w-4 text-[#00E5FF]" /> Todo local</li>
          <li className="flex items-center gap-2"><Cpu className="h-4 w-4 text-[#00E5FF]" /> Solo CPU, sin GPU</li>
          <li className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-[#00E5FF]" /> Cada cifra con su guion</li>
        </ul>
      </div>

      <div className="lg:col-span-5">
        <div className="syn-card glow-cyan rounded-2xl p-6 sm:p-8">
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-[#8B949E]">Medido con un agente real</p>
          <p className="mt-4 text-6xl font-black tracking-tight text-[#00E5FF] sm:text-7xl">{PRINCIPAL.ahorro}</p>
          <p className="mt-2 text-lg font-semibold text-white">tokens frente a trabajar sin SynRAG</p>
          <dl className="mt-6 grid grid-cols-2 gap-4 border-t border-[#30363D] pt-6 text-sm">
            <div>
              <dt className="text-[#8B949E]">Sin SynRAG</dt>
              <dd className="font-mono text-white">{PRINCIPAL.sin} tokens</dd>
            </div>
            <div>
              <dt className="text-[#8B949E]">Con SynRAG</dt>
              <dd className="font-mono text-[#00E5FF]">{PRINCIPAL.con} tokens</dd>
            </div>
            <div>
              <dt className="text-[#8B949E]">Respuestas correctas</dt>
              <dd className="font-mono text-white">{PRINCIPAL.calidadAntes} -&gt; {PRINCIPAL.calidadDespues}</dd>
            </div>
            <div>
              <dt className="text-[#8B949E]">Intervalo 95 %</dt>
              <dd className="font-mono text-white">{PRINCIPAL.ic}</dd>
            </div>
          </dl>
          <p className="mt-6 text-xs leading-relaxed text-[#8B949E]">
            {PRINCIPAL.tareas} (localizar, entender, planear un cambio, correr pruebas), {PRINCIPAL.modelo}, tokens cobrados por la API,{' '}
            {PRINCIPAL.fecha}.{' '}
            <a href={CLAIMS} target="_blank" rel="noreferrer" className="text-[#00E5FF] underline underline-offset-2">
              Detalle, límites y comando para repetirlo
            </a>
            .
          </p>
        </div>
      </div>
    </div>
  </section>
);
