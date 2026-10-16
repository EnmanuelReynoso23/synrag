// Oraculo para benchmarks/resolucion.py: a que archivo resuelve TypeScript cada import.
// Lee por stdin lineas "archivo<TAB>origen" y escribe "archivo<TAB>origen<TAB>destino" (destino vacio si
// es un paquete externo o no resuelve). Usa el tsconfig/jsconfig mas cercano que incluya el archivo
// (con extends) y, en monorepos, sigue los enlaces de node_modules hasta el paquete local.
const fs = require("fs");
const path = require("path");
const ts = require("typescript");

const configs = new Map(); // ruta de config -> {options, files:Set}
function cargar(cfgPath) {
  if (!configs.has(cfgPath)) {
    let r = null;
    try {
      const p = ts.getParsedCommandLineOfConfigFile(cfgPath, {}, { ...ts.sys, onUnRecoverableConfigFileDiagnostic: () => {} });
      if (p) r = { options: p.options, files: new Set(p.fileNames.map((f) => path.resolve(f))) };
    } catch (e) {}
    configs.set(cfgPath, r);
  }
  return configs.get(cfgPath);
}

const porCarpeta = new Map();
function opcionesPara(archivo) {
  const carpeta = path.dirname(archivo);
  if (porCarpeta.has(carpeta)) {
    const c = porCarpeta.get(carpeta);
    if (c === null || c.files.has(archivo)) return c ? c.options : { allowJs: true };
  }
  let dir = carpeta, primero = null;
  for (let i = 0; i < 12; i++) {
    for (const n of ["tsconfig.json", "tsconfig.app.json", "jsconfig.json"]) {
      const f = path.join(dir, n);
      if (fs.existsSync(f)) {
        const c = cargar(f);
        if (!c) continue;
        if (!primero) primero = c;
        if (c.files.has(archivo)) { porCarpeta.set(carpeta, c); return c.options; }
      }
    }
    const padre = path.dirname(dir);
    if (padre === dir) break;
    dir = padre;
  }
  porCarpeta.set(carpeta, primero);
  return primero ? primero.options : { allowJs: true };
}

const lineas = fs.readFileSync(0, "utf8").split("\n").filter(Boolean);
const salida = [];
for (const l of lineas) {
  const [archivo, origen] = l.split("\t");
  let destino = "";
  try {
    const opts = { allowJs: true, ...opcionesPara(archivo) };
    const r = ts.resolveModuleName(origen, archivo, opts, ts.sys);
    const m = r.resolvedModule;
    if (m) {
      const real = fs.realpathSync(m.resolvedFileName);
      if (!real.split(path.sep).includes("node_modules")) destino = real;
    }
  } catch (e) {}
  salida.push(`${archivo}\t${origen}\t${destino}`);
}
process.stdout.write(salida.join("\n") + "\n");
