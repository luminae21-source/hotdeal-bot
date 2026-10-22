#!/usr/bin/env python3
"""핫딜봇: 뽐뿌·루리웹·클리앙 핫딜 -> Claude 선별/코멘트 -> 채널 바로 게시.
상품 주소가 있으면(루리웹·클리앙 글) 링크프라이스 승인 몰은 상품 페이지 제휴 링크 자동, 없으면(뽐뿌: GitHub IP 차단) 검색 제휴 링크.
쿠팡·네이버 등 수동 몰은 관리자에게 사본(+쿠팡은 파트너스 검색 버튼, 네이버는 상품명 복사·쇼핑커넥트 버튼, 그 외 상품 열기 버튼) -> 제휴 링크를 답장(또는 그냥 전송)하면 채널 글 교체. 쿠팡 골드박스는 매일 7시 이후 1번 채널에 바로(키 없으면 골드박스 링크, 있으면 TOP5).
GitHub Actions에서 15분마다 실행(tick.yml 타이머가 workflow_dispatch로 실행 + 예약 보조). 외부 패키지 없음(파이썬 표준 라이브러리만)."""
import base64, collections, hashlib, hmac, html, json, math, os, random, re, shutil, tempfile, time, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from build_site import BASE as SITE, BLOG, GOLDBOX, NOTE_STARTS, title_of, split_title, parse, react, TOSS_HOSTS, NAVER_HOSTS, AFF_HOSTS, OY_HOSTS, toss_share, day_deals, card_order, saving, buy_label, aff, MALL_HEAD, mall_title, CATS, CARD_N, SLOT_NAMES, card_name, SAVE_STORES, STEM, unit_of, strip_cmp, OTHER_STORES, CMP_WORDS, shop_of, price_won, FOOD, CHANNEL_WEB, price_records, PRICE_MIN  # 제휴 도메인은 사이트와 같이 씀

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
IG_SLOTS = {12: "점심에 볼 딜", 18: "퇴근길에 볼 딜"}  # 인스타 하루 3번(10/11 진우 '인스타 업그레이드 1번'): 12시 = 0~12시 딜, 18시 = 12~18시 딜 카드 + 21시 하루 카드(모아보기) — 7일 표에서 채널 글이 가장 많은 12·18시(TOP5 회차와 같은 시간대)
IG_LATE, IG_MIN, IG_DAY_MAX = 3, 3, 5  # 시간대 카드는 그 시각 3시간 안에만(늦게 몰아 안 올림) · 딜 3개 미만이면 건너뜀 · 인스타 하루 발행 최대 5개(카드 3 + 릴스 1 + 다시 올리기 1, 오류로 몰려 올라가지 않게 — API 상한 50)
IG_CAROUSEL, SLIDE_KEEP, KIDS_WAIT = True, 2, 3600  # 넘기기(10/11 진우 '인스타 업그레이드 2번'): 표지 + 딜마다 1장(False면 1단계 한 장 카드) · 딜 카드는 인스타가 가져간 뒤 2일 지나면 지움(저장소 크기) · 조각 처리 1시간 넘으면 버림
OY_DENY = r"후기|리뷰|추천|댓글|반응|좋|최고|100%|효과|효능|강추|쟁여|인생|대박|미백|주름|탄력|개선"  # 올리브영 딜 카드에서 빼는 말(큐레이터 정책: 가격·용량·구성·조건만)
REEL_PUBLIC, REEL_HOUR, REEL_THUMB_MS = False, 22, 1500  # 릴스 자동(10/11 진우 '인스타 업그레이드 3번'): 영상을 docs/reels/에 공개 -> 인스타가 video_url로 가져감. 음원(Pixabay) 든 영상 공개는 진우 확인 뒤 True · 22시(21시 카드와 간격) · 표지 = 1.5초(첫 화면 다 뜬 뒤)
IG_TRIES, IG_SITE_LAG = 3, 300  # 카드 컨테이너 만들기 실패(인스타 일시 오류)는 회차 안에서 3번까지 다시(안 올라간 컨테이너는 안 보여서 두 번 안 올라감) · 카드는 사이트 맨 위에 먼저(만든 실행) -> 5분 넘은 다음 실행에 발행
IG_TAGS, IG_CAT_TAGS, IG_FILL_TAGS, IG_TAG_MAX = ("#핫딜", "#특가", "#핫딜픽"), {"life": "#생필품", "beauty": "#화장품"}, ("#살림템", "#쇼핑정보"), 5  # 해시태그 5개(근거 없는 #최저가 뺌, 카테고리 태그는 그날 딜에 있을 때만)
TOP_HOURS = (12, 15, 18)  # 10/12 01:25 진우 '좋은 딜은 묶어서 중간에 리스트도' -> 15시 추가(Threads 시청 피크 목·금 15~18시) · 커뮤니티 반응 좋은 딜 TOP5 묶음 글(10/9 진우 '사람들이 사는 제품을 보기 좋고 사고 싶게') — top_deals()
NUM = "1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣".split()
TOSS_DAY_HOURS = (9, 13, 17)  # 하루특가(= 토스 앱 '매일 밤 12시 선착순특가') 회차, 회차마다 안 올린 것 최대 5개 (10/10 진우가 선착순 상품 링크를 직접 보내다가 '이 작업도 자동으로')
TOSS_BEST_HOURS = (10, 11, 12, 14, 16, 18, 20)  # 10/11 진우 '회차 늘리기, 적절하게': 7일 표에서 묶음 글 없는 11시 추가(12시는 TOP5와 겹침). 줄이려면 여기서 빼기. 토스 '지금 많이 팔리는 상품'(1시간마다 갱신) 중 Claude가 살 만한 것만: 10~20시 2시간마다 (10/7 진우 제안 2번 -> 10/8 3번 -> 10/9 '쿠팡·토스 주력' 6번)
TOSS_BEAUTY_HOURS = (15, 19)  # 토스 뷰티(화장품) 카테고리 베스트 중 살 만한 것 (10/11 진우 '화장품도 올리자' -> '화장품도 발굴': 저녁 1번 더 = 7일 표에서 저녁 중 가장 조용하고 묶음 글 없는 19시)
AD_FIRST = ""  # 10/12 00:40 진우 결정 '첫 줄 변경 취소': 예전 형식(고지문 첫 줄 → 💸 쿠팡보다 N원 싸요 → 🔥 제목 → … — 23:33 에이지랩 크림 글 51분 조회 20)이 더 좋음, 2주 동결.
# 날짜(KST, 예 "2026-10-12")를 넣으면 그날부터 개별 딜 글(채널·Threads) 첫 줄 '[광고] + 훅 + 상품 + 가격'(10/11 결정, 10/12 0:01~0:5x만 나감). "" = 예전(고지문이 첫 줄)


def ad_on():
    return bool(AD_FIRST) and time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600)) >= AD_FIRST
PREVIEW_LINKS = f"\n\n🛍 지금 살 수 있는 딜 한눈에(앱 설치 없이) 👉 {SITE}?ref=th\n📲 텔레그램 쓰는 분은 올라오는 순간 알림 👉 t.me/hotdeal_pick"  # Threads 22시 미리보기 끝 블록(10/13 01:25 진우, 01:40 텔레그램 줄 = 선택사항으로)
TH_REPLY = True  # 10/13 00:50 진우 '타래 + 브랜드 섞기': Threads 22시 미리보기 나머지는 댓글(타래)로 — 토큰이 댓글을 못 달면(th_reply_ok) 자동으로 댓글 없이. False = 댓글 안 씀
PREVIEW_HOUR, PREVIEW_MIN, PREVIEW_TH = 22, 3, 5  # 10/11 진우 '묶음 리스트도, 꾸준함이 중요': 매일 밤 10시 '🌙 오늘 밤 특가 미리보기'(진우 예약 딜 중 지금~다음 날 8시) — 진우 예약은 17~24시에 몰림(10/10 20~22시 34개, 10/11 밤 19개)·토스 하루특가는 밤 12시에 바뀜 · 3개 미만이면 21시 모아보기에 합침 · Threads는 앞 5개(500자)
BUNDLE_GAP, HOUR_CAP = 600, 8  # 10/11 진우 '너무 자주 올리면 역효과': 묶음 글(토스 회차·TOP5·모아보기)은 앞 묶음 글과 10분 이상 띄움 / 토스 회차는 최근 1시간 채널 글이 8개 이상이면 미룸(7일 표: 평소 시간당 최대 6개 -> 진우 예약이 몰린 시간에만 걸림)
TH_REOPEN_NIGHT, TH_REOPEN_MORN, TH_REOPEN_DAY = 2, 2, 4  # 10/12 진우 '6시부터 해도 괜찮아, 한도 관리': 재오픈 Threads 글은 개별 5개와 따로 — 밤(0~6시) 2개 + 아침(6시~) 2개, 하루 4개까지, 일반 딜이 먼저(main 순서)
TH_REOPEN_GAP, TH_REOPEN_HOUR, TH_REOPEN_AM = 600, 3, (6, 11)  # (10/12: 아침 8시 -> 6시) 10/11 진우 '토스 품절 풀리면 다시 쓰레드에, 자정 + 아침 8시': 재게시끼리 10분(= 실행당 1개) · 1시간 최대 3개(7일 표: 0~3시 채널 시간당 1~4.5개, 8시 2개 -> 그 시간 평소 글 수 수준) · 아침 재알림은 8~11시(놓치면 낮에 몰아 안 올림)
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
    return pre + mall_view(text[len(pre):], link or d["url"]), link or d["url"], label  # 토스·쿠팡 = 몰별 틀(10/22 진우 '한눈에')


TOSS_TAG = r"\[토스(?:쇼핑)?\]"  # 토스 딜 제목 [몰] — 10/18 진우 '[토스쇼핑]도 토스'(같은 토스쇼핑: 비교 X·게시 시점 가격·뽐뿌 말고 바로 연결)


def is_toss(url, text=""):
    """토스 딜인지: 쉐어링크(toss.shopping·toss.im) 또는 제목이 [토스]·[토스쇼핑](몰별 틀 = '💙 토스 특가' 머리 줄)."""
    return bool(toss_share(url or "") or re.search(r"(^|\n)(?:(?:\[광고\][^\n]*\n)?[^\n]*" + TOSS_TAG + "|💙 토스 특가)", text[:400]))


STEADY_BUY, STEADY_REV = r"한\s*달(?:\s*동안|간)?\s*([\d,]*\d)\s*명\s*\+?\s*(?:이상\s*)?(?:구매|샀)", r"리뷰\s*([\d,]*\d)(?![\d,]*\s*(?:원|%))"  # 👍 꾸준템 가격 줄 숫자('한 달 1,000명+ 구매'·'리뷰 1,969' — 숫자로 쓴 것만)
MALLS = {"toss": ("💙 토스 특가", "💙 토스에서"), "coupang": ("🚀 쿠팡 로켓", "🚀 쿠팡에서")}  # 10/22 진우 '토스 글과 쿠팡 글을 한눈에'(색·내용 둘 다): 개별 글 머리 줄 · 구매 버튼


def mall_of(url, title=""):
    """토스·쿠팡 개별 딜인지 -> 'toss'·'coupang'·None(그 밖의 몰 = 예전 틀). 토스 = 쉐어링크·[토스]·[토스쇼핑], 쿠팡 = 제목 [쿠팡…]·쿠팡 주소."""
    tag, host = store_tag(title), urllib.parse.urlsplit(url or "").netloc.lower()
    if is_toss(url, f"[{tag}]"):
        return "toss"
    return "coupang" if "쿠팡" in tag or host in ("link.coupang.com", "coupa.ng", "coupang.com") or host.endswith(".coupang.com") else None


def mall_btn(mall, price):
    """몰별 구매 버튼: '💙 토스에서 15,580원' · '🚀 쿠팡에서 8,860원'(가격 모르면 '… 보기')."""
    won = re.search(r"\d[\d,]*\s*원", price or "")
    return f"{MALLS[mall][1]} {won[0].replace(' ', '') if won else '보기'}"


def buy_btn(title, url):
    """채널 개별 딜 버튼: 토스·쿠팡 = mall_btn, 그 밖의 몰 = 예전 buy_label('🛒 N원 구매하기')."""
    mall = mall_of(url, title)
    return mall_btn(mall, parse(title)[2]) if mall else buy_label(title)


