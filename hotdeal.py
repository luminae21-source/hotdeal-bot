#!/usr/bin/env python3
"""핫딜봇: 뽐뿌·루리웹·클리앙 핫딜 -> Claude 선별/코멘트 -> 채널 바로 게시.
상품 주소가 있으면(루리웹·클리앙 글) 링크프라이스 승인 몰은 상품 페이지 제휴 링크 자동, 없으면(뽐뿌: GitHub IP 차단) 검색 제휴 링크.
쿠팡·네이버 등 수동 몰은 관리자에게 사본(+쿠팡은 파트너스 검색 버튼, 네이버는 상품명 복사·쇼핑커넥트 버튼, 그 외 상품 열기 버튼) -> 제휴 링크를 답장(또는 그냥 전송)하면 채널 글 교체. 쿠팡 골드박스는 매일 7시 이후 1번 채널에 바로(키 없으면 골드박스 링크, 있으면 TOP5).
GitHub Actions에서 15분마다 실행(tick.yml 타이머가 workflow_dispatch로 실행 + 예약 보조). 외부 패키지 없음(파이썬 표준 라이브러리만)."""
import base64, hashlib, hmac, html, json, os, re, shutil, tempfile, time, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from build_site import BASE as SITE, BLOG, GOLDBOX, NOTE_STARTS, title_of, split_title, parse, react, TOSS_HOSTS, NAVER_HOSTS, AFF_HOSTS, OY_HOSTS, toss_share, day_deals, card_order, saving, buy_label, aff, CATS, CARD_N, SLOT_NAMES, card_name, SAVE_STORES, STEM, unit_of  # 제휴 도메인은 사이트와 같이 씀

E = {k: "".join(v.split()) for k, v in os.environ.items()}  # 시크릿 붙여넣을 때 섞인 공백·줄바꿈 전부 제거
ADMIN, CHANNEL = E.get("TG_ADMIN_ID", ""), E.get("TG_CHANNEL", "")
MODEL = E.get("MODEL") or "claude-sonnet-5-5"
MIN_SCORE = int(E.get("MIN_SCORE") or 6)  # 10/8 진우: 6점도 바로(그 전 7)
HAS_CP = bool(E.get("COUPANG_ACCESS_KEY") and E.get("COUPANG_SECRET_KEY"))
HAS_TOSS = bool(E.get("TOSS_ACCESS_KEY") and E.get("TOSS_SECRET_KEY") and E.get("TOSS_PUBLISHER_ID"))  # 쉐어링크 Open API(10/6 승인). 호출은 고정 IP(오라클) 터널 경유 -> hotdeal.yml
TOSS_API, TOSS_TOKEN = "https://sharelink.toss.im/openapi", "toss.json"  # toss.json: 1년짜리 액세스 토큰 보관(Actions 캐시, 매번 재발급 금지)
MAX_DRAFTS = 1                 # 1회 실행(15분)당 채널 게시 최대 개수. 몰아 올리면 묻히고 뒤가 비어서 1개씩(10/6 진우 '꾸준하게') -> 넘친 딜은 판단 그대로 보관했다가 다음 실행에 먼저
GAP_FILL, FILL_SCORE = 45, 6    # 8~24시에 45분 넘게 채널 딜 글이 없으면 그 실행 후보 중 6점↑ 최고 1개로 빈틈 메움(5점은 안 올림). MIN_SCORE가 6이면 6점은 원래 바로 올라가서 MIN_SCORE를 7로 올렸을 때만 쓰임
MIN_AGE, MAX_AGE = 30, 360     # 분: 반응이 쌓인 뒤 판단, 너무 오래된 글은 무시
MIN_AGE_RULIWEB = 15           # 루리웹 RSS엔 추천·댓글 수가 없어 기다려도 판단 근거가 안 늘어남 -> 빨리
RUN_GAP = 20                   # 분: 다음 실행까지(15분 체인 + 지연 여유). 이 안에 목록에서 밀려날 글은 덜 묵었어도 지금 판단
FEEDS = {"ppomppu": "뽐뿌"}  # 뽐뿌 보드 추가: {"rss id": "표시명"}
RULIWEB_RSS = "https://bbs.ruliweb.com/market/board/1020/rss"  # 루리웹 핫딜예판: RSS + 글 아래 '출처'에 상품 주소 (robots 허용, GitHub 서버 OK 10/5)
CLIEN_LIST = "https://www.clien.net/service/board/jirum"  # 클리앙 알뜰구매: RSS 없음 -> 목록 HTML, 글 위 '구매링크' (robots: 쿼리 없는 /service/board/ 허용)
KST = timezone(timedelta(hours=9))
SEEN, POSTS = "seen.json", "posts.json"  # posts.json: 채널에 게시된 딜 -> build_site.py가 웹사이트로 만듦
EVENTS = "events.json"  # 예약 게시(쿠가세 같은 행사): [{"at": "YYYY-MM-DD HH:MM"(KST), "text": HTML, "button", "url": 파트너스 링크}] — Claude가 저장소에 넣음
CP_NEWS = "https://newsis.com/RSS/industry.xml"  # 뉴시스 산업 RSS(기사 전문) -> 쿠팡 행사(○○데이·기획전) 자동 게시 — cp_events(). 쿠팡 뉴스룸은 GitHub 서버 403(10/9, 우회 안 함)
CP_HOME, CP_FRESH = "https://link.coupang.com/a/hHgmfLTIUm", "https://link.coupang.com/a/hHgxjTMio8"  # 파트너스 간편 링크(10/9 진우, 이름 붙여 보낸 것): 쿠팡 홈·로켓프레시 — 행사 글 버튼
REPOST = "ig_repost.txt"  # 오늘 인스타 카드를 1번 다시 올릴 때 날짜(YYYY-MM-DD) 한 줄 — ig_repost()
MUSIC = "music.json"  # 릴스 배경음악 목록: Pixabay 음원 주소(Claude가 고름) 또는 봇에 보낸 음악의 텔레그램 file_id. 음원 파일은 공개 저장소에 안 올림(무료 음원도 원본 재배포는 금지)
IG = "https://graph.%s.com/v25.0" % ("facebook" if E.get("IG_TOKEN", "").startswith("EAA") else "instagram")  # 인스타 자동 게시. IG_TOKEN = 앱 대시보드 '계정 추가'로 받은 Instagram 토큰(IGAA…, 60일, 카드 사진 자동) — 페이스북 페이지 토큰(EAA…)이면 페이스북 주소(릴스 영상 파일 업로드까지)
CP_HOST, CP_BASE = "https://api-gateway.coupang.com", "/v2/providers/affiliate_open_api/apis/openapi/v1"
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
IG_SLOTS = {12: "점심에 볼 딜", 18: "퇴근길에 볼 딜"}  # 인스타 하루 3번(10/11 진우 '인스타 업그레이드 1번'): 12시 = 0~12시 딜, 18시 = 12~18시 딜 카드 + 21시 하루 카드(모아보기) — 7일 표에서 채널 글이 가장 많은 12·18시(TOP5 회차와 같은 시간대)
IG_LATE, IG_MIN, IG_DAY_MAX = 3, 3, 5  # 시간대 카드는 그 시각 3시간 안에만(늦게 몰아 안 올림) · 딜 3개 미만이면 건너뜀 · 인스타 하루 발행 최대 5개(카드 3 + 릴스 1 + 다시 올리기 1, 오류로 몰려 올라가지 않게 — API 상한 50)
IG_CAROUSEL, SLIDE_KEEP, KIDS_WAIT = True, 2, 3600  # 넘기기(10/11 진우 '인스타 업그레이드 2번'): 표지 + 딜마다 1장(False면 1단계 한 장 카드) · 딜 카드는 인스타가 가져간 뒤 2일 지나면 지움(저장소 크기) · 조각 처리 1시간 넘으면 버림
OY_DENY = r"후기|리뷰|추천|댓글|반응|좋|최고|100%|효과|효능|강추|쟁여|인생|대박|미백|주름|탄력|개선"  # 올리브영 딜 카드에서 빼는 말(큐레이터 정책: 가격·용량·구성·조건만)
IG_TRIES, IG_SITE_LAG = 3, 300  # 카드 컨테이너 만들기 실패(인스타 일시 오류)는 회차 안에서 3번까지 다시(안 올라간 컨테이너는 안 보여서 두 번 안 올라감) · 카드는 사이트 맨 위에 먼저(만든 실행) -> 5분 넘은 다음 실행에 발행
IG_TAGS, IG_CAT_TAGS, IG_FILL_TAGS, IG_TAG_MAX = ("#핫딜", "#특가", "#핫딜픽"), {"life": "#생필품", "beauty": "#화장품"}, ("#살림템", "#쇼핑정보"), 5  # 해시태그 5개(근거 없는 #최저가 뺌, 카테고리 태그는 그날 딜에 있을 때만)
TOP_HOURS = (12, 18)  # 커뮤니티 반응 좋은 딜 TOP5 묶음 글(10/9 진우 '사람들이 사는 제품을 보기 좋고 사고 싶게') — top_deals()
NUM = "1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣".split()
TOSS_DAY_HOURS = (9, 13, 17)  # 하루특가(= 토스 앱 '매일 밤 12시 선착순특가') 회차, 회차마다 안 올린 것 최대 5개 (10/10 진우가 선착순 상품 링크를 직접 보내다가 '이 작업도 자동으로')
TOSS_BEST_HOURS = (10, 11, 12, 14, 16, 18, 20)  # 10/11 진우 '회차 늘리기, 적절하게': 7일 표에서 묶음 글 없는 11시 추가(12시는 TOP5와 겹침). 줄이려면 여기서 빼기. 토스 '지금 많이 팔리는 상품'(1시간마다 갱신) 중 Claude가 살 만한 것만: 10~20시 2시간마다 (10/7 진우 제안 2번 -> 10/8 3번 -> 10/9 '쿠팡·토스 주력' 6번)
TOSS_BEAUTY_HOURS = (15, 19)  # 토스 뷰티(화장품) 카테고리 베스트 중 살 만한 것 (10/11 진우 '화장품도 올리자' -> '화장품도 발굴': 저녁 1번 더 = 7일 표에서 저녁 중 가장 조용하고 묶음 글 없는 19시)
AD_FIRST = "2026-10-12"  # 10/11 진우 결정(조회는 되는데 구매가 적음 -> 집중 모드 10/12~10/25): 이 날(KST)부터 개별 딜 글(채널·Threads) 첫 줄 '[광고] + 훅 + 상품 + 가격', 둘째 줄 제휴 고지문 그대로. "" = 예전(고지문이 첫 줄)


def ad_on():
    return bool(AD_FIRST) and time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600)) >= AD_FIRST
PREVIEW_HOUR, PREVIEW_MIN, PREVIEW_TH = 22, 3, 5  # 10/11 진우 '묶음 리스트도, 꾸준함이 중요': 매일 밤 10시 '🌙 오늘 밤 특가 미리보기'(진우 예약 딜 중 지금~다음 날 8시) — 진우 예약은 17~24시에 몰림(10/10 20~22시 34개, 10/11 밤 19개)·토스 하루특가는 밤 12시에 바뀜 · 3개 미만이면 21시 모아보기에 합침 · Threads는 앞 5개(500자)
BUNDLE_GAP, HOUR_CAP = 600, 8  # 10/11 진우 '너무 자주 올리면 역효과': 묶음 글(토스 회차·TOP5·모아보기)은 앞 묶음 글과 10분 이상 띄움 / 토스 회차는 최근 1시간 채널 글이 8개 이상이면 미룸(7일 표: 평소 시간당 최대 6개 -> 진우 예약이 몰린 시간에만 걸림)
TH_REOPEN_GAP, TH_REOPEN_HOUR, TH_REOPEN_AM = 600, 3, (8, 11)  # 10/11 진우 '토스 품절 풀리면 다시 쓰레드에, 자정 + 아침 8시': 재게시끼리 10분(= 실행당 1개) · 1시간 최대 3개(7일 표: 0~3시 채널 시간당 1~4.5개, 8시 2개 -> 그 시간 평소 글 수 수준) · 아침 재알림은 8~11시(놓치면 낮에 몰아 안 올림)
TOSS_SPECIAL_HOURS, SPECIAL_DR, SPECIAL_RC = (8, 22), 40, 50  # 10/11 진우 '특가 탭 자동으로': 토스 특가(할인 40%↑·리뷰 50개↑) 회차 — 7일 표에서 묶음 글 없는 아침 8시(시간당 2개)·밤 22시(4개), 회차 3시간 안에만. 줄이려면 여기서 빼기
PICK_AHEAD, PICK_LATE, PICK_SCAN, PICK_ASK = 8 * 3600, 3 * 3600, 10, 90 * 60  # 토스 이름 예약(toss_picks): 8시간 전부터 찾음 · 예약 시각 3시간 지나면 안 올림 · 못 찾으면 하위 카테고리 베스트 하루 10개(1,000개 — 일 상한 10,000 안)까지 더 봄 · 그래도 없거나 90분 전이면 진우에게 링크 요청
BEAUTY = dict((k, rx) for k, _, rx in CATS)["beauty"]  # 화장품 제목 키워드(사이트 '💄 화장품' 칸과 같음)
TOSS_CAT_HOUR, TOSS_CATS = 17, ("식품", "생활용품")  # 카테고리 베스트(매일 9시 갱신) 중 살 만한 것: 하루 1번 (10/8 진우: 베스트 랭킹 페이지). 이름 = 카테고리 트리 최상위


