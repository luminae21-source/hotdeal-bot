#!/usr/bin/env python3
"""posts.json(채널에 게시된 딜) -> docs/ 정적 사이트. GitHub Pages로 서빙. 외부 패키지 없음."""
import html, json, os, re, urllib.parse

BASE = "https://hotdealpick.kr/"
CHANNEL = "https://t.me/hotdeal_pick"
BLOG = "https://blog.naver.com/hotdeal_pick"
INSTA = "https://www.instagram.com/hotdealpick.kr/"
THREADS = "https://www.threads.com/@hotdealpick.kr"
GOLDBOX = "https://link.coupang.com/a/hBMtMDCxFY"  # 쿠팡 파트너스 간편 링크: 골드박스 페이지(coupang.com/np/goldbox), 10/6 생성. 클릭 후 24시간 안 쿠팡 구매가 실적
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
.dis{font-size:12px;color:#888;margin:8px 0}footer{font-size:12px;color:#888;text-align:center;padding:24px 0}
@media(prefers-color-scheme:dark){body{background:#111;color:#eee}.card{background:#1c1c1e}.sub,.t,.dis,footer{color:#999}a{color:#6cb0ff}.pick{background:#2a1f17;border-color:#9a3412;color:#eee}.pick em{color:#fdba74}}"""


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
    picks = [(i, p) for i, p in enumerate(posts) if days and p["t"].startswith(days[-1]) and not p["text"].startswith("📋")]
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


def build(posts, out="docs"):
    os.makedirs(f"{out}/p", exist_ok=True)
    open(f"{out}/.nojekyll", "w").close()
    open(f"{out}/CNAME", "w").write(BASE.split("/")[2])  # GitHub Pages 커스텀 도메인 (재생성 때 안 날아가게)
    cards, urls = [], [BASE]
    for i, p in reversed(list(enumerate(posts))):
        title, rest, cut = split_title(p["text"])
        body = to_html(rest, [{**e, "offset": e["offset"] - cut} for e in p.get("entities") or [] if e["offset"] >= cut])
        btn = f'<a class="btn" href="{html.escape(p["url"])}" rel="nofollow noopener" target="_blank">🛒 구매하러 가기</a>' if p.get("url") else ""
        if community(p.get("url")):  # 원글로 가는 버튼이면 이름을 정확히 + 원글이 지워져도 찾을 수 있게
            btn = (f'<a class="btn" href="{html.escape(p["url"])}" rel="nofollow noopener" target="_blank">📄 원글에서 구매 링크 보기</a>'
                   f'<a class="btn2" href="{html.escape(find_url(title))}" rel="nofollow noopener" target="_blank">🔎 원글이 안 열리면 같은 상품 찾기</a>')
        url = f"{BASE}p/{i}.html"
        card = f'<article class="card"><div class="t">{p["t"]}</div><h2><a href="{url}">{html.escape(title)}</a></h2><p>{body}</p>{btn}</article>'
        cards.append(card)
        open(f"{out}/p/{i}.html", "w").write(page(f"{title} | {TITLE}", card, p["text"], url))
        urls.append(url)
    open(f"{out}/index.html", "w").write(page(f"{TITLE} - 오늘의 핫딜 모음", card_picks(posts, out) + ("\n".join(cards) or "<p>첫 딜을 준비 중이에요.</p>"), "매일 살 만한 핫딜만 골라드려요", BASE))
    open(f"{out}/sitemap.xml", "w").write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                           + "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>")
    return len(posts)


if __name__ == "__main__":
    posts = json.load(open("posts.json")) if os.path.exists("posts.json") else []
    print("site:", build(posts), "posts")