def mall_head(mall, src, icon, rocket=True):
    """몰별 머리 줄: '💙 토스 특가 · {출처} 🔥' / '🚀 쿠팡 로켓 · {각도} 🛒'(출처·각도 모르면 칸 없이). 로켓 근거 없는 쿠팡 = '🚀 쿠팡 · …'(10/22 진우 '사실 아닌 표기 X')."""
    return f"{MALLS[mall][0] if rocket or mall != 'coupang' else '🚀 쿠팡'}{f' · {src}' if src else ''} {icon}"


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
        st = [f"한 달 {n[1]}명+ 구매" for n in [re.search(STEADY_BUY, plain)] if n] + [f"리뷰 {n[1]}" for n in [re.search(STEADY_REV, plain)] if n]
        line += "".join(f" · {x}" for x in st)
        rest = "\n".join(l for l in rest.split("\n") if not (st and re.search(f"{STEADY_BUY}|{STEADY_REV}", plain_of(l)) and re.fullmatch(r"[\W_]*", re.sub(f"{STEADY_BUY}|{STEADY_REV}", "", plain_of(l)))))
    line += "".join(f" · {x.strip()}" for x in (extra, ship) if x.strip())
    rest = re.sub(r"^((?:\n🏆[^\n]*)?)\n\n", r"\1\n", rest, count=1)  # 제목 아래 빈 줄(🏆 인기 줄은 가격 줄 아래로)
    if mall == "coupang" and "결제 전" not in plain:
        k = time.gmtime(time.time() + 9 * 3600)
        i = rest.find("\n\n출처: ")
        i = len(rest) if i < 0 else i
        rest = rest[:i] + f"\n⚠️ 결제 전 최종가 ({k.tm_mon}/{k.tm_mday} {k.tm_hour}시)" + rest[i:]
    return mall_body(mall, "" if m[1] == "🛒" else "꾸준히 팔리는 상품" if m[1] == "👍" else mall_src(mall, plain, title), m[1], name, line, [], bool(re.search(r"로켓|새벽\s*도착", plain))) + rest  # 쿠팡 '로켓' = 글에 로켓·새벽 도착 근거 있을 때만


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
    if TOSS_NO_CMP and is_toss(url, text):  # 토스 딜 = 다른 몰 비교 없이(사이트·카드·리스트·Threads)
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
    kb = [[{"text": buy_btn(title_of(notice.get("text", "")), url), "url": url}]]  # 토스·쿠팡 = 몰별 버튼(10/22)
    if not tg("editMessageText", chat_id=CHANNEL, message_id=mid, text=text, entities=ents,
              link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": kb}):
        return
    tg("editMessageText", chat_id=notice["chat"]["id"], message_id=notice["message_id"], text=text, entities=ents,
       link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": kb + [[{"text": "✅ 채널 글 교체됨", "callback_data": "-"}]]})
    for p in posts:
        if p.get("mid") == mid:
            p.update(text=text, entities=ents, url=url)
    json.dump(posts, open(POSTS, "w"), ensure_ascii=False)
    return True


def relink(m, url):
    """초안 m의 구매 버튼을 url로 교체(제휴 링크면 대가성 문구를 맨 앞에) -> (text, entities, 버튼 rows)."""
    text, ents = with_note(m.get("text", ""), m.get("entities", []), url)
    rows = [[{"text": buy_btn(title_of(text), url) if mall_of(url, title_of(text)) else "🛒 구매하러 가기", "url": url}]]  # 토스·쿠팡 링크 = 몰별 버튼(10/22)
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
    facts = facts_of(p, aff_note(link) == TOSS_NOTE)
    weak = p["score"] < MIN_SCORE - (earns(title) or aff(link))  # 진우 제휴 링크 = 수수료 되는 딜 -> 1점 완화(네이버는 EARN_TAGS에 없음: 커뮤니티 [네이버] 딜은 진우가 링크를 만들어야 수수료라서)
    m = tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", text=ad_head(aff_note(link), f"🔥 {title}\n\n{p['comment']}", p.get("unit") or "") + mall_view(toss_body(f"{'🛒' if weak else '🔥'} <b>{esc(title)}</b>\n\n"
           + ("🤔 솔직히 특가로는 약한 제품\n" if weak else "") + f"{esc(p['comment'])}{facts}", link), link),  # 토스·쿠팡 = 몰별 틀(10/22)
           link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": [[{"text": buy_btn(title, link), "url": link}]]})
    if not m:
        return False
    record(m.get("text", ""), m.get("entities", []), link, m.get("message_id"), p["score"], {**{k: p.get(k) for k in ("e", "hook", "pts", "unit", "warn", "who", "use")}, "own": 1})  # own: 진우가 보낸 링크 -> Threads 엄선에서 안 빠짐
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
               text=f"🎵 릴스 배경음악 등록 (총 {len(mus)}곡, 날마다 돌아가며 사용)")
            continue
        text = m.get("text") or m.get("caption") or ""  # 사진에 글을 붙여 보내도(캡션)
        if text.lstrip().startswith("#일상") and str(m.get("from", {}).get("id")) == ADMIN:
            daily_in({} if seen is None else seen, m, text.strip())
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
        if m.get("reply_to_message"):
            rm = m["reply_to_message"]
            tw = next((k for k, v in (seen or {}).items() if k.startswith("tw_") and isinstance(v, dict) and v.get("ask") == rm["message_id"]), None)
            if tw:  # 토스 링크 요청(toss_wait)에 답장 -> 이제 채널에 게시
                toss_post(seen.pop(tw), link)
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
            draft(ad_head(note, f"🔥 {title}\n\n{body}") + mall_view(toss_body(f"🔥 <b>{esc(title)}</b>" + (f"\n\n{esc(body)}" if body else ""), link), link),
                  link, info="🤖 자동 게시 실패(Claude 오류·채널 실패) · ✅ 누르면 게시" if note else None, label=buy_btn(title, link) if note or mall_of(link, title) else "🛒 구매하러 가기")
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
        out.append({"at": ev["at"], "icon": "👍" if th_steady(plain) and not weak else "🛒" if weak else "🔥", "name": clip(name, 26), "price": price.split("/")[0].strip(),
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


def preview(seen):
    """매일 밤 10시 '🌙 오늘 밤 특가 미리보기'(10/11 진우 '리스트 필요, 꾸준함이 중요' — 팔로워가 이 시간엔 리스트가 뜬다고 알게): 진우 예약 딜 중
    지금~다음 날 8시에 나갈 것(PREVIEW_MIN개 이상)을 시간표로 채널에 1번(시각·짧은 이름·링크·가격·같은 상품 쿠팡 차이, 대가성 문구 맨 앞) + Threads 타래(10/13: 본문 = 🔥 먼저·브랜드 1개씩 PREVIEW_TH개, 나머지 = 댓글, 링크 미리보기 = 사이트).
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
    top, brands = [], set()  # 10/13 진우 '타래 + 브랜드 섞기': 본문 = 🔥 먼저(🛒 뒤로) · 같은 브랜드(이름 첫 단어)는 1개만 -> 시각 순 PREVIEW_TH개, 나머지는 댓글(타래)로
    for d in sorted(ds, key=lambda d: "🔥👍🛒".index(d["icon"])):  # 🔥 -> 👍 꾸준템 -> 🛒
        if len(top) < PREVIEW_TH and (d["name"].split() or [""])[0] not in brands:
            top.append(d)
            brands.add((d["name"].split() or [""])[0])
    note = lambda xs: "\n".join(dict.fromkeys(aff_note(d["url"]) for d in xs if aff_note(d["url"])))
    can = TH_REPLY and th_reply_ok(seen)  # 댓글(reply_to_id)이 되는 토큰일 때만 '댓글에 👇'(10/13 — 안 되면 댓글 없이 끝 문구만)
    while True:  # Threads 500자: 대가성 문구·끝 문구는 그대로, 본문 줄을 줄임(뺀 줄은 댓글로)
        top.sort(key=lambda d: d["at"])
        rest = [d for d in ds if d not in top]
        end = lambda reply: (f"\n\n나머지 {len(rest)}개는 댓글에 👇\n🔔 시간 되면 이 계정에 하나씩 올라와요" if rest and reply else f"\n\n나머지 {len(rest)}개도 시간 되면 여기 하나씩 올라와요" if rest
                             else "\n\n🔔 시간 되면 이 계정에 하나씩 올라와요") + PREVIEW_LINKS  # 10/13 01:25 진우: 사이트·텔레그램 링크를 장점 설명과 함께 본문 글자로
        head = (note(ds) + "\n\n" if note(ds) else "") + f"🌙 오늘 밤 특가 미리보기 ({len(ds)}개)\n\n" + "\n".join(night_line(d, False) for d in top)
        if len(head + end(can)) <= 480 or len(top) <= 1:
            break
        top = top[:-1]
    try:  # 링크 미리보기 = 사이트(텔레그램 카드 X), 전체 목록 줄·'… 외 N개' X
        r = th_bundle(seen, "preview", head + end(can), f"{SITE}?ref=th")
    except Exception:
        if can and rest:  # 다음 실행 재시도(th_retry)는 본문만 -> 댓글 없는 끝 문구로
            seen[time.strftime("thretry_%Y%m%d_preview", kst)]["text"] = head + end(False)
        raise
    if not (can and rest):
        return
    parts, cur = [], []  # 댓글 = 나머지 시각 순, 댓글마다 대가성 문구 맨 앞 · 480자 이하, 본문 -> 댓글1 -> 댓글2 순으로 이어 붙임
    txt = lambda xs: (note(xs) + "\n\n" if note(xs) else "") + "\n".join(night_line(d, False) for d in xs)
    for d in rest:
        if cur and len(txt(cur + [d])) > 480:
            parts.append(txt(cur))
            cur = []
        cur.append(d)
    parts.append(txt(cur))
    done = 0
    try:
        to = r["id"]
        for p in parts:
            to = th_reply(tok, to, p)
            done += 1
        seen["threply"] = {**seen["threply"], "t": time.time()}  # 되면 3일마다 다시 확인 안 함(계속 씀)
    except Exception as e:  # 본문은 이미 나감 -> 관리자에게 바로(못 올린 댓글 붙여넣기용), 다음 날부터 댓글 없는 끝 문구
        seen["threply"] = {"t": time.time(), "ok": 0, "err": (getattr(e, "body", "") or repr(e))[:300]}
        print("preview 댓글 실패", seen["threply"]["err"])
        tg("sendMessage", chat_id=ADMIN, text=f"⚠️ 22시 미리보기 댓글 실패 — 본문은 나갔고 댓글 {len(parts)}개 중 {len(parts) - done}개 못 올림({err_brief(e)}). "
           "본문에 \"댓글에 👇\"가 남아 있어 — 아래 글을 Threads 앱에서 댓글로 붙여넣거나 본문 삭제\n\n" + "\n\n— — —\n\n".join(parts[done:]))


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
               reply_markup={"inline_keyboard": [[{"text": "🚀 쿠팡 바로가기", "url": CP_FRESH if "프레시" in p["q"] else CP_HOME}]]})  # 쿠팡 버튼 = 🚀(10/22)
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
    booked = {re.sub(r"\W", "", e["name"]) for e in load(EVENTS, []) if e.get("name") and e["at"][:10] == time.strftime("%Y-%m-%d", kst)}  # 진우 링크로 오늘 예약한 토스 상품은 자동 글에서 뺌(같은 상품 두 번 방지, 10/11)
    picked = {v.get("id") for k, v in seen.items() if k.startswith("pk_" + time.strftime("%Y-%m-%d", kst)) and isinstance(v, dict)}  # 오늘 이름 예약(toss_picks)으로 찾은 상품도(이름이 달라도 id로)
    items = list({x["tacaItemId"]: x for x in raw if not x.get("isSoldOut") and f"tb_{x['tacaItemId']}" not in seen and toss_ok(seen, x["tacaItemId"])
                  and re.sub(r"\W", "", x["displayName"]) not in booked and x["tacaItemId"] not in picked}.values())  # 카테고리 겹친 상품은 1번만 · 토스 점검 땐 보관 링크 있는 것만
    picks = items and ai_pick(SPECIAL_PROMPT if special else BEST_PROMPT if best else GOLD_PROMPT.replace("쿠팡 골드박스", "토스쇼핑 하루특가") + TOSS_EASE + TOSS_WU,
                              [f"{x['displayName']} | {x['displayPrice']:,}원 ({x.get('discountRate', 0)}% 할인)"
                               + (f" | 리뷰 {x.get('reviewScore')}점 {x['reviewCount']:,}개" if x.get("reviewCount") else "") for x in items])[:5 if special or not best else 3]
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
        plain.append(f"{NUM[len(plain)]} {clip(x['displayName'], 24)} — {x['displayPrice']:,}원" + (" (하루특가·밤 12시까지)" if x["tacaItemId"] in night else "") + f"\n{link}")
        rows.append((x["displayName"], link, (["⏰ 토스 하루특가 · 밤 12시까지"] if x["tacaItemId"] in night else []) + [f"💰 <b>{x['displayPrice']:,}원</b>" + (f" ({x['discountRate']}%↓)" if x.get("discountRate") else "")
                                             + (f" · ⭐ {x['reviewScore']} (리뷰 {x['reviewCount']:,})" if x.get("reviewCount") else ""), "👉 " + esc(p["comment"])]))
    print("toss_special" if special else "toss_beauty" if beauty else "toss_cat" if cat else "toss_best" if best else "toss_deals", len(items), "items", len(picks or []), "picks", len(rows), "links")  # 0건이어도 로그로 확인
    if raw or special:  # 목록을 받았으면(Claude까지 돌렸으면, 특가는 후보 0개여도) 이번 회차는 끝(발급이 다 막혀도 15분마다 다시 고르지 않게). Threads가 실패해도 채널에 두 번 안 올라가게 먼저 표시
        seen[key] = time.time()
    if rows:
        text, kb = top_post(head.format(len(rows)), rows)
        m = tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True},
               text=f"<i>{TOSS_NOTE}</i>\n\n{text}" + (tail := f"\n\n{toss_when()}" if TOSS_NO_CMP else ""), reply_markup={"inline_keyboard": kb})
        if m:
            bundled(seen)
        if m:  # 품절 지켜보기(toss_soldout): 글을 다시 그릴 재료 + 상품별 [id, 이름, 올린 가격, 하루특가?, 상태, 마지막 확인]
            seen[f"sold_{m['message_id']}"] = {"t": time.time(), "d": time.strftime("%Y-%m-%d", kst), "k": "top", "pre": f"<i>{TOSS_NOTE}</i>\n\n", "tail": tail,  # tail = 게시 시점 가격 줄(품절 고칠 때 빠지던 것)
                                               "head": head.format(len(rows)), "rows": rows, "it": [[x["tacaItemId"], x["displayName"], x["displayPrice"], int(not best or x["tacaItemId"] in night), 0, 0] for x in got]}
    tok = E.get("THREADS_TOKEN")
    kind = "special" if special else "beauty" if beauty else "cat" if cat else "best" if best else "day"
    lst = kind in TH_TOSS_KINDS and (hrs[-1] in TH_LIST_HOURS or kind == "cat")  # 이 회차가 Threads 리스트로도 나가는지
    if rows and tok and kind in TH_TOSS_FILL:  # 10/12 22:45·22:50 진우 '토스 인기 생필품·많이 팔리는 제품 꾸준하게': 이 회차 픽을 Threads 개별 글 채움 후보로(45분 칸이 비었을 때 토스 픽 먼저, 3시간 안)
        seen["thtoss"] = {"t": time.time(), "q": [x for x in seen.get("thtoss", {}).get("q", []) if time.time() - x["t"] < 3 * 3600] + [  # 사이트·posts.json X, 쉐어링크 그대로
            {"t": time.time(), "l": lst, "id": x["tacaItemId"], "n": x["displayName"], "k": kind, "r": n, "s": next((p.get("score", 0) for p in picks if items[p["i"]] is x), 0), "bt": th_beauty(x["displayName"]),
             "text": toss_th("하루특가 · 밤 12시까지" if x["tacaItemId"] in night else x.get("_src", ""), name, toss_price(x), toss_lines(gp[n]), link), "link": link} for n, (x, (name, link, lines)) in enumerate(zip(got, rows))]}
    if rows and tok and lst:  # Threads는 12·15·18시 베스트 리스트 + 17시 생필품(식품·생활용품) 리스트(10/12 22:45 진우)만(10/11 진우 '나누지 말고 묶기' — 나머지 회차는 채널에만). 500자 -> 넘치면 뒤 상품부터 뺌, 대가성 문구 맨 앞
        while len(plain) > 1 and len(TOSS_NOTE) + len(head) + len("\n\n".join(plain)) > 480:
            plain.pop()
        text = f"{TOSS_NOTE}\n\n{re.sub('<.*?>', '', head).format(len(plain))}\n\n" + "\n\n".join(plain) + (f"\n\n{toss_when()}" if TOSS_NO_CMP else "")
        th_bundle(seen, f"toss{hrs[-1]}", text[:500])
    elif rows and tok and beauty and th_day(seen, time.time())["b"] < TH_BEAUTY_MIN and not jw_beauty(seen, time.time()):  # 오늘 화장품 자리가 비었고 진우 화장품 링크가 더 없으면
        k = next((n for n, x in enumerate(got) if th_beauty(x["displayName"]) == 2), 0)  # 이 회차 1개를 Threads 개별 글로(소모품 먼저, 없으면 Claude 1순위) — 10/11 23:50 진우
        bt, (name, link, lines) = max(1, th_beauty(got[k]["displayName"])), rows[k]
        text = toss_th(got[k].get("_src", ""), name, toss_price(got[k]), toss_lines(gp[k]), link)
        if TH_SLOTS:  # 슬롯 방식: 줄에(15시 슬롯·20시 슬롯에 1순위로 골리면 나감)
            th_queue(seen, text, link, bt)
        elif th_solo(seen, plain_of(text), beauty=bt, slot=True):
            th_mark(seen, bt)
            me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
            th_deal(seen, tok, me, text, link)


def toss_th(src, name, price, lines, link):
    """토스 API 상품 Threads 개별 글(매시 개별·뷰티 회차 채움·토스 픽 채움·이름 예약): 대가성 문구 → 머리 줄 '💙 토스 특가 · 출처 🔥'(채널 글과 같게, 10/22 진우 '한눈에')
    → 상품명 → 가격 줄 → 줄들(🙋·👍, 일반 글자) → 게시 시점 가격 → 쉐어링크(API 상품 = 사이트·쿠팡 비교 X). 480자 넘으면 👍 → 🙋 줄 순서로 뺌(10/20 진우 — 머리·가격·대가성 문구·게시 시점·링크는 그대로)."""
    for drop in ("", "👍", "🙋"):
        lines = [l for l in lines if not (drop and l.startswith(drop))]
        text = th_note(TOSS_NOTE) + f"{mall_head('toss', src, '🔥')}\n{clip(name, 60)}\n{price}" + "".join("\n" + clip(l, 120) for l in lines) \
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
    목록은 seen에 저장해 재사용(문서 권장, 일 상한 10,000개): 카테고리·하루특가 = 하루 1번(9시 갱신), 베스트 = 1시간 1번(못 찾은 딜이 남아 있을 때만).
    10/18 진우 '나머지 토스 링크는 뽐뿌 말고 바로 연결': TOSS_BACKFILL 글(3일 지난 글 포함)도 1번 새로 찾고(하루 넘은 글은 지금 가격이 글 가격보다 15% 넘게 비싸면 특가 끝 -> 연결 X),
    올린 지 TOSS_WAIT(2시간) 지나도 못 찾은 글은 진우에게 링크 요청 1번(toss_ask — 답장하면 사본 답장과 같은 길로 교체, posts.json cp·ask)."""
    kst = lambda h: time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - h * 3600))
    since, late, old = kst(72), kst(TOSS_WAIT / 3600), kst(24)
    key = lambda p: ("trb_" if p["mid"] in TOSS_BACKFILL else "tr_") + str(p["mid"])  # 백필 = 새 기록(10/18 01시 크레딧 바닥 때 Claude 없이 '본 후보'로 넘어간 1204 등)
    todo = [p for p in load(POSTS, []) if HAS_TOSS and p.get("mid") and (p["t"] >= since or p["mid"] in TOSS_BACKFILL) and not toss_share(p.get("url")) and not p.get("ask")
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


def toss_post(w, link):
    """기다리던 토스 딜(main이 보관한 Claude 판단 그대로)을 쉐어링크로 채널에 — 대가성 문구 맨 앞·게시 시점 가격 줄은 deal_post가."""
    p = w["p"]
    post_or_draft({**w["d"], "toss": link}, p["comment"], p["score"], p.get("q"), {k: p.get(k) for k in ("e", "hook", "pts", "unit", "warn", "who", "use")})


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
            toss_post(w, link)
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
            p = (ai_pick(PICK_PROMPT, [f"{r['n']} | {price:,}원 ({x.get('discountRate', 0)}% 할인)" + (f" | 리뷰 {x.get('reviewScore')}점 {x['reviewCount']:,}개" if x.get("reviewCount") else "")]) or [None])[0]
        except Exception as ex:  # 코멘트 없이도 올림(사람이 고른 상품)
            print("toss pick comment", repr(ex))
            p = None
        info, lines = "하루특가 · 밤 12시까지" if night else "", toss_lines(p)  # 10/20 진우 '사고 싶게' 🙋·👍(없으면 Claude 한 줄)
        body = mall_body("toss", info, "🔥", r["n"], toss_price(x), list(map(esc, lines)) + ([toss_when()] if TOSS_NO_CMP else []))  # 10/22 진우 '토스·쿠팡 한눈에'
        btn = mall_btn("toss", f"{price:,}원")
        r["st"] = "done"  # 먼저 표시: 채널·Threads 실패해도 같은 글 반복 안 함
        m = tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True},
               text=ad_head(TOSS_NOTE, plain_of(body)) + body, reply_markup={"inline_keyboard": [[{"text": btn, "url": r["link"]}]]})
        if not m:
            r["st"] = None  # 채널 실패 -> 다음 실행에 다시
            continue
        seen[f"tb_{r['id']}"] = {"t": now, "n": r["n"]}  # 3일 동안 토스 자동 회차에 다시 안 올림
        bundled(seen)  # 토스 자동 회차가 이 글과 10분 띄우고 1시간 글 수에도 셈
        seen["ev_" + e["at"]] = now  # 실제 게시 시각(events()와 같은 키 — api 예약은 events()가 안 봄) -> toss_solo가 뒤 10분 쉼
        seen[f"sold_{m['message_id']}"] = {"t": now, "d": today, "k": "ev", "pre": ad_head(TOSS_NOTE, plain_of(body)), "body": body, "btn": btn, "url": r["link"],
                                           "n": r["n"], "p": price, "it": [[r["id"], r["n"], price, night, 0, 0]]}  # 품절 지켜보기(진우 예약 글과 같은 모양)
        print("toss pick", e["at"], clip(r["n"], 30), f"{price:,}원 게시")
        bt = th_beauty(r["n"])
        text = toss_th(info, r["n"], toss_price(x), lines, r["link"])
        if tok and TH_SLOTS:  # 슬롯 방식: 줄에 → 슬롯에 1순위로 골리면 나감
            th_queue(seen, text, r["link"], bt)
        elif tok and th_solo(seen, plain_of(body), fill=True, beauty=bt, slot=True):  # Threads 개별 글(하루 5개·45분 간격 같이 셈, 진우 화장품 이름 예약은 화장품 자리 채움): 대가성 문구 맨 앞, 실패는 main()이 알림
            th_mark(seen, bt)
            me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
            th_deal(seen, tok, me, text, r["link"])