def http(url, body=None, headers=None, method=None):
    h = {"User-Agent": UA, **(headers or {})}
    if body is not None and not isinstance(body, bytes):  # bytes = 폼 등 이미 인코딩된 본문(Content-Type은 headers로)
        body, h["Content-Type"] = json.dumps(body).encode(), "application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, body, h, method=method), timeout=30) as r:
            return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")
    except urllib.error.HTTPError as e:
        e.body = e.read().decode("utf-8", "replace")[:300]  # 로그에서 원인 바로 보이게
        print("HTTP", e.code, url.split("/bot")[0], e.body)
        raise


def tg_video(path, caption):
    """관리자에게 영상 파일 업로드 (sendVideo, multipart). -> 보낸 메시지"""
    b = "hotdeal" + os.urandom(8).hex()
    fields = {"chat_id": ADMIN, "caption": caption, "supports_streaming": "true", "width": "1080", "height": "1920"}
    body = ("".join(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n' for k, v in fields.items())
            + f'--{b}\r\nContent-Disposition: form-data; name="video"; filename="reel.mp4"\r\nContent-Type: video/mp4\r\n\r\n').encode() \
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
        return json.loads(http(f"https://api.telegram.org/bot{E['TG_TOKEN']}/{method}", params))["result"]
    except urllib.error.HTTPError as e:
        print("TG", method, e.code, e.body)


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
                           "pts": {"type": "array", "items": {"type": "string"}}, "unit": {"type": "string"}, "warn": {"type": "string"}}}}}}}
    r = json.loads(http("https://api.anthropic.com/v1/messages", {
        "model": MODEL, "max_tokens": 4000, "tools": [tool], "tool_choice": {"type": "auto"},
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


def coupang(method, path, body=None):
    dt = time.strftime("%y%m%dT%H%M%SZ", time.gmtime())
    p, _, q = (CP_BASE + path).partition("?")
    sig = hmac.new(E["COUPANG_SECRET_KEY"].encode(), (dt + method + p + q).encode(), hashlib.sha256).hexdigest()
    auth = f"CEA algorithm=HmacSHA256, access-key={E['COUPANG_ACCESS_KEY']}, signed-date={dt}, signature={sig}"
    return json.loads(http(CP_HOST + CP_BASE + path, body, {"Authorization": auth}, method))["data"]


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


def affiliate(url):
    """쇼핑몰 주소 -> (버튼 링크, 제휴여부). 쿠팡: API 키 있으면 파트너스 링크. 토스: 쉐어링크 API(상품 주소의 tacaId).
    그 외: 링크프라이스 딥링크 API (승인된 몰이면 상품 페이지 딥링크 — 새로 승인된 몰도 코드 수정 없이 바로 적용). API 장애 땐 LP_HOSTS로 직접."""
    host = urllib.parse.urlsplit(url or "").netloc.lower()
    taca = HAS_TOSS and re.match(r"https://toss\.shopping/t/(\d+)", url or "")
    if taca:  # 실패(발급 제한 상품 등)하면 상품 주소 그대로 -> 관리자 사본으로 수동
        try:
            return toss("/links", {"tacaId": int(taca.group(1)), "publisherId": E["TOSS_PUBLISHER_ID"]})["shortUrl"], True
        except Exception as e:
            print("toss link", repr(e))
            return url, False
    if HAS_CP and host.endswith("coupang.com"):
        try:
            return coupang("POST", "/deeplink", {"coupangUrls": [url]})[0]["shortenUrl"], True
        except Exception as e:
            print("deeplink", repr(e))
    if not url:
        return url, False
    try:
        r = json.loads(http(LP_API.format(LP_AID, urllib.parse.quote(url, safe=""))))
        return (r["url"], True) if r.get("result") == "S" and r.get("url") else (url, False)
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


def deal_post(d, comment, q=None, extra=None):
    """-> (본문, 버튼 링크, 버튼 이름). 상품 주소가 있으면 쿠팡 API·링크프라이스 상품 딥링크 > 링크프라이스 검색 링크
    > 상품 페이지(제휴 없음, 관리자 사본으로 수동) > 그 몰 검색 결과(MALL_SEARCH, 10/10~) > 원글. 제휴 링크면 대가성 문구를 맨 앞에.
    extra의 unit(단위가격)·warn(확인할 점)이 있으면 코멘트 아래 한 줄씩 (다른 핫딜 채널과의 차이: 비교 근거 + 단점까지)."""
    link, aff = affiliate(store_link(d["url"]))
    label = buy_label(d["title"])
    if not aff:
        lp, name = lp_search(d["title"], q)
        if not lp and not link:  # 상품 주소도 제휴 검색도 없으면 원글 대신 그 몰 검색 결과(원글은 본문 '출처' 링크로 남음). 토스·모르는 몰·앱 쿠폰은 원글 그대로
            name, base = next((v for k, v in MALL_SEARCH.items() if k in store_tag(d["title"])), (None, None))
            lp = base and base + urllib.parse.quote(q or keyword(d["title"]))
        if lp:
            link, label = lp, f"🔎 {name}에서 찾기"
    note = aff_note(link or "")
    x = extra or {}
    facts = "".join(f"\n{icon} {esc(x[k])}" for k, icon in (("unit", "💡 단위가격"), ("warn", "⚠️ 확인할 점")) if x.get(k))
    head = ad_head(note, f"🔥 {d['title']}\n\n{comment}", x.get("unit") or "")  # 공정위 지침: 대가성 문구는 첫 부분에 — 1줄 [광고] 첫 줄 + 2줄 고지문(10/11 진우 결정)
    badge = f"\n🏆 <b>인기</b> · {esc(d['hot'])}" if d.get("hot") else ""  # 제목 바로 아래(제목 줄은 사이트 split_title이 첫 줄로 읽음)
    text = f"{head}🔥 <b>{esc(d['title'])}</b>{badge}\n\n{esc(comment)}{facts}\n\n출처: <a href=\"{esc(d['url'])}\">{d['board']}</a>"
    return text, link or d["url"], label


def record(text, ents, url, mid=None, score=None, extra=None):
    """채널에 올라간 글 -> posts.json (웹사이트·모아보기·카드·릴스 재료). mid = 채널 메시지 번호(나중에 링크 교체용),
    s = Claude 점수(릴스 TOP3), extra = 릴스용 e(이모지)·hook(첫 화면 한 줄)·pts(합리적인 이유)."""
    posts = load(POSTS, [])
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
    return next((p for p in reversed(load(POSTS, [])) if shop and p.get("cp") and p.get("mid") and p["t"] >= since
                 and not aff_note(p.get("url") or "") and store_info(title_of(p["text"]), p.get("url")).startswith("💰 " + shop)), None)


def aff_note(url):
    """제휴 링크면 그 프로그램의 대가성 문구, 일반 쇼핑몰 주소면 ''."""
    host = urllib.parse.urlsplit(url).netloc
    return (DISCLOSURE if host == "link.coupang.com" else TOSS_NOTE if toss_share(url) else NAVER_NOTE if host in NAVER_HOSTS
            else OY_NOTE if host in OY_HOSTS else AFF_NOTE if host in AFF_HOSTS else "")


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
    h = ad_hook(plain, unit)
    if not h:
        return f"[광고] 🔥 {pp}"
    k = int(hashlib.md5(name.encode()).hexdigest(), 16) % 3
    return ("[광고] {e} {adj} {pp}", "[광고] {pp} — {sent}", "[광고] {e} {sent} · {pp}")[k].format(e=h[0], adj=h[1], sent=h[2], pp=pp)


def ad_head(note, plain, unit="", html_=True):
    """개별 딜 글 머리: 1줄 [광고] 첫 줄 + 2줄 제휴 고지문(그대로) + 빈 줄. 제휴 링크가 아니면(note 없음) ''."""
    if not note:
        return ""
    if not ad_on():
        return f"<i>{note}</i>\n\n" if html_ else f"{note}\n\n"
    a = ad_line(plain, unit)
    return f"{esc(a)}\n<i>{note}</i>\n\n" if html_ else f"{a}\n{note}\n\n"


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
    text, ents = with_note(notice.get("text", ""), notice.get("entities", []), url)
    kb = [[{"text": buy_label(title_of(notice.get("text", ""))), "url": url}]]
    if not tg("editMessageText", chat_id=CHANNEL, message_id=mid, text=text, entities=ents,
              link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": kb}):
        return
    tg("editMessageText", chat_id=notice["chat"]["id"], message_id=notice["message_id"], text=text, entities=ents,
       link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": kb + [[{"text": "✅ 채널 글 교체됨", "callback_data": "-"}]]})
    posts = load(POSTS, [])
    for p in posts:
        if p.get("mid") == mid:
            p.update(text=text, entities=ents, url=url)
    json.dump(posts, open(POSTS, "w"), ensure_ascii=False)
    return True


def relink(m, url):
    """초안 m의 구매 버튼을 url로 교체(제휴 링크면 대가성 문구를 맨 앞에) -> (text, entities, 버튼 rows)."""
    text, ents = with_note(m.get("text", ""), m.get("entities", []), url)
    rows = [[{"text": "🛒 구매하러 가기", "url": url}]]
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


def admin_deal(lines, link, mid):
    """관리자가 봇에 '상품명·가격 줄 + 제휴 링크'를 새로 보내면(10/10 진우 '봇에 링크+가격 보내면 자동') Claude가 코멘트·단위가격·확인할 점을 달아
    채널에 바로 + posts.json(사이트·모아보기). 링크는 서버에서 열지 않음(파트너스 자기 클릭 방지) -> 적힌 정보로만 판단.
    채널 점수 컷(MIN_SCORE, 수수료 몰 -1) 미만이면 🛒 + '솔직히 특가로는 약한 제품' 줄(10/10 진우 '특가로는 약한 제품이라고 써 보자').
    처리했으면 True, Claude 오류·응답 없음·채널 실패면 False(-> 지금처럼 초안 ✅)."""
    if any(link_key(x.get("url")) == link_key(link) for x in load(POSTS, [])[-80:]):  # 15분 안 바뀌어서 다시 보낸 링크(대소문자·끝 / 달라도) -> 두 번 안 올림
        tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": mid}, text="이미 채널에 올린 링크야")
        return True
    title = admin_title(lines[0], link)
    try:
        p = (ai_pick(ADMIN_PROMPT, [f"[운영자] {title} |  | 0분 전 | {' / '.join(lines[1:])}"]) or [None])[0]
    except Exception as e:
        print("admin ai_pick 실패", repr(e))
        return False
    if not p:
        return False
    facts = "".join(f"\n{icon} {esc(p[k])}" for k, icon in (("unit", "💡 단위가격"), ("warn", "⚠️ 확인할 점")) if p.get(k))
    weak = p["score"] < MIN_SCORE - (earns(title) or aff(link))  # 진우 제휴 링크 = 수수료 되는 딜 -> 1점 완화(네이버는 EARN_TAGS에 없음: 커뮤니티 [네이버] 딜은 진우가 링크를 만들어야 수수료라서)
    m = tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", text=ad_head(aff_note(link), f"🔥 {title}\n\n{p['comment']}", p.get("unit") or "") + f"{'🛒' if weak else '🔥'} <b>{esc(title)}</b>\n\n"
           + ("🤔 솔직히 특가로는 약한 제품\n" if weak else "") + f"{esc(p['comment'])}{facts}",
           link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": [[{"text": buy_label(title), "url": link}]]})
    if not m:
        return False
    record(m.get("text", ""), m.get("entities", []), link, m.get("message_id"), p["score"], {**{k: p.get(k) for k in ("e", "hook", "pts", "unit", "warn")}, "own": 1})  # own: 진우가 보낸 링크 -> Threads 엄선에서 안 빠짐
    tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": mid}, text=f"✅ 채널에 올림 (Claude {p['score']}점{' · 특가로는 약함 표시' if weak else ''})",
       reply_markup={"inline_keyboard": [[{"text": "📢 채널 글", "url": post_url(m["message_id"])}]]})
    return True


def publish_approved():
    """관리자 입력 처리. 텔레그램이 입력을 24시간 보관하므로 15분 주기로 충분.
    1) 사본·초안에 링크로 답장 -> 구매 버튼 교체 (쿠팡·토스·네이버 링크는 답장 없이 링크만 보내도 가장 최근 같은 몰 사본)
    2) 봇에게 '제목 줄 + 링크' 새로 보내기 -> 제휴 링크면 Claude 코멘트 달아 채널에 바로(admin_deal, 10/10~), 아니면·실패면 그 딜 초안 생성
    3) ✅/❌ -> 채널 게시/패스 (답장하고 바로 ✅ 눌러도 교체된 링크로 게시)
    4) 음악 파일 보내기 -> 릴스 배경음악 목록(music.json)에 추가"""
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
               text=f"🎵 릴스 배경음악 등록 (총 {len(mus)}곡, 날마다 돌아가며 사용)")
            continue
        text = m.get("text") or m.get("caption") or ""  # 사진에 글을 붙여 보내도(캡션)
        urls = [u.rstrip(").,]>」』'\"") for u in re.findall(r"https?://\S+", text)]  # (링크) 처럼 괄호·문장부호가 붙어도 링크만
        link = next((u for u in urls if aff_note(u)), urls[0] if urls else None)  # 상품 주소 + 제휴 링크를 같이 보내면 제휴 링크로
        if not link or str(m.get("from", {}).get("id")) != ADMIN:
            continue
        if "<iframe" in text:  # 파트너스 배너 코드는 사이트용 -> 단축 URL로
            tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": m["message_id"]}, text="iframe 말고 단축 URL(link.coupang.com/a/…)로 보내줘")
            continue
        if m.get("reply_to_message"):
            rm = m["reply_to_message"]
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
        if not lines and any(link_key(x.get("url")) == link_key(link) for x in load(POSTS, [])[-80:]):  # 링크만 또 보냄 -> 다른 글 버튼을 또 바꾸지 않음
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
        if not (note and admin_deal(lines, link, m["message_id"])):
            title = admin_title(lines[0], link) if note else lines[0]  # 초안도 채널 글과 같은 제목·버튼([몰]·가격)
            draft(ad_head(note, f"🔥 {title}\n\n{body}") + f"🔥 <b>{esc(title)}</b>" + (f"\n\n{esc(body)}" if body else ""),
                  link, info="🤖 자동 게시 실패(Claude 오류·채널 실패) · ✅ 누르면 게시" if note else None, label=buy_label(title) if note else "🛒 구매하러 가기")
    handled = set()
    for u in ups:
        q = u.get("callback_query") or {}
        m = q.get("message")
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
    items = coupang("GET", "/products/goldbox")[:40]
    picks = ai_pick(GOLD_PROMPT, [f"{x['productName']} | {int(x['productPrice']):,}원" for x in items])[:5]
    rows = [f"{n}. <a href=\"{esc(x['productUrl'])}\">{esc(x['productName'])}</a> — <b>{int(x['productPrice']):,}원</b>\n"
            f"   {esc(p['comment'])}" for n, p in enumerate(picks, 1) for x in [items[p["i"]]]]
    m = rows and tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True},
                    text=f"<i>{DISCLOSURE}</i>\n\n⏰ <b>오늘의 쿠팡 골드박스 TOP{len(rows)}</b>\n\n" + "\n\n".join(rows),
                    reply_markup={"inline_keyboard": [[{"text": "⏰ 골드박스 전체 보기", "url": GOLDBOX}]]})
    if m:
        record(m.get("text", ""), m.get("entities", []), GOLDBOX, m.get("message_id"))
    if m or not rows:  # 살 만한 게 없으면 오늘은 안 올림(15분마다 다시 고르지 않게)
        seen[key] = time.time()


def events(seen):
    """예약 게시: 시각이 됐고 6시간 안 지났으면 채널에 1번(제휴 링크면 그 대가성 문구 맨 앞, "pin": true면 채널 맨 위 고정, "deal": true면 딜로 기록). 놓친 지 오래된 글은 안 올림(식은 글)."""
    kst = lambda h: time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + h * 3600))
    for ev in load(EVENTS, []):
        key = "ev_" + ev["at"]
        if key in seen or (ev.get("api") and not ev.get("url")) or not (kst(9 - 6) <= ev["at"] <= kst(9)):  # api(링크 없음) = 토스 API 상품 이름 예약 -> toss_picks가 찾아서 올림
            continue
        note = aff_note(ev["url"])
        m = tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True},
               text=ev_head(ev) + ev["text"], reply_markup={"inline_keyboard": [[{"text": ev["button"], "url": ev["url"]}]]})
        if m:
            seen[key] = time.time()
            if ev.get("name") and toss_share(ev["url"]):  # 진우 토스 예약 -> 품절 지켜보기(toss_soldout): 이 글 번호·이 예약의 본문 그대로(같은 링크를 두 번 예약해도 안 섞임)
                seen[f"sold_{m['message_id']}"] = sold_ev(ev, time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600)))
            if ev.get("deal"):  # Claude가 예약한 상품 딜(10/10 진우 '쓰레드에 업로드 되게') -> posts.json = 사이트·모아보기·Threads에도
                record(m.get("text", ""), m.get("entities", []), ev["url"], m["message_id"], extra={"tag": ev.get("tag"), "own": 1})  # "tag": "정품" -> 사이트 정품 배지·칸(10/10)
            if ev.get("pin"):  # 10/10 채널 고정 글(사용법). 봇에 고정 권한이 없으면 글만 남음 -> 진우가 길게 눌러 고정
                tg("pinChatMessage", chat_id=CHANNEL, message_id=m["message_id"], disable_notification=True)


