#!/usr/bin/env python3
"""posts.json(채널에 게시된 딜) -> docs/ 정적 사이트. GitHub Pages로 서빙. 외부 패키지 없음."""
import calendar, html, json, os, re, time, urllib.parse

BASE = "https://hotdealpick.kr/"
CHANNEL = "https://t.me/hotdeal_pick"
BLOG = "https://blog.naver.com/hotdeal_pick"
INSTA = "https://www.instagram.com/hotdealpick.kr/"
THREADS = "https://www.threads.com/@hotdealpick.kr"
GOLDBOX = "https://link.coupang.com/a/hBMtMDCxFY"  # 쿠팡 파트너스 간편 링크: 골드박스 페이지(coupang.com/np/goldbox), 10/6 생성. 클릭 후 24시간 안 쿠팡 구매가 실적
CHANNEL_WEB = "https://t.me/s/hotdeal_pick"  # 텔레그램 채널 웹 보기(앱 없이 열림)
TITLE = "핫딜픽"  # 브랜드 이름 (텔레그램·블로그·스레드·인스타·페이스북 모두 핫딜픽, 10/5 통일)
DISCLOSURE = "이 사이트는 쿠팡 파트너스·토스쇼핑 쉐어링크 등 제휴 마케팅 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받을 수 있습니다."
CSS = """*{box-sizing:border-box}[hidden]{display:none!important}body{margin:0;font:16px/1.55 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;background:#f4f5f7;color:#191f28;-webkit-font-smoothing:antialiased;word-break:keep-all;overflow-wrap:anywhere}
a{color:#1b64da}main{max-width:680px;margin:0 auto;padding:12px 16px 16px}header{position:relative;padding:8px 0 0}header h1{margin:0;font-size:21px;font-weight:800;letter-spacing:-.3px}header h1 a{color:inherit;text-decoration:none}
.sub{color:#6b7684;font-size:13px;margin-top:1px}.lk{position:absolute;right:0;top:6px;display:flex;align-items:center;gap:4px;min-height:40px;padding:0 14px;border-radius:20px;background:#fff;border:1px solid #e8eaee;color:#e42939;text-decoration:none;font-weight:700;font-size:14px}.lk svg{width:18px;height:18px}
.dis{font-size:11px;line-height:1.5;color:#8b95a1;margin:8px 0}footer{font-size:12px;color:#8b95a1;text-align:center;padding:24px 0}
.gb{display:flex;align-items:center;justify-content:center;min-height:44px;padding:6px 12px;margin:6px 0 2px;border-radius:12px;background:#fff4e6;color:#c2410c;border:1px solid #ffd8a8;text-decoration:none;font-weight:700;font-size:15px}
.card{background:#fff;border-radius:16px;padding:18px 16px;margin:12px 0;border:1px solid #eef0f3;box-shadow:0 1px 2px rgba(25,31,40,.05)}.card h2{margin:0 0 8px;font-size:17px;line-height:1.4}.card h2 a{color:inherit;text-decoration:none}.t{color:#8b95a1;font-size:12px}
.btn{display:flex;align-items:center;justify-content:center;min-height:50px;padding:10px 12px;margin-top:12px;border-radius:12px;background:#1b64da;color:#fff;text-decoration:none;font-weight:700;font-size:16px;text-align:center}
.btn2{display:flex;align-items:center;justify-content:center;min-height:46px;padding:8px 12px;margin-top:8px;border-radius:12px;border:1.5px solid #1b64da;color:#1b64da;text-decoration:none;font-weight:700;text-align:center}
.tg{display:flex;align-items:center;justify-content:center;min-height:50px;padding:10px;margin:16px 0;border-radius:12px;background:#229ed9;color:#fff;text-decoration:none;font-weight:700;text-align:center}
.pick{display:flex;align-items:center;gap:12px;min-height:56px;padding:12px 14px;margin:8px 0;border-radius:14px;background:#fff;border:1px solid #eef0f3;color:#191f28;text-decoration:none;font-weight:600}.alt{display:block;margin:-4px 0 8px 56px;font-size:15px;padding:12px 0}.pick b{color:#e8590c;font-size:20px;min-width:30px}.pick span{flex:1;line-height:1.35}.pick em{font-style:normal;color:#c2410c;font-size:14px;white-space:nowrap}
a:focus-visible,button:focus-visible,input:focus-visible{outline:3px solid #1b64da;outline-offset:2px}
.bar{position:fixed;left:0;right:0;bottom:0;z-index:9;display:flex;justify-content:center;gap:2px;background:rgba(255,255,255,.94);-webkit-backdrop-filter:saturate(180%) blur(12px);backdrop-filter:saturate(180%) blur(12px);border-top:1px solid #e8eaee;padding:6px 6px calc(6px + env(safe-area-inset-bottom))}.bar a{flex:1;max-width:88px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;min-height:52px;border-radius:12px;color:#6b7684;text-decoration:none;font-size:12px;font-weight:600}.bar svg{width:22px;height:22px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.bar a[aria-current=true]{color:#1b64da;background:#e8f1fd}main:has(.bar){padding-bottom:84px}
.day h2{font-size:18px;font-weight:800;letter-spacing:-.3px;margin:22px 2px 2px}.day>.t{margin:0 2px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:10px}
.g{position:relative;display:flex;flex-direction:column;background:#fff;border-radius:16px;padding:12px;border:1px solid #eef0f3;box-shadow:0 1px 2px rgba(25,31,40,.04);min-width:0}.g .s{min-height:22px;padding:2px 30px 0 0;font-size:12px;color:#8b95a1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.like{position:absolute;top:4px;right:2px;width:40px;height:40px;display:flex;align-items:center;justify-content:center;padding:0;border:0;border-radius:20px;background:none;color:#b0b8c1;cursor:pointer}.like svg,.lk svg{fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.like svg{width:20px;height:20px}.like[aria-pressed=true]{color:#e42939}.like[aria-pressed=true] svg,.lk svg{fill:currentColor}
.g h3{margin:4px 0 6px;font-size:15px;line-height:1.4;font-weight:600;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}.g h3 a{color:inherit;text-decoration:none}
.g .pr{font-weight:800;font-size:18px;letter-spacing:-.3px;line-height:1.3}.sv{color:#e42939;font-size:13px;font-weight:700;line-height:1.45}.g .u{font-size:12px;color:#6b7684}.g .rx{font-size:12px;color:#8b95a1}
.g .go{margin-top:auto;padding-top:10px}.g .go a{display:flex;align-items:center;justify-content:center;min-height:44px;border-radius:10px;background:#1b64da;color:#fff;text-decoration:none;font-weight:700;font-size:15px}.g .go a.o{background:#f2f4f6;color:#333d4b}.g .go a.f{min-height:40px;font-size:13px;background:none;color:#6b7684;font-weight:600}
.find{position:sticky;top:0;z-index:8;background:#f4f5f7;padding:8px 0 4px}.find input{width:100%;min-height:46px;border:1px solid #e1e4e8;border-radius:12px;padding:0 14px;font:inherit;font-size:16px;background:#fff;color:inherit}.chips{display:flex;gap:6px;overflow-x:auto;padding:8px 0 2px;scrollbar-width:none}.chips::-webkit-scrollbar{display:none}.chips button{flex:none;min-height:36px;padding:0 13px;border-radius:18px;border:1px solid #e1e4e8;background:#fff;color:#333d4b;font:inherit;font-size:14px;font-weight:600;cursor:pointer}.chips button[aria-pressed=true]{background:#191f28;border-color:#191f28;color:#fff}#qn{margin:6px 2px 0}
.bd{display:flex;flex-wrap:wrap;gap:4px;margin:2px 0 4px}.bd b{font-size:11px;font-weight:700;padding:2px 7px;border-radius:6px;line-height:1.5}.b1{background:#e7f6ec;color:#15803d}.b2{background:#fdecec;color:#c62828}.b3{background:#f2f4f6;color:#6b7684}.b4{background:#fff4e6;color:#d9480f}
.deal .s{font-size:13px;color:#8b95a1}.deal h2{font-size:20px;letter-spacing:-.3px;margin:4px 0 12px}.hero{display:flex;align-items:baseline;flex-wrap:wrap;gap:2px 8px}.hero .pr{font-size:30px;font-weight:800;letter-spacing:-.6px;line-height:1.2}.ship{font-size:13px;color:#6b7684}.hero .sv{font-size:15px}.deal .u{font-size:14px;color:#6b7684;margin-top:2px}
.deal .btn{min-height:56px;font-size:18px;margin-top:16px}.deal .note{font-size:12px;color:#8b95a1;text-align:center;margin:8px 0 0}.why{font-size:14px;color:#6b7684;font-weight:700;margin:18px 0 6px;padding-top:16px;border-top:1px solid #f2f4f6}.deal p{margin:0;font-size:15px;line-height:1.65;color:#333d4b}
@media(prefers-color-scheme:dark){body{background:#101012;color:#ececf0}.card,.g,.pick,.lk{background:#1c1c1f;border-color:#2b2b30;box-shadow:none}.pick{color:#ececf0}.sub,.t,.dis,footer,.g .s,.deal .s,.deal .note,.g .rx{color:#8e8e96}a{color:#6ea8ff}.gb{background:#2a1f17;border-color:#7c2d12;color:#fdba74}.pick em{color:#fdba74}
.bar{background:rgba(28,28,31,.94);border-color:#2b2b30}.bar a{color:#a1a1aa}.bar a[aria-current=true]{color:#6ea8ff;background:#1f2a3a}.like{color:#71717a}.btn,.g .go a{background:#2b6fd6;color:#fff}.btn2{border-color:#6ea8ff;color:#6ea8ff}.find{background:#101012}.find input,.chips button{background:#1c1c1f;border-color:#2b2b30;color:#ececf0}.chips button[aria-pressed=true]{background:#ececf0;border-color:#ececf0;color:#101012}
.b1{background:#12301c;color:#86efac}.b2{background:#3a1616;color:#fca5a5}.b3{background:#2b2b30;color:#a1a1aa}.b4{background:#2a1f17;color:#fdba74}.g .go a.o{background:#2b2b30;color:#ececf0}.g .go a.f{background:none;color:#a1a1aa}.sv{color:#ff6b78}.g .u,.deal .u,.ship,.why{color:#a1a1aa}.why{border-color:#2b2b30}.deal p{color:#d4d4d8}}"""


