import { chromium } from '@playwright/test';
import { lookup } from 'node:dns/promises';
import net from 'node:net';
import { readFile, rename, rm } from 'node:fs/promises';
import path from 'node:path';
import { ROOT, sha256, readCards, cardStatus, assertValid, rendererHash, resetDirectory, writeJSON, parseArgs, isMain } from './common.mjs';
import { startServer } from './serve.mjs';

function publicAddress(address) {
  if (net.isIP(address) === 4) {
    const [a, b] = address.split('.').map(Number);
    return !(a === 0 || a === 10 || a === 127 || a >= 224 || (a === 169 && b === 254) || (a === 172 && b >= 16 && b <= 31) || (a === 192 && (b === 168 || b === 0)) || (a === 100 && b >= 64 && b <= 127) || (a === 198 && (b === 18 || b === 19)));
  }
  const text = address.toLowerCase();
  if (text.startsWith('::ffff:')) return publicAddress(text.slice(7));
  return net.isIP(address) === 6 && !(/^(::|fc|fd|fe[89ab]|ff)/.test(text));
}

async function guardNetwork(context, localOrigin) {
  const cache = new Map();
  await context.route('**/*', async route => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.origin === localOrigin) { await route.continue(); return; }
    // External resources are product images only. Credentials, scripts, HTTP,
    // local/private networks and metadata endpoints never leave this renderer.
    if (url.protocol !== 'https:' || request.resourceType() !== 'image' || url.username || url.password) { await route.abort('blockedbyclient'); return; }
    const host = url.hostname.replace(/^\[|\]$/g, '');
    if (!cache.has(host)) cache.set(host, lookup(host, { all: true }).then(values => values.length > 0 && values.every(value => publicAddress(value.address))).catch(() => false));
    if (!await cache.get(host)) { await route.abort('blockedbyclient'); return; }
    await route.continue();
  });
}

export async function inspectLayout(page) {
  return page.evaluate(() => {
    const card = document.querySelector('#card');
    if (!card) return { errors: ['Missing #card element.'] };
    const bounds = card.getBoundingClientRect();
    const errors = [];
    if (Math.abs(bounds.width - 1080) > 0.1 || Math.abs(bounds.height - 1350) > 0.1) errors.push(`Card must be 1080×1350; got ${bounds.width}×${bounds.height}.`);
    if (card.scrollWidth > card.clientWidth + 1 || card.scrollHeight > card.clientHeight + 1) errors.push('Card content overflows the canvas.');
    for (const node of card.querySelectorAll('*')) {
      const style = getComputedStyle(node);
      if (style.display === 'none' || style.visibility === 'hidden' || node.closest('[data-overflow-ignore]')) continue;
      const rectangle = node.getBoundingClientRect();
      if (rectangle.width < 1 || rectangle.height < 1) continue;
      if (rectangle.left < bounds.left - 1 || rectangle.right > bounds.right + 1 || rectangle.top < bounds.top - 1 || rectangle.bottom > bounds.bottom + 1) errors.push(`Element outside card: ${node.tagName}.${node.className?.baseVal ?? node.className}`);
      if (node instanceof HTMLElement && (node.scrollWidth > node.clientWidth + 1 || node.scrollHeight > node.clientHeight + 1)) errors.push(`Clipped content: ${node.tagName}.${node.className}`);
    }
    const faces = [...document.fonts];
    const brandFont = faces.some(face => face.family.replaceAll('"', '').replaceAll("'", '') === 'HotdealSans' && face.status === 'loaded');
    if (!brandFont || !document.fonts.check('700 30px HotdealSans', '핫딜픽')) errors.push('Bundled Korean font did not load.');
    if (faces.some(face => face.status === 'error')) errors.push('A font failed to load.');
    return { errors: [...new Set(errors)], width: bounds.width, height: bounds.height, fontLoaded: brandFont };
  });
}