def night_deals(seen, since, until):
    """진우 예약 딜(events.json의 링크 있는 deal — 토스 API 이름 예약은 빼고, 사이트 표시·쿠팡 비교 금지 그대로) 중 since~until(KST 'YYYY-MM-DD HH:MM')에 나갈,
    아직 안 나간 것 -> [{"at", "icon", "name", "price", "sv", "url"}] 시각 순. sv = 같은 상품 쿠팡 비교('…보다 N원 쌈' 문장)일 때만 ('쿠팡', 'N원')."""
    out = []
    for ev in sorted(load(EVENTS, []), key=lambda e: e["at"]):
        if not (ev.get("url") and ev.get("deal") and not ev.get("api")) or "ev_" + ev["at"] in seen or not since <= ev["at"] < until:
            continue
        plain = html.unescape(re.sub(r"<[^>]+>", "", ev["text"]))
        store, name, price = parse(re.sub(r"^[^\[]*", "", plain.split("\n")[0]).strip())
        sv = re.search(rf"({SAVE_STORES})\s*같은 상품[^\n—]*?보다\s*([\d,]+원)\s*쌈", plain)  # '같은 상품'이라고 쓴 비교만(다른 상품·단위가격 참고는 X)
        out.append({"at": ev["at"], "icon": "🛒" if "특가로는 약한 제품" in plain else "🔥", "name": clip(name, 26), "price": price.split("/")[0].strip(),
                    "sv": sv and sv.groups(), "url": ev["url"]})
    return out


def night_window(now):
    """미리보기 범위: 지금(KST) ~ 다음 아침 8시."""
    kst = time.gmtime(now + 9 * 3600)
    return time.strftime("%Y-%m-%d %H:%M", kst), time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600 + (86400 if kst.tm_hour >= 8 else 0))) + " 08:00"


def night_line(d, link=True):
    """미리보기 한 줄: '22:20 🔥 메르헨트 폼클렌징 500ml 2개 11,900원 · 💡 쿠팡 같은 상품보다 6,000원 쌈'."""
    name = f'<a href="{esc(d["url"])}">{esc(d["name"])}</a>' if link else d["name"]
    return f"{d['at'][11:]} {d['icon']} {name} {d['price']}" + (f" · 💡 {d['sv'][0]} 같은 상품보다 {d['sv'][1]} 쌈" if d["sv"] else "")