def to_html(text, entities):
    """텔레그램 text + text_link 엔티티(UTF-16 오프셋) -> HTML."""
    u, out, pos = text.encode("utf-16-le"), [], 0
    for e in sorted((e for e in entities or [] if e.get("type") == "text_link"), key=lambda e: e["offset"]):
        s, n = e["offset"] * 2, (e["offset"] + e["length"]) * 2
        out.append(html.escape(u[pos:s].decode("utf-16-le")))
        out.append(f'<a href="{html.escape(e["url"])}" rel="nofollow noopener" target="_blank">'
                   f'{html.escape(u[s:n].decode("utf-16-le"))}</a>')
        pos = n
    out.append(html.escape(u[pos:].decode("utf-16-le")))
    return "".join(out).replace("\n", "<br>")


NOTE_STARTS = ("이 포스팅은", "이 콘텐츠는", "[광고]")  # 대가성 문구 줄 시작(쿠팡·링크프라이스·네이버 = 이 포스팅은, 토스 = 이 콘텐츠는)


def split_title(text):
    """(제목, 제목 아래 본문, 잘라낸 UTF-16 길이). 본문에 제목이 한 번 더 나오지 않게 제목 줄까지 잘라냄."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        t = re.sub(r"^[^\w가-ퟣ\[]+", "", line).strip()  # 앞 이모지 제거
        if t and not t.startswith(NOTE_STARTS):  # 대가성 문구 줄(쿠팡·토스·기타 제휴)은 제목이 아님
            rest = "\n".join(lines[i + 1:]).lstrip("\n")
            return t, rest, (len(text.encode("utf-16-le")) - len(rest.encode("utf-16-le"))) // 2
    return TITLE, text, 0


def title_of(text):
    return split_title(text)[0]


def page(title, body, desc="", canonical="", gb=True):
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><meta name="description" content="{html.escape(desc[:150])}">
<meta name="naver-site-verification" content="31caccebc9de97ffa6547f7d55966278daf9c469">
<meta property="og:title" content="{html.escape(title)}"><meta property="og:description" content="{html.escape(desc[:150])}"><meta property="og:type" content="website">
{f'<meta property="og:url" content="{canonical}"><link rel="canonical" href="{canonical}">' if canonical else ''}<link rel="alternate" type="application/rss+xml" title="{TITLE}" href="{BASE}rss.xml"><style>{CSS}</style></head><body><main>
<header><h1><a href="{BASE}">🔥 {TITLE}</a></h1><a class="lk" href="{BASE}#saved" aria-label="찜한 딜 보기"><svg viewBox="0 0 24 24" aria-hidden="true">{ICONS["saved"]}</svg>찜<b id="lc"></b></a><div class="sub">매일 살 만한 핫딜만 골라드려요</div></header>
<p class="dis">{DISCLOSURE}</p>{GB_LINK if gb else ""}{body}
<a class="tg" href="{CHANNEL}">📲 텔레그램에서 실시간으로 받기</a>
<footer>딜 정보는 게시 시점 기준이며 가격·재고는 변동될 수 있어요.<br><a href="{BLOG}">네이버 블로그</a> · <a href="{INSTA}">인스타그램</a> · <a href="{THREADS}">Threads</a> · <a href="{CHANNEL}">텔레그램</a></footer></main></body></html>"""