export async function renderCards({ root = ROOT, data } = {}) {
  const output = await resetDirectory(root, 'rendered');
  const stageName = `.render-stage-${process.pid}-${Date.now()}`;
  const stage = await resetDirectory(root, stageName);
  const report = { ok: false, generatedAt: new Date().toISOString(), canvas: { width: 1080, height: 1350, deviceScaleFactor: 1 }, rendererHash: null, cards: [], errors: [] };
  let browser, app;
  try {
    const cards = await readCards(root, data);
    report.cards = cards.map(card => ({ file: card.file, status: cardStatus(card), sourceHash: card.sourceHash, warnings: card.result.warnings ?? [], errors: card.result.errors ?? [], imageFailures: [] }));
    assertValid(cards);
    report.rendererHash = await rendererHash(root);
    const active = cards.filter(card => cardStatus(card) === 'ready');
    if (active.length) {
      app = await startServer({ root });
      browser = await chromium.launch();
      const context = await browser.newContext({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1, locale: 'ko-KR', timezoneId: 'Asia/Seoul', reducedMotion: 'reduce', serviceWorkers: 'block' });
      await guardNetwork(context, app.url);
      for (const card of active) {
        const page = await context.newPage();
        const entry = report.cards.find(item => item.file === card.file);
        const runtimeErrors = [];
        page.on('pageerror', error => runtimeErrors.push(error.message));
        try {
          await page.goto(`${app.url}/card.html?data=${encodeURIComponent(card.file)}&export=1`, { waitUntil: 'domcontentloaded', timeout: 30000 });
          await page.waitForFunction(() => ['ready', 'invalid', 'error'].includes(window.__CARD_STATE__?.status), null, { timeout: 45000 });
          const state = await page.evaluate(() => window.__CARD_STATE__);
          entry.imageFailures = state.imageFailures ?? [];
          entry.warnings = [...entry.warnings, ...(state.warnings ?? [])].filter((warning, index, all) => all.findIndex(other => JSON.stringify(warning) === JSON.stringify(other)) === index);
          if (state.status !== 'ready') throw new Error(`Card is ${state.status}: ${JSON.stringify(state.errors ?? [])}`);
          await page.evaluate(() => document.fonts.ready);
          const layout = await inspectLayout(page);
          entry.layout = layout;
          if (layout.errors.length || runtimeErrors.length) throw new Error([...layout.errors, ...runtimeErrors].join('\n'));
          const pngName = `${path.basename(card.name, '.json')}.png`;
          const destination = path.join(stage, pngName);
          await page.locator('#card').screenshot({ path: destination, type: 'png', animations: 'disabled', scale: 'css', timeout: 15000 });
          const buffer = await readFile(destination);
          if (buffer.readUInt32BE(16) !== 1080 || buffer.readUInt32BE(20) !== 1350) throw new Error('Saved PNG has incorrect pixel dimensions.');
          entry.png = `rendered/${pngName}`;
          entry.pngHash = sha256(buffer);
          console.log(`RENDERED ${entry.png}${entry.imageFailures.length ? ` (${entry.imageFailures.length} image fallback(s))` : ''}`);
        } catch (error) {
          entry.status = 'error';
          entry.errors.push({ path: card.file, code: 'RENDER_FAILED', message: error.message });
          throw error;
        } finally { await page.close(); }
      }
    }
    report.ok = true;
    await writeJSON(path.join(stage, 'report.json'), report);
    await rm(output, { recursive: true, force: true });
    await rename(stage, output);
    console.log(`Saved ${active.length} PNG(s); ${cards.length - active.length} blank draft(s) skipped.`);
    return report;
  } catch (error) {
    report.errors.push(error.message);
    for (const entry of report.cards) { delete entry.png; delete entry.pngHash; }
    await writeJSON(path.join(output, 'report.json'), report);
    throw error;
  } finally {
    await browser?.close();
    await app?.close();
    await rm(stage, { recursive: true, force: true });
  }
}
if (isMain(import.meta.url)) {
  try { await renderCards(parseArgs(process.argv.slice(2))); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