def preview(seen):
    """매일 밤 10시 '🌙 오늘 밤 특가 미리보기'(10/11 진우 '리스트 필요, 꾸준함이 중요' — 팔로워가 이 시간엔 리스트가 뜬다고 알게): 진우 예약 딜 중
    지금~다음 날 8시에 나갈 것(PREVIEW_MIN개 이상)을 시간표로 채널에 1번(시각·짧은 이름·링크·가격·같은 상품 쿠팡 차이, 대가성 문구 맨 앞) + Threads(앞 PREVIEW_TH개 + 전체 목록 링크).
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
    top = sorted(sorted(ds, key=lambda d: d["icon"] == "🛒")[:PREVIEW_TH], key=lambda d: d["at"])  # 약한 딜(🛒)은 뒤로 -> 앞 5개, 다시 시각 순
    notes = "\n".join(dict.fromkeys(aff_note(d["url"]) for d in ds if aff_note(d["url"])))
    full = post_url(m["message_id"])
    head, lines = (notes + "\n\n" if notes else "") + f"🌙 오늘 밤 특가 미리보기 ({len(ds)}개)\n\n", [night_line(d, False) for d in top]
    while True:  # Threads 500자: 대가성 문구·전체 링크는 그대로, 줄을 줄임
        th = head + "\n".join(lines) + (f"\n… 외 {len(ds) - len(lines)}개" if len(ds) > len(lines) else "") + f"\n\n전체 {len(ds)}개·구매 링크 👉 {full}"
        if len(th) <= 480 or len(lines) <= 1:
            break
        lines = lines[:-1]
    me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
    th_text(tok, me, th, full)


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
    posted = "\n".join(p["text"] for p in load(POSTS, [])[-80:])  # 딜로 이미 올라간 글은 빼기
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
               reply_markup={"inline_keyboard": [[{"text": "🛒 쿠팡 바로가기", "url": CP_FRESH if "프레시" in p["q"] else CP_HOME}]]})
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
    if busy(seen):  # 10분 안에 다른 묶음 글이 나갔거나 최근 1시간 글이 많음 -> 다음 실행(14분 뒤)에 다시(API도 안 부름)
        print("toss_special" if special else "toss_beauty" if beauty else "toss_cat" if cat else "toss_best" if best else "toss_deals", "미룸(묶음 글 간격·1시간 글 수)")
        return
    head = "🔥 <b>토스 특가 중 살 만한 {}개</b>" if special else "🏆 <b>토스에서 지금 많이 팔리는 것 중 살 만한 {}개</b>" if best else \
        "⏰ <b>오늘의 토스 하루특가 TOP{}</b>\n<i>밤 12시까지 선착순 · 일부 고객에게만 보이고 수량 제한이 있을 수 있어요</i>"  # 10/10 진우 화면: 선착순특가 유의사항
    if cat:  # 카테고리 ID는 트리에서 이름으로 찾음(트리 조회는 일 상한 차감 없음)
        tree = toss("/categories")["categories"]
        cats = [c for c in tree if (re.search("뷰티|화장품", c["displayName"]) if beauty else c["displayName"] in TOSS_CATS)]  # 뷰티는 이름이 '뷰티'·'화장품/미용' 등이어도 찾게
        if not cats:
            raise RuntimeError(f"토스 카테고리 이름 확인: {[c['displayName'] for c in tree]}")
        others = [c for c in tree if c["displayName"] not in TOSS_CATS]  # 10/8 진우 '더 넓게': 다른 최상위 카테고리를 날마다 1개씩 돌아가며
        cats += [others[kst.tm_yday % len(others)]] if others and not beauty else []
        ids = [c["categoryId"] for c in cats]
        head = ("💄" if beauty else "🧺") + " <b>토스 " + "·".join(c["displayName"] for c in cats) + " 베스트 중 살 만한 {}개</b>"
        raw = [x for i in ids for x in toss(f"/products/best-categories/{i}?size=30")["items"]]
    elif special:  # API엔 '특가' 탭·개당 수익·30일 최저가가 없음(10/11 문서 확인) -> 1일 목록(하루특가·베스트·카테고리 베스트) 중 할인 SPECIAL_DR%↑·리뷰 SPECIAL_RC개↑,
        cand = [x for x in toss_pool(seen) if len(x) > 6 and (x[4] or 0) >= SPECIAL_DR and (x[6] or 0) >= SPECIAL_RC and f"tb_{x[0]}" not in seen]  # 할인율 높은 순 30개를 상세로 지금 가격·품절 다시 확인
        ids = [x[0] for x in sorted(cand, key=lambda x: -x[4])[:30]]
        raw = [x for x in (toss("/products/detail?tacaItemIds=" + ",".join(map(str, ids)))["items"] if ids else [])
               if (x.get("discountRate") or 0) >= SPECIAL_DR and (x.get("reviewCount") or 0) >= SPECIAL_RC]  # 지금 값으로 다시 거름(1일 된 목록의 끝난 하루특가 할인 X)
    else:
        raw = toss(f"/products/{'best-selling' if best else 'today-deals'}?size=30")["items"]
    booked = {re.sub(r"\W", "", e["name"]) for e in load(EVENTS, []) if e.get("name") and e["at"][:10] == time.strftime("%Y-%m-%d", kst)}  # 진우 링크로 오늘 예약한 토스 상품은 자동 글에서 뺌(같은 상품 두 번 방지, 10/11)
    picked = {v.get("id") for k, v in seen.items() if k.startswith("pk_" + time.strftime("%Y-%m-%d", kst)) and isinstance(v, dict)}  # 오늘 이름 예약(toss_picks)으로 찾은 상품도(이름이 달라도 id로)
    items = list({x["tacaItemId"]: x for x in raw if not x.get("isSoldOut") and f"tb_{x['tacaItemId']}" not in seen
                  and re.sub(r"\W", "", x["displayName"]) not in booked and x["tacaItemId"] not in picked}.values())  # 카테고리 겹친 상품은 1번만
    picks = items and ai_pick(SPECIAL_PROMPT if special else BEST_PROMPT if best else GOLD_PROMPT.replace("쿠팡 골드박스", "토스쇼핑 하루특가") + TOSS_EASE,
                              [f"{x['displayName']} | {x['displayPrice']:,}원 ({x.get('discountRate', 0)}% 할인)"
                               + (f" | 리뷰 {x.get('reviewScore')}점 {x['reviewCount']:,}개" if x.get("reviewCount") else "") for x in items])[:5 if special or not best else 3]
    if special and picks:  # 진우 '개당 수익 × Claude 점수': 수수료가 일괄 8%(10/1~, 쉐어링크 공지)라 개당 수익 = 가격 × 8% -> 7점↑ 중 점수 × 가격 높은 순 3개
        picks = sorted((p for p in picks if p["score"] >= 7), key=lambda p: -p["score"] * items[p["i"]]["displayPrice"])[:3]
    rows, plain, got = [], [], []
    today = time.strftime("%Y-%m-%d", kst)
    night = {v[0] for v in (toss_daymap(seen, time.time(), today, seen.get("soldmap", {}).get("d") != today) or {}).get("m", {}).values()} if special and picks else set()  # 특가 중 오늘 하루특가 = 품절 땐 '밤 12시 재오픈'(오늘 목록이 없으면 1번 받음)
    for p in picks or []:
        x = items[p["i"]]
        try:
            link = toss("/links", {"tacaItemId": x["tacaItemId"], "publisherId": E["TOSS_PUBLISHER_ID"]})["shortUrl"]
        except Exception as e:  # 발급 제한 상품은 빼고 나머지만
            print("toss link", repr(e))
            continue
        seen[f"tb_{x['tacaItemId']}"] = {"t": time.time(), "n": x["displayName"]}  # 올린 상품은 3일(seen 보관 기간) 안엔 베스트에 다시 안 올림 (베스트는 며칠씩 그대로, 하루특가와도 겹침). 이름 = 커뮤니티 딜 판단 때 '이미 올린 딜'로
        got.append(x)
        plain.append(f"{NUM[len(plain)]} {clip(x['displayName'], 24)} — {x['displayPrice']:,}원" + (" (하루특가·밤 12시까지)" if x["tacaItemId"] in night else "") + f"\n{link}")
        rows.append((x["displayName"], link, (["⏰ 토스 하루특가 · 밤 12시까지"] if x["tacaItemId"] in night else []) + [f"💰 <b>{x['displayPrice']:,}원</b>" + (f" ({x['discountRate']}%↓)" if x.get("discountRate") else "")
                                             + (f" · ⭐ {x['reviewScore']} (리뷰 {x['reviewCount']:,})" if x.get("reviewCount") else ""), "👉 " + esc(p["comment"])]))
    print("toss_special" if special else "toss_beauty" if beauty else "toss_cat" if cat else "toss_best" if best else "toss_deals", len(items), "items", len(picks or []), "picks", len(rows), "links")  # 0건이어도 로그로 확인
    if raw or special:  # 목록을 받았으면(Claude까지 돌렸으면, 특가는 후보 0개여도) 이번 회차는 끝(발급이 다 막혀도 15분마다 다시 고르지 않게). Threads가 실패해도 채널에 두 번 안 올라가게 먼저 표시
        seen[key] = time.time()
    if rows:
        text, kb = top_post(head.format(len(rows)), rows)
        m = tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True},
               text=f"<i>{TOSS_NOTE}</i>\n\n{text}", reply_markup={"inline_keyboard": kb})
        if m:
            bundled(seen)
        if m:  # 품절 지켜보기(toss_soldout): 글을 다시 그릴 재료 + 상품별 [id, 이름, 올린 가격, 하루특가?, 상태, 마지막 확인]
            seen[f"sold_{m['message_id']}"] = {"t": time.time(), "d": time.strftime("%Y-%m-%d", kst), "k": "top", "pre": f"<i>{TOSS_NOTE}</i>\n\n",
                                               "head": head.format(len(rows)), "rows": rows, "it": [[x["tacaItemId"], x["displayName"], x["displayPrice"], int(not best or x["tacaItemId"] in night), 0, 0] for x in got]}
    tok = E.get("THREADS_TOKEN")
    if rows and tok:  # Threads 글자 수 500 -> 넘치면 뒤 상품부터 뺌. 대가성 문구는 토스 가이드대로 맨 앞(더보기 없이 보이게)
        while len(plain) > 1 and len(TOSS_NOTE) + len(head) + len("\n\n".join(plain)) > 480:
            plain.pop()
        text = f"{TOSS_NOTE}\n\n{re.sub('<.*?>', '', head).format(len(plain))}\n\n" + "\n\n".join(plain)
        me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
        q = urllib.parse.urlencode({"media_type": "TEXT", "text": text[:500], "topic_tag": "핫딜", "access_token": tok})
        cid = json.loads(http(f"{THREADS}/{me}/threads?{q}", method="POST"))["id"]
        time.sleep(10)
        json.loads(http(f"{THREADS}/{me}/threads_publish?creation_id={cid}&access_token={tok}", method="POST"))


def top_post(head, items):
    """번호 목록 글 모양(10/9 진우 '시안성 좋고 사고 싶게'): 번호·굵은 이름(링크) + 줄들(💰가격·👉이유 등, HTML 이스케이프된 것) + 번호 버튼.
    items = [(이름, 링크, [줄])] -> (본문, 버튼 줄들). 토스 하루특가·베스트·카테고리와 TOP5 묶음이 같이 씀."""
    text = head + "\n\n" + "\n\n".join(f"{NUM[n]} <a href=\"{esc(link)}\"><b>{esc(name)}</b></a>" + "".join("\n" + l for l in lines if l)
                                        for n, (name, link, lines) in enumerate(items))
    return text, [[{"text": f"{NUM[n]} {clip(name, 20)}", "url": link}] for n, (name, link, _) in enumerate(items)]


def top_deals(seen):
    """12·18시: 그 시간대(0~12시·12~18시)에 채널에 올린 커뮤니티 딜 중 반응(분당 조회수 + 추천×5, 게시 때 뽐뿌·클리앙 수치) 높은 TOP5를 한 글로.
    3개 미만이면 안 올림. 조회수 기준이라 '많이 보는' 딜(구매 수는 모름). 링크마다 그 제휴 프로그램 대가성 문구를 맨 앞에."""
    kst = time.gmtime(time.time() + 9 * 3600)
    hrs = [h for h in TOP_HOURS if h <= kst.tm_hour]
    key = time.strftime("top_%Y%m%d_", kst) + (str(hrs[-1]) if hrs else "")
    if not hrs or key in seen or busy(seen, cap=False):  # 10분 안에 다른 묶음 글 -> 다음 실행에
        return
    seen[key] = time.time()
    day = time.strftime("%Y-%m-%d ", kst)  # 회차가 늦게 돌아도(실행 누락) 그 시간대 글만 -> 다음 회차와 안 겹침
    since, until = day + f"{([0] + list(TOP_HOURS))[TOP_HOURS.index(hrs[-1])]:02d}:00", day + f"{hrs[-1]:02d}:00"
    top = sorted((p for p in load(POSTS, []) if since <= p["t"] < until and p.get("mid") and p.get("pop")), key=lambda p: -p["pop"])[:5]
    if len(top) < 3:
        return
    items = []
    for p in top:
        price, why = parse(title_of(p["text"]))[2].split("/")[0].strip(), comment_of(p["text"]).split("\n")[0]  # 첫 줄만(💡 단위가격 줄은 💰 줄에 이미)
        items.append((parse(title_of(p["text"]))[1], p["url"], [
            ("💰 <b>" + esc(price) + "</b>" if price else "") + (" · " + esc(p["unit"]) if p.get("unit") else ""),
            "👀 " + esc(p.get("hot") or react(p)), "👉 " + esc(clip(why, 60)) if why else ""]))
    notes = "\n".join(f"<i>{n}</i>" for n in dict.fromkeys(aff_note(p["url"]) for p in top) if n)
    text, kb = top_post(f"🏆 <b>지금 반응 좋은 딜 TOP{len(items)}</b> ({hrs[-1]}시)\n뽐뿌·클리앙 조회수·추천 기준, 채널에 올린 딜 중에서", items)
    if tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True},
          text=(notes + "\n\n" if notes else "") + text, reply_markup={"inline_keyboard": kb}):
        bundled(seen)


def busy(seen, cap=True):
    """묶음 글(토스 회차·TOP5·모아보기)을 지금 올리면 몰리는지(10/11 진우 '너무 자주 올리면 역효과'): 10분(BUNDLE_GAP) 안에 다른 묶음 글이 나갔거나,
    cap이면 최근 1시간 채널 글(posts.json 딜 + 묶음 글)이 HOUR_CAP 이상. 미루면 다음 실행에 다시 봄."""
    now = time.time()
    ts = [t for t in seen.get("bundles", {}).get("ts", []) if now - 3600 < t <= now]  # 최근 1시간(시계가 뒤로 간 기록은 무시)
    if ts and now - max(ts) < BUNDLE_GAP:
        return True
    since = time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 9 * 3600 - 3600))
    return cap and sum(p["t"] >= since for p in load(POSTS, [])) + len(ts) >= HOUR_CAP


def bundled(seen):
    """묶음 글을 올린 시각 기록(최근 1시간만) -> busy()가 간격·시간당 수를 셈."""
    now = time.time()
    seen["bundles"] = {"t": now, "ts": [t for t in seen.get("bundles", {}).get("ts", []) if now - 3600 < t <= now] + [now]}


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
    목록은 seen에 저장해 재사용(문서 권장, 일 상한 10,000개): 카테고리·하루특가 = 하루 1번(9시 갱신), 베스트 = 1시간 1번(못 찾은 딜이 남아 있을 때만)."""
    since = time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - 3 * 86400))
    todo = [p for p in load(POSTS, []) if HAS_TOSS and p["t"] >= since and not toss_share(p.get("url")) and p.get("mid")
            and store_info(title_of(p["text"]), p.get("url")).startswith("💰 토스") and not seen.get("tr_" + str(p["mid"]), {}).get("done")]
    if not todo:
        return
    now = time.time()
    items = toss_pool(seen)
    items = [["ev:" + e["url"], e["name"], int(re.sub(r"\D", "", e.get("button", "")) or 0), now] for e in load(EVENTS, [])
             if e.get("name") and toss_share(e.get("url")) and e["at"] >= since] + items  # 진우가 준 토스 링크(예약 글)도 후보 — 같은 상품이면 그 링크 그대로(10/11 뽐뿌 민물장어)
    toks = lambda s: {t for t in re.findall(r"[0-9a-z.]+[가-힣a-z]*|[가-힣]+", s.lower()) if len(t) > 1}
    ns = lambda s: re.sub(r"\s+", "", s.lower())
    for p in todo:
        key, title = "tr_" + str(p["mid"]), title_of(p["text"]).lstrip("🔥 ")
        first = key not in seen
        r = seen.setdefault(key, {"t": now, "ids": []})
        notice = {"chat": {"id": ADMIN}, "message_id": p.get("cp"), "text": p["text"], "entities": p.get("entities", [])}
        src, u = p.get("url") or "", None
        if not r.get("src"):  # 1번만: 루리웹·클리앙 글은 상품 주소 다시 읽기, 토스 주소(앱 공유 service.toss.im 등)는 상품 주소로 풀기
            r["src"] = 1
            u = store_link(src) if re.search(r"//[\w.]*(ruliweb\.com|clien\.net)/", src) else plain(src) if "toss" in urllib.parse.urlsplit(src).netloc else None
        link = affiliate(u)[0] if (u or "").startswith("https://toss.shopping/t/") else None
        if toss_share(link):
            r["done"] = True
            relink_channel(notice, p["mid"], link)
            print("toss match", p["t"][5:], title[:40], "-> 글의 상품 주소", u, "| 링크 교체")
            continue
        name = parse(title)[1]
        near = lambda x: sum(t in ns(x[1]) for t in toks(name)) + sum(t in ns(name) for t in toks(x[1]))  # 띄어쓰기 달라도(극조생감귤 = 극조생 감귤) 겹친 낱말 수
        cand = sorted((x for x in items if x[0] not in r["ids"] and near(x) >= 3), key=lambda x: -near(x))[:8]
        if not cand and not first:  # 새 후보 없음 -> 조용히 다음 실행에
            continue
        r["ids"] += [x[0] for x in cand]
        pick = cand and ai_pick(MATCH_PROMPT.format(title), [f"{x[1]} | {x[2]:,}원" for x in cand])
        hit = cand[pick[0]["i"]] if pick and pick[0]["score"] >= 8 else None
        link = hit[0][3:] if hit and str(hit[0]).startswith("ev:") else None  # 진우 링크 = 발급 없이 그대로
        if hit:
            r["done"] = True
        if hit and not link:
            seen[f"tb_{hit[0]}"] = {"t": now, "n": hit[1]}  # 채널에 이미 나간 상품 -> 3일 동안 토스 베스트·하루특가에 다시 안 올림(10/10 삼겹살 01:31 딜 → 12:09 베스트)
            try:
                link = toss("/links", {"tacaItemId": hit[0], "publisherId": E["TOSS_PUBLISHER_ID"]})["shortUrl"]
            except Exception as e:  # 발급 제한 상품 -> 사본 답장으로
                print("toss link", repr(e))
        if link:
            relink_channel(notice, p["mid"], link)
        res = f"{hit[1][:40]} {hit[2]:,}원 (id {hit[0]}, {pick[0]['score']}점) | " + ("링크 교체" if link else "발급 실패") if hit else "없음"
        print("toss match", p["t"][5:], title[:40], "->", res, f"| {'' if first else '다시 · '}후보 {len(cand)}/{len(items)}")


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
            cand = sorted({x[0]: x for x in items if x[0] not in r["ids"] and near(x) >= 3}.values(), key=lambda x: -near(x))[:8]
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
                    link = toss("/links", {"tacaItemId": hit[0], "publisherId": E["TOSS_PUBLISHER_ID"]})["shortUrl"]
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
        line = f"💰 <b>{price:,}원</b>" + (f" ({x['discountRate']}%↓)" if x.get("discountRate") else "") + (f" · ⭐ {x['reviewScore']} (리뷰 {x['reviewCount']:,})" if x.get("reviewCount") else "")
        try:
            p = (ai_pick(PICK_PROMPT, [f"{r['n']} | {price:,}원 ({x.get('discountRate', 0)}% 할인)" + (f" | 리뷰 {x.get('reviewScore')}점 {x['reviewCount']:,}개" if x.get("reviewCount") else "")]) or [None])[0]
        except Exception as ex:  # 코멘트 없이도 올림(사람이 고른 상품)
            print("toss pick comment", repr(ex))
            p = None
        body = f"🔥 <b>[토스] {esc(r['n'])}</b>\n\n" + ("토스 하루특가 · 밤 12시까지\n" if night else "") + line + (f"\n👉 {esc(p['comment'])}" if p else "")
        btn = f"🛒 {price:,}원 구매하기"
        r["st"] = "done"  # 먼저 표시: 채널·Threads 실패해도 같은 글 반복 안 함
        m = tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True},
               text=ad_head(TOSS_NOTE, plain_of(body)) + body, reply_markup={"inline_keyboard": [[{"text": btn, "url": r["link"]}]]})
        if not m:
            r["st"] = None  # 채널 실패 -> 다음 실행에 다시
            continue
        seen[f"tb_{r['id']}"] = {"t": now, "n": r["n"]}  # 3일 동안 토스 자동 회차에 다시 안 올림
        bundled(seen)  # 토스 자동 회차가 이 글과 10분 띄우고 1시간 글 수에도 셈
        seen[f"sold_{m['message_id']}"] = {"t": now, "d": today, "k": "ev", "pre": ad_head(TOSS_NOTE, plain_of(body)), "body": body, "btn": btn, "url": r["link"],
                                           "n": r["n"], "p": price, "it": [[r["id"], r["n"], price, night, 0, 0]]}  # 품절 지켜보기(진우 예약 글과 같은 모양)
        print("toss pick", e["at"], clip(r["n"], 30), f"{price:,}원 게시")
        if tok:  # Threads: 대가성 문구 맨 앞, 실패는 main()이 알림
            text = ad_head(TOSS_NOTE, plain_of(body), html_=False) + f"🔥 {clip(r['n'], 60)}\n" + html.unescape(re.sub(r"<[^>]+>", "", line)) + (f"\n👉 {clip(p['comment'], 120)}" if p else "") \
                + f"\n\n🛒 {r['link']}\n📲 실시간 알림 t.me/hotdeal_pick"
            me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
            th_text(tok, me, text, r["link"])


