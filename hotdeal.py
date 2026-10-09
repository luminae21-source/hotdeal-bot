#!/usr/bin/env python3
"""핫딜봇: 뽐뿌·루리웹·클리앙 핫딜 -> Claude 선별/코멘트 -> 채널 바로 게시.
상품 주소가 있으면(루리웹·클리앙 글) 링크프라이스 승인 몰은 상품 페이지 제휴 링크 자동, 없으면(뽐뿌: GitHub IP 차단) 검색 제휴 링크.
쿠팡·네이버 등 수동 몰은 관리자에게 사본(+쿠팡은 파트너스 검색 버튼, 네이버는 상품명 복사·쇼핑커넥트 버튼, 그 외 상품 열기 버튼) -> 제휴 링크를 답장(또는 그냥 전송)하면 채널 글 교체. 쿠팡 골드박스는 매일 7시 이후 1번 채널에 바로(키 없으면 골드박스 링크, 있으면 TOP5).
GitHub Actions에서 15분마다 실행(tick.yml 타이머가 workflow_dispatch로 실행 + 예약 보조). 외부 패키지 없음(파이썬 표준 라이브러리만)."""
import base64, hashlib, hmac, html, json, os, re, tempfile, time, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from build_site import BASE as SITE, BLOG, GOLDBOX, NOTE_STARTS, title_of, split_title, parse, react, TOSS_HOSTS, NAVER_HOSTS, AFF_HOSTS, OY_HOSTS, toss_share, day_deals, card_order  # 제휴 도메인은 사이트와 같이 씀

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
CP_SEARCH = "https://partners.coupang.com/#affiliate/ws/link/0/"  # 파트너스 '상품 링크' 검색 결과를 바로 여는 주소(10/6 확인: 새로 열어도 검색됨, 상품 주소로는 검색 안 됨)
NAVER_SC = "https://brandconnect.naver.com/1003150047355424/affiliate/products"  # 쇼핑커넥트 상품 찾기(진우 스페이스, 로그인 필요). 봇 자동 발급은 네이버 정책상 금지(7/9 공지: 매크로 감지 시 7일 발급 제한)
LP_API = "https://api.linkprice.com/ci/service/custom_link_xml?a_id={}&mode=json&url={}"  # 링크프라이스 딥링크 API: 승인된 몰이면 S + 링크, 아니면 F(승인거부·유효하지 않은 URL)
LP_HOSTS = {"gmarket.co.kr": "gmarket", "auction.co.kr": "auction", "lotteon.com": "lotteon", "emart.ssg.com": "emart"}  # API 장애 때만 쓰는 승인 몰 목록(직접 딥링크)
HOST_STORES = {"coupang.com": "쿠팡", "naver.com": "네이버", "toss.im": "토스", "toss.shopping": "토스", "11st.co.kr": "11번가",
               "aliexpress": "알리", "auction.co.kr": "옥션", "emart.ssg.com": "이마트", "e-himart.co.kr": "하이마트", "ohou.se": "오늘의집", "oliveyoung.co.kr": "올리브영"}  # 제목에 [쇼핑몰]이 없을 때(클리앙) 주소로 몰 판단
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
esc = html.escape