TOSS_SOLO_HOURS = range(0, 24)  # 10/13 22:30 진우 '토스 쇼핑에서 추출해서 자동으로 올려줘' -> '매시 1개': 이 시각마다 토스 API 상품 개별 글 1개(10/22 진우 '새벽에도' -> 0~8시도, 밤 발송은 무음). () = 끔
TOSS_GAP_MIN, TOSS_GAP_NIGHT, TOSS_EV_PAD = 30, 60, 10 * 60  # 10/15 진우 '꾸준하게': 그 시각들에 채널 딜 글이 마지막 글 뒤 30분(0~8시는 60분, 10/22) 넘게 없으면 그 실행에 1개 더(빈틈 채움, 0 = 끔) · 진우 예약(events.json) 시각 앞뒤 10분이면 그 실행은 쉼(예약 먼저 — 예전 '예약 있는 시각 통째로 건너뜀' 대신)
TOSS_SOLO_SRC, TOSS_SOLO_MIN, TOSS_SOLO_TRY = ("best", "beauty", "life", "day"), 7, 2  # 시각마다 돌아가며(많이 팔린 순위 -> 화장품 -> 생필품 -> 하루특가) · 점수 7↑ · 출처 2곳까지(Claude·API 아낌)
SOLO_PROMPT = SPECIAL_PROMPT.replace("특가 후보 목록이야(할인율 높고 리뷰 있는 상품, ", "상품 목록이야(") + TOSS_EASE + "\ncomment는 단위가격·구성 같은 사실 한 줄만.\n"


def kst_ts(at):
    """'YYYY-MM-DD HH:MM'(KST) -> epoch."""
    return datetime.strptime(at[:16], "%Y-%m-%d %H:%M").replace(tzinfo=KST).timestamp()


