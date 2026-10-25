#!/usr/bin/env python3
"""핫딜봇: 뽐뿌·루리웹·클리앙 핫딜 -> Claude 선별/코멘트 -> 채널 바로 게시.
상품 주소가 있으면(루리웹·클리앙 글) 링크프라이스 승인 몰은 상품 페이지 제휴 링크 자동, 없으면(뽐뿌: GitHub IP 차단) 검색 제휴 링크.
쿠팡·네이버 등 수동 몰은 관리자에게 사본(+쿠팡은 파트너스 검색 버튼, 네이버는 상품명 복사·쇼핑커넥트 버튼, 그 외 상품 열기 버튼) -> 제휴 링크를 답장(또는 그냥 전송)하면 채널 글 교체. 쿠팡 골드박스는 매일 7시 이후 1번 채널에 바로(키 없으면 골드박스 링크, 있으면 TOP5).
GitHub Actions에서 15분마다 실행(tick.yml 타이머가 workflow_dispatch로 실행 + 예약 보조). 외부 패키지 없음(파이썬 표준 라이브러리만)."""
import base64, collections, glob, hashlib, hmac, html, json, math, os, random, re, shutil, tempfile, time, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from build_site import day_end, BASE as SITE, BLOG, GOLDBOX, NOTE_STARTS, title_of, split_title, parse, react, TOSS_HOSTS, NAVER_HOSTS, AFF_HOSTS, OY_HOSTS, toss_share, day_deals, card_order, saving, buy_label, aff, MALL_HEAD, mall_title, CATS, CARD_N, SLOT_NAMES, card_name, SAVE_STORES, STEM, unit_of, strip_cmp, OTHER_STORES, CMP_WORDS, shop_of, price_won, FOOD, CHANNEL_WEB, price_records, PRICE_MIN, DAY_ONLY, cat_of, SHELF_CATS, ev_info, ev_list, CP_LINKS, CP_PROD, CP_SHORT, icon_of, md_h as S_md_h, CAT_META, GC_CODE, per_unit as S_per_unit, items as shelf_items, PRICE_ITEMS, PRICE_NOT, price_item, LINK_AB, PROMOS, PROMO_LINKS, promo_list, promo_days, promo_pre, site_ok, img_of, drops, c_url, md_of, won  # 제휴 도메인은 사이트와 같이 씀

E = {k: "".join(v.split()) for k, v in os.environ.items()}  # 시크릿 붙여넣을 때 섞인 공백·줄바꿈 전부 제거
ADMIN, CHANNEL = E.get("TG_ADMIN_ID", ""), E.get("TG_CHANNEL", "")
MODEL = E.get("MODEL") or "claude-sonnet-5-5"
MIN_SCORE = int(E.get("MIN_SCORE") or 6)  # 10/8 진우: 6점도 바로(그 전 7)
HAS_CP = bool(E.get("COUPANG_ACCESS_KEY") and E.get("COUPANG_SECRET_KEY"))
HAS_TOSS = bool(E.get("TOSS_ACCESS_KEY") and E.get("TOSS_SECRET_KEY") and E.get("TOSS_PUBLISHER_ID"))  # 쉐어링크 Open API(10/6 승인). 호출은 고정 IP(오라클) 터널 경유 -> hotdeal.yml
TOSS_API, TOSS_TOKEN = "https://sharelink.toss.im/openapi", "toss.json"  # toss.json: 1년짜리 액세스 토큰 보관(Actions 캐시, 매번 재발급 금지)
MAX_DRAFTS = 1                 # 1회 실행(15분)당 채널 게시 최대 개수. 몰아 올리면 묻히고 뒤가 비어서 1개씩(10/6 진우 '꾸준하게') -> 넘친 딜은 판단 그대로 보관했다가 다음 실행에 먼저
GAP_FILL, FILL_SCORE = 45, 6    # 45분(0~8시 90분, 10/22~) 넘게 채널 딜 글이 없으면 그 실행 후보 중 6점↑ 최고 1개로 빈틈 메움(5점은 안 올림). MIN_SCORE가 6이면 6점은 원래 바로 올라가서 MIN_SCORE를 7로 올렸을 때만 쓰임
MIN_AGE, MAX_AGE = 30, 360     # 분: 반응이 쌓인 뒤 판단, 너무 오래된 글은 무시
MIN_AGE_RULIWEB = 15           # 루리웹 RSS엔 추천·댓글 수가 없어 기다려도 판단 근거가 안 늘어남 -> 빨리
RUN_GAP = 20                   # 분: 다음 실행까지(15분 체인 + 지연 여유). 이 안에 목록에서 밀려날 글은 덜 묵었어도 지금 판단
FEEDS = {"ppomppu": "뽐뿌"}  # 뽐뿌 보드 추가: {"rss id": "표시명"}
RULIWEB_RSS = "https://bbs.ruliweb.com/market/board/1020/rss"  # 루리웹 핫딜예판: RSS + 글 아래 '출처'에 상품 주소 (robots 허용, GitHub 서버 OK 10/5)
CLIEN_LIST = "https://www.clien.net/service/board/jirum"  # 클리앙 알뜰구매: RSS 없음 -> 목록 HTML, 글 위 '구매링크' (robots: 쿼리 없는 /service/board/ 허용)
KST = timezone(timedelta(hours=9))
SEEN, POSTS = "seen.json", "posts.json"  # posts.json: 채널에 게시된 딜 -> build_site.py가 웹사이트로 만듦
SEEN_COLD = E.get("COLD_START") == "true"  # seen.json(Actions 캐시)을 못 받으면 실행을 건너뜀(10/23 16:22 KST 캐시 받기가 85%에서 멈춤 -> 빈 seen으로 골드박스·간식 또 게시). 캐시가 다 지워졌을 때만 Run workflow의 cold_start로 처음부터
EVENTS = "events.json"  # 예약 게시(쿠가세 같은 행사): [{"at": "YYYY-MM-DD HH:MM"(KST), "text": HTML, "button", "url": 파트너스 링크}] — Claude가 저장소에 넣음
CP_NEWS = "https://newsis.com/RSS/industry.xml"  # 뉴시스 산업 RSS(기사 전문) -> 쿠팡 행사(○○데이·기획전) 자동 게시 — cp_events(). 쿠팡 뉴스룸은 GitHub 서버 403(10/9, 우회 안 함)
CP_HOME, CP_FRESH = "https://link.coupang.com/a/hHgmfLTIUm", "https://link.coupang.com/a/hHgxjTMio8"  # 파트너스 간편 링크(10/9 진우, 이름 붙여 보낸 것): 쿠팡 홈·로켓프레시 — 행사 글 버튼
REPOST = "ig_repost.txt"  # 오늘 인스타 카드를 1번 다시 올릴 때 날짜(YYYY-MM-DD) 한 줄 — ig_repost()
MUSIC = "music.json"  # 릴스 배경음악 목록: Pixabay 음원 주소(Claude가 고름) 또는 봇에 보낸 음악의 텔레그램 file_id. 음원 파일은 공개 저장소에 안 올림(무료 음원도 원본 재배포는 금지)
IG = "https://graph.%s.com/v25.0" % ("facebook" if E.get("IG_TOKEN", "").startswith("EAA") else "instagram")  # 인스타 자동 게시. IG_TOKEN = 앱 대시보드 '계정 추가'로 받은 Instagram 토큰(IGAA…, 60일, 카드 사진 자동) — 페이스북 페이지 토큰(EAA…)이면 페이스북 주소(릴스 영상 파일 업로드까지)
CP_HOST, CP_BASE = "https://api-gateway.coupang.com", "/v2/providers/affiliate_open_api/apis/openapi/v1"
CP_HOUR, CP_SEARCH_HOUR = 25, 6  # 쿠팡 API 최근 1시간 호출 상한(전체·검색, seen cpuse) — 공식 가이드: 검색 10·그 외 100/시간, 넘으면 24시간 차단·3번이면 파트너스 기능 차단 -> 여유 두고, 미검증 '계정 전체 30'도 안 넘게
CP_RUN, CP_SEARCH_RUN = 6, 2  # (10/24 진우 1주 ① 썸네일: 1 -> 2 — 시간당 CP_SEARCH_HOUR 6 그대로)  실행마다 상한 — 실패한 실행은 seen 캐시가 저장 안 돼(Actions 캐시 = 성공 때만) 그 호출이 다음 실행에 안 보임 -> 1시간 4~6번 실행이 다 실패해도 검색 ≤ 6·전체 ≤ 36
CP_RETRY_DAYS, CP_FAIL = 7, "cp_fail.json"  # 진열 상품이 서로 다른 날 2번 변환 실패하면 그 뒤엔 7일마다 1번(10/25 진우 '다 올려' — 사이트엔 쿠팡 주소 그대로 진열, 나중에 되면 파트너스 링크로) · 아직 안 바뀐 쿠팡 상품 주소 표(pid·이름·실패 날짜·마지막 시도·이유 — Cowork 점검용, 가격·수수료 X)
CP_DL_BATCH = 20  # 딥링크 한 호출에 묶는 쿠팡 주소 수 — shortcut: 공식 최대 개수는 문서에 없음(20으로), 묶음 오류면 반씩 나눠 다시 · 공식 수 알면 바꿈
CP_GROUP_MIN = 3  # T(10/26 진우): 사진 없는 쿠팡 글 = 품목 낱말(사이트 품목 칸 낱말) 같은 것 3개↑면 그 낱말로 검색 1번 먼저(7일에 1번) — 결과에 같은 pid 다 사진
CP_CHK_HOUR = 0  # ② 진우 쿠팡 상품 가격 확인(검색 API, pid마다 하루 1번) 시작 시각(KST) — 실행마다 1개라 75개면 ~17시
CP_QTY = r"\d+(?:\s*\+\s*\d+)+|(?<![a-z])[x×]\s*\d+(?![\d.]|\s*개)|\d+(?:\.\d+)?\s*(?:ml|kg|g|l|m|개입|개|팩|롤|포|정|구|캔|병|입|매|세트|박스|봉|켤레|족|판|장|p)(?![a-z])"  # 수량·용량·묶음(2+1·x2) 글자(같은 productId = 1팩/2팩·용량 옵션 묶음 -> 옵션 맞추기)
DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
AFF_NOTE = "이 포스팅은 제휴마케팅이 포함된 광고로 커미션을 지급 받습니다."  # 링크프라이스 머천트 안내 대가성 문구 그대로(10/5 머천트 정보 화면)
TOSS_NOTE = "이 콘텐츠는 토스쇼핑 쉐어링크 활동의 일환으로, 링크를 통한 구매가 발생하면 일정 수수료를 지급받습니다."  # 토스 권장 문구 (쉐어링크 가이드 '대가성 문구 표시하기', 10/5 확인)
NAVER_NOTE = "이 포스팅은 네이버 쇼핑 커넥트 활동의 일환으로, 판매 발생 시 수수료를 제공받습니다."  # 네이버 안내 문구 그대로(변형·누락 시 패널티), 글 맨 앞
LP = "💰 링크프라이스 최대 {} · 딥링크 만들어 답장"
OY_NOTE = "이 포스팅은 올리브영 쇼핑 큐레이터 활동의 일환으로, 구매 시 일정 금액의 수수료를 제공받습니다."  # 올리브영 활동 가이드 '반드시 표기해야 할 광고 표기 문구' 그대로(FAQ는 '제공 받습니다'로 띄어 씀 — 가이드·맞춤법 쪽으로), 제목·서두에(10/10)
STORES = {"쿠팡": "💰 쿠팡 파트너스 · 링크 만들어 답장", "토스": "💰 토스 쉐어링크 · 링크 만들어 답장",  # 뽐뿌 제목 [쇼핑몰] -> 초안 안내 버튼
          "g마켓": LP.format("0.6%"), "지마켓": LP.format("0.6%"), "옥션": LP.format("0.6%"), "롯데온": LP.format("1.4%"),
          "롯데on": LP.format("1.4%"), "하이마트": LP.format("1.26%"), "이마트": LP.format("1%"),  # 하이마트(10/5 자동 승인)는 '이마트'보다 먼저(글자 포함 관계)
          # ⏳ = 아직 링크를 못 만드는 몰 -> 사본 안 보냄(💰만 보냄). 승인 나면 LP.format("1.05%")·LP.format("6.3%")·LP.format("3.18%")로 바꾸기
          "11번가": "⏳ 11번가 링크프라이스 승인 대기 · 지금은 수수료 0", "알리": "⏳ 알리 링크프라이스 승인 대기(10/5 신청) · 지금은 수수료 0",
          "오늘의집": "⏳ 오늘의집 링크프라이스 승인 대기(10/5 신청) · 지금은 수수료 0",
          "네이버": "💰 네이버 쇼핑커넥트 · 상품 검색해 링크 발급 후 답장",  # 10/5 가입. 활동 제한 채널(일베·오유·워마드·다모앙·더쿠·일부 카페)에 우리 채널 없음 -> 허용. 판매자가 참여한 상품만 링크 발급 가능
          "올리브영": "💰 올리브영 쇼핑 큐레이터 · 앱에서 링크 만들어 답장(건기식·의료기기는 안 됨)"}  # 10/10 가입. 기프트카드·건기식·의료기기·본인 구매는 수익 0(FAQ)
# ponytail: 수수료율은 2026-10-05 링크프라이스 화면 기준 고정값. 바뀌면 여기만 고치면 됨
LP_AID = "A100708461"  # 링크프라이스 사이트 코드 (모든 링크프라이스 링크에 그대로 보이는 공개 값)
LP_SEARCH = {  # 링크프라이스 승인 몰: 제목 [쇼핑몰] -> (머천트, 표시 이름, 검색 주소). 상품 주소는 뽐뿌 차단으로 못 얻어서 검색 결과로 연결
    # 옥션은 승인됐지만 검색 결과 딥링크 미지원(메인으로 랜딩, 머천트 유의사항) -> 수동(관리자 사본에 상품 링크 답장)
    "g마켓": ("gmarket", "G마켓", "https://www.gmarket.co.kr/n/search?keyword="),
    "지마켓": ("gmarket", "G마켓", "https://www.gmarket.co.kr/n/search?keyword="),
    "롯데온": ("lotteon", "롯데온", "https://www.lotteon.com/csearch/search/search?render=search&platform=pc&q="),
    "롯데on": ("lotteon", "롯데온", "https://www.lotteon.com/csearch/search/search?render=search&platform=pc&q=")}
MALL_SEARCH = {  # 제휴 검색 링크가 없는 몰: 상품 주소를 못 꺼낸 딜(뽐뿌는 서버 차단)도 원글 대신 그 몰 검색 결과로(10/10 진우 '쇼핑몰로 바로, 구매자가 고민 덜 하게'). 10/10 크롬으로 검색 결과가 열리는지 확인(네이버쇼핑은 사이트 '같은 상품 찾기'와 같은 주소)
    "11번가": ("11번가", "https://search.11st.co.kr/Search.tmall?kwd="),
    "오늘의집": ("오늘의집", "https://ohou.se/search/index?query="),
    "카카오": ("카카오", "https://store.kakao.com/search/result/product?q="),
    "톡딜": ("카카오", "https://store.kakao.com/search/result/product?q="),
    "옥션": ("옥션", "https://www.auction.co.kr/n/search?keyword="),
    "쿠팡": ("쿠팡", "https://www.coupang.com/np/search?q="),
    "네이버": ("네이버쇼핑", "https://search.shopping.naver.com/search/all?query=")}
CP_SEARCH = "https://partners.coupang.com/#affiliate/ws/link/0/"  # 파트너스 '상품 링크' 검색 결과를 바로 여는 주소(10/6 확인: 새로 열어도 검색됨, 상품 주소로는 검색 안 됨)
NAVER_SC = "https://brandconnect.naver.com/1003150047355424/affiliate/products"  # 쇼핑커넥트 상품 찾기(진우 스페이스, 로그인 필요). 봇 자동 발급은 네이버 정책상 금지(7/9 공지: 매크로 감지 시 7일 발급 제한)
LP_API = "https://api.linkprice.com/ci/service/custom_link_xml?a_id={}&mode=json&url={}"  # 링크프라이스 딥링크 API: 승인된 몰이면 S + 링크, 아니면 F(승인거부·유효하지 않은 URL)
LP_HOSTS = {"gmarket.co.kr": "gmarket", "auction.co.kr": "auction", "lotteon.com": "lotteon", "emart.ssg.com": "emart"}  # API 장애 때만 쓰는 승인 몰 목록(직접 딥링크)
HOST_STORES = {"coupang.com": "쿠팡", "naver.com": "네이버", "toss.im": "토스", "toss.shopping": "토스", "11st.co.kr": "11번가",
               "aliexpress": "알리", "auction.co.kr": "옥션", "emart.ssg.com": "이마트", "e-himart.co.kr": "하이마트", "ohou.se": "오늘의집", "oliveyoung.co.kr": "올리브영",
               "naver.me": "네이버", "oy.run": "올리브영"}  # 제목에 [쇼핑몰]이 없을 때(클리앙) 주소로 몰 판단
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
esc = html.escape

REEL_RULES = """e: 상품을 한눈에 보여줄 이모지 1개 (예: 🥛 🍠 🧻 🔋 👟).
hook: 릴스 첫 화면 한 줄, 14자 이내, 숫자 중심(개당·100g당 같은 단위가격이나 핵심 혜택). 예: "우유 팩당 495원". 계산은 제목·본문의 가격과 수량으로만.
pts: 합리적인 소비인 이유 2~3개, 각 14자 이내, 사실만(할인 조건·용량·보관·구성). 배송비·단위가격은 따로 표시되니 빼고, 평소가·최저가·역대가는 글에 나온 경우만.
unit: 단위가격 한 줄(예: "100g당 990원", "개당 495원", "1L당 1,980원"). 제목·본문의 가격과 수량으로 확실히 계산될 때만, 아니면 빈 문자열.
warn: 사기 전에 확인할 점 1개, 16자 이내(예: "쿠폰 1인 1회", "옵션별 가격 다름", "카드할인 적용가"). 글에 근거 있을 때만, 없으면 빈 문자열."""
DEAL_PROMPT = """너는 한국 핫딜 텔레그램 채널 편집자야. 아래 딜 중 구독자가 실제로 살 만한 것만 골라 pick 도구로 반환해.
점수(1~10) 기준: 가격 매력, 생필품/대중성, 커뮤니티 반응(조회 대비 추천·댓글). 비추천이 많거나 품절·종료·가격오류 언급이 있으면 제외.
comment: 구독자용 1~2줄. 핵심 조건(쿠폰·카드할인·무배 등)을 사실대로. 과장 금지, 확인 안 된 '역대최저' 금지, 건강식품·화장품 효능(미백·주름·탄력 개선 등) 언급 금지, 이모지 최대 1개.
[올리브영] 딜 comment·hook·pts·warn은 가격·용량·구성·조건만: 후기·체험담·글쓴이 경험, '추천'·'좋아요'·'쟁여두기' 같은 권유, 효능·효과, '최고'·'100%' 같은 절대 표현 금지(올리브영 쇼핑 큐레이터 정책).
q: 쇼핑몰 검색창에 넣을 짧은 검색어(브랜드+상품명+핵심 용량, 수량·가격·쿠폰 문구 빼고 20자 안팎).
REEL_RULES
같은 상품이 여러 커뮤니티([뽐뿌]·[루리웹]·[클리앙])에 올라왔으면 하나만 골라.
5점 미만은 반환하지 마.
"""
DEAL_PROMPT = DEAL_PROMPT.replace("REEL_RULES", REEL_RULES)
ADMIN_PROMPT = DEAL_PROMPT.replace("5점 미만은 반환하지 마.", "점수와 상관없이 반드시 반환해(약한 딜은 점수를 낮게).") + \
    "이번 딜은 운영자가 쇼핑몰에서 직접 고른 상품이라 커뮤니티 반응 정보가 없어: 가격 매력·대중성만으로 점수를 매기고, 운영자가 적은 가격·조건만 사실로 써(모르는 건 지어내지 마).\n"
REEL_PROMPT = "아래 딜 각각(모든 i)에 대해 인스타 릴스용 정보를 pick 도구로 반환해. score는 0, comment는 빈 문자열.\n" + REEL_RULES + "\n" \
    + "건강식품·화장품 효능(미백·주름·탄력 개선 등) 금지. [올리브영] 딜은 가격·용량·구성·조건만(후기·추천·권유·효능·'최고' 같은 절대 표현 금지 — 올리브영 쇼핑 큐레이터 정책).\n"
GOLD_PROMPT = """쿠팡 골드박스(오늘 하루 특가) 목록이야. 할인율은 정가를 부풀린 경우가 많으니 믿지 말고 구성·단위가격으로 판단해서,
대중적이고 '지금 사도 싸다' 싶은 상품만 최대 5개 pick 도구로 반환해. 억지로 5개 채우지 말고, 없으면 빈 목록 (10/7 진우: 살 만한 제품만).
comment: 1줄, 사실 위주, 과장 금지, 건강식품·화장품 효능(미백·주름·탄력 개선 등) 언급 금지.
"""
BEST_PROMPT = """토스쇼핑에서 지금 많이 팔리는 상품 목록이야(가격 = 배송비 포함 결제가). 많이 팔린다고 싼 건 아니고 할인율은 정가를 부풀린 경우가 많으니
믿지 말고 구성·단위가격·리뷰로 판단해서, 대중적이고 '지금 사도 싸다' 싶은 것만 최대 3개 pick 도구로 반환해. 없으면 빈 목록.
comment: 1줄, 단위가격 등 사실 위주, 과장 금지, 건강식품·화장품 효능(미백·주름·탄력 개선 등) 언급 금지.
"""
# 10/10 진우 '기준만 완화': 진우가 보낸 토스 베스트·하루특가 22개를 쿠팡 같은 상품과 비교하니 전부 토스가 쌌는데 봇은 일부만 골랐음
TOSS_EASE = "토스 상품은 쿠팡 같은 상품보다 싼 경우가 많아: 단위가격·구성·리뷰로 봐서 시중가보다 비싸 보이거나 비대중적인 것만 빼고, 대중적인 생필품·식품이면 골라. 설화수처럼 이름 있는 브랜드 상품은 시중가 수준이면 우선 골라(10/10 진우 '브랜딩 파워 있는 제품도 꼭, 꾸준히').\n"
BEST_PROMPT += TOSS_EASE
SPECIAL_PROMPT = """토스쇼핑 특가 후보 목록이야(할인율 높고 리뷰 있는 상품, 가격 = 배송비 포함 결제가). 할인율은 정가를 부풀린 경우가 많으니 믿지 말고 구성·단위가격·리뷰로 판단해서
대중적이고 '지금 사도 싸다' 싶은 것만 최대 5개 pick 도구로 반환해(score = 지금 사도 싼 정도 1~10). 없으면 빈 목록.
comment: 1줄, 단위가격 등 사실 위주, 과장 금지, 건강식품·화장품 효능(미백·주름·탄력·재생 개선 등) 언급 금지, 쿠팡 등 다른 쇼핑몰 가격 비교 언급 금지(토스 API 신청 범위).
"""
PICK_PROMPT = """토스쇼핑 상품 1개야(가격 = 배송비 포함 결제가, 할인율은 정가를 부풀린 경우가 많음). 채널 글에 붙일 한 줄(comment)과 '지금 사도 싸다' 점수(score 1~10)를 pick 도구로 반환해(i = 0).
comment: 1줄, 구성·단위가격·리뷰 등 사실 위주, 과장 금지, 건강식품·화장품 효능(미백·주름·탄력·재생 개선 등) 언급 금지, 쿠팡 등 다른 쇼핑몰 가격 비교 언급 금지(토스 API 신청 범위).
"""
TOSS_WU = """unit: 단위가격 1줄(예: "병당 약 535원 (24병)", "1L당 약 1,175원 (총 8L)") — 가격·구성으로 확실히 계산될 때만, 다른 쇼핑몰 이름·비교 없이, 아니면 빈 문자열.
who: 이 상품이 필요한 사람 1줄, 30자 안, 2개까지 ' · '로 — 상품명·구성·카테고리에서 나오는 구체적인 사람·상황(예: "설거지 많은 집 · 사무실 탕비실").
use: 이렇게 쓰면 좋은 때 1줄, 40자 안, 한 가지 상황만 — 언제·어떻게 쓰는지·보관(예: "차갑게 해서 식후 한 병").
who·use는 간단하게, 한 번 읽고 '나한테 필요하네' 싶게 짧고 구체적으로. 금지: 써 본 척(제가·써보니·먹어보니·발라보니), 효능·건강·의학(다이어트·혈당·면역·피로·피부 개선·미백·주름·탄력·재생·탈모·여드름·트러블·관절·숙면 등), 다른 쇼핑몰 이름·비교, 과장·조급(역대급·무조건·손해·마지막 기회), 클릭 유도(클릭·눌러).
"""  # 10/20 진우 '토스 글 멘트 사고 싶게 — 간단하게, 필요한 사람이 살 수 있게': 토스 쉐어링크 개별 글 💡 한 줄 -> 💰·🙋·👍 3줄(묶음 글은 그대로)
BEST_PROMPT += TOSS_WU
SPECIAL_PROMPT += TOSS_WU
PICK_PROMPT += TOSS_WU
DEAL_PROMPT += "who·use는 토스 상품(제목 [토스]·[토스쇼핑]이거나 본문에 토스·토스쇼핑 링크)일 때만, 다른 몰은 빈 문자열:\n" + TOSS_WU.split("\n", 1)[1]
ADMIN_PROMPT += "who·use(토스 링크 글에만 나감):\n" + TOSS_WU.split("\n", 1)[1]  # 링크는 Claude에 안 보여서 조건 없이(글에 붙일지는 코드가 링크로 정함 — 10/20 리뷰)
SCAN_PROMPT = """아래는 토스쇼핑 하위 카테고리 목록이야. 다음 상품들이 들어 있을 만한 하위 카테고리를 pick 도구로 골라(상품마다 1~2개, 전체 최대 10개, score = 확신도 1~10, comment = 어느 상품용인지):
{}
"""
MATCH_PROMPT = """커뮤니티 핫딜 글 제목: {}
아래는 토스쇼핑 상품 목록이야. 이 핫딜과 같은 상품(브랜드·상품명·용량·수량·구성이 같음. 가격은 쿠폰·특가 때문에 달라도 됨)을 최대 1개 pick 도구로 골라.
확신이 없거나 같은 상품이 없으면 아무것도 고르지 마. score = 확신도 1~10, comment = 판단 이유 짧게.
"""
EVENT_PROMPT = """오늘은 {}. 아래는 쿠팡 관련 새 뉴스 기사·커뮤니티 핫딜 글이야(제목 | 날짜 | 본문). 쿠팡 고객이 지금 또는 곧 쿠팡 앱에서 참여할 수 있는 할인 행사(○○데이·기획전·세일)만 pick 도구로 골라.
회사 소식·실적·협약·물류·사회공헌·채용·오프라인 행사·단일 상품 판매 시작·이미 끝난 행사·쿠팡이츠·쿠팡플레이는 빼. 글에 적힌 사실만 써(지어내지 마).
q = 행사 이름(쿠팡 앱 검색어, 예: 뷰티풀데이), hook = 기간·대상 한 줄(예: 10/18(일)까지 · 와우회원), pts = 핵심 혜택 2~3개(각 30자 안),
e = 어울리는 이모지 1개, comment = 고른 이유 짧게, score = 고객에게 쓸모 1~10(6 이상만 게시).
"""
CP_REMIND_HOURS = (13, 19)  # 쿠팡 링크 아직 안 만든 오늘 딜 사본을 관리자에게 다시(10/8 진우 '쿠팡 링크 공유 쉽게') — coupang_remind()
IG_SLOTS = {11: "점심 전에 볼 딜", 13: "점심에 볼 딜", 15: "오후에 볼 딜", 17: "퇴근 전에 볼 딜", 19: "퇴근길에 볼 딜", 9: "출근길에 볼 딜", 12: "점심에 볼 딜", 18: "퇴근길에 볼 딜"}  # 10/23 진우 '너무 자주 말고 하루 4번' + 단계적 늘리기: 칸 = 오늘 앞 칸 시각(첫 칸 0시) ~ 그 시각 딜
IG_STAGES = ((11, 15, 19), (11, 13, 15, 19), (11, 13, 15, 17, 19))  # 단계 0 = 하루 4번(+22시 하루 카드) · 1 = 5번(+13시) · 2 = 6번(+17시) — ig_stage가 매일 0시에 판정
IG_STAGE_FILE, IG_STAGE_DAYS = "ig_stage.json", 3  # 단계 기록(커밋 — seen을 잃어도 단계 그대로, 판정 줄 log = README 점검 표) · 올림 = 그 단계로 3일 + 앞 3일 진짜 실패 0(5 -> 6번은 + 글당 조회)
IG_DAY_HOUR, IG_OWN_HOUR = 22, 19  # 22시 = 하루 카드(21시 모아보기 카드를 인스타엔 22시에) · 19시 칸은 진우 쿠팡 🔥·👍 먼저
IG_START = "2026-10-23 15"  # shortcut: 첫날(10/23)은 15시 칸부터(진우 '11시 칸이 이미 지났으면 15시부터') — 10/24부터는 안 씀, 그 뒤 지워도 됨
IG_LATE, IG_MIN = 2, 3  # 칸은 그 시각 2시간 안에만(늦게 몰아 안 올림) · 딜 3개 미만이면 건너뜀(억지로 안 채움) · 하루 발행 최대 = 그 단계 횟수 + 1(ig_day_max — 오류로 몰려 올라가지 않게, API 상한 50)
IG_CAROUSEL, SLIDE_KEEP, KIDS_WAIT = True, 2, 3600  # 넘기기(10/11 진우 '인스타 업그레이드 2번'): 표지 + 딜마다 1장(False면 1단계 한 장 카드) · 딜 카드는 인스타가 가져간 뒤 2일 지나면 지움(저장소 크기) · 조각 처리 1시간 넘으면 버림
OY_DENY = r"후기|리뷰|추천|댓글|반응|좋|최고|100%|효과|효능|강추|쟁여|인생|대박|미백|주름|탄력|개선"  # 올리브영 딜 카드에서 빼는 말(큐레이터 정책: 가격·용량·구성·조건만)
REEL_PUBLIC, REEL_HOUR, REEL_THUMB_MS = True, 22, 1500  # 10/26 00:3x 진우 J-1 '배경음악도 넣어줘' = 공개 OK(라이선스 기록된 Pixabay 곡만 — Content ID 미등록)  # 릴스 자동(10/11 진우 '인스타 업그레이드 3번'): 영상을 docs/reels/에 공개 -> 인스타가 video_url로 가져감. 음원(Pixabay) 든 영상 공개는 진우 확인 뒤 True · 22시(21시 카드와 간격) · 표지 = 1.5초(첫 화면 다 뜬 뒤)
IG_TRIES, IG_SITE_LAG = 3, 300  # 릴스 컨테이너 만들기 실패는 3번까지 다시(IG_H 끈 때만 — H 공개 릴스·카드 = 다시 시도 X) · 카드는 사이트 맨 위에 먼저(만든 실행) -> 5분 넘은 다음 실행에 발행
IG_TAGS, IG_CAT_TAGS, IG_FILL_TAGS, IG_TAG_MAX = ("#핫딜", "#핫딜픽"), {"life": "#생필품", "beauty": "#화장품"}, ("#특가", "#살림템", "#쇼핑정보", "#할인정보", "#가성비템", "#쟁여템", "#장바구니", "#오늘의딜"), 5  # 해시태그 5개(근거 없는 #최저가 뺌, 카테고리 태그는 그날 딜에 있을 때만, 채움은 칸마다 돌림)
TOP_HOURS = (12, 15, 18)  # 10/12 01:25 진우 '좋은 딜은 묶어서 중간에 리스트도' -> 15시 추가(Threads 시청 피크 목·금 15~18시) · 커뮤니티 반응 좋은 딜 TOP5 묶음 글(10/9 진우 '사람들이 사는 제품을 보기 좋고 사고 싶게') — top_deals()
NUM = "1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣".split()
TOSS_DAY_HOURS = (9, 13, 17, 20)  # 하루특가(= 토스 앱 '매일 밤 12시 선착순특가') 회차, 회차마다 안 올린 것 최대 5개 (10/10 진우가 선착순 상품 링크를 직접 보내다가 '이 작업도 자동으로')
TOSS_BEST_HOURS = (10, 11, 12, 14, 16, 18, 20)  # 10/11 진우 '회차 늘리기, 적절하게': 7일 표에서 묶음 글 없는 11시 추가(12시는 TOP5와 겹침). 줄이려면 여기서 빼기. 토스 '지금 많이 팔리는 상품'(1시간마다 갱신) 중 Claude가 살 만한 것만: 10~20시 2시간마다 (10/7 진우 제안 2번 -> 10/8 3번 -> 10/9 '쿠팡·토스 주력' 6번)
TOSS_BEAUTY_HOURS = (15, 19)  # 토스 뷰티(화장품) 카테고리 베스트 중 살 만한 것 (10/11 진우 '화장품도 올리자' -> '화장품도 발굴': 저녁 1번 더 = 7일 표에서 저녁 중 가장 조용하고 묶음 글 없는 19시)
AD_FIRST = ""  # 10/12 00:40 진우 결정 '첫 줄 변경 취소': 예전 형식(고지문 첫 줄 → 💸 쿠팡보다 N원 싸요 → 🔥 제목 → … — 23:33 에이지랩 크림 글 51분 조회 20)이 더 좋음, 2주 동결.
# 날짜(KST, 예 "2026-10-12")를 넣으면 그날부터 개별 딜 글(채널·Threads) 첫 줄 '[광고] + 훅 + 상품 + 가격'(10/11 결정, 10/12 0:01~0:5x만 나감). "" = 예전(고지문이 첫 줄)


def ad_on():
    return bool(AD_FIRST) and time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600)) >= AD_FIRST
TH_REPLY = True  # Threads 댓글(reply_to_id) 쓰기(투표 결과 답글·링크 B 첫 댓글 — th_reply_ok가 토큰 권한 확인) · False = 댓글 안 씀. 22시 미리보기는 10/25부터 댓글(타래) 안 씀(글 1개)
PREVIEW_HOUR, PREVIEW_MIN, PV_NAME = 22, 3, 13  # PV_NAME = Threads 미리보기 짧은 이름이 안 될 때 자르는 길이(10/25 Cowork 390px — '시각 이름 · 가격'이 한 줄, 낱말 단위, '…' X) · 10/11 진우 '묶음 리스트도, 꾸준함이 중요': 매일 밤 10시 '🌙 오늘 밤 특가 미리보기'(진우 예약 딜 중 지금~다음 날 8시) — 진우 예약은 17~24시에 몰림(10/10 20~22시 34개, 10/11 밤 19개)·토스 하루특가는 밤 12시에 바뀜 · 3개 미만이면 21시 모아보기에 합침 · Threads는 앞 5개(500자)
PICK_TH_AT, PICK_TH_END, PICKS_FILE = "10:30", "14:00", "docs/today/picks.json"  # N2(10/24 진우 'Threads 유입 중요'): 사이트가 10시 뒤 첫 빌드에 고정·배포한 오늘의 픽 -> Threads 하루 1번
BUNDLE_GAP, HOUR_CAP = 600, 8  # 10/11 진우 '너무 자주 올리면 역효과': 묶음 글(토스 회차·TOP5·모아보기)은 앞 묶음 글과 10분 이상 띄움 / 토스 회차는 최근 1시간 채널 글이 8개 이상이면 미룸(7일 표: 평소 시간당 최대 6개 -> 진우 예약이 몰린 시간에만 걸림)
TH_REOPEN_NIGHT, TH_REOPEN_MORN, TH_REOPEN_DAY = 2, 2, 4  # 10/12 진우 '6시부터 해도 괜찮아, 한도 관리': 재오픈 Threads 글은 개별 5개와 따로 — 밤(0~6시) 2개 + 아침(6시~) 2개, 하루 4개까지, 일반 딜이 먼저(main 순서)
TH_REOPEN_GAP, TH_REOPEN_HOUR, TH_REOPEN_AM = 600, 3, (6, 11)  # (10/12: 아침 8시 -> 6시) 10/11 진우 '토스 품절 풀리면 다시 쓰레드에, 자정 + 아침 8시': 재게시끼리 10분(= 실행당 1개) · 1시간 최대 3개(7일 표: 0~3시 채널 시간당 1~4.5개, 8시 2개 -> 그 시간 평소 글 수 수준) · 아침 재알림은 8~11시(놓치면 낮에 몰아 안 올림)
TOSS_SPECIAL_HOURS, SPECIAL_DR, SPECIAL_RC = (8, 22), 40, 50  # 10/11 진우 '특가 탭 자동으로': 토스 특가(할인 40%↑·리뷰 50개↑) 회차 — 7일 표에서 묶음 글 없는 아침 8시(시간당 2개)·밤 22시(4개), 회차 3시간 안에만. 줄이려면 여기서 빼기
PICK_AHEAD, PICK_LATE, PICK_SCAN, PICK_ASK = 8 * 3600, 3 * 3600, 10, 90 * 60  # 토스 이름 예약(toss_picks): 8시간 전부터 찾음 · 예약 시각 3시간 지나면 안 올림 · 못 찾으면 하위 카테고리 베스트 하루 10개(1,000개 — 일 상한 10,000 안)까지 더 봄 · 그래도 없거나 90분 전이면 진우에게 링크 요청
BEAUTY = dict((k, rx) for k, _, rx in CATS)["beauty"]  # 화장품 제목 키워드(사이트 '💄 화장품' 칸과 같음)
TOSS_CAT_HOUR, TOSS_CATS = 17, ("식품", "생활용품")  # 카테고리 베스트(매일 9시 갱신) 중 살 만한 것: 하루 1번 (10/8 진우: 베스트 랭킹 페이지). 이름 = 카테고리 트리 최상위


def http(url, body=None, headers=None, method=None):
    if url.startswith(IG):  # 인스타 그래프 API 호출 수(10/22 'Application request limit reached' — 실행마다 로그 'ig api N calls')
        RUN["igc"] = RUN.get("igc", 0) + 1
    h = {"User-Agent": UA, **(headers or {})}
    if body is not None and not isinstance(body, bytes):  # bytes = 폼 등 이미 인코딩된 본문(Content-Type은 headers로)
        body, h["Content-Type"] = json.dumps(body).encode(), "application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, body, h, method=method), timeout=30) as r:
            return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")
    except urllib.error.HTTPError as e:
        e.body = e.read().decode("utf-8", "replace")[:300]  # 로그에서 원인 바로 보이게
        print("HTTP", e.code, url.split("/bot")[0].split("?")[0], re.sub(r"\?[^\s\"'<>]*", "?…", e.body))  # 주소·오류 글의 쿼리(토큰·키·프로젝트 번호) = 공개 로그 X(10/25 리뷰)
        raise


def tg_video(path, caption):
    """관리자에게 영상 파일 업로드 (sendVideo, multipart). -> 보낸 메시지"""
    b = "hotdeal" + os.urandom(8).hex()
    fields = {"chat_id": ADMIN, "caption": caption, "supports_streaming": "true", "width": "1080", "height": "1920"}
    if time.gmtime(time.time() + 9 * 3600).tm_hour < 8:  # 밤(KST 0~8시) = 무음(tg와 같게 — 관리자 안 깨움)
        fields["disable_notification"] = "true"
    body = ("".join(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n' for k, v in fields.items())
            + f'--{b}\r\nContent-Disposition: form-data; name="video"; filename="{os.path.basename(path)}"\r\nContent-Type: video/mp4\r\n\r\n').encode() \
        + open(path, "rb").read() + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{E['TG_TOKEN']}/sendVideo", body,
                                 {"Content-Type": f"multipart/form-data; boundary={b}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())["result"]


def tg(method, **params):
    """텔레그램 API. 실패해도 전체 실행은 멈추지 않고 None 반환. 밤(KST 0~8시) 발송은 무음(구독자·관리자 안 깨움)."""
    if method in ("sendMessage", "copyMessage", "sendPhoto") and time.gmtime(time.time() + 9 * 3600).tm_hour < 8:
        params.setdefault("disable_notification", True)
    text = params.get("text") or ""
    if method == "sendMessage" and len(text) > 4096 and "reply_markup" not in params and "parse_mode" not in params:  # 텔레그램 4096자 제한(10/6 블로그용 글 실패) -> 문단 단위로 나눠 보냄. 버튼 달린 초안은 안 나눔, HTML 글도 안 나눔(한도는 태그·주소 뺀 글자 수 — 10/10 21시 모아보기가 <a> 중간에서 잘려 400)
        parts = []
        for para in text.split("\n\n"):
            if parts and len(parts[-1]) + 2 + len(para) <= 4096:
                parts[-1] += "\n\n" + para
            else:
                parts.append(para)
        r = None
        for p in parts:
            r = tg(method, **{**params, "text": p[:4096]})
        return r
    try:
        r = json.loads(http(f"https://api.telegram.org/bot{E['TG_TOKEN']}/{method}", params))["result"]
        if params.get("chat_id") == CHANNEL and method in TG_SEND:
            RUN["ok"].add("tg")
            if "reply_parameters" not in params and not re.search(r"^📋", text, re.M):  # 채널 딜 글 시각(재오픈 답장·모아보기 X) -> toss_solo 빈틈 채움
                RUN["ch_last"] = time.time()
        return r
    except urllib.error.HTTPError as e:
        print("TG", method, e.code, e.body)
        if params.get("chat_id") == CHANNEL and method in TG_SEND:  # 채널 글 실패 = 실행 끝에 관리자에게 바로(watch)
            RUN["fail"][f"{method} {e.code}"] = RUN["tg_err"] = f"{method} {err_brief(e)}"


def fetch_deals():
    """모든 출처의 새 글 -> [{id, url, board, title, desc, hits, age(분)}]. 출처 하나가 죽어도 나머지는 진행."""
    deals = []
    for board, name in FEEDS.items():
        try:
            deals += ppomppu_feed(board, name)
        except Exception as e:
            print("feed", board, repr(e))
    for feed in (ruliweb_feed, clien_feed):
        try:
            deals += feed()
        except Exception as e:
            print("feed", feed.__name__, repr(e))
    return deals


def ppomppu_feed(board, name):
    deals = []
    for it in ET.fromstring(http(f"https://www.ppomppu.co.kr/rss.php?id={board}")).iter("item"):
        url = it.findtext("link", "").replace("http://", "https://")
        no = re.search(r"no=(\d+)", url).group(1)
        h = (it.findtext("hits") or "").strip(" []").split("|")
        deals.append({
            "id": f"{board}_{no}", "url": url, "board": name,
            "title": it.findtext("title", "").strip(),
            "desc": html.unescape(it.findtext("description", "")).replace("\xa0", " ").strip()[:200],
            "hits": "댓글{}·조회{}·추천{}·비추{}".format(*h) if len(h) == 4 else "",
            "age": (time.time() - parsedate_to_datetime(it.findtext("pubDate")).timestamp()) / 60,
        })
    return deals


def ruliweb_feed():
    """루리웹 핫딜예판 RSS (반응 수치는 없음, 분류는 desc로)."""
    deals = []
    for it in ET.fromstring(http(RULIWEB_RSS)).iter("item"):
        url = it.findtext("link", "").strip()
        deals.append({"id": "ruliweb_" + url.rsplit("/", 1)[-1], "url": url, "board": "루리웹",
                      "title": it.findtext("title", "").strip(), "desc": f"분류: {it.findtext('category', '').strip()}", "hits": "",
                      "age": (time.time() - parsedate_to_datetime(it.findtext("pubDate")).timestamp()) / 60})
    return deals


def clien_feed():
    """클리앙 알뜰구매 목록 HTML (공지 제외). 시간은 KST 'YYYY-MM-DD HH:MM:SS'."""
    deals, page = [], http(CLIEN_LIST)
    for cls, sn, cmt, row in re.findall(r'class="list_item ([^"]*)" data-role="list-row"[^>]*?data-board-sn=(\d+)[^>]*?'
                                        r'data-comment-count=(\d+)>(.*?)(?=class="list_item |$)', page, re.S):
        title, ts = re.search(r'class="list_subject"[^>]*title="([^"]*)"', row), re.search(r'class="timestamp">([\d-]+ [\d:]+)<', row)
        if "notice" in cls or not (title and ts):
            continue
        like, hit = re.search(r'list_votes"><i[^>]*></i>\s*(\d+)', row), re.search(r'class="hit">([\d,]+)<', row)
        at = datetime.strptime(ts.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=KST).timestamp()
        deals.append({"id": f"clien_{sn}", "url": f"{CLIEN_LIST}/{sn}", "board": "클리앙", "title": html.unescape(title.group(1)).strip(),
                      "desc": "", "hits": f"댓글{cmt}·조회{hit.group(1) if hit else '?'}·추천{like.group(1) if like else 0}",
                      "age": (time.time() - at) / 60})
    return deals


def mark_hot(deals):
    """커뮤니티 반응 좋은 딜 강조(10/9 진우 '선호도 좋은 품목 딜 강조 표시', 기준 = 커뮤니티 반응): 게시판별 지금 목록에서
    분당 조회수 3위 안(분당 20회 이상) 또는 추천 3개 이상 -> d["hot"] = 이유. 루리웹은 반응 수치가 없어서 해당 없음."""
    num = lambda d, k: int(m[1]) if (m := re.search(k + r"(\d+)", d.get("hits") or "")) else 0
    for d in deals:  # TOP5 묶음·사이트 인기 칸 순위용(분당 조회수 + 추천×5), 보여 줄 땐 분당 조회·추천을 따로(react)
        if d["age"] >= 5 and num(d, "조회"):
            d["vpm"], d["rec"] = round(num(d, "조회") / d["age"], 1), num(d, "추천")
            d["pop"] = round(num(d, "조회") / d["age"] + 5 * d["rec"], 1)
    for board in {d["board"] for d in deals}:
        peers = sorted((d for d in deals if d["board"] == board and d["age"] >= 5 and num(d, "조회") / d["age"] >= 20), key=lambda d: -num(d, "조회") / d["age"])
        for rank, d in enumerate(peers[:3], 1):
            d["hot"] = f"{board}에서 지금 많이 보는 글 {rank}위"
    for d in deals:
        if num(d, "추천") >= 3:
            d["hot"] = f"{d['board']} 추천 {num(d, '추천')}"
    for d in deals:  # 올리브영 딜은 '추천'·반응 수치 표시 안 함(쇼핑 큐레이터 정책: 사용자 후기·추천 표현 금지) -> 배지·인기 칸·TOP 글에서 빠짐
        if is_oy(d["title"]):
            for k in ("hot", "pop", "vpm", "rec"):
                d.pop(k, None)


def ai_pick(prompt, lines):
    """Claude가 고른 [{i, score, comment}] (점수 내림차순)."""
    tool = {"name": "pick", "description": "게시할 항목", "input_schema": {
        "type": "object", "required": ["picks"], "properties": {"picks": {"type": "array", "items": {
            "type": "object", "required": ["i", "score", "comment"],
            "properties": {"i": {"type": "integer"}, "score": {"type": "integer"}, "comment": {"type": "string"},
                           "q": {"type": "string"}, "e": {"type": "string"}, "hook": {"type": "string"},
                           "pts": {"type": "array", "items": {"type": "string"}}, "unit": {"type": "string"}, "warn": {"type": "string"},
                           "who": {"type": "string"}, "use": {"type": "string"}}}}}}}
    r = json.loads(http("https://api.anthropic.com/v1/messages", {
        "model": MODEL, "max_tokens": 8000, "tools": [tool], "tool_choice": {"type": "auto"},  # 10/19 17:23 커뮤니티 글 많은 회차에 4000으로 picks가 잘림(다음 실행 복구) -> 8000(쓴 만큼만 과금)
        "messages": [{"role": "user", "content": prompt + "\n" + "\n".join(f"{i}. {l}" for i, l in enumerate(lines))}],
    }, {"x-api-key": E["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"}))
    tu = next((c["input"] for c in r["content"] if c["type"] == "tool_use"), {"picks": []})  # 도구를 안 부르면 고른 게 없는 것
    if "picks" not in tu:  # 빈 입력·잘린 답 = 실패(10/8 11:12 KeyError로 실행 전체가 죽음, 15분 뒤 같은 목록에서 7점 2개) -> 본 글 기록 안 하고 다음 실행에 다시
        raise RuntimeError(f"Claude 답에 picks 없음({r.get('stop_reason')})")
    picks = tu["picks"]
    return sorted((p for p in picks if 0 <= p["i"] < len(lines)), key=lambda p: -p["score"])


def store_link(post_url):
    """딜 글에 적힌 실제 쇼핑몰 주소 (남의 제휴 링크·추적값은 plain()으로 걷어냄). 못 찾으면 None.
    루리웹: 글 아래 '출처'(web.ruliweb.com/link.php?ol=원래주소, 네이버·토스는 주소 그대로). 클리앙: 글 위 '구매링크'(attached_link).
    뽐뿌: 상단 링크(s.ppomppu.co.kr ... target=base64) — 뽐뿌는 서버 IP의 글 페이지를 403 차단(GitHub 10/5 linkcheck·오라클 10/9 확인, 우회 안 함)
    -> None -> 검색 제휴 링크 또는 관리자 답장, 사이트엔 '같은 상품 찾기'. (차단이 풀리면 이 파서가 그대로 동작)"""
    try:
        page = http(post_url)
    except Exception as e:
        print("link", post_url, repr(e))
        return None
    if "ruliweb.com" in post_url:
        m = re.search(r'class="source_url.*?href="([^"]+)"', page, re.S)  # 보통 link.php?ol=원래주소, 네이버·토스 등은 주소 그대로
        u = html.unescape(m.group(1)) if m else ""
        if not m:  # '출처' 칸 없이 본문에만 주소를 적은 글(10/8 [토스] 핫식스 -> 버튼이 루리웹 글로 감) -> 본문(view_content)의 첫 토스·쿠팡 주소
            body = page.partition('class="view_content')[2].partition("</article>")[0]
            u = next((x for x in re.findall(r"https?://[\w.-]+/[\w./?=&%#~+-]*", body, re.A)
                      if urllib.parse.urlsplit(x).netloc.endswith(TOSS_HOSTS + ("coupang.com", "coupa.ng"))), "")
        return plain(urllib.parse.parse_qs(urllib.parse.urlsplit(u).query).get("ol", [None])[0] if "link.php" in u else u)
    if "clien.net" in post_url:
        m = re.search(r'class="attached_link.*?href=[\'"]([^\'"]+)', page, re.S)
        return plain(html.unescape(m.group(1)).strip()) if m else None
    m = re.search(r'topTitle-link.*?href="https://s\.ppomppu\.co\.kr/\?([^"]+)"', page, re.S)
    if not m:
        return None
    q = "&" + html.unescape(m.group(1))
    t = urllib.parse.unquote(re.search(r"&target=([^&]*)", q + "&target=").group(1))  # unquote_plus 쓰면 base64의 +가 깨짐
    return plain((base64.b64decode(t + "=" * (-len(t) % 4)).decode() if "&encode=on" in q else t) or None)


class _Stay(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):  # 리다이렉트를 따라가지 않음 -> Location만 읽기
        return None


def location(url):
    """단축·제휴 링크가 보내는 다음 주소 (페이지는 안 받음)."""
    try:
        urllib.request.build_opener(_Stay).open(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=15)
    except urllib.error.HTTPError as e:
        return urllib.parse.urljoin(url, e.headers.get("Location") or "") or None
    except Exception as e:
        print("location", url, repr(e))
    return None


def plain(url, hops=4):
    """남의 제휴 링크(쿠팡 파트너스·링크프라이스 등)·추적값 -> 원래 쇼핑몰 주소. 우리 제휴 링크로 다시 만들기 위해.
    링크프라이스는 tu=, 쿠팡·네이버(naver.me)·토스 단축은 리다이렉트를 따라감. 원래 주소를 못 찾으면 None(남의 링크를 그대로 쓰지 않음)."""
    if not url or not url.startswith("http"):
        return None
    p = urllib.parse.urlsplit(url)
    host, qs = p.netloc.lower(), urllib.parse.parse_qs(p.query)
    if not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}(:\d+)?", host):  # '출처' 칸에 '토스'만 적은 글 -> https://토스 -> 텔레그램 버튼 400으로 딜을 못 올림(10/9 22:40 느린농장)
        return None
    if host == "click.linkprice.com":
        return plain(qs["tu"][0], hops) if "tu" in qs else None
    if host == "service.toss.im" and p.path.startswith("/shopping-discovery/") or host == "toss.shopping" and p.path.startswith("/i/"):
        try:  # 토스 앱 공유 주소(/shopping-discovery/c/번호 -> /i/번호, 10/9 펩시제로) -> 상품 페이지 canonical·og:url의 /t/번호(쉐어링크 API용)
            m = re.search(r"(?:canonical|og:url)[^>]*?(https://toss\.shopping/t/\d+)", http(url))
        except Exception as e:
            print("toss page", url, repr(e))
            m = None
        return m and m.group(1)
    if host == "toss.shopping" and not p.path.startswith("/_m/"):  # 상품은 /t/번호, 쿼리(k=·referrer)는 남의 쉐어링크 표시
        return urllib.parse.urlunsplit(("https", host, p.path, "", ""))
    if host in TOSS_HOSTS:  # 남의 토스 단축 쉐어링크(/_m/) -> 따라가서 상품 주소(/t/번호)만. 상품 주소로 안 풀리면 None(남의 링크 안 씀, 10/9)
        u = plain(location(url), hops - 1) if hops else None
        return u if u and re.fullmatch(r"https://toss\.shopping/t/\d+", u) else None
    if host in ("link.coupang.com", "coupa.ng") or host in AFF_HOSTS + NAVER_HOSTS + OY_HOSTS:
        return plain(location(url), hops - 1) if hops else None
    if host.endswith("coupang.com"):  # lptag·subid 등 추적값 빼고 상품·옵션만
        keep = {k: v[0] for k, v in qs.items() if k in ("itemId", "vendorItemId")}
        return urllib.parse.urlunsplit(("https", "www.coupang.com", p.path, urllib.parse.urlencode(keep), ""))
    if host.endswith("oliveyoung.co.kr") and "goodsNo" in qs:  # 상품 번호만(추적값·남의 큐레이터 표시 빼고)
        return "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=" + urllib.parse.quote(qs["goodsNo"][0])
    if host.endswith(("smartstore.naver.com", "brand.naver.com")):  # 상품은 경로에 있고 쿼리는 추적값(남의 쇼핑커넥트 등)
        return urllib.parse.urlunsplit(("https", host, p.path, "", ""))
    return url


cp_qs = lambda y, k: (urllib.parse.parse_qs(urllib.parse.urlsplit(str(y.get("productUrl") or "")).query).get(k) or [""])[0]  # 파트너스 링크의 상품 번호(pageKey)·옵션 번호(itemId)
CP_BEST, CP_BEST_RUN = (1012, 1014, 1013, 1010, 1024, 1011, 1029, 1016, 1015, 1001, 1018, 1021), 2  # 카테고리 베스트(사진 채움 10/25): 식품·생활용품·주방·뷰티·건강식품·출산유아·반려·가전·홈인테리어·여성패션·자동차·문구 — 하루 1번씩, 실행마다 2개(시간당 상한 CP_HOUR 안)


def cp_photos(seen, items):
    """검색 말고 다른 API 응답(카테고리 베스트·골드박스)의 productId·productImage를 진우·진열 쿠팡 글(events pid)과 맞춰 사진 채움(10/25 진우 '사이트 제품 사진 교체')
    — 같은 pid만, events item이 있으면 그 옵션(itemId)만, https 사진만, 이미 있으면 그대로. -> 채운 수(own_end가 글 img로)."""
    q, ev = seen.setdefault("cpq", {"m": {}}), ev_info()
    i, by = q.setdefault("i", {}), collections.defaultdict(list)
    for p in load(POSTS, []):
        u = p.get("url")
        if p.get("own") and u in ev and ev[u].get("pid") and not p["text"].startswith("📋") and u not in by[str(ev[u]["pid"])]:
            by[str(ev[u]["pid"])].append(u)
    n = 0
    for z in items or []:
        img = str(z.get("productImage") or "") if isinstance(z, dict) else ""
        for u in by.get(str(z.get("productId")), ()) if img.startswith("https://") else ():
            if u not in i and (not ev[u].get("item") or cp_qs(z, "itemId") == str(ev[u]["item"])):
                i[u], n = img, n + 1
    return n


def cp_best(seen):
    """사진 채움(10/25 Cowork ①): 카테고리 베스트(/products/bestcategories — 검색 아닌 API, limit 100)를 카테고리마다 하루 1번(실행마다 CP_BEST_RUN개) -> cp_photos.
    사진 없는 진우·진열 쿠팡 상품이 없으면 안 부름. 상한 = 다음 실행에, 그 밖 오류 = 그 카테고리 오늘은 건너뜀."""
    if not HAS_CP:
        return
    q, ev, today = seen.get("cpq", {}), ev_info(), time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600))
    if not any(p.get("own") and ev.get(p.get("url"), {}).get("pid") and p["url"] not in q.get("i", {}) and not p["text"].startswith("📋") for p in load(POSTS, [])):
        return
    b = seen.setdefault("cpbest", {})
    if b.get("day") != today:
        b.update(day=today, d={})
    b["t"], got = time.time(), []
    for c in [c for c in CP_BEST if str(c) not in b["d"]][:CP_BEST_RUN]:
        try:
            got.append((c, cp_photos(seen, coupang("GET", f"/products/bestcategories/{c}?limit=100"))))
        except CpLimit:
            break
        except Exception as e:
            print("cp best", c, type(e).__name__)
            got.append((c, 0))
        b["d"][str(c)] = got[-1][1]
    if got:
        print("cp best 사진", " · ".join(f"{c} +{k}" for c, k in got), f"(오늘 {len(b['d'])}/{len(CP_BEST)} 카테고리)")


class CpLimit(RuntimeError):
    """쿠팡 API 호출 상한(이번 실행·최근 1시간) — 안 부르고 다음 실행에."""


def coupang(method, path, body=None):
    """쿠팡 파트너스 Open API(HMAC). 상한(최근 1시간 seen cpuse · 이번 실행)이면 CpLimit(안 부름). 응답 rCode 400(그 주소·상품 실패, HTTP 200으로 옴) = ValueError,
    그 밖 rCode·JSON 아닌 응답 = RuntimeError(다음 실행에 다시)."""
    now, u, n = time.time(), RUN.setdefault("cpu", {}), RUN.setdefault("cpn", [0, 0])
    u["a"], u["s"] = [x for x in u.get("a", []) if x > now - 3600], [x for x in u.get("s", []) if x > now - 3600]
    srch = path.startswith("/products/search")
    if len(u["a"]) >= CP_HOUR or n[0] >= CP_RUN or srch and (len(u["s"]) >= CP_SEARCH_HOUR or n[1] >= CP_SEARCH_RUN):
        raise CpLimit("coupang 시간당 상한")
    u["t"] = now
    u["a"].append(now)
    n[0] += 1
    if srch:
        u["s"].append(now)
        n[1] += 1
    dt = time.strftime("%y%m%dT%H%M%SZ", time.gmtime())
    p, _, q = (CP_BASE + path).partition("?")
    sig = hmac.new(E["COUPANG_SECRET_KEY"].encode(), (dt + method + p + q).encode(), hashlib.sha256).hexdigest()
    auth = f"CEA algorithm=HmacSHA256, access-key={E['COUPANG_ACCESS_KEY']}, signed-date={dt}, signature={sig}"
    try:
        r = json.loads(http(CP_HOST + CP_BASE + path, body, {"Authorization": auth}, method))
    except ValueError as e:  # HTTP 200인데 JSON 아님 = 게이트웨이 문제(상품 탓 X)
        raise RuntimeError(f"coupang 응답 {e!r}")
    if str(r.get("rCode", "0")) != "0":
        raise (ValueError if str(r.get("rCode")) == "400" else RuntimeError)(f"coupang rCode {r.get('rCode')} {r.get('rMessage')}")
    return r["data"]


def cp_deeplinks(urls):
    """쿠팡 주소 여러 개 -> {원래 주소: 파트너스 링크}(딥링크 API 1번 — coupangUrls 배열). 응답 originalUrl로 짝짓고(못 읽으면 같은 개수일 때 순서대로),
    파트너스 도메인 아닌 링크·응답에 없는 주소는 빠짐(대가성 문구가 빠지지 않게). 묶음 전체 오류(rCode 400) = ValueError."""
    r = coupang("POST", "/deeplink", {"coupangUrls": list(urls)})
    ds, out = r if isinstance(r, list) else [], {}
    for k, d in enumerate(ds):
        d = d if isinstance(d, dict) else {}
        o = d.get("originalUrl") if d.get("originalUrl") in urls else urls[k] if len(ds) == len(urls) else None
        if o and urllib.parse.urlsplit(d.get("shortenUrl") or "").netloc in CP_SHORT:
            out[o] = d["shortenUrl"]
    return out


def cp_deeplink(url):
    """쿠팡 주소 1개 -> 파트너스 링크. 안 되는 상품(성인·판매자 요청 등)·파트너스 도메인 아닌 응답 = ValueError(대가성 문구가 빠지지 않게)"""
    s = cp_deeplinks([url]).get(url)
    if not s:
        raise ValueError(f"deeplink {url}")
    return s


def lp_link(merchant, target):
    """링크프라이스 딥링크 (공식 형식 그대로, 가공 없음)."""
    return f"https://click.linkprice.com/click.php?m={merchant}&a={LP_AID}&l=9999&l_cd1=3&l_cd2=0&tu={urllib.parse.quote(target, safe='')}"


def toss(path, body=None):
    """쉐어링크 Open API -> success 본문. 토큰(1년)은 toss.json에 두고 만료 하루 전에만 재발급."""
    t = load(TOSS_TOKEN, {})
    if t.get("exp", 0) < time.time() + 86400:
        form = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": E["TOSS_ACCESS_KEY"],
                                       "client_secret": E["TOSS_SECRET_KEY"], "scope": "sharelink:read sharelink:write"}).encode()
        r = json.loads(http("https://oauth2.cert.toss.im/token", form, {"Content-Type": "application/x-www-form-urlencoded"}, "POST"))
        t = {"token": r["access_token"], "exp": time.time() + r["expires_in"]}
        json.dump(t, open(TOSS_TOKEN, "w"))
    r = json.loads(http(TOSS_API + path, body, {"Authorization": "Bearer " + t["token"]}))
    if r.get("resultType") != "SUCCESS":  # HTTP 200이어도 FAIL일 수 있음(IP 미등록·발급 제한 상품 등)
        raise RuntimeError(r.get("error"))
    return r["success"]


def toss_link(seen, iid, name=""):
    """tacaItemId -> 우리 쉐어링크. 만든 링크는 seen['tlink'](id -> [링크, 만든 시각])에 보관. 재사용 모드(토스 점검 — RUN['treuse'])면 새로 안 만들고
    보관 링크를 꺼냄(없으면 None = 그 상품만 빠짐) — 꺼낸 것·없던 것은 점검 하루 요약에."""
    st = seen.setdefault("tlink", {"m": {}})
    st["t"] = time.time()
    if RUN.get("treuse"):
        link = (st["m"].get(str(iid)) or [None])[0]
        tnote(seen, "ok" if link else "miss", name or str(iid))
        return link
    link = toss("/links", {"tacaItemId": iid, "publisherId": E["TOSS_PUBLISHER_ID"]})["shortUrl"]
    st["m"][str(iid)] = [link, time.time()]
    st.setdefault("r", {})[link] = [int(iid), time.time()]  # 링크 -> 상품 id(metrics 잘 된 상품 표 — 옛 링크도)
    return link


def toss_ok(seen, iid):
    """토스 후보 거르기: 재사용 모드면 보관 링크 있는 상품만(Claude가 링크 없는 걸 골라 글이 비지 않게), 보통 땐 전부. 진우 링크(ev:)는 늘 OK."""
    return not RUN.get("treuse") or str(iid).startswith("ev:") or str(iid) in seen.get("tlink", {}).get("m", {})


def tnote(seen, kind, text):
    """토스 점검 하루 요약(toss_mode가 날 바뀌면 보냄)에 1줄: ok = 보관 링크로 씀, miss = 링크 없어 못 올림, err = 토스 단계 오류(바로 알림 대신)."""
    if isinstance(seen.get("tpause"), dict):
        seen["tpause"].setdefault(kind, []).append(clip(text, 30))


def toss_mode(seen, now=None):
    """main 맨 앞 1번: 이번 실행이 토스 재사용 모드인지(RUN['treuse']) + 점검 알림(10/22 Cowork '알림 폭탄 X — 하루 1번 요약'). 보관 링크는 TOSS_LINK_KEEP 지나면 정리.
    점검 기간(TOSS_PAUSE) = 재사용(첫 실행에 '시작' 1번) · 날 바뀌면 어제 요약 1번(보관 링크로 올림·링크 없어 빠짐·토스 단계 오류 — 바로 안 알리고 여기로) ·
    끝난 뒤 = 링크 1개 만들어 봄(1시간에 1번): 되면 보통 모드 + '끝' 알림 1번, 안 되면 재사용 그대로 + '아직' 알림 1번."""
    now = now or time.time()
    k = time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 9 * 3600))
    tp = seen.get("tpause") if isinstance(seen.get("tpause"), dict) else None
    RUN["treuse"] = HAS_TOSS and (TOSS_PAUSE[0] <= k <= TOSS_PAUSE[1] or k > TOSS_PAUSE[1] and bool(tp) and not tp.get("back"))  # 먼저 정함(아래 알림·확인이 실패해도 이번 실행은 이 모드)
    if not HAS_TOSS:
        return
    st = seen.setdefault("tlink", {"t": now, "m": {}})
    st["m"] = {i: v for i, v in st["m"].items() if v[1] > now - TOSS_LINK_KEEP}
    st["r"] = {u: v for u, v in st.get("r", {}).items() if v[1] > now - TOSS_LINK_KEEP}
    def say(t):  # 알림이 실패해도(텔레그램 시간 초과 — tg는 HTTPError만 잡음) 기록·모드는 그대로
        try:
            tg("sendMessage", chat_id=ADMIN, text=t)
        except Exception as e:
            print("toss mode say", repr(e))
    brief = lambda x: f"보관 링크 꺼내 씀 {len(x.get('ok', []))}번 · 링크 없어 못 올림 {len(x.get('miss', []))}개" + (f"({', '.join(x['miss'][:5])}{' 등' if len(x['miss']) > 5 else ''})" if x.get("miss") else "") \
        + (f" · 토스 단계 오류 {len(x['err'])}번({', '.join(list(dict.fromkeys(x['err']))[:3])})" if x.get("err") else "")
    md = lambda d: f"{int(d[5:7])}/{int(d[8:10])}"  # '2026-10-30 ..' -> '10/30'
    left = lambda: f"보관 링크 {len(st['m'])}개(3일 안 올린 것 빼면 {sum(f'tb_{i}' not in seen for i in st['m'])}개)"
    if not RUN["treuse"]:
        return
    if not tp:
        seen["tpause"] = tp = {"d": k[:10], "t": now}  # t 먼저(seen 정리가 t를 봄)
        say(f"🔧 토스 쉐어링크 점검 모드 시작({md(TOSS_PAUSE[0])}~{md(TOSS_PAUSE[1])}) — 새 링크 안 만들고 {left()}를 재사용해 토스 글(채널·Threads) 계속 올려요(수익 0 기간). "
            "링크 없어 빠진 상품·토스 단계 오류는 바로 안 알리고 하루 1번(날 바뀌면) 요약")
    tp["t"] = now
    if tp["d"] != k[:10]:  # 어제 요약
        old = dict(tp)
        tp.update(d=k[:10], ok=[], miss=[], err=[])
        say(f"🔧 토스 점검 모드 {md(old['d'])} 요약 — {brief(old)} · 남은 {left()}")
    if k <= TOSS_PAUSE[1] or now - tp.get("probe", 0) < 3600:
        return
    tp["probe"] = now
    try:  # 점검 끝난 뒤 = 지금 베스트 중 품절 아닌 상품으로 만들어 봄(보관 상품은 그사이 발급 제한·판매 끝일 수 있어서 — 10/22 리뷰), 그 상품만 막혔을 수 있어 3개까지
        RUN["treuse"], err = False, None
        for x in [x for x in toss("/products/best-selling?size=10")["items"] if not x.get("isSoldOut")][:3]:
            try:
                toss_link(seen, x["tacaItemId"])
                break
            except RuntimeError as e:
                err = e
        else:
            raise err or RuntimeError("베스트 목록 비어 있음")
    except Exception as e:
        RUN["treuse"] = True
        print("toss probe", repr(e))
        if not tp.get("warn"):
            tp["warn"] = 1
            say(f"⚠️ 토스 쉐어링크 점검 기간({md(TOSS_PAUSE[1])}까지)이 끝났는데 링크 새로 만들기가 아직 안 돼요({err_brief(e)}) — 재사용 모드 그대로, 1시간마다 다시 확인해서 되면 알려요")
        return
    tp["back"] = 1
    say("✅ 토스 쉐어링크 점검 끝 — 링크 새로 만들기 확인, 보통 모드로 돌아왔어요(새 링크로 올림 · 링크 실패 알림도 다시 바로). 11/5부터 수수료 토스 5%·선착순특가 3%"
        + (f" (오늘 재사용 모드 동안: {brief(tp)})" if any(tp.get(x) for x in ("ok", "miss", "err")) else ""))


def toss_stock(seen):
    """점검 대비 미리 만들기(10/22 Cowork ③ — TOSS_STOCK_DAYS): TOSS_STOCK_GAP마다 베스트 100·생필품(TOSS_CATS)·뷰티 베스트 30·하루특가 30 중 품절 아닌 상품 id를 줄(q)에 받아
    한 실행 TOSS_STOCK_RUN개씩 쉐어링크를 만들어 보관(tlink — 남은 줄은 다음 실행에, 목록은 회차에 1번만 조회). 다 올리진 않음 — 점검 기간 회차·개별 글이 이 중에서 지금처럼 Claude로 고름.
    발급 제한 상품(FAIL)은 그 상품만 빼고(tstockbad) 계속, 3번 연달아 막히거나 네트워크 오류면 이번 실행은 거기서 멈춤."""
    now = time.time()
    if not HAS_TOSS or RUN.get("treuse") or time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600)) not in TOSS_STOCK_DAYS:
        return
    st, have = seen.get("tstock", {}), seen.setdefault("tlink", {"t": now, "m": {}})["m"]
    bad = set(seen.get("tstockbad", {}).get("ids", []))
    if now - st.get("t", 0) >= TOSS_STOCK_GAP:  # 새 회차
        tree = toss("/categories")["categories"]  # 트리 조회는 일 상한 차감 없음
        raw = toss("/products/best-selling?size=100")["items"] + toss("/products/today-deals?size=30")["items"] + [
            x for c in tree if c["displayName"] in TOSS_CATS or re.search("뷰티|화장품", c["displayName"]) for x in toss(f"/products/best-categories/{c['categoryId']}?size=30")["items"]]
        st = seen["tstock"] = {"t": now, "q": list(dict.fromkeys(x["tacaItemId"] for x in raw if not x.get("isSoldOut")))}
    q = [i for i in st.get("q", []) if str(i) not in have and i not in bad]
    n = fails = 0
    for i in q[:TOSS_STOCK_RUN]:
        try:
            toss_link(seen, i)
        except RuntimeError as e:  # 발급 제한 상품 등(FAIL) = 그 상품만 빼고 계속
            print("toss stock", i, repr(e))
            bad.add(i)
            fails += 1
            if fails >= 3:
                break
            continue
        except Exception as e:  # 네트워크 -> 다음 실행에 이어서
            print("toss stock", repr(e))
            break
        n, fails = n + 1, 0
    if bad:
        seen["tstockbad"] = {"t": now, "ids": sorted(bad)}
    st["q"] = [i for i in q if str(i) not in have and i not in bad]
    print(f"toss stock: 새 링크 {n} · 남은 줄 {len(st['q'])} · 보관 {len(have)}개" + (f" · 발급 제한 {len(bad)}" if bad else ""))


def lp_api(url):
    """링크프라이스 딥링크 API 1번 -> (링크 — result S(승인 몰)일 때만, 아니면 None · 응답 result(+ 메시지)). 접속 오류 = 예외 그대로."""
    r = json.loads(http(LP_API.format(LP_AID, urllib.parse.quote(url, safe=""))))
    why = " ".join(str(r.get(k)) for k in ("result", "msg", "message") if r.get(k))
    return (r["url"] if r.get("result") == "S" and r.get("url") else None), re.sub(r"\s*https?://\S+", "", why)[:80] or "?"


def affiliate(url):
    """쇼핑몰 주소 -> (버튼 링크, 제휴여부). 쿠팡: API 키 있으면 파트너스 링크. 토스: 쉐어링크 API(상품 주소의 tacaId).
    그 외: 링크프라이스 딥링크 API (승인된 몰이면 상품 페이지 딥링크 — 새로 승인된 몰도 코드 수정 없이 바로 적용). API 장애 땐 LP_HOSTS로 직접."""
    host = urllib.parse.urlsplit(url or "").netloc.lower()
    taca = HAS_TOSS and re.match(r"https://toss\.shopping/t/(\d+)", url or "")
    if taca:  # 실패(발급 제한 상품 등)하면 상품 주소 그대로 -> 관리자 사본으로 수동
        if RUN.get("treuse"):  # 토스 점검 = 새 링크 X(토스 딜 이름 대조가 보관 링크로 — toss_match)
            return url, False
        try:
            return toss("/links", {"tacaId": int(taca.group(1)), "publisherId": E["TOSS_PUBLISHER_ID"]})["shortUrl"], True
        except Exception as e:
            print("toss link", repr(e))
            return url, False
    if HAS_CP and host.endswith("coupang.com"):  # 커뮤니티 딜만 옴(진우 단축 링크는 events·관리자 글로 그대로) — 남의 파트너스 링크도 우리 것으로
        try:
            return cp_deeplink(url), True
        except Exception as e:
            print("deeplink", repr(e))
    if not url:
        return url, False
    try:
        link = lp_api(url)[0]
        return (link, True) if link else (url, False)
    except Exception as e:
        print("lp api", repr(e))
    m = next((v for k, v in LP_HOSTS.items() if host == k or host.endswith("." + k)), None)
    return (lp_link(m, url), True) if m else (url, False)


def store_info(title, url=""):
    """제목의 [쇼핑몰](없으면 상품 주소의 도메인)로 수익 안내 문구. 제휴 없는 몰은 수수료 0 표시."""
    host = urllib.parse.urlsplit(url or "").netloc.lower()
    tag = store_tag(title) + " " + next((v for k, v in HOST_STORES.items() if k in host), "")
    return next((v for k, v in STORES.items() if k in tag), "💸 제휴 없는 쇼핑몰 · 수수료 0")


def draft(text, buy_url=None, score=None, info=None, label="🛒 구매하러 가기"):
    """관리자에게 검수용 초안 전송. ✅ 누르면 다음 실행 때 채널에 그대로 복사됨.
    info: 관리자만 보는 안내 버튼(채널엔 링크 버튼만 복사되므로 안 나감)."""
    kb = [[{"text": label, "url": buy_url}]] if buy_url else []
    kb.append([{"text": f"✅ 게시 ({score}점)" if score else "✅ 게시", "callback_data": "ok"},
               {"text": "❌ 패스", "callback_data": "no"}])
    if info:
        kb.append([{"text": info, "callback_data": "-"}])
    return tg("sendMessage", chat_id=ADMIN, text=text, parse_mode="HTML",
              link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": kb})


def comment_of(text):
    """채널 글(posts.json text) -> 제목 아래 코멘트 (🏆 인기 배지 줄·출처 줄 제외)."""
    return re.sub(r"^🏆 인기 · .*\n*", "", split_title(text)[1].rsplit("\n\n출처:", 1)[0].strip())


def store_tag(title):
    """뽐뿌 제목 맨 앞 [쇼핑몰] -> 비교용 소문자·공백 제거 ('[G마켓]메디폴미' -> 'g마켓')."""
    tag = re.match(r"\s*\[([^\]]+)\]", title)
    return tag.group(1).lower().replace(" ", "") if tag else ""


PRICE_TAIL = r"\s*\([^()]*(원|무료|무배|배송)[^()]*\)\s*$"  # 뽐뿌 제목 끝 (가격/배송)


def is_oy(title):
    """[올리브영]·[올영] 딜(올리브영 쇼핑 큐레이터 링크 대상)."""
    return store_tag(title) in ("올리브영", "올영")


EARN_TAGS = ("올리브영", "올영", "g마켓", "지마켓", "롯데온", "롯데on", "토스", "쿠팡")  # 수수료 되는 몰: 링크프라이스 검색 링크·토스 자동 링크·쿠팡 파트너스(사본)·올영 큐레이터


FOCUS_TAGS, OTHER_MIN, OTHER_MAX = ("토스", "쿠팡", "네이버", "스마트스토어"), 8, 3  # 10/14 23:55 진우 '토스·쿠팡·네이버 위주': 그 밖의 몰 커뮤니티 딜은 8점↑·KST 하루 3개까지(되돌리기 = 0, 99)


def focus(title):
    """제목 [쇼핑몰]이 3사(토스·쿠팡·네이버·스마트스토어)인지 — 3사 딜은 예전 규칙 그대로."""
    return any(k in store_tag(title) for k in FOCUS_TAGS)


def earns(title):
    """제목 [쇼핑몰]이 수수료 되는 몰이거나 화장품이면 True -> 점수 컷 1점 낮춤·같은 점수면 먼저(10/10 진우 '수수료 되는 딜 꼭 챙겨').
    화장품(10/11 진우 '화장품도 발굴'): 어느 몰 딜이든 올리브영 큐레이터 링크로 수익 연결 -> 같이 완화(효능 문구 금지 규칙은 그대로)."""
    return any(k in store_tag(title) for k in EARN_TAGS) or bool(re.search(BEAUTY, title))


def keyword(title):
    """Claude 검색어가 없을 때: 제목에서 [쇼핑몰]·끝의 (가격/배송) 떼고 40자."""
    t = re.sub(r"^\s*\[[^\]]*\]\s*", "", title)
    return re.sub(PRICE_TAIL, "", t).strip()[:40]


def clip(s, n):
    """n자 넘으면 띄어쓰기 단위로 자르고 … (가격·단어 중간에서 안 끊김)."""
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0].rstrip(" +,(") + "…"


def lp_search(title, q=None):
    """링크프라이스 승인 몰이면 그 몰 검색 결과로 가는 제휴 링크 -> (링크, 몰 이름), 아니면 (None, None)."""
    hit = next((v for k, v in LP_SEARCH.items() if k in store_tag(title)), None)
    if not hit:
        return None, None
    m, name, base = hit
    return lp_link(m, base + urllib.parse.quote(q or keyword(title))), name


def facts_of(x, toss=False):
    """코멘트 아래 줄: 💡 단위가격 → (토스 쉐어링크 글이면 🙋 누가·👍 언제, 10/20 진우 '사고 싶게') → ⚠️ 확인할 점."""
    return "".join(f"\n{esc(l)}" for l in ([f"💡 단위가격 {x['unit']}"] if x.get("unit") else []) + (wu(x) if toss else []) + ([f"⚠️ 확인할 점 {x['warn']}"] if x.get("warn") else []))


def deal_post(d, comment, q=None, extra=None):
    """-> (본문, 버튼 링크, 버튼 이름). 상품 주소가 있으면 쿠팡 API·링크프라이스 상품 딥링크 > 링크프라이스 검색 링크
    > 상품 페이지(제휴 없음, 관리자 사본으로 수동) > 그 몰 검색 결과(MALL_SEARCH, 10/10~) > 원글. 제휴 링크면 대가성 문구를 맨 앞에.
    extra의 unit(단위가격)·warn(확인할 점)이 있으면 코멘트 아래 한 줄씩 (다른 핫딜 채널과의 차이: 비교 근거 + 단점까지)."""
    link, aff = (d["toss"], True) if d.get("toss") else affiliate(store_link(d["url"]))  # toss = toss_wait가 찾은(또는 진우가 보낸) 쉐어링크
    label = buy_btn(d["title"], link or d["url"])  # 토스·쿠팡 = '💙 토스에서 N원'·'🚀 쿠팡에서 N원'(10/22), 그 밖 = '🛒 N원 구매하기'
    if not aff:
        lp, name = lp_search(d["title"], q)
        if not lp and not link:  # 상품 주소도 제휴 검색도 없으면 원글 대신 그 몰 검색 결과(원글은 본문 '출처' 링크로 남음). 토스·모르는 몰·앱 쿠폰은 원글 그대로
            name, base = next((v for k, v in MALL_SEARCH.items() if k in store_tag(d["title"])), (None, None))
            lp = base and base + urllib.parse.quote(q or keyword(d["title"]))
        if lp:
            link, label = lp, f"🔎 {name}에서 찾기"
    note = aff_note(link or "")
    x = extra or {}
    facts = facts_of(x, note == TOSS_NOTE)
    head = ad_head(note, f"🔥 {d['title']}\n\n{comment}", x.get("unit") or "")  # 공정위 지침: 대가성 문구는 첫 부분에 — 1줄 [광고] 첫 줄 + 2줄 고지문(10/11 진우 결정)
    badge = f"\n🏆 <b>인기</b> · {esc(d['hot'])}" if d.get("hot") else ""  # 제목 바로 아래(제목 줄은 사이트 split_title이 첫 줄로 읽음)
    text = f"{head}🔥 <b>{esc(d['title'])}</b>{badge}\n\n{esc(comment)}{facts}\n\n출처: <a href=\"{esc(d['url'])}\">{d['board']}</a>"
    if TOSS_NO_CMP and is_toss(link or d["url"], f"[{store_tag(d['title'])}]"):  # 토스 딜: 다른 몰 비교 빼고 게시 시점 가격(10/12 토스 비즈니스 요청)
        text = strip_cmp(text)[0].replace("\n\n출처: ", f"\n{toss_when()}\n\n출처: ", 1)
    pre = head if text.startswith(head) else ""  # (토스 [광고] 첫 줄은 strip_cmp가 훅을 뺄 수 있음 -> 그땐 글 전체를 봄 = 몰별 틀 X)
    text = pre + mall_view(text[len(pre):], link or d["url"])  # 토스·쿠팡 = 몰별 틀(10/22 진우 '한눈에')
    return text, link or d["url"], label if label.startswith("🔎") else buy_btn(d["title"], link or d["url"], plain_of(text))  # 쿠팡 버튼 🚀/📦 = 머리 줄과 같게


TOSS_TAG = r"\[토스(?:쇼핑)?\]"  # 토스 딜 제목 [몰] — 10/18 진우 '[토스쇼핑]도 토스'(같은 토스쇼핑: 비교 X·게시 시점 가격·뽐뿌 말고 바로 연결)


def is_toss(url, text=""):
    """토스 딜인지: 쉐어링크(toss.shopping·toss.im) 또는 제목이 [토스]·[토스쇼핑](몰별 틀 = '💙 토스 특가' 머리 줄)."""
    return bool(toss_share(url or "") or re.search(r"(^|\n)(?:(?:\[광고\][^\n]*\n)?[^\n]*" + TOSS_TAG + "|💙 토스 특가|💙 토스 · )", text[:400]))


STEADY_BUY, STEADY_REV = r"한\s*달(?:\s*동안|간)?\s*([\d,]*\d(?:\.\d+)?(?:\s*[천만])?)\s*명\s*\+?\s*(?:이상\s*)?(?:구매|샀)", r"리뷰\s*([\d,]*\d(?:\.\d+)?(?:\s*[천만])?)(?![\d,.]*\s*[천만]?\s*(?:원|%))(?:\s*개)?"  # 👍 꾸준템 가격 줄 숫자('한 달 1,000명+ 구매'·'한 달 1만명+'·'리뷰 1,969(개)'·'리뷰 1.6만' — 쿠팡은 만 단위가 많음, 10/22 리뷰 '리뷰 1.6만'이 '리뷰 1'로) · 만원·% 숫자 X
steady_n = lambda x: round(float(re.sub(r"[,\s천만]", "", x)) * (10000 if "만" in x else 1000 if "천" in x else 1))  # '1.6만' -> 16000
CP_ROCKET = r"(?<!비)로켓(?!\s*(?:배송)?\s*[은는이가도]?\s*(?:아님|아니|아닌|안\s*[돼됨되]|불가|미적용|X|x|없)|\s*와우)|새벽\s*도착"  # 쿠팡 로켓 근거 = 글에 로켓·새벽 도착('로켓배송 아님·이 아닌·미적용'·'비로켓'·'로켓와우'(멤버십) X — 10/22·10/23 리뷰)
CP_OLD = r"^🚀 쿠팡(?= · [^\n]* [🔥🛒👍]$| [🔥🛒👍]$)"  # 10/23 전 로켓 근거 없는 쿠팡 머리 줄('🚀 쿠팡 · … 🔥') — 새로 내보낼 땐 📦(예약·Threads), 이미 올라간 글은 그대로
CP_PLAIN = ("📦 쿠팡", "📦 쿠팡에서")  # 10/23 진우: 로켓 근거 없는 쿠팡 글 = 📦(🚀는 로켓으로 오해) — 머리 줄·구매 버튼(Threads·인스타 배지도). 로켓 = '🚀 쿠팡 로켓' 그대로
TOSS_STEADY_HEAD = "💙 토스"  # 10/24 17:5x 진우: 토스 꾸준템(👍 = 특가 아님) 머리 줄 = '💙 토스 · 꾸준히 팔리는 상품 👍'(특가 글은 '💙 토스 특가 · …' 그대로) — 채널·Threads·사이트·인스타 카드 같은 규칙
MALLS = {"toss": ("💙 토스 특가", "💙 토스에서"), "coupang": ("🚀 쿠팡 로켓", "🚀 쿠팡에서")}  # 10/22 진우 '토스 글과 쿠팡 글을 한눈에'(색·내용 둘 다): 개별 글 머리 줄 · 구매 버튼


def mall_of(url, title=""):
    """토스·쿠팡 개별 딜인지 -> 'toss'·'coupang'·None(그 밖의 몰 = 예전 틀). 토스 = 쉐어링크·[토스]·[토스쇼핑], 쿠팡 = 제목 [쿠팡…]·쿠팡 주소."""
    tag, host = store_tag(title), urllib.parse.urlsplit(url or "").netloc.lower()
    if is_toss(url, f"[{tag}]"):
        return "toss"
    return "coupang" if "쿠팡" in tag or host in ("link.coupang.com", "coupa.ng", "coupang.com") or host.endswith(".coupang.com") else None


def cp_rocket(plain):
    """쿠팡 글이 로켓인지: 몰별 머리 줄이 있으면 그 줄('🚀 쿠팡 로켓'만 로켓 — 📦 쿠팡·10/23 전 '🚀 쿠팡' = 아님, 버튼·배지가 머리 줄과 같게), 없으면 글에 로켓 근거(CP_ROCKET)."""
    m = next((m for m in map(MALL_HEAD.fullmatch, (plain or "").split("\n")) if m and "쿠팡" in m[1]), None)
    return m[1] == MALLS["coupang"][0] if m else bool(re.search(CP_ROCKET, plain or ""))


def mall_btn(mall, price, rocket=True):
    """몰별 구매 버튼: '💙 토스에서 15,580원' · '🚀 쿠팡에서 8,860원'(로켓 근거 없는 쿠팡 = '📦 쿠팡에서 …', 가격 모르면 '… 보기')."""
    won = re.search(r"\d[\d,]*\s*원", price or "")
    return f"{MALLS[mall][1] if rocket or mall != 'coupang' else CP_PLAIN[1]} {won[0].replace(' ', '') if won else '보기'}"


def buy_btn(title, url, plain=None):
    """채널 개별 딜 버튼: 토스·쿠팡 = mall_btn(쿠팡 🚀/📦 = 글 plain의 cp_rocket — 글을 모르면 🚀), 그 밖의 몰 = 예전 buy_label('🛒 N원 구매하기')."""
    mall = mall_of(url, title)
    return mall_btn(mall, parse(title)[2], plain is None or bool(re.search(CP_OLD, plain, re.M)) or cp_rocket(plain)) if mall else buy_label(title)  # 10/23 전 글('🚀 쿠팡' 머리 줄)의 링크 교체 = 버튼도 🚀(머리 줄과 같게)


def mall_head(mall, src, icon, rocket=True):
    """몰별 머리 줄: '💙 토스 특가 · {출처} 🔥' / '🚀 쿠팡 로켓 · {각도} 🛒'(출처·각도 모르면 칸 없이). 로켓 근거 없는 쿠팡 = '📦 쿠팡 · …'(10/22 진우 '사실 아닌 표기 X' · 10/23 🚀 -> 📦)."""
    return f"{TOSS_STEADY_HEAD if mall == 'toss' and icon == '👍' else MALLS[mall][0] if rocket or mall != 'coupang' else CP_PLAIN[0]}{f' · {src}' if src else ''} {icon}"  # 토스 👍 꾸준템 = '특가' X(10/24 진우)


def mall_body(mall, src, icon, name, price, lines, rocket=True):
    """몰별 개별 글 본문(HTML, 대가성 문구 아래): 머리 줄 → 상품명(굵게) → 가격 줄 → 줄들(HTML).
    저장된 글은 split_title이 '[몰] 상품명 (가격)'으로 읽음(사이트·리스트·Threads 그대로)."""
    return f"{esc(mall_head(mall, src, icon, rocket))}\n<b>{esc(name)}</b>\n{esc(price)}" + "".join(f"\n{l}" for l in lines if l)


def mall_dr(plain):
    """글의 할인율 -> (조건, %): 정가 기준·참고·비교 말이 든 줄의 %는 X(10/22 리뷰 '88% 할인율보다 쿠팡 …'),
    % 바로 앞 와우·쿠폰·멤버십·회원·카드 조건은 같이(10/22 Cowork: '와우 쿠폰 44% 할인'이 머리 줄에 '44% 할인'만 — 누구나 받는 할인처럼)."""
    return next(((m[1].strip(), m[2]) for l in plain.split("\n") if not re.search(rf"정가 기준|참고|{CMP_WORDS}", l)
                 for m in [re.search(r"((?:(?:와우|쿠폰|멤버십|회원|카드)\S*(?:\s+(?:적용|할인|가|즉시))?\s*)*)(\d{1,2})\s*%\s*(?:할인|↓)", l)] if m), ("", ""))


def mall_src(mall, plain, title=""):
    """글만 아는 딜(커뮤니티·진우 링크·예전 틀 예약)의 머리 줄 '· …' 칸 — 글에 근거가 있을 때만, 없으면 ''.
    토스 = 순위 > 하루특가 > 30일 최저가 > 할인 · 쿠팡 = 같은 상품 최저 > 1개당 최저 > 와우 할인 > 30일 최저가 > 순위 > 할인('정가 기준' 할인은 X)."""
    k = time.gmtime(time.time() + 9 * 3600)
    fresh = "\n".join(l for l in plain.split("\n") if not set(re.findall(r"(?<![\d/])\d{1,2}/\d{1,2}(?![\d/])|어제|그제", re.sub(r"\(\d{1,2}/\d{1,2} \d{1,2}(?::\d{2})?시?(?: 가격)?\)", "", l))) - {f"{k.tm_mon}/{k.tm_mday}"})  # 지난 날 순위('10/12 밤 … 1위')는 지금 순위처럼 X(10/22 리뷰)
    rank = re.search(r"(많이 팔린 순위 \d{1,2}위|[가-힣/·]{1,12} ?(?:베스트|구매|판매) ?\d{1,2}위)" if mall == "coupang" else r"(많이 팔린 순위 \d{1,2}위|[가-힣/·]{1,12} 베스트 \d{1,2}위)", fresh)
    rank = rank if rank and not re.search(f"{OTHER_STORES}|{WU_CMP}", rank[1]) else None  # 토스 머리 줄에 다른 몰 순위(예 '쿠팡 판매 1위') X — 토스 글은 토스 순위 말만
    low = re.search(r"30일 (?:내 )?최저가(?!는 아니|가 아니| 아님)", plain)
    cond, dr = mall_dr(plain)
    dr = dr and f"{cond} {dr}% 할인".strip()  # 조건째('와우 쿠폰 44% 할인')
    if mall == "toss":
        return rank[1] if rank else "하루특가" if "하루특가" in plain else "30일 최저가" if low else dr
    if saving(plain) or re.search(r"같은 상품[^\n—]*?(?:최저|가장 싸|제일 싸|젤 싸)", plain):
        return "같은 상품 최저"
    if re.search(r"1개당 (?:최저|가장 싸|제일 싸|젤 싸)", plain):
        return "1개당 최저"
    if "와우" in store_tag(title) or re.search(r"와우\s*(?:회원|할인|전용|가)", plain):
        return "와우 할인"
    return "30일 최저가" if low else rank[1] if rank else dr


def mall_view(body, url):
    """예전 틀 개별 글 본문(HTML, 첫 줄 '🔥|🛒 <b>[몰] 제목 (가격)</b>')이 토스·쿠팡이면 몰별 틀로(커뮤니티 딜·진우 링크·예전 틀로 쓴 예약 글):
    제목 -> 머리 줄(mall_src, 🛒 약한 딜은 칸 없이) + 상품명 + 가격 줄(토스 = 가격 (할인%↓) · ⭐ 평점 (리뷰), 쿠팡 = 가격 → 단위가격 — '💡 단위가격' 줄을 옮김),
    제목 아래 빈 줄은 뺌, 쿠팡에 '결제 전' 줄이 없으면 '⚠️ 결제 전 최종가 (M/D H시)'. 토스·쿠팡 아님·가격 모름·이미 몰별 틀 = 그대로."""
    body = re.sub(CP_OLD, CP_PLAIN[0], body, flags=re.M)  # 이미 몰별 틀로 쓴 글(예약)의 로켓 근거 없는 '🚀 쿠팡' 머리 줄 = 📦(10/23 진우)
    m = re.match(r"([🔥🛒👍]) <b>(.+?)</b>", body)
    title = html.unescape(m[2]) if m else ""
    mall = m and mall_of(url, title)
    mall = None if m and m[1] == "👍" and mall == "toss" else mall  # 👍 꾸준템 = 쿠팡만(토스 글은 지금 그대로)
    _, name, price = parse(title)
    if not price and (p := re.search(r"\s*\((\d{1,3}(?:,\d{3})+|\d{4,})\s*(?:[/,]\s*([^()]*))?\)\s*$", title)):  # 뽐뿌 '(89,890/무료)'처럼 '원' 없는 가격(10/22 13:26 기가바이트 글이 예전 틀로)
        _, name, price = parse(f"{title[:p.start()]} ({p[1]}원{'/' + p[2] if p[2] else ''})")
    if not mall or not price:
        return body
    plain, rest = plain_of(body), body[m.end():]
    main, _, ship = price.partition("/")
    line, _, extra = main.partition(" · ")  # '33,900원 · 5천원 쿠폰가' -> 할인·평점·단위가격은 금액 바로 뒤
    line = line.strip()
    if mall == "toss":
        (cond, dr), star = mall_dr(plain), re.search(r"⭐\s*([\d.]+)\s*\(리뷰\s*([\d,]+)\)", plain)
        line += (f" ({dr}%↓)" if dr and not cond else "") + (f" · ⭐ {star[1]} ({star[2]})" if star else "")  # 조건 붙은 %는 가격 줄에 X(누구나 받는 할인처럼 보임)
    elif u := re.search(r"\n💡 (?:단위가격:?[^\S\n]*)?((?:[\d.]*[가-힣A-Za-z]+당|1[가-힣]+)[^\S\n]*(?:약[^\S\n]*)?[\d,]+원꼴?(?:[^\S\n]?\([^)\n]*\))?)([^\n]*)", rest):  # 💡 줄 맨 앞 단위가격('1개당 373원'·'100ml당 24원'·'단위가격 개당 534원')만 가격 줄로, 나머지 조각은 💡 줄에 남김
        more = re.sub(r"^\s*(?:·|—)\s*", "", u[2]).strip()  # (HTML에서 꺼낸 글자 -> mall_body가 다시 이스케이프)
        rest, line = rest[:u.start()] + (f"\n💡 {more}" if more else "") + rest[u.end():], f"{line} → {re.sub(r'^1?개당 ', '1개 ', html.unescape(u[1]))}"
    if m[1] == "👍":  # 10/22 진우 👍 꾸준템: 가격 줄 = 가격 · 한 달 N명+ 구매 · 리뷰 N(글에 있는 숫자만), 그 숫자만 있던 줄은 뺌(두 번 X)
        st = [f"한 달 {re.sub(r'\s', '', n[1])}명+ 구매" for n in [re.search(STEADY_BUY, plain)] if n] + [f"리뷰 {re.sub(r'\s', '', n[1])}" for n in [re.search(STEADY_REV, plain)] if n]
        line += "".join(f" · {x}" for x in st)
        rest = "\n".join(l for l in rest.split("\n") if not (st and re.search(f"{STEADY_BUY}|{STEADY_REV}", plain_of(l)) and re.fullmatch(r"[\W_]*", re.sub(f"{STEADY_BUY}|{STEADY_REV}", "", plain_of(l)))))
    line += "".join(f" · {x.strip()}" for x in (extra, ship) if x.strip())
    rest = re.sub(r"^((?:\n🏆[^\n]*)?)\n\n", r"\1\n", rest, count=1)  # 제목 아래 빈 줄(🏆 인기 줄은 가격 줄 아래로)
    if mall == "coupang" and "결제 전" not in plain:
        k = time.gmtime(time.time() + 9 * 3600)
        i = rest.find("\n\n출처: ")
        i = len(rest) if i < 0 else i
        rest = rest[:i] + f"\n⚠️ 결제 전 최종가 ({k.tm_mon}/{k.tm_mday} {k.tm_hour}시)" + rest[i:]
    return mall_body(mall, "" if m[1] == "🛒" else "꾸준히 팔리는 상품" if m[1] == "👍" else mall_src(mall, plain, title), m[1], name, line, [], bool(re.search(CP_ROCKET, plain))) + rest  # 쿠팡 '로켓' = 글에 로켓·새벽 도착 근거 있을 때만('로켓배송 아님' X — 10/22 리뷰)


def toss_when(t=None):
    """'⚠️ 10/12 21:30 게시 시점 가격'(토스 비즈니스 요청 — 게시 시점 기준 가격 표시). t = 'YYYY-MM-DD HH:MM'(KST), 없으면 지금."""
    t = t or time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600))
    return f"⚠️ {int(t[5:7])}/{int(t[8:10])} {t[11:16]} 게시 시점 가격"


def toss_list(ps):
    """토스 딜이 든 리스트인지 — 그런 리스트는 다른 몰 이름 X·게시 시점 줄(10/14 22:30 TOP 리스트와 같은 규칙)."""
    return TOSS_NO_CMP and any(is_toss(p.get("url"), p["text"]) for p in ps)


def list_name(p, toss_in, ship=False):
    """리스트 줄 제목: 토스 딜이 든 리스트면 [몰] 태그 없이 '상품명 (가격)'(10/21 22:30 점검: 21시 모아보기·카드·블로그에 [토스]와 [네이버]·[쿠팡]이 같이 나가던 것).
    ship = 가격 뒤 배송 조각('/무배')도 그대로(카드 이미지의 배송 칸)."""
    t = title_of(p["text"])
    if not toss_in:
        return t
    _, name, price = parse(t)
    return f"{name} ({price if ship else price.split('/')[0].strip()})" if price else name


def toss_body(body, url):
    """진우가 봇에 보낸 토스 링크 글(admin_deal·초안) 본문 HTML = deal_post와 같게 다른 몰 비교 빼고 끝에 게시 시점 가격 줄(10/22 리뷰 — 채널 글엔 없던 것)."""
    return add_when(strip_cmp(body)[0], [])[0] if TOSS_NO_CMP and is_toss(url) else body


def add_when(text, ents, t=None):
    """토스 글에 게시 시점 가격 줄이 없으면 출처 줄 앞(없으면 끝)에 넣음(deal_post와 같은 자리). 엔티티 오프셋은 UTF-16 단위로 뒤로 밂."""
    if "게시 시점 가격" in text:
        return text, ents
    i = text.find("\n\n출처: ")
    i = len(text) if i < 0 else i
    add = "\n" + toss_when(t)
    at, n = len(text[:i].encode("utf-16-le")) // 2, len(add.encode("utf-16-le")) // 2
    return text[:i] + add + text[i:], [{**e, "offset": e["offset"] + n} if e["offset"] >= at else e for e in ents]


def toss_clean_posts():
    """posts.json의 토스 딜 글에서 다른 몰 비교를 뺌(실행마다, 이미 뺀 글은 그대로) -> 사이트 딜 페이지·카드·리스트·Threads가 다음 빌드부터 비교 없이."""
    posts, n = load(POSTS, []), 0
    for p in posts:
        if is_toss(p.get("url"), p["text"]):
            t, e = strip_cmp(p["text"], p.get("entities"))
            if t != p["text"]:
                p.update(text=t, entities=e)
                n += 1
    if n:
        json.dump(posts, open(POSTS, "w"), ensure_ascii=False)
        print("toss 비교 뺌", n)


RUN = {"ok": set(), "fail": {}, "failch": set(), "th_last": 0, "th_why": "", "tg_err": "", "ch_last": 0, "treuse": False}  # 이번 실행 기록(watch 알림용): 올라간 채널·텔레그램 채널 실패·Threads 마지막 글·Threads 대기 이유 · 채널 마지막 딜 글(빈틈 채움) · 토스 점검 재사용 모드(toss_mode)
TG_SEND = ("sendMessage", "sendPhoto", "sendVideo", "copyMessage", "sendMediaGroup")  # 채널 '올리기' 호출(수정·답장 수정은 X)
TOSS_PAUSE = ("2026-10-30 00:00", "2026-11-04 23:59")  # 10/22 Cowork·진우: 토스 쉐어링크 점검(새 링크 X·공유 수익 0)에도 토스 글은 채널·Threads 둘 다 계속 -> 이 동안(KST, 끝 분 포함) 새로 안 만들고 만들어 둔 링크(tlink) 재사용(toss_mode)
TOSS_FEE_DAY = "2026-11-05"  # 토스 공지: 이날 0시 뒤 구매확정분부터 수수료 일괄 8% -> 기본 5%·선착순특가(= 하루특가) 3% (toss_deals 특가 회차 개당 수익)
TOSS_STOCK_DAYS, TOSS_STOCK_GAP, TOSS_STOCK_RUN, TOSS_LINK_KEEP = ("2026-10-28", "2026-10-29"), 4 * 3600, 30, 14 * 86400  # 점검 전 미리 만들기 날(KST, 4시간마다 목록 1번 — toss_stock) · 한 실행 발급 수(실행 6분 한도 — 남으면 다음 실행에 이어서) · 만든 링크 보관 14일(10/22~ 만든 것도 11/4까지 남게)
TOSS_WAIT = 2 * 3600  # 10/18 진우 '토스 링크는 뽐뿌 말고 바로 연결': 쉐어링크 못 찾은 토스 딜은 이만큼 실행마다 다시 찾고 -> 그래도 없으면 진우에게 링크 요청(toss_wait·toss_relink)
TOSS_BACKFILL = (59, 88, 97, 102, 128, 171, 223, 810, 932, 1002, 1049, 1087, 1102, 1204)  # 10/18 뽐뿌 버튼으로 남은 채널 토스 딜(10/7~10/18) -> toss_relink가 1번 새로 찾고 못 찾으면 진우에게
TOSS_FIX, TOSS_FIX_RUN = "tossfix.json", 8  # 10/12 22:50 진우 '앞서 올라간 글에서 쿠팡 비교글은 수정하자': 채널 옛 토스 딜 글 고칠 번호 목록(1번만) · 한 실행 고치는 글 수(채널 분당 약 20개, 품절 지켜보기 8개와 같이)


def toss_fix_channel(seen):
    """토스 비즈니스 요청(10/12 21:05) 전에 올린 채널 토스 딜 글(TOSS_FIX 번호)에서 다른 몰 비교 줄만 editMessage로 뺌 — 본문 = posts.json(21:18부터 비교 뺀 글, 엔티티 그대로),
    버튼 = 원래 글자·링크(진우·Claude 예약 = events.json 버튼 글자, 아니면 buy_label). 품절 지켜보기 기록(sold_)이 있으면 그 모양(⛔ 줄·버튼 글자) 그대로 다시 그림.
    품절 지켜보기 기록 본문도 비교를 빼 둠(나중에 품절 줄을 고칠 때 비교가 돌아오지 않게). 글마다 1번만(실패 = 로그, 지운 글 등)."""
    for w in [w for k, w in seen.items() if k.startswith("sold_") and isinstance(w, dict) and w.get("k") == "ev"]:
        w["pre"], w["body"] = strip_cmp(w.get("pre", ""))[0], strip_cmp(w.get("body", ""))[0]
    fx = load(TOSS_FIX, {})
    key = "tossfix" + str(fx.get("v") or "")  # 목록이 바뀌면(v) 처음부터(10/13 2차 28개)
    done = seen.get(key, {}).get("done", [])
    todo = [m for m in fx.get("mids", []) if m not in done]
    if not todo:
        return
    st = seen[key] = {"t": time.time(), "done": done}
    posts, evs, ok = {p["mid"]: p for p in load(POSTS, []) if p.get("mid")}, load(EVENTS, []), 0
    for mid in todo[:TOSS_FIX_RUN]:
        st["done"].append(mid)  # 먼저 표시: 실패해도 같은 글 반복 안 함
        w, p = seen.get(f"sold_{mid}"), posts.get(mid)
        if isinstance(w, dict) and w.get("k") == "ev":
            text, kb = sold_render(w)
            r = tg("editMessageText", chat_id=CHANNEL, message_id=mid, text=text, parse_mode="HTML", link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": kb})
        elif p:
            ev = [e for e in evs if e.get("url") == p["url"] and e["at"] <= p["t"] and e.get("button")]
            btn = max(ev, key=lambda e: e["at"])["button"] if ev else buy_label(title_of(p["text"]))
            r = tg("editMessageText", chat_id=CHANNEL, message_id=mid, text=p["text"], entities=p.get("entities", []), link_preview_options={"is_disabled": True},
                   reply_markup={"inline_keyboard": [[{"text": btn, "url": p["url"]}]]})
        else:  # 묶음 글(미리보기·TOP5) = posts.json에 없음 -> 관리자 방에 전달해 글·엔티티·버튼을 읽고 비교 조각만 바꿔 다시 씀(전달본은 바로 지움)
            f = tg("forwardMessage", chat_id=ADMIN, from_chat_id=CHANNEL, message_id=mid, disable_notification=True) or {}
            t, ents = cut_cmp(f.get("text", ""), f.get("entities", []))
            kb = f.get("reply_markup")
            r = t != f.get("text", "") and (kb or "1️⃣" not in t) and tg(  # 번호 버튼이 있어야 할 글인데 못 읽었으면 안 고침(버튼이 지워짐)
                "editMessageText", chat_id=CHANNEL, message_id=mid, text=t, entities=ents, link_preview_options={"is_disabled": True}, **({"reply_markup": kb} if kb else {}))
            if f.get("message_id"):
                tg("deleteMessage", chat_id=ADMIN, message_id=f["message_id"])
        ok += bool(r)
        time.sleep(1)
    print("toss 채널 비교 뺌", ok, "/", min(len(todo), TOSS_FIX_RUN), "· 남음", max(0, len(todo) - TOSS_FIX_RUN))


def cut_cmp(text, ents):
    """옛 채널 묶음 글의 쿠팡 비교 조각만 바꿈: 미리보기 줄 끝 ' · 💡 쿠팡 같은 상품보다 N원 쌈' 지움, TOP5 부제 TOP_SUB -> TOP_SUB_TOSS.
    entities(UTF-16)는 바뀐 만큼 밀고, 바뀐 조각과 겹치는 건 뺌(조각을 감싸는 건 길이만 바꿈)."""
    u = lambda s: len(s.encode("utf-16-le")) // 2
    for pat, rep in ((rf" · 💡 ?(?:{OTHER_STORES})[^\n]*?쌈", ""), (TOP_SUB, TOP_SUB_TOSS)):
        while m := re.search(pat, text):
            s, old, new = u(text[:m.start()]), u(m[0]), u(rep)
            ents = [{**e, "offset": e["offset"] + new - old} if e["offset"] >= s + old else e if e["offset"] + e["length"] <= s
                    else {**e, "length": e["length"] + new - old} for e in ents if e["offset"] >= s + old or e["offset"] + e["length"] <= s or e["offset"] <= s and e["offset"] + e["length"] >= s + old]
            text = text[:m.start()] + rep + text[m.end():]
    return text, ents


CMP_REPORT = True  # 10/12 22:50·23:00 진우: Threads·인스타 토스 비교 글 목록(로그, 하루 1번) — 진우가 보고 삭제·재업로드 정함. 다 보면 False


def cmp_report(seen):
    """Threads(10/1~)·인스타 캡션에 올라간 토스 글 중 다른 몰 비교가 든 것 -> 실행 로그에 1줄씩: 게시 시각 · 링크 출처(진우 쉐어링크 = events.json 링크 / 토스 API)
    · 하루특가(지난 날 = 끝남, 재업로드 X) · 제목 · 비교 문구 · 지금 토스 목록 가격(1일 목록에 이름이 같은 게 있을 때만 — 진우 링크는 안 엶) · 주소. 묶음 글(리스트·미리보기)은 '묶음'.
    읽기만 함(삭제 X — 지금 토큰엔 threads_delete 권한 없음)."""
    kst = time.gmtime(time.time() + 9 * 3600)
    key, today = time.strftime("cmprep2_%Y%m%d", kst), time.strftime("%Y-%m-%d", kst)  # 2 = [토스쇼핑]도(10/18) -> 그날 1번 더
    if not CMP_REPORT or key in seen:
        return
    norm = lambda x: re.sub(r"\W", "", x or "")
    jw = {e["url"] for e in load(EVENTS, []) if e.get("url")}
    posts = load(POSTS, [])
    now_list = {norm(x[1]): x[2] for x in seen.get("tosscache", {}).get("items", []) if x[3] > time.time() - 86400}
    now_list.update({k: v[1] for k, v in seen.get("soldmap", {}).get("m", {}).items()} if seen.get("soldmap", {}).get("d") == today else {})

    def line(where, ts, text, url):
        clean = strip_cmp(text)[0].split("\n")
        if not (TOSS_NOTE in text or re.search(TOSS_TAG, text) or re.search(r"toss\.(?:shopping|im)/", text)) or "\n".join(clean) == text:
            return
        cmp = [l for l in text.split("\n") if l not in clean]  # 지워지거나 바뀐 줄 = 비교 문구
        sp = re.search(rf"{re.escape(SITE)}p/(\d+)\.html", text)
        link = posts[int(sp[1])]["url"] if sp and int(sp[1]) < len(posts) else (re.findall(r"https://toss\.(?:shopping|im)/[^\s)]+", text) or [""])[0]
        title = next((l for l in text.split("\n") if re.match(r"(?:🔥|🛒) ", l) and "http" not in l), None) or \
            next((l for l in text.split("\n") if l.strip() and not l.startswith(NOTE_STARTS + ("[광고]",))), text.split("\n")[0])  # 묶음 = 머리 줄
        day = ("하루특가 오늘" if ts[:10] == today else "하루특가 끝남(재업로드 X)") if re.search(r"하루특가|밤 12시", text) else "-"
        price = now_list.get(norm(re.sub(r"^[^\w\[]*(?:\[[^\]]*\]\s*)?|\s*\([^)]*원[^)]*\)\s*$", "", title)))
        print("cmp", where, ts[5:16], "|", "묶음" if len(re.findall(r"https?://", text)) >= 3 else "진우 쉐어링크" if link in jw else "토스 API" if link else "?", "|", day, "|",
              clip(title.strip(), 50), "|", " / ".join(clip(c.strip(), 70) for c in cmp[:2]), "|", f"지금 토스 목록 {price:,}원" if price else "지금 목록에 같은 이름 없음", "|", url)

    tok, n = E.get("THREADS_TOKEN"), 0
    if tok:
        me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
        url = f"{THREADS}/{me}/threads?fields=id,text,timestamp,permalink&limit=100&since=1790780400&access_token={tok}"  # 10/1 0시 KST
        while url and n < 2000:
            r = json.loads(http(url))
            for t in r.get("data", []):
                n += 1
                line("th", (datetime.strptime(t["timestamp"], "%Y-%m-%dT%H:%M:%S%z") + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M"), t.get("text") or "", t.get("permalink", t["id"]))
            after = r.get("paging", {}).get("cursors", {}).get("after")
            url = r.get("paging", {}).get("next") or (after and len(r.get("data", [])) >= 100 and re.sub(r"&after=[^&]*", "", url) + f"&after={after}")
    itok, uid, m = E.get("IG_TOKEN"), E.get("IG_USER_ID"), 0
    try:  # 인스타 캡션(카드 이미지는 사진이라 못 읽음 — 카드 재료는 10/12 확인: 비교 없음)
        url, h = itok and uid and f"{IG}/{uid}/media?fields=id,caption,timestamp,permalink&limit=50", {"Authorization": f"Bearer {itok}"}
        while url and m < 2000:
            r = json.loads(http(url, None, h))
            for t in r.get("data", []):
                m += 1
                line("ig", (datetime.strptime(t["timestamp"], "%Y-%m-%dT%H:%M:%S%z") + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M"), t.get("caption") or "", t.get("permalink", t["id"]))
            url = r.get("paging", {}).get("next")
    except Exception as e:  # 인스타가 실패해도 Threads 목록은 오늘 끝(다시 안 부름)
        print("cmp ig", repr(e))
    seen[key] = time.time()  # 다 읽었으면 오늘은 끝(Threads가 중간에 실패하면 다음 실행에 다시)
    print("cmp 끝 · Threads 글", n, "· 인스타 글", m, "· 삭제 권한: 토큰 = threads_basic·content_publish·manage_insights(README 세팅) — threads_delete 없음")


def record(text, ents, url, mid=None, score=None, extra=None):
    """채널에 올라간 글 -> posts.json (웹사이트·모아보기·카드·릴스 재료). mid = 채널 메시지 번호(나중에 링크 교체용),
    s = Claude 점수(릴스 TOP3), extra = 릴스용 e(이모지)·hook(첫 화면 한 줄)·pts(합리적인 이유)."""
    posts = load(POSTS, [])
    if TOSS_NO_CMP and is_toss(url, text) and not text.startswith("📋"):  # 토스 딜 = 다른 몰 비교 없이(사이트·카드·리스트·Threads) — 📋 묶음 글(행사 목록)은 그대로(첫 줄 '📋'가 지워지면 사이트 카드가 됨)
        text, ents = strip_cmp(text, ents)
    posts.append({"t": time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600)), "text": text,
                  "entities": ents, "url": url, **({"mid": mid} if mid else {}), **({"s": score} if score else {}),
                  **{k: v for k, v in (extra or {}).items() if v}})
    json.dump(posts, open(POSTS, "w"), ensure_ascii=False)


def post_url(mid):
    """채널 글 주소 (@공개채널 또는 -100… 숫자 id)."""
    return f"https://t.me/{CHANNEL[1:]}/{mid}" if CHANNEL.startswith("@") else f"https://t.me/c/{CHANNEL.removeprefix('-100')}/{mid}"


def post_or_draft(d, comment, score, q=None, extra=None):
    """✅ 없이 채널에 바로 게시. 링크프라이스 몰은 검색 제휴 링크가 자동으로 붙음.
    쿠팡처럼 링크를 손으로 만들어야 하는 몰은 관리자에게 채널 글 사본을 보냄 -> 원하면 제휴 링크를 답장(또는 그냥 전송) -> 채널 글 교체(선택).
    채널 게시가 실패하면 초안으로 보내서 딜을 놓치지 않음."""
    text, url, label = deal_post(d, comment, q, extra)
    info = store_info(d["title"], url)
    m = tg("sendMessage", chat_id=CHANNEL, text=text, parse_mode="HTML", link_preview_options={"is_disabled": True},
           reply_markup={"inline_keyboard": [[{"text": label, "url": url}]]})
    if not m:
        return draft(text, url, score=score, info=info, label=label)
    cp = None
    if info.startswith("💰") and not aff_note(url):
        kb = [[{"text": "📢 채널에 올라간 글", "url": post_url(m["message_id"])}],
              [{"text": info.split(" · ")[0] + " · 링크 보내면 채널 글 교체(선택)", "callback_data": "-"}]]
        if info.startswith("💰 쿠팡"):  # 앱 공유·주소 복사 없이: 파트너스 검색 결과 -> 상품 -> 링크 생성 -> URL 복사 -> 봇에 붙여넣기
            kb.insert(1, [{"text": "🔗 파트너스 링크 만들기", "url": CP_SEARCH + urllib.parse.quote(q or keyword(d["title"]))}])
        elif info.startswith("💰 네이버"):  # 상품명 복사 -> 쇼핑커넥트 상품 찾기 검색창에 붙여넣기 -> [링크 발급] -> 링크만 봇에 보내기
            kb.insert(1, [{"text": "📋 상품명 복사", "copy_text": {"text": (q or keyword(d["title"]) or d["title"])[:256]}},
                          {"text": "🔗 쇼핑커넥트 열기", "url": NAVER_SC}])
        elif info.startswith("💰 올리브영"):  # 앱 큐레이터에서 상품 검색 -> 링크 만들기 -> oy.run 링크 답장
            kb.insert(1, [{"text": "📋 상품명 복사", "copy_text": {"text": (q or keyword(d["title"]) or d["title"])[:256]}}]
                      + ([{"text": "🛒 올영 상품 열기", "url": url}] if url != d["url"] else []))
        elif url != d["url"]:  # 상품 주소를 알면: 눌러서 쇼핑앱 열기 -> 공유 -> 제휴 링크 복사 -> 답장 (뽐뿌 글 거칠 필요 없음)
            kb.insert(1, [{"text": "🛒 상품 열기 (앱에서 공유 → 제휴 링크)", "url": url}])
        cp = (tg("copyMessage", chat_id=ADMIN, from_chat_id=CHANNEL, message_id=m["message_id"],
                 reply_markup={"inline_keyboard": kb}) or {}).get("message_id")
    record(m.get("text", ""), m.get("entities", []), url, m.get("message_id"), score, {**(extra or {}), "cp": cp, "hot": d.get("hot"), "pop": d.get("pop"), "vpm": d.get("vpm"), "rec": d.get("rec")})  # cp: 관리자 사본 번호(답장 없이 링크만 보낼 때 찾기용)


def pending_copy(link):
    """답장 없이 제휴 링크만 보냈을 때 바꿀 채널 글: 같은 프로그램(쿠팡·토스·네이버) 사본 중 아직 안 바꾼 가장 최근 글(24시간 안)."""
    shop = {DISCLOSURE: "쿠팡", TOSS_NOTE: "토스", NAVER_NOTE: "네이버", OY_NOTE: "올리브영"}.get(aff_note(link))
    since = time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - 86400))
    return next((p for p in reversed(load(POSTS, [])) if shop and p.get("cp") and p.get("mid") and p["t"] >= since and not p["text"].startswith("📋")
                 and not aff_note(p.get("url0") or p.get("url") or "") and store_info(title_of(p["text"]), p.get("url0") or p.get("url")).startswith("💰 " + shop)), None)  # url0 = 채널 글 주소(사이트만 바꾼 글 — site_relink·link_swap)


def aff_note(url):
    """제휴 링크면 그 프로그램의 대가성 문구, 일반 쇼핑몰 주소면 ''."""
    host = urllib.parse.urlsplit(url).netloc
    return (DISCLOSURE if host in CP_SHORT else TOSS_NOTE if toss_share(url) else NAVER_NOTE if host in NAVER_HOSTS
            else OY_NOTE if host in OY_HOSTS else AFF_NOTE if host in AFF_HOSTS else "")


def aff_notes(urls):
    """링크들의 대가성 문구(프로그램마다 그대로 1줄): 네이버('글 맨 앞')·올리브영('제목·서두') 먼저 — ig_notes와 같은 순서."""
    ns = {aff_note(u or "") for u in urls}
    return "\n".join(n for n in (NAVER_NOTE, OY_NOTE, DISCLOSURE, TOSS_NOTE, AFF_NOTE) if n in ns)


def ad_hook(plain, unit=""):
    """첫 줄 훅(10/11 진우 결정 우선순위): 같은 상품 쿠팡 차이 > 단위가격 > 30일 최저가·순위 > 할인율 -> (이모지, 꾸밈말, 문장) / 없으면 None.
    쿠팡 차이는 글에 '같은 상품…보다 N원 쌈'이 있을 때만(토스 API 상품엔 없음 -> 3·4번)."""
    m = re.search(rf"({SAVE_STORES})\s*같은 상품[^\n—]*?보다\s*([\d,]+원)\s*쌈", plain)
    if m:
        return "💸", f"{m.group(1)}보다 {m.group(2)} 싼", f"{m.group(1)}보다 {m.group(2)} 쌈"
    u = (unit or unit_of({"text": plain})).split(" (")[0].strip()
    if u and re.search(r"\d", u) and len(u) <= 20:
        return "📏", f"{u}꼴", u
    if re.search(r"30일 (내 )?최저가", plain):
        return "📉", "30일 최저가", "30일 최저가"
    r = re.search(r"(?:^|· |\n)([^·\n💰⭐]{1,16}?\d{1,2}위)", plain)
    if r:
        return "🏆", r.group(1).strip(), r.group(1).strip()
    d = re.search(r"(\d{1,2})%\s*(?:할인|↓)|할인율\s*(\d{1,2})%", plain)
    if d:
        return "🔻", f"{d.group(1) or d.group(2)}% 할인", f"{d.group(1) or d.group(2)}% 할인"
    return None


def ad_line(plain, unit=""):
    """개별 딜 글 첫 줄(10/11 진우 결정 — 공정위: 광고 표시는 첫 부분): '[광고] + 훅 + 상품 + 가격'. 둘째 줄은 제휴사 고지문 그대로(ad_head).
    틀 3가지를 제목으로 정해 돌림(같은 모양 반복 X, 같은 글은 고쳐도 같은 틀)."""
    store, name, price = parse(title_of(plain))
    pp = f"{clip(name, 24)} {price.split('/')[0].strip()}".strip()
    if "특가로는 약한 제품" in plain:  # 🛒 약한 딜 = 훅·🔥 없이(본문 🛒·솔직 메모와 같게 — 10/12 0시 Q3500 '[광고] 🔥' 고침)
        return f"[광고] 🛒 {pp}"
    if th_steady(plain):  # 👍 꾸준템 = 특가 훅(💸·📉·🔻) 없이
        return f"[광고] 👍 {pp}"
    h = ad_hook(plain, unit)
    if not h:
        return f"[광고] 🔥 {pp}"
    k = int(hashlib.md5(name.encode()).hexdigest(), 16) % 3
    return ("[광고] {e} {adj} {pp}", "[광고] {pp} — {sent}", "[광고] {e} {sent} · {pp}")[k].format(e=h[0], adj=h[1], sent=h[2], pp=pp)


def ad_head(note, plain, unit=""):
    """채널 개별 딜 글 머리(HTML): 1줄 [광고] 첫 줄 + 2줄 제휴 고지문(그대로) + 빈 줄. 제휴 링크가 아니면(note 없음) ''. Threads 글은 th_note."""
    if not note:
        return ""
    if not ad_on():
        return f"<i>{note}</i>\n\n"
    return f"{esc(ad_line(plain, unit))}\n<i>{note}</i>\n\n"


def plain_of(html_text):
    return html.unescape(re.sub(r"<[^>]+>", "", html_text))


def with_note(text, ents, url):
    """제휴 링크면 대가성 문구를 맨 앞에 붙인 (text, entities). 텔레그램 오프셋은 UTF-16 단위라 그만큼 뒤로 밂."""
    note = aff_note(url)
    if note and text.startswith(NOTE_STARTS) and not text.startswith(note):  # 다른 프로그램 문구(쿠팡 초안에 네이버 링크로 답장 등) -> 그 문구를 떼고 새 문구로(네이버: 문구 누락·변형 시 패널티)
        head, sep, rest = text.partition("\n\n")
        cut = len((head + sep).encode("utf-16-le")) // 2
        text, ents = rest, [{**e, "offset": e["offset"] - cut} for e in ents if e["offset"] >= cut]
    if ad_on() and note and text.startswith("[광고]"):  # 첫 줄·고지문 머리를 지금 링크 기준으로 다시(10/11~ 첫 줄)
        head, sep, rest = text.partition("\n\n")
        cut = len((head + sep).encode("utf-16-le")) // 2
        text, ents = rest, [{**e, "offset": e["offset"] - cut} for e in ents if e["offset"] >= cut]
    if note and not text.startswith(NOTE_STARTS) and not ad_on():
        n = len(note.encode("utf-16-le")) // 2
        return f"{note}\n\n{text}", [{"type": "italic", "offset": 0, "length": n}] + [{**e, "offset": e["offset"] + n + 2} for e in ents]
    if note and not text.startswith(NOTE_STARTS):
        a = ad_line(text)
        la, n = len(a.encode("utf-16-le")) // 2, len(note.encode("utf-16-le")) // 2
        return f"{a}\n{note}\n\n{text}", [{"type": "italic", "offset": la + 1, "length": n}] + [{**e, "offset": e["offset"] + la + 1 + n + 2} for e in ents]
    return text, ents


def relink_channel(notice, mid, url):
    """이미 올라간 채널 글(mid)의 버튼을 url로 교체 + 대가성 문구. 관리자 사본과 posts.json도 같이 고침."""
    posts = load(POSTS, [])
    text, ents = with_note(notice.get("text", ""), notice.get("entities", []), url)
    if TOSS_NO_CMP and is_toss(url):  # 토스 링크로 바꾼 글 = 다른 몰 비교 뺌 + 게시 시점 가격 줄(10/12 전 글엔 없음 — 그 글을 올린 시각으로)
        text, ents = add_when(*strip_cmp(text, ents), next((p["t"] for p in posts if p.get("mid") == mid), None))
    kb = [[{"text": buy_btn(title_of(notice.get("text", "")), url, text), "url": url}]]  # 토스·쿠팡 = 몰별 버튼(10/22, 쿠팡 🚀/📦 = 그 글 머리 줄)
    if not tg("editMessageText", chat_id=CHANNEL, message_id=mid, text=text, entities=ents,
              link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": kb}):
        return
    tg("editMessageText", chat_id=notice["chat"]["id"], message_id=notice["message_id"], text=text, entities=ents,
       link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": kb + [[{"text": "✅ 채널 글 교체됨", "callback_data": "-"}]]})
    for p in posts:
        if p.get("mid") == mid:
            p.update(text=text, entities=ents, url=url)
            p.pop("url0", None)  # 채널 글도 이 주소 = 사이트만 바꾼 표시 지움(link_swap 줄도 더는 안 맞음)
            p.pop("nosite", None)
    json.dump(posts, open(POSTS, "w"), ensure_ascii=False)
    return True


def relink(m, url):
    """초안 m의 구매 버튼을 url로 교체(제휴 링크면 대가성 문구를 맨 앞에) -> (text, entities, 버튼 rows)."""
    text, ents = with_note(m.get("text", ""), m.get("entities", []), url)
    rows = [[{"text": buy_btn(title_of(text), url, text) if mall_of(url, title_of(text)) else "🛒 구매하러 가기", "url": url}]]  # 토스·쿠팡 링크 = 몰별 버튼(10/22)
    rest = [r for r in m.get("reply_markup", {}).get("inline_keyboard", []) if "url" not in r[0]] or \
        [[{"text": "✅ 게시", "callback_data": "ok"}, {"text": "❌ 패스", "callback_data": "no"}]]
    tg("editMessageText", chat_id=m["chat"]["id"], message_id=m["message_id"], text=text, entities=ents,
       link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": rows + rest})
    return text, ents, rows


def link_key(u):
    """같은 링크인지 비교용: 도메인 대소문자·끝 / 무시(쿼리는 그대로)."""
    s = urllib.parse.urlsplit(u or "")
    return s.netloc.lower(), s.path.rstrip("/"), s.query


def admin_title(t, link):
    """진우가 보낸 첫 줄 -> 채널 제목. 앞 이모지·기호를 떼고, 끝 가격이 괄호 밖이면 (가격/배송)으로 묶고(버튼·사이트가 가격을 읽게),
    링크 주소로 몰을 알면 [몰]을 붙임 — 제목이 [단독기획]·[1+1]처럼 몰 아닌 대괄호로 시작해도(10/11 naver.me·oy.run 점검)."""
    t = re.sub(r"^[^\w\[]+", "", t).strip()
    if not re.search(r"\([^()]*원[^()]*\)", t):
        t = re.sub(r"\s+(\d[\d,]*\s*원(?:\s*/\s*\S+|\s+(?:무료|무배)\S*)?)\s*$", r" (\1)", t)
    shop, tag = next((v for k, v in HOST_STORES.items() if k in urllib.parse.urlsplit(link).netloc), ""), store_tag(t)
    return t if not shop or tag and any(k in tag for k in (shop.lower(), *STORES, *EARN_TAGS)) else f"[{shop}] {t}"


def admin_deal(lines, link, mid, seen=None):
    """관리자가 봇에 '상품명·가격 줄 + 제휴 링크'를 새로 보내면(10/10 진우 '봇에 링크+가격 보내면 자동') Claude가 코멘트·단위가격·확인할 점을 달아
    채널에 바로 + posts.json(사이트·모아보기). 링크는 서버에서 열지 않음(파트너스 자기 클릭 방지) -> 적힌 정보로만 판단.
    채널 점수 컷(MIN_SCORE, 수수료 몰 -1) 미만이면 🛒 + '솔직히 특가로는 약한 제품' 줄(10/10 진우 '특가로는 약한 제품이라고 써 보자').
    처리했으면 True, Claude 오류·응답 없음·채널 실패면 False(-> 지금처럼 초안 ✅)."""
    if any(link_key(x.get("url")) == link_key(link) for x in [x for x in load(POSTS, []) if not x.get("shelf")][-80:]):  # 사이트 진열(shelf)은 채널 글 아님 · 15분 안 바뀌어서 다시 보낸 링크(대소문자·끝 / 달라도) -> 두 번 안 올림
        tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": mid}, text="이미 채널에 올린 링크야")
        return True
    title = admin_title(lines[0], link)
    try:
        tone, tsuf = tone_ask(RUN if seen is None else seen, "ch")  # 10/23 진우 말투 4가지(채널 글 직전 2개와 다르게 — seen 기록)
        p = (ai_pick(ADMIN_PROMPT + tsuf, [f"[운영자] {title} |  | 0분 전 | {' / '.join(lines[1:])}"]) or [None])[0]
    except Exception as e:
        print("admin ai_pick 실패", repr(e))
        return False
    if not p:
        return False
    facts = facts_of(p, aff_note(link) == TOSS_NOTE)
    weak = p["score"] < MIN_SCORE - (earns(title) or aff(link))  # 진우 제휴 링크 = 수수료 되는 딜 -> 1점 완화(네이버는 EARN_TAGS에 없음: 커뮤니티 [네이버] 딜은 진우가 링크를 만들어야 수수료라서)
    body = ad_head(aff_note(link), f"🔥 {title}\n\n{p['comment']}", p.get("unit") or "") + mall_view(toss_body(f"{'🛒' if weak else '🔥'} <b>{esc(title)}</b>\n\n"
           + ("🤔 솔직히 특가로는 약한 제품\n" if weak else "") + f"{esc(p['comment'])}{facts}", link), link)  # 토스·쿠팡 = 몰별 틀(10/22)
    m = tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", text=body,
           link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": [[{"text": buy_btn(title, link, plain_of(body)), "url": link}]]})
    if not m:
        return False
    tone_keep(RUN if seen is None else seen, "ch", tone)
    record(m.get("text", ""), m.get("entities", []), link, m.get("message_id"), p["score"], {**{k: p.get(k) for k in ("e", "hook", "pts", "unit", "warn", "who", "use")}, "own": 1, "tone": tone})  # own: 진우가 보낸 링크 -> Threads 엄선에서 안 빠짐 · tone = 채널 한 줄 말투
    tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": mid}, text=f"✅ 채널에 올림 (Claude {p['score']}점{' · 특가로는 약함 표시' if weak else ''})",
       reply_markup={"inline_keyboard": [[{"text": "📢 채널 글", "url": post_url(m["message_id"])}]]})
    return True


def publish_approved(seen=None):
    """관리자 입력 처리. 텔레그램이 입력을 24시간 보관하므로 15분 주기로 충분.
    1) 사본·초안에 링크로 답장 -> 구매 버튼 교체 (쿠팡·토스·네이버 링크는 답장 없이 링크만 보내도 가장 최근 같은 몰 사본)
    2) 봇에게 '제목 줄 + 링크' 새로 보내기 -> 제휴 링크면 Claude 코멘트 달아 채널에 바로(admin_deal, 10/10~), 아니면·실패면 그 딜 초안 생성
    3) ✅/❌ -> 채널 게시/패스 (답장하고 바로 ✅ 눌러도 교체된 링크로 게시)
    4) 음악 파일 보내기 -> 릴스 배경음악 목록(music.json)에 추가
    5) '#일상 …'(사진 + 캡션) -> daily_in(사이트에 사진 저장 -> daily_post가 Threads에)"""
    ups = tg("getUpdates", allowed_updates=["callback_query", "message"]) or []
    fixed = {}
    for u in ups:
        m = u.get("message") or {}
        doc = m.get("document") or {}
        au = m.get("audio") or (doc if doc.get("mime_type", "").startswith("audio/") else None)
        if au and str(m.get("from", {}).get("id")) == ADMIN:
            mus = load(MUSIC, [])
            if all(x.get("u") != au["file_unique_id"] for x in mus):  # 같은 곡 두 번 보내도 1번만 (Pixabay 주소 곡엔 u 없음)
                mus.append({"id": au["file_id"], "u": au["file_unique_id"], "name": au.get("title") or au.get("file_name", "")})
                json.dump(mus, open(MUSIC, "w"), ensure_ascii=False)
            tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": m["message_id"]},
               text=f"🎵 플레이리스트에 등록 (총 {len(mus)}곡) — 출처·라이선스가 없는 곡이라 릴스엔 안 써요(docs/reels/MUSIC.md에 적힌 곡만)")
            continue
        text = m.get("text") or m.get("caption") or ""  # 사진에 글을 붙여 보내도(캡션)
        if text.lstrip().startswith("#일상") and str(m.get("from", {}).get("id")) == ADMIN:
            daily_in({} if seen is None else seen, m, text.strip())
            continue
        rmid = (m.get("reply_to_message") or {}).get("message_id")
        rd = rmid and next((k for k, v in (seen or {}).items() if k.startswith("igrd_") and isinstance(v, dict) and v.get("mid") == rmid), None)
        if rd and text.strip() and str(m.get("from", {}).get("id")) == ADMIN:  # L: 인스타 댓글 알림에 답장 = 고친 문구로 답글
            ok, err = ig_reply_send(seen, rd[5:], text.strip())
            tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": m["message_id"]}, text="✅ 그 댓글에 이 문구로 답글 달았어" if ok else f"⚠️ 답글 실패: {err}")
            continue
        urls = [u.rstrip(").,]>」』'\"") for u in re.findall(r"https?://\S+", text)]  # (링크) 처럼 괄호·문장부호가 붙어도 링크만
        link = next((u for u in urls if aff_note(u)), urls[0] if urls else None)  # 상품 주소 + 제휴 링크를 같이 보내면 제휴 링크로
        if not link or str(m.get("from", {}).get("id")) != ADMIN:
            continue
        if "<iframe" in text:  # 파트너스 배너 코드는 사이트용 -> 단축 URL로
            tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": m["message_id"]}, text="iframe 말고 단축 URL(link.coupang.com/a/…)로 보내줘")
            continue
        if HAS_TOSS and not toss_share(link) and urllib.parse.urlsplit(link).netloc in ("service.toss.im", "toss.shopping"):  # 토스 앱 일반 공유 주소 -> 상품 주소 -> 우리 쉐어링크(못 하면 그대로)
            u = plain(link)
            link = affiliate(u)[0] if (u or "").startswith("https://toss.shopping/t/") else link
        if HAS_CP and re.match(CP_PROD, link):  # 진우가 보낸 쿠팡 상품 주소 -> 파트너스 링크(딥링크 API, 못 하면 그대로 — 10/23). 단축 링크는 그대로
            link = affiliate(plain(link))[0]
        if m.get("reply_to_message"):
            rm = m["reply_to_message"]
            tw = next((k for k, v in (seen or {}).items() if k.startswith("tw_") and isinstance(v, dict) and v.get("ask") == rm["message_id"]), None)
            if tw:  # 토스 링크 요청(toss_wait)에 답장 -> 이제 채널에 게시
                toss_post(seen.pop(tw), link, seen)
                tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": m["message_id"]}, text="✅ 이 링크로 채널에 올렸어")
                continue
            ch = next((b["url"] for r in rm.get("reply_markup", {}).get("inline_keyboard", []) for b in r
                       if b.get("url", "").startswith("https://t.me/")), None)
            if ch:  # 채널에 이미 올라간 글의 사본 -> 채널 글 교체. 답장한 글이 사본이 아니면('✅ 채널에 올림' 안내 등) posts.json 채널 글 본문으로(채널 글이 안내 문구로 안 바뀌게)
                cm = int(ch.rsplit("/", 1)[1])
                p = next((x for x in load(POSTS, []) if x.get("mid") == cm), None)
                relink_channel({**rm, "text": p["text"], "entities": p.get("entities", [])} if p and title_of(p["text"]) != title_of(rm.get("text", "")) else rm, cm, link)
            else:   # 아직 초안 -> 초안 버튼 교체(✅ 때 반영)
                fixed[rm["message_id"]] = relink(rm, link)
            continue
        for u in urls:  # 링크는 본문에서 빼고(남은 빈 괄호도) 제목·코멘트 줄만
            text = text.replace(u, "")
        lines = [re.sub(r"[(\[]\s*[)\]]", "", l).strip().lstrip("🔥").strip() for l in text.split("\n")]
        lines = [l for l in lines if l and not l.startswith(NOTE_STARTS)]  # 붙여넣은 대가성 문구는 빼고 링크 기준으로 다시 붙임
        if not lines and any(link_key(x.get("url")) == link_key(link) for x in [x for x in load(POSTS, []) if not x.get("shelf")][-80:]):  # 링크만 또 보냄 -> 다른 글 버튼을 또 바꾸지 않음
            tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": m["message_id"]}, text="이미 채널 글에 붙인 링크야 (새 딜이면 첫 줄에 상품명 (가격/배송)도 같이)")
            continue
        p = None if lines else pending_copy(link)
        if p:  # 링크만 보냄 -> 가장 최근 같은 몰 사본의 채널 글 교체 + 어느 글을 바꿨는지 답장(새 딜인데 제목을 빠뜨렸으면 바로 알게)
            if relink_channel({"chat": {"id": ADMIN}, "message_id": p["cp"], "text": p["text"], "entities": p["entities"]}, p["mid"], link):
                tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": m["message_id"]}, text=f"🔁 '{title_of(p['text'])}' 채널 글 버튼을 이 링크로 바꿨어. 새 딜이면 첫 줄에 상품명 (가격/배송)도 같이 보내줘",
                   reply_markup={"inline_keyboard": [[{"text": "📢 채널 글", "url": post_url(p["mid"])}]]})
            continue
        if not lines:
            tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": m["message_id"]},
               text="첫 줄에 제목을 같이 보내줘. 예)\n[G마켓] 상품명 (39,910원/무료)\n한 줄 코멘트\n링크")
            continue
        note, body = aff_note(link), "\n".join(lines[1:])
        if not (note and admin_deal(lines, link, m["message_id"], seen)):
            title = admin_title(lines[0], link) if note else lines[0]  # 초안도 채널 글과 같은 제목·버튼([몰]·가격)
            dt = ad_head(note, f"🔥 {title}\n\n{body}") + mall_view(toss_body(f"🔥 <b>{esc(title)}</b>" + (f"\n\n{esc(body)}" if body else ""), link), link)
            draft(dt, link, info="🤖 자동 게시 실패(Claude 오류·채널 실패) · ✅ 누르면 게시" if note else None, label=buy_btn(title, link, plain_of(dt)) if note or mall_of(link, title) else "🛒 구매하러 가기")
    handled = set()
    for u in ups:
        q = u.get("callback_query") or {}
        m = q.get("message")
        if m and str(q["from"]["id"]) == ADMIN and str(q.get("data", "")).startswith("dl:") and m["message_id"] not in handled:  # P: #일상 링크 후보 고름
            handled.add(m["message_id"])
            _, dm, pick = (q["data"].split(":") + ["", ""])[:3]
            v = (seen or {}).get(f"dly_{dm}") or {}
            v = v if v.get("kb") == m["message_id"] else {}  # 지금 후보 목록을 보낸 그 메시지 버튼만
            if v and "pick" not in v and (pick == "x" or pick.isdigit() and int(pick) < len(v.get("c", []))):
                v.update(pick=pick, pt=time.time())
            c = v.get("c", [])[int(v["pick"])] if str(v.get("pick")).isdigit() and int(v["pick"]) < len(v.get("c", [])) else None
            tg("editMessageReplyMarkup", chat_id=m["chat"]["id"], message_id=m["message_id"],
               reply_markup={"inline_keyboard": [[{"text": f"✅ {clip(c['n'], 30)} — 첫 댓글 링크" if c else "✅ 링크 없이 사진만" if v.get("pick") == "x" else "⚠️ 지난 버튼(기록 없음) — 새 버튼에서 골라줘", "callback_data": "-"}]]})
            continue
        if m and str(q["from"]["id"]) == ADMIN and str(q.get("data", "")).startswith("igr:") and m["message_id"] not in handled:  # L: 인스타 답글 초안 [보내기]
            handled.add(m["message_id"])
            v = (seen or {}).get("igrd_" + q["data"][4:]) or {}
            ok, err = (False, "초안 기록 없음") if not v.get("draft") else (True, "") if v.get("done") else ig_reply_send(seen, q["data"][4:], v["draft"])
            tg("editMessageReplyMarkup", chat_id=m["chat"]["id"], message_id=m["message_id"], reply_markup={"inline_keyboard": [[{"text": "✅ 보냄" if ok else f"⚠️ {err[:40]}", "callback_data": "-"}]]})
            continue
        if not m or str(q["from"]["id"]) != ADMIN or q.get("data") not in ("ok", "no") or m["message_id"] in handled:
            continue
        handled.add(m["message_id"])
        chat, mid = m["chat"]["id"], m["message_id"]
        if q["data"] == "ok":
            text, ents, rows = fixed.get(mid) or (m.get("text", ""), m.get("entities", []),
                                                  [r for r in m.get("reply_markup", {}).get("inline_keyboard", []) if "url" in r[0]])
            cp = tg("copyMessage", chat_id=CHANNEL, from_chat_id=chat, message_id=mid,  # 복사는 수정된 현재 내용 기준
                    reply_markup={"inline_keyboard": rows})
            if not cp:
                tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": mid},
                   text="⚠️ 채널 게시 실패: 봇이 채널 관리자인지, TG_CHANNEL 값이 맞는지 확인 후 ✅ 다시 눌러줘")
                continue  # 버튼 유지 -> 재시도 가능
            record(text, ents, rows[0][0]["url"] if rows else None, cp.get("message_id"))
        mark = "✅ 게시됨" if q["data"] == "ok" else "❌ 패스"
        tg("editMessageReplyMarkup", chat_id=chat, message_id=mid,
           reply_markup={"inline_keyboard": [[{"text": mark, "callback_data": "-"}]]})
    if ups:
        tg("getUpdates", offset=ups[-1]["update_id"] + 1)  # 처리한 입력 확인(삭제)


def goldbox(seen):
    kst = time.gmtime(time.time() + 9 * 3600)
    key = time.strftime("goldbox_%Y%m%d", kst)
    if not HAS_CP:  # 최종 승인(API) 전: 아침 7시 골드박스가 바뀌면 파트너스 링크로 하루 1번 바로 게시 -> 24시간 안 쿠팡 구매가 실적
        if key not in seen and kst.tm_hour >= 7 and tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML",
                text=f"<i>{DISCLOSURE}</i>\n\n⏰ <b>오늘의 쿠팡 골드박스 오픈</b>\n매일 아침 7시에 바뀌는 하루 한정 특가예요. 필요한 게 있는지 한 번 둘러보세요 👀",
                reply_markup={"inline_keyboard": [[{"text": "⏰ 골드박스 보러가기", "url": GOLDBOX}]]}):
            seen[key] = time.time()
        return
    if key in seen or kst.tm_hour < 7:  # 최종 승인 후: 7시 골드박스가 바뀌면 TOP5도 ✅ 없이 채널에 바로 (다른 딜과 같은 방식)
        return
    allg = coupang("GET", "/products/goldbox")
    n = cp_photos(seen, allg)  # 진열 상품 사진 채움(10/25 — 추가 호출 X)
    if n:
        print("goldbox 사진", n)
    items = allg[:40]
    picks = ai_pick(GOLD_PROMPT, [f"{x['productName']} | {int(x['productPrice']):,}원" for x in items])[:5]
    rows = [f"{n}. {'🚀 ' if x.get('isRocket') is True else ''}<a href=\"{esc(x['productUrl'])}\">{esc(x['productName'])}</a> — <b>{int(x['productPrice']):,}원</b>\n"
            f"   {esc(p['comment'])}" for n, p in enumerate(picks, 1) for x in [items[p["i"]]]]
    m = rows and tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True},
                    text=f"<i>{DISCLOSURE}</i>\n\n⏰ <b>오늘의 쿠팡 골드박스 TOP{len(rows)}</b>\n\n" + "\n\n".join(rows) + f"\n\n{toss_when()}",  # 🚀 = API isRocket인 것만 · 게시 시점 가격(10/23)
                    reply_markup={"inline_keyboard": [[{"text": "⏰ 골드박스 전체 보기", "url": GOLDBOX}]]})
    if m:
        record(m.get("text", ""), m.get("entities", []), GOLDBOX, m.get("message_id"))
    if not rows and seen.get("gold0", {}).get("d") != key:  # 고른 것 0 = 다음 실행에 1번 더(Claude 판단 흔들림 — 10/25 07:03 40개 중 0개로 그날 조용히 안 올라감)
        seen["gold0"] = {"t": time.time(), "d": key}
        print("goldbox", len(items), "개 중 고른 것 0 — 다음 실행에 1번 더")
        return
    if not rows:
        print("goldbox", len(items), "개 중 고른 것 0(2번째) — 오늘 안 올림")
    if m or not rows:  # 살 만한 게 없으면 오늘은 안 올림(15분마다 다시 고르지 않게)
        seen[key] = time.time()


def cp_links(seen):
    """① 딥링크(10/23 쿠팡 최종 승인): events의 쿠팡 상품 주소(coupang.com/vp/products/…) -> 파트너스 링크(상품마다 1번) -> cp_links.json(봇·사이트가 그 주소 대신 씀).
    진우 단축 링크(link.coupang.com)는 그대로. 안 되는 상품(ValueError)은 관리자 알림 + 하루 뒤 다시, 상한·접속 오류는 다음 실행에. 키 없으면 아무것도 안 함."""
    if not HAS_CP:
        return
    cl, st, now = load(CP_LINKS, {}), seen.setdefault("cpdl", {"x": {}}), time.time()
    st["t"], n, since = now, 0, time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 3 * 3600))  # events()가 아직 올릴 수 있는 것만(6시간 지난 예약은 안 올라감 -> 안 바꿈·알림 X)
    raw = ev_list(EVENTS)
    evs = [e for e in raw if re.match(CP_PROD, e.get("url") or "") and (e.get("at", "") >= since or e.get("shelf"))]  # 사이트 진열(shelf)은 시각 상관없이
    lst = {i["url"]: str(i.get("name") or "") for e in raw if e.get("list") and isinstance(e.get("items"), list) and e.get("at", "") >= since
           for i in e["items"] if isinstance(i, dict) and re.match(CP_PROD, str(i.get("url") or ""))}  # 행사 목록 글(list_post) 상품 = 채널 예약
    evs += [{"url": u, "text": esc(n)} for u, n in lst.items()]
    chan, kst = {e["url"] for e in evs if not e.get("shelf")}, time.gmtime(now + 9 * 3600)
    today, names = time.strftime("%Y-%m-%d", kst), {e["url"]: parse(title_of(plain_of(e.get("text") or "")))[1] for e in evs}
    st["f"] = {u: d for u, d in st.get("f", {}).items() if u in names}  # 진열 실패 날짜들(events에서 빠지면 지움)
    st["e"] = {u: v for u, v in st.get("e", {}).items() if u in names}  # 마지막 실패 이유('400' = 1개만 보낸 호출이 rCode 400 · '응답 없음' = 오류 없이 그 주소만 빠짐)
    rush = set(seen.get("srl", {}).get("now", ()))  # 10/25 21시 '1번 바로' 중인 진열 = site_relink 몫(1개씩 주소 2가지 — 같은 상품 두 번 X)
    todo = [u for u in sorted({e["url"] for e in evs}, key=lambda u: (u not in chan, u)) if (u in chan or u not in rush) and now - st["x"].get(u, 0) >= (86400 if u in chan or len(st["f"].get(u, [])) < 2 else CP_RETRY_DAYS * 86400)]  # 진열은 서로 다른 날 2번 실패하면 그 뒤 CP_RETRY_DAYS일마다(10/24 Cowork 'X' -> 10/25 진우 '다 올려' — 생 주소로 진열 중, 되면 바뀜) · 채널 예약 먼저 · 남은 상품 주소 = 아직 못 바꾼 것(바꾼 건 load가 이미 링크로)
    pq = [b for b in ([u for u in b if u in todo] for b in st.get("pq", [])) if b]  # 지난 실행에 나누다 만 묶음(10/24 리뷰: 안 그러면 매 실행 같은 20개를 처음부터 나눠 — 진열만 4번 호출로는 나쁜 주소 1개를 못 찾아 진열 변환이 멈춤)
    rest = [u for u in todo if not any(u in b for b in pq)]
    one = [[u] for u in rest if u in st["f"] and u not in chan]  # 진열 실패했던 상품 = 1개씩(좋은 주소와 묶으면 묶음 오류 -> 반씩 나누느라 호출이 늘어남) · 채널·목록 예약이 된 것은 채널 먼저 그대로(10/25 리뷰)
    rest = [u for u in rest if [u] not in one]
    q, calls, why = [rest[k:k + CP_DL_BATCH] for k in range(0, len(rest), CP_DL_BATCH)], 0, {}
    q = [b for b in q if chan & set(b)] + pq + [b for b in q if not chan & set(b)] + one  # 채널 예약 먼저
    while q:  # 10/24 진우 '수량 제한 X': 묶어서 변환, 호출 수 상한만(진열만 남으면 이 실행 CP_RUN-2번째 호출까지 — 남은 몫 = 가격 확인·골드박스·커뮤니티 딥링크)
        b = q.pop(0)
        if RUN.get("cpn", [0])[0] >= CP_RUN - 2 and not chan & set(b):  # 이 실행 전체 호출 수(site_relink가 먼저 쓴 몫 포함)
            q.insert(0, b)
            break
        try:
            got = cp_deeplinks(b)
        except ValueError as e:  # 묶음 오류 = 반씩 나눠 다시 · 1개짜리 오류 = 그 상품만 안 됨
            got = {}
            if len(b) == 1:
                print("cp link", b[0], repr(e))
                why[b[0]] = "400"
        except Exception as e:  # 상한·접속·게이트웨이 = 다음 실행에
            print("cp link", repr(e))
            q.insert(0, b)
            break
        calls += 1
        cl.update(got)
        n += len(got)
        miss = [u for u in b if u not in got]
        if miss and len(b) > 1:  # 응답에 빠진 주소 = 따로 다시(어느 것이 안 되는지 — 전부 빠졌으면 반씩)
            q[:0] = [miss] if len(miss) < len(b) else [b[:len(b) // 2], b[len(b) // 2:]]
            continue
        for u in miss:
            st["x"][u], st["e"][u] = now, why.get(u, "응답 없음")
            if u in chan:  # 채널 예약 = 바로 알림
                alert(seen, "alert_cplink_" + re.match(CP_PROD, u)[1], f"⚠️ 쿠팡 링크 변환 안 됨(파트너스 불가 상품일 수 있음) — "
                      + (f"{lst[u] or '?'} (pid {re.match(CP_PROD, u)[1]})\n행사 목록 글에서 그 상품만 빠짐(바뀐 상품 {LIST_MIN}개 밑이면 목록 글 안 올라감)" if u in lst else f"{u}\n그 예약은 안 올라감") + ". 진우 단축 링크(link.coupang.com/a/…)로 events에 넣어줘")
            else:  # 진열 = 하루 1번 묶어서(10/24 Cowork '상품마다 DM 말고') · 3번째(7일 뒤 다시)부터는 알림 X
                st["f"][u] = sorted(set(st["f"].get(u, [])) | {today})
                if len(st["f"][u]) <= 2:
                    st.setdefault("q", {})[u] = names.get(u, "")
    st["pq"] = [b for b in q if len(b) < CP_DL_BATCH]  # 나눈 조각만 저장(통째 묶음은 다음 실행에 다시 만듦)
    if st.get("q") and st.get("qd") != today and kst.tm_hour >= 9:  # 진열 변환 실패 묶음 알림(하루 1번, 9시~ · 상품 번호만 — 주소 쿼리 X)
        if tg("sendMessage", chat_id=ADMIN, text=(f"⚠️ 쿠팡 진열 링크 변환 안 됨 {len(st['q'])}개(rCode 400 — 상품별 파트너스 제휴 불가로 보임)\n"
                                                  + "\n".join(f"· {n or '?'} (pid {re.match(CP_PROD, u)[1]})" + (f" — 2번째(다른 날) · {CP_RETRY_DAYS}일 뒤 다시" if len(st["f"].get(u, [])) >= 2 else " — 내일 1번 더 시도")
                                                              for u, n in st["q"].items()) + "\n사이트엔 쿠팡 상품 주소 그대로 진열 중(수수료 X · 바뀌면 파트너스 링크로). 진우 단축 링크를 같은 pid로 events에 넣으면 사이트 카드도 그 링크로 바뀜(다른 상품으로 바꾸면 생 주소 카드는 그대로 남음)")[:4000]):
            st.update(q={}, qd=today)
    if n:
        json.dump(cl, open(CP_LINKS, "w"), ensure_ascii=False, indent=1)
        print("cp link", f"쿠팡 상품 주소 {n}개 -> 파트너스 링크")
    md = lambda ts: time.strftime("%m-%d %H:%M", time.gmtime(ts + 9 * 3600))
    json.dump([{"pid": re.match(CP_PROD, u)[1], "n": names[u], "f": st["f"].get(u, []), "x": md(st["x"][u]) if u in st["x"] else "", "e": st["e"].get(u, "")}
               for u in sorted(names, key=lambda u: (names[u], u)) if u not in cl], open(CP_FAIL, "w"), ensure_ascii=False, indent=1)  # 아직 안 바뀐 것(x 없음 = 아직 시도 전 — 상한·실행 몫 대기)


def cp_price(seen):
    """② 진우 쿠팡 상품 지금가(10/23 — Cowork 9:10 손 확인 대신): 진우 글(url)마다 하루 1번(CP_CHK_HOUR~, 실행마다 1개, 가장 오래전에 확인한 것 먼저) 글 상품명으로 검색 API
    -> 결과(최대 10개) 중 events pid와 같은 상품(productId 또는 파트너스 링크 pageKey)이고 같은 옵션인 것만(events item = 옵션 itemId가 있으면 그것, 없으면 이름 수량·용량 cp_same)
    -> seen cpq m[url] = [가격(못 찾으면 0), 'YYYY-MM-DD HH:MM'(KST)]
    -> own_end가 events now·chk보다 새것이면 그 값(사이트 ⏳/🔥 같은 값). 못 찾으면 로그에 pid·보낸 검색어·결과 위 3개(pid 있음 = 옵션 다름 / pid 없음 구분).
    상한 = 다음 실행에, 그 밖 오류 = 오늘은 그 글 건너뜀(어제 가격 그대로 · 한 글이 줄을 막지 않게). 키 없으면 아무것도 안 함."""
    kst = time.gmtime(time.time() + 9 * 3600)
    if not HAS_CP or kst.tm_hour < CP_CHK_HOUR:
        return
    today, q = time.strftime("%Y-%m-%d", kst), seen.setdefault("cpq", {"m": {}})
    q["t"], ev = time.time(), ev_info()
    posts = load(POSTS, [])
    names = {p["url"]: parse(title_of(p["text"]))[1] for p in posts if p.get("own") and p.get("url") in ev and not p["text"].startswith("📋")}  # 같은 url 마지막 글 이름
    q["m"], q["e"] = {u: v for u, v in q["m"].items() if u in names}, {u: d for u, d in q.get("e", {}).items() if d == today}  # e = 오늘 오류로 건너뛴 글
    q["i"] = {u: v for u, v in q.get("i", {}).items() if u in names}  # i = 상품 사진(productImage — 사이트 썸네일, 10/24 개편)
    q["r"] = {u: v for u, v in q.get("r", {}).items() if u in names}  # r = 로켓 근거(검색 API isRocket — E 자동 재게시 🚀/📦)
    q["v"] = {u: v for u, v in q.get("v", {}).items() if u in names}  # v = 사진 없는 글의 다음 검색어 번호(cp_kws — pid 찾으면 그대로)
    q["pm"] = {u: v for u, v in q.get("pm", {}).items() if u in names and v[0] == today}  # pm = 사진 없는 글이 오늘 pid 못 찾은 수 — 다음 검색어로 오늘 다시(검색어 수까지)
    bypid = {}
    for u in names:
        if ev[u].get("pid"):
            bypid.setdefault(ev[u]["pid"], []).append(u)
    todo = sorted(((q["m"].get(u, [0, ""])[1], u, ev[u]["pid"], n, ev[u].get("item")) for u, n in names.items() if ev[u].get("pid") and n and (not q["m"].get(u, [0, ""])[1].startswith(today) or ev[u].get("item") and q["m"][u][2:3] != [ev[u]["item"]]
                                                                                                   or u not in q.get("i", {}) and u in q["pm"] and q["pm"][u][1] < len(cp_kws(n))) and u not in q["e"]),
                  key=lambda t: t[0])  # 가장 오래전에 확인한 글 먼저(같으면 글 순서) — 글이 하루 실행 수보다 많아도 뒤쪽이 굶지 않게
    def shown(f, k=None):  # 지난 빌드 쪽에 보이는 딜(쪽 링크 순서 — k = 첫 화면 몇 개)
        try:
            return {posts[int(x)].get("url") for x in re.findall(r'/p/(\d+)\.html', open(f, encoding="utf-8").read().split("<body", 1)[-1])[:k] if int(x) < len(posts)}  # 본문만(머리 JSON-LD = 사진 있는 상품 목록 X — 10/25 리뷰)
        except OSError:
            return set()
    home = shown("docs/index.html")  # 홈에 나오는 상품 — 사진 채움 먼저(10/24 Cowork A①)
    cfirst = set().union(*[shown(f, 12) for f in sorted(glob.glob("docs/c/*/index.html"))])  # 그다음 /c/ 칸마다 첫 화면(10/25 Cowork ② — /c/season/ 사진 1/21)
    rank = lambda u: (u not in home, u not in cfirst)
    wk = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600 - 7 * 86400))
    q["gs"], grp = {w: d for w, d in q.get("gs", {}).items() if d > wk}, collections.defaultdict(list)  # gs = 품목 낱말 검색한 날
    q["gm"] = {u: d for u, d in q.get("gm", {}).items() if d > wk and u in names}  # gm = 품목 낱말 검색에 들어간 글(7일 안 = 다른 낱말로도 다시 묶지 않음)
    shownimg = {p["url"] for p in posts if p.get("img")}  # 사이트에 사진 있는 글(events img·cp_img.json 등) = 묶음 X
    cw = {u: cp_words(n) - set(q["gs"]) for u, n in names.items() if ev[u].get("pid") and u not in q.get("i", {}) and u not in shownimg and u not in q["gm"]}
    cnt = collections.Counter(w for ws in cw.values() for w in ws)
    for u, ws in cw.items():  # 글마다 낱말 1개 = 사진 없는 글에 가장 많이 나오는 것('발난로 … 핫팩' -> 핫팩)
        if ws:
            grp[max(ws, key=lambda w: (cnt[w], w))].append(u)
    gk = {w: min(map(rank, us)) for w, us in grp.items() if len(us) >= CP_GROUP_MIN}
    pho = [x for _, x in sorted([((*gk[w], 0, ""), (0, None, None, w, None)) for w in gk] + [((*rank(t[1]), 1, t[0]), t) for t in todo if t[1] not in q.get("i", {})], key=lambda y: y[0])]  # 사진 없는 것(홈 → 칸 첫 화면 → 나머지 — 같은 칸이면 T 품목 낱말 검색 먼저)과 오래전 확인을 번갈아 — 사진 채우면서 가격 확인도 안 굶게
    old = [t for t in todo if t[1] in q.get("i", {})]
    todo = [t for k in range(max(len(pho), len(old))) for t in pho[k:k + 1] + old[k:k + 1]]
    got = miss = err = gn = 0
    qs = cp_qs
    ps = q.setdefault("ps", {"d": today, "n": 0, "m": 0})  # 사진 검색 수·채운 사진 수(하루 1줄 'img 쿠팡 검색 N번으로 M개' — 다음 날 첫 실행에)
    if ps["d"] != today:
        if ps["n"]:
            print("img", f"쿠팡 검색 {ps['n']}번으로 {ps['m']}개 ({int(ps['d'][5:7])}/{int(ps['d'][8:])})")
        ps.update(d=today, n=0, m=0)
    for _, u, pid, name, item in todo:  # 검색 1번씩(사진 없는 글·오래된 확인 번갈아 — 한 글이 실행 상한을 다 쓰지 않게)
        kws = cp_kws(name) if u else [name]  # u 없음 = 품목 낱말 검색(T)
        v = q["v"].get(u, 0) % len(kws) if u and u not in q.get("i", {}) else 0  # 사진 있는 글 = 늘 이름 그대로(옵션 가격 맞추기) · 없는 글 = 오늘 못 찾은 만큼 다음 검색어
        kw, n0, photo = kws[v], len(q.setdefault("i", {})), not u or u not in q.get("i", {})
        try:
            r = coupang("GET", f"/products/search?keyword={urllib.parse.quote(kw)}&limit=10")
        except CpLimit:
            if not (got or miss or err or gn):  # 이번 실행에 하나도 못 함 = 최근 1시간 상한(실행 1개 다 쓴 건 말 안 함)
                print("cp price 상한(실행 1·시간 6) — 다음 실행에")
            break
        except Exception as e:
            print("cp price", pid or kw, repr(e))
            if u:
                q["e"][u], err = today, err + 1
            else:
                q["gs"][kw], gn = today, gn + 1  # 오류 = 그 낱말 이번 주 X(줄 막지 않게)
            ps["n"] += photo  # 실패한 검색도 1번(상한 셈 그대로)
            continue
        ds = [x for x in (r if isinstance(r, dict) else {}).get("productData") or [] if isinstance(x, dict)]
        ps["n"] += photo
        for z in ds:  # 같은 검색 결과에 다른 진우 글 상품(같은 pid)도 있으면 그 사진도(10/24 진우 1주 ① — 사진 212개 중 14개뿐이던 것, 추가 호출 X) · T 품목 낱말 검색 = 이것만
            for u2 in bypid.get(str(z.get("productId")), ()):
                if u2 != u and u2 not in q["i"] and str(z.get("productImage") or "").startswith("https://") and (not ev[u2].get("item") or qs(z, "itemId") == ev[u2]["item"]):
                    q["i"][u2] = z["productImage"]
        if not u:
            q["gs"][kw], gn = today, gn + 1
            q["gm"].update(dict.fromkeys(grp[kw], today))
            ps["m"] += len(q["i"]) - n0
            print(f"cp img 품목 '{kw}' 사진 없는 글 {len(grp[kw])}개 → 사진 {len(q['i']) - n0}개 · 결과 {len(ds)}개")
            continue
        same = [x for x in ds if pid in (str(x.get("productId")), qs(x, "pageKey"))]
        if u not in q.get("i", {}):
            if same:
                q["v"][u] = v
                q["pm"].pop(u, None)
            else:  # pid 없음 = 다음엔 다음 검색어(오늘 안에 — 검색어 수까지)
                q["v"][u], q["pm"][u] = (v + 1) % len(kws), [today, q["pm"].get(u, [today, 0])[1] + 1]
        x = next((x for x in same if x.get("productPrice") and (qs(x, "itemId") == item if item else cp_same(name, x.get("productName")))), None)  # 쿠팡 이름엔 옵션이 안 붙기도(10/23 고려은단 180정 = 같은 pid 4개 이름 같음)
        q["m"][u] = [int(x["productPrice"]) if x else 0, time.strftime("%Y-%m-%d %H:%M", kst), item or ""]  # [2] = 맞춘 옵션 itemId("" = 이름 cp_same) — events item이 나중에 바뀌면 own_end가 안 믿음
        q.setdefault("r", {})[u] = bool(x) and x.get("isRocket") is True  # 못 찾음 = 로켓 근거 없음(옛 True 그대로 X)
        y = x or next((z for z in same if not item or qs(z, "itemId") == item), None)  # 사진 = 같은 pid면 옵션이 달라도(추가 호출 X) — events item이 있으면 그 옵션 사진만
        if y and str(y.get("productImage") or "").startswith("https://"):
            q["i"][u] = y["productImage"]
        ps["m"] += (len(q["i"]) - n0) * photo
        got, miss = got + bool(x), miss + (not x)
        if not x:  # 원인 찾기(10/23 Cowork — 적중 0): 결과에 pid가 있는데 옵션이 다른지 / 아예 없는지 · 위 3개(키·주소 쿼리 X)
            print(f"cp price 못 찾음 pid {pid} · 검색어 '{kw}' · " + (f"pid 있음 {len(same)}개 = " + (f"item {item} 없음" if item else "옵션 다름(cp_same) — events에 item(옵션 itemId)을 넣으면 그 옵션으로") if same else "pid 없음") + f" · 결과 {len(ds)}개")
            for y in ds[:3] + [y for y in same if y not in ds[:3]][:6]:
                print(f"  {y.get('productId')} {str(y.get('productName') or '')[:30]}" + (f" ← 같은 pid · item {qs(y, 'itemId') or '-'}" if y in same else ""))
    if got or miss or err:
        print("cp price", f"진우 쿠팡 상품 {got}개 가격 확인 · 못 찾음 {miss} · 오류 {err} · 오늘 남음 {len(todo) - len(gk) - got - miss - err}")


def cp_words(name):
    """품목 낱말 후보(T — 사진 없는 쿠팡 글 묶기): 사이트 품목 칸 정규식에 맞는 글자를 앞뒤 한글까지 늘린 낱말 전부
    ('발난로 핫팩' -> {'발난로', '핫팩'} · '홈매트'의 '매트' -> '홈매트' · '스카치브라이트'의 '브라' -> '스카치브라이트' — 리뷰 10/26)."""
    out = set()
    for _, _, r in SHELF_CATS:
        for m in re.finditer(r, name):
            s, e = m.span()
            while s and "가" <= name[s - 1] <= "힣":
                s -= 1
            while e < len(name) and "가" <= name[e] <= "힣":
                e += 1
            out.add(name[s:e].strip())
    return out - {""}


def cp_kws(name):
    """쿠팡 검색어 1~3개(10/24 Cowork A① 사진 채움 — pid가 결과 10개 안에 없을 때 다음 것): 이름 그대로 · 수량·용량 뺀 이름 · 브랜드(첫 낱말) + 끝 두 낱말(핵심 낱말)."""
    b = " ".join(re.sub(r"[(\[][^)\]]*[)\]]|" + CP_QTY + r"|[{}/+,·]|(?<![가-힣a-z])[x×](?![가-힣a-z])", " ", name, flags=re.I).split())  # 괄호 안(옵션)·수량·용량 뺌
    w = [x for x in b.split() if not re.fullmatch(r"대용량|묶음|세트|기획|기획세트|증정|단품|본품|정품|무료배송|택1|리필|팩|개|대|특대|국내산", x)]
    c = " ".join([w[0]] + w[-2:]) if len(w) >= 4 else ""
    return list(dict.fromkeys(k[:50] for k in (name, b, c) if len(k) >= 2)) or [name[:50]]


def cp_same(name, api):
    """검색 결과 이름이 진우 글과 같은 옵션인지: 글의 수량·용량 글자가 다 있고 글에 없는 묶음 수(개·팩·켤레·2+1·x2…)는 없음. 글에 수량이 없으면 결과에도 없어야(1개·1팩은 무시).
    캔·병·개입·입 = 개(쿠팡 이름은 '24개' — 글은 '24캔')."""
    qty = lambda s: {re.sub(r"(캔|병|개입|입)$", "개", re.sub(r"\s", "", t).lower()) for t in re.findall(CP_QTY, s or "", re.I)} - {"1개", "1팩", "1세트", "1박스", "1봉", "1p"}
    need, got = qty(name), qty(api)
    extra = got - need
    return need <= got and not (extra if not need else {t for t in extra if re.search(r"(개|팩|세트|박스|봉|켤레|족|판|장|p|\d)$", t)})


def html_ents(h):
    """텔레그램 HTML(<b>·<i>·<a href>) -> (글자, text_link 엔티티 — UTF-16 오프셋): 채널에 안 보내는 사이트 진열 글(shelf)을 채널 글과 같은 posts.json 모양으로."""
    text, ents, u16 = "", [], lambda x: len(x.encode("utf-16-le")) // 2
    for m in re.finditer(r'<a href="([^"]*)">(.*?)</a>|<[^>]*>|[^<]+', h, re.S):
        if m[1] is not None:
            ents.append({"type": "text_link", "offset": u16(text), "length": u16(plain_of(m[2])), "url": html.unescape(m[1])})
            text += plain_of(m[2])
        elif not m[0].startswith("<"):
            text += html.unescape(m[0])
    return text.strip(), ents


CP_IMG = "cp_img.json"  # 10/25 Cowork {쿠팡 pid: 사진 주소} — shelf_posts가 같은 pid 글(사진 없는 것) 사진으로(img_of 허용 목록 · 파트너스 API 사진이 먼저)
SITE_RELINK_DAYS, RELINK = 7, "relink.json"  # 사이트 ② 생 주소(커뮤니티 쿠팡·옥션 등) 수수료 링크로 다시 = 안 되면 7일 뒤 · relink.json = 바뀐 수·끝까지 안 된 것(Cowork·진우 확인 — 가격 X)


def site_relink(seen):
    """사이트 ② 생 주소 -> 수수료 링크(10/25 20:3x Cowork 최종 규칙 '수수료 길이 있는 몰 = 당분간 보이고 수수료 링크로 교체'): posts.json 커뮤니티 글의
    쿠팡 주소(상품·검색) = 파트너스 딥링크(cp_links.json에 이미 있으면 그것 — 호출 X) · 링크프라이스 몰(LP_HOSTS — 옥션·G마켓·롯데온·이마트) 주소 = 딥링크 API result S만(LP_HOSTS 직접 링크 X — 승인 안 된 링크가 제휴로 보임).
    되면 그 주소 글 전부 url = 수수료 링크 + 그 대가성 문구(사이트만 — 텔레그램 채널 글은 그대로) · 안 되면 SITE_RELINK_DAYS일 뒤 다시.
    10/25 21시 진우 '쿠팡 88개 수수료 링크로 교체': 처음 1번(st now)은 7일 규칙 없이 지금 생 주소 전부 — 진열 글(shelf) 쿠팡 생 주소도(되면 cp_links.json -> 같은 실행 shelf_posts가 그 자리에서 바꿈 ·
    그 뒤 진열 재시도는 cp_links 몫). 쿠팡 = 1개씩(묶음 하나가 400이면 묶음 전체 실패) 주소 2가지(① 원래 주소 itemId 포함 ② www.coupang.com/vp/products/PID — 기본 옵션으로 열림, 바뀐 수에 따로 셈) ·
    호출 = 이번 실행 CP_RUN-2번째까지(가격 확인·골드박스 몫) + 시간당 상한(CpLimit) = 실행마다 나눠서."""
    posts, now, cl = load(POSTS, []), time.time(), load(CP_LINKS, {})
    host = lambda u: urllib.parse.urlsplit(u).netloc.lower()
    lpm = lambda u: next((v for k, v in LP_HOSTS.items() if host(u) == k or host(u).endswith("." + k)), None)
    cands = {p["url"]: p for p in posts if isinstance(p.get("url"), str) and not p.get("shelf") and not p["text"].startswith("📋") and not aff(p["url"])
             and (host(p["url"]).endswith("coupang.com") or lpm(p["url"]))}
    shelf = {p["url"]: p for p in posts if p.get("shelf") and re.match(CP_PROD, p.get("url") or "") and p["url"] not in cl}
    alls, kind = {**shelf, **cands}, lambda u: lpm(u) or ("진열" if u in shelf else "커뮤니티")
    st = seen.setdefault("srl", {"x": {}})
    if "now" not in st:  # 1번만(배포 뒤 첫 실행) = 지금 생 주소 전부 바로 · 진열 먼저
        st["now"] = sorted(alls, key=lambda u: (u not in shelf, u))
    st["t"], st["now"] = now, [u for u in st["now"] if u in alls]
    st["x"], st["e"] = {u: t for u, t in st.get("x", {}).items() if u in alls}, {u: v for u, v in st.get("e", {}).items() if u in alls}  # e = 주소마다 응답(①·②)
    forms = lambda u: list(dict.fromkeys([u, f"https://www.coupang.com/vp/products/{re.match(CP_PROD, u)[1]}"])) if re.match(CP_PROD, u) else [u]  # 원래 주소(옵션 그대로) 먼저 — 상품 번호만 = 기본 옵션으로 열림(10/25 리뷰)
    why = lambda x: "응답에 링크 없음" if str(x).startswith("deeplink") else re.sub(r"\s*https?://\S+", "", str(x).replace("coupang rCode ", "rCode "))[:80]
    got, stop = {}, not HAS_CP
    for u in st["now"] + sorted(u for u in cands if u not in st["now"] and now - st["x"].get(u, 0) >= SITE_RELINK_DAYS * 86400):
        link, f0 = None, u  # f0 = 된 주소 모양(② 상품 번호만 = 기본 옵션)
        if lpm(u):
            try:
                link, w = lp_api(u)
            except Exception as x:  # 접속 오류 = 다음 실행에
                print("site relink 링크프라이스", type(x).__name__)
                continue
            st["e"][u] = [] if link else [w]
        elif cl.get(u):  # 같은 주소를 cp_links가 이미 바꿈 = 그 링크(진열·예약과 같은 값)
            link = cl[u]
        elif stop:
            continue
        else:
            e = st["e"][u] = [] if len(st["e"].get(u, [])) >= len(forms(u)) else st["e"].get(u, [])  # 다 시도한 뒤(7일 뒤) = 처음부터
            for f in forms(u)[len(e):]:
                if RUN.get("cpn", [0])[0] >= CP_RUN - 4:  # 이 실행 2번까지(cp_links보다 먼저 돎 — 10/25 22:30 점검: cp_links가 몫을 다 써 '1번 바로'가 멈춰 있던 것) · 나머지 = 진열 묶음·가격 확인·골드박스
                    stop = True
                    break
                try:
                    link, f0 = cp_deeplink(f), f
                    break
                except ValueError as x:  # 그 주소 안 됨 = 다음 모양
                    e.append(why(x))
                except Exception as x:  # 상한·접속·게이트웨이 = 다음 실행에 이어서(시도한 모양은 e에)
                    print("site relink 쿠팡", type(x).__name__)
                    stop = True
                    break
            if not link and len(e) < len(forms(u)):
                continue
        if link:
            got[u] = link
            st["e"].pop(u, None)
            ok, kk = st.setdefault("ok", {}), kind(u) + (" ②상품 번호만" if f0 != u else "")  # 바뀐 수(진열·커뮤니티·옥션 … · ② = 기본 옵션 링크)
            ok[kk] = ok.get(kk, 0) + 1
        else:
            st["x"][u] = now
            print("site relink 안 됨", (re.match(CP_PROD, u) or [0, host(u)])[1], " · ".join(st["e"][u]))
        if u in st["now"]:
            st["now"].remove(u)
    md = lambda ts: time.strftime("%m-%d %H:%M", time.gmtime(ts + 9 * 3600))
    json.dump({"left_now": len(st["now"]), "ok": st.get("ok", {}),
               "fail": [{"k": kind(u), "pid": (re.match(CP_PROD, u) or [0, ""])[1], "n": re.sub(r"\s*[\d,]+\s*원\S*", "", parse(title_of(alls[u]["text"]))[1]).strip(),  # 이름 속 가격 X(공개 파일)
                         "e": " · ".join(f"{'①②'[k] if len(v) > 1 else ''}{w}" for k, w in enumerate(v)), "x": md(st["x"][u]) if u in st["x"] else ""}
                        for u, v in sorted(st["e"].items()) if len(v) >= len(forms(u))]}, open(RELINK, "w"), ensure_ascii=False, indent=1)  # 끝까지 안 된 것(응답 = ①·② 모양마다)
    if not got:
        return
    n = 0
    for p in posts:
        if p.get("url") in got and not p.get("shelf"):  # 진열 글 = events 몫(아래 cp_links.json -> shelf_posts가 그 자리에서 바꿈)
            p.setdefault("url0", p["url"])  # 처음 주소(link_swap이 이걸로 찾음)
            p["url"] = got[p["url"]]
            p["text"], p["entities"] = with_note(p["text"], p.get("entities") or [], p["url"])
            n += 1
    json.dump(posts, open(POSTS, "w"), ensure_ascii=False)
    if any(re.match(CP_PROD, u) and u not in cl for u in got):  # 같은 쿠팡 상품 주소의 events 예약·진열도 이 링크로(봇·사이트가 같은 값 · 이미 있는 것은 안 바꿈)
        cl.update({u: v for u, v in got.items() if re.match(CP_PROD, u) and u not in cl})
        json.dump(cl, open(CP_LINKS, "w"), ensure_ascii=False, indent=1)
    print("site relink", f"생 주소 {len(got)}개(글 {n}개 · 진열 {len(set(got) & set(shelf))}) -> 수수료 링크 · 1번 바로 남은 {len(st['now'])}개")


LINK_SWAP = "link_swap.txt"  # 뽐뿌 원문에서 뽑은 원래 상품 주소(Cowork — 진우 크롬 · 줄 = 글 시각|md5(옛 url)[:8]|종류|새 주소 · Cowork가 계속 덧붙임)


def link_swap(seen):
    """posts.json 글 주소 바꾸기(10/25 21:3x 진우 '네이버 검색 중 쇼핑커넥트 참여한 것으로 교체' — 사이트만, 채널 글 그대로 · 옛 주소 = url0): link_swap.txt 줄마다
    시각·md5(처음 주소 = url0, 없으면 url)가 맞는 글 · 같은 글에 줄이 여러 개면 파일 마지막 줄(21:4x) · 글에 적용한 줄(sw)과 같으면 건너뜀(여러 번 돌아도 같은 결과).
    종류: naver_direct = 네이버 상품 주소 그대로(수수료 0) · connect = 진우 쇼핑커넥트 naver.me 그대로(제휴) · none = 진우가 쇼핑커넥트 '참여 안 함' 확인 -> 사이트 X(nosite · 주소 그대로) ·
    naver_other_link = 남의 naver.me·광고 링크 -> plain(리다이렉트·추적값 뺌)으로 스마트스토어·브랜드스토어 상품 주소만(못 풀면 X — 남의 제휴 링크 안 씀) ·
    toss = affiliate(우리 쉐어링크 — 안 되면 X) · lp = 링크프라이스 API result S만(옥션 ego.aspx = 상품 주소 아님 X). 안 된 줄 = 하루 뒤 다시."""
    try:
        rows = [[x.strip() for x in l.split("|")] for l in open(LINK_SWAP, encoding="utf-8") if l.strip() and not l.startswith("#")]
    except OSError:
        return
    posts, now = load(POSTS, []), time.time()
    host = lambda u: urllib.parse.urlsplit(u).netloc.lower()
    idx, last = {}, {}
    for p in posts:
        if isinstance(p.get("url"), str) and not p["text"].startswith("📋"):
            idx.setdefault((p.get("t"), hashlib.md5((p.get("url0") or p["url"]).encode()).hexdigest()[:8]), []).append(p)
    for r in rows:
        r = r + [""] if len(r) == 3 and r[2] == "none" else r  # none = 새 주소 칸 빈칸(끝 '|' 없어도)
        if len(r) == 4:
            last[(r[0], r[1])] = r  # 마지막 줄이 이김
    st = seen.setdefault("lsw", {"x": {}})
    cur = {"|".join(r) for r in last.values()}
    st["t"], st["x"] = now, {k: v for k, v in st.get("x", {}).items() if k in cur}  # 안 된 줄(줄 전체 = 키 — 새 줄이 오면 바로 시도)
    got = {}
    for key, r in last.items():
        kind, new, sig, link = r[2], r[3], f"{r[2]}|{r[3]}", None
        ps = [p for p in idx.get(key, []) if p.get("sw") != sig]
        if not ps or now - st["x"].get("|".join(r), 0) < 86400 or kind != "none" and (not new.startswith("https://") or re.search(r"\s", new)):
            continue
        try:
            if kind == "naver_direct" and host(new).endswith("naver.com") or kind == "connect" and host(new) in NAVER_HOSTS:
                link = new
            elif kind == "naver_other_link":
                link = (lambda u: u if u and host(u).endswith(("smartstore.naver.com", "brand.naver.com")) else None)(plain(new))
            elif kind == "toss":
                link = (lambda x: x[0] if x[1] else None)(affiliate(new))
            elif kind == "lp" and "/ego.aspx" not in new.lower():
                link = lp_api(new)[0]
        except Exception as e:  # 접속 오류 = 하루 뒤
            print("link swap", kind, type(e).__name__)
        if not link and kind != "none":
            st["x"]["|".join(r)] = now
            print("link swap 안 됨", kind, r[0], host(new))
            continue
        for p in ps:
            if kind == "none":
                p["nosite"] = 1
            else:
                p.setdefault("url0", p["url"])
                p["url"] = link
                p.pop("nosite", None)
                if not aff_note(link) and p["text"].startswith(NOTE_STARTS):  # 제휴 -> 수수료 0 주소 = 옛 대가성 문구 뗌
                    head, sep, rest = p["text"].partition("\n\n")
                    cut = len((head + sep).encode("utf-16-le")) // 2
                    p["text"], p["entities"] = rest, [{**e, "offset": e["offset"] - cut} for e in p.get("entities") or [] if e["offset"] >= cut]
                p["text"], p["entities"] = with_note(p["text"], p.get("entities") or [], link)
            p["sw"] = sig
        got[kind] = got.get(kind, 0) + len(ps)
    if got:
        json.dump(posts, open(POSTS, "w"), ensure_ascii=False)
        print("link swap", " · ".join(f"{k} {n}" for k, n in got.items()), "-> 글 주소 바꿈·사이트 X(none — 사이트만)")


def shelf_posts(seen):
    """사이트 진열 전용(10/24 진우 '생필품·화장품은 사이트에 먼저 빠르게'): events "shelf": true 항목 -> at이 지나면 posts.json에만 1번(own·shelf, 채널 글 번호 mid 없음)
    = 사이트 품목 칸·🔥/⏳(target·now — own_end)·상품 페이지·사이트맵 · 채널·Threads·인스타 X(load(EVENTS)가 shelf를 빼고, posts 쪽은 shelf 글을 건너뜀).
    글 = 채널에 나갈 것과 같은 틀(대가성 문구·몰별 머리 줄·버튼 가격). 같은 url·pid 진우 글이 이미 있으면 안 만듦(사이트 카드 하나 —
    나중에 같은 url 채널 예약이 나가면 그 글이 진열 자리를 이어받음: build_site.home_pool = url마다 최신 진우 글).
    쿠팡 상품 주소 = 딥링크 전이어도 at이 지나면 생 주소 그대로(10/25 진우 '품목들은 무조건 다 올려' — 대가성 문구·[광고] X: aff_note = 제휴 링크만 · 20:3x Cowork 최종 규칙 ②) ->
    나중에 cp_links가 바꾸거나 같은 pid 파트너스 링크가 events에 오면 그 글을 그 자리(posts 번호·사이트 쪽 주소·찜 그대로)에서 파트너스 링크 + 대가성 문구로 바꿈(채널·Threads·인스타는 지금처럼 바뀐 링크만)."""
    now, posts, ev, cl = time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600)), load(POSTS, []), ev_info(), load(CP_LINKS, {})
    itm, same, cpq, fix = lambda u: ev.get(u, {}).get("item") or (re.search(r"[?&]itemId=(\d+)", u) or [0, ""])[1], {}, seen.get("cpq", {}), 0
    for u, i in ev.items():  # 같은 상품(pid)의 파트너스 링크(진우 단축 링크·딥링크) — events에서 생 주소를 바꿔 넣거나 같은 상품 채널 예약이 와도 카드 하나(10/25 리뷰 · 옵션 itemId가 둘 다 있고 다르면 X)
        if i.get("pid") and urllib.parse.urlsplit(u).netloc in CP_SHORT:
            same.setdefault(i["pid"], []).append(u)
    for p in posts:
        m = p.get("shelf") and re.match(CP_PROD, p.get("url") or "")
        new = m and (cl.get(p["url"]) or next((v for v in same.get(m[1], []) if not (itm(p["url"]) and ev[v].get("item") and ev[v]["item"] != itm(p["url"]))), None))
        if not new:
            continue
        for k in ("m", "i", "r", "v", "pm", "gm"):  # cp_price 기록(검색 가격·사진·로켓·T 품목 낱말 검색에 든 글)도 새 주소로 — 안 그러면 다음 검색 전까지 events 옛 가격으로 '특가 끝'·'다시 특가'가 잘못 뜸(10/25 리뷰)
            if p["url"] in cpq.get(k, {}):
                cpq[k].setdefault(new, cpq[k].pop(p["url"]))
        p["url"] = new
        p["text"], p["entities"] = with_note(p["text"], p.get("entities") or [], new)
        fix += 1
    raw, ph, ci = {v: k for k, v in cl.items()}, 0, load(CP_IMG, {})  # 파트너스 링크 -> 생 주소(상품 번호 찾기)
    pid_of = lambda u: ev.get(u, {}).get("pid") or (re.match(CP_PROD, u or "") or [0, ""])[1]
    pim = {str(k): v for k, v in ci.items() if isinstance(v, str)} if isinstance(ci, dict) else {}  # 10/25 Cowork cp_img.json {pid: 사진 주소}(쿠팡 검색 화면 사진 — 계속 늘어남)
    for u, i in ev.items():  # events img(진열 쿠팡 썸네일)가 cp_img.json보다 먼저
        if i.get("img") and pid_of(u):
            pim[pid_of(u)] = i["img"]
    eimg = lambda p: ev.get(p.get("url") or "", {}).get("img") or next((pim[x] for u in (p.get("url"), p.get("url0"), raw.get(p.get("url"))) if u and (x := pid_of(u)) in pim), None)
    for p in posts:  # 10/25 Cowork: events img·cp_img.json -> 같은 url·같은 상품 번호(url0 = 사이트만 바꾼 글의 처음 주소 · cp_links 생 주소) 글 사진 — 이미 있는 글도(진열·진우 글·커뮤니티 쿠팡 딜) · 있는 사진(파트너스 API) 그대로 · img_of 허용 목록만(네이버 X)
        if not p.get("img") and (im := img_of({**p, "img": eimg(p)})):
            p["img"], ph = im, ph + 1
    if fix or ph:
        json.dump(posts, open(POSTS, "w"), ensure_ascii=False)
        print("shelf", " · ".join(x for x in (fix and f"생 주소 진열 {fix}개 -> 파트너스 링크", ph and f"사진 {ph}개 채움") if x))
    have = {p.get("url") for p in posts if p.get("own")}
    pids, n = {ev[u]["pid"] for u in have if ev.get(u, {}).get("pid")}, 0
    for e in ev_list(EVENTS):
        if not (isinstance(e, dict) and e.get("shelf") and isinstance(e.get("url"), str) and e.get("text") and str(e.get("at", "9")) <= now) or e["url"] in have or e.get("pid") and e["pid"] in pids:
            continue
        e = {**e, "deal": True}  # 진열 = 상품 글 틀(몰별 머리 줄·[광고] 첫 줄)
        t, ents = html_ents(ev_head(e) + ev_view(e)[0])
        record(t, ents, e["url"], extra={"own": 1, "shelf": 1, "tag": e.get("tag"), "img": img_of({"text": t, "url": e["url"], "img": eimg({"url": e["url"]})})})
        have.add(e["url"])
        pids.add(e.get("pid") or e["url"])
        n += 1
    if n:
        print("shelf", f"사이트 진열 {n}개")


def events(seen):
    """예약 게시: 시각이 됐고 6시간 안 지났으면 채널에 1번(제휴 링크면 그 대가성 문구 맨 앞, "pin": true면 채널 맨 위 고정, "deal": true면 딜로 기록, "list": true면 행사 목록 글 — list_post). 놓친 지 오래된 글은 안 올림(식은 글)."""
    kst = lambda h: time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + h * 3600))
    for ev in load(EVENTS, []):
        key = "ev_" + ev["at"]
        if key in seen or (ev.get("api") and not ev.get("url")) or not (kst(9 - 6) <= ev["at"] <= kst(9)):  # api(링크 없음) = 토스 API 상품 이름 예약 -> toss_picks가 찾아서 올림
            continue
        if ev.get("list"):
            list_post(seen, ev, key)
            continue
        if HAS_CP and re.match(CP_PROD, ev.get("url") or ""):  # 쿠팡 상품 주소 = 파트너스 링크로 바뀐 뒤에(cp_links — 상한·오류면 다음 실행, 6시간 안)
            continue
        if ev.get("re") and (bot := next((p for p in reversed(load(POSTS, [])) if p.get("re") and p.get("url") == ev.get("url")), None)) \
                and kst_ts(bot["t"]) > time.time() - CPRE_DAYS * 86400:  # E: 봇이 3일 안에 자동 재게시한 상품의 Cowork 재게시 = 두 번 X(관리자에게 알림)
            seen[key] = time.time()
            print("events 재게시 건너뜀(봇 자동 재게시 3일 안)", ev["at"])
            tg("sendMessage", chat_id=ADMIN, text=f"ℹ️ {ev['at']} 재게시 예약은 건너뜀 — 봇이 {bot['t']}에 같은 상품을 자동 재게시함(3일 안). 다른 상품으로 바꿔 넣어 주세요.")
            continue
        body, btn = ev_view(ev)
        m = tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True},
               text=ev_head(ev) + body, reply_markup={"inline_keyboard": [[{"text": btn, "url": ev["url"]}]]})
        if m:
            seen[key] = time.time()
            if ev.get("name") and toss_share(ev["url"]):  # 진우 토스 예약 -> 품절 지켜보기(toss_soldout): 이 글 번호·이 예약의 본문 그대로(같은 링크를 두 번 예약해도 안 섞임)
                seen[f"sold_{m['message_id']}"] = sold_ev(ev, time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600)))
            if ev.get("deal"):  # Claude가 예약한 상품 딜(10/10 진우 '쓰레드에 업로드 되게') -> posts.json = 사이트·모아보기·Threads에도
                record(m.get("text", ""), m.get("entities", []), ev["url"], m["message_id"], extra={"tag": ev.get("tag"), "own": 1})  # "tag": "정품" -> 사이트 정품 배지·칸(10/10)
            if ev.get("pin"):  # 10/10 채널 고정 글(사용법). 봇에 고정 권한이 없으면 글만 남음 -> 진우가 길게 눌러 고정
                tg("pinChatMessage", chat_id=CHANNEL, message_id=m["message_id"], disable_notification=True)


LIST_NUM, LIST_MIN, LIST_WAIT, LIST_MAX = NUM + "6️⃣ 7️⃣ 8️⃣ 9️⃣ 🔟".split(), 3, 30 * 60, 4000  # 행사 목록 글: 번호(11번부터 '11.') · 쿠팡 링크로 바뀐 상품 3개↑ · 안 바뀐 게 남아도 예약 30분 지나면 바뀐 것만 · 텔레그램 글 1개 글자 수(넘으면 나눔)
LIST_CHECK = "⚠️ 행사 상품 여부·최종가는 결제 전 확인"


def list_post(seen, ev, key):
    """쿠팡 행사 목록 글(10/24 진우 '행사가 있으면 3개 + 목록 1개' · 개수 제한 X): events {"at", "list": true, "title", "until": "YYYY-MM-DD", "items": [{"url": 쿠팡 상품 주소·토스 링크, "name", "price", "unit"}]}
    -> 채널: 대가성 문구 + '🎉 <b>{title} · 핫딜픽이 고른 N개</b> (~M/D)' + 번호 줄('1️⃣ <a>이름</a> 가격 · 단가') + 확인 줄, 버튼 1개(그 글 첫 상품 — 묶음 글 버튼처럼 번호·이름) — LIST_MAX자 넘으면 글 여러 개('(1/2)')
    + Threads 묶음 글(같은 순서·가격 · 수수료 링크 앞 4개까지 480자, 남은 건 '전체 N개 → 채널 글') + posts.json('📋' = 사이트 카드·Threads 딜·리스트 X — 상품마다 진열 카드가 따로 · url = 채널 글 · metrics = kind list).
    쿠팡 상품 주소 = cp_links가 바꾼 뒤(ev_list가 items도): 안 바뀐 게 없으면(실패 = 하루 뒤 다시라 이 예약엔 X) 바로, 남았어도 예약 LIST_WAIT 지나면 바뀐 것만 — LIST_MIN개↑일 때.
    LIST_MIN개 밑 = 관리자 알림 1번 + 안 올림(바뀌는 중이면 5시간까지 기다림). 토스는 토스끼리(다른 몰과 섞이면 토스 상품을 뺌 — 토스 = 다른 몰 이름·비교 X)."""
    now, x = time.time(), seen.get("cpdl", {}).get("x", {})
    at = lambda sec: time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 9 * 3600 - sec))
    its = [i for i in ev.get("items") or [] if isinstance(i, dict) and str(i.get("url") or "").startswith("https://") and str(i.get("name") or "").strip()]
    tossy = lambda u: urllib.parse.urlsplit(u).netloc in TOSS_HOSTS
    its = [i for i in its if not tossy(i["url"]) or toss_share(i["url"])]  # 토스 상품 주소(쉐어링크 아님) = 수수료 X
    if any(tossy(i["url"]) for i in its) and not all(tossy(i["url"]) for i in its):
        print("events list 토스 상품 뺌(다른 몰과 섞임)", ev["at"], sum(tossy(i["url"]) for i in its))
        its = [i for i in its if not tossy(i["url"])]
    ok = [i for i in its if not re.match(CP_PROD, i["url"])]
    wait = [i for i in its if re.match(CP_PROD, i["url"]) and HAS_CP and i["url"] not in x]  # 실패한 것(x) = 하루 뒤 다시 · 키 없음 = 못 바꿈
    if len(ok) < LIST_MIN or wait and ev["at"] > at(LIST_WAIT):
        if wait and ev["at"] > at(5 * 3600):
            return  # 아직 바뀌는 중(상한·오류면 다음 실행)
        seen[key] = now
        print("events list 안 올림", ev["at"], f"바뀐 상품 {len(ok)}개")
        tg("sendMessage", chat_id=ADMIN, text=f"⚠️ {ev['at']} 행사 목록 글 안 올림 — 쿠팡 링크로 바뀐 상품 {len(ok)}개({LIST_MIN}개 밑) · {clip(str(ev.get('title') or ''), 40)}\n"
                                              f"안 바뀐 상품: {', '.join(clip(str(i['name']), 20) for i in its if i not in ok)[:1500]}\n진우 단축 링크로 items를 바꿔 다시 예약해 줘")
        return
    md = re.match(r"(?:\d{4}-)?(\d{1,2})[-/.](\d{1,2})", str(ev.get("until") or ""))
    title, till = clip(str(ev.get("title") or "기획전").strip(), 60), f" (~{int(md[1])}/{int(md[2])})" if md else ""
    tail = lambda i: " · ".join(clip(t, 30) for t in (str(i.get("price") or "").strip(), str(i.get("unit") or "").strip()) if t)  # 한 줄이 글 1개를 넘지 않게
    name = lambda i, n: clip(str(i["name"]).strip(), n)
    num = lambda k: LIST_NUM[k] if k < len(LIST_NUM) else f"{k + 1}."
    end = lambda xs: f"\n\n{LIST_CHECK}" + (f"\n{toss_when()}" if TOSS_NO_CMP and any(toss_share(i["url"]) for i in xs) else "")  # 토스 = 게시 시점 가격
    notes = "\n".join(f"<i>{n}</i>" for n in aff_notes(i["url"] for i in ok).split("\n") if n)
    rows = [f'{num(k)} <a href="{esc(i["url"])}"><b>{esc(name(i, 40))}</b></a>' + (f" {esc(tail(i))}" if tail(i) else "") for k, i in enumerate(ok)]
    text = lambda rs, part: (notes + "\n\n" if notes else "") + f"🎉 <b>{esc(title)} · 핫딜픽이 고른 {len(ok)}개</b>{esc(till)}{part}\n\n" + "\n".join(rs) + end(ok)
    u16 = lambda h: len(plain_of(h).encode("utf-16-le")) // 2
    fit = lambda ks: len(ks) <= (90 - notes.count("<i>") - 1) // 2 and sum(len(ok[k]["url"]) for k in ks) <= 5000 and u16(text([rows[k] for k in ks], " (99/99)")) <= LIST_MAX  # 글자 수(태그 뺀) · 링크·굵게 90개(텔레그램 100개 넘으면 뒤 링크가 사라짐 — 10/11 모아보기)·주소 5,000자
    parts, cur = [], []  # 줄을 나눔 — 번호는 이어서
    for k in range(len(rows)):
        if cur and not fit(cur + [k]):
            parts.append(cur)
            cur = []
        cur.append(k)
    parts.append(cur)
    size = -(-len(rows) // len(parts))
    even = [list(range(j, min(j + size, len(rows)))) for j in range(0, len(rows), size)]
    parts = even if len(even) == len(parts) and all(map(fit, even)) else parts  # 고르게(마지막 글이 1~2줄만 남지 않게)
    mids = []
    for n, ks in enumerate(parts):
        m = tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True}, text=text([rows[k] for k in ks], f" ({n + 1}/{len(parts)})" if len(parts) > 1 else ""),
               reply_markup={"inline_keyboard": [[{"text": str(ev.get("button") or "") if not n and ev.get("button") else f"{num(ks[0])} {name(ok[ks[0]], 20)}", "url": ok[ks[0]]["url"]}]]})
        if not m:
            if n:  # 첫 글은 나갔음 = 다시 안 보냄(같은 목록 두 번 X) — 남은 쪽만 알림
                tg("sendMessage", chat_id=ADMIN, text=f"⚠️ {ev['at']} 행사 목록 글 {n + 1}/{len(parts)}쪽 전송 실패({RUN['tg_err'] or '텔레그램 오류'}) — 앞쪽만 올라감")
                break
            return  # 다음 실행에 다시(6시간 안)
        if not n:
            seen[key] = now
            bundled(seen)
        mids.append(m["message_id"])
        record("📋 " + m.get("text", ""), [{**e, "offset": e["offset"] + 3} for e in m.get("entities", [])], post_url(m["message_id"]), m["message_id"])  # '📋 ' = UTF-16 3칸 · url = 채널 글(상품 링크 X — 같은 링크 단독 글·👍 리스트 후보를 안 막게)
    print("events list", ev["at"], f"{len(ok)}개" + (f" · 글 {len(mids)}개" if len(parts) > 1 else "") + (f" · 안 바뀐 상품 {len(its) - len(ok)}개 뺌" if len(its) > len(ok) else ""))
    ts = [i for i in ok if aff_note(i["url"]) and len(i["url"]) <= 150]  # Threads = 수수료 링크만(10/19 밤 진우) · 긴 링크 X(500자)
    if not E.get("THREADS_TOKEN") or len(ts) < 2:
        return

    def th(n):
        return aff_notes(i["url"] for i in ts[:n]) + f"\n\n🎉 {title} · 핫딜픽이 고른 {len(ok)}개{till}\n\n" \
            + "\n".join(f"{num(j)} {name(i, 28)}" + (f"\n💰 {tail(i)}" if tail(i) else "") + f"\n👉 {i['url']}" for j, i in enumerate(ts[:n])) \
            + (f"\n\n전체 {len(ok)}개 → {post_url(mids[0])}" if len(ok) > n else "") + end(ts[:n])
    n = min(len(ts), 4)  # 상품 링크 4개 + 채널 글 1개 = Threads 5개 한도
    while n > 2 and len(th(n)) > 480:
        n -= 1
    if len(th(n)) > 480:
        print("threads list 500자 넘음 — Threads 생략", ev["at"])
        return
    try:
        th_bundle(seen, "list" + ev["at"][11:13], th(n), ts[0]["url"])
        print("th list", n, "items")
    except Exception as e:  # th_bundle이 다음 실행에 1번 더(th_retry) — 같은 실행의 다른 예약은 계속
        print("threads list", repr(e))


def night_deals(seen, since, until):
    """진우 예약 딜(events.json의 링크 있는 deal — 토스 API 이름 예약은 빼고, 사이트 표시·쿠팡 비교 금지 그대로) 중 since~until(KST 'YYYY-MM-DD HH:MM')에 나갈,
    아직 안 나간 것 -> [{"at", "icon", "name", "price", "sv", "url"}] 시각 순. sv = 같은 상품 쿠팡 비교('…보다 N원 쌈' 문장)일 때만 ('쿠팡', 'N원')."""
    out = []
    for ev in sorted(load(EVENTS, []), key=lambda e: e["at"]):
        if not (ev.get("url") and ev.get("deal") and not ev.get("api")) or "ev_" + ev["at"] in seen or not since <= ev["at"] < until:
            continue
        plain = html.unescape(re.sub(r"<[^>]+>", "", ev["text"]))
        store, name, price = parse(title_of(plain))  # 몰별 틀(10/22)도 '[몰] 상품명 (가격)'으로
        sv = re.search(rf"({SAVE_STORES})\s*같은 상품[^\n—]*?보다\s*([\d,]+원)\s*쌈", plain)  # '같은 상품'이라고 쓴 비교만(다른 상품·단위가격 참고는 X)
        gap = re.search(r"([\d,]+원)\s*차이", plain)
        weak = th_weak(plain) and (f"쿠팡과 {gap.group(1)} 차이" if gap else "특가로는 약함")  # 문구 또는 🛒 제목·몰별 머리 줄 끝 🛒(10/22)
        if TOSS_NO_CMP and is_toss(ev["url"]):  # 토스 딜 = 쿠팡 비교·차이 표시 X(10/12 토스 비즈니스 요청)
            sv, weak = None, weak and "특가로는 약함"
        out.append({"at": ev["at"], "icon": "👍" if th_steady(plain) and not weak else "🛒" if weak else "🔥", "name": clip(name, 26), "full": name, "price": price.split("/")[0].strip(),
                    "sv": sv and sv.groups(), "url": ev["url"], "weak": weak})
    return out


def night_window(now):
    """미리보기 범위: 지금(KST) ~ 다음 아침 8시."""
    kst = time.gmtime(now + 9 * 3600)
    return time.strftime("%Y-%m-%d %H:%M", kst), time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600 + (86400 if kst.tm_hour >= 8 else 0))) + " 08:00"


def night_line(d, link=True):
    """미리보기 한 줄: '22:20 🔥 메르헨트 폼클렌징 500ml 2개 11,900원 · 💡 쿠팡 같은 상품보다 6,000원 쌈'."""
    name = f'<a href="{esc(d["url"])}">{esc(d["name"])}</a>' if link else d["name"]
    return f"{d['at'][11:]} {d['icon']} {name} {d['price']}" + (f" · 💡 {d['sv'][0]} 같은 상품보다 {d['sv'][1]} 쌈" if d["sv"] else "") \
        + (f" · 🤔 {d['weak']}" if d.get("weak") else "")  # 약한 딜 솔직 메모(10/11 진우: 🛒는 리스트에만, 메모와 함께)


PV_HELLO = ("월요일 버티느라 고생 많았어요 🍵", "오늘 하루도 고생 많았어요 🍵", "한 주의 반, 잘 넘겼어요 🙌", "내일만 버티면 금요일이에요 💪",
            "드디어 금요일 밤이에요 🎉", "느긋한 토요일 밤 보내고 계세요? 🛋", "내일 출근 전, 장바구니 정리 어때요? 🧺")  # Threads 22시 미리보기 요일 인사(KST 월=0 — 10/25 23시 진우 '귀엽고 정겹게')
PV_REPLY = (f"🛍 오늘 밤 딜, 여기서 한 번에 볼 수 있어요\n앱 설치 없이 바로 👉 {urllib.parse.urlsplit(SITE).netloc}\n\n"
            "🔔 올라오자마자 알려드릴까요?\n텔레그램 👉 t.me/hotdeal_pick\n\n편안한 밤 보내세요 🌙")  # 미리보기 댓글(링크 카드 = 사이트 ?ref=th · 글자 주소는 ref 없이 · 대가성 문구·딜 줄 X)
PV_PROMPT = """Threads 밤 미리보기 줄('22:10 이름 · 16,900원')에 쓸 짧은 상품 이름을 만들어 주세요(names[i] = i번 상품, 개수 그대로).
- 휴대폰 한 줄에 들어가게 한글 13자 안팎(16자 넘지 않게).
- 판매처·스토어 이름 앞머리(예: '명대잡는날')·겹치는 용량·수식어는 빼고 품목·브랜드·핵심 구분(5년/15년·20봉·1kg처럼 비슷한 상품끼리 구분되는 것 하나)만.
- 원래 이름에 없는 말·숫자는 쓰지 않기, '…' 쓰지 않기."""


def pv_names(fulls):
    """Threads 미리보기 짧은 이름(10/25 Cowork — 휴대폰 390px에서 '시각 이름 · 가격' 한 줄): Claude 1번(한 번에) -> 16자↓ · 원래 이름에 있는 숫자만 · 낱말마다 원래 이름과 2글자↑ 겹침이
    아니거나 실패면 그 줄은 pv_name(PV_NAME자 낱말 단위)."""
    try:
        got = ai_json(PV_PROMPT + "\n\n" + "\n".join(f"{k}. {s}" for k, s in enumerate(fulls)), {"names": {"type": "array", "items": {"type": "string"}}}).get("names") or []
        got = got if len(got) == len(fulls) else []  # 수가 다르면 줄이 밀려 다른 상품 가격 옆에 붙음(10/25 리뷰) -> 전부 pv_name
    except Exception as e:
        print("preview 짧은 이름 없이", clip(repr(e), 100))
        got = []
    ok = lambda x, s: 0 < len(x) <= 16 and "…" not in x and set(re.findall(r"\d+", x)) <= set(re.findall(r"\d+", s)) and all(any(w[i:i + 2] in s for i in range(len(w) - 1)) for w in x.split() if len(w) >= 2)
    return [x if k < len(got) and ok(x := re.sub(r"\s+", " ", str(got[k])).strip(), s) else pv_name(s) for k, s in enumerate(fulls)]


def pv_name(s, n=PV_NAME):
    """Threads 미리보기 이름: n+3자까지는 그대로, 넘으면 n자 안에서 낱말 단위로 자름('…' X · 낱말 하나가 n자보다 길면 n자에서)."""
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) <= n + 3:
        return s
    cut = s[:n + 1].rsplit(" ", 1)[0].rstrip(" +,(·/-") if " " in s[:n + 1] else ""
    return cut or s[:n]


def preview(seen):
    """매일 밤 10시 '🌙 오늘 밤 특가 미리보기'(10/11 진우 '리스트 필요, 꾸준함이 중요' — 팔로워가 이 시간엔 리스트가 뜬다고 알게): 진우 예약 딜 중
    지금~다음 날 8시에 나갈 것(PREVIEW_MIN개 이상)을 시간표로 채널에 1번(시각·짧은 이름·링크·가격·같은 상품 쿠팡 차이, 대가성 문구 맨 앞) + Threads(10/25 23시 진우 '귀엽고 정겹게' ·
    '홈페이지 링크도 · 링크는 첫 댓글에'): 본문 = 대가성 문구(맨 위 1번) · 요일 인사 · 수수료 딜 전부 시각 순 '시각 짧은 이름 · 가격'(아이콘·🤔·💡 X, pv_names) · 500자 넘으면 뒷줄 대신 '🧺 그리고 N개 더…'
    · 링크 카드 X / 댓글 1개 = 사이트·텔레그램(PV_REPLY, 링크 카드 = 사이트 ?ref=th). 댓글 못 다는 토큰·본문 다시 올리기 = 끝 2줄을 사이트·텔레그램으로 바꾼 글 1개 + 링크 카드.
    개별 글은 예약대로 그대로 나감. 묶음 글이라 BUNDLE_GAP(토스 22시 회차보다 먼저 — main 순서), 23시 넘으면 안 올림(이미 나가기 시작), 적은 날은 21시 모아보기에(digest)."""
    now = time.time()
    kst = time.gmtime(now + 9 * 3600)
    key = time.strftime("preview_%Y%m%d", kst)
    if kst.tm_hour != PREVIEW_HOUR or key in seen or busy(seen, cap=False):  # 시간당 상한(HOUR_CAP)은 안 봄: 하루 1번이고 진우 예약(시간당 6개)이 몰린 밤엔 늘 걸려서 첫 글 뒤로 밀림
        return
    ds = night_deals(seen, *night_window(now))
    if len(ds) < PREVIEW_MIN:
        seen[key] = {"t": now, "n": len(ds)}  # 적은 날 = 21시 모아보기에 합침
        return
    notes = "\n".join(f"<i>{n}</i>" for n in dict.fromkeys(aff_note(d["url"]) for d in ds) if n)
    rows = [night_line(d) for d in ds[:20]]
    text = (notes + "\n\n" if notes else "") + f"🌙 <b>오늘 밤 특가 미리보기</b> ({kst.tm_mon}/{kst.tm_mday} · {len(ds)}개)\n시간이 되면 하나씩 채널에 올라와요 — 미리 찜해 두세요\n\n" \
        + "\n".join(rows) + (f"\n… 외 {len(ds) - len(rows)}개" if len(ds) > len(rows) else "") + "\n\n🔔 매일 밤 10시 미리보기 · 알림 켜두면 안 놓쳐요"
    m = tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True}, text=text)
    if not m:
        return  # 다음 실행에 다시(10시대 안에서)
    seen[key] = {"t": now, "n": len(ds), "mid": m["message_id"]}
    bundled(seen)
    tok = E.get("THREADS_TOKEN")
    if not tok:
        return
    ds = [d for d in ds if aff_note(d["url"])]  # 10/19 밤 진우 'Threads는 수수료 딜만'(채널 미리보기는 그대로)
    if not ds:
        print("threads skip (수수료 링크 아님) preview 묶음 | 항목 0개")
        return
    note = "\n".join(dict.fromkeys(aff_note(d["url"]) for d in ds))  # 대가성 문구 = 본문 맨 위 1번(프로그램마다 · 댓글엔 X)
    rows = [f"{d['at'][11:]} {nm}" + (f" · {d['price']}" if d["price"] else "") for d, nm in zip(ds, pv_names([d["full"] for d in ds]))]  # 시각 순(night_deals) · 브랜드 1개 규칙 X · 짧은 이름(pv_names)
    link, can = f"{SITE}?ref=th", TH_REPLY and th_reply_ok(seen)  # 댓글(reply_to_id)이 되는 토큰일 때만 '👇 댓글에'

    def body(reply):
        end = "\n\n⏰ 시간 맞춰 하나씩 쏙쏙 올려드릴게요\n👇 한눈에 보기·알림은 댓글에 있어요" if reply else f"\n\n🛍 한눈에 보기 {urllib.parse.urlsplit(SITE).netloc}\n🔔 텔레그램 알림 t.me/hotdeal_pick"
        for k in range(len(rows), 0, -1):  # Threads 500자(th_len — 이모지 = UTF-8 바이트): 넘치면 뒷줄을 빼고 '🧺 그리고 N개 더…' 1줄(댓글로 밀지 X)
            text = f"{note}\n\n{PV_HELLO[kst.tm_wday]}\n🌙 오늘 밤 딜 {len(ds)}개, 먼저 살짝 보여드려요\n\n" + "\n".join(rows[:k]) \
                + (f"\n🧺 그리고 {len(rows) - k}개 더 있어요, 시간 맞춰 올려드릴게요" if k < len(rows) else "") + end
            if th_len(text) <= 500:
                break
        return text
    try:
        r = th_bundle(seen, "preview", body(can), None if can else link)  # 댓글이 있으면 본문엔 링크 카드 X
    except Exception:
        if can:  # 다음 실행 재시도(th_retry)는 글 1개 -> 끝 2줄 = 사이트·텔레그램 + 링크 카드('👇 댓글에' X)
            seen[time.strftime("thretry_%Y%m%d_preview", kst)].update(text=body(False), link=link)
        raise
    if not can:
        return
    try:
        th_reply(tok, r["id"], PV_REPLY, link)
    except Exception as e:  # 본문은 이미 나감('👇 댓글에' — Threads 글은 못 고침) -> 관리자에게 바로(댓글 붙여넣기용) · 다음 날부터 3일은 글 1개 + 링크 카드(th_reply_ok 다시 확인 전)
        print("preview 댓글 실패", err_brief(e))
        seen["threply"] = {"t": time.time(), "ok": 0, "err": (getattr(e, "body", "") or repr(e))[:300]}
        tg("sendMessage", chat_id=ADMIN, text=f"⚠️ 22시 미리보기 댓글 실패({err_brief(e)}) — 본문은 나갔고 '👇 댓글에 있어요'가 남아 있어. "
           f"아래 글을 Threads 앱에서 그 글 댓글로 붙여넣어 줘(링크 {link})\n\n{PV_REPLY}")


def cp_events(seen, deals=()):
    """쿠팡 행사 자동 게시(10/9 진우 '로켓프레시데이 등 각종 데이 띄워줘' -> 공용 링크로 바로): 뉴시스 산업 RSS의 쿠팡 기사(2일 안, 뉴스룸은 GitHub 서버 차단)
    + 기사 없는 행사도(10/9 진우): 이번 실행에 읽은 뽐뿌·루리웹·클리앙 글 중 제목에 쿠팡·행사 낱말이 있는 글 -> Claude가 고객 할인 행사만
    골라 행사명·기간·혜택·검색어로 채널에 바로. 버튼 = 공용 파트너스 링크(쿠팡 홈, 프레시 행사는 로켓프레시 — API 승인 전엔 행사마다 링크를 못 만듦, 24시간 안 쿠팡 구매는 다 실적).
    관리자 사본에 행사 페이지 파트너스 링크를 답장하면 버튼 교체(딜 사본과 같은 흐름). posts.json(사이트·모아보기)엔 안 남김(딜 아님)."""
    since = time.time() - 2 * 86400  # seen은 3일 뒤 지워짐 -> 그보다 짧게(다시 올리지 않게)
    new = [(it.findtext("link", "").strip(), it.findtext("title", "").strip(), parsedate_to_datetime(it.findtext("pubDate")).timestamp(),
            " ".join(html.unescape(re.sub(r"<[^>]+>", " ", it.findtext("description", ""))).split()))
           for it in ET.fromstring(http(CP_NEWS)).iter("item")]
    new += [(d["url"], d["title"], time.time() - d["age"] * 60, d["desc"]) for d in deals if re.search(r"데이|기획전|페스타|세일|위크|행사|쿠폰|이벤트", d["title"])]
    posted = "\n".join(p["text"] for p in [q for q in load(POSTS, []) if not q.get("shelf")][-80:])  # 딜로 이미 올라간 글은 빼기
    new = [x for x in new if "쿠팡" in x[1] and x[2] > since and "cn_" + x[0] not in seen and x[1][:25] not in posted]
    if not new:
        return
    today = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600))
    picks = ai_pick(EVENT_PROMPT.format(today), [f"{t} | {time.strftime('%m/%d', time.gmtime(ts + 9 * 3600))} | {body[:1500]}" for _, t, ts, body in new])
    print("cp_events", [(p["score"], p.get("q")) for p in picks], "/", len(new))
    done = {x[0] for x in new} - {new[p["i"]][0] for p in picks if p["score"] >= 6 and p.get("q")}
    for p in picks:
        link = new[p["i"]][0]
        if link in done:
            continue
        m = tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True},
               text=f"<i>{DISCLOSURE}</i>\n\n{esc(p.get('e') or '🎉')} <b>쿠팡 {esc(p['q'])}</b>\n{esc(p.get('hook', ''))}\n\n"
                    + "".join(f"• {esc(x)}\n" for x in p.get("pts", [])[:3]) + f"\n👉 쿠팡 앱 검색창에 <b>{esc(p['q'])}</b>",
               reply_markup={"inline_keyboard": [[{"text": ("🚀 쿠팡" if "프레시" in p["q"] else CP_PLAIN[0]) + " 바로가기", "url": CP_FRESH if "프레시" in p["q"] else CP_HOME}]]})  # 로켓프레시 행사만 🚀, 그 밖 행사 = 📦(10/23)  # 쿠팡 버튼 = 🚀(10/22)
        if m:  # 실패하면 다음 실행에 다시
            done.add(link)
            seen.update({d["id"]: time.time() for d in deals if d["url"] == link})  # 커뮤니티 글이면 딜로 또 올리지 않게
            tg("copyMessage", chat_id=ADMIN, from_chat_id=CHANNEL, message_id=m["message_id"], reply_markup={"inline_keyboard": [
                [{"text": "📢 채널에 올라간 글", "url": post_url(m["message_id"])}], [{"text": "📰 보도자료", "url": link}],
                [{"text": "쿠팡 행사 · 행사 페이지 파트너스 링크 답장하면 버튼 교체(선택)", "callback_data": "-"}]]})
    seen.update({"cn_" + x: time.time() for x in done})


def threads_hint(e):
    """Threads 실패 알림의 조치 문구: Meta 개발자 계정 잠김('API access blocked', 10/6)과 토큰 만료를 구분."""
    if "blocked" in (getattr(e, "body", "") or ""):
        return "Meta가 개발자 계정을 잠갔어(API access blocked) → developers.facebook.com 접속해서 '계정 확인' 진행해줘. 끝나면 자동 재개"
    return "토큰 만료(60일)면 THREADS_TOKEN 시크릿 재발급해줘"


def toss_deals(seen, best=False):
    """토스 하루특가(API): 9시 이후 하루 1번, Claude가 고른 5개를 쉐어링크로 채널 + Threads에 바로. 편성 0건인 날은 다음 실행에 다시.
    best=True: 토스 베스트(지금 많이 팔리는 상품) 중 Claude가 '진짜 싼' 것만 최대 3개, TOSS_BEST_HOURS마다 1번. 3일 안에 올린 상품은 빼고, 없으면 안 올림.
    best="cat": 같은 방식으로 카테고리 베스트(TOSS_CATS 최상위 카테고리들 + 날마다 돌아가는 다른 최상위 카테고리 1개) 중 최대 3개, TOSS_CAT_HOUR에 1번.
    API 상품·가격은 채널·Threads 글로만 쓰고 posts.json(사이트·모아보기·블로그)엔 안 남김 — 승인 신청 내용(서비스 = 텔레그램 채널 + 스레드 자동 게시,
    커머스형 전시·가격 비교 안 함) 그대로."""
    kst, cat, beauty, special = time.gmtime(time.time() + 9 * 3600), best in ("cat", "beauty"), best == "beauty", best == "special"  # beauty = 뷰티 카테고리만 따로 1회차, special = 토스 특가(10/11)
    day = [h for h in TOSS_DAY_HOURS if h <= kst.tm_hour < h + 3]  # 하루특가는 회차 3시간 안에만(놓친 회차를 밤에 몰아 올리지 않게)
    hrs = [h for h in (TOSS_BEAUTY_HOURS if beauty else (TOSS_CAT_HOUR,) if cat else [h for h in TOSS_SPECIAL_HOURS if kst.tm_hour < h + 3] if special else TOSS_BEST_HOURS if best else day) if h <= kst.tm_hour]
    key = time.strftime("tossspecial_%Y%m%d_" if special else "tossbeauty_%Y%m%d_" if beauty else "tosscat_%Y%m%d_" if cat else "tossbest_%Y%m%d_" if best else "tossday_%Y%m%d", kst) + \
        (str(hrs[-1]) if best and hrs else f"_{hrs[-1]}" if hrs and hrs[-1] != TOSS_DAY_HOURS[0] else "")  # 9시 키는 예전 그대로
    if not HAS_TOSS or not hrs or key in seen:
        return
    if busy(seen, cap=not (best is True and "best" in TH_TOSS_KINDS and hrs[-1] in TH_LIST_HOURS)):  # 12·18시 Threads 베스트 리스트는 시간당 글 수에 안 막힘(10/12 진우 '묶음 글은 반드시') · 10분 안에 다른 묶음 글이 나갔거나 최근 1시간 글이 많음 -> 다음 실행(14분 뒤)에 다시(API도 안 부름)
        print("toss_special" if special else "toss_beauty" if beauty else "toss_cat" if cat else "toss_best" if best else "toss_deals", "미룸(묶음 글 간격·1시간 글 수)")
        return
    head = "💙 <b>토스 특가 중 살 만한 {}개</b>" if special else "💙 <b>토스에서 지금 많이 팔리는 것 중 살 만한 {}개</b>" if best else \
        "💙 <b>오늘의 토스 하루특가 TOP{}</b>\n<i>밤 12시까지 선착순 · 일부 고객에게만 보이고 수량 제한이 있을 수 있어요</i>"  # 10/10 진우 화면: 선착순특가 유의사항 · 10/22 진우 '토스 = 💙'(⏰·🏆·🔥 -> 💙)
    if cat:  # 카테고리 ID는 트리에서 이름으로 찾음(트리 조회는 일 상한 차감 없음)
        tree = toss("/categories")["categories"]
        cats = [c for c in tree if (re.search("뷰티|화장품", c["displayName"]) if beauty else c["displayName"] in TOSS_CATS)]  # 뷰티는 이름이 '뷰티'·'화장품/미용' 등이어도 찾게
        if not cats:
            raise RuntimeError(f"토스 카테고리 이름 확인: {[c['displayName'] for c in tree]}")
        others = [c for c in tree if c["displayName"] not in TOSS_CATS]  # 10/8 진우 '더 넓게': 다른 최상위 카테고리를 날마다 1개씩 돌아가며
        cats += [others[kst.tm_yday % len(others)]] if others and not beauty else []
        head = "💙 <b>토스 " + "·".join(c["displayName"] for c in cats) + " 베스트 중 살 만한 {}개</b>"  # 17시 생필품 목록(10/22 진우 💙 머리 — 예전 🧺·💄)
        raw = [{**x, "_src": f"{'뷰티' if beauty else '생필품' if c['displayName'] in TOSS_CATS else c['displayName']} 베스트 {r + 1}위"}
               for c in cats for r, x in enumerate(toss(f"/products/best-categories/{c['categoryId']}?size=30")["items"])]  # _src = Threads 개별 글 머리 줄 출처
    elif special:  # API엔 '특가' 탭·개당 수익·30일 최저가가 없음(10/11 문서 확인) -> 1일 목록(하루특가·베스트·카테고리 베스트) 중 할인 SPECIAL_DR%↑·리뷰 SPECIAL_RC개↑,
        cand = [x for x in toss_pool(seen) if len(x) > 6 and (x[4] or 0) >= SPECIAL_DR and (x[6] or 0) >= SPECIAL_RC and f"tb_{x[0]}" not in seen and toss_ok(seen, x[0])]  # 할인율 높은 순 30개를 상세로 지금 가격·품절 다시 확인
        ids = [x[0] for x in sorted(cand, key=lambda x: -x[4])[:30]]
        raw = [x for x in (toss("/products/detail?tacaItemIds=" + ",".join(map(str, ids)))["items"] if ids else [])
               if (x.get("discountRate") or 0) >= SPECIAL_DR and (x.get("reviewCount") or 0) >= SPECIAL_RC]  # 지금 값으로 다시 거름(1일 된 목록의 끝난 하루특가 할인 X)
    else:
        raw = [{**x, "_src": f"많이 팔린 순위 {r + 1}위" if best else "하루특가 · 밤 12시까지"} for r, x in enumerate(toss(f"/products/{'best-selling' if best else 'today-deals'}?size=30")["items"])]
    evs, ti = load(EVENTS, []), seen.get("tossid", {}).get("m", {})
    booked = {re.sub(r"\W", "", e["name"]) for e in evs if e.get("name") and e["at"][:10] == time.strftime("%Y-%m-%d", kst)}  # 진우 링크로 오늘 예약한 토스 상품은 자동 글에서 뺌(같은 상품 두 번 방지, 10/11)
    booked_id = {x for e in evs if e.get("url") in ti and e["at"][:10] == time.strftime("%Y-%m-%d", kst) for x in (("g", ti[e["url"]][0]), ti[e["url"]][7] if len(ti[e["url"]]) > 7 else 0) if x and x != ("g", 0)}  # 같은 상품 = 토스 id 기준도(10/23 진우 — 옵션 id·상품 그룹 id)
    picked = {v.get("id") for k, v in seen.items() if k.startswith("pk_" + time.strftime("%Y-%m-%d", kst)) and isinstance(v, dict)}  # 오늘 이름 예약(toss_picks)으로 찾은 상품도(이름이 달라도 id로)
    eve = not (best or special) and hrs[-1] == TOSS_DAY_EVE  # S 저녁 회차 = '1번 더': 오늘 올린 하루특가도 다시(판매 중 TOP5 — 진우 예약·이름 예약 상품은 그대로 뺌)
    items = list({x["tacaItemId"]: x for x in raw if not x.get("isSoldOut") and (eve or f"tb_{x['tacaItemId']}" not in seen) and toss_ok(seen, x["tacaItemId"])
                  and re.sub(r"\W", "", x["displayName"]) not in booked and x["tacaItemId"] not in picked | booked_id and ("g", x.get("tacaId")) not in booked_id}.values())  # 카테고리 겹친 상품은 1번만 · 토스 점검 땐 보관 링크 있는 것만
    tone, tsuf = tone_ask(seen, "ch") if items else (0, "")
    picks = items and ai_pick((SPECIAL_PROMPT if special else BEST_PROMPT if best else GOLD_PROMPT.replace("쿠팡 골드박스", "토스쇼핑 하루특가") + TOSS_EASE + TOSS_WU) + tsuf,
                              [f"{x['displayName']} | {x['displayPrice']:,}원 ({x.get('discountRate', 0)}% 할인)"
                               + (f" | 리뷰 {x.get('reviewScore')}점 {x['reviewCount']:,}개" if x.get("reviewCount") else "") for x in items])
    picks = picks and sorted(({**p, "score": p["score"] + toss_freq(items[p["i"]])} for p in picks), key=lambda p: -p["score"])[:5 if special or not best else 3]  # S: 자주 사는 상품 +1 뒤 순위
    today = time.strftime("%Y-%m-%d", kst)
    night = {v[0] for v in (toss_daymap(seen, time.time(), today, seen.get("soldmap", {}).get("d") != today) or {}).get("m", {}).values()} if special and picks else set()  # 특가 중 오늘 하루특가 = 품절 땐 '밤 12시 재오픈'(오늘 목록이 없으면 1번 받음)
    if special and picks:  # 진우 '개당 수익 × Claude 점수': 개당 수익 = 가격 × 수수료(10/1~ 일괄 8%, TOSS_FEE_DAY~ 기본 5%·오늘 하루특가 = 선착순특가 3%) -> 7점↑ 중 점수 × 개당 수익 높은 순 3개
        fee = lambda x: (0.03 if x["tacaItemId"] in night else 0.05) if today >= TOSS_FEE_DAY else 0.08
        picks = sorted((p for p in picks if p["score"] >= 7), key=lambda p: -p["score"] * items[p["i"]]["displayPrice"] * fee(items[p["i"]]))[:3]
    rows, plain, got, gp = [], [], [], []  # gp = 올린 상품의 픽(개별 글 💰·🙋·👍)
    for p in picks or []:
        x = items[p["i"]]
        try:
            link = toss_link(seen, x["tacaItemId"], x["displayName"])
        except Exception as e:  # 발급 제한 상품은 빼고 나머지만
            print("toss link", repr(e))
            continue
        if not link:  # 토스 점검인데 보관 링크 없음(위에서 걸러서 거의 없음)
            continue
        seen[f"tb_{x['tacaItemId']}"] = {"t": time.time(), "n": x["displayName"]}  # 올린 상품은 3일(seen 보관 기간) 안엔 베스트에 다시 안 올림 (베스트는 며칠씩 그대로, 하루특가와도 겹침). 이름 = 커뮤니티 딜 판단 때 '이미 올린 딜'로
        got.append(x)
        gp.append(p)
        plain.append(f"{NUM[len(plain)]} {clip(x['displayName'], 24)} — {x['displayPrice']:,}원" + (f" ({u})" if (u := toss_unit(x["displayName"], x["displayPrice"])) else "") + (" (하루특가·밤 12시까지)" if x["tacaItemId"] in night else "") + f"\n{link}")
        rows.append((x["displayName"], link, (["⏰ 토스 하루특가 · 밤 12시까지"] if x["tacaItemId"] in night else []) + [f"💰 <b>{x['displayPrice']:,}원</b>" + (f" ({x['discountRate']}%↓)" if x.get("discountRate") else "")
                                             + (f" · ⭐ {x['reviewScore']} (리뷰 {x['reviewCount']:,})" if x.get("reviewCount") else "")] + toss_ul(x) + ["👉 " + esc(p["comment"])]))
    print("toss_special" if special else "toss_beauty" if beauty else "toss_cat" if cat else "toss_best" if best else "toss_deals", len(items), "items", len(picks or []), "picks", len(rows), "links")  # 0건이어도 로그로 확인
    if raw or special:  # 목록을 받았으면(Claude까지 돌렸으면, 특가는 후보 0개여도) 이번 회차는 끝(발급이 다 막혀도 15분마다 다시 고르지 않게). Threads가 실패해도 채널에 두 번 안 올라가게 먼저 표시
        seen[key] = time.time()
    if rows:
        text, kb = top_post(head.format(len(rows)), rows)
        m = tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True},
               text=f"<i>{TOSS_NOTE}</i>\n\n{text}" + (tail := f"\n\n{toss_when()}" if TOSS_NO_CMP else ""), reply_markup={"inline_keyboard": kb})
        if m:
            bundled(seen)
            tone_keep(seen, "ch", tone)
        if m:  # 품절 지켜보기(toss_soldout): 글을 다시 그릴 재료 + 상품별 [id, 이름, 올린 가격, 하루특가?, 상태, 마지막 확인]
            seen[f"sold_{m['message_id']}"] = {"t": time.time(), "d": time.strftime("%Y-%m-%d", kst), "k": "top", "pre": f"<i>{TOSS_NOTE}</i>\n\n", "tail": tail,  # tail = 게시 시점 가격 줄(품절 고칠 때 빠지던 것)
                                               "head": head.format(len(rows)), "rows": rows, "it": [[x["tacaItemId"], x["displayName"], x["displayPrice"], int(not best or x["tacaItemId"] in night), 0, 0] for x in got]}
    tok = E.get("THREADS_TOKEN")
    kind = "special" if special else "beauty" if beauty else "cat" if cat else "best" if best else "day"
    lst = kind in TH_TOSS_KINDS and (hrs[-1] in TH_LIST_HOURS or kind == "cat") or kind == "day" and hrs[-1] == TOSS_DAY_EVE  # 이 회차가 Threads 리스트로도 나가는지(S: 저녁 하루특가 TOP5도)
    if rows and tok and kind in TH_TOSS_FILL and not eve:  # 10/12 22:45·22:50 진우 '토스 인기 생필품·많이 팔리는 제품 꾸준하게': 이 회차 픽을 Threads 개별 글 채움 후보로(45분 칸이 비었을 때 토스 픽 먼저, 3시간 안)
        seen["thtoss"] = {"t": time.time(), "q": [x for x in seen.get("thtoss", {}).get("q", []) if time.time() - x["t"] < 3 * 3600] + [  # 사이트·posts.json X, 쉐어링크 그대로
            {"t": time.time(), "l": lst, "id": x["tacaItemId"], "n": x["displayName"], "k": kind, "r": n, "s": next((p.get("score", 0) for p in picks if items[p["i"]] is x), 0), "bt": th_beauty(x["displayName"]),
             "text": toss_th("하루특가 · 밤 12시까지" if x["tacaItemId"] in night else x.get("_src", ""), name, toss_price(x), toss_ul(x) + toss_lines(gp[n]), link), "link": link} for n, (x, (name, link, lines)) in enumerate(zip(got, rows))]}
    if rows and tok and lst:  # Threads는 12·15·18시 베스트 리스트 + 17시 생필품(식품·생활용품) 리스트(10/12 22:45 진우)만(10/11 진우 '나누지 말고 묶기' — 나머지 회차는 채널에만). 500자 -> 넘치면 뒤 상품부터 뺌, 대가성 문구 맨 앞
        while len(plain) > 1 and len(TOSS_NOTE) + len(head) + len("\n\n".join(plain)) > 480:
            plain.pop()
        text = f"{TOSS_NOTE}\n\n{re.sub('<.*?>', '', head).format(len(plain))}\n\n" + "\n\n".join(plain) + (f"\n\n{toss_when()}" if TOSS_NO_CMP else "")
        th_bundle(seen, f"toss{hrs[-1]}", text[:500])
    elif rows and tok and beauty and th_day(seen, time.time())["b"] < TH_BEAUTY_MIN and not jw_beauty(seen, time.time()):  # 오늘 화장품 자리가 비었고 진우 화장품 링크가 더 없으면
        k = next((n for n, x in enumerate(got) if th_beauty(x["displayName"]) == 2), 0)  # 이 회차 1개를 Threads 개별 글로(소모품 먼저, 없으면 Claude 1순위) — 10/11 23:50 진우
        bt, (name, link, lines) = max(1, th_beauty(got[k]["displayName"])), rows[k]
        text = toss_th(got[k].get("_src", ""), name, toss_price(got[k]), toss_ul(got[k]) + toss_lines(gp[k]), link)
        if TH_SLOTS:  # 슬롯 방식: 줄에(15시 슬롯·20시 슬롯에 1순위로 골리면 나감)
            th_queue(seen, text, link, bt)
        elif th_solo(seen, plain_of(text), beauty=bt, slot=True):
            th_mark(seen, bt)
            me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
            th_deal(seen, tok, me, text, link)


TOSS_FREQ, TOSS_FREQ_BONUS, TOSS_DAY_EVE = (r"골지|민소매|기본\s*티|양말|레깅스|(?<!실)내의(?!류)|들기름|참기름|양념(?!통|병|용기|함|그릇)"  # S(10/26 진우 '토스 더 자주 사게'): 여성 기본템·식재료 소모품 이름 + 묶음(단가 줄) = Claude 점수 +1
                                             r"|(?:조미|재래|곱창|파래|돌|도시락|구운|광천|김밥용|전장|감태)\s*김|(?<![가-힣])김(?![가-힣])"), 1, 20  # 김 = 김 낱말·김 이름만(튀김·김서림·김냉·김정문 X) · 하루특가 TOP5 저녁 회차(채널 + Threads 리스트)
TOSS_IN, TOSS_OUT = r"개입|개|롤|매|입|켤레|족|포|장|병|캔|봉", r"팩|박스|세트|판"  # 낱개 이름 · 겉 묶음(곱함)


def toss_unit(name, price):
    """S 묶음 단가(우리 계산 = 이름의 개수 × 가격만, 헷갈리면 X — 틀린 단가보다 없는 게 나음):
    '(총 N개)' 있으면 그 수 · 아니면 낱개 수 1개 × 겉 묶음 수(팩·박스·세트·판) 1개 × 'x N' · '1+1'·'2+1+1' = 합 · '30구'는 계란만.
    -> '1개당 295원꼴'(10원 밑이면 10·100개당) / 1개·옵션(택1·옵션·골라·'중 N'·'/'·'~'·같은 낱개 이름 두 번)·다른 상품 더하기('A + B')·모델명 '+'(S24+)·못 읽음 = ''."""
    nm = re.sub(r"\+\s*[^+\d]*증정", "", name)  # '+ 선크림 증정'(덤) = 셈 X
    if not price or re.search(r"택\s*1|택일|옵션|골라|중\s*\d|\d\s*[a-zA-Z가-힣]*\s*[/~]\s*\d", nm):
        return ""
    tot = re.search(rf"총\s*(\d+)\s*({TOSS_IN}|구)(?![가-힣])", nm)
    if tot:
        n, u = int(tot[1]), tot[2]
    else:
        pl = r"(?<![\w.])\d+(?:\s*\+\s*\d+)+(?![\w.+])"  # 1+1 · 2+1+1(모델명 S24+ 256GB X)
        plus, rest = re.findall(pl, nm), re.sub(pl, " ", nm)
        if "+" in rest:  # 다른 상품 더하기·모델명 '+' = 헷갈림
            return ""
        egg = re.search(r"계란|달걀|유정란|특란|왕란|대란", nm)
        ins = re.findall(rf"(\d+)\s*({TOSS_IN}{'|구' if egg else ''})(?![가-힣])", rest)
        outs = re.findall(rf"(\d+)\s*({TOSS_OUT})(?![가-힣])", rest)
        xs = re.findall(rf"(?<![\dA-Za-z])[x×X]\s*(\d+)(?![\d.]|\s*(?:(?![x×X]\s*\d)[A-Za-z]|{TOSS_IN}|{TOSS_OUT}|구))", rest)  # 'x 5'(낱말 없는 곱) — '1920x1080'·'x 4봉' X
        if len(ins) > 1 or len(outs) > 1 or len(xs) > 1 or plus and (ins or outs or xs) or len(plus) > 1:
            return ""
        n = math.prod([int(k) for k, _ in ins + outs] + [int(k) for k in xs] + [sum(map(int, re.findall(r"\d+", p))) for p in plus])
        u = ins[0][1] if ins else outs[0][1] if outs else "개"  # 낱개 이름 없이 '3박스'만 = 1박스당
    u = "개" if u in ("개입", "입") else u
    if n < 2:
        return ""
    base = next(b for b in (1, 10, 100, 1000) if price * b / n >= 10 or b == 1000)
    return f"{base}{u}당 {round(price * base / n):,}원꼴"


def toss_freq(x):
    """S 가산 대상: 이름에 여성 기본템·식재료 소모품 낱말 또는 묶음 단가가 나오는 상품(그 글엔 💰 단가 줄이 붙음) -> +TOSS_FREQ_BONUS, 아니면 0."""
    return TOSS_FREQ_BONUS if re.search(TOSS_FREQ, x["displayName"]) or toss_unit(x["displayName"], x["displayPrice"]) else 0


def toss_ul(x):
    """토스 글 💰 단가 줄(S — 묶음이면) -> [줄] 또는 []."""
    u = toss_unit(x["displayName"], x["displayPrice"])
    return [f"💰 {u}"] if u else []


def toss_th(src, name, price, lines, link, icon="🔥"):
    """토스 API 상품 Threads 개별 글(매시 개별·뷰티 회차 채움·토스 픽 채움·이름 예약): 대가성 문구 → 머리 줄 '💙 토스 특가 · 출처 🔥'(채널 글과 같게, 10/22 진우 '한눈에')
    → 상품명 → 가격 줄 → 줄들(🙋·👍, 일반 글자) → 게시 시점 가격 → 쉐어링크(API 상품 = 사이트·쿠팡 비교 X). 480자 넘으면 👍 → 🙋 줄 순서로 뺌(10/20 진우 — 머리·가격·대가성 문구·게시 시점·링크는 그대로)."""
    for drop in ("", "👍", "🙋"):
        lines = [l for l in lines if not (drop and l.startswith(drop))]
        text = th_note(TOSS_NOTE) + f"{mall_head('toss', src, icon)}\n{clip(name, 60)}\n{price}" + "".join("\n" + clip(l, 120) for l in lines) \
            + (f"\n{toss_when()}" if TOSS_NO_CMP else "") + f"\n\n🛒 {link}\n📲 실시간 알림 t.me/hotdeal_pick"
        if len(text) <= 480:
            break
    return text


def toss_price(x):
    """토스 API 상품 가격 줄(몰별 틀 셋째 줄): '15,580원 (60%↓) · ⭐ 4.7 (11,683)'."""
    return f"{x['displayPrice']:,}원" + (f" ({x['discountRate']}%↓)" if x.get("discountRate") else "") + (f" · ⭐ {x['reviewScore']} ({x['reviewCount']:,})" if x.get("reviewCount") else "")


def toss_lines(p):
    """토스 API 개별 글 가격 줄 아래: 🙋 누가·👍 언제(a7cee6f 틀 그대로 — wu), 둘 다 없으면 Claude 한 줄(👉, 다른 몰·금지어 든 건 X)."""
    c = re.sub(r"\s+", " ", (p or {}).get("comment") or "").strip()
    return wu(p) or ([f"👉 {c}"] if c and not re.search(f"{WU_BAN}|{TOSS_BAN}", c) else [])


WU_FAKE = r"(?<![가-힣])제가|(?:써|먹어|발라|마셔|사용해|입어|신어)\s*(?:보니|봤|봄|본)"  # 써 본 척
WU_HEALTH = r"다이어트|혈당|면역|피로|건강|효능|효과|개선|미백|주름|탄력|(?:피부|모발|두피)\s*재생|재생\s*(?:크림|효과|케어)|치료|탈모|여드름|트러블|아토피|숙면|관절|변비|혈압"  # 효능·건강·의학
WU_CMP = r"보다\s*(?:싸|저렴|비싸)|반값|코스트코|홈플러스|트레이더스"  # 다른 몰·비교(+ OTHER_STORES)
WU_HYPE = r"역대급|무조건|손해|마지막\s*기회|클릭|눌러\s*(?:보|주)"  # 과장·조급·클릭 유도
WU_BAN = "|".join((WU_FAKE, WU_HEALTH, WU_CMP, WU_HYPE))
TOSS_BAN = rf"{WU_CMP}|{OTHER_STORES}|{CMP_WORDS}|비교|비쌈|(?:온라인|인터넷|국내|업계|시중)\s*최저|시중|타\s*(?:몰|사이트|쇼핑몰)|다른\s*(?:데|곳|몰|쇼핑몰|사이트)|(?:가장|제일|젤)\s*(?:싸|싼|쌌|쌈|저렴|낮)"  # 토스 글 = 다른 몰·가격 비교 말 X(th_voice·Claude 한 줄)


def wu(p):
    """토스 쉐어링크 개별 글 🙋 누가·👍 언제 줄(10/20 진우 '사고 싶게'): 써 본 척·효능·다른 몰·과장·클릭 유도 말이 있거나 너무 길면(🙋 40·👍 50자 넘음) 그 줄만 뺌."""
    return [f"{e} {t}" for e, k, n in (("🙋", "who", 40), ("👍", "use", 50)) for t in [re.sub(r"^\W+", "", (p or {}).get(k) or "").strip()]
            if t and len(t) <= n and not re.search(f"{WU_BAN}|{OTHER_STORES}", t)]


def top_post(head, items):
    """번호 목록 글 모양(10/9 진우 '시안성 좋고 사고 싶게'): 번호·굵은 이름(링크) + 줄들(💰가격·👉이유 등, HTML 이스케이프된 것) + 번호 버튼.
    items = [(이름, 링크, [줄])] -> (본문, 버튼 줄들). 토스 하루특가·베스트·카테고리와 TOP5 묶음이 같이 씀."""
    text = head + "\n\n" + "\n\n".join(f"{NUM[n]} <a href=\"{esc(link)}\"><b>{esc(name)}</b></a>" + "".join("\n" + l for l in lines if l)
                                        for n, (name, link, lines) in enumerate(items))
    return text, [[{"text": f"{NUM[n]} {clip(name, 20)}", "url": link}] for n, (name, link, _) in enumerate(items)]


TOP_SUB, TOP_SUB_TOSS = "쿠팡보다 싼 딜·30일 최저가 먼저", "30일 최저가·순위 먼저"
STEADY_AT, STEADY_END, STEADY_DAYS, STEADY_N, STEADY_MIN_BUY, STEADY_FILE = "19:50", "21:00", 14, 5, 1000, "docs/steady.json"  # 10/22 진우 '꾸준템 리스트도': 하루 1번 19:50(KST, 늦어도 21시 전) · 후보 14일 · 5개 · 🛒는 한 달 1,000명+ 구매만 · 사이트 페이지 재료


STEADY_CAT_EVERY, STEADY_CAT_MIN = 3, 3  # 10/24 진우 '가끔 품목 하나로 묶어(💄 화장품 스테디셀러 모음)': 사흘에 1번(1년 중 날짜 % 3 == 0), 한 품목 후보 3개+일 때만


def steady_cands(seen, now, n=None):
    """👍 꾸준템 리스트 후보(수수료 링크만, 같은 링크·이름 1번, 최대 STEADY_N): ① 최근 STEADY_DAYS일 진우 👍 글(최근 것부터)
    → ② 잘 된 상품 표(top.json 순서 — 토스 = 상세 API로만 지금 가격·리뷰·품절(id = 표 키·우리 쉐어링크·1일 목록 이름, 못 찾으면 뺌), 그 밖 = 같은 링크 최근 채널 글의 가격·숫자)
    → ③ 진우 🛒 중 한 달 STEADY_MIN_BUY명+ 구매(많은 순). 채널 글에서 가져온 가격이 오늘 글이 아니면 '(M/D 글 가격)'(리스트 게시 시점 줄과 안 맞게 X).
    -> [{"n": 이름, "p": 가격, "st": '한 달 N명+ 구매'·'리뷰 N'·'', "u": 채널 링크, "tu": Threads 링크, "i": posts 번호(없으면 None)}]
    shortcut: 쿠팡 판매 중 확인은 못 함(쿠팡 API 승인 전) — 토스만 API로 품절 거름(토스 채널 글은 후보 X — 품절 기록이 그날만 남아서)."""
    posts, kst = load(POSTS, []), time.gmtime(now + 9 * 3600)
    today, since = time.strftime("%Y-%m-%d", kst), time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 9 * 3600 - STEADY_DAYS * 86400))
    tossy, sp, norm = lambda u: urllib.parse.urlsplit(u or "").netloc in TOSS_HOSTS, lambda x: re.sub(r"\s", "", x), lambda x: re.sub(r"\W", "", str(x or "").lower())
    def item(i):
        p = posts[i]
        _, name, price = parse(title_of(p["text"]))
        b, r, pr = re.search(STEADY_BUY, p["text"]), re.search(STEADY_REV, p["text"]), price.split("/")[0].strip()
        return {"n": name, "p": p.get("shelf") and p.get("now") and p["now"] + (f" ({p['chk']} 확인)" if p.get("chk") else "") or pr and pr + ("" if p["t"][:10] == today else f" ({int(p['t'][5:7])}/{int(p['t'][8:10])} 글 가격)"),  # 진열 글 = 지금 확인 가격
                "st": f"한 달 {sp(b[1])}명+ 구매" if b else f"리뷰 {sp(r[1])}" if r else "", "u": p["url"], "tu": th_url(p, i), "i": i}
    own = [i for i in range(len(posts) - 1, -1, -1) if posts[i].get("own") and (posts[i]["t"] >= since and not posts[i].get("shelf") or posts[i].get("shelf") and posts[i].get("st") not in ("gone", "out") and th_steady(posts[i]["text"]))
           and aff_note(posts[i].get("url") or "") and not tossy(posts[i].get("url"))]  # 사이트 진열(shelf)은 👍만, 날짜 상관없이(진열에서 빠진 것·일시 품절 X — 10/24 진우)
    out = [item(i) for i in own if th_steady(posts[i]["text"])]
    tops = [x for x in load(TOP, {}).get("items", []) if aff_note(x.get("url") or "")]
    tu, tc = toss_ids(seen), {norm(c[1]): c[0] for c in seen.get("tosscache", {}).get("items", []) if len(c) > 1}
    ti = seen.get("tossid", {}).get("m", {})  # 진우 쉐어링크 -> 대표 옵션 id(own_end가 tacaIds로 확인한 것 — 주소 /t/번호는 그룹 id라 여기 X)
    tid = lambda x: int(k[5:]) if (k := str(x.get("key", ""))).startswith("toss:") else tu.get(x["url"]) or (len(ti.get(x["url"], [])) > 7 and ti[x["url"]][7]) \
        or tc.get(norm(k[6:] if k.startswith("tname:") else x.get("name")))  # 전부 옵션 id(tacaItemId): 우리 링크(toss_link)·진우 링크(tossid)·1일 목록 이름
    ids = list(dict.fromkeys(tid(x) for x in tops if tossy(x["url"]) and tid(x)))[:30]
    try:
        det = {d["tacaItemId"]: d for d in (toss("/products/detail?tacaItemIds=" + ",".join(map(str, ids)))["items"] if ids and HAS_TOSS else [])}
    except Exception as e:  # 터널 끊김 등 = 토스 표 상품만 빼고 리스트는 그대로
        print("steady toss detail", repr(e))
        det = {}
    for x in tops:
        if tossy(x["url"]):
            d = det.get(tid(x))
            if d and not d.get("isSoldOut"):
                out.append({"n": x.get("name") or d["displayName"], "p": f"{d['displayPrice']:,}원", "st": f"리뷰 {d['reviewCount']:,}" if d.get("reviewCount") else "", "u": x["url"], "tu": x["url"], "i": None})
        elif (i := next((i for i in range(len(posts) - 1, -1, -1) if posts[i].get("url") == x["url"]), None)) is not None:
            out.append(item(i))
    buys = lambda i: next((steady_n(b[1]) for b in [re.search(STEADY_BUY, posts[i]["text"])] if b), 0)
    out += [item(i) for i in sorted((i for i in own if th_weak(posts[i]["text"]) and buys(i) >= STEADY_MIN_BUY), key=lambda i: -buys(i))]
    keep, us, ns = [], set(), set()
    for x in out:
        if x["p"] and x["u"] not in us and norm(x["n"]) not in ns:
            keep.append(x)
            us.add(x["u"])
            ns.add(norm(x["n"]))
    return keep[:n or STEADY_N]


def steady_list(seen):
    """하루 1번 STEADY_AT~STEADY_END(KST): 채널·Threads 목록 글 '👍 꾸준히 팔리는 것 모음'(steady_cands, 상품마다 가격 · 한 달 N명+ 또는 리뷰 N · 링크) —
    대가성 문구 맨 앞(링크마다 그 프로그램) · 게시 시점 줄 · 다른 묶음 글 10분 안이면 다음 실행 · 후보 0개면 그 회차 생략. 사이트 꾸준템 페이지 재료(STEADY_FILE)도 씀."""
    now = time.time()
    kst = time.gmtime(now + 9 * 3600)
    key = time.strftime("steady_%Y%m%d", kst)
    if not STEADY_AT <= time.strftime("%H:%M", kst) < STEADY_END or key in seen or busy(seen, cap=False):
        return
    seen[key] = now
    items, posts, names = steady_cands(seen, now, 99), load(POSTS, []), {k: n.split("·")[0] for k, n, _ in SHELF_CATS}
    cats = {}
    for x in items:
        if x["i"] is not None and (c := cat_of(posts[x["i"]])):
            cats.setdefault(c, []).append(x)
    cat = kst.tm_yday % STEADY_CAT_EVERY == 0 and max((c for c in cats if len(cats[c]) >= STEADY_CAT_MIN), key=lambda c: len(cats[c]), default=None)  # 가끔 한 품목 모음
    items = cats[cat][:STEADY_N] if cat else items[:STEADY_N]
    if not items:
        print("steady 후보 0개 — 이번 회차 생략")
        return
    head = "{} <b>{} 스테디셀러 모음</b>".format(*names[cat].split(" ", 1)) if cat else "👍 <b>꾸준히 팔리는 것 모음</b>"
    notes = list(dict.fromkeys(aff_note(x["u"]) for x in items))
    text, kb = top_post(head + "\n최저가는 아니어도 꾸준히 많이 사는 것", [(x["n"], x["u"], [f"💰 <b>{esc(x['p'])}</b>" + (f" · {esc(x['st'])}" if x["st"] else "")]) for x in items])
    if not tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True},
              text="\n".join(f"<i>{n}</i>" for n in notes) + f"\n\n{text}\n\n{toss_when()}", reply_markup={"inline_keyboard": kb}):
        return
    bundled(seen)
    print("steady", len(items), "items" + (f" ({cat} 모음)" if cat else ""), "|", " / ".join(clip(x["n"], 20) for x in items))
    os.makedirs(os.path.dirname(STEADY_FILE), exist_ok=True)
    api = lambda x: x["i"] is None and urllib.parse.urlsplit(x["u"]).netloc in TOSS_HOSTS  # 토스 상세 API로 가격·리뷰를 받은 상품 = 사이트엔 가격·리뷰 X(API 신청 범위 — 10/23 Cowork 정정)
    json.dump({"at": time.strftime("%Y-%m-%d %H:%M", kst), "head": plain_of(head), "notes": notes, "items": [{**x, "p": "", "st": ""} if api(x) else x for x in items]}, open(STEADY_FILE, "w"), ensure_ascii=False)
    if not E.get("THREADS_TOKEN"):
        return
    render = lambda n: "\n".join(dict.fromkeys(aff_note(x["u"]) for x in items[:n])) + f"\n\n{plain_of(head)}\n\n" \
        + "\n".join(f"{NUM[k]} {clip(x['n'], 30)} {x['p']}" + (f" · {x['st']}" if x["st"] else "") + f"\n👉 {x['tu']}" for k, x in enumerate(items[:n])) + f"\n\n{toss_when()}" \
        + f"\n전체 보기 → {SITE}c/{CAT_META[cat][0] if cat else 'steady'}/?ref=th"  # N2(10/24 진우): 묶음 글 끝 = 사이트 그 품목 쪽(20개씩) — Threads 글 링크 5개 한도라 상품 링크는 4개까지
    n = min(len(items), 4)
    while n > 1 and len(render(n)) > 480:
        n -= 1
    th_bundle(seen, "steady", render(n), items[0]["tu"])


def top_deals(seen):
    """12·18시: 그 시간대(0~12시·12~18시)에 채널에 올린 커뮤니티 딜 중 반응(분당 조회수 + 추천×5, 게시 때 뽐뿌·클리앙 수치) 높은 TOP5를 한 글로.
    3개 미만이면 안 올림. 조회수 기준이라 '많이 보는' 딜(구매 수는 모름). 링크마다 그 제휴 프로그램 대가성 문구를 맨 앞에."""
    kst = time.gmtime(time.time() + 9 * 3600)
    hrs = [h for h in TOP_HOURS if h <= kst.tm_hour]
    key = time.strftime("top_%Y%m%d_", kst) + (str(hrs[-1]) if hrs else "")
    if not hrs or key in seen or busy(seen, cap=False):  # 10분 안에 다른 묶음 글 -> 다음 실행에
        return
    seen[key] = time.time()
    wb = wx_bonus(seen)  # 날씨 가점(10/15 진우): 반응 점수까지 같을 때만 먼저 — 🔥 등급·Threads 표시·반응 순서는 그대로
    day = time.strftime("%Y-%m-%d ", kst)  # 회차가 늦게 돌아도(실행 누락) 그 시간대 글만 -> 다음 회차와 안 겹침
    since, until = day + f"{([0] + list(TOP_HOURS))[TOP_HOURS.index(hrs[-1])]:02d}:00", day + f"{hrs[-1]:02d}:00"
    prev = time.strftime("%Y-%m-%d ", time.gmtime(time.time() + 9 * 3600 - 86400)) + f"{TOP_HOURS[-1]:02d}:00" if hrs[-1] == TOP_HOURS[0] else since  # 첫 리스트(12시)는 어젯밤(전날 마지막 리스트 뒤) 좋은 딜도
    top = sorted((p for p in load(POSTS, []) if p.get("mid") and ((since <= p["t"] < until and (p.get("pop") or th_tier(p["text"])))
                                                              or (prev <= p["t"] < since and th_tier(p["text"]) and not p.get("th") and aff_note(p["url"] or "")))),  # 10/12 진우 '누락 없이': 개별 글로 못 나간 ①②(45분 간격·화장품 한도·3시간)는 다음 리스트에
                 key=lambda p: (not th_tier(p["text"]), bool(p.get("th")) or not aff_note(p["url"] or ""), -(p.get("pop") or 0), -wb(title_of(p["text"]))))[:5]  # 수수료 링크 아닌 딜 = Threads에 나간 딜처럼 셈(10/19 밤 'Threads는 수수료 딜만' 전엔 대부분 개별 글로 나가 th 1 -> 채널 순서 그대로)  # 10/12 진우 '좋은 딜은 묶어서': 🔥 좋은 딜(① 쿠팡 같은 상품 차이·② 30일 최저가·순위) 먼저, 그다음 커뮤니티 반응 순
    if len(top) < 3:
        return
    toss_in = TOSS_NO_CMP and any(is_toss(p["url"], p["text"]) for p in top)  # 토스 딜이 든 리스트 = 다른 몰 이름 X(10/14 22:30 점검) + 게시 시점 줄(10/19 12:30 점검)
    tail = f"\n\n{toss_when()}" if toss_in else ""
    items = []
    for p in top:
        price, why = parse(title_of(p["text"]))[2].split("/")[0].strip(), comment_of(p["text"]).split("\n")[0]  # 첫 줄만(💡 단위가격 줄은 💰 줄에 이미)
        why = strip_cmp("👉 " + why)[0][2:] if toss_in and why else why  # 👉 줄의 다른 몰 이름 조각(예: '네이버 지금배달 …')은 뺌, 다 빠지면 줄째
        items.append((parse(title_of(p["text"]))[1], p["url"], [
            ("💰 <b>" + esc(price) + "</b>" if price else "") + (" · " + esc(p["unit"]) if p.get("unit") else ""),
            "👀 " + esc(p.get("hot") or react(p)), "👉 " + esc(clip(why, 60)) if why else ""]))
    notes = "\n".join(f"<i>{n}</i>" for n in dict.fromkeys(aff_note(p["url"]) for p in top) if n)
    text, kb = top_post(f"🏆 <b>지금 살 만한 딜 TOP{len(items)}</b> ({hrs[-1]}시)\n{TOP_SUB_TOSS if toss_in else TOP_SUB}, 그다음 뽐뿌·클리앙 조회수·추천 순", items)
    if not tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True},
              text=(notes + "\n\n" if notes else "") + text + tail, reply_markup={"inline_keyboard": kb}):
        return
    bundled(seen)
    tok = E.get("THREADS_TOKEN")
    if not tok or hrs[-1] not in TH_LIST_HOURS:
        return
    posts = load(POSTS, [])  # Threads 12·18시 리스트(10/11 진우 '나누지 말고 묶기'): 대가성 문구 맨 앞, 번호·이름·가격 + 사이트 딜 페이지(구매 버튼), 500자
    top = [p for p in top if aff_note(p["url"] or "")]  # 10/19 밤 진우 'Threads는 수수료 딜만'
    if not top:
        print(f"threads skip (수수료 링크 아님) top{hrs[-1]} 리스트 | 항목 0개")
        return
    lines = [f"{NUM[n]} {clip(parse(title_of(p['text']))[1], 30)} {parse(title_of(p['text']))[2].split('/')[0].strip()}\n👉 {th_url(p, posts.index(p))}" for n, p in enumerate(top)]  # 10/19 진우 '직접 링크로': 텔레그램 버튼과 같은 링크

    def render(n, bs):  # 리스트 n줄 + 💄 (글, 줄) — 대가성 문구·토스 게시 시점 줄은 실제로 든 딜 기준(💄 포함, 10/19 밤 점검: 💄 토스 링크에 문구·시점 줄이 없던 것)
        used = top[:n] + [p for p, _ in bs]
        head = "\n".join(dict.fromkeys(aff_note(p["url"]) for p in used))
        tail = f"\n\n{toss_when()}" if TOSS_NO_CMP and any(is_toss(p["url"], p["text"]) for p in used) else ""
        return f"{head}\n\n🏆 지금 살 만한 딜 TOP{n} ({hrs[-1]}시)\n\n" + "\n".join(lines[:n]) + ("\n\n💄 화장품\n" + "\n".join(l for _, l in bs) if bs else "") + tail
    n = len(lines)
    while n > 1 and len(render(n, [])) > 480:  # 직접 링크는 사이트 주소보다 길 수 있어 1개까지 줄임
        n -= 1
    links, beauty = n, []  # 10/12 19:50 진우 '리스트로 만들어도 좋아': 개별 글이 못 된 화장품 🔥는 '💄 화장품' 칸으로 더함(기존 딜·링크 그대로, 링크는 합쳐 5개까지 — 넘으면 이름·가격만, 🛒 X)
    for p in [p for p in posts if p.get("mid") and prev <= p["t"] < until and not p.get("th") and p not in top and aff_note(p["url"] or "") and not th_weak(p["text"]) and th_beauty(title_of(p["text"]))][:5]:
        line = f"· {clip(parse(title_of(p['text']))[1], 26)} {parse(title_of(p['text']))[2].split('/')[0].strip()}" + (f"\n👉 {th_url(p, posts.index(p))}" if links < 5 else "")
        if len(render(n, beauty + [(p, line)])) > 480:
            break
        links += "👉" in line
        beauty.append((p, line))
    th_bundle(seen, f"top{hrs[-1]}", render(n, beauty), th_url(top[0], posts.index(top[0])))  # Threads 글 하나에 서로 다른 링크 5개까지(4279111, 10/12 12·15·18시 실패) -> 딜 링크만(미리보기 = 1번 딜, t.me 줄 X)


def busy(seen, cap=True):
    """묶음 글(토스 회차·TOP5·모아보기)을 지금 올리면 몰리는지(10/11 진우 '너무 자주 올리면 역효과'): 10분(BUNDLE_GAP) 안에 다른 묶음 글이 나갔거나,
    cap이면 최근 1시간 채널 글(posts.json 딜 + 묶음 글)이 HOUR_CAP 이상. 미루면 다음 실행에 다시 봄."""
    now = time.time()
    ts = [t for t in seen.get("bundles", {}).get("ts", []) if now - 3600 < t <= now]  # 최근 1시간(시계가 뒤로 간 기록은 무시)
    if ts and now - max(ts) < BUNDLE_GAP:
        return True
    since = time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 9 * 3600 - 3600))
    return cap and sum(p["t"] >= since and not p.get("shelf") for p in load(POSTS, [])) + len(ts) >= HOUR_CAP


def bundled(seen):
    """묶음 글을 올린 시각 기록(최근 1시간만) -> busy()가 간격·시간당 수를 셈."""
    now = time.time()
    seen["bundles"] = {"t": now, "ts": [t for t in seen.get("bundles", {}).get("ts", []) if now - 3600 < t <= now] + [now]}


def pick_price(p):
    """Threads 묶음 글 가격 칸(오늘의 픽·둘 중 뭐 살래): 쿠팡·네이버 = 확인가(own_end now + 확인 시각) 또는 글 가격(날짜), 토스 = 글 가격 + 그 글 게시 시점 줄(지금 가격 X)."""
    pr = " · ".join([s.strip() for s in parse(title_of(p["text"]))[2].split("/")[0].split(" · ") if s.strip()][:2])  # 가격 + 조건 1개(쿠폰가·와우가 — 빼면 누구나 그 가격처럼 보임)
    if shop_of(p) == "toss":
        m = re.search(r"(\d{1,2}/\d{1,2} \d{1,2}:\d{2}) 게시 시점", p["text"])  # 글에 적힌 토스 가격 시각 그대로(없으면 글 시각)
        return pr and f"{pr} · " + (f"⚠️ {m[1]} 게시 시점 가격" if m else toss_when(p["t"]))
    return f"{p['now']}" + (f" ({p['chk']} 확인)" if p.get("chk") else "") if p.get("now") else pr and f"{pr} ({int(p['t'][5:7])}/{int(p['t'][8:10])} 글 가격)"


def pick_post(seen):
    """N2 하루 1번 PICK_TH_AT~PICK_TH_END(KST): Threads '🎯 오늘의 픽 3' — 대가성 문구 맨 앞(상품마다 그 프로그램) + 이름·가격 + 오늘의 픽 날짜 쪽 링크 1개
    (사이트 링크가 들어가는 Threads 글은 이것만 — 딜 글은 지금처럼 직접 링크, 10/19 진우). 재료 = 사이트가 고정한 docs/today/picks.json(오늘), 날짜 쪽이 배포된 뒤(HEAD)만.
    가격 = 쿠팡·네이버는 확인가(own_end now + 확인 시각) 또는 글 가격(날짜), 토스는 글 가격 + 게시 시점 줄(지금 가격 X). 실패 = th_retry(묶음 글 규칙)."""
    kst = time.gmtime(time.time() + 9 * 3600)
    today, key = time.strftime("%Y-%m-%d", kst), time.strftime("thpick_%Y%m%d", kst)
    if not E.get("THREADS_TOKEN") or not PICK_TH_AT <= time.strftime("%H:%M", kst) < PICK_TH_END or key in seen or busy(seen, cap=False):  # 다른 묶음 글 10분 안이면 다음 실행
        return
    posts, ids = load(POSTS, []), load(PICKS_FILE, {}).get(today) or []
    ps = [posts[i] for i in ids if isinstance(i, int) and i < len(posts)]
    if not ps:
        return
    url = f"{SITE}today/{today}/"
    try:
        http(url, method="HEAD")  # 사이트 반영 전 = 다음 실행(링크가 404면 X)
    except Exception:
        return
    seen[key] = time.time()

    rows = [f"{NUM[k]} {clip(parse(title_of(p['text']))[1], 30)}" + (f" {pick_price(p)}" if pick_price(p) else "") for k, p in enumerate(ps)]
    text = aff_notes(p.get("url") for p in ps) \
        + f"\n\n🎯 오늘의 픽 {len(ps)} ({kst.tm_mon}/{kst.tm_mday})\n고민은 줄이고, 오늘은 이 {len(ps)}개만\n\n" + "\n".join(rows) + f"\n\n👉 {url}?ref=th"
    th_bundle(seen, "pick", text.strip()[:480], f"{url}?ref=th")
    bundled(seen)
    print("th pick", len(ps), "|", " / ".join(clip(parse(title_of(p["text"]))[1], 15) for p in ps))


PAIR_AT, PAIR_END, PAIR_UNIT = "16:10", "16:50", re.compile(r"^💰 (\S+당 [\d,]+원)", re.M)  # F(10/24 진우 '쓰레드엔 핫딜 + 비슷한 상품 묶음'): 하루 1번 15:30 간식 글 ~ 17시 토스 생필품 리스트 사이 · 진우 글 '💰 100ml당 554원꼴' 앞부분 그대로(다시 셈 X)


def pair_key(p):
    """'둘 중 뭐 살래' 같은 품목 열쇠 (품목 칸, 품목 이름, 토스?): 최저가 기록 품목(price_item — 그 낱말 바로 뒤에 한글이 붙으면 X: '햇반시'(감) ≠ 즉석밥)
    또는 그 칸 정규식에 걸린 낱말(글자만 — 쉼표·괄호 X, 첫 낱말(보통 브랜드)이면 다음 것). 토스는 다른 몰과 한 묶음 X(TOSS_NO_CMP — 한 글에 놓는 것도 비교).
    shortcut: 낱말 맞춤이라 '앰플 인 아이크림' 같은 겹친 이름은 못 거름 — 엉뚱한 묶음이 로그('th pair')에 보이면 PRICE_NOT·칸 정규식에 더함."""
    c, t = cat_of(p), title_of(p["text"])
    name = parse(t)[1]
    if not c or re.search(PRICE_NOT, t):
        return None
    it = price_item(p)  # 토스 = None
    if it and (m := re.search(it[2], name)) and not re.match(r"[가-힣]", name[m.end():m.end() + 1]):
        return (c, it[1], False)
    w = next((m for m in re.finditer(rf"\w*(?:{dict((k, r) for k, _, r in SHELF_CATS)[c]})\w*", name) if m.start()), None)
    return w and (c, re.sub(r"\s", "", w[0]), shop_of(p) == "toss")


def pair_post(seen):
    """F 하루 1번 PAIR_AT~PAIR_END(KST): Threads '🤔 ○○ 둘 중 뭐 살래? / 지금 특가 중인 것끼리 모아 봄' — 사이트 🔥 진열(build_site.items 단계 0) 중 같은 품목(pair_key) 2~4개(480자에 맞게).
    '지금 특가 중'이 참인 것만: 진우 쿠팡·네이버 = 보이는 가격 확인(chkt) CPRE_FRESH 안, 진우 토스 = 오늘 확인(own_end chk), 커뮤니티 딜 = 오늘 올린 것만 · 수수료 링크만(올리브영 X — 링크 나열 금지 FAQ)
    · 브랜드 2개↑ · 대가성 문구 맨 앞(aff_notes) · 토스는 토스끼리(+ 게시 시점, '전체 보기' = 토스 모음 쪽) · 쿠팡 🚀 = 오늘 API isRocket(cpq r), 없으면 글 로켓 근거, 아니면 📦
    · 💰 = pick_price(쿠폰·와우 조건 그대로) · 단가 = 모두 같은 단위·조건 없는 가격·확인가 = 글 가격일 때만 · 긴 링크(150자↑) = 사이트 딜 쪽 · 끝 줄 '전체 보기 → 사이트 품목 쪽'
    · 쓴 상품은 3일 안 다시 X(seen pairu 날짜) · 토스 아닌 묶음·3개 되는 묶음 먼저 · 480자에 안 맞으면 다음 묶음 · 후보 0 = 그날 생략. 실패 = th_retry."""
    now = time.time()
    kst = time.gmtime(now + 9 * 3600)
    today, key = time.strftime("%Y-%m-%d", kst), time.strftime("pair_%Y%m%d", kst)
    if not E.get("THREADS_TOKEN") or not PAIR_AT <= time.strftime("%H:%M", kst) < PAIR_END or key in seen or busy(seen, cap=False):
        return
    cut = time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600 - 3 * 86400))
    mem = {u: d for u, d in seen.get("pairu", {}).get("m", {}).items() if d > cut}  # 3일 안 쓴 상품(seen 3일 지움과 따로 — 날짜로)
    fresh_at, md = time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 9 * 3600 - CPRE_FRESH)), f"{kst.tm_mon}/{kst.tm_mday} "
    ok = lambda p: (p.get("chkt", "") >= fresh_at if shop_of(p) != "toss" else (p.get("chk") or "").startswith(md)) if p.get("own") else p["t"][:10] == today  # '지금 특가 중' 근거
    posts, rk = load(POSTS, []), seen.get("cpq", {}).get("r", {})
    days, gs = sorted({p["t"][:10] for p in posts if not p["text"].startswith("📋")}, reverse=True), {}
    for i, p, sh in shelf_items(posts, days):  # 진열 순서(🔁 다시 특가 → 진우 상품 → 최신) = 첫 상품이 그 묶음의 핫딜
        if sh[0] == 0 and aff(p.get("url")) and aff_note(p["url"]) != OY_NOTE and p["url"] not in mem and ok(p) and (k := pair_key(p)) \
                and parse(title_of(p["text"]))[1] not in [parse(title_of(q["text"]))[1] for _, q in gs.get(k, [])]:
            gs.setdefault(k, []).append((i, p))
    brand, lab = lambda p: parse(title_of(p["text"]))[1].split()[0], lambda p: (PAIR_UNIT.search(p["text"]) or [""])[0].split("당")[0]
    gs = {k: g[:1] + sorted(g[1:], key=lambda x: (lab(x[1]) != lab(g[0][1]), brand(x[1]) == brand(g[0][1]))) for k, g in gs.items()}  # 같은 단위 먼저(단가 비교) · 다른 브랜드 먼저
    seen[key] = {"t": now}
    link = lambda i, p: (lambda u: u if len(u) <= 150 else f"{SITE}p/{i}.html?ref=th")(th_url(p, i))  # 긴 제휴 링크(링크프라이스 등) = 사이트 딜 쪽(500자 안)

    def render(k, n):
        rows = gs[k][:n]
        cond = lambda p: re.search(r"쿠폰|와우|회원|멤버십|카드", pick_price(p) or "")
        unit = lambda p: (m := PAIR_UNIT.search(p["text"])) and (p.get("now") or "").split(" ")[0] in ("", parse(title_of(p["text"]))[2].split(" ")[0]) and m[1]  # 확인가 ≠ 글 가격 = 단가 X(옛 가격 기준)
        us = [unit(p) for _, p in rows]
        us = us if all(us) and len({u.split("당")[0] for u in us}) == 1 and not any(cond(p) for _, p in rows) else [""] * n  # 단가는 모두 같은 단위·조건 없는 가격일 때만(와우가 옆 일반가 비교 X)
        badge = lambda p: ("🚀 " if (rk[p["url"]] if p["url"] in rk else cp_rocket(p["text"])) else "📦 ") if shop_of(p) == "coupang" else ""
        return aff_notes(p["url"] for _, p in rows) + f"\n\n🤔 {k[1]} {'둘' if n == 2 else '이'} 중 뭐 살래?\n지금 특가 중인 것끼리 모아 봄\n\n" \
            + "\n".join(f"{NUM[j]} {badge(p)}{clip(parse(title_of(p['text']))[1], 28)}\n💰 {pick_price(p)}" + (f" · {u}" if u else "") + f"\n👉 {link(i, p)}" for j, ((i, p), u) in enumerate(zip(rows, us))) \
            + f"\n\n전체 보기 → {SITE}c/{'toss' if k[2] else CAT_META[k[0]][0]}/?ref=th"
    for k in sorted((k for k in gs if len({brand(p) for _, p in gs[k]}) >= 2), key=lambda k: (k[2], len(gs[k]) < 3)):  # 브랜드 2개↑(한 브랜드 맛만 다른 것 X)
        g = gs[k]
        j = next(n_ for n_, x in enumerate(g) if brand(x[1]) != brand(g[0][1]))
        gs[k] = [g[0], g[j]] + [x for n_, x in enumerate(g[1:], 1) if n_ != j]  # 둘째 = 핫딜과 다른 브랜드(둘만 나가도 '둘 중'이 고를 만하게)
        n = min(len(gs[k]), 4)  # 상품 링크 4개 + 사이트 1개 = Threads 5개 한도
        while n > 2 and len(render(k, n)) > 480:
            n -= 1
        if len(render(k, n)) > 480:
            continue
        seen["pairu"] = {"t": now, "m": {**mem, **{p["url"]: today for _, p in gs[k][:n]}}}
        th_bundle(seen, "pair", render(k, n), link(*gs[k][0]))  # 미리보기 = 1번(핫딜)
        bundled(seen)
        print("th pair", k[1], n, "items |", " / ".join(clip(parse(title_of(p["text"]))[1], 15) for _, p in gs[k][:n]))
        return
    print("pair 후보 0개 — 오늘 생략")


def toss_pool(seen):
    """토스 API 목록 1일치 모음(toss_relink 이름 대조·toss_picks 이름 찾기가 같이 씀) -> [[id, 이름, 가격, 마지막으로 본 시각]].
    카테고리·하루특가 = UTC 날짜로 하루 1번(9시 갱신), 베스트 = 1시간 1번. 같은 실행에서 두 번 불러도 API는 1번(일 상한 아끼기)."""
    now = time.time()
    day, hour, got = time.strftime("%Y%m%d", time.gmtime(now)), time.strftime("%Y%m%d%H", time.gmtime(now)), []  # 9시(KST) = 0시(UTC) 갱신 -> UTC 날짜로 하루 1번
    if seen.get("tossget_cat", {}).get("d") != day or seen["tossget_cat"].get("v") != 2:  # v2(10/11) = 할인율·리뷰도 저장 -> 예전 목록이면 1번 다시
        tree = toss("/categories")["categories"]
        got += toss("/products/today-deals?size=30")["items"] + [x for c in tree for x in toss(f"/products/best-categories/{c['categoryId']}?size=100")["items"]]
        for c in [k for c in tree if c["displayName"] == "식품" for k in c.get("children") or []][:15]:  # 10/10: 뽐뿌 [토스] 딜은 거의 식품인데 최상위 베스트엔 없던 것(청도반시·삼겹살 5kg·모짜렐라 치즈떡) -> 식품 하위 베스트도(최대 1,500개, 일 상한 10,000 안)
            try:
                got += toss(f"/products/best-categories/{c['categoryId']}?size=100")["items"]
            except Exception as e:  # 하위 카테고리 베스트가 안 되는 ID면 그것만 건너뜀
                print("toss sub", c.get("displayName"), repr(e))
        seen["tossget_cat"] = {"t": now, "d": day, "v": 2}
    if seen.get("tossget_best", {}).get("h") != hour:
        got += toss("/products/best-selling?size=100")["items"]
        seen["tossget_best"] = {"t": now, "h": hour}
    cache = {x[0]: x for x in seen.get("tosscache", {}).get("items", []) if x[3] > now - 86400}  # [id, 이름, 가격, 마지막으로 본 시각]. 1일(쉐어링크 FAQ: API 데이터 저장·캐싱은 가능한 한 1일 이내, 10/9)
    cache.update({x["tacaItemId"]: [x["tacaItemId"], x["displayName"], x["displayPrice"], now, x.get("discountRate"), x.get("reviewScore"), x.get("reviewCount")] for x in got})  # 할인율·리뷰 = 특가 회차 거르기
    items = list(cache.values())
    seen["tosscache"] = {"t": now, "items": items}
    return items


def toss_relink(seen):
    """쉐어링크가 없는 최근 3일 [토스] 채널 딜에 우리 쉐어링크를 붙여 채널 글 버튼을 교체(진우가 사본에 답장한 것과 같은 relink_channel — 대가성 문구·사본 '교체됨'·posts.json·사이트).
    ① 루리웹·클리앙 글 = 처음 1번 글의 상품 주소를 다시 읽어 발급(본문 링크 고치기 전 글·그때 실패한 글). 버튼이 토스 앱 공유 주소(service.toss.im)면 상품 주소로 풀어 발급.
    ② 그 외(뽐뿌는 서버 차단이라 상품 주소를 못 읽음) = 토스 API 목록(하루특가·최상위 카테고리별 베스트 100·식품 하위 카테고리별 베스트 100(10/10~)·베스트 100)에서 찾기 — 검색 API가 없어서 목록 대조:
    이름 겹침 후보 8개 -> Claude가 같은 상품인지 확인(8점 이상만, 용량·수량 다르면 X). 10/9 기록만 해 본 첫 실행 11개 중 6개 찾음·6개 모두 같은 상품 -> '수정하자'로 교체.
    10/9 진우 '수수료 링크 안 붙은 것도 자동으로': 못 찾은 딜은 3일 동안 새 후보가 목록에 들어올 때마다 다시 확인(이미 본 후보는 Claude에 다시 안 물음),
    목록은 1일치를 모아 둠(베스트 순위에서 빠진 상품도 하루 동안은 대조 — 10/9 계란·비타500. 3일 -> 1일: 쉐어링크 FAQ '저장·캐싱은 가능한 한 1일 이내'). 찾으면(발급 실패 포함) 끝, 못 찾으면 지금처럼 사본 답장.
    목록은 seen에 저장해 재사용(문서 권장, 일 상한 10,000개): 카테고리·하루특가 = 하루 1번(9시 갱신), 베스트 = 1시간 1번(못 찾은 딜이 남아 있을 때만).
    10/18 진우 '나머지 토스 링크는 뽐뿌 말고 바로 연결': TOSS_BACKFILL 글(3일 지난 글 포함)도 1번 새로 찾고(하루 넘은 글은 지금 가격이 글 가격보다 15% 넘게 비싸면 특가 끝 -> 연결 X),
    올린 지 TOSS_WAIT(2시간) 지나도 못 찾은 글은 진우에게 링크 요청 1번(toss_ask — 답장하면 사본 답장과 같은 길로 교체, posts.json cp·ask)."""
    kst = lambda h: time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - h * 3600))
    since, late, old = kst(72), kst(TOSS_WAIT / 3600), kst(24)
    key = lambda p: ("trb_" if p["mid"] in TOSS_BACKFILL else "tr_") + str(p["mid"])  # 백필 = 새 기록(10/18 01시 크레딧 바닥 때 Claude 없이 '본 후보'로 넘어간 1204 등)
    todo = [p for p in load(POSTS, []) if HAS_TOSS and p.get("mid") and (p["t"] >= since or p["mid"] in TOSS_BACKFILL) and not toss_share(p.get("url")) and not p.get("ask") and not p["text"].startswith("📋")
            and store_info(title_of(p["text"]), p.get("url")).startswith("💰 토스") and (not seen.get(key(p), {}).get("done") or p["t"] <= late)]
    if not todo:
        return
    items = toss_items(seen) if any(not seen.get(key(p), {}).get("done") for p in todo) else []
    asks = {}
    for p in todo:
        r, title = seen.setdefault(key(p), {"t": time.time()}), title_of(p["text"]).lstrip("🔥 ")
        notice = {"chat": {"id": ADMIN}, "message_id": p.get("cp"), "text": p["text"], "entities": p.get("entities", [])}
        won = price_won(title) if p["t"] < old else None
        link, msg = (None, None) if r.get("done") else toss_match(seen, r, title, p.get("url") or "", items, won and won * 1.15)
        if msg:
            print("toss match", p["t"][5:], title[:40], msg)
        if link:
            relink_channel(notice, p["mid"], link)
        elif p["t"] <= late and not RUN.get("treuse") and (a := toss_ask(title, p.get("url") or "", p["mid"], quiet=bool(asks))):  # 토스 점검 땐 안 물음(진우도 못 만듦)
            asks[p["mid"]] = a
    if asks:  # 진우 답장이 이 글로 가게 사본 번호를 요청 메시지로, 다시 안 물음(ask)
        posts = load(POSTS, [])
        for p in posts:
            if p.get("mid") in asks:
                p.update(cp=asks[p["mid"]], ask=1)
        json.dump(posts, open(POSTS, "w"), ensure_ascii=False)
        print("toss ask", list(asks))


def toss_items(seen):
    """이름 대조 후보 = 진우가 예약한 토스 링크(최근 3일, 같은 상품이면 발급 없이 그 링크 — 10/11 뽐뿌 민물장어) + 토스 API 1일 목록(toss_pool)."""
    now, since = time.time(), time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - 3 * 86400))
    return [["ev:" + e["url"], e["name"], int(re.sub(r"\D", "", e.get("button", "")) or 0), now] for e in load(EVENTS, [])
            if e.get("name") and toss_share(e.get("url")) and e["at"] >= since] + toss_pool(seen)


def toss_match(seen, r, title, src, items, maxp=None):
    """토스 딜 하나 -> (우리 쉐어링크 또는 None, 로그 조각 또는 None=새 후보 없음). r = 딜마다 기록(src: 글 주소 1번 읽음, ids: Claude가 본 후보, done: 같은 상품 찾음 — 발급 실패·특가 끝 포함).
    ① 루리웹·클리앙 글 = 처음 1번 상품 주소를 다시 읽어 발급, 토스 앱 공유 주소는 상품 주소로 풀어 발급 ② 목록에서 이름 겹침 후보 8개 -> Claude 8점 이상만.
    maxp = 받아들일 지금 가격 상한(넘으면 특가 끝 — 다른 가격에 억지로 연결 안 함)."""
    first, u = "ids" not in r, None
    r.setdefault("ids", [])
    if not r.get("src") and not RUN.get("treuse"):  # (토스 점검 땐 발급이 안 돼 상품 주소 1번 읽기는 아껴 둠)
        r["src"] = 1
        u = store_link(src) if re.search(r"//[\w.]*(ruliweb\.com|clien\.net)/", src) else plain(src) if "toss" in urllib.parse.urlsplit(src).netloc else None
    link = affiliate(u)[0] if (u or "").startswith("https://toss.shopping/t/") else None
    if toss_share(link):
        r["done"] = True
        return link, f"-> 글의 상품 주소 {u} | 링크 교체"
    toks = lambda s: {t for t in re.findall(r"[0-9a-z.]+[가-힣a-z]*|[가-힣]+", s.lower()) if len(t) > 1}
    ns = lambda s: re.sub(r"\s+", "", s.lower())
    name = parse(title)[1]
    near = lambda x: sum(t in ns(x[1]) for t in toks(name)) + sum(t in ns(name) for t in toks(x[1]))  # 띄어쓰기 달라도(극조생감귤 = 극조생 감귤) 겹친 낱말 수
    cand = sorted((x for x in items if x[0] not in r["ids"] and near(x) >= 3 and toss_ok(seen, x[0])), key=lambda x: -near(x))[:8]  # 토스 점검 땐 보관 링크 있는 것만(빠진 후보는 '본 후보'가 아니라 점검 끝나면 다시)
    if not cand and not first:  # 새 후보 없음 -> 조용히 다음 실행에
        return None, None
    pick = cand and ai_pick(MATCH_PROMPT.format(title), [f"{x[1]} | {x[2]:,}원" for x in cand])
    r["ids"] += [x[0] for x in cand]  # Claude가 답한 뒤에만 '본 후보'(실패하면 다음 실행에 다시 — 10/18 크레딧 바닥)
    hit = cand[pick[0]["i"]] if pick and pick[0]["score"] >= 8 else None
    over = hit and maxp and hit[2] > maxp
    link = hit[0][3:] if hit and not over and str(hit[0]).startswith("ev:") else None  # 진우 링크 = 발급 없이 그대로
    if hit:
        r["done"] = True
    if hit and not link and not over:
        seen[f"tb_{hit[0]}"] = {"t": time.time(), "n": hit[1]}  # 채널에 이미 나간 상품 -> 3일 동안 토스 베스트·하루특가에 다시 안 올림(10/10 삼겹살 01:31 딜 → 12:09 베스트)
        try:
            link = toss_link(seen, hit[0], hit[1])
        except Exception as e:  # 발급 제한 상품 -> 진우에게 요청
            print("toss link", repr(e))
    res = f"{hit[1][:40]} {hit[2]:,}원 (id {hit[0]}, {pick[0]['score']}점) | " + ("링크 교체" if link else "특가 끝" if over else "발급 실패") if hit else "없음"
    return link, f"-> {res} | {'' if first else '다시 · '}후보 {len(cand)}/{len(items)}"


def toss_ask(title, src, mid=None, quiet=False):
    """쉐어링크를 못 찾은 토스 딜 -> 진우에게 링크 요청(상품명 + 원글 주소) -> 요청 메시지 번호(실패 None = 다음 실행에 다시).
    이 메시지에 토스 앱 공유 링크를 답장하면 publish_approved가: 채널에 올라간 글(mid — '📢 채널에 올라간 글' 버튼 = 사본 답장과 같은 길)은 버튼·문구 교체, 아직 안 올린 딜(toss_wait)은 그때 게시."""
    m = tg("sendMessage", chat_id=ADMIN, disable_notification=quiet, link_preview_options={"is_disabled": True},
           text=f"🔗 토스 링크 필요 — {title}\n원글: {src}\n\n토스 앱에서 같은 상품 → 공유 → 링크를 이 메시지에 답장으로 보내줘. "
                + ("채널 글 버튼·문구를 그 링크로 바꿔요" if mid else "그때 채널에 올려요(그 전엔 안 올림)"),
           reply_markup={"inline_keyboard": [[{"text": "📢 채널에 올라간 글", "url": post_url(mid)}]] if mid else []})
    return (m or {}).get("message_id")


def toss_post(w, link, seen=None):
    """기다리던 토스 딜(main이 보관한 Claude 판단 그대로)을 쉐어링크로 채널에 — 대가성 문구 맨 앞·게시 시점 가격 줄은 deal_post가."""
    p = w["p"]
    if not post_or_draft({**w["d"], "toss": link}, p["comment"], p["score"], p.get("q"), {k: p.get(k) for k in ("e", "hook", "pts", "unit", "warn", "who", "use", "tone")}) and seen is not None:
        tone_keep(seen, "ch", p.get("tone"))


def toss_wait(seen):
    """10/18 진우 '토스 딜인데 쉐어링크를 못 찾으면 뽐뿌 링크로 올리지 말고': main이 tw_로 보관한 토스 커뮤니티 딜을 실행마다 다시 찾아(toss_match) 찾으면 그때 게시.
    TOSS_WAIT(2시간) 지나도 없으면 진우에게 링크 요청 1번(toss_ask) -> 답장 오면 publish_approved가 게시. 답이 없으면 3일 뒤 seen 정리로 끝."""
    ws = [k for k, v in seen.items() if k.startswith("tw_") and not v.get("ask")]
    if not ws:
        return
    items = None
    for k in ws:
        w, link = seen[k], None
        d = w["d"]
        if not w.get("done"):
            try:
                items = toss_items(seen) if items is None else items
                link, msg = toss_match(seen, w, d["title"], d["url"], items)
                if msg:
                    print("toss wait", d["title"][:40], msg)
            except Exception as e:  # 토스 API(터널)·Claude 오류여도 2시간 지난 딜은 진우에게 물음
                print("toss wait", repr(e))
        if link:
            seen.pop(k)
            toss_post(w, link, seen)
        elif time.time() - w["t"] >= TOSS_WAIT and RUN.get("treuse"):  # 토스 점검 = 진우도 새 링크를 못 만듦 -> 안 묻고 그만 찾음(하루 요약에 1줄)
            w["ask"] = -1
            tnote(seen, "miss", "커뮤니티 " + d["title"])
        elif time.time() - w["t"] >= TOSS_WAIT:
            w["ask"] = toss_ask(d["title"], d["url"])


def pick_scan(seen, names):
    """이름 예약 상품이 1일 목록에 없을 때: Claude가 이름에 맞는 하위 카테고리(2·3단계)를 고르고(카테고리 트리는 일 상한 차감 없음, 새 이름이 생기면 그 이름만 더 물음),
    그 하위 카테고리 베스트 100을 실행마다 3개씩, 하루(KST — 밤 12시에 새로) PICK_SCAN개까지 더 받아 1일 목록(tosscache)에 넣음.
    이 이름들의 하위 카테고리를 다 봤으면 True(하루 상한에 걸려 못 고른 이름이 있으면 False -> 진우에게 묻지 않고 다음 날 상한·예약 90분 전까지 기다림)."""
    now = time.time()
    day = time.strftime("%Y%m%d", time.gmtime(now + 9 * 3600))
    sc = seen.get("pickscan") if seen.get("pickscan", {}).get("d") == day else None
    sc = seen["pickscan"] = sc or {"t": now, "d": day, "plan": [], "done": [], "names": []}
    new = [n for n in names if n not in sc["names"]]
    if new and len(sc["plan"]) < PICK_SCAN:
        tree = toss("/categories")["categories"]
        food = {k["categoryId"] for c in tree if c["displayName"] == "식품" for k in (c.get("children") or [])[:15]}  # toss_pool이 이미 보는 식품 하위
        subs = [(k["categoryId"], f"{c['displayName']} > {k['displayName']}") for c in tree for k in c.get("children") or [] if k["categoryId"] not in food]
        subs += [(g["categoryId"], f"{c['displayName']} > {k['displayName']} > {g['displayName']}") for c in tree for k in c.get("children") or [] for g in k.get("children") or []]
        picks = subs and ai_pick(SCAN_PROMPT.format("\n".join(new)), [n for _, n in subs]) or []
        sc["plan"] += [c for c in dict.fromkeys(subs[p["i"]][0] for p in picks) if c not in sc["plan"]][:PICK_SCAN - len(sc["plan"])]
        sc["names"] += new  # (상한이 남아 있을 때만 — 다 찼으면 이 이름들은 안 넣어서 아래가 False)
    got = []
    for cid in [c for c in sc["plan"] if c not in sc["done"]][:3]:
        sc["done"].append(cid)
        try:
            got += toss(f"/products/best-categories/{cid}?size=100")["items"]
        except Exception as e:
            print("toss pick scan", cid, repr(e))
    if got:
        cache = {x[0]: x for x in seen.get("tosscache", {}).get("items", []) if x[3] > now - 86400}
        cache.update({x["tacaItemId"]: [x["tacaItemId"], x["displayName"], x["displayPrice"], now, x.get("discountRate"), x.get("reviewScore"), x.get("reviewCount")] for x in got})
        seen["tosscache"] = {"t": now, "items": list(cache.values())}
    sc["t"] = now
    return all(n in sc["names"] for n in names) and len(sc["done"]) >= len(sc["plan"])


def toss_picks(seen):
    """토스 상품 이름 예약(10/11 진우 '특가 탭 추천 9개 자동으로'): events.json {"at": "YYYY-MM-DD HH:MM", "name": 상품명, "api": true} -> 사람 손 없이
    ① 예약 8시간 전부터 토스 API 목록(1일치: 하루특가 전체·베스트·카테고리 베스트 + 모자라면 Claude가 고른 하위 카테고리 베스트)에서 이름 겹침 후보 ->
    Claude가 같은 상품인지 확인(8점 이상, 용량·수량 다르면 X) -> 쉐어링크 자동 발급(토스는 자동 발급 OK). 못 찾거나 발급이 막히면 진우에게 1번 링크 요청
    (진우 링크를 받으면 그 행을 진우 예약(url·text·button)으로 바꾸면 끝 — api 행이 없어지면 이 예약도 없음).
    ② 예약 시각이 되면(3시간 안) 상품 상세로 지금 가격·품절 재확인(품절이면 안 올림) -> 채널(대가성 문구 맨 앞·상품명·가격·할인·리뷰·Claude 한 줄 — 효능·쿠팡 비교 없음) + Threads.
    API 상품이라 posts.json(사이트·모아보기·블로그)엔 안 남김. 품절 지켜보기(toss_soldout)·3일 중복 방지(tb_)·같은 날 자동 회차에서 빠짐(toss_deals booked)."""
    if not HAS_TOSS:
        return
    now = time.time()
    kst = time.gmtime(now + 9 * 3600)
    nowk, today = time.strftime("%Y-%m-%d %H:%M", kst), time.strftime("%Y-%m-%d", kst)
    at = lambda d: time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 9 * 3600 + d))
    for k in [k for k in seen if k.startswith("pk_") and k[3:] < at(-86400)]:  # 토스 API 데이터(상품명·id)는 1일 안에 지움(쉐어링크 FAQ)
        del seen[k]
    todo = [e for e in load(EVENTS, []) if e.get("api") and not e.get("url") and e.get("name") and at(-PICK_LATE) <= e["at"] <= at(PICK_AHEAD)
            and seen.get("pk_" + e["at"], {}).get("st") not in ("done", "skip")]
    if not todo:
        return
    for e in todo:  # 같은 시각 행의 상품명이 바뀌었으면(옛 대화가 고침) 처음부터
        if seen.get("pk_" + e["at"], {}).get("n0", e["name"]) != e["name"]:
            del seen["pk_" + e["at"]]
    toks = lambda s: {t for t in re.findall(r"[0-9a-z.]+[가-힣a-z]*|[가-힣]+", s.lower()) if len(t) > 1}
    ns = lambda s: re.sub(r"\s+", "", s.lower())
    need = [e for e in todo if not seen.get("pk_" + e["at"], {}).get("id") and not seen.get("pk_" + e["at"], {}).get("asked")]  # 진우에게 링크를 요청했으면 그만 찾음(나중에 찾아 올리면 진우 링크와 두 번)
    if need:
        try:  # 터널 끊김 등 -> 이번 실행은 찾기만 건너뜀(Threads 실패 알림 아님), 예약 시각 게시는 아래에서 그대로
            items = toss_pool(seen)
            sm = toss_daymap(seen, now, today, True)  # 오늘 하루특가 전체(커서 페이지)
            items = items + [[v[0], v[2], v[1], now] for v in (sm or {}).get("m", {}).values() if len(v) > 2]
            if any(not seen.get("pk_" + e["at"], {}).get("ids") for e in need):  # 처음 보는 예약이 있으면 1일 목록부터
                scanned = False
            else:
                scanned = pick_scan(seen, [e["name"] for e in need])
                items = seen.get("tosscache", {}).get("items", []) + [[v[0], v[2], v[1], now] for v in (sm or {}).get("m", {}).values() if len(v) > 2]
        except Exception as ex:
            print("toss pick list", repr(ex))
            need = []
        for e in need:
            r = seen.setdefault("pk_" + e["at"], {"t": now, "ids": [], "n0": e["name"]})
            near = lambda x: sum(t in ns(x[1]) for t in toks(e["name"])) + sum(t in ns(e["name"]) for t in toks(x[1]))
            cand = sorted({x[0]: x for x in items if x[0] not in r["ids"] and near(x) >= 3 and toss_ok(seen, x[0])}.values(), key=lambda x: -near(x))[:8]  # 토스 점검 땐 보관 링크 있는 것만
            r["ids"] = r["ids"] + [x[0] for x in cand] or ["-"]  # 빈 목록이면 '처음 봄' 표시만
            try:
                pick = cand and ai_pick(MATCH_PROMPT.format(e["name"]), [f"{x[1]} | {x[2]:,}원" for x in cand])
            except Exception as ex:  # Claude 오류 -> 본 후보에서 빼고 다음 실행에 다시
                print("toss pick match", repr(ex))
                r["ids"] = [i for i in r["ids"] if i not in {x[0] for x in cand}] or ["-"]
                continue
            hit = cand[pick[0]["i"]] if pick and pick[0]["score"] >= 8 else None
            if hit:
                try:
                    link = toss_link(seen, hit[0], hit[1])
                except Exception as ex:  # resultType FAIL(발급 제한 상품) -> 진우에게 / 터널·네트워크·ACCESS_DENIED(터널 실패로 직접 호출)·호출 제한 -> 이 후보 다시(다음 실행), 이번엔 진우에게 안 물음
                    print("toss link", repr(ex))
                    if not isinstance(ex, RuntimeError) or re.search(r"ACCESS|DENIED|UNAUTH|\bIP\b|RATE|LIMIT|429|TOO_MANY|500", str(ex), re.I):
                        r["ids"], r["net"] = [i for i in r["ids"] if i != hit[0]] or ["-"], now
                        continue
                    link = None
                r.update(id=hit[0], n=hit[1], link=link, t=now)
                print("toss pick", e["at"], clip(e["name"], 30), "->", clip(hit[1], 30), f"{hit[2]:,}원 (id {hit[0]}, {pick[0]['score']}점)", "| 링크" if link else "| 발급 실패")
            else:
                print("toss pick", e["at"], clip(e["name"], 30), "-> 없음", f"| 후보 {len(cand)}/{len(items)}" + (" · 하위 카테고리까지 봄" if scanned else "")
                      + (f" | 가장 비슷: {clip(cand[pick[0]['i']][1], 40)} {pick[0]['score']}점" if pick else f" | 겹침 1위: {clip(cand[0][1], 40)}" if cand else ""))  # 이름 찾기 판단 근거(점검용)
    for e in todo:  # 못 찾음·발급 실패 -> 진우에게 1번(하위 카테고리까지 다 봤거나 예약 90분 전)
        r = seen.get("pk_" + e["at"])
        if r and not r.get("link") and not r.get("asked") and r.get("net") != now and (r.get("id") or (need and scanned) or e["at"] <= at(PICK_ASK)):
            if RUN.get("treuse"):  # 토스 점검 = 진우도 새 링크를 못 만듦 -> 안 물음: 점검 안 예약은 하루 요약 1줄로 끝(st skip = watch 알림 X), 점검 뒤 예약은 복귀 뒤 다시 찾음
                if e["at"] <= TOSS_PAUSE[1]:
                    r.update(asked=1, st="skip")
                    tnote(seen, "miss", f"이름 예약 {e['name']}")
                continue
            r["asked"] = 1
            tg("sendMessage", chat_id=ADMIN, text=f"🔎 토스 이름 예약 {e['at']} '{e['name']}' — " + ("쉐어링크 발급이 막힌 상품이야" if r.get("id") else "토스 API 목록에서 못 찾았어")
               + " → 이 상품 쉐어링크 공유 문구를 Claude 대화에 주면 그 시각 진우 예약으로 바꿀게(안 주면 이 상품만 안 올라감)")
    tok = E.get("THREADS_TOKEN")
    for e in todo:  # ② 예약 시각
        r = seen.get("pk_" + e["at"])
        if e["at"] > nowk or not r or not r.get("link"):
            continue
        if seen.get(f"tb_{r['id']}", {}).get("t", 0) >= now - (kst.tm_hour * 3600 + kst.tm_min * 60 + kst.tm_sec):  # 오늘 이미 나간 상품(특가 회차·다른 이름 예약) -> 같은 날 두 번 X
            r["st"] = "skip"
            print("toss pick", e["at"], clip(r["n"], 30), "오늘 이미 올린 상품 -> 안 올림")
            continue
        try:
            d = toss(f"/products/detail?tacaItemIds={r['id']}")
        except Exception as ex:  # 터널 등 -> 다음 실행에(3시간 안)
            print("toss pick detail", repr(ex))
            continue
        x = (d["items"] or [None])[0]
        if not x or x.get("isSoldOut"):
            r["st"] = "skip"
            print("toss pick", e["at"], clip(r["n"], 30), "품절·조회 안 됨 -> 안 올림")
            continue
        price, night = x["displayPrice"], int(r["id"] in {v[0] for v in (toss_daymap(seen, now, today, seen.get("soldmap", {}).get("d") != today) or {}).get("m", {}).values()})  # 오늘 하루특가면 품절 땐 '밤 12시 재오픈'
        try:
            tone, tsuf = tone_ask(seen, "ch")
            p = (ai_pick(PICK_PROMPT + tsuf, [f"{r['n']} | {price:,}원 ({x.get('discountRate', 0)}% 할인)" + (f" | 리뷰 {x.get('reviewScore')}점 {x['reviewCount']:,}개" if x.get("reviewCount") else "")]) or [None])[0]
        except Exception as ex:  # 코멘트 없이도 올림(사람이 고른 상품)
            print("toss pick comment", repr(ex))
            p = None
        info, lines = "하루특가 · 밤 12시까지" if night else "", toss_ul(x) + toss_lines(p)  # 10/20 진우 '사고 싶게' 🙋·👍(없으면 Claude 한 줄) · S 묶음 단가 줄
        body = mall_body("toss", info, "🔥", r["n"], toss_price(x), list(map(esc, lines)) + ([toss_when()] if TOSS_NO_CMP else []))  # 10/22 진우 '토스·쿠팡 한눈에'
        btn = mall_btn("toss", f"{price:,}원")
        r["st"] = "done"  # 먼저 표시: 채널·Threads 실패해도 같은 글 반복 안 함
        img = toss_photo(x)
        m, ph = tg_toss(ad_head(TOSS_NOTE, plain_of(body)) + body, {"inline_keyboard": [[{"text": btn, "url": r["link"]}]]}, img)
        if not m:
            r["st"] = None  # 채널 실패 -> 다음 실행에 다시
            continue
        if ph:
            tph_log(seen, (r["id"], x.get("tacaId")), tg=m["message_id"])
        seen[f"tb_{r['id']}"] = {"t": now, "n": r["n"]}  # 3일 동안 토스 자동 회차에 다시 안 올림
        bundled(seen)  # 토스 자동 회차가 이 글과 10분 띄우고 1시간 글 수에도 셈
        tone_keep(seen, "ch", p and tone)
        seen["ev_" + e["at"]] = now  # 실제 게시 시각(events()와 같은 키 — api 예약은 events()가 안 봄) -> toss_solo가 뒤 10분 쉼
        seen[f"sold_{m['message_id']}"] = {"t": now, "d": today, "k": "ev", "pre": ad_head(TOSS_NOTE, plain_of(body)), "body": body, "btn": btn, "url": r["link"],
                                           "n": r["n"], "p": price, "it": [[r["id"], r["n"], price, night, 0, 0]], **({"ph": 1} if ph else {})}  # 품절 지켜보기(진우 예약 글과 같은 모양)
        print("toss pick", e["at"], clip(r["n"], 30), f"{price:,}원 게시")
        bt = th_beauty(r["n"])
        text = toss_th(info, r["n"], toss_price(x), lines, r["link"])
        if tok and TH_SLOTS:  # 슬롯 방식: 줄에 → 슬롯에 1순위로 골리면 나감
            th_queue(seen, text, r["link"], bt, img, (r["id"], x.get("tacaId")))
        elif tok and th_solo(seen, plain_of(body), fill=True, beauty=bt, slot=True):  # Threads 개별 글(하루 5개·45분 간격 같이 셈, 진우 화장품 이름 예약은 화장품 자리 채움): 대가성 문구 맨 앞, 실패는 main()이 알림
            th_mark(seen, bt)
            me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
            th_deal(seen, tok, me, text, r["link"], image=img, tids=(r["id"], x.get("tacaId")))


TOSS_PHOTO, TOSS_NOIMG, PHOTO_CREDIT = True, "toss_noimg.txt", "사진: 토스쇼핑"  # 토스 개별 글 상품 사진(10/26 Cowork·진우 '바로 진행' — 승인 채널 = 텔레그램 sendPhoto·Threads 사진 글만 · 인스타·사이트 X · 글 끝 '사진: 토스쇼핑'):
# 토스 이미지 기준 = 썸네일(thumbnailUrl) 원본 주소 그대로(자르기·여백·글자·합성·우리 서버에 다시 그리기 X) · '이미지 사용 금지' 상품 X(API 응답에 그 표시 없음 -> toss_noimg.txt 수동) · 셀러 요청 = 내림(toss_takedown)
# toss_noimg.txt = 사진 안 쓸 상품(tacaItemId·tacaId 줄마다) — 넣으면 다음 글부터 사진 X + 이미 나간 그 상품 사진 글: 텔레그램 = 지움(못 지우면 링크) · Threads = 링크 목록(진우가 앱에서) -> 관리봇
TPH_KEEP = 30 * 86400  # 토스 사진 글 기록(상품 id -> 텔레그램 message_id·Threads id) 보관 — 셀러 요청 내림용


def toss_noimg():
    """toss_noimg.txt 상품 id들(줄마다 · '#' 뒤 = 메모)."""
    try:
        return {l.split("#")[0].strip() for l in open(TOSS_NOIMG, encoding="utf-8")} - {""}
    except OSError:
        return set()


def toss_photo(x):
    """토스 상품 썸네일 주소(원본 그대로) / TOSS_PHOTO 꺼짐·https 아님·toss_noimg.txt에 있는 상품 = None. 상세 응답 필드 이름은 실행마다 1번 로그(값 X — 이미지 사용 금지 표시가 생기는지 확인용)."""
    if TOSS_PHOTO and isinstance(x, dict) and not RUN.get("tkeys"):
        RUN["tkeys"] = 1
        print("toss 상품 필드", ",".join(sorted(x)))
    u = x.get("thumbnailUrl") if TOSS_PHOTO and isinstance(x, dict) else None
    if not (isinstance(u, str) and u.startswith("https://") and not re.search(r"\s", u)):
        return None
    return None if {str(x.get("tacaItemId")), str(x.get("tacaId"))} & toss_noimg() else u


def tph_log(seen, ids, **ref):
    """토스 사진 글 기록: ids = (tacaItemId, tacaId) · ref = tg=message_id 또는 th=Threads 글 id -> seen tphoto(TPH_KEEP)."""
    now = time.time()
    st = seen.setdefault("tphoto", {"t": now, "m": []})
    st["t"], st["m"] = now, [r for r in st["m"] if now - r["t"] < TPH_KEEP] + [{"t": now, "ids": [str(i) for i in ids if i], **ref}]


def toss_takedown(seen):
    """셀러 요청 내림(10/26 Cowork): toss_noimg.txt에 든 상품의 사진 글 -> 텔레그램 = deleteMessage(품절 지켜보기도 그만) · 못 지움(48시간 지남 등)·Threads = 링크를 관리봇으로(진우가 앱에서) · 상품당 1번."""
    st, no = seen.get("tphoto"), toss_noimg()
    if not st or not no:
        return
    st["t"] = time.time()  # 사진 글을 안 올리는 날에도 기록 유지(seen 3일 정리)
    hit = [r for r in st["m"] if set(r["ids"]) & no]
    if not hit:
        return
    st["m"] = [r for r in st["m"] if r not in hit]
    left, tok = [], E.get("THREADS_TOKEN")
    for r in hit:
        if "tg" in r:
            if tg("deleteMessage", chat_id=CHANNEL, message_id=r["tg"]):
                seen.pop(f"sold_{r['tg']}", None)
                continue
            left.append(f"텔레그램 t.me/{CHANNEL.lstrip('@')}/{r['tg']}")
        elif "th" in r:
            try:
                left.append("Threads " + json.loads(http(f"{THREADS}/{r['th']}?fields=permalink&access_token={tok}")).get("permalink", r["th"]))
            except Exception:
                left.append(f"Threads 글 id {r['th']}")
    print("toss 사진 내림", len(hit), "개 · 남은 것", len(left))
    if left:
        tg("sendMessage", chat_id=ADMIN, text="🖼 토스 사진 내림(toss_noimg.txt) — 봇이 못 지운 글이에요. 앱에서 지워 주세요\n" + "\n".join(left), link_preview_options={"is_disabled": True})


def tg_toss(text, kb, photo):
    """토스 개별 글 채널 게시 -> (메시지, 사진 글?): 사진 = sendPhoto(캡션 = 글 + '사진: 토스쇼핑' — 1,024자 넘거나 실패 = 지금처럼 글만, 그 실패는 알림 X)."""
    cap = f"{text}\n\n{PHOTO_CREDIT}"
    if photo and len(plain_of(cap).encode("utf-16-le")) // 2 <= 1024:
        m = tg("sendPhoto", chat_id=CHANNEL, photo=photo, caption=cap, parse_mode="HTML", reply_markup=kb)
        if m:
            return m, True
        fail = [k for k in RUN["fail"] if k.startswith("sendPhoto")]
    else:
        fail = []
    m = tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True}, text=text, reply_markup=kb)
    if m and fail:  # 글만으로 올라감 = 사진 실패는 알림 X
        for k in fail:
            RUN["fail"].pop(k, None)
        RUN["tg_err"] = "" if not RUN["fail"] else RUN["tg_err"]
    return m, False


TOSS_SOLO_HOURS = range(0, 24)  # 10/13 22:30 진우 '토스 쇼핑에서 추출해서 자동으로 올려줘' -> '매시 1개': 이 시각마다 토스 API 상품 개별 글 1개(10/22 진우 '새벽에도' -> 0~8시도, 밤 발송은 무음). () = 끔
TOSS_GAP_MIN, TOSS_GAP_NIGHT, TOSS_EV_PAD = 30, 60, 10 * 60  # 10/15 진우 '꾸준하게': 그 시각들에 채널 딜 글이 마지막 글 뒤 30분(0~8시는 60분, 10/22) 넘게 없으면 그 실행에 1개 더(빈틈 채움, 0 = 끔) · 진우 예약(events.json) 시각 앞뒤 10분이면 그 실행은 쉼(예약 먼저 — 예전 '예약 있는 시각 통째로 건너뜀' 대신)
TOSS_SOLO_SRC, TOSS_SOLO_MIN, TOSS_SOLO_TRY = ("best", "beauty", "life", "day"), 7, 2  # 시각마다 돌아가며(많이 팔린 순위 -> 화장품 -> 생필품 -> 하루특가) · 점수 7↑ · 출처 2곳까지(Claude·API 아낌)
TOSS_SITE = False  # 10/24 10:0x 보류(Cowork 확인: API 데이터로 사이트 전시 = 10/6 신청서 범위 밖) — 토스는 쉐어링크 웹에서 진우 계정으로 만든 링크를 events shelf로(진우 직접 링크와 같은 방식). True = 토스 API 개별 글 + toss_shelf 대량 진열도 사이트에(toss_site — 사이트 전용, 리뷰 수·평점 X)
TOSS_SHELF_RUN = 10  # 토스 사이트 진열: 실행마다 새로 진열하는 상품 수(쉐어링크 발급 = API 호출, 하루 상한 X) — shortcut: 공식 호출 상한 문서 없음 -> 오류 응답이면 그 상품은 하루 쉬고 그 실행은 멈춤
TOSS_STEADY_HOURS = (10, 15, 20)  # 10/23 진우 '특가는 끝났지만 꾸준하게 팔리는 상품들 올려줘 — 꾸준하게 제품 올라오는 게 좋지': 이 시각 매시 글은 진우 토스 꾸준템(own_end) 먼저(하루 3개까지, 같은 상품 3일 간격 tb_)
SOLO_PROMPT = SPECIAL_PROMPT.replace("특가 후보 목록이야(할인율 높고 리뷰 있는 상품, ", "상품 목록이야(") + TOSS_EASE + "\ncomment는 단위가격·구성 같은 사실 한 줄만.\n"


def kst_ts(at):
    """'YYYY-MM-DD HH:MM'(KST) -> epoch."""
    return datetime.strptime(at[:16], "%Y-%m-%d %H:%M").replace(tzinfo=KST).timestamp()


def ch_last(seen):
    """텔레그램 채널 마지막 딜 글 시각(epoch): 이번 실행(RUN) · 지난 실행 기록(seen) · posts.json 마지막 딜(토스 API 글은 posts.json에 없어서 기록이 주, 첫 배포 땐 posts.json)."""
    t = max((p["t"] for p in load(POSTS, []) if not p["text"].startswith("📋") and not p.get("shelf")), default="")
    return max(RUN["ch_last"], seen.get("ch_last", {}).get("t", 0), t and kst_ts(t) or 0)


def toss_site(seen, x, link, text):
    """토스 API 상품 -> 사이트 전용 글(TOSS_SITE, 10/24 진우 '웹사이트엔 최대한 많은 수량'): posts.json에 own·shelf·tid 1번(같은 상품 id·링크 진우 글이 있으면 X)
    = 사이트 몰·품목 칸·상품 페이지·사이트맵, 채널·Threads·인스타·모아보기 X(shelf) · 리뷰 수·평점 X(가격·게시 시점만) · 진열 규칙 그대로(own_end: 판매 중 유지·⏳·🔁 —
    상품 그룹 id를 tossid에 미리 넣어 단축 링크를 안 풂)."""
    if any(p.get("tid") == x["tacaItemId"] or p.get("own") and p.get("url") == link for p in load(POSTS, [])):
        return False
    record(re.sub(r" · ⭐ [\d.]+ \([\d,]+\)", "", text), [], link, extra={"own": 1, "shelf": 1, "tid": x["tacaItemId"]})
    if x.get("tacaId"):
        seen.setdefault("tossid", {"m": {}})["m"].setdefault(link, [int(x["tacaId"]), time.time(), 0])
    return True


def toss_shelf(seen):
    """토스 대량 사이트 진열(10/24 진우 '하루특가·BEST(카테고리별) API 목록 -> 쉐어링크 -> 사이트 전용 진열, API가 허용하는 만큼'): 실행마다 목록 1곳(하루특가 -> 많이 팔린 순위 ->
    카테고리 베스트들, 돌아가며) 중 사이트에 없는·판매 중 상품을 TOSS_SHELF_RUN개까지 -> 쉐어링크(만든 것 있으면 재사용) -> toss_site. 글 = 토스 개별 글 틀(대가성 문구·💙 머리 줄·
    가격(할인)·게시 시점 가격 — 다른 몰 비교·리뷰 X). 토스 점검(재사용 모드)·키 없음·TOSS_SITE False면 X. 링크 오류 = 그 상품 하루 쉬고 그 실행 멈춤."""
    if not (TOSS_SITE and HAS_TOSS) or RUN.get("treuse"):
        return
    now, st = time.time(), seen.setdefault("tshelf", {"i": 0, "x": {}})
    st["t"], st["x"] = now, {k: t for k, t in st.get("x", {}).items() if now - t < 86400}
    have = {p.get("tid") for p in load(POSTS, []) if p.get("tid")}
    try:
        tree = toss("/categories")["categories"]  # 트리 조회는 일 상한 차감 없음
        srcs = [("하루특가 · 밤 12시까지", "/products/today-deals?size=30"), ("많이 팔린 순위 {}위", "/products/best-selling?size=30")] \
            + [(f"{c['displayName']} 베스트 {{}}위", f"/products/best-categories/{c['categoryId']}?size=30") for c in tree]
        info, path = srcs[st["i"] % len(srcs)]
        st["i"] += 1
        raw = toss(path)["items"]
    except Exception as e:  # 터널 끊김 등 = 다음 실행에
        print("toss shelf", repr(e))
        return
    n, links = 0, seen.get("tlink", {}).get("m", {})
    for r, x in enumerate(raw):
        if n >= TOSS_SHELF_RUN:
            break
        if x.get("isSoldOut") or x["tacaItemId"] in have or str(x["tacaItemId"]) in st["x"]:
            continue
        try:
            link = (links.get(str(x["tacaItemId"])) or [None])[0] or toss_link(seen, x["tacaItemId"], x["displayName"])
        except Exception as e:  # 발급 제한 상품·호출 제한·접속 = 그 상품 하루 쉬고 이 실행은 멈춤
            print("toss shelf link", x["tacaItemId"], repr(e))
            st["x"][str(x["tacaItemId"])] = now
            break
        body = mall_body("toss", info.format(r + 1), "🔥", x["displayName"], toss_price({**x, "reviewCount": 0}), [toss_when()])
        if toss_site(seen, x, link, html_ents(ad_head(TOSS_NOTE, plain_of(body)) + body)[0]):
            n += 1
        have.add(x["tacaItemId"])
    print("toss shelf", f"{info.format('N')} · 사이트 진열 {n}개")


AT_RX = r"\d{4}-\d\d-\d\d ([01]\d|2[0-3]):[0-5]\d$"  # events at 모양(이 모양만 시각 계산 — 틀린 줄 하나가 단계를 멈추지 않게)


def ev_near(seen, now, evs=None):
    """진우 예약(events.json) 시각 앞뒤 TOSS_EV_PAD 안인지 — 진우 것 먼저(예약은 실행 간격만큼 늦게 나가서 실제 게시 시각으로도). 자동 글(toss_solo·cp_repost)은 이때 쉼."""
    ats = [e["at"] for e in (load(EVENTS, []) if evs is None else evs) if re.match(AT_RX, e.get("at", ""))]  # 손으로 넣은 시각 모양이 틀려도 멈추지 않게
    return any(abs(kst_ts(a) - now) <= TOSS_EV_PAD or now - seen.get("ev_" + a, 0) <= TOSS_EV_PAD for a in ats)


def toss_solo(seen):
    """토스 API 상품 개별 글(진우 토스 예약 글과 같은 틀): TOSS_SOLO_HOURS 매시 첫 실행에 1개 + 채널 딜 글이 TOSS_GAP_MIN분 넘게 없으면 그 실행에 1개(빈틈 채움, 못 찾으면 TOSS_GAP_MIN 뒤 다시).
    진우 예약(events.json) 시각 앞뒤 TOSS_EV_PAD 안이면 이번 실행은 쉼(기록 X -> 다음 실행에 다시).
    후보 = 그 시각 출처 목록 1번(30개, 순위 그대로) 중 품절·3일 안 게시(tb_)·오늘 진우 예약 이름·이름 예약 id 빼고 Claude 7점↑ 최고점. 텔레그램 채널 글 + 품절 지켜보기 + Threads 채움 후보(thtoss).
    사이트·posts.json X(API 범위). 묶음 회차는 tb_로 이 상품을 뺌."""
    now, kst = time.time(), time.gmtime(time.time() + 9 * 3600)
    h, key, today = kst.tm_hour, time.strftime("tsolo_%Y%m%d_%H", kst), time.strftime("%Y-%m-%d", kst)
    if not HAS_TOSS or h not in TOSS_SOLO_HOURS:
        return
    gap = TOSS_GAP_MIN and int(now - max(ch_last(seen), seen.get("tgap", {}).get("t", 0))) // 60
    gap = gap if gap > (TOSS_GAP_NIGHT if h < 8 else TOSS_GAP_MIN) else 0
    if key in seen and not gap:
        return
    evs, norm = load(EVENTS, []), lambda s: re.sub(r"\W", "", s or "")
    if ev_near(seen, now, evs):
        print(f"toss solo {h:02d}: 쉼(진우 예약 앞뒤 {TOSS_EV_PAD // 60}분)")
        return
    if gap:
        seen["tgap"] = {"t": now}  # 빈틈 채움 시도 — 못 찾아도 TOSS_GAP_MIN 동안 다시 안 찾음(API·Claude 아낌)
    since = time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 9 * 3600 - 86400))
    recent = lambda at: at[:10] == today or at >= since  # 오늘 + 지난 24시간(밤 12시 넘어 어젯밤 진우 예약 상품이 다시 나가지 않게 — 10/22 0~8시 글 켜며)
    booked = {norm(e["name"]) for e in evs if e.get("name") and recent(e.get("at", ""))}
    ti = seen.get("tossid", {}).get("m", {})
    booked_id = {x for e in evs if e.get("url") in ti and recent(e.get("at", "")) for x in (("g", ti[e["url"]][0]), ti[e["url"]][7] if len(ti[e["url"]]) > 7 else 0) if x and x != ("g", 0)}  # 같은 상품 = 토스 id 기준(10/23 진우 — 옵션 id·상품 그룹 id)
    picked = {v.get("id") for k, v in seen.items() if k.startswith("pk_") and recent(k[3:]) and isinstance(v, dict)}
    tree, tried, best, tops = None, 0, None, top_toss(seen, now)  # tops = 잘 된 토스 상품(top.json) — 후보면 +TOP_BONUS점(하루 TOP_BONUS_DAY번)
    fill = key in seen  # 매시 글은 이미 = 이번은 빈틈 채움
    for src in (["rehot"] if fill else []) + (["steady"] if h in TOSS_STEADY_HOURS and not fill else []) + [TOSS_SOLO_SRC[(h + n) % len(TOSS_SOLO_SRC)] for n in range(len(TOSS_SOLO_SRC))] \
            + ([] if fill else ["rehot"]) + (["stock"] if RUN.get("treuse") else []):  # 🔁 다시 특가 = 빈틈 채움엔 먼저, 매시 글엔 새 상품 뒤(10/23 진우 '🔥 새 상품보다 뒤 칸') · 토스 점검 = 마지막에 보관 링크 상품(stock)도
        if src == "day" and (h < 9 or h == 23 and kst.tm_min >= 30) or tried >= TOSS_SOLO_TRY and src not in ("stock", "rehot"):  # 하루특가 목록은 9시에 바뀜(그 전엔 어제 것) · 23:30 넘으면 '밤 12시까지'가 몇 분 안 남음
            continue
        label = None
        if src == "stock":  # 3일 안 안 올린 보관 링크 상품 최근 것 30개 -> 상세로 지금 가격·품절(순위는 옛 것이라 머리 줄 출처 X)
            ids = [i for i, _ in sorted(seen.get("tlink", {}).get("m", {}).items(), key=lambda kv: -kv[1][1]) if f"tb_{i}" not in seen]
            ids = (ids[(kst.tm_yday * 24 + h) * 30 % len(ids):] + ids)[:30] if ids else []  # 시각마다 다음 30개(같은 30개만 보지 않게 — 10/22 리뷰)
            raw = toss("/products/detail?tacaItemIds=" + ",".join(ids))["items"] if ids else []
        elif src in ("steady", "rehot"):  # 진우 토스 상품 다시 올리기(링크 = 진우 쉐어링크 — 점검 땐 재사용 모드 그대로, 같은 상품 3일 tb_):
            # steady = 10/23 진우 '특가는 끝났지만 꾸준하게 팔리는 상품' — own_end ⏳ 특가 대기 + 👍 꾸준템, 정가 글이라 '지금은 특가 아님 · 특가 때 M원' 한 줄
            # rehot = '나중에 특가가 되면 다시 특가 제품으로' — own_end가 ⏳ -> 🔥로 본 것(seen rehot), 지금 가격이 목표가 +5% 안일 때만 '🔁 다시 특가'(Claude 점수 없이)
            ti, last = seen.get("tossid", {}).get("m", {}), {}
            for q in load(POSTS, []):
                if q.get("own") and toss_share(q.get("url")) and not q.get("shelf"):
                    last[q["url"]] = q
            jw = {ti[u][7]: (u, q.get("tgt", "")) for u, q in last.items() if q.get("st") == "wait" and q.get("stdy") and len(ti.get(u, [])) > 7 and ti[u][7]} if src == "steady" \
                else {q["id"]: (q["u"], q["tgt"]) for q in seen.get("rehot", {}).get("q", [])}
            jw = {i: x for i, x in jw.items() if f"tb_{i}" not in seen}
            ids = list(dict.fromkeys(list(jw)[(kst.tm_yday * 24 + h) * 30 % len(jw):] + list(jw)))[:30] if jw else []  # 시각마다 다음 30개(끝에서 처음으로 이어서, 같은 id 두 번 X)
            near = lambda x: (lambda w: w[0] and x["displayPrice"] <= (w[0] + w[1]) * (100 + OWN_HOT_PCT) / 100)(won_of(jw[x["tacaItemId"]][1]))
            raw = [x for x in toss("/products/detail?tacaItemIds=" + ",".join(map(str, ids)))["items"] if (toss_steady(x) and not near(x) if src == "steady" else near(x))] if ids else []  # 다시 특가 가격이면 꾸준템 글 X(own_end가 🔁로 — 10/23 리뷰)
            if not raw:
                continue
            label = "꾸준히 팔리는 상품" if src == "steady" else "🔁 다시 특가"
        elif src in ("beauty", "life"):
            tree = tree or toss("/categories")["categories"]  # 트리 조회는 일 상한 차감 없음
            cs = [c for c in tree if (re.search("뷰티|화장품", c["displayName"]) if src == "beauty" else c["displayName"] in TOSS_CATS)]
            if not cs:
                continue
            c = cs[h % len(cs)]  # 생필품 = 식품·생활용품 번갈아
            raw, label = toss(f"/products/best-categories/{c['categoryId']}?size=30")["items"], "뷰티 베스트" if src == "beauty" else "생필품 베스트"
        else:
            raw = toss(f"/products/{'best-selling' if src == 'best' else 'today-deals'}?size=30")["items"]
        tried += 1
        items = [(r + 1, x) for r, x in enumerate(raw) if not x.get("isSoldOut") and f"tb_{x['tacaItemId']}" not in seen and (src in ("steady", "rehot") or toss_ok(seen, x["tacaItemId"]))
                 and norm(x["displayName"]) not in booked and x["tacaItemId"] not in picked | booked_id and ("g", x.get("tacaId")) not in booked_id]
        tone, tsuf = tone_ask(seen, "ch") if items and src != "rehot" else (0, "")
        picks = [{"i": 0, "score": 10}] if src == "rehot" and items else [p for p in (items and ai_pick(SOLO_PROMPT + tsuf, [f"{x['displayName']} | {x['displayPrice']:,}원 ({x.get('discountRate', 0)}% 할인)"
                                                               + (f" | 리뷰 {x.get('reviewScore')}점 {x['reviewCount']:,}개" if x.get("reviewCount") else "") for _, x in items]) or []) if 0 <= p["i"] < len(items)]
        for p in picks:  # 10/22 Cowork: 잘 된 토스 상품(판매 중·3일 지남 = 위 품절·tb_ 거름 그대로)은 +TOP_BONUS점
            if top_hit(tops, items[p["i"]][1]["tacaItemId"], items[p["i"]][1]["displayName"]):
                p.update(score=p["score"] + TOP_BONUS, top=1)
            if src != "rehot" and toss_freq(items[p["i"]][1]):  # S: 여성 기본템·식재료 소모품·묶음 +1
                p.update(score=p["score"] + TOSS_FREQ_BONUS, fq=1)
        picks = [p for p in picks if p["score"] >= TOSS_SOLO_MIN]
        if picks:
            best = (src, label, max(picks, key=lambda p: (p["score"], p.get("top", 0))), tone)  # 같은 점수면 잘 된 상품
            break
    if not best:
        seen[key] = now
        print(f"toss solo {h:02d}{f' 빈틈 {gap}분' if gap else ''}: 7점↑ 없음(출처 {tried}곳)")
        return
    src, label, p, tone = best
    rank, x = items[p["i"]]
    name, price = x["displayName"], x["displayPrice"]
    link = jw[x["tacaItemId"]][0] if src in ("steady", "rehot") else toss_link(seen, x["tacaItemId"], name)  # 진우 상품 = 진우 쉐어링크 그대로
    if not link:  # 토스 점검인데 보관 링크 없음(위에서 걸러서 거의 없음) -> 이 시각은 끝
        seen[key] = now
        return
    info = "하루특가 · 밤 12시까지" if src == "day" else f"많이 팔린 순위 {rank}위" if src == "best" else label if src in ("steady", "rehot") else f"{label} {rank}위" if label else ""  # 머리 줄 출처(10/22 진우 시안 '생필품 베스트 3위')
    icon = "👍" if src == "steady" else "🔥"  # 👍 꾸준템(Threads 순서·리스트 규칙 = th_steady)
    tgt = jw[x["tacaItemId"]][1] if src in ("steady", "rehot") else ""
    lines = [f"🔁 특가 때 {tgt} 가격으로 다시 왔어요" if (lambda w: w[0] and price <= w[0] + w[1])(won_of(tgt)) else f"🔁 특가 때({tgt}) 가격 근처로 다시 내려왔어요"] if src == "rehot" else toss_ul(x) + toss_lines(p) + ([f"지금은 특가 아님 · 특가 때 {tgt}"] if src == "steady" and tgt else [])  # 🙋 누가·👍 언제(10/20 a7cee6f 그대로) · 정가 재게시는 정직하게(10/23 진우)
    body = mall_body("toss", info, icon, name, toss_price(x), list(map(esc, lines)) + [toss_when()])  # 10/22 진우 '토스·쿠팡 한눈에': 💙 토스 특가 · 출처 → 상품명 → 가격 (할인) · ⭐ → 🙋 → 게시 시점 가격
    head, btn = ad_head(TOSS_NOTE, plain_of(body)), mall_btn("toss", f"{price:,}원")
    img = toss_photo(x)
    m, ph = tg_toss(head + body, {"inline_keyboard": [[{"text": btn, "url": link}]]}, img)
    if not m:
        return  # 다음 실행에 다시(실패는 바로 알림)
    if ph:
        tph_log(seen, (x["tacaItemId"], x.get("tacaId")), tg=m["message_id"])
    seen[key] = now
    tone_keep(seen, "ch", tone)
    seen[f"tb_{x['tacaItemId']}"] = {"t": now, "n": name}  # 3일 동안 묶음 회차·다음 개별 글에서 빠짐
    if src == "rehot":
        seen["rehot"]["q"] = [q for q in seen["rehot"]["q"] if q["id"] != x["tacaItemId"]]
    if p.get("top"):
        top_mark(seen, now, x["tacaItemId"])
    if TOSS_SITE and src not in ("steady", "rehot"):  # 진우 토스 상품(꾸준템·다시 특가)은 진우 글이 이미 사이트에
        toss_site(seen, x, link, html_ents(head + body)[0])
    bundled(seen)
    seen[f"sold_{m['message_id']}"] = {"t": now, "d": today, "k": "ev", "pre": head, "body": body, "btn": btn, "url": link, "n": name, "p": price,
                                       "it": [[x["tacaItemId"], name, price, int(src == "day"), 0, 0]], **({"ph": 1} if ph else {})}  # 품절 지켜보기(진우 예약 글과 같은 모양) · ph = 사진 글(캡션 고침)
    if E.get("THREADS_TOKEN"):  # Threads = 채움 후보(45분 간격·화장품 한도 그대로)
        seen["thtoss"] = {"t": now, "q": [q for q in seen.get("thtoss", {}).get("q", []) if now - q["t"] < 3 * 3600] + [
            {"t": now, "l": False, "id": x["tacaItemId"], "n": name, "k": "solo", "r": 0, "s": p["score"] - TOP_BONUS * bool(p.get("top")), "bt": th_beauty(name), "text": toss_th(info, name, toss_price(x), lines, link, icon), "link": link, **({"img": img, "tids": [x["tacaItemId"], x.get("tacaId")]} if img else {})}]}
    print(f"toss solo {h:02d}{f' 빈틈 {gap}분' if gap else ''}: {clip(name, 30)} ({src} {rank}위 · {p['score']}점{' · 잘 된 상품 +' + str(TOP_BONUS) if p.get('top') else ''}{' · 자주 사는 상품 +' + str(TOSS_FREQ_BONUS) if p.get('fq') else ''})")


SOLD = ([None, ("⛔ <b>품절</b> — 다시 들어오면 답글로 알려드릴게요", "품절"), ("⛔ <b>품절</b>", "품절")],  # [하루특가 아님 / 하루특가][상태 1 = 품절, 2 = 끝]: (글 줄, 버튼 글자)
        [None, ("⛔ <b>품절</b> — 밤 12시부터 다시 살 수 있어요", "품절 · 밤 12시 재오픈"), ("⛔ <b>특가 끝</b> — 이 가격으로는 다시 안 열렸어요", "특가 끝")])  # 토스 화면 '품절 · 밤 12시부터 구매할 수 있어요'(10/11 진한다시)
SOLD_EDITS = 8  # 한 실행에 고치는 채널 글 수(텔레그램 채널 분당 약 20개 — 밤 12시에 한꺼번에 열려도 나머지는 다음 실행에)


def ev_head(ev):
    """예약 글 머리: 상품 딜(deal)이고 제휴 링크면 [광고] 첫 줄 + 고지문, 행사 알림 등은 고지문만(예전 그대로)."""
    note = aff_note(ev["url"])
    return ad_head(note, plain_of(ev["text"])) if ev.get("deal") else (f"<i>{note}</i>\n\n" if note else "")


def ev_view(ev):
    """예약 글(events.json) -> 채널에 나가는 (본문 HTML, 버튼 글자): 토스·쿠팡 상품 딜(deal)이면 몰별 틀 — 예전 틀로 쓴 글('🔥 <b>[쿠팡] …</b>')은 mall_view로 바꾸고
    (몰별 틀로 쓴 글은 그대로), 🛒 버튼('🛒 구매하러 가기'·'🛒 N원 구매하기')은 '💙 토스에서 N원'·'🚀 쿠팡에서 N원'(가격 = 버튼 → 제목, 모르면 '… 보기'). 그 밖 = 그대로."""
    text, btn = ev.get("text", ""), ev.get("button", "🛒 구매하기")
    if not ev.get("deal"):
        return text, btn
    text = mall_view(text, ev.get("url"))
    t = title_of(plain_of(text))
    mall, won = mall_of(ev.get("url"), t), re.search(r"\d[\d,]*\s*원", btn)
    return text, mall_btn(mall, won[0] if won else parse(t)[2], cp_rocket(plain_of(text))) if mall and btn.startswith(("🛒", "🚀 쿠팡에서", "📦 쿠팡에서")) else btn  # 쿠팡 🚀/📦 = 머리 줄과 같게(예약에 써 둔 '🚀 쿠팡에서'도)


def sold_ev(ev, day):
    """진우 예약 글(토스 쉐어링크 + 상품명) -> 품절 지켜보기 항목(채널에 나간 본문·버튼 = ev_view). 가격 = 버튼 'N원', 없으면 본문 첫 'N원'(그래도 없으면 id 찾을 때 API 가격)."""
    body, btn = ev_view(ev)
    note, won = aff_note(ev["url"]), re.search(r"([\d,]+)원", btn) or re.search(r"([\d,]+)원", body)
    return {"t": time.time(), "d": day, "k": "ev", "pre": ev_head(ev), "body": body, "btn": btn,
            "url": ev["url"], "n": ev["name"], "p": int(won[1].replace(",", "")) if won else 0, "it": []}


def sold_render(w):
    """품절 지켜보는 채널 글 -> (HTML, 버튼). 진우 예약 글(ev) = 대가성 문구 바로 아래 한 줄, API 묶음 글(top) = 그 상품 아래 한 줄. 버튼은 글자만 바꾸고 링크는 그대로."""
    if w["k"] == "ev":
        s = w["it"] and w["it"][0][4] and SOLD[w["it"][0][3]][w["it"][0][4]]
        return w["pre"] + (s[0] + "\n\n" if s else "") + w["body"], [[{"text": s[1] if s else w["btn"], "url": w["url"]}]]
    text, kb = top_post(w["head"], [(n, link, lines + [SOLD[x[3]][x[4]][0]] if x[4] else lines) for (n, link, lines), x in zip(w["rows"], w["it"])])
    for i, x in enumerate(w["it"]):
        if x[4]:
            kb[i][0]["text"] = f"{NUM[i]} {SOLD[x[3]][x[4]][1]}"
    tail = w["tail"] if "tail" in w else f"\n\n{toss_when(time.strftime('%Y-%m-%d %H:%M', time.gmtime(w['t'] + 9 * 3600)))}" if TOSS_NO_CMP else ""  # 꼬리 없는 배포 전 기록 = 그 글 시각으로
    return w["pre"] + text + tail, kb


def toss_daymap(seen, now, today, need):
    """오늘 하루특가 목록 전체(커서 페이지) -> seen["soldmap"] = {"m": {이름(기호·띄어쓰기 뺌): [id, 가격]}}. 목록은 그날만(endAt = 밤 12시),
    need면 받음: 하루 최대 3번(처음 + 못 찾은 게 있으면 2시간 뒤), 실패해도 받은 만큼 저장(부르는 쪽 확인은 계속)."""
    norm = lambda s: re.sub(r"\W", "", s or "")
    if seen.get("soldmap", {}).get("d") != today:
        seen.pop("soldmap", None)
    sm = seen.get("soldmap")
    if need and (not sm or (sm["n"] < 3 and now - sm["t"] > 7200)):
        got, cur = dict(sm["m"]) if sm else {}, None
        try:
            for _ in range(10):
                r = toss("/products/today-deals?size=30" + (f"&cursor={urllib.parse.quote(str(cur), safe='')}" if cur else ""))
                got.update({norm(x["displayName"]): [x["tacaItemId"], x["displayPrice"], x["displayName"]] for x in r["items"]})  # 이름 그대로도(toss_picks 이름 찾기)
                cur = r.get("nextCursor")
                if not (r.get("hasNext") and cur):
                    break
        except Exception as e:
            print("toss soldout list", repr(e))
        sm = seen["soldmap"] = {"t": now, "d": today, "n": (sm["n"] if sm else 0) + 1, "m": got}
    return sm


def toss_soldout(seen):
    """오늘 올린 토스 글(API 묶음 + 진우 예약 중 API 상품과 이름이 같은 것)의 품절을 매 실행 상품 상세 API 1번(최대 30개, 오래 안 본 것부터)으로 다시 봄(10/11 진우 '품절 뜨는 경우는 속상해').
    품절 -> 채널 글 수정('⛔ 품절 — 밤 12시부터 다시 살 수 있어요' + 버튼 글자 '품절 · 밤 12시 재오픈', 링크는 그대로 — 진우 링크 안 뺌).
    다시 열림(올린 가격 이하) -> 그 글에 답글 '🔔 다시 열렸어요'(상품당 하루 1번) + 품절 줄 지움. 품절된 하루특가는 밤 12시 전엔 안 열려서 다시 안 보고,
    밤 12시 지나 한 번은 꼭 + 1시까지 봄 -> 그래도 안 열리면 '특가 끝 — 이 가격으로는 다시 안 열렸어요'로 바꾸고 그만 봄(토스 API 데이터 보관은 1일 이내).
    상태는 채널 글 수정이 성공해야 바꿈(실패하면 다음 실행에 다시, 3번 실패 = 지운 글 등 -> 그만 봄). Threads는 글 수정 API가 없어 채널만."""
    if not HAS_TOSS:
        return
    now, kst = time.time(), time.gmtime(time.time() + 9 * 3600)
    today, midnight = time.strftime("%Y-%m-%d", kst), now - (kst.tm_hour * 3600 + kst.tm_min * 60 + kst.tm_sec)  # 오늘 0시(KST)
    norm = lambda s: re.sub(r"\W", "", s or "")
    evs = [e for e in load(EVENTS, []) if e.get("name") and toss_share(e.get("url")) and e["at"].startswith(today) and "ev_" + e["at"] in seen]
    own = [p for p in load(POSTS, []) if p["t"].startswith(today) and p.get("mid") and p.get("own")]
    for ev in evs:  # events()가 지켜보기를 만들기 전(10/11 배포 전)에 나간 예약 글: 같은 링크가 오늘 예약·글 모두 1개일 때만 그 글 번호로(다른 글에 잘못 붙지 않게)
        ps = [p for p in own if p.get("url") == ev["url"]]
        if len(ps) == 1 and sum(e["url"] == ev["url"] for e in evs) == 1:
            seen.setdefault(f"sold_{ps[0]['mid']}", sold_ev(ev, today))
    need = [w for k, w in seen.items() if k.startswith("sold_") and w["k"] == "ev" and w["d"] == today and not w["it"] and not w.get("off")]
    ti = seen.get("tossid", {}).get("m", {})
    fresh = [w["url"] for w in need if w.get("url") and toss_share(w["url"]) and w["url"] not in ti][:OWN_END_RES]
    if fresh:  # 새 진우 링크 = 여기서 바로 풀어 둠(own_end는 이 단계 뒤 — 10/23 리뷰, 못 풀면 0 = 이름으로)
        tt = seen.setdefault("tossid", {"m": {}})
        tt["t"], ti = now, tt["m"]  # seen 정리(t 기준)
        for u in fresh:
            m = re.fullmatch(r"https://toss\.shopping/t/(\d+)", plain(u) or "")
            ti[u] = [int(m[1]) if m else 0, now, 0]
    for w in need:  # 10/23 진우 '같은 상품 짝짓기는 토스 상품 id 기준'(이름 비슷한 다른 구성과 안 섞이게): 진우 링크 -> id 먼저, 없으면 이름
        if len(ti.get(w.get("url"), [])) > 7 and ti[w["url"]][7]:  # 대표 옵션 id(own_end가 tacaIds로 확인한 것) — 주소 /t/번호(tacaId)는 상세 tacaItemIds가 아님
            w["it"] = [[ti[w["url"]][7], w["n"], w["p"] or 0, int(bool(re.search(DAY_ONLY, w.get("body", "")))), 0, 0]]
    need = [w for w in need if not w["it"]]
    sm = toss_daymap(seen, now, today, bool(need))
    if need and sm:  # 하루특가 목록에 없으면 toss_relink가 모아 둔 1일 목록(베스트·카테고리)에서 같은 이름
        cache = {norm(x[1]): [x[0], x[2]] for x in seen.get("tosscache", {}).get("items", []) if x[3] > now - 86400}
        for w in need:
            hit = sm["m"].get(norm(w["n"])) or cache.get(norm(w["n"]))
            if hit:
                w["it"] = [[hit[0], w["n"], w["p"] or hit[1], int(norm(w["n"]) in sm["m"]), 0, 0]]
    cand, fin = [], []  # (마지막 확인, 글, 상품 번호) / 끝 문구로 바꿀 글
    for k, w in [(k, w) for k, w in seen.items() if k.startswith("sold_")]:
        if w.get("off"):
            if w["d"] != today:
                del seen[k]
            continue
        if w["d"] == today:  # 오늘: 안 품절된 상품 + 하루특가 아닌 품절 상품(다시 들어올 수 있음). 품절된 하루특가는 밤 12시 전엔 안 열려서 안 봄(일 상한 아끼기)
            cand += [(x[5], k, i) for i, x in enumerate(w["it"]) if not x[4] or not x[3]]
            continue
        out = [i for i, x in enumerate(w["it"]) if x[4] == 1]
        if not out:
            del seen[k]
        elif kst.tm_hour < 1 or any(w["it"][i][5] < midnight for i in out):  # 밤 12시 지나 한 번은 꼭 보고(실행이 늦어도), 1시까지는 계속
            cand += [(w["it"][i][5], k, i) for i in out]
        else:
            fin.append(k)
    ids = list(dict.fromkeys(seen[k]["it"][i][0] for _, k, i in sorted(cand)))[:30]  # 상세 조회 한 번에 최대 30개(일 상한 = 받은 상품 10,000개)
    data, nf = {}, []
    if ids:
        r = toss("/products/detail?tacaItemIds=" + ",".join(map(str, ids)))
        data, nf = {x["tacaItemId"]: x for x in r["items"]}, r.get("notFoundIds") or []
    edits, n_out, n_back = 0, 0, 0
    for k in list(dict.fromkeys(k for _, k, _ in cand)) + fin:
        w = seen[k]
        new, opened = [list(x) for x in w["it"]], []
        for i, x in enumerate(new):
            if k in fin:
                x[4] = 2 if x[4] == 1 else x[4]
                continue
            d = data.get(x[0])
            if x[0] not in ids:
                continue
            x[5] = w["it"][i][5] = now if d else now + 7200  # 조회 안 되는 상품(판매 종료·페널티)은 2시간 뒤에(문서: 바로 재시도 X, 영구 제외 X)
            if not d:
                continue
            avail, cheap = not d.get("isSoldOut"), bool(x[2]) and d["displayPrice"] <= x[2]
            if not x[4] and not avail and w["d"] == today:
                x[4] = 1
            elif x[4] == 1 and avail and (cheap or not x[3]):  # 하루특가는 올린 가격 이하로 열려야 다시 열림(비싸지면 = 특가 끝), 다른 상품은 들어오면 품절 줄 지움
                x[4] = 0
                if cheap and i not in w.get("rp", []):
                    opened.append((i, d["displayPrice"]))
        if [x[4] for x in new] == [x[4] for x in w["it"]]:
            continue
        if edits >= SOLD_EDITS:  # 상태를 안 바꿨으니 다음 실행에 다시 잡힘
            continue
        edits += 1
        text, kb = sold_render({**w, "it": new})
        try:
            ok = (tg("editMessageCaption", chat_id=CHANNEL, message_id=int(k[5:]), caption=f"{text}\n\n{PHOTO_CREDIT}", parse_mode="HTML", reply_markup={"inline_keyboard": kb}) if w.get("ph")  # 사진 글 = 캡션
                  else tg("editMessageText", chat_id=CHANNEL, message_id=int(k[5:]), text=text, parse_mode="HTML", link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": kb}))
        except Exception as e:  # 네트워크 오류도 이 글만 건너뜀(다른 글·다른 단계는 계속)
            print("toss soldout edit", k, repr(e))
            ok = None
        if not ok:
            w["fail"] = w.get("fail", 0) + 1
            w["off"] = 1 if w["fail"] >= 3 else w.get("off")  # 지운 글 등 -> 그만 봄
            continue
        n_out += sum(x[4] == 1 and y[4] != 1 for x, y in zip(new, w["it"]))
        w["it"], w["fail"] = new, 0
        for i, price in opened:  # 답글 = 채널 알림(밤 0~8시는 tg()가 무음). 버튼 링크 = 원래 글과 같은 링크
            url = w["url"] if w["k"] == "ev" else w["rows"][i][1]
            note = aff_note(url)
            w.setdefault("rp", []).append(i)
            n_back += 1
            same = next((e for e in seen.get("reopen", {}).get("q", []) if e["id"] == new[i][0]), None)
            if w["d"] != today and E.get("THREADS_TOKEN") and (not same or (w["k"] == "ev" and same["k"] != "ev")):  # 밤 12시 지나 다시 열림 -> Threads 새 글도(toss_reopen, 10/11 진우)
                body = html.unescape(re.sub(r"<[^>]+>", "", w.get("body", "")))  # 진우 예약 글의 쿠팡 비교·단위가격 줄(💡·🤔) = 가격이 그대로일 때만 다시 씀
                cmp = html.unescape(re.sub(r"<[^>]+>", "", next((l for l in w.get("body", "").split("\n") if l[:1] in ("💡", "🤔") or l.startswith("💰") and "<b>" not in l), "")))  # 10/20~ 토스 단독 글 = 💰 단위가격 줄
                if re.search(r"오늘|어제|내일|오전|오후|아침|저녁|\d{1,2}시|\d{1,2}:\d{2}", cmp):  # '오늘 18시엔'처럼 날·시각이 든 줄은 다음 날 글에선 틀림 -> 빼고, 약한 딜이면 표시만
                    cmp = cmp.split(" — ")[0] if cmp.startswith("🤔") else ""
                ent = {"id": new[i][0], "n": new[i][1], "url": url, "p0": new[i][2], "icon": "🛒" if th_weak(body) else "🔥", "cmp": clip(cmp, 120), "k": w["k"], "day": today, "st": 0,
                       "title": body and parse(title_of(body))[1], "warn": next((l for l in body.split("\n") if l.startswith("⚠️")), "")}  # Threads 재오픈 글 제목·⚠️ 줄(진우 예약 글 그대로, 10/12 00:40)
                rq = seen.setdefault("reopen", {"t": now, "q": [], "ts": []})
                rq["t"] = now
                if same:  # 같은 상품이 봇 묶음 글에도 있었으면 진우 예약 글 것으로(진우 링크·비교 줄 — 진우 링크 안 뺌), 올렸는지는 그대로
                    same.update({x: v for x, v in ent.items() if x not in ("day", "st")})
                else:
                    rq["q"].append(ent)
            try:
                tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True}, reply_parameters={"message_id": int(k[5:])},
                   text=(f"<i>{note}</i>\n\n" if note else "") + f"🔔 <b>다시 열렸어요!</b> {esc(new[i][1])} — {price:,}원", reply_markup={"inline_keyboard": [[{"text": mall_btn("toss", f"{price:,}원"), "url": url}]]})
            except Exception as e:
                print("toss soldout reply", k, repr(e))
        if k in fin or (w["d"] != today and not any(x[4] == 1 for x in w["it"])):
            del seen[k]
    if ids or fin:
        evw = [w for k, w in seen.items() if k.startswith("sold_") and w["k"] == "ev" and w["d"] == today]
        print("toss soldout", len(ids), "checked", len(nf), "notfound", n_out, "out", n_back, "reopen", edits, "edits", f"| 진우 예약 id {sum(bool(w['it']) for w in evw)}/{len(evw)}")


REOPEN_WARN = "⚠️ 확인할 점: 사람마다 가격이 다를 수 있음 · 결제 전 최종가 확인"  # 진우 예약 글 ⚠️ 줄이 없거나 날·시각이 든 줄일 때(다음 날 글에선 틀림)


def reopen_text(seen, e, price, am, hot):
    """재오픈 Threads 글 = 일반 개별 글 틀 + 맨 위 '🔔 다시 열렸어요'(10/12 00:40·00:55 진우 — 0:02 샤워기 36분 조회 3, '🔔 줄은 좋아, 눈에 띄게'):
    고지문 → 머리 줄 '💙 토스 특가 · 🔔 다시 열렸어요 🔥'(10/22 몰별 틀) → 제목 → 지금 가격 → 💸 쿠팡보다 N원 싸요 → 정보 줄 '토스 하루특가 · 밤 12시 재오픈'(하루특가는 오늘 목록에 있을 때만) → 💡 비교 → ⚠️ 확인할 점
    → 👉 링크 → 👋 팔로우 → 📲. 아침 8시 글도 같은 틀(같은 상품 두 번째 글이라 🔔·정보 줄 끝만 조금 다르게 — 같은 글 반복은 Threads 스팸 표시 위험).
    제목·⚠️ 줄 = 진우 예약 글 본문(줄 세울 때 저장 — 품절 지켜보기 기록은 다시 열리면 지워짐; 그 전에 줄 선 것은 posts.json 글에서), 날·시각 든 ⚠️ 줄은 기본 문구.
    💡·💸는 가격이 그대로일 때만. 링크는 예전 그대로(그 글의 토스 링크)."""
    src = "" if e.get("title") else next((p["text"] for p in reversed(load(POSTS, [])) if p.get("url") == e["url"]), "")
    name = clip(e.get("title") or (src and parse(title_of(src))[1]) or e["n"], 60)
    warn = e.get("warn") or next((l for l in src.split("\n") if l.startswith("⚠️")), "")
    warn = REOPEN_WARN if not warn or re.search(r"오늘|어제|내일|오전|오후|아침|저녁|\d{1,2}시|\d{1,2}:\d{2}", warn) else warn
    info = ("토스 하루특가 · " if hot else "") + "밤 12시 재오픈" + (" · 아침에도 살 수 있어요" if am else "")
    cmp = e["cmp"] if e["cmp"] and price == e["p0"] else ""
    if TOSS_NO_CMP:  # 재오픈 = 토스 딜: 다른 몰 비교 X, 게시 시점 가격(10/12 토스 비즈니스 요청)
        cmp, warn = strip_cmp(cmp)[0], toss_when()
    sv = saving(cmp) if cmp.startswith("💡") else None
    main = "\n".join(x for x in (mall_head("toss", "🔔 다시 열렸어요" + (" · 아침 재알림" if am else ""), e["icon"]), name, f"{price:,}원",
                                  f"💸 {sv[0]}보다 {sv[1]} 싸요" if sv else "", info, cmp, warn) if x)[:280]  # 10/22 진우 '한눈에': 대가성 문구 다음 = 💙 머리 줄(🔔은 머리 줄 안)
    return th_note(TOSS_NOTE) + main \
        + f"\n\n👉 {e['url']}\n{th_follow(TOSS_NO_CMP and is_toss(e['url'], main))}\n📲 실시간 알림 t.me/hotdeal_pick"


def toss_reopen(seen):
    """품절됐던 토스 딜이 밤 12시 지나 다시 열리면(toss_soldout이 채널 답글과 함께 줄 세움) Threads에도 새 글 — 10/11 진우 '품절 풀리면 다시 쓰레드에 시간 맞춰서, 자정 + 아침 8시 둘 다'.
    0~6시 = 밤 글, 6~11시(TH_REOPEN_AM, 10/12 8시 -> 6시) = 같은 상품을 다시 확인해 아직 살 수 있으면 '☀️ 아침 재알림'(문구를 다르게 — 같은 글 반복은 Threads 스팸 표시 위험), 품절·조회 안 됨이면 안 올림.
    올리기 직전 상품 상세 API로 다시 확인: 가격 = 지금 가격(올린 가격보다 비싸면 특가 끝 -> 안 올림), '토스 하루특가·선착순'은 오늘 하루특가 목록에 있을 때만, 쿠팡 비교 줄은 가격이 그대로일 때만.
    몰림 방지: 재게시끼리 10분(TH_REOPEN_GAP, 실행당 1개) + 1시간 최대 TH_REOPEN_HOUR개 + 토스 묶음 글(채널·Threads)과 10분 -> 넘친 건 다음 실행에.
    한도(10/12 진우 (나)+(다)): 개별 글 하루 5개와 따로 밤 TH_REOPEN_NIGHT·아침 TH_REOPEN_MORN·하루 TH_REOPEN_DAY개, 45분 간격은 같이(Threads 글끼리), main에서 threads_deals 뒤 = 일반 딜이 먼저.
    줄에서 지금 올릴 수 있는(①② · 🛒 X) 첫 글을 고름 — 맨 앞이 약한 글이어도 뒤를 안 막음(4d9271a1부터 있던 것, 10/12 리뷰).
    실패는 기존 규칙(먼저 표시 -> 같은 글 다시 시도 안 함, 4279047은 첨부 없이 1번 더, main()이 하루 1번 알림). 토스 데이터는 그날만(다음 날·11시 지나면 버림)."""
    r = seen.get("reopen")
    if not r or not r["q"]:
        return
    now, kst = time.time(), time.gmtime(time.time() + 9 * 3600)
    today, am = time.strftime("%Y-%m-%d", kst), TH_REOPEN_AM[0] <= kst.tm_hour
    booked = {re.sub(r"\W", "", ev["name"]) for ev in load(EVENTS, []) if am and ev.get("name") and ev["at"].startswith(today)}  # 진우가 오늘 같은 상품을 다시 예약 -> 아침 재알림은 진우 글이 대신(toss_deals와 같은 규칙, 밤 글은 선착순이라 그대로)
    late = [e for e in r["q"] if e["day"] != today or kst.tm_hour >= TH_REOPEN_AM[1] or re.sub(r"\W", "", e["n"]) in booked]
    r["q"] = [e for e in r["q"] if e not in late]
    r["ts"] = [t for t in r.get("ts", []) if now - 3600 < t <= now]  # 최근 1시간 재게시 시각(시계가 뒤로 간 기록은 무시)
    if late:
        print("toss reopen 버림(지난 회차·진우 오늘 예약)", len(late))
    todo = [e for e in r["q"] if am or not e["st"]]  # 밤: 아직 안 올린 것만 / 아침: 전부(밤에 못 올린 건 아침 글 1개만)
    tok, mode = E.get("THREADS_TOKEN"), "am" if am else "night"
    if not todo or not tok or not HAS_TOSS or (r["ts"] and now - max(r["ts"]) < TH_REOPEN_GAP) or len(r["ts"]) >= TH_REOPEN_HOUR or busy(seen, cap=False) or not th_solo(seen, "", reopen=mode, gate=True):
        return  # 간격·한도가 안 되면 상품 조회도 안 함
    try:
        d = toss("/products/detail?tacaItemIds=" + ",".join(dict.fromkeys(str(e["id"]) for e in todo[:30])))
    except Exception as e:  # 터널 끊김 등 -> 다음 실행에(Threads 실패 알림 아님)
        print("toss reopen detail", repr(e))
        return
    data, live = {x["tacaItemId"]: x for x in d["items"]}, []
    for e in todo[:30]:
        x = data.get(e["id"])
        if not x or x.get("isSoldOut") or (e["p0"] and x["displayPrice"] > e["p0"]):  # 다시 품절·조회 안 됨·비싸짐(특가 끝) -> 밤 글은 건너뛰고 아침에 다시 봄, 아침이면 안 올림
            e["st"] = 1
            if am:
                r["q"].remove(e)
            continue
        live.append((e, x["displayPrice"]))
    ids = lambda: {v[0] for v in seen["soldmap"]["m"].values()} if seen.get("soldmap", {}).get("d") == today else set()
    for e, price in live:  # 올릴 수 있는 첫 글(①② · 🛒 X) — 약한 글은 건너뛰고 줄에 남김
        toss_daymap(seen, now, today, e["id"] not in ids())  # 오늘 목록이 없거나 그 상품이 없으면 받음(하루 3번·2시간 간격 규칙 그대로)
        hot = e["id"] in ids()  # 오늘 하루특가 목록에 있을 때만 '토스 하루특가'
        text = reopen_text(seen, e, price, am, hot)
        if th_solo(seen, text, fill=True, reopen=mode):
            break
    else:  # 올릴 게 없음 -> 이유를 로그로(10/12 아침 재오픈 0개가 로그로 안 보이던 것): 살 수 있는 것 중 ①② 없음(값이 바뀌어 쿠팡 비교 줄 빠짐·🛒 등) / 다 품절·비싸짐
        print("toss reopen", "아침" if am else "밤", f"줄 {len(todo)}개 중 살 수 있는 것 {len(live)}개 — " + ("①② 아님(값 바뀜·🛒 등)이라 안 올림" if live else "다 품절·비싸짐"))
        for e, _ in [] if am else live:  # 밤 = 아침에 다시(품절·비싸짐과 같이) — threads_deals가 토스 픽 칸을 비워 둔 채 밤새 기다리지 않게(10/22)
            e["st"] = 1
        return
    th_mark(seen, reopen=mode)
    e["st"] = 1  # 먼저 표시: 실패해도 같은 글 반복 시도 안 함(스팸 방지), 실패는 main()이 알림
    if am:
        r["q"].remove(e)
    r["t"] = now
    r["ts"].append(now)
    print("toss reopen", "아침" if am else "밤", clip(e["n"], 30), f"{price:,}원", "하루특가" if hot else "목록 없음", f"| 남은 {len(r['q'])}")
    me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
    th_deal(seen, tok, me, text, e["url"])


TH_LINK_AB, TH_AB_MARK = False, "👇 구매 링크는 첫 댓글에"  # 10/25 2주 비교 뒤 진우 결정 = A(본문 링크) 고정 — 48시간 조회 A 9.8(29개) > B 7.8(28개)+댓글 1.7, B 시험 끝(C·상황 3장면도 링크가 댓글이라 같이 쉼) · 10/18 18:30 진우 'Threads 개별 딜 글 링크 위치 A/B — 절반만 시험'(10/25 점검 때 비교해 이긴 쪽으로): False = 지금처럼 A만
TH_AB_URL = re.compile(r"https?://|t\.me/|\.kr(?![a-z])")  # B 본문에서 뺄 주소 든 줄(👉·🛒 링크, 📲 t.me)
TH_LINK_MAX = 300  # 10/19 17시 진우 '경유 링크 말고 직접 링크로': Threads 딜 링크 = 텔레그램 버튼 링크. 이보다 긴 주소(링크프라이스 딥링크 ~450자)만 500자에 못 들어가서 사이트 딜 페이지


def th_url(p, i, ref="th"):
    """Threads 글에 넣을 딜 링크: 텔레그램 버튼과 같은 링크(제휴·상품 페이지, 아직 검색 링크인 딜은 검색 링크 그대로). 주소가 없거나 TH_LINK_MAX보다 길면 사이트 딜 페이지."""
    u = p.get("url") or ""
    return u if u and len(u) <= TH_LINK_MAX else f"{SITE}p/{i}.html?ref={ref}"


def link_kind(u):
    """Threads A/B 비교용 링크 종류(10/25 점검: 바뀐 뒤 글끼리만): site = 사이트 딜 페이지 경유 · search = 쇼핑몰 검색 결과 · direct = 제휴·상품 페이지."""
    if (u or "").startswith(SITE):
        return "site"
    p = urllib.parse.urlsplit(u or "")
    tu = urllib.parse.parse_qs(p.query).get("tu")  # 링크프라이스 = 가는 곳(tu)으로 판단
    return "search" if "search" in urllib.parse.urlsplit(tu[0] if tu else u or "").path.lower() else "direct"


def th_ab(text, link):
    """A 본문(지금 개별 딜 글) -> (B 본문, 첫 댓글). B 본문 = 주소 든 줄만 빼고(대가성 문구 첫 줄·💸·제목·코멘트·토스 게시 시점 가격·팔로우 줄 그대로) 끝에 TH_AB_MARK.
    첫 댓글 = 대가성 문구 한 줄(공정위: 표시문구는 댓글 X -> 본문 첫 줄에도 그대로) + 👉 링크(A와 같은 직접 링크 — 사이트 딜 페이지일 때만 ?ref=thc) + 📲."""
    body = re.sub(r"\n{3,}", "\n\n", "\n".join(l for l in text.split("\n") if not TH_AB_URL.search(l))).strip()
    head = text.split("\n\n", 1)[0] + "\n\n" if text.startswith(NOTE_STARTS) else ""
    last = body.rsplit("\n", 1)[-1]  # 고정 레이아웃(th_voice) = ⏰·게시 시점 줄 바로 아래 👇(10/23 진우 시안)
    return f"{body}{chr(10) if last.startswith('⏰') or '게시 시점 가격' in last else chr(10) * 2}{TH_AB_MARK}", f"{head}👉 {re.sub(r'[?]ref=th$', '?ref=thc', link)}\n📲 실시간 알림 t.me/hotdeal_pick"


TH_VOICE, TH_GAP_JITTER = True, 10 * 60  # 10/21 밤 진우 'Threads 개별 딜 글 사람이 올리는 느낌': 본문을 Claude가 반말·음슴체 문장으로(th_voice, False = 지금 틀) · 개별 글 간격 45분 ± 10분(th_gap, 0 = 45분 그대로)
VOICE_LABEL = ("⭐", "💰", "🙋", "👍", "💡", "⚠", "🔥", "🛒", "👉", "👇", "📲", "👋", "💸", "🔔", "🏆", "⏰", "🤔", "🚀", "📦", "💙", "📊", "🚚", "[", "#")  # 이걸로 시작하는 줄 = 라벨·제목 줄(문장 아님)
VOICE_BAN = "|".join((WU_FAKE, r"샀는데|사\s*봤|사봄|사\s*보니|질렀|재구매|쓰는\s*중|(?:어제|작년|지난번|저번|예전)에?\s*\S*\s*샀|(?<![가-힣])(?:내가|나도|난|나는|저는|저도|우리\s*집)(?![가-힣])", WU_HEALTH, WU_HYPE, r"눌러"))  # 써 본 척(반말·음슴체 '나도·질렀' 포함, '비교해봤는데'·'N명 넘게 삼'은 OK)·효능·과장·조급·클릭 유도(토스 글은 + 다른 몰·비교)
VOICE_YO = r"(?<![필중주수소])요(?![가-힣])|죠(?![가-힣])|(?<![다아])니다(?![가-힣])"  # 해요체(~요·~죠)·~니다로 끝나는 말('확인 필요'·'중요' 같은 낱말은 아님, '30개요'는 해요체)
VOICE_EMOJI = r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u231A-\u23FA\u2B05-\u2B55\u203C\u2049]\uFE0F?|[#*0-9]\uFE0F?\u20E3|\S\uFE0F|\u200D"  # → 같은 화살표는 아님(음슴체 예시)
TONES = {  # 10/23 진우 '보는 사람이 사고 싶게 단정하고 발랄하고 이쁜 말투 — 꼭 하나의 말투만 고집하지 말고': 글마다 무작위(쓰는 곳마다 직전 2개와 다르게) · (이름, 지시, 해요체 OK?)
    1: ("단정한 해요체", "말투 = 단정한 해요체(차분하고 깔끔하게, ~요로 끝냄). 결 예시(내용·숫자는 재료에서): 오늘 이 가격이면 쟁여 두기 좋아요", True),
    2: ("발랄한 반말", "말투 = 발랄한 반말(밝고 신나게, 친구한테 말하듯 — 산 척·써 본 척은 X). 결 예시(내용·숫자는 재료에서): 이 가격 실화? 장바구니각이다✨", False),
    3: ("다정한 추천 해요체", "말투 = 다정한 추천 해요체(챙겨 주듯 따뜻하게, ~요로 끝냄). 결 예시(내용·숫자는 재료에서): 요즘 같은 날씨엔 하나쯤 있으면 든든해요", True),
    4: ("짧고 깔끔한 음슴체", "말투 = 짧고 깔끔한 음슴체(~함·~음·~임 또는 명사로 끝냄). 결 예시(내용·숫자는 재료에서): 1개 100원꼴, 쟁여 둘 만함", False)}
TONE_RULE = "공통: 문장은 짧고 읽기 편하게(예쁘고 단정하게) · 가격·숫자는 재료 그대로 · 써 봤다·샀다·후기처럼 꾸민 경험 X · '클릭하세요·지금 바로 구매' 같은 재촉 X · 과장·효능 단정 X · 이모지 0~2개."


def pick_tone(seen, where, keep=True, tones=TONES):
    """말투 무작위(tones 번호 중 — 기본 TONES 1~4), 그 쓰는 곳(where: th·ig·ch)의 직전 2개와 다르게 -> 번호(keep이면 seen['tone_'+where]에 최근 2개 — 채널은 게시한 뒤 tone_keep)."""
    t = random.choice([k for k in tones if k not in seen.get(f"tone_{where}", {}).get("l", [])[-2:]] or list(tones))
    if keep:
        tone_keep(seen, where, t)
    return t


def tone_keep(seen, where, t):
    """실제로 나간 글의 말투를 기록(직전 2개 — 10/23 리뷰: 프롬프트만 만들고 안 올린 회차가 기록을 밀지 않게)."""
    if t:
        seen[f"tone_{where}"] = {"t": time.time(), "l": (seen.get(f"tone_{where}", {}).get("l", []) + [t])[-2:]}


def tone_ask(seen, where):
    """채널 글 Claude 한 줄(comment·who·use) 말투 -> (번호, 프롬프트에 붙일 말). 기록은 게시한 뒤(tone_keep). 올리브영 딜은 큐레이터 정책(가격·용량·구성·조건만)이 먼저."""
    t = pick_tone(seen, where, keep=False)
    return t, f"\ncomment·who·use 말투 — {TONES[t][1]} {TONE_RULE.replace('이모지 0~2개', '이모지 최대 1개')} 단, [올리브영] 딜은 위 올리브영 규칙(권유·후기 X)이 먼저.\n"  # 채널 프롬프트 = 이모지 최대 1개(DEAL_PROMPT와 같게)


VOICE_STYLE = {  # (10/21 A 반말·B 음슴체 -> 10/23 TONES 4가지로, 인스타 예전 시안 호환용)
    "A": "말투 = 반말(진우가 일상 글 쓰듯 친구한테 말하는 느낌). 말투 예시일 뿐 내용·숫자는 재료에서: 핫팩 가격 비교해봤는데 / 로켓 100g 중엔 코멧이 개당 295원으로 젤 싸네 / 30개 8,860원, 150개로 사면 개당 269원까지 내려감 / 리뷰도 1,400개 넘고",
    "B": "말투 = 음슴체(핫딜 커뮤니티 글처럼 ~함·~음·~임 또는 명사로 끝냄). 말투 예시일 뿐 내용·숫자는 재료에서: 로켓 핫팩 100g 개당 가격 비교함 / 코멧 30개 8,860원 → 개당 295원으로 젤 쌈 / 150개짜리는 개당 269원 / 리뷰 1,400개 넘음"}


def ai_json(prompt, props):
    """Claude 답을 JSON으로(구조화 출력 — props = 칸 이름: JSON 스키마, 전부 필수). 10/22 08:00 강제 tool_choice가 이 모델에서 400 -> 이 방식.
    effort low = 짧은 글이라 빨리(http 30초 안). 다 못 끝냄·거절 = 실패(부른 곳이 지금 틀로)."""
    r = json.loads(http("https://api.anthropic.com/v1/messages", {
        "model": MODEL, "max_tokens": 4000, "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": {
            "type": "object", "required": list(props), "additionalProperties": False, "properties": props}}},
        "messages": [{"role": "user", "content": prompt}],
    }, {"x-api-key": E["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"}))
    if r.get("stop_reason") != "end_turn":
        raise RuntimeError(f"Claude 답 안 끝남({r.get('stop_reason')})")
    return json.loads(next(c["text"] for c in r["content"] if c["type"] == "text"))


TH_TONE_PROMPT = """Threads 핫딜 글 끝에 붙일 말투 한 줄을 써 주세요(10/23 진우 '고정 레이아웃 + 말투 한 줄'). 상품명·가격·리뷰 수 같은 숫자는 위 줄에 따로 있으니 이 한 줄엔 숫자 없이, 아래 재료에 맞는 느낌만.
- 한 문장, 폰 한 줄(20자 안팎). 이모지는 0~1개.
- 써 본 척(제가·나도·써보니·먹어보니·샀는데·질렀음), 효능·건강·의학 말, 과장·조급(역대급·무조건·손해·마지막 기회), 재촉·클릭 유도(클릭·눌러·지금 바로 구매), 링크·댓글·광고 말 쓰지 않기.
- '최근 줄'과 다른 문장으로."""
TH_TONE_POOL = {1: ("필요할 때 쟁여 두기 좋아요", "장바구니에 담아 두기 좋아요"), 2: ("장바구니에 담아 둘 만하다", "이 구성 꽤 괜찮다"),
                3: ("하나쯤 있으면 든든해요", "필요한 분께 잘 맞아요"), 4: ("쟁여 둘 만함", "구성 괜찮음")}  # Claude 실패·조건 안 맞음 = 말투별 기본 한 줄(숫자·경험담 X)
TH_TONES = {  # M-5(10/26 진우 'Threads 쿠팡 글 재미나게 소통하는 느낌') + O(친구한테 말하듯 — '사세요' X): Threads 개별 딜 글 말투 5가지 돌림 · 다 반말 · (이름, 지시, 해요체 OK?)
    1: ("계산형", "말투 = 계산형 반말(구성·단가가 왜 괜찮은지 계산하듯 짚기 — 숫자는 쓰지 말고). 결 예시: 낱개로 사는 것보다 이 묶음이 낫겠다", False),
    2: ("공감형", "말투 = 공감형 반말(이런 날 꼭 있지 하는 생활 장면). 결 예시: 꼭 다 떨어졌을 때 생각나더라", False),
    3: ("질문형", "말투 = 질문형 반말(가볍게 묻고 끝내기 — 물음표 1개). 결 예시: 다들 이런 거 몇 개씩 쟁여 둬?", False),
    4: ("짧은 감탄형", "말투 = 짧은 감탄 반말(10자 안팎). 결 예시: 이 구성 실화냐", False),
    5: ("비교형", "말투 = 비교형 반말 — 재료의 🔁·'보다 내려' 줄(우리 기록)에 쓰인 사실만 · 다른 쇼핑몰 X · 숫자 X. 결 예시: 기록 보니 다시 내려온 가격", False)}
TH_ASK, TH_TONE_POOL5 = 3, {1: ("구성 보고 계산해 볼 만함", "단가 따져 보면 괜찮은 편"), 2: ("이런 건 떨어질 때 꼭 생각나더라", "있으면 은근 자주 쓰는 거"), 3: ("다들 이런 거 쟁여 둬?", "이거 어디에 쓸 것 같아?"),
                            4: ("이 구성 실화냐", "오 이건 괜찮다"), 5: ("기록 보니 다시 내려온 가격", "전에 본 가격이랑 같이 보면 좋음")}  # 질문형만 물음표 · Claude 실패 = 기본 한 줄(숫자·경험담·상품 사실 단정 X — 비교형은 기록 재료 있을 때만 뽑힘)
TH_FRIEND = "\n- 친구한테 말하듯 반말 한 줄. '나라면 쟁여 둠' 같은 의견은 OK, 써 본 척(써 보니·먹어 보니·샀는데)·'사세요·구매하세요' 같은 권유는 X."
TH_HOOK, TH_HOOKS = True, {1: "질문 자답", 2: "계절·상황", 3: "오늘 마감", 4: "공유형", 5: "숫자 앵커"}  # U(10/26 진우 @love__pastel 글): 개별 딜 글 첫 줄(대가성 문구 다음) 훅 5가지 돌림(직전 2개와 다르게) · metrics hook = 2주 뒤 비교
TH_HOOK_POOL = ("이건 알아 두면 좋을 것 같아서", "이건 같이 보려고 가져옴", "보자마자 공유각이라 올림")  # ④ 공유형(특가 아닌 👍 꾸준템 글에도 맞게 — '이 가격 놓치기 아까워' 같은 특가 말 X)
TH_FLAWS = ((r"와우(?!\s*쿠폰)\s*(?:회원)?\s*(?:가|할인|전용)", "와우회원가라 일반 회원은 가격이 다를 수 있음"), (r"쿠폰\s*(?:가|적용|받|할인|사용|다운)|(?:\d\s*(?:원|%)|와우)\s*쿠폰", "쿠폰 받아야 이 가격"),
            (r"카드\s*(?:할인|청구|즉시|결제\s*시|가)", "카드할인 조건가"), (r"페이(?!지)\s*(?:결제|할인|가)", "페이 결제 조건가"), (r"(?:멤버십|네멤)\s*(?:가|할인|전용|회원)", "멤버십 조건가"),
            (r"옵션\s*(?:별|마다)\s*(?:가격|상이|다름|다른)|옵션가", "옵션마다 가격이 달라서 고를 때 확인 필요"))  # O 단점 = ⚠️ 조각에 이 말이 그대로 있을 때만('카드 무이자'·'사이즈 옵션 확인' X)
TH_PUSH = r"사\s*둬|사\s*놔|사\s*둘\s*것|질러|지르자|담아\s*둬|사야\s*(?:해|돼|됨|지)|사세요|구매하|서둘러|얼른|빨리\s*사|놓치지\s*마"  # 반말 재촉(O '사세요' X)
TH_PRICE_WORD, TH_QM = r"[만천백십]\s*원|원\s*(?:도|대|짜리|꼴|이하|밖에)|(?:한\s*잔|밥|커피)\s*값", r"[?？❓❔⁉⁇]"  # 숫자 말로 쓴 가격('만 원도 안 해') · 물음표(이모지 포함)
TH_HOOK_ASK = {1: "형식 = 질문 자답: 짧은 질문 + 답이 이 상품 종류(예: 겨울 되면 뭐부터 바꿔? 핸드크림!) — 물음표 1개", 2: "형식 = 계절·상황: 지금 계절·생활 상황 한 줄(사실·계절만, 경험담 X — 예: 샤워하고 나오면 욕실 추운 계절 시작)"}
TH_HOOK_PROMPT = """Threads 핫딜 글 첫 줄(훅) 1개를 써 주세요. 반말·구어체, 폰 한 줄(20자 안팎), 이모지 0~2개.
- {kind}
- 가격·숫자 X. 써 본 척(써 보니·먹어 보니·샀는데), 효능·건강, 과장·재촉('지금 안 사면 손해'·'지금 바로'), 링크·광고 말 X.

상품명: {name}"""
TH_END_FROM, TH_FEW_REV = "2026-10-26", 30  # O 실험 시작일(metrics chg · 1주 뒤 리포트 비교 th_end_report) · 리뷰 이만큼 안 되면 '리뷰 아직 적음'
TH_W, TH_NUMS = 22, 5  # 10/23 진우 'Threads 딜 글 가독성': 한 줄 = 폰 한 줄(th_w 폭 22 안팎) · 숫자(가격·단가·리뷰·구매 수·%)는 5개까지
TH_MOD = r"남녀공용|로얄특품|최고|표기|백화점|선물|포장|대용량|프리미엄|정품|신상|기획|단독|한정|무료배송|무배|특가|리미티드|에디션|본품|순수|시그니처|천연펄프|도톰한|부드러운|촉촉한|고급|명품|인기|베스트|초특가|국민|공식|본사|직영|당일발송|빠른배송"  # 짧은 상품명에서 빼는 꾸밈말(낱말째)
TH_SZ = r"\d[\d.,]*\s*(?:ml|mL|ML|l|L|g|kg|KG|Kg|mg|m|cm|mm|겹|개입)"  # 용량·크기(뒤 개수와 사이에 ×)
TH_CNT = r"\d+\s*(?:개입|개|매|롤|켤레|병|팩|입|캔|봉|포|구|알|장|세트|박스|인분|족|통|p|P|EA|ea)"
TH_QTY = rf"(?<![\d.,]){TH_CNT}(?![A-Za-z가-힣])|\d+(?:\+\d+)+"  # 개수(다른 말에 붙은 것도 — '6개+미니치약'·'1+1+1', 10/23 리뷰)
TH_UNIT = r"((?:1|한)\s*(?:개|롤|매|병|캔|켤레|팩|봉|포|장|알|구|인분|입)|(?:개|병|롤|매|\d[\d.,]*\s*(?:ml|mL|g|kg|L|l|매|롤|개|병|팩|m|구|알|인분|포|정|장|입|켤레|봉|캔|족|박스|세트))\s*당)\s*(약\s*)?(\d[\d,]*)\s*원(?!\s*(?:씩\s*)?(?:추가\s*|더\s*)?(?:할인|적립|캐시백|페이백))"
TH_ALT = r"많이|더\s*(?:쌈|싸)|짜리|이면|참고|대신|\d\s*(?:개|롤|병|팩|매|입|켤레)\s*\("  # 다른 구성·참고 비교 조각(단가·사실 줄로 안 씀 — 💡 한 줄 후보)
TH_FACTS = ((r"[가-힣A-Za-z]{2,6}\s(?:제조|생산)|국내산|국산|[가-힣]{2,4}산", True), (r"[가-힣A-Za-z]{2,8}\s?(?:향|맛)", True), (r"(?:\d+일\s*)?무료\s*반품(?:\s*\d+일)?", True),
            (r"무료\s*배송|무배", True), (r"(?:오늘|내일|모레)(?:\([^)]{1,3}\))?\s*[^·()]{0,12}?도착", False), (r"로켓\s*(?:배송|프레시)", True))  # ✔ 줄 사실(앞일수록 먼저) — True = 조각 전체가 그 모양일 때만
TH_NUM = r"리뷰 \d[\d,]*|\d[\d,.]*\s*(?:원|만|명|%)|평점 \d\.\d"  # 숫자 셈(가격·단가·리뷰·구매 수·%·평점 — 용량·개수·날짜는 X)


def ai_voice(prompt):
    """Claude가 쓴 Threads 개별 글 말투 한 줄 {line}(th_voice)."""
    return ai_json(prompt, {"line": {"type": "string"}})


def th_w(s):
    """폰 한 줄 폭(Threads 앱 대략): 한글·이모지 = 1, 숫자·영문·기호·빈칸 = 0.55 — TH_W(22)면 폰 한 줄."""
    return sum(0 if c in "️‍" else 0.55 if ord(c) < 0x2000 else 1 for c in s)


def th_round(n):
    """리뷰·구매 수 반올림(아래로 — 부풀리지 않게): 51,181 -> '5만+' · 2,000 -> '2,000+' · 1,419 -> '1,400+' · 357 -> '350+' · 12 -> '12'."""
    return f"{n // 10000}만+" if n >= 10000 else f"{n // 100 * 100:,}+" if n >= 1000 else f"{n // 10 * 10}+" if n >= 100 else str(n)


def th_name(name):
    """짧은 상품명(Claude 없이 원문 낱말만 — 없는 이름 X): 괄호 안이 용량·개수면 괄호만 벗기고(30m 30롤·[1+1]) 아니면 뺌 · 꾸밈말(TH_MOD) 뺌 · '용량 개수' 사이 ×(100ml 3개 -> 100ml × 3개)
    · 폭 TH_W 넘으면 마지막 용량·개수 뒤 꼬리만 뺌(낱말을 임의로 빼면 품명·브랜드가 빠져서 X — 10/23 리뷰, 그래도 길면 두 줄) · 끝에 남은 ×·+ 정리."""
    n = re.sub(r"\([^()]*\)|\[[^\]]*\]", lambda m: f" {m[0][1:-1]} " if re.search(rf"{TH_QTY}|{TH_SZ}", m[0]) else " ", name)
    n = re.sub(r"(?<!\d),|,(?!\d)", " ", re.sub(r"\s외\s*\d+\s*(?:개|종|건)?\s*$", " ", n))  # '… 외 2'(옵션 수) 꼬리 · 쉼표(천 단위 쉼표는 그대로)
    n = re.sub(r"(?:(?<=\d)|(?<=\d[A-Za-z])|(?<=\d[A-Za-z]{2}))\s*[xX×*]\s*(?=\d)", " × ", n)  # 2LX30병·39g x 4개 -> × (모델명 IPX500A X)
    ws = [w for w in n.split() if not re.fullmatch(TH_MOD, w)]
    q = lambda w: w != "×" and (re.fullmatch(rf"{TH_SZ}|{TH_CNT}", w) or re.search(TH_QTY, w))
    if "×" not in ws:  # 마지막 개수 바로 앞이 용량이면 ×
        k = max((i for i, w in enumerate(ws) if i and re.fullmatch(TH_CNT, w) and re.fullmatch(TH_SZ, ws[i - 1])), default=0)
        ws = ws[:k] + ["×"] + ws[k:] if k else ws
    last = max((i for i, w in enumerate(ws) if q(w)), default=0)
    if th_w(" ".join(ws)) > TH_W and last > 0:
        ws = ws[:last + 1]
    return re.sub(r"[\s×+/]+$", "", " ".join(ws)) or name


def th_segs(line):
    """줄 -> 조각들(' · '·' — '·', ' 기준 — 괄호 안은 안 나눔), 앞 라벨(⭐·💡·🚀 이모지, '확인할 점:'·'단위가격') 뺌."""
    out, cur, d, i = [], "", 0, 0
    while i < len(line):
        sep = next((s for s in (" · ", " — ", ", ") if not d and line.startswith(s, i)), None)
        if sep:
            out, cur, i = out + [cur], "", i + len(sep)
            continue
        d += (line[i] == "(") - (line[i] == ")")
        cur, i = cur + line[i], i + 1
    return [x for x in (re.sub(r"^[^\w(]*(?:확인할 점:?|단위가격:?)?\s*", "", s).strip() for s in out + [cur]) if x]


def th_voice(seen, text, link, src=None):
    """Threads 개별 딜 글(th_deal로 가는 글 전부) = 고정 레이아웃 + Claude 말투 한 줄(10/23 진우 '가독성 — 보기 좋게, 깔끔하게'):
    대가성 문구 첫 줄 그대로 / 몰 머리 줄 그대로(예전 틀 글은 mall_head) · 짧은 상품명(th_name) · 💰 가격 (단가 — 토스는 없으면 할인%) · (🔁 다시 특가·'지금은 특가 아님' 줄 그대로)
    / ✔ 리뷰·구매 수(반올림) · ✔ 원문 사실 2개(제조국·향·반품·배송 등) · 💡 다른 구성·비교 한 줄(토스 X) / 말투 한 줄(TONES 4가지 돌림, 숫자 X, 이모지 0~1)
    / ⏰ M/D H시 가격(쿠폰가 등 조건) · 결제 전 확인(토스 = '⚠️ M/D HH:MM 게시 시점 가격' 그대로) + 👉 링크. 블록 사이 빈 줄, 줄마다 폭 TH_W 안,
    숫자 TH_NUMS개 넘으면 💡 -> 구매 수 -> 단가 순서로 뺌, 480자 넘으면 💡 -> ✔ -> 말투 줄. 말투 줄 = 금지어·~요(해요체 말투 아니면)·숫자·폭·최근 10개와 같은 문장이면 1번 다시, 그래도면 TH_TONE_POOL.
    대가성 문구 없음·상품명·가격 못 읽음·480자 못 넣음 = 지금 틀(text) 그대로. 👋 팔로우·📲 줄은 뺌(B 첫 댓글엔 📲 그대로 — th_ab). src = 줄이기 전 글(재료, 없으면 text)."""
    full = src or text
    if not full.startswith(NOTE_STARTS):
        return text
    try:
        head, rest = full.split("\n\n", 1)
        toss = TOSS_NO_CMP and is_toss(link, full)
        ls = [l.strip() for l in rest.split("\n") if l.strip() and not TH_AB_URL.search(l) and not l.startswith(("👋", "📲", "🏆", "출처:"))]
        hi = next((i for i in range(len(ls)) if mall_title(ls, i)), None)
        if hi is not None:  # 몰별 틀: 머리 줄 그대로 · 다음 두 줄 = 상품명·가격 줄
            mhead, title, pline, body = ls[hi], mall_title(ls, hi), ls[hi + 2], ls[:hi] + ls[hi + 3:]
        else:  # 예전 틀 '🔥 [몰] 상품명 (가격)' -> 머리 줄 만듦(토스·쿠팡 = mall_head, 그 밖 = 아이콘 + [몰])
            ti = next(i for i, l in enumerate(ls) if l.startswith(("🔥", "🛒", "👍")))
            icon, title = ls[ti][0], re.sub(r"^[🔥🛒👍]\s*", "", ls[ti])
            mall, tag = mall_of(link, title), parse(title)[0]
            mhead = mall_head(mall, mall_src(mall, full, title), icon, mall != "coupang" or cp_rocket(full)) if mall else f"{icon} [{tag}]" if tag else icon
            pline, body = "", ls[:ti] + ls[ti + 1:]
        _, name, price = parse(title)
        won = re.search(r"\d[\d,]*(?=\s*원)", price) or re.search(r"^\d[\d,]{3,}", price)
        if not (won and name):
            raise ValueError("상품명·가격 못 읽음")
        won = f"{int(won[0].replace(',', '')):,}원"
        steady = th_steady(full)
        when = [l for l in body if "게시 시점" in l]
        warn = [s for l in body if l.startswith("⚠") and "게시 시점" not in l for s in th_segs(l)] + [price.split(won.rstrip("원"))[0]]  # ⚠️ 확인할 점 조각 + 가격 앞 '쿠폰'·'와우' 말
        status = [l for l in body if l.startswith("🔁") or "지금은 특가 아님" in l]
        detail = [l for l in body if l not in when and l not in status and not l.startswith(("⚠", "💸", "🙋", "👍", "👉"))]
        segs = [s for l in [pline] + detail for s in th_segs(l)] + [x.strip() for x in price.split("/")[1:]]  # 예전 틀 가격 '/무료배송' 조각도 사실 후보
        flat = [re.sub(r"\([^()]*\)", "", s).strip() for s in segs]  # 괄호 안(참고·검색 시각) 뺀 조각
        unit = next((f"{m[1]} {m[2] or ''}{m[3]}원" for s in flat if not re.search(TH_ALT, s) for m in [re.search(TH_UNIT, s)] if m), "")
        dr = re.search(r"\((\d{1,2})%↓\)", pline)
        own = [s for l in [pline] + [l for l in detail if l.startswith("⭐")] for s in th_segs(l)] + [s for s in segs if not re.search(TH_ALT, s)]  # 이 상품 리뷰·구매 수 = 가격 줄·⭐ 줄 먼저(참고 상품 수 X — 10/23 리뷰)
        rate, rv, buy = re.search(r"⭐\s*(\d\.\d)", pline), *(next((steady_n(m[1]) for s in own for m in [re.search(rx, s)] if m), 0) for rx in (STEADY_REV, STEADY_BUY))
        rv = rv or (int(m[1].replace(",", "")) if (m := re.search(r"⭐\s*\d\.\d\s*\((?:리뷰\s*)?([\d,]+)\)", pline)) else 0)
        ban = f"{WU_BAN}" + (f"|{TOSS_BAN}" if toss else "")
        facts = sorted(((k, j, (m[0] if full_ else m[0]).strip()) for j, (s, f) in enumerate(zip(segs, flat)) for k, (rx, full_) in enumerate(TH_FACTS)
                        for m in [re.fullmatch(rx, f) if full_ else re.search(rx, s)] if m and not (k == 5 and "로켓" in mhead)
                        and th_w(m[0]) <= 12 and not re.search(rf"원|%|리뷰|구매|가격|할인|쿠폰|{ban}", m[0])), key=lambda x: x[:2])
        facts = list(dict.fromkeys("무료배송" if x[2] == "무배" else x[2] for x in facts))
        alt = []
        if not toss:  # 💡 한 줄 후보: 💸 같은 상품 다른 몰 > 다른 구성(N개짜리는 1개 M원) > 날짜 붙은 지난 가격·참고
            alt += [re.sub(r"^💸\s*", "", l) for l in body if l.startswith("💸")]
            for l in detail:
                for s in th_segs(l):
                    m = re.search(r"((?:[가-힣A-Za-z]+(?<!면)\s)?\d+\s*(?:개|롤|병|팩|매|입|캔|봉|켤레))\s*(?:\(|\d[\d,]*\s*원\s*이?면)", s)  # '6개(15,860원)가 1개 …' · '150개 40,310원이면 1개당 …'
                    u = m and re.search(TH_UNIT, s[m.end():])
                    alt += [f"{m[1].strip()}짜리는 {u[1]} {u[2] or ''}{u[3]}원"] if u and re.search(r"많이|더\s*(?:쌈|싸)|거면|이면|쟁일", s) else []
            alt += [re.sub(r"^[^\w(]*", "", l) for l in detail if l.lstrip("📊💡 ").startswith("참고") and re.search(r"\d\s*원", l)]  # '📊 참고: …' 줄째(들어가면)
            alt += [s for s in segs if re.search(r"소개 때|보다 내려|전보다|참고", s) and re.search(r"\d\s*원", s)]
        tip = next((f"💡 {a}" for a in alt if th_w(a) <= TH_W - 1 and not re.search(WU_BAN, a)), "")
        md = re.search(r"\((\d{1,2})/(\d{1,2}) (\d{1,2})(?::\d{2})?시?(?: 가격)?\)", full)
        k = time.gmtime(time.time() + 9 * 3600)
        mo, d, h = (int(md[1]), int(md[2]), int(md[3])) if md else (k.tm_mon, k.tm_mday, k.tm_hour)
        conds, other = [], ""  # 가격 조건(긴 이름, 짧은 이름) — ⚠️ 조각 전부에서(쿠폰·카드·페이·와우·멤버십), 적립·배송 조건은 X(10/23 리뷰)
        for s in (re.sub(r"\([^()]*\)", "", x or "") for x in warn):
            if not s.strip() or re.search(r"결제 전|최종가|게시 시점|정가 기준|적립|배송|무배|무료|별도", s):
                continue
            m = re.search(r"(\d[\d,]*원|\d+%)\s*쿠폰", s)
            for rx, lg, sh in ((r"쿠폰", m and f"{m[1]} 쿠폰" or ("와우쿠폰" if "와우" in s else "쿠폰"), "쿠폰"), (r"카드", "카드할인", "카드"), (r"페이(?!지)", "페이 결제", "페이"),
                               (r"와우(?!\s*쿠폰)", "와우회원", "와우"), (r"멤버|네멤", "멤버십", "멤버십")):
                if re.search(rx, s) and (lg, sh) not in conds:
                    conds.append((lg, sh))
            other = other or ("옵션별 가격" if "옵션" in s else (lambda m: f"{m[1]}부터" if m else "")(re.search(r"(\d{1,2}/\d{1,2})\s*부터", s)))
        cands = ["+".join(x[0] for x in conds) + "가", "+".join(x[1] for x in conds) + "가", conds[0][1] + "가"] if conds else [other] if other else []
        tl = next((x for c in cands for x in [f"⏰ {mo}/{d} {h}시 {c} · 결제 전 확인"] if th_w(x) <= TH_W + 1e-6), f"⏰ {mo}/{d} {h}시 가격 · 결제 전 확인")  # 길면 짧은 이름으로
        tl = (when[0] if when else toss_when()) if toss else tl
        ws = [x for x in (re.sub(r"\([^()]*\)", "", y).strip() for y in warn) if x and not re.search(r"없이|없어도|불필요|필요\s*없|무관", x)]  # O(10/26 진우): 끝 = 친구 한 줄 + 아쉬운 점 사실 한 줄(우리 데이터에서만, 없으면 X) — '쿠폰 없이도' 같은 부정 조각 X
        flaw = next((t for rx, t in TH_FLAWS if any(re.search(rx, x) for x in ws)), "") \
            or next((re.sub(r"\s*확인$", " 확인 필요", x) for x in ws[:-1] if not re.search(r"결제 전|최종가|게시 시점|정가|적립|배송|무료|무이자|원|%", x)), "") or ("리뷰가 아직 적음" if 0 < rv < TH_FEW_REV else "")
        con = f"단점 하나: {flaw}" if flaw and not re.search(ban, flaw) and th_w(f"단점 하나: {flaw}") <= TH_W + 6 else ""  # 토스 = 다른 몰 비교 말 X(TOSS_BAN)
        st, norm = seen.get("thvoice", {}), lambda s: re.sub(r"[\W_]+", "", s)
        drop = bool(re.search(r"다시 왔|보다 내려|내려왔|내려갔", " ".join(status + [tip])))  # 우리 기록에 '내려감'이 쓰여 있을 때만(처음 소개 때 가격·특가 아님 = 방향 모름)
        cmp_ok = not toss and drop  # 비교형 = 그때만(토스 X)
        tone = pick_tone(seen, "th", keep=False, tones=[k for k in TH_TONES if k != 5 or cmp_ok])  # M-5 말투 5가지 돌림 — 한 줄에, 기록은 실제로 쓴 뒤
        yo_ok, oy = TH_TONES[tone][2], aff_note(link) == OY_NOTE
        lban = f"{ban}|{VOICE_BAN}" + (r"|특가|최저(?!가?는?\s*아[니닌님냐])|할인" if steady else "") + (f"|{OY_DENY}" if oy else "") + r"|링크|댓글|팔로우|광고|수수료|결제 전|게시 시점|지금\s*바로|" + TH_PUSH + ("" if drop else r"|내려왔|내려갔|싸졌|떨어졌")  # 써 본 척·재촉(반말 '사 둬'·'질러' 포함) · 올리브영 큐레이터 정책 · 기록 없이 '내려왔다' X
        names = [w for i, w in enumerate(re.findall(r"[가-힣A-Za-z]{2,}", name)) if not i or not re.search(lban, w)]  # 금지어 검사에서 빼는 상품명 낱말 = 브랜드 + 금지어 아닌 것만
        dl = toss and re.search(r"밤\s*12시까지|하루\s*특가", full) and (m := re.search(r"(\d{1,2})/(\d{1,2}) \d{1,2}:\d{2} 게시 시점", " ".join(when))) and (int(m[1]), int(m[2])) == (k.tm_mon, k.tm_mday)
        hook, hk = th_hook(seen, name, dl, unit, lban, names) if TH_HOOK and not oy else ("", 0)  # ③ 근거 = 토스 하루특가 + 게시 시점이 오늘(밤 12시 지나 올라가는 줄 선 글 X) · 올리브영 = 훅 X(큐레이터 정책)
        ok = lambda s: s and not s.startswith(VOICE_LABEL) and not TH_AB_URL.search(s) and not re.search(rf"\d|{TH_PRICE_WORD}", s) and th_w(s) <= TH_W + 2 \
            and not re.search(lban, re.sub("|".join(map(re.escape, names)) or "^$", "", s)) and (tone == TH_ASK or not re.search(TH_QM, s)) \
            and (yo_ok or not re.search(VOICE_YO, re.sub("|".join(map(re.escape, names)) or "^$", "", s))) and norm(s) not in st.get("f", [])
        prompt = TH_TONE_PROMPT + TH_FRIEND + "\n- " + TH_TONES[tone][1] + "\n- " + TONE_RULE.replace("이모지 0~2개", "이모지 0~1개").replace("가격·숫자는 재료 그대로 · ", "") + ("\n- 올리브영 딜: 권유·후기·추천·효과 말 X." if oy else "") + ("" if yo_ok else "\n- 해요체 X: '~요'로 끝나는 말(~해요·~해 주세요·~대요·~거든요 등) 쓰지 않기.") \
            + ("\n- 물음표 쓰지 않기." if tone != TH_ASK else "") + ("\n- 토스 딜: 다른 쇼핑몰 이름·가격 비교(보다 싸·젤 싸·비교) 없이." if toss else "") \
            + ("\n- 이 글 = '꾸준히 팔리는 상품': 특가·최저가·할인이라고 하지 않기." if steady else "") \
            + f"\n\n상품명: {name}\n가격: {won}\n재료:\n" + "\n".join(l for l in ls if "게시 시점" not in l) + ("\n\n최근 줄: " + " / ".join(st.get("b", [])[-5:]) if st.get("b") else "")
        line, again = "", ""
        for _ in (0, 1):
            try:
                x = re.sub(r"\s+", " ", str(ai_voice(prompt + again).get("line") or "")).strip()
            except Exception as e:  # Claude 실패 = 기본 한 줄
                print("th voice 기본 한 줄", clip(repr(e), 120))
                break
            x = re.sub(r"\s{2,}", " ", re.sub(VOICE_EMOJI, "", x)).strip() if len(re.findall(VOICE_EMOJI, x)) > 1 else x  # 이모지 0~1개 -> 넘으면 다 뺌
            if ok(x):
                line = x
                break
            again = f"\n\n다시: '{x}'은 규칙에 안 맞음(숫자·가격 말 X · 폰 한 줄 · {TH_TONES[tone][0]} · 금지어·재촉 X · 최근 줄과 다르게)."
        pool = [] if oy else list(TH_TONE_POOL5[tone])  # 올리브영 = 기본 줄 X(큐레이터 정책: 가격·용량·구성·조건만)
        line = line or ([x for x in pool if norm(x) not in st.get("f", [])] or pool or [""])[0]  # 올리브영이라 맞는 기본 줄이 없으면 말투 줄 없이
        soc = ([f"평점 {rate[1]}"] if rate else []) + ([f"리뷰 {th_round(rv)}"] if rv else []) + ([f"한 달 {th_round(buy).rstrip('+')}명{'+' * th_round(buy).endswith('+')} 구매"] if buy else [])
        def render(soc, unit, tip, facts, line, con, hook=hook):
            money = f"💰 {won}" + (f" ({unit})" if unit else f" ({dr[1]}%↓)" if dr else "")
            chk = [f"✔ {' · '.join(soc)}"] * bool(soc)
            for a, b in zip(facts[0::2], facts[1::2] + [""]):  # 사실 2개씩 한 줄(폭 넘으면 1개)
                if len(chk) < 2:
                    chk.append(f"✔ {a} · {b}" if b and th_w(f"✔ {a} · {b}") <= TH_W else f"✔ {a}")
            blocks = [head, hook, "\n".join([mhead, th_name(name), money] + status), "\n".join(chk + [tip] * bool(tip)), tl, "\n".join(x for x in (line, con) if x), f"👉 {link}"]  # O: ⏰ 가격 시각 -> 끝 = 한 줄 + 단점 하나
            return "\n\n".join(b for b in blocks if b), "\n".join([money] + status + chk + [tip] * bool(tip))
        steps = [{}, {"tip": ""}, {"tip": "", "soc": soc[:2] if buy else soc}, {"tip": "", "soc": soc[:2] if buy else soc, "unit": ""}]  # 숫자 넘침 -> 💡 -> 구매 수 -> 단가
        cur = next((s for s in steps if len(re.findall(TH_NUM, render(**{**dict(soc=soc, unit=unit, tip=tip, facts=facts, line=line, con=con), **s})[1])) <= TH_NUMS), steps[-1])
        args = {**dict(soc=soc, unit=unit, tip=tip, facts=facts, line=line, con=con), **cur}
        for cut in ({}, {"tip": ""}, {"tip": "", "facts": []}, {"tip": "", "facts": [], "soc": []}, {"tip": "", "facts": [], "soc": [], "con": ""}, {"tip": "", "facts": [], "soc": [], "con": "", "line": ""}, {"tip": "", "facts": [], "soc": [], "con": "", "line": "", "hook": ""}):  # 480자 넘으면 💡 -> ✔ -> 단점 -> 말투 줄 -> 훅
            out = render(**{**args, **cut})[0]
            if len(out) <= 480:
                break
        else:
            raise ValueError(f"480자({len(out)})")
        if line and line in out.split("\n"):
            tone_keep(seen, "th", tone)
            seen["thvoice"] = {"t": time.time(), "s": tone, "f": (st.get("f", []) + [norm(line)])[-10:], "b": (st.get("b", []) + [line])[-5:]}
        else:  # 말투 줄이 빠짐(480자·올리브영) = 말투 기록 X
            seen.setdefault("thvoice", {"t": time.time()}).pop("s", None)
        if hook and hook in out.split("\n"):  # U: 글에 든 훅 = th_deal이 올라간 뒤 돌림 기록 · metrics hook
            seen["thvoice"]["h"] = hk
        else:
            seen["thvoice"].pop("h", None)
        print("th voice", f"말투 {tone}", clip(name, 30), "| " + ("말투 줄 없음" if not line else "기본 한 줄" if line in TH_TONE_POOL5[tone] else "Claude 한 줄"))
        return out
    except Exception as e:  # 못 읽음·480자 = 지금 틀 그대로(글은 나감)
        print("th voice 지금 틀로", clip(repr(e), 120))
        return text


def th_hook(seen, name, dl, unit, ban, names):
    """U 첫 줄 훅 -> (줄, 종류 1~5) 또는 ("", 0): 이 글에 쓸 수 있는 종류(③ = dl(토스 하루특가 오늘) · ⑤ = 단가 있을 때만) 중 직전 2개 X, 지난번 다음 번호부터 차례로.
    ①② = Claude(숫자·가격 말 X · 금지 말 · 폭 · 물음표는 ①만) — 실패·규칙 X = 다음 차례 종류로(직전 2개는 끝까지 X). 숫자는 우리 데이터(단가)만."""
    last = seen.get("thhook", {}).get("l", [])
    fixed = {3: "이 가격 오늘 밤 12시까지" if dl else "", 4: TH_HOOK_POOL[sum(map(ord, name)) % len(TH_HOOK_POOL)], 5: f"{unit}꼴" if unit else ""}  # ④ = 상품마다 다른 줄
    for k in sorted((x for x in TH_HOOKS if fixed.get(x, True) and x not in last), key=lambda x: (x - (last[-1] if last else 0) - 1) % len(TH_HOOKS)):
        if k in fixed:
            return fixed[k], k
        try:
            h = re.sub(r"\s+", " ", str(ai_json(TH_HOOK_PROMPT.format(kind=TH_HOOK_ASK[k], name=name), {"hook": {"type": "string"}}).get("hook") or "")).strip()
            plain = re.sub("|".join(map(re.escape, names)) or "^$", "", h)
            if h and not re.search(rf"\d|{TH_PRICE_WORD}|값|가격", h) and th_w(h) <= TH_W + 2 and len(re.findall(VOICE_EMOJI, h)) <= 2 and not re.search(ban, plain) and (k == 1) == bool(re.search(TH_QM, h)) and not h.startswith(VOICE_LABEL):
                return h, k
        except Exception as e:
            print("th hook 다음 종류로", clip(repr(e), 80))
    return "", 0


TH_C, TH_C_FROM, TH_SCENE_H = True, "2026-10-25 20:00", (19, 22)  # 10/25 Cowork·진우 Threads 글 틀 업그레이드(playto876·gaebalza_·billy___ssam 방식 참고): C = 본문 '[광고] 상황 훅'(상품명·가격·링크 X) + 바로 첫 댓글 = 답·상품·가격·링크
# — 설정값 변경이라 10/25 19시 점검(A/B 비교) 뒤부터 A→B→C 돌림, 2주 비교(v48·rv48·답글) · S '상황 3장면' = 하루 1개(TH_SCENE_H시 KST 사이 첫 개별 글 칸). 간격(35~55분)·한도는 그대로
TH_C_BAN = r"추천|인생\s*템|강추|무조건|최저|역대|(?:가장|제일|젤)\s*(?:싸|저렴)|품절\s*임박|서두르|지금\s*바로|사세요|사야\s*해|구매하|링크|광고|수수료|https?:|\.kr|\.com"  # C·S 글(대가성 문구·링크는 코드가 붙임)
TH_C_FAKE = r"쟁여\s*(?:둔다|둠|둬|뒀|놨|놔|놓음|놓았|두는\s*중|두고\s*있)|쟁였|(?:쓰|써\s*보|마시|먹|입|신|뿌리|바르|발라\s*보|사용하|들고\s*다니)는\s*중(?!에)|쓰고\s*(?:부터|나서|나니)|쓰니까|써\s*보니|먹고\s*(?:부터|나서)|바꿨|바꿈|바꾸고\s*나|갈아타|갈아탔|갈아탐|정착|들인\s*뒤|들이고\s*나|(?:사다|사|주문해|시켜|챙겨|걸어)\s*(?:둠|둬|둔다|뒀|놨|놔|놓음)|(?:이거|이걸로)\s*(?:만\s*)?(?:씀|써|먹어|먹음|마셔|마심)(?![가-힣])|챙겨\s*먹|챙김|바름|샀더니|써\s*봄|먹어\s*봄|이거만\s*(?:씀|써|먹)|매일\s*(?:마심|먹음|씀|바름)|요즘\s*(?:이거|이걸로)|정기\s*배송|해결\s*(?:함|했|됨)|편해\s*(?:짐|졌)|좋아\s*(?:짐|졌)|달라\s*(?:짐|졌)"  # 내가 샀다·쓴다는 말(써 본 척 — 10/25 리뷰 2번: '쟁여 두기·두면' 같은 권유 꼴은 OK)
TH_C_SKIP = r"영양제|유산균|프로바이오|락토|비타민|멀티\s*비타|종합\s*비타|오메가|콜라겐|홍삼|루테인|밀크\s*[씨시]슬|쏘팔|아르기닌|코엔자임|코큐텐|프로폴리스|크릴|보스웰리아|양배추즙|도라지|프로틴|다이어트|건강|효소|흑마늘|녹용|글루타치온|마그네슘|철분|칼슘|엽산|의약|파스|마스크팩|탈모|두피|\d+\s*(?:정|캡슐)(?![가-힣])"  # 몸·피부 고민 → 상품 = 효능 주장이 되는 품목은 C·S X(A/B만 — 전체 제목으로 봄, + WU_HEALTH)
TH_C_BODY = r"아프|아파|뻐근|결림|저리|가려|간지러|빠진\s*머리|머리카락이\s*빠|더부룩|소화가|붓기|부었|피곤|칼칼|기침|콧물|여드름|트러블|잡티|기미|주름|각질|두통|생리통|변비|불면|잠이\s*안"  # 몸·피부 증상 장면 X(상황 → 상품 = 효능 주장 — 생활 불편만)
TH_C_PROMPT = """너는 Threads에 생활 속 불편을 반말로 짧게 쓰는 사람이야. 아래 상품이 해결하는 '실제로 자주 겪는 불편한 상황'을 써.
- 상품명·브랜드·'추천'이라는 말 X. 가격·숫자·용량·스펙·링크 X. 써 본 척(나도·내가·샀는데·써 보니)·효과·효능 약속·과장(인생템·강추·무조건·최저) X. 다른 쇼핑몰 이야기 X. 재촉('지금 바로'·'사세요') X.
- 말하는 사람이 그 물건을 샀다·쓴다·먹는다·바꿨다·쟁여 뒀다는 말 X(요즘 이거 써·먹는 중·바꿨더니·들인 뒤로·쟁여 둠·챙김 X) — 불편한 장면만, 해결은 '방법·물건 소개'로.
- 몸·피부·건강 증상(아픔·뻐근·가려움·빠진 머리카락·더부룩·피곤·트러블 등) 장면 X — 떨어짐·번거로움·자리·시간·정리 같은 생활 불편만.
- 반말. 한 줄 = 폰 한 줄(20자 안팎). 이모지는 전체에서 0~1개."""
TH_C_RULE = {"C": """- hook: 첫 줄 — 반전형·질문형·고백형 중 하나로 상황이 바로 떠오르게(예: '빨래 개다가 또 짝 안 맞는 양말 나옴').
- lines: 그 상황을 이어 가는 2~4줄(장면만 — 해결책·상품 X).
- tease: 마지막 줄 — 답이 궁금하게(답은 말하지 않기, 끝에 👇 가능. 예: '이럴 때 답은 하나 👇').
- answer: 첫 댓글 첫 줄 — tease의 답을 방법·물건 소개로(예: '계란은 한 판씩 미리 쟁여 두기' — '~해 둠'·'~쓰는 중' 같은 내 경험 말 X. 상품명은 바로 아래 줄에 따로 붙음).""",
             "S": """- hook: 첫 줄 — 세 장면을 묶는 질문형·고백형 한 줄(예: '이 세 개 다 겪어 봤으면 손').
- scenes: 불편한 장면 3개 — 장면마다 3~5줄(상황만 — 해결책·상품 X), 장면끼리 다른 때·다른 곳.
- close: 마지막 한 줄 — '그래서 찾아본 게 ○○'처럼 찾아본 상품 종류만(샀다·쓴다·쟁여 뒀다 X, 상품명·가격 X — 상품명은 아래 줄에 따로 붙음)."""}


def th_c_line(x, names, toss, name_ok=False):
    """C·S 글 한 줄 검사: 폭·금지어(TH_C_BAN·써 본 척·효능·과장·비교 — 토스 = 다른 몰 말 X)·숫자 X·상품명 낱말 X(name_ok면 허용) -> 다듬은 줄 또는 ''."""
    x = re.sub(r"\s+", " ", str(x or "")).strip()
    bad = not x or th_w(x) > TH_W + 6 or re.search(rf"{TH_C_BAN}|{TH_C_FAKE}|{TH_C_BODY}|{VOICE_BAN}|{WU_BAN}" + (f"|{TOSS_BAN}" if toss else ""), x) or re.search(r"\d", x) \
        or not name_ok and any(n in x for n in names)
    return "" if bad else x


def th_c_gen(kind, name, cat, toss):
    """Claude -> C {hook, lines, tease, answer} 또는 S {hook, scenes, close} (규칙 안 맞으면 1번 다시, 그래도·실패 = None -> A/B로)."""
    names = [w for i, w in enumerate(re.findall(r"[가-힣A-Za-z]{2,}", name)) if not i or re.search(r"[A-Za-z]", w)]  # 상품명 X = 브랜드(첫 낱말)·영문 낱말(모델명) — '화장지'·'생수' 같은 종류 말은 상황 말로 OK
    props = {"hook": {"type": "string"}, "lines": {"type": "array", "items": {"type": "string"}}, "tease": {"type": "string"}, "answer": {"type": "string"}} if kind == "C" else \
        {"hook": {"type": "string"}, "scenes": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}}, "close": {"type": "string"}}
    prompt, again = TH_C_PROMPT + "\n" + TH_C_RULE[kind] + ("\n- 토스 상품: 다른 쇼핑몰 이름·가격 비교 없이." if toss else "") + f"\n\n상품: {name}\n품목: {cat or '생활용품'}", ""
    for _ in (0, 1):
        try:
            x = ai_json(prompt + again, props)
        except Exception as e:
            print("th c Claude 실패", kind, clip(repr(e), 120))
            return None
        emo = len(re.findall(VOICE_EMOJI, json.dumps(x, ensure_ascii=False)))
        if kind == "C":
            out = {"hook": th_c_line(x.get("hook"), names, toss), "lines": [th_c_line(l, names, toss) for l in (x.get("lines") or [])], "tease": th_c_line(x.get("tease"), names, toss),
                   "answer": th_c_line(x.get("answer"), names, toss, True)}
            if out["hook"] and out["tease"] and out["answer"] and 2 <= len(out["lines"]) <= 4 and all(out["lines"]) and emo <= 1:
                return out
        else:
            sc = [[th_c_line(l, names, toss) for l in z] for z in (x.get("scenes") or []) if isinstance(z, list)]
            out = {"hook": th_c_line(x.get("hook"), names, toss), "scenes": sc, "close": th_c_line(x.get("close"), names, toss)}
            if out["hook"] and out["close"] and len(sc) == 3 and all(3 <= len(z) <= 5 and all(z) for z in sc) and emo <= 1:
                return out
        again = "\n\n다시: 앞 답이 규칙에 안 맞음(줄 수·숫자 X·상품명 X·금지어 X·한 줄 폭)."
    print("th c 규칙 안 맞음", kind, clip(name, 30))
    return None


def th_parts(vt):
    """th_voice 고정 레이아웃 글 -> (대가성 문구, 몰 머리 줄, 짧은 이름, 💰 줄 + 상태 줄들, ⏰/⚠️ 가격 시각 줄) 또는 None(지금 틀 = C·S X).
    shortcut: 10/26 O·U 틀(훅 줄·⏰ 다음 끝 줄)은 못 읽어 C·S = A로 감 — TH_LINK_AB(C·S)를 다시 켜면 여기 먼저 새 틀에 맞출 것."""
    b = vt.split("\n\n")
    h = b[1].split("\n") if len(b) > 2 else []
    last = b[-1].split("\n")
    if not (b[0].startswith(NOTE_STARTS) and len(h) >= 3 and h[2].startswith("💰") and len(last) == 2 and last[1].startswith("👉")):
        return None
    return b[0], h[0], h[1], "\n".join(h[2:]), last[0]


def th_why(link, tl):
    """첫 댓글 링크 앞 '지금 확인할 이유' 한 줄(10/25 Cowork — '사세요' X, 우리 데이터로): 오늘 밤 12시 마감 > 이번 주 같은 품목(PRICE_ITEMS) 단위가 순위(3위 안·3개↑) > 가격 확인 시각."""
    posts = load(POSTS, [])
    m = re.search(r"/p/(\d+)\.html", link or "")
    p = posts[int(m[1])] if m and int(m[1]) < len(posts) else next((q for q in reversed(posts) if q.get("url") == link), None)
    today = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600))
    if p and day_end(p, today):
        return "오늘 밤 12시에 끝나는 가격이라 지금 한 번 확인해 봐"
    pu, it = p and S_per_unit(p), p and price_item(p)  # 같은 품목(최저가 기록 품목 — 즉석밥·화장지 등)끼리만(쌀 vs 햇반 X · 토스 = None — 10/25 리뷰)
    if pu and it:
        since = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600 - 6 * 86400))
        best = {}
        for q in posts:
            u = q["t"][:10] >= since and not q["text"].startswith("📋") and (price_item(q) or ("",))[0] == it[0] and S_per_unit(q)
            if u and u[0] == pu[0]:
                best[q.get("url") or id(q)] = min(best.get(q.get("url") or id(q), u[1]), u[1])
        r = 1 + sum(v < pu[1] for k, v in best.items() if k != p.get("url"))
        if len(best) >= 3 and r <= 3:
            return f"이번 주 핫딜픽 {it[1]} 중 단위가 {r}위라 지금 볼 만해"
    t = re.search(r"(\d{1,2}/\d{1,2} \d{1,2}(?::\d{2})?시?)", tl)
    return f"{t[1]} 기준 가격이라 바뀌기 전에 확인해 봐" if t else "가격은 바뀔 수 있어서 결제 전에 한 번 확인해 봐"


def th_len(s):
    """Threads 글자 수(500 한도): 이모지 = UTF-8 바이트 수(공식 문서), 나머지 = 1."""
    return sum(len(c.encode()) if ord(c) >= 0x2000 and not ("\uac00" <= c <= "\ud7a3" or "\u3130" <= c <= "\u318f") else 1 for c in s)


def th_c_post(kind, vt, link, cat, toss, title=""):
    """C(상황 훅)·S(상황 3장면) -> (본문, 첫 댓글) 또는 None. 본문 = '[광고] 훅'(대가성 표시 맨 앞 — 링크·가격 X) · 첫 댓글 = 대가성 문구 전문 + 답·상품·가격·시각 + 지금 확인할 이유 + 👉 링크(여기에만)."""
    pt = th_parts(vt)
    if not pt:
        return None
    head, mhead, name, money, tl = pt
    if DISCLOSURE not in head or any(n in head for n in (TOSS_NOTE, NAVER_NOTE, OY_NOTE, AFF_NOTE)) or cat == "beauty" or th_beauty(title or name) or th_beauty(name) \
            or re.search(f"{TH_C_SKIP}|{WU_HEALTH}", f"{title} {name}"):  # 전체 제목(괄호 안 '탈모 증상 완화' 등)까지
        return None  # C·S = 쿠팡 딜만(네이버·올영 = 프로그램 문구 본문 맨 앞, 토스 = 게시 시점 가격 같이 — 10/25 리뷰) · 화장품·건강 품목 X(상황→상품 = 효능 주장)
    g = th_c_gen(kind, name, CAT_META.get(cat, ("", ""))[1] if cat else "", toss)
    if not g:
        return None
    why, link = th_why(link, tl), re.sub(r"[?]ref=th$", f"?ref=th{kind}", link)  # 사이트 딜 쪽 링크 = GoatCounter 꼬리표 thC·thS(B 댓글 = thc)
    if kind == "C":
        body = "\n\n".join([f"[광고] {g['hook']}", "\n".join(g["lines"]), g["tease"]])
        reply = "\n\n".join([head, "\n".join([g["answer"], mhead, name, money, tl]), f"{why}\n👉 {link}"])
    else:
        body = "\n\n".join([f"[광고] {g['hook']}"] + ["\n".join(z) for z in g["scenes"]] + ["\n".join([g["close"], name])])  # 상품 = 끝 2줄(가격·시각은 첫 댓글 — 시각 없는 가격 X)
        reply = "\n\n".join([head, "\n".join([mhead, name, money, tl]), f"{why}\n👉 {link}"])
    while th_len(body) > 480 and kind == "S" and max(map(len, g["scenes"])) > 3:  # 길면 장면마다 끝 줄부터(3줄까지)
        g["scenes"] = [z[:-1] if len(z) == max(map(len, g["scenes"])) and len(z) > 3 else z for z in g["scenes"]]
        body = "\n\n".join([f"[광고] {g['hook']}"] + ["\n".join(z) for z in g["scenes"]] + ["\n".join([g["close"], name])])
    if th_len(body) > 480 or th_len(reply) > 490:
        print("th c 길이 넘음", kind, th_len(body), th_len(reply))
        return None
    return body, reply



def th_gap(last):
    """개별 글 간격 = TH_SOLO_GAP ± TH_GAP_JITTER(10/21 밤 진우 '35~55분 무작위') — 앞 개별 글 시각으로 정함(실행마다 다시 뽑으면 짧은 쪽으로 쏠림)."""
    return TH_SOLO_GAP + (random.Random(int(last)).randint(-TH_GAP_JITTER, TH_GAP_JITTER) if TH_GAP_JITTER else 0)


def th_deal(seen, tok, me, text, link, src=None, cat=None, image=None, tids=None):
    """Threads 개별 딜 글 1개(threads_deals·토스 픽 채움·슬롯 줄·뷰티 채움·토스 이름 예약·재오픈 — 묶음·날씨·간식·투표·#일상은 th_post 그대로).
    TH_LINK_AB면 직전 개별 딜 글이 A였으면 B: 본문 주소 없이(미리보기 X) 올리고 바로 첫 댓글 = 링크. 댓글 못 다는 토큰(th_reply_ok)이면 A.
    B 댓글이 실패하면 관리자 알림 + 다음 실행에 1번 더(th_retry — 링크 없는 딜 글이 남지 않게). 글마다 A/B·댓글 id -> seen(metrics.json 줄 ab·rv·48시간 v48·rv48)."""
    tt, topic = title_of(text), th_topic(seen, text, cat=cat)  # 지금 틀 제목(사람 느낌 글은 첫 줄이 문장 -> metrics 분류·가격대는 이걸로) · 주제 = 품목 칸(10/23 진우)
    cat = cat or cat_of({"text": src or text}) or None  # C·S 글 품목(Claude 재료)
    vt = th_voice(seen, text, link, src) if TH_VOICE else text  # 10/21 밤 진우 '사람이 올리는 느낌'(실패·조건 안 맞으면 지금 틀)
    voiced, text = vt != text, vt
    st, now = seen.get("thab", {}), time.time()
    kst, cx = time.gmtime(now + 9 * 3600), TH_C and voiced and now >= kst_ts(TH_C_FROM)
    seq = ("A", "B", "C") if cx else ("A", "B")  # 10/25 C 추가 = A→B→C 돌림(그 전·지금 틀 글 = A↔B)
    ab = seq[(seq.index(st["last"]) + 1) % len(seq)] if st.get("last") in seq else "A"
    ab = ab if ab == "A" or TH_LINK_AB and th_reply_ok(seen) else "A"
    sday = time.strftime("%Y-%m-%d", kst)
    scene = cx and ab != "A" and TH_SCENE_H[0] <= kst.tm_hour < TH_SCENE_H[1] and seen.get("thscene", {}).get("d") != sday  # '상황 3장면' = 하루 1개(돌림 차례는 그대로 둠)
    toss = TOSS_NO_CMP and is_toss(link, src or text)
    cs, kind = (th_c_post("S", text, link, cat, toss, tt), "S") if scene else (None, ab)
    if not cs and ab == "C":
        cs, kind = th_c_post("C", text, link, cat, toss, tt), "C"
    if cs:
        body, reply = cs
    else:
        kind = ab = "A" if ab == "C" else ab  # C를 못 만들면 A(링크 본문) · 3장면을 못 만들면 그 차례 그대로
        body, reply = th_ab(text, link) if ab == "B" else (text, None)
    image = image if not (tids and set(map(str, tids)) & toss_noimg()) else None  # 줄에 선 사이 셀러 요청(toss_noimg.txt) = 글만
    ph, rlink = None, None
    if image and not reply and TH_REPLY and th_reply_ok(seen):  # 댓글 못 다는 토큰·TH_REPLY 끔 = 지금처럼 글 + 링크 · K-1(10/26): 사진 글 = 본문(대가성 첫 줄 그대로·주소 X) + 사진(쿠팡 실사·토스 썸네일 주소 그대로 — 토스 = 끝 '사진: 토스쇼핑') -> 링크 = 첫 댓글 + 링크 카드
        pbody = th_ab(body, link)[0] + (f"\n\n{PHOTO_CREDIT}" if tids else "")
        ph = th_len(pbody) <= 500 and th_img(tok, me, pbody, image, topic)
        if ph:  # 사진 실패·500자 = 지금처럼 글 + 링크(본문)
            body, reply, rlink = pbody, (body.split("\n\n", 1)[0] + "\n\n" if body.startswith(NOTE_STARTS) else "") + f"👉 구매 링크 {link}", link  # 댓글도 대가성 문구 첫 줄(th_ab B와 같게)
    pid, rid = (ph or th_text(tok, me, body, None if reply else link, topic) or {}).get("id"), None
    if ph and pid and tids:
        tph_log(seen, tids, th=pid)
    if pid and voiced and kind in ("A", "B") and seen.get("thvoice", {}).get("h"):  # U 훅 돌림 = 올라간 글만
        seen["thhook"] = {"t": now, "l": (seen.get("thhook", {}).get("l", []) + [seen["thvoice"]["h"]])[-2:]}
    if pid and kind in ("C", "S"):
        print("th", kind, clip(tt, 30), "| 본문", th_len(body), "· 댓글", th_len(reply))
        if kind == "S":
            seen["thscene"] = {"t": now, "d": sday}  # 올라간 뒤에만(실패 = 그날 다음 칸에 다시)
    if reply:
        try:
            rid = th_reply(tok, pid, reply, rlink)
        except Exception as e:
            seen[f"thabq_{pid}"] = {"t": now, "id": pid, "text": reply}
            alert(seen, f"alert_thab_{pid}", f"⚠️ Threads 개별 딜 글({kind}: 링크는 첫 댓글)의 링크 댓글 실패: {err_brief(e)}\n다음 실행에 1번 더 달아요 — 그래도 안 되면 다시 알려요\n링크: {reply.split('👉 ')[-1].split(chr(10))[0]}")
    seen["thab"] = {"t": now, "last": st.get("last") if kind == "S" else ab, "m": {**{k: v for k, v in st.get("m", {}).items() if now - v["ts"] < 4 * 86400}, **({pid: {"ab": kind, "ts": now, "u": link, "n": tt, **({"tone": seen["thvoice"]["s"]} if voiced and kind in ("A", "B") and "s" in seen.get("thvoice", {}) else {}), **({"hook": seen["thvoice"]["h"]} if voiced and kind in ("A", "B") and seen.get("thvoice", {}).get("h") else {}), **({"r": rid} if rid else {}), **({"ph": 1} if ph else {})}} if pid else {})}}  # ph = 사진 글(K-1) · u = 링크(B 본문엔 주소가 없어 metrics가 몰을 못 읽음) · n = 제목 · v = 사람 느낌 글 말투(A 반말·B 음슴체)
    return pid


def th_img(tok, me, text, image, tag="핫딜"):
    """Threads 사진 글 1개(IMAGE — 원본 이미지 주소 그대로 · 링크는 본문) -> 결과 / 실패 = None(부르는 쪽이 글만으로)."""
    try:
        q = urllib.parse.urlencode({"media_type": "IMAGE", "image_url": image, "text": text, "topic_tag": tag, "access_token": tok})
        cid = json.loads(http(f"{THREADS}/{me}/threads?{q}", method="POST"))["id"]
        time.sleep(30)  # 미디어 처리 대기(공식 권장)
        return th_ok(json.loads(http(f"{THREADS}/{me}/threads_publish?creation_id={cid}&access_token={tok}", method="POST")))
    except Exception as e:
        print("th photo 안 됨 -> 글만", err_brief(e))
        return None


def th_carousel(tok, me, text, images, tag="핫딜"):
    """Threads 캐러셀 글 1개(사진 2~10장 — 사진마다 IMAGE 항목(is_carousel_item) -> CAROUSEL, 링크는 본문) -> 결과 / 실패 = None(부르는 쪽이 글만으로)."""
    try:
        kids = [json.loads(http(f"{THREADS}/{me}/threads?" + urllib.parse.urlencode({"media_type": "IMAGE", "image_url": u, "is_carousel_item": "true", "access_token": tok}), method="POST"))["id"] for u in images[:10]]
        time.sleep(30)  # 미디어 처리 대기(공식 권장)
        q = urllib.parse.urlencode({"media_type": "CAROUSEL", "children": ",".join(kids), "text": text, "topic_tag": tag, "access_token": tok})
        cid = json.loads(http(f"{THREADS}/{me}/threads?{q}", method="POST"))["id"]
        time.sleep(10)
        return th_ok(json.loads(http(f"{THREADS}/{me}/threads_publish?creation_id={cid}&access_token={tok}", method="POST")))
    except Exception as e:
        print("th carousel 안 됨 -> 글만", err_brief(e))
        return None


def th_text(tok, me, text, link, tag="핫딜"):
    """Threads 글 1개(TEXT + 링크 미리보기). 미리보기를 못 만들면(4279047 'Invalid Link Attachment', 10/7 15:51) 첨부 없이 1번 더 — 본문 주소는 그대로."""
    for att in ({"link_attachment": link}, {}) if link else ({},):  # 링크 없음(A/B 시험 B 본문) = 미리보기 없이
        q = urllib.parse.urlencode({"media_type": "TEXT", "text": text, **att, "topic_tag": tag, "access_token": tok})
        cid = json.loads(http(f"{THREADS}/{me}/threads?{q}", method="POST"))["id"]
        time.sleep(10)
        try:
            return th_ok(json.loads(http(f"{THREADS}/{me}/threads_publish?creation_id={cid}&access_token={tok}", method="POST")))
        except urllib.error.HTTPError as e:
            if not att or "4279047" not in (getattr(e, "body", "") or ""):
                raise


def digest(seen, posts):
    """매일 21시(KST) 이후 1회: 오늘 게시한 딜 모아보기 -> 채널에 바로(10/10~, 실패하면 ✅ 초안). 바로 뒤 블로그용 글(길면 나눠서, 실패하면 다음 실행에 다시)·카드·릴스."""
    kst = time.gmtime(time.time() + 9 * 3600)
    key, today = time.strftime("digest_%Y%m%d", kst), time.strftime("%Y-%m-%d", kst)
    todays = [p for p in posts if p["t"].startswith(today) and not p["text"].startswith("📋") and not p.get("shelf")]  # 사이트 진열(shelf) = 모아보기·블로그 X
    if kst.tm_hour < 21 or not todays:
        return

    def blog():  # 실패하면(10/6: 4096자 초과) 다음 실행에 다시 — 모아보기 초안은 한 번만
        if tg("sendMessage", chat_id=ADMIN, text=blog_text(todays, kst), link_preview_options={"is_disabled": True}):
            seen["blog_" + key[7:]] = time.time()
    if key in seen:
        if "blog_" + key[7:] not in seen:
            blog()
        return
    if busy(seen, cap=False):  # 10분 안에 다른 묶음 글 -> 다음 실행에(모아보기는 하루 1번이라 조금 늦어도 됨)
        return
    urls = [(post_url(p["mid"]) if not site_ok(p) and p.get("mid") else f"{SITE}p/{posts.index(p)}.html?ref=tg") if aff_note(p["url"] or "") == OY_NOTE or len(p["url"] or "") > 150 else p["url"] for p in todays]  # 사이트에서 뺀 딜 = 쪽이 없음 -> 채널 글(10/25 리뷰)  # 올영: 링크만 나열 금지(FAQ) -> 사이트 · 아주 긴 주소(G마켓 검색 링크 ~400자)도 사이트 딜 페이지로(같은 구매 버튼, 텔레그램 링크 길이 한도)
    night = night_deals(seen, today + f" {PREVIEW_HOUR:02d}:00", night_window(time.time())[1])  # 밤 10시 미리보기가 안 나갈 만큼 적은 날(PREVIEW_MIN개 미만) = 여기에 합침
    night = night if len(night) < PREVIEW_MIN else []
    toss_in = toss_list(todays) or (TOSS_NO_CMP and any(is_toss(d["url"]) for d in night))  # 합친 밤 줄도 같은 글
    if toss_in:  # 토스 딜이 든 모아보기 = 밤 줄도 다른 몰 비교 X(toss 밤 딜과 같은 처리)
        night = [{**d, "sv": None, "weak": d["weak"] and "특가로는 약함"} for d in night]
    rows = [f"{n}. <a href=\"{esc(u)}\">{esc(list_name(p, toss_in))}</a>" for n, (p, u) in enumerate(zip(todays, urls), 1)]
    notes = "\n".join(f"<i>{n}</i>" for n in dict.fromkeys(aff_note(u or "") for u in urls + [d["url"] for d in night]) if n)  # 제휴 링크 프로그램마다 1줄 맨 위(TOP 글과 같은 방식) — 밤 줄 링크도
    tail = f"\n\n🔎 지난 딜 전체 보기: {SITE}all.html?ref=tg\n📝 블로그: {BLOG}\n📲 실시간 알림: https://t.me/hotdeal_pick"
    if night:
        tail = "\n\n🌙 <b>오늘 밤 예약 특가</b>\n" + "\n".join(night_line(d) for d in night) + tail
    while True:  # 텔레그램 4096자(링크 주소 빼고 보이는 글자)·서식 100개(링크·굵게·기울임 + 글 속 주소 — 10/11 21시 딜 100개 넘어 ENTITIES_TOO_LONG) — 딜이 아주 많은 날은 뒤쪽을 '외 N개'로 줄임
        more = f"\n… 외 {len(todays) - len(rows)}개는 사이트에서" if len(rows) < len(todays) else ""
        text = (notes + "\n\n" if notes else "") + f"📋 <b>오늘의 딜 모아보기 ({kst.tm_mon}/{kst.tm_mday})</b>\n\n" + "\n".join(rows) + more + (f"\n\n{toss_when()}" if toss_in else "") + tail
        seen_text = html.unescape(re.sub(r"<[^>]+>", "", text))
        if (len(seen_text) <= 4000 and len(re.findall(r"<(?:a|b|i)[ >]", text)) + seen_text.count("http") <= 90
                and sum(map(len, re.findall(r'href="([^"]*)"', text))) <= 5000) or len(rows) <= 1:  # 링크 주소 합도(10/11 21:39: 82개·9,863자 -> ENTITIES_TOO_LONG)
            break
        rows.pop()
    if (tg("sendMessage", chat_id=CHANNEL, text=text, parse_mode="HTML", link_preview_options={"is_disabled": True}) and not bundled(seen)) or draft(text):  # 10/10 진우 '✅ 없이 자동 게시' — 채널 게시가 실패하면 예전처럼 초안
        seen[key] = time.time()
        blog()
        import cards
        try:  # Threads/인스타용 카드 -> docs/cards/ (워크플로가 커밋 -> 사이트에 공개 -> 다음 실행 때 threads()가 올림)
            order = day_deals(posts, today)
            os.makedirs("docs/cards", exist_ok=True)
            json.dump([i for i, _ in order], open(f"docs/cards/{today}.json", "w"))  # 카드 번호 순서를 고정(사이트·캡션이 같이 씀)
            ct = toss_list([p for _, p in order[:CARD_N]])  # 카드에 토스 딜이 있으면 몰 이름 X
            cards.make([{"title": list_name(p, ct, True), "unit": p.get("unit")} for _, p in order], f"{kst.tm_mon}월 {kst.tm_mday}일", f"docs/cards/{today}.png")
            if IG_CAROUSEL and E.get("IG_TOKEN"):
                deal_slides(today, [p for _, p in order[:CARD_N]])  # 인스타 넘기기용 딜 카드(재료 채운 글은 아래 릴스도 같이 씀)
        except Exception as e:
            print("card", repr(e))
        try:  # 인스타 릴스용 15~20초 영상 -> 관리자에게 바로 전송 + REEL_PUBLIC이면 docs/reels/에 공개 -> 22시 ig_reel이 인스타에. 점수 높은 순 TOP3 · H = 점심 테마 넘기기 릴스(ig_theme_reel)
            if IG_H:
                raise StopIteration("H — 테마 넘기기 릴스")
            top = [p for _, p in card_order(posts, today)][:3]  # 카드와 같은 순서(점수, 같으면 제휴 딜 먼저)
            auto = REEL_PUBLIC and E.get("IG_TOKEN") and E.get("IG_USER_ID")
            path, cap, _ = make_reel(top, kst, f"docs/reels/{today}.mp4" if auto else os.path.join(tempfile.gettempdir(), f"reel_{today}.mp4"))
            if auto:
                seen["reel_" + today] = {"t": time.time(), "cap": cap}  # 22시 ig_reel이 같은 캡션으로
            tg_video(path, (f"🎬 {REEL_HOUR}시에 인스타 자동 게시돼요(직접 올리지 마세요) — 확인용\n\n" if auto else "") + cap)
        except Exception as e:
            print("reel", repr(e))


TTS_URL, TTS_VOICES, TTS_RATE = "https://texttospeech.googleapis.com/v1/text:synthesize", ("ko-KR-Wavenet-A", "ko-KR-Standard-A"), 1.1  # 릴스 나레이션(10/24 Cowork·진우): Google Cloud TTS 공식만(edge-tts X)


def tts(text, rate=TTS_RATE):
    """Google Cloud Text-to-Speech 한국어 -> WAV bytes(LINEAR16 24kHz) 또는 None. 키 = GOOGLE_TTS_KEY(진우가 GCP에서 만들어 Secrets에 직접) — 헤더로만 보냄(주소·로그 X).
    키 없거나 실패 = None(릴스는 글자 + 음악). WaveNet이 안 되면 Standard 목소리로 한 번 더."""
    key = E.get("GOOGLE_TTS_KEY")
    if not key or not text:
        return None
    err, auth = "", False
    for v in TTS_VOICES:
        try:
            r = json.loads(http(TTS_URL, {"input": {"text": text}, "voice": {"languageCode": "ko-KR", "name": v},
                                          "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 24000, "speakingRate": round(rate, 2)}}, {"X-Goog-Api-Key": key}, "POST"))
            wav = base64.b64decode(r["audioContent"])
        except Exception as e:
            err, auth = f"{type(e).__name__} {getattr(e, 'code', '')}".strip(), getattr(e, "code", 0) in API_AUTH
            print("tts", v, err)
            continue
        if "tts" not in API_ST:
            print("tts ok", v)
        API_ST.setdefault("tts", "ok")
        return wav
    print("tts fail", err)
    if auth:  # 키·권한 오류만 '실패' 알림(네트워크·5xx·429 = 로그만 — 한 번 끊겼다고 키 탓 알림 X, 10/25 리뷰)
        API_ST.setdefault("tts", "fail " + err)
    return None


def say_ko(s):
    """나레이션으로 읽을 말(자막은 그대로): 괄호·이모지·기호 빼고 숫자 뒤 단위를 한국어로(100g -> 100그램 · 1+1 -> 1 플러스 1)."""
    s = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", s)
    s = re.sub(r"(?<=[\dgGlL가-힣])\s*[x×X*]\s*(?=\d)", " ", s)  # 2L x 24개·190mlX32(영문 모델명 WX242는 그대로)
    s = re.sub(r"(?<=\d)\s*~\s*(?=\d)", "에서 ", s)
    for a, b in ((r"kg", "킬로그램"), (r"mg", "밀리그램"), (r"(?-i:g)", "그램"), (r"ml", "밀리리터"), (r"l", "리터"), (r"cm", "센티미터"), (r"mm", "밀리미터")):
        s = re.sub(r"(?<=\d)\s*" + a + r"(?![a-z])", b, s, flags=re.I)
    s = re.sub(r"(?<=\d)\s*\+\s*", " 플러스 ", s)  # 1+1 · 1+ 한우
    s = re.sub(r"\s*[·/|~]\s*", ", ", s)
    s = re.sub(r"[^0-9A-Za-z가-힣\s,.%]", " ", s)
    return re.sub(r"\s+", " ", re.sub(r"(\s*,)+", ",", s)).strip(" ,")


def reel_say(top, kst, unit=True, nmax=14, head=None):
    """릴스 나레이션 대본(10/24 Cowork·진우 — 사실만, 효능·과장·'써보니' X) -> [(자막, 읽을 말)] 표지·딜마다·끝.
    표지 = 우리 데이터 한 줄('오늘 밤 12시 마감 포함' — 사이트 '오늘 마감'과 같은 판단 + 오늘의 가성비 TOPn) · 딜 = 짧은 이름(nmax자), 가격, 단위가격(unit=False면 빼고) · 끝 = 핫딜픽에서 더 보기.
    딜 한 장 ~3초(10/24 첫 실행: 긴 이름이면 1.4배로도 20초 넘음) -> 이름 = 수량·용량 낱말 빼고 nmax자 안(일부 수량만 남으면 가격이 그 양인 것처럼 들림 — 단위가격이 따로)."""
    import cards
    day = time.strftime("%Y-%m-%d", kst)
    head = ("오늘 밤 12시 마감 포함 · " if any(day_end(p, day) for p in top) else "") + (head or f"오늘의 가성비 TOP{len(top)}")
    rows = [(head, say_ko(head.replace(f"TOP{len(top)}", "탑 " + ("원", "투", "쓰리")[len(top) - 1])))]
    for p in top:
        it = cards._norm(card_item(p)[0])
        w = [x for x in re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", it["name"]).split() if not re.fullmatch(r"[+xX×*,·/]+", x)]
        w = [x for x in w if not re.search(r"\d", x)] or w[:1]
        name = " ".join(w[:next((k for k in range(len(w), 0, -1) if len(" ".join(w[:k])) <= nmax), 1)])
        parts = [x for x in (name, it["main"], it["unit"] if unit else "") if x]
        rows.append((" · ".join(parts), say_ko(", ".join(parts))))
    return rows + [("핫딜픽에서 더 보기", "핫딜픽에서 더 보세요")]


def reel_voice(rows):
    """대본 -> [(자막, WAV)] 또는 None(키 없음·실패 — 글자 + 음악). 장 길이 합이 20초 넘으면 더 빠르게 한 번 더 읽힘(최대 1.4배), 그래도 넘으면 None."""
    import cards
    rate = TTS_RATE
    try:
        for _ in range(2):
            wavs = []
            for _s, sp in rows:  # 하나라도 실패하면 바로 그만(멈춘 API를 장마다 기다리지 않게)
                wavs.append(tts(sp, rate))
                if not wavs[-1]:
                    return None
            segs = [cards._wav(w)[3] for w in wavs]
            total = sum(cards.reel_plan(segs, len(rows) - 2))
            if total <= 20:
                print("reel narration", f"{total:.1f}초 · {rate:.2f}배")  # 정기 점검용(몇 초·몇 배로 됐는지)
                return [(sub, w) for (sub, _), w in zip(rows, wavs)]
            sp = sum(x for x in segs if cards.LEAD + x + cards.TAIL > 3)  # 줄일 수 있는 건 3초 넘는 장의 말뿐(여백·3초 기본은 그대로)
            rate = min(1.4, rate * sp / max(0.1, sp - (total - 19.5)))
    except Exception as e:  # 깨진 음성(WAV 아님 등) = 글자 + 음악
        print("reel voice", type(e).__name__)
        return None
    print("reel narration 20초 넘음", f"({rows[1][0][:20]}…)" if len(rows) > 2 else "")
    return None


def make_reel(top, kst, out, k=0, safe=False, label=None):
    """릴스 1편(모아보기·샘플 같이): 재료 채움 -> 나레이션(GOOGLE_TTS_KEY 있으면) -> 영상(cards.reel) -> (경로, 캡션, 나레이션 됐는지).
    배경음악 = 라이선스 기록된 곡(MUSIC.md) 중 오늘 차례 + k. 캡션 = 대가성 문구 맨 앞(ig_notes) 그대로."""
    import cards
    fill_reel(top)  # ✅로 올린 글·예전 글은 릴스 재료가 없음 -> 여기서 채움(딜 카드 때 채웠으면 그대로)
    music, song = bgm(kst, k), song_of(kst, k)
    voice = None
    for kw in ({}, {"nmax": 8}, {"unit": False}) if E.get("GOOGLE_TTS_KEY") else ():  # 20초 넘으면 이름 더 짧게 -> 그래도 넘으면 단위가격 빼고
        voice = reel_voice(reel_say(top, kst, head=label and f"오늘의 {label}", **kw))
        if voice:
            break
    if E.get("GOOGLE_TTS_KEY"):
        print("reel", "나레이션 " + (("이름 8자" if kw.get("nmax") else "단위가격 뺌" if kw else "기본") if voice else "X — 글자 + 음악"))
    path = cards.reel([card_item(p)[0] for p in top], f"{kst.tm_mon}월 {kst.tm_mday}일", out, music, say=voice, **({"safe": True, "label": label} if safe else {}))  # 올리브영 딜은 딜 카드처럼 거른 재료
    cap = (ig_notes(top) + "\n\n" + (top[0].get("hook") + " · " if top[0].get("hook") else "") + f"{kst.tm_mon}월 {kst.tm_mday}일 가성비 TOP{len(top)}\n\n"
           + "\n".join(f"{n}. {title_of(p['text'])}" for n, p in enumerate(top, 1))
           + (f"\n\n🎵 {song['name']}" + (" (Pixabay)" if "pixabay.com" in song.get("page", "") else "") if music and song else "")
           + f"\n\n🛒 구매: 프로필 링크(hotdealpick.kr) → '{card_name(time.strftime('%Y-%m-%d', kst))}'에서 1~{len(top)}번"  # 릴스 TOP = 하루 카드 앞 번호
           + "\n\n" + ig_tags(top, kst.tm_mday))[:1024]
    return path, cap, bool(voice)


def reel_samples(seen):
    """릴스 새 틀 샘플 3편(10/24 Cowork·진우 '나레이션·움직임·배경음악'): 관리자에게만(공개 X — REEL_PUBLIC은 진우 OK 뒤), 실행마다 1편(작업 6분 제한).
    한 벌 = 최근 4일 중 딜 있는 날 3개 × 그날 TOP3, 곡은 편마다 다르게. 처음 1벌 -> 나레이션이 안 됐으면 키가 새로 생길 때 바로, 키가 있었는데 실패였으면 하루 뒤 다시(최대 2번)."""
    v, key, now = seen.get("reel_v3"), bool(E.get("GOOGLE_TTS_KEY")), time.time()  # v3 = 10/25 대본 줄인 뒤 새 한 벌(v2 첫 편은 20초 넘어 나레이션 X)
    if v:
        v["t"] = now  # seen.json은 t가 3일 지난 칸을 버림 -> 실행마다 새로(안 그러면 3일마다 샘플을 또 보냄) · 한 벌 만든 때 = t0
    if v and v.get("n", 0) >= 3 and (v.get("tts") or not key or v.get("key") and (now - v["t0"] < 86400 or v.get("r", 0) >= 2)):
        return
    if not v or v.get("n", 0) >= 3:  # 새 한 벌(r = 키가 있었는데 나레이션 실패로 다시 — 최대 2번)
        v = seen["reel_v3"] = {"t": now, "t0": now, "key": key, "tts": False, "n": 0, "r": v.get("r", 0) + 1 if v and v.get("key") else 0}
    posts, n = load(POSTS, []), v["n"] + 1
    days = [time.gmtime(v["t0"] + 9 * 3600 - d * 86400) for d in range(4)]
    sets = [x for x in ((k, [p for _, p in card_order(posts, time.strftime("%Y-%m-%d", k))][:3]) for k in days) if x[1]][:3]
    v["n"] = n if n < len(sets) else 3  # 먼저 기록(보내다 실패해도 15분마다 같은 편을 또 만들지 않게)
    if n > len(sets):
        return
    kst, ps = sets[n - 1]
    try:
        path, cap, said = make_reel(ps, kst, os.path.join(tempfile.gettempdir(), f"reel_sample{n}.mp4"), n + days[0].tm_yday - kst.tm_yday)  # 곡 = 오늘 차례 + n(편마다 다름)
        v["tts"] = v["tts"] or said
        tg_video(path, f"🎬 릴스 새 틀 샘플 {n}/{len(sets)} — " + ("나레이션 O" if said else "나레이션 X(GOOGLE_TTS_KEY 없음·실패 — 글자 + 음악)")
                 + " · 켄번스·0.3초 전환·자막 · 공개 X(진우 OK 뒤 REEL_PUBLIC)\n\n" + cap)
    except Exception as e:
        print("reel sample", n, repr(e))
        tg("sendMessage", chat_id=ADMIN, text=f"🎬 릴스 샘플 {n} 실패({type(e).__name__}) — 다음 편은 다음 실행에")


CLIP_AT, CLIP_LINK = {"A": 9, "B": 13}, "hotdealpick.kr/link?ref=clip"  # Q(10/26 진우): 네이버 클립 하루 2편 -> 관리자 텔레그램만(진우가 클립에 직접 올림) · 프로필 링크(진우가 클립 프로필에)


def clip_post(seen):
    """Q 네이버 클립 영상(1080x1920·30fps·H.264 + AAC 44.1kHz·15~20초 · 첫 장 '광고·제휴' · 아래 25%·오른쪽 15% 글자 X — cards.reel safe) 하루 2편, 실행마다 1편:
    A(CLIP_AT A시~) = 쿠팡 핫딜 3(3일 안 지금 특가 딜 점수 > 최근 순 · 지난 클립 상품 X — 릴스 틀, 3개일 때만) · 캡션 = 쿠팡 파트너스 문구 + '프로필 링크에서 보기' + 해시태그 5개
    B(B시~) = 네이버 쇼핑커넥트(진우 naver.me 글) 1개 글자 카드(상품 사진 X — 릴스 틀은 이모지 타일) · 캡션 첫 줄 = 쇼핑 커넥트 문구 + 상품 태그 붙이는 법·naver.me 링크(열지 않음)
    파일 = clip_MMDD_A/B.mp4 · 재료 없음·실패 = 그날 그 편 X(관리자에게 1줄) · seen clip = 이번 달 보낸 수(일요일 DM 줄)."""
    kst, now = time.gmtime(time.time() + 9 * 3600), time.time()
    day, st = time.strftime("%Y-%m-%d", kst), seen.get("clip") or {}
    k = next((k for k, h in CLIP_AT.items() if kst.tm_hour >= h and st.get(k) != day), None)
    if not k:
        return
    st = seen["clip"] = {**st, "t": now, k: day}  # 먼저 기록(실패해도 15분마다 다시 만들지 않게)
    if st.get("m") != day[:7]:
        st.update(m=day[:7], n=0)
    posts = load(POSTS, [])
    if k == "A":
        days = [time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600 - d * 86400)) for d in range(3)]
        ds = sorted(sorted((p for d in days for _, p in day_deals(posts, d) if urllib.parse.urlsplit(p.get("url") or "").netloc in CP_SHORT and p.get("st") in (None, "hot")
                            and "원" in parse(title_of(p["text"]))[2] and p["url"] not in st.get("u", [])), key=lambda p: p["t"], reverse=True), key=lambda p: -p.get("s", 0))  # 3일 안 쿠팡 딜(지금 특가 · 가격 있는 한 상품 글 — 골드박스 모음 X) 점수 > 최근 순
        top = [p for i, p in enumerate(ds) if p["url"] not in {x["url"] for x in ds[:i]}][:3]  # 같은 상품 두 번 X
        top = top if len(top) == 3 else []  # '쿠팡 핫딜 3' = 3개일 때만
        label, cap = None, f"{DISCLOSURE}\n\n오늘의 쿠팡 핫딜 3 — 프로필 링크에서 보기\n\n" + ig_tags(top, kst.tm_mday)
    else:
        top = [p for p in reversed(posts) if urllib.parse.urlsplit(p.get("url") or "").netloc == "naver.me" and now - kst_ts(p["t"]) < 7 * 86400 and p["url"] not in st.get("u", [])][:1]  # 최근 7일 진우 쇼핑커넥트 글 중 아직 안 만든 것
        label, cap = "네이버 쇼핑 픽", f"{NAVER_NOTE}\n\n" + "\n\n".join(title_of(p["text"]) for p in top) + "\n\n" + ig_tags(top, kst.tm_mday)
    if not top:  # 재료 없음 = 그날 그 편 X — 진우가 고장으로 안 보게 1줄
        tg("sendMessage", chat_id=ADMIN, text=f"🎬 네이버 클립 {k} — 오늘은 건너뜀(" + ("최근 3일 쿠팡 핫딜이 3개 안 됨" if k == "A" else "최근 7일 새 쇼핑커넥트(naver.me) 글 없음") + ")")
        return
    out = os.path.join(tempfile.gettempdir(), time.strftime(f"clip_%m%d_{k}.mp4", kst))
    try:
        said = make_reel(top, kst, out, ord(k) - 64, safe=True, label=label)[2]  # 곡 = 오늘 차례 + 1·2(A·B 다르게)
        tg_video(out, cap)
    except Exception as e:
        print("clip", k, repr(e))
        tg("sendMessage", chat_id=ADMIN, text=f"🎬 네이버 클립 {k} 실패({type(e).__name__}) — 오늘 {k}편은 건너뜀")
        return
    st["n"] = st.get("n", 0) + 1
    st["u"] = (st.get("u", []) + [p["url"] for p in top])[-40:]  # 만든 상품(A·B) = 다음 클립에 다시 X
    tg("sendMessage", chat_id=ADMIN, link_preview_options={"is_disabled": True}, text=f"🎬 네이버 클립 {k} — {os.path.basename(out)} · 나레이션 {'O' if said else 'X'} · 위 영상 캡션 그대로\n"
       + (f"상품 태그: {parse(title_of(top[0]['text']))[1]} — 클립 편집기 정보 태그 → 쇼핑 커넥트에서 붙이기\n{top[0]['url']}" if k == "B" else f"프로필 링크: {CLIP_LINK}"))


def licensed():
    """릴스에 쓰는 곡 = 출처(page)·라이선스가 docs/reels/MUSIC.md에 기록된 곡만(10/24 Cowork '상업 이용 무료 라이선스 곡만') — 봇에 보낸 음악(출처 없음)은 X."""
    return [m for m in load(MUSIC, []) if m.get("page") and m.get("url")]


def song_of(kst, k=0):
    """오늘 차례 곡(+k — 샘플마다 다르게) -> music.json 항목 또는 None."""
    mus = licensed()
    return mus[(kst.tm_yday + k) % len(mus)] if mus else None


def bgm(kst, k=0):
    """오늘 차례 1곡(song_of) -> 파일 경로. 없거나 못 받으면 None(무음 릴스).
    url = Pixabay 음원(Claude가 고름): 처음 1번만 받아 Actions 캐시 music/에 보관(공개 저장소엔 안 올림 — 음원 단독 재배포 금지)."""
    m = song_of(kst, k)
    if not m:
        return None
    try:
        path = os.path.join("music", hashlib.sha1(m["url"].encode()).hexdigest()[:12] + ".mp3")
        if not os.path.exists(path):
            with urllib.request.urlopen(urllib.request.Request(m["url"], headers={"User-Agent": UA}), timeout=60) as r:
                data = r.read()
            os.makedirs("music", exist_ok=True)
            open(path, "wb").write(data)
        return path
    except Exception as e:
        print("bgm", repr(e))


def playlist(seen):
    """릴스 배경음악 플레이리스트(관리자 채팅): 곡이 새로 들어오면(sent 없음) 목록 글 + 전 곡을 오디오로 다시 보냄 -> 텔레그램에서
    곡을 누르면 재생되고 다음 곡으로 이어짐(곡명·아티스트는 플레이어에 표시). 원본 음원은 관리자 채팅에만(Pixabay: 단독 배포 금지)."""
    mus = load(MUSIC, [])
    if all(m.get("sent") for m in mus):
        return
    kst = time.gmtime(time.time() + 9 * 3600)
    today = song_of(kst)
    tg("sendMessage", chat_id=ADMIN, text=f"🎵 릴스 배경음악 플레이리스트 ({kst.tm_mon}/{kst.tm_mday} 갱신, {len(mus)}곡)\n\n"
       + "\n".join(f"{i}. {m['name']}" + (" ← 오늘 릴스" if m is today or m == today else "") + ("" if m.get("page") else " (출처 없음 — 릴스 X)") for i, m in enumerate(mus, 1))
       + "\n\n아래 곡을 누르면 재생돼요(다음 곡으로 이어서). Pixabay 콘텐츠 라이선스·Content ID 미등록 곡만")
    for m in mus:
        title, _, artist = m["name"].partition(" — ")
        r = tg("sendAudio", chat_id=ADMIN, audio=m.get("fid") or m.get("url") or m["id"], title=title, caption=m.get("page", ""),
               **({"performer": artist} if artist else {}))
        if r and r.get("audio"):
            m["fid"] = r["audio"]["file_id"]  # 다음 갱신 땐 텔레그램에 있는 파일로(다시 안 받음)
        elif not r:
            tg("sendMessage", chat_id=ADMIN, text=f"🎵 {m['name']} — {m.get('page', '')}", link_preview_options={"is_disabled": True})
        m["sent"] = 1
    json.dump(mus, open(MUSIC, "w"), ensure_ascii=False, indent=1)


IG_AUTO = True  # 10/23 진우 '인스타그램에도 꾸준하게 올라가게 하자'(10/31 판단 앞당김 — 지난주 '3일 연속 차단'은 3번 다 실제 게시된 오탐, README 9d926fc70 대조): 카드(ig_hours — 10/23 진우 '하루 4번' 11·15·19·22시, 3일씩 진짜 실패 0이면 5번·6번으로 — ig_stage)·넘기기. 릴스는 REEL_PUBLIC(꺼짐) 그대로
#   (10/17~10/23 꺼 둠: code 4·2207051 — False = 다시 멈춤, 남은 컨테이너는 발행 없이 지움 · 21시 카드 이미지·사이트·Threads 카드·metrics 인스타 읽기는 그대로)
IG_HUMAN = IG_AUTO  # 10/22 22시 진우 '사람처럼': 정기 카드 게시에도 15~20분 무작위 지연(IG_JITTER) + 새 디자인 한 벌(ig_set — 표지 A 남색·B 핑크·P 파스텔 칸마다 돌림, 제목은 그날 안 겹치게) + 사람 멘트 캡션(ig_human — 말투 4가지)
IG_GAP, IG_QUOTA_SHARE = 2 * 3600, 0.5  # 10/25 23시 진우 '정지 안 되게': 게시 사이 최소 2시간 · 공식 24시간 게시 한도(content_publishing_limit 응답)의 절반 안
IG_BLOCK = r"\((?:4|9|10|17|32|190|200|368|613|80002)(?:/\d+)?\)|2207051|spam|block|restrict|permission|limit reached|too many|권한|제한"  # 행동 제한·스팸·권한·한도 오류(ig_err 'code/subcode') = 그날 인스타 전부 멈춤
IG_FAIL_MAX = 2  # 10/23 진우: 진짜 실패(ig_landed 기준 안 올라감) = 그 회차만 건너뜀(다시 시도 X), 하루 IG_FAIL_MAX번이면 24시간 쉼 + 관리봇 알림
IG_TEST, IG_TEST_DIR, IG_JITTER = "ig_test.txt", "igt", (15 * 60, 20 * 60)  # 인스타만 1번 테스트(ig_test): 날짜 한 줄 = 그날 하루 카드를 변주·지연·사람 멘트로 1건(실패해도 다시 X)
IG_THEMES = {"pal": [((246, 244, 239), (255, 84, 28)), ((250, 250, 250), (37, 99, 235)), ((238, 246, 240), (22, 128, 74)), ((247, 242, 250), (124, 58, 237))],  # 0 = 지난주 막힌 카드(크림·주황)
             "head": ["오늘 살 만한 딜", "오늘 밤 살 만한 딜", "자기 전에 볼 딜", "오늘 고른 가성비 딜", "지금 담아둘 만한 딜"], "band": [False, True]}
IG_HUMAN_POOL = ("오늘 밤엔 이 정도면 살 만한 듯", "생필품 떨어진 집은 한번 볼 만함", "필요한 거 있으면 이참에 담아 둘 만함", "자기 전에 한 번 훑어보기 좋은 구성",
                 "가격 괜찮은 것만 골라 봄", "이번 주 장바구니 채울 때 참고용", "급한 거 아니면 천천히 비교하고 사도 됨", "쟁여 두는 거 좋아하면 체크해 둘 만함")  # Claude 실패 때 대신(~요·경험담·클릭 유도 X)
IG_HUMAN_PROMPT = """인스타 '오늘의 딜 카드' 게시글 아래에 붙일 짧은 멘트를 사람이 직접 쓰듯 2~3줄 써 주세요. 아래 '오늘 카드 딜'에 있는 사실만(없는 숫자 X).
- {style} 줄마다 문장 틀을 다르게, 짧은 조각 문장도 OK.
- 결 예시(그대로 쓰지 말고 비슷한 느낌만): 오늘 밤엔 이 정도면 살 만한 듯 / 휴지 떨어진 집 손 ㅋㅋ
- 써 본 척(샀는데·써보니·나도 등), 효능·건강 말, 과장(역대급·무조건), 클릭·링크·프로필·팔로우 유도, 해시태그, 광고·수수료 말은 쓰지 않기.
- '최근 멘트'와 다른 문장으로."""


def ig_variant(seen):
    """인스타 카드 변주: 직전 회차(처음이면 지난주 막힌 기본 카드)에서 표지 문구·배치(머리 띠)·색 조합 중 1~2개를 바꿈(같은 템플릿 반복 = 스팸 신호 줄이기, 10/22 진우).
    -> {"pal", "head", "band"} 번호(seen igvar에 기록) — cards.make theme·head는 ig_theme로."""
    prev = seen.get("igvar") or {"pal": 0, "head": 0, "band": 0}
    while True:
        v = dict(prev)
        for k in random.sample(sorted(IG_THEMES), random.choice((1, 2))):
            v[k] = random.choice([i for i in range(len(IG_THEMES[k])) if i != prev.get(k)])
        if v != {"pal": 0, "head": 0, "band": 0}:  # 지난주 막힌 카드와 똑같은 모양은 X
            seen["igvar"] = {**v, "t": time.time()}
            return v


def ig_theme(v):
    """ig_variant 번호 -> (cards.make theme, 표지 문구)."""
    bg, accent = IG_THEMES["pal"][v["pal"]]
    return {"bg": bg, "accent": accent, "band": IG_THEMES["band"][v["band"]]}, IG_THEMES["head"][v["head"]]


def ig_human(seen, ps):
    """인스타 캡션 대가성 문구 아래 사람 멘트 2~3줄(10/22 진우 '사람이 표현하는 다양한 멘트'): Claude(반말·음슴체 무작위, th_voice 규칙 — ~요·써 본 척·클릭 유도 X,
    재료에 없는 금액 X, 이모지 0~1, 최근 멘트와 다른 문장) — 2줄 못 채우면 IG_HUMAN_POOL에서(최근 것 빼고). 쓴 멘트는 seen ighum(최근 60개 — 하루 8번 캡션끼리도 안 겹치게)."""
    recent = seen.get("ighum", {}).get("l", [])
    facts = "\n".join(f"- {list_name(p, False)}" for p in ps)
    money = lambda x: set(re.findall(r"\d[\d,]*(?=\s*원)", x))
    tone = seen.get("ighum", {}).get("next") or pick_tone(seen, "ig")  # 10/23 진우 말투 4가지 — 같은 게시물의 상품 장 멘트(ig_lines)와 같은 말투
    ok = lambda x: ig_line_ok(x, recent, facts, TONES[tone][2])
    lines = []
    try:
        a = ai_json(IG_HUMAN_PROMPT.format(style=tone_style(tone))
                    + f"\n\n오늘 카드 딜:\n{facts}" + ("\n\n최근 멘트: " + " / ".join(recent[-8:]) if recent else ""), {"lines": {"type": "array", "items": {"type": "string"}}})
        lines = [x for x in (re.sub(r"\s+", " ", str(x)).strip() for x in a.get("lines") or []) if ok(x)][:3]
    except Exception as e:
        print("ig human 기본 멘트로", clip(repr(e), 120))
    if len(lines) < 2:
        lines = random.sample([x for x in IG_HUMAN_POOL if x not in recent] or list(IG_HUMAN_POOL), 2)
    if sum(len(re.findall(VOICE_EMOJI, x)) for x in lines) > 2:  # 이모지 0~2개 -> 넘으면 다 뺌
        lines = [x for x in (re.sub(r"\s{2,}", " ", re.sub(VOICE_EMOJI, "", x)).strip() for x in lines) if x]
    seen["ighum"] = {"t": time.time(), "l": (recent + lines)[-60:], "tone": tone}
    return lines


IG_PHOTO_NOTE = "상품 사진: 판매 페이지(쿠팡)"  # 사진 장이 있는 넘기기 캡션 — 대가성 문구 바로 아래(10/25 Cowork ②)
IG_KIND = {"cur": "큐레이션", "drop": "가격 내려간 상품", "theme": "테마 넘기기", "one": "개별 아이템", "story": "스토리"}  # 카드 칸 밖 인스타 글(igc_·igk_ kind) — 게시 기록·알림 이름


def ig_caption(seen, stem, human=False, ps=None, photo=False):
    """인스타 카드 캡션: card_caption 그대로, human이면 대가성 문구(첫 줄·공정위) 바로 아래에 사람 멘트 2~3줄(ig_human) · photo = 상품 사진 장이 있으면 대가성 문구 다음 줄에 IG_PHOTO_NOTE."""
    cap = card_caption(stem)[1]
    notes, _, rest = cap.partition("\n\n")
    notes += "\n" + IG_PHOTO_NOTE if photo else ""
    if not human:
        return (notes + "\n\n" + rest)[:2200] if photo else cap
    ps = ps if ps is not None else [p for _, p in card_order(load(POSTS, []), stem)[:CARD_N]]
    return (notes + "\n\n" + "\n".join(ig_human(seen, ps)) + "\n\n" + rest)[:2200]


def ig_card_copy(seen, day, out):
    """그날 하루 카드(21시 카드와 같은 딜·순서)를 변주(ig_variant)로 인스타용 사본 out(.jpg로 저장 — 텔레그램·사이트 하루 카드는 그대로) -> 변주 번호, 딜 IG_MIN개 미만이면 None."""
    order = card_order(load(POSTS, []), day)
    if len(order) < IG_MIN:
        return None
    import cards
    v = ig_variant(seen)
    theme, head = ig_theme(v)
    ct = toss_list([p for _, p in order[:CARD_N]])
    cards.make([{"title": list_name(p, ct, True), "unit": p.get("unit")} for _, p in order], f"{int(day[5:7])}월 {int(day[8:10])}일", out, head=head, png=False, theme=theme)
    return v


IG_TITLES = {"A": ("오늘 밤 장바구니에\n넣을 만한 {n}개", "퇴근길에 볼 만한\n딜 {n}개", "이번 주 쟁여 둘\n딜 {n}개", "자기 전에 담아 둘\n딜 {n}개",  # 제목 최대 2줄(10/22 진우 '1초 안에')
                   "지금 담아 둘 만한\n딜 {n}개", "가격 보고 고른\n딜 {n}개", "떨어지기 전에\n채워 둘 거 {n}개", "오늘 새로 올라온\n딜 {n}개", "장바구니 채울\n후보 {n}개"),
             "B": ("퇴근길에 골라 둔\n살 만한 거 {n}개", "오늘 장보기 메모\n쟁여 둘 거 {n}개", "이번 주 장바구니\n채울 거 {n}개", "생필품 체크\n살 만한 거 {n}개", "가격 괜찮은 거만\n골라 둔 {n}개")}  # 칸마다 무작위, 그날 쓴 제목은 X(10/23 진우) · 밤·퇴근 말은 18시부터
IG_KIND_SKIP = r"리필|무향|대용량|국내산|국산|프리미엄|오리지널|오리지날|기획|세트|증정|무료|무배|한정|특가|신상|정품|클래식|에디션|퍼플에디션|용기|본품"
IG_LINE_PROMPT = """인스타 넘기기 카드에 상품마다 붙일 한 줄 멘트를 사람이 직접 쓰듯 써 주세요(lines[i] = i번 상품, 개수 그대로). 아래 상품 정보에 있는 사실만(없는 숫자 X).
- {style} 30자 안팎.
- 결 예시(그대로 쓰지 말고 느낌만): 휴지·물티슈 떨어진 집이면 지금 쟁여도 됨 / 커피 매일 마시면 개당 가격 보고 고르기
- 써 본 척(샀는데·써보니·나도), 효능·건강 말, 과장(역대급·무조건), 클릭·링크·프로필 유도, 광고·수수료 말은 쓰지 않기."""


def ig_design(day, k=0):
    """인스타 카드 디자인 칸마다 돌림(10/22 진우 '번갈아' -> 10/23 '파스텔 A 표지도 좋다' 3가지 -> 10/23 '칸마다 다르게'): k = 오늘 몇 번째 칸, A 남색 표지 -> B 핑크 스티커 -> P 파스텔 표지 …
    (날짜만큼 밀어서 날마다 첫 칸이 다름 · A·P 상품 장 = 파스텔, B = B 그대로)."""
    return "ABP"[(datetime(int(day[:4]), int(day[5:7]), int(day[8:10])).toordinal() - datetime(2026, 10, 22).toordinal() + k) % 3]


def tone_style(tone):
    """인스타 멘트 프롬프트에 넣을 말투(TONES) + 공통 규칙(해요체 아닌 말투면 ~요 X)."""
    return f"{TONES[tone][1]} {TONE_RULE}" + ("" if TONES[tone][2] else " 해요체 X('~요'로 끝나는 말 쓰지 않기).")


def ig_line_ok(x, recent, facts, yo_ok=False):
    """사람 멘트 한 줄 거르기(th_voice 규칙): (해요체 말투가 아니면) ~요·써 본 척·효능·과장·클릭/링크/프로필 유도·광고 말·재료에 없는 금액 X, 60자 안, 최근 멘트와 다르게."""
    money = lambda t: set(re.findall(r"\d[\d,]*(?=\s*원)", t))
    return bool(x) and len(x) <= 60 and not x.startswith(VOICE_LABEL) and x not in recent and (yo_ok or not re.search(VOICE_YO, x)) and not re.search(VOICE_BAN, x) \
        and not re.search(r"링크|클릭|눌러|프로필|팔로우|광고|수수료|댓글|저장|#", x) and money(x) <= money(facts)


def ig_lines(seen, ps):
    """넘기기 상품 장의 한 줄 멘트(상품마다, Claude 1번) — 규칙에 안 맞거나 실패면 ''(그 장은 멘트 없이)."""
    facts = "\n".join(f"{k}. {list_name(p, False)}" + (f" · {p['unit']}" if p.get("unit") else "") for k, p in enumerate(ps))
    recent, tone = seen.get("ighum", {}).get("l", []), pick_tone(seen, "ig")
    try:
        a = ai_json(IG_LINE_PROMPT.format(style=tone_style(tone)) + f"\n\n상품 정보:\n{facts}", {"lines": {"type": "array", "items": {"type": "string"}}})
        got = [re.sub(r"\s+", " ", str(x)).strip() for x in a.get("lines") or []]
    except Exception as e:
        print("ig lines 없이", clip(repr(e), 120))
        got = []
    out = [x if k < len(got) and ig_line_ok(x := got[k], recent, facts, TONES[tone][2]) and len(re.findall(VOICE_EMOJI, x)) <= 2 else "" for k in range(len(ps))]
    seen["ighum"] = {"t": time.time(), "l": (recent + [x for x in out if x])[-60:], "next": tone}  # next = 이 게시물 캡션(ig_human)도 같은 말투
    return out


def ig_kind(name):
    """사진이 없을 때 칸에 쓸 상품 종류 낱말: 상품명 한글 낱말 중 브랜드(첫 낱말)·수식어 빼고 마지막(예 '도브 바디워시 1000ml 3개' -> '바디워시')."""
    ws = [w for w in re.findall(r"[가-힣]{2,}", re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", name)) if not re.fullmatch(IG_KIND_SKIP, w)]
    return (ws[1:] or ws or [""])[-1]


def ig_photo(p, d, seen=None):
    """상품 사진(10/25 Cowork ② — 판매 페이지 사진만): 쿠팡 = 글 img(파트너스 API·events img — 사이트 img_of 허용 목록) · 토스 = X(카드에 그리면 크롭·합성 + 인스타 = 토스 승인 범위 밖, 10/26 Cowork)
    · 네이버·다른 몰·커뮤니티 글 사진 = X -> (d/에 저장한 경로, 'coupang'), 없거나 못 받으면 (None, '')."""
    u = p.get("url") or ""
    try:
        img, src = img_of(p), "coupang"
        if not img:
            return None, ""
        os.makedirs(d, exist_ok=True)
        f = os.path.join(d, hashlib.md5(img.encode()).hexdigest()[:12] + ".img")
        data = urllib.request.urlopen(urllib.request.Request(img, headers={"User-Agent": "Mozilla/5.0"}), timeout=8).read(5_000_000)
        open(f, "wb").write(data)
        with __import__("PIL.Image", fromlist=["Image"]).open(f) as im:
            im.load()  # 끝까지 풀리는 사진만(verify만 통과하고 그릴 때 깨지는 사진 = 넘기기 중간에 멈춤 — 10/25 리뷰)
        return f, src
    except Exception as e:
        print("ig photo 없음", clip(u, 50), clip(repr(e), 80))
        return None, ""


def ig_items(seen, ps, photos=True):
    """인스타 새 카드 재료(cards.ig_cover·ig_slide의 it) — 이름·짧은 이름·가격·칩(단위가격 > '와우 할인' > 'N%↓')·몰 배지(채널 머리 줄 규칙)·배송·사진·이모지·종류·한 줄 멘트·가격 시각."""
    lines = ig_lines(seen, ps)
    out = []
    for p, line in zip(ps, lines):
        t, plain = title_of(p["text"]), p["text"]
        _, name, price = parse(t)
        main, _, ship = price.partition("/")
        mall = mall_of(p.get("url"), t)
        cond, dr = mall_dr(plain)
        badge = (TOSS_STEADY_HEAD if icon_of(plain) == "👍" else MALLS["toss"][0]) if mall == "toss" else (MALLS["coupang"][0] if cp_rocket(plain) else CP_PLAIN[0]) if mall == "coupang" else store_tag(t)
        arrive = re.search(r"(내일|모레|오늘)(?:\s*\([월화수목금토일]\))?\s*(?:새벽\s*)?도착", plain)
        out.append({"name": name, "short": re.sub(r",?\s*\d+\s*(?:개|팩|입|매|롤|병|캔|봉)\s*$", "", name).strip() or name, "price": main.strip(),
                    "chip": (p.get("unit") or "").split(" (")[0].strip() or ("와우 할인" if "와우" in cond else f"{dr}%↓" if dr and not cond else ""),
                    "badge": badge, "ship": arrive[0].replace("  ", " ") if arrive else "무료배송" if ship.strip() in ("무료", "무배", "무료배송") else "",
                    "e": p.get("e") or "🛒", "kind": ig_kind(name), "line": line, "when": f"{int(p['t'][5:7])}/{int(p['t'][8:10])} {int(p['t'][11:13])}시"})
        out[-1]["photo"], out[-1]["src"] = ig_photo(p, "ig_photos", seen) if photos else (None, "")
    return out


def ig_set(seen, day, ps, d, design=None, h=IG_DAY_HOUR):
    """인스타 새 디자인 한 벌(표지 + 상품 장) -> d/cover.jpg, d/01.jpg… (design 없으면 직전에 만든 표지 다음 것 — 밤 22시 -> 다음 날 11시도 다르게, 기록이 없으면 날짜·오늘 몇 번째 칸으로 A·B·P).
    표지 문구(그날 쓴 것 빼고)·칩 순서는 회차마다 무작위. -> (표지, [상품 장], 디자인)"""
    import cards
    hs, last = ig_hours(seen), seen.get("igdz", {}).get("d")
    design = design or ("ABP"[("ABP".index(last) + 1) % 3] if last in ("A", "B", "P") else ig_design(day, hs.index(h) if h in hs else 0))
    seen["igdz"] = {"t": time.time(), "d": design}
    r = seen.get("igday", {}) if seen.get("igday", {}).get("d") == day else {"d": day, "ti": []}
    pool = [x for x in IG_TITLES["A" if design == "P" else design] if h >= 18 or not re.search(r"밤|자기 전|퇴근", x)]
    title = random.choice([x for x in pool if x not in r["ti"]] or pool)
    seen["igday"] = {**r, "t": time.time(), "ti": r["ti"] + [title]}
    its = ig_items(seen, ps[:CARD_N])
    k = datetime(int(day[:4]), int(day[5:7]), int(day[8:10]))
    date_text = f"{k.month}월 {k.day}일 {'월화수목금토일'[k.weekday()]}요일" if design in "AP" else f"{k.month}.{k.day} {'월화수목금토일'[k.weekday()]}"
    slides = []
    for n, it in enumerate(its, 1):  # 사진 있는 상품만(번호 = 카드 번호) — 0장이면 표지 한 장 글
        if it.get("photo"):
            try:
                slides.append(cards.ig_photo_card(it, n, f"{d}/{n:02d}.jpg"))
            except Exception as x:  # 그 장만 X(넘기기는 나머지로)
                print("ig photo card", n, type(x).__name__)
                if os.path.exists(f"{d}/{n:02d}.jpg"):
                    os.remove(f"{d}/{n:02d}.jpg")
    chips = [{**it, "photo": None} if it.get("src") == "toss" else it for it in random.sample(its, len(its))]  # 표지 칸은 꽉 차게 자름 = 토스 사진 X(토스 = 원본 그대로·출처 표시 — 사진 장에만)
    cover = cards.ig_cover(design, chips, date_text, title.format(n=len(its)), f"{d}/cover.jpg", swipe=bool(slides),  # 표지 = 마지막(있으면 한 벌 다 됨 — ig_cards)
                           sub="최저가 아니어도 꾸준히 팔리는 것까지" if any(th_steady(p["text"]) for p in ps[:CARD_N]) else "")
    return cover, slides, design


def ig_landed(tok, uid, cid, cap="", since=0):
    """발행 오류 응답 뒤 실제로 올라갔는지(10/22 #1804: code 4·2207051 'action is blocked'인데 게시됨 — 오탐): 컨테이너 status_code = PUBLISHED이거나
    최근 게시물 1개(GET /{uid}/media?limit=1)의 캡션 앞부분이 cap과 같고 시각이 since(발행 시도) 2분 전 뒤면 -> 게시물 id(모르면 'published'), 아니면 None. 확인 실패도 None."""
    h = {"Authorization": "Bearer " + tok}
    try:
        st = json.loads(http(f"{IG}/{cid}?fields=status_code", headers=h)).get("status_code")
        x = (json.loads(http(f"{IG}/{uid}/media?fields=id,caption,timestamp&limit=1", headers=h)).get("data") or [{}])[0] if cap else {}  # 캡션 모르면 최근 게시물은 안 봄(호출 1번 아낌)
        same = cap and (x.get("caption") or "")[:80] == cap[:80] and datetime.strptime(x.get("timestamp", "1970-01-01T00:00:00+0000"), "%Y-%m-%dT%H:%M:%S%z").timestamp() >= since - 120
        return x.get("id") if same else ("published" if st == "PUBLISHED" else None)
    except Exception as e:
        print("ig landed 확인 실패", clip(repr(e), 120))
        return None


def ig_due(seen, key, base):
    """인스타 게시 무작위 지연: base(이번 회차 시작) + IG_JITTER 사이 아무 때(회차마다 1번 정해 seen에) -> 이 시각 전엔 컨테이너 X."""
    if key not in seen:
        seen[key] = {"t": base, "at": base + random.uniform(*IG_JITTER)}
    return seen[key]["at"]


IG_LIVE = "docs/cards/ig.json"  # 인스타에 올리는(컨테이너 만든)·올라간 카드 {카드 이름: 시각} — 사이트 맨 위 카드 딜이 인스타 게시물과 같은 번호(build_site.card_stems)


def ig_live(stem, now):
    """IG_LIVE에 카드 기록(7일치). 컨테이너 만든 실행에 기록 -> 같은 실행의 사이트 만들기가 맨 위 카드를 바꿈 -> 다음 실행에 인스타 발행(사이트가 먼저).
    커밋된 기록이라 seen 캐시를 잃어도 같은 카드를 다시 안 올림(ig_cards)."""
    led = {k: t for k, t in load(IG_LIVE, {}).items() if t > now - 7 * 86400}
    led[stem] = now
    os.makedirs(os.path.dirname(IG_LIVE), exist_ok=True)
    json.dump(led, open(IG_LIVE, "w"), ensure_ascii=False)


def ig_publish(seen):
    """올려둔 인스타 컨테이너(카드·릴스)가 처리 끝났으면(FINISHED) 발행. 처리 중이면 다음 실행에.
    카드는 만든 실행에 사이트 맨 위에 먼저 뜨고(ig_live) IG_SITE_LAG 지난 뒤 발행(상태 조회도 그때부터 — 그래프 API 호출 줄이기). 이미 PUBLISHED = 게시 완료로.
    10/23 진우: 발행 오류 -> ig_landed로 확인, 올라갔으면 성공(쉼 X) · 아니면 다음 실행에 상태만 다시 봄(다시 발행 X) -> 그래도 안 올라감·처리 ERROR·EXPIRED = 진짜 실패(ig_fail — 그 회차만 건너뜀,
    하루 IG_FAIL_MAX번이면 24시간 쉼 + 알림). 하루 ig_day_max개까지(그 단계 횟수 + 1, 넘으면 다음 날 — 컨테이너는 24시간 유효)."""
    tok, uid = E.get("IG_TOKEN"), E.get("IG_USER_ID")
    now = time.time()
    if not IG_AUTO:  # 꺼짐: 남은 컨테이너(igc_ 발행 대기·igk_ 넘기기 조각)는 발행 없이 지움(인스타 API 안 부름)
        drop = [k for k in seen if k.startswith(("igc_", "igk_"))]
        for k in drop:
            seen.pop(k)
        if drop:
            print("ig 꺼짐 -> 남은 컨테이너 발행 없이 지움", len(drop))
        return
    if not (tok and uid):
        return
    day = time.strftime("igpub_%Y%m%d", time.gmtime(now + 9 * 3600))
    card = lambda v: v.get("card") if isinstance(v, dict) else None  # 릴스·다시 올리기는 시각(float)만
    for k in [k for k in seen if k.startswith("igc_")]:
        if k not in seen:  # 앞 컨테이너 진짜 실패 2번째(ig_fail)가 남은 컨테이너를 지움
            continue
        v = seen[k]
        failed = isinstance(v, dict) and v.get("fail")  # 지난 실행 발행 오류 + 그때 안 올라감 -> 이번 상태로만 판정(다시 발행 X)
        kind = isinstance(v, dict) and v.get("kind")
        if (card(v) or kind in IG_KIND) and now - v["t"] < IG_SITE_LAG:  # 사이트 맨 위에 먼저(카드 만든 실행 배포) -> 다음 실행에 발행 — 상태도 그때(그래프 API 호출 줄이기) · 큐레이션도 만든·묶은 실행 다음(그 실행 seen이 저장 안 되면 두 번 X — 10/25 리뷰)
            continue
        n, free = seen.get(day, {}).get("n", 0), kind == "story" or IG_H and kind == "reel"  # H: 스토리·릴스(피드에 X) = 하루 피드 상한·2시간 간격 X(쉼·공식 한도는 같게)
        if not failed and (seen.get("ig_hold", 0) > now or not free and (n >= ig_day_max(seen) or now - seen.get("iglast", {}).get("t", 0) < IG_GAP)):
            print("ig publish 미룸", k, f"오늘 {n}개" + (" · 진짜 실패로 쉼" if seen.get("ig_hold", 0) > now else " · 직전 게시 2시간 안" if now - seen.get("iglast", {}).get("t", 0) < IG_GAP else ""))
            continue
        st = json.loads(http(f"{IG}/{k[4:]}?fields=status_code", headers={"Authorization": "Bearer " + tok}))["status_code"]
        if st == "IN_PROGRESS" and not failed:
            continue
        if st != "PUBLISHED" and (failed or st != "FINISHED"):  # 처리 실패(ERROR·EXPIRED) · 발행 오류 뒤에도 안 올라감 = 진짜 실패, 그 회차만 건너뜀
            seen.pop(k)
            ig_fail(seen, now, (card(v) or IG_KIND.get(kind, "릴스")) + (f" 발행 {failed}" if failed else f" 처리 {st}"))
            continue
        pid = None
        if st != "PUBLISHED" and not failed and (q := ig_quota(tok, uid)) and q[0] >= q[1] * IG_QUOTA_SHARE:  # 공식 24시간 한도의 절반을 넘으면 미룸(실제 응답)
            print("ig publish 미룸", k, f"공식 한도 {q[0]}/{q[1]} — 절반 넘음")
            continue
        if st != "PUBLISHED":
            try:
                pid = json.loads(http(f"{IG}/{uid}/media_publish", {"creation_id": k[4:]}, {"Authorization": "Bearer " + tok}, "POST")).get("id")
            except Exception as e:
                pid = ig_landed(tok, uid, k[4:], (v.get("cap80") or "") if isinstance(v, dict) else "", since=now)  # 캡션 알면 게시물 id까지(구매 댓글·정답 예약)
                if not pid:  # 오류 응답이어도 실제로 올라감(10/22 #1804 code 4·2207051 오탐)이면 성공 · 아니면 다음 실행에 상태만 다시 봄
                    seen[k] = {**(v if isinstance(v, dict) else {"t": v}), "fail": ig_err(e)}
                    if not free:  # 발행 시도도 2시간 간격에 셈(차단 오류 바로 뒤 다른 컨테이너 X — 10/25 리뷰)
                        seen["iglast"] = {"t": now}
                    print("ig publish 오류 — 다음 실행에 게시 여부만 확인(다시 발행 X)", k, clip(repr(e), 80))
                    continue
                print("ig publish 오류 응답이지만 게시됨", k, clip(repr(e), 80))
        elif failed:
            print("ig publish 오류 응답 뒤 게시 확인됨", k)
            pid = v.get("cap80") and ig_landed(tok, uid, k[4:], v["cap80"], since=v["t"])  # 피드 글 = 게시물 id 찾기(구매 댓글·정답 예약 — 'published'면 그건 X)
        RUN["ok"].add("ig")
        print("ig publish", card(v) or IG_KIND.get(kind, "릴스"), pid or "(게시됨 확인)")  # 게시 id(점검 표 — 오류 응답 뒤 확인·이미 PUBLISHED면 id 없음)
        seen.pop(k)
        if not free:
            seen[day], seen["iglast"] = {"t": now, "n": n + 1}, {"t": now}  # iglast = 게시 사이 2시간(IG_GAP)
        if card(v):
            ig_live(card(v), now)
        if isinstance(v, dict) and v.get("stem") and pid:
            card_names_put(v["stem"], pid=pid)  # 게시물 id -> 테마(metrics 테마별 저장)
        if isinstance(v, dict) and v.get("cmt") and pid and pid != "published":
            ig_comment(seen, tok, pid, v["cmt"])  # I: 게시 직후 구매 링크 안내 댓글
        if isinstance(v, dict) and v.get("guess") and pid and pid != "published":
            seen["igans_" + str(pid)] = {"t": now, "stem": v.get("stem"), **v["guess"]}  # M-2: 3시간 뒤 정답 댓글(ig_guess)
        if isinstance(v, dict) and v.get("ask") and pid and pid != "published":
            seen["igask"] = {"t": now, "pid": pid, "names": v["ask"], "day": time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600))}  # M-4: 재미 질문 카드가 댓글 집계
        label = card(v) or ""
        tg("sendMessage", chat_id=ADMIN, text="📸 인스타 자동 게시 완료" + (f" — {SLOT_NAMES[label[11:]]} 카드" if label[11:] in SLOT_NAMES else " — 오늘 카드" if label else " — 오늘 릴스" if kind == "reel" else f" — {IG_KIND[kind]}" if kind in IG_KIND else "") + " (instagram.com/hotdealpick.kr)")


def ig_comment(seen, tok, mid, text):
    """I(10/26 진우 '구매링크는 인스타 댓글로'): 게시 직후 계정 본인 댓글 1개(POST /{media-id}/comments) — 권한 없음·실패 = 건너뜀 + 로그, 관리봇 알림은 3일에 1번."""
    try:
        http(f"{IG}/{mid}/comments", {"message": text}, {"Authorization": "Bearer " + tok}, "POST")
        print("ig 댓글", mid)
    except Exception as e:
        print("ig 댓글 실패", ig_err(e))
        if "igcmt_err" not in seen:
            seen["igcmt_err"] = {"t": time.time()}
            tg("sendMessage", chat_id=ADMIN, text=f"⚠️ 인스타 구매 링크 댓글을 못 달았어요({ig_err(e)}) — 토큰 권한 instagram_business_manage_comments 확인 · 그동안 댓글 없이 게시(이 알림은 3일에 1번)")

def ig_quota(tok, uid):
    """공식 게시 한도(GET content_publishing_limit — 최근 24시간 게시 수·한도) -> (쓴 수, 한도), 못 읽으면 None(하루 상한 ig_day_max만) · 실행마다 1번만 부름."""
    if "igq" not in RUN:
        try:
            x = (json.loads(http(f"{IG}/{uid}/content_publishing_limit?fields=quota_usage,config", headers={"Authorization": "Bearer " + tok})).get("data") or [{}])[0]
            RUN["igq"] = (int(x["quota_usage"]), int(x["config"]["quota_total"]))
        except Exception as e:
            print("ig 게시 한도 못 읽음", err_brief(e))
            RUN["igq"] = None
    return RUN["igq"]


def ig_err(e):
    """인스타 오류 한 줄(진짜 실패 기록·README 점검용): 메시지 + code·subcode(예 'Application request limit reached (4/2207051)')."""
    c = re.findall(r'"(?:code|error_subcode)":\s*(\d+)', getattr(e, "body", "") or "")
    tail = f" ({'/'.join(c)})" if c else ""
    return clip(err_brief(e), 80 - len(tail)) + tail  # 코드는 안 잘리게(IG_BLOCK이 368·190을 봄 — 10/25 리뷰)


def ig_hours(seen):
    """오늘 인스타 칸(ig_cards): 단계(seen igstage s — ig_stage가 실행마다 ig_stage.json에 맞춤) 시간대 칸 + 22시 하루 카드. 기록이 없으면 단계 0(조심 쪽)."""
    return (*IG_STAGES[seen.get("igstage", {}).get("s", 0)], IG_DAY_HOUR)


def ig_day_max(seen):
    """하루 발행 상한 = 그 단계 횟수 + 1(10/23 진우 — 다시 올리기·늦게 올라간 것 여유)."""
    return IG_FEED_MAX if IG_H else len(ig_hours(seen)) + 1  # H(10/26): 피드 = 테마·개별 칸 하루 IG_FEED_MAX(시간대 카드 = 스토리 — 상한 밖)


def ig_room(seen, now):
    """오늘(KST) 인스타 발행 여유 = 하루 상한(ig_day_max) - (올린 수 + 기다리는 컨테이너·조각 + 아직 안 한 카드 칸) — 큐레이션이 딜 카드 칸을 밀어내지 않게(10/25 리뷰: 22시 카드가 자정 뒤로)."""
    kst = time.gmtime(now + 9 * 3600)
    today, led = time.strftime("%Y-%m-%d", kst), load(IG_LIVE, {})
    left = sum(1 for h in ig_hours(seen) if (stem := today if h == IG_DAY_HOUR else f"{today}_{h:02d}") not in led and "igs_" + stem not in seen and kst.tm_hour < h + IG_LATE) if not IG_H \
        else sum(1 for hh, (h, m) in IG_FEED.items() if not (seen.get(f"igf_{today}_{hh}") or {}).get("done") and kst.tm_hour * 60 + kst.tm_min < h * 60 + m + IG_LATE * 60)  # H = 남은 피드 칸
    if left and kst.tm_hour * 3600 + kst.tm_min * 60 > 86400 - IG_GAP - 3600:  # 21시 뒤 = 칸 밖 글 X(2시간 간격 때문에 남은 칸이 자정 뒤로 — 10/25 리뷰)
        return 0
    return ig_day_max(seen) - seen.get(time.strftime("igpub_%Y%m%d", kst), {}).get("n", 0) - sum(1 for k in seen if k.startswith(("igc_", "igk_"))) - left


def ig_stage_get(today):
    """인스타 단계 기록 {s 단계, since 그 단계(또는 내린 날)부터, fd 진짜 실패 날짜들, h {날짜: 단계}, j 마지막 판정 날, log 판정 줄, b {단계: 마지막 글당 조회 평균}}: ig_stage.json > 처음(오늘 단계 0)."""
    return {"s": 0, "since": today, "fd": [], "h": {today: 0}, "j": "", "log": [], "b": {}, **load(IG_STAGE_FILE, {})}


def ig_stage_put(seen, r):
    json.dump(r, open(IG_STAGE_FILE, "w"), ensure_ascii=False, indent=1)
    seen["igstage"] = {"t": time.time(), "s": r["s"]}


def ig_views(days):
    """metrics.json 인스타 글당 조회(views — 다음 날 아침에 모은 값) 평균, 그날들에 숫자가 없으면 None."""
    m = load(METRICS, {})
    v = [x["views"] for d in days for x in m.get(d, {}).get("rows", []) if x["ch"] == "ig" and x.get("views") is not None]
    return round(sum(v) / len(v), 1) if v else None


def ig_stage(seen):
    """인스타 단계(10/23 진우 '단계적 늘리기' — 하루 4번 11·15·19 -> 5번 +13시 -> 6번 +17시, 22시 하루 카드는 늘 따로): 실행마다 seen igstage를 ig_stage.json에 맞추고,
    매일 0시(KST) 뒤 첫 실행에 1번 판정 — 그 단계로 IG_STAGE_DAYS일 지났고 앞 3일 진짜 실패 0이면 한 단계 올림(5 -> 6번은 + 그 단계 글당 조회 평균 >= 앞 단계 평균 —
    metrics.json 인스타 views는 다음 날 아침에 모아서 어제 글은 아직 없음, 숫자가 없으면 안 올림). 내림 = 진짜 실패 난 날 ig_fail이 바로(그날부터 다시 셈).
    판정을 건너뛴 날(인스타 꺼짐·실행 없음)이 있으면 3일을 그날부터 다시 셈(안 올린 날은 실패 0이어도 셈 X). 앞 단계 평균은 metrics(14일)에 없으면 그때 적어 둔 b.
    판정 줄 -> 로그·기록 log(README 점검 표 — 단계·실패 수·글당 조회), 올리면 관리봇(내림은 ig_fail 로그 줄 — 1번째 실패 알림 X 그대로, 2번째 = 24시간 쉼 알림)."""
    if not IG_AUTO or IG_H:  # H(10/26): 피드 = 테마·개별 칸 고정(IG_FEED) — 단계 X
        return
    now = time.time()
    today = time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600))
    r = ig_stage_get(today)
    if r["j"] != today:
        ago = lambda k: (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=k)).strftime("%Y-%m-%d")
        if r["j"] and r["j"] < ago(1):  # 판정을 건너뛴 날 = 인스타 꺼짐·실행 없음 -> 안 올린 날을 '실패 0'으로 세지 않게 다시 셈
            r["since"] = today
        s, fails = r["s"], sum(ago(IG_STAGE_DAYS) <= d < today for d in r["fd"])
        avg = ig_views([d for d, k in r["h"].items() if k == s and d >= r["since"]])
        prev = ig_views([d for d, k in r["h"].items() if k == s - 1]) if s else None
        prev = r["b"].get(str(s - 1)) if s and prev is None else prev  # 앞 단계 날이 14일(metrics·h)보다 오래되면 그때 적어 둔 평균
        if avg is not None:
            r["b"] = {**r["b"], str(s): avg}
        up = s + 1 < len(IG_STAGES) and r["since"] <= ago(IG_STAGE_DAYS) and not fails and (s == 0 or None not in (avg, prev) and avg >= prev)
        r.update(s=s + up, since=today if up else r["since"], j=today, h={**{d: k for d, k in r["h"].items() if d >= ago(14)}, today: s + up})
        line = f"{today} 단계 {s + up}(하루 {len(IG_STAGES[s + up]) + 1}번{' — 올림' if up else ''}) · 앞 3일 진짜 실패 {fails} · 글당 조회 {avg} (앞 단계 {prev})"
        r["log"] = (r["log"] + [line])[-30:]
        print("ig stage", line)
        if up:
            tg("sendMessage", chat_id=ADMIN, text=f"📸 인스타 단계 올림 — 오늘부터 하루 {len(IG_STAGES[s + up]) + 1}번(" + "·".join(map(str, ig_hours({"igstage": {"s": s + up}}))) + f"시)\n{line}")
        ig_stage_put(seen, r)
    seen["igstage"] = {"t": now, "s": r["s"]}


def ig_fail(seen, now, why):
    """인스타 진짜 실패(게시 안 됨 — 컨테이너·묶음 만들기 실패, 처리 ERROR·EXPIRED, 발행 오류 뒤 ig_landed·다음 실행 상태로도 안 올라감):
    그 회차만 건너뜀(다시 시도 X, 10/23 진우) · 그날 첫 실패면 단계 한 단계 내림(ig_stage — 그날부터 다시 셈) · 오늘 IG_FAIL_MAX번째면 24시간 쉼(남은 컨테이너는 발행 없이 지움) + 관리봇 알림.
    seen igfail f = 오늘 진짜 실패."""
    today = time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600))
    st = ig_stage_get(today)
    if today not in st["fd"]:
        st.update(s=max(0, st["s"] - 1), since=today, h={**st["h"], today: max(0, st["s"] - 1)})
        st["log"] = (st["log"] + [f"{today} 진짜 실패 -> 단계 {st['s']}(하루 {len(IG_STAGES[st['s']]) + 1}번) · 그날부터 다시 셈"])[-30:]
    st["fd"] = (st["fd"] + [today])[-30:]
    ig_stage_put(seen, st)
    r = seen.setdefault("igfail", {"f": []})
    r.update(t=now, f=[x for x in r["f"] if x[:10] == today] + [f"{today} {clip(why, 80)}"])
    print("ig 진짜 실패", why, f"(오늘 {len(r['f'])}번)")
    if re.search(IG_BLOCK, why, re.I) and seen.get("ig_hold", 0) < (end := kst_ts(time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600 + 86400)) + " 00:00")):  # 행동 제한·스팸·권한 = 오늘 인스타 전부 멈춤(내일 0시까지) + 알림(단계는 위에서 1칸 내림)
        day2 = len(r["f"]) >= IG_FAIL_MAX  # 오늘 2번째 진짜 실패면 24시간 쉼이 더 김(짧아지지 않게 — 10/25 리뷰)
        seen["ig_hold"] = max(end, now + 86400 if day2 else 0)
        for k in [k for k in seen if k.startswith(("igc_", "igk_"))]:
            seen.pop(k)
        tg("sendMessage", chat_id=ADMIN, text=f"⛔ 인스타 행동 제한·스팸·권한 오류 — " + ("오늘 진짜 실패 2번째라 24시간 쉼" if day2 else "오늘 인스타 전부 멈춤(내일 0시부터 다시") + f" · 단계 1칸 내림 · 남은 게시 대기 지움)\n{clip(why, 200)}")
    elif len(r["f"]) >= IG_FAIL_MAX:
        seen["ig_hold"] = now + 86400
        for k in [k for k in seen if k.startswith(("igc_", "igk_"))]:
            seen.pop(k)
        tg("sendMessage", chat_id=ADMIN, text=f"⚠️ 인스타 진짜 실패(게시 안 됨) 오늘 {len(r['f'])}번 — 24시간 쉼, 다시 시도 X\n" + "\n".join(x[11:] for x in r["f"]))


OY_CLAIM = ("📅 올리브영 쇼핑 큐레이터 수익금 지급 신청 기간이에요(21일~말일)\n앱 → 큐레이터 대시보드 → 지급 신청. 확정 수익 첫 지급 5천 원·이후 1만 원 이상일 때.\n"
            "첫 지급이면 최종 승인 신청도 같이(등록 채널 5개 링크·캡처 + 게시물 예시). 신청 안 하면 6개월 뒤 소멸.")


def oy_claim(seen):
    """매달 21일~말일 10시 이후 1번: 올리브영 큐레이터 수익금 지급 신청 알림(직접 신청해야 지급 — FAQ, 10/10)."""
    kst = time.gmtime(time.time() + 9 * 3600)
    key = time.strftime("oyclaim_%Y%m", kst)
    if kst.tm_mday >= 21 and kst.tm_hour >= 10 and key not in seen and tg("sendMessage", chat_id=ADMIN, text=OY_CLAIM):
        seen[key] = time.time()


def blog_text(todays, kst):
    """네이버 블로그에 그대로 복붙할 제목+본문 (일반 텍스트, 링크 그대로 노출, 대가성 문구 포함)."""
    toss_in = toss_list(todays)
    title = f"{kst.tm_mon}월 {kst.tm_mday}일 핫딜 모음 | {list_name(todays[0], toss_in)}" + (f" 외 {len(todays) - 1}건" if len(todays) > 1 else "")
    items = []
    for n, p in enumerate(todays, 1):
        t = list_name(p, toss_in)
        why = next((l for l in comment_of(p["text"]).split("\n") if l and not l.startswith("🤔")), "")  # 약한 딜 표시 줄 말고 코멘트(10/11 점검: 5점 진우 딜이 '약한 제품'만 남던 것)
        why = strip_cmp("👉 " + why)[0][2:] if toss_in and why else why  # 토스 딜이 든 글 = 다른 몰 이름 조각 뺌(TOP 👉 줄과 같게)
        items.append(f"{n}. {t}\n{why}\n👉 {p['url'] or SITE}")
    notes = aff_notes(p["url"] for p in todays)  # F(10/24): 링크마다 그 프로그램 문구 그대로 맨 앞(쿠팡·토스도 — 예전 맨 끝 합친 한 문장 X)
    return (f"📝 블로그용 (제목·본문 그대로 복붙)\n\n제목: {title}\n\n" + (notes + "\n\n" if notes else "") + "\n\n".join(items) + (f"\n\n{toss_when()}" if toss_in else "")
            + f"\n\n더 많은 핫딜 👉 {SITE}?ref=blog\n실시간 알림 👉 https://t.me/hotdeal_pick")


THREADS = "https://graph.threads.com/v1.0"  # 공식 문서 기준 도메인


def ig_tags(ps, k=0):
    """인스타 해시태그 IG_TAG_MAX개: 기본 + 그날 딜에 있는 카테고리(사이트 '🧻 생필품'·'💄 화장품'과 같은 낱말) + 채움(k = 칸 번호만큼 돌려서 칸마다 조금씩 다르게)."""
    titles = " ".join(title_of(p["text"]) for p in ps)
    cat = [IG_CAT_TAGS[k] for k, _, rx in CATS if k in IG_CAT_TAGS and re.search(rx, titles)]
    k %= len(IG_FILL_TAGS)
    return " ".join(list(dict.fromkeys(IG_TAGS + tuple(cat) + IG_FILL_TAGS[k:] + IG_FILL_TAGS[:k]))[:IG_TAG_MAX])


def ig_used(day):
    """오늘 시간대 카드(docs/cards/날짜_시.json)에 이미 든 posts 번호."""
    d = "docs/cards"
    return {i for f in (os.listdir(d) if os.path.isdir(d) else []) if re.fullmatch(re.escape(day) + r"_\d\d\.json", f) for i in json.load(open(f"{d}/{f}"))}


def slot_deals(posts, day, h, hours=IG_STAGES[0]):
    """시간대 카드 딜 = 오늘 앞 칸 시각(첫 칸은 0시) ~ h시에 올린 딜(10/23 진우 '11시 = 0~11시, 15시 = 11~15시, 19시 = 15~19시') 중 오늘 다른 칸 카드에 안 든 것,
    하루 카드와 같은 순서(점수·제휴 먼저 — 19시 칸은 진우 쿠팡 🔥·👍 먼저) 앞 CARD_N개. hours = 오늘 칸(ig_hours)."""
    since, used = f"{day} {max([0] + [x for x in hours if x < h]):02d}:00", ig_used(day)
    ds = [x for x in day_deals(posts, day) if since <= x[1]["t"] < f"{day} {h:02d}:00" and x[0] not in used]
    if h == IG_OWN_HOUR:
        ds.sort(key=lambda x: not (x[1].get("own") and mall_of(x[1].get("url"), title_of(x[1]["text"])) == "coupang"
                                   and any(m[2] in ("🔥", "👍") for m in map(MALL_HEAD.fullmatch, x[1]["text"].split("\n")) if m)))
    return ds[:CARD_N]


def ig_notes(ps):
    """인스타·Threads 카드 캡션 맨 앞 대가성 문구(캡션은 올린 뒤 못 고침): 딜마다 지금 제휴 프로그램 + 올린 뒤 제휴 링크로 바뀔 몰
    (쿠팡·네이버·올리브영 = 진우 링크, 토스 = toss_relink)도 미리. 네이버('글 맨 앞')·올리브영('제목·서두') 먼저, 하나도 없으면 일반 안내 1줄."""
    later = {"💰 쿠팡": DISCLOSURE, "💰 토스": TOSS_NOTE, "💰 네이버": NAVER_NOTE, "💰 올리브영": OY_NOTE}
    ns = {n for p in ps for n in (aff_note(p.get("url") or ""), *(v for k, v in later.items() if store_info(title_of(p["text"]), p.get("url")).startswith(k))) if n}
    return "\n".join(n for n in (NAVER_NOTE, OY_NOTE, DISCLOSURE, TOSS_NOTE, AFF_NOTE) if n in ns) or "일부 링크는 제휴 링크로 수수료를 받을 수 있어요."


def card_caption(stem):
    """카드의 (목록 줄 CARD_N개, 인스타 캡션). 목록 번호 = 카드·사이트 맨 위 번호. 가격은 카드 이미지에.
    대가성 문구는 늘 맨 앞(ig_notes), 사이트 맨 위 어느 카드 칸인지(칸 이름 그대로 — 24시간 동안 접힌 칸으로 남음)."""
    ps = [p for _, p in card_order(load(POSTS, []), stem)[:CARD_N]]
    toss_in = toss_list(ps)
    rows = [f"{n}. {clip(re.sub(PRICE_TAIL, '', list_name(p, toss_in)).strip(), 34)}" for n, p in enumerate(ps, 1)]
    slot = SLOT_NAMES.get(stem[11:]) if len(stem) > 10 else None
    return rows, (ig_notes(ps) + "\n\n" + f"{int(stem[5:7])}월 {int(stem[8:10])}일 " + (f"{slot} 핫딜" if slot else "오늘의 핫딜 모음") + "\n\n" + "\n".join(rows)
                  + f"\n\n🛒 프로필 링크 → '{card_name(stem)}' 번호 누르면 바로 구매\n\n" + ig_tags(ps, int(stem[11:] or IG_DAY_HOUR) // 2 + int(stem[8:10])))[:2200]  # 칸·날마다 조금씩 다르게(10/25 진우 '정지 안 되게')


def fill_reel(ps):
    """릴스·딜 카드 재료(e·hook·pts·unit·warn)가 없는 딜(✅로 올린 글·예전 글)만 Claude로 채움(글 dict에 바로). 실패하면 그대로(제목·코멘트로 그림)."""
    need = [p for p in ps if not (p.get("hook") and p.get("pts"))]
    if not need:
        return
    try:
        for f in ai_pick(REEL_PROMPT, [f"{title_of(p['text'])} | {comment_of(p['text'])}" for p in need]):
            need[f["i"]].update({k: f[k] for k in ("e", "hook", "pts", "unit", "warn", "who", "use") if f.get(k)})
    except Exception as e:
        print("reel fill", repr(e))


def card_item(p):
    """딜 카드·릴스 한 장 재료 -> (재료, 올리브영인지). 올리브영 딜은 후기·추천·반응·효능 말 든 이유·첫 화면 문구와 코멘트를 뺌(큐레이터 정책 — 그림·영상은 못 고침)."""
    oy = aff_note(p.get("url") or "") == OY_NOTE or is_oy(title_of(p["text"]))
    ok = lambda x: not (oy and re.search(OY_DENY, x or ""))
    return {"title": title_of(p["text"]), "comment": "" if oy else comment_of(p["text"]), "e": p.get("e"), "hook": p.get("hook") if ok(p.get("hook")) else "",
            "unit": p.get("unit"), "warn": p.get("warn"), "pts": [x for x in p.get("pts") or [] if ok(x)]}, oy


def deal_slides(stem, ps):
    """넘기기 딜 카드: 카드 번호 순서대로 딜마다 1장 -> docs/cards/{stem}/01.jpg…(표지 다음 장들, 워크플로가 커밋 -> 사이트 공개 -> ig_cards가 올림).
    올리브영 딜은 이유 제목 '체크 포인트'(큐레이터 정책: 권유 문구 X). 한 장이라도 실패하면 폴더째 지움 -> 한 장짜리 카드로."""
    import cards
    fill_reel(ps)
    d = f"docs/cards/{stem}"
    try:
        os.makedirs(d, exist_ok=True)
        for n, p in enumerate(ps, 1):
            it, oy = card_item(p)
            cards.deal_card(it, n, len(ps), f"{d}/{n:02d}.jpg", why="체크 포인트" if oy else "살 만한 이유")
    except Exception as e:
        print("slides", stem, repr(e))
        shutil.rmtree(d, ignore_errors=True)


def ig_carousel(seen, tok, uid, now):
    """넘기기 묶기: 조각(표지·딜 카드) 컨테이너가 다 처리되면(FINISHED) 묶음(CAROUSEL, 캡션) 컨테이너 -> igc_(ig_publish가 발행).
    처리 중이면 다음 실행에, 조각 실패(ERROR·EXPIRED)·KIDS_WAIT 넘게 처리 중이면 그 회차는 버리고 알림(카드 주소). 조각은 igc_에 안 둠(따로 발행되면 안 됨)."""
    h = {"Authorization": "Bearer " + tok}
    for k in [k for k in seen if k.startswith("igk_")]:
        if k not in seen:  # 앞 조각 진짜 실패 2번째(ig_fail)가 남은 조각을 지움
            continue
        v, stem = seen[k], k[4:]
        if now - v["t"] < IG_SITE_LAG:  # 조각 만든 실행엔 상태 안 봄(10/23 진우 '폴링 간격 늘려 호출 수 줄이기') -> 다음 실행에
            continue
        st = json.loads(http(f"{IG}/{v['kids'][-1]}?fields=status_code", headers=h))["status_code"]  # 마지막 조각만(이미지는 몇 초면 끝 — 14분 뒤라 앞 조각도 끝, 안 끝난 조각이 있으면 묶기 오류 = 진짜 실패)
        if st == "IN_PROGRESS" and now - v["t"] <= KIDS_WAIT:
            continue
        seen.pop(k)
        try:
            if st != "FINISHED":
                raise RuntimeError(f"조각 처리 {st}")
            c = json.loads(http(f"{IG}/{uid}/media", {"media_type": "CAROUSEL", "children": ",".join(v["kids"]), "caption": v.get("cap") or ig_caption(seen, stem, IG_HUMAN, photo=IG_HUMAN)}, h, "POST"))  # cap = 큐레이션(curation) · IG_HUMAN 넘기기 = 사진 장 있을 때만
        except Exception as e:
            ig_fail(seen, now, f"{stem} 넘기기 {ig_err(e)}")
            continue
        seen["igc_" + c["id"]] = {"t": now, **({"kind": v["kind"]} if v.get("kind") else {"card": stem}), **{x: v[x] for x in ("cmt", "stem", "guess", "ask") if v.get(x)}, **({"cap80": v["cap"][:80]} if v.get("stem") and v.get("cap") else {})}  # 큐레이션 = 사이트 맨 위 카드 기록 X  # 발행은 다음 실행(묶은 실행 seen이 저장 안 되면 다음 실행이 같은 조각으로 또 묶어 두 번 올라가지 않게 — 10/23 리뷰)
        print("ig carousel", stem, len(v["kids"]), "장")


def prune_slides(now):
    """딜 카드 폴더(docs/cards/날짜[_시]/)·릴스 영상(docs/reels/날짜.mp4)은 SLIDE_KEEP일 지나면 지움(인스타가 이미 가져감, 사이트는 표지만 씀 — 저장소 크기).
    git add -A가 지운 것도 커밋."""
    cut = time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600 - SLIDE_KEEP * 86400))
    for base in ("docs/cards", "docs/cards/igv", IGT_DIR):  # igv = 인스타 새 디자인 한 벌(IG_HUMAN) · igt = 테마 넘기기(H)
        for f in os.listdir(base) if os.path.isdir(base) else []:
            if STEM.fullmatch(f) and f[:10] < cut and os.path.isdir(f"{base}/{f}"):
                shutil.rmtree(f"{base}/{f}")
    for f in os.listdir(STORY_DIR) if os.path.isdir(STORY_DIR) else []:  # H-2 스토리
        if f[:10] < cut:
            os.remove(f"{STORY_DIR}/{f}")
    for f in os.listdir("docs/reels") if os.path.isdir("docs/reels") else []:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.mp4", f) and f[:10] < cut:
            os.remove(f"docs/reels/{f}")


def ig_reel(seen):
    """릴스 하루 1개 자동(10/11 진우 '인스타 업그레이드 3번'): REEL_HOUR시~자정, 모아보기(digest)가 docs/reels/에 공개한 오늘 영상이 사이트에 뜨면(HEAD)
    REELS 컨테이너(video_url·캡션·피드에도·표지 1.5초) -> ig_publish가 처리 끝나면 발행(영상은 보통 1~10분). 만들기 실패는 IG_TRIES번까지 다음 실행에 다시."""
    tok, uid = E.get("IG_TOKEN"), E.get("IG_USER_ID")
    now = time.time()
    kst = time.gmtime(now + 9 * 3600)
    today = time.strftime("%Y-%m-%d", kst)
    r, tried = seen.get("reel_" + today), seen.get("igr_" + today)
    if not (IG_AUTO and tok and uid and r) or kst.tm_hour < REEL_HOUR or seen.get("ig_hold", 0) > now or (tried and tried.get("fail", IG_TRIES) >= IG_TRIES):
        return
    url = f"{SITE}reels/{today}.mp4"
    try:
        http(url, method="HEAD")  # 아직 배포 전이면 다음 실행에
    except Exception:
        return
    fail = (tried or {}).get("fail", 0)
    seen["igr_" + today] = {"t": now}
    try:
        c = json.loads(http(f"{IG}/{uid}/media", {"media_type": "REELS", "video_url": url, "caption": r["cap"], "share_to_feed": r.get("feed", True), "thumb_offset": REEL_THUMB_MS},
                            {"Authorization": "Bearer " + tok}, "POST"))
    except Exception as e:
        if IG_H:  # 공개 릴스(J-1) = F 그대로: 실패 = 다시 X · ig_fail(행동 제한이면 그날 멈춤)
            seen["igr_" + today] = {"t": now, "fail": IG_TRIES}
            ig_fail(seen, now, f"릴스 컨테이너 {ig_err(e)}")
            return
        seen["igr_" + today] = {"t": now, "fail": fail + 1}
        raise RuntimeError(f"인스타 릴스 컨테이너 실패({fail + 1}/{IG_TRIES}) — " + ("다음 실행에 다시" if fail + 1 < IG_TRIES else "봇 채팅에 온 영상을 직접 올려줘") + f": {e!r} {getattr(e, 'body', '') or ''}")
    seen["igc_" + c["id"]] = {"t": now, "kind": "reel"}
    print("ig reel 컨테이너", today)


def ig_cards(seen):
    """인스타 하루 4번부터(10/23 진우 '너무 자주 말고' — 단계적 늘리기 ig_stage): 오늘 칸(ig_hours, 11·15·19시 …) 시간대 카드 + 22시 하루 카드(21시 모아보기 때 만든 것).
    시간대 카드: 그 시각 첫 실행에 카드(JPEG)·번호 순서를 docs/cards/날짜_시에 만들고(워크플로가 커밋 -> 사이트 공개) 다음 실행에 사이트에 뜨면 인스타 컨테이너
    -> 사이트 맨 위 카드 기록(ig_live, 사이트 먼저) -> 다음 실행에 ig_publish가 발행. 그 시각 IG_LATE시간 안에만, 딜 IG_MIN개 미만이면 건너뜀(억지로 안 채움), 회차마다 1번
    (기록에 있으면 seen을 잃어도 다시 안 올림). 컨테이너 만들기 실패 = 진짜 실패(ig_fail — 그 회차 건너뜀, 다시 시도 X · 10/23 진우).
    넘기기(IG_CAROUSEL, 10/11 진우 '인스타 업그레이드 2번'): 카드 만들 때 딜 카드(deal_slides)도 -> 올릴 때 표지·딜 카드 조각 컨테이너 -> ig_carousel이 묶음."""
    tok, uid = E.get("IG_TOKEN"), E.get("IG_USER_ID")
    now = time.time()
    if tok and uid:
        prune_slides(now)  # 지난 넘기기 카드 정리는 인스타를 꺼도(모아보기가 21시 딜 카드를 계속 만듦)
    if not (IG_AUTO and tok and uid) or seen.get("ig_hold", 0) > now:
        return
    ig_carousel(seen, tok, uid, now)  # 지난 실행에 만든 조각
    kst = time.gmtime(now + 9 * 3600)
    today, led = time.strftime("%Y-%m-%d", kst), load(IG_LIVE, {})
    built = {int(f[11:13]) for f in (os.listdir("docs/cards") if os.path.isdir("docs/cards") else []) if re.fullmatch(re.escape(today) + r"_\d\d\.json", f)}
    hours = tuple(IG_STORY) if IG_H else tuple(sorted(set(ig_hours(seen)) | built))  # 이미 만든 칸 카드는 낮에 단계가 내려가도 마저 올림(그 딜이 다른 칸에서 빠지니까) · H = 스토리 칸(M-1)
    mins = kst.tm_hour * 60 + kst.tm_min
    for h in hours:
        stem = today if h == IG_DAY_HOUR else f"{today}_{h:02d}"
        tried = seen.get("igs_" + stem)
        if not h <= kst.tm_hour < h + IG_LATE or (today == IG_START[:10] and h < int(IG_START[11:])) or stem in led or (tried and tried.get("fail", IG_TRIES) >= IG_TRIES):  # 끝난 회차(올림·건너뜀)는 fail 없음
            continue
        if IG_H and not 0 <= mins - h * 60 - IG_STORY[h] < IG_LATE * 60:  # 스토리 시각(12:30 등) 전·2시간 뒤 = X
            continue
        jpg = f"docs/cards/{stem}.jpg"
        if IG_H and h == IG_DAY_HOUR and os.path.exists(dc := f"{DPOST_DIR}/{today}_0.jpg"):  # 22시 스토리 = 📉 가격 내려간 상품 표지(M-1)
            ig_story_card(seen, tok, uid, stem, dc, now, "핫딜픽 · 오늘 가격 내려간 상품", "프로필 링크 → 가격 내려간 상품")
            return
        if h != IG_DAY_HOUR and not os.path.exists(jpg):  # 시간대 카드 만들기(이번 실행) -> 다음 실행에 올림
            posts = load(POSTS, [])
            order = slot_deals(posts, today, h, hours)
            if len(order) < IG_MIN:
                seen["igs_" + stem] = {"t": now, "skip": len(order)}
                print("ig card", stem, f"딜 {len(order)}개 -> 건너뜀")
                continue
            import cards
            os.makedirs("docs/cards", exist_ok=True)
            json.dump([i for i, _ in order], open(f"docs/cards/{stem}.json", "w"))  # 카드 번호 순서 고정(캡션·사이트가 같이 씀)
            ct = toss_list([p for _, p in order[:CARD_N]])
            cards.make([{"title": list_name(p, ct, True), "unit": p.get("unit")} for _, p in order], f"{kst.tm_mon}월 {kst.tm_mday}일", jpg,
                       head=IG_SLOTS[h], label=f"{SLOT_NAMES[f'{h:02d}']} 핫딜", png=False)
            if IG_CAROUSEL and not IG_H:
                deal_slides(stem, [p for _, p in order])
            print("ig card", stem, f"만듦 {len(order)}개")
            return
        if not os.path.exists(jpg):  # 22시: 모아보기(digest, 21시)가 카드를 안 만듦(딜 없음)
            continue
        if h == IG_DAY_HOUR and (n := len(card_order(load(POSTS, []), stem))) < IG_MIN:  # 하루 카드도 딜 3개 밑이면 건너뜀(10/23 진우)
            seen["igs_" + stem] = {"t": now, "skip": n}
            print("ig card", stem, f"딜 {n}개 -> 건너뜀")
            continue
        if IG_H:  # H-2(10/26): 시간대·하루 카드 = 스토리(9:16 — cards.ig_story, 하루 IG_STORY_MAX · 피드 X)
            if any(shop_of(p) == "toss" for _, p in card_order(load(POSTS, []), stem)):  # 인스타 토스 X(10/26 Cowork N — 토스 범위 답 전): 토스 딜 든 카드 = 사이트·텔레그램만
                seen["igs_" + stem] = {"t": now, "skip": "toss"}
                print("ig story", stem, "토스 딜 든 카드 -> 건너뜀")
                continue
            ig_story_card(seen, tok, uid, stem, jpg, now)
            return
        url, d = f"{SITE}cards/{stem}.jpg", f"docs/cards/{stem}"
        if IG_HUMAN:  # 인스타엔 새 디자인 한 벌(A·B 날마다 번갈아, docs/cards/igv/ — 사이트·텔레그램 카드는 그대로) -> 만든 실행 다음에 올림
            iv = f"docs/cards/igv/{stem}"
            if not os.path.exists(f"{iv}/cover.jpg"):
                ig_set(seen, today, [p for _, p in card_order(load(POSTS, []), stem)], iv, h=h)
                continue
            url, d = f"{SITE}cards/igv/{stem}/cover.jpg", iv
        if IG_HUMAN and now < ig_due(seen, "igd_" + stem, kst_ts(f"{today} {h:02d}:00")):  # 회차 시각 + 15~20분 무작위 뒤에 컨테이너(한 벌은 먼저 만들어 둠)
            continue
        slides = [f"{SITE}{d[5:]}/{f}" for f in sorted(os.listdir(d)) if re.fullmatch(r"\d\d\.jpg", f)] if IG_CAROUSEL and os.path.isdir(d) else []  # d = docs/… -> 사이트 주소
        try:
            for u in [url] + slides[-1:]:
                http(u, method="HEAD")  # 아직 배포 전(404)이면 다음 실행에 (표지·딜 카드는 같은 커밋)
        except Exception:
            continue
        seen["igs_" + stem] = {"t": now}  # 먼저 표시(만들기 성공 = 회차 끝)
        auth = {"Authorization": "Bearer " + tok}
        try:
            if slides:  # 넘기기: 조각(캡션 X) -> 다 처리되면 묶음(ig_carousel)
                seen["igk_" + stem] = {"t": now, "kids": [json.loads(http(f"{IG}/{uid}/media", {"image_url": u, "is_carousel_item": True}, auth, "POST"))["id"] for u in [url] + slides]}
            else:
                c = json.loads(http(f"{IG}/{uid}/media", {"image_url": url, "caption": ig_caption(seen, stem, IG_HUMAN)}, auth, "POST"))
        except Exception as e:
            seen["igs_" + stem] = {"t": now, "fail": IG_TRIES}  # 다시 시도 X(10/23 진우) — 그 회차는 건너뜀(만든 조각은 발행 안 하면 안 보임)
            ig_fail(seen, now, f"{stem} 컨테이너 {ig_err(e)}")
            return
        if not slides:
            seen["igc_" + c["id"]] = {"t": now, "card": stem}
        ig_live(stem, now)
        print("ig card", stem, f"넘기기 조각 {len(slides) + 1}장" if slides else "컨테이너")


STORY_DIR = "docs/cards/story"  # H-2 스토리(9:16) — SLIDE_KEEP일 뒤 지움(prune_slides)


def ig_story_card(seen, tok, uid, stem, jpg, now, top=None, bottom="프로필 링크 → 번호 누르면 바로 구매"):
    """H-2 스토리 1장: 카드(사이트·텔레그램과 같은 번호) -> 9:16(docs/cards/story/{stem}.jpg — 이 실행 커밋) -> 다음 실행에 사이트에 뜨면 STORIES 컨테이너(kind story)
    -> ig_publish 발행(피드 상한·2시간 간격 X · 쉼·공식 한도·차단 = 같게) · 사이트 맨 위 카드(ig_live) · 하루 IG_STORY_MAX(넘으면 그 칸 = 사이트만) · 실패 = 다시 X(ig_fail)."""
    today, sp = stem[:10], f"{STORY_DIR}/{stem}.jpg"
    if sum(1 for k, v in seen.items() if k.startswith("igs_" + today) and isinstance(v, dict) and v.get("story")) >= IG_STORY_MAX:
        seen["igs_" + stem] = {"t": now, "skip": "스토리 하루 상한"}
        return
    if not os.path.exists(sp):
        import cards
        cards.ig_story(jpg, sp, top or f"핫딜픽 · {card_name(stem)}", bottom)
        print("ig story 만듦", stem)
        return
    url = SITE + sp[len("docs/"):]
    try:
        http(url, method="HEAD")
    except Exception:
        return
    seen["igs_" + stem] = {"t": now, "story": 1}
    try:
        c = json.loads(http(f"{IG}/{uid}/media", {"image_url": url, "media_type": "STORIES"}, {"Authorization": "Bearer " + tok}, "POST"))
    except Exception as e:
        seen["igs_" + stem] = {"t": now, "story": 1, "fail": IG_TRIES}
        ig_fail(seen, now, f"{stem} 스토리 컨테이너 {ig_err(e)}")
        return
    seen["igc_" + c["id"]] = {"t": now, "kind": "story"}
    ig_live(stem, now)
    print("ig story 컨테이너", stem)

def ig_test(seen):
    """인스타만 1건 테스트(10/22 22시 진우 — 텔레그램·Threads 그대로, IG_AUTO 정기 게시는 그대로 멈춤): ig_test.txt 날짜 = 오늘(밤 3시까지는 어제 날짜도)이면
    1) 그날 하루 카드(21시 카드와 같은 딜·순서)를 변주(ig_variant)로 다시 그려 docs/cards/igt/에(워크플로가 커밋 -> 사이트 공개), 게시 시각 = 지금 + 15~20분 무작위(IG_JITTER)
    2) 그 시각 뒤 실행에서 사이트에 뜨면 컨테이너(캡션 = 대가성 문구 + 사람 멘트 ig_human + 원래 캡션) -> 처리 끝나면(최대 30초 봄) 바로 발행, 아직이면 다음 실행에 발행
    3) 결과(성공·실패 코드)를 관리봇에 1번. 실패(code 4·2207051 등)·오류는 다시 시도 X — 기록(docs/cards/igt/날짜.json + seen)이 있으면 다시 안 함."""
    tok, uid = E.get("IG_TOKEN"), E.get("IG_USER_ID")
    day = open(IG_TEST).read().strip() if os.path.exists(IG_TEST) else ""
    now = time.time()
    kst = time.gmtime(now + 9 * 3600)
    if not day or not (tok and uid) or day not in (time.strftime("%Y-%m-%d", kst), time.strftime("%Y-%m-%d", time.gmtime(now + 6 * 3600))):  # 오늘 · 밤 3시까지는 어제 날짜도
        return
    rec = f"docs/cards/{IG_TEST_DIR}/{day}.json"
    r = {**seen.get("igt_" + day, {}), **load(rec, {})}
    if r.get("st"):
        return
    def save():
        os.makedirs(os.path.dirname(rec), exist_ok=True)
        json.dump(r, open(rec, "w"), ensure_ascii=False)
        seen["igt_" + day] = dict(r)
    def done(ok, msg):
        r.update(st="done" if ok else "fail", end=now, msg=msg)
        save()
        tg("sendMessage", chat_id=ADMIN, text=("📸 인스타 테스트 1건 게시 완료 — " if ok else "⚠️ 인스타 테스트 실패(다시 시도 X) — ") + msg)
        print("ig test", r["st"], msg)
    if not r:
        v = ig_card_copy(seen, day, f"docs/cards/{IG_TEST_DIR}/{day}.png")
        if v is None:
            return done(False, f"{day} 딜 {IG_MIN}개 미만 — 카드 X")
        r.update(t=now, at=ig_due(seen, "igtd_" + day, now), v=v)
        save()
        print("ig test 카드 만듦", v, f"· {round((r['at'] - now) / 60)}분 뒤부터 게시")
        return
    if now < r["at"]:
        print("ig test 대기", f"{round((r['at'] - now) / 60)}분 남음")
        return
    h, url = {"Authorization": "Bearer " + tok}, f"{SITE}cards/{IG_TEST_DIR}/{day}.jpg"
    err = lambda e: f"{e!r} {getattr(e, 'body', '') or ''}"[:300]
    if not r.get("c"):
        try:
            http(url, method="HEAD")  # 아직 배포 전이면 다음 실행에
        except Exception:
            return
        try:
            cap = ig_caption(seen, day, True)
            r["c"] = json.loads(http(f"{IG}/{uid}/media", {"image_url": url, "caption": cap}, h, "POST"))["id"]
            r["ct"], r["cap"] = now, cap[:80]
            save()
        except Exception as e:
            return done(False, "컨테이너 " + err(e))
    try:  # 상태는 실행마다 1번만(폴링 X — 그래프 API 호출 줄이기), 처리 중이면 다음 실행에
        st = json.loads(http(f"{IG}/{r['c']}?fields=status_code", headers=h))["status_code"]
    except Exception as e:
        return done(False, "상태 " + err(e))
    if st == "IN_PROGRESS" and now - r["ct"] < KIDS_WAIT:
        print("ig test 처리 중 -> 다음 실행에 발행")
        return
    if st == "PUBLISHED":  # 지난 실행이 발행 뒤 기록 전에 끊김
        r["id"] = "published"
        return done(True, "이미 게시됨(컨테이너 PUBLISHED) · instagram.com/hotdealpick.kr")
    if st != "FINISHED":
        return done(False, f"컨테이너 처리 {st}")
    try:
        pid = json.loads(http(f"{IG}/{uid}/media_publish", {"creation_id": r["c"]}, h, "POST")).get("id")
    except Exception as e:  # 오류 응답이어도 실제로 올라갔을 수 있음(10/22 #1804) -> 확인 뒤에만 실패, 다시 시도 X
        pid = ig_landed(tok, uid, r["c"], r.get("cap", ""), now)
        if not pid:
            return done(False, "발행 " + err(e))
        r["warn"] = err(e)[:160]
        print("ig test 발행 오류 응답이지만 게시됨", pid)
    r["id"] = pid
    done(True, ("(API는 오류 응답 — 게시 확인됨) " if r.get("warn") else "") + f"변주 {r['v']} · 게시 {time.strftime('%H:%M', kst)}(카드 {time.strftime('%H:%M', time.gmtime(r['t'] + 9 * 3600))} + {round((now - r['t']) / 60)}분) · instagram.com/hotdealpick.kr")


def ig_repost(seen):
    """ig_repost.txt 날짜 = 오늘이면 그날 카드를 지금 코드로 다시 그려 인스타에만 1번 더 게시(10/8 진우 '다시 업로드'). 지난 날짜면 무시.
    1번째 실행: 새 카드 -> docs/cards/re/(새 주소라 사이트 캐시 영향 없음, 워크플로가 커밋) / 다음 실행: 사이트에 뜨면 컨테이너 -> ig_publish가 발행.
    예전 게시물 삭제는 진우(Instagram 로그인 토큰은 삭제 권한 없음)."""
    kst = time.gmtime(time.time() + 9 * 3600)
    day = open(REPOST).read().strip() if os.path.exists(REPOST) else ""
    if not IG_AUTO or day != time.strftime("%Y-%m-%d", kst) or "igre_" + day in seen or not (E.get("IG_TOKEN") and E.get("IG_USER_ID")):
        return
    path = f"docs/cards/re/{day}.png"
    if not os.path.exists(path):
        import cards
        os.makedirs(os.path.dirname(path), exist_ok=True)
        order = card_order(load(POSTS, []), day)
        ct = toss_list([p for _, p in order[:CARD_N]])
        cards.make([{"title": list_name(p, ct, True), "unit": p.get("unit")} for _, p in order], f"{kst.tm_mon}월 {kst.tm_mday}일", path)
        return
    url = f"{SITE}cards/re/{day}.jpg"
    try:
        http(url, method="HEAD")  # 아직 배포 전이면 다음 실행에
    except Exception:
        return
    c = json.loads(http(f"{IG}/{E['IG_USER_ID']}/media", {"image_url": url, "caption": card_caption(day)[1]}, {"Authorization": "Bearer " + E["IG_TOKEN"]}, "POST"))
    seen["igc_" + c["id"]] = seen["igre_" + day] = time.time()


def coupang_remind(seen):
    """13·19시: 오늘 채널에 올라간 쿠팡 딜 중 아직 파트너스 링크가 아닌 글의 관리자 사본을 채팅 맨 아래로 다시 보냄(최대 5개).
    쿠팡 API 승인 전이라 링크는 진우가 만들어야 하는데 사본이 묻혀서 놓침 -> 다시 꺼내 줌. 새 사본에 답장하거나 링크만 보내면 채널 글 교체(기존 흐름 그대로, cp 갱신)."""
    kst = time.gmtime(time.time() + 9 * 3600)
    hrs = [h for h in CP_REMIND_HOURS if h <= kst.tm_hour]
    key = time.strftime("cprem_%Y%m%d_", kst) + (str(hrs[-1]) if hrs else "")
    if not hrs or key in seen:
        return
    seen[key] = time.time()
    posts, today = load(POSTS, []), time.strftime("%Y-%m-%d", kst)
    todo = [p for p in posts if p["t"].startswith(today) and p.get("mid") and p.get("cp") and not aff_note(p.get("url0") or p.get("url") or "")
            and store_info(title_of(p["text"]), p.get("url0") or p.get("url")).startswith("💰 쿠팡")][-5:]  # url0 = 채널 글 주소(사이트만 바꾼 글)
    if not todo:
        return
    tg("sendMessage", chat_id=ADMIN, text=f"🔗 쿠팡 링크 아직 안 만든 오늘 딜 {len(todo)}개 — 사본마다 '파트너스 링크 만들기' → 만든 링크를 그 사본에 답장하면 채널 글·사이트 버튼이 바뀌어")
    for p in todo:
        kb = [[{"text": "📢 채널에 올라간 글", "url": post_url(p["mid"])}],
              [{"text": "🔗 파트너스 링크 만들기", "url": CP_SEARCH + urllib.parse.quote(keyword(title_of(p["text"])))}]]
        cp = (tg("copyMessage", chat_id=ADMIN, from_chat_id=CHANNEL, message_id=p["mid"], reply_markup={"inline_keyboard": kb}) or {}).get("message_id")
        p["cp"] = cp or p["cp"]  # 링크만 보낼 때 '교체됨' 표시를 새 사본에
    json.dump(posts, open(POSTS, "w"), ensure_ascii=False)


def threads(seen):
    """오늘 카드가 사이트에 올라와 있으면 관리자에게 1회 보내고, THREADS_TOKEN 있으면 Threads에도 게시(인스타는 ig_cards — 10/11~ 하루 3번).
    Threads 토큰은 60일마다 만료 -> 실패하면 main()이 관리자에게 알림."""
    kst = time.gmtime(time.time() + 9 * 3600)
    today, key = time.strftime("%Y-%m-%d", kst), time.strftime("threads_%Y%m%d", kst)
    if key in seen or not os.path.exists(f"docs/cards/{today}.png"):
        return
    url = f"{SITE}cards/{today}.png"
    try:
        http(url, method="HEAD")  # 아직 배포 전(404)이면 다음 실행에 다시
    except Exception:
        return
    tok, ig = E.get("THREADS_TOKEN"), E.get("IG_TOKEN") and E.get("IG_USER_ID")
    auto = [n for n, on in (("인스타", ig), ("Threads", tok)) if on]
    tg("sendPhoto", chat_id=ADMIN, photo=url, caption="📸 오늘의 카드" + ("" if ig else " (인스타에 그대로 올리면 돼)") + (f" · {'·'.join(auto)} 자동 게시 중" if auto else ""))
    seen[key] = time.time()  # 사진은 1번만. 인스타·Threads 실패는 관리자에게 알리고 재시도 안 함(스팸 방지)
    rows, cap = card_caption(today)  # 인스타는 ig_cards(10/11~ 하루 3번 — 21시 하루 카드 포함)
    if not tok:
        return
    order = card_order(load(POSTS, []), today)
    rows = [r for r, (_, p) in zip(rows, order) if aff_note(p.get("url") or "")]
    when = f"\n\n{toss_when()}" if toss_list([p for _, p in order[:CARD_N]]) else ""  # 토스 딜이 든 카드 = 게시 시점 줄(카드 이미지의 딜·가격 기준 — 수수료 줄만이 아니라)  # 10/19 밤 진우 'Threads는 수수료 딜만': 줄도 수수료 링크 딜만(카드 번호 그대로 — card_caption과 같은 순서)
    if not rows:
        print("threads skip (수수료 링크 아님) card 묶음 | 항목 0개")
        return
    while True:  # 대가성 문구는 맨 앞 그대로, 길면 번호 줄을 줄임(Threads 500자)
        text = (cap.split("\n\n")[0] + f"\n\n📋 {kst.tm_mon}/{kst.tm_mday} 오늘의 핫딜 모음\n\n" + "\n".join(rows) + when
                + f"\n\n전체 딜·구매 링크 👉 {SITE}?ref=th\n실시간 알림 👉 https://t.me/hotdeal_pick")
        if len(text) <= 480 or len(rows) <= 1:
            break
        rows = rows[:-1]
    th_bundle(seen, "card", text[:480], image=url)


TH_TOPICS = {"food": "장보기", "snack": "장보기", "season": "장보기", "life": "생필품", "laundry": "생필품", "women": "생필품", "beauty": "화장품", "home": "살림템", "kitchen": "살림템", "digital": "가전", "fashion": "패션", "heat": "겨울준비"}  # 10/23 진우 'Threads 주제 태그(그 주제 보는 사람에게도)': 딜 글 = 품목 칸(cat_of) 주제
TH_TOPIC_RUN = 3  # 같은 주제 연달아 3번까지 — 넘으면 '핫딜'(핫딜이면 '특가')


def th_topic(seen, text=None, base=None, cat=None):
    """Threads 글 주제(topic_tag — 글당 1개, 1~50자, '.'·'&' X, 공식 문서 posts·publishing): 딜 글(text — 토스 포함) = 품목 칸 주제(TH_TOPICS, 칸 없음 = 핫딜),
    묶음·리스트·운영 일지·날씨·투표 = '핫딜', base = 정해 둔 주제(#일상). 품목 칸 = 사이트와 같은 cat_of(제목 -> 글 cat = Claude 한 단어), 칸 없음이면 화장품 낱말(th_beauty).
    방금 TH_TOPIC_RUN번 연달아 같은 주제면 '핫딜'(핫딜이면 '특가'). 고른 주제는 seen thtopic l(최근 10개)에 바로 — 글별 주제는 metrics가 Threads 글 목록 topic_tag로 다시 읽음.
    shortcut: 올리기 전에 기록 -> 올리기가 실패하면 그 주제도 셈(실패 직후 같은 주제가 1번 더 나갈 수 있음), 실패가 잦아지면 올린 뒤 기록으로."""
    c = text and (cat_of({"text": text, "cat": cat}) or ("beauty" if th_beauty(title_of(text)) else ""))
    t = base or TH_TOPICS.get(c, "핫딜")
    r = seen.get("thtopic", {}).get("l", [])
    if r[-TH_TOPIC_RUN:] == [t] * TH_TOPIC_RUN:
        t = "특가" if t == "핫딜" else "핫딜"
    seen["thtopic"] = {"t": time.time(), "l": (r + [t])[-10:]}
    print("th topic", t)
    return t


def th_post(tok, text, link=None, image=None, tag="핫딜"):
    """Threads 글 1개: image = 사진 글(30초 처리 대기), link = 링크 미리보기(th_text), 둘 다 없으면 글만."""
    me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
    if link and not image:
        return th_text(tok, me, text, link, tag)
    q = urllib.parse.urlencode({"media_type": "IMAGE" if image else "TEXT", **({"image_url": image} if image else {}), "text": text[:500], "topic_tag": tag, "access_token": tok})
    cid = json.loads(http(f"{THREADS}/{me}/threads?{q}", method="POST"))["id"]
    time.sleep(30 if image else 10)  # 미디어 처리 대기 (공식 권장값)
    return th_ok(json.loads(http(f"{THREADS}/{me}/threads_publish?creation_id={cid}&access_token={tok}", method="POST")))


def th_bundle(seen, kind, text, link=None, image=None):
    """묶음 글 Threads(12·18시 리스트·토스 베스트 리스트·21시 카드·22시 미리보기 — 10/12 진우 '묶음 글은 반드시'): 실패하면 다음 실행에 1번 더(th_retry), 예외는 그대로(main 알림)."""
    try:
        return th_post(E.get("THREADS_TOKEN"), text, link, image, th_topic(seen))
    except Exception:
        seen.setdefault(time.strftime("thretry_%Y%m%d_", time.gmtime(time.time() + 9 * 3600)) + kind, {"t": time.time(), "text": text, "link": link, "img": image})
        raise


def th_reply(tok, to, text, link=None):
    """Threads 댓글(타래) 1개: 글·댓글 to에 reply_to_id로 이어 붙임(link = 링크 카드 — 22시 미리보기 댓글) -> 새 댓글 id."""
    me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
    for att in ({"link_attachment": link}, {}) if link else ({},):  # 링크 카드를 못 만들면(4279047) 카드 없이 1번 더(th_text와 같음 — 글 속 주소는 그대로)
        q = urllib.parse.urlencode({"media_type": "TEXT", "text": text[:500], "reply_to_id": to, **att, "access_token": tok})
        cid = json.loads(http(f"{THREADS}/{me}/threads?{q}", method="POST"))["id"]
        time.sleep(10)
        try:
            return th_ok(json.loads(http(f"{THREADS}/{me}/threads_publish?creation_id={cid}&access_token={tok}", method="POST")), top=False)["id"]
        except urllib.error.HTTPError as e:
            if not att or "4279047" not in (getattr(e, "body", "") or ""):
                raise


def th_poll(tok, text, opts, tag="핫딜"):
    """Threads 투표 글 1개(TEXT + poll_attachment, 공식 문서 create-posts/polls: 보기 2~4개·1~25, 글만 있는 글에만) -> 글 id. 보기가 규칙 밖이면 안 올림(ValueError).
    25 = UTF-8 바이트(한글 1자 = 3 — 10/23·24 한글 12~14자 보기가 HTTP 400 'Poll Option Has Invalid Length')."""
    if not 2 <= len(opts) <= 4 or not all(1 <= len(o.encode()) <= 25 for o in opts):
        raise ValueError(f"투표 보기는 2~4개·1~25바이트: {opts}")
    me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
    q = urllib.parse.urlencode({"media_type": "TEXT", "text": text[:500], "topic_tag": tag, "access_token": tok})
    form = urllib.parse.urlencode({"poll_attachment": json.dumps(dict(zip(POLL_KEYS, opts)), ensure_ascii=False)}).encode()  # 문서 예시처럼 본문(-d)으로
    cid = json.loads(http(f"{THREADS}/{me}/threads?{q}", form, {"Content-Type": "application/x-www-form-urlencoded"}, method="POST"))["id"]
    time.sleep(10)
    return th_ok(json.loads(http(f"{THREADS}/{me}/threads_publish?creation_id={cid}&access_token={tok}", method="POST")))["id"]


def th_reply_ok(seen):
    """지금 토큰으로 댓글(reply_to_id)을 달 수 있는지 — 내 최근 글에 댓글 컨테이너만 만들고 발행은 안 함(Threads에 안 보임, 24시간 뒤 사라짐).
    결과 = seen["threply"](3일 보관 -> 그 뒤 다시 확인). 권한 오류(HTTP 4xx)만 '안 됨'으로 남기고, 네트워크 오류는 이번엔 안 됨으로 보고 다음에 다시."""
    tok, r = E.get("THREADS_TOKEN"), seen.get("threply")
    if r or not tok or not TH_REPLY:
        return bool(r and r.get("ok"))
    try:
        me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
        last = json.loads(http(f"{THREADS}/{me}/threads?fields=id&limit=1&access_token={tok}"))["data"][0]["id"]
        q = urllib.parse.urlencode({"media_type": "TEXT", "text": "댓글 권한 확인", "reply_to_id": last, "access_token": tok})
        json.loads(http(f"{THREADS}/{me}/threads?{q}", method="POST"))["id"]
        seen["threply"] = {"t": time.time(), "ok": 1}
    except urllib.error.HTTPError as e:
        if e.code >= 500:
            print("threads 댓글 권한 확인 실패(다음에 다시)", e.code)
            return False
        seen["threply"] = {"t": time.time(), "ok": 0, "err": (getattr(e, "body", "") or repr(e))[:300]}
    except Exception as e:
        print("threads 댓글 권한 확인 실패(다음에 다시)", repr(e))
        return False
    print("threads 댓글 권한", "됨" if seen["threply"]["ok"] else "안 됨 — " + seen["threply"]["err"])
    return bool(seen["threply"]["ok"])


TH_WATCH_MIN, TH_WATCH_REPLY = 120, 35  # 첫 30분 대응(10/25 Cowork·진우): 올린 지 120분 안 글을 보고(실행이 늦거나 빠져도 놓치지 않게) 글 올린 뒤 35분 안에 달린 답글만 알림(실행 간격 ~15분 여유)


def th_watch(seen):
    """첫 30분 대응(10/25 Cowork — 설정값 변경 X): 우리 Threads 글(올린 지 TH_WATCH_MIN분 안)에 다른 사람 답글(글 올린 뒤 TH_WATCH_REPLY분 안 — 우리 링크 댓글 밑 답글까지, /conversation)이 달리면
    관리자에게 1번(글 링크 + 답글 내용) — 진우가 빨리 답하게. 자동 댓글·리포스트 X(답은 사람이). 답글 읽기 권한(threads_read_replies) 없음 = 하루 1번 알림(그 밖 오류 = 그 글만 건너뜀).
    알린 답글 id = seen thw(3일). 공개 로그엔 답글 내용·아이디 X(개수만)."""
    tok = E.get("THREADS_TOKEN")
    if not tok:
        return
    now = time.time()
    w = seen.setdefault("thw", {"ids": []})
    w["t"] = now
    me = json.loads(http(f"{THREADS}/me?fields=id,username&access_token={tok}"))
    ps = json.loads(http(f"{THREADS}/{me['id']}/threads?fields=id,permalink,timestamp&limit=10&access_token={tok}")).get("data", [])
    ts = lambda x: datetime.strptime(str(x)[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp()  # Threads = UTC(+0000)
    n = 0
    for p in [p for p in ps if p.get("timestamp") and now - ts(p["timestamp"]) <= TH_WATCH_MIN * 60]:
        try:
            rs = json.loads(http(f"{THREADS}/{p['id']}/conversation?fields=id,text,username,timestamp&access_token={tok}")).get("data", [])  # 모든 깊이(우리 링크 댓글 밑 답글도)
        except urllib.error.HTTPError as e:
            k, perm = time.strftime("alert_thw_%Y%m%d", time.gmtime(now + 9 * 3600)), re.search(r'permission|"code":\s*(?:10|200)\b', getattr(e, "body", "") or "", re.I)
            if perm and k not in seen:  # 권한 없음만 하루 1번(속도 제한·일시 오류 = 그 글만 건너뜀)
                alert(seen, k, f"⚠️ Threads 답글 읽기 안 됨(HTTP {e.code}) — 토큰에 threads_read_replies 권한이 있는지 확인해 주세요(첫 30분 답글 알림이 멈춤)")
            print("th watch 답글 읽기 실패", e.code)
            if perm:
                return
            continue
        for r in rs:
            if r.get("username") == me.get("username") or r.get("id") in w["ids"] or not r.get("timestamp") or ts(r["timestamp"]) - ts(p["timestamp"]) > TH_WATCH_REPLY * 60:
                continue
            mins = max(0, int((now - ts(p["timestamp"])) // 60))
            try:  # 텔레그램 시간 초과 = 이 답글만 다음 실행에(다른 답글은 계속)
                ok = tg("sendMessage", chat_id=ADMIN, text=f"💬 Threads 답글 — 올린 지 {mins}분 된 글\n{p.get('permalink') or ''}\n\n@{r.get('username') or '?'}: {clip(r.get('text') or '(글 없음)', 400)}\n\n👉 30분 안에 답하면 노출에 좋아요(자동 답글 X)",
                        link_preview_options={"is_disabled": True})
            except Exception as e:
                print("th watch 알림 실패", type(e).__name__)
                continue
            if ok:
                w["ids"] = (w["ids"] + [r["id"]])[-300:]
                n += 1
    if n:
        print("th watch 답글 알림", n)


def th_retry(seen):
    """실패한 묶음 글 Threads를 같은 날 다음 실행에 1번만 더."""
    tok, today = E.get("THREADS_TOKEN"), time.strftime("thretry_%Y%m%d_", time.gmtime(time.time() + 9 * 3600))
    for k in [k for k, v in seen.items() if k.startswith("thretry_") and isinstance(v, dict) and not v.get("done")]:
        seen[k]["done"] = 1
        if tok and k.startswith(today) and not th_landed(tok, seen[k]["text"], seen[k]["t"] - 300):
            th_post(tok, seen[k]["text"], seen[k].get("link"), seen[k].get("img"), th_topic(seen))
    for k in [k for k in seen if k.startswith("thabq_") and time.time() - seen[k].get("t", 0) >= 600]:  # B·C·S 글의 링크 댓글이 실패했던 것 -> 다음 실행에 1번만 더(같은 실행 X — 잠깐 끊긴 동안 2번 다 실패 X, 10/25 리뷰 · 안 되면 알림, 그 뒤엔 안 함)
        v = seen.pop(k)
        try:
            rid = th_reply(tok, v["id"], v["text"])
            seen.get("thab", {}).get("m", {}).get(v["id"], {})["r"] = rid
        except Exception as e:
            alert(seen, f"alert_thab2_{v['id']}", f"⚠️ Threads 링크 댓글 2번째도 실패: {err_brief(e)}\n링크 없는 딜 글이 남았어요 — 직접 첫 댓글로 달거나 글을 지워 주세요\n{v['text']}")


def th_landed(tok, text, since):
    """실패로 끝난 글이 사실 올라갔는지(시간 초과 뒤 게시 — 10/25 리뷰: 다시 올리면 두 번): 내 최근 글 5개 중 since 뒤·첫 줄(대가성 문구 다음 첫 줄 40자)이 같은 글. 확인 실패 = False(다시 올림)."""
    try:
        me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
        xs = json.loads(http(f"{THREADS}/{me}/threads?fields=text,timestamp&limit=5&access_token={tok}")).get("data") or []
        head = lambda t: next((l for l in (t or "").split("\n\n")[1:2] or [t or ""]), "")[:40]
        return any(head(x.get("text")) == head(text) and datetime.strptime(x["timestamp"], "%Y-%m-%dT%H:%M:%S%z").timestamp() >= since for x in xs)
    except Exception as e:
        print("th landed 확인 실패", err_brief(e))
        return False


TH_SOLO_MAX, TH_SOLO_MIN, TH_SOLO_GAP, TH_SOLO_SAVE, TH_SOLO_RUN, TH_LIST_HOURS, TH_TOSS_KINDS = 99, 0, 45 * 60, 1, 1, (12, 15, 18), ("best", "cat")  # 10/12 01:20 진우 '한도 없이 45분마다'(하루 5개 -> 99 = 사실상 없음), 리스트 12·15·18시, 토스 리스트 = 베스트 + 17시 생필품(10/12 22:45)
TH_TOSS_FILL = ("day", "best", "cat")  # 10/12 22:50 진우 '많이 팔리는 제품도 꾸준하게 — 토스에서 실적 볼 수 있으니까': 이 토스 회차(하루특가·베스트·생필품 카테고리) 픽 = Threads 채움 후보,
# 채움 땐 토스 픽 먼저(회차 1순위 먼저 · 생필품 먼저 · 점수 · 최근), 진우 예약·다른 몰 ①②·화장품은 지금 순서 그대로. () = 끔
TOSS_NO_CMP, TH_TOSS_DR = True, 30  # 10/12 21:05 토스 비즈니스 답변 '대가성 문구·게시 시점 가격 표시, 타 쇼핑몰과의 가격 비교 없이' -> 진우: 토스 글 전부에서 쿠팡 등 다른 몰 비교 뺌
# (채널 새 글·링크 교체·posts.json(사이트 딜 페이지·카드·리스트·Threads)·미리보기·재오픈) + '⚠️ 게시 시점 가격' 줄. 토스 딜 Threads 고르기는 토스 자체 신호(30일 최저가·순위·할인율 TH_TOSS_DR%↑). False = 예전
TH_SOLO_FILL = True  # 10/12 18:55 진우 '상위 딜로 채우기': 45분이 됐는데 ①·화장품·② 후보가 없으면 최근 3시간 채널 딜 중 점수 높은 것 1개(같은 점수면 제휴 링크 먼저, 그다음 최근 것) — Threads에 나간 것·🛒·품절 X, 화장품 하루 2개·45분 간격 그대로. False = 끔
TH_SLOTS = None  # 개별 글 고정 슬롯(예: (9, 11, 15, 20, 23) — 슬롯 시각 뒤 첫 실행에 대기 중 1순위 1개, 토스 이름 예약·뷰티 회차 글은 줄에서 기다림). 10/12 01:10 진우 요청 -> 01:20 취소('45분 간격 유지') = None
TH_SOLO_RANK = 3  # 10/11 23:40 진우 '이 방식 유지하면서 경과 보기'(밤 메르헨트 💸 2,000원 글 50분에 조회 20 — 낮 글보다 빠름): 개별 글 기준 못 박음 —
# ① 쿠팡 같은 상품 대비 N원 쌈이 확실한 🔥(💸 훅, 금액 상관없이) 먼저 ② 30일 최저가·순위 1~3위 ③ 🛒·단위가격 참고만은 리스트로(18시 채움 없음 = TH_SOLO_MIN 0)  # 10/11 진우 결정 '나누지 말고 묶기, 꾸준하게'(2주 동결 ~10/25):
# Threads 개별 글 = 하루 최대 5개·45분 간격·1회 1개·위 ①② 순서로만, 나머지는 리스트로
# (12·18시 '지금 살 만한 딜'·토스 베스트 리스트, 21시 모아보기 카드, 22시 미리보기). 텔레그램 채널은 개별 글 그대로
TH_BEAUTY_MIN, TH_BEAUTY_MAX = 1, 7  # (10/12 19:50 진우 2 -> 4 -> 20:00 "6~7개까지도 좋겠는데" -> 7) 10/11 23:50 진우 '화장품은 꾸준하게 올리자, 소모량이 많을 거라 생각해' + '우선 관찰': 개별 글 3~5개 중 매일 화장품 1~2개 —
# 화장품이 TH_BEAUTY_MIN개 안 찼으면 그 자리는 남겨둠(다른 글은 TH_SOLO_MAX - 1개까지), 화장품은 하루 TH_BEAUTY_MAX개까지. 자리 채우는 순서: ①② 화장품(소모품 먼저)
# > 진우 화장품 링크·이름 예약(🛒 X) > 오늘 진우 화장품 링크가 더 없으면 15·19시 토스 뷰티 회차 1개(소모품 먼저). 시간은 그대로(진우 예약·뷰티 회차 시각)
TH_BEAUTY_USE = (r"클렌징|클렌저|폼클렌|(?:립|아이|립앤아이|메이크업|포인트|네일|마스카라)\s*리무버|[선썬]\s*(?:크림|스틱|쿠션|블[록럭]|로션|젤|세럼|밀크|스프레이)"  # 소모품(썬·선 둘 다)
                 r"|(?:토너|각질|닦토|진정|스킨|화장|코튼|흔적|필링|모공|비타민|PHA|수분|트러블)\s*패드|화장솜|(?:마스크|시트|모델링|수면)\s*팩|(?:니들|여드름|스팟)\s*패치")
TH_BEAUTY_MORE = r"비비\s*크림|[BbCc]{2}\s*크림|(?:리페어|페이스|영양|진정|보습|장벽|시카|EGF|세라마이드|수분|탄력|톤업|주름|쿨링)\s*크림|기초\s*\d*\s*종|\d+\s*종\s*기초"  # 사이트 '💄' 낱말(BEAUTY)에 없는 화장품(10/12 진우 BB크림 10개)
TH_BEAUTY_NOT = r"충전기|케이블|카트리지|프린터|살균기|선풍기|가습기|세제|스티커|노트북|에센스웨어|욕실|주방|변기|얼룩|곰팡이"  # 화장품 낱말이 들어도 화장품 아님(10/12 리뷰: 진우 링크 '에센스웨어 충전기' 등)


def th_tier(plain):
    """Threads 개별 글감 순위: 1 = 쿠팡 같은 상품 대비 N원 쌈이 확실한 🔥('같은 상품…보다 N원 쌈', TH_SOLO_SAVE원↑) · 2 = 30일 최저가·순위 1~TH_SOLO_RANK위
    · 0 = 리스트로(🛒 약한 딜·단위가격 참고만·나머지)."""
    if th_weak(plain) or th_steady(plain):  # 👍 꾸준템 = 순위가 있어도 강한 딜(①②) X — TOP 리스트 앞자리·놓친 ①② 이월 X(10/22 리뷰)
        return 0
    m = re.search(rf"({SAVE_STORES})\s*같은 상품[^\n—]*?보다\s*([\d,]+)원\s*쌈", plain)
    if m and int(m.group(2).replace(",", "")) >= TH_SOLO_SAVE:
        return 1
    plain = re.sub(r"[^\n]*많이 보는 글 \d+위[^\n]*", "", plain)  # 봇 '🏆 인기 · 뽐뿌에서 지금 많이 보는 글 N위' = 커뮤니티 조회 순위(상품 순위 아님, 10/12 리뷰)
    r = re.search(r"(?:^|· |\n)(?:[^·\n💰⭐]|·(?! )){1,24}?(?<!\d)(\d{1,2})위", plain)  # 토스 카테고리 이름에 든 '·'(선블록·선크림·선로션 2위)도, '10위'를 '0위'로 안 읽게
    dr = TOSS_NO_CMP and is_toss("", plain) and max([int(x) for x in re.findall(r"(\d{1,2})\s*%\s*(?:↓|할인)|할인율\s*(\d{1,2})\s*%", plain) for x in x if x] or [0]) >= TH_TOSS_DR  # 토스 딜 = 할인율도(쿠팡 비교 없이)
    return 2 if re.search(r"30일 (내 )?최저가(?!는 아니|가 아니| 아님)", plain) or (r and 1 <= int(r.group(1)) <= TH_SOLO_RANK) or dr else 0


def th_weak(plain):
    """🛒 약한 딜: '특가로는 약한 제품' 문구, 또는 제목 줄이 '🛒 ['로 시작(10/11 진우 🛒 글 중 문구 없이 '쿠팡에선 같은 상품을 못 찾아' 쓴 것 — 로로보아·삭스팡·후드 필터가
    ②로 읽혀 Threads에 🔥로 나가던 것, 10/12 리뷰), 몰별 틀은 머리 줄 끝 🛒. 토스 Threads 글 끝 '🛒 https://…' 링크 줄은 아님."""
    return "특가로는 약한 제품" in plain or bool(re.search(r"^🛒 \[", plain, re.M)) or any(m[2] == "🛒" for m in map(MALL_HEAD.fullmatch, plain.split("\n")) if m)


def th_steady(plain):
    """👍 꾸준템(10/22 진우 '최저가 아니어도 꾸준히 팔리는 제품'): 제목 줄이 '👍 ['로 시작(예전 틀 예약 글) 또는 몰별 틀 머리 줄 끝 👍.
    토스 글의 '👍 …' 설명 줄은 아님('['로 시작 X)."""
    return bool(re.search(r"^👍 \[", plain, re.M)) or any(m[2] == "👍" for m in map(MALL_HEAD.fullmatch, plain.split("\n")) if m)


def th_strong(plain):
    """Threads 개별 글감인지(th_tier 1·2)."""
    return th_tier(plain) > 0


def th_beauty(name):
    """화장품인지(제목·상품명으로만 — 본문 '선크림 대신' 같은 말에 안 걸리게): 2 = 소모품(TH_BEAUTY_USE), 1 = 다른 화장품(사이트 💄 낱말 + TH_BEAUTY_MORE), 0 = 아님."""
    name = re.sub(r"^\s*(?:[🔥🛒👍]\s*)?\[[^\]]*\]\s*", "", name)  # 몰 이름([올리브영] 등)은 안 봄
    if re.search(TH_BEAUTY_NOT, name):
        return 0
    return 2 if re.search(TH_BEAUTY_USE, name) else 1 if re.search(BEAUTY, name) or re.search(TH_BEAUTY_MORE, name) else 0


def th_day(seen, now):
    """오늘(KST) Threads 개별 글 기록 {n: 글 수, b: 그중 화장품, last: 마지막 시각 — 어제 마지막 글도(45분 간격은 밤 12시를 넘어서도)}.
    b 없는 기록(화장품 규칙 배포 전 = 10/12 0:02 재오픈 샤워기 헤드 1개)은 화장품 0개."""
    kst = time.gmtime(now + 9 * 3600)
    r = seen.get(time.strftime("thsolo_%Y%m%d", kst), {"n": 0, "last": 0})
    return {**r, "b": r.get("b", 0), "last": max(r["last"], seen.get(time.strftime("thsolo_%Y%m%d", time.gmtime(now + 9 * 3600 - 86400)), {}).get("last", 0))}


def jw_beauty(seen, now):
    """오늘 Threads 차례를 기다리는 진우 화장품 링크·이름 예약(🛒 X)이 있는지 — 있으면 그게 화장품 자리를 채움(15·19시 토스 뷰티 회차는 Threads에 안 냄, 10/11 23:50 진우).
    = 아직 시각이 안 된 예약 + 시각이 됐지만 아직 Threads에 안 나간 것(채널엔 나갔고 threads_deals 3시간 안 / 같은 실행 뒤 순서인 toss_picks가 올릴 이름 예약 — 10/12 리뷰:
    19:00 진우 링크가 19:04 실행의 뷰티 회차에 자리를 뺏기던 것)."""
    kst = time.gmtime(now + 9 * 3600)
    today, nowk, since = time.strftime("%Y-%m-%d", kst), time.strftime("%Y-%m-%d %H:%M", kst), time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 6 * 3600))
    if any(p.get("own") and not p.get("th") and not p.get("shelf") and p["t"] >= max(since, today) and aff(p.get("url")) and not th_weak(p["text"]) and not th_steady(p["text"]) and th_beauty(title_of(p["text"])) for p in load(POSTS, [])):  # 👍는 화장품 자리를 안 가져감(threads_deals) -> 대신 막지도 X
        return True
    return any(e["at"].startswith(today) and (e.get("api") or (e.get("deal") and aff(e.get("url")))) and not th_weak(plain_of(e.get("text") or "")) and not th_steady(plain_of(e.get("text") or ""))
               and th_beauty(e.get("name") or title_of(plain_of(e.get("text") or "")))
               and (e["at"] >= nowk or (e.get("api") and e["at"] >= since and seen.get("pk_" + e["at"], {}).get("st") not in ("done", "skip"))) for e in load(EVENTS, []))


def th_follow(toss):
    """Threads 개별·재오픈 글 끝 팔로우 줄: 토스 글 = '특가'(10/13 00:35 진우 — 토스 요청 '타 쇼핑몰과의 가격 비교 없이'), 다른 몰 글 = 예전 '가격 비교' 그대로."""
    return f"👋 팔로우하면 매일 이런 {'특가가' if toss else '가격 비교가'} 피드에 떠요"  # 10/21 진우: 🙋 -> 👋(토스 글 🙋 '누가' 줄과 안 겹치게, 문구는 그대로)


def th_note(note):
    """Threads 개별 글 머리: 제휴 고지문 맨 앞, 10/12~ 그 앞에 '[광고] '(10/11 23:40 진우: 본문 틀 💸 훅 → 🔥 제목 → … → 👉 링크는 그대로, [광고]만 맨 앞)."""
    return (("[광고] " if ad_on() else "") + note + "\n\n") if note else ""


def th_solo(seen, plain, fill=False, beauty=0, slot=False, reopen=None, gate=False, top=False):
    """Threads 개별 글을 지금 올려도 되는지(딜 글·토스 이름 예약·재오픈·뷰티 회차 같이 셈): 오늘 TH_SOLO_MAX개 미만·앞 개별 글과 TH_SOLO_GAP 이상, 🛒 X,
    강한 딜(th_strong)만 — 18시 넘어 오늘 TH_SOLO_MIN개가 안 찼으면 fill(일반 🔥 딜)도. 올렸으면 th_mark(seen, beauty).
    beauty(th_beauty) = 화장품: 하루 TH_BEAUTY_MAX개까지, 오늘 화장품이 TH_BEAUTY_MIN개 안 찼으면 slot(진우 화장품 링크·이름 예약·뷰티 회차)은 ①② 아니어도 O.
    화장품 아닌 글은 화장품 자리(TH_BEAUTY_MIN개)를 남기고 셈.
    reopen("night"/"am") = 재오픈 글: 개별 5개·화장품 수와 따로 밤 TH_REOPEN_NIGHT·아침 TH_REOPEN_MORN·하루 TH_REOPEN_DAY개, 45분 간격은 같이, ①②만(10/12 진우). gate = 간격·한도만 봄."""
    now = time.time()
    r = th_day(seen, now)
    b = r["b"]
    if reopen:
        rn, ra = r.get("rn", 0), r.get("ra", 0)
        if now - r["last"] < (th_gap(r["last"]) if TH_SLOTS is None else TH_REOPEN_GAP) or rn + ra >= TH_REOPEN_DAY or (rn >= TH_REOPEN_NIGHT if reopen == "night" else ra >= TH_REOPEN_MORN):
            return False
        return gate or ("특가로는 약한 제품" not in plain and th_strong(plain))
    if r["n"] >= TH_SOLO_MAX or "특가로는 약한 제품" in plain or (now - r["last"] < th_gap(r["last"]) if TH_SLOTS is None else th_slot(r, now) is None):
        return False
    if beauty:
        if b >= TH_BEAUTY_MAX:
            return False
        if slot and b < TH_BEAUTY_MIN and not th_weak(plain):  # 🛒(문구 없이 제목만 🛒인 것도)는 화장품 자리에도 X
            return True
    elif r["n"] - b >= TH_SOLO_MAX - TH_BEAUTY_MIN:
        return False
    return th_strong(plain) or (top and not th_weak(plain)) or (fill and time.gmtime(now + 9 * 3600).tm_hour >= 18 and r["n"] < TH_SOLO_MIN)  # top = 상위 딜 채우기(TH_SOLO_FILL)


def th_mark(seen, beauty=0, reopen=None):
    now = time.time()
    k, r = time.strftime("thsolo_%Y%m%d", time.gmtime(now + 9 * 3600)), th_day(seen, now)
    if reopen:  # 재오픈은 따로 셈(rn 밤 / ra 아침), 45분 간격(last)은 같이
        seen[k] = {**seen.get(k, {"n": 0}), "t": now, "b": r["b"], "rn": r.get("rn", 0) + (reopen == "night"), "ra": r.get("ra", 0) + (reopen == "am"), "last": now}
        return
    h = time.gmtime(now + 9 * 3600).tm_hour
    seen[k] = {**seen.get(k, {}), "t": now, "n": r["n"] + 1, "b": r["b"] + bool(beauty), "last": now, **({"slots": r.get("slots", []) + ([h] if h in TH_SLOTS else [])} if TH_SLOTS else {})}


def th_slot(r, now):
    """지금 열린 개별 글 슬롯(TH_SLOTS 시각부터 1시간 안, 오늘 아직 안 씀) — 없으면 None."""
    h = time.gmtime(now + 9 * 3600).tm_hour
    return h if TH_SLOTS and h in TH_SLOTS and h not in r.get("slots", []) else None


def th_queue(seen, text, link, bt, img=None, tids=None):
    """슬롯 방식에서 토스 이름 예약·15·19시 뷰티 회차 개별 글은 바로 안 올리고 줄에 — threads_deals가 슬롯에 채널 딜과 같이 1순위를 고름(3시간 지나면 버림)."""
    now = time.time()
    seen["thq"] = {"t": now, "q": [x for x in seen.get("thq", {}).get("q", []) if now - x["t"] < 3 * 3600] + [{"t": now, "text": text, "link": link, "bt": bt, **({"img": img, "tids": list(tids or [])} if img else {})}]}


def th_fit(body, lim):
    """Threads 개별 글 본문을 lim자 안으로 — 줄 중간에서 안 자름(10/21 밤 Cowork: 쿠팡 글이 '⚠️ 확인할 점:'·'⚠️'만 남던 것). ⚠️ 줄은 끝에 남기고
    (넘치면 마지막 조각 '결제 전 최종가 확인 (… 가격)'만, 그래도 안 되면 줄째 뺌), 나머지 줄은 앞에서부터 들어가는 만큼 — 처음 넘치는 줄은 '…'로 줄이고 그 뒤는 뺌."""
    if len(body) <= lim:
        return body
    lines = body.split("\n")
    ws = [l for l in lines if l.startswith("⚠️")]
    short = [re.sub(r"^(⚠️\s*(?:확인할 점:?\s*)?).* · ", r"\1", w) for w in ws]  # 앞 조각들 빼고 마지막 조각만
    size = lambda xs: len("\n".join(xs)) + bool(xs)  # 줄들 + 앞 줄바꿈
    if len(lines[0]) + size(short) > lim:  # 제목과 ⚠️ 짧은 줄도 같이 못 들어감 = ⚠️ 줄째 뺌(제목 먼저)
        ws, short = [], []
    out = []
    for l in (l for l in lines if not l.startswith("⚠️")):
        room = lim - size(short) - (size(out) - bool(out)) - bool(out)
        if len(l) <= room:
            out.append(l)
            continue
        if room >= 15 and l.strip():
            out.append(clip(l, room - 1))
        break
    for k, (w, sw) in enumerate(zip(ws, short)):
        room = lim - (size(out) - bool(out)) - bool(out) - size(short[k + 1:])
        out += [w] if len(w) <= room else [sw] if len(sw) <= room else []
    return "\n".join(out).rstrip("\n")


def threads_deals(seen):
    """채널에 올라간 딜 중 골라서 Threads 개별 글로(10/11 진우 '나누지 말고 묶기': th_solo — 하루 5개·45분 간격·강한 🔥만, 나머지는 리스트로).
    링크 = 사이트 딜 페이지(구매 버튼·대가성 문구 있음). 사이트 반영 전(404)이면 다음 실행에. posts.json에 th 표시 -> 두 번 안 올림. 3시간 지난 딜은 안 올림(식은 딜), 1회 1개."""
    tok, posts = E.get("THREADS_TOKEN"), load(POSTS, [])
    since = time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - 3 * 3600))
    fresh = [i for i, p in enumerate(posts) if not p.get("th") and not p.get("shelf") and p["t"] >= since and not p["text"].startswith("📋")]  # shelf = Threads X
    skip = [i for i in fresh if not aff_note(posts[i].get("url") or "")]  # 10/19 밤 진우 'Threads는 수수료 딜만': 대가성 문구가 붙는 링크만 — 나머지는 텔레그램·사이트에만(나중에 진우 링크로 바뀌면 그때 후보)
    new = [i for i in skip if "th" not in posts[i]] if tok else []  # 로그는 딜마다 1번(th = 0: 거짓값이라 리스트 셈은 그대로)
    for i in new:
        print("threads skip (수수료 링크 아님)", clip(title_of(posts[i]["text"]), 40), "|", link_kind(posts[i].get("url")))
        posts[i]["th"] = 0
    if new:
        json.dump(posts, open(POSTS, "w"), ensure_ascii=False)
    fresh = [i for i in fresh if i not in skip]
    rei = {i for i in fresh if posts[i].get("own") and (posts[i].get("re") or posts[i].get("url") in {e["url"] for e in load(EVENTS, []) if e.get("re") and e.get("url")})}  # + E 자동 재게시(posts re)  # 10/12 23:05 진우 재업로드(events "re": true, 같은 진우 링크로 전에 나간 강점 품목)
    bt = {i: 0 if i in rei and not posts[i].get("re") else th_beauty(title_of(posts[i]["text"])) for i in fresh}  # 재업로드는 화장품 하루 한도에서 뺌(밤 화장품 글이 한도를 채워도 막히지 않게)
    now = time.time()
    q = [x for x in seen.get("thq", {}).get("q", []) if now - x["t"] < 3 * 3600]  # 슬롯 기다리는 토스 이름 예약·뷰티 회차 글
    cand = [(i, posts[i]["text"], bt[i], posts[i]["t"]) for i in fresh if not th_steady(posts[i]["text"]) and th_solo(seen, posts[i]["text"], beauty=bt[i], slot=bool(posts[i].get("own")), top=i in rei)] \
        + [(x, x["text"], x["bt"], time.strftime("%Y-%m-%d %H:%M", time.gmtime(x["t"] + 9 * 3600))) for x in q if th_solo(seen, x["text"], beauty=x["bt"], slot=True)]  # 진우 화장품 링크·이름 예약은 화장품 자리 채움
    grp = lambda c: -1 if isinstance(c[0], int) and c[0] in rei else 0 if th_tier(c[1]) == 1 else 1 if c[2] and TH_BEAUTY_MIN else 2  # 10/12 01:10 진우: ① 쿠팡 같은 상품 차이 > 화장품(하루 1~2) > ② 30일 최저가·순위 (재업로드는 맨 먼저, 23:05)
    wb = wx_bonus(seen)  # 날씨 가점(10/15 진우): 같은 등급 안에서만 먼저(🔥·30일 최저가 순서 그대로)
    strong = [c[0] for c in sorted(cand, key=lambda c: (grp(c), grp(c) == 1 and c[2] != 2, th_tier(c[1]) or 3, -wb(title_of(c[1])), c[3]))]  # 화장품은 소모품 먼저, 같으면 먼저 올라온 것
    out = {int(k[5:]) for k, v in seen.items() if k.startswith("sold_") and k[5:].isdigit() and isinstance(v, dict) and any(x[4] for x in v.get("it", []))}
    own = sorted((i for i in fresh if posts[i].get("own") and posts[i].get("mid") not in out and th_solo(seen, posts[i]["text"], beauty=bt[i], top=True)), key=lambda i: (th_steady(posts[i]["text"]), posts[i]["t"], i not in strong))  # 기다리는 진우 🔥 딜(🛒는 th_solo가 거름), 먼저 올라온 것부터(같은 분이면 강한 후보 먼저) · 👍 꾸준템은 🔥 다 나간 뒤(강한 후보·끝나가는 칸 X — 10/22 진우)
    left = own and kst_ts(posts[own[0]]["t"]) + 3 * 3600 - now  # 10/22 진우 '끝나가는 🔥 먼저': 다음 칸(간격 최대 + 다음 실행)까지 기다리면 3시간 창이 지나는 진우 딜이면
    late = [i for i in own if not th_steady(posts[i]["text"]) and kst_ts(posts[i]["t"]) + 3 * 3600 - now < TH_SOLO_GAP + TH_GAP_JITTER + RUN_GAP * 60] if TH_SOLO_FILL else []  # 끝나가는 진우 🔥(창이 먼저 끝나는 것 = 먼저 올라온 것부터)
    first = strong[:1]  # 10/22 Cowork(14:37 re 깨끗한나라(창 15:29)가 먼저 나가 11:47 진우 🔥 홈키파 창 14:47 놓침): 끝나가는 진우 🔥 = re·①②·화장품보다도 먼저(re도 끝나가면 그 안에서 먼저 올라온 순)
    strong = late + [c for c in strong if c not in late] if strong else strong
    jump = strong[:1] != first  # 순서가 바뀔 때만 로그·채움 차례(own)
    if jump:
        print(f"threads turn own(창 끝남 {max(0, int(left)) // 60}분 전) — re·①②·화장품 {len(first)}개 앞")
    todo, turn = strong or [i for i in fresh if (posts[i].get("own") or posts[i].get("s", 0) >= 7) and not th_steady(posts[i]["text"]) and th_solo(seen, posts[i]["text"], fill=True, beauty=bt[i])], "own" if jump and strong[0] not in rei else None  # turn = 채움 칸 종류(own·toss·post) — 앞으로 온 게 re면 채움 차례 X
    if not todo and TH_SOLO_FILL:  # ①·화장품·② 없음 -> 채움(10/12 진우): 토스 픽 ↔ 진우 🔥 딜 번갈아(10/21), 둘 다 없으면 점수 높은 순 · 같은 점수면 제휴 링크 · 최근 것, 품절(품절 지켜보기 기록) X
        gone = {x[0] for k, v in seen.items() if k.startswith("sold_") and isinstance(v, dict) for x in v.get("it", []) if x[4]}  # 품절·특가 끝 토스 상품
        rd = th_day(seen, now)  # 밤(0~6시) 재오픈이 기다리면 토스 픽 칸은 비워 둠(같은 실행 뒤 toss_reopen 차례 — 10/22 새벽 토스 글이 자정 재오픈 칸을 가져가던 것)
        rw = HAS_TOSS and time.gmtime(now + 9 * 3600).tm_hour < TH_REOPEN_AM[0] and rd.get("rn", 0) < TH_REOPEN_NIGHT and rd.get("rn", 0) + rd.get("ra", 0) < TH_REOPEN_DAY \
            and any(not e.get("st") for e in seen.get("reopen", {}).get("q", []))
        tq = [] if rw else [x for x in seen.get("thtoss", {}).get("q", []) if (TH_SOLO_GAP if x.get("l") else 0) <= now - x["t"] < 3 * 3600 and x["id"] not in gone
                                     and not ("밤 12시까지" in x["text"] and now >= kst_ts(time.strftime("%Y-%m-%d", time.gmtime(x["t"] + 9 * 3600)) + " 23:30")) and th_solo(seen, x["text"], beauty=x["bt"], top=True)]  # 하루특가 = 그날 23:30까지만(밤 12시 넘어 '밤 12시까지' 글 X)
        due = late and tq and seen.get("thfill", {}).get("k") != "toss"  # 10/22 진우 '끝나가는 🔥 먼저': 차례와 상관없이 이번 칸(창이 먼저 끝나는 것 = 먼저 올라온 것부터), 다음 칸은 토스
        if own and (due or not tq or seen.get("thfill", {}).get("k") == "toss"):  # 10/21 진우 '번갈아': 직전 채움이 토스 픽이면 이번 칸 = 진우 딜(토스 대기 줄이 비어도 진우 딜)
            todo, turn = own, "own"
        elif tq:
            tops = top_toss(seen, now)  # 10/22 Cowork: 잘 된 토스 상품 = 순위 한 칸·점수 +TOP_BONUS(하루 TOP_BONUS_DAY개)
            hit = lambda x: top_hit(tops, x["id"], x.get("n"))
            todo, turn = sorted(tq, key=lambda x: (x["r"] - hit(x), x["k"] != "cat", -x["s"] - TOP_BONUS * hit(x), -wb(title_of(x["text"])), -x["t"])), "toss"
        else:
            todo, turn = sorted((i for i in fresh if posts[i].get("mid") not in out and th_solo(seen, posts[i]["text"], beauty=bt[i], top=True)),
                                key=lambda i: (-(posts[i].get("s") or 0), not aff(posts[i].get("url")), -wb(title_of(posts[i]["text"])), [-ord(c) for c in posts[i]["t"]])), "post"
        if todo:
            print("threads fill turn", f"own(창 끝남 {max(0, int(left) // 60)}분 전)" if due else turn, f"(대기 own {len(own)}·toss {len(tq)})")
    todo = todo[:TH_SOLO_RUN]
    r, today = th_day(seen, now), time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600))  # 실행마다 1줄(10/12 진우 '누락 없이'): 후보 · ①② · 개별 · 빠짐 이유
    RUN["th_why"] = " ".join(map(str, ("threads 후보", len(fresh), "· ①②", sum(th_tier(posts[i]["text"]) > 0 for i in fresh), "· 개별", len(todo) if tok else 0, "· 🛒", sum(th_weak(posts[i]["text"]) for i in fresh),
          "· 화장품 한도", sum(bool(bt[i]) and r["b"] >= TH_BEAUTY_MAX and th_tier(posts[i]["text"]) > 0 for i in fresh), "· 간격", f"대기({th_gap(r['last']) // 60}분)" if now - r["last"] < th_gap(r["last"]) else "열림",
          "· 3시간 지난 ①②(리스트로)", sum(p["t"].startswith(today) and p["t"] < since and not p.get("th") and not p.get("shelf") and th_tier(p["text"]) > 0 for p in posts),
          "· 토스 픽 대기", sum(now - x["t"] < 3 * 3600 for x in seen.get("thtoss", {}).get("q", [])), "· 수수료 링크 아님", len(skip))))
    print(RUN["th_why"])
    tm = seen.setdefault("thmiss", {"u": []})
    tm["t"] = now
    for u in sorted(th_missed(posts, now) - set(tm["u"])):  # 3시간 창이 끝나 Threads를 놓친 진우 🔥 = 1번 로그(재게시 루틴 후보 — 10/25)
        print("threads 놓침(3시간 지남 · 3일 뒤 재게시 루틴이 지금 🔥·24시간 안 확인 가격이면 고름):", clip(title_of(next(p["text"] for p in reversed(posts) if p.get("url") == u)), 40))
        tm["u"] = (tm["u"] + [u])[-200:]
    if not tok or not todo:
        return
    me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
    for i in todo:
        if isinstance(i, dict):  # 줄 선 토스 글(쉐어링크 그대로 — API 상품은 사이트 X): 슬롯 줄(thq)·토스 픽 채움(thtoss)
            for k in ("thq", "thtoss"):
                if k in seen:
                    seen[k]["q"] = [x for x in seen[k]["q"] if x is not i]
            th_mark(seen, i["bt"])
            if turn:
                seen["thfill"] = {"t": now, "k": turn}  # 직전 채움 종류(번갈아) — seen 정리가 t를 봄
            if turn == "toss" and i.get("id") and top_hit(top_toss(seen, now), i["id"], i.get("n")):
                top_mark(seen, now, i["id"])
            th_deal(seen, tok, me, i["text"], i["link"], image=i.get("img"), tids=i.get("tids"))
            continue
        url = th_url(posts[i], i)  # 10/19 진우 '직접 링크로': 텔레그램 버튼과 같은 링크(아주 긴 주소만 사이트 딜 페이지 — 그땐 사이트에 올라온 뒤에)
        if url.startswith(SITE):
            try:
                http(url, method="HEAD")
            except Exception:
                return
        note = aff_note(posts[i].get("url") or "")
        icon = "👍" if th_steady(posts[i]["text"]) else "🛒" if th_weak(posts[i]["text"]) else "🔥"  # 채널 글과 같게(약한 딜에 🔥 안 붙임)
        ls = re.sub(CP_OLD, CP_PLAIN[0], posts[i]["text"], flags=re.M).split("\n")  # 10/23 전 채널 글의 '🚀 쿠팡' 머리 줄 = 새 Threads 글엔 📦(채널 글은 그대로)
        mi = next((k for k in range(len(ls)) if mall_title(ls, k)), None)  # 몰별 틀(10/22 진우 '한눈에') = 대가성 문구 다음 줄이 채널 글과 같은 머리 줄
        sv = None if mi is not None else saving(posts[i]["text"])  # 고지문 다음 줄 = 얼마나 싼지(10/11 진우 'Threads 훅') — 몰별 틀은 머리 줄이 먼저(각도 칸)
        tw = f"\n{toss_when(posts[i]['t'])}" if TOSS_NO_CMP and is_toss(posts[i].get("url"), posts[i]["text"]) and "게시 시점" not in posts[i]["text"] else ""
        sv = None if tw or (TOSS_NO_CMP and is_toss(posts[i].get("url"), posts[i]["text"])) else sv  # 토스 딜 = 💸 쿠팡 줄 X
        head = th_note(note) + (f"💸 {sv[0]}보다 {sv[1]} 싸요\n" if sv else "")
        tail = f"\n\n👉 {url}\n{th_follow(TOSS_NO_CMP and is_toss(posts[i].get('url'), posts[i]['text']))}\n📲 실시간 알림 t.me/hotdeal_pick"
        body = re.sub(r"\n🏆 인기 · [^\n]*", "", "\n".join(ls[mi:]).split("\n\n출처:")[0].strip()) if mi is not None else f"{icon} {title_of(posts[i]['text'])}\n\n{comment_of(posts[i]['text'])}"
        lim = 480 - len(head) - len(tw) - len(tail)
        full = head + body + tw + tail  # 사람 느낌 글(th_voice) 재료 = 줄이기 전 글
        lim = lim if re.search(r"\n[🙋👍] ", body) else min(250, lim)  # 🙋·👍 줄 있는 토스 글 = 480자까지(빼기 전에 정함 — 10/20 리뷰)
        for e in ("👍", "🙋"):  # 10/20 진우 '사고 싶게': 토스 글 🙋·👍 줄 = 480자 넘으면 👍 -> 🙋 순서로 뺌
            body = re.sub(rf"\n{e} [^\n]*", "", body) if len(body) > lim else body
        fit = th_fit(body, lim)  # Threads 500자 제한 — 링크가 길면(검색 링크 ~210자) 코멘트를 줄임(줄 단위, ⚠️ 줄은 끝에 남김)
        if not tw and "게시 시점" not in fit and TOSS_NO_CMP and is_toss(posts[i].get("url"), posts[i]["text"]):  # 줄이다 토스 게시 시점 조각이 빠지면 끝에 다시(10/22 리뷰 — 몰별 틀은 머리·가격 줄만큼 길어짐)
            tw = f"\n{toss_when(posts[i]['t'])}"
            fit = th_fit(body, lim - len(tw))
        text = head + fit + tw + tail
        posts[i]["th"] = 1  # 먼저 표시: 실패해도 같은 딜 반복 시도 안 함(스팸 방지), 실패는 main()이 알림
        th_mark(seen, bt[i])
        if turn:
            seen["thfill"] = {"t": now, "k": turn}
        json.dump(posts, open(POSTS, "w"), ensure_ascii=False)
        th_deal(seen, tok, me, text, url, full, posts[i].get("cat"), image=img_of(posts[i]) or None)  # 주제 = 사이트 품목 칸(글 cat까지) · 쿠팡 실사 사진 있으면 사진 글(K-1)


CAL_HOUR, CAL_DAYS, CAL_LINK = (9, 40), 14, f"{SITE}events/?ref=thi"  # ref=thi = 정보 글 유입 따로(GoatCounter) · 10/25 2주 비교 뒤 진우·Cowork '정보 글 하루 1~2개 — 딜 글 수·간격은 그대로, 그 위에 더하기만': 아침 날씨(7:30) 뒤 '🗓 쇼핑 달력'(promos.json 앞으로 2주 · 바뀐 날만 · Threads만)
WEATHER_HOUR, SNACK_HOUR, DAILY_LOG_HOUR, WEATHER_DM = (7, 30), (15, 30), (20, 30), (6, 20)  # 10/15 23:40 진우 '계절·날씨 맞춰 추천·간식·일상': 아침 날씨 글 · 간식 3 · 운영 일지(Threads) · 일요일(요일 6) 20시 시즌 키워드 DM. None = 끔
WEATHER_LAT, WEATHER_LON, WEATHER_BONUS, WX_LATE = 37.57, 126.98, 5, 2 * 3600  # 서울(Open-Meteo, 키 없음) · 오늘 날씨 키워드에 맞는 딜 가점(TOP5·Threads 개별 = 동점일 때만 먼저 — 🔥·30일 최저가 순서는 그대로, 0 = 끔) · 그 시각 뒤 2시간 안에만
POLL_HOUR, POLL_REUSE = (21, 40), 7  # 10/17 진우 '유입 늘리기 ① 가격 투표'(Threads만, 하루 1번): 최저가 기록 품목 투표(10/22~ Claude 반말 질문·보기 4개 — poll_ai) + 다음 날 같은 회차에 결과·기록 최저 답글, 같은 품목은 7일 뒤에. 10/22 진우 '저녁 9시대'(12:30 조회 2~6 vs 저녁 운영 일지 124~177): 21:40 = 21시 모아보기·22시 미리보기·묶음 간격 사이. None = 끔
POLL_KEYS = ("option_a", "option_b", "option_c", "option_d")  # Threads poll_attachment 보기(2~4개, 보기마다 1~25 UTF-8 바이트 = 한글 8자 — 공식 문서 create-posts/polls·10/24 HTTP 400)
SUNEUNG = "2026-11-19"  # 2027학년도 수능(해마다 확인해서 바꿈) — 6일 전~당일 = 수능 주간 간식
WEATHER_RULES = (  # (조건, 이름, 아이템 키워드, 간식 키워드, 운영 일지 질문) — 위에서부터 맞는 것 모두. 키워드 = 딜 제목에 들어 있으면(키워드에 띄어 쓴 자리는 붙여 써도 맞음)
    (lambda w: w["rain"] >= 60, "비 소식", ("우산", "우비", "제습제", "실내 건조"), ("라면", "부침가루", "어묵"), "우산 챙기셨어요?"),
    (lambda w: w["tmin"] <= 3, "많이 추움", ("핫팩", "발열 내의", "전기 매트", "가습기"), ("군고구마", "어묵", "유자차"), "핫팩 벌써 꺼냈어요?"),
    (lambda w: w["tmin"] <= 10, "쌀쌀함", ("전기요", "기모", "보습 크림"), ("호빵", "핫초코", "고구마"), "다들 전기요 꺼냈어요?"),
    (lambda w: w["tmax"] >= 28, "더움", ("선풍기", "쿨 매트"), ("아이스크림", "탄산"), "선풍기 아직 안 넣으셨죠?"),
    (lambda w: w["hum"] <= 35, "건조함", ("가습기", "립밤", "핸드 크림", "바디 로션"), (), "가습기 트셨어요?"),
    (lambda w: w["tmax"] - w["tmin"] >= 10, "일교차 큼", ("가디건", "경량 조끼"), (), "겉옷 하나 챙기셨어요?"),
    (lambda w: (w["pm"] or 0) >= 36, "초미세먼지 나쁨", ("KF94", "KF80", "공기청정기 필터"), (), "오늘 마스크 쓰셨어요?"),
    (lambda w: "11-01" <= w["date"][5:] <= "11-30", "김장철", ("김장 비닐", "고무장갑", "천일염"), (), "올해 김장 하세요?"),
    (lambda w: "11-01" <= w["date"][5:] <= "11-11", "빼빼로데이", (), ("빼빼로",), "빼빼로 누구 주실 거예요?"),
    (lambda w: 0 <= (kst_ts(SUNEUNG + " 00:00") - kst_ts(w["date"] + " 00:00")) // 86400 <= 6, "수능 주간", (), ("찹쌀떡", "초콜릿", "견과"), "수능 응원 간식 뭐가 좋을까요?"))
SNACK_WORDS = ("과자", "젤리", "견과", "초콜릿", "초코", "커피", "아이스크림", "빵", "떡", "음료")  # 15:30 간식 글(+ 오늘 날씨 간식 키워드)
SNACK_NOT = r"머신|포트|메이커|그라인더|드리퍼|텀블러|제빵기|토스터|빵칼|떡갈비|케이스|필터|냉장고|배터리|제조기|금액권|과탄산"  # 간식 아님(커피머신·떡갈비·젤리 케이스·커피 필터·쿠폰 행사·과탄산소다(더운 날 '탄산') 등 — '할인'은 X: 떡볶이 64%할인)
WX_FILL = ("휴지", "물티슈", "세제", "생수", "라면", "햇반", "칫솔", "샴푸", "섬유유연제", "김")  # 일요일 DM: 날씨 키워드가 10개 안 되면 생필품·식품으로(쿠팡 전략 생필품·식품 70)
LOG_DENY = ("써봤", "써보니", "사용해보니", "제가 직접", "내돈내산", "우리 집")  # 운영 일지 금지어 — 지어낸 경험담 X(공정위 추천·보증 심사지침 2026.6), 들어가면 안 올림
DAILY_DIR = "docs/daily"  # #일상 사진(사이트 주소로 Threads에 — 봇 토큰 든 텔레그램 파일 주소는 안 씀)


def weather(seen):
    """서울 날씨 [오늘, 내일 … 7일 뒤] — Open-Meteo 예보(최저·최고·강수확률·최저습도) + 대기질(초미세먼지 하루 평균), 하루 1번 seen 캐시.
    예보를 못 받으면 None(날씨 글·간식 날씨 키워드·가점 X, 딜 글은 그대로 — 1시간 뒤 다시 받아 봄). 대기질만 실패면 pm = None."""
    key = time.strftime("wx_%Y%m%d", time.gmtime(time.time() + 9 * 3600))
    if key not in seen or not seen[key]["w"] and time.time() - seen[key]["t"] >= 3600:  # 못 받았으면 1시간 뒤 다시(0시 첫 실패 하나로 하루 종일 X)
        q, pm = f"latitude={WEATHER_LAT}&longitude={WEATHER_LON}&timezone=Asia%2FSeoul", {}
        try:
            d = json.loads(http(f"https://api.open-meteo.com/v1/forecast?{q}&forecast_days=8&daily=temperature_2m_min,temperature_2m_max,"
                                "precipitation_probability_max,relative_humidity_2m_min"))["daily"]
            try:
                a = json.loads(http(f"https://air-quality-api.open-meteo.com/v1/air-quality?{q}&forecast_days=7&hourly=pm2_5"))["hourly"]
                for t, v in zip(a["time"], a["pm2_5"]):
                    if v is not None:
                        pm.setdefault(t[:10], []).append(v)
            except Exception as e:
                print("weather pm", repr(e))
            seen[key] = {"t": time.time(), "w": [{"date": dt, "tmin": round(lo), "tmax": round(hi), "rain": pr or 0, "hum": 100 if hu is None else hu,
                                                  "pm": round(sum(pm[dt]) / len(pm[dt])) if pm.get(dt) else None}
                                                 for dt, lo, hi, pr, hu in zip(d["time"], d["temperature_2m_min"], d["temperature_2m_max"],
                                                                               d["precipitation_probability_max"], d["relative_humidity_2m_min"]) if lo is not None and hi is not None]}
        except Exception as e:
            print("weather", repr(e))
            seen[key] = {"t": time.time(), "w": []}
    return seen[key]["w"] or None


def wx_rules(w):
    return [r for r in WEATHER_RULES if r[0](w)]


def wx_words(seen, snack=False):
    """오늘 날씨에 맞는 아이템(snack이면 간식) 키워드. 날씨 없으면 []."""
    ws = weather(seen)
    return [k for r in wx_rules(ws[0]) for k in r[3 if snack else 2]] if ws else []


def wx_hit(name, words):  # 띄어쓰기는 키워드에 띄어 쓴 자리만 무시 — 제목 띄어쓰기를 다 지우면 '소고기 모듬'이 '기모'에 걸림
    return any(re.search(re.escape(w).replace(r"\ ", r"\s*"), name or "", re.I) for w in words)


def wx_bonus(seen):
    """딜 제목 -> 날씨 가점(오늘 아이템·간식 키워드에 맞으면 WEATHER_BONUS). 0이면 날씨도 안 받음."""
    kw = wx_words(seen) + wx_words(seen, True) if WEATHER_BONUS else []
    return lambda title: WEATHER_BONUS * wx_hit(title, kw) if kw else 0


def wx_line(w):
    """'오늘 서울 13~22도, 일교차 9도' + 비·건조·초미세먼지 해당되면 덧붙임."""
    return (f"오늘 서울 {w['tmin']}~{w['tmax']}도, 일교차 {w['tmax'] - w['tmin']}도" + (f" · 비 올 확률 {w['rain']}%" if w["rain"] >= 60 else "")
            + (f" · 습도 {w['hum']}%" if w["hum"] <= 35 else "") + (f" · 초미세먼지 {w['pm']}㎍" if (w["pm"] or 0) >= 36 else ""))


def wx_deals(seen, words, n=3, deny=None):
    """최근 3일 딜 중 제목(이름)에 words가 든 것 최대 n개: 3사 먼저 · 🔥 먼저 · 최근 먼저, 같은 이름 1번.
    커뮤니티·진우 딜 = posts.json(링크 = 제휴 링크, 아니면 사이트 딜 페이지), 토스 = 품절 지켜보기 기록(sold_)의 API 상품 — 지금 가격·품절을 다시 봄(게시 시점 가격)."""
    if not words:
        return []
    now, posts, out = time.time(), load(POSTS, []), []
    since = time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 9 * 3600 - 3 * 86400))
    today = time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600))  # 오늘 채널에 나간 딜은 X(10/24 진우 1주 ③ — 15:43 간식 글에 14:32 그래놀라·11:43 콘푸로스트가 또)
    ok = lambda name: wx_hit(name, words) and not (deny and re.search(deny, name))
    for i, p in enumerate(posts):
        if p["t"] < since or p["t"][:10] == today or p["text"].startswith("📋") or p.get("shelf") or is_toss(p.get("url"), p["text"]):  # 사이트 진열 X · 토스는 아래에서(지금 가격)
            continue
        title = title_of(p["text"])
        name, won = re.sub(r"\s*\((?=[^()]*(?:\d|무료|무배))[^()]*(?:원|/|무료|무배|배송)[^()]*\)\s*$", "", parse(title)[1]), price_won(title)  # '(21,920/무료)'·'(무료)' 같은 가격·배송 괄호만 이름에서 빼고 가격으로('(30개)'·'(1+1)'은 그대로)
        if ok(name):
            out.append({"n": name, "p": f"{won:,}원" if won else "", "u": p["url"] if aff(p.get("url")) else None, "i": i,
                        "hot": not th_weak(p["text"]) and not th_steady(p["text"]), "steady": th_steady(p["text"]) and not th_weak(p["text"]), "top3": bool(shop_of(p)), "t": kst_ts(p["t"])})
    cand = {}
    for k, v in seen.items():
        if HAS_TOSS and k.startswith("sold_") and isinstance(v, dict) and now - v.get("t", 0) < 3 * 86400:
            for link, x in zip([v.get("url")] if v.get("k") == "ev" else [r[1] for r in v.get("rows", [])], v.get("it", [])):
                if not x[4] and link and ok(x[1]) and time.strftime("%Y-%m-%d", time.gmtime(v["t"] + 9 * 3600)) != today:
                    cand[x[0]] = {"n": x[1], "u": link, "hot": True, "top3": True, "t": v["t"], "toss": 1}
    try:
        got = cand and {x["tacaItemId"]: x for x in toss("/products/detail?tacaItemIds=" + ",".join(map(str, list(cand)[:30])))["items"]}
        out += [{**c, "p": f"{got[i]['displayPrice']:,}원"} for i, c in cand.items() if i in got and not got[i].get("isSoldOut")]
    except Exception as e:  # 토스 API가 안 되면 토스 딜만 빼고
        print("wx toss", repr(e))
    picked, names = [], set()
    for c in sorted(out, key=lambda c: (not c["top3"], not c["hot"], not c.get("steady"), -c["t"])):  # 🔥 -> 👍 -> 🛒
        k = re.sub(r"\W", "", c["n"])[:20]
        if k not in names:
            names.add(k)
            picked.append(c)
    return picked[:n]


def wx_render(items, ref, html_text):
    """딜 줄(🔥/🛒 이름 가격 + 링크) -> (머리 대가성 문구, 줄들, 꼬리). 대가성 문구 = 링크 몰마다 맨 앞, 토스가 있으면 꼬리에 게시 시점 줄. 몰 이름·비교 없음.
    Threads = 텔레그램 버튼과 같은 링크(10/19 진우 '직접 링크로' — TH_LINK_MAX보다 긴 링크프라이스 주소만 사이트 딜 페이지), 토스 API 상품은 공유 링크 그대로."""
    links = [c["u"] if c["u"] and (html_text or c.get("toss") or len(c["u"]) <= TH_LINK_MAX) else f"{SITE}p/{c['i']}.html?ref={ref}" for c in items]
    notes = list(dict.fromkeys(n for n in (aff_note(c["u"] or "") for c in items) if n))
    rows = [f"{'🔥' if c['hot'] else '👍' if c.get('steady') else '🛒'} " + (f'<a href="{esc(u)}">{esc(clip(c["n"], 40))}</a>' + (f" {esc(c['p'])}" if c["p"] else "") if html_text else f"{clip(c['n'], 30)} {c['p']}".rstrip() + f"\n👉 {u}")
            for c, u in zip(items, links)]
    tail = f"\n\n{toss_when()}" if TOSS_NO_CMP and any(c.get("toss") for c in items) else ""
    return "\n".join(f"<i>{n}</i>" if html_text else n for n in notes) + ("\n\n" if notes else ""), rows, tail, links


def due(at, name, seen):
    """at(KST (시, 분))이 지났고 WX_LATE 안이고 오늘 아직이면 오늘 키, 아니면 None."""
    kst = time.gmtime(time.time() + 9 * 3600)
    k = time.strftime(name + "_%Y%m%d", kst)
    return k if at and k not in seen and 0 <= (kst.tm_hour * 60 + kst.tm_min - at[0] * 60 - at[1]) * 60 < WX_LATE else None


def wx_post(seen, key, head, items, alone, kind, lo=1):
    """채널(HTML) + Threads(글) 묶음 글 1개: head = 첫 줄(굵게, {n} = 딜 수), items 없으면 alone(날씨 + 질문, 링크 X). 시간당 상한·묶음 간격(busy) 같이 셈.
    Threads 480자를 넘으면 뒤 딜부터 빼고(lo개까지), 그래도 넘으면 alone(없으면 Threads X)."""
    if busy(seen):
        return
    tag, rows, tail, links = wx_render(items, "tg", True)
    text = tag + f"<b>{esc(head.format(n=len(items)))}</b>\n\n" + "\n".join(rows) + tail if items else esc(alone)
    if not tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True}, text=text):
        return
    seen[key] = time.time()
    bundled(seen)
    items = items if kind == "wx" else [c for c in items if aff_note(c["u"] or "")]  # 10/19 밤 진우 'Threads는 수수료 딜만'(날씨 글은 그대로)
    if E.get("THREADS_TOKEN") and not items and not alone:
        print(f"threads skip (수수료 링크 아님) {kind} 묶음 | 항목 0개")
    for n in range(len(items), min(lo, len(items)) - 1, -1) if E.get("THREADS_TOKEN") and items else ():  # Threads 500자(링크 미리보기는 글자를 안 자름) — 넘으면 뒤 딜부터 뺌
        tag, rows, tail, links = wx_render(items[:n], "th", False)
        th = tag + f"{head.format(n=n)}\n\n" + "\n".join(rows) + tail
        if len(th) <= 480:
            return th_bundle(seen, kind, th, links[0])
    if E.get("THREADS_TOKEN") and alone:
        th_bundle(seen, kind, alone)


def weather_post(seen):
    """아침 7:30 '☁️ 오늘 서울 13~22도, 일교차 9도 — 이런 날 필요한 것' + 키워드 맞는 최근 3일 딜 최대 3개(채널 + Threads). 맞는 딜 0개면 날씨 + 질문 한 줄."""
    key = due(WEATHER_HOUR, "wxpost", seen)
    ws = key and weather(seen)
    if not key or not ws:
        if key:
            seen[key] = time.time()
            print("weather post: 날씨 못 받음 -> 오늘 건너뜀")
        return
    rules = wx_rules(ws[0])
    wx_post(seen, key, f"☁️ {wx_line(ws[0])} — 이런 날 필요한 것", wx_deals(seen, [k for r in rules for k in r[2]]),
            f"☁️ {wx_line(ws[0])}\n{rules[0][4] if rules else '오늘은 뭐 챙기셨어요?'}", "wx")


def cal_text(today):
    """'🗓 쇼핑 달력' 글(사실만 — 날짜·몰·행사·D-day, 과장·추천 말 X · 링크 = 우리 사이트 기획전 모음뿐 = 대가성 문구 X) -> (글, 서명 = 행사 id·이름·날짜가 바뀌면 달라짐) / 앞으로 CAL_DAYS일 행사 없음 = (None, None)."""
    lim = time.strftime("%Y-%m-%d", time.gmtime(kst_ts(today + " 00:00") + 9 * 3600 + CAL_DAYS * 86400))
    try:  # /events/에 보이는 행사만(promo_shown — 수수료 길이 없어 숨긴 행사를 글이 소개하지 않게 · 지난 빌드 쪽, 없으면 글 X)
        shown = set(re.findall(r'<article class="pv" id="([a-z0-9-]+)"', open("docs/events/index.html", encoding="utf-8").read()))
    except OSError:
        shown = set()
    rows = [(p, st, first) for p, st, first in promo_list(today) if st != "past" and (first or today) <= lim and p["id"] in shown][:5]
    if not rows:
        return None, None
    md = lambda d: f"{int(d[5:7])}/{int(d[8:10])}"
    span = lambda a, b: f"{md(a)}~{md(b)}" if a and b else f"~{md(b)}" if b else f"{md(a)}~" if a else ""
    def line(p, st, first):
        pre = p.get("pre") or {}
        early = promo_pre(p, today)  # 사전 행사 전·중(끝난 사전 행사 X)
        dd = "오늘 마감" if st == "end" else f"D-{promo_days(today, first)}" if st == "soon" else "사전 행사 중" if early else "진행 중"
        return " ".join(x for x in ("·", span(p.get("start"), p.get("end")), str(p.get("mall_name") or p["mall"]).replace(" · ", "·"), p["name"].strip(),
                                     f"(사전 {span(pre.get('start'), pre.get('end'))})" if early else "", f"— {dd}") if x)
    sig = hashlib.md5(json.dumps([[p["id"], p["name"], p.get("start"), p.get("end"), p.get("pre")] for p, _, _ in rows], ensure_ascii=False).encode()).hexdigest()[:12]
    return f"🗓 앞으로 2주 쇼핑 달력 — 저장해 두면 편해요\n\n" + "\n".join(line(*r) for r in rows) + f"\n\n👉 기획전·특가 한눈에 {CAL_LINK}", sig


def cal_post(seen):
    """CAL_HOUR '🗓 쇼핑 달력' 정보 글 1번(Threads만 · TEXT + 링크 카드 = 사이트 /events/?ref=thi — og.png 로고 카드라 로고·카드 터치 = 바로 사이트, 본문 끝 줄에도 같은 주소 ·
    10/25 20시 진우 '정보글은 로고나 링크 터치하면 자동으로 유입되게' · 사진 글 X(링크 카드가 안 붙음)): promos.json(Cowork 매일 17:30)이 지난 글 뒤 바뀐 날만. 묶음 간격만 봄(일지처럼)."""
    key = due(CAL_HOUR, "calpost", seen)
    if not key or not E.get("THREADS_TOKEN") or busy(seen, cap=False):
        return
    text, sig = cal_text(time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600)))
    seen[key] = time.time()
    if not text or seen.get("calsig", {}).get("s") == sig:
        if seen.get("calsig"):  # seen 3일 정리에 안 지워지게(그대로인 날도 — 안 그러면 4일째 같은 글 다시)
            seen["calsig"]["t"] = time.time()
        print("cal post: 행사 목록 그대로·없음 -> 안 올림")
        return
    bundled(seen)
    seen["calsig"] = {"t": time.time(), "s": sig}  # 올리기 전에(실패 = th_retry가 올림 — 다음 날 같은 글 다시 X)
    r = th_bundle(seen, "info", text, CAL_LINK) or {}
    seen["calsig"]["id"] = r.get("id")
    print("cal post: 쇼핑 달력", text.count("\n· "), "줄 · 글", r.get("id"))


CUR_DIR, CUR_PREP, CUR_LATE, CUR_IMG_WAIT = "docs/cards/cur", 3 * 3600, 6 * 3600, 3600  # 큐레이션 사진(우리 서버 JPEG — 인스타·Threads는 공개 JPEG 주소가 필요) · 시각 3시간 전부터 준비 · 6시간 지나면 안 올림 · 사진이 사이트에 1시간 넘게 안 뜨면 글 + 링크 카드


def cur_events(seen=None):
    """events.json 큐레이션 항목(10/25 21시 진우 'Threads 등에서 계속 검색에 나오게 — 제품 한두 개로 더 많은 상품이 있다는 걸 여자들이 좋아할 만한 내용으로'):
    {"at","curation":true,"text","link"(사이트 c/ 쪽만),"topic"(Threads 주제 태그),"img":[쿠팡 사진 주소 …]} — 모양 틀린 항목 = 뺌(로그)."""
    out = []
    for e in ev_list(EVENTS):
        if not (isinstance(e, dict) and e.get("curation")):
            continue
        at, text, link, img = e.get("at"), e.get("text"), e.get("link"), e.get("img") or []
        try:
            ok = isinstance(at, str) and re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d", at) and kst_ts(at)  # 없는 날짜·시각(13월·25시) = X
        except ValueError:
            ok = False
        if not (ok and isinstance(text, str) and text.strip() and isinstance(link, str)
                and link.startswith(SITE + "c/") and not re.search(r"\s", link) and isinstance(img, list) and all(isinstance(u, str) for u in img)):
            print("curation 모양 틀림 -> 건너뜀", str(at)[:16])
            k = "alert_curbad_" + hashlib.md5(json.dumps(e, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:8]
            if seen is not None and k not in seen:  # Cowork에 알림 항목마다 1번(조용히 빠지지 않게 · 3시간마다 X)
                alert(seen, k, f"⚠️ 큐레이션 항목 모양이 틀려서 안 올려요: {str(at)[:16]} — at = 'YYYY-MM-DD HH:MM' · text · link = {SITE}c/… · img = 주소 목록")
            continue
        out.append({**e, "img": img[:10]})
    return out


def cur_img(u):
    """큐레이션 사진 1장 -> docs/cards/cur/<md5>.jpg — 자르기·크기 조정만(글자·합성 X): 비율이 인스타 범위(4:5~1.91:1) 밖이면 가운데만 잘라 그 범위로, 긴 변 1080 넘으면 줄이고
    짧은 변 320 밑이면 키움 · 투명 배경 = 흰색 · 쿠팡 사진 주소만(사이트 img_of와 같은 허용 목록) · 못 받으면 None."""
    try:
        host = urllib.parse.urlsplit(u).netloc.lower()
        if not (u.startswith("https://") and (host == "coupang.com" or host.endswith((".coupang.com", ".coupangcdn.com")))):
            return None
        f = f"{CUR_DIR}/{hashlib.md5(u.encode()).hexdigest()[:12]}.jpg"
        if os.path.exists(f):
            return f
        from io import BytesIO
        from PIL import Image
        im = Image.open(BytesIO(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=8).read(8_000_000)))
        im.load()
        if im.mode in ("RGBA", "LA", "P") or "transparency" in im.info:  # 투명 = 흰 바탕(검게 X)
            rgba = im.convert("RGBA")
            bg = Image.new("RGB", rgba.size, "white")
            bg.paste(rgba, mask=rgba.split()[3])
            im = bg
        im = im.convert("RGB")
        r = im.width / im.height
        if r > 1.91:  # 너무 넓음 = 가운데 1.91:1
            w = int(im.height * 1.91)
            im = im.crop(((im.width - w) // 2, 0, (im.width - w) // 2 + w, im.height))
        elif r < 0.8:  # 너무 높음 = 가운데 4:5
            h = int(im.width / 0.8)
            im = im.crop((0, (im.height - h) // 2, im.width, (im.height - h) // 2 + h))
        k = min(1080 / max(im.size), 1) if max(im.size) > 1080 else max(320 / min(im.size), 1)
        im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS) if k != 1 else im
        os.makedirs(CUR_DIR, exist_ok=True)
        im.save(f, "JPEG", quality=88)
        return f
    except Exception as e:
        print("curation 사진 못 받음", clip(u, 60), type(e).__name__)
        return None


def cur_prune(now):
    """docs/cards/cur 사진 = 지금 events 큐레이션(3일 안) 사진만 남김(저장소 크기 — 인스타·Threads는 게시 때 이미 가져감)."""
    keep = {hashlib.md5(u.encode()).hexdigest()[:12] + ".jpg" for e in cur_events() if kst_ts(e["at"]) > now - 3 * 86400 for u in e["img"]}
    for f in os.listdir(CUR_DIR) if os.path.isdir(CUR_DIR) else []:
        if f.endswith(".jpg") and f not in keep:
            os.remove(f"{CUR_DIR}/{f}")


def cur_ig(seen, st, e, key, live, now):
    """큐레이션 인스타(10/25 Cowork ② — 사진 넘기기 + 캡션 '프로필 링크 → {topic}'): 사이트에 뜬 사진(자르기·크기만, 글자 X) 1장 = 사진 글 · 2장↑ = 조각 -> ig_carousel이 묶음(캡션)
    -> ig_publish 발행(하루 상한 ig_day_max = 카드 칸 + 1 여유 안) · 사진 없음 = 안 올림(인스타는 사진 필요) · 만들기 실패 = 다시 X(10/23 진우 — ig_fail). st ig = 사진 수(0 = 안 올림, None = 실패)."""
    st["ig"] = 0
    if not live:
        print("curation 인스타: 사진 없음 -> 안 올림", e["at"])
        return
    if ig_room(seen, now) < 1:  # 하루 상한 = 딜 카드 칸 먼저(그날 남은 칸 몫을 남김)
        print("curation 인스타: 오늘 상한(딜 카드 칸 먼저) -> 안 올림", e["at"])
        return
    tail = f"\n\n🛒 프로필 링크 → {str(e.get('topic') or '').strip() or '핫딜픽'}\n\n상품 사진: 판매 페이지(쿠팡)"
    cap, auth, uid = clip(e["text"].strip(), 2200 - len(tail) - 1) + tail, {"Authorization": "Bearer " + E["IG_TOKEN"]}, E["IG_USER_ID"]
    try:
        if len(live) == 1:
            seen["igc_" + json.loads(http(f"{IG}/{uid}/media", {"image_url": live[0], "caption": cap}, auth, "POST"))["id"]] = {"t": now, "kind": "cur"}
        else:
            seen["igk_" + key] = {"t": now, "kind": "cur", "cap": cap, "kids": [json.loads(http(f"{IG}/{uid}/media", {"image_url": u, "is_carousel_item": True}, auth, "POST"))["id"] for u in live]}
        st["ig"] = len(live)
        print("curation 인스타", e["at"], f"사진 {len(live)}장 컨테이너")
    except Exception as x:
        st["ig"] = None
        ig_fail(seen, now, f"큐레이션 {e['at']} 컨테이너 {ig_err(x)}")


def curation(seen):
    """큐레이션 글(events curation): 시각이 되면 텔레그램 채널 = 본문 + '🛍 더 보기' 버튼(같은 쪽, ref=tgc) · Threads = 사진(우리 서버 JPEG) 1장 IMAGE·2장↑ CAROUSEL, 본문 끝 링크(ref=thc), topic_tag = topic
    / 사진 없음 = TEXT + 링크 카드(정보 글처럼) · 6시간 지나면 X. 사진은 시각 3시간 전부터 준비(이 실행 커밋 -> 사이트에 뜨면(HEAD) 게시 · 준비 뒤 1시간 넘게 안 뜨면 뜬 사진만, 없으면 글 + 링크 카드 ·
    못 받은 사진 = 1시간 뒤 다시). 우리 사이트 쪽 링크 = 대가성 문구 X(상품 링크 규칙은 그대로) · 묶음 간격만 봄(딜 글 수·간격 그대로) · Threads 실패 = 다음 실행에 다시(3번째 = 알림·그만).
    인스타(IG_AUTO) = 같은 사진 넘기기 + 캡션 '프로필 링크 → topic'(cur_ig — 사진 없음 = 안 올림, 실패 = 다시 X)."""
    now, tok = time.time(), E.get("THREADS_TOKEN")
    cur_prune(now)
    for e in cur_events(seen):
        t0 = kst_ts(e["at"])
        if not t0 - CUR_PREP <= now <= t0 + CUR_LATE:
            continue
        key = f"cur_{e['at'][:10]}_{e['at'][11:13]}{e['at'][14:16]}"  # 시각 = 열쇠(글을 고쳐도 다시 X — 같은 시각 큐레이션은 1개)
        st = seen.setdefault(key, {"t": now})
        st["t"], files = now, []
        ig = IG_AUTO and E.get("IG_TOKEN") and E.get("IG_USER_ID") and "ig" not in st and seen.get("ig_hold", 0) <= now  # 인스타 = 큐레이션 사진 넘기기(cur_ig)
        if "th" not in st or ig:
            bad = st.setdefault("bad", {})
            for u in e["img"]:
                f = cur_img(u) if now - bad.get(u, 0) >= 3600 else None  # 못 받은 사진 = 1시간 뒤 다시(실행마다 X)
                if f:
                    files.append(f)
                    bad.pop(u, None)
                    st.setdefault("pt", now)  # 사진 처음 준비된 시각(사이트에 뜨기 기다림 기준)
                elif u not in bad or now - bad[u] >= 3600:
                    bad[u] = now
        if now < t0:  # 사진만 미리(다음 실행 전에 사이트에 뜨게)
            continue
        body = e["text"].strip()
        if "tg" not in st:
            m = tg("sendMessage", chat_id=CHANNEL, text=esc(clip(body, 2000)), parse_mode="HTML", link_preview_options={"is_disabled": True},  # 4096자 한도(이모지 = 2자로 셈)
                   reply_markup={"inline_keyboard": [[{"text": "🛍 더 보기", "url": re.sub(r"([?&]ref=)thc\b", r"\g<1>tgc", e["link"])}]]})
            if m:
                st["tg"] = m["message_id"]
        th = tok and "th" not in st and not busy(seen, cap=False)
        if not (th or ig):
            continue
        urls, live = [SITE + f[len("docs/"):] for f in files], []
        for u in urls:
            try:
                http(u, method="HEAD")
                live.append(u)
            except Exception:
                pass
        if len(live) < len(urls) and now < max(t0, st.get("pt", now)) + CUR_IMG_WAIT:
            continue  # 아직 사이트에 다 안 뜸 = 다음 실행에(준비 뒤 1시간까지)
        if ig:
            cur_ig(seen, st, e, key, live, now)
        if not th:
            continue
        topic = re.sub(r"[.&]", "", str(e.get("topic") or "")).strip()[:50] or th_topic(seen)  # Threads 주제 태그: 마침표·& X · 50자
        lim = n = 500 - th_len(e["link"]) - 2
        cut = th_fit(body, n)
        while th_len(cut) > lim and n > 40:  # Threads 글자 수 = 이모지 UTF-8 바이트(th_len) — th_fit은 글자 수라 넘치면 자를 길이만 줄임(한도는 그대로)
            n -= 10
            cut = th_fit(body, n)
        post = f"{cut}\n\n{e['link']}"
        try:
            me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
            r = th_img(tok, me, post, live[0], topic) if len(live) == 1 else th_carousel(tok, me, post, live, topic) if live else None
            ph = len(live) if r else 0
            r = r or th_text(tok, me, post, e["link"], topic)
        except Exception as x:
            st["n"] = st.get("n", 0) + 1
            print("curation threads 실패", st["n"], err_brief(x))
            if st["n"] >= 3:
                st["th"] = None
                alert(seen, "alert_" + key, f"⚠️ 큐레이션 글 Threads 3번 실패: {err_brief(x)}\n{e['at']} {clip(body, 60)}")
            continue
        st["th"], st["ph"] = (r or {}).get("id"), ph
        bundled(seen)
        print("curation:", e["at"], "Threads", st["th"], f"사진 {ph}장" if ph else "글 + 링크 카드", "· 채널", st.get("tg"))


DPOST_AT, DPOST_PREP, DPOST_N, DPOST_MINPH, DPOST_DIR = (20, 40), 30 * 60, 5, 3, "docs/cards/drop"  # 10/25 23시 진우 D: 📉 하루 1번 20:40(진우 예약 20시대·22:03 미리보기와 따로 — 묶음 간격 busy) · 30분 전 카드 준비(커밋 -> 사이트) · 상품 5개 · 사진 3개↑일 때만
DPOST_REPLY = "📉 가격 내려간 상품 전체는 여기서 볼 수 있어요 👇\n\n🔔 올라오자마자 알려드릴까요?\n텔레그램 👉 t.me/hotdeal_pick"  # 사이트 주소 = 링크 카드만(?ref=thd)


def drop_post(seen):
    """📉 가격 내려간 상품 하루 1번(10/25 23시 진우 D): 사이트 📉 칸과 같은 기준(build_site.drops — 같은 구성·첫 기록 대비·확인 24시간 안) 중 수수료 링크·3일 안 안 쓴 상품을
    내림 큰 순으로 사진(쿠팡 img_of — ig_photo) 있는 것만 DPOST_N개 · DPOST_MINPH개 미만이면 그날 X. DPOST_AT 30분 전 카드(우리 서버 JPEG — 상품마다 기록가 취소선 → 지금가·▼N%·동물 + 표지)를
    docs/cards/drop/에 만들고(이 실행 커밋 -> 사이트) DPOST_AT 뒤 사이트에 뜨면(HEAD) Threads = 캐러셀(상품 장) + 본문(대가성 문구 맨 위·귀여운 말투·'이름 · 기록가 → 지금가 (▼N%)'·기준 줄)
    + 댓글(사이트 c/drop/ 링크 카드 ?ref=thd · 텔레그램) / 인스타 = 표지 + 상품 장 넘기기(캡션 '프로필 링크 → 가격 내려간 상품' — 하루 상한·2시간 간격·쉼은 ig_publish).
    'N원 쌈'·'최저가' X · 쿠폰·와우 가격은 글자 그대로. 1시간 넘게 안 뜨면 그날 X. Threads 실패 = 다음 실행에 다시(3번째 = 알림·그만)."""
    import cards
    now = time.time()
    kst = time.gmtime(now + 9 * 3600)
    day, sec, at = time.strftime("%Y-%m-%d", kst), kst.tm_hour * 3600 + kst.tm_min * 60, DPOST_AT[0] * 3600 + DPOST_AT[1] * 60
    key, link = "droppost_" + day.replace("-", ""), f"{c_url('drop')}?ref=thd"
    ends = ("\n👇 전체는 댓글에 있어요", f"\n\n🛍 전체 보기 {link}\n🔔 텔레그램 알림 t.me/hotdeal_pick")  # 댓글 됨 / 댓글 못 다는 토큰 = 본문에 주소
    st = seen.get(key)
    if st is None:
        if not at - DPOST_PREP <= sec < at + WX_LATE:
            return
        for f in os.listdir(DPOST_DIR) if os.path.isdir(DPOST_DIR) else []:  # 지난 날 카드 = 지움(인스타·Threads는 게시 때 가져감)
            if f[:10] != day:
                os.remove(f"{DPOST_DIR}/{f}")
        posts = load(POSTS, [])
        days = sorted({p["t"][:10] for p in posts if not p["text"].startswith("📋")}, reverse=True)
        cut = time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600 - 3 * 86400))
        mem = {u: d for u, d in seen.get("dropu", {}).get("m", {}).items() if d > cut}  # 3일 안 쓴 상품(날짜로 — seen 3일 지움과 따로)
        picks = []
        for i, p, sh, base, nw, pct, rec, chk in drops(posts, shelf_items(posts, days), now):
            if len(picks) < DPOST_N and aff_note(p["url"]) and aff_note(p["url"]) != OY_NOTE and p["url"] not in mem:  # Threads = 수수료 딜만(10/19 진우)
                f = ig_photo(p, "ig_photos", seen)[0]
                if f:
                    picks.append((p, base, nw, pct, rec, f))
        seen[key] = st = {"t": now, "n": len(picks)}
        if len(picks) < DPOST_MINPH:
            print(f"drop post: 사진 있는 상품 {len(picks)}개 -> 오늘 X")
            return
        lab = lambda p: (re.match(r"[\d,]+원\s*(\S.*)", p.get("now") or "") or ["", ""])[1]  # 쿠폰·와우 조건 = 그대로(사이트 drop_section과 같음)
        names = pv_names([title_of(p["text"]) for p, *_ in picks])
        its = [{"name": parse(title_of(p["text"]))[1], "short": nm, "price": f"{nw:,}원" + (f" {lab(p)}" if lab(p) else ""), "photo": f, "src": "coupang", "was": base, "pct": pct,
                "basis": f"같은 구성 · {rec} 기록 대비", "when": f"{p.get('chk') or md_of(p['chkt'])} 확인"} for (p, base, nw, pct, rec, f), nm in zip(picks, names)]
        files = []
        for n, it in enumerate(its, 1):
            try:
                files.append(cards.ig_photo_card(it, n, f"{DPOST_DIR}/{day}_{n}.jpg"))
            except Exception as x:
                print("drop card", n, type(x).__name__)
        if len(files) < DPOST_MINPH:
            print(f"drop post: 카드 {len(files)}장 -> 오늘 X")
            return
        recs, chks = ("·".join(dict.fromkeys(x)) for x in zip(*[(r[4], md_of(r[0]["chkt"])) for r in picks]))
        k = datetime(int(day[:4]), int(day[5:7]), int(day[8:10]))
        design = ig_design(day, 1)
        cover = cards.ig_cover(design, [{**it, "price": it["price"].split(" ")[0]} for it in its], f"{k.month}월 {k.day}일 {'월화수목금토일'[k.weekday()]}요일" if design in "AP" else f"{k.month}.{k.day} {'월화수목금토일'[k.weekday()]}",
                               f"📉 가격 내려간\n상품 {len(its)}개", f"{DPOST_DIR}/{day}_0.jpg", sub="같은 구성 · 우리 기록 대비", note=f"제휴 링크(수수료) · {chks} 확인 가격")
        rows = [f"{it['short']} · {it['was']:,}원 → {it['price']} (▼{it['pct']}%)" for it in its]
        notes = aff_notes(p["url"] for p, *_ in picks)
        th = lambda k: f"{notes}\n\n📉 오늘 가격 내려간 거 모아왔어요 🐻\n\n" + "\n".join(rows[:k]) + f"\n\n같은 구성 · {recs} 기록 대비 · {chks} 확인 가격"
        k = next((k for k in range(len(rows), 0, -1) if th_len(th(k) + ends[1]) <= 500), 1)  # Threads 500자(th_len) — 긴 끝 줄 몫까지
        st.update(files=files, cover=cover, urls=[p["url"] for p, *_ in picks], tags=ig_tags([p for p, *_ in picks], kst.tm_mday + 2), th=th(k),
                  igcap=f"{notes}\n\n📉 가격 내려간 상품 {len(its)}개\n\n" + "\n".join(rows) + f"\n\n같은 구성 · {recs} 기록 대비 · {chks} 확인 가격(쿠폰·와우 조건 그대로)\n\n🛒 프로필 링크 → 가격 내려간 상품\n\n상품 사진: 판매 페이지(쿠팡)")
        seen["dropu"] = {"t": now, "m": {**mem, **{u: day for u in st["urls"]}}}
        print("drop post 준비", len(files), "장 ·", " / ".join(clip(it["short"], 12) for it in its))
        return
    if not st.get("files") or st.get("done") or sec < at:
        return
    urls = [SITE + f[len("docs/"):] for f in [st["cover"]] + st["files"]]
    try:
        for u in urls:
            http(u, method="HEAD")
    except Exception:
        if now - st["t"] > CUR_IMG_WAIT + DPOST_PREP:
            st["done"] = "사이트에 안 뜸"
            print("drop post: 카드가 사이트에 안 뜸 -> 오늘 X")
        return
    tok = E.get("THREADS_TOKEN")
    if IG_AUTO and not IG_H and E.get("IG_TOKEN") and E.get("IG_USER_ID") and "ig" not in st and seen.get("ig_hold", 0) <= now:  # H(10/26 M): 📉 = 22시 스토리(ig_cards — 표지)
        st["ig"] = 0
        if ig_room(seen, now) < 1:  # 하루 상한 = 딜 카드 칸 먼저
            print("drop post 인스타: 오늘 상한(딜 카드 칸 먼저) -> 안 올림")
        else:
            auth = {"Authorization": "Bearer " + E["IG_TOKEN"]}
            try:
                seen["igk_drop_" + day] = {"t": now, "kind": "drop", "cap": clip(st["igcap"], 2200 - len(st["tags"]) - 3) + "\n\n" + st["tags"],
                                           "kids": [json.loads(http(f"{IG}/{E['IG_USER_ID']}/media", {"image_url": u, "is_carousel_item": True}, auth, "POST"))["id"] for u in urls]}
                st["ig"] = len(urls)
            except Exception as x:
                st["ig"] = None
                ig_fail(seen, now, f"가격 내려간 상품 컨테이너 {ig_err(x)}")
    if not tok:
        st["done"] = 1
        return
    if busy(seen, cap=False):  # 묶음 간격 -> 다음 실행에
        return
    can = TH_REPLY and th_reply_ok(seen)
    text = st["th"] + ends[0 if can else 1]
    try:
        me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
        r = th_carousel(tok, me, text, urls[1:], th_topic(seen)) or th_text(tok, me, text, None if can else link, th_topic(seen))
    except Exception as x:
        st["n_th"] = st.get("n_th", 0) + 1
        print("drop post threads 실패", st["n_th"], err_brief(x))
        if st["n_th"] >= 3:
            st["done"] = "Threads 3번 실패"
            alert(seen, "alert_" + key, f"⚠️ 📉 가격 내려간 상품 글 Threads 3번 실패: {err_brief(x)}")
        return
    st["post"], st["done"] = r["id"], 1
    bundled(seen)
    print("drop post: Threads", r["id"], len(urls) - 1, "장")
    if can:
        try:
            th_reply(tok, r["id"], DPOST_REPLY, link)
        except Exception as e:  # 본문은 이미 나감('👇 댓글에') -> 관리자에게 바로(붙여넣기용)
            print("drop post 댓글 실패", err_brief(e))
            seen["threply"] = {"t": time.time(), "ok": 0, "err": (getattr(e, "body", "") or repr(e))[:300]}
            tg("sendMessage", chat_id=ADMIN, text=f"⚠️ 📉 가격 내려간 상품 댓글 실패({err_brief(e)}) — 아래 글을 Threads 앱에서 그 글 댓글로 붙여넣어 줘(링크 {link})\n\n{DPOST_REPLY}")

IG_H = True  # 10/26 H·L·M(진우 '노출이 너무 적고 보고 싶을 수준 X' · '광고처럼 보여, 소통하고 싶어' · '꾸준하게 제품도 시간마다'): 피드 = IG_FEED 4칸 형식 돌림 · 시간대·하루 카드·📉 = 스토리 · False = 예전(칸 카드 피드)
IG_FEED = {"11": (11, 0), "14": (14, 0), "17": (17, 0), "20": (20, 0)}  # M-1 피드 4칸(3시간 간격 + 15~20분 무작위 지연) — 카드 이름 날짜_시(사이트 맨 위·c/칸 맨 위 번호 = 인스타 번호)
IG_CYCLE = (("theme", "guess", "one", "vs"), ("top", "ask", "one", "fun"), ("theme", "check", "one", "guess"))  # L·M 형식 3일 돌림 — 같은 형식 연달아 X(날 넘어서도) · 링크 미는 글(IG_LINKY) 하루 2개 · 질문 카드 그날 저녁 = 재미 질문
IG_LINKY = ("theme", "one", "top")  # 구매 링크 미는 형식(댓글 = 구매 링크 안내) — 나머지 = 소통(댓글로 답·정답·투표)
IG_STORY, IG_STORY_MAX = {9: 0, 12: 30, 15: 30, 18: 30, 22: 0}, 5  # M-1 스토리(시: 분) — 그 시간대 딜 카드(9 = 0~9시 …) · 22시 = 📉 표지(없으면 하루 카드) · 피드 수 X
IG_FEED_MAX, IGT_N, IGT_MIN, IG_REPEAT, IGF_PREP, IG_GUESS_AFTER = 4, 5, 3, 7, 20 * 60, 3 * 3600  # 하루 피드 4 · 테마 상품 5(3개↓ = 다른 형식) · 같은 상품 7일 X · 20분 전 카드(커밋 -> 사이트) · 가격 맞히기 정답 3시간 뒤
IGT_DIR, CARD_NAMES = "docs/cards/igt", "docs/cards/names.json"  # 피드 카드 · 카드 이름(사이트 '📸 {이름}'·c/칸 맨 위 번호·pid -> 테마 = 주간 저장 순위)
IGT_DAYS = (("자취·살림", ("home", "life")), ("뷰티", ("beauty", "women")), ("주방·세탁", ("kitchen", "laundry")), ("겨울템", ("heat",)), ("간식", ("snack",)), ("패션", ("fashion",)), ("생필품", ("life",)))  # 요일 테마(월~일, 시리즈처럼)
IGT_SEASON = (("겨울템", ("heat",)), ("제철 먹거리", ("season",)))  # 많이 본 5개(GoatCounter)가 없을 때 테마(10~2월 = 겨울템)
IGT_TAGS = {"자취·살림": "#자취템 #살림템 #생활꿀템", "뷰티": "#뷰티템 #스킨케어 #데일리뷰티", "주방·세탁": "#주방템 #살림꿀템 #세탁템", "겨울템": "#겨울템 #방한용품 #겨울필수템",
            "간식": "#간식추천 #탕비실간식 #간식템", "패션": "#데일리룩 #가성비패션 #겨울옷", "생필품": "#생필품 #쟁여템 #장보기", "제철 먹거리": "#제철음식 #집밥 #장보기"}
IGT_BAN = r"최저|역대|1위|최고|효과|효능|치료|완화|개선|보장|무조건|강추|미쳤|대박|광고|써보|써봤|써 보|써 봤|사봤|먹어보|발라보|제가 쓰|저도 쓰"  # 문구 금지(효능·단정·과장·써 본 척) — 걸리면 기본 문구
IG_CMT_HEADS = ("🛒 구매 링크 모아뒀어요", "🛍 살 수 있는 곳 정리해 뒀어요", "👀 구매 링크는 여기 모아뒀어요", "🧺 상품 링크 한곳에 모아뒀어요", "📌 구매 링크 정리해 뒀어요")  # I: 첫 줄 돌림(같은 댓글 반복 X)
IG_FUN_Q = (("붕어빵, 팥 vs 슈크림?", ("snack",)), ("겨울 아침, 이불 밖으로 나오는 데 몇 분 걸려요?", ("heat", "home")), ("귤은 한 번에 몇 개까지 먹어 봤어요?", ("season", "food")),
            ("핫팩은 붙이는 거 vs 흔드는 거?", ("heat",)), ("라면에 계란, 넣는다 vs 안 넣는다?", ("food", "snack")), ("샤워는 아침 vs 저녁?", ("beauty", "life")), ("수면양말 신고 잔다 vs 벗고 잔다?", ("fashion", "heat")))  # M-4 재미 질문(관련 제품 1개 작게)
IG_COPY = """인스타그램 '{kind}' 글 문구를 써 주세요. 핫딜픽이 친구한테 말하듯 1인칭·짧게·해요체. 상품(번호. 이름 · 가격 · 사실):
{rows}

{need}
- tags: 해시태그 3개('#'로 시작, 띄어쓰기 X, 글 내용에 맞게).
- 위 상품 정보에 없는 사실·효능, '최저가'·'역대급'·'1위' 같은 단정, 써 본 척(써 보니·제가 쓰는) X. 숫자는 위 정보에서만."""
IG_NEED = {"theme": "- title: 표지 제목 2줄('\\n'으로, 줄마다 14자 안팎 — 공감형, 예 '발 시린 사무실,\\n1만원대 온기템 5가지')\n- seo: 캡션 첫 줄(32자 안팎 — 검색 낱말 + ' | ' + 짧은 요약, 예 '사무실 발난로 추천 | 1만원대 온기템 5')\n- say: 1인칭 한 줄(35자 안팎)\n- q: 댓글 유도 질문 1줄(25자 안팎)",
           "one": "- open: 첫 문장 — 이 상품이 필요해지는 상황 공감(20자 안팎, 이모지 1개, 예 '퇴근하고 발이 꽁꽁 얼 때 🥶')\n- close: 끝 문장 — open을 받아 이 상품으로 마무리(30자 안팎, 이모지 1개, 예 '이제 발 꽁꽁은 그만, 책상 밑 미니 온풍기 🐻')\n- say: 1인칭 한 줄(35자 안팎)\n- q: 댓글 유도 질문 1줄(25자 안팎)",
           "vs": "- say: 1인칭 한 줄(35자 안팎 — 둘 다 괜찮아 보여서 고민, 같은 느낌)\n- q: 'A vs B' 고르게 하는 질문 1줄(25자 안팎)",
           "ask": "- title: 4개 중 고르게 하는 질문(2줄, '\\n'으로, 예 '겨울에 제일 먼저\\n꺼내는 건?')\n- say: 1인칭 한 줄(35자 안팎)",
           "check": "- title: 표지 제목 2줄('\\n'으로, 예 '전기요 사기 전\\n확인할 3가지')\n- say: 1인칭 한 줄(35자 안팎 — 정보만, 구매 권유 X)\n- q: 질문 1줄(25자 안팎)",
           "guess": "- say: 1인칭 한 줄(35자 안팎 — 가격은 말하지 않기)",
           "top": "- title: 표지 제목 2줄('\\n'으로, 예 '요즘 사이트에서\\n많이 본 5가지')\n- say: 1인칭 한 줄(35자 안팎)\n- q: 질문 1줄(25자 안팎)",
           "fun": "- say: 1인칭 한 줄(35자 안팎 — 재미 질문에 가볍게, 아래 상품을 살짝 곁들임)"}


def card_names_put(stem, **kv):
    """카드 이름 기록(docs/cards/names.json — 7일): {stem: {title, slug, cat, theme, kind, pid}} — 사이트 card_name·c/칸 맨 위·metrics 테마."""
    now = time.time()
    m = {k: v for k, v in load(CARD_NAMES, {}).items() if isinstance(v, dict) and v.get("t", now) > now - 7 * 86400}
    m[stem] = {**m.get(stem, {"t": now}), **kv}
    os.makedirs(os.path.dirname(CARD_NAMES), exist_ok=True)
    json.dump(m, open(CARD_NAMES, "w"), ensure_ascii=False)


def igt_item(seen, i, p, k=0):
    """피드 장 재료(판매 페이지 사진 있는 것만 — 없으면 None): 이름 · 가격(확인가 + 쿠폰·와우 조건 그대로) · 사실(✔ 줄 — 배송·반품·리뷰) · 확인할 점(⚠️) · 한 줄(💡)·단가(💰) · 용량 · 확인 시각."""
    f = ig_photo(p, "ig_photos", seen)[0]
    if not f:
        return None
    t = p["text"]
    _, name, price = parse(title_of(t))
    line = lambda e: (re.search(rf"^{e}\s*(.+)$", t, re.M) or [None, ""])[1].strip()
    check = re.sub(r"\s*\(\d{1,2}/\d{1,2}[^)]*\)\s*$", "", (re.search(r"확인할 점:\s*(.+)", t) or [None, ""])[1]).strip()  # '(10/24 4시 가격)' 꼬리 = 확인 시각 칸에
    size = " ".join(re.findall(rf"{TH_SZ}|{TH_CNT}", name))
    return {"i": i, "p": p, "photo": f, "src": "coupang", "k": k, "name": name, "price": p["now"] if p.get("now") and p.get("chk") else price.split("/")[0].strip(),
            "fact": line("✔"), "check": check, "tip": line("💡"), "unit": line("💰"), "size": size,
            "when": f"{p['chk']} 확인" if p.get("chk") else f"{int(p['t'][5:7])}/{int(p['t'][8:10])} {int(p['t'][11:13])}시"}


def igt_pool(seen, posts, cats, day, one=False):
    """진열(🔥 특가·👍 꾸준템) 쿠팡 수수료 상품(cats 품목 칸 — None = 전부) · 사진 · 7일 안 인스타에 안 쓴 것(seen igu) -> [(i, p)] 진열 순서.
    one = 그날 올린 🔥 쿠팡 딜(없으면 오늘 확인한 🔥 진열). 토스 = X(인스타 토스 = 토스 범위 답 전 X — 쿠팡만)."""
    cut = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600 - IG_REPEAT * 86400))
    used = {u for u, d in seen.get("igu", {}).get("m", {}).items() if d > cut}
    ok = lambda p: shop_of(p) == "coupang" and aff(p.get("url")) and img_of(p) and p["url"] not in used and cat_of(p) in CAT_META and (cats is None or cat_of(p) in cats)
    days = sorted({p["t"][:10] for p in posts if not p["text"].startswith("📋")}, reverse=True)
    it = shelf_items(posts, days)
    if one:
        md = f"{int(day[5:7])}/{int(day[8:10])} "
        return [(i, p) for i, p, sh in it if sh[0] == 0 and ok(p) and (p["t"][:10] == day or (p.get("chk") or "").startswith(md))]
    return [(i, p) for i, p, sh in it if sh[0] in (0, 1) and ok(p)]


def ig_copy(kind, label, its):
    """피드 문구(Claude 1번 — IG_NEED[kind] 칸 + tags) · 숫자는 상품 수·가격·가격대에서만 · 금지 말(IGT_BAN) X · 실패·안 맞음 = 칸마다 기본 문구."""
    n, ws = len(its), [w for it in its if (w := won(it["price"]))]
    base = {"title": {"theme": f"{label} 고민될 때,\n지금 살 만한 {n}가지", "ask": f"{label} 중에\n제일 먼저 챙기는 건?", "check": f"{label} 사기 전\n확인할 {n}가지", "top": f"요즘 사이트에서\n많이 본 {n}가지"}.get(kind, ""),
            "seo": f"{label} 추천 | 지금 살 만한 {n}가지", "say": "요즘 눈에 띄는 것만 골라 봤어요", "q": f"여러분은 {label} 뭐 쓰세요?",
            "open": f"{label} 하나 필요할 때 🤔", "close": f"그럴 땐 이거 하나면 돼요 🐻", "tags": IGT_TAGS.get(label, "#핫딜픽 #쟁여템 #쇼핑정보").split()[:3]}
    rows = "\n".join(f"{k}. {it['name']} · {it['price']} · {it['fact']}" for k, it in enumerate(its, 1))
    props = {k: {"type": "string"} for k in re.findall(r"^- (\w+):", IG_NEED[kind], re.M)} | {"tags": {"type": "array", "items": {"type": "string"}}}
    try:
        r = ai_json(IG_COPY.format(kind={"theme": "테마 넘기기", "one": "개별 상품 소개", "vs": "이거 vs 저거", "ask": "질문 카드", "check": "사기 전 체크리스트", "guess": "가격 맞히기", "top": "많이 본 5가지", "fun": "재미 질문 카드"}[kind],
                                    rows=rows, need=IG_NEED[kind]), props)
    except Exception as e:
        print("인스타 문구 기본으로", clip(repr(e), 80))
        return base
    nums = set(re.findall(r"\d+", rows)) | {str(n), "1", "2", "3", "4"} | {str(w // 10000) for w in ws} | {str(w // 1000) for w in ws}
    good = lambda s, z: isinstance(s, str) and s.strip() and len(s) <= z and not re.search(IGT_BAN, s) and set(re.findall(r"\d+", s)) <= nums and (kind != "guess" or not re.search(r"\d[\d,]*\s*원", s))
    out = dict(base)
    for k, z in (("seo", 40), ("say", 45), ("q", 30), ("open", 28), ("close", 40)):
        if good(r.get(k), z):
            out[k] = r[k].strip()
    t = str(r.get("title", "")).replace("\\n", "\n").strip()
    if good(t, 40) and t.count("\n") == 1 and all(len(x) <= 18 for x in t.split("\n")):
        out["title"] = t
    tags = [x for x in (r.get("tags") or []) if isinstance(x, str) and re.fullmatch(r"#[가-힣A-Za-z0-9_]{1,20}", x) and good(x, 21)][:3]  # 태그도 금지 말·숫자 검사
    out["tags"] = tags if len(tags) >= 2 else base["tags"]
    return out


def ig_cmt(seen, cat, n, slug):
    """I: 게시 직후 계정 본인 댓글 1개(인스타 댓글·캡션 주소는 안 눌림 -> 프로필 링크) — 첫 줄 게시물마다 돌림."""
    k = seen.setdefault("igcmt", {"t": 0, "n": 0})
    k.update(t=time.time(), n=k["n"] + 1)
    return (f"{IG_CMT_HEADS[k['n'] % len(IG_CMT_HEADS)]}\n프로필 링크 → {cat} {'1번' if n == 1 else f'1~{n}번'}\n{urllib.parse.urlsplit(SITE).netloc}/c/{slug}\n"
            "(인스타 댓글 주소는 눌리지 않아서 프로필 링크로 열어주세요 🙏)")


def ig_fmt(day_ord, hh):
    """그 칸 형식(IG_CYCLE — 날짜 순서 % 3)."""
    return IG_CYCLE[day_ord % len(IG_CYCLE)][list(IG_FEED).index(hh)]


def ig_ask_tally(seen, tok):
    """앞 질문 카드(seen igask — 3일) 댓글 집계: 1~4 중 가장 많은 번호 -> (번호, 이름, 댓글 수) · 댓글 0개·못 읽음 = None(지어내지 않음)."""
    a = seen.get("igask") or {}
    if not a.get("pid"):
        return None
    try:
        cs = json.loads(http(f"{IG}/{a['pid']}/comments?fields=text&limit=50", None, {"Authorization": f"Bearer {tok}"})).get("data") or []
    except Exception as e:
        print("ig 질문 댓글 못 읽음", err_brief(e))
        return None
    c = collections.Counter(int(m[1]) for x in cs if (m := re.search(r"(?<!\d)([1-4])(?!\d)", x.get("text") or "")))
    if not c:
        return None
    k, v = c.most_common(1)[0]
    return k, a["names"][k - 1] if k <= len(a["names"]) else "", sum(c.values())


def igf_make(seen, kind, stem, kst):
    """피드 칸 카드 만들기(그 시각 IGF_PREP 전부터 — 이 실행 커밋 -> 사이트). 형식(L·M):
    theme = 표지(사진 3장·공감 제목) + 상품 장 3~5 + 저장 장 · one = 수미상관(첫 장·캡션 첫 줄 문장 -> 끝 장·캡션 끝에서 받기) 3장 · vs = 사진 2장 나란히 + 'A vs B' ·
    ask = 사진 4장 + 1~4 댓글 질문(그날 저녁 재미 질문이 결과 1줄) · check = 사기 전 확인할 점(정보만) · guess = 사진 + '얼마일까요?' + 힌트 장(가격 X) -> 3시간 뒤 정답 댓글 ·
    top = 최근 24시간 사이트 많이 본 5개(GoatCounter 실제) · fun = 재미 질문 + 관련 제품 1개 작게. 못 만들면 one -> theme 순으로 대신.
    카드 번호 순서 = docs/cards/{stem}.json · 이름 = names.json · 쓴 상품 = seen igu(7일). -> 칸 상태 dict({"done": 이유} = 그 칸 X)."""
    import cards
    now, day, posts = time.time(), stem[:10], load(POSTS, [])
    tok = E.get("IG_TOKEN")
    label, cats = IGT_DAYS[kst.tm_wday]
    d, k0 = f"{IGT_DIR}/{stem}", kst.tm_yday + int(stem[11:])
    shutil.rmtree(d, ignore_errors=True)
    take = lambda pool, n: [x for x in (igt_item(seen, i, p, k0 + j) for j, (i, p) in enumerate(pool[:n * 3])) if x][:n]
    for kd in dict.fromkeys((kind, "one", "theme")):
        lb = "요즘 많이 본" if kd == "top" else label  # 대신 형식(top -> theme)엔 요일 테마 이름 그대로
        its, extra, files = [], {}, []
        if kd == "top":
            urls = (load(GC_TOP, {}) or {}).get("urls") or []
            pool = {p["url"]: (i, p) for i, p in igt_pool(seen, posts, None, day)}
            its = take([pool[u] for u in urls if u in pool], IGT_N)
        elif kd == "fun":
            q, qc = IG_FUN_Q[kst.tm_yday % len(IG_FUN_Q)]
            its = take(igt_pool(seen, posts, qc, day), 1)
        elif kd == "one":
            its = take(igt_pool(seen, posts, None, day, one=True), 1)
        else:
            its = take(igt_pool(seen, posts, cats, day), {"theme": IGT_N, "vs": 2, "ask": 4, "check": 3, "guess": 1}[kd])
        need = {"theme": IGT_MIN, "top": IGT_MIN, "vs": 2, "ask": 4, "check": 2}.get(kd, 1)
        if kd == "check":  # 확인할 점이 다른 상품만(같은 줄 X) -> 'N가지' = 보이는 줄 수
            its = [x for k, x in enumerate(its) if x["check"] and x["check"] not in [y["check"] for y in its[:k]]][:4]
        if len(its) < need:
            print("ig feed", stem, kd, f"상품 {len(its)}개 -> 다른 형식")
            continue
        c = cat_of(its[0]["p"]) if kd in ("one", "guess", "fun", "top") else cats[0]
        cat, slug = CAT_META[c][1], CAT_META[c][0]
        cp = ig_copy(kd, lb if kd != "one" else cat, its)
        notes = aff_notes(x["p"]["url"] for x in its)
        rows = "\n".join(f"{n}. {clip(x['name'], 28)} · {x['price']}" for n, x in enumerate(its, 1))
        nums = "1번" if len(its) == 1 else f"1~{len(its)}번"
        link = f"🛒 프로필 링크 → {cat} {nums}"
        if kd in ("theme", "top"):
            files = [cards.theme_cover([x["photo"] for x in its], cp["title"], " · ".join(clip(x["name"], 10) for x in its), f"{'월화수목금토일'[kst.tm_wday]}요일 {lb}", k0, f"{d}/00.jpg")]
            files += [cards.theme_slide(x, n, f"{d}/{n:02d}.jpg") for n, x in enumerate(its, 1)] + [cards.theme_end(cat, k0 + 3, f"{d}/09.jpg")]
            cap = f"{cp['seo']}\n{notes}\n\n{cp['say']}\n\n{rows}\n\n저장해 두고 필요할 때 보세요 🔖\n{cp['q']}\n\n{link}"
        elif kd == "one":
            it = its[0]
            good = [x for x in (it["tip"], it["unit"], it["fact"]) if x][:2] or [f"{cat} 중 오늘 특가"]
            files = [cards.theme_slide({**it, "head": cp["open"]}, None, f"{d}/01.jpg", facts=False),
                     cards.theme_note(clip(it["name"], 22), [("이런 점이 좋아요", good), ("확인할 점", [it["check"] or "결제 전 최종가 확인"])], f"{it['when']} 가격 · 제휴 링크(수수료)", k0 + 1, f"{d}/02.jpg"),
                     cards.theme_end(f"{cat} 1번", k0 + 2, f"{d}/03.jpg", top="\n".join(cards.wrap(ImageDraw_dummy(), cp["close"], cards.pf("ExtraBold", 80), 860, 3)), mark=False)]
            cap = f"{cp['open']}\n{notes}\n\n{cp['say']}\n{rows}\n\n{cp['q']}\n\n{link}\n\n{cp['close']}"  # 수미상관(M-3): 첫 줄 = 첫 장 문장, 끝 줄 = 끝 장 문장
        elif kd == "vs":
            a, b = its
            files = [cards.q_card([a["photo"], b["photo"]], ("A", "B"), f"{clip(a['name'], 9)} vs\n{clip(b['name'], 9)}", [f"A {a['name']} · {a['price']}", f"B {b['name']} · {b['price']}"],
                                  f"{a['when']} 가격 · 제휴 링크(수수료)", k0, f"{d}/01.jpg", head=f"핫딜픽 · 이거 vs 저거")]
            cap = f"A vs B, 여러분은? 🤔\n{notes}\n\n{cp['say']}\n\nA {a['name']} · {a['price']}\nB {b['name']} · {b['price']}\n\n{cp['q']} 댓글로 A·B 알려주세요"
        elif kd == "ask":
            files = [cards.q_card([x["photo"] for x in its], ("1", "2", "3", "4"), cp["title"], [f"{n}. {clip(x['name'], 24)}" for n, x in enumerate(its, 1)], "댓글로 1~4 번호만 남겨 주세요 · 제휴 링크(수수료)", k0, f"{d}/01.jpg", head=f"핫딜픽 · 오늘의 질문")]
            cap = f"{cp['title'].replace(chr(10), ' ')} 1~4 댓글로 🙋\n{notes}\n\n{cp['say']}\n\n{rows}"
            extra = {"ask": [x["name"] for x in its]}
        elif kd == "check":
            chk = [x["check"] for x in its]
            files = [cards.q_card([its[0]["photo"]], (), cp["title"], [f"✔ {c_}" for c_ in chk], "판매 페이지 정보 그대로 · 결제 전 최종가 확인", k0, f"{d}/01.jpg", head=f"핫딜픽 · 사기 전 체크리스트", small=True)]
            cap = f"{cp['title'].replace(chr(10), ' ')} ✅\n{notes}\n\n{cp['say']}\n\n" + "\n".join(f"✔ {c_}" for c_ in chk) + f"\n\n{cp['q']}"
        elif kd == "guess":
            it = its[0]
            hint = [x for x in (it["size"] and f"구성: {it['size']}", it["fact"] and re.sub(r"\s*·?\s*\d[\d,]*\s*원[^·]*", "", it["fact"])) if x] or ["쿠팡 진열 상품"]
            files = [cards.q_card([it["photo"]], (), "이거 얼마일 것\n같아요?", [it["name"]], "3시간 뒤 정답을 댓글로 알려드려요", k0, f"{d}/01.jpg", head="핫딜픽 · 가격 맞히기"),
                     cards.theme_note("힌트 드려요 🔎", [("힌트", hint), ("정답은", ["3시간 뒤 댓글로!"])], f"{it['when']} 가격 기준 · 제휴 링크(수수료)", k0 + 1, f"{d}/02.jpg")]
            cap = f"이거 얼마일 것 같아요? 🤔\n{notes}\n\n{cp['say']}\n\n댓글로 맞혀 봐요, 3시간 뒤 정답!"
            extra = {"guess": {"price": it["price"], "won": won(it["price"]), "when": it["when"], "cat": cat}}
        else:  # fun
            it = its[0]
            tl = ig_ask_tally(seen, tok)
            res = [f"{'어제는' if (seen.get('igask') or {}).get('day') != day else '아까 질문엔'} {tl[0]}번({clip(tl[1], 12)})이 제일 많았어요!"] if tl else []  # 실제 댓글 집계만
            files = [cards.q_card([it["photo"]], (), "\n".join(cards.wrap(ImageDraw_dummy(), q, cards.pf("ExtraBold", 76), 950, 2)), res + [f"곁들임: {clip(it['name'], 22)} · {it['price']}"],
                                  f"{it['when']} 가격 · 제휴 링크(수수료)", k0, f"{d}/01.jpg", head="핫딜픽 · 재미 질문", small=True)]
            cap = f"{q} 😆\n{notes}\n\n" + (res[0] + "\n\n" if res else "") + f"{cp['say']}\n\n곁들임: {it['name']} · {it['price']}"
        cap = (cap + f"\n\n상품 사진: 판매 페이지(쿠팡)\n\n{' '.join(cp['tags'][:3])}")[:2200]
        json.dump([x["i"] for x in its], open(f"docs/cards/{stem}.json", "w"))  # 카드 번호 순서(사이트 맨 위·c/칸 맨 위)
        card_names_put(stem, title=cp["title"].replace("\n", " ") if kd in ("theme", "top", "check", "ask") else clip(its[0]["name"], 24) if kd != "vs" else "이거 vs 저거",
                       slug=slug, cat=cat, theme=lb if kd in ("theme", "check", "ask", "vs") else kd, kind=kd)
        cut = time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600 - IG_REPEAT * 86400))
        seen["igu"] = {"t": now, "m": {**{u: x for u, x in seen.get("igu", {}).get("m", {}).items() if x > cut}, **{x["p"]["url"]: day for x in its}}}
        print("ig feed 준비", stem, kd, lb, len(its), "개 ·", " / ".join(clip(x["name"], 12) for x in its))
        return {"t": now, "kind": kd, "files": files, "cap": cap, "cmt": ig_cmt(seen, cat, len(its), slug) if kd in IG_LINKY else "", **extra}
    return {"t": now, "done": "상품 모자람"}


def ImageDraw_dummy():
    """줄 나누기(cards.wrap)용 빈 그림판."""
    from PIL import Image, ImageDraw
    return ImageDraw.Draw(Image.new("RGB", (1, 1)))


def ig_feed(seen):
    """L·M 피드(IG_FEED 11·14·17·20시 — 형식 IG_CYCLE): 칸 시각 IGF_PREP 전 카드(igf_make) -> 칸 시각 + 15~20분 무작위 뒤 사이트에 뜨면(HEAD) 조각(1장 = 사진 글) -> ig_carousel 묶음
    -> ig_publish 발행(하루 IG_FEED_MAX·2시간 간격·쉼 = F) -> 링크 형식 = 구매 링크 댓글(I) · 가격 맞히기 = 3시간 뒤 정답(ig_guess) · 질문 = 그날 재미 질문 집계(igask).
    첫 테마 넘기기 = 릴스(H-4). 실행마다 칸 1개만."""
    tok, uid = E.get("IG_TOKEN"), E.get("IG_USER_ID")
    now = time.time()
    if not (IG_H and IG_AUTO and tok and uid) or seen.get("ig_hold", 0) > now:
        return
    kst = time.gmtime(now + 9 * 3600)
    today, sec = time.strftime("%Y-%m-%d", kst), kst.tm_hour * 3600 + kst.tm_min * 60
    for hh, (h, m) in IG_FEED.items():
        at, stem = h * 3600 + m * 60, f"{today}_{hh}"
        key, st = "igf_" + stem, seen.get("igf_" + stem)
        if (st and st.get("done")) or not at - IGF_PREP <= sec < at + IG_LATE * 3600:
            continue
        if st is None:
            st = seen[key] = igf_make(seen, ig_fmt(datetime(kst.tm_year, kst.tm_mon, kst.tm_mday).toordinal(), hh), stem, kst)
            if st.get("files"):
                return
            continue
        if now < ig_due(seen, "igd_" + stem, kst_ts(f"{today} {h:02d}:{m:02d}")):  # 칸 시각 + 15~20분 무작위(M-1)
            continue
        urls = [SITE + f[len("docs/"):] for f in st["files"]]
        try:
            for u in urls:
                http(u, method="HEAD")
        except Exception:
            if now - st["t"] > IGF_PREP + 3600:
                st["done"] = "사이트에 안 뜸"
            continue
        st["done"] = 1
        auth, meta = {"Authorization": "Bearer " + tok}, {"kind": "one" if st["kind"] == "one" else "theme", "cmt": st["cmt"], "stem": stem,
                                                          **({"guess": st["guess"]} if st.get("guess") else {}), **({"ask": st["ask"]} if st.get("ask") else {})}
        try:
            if len(urls) == 1:
                seen["igc_" + json.loads(http(f"{IG}/{uid}/media", {"image_url": urls[0], "caption": st["cap"]}, auth, "POST"))["id"]] = {"t": now, **meta, "cap80": st["cap"][:80]}
            else:
                seen["igk_" + stem] = {"t": now, "cap": st["cap"], "kids": [json.loads(http(f"{IG}/{uid}/media", {"image_url": u, "is_carousel_item": True}, auth, "POST"))["id"] for u in urls], **meta}
        except Exception as e:
            ig_fail(seen, now, f"{stem} {st['kind']} 컨테이너 {ig_err(e)}")
            return
        ig_live(stem, now)
        print("ig feed", stem, st["kind"], len(urls), "장")
        if st["kind"] == "theme" and not seen.get("reelt_" + today):
            seen["reelt_" + today] = {"t": now}
            ig_theme_reel(seen, stem, st, kst)
        return


def ig_guess(seen):
    """M-2 가격 맞히기 정답(게시 IG_GUESS_AFTER 뒤 — 댓글 0개여도 꼭): 계정 댓글 '정답은 N원이에요! (M/D H시 확인)' + 구매 = 프로필 링크 → 칸 1번 ·
    가장 가까운 댓글 1개에만 답글 '거의 정답! 👏'(그 게시물에 1번 — 도배 X) · 댓글 읽기 못 하면 정답 댓글만. 실패 = 로그·알림(ig_comment)."""
    tok = E.get("IG_TOKEN")
    now = time.time()
    if seen.get("ig_hold", 0) > now:  # 행동 제한 쉼 = 댓글도 X(쉼 끝나고 늦게라도 정답)
        return
    for k in [k for k, v in seen.items() if k.startswith("igans_") and isinstance(v, dict) and not v.get("done") and now - v["t"] >= IG_GUESS_AFTER]:
        v, pid = seen[k], k[6:]
        v["done"] = 1
        if not tok:
            continue
        ig_comment(seen, tok, pid, f"정답은 {v['price']}이에요! ({v['when'].replace(' 확인', '')} 확인)\n구매는 프로필 링크 → {v['cat']} 1번 🙂")
        if v.get("stem"):
            card_names_put(v["stem"], ans=1)  # 정답 뒤에야 사이트 c/칸 맨 위에(그 전엔 가격이 보이니까)
        try:
            cs = json.loads(http(f"{IG}/{pid}/comments?fields=id,text&limit=50", None, {"Authorization": f"Bearer {tok}"})).get("data") or []
        except Exception as e:
            print("ig 정답 댓글 읽기 X", err_brief(e))
            continue
        guess = lambda t: [round(float(a) * {"만": 10000, "천": 1000}.get(u, 1) + (int(c) * 1000 if c else 0)) for a, u, c in re.findall(r"(\d+(?:\.\d+)?)\s*(만|천)?\s*(?:(\d+)\s*천)?", (t or "").replace(",", ""))]  # '1만2천'·'1.2만'·'12000'·'11,990원'
        best = min(((abs(g - v["won"]), c["id"]) for c in cs if not (c.get("text") or "").startswith("정답은") for g in guess(c.get("text")) if g >= 100), default=None)
        if best and v.get("won"):
            try:
                http(f"{IG}/{best[1]}/replies", {"message": "거의 정답! 👏"}, {"Authorization": f"Bearer {tok}"}, "POST")
                print("ig 정답 가까운 댓글에 답글", pid)
            except Exception as e:
                print("ig 답글 실패", ig_err(e))

IG_CW_GAP, IG_CW_POSTS = 30 * 60, 6  # L 소통: 댓글 확인 30분마다 · 최근 게시물 6개
IG_REPLY_PROMPT = """인스타그램 댓글에 달 답글 초안 1개를 써 주세요. 핫딜픽(쇼핑 정보 계정)이 친구한테 말하듯 1인칭·짧게(40자 안팎)·해요체·이모지 0~1개.
- 게시물: {post}
- 댓글: {text}
- 아는 사실(게시물 안 정보)만. 효능·최저가 단정, 써 본 척, 다른 계정 언급 X. 구매·링크를 묻지 않으면 구매 권유 X."""


def ig_comments(seen):
    """L 소통(10/26 진우 '인스타에서 소통하고 싶어'): 최근 게시물 IG_CW_POSTS개의 새 댓글(내 계정·이미 본 것 X) -> 관리봇 알림 + 답글 초안 1개(Claude — '링크'·'어디서' = '프로필 링크 → {칸} N번이에요 🙂')
    + [보내기] 버튼(누르면 그 댓글에 답글) · 이 알림에 답장으로 고친 문구 = 그걸로 답글(publish_approved) · 자동 답글 X · 30분마다(IG_CW_GAP) · 못 읽음(권한) = 로그만."""
    tok, uid = E.get("IG_TOKEN"), E.get("IG_USER_ID")
    now = time.time()
    if not (IG_H and tok and uid) or now - seen.get("igcw", {}).get("t", 0) < IG_CW_GAP:
        return
    h = {"Authorization": f"Bearer {tok}"}
    cw = seen["igcw"] = {"t": now, "ids": {k: v for k, v in seen.get("igcw", {}).get("ids", {}).items() if v > now - 7 * 86400}, "me": seen.get("igcw", {}).get("me")}
    try:
        cw["me"] = cw["me"] or json.loads(http(f"{IG}/{uid}?fields=username", None, h)).get("username")
        ms = json.loads(http(f"{IG}/{uid}/media?fields=id,caption&limit={IG_CW_POSTS}", None, h)).get("data") or []
    except Exception as e:
        print("ig 댓글 확인 X", err_brief(e))
        return
    names = {str(v.get("pid")): (k, v) for k, v in load(CARD_NAMES, {}).items() if isinstance(v, dict) and v.get("pid")}  # 게시물 id -> (카드 이름, 칸)
    for m in ms:
        try:
            cs = json.loads(http(f"{IG}/{m['id']}/comments?fields=id,text,username,timestamp&limit=50", None, h)).get("data") or []
        except Exception as e:
            print("ig 댓글 못 읽음", err_brief(e))
            return
        for c in cs:
            if c["id"] in cw["ids"] or c.get("username") == cw["me"]:
                continue
            cw["ids"][c["id"]] = now
            (stem, nm), text = names.get(str(m["id"]), ("", {})), (c.get("text") or "")[:300]
            n = len(load(f"docs/cards/{stem}.json", [])) if stem else 0
            if re.search(r"링크|어디서|어디|구매|파는|사는 곳|판매", text):
                draft = f"프로필 링크 → {nm.get('cat', '오늘 카드 딜')} {'1번' if n == 1 else f'1~{n}번' if n else '번호'}이에요 🙂"
            else:
                try:
                    draft = clip(str(ai_json(IG_REPLY_PROMPT.format(post=clip((m.get("caption") or "").split("\n")[0], 80), text=text), {"reply": {"type": "string"}})["reply"]).strip(), 80)
                    draft = draft if draft and not re.search(IGT_BAN, draft) else "고마워요 🙂"
                except Exception:
                    draft = "고마워요 🙂"
            r = tg("sendMessage", chat_id=ADMIN, text=f"💬 인스타 댓글 — @{c.get('username', '?')}\n{text}\n\n✏️ 답글 초안: {draft}\n\n그대로 = [보내기] · 고쳐 보내기 = 이 메시지에 답장으로 문구",
                   reply_markup={"inline_keyboard": [[{"text": "📤 보내기", "callback_data": f"igr:{c['id']}"[:64]}]]})
            if r:
                seen["igrd_" + c["id"]] = {"t": now, "draft": draft, "mid": r["message_id"]}


def ig_reply_send(seen, cid, text):
    """관리봇 [보내기]·답장 -> 그 인스타 댓글에 답글 1번(POST /{comment-id}/replies) -> (성공, 오류)."""
    try:
        http(f"{IG}/{cid}/replies", {"message": text[:300]}, {"Authorization": "Bearer " + E.get("IG_TOKEN", "")}, "POST")
        seen.get("igrd_" + cid, {})["done"] = 1
        return True, ""
    except Exception as e:
        return False, ig_err(e)


def ig_theme_reel(seen, stem, st, kst):
    """H-4 릴스: 그날 첫 테마 넘기기 장들을 1.5초씩 넘김 영상(1080x1920 — 흐린 바탕 + 가운데 장, 0.3초 전환) + 배경음악(라이선스 기록된 Pixabay 곡, 날마다 돌림) ->
    REEL_PUBLIC이면 docs/reels/{날짜}.mp4 + 22시 ig_reel(피드엔 X — 하루 피드 수 그대로) · 관리봇에 영상·곡 이름(기록). 실패 = 로그만(넘기기는 그대로)."""
    import cards
    today = stem[:10]
    try:
        music, song = bgm(kst), song_of(kst)
        out = f"docs/reels/{today}.mp4" if REEL_PUBLIC else os.path.join(tempfile.gettempdir(), f"reel_{today}.mp4")
        path = cards.slideshow(st["files"], out, music)
        if REEL_PUBLIC:
            seen["reel_" + today] = {"t": time.time(), "cap": st["cap"][:1024], "feed": False}
        tg_video(path, f"🎬 오늘 릴스(테마 넘기기 {len(st['files'])}장 · 1.5초씩)" + (f" · 🎵 {song['name']}" if music and song else " · 음악 X") + (f" — {REEL_HOUR}시 자동 게시" if REEL_PUBLIC else ""))
        print("ig reel 테마", stem, song and song.get("name"))
    except Exception as e:
        print("ig reel 테마 실패", repr(e))


def snack_post(seen):
    """15:30 '🍪 출출할 때 간식 N' — 최근 3일 간식 딜(SNACK_WORDS + 오늘 날씨 간식) 최대 3개, 2개 미만이면 안 올림(빈 글 X)."""
    key = due(SNACK_HOUR, "snack", seen)
    if not key:
        return
    items = wx_deals(seen, SNACK_WORDS + tuple(wx_words(seen, True)), deny=SNACK_NOT)
    if len(items) < 2:
        seen[key] = time.time()
        print(f"snack post: 간식 딜 {len(items)}개 -> 안 올림")
        return
    wx_post(seen, key, "🍪 출출할 때 간식 {n}", items, "", "snack", lo=2)


def poll_opts(low):
    """기록 최저 단위가격 근처 구간 보기 4개 — 간격 = 최저의 1/3 이하 1·2·5×10ⁿ원: 120 -> 120원 이하 / 140원까지 / 160원까지 / 더 줘도 사요."""
    s = max((x for x in (10, 20, 50, 100, 200, 500, 1000, 2000, 5000) if x <= low / 3), default=10)
    a = max(s, round(low / s) * s)
    return [f"{a:,}원 이하", f"{a + s:,}원까지", f"{a + 2 * s:,}원까지", "더 줘도 사요"]


def poll_text(rec):
    """투표 글 (본문, 보기) — 링크·상품명·몰 이름 없음 = 대가성 문구 X."""
    name, unit, rows = rec
    return f"🗳️ {name} {unit} 얼마면 '싸다' 싶어요?\n\n내일 이 글 답글로 핫딜픽 기록 최저가 알려드릴게요", poll_opts(rows[0][0])


POLL_PROMPT = """Threads 가격 투표 글을 반말로 써 주세요. 품목: {name}(핫딜픽이 {unit} 가격 기록을 모으는 생활용품).
- q = 질문 한 줄(40자 안팎), opts = 보기 정확히 4개(짧게 — Threads가 보기를 25바이트까지만 받음: 한글 1자 3바이트·숫자·띄어쓰기·기호 1바이트, 한글만이면 8자).
- 반말·공감형('~요'로 끝나는 말 X). 마지막 보기는 가볍게 웃긴 것.
- 상품명·브랜드(신라면·삼다수·햇반 같은 것)·쇼핑몰·편의점 이름·링크·광고 문구 X, 과장(역대급·무조건·손해) X.
- {kind}"""
POLL_KIND = {  # 10/22 진우 시안 고름(반말·공감형 보기·마지막 보기는 가볍게 웃기게): 글마다 무작위 가 생활형 / 나 가격형
    "life": "유형: 생활형 — 이 품목을 쟁이는 스타일·떨어졌을 때 어떻게 하는지 같은 생활 질문, 가격(원) 숫자 X. 예: 라면 쟁이는 스타일 골라봐 / 박스째 쌓아둠 · 5개입이면 충분 · 땡기면 편의점행 · 라면 끊음(진짜)",
    "price": "유형: 가격형 — '{unit} 얼마면 오 싸다 해?' 같은 질문, 가격 숫자는 {nums}만(다른 숫자 X). 예: {name} {unit}, 얼마면 \"오 싸다\" 해? / {a}이면 삼 · {b}까진 OK · {c}부턴 고민 · 가격 안 보고 집음"}
POLL_BRANDS = (r"신라면|진라면|너구리|짜파게티|안성탕면|컵누들|사발면|농심|삼양|오뚜기|팔도|삼다수|아이시스|백산수|풀무원|크리넥스|깨끗한나라|모나리자|잘풀리는|"  # 기록 품목(PRICE_ITEMS) 브랜드
               r"퍼실|리큐|테크|피죤|맥심|모카\s*골드|화이트\s*골드|카누|베베숲|몽드드|햇반|엘라스틴|케라시스|GS25|세븐일레븐|이마트24|(?<![A-Za-z])CU(?![A-Za-z])")  # + 편의점(몰)
POLL_YO = r"(?<![필중주수소])요[?!.~ㅋㅎ\s]*$|죠[?!.~ㅋㅎ\s]*$|(?<![다아])니다[?!.~ㅋㅎ\s]*$"  # 투표 보기 = 끝에서만(‘요 정도면’·‘참치마요’는 반말)


def wons(s):
    """글 속 원 금액(숫자) — '5천원대' 5000 · '1만2천원' 12000 · '1,500원' 1500."""
    return {int(m[1].replace(",", "")) * {"만": 10000, "천": 1000, "": 1}[m[2]] + int(m[3] or 0) * 1000
            for m in re.finditer(r"(\d[\d,]*)\s*(만|천|)\s*(?:(\d+)\s*천)?\s*원", s)}


def poll_ai(rec):
    """10/22 진우 '재미있게': Claude가 반말 질문·보기 4개(글마다 무작위 가 생활형 / 나 가격형 — 가격 숫자는 poll_opts 구간 값만) -> (본문, 보기).
    검사(질문 60자·보기 4개 1~25바이트(th_poll)·끝이 ~요 X·몰·편의점·브랜드(POLL_BRANDS)·링크·광고·과장 X·없는 금액 X) 실패 -> 걸린 말을 알려 주고 1번 다시, 그래도면 지금 틀(poll_text).
    링크·상품명 없음 = 대가성 문구 X 그대로."""
    name, unit, rows = rec
    kind, opts0 = random.choice(("life", "price")), poll_opts(rows[0][0])
    nums = wons(" ".join(opts0)) if kind == "price" else set()
    ban = "|".join((OTHER_STORES, SAVE_STORES.replace("토스", "토스(?!트)"), POLL_BRANDS, r"https?://|www\.|\.com|\.kr|t\.me|링크|광고|수수료", WU_HYPE))
    def why(s):  # 걸린 이유('' = 통과)
        m = re.search(ban, s, re.I)
        return ("빈 칸" if not s else f"'{s}' ~요로 끝남" if any(re.search(POLL_YO, x) for x in re.split(r"[,·/()]", s))
                else f"'{m[0]}' 쓰면 안 됨" if m else f"'{s}' 재료에 없는 금액" if wons(s) - nums else "")
    a, b, c = (re.match(r"[\d,]+원", x)[0] for x in opts0[:3])
    prompt = POLL_PROMPT.format(name=name, unit=unit, kind=POLL_KIND[kind].format(unit=unit, name=name, nums=", ".join(opts0[:3]), a=a, b=b, c=c))
    try:
        again = ""
        for _ in (0, 1):
            r = ai_json(prompt + again, {"q": {"type": "string"}, "opts": {"type": "array", "items": {"type": "string"}}})
            q, opts = re.sub(r"\s+", " ", str(r.get("q") or "")).strip(), [re.sub(r"\s+", " ", str(o)).strip() for o in r.get("opts") or []]
            bad = [x for x in [f"질문 {len(q)}자" if len(q) > 60 else "", f"보기 {len(opts)}개" if len(opts) != 4 else "", why(q), *map(why, opts),  # 내용 먼저(다시 = 앞 4개만)
                               *(f"'{o}' 너무 김(한글 8자까지)" for o in opts if len(o.encode()) > 25)] if x]
            if not bad:
                print("poll ai", kind, q, "|", " / ".join(opts))
                return f"🗳️ {q}\n\n내일 이 시간에 답글로 핫딜픽 기록 최저가 알려줌", opts
            again = "\n\n다시: " + " · ".join(bad[:4])
        raise ValueError(f"검사 실패: {bad}")
    except Exception as e:  # Claude 실패·검사 실패 = 지금 틀
        print("poll ai 지금 틀로", clip(repr(e), 160))
        return poll_text(rec)


def poll_reply_text(k, rec, pa):
    """어제 투표 결과 답글: '📊 어제 1등은 "보기" N% ㅋㅋ'(0명 = '아무도 안 찍음 ㅋㅋ') + '쟁일 거면 … → 기록 최저(게시 날짜)' + 기록 페이지 — 사이트 링크 글 규칙 그대로(맨 앞 대가성 문구 = 기록 딜들의 프로그램, 👉 링크·팔로우·텔레그램 줄)."""
    name, unit, rows = rec
    low, n, ks = rows[0], (pa or {}).get("total_votes") or 0, [x for x in POLL_KEYS if x in (pa or {})]
    pct = {x: pa.get(x + "_votes_percentage") or 0 for x in ks}
    top = n and ks and max(ks, key=pct.get)
    scale = 100 if sum(pct.values()) <= 1.01 else 1  # 문서 예시 = 0.10(비율) — 0~100으로 와도 그대로
    t = th_note(ig_notes([r[3] for r in rows])) + (f'📊 어제 1등은 "{pa[top]}" {round(pct[top] * scale)}% ㅋㅋ' if top else "📊 어제는 아무도 안 찍음 ㅋㅋ 그래도 알려줌") \
        + f"\n쟁일 거면 이 가격은 알아두자 → 핫딜픽 기록 최저 {name} {low[1]} ({int(low[3]['t'][5:7])}/{int(low[3]['t'][8:10])})\n\n👉 {SITE}c/{k}.html?ref=th\n{th_follow(False)}\n📲 실시간 알림 t.me/hotdeal_pick"  # 10/22 진우 '재미있게'(반말)
    return t if len(t) <= 480 else t.rsplit("\n", 2)[0]  # 넘치면 팔로우·텔레그램 줄을 뺌(링크는 남김)


def poll_post(seen):
    """POLL_HOUR(21:40) Threads 가격 투표(10/17 진우 '유입 늘리기 ①', 10/22 '재미있게' — Claude 반말 질문·보기, poll_ai): 어제 투표가 있으면 먼저 결과 답글(댓글 권한 없으면 건너뜀·알림, 실패해도 다시 X),
    그다음 오늘 투표 1개 — 기록 PRICE_MIN개↑ 품목 중 최근 POLL_REUSE일 안 쓴 것, 기록 많은 순. 묶음 간격·시간당 상한(busy)·Threads 45분 간격 안에서(막히면 다음 실행에, 2시간 안)."""
    tok, key = E.get("THREADS_TOKEN"), due(POLL_HOUR, "poll", seen)
    if not tok or not key:
        return
    ps = load(POSTS, [])
    now, recs = time.time(), price_records(ps, shelf=False, skip={i for i, p in enumerate(ps) if not p["text"].startswith("📋") and not site_ok(p)})  # Threads 투표 = 채널 글 기록만 · 사이트에서 뺀 딜 X(사이트 c/ 쪽과 같은 기록 — 없는 쪽 링크·안 보이는 최저가 X, 10/25 리뷰)
    op = seen.get("polls", {}).get("open")
    if op and now - op["t"] >= 20 * 3600:  # 24시간 투표가 닫힐 즈음(다음 날 같은 회차)
        seen["polls"] = {**seen["polls"], "t": now, "open": None}  # 먼저 지움: 실패해도 같은 답글 반복 X
        if op["slug"] not in recs:
            print("poll reply: 기록 품목이 없어짐 -> 답글 X")
        elif not th_reply_ok(seen):
            alert(seen, "alert_poll_reply", "⚠️ 가격 투표 결과 답글 못 달았어요 — Threads 댓글 권한 확인: " + clip((seen.get("threply") or {}).get("err") or "권한 확인 실패(네트워크)", 160))
        else:
            pa = json.loads(http(f"{THREADS}/{op['id']}?fields=poll_attachment{{{','.join(POLL_KEYS + tuple(x + '_votes_percentage' for x in POLL_KEYS))},total_votes}}&access_token={tok}")).get("poll_attachment")
            th_reply(tok, op["id"], poll_reply_text(op["slug"], recs[op["slug"]], pa))
    card = os.path.exists(time.strftime("docs/cards/%Y-%m-%d.png", time.gmtime(now + 9 * 3600))) and now - seen.get(time.strftime("threads_%Y%m%d", time.gmtime(now + 9 * 3600)), now) < BUNDLE_GAP
    if busy(seen, cap=False) or card or now - th_day(seen, now)["last"] < TH_SOLO_GAP:  # 21:40 = 시간당 상한(채널 글 수)은 안 봄 · 21시 카드 Threads 글과 10분 띄움(10/22 리뷰)
        return
    used = {k: t for k, t in seen.get("polls", {}).get("used", {}).items() if now - t < POLL_REUSE * 86400}
    k = next((k for k, v in sorted(recs.items(), key=lambda x: -len(x[1][2])) if k not in used), None)
    seen[key] = now  # 먼저 표시: 실패해도 오늘 다시 안 올림(스팸 방지) — 실패는 main 알림
    if not k:
        print(f"poll: 기록 {PRICE_MIN}개↑ 품목이 없거나 {POLL_REUSE}일 안에 다 씀 -> 오늘 X")
        return
    pid = th_poll(tok, *poll_ai(recs[k]), th_topic(seen))
    th_mark(seen, reopen="poll")  # 개별 글 수엔 안 셈(재오픈처럼) — 45분 간격만 같이
    seen["polls"] = {"t": now, "used": {**used, k: now}, "open": {"id": pid, "slug": k, "t": now}}
    print("poll:", k, len(recs[k][2]), "records")


def log_text(seen):
    """운영 일지(Threads, 링크 X) — posts.json·seen 사실로만: 오늘 본 커뮤니티 딜 수 · 고른 수 · 반응(분당 조회) 1등 + 날씨 질문 한 줄. 금지어(LOG_DENY)가 들어가면 None."""
    kst = time.gmtime(time.time() + 9 * 3600)
    today = time.strftime("%Y-%m-%d", kst)
    t0, ids = kst_ts(today + " 00:00"), "|".join([*FEEDS, "ruliweb", "clien"])
    judged = sum(1 for k, v in seen.items() if re.match(rf"(?:{ids})_", k) and isinstance(v, (int, float)) and v >= t0)
    picked = [p for p in load(POSTS, []) if p["t"].startswith(today) and not p["text"].startswith("📋") and not p.get("own")]
    if not picked:
        return None
    top = max(picked, key=lambda p: p.get("vpm") or p.get("pop") or 0)
    ws = weather(seen)
    rules = wx_rules(ws[0]) if ws else []
    text = (f"📝 핫딜픽 운영 일지 · {kst.tm_mon}/{kst.tm_mday}\n" + (f"오늘 핫딜픽이 본 커뮤니티 딜 {judged}개 중 {len(picked)}개만 골랐어요." if judged >= len(picked) else f"오늘 커뮤니티 딜 {len(picked)}개를 골랐어요.")
            + (f"\n커뮤니티 반응이 제일 빨랐던 딜: {clip(parse(title_of(top['text']))[1], 30)}" if top.get("vpm") or top.get("pop") else "")
            + f"\n\n{rules[0][4] if rules else '오늘 하루 어땠어요?'}")
    return None if any(w in text for w in LOG_DENY) else text


def daily_log(seen):
    """20:30 운영 일지 1번(Threads만, 링크 X). 금지어면 안 올림. 채널 글이 아니라 묶음 간격만 봄(시간당 상한 X — 22시 미리보기처럼)."""
    key = due(DAILY_LOG_HOUR, "dlog", seen)
    if not key or not E.get("THREADS_TOKEN") or busy(seen, cap=False):
        return
    text = log_text(seen)
    seen[key] = time.time()
    if not text:
        print("daily log: 고른 딜 없음·금지어 -> 안 올림")
        return
    bundled(seen)
    th_bundle(seen, "log", text)


def wx_dm_text(days):
    """다음 7일 예보 -> 진우 DM: 쿠팡 링크 만들 시즌 키워드 10개 + 간식 5개(날씨 맞는 날 수 많은 순, 모자라면 WX_FILL·SNACK_WORDS) + 파트너스 검색 주소(텍스트만)."""
    its, sn = collections.Counter(), collections.Counter()
    for w in days:  # 키워드마다 그날 1번(가습기·어묵처럼 규칙 두 개에 든 것도)
        its.update(dict.fromkeys((k for r in wx_rules(w) for k in r[2]), 1))
        sn.update(dict.fromkeys((k for r in wx_rules(w) for k in r[3]), 1))
    pick = lambda c, fill, n: ([(k, d) for k, d in c.most_common()] + [(k, 0) for k in fill if k not in c])[:n]
    line = lambda n, k, d: f"{n}. {k}" + (f" ({d}일)" if d else "") + f" {CP_SEARCH}{urllib.parse.quote(k)}"
    lo, hi = [w["tmin"] for w in days], [w["tmax"] for w in days]
    return (f"🗓 다음 7일 서울 예보({int(days[0]['date'][5:7])}/{int(days[0]['date'][8:])}~{int(days[-1]['date'][5:7])}/{int(days[-1]['date'][8:])}) — 쿠팡 링크 만들 시즌 키워드\n"
            f"최저 {min(lo)}~{max(lo)}도 · 최고 {min(hi)}~{max(hi)}도 · 비 {sum(w['rain'] >= 60 for w in days)}일 · 건조 {sum(w['hum'] <= 35 for w in days)}일 · 미세먼지 나쁨 {sum((w['pm'] or 0) >= 36 for w in days)}일\n\n"
            "🔑 키워드 10\n" + "\n".join(line(n, k, d) for n, (k, d) in enumerate(pick(its, WX_FILL, 10), 1))
            + "\n\n🍪 간식 5\n" + "\n".join(line(n, k, d) for n, (k, d) in enumerate(pick(sn, SNACK_WORDS, 5), 1)) + "\n\n(주소 = 파트너스 상품 링크 검색 — 골라서 링크 만들어 보내줘)")


def wx_dm(seen):
    """매주 일요일 20시 관리자 DM 1번: 다음 7일 예보 기준 시즌 키워드."""
    kst = time.gmtime(time.time() + 9 * 3600)
    key = time.strftime("wxdm_%Y%m%d", kst)
    if not WEATHER_DM or kst.tm_wday != WEATHER_DM[0] or kst.tm_hour < WEATHER_DM[1] or key in seen:
        return
    ws = weather(seen)
    clip = (seen.get("clip") or {}).get("m") == time.strftime("%Y-%m", kst) and seen["clip"].get("n", 0)
    if ws and len(ws) > 1 and tg("sendMessage", chat_id=ADMIN, text=wx_dm_text(ws[1:8]) + f"\n\n🎬 이번 달 클립 {clip or 0}개 보냄", link_preview_options={"is_disabled": True}):
        seen[key] = time.time()  # 보낸 뒤에만: 날씨·텔레그램 실패면 그날 밤 다음 실행에 다시


def daily_text(cap):
    """#일상 Threads 글: 캡션 그대로(우리 링크 X) + 캡션에 제휴 링크가 있으면 프로그램마다 대가성 문구 맨 앞, 토스 링크면 게시 시점 줄."""
    urls = [u.rstrip(").,]>」』'\"") for u in re.findall(r"https?://\S+", cap)]
    return th_note("\n".join(dict.fromkeys(n for n in map(aff_note, urls) if n))) + cap + (f"\n\n{toss_when()}" if TOSS_NO_CMP and any(map(toss_share, urls)) else "")


def daily_in(seen, m, cap):
    """진우 '#일상 …'(사진 + 캡션): 사진 = docs/daily/에 저장(사이트 반영 뒤 공개 주소 hotdealpick.kr/daily/… — 봇 토큰 든 텔레그램 파일 주소는 저장·게시 X) -> daily_post가 Threads에.
    사진으로 보낸 것만(텔레그램이 위치 정보를 지움 — 파일로 보낸 원본엔 GPS가 남아 사이트에 공개됨), 사진 없거나 글이 Threads 500자를 넘으면 답장만, 같은 메시지가 다시 와도 1번."""
    k = f"dly_{m['message_id']}"
    reply = lambda t: tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": m["message_id"]}, text=t)
    if k in seen:
        return
    if not m.get("photo"):
        reply("📷 #일상은 사진으로 보내줘(파일로 보낸 원본엔 위치 정보가 남고, 글만은 안 올려요)" if m.get("document") else "📷 #일상은 사진과 같이 보내줘(글만은 안 올려요)")
        return
    try:  # 깨진 주소('[https://…]')도 여기서 잡음 — publish_approved는 main 단계 밖이라 예외면 실행 전체가 멈춤
        n = sum(len(c.encode()) if ord(c) > 0xFFFF or 0x2000 <= ord(c) <= 0x2BFF or c == "\ufe0f" else 1 for c in daily_text(cap))  # Threads는 이모지를 바이트로 셈
        if n > 480:  # th_post가 500자에서 자르면 대가성 문구·게시 시점 줄·링크가 잘림
            reply(f"✂️ 글이 {n}자라 Threads에 다 안 들어가요(대가성 문구 포함 480자까지, 이모지는 3~4자로 셈) — 캡션 줄여서 다시 보내줘")
            return
        if TOSS_NO_CMP and any(map(toss_share, re.findall(r"https?://\S+", cap))) and strip_cmp(cap)[0] != cap:
            reply("🙅 토스 링크 글엔 다른 몰 이름·가격 비교를 못 넣어요(토스 규칙) — 빼고 다시 보내줘")
            return
        f = tg("getFile", file_id=m["photo"][-1]["file_id"])
        name = time.strftime("%Y%m%d", time.gmtime(time.time() + 9 * 3600)) + f"_{m['message_id']}.jpg"
        with urllib.request.urlopen(f"https://api.telegram.org/file/bot{E['TG_TOKEN']}/{f['file_path']}", timeout=60) as r:
            data = r.read()
        os.makedirs(DAILY_DIR, exist_ok=True)
        open(f"{DAILY_DIR}/{name}", "wb").write(data)
        ask = (HAS_CP or HAS_TOSS) and not re.search(r"https?://", cap) and bool(daily_kw(cap))  # P: 링크 없는 '#일상 상품명' = 같은 상품 링크 후보 먼저(daily_cands)
        seen[k] = {"t": time.time(), "text": cap, "img": f"{SITE}daily/{name}", **({"ask": 1} if ask else {})}
        reply("📝 받았어요 — " + ("같은 상품 링크 후보를 찾아서 버튼으로 보낼게요(고른 것 = 첫 댓글 링크 · '없음' = 사진만)" if ask else "사이트에 사진이 올라가면(15분쯤) Threads에 올릴게요"))
    except Exception as e:
        print("daily in", repr(e))
        reply(f"⚠️ #일상 사진을 못 받았어요: {err_brief(e)} — 다시 보내줘")


def daily_kw(cap):
    """'#일상 상품명 …' -> 검색어: 첫 줄에서 #태그·주소·이모지·기호 뺀 말(40자 안)."""
    s = re.sub(r"#\S+|https?://\S+|[^\w\s+%.-]", " ", cap.split("\n")[0])
    return " ".join(s.split())[:40].strip()


def daily_cands(seen):
    """P(10/26 진우): 링크 없는 #일상 = 같은 상품 링크 후보 3개(토스 하루특가·많이 팔린 이름에 검색어 낱말이 다 든 것 먼저 — 다른 몰 비교 없는 캡션만 · 점검 땐 보관 링크 있는 것만
    -> 쿠팡 검색 API) -> 관리봇 버튼(publish_approved 'dl:' — 이 버튼 메시지에서 누른 것만) · 진우가 고른 것만 첫 댓글 링크(daily_post) · '없음'·후보 0개 = 사진만.
    main 맨 앞 단계(쿠팡 검색 상한을 사진 가격 확인보다 먼저) · 실행마다 1건 · 토스 후보는 1번만 받아 둠(tc) · 쿠팡 상한·오류 = 다음 실행에 · 버튼 못 보냄 = 다음 실행에 다시."""
    for k in [k for k in seen if k.startswith("dly_") and seen[k].get("ask") and "c" not in seen[k] and not seen[k].get("done")]:
        v = seen[k]
        kw = daily_kw(v["text"])
        if "cs" not in v:
            if "tc" not in v:
                try:
                    ids = set()
                    v["tc"] = [{"n": x["displayName"], "p": x["displayPrice"], "toss": x["tacaItemId"]} for x in toss("/products/today-deals?size=30")["items"] + toss("/products/best-selling?size=100")["items"]
                               if not x.get("isSoldOut") and toss_ok(seen, x["tacaItemId"]) and all(w in x["displayName"] for w in kw.split()) and not (x["tacaItemId"] in ids or ids.add(x["tacaItemId"]))][:3] \
                        if HAS_TOSS and strip_cmp(v["text"])[0] == v["text"] else []
                except Exception as e:  # 토스 실패 = 쿠팡 후보만
                    print("daily cands toss", clip(repr(e), 120))
                    v["tc"] = []
            cs = list(v["tc"])
            try:
                if HAS_CP and len(cs) < 3:
                    r = coupang("GET", f"/products/search?keyword={urllib.parse.quote(kw)}&limit=5")
                    cs += [{"n": x["productName"], "p": int(x.get("productPrice") or 0), "u": x["productUrl"]} for x in (r if isinstance(r, dict) else {}).get("productData") or []
                           if isinstance(x, dict) and urllib.parse.urlsplit(str(x.get("productUrl"))).netloc in CP_SHORT and x.get("productName")][:3 - len(cs)]
            except Exception as e:  # 쿠팡 상한·오류 = 다음 실행에(후보 0개로 끝내지 않음 — 하루 지나면 daily_post가 사진만)
                print("daily cands", "상한" if isinstance(e, CpLimit) else clip(repr(e), 120))
                return
            v["cs"] = cs
        if not v["cs"]:
            v.update(c=[], pick="x", pt=time.time())
            tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": int(k[4:])}, text=f"🔎 '{kw}' 같은 상품 후보를 못 찾아서 사진만 올릴게요")
            continue
        kb = [[{"text": f"{'💙 토스' if c.get('toss') else '🚀 쿠팡'} · {clip(c['n'], 30)} · {c['p']:,}원", "callback_data": f"dl:{k[4:]}:{i}"}] for i, c in enumerate(v["cs"])]
        r = tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": int(k[4:]), "allow_sending_without_reply": True},
               text=f"🔗 '{kw}' 같은 상품 링크 후보 — 사진 속 상품과 확실히 같을 때만 골라줘(고른 것 = 첫 댓글 링크)", reply_markup={"inline_keyboard": kb + [[{"text": "❌ 없음(사진만)", "callback_data": f"dl:{k[4:]}:x"}]]})
        if r:  # 보낸 버튼 메시지 = 이 후보 목록(다른 버튼 메시지에서 누른 건 안 받음)
            v.update(c=v.pop("cs"), kb=r["message_id"])
        return


def daily_post(seen):
    """#일상(daily_in)이 사이트에 올라가면(사진 주소 HEAD) Threads에 1번 — daily_text(사진 + 캡션 그대로, 대가성 문구·게시 시점 줄) + 진우에게 '올렸어요'.
    묶음 글 간격(busy, 시간당 상한 X) 같이 셈. 1시간 넘게 사이트에 안 뜨면 진우에게 알리고 그만."""
    tok, now = E.get("THREADS_TOKEN"), time.time()
    for k in [k for k in seen if k.startswith("dly_") and not seen[k].get("done")] if tok and not busy(seen, cap=False) else []:
        v = seen[k]
        if v.get("ask") and "pick" not in v:  # P: 진우가 링크 후보를 고를 때까지(고르기 전엔 안 올림) · 하루 지나도 안 고름 = 사진만
            if now - v["t"] < 86400:
                continue
            v.update(pick="x", pt=now, late=1)
        try:
            http(v["img"], method="HEAD")
        except Exception:
            if now - v.get("pt", v["t"]) > 3600:  # 고른 때부터 1시간(후보 고르느라 늦어진 글이 HEAD 한 번 실패로 버려지지 않게)
                v["done"] = now
                tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": int(k[4:])}, text="⚠️ 사이트에 사진이 안 떠서 Threads에 못 올렸어요 — 다시 보내줘")
            continue
        v["done"] = now  # 먼저 표시: 실패해도 두 번 안 올림(실패는 main 알림)
        c = v["c"][int(v["pick"])] if str(v.get("pick", "x")).isdigit() and int(v["pick"]) < len(v.get("c", [])) else None
        try:
            link = c and (toss_link(seen, c["toss"], c["n"]) if c.get("toss") else c["u"])  # 토스 = 고른 뒤에만 쉐어링크 만듦
        except Exception as e:  # 링크 못 만듦 = 사진만(사진 글은 그대로 올림)
            print("daily toss link", clip(repr(e), 80))
            link = None
        why = "" if not c else "링크 못 만듦" if not link else "" if TH_REPLY and th_reply_ok(seen) else "댓글 못 닮"  # 링크 = 첫 댓글만(본문 X)
        body, note = daily_text(f"{v['text']}\n{link}").replace(f"\n{link}", "") if link and not why else daily_text(v["text"]), link and aff_note(link)
        if link and not why and th_len(body) > 480:  # 대가성 문구·게시 시점 줄 붙이면 500자에서 잘림 = 사진만
            why = "대가성 문구까지 480자 넘음"
        if why:
            body = daily_text(v["text"])
        rep = link and not why
        r = th_post(tok, body, image=v["img"], tag=th_topic(seen, base="일상"))
        bundled(seen)
        try:
            if rep:
                th_reply(tok, r["id"], f"{note}\n\n👉 구매 링크 {link}", link)
        except Exception as e:
            tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": int(k[4:])}, text=f"⚠️ #일상 링크 댓글 실패({err_brief(e)}) — 앱에서 직접 달아줘\n{link}")
        tail = " (링크 = 첫 댓글)" if rep else f" (링크 없이 사진만: {why}" + (f" · 필요하면 앱에서 직접 댓글 {link}" if link else "") + ")" if why else " (하루 동안 안 골라서 사진만)" if v.get("late") else ""
        tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": int(k[4:])}, text="✅ Threads에 올렸어요" + tail)
        return  # 1번에 1개(묶음 간격)


REPORT_HOURS = (10, 14, 18, 22)  # 관리자에게 성과 리포트 보내는 시각(KST), 회차마다 1번 (10/8 진우 '토스 쉐어 정산금 들어오기 시작' → '1일 4회')


def report(seen):
    """REPORT_HOURS마다 관리자에게: 토스 쉐어링크 실적(오늘·이번 달 — 잠정, 환불되면 줄어듦) + Threads 오늘 올린 글 조회수·링크 클릭·팔로워.
    Threads 숫자는 토큰에 threads_manage_insights 권한이 있어야 나옴(없으면 '권한 필요' 한 줄). 텔레그램 전송이 실패하면 다음 실행에 다시."""
    kst = time.gmtime(time.time() + 9 * 3600)
    hrs = [h for h in REPORT_HOURS if h <= kst.tm_hour]  # 실행이 밀려 회차를 건너뛰면 가장 최근 회차 1번만
    key, today = time.strftime("report_%Y%m%d_", kst) + (str(hrs[-1]) if hrs else ""), time.strftime("%Y-%m-%d", kst)
    if not hrs or key in seen:
        return
    lines = [f"📊 {kst.tm_mon}/{kst.tm_mday} {kst.tm_hour}:{kst.tm_min:02d} 성과 리포트"]  # 회차가 아니라 실제 조회 시각
    if HAS_TOSS:
        try:
            for label, frm in (("오늘", today), ("이번 달", today[:8] + "01")):
                r = toss(f"/performance?fromDate={frm}&toDate={today}&size=50")
                s = r["summary"]
                lines.append(f"\n💰 토스 {label}: 클릭 {s['clickCount']:,} · 판매 {s['soldQuantity']:,}개 · 예상 수익 {s['expectedCommissionAmount']:,}원"
                             f" (구매확정 {s['confirmedCommissionAmount']:,}원)")
            lines += [f"  · {clip(x['productName'] or str(x['productId']), 22)} {x['soldQuantity']}개 {x['expectedCommissionAmount']:,}원"
                      + (" (링크 타고 다른 상품)" if x["attribution"] == "INDIRECT" else "") for x in r["items"][:3]]  # 이번 달, 예상 수익 높은 순(API 정렬)
            if s.get("lastUpdatedAt"):
                lines.append(f"  {s['lastUpdatedAt'][5:16].replace('T', ' ')} 집계 · 잠정(취소·환불되면 줄어듦)")
        except Exception as e:
            lines.append(f"\n💰 토스 실적 조회 실패: {e!r}"[:200])
    tok = E.get("THREADS_TOKEN")
    if tok:
        try:
            now = int(time.time())
            since = now - (now + 9 * 3600) % 86400  # 오늘 0시(KST)
            me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
            posts = json.loads(http(f"{THREADS}/{me}/threads?fields=id,text&since={since}&limit=50&access_token={tok}"))["data"]
            views = []
            for p in posts:
                d = json.loads(http(f"{THREADS}/{p['id']}/insights?metric=views&access_token={tok}"))["data"]  # 남의 글 리포스트는 빈 목록
                views.append((d[0]["values"][0]["value"] if d else 0, p.get("text") or ""))
            c = json.loads(http(f"{THREADS}/{me}/threads_insights?metric=clicks&since={since}&until={now}&access_token={tok}"))["data"]
            f = json.loads(http(f"{THREADS}/{me}/threads_insights?metric=followers_count&access_token={tok}"))["data"]  # since 안 받는 지표
            lines.append(f"\n🧵 Threads 오늘: 글 {len(views)}개 · 조회 {sum(v for v, _ in views):,} · 링크 클릭 "
                         f"{sum(x['value'] for x in (c[0].get('link_total_values') or [])) if c else 0:,} · 팔로워 {f[0]['total_value']['value']:,}")
            for v, t in sorted(views, key=lambda x: -x[0])[:3]:
                t = re.sub(r"^이 (포스팅|콘텐츠)[^\n]*\n+", "", t).split("\n")[0]  # 대가성 문구 줄 빼고 제목
                lines.append(f"  · {v:,} — {clip(t, 26)}")
        except Exception as e:
            body = getattr(e, "body", "") or ""
            lines.append("\n🧵 Threads 조회수: 토큰에 threads_manage_insights 권한 필요 → README 세팅 6번의 6"
                         if "permission" in body.lower() else f"\n🧵 Threads 조회 실패: {e!r} {body}"[:200])
    top = sorted((p for p in load(POSTS, []) if p["t"].startswith(today) and p.get("pop")), key=lambda p: -p["pop"])[:5]
    if top:  # 10/9 진우 '반응 수치 한눈에': 오늘 올린 딜 중 커뮤니티 반응 높은 순(게시 때 뽐뿌·클리앙 수치)
        lines.append(f"\n🏆 오늘 반응 TOP{len(top)} (게시 때 뽐뿌·클리앙)")
        lines += [f"  · {react(p)} — {clip(parse(title_of(p['text']))[1], 24)}" + (" 🏆" if p.get("hot") else "") for p in top]
    if tg("sendMessage", chat_id=ADMIN, text="\n".join(lines), link_preview_options={"is_disabled": True}):
        seen[key] = time.time()


def load(path, default):
    if path == EVENTS:  # 쿠팡 상품 주소 -> 봇이 만든 파트너스 링크(cp_links.json, 키 있을 때만) — 사이트와 같은 값 · "shelf" 항목 = 사이트 진열 전용(shelf_posts·cp_links·ev_info만 봄 — 채널·Threads·미리보기·토스 쉼·알림 X)
        return [e for e in ev_list(path) if not (isinstance(e, dict) and (e.get("shelf") or e.get("curation")))]  # curation = 큐레이션 글(curation()만 봄 — url 없는 항목이 events()를 멈추지 않게)
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return default


def dkey(title):
    """같은 딜 판단 키: [쇼핑몰]·가격 꼬리(괄호·' / 가격') 떼고 글자·숫자만 앞 24자. 너무 짧으면 None(판단 안 함). 24시간 지나면 같은 상품도 새 딜로 봄."""
    k = re.sub(r"[^0-9a-z가-힣]", "", re.split(r"\s/\s", keyword(title))[0].lower())[:24]
    return "k:" + k if len(k) >= 4 else None


def quiet():
    """마지막 채널 딜 글이 GAP_FILL분(0~8시는 2배 — 10/22 진우 '새벽에도')보다 오래됐으면 True -> 6점 딜로 빈틈 메움."""
    now = time.time() + 9 * 3600
    last = max((p["t"] for p in load(POSTS, []) if not p["text"].startswith("📋") and not p.get("shelf")), default="")
    return last < time.strftime("%Y-%m-%d %H:%M", time.gmtime(now - GAP_FILL * 60 * (2 if time.gmtime(now).tm_hour < 8 else 1)))


ALERT_GAP, QUIET_TH, QUIET_EV = 3 * 3600, 2 * 3600, 20 * 60  # 10/13 01:50 진우 '업로드 안 되면 바로 알람': 같은 단계·오류 알림 간격 · Threads 글 없음(8~24시) · 예약 글 늦음
ALERT_STEPS = {"events": "텔레그램 예약 글", "preview": "22시 미리보기", "top_deals": "지금 살 만한 딜 리스트", "steady_list": "👍 꾸준템 리스트", "pick_post": "Threads 오늘의 픽", "pair_post": "Threads 둘 중 뭐 살래 묶음", "drop_post": "📉 가격 내려간 상품 글", "cp_repost": "쿠팡 자동 재게시", "toss_deals": "토스 회차 글", "toss_picks": "토스 이름 예약 글", "toss_solo": "토스 자동 개별 글", "toss_wait": "토스 커뮤니티 딜(링크 찾은 뒤 게시)",
               "digest": "21시 모아보기", "threads": "21시 Threads 카드", "threads_deals": "Threads 개별 글", "toss_reopen": "재오픈 글", "th_retry": "Threads 묶음 글 재시도",
               "ig_cards": "인스타 카드", "ig_reel": "인스타 릴스", "ig_publish": "인스타 게시",
               "weather_post": "아침 날씨 글", "snack_post": "간식 글", "daily_post": "#일상 Threads 글", "daily_log": "운영 일지", "poll_post": "Threads 가격 투표"}  # 업로드하는 단계(이 단계가 예외로 멈추면 알림)


def err_brief(e):
    """알림용 오류 한 줄: API 오류 message가 있으면 그것, 없으면 repr."""
    m = re.search(r'"(?:message|description)":\s*"([^"]+)"', getattr(e, "body", "") or "")
    return clip(f"{getattr(e, 'code', '')} {m[1]}".strip() if m else repr(e), 160)


def alert(seen, key, text, ch=None, label=None):
    """관리자 텔레그램에 바로 알림 — 같은 key는 ALERT_GAP(3시간)에 1번. ch(th·ig·tg) = 그 채널이 다시 올라가면 '✅ 다시 올라감' 1줄(watch)."""
    now = time.time()
    if ch:
        RUN["failch"].add(ch)
        seen["alert_open"] = {"t": now, "v": {**seen.get("alert_open", {}).get("v", {}), ch: label}}
    if now - (seen.get(key) or {}).get("t", 0) < ALERT_GAP:
        return
    try:
        tg("sendMessage", chat_id=ADMIN, text=text[:3500])
        seen[key] = {"t": now}
    except Exception as e:  # 알림이 실패해도(텔레그램 시간 초과) 실행은 계속 — 안 그러면 seen이 저장 안 돼 같은 글이 다시 올라감(10/17 10:11·10:26 토스 베스트 두 번)
        print("alert", repr(e))


CREDIT_HINT = "Claude API 크레딧이 바닥났어요 — console.anthropic.com → Plans & Billing에서 충전하면 다음 실행부터 다시(그동안 커뮤니티 딜·토스 회차 고르기 멈춤, 예약 글·날씨·투표는 그대로)"


def step_alert(seen, step, e):
    """업로드 단계(ALERT_STEPS)가 예외로 멈춤 -> 바로 알림(단계·오류 종류마다 3시간에 1번). Threads·인스타는 토큰 안내도."""
    name = step.__name__ if step.__name__ != "<lambda>" else next((n for n in step.__code__.co_names if n in ALERT_STEPS), "lambda")  # lambda s: toss_deals(s, "cat") -> toss_deals
    if name not in ALERT_STEPS:
        return
    url = str(getattr(e, "url", "") or getattr(e, "filename", "") or "")
    ch = "ig" if name.startswith("ig_") or "instagram" in url or "facebook" in url else "th" if "threads" in url or name in ("threads", "threads_deals", "toss_reopen", "th_retry") else None
    kind = type(e).__name__ + (f" {e.code}" if isinstance(getattr(e, "code", None), int) else "") + "".join(f" {x}" for x in re.findall(r'"error_subcode":\s*(\d+)', getattr(e, "body", "") or "")[:1])
    label = ALERT_STEPS[name] + {"th": " (Threads)", "ig": "", None: ""}[ch]
    if RUN.get("treuse") and name.startswith("toss_") and not ch and (isinstance(e, RuntimeError) or "toss" in url):  # 토스 점검 중 토스 API 오류(FAIL·토스 주소) = 바로 안 알리고 하루 요약에(10/22 Cowork '알림 폭탄 X') — 그 밖(Claude·코드 오류 등)은 그대로 바로
        tnote(seen, "err", f"{label} {kind}")
        return
    hint = CREDIT_HINT if "credit balance" in (getattr(e, "body", "") or "") else ("인스타 스팸 의심 차단(토큰 문제 아님) — 24시간 쉼, 계속되면 IG_AUTO로 끄기" if "2207051" in (getattr(e, "body", "") or "") else "IG_TOKEN 만료(60일)면 앱 대시보드에서 토큰 다시 생성 → README 세팅 6-2") if ch == "ig" else threads_hint(e) if ch == "th" else "다음 실행(14분 뒤)에 다시 시도해요"
    alert(seen, f"alert_{name}_{kind.replace(' ', '_')}", f"⚠️ {label} 게시 실패: {err_brief(e)}\n{hint}", ch, label)


def th_ok(r, top=True):
    """Threads 글·댓글이 올라감 -> 이번 실행 기록(watch: '✅ 다시 올라감'·2시간 글 없음 감시). top = 글(댓글 X) -> id를 th_verify가 계정 글 목록에서 확인."""
    RUN["ok"].add("th")
    RUN["th_last"] = time.time()
    if top and isinstance(r, dict) and r.get("id"):
        RUN.setdefault("thids", []).append([time.time(), str(r["id"])])
        print("th ok", r["id"])
    return r


TH_VERIFY_MIN = 10 * 60  # 올린 지 10분 지난 글부터 계정 글 목록에서 확인


def th_verify(seen):
    """10/23 저녁 Cowork: 18:16 뒤 Threads 글이 프로필에 안 보임(봇은 올렸다고 기록·오류 0) -> 실행마다 계정 글 목록(/me/threads 최근 25개, 호출 1번)의 위 3개를 로그로 +
    올린 지 10분~24시간 된 우리 글 id(seen thids)가 목록에 없으면 관리자 알림(3시간에 1번 — 계정 제한·검토 확인). 목록 밖으로 밀려난 옛 글은 안 셈."""
    tok, now = E.get("THREADS_TOKEN"), time.time()
    st = seen.setdefault("thids", {"l": []})
    st["t"], st["l"] = now, [x for x in st["l"] + RUN.get("thids", []) if now - x[0] < 86400][-30:]
    if not tok:
        return
    ds = json.loads(http(f"{THREADS}/me/threads?fields=id,timestamp,permalink,text&limit=25&access_token={tok}")).get("data") or []
    ts = lambda x: datetime.strptime(x["timestamp"], "%Y-%m-%dT%H:%M:%S%z").timestamp()
    for x in ds[:3]:
        print("th 계정 최근 글", time.strftime("%m/%d %H:%M", time.gmtime(ts(x) + 9 * 3600)), x.get("permalink", ""), (x.get("text") or "")[:24].replace("\n", " "))
    have, edge = {str(x.get("id")) for x in ds}, (min(map(ts, ds)) if len(ds) >= 25 else 0)
    miss = [(t, i) for t, i in st["l"] if now - t > TH_VERIFY_MIN and t >= edge and i not in have]
    if miss:
        print("th 계정 목록에 없음", len(miss), "개:", " ".join(f"{time.strftime('%H:%M', time.gmtime(t + 9 * 3600))} {i}" for t, i in miss))
        alert(seen, "alert_thmiss", f"⚠️ Threads에 올렸다고 기록된 글 {len(miss)}개가 계정 글 목록에 없음(첫 글 {time.strftime('%m/%d %H:%M', time.gmtime(miss[0][0] + 9 * 3600))}) — "
                                     f"Meta가 지웠거나 계정 제한일 수 있음. Threads 앱 → 설정 → 계정 → 계정 상태 확인")


METRICS, METRICS_HOUR, METRICS_KEEP = "metrics.json", 5, 14  # 10/15 진우 '데이터 계획 1단계': 매일 5시 넘은 첫 실행에 어제 글별 조회·반응 -> metrics.json(최근 14일, 그 전은 git 기록) — 아침 08:30 보고가 Chrome 없이 읽음
PRICE_BANDS = ((10000, "~1만"), (30000, "1~3만"), (50000, "3~5만"), (100000, "5~10만"))  # 가격대(넘으면 '10만~', 못 읽으면 '')
TOP, TOP_DAYS, TOP_SHARE, TOP_FILL, TOP_BONUS, TOP_BONUS_DAY = "top.json", 14, 0.2, 40, 1, 2  # 10/22 진우 '잘 되는 제품은 꾸준하게': 잘 된 상품 표(top_build) — 지난 14일 Threads 개별 글 상위 20% · 예전 줄 채우기 한 실행 40개 · 토스 후보 가산 +1점 하루 2번까지
NOT_PROD = r"^https?://(?:[\w-]+\.)*(?:ppomppu\.co\.kr|ruliweb\.com|clien\.net|quasarzone\.com|fmkorea\.com|t\.me)(?:[/?#]|$)"  # 상품 링크 아님(커뮤니티 출처·채널)
TH_AB_START = "2026-10-18"  # 이날부터 Threads 개별 딜 글은 전부 thab 기록(metrics 줄 ab) -> ab 없는 Threads 글 = 개별 딜 아님(미리보기·카드 모음 등)


def tg_num(v):
    """채널 웹 숫자 '1.2K'·'3M'·'15' -> 정수."""
    v = v.strip().replace(",", "")
    return int(float(v[:-1]) * {"K": 1000, "M": 10 ** 6}[v[-1]]) if v[-1:] in ("K", "M") else int(v)


def metrics_save(m):
    js = lambda x: json.dumps(x, ensure_ascii=False)
    open(METRICS, "w", encoding="utf-8").write("{" + ",\n".join(f'{js(d)}: {{"at": {js(v["at"])}, "miss": {js(v["miss"])}, ' + "".join(f'{js(k)}: {js(x)}, ' for k, x in v.items() if k not in ("at", "miss", "rows"))  # igf·igw(인스타 팔로워·7일 요약)
                                                                 + '"rows": [\n' + ",\n".join(map(js, v["rows"])) + "]}"
                                                                 for d, v in sorted(m.items(), reverse=True)[:METRICS_KEEP]) + "}\n")  # 최신 날짜 맨 위 · 글 1개 = 1줄(보고가 읽기 쉽게)


def prod_cols(title, cat, links, ids, deal=None):
    """metrics 줄 상품 칸(10/22 Cowork — 어떤 상품 글이 잘 됐는지 잇기): kind = deal(상품 1개 글)·list(묶음·목록 = urls)·etc(투표·날씨·#일상·미리보기 등),
    url·name(상품명) · tid = 토스 상품 id(우리가 만든 쉐어링크 — 쉐어링크는 만들 때마다 주소가 달라 상품은 id로 묶음).
    deal = True(Threads 개별 딜 글 — th_deal 기록, B 글은 링크를 못 읽어도 이름으로) / False(개별 딜 아님) / None(모름 = 링크 수로). 사이트 첫 화면·블로그·골드박스·쿠팡 홈 링크는 상품 X."""
    junk = lambda u: re.search(NOT_PROD, u) or u.startswith((BLOG, GOLDBOX, CP_HOME, CP_FRESH)) or u.startswith(SITE) and "/p/" not in u
    ls = [u for u in dict.fromkeys(links) if u and not junk(u)]
    kind = "deal" if deal else "etc" if cat in ("투표", "날씨", "달력") or not ls else "list" if cat == "묶음" or len(ls) > 1 else "etc" if deal is False else "deal"
    if kind == "etc":
        return {"kind": kind}
    if kind == "list":
        return {"kind": kind, "name": clip(title, 40), "urls": ls}
    return {"kind": kind, "name": parse(title)[1], **({"url": ls[0], **({"tid": ids[ls[0]]} if ls[0] in ids else {})} if ls else {})}


OWN_END_GAP, OWN_END_RES, OWN_END_SEC = 12 * 3600, 20, 30  # 10/23 진우 '사이트에서 판매 중이면 없애지 마': 진우 토스 상품마다 판매 확인 간격(하루 2번) · 한 실행에 단축 링크(/_m/) 푸는 최대 수·시간(초)
TS_REV, TS_REV2, TS_SCORE = 1000, 300, 4.7  # 토스 꾸준템(10/23 진우 '특가는 끝났지만 꾸준하게 팔리는 상품'): 리뷰 1,000개↑ 또는 평점 4.7↑·리뷰 300개↑(👍 꾸준템과 같은 결)


def toss_steady(x):
    """토스 상세 API 상품이 꾸준히 팔리는지(TS_REV·TS_REV2·TS_SCORE). 상세 API엔 판매량 칸이 없어 리뷰 수·평점으로."""
    n = x.get("reviewCount") or 0
    return n >= TS_REV or n >= TS_REV2 and (x.get("reviewScore") or 0) >= TS_SCORE


CPS_HOUR, CPS_DAYS, CPS_GC_PAGES = 5, 14, 5  # E(10/24 진우 '반응 좋은 품목 자동 재게시'): 반응 점수 하루 1번(5시~ KST) — 쿠팡 주문 리포트 1번 + GoatCounter 14일(쪽 100개씩 최대 5번)
CPRE_HOURS, CPRE_SPAN, CPRE_DAYS, CPRE_FRESH = (12, 18), 2, 3, 24 * 3600  # 자동 재게시 = 12·18시 칸 1개씩(그 시각부터 2시간 안 — 12·18시는 TOP·토스 묶음 글이 몰려 10분 간격에 밀리기 쉬움) · 같은 상품(url·pid) 3일 · 가격 확인 24시간 안만
OWN_HOT_PCT = 5  # 🔥 특가 중 = 지금 가격 ≤ 목표가 +5%(10/23 진우)
REHOT_OFF = {"https://link.coupang.com/a/hRRpHJxXBA": "2026-10-25"}  # 가짜 🔁 다시 특가(url: 그날 rehot만 지움, 🔥 그대로) — 10/25 Cowork 페리오 치약: events now가 10개 묶음 가격을 잘못 짝지어 ⏳로 보였음(1개 가격은 소개 때 그대로)


def won_of(s):
    """'9,900원 · 5천원 쿠폰가' -> (9900, 쿠폰 5000) — 가격 못 읽으면 (None, 0)."""
    m = re.search(r"\d[\d,]*(?=\s*원)", s or "")
    cp = re.search(r"(\d+)\s*천\s*원\s*쿠폰|([\d,]+)\s*원\s*쿠폰", s or "")
    return (int(m[0].replace(",", "")) if m else None), (cp and (int(cp[1]) * 1000 if cp[1] else int(cp[2].replace(",", ""))) or 0)


def own_end(seen):
    """진우 상품 진열 상태(10/23 진우 '진열 = 기본 유지' · '지금 특가가 아닌 제품은 특가를 기다릴 제품으로 알려주고, 나중에 특가가 되면 다시 특가 제품으로') — url마다(같은 url 진우 글 전부에) posts에:
    st = hot 🔥 특가 중(지금가 ≤ 목표가 +OWN_HOT_PCT%) | wait ⏳ 특가 대기(판매 중, 그보다 비쌈 · 목표가 없으면 🔥 X) | out 일시 품절 | gone 빼기(토스 '조회 안 됨' 서로 다른 날 연속 3번 · events end + why gone/issue — 이 2가지뿐),
    tgt = 목표가(처음 🔥로 소개한 진우 글 가격, 🔥 글이 없으면 events target), now = 지금가(쿠팡·네이버만 = events now — 토스 API 가격은 posts·사이트 X, API 신청 범위), chk = 확인 시각,
    stdy = 👍 꾸준템(토스 = 리뷰 toss_steady, 쿠팡·네이버 = 👍 글), rehot = ⏳ -> 🔥 된 날(사이트 🔁 배지 · 토스는 seen rehot 줄 -> toss_solo '🔁 다시 특가' 글),
    std·stp = st가 바뀐 날·앞 st(10/24) · cpp·cpt = 옵션을 맞춘(events item 또는 이름 수량·용량) 쿠팡 검색 API 가격·시각(10/24 — 사이트 📉·drop_check).
    토스 = 상세 API(실행마다 1번, 마지막 확인이 OWN_END_GAP 지난 id 30개까지 — 단축 링크 -> id는 seen tossid에 1번, 확인 뒤 다시 올린 글은 바로) · 쿠팡·네이버 = events 진우 항목 now·chk·target·end·why(Cowork).
    seen tossid m[url] = [상품 그룹 id(tacaId = 주소 /t/번호), 푼 시각, 마지막 확인, 'ok'|'out', 조회 안 됨 날짜들, 지금가(내부 — 1일 캐시), 꾸준템, 대표 옵션 id(tacaItemId)]
    — 상세는 tacaIds로(10/23: 그 전엔 tacaItemIds로 물어 대부분 '조회 안 됨' = 잘못된 일시 품절 → 8칸 아닌 기록은 다시 확인, 그 상태로는 🔁 X)."""
    now = time.time()
    kst = time.gmtime(now + 9 * 3600)
    posts, today = load(POSTS, []), time.strftime("%Y-%m-%d", kst)
    stale = lambda u: re.search(DAY_ONLY, posts[urls[u][-1]]["text"]) and posts[urls[u][-1]]["t"][:10] < today and (ti.get(u, [0, 0, 0])[2] or 0) < kst_ts(posts[urls[u][-1]]["t"][:10] + " 00:00") + 86400  # 하루특가·선착순 = 그날(글 날짜) 밤 12시 전 확인은 끝난 특가 가격(10/23 리뷰 — 오늘 0시 기준이면 매일 밤 다시 ⏳)
    urls = {}
    for i, p in enumerate(posts):
        if p.get("own") and p.get("url") and not p["text"].startswith("📋"):
            urls.setdefault(p["url"], []).append(i)
    tossy = [u for u in urls if toss_share(u)]
    tt = seen.setdefault("tossid", {"m": {}})
    tt["t"], ti = now, tt["m"]  # seen 정리(t 기준)에서 안 지워지게
    valid = {u for u in tossy if len(ti.get(u, [])) > 7}  # 상품 그룹 id(tacaIds)로 확인한 기록 — 그 전(10/23 새벽까지 tacaItemIds로 잘못 물은 것)은 다시 확인 · 그 상태에서 🔁 X
    if HAS_TOSS:
        for u in [u for u in tossy if u not in ti or not ti[u][0] and now - ti[u][1] > 86400][:OWN_END_RES]:
            if time.time() - now > OWN_END_SEC:
                break
            m = re.fullmatch(r"https://toss\.shopping/t/(\d+)", plain(u) or "")
            ti[u] = [int(m[1]) if m else 0, now, 0]
        by = {}
        for _, u in sorted(((ti[u] + [0])[2], u) for u in tossy if ti.get(u, [0])[0] and ((ti[u] + [0])[2] < max(now - OWN_END_GAP, kst_ts(posts[urls[u][-1]]["t"])) or len(ti[u]) < 8 or stale(u))):  # 이 규칙 전 기록·확인 뒤 다시 올린 글·밤 12시 지난 하루특가도 바로
            if len(by) < 30 or ti[u][0] in by:
                by.setdefault(ti[u][0], []).append(u)
        if by:
            try:
                r = toss("/products/detail?tacaIds=" + ",".join(map(str, by)))  # 쉐어링크 주소 /t/번호 = 상품 그룹 id(tacaId) — 대표 옵션으로 조회(10/23: tacaItemIds로 물어 대부분 '조회 안 됨'이던 것, 공식 문서)
            except Exception as e:  # 터널 끊김 등 = 다음 실행에 다시(상태는 그대로)
                print("own end", repr(e))
                r = None
            got, nf = ({x.get("tacaId"): x for x in r["items"]}, {int(i) for i in r.get("notFoundIds") or []}) if r else ({}, set())
            for i, us in by.items():
                for u in us:
                    x, v = got.get(i), ti[u]
                    if not x and i not in nf:  # 응답에 없음 = 그대로, 다음에
                        continue
                    nfd = [] if x else [d for d in (v[4] if len(v) > 7 else []) if d != today] + [today]  # 조회 안 됨이 이어진 날들(조회되면 처음부터 · 예전 잘못 물은 기록은 버림)
                    v[2:] = [now, "out" if not x or x.get("isSoldOut") else "ok", nfd, x and x["displayPrice"], bool(x and toss_steady(x)), x and x.get("tacaItemId") or (v[7] if len(v) > 7 else 0)]  # v[7] = 대표 옵션 id(tacaItemId — 꾸준템·🔁 글·품절 지켜보기·같은 상품 거르기)
    ev, chk, cpq, cpi = ev_info(), f"{kst.tm_mon}/{kst.tm_mday} {kst.tm_hour}시", seen.get("cpq", {}).get("m", {}), seen.get("cpq", {}).get("i", {})
    rq = seen.setdefault("rehot", {"q": []})
    rq["t"], rq["q"], n, c = now, [q for q in rq["q"] if q.get("g")], 0, collections.Counter()  # g 없는 줄 = 예전(잘못 물은 id) 기록 — 버림
    for u, idxs in urls.items():
        p, tsy = posts[idxs[-1]], u in tossy
        first = next((posts[i] for i in idxs if icon_of(posts[i]["text"]) == "🔥"), None)  # 목표가 = 처음 🔥로 소개한 글 가격
        tp = parse(title_of(first["text"]))[2].split("/")[0].strip() if first else ev.get(u, {}).get("target", "")
        tw, cp = won_of(tp)
        e, v = ev.get(u, {}), ti.get(u, [])
        cq = cpq.get(u) or []
        cq = not tsy and e.get("pid") and (cq[2:3] == [e["item"]] if e.get("item") else cq[2:3] in ([], [""]) and re.search(CP_QTY, parse(title_of(p["text"]))[1], re.I)) and cq  # item = 그 itemId로 맞춘 가격만(약한 이름 매칭 캐시 X — 10/24 리뷰)  # 옵션을 맞춘 검색 가격만(10/24 Cowork: 이름에 수량·용량 글자가 없으면 cp_same이 약함 — 'AMUSE 젤핏 틴트 05' 179,300원·'롬앤 쥬시 틴트 04' 10,630원이 지금 가격으로)
        if cq and cq[0] and cq[1] > e.get("chk", "") and not re.search(r"쿠폰|와우", e.get("now", "")):  # ② 봇 검색 API 가격(cp_price)이 Cowork 확인보다 새것이면 그것(검색 가격엔 쿠폰·와우가 없음 -> Cowork 쿠폰·와우 가격은 그대로)
            e = {**e, "now": f"{cq[0]:,}원", "chk": cq[1]}
        f = {"tgt": tp} if tw else {}
        if cq and cq[0]:
            f.update(cpp=int(cq[0]), cpt=cq[1])  # 검증된 쿠팡 API 가격·시각(10/24 Cowork — 사이트 📉·drop_check 근거, 지금 가격을 덮었든 아니든)
        if e.get("end", "") >= p["t"][:10] and e.get("why", "gone") in ("gone", "issue"):
            f["st"] = "gone"
        elif tsy and len(v) > 7:
            f.update(st="gone" if len(v[4]) >= 3 else "out" if v[3] == "out" else "hot" if tw and not stale(u) and v[5] <= (tw + cp) * (100 + OWN_HOT_PCT) / 100 else "wait",
                     chk=(lambda k: f"{k.tm_mon}/{k.tm_mday} {k.tm_hour}시")(time.gmtime(v[2] + 9 * 3600)))
            if v[6]:
                f["stdy"] = 1
            if f["st"] == "wait" and stale(u):
                f["stl"] = 1  # 밤 12시 전 확인이라 대기 = 다음 확인에 🔥여도 '다시 특가' X
        elif not tsy and e.get("why") == "out" and e.get("end", "") >= p["t"][:10]:  # 쿠팡·네이버 일시 품절 = events end + why out(Cowork 확인)
            f.update(st="out", chk=f"{int(e['end'][5:7])}/{int(e['end'][8:10])}")
        elif not tsy and e.get("now") and (p.get("shelf") or p.get("re") or e.get("chk", "") >= p["t"][:16]):  # re = E 자동 재게시(그 확인 가격으로 올린 글)  # 진우가 다시 올린 글보다 옛 확인은 X(10/23 리뷰) — 사이트 진열 글은 같은 events 항목이라 그대로
            nw = won_of(e["now"])[0]
            f.update(st="hot" if tw and nw and nw <= tw * (100 + OWN_HOT_PCT) / 100 else "wait", now=e["now"], chk=S_md_h(e.get("chk", "")), chkt=e.get("chk", ""))  # chkt = 보이는 가격의 확인 시각 그대로(E 재게시 24시간 판단 — 쿠폰·와우는 Cowork 확인 시각)
        else:  # 확인 전 = 아이콘대로(토스 하루특가·선착순 날 지남 = 대기 + stl: 첫 확인에 🔥여도 '다시 특가' X — 10/23 리뷰)
            day_end = tsy and re.search(DAY_ONLY, p["text"]) and p["t"][:10] < today
            f["st"] = "hot" if icon_of(p["text"]) == "🔥" and not day_end else "wait"
            if day_end:
                f["stl"] = 1
        if not tsy and any(icon_of(posts[i]["text"]) == "👍" for i in idxs):
            f["stdy"] = 1
        f["rehot"] = today if p.get("st") == "wait" and not p.get("stl") and f["st"] == "hot" and (not tsy or u in valid) else p.get("rehot")  # 토스 = 앞 상태도 맞는 id로 확인한 것일 때만
        if REHOT_OFF.get(u) == f["rehot"]:
            f["rehot"] = None
        pv = next((posts[i] for i in reversed(idxs) if posts[i].get("st")), {})  # 앞 상태 = st가 있는 최신 글(막 다시 올린 글엔 st 없음 — 기록 안 잃게)
        f["std"], f["stp"] = (today, pv["st"]) if pv.get("st") and pv["st"] != f["st"] else (pv.get("std"), pv.get("stp"))  # 상태 바뀐 날·앞 상태(10/24 Cowork 사이트 '특가 끝(hot→wait)'·'판매 종료(→gone)' 최근 3일) — 첫 판단은 X
        if f["rehot"] == today and p.get("rehot") != today and tsy and not p.get("shelf") and len(v) > 7 and v[7]:  # 토스 ⏳ -> 🔥 = 채널·Threads '🔁 다시 특가' 줄(toss_solo — 같은 상품 3일 간격, id = 대표 옵션)
            rq["q"] = [q for q in rq["q"] if q["id"] != v[7]] + [{"id": v[7], "g": v[0], "u": u, "tgt": tp, "d": today, "n": parse(title_of(p["text"]))[1]}]
        if not tsy and (im := e.get("pid") and cpi.get(u) or img_of({**p, "img": e.get("img")})):
            f["img"] = im  # 쿠팡 상품 사진(cp_price) > events img(10/25 Cowork ② — 쿠팡 사진 주소만, img_of) — 캐시가 비어도 글의 옛 사진은 그대로(아래 지우는 칸에 없음)
        f = {k: x for k, x in f.items() if x}
        c[f["st"]] += 1
        for i in idxs:
            q = posts[i]
            was = {k: q.get(k) for k in ("st", "tgt", "now", "chk", "chkt", "stdy", "rehot", "stl", "std", "stp", "cpp", "cpt", "end", "tst", "ts", "img")}
            for k in ("st", "tgt", "now", "chk", "chkt", "stdy", "rehot", "stl", "std", "stp", "cpp", "cpt", "end", "tst", "ts"):  # end·tst·ts = 예전 규칙(10/23 새벽) 칸 — 지움
                q.pop(k, None)
            q.update(f)
            n += was != {k: q.get(k) for k in was}
    rq["q"] = [q for q in rq["q"] if q["d"] >= time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600 - 2 * 86400))]  # 3일 지난 다시 특가는 안 올림
    if n:
        json.dump(posts, open(POSTS, "w"), ensure_ascii=False)
    if n or HAS_TOSS and by:
        print("own end", f"진우 상품 {len(urls)}개(토스 {len(tossy)}) · 🔥 {c['hot']} · ⏳ {c['wait']} · 일시 품절 {c['out']} · 뺌 {c['gone']} · 글 바꿈 {n}" + (f" · 토스 이번 확인 {len(by)}개" if HAS_TOSS else ""))
    ph = collections.Counter((shop_of(posts[ix[-1]]), any(posts[i].get("img") for i in ix)) for ix in urls.values() if posts[ix[-1]].get("st") != "gone")
    mr = [f"{n} {ph[(k, True)]}/{ph[(k, True)] + ph[(k, False)]}" for k, n in (("coupang", "쿠팡"), ("naver", "네이버"))]
    print("사진", " · ".join(mr) + " · 토스 X(규칙)")  # 몰별 사진 비율(10/24 Cowork A⑤ — 정기 점검 README 줄)
    il = seen.setdefault("imgl", {})
    if il.get("d") != today:  # 하루 1줄(10/25 Cowork ③): 몰 + 품목 칸(/c/ 주소 — 진우 상품 전체, 토스·네이버 포함 = 사이트에 보이는 비율)
        il.update(d=today, t=now)
        cc = collections.Counter((cat_of(posts[ix[-1]]), any(posts[i].get("img") for i in ix)) for ix in urls.values() if posts[ix[-1]].get("st") != "gone")
        print("img", " · ".join(mr + ["토스 X"] + [f"{m[0]} {cc[(k, True)]}/{cc[(k, True)] + cc[(k, False)]}" for k, m in CAT_META.items() if cc[(k, True)] + cc[(k, False)]]))


DROP_PCT, DROP_AT = 30, "09:30"  # 옵션 바뀜 의심(10/24 Cowork): 첫 글 가격보다 30%↓인데 API 확인 X -> 하루 1번 관리자 DM(9:30~ KST)


def drop_rows(posts, ev, now_ts):
    """쿠팡·네이버 진우 상품(url마다 최신 진우 글 — gone·out·📋 X)의 가격 내림 -> [(i, p, base, nowp, pct, verified)] — pct ≥ 3 · 확인(chkt) 24시간 안만.
    base = 그 url 첫 진우 글 제목 가격, nowp = 지금 확인 가격(p now 첫 숫자) · verified = 옵션 맞춘 API 가격(cpp)이 48시간 안(cpt)이고 지금가 ±5% 또는 base×0.7 이하.
    ev(ev_info) = 사이트(build_site) 쪽과 같은 모양 — 여기선 안 씀. 사이트도 같은 계산을 따로 씀."""
    first, last = {}, {}
    for i, p in enumerate(posts):
        if p.get("own") and p.get("url") and not p["text"].startswith("📋") and shop_of(p) in ("coupang", "naver"):
            first.setdefault(p["url"], p)
            last[p["url"]] = i
    out = []
    for u, i in last.items():
        p = posts[i]
        base, nowp = won_of(parse(title_of(first[u]["text"]))[2])[0], won_of(p.get("now"))[0]
        if p.get("st") in ("gone", "out") or not base or not nowp or not re.match(AT_RX, p.get("chkt") or "") or kst_ts(p["chkt"]) < now_ts - 86400:
            continue
        pct = round((base - nowp) * 100 / base)
        if pct >= 3:
            cpp = p.get("cpp")
            out.append((i, p, base, nowp, pct, bool(cpp and re.match(AT_RX, p.get("cpt") or "") and kst_ts(p["cpt"]) >= now_ts - 48 * 3600 and (abs(cpp - nowp) <= nowp * 0.05 or cpp <= base * 0.7))))
    return out


def drop_check(seen):
    """하루 1번(DROP_AT~ KST, seen dropchk) 관리자 DM: drop_rows 중 ▼DROP_PCT%↑ + API 확인 X = 옵션 바뀜 의심(가격 = DM에만, 로그엔 pid·%만) · 없으면 DM X."""
    now = time.time()
    kst = time.gmtime(now + 9 * 3600)
    today = time.strftime("%Y-%m-%d", kst)
    if time.strftime("%H:%M", kst) < DROP_AT or seen.get("dropchk", {}).get("d") == today:
        return
    old, ev = set(seen.get("dropchk", {}).get("k") or []), ev_info()
    rows = sorted((r for r in drop_rows(load(POSTS, []), ev, now) if r[4] >= DROP_PCT and not r[5]), key=lambda r: -r[4])
    seen["dropchk"] = {"t": now, "d": today, "k": [f"{r[1]['url']}|{r[3]}" for r in rows]}
    rows = [r for r in rows if f"{r[1]['url']}|{r[3]}" not in old]  # 어제 알린 같은 줄(같은 지금가) = 다시 X(네이버는 API 확인이 없어 매일 나옴)
    pid = lambda p: ev.get(p["url"], {}).get("pid")
    for _, p, _, _, pct, _ in rows:
        print(f"drop check {pid(p) or '-'} ▼{pct}% 옵션 확인 필요")
    if rows:
        nv = any(shop_of(r[1]) == "naver" for r in rows)
        tg("sendMessage", chat_id=ADMIN, text="\n".join(f"· {parse(title_of(p['text']))[1][:24]} {base:,}→{nw:,}원 ▼{pct}%" + (f" (pid {pid(p)})" if pid(p) else " (네이버)" if shop_of(p) == "naver" else "") for _, p, base, nw, pct, _ in rows[:20])
           + "\n옵션 바뀜 의심 — 사이트 📉 칸엔 안 올림. " + " · ".join(x for x in ("쿠팡 = events item(옵션 itemId) 확인해 줘" if any(shop_of(r[1]) != "naver" for r in rows) else "", "네이버 = API 확인이 없어 가격·구성만 봐 줘" if nv else "") if x))


CAT_FILL_N = 60  # 한 실행에 Claude로 품목 칸 채우는 글 수(진우 상품 처음 채울 때 ~100개 = 2번)
CAT_PROMPT = ("아래 상품마다 쇼핑 사이트 품목 칸 하나를 골라 cats 배열로 답해(순서 그대로, 상품 수만큼). food = 식품·음료·건강식품·영양제, snack = 과자·간식, season = 제철 과일·해산물·겨울 먹거리, life = 생필품(휴지·위생·욕실 소모품), "
              "kitchen = 주방 용품·소모품(조리 도구·그릇·랩·수세미), laundry = 세탁(세제·유연제·빨래 용품), women = 여성용품(생리대 등), beauty = 화장품·뷰티·헤어·바디, home = 생활·청소·욕실 용품·가구·공구, fashion = 패션·잡화·신발·가방, digital = 가전·디지털, heat = 겨울 난방·방한(핫팩·전기요 등), etc = 그 밖.\n")


def cat_fill(seen):
    """사이트 품목 칸(build_site.SHELF_CATS, 10/23 진우 '사이트에도 제품 카테고리 구분'): 제목 정규식에 안 맞는 글(진우 상품 전부 + 최근 3일 커뮤니티 딜)은
    Claude 한 번에 한 단어씩(CAT_PROMPT) 받아 글 cat에 저장(etc = 칸 없음, 한 번만). 실패·개수 다름 = 다음 실행에 다시."""
    posts = load(POSTS, [])
    since = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600 - 3 * 86400))
    todo = [p for p in posts if not p["text"].startswith("📋") and "cat" not in p and not cat_of(p) and (p.get("own") or p["t"][:10] >= since)][-CAT_FILL_N:]
    if not todo or not E.get("ANTHROPIC_API_KEY"):
        return
    keys = [k for k, _, _ in SHELF_CATS] + ["etc"]
    try:
        cats = ai_json(CAT_PROMPT + "\n".join(f"{k + 1}. {parse(title_of(p['text']))[1]}" for k, p in enumerate(todo)), {"cats": {"type": "array", "items": {"type": "string", "enum": keys}}})["cats"]
    except Exception as e:
        print("cat fill", repr(e))
        return
    if len(cats) != len(todo):
        print("cat fill", f"개수 다름 {len(cats)}/{len(todo)}")
        return
    for p, c in zip(todo, cats):
        p["cat"] = c
    json.dump(posts, open(POSTS, "w"), ensure_ascii=False)
    print("cat fill", len(todo), dict(collections.Counter(cats)))


TOSS_LIST, TOSS_LIST_AT = "toss_list.json", ("07:00", "08:00")  # 10/23 진우 '토스도 리스트 관리 잘하고 꾸준하게': 매일 아침 8시 전(Cowork 8:30 보고)


def toss_roster(seen):
    """매일 TOSS_LIST_AT(KST) 1번: 진우 토스 상품 전부(같은 url 최신 진우 글, own_end 상태) -> toss_list.json(저장소가 공개라 토스 API 지금 가격·리뷰 수는 X — API 신청 범위):
    {at, n: {hot·wait·out·gone 수}, rehot: 어제·오늘 🔁 다시 특가 된 이름, gone: 빠진 이름, new: {날짜: 그날 채널에 새로 나간 토스 상품 수(토스 API 글 tb_ + 진우 토스 글), 최근 7일},
     items: [{n, st, tgt 목표(올린) 가격, chk 확인 시각, stdy 👍, last 마지막 채널 게시일, url}]} — 🔥 → ⏳ → 일시 품절 → 뺌 순."""
    now = time.time()
    kst = time.gmtime(now + 9 * 3600)
    key = time.strftime("tlist_%Y%m%d", kst)
    if not TOSS_LIST_AT[0] <= time.strftime("%H:%M", kst) < TOSS_LIST_AT[1] or key in seen:
        return
    seen[key] = now
    posts, ti = load(POSTS, []), seen.get("tossid", {}).get("m", {})
    day = lambda t: time.strftime("%Y-%m-%d", time.gmtime(t + 9 * 3600))
    yd = day(now - 86400)
    tb = {int(k[3:]): v["t"] for k, v in seen.items() if k.startswith("tb_") and isinstance(v, dict) and k[3:].isdigit()}  # 토스 id -> 채널에 마지막으로 올린 시각(3일 안)
    last, dates = {}, {}
    for p in posts:
        if p.get("own") and toss_share(p.get("url")):
            last[p["url"]] = p
            dates.setdefault(p["url"], []).append(p["t"][:10])
    items = [{"n": parse(title_of(p["text"]))[1], "st": p.get("st", ""), "tgt": p.get("tgt", ""), "chk": p.get("chk", ""), "stdy": bool(p.get("stdy")),
              "last": max(dates[u] + ([day(tb[ti[u][7]])] if len(ti.get(u, [])) > 7 and ti[u][7] in tb else [])), "url": u} for u, p in last.items()]
    items.sort(key=lambda x: ({"hot": 0, "wait": 1, "out": 2, "gone": 3}.get(x["st"], 1), not x["stdy"]))
    old = load(TOSS_LIST, {})
    new = {d: n for d, n in {**old.get("new", {}), yd: sum(day(t) == yd for t in tb.values()) + sum(d == yd for ds in dates.values() for d in ds)}.items() if d > day(now - 8 * 86400)}
    out = {"at": time.strftime("%Y-%m-%d %H:%M", kst), "n": dict(collections.Counter(x["st"] or "wait" for x in items)), "rehot": [parse(title_of(p["text"]))[1] for p in last.values() if (p.get("rehot") or "") >= yd],
           "gone": [x["n"] for x in items if x["st"] == "gone"], "new": new, "items": items}
    json.dump(out, open(TOSS_LIST, "w"), ensure_ascii=False, indent=1)
    print("toss roster", out["n"], "| 어제 새 토스 상품", new.get(yd), "| 다시 특가", len(out["rehot"]))


def toss_ids(seen):
    """우리 토스 쉐어링크 -> 상품 id(toss_link가 만든 것 전부 — 같은 상품을 다시 만들어도 옛 링크 그대로)."""
    return {k: v[0] for k, v in seen.get("tlink", {}).get("r", {}).items()}


def th_views(tok, i):
    """Threads 글·댓글 1개 조회수(insights views)."""
    return next(((x.get("total_value") or x["values"][0])["value"] for x in json.loads(http(f"{THREADS}/{i}/insights?metric=views&access_token={tok}"))["data"]), None)


def th_ab_48(seen):
    """A/B 시험 글이 올린 지 48시간 지나면(실행마다 확인) 1번: 글 조회(B는 링크 댓글 조회도) -> metrics.json 그 글 줄에 v48·rv48(10/25 A·B 글당 조회 비교)."""
    tok, mm, now = E.get("THREADS_TOKEN"), seen.get("thab", {}).get("m", {}), time.time()
    due = [(k, v) for k, v in mm.items() if "v48" not in v and now - v["ts"] >= 48 * 3600]
    if not tok or not due:
        return
    m = load(METRICS, {})
    for k, v in due:
        try:
            v.update(v48=th_views(tok, k), **({"rv48": th_views(tok, v["r"])} if v.get("r") else {}))
        except Exception as e:  # 지운 글·권한 -> 빈 칸으로 끝(다시 안 물음)
            v["v48"] = None
            print("th ab 48h", k, repr(e))
        for r in (r for d in m.values() for r in d["rows"] if r["ch"] == "th" and r["id"] == k):
            r.update(v48=v["v48"], **({"rv48": v.get("rv48")} if v.get("r") else {}))
    metrics_save(m)
    print("th ab 48h", [(v["ab"], v["v48"], v.get("rv48")) for _, v in due])


def metrics(seen):
    """성과 숫자: A/B 48시간 조회(th_ab_48) → 어제 글별 성과(metrics_rows) → 잘 된 상품 표(top_build)."""
    th_ab_48(seen)
    metrics_rows(seen)
    top_build(seen)
    cp_score(seen)


def metrics_rows(seen):
    """하루 1번 어제(KST) 글별 성과 -> metrics.json {날짜: {"at", "miss": {채널: 빈 칸 이유}, "rows": [{date, ch, id, shop, cat, price, at, views, react, (likes, replies)}]}}.
    텔레그램(tg) = 채널 웹(t.me/s) 조회·반응(posts.json 글이면 그 글·링크로 몰·품목), Threads(th) = 글 목록 + insights(views·likes·replies·reposts·quotes),
    인스타(ig) = 미디어 목록(좋아요·댓글) + insights(views). 못 읽은 칸 = None, 이유는 miss(권한 없음 등). 수동 실행에 METRICS_DAY(YYYY-MM-DD)면 그날을 바로(점검·다시 모으기).
    tg·th 줄엔 상품 칸(prod_cols — kind·url·name·tid, 목록은 urls)도."""
    now = time.time()
    day = E.get("METRICS_DAY") or (time.gmtime(now + 9 * 3600).tm_hour >= METRICS_HOUR and time.strftime("%Y-%m-%d", time.gmtime(now - 15 * 3600)))
    if not day or "mt_" + day in seen and not E.get("METRICS_DAY"):
        return
    t0 = kst_ts(day + " 00:00")
    rows, miss, stamp = [], {}, lambda x: datetime.strptime(x, "%Y-%m-%dT%H:%M:%S%z").timestamp()
    soft = []  # 일시 오류(네트워크·5xx) -> 그날은 아직 안 끝남(8시까지 다음 실행에 다시), 4xx(권한 등)는 다시 해도 같음
    blame = lambda e: soft.append(isinstance(e, OSError) and not (isinstance(e, urllib.error.HTTPError) and e.code < 500)) or err_brief(e)
    denied = lambda e: re.search(r'"code":\s*(10|190|200)\b', getattr(e, "body", "") or "")  # 권한 없음·토큰 = 나머지 글도 같음 -> 그만 물음, 그 밖(지운 글·빈 응답)은 그 글만 빈 칸

    ids = toss_ids(seen)  # 우리 토스 쉐어링크 -> 상품 id

    def row(ch, i, text, url, t, views, react, title=None, links=None, deal=None, **more):
        title = title or title_of(text)
        w = price_won(title)
        cat = "투표" if text.startswith("🗳️") else "달력" if text.startswith("🗓 앞으로") else "날씨" if re.search(r"^☁️", text, re.M) else "묶음" if re.search(r"2️⃣|^2\. |핫딜픽이 고른 \d+개", text, re.M) else next((n.split()[-1] for _, n, rx in CATS if re.search(rx, title)), "식품" if re.search(FOOD, title) else "기타")
        rows.append({"date": day, "ch": ch, "id": i, "shop": shop_of({"text": text, "url": next((u for u in links or [] if u and not re.search(NOT_PROD, u)), url) if (url or "").startswith("https://t.me/") else url}) or "기타", "cat": cat,
                     "price": "" if w is None else next((n for b, n in PRICE_BANDS if w <= b), "10만~"), "at": time.strftime("%H:%M", time.gmtime(t + 9 * 3600)), "views": views, "react": react, **more,
                     **(prod_cols(title, cat, links, ids, deal) if links is not None else {})})

    pm, url, n = {p["mid"]: p for p in load(POSTS, []) if p.get("mid")}, CHANNEL_WEB, 0
    try:
        while url and n < 40:  # 한 쪽 20개, 오래된 쪽으로(?before=)
            n += 1
            bs = [(int(m[1]), stamp(t[1]), b) for b in http(url).split('<div class="tgme_widget_message_wrap')[1:]
                  for m, t in [(re.search(r'data-post="[^"]+/(\d+)"', b), re.search(r'<time datetime="([^"]+)"', b))] if m and t]
            for mid, t, b in bs:
                if t0 <= t < t0 + 86400:
                    p, tx = pm.get(mid), re.search(r'js-message_text[^"]*"[^>]*>(.*?)</div>', b, re.S)  # 답장 글의 인용(js-message_reply_text) 말고 본문
                    btn, v = re.search(r'inline_button url_button" href="([^"]+)"', b), re.search(r'tgme_widget_message_views">([^<]+)<', b)
                    rx = re.findall(r"(?:</i>|</tg-emoji>)\s*([\d.,]+[KM]?)\s*</span>", b.split("tgme_widget_message_reactions", 1)[1]) if "tgme_widget_message_reactions" in b else []  # 이모지 뒤 숫자(맞춤 이모지 포함)
                    row("tg", mid, p["text"] if p else html.unescape(re.sub(r"<[^>]+>", "", re.sub(r"<br\s*/?>", "\n", tx[1]))) if tx else "",
                        p and p.get("url") or btn and html.unescape(btn[1]) or "", t, v and tg_num(v[1]), sum(map(tg_num, rx)),
                        links=[p and p.get("url")] + [html.unescape(u) for u in re.findall(r'inline_button url_button" href="([^"]+)"', b) + re.findall(r'href="([^"]+)"', tx[1] if tx else "")],
                        **({"tone": p["tone"]} if p and p.get("tone") else {}))  # 채널 글 말투(10/23)  # 버튼·본문 링크(목록 = 상품 여러 개)
            url = bs and bs[0][1] >= t0 and f"{CHANNEL_WEB}?before={bs[0][0]}"
    except Exception as e:  # 막히면 그 칸만 비움(다른 채널은 계속)
        miss["tg"] = "채널 웹 못 읽음: " + blame(e)
    if not rows:
        miss.setdefault("tg", "채널 웹에서 그날 글 0개(페이지 모양 바뀜?)")

    tok, ths = E.get("THREADS_TOKEN"), []
    if not tok:
        miss["th"] = "THREADS_TOKEN 없음"
    try:
        url = tok and f"{THREADS}/me/threads?fields=id,text,timestamp,topic_tag&since={int(t0)}&until={int(min(t0 + 86400, now))}&limit=100&access_token={tok}"
        while url and len(ths) < 1000:
            r = json.loads(http(url))
            ths, url = ths + r.get("data", []), r.get("data") and r.get("paging", {}).get("next")
    except Exception as e:
        miss["th"] = "글 목록 못 읽음: " + blame(e)
    for x in ths:
        if not t0 <= stamp(x["timestamp"]) < t0 + 86400:
            continue
        ins = {}
        if "th" not in miss:  # 한 번 막히면(권한 없음 등) 나머지는 안 물음
            try:
                ins = {m["name"]: (m.get("total_value") or m["values"][0])["value"] for m in json.loads(http(f"{THREADS}/{x['id']}/insights?metric=views,likes,replies,reposts,quotes&access_token={tok}"))["data"]}
            except Exception as e:
                why = blame(e)
                if denied(e):
                    miss["th"] = "insights 권한 없음(토큰 권한 threads_manage_insights 확인): " + why
                else:
                    miss.setdefault("th_part", "일부 글 insights 못 읽음: " + why)
        lk = re.search(r"https?://\S+", x.get("text") or "")  # Threads 글은 [몰] 없이 쓰는 일이 많아 글 속 구매 링크로 몰
        ab, rv = seen.get("thab", {}).get("m", {}).get(x["id"]) or {}, None  # 링크 위치 A/B 시험(10/18~): B = 링크 댓글 조회(rv)도, 본문에 주소 없으면 올린 링크(u)로 몰
        if ab.get("r") and "th" not in miss:
            try:
                rv = th_views(tok, ab["r"])
            except Exception as e:
                miss.setdefault("th_part", "일부 글 insights 못 읽음: " + blame(e))
        row("th", x["id"], x.get("text") or "", lk[0] if lk else ab.get("u", ""), stamp(x["timestamp"]), ins.get("views"), sum(ins.get(k, 0) for k in ("likes", "replies", "reposts", "quotes")) if ins else None,
            title=ab.get("n"), links=[ab.get("u")] + re.findall(r"https?://[^\s<>\"]+", x.get("text") or ""), deal=bool(ab) or (False if day >= TH_AB_START else None), likes=ins.get("likes"), replies=ins.get("replies"), **({"ab": ab["ab"], "lk": link_kind(ab.get("u"))} if ab else {}), **({"rv": rv} if ab.get("r") else {}), **({"v": ab["v"]} if ab.get("v") else {}), **({"tone": ab["tone"]} if ab.get("tone") else {}), **({"ph": 1} if ab.get("ph") else {}), **({"hook": ab["hook"]} if ab.get("hook") else {}), **({"topic": x["topic_tag"]} if x.get("topic_tag") else {}))  # topic = Threads 주제 태그(10/23~, 주제별 조회 비교) · lk = 링크 종류(10/19~ 직접 링크 — 10/25 비교는 바뀐 뒤 글끼리)

    itok, uid, ms = E.get("IG_TOKEN"), E.get("IG_USER_ID"), []
    h = {"Authorization": f"Bearer {itok}"}
    if not (itok and uid):
        miss["ig"] = "IG_TOKEN·IG_USER_ID 없음"
    try:  # 하루 글 몇 개라 최근 50개면 어제까지 덮음
        ms = itok and uid and json.loads(http(f"{IG}/{uid}/media?fields=id,caption,timestamp,like_count,comments_count&limit=50", None, h))["data"] or []
    except Exception as e:
        miss["ig"] = "미디어 목록 못 읽음: " + blame(e)
    for x in ms:
        if not t0 <= stamp(x["timestamp"]) < t0 + 86400:
            continue
        v = None
        if "ig" not in miss:
            try:
                ins = {m["name"]: (m.get("total_value") or m["values"][0])["value"] for m in json.loads(http(f"{IG}/{x['id']}/insights?metric=views,reach,saved,shares", None, h))["data"]}
                if "views" not in ins:  # 빈 insights = 그 글만 빈 칸(일부 못 읽음)
                    raise ValueError("빈 insights")
                v, x["reach"], x["saved"], x["shares"] = ins["views"], ins.get("reach"), ins.get("saved"), ins.get("shares")  # 도달·저장·공유(10/25 진우 '상황 잘 보고' · H-5 — 주간 요약 igw)
            except Exception as e:
                why = blame(e)
                if denied(e):
                    miss["ig"] = "조회수 권한 없음(토큰 권한 instagram_business_manage_insights 확인): " + why
                else:
                    miss.setdefault("ig_part", "일부 글 조회수 못 읽음: " + why)
        lk, cm = x.get("like_count"), x.get("comments_count")
        row("ig", x["id"], x.get("caption") or "", "", stamp(x["timestamp"]), v, None if lk is None else lk + (cm or 0), likes=lk, replies=cm, **{k: x[k] for k in ("reach", "saved", "shares") if x.get(k) is not None}, **({"theme": th} if (th := ig_theme_of(x["id"])) else {}))  # 도달·저장 = 읽힌 것만(권한 없으면 칸 X)

    rows.sort(key=lambda r: (("tg", "th", "ig").index(r["ch"]), r["at"]))  # 채널별 시각 순(채널 웹은 쪽 순서로 읽힘)
    m = load(METRICS, {})
    m[day] = {"at": time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 9 * 3600)), "miss": miss, "rows": rows}
    try:  # 인스타 팔로워(하루 1번)
        m[day]["igf"] = itok and uid and json.loads(http(f"{IG}/{uid}?fields=followers_count", None, h)).get("followers_count")
    except Exception as e:
        print("ig 팔로워 못 읽음", err_brief(e))
    m[day]["igw"] = ig_week(m, day)  # 그날까지 7일 인스타 요약(Cowork가 읽고 단계 올릴지 판단 — 매일 그날 줄에)
    if day == TH_END_FROM:
        m[day]["chg"] = ["th_end", "th_tone5"]  # O: Threads 딜 글 끝맺음(친구 한 줄 + 단점 하나)·사진 글(K-1)·훅(U) 바꾼 날 · th_tone5 = 이날부터 th 줄 tone = TH_TONES 1~5(그 전 = TONES 1~4 — 같은 번호 다른 말투)
    metrics_save(m)
    if not E.get("METRICS_DAY") and (not any(soft) or time.gmtime(now + 9 * 3600).tm_hour >= 8):  # 수동 실행(오늘치 점검 등)은 기록 X -> 다음 날 5시에 그날 전체를 다시
        seen["mt_" + day] = now
    c = collections.Counter(r["ch"] for r in rows)
    print(f"metrics {day}: " + " · ".join(f"{ch} {c[ch]}개 빈 칸 {sum(r['views'] is None or r['react'] is None for r in rows if r['ch'] == ch)}" for ch in ("tg", "th", "ig")), miss or "")


def ig_peek(seen):
    """10/26 Cowork G-4('글당 조회 1.0이 진짜인지'): 최근 인스타 게시물 5개의 지금 views·reach·saved + 좋아요·댓글을 로그에(3일에 1번 — seen igpeek) · 지표 이름 확인용(조회 숫자만, 수익 X)."""
    tok, uid = E.get("IG_TOKEN"), E.get("IG_USER_ID")
    if not (tok and uid) or seen.get("igpeek"):
        return
    seen["igpeek"], h = {"t": time.time()}, {"Authorization": f"Bearer {tok}"}
    xs = json.loads(http(f"{IG}/{uid}/media?fields=id,timestamp,media_type,like_count,comments_count&limit=5", None, h)).get("data") or []
    for x in xs:
        try:
            ins = {m["name"]: (m.get("total_value") or m["values"][0])["value"] for m in json.loads(http(f"{IG}/{x['id']}/insights?metric=views,reach,saved,shares", None, h))["data"]}
        except Exception as e:
            ins = {"오류": err_brief(e)}
        print("ig peek", x.get("timestamp", "")[:16], x.get("media_type"), ins, "좋아요", x.get("like_count"), "댓글", x.get("comments_count"))
    for name, url in (("댓글(instagram_business_manage_comments)", f"{IG}/{xs[0]['id']}/comments?fields=id&limit=1" if xs else None), ("메시지(instagram_business_manage_messages)", f"{IG}/{uid}/conversations?platform=instagram&limit=1")):
        try:  # I: 지금 토큰 권한(댓글 읽기 = 쓰기와 같은 권한 · DM = 메시지 권한) — 숫자·내용은 로그에 X
            json.loads(http(url, None, h)) if url else None
            print("ig 권한", name, "됨" if url else "확인 못 함(게시물 없음)")
        except Exception as e:
            print("ig 권한", name, "안 됨 —", err_brief(e))


def ig_week(m, day):
    """metrics.json 최근 7일(day까지) 인스타 요약: 게시 수·조회·도달·저장·좋아요+댓글 합 · 팔로워 처음 -> 끝(하루 1번 igf) — 숫자가 없는 칸은 빼고 더함."""
    days = [time.strftime("%Y-%m-%d", time.gmtime(kst_ts(day + " 00:00") + 9 * 3600 - k * 86400)) for k in range(6, -1, -1)]
    rs = [r for d in days for r in (m.get(d) or {}).get("rows", []) if r.get("ch") == "ig"]
    fs = [m[d]["igf"] for d in days if isinstance((m.get(d) or {}).get("igf"), int)]
    total = lambda k: sum(r[k] for r in rs if isinstance(r.get(k), int))
    th = collections.Counter()
    for r in rs:
        if r.get("theme"):
            th[r["theme"]] += r["saved"] if isinstance(r.get("saved"), int) else 0
    return {"from": days[0], "to": day, "posts": len(rs), "views": total("views"), "reach": total("reach"), "saved": total("saved"), "shares": total("shares"), "react": total("react"),
            "followers": [fs[0], fs[-1]] if fs else None, "themes": dict(th.most_common())}  # H-5 테마별 저장 순위(Cowork 판단용 — 테마는 요일마다 매주 다시 돎)


def ig_theme_of(mid):
    """인스타 게시물 id -> 테마(카드 이름 기록 names.json pid — 테마 넘기기·개별 아이템), 없으면 None."""
    return next((v.get("theme") for v in load(CARD_NAMES, {}).values() if isinstance(v, dict) and str(v.get("pid")) == str(mid)), None)


def th_end_report(seen):
    """O 실험(TH_END_FROM~ Threads 딜 글 끝맺음·사진 글) 1주 뒤 1번: 쿠팡 파트너스 리포트 클릭·주문 = 바꾼 뒤 7일 vs 그 전 7일 -> 관리봇만(숫자 = 로그·파일 X).
    shortcut: 쿠팡 링크에 채널 구분(subId)이 없어서 쿠팡 전체(텔레그램·사이트 포함) 비교 — Threads만 보려면 Threads 글 링크를 subId 붙여 따로 만들어야 함."""
    now, start = time.time(), kst_ts(TH_END_FROM + " 00:00")
    if not HAS_CP or not start + 8 * 86400 <= now < start + 10 * 86400 or seen.get("thend", {}).get("done"):  # 8~10일째 사이 1번(seen 3일 정리 뒤 다시 X)
        return
    ymd = lambda t: time.strftime("%Y%m%d", time.gmtime(t + 9 * 3600))
    try:
        tot = []
        for a in (start - 7 * 86400, start):
            q = f"startDate={ymd(a)}&endDate={ymd(a + 6 * 86400)}"
            cl, od = coupang("GET", f"/reports/clicks?{q}"), coupang("GET", f"/reports/orders?{q}&page=0")
            tot.append((sum(int(r.get("click") or 0) for r in cl if isinstance(r, dict)) if isinstance(cl, list) else 0, len(od) if isinstance(od, list) else 0))
    except CpLimit:
        return  # 다음 실행에
    except Exception as e:
        print("th end 리포트 실패", type(e).__name__)
        return
    (c0, o0), (c1, o1) = tot
    rate = lambda o, c: f"{o / c * 100:.1f}%" if c else "-"
    if tg("sendMessage", chat_id=ADMIN, text=f"🧪 Threads 딜 글 끝맺음 실험(O · {TH_END_FROM}~) 1주 비교 — 쿠팡 파트너스 리포트(링크에 채널 구분이 없어 쿠팡 전체)\n"
                                          f"클릭 {c0:,} → {c1:,}\n주문 {o0:,} → {o1:,}\n클릭당 주문 {rate(o0, c0)} → {rate(o1, c1)}"):
        seen["thend"] = {"t": now, "done": 1}  # 보낸 뒤에만(텔레그램 실패 = 창 안 다음 실행에 다시)
        print("th end 리포트 보냄")


def cp_score(seen):
    """E 반응 점수(하루 1번 CPS_HOUR~ KST) -> seen cps {o 주문, c 구매 클릭, v 딜 쪽 조회: {url: 수}} — seen.json(Actions 캐시)에만, 커밋·로그에 숫자 X(공개 저장소).
    o = 쿠팡 파트너스 주문 리포트(D-CPS_DAYS~D-1, 1번 — 24시간 안 다른 상품 구매도 실적이라 events pid와 같은 상품만), 키 없으면 X.
    c·v = GoatCounter(GOATCOUNTER_TOKEN 있을 때만): 이벤트 'buy/<주소>'(사이트 구매 클릭 — 10/24부터 링크 경로까지) · '/p/<번호>.html'(딜 쪽 조회 -> 그 글 링크).
    오류 = 어제 값 그대로(쿠팡 상한 = 다음 실행에 다시)."""
    now = time.time()
    kst = time.gmtime(now + 9 * 3600)
    today, d = time.strftime("%Y-%m-%d", kst), seen.get("cps", {})
    if kst.tm_hour < CPS_HOUR or d.get("do") == d.get("dg") == today:
        return
    d = seen["cps"] = {**d, "t": now}
    bare = lambda u: (u or "").split("?")[0]
    if d.get("do") != today and RUN.get("cpn", [0])[0] < CP_RUN - 1:  # 이번 실행 쿠팡 호출을 거의 다 썼으면 다음 실행에(cp_price 몫 남김)
        if not HAS_CP:
            d.update(o={}, do=today)
        else:
            ymd = lambda k: time.strftime("%Y%m%d", time.gmtime(now + 9 * 3600 - k * 86400))
            try:
                rows = coupang("GET", f"/reports/orders?startDate={ymd(CPS_DAYS)}&endDate={ymd(1)}&page=0")  # shortcut: 1쪽(1000줄)만·취소 안 뺌 — 주문이 1000줄을 넘거나 취소가 순위를 바꾸면 page·/reports/cancels
                urls = {}
                for u, x in ev_info().items():
                    if x.get("pid"):
                        urls.setdefault(x["pid"], []).append(bare(u))
                o = collections.Counter()
                for r in rows if isinstance(rows, list) else []:
                    for u in urls.get(str(r.get("productId")), []):
                        o[u] += int(r.get("quantity") or 1)
                d.update(o=dict(o), do=today)
                print("cp score 주문 리포트 읽음")
            except CpLimit:
                pass  # 다음 실행에
            except Exception as e:
                d["do"] = today
                print("cp score 주문 리포트", type(e).__name__)
    if d.get("dg") != today:
        tok = E.get("GOATCOUNTER_TOKEN")
        if not tok:
            d.update(c={}, v={}, dg=today)
        else:
            hr = lambda t: time.strftime("%Y-%m-%dT%H:00:00Z", time.gmtime(t))
            c, v, seen_ids, posts = collections.Counter(), collections.Counter(), [], load(POSTS, [])
            try:
                for _ in range(CPS_GC_PAGES):  # shortcut: 많이 본 순 앞쪽 경로만(100개 × CPS_GC_PAGES) — 딜 쪽이 더 늘면 쪽 수를 늘림
                    q = urllib.parse.urlencode({"start": hr(now - CPS_DAYS * 86400), "end": hr(now), "limit": 100, **({"exclude_paths": ",".join(seen_ids)} if seen_ids else {})})
                    r = json.loads(http(f"https://{GC_CODE}.goatcounter.com/api/v0/stats/hits?{q}", headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}))
                    for h in r.get("hits") or []:
                        seen_ids.append(str(h.get("path_id")))
                        path, n = re.sub(r"^buy/link-[ab]/", "buy/", str(h.get("path") or "")), int(h.get("count") or 0)  # /link A·B 상품 클릭(buy/link-a/몰 주소)도 같은 상품
                        if path.startswith("buy/") and "/" in path[4:]:  # 예전 'buy/<몰 주소>'(상품 구분 X)는 뺌
                            c["https://" + path[4:]] += n
                        elif (m := re.fullmatch(r"/p/(\d+)\.html", path)) and int(m[1]) < len(posts) and posts[int(m[1])].get("url"):
                            v[bare(posts[int(m[1])]["url"])] += n
                    if not r.get("more"):
                        break
                    time.sleep(0.3)  # 초당 4번 상한
                d.update(c=dict(c), v=dict(v), dg=today)
                print("cp score GoatCounter 읽음")
            except Exception as e:
                d["dg"] = today
                print("cp score GoatCounter", type(e).__name__)


GC_TOP = "gc_top.json"  # 사이트 '많이 본' 순서(10/24 Cowork 개편) — 순서만, 숫자 X(공개 저장소)


def gc_top(seen):
    """1시간에 1번(seen gct) GoatCounter 최근 24시간(cp_score와 같은 호출): 딜 쪽 조회('/p/N.html' -> 그 글 url) + 구매 클릭('buy/<주소>') × 3
    -> gc_top.json {at: KST 'YYYY-MM-DD HH:MM', urls: 높은 순 60개(쿼리 뺀 주소 — 그 주소가 상품 1개일 때만, 검색·클릭 주소는 ?뒤가 상품이라 그대로)} — 순서만(조회·클릭 수 X). 토큰 없으면 X · 오류 = 옛 파일 그대로."""
    now, tok = time.time(), E.get("GOATCOUNTER_TOKEN")
    if not tok or now - seen.get("gct", {}).get("t", 0) < 3600:
        return
    seen["gct"] = {"t": now}
    hr = lambda t: time.strftime("%Y-%m-%dT%H:00:00Z", time.gmtime(t))
    sc, seen_ids, posts = collections.Counter(), [], load(POSTS, [])
    nb = collections.Counter(u.split("?")[0] for u in {p.get("url") for p in posts if p.get("url")})
    key = lambda u: u.split("?")[0] if nb[u.split("?")[0]] == 1 else u  # build_site.top_list와 같은 규칙(search/all·click.php 여러 상품이 한 주소로 합쳐지지 않게)
    try:
        for _ in range(CPS_GC_PAGES):  # shortcut: 많이 본 순 앞쪽 경로만(100개 × CPS_GC_PAGES) — 24시간이라 보통 1~2쪽
            q = urllib.parse.urlencode({"start": hr(now - 86400), "end": hr(now), "limit": 100, **({"exclude_paths": ",".join(seen_ids)} if seen_ids else {})})
            r = json.loads(http(f"https://{GC_CODE}.goatcounter.com/api/v0/stats/hits?{q}", headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}))
            for h in r.get("hits") or []:
                seen_ids.append(str(h.get("path_id")))
                path, n = re.sub(r"^buy/link-[ab]/", "buy/", str(h.get("path") or "")), int(h.get("count") or 0)  # /link A·B 상품 클릭도 같은 상품
                if path.startswith("buy/") and "/" in path[4:]:  # 예전 'buy/<몰 주소>'(상품 구분 X)는 뺌
                    if nb["https://" + path[4:]] == 1:  # 상품 1개로 정해지는 주소만(검색·클릭 주소 = 어느 상품인지 모름)
                        sc["https://" + path[4:]] += 3 * n
                elif (m := re.fullmatch(r"/p/(\d+)\.html", path)) and int(m[1]) < len(posts) and posts[int(m[1])].get("url"):
                    sc[key(posts[int(m[1])]["url"])] += n
            if not r.get("more"):
                break
            time.sleep(0.3)  # 초당 4번 상한
    except Exception as e:
        err = f"{type(e).__name__} {getattr(e, 'code', '')}".strip()
        print("gc fail", err)
        if getattr(e, "code", 0) in API_AUTH:  # 토큰·권한 오류만 '실패' 알림(네트워크·5xx·429·응답 깨짐 = 로그만)
            API_ST.setdefault("gc", "fail " + err)
        return
    json.dump({"at": time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 9 * 3600)), "urls": [u for u, _ in sc.most_common(60)]}, open(GC_TOP, "w"), ensure_ascii=False)
    print("gc ok · 많이 본 순서 갱신")
    API_ST.setdefault("gc", "ok")


LINK_AB_FILE, LINK_AB_PAGES = "link_ab.json", 10  # /link A·B 하루 집계(10/25 Cowork·진우 — 기간 = build_site.LINK_AB) · GoatCounter 경로 쪽 수(100개씩)


LP_PROMO = ("gmarket.co.kr", "auction.co.kr", "lotteon.com", "ssg.com")  # 기획전 주소 -> 링크프라이스 딥링크(10/25 Cowork — G마켓·옥션·롯데온·이마트(SSG)) · 11번가 등 = 원래 주소(사이트에서 nofollow)
MALL_SITES = {"coupang": "https://www.coupang.com", "11st": "https://www.11st.co.kr", "ssg": "https://www.ssg.com", "gmarket": "https://www.gmarket.co.kr", "auction": "https://www.auction.co.kr",
              "lotteon": "https://www.lotteon.com", "oliveyoung": "https://www.oliveyoung.co.kr", "emart": "https://emart.ssg.com"}  # 기획전 몰 로고 받을 첫 화면(mall_icons)
MALL_ICONS = "docs/icons/mall"


def promo_urls():
    """promos.json(Cowork 기획전 — 깨진 파일 = 없음) 항목들."""
    d = load(PROMOS, {})
    return [p for p in (d.get("promos") if isinstance(d, dict) and isinstance(d.get("promos"), list) else []) if isinstance(p, dict)]


def promo_links(seen):
    """기획전 주소 중 링크프라이스 몰(LP_PROMO)만 딥링크 API(result S만 — LP_HOSTS 직접 링크 X: 승인 안 된 링크가 제휴로 보임, 10/25 21시 Cowork)로 1번(실패 = 하루 뒤 다시) -> promo_links.json {원래 주소: 제휴 링크}
    (사이트 빌드가 씀 — 아직·실패면 몰 홈 그대로 = 20:3x Cowork 최종 규칙 ② · promos.json에서 빠지면 지움)."""
    urls = {u for p in promo_urls() for u in (p.get("url"), (p.get("cta") or {}).get("href") if isinstance(p.get("cta"), dict) else None)
            if isinstance(u, str) and u.startswith("https://") and (lambda h: any(h == x or h.endswith("." + x) for x in LP_PROMO))(urllib.parse.urlsplit(u).netloc.lower())}
    pl, now = load(PROMO_LINKS, {}), time.time()
    st = seen.setdefault("prl", {"x": {}})
    st["t"], st["x"] = now, {u: t for u, t in st.get("x", {}).items() if u in urls}
    keep = {u: v for u, v in (pl if isinstance(pl, dict) else {}).items() if u in urls}
    for u in sorted(urls - set(keep)):
        if now - st["x"].get(u, 0) < 86400:
            continue
        try:
            link, why = lp_api(u)
        except Exception as e:  # 접속 오류 = 다음 실행에
            print("promo link", urllib.parse.urlsplit(u).netloc, type(e).__name__)
            continue
        if link and str(link).startswith(("https://", "http://")):
            keep[u] = link
            print("promo link", urllib.parse.urlsplit(u).netloc, "-> 링크프라이스")
        else:
            st["x"][u] = now
            print("promo link 안 됨(승인 몰 아님?)", urllib.parse.urlsplit(u).netloc, why)
    if keep != pl:
        json.dump(keep, open(PROMO_LINKS, "w"), ensure_ascii=False, indent=1)


def mall_icons(seen):
    """기획전 몰 로고(10/25 Cowork — 사이트가 바깥 주소를 실시간으로 안 부르게): promos.json 몰마다 docs/icons/mall/<몰>.png가 없으면 하루 1번
    그 몰 첫 화면의 apple-touch-icon(없으면 icon · /favicon.ico) -> 64px PNG(Pillow). 못 받으면 사이트는 흰 칸에 몰 글자."""
    from io import BytesIO
    from PIL import Image
    st, now = seen.setdefault("micon", {}), time.time()
    st["t"] = now
    for m in sorted({p["mall"] for p in promo_urls() if p.get("mall") in MALL_SITES}):
        f = f"{MALL_ICONS}/{m}.png"
        if os.path.exists(f) or now - st.get(m, 0) < 86400:
            continue
        st[m] = now
        try:
            home = MALL_SITES[m]
            page_ = http(home)
            rels = re.findall(r'<link[^>]+rel=["\'](?:apple-touch-icon(?:-precomposed)?|(?:shortcut )?icon)["\'][^>]*>', page_, re.I)
            hrefs = [re.search(r'href=["\']([^"\']+)', l, re.I) for l in sorted(rels, key=lambda l: "apple" not in l.lower())]
            cands = [u for u in (urllib.parse.urljoin(home + "/", h[1]) for h in hrefs if h) if u.startswith(("https://", "http://"))] + [home + "/favicon.ico"]
        except Exception as e:
            print("mall icon", m, repr(e))
            cands = [MALL_SITES[m] + "/favicon.ico"]
        for u in cands:
            try:
                with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=20) as r:
                    im = Image.open(BytesIO(r.read(2_000_000)))
                    im.load()
                im = im.convert("RGBA")
                if min(im.size) < 16:
                    continue
                os.makedirs(MALL_ICONS, exist_ok=True)
                im.resize((64, 64), Image.LANCZOS).save(f, "PNG", optimize=True)
                print("mall icon", m, "저장")
                break
            except Exception as e:
                print("mall icon", m, urllib.parse.urlsplit(u).path[-40:], repr(e)[:80])


def link_ab(seen):
    """/link A·B 반반 비교(10/26~11/8 — 결과 판단은 Cowork·진우, 자동으로 한쪽으로 몰지 않음): 하루 1번(0:30 KST 뒤 첫 실행) 어제(KST) GoatCounter
    보기 'link-a'·'link-b'(가상 경로) · 상품 클릭 'buy/link-a/…' · 채널 클릭 'link-a/…'(카톡·블로그·Threads·인스타·텔레그램) · 사이트 홈 'link-a/home'(따로)
    -> link_ab.json {날짜: {a: {view, buy, ch, home}, b: …, line}} + 로그 줄(README 점검 표에 그대로). 상품 클릭률 = buy ÷ view · 채널 클릭률 = ch ÷ view.
    마지막 날(11/8) 줄은 11/9 0:30 뒤에 생김. 토큰 없으면 X · 오류 = 그날 3번까지 다음 실행에 다시."""
    tok, now = E.get("GOATCOUNTER_TOKEN"), time.time()
    kst = time.gmtime(now + 9 * 3600)
    day = time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600 - 86400))
    tries = seen.get("lab", {}).get("d", {}).get(day, 0)  # seen 칸 = {t, d: {날짜: 오류 횟수}}(seen 정리는 t로)
    if not tok or not LINK_AB[0] <= day <= LINK_AB[1] or kst.tm_hour == 0 and kst.tm_min < 30 or day in load(LINK_AB_FILE, {}) or tries >= 3:
        return
    t0 = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() - 9 * 3600  # 어제 KST 0시(UTC)
    hr = lambda t: time.strftime("%Y-%m-%dT%H:00:00Z", time.gmtime(t))
    c, ids = {v: {"view": 0, "buy": 0, "ch": 0, "home": 0} for v in "ab"}, []
    try:
        for _ in range(LINK_AB_PAGES):
            q = urllib.parse.urlencode({"start": hr(t0), "end": hr(t0 + 86400 - 3600), "limit": 100, **({"exclude_paths": ",".join(ids)} if ids else {})})  # end = 마지막 시간 칸(23시 KST — GoatCounter end는 그 칸까지 포함)
            r = json.loads(http(f"https://{GC_CODE}.goatcounter.com/api/v0/stats/hits?{q}", headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}))
            for h in r.get("hits") or []:
                ids.append(str(h.get("path_id")))
                path, n = str(h.get("path") or ""), int(h.get("count") or 0)
                if m := re.fullmatch(r"link-([ab])/home", path):  # 사이트 홈으로(전체 특가) = 채널 클릭과 따로
                    c[m[1]]["home"] += n
                elif m := re.fullmatch(r"/?link-([ab])", path):
                    c[m[1]]["view"] += n
                elif m := re.match(r"buy/link-([ab])/", path):
                    c[m[1]]["buy"] += n
                elif m := re.match(r"link-([ab])/", path):
                    c[m[1]]["ch"] += n
            if not r.get("more"):
                break
            time.sleep(0.3)  # 초당 4번 상한
    except Exception as e:
        lab = seen.setdefault("lab", {"d": {}})
        lab.update(t=now, d={**lab.get("d", {}), day: tries + 1})
        print("link ab", day, type(e).__name__, getattr(e, "code", ""))
        return
    pct = lambda a, b: f"{round(100 * a / b)}%" if b else "-"
    line = f"link {int(day[5:7])}/{int(day[8:10])} " + " · ".join(f"{v} {x['view']} view {x['buy']} buy({pct(x['buy'], x['view'])}) {x['ch']} ch({pct(x['ch'], x['view'])}) {x['home']} home" for v, x in c.items())
    d = load(LINK_AB_FILE, {})
    d[day] = {**c, "line": line}
    json.dump(dict(sorted(d.items())), open(LINK_AB_FILE, "w"), ensure_ascii=False, indent=1)
    print(line)


API_ST, API_AUTH = {}, (400, 401, 403)  # API_ST = 이번 실행 첫 호출 결과 {'tts'|'gc': 'ok' | 'fail <오류>'} — tts·gc_top이 채우고 api_check가 관리자 알림
API_MSG = {"tts": ("Google TTS 키(릴스 나레이션)", "릴스 나레이션 켜짐", "릴스는 나레이션 없이 글자+음악으로 계속 — GCP 키의 API 제한(Cloud Text-to-Speech API)·결제 연결 확인"),
           "gc": ("GoatCounter 토큰(통계 읽기)", "🏆 TOP 10 '많이 본'·화면 비교 데이터 씀", "사이트 TOP 10은 옛 순서 그대로 — 토큰 권한(Read statistics)·사이트(hotdealpick) 확인")}


def api_check(seen):
    """GOOGLE_TTS_KEY·GOATCOUNTER_TOKEN 첫 호출 성공/실패(10/25 Cowork) -> 처음이거나 성공↔실패가 바뀔 때만 관리자 알림 1번(로그 줄 = tts·gc_top의 'tts ok/fail'·'gc ok/fail').
    TTS는 키가 생기고 아직 확인 기록이 없으면 짧은 말 1번 불러 봄(릴스는 하루 1번이라) · GoatCounter = gc_top(1시간에 1번) 결과 그대로. 키 값·주소는 알림·로그 X."""
    c = seen.setdefault("apichk", {})
    c["t"] = time.time()  # seen 정리(t 기준)에서 안 지워지게
    if E.get("GOOGLE_TTS_KEY") and "tts" not in c and "tts" not in API_ST:
        tts("확인")
    for k, (name, ok, bad) in API_MSG.items():
        v = API_ST.get(k)
        if v and v.split()[0] != c.get(k) and tg("sendMessage", chat_id=ADMIN, text=f"✅ {name} 첫 호출 성공 — {ok}" if v == "ok" else f"⚠️ {name} 호출 실패({v[5:] or '오류'}) — {bad}"):
            c[k] = v.split()[0]  # 보낸 뒤에만 기록(텔레그램 실패 = 다음 실행에 다시)


def cp_repost(seen):
    """E 자동 재게시(10/24 진우 '반응 좋은 품목 자동 재게시 — 잘 된 쿠팡 품목 3일마다 재게시 순서 앞으로'): CPRE_HOURS 칸마다 1개(그 시각부터 CPRE_SPAN시간 안 첫 빈 실행).
    후보 = 진우 쿠팡 상품(파트너스 링크·채널에 나간 적 있음) 중 지금 🔥(own_end st hot) · 보이는 가격의 확인(own_end chkt)이 CPRE_FRESH 안 · 같은 상품(url·pid) 채널 글/진우·Cowork 예약이 앞뒤 CPRE_DAYS일 없음 · 반응 신호 있음.
    순서 = 주문(cp_score o) > 사이트 구매 클릭(c) > 딜 쪽 조회(v) > 잘 된 상품 표(top.json Threads 조회) > Threads 놓친 진우 🔥(th_missed — 10/25) — 점수·순서 근거·후보 수는 로그에 X(공개 로그).
    글 = 새 글(옛 글 안 고침): 쿠팡 대가성 문구 첫 줄 · '🔁 다시 소개' · 가격 = 확인 가격 '(M/D H시 확인)' · '처음 소개 때' = 진짜 첫 🔥 글이 있을 때만 · 🚀 = 검색 API isRocket일 때만(아니면 📦)
    · posts re:1(지금 진열 상태 그대로 — 🔁 다시 특가 배지 유지) -> Threads 맨 앞. 진우 예약 앞뒤 TOSS_EV_PAD·묶음 간격·시간당 상한(busy)이면 다음 실행에(칸 안)."""
    now = time.time()
    kst = time.gmtime(now + 9 * 3600)
    slot = next((h for h in CPRE_HOURS if h <= kst.tm_hour < h + CPRE_SPAN), None)
    key = time.strftime("cpre_%Y%m%d_", kst) + f"{slot:02d}" if slot is not None else ""
    if slot is None or key in seen:
        return
    evs = load(EVENTS, [])
    if ev_near(seen, now, evs) or busy(seen):
        print(f"cp repost {slot:02d}: 미룸(진우 예약 앞뒤·묶음 간격·시간당 상한)")
        return
    posts, ev, rk = load(POSTS, []), ev_info(), seen.get("cpq", {}).get("r", {})
    since = time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 9 * 3600 - CPRE_DAYS * 86400))
    last, first, chan = {}, {}, set()
    block = {x["url"] for e in evs if re.match(AT_RX, e.get("at", "")) and abs(kst_ts(e["at"]) - now) < CPRE_DAYS * 86400
             for x in [e] + (e["items"] if e.get("list") and isinstance(e.get("items"), list) else []) if isinstance(x, dict) and x.get("url")}  # 진우·Cowork 예약(지난·앞으로 3일 · 행사 목록 글 상품도)
    for p in posts:
        u = p.get("url") or ""
        if not p.get("own") or aff_note(u) != DISCLOSURE or p["text"].startswith("📋"):
            continue
        last[u] = p
        if icon_of(p["text"]) == "🔥" and not p.get("re"):
            first.setdefault(u, p)  # '처음 소개 때' = 진짜 첫 🔥 글(events target만 있는 상품 X)
        if p.get("mid"):
            chan.add(u)
            if p["t"] >= since:
                block.add(u)
    bpid = {ev.get(u, {}).get("pid") for u in block} - {None}  # 같은 상품 다른 파트너스 링크도
    fresh_at = time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 9 * 3600 - CPRE_FRESH))
    sc, bare = seen.get("cps", {}), lambda u: u.split("?")[0]
    top = {x.get("url"): n for n, x in enumerate(load(TOP, {}).get("items", [])) if x.get("url")}
    sig = lambda u: tuple(-sc.get(k, {}).get(bare(u), 0) for k in "ocv") + (top.get(u, len(top)),)
    miss = th_missed(posts, now)  # Threads 개별 글 칸에 밀려 3시간 창이 끝난 진우 🔥(10/25 Cowork '밀렸으면 재게시 루틴 대상으로') = 반응 신호 다음 차례
    cand = [u for u in chan if u not in block and ev.get(u, {}).get("pid") not in bpid and last[u].get("st") == "hot" and last[u].get("now") and last[u].get("chkt", "") >= fresh_at
            and (any(sig(u)[:3]) or u in top or u in miss)]
    seen[key] = now
    if not cand:
        print(f"cp repost {slot:02d}: 후보 없음")
        return
    u = min(cand, key=lambda u: (sig(u), last[u]["t"]))  # 같으면 오래전에 나간 것
    p = last[u]
    name, rocket = parse(title_of(p["text"]))[1], rk.get(u) is True
    tgt = first[u] and parse(title_of(first[u]["text"]))[2].split("/")[0].split(" · ")[0].strip() if u in first else ""
    body = mall_body("coupang", "🔁 다시 소개", "🔥", name, f"{p['now']} ({p['chk']} 확인)", [esc(f"💡 처음 소개 때 {tgt}") if tgt else "", "⚠️ 결제 전 최종가 확인"], rocket)
    m = tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True}, text=ad_head(DISCLOSURE, plain_of(body)) + body,
           reply_markup={"inline_keyboard": [[{"text": mall_btn("coupang", p["now"], rocket), "url": u}]]})
    if not m:
        del seen[key]
        return  # 다음 실행에 다시(실패는 바로 알림)
    bundled(seen)
    record(m.get("text", ""), m.get("entities", []), u, m["message_id"], extra={"own": 1, "re": 1, **{k: p.get(k) for k in ("cat", "tag", "st", "tgt", "now", "chk", "chkt", "stdy", "rehot", "img")}})
    print(f"cp repost {slot:02d}: {clip(name, 30)}")


TH_MISS_DAYS = 7  # Threads 놓친 진우 🔥 = 채널 글 뒤 이 날 수 안만 재게시 후보(cp_repost — 3일 간격 규칙은 그대로)


def th_missed(posts, now):
    """Threads 개별 글을 못 받은 진우 쿠팡 🔥 채널 글(10/25 Cowork — 35~55분 간격·칸마다 1개에 밀려 3시간 창이 끝남) -> 링크 집합.
    = 채널에 나감(mid)·사이트 진열만 X·대가성 쿠팡·🔥·올린 지 3시간~TH_MISS_DAYS일 · 같은 링크 글 중 Threads에 나간(th) 글·재게시(re) 글이 하나도 없음
    (재게시는 1번만 — 재게시 글도 Threads를 놓치면 3일마다 되풀이 X, 10/25 리뷰)."""
    lo, hi = (time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 9 * 3600 - x)) for x in (TH_MISS_DAYS * 86400, 3 * 3600))
    th = {p.get("url") for p in posts if p.get("th") or p.get("re")}
    return {p["url"] for p in posts if p.get("own") and p.get("mid") and not p.get("shelf") and p.get("url") and p["url"] not in th and lo <= p["t"] < hi
            and aff_note(p["url"]) == DISCLOSURE and icon_of(p["text"]) == "🔥" and not p["text"].startswith("📋")}


def top_build(seen):
    """잘 된 상품 표 -> top.json(10/22 Cowork·진우 '잘 되는 제품은 꾸준하게' — Cowork 진우 🔥 재게시·토스 후보 가산이 읽음), 하루 1번(METRICS_HOUR 넘어, 어제 줄 모은 뒤):
    지난 TOP_DAYS일 metrics Threads 개별 글(kind deal) 중 조회(v48, 없으면 views) 상위 TOP_SHARE ∪ 답글 상위 TOP_SHARE(1개↑ — B 글의 우리 링크 댓글 1개는 뺌)를
    상품별로(토스 = 상품 id, id 없는 토스 글 = 이름, 그 밖 = 링크 — 링크 모르는 글은 같은 이름 글의 링크) — 이름·링크·몰·최고 조회·최고 답글·Threads 글 수·마지막 게시(tg·th 통틀어), 최고 조회 순.
    상품 칸 없는 예전 Threads 줄은 글을 다시 읽어 채움(한 실행 TOP_FILL개 — B 글은 링크 댓글, 댓글 권한 없으면 이름으로 · 지운 글 = etc · 일시 오류면 다음 실행에 이어서, 다 채우기 전엔 그날 끝 표시 X)."""
    now, tok = time.time(), E.get("THREADS_TOKEN")
    kst = time.gmtime(now + 9 * 3600)
    today = time.strftime("%Y-%m-%d", kst)
    if kst.tm_hour < METRICS_HOUR or load(TOP, {}).get("d") == today or "mt_" + time.strftime("%Y-%m-%d", time.gmtime(now - 15 * 3600)) not in seen and kst.tm_hour < 8:  # 어제 줄을 다 모은 뒤(늦어도 8시)
        return
    m, ids, thab = load(METRICS, {}), toss_ids(seen), seen.get("thab", {}).get("m", {})
    days = sorted(d for d in m if d >= time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600 - TOP_DAYS * 86400)))
    old, n_fill, no_rep = [r for d in days for r in m[d]["rows"] if r["ch"] == "th" and "kind" not in r], 0, False
    url_rx = r"https?://[^\s<>\"]+"
    for r in old[:TOP_FILL] if tok else []:
        try:
            text = json.loads(http(f"{THREADS}/{r['id']}?fields=text&access_token={tok}")).get("text") or ""
            links = [thab.get(r["id"], {}).get("u")] + re.findall(url_rx, text)
            if not any(links) and r.get("ab") in ("B", "C", "S") and not no_rep:  # B·C·S = 본문에 주소 없음, 첫 댓글 = 링크
                try:
                    links = [u for c in json.loads(http(f"{THREADS}/{r['id']}/replies?fields=text&access_token={tok}")).get("data", []) for u in re.findall(url_rx, c.get("text") or "")][:1]
                except urllib.error.HTTPError as e:  # 댓글 읽기 권한 없음(threads_read_replies) 등 -> 이번 실행은 이름으로만
                    if e.code >= 500:
                        raise
                    no_rep = True
        except urllib.error.HTTPError as e:
            if e.code >= 500:
                break
            r["kind"] = "etc"  # 지운 글·권한 = 상품 칸 없음으로 끝
            print("top fill", r["id"], repr(e))
            continue
        except Exception as e:  # 시간 초과·터널 등 = 다음 실행에 이어서
            print("top fill", r["id"], repr(e))
            break
        r.update(prod_cols(title_of(re.sub(r"^💸[^\n]*\n?", "", text, flags=re.M)), r["cat"], links, ids, True if r.get("ab") else False if r["date"] >= TH_AB_START else None))  # 💸 훅 줄(10/11~19 Threads 첫 줄) = 상품명 X
        n_fill += 1
    posts, fixed = load(POSTS, []), 0
    for r in (r for d in days for r in m[d]["rows"] if r.get("kind") == "deal"):  # 사이트 딜 페이지 링크(10/19 직접 링크 전 Threads 글) -> 그 글의 구매 링크·상품명·몰(posts.json 번호 = 페이지 번호)
        pn = re.match(re.escape(SITE) + r"p/(\d+)\.html", r.get("url") or "")
        if pn and int(pn[1]) < len(posts) and posts[int(pn[1])].get("url"):
            pp = posts[int(pn[1])]
            r.update(url=pp["url"], name=parse(title_of(pp["text"]))[1], shop=shop_of(pp) or r["shop"])
            fixed += 1
    if old and tok or fixed:
        metrics_save(m)
    left = sum("kind" not in r for r in old) if tok else 0
    rows = [r for d in days for r in m[d]["rows"]]
    deals = [r for r in rows if r["ch"] == "th" and r.get("kind") == "deal" and (r.get("v48") or r.get("views")) is not None]
    sv, rp = (lambda r: r.get("v48") or r.get("views") or 0), (lambda r: max(0, (r.get("replies") or 0) - (r.get("ab") in ("B", "C", "S"))))  # B·C·S 글 답글 = 우리 링크 댓글 1개 빼고
    norm = lambda x: re.sub(r"\W", "", (x or "").lower())
    tn = {norm(r.get("name")): r["tid"] for r in rows if r.get("tid")}
    nu = {norm(r.get("name")): r["url"] for r in sorted(rows, key=lambda r: (r["date"], r["at"])) if r.get("kind") == "deal" and r.get("url") and r["shop"] != "toss"}

    def key(r):
        tid = r.get("tid") or (r["shop"] == "toss" and tn.get(norm(r.get("name"))))
        return f"toss:{tid}" if tid else "tname:" + norm(r.get("name")) if r["shop"] == "toss" else r.get("url") or nu.get(norm(r.get("name"))) or "name:" + norm(r.get("name"))
    n = math.ceil(len(deals) * TOP_SHARE)
    pick = {r["id"]: r for r in sorted(deals, key=lambda r: (-sv(r), -rp(r)))[:n]}
    pick.update({r["id"]: r for r in sorted(deals, key=lambda r: -rp(r))[:n] if rp(r)})
    last, lu, cnt = {}, {}, collections.Counter(key(r) for r in deals)
    for r in sorted(rows, key=lambda r: (r["date"], r["at"])):
        if r.get("kind") == "deal":
            last[key(r)] = f"{r['date']} {r['at']}"
            lu[key(r)] = r.get("url") or lu.get(key(r), "")
    items = {}
    for r in sorted(pick.values(), key=lambda r: (r["date"], r["at"])):  # 같은 상품은 최근 글 이름으로
        k, x = key(r), items.get(key(r), {})
        items[k] = {"key": k, "name": r.get("name") or x.get("name", ""), "url": lu.get(k, ""), "mall": r["shop"], "best": max(sv(r), x.get("best", 0)),
                    "replies": max(rp(r), x.get("replies", 0)), "n": cnt[k], "last": last.get(k, "")}
    js = lambda x: json.dumps(x, ensure_ascii=False)
    out = sorted(items.values(), key=lambda x: (-x["best"], -x["replies"]))
    open(TOP, "w", encoding="utf-8").write(f'{{"d": {js("" if left else today)}, "at": {js(time.strftime("%Y-%m-%d %H:%M", kst))}, "days": {TOP_DAYS}, '
                                           f'"rule": {js(f"Threads 개별 글 조회(v48, 없으면 views) 상위 {int(TOP_SHARE * 100)}% + 답글(우리 링크 댓글 빼고) 상위 {int(TOP_SHARE * 100)}%(1개↑), 상품(토스 = 상품 id·이름, 그 밖 = 링크)별 · 최고 조회 순")}, '
                                           f'"posts": {len(deals)}, "items": [\n' + ",\n".join(map(js, out)) + "]}\n")  # 상품 1개 = 1줄
    print(f"top: Threads 개별 글 {len(deals)}개 -> 잘 된 상품 {len(out)}개" + (f" · 예전 줄 채움 {n_fill}/{len(old)}" + (" · 댓글 권한 없음(이름으로)" if no_rep else "") if old else ""))


def top_toss(seen, now):
    """잘 된 토스 상품(top.json) -> (상품 id 집합, 이름(기호·띄어쓰기 뺌) 집합) — 토스 개별·토스 픽 채움 후보 가산용. 오늘(KST) 가산으로 TOP_BONUS_DAY개 상품을 올렸으면 빈 집합."""
    d = seen.get("topb", {})
    if d.get("d") == time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600)) and len(d.get("ids", [])) >= TOP_BONUS_DAY:
        return set(), set()
    ks = [str(x.get("key", "")) for x in load(TOP, {}).get("items", [])]
    return {int(k[5:]) for k in ks if k.startswith("toss:")}, {k[6:] for k in ks if k.startswith("tname:")}


def top_hit(tops, iid, name):
    """이 토스 상품이 잘 된 상품 표에 있나(id 또는 이름)."""
    return iid in tops[0] or re.sub(r"\W", "", (name or "").lower()) in tops[1]


def top_mark(seen, now, iid):
    """잘 된 상품 가산으로 올림 -> 오늘 상품 수(같은 상품 = 채널 글·Threads 글 합쳐 1번)."""
    day, d = time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600)), seen.get("topb", {})
    ids = d.get("ids", []) if d.get("d") == day else []
    seen["topb"] = {"t": now, "d": day, "ids": ids + [iid] if iid not in ids else ids}


def watch(seen):
    """실행 끝 감시(10/13 진우): ① 텔레그램 채널 글 실패 -> 바로 알림 ② 실패했던 채널이 다시 올라가면 '✅ 다시 올라감' 1줄
    ③ 8~24시 Threads 글(개별·묶음·댓글) QUIET_TH(2시간) 넘게 0개 -> '⏸' 1번(다시 올라가기 전까지 반복 X) ④ 예약 글이 시각 + QUIET_EV(20분) 넘게 안 나감 -> 예약마다 1번."""
    now, kst = time.time(), time.gmtime(time.time() + 9 * 3600)
    for k, why in RUN["fail"].items():
        alert(seen, "alert_tg_" + k.replace(" ", "_"), f"⚠️ 텔레그램 채널 게시 실패: {why}\n다음 실행(14분 뒤)에 다시 시도해요", "tg", "텔레그램 채널")
    op = seen.get("alert_open", {}).get("v", {})
    for ch in [c for c in op if c in RUN["ok"] and c not in RUN["failch"]]:
        tg("sendMessage", chat_id=ADMIN, text=f"✅ 다시 올라감: {op.pop(ch)}")
    seen["alert_open"] = {"t": now, "v": op}
    if RUN["th_last"]:
        seen["th_last"] = {"t": RUN["th_last"]}
        seen.pop("quiet_th", None)
    last = seen.setdefault("th_last", {"t": now})["t"]
    ref = max(last, now - (kst.tm_hour - 8) * 3600 - kst.tm_min * 60 - kst.tm_sec)  # 밤(0~8시)은 안 셈 -> 8시부터
    if E.get("THREADS_TOKEN") and kst.tm_hour >= 8 and now - ref > QUIET_TH and "quiet_th" not in seen:
        since, posts = time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 6 * 3600)), load(POSTS, [])
        wait = sum(not p.get("th") and not p.get("shelf") and p["t"] >= since and not p["text"].startswith("📋") and not th_weak(p["text"]) and aff(p.get("url")) for p in posts) \
            + sum(now - x["t"] < 3 * 3600 for x in seen.get("thtoss", {}).get("q", []))
        tg("sendMessage", chat_id=ADMIN, text=f"⏸ Threads {int((now - ref) // 3600)}시간째 글 없음 — 마지막 글 {time.strftime('%H:%M', time.gmtime(last + 9 * 3600))}, "
                                              f"대기 중 {wait}개, 이유: {RUN['th_why'] or '로그 확인'}"[:1000])
        seen["quiet_th"] = {"t": now}
    old, late = time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 3 * 3600)), time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 9 * 3600 - QUIET_EV))
    for ev in load(EVENTS, []):
        at = ev.get("at", "")
        if not old <= at <= late or f"quietev_{at}" in seen:
            continue
        if ev.get("api") and not ev.get("url"):  # 토스 이름 예약 = toss_picks가 찾아서 올림
            st = (seen.get("pk_" + at) or {}).get("st") if isinstance(seen.get("pk_" + at), dict) else None
            if st in ("done", "skip"):
                continue
            why = "토스 이름 예약 — 상품을 아직 못 찾았거나 채널 전송 실패(toss pick 로그)"
        elif "ev_" + at in seen:
            continue
        else:
            why = "행사 목록 — 쿠팡 링크 변환 기다리는 중(cp link 로그)" if ev.get("list") else RUN["tg_err"] or "events 로그 확인"
        tg("sendMessage", chat_id=ADMIN, text=f"⏸ 텔레그램 예약 글 안 나감 — {at[5:]} {clip(ev.get('name') or ev.get('title') or plain_of(ev.get('text') or '').split(chr(10))[0], 40)} (예약 + {QUIET_EV // 60}분 지남), 이유: {why}")
        seen[f"quietev_{at}"] = {"t": now}


def main():
    try:
        seen = json.load(open(SEEN))
    except (OSError, ValueError) as e:
        seen = repr(e)
    if not isinstance(seen, dict):
        if not SEEN_COLD:  # 캐시 못 받음 = 아무것도 안 올림·seen도 안 씀 -> 실패로 끝나 캐시가 안 덮이고(성공 때만 저장) 다음 실행이 다시 받음
            msg = f"⚠️ 봇 기억(seen.json) 못 받음 — 이번 실행 건너뜀(하루 1번 글·예약 중복 게시 방지): {str(seen)[:120]}\n계속되면(캐시가 다 지워짐) Actions → Run workflow → cold_start 체크"
            print(msg)
            try:
                tg("sendMessage", chat_id=ADMIN, text=msg)
            except Exception as e:
                print("alert", repr(e))
            raise SystemExit(1)
        seen = {}
    RUN.update(ok=set(), fail={}, failch=set(), th_last=0, th_why="", tg_err="", ch_last=0, treuse=False, thids=[])
    RUN.pop("cpu", None)
    RUN.pop("cpn", None)
    if TOSS_NO_CMP:
        toss_clean_posts()
    if HAS_CP:  # 쿠팡 API 최근 1시간 호출 시각(실행 사이에도 상한 — coupang())
        RUN["cpu"] = seen.setdefault("cpuse", {"t": 0})
    try:
        toss_mode(seen)  # 토스 점검 재사용 모드(RUN['treuse'])·점검 알림 — 실패해도 실행은 계속
    except Exception as e:
        print("toss mode", repr(e))
    publish_approved(seen)
    new, keys = [], set()
    deals = fetch_deals()
    mark_hot(deals)
    cover = {}  # 출처별 목록이 덮는 시간(가장 오래된 글 나이). 뽐뿌 RSS는 15개뿐 -> 바쁜 저녁엔 30분도 안 돼서 30분 기다리면 영영 못 봄(10/6 17시대)
    for d in deals:
        cover[d["board"]] = max(cover.get(d["board"], 0), d["age"])
    fresh = [d for d in deals if d["id"] not in seen
             and min(MIN_AGE_RULIWEB if d["id"].startswith("ruliweb_") else MIN_AGE, cover[d["board"]] - RUN_GAP) <= d["age"] <= MAX_AGE]
    for d in sorted(fresh, key=lambda d: d["id"].split("_")[0] in FEEDS):  # 같은 딜이면 상품 주소를 얻을 수 있는 루리웹·클리앙 쪽을 남김
        k = dkey(d["title"])
        if k and (seen.get(k, 0) > time.time() - 86400 or k in keys):  # 24시간 안에 다른 커뮤니티에 올라온(또는 이미 판단한) 같은 딜
            seen[d["id"]] = time.time()
            continue
        keys.add(k)
        new.append(d)
    held = []  # 지난 실행에서 넘친 좋은 딜(Claude 판단 그대로). 다시 물으면 점수가 흔들려 7점이 사라짐(10/8 17:21 갈비·MSI 7점 → 15분 뒤 5점 미만)
    for k in [k for k in seen if k.startswith("hold_")]:
        if seen[k]["t"] > time.time() - 3 * 3600:
            held.append(seen[k])
        else:  # 3시간 넘게 못 올린 딜은 식은 딜
            seen.pop(k)
    rank = lambda h: (-h["p"]["score"], not earns(h["d"]["title"]))  # 점수순, 같은 점수면 수수료 되는 딜 먼저
    held.sort(key=rank)
    good = []
    tone = 0  # 채널 한 줄 말투(새 딜을 Claude에 물은 회차만 — 보류했다 올리는 딜은 기록 X)
    if new:
        since = time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - 86400))
        recent = [title_of(p["text"]) for p in load(POSTS, []) if p["t"] >= since and not p["text"].startswith("📋") and not p.get("shelf")][-30:]
        recent += [v["n"] for k, v in seen.items() if k.startswith("tb_") and isinstance(v, dict) and v["t"] > time.time() - 86400]  # 토스 하루특가·베스트 글(posts.json엔 없음)도 — 10/10 케라시스 베스트 10:02 → 같은 딜 10:44
        tone, tsuf = tone_ask(seen, "ch")  # 10/23 진우 말투 4가지(채널 글 한 줄 — 이 회차 딜은 같은 말투)
        prompt = DEAL_PROMPT + tsuf + ("\n최근 24시간에 이미 올린 딜(같은 상품이면 고르지 마):\n" + "\n".join(recent) if recent else "")
        try:
            picks = ai_pick(prompt, [f"[{d['board']}] {d['title']} | {d['hits']} | {d['age']:.0f}분 전 | {d['desc']}" for d in new])
        except Exception as e:  # Claude 오류면 이번엔 딜 판단만 건너뜀(본 글 기록 안 함 -> 다음 실행에 다시). 실행 전체가 죽으면 토스·Threads·리포트도 멈추고 seen 캐시도 안 남음
            print("ai_pick 실패", repr(e))
            if "credit balance" in (getattr(e, "body", "") or ""):  # 10/18 03시쯤 크레딧 바닥 -> 커뮤니티 딜이 조용히 멈춤(토스 단계 알림은 '다음 실행에 다시'로 읽힘)
                alert(seen, "alert_credit", "⚠️ 커뮤니티 딜 판단 멈춤 — " + CREDIT_HINT)
            new = picks = []
        for d in new:  # AI 판단 성공한 뒤에만 '본 글'로 기록 -> 실패 시 다음 실행에서 재시도
            seen[d["id"]] = time.time()
            if dkey(d["title"]):
                seen[dkey(d["title"])] = time.time()
        if new:
            print("점수", [(p["score"], new[p["i"]]["title"][:30]) for p in picks] or "5점 이상 없음")  # 컷 조절용 근거
        ok = lambda p: focus(new[p["i"]]["title"]) or p["score"] >= OTHER_MIN  # 3사가 아니면 대박(8점↑)만
        good = [p for p in picks if ok(p) and p["score"] >= MIN_SCORE - earns(new[p["i"]]["title"])]  # 수수료 되는 몰은 1점 낮춰도(10/10 올리브영 -> 같은 날 진우 '수수료 딜 꼭 챙겨': 5점 링크프라이스 딜 3개가 빠지던 것)
        if not good and not held and picks and quiet():
            best = max(filter(ok, picks), key=lambda p: p["score"], default=None)
            good = [best] if best and best["score"] >= FILL_SCORE else []
        good = sorted(({"d": new[p["i"]], "p": {**{k: v for k, v in p.items() if k != "i"}, "tone": tone}} for p in good), key=rank)  # 말투 = 코멘트를 쓴 회차 것(보관했다 올려도 — 10/23 리뷰)
    today = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600))
    left, drop = OTHER_MAX - sum(p["t"].startswith(today) and not p.get("own") and not p["text"].startswith("📋") and not focus(title_of(p["text"])) for p in load(POSTS, [])), set()
    for h in held + good:  # 3사가 아닌 딜: 8점 미만·오늘 OTHER_MAX개 넘김 = 버림(보관도 X, 보관 중이던 것도)
        if not focus(h["d"]["title"]):
            if h["p"]["score"] < OTHER_MIN or left <= 0:
                drop.add(h["d"]["id"])
                seen.pop("hold_" + h["d"]["id"], None)
            else:
                left -= 1
    held, good = [h for h in held if h["d"]["id"] not in drop], [h for h in good if h["d"]["id"] not in drop]
    for h in (held + good)[:MAX_DRAFTS]:  # 보관해 둔 딜이 먼저
        seen.pop("hold_" + h["d"]["id"], None)
        p = h["p"]
        if HAS_TOSS and store_info(h["d"]["title"], h["d"].get("url")).startswith("💰 토스"):  # 10/18 진우 '뽐뿌 말고 바로 연결': 토스 딜은 쉐어링크를 찾은 뒤에 게시(아래 toss_wait 단계가 이번 실행부터)
            seen["tw_" + h["d"]["id"]] = {**h, "t": time.time()}
            continue
        if not post_or_draft(h["d"], p["comment"], p["score"], p.get("q"), {k: p.get(k) for k in ("e", "hook", "pts", "unit", "warn", "who", "use", "tone")}):  # 채널 게시(초안 X)일 때만 말투 기록
            tone_keep(seen, "ch", p.get("tone"))
    for h in good[max(0, MAX_DRAFTS - len(held)):]:  # 넘친 좋은 딜은 다음 실행에 다시 묻지 않고 올리게 보관
        seen["hold_" + h["d"]["id"]] = {"t": time.time(), **h}
    for step in (daily_cands, site_relink, cp_links, link_swap, shelf_posts, toss_shelf, events, preview, playlist, goldbox, lambda s: cp_events(s, deals), top_deals, pick_post, steady_list, pair_post, weather_post, cal_post, curation, drop_post, snack_post, poll_post, toss_deals, lambda s: toss_deals(s, True), lambda s: toss_deals(s, "cat"), lambda s: toss_deals(s, "beauty"), lambda s: toss_deals(s, "special"), toss_wait, toss_relink, toss_picks, toss_solo, cp_repost, toss_soldout, toss_takedown, toss_fix_channel, lambda s: digest(s, load(POSTS, [])), cat_fill, threads, threads_deals, daily_post, daily_log, wx_dm, toss_reopen, ig_cards, ig_feed, ig_guess, ig_comments, ig_reel, reel_samples, clip_post, ig_repost, ig_publish, ig_stage, ig_test, toss_stock, coupang_remind, oy_claim, report, th_retry, cmp_report, th_reply_ok, th_verify, th_watch, metrics, ig_peek, gc_top, link_ab, promo_links, mall_icons, api_check, cp_best, cp_price, own_end, drop_check, toss_roster, th_end_report):
        try:
            step(seen)
        except Exception as e:
            print(step.__name__, repr(e))
            step_alert(seen, step, e)  # 10/13 진우 '업로드 안 되면 바로 알람': 하루 1번 -> 바로(같은 단계·같은 오류는 3시간에 1번), Threads·인스타 + 채널 글 단계(ALERT_STEPS)
    if RUN.get("igc"):  # 하루 합계(KST)도 — README 점검 표
        d = seen.setdefault(time.strftime("igapi_%Y%m%d", time.gmtime(time.time() + 9 * 3600)), {"n": 0})
        d.update(t=time.time(), n=d["n"] + RUN["igc"])
        print("ig api", RUN["igc"], "calls · 오늘", d["n"])
    try:
        watch(seen)
    except Exception as e:  # 감시가 실패해도 seen은 저장
        print("watch", repr(e))
    if RUN["ch_last"]:
        seen["ch_last"] = {"t": RUN["ch_last"]}
    cutoff = time.time() - 3 * 86400
    json.dump({k: v for k, v in seen.items() if (v["t"] if isinstance(v, dict) else v) > cutoff}, open(SEEN, "w"))  # hold_ = 딜째 보관
    print(f"new={len(new)} seen={len(seen)}")


if __name__ == "__main__":
    main()
