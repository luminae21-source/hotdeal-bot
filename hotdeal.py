#!/usr/bin/env python3
"""핫딜봇: 뽐뿌·루리웹·클리앙 핫딜 -> Claude 선별/코멘트 -> 채널 바로 게시.
상품 주소가 있으면(루리웹·클리앙 글) 링크프라이스 승인 몰은 상품 페이지 제휴 링크 자동, 없으면(뽐뿌: GitHub IP 차단) 검색 제휴 링크.
쿠팡·네이버 등 수동 몰은 관리자에게 사본(+쿠팡은 파트너스 검색 버튼, 네이버는 상품명 복사·쇼핑커넥트 버튼, 그 외 상품 열기 버튼) -> 제휴 링크를 답장(또는 그냥 전송)하면 채널 글 교체. 쿠팡 골드박스는 매일 7시 이후 1번 채널에 바로(키 없으면 골드박스 링크, 있으면 TOP5).
GitHub Actions에서 15분마다 실행(tick.yml 타이머가 workflow_dispatch로 실행 + 예약 보조). 외부 패키지 없음(파이썬 표준 라이브러리만)."""
import base64, hashlib, hmac, html, json, os, re, tempfile, time, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from build_site import BASE as SITE, BLOG, GOLDBOX, NOTE_STARTS, title_of, split_title

