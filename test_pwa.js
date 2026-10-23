// 웹앱(PWA) 셀프체크: node test_pwa.js  (docs/를 로컬 서버로 띄워 Playwright 크로미움으로 확인 — build_site.py 먼저)
// manifest 필드·아이콘 크기·서비스워커 등록·설치 가능(크롬 DevTools getInstallabilityErrors = 0)·오프라인(저장해 둔 홈)·설치 버튼(안드로이드·아이폰·앱 안 브라우저·설치됨·닫기 7일)
// · GoatCounter 웹앱 출처('app') · 지금 사이트 동작(탭·찜·검색) · 휴대폰 3종(360·393·412) 일반·앱 첫 화면 + 아이콘 48px -> docs/cards/pwa_preview.png 한 장. 마지막 줄 'OK: 웹앱 셀프체크 통과'
const http = require('http'), fs = require('fs'), path = require('path'), assert = require('assert');
const { chromium } = require('playwright');
const ROOT = path.join(__dirname, 'docs');
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.webmanifest': 'application/manifest+json', '.png': 'image/png', '.jpg': 'image/jpeg', '.ico': 'image/x-icon', '.json': 'application/json', '.xml': 'application/xml' };
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
    assert.deepStrictEqual([m.name, m.short_name, m.start_url, m.scope, m.display, m.lang, m.background_color, m.theme_color], ['핫딜픽 — 매일 살 만한 핫딜', '핫딜픽', '/?src=app', '/', 'standalone', 'ko', '#f4f5f7', '#f4f5f7']);
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
    assert.ok((await pg.title()).includes('핫딜픽') && (await pg.$('#wait')), '오프라인 홈');
    const p0 = fs.readdirSync(path.join(ROOT, 'p')).find(f => f.endsWith('.html'));
    await pg.goto(U + '/p/' + p0, { waitUntil: 'load' });
    assert.ok((await pg.title()).includes('오늘의 핫딜'), '오프라인 처음 여는 쪽 = 저장해 둔 홈');
    OFF = false;
    // 3) 지금 사이트 동작: 탭(칸 바꿈)·찜(localStorage)·검색
    await pg.goto(U + '/', { waitUntil: 'load' });
    const tab = h => pg.evaluate(h => document.querySelector(`nav.bar:not(.top) a[href="${h}"]`).click(), h);  // 아래 탭 줄(가로 스크롤 — 화면 밖 칸도 누르면 같음)
    await tab('#wait');
    assert.ok(await pg.evaluate(() => !document.getElementById('wait').closest('.pane').hidden), '탭 = 대기 칸');
    await tab('#hot');
    const lk = await pg.$('.pane:not([hidden]) .like');
    await lk.click();
    assert.strictEqual(await pg.evaluate(() => JSON.parse(localStorage.getItem('likes')).length), 1, '찜 1개');
    assert.strictEqual(await lk.getAttribute('aria-pressed'), 'true');
    await pg.fill('#q', '휴지');
    await pg.waitForTimeout(400);
    assert.ok(await pg.evaluate(() => { const qn = document.getElementById('qn'), n = document.querySelectorAll('#days .g:not([hidden])').length;
      return !qn.hidden && (n ? qn.textContent === n + '개 찾았어요' : /찾는 딜이 없어요/.test(qn.textContent)); }), '검색 결과 줄');
    // 4) GoatCounter 웹앱 출처: ?src=app = 'app', 경로는 ?src 뺌
    const gc = await pg.evaluate(js => { eval(js); return [window.goatcounter.path('/?src=app'), window.goatcounter.path('/?src=app&x=1'), window.goatcounter.path('/p/1.html')]; }, require('child_process').execSync("python3 -c \"import build_site; print(build_site.GC_APP)\"").toString());
    assert.deepStrictEqual(gc, ['/', '/?x=1', '/p/1.html']);
    const ref = await pg.evaluate(js => { history.replaceState(null, '', '/?src=app'); eval(js); return window.goatcounter.referrer('https://www.instagram.com/'); }, require('child_process').execSync("python3 -c \"import build_site; print(build_site.GC_APP)\"").toString());
    assert.strictEqual(ref, 'app');
    // GoatCounter 실제 태그(10/23 hotdealpick): 바깥 count.js는 서비스워커가 안 막음(가짜 count.js가 실행됨) · 구매 링크 클릭 = 이벤트 buy/몰 주소 · ?ref=th 출처는 그대로('app'으로 안 바꿈 — count.js가 location.search를 보냄)
    await ctx.route(/\/\/gc\.zgo\.at\/count\.js/, r => r.fulfill({ contentType: 'text/javascript', body: 'window.__gcl=1;goatcounter.count=function(v){(window.__gc=window.__gc||[]).push(v)}' }));
    await pg.goto(U + '/?ref=th', { waitUntil: 'load' });
    await pg.waitForFunction(() => window.__gcl === 1 && navigator.serviceWorker.controller);
    assert.strictEqual(await pg.getAttribute('script[data-goatcounter]', 'data-goatcounter'), 'https://hotdealpick.goatcounter.com/count');
    assert.strictEqual(await pg.evaluate(() => goatcounter.referrer('https://www.threads.net/')), 'https://www.threads.net/');
    const buy = await pg.evaluate(() => { const a = document.querySelector('a[rel~="nofollow"][href^="http"]'); a.addEventListener('click', e => e.preventDefault()); a.click(); return [new URL(a.href).hostname, window.__gc]; });
    assert.ok(buy[1] && buy[1].some(v => v.event === true && v.path === 'buy/' + buy[0]), JSON.stringify(buy));
    await ctx.close();
    // 5) 설치 버튼: 안드로이드 크롬 = beforeinstallprompt -> 설치 / 아이폰 = 2줄 안내 / 앱 안 브라우저 = 브라우저 안내 / 설치됨 = 숨김 / 닫기 = 7일
    const show = async (opt, init, fire) => {
      const c = await browser.newContext(opt), p = await c.newPage();
      if (init) await p.addInitScript(init);
      await p.goto(U + '/', { waitUntil: 'load' });
      if (fire) await p.evaluate(() => { const e = new Event('beforeinstallprompt'); e.prompt = () => { window.__prompted = 1; }; e.userChoice = Promise.resolve({ outcome: 'accepted' }); dispatchEvent(e); });
      const r = await p.evaluate(() => ({ shown: !document.getElementById('inst').hidden, text: document.getElementById('instt').textContent, btn: !document.getElementById('instb').hidden }));
      return [r, c, p];
    };
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
    // 6) 휴대폰 기준(10/23 진우 '모바일이 중요'): 360(갤럭시 S)·393(아이폰 15)·412(갤럭시 플러스) × 일반 브라우저·설치 앱(standalone) 첫 화면
    //    설치 띠 = 작은 띠(48~80px)·버튼 44px+·아래 고정 바·앱 안 탭 줄과 안 겹침·첫 딜이 첫 화면에 보임 · 노치·홈 바(safe-area) 여백 -> 한 장(docs/cards/pwa_preview.png)
    const AND = 'Mozilla/5.0 (Linux; Android 15; SM-S921N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36';
    const PHONES = [[360, 780, AND, 'Galaxy S 360'], [393, 852, IOS, 'iPhone 15 393'], [412, 915, AND, 'Galaxy+ 412']];
    const shots = [], tmp = fs.mkdtempSync(path.join(require('os').tmpdir(), 'pwa'));
    const layout = p => p.evaluate(() => {
      const R = e => e && getComputedStyle(e).display !== 'none' && !e.hidden ? e.getBoundingClientRect() : null, i = document.getElementById('inst');
      const g = [...document.querySelectorAll('.pane:not([hidden]) .g')].map(x => x.getBoundingClientRect())[0];
      return { inst: R(i), btn: R(document.getElementById('instb')), x: R(document.getElementById('instx')), bottom: R(document.querySelector('nav.bar:not(.top)')), top: R(document.querySelector('nav.bar.top')), g, vh: innerHeight,
               pb: parseFloat(getComputedStyle(document.querySelector('nav.bar:not(.top)')).paddingBottom), pt: parseFloat(getComputedStyle(document.querySelector('main')).paddingTop) };
    });
    const over = (a, b) => a && b && a.top < b.bottom && b.top < a.bottom;
    for (const [w, h, ua, name] of PHONES) for (const app of [false, true]) {
      const c2 = await browser.newContext({ viewport: { width: w, height: h }, userAgent: ua, isMobile: true, hasTouch: true, deviceScaleFactor: 1 }), p2 = await c2.newPage();
      if (app) await p2.addInitScript(STANDALONE);
      let safe = false;
      if (app && ua === IOS) try { const s = await c2.newCDPSession(p2); await s.send('Emulation.setSafeAreaInsetsOverride', { insets: { top: 0, bottom: 34, left: 0, right: 0 } }); safe = true; } catch (e) {}  // 아이폰 홈 바(크롬 DevTools가 지원하면)
      await p2.goto(U + (app ? '/?src=app' : '/'), { waitUntil: 'load' });
      if (!app && ua === AND) await p2.evaluate(() => { const e = new Event('beforeinstallprompt'); e.prompt = () => {}; e.userChoice = Promise.resolve({}); dispatchEvent(e); });
      const L = await layout(p2), tag = `${name} ${app ? '앱' : '브라우저'}`;
      if (app) assert.ok(!L.inst, tag + ': 설치 앱 = 띠 없음');
      else {
        assert.ok(L.inst && L.inst.height >= 48 && L.inst.height <= 80 && L.inst.top < 220, tag + ' 띠 ' + JSON.stringify(L.inst));
        assert.ok(L.x.width >= 44 && L.x.height >= 44 && (!L.btn || L.btn.height >= 44), tag + ' 버튼 44px+');
        assert.ok(!over(L.inst, L.bottom) && !over(L.inst, L.top), tag + ' 띠가 고정 바와 안 겹침');
      }
      assert.ok(L.g && L.g.top < L.vh - (L.bottom ? L.bottom.height : 0) - 40, tag + ' 첫 딜이 첫 화면에 ' + JSON.stringify([L.g, L.vh]));
      if (safe) assert.ok(L.pb >= 40, tag + ' 홈 바 여백 ' + L.pb);
      const f = path.join(tmp, `${w}${app ? 'a' : 'b'}.png`);
      await p2.screenshot({ path: f });
      shots.push([f, tag + (safe ? ' (홈 바 34px)' : '')]);
      await c2.close();
    }
    const c3 = await browser.newContext({ viewport: { width: 390, height: 844 }, userAgent: IG, isMobile: true, hasTouch: true }), p3 = await c3.newPage();  // 앱 안 브라우저(인스타) — 띠 + 위 탭 줄
    await p3.goto(U + '/', { waitUntil: 'load' });
    const L3 = await layout(p3);
    assert.ok(L3.inst && L3.top && !over(L3.inst, L3.top) && !L3.bottom, '앱 안: 띠·탭 줄 안 겹침 ' + JSON.stringify([L3.inst, L3.top]));
    await p3.evaluate(() => scrollTo(0, 600)); const L4 = await layout(p3);
    assert.ok(!over(L4.inst, L4.top) || L4.inst.bottom <= 0, '앱 안: 내려도 탭 줄이 띠를 안 덮음');
    await c3.close();
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
