import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { Problema } from './components/Problema';
import { ComoFunciona } from './components/ComoFunciona';
import { Resultados } from './components/Resultados';
import { Herramientas } from './components/Herramientas';
import { Install } from './components/Install';
import { Faq } from './components/Faq';
import { Footer } from './components/Footer';

export const App: React.FC = () => (
  <div className="min-h-screen bg-[#0D1117] font-sans text-white antialiased selection:bg-[#00E5FF]/25 selection:text-[#00E5FF]">
    <Navbar />
    <main>
      <Hero />
      <Problema />
      <ComoFunciona />
      <Resultados />
      <Herramientas />
      <Install />
      <Faq />
    </main>
    <Footer />
  </div>
);

export default App;
