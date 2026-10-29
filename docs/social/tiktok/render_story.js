// story.html + story-sound.wav -> MP4.  node render_story.js <ordner mit story.html> <ausgabe-ordner> [de|en]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const [SRC, OUT, LANG = 'de'] = process.argv.slice(2), FPS = 30;
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto(`file://${SRC}/story.html?lang=${LANG}`); await p.waitForTimeout(400);
  const duration = await p.evaluate(() => window.duration);
  const name = LANG === 'en' ? 'malipin-tiktok-4-every-night-en' : 'malipin-tiktok-4-jeden-abend';
  const ff = spawn('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-i', `${OUT}/story-sound.wav`, '-map', '0:v', '-map', '1:a', '-shortest',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k',
    '-movflags', '+faststart', `${OUT}/${name}.mp4`]);
  for (let f = 0; f < duration * FPS; f++) {
    await p.evaluate((t) => window.draw(t), f / FPS);
    const buf = await p.screenshot({ type: 'jpeg', quality: 95 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  console.log('fertig', name);
  await b.close();
})();
