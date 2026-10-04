"""셀프체크: python test_hotdeal.py  (네트워크·키 불필요)"""
import hashlib, hmac, json, os, tempfile, time
from email.utils import formatdate

os.environ.update(TG_TOKEN="t", TG_ADMIN_ID="42", TG_CHANNEL="@ch", COUPANG_ACCESS_KEY="ak", COUPANG_SECRET_KEY="sk")
import hotdeal as H

ago = lambda m: formatdate(time.time() - m * 60, usegmt=True)
RSS = f"""<?xml version="1.0" encoding="UTF-8" ?><rss version="2.0"><channel>
<item><title>[쿠팡] 휴지 30롤 (9,900원/무료)</title><link>http://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&amp;no=101</link>
<description>쿠폰가&amp;nbsp;좋네요</description><pubDate>{ago(45)}</pubDate><hits> [3|900|2|0]</hits></item>
<item><title>[G마켓] 너무 새 글 (1원)</title><link>http://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&amp;no=102</link>
<description>x</description><pubDate>{ago(5)}</pubDate><hits> [0|1|0|0]</hits></item>
</channel></rss>"""
PAGE = '<li class="topTitle-link partner"><span></span><a href="https://s.ppomppu.co.kr/?x=1" target="_blank">https://www.coupang.com/vp/products/1?a=1&amp;b=2</a>'

calls = []
def fake_http(url, body=None, headers=None, method=None):
    calls.append((url, body, headers, method))
    if "rss.php?id=dead" in url: raise OSError("feed down")
    if "rss.php" in url: return RSS
    if "view.php" in url: return PAGE
    if "deeplink" in url: return json.dumps({"data": [{"shortenUrl": "https://link.coupang.com/a/AFF"}]})
    raise AssertionError(url)
H.http = fake_http
H.FEEDS = {"ppomppu": "뽐뿌", "dead": "죽은피드"}

# 1) 피드 파싱 (+ 죽은 피드는 건너뜀)
deals = H.fetch_deals()
d = deals[0]
assert len(deals) == 2 and d["id"] == "ppomppu_101" and d["url"].startswith("https://")
assert d["hits"] == "댓글3·조회900·추천2·비추0" and d["desc"] == "쿠폰가 좋네요" and 44 < d["age"] < 46

# 2) 쇼핑몰 링크 추출 + 쿠팡 제휴 변환 + 서명
assert H.store_link(d["url"]) == "https://www.coupang.com/vp/products/1?a=1&b=2"
assert H.affiliate("https://www.gmarket.co.kr/x") == ("https://www.gmarket.co.kr/x", False)
assert H.affiliate("https://www.coupang.com/vp/products/1") == ("https://link.coupang.com/a/AFF", True)
url, body, hdr, method = calls[-1]
dt = hdr["Authorization"].split("signed-date=")[1].split(",")[0]
want = hmac.new(b"sk", (dt + "POST" + H.CP_BASE + "/deeplink").encode(), hashlib.sha256).hexdigest()
assert method == "POST" and hdr["Authorization"].endswith("signature=" + want) and body == {"coupangUrls": ["https://www.coupang.com/vp/products/1"]}
text, link = H.deal_post(d, "<싸다>")
assert text.startswith("<i>" + H.DISCLOSURE) and "&lt;싸다&gt;" in text and link == "https://link.coupang.com/a/AFF"

# 3) 승인 처리: 관리자 ✅(중복 클릭 1회만), ❌, 타인 클릭 무시, 처리 후 offset 확인, posts.json 기록
os.chdir(tempfile.mkdtemp())
sent = []
def fake_tg(method, **p):
    sent.append((method, p))
    if method == "getUpdates" and "offset" not in p:
        kb = {"inline_keyboard": [[{"text": "🛒", "url": "https://buy"}], [{"text": "✅", "callback_data": "ok"}]]}
        msg = lambda mid: {"message_id": mid, "chat": {"id": 42}, "reply_markup": kb, "text": "🔥 [쿠팡] 휴지\n\n좋음\n\n출처: 뽐뿌",
                           "entities": [{"type": "text_link", "offset": 20, "length": 2, "url": "https://src"}]}
        return [{"update_id": 1, "callback_query": {"from": {"id": 42}, "data": "ok", "message": msg(10)}},
                {"update_id": 2, "callback_query": {"from": {"id": 42}, "data": "ok", "message": msg(10)}},
                {"update_id": 3, "callback_query": {"from": {"id": 42}, "data": "no", "message": msg(11)}},
                {"update_id": 4, "callback_query": {"from": {"id": 99}, "data": "ok", "message": msg(12)}}]
    return {"message_id": 1}
H.tg = fake_tg
H.publish_approved()
copies = [p for m, p in sent if m == "copyMessage"]
assert len(copies) == 1 and copies[0]["message_id"] == 10 and copies[0]["reply_markup"]["inline_keyboard"] == [[{"text": "🛒", "url": "https://buy"}]]
assert [p["message_id"] for m, p in sent if m == "editMessageReplyMarkup"] == [10, 11]
assert sent[-1] == ("getUpdates", {"offset": 5})
posts = json.load(open("posts.json"))
assert len(posts) == 1 and posts[0]["url"] == "https://buy" and posts[0]["text"].startswith("🔥 [쿠팡] 휴지")