SOLD = ([None, ("⛔ <b>품절</b> — 다시 들어오면 답글로 알려드릴게요", "품절"), ("⛔ <b>품절</b>", "품절")],  # [하루특가 아님 / 하루특가][상태 1 = 품절, 2 = 끝]: (글 줄, 버튼 글자)
        [None, ("⛔ <b>품절</b> — 밤 12시부터 다시 살 수 있어요", "품절 · 밤 12시 재오픈"), ("⛔ <b>특가 끝</b> — 이 가격으로는 다시 안 열렸어요", "특가 끝")])  # 토스 화면 '품절 · 밤 12시부터 구매할 수 있어요'(10/11 진한다시)
SOLD_EDITS = 8  # 한 실행에 고치는 채널 글 수(텔레그램 채널 분당 약 20개 — 밤 12시에 한꺼번에 열려도 나머지는 다음 실행에)


def ev_head(ev):
    """예약 글 머리: 상품 딜(deal)이고 제휴 링크면 [광고] 첫 줄 + 고지문, 행사 알림 등은 고지문만(예전 그대로)."""
    note = aff_note(ev["url"])
    return ad_head(note, plain_of(ev["text"])) if ev.get("deal") else (f"<i>{note}</i>\n\n" if note else "")


def sold_ev(ev, day):
    """진우 예약 글(토스 쉐어링크 + 상품명) -> 품절 지켜보기 항목. 가격 = 버튼 'N원', 없으면 본문 첫 'N원'(그래도 없으면 id 찾을 때 API 가격)."""
    note, won = aff_note(ev["url"]), re.search(r"([\d,]+)원", ev.get("button", "")) or re.search(r"([\d,]+)원", ev.get("text", ""))
    return {"t": time.time(), "d": day, "k": "ev", "pre": ev_head(ev), "body": ev["text"], "btn": ev.get("button", "🛒 구매하기"),
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
    return w["pre"] + text, kb


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
            ok = tg("editMessageText", chat_id=CHANNEL, message_id=int(k[5:]), text=text, parse_mode="HTML", link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": kb})
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
                cmp = next((l for l in body.split("\n") if l[:1] in ("💡", "🤔")), "")
                if re.search(r"오늘|어제|내일|오전|오후|아침|저녁|\d{1,2}시|\d{1,2}:\d{2}", cmp):  # '오늘 18시엔'처럼 날·시각이 든 줄은 다음 날 글에선 틀림 -> 빼고, 약한 딜이면 표시만
                    cmp = cmp.split(" — ")[0] if cmp.startswith("🤔") else ""
                ent = {"id": new[i][0], "n": new[i][1], "url": url, "p0": new[i][2], "icon": "🛒" if body.startswith("🛒") else "🔥", "cmp": clip(cmp, 120), "k": w["k"], "day": today, "st": 0}
                rq = seen.setdefault("reopen", {"t": now, "q": [], "ts": []})
                rq["t"] = now
                if same:  # 같은 상품이 봇 묶음 글에도 있었으면 진우 예약 글 것으로(진우 링크·비교 줄 — 진우 링크 안 뺌), 올렸는지는 그대로
                    same.update({x: v for x, v in ent.items() if x not in ("day", "st")})
                else:
                    rq["q"].append(ent)
            try:
                tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True}, reply_parameters={"message_id": int(k[5:])},
                   text=(f"<i>{note}</i>\n\n" if note else "") + f"🔔 <b>다시 열렸어요!</b> {esc(new[i][1])} — {price:,}원", reply_markup={"inline_keyboard": [[{"text": f"🛒 {price:,}원 구매하기", "url": url}]]})
            except Exception as e:
                print("toss soldout reply", k, repr(e))
        if k in fin or (w["d"] != today and not any(x[4] == 1 for x in w["it"])):
            del seen[k]
    if ids or fin:
        evw = [w for k, w in seen.items() if k.startswith("sold_") and w["k"] == "ev" and w["d"] == today]
        print("toss soldout", len(ids), "checked", len(nf), "notfound", n_out, "out", n_back, "reopen", edits, "edits", f"| 진우 예약 id {sum(bool(w['it']) for w in evw)}/{len(evw)}")


