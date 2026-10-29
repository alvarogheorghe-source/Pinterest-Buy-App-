// Eine Animations-Seite + WAV -> MP4.
// node render_page.js <ordner mit seite> <ausgabe-ordner> <seite.html> <ton.wav> <name> [de|en]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const [SRC, OUT, PAGE, WAV, NAME, LANG = 'de'] = process.argv.slice(2), FPS = 30;
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto(`file://${SRC}/${PAGE}?lang=${LANG}`); await p.waitForTimeout(400);
  const duration = await p.evaluate(() => window.duration);
  const file = `${OUT}/${NAME}${LANG === 'en' ? '-en' : ''}.mp4`;
  const ff = spawn('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-i', `${OUT}/${WAV}`, '-map', '0:v', '-map', '1:a', '-shortest',
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
  await b.close();
})();
