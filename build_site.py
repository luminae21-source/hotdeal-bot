#!/usr/bin/env python3
"""posts.json(채널에 게시된 딜) -> docs/ 정적 사이트. GitHub Pages로 서빙. 외부 패키지 없음."""
import html, json, os, re, urllib.parse

BASE = "https://hotdealpick.kr/"
CHANNEL = "https://t.me/hotdeal_pick"
BLOG = "https://blog.naver.com/hotdeal_pick"
INSTA = "https://www.instagram.com/hotdealpick.kr/"
THREADS = "https://www.threads.com/@hotdealpick.kr"
GOLDBOX = "https://link.coupang.com/a/hBMtMDCxFY"  # 쿠팡 파트너스 간편 링크: 골드박스 페이지(coupang.com/np/goldbox), 10/6 생성. 클릭 후 24시간 안 쿠팡 구매가 실적
CHANNEL_WEB = "https://t.me/s/hotdeal_pick"  # 텔레그램 채널 웹 보기(앱 없이 열림)
TITLE = "핫딜픽"  # 브랜드 이름 (텔레그램·블로그·스레드·인스타·페이스북 모두 핫딜픽, 10/5 통일)
DISCLOSURE = "이 사이트는 쿠팡 파트너스·토스쇼핑 쉐어링크 등 제휴 마케팅 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받을 수 있습니다."
CSS = """*{box-sizing:border-box}body{margin:0;font:16px/1.6 -apple-system,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;background:#f6f7f9;color:#1c1e21}
a{color:#0b63ce}main{max-width:680px;margin:0 auto;padding:16px}header{padding:12px 0 4px}header h1{margin:0;font-size:22px}header h1 a{color:inherit;text-decoration:none}
.sub{color:#666;font-size:13px}.card{background:#fff;border-radius:12px;padding:16px;margin:12px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.card h2{margin:0 0 8px;font-size:17px;line-height:1.4}.card h2 a{color:inherit;text-decoration:none}.t{color:#888;font-size:12px}
.btn{display:block;text-align:center;background:#0b63ce;color:#fff;border-radius:10px;padding:12px;margin-top:12px;text-decoration:none;font-weight:600}
.gb{display:block;text-align:center;background:#fff4ec;color:#c2410c;border:1.5px solid #fdba74;border-radius:10px;padding:10px;margin:12px 0;text-decoration:none;font-weight:600}
.tg{display:block;text-align:center;background:#229ed9;color:#fff;border-radius:10px;padding:12px;margin:16px 0;text-decoration:none;font-weight:600}
.pick{display:flex;align-items:center;gap:12px;min-height:56px;padding:12px 14px;margin:8px 0;border-radius:12px;background:#fff4ec;border:1.5px solid #fdba74;color:#1c1e21;text-decoration:none;font-weight:600}.alt{display:block;margin:-4px 0 8px 56px;font-size:15px;padding:12px 0}.btn2{display:block;text-align:center;border:1.5px solid #0b63ce;color:#0b63ce;border-radius:10px;padding:11px;margin-top:8px;text-decoration:none;font-weight:600}.pick b{color:#e8590c;font-size:20px;min-width:30px}.pick span{flex:1;line-height:1.35}.pick em{font-style:normal;color:#c2410c;font-size:14px;white-space:nowrap}a:focus-visible{outline:3px solid #0b63ce;outline-offset:2px}
.tabs{position:sticky;top:0;z-index:5;display:flex;gap:8px;overflow-x:auto;background:#f6f7f9;padding:10px 0;margin:4px 0}.tabs a{flex:none;display:flex;align-items:center;min-height:44px;padding:0 16px;border-radius:22px;background:#fff;border:1px solid #d0d7de;color:#1c1e21;text-decoration:none;font-weight:600;font-size:15px}
.day h2{font-size:18px;margin:18px 2px 8px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.g{display:flex;flex-direction:column;background:#fff;border-radius:12px;padding:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);min-width:0}.g .s{font-size:12px;color:#888}.g .hot{color:#c2410c}.g h3{margin:4px 0 6px;font-size:15px;line-height:1.35;font-weight:600;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}.g h3 a{color:inherit;text-decoration:none}.g .pr{font-weight:800;font-size:17px}.g .u{font-size:12px;color:#c2410c}.g .go{margin-top:auto;padding-top:8px}.g .go a{display:flex;align-items:center;justify-content:center;min-height:44px;border-radius:10px;background:#0b63ce;color:#fff;text-decoration:none;font-weight:700;font-size:15px}.g .go a.o{background:none;border:1.5px solid #0b63ce;color:#0b63ce}.g .go a.f{min-height:40px;font-size:13px;background:none;color:#0b63ce;font-weight:600}
.dis{font-size:12px;color:#888;margin:8px 0}footer{font-size:12px;color:#888;text-align:center;padding:24px 0}
@media(prefers-color-scheme:dark){body{background:#111;color:#eee}.card{background:#1c1c1e}.sub,.t,.dis,footer{color:#999}a{color:#6cb0ff}.pick{background:#2a1f17;border-color:#9a3412;color:#eee}.pick em{color:#fdba74}.tabs{background:#111}.tabs a{background:#1c1c1e;border-color:#3a3a3c;color:#eee}.g{background:#1c1c1e}.g .go a.o,.g .go a.f{color:#6cb0ff;border-color:#6cb0ff}.g .u{color:#fdba74}.g .hot{color:#fdba74}}"""


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


