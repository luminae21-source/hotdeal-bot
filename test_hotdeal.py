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

# 3) 승인 처리: 관리자 ✅(중복 클릭 1회만), ❌, 타인 클릭 무시, 처리 후 offset 확인
sent = []
def fake_tg(method, **p):
    sent.append((method, p))
    if method == "getUpdates" and "offset" not in p:
        kb = {"inline_keyboard": [[{"text": "🛒", "url": "https://buy"}], [{"text": "✅", "callback_data": "ok"}]]}
        msg = lambda mid: {"message_id": mid, "chat": {"id": 42}, "reply_markup": kb}
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

# 4) 전체 흐름: 30분 미만 글 제외, 점수 컷, 본 글 저장
os.chdir(tempfile.mkdtemp())
sent.clear()
H.ai_pick = lambda prompt, lines: [{"i": 0, "score": 8, "comment": "좋음"}] if len(lines) == 1 else []
H.main()
drafts = [p for m, p in sent if m == "sendMessage"]
assert len(drafts) == 1 and "휴지" in drafts[0]["text"] and json.load(open("seen.json")).keys() == {"ppomppu_101"}
sent.clear(); H.main()  # 재실행: 같은 글 다시 안 보냄
assert not [m for m, _ in sent if m == "sendMessage"]

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
print("OK: 모든 셀프체크 통과")
