import React from 'react';
import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { Metrics } from './components/Metrics';
import { Playground } from './components/Playground';
import { Architecture } from './components/Architecture';
import { Features } from './components/Features';
import { Comparison } from './components/Comparison';
import { DaemonStatus } from './components/DaemonStatus';
import { Integrations } from './components/Integrations';
import { Footer } from './components/Footer';

export const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#0d1117] text-[#cdd6f4] selection:bg-[#00e5ff]/30 selection:text-white">
      {/* Top Navbar */}
      <Navbar />

      {/* Main Page Flow */}
      <main>
        {/* Hero Section */}
        <Hero />

        {/* Live Ecosystem Metrics */}
        <Metrics />

        {/* Interactive AST Search & Impact Graph Playground */}
        <Playground />

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
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default App;
