import { validateCard, MALLS } from './validation.mjs';

const state = window.__CARD_STATE__ = { status: 'loading', errors: [], warnings: [], imageFailures: [] };
const params = new URLSearchParams(location.search);
const isExport = params.get('export') === '1';
document.body.classList.toggle('export-mode', isExport);

const $ = (id) => document.getElementById(id);
const stage = $('card-stage');
const card = $('card');
const placeholderIcon = '<svg viewBox="0 0 36 36" fill="none" aria-hidden="true"><rect x="5" y="6" width="26" height="24" rx="5" stroke="currentColor" stroke-width="1.8"/><circle cx="13" cy="13" r="2.5" stroke="currentColor" stroke-width="1.8"/><path d="m6 25 7-7 5 5 5-6 7 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function shortTime(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}:\d{2})/.exec(value);
  return match ? `${Number(match[2])}/${Number(match[3])} ${match[4]}` : value;
}

function safeDataPath(value) {
  if (!value || !/^(?:data\/)?[A-Za-z0-9_-]+\.json$/.test(value)) return null;
  return value.startsWith('data/') ? value : `data/${value}`;
}

function updateScale() {
  if (isExport || stage.hidden) return;
  const scale = Math.min(1, Math.max(0.1, (document.documentElement.clientWidth - 24) / 1080));
  card.style.transform = `scale(${scale})`;
  stage.style.width = `${1080 * scale}px`;
  stage.style.height = `${1350 * scale}px`;
}
window.addEventListener('resize', updateScale);

function showFeedback(status, title, message, errors = []) {
  state.status = status;
  state.errors = errors;
  stage.hidden = true;
  $('feedback').hidden = false;
  $('feedback-title').textContent = title;
  $('feedback-message').textContent = message;
  $('feedback-details').replaceChildren(...errors.map((error) => element('li', '', error.message || String(error))));
  $('feedback-back').hidden = false;
  document.title = `${title} · 핫딜픽`;
}

function placeholder() {
  const node = element('span', 'image-placeholder');
  node.dataset.testid = 'image-fallback';
  // This constant icon contains no product or externally supplied markup.
  node.innerHTML = placeholderIcon;
  node.append(element('span', '', '이미지 없음'));
  return node;
}

function loadProductImage(frame, item, index) {
  const fallback = placeholder();
  frame.append(fallback);
  return new Promise((resolve) => {
    if (!item.img) {
      state.imageFailures.push({ index, name: item.name, reason: 'missing' });
      resolve();
      return;
    }
    const image = element('img', 'product-image');
    image.alt = item.name;
    image.loading = 'eager';
    image.decoding = 'async';
    image.referrerPolicy = 'no-referrer';
    let settled = false;
    let timer;
    const finish = (reason) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      image.onload = image.onerror = null;
      if (reason) {
        image.removeAttribute('src');
        image.remove();
        state.imageFailures.push({ index, name: item.name, reason });
      } else {
        fallback.hidden = true;
      }
      resolve();
    };
    image.onload = async () => {
      try {
        if (image.decode) await image.decode();
        finish(image.naturalWidth > 0 ? null : 'empty');
      } catch { finish('decode'); }
    };
    image.onerror = () => finish('load');
    timer = setTimeout(() => finish('timeout'), 8000);
    frame.append(image);
    // No crossorigin attribute: ordinary remote product images can render in screenshots.
    image.src = item.img;
  });
}

function renderProduct(item, index) {
  const row = element('li', 'product');
  row.dataset.testid = 'product';
  if ([...item.cond].length > 4 || [...item.unit].length > 13 || item.price.length > 9 || (item.price.length > 7 && item.cond.length > 2)) {
    row.classList.add('wide-offer');
  }
  const frame = element('div', 'product-image-frame');
  const info = element('div', 'product-info');
  const number = element('span', 'product-number', String(index + 1).padStart(2, '0'));
  number.setAttribute('aria-hidden', 'true');
  const name = element('h2', 'product-name');
  name.dataset.testid = 'product-name';
  name.dataset.overflowIgnore = 'true';
  name.title = item.name;
  if (item.url) {
    const link = element('a', '', item.name);
    link.href = item.url;
    link.target = '_blank';
    link.rel = 'sponsored noopener noreferrer';
    name.append(link);
  } else name.textContent = item.name;
  info.append(number, name);
  const offer = element('div', 'product-offer');
  const priceLine = element('div', 'price-line');
  const price = element('strong', 'product-price', item.price);
  price.dataset.testid = 'product-price';
  priceLine.append(price);
  if (item.cond) priceLine.append(element('span', 'product-condition', item.cond));
  offer.append(priceLine);
  if (item.unit) {
    const unit = element('p', 'product-unit', item.unit);
    unit.dataset.testid = 'product-unit';
    offer.append(unit);
  }
  const checked = element('p', 'product-checked', `${shortTime(item.checked)} 확인`);
  checked.title = `${item.checked} (한국시간)`;
  offer.append(checked);
  row.append(frame, info, offer);
  return { row, loaded: loadProductImage(frame, item, index) };
}

