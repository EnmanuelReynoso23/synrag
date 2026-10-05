import { useState, useMemo } from 'react';
import { DollarSign, TrendingUp, Zap, Clock, ShieldCheck, Cpu } from 'lucide-react';

interface AIModel {
  name: string;
  provider: string;
  costPerMillionTokens: number;
}

const AI_MODELS: AIModel[] = [
  { name: 'Claude 3.5 Sonnet', provider: 'Anthropic', costPerMillionTokens: 3.0 },
  { name: 'Claude 3 Opus', provider: 'Anthropic', costPerMillionTokens: 15.0 },
  { name: 'GPT-4o', provider: 'OpenAI', costPerMillionTokens: 2.5 },
  { name: 'Gemini 1.5 Pro', provider: 'Google', costPerMillionTokens: 3.5 },
];

export const SavingsCalculator: React.FC = () => {
  const [dailyQueries, setDailyQueries] = useState<number>(60);
  const [avgFileLines, setAvgFileLines] = useState<number>(650);
  const [selectedModelIdx, setSelectedModelIdx] = useState<number>(0);

  const selectedModel = AI_MODELS[selectedModelIdx];

  const calculations = useMemo(() => {
    // Estimacion de tokens:
    // Lectura completa tradicional: archivo completo + archivos importados (~3.5x lineas) * ~4 tokens por linea
    const tokensPerTraditionalQuery = Math.round(avgFileLines * 3.5 * 3.8);
    // SyntaxRAG: solo el fragmento sintactico AST exacto (~45 lineas promedio) * ~3.8 tokens
    const tokensPerSynragQuery = Math.round(45 * 3.8);

    const tokensSavedPerQuery = Math.max(0, tokensPerTraditionalQuery - tokensPerSynragQuery);
    const monthlyQueries = dailyQueries * 30;

    const monthlyTokensSaved = monthlyQueries * tokensSavedPerQuery;
    const monthlyDollarsSaved = (monthlyTokensSaved / 1_000_000) * selectedModel.costPerMillionTokens;
    const yearlyDollarsSaved = monthlyDollarsSaved * 12;

    // Latencia: 3.8s por lectura de archivo completa vs 0.018s (18ms) con SyntaxRAG
    const secondsSavedMonthly = monthlyQueries * 3.6;
    const hoursSavedMonthly = +(secondsSavedMonthly / 3600).toFixed(1);

    const tokenReductionPercent = Math.round((tokensSavedPerQuery / tokensPerTraditionalQuery) * 100);

    return {
      tokensPerTraditionalQuery,
      tokensPerSynragQuery,
      monthlyTokensSaved,
      monthlyDollarsSaved: monthlyDollarsSaved.toFixed(2),
      yearlyDollarsSaved: yearlyDollarsSaved.toFixed(2),
      hoursSavedMonthly,
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
            ECONOMIA DE TOKENS & LATENCIA LOCAL
          </p>
          <h2 className="mt-3 text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight text-white">
            Calculadora de Ahorro Real en Desarrollo
          </h2>
          <p className="mt-3 text-sm sm:text-base text-[#8B949E]">
            Mide el impacto económico y el tiempo que recuperas al alimentar tus agentes de IA (Claude Code, Google Antigravity) con fragmentos AST quirúrgicos en lugar de volcar archivos enteros al contexto.
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
                  Consultas semánticas a la IA por día:
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
                Modelo de IA del agente de codificación:
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
                  <span className="text-[#FF7B72]">RAG Tradicional / Lectura Completa:</span>
                  <span className="font-bold text-[#FF7B72]">{calculations.tokensPerTraditionalQuery.toLocaleString()} tokens</span>
                </div>
                <div className="w-full bg-[#0D1117] rounded-full h-2.5 overflow-hidden border border-[#30363D]">
                  <div className="bg-[#FF7B72] h-full rounded-full w-full" />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-mono mb-1">
                  <span className="text-[#00E5FF]">SyntaxRAG (Fragmento AST Quirúrgico):</span>
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
                Ahorro Económico Estimado
              </div>

              <div className="mt-3 flex items-baseline gap-2">
                <span className="text-4xl sm:text-5xl font-black text-white font-mono tracking-tight">
                  ${calculations.monthlyDollarsSaved}
                </span>
                <span className="text-xs font-mono text-[#8B949E]">/ mes</span>
              </div>

              <div className="mt-1 text-xs font-mono text-[#7EE787]">
                Equivalente a <strong className="font-bold">${calculations.yearlyDollarsSaved} USD</strong> ahorrados al año.
              </div>

              <div className="mt-5 pt-4 border-t border-[#30363D] grid grid-cols-2 gap-4">
                <div>
                  <div className="text-[11px] font-mono text-[#8B949E]">Tokens reducidos:</div>
                  <div className="text-sm font-mono font-bold text-white mt-0.5">
                    {(calculations.monthlyTokensSaved / 1_000_000).toFixed(1)}M / mes
                  </div>
                </div>
                <div>
                  <div className="text-[11px] font-mono text-[#8B949E]">Eficiencia de contexto:</div>
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
                  <div className="text-xs font-mono text-[#8B949E]">Horas de Espera Ahorradas:</div>
                  <div className="text-lg font-black font-mono text-white">
                    {calculations.hoursSavedMonthly} horas / mes
                  </div>
                </div>
              </div>
              <p className="mt-3 text-xs text-[#8B949E] leading-relaxed">
                Al evitar lecturas de disco masivas y procesamiento de tokens en la nube, el agente responde en microsegundos vía caché LanceDB local.
              </p>
            </div>

            {/* Tarjeta de Blindaje de Cuota */}
            <div className="rounded-2xl border border-[#30363D] bg-[#161B22] p-5 shadow-xl">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-[#7EE787]/15 text-[#7EE787] shrink-0">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-xs font-mono text-[#8B949E]">Protección de Ventana de Contexto:</div>
                  <div className="text-sm font-black text-white">
                    100% libre de saturación de ventana
                  </div>
                </div>
              </div>
              <p className="mt-2 text-xs text-[#8B949E] leading-relaxed">
                Los prompts se mantienen compactos. La IA nunca sufre de alucinaciones por agotamiento de contexto ni alcanza el límite de TPM (tokens por minuto).
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