GB_LINK = f'<a class="gb" href="{GOLDBOX}" rel="nofollow sponsored noopener" target="_blank">⏰ 쿠팡 골드박스 · 오늘의 하루 특가 보기</a>'
TOSS_HOSTS = ("toss.im", "toss.shopping")  # 쉐어링크 단축(toss.shopping/_m/.. — API·앱 발급 모두 이 모양, toss.im/_m/..)·원본(toss.shopping/t/..?k=)
NAVER_HOSTS = ("naver.me",)  # 쇼핑커넥트 '링크 발급' 주소 (naver.me 단축)
OY_HOSTS = ("oy.run",)  # 올리브영 쇼핑 큐레이터 링크(10/10 진우 가입, 앱에서 발급)
AFF_HOSTS = ("click.linkprice.com", "lpweb.kr", "linkmoa.kr", "lase.kr", "bestmore.net", "newtip.net", "s.click.aliexpress.com")  # 쿠팡(link.coupang.com) 외 제휴 링크 도메인


def parse(title):
    """'[롯데온] 삼양 파스타 32봉 (14,490원/무료)' -> ('롯데온', '삼양 파스타 32봉', '14,490원/무료')"""
    store = re.match(r"\s*\[(.+?)\]", title)
    prices = re.findall(r"\(([^()]*원[^()]*)\)", title)  # 괄호 안에 '원' 들어간 마지막 묶음 = 가격
    name = title[store.end():] if store else title
    if prices:
        name = name.replace(f"({prices[-1]})", " ")
    elif tail := re.search(r"\s*/\s*(\d[\d,]*\s*원.*)$", name):  # 루리웹식 '…1개/ 9,730원' 꼬리(10/8 카드 03번에 가격이 제목에 붙어 나옴)
        prices, name = [tail.group(1)], name[:tail.start()]
    return (store.group(1) if store else "", re.sub(r"\s+", " ", name).strip() or title, prices[-1] if prices else "")


SAVE_STORES = r"쿠팡|네이버|G마켓|지마켓|11번가|이마트|롯데온|올리브영|오늘의집|컬리|토스"


def saving(text):
    """글의 비교 문장 -> ('쿠팡', '7,210원'): '쿠팡 같은 상품(18,200원)보다 7,210원 쌈'(진우 링크 글·Claude 코멘트). 없으면 None (10/11 진우 '얼마나 싼지')."""
    m = re.search(rf"({SAVE_STORES})[^\n—]*?보다\s*([\d,]+원)\s*쌈", text)
    return m and (m.group(1), m.group(2))


def unit_of(p):
    """단위가격: Claude가 매긴 unit, 없으면 글의 '💡 단위가격: 10매당 31원 — …' 줄 앞부분."""
    m = re.search(r"💡 단위가격:?\s*([^—\n]+)", p["text"])
    return p.get("unit") or (m.group(1).strip() if m else "")


def buy_label(title):
    """구매 버튼에 가격(10/10 진우 'UI 편하게' → 가격·구매 먼저): '[쿠팡] 휴지 (9,900원/무료)' -> '🛒 9,900원 구매하기'. 가격 모르면 예전 문구."""
    m = re.search(r"\d[\d,]*\s*원", parse(title)[2])
    return f"🛒 {m.group(0).replace(' ', '')} 구매하기" if m else "🛒 구매하러 가기"


def toss_share(url):
    """토스 쉐어링크(수수료)인지: 단축(/_m/) 또는 원본(/t/번호?k=). k= 없는 상품 주소(/t/번호)는 아님 — 발급 실패로 사본용으로 남은 주소(10/9 확인)."""
    p = urllib.parse.urlsplit(url or "")
    return p.netloc in TOSS_HOSTS and (p.path.startswith("/_m/") or "k" in urllib.parse.parse_qs(p.query))


def aff(url):
    """제휴(수수료) 링크인지: 쿠팡 파트너스·토스 쉐어링크·네이버 쇼핑커넥트·링크프라이스 등."""
    host = urllib.parse.urlsplit(url or "").netloc
    return host == "link.coupang.com" or toss_share(url) or host in NAVER_HOSTS + AFF_HOSTS + OY_HOSTS


def day_deals(posts, day):
    """그날 딜의 카드 순서 [(posts 번호, 글)]: 점수 높은 순, 같은 점수면 제휴 링크 딜 먼저(10/8 진우 '쿠팡·토스 잘 팔리게'), 그다음 게시 순.
    카드(앞 5개)·인스타 캡션(앞 6개)·릴스(앞 3개)·사이트 맨 위 카드 딜 번호가 모두 이 순서."""
    ds = [(i, p) for i, p in enumerate(posts) if p["t"].startswith(day) and not p["text"].startswith("📋")]
    return sorted(ds, key=lambda x: (-x[1].get("s", 0), not aff(x[1].get("url")), x[1]["t"]))


