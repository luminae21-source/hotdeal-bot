import { MALLS } from './validation.mjs';

const container = document.getElementById('gallery-cards');
const feedback = document.getElementById('gallery-feedback');
const counter = document.getElementById('gallery-count');
const badges = { coupang: '🚀 쿠팡', toss: '💙 토스', naver: '네이버' };

function node(tag, className, text) {
  const item = document.createElement(tag);
  if (className) item.className = className;
  if (text !== undefined) item.textContent = text;
  return item;
}

function localPath(value, directory, extension) {
  if (typeof value !== 'string') return null;
  const filename = value.startsWith(`${directory}/`) ? value.slice(directory.length + 1) : value;
  if (!new RegExp(`^[A-Za-z0-9_-]+\\.${extension}$`).test(filename)) return null;
  return `${directory}/${filename}`;
}

function link(text, href, className = '') {
  const item = node('a', className, text);
  item.href = href;
  return item;
}

function card(entry) {
  const file = localPath(entry.file, 'data', 'json');
  if (!file || !MALLS[entry.mall] || !['ready', 'draft'].includes(entry.status)) return null;
  const ready = entry.status === 'ready';
  const article = node('article', 'gallery-card');
  article.dataset.mall = entry.mall;
  const top = node('div', 'gallery-card-top');
  top.append(node('span', 'gallery-card-badge', badges[entry.mall]), node('h3', '', entry.title || '오늘의 장바구니'));
  if (entry.checked) top.append(node('time', '', `${entry.checked} 확인 · 한국시간`));
  top.append(node('p', 'gallery-card-status', ready ? '가격과 단위가를 카드로 확인해 보세요.' : '상품 정보 입력 전 · 빈 JSON 샘플'));
  const actions = node('div', 'gallery-card-actions');
  if (ready) actions.append(link('카드 보기 ↗', `card.html?data=${encodeURIComponent(file)}`, 'primary-link'));
  else actions.append(node('span', 'disabled-link', '상품 정보를 기다리는 중'));
  actions.append(link('JSON', file));
  const png = localPath(entry.png, 'rendered', 'png');
  if (ready && png) {
    const download = link('PNG ↓', png);
    download.download = png.split('/').pop();
    actions.append(download);
  }
  article.append(top, actions);
  return article;
}

async function init() {
  try {
    const response = await fetch('manifest.json', { cache: 'no-store' });
    if (!response.ok) throw new Error('manifest unavailable');
    const manifest = await response.json();
    if (!Array.isArray(manifest.cards)) throw new Error('invalid manifest');
    const cards = manifest.cards.map(card).filter(Boolean);
    container.replaceChildren(...cards);
    const readyCount = manifest.cards.filter((entry) => entry.status === 'ready' && localPath(entry.file, 'data', 'json') && MALLS[entry.mall]).length;
    counter.textContent = `${readyCount}개의 카드`;
    if (!cards.length || !readyCount) {
      feedback.querySelector('h3').textContent = '오늘의 카드를 준비하고 있어요';
      feedback.querySelector('p').textContent = '확인한 실제 상품 정보가 등록되면 이곳에서 카드와 PNG를 볼 수 있어요.';
      if (cards.length) feedback.style.marginBottom = '20px';
    } else feedback.hidden = true;
  } catch {
    feedback.querySelector('h3').textContent = '아직 등록된 카드가 없어요';
    feedback.querySelector('p').textContent = '상품 정보를 채우고 프로젝트를 빌드하면 카드 목록이 여기에 표시됩니다.';
    counter.textContent = '0개의 카드';
  }
}

init();
