# 🔥 핫딜봇 (자동 수익형 텔레그램 채널)

뽐뿌 핫딜을 30분마다 수집 → **Claude가 살 만한 딜만 골라 코멘트** → 내 텔레그램으로 초안 → **✅ 누르면 채널에 자동 게시**.
쿠팡파트너스 키를 넣으면 쿠팡 링크가 **제휴링크로 자동 변환**되고, 매일 **골드박스 TOP5**도 올라와.

```
GitHub Actions (30분마다, KST 08~24시 · GitHub 예약 실행은 지연·누락될 수 있음)
 ├─ ✅/❌ 누른 초안 처리 → 채널 게시
 ├─ 뽐뿌 RSS → 30분 지난 새 글 → Claude 점수·코멘트 → 7점↑ 최대 5개 초안
 ├─ (쿠팡 키 있으면) 09시 이후 1회 골드박스 TOP5 초안
 ├─ 21시 이후 1회 '오늘의 딜 모아보기' 초안 (✅ → 채널 게시) + 📝 블로그용 글 + 카드 이미지 생성
 ├─ 카드가 사이트에 올라오면(다음 실행) Threads 자동 게시 + 인스타용으로 관리자에게 전송
 └─ 채널에 게시된 딜 → 웹사이트 자동 갱신 (hotdealpick.kr)
```

## 파일
| 파일 | 역할 |
|---|---|
| `hotdeal.py` | 봇 본체 (표준 라이브러리만) |
| `build_site.py` | 게시된 딜(`posts.json`) → `docs/` 웹사이트 생성 (GitHub Pages) |
| `cards.py` | 오늘의 딜 → Threads/인스타 카드 이미지(1080×1350) → `docs/cards/날짜.png` (Pillow·나눔고딕은 워크플로가 설치) |
| `.github/workflows/hotdeal.yml` | 30분마다 자동 실행 + 사이트 커밋 |
| `.github/workflows/linkcheck.yml` | (수동) GitHub 서버에서 뽐뿌 쇼핑몰 링크 추출 점검 |
| `test_hotdeal.py` | 셀프체크 (`python test_hotdeal.py`) |

---

## 세팅 (약 20분, 폰으로 가능)

### 1. 텔레그램
1. **@BotFather** → `/newbot` → 이름 정하기 → **토큰** 복사 → `TG_TOKEN`
2. 새 **채널** 만들기(공개, 예: `@jinwoo_hotdeal`) → 채널 관리자에 **방금 만든 봇 추가**(메시지 게시 권한) → `TG_CHANNEL` = `@채널아이디`
3. 내 봇 채팅방 들어가서 **`/start`** 한 번 (안 하면 봇이 나한테 못 보냄)
4. **@userinfobot** 에게 아무 말 → 나오는 숫자 ID → `TG_ADMIN_ID`

### 2. Claude API 키
- console.anthropic.com → 결제수단 등록 + 크레딧 $10 충전 → API Keys → 키 발급 → `ANTHROPIC_API_KEY`
- ⚠️ Claude Max 구독과 API 요금은 **별도**야

### 3. GitHub
1. 새 저장소 **Private**로 생성
2. `Add file → Upload files` 로 `hotdeal.py`, `test_hotdeal.py`, `README.md` 업로드
3. `Add file → Create new file` → 파일명에 **`.github/workflows/hotdeal.yml`** 입력 → `hotdeal.yml` 내용 붙여넣기 → Commit
4. `Settings → Secrets and variables → Actions → New repository secret` 로 4개 등록
   `TG_TOKEN`, `TG_ADMIN_ID`, `TG_CHANNEL`, `ANTHROPIC_API_KEY`
5. `Actions` 탭 → `hotdeal` → **Run workflow** → 텔레그램에 초안 오면 성공 🎉
   (초안이 0개면 7점 넘는 딜이 없던 것. 테스트용으로 Variables에 `MIN_SCORE=1` 넣고 다시 실행 → 확인 후 삭제)

