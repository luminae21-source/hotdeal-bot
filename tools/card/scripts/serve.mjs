import http from 'node:http';
import { readFile, lstat, realpath } from 'node:fs/promises';
import path from 'node:path';
import { ROOT, inside, createManifest, isMain, parseArgs } from './common.mjs';

const MIME = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.gif': 'image/gif', '.woff2': 'font/woff2', '.txt': 'text/plain; charset=utf-8' };
const publicPath = name => ['index.html', 'card.html', 'manifest.json'].includes(name) || /^(assets|data|rendered)\//.test(name);

export async function startServer({ root = ROOT, port = 0 } = {}) {
  const base = await realpath(path.resolve(root));
  const server = http.createServer(async (request, response) => {
    const send = (status, message, type = 'text/plain; charset=utf-8') => {
      response.writeHead(status, { 'Content-Type': type, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
      response.end(request.method === 'HEAD' ? undefined : message);
    };
    try {
      if (!['GET', 'HEAD'].includes(request.method)) { send(405, 'Method not allowed'); return; }
      let pathname;
      try { pathname = decodeURIComponent((request.url ?? '/').split(/[?#]/, 1)[0]); }
      catch { send(400, 'Invalid URL'); return; }
      if (!pathname.startsWith('/') || pathname.includes('\\') || pathname.includes('\0') || pathname.includes(':')) { send(400, 'Invalid path'); return; }
      const parts = pathname.split('/').slice(1);
      if (parts.some(part => part.startsWith('.'))) { send(403, 'Forbidden'); return; }
      const relative = pathname === '/' ? 'index.html' : pathname.slice(1);
      if (!publicPath(relative)) { send(404, 'Not found'); return; }
      if (relative === 'manifest.json') {
        // A built site has an immutable manifest. Development gets fresh entries.
        try {
          const target = path.join(base, 'manifest.json');
          const metadata = await lstat(target);
          if (!metadata.isFile() || metadata.isSymbolicLink() || !inside(base, await realpath(target))) { send(403, 'Forbidden'); return; }
          const saved = await readFile(target, 'utf8');
          send(200, saved, MIME['.json']);
        } catch (error) {
          if (error.code !== 'ENOENT') throw error;
          send(200, JSON.stringify(await createManifest(base)), MIME['.json']);
        }
        return;
      }
      const target = path.resolve(base, relative);
      if (!inside(base, target)) { send(403, 'Forbidden'); return; }
      const canonical = await realpath(target);
      if (!inside(base, canonical)) { send(403, 'Forbidden'); return; }
      const metadata = await lstat(target);
      if (!metadata.isFile() || metadata.isSymbolicLink()) { send(404, 'Not found'); return; }
      send(200, await readFile(target), MIME[path.extname(target).toLowerCase()] ?? 'application/octet-stream');
    } catch (error) {
      send(error.code === 'ENOENT' || error.code === 'ENOTDIR' ? 404 : 500, error.code === 'ENOENT' || error.code === 'ENOTDIR' ? 'Not found' : 'Unable to serve this resource');
    }
  });
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(port, '127.0.0.1', resolve); });
  const address = server.address();
  return { server, url: `http://127.0.0.1:${address.port}`, close: () => new Promise((resolve, reject) => { server.close(error => error ? reject(error) : resolve()); server.closeIdleConnections?.(); }) };
}

if (isMain(import.meta.url)) {
  try {
    const options = parseArgs(process.argv.slice(2), ['port', 'root']);
    const port = Number(options.port ?? process.env.PORT ?? 4173);
    if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error('Port must be an integer from 0 to 65535.');
    const app = await startServer({ root: options.root ? path.resolve(options.root) : ROOT, port });
    console.log(`Hotdealpick: ${app.url}`);
    for (const signal of ['SIGINT', 'SIGTERM']) process.once(signal, async () => { await app.close(); process.exit(0); });
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
