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
const P = { paper: '#F8FAF7', mint: '#E8F4F1', teal: '#426765', navy: '#223845', red: '#F33430', yellow: '#F4CF59', muted: '#647B7A', line: '#D8E4DF', white: '#FFFFFF', soft: '#F0F7F3', track: '#EDF1ED', grey: '#A8BAB8' };
const esc = s => String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const t = (x, y, s, size = 28, weight = 400, color = P.navy, anchor = 'start') => `<text x="${x}" y="${y}" font-size="${size}" font-weight="${weight}" fill="${color}" text-anchor="${anchor}">${esc(s)}</text>`;
const r = (x, y, w, h, fill, rx = 0, stroke = 'none') => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="${fill}" stroke="${stroke}"/>`;
const line = (x1, y1, x2, y2, color = P.line, width = 1) => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-width="${width}"/>`;
const image = (src, x, y, w, h) => src ? `<image href="${src}" x="${x}" y="${y}" width="${w}" height="${h}" preserveAspectRatio="xMidYMid meet"/>` : '';
const photo = (src, x, y, w, h) => src ? r(x, y, w, h, P.white, 18, P.line) + image(src, x + 10, y + 10, w - 20, h - 20) : '';  // 상품 사진 칸(흰 바탕 그대로 · 다시 그리기 X)
const logo = S.logo ? image(S.logo, 64, 105, 52, 52) + t(126, 145, '핫딜픽', 29, 700) : r(64, 111, 44, 46, P.red, 12) + t(86, 145, '딜', 30, 700, P.white, 'middle') + t(122, 145, '핫딜픽', 29, 700);
const base = (n, label) => `<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350"><title>핫딜픽 ${esc(label)}</title><style>text{font-family:'Noto Sans CJK KR','Noto Sans KR',sans-serif;font-kerning:normal;letter-spacing:-.6px}</style>`
  + r(0, 0, 1080, 1350, P.paper) + t(64, 34, S.disclosure[0], 22, 400, P.muted) + t(64, 64, S.disclosure[1], 22, 400, P.muted) + line(64, 87, 1016, 87) + logo + t(1016, 143, `${String(n).padStart(2, '0')} / 04`, 22, 400, P.teal, 'end');
const footer = () => line(64, 1245, 1016, 1245) + t(64, 1283, 'hotdealpick.kr', 25, 700, P.teal) + t(1016, 1283, S.foot, 21, 400, P.muted, 'end') + t(64, 1320, '구매 전 배송비·쿠폰 조건과 최종 결제 금액을 확인하세요.', 21, 400, P.muted) + '</svg>';
const kicker = s => t(64, 219, s, 23, 500, P.teal);
const its = S.items, top3 = its.slice(0, 3);

let cover = base(1, S.title.join(' ')) + kicker(S.kicker);
cover += t(60, 309, S.title[0], 76, 700) + t(60, 399, S.title[1], 70, 700, P.teal);
cover += `<path d="M66 423 Q300 410 632 422" fill="none" stroke="${P.yellow}" stroke-width="9" stroke-linecap="round"/>`;
cover += t(64, 547, its[0].unit, 92, 700, P.red) + t(64 + S.loW, 536, '—', 63, 400, P.muted, 'middle') + t(64 + S.loW + 90, 547, its.at(-1).unit, 92, 700, P.navy);
cover += t(64, 594, `비교한 ${S.n}종 · ${S.label} 기준`, 26, 400, P.muted) + t(1016, 594, `약 ${S.ratio}배 차이`, 28, 700, P.teal, 'end');
cover += r(64, 638, 952, 442, P.mint, 30) + t(94, 692, `${S.label} 낮은 순`, 25, 700, P.teal);
top3.forEach((p, i) => { const y = 762 + i * 99; cover += t(94, y, String(i + 1).padStart(2, '0'), 22, 500, P.muted) + t(142, y, p.short, 29, 500) + t(142, y + 39, p.unit, 40, 700, i === 0 ? P.red : P.teal); });
cover += photo(its[0].img, 620, 676, 366, 366) + t(64, 1151, S.coverNote[0], 32, 500) + t(64, 1194, S.coverNote[1], 32, 500, P.teal) + footer();