### 4. 쿠팡파트너스 (수익 연결)
1. partners.coupang.com 가입 → **활동 페이지에 텔레그램 채널 주소 등록** (미등록 시 제재 가능)
2. **최종 승인**(누적 판매 15만원 이후) → 파트너스 사이트에서 **API 키(Access/Secret) 발급**
3. 시크릿 2개 추가: `COUPANG_ACCESS_KEY`, `COUPANG_SECRET_KEY` → 끝. 다음 실행부터 자동 변환 + 골드박스 시작
- 승인 전엔 자동 변환이 안 됨 → 쿠팡 딜 초안에 **파트너스 링크로 답장**하면 버튼 교체 + 대가성 문구 자동 (아래 '매일 할 일'). 이렇게 판매 쌓이면 최종 승인 빨라짐
- 대가성 문구(`이 포스팅은 쿠팡 파트너스 활동의 일환으로…`)는 **제휴링크 글 맨 앞에 자동 삽입**됨

### 5. 웹사이트 (GitHub Pages, 무료)
- 저장소 **Public** 필요 (Free 플랜은 공개 저장소만 Pages 가능. 코드에 비밀값 없음, 시크릿은 별도 보관)
- `Settings → Pages → Source: Deploy from a branch → main / docs` → 저장
- 기본 주소 `https://luminae21-source.github.io/hotdeal-bot/` → 커스텀 도메인 **https://hotdealpick.kr** 연결됨 (가비아 DNS: A @ → 185.199.108~111.153, CNAME www → luminae21-source.github.io / Pages → Custom domain / `docs/CNAME`은 `build_site.py`가 매번 생성)
- 사이트 주소는 텔레그램 채널 설명과 쿠팡파트너스 **내 정보 → 웹사이트**에도 등록
- 검색 등록 완료: 구글 서치콘솔(DNS TXT 인증), 네이버 서치어드바이저(HTML 태그 — `build_site.py`의 `naver-site-verification` 메타, 지우면 소유확인 풀림)

### 6. Threads 자동 게시 (선택, 무료)
1. 브랜드용 인스타그램 계정 → Threads 앱 로그인 → 프로필 **공개**
2. developers.facebook.com → 내 앱 → **앱 만들기** → 사용 사례 **Threads API 액세스** → 이름 `hotdealpick`
3. 앱 대시보드 → **앱 역할 → 역할 → 사람 추가 → Threads 테스터** → 내 Threads 사용자명 → Threads 앱 **설정 → 계정 → 웹사이트 권한 → 초대 수락**
4. 사용 사례 → Threads API → **맞춤 설정**: 권한 `threads_basic`, `threads_content_publish` 추가 → 설정에 Redirect URI `https://hotdealpick.kr/` → **사용자 토큰 생성기**에서 테스터 토큰 생성 → 복사
5. GitHub 시크릿 `THREADS_TOKEN` 등록 → 끝. 다음날 21시 모아보기 뒤 자동으로 올라감
- 토큰은 **60일 만료** → 봇이 "⚠️ Threads 게시 실패" 보내면 4번 다시 해서 시크릿 교체
- 인스타그램은 API 조건(비즈니스 계정+페이스북 페이지)이 까다로워 자동화 안 함. 대신 Threads 게시 후 **같은 카드를 봇이 채팅으로 보내줌** → 폰에서 인스타에 올리면 10초

---

