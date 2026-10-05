import React from 'react';
import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { Metrics } from './components/Metrics';
import { Playground } from './components/Playground';
import { SavingsCalculator } from './components/SavingsCalculator';
import { InteractiveTerminal } from './components/InteractiveTerminal';
import { Architecture } from './components/Architecture';
import { Features } from './components/Features';
import { Comparison } from './components/Comparison';
import { DaemonStatus } from './components/DaemonStatus';
import { Integrations } from './components/Integrations';
import { Install } from './components/Install';
import { Faq } from './components/Faq';
import { Footer } from './components/Footer';

export const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#0D1117] text-white selection:bg-[#00E5FF]/25 selection:text-[#00E5FF] font-sans antialiased">
      {/* Top Navbar */}
      <Navbar />

      {/* Main Page Flow */}
      <main>
        {/* Hero Section */}
        <Hero />

        {/* Instalación en 1 línea */}
        <Install />

        {/* Live Ecosystem Metrics */}
        <Metrics />

        {/* Interactive AST Search & Impact Graph Playground */}
        <Playground />

        {/* Real Economic & Latency Savings Interactive Calculator */}
        <SavingsCalculator />

        {/* Live Developer Interactive Terminal Simulator */}
        <InteractiveTerminal />

        {/* 7-Stage Architecture Flow */}
        <Architecture />

        {/* 5 Core Innovations */}
        <Features />

        {/* Benchmark: Traditional RAG vs Synrag */}
        <Comparison />

        {/* Real-time Daemon Event Simulator */}
        <DaemonStatus />

        {/* Ready-to-copy MCP and CLI Integrations */}
        <Integrations />

        {/* Preguntas frecuentes */}
        <Faq />
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default App;