def page(title, body, desc="", canonical=""):
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><meta name="description" content="{html.escape(desc[:150])}">
<meta name="naver-site-verification" content="31caccebc9de97ffa6547f7d55966278daf9c469">
<meta property="og:title" content="{html.escape(title)}"><meta property="og:description" content="{html.escape(desc[:150])}"><meta property="og:type" content="website">
{f'<meta property="og:url" content="{canonical}"><link rel="canonical" href="{canonical}">' if canonical else ''}<style>{CSS}</style></head><body><main>
<header><h1><a href="{BASE}">🔥 {TITLE}</a></h1><div class="sub">매일 살 만한 핫딜만 골라드려요</div></header>
<p class="dis">{DISCLOSURE}</p><a class="gb" href="{GOLDBOX}" rel="nofollow sponsored noopener" target="_blank">⏰ 쿠팡 골드박스 · 오늘의 하루 특가 보기</a>{body}
<a class="tg" href="{CHANNEL}">📲 텔레그램에서 실시간으로 받기</a>
<footer>딜 정보는 게시 시점 기준이며 가격·재고는 변동될 수 있어요.<br><a href="{BLOG}">네이버 블로그</a> · <a href="{INSTA}">인스타그램</a> · <a href="{THREADS}">Threads</a> · <a href="{CHANNEL}">텔레그램</a></footer></main></body></html>"""


TOSS_HOSTS = ("toss.im", "toss.shopping")  # 쉐어링크 단축(toss.shopping/_m/.. — API·앱 발급 모두 이 모양, toss.im/_m/..)·원본(toss.shopping/t/..?k=)
NAVER_HOSTS = ("naver.me",)  # 쇼핑커넥트 '링크 발급' 주소 (naver.me 단축)
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


def toss_share(url):
    """토스 쉐어링크(수수료)인지: 단축(/_m/) 또는 원본(/t/번호?k=). k= 없는 상품 주소(/t/번호)는 아님 — 발급 실패로 사본용으로 남은 주소(10/9 확인)."""
    p = urllib.parse.urlsplit(url or "")
    return p.netloc in TOSS_HOSTS and (p.path.startswith("/_m/") or "k" in urllib.parse.parse_qs(p.query))


def aff(url):
    """제휴(수수료) 링크인지: 쿠팡 파트너스·토스 쉐어링크·네이버 쇼핑커넥트·링크프라이스 등."""
    host = urllib.parse.urlsplit(url or "").netloc
    return host == "link.coupang.com" or toss_share(url) or host in NAVER_HOSTS + AFF_HOSTS


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


def grid_item(i, p):
    """격자 칸 1개: 몰·이름(3줄까지)·가격·단위가격·버튼(제휴·쇼핑몰 = 구매, 원글 = 원글 + 같은 상품 찾기, 주소 없음 = 자세히)."""
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
    return (f'<article class="g"><div class="s">{"<b class=hot>🏆 인기</b> " if p.get("hot") else ""}{html.escape(store) or "핫딜"} · {p["t"][11:16]}</div><h3><a href="{page_url}">{html.escape(name)}</a></h3>'
            + (f'<div class="pr">{html.escape(price.split("/")[0].strip())}</div>' if price else "")
            + (f'<div class="u">{html.escape(p["unit"])}</div>' if p.get("unit") else "") + f'<div class="go">{go}</div></article>')


def hot_section(posts, days):
    """홈 맨 위 '지금 반응 좋은 딜'(10/9 진우): 최근 2일 커뮤니티 딜 중 반응(pop = 게시 때 분당 조회수 + 추천×5) 높은 6개. 반응 수치가 쌓이기 전엔 안 보임."""
    ds = sorted(((i, p) for i, p in enumerate(posts) if p["t"][:10] in days[:2] and p.get("pop")), key=lambda x: -x[1]["pop"])[:6]
    return (f'<section class="day" id="hot" aria-labelledby="hoth"><h2 id="hoth">🏆 지금 반응 좋은 딜</h2><div class="t">뽐뿌·클리앙 조회수·추천 기준</div>'
            f'<div class="grid">{"".join(grid_item(i, p) for i, p in ds)}</div></section>') if len(ds) >= 2 else ""


CATS = (("life", "🧻 생필품", r"휴지|화장지|티슈|키친타[월올]|세제|유연제|퍼실|다우니|피죤|스너글|샴푸|린스|컨디셔너|트리트먼트|바디워시|핸드워시|손세정|비누|치약|칫솔|가글"
                              r"|리스테린|생리대|라이너|기저귀|면도|마스크(?!팩)|KF\d|크린랩|위생[백랩장]|니트릴|지퍼백|쿠킹호일|종량제|쓰레기봉투|수세미|고무장갑|행주|탈취|방향제"
                              r"|페브리즈|제습제|건전지|락스|세정제"),
        ("beauty", "💄 화장품", r"화장품|올리브영|스킨케어|토너|에센스|세럼|앰플|로션|[수영]분크림|아이크림|선크림|핸드크림|바디크림|재생크림|선케어|선스틱|선쿠션|자외선"
                               r"|클렌징|클렌저|폼클렌|마스크팩|시트팩|토너패드|각질|화장솜|립스틱|립밤|립글로|틴트|쿠션팩트|에어쿠션|파운데이션|컨실러|미스트|향수|메이크업"
                               r"|마스카라|아이섀도|네일|올인원"))  # 제목 키워드(10/9 실제 딜 121개로 맞춤 — 크림·팩·쿠션·립·패드 단독은 음식·가구랑 겹쳐서 뺌)


def cat_sections(posts, days):
    """홈 품목별 칸(10/9 진우 '생필품 화장품이 있음 좋겠어'): 최근 3일 딜 중 제목 키워드(CATS)로 고른 최신 6개. 없으면 칸·탭 없음.
    posts.json = 커뮤니티 딜만이라 토스 API 상품은 안 들어감(승인 범위). -> (칸 HTML, 탭 링크 HTML)"""
    out = tabs = ""
    for key, name, rx in CATS:
        ds = [(i, p) for i, p in enumerate(posts) if p["t"][:10] in days[:3] and not p["text"].startswith("📋") and re.search(rx, title_of(p["text"]))][::-1][:6]
        if ds:
            out += (f'<section class="day" id="{key}" aria-labelledby="{key}h"><h2 id="{key}h">{name}</h2><div class="t">최근 3일 · 최신 순</div>'
                    f'<div class="grid">{"".join(grid_item(i, p) for i, p in ds)}</div></section>')
            tabs += f'<a href="{BASE}#{key}">{name}</a>'
    return out, tabs


def toss_section(posts, days):
    """홈 '토스' 칸(10/9 진우 '쿠팡·토스 주력'): 최근 2일 커뮤니티 딜 중 토스 쉐어링크가 붙은 것(최신 6개) + 텔레그램 토스 추천 버튼.
    토스 API 상품(베스트·하루특가)은 사이트에 안 올림 — API 승인 범위가 채널·Threads(신청서 '사이트 전시·가격 비교 안 함')라서 버튼으로 채널에 보냄."""
    ds = [(i, p) for i, p in enumerate(posts) if p["t"][:10] in days[:2] and not p["text"].startswith("📋")
          and toss_share(p.get("url"))][::-1][:6]
    return (f'<section class="day" id="toss" aria-labelledby="tossh"><h2 id="tossh">💙 토스 딜{f" {len(ds)}개" if ds else ""}</h2>'
            + (f'<div class="grid">{"".join(grid_item(i, p) for i, p in ds)}</div>' if ds else "")
            + f'<a class="btn2" href="{CHANNEL_WEB}" rel="noopener" target="_blank">🧺 토스 베스트·하루특가 추천 보기 (텔레그램)</a></section>')


def day_grids(posts, days):
    """날짜별 2열 격자. 날짜 안에서는 제휴 링크 딜(쿠팡·토스 등) 먼저, 그다음 최신 순(10/8 진우 '쿠팡·토스 먼저', '모바일 격자')."""
    out = []
    for n, day in enumerate(days):
        ds = sorted(((i, p) for i, p in enumerate(posts) if p["t"].startswith(day) and not p["text"].startswith("📋")),
                    key=lambda x: (not aff(x[1].get("url")), [-ord(c) for c in x[1]["t"]]))
        out.append(f'<section class="day" id="d{n}" aria-labelledby="d{n}h"><h2 id="d{n}h">{int(day[5:7])}월 {int(day[8:])}일 딜 {len(ds)}개</h2>'
                   f'<div class="grid">{"".join(grid_item(i, p) for i, p in ds)}</div></section>')
    return "".join(out)


def build(posts, out="docs"):
    os.makedirs(f"{out}/p", exist_ok=True)
    open(f"{out}/.nojekyll", "w").close()
    open(f"{out}/CNAME", "w").write(BASE.split("/")[2])  # GitHub Pages 커스텀 도메인 (재생성 때 안 날아가게)
    urls = [BASE]
    for i, p in reversed(list(enumerate(posts))):
        title, rest, cut = split_title(p["text"])
        body = to_html(rest, [{**e, "offset": e["offset"] - cut} for e in p.get("entities") or [] if e["offset"] >= cut])
        btn = f'<a class="btn" href="{html.escape(p["url"])}" rel="nofollow noopener" target="_blank">🛒 구매하러 가기</a>' if p.get("url") else ""
        if community(p.get("url")):  # 원글로 가는 버튼이면 이름을 정확히 + 원글이 지워져도 찾을 수 있게
            btn = (f'<a class="btn" href="{html.escape(p["url"])}" rel="nofollow noopener" target="_blank">📄 원글에서 구매 링크 보기</a>'
                   f'<a class="btn2" href="{html.escape(find_url(title))}" rel="nofollow noopener" target="_blank">🔎 원글이 안 열리면 같은 상품 찾기</a>')
        url = f"{BASE}p/{i}.html"
        card = f'<article class="card"><div class="t">{p["t"]}</div><h2><a href="{url}">{html.escape(title)}</a></h2><p>{body}</p>{btn}</article>'
        open(f"{out}/p/{i}.html", "w").write(page(f"{title} | {TITLE}", card, p["text"], url))
        urls.append(url)
    days = sorted({p["t"][:10] for p in posts if not p["text"].startswith("📋")}, reverse=True)
    cats, cat_tabs = cat_sections(posts, days)
    tabs = (f'<nav class="tabs" aria-label="날짜별 딜"><a href="{BASE}#toss">💙 토스</a>{cat_tabs}' + "".join(f'<a href="{BASE}#d{n}">{int(d[5:7])}/{int(d[8:])}</a>' for n, d in enumerate(days[:2]))
            + f'<a href="{BASE}all.html">지난 딜 전체</a></nav>') if days else ""
    open(f"{out}/index.html", "w").write(page(f"{TITLE} - 오늘의 핫딜 모음", hot_section(posts, days) + card_picks(posts, out) + toss_section(posts, days) + cats + tabs + (day_grids(posts, days[:2]) or "<p>첫 딜을 준비 중이에요.</p>"),
                                              "매일 살 만한 핫딜만 골라드려요", BASE))
    open(f"{out}/all.html", "w").write(page(f"지난 딜 전체 | {TITLE}", tabs + day_grids(posts, days), "핫딜픽에 올라온 딜 전체", f"{BASE}all.html"))
    urls.append(f"{BASE}all.html")
    open(f"{out}/sitemap.xml", "w").write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                           + "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>")
    return len(posts)


if __name__ == "__main__":
    posts = json.load(open("posts.json")) if os.path.exists("posts.json") else []
    print("site:", build(posts), "posts")
