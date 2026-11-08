import { validateCard } from './validation.mjs';

const state = window.__FILL__ = { status: 'loading', imageFailures: [], warnings: [] };
const card = document.getElementById('card');
const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
};
const short = value => {
  const m = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}:\d{2})/.exec(value);
  return m ? `${+m[2]}/${+m[3]} ${m[4]}` : value;
};

async function json(url) {
  const response = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(12000) });
  if (!response.ok) throw new Error(`파일을 읽지 못했습니다: ${url} (${response.status})`);
  return response.json();
}

function imageReady(image, src) {
  return new Promise(resolve => {
    let done = false;
    const finish = reason => {
      if (done) return;
      done = true; clearTimeout(timer); image.onload = image.onerror = null;
      resolve(reason);
    };
    const timer = setTimeout(() => finish('timeout'), 8000);
    image.onload = async () => {
      try { await image.decode(); finish(image.naturalWidth ? null : 'empty'); }
      catch { finish('decode'); }
    };
    image.onerror = () => finish('load');
    image.src = src;
  });
}

async function productImage(frame, item, index) {
  const fallback = el('span', 'image-placeholder', '이미지 없음');
  fallback.dataset.testid = 'image-fallback';
  frame.append(fallback);
  if (!item.img) { state.imageFailures.push({ index, name: item.name, reason: 'missing' }); return; }
  const image = el('img');
  image.alt = item.name; image.referrerPolicy = 'no-referrer';
  const reason = await imageReady(image, /^https:/.test(item.img) ? item.img : `../${item.img}`);
  if (reason) {
    image.removeAttribute('src');
    state.imageFailures.push({ index, name: item.name, reason });
  } else { fallback.hidden = true; frame.append(image); }
}

async function init() {
  try {
    const file = new URLSearchParams(location.search).get('data');
    if (!/^data\/[A-Za-z0-9_-]+\.json$/.test(file)) throw new Error('data/ 안의 상품 JSON 경로를 지정해 주세요.');
    const result = validateCard(await json(`../${file}`));
    if (!result.ok) throw new Error(result.draft ? '빈 초안입니다. 확인한 상품 정보를 먼저 입력해 주세요.' : result.errors.map(e => e.message).join(' / '));
    const data = result.data;
    state.warnings = result.warnings ?? [];
    const template = `${data.mall}-${data.items.length}`;
    const layout = await json(`tpl/${template}.json`);
    if (layout.rows.length !== data.items.length || layout.size[0] !== 1080 || layout.size[1] !== 1350) throw new Error('템플릿의 상품 수 또는 크기가 맞지 않습니다.');
    const background = new Image();
    const backgroundURL = `tpl/${template}.png`;
    const backgroundPromise = imageReady(background, backgroundURL).then(reason => {
      if (reason) throw new Error(`템플릿 배경을 읽지 못했습니다: ${template} (${reason})`);
      card.style.backgroundImage = `url("${backgroundURL}")`;
    });
    card.dataset.mall = data.mall; card.dataset.count = String(data.items.length);
    const sub = el('p', 'sub', `${short(data.checked)} ${data.mall === 'toss' ? '게시 시점 가격' : '확인 가격'} · ${data.items.length}개의 픽`);
    sub.style.left = `${layout.sub.cx}px`; sub.style.top = `${layout.sub.cy}px`;
    card.append(sub);
    const waits = data.items.map((item, index) => {
      const { top, bottom } = layout.rows[index];
      const row = el('section', 'fill-row'); row.dataset.testid = 'product';
      row.style.top = `${top}px`; row.style.height = `${bottom - top}px`;
      if ([...item.cond].length > 4 || [...item.unit].length > 13 || item.price.length > 9 || (item.price.length > 7 && item.cond.length > 2)) row.classList.add('wide-offer');
      const photo = el('div', 'slot-photo');
      const info = el('div', 'slot-info');
      const name = el('h2', 'name'); name.dataset.testid = 'product-name'; name.dataset.overflowIgnore = 'true'; name.title = item.name;
      const link = el('a', '', item.name); link.href = item.url; link.target = '_blank'; link.rel = 'sponsored noopener noreferrer'; name.append(link); info.append(name);
      const offer = el('div', 'slot-offer');
      const priceLine = el('div', 'price-line');
      const price = el('strong', 'price', item.price); price.dataset.testid = 'product-price'; priceLine.append(price);
      if (item.cond) priceLine.append(el('span', 'chip', item.cond));
      offer.append(priceLine);
      if (item.unit) { const unit = el('p', 'unit', item.unit); unit.dataset.testid = 'product-unit'; offer.append(unit); }
      if (item.checked !== data.checked) info.append(el('p', 'when', `${short(item.checked)} 확인`));
      row.append(photo, info, offer); card.append(row);
      return productImage(photo, item, index);
    });
    if (data.mall === 'toss') card.append(el('p', 'posting-note', `⚠️ ${short(data.checked)} 게시 시점 가격 · 결제 전 최종가 확인 · 사진: 토스쇼핑`));  // 11/8 핫딜봇: 토스 원본 사진 출처
    const fonts = Promise.all([document.fonts.load('750 32px HotdealSans', '핫딜픽'), document.fonts.load('850 46px HotdealSans', '0123456789,원')]);
    await Promise.all([...waits, backgroundPromise, fonts]);
    await document.fonts.ready;
    if (!document.fonts.check('750 32px HotdealSans', '핫딜픽')) throw new Error('한글 글꼴을 읽지 못했습니다.');
    document.getElementById('frame').hidden = false;
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    for (const [index, name] of [...card.querySelectorAll('.name')].entries()) {
      if (name.scrollHeight > name.clientHeight + 1) state.warnings.push({ path: `items[${index}].name`, code: 'NAME_ELLIPSIS', message: '상품명이 두 줄을 넘어 말줄임했습니다. 전체 이름은 본문과 대체텍스트에 유지됩니다.' });
    }
    state.template = template; state.itemCount = data.items.length; state.status = 'ready';
  } catch (error) {
    document.getElementById('frame').hidden = true;
    const feedback = document.getElementById('feedback'); feedback.hidden = false; feedback.textContent = error.message;
    state.status = 'error'; state.error = error.message;
  }
}
init();
