// Oraculo para benchmarks/imports.py: los imports de cada archivo segun el compilador de TypeScript.
// Lee rutas por stdin (una por linea) y escribe una linea JSON por archivo: {file, edges: [[simbolo, origen]]}.
// Uso: git ls-files '*.ts' | node benchmarks/imports_ts.cjs   (necesita `typescript` en node_modules)
const fs = require("fs");
const ts = require("typescript");

const rutas = fs.readFileSync(0, "utf8").split("\n").filter(Boolean);
for (const ruta of rutas) {
  const edges = [];
  try {
    const texto = fs.readFileSync(ruta, "utf8");
    const sf = ts.createSourceFile(ruta, texto, ts.ScriptTarget.Latest, false);
    for (const st of sf.statements) {
      if (ts.isImportDeclaration(st) && st.importClause) {
        const origen = st.moduleSpecifier.text;
        const c = st.importClause;
        if (c.name) edges.push([c.name.text, origen]);
        const nb = c.namedBindings;
        if (nb && ts.isNamespaceImport(nb)) edges.push([nb.name.text, origen]);
        if (nb && ts.isNamedImports(nb)) for (const el of nb.elements) edges.push([(el.propertyName || el.name).text, origen]);
      } else if (ts.isExportDeclaration(st) && st.moduleSpecifier) {
        const origen = st.moduleSpecifier.text;
        const ec = st.exportClause;
        if (!ec) edges.push(["*", origen]);
        else if (ts.isNamespaceExport(ec)) edges.push([ec.name.text, origen]);
        else for (const el of ec.elements) edges.push([(el.propertyName || el.name).text, origen]);
      }
    }
  } catch (e) {
    continue;
  }
  process.stdout.write(JSON.stringify({ file: ruta, edges }) + "\n");
}
