# 🔥 핫딜봇 (자동 수익형 텔레그램 채널)

뽐뿌 핫딜을 30분마다 수집 → **Claude가 살 만한 딜만 골라 코멘트** → 내 텔레그램으로 초안 → **✅ 누르면 채널에 자동 게시**.
쿠팡파트너스 키를 넣으면 쿠팡 링크가 **제휴링크로 자동 변환**되고, 매일 **골드박스 TOP5**도 올라와.

```
GitHub Actions (30분마다, KST 08~24시)
 ├─ ✅/❌ 누른 초안 처리 → 채널 게시
 ├─ 뽐뿌 RSS → 30분 지난 새 글 → Claude 점수·코멘트 → 7점↑ 최대 5개 초안
 └─ (쿠팡 키 있으면) 09시 이후 1회 골드박스 TOP5 초안
```

## 파일
| 파일 | 역할 |
|---|---|
| `hotdeal.py` | 봇 본체 (표준 라이브러리만, 설치 X) |
| `.github/workflows/hotdeal.yml` | 30분마다 자동 실행 |
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
- 승인 전엔 링크가 원본 그대로 나감 → 이 기간은 **구독자 모으기** 기간. 쿠팡 딜은 파트너스 앱으로 링크 직접 만들어 몇 개 올리면 승인 앞당길 수 있어
- 대가성 문구(`이 포스팅은 쿠팡 파트너스 활동의 일환으로…`)는 **제휴링크 글 맨 앞에 자동 삽입**됨

---

## 매일 할 일 (5~10분)
- 봇 채팅에 오는 초안 보고 **✅ 게시 / ❌ 패스** 만 누르기
- ✅ 누른 건 **다음 실행(최대 30분)** 때 채널에 올라감. 급하면 GitHub 앱 → Actions → Run workflow

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
| — | ✅ 승인 → 채널 게시, 쿠팡 API | 다음 실행 / 쿠팡 승인 후 | ⏳ |