## 매일 할 일 (5~10분)
- 봇 채팅에 오는 초안 보고 **✅ 게시 / ❌ 패스** 만 누르기
- 수수료 받을 딜이면: 초안의 🛒 버튼(뽐뿌 글) → 쇼핑몰 주소 복사 → 쿠팡 파트너스 / 링크프라이스 / 토스 쉐어링크('[토스]' 딜은 토스 앱 상품 공유 → '팔릴 때마다 돈 버는 링크 공유하기')에서 제휴 링크 만들기 → **초안에 답장으로 링크 붙여넣기** → 바로 ✅ 눌러도 됨. 다음 실행 때 버튼이 그 링크로 바뀌고 대가성 문구가 맨 앞에 붙어서 게시됨 (일반 쇼핑몰 주소로 답장하면 버튼만 바뀜)
- 내가 찾은 딜(초안 없음)은 봇 채팅에 **첫 줄 제목 + (코멘트) + 링크**를 보내면 다음 실행 때 그 딜 초안이 옴 → ✅. 제휴 링크면 대가성 문구 자동, 링크만 보내면 제목 달라고 답장 옴
- ✅ 누른 건 **다음 실행** 때 채널에 올라감 (보통 30분 안, GitHub 예약 실행이 밀리면 더 늦음). 급하면 GitHub 앱 → Actions → hotdeal → Run workflow
- 밤 9시 '오늘의 딜 모아보기' 초안 → ✅ 게시. 바로 뒤에 오는 **📝 블로그용 메시지**(제목+본문)를 blog.naver.com/hotdeal_pick 에 복붙 1분 = 네이버 검색 유입
- 9시 반쯤 📸 **오늘의 카드** 사진이 옴 → 인스타에 그대로 올리면 끝 (Threads 연결돼 있으면 Threads는 이미 자동 게시됨)

## 유입 늘리기 (한 번만 하면 되는 것)
| 할 일 | 효과 |
|---|---|
| ✅ 채널 이름 `오늘의 딜 pick | 핫딜·특가 알림`, 사진, 설명에 사이트 주소 | 텔레그램 내 검색 노출 |
| ✅ Google Search Console 등록 + `sitemap.xml` 제출 | 구글 검색 유입 |
| ✅ Naver Search Advisor 등록 + 사이트맵 제출 | 네이버 검색 유입 |
| ✅ 네이버 블로그 blog.naver.com/hotdeal_pick 개설 → 매일 21시 봇이 보내는 📝 블로그용 메시지 복붙 | 가장 큰 국내 유입원 |
| Threads 연결 (위 6번) → 매일 카드 자동 게시 | 2030 유입, 손 안 감 |
| 토스 쉐어링크(sharelink.toss.im, 개인 가입 가능·기본 5%, Threads·인스타 허용) 가입 → `[토스]` 딜에 쉐어링크 답장. 쿠팡 승인과 별개로 지금 가능 | `[토스]` 딜 수익화 |
| 알리 어필리에이트·링크프라이스(11번가·G마켓·옥션, 딥링크 API 있음)·네이버 쇼핑커넥트(블로그·인스타용) **지금 신청** → 승인 나면 링크 변환 붙임 | 수수료 되는 딜 비율 35% → 80% |
| 애드센스·애드포스트는 글 50개+ 뒤에 | 일찍 넣으면 반려 |

## 조절 (Settings → Variables, 선택)
| 변수 | 기본값 | 설명 |
|---|---|---|
| `MIN_SCORE` | 7 | 초안 받을 최소 점수. 너무 많으면 8로 |
| `MODEL` | claude-sonnet-5-5 | Claude 모델 |
보드 추가는 `hotdeal.py` 의 `FEEDS` 한 줄 수정.

## 비용 (추정)
| 항목 | 월 |
|---|---|
| GitHub Actions | 0원 (월 ~1,000분, 무료 2,000분 이내) |
| Claude API | 약 $5~10 (1회 2~4건 판단 기준) |
| 텔레그램 | 0원 |

