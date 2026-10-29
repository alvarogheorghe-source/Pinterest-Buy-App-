// serie.html + serie-<name>.wav -> MP4.  node render_serie.js <ordner mit serie.html> <ausgabe-ordner> [de|en]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const [SRC, OUT, LANG = 'de'] = process.argv.slice(2), FPS = 30;
const NAMES = ['ausverkauft', 'paket', 'schrank', 'warenkorb'];
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  for (const v of NAMES) {
    await p.goto(`file://${SRC}/serie.html?v=${v}&lang=${LANG}`); await p.waitForTimeout(300);
    const duration = await p.evaluate(() => window.duration);
    const file = `${OUT}/malipin-serie-${v}${LANG === 'en' ? '-en' : ''}.mp4`;
    const ff = spawn('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
      '-i', `${OUT}/serie-${v}.wav`, '-map', '0:v', '-map', '1:a', '-shortest',
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k',
      '-movflags', '+faststart', file]);
    for (let f = 0; f < duration * FPS; f++) {
      await p.evaluate((t) => window.draw(t), f / FPS);
      const buf = await p.screenshot({ type: 'jpeg', quality: 95 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
    console.log('fertig', file.split('/').pop());
  }
  await b.close();
})();
