# ⚡ Synrag Web (SyntaxRAG)

Landing page premium y simulador interactivo de búsqueda AST para **Synrag (SyntaxRAG)**, el motor de inteligencia de código local nativo para agentes de IA (Claude Code, Antigravity CLI).

[![Vite](https://img.shields.io/badge/Vite-8.3-646CFF.svg)](https://vite.dev/)
[![React](https://img.shields.io/badge/React-19.3-61DAFB.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.0-3178C6.svg)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-4.3-38B2AC.svg)](https://tailwindcss.com/)
[![Catppuccin](https://img.shields.io/badge/Theme-Catppuccin%20Mocha-cba6f7.svg)](https://github.com/catppuccin/catppuccin)

---

## 🚀 Características de la Web

1. **Terminal Hero Interactivo**: Visualización de consultas reales del CLI y MCP (`useAsistenciaServicio`, alertas de Grafo de Impacto, `0.38 ms` de latencia en caché).
2. **Simulador de Búsqueda AST (Playground)**:
   - Prueba consultas reales del monorepo (`asistoya-web`, `syntaxrag-core`, `asistoya-api`).
   - Muestra el bloque extraído quirúrgicamente por Tree-sitter con numeración de líneas.
   - Inspector de consumidores del **Grafo de Impacto** con niveles de riesgo (CRITICAL, WARNING, INFO).
   - Interruptor de Caché Semántico (`< 1 ms` vs `Tantivy + FlashRank`).
3. **Diagrama de Arquitectura de 7 Fases**: Inspección interactiva de cada etapa del pipeline (desde el agente IA hasta el reranker ONNX en CPU).
4. **Métricas en Tiempo Real**: Estadísticas en vivo del ecosistema local (7,536+ archivos, 95,597+ fragmentos AST, 23,364+ dependencias, 18 ms hot-reload).
5. **Simulador del Demonio Reactivo (Ctrl+S)**: Visualización en vivo del log del servicio `lancedb-watcher.service`.
6. **Benchmark Comparativo**: Comparativa punto por punto entre RAG tradicional vs. Synrag.
7. **Guía de Integración Rápida**: Snippets copiables con un clic para `~/.claude.json`, `mcp.json`, binario CLI y atajos de Herdr.

---

## 💻 Desarrollo Local

```bash
# Entrar al proyecto
cd ~/Proyectos/synrag-web

# Instalar dependencias (ya instaladas)
pnpm install

# Iniciar servidor de desarrollo
pnpm dev

# Compilar para producción
pnpm build

# Previsualizar el bundle de producción
pnpm preview
```

---

## 📁 Estructura del Código

- `src/components/Navbar.tsx`: Barra superior con el logo oficial SVG, pulso del watcher y botón de copia rápida de configuración MCP.
- `src/components/Hero.tsx`: Encabezado de alto impacto con terminal interactiva de 3 pestañas (CLI, MCP, Impacto).
- `src/components/Playground.tsx`: Simulador AST interactivo con filtrado por proyectos y visor de dependencias.
- `src/components/Architecture.tsx`: Navegador interactivo de las 7 fases del pipeline.
- `src/components/Features.tsx`: Tarjetas de las 5 innovaciones clave de SyntaxRAG.
- `src/components/Comparison.tsx`: Tabla de comparación RAG tradicional vs Synrag.
- `src/components/DaemonStatus.tsx`: Simulador de eventos reactivos del watcher por guardado Ctrl+S.
- `src/components/Integrations.tsx`: Pestañas con snippets copiables para Claude Code, Antigravity, CLI y Systemd.
- `src/components/Footer.tsx`: Enlaces, referencias a `/home/reyno/.local/opt/lancedb-hub` y créditos tecnológicos.
- `src/data/mockData.ts`: Consultas realistas del monorepo, fragmentos AST y pipeline de datos.