def card_order(posts, day, out="docs"):
    """카드 번호 순서: 카드를 만들 때 정해 둔 순서(docs/cards/날짜.json = posts 번호 목록)가 있으면 그대로 — 카드가 나간 뒤 딜이 더 올라오거나
    점수가 바뀌어도 인스타 카드·캡션과 사이트 번호가 안 어긋남. 없으면 day_deals."""
    f = f"{out}/cards/{day}.json"
    return [(i, posts[i]) for i in json.load(open(f)) if i < len(posts)] if os.path.exists(f) else day_deals(posts, day)

COMMUNITY = ("ppomppu.co.kr", "ruliweb.com", "clien.net")  # 구매 버튼이 커뮤니티 원글인 딜(상품 주소를 못 꺼냄) -> 원글이 지워지면 안 열림(10/8 01번)


def community(url):
    return urllib.parse.urlsplit(url or "").netloc.endswith(COMMUNITY)


def find_url(title):
    """원글이 지워져도 살 길: 네이버쇼핑 검색('[몰]'·가격 괄호·'/ 가격' 꼬리 뺀 상품명)."""
    q = " ".join(re.sub(r"\[[^\]]*\]|\([^()]*\)|/\s*\d[\d,]*\s*원.*$", " ", title).split())
    return "https://search.shopping.naver.com/search/all?query=" + urllib.parse.quote(q[:60])


def card_picks(posts, out):
    """홈 맨 위: 가장 최근 인스타·Threads 카드의 딜을 카드와 같은 번호로, 누르면 바로 구매 페이지(인스타 캡션 링크는 안 눌려서 프로필 링크 -> 여기서 한 번에, 10/8 진우)."""
    days = sorted(f[:-4] for f in os.listdir(f"{out}/cards") if f.endswith(".png")) if os.path.isdir(f"{out}/cards") else []
    picks = card_order(posts, days[-1], out)[:6] if days else []  # 카드·캡션에 나온 6개만(나머지는 아래 격자) — 스크롤 짧게
    if not picks:
        return ""
    rows = "".join(f'<a class="pick" href="{html.escape(p.get("url") or f"{BASE}p/{i}.html")}" rel="nofollow sponsored noopener" target="_blank" '
                   f'aria-label="{n}번 {html.escape(title_of(p["text"]))} {"원글에서 구매 링크 보기" if community(p.get("url")) else "구매하러 가기"}">'
                   f'<b>{n:02d}</b><span>{html.escape(title_of(p["text"]))}</span><em>{"원글 →" if community(p.get("url")) else "구매 →"}</em></a>'
                   + (f'<a class="alt" href="{html.escape(find_url(title_of(p["text"])))}" rel="nofollow noopener" target="_blank">🔎 {n}번 원글이 안 열리면 같은 상품 찾기</a>'
                      if community(p.get("url")) else "")
                   for n, (i, p) in enumerate(picks, 1))
    m, d = days[-1][5:7].lstrip("0"), days[-1][8:].lstrip("0")
    return (f'<section class="card" id="today" aria-labelledby="today-h"><h2 id="today-h">📸 {m}월 {d}일 카드 딜</h2>'
            f'<div class="t">번호를 누르면 바로 구매 페이지로 가요 · 인스타·Threads 카드 번호와 같아요</div>{rows}</section>')


def react(p):
    """반응 수치 글자(게시 때 뽐뿌·클리앙 수치, 10/9~): '분당 조회 13.5회 · 추천 1'. 10/9 이 표시 배포 전 글은 합친 값(pop)만 있어서 '반응 18.5'."""
    if p.get("vpm") is not None:
        return f"분당 조회 {p['vpm']:g}회" + (f" · 추천 {p['rec']}" if p.get("rec") else "")
    return f"반응 {p['pop']:g}" if p.get("pop") else ""


BRAND = r"설화수|더\s?후|헤라|라네즈|아이오페|이니스프리|에스티\s?로더|랑콤|키엘|SK-?II|디올|샤넬|조말론|라로슈포제|아벤느|피지오겔|세타필|닥터지|다이슨|필립스|브라운|나이키|아디다스"  # 이름 있는 브랜드(10/10 진우 '브랜딩 파워 있는 제품도 꼭')
FOOD = r"쌀|라면|햇반|생수|샘물|우유|계란|달걀|구운란|특란|삼겹|목살|한우|갈비|닭|족발|감귤|사과|망고|바나나|단감|반시|양파|과일|김치|만두|떡|커피|콜드브루|음료|소다|주스|과자|초코|견과|새우|오징어|감자탕|소스|올리브|파운드"


def badges(p):
    """카드 배지(10/10 진우 'UI 편하게'): 🏆 인기(커뮤니티 반응, 10/11 몰·시각 줄에서 옮김 — 좁은 칸에서 시각이 잘려서) · 본사 정품(예약 글 tag) · 오늘 밤 12시 마감(토스 선착순특가, 오늘 올린 글만) · 약한 딜."""
    today = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600))
    return ([("b4", "🏆 인기")] if p.get("hot") else []) + ([("b1", "✅ 본사 정품")] if p.get("tag") == "정품" else []) + ([("b2", "⏰ 오늘 밤 12시 마감")] if "밤 12시까지" in p["text"] and p["t"][:10] == today else []) \
        + ([("b3", "🛒 약한 딜")] if "특가로는 약한 제품" in p["text"] else [])


def end_at(p):
    """토스 선착순특가 마감 = 올린 날 밤 12시(KST) -> epoch 초 (배지가 '마감까지 1시간 25분'으로 줄어듦, END_JS)."""
    return calendar.timegm(time.strptime(p["t"][:10], "%Y-%m-%d")) + 86400 - 9 * 3600


def badge_html(p, skip=()):
    return "".join(f'<b class="{c}"' + (f' data-end="{end_at(p)}"' if c == "b2" else "") + f">{t}</b>" for c, t in badges(p) if c not in skip)


END_JS = """<script>(function(){function f(){var n=Date.now()/1000;[].forEach.call(document.querySelectorAll('[data-end]'),function(b){var s=b.dataset.end-n,h=Math.floor(s/3600),m=Math.floor(s%3600/60);
b.textContent=s<=0?'⏰ 마감됐어요':s<60?'⏰ 곧 마감':'⏰ 마감까지 '+(h?h+'시간 ':'')+m+'분'})}f();setInterval(f,30000)})()</script>"""


