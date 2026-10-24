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
    const buy = await pg.evaluate(() => { const a = document.querySelector('a[rel~="nofollow"][href^="http"]'); a.addEventListener('click', e => e.preventDefault()); a.click(); const u = new URL(a.href); return [u.hostname + u.pathname, window.__gc, u.search]; });
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
      const r = await p.evaluate(() => ({ shown: !document.getElementById('inst').hidden, text: document.getElementById('instt').textContent, btn: !document.getElementById('instb').hidden }));
      return [r, c, p];
    };
    const c0 = await browser.newContext({ viewport: { width: 412, height: 915 } }), p0a = await c0.newPage();  // 첫 방문 = 띠 X, 같은 탭 새로 고침도 X(세션 1번), 새 탭(두 번째 방문) = 보임
    const fire0 = () => p0a.evaluate(() => { const e = new Event('beforeinstallprompt'); e.prompt = () => {}; e.userChoice = Promise.resolve({}); dispatchEvent(e); });
    await p0a.goto(U + '/', { waitUntil: 'load' }); await fire0();
    assert.ok(await p0a.evaluate(() => document.getElementById('inst').hidden), '첫 방문 = 설치 띠 X');
    await p0a.reload({ waitUntil: 'load' }); await fire0();
    assert.ok(await p0a.evaluate(() => document.getElementById('inst').hidden), '같은 방문(새로 고침) = 띠 X');
    const p0b = await c0.newPage(); await p0b.goto(U + '/', { waitUntil: 'load' });
    await p0b.evaluate(() => { const e = new Event('beforeinstallprompt'); e.prompt = () => {}; e.userChoice = Promise.resolve({}); dispatchEvent(e); });
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
    await p.reload({ waitUntil: 'load' });
    assert.ok(await p.evaluate(() => document.getElementById('inst').hidden && +localStorage.getItem('instx') > 0), '닫으면 7일 안 보임');
    await p.evaluate(() => localStorage.setItem('instx', Date.now() - 8 * 864e5)); await p.reload({ waitUntil: 'load' });
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
      await p6.addInitScript(() => { try { localStorage.setItem('instx', String(Date.now() + 9e8)); } catch (e) {} });
      await p6.goto(U + '/', { waitUntil: 'load' });
      const F = await p6.evaluate(() => { const nav = document.querySelector('nav.nav').getBoundingClientRect().top, B = s => { const e = document.querySelector(s); return e ? e.getBoundingClientRect().bottom : null; };
        return { nav, sb: B('.sb'), evb: B('.evb'), qk: B('.qk'), rows: [...document.querySelectorAll('#fire .rows:not([hidden]) .r')].filter(e => e.getBoundingClientRect().bottom <= nav).length, bub: !!document.querySelector('.qk .qb') }; });
      assert.ok(F.sb && F.qk && F.qk < F.nav && F.rows >= (F.evb ? 2 : 3), '390×660 첫 화면 ' + JSON.stringify(F));
      await p6.evaluate(() => scrollTo(0, 600)); await p6.waitForTimeout(100);
      const st = await p6.evaluate(() => [document.querySelector('.sb').getBoundingClientRect().top, document.querySelector('.hr').getBoundingClientRect().bottom]);
      assert.ok(st[0] >= -1 && st[0] <= 8 && st[1] <= 1, '밀면 로고 줄은 사라지고 검색칸만 위에 ' + JSON.stringify(st));
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
               evb: R(document.querySelector('.evb')), sb: R(document.querySelector('.sb')) };
    });
    const over = (a, b) => a && b && a.top < b.bottom && b.top < a.bottom;
    for (const [w, h, ua, name] of PHONES) for (const app of [false, true]) {
      const c2 = await browser.newContext({ viewport: { width: w, height: h }, userAgent: ua, isMobile: true, hasTouch: true, deviceScaleFactor: 1 }), p2 = await c2.newPage();
      if (app) await p2.addInitScript(STANDALONE); else await p2.addInitScript(V2);
      let safe = false;
      if (app && ua === IOS) try { const s = await c2.newCDPSession(p2); await s.send('Emulation.setSafeAreaInsetsOverride', { insets: { top: 0, bottom: 34, left: 0, right: 0 } }); safe = true; } catch (e) {}  // 아이폰 홈 바(크롬 DevTools가 지원하면)
      await p2.goto(U + (app ? '/?src=app' : '/'), { waitUntil: 'load' });
      if (!app && ua === AND) await p2.evaluate(() => { const e = new Event('beforeinstallprompt'); e.prompt = () => {}; e.userChoice = Promise.resolve({}); dispatchEvent(e); });
      const L = await layout(p2), tag = `${name} ${app ? '앱' : '브라우저'}`;
      if (app) assert.ok(!L.inst, tag + ': 설치 앱 = 띠 없음');
      else {
        assert.ok(L.inst && L.inst.height >= 48 && L.inst.height <= 80 && L.inst.bottom <= L.vh - (L.bottom ? L.bottom.height : 0), tag + ' 띠(아래 메뉴 위 얇게) ' + JSON.stringify(L.inst));
        assert.ok(L.x.width >= 44 && L.x.height >= 44 && (!L.btn || L.btn.height >= 44), tag + ' 버튼 44px+');
        assert.ok(!over(L.inst, L.bottom) && !over(L.inst, L.top), tag + ' 띠가 고정 바와 안 겹침');
      }
      assert.ok(L.g && L.g.top < L.vh - (L.bottom ? L.bottom.height : 0) - 40, tag + ' 실시간 핫딜 1번이 첫 화면에 ' + JSON.stringify([L.g, L.vh]));
      assert.ok(L.qk && L.sb && L.qk.bottom <= L.vh && L.q1 >= 6 && L.q2 === 13 && L.rows >= (w >= 390 ? 4 : 3), tag + ' 첫 화면 = 검색·바로가기 2줄(6개+)·핫딜 줄 4개↑(포털형 2차) ' + JSON.stringify([L.rows, L.qk, L.q1, L.vh]));
      assert.ok(await p2.evaluate(() => document.documentElement.scrollWidth <= innerWidth), tag + ' 옆으로 안 넘침');
      if (safe) assert.ok(L.pb >= 40, tag + ' 홈 바 여백 ' + L.pb);
      const f = path.join(tmp, `${w}${app ? 'a' : 'b'}.png`);
      await p2.screenshot({ path: f });
      shots.push([f, tag + (safe ? ' (홈 바 34px)' : '')]);
      await c2.close();
    }
    const c3 = await browser.newContext({ viewport: { width: 390, height: 844 }, userAgent: IG, isMobile: true, hasTouch: true }), p3 = await c3.newPage();  // 앱 안 브라우저(인스타) — 띠 + 헤더 아래 메뉴 한 줄
    await p3.addInitScript(V2); await p3.goto(U + '/', { waitUntil: 'load' });
    const L3 = await layout(p3);
    assert.ok(L3.inst && L3.top && !over(L3.inst, L3.top) && !L3.bottom, '앱 안: 띠·탭 줄 안 겹침 ' + JSON.stringify([L3.inst, L3.top]));
    await p3.evaluate(() => scrollTo(0, 600)); const L4 = await layout(p3);
    assert.ok(!over(L4.inst, L4.top) || L4.inst.bottom <= 0, '앱 안: 내려도 탭 줄이 띠를 안 덮음');
    await c3.close();
    const rd = [];
    for (const [w, h, ua, url, dark, name] of [[360, 780, AND, '/', false, '홈 360'], [390, 844, IOS, '/', false, '홈 390'], [412, 915, AND, '/', false, '홈 412'], [390, 660, IOS, '/', false, '홈 390×660'],
                                                [360, 780, AND, '/', true, '홈 360 다크'], [390, 844, IOS, '/', true, '홈 390 다크'], [412, 915, AND, '/', true, '홈 412 다크'], [390, 844, IOS, '/c/', false, '카테고리 390'], [390, 844, IOS, '/c/coupang/', false, '쿠팡 쪽 390'], [390, 844, IOS, '/alarm/', false, '알림 390'], [390, 844, IOS, '/c/life/', false, '생필품 쪽 390'], [390, 844, IOS, '/p/' + p0, false, '딜 쪽 390']]) {
      const c4 = await browser.newContext({ viewport: { width: w, height: h }, userAgent: ua, isMobile: true, hasTouch: true, deviceScaleFactor: 2, colorScheme: dark ? 'dark' : 'light' }), p4 = await c4.newPage();
      await p4.addInitScript(() => { try { localStorage.setItem('instx', String(Date.now())); } catch (e) {} });
      await p4.goto(U + url, { waitUntil: 'load' }); await p4.waitForTimeout(300);
      const f = path.join(tmp, `rd${rd.length}.png`); await p4.screenshot({ path: f }); rd.push([f, name]); await c4.close();
    }
    require('child_process').execFileSync('python3', ['-c', `
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
`, JSON.stringify(rd), path.join(ROOT, 'cards', 'redesign_preview.png')]);
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
