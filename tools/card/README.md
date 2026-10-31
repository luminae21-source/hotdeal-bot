# tools/card — 몰별 카드 렌더러 (진우 GPT v2 + Cowork 수정, 2026-10-31)

진우가 GPT로 만든 렌더 전용 템플릿 v2(card.html + JSON + Playwright). 봇이 확인한 가격·사진으로 몰별 4:5 카드(1080×1350)를 만드는 용도. 데이터 틀 = data/ (빈 값 — 가짜 상품·가격 X).

## Cowork 시험(10/31, 실제 쿠팡 상품 5개 — 할로윈 반짝 데이터)과 고친 것
1. 쿠팡 사진이 전부 안 나옴 — img.crossOrigin='anonymous' 때문(쿠팡 CDN은 CORS 헤더 없음 → ERR_FAILED). 스크린샷엔 CORS 필요 없어서 그 줄 삭제 → 5장 다 나옴.
2. 토스 카드 겹침 — 제휴 문구 2줄 + 긴 제목이면 5번째 상품이 '게시 시점 가격' 줄·하단과 겹침. 절대 위치 → 세로 flex, 제목 한 줄 말줄임, 상품 칸 높이 자동.
3. 글꼴 — Arial/Noto Sans KR 지정이라 Actions(ubuntu)에선 한글이 대체 글꼴로 나옴 → Pretendard(jsDelivr woff2) + document.fonts.ready 기다림. CDN이 막히면 봇 fonts/ 나눔고딕을 로컬 @font-face로.
4. 시각 표시 — 머리 'M/D HH:MM 확인 가격', 상품별 시각은 머리와 다를 때만. 가격 조건(와우가 등) 빨강 굵게.
5. 폴더 단순화 — scripts/render.mjs → render.mjs (package.json 그대로 맞춤).

## 규칙(그대로)
제휴 문구 HTML 고정(JSON으로 못 바꿈) · 카드 1장 = 몰 1개 · 가격+확인 시각 있는 상품만 · 3~5개 아니면 실패 · 정가·할인율 없음 · 금지 표현 검사 · 토스 = 하단 '⚠️ M/D HH:MM 게시 시점 가격'.

## 실행
cd tools/card && npm i && npx playwright install --with-deps chromium && node render.mjs data/coupang_1101.json output/card.png
(render.yml.example = GPT 수동 워크플로 원본, 경로는 루트 기준 — 봇 연결 땐 hotdeal.yml 안에서 직접 부르기)
