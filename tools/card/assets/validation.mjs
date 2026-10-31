/** Shared by the browser, CLI and CI. Never trusts HTML or disclosures from JSON. */
export const MALLS = Object.freeze({
  coupang: Object.freeze({
    label: '🚀 쿠팡',
    disclosure: '이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.',
    hosts: Object.freeze(['coupang.com']),
  }),
  toss: Object.freeze({
    label: '💙 토스',
    disclosure: '이 콘텐츠는 토스쇼핑 쉐어링크 활동의 일환으로, 링크를 통한 구매가 발생하면 일정 수수료를 지급받습니다.',
    hosts: Object.freeze(['toss.im']),
  }),
  naver: Object.freeze({
    label: '네이버',
    disclosure: '이 포스팅은 네이버 쇼핑 커넥트 활동의 일환으로, 판매 발생 시 수수료를 제공받습니다.',
    hosts: Object.freeze(['smartstore.naver.com', 'brand.naver.com', 'shopping.naver.com', 'naver.me']),
  }),
});

const ROOT_KEYS = ['mall', 'title', 'checked', 'items'];
const ITEM_KEYS = ['name', 'price', 'cond', 'unit', 'img', 'url', 'checked'];
const TEXT_KEYS = ['name', 'price', 'cond', 'unit'];
const LIMITS = { title: 36, name: 180, price: 14, cond: 12, unit: 32, img: 2048, url: 2048, checked: 16 };
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const clean = value => value.normalize('NFC').replace(/[\u200B-\u200D\u2060\uFEFF]/g, '').trim();
const folded = value => clean(value).normalize('NFKC').replace(/\s+/g, '').toLowerCase();

const FORBIDDEN = [
  [/최저가|최저가격|역대최저|최저가보장|lowestprice|bestprice/i, '최저가 표현'],
  [/미백|다이어트|면역|효능|치료|완치|예방|항암|항염|혈당|혈압|체지방|지방분해|살빠|체중감량|피부재생|주름개선|탈모방지|통증완화|보습효과/i, '효능 표현'],
  [/써봤|써보니|써본|써보았|써봐서|사용해봤|사용해보니|사용해본|사용해보았|먹어봤|먹어보니|먹어본|먹어보았|직접사용|직접구매|직접먹|직접써|실사용|내돈내산|체험후기|체험했|체험한|찐후기|써보고|먹어보고|사용후기|사용해보고/i, '체험·사용 사칭 가능 표현'],
  [/정가|정상가|소비자가|기존가격|기존가|원래가격|원래가|할인율|할인률|[0-9]+(?:\.[0-9]+)?%|퍼센트할인|반값/i, '정가·할인율 표현'],
];
const MALL_WORDS = { coupang: /쿠팡|coupang/i, toss: /토스|toss/i, naver: /네이버|naver/i };
const TOSS_COMPARE = /가격비교|타사|타몰|다른몰|대비|보다싸|보다저렴|더싸|더저렴|11번가|지마켓|g마켓|gmarket|옥션|auction|알리|aliexpress|테무|temu|아마존|amazon|ssg|쓱닷컴|최저/i;

export function isValidTimestamp(value) {
  if (typeof value !== 'string') return false;
  const m = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})$/.exec(value);
  if (!m) return false;
  const [y, mo, d, h, mi] = m.slice(1).map(Number);
  if (y < 2000 || y > 2099 || mo < 1 || mo > 12 || h > 23 || mi > 59 || d < 1) return false;
  return d <= new Date(Date.UTC(y, mo, 0)).getUTCDate();
}