# 4) 전체 흐름: 30분 미만 글 제외, 점수 컷, 본 글 저장
sent.clear()
H.ai_pick = lambda prompt, lines: [{"i": 0, "score": 8, "comment": "좋음"}] if len(lines) == 1 else []
H.main()
drafts = [p for m, p in sent if m == "sendMessage" and "🔥" in p["text"]]  # (21시 이후엔 📋 모아보기 초안도 같이 나감)
assert len(drafts) == 1 and "휴지" in drafts[0]["text"] and {k for k in json.load(open("seen.json")) if k.startswith("ppomppu_")} == {"ppomppu_101"}
sent.clear(); H.main()  # 재실행: 같은 글 다시 안 보냄
assert not [p for m, p in sent if m == "sendMessage" and "🔥" in p["text"]]

# 5) 골드박스: 하루 1번, 대가성 문구 맨 앞, 고른 순서대로
GB = [{"productName": f"상품{i}", "productPrice": 1000.0 * (i + 1), "productUrl": f"https://link.coupang.com/{i}"} for i in range(8)]
H.http = lambda url, *a, **k: json.dumps({"data": GB})
H.ai_pick = lambda prompt, lines: [{"i": 3, "score": 9, "comment": "a"}, {"i": 0, "score": 8, "comment": "b"}]
seen, sent[:] = {}, []
H.goldbox(seen)
if time.gmtime(time.time() + 9 * 3600).tm_hour >= 9:
    t = sent[-1][1]["text"]
    assert t.startswith("<i>" + H.DISCLOSURE) and "TOP2" in t and t.index("상품3") < t.index("상품0") and "4,000원" in t
    sent.clear(); H.goldbox(seen); assert not sent  # 같은 날 재실행 시 안 보냄

# 6) 사이트 생성: 이모지(UTF-16 2유닛) 뒤 링크 오프셋, 제목 추출, 페이지/사이트맵 생성
import build_site as S
assert S.to_html("🔥 a <b> 뽐뿌", [{"type": "text_link", "offset": 9, "length": 2, "url": "https://x"}]) == \
    '🔥 a &lt;b&gt; <a href="https://x" rel="nofollow noopener" target="_blank">뽐뿌</a>'
assert S.title_of("이 포스팅은 쿠팡 파트너스 활동의 일환으로, 수수료\n\n⏰ 오늘의 골드박스 TOP5") == "오늘의 골드박스 TOP5"
assert S.title_of("🔥 [롯데온] 파스타 (14,490원)") == "[롯데온] 파스타 (14,490원)"
n = S.build(posts, "docs")
idx = open("docs/index.html").read()
assert n == 1 and idx.count("[쿠팡] 휴지") == 1 and 'href="https://buy"' in idx and os.path.exists("docs/p/0.html") and os.path.exists("docs/.nojekyll") and open("docs/CNAME").read() == "hotdealpick.kr"
assert '<a href="https://src" rel="nofollow noopener" target="_blank">뽐뿌</a>' in idx  # 제목 줄 잘라낸 뒤에도 링크 위치 정확
assert "p/0.html" in open("docs/sitemap.xml").read() and "쿠팡 파트너스" in open("docs/p/0.html").read()
assert S.build([], "docs2") == 0 and "준비 중" in open("docs2/index.html").read()

# 7) 일일 모아보기: 21시 이후 1회, 오늘 글만, 모아보기 자신은 제외
H.draft = lambda text, **k: sent.append(("draft", text)) or {"message_id": 9}
today = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600))
P = [{"t": f"{today} 10:00", "text": "🔥 A딜", "url": "https://a"}, {"t": "2000-01-01 10:00", "text": "🔥 옛날딜", "url": "https://o"},
     {"t": f"{today} 11:00", "text": "📋 오늘의 딜 모아보기", "url": None}]
seen, sent[:] = {}, []
H.digest(seen, P)
if time.gmtime(time.time() + 9 * 3600).tm_hour >= 21:
    t = [x for m, x in sent if m == "draft"][-1]
    assert "A딜" in t and "옛날딜" not in t and t.count("모아보기") == 1 and "hotdealpick.kr" in t and list(seen)[0].startswith("digest_")
    blog = sent[-1][1]["text"]  # 블로그용은 버튼 없는 일반 메시지로 뒤따라옴
    assert sent[-1][0] == "sendMessage" and "제목: " in blog and "A딜" in blog and "https://a" in blog and "옛날딜" not in blog and "쿠팡 파트너스" in blog
    sent.clear(); H.digest(seen, P); assert not sent
assert "og:title" in idx and "naver-site-verification" in idx
print("OK: 모든 셀프체크 통과")
