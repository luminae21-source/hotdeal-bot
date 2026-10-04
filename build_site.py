#!/usr/bin/env python3
"""posts.json(채널에 게시된 딜) -> docs/ 정적 사이트. GitHub Pages로 서빙. 외부 패키지 없음."""
import html, json, os, re

BASE = "https://luminae21-source.github.io/hotdeal-bot/"
CHANNEL = "https://t.me/hotdeal_pick"
TITLE = "오늘의 딜 pick"
DISCLOSURE = "이 사이트는 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받을 수 있습니다."
CSS = """*{box-sizing:border-box}body{margin:0;font:16px/1.6 -apple-system,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;background:#f6f7f9;color:#1c1e21}
a{color:#0b63ce}main{max-width:680px;margin:0 auto;padding:16px}header{padding:12px 0 4px}header h1{margin:0;font-size:22px}header h1 a{color:inherit;text-decoration:none}
.sub{color:#666;font-size:13px}.card{background:#fff;border-radius:12px;padding:16px;margin:12px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.card h2{margin:0 0 8px;font-size:17px;line-height:1.4}.card h2 a{color:inherit;text-decoration:none}.t{color:#888;font-size:12px}
.btn{display:block;text-align:center;background:#0b63ce;color:#fff;border-radius:10px;padding:12px;margin-top:12px;text-decoration:none;font-weight:600}
.tg{display:block;text-align:center;background:#229ed9;color:#fff;border-radius:10px;padding:12px;margin:16px 0;text-decoration:none;font-weight:600}
.dis{font-size:12px;color:#888;margin:8px 0}footer{font-size:12px;color:#888;text-align:center;padding:24px 0}
@media(prefers-color-scheme:dark){body{background:#111;color:#eee}.card{background:#1c1c1e}.sub,.t,.dis,footer{color:#999}a{color:#6cb0ff}}"""


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


def title_of(text):
    for line in text.split("\n"):
        line = re.sub(r"^[^\w가-ퟣ\[]+", "", line).strip()  # 앞 이모지 제거
        if line and "쿠팡 파트너스 활동" not in line:
            return line
    return TITLE


def page(title, body, desc="", canonical=""):
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><meta name="description" content="{html.escape(desc[:150])}">
{f'<link rel="canonical" href="{canonical}">' if canonical else ''}<style>{CSS}</style></head><body><main>
<header><h1><a href="{BASE}">🔥 {TITLE}</a></h1><div class="sub">매일 살 만한 핫딜만 골라드려요</div></header>
<p class="dis">{DISCLOSURE}</p>{body}
<a class="tg" href="{CHANNEL}">📲 텔레그램에서 실시간으로 받기</a>
<footer>딜 정보는 게시 시점 기준이며 가격·재고는 변동될 수 있어요.</footer></main></body></html>"""


def build(posts, out="docs"):
    os.makedirs(f"{out}/p", exist_ok=True)
    open(f"{out}/.nojekyll", "w").close()
    cards, urls = [], [BASE]
    for i, p in reversed(list(enumerate(posts))):
        title, body = title_of(p["text"]), to_html(p["text"], p.get("entities"))
        btn = f'<a class="btn" href="{html.escape(p["url"])}" rel="nofollow noopener" target="_blank">🛒 구매하러 가기</a>' if p.get("url") else ""
        url = f"{BASE}p/{i}.html"
        card = f'<article class="card"><div class="t">{p["t"]}</div><h2><a href="{url}">{html.escape(title)}</a></h2><p>{body}</p>{btn}</article>'
        cards.append(card)
        open(f"{out}/p/{i}.html", "w").write(page(f"{title} | {TITLE}", card, p["text"], url))
        urls.append(url)
    open(f"{out}/index.html", "w").write(page(f"{TITLE} - 오늘의 핫딜 모음", "\n".join(cards) or "<p>첫 딜을 준비 중이에요.</p>", "매일 살 만한 핫딜만 골라드려요", BASE))
    open(f"{out}/sitemap.xml", "w").write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                           + "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>")
    return len(posts)


if __name__ == "__main__":
    posts = json.load(open("posts.json")) if os.path.exists("posts.json") else []
    print("site:", build(posts), "posts")