E = {k: "".join(v.split()) for k, v in os.environ.items()}  # 시크릿 붙여넣을 때 섞인 공백·줄바꿈 전부 제거
ADMIN, CHANNEL = E.get("TG_ADMIN_ID", ""), E.get("TG_CHANNEL", "")
MODEL = E.get("MODEL") or "claude-sonnet-5-5"
MIN_SCORE = int(E.get("MIN_SCORE") or 7)
HAS_CP = bool(E.get("COUPANG_ACCESS_KEY") and E.get("COUPANG_SECRET_KEY"))
HAS_TOSS = bool(E.get("TOSS_ACCESS_KEY") and E.get("TOSS_SECRET_KEY") and E.get("TOSS_PUBLISHER_ID"))  # 쉐어링크 Open API(10/6 승인). 호출은 고정 IP(오라클) 터널 경유 -> hotdeal.yml
TOSS_API, TOSS_TOKEN = "https://sharelink.toss.im/openapi", "toss.json"  # toss.json: 1년짜리 액세스 토큰 보관(Actions 캐시, 매번 재발급 금지)
MAX_DRAFTS = 2                 # 1회 실행(15분)당 채널 게시 최대 개수. 몰아 올리면 묻혀서 나눠 올림 -> 넘친 딜은 다음 실행에 다시 판단
MIN_AGE, MAX_AGE = 30, 360     # 분: 반응이 쌓인 뒤 판단, 너무 오래된 글은 무시
MIN_AGE_RULIWEB = 15           # 루리웹 RSS엔 추천·댓글 수가 없어 기다려도 판단 근거가 안 늘어남 -> 빨리
RUN_GAP = 20                   # 분: 다음 실행까지(15분 체인 + 지연 여유). 이 안에 목록에서 밀려날 글은 덜 묵었어도 지금 판단
FEEDS = {"ppomppu": "뽐뿌"}  # 뽐뿌 보드 추가: {"rss id": "표시명"}
RULIWEB_RSS = "https://bbs.ruliweb.com/market/board/1020/rss"  # 루리웹 핫딜예판: RSS + 글 아래 '출처'에 상품 주소 (robots 허용, GitHub 서버 OK 10/5)
CLIEN_LIST = "https://www.clien.net/service/board/jirum"  # 클리앙 알뜰구매: RSS 없음 -> 목록 HTML, 글 위 '구매링크' (robots: 쿼리 없는 /service/board/ 허용)
KST = timezone(timedelta(hours=9))
SEEN, POSTS = "seen.json", "posts.json"  # posts.json: 채널에 게시된 딜 -> build_site.py가 웹사이트로 만듦
EVENTS = "events.json"  # 예약 게시(쿠가세 같은 행사): [{"at": "YYYY-MM-DD HH:MM"(KST), "text": HTML, "button", "url": 파트너스 링크}] — Claude가 저장소에 넣음
MUSIC = "music.json"  # 릴스 배경음악: 관리자가 봇에 보낸 음악의 텔레그램 file_id만 저장(음원 파일은 공개 저장소에 안 올림 — 무료 음원도 원본 재배포는 금지)
IG = "https://graph.facebook.com/v25.0"  # 인스타 릴스 자동 게시(Facebook 로그인 방식 = 영상 파일을 바로 올림, 호스팅 불필요). IG_TOKEN = 페이지 액세스 토큰
CP_HOST, CP_BASE = "https://api-gateway.coupang.com", "/v2/providers/affiliate_open_api/apis/openapi/v1"
DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
AFF_NOTE = "이 포스팅은 제휴마케팅이 포함된 광고로 커미션을 지급 받습니다."  # 링크프라이스 머천트 안내 대가성 문구 그대로(10/5 머천트 정보 화면)
TOSS_NOTE = "이 콘텐츠는 토스쇼핑 쉐어링크 활동의 일환으로, 링크를 통한 구매가 발생하면 일정 수수료를 지급받습니다."  # 토스 권장 문구 (쉐어링크 가이드 '대가성 문구 표시하기', 10/5 확인)
TOSS_HOSTS = ("toss.im", "toss.shopping")  # 쉐어링크 단축(toss.im/_m/..)·원본(toss.shopping/t/..)
NAVER_NOTE = "이 포스팅은 네이버 쇼핑 커넥트 활동의 일환으로, 판매 발생 시 수수료를 제공받습니다."  # 네이버 안내 문구 그대로(변형·누락 시 패널티), 글 맨 앞
NAVER_HOSTS = ("naver.me",)  # 쇼핑커넥트 '링크 발급' 주소 (naver.me 단축)
LP = "💰 링크프라이스 최대 {} · 딥링크 만들어 답장"
STORES = {"쿠팡": "💰 쿠팡 파트너스 · 링크 만들어 답장", "토스": "💰 토스 쉐어링크 · 링크 만들어 답장",  # 뽐뿌 제목 [쇼핑몰] -> 초안 안내 버튼
          "g마켓": LP.format("0.6%"), "지마켓": LP.format("0.6%"), "옥션": LP.format("0.6%"), "롯데온": LP.format("1.4%"),
          "롯데on": LP.format("1.4%"), "하이마트": LP.format("1.26%"), "이마트": LP.format("1%"),  # 하이마트(10/5 자동 승인)는 '이마트'보다 먼저(글자 포함 관계)
          # ⏳ = 아직 링크를 못 만드는 몰 -> 사본 안 보냄(💰만 보냄). 승인 나면 LP.format("1.05%")·LP.format("6.3%")·LP.format("3.18%")로 바꾸기
          "11번가": "⏳ 11번가 링크프라이스 승인 대기 · 지금은 수수료 0", "알리": "⏳ 알리 링크프라이스 승인 대기(10/5 신청) · 지금은 수수료 0",
          "오늘의집": "⏳ 오늘의집 링크프라이스 승인 대기(10/5 신청) · 지금은 수수료 0",
          "네이버": "💰 네이버 쇼핑커넥트 · 상품 검색해 링크 발급 후 답장"}  # 10/5 가입. 활동 제한 채널(일베·오유·워마드·다모앙·더쿠·일부 카페)에 우리 채널 없음 -> 허용. 판매자가 참여한 상품만 링크 발급 가능
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
               "aliexpress": "알리", "auction.co.kr": "옥션", "emart.ssg.com": "이마트", "e-himart.co.kr": "하이마트", "ohou.se": "오늘의집"}  # 제목에 [쇼핑몰]이 없을 때(클리앙) 주소로 몰 판단