REEL_RULES = """e: 상품을 한눈에 보여줄 이모지 1개 (예: 🥛 🍠 🧻 🔋 👟).
hook: 릴스 첫 화면 한 줄, 14자 이내, 숫자 중심(개당·100g당 같은 단위가격이나 핵심 혜택). 예: "우유 팩당 495원". 계산은 제목·본문의 가격과 수량으로만.
pts: 합리적인 소비인 이유 2~3개, 각 14자 이내, 사실만(할인 조건·용량·보관·구성). 배송비·단위가격은 따로 표시되니 빼고, 평소가·최저가·역대가는 글에 나온 경우만.
unit: 단위가격 한 줄(예: "100g당 990원", "개당 495원", "1L당 1,980원"). 제목·본문의 가격과 수량으로 확실히 계산될 때만, 아니면 빈 문자열.
warn: 사기 전에 확인할 점 1개, 16자 이내(예: "쿠폰 1인 1회", "옵션별 가격 다름", "카드할인 적용가"). 글에 근거 있을 때만, 없으면 빈 문자열."""
DEAL_PROMPT = """너는 한국 핫딜 텔레그램 채널 편집자야. 아래 딜 중 구독자가 실제로 살 만한 것만 골라 pick 도구로 반환해.
점수(1~10) 기준: 가격 매력, 생필품/대중성, 커뮤니티 반응(조회 대비 추천·댓글). 비추천이 많거나 품절·종료·가격오류 언급이 있으면 제외.
comment: 구독자용 1~2줄. 핵심 조건(쿠폰·카드할인·무배 등)을 사실대로. 과장 금지, 확인 안 된 '역대최저' 금지, 건강식품 효능 언급 금지, 이모지 최대 1개.
[올리브영] 딜 comment는 가격·용량·구성·조건만: 후기·체험담·글쓴이 경험, '추천'·'좋아요'·'쟁여두기' 같은 권유, 효능·효과, '최고'·'100%' 같은 절대 표현 금지(올리브영 쇼핑 큐레이터 정책).
q: 쇼핑몰 검색창에 넣을 짧은 검색어(브랜드+상품명+핵심 용량, 수량·가격·쿠폰 문구 빼고 20자 안팎).
REEL_RULES
같은 상품이 여러 커뮤니티([뽐뿌]·[루리웹]·[클리앙])에 올라왔으면 하나만 골라.
5점 미만은 반환하지 마.
"""
DEAL_PROMPT = DEAL_PROMPT.replace("REEL_RULES", REEL_RULES)
REEL_PROMPT = "아래 딜 각각(모든 i)에 대해 인스타 릴스용 정보를 pick 도구로 반환해. score는 0, comment는 빈 문자열.\n" + REEL_RULES + "\n"
GOLD_PROMPT = """쿠팡 골드박스(오늘 하루 특가) 목록이야. 할인율은 정가를 부풀린 경우가 많으니 믿지 말고 구성·단위가격으로 판단해서,
대중적이고 '지금 사도 싸다' 싶은 상품만 최대 5개 pick 도구로 반환해. 억지로 5개 채우지 말고, 없으면 빈 목록 (10/7 진우: 살 만한 제품만).
comment: 1줄, 사실 위주, 과장 금지, 건강식품 효능 언급 금지.
"""
BEST_PROMPT = """토스쇼핑에서 지금 많이 팔리는 상품 목록이야(가격 = 배송비 포함 결제가). 많이 팔린다고 싼 건 아니고 할인율은 정가를 부풀린 경우가 많으니
믿지 말고 구성·단위가격·리뷰로 판단해서, 대중적이고 '지금 사도 싸다' 싶은 것만 최대 3개 pick 도구로 반환해. 없으면 빈 목록.
comment: 1줄, 단위가격 등 사실 위주, 과장 금지, 건강식품 효능 언급 금지.
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
TOP_HOURS = (12, 18)  # 커뮤니티 반응 좋은 딜 TOP5 묶음 글(10/9 진우 '사람들이 사는 제품을 보기 좋고 사고 싶게') — top_deals()
NUM = "1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣".split()
TOSS_BEST_HOURS = (10, 12, 14, 16, 18, 20)  # 토스 '지금 많이 팔리는 상품'(1시간마다 갱신) 중 Claude가 살 만한 것만: 10~20시 2시간마다 (10/7 진우 제안 2번 -> 10/8 3번 -> 10/9 '쿠팡·토스 주력' 6번)
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
    if method == "sendMessage" and len(text) > 4096 and "reply_markup" not in params:  # 텔레그램 4096자 제한(10/6 블로그용 글 실패) -> 문단 단위로 나눠 보냄. 버튼 달린 초안은 안 나눔
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
    > 상품 페이지(제휴 없음, 관리자 사본으로 수동) > 원글. 제휴 링크면 대가성 문구를 맨 앞에.
    extra의 unit(단위가격)·warn(확인할 점)이 있으면 코멘트 아래 한 줄씩 (다른 핫딜 채널과의 차이: 비교 근거 + 단점까지)."""
    link, aff = affiliate(store_link(d["url"]))
    label = "🛒 구매하러 가기"
    if not aff:
        lp, name = lp_search(d["title"], q)
        if lp:
            link, label = lp, f"🔎 {name}에서 찾기"
    note = aff_note(link or "")
    head = f"<i>{note}</i>\n\n" if note else ""  # 공정위 지침: 대가성 문구는 첫 부분에
    x = extra or {}
    facts = "".join(f"\n{icon} {esc(x[k])}" for k, icon in (("unit", "💡 단위가격"), ("warn", "⚠️ 확인할 점")) if x.get(k))
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


