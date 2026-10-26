// 웹앱(PWA) 셀프체크: node test_pwa.js  (docs/를 로컬 서버로 띄워 Playwright 크로미움으로 확인 — build_site.py 먼저)
// manifest 필드·아이콘 크기·서비스워커 등록·설치 가능(크롬 DevTools getInstallabilityErrors = 0)·오프라인(저장해 둔 홈)·설치 버튼(안드로이드·아이폰·앱 안 브라우저·설치됨·닫기 7일)
// · GoatCounter 웹앱 출처('app') · 지금 사이트 동작(탭·찜·검색) · 휴대폰 3종(360·393·412) 일반·앱 첫 화면 + 아이콘 48px -> docs/cards/pwa_preview.png 한 장. 마지막 줄 'OK: 웹앱 셀프체크 통과'
const http = require('http'), fs = require('fs'), path = require('path'), assert = require('assert');
const { chromium } = require('playwright');
const ROOT = path.join(__dirname, 'docs');
const MIME = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.woff2': 'font/woff2', '.js': 'text/javascript', '.webmanifest': 'application/manifest+json', '.png': 'image/png', '.jpg': 'image/jpeg', '.ico': 'image/x-icon', '.json': 'application/json', '.xml': 'application/xml' };
let OFF = false;  // true = 서버가 끊김(진짜 오프라인 — Playwright setOffline은 서비스워커 요청은 안 막음, 10/23 리뷰)
const server = http.createServer((q, s) => {  // GitHub Pages처럼: / -> index.html, 쿼리 무시
  if (OFF) return q.socket.destroy();
  let f = path.join(ROOT, decodeURIComponent(new URL(q.url, 'http://x').pathname));
  if (f.endsWith('/')) f += 'index.html';
  fs.readFile(f, (e, b) => { if (e) { s.writeHead(404); return s.end('404'); } s.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' }); s.end(b); });
});
const IOS = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1';
const IG = IOS.replace('Safari/604.1', 'Instagram 350.0.0.0');
const STANDALONE = () => { const m = window.matchMedia.bind(window); window.matchMedia = q => /display-mode:\s*standalone/.test(q) ? { matches: true, media: q, addEventListener() {}, addListener() {} } : m(q); };

(async () => {
  await new Promise(r => server.listen(8765, '127.0.0.1', r));
  const U = 'http://127.0.0.1:8765';
  const browser = await chromium.launch();
  const NC = browser.newContext.bind(browser), LAY = l => { try { if (!localStorage.getItem('hp_layout')) localStorage.setItem('hp_layout', l); } catch (e) {} };
  browser.newContext = async (o, l = 'b') => { const c = await NC(o); if (l) await c.addInitScript(LAY, l); return c; };  // 기존 확인 = 아이콘형(B) · 목록형(A)·첫 방문 무작위·저장소 막힘 = 7) 화면 고르기
  const nudge = p => p.evaluate(() => new Promise(r => { scrollBy(0, 1); setTimeout(r, 80); }));  // 홈 설치 띠 = 처음 밀 때(첫 화면 🔥 줄 안 가림)
  try {
    // 1) manifest·아이콘·서비스워커·설치 가능
    const ctx = await browser.newContext({ viewport: { width: 412, height: 915 } });
    const pg = await ctx.newPage();
    await pg.goto(U + '/?src=app', { waitUntil: 'load' });
    const m = JSON.parse(fs.readFileSync(path.join(ROOT, 'manifest.webmanifest'), 'utf8'));
    assert.deepStrictEqual([m.name, m.short_name, m.start_url, m.scope, m.display, m.lang, m.background_color, m.theme_color], ['핫딜픽 — 매일 살 만한 핫딜', '핫딜픽', '/?src=app', '/', 'standalone', 'ko', '#F6F7F9', '#F6F7F9']);
    assert.deepStrictEqual(m.shortcuts.map(s => s.url), ['/#fire', '/#wait', '/#life']);
    for (const i of [...m.icons, ...m.shortcuts.flatMap(s => s.icons)]) {  // 바로가기 아이콘(🔥·⏳·🧻)도 선언한 크기로 열림
      const [w, h] = await pg.evaluate(src => new Promise(ok => { const im = new Image(); im.onload = () => ok([im.naturalWidth, im.naturalHeight]); im.src = src; }), i.src);
      assert.strictEqual(`${w}x${h}`, i.sizes, i.src);
    }
    assert.deepStrictEqual(m.icons.map(i => i.purpose).sort(), ['any', 'any', 'maskable']);
    for (const [src, n] of [['/icons/apple-touch-icon.png', 180], ['/icons/favicon-32.png', 32], ['/icons/favicon-16.png', 16]])
      assert.strictEqual(await pg.evaluate(s => new Promise(ok => { const im = new Image(); im.onload = () => ok(im.naturalWidth); im.src = s; }), src), n, src);
    const head = await pg.evaluate(() => ['link[rel=manifest]', 'link[rel=apple-touch-icon]', 'link[rel=icon]', 'meta[name=theme-color]', 'meta[name=apple-mobile-web-app-capable]', 'meta[name=apple-mobile-web-app-title]', 'meta[name=apple-mobile-web-app-status-bar-style]'].map(s => !!document.querySelector(s)));
    assert.ok(head.every(Boolean), 'head ' + head);
    const active = await pg.evaluate(() => navigator.serviceWorker.ready.then(r => r.active && r.active.scriptURL));
    assert.ok(active.endsWith('/sw.js'), 'sw ' + active);
    const cdp = await ctx.newCDPSession(pg);
    const inst = await cdp.send('Page.getInstallabilityErrors');
    assert.deepStrictEqual(inst.installabilityErrors, [], JSON.stringify(inst));  // 크롬이 보는 설치 가능 조건(manifest·아이콘·서비스워커·HTTPS/로컬) 다 맞음
    const am = await cdp.send('Page.getAppManifest');
    assert.ok(!am.errors.length, JSON.stringify(am.errors));
    // 2) 서비스워커: 같은 출처만 · 오프라인이면 저장해 둔 홈
    await pg.reload({ waitUntil: 'load' });
    assert.ok(await pg.evaluate(() => !!navigator.serviceWorker.controller));
    OFF = true;  // 서버 끊김: 홈 = 저장해 둔 홈, 처음 여는 딜 페이지 = 저장해 둔 홈으로(빈 화면 X)
    await pg.goto(U + '/', { waitUntil: 'load' });
    assert.ok((await pg.title()).includes('핫딜픽') && (await pg.$('#fire')), '오프라인 홈');
    const p0 = fs.readdirSync(path.join(ROOT, 'p')).find(f => f.endsWith('.html'));
    await pg.goto(U + '/p/' + p0, { waitUntil: 'load' });
    assert.ok((await pg.title()).includes('오늘의 핫딜'), '오프라인 처음 여는 쪽 = 저장해 둔 홈');
    OFF = false;
    // 3) 지금 사이트 동작(10/24 개편): 아래 메뉴 5개 · 찜(localStorage -> /saved/) · 검색(search.json = 진열 상품 전부, 🔥 먼저) · 옛 홈 #칸 주소(웹앱 바로가기 #wait·#life) -> 새 쪽
    await pg.goto(U + '/', { waitUntil: 'load' });
    assert.deepStrictEqual(await pg.evaluate(() => [...document.querySelectorAll('nav.nav a')].map(a => a.textContent.trim())), ['홈', '특가', '카테고리', '찜', '알림']);
    const lk = await pg.$('#pick .like, #steady .like');  // 10/24 포털형: 🔥 실시간 핫딜 = 목록형 줄(♡ X) — 가로 카드(오늘의 픽·꾸준템)에 ♡
    await lk.click();
    assert.strictEqual(await pg.evaluate(() => JSON.parse(localStorage.getItem('likes')).length), 1, '찜 1개');
    assert.strictEqual(await lk.getAttribute('aria-pressed'), 'true');
    assert.strictEqual(await pg.textContent('#lc'), ' 1', '아래 메뉴 찜 숫자(헤더 ♡ X — 포털형 헤더 1줄)');
    await pg.goto(U + '/saved/', { waitUntil: 'load' });
    assert.ok(await pg.evaluate(() => document.querySelectorAll('#savedg .g').length === 1 && document.getElementById('saved0').hidden), '찜 쪽');
    await pg.goto(U + '/', { waitUntil: 'load' });
    await pg.fill('#q', '화장지');
    await pg.waitForFunction(() => document.getElementById('qn'));
    const ix = JSON.parse(fs.readFileSync(path.join(ROOT, 'search.json'), 'utf8')).filter(x => x.k.includes('화장지'));
    const fd = await pg.evaluate(() => { const g = [...document.querySelectorAll('#sr .g')]; return { line: document.getElementById('qn').textContent, ids: g.map(x => x.querySelector('.like').dataset.i), seen: g.every(x => x.textContent.includes('화장지')),
                                                                     hid: document.getElementById('fire').hidden, liked: g.filter(x => x.querySelector('.like').getAttribute('aria-pressed') === 'true').length }; });
    assert.ok(ix.length > 0 && fd.line === ix.length + '개 찾았어요' && fd.ids.join() === ix.slice(0, 60).map(x => String(x.i)).join() && fd.seen && fd.hid, '검색 = 진열 상품 전부(색인 순서 = 🔥 먼저) ' + JSON.stringify([fd, ix.length]));
    await pg.fill('#q', ''); await pg.waitForTimeout(300);
    assert.ok(await pg.evaluate(() => !document.getElementById('sr') && !document.getElementById('fire').hidden), '검색 지우면 그대로');
    for (const [h, to] of [['#wait', '/c/wait/'], ['#life', '/c/life/'], ['#toss', '/c/toss/']]) {
      await pg.goto(U + '/' + h, { waitUntil: 'load' }); await pg.waitForURL(u => new URL(u).pathname === to, { timeout: 5000 });
    }
    await pg.goto(U + '/#fire', { waitUntil: 'load' }); await pg.waitForTimeout(200); assert.strictEqual(new URL(pg.url()).pathname, '/', '#fire = 홈 그대로');
    // 4) GoatCounter 웹앱 출처: ?src=app = 'app', 경로는 ?src 뺌
    const gc = await pg.evaluate(js => { eval(js); return [window.goatcounter.path('/?src=app'), window.goatcounter.path('/?src=app&x=1'), window.goatcounter.path('/p/1.html')]; }, require('child_process').execSync("python3 -c \"import build_site; print(build_site.GC_APP)\"").toString());
    assert.deepStrictEqual(gc, ['/', '/?x=1', '/p/1.html']);
    const ref = await pg.evaluate(js => { history.replaceState(null, '', '/?src=app'); eval(js); return window.goatcounter.referrer('https://www.instagram.com/'); }, require('child_process').execSync("python3 -c \"import build_site; print(build_site.GC_APP)\"").toString());
    assert.strictEqual(ref, 'app');
    // GoatCounter 실제 태그(10/23 hotdealpick): 바깥 count.js는 서비스워커가 안 막음(가짜 count.js가 실행됨) · 구매 링크 클릭 = 이벤트 buy/몰 주소+경로(10/24 E — 상품마다, 쿼리 X) · ?ref=th 출처는 그대로('app'으로 안 바꿈 — count.js가 location.search를 보냄)
    await ctx.route(/\/\/gc\.zgo\.at\/count\.js/, r => r.fulfill({ contentType: 'text/javascript', body: 'window.__gcl=1;goatcounter.count=function(v){(window.__gc=window.__gc||[]).push(v)}' }));
    await pg.goto(U + '/?ref=th', { waitUntil: 'load' });
    await pg.waitForFunction(() => window.__gcl === 1 && navigator.serviceWorker.controller);
    assert.strictEqual(await pg.getAttribute('script[data-goatcounter]', 'data-goatcounter'), 'https://hotdealpick.goatcounter.com/count');
    assert.strictEqual(await pg.evaluate(() => goatcounter.referrer('https://www.threads.net/')), 'https://www.threads.net/');
    const buy = await pg.evaluate(() => { const a = document.querySelector('a[rel~="nofollow"][href^="http"]:not([data-gc^="promo/"])'); a.addEventListener('click', e => e.preventDefault()); a.click(); const u = new URL(a.href); return [u.hostname + u.pathname, window.__gc, u.search]; });
    assert.ok(buy[1] && buy[1].some(v => v.event === true && v.path === 'buy/' + buy[0]) && buy[0].includes('/') && !buy[1].some(v => buy[2] && v.path.includes(buy[2])), JSON.stringify(buy));
    const bn = await pg.evaluate(() => { const a = document.createElement('a'); a.href = '#ev'; a.dataset.ev = 'e1a2b3c'; a.textContent = '배너'; document.querySelector('main').append(a); a.click(); a.remove(); return window.__gc; });
    assert.ok(bn.some(v => v.event === true && v.path === 'banner/e1a2b3c'), JSON.stringify(bn));  // 기획전 배너 클릭 = 이벤트 banner/행사(10/24 Cowork — 1주 보고 팝업 여부)
    const gcm = await pg.evaluate(() => { window.__gc = []; const a = document.querySelector('.qk [data-gc="mall/coupang"]'); a.addEventListener('click', e => e.preventDefault()); a.click(); return [a.dataset.gc, window.__gc]; });
    assert.ok(gcm[0] === 'mall/coupang' && gcm[1].some(v => v.event === true && v.path === 'mall/coupang'), JSON.stringify(gcm));  // 칸별 클릭 data-gc(mall/·top/·deadline/·drop/·changes/)
    // 3b) 포털형 홈·몰 쪽·변경 찾기(10/24 Cowork): 🔥 탭 · 몰 쪽 품목 칩·상태 탭·20개씩 더 보기 · 찜 변경 배지·요약 · 🔔 빨간 점 → 알림 탭 보면 꺼짐(changes.json = 가짜로)
    const c5 = await browser.newContext({ viewport: { width: 390, height: 844 }, serviceWorkers: 'block' }), p5 = await c5.newPage();
    await p5.goto(U + '/', { waitUntil: 'load' });
    const tb = await p5.$('#fire [data-t]:not([data-t="all"])'), tk = await tb.getAttribute('data-t'); await tb.click();
    assert.ok(await p5.evaluate(k => [...document.querySelectorAll('#fire .rows')].every(o => o.hidden === (o.dataset.p !== k)) && document.querySelector('#fire [data-t="' + k + '"]').getAttribute('aria-selected') === 'true', tk), '🔥 탭 ' + tk);
    await p5.goto(U + '/c/coupang/', { waitUntil: 'load' });
    const vis = () => p5.evaluate(() => [...document.querySelectorAll('#mg > .g')].filter(e => !e.hidden).map(e => [e.dataset.c, e.dataset.s]));
    let v5 = await vis(); const all5 = await p5.evaluate(() => document.querySelectorAll('#mg > .g').length);
    assert.ok(v5.length === Math.min(20, all5) && (all5 <= 20) === (await p5.evaluate(() => document.getElementById('mm').hidden)), '몰 쪽 20개 + 더 보기 ' + [v5.length, all5]);
    if (all5 > 20) { await p5.click('#mm'); assert.strictEqual((await vis()).length, Math.min(40, all5), '더 보기 = 20개 더'); }
    const cb = await p5.$('.mf [data-c]:not([data-c=""])'), cc = await cb.getAttribute('data-c'); await cb.click(); v5 = await vis();
    assert.ok(v5.length > 0 && v5.every(x => x[0] === cc), '품목 칩 ' + cc);
    await p5.click('[role=tab][data-s="h"]'); v5 = await vis();
    assert.ok(v5.every(x => x[0] === cc && x[1].split(' ').includes('h')), '상태 탭 🔥 + 품목');
    await p5.goto(U + '/c/coupang/?s=h', { waitUntil: 'load' });
    assert.ok(await p5.evaluate(() => document.querySelector('[role=tab][data-s="h"]').getAttribute('aria-selected') === 'true' && [...document.querySelectorAll('#mg > .g')].filter(e => !e.hidden).every(e => e.dataset.s.split(' ').includes('h'))), '?s=h = 🔥 탭(특가 쪽 몰 칩)');
    const li5 = await p5.evaluate(() => { const g = document.querySelector('#mg > .g'); return [g.querySelector('.like').dataset.i, g.outerHTML]; });
    const D5 = Math.floor(Date.now() / 1000) - 60;  // 바뀐 때 = 지금보다 1분 전(알림 탭 본 뒤엔 점 X)
    await c5.route('**/changes.json', r => r.fulfill({ contentType: 'application/json', body: JSON.stringify({ at: '', n: {}, a: { [li5[0]]: '99999' }, items: { 99999: { m: 'coupang', n: 'x', r: '10,000원', c: '8,000원', t: '10/24 10시', k: ['drop'], d: D5, p: 20 } } }) }));
    await p5.evaluate(h => localStorage.setItem('likes', JSON.stringify([{ i: h[0], h: h[1] }])), li5);
    await p5.goto(U + '/saved/', { waitUntil: 'load' }); await p5.waitForFunction(() => document.querySelector('#savedg .chg'));
    assert.ok(await p5.evaluate(() => document.querySelector('#savedg .chg').textContent === '▼ 20% 내림 · 10/24 확인' && !document.getElementById('chgsum').hidden && document.getElementById('chgsum').textContent.includes('가격 내려간 1개') && !document.getElementById('savn').hidden), '찜 변경 배지·요약(옛 글 번호 = a로 지금 글)');
    await p5.goto(U + '/', { waitUntil: 'load' }); await p5.waitForFunction(() => !document.getElementById('adot').hidden, null, { timeout: 5000 });
    await p5.waitForFunction(() => !document.getElementById('my').hidden && document.querySelector('#myr .mi b'), null, { timeout: 5000 });
    assert.ok(await p5.evaluate(() => { const a = [...document.querySelectorAll('#myr .mi')]; return a[0].classList.contains('me') && a[0].getAttribute('href') === '/saved/' && a[1].getAttribute('href') === '/p/99999.html' && a[1].querySelector('b.d').textContent === '▼20%' && a[1].querySelector('.im'); }), '♡ 내가 찜·본 딜 = MY(찜 전체) + 바뀐 찜 먼저(▼N% 초록 · 옛 글 번호 = 지금 글)');
    const pd5 = await p5.evaluate(k => [...document.querySelectorAll('#fire .r a')].map(a => new URL(a.getAttribute('href')).pathname).find(p => p !== '/p/' + k + '.html'), li5[0]);  // 찜과 다른 딜(같은 상품 = 1번만)
    await p5.goto(U + pd5, { waitUntil: 'load' }); assert.ok(await p5.evaluate(() => (JSON.parse(localStorage.getItem('seen')) || []).length === 1), '딜 쪽 = 본 기록(seen)');
    await p5.goto(U + '/', { waitUntil: 'load' }); await p5.waitForTimeout(300);
    assert.ok(await p5.evaluate(h => [...document.querySelectorAll('#myr .mi')].some(e => h.endsWith(e.getAttribute('href'))), pd5), '본 딜도 ♡ 줄에');
    await p5.goto(U + '/alarm/', { waitUntil: 'load' }); await p5.waitForFunction(() => document.getElementById('chgn').textContent === '1');
    assert.ok(await p5.evaluate(() => +localStorage.getItem('chgseen') > 0 && document.getElementById('adot').hidden), '알림 탭 = 내 찜 변경 1 · 본 시각');
    await p5.evaluate(() => sessionStorage.clear()); await p5.goto(U + '/', { waitUntil: 'load' }); await p5.waitForTimeout(500);
    assert.ok(await p5.evaluate(() => document.getElementById('adot').hidden), '본 뒤 = 빨간 점 X');
    await c5.addInitScript(() => { Object.defineProperty(window, 'localStorage', { get() { throw new Error('blocked'); } }); });
    const p6 = await c5.newPage(); const err6 = []; p6.on('pageerror', e => err6.push(String(e)));
    for (const u of ['/', '/saved/', '/alarm/', '/c/coupang/', '/p/' + p0]) await p6.goto(U + u, { waitUntil: 'load' });
    assert.deepStrictEqual(err6, [], '저장소 막힘에도 스크립트 오류 X');
    await c5.close();
    await ctx.close();
    // 5) 설치 버튼: 안드로이드 크롬 = beforeinstallprompt -> 설치 / 아이폰 = 2줄 안내 / 앱 안 브라우저 = 브라우저 안내 / 설치됨 = 숨김 / 닫기 = 7일
    const V2 = () => { try { if (!localStorage.getItem('hv')) localStorage.setItem('hv', '1'); } catch (e) {} };  // 두 번째 방문(10/24 Cowork: 첫 방문엔 띠 X)
    const show = async (opt, init, fire) => {
      const c = await browser.newContext(opt), p = await c.newPage();
      await p.addInitScript(V2);
      if (init) await p.addInitScript(init);
      await p.goto(U + '/', { waitUntil: 'load' });
      if (fire) await p.evaluate(() => { const e = new Event('beforeinstallprompt'); e.prompt = () => { window.__prompted = 1; }; e.userChoice = Promise.resolve({ outcome: 'accepted' }); dispatchEvent(e); });
      await nudge(p);
      const r = await p.evaluate(() => ({ shown: !document.getElementById('inst').hidden, text: document.getElementById('instt').textContent, btn: !document.getElementById('instb').hidden }));
      return [r, c, p];
    };
    const c0 = await browser.newContext({ viewport: { width: 412, height: 915 } }), p0a = await c0.newPage();  // 첫 방문 = 띠 X, 같은 탭 새로 고침도 X(세션 1번), 새 탭(두 번째 방문) = 보임
    const fire0 = () => p0a.evaluate(() => { const e = new Event('beforeinstallprompt'); e.prompt = () => {}; e.userChoice = Promise.resolve({}); dispatchEvent(e); });
    await p0a.goto(U + '/', { waitUntil: 'load' }); await fire0(); await nudge(p0a);
    assert.ok(await p0a.evaluate(() => document.getElementById('inst').hidden), '첫 방문 = 설치 띠 X');
    await p0a.reload({ waitUntil: 'load' }); await fire0(); await nudge(p0a);
    assert.ok(await p0a.evaluate(() => document.getElementById('inst').hidden), '같은 방문(새로 고침) = 띠 X');
    const p0b = await c0.newPage(); await p0b.goto(U + '/', { waitUntil: 'load' });
    await p0b.evaluate(() => { const e = new Event('beforeinstallprompt'); e.prompt = () => {}; e.userChoice = Promise.resolve({}); dispatchEvent(e); });
    assert.ok(await p0b.evaluate(() => document.getElementById('inst').hidden), '홈 첫 화면 = 띠 X(처음 밀 때 — 🔥 줄 안 가림)'); await nudge(p0b);
    assert.ok(await p0b.evaluate(() => !document.getElementById('inst').hidden && +localStorage.getItem('hv') === 2), '두 번째 방문 = 띠');
    await c0.close();
    let [r, c, p] = await show({ viewport: { width: 412, height: 915 } }, null, true);
    assert.ok(r.shown && r.btn && r.text.includes('홈 화면') && (await p.textContent('#instb')) === '📲 앱으로 설치', JSON.stringify(r));
    await p.click('#instb'); await p.waitForTimeout(100);
    assert.ok(await p.evaluate(() => window.__prompted === 1 && document.getElementById('inst').hidden), '설치 창');
    await c.close();
    [r, c, p] = await show({ viewport: { width: 390, height: 844 }, userAgent: IOS });
    assert.ok(r.shown && !r.btn && r.text.includes('공유') && r.text.includes('홈 화면에 추가'), JSON.stringify(r));
    await p.click('#instx');
    await p.reload({ waitUntil: 'load' }); await nudge(p);
    assert.ok(await p.evaluate(() => document.getElementById('inst').hidden && +localStorage.getItem('instx') > 0), '닫으면 7일 안 보임');
    await p.evaluate(() => localStorage.setItem('instx', Date.now() - 8 * 864e5)); await p.reload({ waitUntil: 'load' }); await nudge(p);
    assert.ok(await p.evaluate(() => !document.getElementById('inst').hidden), '7일 지나면 다시');
    await c.close();
    [r, c, p] = await show({ viewport: { width: 390, height: 844 }, userAgent: IG }, null, true);
    assert.ok(r.shown && !r.btn && r.text.includes('크롬·사파리에서 열면'), JSON.stringify(r));
    await p.waitForTimeout(300);
    assert.strictEqual(await p.evaluate(() => navigator.serviceWorker.getRegistrations().then(x => x.length)), 0, '앱 안 브라우저 = 서비스워커 X');
    await c.close();
    const TG = 'Mozilla/5.0 (Linux; Android 14; SM-S918N Build/UP1A; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/129.0.0.0 Mobile Safari/537.36 Telegram-Android/11.2.3';
    for (const ua of [TG, IOS.replace(' Version/18.0 Mobile/15E148 Safari/604.1', ' Mobile/15E148')]) {  // 텔레그램 안드로이드 WebView · 사파리 아닌 iOS 앱 안 브라우저
      [r, c, p] = await show({ viewport: { width: 390, height: 844 }, userAgent: ua }, null, true);
      assert.ok(r.shown && !r.btn && r.text.includes('크롬·사파리에서 열면'), ua + JSON.stringify(r));
      await c.close();
    }
    [r, c, p] = await show({ viewport: { width: 820, height: 1180 }, userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15' },
                           () => Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 5 }));  // 아이패드 사파리(맥 UA)
    assert.ok(r.shown && !r.btn && r.text.includes('홈 화면에 추가'), '아이패드 ' + JSON.stringify(r));
    await c.close();
    [r, c, p] = await show({ viewport: { width: 390, height: 844 } }, STANDALONE, true);
    assert.ok(!r.shown, '설치됨 = 숨김');
    await c.close();
    // 6) 휴대폰 기준(10/23 진우 '모바일이 중요' · 10/24 개편 360·390·412): 갤럭시 S·아이폰·갤럭시 플러스 × 일반 브라우저·설치 앱(standalone) 첫 화면
    //    설치 띠 = 작은 띠(48~80px)·버튼 44px+·아래 고정 바·앱 안 탭 줄과 안 겹침·첫 딜이 첫 화면에 보임 · 노치·홈 바(safe-area) 여백 -> 한 장(docs/cards/pwa_preview.png)
    const AND = 'Mozilla/5.0 (Linux; Android 15; SM-S921N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36';
    {  // 포털형 2차(진우 v3) 확인: 390×660 첫 화면 = 검색 + 기획전 배너(있으면) + 바로가기 2줄 + 🔥 줄 2개↑(배너 없으면 3개↑) · 위로 밀면 검색칸만 붙음
      const c6 = await browser.newContext({ viewport: { width: 390, height: 660 }, userAgent: IOS, isMobile: true, hasTouch: true }), p6 = await c6.newPage();
      await p6.addInitScript(V2);  // 두 번째 방문(설치 띠 대상) — 첫 화면은 띠 X, 처음 밀 때 띠
      await p6.goto(U + '/', { waitUntil: 'load' });
      assert.ok(await p6.evaluate(() => document.getElementById('inst').hidden), '390×660 첫 화면 = 설치 띠 X');
      const F = await p6.evaluate(() => { const nav = document.querySelector('nav.nav').getBoundingClientRect().top, B = s => { const e = document.querySelector(s); return e ? e.getBoundingClientRect().bottom : null; };
        return { nav, sb: B('.sb'), evb: B('.evb'), pb: B('.pb'), qk: B('.qk'), rows: [...document.querySelectorAll('#fire .rows:not([hidden]) .r')].filter(e => e.getBoundingClientRect().bottom <= nav).length,
                 ft: (document.querySelector('#fire .rows:not([hidden]) .r') || { getBoundingClientRect: () => ({ top: 1e9 }) }).getBoundingClientRect().top, bub: !!document.querySelector('.qk .qb') }; });
      assert.ok(F.sb && F.qk && F.qk < F.nav && (F.pb ? F.pb < F.qk && F.ft < F.nav : F.rows >= (F.evb ? 2 : 3)), '390×660 첫 화면 ' + JSON.stringify(F));  // 기획전 띠(10/25 진우 시안 B — 검색 아래·핫딜 위, 칸 250×112)가 있으면 = 띠 + 바로가기 + 🔥 첫 줄이 첫 화면에서 시작(줄 수는 띠 높이만큼 줄어듦 — Cowork에 숫자 보고)
      await p6.evaluate(() => scrollTo(0, 600)); await p6.waitForTimeout(100);
      const st = await p6.evaluate(() => [document.querySelector('.sb').getBoundingClientRect().top, document.querySelector('.hr').getBoundingClientRect().bottom]);
      assert.ok(st[0] >= -1 && st[0] <= 8 && st[1] <= 1, '밀면 로고 줄은 사라지고 검색칸만 위에 ' + JSON.stringify(st));
      assert.ok(await p6.evaluate(() => !document.getElementById('inst').hidden), '밀면 설치 띠');
      await c6.close();
    }
    const PHONES = [[360, 780, AND, 'Galaxy S 360'], [390, 844, IOS, 'iPhone 390'], [412, 915, AND, 'Galaxy+ 412']];
    const shots = [], tmp = fs.mkdtempSync(path.join(require('os').tmpdir(), 'pwa'));
    const layout = p => p.evaluate(() => {  // 아래 메뉴: 보통 = 아래 고정(fixed), 앱 안 브라우저 = 헤더 아래 한 줄(static)
      const R = e => e && getComputedStyle(e).display !== 'none' && !e.hidden ? e.getBoundingClientRect() : null, i = document.getElementById('inst'), nav = document.querySelector('nav.nav'), fx = getComputedStyle(nav).position === 'fixed';
      const navTop = fx ? nav.getBoundingClientRect().top : innerHeight;
      return { inst: R(i), btn: R(document.getElementById('instb')), x: R(document.getElementById('instx')), bottom: fx ? R(nav) : null, top: fx ? null : R(nav), g: R(document.querySelector('#fire .rows:not([hidden]) .r')), vh: innerHeight,
               pb: parseFloat(getComputedStyle(nav).paddingBottom), pt: 0, rows: [...document.querySelectorAll('#fire .rows:not([hidden]) .r')].filter(e => e.getBoundingClientRect().bottom <= navTop).length,
               qk: R(document.querySelector('.qk')), q1: [...document.querySelectorAll('.qr:first-child .q')].filter(e => e.getBoundingClientRect().right <= innerWidth).length, q2: document.querySelectorAll('.qr:last-child .q').length,
               evb: R(document.querySelector('.evb')), band: R(document.querySelector('.pb')), sb: R(document.querySelector('.sb')) };
    });
    const over = (a, b) => a && b && a.top < b.bottom && b.top < a.bottom;
    for (const [w, h, ua, name] of PHONES) for (const app of [false, true]) {
      const c2 = await browser.newContext({ viewport: { width: w, height: h }, userAgent: ua, isMobile: true, hasTouch: true, deviceScaleFactor: 1 }), p2 = await c2.newPage();
      if (app) await p2.addInitScript(STANDALONE); else await p2.addInitScript(V2);
      let safe = false;
      if (app && ua === IOS) try { const s = await c2.newCDPSession(p2); await s.send('Emulation.setSafeAreaInsetsOverride', { insets: { top: 0, bottom: 34, left: 0, right: 0 } }); safe = true; } catch (e) {}  // 아이폰 홈 바(크롬 DevTools가 지원하면)
      await p2.goto(U + (app ? '/?src=app' : '/'), { waitUntil: 'load' });
      if (!app && ua === AND) await p2.evaluate(() => { const e = new Event('beforeinstallprompt'); e.prompt = () => {}; e.userChoice = Promise.resolve({}); dispatchEvent(e); });
      if (!app) await nudge(p2);
      const L = await layout(p2), tag = `${name} ${app ? '앱' : '브라우저'}`;
      if (app) assert.ok(!L.inst, tag + ': 설치 앱 = 띠 없음');
      else {
        assert.ok(L.inst && L.inst.height >= 48 && L.inst.height <= 80 && L.inst.bottom <= L.vh - (L.bottom ? L.bottom.height : 0), tag + ' 띠(아래 메뉴 위 얇게) ' + JSON.stringify(L.inst));
        assert.ok(L.x.width >= 44 && L.x.height >= 44 && (!L.btn || L.btn.height >= 44), tag + ' 버튼 44px+');
        assert.ok(!over(L.inst, L.bottom) && !over(L.inst, L.top), tag + ' 띠가 고정 바와 안 겹침');
      }
      assert.ok(L.g && L.g.top < L.vh - (L.bottom ? L.bottom.height : 0) - 40, tag + ' 실시간 핫딜 1번이 첫 화면에 ' + JSON.stringify([L.g, L.vh]));
      assert.ok(L.qk && L.sb && L.qk.bottom <= L.vh && L.q1 >= 6 && L.q2 === 14 && L.rows >= (w >= 390 ? 4 : 3) - (L.band ? 2 : 0), tag + ' 첫 화면 = 검색·(기획전 띠 = 2줄 덜)·바로가기 2줄(6개+)·핫딜 줄 4개↑(포털형 2차) ' + JSON.stringify([L.rows, L.qk, L.q1, L.vh]));
      assert.ok(await p2.evaluate(() => document.documentElement.scrollWidth <= innerWidth), tag + ' 옆으로 안 넘침');
      if (safe) assert.ok(L.pb >= 40, tag + ' 홈 바 여백 ' + L.pb);
      const f = path.join(tmp, `${w}${app ? 'a' : 'b'}.png`);
      await p2.screenshot({ path: f });
      shots.push([f, tag + (safe ? ' (홈 바 34px)' : '')]);
      await c2.close();
    }
    const c3 = await browser.newContext({ viewport: { width: 390, height: 844 }, userAgent: IG, isMobile: true, hasTouch: true }), p3 = await c3.newPage();  // 앱 안 브라우저(인스타) — 띠 + 헤더 아래 메뉴 한 줄
    await p3.addInitScript(V2); await p3.goto(U + '/', { waitUntil: 'load' }); await nudge(p3);
    const L3 = await layout(p3);
    assert.ok(L3.inst && L3.top && !over(L3.inst, L3.top) && !L3.bottom, '앱 안: 띠·탭 줄 안 겹침 ' + JSON.stringify([L3.inst, L3.top]));
    await p3.evaluate(() => scrollTo(0, 600)); const L4 = await layout(p3);
    assert.ok(!over(L4.inst, L4.top) || L4.inst.bottom <= 0, '앱 안: 내려도 탭 줄이 띠를 안 덮음');
    await c3.close();
    {  // 7) 화면 고르기(10/24 Cowork·진우): A 목록형(1차 — 헤더 1줄 검색·몰 버튼·품목 6×2) / B 아이콘형(2차) · 첫 방문 무작위 50:50(hp_layout) · 저장소 막힘 = A · 바꾸기 버튼(홈 맨 아래·/c/) 기억 · GoatCounter layout/
      const GCS = r => r.fulfill({ contentType: 'text/javascript', body: 'window.__gcl=1;goatcounter.count=function(v){(window.__gc=window.__gc||[]).push(v)}' });
      const A = await browser.newContext({ viewport: { width: 390, height: 844 }, userAgent: IOS, isMobile: true, hasTouch: true }, 'a'), pa = await A.newPage(), errA = []; pa.on('pageerror', e => errA.push(String(e)));
      await A.route(/\/\/gc\.zgo\.at\/count\.js/, GCS);
      await pa.goto(U + '/', { waitUntil: 'load' }); await pa.waitForFunction(() => window.__gcl === 1 && (window.__gc || []).length);
      const LA = await pa.evaluate(() => { const V = s => { const e = document.querySelector(s); return !!e && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().height > 1; }, r = s => document.querySelector(s).getBoundingClientRect();
        return { cls: document.documentElement.className, mb: V('main > .la .mb'), m: document.querySelectorAll('.mb .m').length, t6: document.querySelectorAll('main > .la .t6 .tile').length, t6r: new Set([...document.querySelectorAll('main > .la .t6 .tile')].map(e => Math.round(e.getBoundingClientRect().top))).size, qk: V('.qk'), evb: V('.evb'), sb: r('.sb').top, hr: r('.hr').bottom, lg: r('.lg h1, .lg b').width,
                 heart: V('.hr .ib+.ib'), over: document.documentElement.scrollWidth - innerWidth, fire: r('#fire .rows:not([hidden]) .r').top, vh: innerHeight, gc: (window.__gc || []).map(v => v.event && v.path) }; });
      assert.ok(/\blay-a\b/.test(LA.cls) && LA.mb && LA.m >= 3 && LA.t6 === 13 && LA.t6r === 2 && !LA.qk && !LA.evb && LA.sb < LA.hr && LA.lg <= 1 && !LA.heart && LA.over <= 0 && LA.fire < LA.vh - 120, 'A 목록형 = 검색 헤더 1줄·몰 버튼·품목 2줄(13칸 = 7칸씩 — 10/26 자동차 칸)(바로가기·배너 X) ' + JSON.stringify(LA));
      assert.ok(LA.gc.includes('layout/A'), 'GoatCounter 방문 layout/A ' + LA.gc);
      const bA = await pa.evaluate(() => { window.__gc = []; const a = document.querySelector('a[rel~="nofollow"][href^="http"]:not([data-gc^="promo/"])'); a.addEventListener('click', e => e.preventDefault()); a.click(); return window.__gc.map(v => v.path); });
      assert.ok(bA.some(p => p.startsWith('buy/') && p.includes('/', 4)) && bA.includes('layout/A/buy'), '구매 클릭 = buy/ 그대로 + 화면 꼬리표 layout/A/buy ' + bA);
      await pa.reload({ waitUntil: 'load' }); await pa.waitForFunction(() => window.__gcl === 1); await pa.waitForTimeout(100);
      assert.ok(!(await pa.evaluate(() => (window.__gc || []).some(v => v.path === 'layout/A'))), '방문 = 탭 세션 1번');
      await pa.click('.lsw [data-l=b]');
      const sw = await pa.evaluate(() => [document.documentElement.className, localStorage.getItem('hp_layout'), scrollY, getComputedStyle(document.querySelector('main > .lb')).display, getComputedStyle(document.querySelector('main > .la')).display, (window.__gc || []).map(v => v.path), document.querySelector('.lsw [data-l=b]').getAttribute('aria-pressed') === 'true' && document.querySelector('.lsw [data-l=a]').getAttribute('aria-pressed') === 'false']);
      assert.ok(/\blay-b\b/.test(sw[0]) && !/\blay-a\b/.test(sw[0]) && sw[1] === 'b' && sw[2] === 0 && sw[3] !== 'none' && sw[4] === 'none' && sw[5].includes('layout/switch/B') && sw[6], '바꾸기(홈 맨 아래 — 화면: 목록형·아이콘형·혼합형) = 아이콘형 + 기억 + 맨 위로 + 눌림 표시 + layout/switch/B ' + JSON.stringify(sw));
      const bS = await pa.evaluate(() => { window.__gc = []; const a = document.querySelector('a[rel~="nofollow"][href^="http"]:not([data-gc^="promo/"])'); a.addEventListener('click', e => e.preventDefault()); a.click(); return window.__gc.map(v => v.path); });
      assert.ok(bS.includes('layout/A/buy') && !bS.includes('layout/B/buy'), '바꾼 탭의 구매 = 방문을 센 화면(A) 꼬리표 ' + bS);
      await pa.reload({ waitUntil: 'load' }); assert.ok(await pa.evaluate(() => document.documentElement.classList.contains('lay-b')), '다시 열어도 고른 화면');
      await pa.goto(U + '/c/', { waitUntil: 'load' }); await pa.click('.lsw [data-l=a]');
      assert.ok(await pa.evaluate(() => document.documentElement.classList.contains('lay-a') && localStorage.getItem('hp_layout') === 'a' && getComputedStyle(document.querySelector('.sb')).position === 'absolute'), '/c/ 바꾸기 버튼(헤더도 목록형)');
      assert.deepStrictEqual(errA, [], '화면 고르기 스크립트 오류 X');
      await A.close();
      for (const [x, l] of [[0.2, 'a'], [0.5, 'b'], [0.8, 'c']]) {  // 첫 방문 = 무작위 1/3(10/25 C 혼합형 — 이미 정해진 A·B는 그대로) → 저장
        const c = await browser.newContext({ viewport: { width: 390, height: 844 } }, null), p = await c.newPage(); await p.addInitScript(x => { Math.random = () => x; }, x); await p.goto(U + '/p/' + p0, { waitUntil: 'load' });
        assert.deepStrictEqual(await p.evaluate(() => [(document.documentElement.className.match(/lay-[abc]/) || [''])[0], localStorage.getItem('hp_layout')]), ['lay-' + l, l], '첫 방문 무작위 ' + x); await c.close();
      }
      const cB = await browser.newContext({ viewport: { width: 390, height: 844 } }, null); await cB.addInitScript(() => { Object.defineProperty(window, 'localStorage', { get() { throw new Error('blocked'); } }); });
      await cB.route(/\/\/gc\.zgo\.at\/count\.js/, GCS);
      const pB = await cB.newPage(), errB = []; pB.on('pageerror', e => errB.push(String(e))); await pB.goto(U + '/', { waitUntil: 'load' }); await pB.waitForFunction(() => window.__gcl === 1); await pB.waitForTimeout(100);
      const gB = await pB.evaluate(() => { const a = document.querySelector('a[rel~="nofollow"][href^="http"]:not([data-gc^="promo/"])'); a.addEventListener('click', e => e.preventDefault()); a.click(); return (window.__gc || []).map(v => v.path); });
      assert.ok(gB.some(p => p.startsWith('buy/')) && !gB.some(p => p.startsWith('layout/')), '저장소 막힘 = 무작위 X → 화면 실험 밖(layout/ 방문·구매 꼬리표 X, buy/는 그대로) ' + gB);
      const LB = await pB.evaluate(() => [document.documentElement.classList.contains('lay-a'), getComputedStyle(document.querySelector('main > .la')).display !== 'none', getComputedStyle(document.querySelector('main > .lb')).display === 'none', document.documentElement.scrollWidth <= innerWidth]);
      await pB.click('.lsw [data-l=b]'); const LB2 = await pB.evaluate(() => document.documentElement.classList.contains('lay-b') && getComputedStyle(document.querySelector('main > .lb')).display !== 'none');
      assert.ok(LB.every(Boolean) && LB2 && !errB.length, '저장소 막힘 = A 목록형 정상(바꾸기는 이 쪽에서만) ' + JSON.stringify([LB, LB2, errB]));
      await cB.close();
      for (const [w, h, ua, name] of PHONES) for (const l of ['a', 'b', 'c']) for (const ia of [false, true]) {  // 세 화면 × 일반·앱 안 브라우저 = 옆으로 안 넘침 · 🔥 첫 줄이 첫 화면에
        const c = await browser.newContext({ viewport: { width: w, height: h }, userAgent: ia ? IG : ua, isMobile: true, hasTouch: true }, l), p = await c.newPage(); await p.goto(U + '/', { waitUntil: 'load' }); await p.evaluate(() => scrollTo(0, 0));
        const o = await p.evaluate(() => [document.documentElement.scrollWidth - innerWidth, document.querySelector('#fire .rows:not([hidden]) .r').getBoundingClientRect().top, innerHeight, document.documentElement.className]);
        assert.ok(o[3].includes('lay-' + l) && o[0] <= 0 && (ia || o[1] < o[2]), `${name} ${l}${ia ? ' 앱 안' : ''} 옆 넘침 0·🔥 첫 화면 ` + JSON.stringify(o)); await c.close();
      }
      for (const old of ['a', 'b']) {  // 이미 A·B인 사람 = 그대로(C로 안 바뀜)
        const c = await browser.newContext({ viewport: { width: 390, height: 844 } }, old), p = await c.newPage(); await p.addInitScript(() => { Math.random = () => 0.9; }); await p.goto(U + '/', { waitUntil: 'load' });
        assert.ok(await p.evaluate(o => document.documentElement.classList.contains('lay-' + o) && localStorage.getItem('hp_layout') === o, old), '기존 화면 유지 ' + old); await c.close();
      }
      // 7b) C 혼합형(10/25 진우 '둘의 장점을 합친 화면' · Cowork): 헤더 1줄(로고·빨강 검색·🔔·♡) + B 배너 + 바로가기 1줄(끝 ▦ 품목 전체) + 대가성 + A 🔥 탭·목록 — 390×660 첫 화면 = 배너 + 아이콘 1줄 + 🔥 4줄(아래 메뉴 위) · layout/C
      const C = await browser.newContext({ viewport: { width: 390, height: 660 }, userAgent: IOS, isMobile: true, hasTouch: true }, 'c'), pc = await C.newPage(), errC = []; pc.on('pageerror', e => errC.push(String(e)));
      await C.addInitScript(() => { try { localStorage.setItem('instx', String(Date.now())); } catch (e) {} }); await C.route(/\/\/gc\.zgo\.at\/count\.js/, GCS);
      await pc.goto(U + '/', { waitUntil: 'load' }); await pc.waitForFunction(() => window.__gcl === 1 && (window.__gc || []).length);
      const LC = await pc.evaluate(() => { const V = e => !!e && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().height > 1, r = e => e.getBoundingClientRect(), Q = s => document.querySelector(s);
        const rows = [...document.querySelectorAll('#fire .rows:not([hidden]) .r')].slice(0, 4).map(e => r(e).bottom), ev = Q('.evb');
        return { pb: V(Q('.pb')), cls: document.documentElement.className, la: V(Q('main > .la')), lb: V(Q('main > .lb')), ev: !!ev, evb: V(ev), evh: ev && Math.round(r(ev.querySelector('.ev')).height), qr: [...document.querySelectorAll('.qr')].filter(V).length, qc: V(Q('.qr .qc')), qch: Q('.qr .qc').getAttribute('href'),
                 t6: V(Q('.t6')), mb: V(Q('.mb')), sb: r(Q('.sb')).toJSON(), hr: r(Q('.hr')).bottom, ib: [...document.querySelectorAll('.hr .ib')].map(e => V(e) && r(e).left), red: getComputedStyle(Q('.sb input')).borderTopColor, rows, nav: r(Q('.nav')).top,
                 dis: r(Q('main > .dis')).top > r(Q('.qr')).bottom && r(Q('main > .dis')).bottom < r(Q('#fire')).top, over: document.documentElement.scrollWidth - innerWidth, gc: (window.__gc || []).map(v => v.event && v.path) }; });
      assert.ok(/\blay-c\b/.test(LC.cls) && !LC.la && LC.lb && LC.evb === LC.ev && (!LC.ev || LC.evh === 84) && LC.qr === 1 && LC.qc && LC.qch.endsWith('/c/') && !LC.t6 && !LC.mb && LC.dis && LC.over <= 0, 'C = 배너(84px) + 바로가기 1줄 + ▦ 품목 전체 → 대가성 → 🔥 · 품목 12칸·몰 버튼 X ' + JSON.stringify(LC));
      assert.ok(LC.sb.top < LC.hr && LC.ib.length === 2 && LC.ib.every(x => x !== false && x >= LC.sb.right) && LC.red === 'rgb(229, 48, 63)', 'C 헤더 1줄 = 로고 · 빨강 테두리 검색 · 🔔 · ♡(안 겹침) ' + JSON.stringify(LC));
      assert.ok(LC.rows.length === 4 && LC.rows[LC.pb ? 2 : 3] <= LC.nav, '390×660 첫 화면 = (기획전 있으면 배너 +) 아이콘 1줄 + 🔥 4줄(기획전 띠 = 3줄 · 아래 메뉴 위) ' + JSON.stringify([LC.ev, LC.pb, LC.rows, LC.nav]));  // 배너 없는 날도(행사 끝나면) 확인
      assert.ok(LC.gc.includes('layout/C'), 'GoatCounter 방문 layout/C ' + LC.gc);
      const bC = await pc.evaluate(() => { window.__gc = []; const a = document.querySelector('a[rel~="nofollow"][href^="http"]:not([data-gc^="promo/"])'); a.addEventListener('click', e => e.preventDefault()); a.click(); return window.__gc.map(v => v.path); });
      assert.ok(bC.includes('layout/C/buy'), '구매 클릭 꼬리표 layout/C/buy ' + bC);
      assert.ok(await pc.evaluate(() => document.querySelector('.lsw [data-l=c]').getAttribute('aria-pressed') === 'true' && /화면:\s*목록형\s*아이콘형\s*혼합형/.test(document.querySelector('.lsw').textContent)), '고르기 = 화면: 목록형 · 아이콘형 · 혼합형(지금 = 혼합형)');
      await pc.evaluate(() => { window.__gc = []; }); await pc.click('.lsw [data-l=c]');
      assert.ok(await pc.evaluate(() => document.documentElement.classList.contains('lay-c') && !(window.__gc || []).length), '지금 화면 버튼 = 바꿈 X·GoatCounter X');
      assert.ok(!LC.gc.some(p => p && p.startsWith('layout3/')) && !bC.some(p => p.startsWith('layout3/')), '예전 배정(hp_lc 없음) = layout3/ X');
      await pc.click('.lsw [data-l=a]');
      assert.ok(await pc.evaluate(() => document.documentElement.classList.contains('lay-a') && localStorage.getItem('hp_layout') === 'a' && getComputedStyle(document.querySelector('main > .la')).display !== 'none' && (window.__gc || []).some(v => v.path === 'layout/switch/A')), 'C → 목록형 바꾸기');
      assert.deepStrictEqual(errC, [], 'C 스크립트 오류 X'); await C.close();
      const N3 = await browser.newContext({ viewport: { width: 390, height: 844 } }, null), p3 = await N3.newPage(); await N3.route(/\/\/gc\.zgo\.at\/count\.js/, GCS);  // C 연 뒤 새로 배정된 사람 = layout3/ 꼬리표(A·B·C 공정 비교 — 예전 A·B 사람은 다시 오는 사람)
      await p3.addInitScript(() => { Math.random = () => 0.9; }); await p3.goto(U + '/', { waitUntil: 'load' }); await p3.waitForFunction(() => window.__gcl === 1 && (window.__gc || []).length);
      const g3 = await p3.evaluate(() => { const v = (window.__gc || []).map(x => x.path); window.__gc = []; const a = document.querySelector('a[rel~="nofollow"][href^="http"]:not([data-gc^="promo/"])'); a.addEventListener('click', e => e.preventDefault()); a.click(); return [v, window.__gc.map(x => x.path), localStorage.getItem('hp_lc')]; });
      assert.ok(g3[0].includes('layout/C') && g3[0].includes('layout3/C') && g3[1].includes('layout/C/buy') && g3[1].includes('layout3/C/buy') && g3[2] === '3', '새 배정 = layout3/C 방문·구매 ' + JSON.stringify(g3)); await N3.close();
    }
    {  // 7c) TOP/END(10/25 진우 '맨 위로 올라가는 TOP 혹은 END 버튼 — 있으면 의외로 좋더라'): 모든 쪽 오른쪽 아래 ↑ 맨 위 / ↓ 맨 아래 — 100vh 넘게 내렸을 때만 · 맨 아래 근처 ↓ 숨김 · 44px · 아래 메뉴·설치 띠 안 가림 · 움직임 줄이기 = 바로 · nav/top·nav/end
      const GCT = r => r.fulfill({ contentType: 'text/javascript', body: 'window.__gcl=1;goatcounter.count=function(v){(window.__gc=window.__gc||[]).push(v)}' });
      const hit = (a, b) => a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3], R4 = 'const R=e=>{const x=e.getBoundingClientRect();return [x.left,x.top,x.right,x.bottom]};';
      for (const u of ['index.html', 'c/index.html', 'c/coupang/index.html', 'c/life/index.html', 'p/' + p0, 'saved/index.html', 'alarm/index.html'])
        assert.ok(/<div class="tb" hidden><button type="button" data-gc="nav\/top" aria-label="맨 위로">.*<button type="button" data-gc="nav\/end" aria-label="맨 아래로">/.test(fs.readFileSync(path.join(ROOT, u), 'utf8')), 'TOP/END 모든 쪽 ' + u);
      for (const l of ['a', 'b', 'c']) for (const dark of [false, true]) {
        const c = await browser.newContext({ viewport: { width: 390, height: 844 }, userAgent: IOS, isMobile: true, hasTouch: true, reducedMotion: 'reduce', colorScheme: dark ? 'dark' : 'light' }, l), p = await c.newPage(), err = []; p.on('pageerror', e => err.push(String(e)));
        await c.addInitScript(() => { try { localStorage.setItem('instx', String(Date.now())); } catch (e) {} }); await c.route(/\/\/gc\.zgo\.at\/count\.js/, GCT);
        await p.goto(U + '/', { waitUntil: 'load' }); await p.waitForFunction(() => window.__gcl === 1);
        const st = () => p.evaluate(R4 + "const b=document.querySelector('.tb'),u=b.children[0],d=b.children[1],V=e=>!e.closest('[hidden]')&&getComputedStyle(e).display!=='none'&&getComputedStyle(e).visibility!=='hidden';"
          + "({y:scrollY,u:V(u),d:V(d),ur:R(u),dr:R(d),nav:R(document.querySelector('.nav')),bg:getComputedStyle(u).backgroundColor,max:document.documentElement.scrollHeight-innerHeight})");
        let s = await st(); assert.ok(!s.u && !s.d, '맨 위 = 버튼 X ' + l);
        await p.evaluate(() => scrollTo(0, innerHeight * 0.9)); await p.waitForTimeout(80); s = await st(); assert.ok(!s.u && !s.d, '100vh 안 = X ' + l);
        await p.evaluate(() => scrollTo(0, innerHeight * 1.5)); await p.waitForTimeout(80); s = await st();
        assert.ok(s.u && s.d && s.ur[2] - s.ur[0] === 44 && s.ur[3] - s.ur[1] === 44 && s.dr[3] - s.dr[1] === 44 && s.dr[1] > s.ur[3] && s.dr[3] <= s.nav[1] && !hit(s.dr, s.nav) && s.ur[2] <= 390, 'TOP/END = 44px 세로 2개 · 아래 메뉴 위 ' + l + JSON.stringify(s));
        const n = s.bg.match(/[\d.]+/g).map(Number), lum = (s.bg.startsWith('color(') ? n.slice(0, 3).map(v => v * 255) : n.slice(0, 3)).reduce((a, b) => a + b, 0), al = s.bg.startsWith('color(') ? n[3] : n[3];
        assert.ok((dark ? lum < 200 : lum > 600) && al > 0.5 && al < 1, '다크·라이트 반투명 바탕 ' + s.bg);
        const ur0 = s.ur; await p.evaluate(() => { window.__gc = []; }); await p.click('.tb [aria-label="맨 아래로"]'); await p.waitForTimeout(80); s = await st();
        assert.ok(s.y >= s.max - 2 && s.u && !s.d && JSON.stringify(s.ur) === JSON.stringify(ur0), '↓ = 맨 아래(움직임 줄이기 = 바로) · 맨 아래 근처 ↓ 숨김(↑ 자리 그대로 — 두 번 눌러도 ↑ X) ' + JSON.stringify(s));
        assert.ok(await p.evaluate(() => document.activeElement === document.querySelector('.tb [aria-label="맨 위로"]')), '↓ 누른 뒤 초점 = ↑');
        await p.click('.tb [aria-label="맨 위로"]'); await p.waitForTimeout(80); s = await st();
        assert.ok(s.y === 0 && !s.u && await p.evaluate(() => document.activeElement === document.querySelector('.lg')), '↑ = 맨 위 + 버튼 숨김 · 초점 = 로고 ' + JSON.stringify(s));
        assert.deepStrictEqual(await p.evaluate(() => window.__gc.filter(v => v.event).map(v => v.path)), ['nav/end', 'nav/top'], 'GoatCounter nav/end·nav/top');
        assert.deepStrictEqual(err, [], 'TOP/END 오류 X'); await c.close();
      }
      const cs = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true }), ps = await cs.newPage(); await ps.goto(U + '/', { waitUntil: 'load' });  // 움직임 줄이기 X = 부드럽게(바로 0 아님 → 결국 맨 위)
      await ps.evaluate(() => scrollTo(0, innerHeight * 3)); await ps.waitForTimeout(80); await ps.click('.tb [aria-label="맨 위로"]');
      assert.ok(await ps.evaluate(() => scrollY) > 0, '부드럽게 올라감'); await ps.waitForFunction(() => scrollY === 0, null, { timeout: 5000 }); await cs.close();
      const ci = await browser.newContext({ viewport: { width: 390, height: 844 }, userAgent: IOS, isMobile: true, hasTouch: true }, 'c'), pi = await ci.newPage();  // 설치 띠 있을 때 = 그 위로
      await ci.addInitScript(() => { try { localStorage.setItem('hv', '5'); } catch (e) {} }); await pi.goto(U + '/', { waitUntil: 'load' });
      await pi.evaluate(() => scrollTo(0, innerHeight * 1.5)); await pi.waitForTimeout(150);
      const si = await pi.evaluate(R4 + "const i=document.getElementById('inst'),b=document.querySelector('.tb');({inst:!i.hidden&&R(i),tb:!b.hidden,u:R(b.children[0]),d:R(b.children[1]),nav:R(document.querySelector('.nav'))})");
      assert.ok(si.inst && si.tb && !hit(si.u, si.inst) && !hit(si.d, si.inst) && si.d[3] <= si.inst[1] && !hit(si.d, si.nav), '설치 띠·아래 메뉴 안 가림 ' + JSON.stringify(si));
      await pi.evaluate(() => { const i = document.getElementById('inst'); i.style.minHeight = '120px'; dispatchEvent(new Event('resize')); }); await pi.waitForTimeout(80);  // 띠가 높아져도(큰 글자) 그 위로
      const sj = await pi.evaluate(R4 + "const i=document.getElementById('inst'),b=document.querySelector('.tb');({inst:R(i),d:R(b.children[1])})");
      assert.ok(sj.d[3] <= sj.inst[1], '높은 설치 띠도 안 가림 ' + JSON.stringify(sj)); await ci.close();
      const cw = await browser.newContext({ viewport: { width: 1024, height: 768 } }), pw = await cw.newPage(); await pw.goto(U + '/', { waitUntil: 'load' }); await pw.evaluate(() => scrollTo(0, innerHeight * 1.5)); await pw.waitForTimeout(80);  // 넓은 화면 = 본문 칸 밖(카드·♡ 안 가림)
      assert.ok(await pw.evaluate(() => !document.querySelector('.tb').hidden && document.querySelector('.tb').getBoundingClientRect().left >= document.querySelector('main').getBoundingClientRect().right), '넓은 화면 = 본문 밖'); await cw.close();
      const cg = await browser.newContext({ viewport: { width: 390, height: 844 }, userAgent: IG, isMobile: true, hasTouch: true }), pg2 = await cg.newPage(); await pg2.goto(U + '/', { waitUntil: 'load' });  // 앱 안 브라우저(아래 메뉴 = 검색 아래) = 맨 아래 쪽
      await pg2.evaluate(() => scrollTo(0, innerHeight * 1.5)); await pg2.waitForTimeout(80);
      assert.ok(await pg2.evaluate(() => { const r = document.querySelector('.tb').getBoundingClientRect(); return !document.querySelector('.tb').hidden && r.bottom <= innerHeight - 90 && r.bottom >= innerHeight - 160; }), '앱 안 = 앱 툴바(아래 ~85px) 위'); await cg.close();
      for (const [ua, lay] of [[IOS, 'a'], [IG, 'c']]) {  // 좁은 폰(320) 맨 아래 = ↑가 꼬리말 링크(블로그·인스타·Threads·텔레그램) 안 가림
        const cn = await browser.newContext({ viewport: { width: 320, height: 640 }, userAgent: ua, isMobile: true, hasTouch: true }, lay), pn = await cn.newPage(); await pn.goto(U + '/', { waitUntil: 'load' });
        await pn.evaluate(() => scrollTo(0, document.documentElement.scrollHeight)); await pn.waitForTimeout(120);
        const fo = await pn.evaluate(R4 + "const u=document.querySelector('.tb').children[0];({tb:!document.querySelector('.tb').hidden,u:R(u),a:[...document.querySelectorAll('footer a')].map(R)})");
        assert.ok(fo.tb && fo.a.length >= 4 && fo.a.every(a => !hit(a, fo.u)), '320 맨 아래 ↑ ≠ 꼬리말 링크 ' + lay + JSON.stringify(fo)); await cn.close();
      }
    }
    const rl = [];
    {  // 7d) /link(10/25 진우 — 시안 A·B 반반 같은 주소 · B 미리보기 /link/b/ noindex): 배정 = 50:50 무작위 → 이 브라우저에 저장(다시 와도 같은 쪽) · v=a/b 고정(저장·집계 X) · 저장 막힘 = 이번만 무작위 · JS 꺼짐 = A
      //     GoatCounter 보기 = 가상 경로 link-a·link-b · 채널 = link-a/채널 · 상품 = buy/link-a/몰 주소(미리보기 = link/·buy/) · 첫 화면 = 채널·대가성 문구(A = 지금 특가 첫 줄까지) · 칩 · 번호 · 제휴 안내 · 가로 넘침 X · 390 캡처
      const GCL = r => r.fulfill({ contentType: 'text/javascript', body: 'window.__gcl=1;goatcounter.count=function(v){(window.__gc=window.__gc||[]).push(v)}' });
      const LK = fs.readFileSync(path.join(ROOT, 'link/index.html'), 'utf8'), K = /data-gc="link\/kakao"/.test(LK);
      assert.ok(fs.statSync(path.join(ROOT, 'link/index.html')).size < 72000 && /name="robots" content="noindex/.test(fs.readFileSync(path.join(ROOT, 'link/b/index.html'), 'utf8')) && !/noindex/.test(LK), '/link 가볍게 · /link/b/ noindex');
      const NEW = async (o = {}) => { const c = await browser.newContext({ viewport: { width: 390, height: 844 }, userAgent: IOS, isMobile: true, hasTouch: true, ...o }, null); await c.route(/\/\/gc\.zgo\.at\/count\.js/, GCL); return c; };
      const ST = p => p.evaluate(() => [document.documentElement.className, (() => { try { return localStorage.getItem('hp_link'); } catch (e) { return 'X'; } })(), window.goatcounter && goatcounter.path && goatcounter.path('/x'),
                                         ...['.va', '.vb'].map(q => document.querySelector(q) ? getComputedStyle(document.querySelector(q)).display : ''), !!(window.goatcounter && goatcounter.no_onload)]);
      const CLK = p => p.evaluate(() => { window.__gc = []; [document.querySelector('.' + (document.documentElement.className === 'lb' ? 'vb' : 'va') + ' nav a[data-gc]'), document.querySelector('#lg > a:not([hidden])'), document.querySelector('.cr a[rel~="sponsored"]')].filter(Boolean)
        .forEach(a => { a.addEventListener('click', e => e.preventDefault()); a.click(); }); return window.__gc.map(v => v.event && v.path); });
      for (const [r, v] of [[0.9, 'b'], [0.1, 'a']]) {
        const c = await NEW(), p = await c.newPage(); await c.addInitScript(r => { if (!sessionStorage.getItem('r2')) Math.random = () => r; }, r);
        await p.goto(U + '/link/?ref=ig', { waitUntil: 'load' }); await p.waitForFunction(() => window.__gcl === 1);
        assert.deepStrictEqual(await ST(p), ['l' + v, v, 'link-' + v, v === 'a' ? 'block' : 'none', v === 'a' ? 'none' : 'block', false], '무작위 배정 ' + v);
        const g = await CLK(p); assert.ok(g[0] === 'link-' + v + '/blog' && g.slice(1).every(x => x.startsWith('buy/link-' + v + '/')) && g.length >= 2, 'GoatCounter 변형 표시 ' + JSON.stringify(g));
        await p.evaluate(() => sessionStorage.setItem('r2', '1')); await c.addInitScript(r => { Math.random = () => 1 - r; }, r);  // 다시 와도(무작위가 반대여도) 같은 쪽
        await p.goto(U + '/link/', { waitUntil: 'load' }); assert.deepStrictEqual((await ST(p)).slice(0, 3), ['l' + v, v, 'link-' + v], '다시 와도 같은 쪽 ' + v);
        const f = v === 'a' ? 'b' : 'a'; await p.goto(U + '/link/?v=' + f, { waitUntil: 'load' }); await p.waitForFunction(() => window.__gcl === 1);  // v= 고정 = 그 쪽 보기 · 저장 그대로 · 보기·클릭 집계 X
        assert.deepStrictEqual(await ST(p), ['l' + f, v, '/x', f === 'a' ? 'block' : 'none', f === 'a' ? 'none' : 'block', true], 'v= 고정 ' + f);
        assert.deepStrictEqual(await CLK(p), [], 'v= 고정 = 집계 X'); await c.close();
      }
      { const c = await NEW(), p = await c.newPage(), err = []; p.on('pageerror', e => err.push(String(e)));  // 저장 막힘(사생활 보호 모드 등) = 이번만 무작위, 오류 X
        await c.addInitScript(() => { Object.defineProperty(window, 'localStorage', { get() { throw new Error('blocked'); } }); Math.random = () => 0.2; });
        await p.goto(U + '/link/', { waitUntil: 'load' }); assert.deepStrictEqual((await ST(p)).slice(0, 3), ['la', 'X', 'link-a'], '저장 막힘 = 이번만'); assert.deepStrictEqual(err, [], '저장 막힘 오류 X'); await c.close(); }
      { const c = await NEW({ javaScriptEnabled: false }), p = await c.newPage(); await p.goto(U + '/link/', { waitUntil: 'load' });  // JS 꺼짐 = A
        assert.deepStrictEqual(await p.evaluate(() => [getComputedStyle(document.querySelector('.va')).display, getComputedStyle(document.querySelector('.vb')).display]), ['block', 'none'], 'JS 꺼짐 = A'); await c.close(); }
      { const c = await NEW(), p = await c.newPage(); await p.goto(U + '/link/b/', { waitUntil: 'load' }); await p.waitForFunction(() => window.__gcl === 1);  // 미리보기 = 배정·저장 X · 예전 경로
        const s = await ST(p), g = await CLK(p); assert.ok(s[0] === 'lb' && s[1] === null && g[0] === 'link/blog' && g.length >= 2 && g.slice(1).every(x => x.startsWith('buy/') && !x.startsWith('buy/link-')), '미리보기 ' + JSON.stringify([s, g])); await c.close(); }
      for (const [u, ua, st] of [['/link/?v=a', IOS, 'a'], ['/link/?v=a', IG, 'a'], ['/link/?v=b', IOS, 'b']]) for (const dark of [false, true]) {
        const c = await browser.newContext({ viewport: { width: 390, height: 844 }, userAgent: ua, isMobile: true, hasTouch: true, deviceScaleFactor: 2, colorScheme: dark ? 'dark' : 'light' }, null), p = await c.newPage(), err = [];
        p.on('pageerror', e => err.push(String(e))); await c.route(/\/\/gc\.zgo\.at\/count\.js/, GCL);
        await p.goto(U + u + '&ref=ig', { waitUntil: 'load' }); await p.waitForFunction(() => window.__gcl === 1);
        const s = await p.evaluate(() => { const R = e => e.getBoundingClientRect(), top = document.querySelector(document.documentElement.className === 'lb' ? '.vb' : '.va'), ch = [...top.querySelectorAll('nav a[data-gc]')], t1 = document.querySelector('#lg > a');
          return { sw: document.documentElement.scrollWidth, disc: R(document.querySelector('.disc')).bottom, ch: ch.map(a => a.getAttribute('data-gc')), chb: Math.max(...ch.map(a => R(a).bottom)), t1: t1 && R(t1).bottom,
                   bg: getComputedStyle(document.body).backgroundColor, cls: document.documentElement.className, no: document.querySelectorAll('#lg > a:not([hidden])').length, badge: document.querySelectorAll('#lg .no').length,
                   font: getComputedStyle(document.body).fontFamily, fonts: performance.getEntriesByType('resource').filter(r => /\.woff2/.test(r.name)).length }; });
        const lum = s.bg.match(/[\d.]+/g).slice(0, 3).map(Number).reduce((a, b) => a + b, 0);
        assert.ok(s.sw <= 390 && s.disc <= 844 && s.chb <= 844 && s.cls === 'l' + st && (dark ? lum < 120 : lum > 700) && s.no <= 12 && !s.badge && !/HDP Sans/.test(s.font) && !s.fonts, '첫 화면·번호 배지 X·시스템 글꼴(글꼴 파일 X) ' + u + dark + JSON.stringify(s));
        if (st === 'a') assert.ok(!s.t1 || s.t1 <= 844 - (K ? 0 : 64), 'A 첫 화면 = 지금 특가 첫 줄까지(카톡 버튼 자리 남김) ' + s.t1);
        assert.deepStrictEqual(s.ch, [...(K ? ['link/kakao'] : []), ...(st === 'a' ? ['link/blog', 'link/threads', 'link/instagram', 'link/telegram', 'link/home'] : ['link/blog', 'link/threads', 'link/instagram'])], '채널 ' + u);
        if (st === 'a') {
          const tg = () => p.evaluate(() => [!document.getElementById('adw').hidden, document.querySelector('.ad').getAttribute('aria-expanded')]);
          await p.click('.ad'); assert.deepStrictEqual(await tg(), [true, 'true'], '제휴 안내 펼침'); await p.click('.ad'); assert.deepStrictEqual(await tg(), [false, 'false'], '제휴 안내 접기');
        }
        if (await p.$('#lg')) for (const k of await p.$$eval('.chips button', b => b.map(x => x.getAttribute('data-k')))) {
          await p.click(`.chips button[data-k="${k}"]`);
          const v = await p.evaluate(k => { const T = [...document.querySelectorAll('#lg > a')].filter(t => !t.hidden), r = T.slice(0, 3).map(t => t.getBoundingClientRect());
            return { n: T.length, dn: +document.getElementById('dn').textContent, k: T.every(t => (' ' + t.getAttribute('data-k') + ' ').includes(' ' + k + ' ')),
                     on: [...document.querySelectorAll('.chips button')].filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.getAttribute('data-k')), ck: T.every(t => /\d+\/\d+ (\d+시 확인|가격)$/.test(t.querySelector('.ck').textContent)),
                     row: r.length < 3 || r[0].top === r[2].top && Math.abs(r[0].width - r[2].width) < 1, rel: T.every(t => /nofollow/.test(t.rel) && /sponsored/.test(t.rel) && t.target === '_blank'), sw: document.documentElement.scrollWidth }; }, k);
          assert.ok(v.n > 0 && v.n <= 12 && v.dn === v.n && v.k && v.on.join() === k && v.ck && v.row && v.rel && v.sw <= 390, '칩 ' + k + ' ' + JSON.stringify(v));
        }
        await p.click('.chips button[data-k="all"]').catch(() => {});
        if (ua === IOS) { await p.evaluate(() => scrollTo(0, 0)); const f = path.join(tmp, `lk${rl.length}.png`); await p.screenshot({ path: f }); rl.push([f, `/link?v=${st} ${st === 'a' ? 'A' : 'B'} 390${dark ? ' 다크' : ''}`]); }
        assert.deepStrictEqual(err, [], '/link 오류 X ' + u); await c.close();
      }
    }
    const rd = [], rc = [];
    for (const [w, h, ua, url, dark, name, lay = 'b', sc = 0] of [[360, 780, AND, '/', false, '홈 360'], [390, 844, IOS, '/', false, '홈 390'], [412, 915, AND, '/', false, '홈 412'], [390, 660, IOS, '/', false, '홈 390×660'],
                                                [360, 780, AND, '/', true, '홈 360 다크'], [390, 844, IOS, '/', true, '홈 390 다크'], [412, 915, AND, '/', true, '홈 412 다크'], [390, 844, IOS, '/c/', false, '카테고리 390'], [390, 844, IOS, '/c/coupang/', false, '쿠팡 쪽 390'], [390, 844, IOS, '/alarm/', false, '알림 390'], [390, 844, IOS, '/c/life/', false, '생필품 쪽 390'], [390, 844, IOS, '/p/' + p0, false, '딜 쪽 390'],
                                                [360, 780, AND, '/', false, '홈 A 목록형 360', 'a'], [390, 844, IOS, '/', false, '홈 A 목록형 390', 'a'], [412, 915, AND, '/', true, '홈 A 목록형 412 다크', 'a'],
                                                [360, 780, AND, '/', false, '홈 C 혼합형 360', 'c'], [390, 844, IOS, '/', false, '홈 C 혼합형 390', 'c'], [412, 915, AND, '/', false, '홈 C 혼합형 412', 'c'], [390, 660, IOS, '/', false, '홈 C 390×660', 'c'],
                                                [360, 780, AND, '/', true, '홈 C 360 다크', 'c'], [390, 844, IOS, '/', true, '홈 C 390 다크', 'c'], [412, 915, AND, '/', true, '홈 C 412 다크', 'c'],
                                                [390, 844, IOS, '/', false, 'TOP/END 390', 'c', 1.5], [390, 844, IOS, '/', true, 'TOP/END 390 다크', 'b', 1.5], [390, 844, IOS, '/c/life/', false, 'TOP/END 생필품 쪽 390', 'b', 1.5]]) {
      const c4 = await browser.newContext({ viewport: { width: w, height: h }, userAgent: ua, isMobile: true, hasTouch: true, deviceScaleFactor: 2, colorScheme: dark ? 'dark' : 'light' }, lay), p4 = await c4.newPage();
      await p4.addInitScript(() => { try { localStorage.setItem('instx', String(Date.now())); } catch (e) {} });
      await p4.goto(U + url, { waitUntil: 'load' }); if (sc) await p4.evaluate(k => scrollTo(0, innerHeight * k), sc); await p4.waitForTimeout(300);
      const to = /^(홈 C|TOP\/END)/.test(name) ? rc : rd, f = path.join(tmp, `rd${rd.length}_${rc.length}.png`); await p4.screenshot({ path: f }); to.push([f, name]); await c4.close();
    }
    const SHEET = `
import json, sys
from PIL import Image, ImageDraw
sys.path.insert(0, ${JSON.stringify(__dirname)})
import cards
shots, out = json.loads(sys.argv[1]), sys.argv[2]
ims = [Image.open(f).convert("RGB") for f, _ in shots]
G, top = 32, 72
c = Image.new("RGB", (sum(i.width for i in ims) + G * (len(ims) + 1), top + max(i.height for i in ims) + G), (226, 229, 234)); d = ImageDraw.Draw(c); f = cards.pf("Bold", 30); x = G
for im, (_, t) in zip(ims, shots):
    d.text((x, 22), t, font=f, fill=(20, 22, 27)); c.paste(im, (x, top)); x += im.width + G
c.save(out, optimize=True)
`;
    for (const [sh, n] of [[rd, 'redesign_preview.png'], [rc, 'layout_c_preview.png'], [rl, 'link_preview.png']]) require('child_process').execFileSync('python3', ['-c', SHEET, JSON.stringify(sh), path.join(ROOT, 'cards', n)]);  // C 혼합형·TOP/END(10/25) = 따로 한 장

    require('child_process').execFileSync('python3', ['-c', `
import json, sys
from PIL import Image, ImageDraw
sys.path.insert(0, ${JSON.stringify(__dirname)})
import cards
shots, out, icons = json.loads(sys.argv[1]), sys.argv[2], sys.argv[3]
ims = [Image.open(f).convert("RGB") for f, _ in shots]
G, top = 24, 56
W = sum(i.width for i in ims) + G * (len(ims) + 1)
H = top + max(i.height for i in ims) + 190
c = Image.new("RGB", (W, H), (226, 229, 234)); d = ImageDraw.Draw(c); f = cards.pf("Bold", 22); x = G
for im, (_, t) in zip(ims, shots):
    d.text((x, 18), t, font=f, fill=(25, 31, 40)); c.paste(im, (x, top)); x += im.width + G
def mask(im, kind, r=.22):
    m = Image.new("L", im.size, 0); dd = ImageDraw.Draw(m)
    if kind == "c": dd.ellipse((0, 0, im.width - 1, im.height - 1), fill=255)
    else: dd.rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=int(im.width * r), fill=255)
    o = Image.new("RGBA", im.size, (0, 0, 0, 0)); o.paste(im, (0, 0), m); return o
def phone(n, k=96):  # 안드로이드가 보여 주는 부분: 크롬이 maskable 안전 영역(80%)을 66/108에 맞추고 런처는 가운데 72/108만 -> 원본 0.0636~0.9364
    im = Image.open(icons + "/" + n).convert("RGBA"); a, b = round(im.width * .0636), round(im.width * .9364)
    return im.crop((a, a, b, b)).resize((k, k), Image.LANCZOS)
def legacy(n, k=96):  # 바로가기 아이콘 = 크롬이 'any' 비트맵 그대로 -> 픽셀(Launcher3)은 흰 원 위에 0.807×0.7 ≈ 0.565로 줄여 둠(안 깎음)
    o = Image.new("RGBA", (k, k), (0, 0, 0, 0)); ImageDraw.Draw(o).ellipse((0, 0, k - 1, k - 1), fill=(255, 255, 255, 255)); s = round(k * .565)
    o.paste(Image.open(icons + "/" + n).convert("RGBA").resize((s, s), Image.LANCZOS), ((k - s) // 2, (k - s) // 2)); return o
def badge(im):  # 크롬 '바로가기' 배지 = 픽셀(Launcher3) 아이콘 오른쪽 아래 0.444(ICON_BADGE_SCALE)
    im = im.copy(); dd = ImageDraw.Draw(im); w = im.width; s = round(w * .444)
    dd.ellipse((w - s, w - s, w - 1, w - 1), fill=(255, 255, 255, 255)); dd.ellipse((w - s + 3, w - s + 3, w - 4, w - 4), fill=(66, 133, 244, 255)); return im
y = top + max(i.height for i in ims) + 24
d.text((G, y), "아이콘(A 레드, 96·48px): 192 · 512 · 안드로이드 원 · 스쿼클 · 애플 둥근 네모 · 크롬 '바로가기' 배지(픽셀 크기 — 앱 설치는 배지 X) · 48px · 파비콘 32 · 바로가기 특가·대기·생필품(파일 · 픽셀 런처 = 흰 원 안 작은 네모)", font=f, fill=(25, 31, 40))
z = lambda n, k=96: Image.open(icons + "/" + n).convert("RGBA").resize((k, k), Image.LANCZOS)
ic = [z("icon-192.png"), z("icon-512.png"), mask(phone("icon-512-maskable.png"), "c"), mask(phone("icon-512-maskable.png"), "r", .35),
      mask(z("apple-touch-icon.png"), "r", .2237), badge(mask(phone("icon-512-maskable.png"), "c")), mask(phone("icon-512-maskable.png", 48), "c"),
      Image.open(icons + "/favicon-32.png").convert("RGBA")] + [z(f"sc-{k}-96.png") for k in ("fire", "wait", "life")] + [legacy(f"sc-{k}.png") for k in ("fire", "wait", "life")]
x = G
for im in ic: c.paste(im, (x, y + 40 + (96 - im.height) // 2), im); x += im.width + 24
c.save(out, optimize=True)
`, JSON.stringify(shots), path.join(ROOT, 'cards', 'pwa_preview.png'), path.join(ROOT, 'icons')]);
    console.log('OK: 웹앱 셀프체크 통과');
  } finally {
    await browser.close();
    server.close();
  }
})().catch(e => { console.error(e); process.exit(1); });
