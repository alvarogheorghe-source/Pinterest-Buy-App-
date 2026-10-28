const { chromium } = require('playwright');
const { spawn } = require('child_process');
const D = process.argv[2], LANG = process.argv[3] || 'de', FPS = 30;   // node render.js <ordner> [de|en]
const names = LANG === 'en'
  ? { 1: 'malipin-tiktok-1-which-vibe-en', 2: 'malipin-tiktok-2-pinterest-shop-en', 3: 'malipin-tiktok-3-screenshot-en' }
  : { 1: 'malipin-tiktok-1-welcher-vibe', 2: 'malipin-tiktok-2-pinterest-shop', 3: 'malipin-tiktok-3-screenshot' };
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  for (const v of [1, 2, 3]) {
    await p.goto(`file://${D}/video.html?v=${v}&lang=${LANG}`); await p.waitForTimeout(400);
    const duration = await p.evaluate(() => window.duration);
    const ff = spawn('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
      '-i', `${D}/sound-${v}.wav`, '-map', '0:v', '-map', '1:a', '-shortest',
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart',
      `${D}/${names[v]}.mp4`]);
    for (let f = 0; f < duration * FPS; f++) {
      await p.evaluate((t) => window.draw(t), f / FPS);
      const buf = await p.screenshot({ type: 'jpeg', quality: 95 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
    console.log('fertig', names[v]);
  }
  await b.close();
})();
