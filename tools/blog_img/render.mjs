// 블로그 사진 4장(11/12 진우 — hotdealpick-cards/hotdealpick-deicer-redesign-20261111 GPT 잡지형 틀): node tools/blog_img/render.mjs <spec.json> <출력 폴더>
// spec = hotdeal.blog_img_spec(blog_data 숫자·편집 문구 다 정해 둠 — 여기선 그리기만) -> 1~4.svg·png(1080×1350) · 글자·가격 = SVG 글자(이미지 생성 X) · 사진 = 받은 그대로(meet).
// 브라우저 = tools/card의 @playwright/test(카드와 같은 것 — tools/card 파일은 안 고침)
import { createRequire } from 'node:module';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const { chromium } = createRequire(path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../card/package.json'))('@playwright/test');

const [specPath, outDir] = process.argv.slice(2);
const S = JSON.parse(await readFile(specPath, 'utf8'));
const P = { paper: '#F8FAF7', mint: '#E8F4F1', teal: '#426765', navy: '#223845', red: '#F33430', yellow: '#F4CF59', muted: '#647B7A', ink2: '#3F5452', line: '#D8E4DF', white: '#FFFFFF', soft: '#F0F7F3', track: '#EDF1ED', grey: '#A8BAB8' };
const cut = (s, n) => [...String(s)].length > n ? [...String(s)].slice(0, n - 1).join('').trimEnd() + '…' : String(s);  // 글씨 키운 만큼 이름 자르기
const wrap2 = (s, n) => { const ws = String(s).split(' '); let a = ''; while (ws.length && [...(a ? a + ' ' + ws[0] : ws[0])].length <= n) a = a ? a + ' ' + ws.shift() : ws.shift(); if (!a) return [cut(s, n), '']; return [a, cut(ws.join(' '), n)]; };  // 표 이름 2줄(n자씩)
const esc = s => String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const t = (x, y, s, size = 28, weight = 400, color = P.navy, anchor = 'start') => `<text x="${x}" y="${y}" font-size="${size}" font-weight="${weight}" fill="${color}" text-anchor="${anchor}">${esc(s)}</text>`;
const r = (x, y, w, h, fill, rx = 0, stroke = 'none') => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="${fill}" stroke="${stroke}"/>`;
const line = (x1, y1, x2, y2, color = P.line, width = 1) => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-width="${width}"/>`;
const image = (src, x, y, w, h) => src ? `<image href="${src}" x="${x}" y="${y}" width="${w}" height="${h}" preserveAspectRatio="xMidYMid meet"/>` : '';
const photo = (src, x, y, w, h) => src ? r(x, y, w, h, P.white, 18, P.line) + image(src, x + 10, y + 10, w - 20, h - 20) : '';  // 상품 사진 칸(흰 바탕 그대로 · 다시 그리기 X)
const logo = S.logo ? image(S.logo, 64, 106, 58, 58) + t(134, 149, '핫딜픽', 34, 800) : r(64, 111, 44, 46, P.red, 12) + t(86, 145, '딜', 30, 700, P.white, 'middle') + t(122, 145, '핫딜픽', 29, 700);
const base = (n, label) => `<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350"><title>핫딜픽 ${esc(label)}</title><style>text{font-family:'Noto Sans CJK KR','Noto Sans KR',sans-serif;font-kerning:normal;letter-spacing:-.6px}</style>`
  + r(0, 0, 1080, 1350, P.paper) + t(64, 38, S.disclosure[0], 27, 500, P.ink2) + t(64, 73, S.disclosure[1], 27, 500, P.ink2) + line(64, 92, 1016, 92) + logo + t(1016, 143, `${String(n).padStart(2, '0')} / 04`, 27, 600, P.teal, 'end');
const footer = () => line(64, 1245, 1016, 1245) + t(64, 1286, 'hotdealpick.kr', 32, 800, P.teal) + t(1016, 1286, S.foot, 27, 500, P.ink2, 'end') + t(64, 1328, '구매 전 배송비·쿠폰 조건과 최종 결제 금액을 확인하세요.', 27, 500, P.ink2) + '</svg>';
const kicker = s => t(64, 219, s, 30, 600, P.teal);
const its = S.items, top3 = its.slice(0, 3);

let cover = base(1, S.title.join(' ')) + kicker(S.kicker);
cover += t(60, 309, S.title[0], 76, 700) + t(60, 399, S.title[1], 70, 700, P.teal);
cover += `<path d="M66 423 Q300 410 632 422" fill="none" stroke="${P.yellow}" stroke-width="9" stroke-linecap="round"/>`;
cover += t(64, 547, its[0].unit, 92, 700, P.red) + t(64 + S.loW, 536, '—', 63, 400, P.muted, 'middle') + t(64 + S.loW + 90, 547, its.at(-1).unit, 92, 700, P.navy);
cover += t(64, 598, `비교한 ${S.n}종 · ${S.label} 기준`, 33, 500, P.ink2) + t(1016, 598, `약 ${S.ratio}배 차이`, 35, 800, P.teal, 'end');
cover += r(64, 638, 952, 442, P.mint, 30) + t(94, 694, `${S.label} 낮은 순`, 30, 800, P.teal);
top3.forEach((p, i) => { const y = 768 + i * 100; cover += t(94, y, String(i + 1).padStart(2, '0'), 26, 600, P.ink2) + t(142, y, cut(p.short, 13), 33, 600) + t(142, y + 45, p.unit, 46, 800, i === 0 ? P.red : P.teal); });
cover += photo(its[0].img, 620, 676, 366, 366) + t(64, 1148, S.coverNote[0], 40, 700) + t(64, 1200, S.coverNote[1], 40, 700, P.teal) + footer();

let chart = base(2, `${S.label} 가격 비교`) + kicker(`PRICE CHECK  /  ${S.label} 기준`);
chart += t(64, 300, '같은 기준으로 놓고,', 64, 700) + t(64, 379, '가격만 비교했어요.', 64, 700, P.teal) + t(64, 438, S.chartNote, 32, 500, P.ink2);
const x0 = 118, plotW = 898, rowH = its.length <= 4 ? 150 : Math.floor(680 / its.length), sub = rowH >= 105, big = rowH >= 140, axis = its.length <= 4, startY = 503;  // 5개↑ = 눈금 빼고 그 자리까지 줄 간격으로
its.forEach((p, i) => {
  const y = startY + i * rowH, col = i === 0 ? P.red : i < 3 ? P.teal : P.grey;
  const by = y + (big ? 58 : sub ? 46 : 18);  // 한 상품 = 이름 → 구성(이름 바로 밑) → 막대
  if (i > 0 && !big) chart += line(64, y - 26 - Math.round((rowH - (sub ? 90 : 60)) / 2), 1016, y - 26 - Math.round((rowH - (sub ? 90 : 60)) / 2));  // 상품 사이 구분선
  chart += t(64, y, String(i + 1).padStart(2, '0'), 26, 600, P.ink2) + t(x0, y, cut(p.name, big ? 18 : 20), big ? 37 : 32, 600) + t(1016, y, p.unit, big ? 48 : 40, 800, i === 0 ? P.red : P.teal, 'end');
  if (sub) chart += t(x0, y + (big ? 42 : 34), p.sub, big ? 30 : 26, 500, P.ink2);
  chart += r(x0, by, plotW, big ? 22 : 18, P.track, 7) + r(x0, by, Math.max(4, p.uv / S.axis.max * plotW), big ? 22 : 18, col, 7);
});
const ay = startY + its.length * rowH + 10;
if (axis) chart += line(x0, ay, 1016, ay);
if (axis) S.axis.ticks.forEach((tick, k) => { const x = x0 + tick / S.axis.max * plotW; chart += line(x, ay, x, ay + 8, P.muted) + t(x, ay + 40, S.axis.labels[k], 27, 500, P.ink2, k === 0 ? 'start' : k === S.axis.ticks.length - 1 ? 'end' : 'middle'); });
chart += t(64, 1214, S.formula, 28, 500, P.ink2) + footer();

let table = base(3, `${S.query} 판매가 표`) + kicker('PRICE LIST  /  표시 판매가 함께 보기');
table += t(64, 300, '살 때 내는 가격도', 64, 700) + t(64, 379, '함께 확인하세요.', 64, 700, P.teal) + t(64, 438, '구성·수량과 로켓배송 표시까지 같은 줄에 담았어요.', 32, 500, P.ink2);
const th = its.length <= 4 ? 150 : Math.floor(640 / its.length), tw = th >= 90, two = th >= 140, ps = Math.min(th - 16, 112), nx = tw ? 154 + ps : 147;
table += r(64, 475, 952, 59 + th * its.length + 6, P.white, 24, P.line) + r(65, 476, 950, 59, P.mint, 22) + r(65, 505, 950, 30, P.mint);
table += t(92, 515, '순', 26, 700, P.teal) + t(nx, 515, '상품 · 구성', 26, 700, P.teal) + t(792, 515, '판매가', 26, 700, P.teal, 'end') + t(990, 515, S.label, 26, 700, P.teal, 'end');
its.forEach((p, i) => {
  const y = 535 + i * th;
  if (i < 3) table += r(65, y, 950, th, P.soft);
  if (i > 0) table += line(84, y, 996, y);
  if (tw) table += photo(p.img, 138, y + (th - ps) / 2, ps, ps);
  const nm = two ? wrap2(p.name.replace(/…$/, ''), 10) : [cut(p.tname, tw ? 12 : 15), ''];
  table += t(100, y + th / 2 + 6, String(i + 1).padStart(2, '0'), 26, 600, P.ink2, 'middle') + (two ? t(nx, y + 50, nm[0], 33, 700) + t(nx, y + 88, nm[1], 33, 700) + t(nx, y + 127, p.sub, 28, 500, P.ink2) : t(nx, y + th * 0.43, nm[0], tw ? 31 : 27, 600) + t(nx, y + th * 0.78, p.sub, tw ? 26 : 23, 500, P.ink2))
    + t(792, y + th / 2 + 13, p.price, two ? 38 : tw ? 37 : 31, 600, P.navy, 'end') + t(990, y + th / 2 + 13, p.unit, two ? 42 : tw ? 38 : 32, 800, i === 0 ? P.red : P.teal, 'end');
});
table += t(64, 1214, S.tableNote, 28, 500, P.ink2) + footer();

let faq = base(4, `${S.query} 구매 전 확인사항`) + kicker('SHOPPING NOTE  /  구매 전 확인');
faq += t(64, 300, '사기 전에,', 64, 700) + t(64, 379, '세 가지만 확인해요.', 64, 700, P.teal) + image(S.duo, 767, 218, 249, 166);
S.tips.forEach((q, i) => { const y = 486 + i * 228; faq += t(64, y + 4, String(i + 1).padStart(2, '0'), 50, 600, P.teal) + t(151, y - 14, q[0], 29, 600, P.ink2) + t(151, y + 40, q[1], 42, 800) + t(151, y + 94, q[2], 32, 500, P.teal) + t(151, y + 138, q[3], 32, 500, P.teal); if (i < 2) faq += line(151, y + 176, 1016, y + 176); });
faq += r(64, 1162, 952, 60, P.mint, 12) + t(540, 1204, S.strip, 32, 700, P.teal, 'middle') + footer();

await mkdir(outDir, { recursive: true });
const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
  for (const [n, svg] of [cover, chart, table, faq].entries()) {
    await writeFile(path.join(outDir, `${n + 1}.svg`), svg);
    await page.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;padding:0;background:${P.paper}}</style></head><body>${svg}</body></html>`, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: path.join(outDir, `${n + 1}.png`), clip: { x: 0, y: 0, width: 1080, height: 1350 } });
  }
} finally {
  await browser.close();
}
console.log(JSON.stringify({ pages: 4, n: its.length }));