def keys(p):
    """검색 칩 필터용 키(data-k): 몰(쿠팡·토스) · 생필품·식품·화장품 · 브랜드 · 마감."""
    title = title_of(p["text"])
    store = parse(title)[0]
    return " ".join([k for k in ("쿠팡", "토스") if k in store] + [n.split()[-1] for _, n, rx in CATS if re.search(rx, title)]
                    + (["식품"] if re.search(FOOD, title) else []) + (["브랜드"] if p.get("tag") == "정품" or re.search(BRAND, title) else [])
                    + (["마감"] if any(c == "b2" for c, _ in badges(p)) else []))


def grid_item(i, p, rx=False):
    """격자 칸 1개: 몰·이름(3줄까지)·가격·단위가격·(rx면 반응 수치)·버튼(제휴·쇼핑몰 = 구매, 원글 = 원글 + 같은 상품 찾기, 주소 없음 = 자세히)."""
    title = title_of(p["text"])
    store, name, price = parse(title)
    page_url, url = f"{BASE}p/{i}.html", p.get("url")
    if community(url):
        go = (f'<a class="o" href="{html.escape(url)}" rel="nofollow noopener" target="_blank" aria-label="{html.escape(name)} 원글에서 구매 링크 보기">원글 →</a>'
              f'<a class="f" href="{html.escape(find_url(title))}" rel="nofollow noopener" target="_blank" aria-label="{html.escape(name)} 같은 상품 찾기">🔎 같은 상품 찾기</a>')
    elif url:
        go = f'<a href="{html.escape(url)}" rel="nofollow sponsored noopener" target="_blank" aria-label="{html.escape(name)} 구매하러 가기">구매 →</a>'
    else:
        go = f'<a class="o" href="{page_url}" aria-label="{html.escape(name)} 자세히 보기">자세히 →</a>'
    bd, sv, u = badge_html(p, ("b4",) if rx else ()), saving(p["text"]), unit_of(p)  # '반응 좋은 딜' 칸에선 🏆 배지가 겹쳐서 뺌
    return (f'<article class="g" data-k="{html.escape(keys(p))}"><button class="like" type="button" data-i="{i}" aria-pressed="false" aria-label="{html.escape(name)} 찜"><svg viewBox="0 0 24 24" aria-hidden="true">{ICONS["saved"]}</svg></button><div class="s">{html.escape(store) or "핫딜"} · {p["t"][11:16]}</div>'
            + (f'<div class="bd">{bd}</div>' if bd else "") + f'<h3><a href="{page_url}">{html.escape(name)}</a></h3>' + (f'<div class="pr">{html.escape(price.split("/")[0].strip())}</div>' if price else "")
            + (f'<div class="sv">{sv[0]}보다 {sv[1]}↓</div>' if sv else "") + (f'<div class="u">{html.escape(u)}</div>' if u else "")
            + (f'<div class="rx">👀 {html.escape(react(p).replace("분당 조회 ", "분당 "))}</div>' if rx and react(p) else "") + f'<div class="go">{go}</div></article>')


def hot_section(posts, days):
    """홈 맨 위 '지금 반응 좋은 딜'(10/9 진우): 최근 2일 커뮤니티 딜 중 반응(pop = 게시 때 분당 조회수 + 추천×5) 높은 6개. 반응 수치가 쌓이기 전엔 안 보임."""
    ds = sorted(((i, p) for i, p in enumerate(posts) if p["t"][:10] in days[:2] and p.get("pop")), key=lambda x: -x[1]["pop"])[:6]
    return (f'<section class="day" id="hot" aria-labelledby="hoth"><h2 id="hoth">🏆 지금 반응 좋은 딜</h2><div class="t">뽐뿌·클리앙 조회수·추천 기준</div>'
            f'<div class="grid">{"".join(grid_item(i, p, True) for i, p in ds)}</div></section>') if len(ds) >= 2 else ""


CATS = (("life", "🧻 생필품", r"휴지|화장지|티슈|키친타[월올]|세제|유연제|퍼실|다우니|피죤|스너글|샴푸|린스|컨디셔너|트리트먼트|바디워시|핸드워시|손세정|비누|치약|칫솔|가글"
                              r"|리스테린|생리대|라이너|기저귀|면도|마스크(?!팩)|KF\d|크린랩|위생[백랩장]|니트릴|지퍼백|쿠킹호일|종량제|쓰레기봉투|수세미|고무장갑|행주|탈취|방향제"
                              r"|페브리즈|제습제|건전지|락스|세정제"),
        ("beauty", "💄 화장품", r"화장품|올리브영|스킨케어|토너|에센스|세럼|앰플|로션|[수영]분크림|아이크림|선크림|핸드크림|바디크림|재생크림|선케어|선스틱|선쿠션|자외선"
                               r"|클렌징|클렌저|폼클렌|마스크팩|시트팩|토너패드|각질|화장솜|립스틱|립밤|립글로|틴트|쿠션팩트|에어쿠션|파운데이션|컨실러|미스트|향수|메이크업"
                               r"|마스카라|아이섀도|네일|올인원"))  # 제목 키워드(10/9 실제 딜 121개로 맞춤 — 크림·팩·쿠션·립·패드 단독은 음식·가구랑 겹쳐서 뺌)


def cat_sections(posts, days):
    """홈 품목별 칸(10/9 진우 '생필품 화장품이 있음 좋겠어'): 최근 3일 딜 중 제목 키워드(CATS)로 고른 최신 6개. 없으면 칸·탭 없음.
    posts.json = 커뮤니티 딜만이라 토스 API 상품은 안 들어감(승인 범위). -> [(id, 이름, 칸 HTML 또는 빈 값)]"""
    out = []
    for key, name, rx in CATS:
        ds = [(i, p) for i, p in enumerate(posts) if p["t"][:10] in days[:3] and not p["text"].startswith("📋") and re.search(rx, title_of(p["text"]))][::-1][:6]
        out.append((key, name, ds and f'<section class="day" id="{key}" aria-labelledby="{key}h"><h2 id="{key}h">{name}</h2><div class="t">최근 3일 · 최신 순</div>'
                                      f'<div class="grid">{"".join(grid_item(i, p) for i, p in ds)}</div></section>'))
    return out


