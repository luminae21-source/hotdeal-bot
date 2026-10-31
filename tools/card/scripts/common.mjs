import { createHash } from 'node:crypto';
import { readFile, readdir, lstat, realpath, access, mkdir, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { validateCard } from '../assets/validation.mjs';

export const ROOT = fileURLToPath(new URL('../', import.meta.url));
export const sha256 = value => createHash('sha256').update(value).digest('hex');
export function isCardPNG(buffer) {
  return buffer.length > 24 && buffer.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])) && buffer.toString('ascii', 12, 16) === 'IHDR' && buffer.readUInt32BE(16) === 1080 && buffer.readUInt32BE(20) === 1350;
}
export const slash = value => value.split(path.sep).join('/');
export const isMain = moduleUrl => Boolean(process.argv[1]) && pathToFileURL(path.resolve(process.argv[1])).href === moduleUrl;
export async function exists(file) { try { await access(file); return true; } catch { return false; } }
export function inside(root, candidate) {
  const relative = path.relative(path.resolve(root), path.resolve(candidate));
  return relative !== '' && !relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative);
}
export async function resetDirectory(root, name) {
  const target = path.resolve(root, name);
  if (!inside(root, target) || name.includes('/') || name.includes('\\')) throw new Error('Unsafe output directory.');
  // Remove the named output itself, never follow a symlink outside the project.
  await rm(target, { recursive: true, force: true });
  await mkdir(target, { recursive: true });
  return target;
}
export async function writeJSON(file, value) { await writeFile(file, `${JSON.stringify(value, null, 2)}\n`, 'utf8'); }

export function parseArgs(args, allowed = ['data']) {
  const result = {};
  for (let i = 0; i < args.length; i++) {
    const key = args[i].replace(/^--/, '');
    if (!args[i].startsWith('--') || !allowed.includes(key) || !args[i + 1] || args[i + 1].startsWith('--')) {
      throw new Error(`Unknown or incomplete option: ${args[i]}`);
    }
    if (Object.hasOwn(result, key)) throw new Error(`Duplicate option: --${key}`);
    result[key] = args[++i];
  }
  return result;
}

export async function readCards(root = ROOT, selected) {
  const directory = path.join(root, 'data');
  if (!await exists(directory)) throw new Error('data/ directory is missing.');
  const entries = await readdir(directory, { withFileTypes: true });
  let files = entries.filter(entry => entry.name.toLowerCase().endsWith('.json')).map(entry => entry.name).sort();
  if (selected) {
    const normalized = selected.replaceAll('\\', '/').replace(/^\.\//, '');
    if (!/^data\/[A-Za-z0-9_-]+\.json$/.test(normalized)) {
      throw new Error('--data must name one JSON file directly inside data/, using English letters, digits, - or _, e.g. data/coupang.json');
    }
    const name = normalized.slice(5);
    if (!files.includes(name)) throw new Error(`Data file not found: ${normalized}`);
    files = [name];
  }
  const cards = [];
  for (const name of files) {
    const file = `data/${name}`;
    const absolute = path.join(directory, name);
    try {
      if (!/^[A-Za-z0-9_-]+\.json$/.test(name)) throw new Error('JSON filenames must use only English letters, digits, - or _, ending in lowercase .json.');
      const metadata = await lstat(absolute);
      if (!metadata.isFile() || metadata.isSymbolicLink()) throw new Error('Data files must be regular files, not links.');
      if (metadata.size > 1024 * 1024) throw new Error('JSON exceeds the 1 MiB file limit.');
      if (!inside(await realpath(root), await realpath(absolute))) throw new Error('Data file is outside the project.');
      const raw = await readFile(absolute, 'utf8');
      const input = JSON.parse(raw.replace(/^\uFEFF/, ''));
      const result = validateCard(input);
      cards.push({ file, name, input, sourceHash: sha256(raw), result });
    } catch (error) {
      cards.push({ file, name, result: { ok: false, draft: false, errors: [{ path: file, code: 'JSON_FILE', message: error.message }], warnings: [] } });
    }
  }
  return cards;
}

export function cardStatus(card) {
  if (card.result.draft && !(card.result.errors?.length)) return 'draft';
  return card.result.ok ? 'ready' : 'invalid';
}
export function assertValid(cards) {
  const invalid = cards.filter(card => cardStatus(card) === 'invalid');
  if (invalid.length) {
    throw new Error(invalid.map(card => `${card.file}:\n${(card.result.errors ?? []).map(error => `  ${error.path}: ${error.message}`).join('\n')}`).join('\n'));
  }
}

export async function rendererHash(root = ROOT) {
  const files = [];
  async function walk(relative) {
    const absolute = path.join(root, relative);
    const item = await lstat(absolute);
    if (item.isSymbolicLink()) throw new Error(`Symlink is not allowed in public assets: ${relative}`);
    if (item.isDirectory()) {
      for (const name of (await readdir(absolute)).sort()) {
        if (!name.startsWith('.')) await walk(path.join(relative, name));
      }
    } else if (item.isFile()) files.push(relative);
  }
  await walk('card.html');
  await walk('assets');
  const hash = createHash('sha256');
  for (const relative of files) hash.update(slash(relative)).update('\0').update(await readFile(path.join(root, relative))).update('\0');
  return hash.digest('hex');
}

export async function readReport(root = ROOT) {
  try { return JSON.parse(await readFile(path.join(root, 'rendered', 'report.json'), 'utf8')); }
  catch { return null; }
}
export async function createManifest(root = ROOT, { strict = false, cards: providedCards } = {}) {
  const cards = providedCards ?? await readCards(root);
  if (strict) assertValid(cards);
  const report = await readReport(root);
  const currentRenderer = report ? await rendererHash(root) : null;
  const manifest = { cards: [] };
  for (const card of cards) {
    const status = cardStatus(card);
    if (status === 'invalid') continue;
    const data = card.result.data ?? card.input;
    const entry = { file: card.file, mall: data.mall, title: data.title, checked: data.checked, status };
    const rendered = report?.cards?.find(item => item.file === card.file && item.status === 'ready');
    const png = `rendered/${path.basename(card.name, '.json')}.png`;
    if (status === 'ready' && report?.ok && report.rendererHash === currentRenderer && rendered?.sourceHash === card.sourceHash && rendered?.png === png) {
      try {
        const image = await readFile(path.join(root, png));
        if (isCardPNG(image) && sha256(image) === rendered.pngHash) entry.png = png;
      } catch { /* Local previews can have no saved PNG yet. */ }
    }
    if (strict && status === 'ready' && !entry.png) throw new Error(`${card.file}: saved PNG is missing or stale. Run npm run render before npm run build.`);
    manifest.cards.push(entry);
  }
  return manifest;
}