def with_note(text, ents, url):
    """제휴 링크면 대가성 문구를 맨 앞에 붙인 (text, entities). 텔레그램 오프셋은 UTF-16 단위라 그만큼 뒤로 밂."""
    note = aff_note(url)
    if note and not text.startswith(NOTE_STARTS):
        n = len(note.encode("utf-16-le")) // 2
        return f"{note}\n\n{text}", [{"type": "italic", "offset": 0, "length": n}] + [{**e, "offset": e["offset"] + n + 2} for e in ents]
    return text, ents


def relink_channel(notice, mid, url):
    """이미 올라간 채널 글(mid)의 버튼을 url로 교체 + 대가성 문구. 관리자 사본과 posts.json도 같이 고침."""
    text, ents = with_note(notice.get("text", ""), notice.get("entities", []), url)
    kb = [[{"text": "🛒 구매하러 가기", "url": url}]]
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


def relink(m, url):
    """초안 m의 구매 버튼을 url로 교체(제휴 링크면 대가성 문구를 맨 앞에) -> (text, entities, 버튼 rows)."""
    text, ents = with_note(m.get("text", ""), m.get("entities", []), url)
    rows = [[{"text": "🛒 구매하러 가기", "url": url}]]
    rest = [r for r in m.get("reply_markup", {}).get("inline_keyboard", []) if "url" not in r[0]] or \
        [[{"text": "✅ 게시", "callback_data": "ok"}, {"text": "❌ 패스", "callback_data": "no"}]]
    tg("editMessageText", chat_id=m["chat"]["id"], message_id=m["message_id"], text=text, entities=ents,
       link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": rows + rest})
    return text, ents, rows


def publish_approved():
    """관리자 입력 처리. 텔레그램이 입력을 24시간 보관하므로 15분 주기로 충분.
    1) 사본·초안에 링크로 답장 -> 구매 버튼 교체 (쿠팡·토스·네이버 링크는 답장 없이 링크만 보내도 가장 최근 같은 몰 사본)
    2) 봇에게 '제목 줄 + 링크' 새로 보내기 -> 그 딜 초안 생성
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
        url = re.search(r"https?://\S+", m.get("text", ""))
        if not url or str(m.get("from", {}).get("id")) != ADMIN:
            continue
        if m.get("reply_to_message"):
            rm = m["reply_to_message"]
            ch = next((b["url"] for r in rm.get("reply_markup", {}).get("inline_keyboard", []) for b in r
                       if b.get("url", "").startswith("https://t.me/")), None)
            if ch:  # 채널에 이미 올라간 글의 사본 -> 채널 글 교체
                relink_channel(rm, int(ch.rsplit("/", 1)[1]), url.group(0))
            else:   # 아직 초안 -> 초안 버튼 교체(✅ 때 반영)
                fixed[rm["message_id"]] = relink(rm, url.group(0))
            continue
        lines = [l.strip().lstrip("🔥").strip() for l in m["text"].replace(url.group(0), "").split("\n")]
        lines = [l for l in lines if l and not l.startswith(NOTE_STARTS)]  # 붙여넣은 대가성 문구는 빼고 링크 기준으로 다시 붙임
        p = None if lines else pending_copy(url.group(0))
        if p:  # 링크만 보냄 -> 가장 최근 같은 몰 사본의 채널 글 교체 (사본에 '✅ 채널 글 교체됨' 표시로 어느 글인지 보임)
            relink_channel({"chat": {"id": ADMIN}, "message_id": p["cp"], "text": p["text"], "entities": p["entities"]}, p["mid"], url.group(0))
            continue
        if not lines:
            tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": m["message_id"]},
               text="첫 줄에 제목을 같이 보내줘. 예)\n[G마켓] 상품명 (39,910원/무료)\n한 줄 코멘트\n링크")
            continue
        note, body = aff_note(url.group(0)), "\n".join(lines[1:])
        draft((f"<i>{note}</i>\n\n" if note else "") + f"🔥 <b>{esc(lines[0])}</b>" + (f"\n\n{esc(body)}" if body else ""),
              url.group(0))
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
    """예약 게시: 시각이 됐고 6시간 안 지났으면 채널에 1번(제휴 링크면 그 대가성 문구 맨 앞). 놓친 지 오래된 글은 안 올림(식은 글)."""
    kst = lambda h: time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + h * 3600))
    for ev in load(EVENTS, []):
        key = "ev_" + ev["at"]
        if key in seen or not (kst(9 - 6) <= ev["at"] <= kst(9)):
            continue
        note = aff_note(ev["url"])
        if tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True},
              text=(f"<i>{note}</i>\n\n" if note else "") + ev["text"], reply_markup={"inline_keyboard": [[{"text": ev["button"], "url": ev["url"]}]]}):
            seen[key] = time.time()


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
    kst, cat = time.gmtime(time.time() + 9 * 3600), best == "cat"
    hrs = [h for h in ((TOSS_CAT_HOUR,) if cat else TOSS_BEST_HOURS if best else (9,)) if h <= kst.tm_hour]
    key = time.strftime("tosscat_%Y%m%d_" if cat else "tossbest_%Y%m%d_" if best else "tossday_%Y%m%d", kst) + (str(hrs[-1]) if best and hrs else "")
    if not HAS_TOSS or not hrs or key in seen:
        return
    head = "🏆 <b>토스에서 지금 많이 팔리는 것 중 살 만한 {}개</b>" if best else "⏰ <b>오늘의 토스 하루특가 TOP{}</b>"
    if cat:  # 카테고리 ID는 트리에서 이름으로 찾음(트리 조회는 일 상한 차감 없음)
        tree = toss("/categories")["categories"]
        cats = [c for c in tree if c["displayName"] in TOSS_CATS]
        if not cats:
            raise RuntimeError(f"토스 카테고리 이름 확인: {[c['displayName'] for c in tree]}")
        others = [c for c in tree if c["displayName"] not in TOSS_CATS]  # 10/8 진우 '더 넓게': 다른 최상위 카테고리를 날마다 1개씩 돌아가며
        cats += [others[kst.tm_yday % len(others)]] if others else []
        ids = [c["categoryId"] for c in cats]
        head = "🧺 <b>토스 " + "·".join(c["displayName"] for c in cats) + " 베스트 중 살 만한 {}개</b>"
        raw = [x for i in ids for x in toss(f"/products/best-categories/{i}?size=30")["items"]]
    else:
        raw = toss(f"/products/{'best-selling' if best else 'today-deals'}?size=30")["items"]
    items = list({x["tacaItemId"]: x for x in raw if not x.get("isSoldOut") and f"tb_{x['tacaItemId']}" not in seen}.values())  # 카테고리 겹친 상품은 1번만
    picks = items and ai_pick(BEST_PROMPT if best else GOLD_PROMPT.replace("쿠팡 골드박스", "토스쇼핑 하루특가"),
                              [f"{x['displayName']} | {x['displayPrice']:,}원 ({x.get('discountRate', 0)}% 할인)"
                               + (f" | 리뷰 {x.get('reviewScore')}점 {x['reviewCount']:,}개" if x.get("reviewCount") else "") for x in items])[:3 if best else 5]
    rows, plain = [], []
    for p in picks or []:
        x = items[p["i"]]
        try:
            link = toss("/links", {"tacaItemId": x["tacaItemId"], "publisherId": E["TOSS_PUBLISHER_ID"]})["shortUrl"]
        except Exception as e:  # 발급 제한 상품은 빼고 나머지만
            print("toss link", repr(e))
            continue
        seen[f"tb_{x['tacaItemId']}"] = time.time()  # 올린 상품은 3일(seen 보관 기간) 안엔 베스트에 다시 안 올림 (베스트는 며칠씩 그대로, 하루특가와도 겹침)
        plain.append(f"{NUM[len(plain)]} {clip(x['displayName'], 24)} — {x['displayPrice']:,}원\n{link}")
        rows.append((x["displayName"], link, [f"💰 <b>{x['displayPrice']:,}원</b>" + (f" ({x['discountRate']}%↓)" if x.get("discountRate") else "")
                                             + (f" · ⭐ {x['reviewScore']} (리뷰 {x['reviewCount']:,})" if x.get("reviewCount") else ""), "👉 " + esc(p["comment"])]))
    print("toss_cat" if cat else "toss_best" if best else "toss_deals", len(items), "items", len(picks or []), "picks", len(rows), "links")  # 0건이어도 로그로 확인
    if raw:  # 목록을 받았으면(Claude까지 돌렸으면) 이번 회차는 끝(발급이 다 막혀도 15분마다 다시 고르지 않게). Threads가 실패해도 채널에 두 번 안 올라가게 먼저 표시
        seen[key] = time.time()
    if rows:
        text, kb = top_post(head.format(len(rows)), rows)
        tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True},
           text=f"<i>{TOSS_NOTE}</i>\n\n{text}", reply_markup={"inline_keyboard": kb})
    tok = E.get("THREADS_TOKEN")
    if rows and tok:  # Threads 글자 수 500 -> 넘치면 뒤 상품부터 뺌. 대가성 문구는 토스 가이드대로 맨 앞(더보기 없이 보이게)
        while len(plain) > 1 and len(TOSS_NOTE) + 40 + len("\n\n".join(plain)) > 480:
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
    if not hrs or key in seen:
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
    tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True},
       text=(notes + "\n\n" if notes else "") + text, reply_markup={"inline_keyboard": kb})


def toss_relink(seen):
    """쉐어링크가 없는 최근 3일 [토스] 채널 딜에 우리 쉐어링크를 붙여 채널 글 버튼을 교체(진우가 사본에 답장한 것과 같은 relink_channel — 대가성 문구·사본 '교체됨'·posts.json·사이트).
    ① 루리웹·클리앙 글 = 처음 1번 글의 상품 주소를 다시 읽어 발급(본문 링크 고치기 전 글·그때 실패한 글). 버튼이 토스 앱 공유 주소(service.toss.im)면 상품 주소로 풀어 발급.
    ② 그 외(뽐뿌는 서버 차단이라 상품 주소를 못 읽음) = 토스 API 목록(하루특가·최상위 카테고리별 베스트 100·베스트 100)에서 찾기 — 검색 API가 없어서 목록 대조:
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
    day, hour, got = time.strftime("%Y%m%d", time.gmtime(now)), time.strftime("%Y%m%d%H", time.gmtime(now)), []  # 9시(KST) = 0시(UTC) 갱신 -> UTC 날짜로 하루 1번
    if seen.get("tossget_cat", {}).get("d") != day:
        got += toss("/products/today-deals?size=30")["items"] + [x for c in toss("/categories")["categories"]
                                                                 for x in toss(f"/products/best-categories/{c['categoryId']}?size=100")["items"]]
        seen["tossget_cat"] = {"t": now, "d": day}
    if seen.get("tossget_best", {}).get("h") != hour:
        got += toss("/products/best-selling?size=100")["items"]
        seen["tossget_best"] = {"t": now, "h": hour}
    cache = {x[0]: x for x in seen.get("tosscache", {}).get("items", []) if x[3] > now - 86400}  # [id, 이름, 가격, 마지막으로 본 시각]. 1일(쉐어링크 FAQ: API 데이터 저장·캐싱은 가능한 한 1일 이내, 10/9)
    cache.update({x["tacaItemId"]: [x["tacaItemId"], x["displayName"], x["displayPrice"], now] for x in got})
    items = list(cache.values())
    seen["tosscache"] = {"t": now, "items": items}
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
        link = None
        if hit:
            r["done"] = True
            try:
                link = toss("/links", {"tacaItemId": hit[0], "publisherId": E["TOSS_PUBLISHER_ID"]})["shortUrl"]
            except Exception as e:  # 발급 제한 상품 -> 사본 답장으로
                print("toss link", repr(e))
        if link:
            relink_channel(notice, p["mid"], link)
        res = f"{hit[1][:40]} {hit[2]:,}원 (id {hit[0]}, {pick[0]['score']}점) | " + ("링크 교체" if link else "발급 실패") if hit else "없음"
        print("toss match", p["t"][5:], title[:40], "->", res, f"| {'' if first else '다시 · '}후보 {len(cand)}/{len(items)}")


def digest(seen, posts):
    """매일 21시(KST) 이후 1회: 오늘 게시한 딜 모아보기 초안 -> ✅ 누르면 채널 게시. 바로 뒤 블로그용 글(길면 나눠서, 실패하면 다음 실행에 다시)·카드·릴스."""
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
    rows = [f"{n}. <a href=\"{esc(f'{SITE}p/{posts.index(p)}.html' if aff_note(p['url'] or '') == OY_NOTE else p['url'])}\">{esc(title_of(p['text']))}</a>"  # 올영: 링크만 나열 금지(FAQ) -> 사이트
            for n, p in enumerate(todays, 1)]
    text = (f"📋 <b>오늘의 딜 모아보기 ({kst.tm_mon}/{kst.tm_mday})</b>\n\n" + "\n".join(rows)
            + f"\n\n🔎 지난 딜 전체 보기: {SITE}\n📝 블로그: {BLOG}\n📲 실시간 알림: https://t.me/hotdeal_pick")
    if draft(text):
        seen[key] = time.time()
        blog()
        import cards
        try:  # Threads/인스타용 카드 -> docs/cards/ (워크플로가 커밋 -> 사이트에 공개 -> 다음 실행 때 threads()가 올림)
            order = day_deals(posts, today)
            os.makedirs("docs/cards", exist_ok=True)
            json.dump([i for i, _ in order], open(f"docs/cards/{today}.json", "w"))  # 카드 번호 순서를 고정(사이트·캡션이 같이 씀)
            cards.make([{"title": title_of(p["text"]), "unit": p.get("unit")} for _, p in order], f"{kst.tm_mon}월 {kst.tm_mday}일", f"docs/cards/{today}.png")
        except Exception as e:
            print("card", repr(e))
        try:  # 인스타 릴스용 15초 영상 -> 관리자에게 바로 전송 (저장소엔 안 올림). 점수 높은 순 TOP3
            top = [p for _, p in card_order(posts, today)][:3]  # 카드와 같은 순서(점수, 같으면 제휴 딜 먼저)
            need = [p for p in top if not (p.get("hook") and p.get("pts"))]  # ✅로 올린 글·예전 글은 릴스 재료가 없음 -> 여기서 채움
            if need:
                try:
                    for f in ai_pick(REEL_PROMPT, [f"{title_of(p['text'])} | {comment_of(p['text'])}" for p in need]):
                        need[f["i"]].update({k: f[k] for k in ("e", "hook", "pts", "unit", "warn") if f.get(k)})
                except Exception as e:
                    print("reel fill", repr(e))
            music, mus = bgm(kst), load(MUSIC, [])
            song = mus[kst.tm_yday % len(mus)] if music else None  # 캡션에 곡명(인스타에서도 무슨 곡인지 보이게)
            path = cards.reel([{"title": title_of(p["text"]), "comment": comment_of(p["text"]),
                                **{k: p.get(k) for k in ("e", "hook", "pts", "unit", "warn")}} for p in top], f"{kst.tm_mon}월 {kst.tm_mday}일",
                              os.path.join(tempfile.gettempdir(), f"reel_{today}.mp4"), music)
            cap = ((top[0].get("hook") + " · " if top[0].get("hook") else "") + f"{kst.tm_mon}월 {kst.tm_mday}일 가성비 TOP{len(top)}\n\n"
                   + "\n".join(f"{n}. {title_of(p['text'])}" for n, p in enumerate(top, 1))
                   + (f"\n\n🎵 {song['name']}" + (" (Pixabay)" if song.get("url") else "") if song else "")
                   + "\n\n🛒 구매: 프로필 링크(hotdealpick.kr) → 맨 위 오늘의 딜에서 바로\n일부 링크는 제휴 링크로 수수료를 받을 수 있어요."
                   + "\n\n#핫딜 #오늘의핫딜 #특가 #최저가 #살림템 #쇼핑정보")[:1024]
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


def ig_publish(seen):
    """올려둔 인스타 컨테이너(카드·릴스)가 처리 끝났으면(FINISHED) 발행. 처리 중이면 다음 실행에, 실패(ERROR·EXPIRED)면 알림(main)."""
    tok, uid = E.get("IG_TOKEN"), E.get("IG_USER_ID")
    if not (tok and uid):
        return
    for k in [k for k in seen if k.startswith("igc_")]:
        st = json.loads(http(f"{IG}/{k[4:]}?fields=status_code", headers={"Authorization": "Bearer " + tok}))["status_code"]
        if st == "IN_PROGRESS":
            continue
        seen.pop(k)
        if st != "FINISHED":
            raise RuntimeError(f"인스타 처리 실패({st}) — 오늘 카드·영상은 봇 채팅에 온 걸 직접 올려줘")
        json.loads(http(f"{IG}/{uid}/media_publish", {"creation_id": k[4:]}, {"Authorization": "Bearer " + tok}, "POST"))
        tg("sendMessage", chat_id=ADMIN, text="📸 인스타 자동 게시 완료 (instagram.com/hotdealpick.kr)")


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
        items.append(f"{n}. {t}\n{comment_of(p['text']).split(chr(10))[0]}\n👉 {p['url'] or SITE}")
    notes = "\n".join(n for n in dict.fromkeys(aff_note(p["url"] or "") for p in todays) if n in (OY_NOTE, NAVER_NOTE))  # 본문 맨 위 필수인 프로그램
    return (f"📝 블로그용 (제목·본문 그대로 복붙)\n\n제목: {title}\n\n" + (notes + "\n\n" if notes else "") + "\n\n".join(items)
            + f"\n\n더 많은 핫딜 👉 {SITE}\n실시간 알림 👉 https://t.me/hotdeal_pick\n\n"
            + "이 포스팅은 쿠팡 파트너스·토스쇼핑 쉐어링크 등 제휴 마케팅 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받을 수 있습니다.")


THREADS = "https://graph.threads.com/v1.0"  # 공식 문서 기준 도메인


def card_caption(day):
    """그날 카드의 (목록 줄 6개, 인스타 캡션). 목록 번호 = 카드·사이트 맨 위 번호. 가격은 카드 이미지에."""
    rows = [f"{n}. {clip(re.sub(PRICE_TAIL, '', title_of(p['text'])).strip(), 34)}" for n, (_, p) in enumerate(card_order(load(POSTS, []), day)[:6], 1)]
    return rows, (f"{int(day[5:7])}월 {int(day[8:])}일 오늘의 핫딜 모음\n\n" + "\n".join(rows)
                  + "\n\n🛒 구매: 프로필 링크(hotdealpick.kr) → 맨 위에서 카드 번호를 누르면 바로 구매 페이지\n일부 링크는 제휴 링크로 수수료를 받을 수 있어요."
                  + "\n\n#핫딜 #오늘의핫딜 #특가 #최저가 #살림템 #쇼핑정보")


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
    """오늘 카드가 사이트에 올라와 있으면 관리자에게 1회 보내고, IG_TOKEN 있으면 인스타(JPEG 카드, ig_publish가 발행), THREADS_TOKEN 있으면 Threads에도 게시.
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
    rows, cap = card_caption(today)
    if ig:  # 10/8 진우 '자동으로 올리게'. 컨테이너만 만들고 발행은 ig_publish(처리 끝나면)
        try:
            c = json.loads(http(f"{IG}/{E['IG_USER_ID']}/media", {"image_url": url[:-4] + ".jpg", "caption": cap}, {"Authorization": "Bearer " + E["IG_TOKEN"]}, "POST"))
            seen["igc_" + c["id"]] = time.time()
        except Exception as e:  # 인스타가 실패해도 Threads는 올림
            tg("sendMessage", chat_id=ADMIN, text=f"⚠️ 인스타 카드 게시 실패 — 위 카드 사진을 직접 올려줘: {e!r} {getattr(e, 'body', '')}"[:400])
    if not tok:
        return
    text = (f"📋 {kst.tm_mon}/{kst.tm_mday} 오늘의 핫딜 모음\n\n" + "\n".join(rows)
            + f"\n\n전체 딜·구매 링크 👉 {SITE}\n실시간 알림 👉 https://t.me/hotdeal_pick")[:480]
    me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
    q = urllib.parse.urlencode({"media_type": "IMAGE", "image_url": url, "text": text, "topic_tag": "핫딜", "access_token": tok})
    cid = json.loads(http(f"{THREADS}/{me}/threads?{q}", method="POST"))["id"]
    time.sleep(30)  # 미디어 처리 대기 (공식 권장값)
    json.loads(http(f"{THREADS}/{me}/threads_publish?creation_id={cid}&access_token={tok}", method="POST"))


def threads_deals(seen):
    """채널에 올라간 딜을 Threads에도 하나씩 (링크 = 사이트 딜 페이지: 구매 버튼·대가성 문구 있음).
    사이트 반영 전(404)이면 다음 실행에. posts.json에 th 표시 -> 두 번 안 올림. 3시간 지난 딜은 안 올림(식은 딜), 1회 최대 3개(도배 방지)."""
    tok, posts = E.get("THREADS_TOKEN"), load(POSTS, [])
    since = time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - 3 * 3600))
    todo = [i for i, p in enumerate(posts) if not p.get("th") and p["t"] >= since and not p["text"].startswith("📋")][:3]
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
        text = (f"{note}\n\n" if note else "") + f"🔥 {title_of(posts[i]['text'])}\n\n{comment_of(posts[i]['text'])}"[:250] \
            + f"\n\n👉 {url}\n📲 실시간 알림 t.me/hotdeal_pick"  # Threads 500자 제한(이모지는 바이트로 셈)
        posts[i]["th"] = 1  # 먼저 표시: 실패해도 같은 딜 반복 시도 안 함(스팸 방지), 실패는 main()이 알림
        json.dump(posts, open(POSTS, "w"), ensure_ascii=False)
        for att in ({"link_attachment": url}, {}):  # 링크 미리보기를 Threads가 못 만들면(4279047 'Invalid Link Attachment', 10/7 15:51) 첨부 없이 1번 더 — 본문 주소는 그대로
            q = urllib.parse.urlencode({"media_type": "TEXT", "text": text, **att, "topic_tag": "핫딜", "access_token": tok})
            cid = json.loads(http(f"{THREADS}/{me}/threads?{q}", method="POST"))["id"]
            time.sleep(10)
            try:
                json.loads(http(f"{THREADS}/{me}/threads_publish?creation_id={cid}&access_token={tok}", method="POST"))
                break
            except urllib.error.HTTPError as e:
                if not att or "4279047" not in (getattr(e, "body", "") or ""):
                    raise


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
    held.sort(key=lambda h: -h["p"]["score"])
    good = []
    if new:
        since = time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - 86400))
        recent = [title_of(p["text"]) for p in load(POSTS, []) if p["t"] >= since and not p["text"].startswith("📋")][-30:]
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
        good = [p for p in picks if p["score"] >= MIN_SCORE - is_oy(new[p["i"]]["title"])]  # 올리브영은 1점 낮춰도(10/10 쇼핑 큐레이터 — 뽐뿌에 주 2~3개인데 6점 미만으로 다 빠지던 것)
        if not good and not held and picks and quiet():
            best = max(picks, key=lambda p: p["score"])
            good = [best] if best["score"] >= FILL_SCORE else []
        good = [{"d": new[p["i"]], "p": {k: v for k, v in p.items() if k != "i"}} for p in good]
    for h in (held + good)[:MAX_DRAFTS]:  # 보관해 둔 딜이 먼저
        seen.pop("hold_" + h["d"]["id"], None)
        p = h["p"]
        post_or_draft(h["d"], p["comment"], p["score"], p.get("q"), {k: p.get(k) for k in ("e", "hook", "pts", "unit", "warn")})
    for h in good[max(0, MAX_DRAFTS - len(held)):]:  # 넘친 좋은 딜은 다음 실행에 다시 묻지 않고 올리게 보관
        seen["hold_" + h["d"]["id"]] = {"t": time.time(), **h}
    for step in (events, playlist, goldbox, lambda s: cp_events(s, deals), top_deals, toss_deals, lambda s: toss_deals(s, True), lambda s: toss_deals(s, "cat"), toss_relink, lambda s: digest(s, load(POSTS, [])), threads, threads_deals, ig_repost, ig_publish, coupang_remind, oy_claim, report):
        try:
            step(seen)
        except Exception as e:
            print(step.__name__, repr(e))
            ig = step is ig_publish
            alert = time.strftime(("ig" if ig else "th") + "_alert_%Y%m%d", time.gmtime(time.time() + 9 * 3600))
            if step in (threads, threads_deals, ig_publish) and alert not in seen:  # 토큰 만료 등: 하루 1번만 알림
                seen[alert] = time.time()
                tg("sendMessage", chat_id=ADMIN, text=f"⚠️ {'인스타' if ig else 'Threads'} 게시 실패: {e!r}"[:300] + "\n"
                   + ("IG_TOKEN 만료(60일)면 앱 대시보드에서 토큰 다시 생성 → README 세팅 6-2" if ig else threads_hint(e)))
    cutoff = time.time() - 3 * 86400
    json.dump({k: v for k, v in seen.items() if (v["t"] if isinstance(v, dict) else v) > cutoff}, open(SEEN, "w"))  # hold_ = 딜째 보관
    print(f"new={len(new)} seen={len(seen)}")


if __name__ == "__main__":
    main()