def toss_section(posts, days):
    """홈 '토스' 칸(10/9 진우 '쿠팡·토스 주력'): 최근 2일 커뮤니티 딜 중 토스 쉐어링크가 붙은 것(최신 6개) + 텔레그램 토스 추천 버튼.
    토스 API 상품(베스트·하루특가)은 사이트에 안 올림 — API 승인 범위가 채널·Threads(신청서 '사이트 전시·가격 비교 안 함')라서 버튼으로 채널에 보냄."""
    ds = [(i, p) for i, p in enumerate(posts) if p["t"][:10] in days[:2] and not p["text"].startswith("📋")
          and toss_share(p.get("url"))][::-1][:6]
    return (f'<section class="day" id="toss" aria-labelledby="tossh"><h2 id="tossh">💙 토스 딜{f" {len(ds)}개" if ds else ""}</h2>'
            + (f'<div class="grid">{"".join(grid_item(i, p) for i, p in ds)}</div>' if ds else "")
            + f'<a class="btn2" href="{CHANNEL_WEB}" rel="noopener" target="_blank">🧺 토스 베스트·하루특가 추천 보기 (텔레그램)</a></section>')


def brand_section(posts, days):
    """홈 '✨ 정품·브랜드' 칸(10/10 진우 '브랜딩 파워 있는 제품도 꼭, 정품도'): 최근 3일 딜 중 본사 정품 표시(tag)·이름 있는 브랜드(BRAND) 최신 8개."""
    ds = [(i, p) for i, p in enumerate(posts) if p["t"][:10] in days[:3] and not p["text"].startswith("📋")
          and (p.get("tag") == "정품" or re.search(BRAND, title_of(p["text"])))][::-1][:8]
    return ds and (f'<section class="day" id="brand" aria-labelledby="brandh"><h2 id="brandh">✨ 정품·브랜드 딜</h2><div class="t">최근 3일 · 판매자(본사 정품 여부)는 배지·상세에서 확인</div>'
                   f'<div class="grid">{"".join(grid_item(i, p) for i, p in ds)}</div></section>')


def day_grids(posts, days):
    """날짜별 2열 격자. 날짜 안에서는 제휴 링크 딜(쿠팡·토스 등) 먼저, 그다음 최신 순(10/8 진우 '쿠팡·토스 먼저', '모바일 격자')."""
    out = []
    for n, day in enumerate(days):
        ds = sorted(((i, p) for i, p in enumerate(posts) if p["t"].startswith(day) and not p["text"].startswith("📋")),
                    key=lambda x: (not aff(x[1].get("url")), [-ord(c) for c in x[1]["t"]]))
        out.append(f'<section class="day" id="d{n}" aria-labelledby="d{n}h"><h2 id="d{n}h">{int(day[5:7])}월 {int(day[8:])}일 딜 {len(ds)}개</h2>'
                   f'<div class="grid">{"".join(grid_item(i, p) for i, p in ds)}</div></section>')
    return "".join(out)


# 홈 = 한 칸씩(10/9 진우 '홈페이지가 정신이 없네' → 아래 고정 바 + 누른 칸만). 주소 #id가 든 칸만 보이고, 없으면 첫 칸(인스타·Threads에서 왔으면 카드 딜). JS가 꺼져 있으면 전부 보임(예전처럼)
ICONS = {  # 아래 바 아이콘 = Lucide(ISC 라이선스) 선 아이콘 — 이모지는 기기마다 모양·색이 달라 산만해서(10/9 진우 '심플하고 이쁘게')
    "hot": '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
    "today": '<path d="M10 12h11"/><path d="M10 18h11"/><path d="M10 6h11"/><path d="M4 10h2"/><path d="M4 6h1v4"/><path d="M6 18H4c0-1 2-2 2-3s-1-1.5-2-1"/>',
    "toss": '<path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/>',
    "life": '<path d="M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z"/><path d="M12 22V12"/><path d="m3.3 7 7.703 4.734a2 2 0 0 0 1.994 0L20.7 7"/><path d="m7.5 4.27 9 5.15"/>',
    "beauty": '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/><path d="M20 3v4"/><path d="M22 5h-4"/><path d="M4 17v2"/><path d="M5 18H3"/>',
    "brand": '<path d="M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z"/><path d="m9 12 2 2 4-4"/>',
    "saved": '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>',
    "days": '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/><path d="M8 14h.01"/><path d="M12 14h.01"/><path d="M16 14h.01"/><path d="M8 18h.01"/><path d="M12 18h.01"/><path d="M16 18h.01"/>'}
PANE_JS = """<script>(function(){var ps=[].slice.call(document.querySelectorAll('.pane'));if(!ps.length)return;
function show(){var e=location.hash&&document.getElementById(decodeURIComponent(location.hash.slice(1))),t=document.getElementById('today'),ig=/instagram|threads/i.test(document.referrer)||/[?&](fbclid|igsh|utm_source=(ig|threads))/.test(location.search),
p=e&&e.closest('.pane')||ig&&t&&t.parentNode||ps[0];
ps.forEach(function(x){x.hidden=x!==p});[].forEach.call(document.querySelectorAll('.bar a'),function(a){a.setAttribute('aria-current',p.contains(document.getElementById(a.hash.slice(1)))?'true':'false')});
if(e&&e.parentNode!==p)e.scrollIntoView();else scrollTo(0,0)}addEventListener('hashchange',show);show()})()</script>"""

# 찜(10/9 진우 '핫딜도 장바구니처럼' → 쇼핑몰마다 결제가 달라 한 번에 결제는 안 되고 모아 두기만): 카드 하트 -> 이 브라우저(localStorage)에 카드째 저장(최대 50개),
# 맨 위 '찜 N' -> 홈 '찜한 딜' 칸. 로그인·서버 저장 없음(다른 기기와 공유 X). 저장이 막힌 브라우저(사생활 모드 등)에선 그 화면에서만 유지
SAVED = ('<section class="day" id="saved" aria-labelledby="savedh"><h2 id="savedh">❤️ 찜한 딜</h2><div class="t">이 폰(브라우저)에만 저장돼요 · 가격은 올린 때 기준이라 바뀌었을 수 있어요</div>'
         '<div class="grid" id="savedg"></div><p id="saved0">아직 찜한 딜이 없어요. 딜 카드의 하트를 누르면 여기 모여요.</p></section>')