AFF_HOSTS = ("click.linkprice.com", "lpweb.kr", "linkmoa.kr", "lase.kr", "bestmore.net", "newtip.net", "s.click.aliexpress.com")  # 쿠팡(link.coupang.com) 외 제휴 링크 도메인
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
q: 쇼핑몰 검색창에 넣을 짧은 검색어(브랜드+상품명+핵심 용량, 수량·가격·쿠폰 문구 빼고 20자 안팎).
REEL_RULES
같은 상품이 여러 커뮤니티([뽐뿌]·[루리웹]·[클리앙])에 올라왔으면 하나만 골라.
5점 미만은 반환하지 마.
"""
DEAL_PROMPT = DEAL_PROMPT.replace("REEL_RULES", REEL_RULES)
REEL_PROMPT = "아래 딜 각각(모든 i)에 대해 인스타 릴스용 정보를 pick 도구로 반환해. score는 0, comment는 빈 문자열.\n" + REEL_RULES + "\n"
GOLD_PROMPT = """쿠팡 골드박스(오늘 하루 특가) 목록이야. 대중적으로 많이 살 만한 상품 5개를 골라 pick 도구로 반환해.
comment: 1줄, 사실 위주, 과장 금지, 건강식품 효능 언급 금지.
"""


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
    picks = next((c["input"]["picks"] for c in r["content"] if c["type"] == "tool_use"), [])
    return sorted((p for p in picks if 0 <= p["i"] < len(lines)), key=lambda p: -p["score"])


def store_link(post_url):
    """딜 글에 적힌 실제 쇼핑몰 주소 (남의 제휴 링크·추적값은 plain()으로 걷어냄). 못 찾으면 None.
    루리웹: 글 아래 '출처'(web.ruliweb.com/link.php?ol=원래주소, 네이버·토스는 주소 그대로). 클리앙: 글 위 '구매링크'(attached_link).
    뽐뿌: 상단 링크(s.ppomppu.co.kr ... target=base64) — ponytail: GitHub 서버 IP를 403 차단(10/5 linkcheck)이라 지금은 None,
    그동안은 검색 제휴 링크 또는 관리자 답장. 차단 풀리면 그대로 다시 동작."""
    try:
        page = http(post_url)
    except Exception as e:
        print("link", post_url, repr(e))
        return None
    if "ruliweb.com" in post_url:
        m = re.search(r'class="source_url.*?href="([^"]+)"', page, re.S)  # 보통 link.php?ol=원래주소, 네이버·토스 등은 주소 그대로
        u = html.unescape(m.group(1)) if m else ""
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
    if host == "click.linkprice.com":
        return plain(qs["tu"][0], hops) if "tu" in qs else None
    if host == "toss.shopping":  # 상품은 /t/번호, 쿼리(k=·referrer)는 남의 쉐어링크 표시
        return urllib.parse.urlunsplit(("https", host, p.path, "", ""))
    if host in ("link.coupang.com", "coupa.ng") or host in AFF_HOSTS + TOSS_HOSTS + NAVER_HOSTS:
        return plain(location(url), hops - 1) if hops else None
    if host.endswith("coupang.com"):  # lptag·subid 등 추적값 빼고 상품·옵션만
        keep = {k: v[0] for k, v in qs.items() if k in ("itemId", "vendorItemId")}
        return urllib.parse.urlunsplit(("https", "www.coupang.com", p.path, urllib.parse.urlencode(keep), ""))
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
    """채널 글(posts.json text) -> 제목 아래 코멘트 (출처 줄 제외)."""
    return split_title(text)[1].rsplit("\n\n출처:", 1)[0].strip()


def store_tag(title):
    """뽐뿌 제목 맨 앞 [쇼핑몰] -> 비교용 소문자·공백 제거 ('[G마켓]메디폴미' -> 'g마켓')."""
    tag = re.match(r"\s*\[([^\]]+)\]", title)
    return tag.group(1).lower().replace(" ", "") if tag else ""


PRICE_TAIL = r"\s*\([^()]*(원|무료|무배|배송)[^()]*\)\s*$"  # 뽐뿌 제목 끝 (가격/배송)


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
    text = f"{head}🔥 <b>{esc(d['title'])}</b>\n\n{esc(comment)}{facts}\n\n출처: <a href=\"{esc(d['url'])}\">{d['board']}</a>"
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
        elif url != d["url"]:  # 상품 주소를 알면: 눌러서 쇼핑앱 열기 -> 공유 -> 제휴 링크 복사 -> 답장 (뽐뿌 글 거칠 필요 없음)
            kb.insert(1, [{"text": "🛒 상품 열기 (앱에서 공유 → 제휴 링크)", "url": url}])
        cp = (tg("copyMessage", chat_id=ADMIN, from_chat_id=CHANNEL, message_id=m["message_id"],
                 reply_markup={"inline_keyboard": kb}) or {}).get("message_id")
    record(m.get("text", ""), m.get("entities", []), url, m.get("message_id"), score, {**(extra or {}), "cp": cp})  # cp: 관리자 사본 번호(답장 없이 링크만 보낼 때 찾기용)


def pending_copy(link):
    """답장 없이 제휴 링크만 보냈을 때 바꿀 채널 글: 같은 프로그램(쿠팡·토스·네이버) 사본 중 아직 안 바꾼 가장 최근 글(24시간 안)."""
    shop = {DISCLOSURE: "쿠팡", TOSS_NOTE: "토스", NAVER_NOTE: "네이버"}.get(aff_note(link))
    since = time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - 86400))
    return next((p for p in reversed(load(POSTS, [])) if shop and p.get("cp") and p.get("mid") and p["t"] >= since
                 and not aff_note(p.get("url") or "") and store_info(title_of(p["text"]), p.get("url")).startswith("💰 " + shop)), None)


def aff_note(url):
    """제휴 링크면 그 프로그램의 대가성 문구, 일반 쇼핑몰 주소면 ''."""
    host = urllib.parse.urlsplit(url).netloc
    return (DISCLOSURE if host == "link.coupang.com" else TOSS_NOTE if host in TOSS_HOSTS else NAVER_NOTE if host in NAVER_HOSTS
            else AFF_NOTE if host in AFF_HOSTS else "")


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
            if all(x["u"] != au["file_unique_id"] for x in mus):  # 같은 곡 두 번 보내도 1번만
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


def threads_hint(e):
    """Threads 실패 알림의 조치 문구: Meta 개발자 계정 잠김('API access blocked', 10/6)과 토큰 만료를 구분."""
    if "blocked" in (getattr(e, "body", "") or ""):
        return "Meta가 개발자 계정을 잠갔어(API access blocked) → developers.facebook.com 접속해서 '계정 확인' 진행해줘. 끝나면 자동 재개"
    return "토큰 만료(60일)면 THREADS_TOKEN 시크릿 재발급해줘"


def toss_deals(seen):
    """토스 하루특가(API): 9시 이후 하루 1번, Claude가 고른 5개를 쉐어링크로 채널 + Threads에 바로. 편성 0건인 날은 다음 실행에 다시.
    API 상품·가격은 채널·Threads 글로만 쓰고 posts.json(사이트·모아보기·블로그)엔 안 남김 — 승인 신청 내용(서비스 = 텔레그램 채널 + 스레드 자동 게시,
    커머스형 전시·가격 비교 안 함) 그대로."""
    kst = time.gmtime(time.time() + 9 * 3600)
    key = time.strftime("tossday_%Y%m%d", kst)
    if not HAS_TOSS or key in seen or kst.tm_hour < 9:
        return
    items = [x for x in toss("/products/today-deals?size=30")["items"] if not x.get("isSoldOut")]
    picks = items and ai_pick(GOLD_PROMPT.replace("쿠팡 골드박스", "토스쇼핑 하루특가"),
                              [f"{x['displayName']} | {x['displayPrice']:,}원 ({x.get('discountRate', 0)}% 할인)" for x in items])[:5]
    rows, plain = [], []
    for p in picks or []:
        x = items[p["i"]]
        try:
            link = toss("/links", {"tacaItemId": x["tacaItemId"], "publisherId": E["TOSS_PUBLISHER_ID"]})["shortUrl"]
        except Exception as e:  # 발급 제한 상품은 빼고 나머지만
            print("toss link", repr(e))
            continue
        plain.append(f"{len(plain) + 1}. {clip(x['displayName'], 24)} — {x['displayPrice']:,}원\n{link}")
        rows.append(f"{len(rows) + 1}. <a href=\"{esc(link)}\">{esc(x['displayName'])}</a> — <b>{x['displayPrice']:,}원</b>"
                    + (f" ({x['discountRate']}%↓)" if x.get("discountRate") else "") + f"\n   {esc(p['comment'])}")
    print("toss_deals", len(items), "items", len(picks or []), "picks", len(rows), "links")  # 0건이어도 로그로 확인
    if items:  # Claude까지 돌렸으면 오늘은 끝(발급이 다 막혀도 15분마다 다시 고르지 않게). Threads가 실패해도 채널에 두 번 안 올라가게 먼저 표시
        seen[key] = time.time()
    if rows:
        tg("sendMessage", chat_id=CHANNEL, parse_mode="HTML", link_preview_options={"is_disabled": True},
           text=f"<i>{TOSS_NOTE}</i>\n\n⏰ <b>오늘의 토스 하루특가 TOP{len(rows)}</b>\n\n" + "\n\n".join(rows))
    tok = E.get("THREADS_TOKEN")
    if rows and tok:  # Threads 글자 수 500 -> 넘치면 뒤 상품부터 뺌. 대가성 문구는 토스 가이드대로 맨 앞(더보기 없이 보이게)
        while len(plain) > 1 and len(TOSS_NOTE) + 40 + len("\n\n".join(plain)) > 480:
            plain.pop()
        text = f"{TOSS_NOTE}\n\n⏰ 오늘의 토스 하루특가 TOP{len(plain)}\n\n" + "\n\n".join(plain)
        me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
        q = urllib.parse.urlencode({"media_type": "TEXT", "text": text[:500], "topic_tag": "핫딜", "access_token": tok})
        cid = json.loads(http(f"{THREADS}/{me}/threads?{q}", method="POST"))["id"]
        time.sleep(10)
        json.loads(http(f"{THREADS}/{me}/threads_publish?creation_id={cid}&access_token={tok}", method="POST"))


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
    rows = [f"{n}. <a href=\"{esc(p['url'])}\">{esc(title_of(p['text']))}</a>" for n, p in enumerate(todays, 1)]
    text = (f"📋 <b>오늘의 딜 모아보기 ({kst.tm_mon}/{kst.tm_mday})</b>\n\n" + "\n".join(rows)
            + f"\n\n🔎 지난 딜 전체 보기: {SITE}\n📝 블로그: {BLOG}\n📲 실시간 알림: https://t.me/hotdeal_pick")
    if draft(text):
        seen[key] = time.time()
        blog()
        import cards
        try:  # Threads/인스타용 카드 -> docs/cards/ (워크플로가 커밋 -> 사이트에 공개 -> 다음 실행 때 threads()가 올림)
            cards.make([{"title": title_of(p["text"]), "unit": p.get("unit")} for p in todays], f"{kst.tm_mon}월 {kst.tm_mday}일", f"docs/cards/{today}.png")
        except Exception as e:
            print("card", repr(e))
        try:  # 인스타 릴스용 15초 영상 -> 관리자에게 바로 전송 (저장소엔 안 올림). 점수 높은 순 TOP3
            top = sorted(todays, key=lambda p: -p.get("s", 0))[:3]
            need = [p for p in top if not (p.get("hook") and p.get("pts"))]  # ✅로 올린 글·예전 글은 릴스 재료가 없음 -> 여기서 채움
            if need:
                try:
                    for f in ai_pick(REEL_PROMPT, [f"{title_of(p['text'])} | {comment_of(p['text'])}" for p in need]):
                        need[f["i"]].update({k: f[k] for k in ("e", "hook", "pts", "unit", "warn") if f.get(k)})
                except Exception as e:
                    print("reel fill", repr(e))
            path = cards.reel([{"title": title_of(p["text"]), "comment": comment_of(p["text"]),
                                **{k: p.get(k) for k in ("e", "hook", "pts", "unit", "warn")}} for p in top], f"{kst.tm_mon}월 {kst.tm_mday}일",
                              os.path.join(tempfile.gettempdir(), f"reel_{today}.mp4"), bgm(kst))
            cap = ((top[0].get("hook") + " · " if top[0].get("hook") else "") + f"{kst.tm_mon}월 {kst.tm_mday}일 가성비 TOP{len(top)}\n\n"
                   + "\n".join(f"{n}. {title_of(p['text'])}" for n, p in enumerate(top, 1))
                   + "\n\n전체 딜·구매 링크는 프로필 링크(hotdealpick.kr)에서\n일부 링크는 제휴 링크로 수수료를 받을 수 있어요."
                   + "\n\n#핫딜 #오늘의핫딜 #특가 #최저가 #살림템 #쇼핑정보")[:1024]
            if E.get("IG_TOKEN") and E.get("IG_USER_ID"):
                try:
                    ig_upload(path, cap, seen)
                except Exception as e:
                    print("ig upload", repr(e), getattr(e, "body", ""))
                    tg("sendMessage", chat_id=ADMIN, text=f"⚠️ 인스타 릴스 업로드 실패 — 아래 영상을 직접 올려줘: {e!r} {getattr(e, 'body', '')}"[:400])
            tg_video(path, cap)
        except Exception as e:
            print("reel", repr(e))


def bgm(kst):
    """관리자가 봇에 보낸 배경음악(music.json) 중 오늘 차례 1곡 -> 임시 파일 경로. 없거나 못 받으면 None(무음 릴스)."""
    mus = load(MUSIC, [])
    if not mus:
        return None
    try:
        f = tg("getFile", file_id=mus[kst.tm_yday % len(mus)]["id"])
        path = os.path.join(tempfile.gettempdir(), "bgm")
        with urllib.request.urlopen(f"https://api.telegram.org/file/bot{E['TG_TOKEN']}/{f['file_path']}", timeout=60) as r:
            open(path, "wb").write(r.read())
        return path
    except Exception as e:
        print("bgm", repr(e))


def ig_upload(path, caption, seen):
    """릴스 영상 -> 인스타 컨테이너 생성 + 영상 파일 업로드(rupload). 인스타가 처리하는 동안 기다리지 않고 다음 실행의 ig_publish()가 발행."""
    h = {"Authorization": "Bearer " + E["IG_TOKEN"]}
    c = json.loads(http(f"{IG}/{E['IG_USER_ID']}/media", {"media_type": "REELS", "upload_type": "resumable", "caption": caption, "share_to_feed": True}, h, "POST"))
    data = open(path, "rb").read()
    http(c["uri"], data, {"Authorization": "OAuth " + E["IG_TOKEN"], "offset": "0", "file_size": str(len(data))}, "POST")
    seen["igc_" + c["id"]] = time.time()


def ig_publish(seen):
    """올려둔 릴스 컨테이너가 처리 끝났으면(FINISHED) 발행. 처리 중이면 다음 실행에, 실패(ERROR·EXPIRED)면 알림(main)."""
    tok, uid = E.get("IG_TOKEN"), E.get("IG_USER_ID")
    if not (tok and uid):
        return
    for k in [k for k in seen if k.startswith("igc_")]:
        st = json.loads(http(f"{IG}/{k[4:]}?fields=status_code", headers={"Authorization": "Bearer " + tok}))["status_code"]
        if st == "IN_PROGRESS":
            continue
        seen.pop(k)
        if st != "FINISHED":
            raise RuntimeError(f"인스타 릴스 처리 실패({st}) — 오늘 영상은 봇 채팅에서 직접 올려줘")
        json.loads(http(f"{IG}/{uid}/media_publish", {"creation_id": k[4:]}, {"Authorization": "Bearer " + tok}, "POST"))
        tg("sendMessage", chat_id=ADMIN, text="🎬 인스타 릴스 자동 게시 완료 (instagram.com/hotdealpick.kr)")


def blog_text(todays, kst):
    """네이버 블로그에 그대로 복붙할 제목+본문 (일반 텍스트, 링크 그대로 노출, 대가성 문구 포함)."""
    title = f"{kst.tm_mon}월 {kst.tm_mday}일 핫딜 모음 | {title_of(todays[0]['text'])}" + (f" 외 {len(todays) - 1}건" if len(todays) > 1 else "")
    items = []
    for n, p in enumerate(todays, 1):
        t, rest, _ = split_title(p["text"])
        items.append(f"{n}. {t}\n{rest.split(chr(10))[0]}\n👉 {p['url'] or SITE}")
    return (f"📝 블로그용 (제목·본문 그대로 복붙)\n\n제목: {title}\n\n" + "\n\n".join(items)
            + f"\n\n더 많은 핫딜 👉 {SITE}\n실시간 알림 👉 https://t.me/hotdeal_pick\n\n"
            + "이 포스팅은 쿠팡 파트너스·토스쇼핑 쉐어링크 등 제휴 마케팅 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받을 수 있습니다.")


THREADS = "https://graph.threads.com/v1.0"  # 공식 문서 기준 도메인


def threads(seen):
    """오늘 카드가 사이트에 올라와 있으면 관리자에게 인스타용으로 1회 보내고, THREADS_TOKEN 있으면 Threads에도 게시.
    토큰은 60일마다 만료 -> 실패하면 main()이 관리자에게 알림."""
    kst = time.gmtime(time.time() + 9 * 3600)
    today, key = time.strftime("%Y-%m-%d", kst), time.strftime("threads_%Y%m%d", kst)
    if key in seen or not os.path.exists(f"docs/cards/{today}.png"):
        return
    url = f"{SITE}cards/{today}.png"
    try:
        http(url, method="HEAD")  # 아직 배포 전(404)이면 다음 실행에 다시
    except Exception:
        return
    tok = E.get("THREADS_TOKEN")
    tg("sendPhoto", chat_id=ADMIN, photo=url, caption="📸 오늘의 카드 (인스타에 그대로 올리면 돼)" + (" · Threads는 자동 게시 중" if tok else ""))
    seen[key] = time.time()  # 사진은 1번만. Threads 실패는 아래서 관리자에게 알리고 재시도 안 함(스팸 방지)
    if not tok:
        return
    todays = [p for p in load(POSTS, []) if p["t"].startswith(today) and not p["text"].startswith("📋")]
    rows = [f"{n}. {clip(re.sub(PRICE_TAIL, '', title_of(p['text'])).strip(), 34)}" for n, p in enumerate(todays[:6], 1)]  # 가격은 카드 이미지에
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
        q = urllib.parse.urlencode({"media_type": "TEXT", "text": text, "link_attachment": url, "topic_tag": "핫딜", "access_token": tok})
        cid = json.loads(http(f"{THREADS}/{me}/threads?{q}", method="POST"))["id"]
        time.sleep(10)
        json.loads(http(f"{THREADS}/{me}/threads_publish?creation_id={cid}&access_token={tok}", method="POST"))


def load(path, default):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return default


def dkey(title):
    """같은 딜 판단 키: [쇼핑몰]·가격 꼬리(괄호·' / 가격') 떼고 글자·숫자만 앞 24자. 너무 짧으면 None(판단 안 함). 24시간 지나면 같은 상품도 새 딜로 봄."""
    k = re.sub(r"[^0-9a-z가-힣]", "", re.split(r"\s/\s", keyword(title))[0].lower())[:24]
    return "k:" + k if len(k) >= 4 else None


def main():
    seen = load(SEEN, {})
    publish_approved()
    new, keys = [], set()
    deals = fetch_deals()
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
    if new:
        since = time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - 86400))
        recent = [title_of(p["text"]) for p in load(POSTS, []) if p["t"] >= since and not p["text"].startswith("📋")][-30:]
        prompt = DEAL_PROMPT + ("\n최근 24시간에 이미 올린 딜(같은 상품이면 고르지 마):\n" + "\n".join(recent) if recent else "")
        picks = ai_pick(prompt, [f"[{d['board']}] {d['title']} | {d['hits']} | {d['age']:.0f}분 전 | {d['desc']}" for d in new])
        for d in new:  # AI 판단 성공한 뒤에만 '본 글'로 기록 -> 실패 시 다음 실행에서 재시도
            seen[d["id"]] = time.time()
            if dkey(d["title"]):
                seen[dkey(d["title"])] = time.time()
        print("점수", [(p["score"], new[p["i"]]["title"][:30]) for p in picks] or "5점 이상 없음")  # 컷 조절용 근거
        good = [p for p in picks if p["score"] >= MIN_SCORE]
        for p in good[MAX_DRAFTS:]:  # 넘친 좋은 딜은 '본 글'에서 빼서 다음 실행(15분 뒤)에 다시 판단 -> 나눠서 게시
            seen.pop(new[p["i"]]["id"], None)
            seen.pop(dkey(new[p["i"]]["title"]), None)
        for p in good[:MAX_DRAFTS]:
            post_or_draft(new[p["i"]], p["comment"], p["score"], p.get("q"), {k: p.get(k) for k in ("e", "hook", "pts", "unit", "warn")})
    for step in (events, goldbox, toss_deals, lambda s: digest(s, load(POSTS, [])), threads, threads_deals, ig_publish):
        try:
            step(seen)
        except Exception as e:
            print(step.__name__, repr(e))
            ig = step is ig_publish
            alert = time.strftime(("ig" if ig else "th") + "_alert_%Y%m%d", time.gmtime(time.time() + 9 * 3600))
            if step in (threads, threads_deals, ig_publish) and alert not in seen:  # 토큰 만료 등: 하루 1번만 알림
                seen[alert] = time.time()
                tg("sendMessage", chat_id=ADMIN, text=f"⚠️ {'인스타' if ig else 'Threads'} 게시 실패: {e!r}"[:300] + "\n"
                   + ("IG_TOKEN(페이지 토큰)·권한 확인 → README 세팅 6-2" if ig else threads_hint(e)))
    cutoff = time.time() - 3 * 86400
    json.dump({k: v for k, v in seen.items() if v > cutoff}, open(SEEN, "w"))
    print(f"new={len(new)} seen={len(seen)}")


if __name__ == "__main__":
    main()