def ch_last(seen):
    """텔레그램 채널 마지막 딜 글 시각(epoch): 이번 실행(RUN) · 지난 실행 기록(seen) · posts.json 마지막 딜(토스 API 글은 posts.json에 없어서 기록이 주, 첫 배포 땐 posts.json)."""
    t = max((p["t"] for p in load(POSTS, []) if not p["text"].startswith("📋")), default="")
    return max(RUN["ch_last"], seen.get("ch_last", {}).get("t", 0), t and kst_ts(t) or 0)


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
    ats = [e["at"] for e in evs if re.match(r"\d{4}-\d\d-\d\d ([01]\d|2[0-3]):[0-5]\d$", e.get("at", ""))]  # 손으로 넣은 시각 모양이 틀려도 멈추지 않게
    if any(abs(kst_ts(a) - now) <= TOSS_EV_PAD or now - seen.get("ev_" + a, 0) <= TOSS_EV_PAD for a in ats):  # 진우 것 먼저(예약은 실행 간격만큼 늦게 나가서 실제 게시 시각으로도)
        print(f"toss solo {h:02d}: 쉼(진우 예약 앞뒤 {TOSS_EV_PAD // 60}분)")
        return
    if gap:
        seen["tgap"] = {"t": now}  # 빈틈 채움 시도 — 못 찾아도 TOSS_GAP_MIN 동안 다시 안 찾음(API·Claude 아낌)
    since = time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 9 * 3600 - 86400))
    recent = lambda at: at[:10] == today or at >= since  # 오늘 + 지난 24시간(밤 12시 넘어 어젯밤 진우 예약 상품이 다시 나가지 않게 — 10/22 0~8시 글 켜며)
    booked = {norm(e["name"]) for e in evs if e.get("name") and recent(e.get("at", ""))}
    picked = {v.get("id") for k, v in seen.items() if k.startswith("pk_") and recent(k[3:]) and isinstance(v, dict)}
    tree, tried, best, tops = None, 0, None, top_toss(seen, now)  # tops = 잘 된 토스 상품(top.json) — 후보면 +TOP_BONUS점(하루 TOP_BONUS_DAY번)
    for src in [TOSS_SOLO_SRC[(h + n) % len(TOSS_SOLO_SRC)] for n in range(len(TOSS_SOLO_SRC))] + (["stock"] if RUN.get("treuse") else []):  # 토스 점검 = 마지막에 보관 링크 상품(stock)도
        if src == "day" and (h < 9 or h == 23 and kst.tm_min >= 30) or tried >= TOSS_SOLO_TRY and src != "stock":  # 하루특가 목록은 9시에 바뀜(그 전엔 어제 것) · 23:30 넘으면 '밤 12시까지'가 몇 분 안 남음
            continue
        label = None
        if src == "stock":  # 3일 안 안 올린 보관 링크 상품 최근 것 30개 -> 상세로 지금 가격·품절(순위는 옛 것이라 머리 줄 출처 X)
            ids = [i for i, _ in sorted(seen.get("tlink", {}).get("m", {}).items(), key=lambda kv: -kv[1][1]) if f"tb_{i}" not in seen]
            ids = (ids[(kst.tm_yday * 24 + h) * 30 % len(ids):] + ids)[:30] if ids else []  # 시각마다 다음 30개(같은 30개만 보지 않게 — 10/22 리뷰)
            raw = toss("/products/detail?tacaItemIds=" + ",".join(ids))["items"] if ids else []
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
        items = [(r + 1, x) for r, x in enumerate(raw) if not x.get("isSoldOut") and f"tb_{x['tacaItemId']}" not in seen and toss_ok(seen, x["tacaItemId"])
                 and norm(x["displayName"]) not in booked and x["tacaItemId"] not in picked]
        picks = [p for p in (items and ai_pick(SOLO_PROMPT, [f"{x['displayName']} | {x['displayPrice']:,}원 ({x.get('discountRate', 0)}% 할인)"
                                                               + (f" | 리뷰 {x.get('reviewScore')}점 {x['reviewCount']:,}개" if x.get("reviewCount") else "") for _, x in items]) or []) if 0 <= p["i"] < len(items)]
        for p in picks:  # 10/22 Cowork: 잘 된 토스 상품(판매 중·3일 지남 = 위 품절·tb_ 거름 그대로)은 +TOP_BONUS점
            if top_hit(tops, items[p["i"]][1]["tacaItemId"], items[p["i"]][1]["displayName"]):
                p.update(score=p["score"] + TOP_BONUS, top=1)
        picks = [p for p in picks if p["score"] >= TOSS_SOLO_MIN]
        if picks:
            best = (src, label, max(picks, key=lambda p: (p["score"], p.get("top", 0))))  # 같은 점수면 잘 된 상품
            break
    if not best:
        seen[key] = now
        print(f"toss solo {h:02d}{f' 빈틈 {gap}분' if gap else ''}: 7점↑ 없음(출처 {tried}곳)")
        return
    src, label, p = best
    rank, x = items[p["i"]]
    name, price = x["displayName"], x["displayPrice"]
    link = toss_link(seen, x["tacaItemId"], name)
    if not link:  # 토스 점검인데 보관 링크 없음(위에서 걸러서 거의 없음) -> 이 시각은 끝
        seen[key] = now
        return
    info = "하루특가 · 밤 12시까지" if src == "day" else f"많이 팔린 순위 {rank}위" if src == "best" else f"{label} {rank}위" if label else ""  # 머리 줄 출처(10/22 진우 시안 '생필품 베스트 3위')
    lines = toss_lines(p)  # 🙋 누가·👍 언제(10/20 a7cee6f 그대로)
    body = mall_body("toss", info, "🔥", name, toss_price(x), list(map(esc, lines)) + [toss_when()])  # 10/22 진우 '토스·쿠팡 한눈에': 💙 토스 특가 · 출처 → 상품명 → 가격 (할인) · ⭐ → 🙋 → 게시 시점 가격
    head, btn = ad_head(TOSS_NOTE, plain_of(body)), mall_btn("toss", f"{price:,}원")
    m = tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True}, text=head + body, reply_markup={"inline_keyboard": [[{"text": btn, "url": link}]]})
    if not m:
        return  # 다음 실행에 다시(실패는 바로 알림)
    seen[key] = now
    seen[f"tb_{x['tacaItemId']}"] = {"t": now, "n": name}  # 3일 동안 묶음 회차·다음 개별 글에서 빠짐
    if p.get("top"):
        top_mark(seen, now, x["tacaItemId"])
    bundled(seen)
    seen[f"sold_{m['message_id']}"] = {"t": now, "d": today, "k": "ev", "pre": head, "body": body, "btn": btn, "url": link, "n": name, "p": price,
                                       "it": [[x["tacaItemId"], name, price, int(src == "day"), 0, 0]]}  # 품절 지켜보기(진우 예약 글과 같은 모양)
    if E.get("THREADS_TOKEN"):  # Threads = 채움 후보(45분 간격·화장품 한도 그대로)
        seen["thtoss"] = {"t": now, "q": [q for q in seen.get("thtoss", {}).get("q", []) if now - q["t"] < 3 * 3600] + [
            {"t": now, "l": False, "id": x["tacaItemId"], "n": name, "k": "solo", "r": 0, "s": p["score"] - TOP_BONUS * bool(p.get("top")), "bt": th_beauty(name), "text": toss_th(info, name, toss_price(x), lines, link), "link": link}]}
    print(f"toss solo {h:02d}{f' 빈틈 {gap}분' if gap else ''}: {clip(name, 30)} ({src} {rank}위 · {p['score']}점{' · 잘 된 상품 +' + str(TOP_BONUS) if p.get('top') else ''})")


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
    return text, mall_btn(mall, won[0] if won else parse(t)[2]) if mall and btn.startswith("🛒") else btn


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


TH_LINK_AB, TH_AB_MARK = True, "👇 구매 링크는 첫 댓글에"  # 10/18 18:30 진우 'Threads 개별 딜 글 링크 위치 A/B — 절반만 시험'(10/25 점검 때 비교해 이긴 쪽으로): False = 지금처럼 A만
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
    return f"{body}\n\n{TH_AB_MARK}", f"{head}👉 {re.sub(r'[?]ref=th$', '?ref=thc', link)}\n📲 실시간 알림 t.me/hotdeal_pick"