let chart = base(2, `${S.label} 가격 비교`) + kicker(`PRICE CHECK  /  ${S.label} 기준`);
chart += t(64, 300, '같은 기준으로 놓고,', 64, 700) + t(64, 379, '가격만 비교했어요.', 64, 700, P.teal) + t(64, 433, S.chartNote, 27, 400, P.muted);
const x0 = 118, plotW = 898, rowH = Math.min(101, Math.floor(600 / its.length)), startY = 503;
its.forEach((p, i) => {
  const y = startY + i * rowH, col = i === 0 ? P.red : i < 3 ? P.teal : P.grey;
  chart += t(64, y, String(i + 1).padStart(2, '0'), 23, 400, P.muted) + t(x0, y, p.name, rowH < 90 ? 26 : 30, 500) + t(1016, y, p.unit, rowH < 90 ? 34 : 40, 700, i === 0 ? P.red : P.teal, 'end');
  chart += r(x0, y + 17, plotW, 17, P.track, 5) + r(x0, y + 17, Math.max(4, p.uv / S.axis.max * plotW), 17, col, 5);
  if (rowH >= 80) chart += t(x0, y + 62, p.sub, 21, 400, P.muted);
});
const ay = startY + its.length * rowH + 20;
chart += line(x0, ay, 1016, ay);
S.axis.ticks.forEach((tick, k) => { const x = x0 + tick / S.axis.max * plotW; chart += line(x, ay, x, ay + 8, P.muted) + t(x, ay + 35, S.axis.labels[k], 20, 400, P.muted, k === 0 ? 'start' : k === S.axis.ticks.length - 1 ? 'end' : 'middle'); });
chart += t(64, 1213, S.formula, 23, 400, P.muted) + footer();

let table = base(3, `${S.query} 판매가 표`) + kicker('PRICE LIST  /  표시 판매가 함께 보기');
table += t(64, 300, '살 때 내는 가격도', 64, 700) + t(64, 379, '함께 확인하세요.', 64, 700, P.teal) + t(64, 432, '구성·수량과 로켓배송 표시까지 같은 줄에 담았어요.', 26, 400, P.muted);
const th = Math.min(109, Math.floor(650 / its.length)), tw = th >= 90;
table += r(64, 475, 952, 59 + th * its.length + 6, P.white, 24, P.line) + r(65, 476, 950, 59, P.mint, 22) + r(65, 505, 950, 30, P.mint);
table += t(92, 514, '순', 23, 500, P.teal) + t(tw ? 236 : 147, 514, '상품 · 구성', 23, 500, P.teal) + t(792, 514, '판매가', 23, 500, P.teal, 'end') + t(990, 514, S.label, 23, 500, P.teal, 'end');
its.forEach((p, i) => {
  const y = 535 + i * th;
  if (i < 3) table += r(65, y, 950, th, P.soft);
  if (i > 0) table += line(84, y, 996, y);
  const nx = tw ? 236 : 147;
  if (tw) table += photo(p.img, 138, y + 8, th - 16, th - 16);
  table += t(100, y + th / 2 + 4, String(i + 1).padStart(2, '0'), 23, 400, P.muted, 'middle') + t(nx, y + th * 0.42, p.tname, tw ? 28 : 24, 500) + t(nx, y + th * 0.76, p.sub, tw ? 21 : 19, 400, P.muted)
    + t(792, y + th / 2 + 10, p.price, tw ? 36 : 30, 500, P.navy, 'end') + t(990, y + th / 2 + 10, p.unit, tw ? 36 : 30, 700, i === 0 ? P.red : P.teal, 'end');
});
table += t(64, 1222, S.tableNote, 22, 400, P.muted) + footer();

let faq = base(4, `${S.query} 구매 전 확인사항`) + kicker('SHOPPING NOTE  /  구매 전 확인');
faq += t(64, 300, '사기 전에,', 64, 700) + t(64, 379, '세 가지만 확인해요.', 64, 700, P.teal) + image(S.duo, 767, 218, 249, 166);
S.tips.forEach((q, i) => { const y = 492 + i * 220; faq += t(64, y, String(i + 1).padStart(2, '0'), 44, 400, P.teal) + t(151, y - 10, q[0], 22, 500, P.muted) + t(151, y + 39, q[1], 36, 700) + t(151, y + 88, q[2], 26, 400, P.teal) + t(151, y + 128, q[3], 26, 400, P.teal); if (i < 2) faq += line(151, y + 164, 1016, y + 164); });
faq += r(64, 1175, 952, 45, P.mint, 11) + t(540, 1207, S.strip, 25, 500, P.teal, 'middle') + footer();

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