export function isPrivateHost(host) {
  const h = host.toLowerCase().replace(/^\[|\]$/g, '');
  if (h === 'localhost' || h.endsWith('.localhost') || h.endsWith('.local') || h.endsWith('.internal') || !h.includes('.')) return true;
  // Reject literal IPv6, mapped IPs and IP literals in private/reserved address ranges.
  if (h.includes(':')) return true;
  if (/^\d+\.\d+\.\d+\.\d+$/.test(h)) {
    const [a, b] = h.split('.').map(Number);
    return a === 0 || a === 10 || a === 127 || a >= 224 || (a === 169 && b === 254) ||
      (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || (a === 100 && b >= 64 && b <= 127) || (a === 198 && (b === 18 || b === 19));
  }
  return false;
}

function httpsURL(value) {
  try {
    if (!/^https:\/\//i.test(value) || /[\s\\]/.test(value)) return null;
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.username || url.password || (url.port && url.port !== '443') || isPrivateHost(url.hostname)) return null;
    return url;
  } catch { return null; }
}

export function isMallURL(value, mall) {
  const url = httpsURL(value);
  if (!url || !Object.hasOwn(MALLS, mall)) return false;
  return MALLS[mall].hosts.some(host => url.hostname === host || (host !== 'naver.me' && url.hostname.endsWith(`.${host}`)));
}

export function isAllowedImage(value) {
  if (value === '') return true;
  // Local paths are deliberately restricted; neither JSON nor remote media can execute code.
  if (/^assets\/images\/[A-Za-z0-9][A-Za-z0-9_.-]*\.(?:png|jpe?g|webp|avif|gif)$/i.test(value) && !value.includes('..')) return true;
  return Boolean(httpsURL(value));
}

export function validateCard(input) {
  const errors = [], warnings = [];
  const add = (path, code, message) => errors.push({ path, code, message });
  const warn = (path, code, message) => warnings.push({ path, code, message });
  const result = (data = null, draft = false) => ({ ok: errors.length === 0 && data !== null && !draft, draft, errors, warnings, data });
  if (!object(input)) { add('$', 'SCHEMA', 'JSON 최상위는 객체여야 합니다.'); return result(); }
  for (const key of Object.keys(input)) if (!ROOT_KEYS.includes(key)) add(key, 'UNKNOWN_FIELD', '지원하지 않는 필드입니다. 기존 JSON 스키마만 사용하세요.');
  const getString = (obj, key, path, optional = false) => {
    if (optional && obj[key] === undefined) return '';
    if (typeof obj[key] !== 'string') { add(path, 'TYPE', '문자열로 입력하세요.'); return ''; }
    const text = clean(obj[key]);
    if (/[\u0000-\u001F\u007F\u202A-\u202E\u2066-\u2069]/.test(text)) add(path, 'CONTROL_TEXT', '줄바꿈과 숨김 제어문자는 사용할 수 없습니다.');
    if (Array.from(text).length > (LIMITS[key] ?? 50)) add(path, 'TEXT_LENGTH', `${LIMITS[key] ?? 50}자 이하로 입력하세요.`);
    return text;
  };
  const mall = getString(input, 'mall', 'mall');
  const title = getString(input, 'title', 'title');
  const checked = getString(input, 'checked', 'checked');
  const knownMall = Object.hasOwn(MALLS, mall);
  if (!knownMall) add('mall', 'MALL', 'mall은 coupang, toss, naver 중 하나여야 합니다.');
  if (!title) add('title', 'REQUIRED', '카드 제목을 입력하세요.');
  if (!Array.isArray(input.items)) { add('items', 'SCHEMA', 'items는 배열이어야 합니다.'); return result(); }
  if (input.items.length < 3 || input.items.length > 5) add('items', 'ITEM_COUNT', '입력 상품 행은 3~5개여야 합니다.');
  const items = input.items.slice(0, 100).map((item, index) => {
    const path = `items[${index}]`;
    if (!object(item)) { add(path, 'SCHEMA', '상품 행은 객체여야 합니다.'); return Object.fromEntries(ITEM_KEYS.map(k => [k, ''])); }
    for (const key of Object.keys(item)) if (!ITEM_KEYS.includes(key)) add(`${path}.${key}`, 'UNKNOWN_FIELD', '판매처·정가·할인율 등 추가 필드는 허용하지 않습니다.');
    return Object.fromEntries(ITEM_KEYS.map(key => [key, getString(item, key, `${path}.${key}`, true)]));
  });
  const inspectCopy = (value, path) => {
    const text = folded(value);
    for (const [pattern, label] of FORBIDDEN) if (pattern.test(text)) add(path, 'FORBIDDEN_COPY', `${label}을 삭제하세요.`);
    if (knownMall) for (const [other, pattern] of Object.entries(MALL_WORDS)) {
      if (mall !== other && pattern.test(text)) add(path, 'MIXED_MALL', '다른 몰의 이름은 카드에 표시할 수 없습니다.');
    }
    if (mall === 'toss' && TOSS_COMPARE.test(text)) add(path, 'PRICE_COMPARISON', '토스 카드에는 타 몰 언급과 가격 비교를 표시할 수 없습니다.');
  };
  inspectCopy(title, 'title');
  items.forEach((item, index) => TEXT_KEYS.forEach(key => inspectCopy(item[key], `items[${index}].${key}`)));
  const draft = checked === '' && items.length >= 3 && items.length <= 5 && items.every(item => ITEM_KEYS.every(key => item[key] === ''));
  if (draft && errors.length === 0) {
    warn('items', 'DRAFT', '빈 데이터 초안입니다. 검증된 상품을 3개 이상 입력하면 카드가 생성됩니다.');
    return result(null, true);
  }
  if (!isValidTimestamp(checked)) add('checked', 'TIMESTAMP', '게시 기준 시각을 YYYY-MM-DD HH:mm (한국 시간)으로 입력하세요.');
  const eligible = [];
  items.forEach((item, index) => {
    const path = `items[${index}]`;
    // Missing price/timestamp means omission, never a placeholder product or guessed value.
    if (!item.price || !item.checked) {
      warn(path, 'ITEM_OMITTED', '가격 또는 상품 확인 시각이 없어 이 상품을 제외했습니다.');
      return;
    }
    if (!item.name) add(`${path}.name`, 'REQUIRED', '검증된 상품명을 입력하세요.');
    if (!/^(?:[1-9]\d{0,8}|[1-9]\d{0,2}(?:,\d{3}){1,2})원$/.test(item.price)) add(`${path}.price`, 'PRICE', '가격은 양수 원화 문자열로 입력하세요. (최대 999,999,999원)');
    if (!isValidTimestamp(item.checked)) add(`${path}.checked`, 'TIMESTAMP', '상품 확인 시각을 YYYY-MM-DD HH:mm (한국 시간)으로 입력하세요.');
    else if (isValidTimestamp(checked) && item.checked > checked) add(`${path}.checked`, 'TIMESTAMP_ORDER', '상품 확인 시각은 게시 기준 시각보다 늦을 수 없습니다.');
    if (!isMallURL(item.url, mall)) add(`${path}.url`, 'MALL_URL', '해당 몰의 허용된 HTTPS 구매 링크를 입력하세요.');
    if (!isAllowedImage(item.img)) add(`${path}.img`, 'IMAGE_URL', '이미지는 공개 HTTPS 주소 또는 assets/images/ 안의 이미지 경로만 허용합니다.');
    if (!item.img) warn(`${path}.img`, 'IMAGE_MISSING', '이미지가 없어 사진 확인 안내를 표시합니다.');
    if (mall !== 'coupang' && /와우/.test(folded(item.cond))) add(`${path}.cond`, 'MIXED_MALL', '다른 몰의 회원 조건을 사용할 수 없습니다.');
    eligible.push(item);
  });
  if (eligible.length < 3 || eligible.length > 5) add('items', 'ITEM_COUNT', `가격과 확인 시각을 갖춘 상품이 ${eligible.length}개입니다. 3~5개가 필요합니다.`);
  return result(errors.length ? null : { mall, title, checked, items: eligible });
}