LIKE_JS = """<script>(function(){var L;try{L=JSON.parse(localStorage.getItem('likes'))||[]}catch(e){L=[]}
function has(i){return L.some(function(x){return x.i===i})}
function sync(){[].forEach.call(document.querySelectorAll('.like'),function(b){b.setAttribute('aria-pressed',has(b.dataset.i)?'true':'false')});
var c=document.getElementById('lc'),g=document.getElementById('savedg');if(c)c.textContent=L.length?' '+L.length:'';
if(g){g.innerHTML=L.map(function(x){return x.h}).join('');document.getElementById('saved0').hidden=L.length>0;[].forEach.call(g.querySelectorAll('.like'),function(b){b.setAttribute('aria-pressed','true')})}}
document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('.like');if(!b)return;var i=b.dataset.i;
L=has(i)?L.filter(function(x){return x.i!==i}):[{i:i,h:b.closest('.g').outerHTML}].concat(L).slice(0,50);try{localStorage.setItem('likes',JSON.stringify(L))}catch(e){}sync()});sync()})()</script>"""

# 검색·필터(10/10 진우 'UI 편하게'): 맨 위 고정 검색창 + 칩. 홈은 '전체' 칸(최근 2일), all.html은 전체 딜에서 걸러 보여 줌. JS가 꺼져 있으면 그냥 안 걸러짐
CHIPS = (("쿠팡", "쿠팡"), ("토스", "토스"), ("생필품", "🧻 생필품"), ("식품", "🍚 식품"), ("화장품", "💄 화장품"), ("브랜드", "✨ 브랜드"), ("마감", "⏰ 오늘 마감"))
FIND = ('<div class="find" role="search"><input id="q" type="search" placeholder="🔎 딜 검색 (예: 휴지, 설화수)" aria-label="딜 검색" autocomplete="off">'
        '<div class="chips">' + "".join(f'<button type="button" data-c="{k}" aria-pressed="false">{n}</button>' for k, n in CHIPS) + '</div><div id="qn" class="t" hidden></div></div>')
FIND_JS = """<script>(function(){var q=document.getElementById('q');if(!q)return;var cs=[].slice.call(document.querySelectorAll('.chips button')),c='',qn=document.getElementById('qn'),host=document.getElementById('days')||document.body;
function run(){var v=q.value.trim().toLowerCase(),on=!!(v||c),n=0;if(on)[].forEach.call(document.querySelectorAll('.pane'),function(p){p.hidden=!p.contains(host)});
[].forEach.call(host.querySelectorAll('.g'),function(g){var ok=!on||(!v||g.textContent.toLowerCase().indexOf(v)>=0)&&(!c||(' '+g.dataset.k+' ').indexOf(' '+c+' ')>=0);g.hidden=!ok;if(ok&&on)n++});
[].forEach.call(host.querySelectorAll('.day'),function(s){s.hidden=on&&!s.querySelector('.g:not([hidden])')});qn.hidden=!on;qn.textContent=n?n+'개 찾았어요':'찾는 딜이 없어요 · 다른 말로 찾아보세요';
if(!on)dispatchEvent(new HashChangeEvent('hashchange'))}
q.addEventListener('input',run);cs.forEach(function(b){b.addEventListener('click',function(){c=c===b.dataset.c?'':b.dataset.c;cs.forEach(function(x){x.setAttribute('aria-pressed',x.dataset.c===c?'true':'false')});run()})});
addEventListener('hashchange',function(){if(q.value||c){q.value='';c='';cs.forEach(function(x){x.setAttribute('aria-pressed','false')});run()}})})()</script>"""


def related(i, p, pool, n=4):
    """딜 페이지 아래 '같이 보면 좋은 딜'(10/11 진우 '더 사고 싶게'): pool(최근 2일 제휴 링크 딜, 약한 딜 빼고) 중 같은 품목 먼저, 그다음 최신. 같은 이름 제외.
    쿠팡은 클릭 후 24시간 안 산 건 다 실적 -> 들어온 사람이 한 번 더 둘러보게."""
    me, k = title_of(p["text"]), set(keys(p).split()) - {"쿠팡", "토스", "마감"}
    c = sorted(((j, q, ks) for j, q, ks in pool if j != i and title_of(q["text"]) != me), key=lambda x: x[1]["t"], reverse=True)
    return [(j, q) for j, q, _ in sorted(c, key=lambda x: -len(k & x[2]))[:n]]


def deal_card(i, p):
    """딜 페이지 본문(10/11 진우 '더 사고 싶게'): 몰·시각 -> 배지 -> 이름 -> 가격·얼마나 싼지·단위가격 -> 큰 구매 버튼 -> 왜 골랐나요(코멘트·확인할 점)."""
    title, rest, cut = split_title(p["text"])
    store, name, price = parse(title)
    body = to_html(rest, [{**e, "offset": e["offset"] - cut} for e in p.get("entities") or [] if e["offset"] >= cut])
    url, sv, u = f"{BASE}p/{i}.html", saving(p["text"]), unit_of(p)
    if community(p.get("url")):  # 원글로 가는 버튼이면 이름을 정확히 + 원글이 지워져도 찾을 수 있게
        btn = (f'<a class="btn" href="{html.escape(p["url"])}" rel="nofollow noopener" target="_blank">📄 원글에서 구매 링크 보기</a>'
               f'<a class="btn2" href="{html.escape(find_url(title))}" rel="nofollow noopener" target="_blank">🔎 원글이 안 열리면 같은 상품 찾기</a>')
    else:
        btn = f'<a class="btn" href="{html.escape(p["url"])}" rel="nofollow sponsored noopener" target="_blank">{buy_label(title)}</a>' if p.get("url") else ""
    main, _, ship = price.partition("/")
    ship = {"무료": "무료배송", "무배": "무료배송"}.get(ship.strip(), ship.strip())
    hero = ((f'<div class="hero"><span class="pr">{html.escape(main.strip())}</span>' + (f'<span class="ship">{html.escape(ship.strip())}</span>' if ship.strip() else "")
             + (f'<span class="sv">{sv[0]}보다 {sv[1]}↓</span>' if sv else "") + "</div>") if price else "") + (f'<div class="u">{html.escape(u)}</div>' if u else "")
    bd = badge_html(p)
    return (f'<article class="card deal"><div class="s">{html.escape(store or "핫딜")} · {int(p["t"][5:7])}월 {int(p["t"][8:10])}일 {p["t"][11:16]}</div>'
            + (f'<div class="bd">{bd}</div>' if bd else "") + f'<h2><a href="{url}">{html.escape(name if price else title)}</a></h2>{hero}{btn}'
            + (f'<p class="note">가격·재고는 바뀔 수 있어요 · 결제 전 최종가 확인</p>' if btn else "") + f'<h3 class="why">왜 골랐나요</h3><p>{body}</p></article>')


