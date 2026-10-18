// Renderiza video/escenas.html a MP4 (1080x1350, 30 fps) fotograma a fotograma.
//
//   node video/render.cjs salida.mp4            video completo
//   node video/render.cjs fotos/ 3 15 27 45     solo fotogramas sueltos (PNG) en esos segundos
//
// Necesita playwright (NODE_PATH a sus node_modules si es global) y ffmpeg en el PATH.
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const FPS = 30;
const AQUI = __dirname;

async function main() {
  const [salida, ...segundos] = process.argv.slice(2);
  if (!salida) throw new Error('uso: node video/render.cjs salida.mp4 | carpeta/ seg1 seg2 ...');

  const terminal = fs.readFileSync(path.join(AQUI, 'terminal.json'), 'utf8');
  const navegador = await chromium.launch();
  const pagina = await navegador.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
  await pagina.addInitScript(`window.TERMINAL = ${terminal};`);
  await pagina.goto('file://' + path.join(AQUI, 'escenas.html'));
  await pagina.evaluate(() => document.fonts.ready);
  const duracion = await pagina.evaluate(() => window.DURACION);

  if (segundos.length) {
    fs.mkdirSync(salida, { recursive: true });
    for (const s of segundos) {
      await pagina.evaluate((t) => window.render(t), +s);
      await pagina.screenshot({ path: path.join(salida, `fotograma-${s}.png`) });
    }
    await navegador.close();
    return;
  }

  const ffmpeg = spawn('ffmpeg', [
    '-y', '-loglevel', 'error',
    '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=48000',
    '-shortest', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', salida,
  ], { stdio: ['pipe', 'inherit', 'inherit'] });

  const total = Math.round(duracion * FPS);
  for (let i = 0; i < total; i++) {
    await pagina.evaluate((t) => window.render(t), i / FPS);
    const png = await pagina.screenshot({ type: 'png' });
    if (!ffmpeg.stdin.write(png)) await new Promise((r) => ffmpeg.stdin.once('drain', r));
    if (i % (FPS * 5) === 0) process.stdout.write(`\r${Math.round((i / total) * 100)} %`);
  }
  ffmpeg.stdin.end();
  await new Promise((r, f) => ffmpeg.on('close', (c) => (c === 0 ? r() : f(new Error('ffmpeg salió con ' + c)))));
  await navegador.close();
  console.log(`\r100 % -> ${salida}`);
}

main().catch((e) => { console.error(e); process.exit(1); });