async function waitForFonts() {
  let timer;
  try {
    await Promise.race([
      Promise.all([document.fonts.load('600 30px HotdealSans', '핫딜픽'), document.fonts.load('850 42px HotdealSans', '0123456789,원')]),
      new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('글꼴을 불러오는 시간이 초과되었습니다.')), 10000); }),
    ]);
    await document.fonts.ready;
    if (!document.fonts.check('600 30px HotdealSans', '핫딜픽')) throw new Error('카드 글꼴을 불러오지 못했습니다.');
    state.fontsReady = true;
  } finally { clearTimeout(timer); }
}

async function waitForMascots() {
  const image = document.querySelector('.mascots');
  if (!(image.complete && image.naturalWidth > 0)) {
    await new Promise((resolve) => {
      let done = false;
      const finish = () => { if (done) return; done = true; clearTimeout(timer); image.onload = image.onerror = null; resolve(); };
      const timer = setTimeout(finish, 12000);
      image.onload = image.onerror = finish;
    });
  }
  if (!image.naturalWidth) throw new Error('캐릭터 일러스트를 불러오지 못했습니다. assets/mascots-anime-v2.png 파일을 확인해 주세요.');
  if (image.decode) await image.decode();
  state.heroReady = true;
}

function showNotices() {
  const notices = $('preview-notices');
  const messages = [...state.warnings.map((warning) => warning.message || String(warning))];
  if (state.imageFailures.length) messages.push(`이미지가 없거나 열리지 않는 상품 ${state.imageFailures.length}개는 ‘이미지 없음’으로 표시했습니다. 상품 정보는 유지됩니다.`);
  if (!messages.length) return;
  notices.replaceChildren(element('p', '', '카드 확인 안내'), element('ul'));
  notices.querySelector('ul').append(...messages.map((message) => element('li', '', message)));
  notices.hidden = false;
}

async function init() {
  const file = safeDataPath(params.get('data'));
  if (!file) {
    showFeedback('invalid', '표시할 카드를 선택해 주세요', '카드 목록에서 카드를 열거나, 주소에 ?data=파일이름.json을 지정해 주세요.', [{ path: 'data', code: 'INVALID_DATA_PATH', message: 'JSON은 data 폴더의 영문·숫자·밑줄·하이픈 파일명만 사용할 수 있습니다.' }]);
    return;
  }
  state.file = file;
  let response;
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 12000);
    try { response = await fetch(file, { cache: 'no-store', signal: controller.signal }); }
    finally { clearTimeout(timer); }
    if (!response.ok) throw new Error(`상품 JSON을 열 수 없습니다. (${response.status})`);
    let input;
    try { input = await response.json(); }
    catch { throw new Error('JSON 문법을 확인해 주세요. 파일을 읽을 수 없습니다.'); }
    const result = validateCard(input);
    state.warnings = result.warnings || [];
    state.draft = !!result.draft;
    if (!result.ok || !result.data) {
      showFeedback('invalid', result.draft ? '상품 정보를 기다리고 있어요' : '상품 정보를 확인해 주세요', result.draft ? '빈 샘플입니다. 확인한 실제 상품 정보를 채우면 카드가 생성됩니다.' : '아래 내용을 수정하면 카드가 자동으로 생성됩니다.', result.errors || []);
      return;
    }
    const data = result.data;
    const mall = MALLS[data.mall];
    card.dataset.mall = data.mall;
    $('disclosure').textContent = mall.disclosure;
    $('disclosure').dataset.testid = 'disclosure';
    $('mall-badge').textContent = { coupang: '🚀 쿠팡', toss: '💙 토스', naver: '네이버' }[data.mall];
    $('card-title').textContent = data.title;
    const titleLength = [...data.title].length;
    $('card-title').className = titleLength > 28 ? 'title-long' : titleLength > 23 ? 'title-medium' : '';
    $('checked-summary').textContent = `${shortTime(data.checked)} 확인 가격`;
    $('item-count').textContent = `${data.items.length}개의 픽`;
    $('products').style.setProperty('--item-count', data.items.length);
    $('products').dataset.count = String(data.items.length);
    if (data.mall === 'toss') {
      $('posting-note').textContent = `⚠️ ${shortTime(data.checked)} 게시 시점 가격`;
      $('posting-note').hidden = false;
    }
    const products = data.items.map(renderProduct);
    $('products').replaceChildren(...products.map((product) => product.row));
    $('feedback').hidden = true;
    stage.hidden = false;
    updateScale();
    await Promise.all([...products.map((product) => product.loaded), waitForFonts(), waitForMascots()]);
    // Two animation frames let font metrics, image decoding and responsive layout settle.
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    state.mall = data.mall;
    state.itemCount = data.items.length;
    state.checked = data.checked;
    state.status = 'ready';
    document.title = `${data.title} · 핫딜픽`;
    showNotices();
    window.dispatchEvent(new CustomEvent('hotdealpick:ready', { detail: state }));
  } catch (error) {
    showFeedback('error', '카드를 불러오지 못했어요', '파일 경로와 연결 상태를 확인한 뒤 새로고침해 주세요.', [{ path: file, code: 'LOAD_FAILED', message: error.name === 'AbortError' ? '상품 JSON을 불러오는 시간이 초과되었습니다.' : error.message }]);
  }
}

init();