TH_VOICE, TH_GAP_JITTER = True, 10 * 60  # 10/21 밤 진우 'Threads 개별 딜 글 사람이 올리는 느낌': 본문을 Claude가 반말·음슴체 문장으로(th_voice, False = 지금 틀) · 개별 글 간격 45분 ± 10분(th_gap, 0 = 45분 그대로)
VOICE_LABEL = ("⭐", "💰", "🙋", "👍", "💡", "⚠", "🔥", "🛒", "👉", "👇", "📲", "👋", "💸", "🔔", "🏆", "⏰", "🤔", "🚀", "💙", "📊", "🚚", "[", "#")  # 이걸로 시작하는 줄 = 라벨·제목 줄(문장 아님)
VOICE_BAN = "|".join((WU_FAKE, r"샀는데|사\s*봤|사봄|사\s*보니|질렀|재구매|쓰는\s*중|(?:어제|작년|지난번|저번|예전)에?\s*\S*\s*샀|(?<![가-힣])(?:내가|나도|난|나는|저는|저도|우리\s*집)(?![가-힣])", WU_HEALTH, WU_HYPE, r"눌러"))  # 써 본 척(반말·음슴체 '나도·질렀' 포함, '비교해봤는데'·'N명 넘게 삼'은 OK)·효능·과장·조급·클릭 유도(토스 글은 + 다른 몰·비교)
VOICE_YO = r"(?<![필중주수소])요(?![가-힣])|죠(?![가-힣])|(?<![다아])니다(?![가-힣])"  # 해요체(~요·~죠)·~니다로 끝나는 말('확인 필요'·'중요' 같은 낱말은 아님, '30개요'는 해요체)
VOICE_EMOJI = r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u231A-\u23FA\u2B05-\u2B55\u203C\u2049]\uFE0F?|[#*0-9]\uFE0F?\u20E3|\S\uFE0F|\u200D"  # → 같은 화살표는 아님(음슴체 예시)
VOICE_PROMPT = """Threads에 올릴 핫딜 글 본문을 사람이 직접 쓰듯 써 주세요. 아래 '재료'에 있는 사실만(없는 내용·숫자 X, 숫자는 재료 그대로 — 어림은 '넘게'처럼 아래로만).
- lines = 3~4줄. 줄 길이는 들쭉날쭉하게, 짧은 조각 문장도 OK. 맞춤법은 정상(일부러 틀리지 않기). 이모지는 0~1개. 질문은 lines에 쓰지 않기(q에만).
- 해요체 X: '~요'로 끝나는 말(~해요·~해 주세요·~대요·~거든요 등) 쓰지 않기.
- 둘째 줄까지 안에 상품명(브랜드 그대로), 글 어딘가에 가격(재료의 원 단위 숫자 그대로, 예 8,860원)을 꼭 넣기.
- 쓸 거리: 구성·단위가격·리뷰 수·구매 수·로켓/와우·포장 표기·누구에게/언제 좋은지.
- ⭐💰🙋👍💡⚠️🔥 같은 이모지로 시작하는 라벨 줄, [몰] 제목 줄, 링크, 해시태그, 광고 문구, '결제 전 확인'·'게시 시점' 문장은 쓰지 않기(따로 붙임).
- 써 본 척(제가·나도·써보니·먹어보니·샀는데·질렀음 — '비교해봤는데'처럼 실제로 한 일은 OK), 효능·건강·의학 말, 과장·조급(역대급·무조건·손해·마지막 기회), 클릭 유도(클릭·눌러) 쓰지 않기.
- '최근 글'과 문장 틀·첫 문장을 다르게.
- 재료에서 날짜(10/21·어제 등)가 붙은 숫자(예: '10/21 쿠팡 검색 기준 469원')를 쓰면 그 날짜도 같은 줄에 그대로(오늘 숫자처럼 쓰지 않기)."""
VOICE_STYLE = {  # 10/21 밤 진우 '너무 AI 같다' -> 두 시안 '섞어서': 글마다 무작위 A·B(한 글 안에선 하나), 해요체 X
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


def ai_voice(prompt):
    """Claude가 쓴 Threads 개별 글 문장 {lines, q}(th_voice)."""
    return ai_json(prompt, {"lines": {"type": "array", "items": {"type": "string"}}, "q": {"type": "string"}})


def th_voice(seen, text, link, src=None):
    """Threads 개별 딜 글(th_deal로 가는 글 전부)을 사람이 쓰듯 — 10/21 밤 진우: 대가성 문구 첫 줄 그대로 → Claude 문장 2~4줄(글마다 무작위 A 반말 / B 음슴체, 해요체 X,
    재료 = 그 글에 이미 있는 사실, 둘째 줄까지 상품명 · 가격은 어딘가에, 질문은 lines X) → 가격 기준 줄(토스 = '⚠️ M/D HH:MM 게시 시점 가격' 그대로, A = '가격은 바뀌니까 결제 전에 한번 확인 (어제 저녁 7시 기준)',
    B = '결제 전 가격 확인 필수 (M/D H시 기준)') → A일 때만 3개에 1개쯤 가벼운 질문 → 👉 링크. 이모지는 0~1개(토스 글은 ⚠️가 1개 — 넘으면 다 뺌).
    라벨 줄·써 본 척·효능·과장·클릭 유도(토스 글은 + 다른 몰·비교)·재료에 없는 원 금액 든 문장은 그 문장만 뺌. 상품명·가격이 빠지거나 ~요로 끝나는 줄·최근 10개와 같은 첫 문장이
    (1번 다시 써도) 남거나 480자에 못 넣으면(질문 -> 뒤 줄부터, 상품명·가격 줄은 남김) · Claude 실패 = 지금 틀(text) 그대로. 👋 팔로우·📲 줄은 뺌(B 첫 댓글엔 📲 그대로 — th_ab).
    src = 줄이기 전 글(재료, 없으면 text)."""
    full = src or text
    if not full.startswith(NOTE_STARTS):
        return text
    try:
        head, rest = full.split("\n\n", 1)
        toss = TOSS_NO_CMP and is_toss(link, full)
        facts = [l for l in rest.split("\n") if l.strip() and not TH_AB_URL.search(l) and not l.startswith(("👋", "📲")) and "게시 시점" not in l]
        hi = next((i for i in range(len(facts)) if mall_title(facts, i)), None)  # 몰별 틀(10/22): 머리 줄은 고정 줄로 그대로 두고 다음 두 줄이 상품명·가격
        mall, mhead = ("toss" if facts[hi].startswith("💙") else "coupang", facts[hi] + "\n") if hi is not None else (None, "")
        _, name, price = parse(mall_title(facts, hi) if mall else re.sub(r"^[🔥🛒👍]\s*", "", next((l for l in facts if l.startswith(("🔥", "🛒", "👍"))), "")))
        steady = th_steady(full)  # 👍 꾸준템 = '최저가는 아니지만 꾸준히 팔리는 것' 솔직하게(특가·최저 말 X)
        won = lambda s: {x.replace(",", "") for x in re.findall(r"(\d[\d,]*)\s*원|(\d[\d,]{3,})\s*(?:에서|짜리|→)", s) for x in x if x} | {x + "%" for x in re.findall(r"(\d+)\s*%", s)} \
            | {re.sub(r"\s", "", x) for x in re.findall(r"\d[\d\s]*[만천][\d만천백\s]*원", s)}  # 원 금액·%·'1만6천원' 꼴 금액
        p0 = re.search(r"\d[\d,]*(?=\s*원)", price) or re.search(r"\d[\d,]*(?=\s*원)", "\n".join(facts))
        names = [w for w in re.findall(r"[가-힣A-Za-z]{2,}", re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", name)) if not re.fullmatch(r"(?i)ml|kg|mg|cm|mm|ea|국내산|국산|제로|대용량|프리미엄|냉동|냉장|무항생제|유기농|정품|신상|특대|년산|무료배송|특가|세트|오리지널|시그니처|산지직송|제철|기획|단독|한정|증정", w)][:2]
        if not (p0 and names):
            raise ValueError("상품명·가격 못 읽음")
        style, st, norm = random.choice("AB"), seen.get("thvoice", {}), lambda s: re.sub(r"[\W_]+", "", s)
        if toss:
            basis = next((l for l in rest.split("\n") if "게시 시점" in l), "") or toss_when()
        else:
            m, now = re.search(r"\((\d{1,2})/(\d{1,2}) (\d{1,2})(?::\d{2})?시?(?: 가격)?\)", full), time.time() + 9 * 3600  # '(10/22 9시 가격)'·쿠팡 몰별 틀 '(10/22 10시)'
            k = time.gmtime(now)
            mo, d, h = (int(m[1]), int(m[2]), int(m[3])) if m else (k.tm_mon, k.tm_mday, k.tm_hour)
            y = time.gmtime(now - 86400)
            day = "오늘" if (mo, d) == (k.tm_mon, k.tm_mday) else "어제" if (mo, d) == (y.tm_mon, y.tm_mday) else f"{mo}/{d}"
            part = "새벽" if h < 6 else "오전" if h < 12 else "오후" if h < 18 else "저녁" if h < 21 else "밤"
            basis = f"가격은 바뀌니까 결제 전에 한번 확인 ({day} {part} {h % 12 or 12}시 기준)" if style == "A" else f"결제 전 가격 확인 필수 ({mo}/{d} {h}시 기준)"
        ask = style == "A" and st.get("k", 0) >= 1  # 질문 = A(반말)일 때만, 앞 질문 뒤 1개 쉬고 A면 -> 3개에 1개쯤
        ban = VOICE_BAN + (f"|{TOSS_BAN}" if toss else "") + (r"|특가|최저(?!가?는\s*아니|가\s*아니)|할인" if steady else "")
        yd, dated, flat = time.gmtime(time.time() + 9 * 3600 - 86400), {}, set()  # 날짜 붙은 숫자(10/22 Cowork: '10/21 쿠팡 검색 기준 469원'이 날짜 없이 '오늘 10시 기준' 글에 — 어제 숫자가 오늘 숫자처럼)
        for l in facts:  # 가격 확인 시각 '(10/22 10시 가격)'은 숫자 날짜가 아님
            ds = set(re.findall(r"(?<![\d/])\d{1,2}/\d{1,2}(?![\d/])|어제|그제", re.sub(r"\(\d{1,2}/\d{1,2} \d{1,2}(?::\d{2})?시?(?: 가격)?\)", "", l)))
            for w in won(l):
                dated.setdefault(w, set()).update(ds) if ds else flat.add(w)
        for ds in dated.values():  # 어제 날짜 = '어제'로 써도 OK(반대도)
            ds |= {"어제", f"{yd.tm_mon}/{yd.tm_mday}"} if ds & {"어제", f"{yd.tm_mon}/{yd.tm_mday}"} else set()
        when = lambda s, w: w not in dated or w in flat or any(d in s for d in dated[w])
        ok = lambda s: s and not s.startswith(VOICE_LABEL) and not TH_AB_URL.search(s) and not re.search(rf"{ban}|링크|댓글|팔로우|광고|수수료|결제 전|게시 시점", re.sub("|".join(map(re.escape, names)), "", s)) \
            and won(s) <= won(rest) and all(when(s, w) for w in won(s))  # 재료에 없는 금액·% X · 금지어는 상품명 빼고 봄('더건강플러스'의 건강 X) · 날짜 붙은 숫자는 그 날짜와 같이(10/22)
        prompt = VOICE_PROMPT + "\n- " + VOICE_STYLE[style] + ("\n- 토스 딜: 다른 쇼핑몰 이름·가격 비교(보다 싸·젤 싸·비교) 없이 이 상품 자체 정보만." if toss else "") \
            + {"toss": "\n- 이 글 = 토스 '오늘 특가 소식': 짧게, 순위·할인·마감·누가 쓰면 좋은지 위주(재료에 있는 것만).",
               "coupang": "\n- 이 글 = 쿠팡 '로켓 가격 비교': 1개당 가격·참고 비교·도착 위주(재료에 있는 것만).",
               "steady": "\n- 이 글 = '꾸준히 팔리는 상품': '최저가는 아니지만 꾸준히 팔리는 것' 결로 솔직하게(특가·최저가·할인이라고 하지 않기), 한 달 구매 수·리뷰 수·구성·누가 쓰면 좋은지 위주(재료에 있는 것만)."}.get("steady" if steady else mall, "") \
            + ("\n- q = 마지막에 붙일 가벼운 반말 질문 한 줄(예: 다들 핫팩 몇 개씩 쟁여둬?), 최근 질문과 다르게." if ask else "\n- q = 빈 문자열.") \
            + f"\n\n상품명: {name}\n가격: {price or p0[0] + '원'}\n재료:\n" + "\n".join(facts) \
            + "".join(f"\n\n최근 글 {n + 1}:\n{b}" for n, b in enumerate(st.get("b", [])[-5:])) + ("\n\n최근 질문: " + " / ".join(st["q"]) if ask and st.get("q") else "")
        again, yo_ = "", lambda x: re.search(VOICE_YO, re.sub("|".join(map(re.escape, names)), "", x))  # 상품명 속 '요'(요기요 등)는 빼고
        for _ in (0, 1):  # ~요로 끝나는 줄·최근 10개와 같은 첫 문장 -> 1번 다시
            a = ai_voice(prompt + again)
            ls = [x for x in (re.sub(r"\s+", " ", str(x)).strip() for x in a.get("lines") or []) if ok(x) and not re.search(r"[?？]", x)][:4]  # 질문은 q에만(A·3개에 1개쯤)
            yo, dup = [x for x in ls if yo_(x)], ls and norm(ls[0]) in st.get("f", [])
            if not yo and not dup:
                break
            again = "\n\n다시: " + (f"'{yo[0]}'처럼 ~요로 끝나는 말 X({'반말' if style == 'A' else '음슴체'}로). " if yo else "") + (f"첫 줄 '{ls[0]}'은 최근 글과 같음 — 다른 문장으로 시작." if dup else "")
        else:
            raise ValueError("~요 줄·같은 첫 문장이 다시 써도 남음")
        q = re.sub(r"\s+", " ", str(a.get("q") or "")).strip() if ask else ""
        q = q if ok(q) and not yo_(q) and norm(q) not in map(norm, st.get("q", [])) else ""
        if sum(len(re.findall(VOICE_EMOJI, x)) for x in ls + [q]) > (0 if toss else 1):  # 이모지 0~1개(👉·👇 링크 줄 빼고 — 토스 글은 ⚠️ 게시 시점 줄이 1개) -> 넘으면 다 뺌
            ls, q = [x for x in (re.sub(r"\s{2,}", " ", re.sub(VOICE_EMOJI, "", x)).strip() for x in ls) if x], re.sub(r"\s{2,}", " ", re.sub(VOICE_EMOJI, "", q)).strip()
        has = lambda x, w: w in re.sub(r"[,\s]", "", x)
        nl = next((i for i, x in enumerate(ls[:2]) if any(has(x, w) for w in names)), None)
        pl = next((i for i, x in enumerate(ls) if has(x, p0[0].replace(",", "") + "원")), None)
        if nl is None or pl is None:
            raise ValueError(f"상품명(둘째 줄까지)·가격 없음: {ls}")
        out = lambda: f"{head}\n\n{mhead}" + "\n".join(ls + [basis] + ([q] if q else [])) + f"\n\n👉 {link}"  # 몰별 머리 줄 = 대가성 문구 다음 고정 줄(이모지 셈 X)
        q = q if len(out()) <= 480 else ""
        for i in sorted(set(range(len(ls))) - {nl, pl}, reverse=True):  # 480자 넘으면 뒤 줄부터(상품명·가격 줄은 남김)
            if len(out()) <= 480:
                break
            ls.pop(i)
        if len(out()) > 480 or len(ls) < 2 or norm(ls[0]) in st.get("f", []):  # 480자 · 1줄 · 줄여서 첫 줄이 바뀌었는데 최근 글과 같음
            raise ValueError(f"480자({len(out())})·1줄·같은 첫 문장")
        seen["thvoice"] = {"t": time.time(), "s": style, "k": 0 if q else st.get("k", 0) + 1, "f": (st.get("f", []) + [norm(ls[0])])[-10:],
                           "b": (st.get("b", []) + ["\n".join(ls)])[-5:], "q": (st.get("q", []) + ([q] if q else []))[-10:]}
        print("th voice", style, clip(name, 30), f"| {len(ls)}줄" + (" + 질문" if q else ""))
        return out()
    except Exception as e:  # Claude 실패·조건 안 맞음 = 지금 틀 그대로(글은 나감)
        print("th voice 지금 틀로", clip(repr(e), 120))
        return text


def th_gap(last):
    """개별 글 간격 = TH_SOLO_GAP ± TH_GAP_JITTER(10/21 밤 진우 '35~55분 무작위') — 앞 개별 글 시각으로 정함(실행마다 다시 뽑으면 짧은 쪽으로 쏠림)."""
    return TH_SOLO_GAP + (random.Random(int(last)).randint(-TH_GAP_JITTER, TH_GAP_JITTER) if TH_GAP_JITTER else 0)


def th_deal(seen, tok, me, text, link, src=None):
    """Threads 개별 딜 글 1개(threads_deals·토스 픽 채움·슬롯 줄·뷰티 채움·토스 이름 예약·재오픈 — 묶음·날씨·간식·투표·#일상은 th_post 그대로).
    TH_LINK_AB면 직전 개별 딜 글이 A였으면 B: 본문 주소 없이(미리보기 X) 올리고 바로 첫 댓글 = 링크. 댓글 못 다는 토큰(th_reply_ok)이면 A.
    B 댓글이 실패하면 관리자 알림 + 다음 실행에 1번 더(th_retry — 링크 없는 딜 글이 남지 않게). 글마다 A/B·댓글 id -> seen(metrics.json 줄 ab·rv·48시간 v48·rv48)."""
    tt = title_of(text)  # 지금 틀 제목(사람 느낌 글은 첫 줄이 문장 -> metrics 분류·가격대는 이걸로)
    vt = th_voice(seen, text, link, src) if TH_VOICE else text  # 10/21 밤 진우 '사람이 올리는 느낌'(실패·조건 안 맞으면 지금 틀)
    voiced, text = vt != text, vt
    st, now = seen.get("thab", {}), time.time()
    ab = "B" if TH_LINK_AB and st.get("last") == "A" and th_reply_ok(seen) else "A"
    body, reply = th_ab(text, link) if ab == "B" else (text, None)
    pid, rid = (th_text(tok, me, body, None if reply else link) or {}).get("id"), None
    if reply:
        try:
            rid = th_reply(tok, pid, reply)
        except Exception as e:
            seen[f"thabq_{pid}"] = {"t": now, "id": pid, "text": reply}
            alert(seen, f"alert_thab_{pid}", f"⚠️ Threads 개별 딜 글(B: 링크는 첫 댓글)의 링크 댓글 실패: {err_brief(e)}\n다음 실행에 1번 더 달아요 — 그래도 안 되면 다시 알려요\n링크: {reply.split('👉 ')[-1].split(chr(10))[0]}")
    seen["thab"] = {"t": now, "last": ab, "m": {**{k: v for k, v in st.get("m", {}).items() if now - v["ts"] < 4 * 86400}, **({pid: {"ab": ab, "ts": now, "u": link, "n": tt, **({"v": seen["thvoice"]["s"]} if voiced else {}), **({"r": rid} if rid else {})}} if pid else {})}}  # u = 링크(B 본문엔 주소가 없어 metrics가 몰을 못 읽음) · n = 제목 · v = 사람 느낌 글 말투(A 반말·B 음슴체)
    return pid


def th_text(tok, me, text, link):
    """Threads 글 1개(TEXT + 링크 미리보기). 미리보기를 못 만들면(4279047 'Invalid Link Attachment', 10/7 15:51) 첨부 없이 1번 더 — 본문 주소는 그대로."""
    for att in ({"link_attachment": link}, {}) if link else ({},):  # 링크 없음(A/B 시험 B 본문) = 미리보기 없이
        q = urllib.parse.urlencode({"media_type": "TEXT", "text": text, **att, "topic_tag": "핫딜", "access_token": tok})
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
    urls = [f"{SITE}p/{posts.index(p)}.html?ref=tg" if aff_note(p["url"] or "") == OY_NOTE or len(p["url"] or "") > 150 else p["url"] for p in todays]  # 올영: 링크만 나열 금지(FAQ) -> 사이트 · 아주 긴 주소(G마켓 검색 링크 ~400자)도 사이트 딜 페이지로(같은 구매 버튼, 텔레그램 링크 길이 한도)
    night = night_deals(seen, today + f" {PREVIEW_HOUR:02d}:00", night_window(time.time())[1])  # 밤 10시 미리보기가 안 나갈 만큼 적은 날(PREVIEW_MIN개 미만) = 여기에 합침
    night = night if len(night) < PREVIEW_MIN else []
    toss_in = toss_list(todays) or (TOSS_NO_CMP and any(is_toss(d["url"]) for d in night))  # 합친 밤 줄도 같은 글
    if toss_in:  # 토스 딜이 든 모아보기 = 밤 줄도 다른 몰 비교 X(toss 밤 딜과 같은 처리)
        night = [{**d, "sv": None, "weak": d["weak"] and "특가로는 약함"} for d in night]
    rows = [f"{n}. <a href=\"{esc(u)}\">{esc(list_name(p, toss_in))}</a>" for n, (p, u) in enumerate(zip(todays, urls), 1)]
    notes = "\n".join(f"<i>{n}</i>" for n in dict.fromkeys(aff_note(u or "") for u in urls + [d["url"] for d in night]) if n)  # 제휴 링크 프로그램마다 1줄 맨 위(TOP 글과 같은 방식) — 밤 줄 링크도
    tail = f"\n\n🔎 지난 딜 전체 보기: {SITE}?ref=tg\n📝 블로그: {BLOG}\n📲 실시간 알림: https://t.me/hotdeal_pick"
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
        try:  # 인스타 릴스용 15초 영상 -> 관리자에게 바로 전송 + REEL_PUBLIC이면 docs/reels/에 공개 -> 22시 ig_reel이 인스타에. 점수 높은 순 TOP3
            top = [p for _, p in card_order(posts, today)][:3]  # 카드와 같은 순서(점수, 같으면 제휴 딜 먼저)
            fill_reel(top)  # ✅로 올린 글·예전 글은 릴스 재료가 없음 -> 여기서 채움(딜 카드 때 채웠으면 그대로)
            music, mus = bgm(kst), load(MUSIC, [])
            song = mus[kst.tm_yday % len(mus)] if music else None  # 캡션에 곡명(인스타에서도 무슨 곡인지 보이게)
            auto = REEL_PUBLIC and E.get("IG_TOKEN") and E.get("IG_USER_ID")
            path = cards.reel([card_item(p)[0] for p in top], f"{kst.tm_mon}월 {kst.tm_mday}일",  # 올리브영 딜은 딜 카드처럼 거른 재료
                              f"docs/reels/{today}.mp4" if auto else os.path.join(tempfile.gettempdir(), f"reel_{today}.mp4"), music)
            cap = (ig_notes(top) + "\n\n" + (top[0].get("hook") + " · " if top[0].get("hook") else "") + f"{kst.tm_mon}월 {kst.tm_mday}일 가성비 TOP{len(top)}\n\n"
                   + "\n".join(f"{n}. {title_of(p['text'])}" for n, p in enumerate(top, 1))
                   + (f"\n\n🎵 {song['name']}" + (" (Pixabay)" if song.get("url") else "") if song else "")
                   + f"\n\n🛒 구매: 프로필 링크(hotdealpick.kr) → 맨 위 '{card_name(today)}'에서 1~{len(top)}번"  # 릴스 TOP = 하루 카드 앞 번호
                   + "\n\n" + ig_tags(top))[:1024]
            if auto:
                seen["reel_" + today] = {"t": time.time(), "cap": cap}  # 22시 ig_reel이 같은 캡션으로
            tg_video(path, (f"🎬 {REEL_HOUR}시에 인스타 자동 게시돼요(직접 올리지 마세요) — 확인용\n\n" if auto else "") + cap)
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


IG_AUTO = False  # 10/17 23시 진우 '인스타 자동 게시 멈춤'(3일 연속 code 4·2207051 스팸 의심 차단 · 카드 7개 좋아요 1 · 같은 계정에 묶인 Threads 보호, 10/31 다시 판단): 카드(12·18·21시)·넘기기·릴스·다시 올리기 컨테이너·발행 전부 X, 남은 컨테이너는 발행 없이 지움 — 21시 카드 이미지·사이트·Threads 카드·metrics 인스타 읽기는 그대로. True = 다시 켬
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
            errs.append(RuntimeError(f"인스타 처리 실패({st}) — " + (f"{SITE}cards/{card(v)}.jpg 카드를 직접 올려줘" if card(v) else "오늘 릴스 영상은 봇 채팅에 온 걸 직접 올려줘")))
            continue
        if card(v) and now - v["t"] < IG_SITE_LAG:  # 사이트 맨 위에 먼저(이번 실행 배포) -> 다음 실행에 발행
            continue
        n = seen.get(day, {}).get("n", 0)
        if n >= IG_DAY_MAX or seen.get("ig_hold", 0) > now:
            print("ig publish 미룸", k, f"오늘 {n}개" + (" · 스팸 의심으로 쉼" if seen.get("ig_hold", 0) > now else ""))
            continue
        try:
            json.loads(http(f"{IG}/{uid}/media_publish", {"creation_id": k[4:]}, {"Authorization": "Bearer " + tok}, "POST"))
            RUN["ok"].add("ig")
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
        reel = isinstance(v, dict) and v.get("kind") == "reel"
        tg("sendMessage", chat_id=ADMIN, text="📸 인스타 자동 게시 완료" + (f" — {SLOT_NAMES[label[11:]]} 카드" if label[11:] in SLOT_NAMES else " — 오늘 카드" if label else " — 오늘 릴스" if reel else "") + " (instagram.com/hotdealpick.kr)")
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
    toss_in = toss_list(todays)
    title = f"{kst.tm_mon}월 {kst.tm_mday}일 핫딜 모음 | {list_name(todays[0], toss_in)}" + (f" 외 {len(todays) - 1}건" if len(todays) > 1 else "")
    items = []
    for n, p in enumerate(todays, 1):
        t = list_name(p, toss_in)
        why = next((l for l in comment_of(p["text"]).split("\n") if l and not l.startswith("🤔")), "")  # 약한 딜 표시 줄 말고 코멘트(10/11 점검: 5점 진우 딜이 '약한 제품'만 남던 것)
        why = strip_cmp("👉 " + why)[0][2:] if toss_in and why else why  # 토스 딜이 든 글 = 다른 몰 이름 조각 뺌(TOP 👉 줄과 같게)
        items.append(f"{n}. {t}\n{why}\n👉 {p['url'] or SITE}")
    notes = "\n".join(n for n in dict.fromkeys(aff_note(p["url"] or "") for p in todays) if n in (OY_NOTE, NAVER_NOTE))  # 본문 맨 위 필수인 프로그램
    return (f"📝 블로그용 (제목·본문 그대로 복붙)\n\n제목: {title}\n\n" + (notes + "\n\n" if notes else "") + "\n\n".join(items) + (f"\n\n{toss_when()}" if toss_in else "")
            + f"\n\n더 많은 핫딜 👉 {SITE}?ref=blog\n실시간 알림 👉 https://t.me/hotdeal_pick\n\n"
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
    toss_in = toss_list(ps)
    rows = [f"{n}. {clip(re.sub(PRICE_TAIL, '', list_name(p, toss_in)).strip(), 34)}" for n, p in enumerate(ps, 1)]
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
    """딜 카드 폴더(docs/cards/날짜[_시]/)·릴스 영상(docs/reels/날짜.mp4)은 SLIDE_KEEP일 지나면 지움(인스타가 이미 가져감, 사이트는 표지만 씀 — 저장소 크기).
    git add -A가 지운 것도 커밋."""
    cut = time.strftime("%Y-%m-%d", time.gmtime(now + 9 * 3600 - SLIDE_KEEP * 86400))
    for f in os.listdir("docs/cards") if os.path.isdir("docs/cards") else []:
        if STEM.fullmatch(f) and f[:10] < cut and os.path.isdir(f"docs/cards/{f}"):
            shutil.rmtree(f"docs/cards/{f}")
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
        c = json.loads(http(f"{IG}/{uid}/media", {"media_type": "REELS", "video_url": url, "caption": r["cap"], "share_to_feed": True, "thumb_offset": REEL_THUMB_MS},
                            {"Authorization": "Bearer " + tok}, "POST"))
    except Exception as e:
        seen["igr_" + today] = {"t": now, "fail": fail + 1}
        raise RuntimeError(f"인스타 릴스 컨테이너 실패({fail + 1}/{IG_TRIES}) — " + ("다음 실행에 다시" if fail + 1 < IG_TRIES else "봇 채팅에 온 영상을 직접 올려줘") + f": {e!r} {getattr(e, 'body', '') or ''}")
    seen["igc_" + c["id"]] = {"t": now, "kind": "reel"}
    print("ig reel 컨테이너", today)


def ig_cards(seen):
    """인스타 하루 3번(10/11 진우 '인스타 업그레이드 1번'): 12시·18시(IG_SLOTS) 시간대 카드 + 21시 하루 카드(모아보기 때 만든 것).
    시간대 카드: 그 시각 첫 실행에 카드(JPEG)·번호 순서를 docs/cards/날짜_시에 만들고(워크플로가 커밋 -> 사이트 공개) 다음 실행에 사이트에 뜨면 인스타 컨테이너
    -> 사이트 맨 위 카드 기록(ig_live, 사이트 먼저) -> 다음 실행에 ig_publish가 발행. 그 시각 IG_LATE시간 안에만, 딜 IG_MIN개 미만이면 건너뜀, 회차마다 1번
    (기록에 있으면 seen을 잃어도 다시 안 올림). 컨테이너 만들기 실패는 IG_TRIES번까지 다음 실행에 다시, 마지막엔 카드 주소와 함께 알림(main).
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
            ct = toss_list([p for _, p in order[:CARD_N]])
            cards.make([{"title": list_name(p, ct, True), "unit": p.get("unit")} for _, p in order], f"{kst.tm_mon}월 {kst.tm_mday}일", jpg,
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


def th_post(tok, text, link=None, image=None, tag="핫딜"):
    """Threads 글 1개: image = 사진 글(30초 처리 대기), link = 링크 미리보기(th_text), 둘 다 없으면 글만."""
    me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
    if link and not image:
        return th_text(tok, me, text, link)
    q = urllib.parse.urlencode({"media_type": "IMAGE" if image else "TEXT", **({"image_url": image} if image else {}), "text": text[:500], "topic_tag": tag, "access_token": tok})
    cid = json.loads(http(f"{THREADS}/{me}/threads?{q}", method="POST"))["id"]
    time.sleep(30 if image else 10)  # 미디어 처리 대기 (공식 권장값)
    return th_ok(json.loads(http(f"{THREADS}/{me}/threads_publish?creation_id={cid}&access_token={tok}", method="POST")))


def th_bundle(seen, kind, text, link=None, image=None):
    """묶음 글 Threads(12·18시 리스트·토스 베스트 리스트·21시 카드·22시 미리보기 — 10/12 진우 '묶음 글은 반드시'): 실패하면 다음 실행에 1번 더(th_retry), 예외는 그대로(main 알림)."""
    try:
        return th_post(E.get("THREADS_TOKEN"), text, link, image)
    except Exception:
        seen.setdefault(time.strftime("thretry_%Y%m%d_", time.gmtime(time.time() + 9 * 3600)) + kind, {"t": time.time(), "text": text, "link": link, "img": image})
        raise


def th_reply(tok, to, text):
    """Threads 댓글(타래) 1개: 글·댓글 to에 reply_to_id로 이어 붙임(링크 첨부 X) -> 새 댓글 id."""
    me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
    q = urllib.parse.urlencode({"media_type": "TEXT", "text": text[:500], "reply_to_id": to, "access_token": tok})
    cid = json.loads(http(f"{THREADS}/{me}/threads?{q}", method="POST"))["id"]
    time.sleep(10)
    return th_ok(json.loads(http(f"{THREADS}/{me}/threads_publish?creation_id={cid}&access_token={tok}", method="POST")))["id"]


def th_poll(tok, text, opts):
    """Threads 투표 글 1개(TEXT + poll_attachment, 공식 문서 create-posts/polls: 보기 2~4개·1~25자, 글만 있는 글에만) -> 글 id. 보기가 규칙 밖이면 안 올림(ValueError)."""
    if not 2 <= len(opts) <= 4 or not all(1 <= len(o) <= 25 for o in opts):
        raise ValueError(f"투표 보기는 2~4개·1~25자: {opts}")
    me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
    q = urllib.parse.urlencode({"media_type": "TEXT", "text": text[:500], "topic_tag": "핫딜", "access_token": tok})
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


def th_retry(seen):
    """실패한 묶음 글 Threads를 같은 날 다음 실행에 1번만 더."""
    tok, today = E.get("THREADS_TOKEN"), time.strftime("thretry_%Y%m%d_", time.gmtime(time.time() + 9 * 3600))
    for k in [k for k, v in seen.items() if k.startswith("thretry_") and isinstance(v, dict) and not v.get("done")]:
        seen[k]["done"] = 1
        if tok and k.startswith(today):
            th_post(tok, seen[k]["text"], seen[k].get("link"), seen[k].get("img"))
    for k in [k for k in seen if k.startswith("thabq_")]:  # A/B 시험 B 글의 링크 댓글이 실패했던 것 -> 1번만 더(안 되면 알림, 그 뒤엔 안 함)
        v = seen.pop(k)
        try:
            rid = th_reply(tok, v["id"], v["text"])
            seen.get("thab", {}).get("m", {}).get(v["id"], {})["r"] = rid
        except Exception as e:
            alert(seen, f"alert_thab2_{v['id']}", f"⚠️ Threads 링크 댓글 2번째도 실패: {err_brief(e)}\n링크 없는 딜 글이 남았어요 — 직접 첫 댓글로 달거나 글을 지워 주세요\n{v['text']}")


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
    if th_weak(plain):
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
    if any(p.get("own") and not p.get("th") and p["t"] >= max(since, today) and aff(p.get("url")) and not th_weak(p["text"]) and th_beauty(title_of(p["text"])) for p in load(POSTS, [])):
        return True
    return any(e["at"].startswith(today) and (e.get("api") or (e.get("deal") and aff(e.get("url")))) and not th_weak(plain_of(e.get("text") or ""))
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


def th_queue(seen, text, link, bt):
    """슬롯 방식에서 토스 이름 예약·15·19시 뷰티 회차 개별 글은 바로 안 올리고 줄에 — threads_deals가 슬롯에 채널 딜과 같이 1순위를 고름(3시간 지나면 버림)."""
    now = time.time()
    seen["thq"] = {"t": now, "q": [x for x in seen.get("thq", {}).get("q", []) if now - x["t"] < 3 * 3600] + [{"t": now, "text": text, "link": link, "bt": bt}]}


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
    fresh = [i for i, p in enumerate(posts) if not p.get("th") and p["t"] >= since and not p["text"].startswith("📋")]
    skip = [i for i in fresh if not aff_note(posts[i].get("url") or "")]  # 10/19 밤 진우 'Threads는 수수료 딜만': 대가성 문구가 붙는 링크만 — 나머지는 텔레그램·사이트에만(나중에 진우 링크로 바뀌면 그때 후보)
    new = [i for i in skip if "th" not in posts[i]] if tok else []  # 로그는 딜마다 1번(th = 0: 거짓값이라 리스트 셈은 그대로)
    for i in new:
        print("threads skip (수수료 링크 아님)", clip(title_of(posts[i]["text"]), 40), "|", link_kind(posts[i].get("url")))
        posts[i]["th"] = 0
    if new:
        json.dump(posts, open(POSTS, "w"), ensure_ascii=False)
    fresh = [i for i in fresh if i not in skip]
    rei = {i for i in fresh if posts[i].get("own") and posts[i].get("url") in {e["url"] for e in load(EVENTS, []) if e.get("re") and e.get("url")}}  # 10/12 23:05 진우 재업로드(events "re": true, 같은 진우 링크로 전에 나간 강점 품목)
    bt = {i: 0 if i in rei else th_beauty(title_of(posts[i]["text"])) for i in fresh}  # 재업로드는 화장품 하루 한도에서 뺌(밤 화장품 글이 한도를 채워도 막히지 않게)
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
        tq = [] if rw else [x for x in seen.get("thtoss", {}).get("q", []) if (TH_SOLO_GAP if x.get("l") else 0) <= now - x["t"] < 3 * 3600 and x["id"] not in gone and th_solo(seen, x["text"], beauty=x["bt"], top=True)]
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
          "· 3시간 지난 ①②(리스트로)", sum(p["t"].startswith(today) and p["t"] < since and not p.get("th") and th_tier(p["text"]) > 0 for p in posts),
          "· 토스 픽 대기", sum(now - x["t"] < 3 * 3600 for x in seen.get("thtoss", {}).get("q", [])), "· 수수료 링크 아님", len(skip))))
    print(RUN["th_why"])
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
            th_deal(seen, tok, me, i["text"], i["link"])
            continue
        url = th_url(posts[i], i)  # 10/19 진우 '직접 링크로': 텔레그램 버튼과 같은 링크(아주 긴 주소만 사이트 딜 페이지 — 그땐 사이트에 올라온 뒤에)
        if url.startswith(SITE):
            try:
                http(url, method="HEAD")
            except Exception:
                return
        note = aff_note(posts[i].get("url") or "")
        icon = "👍" if th_steady(posts[i]["text"]) else "🛒" if th_weak(posts[i]["text"]) else "🔥"  # 채널 글과 같게(약한 딜에 🔥 안 붙임)
        ls = posts[i]["text"].split("\n")
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
        th_deal(seen, tok, me, text, url, full)


WEATHER_HOUR, SNACK_HOUR, DAILY_LOG_HOUR, WEATHER_DM = (7, 30), (15, 30), (20, 30), (6, 20)  # 10/15 23:40 진우 '계절·날씨 맞춰 추천·간식·일상': 아침 날씨 글 · 간식 3 · 운영 일지(Threads) · 일요일(요일 6) 20시 시즌 키워드 DM. None = 끔
WEATHER_LAT, WEATHER_LON, WEATHER_BONUS, WX_LATE = 37.57, 126.98, 5, 2 * 3600  # 서울(Open-Meteo, 키 없음) · 오늘 날씨 키워드에 맞는 딜 가점(TOP5·Threads 개별 = 동점일 때만 먼저 — 🔥·30일 최저가 순서는 그대로, 0 = 끔) · 그 시각 뒤 2시간 안에만
POLL_HOUR, POLL_REUSE = (21, 40), 7  # 10/17 진우 '유입 늘리기 ① 가격 투표'(Threads만, 하루 1번): 최저가 기록 품목 투표(10/22~ Claude 반말 질문·보기 4개 — poll_ai) + 다음 날 같은 회차에 결과·기록 최저 답글, 같은 품목은 7일 뒤에. 10/22 진우 '저녁 9시대'(12:30 조회 2~6 vs 저녁 운영 일지 124~177): 21:40 = 21시 모아보기·22시 미리보기·묶음 간격 사이. None = 끔
POLL_KEYS = ("option_a", "option_b", "option_c", "option_d")  # Threads poll_attachment 보기(2~4개, 보기마다 1~25자 — 공식 문서 create-posts/polls)
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
    ok = lambda name: wx_hit(name, words) and not (deny and re.search(deny, name))
    for i, p in enumerate(posts):
        if p["t"] < since or p["text"].startswith("📋") or is_toss(p.get("url"), p["text"]):  # 토스는 아래에서(지금 가격)
            continue
        title = title_of(p["text"])
        name, won = re.sub(r"\s*\((?=[^()]*(?:\d|무료|무배))[^()]*(?:원|/|무료|무배|배송)[^()]*\)\s*$", "", parse(title)[1]), price_won(title)  # '(21,920/무료)'·'(무료)' 같은 가격·배송 괄호만 이름에서 빼고 가격으로('(30개)'·'(1+1)'은 그대로)
        if ok(name):
            out.append({"n": name, "p": f"{won:,}원" if won else "", "u": p["url"] if aff(p.get("url")) else None, "i": i,
                        "hot": not th_weak(p["text"]), "top3": bool(shop_of(p)), "t": kst_ts(p["t"])})
    cand = {}
    for k, v in seen.items():
        if HAS_TOSS and k.startswith("sold_") and isinstance(v, dict) and now - v.get("t", 0) < 3 * 86400:
            for link, x in zip([v.get("url")] if v.get("k") == "ev" else [r[1] for r in v.get("rows", [])], v.get("it", [])):
                if not x[4] and link and ok(x[1]):
                    cand[x[0]] = {"n": x[1], "u": link, "hot": True, "top3": True, "t": v["t"], "toss": 1}
    try:
        got = cand and {x["tacaItemId"]: x for x in toss("/products/detail?tacaItemIds=" + ",".join(map(str, list(cand)[:30])))["items"]}
        out += [{**c, "p": f"{got[i]['displayPrice']:,}원"} for i, c in cand.items() if i in got and not got[i].get("isSoldOut")]
    except Exception as e:  # 토스 API가 안 되면 토스 딜만 빼고
        print("wx toss", repr(e))
    picked, names = [], set()
    for c in sorted(out, key=lambda c: (not c["top3"], not c["hot"], -c["t"])):
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
    rows = [f"{'🔥' if c['hot'] else '🛒'} " + (f'<a href="{esc(u)}">{esc(clip(c["n"], 40))}</a>' + (f" {esc(c['p'])}" if c["p"] else "") if html_text else f"{clip(c['n'], 30)} {c['p']}".rstrip() + f"\n👉 {u}")
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
- q = 질문 한 줄(40자 안팎), opts = 보기 정확히 4개(보기마다 25자 이하, 짧게).
- 반말·공감형('~요'로 끝나는 말 X). 마지막 보기는 가볍게 웃긴 것.
- 상품명·브랜드(신라면·삼다수·햇반 같은 것)·쇼핑몰·편의점 이름·링크·광고 문구 X, 과장(역대급·무조건·손해) X.
- {kind}"""
POLL_KIND = {  # 10/22 진우 시안 고름(반말·공감형 보기·마지막 보기는 가볍게 웃기게): 글마다 무작위 가 생활형 / 나 가격형
    "life": "유형: 생활형 — 이 품목을 쟁이는 스타일·떨어졌을 때 어떻게 하는지 같은 생활 질문, 가격(원) 숫자 X. 예: 라면 쟁이는 스타일 골라봐 / 박스째 쌓아둠 · 5개입 하나면 충분 · 땡길 때 편의점 직행 · 라면 끊음 (진짜임)",
    "price": "유형: 가격형 — '{unit} 얼마면 오 싸다 해?' 같은 질문, 가격 숫자는 {nums}만(다른 숫자 X). 예: {name} {unit}, 얼마면 \"오 싸다\" 해? / {a}이면 바로 삼 · {b}까진 OK · {c} 넘으면 고민 · 가격 안 보고 집음"}
POLL_BRANDS = (r"신라면|진라면|너구리|짜파게티|안성탕면|컵누들|사발면|농심|삼양|오뚜기|팔도|삼다수|아이시스|백산수|풀무원|크리넥스|깨끗한나라|모나리자|잘풀리는|"  # 기록 품목(PRICE_ITEMS) 브랜드
               r"퍼실|리큐|테크|피죤|맥심|모카\s*골드|화이트\s*골드|카누|베베숲|몽드드|햇반|엘라스틴|케라시스|GS25|세븐일레븐|이마트24|(?<![A-Za-z])CU(?![A-Za-z])")  # + 편의점(몰)
POLL_YO = r"(?<![필중주수소])요[?!.~ㅋㅎ\s]*$|죠[?!.~ㅋㅎ\s]*$|(?<![다아])니다[?!.~ㅋㅎ\s]*$"  # 투표 보기 = 끝에서만(‘요 정도면’·‘참치마요’는 반말)


def wons(s):
    """글 속 원 금액(숫자) — '5천원대' 5000 · '1만2천원' 12000 · '1,500원' 1500."""
    return {int(m[1].replace(",", "")) * {"만": 10000, "천": 1000, "": 1}[m[2]] + int(m[3] or 0) * 1000
            for m in re.finditer(r"(\d[\d,]*)\s*(만|천|)\s*(?:(\d+)\s*천)?\s*원", s)}


def poll_ai(rec):
    """10/22 진우 '재미있게': Claude가 반말 질문·보기 4개(글마다 무작위 가 생활형 / 나 가격형 — 가격 숫자는 poll_opts 구간 값만) -> (본문, 보기).
    검사(질문 60자·보기 4개 1~25자·끝이 ~요 X·몰·편의점·브랜드(POLL_BRANDS)·링크·광고·과장 X·없는 금액 X) 실패 -> 걸린 말을 알려 주고 1번 다시, 그래도면 지금 틀(poll_text).
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
            bad = [x for x in [f"질문 {len(q)}자" if len(q) > 60 else "", f"보기 {len(opts)}개" if len(opts) != 4 else "", *(f"'{o}' {len(o)}자" for o in opts if len(o) > 25),
                               why(q), *map(why, opts)] if x]
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
    now, recs = time.time(), price_records(load(POSTS, []))
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
    pid = th_poll(tok, *poll_ai(recs[k]))
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
    if ws and len(ws) > 1 and tg("sendMessage", chat_id=ADMIN, text=wx_dm_text(ws[1:8]), link_preview_options={"is_disabled": True}):
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
        seen[k] = {"t": time.time(), "text": cap, "img": f"{SITE}daily/{name}"}
        reply("📝 받았어요 — 사이트에 사진이 올라가면(15분쯤) Threads에 올릴게요")
    except Exception as e:
        print("daily in", repr(e))
        reply(f"⚠️ #일상 사진을 못 받았어요: {err_brief(e)} — 다시 보내줘")


def daily_post(seen):
    """#일상(daily_in)이 사이트에 올라가면(사진 주소 HEAD) Threads에 1번 — daily_text(사진 + 캡션 그대로, 대가성 문구·게시 시점 줄) + 진우에게 '올렸어요'.
    묶음 글 간격(busy, 시간당 상한 X) 같이 셈. 1시간 넘게 사이트에 안 뜨면 진우에게 알리고 그만."""
    tok, now = E.get("THREADS_TOKEN"), time.time()
    for k in [k for k in seen if k.startswith("dly_") and not seen[k].get("done")] if tok and not busy(seen, cap=False) else []:
        v = seen[k]
        try:
            http(v["img"], method="HEAD")
        except Exception:
            if now - v["t"] > 3600:
                v["done"] = now
                tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": int(k[4:])}, text="⚠️ 사이트에 사진이 안 떠서 Threads에 못 올렸어요 — 다시 보내줘")
            continue
        v["done"] = now  # 먼저 표시: 실패해도 두 번 안 올림(실패는 main 알림)
        th_post(tok, daily_text(v["text"]), image=v["img"], tag="일상")
        bundled(seen)
        tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": int(k[4:])}, text="✅ Threads에 올렸어요")
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
    last = max((p["t"] for p in load(POSTS, []) if not p["text"].startswith("📋")), default="")
    return last < time.strftime("%Y-%m-%d %H:%M", time.gmtime(now - GAP_FILL * 60 * (2 if time.gmtime(now).tm_hour < 8 else 1)))


ALERT_GAP, QUIET_TH, QUIET_EV = 3 * 3600, 2 * 3600, 20 * 60  # 10/13 01:50 진우 '업로드 안 되면 바로 알람': 같은 단계·오류 알림 간격 · Threads 글 없음(8~24시) · 예약 글 늦음
ALERT_STEPS = {"events": "텔레그램 예약 글", "preview": "22시 미리보기", "top_deals": "지금 살 만한 딜 리스트", "toss_deals": "토스 회차 글", "toss_picks": "토스 이름 예약 글", "toss_solo": "토스 자동 개별 글", "toss_wait": "토스 커뮤니티 딜(링크 찾은 뒤 게시)",
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


def th_ok(r):
    """Threads 글·댓글이 올라감 -> 이번 실행 기록(watch: '✅ 다시 올라감'·2시간 글 없음 감시)."""
    RUN["ok"].add("th")
    RUN["th_last"] = time.time()
    return r


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
    open(METRICS, "w", encoding="utf-8").write("{" + ",\n".join(f'{js(d)}: {{"at": {js(v["at"])}, "miss": {js(v["miss"])}, "rows": [\n' + ",\n".join(map(js, v["rows"])) + "]}"
                                                                 for d, v in sorted(m.items(), reverse=True)[:METRICS_KEEP]) + "}\n")  # 최신 날짜 맨 위 · 글 1개 = 1줄(보고가 읽기 쉽게)


def prod_cols(title, cat, links, ids, deal=None):
    """metrics 줄 상품 칸(10/22 Cowork — 어떤 상품 글이 잘 됐는지 잇기): kind = deal(상품 1개 글)·list(묶음·목록 = urls)·etc(투표·날씨·#일상·미리보기 등),
    url·name(상품명) · tid = 토스 상품 id(우리가 만든 쉐어링크 — 쉐어링크는 만들 때마다 주소가 달라 상품은 id로 묶음).
    deal = True(Threads 개별 딜 글 — th_deal 기록, B 글은 링크를 못 읽어도 이름으로) / False(개별 딜 아님) / None(모름 = 링크 수로). 사이트 첫 화면·블로그·골드박스·쿠팡 홈 링크는 상품 X."""
    junk = lambda u: re.search(NOT_PROD, u) or u.startswith((BLOG, GOLDBOX, CP_HOME, CP_FRESH)) or u.startswith(SITE) and "/p/" not in u
    ls = [u for u in dict.fromkeys(links) if u and not junk(u)]
    kind = "deal" if deal else "etc" if cat in ("투표", "날씨") or not ls else "list" if cat == "묶음" or len(ls) > 1 else "etc" if deal is False else "deal"
    if kind == "etc":
        return {"kind": kind}
    if kind == "list":
        return {"kind": kind, "name": clip(title, 40), "urls": ls}
    return {"kind": kind, "name": parse(title)[1], **({"url": ls[0], **({"tid": ids[ls[0]]} if ls[0] in ids else {})} if ls else {})}


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
        cat = "투표" if text.startswith("🗳️") else "날씨" if re.search(r"^☁️", text, re.M) else "묶음" if re.search(r"2️⃣|^2\. ", text, re.M) else next((n.split()[-1] for _, n, rx in CATS if re.search(rx, title)), "식품" if re.search(FOOD, title) else "기타")
        rows.append({"date": day, "ch": ch, "id": i, "shop": shop_of({"text": text, "url": url}) or "기타", "cat": cat,
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
                        links=[p and p.get("url")] + [html.unescape(u) for u in re.findall(r'inline_button url_button" href="([^"]+)"', b) + re.findall(r'href="([^"]+)"', tx[1] if tx else "")])  # 버튼·본문 링크(목록 = 상품 여러 개)
            url = bs and bs[0][1] >= t0 and f"{CHANNEL_WEB}?before={bs[0][0]}"
    except Exception as e:  # 막히면 그 칸만 비움(다른 채널은 계속)
        miss["tg"] = "채널 웹 못 읽음: " + blame(e)
    if not rows:
        miss.setdefault("tg", "채널 웹에서 그날 글 0개(페이지 모양 바뀜?)")

    tok, ths = E.get("THREADS_TOKEN"), []
    if not tok:
        miss["th"] = "THREADS_TOKEN 없음"
    try:
        url = tok and f"{THREADS}/me/threads?fields=id,text,timestamp&since={int(t0)}&until={int(min(t0 + 86400, now))}&limit=100&access_token={tok}"
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
            title=ab.get("n"), links=[ab.get("u")] + re.findall(r"https?://[^\s<>\"]+", x.get("text") or ""), deal=bool(ab) or (False if day >= TH_AB_START else None), likes=ins.get("likes"), replies=ins.get("replies"), **({"ab": ab["ab"], "lk": link_kind(ab.get("u"))} if ab else {}), **({"rv": rv} if ab.get("r") else {}), **({"v": ab["v"]} if ab.get("v") else {}))  # lk = 링크 종류(10/19~ 직접 링크 — 10/25 비교는 바뀐 뒤 글끼리)

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
                v = json.loads(http(f"{IG}/{x['id']}/insights?metric=views", None, h))["data"][0]["values"][0]["value"]
            except Exception as e:
                why = blame(e)
                if denied(e):
                    miss["ig"] = "조회수 권한 없음(토큰 권한 instagram_business_manage_insights 확인): " + why
                else:
                    miss.setdefault("ig_part", "일부 글 조회수 못 읽음: " + why)
        lk, cm = x.get("like_count"), x.get("comments_count")
        row("ig", x["id"], x.get("caption") or "", "", stamp(x["timestamp"]), v, None if lk is None else lk + (cm or 0), likes=lk, replies=cm)

    rows.sort(key=lambda r: (("tg", "th", "ig").index(r["ch"]), r["at"]))  # 채널별 시각 순(채널 웹은 쪽 순서로 읽힘)
    m = load(METRICS, {})
    m[day] = {"at": time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 9 * 3600)), "miss": miss, "rows": rows}
    metrics_save(m)
    if not E.get("METRICS_DAY") and (not any(soft) or time.gmtime(now + 9 * 3600).tm_hour >= 8):  # 수동 실행(오늘치 점검 등)은 기록 X -> 다음 날 5시에 그날 전체를 다시
        seen["mt_" + day] = now
    c = collections.Counter(r["ch"] for r in rows)
    print(f"metrics {day}: " + " · ".join(f"{ch} {c[ch]}개 빈 칸 {sum(r['views'] is None or r['react'] is None for r in rows if r['ch'] == ch)}" for ch in ("tg", "th", "ig")), miss or "")


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
            if not any(links) and r.get("ab") == "B" and not no_rep:  # B = 본문에 주소 없음, 첫 댓글 = 링크
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
    sv, rp = (lambda r: r.get("v48") or r.get("views") or 0), (lambda r: max(0, (r.get("replies") or 0) - (r.get("ab") == "B")))  # B 글 답글 = 우리 링크 댓글 1개 빼고
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
        wait = sum(not p.get("th") and p["t"] >= since and not p["text"].startswith("📋") and not th_weak(p["text"]) and aff(p.get("url")) for p in posts) \
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
            why = RUN["tg_err"] or "events 로그 확인"
        tg("sendMessage", chat_id=ADMIN, text=f"⏸ 텔레그램 예약 글 안 나감 — {at[5:]} {clip(ev.get('name') or plain_of(ev.get('text') or '').split(chr(10))[0], 40)} (예약 + {QUIET_EV // 60}분 지남), 이유: {why}")
        seen[f"quietev_{at}"] = {"t": now}


def main():
    RUN.update(ok=set(), fail={}, failch=set(), th_last=0, th_why="", tg_err="", ch_last=0, treuse=False)
    if TOSS_NO_CMP:
        toss_clean_posts()
    seen = load(SEEN, {})
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
    if new:
        since = time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - 86400))
        recent = [title_of(p["text"]) for p in load(POSTS, []) if p["t"] >= since and not p["text"].startswith("📋")][-30:]
        recent += [v["n"] for k, v in seen.items() if k.startswith("tb_") and isinstance(v, dict) and v["t"] > time.time() - 86400]  # 토스 하루특가·베스트 글(posts.json엔 없음)도 — 10/10 케라시스 베스트 10:02 → 같은 딜 10:44
        prompt = DEAL_PROMPT + ("\n최근 24시간에 이미 올린 딜(같은 상품이면 고르지 마):\n" + "\n".join(recent) if recent else "")
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
        good = sorted(({"d": new[p["i"]], "p": {k: v for k, v in p.items() if k != "i"}} for p in good), key=rank)
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
        post_or_draft(h["d"], p["comment"], p["score"], p.get("q"), {k: p.get(k) for k in ("e", "hook", "pts", "unit", "warn", "who", "use")})
    for h in good[max(0, MAX_DRAFTS - len(held)):]:  # 넘친 좋은 딜은 다음 실행에 다시 묻지 않고 올리게 보관
        seen["hold_" + h["d"]["id"]] = {"t": time.time(), **h}
    for step in (events, preview, playlist, goldbox, lambda s: cp_events(s, deals), top_deals, weather_post, snack_post, poll_post, toss_deals, lambda s: toss_deals(s, True), lambda s: toss_deals(s, "cat"), lambda s: toss_deals(s, "beauty"), lambda s: toss_deals(s, "special"), toss_wait, toss_relink, toss_picks, toss_solo, toss_soldout, toss_fix_channel, lambda s: digest(s, load(POSTS, [])), threads, threads_deals, daily_post, daily_log, wx_dm, toss_reopen, ig_cards, ig_reel, ig_repost, ig_publish, toss_stock, coupang_remind, oy_claim, report, th_retry, cmp_report, th_reply_ok, metrics):
        try:
            step(seen)
        except Exception as e:
            print(step.__name__, repr(e))
            step_alert(seen, step, e)  # 10/13 진우 '업로드 안 되면 바로 알람': 하루 1번 -> 바로(같은 단계·같은 오류는 3시간에 1번), Threads·인스타 + 채널 글 단계(ALERT_STEPS)
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