def summary(text):
    """검색 결과·RSS에 보일 설명: 제목 아래 코멘트 줄들(출처·🏆 배지 줄 빼고 한 줄로). 대가성 문구·제목 반복은 안 넣음(10/9 '구글·네이버 조회가 잘 안 돼')."""
    return " ".join(l.strip() for l in split_title(text)[1].split("\n") if l.strip() and not l.startswith(("출처:", "🏆 인기")))[:150]


def build(posts, out="docs"):
    os.makedirs(f"{out}/p", exist_ok=True)
    open(f"{out}/.nojekyll", "w").close()
    open(f"{out}/CNAME", "w").write(BASE.split("/")[2])  # GitHub Pages 커스텀 도메인 (재생성 때 안 날아가게)
    latest = posts[-1]["t"][:10] if posts else ""
    urls = [(BASE, latest)]
    days = sorted({p["t"][:10] for p in posts if not p["text"].startswith("📋")}, reverse=True)
    pool = [(j, q, set(keys(q).split())) for j, q in enumerate(posts) if q["t"][:10] in days[:2] and not q["text"].startswith("📋")
            and aff(q.get("url")) and "특가로는 약한 제품" not in q["text"]]
    for i, p in reversed(list(enumerate(posts))):
        title, url, rel = title_of(p["text"]), f"{BASE}p/{i}.html", related(i, p, pool)
        more = rel and f'<section class="day rel" aria-labelledby="relh"><h2 id="relh">같이 보면 좋은 딜</h2><div class="grid">{"".join(grid_item(j, q) for j, q in rel)}</div></section>'
        open(f"{out}/p/{i}.html", "w").write(page(f"{title} | {TITLE}", deal_card(i, p) + (more or "") + GB_LINK + LIKE_JS + END_JS, summary(p["text"]) or title, url, gb=False))
        urls.append((url, p["t"][:10]))
    panes = [("hot", "🏆 인기", hot_section(posts, days)), ("today", "📸 카드", card_picks(posts, out)), ("toss", "💙 토스", toss_section(posts, days)), ("brand", "✨ 브랜드", brand_section(posts, days)),
             *cat_sections(posts, days), ("days", "📅 전체", f'<div id="days">{day_grids(posts, days[:2]) or "<p>첫 딜을 준비 중이에요.</p>"}'
                                                          f'<a class="btn2" href="{BASE}all.html">지난 딜 전체 보기 →</a></div>'), ("saved", "❤️ 찜", SAVED)]
    panes = [p for p in panes if p[2]]
    bar = lambda home: ('<nav class="bar" aria-label="바로가기">' + "".join(f'<a href="{home}#{k}"><svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[k]}</svg>{n.split()[-1]}</a>' for k, n, _ in panes if k != "saved") + "</nav>")  # 찜은 맨 위 '찜' 버튼으로
    ld = json.dumps({"@context": "https://schema.org", "@graph": [{"@type": "WebSite", "name": TITLE, "url": BASE, "inLanguage": "ko"},
                                                                  {"@type": "Organization", "name": TITLE, "url": BASE, "sameAs": [INSTA, THREADS, BLOG, CHANNEL]}]}, ensure_ascii=False)
    open(f"{out}/index.html", "w").write(page(f"{TITLE} - 오늘의 핫딜·특가 모음 (쿠팡·네이버·토스)", f'<script type="application/ld+json">{ld}</script>' + FIND + "".join(f'<div class="pane"{" hidden" * (k == "saved")}>{h}</div>' for k, _, h in panes) + bar("") + PANE_JS + LIKE_JS + FIND_JS + END_JS,  # 홈에선 #칸만(인스타 ?fbclid 붙어 와도 새로 안 불러옴)
                                              "뽐뿌·클리앙·루리웹에 올라온 핫딜 중 살 만한 것만 매일 골라 정리해요. 지금 반응 좋은 딜, 생필품·화장품, 토스 특가까지 한눈에.", BASE))
    open(f"{out}/all.html", "w").write(page(f"지난 딜 전체 | {TITLE}", FIND + bar(BASE) + day_grids(posts, days) + LIKE_JS + FIND_JS + END_JS, "핫딜픽에 올라온 딜 전체", f"{BASE}all.html"))
    urls.append((f"{BASE}all.html", latest))
    open(f"{out}/sitemap.xml", "w").write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                           + "".join(f"<url><loc>{u}</loc>{d and f'<lastmod>{d}</lastmod>'}</url>" for u, d in urls) + "</urlset>")
    open(f"{out}/robots.txt", "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}sitemap.xml\n")  # 검색 로봇에게 사이트맵 위치(10/9)
    items = [(i, p) for i, p in enumerate(posts) if not p["text"].startswith("📋")][-30:][::-1]  # 네이버 서치어드바이저 'RSS 제출'용 최근 딜 30개
    open(f"{out}/rss.xml", "w").write(
        f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{TITLE}</title><link>{BASE}</link><description>매일 살 만한 핫딜만 골라드려요</description><language>ko</language>'
        + "".join(f'<item><title>{html.escape(title_of(p["text"]))}</title><link>{BASE}p/{i}.html</link><guid>{BASE}p/{i}.html</guid>'
                  f'<description>{html.escape(summary(p["text"]))}</description><pubDate>{time.strftime("%a, %d %b %Y %H:%M:00 +0900", time.strptime(p["t"][:16], "%Y-%m-%d %H:%M"))}</pubDate></item>'
                  for i, p in items) + "</channel></rss>")
    return len(posts)


if __name__ == "__main__":
    posts = json.load(open("posts.json")) if os.path.exists("posts.json") else []
    print("site:", build(posts), "posts")