def toss_reopen(seen):
    """품절됐던 토스 딜이 밤 12시 지나 다시 열리면(toss_soldout이 채널 답글과 함께 줄 세움) Threads에도 새 글 — 10/11 진우 '품절 풀리면 다시 쓰레드에 시간 맞춰서, 자정 + 아침 8시 둘 다'.
    0~8시 = '🔔 다시 열렸어요', 8~11시(TH_REOPEN_AM) = 같은 상품을 다시 확인해 아직 살 수 있으면 '☀️ 아침 재알림'(문구를 다르게 — 같은 글 반복은 Threads 스팸 표시 위험), 품절·조회 안 됨이면 안 올림.
    올리기 직전 상품 상세 API로 다시 확인: 가격 = 지금 가격(올린 가격보다 비싸면 특가 끝 -> 안 올림), '토스 하루특가·선착순'은 오늘 하루특가 목록에 있을 때만, 쿠팡 비교 줄은 가격이 그대로일 때만.
    몰림 방지: 재게시끼리 10분(TH_REOPEN_GAP, 실행당 1개) + 1시간 최대 TH_REOPEN_HOUR개 + 토스 묶음 글(채널·Threads)과 10분 -> 넘친 건 다음 실행에.
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
    tok = E.get("THREADS_TOKEN")
    if not todo or not tok or not HAS_TOSS or (r["ts"] and now - max(r["ts"]) < TH_REOPEN_GAP) or len(r["ts"]) >= TH_REOPEN_HOUR or busy(seen, cap=False):
        return
    try:
        d = toss("/products/detail?tacaItemIds=" + ",".join(dict.fromkeys(str(e["id"]) for e in todo[:30])))
    except Exception as e:  # 터널 끊김 등 -> 다음 실행에(Threads 실패 알림 아님)
        print("toss reopen detail", repr(e))
        return
    data, post = {x["tacaItemId"]: x for x in d["items"]}, None
    for e in todo[:30]:
        x = data.get(e["id"])
        if not x or x.get("isSoldOut") or (e["p0"] and x["displayPrice"] > e["p0"]):  # 다시 품절·조회 안 됨·비싸짐(특가 끝) -> 밤 글은 건너뛰고 아침에 다시 봄, 아침이면 안 올림
            e["st"] = 1
            if am:
                r["q"].remove(e)
            continue
        if not post:
            post = (e, x["displayPrice"])
    if not post:
        return
    e, price = post
    ids = lambda: {v[0] for v in seen["soldmap"]["m"].values()} if seen.get("soldmap", {}).get("d") == today else set()
    toss_daymap(seen, now, today, e["id"] not in ids())  # 오늘 목록이 없거나 그 상품이 없으면 받음(하루 3번·2시간 간격 규칙 그대로)
    hot = e["id"] in ids()  # 오늘 하루특가 목록에 있을 때만 '토스 하루특가·선착순'
    head = "☀️ 아침 재알림 — 밤사이 다시 열렸고 아직 살 수 있어요" if am else "🔔 다시 열렸어요" + (" · 선착순" if hot else "")
    text = (ad_head(TOSS_NOTE, f"🔥 [토스] {e['n']} ({price:,}원)\n" + (e["cmp"] if e["cmp"] and price == e["p0"] else ""), html_=False) + f"{head}\n{e['icon']} {clip(e['n'], 60)}\n💰 {'지금 ' if am else ''}{price:,}원" + (" · 토스 하루특가(밤 12시까지)" if hot else "")
            + (f"\n{e['cmp']}" if e["cmp"] and price == e["p0"] else "") + f"\n\n👉 {e['url']}\n📲 실시간 알림 t.me/hotdeal_pick")
    e["st"] = 1  # 먼저 표시: 실패해도 같은 글 반복 시도 안 함(스팸 방지), 실패는 main()이 알림
    if am:
        r["q"].remove(e)
    r["t"] = now
    r["ts"].append(now)
    print("toss reopen", "아침" if am else "밤", clip(e["n"], 30), f"{price:,}원", "하루특가" if hot else "목록 없음", f"| 남은 {len(r['q'])}")
    me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
    th_text(tok, me, text, e["url"])


def th_text(tok, me, text, link):
    """Threads 글 1개(TEXT + 링크 미리보기). 미리보기를 못 만들면(4279047 'Invalid Link Attachment', 10/7 15:51) 첨부 없이 1번 더 — 본문 주소는 그대로."""
    for att in ({"link_attachment": link}, {}):
        q = urllib.parse.urlencode({"media_type": "TEXT", "text": text, **att, "topic_tag": "핫딜", "access_token": tok})
        cid = json.loads(http(f"{THREADS}/{me}/threads?{q}", method="POST"))["id"]
        time.sleep(10)
        try:
            return json.loads(http(f"{THREADS}/{me}/threads_publish?creation_id={cid}&access_token={tok}", method="POST"))
        except urllib.error.HTTPError as e:
            if not att or "4279047" not in (getattr(e, "body", "") or ""):
                raise


def digest(seen, posts):
    """매일 21시(KST) 이후 1회: 오늘 게시한 딜 모아보기 -> 채널에 바로(10/10~, 실패하면 ✅ 초안). 바로 뒤 블로그용 글(길면 나눠서, 실패하면 다음 실행에 다시)·카드·릴스."""
    kst = time.gmtime(time.time() + 9 * 3600)
    key, today = time.strftime("digest_%Y%m%d", kst), time.strftime("%Y-%m-%d", kst)
    todays = [p for p in posts if p["t"].startswith(today) and not p["text"].startswith("📋")]
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
    urls = [f"{SITE}p/{posts.index(p)}.html" if aff_note(p["url"] or "") == OY_NOTE or len(p["url"] or "") > 150 else p["url"] for p in todays]  # 올영: 링크만 나열 금지(FAQ) -> 사이트 · 아주 긴 주소(G마켓 검색 링크 ~400자)도 사이트 딜 페이지로(같은 구매 버튼, 텔레그램 링크 길이 한도)
    rows = [f"{n}. <a href=\"{esc(u)}\">{esc(title_of(p['text']))}</a>" for n, (p, u) in enumerate(zip(todays, urls), 1)]
    notes = "\n".join(f"<i>{n}</i>" for n in dict.fromkeys(aff_note(u or "") for u in urls) if n)  # 제휴 링크 프로그램마다 1줄 맨 위(TOP 글과 같은 방식)
    tail = f"\n\n🔎 지난 딜 전체 보기: {SITE}\n📝 블로그: {BLOG}\n📲 실시간 알림: https://t.me/hotdeal_pick"
    night = night_deals(seen, today + f" {PREVIEW_HOUR:02d}:00", night_window(time.time())[1])  # 밤 10시 미리보기가 안 나갈 만큼 적은 날(PREVIEW_MIN개 미만) = 여기에 합침
    if 0 < len(night) < PREVIEW_MIN:
        tail = "\n\n🌙 <b>오늘 밤 예약 특가</b>\n" + "\n".join(night_line(d) for d in night) + tail
    while True:  # 텔레그램 4096자(링크 주소 빼고 보이는 글자)·서식 100개(링크·굵게·기울임 + 글 속 주소 — 10/11 21시 딜 100개 넘어 ENTITIES_TOO_LONG) — 딜이 아주 많은 날은 뒤쪽을 '외 N개'로 줄임
        more = f"\n… 외 {len(todays) - len(rows)}개는 사이트에서" if len(rows) < len(todays) else ""
        text = (notes + "\n\n" if notes else "") + f"📋 <b>오늘의 딜 모아보기 ({kst.tm_mon}/{kst.tm_mday})</b>\n\n" + "\n".join(rows) + more + tail
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
            cards.make([{"title": title_of(p["text"]), "unit": p.get("unit")} for _, p in order], f"{kst.tm_mon}월 {kst.tm_mday}일", f"docs/cards/{today}.png")
            if IG_CAROUSEL and E.get("IG_TOKEN"):
                deal_slides(today, [p for _, p in order[:CARD_N]])  # 인스타 넘기기용 딜 카드(재료 채운 글은 아래 릴스도 같이 씀)
        except Exception as e:
            print("card", repr(e))
        try:  # 인스타 릴스용 15초 영상 -> 관리자에게 바로 전송 (저장소엔 안 올림). 점수 높은 순 TOP3
            top = [p for _, p in card_order(posts, today)][:3]  # 카드와 같은 순서(점수, 같으면 제휴 딜 먼저)
            fill_reel(top)  # ✅로 올린 글·예전 글은 릴스 재료가 없음 -> 여기서 채움(딜 카드 때 채웠으면 그대로)
            music, mus = bgm(kst), load(MUSIC, [])
            song = mus[kst.tm_yday % len(mus)] if music else None  # 캡션에 곡명(인스타에서도 무슨 곡인지 보이게)
            path = cards.reel([{"title": title_of(p["text"]), "comment": comment_of(p["text"]),
                                **{k: p.get(k) for k in ("e", "hook", "pts", "unit", "warn")}} for p in top], f"{kst.tm_mon}월 {kst.tm_mday}일",
                              os.path.join(tempfile.gettempdir(), f"reel_{today}.mp4"), music)
            cap = (ig_notes(top) + "\n\n" + (top[0].get("hook") + " · " if top[0].get("hook") else "") + f"{kst.tm_mon}월 {kst.tm_mday}일 가성비 TOP{len(top)}\n\n"
                   + "\n".join(f"{n}. {title_of(p['text'])}" for n, p in enumerate(top, 1))
                   + (f"\n\n🎵 {song['name']}" + (" (Pixabay)" if song.get("url") else "") if song else "")
                   + f"\n\n🛒 구매: 프로필 링크(hotdealpick.kr) → 맨 위 '{card_name(today)}'에서 1~{len(top)}번"  # 릴스 TOP = 하루 카드 앞 번호
                   + "\n\n" + ig_tags(top))[:1024]
            if E.get("IG_TOKEN") and E.get("IG_USER_ID") and "facebook" in IG:  # 영상 파일 직접 업로드는 페이스북 로그인(페이지 토큰)만 됨 -> 인스타 토큰이면 릴스는 봇 채팅 영상으로 직접
                try:
                    ig_upload(path, cap, seen)
                except Exception as e:
                    print("ig upload", repr(e), getattr(e, "body", ""))
                    tg("sendMessage", chat_id=ADMIN, text=f"⚠️ 인스타 릴스 업로드 실패 — 아래 영상을 직접 올려줘: {e!r} {getattr(e, 'body', '')}"[:400])
            tg_video(path, cap)
        except Exception as e:
            print("reel", repr(e))


def bgm(kst):
    """music.json 중 오늘 차례 1곡 -> 파일 경로. 없거나 못 받으면 None(무음 릴스).
    url = Pixabay 음원(Claude가 고름): 처음 1번만 받아 Actions 캐시 music/에 보관(공개 저장소엔 안 올림) / id = 봇에 보낸 음악(텔레그램 file_id)."""
    mus = load(MUSIC, [])
    if not mus:
        return None
    m = mus[kst.tm_yday % len(mus)]
    try:
        if m.get("url"):
            path = os.path.join("music", hashlib.sha1(m["url"].encode()).hexdigest()[:12] + ".mp3")
            if not os.path.exists(path):
                with urllib.request.urlopen(urllib.request.Request(m["url"], headers={"User-Agent": UA}), timeout=60) as r:
                    data = r.read()
                os.makedirs("music", exist_ok=True)
                open(path, "wb").write(data)
            return path
        f = tg("getFile", file_id=m["id"])
        path = os.path.join(tempfile.gettempdir(), "bgm")
        with urllib.request.urlopen(f"https://api.telegram.org/file/bot{E['TG_TOKEN']}/{f['file_path']}", timeout=60) as r:
            open(path, "wb").write(r.read())
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
    today = kst.tm_yday % len(mus)
    tg("sendMessage", chat_id=ADMIN, text=f"🎵 릴스 배경음악 플레이리스트 ({kst.tm_mon}/{kst.tm_mday} 갱신, {len(mus)}곡)\n\n"
       + "\n".join(f"{i}. {m['name']}" + (" ← 오늘 릴스" if i - 1 == today else "") for i, m in enumerate(mus, 1))
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


def ig_upload(path, caption, seen):
    """릴스 영상 -> 인스타 컨테이너 생성 + 영상 파일 업로드(rupload). 인스타가 처리하는 동안 기다리지 않고 다음 실행의 ig_publish()가 발행."""
    h = {"Authorization": "Bearer " + E["IG_TOKEN"]}
    c = json.loads(http(f"{IG}/{E['IG_USER_ID']}/media", {"media_type": "REELS", "upload_type": "resumable", "caption": caption, "share_to_feed": True}, h, "POST"))
    data = open(path, "rb").read()
    http(c["uri"], data, {"Authorization": "OAuth " + E["IG_TOKEN"], "offset": "0", "file_size": str(len(data))}, "POST")
    seen["igc_" + c["id"]] = time.time()


IG_LIVE = "docs/cards/ig.json"  # 인스타에 올리는(컨테이너 만든)·올라간 카드 {카드 이름: 시각} — 사이트 맨 위 카드 딜이 인스타 게시물과 같은 번호(build_site.card_stems)


def ig_live(stem, now):
    """IG_LIVE에 카드 기록(7일치). 컨테이너 만든 실행에 기록 -> 같은 실행의 사이트 만들기가 맨 위 카드를 바꿈 -> 다음 실행에 인스타 발행(사이트가 먼저).
    커밋된 기록이라 seen 캐시를 잃어도 같은 카드를 다시 안 올림(ig_cards)."""
    led = {k: t for k, t in load(IG_LIVE, {}).items() if t > now - 7 * 86400}
    led[stem] = now
    os.makedirs(os.path.dirname(IG_LIVE), exist_ok=True)
    json.dump(led, open(IG_LIVE, "w"), ensure_ascii=False)


def ig_publish(seen):
    """올려둔 인스타 컨테이너(카드·릴스)가 처리 끝났으면(FINISHED) 발행. 처리 중이면 다음 실행에, 실패(ERROR·EXPIRED)면 알림(main).
    카드는 만든 실행에 사이트 맨 위에 먼저 뜨고(ig_live) IG_SITE_LAG 지난 다음 실행에 발행. 이미 발행됨(PUBLISHED — 기록 전에 실행이 끊김)은 기록만.
    발행 오류(일시 오류·응답 끊김)는 컨테이너를 그대로 둠 -> 다음 실행에 상태 다시(올라갔으면 PUBLISHED, 아니면 다시 발행 — 같은 컨테이너라 두 번 안 올라감, 24시간 지나면 EXPIRED).
    하루 IG_DAY_MAX개까지(넘으면 다음 날 — 컨테이너는 24시간 유효), 스팸 의심(2207051)이면 24시간 인스타 쉼."""
    tok, uid = E.get("IG_TOKEN"), E.get("IG_USER_ID")
    now = time.time()
    if not (tok and uid):
        return
    day = time.strftime("igpub_%Y%m%d", time.gmtime(now + 9 * 3600))
    card = lambda v: v.get("card") if isinstance(v, dict) else None  # 릴스·다시 올리기는 시각(float)만
    errs = []
    for k in [k for k in seen if k.startswith("igc_")]:
        v = seen[k]
        st = json.loads(http(f"{IG}/{k[4:]}?fields=status_code", headers={"Authorization": "Bearer " + tok}))["status_code"]
        if st == "IN_PROGRESS":
            continue
        if st == "PUBLISHED":
            if card(seen.pop(k)):
                ig_live(card(v), now)
            continue
        if st != "FINISHED":
            seen.pop(k)
            errs.append(RuntimeError(f"인스타 처리 실패({st}) — " + (f"{SITE}cards/{card(v)}.jpg 카드를 직접 올려줘" if card(v) else "오늘 카드·영상은 봇 채팅에 온 걸 직접 올려줘")))
            continue
        if card(v) and now - v["t"] < IG_SITE_LAG:  # 사이트 맨 위에 먼저(이번 실행 배포) -> 다음 실행에 발행
            continue
        n = seen.get(day, {}).get("n", 0)
        if n >= IG_DAY_MAX or seen.get("ig_hold", 0) > now:
            print("ig publish 미룸", k, f"오늘 {n}개" + (" · 스팸 의심으로 쉼" if seen.get("ig_hold", 0) > now else ""))
            continue
        try:
            json.loads(http(f"{IG}/{uid}/media_publish", {"creation_id": k[4:]}, {"Authorization": "Bearer " + tok}, "POST"))
        except Exception as e:
            if "2207051" in (getattr(e, "body", "") or ""):  # 스팸 의심: 이 컨테이너는 버리고 24시간 쉼
                seen["ig_hold"] = now + 86400
                seen.pop(k)
                raise
            errs.append(e)  # 컨테이너는 그대로 -> 다음 실행에 상태 다시
            continue
        seen.pop(k)
        seen[day] = {"t": now, "n": n + 1}
        if card(v):
            ig_live(card(v), now)
        label = card(v) or ""
        tg("sendMessage", chat_id=ADMIN, text="📸 인스타 자동 게시 완료" + (f" — {SLOT_NAMES[label[11:]]} 카드" if label[11:] in SLOT_NAMES else " — 오늘 카드" if label else "") + " (instagram.com/hotdealpick.kr)")
    if errs:
        raise errs[0]


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
    title = f"{kst.tm_mon}월 {kst.tm_mday}일 핫딜 모음 | {title_of(todays[0]['text'])}" + (f" 외 {len(todays) - 1}건" if len(todays) > 1 else "")
    items = []
    for n, p in enumerate(todays, 1):
        t = title_of(p["text"])
        why = next((l for l in comment_of(p["text"]).split("\n") if l and not l.startswith("🤔")), "")  # 약한 딜 표시 줄 말고 코멘트(10/11 점검: 5점 진우 딜이 '약한 제품'만 남던 것)
        items.append(f"{n}. {t}\n{why}\n👉 {p['url'] or SITE}")
    notes = "\n".join(n for n in dict.fromkeys(aff_note(p["url"] or "") for p in todays) if n in (OY_NOTE, NAVER_NOTE))  # 본문 맨 위 필수인 프로그램
    return (f"📝 블로그용 (제목·본문 그대로 복붙)\n\n제목: {title}\n\n" + (notes + "\n\n" if notes else "") + "\n\n".join(items)
            + f"\n\n더 많은 핫딜 👉 {SITE}\n실시간 알림 👉 https://t.me/hotdeal_pick\n\n"
            + "이 포스팅은 쿠팡 파트너스·토스쇼핑 쉐어링크 등 제휴 마케팅 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받을 수 있습니다.")


THREADS = "https://graph.threads.com/v1.0"  # 공식 문서 기준 도메인


def ig_tags(ps):
    """인스타 해시태그 IG_TAG_MAX개: 기본 + 그날 딜에 있는 카테고리(사이트 '🧻 생필품'·'💄 화장품'과 같은 낱말) + 채움."""
    titles = " ".join(title_of(p["text"]) for p in ps)
    cat = [IG_CAT_TAGS[k] for k, _, rx in CATS if k in IG_CAT_TAGS and re.search(rx, titles)]
    return " ".join(list(dict.fromkeys(IG_TAGS + tuple(cat) + IG_FILL_TAGS))[:IG_TAG_MAX])


def slot_deals(posts, day, h):
    """시간대 카드 딜 = 그 시간대(앞 시간대 시각 ~ h시)에 올린 딜, 하루 카드와 같은 순서(점수·제휴 먼저) 앞 CARD_N개."""
    since = day + f" {max([0] + [x for x in IG_SLOTS if x < h]):02d}:00"
    return [x for x in day_deals(posts, day) if since <= x[1]["t"] < day + f" {h:02d}:00"][:CARD_N]


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
    rows = [f"{n}. {clip(re.sub(PRICE_TAIL, '', title_of(p['text'])).strip(), 34)}" for n, p in enumerate(ps, 1)]
    slot = SLOT_NAMES.get(stem[11:]) if len(stem) > 10 else None
    return rows, (ig_notes(ps) + "\n\n" + f"{int(stem[5:7])}월 {int(stem[8:10])}일 " + (f"{slot} 핫딜" if slot else "오늘의 핫딜 모음") + "\n\n" + "\n".join(rows)
                  + f"\n\n🛒 구매: 프로필 링크(hotdealpick.kr) → 맨 위 '{card_name(stem)}'에서 번호를 누르면 바로 구매 페이지\n\n" + ig_tags(ps))[:2200]


def fill_reel(ps):
    """릴스·딜 카드 재료(e·hook·pts·unit·warn)가 없는 딜(✅로 올린 글·예전 글)만 Claude로 채움(글 dict에 바로). 실패하면 그대로(제목·코멘트로 그림)."""
    need = [p for p in ps if not (p.get("hook") and p.get("pts"))]
    if not need:
        return
    try:
        for f in ai_pick(REEL_PROMPT, [f"{title_of(p['text'])} | {comment_of(p['text'])}" for p in need]):
            need[f["i"]].update({k: f[k] for k in ("e", "hook", "pts", "unit", "warn") if f.get(k)})
    except Exception as e:
        print("reel fill", repr(e))


def deal_slides(stem, ps):
    """넘기기 딜 카드: 카드 번호 순서대로 딜마다 1장 -> docs/cards/{stem}/01.jpg…(표지 다음 장들, 워크플로가 커밋 -> 사이트 공개 -> ig_cards가 올림).
    올리브영 딜은 이유 제목 '체크 포인트'(큐레이터 정책: 권유 문구 X). 한 장이라도 실패하면 폴더째 지움 -> 한 장짜리 카드로."""
    import cards
    fill_reel(ps)
    d = f"docs/cards/{stem}"
    try:
        os.makedirs(d, exist_ok=True)
        for n, p in enumerate(ps, 1):
            oy = aff_note(p.get("url") or "") == OY_NOTE or is_oy(title_of(p["text"]))
            pts = [x for x in p.get("pts") or [] if not (oy and re.search(OY_DENY, x))]  # 올리브영: 후기·추천·반응·효능 문장은 빼고(큐레이터 정책 — 그림은 못 고침)
            cards.deal_card({"title": title_of(p["text"]), "comment": "" if oy else comment_of(p["text"]), **{k: p.get(k) for k in ("e", "unit", "warn")}, "pts": pts},
                            n, len(ps), f"{d}/{n:02d}.jpg", why="체크 포인트" if oy else "살 만한 이유")
    except Exception as e:
        print("slides", stem, repr(e))
        shutil.rmtree(d, ignore_errors=True)


def ig_carousel(seen, tok, uid, now):
    """넘기기 묶기: 조각(표지·딜 카드) 컨테이너가 다 처리되면(FINISHED) 묶음(CAROUSEL, 캡션) 컨테이너 -> igc_(ig_publish가 발행).
    처리 중이면 다음 실행에, 조각 실패(ERROR·EXPIRED)·KIDS_WAIT 넘게 처리 중이면 그 회차는 버리고 알림(카드 주소). 조각은 igc_에 안 둠(따로 발행되면 안 됨)."""
    h = {"Authorization": "Bearer " + tok}
    for k in [k for k in seen if k.startswith("igk_")]:
        v, stem = seen[k], k[4:]
        sts = [json.loads(http(f"{IG}/{c}?fields=status_code", headers=h))["status_code"] for c in v["kids"]]
        if all(st == "FINISHED" for st in sts):
            c = json.loads(http(f"{IG}/{uid}/media", {"media_type": "CAROUSEL", "children": ",".join(v["kids"]), "caption": card_caption(stem)[1]}, h, "POST"))
            seen.pop(k)
            seen["igc_" + c["id"]] = {"t": now, "card": stem}
            print("ig carousel", stem, len(v["kids"]), "장")
        elif any(st not in ("IN_PROGRESS", "FINISHED") for st in sts) or now - v["t"] > KIDS_WAIT:
            seen.pop(k)
            raise RuntimeError(f"인스타 넘기기 카드 처리 실패({'·'.join(dict.fromkeys(sts))}) — {SITE}cards/{stem}.jpg 카드를 직접 올려줘")


def prune_slides(now):
    """딜 카드 폴더(docs/cards/날짜[_시]/)는 SLIDE_KEEP일 지나면 지움(인스타가 이미 가져감, 사이트는 표지만 씀 — 저장소 크기). git add -A가 지운 것도 커밋."""
    cut = time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600 - SLIDE_KEEP * 86400))
    for f in os.listdir("docs/cards") if os.path.isdir("docs/cards") else []:
        if STEM.fullmatch(f) and f[:10] < cut and os.path.isdir(f"docs/cards/{f}"):
            shutil.rmtree(f"docs/cards/{f}")


def ig_cards(seen):
    """인스타 하루 3번(10/11 진우 '인스타 업그레이드 1번'): 12시·18시(IG_SLOTS) 시간대 카드 + 21시 하루 카드(모아보기 때 만든 것).
    시간대 카드: 그 시각 첫 실행에 카드(JPEG)·번호 순서를 docs/cards/날짜_시에 만들고(워크플로가 커밋 -> 사이트 공개) 다음 실행에 사이트에 뜨면 인스타 컨테이너
    -> 사이트 맨 위 카드 기록(ig_live, 사이트 먼저) -> 다음 실행에 ig_publish가 발행. 그 시각 IG_LATE시간 안에만, 딜 IG_MIN개 미만이면 건너뜀, 회차마다 1번
    (기록에 있으면 seen을 잃어도 다시 안 올림). 컨테이너 만들기 실패는 IG_TRIES번까지 다음 실행에 다시, 마지막엔 카드 주소와 함께 알림(main).
    넘기기(IG_CAROUSEL, 10/11 진우 '인스타 업그레이드 2번'): 카드 만들 때 딜 카드(deal_slides)도 -> 올릴 때 표지·딜 카드 조각 컨테이너 -> ig_carousel이 묶음."""
    tok, uid = E.get("IG_TOKEN"), E.get("IG_USER_ID")
    now = time.time()
    if not (tok and uid) or seen.get("ig_hold", 0) > now:
        return
    prune_slides(now)
    ig_carousel(seen, tok, uid, now)  # 지난 실행에 만든 조각
    kst = time.gmtime(now + 9 * 3600)
    today, led = time.strftime("%Y-%m-%d", kst), load(IG_LIVE, {})
    for h in (*IG_SLOTS, 21):
        stem = today if h == 21 else f"{today}_{h}"
        tried = seen.get("igs_" + stem)
        if not h <= kst.tm_hour < h + IG_LATE or stem in led or (tried and tried.get("fail", IG_TRIES) >= IG_TRIES):  # 끝난 회차(올림·건너뜀)는 fail 없음
            continue
        jpg = f"docs/cards/{stem}.jpg"
        if h != 21 and not os.path.exists(jpg):  # 시간대 카드 만들기(이번 실행) -> 다음 실행에 올림
            posts = load(POSTS, [])
            order = slot_deals(posts, today, h)
            if len(order) < IG_MIN:
                seen["igs_" + stem] = {"t": now, "skip": len(order)}
                print("ig card", stem, f"딜 {len(order)}개 -> 건너뜀")
                continue
            import cards
            os.makedirs("docs/cards", exist_ok=True)
            json.dump([i for i, _ in order], open(f"docs/cards/{stem}.json", "w"))  # 카드 번호 순서 고정(캡션·사이트가 같이 씀)
            cards.make([{"title": title_of(p["text"]), "unit": p.get("unit")} for _, p in order], f"{kst.tm_mon}월 {kst.tm_mday}일", jpg,
                       head=IG_SLOTS[h], label=f"{SLOT_NAMES[str(h)]} 핫딜", png=False)
            if IG_CAROUSEL:
                deal_slides(stem, [p for _, p in order])
            print("ig card", stem, f"만듦 {len(order)}개")
            return
        if not os.path.exists(jpg):  # 21시: 모아보기(digest)가 아직 카드를 안 만듦
            continue
        url, d = f"{SITE}cards/{stem}.jpg", f"docs/cards/{stem}"
        slides = [f"{SITE}cards/{stem}/{f}" for f in sorted(os.listdir(d)) if re.fullmatch(r"\d\d\.jpg", f)] if IG_CAROUSEL and os.path.isdir(d) else []
        try:
            for u in [url] + slides[-1:]:
                http(u, method="HEAD")  # 아직 배포 전(404)이면 다음 실행에 (표지·딜 카드는 같은 커밋)
        except Exception:
            continue
        fail = (tried or {}).get("fail", 0)
        seen["igs_" + stem] = {"t": now}  # 먼저 표시(만들기 성공 = 회차 끝)
        auth = {"Authorization": "Bearer " + tok}
        try:
            if slides:  # 넘기기: 조각(캡션 X) -> 다 처리되면 묶음(ig_carousel)
                seen["igk_" + stem] = {"t": now, "kids": [json.loads(http(f"{IG}/{uid}/media", {"image_url": u, "is_carousel_item": True}, auth, "POST"))["id"] for u in [url] + slides]}
            else:
                c = json.loads(http(f"{IG}/{uid}/media", {"image_url": url, "caption": card_caption(stem)[1]}, auth, "POST"))
        except Exception as e:
            seen["igs_" + stem] = {"t": now, "fail": fail + 1}  # 다음 실행에 다시(IG_TRIES번까지)
            raise RuntimeError(f"인스타 카드 컨테이너 실패({fail + 1}/{IG_TRIES}) — " + ("다음 실행에 다시" if fail + 1 < IG_TRIES else f"{url} 카드를 직접 올려줘") + f": {e!r} {getattr(e, 'body', '') or ''}")
        if not slides:
            seen["igc_" + c["id"]] = {"t": now, "card": stem}
        ig_live(stem, now)
        print("ig card", stem, f"넘기기 조각 {len(slides) + 1}장" if slides else "컨테이너")
    ig_carousel(seen, tok, uid, now)  # 이번에 만든 조각(이미지는 보통 바로 처리 끝)


def ig_repost(seen):
    """ig_repost.txt 날짜 = 오늘이면 그날 카드를 지금 코드로 다시 그려 인스타에만 1번 더 게시(10/8 진우 '다시 업로드'). 지난 날짜면 무시.
    1번째 실행: 새 카드 -> docs/cards/re/(새 주소라 사이트 캐시 영향 없음, 워크플로가 커밋) / 다음 실행: 사이트에 뜨면 컨테이너 -> ig_publish가 발행.
    예전 게시물 삭제는 진우(Instagram 로그인 토큰은 삭제 권한 없음)."""
    kst = time.gmtime(time.time() + 9 * 3600)
    day = open(REPOST).read().strip() if os.path.exists(REPOST) else ""
    if day != time.strftime("%Y-%m-%d", kst) or "igre_" + day in seen or not (E.get("IG_TOKEN") and E.get("IG_USER_ID")):
        return
    path = f"docs/cards/re/{day}.png"
    if not os.path.exists(path):
        import cards
        os.makedirs(os.path.dirname(path), exist_ok=True)
        cards.make([{"title": title_of(p["text"]), "unit": p.get("unit")} for _, p in card_order(load(POSTS, []), day)], f"{kst.tm_mon}월 {kst.tm_mday}일", path)
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
    todo = [p for p in posts if p["t"].startswith(today) and p.get("mid") and p.get("cp") and not aff_note(p.get("url") or "")
            and store_info(title_of(p["text"]), p.get("url")).startswith("💰 쿠팡")][-5:]
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
    while True:  # 대가성 문구는 맨 앞 그대로, 길면 번호 줄을 줄임(Threads 500자)
        text = (cap.split("\n\n")[0] + f"\n\n📋 {kst.tm_mon}/{kst.tm_mday} 오늘의 핫딜 모음\n\n" + "\n".join(rows)
                + f"\n\n전체 딜·구매 링크 👉 {SITE}\n실시간 알림 👉 https://t.me/hotdeal_pick")
        if len(text) <= 480 or len(rows) <= 1:
            break
        rows = rows[:-1]
    text = text[:480]
    me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
    q = urllib.parse.urlencode({"media_type": "IMAGE", "image_url": url, "text": text, "topic_tag": "핫딜", "access_token": tok})
    cid = json.loads(http(f"{THREADS}/{me}/threads?{q}", method="POST"))["id"]
    time.sleep(30)  # 미디어 처리 대기 (공식 권장값)
    json.loads(http(f"{THREADS}/{me}/threads_publish?creation_id={cid}&access_token={tok}", method="POST"))


TH_BOT_MAX = 15  # 봇이 고른 딜의 하루 Threads 최대(10/11 진우 'Threads 엄선' — 10/10 하루 86개라 글당 조회가 얇았음)


def th_pick(p, posts, todo):
    """Threads에 올릴 딜인지: 진우 링크·예약 글(own, 점수 없음)은 전부, 봇 딜은 7점↑ 전부 + 6점은 제휴 링크 딜만 하루 TH_BOT_MAX까지(5점·제휴 없는 6점은 채널에만)."""
    if p.get("own") or "s" not in p or p["s"] >= 7:
        return True
    n = sum(1 for q in posts if q["t"][:10] == p["t"][:10] and "s" in q and not q.get("own") and q.get("th")) + sum("s" in posts[j] and not posts[j].get("own") for j in todo)
    return p["s"] >= 6 and aff(p.get("url")) and n < TH_BOT_MAX


def threads_deals(seen):
    """채널에 올라간 딜을 Threads에도 하나씩 (링크 = 사이트 딜 페이지: 구매 버튼·대가성 문구 있음).
    사이트 반영 전(404)이면 다음 실행에. posts.json에 th 표시 -> 두 번 안 올림. 3시간 지난 딜은 안 올림(식은 딜), 1회 최대 3개(도배 방지)."""
    tok, posts = E.get("THREADS_TOKEN"), load(POSTS, [])
    since = time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - 3 * 3600))
    todo = []
    for i, p in enumerate(posts):
        if len(todo) < 3 and not p.get("th") and p["t"] >= since and not p["text"].startswith("📋") and th_pick(p, posts, todo):
            todo.append(i)
    if not tok or not todo:
        return
    me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
    for i in todo:
        url = f"{SITE}p/{i}.html"
        try:
            http(url, method="HEAD")
        except Exception:
            return
        note = aff_note(posts[i].get("url") or "")
        icon = "🛒" if "특가로는 약한 제품" in posts[i]["text"] else "🔥"  # 채널 글과 같게(약한 딜에 🔥 안 붙임)
        sv = None if note and ad_on() else saving(posts[i]["text"])  # 제휴 링크면 첫 줄 [광고]에 훅(10/11 진우 결정), 아니면 예전처럼 '💸 …보다 N원 싸요'
        head = ad_head(note, posts[i]["text"], posts[i].get("unit") or "", html_=False)
        text = head + (f"💸 {sv[0]}보다 {sv[1]} 싸요\n" if sv else "") \
            + f"{icon} {title_of(posts[i]['text'])}\n\n{comment_of(posts[i]['text'])}"[:250 - max(0, len(head) - len(note) - 2)] \
            + f"\n\n👉 {url}\n🙋 팔로우하면 매일 이런 가격 비교가 피드에 떠요\n📲 실시간 알림 t.me/hotdeal_pick"  # Threads 500자 제한(이모지는 바이트로 셈)
        posts[i]["th"] = 1  # 먼저 표시: 실패해도 같은 딜 반복 시도 안 함(스팸 방지), 실패는 main()이 알림
        json.dump(posts, open(POSTS, "w"), ensure_ascii=False)
        th_text(tok, me, text, url)


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
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return default


def dkey(title):
    """같은 딜 판단 키: [쇼핑몰]·가격 꼬리(괄호·' / 가격') 떼고 글자·숫자만 앞 24자. 너무 짧으면 None(판단 안 함). 24시간 지나면 같은 상품도 새 딜로 봄."""
    k = re.sub(r"[^0-9a-z가-힣]", "", re.split(r"\s/\s", keyword(title))[0].lower())[:24]
    return "k:" + k if len(k) >= 4 else None


def quiet():
    """8~24시(KST)인데 마지막 채널 딜 글이 GAP_FILL분보다 오래됐으면 True -> 6점 딜로 빈틈 메움."""
    now = time.time() + 9 * 3600
    last = max((p["t"] for p in load(POSTS, []) if not p["text"].startswith("📋")), default="")
    return time.gmtime(now).tm_hour >= 8 and last < time.strftime("%Y-%m-%d %H:%M", time.gmtime(now - GAP_FILL * 60))


def main():
    seen = load(SEEN, {})
    publish_approved()
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
    if new:
        since = time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - 86400))
        recent = [title_of(p["text"]) for p in load(POSTS, []) if p["t"] >= since and not p["text"].startswith("📋")][-30:]
        recent += [v["n"] for k, v in seen.items() if k.startswith("tb_") and isinstance(v, dict) and v["t"] > time.time() - 86400]  # 토스 하루특가·베스트 글(posts.json엔 없음)도 — 10/10 케라시스 베스트 10:02 → 같은 딜 10:44
        prompt = DEAL_PROMPT + ("\n최근 24시간에 이미 올린 딜(같은 상품이면 고르지 마):\n" + "\n".join(recent) if recent else "")
        try:
            picks = ai_pick(prompt, [f"[{d['board']}] {d['title']} | {d['hits']} | {d['age']:.0f}분 전 | {d['desc']}" for d in new])
        except Exception as e:  # Claude 오류면 이번엔 딜 판단만 건너뜀(본 글 기록 안 함 -> 다음 실행에 다시). 실행 전체가 죽으면 토스·Threads·리포트도 멈추고 seen 캐시도 안 남음
            print("ai_pick 실패", repr(e))
            new = picks = []
        for d in new:  # AI 판단 성공한 뒤에만 '본 글'로 기록 -> 실패 시 다음 실행에서 재시도
            seen[d["id"]] = time.time()
            if dkey(d["title"]):
                seen[dkey(d["title"])] = time.time()
        if new:
            print("점수", [(p["score"], new[p["i"]]["title"][:30]) for p in picks] or "5점 이상 없음")  # 컷 조절용 근거
        good = [p for p in picks if p["score"] >= MIN_SCORE - earns(new[p["i"]]["title"])]  # 수수료 되는 몰은 1점 낮춰도(10/10 올리브영 -> 같은 날 진우 '수수료 딜 꼭 챙겨': 5점 링크프라이스 딜 3개가 빠지던 것)
        if not good and not held and picks and quiet():
            best = max(picks, key=lambda p: p["score"])
            good = [best] if best["score"] >= FILL_SCORE else []
        good = sorted(({"d": new[p["i"]], "p": {k: v for k, v in p.items() if k != "i"}} for p in good), key=rank)
    for h in (held + good)[:MAX_DRAFTS]:  # 보관해 둔 딜이 먼저
        seen.pop("hold_" + h["d"]["id"], None)
        p = h["p"]
        post_or_draft(h["d"], p["comment"], p["score"], p.get("q"), {k: p.get(k) for k in ("e", "hook", "pts", "unit", "warn")})
    for h in good[max(0, MAX_DRAFTS - len(held)):]:  # 넘친 좋은 딜은 다음 실행에 다시 묻지 않고 올리게 보관
        seen["hold_" + h["d"]["id"]] = {"t": time.time(), **h}
    for step in (events, preview, playlist, goldbox, lambda s: cp_events(s, deals), top_deals, toss_deals, lambda s: toss_deals(s, True), lambda s: toss_deals(s, "cat"), lambda s: toss_deals(s, "beauty"), lambda s: toss_deals(s, "special"), toss_relink, toss_picks, toss_soldout, toss_reopen, lambda s: digest(s, load(POSTS, [])), threads, threads_deals, ig_cards, ig_repost, ig_publish, coupang_remind, oy_claim, report):
        try:
            step(seen)
        except Exception as e:
            print(step.__name__, repr(e))
            ig = step in (ig_cards, ig_publish)
            alert = time.strftime(("ig" if ig else "th") + "_alert_%Y%m%d", time.gmtime(time.time() + 9 * 3600))
            if step in (threads, threads_deals, toss_picks, toss_reopen, preview, ig_cards, ig_publish) and alert not in seen:  # 토큰 만료 등: 하루 1번만 알림
                seen[alert] = time.time()
                tg("sendMessage", chat_id=ADMIN, text=f"⚠️ {'인스타' if ig else 'Threads'} 게시 실패: {e!r}"[:300] + "\n"
                   + ("IG_TOKEN 만료(60일)면 앱 대시보드에서 토큰 다시 생성 → README 세팅 6-2" if ig else threads_hint(e)))
    cutoff = time.time() - 3 * 86400
    json.dump({k: v for k, v in seen.items() if (v["t"] if isinstance(v, dict) else v) > cutoff}, open(SEEN, "w"))  # hold_ = 딜째 보관
    print(f"new={len(new)} seen={len(seen)}")


if __name__ == "__main__":
    main()