## 안 될 때
| 증상 (Actions 로그) | 조치 |
|---|---|
| `feed ppomppu ... 403` | 뽐뿌가 GitHub 서버를 막은 것 → 알려주면 다른 소스 추가 |
| `TG getUpdates 404` | `TG_TOKEN` 틀림 → BotFather `/token`으로 현재 토큰 확인 후 시크릿 수정 |
| `URL can't contain control characters` | 시크릿에 공백 섞임 (현재 코드는 자동 제거) |
| `TG sendMessage 403` | 봇에게 `/start` 안 보냄 |
| `⚠️ 채널 게시 실패` 메시지 | 봇이 채널 관리자인지, `TG_CHANNEL` 확인 |
| `deeplink ...` | 쿠팡 키 오타 / 아직 API 미승인 |
| 초안이 몇 시간째 안 옴 (Actions에 `Scheduled` 실행이 드묾) | GitHub 예약 실행 지연·누락 → Run workflow로 바로 실행. 계속 드물면 외부 크론(cron-job.org)에서 30분마다 workflow_dispatch 호출로 해결 |
| 구매 버튼이 뽐뿌 글로 감 | 현재 정상 (뽐뿌가 GitHub 서버 IP를 차단) → 초안에 링크 답장으로 교체. 차단이 풀렸는지는 Actions → `linkcheck` → Run workflow → 로그에 쇼핑몰 주소가 나오면 자동 추출 재개 |

---

