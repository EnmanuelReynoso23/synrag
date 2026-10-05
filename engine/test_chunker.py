import sys
from pathlib import Path
sys.path.append('/home/reyno/.local/opt/lancedb-hub')
import chunker

f = Path('/home/reyno/AsistoYA/Proyectos/asistoya-web/apps/web/src/modulos/estudiantes/useEstudiantes.ts')
text = f.read_text('utf-8')
chunks = chunker.chunk_file(f, text)
print(f"useEstudiantes.ts -> {len(chunks)} chunks semánticos:")
for c in chunks:
    print(f"  L{c['line']}-L{c['end_line']} [{c['symbol_kind']}] {c['symbol_name']}")
