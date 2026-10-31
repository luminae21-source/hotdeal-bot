import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve, extname, sep } from 'node:path';
import { mkdir } from 'node:fs/promises';
const root=process.cwd();const data=process.argv[2];const output=process.argv[3]||'output/card.png';
if(!data||!/^([a-zA-Z0-9_-]+\/)*[a-zA-Z0-9_-]+\.json$/.test(data))throw Error('Usage: node scripts/render.mjs data/coupang_1101.json output/card.png');
const server=createServer(async(req,res)=>{try{const p=decodeURIComponent(new URL(req.url,'http://localhost').pathname).replace(/^\//,'');const full=resolve(root,p||'card.html');if(full!==root&&!full.startsWith(root+sep))throw Error('Invalid path');const bytes=await readFile(full);res.setHeader('Content-Type',extname(full)==='.json'?'application/json':extname(full)==='.html'?'text/html; charset=utf-8':'application/octet-stream');res.end(bytes)}catch(e){res.statusCode=404;res.end('Not found')}});
await new Promise(ok=>server.listen(0,'127.0.0.1',ok));const port=server.address().port;const browser=await chromium.launch({headless:true,...(process.env.PW_CHROME?{executablePath:process.env.PW_CHROME}:{})});try{const page=await browser.newPage({viewport:{width:1080,height:1350},deviceScaleFactor:1});await page.goto(`http://127.0.0.1:${port}/card.html?data=${encodeURIComponent(data)}`);await page.waitForFunction(()=>['ok','error'].includes(document.documentElement.dataset.ready),{timeout:15000});if(await page.locator('html').getAttribute('data-ready')!=='ok')throw Error('카드 검증 실패: '+await page.locator('.error').innerText());await mkdir(resolve(root,output,'..'),{recursive:true});await page.locator('#card').screenshot({path:output});console.log('Rendered:',output)}finally{await browser.close();server.close()}