## 검증 기록
| 날짜 | 항목 | 방법 | 결과 |
|---|---|---|---|
| 2026-10-04 | RSS 파싱 (조회·추천·댓글, 30분 필터) | 실제 뽐뿌 RSS 구조로 셀프체크 | ✅ |
| 2026-10-04 | 쇼핑몰 링크 추출 | 실제 뽐뿌 글 HTML(no=737993) | ✅ G마켓 링크 정상 추출 |
| 2026-10-04 | 쿠팡 HMAC 서명 | 공식 가이드 포맷으로 재계산 비교 | ✅ |
| 2026-10-04 | 승인 처리 | ✅중복클릭·❌·타인클릭·offset 확인 | ✅ |
| 2026-10-04 | 중복 방지 / 골드박스 1일 1회 / 대가성 문구 위치 | 재실행 시나리오 | ✅ |
| 2026-10-04 | 피드 장애 시 나머지 진행 | 죽은 피드 주입 | ✅ |
| 2026-10-04 | GitHub 서버→뽐뿌 RSS 수집 | 실제 Actions 실행 | ✅ 9건 수집 |
| 2026-10-04 | 뽐뿌 글 본문(쇼핑몰 링크) 접근 | 실제 Actions 실행 | ⚠️ 403 차단 → 구매 버튼이 뽐뿌 글로 연결됨 (RSS는 정상) |
| 2026-10-04 | Claude API 실제 호출 | 실제 Actions 실행 | ✅ (tool_choice 강제 시 400 → auto로 변경) |
| 2026-10-04 | 텔레그램 초안 발송 | 실제 Actions 실행 | ✅ 2건 발송 |
| 2026-10-04 | 시크릿에 공백/줄바꿈 섞임 | 실제 Actions 실행 | ✅ 코드에서 자동 제거 |
| 2026-10-04 | ✅ 승인 → 채널 게시 | 실제 Actions 실행 | ✅ 2건 게시 (t.me/hotdeal_pick) |
| 2026-10-04 | 웹사이트 생성 (링크 오프셋·제목·사이트맵·빈 목록·OG 태그) | 셀프체크 | ✅ |
| 2026-10-04 | 사이트 파일 자동 커밋 | 실제 Actions 실행 | ✅ hotdeal-bot 계정으로 docs/ 커밋 |
| 2026-10-04 | 일일 모아보기 (21시 1회·오늘 글만·자기 제외) | 셀프체크 | ✅ |
| 2026-10-04 | 웹사이트 실제 배포 | 저장소 Public 전환 + Pages(main/docs) | ✅ https://luminae21-source.github.io/hotdeal-bot/ |
| 2026-10-05 | 커스텀 도메인 | 가비아 hotdealpick.kr 구매(3년) + DNS(A×4, CNAME www) + Pages Custom domain + Enforce HTTPS | ✅ https://hotdealpick.kr 정상 (2건 표시, HTTPS) |
| 2026-10-05 | 구글 서치콘솔 | 도메인 속성 + DNS TXT 소유확인 + sitemap.xml 제출 | ✅ 소유확인 통과 (사이트맵은 수집 대기) |
| 2026-10-05 | 블로그용 메시지 (21시 모아보기 뒤 제목+본문+대가성 문구, 1회) | 셀프체크(22시 고정) | ✅ |
| 2026-10-05 | 네이버 서치어드바이저 | HTML 태그(`naver-site-verification`) 사이트에 삽입 + 소유확인 + 사이트맵·수집 요청 | ✅ |
| 2026-10-05 | 카드 이미지 (제목 파싱·중첩 괄호·6개 초과 시 하단 침범 없음·PNG 생성) | 셀프체크 | ✅ |
| 2026-10-05 | 카드 전송·Threads 게시 흐름 (카드 미배포 시 대기 → 사진 1회 → 토큰 있으면 me → 컨테이너 → 발행, 토큰 없으면 사진만) | 셀프체크 (API 모킹) | ✅ |
| 2026-10-05 | 워크플로 Pillow·나눔고딕 설치 | 실제 Actions 실행 #14 | ✅ 3초, 오류 없음 |
| 2026-10-05 | 인스타·Threads 계정 `hotdealpick.kr` (실명 비노출·소개·링크) | 공개 프로필 확인 + Threads 링크 클릭 → 사이트 열림 | ✅ |
| 2026-10-05 | Threads 앱 `hotdealpick` (권한 basic·content_publish, 콜백 URL, 테스터 수락, `THREADS_TOKEN` 시크릿) | Meta 대시보드 새로고침 확인 + Threads 웹사이트 권한 '활성' + GitHub 시크릿 목록 | ✅ |
| 2026-10-05 | 사이트 하단 인스타·Threads 링크 | 셀프체크 6 | ✅ |
| 2026-10-05 | 쇼핑몰 링크 추출 (`target=` base64 복원, `+` 보존, 링크 없는 글·차단 시 None) | 실제 뽐뿌 PC 글(no=738120) + 셀프체크 2 | ✅ G마켓 원본 주소 복원 |
| 2026-10-05 | GitHub 서버 → 뽐뿌 PC·모바일 글 접근 | `linkcheck` #1 실제 실행 | ❌ 둘 다 403 (nginx IP 차단) → 우회하지 않고 답장 교체 방식으로 해결 |
| 2026-10-05 | 초안 답장 링크 교체 (쿠팡=쿠팡 문구 / 링크프라이스·알리=제휴 문구 / 일반 주소=버튼만, UTF-16 오프셋, 같은 실행 ✅, 남의 답장 무시) | 셀프체크 3-2 + 22시 고정 실행 | ✅ |
| 2026-10-05 | 토스 쉐어링크 링크(toss.im·toss.shopping) 답장 교체 + 토스 권장 대가성 문구, 제휴 문구 줄이 제목으로 잡히던 문제 수정 | 셀프체크 3-2 | ✅ (쉐어링크 가입·실제 링크는 ⏳) |
| 2026-10-05 | 링크프라이스 G마켓 딥링크 생성 (item.gmarket.co.kr → click.linkprice.com/click.php?m=gmarket…) + 단축 도메인(lpweb·linkmoa·lase·bestmore·newtip)도 대가성 문구 자동 | 실제 링크프라이스 딥링크 메뉴 + 셀프체크 3-2 | ✅ (구매 시 수수료 집계는 ⏳) |
| 2026-10-05 | 예약 실행 빈도 (`*/30`) | Actions 실행 목록 | ❌ 08~13시 KST 예약 10번 중 1번만 실행(#15, 16분 지연) → 혼잡한 정각·30분을 피해 `7,37`분으로 변경, 관찰 중 ⏳ |
| 2026-10-05 | 봇에게 '제목+링크' 보내기 → 초안 (대가성 문구·HTML 이스케이프·붙여넣은 문구 중복 제거·링크만 보내면 안내·남의 메시지 무시) | 셀프체크 3-3 | ✅ |
| — | Threads 실제 게시 | THREADS_TOKEN 등록 후 첫 21시 | ⏳ |
| — | 쿠팡 API 실제 호출 | 쿠팡 최종 승인 후 | ⏳ |
