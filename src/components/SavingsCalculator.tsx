import { useState, useMemo } from 'react';
import { DollarSign, TrendingUp, Zap, Clock, ShieldCheck, Cpu } from 'lucide-react';

interface AIModel {
  name: string;
  provider: string;
  costPerMillionTokens: number;
}

const AI_MODELS: AIModel[] = [
  { name: 'Económico', provider: 'precio de ejemplo', costPerMillionTokens: 1.0 },
  { name: 'Medio', provider: 'precio de ejemplo', costPerMillionTokens: 3.0 },
  { name: 'Alto', provider: 'precio de ejemplo', costPerMillionTokens: 5.0 },
  { name: 'Premium', provider: 'precio de ejemplo', costPerMillionTokens: 15.0 },
];

export const SavingsCalculator: React.FC = () => {
  const [dailyQueries, setDailyQueries] = useState<number>(60);
  const [avgFileLines, setAvgFileLines] = useState<number>(650);
  const [selectedModelIdx, setSelectedModelIdx] = useState<number>(0);

  const selectedModel = AI_MODELS[selectedModelIdx];

  const calculations = useMemo(() => {
    // Escenario hipotetico (NO es una medicion). Supuesto: sin SynRAG se leeria el archivo completo
    // mas sus importaciones (~3.5x las lineas) a ~3.8 tokens por linea.
    const tokensPerTraditionalQuery = Math.round(avgFileLines * 3.5 * 3.8);
    // SyntaxRAG: solo el fragmento sintactico AST exacto (~45 lineas promedio) * ~3.8 tokens
    const tokensPerSynragQuery = Math.round(45 * 3.8);

    const tokensSavedPerQuery = Math.max(0, tokensPerTraditionalQuery - tokensPerSynragQuery);
    const monthlyQueries = dailyQueries * 30;

    const monthlyTokensSaved = monthlyQueries * tokensSavedPerQuery;
    const monthlyDollarsSaved = (monthlyTokensSaved / 1_000_000) * selectedModel.costPerMillionTokens;
    const yearlyDollarsSaved = monthlyDollarsSaved * 12;

    const tokenReductionPercent = Math.round((tokensSavedPerQuery / tokensPerTraditionalQuery) * 100);

    return {
      tokensPerTraditionalQuery,
      tokensPerSynragQuery,
      monthlyTokensSaved,
      monthlyDollarsSaved: monthlyDollarsSaved.toFixed(2),
      yearlyDollarsSaved: yearlyDollarsSaved.toFixed(2),
      tokenReductionPercent,
    };
  }, [dailyQueries, avgFileLines, selectedModel]);

  return (
    <section id="calculadora" className="scroll-mt-20 border-b border-[#30363D] bg-[#0D1117] py-16 sm:py-24 relative overflow-hidden">
      {/* Background radial glow */}
      <div className="absolute top-1/2 left-1/4 -translate-y-1/2 w-[600px] h-[350px] bg-[#00E5FF]/5 blur-[130px] rounded-full pointer-events-none" />

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Encabezado */}
        <div className="text-center max-w-3xl mx-auto">
          <p className="text-xs font-mono font-bold uppercase tracking-[0.2em] text-[#00E5FF] flex items-center justify-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00E5FF] animate-pulse" />
            ESCENARIO HIPOTÉTICO · SUPUESTOS EDITABLES
          </p>
          <h2 className="mt-3 text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight text-white">
            Calculadora de Escenarios de Tokens
          </h2>
          <p className="mt-3 text-sm sm:text-base text-[#8B949E]">
            Estima un escenario con supuestos que tú ajustas: cuántos tokens leería tu IA con archivos enteros y cuántos con fragmentos AST. No es una medición ni una promesa de ahorro: el resultado real depende de cuántas lecturas evite SyntaxRAG en tu trabajo.
          </p>
        </div>

        {/* Panel Interactivo */}
        <div className="mt-12 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          {/* Lado Izquierdo: Controles y Sliders (7 Cols) */}
          <div className="lg:col-span-7 rounded-2xl border border-[#30363D] bg-[#161B22] p-6 sm:p-8 shadow-2xl space-y-7">
            {/* Control 1: Consultas por dia */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs sm:text-sm font-bold text-white flex items-center gap-2">
                  <Zap className="w-4 h-4 text-[#00E5FF]" />
                  Consultas de código a la IA por día:
                </label>
                <span className="font-mono text-sm sm:text-base font-black text-[#00E5FF] px-2.5 py-0.5 rounded-lg bg-[#0D1117] border border-[#30363D]">
                  {dailyQueries} consultas/día
                </span>
              </div>
              <input
                type="range"
                min="10"
                max="300"
                step="5"
                value={dailyQueries}
                onChange={(e) => setDailyQueries(Number(e.target.value))}
                className="w-full h-2 bg-[#21262D] rounded-lg appearance-none cursor-pointer accent-[#00E5FF]"
              />
              <div className="flex justify-between text-[11px] font-mono text-[#8B949E] mt-1.5">
                <span>10 (Uso personal)</span>
                <span>100 (Programación intensiva)</span>
                <span>300 (Flujo multi-agente)</span>
              </div>
            </div>

            {/* Control 2: Tamaño promedio del archivo */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs sm:text-sm font-bold text-white flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-[#58A6FF]" />
                  Tamaño promedio de archivos consultados:
                </label>
                <span className="font-mono text-sm sm:text-base font-black text-[#58A6FF] px-2.5 py-0.5 rounded-lg bg-[#0D1117] border border-[#30363D]">
                  {avgFileLines} líneas / archivo
                </span>
              </div>
              <input
                type="range"
                min="150"
                max="2000"
                step="50"
                value={avgFileLines}
                onChange={(e) => setAvgFileLines(Number(e.target.value))}
                className="w-full h-2 bg-[#21262D] rounded-lg appearance-none cursor-pointer accent-[#58A6FF]"
              />
              <div className="flex justify-between text-[11px] font-mono text-[#8B949E] mt-1.5">
                <span>150 líneas (Hooks/Utils)</span>
                <span>650 líneas (Servicios/Controladores)</span>
                <span>2,000 líneas (Módulos legacy)</span>
              </div>
            </div>

            {/* Control 3: Modelo de IA */}
            <div>
              <label className="text-xs sm:text-sm font-bold text-white mb-2.5 block">
                Precio por millón de tokens (de ejemplo; revisa el de tu proveedor):
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {AI_MODELS.map((model, idx) => (
                  <button
                    key={model.name}
                    onClick={() => setSelectedModelIdx(idx)}
                    className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                      selectedModelIdx === idx
                        ? 'bg-[#21262D] border-[#00E5FF] shadow-[0_0_12px_-2px_rgba(0,229,255,0.3)]'
                        : 'bg-[#0D1117] border-[#30363D] hover:border-[#8B949E]'
                    }`}
                  >
                    <div className="font-bold text-xs text-white truncate">{model.name}</div>
                    <div className="text-[10px] text-[#8B949E] mt-0.5">{model.provider}</div>
                    <div className="text-[11px] font-mono font-bold text-[#7EE787] mt-1">
                      ${model.costPerMillionTokens}/M tokens
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Comparación Visual de Barras */}
            <div className="pt-4 border-t border-[#30363D] space-y-3">
              <div className="text-xs font-mono font-bold text-[#8B949E] uppercase tracking-wider">
                Consumo de Tokens por Consulta:
              </div>

              <div>
                <div className="flex justify-between text-xs font-mono mb-1">
                  <span className="text-[#FF7B72]">Supuesto: archivo completo y sus importaciones:</span>
                  <span className="font-bold text-[#FF7B72]">{calculations.tokensPerTraditionalQuery.toLocaleString()} tokens</span>
                </div>
                <div className="w-full bg-[#0D1117] rounded-full h-2.5 overflow-hidden border border-[#30363D]">
                  <div className="bg-[#FF7B72] h-full rounded-full w-full" />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-mono mb-1">
                  <span className="text-[#00E5FF]">Supuesto con SyntaxRAG (fragmento AST de ~45 líneas):</span>
                  <span className="font-bold text-[#00E5FF]">{calculations.tokensPerSynragQuery.toLocaleString()} tokens</span>
                </div>
                <div className="w-full bg-[#0D1117] rounded-full h-2.5 overflow-hidden border border-[#30363D]">
                  <div 
                    className="bg-[#00E5FF] h-full rounded-full transition-all duration-300" 
                    style={{ width: `${Math.max(3, 100 - calculations.tokenReductionPercent)}%` }} 
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Lado Derecho: Tarjetas de Impacto Financiero y Productividad (5 Cols) */}
          <div className="lg:col-span-5 space-y-4">
            {/* Tarjeta de Ahorro Monetario */}
            <div className="rounded-2xl border border-[#00E5FF]/40 bg-gradient-to-br from-[#161B22] to-[#0D1117] p-6 shadow-2xl relative overflow-hidden">
              <div className="absolute top-0 right-0 p-4 opacity-10">
                <DollarSign className="w-24 h-24 text-[#00E5FF]" />
              </div>

              <div className="flex items-center gap-2 text-xs font-mono font-bold uppercase tracking-wider text-[#00E5FF]">
                <TrendingUp className="w-4 h-4" />
                Escenario: costo evitado (hipotético)
              </div>

              <div className="mt-3 flex items-baseline gap-2">
                <span className="text-4xl sm:text-5xl font-black text-white font-mono tracking-tight">
                  ${calculations.monthlyDollarsSaved}
                </span>
                <span className="text-xs font-mono text-[#8B949E]">/ mes</span>
              </div>

              <div className="mt-1 text-xs font-mono text-[#7EE787]">
                Equivale a <strong className="font-bold">${calculations.yearlyDollarsSaved} USD</strong> al año en este escenario.
              </div>

              <div className="mt-5 pt-4 border-t border-[#30363D] grid grid-cols-2 gap-4">
                <div>
                  <div className="text-[11px] font-mono text-[#8B949E]">Tokens menos (supuesto):</div>
                  <div className="text-sm font-mono font-bold text-white mt-0.5">
                    {(calculations.monthlyTokensSaved / 1_000_000).toFixed(1)}M / mes
                  </div>
                </div>
                <div>
                  <div className="text-[11px] font-mono text-[#8B949E]">Reducción supuesta:</div>
                  <div className="text-sm font-mono font-bold text-[#00E5FF] mt-0.5">
                    -{calculations.tokenReductionPercent}% tokens
                  </div>
                </div>
              </div>
            </div>

            {/* Tarjeta de Tiempo Ahorrado */}
            <div className="rounded-2xl border border-[#30363D] bg-[#161B22] p-5 shadow-xl">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-[#58A6FF]/15 text-[#58A6FF] shrink-0">
                  <Clock className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-xs font-mono text-[#8B949E]">Latencia local medida por el autor:</div>
                  <div className="text-lg font-black font-mono text-white">
                    ~90 ms por consulta nueva
                  </div>
                </div>
              </div>
              <p className="mt-3 text-xs text-[#8B949E] leading-relaxed">
                Mediana de 14 consultas de 2 a 4 palabras por MCP, con el equipo en reposo (6-oct-2026); ~9 ms si repites la misma consulta. Con la CPU saturada tarda el doble. La calculadora no estima tiempo ahorrado: no hay medición de cuánto tardaría una lectura completa.
              </p>
            </div>

            {/* Tarjeta de Blindaje de Cuota */}
            <div className="rounded-2xl border border-[#30363D] bg-[#161B22] p-5 shadow-xl">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-[#7EE787]/15 text-[#7EE787] shrink-0">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-xs font-mono text-[#8B949E]">Lo que esta calculadora no mide:</div>
                  <div className="text-sm font-black text-white">
                    Depende de tu forma de trabajar
                  </div>
                </div>
              </div>
              <p className="mt-2 text-xs text-[#8B949E] leading-relaxed">
                Supone que sin SyntaxRAG se leería cada archivo completo más sus importaciones. Si tu agente ya lee fragmentos acotados, el ahorro será menor. Los resultados de una búsqueda igualmente cuestan tokens. Mide tu consumo real antes de decidir; los resultados medidos están en CLAIMS.md del repositorio.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
