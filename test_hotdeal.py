"""셀프체크: python test_hotdeal.py  (네트워크·키 불필요)"""
import base64, hashlib, hmac, io, json, os, re, tempfile, time
from urllib.parse import parse_qs, urlsplit
from email.utils import formatdate

os.environ.update(TG_TOKEN="t", TG_ADMIN_ID="42", TG_CHANNEL="@ch", COUPANG_ACCESS_KEY="ak", COUPANG_SECRET_KEY="sk")
import hotdeal as H
AI_PICK = H.ai_pick  # 진짜 함수(아래에서 대부분 가짜로 바꿔 씀)

ago = lambda m: formatdate(time.time() - m * 60, usegmt=True)
RSS = f"""<?xml version="1.0" encoding="UTF-8" ?><rss version="2.0"><channel>
<item><title>[쿠팡] 휴지 30롤 (9,900원/무료)</title><link>http://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&amp;no=101</link>
<description>쿠폰가&amp;nbsp;좋네요</description><pubDate>{ago(45)}</pubDate><hits> [3|900|2|0]</hits></item>
<item><title>[G마켓] 너무 새 글 (1원)</title><link>http://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&amp;no=102</link>
<description>x</description><pubDate>{ago(5)}</pubDate><hits> [0|1|0|0]</hits></item>
</channel></rss>"""
CP = "https://www.coupang.com/vp/products/1?a=1&b=2"
B64 = base64.b64encode(CP.encode()).decode()
PAGE = f'<li class="topTitle-link partner"><span></span><a href="https://s.ppomppu.co.kr/?idno=ppomppu_101&amp;target={B64}&amp;encode=on" target="_blank">{CP}</a>'  # PC 글 (실제 구조)

calls = []
LP_OK = {"gmarket.co.kr": "gmarket", "lotteon.com": "lotteon", "auction.co.kr": "auction", "e-himart.co.kr": "himart"}  # 링크프라이스 API가 '승인'으로 답하는 몰 (하이마트 = 새로 승인된 몰 가정)
def fake_http(url, body=None, headers=None, method=None):
    calls.append((url, body, headers, method))
    if "rss.php?id=dead" in url: raise OSError("feed down")
    if "rss.php" in url: return RSS
    if "view.php" in url: return PAGE
    if "deeplink" in url: return json.dumps({"data": [{"shortenUrl": "https://link.coupang.com/a/AFF"}]})
    if url.startswith("https://api.linkprice.com/ci/service/custom_link_xml?a_id=" + H.LP_AID + "&"):  # 실제 응답 형식(10/5 확인)
        u = parse_qs(urlsplit(url).query)["url"][0]; m = next((v for k, v in LP_OK.items() if k in u), None)
        return json.dumps({"result": "S", "url": H.lp_link(m, u).replace("l_cd2=0", "l_cd2=q"), "mobile_yn": "Y"} if m else {"result": "F", "url": "", "err_msg": "[-6] 승인거부"})
    raise AssertionError(url)
H.http = fake_http
H.FEEDS = {"ppomppu": "뽐뿌", "dead": "죽은피드"}

# 1) 피드 파싱 (+ 죽은 피드는 건너뜀)
deals = H.fetch_deals()
d = deals[0]
assert len(deals) == 2 and d["id"] == "ppomppu_101" and d["url"].startswith("https://")
assert d["hits"] == "댓글3·조회900·추천2·비추0" and d["desc"] == "쿠폰가 좋네요" and 44 < d["age"] < 46

# 2) 쇼핑몰 링크 추출 + 쿠팡 제휴 변환 + 서명
assert H.store_link(d["url"]) == "https://www.coupang.com/vp/products/1"  # target= base64 복원 + 쿠팡 추적값(a·b) 제거
P2 = base64.b64encode("https://item.gmarket.co.kr/Item?goodscode=3383368133&n=>>?".encode()).decode()
assert "+" in P2 or "/" in P2
H.http = lambda url, *a, **k: f'<li class="topTitle-link partner"><a href="https://s.ppomppu.co.kr/?idno=x&amp;target={P2}&amp;encode=on">'
assert H.store_link(d["url"]) == "https://item.gmarket.co.kr/Item?goodscode=3383368133&n=>>?"
H.http = lambda url, *a, **k: "<div>링크 없는 글</div>"; assert H.store_link(d["url"]) is None
def blocked(url, *a, **k): raise OSError("403")
H.http = blocked; assert H.store_link(d["url"]) is None  # GitHub 서버 차단 시 -> 버튼은 뽐뿌 글(관리자 답장으로 교체)
H.http = fake_http
GM = "https://item.gmarket.co.kr/Item?goodscode=1"
assert H.affiliate(GM) == (H.lp_link("gmarket", GM).replace("l_cd2=0", "l_cd2=q"), True)  # 승인 몰 상품 -> 링크프라이스 API 딥링크
assert H.affiliate("https://www.e-himart.co.kr/app/goods/goodsDetail?goodsNo=1")[1]  # 새로 승인된 몰도 코드 수정 없이 자동
assert H.affiliate("https://www.11st.co.kr/products/1") == ("https://www.11st.co.kr/products/1", False)  # 승인 전(F) -> 제휴 아님
H.http = blocked; assert H.affiliate(GM) == (H.lp_link("gmarket", GM), True) and not H.affiliate("https://www.11st.co.kr/products/1")[1]  # API 장애 -> 승인 몰은 직접 딥링크
H.http = fake_http
assert H.plain("https://toss.shopping/t/9?k=1&referrer=affiliate") == "https://toss.shopping/t/9"  # 남의 쉐어링크 표시(k=) 떼고 상품만
assert H.affiliate("https://smartstore.naver.com/a/products/1") == ("https://smartstore.naver.com/a/products/1", False) and H.affiliate(None) == (None, False)
assert H.affiliate("https://www.coupang.com/vp/products/1") == ("https://link.coupang.com/a/AFF", True)
url, body, hdr, method = calls[-1]
dt = hdr["Authorization"].split("signed-date=")[1].split(",")[0]
want = hmac.new(b"sk", (dt + "POST" + H.CP_BASE + "/deeplink").encode(), hashlib.sha256).hexdigest()
assert method == "POST" and hdr["Authorization"].endswith("signature=" + want) and body == {"coupangUrls": ["https://www.coupang.com/vp/products/1"]}
text, link, label = H.deal_post(d, "<싸다>")
assert text.startswith("<i>" + H.DISCLOSURE) and "&lt;싸다&gt;" in text and link == "https://link.coupang.com/a/AFF"
t2 = H.deal_post(d, "싸다", None, {"unit": "100g당 990원", "warn": "쿠폰 <1인 1회>", "pts": ["x"]})[0]  # 단위가격·확인할 점은 코멘트 아래, 출처 위
assert "싸다\n💡 단위가격 100g당 990원\n⚠️ 확인할 점 쿠폰 &lt;1인 1회&gt;\n\n출처:" in t2 and "x" not in t2.split("싸다")[1].split("출처")[0].replace("확인", "")
assert "unit:" in H.DEAL_PROMPT and "warn:" in H.DEAL_PROMPT and "unit:" in H.REEL_PROMPT

# 2-2) 새 출처: 루리웹 RSS·클리앙 목록(공지 제외) 파싱 / 글에서 상품 주소(남의 제휴 링크는 원래 주소로) / 승인 몰은 상품 페이지 딥링크
RULI = f"""<rss><channel><item><title>[롯데온] 매일 피크닉 200ml 48팩 (15,600원/무료)</title><category>음식</category>
<link>https://bbs.ruliweb.com/market/board/1020/read/107788</link><pubDate>{ago(50)}</pubDate></item></channel></rss>"""
kst = lambda m: time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time() + 9 * 3600 - m * 60))
ROW = lambda cls, sn, title, m: (f'<div class="list_item {cls}" data-role="list-row" data-author-id=a data-board-sn={sn} data-comment-count=4> '
    f'<span class="list_votes"><i class="fa fa-heart"></i> 7</span> <span class="list_subject" data-role="cut-string" title="{title}"> '
    f'<div class="list_hit"><span class="hit">1,234</span></div> <span class="time popover">10-05<span class="timestamp">{kst(m)}</span></span></div> ')
CLIEN = ROW("notice", 1, "공지", 10) + ROW("symph_row jirum ", 19273778, "쿠팡 휴지 &amp; 물티슈", 40)
H.http = lambda url, *a, **k: RULI if url == H.RULIWEB_RSS else CLIEN if url == H.CLIEN_LIST else ""
r, c = H.ruliweb_feed()[0], H.clien_feed()
assert r["id"] == "ruliweb_107788" and r["board"] == "루리웹" and r["desc"] == "분류: 음식" and 49 < r["age"] < 51
assert [x["id"] for x in c] == ["clien_19273778"] and c[0]["title"] == "쿠팡 휴지 & 물티슈" and c[0]["url"] == H.CLIEN_LIST + "/19273778"
assert c[0]["hits"] == "댓글4·조회1,234·추천7" and 39 < c[0]["age"] < 41
H.http = lambda url, *a, **k: ('<div class="source_url box_line_with_shadow"><span class="text_bar">출처 : </span> '
    '<a href="https://web.ruliweb.com/link.php?ol=https%3A%2F%2Fwww.lotteon.com%2Fp%2Fproduct%2FLO1&amp;bbs=1020">x</a></div>')
assert H.store_link(r["url"]) == "https://www.lotteon.com/p/product/LO1"
H.http = lambda url, *a, **k: '<div class="source_url box_line_with_shadow"><span class="text_bar">출처 : </span> <a href="https://brand.naver.com/lottechilsung/products/127?NaPm=x" target="_blank">'
assert H.store_link(r["url"]) == "https://brand.naver.com/lottechilsung/products/127"  # 네이버는 link.php 없이 주소 그대로(10/5 실제 글)
# '출처' 칸 없이 본문에만 토스 주소를 적은 글(10/8 루리웹 107866 핫식스 [토스] 실제 구조: view_content 안 <p>에 글자로, 본문 밖 JSON·댓글에도 주소)
#  -> 본문의 첫 토스·쿠팡 주소(블로그 등 다른 주소는 건너뜀) -> 남의 단축 쉐어링크는 따라가서 상품 주소(/t/번호)만 -> 우리 쉐어링크로. 상품 주소로 안 풀리면 None
h0, loc0 = H.http, H.location
rb = ('<script>{"articleBody": "https://toss.shopping/_m/OUT1"}</script><div class="view_content autolink" itemprop="articleBody"> <article> <div> <p>애플홀릭이 저렴하게 나왔네요<br>'
      'https://blog.naver.com/x/1 https://toss.shopping/_m/7OD6gVy4</p></div></article></div><div class="comment">https://toss.shopping/_m/OUT2</div>')
H.http, H.location = (lambda url, *a, **k: rb), {"https://toss.shopping/_m/7OD6gVy4": "https://toss.shopping/t/55?k=abc&referrer=affiliate"}.get
assert H.store_link(r["url"]) == "https://toss.shopping/t/55"
H.http = lambda url, *a, **k: rb.replace("toss.shopping/_m/7OD6gVy4", "example.com/x")
assert H.store_link(r["url"]) is None  # 본문에 토스·쿠팡 주소가 없으면 None(본문 밖 JSON·댓글 주소는 안 씀)
H.http, H.location = (lambda url, *a, **k: rb), {"https://toss.shopping/_m/7OD6gVy4": "https://service.toss.im/event?ref=other"}.get
assert H.store_link(r["url"]) is None  # 상품 주소로 안 풀리면 남의 링크를 쓰지 않음
H.http, H.location = h0, loc0
lo = H.affiliate("https://www.lotteon.com/p/product/LO1")
assert lo[1] and parse_qs(urlsplit(lo[0]).query)["m"] == ["lotteon"] and parse_qs(urlsplit(lo[0]).query)["tu"] == ["https://www.lotteon.com/p/product/LO1"]
H.http = lambda url, *a, **k: ("<div class=\"attached_link top\"> <span class=\"attached_subject\">구매링크</span> "
    "<a href='https://click.linkprice.com/click.php?m=gmarket&a=A999&tu=https%3A%2F%2Fitem.gmarket.co.kr%2FItem%3Fgoodscode%3D7'target='_blank'>")
assert H.store_link(c[0]["url"]) == "https://item.gmarket.co.kr/Item?goodscode=7"  # 남의 링크프라이스(a=A999) -> 원래 주소 -> 우리 a=로 다시
assert "a=" + H.LP_AID in H.affiliate(H.store_link(c[0]["url"]))[0]
hops = {"https://link.coupang.com/a/x": "https://link.coupang.com/re/AFFSDP?lptag=AF1&pageKey=9",
        "https://link.coupang.com/re/AFFSDP?lptag=AF1&pageKey=9": "https://www.coupang.com/vp/products/9?itemId=8&vendorItemId=7&lptag=AF1&subid=s",
        "https://naver.me/Ab": "https://smartstore.naver.com/s/products/1?NaPm=ct%3Dx"}
loc = H.location; H.location = hops.get
assert H.plain("https://link.coupang.com/a/x") == "https://www.coupang.com/vp/products/9?itemId=8&vendorItemId=7"  # 남의 쿠팡 파트너스 -> 상품
assert H.plain("https://naver.me/Ab") == "https://smartstore.naver.com/s/products/1"  # 남의 쇼핑커넥트 -> 상품 주소만
assert H.plain("https://link.coupang.com/a/dead") is None and H.plain("javascript:void(0)") is None  # 원래 주소 모르면 남의 링크 안 씀
assert H.plain("https://toss.im/_m/dead") is None and H.plain("https://toss.shopping/_m/dead") is None  # 토스 단축도 풀리지 않으면 None
H.location = loc
import http.server, threading
class R(http.server.BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(302); self.send_header("Location", "/vp/products/5?lptag=x"); self.end_headers()
    def log_message(self, *a): pass
srv = http.server.HTTPServer(("127.0.0.1", 0), R); threading.Thread(target=srv.handle_request, daemon=True).start()
assert H.location(f"http://127.0.0.1:{srv.server_port}/a") == f"http://127.0.0.1:{srv.server_port}/vp/products/5?lptag=x"  # 따라가지 않고 Location만
srv.server_close()
assert H.store_info("쿠팡 휴지 & 물티슈", "https://www.coupang.com/vp/products/9") == H.STORES["쿠팡"]  # 제목에 [몰]이 없으면 주소로
assert H.store_info("땅콩버터", "https://smartstore.naver.com/x/products/1") == H.STORES["네이버"]
assert H.store_info("[롯데하이마트] 에어컨") == H.LP.format("1.26%") and H.store_info("[이마트] 라면") == H.LP.format("1%")  # 하이마트를 이마트로 잘못 보지 않음
assert H.store_info("수납장", "https://ohou.se/productions/1").startswith("⏳")  # 오늘의집 승인 전엔 사본 안 보냄
assert H.dkey("[롯데온] 매일 피크닉 200ml 4종 48팩 (15,600원/무료)") == H.dkey("[롯데온] 매일 피크닉 200ml 4종 48팩 / 15,600원")
assert H.dkey("[쿠팡] 라면") is None  # 너무 짧으면 같은 딜 판단 안 함
bodies, tt = [], time.time  # 밤(KST 0~8시) 발송은 무음, 낮·조회는 그대로
H.http = lambda url, body=None, *a, **k: bodies.append(body) or '{"result": {}}'
time.time = lambda: 1791223200; H.tg("sendMessage", chat_id="@ch", text="x"); H.tg("getUpdates")  # 10/6 03:00 KST
time.time = lambda: 1791248400; H.tg("copyMessage", chat_id="42")  # 10/6 10:00 KST
time.time = tt
assert bodies[0]["disable_notification"] is True and "disable_notification" not in bodies[1] and "disable_notification" not in bodies[2]
bodies.clear(); long = "\n\n".join(f"{i}. " + "가" * 300 for i in range(40))  # 4096자 넘는 일반 글은 문단 단위로 나눠 보냄(10/6 블로그용 글 실패)
H.tg("sendMessage", chat_id="42", text=long); H.tg("sendMessage", chat_id="42", text=long, reply_markup={"inline_keyboard": []})
assert len(bodies) == 5 and all(len(b["text"]) <= 4096 for b in bodies[:4]) and "\n\n".join(b["text"] for b in bodies[:4]) == long and bodies[4]["text"] == long
H.http = fake_http

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

# 3-2) 초안에 링크로 답장 -> 버튼 교체 + 대가성 문구(UTF-16 오프셋 밀기), 같은 실행의 ✅는 교체된 링크로 게시, 남의 답장 무시
sent.clear()
DR = {"message_id": 20, "chat": {"id": 42}, "text": "🔥 [쿠팡] 휴지\n\n출처: 뽐뿌", "entities": [{"type": "text_link", "offset": 16, "length": 2, "url": "https://src"}],
      "reply_markup": {"inline_keyboard": [[{"text": "🛒", "url": "https://ppomppu"}], [{"text": "✅ 게시 (8점)", "callback_data": "ok"}]]}}
UP = [{"update_id": 7, "message": {"from": {"id": 99}, "text": "https://evil.com", "reply_to_message": DR}},
      {"update_id": 8, "message": {"from": {"id": 42}, "text": "이걸로 https://link.coupang.com/a/xyz", "reply_to_message": DR}},
      {"update_id": 9, "callback_query": {"from": {"id": 42}, "data": "ok", "message": DR}}]
H.tg = lambda method, **p: sent.append((method, p)) or (UP if method == "getUpdates" and "offset" not in p else {"message_id": 1})
H.publish_approved()
ed = [p for m, p in sent if m == "editMessageText"]
n = len(H.DISCLOSURE.encode("utf-16-le")) // 2
assert len(ed) == 1 and ed[0]["text"].startswith(H.DISCLOSURE + "\n\n🔥") and ed[0]["entities"][0] == {"type": "italic", "offset": 0, "length": n}
assert ed[0]["entities"][1]["offset"] == 16 + n + 2 and ed[0]["reply_markup"]["inline_keyboard"][1][0]["text"] == "✅ 게시 (8점)"
u16 = ed[0]["text"].encode("utf-16-le"); e = ed[0]["entities"][1]
assert u16[e["offset"] * 2:(e["offset"] + e["length"]) * 2].decode("utf-16-le") == "뽐뿌"  # 링크 위치 그대로
cp = [p for m, p in sent if m == "copyMessage"][0]
assert cp["reply_markup"]["inline_keyboard"] == [[{"text": "🛒 구매하러 가기", "url": "https://link.coupang.com/a/xyz"}]]
last = json.load(open("posts.json"))[-1]
assert last["url"] == "https://link.coupang.com/a/xyz" and last["text"].startswith(H.DISCLOSURE)
sent.clear(); H.relink(DR, "https://item.gmarket.co.kr/Item?goodscode=1")  # 일반 쇼핑몰 링크: 문구 없이 버튼만
assert sent[0][1]["text"] == DR["text"] and sent[0][1]["reply_markup"]["inline_keyboard"][0][0]["url"].startswith("https://item.gmarket")
sent.clear(); H.relink(DR, "https://click.linkprice.com/click.php?m=gmarket")  # 링크프라이스: 일반 제휴 문구
assert sent[0][1]["text"].startswith(H.AFF_NOTE)
sent.clear(); H.relink(DR, "https://linkmoa.kr/abc12")  # 링크프라이스 단축 도메인도 문구 필수 (기본 선택이 linkmoa.kr)
assert sent[0][1]["text"].startswith(H.AFF_NOTE)
for u in ("https://toss.im/_m/abcDE", "https://toss.shopping/t/9?k=1&referrer=affiliate"):  # 토스 쉐어링크: 토스 권장 문구
    sent.clear(); H.relink(DR, u)
    assert sent[0][1]["text"].startswith(H.TOSS_NOTE + "\n\n") and sent[0][1]["reply_markup"]["inline_keyboard"][0][0]["url"] == u
    assert H.title_of(sent[0][1]["text"]) == H.title_of(DR["text"])  # 대가성 문구 줄이 제목이 되면 안 됨
assert H.title_of(H.AFF_NOTE + "\n\n🔥 [G마켓] 라면") == "[G마켓] 라면"
sent.clear(); H.relink(DR, "https://naver.me/FBMXkU0N")  # 네이버 쇼핑커넥트: 네이버 안내 문구 그대로 맨 앞
assert sent[0][1]["text"].startswith(H.NAVER_NOTE + "\n\n") and H.title_of(sent[0][1]["text"]) == H.title_of(DR["text"])
assert H.store_info("[네이버] 퍼실 세제") == H.STORES["네이버"] and H.STORES["네이버"].startswith("💰")  # 쇼핑커넥트: 사본 보냄(텔레그램·사이트는 활동 제한 채널 아님)

# 3-3) 봇에게 '제목 + 링크' 새로 보내기 -> 초안(대가성 문구·제목·코멘트·버튼), 붙여넣은 문구 중복 없음, 링크만 보내면 안내, 남의 메시지 무시
sent.clear()
LP = "https://click.linkprice.com/click.php?m=gmarket&a=A1&tu=x"
UP = [{"update_id": 20, "message": {"message_id": 30, "from": {"id": 42}, "text": f"{H.AFF_NOTE}\n\n🔥 [G마켓] 러닝화 (39,910원/무료)\n쿠폰 <필수>\n{LP}"}},
      {"update_id": 21, "message": {"message_id": 31, "from": {"id": 42}, "text": LP}},
      {"update_id": 22, "message": {"message_id": 32, "from": {"id": 99}, "text": f"[스팸] 광고\n{LP}"}},
      {"update_id": 23, "message": {"message_id": 33, "from": {"id": 42}, "text": "[G마켓] 일반\nhttps://item.gmarket.co.kr/Item?goodscode=1"}}]
H.tg = lambda method, **p: sent.append((method, p)) or (UP if method == "getUpdates" and "offset" not in p else {"message_id": 1})
H.publish_approved()
ms = [p for m, p in sent if m == "sendMessage"]
assert len(ms) == 3, ms
assert ms[0]["chat_id"] == "42" and ms[0]["text"] == f"<i>{H.AFF_NOTE}</i>\n\n🔥 <b>[G마켓] 러닝화 (39,910원/무료)</b>\n\n쿠폰 &lt;필수&gt;"
assert ms[0]["reply_markup"]["inline_keyboard"][0][0] == {"text": "🛒 구매하러 가기", "url": LP} and ms[0]["text"].count("이 포스팅은") == 1
assert ms[1]["reply_parameters"] == {"message_id": 31} and "제목" in ms[1]["text"]  # 링크만 -> 안내
assert ms[2]["text"] == "🔥 <b>[G마켓] 일반</b>"  # 일반 쇼핑몰 주소: 문구 없음
assert sent[-1] == ("getUpdates", {"offset": 24})
H.tg = fake_tg

# 3-7) 음악 파일 보내기 -> 릴스 배경음악 등록(file_id만 저장, 같은 곡 1번, 오디오 문서도 됨, 남이 보낸 건·일반 파일은 무시) / 오늘 차례 곡 받기
UP = [{"update_id": 40, "message": {"message_id": 50, "from": {"id": 42}, "audio": {"file_id": "F1", "file_unique_id": "U1", "title": "Happy"}}},
      {"update_id": 41, "message": {"message_id": 51, "from": {"id": 42}, "document": {"file_id": "F1b", "file_unique_id": "U1", "mime_type": "audio/mpeg"}}},
      {"update_id": 42, "message": {"message_id": 52, "from": {"id": 99}, "audio": {"file_id": "F2", "file_unique_id": "U2"}}},
      {"update_id": 43, "message": {"message_id": 53, "from": {"id": 42}, "document": {"file_id": "F9", "file_unique_id": "U9", "mime_type": "application/pdf"}}},
      {"update_id": 44, "message": {"message_id": 54, "from": {"id": 42}, "document": {"file_id": "F3", "file_unique_id": "U3", "mime_type": "audio/x-wav", "file_name": "b.wav"}}}]
sent.clear(); H.tg = lambda method, **p: sent.append((method, p)) or (UP if method == "getUpdates" and "offset" not in p else {"message_id": 1, "file_path": "music/f.mp3"})
json.dump([{"url": "https://cdn.pixabay.com/download/audio/p.mp3", "name": "Pixabay"}], open("music.json", "w"))  # Claude가 넣은 Pixabay 곡 뒤에 추가
H.publish_approved()
assert [(x.get("id"), x["name"]) for x in json.load(open("music.json"))] == [(None, "Pixabay"), ("F1", "Happy"), ("F3", "b.wav")]
assert [p["reply_parameters"]["message_id"] for m, p in sent if m == "sendMessage" and "배경음악" in p["text"]] == [50, 51, 54] and sent[-1] == ("getUpdates", {"offset": 45})
got_url, uo = [], H.urllib.request.urlopen
H.urllib.request.urlopen = lambda req, timeout=None: got_url.append(getattr(req, "full_url", req)) or io.BytesIO(b"ID3-music")
bp = H.bgm(time.gmtime(86400 * 4))  # tm_yday 5 -> 5 % 3곡 = 세 번째 곡(F3)
assert open(bp, "rb").read() == b"ID3-music" and got_url == ["https://api.telegram.org/file/bott/music/f.mp3"] and ("getFile", {"file_id": "F3"}) in sent
json.dump([{"url": "https://cdn.pixabay.com/download/audio/a.mp3", "name": "Pixabay 곡"}], open("music.json", "w")); got_url.clear()
pp = H.bgm(time.gmtime(0)); pp2 = H.bgm(time.gmtime(0))  # Pixabay 음원: 처음 1번만 받아 music/에 보관(캐시), 다음부턴 안 받음
assert pp == pp2 and pp.startswith("music" + os.sep) and open(pp, "rb").read() == b"ID3-music" and got_url == ["https://cdn.pixabay.com/download/audio/a.mp3"]
def no_net(req, timeout=None):
    raise OSError("403")
H.urllib.request.urlopen = no_net; json.dump([{"url": "https://cdn.pixabay.com/download/audio/b.mp3"}], open("music.json", "w"))
assert H.bgm(time.gmtime(0)) is None and len(os.listdir("music")) == 1  # 못 받으면 무음, 깨진 파일 안 남김
os.remove("music.json"); assert H.bgm(time.gmtime(0)) is None  # 등록된 곡 없으면 무음
# 플레이리스트(관리자 채팅): 새 곡이 들어오면 목록 글 + 전 곡 오디오(곡명·아티스트 표시, 누르면 재생·다음 곡 이어서), 받은 file_id 저장, 못 보내면 링크 글, 두 번 안 보냄
json.dump([{"url": "https://cdn.pixabay.com/a.mp3", "name": "A — x", "page": "https://pixabay.com/music/a/"}, {"id": "F1", "u": "U1", "name": "b.wav", "sent": 1},
           {"url": "https://cdn.pixabay.com/c.mp3", "name": "C", "page": "https://pixabay.com/music/c/"}], open("music.json", "w"))
def pl_tg(method, **p):
    sent.append((method, p))
    return None if p.get("audio", "").endswith("c.mp3") else {"message_id": 1, "audio": {"file_id": "FA" if p.get("audio", "").endswith("a.mp3") else p.get("audio")}}
sent.clear(); H.tg = pl_tg; tq4 = time.time; time.time = lambda: 1791248400  # 10/6 (279일째 -> 279 % 3 = 0번 곡이 오늘)
H.playlist({})
assert [(m, p.get("audio")) for m, p in sent] == [("sendMessage", None), ("sendAudio", "https://cdn.pixabay.com/a.mp3"), ("sendAudio", "F1"), ("sendAudio", "https://cdn.pixabay.com/c.mp3"), ("sendMessage", None)]
assert "3곡" in sent[0][1]["text"] and "1. A — x ← 오늘 릴스" in sent[0][1]["text"] and "누르면 재생" in sent[0][1]["text"]
assert (sent[1][1]["title"], sent[1][1]["performer"]) == ("A", "x") and "performer" not in sent[2][1] and "https://pixabay.com/music/c/" in sent[4][1]["text"]
assert [(m.get("fid"), m.get("sent")) for m in json.load(open("music.json"))] == [("FA", 1), ("F1", 1), (None, 1)]
sent.clear(); H.playlist({}); assert not sent  # 새 곡 없으면 안 보냄
mj = json.load(open("music.json")) + [{"url": "https://cdn.pixabay.com/d.mp3", "name": "D"}]; json.dump(mj, open("music.json", "w"))
H.playlist({}); assert sent[1][1]["audio"] == "FA" and "4곡" in sent[0][1]["text"]  # 새 곡 추가 -> 전체 다시(이미 받은 곡은 텔레그램 파일로)
os.remove("music.json"); sent.clear(); H.playlist({}); assert not sent
time.time = tq4
H.urllib.request.urlopen, H.tg = uo, fake_tg
# 3-4) 쇼핑몰별 수익 안내: 뽐뿌 제목 표기 흔들림([G마켓]붙여쓰기·지마켓·롯데ON) 흡수, 제휴 없는 몰은 수수료 0, 안내 버튼은 채널로 안 감
assert H.store_info("[G마켓]메디폴미 크림") == H.store_info("[지마켓] 신라면") == H.LP.format("0.6%")
assert H.store_info("[롯데ON] 삼다수") == H.store_info("[롯데온]블랙야크") == H.LP.format("1.4%")
assert H.store_info("[알리익스프레스] 충전기").startswith("⏳") and H.store_info("[11번가] 고구마").startswith("⏳") and H.store_info("[쿠팡] 휴지") == H.STORES["쿠팡"]  # 승인 전 몰은 사본 안 보냄(💰만)
assert H.store_info("[sk스토아] 블루베리").startswith("💸") and H.store_info("제목에 태그 없음").startswith("💸")
DI = {"message_id": 40, "chat": {"id": 42}, "text": "🔥 [롯데온] 삼다수", "entities": [],
      "reply_markup": {"inline_keyboard": [[{"text": "🛒", "url": "https://ppomppu"}], [{"text": "✅", "callback_data": "ok"}],
                                           [{"text": H.LP.format("1.4%"), "callback_data": "-"}]]}}
UP = [{"update_id": 30, "callback_query": {"from": {"id": 42}, "data": "-", "message": DI}},  # 안내 버튼 눌러도 무시
      {"update_id": 31, "callback_query": {"from": {"id": 42}, "data": "ok", "message": DI}}]
sent.clear(); H.tg = lambda method, **p: sent.append((method, p)) or (UP if method == "getUpdates" and "offset" not in p else {"message_id": 1})
H.publish_approved()
cps = [p for m, p in sent if m == "copyMessage"]
assert len(cps) == 1 and cps[0]["reply_markup"]["inline_keyboard"] == [[{"text": "🛒", "url": "https://ppomppu"}]]
H.tg = fake_tg

# 3-5) 전부 채널에 바로 게시(✅ 없음): 💸=뽐뿌 링크, 링크프라이스 몰=검색 제휴 링크+문구, 쿠팡 등=게시 후 관리자에게 사본(선택 교체)
#      채널 게시 실패 -> 초안, 사본에 제휴 링크 답장 -> 채널 글·사본·posts.json 교체
sent.clear(); sl = H.store_link; H.store_link = lambda u: None
D = lambda t: {"title": t, "url": "https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&no=1", "board": "뽐뿌"}
n0 = len(json.load(open("posts.json"))); mids = iter(range(100, 200))
def ch_tg(method, **p):
    sent.append((method, p))
    if method == "sendMessage" and p.get("chat_id") == "@ch":
        return {"message_id": next(mids), "text": re.sub(r"<[^>]+>", "", p["text"]), "entities": []}  # 텔레그램은 태그 없는 글 + entities로 돌려줌
    return {"message_id": 1}
H.tg = ch_tg
H.post_or_draft(D("[sk스토아] 블루베리 (18,700원/무료)"), "싸요", 8, None, {"e": "🫐", "hook": "1kg 6,233원", "pts": ["kg당 6,233원"], "unit": "kg당 6,233원", "warn": "", "x": None})  # 💸: 바로 게시, 사본 없음
assert [(m, p["chat_id"]) for m, p in sent] == [("sendMessage", "@ch")]
assert sent[0][1]["reply_markup"]["inline_keyboard"] == [[{"text": "🛒 구매하러 가기", "url": D("")["url"]}]]
lp = json.load(open("posts.json"))[-1]
assert lp["mid"] == 100 and lp["s"] == 8 and lp["e"] == "🫐" and lp["hook"] == "1kg 6,233원" and lp["pts"] == ["kg당 6,233원"] and "x" not in lp  # 릴스 재료 저장
assert lp["unit"] == "kg당 6,233원" and "warn" not in lp and "💡 단위가격 kg당 6,233원" in sent[0][1]["text"]  # 빈 값은 저장 안 함
sent.clear(); H.post_or_draft(D("[롯데온] 제주 삼다수 2L 24병 (23,330원/무료)"), "싸요", 8, "제주 삼다수 2L")  # 링크프라이스: 자동 제휴
b = sent[0][1]["reply_markup"]["inline_keyboard"][0][0]
qs = parse_qs(urlsplit(b["url"]).query)
assert b["text"] == "🔎 롯데온에서 찾기" and qs["m"] == ["lotteon"] and qs["a"] == [H.LP_AID]
assert qs["tu"] == ["https://www.lotteon.com/csearch/search/search?render=search&platform=pc&q=%EC%A0%9C%EC%A3%BC%20%EC%82%BC%EB%8B%A4%EC%88%98%202L"]
assert sent[0][1]["text"].startswith(f"<i>{H.AFF_NOTE}</i>") and len(sent) == 1  # 이미 제휴라 사본 없음
assert H.keyword("[G마켓]메디폴미 레드 크림 50g(17,320원/무료)") == "메디폴미 레드 크림 50g" and H.keyword("[옥션] 라면 (1+1)") == "라면 (1+1)"
assert parse_qs(urlsplit(H.lp_search("[지마켓] 신라면 20봉 (13,800원/무료)")[0]).query)["tu"][0].startswith("https://www.gmarket.co.kr/n/search?keyword=%EC%8B%A0")
assert H.lp_search("[11번가] 로봇청소기") == (None, None)  # 11번가는 링크프라이스 승인 대기 -> 아직 자동 안 함
assert H.lp_search("[옥션] 라면 (1+1)") == (None, None)  # 옥션 검색 딥링크는 메인으로 랜딩 -> 자동 안 함
sent.clear(); H.post_or_draft(D("[쿠팡] 휴지 30롤"), "싸요", 8)  # 손으로 링크 만들어야 하는 몰: 게시 + 관리자 사본
assert [(m, p["chat_id"]) for m, p in sent] == [("sendMessage", "@ch"), ("copyMessage", "42")]
cp = sent[1][1]; assert cp["from_chat_id"] == "@ch" and cp["message_id"] == 102
kb = cp["reply_markup"]["inline_keyboard"]
assert kb[0][0]["url"] == "https://t.me/ch/102" and kb[2][0]["text"].startswith("💰 쿠팡 파트너스")
assert kb[1][0] == {"text": "🔗 파트너스 링크 만들기", "url": "https://partners.coupang.com/#affiliate/ws/link/0/%ED%9C%B4%EC%A7%80%2030%EB%A1%A4"}  # 파트너스 검색 결과 바로 열기
assert json.load(open("posts.json"))[-1]["cp"] == 1  # 관리자 사본 번호 저장(링크만 보낼 때 찾기용)
sent.clear(); H.tg = lambda method, **p: sent.append((method, p)) or (None if p.get("chat_id") == "@ch" else {"message_id": 1})
H.post_or_draft(D("[카카오] 게장"), "싸요", 8)  # 채널 게시 실패 -> 초안으로
assert [p["chat_id"] for m, p in sent] == ["@ch", "42"] and sent[1][1]["reply_markup"]["inline_keyboard"][1][0]["callback_data"] == "ok"
assert len(json.load(open("posts.json"))) == n0 + 3
NT = {"message_id": 50, "chat": {"id": 42}, "text": "🔥 [쿠팡] 휴지 30롤\n\n싸요", "entities": [{"type": "bold", "offset": 3, "length": 4}],
      "reply_markup": {"inline_keyboard": [[{"text": "📢 채널에 올라간 글", "url": "https://t.me/ch/102"}], [{"text": "💰", "callback_data": "-"}]]}}
UP = [{"update_id": 40, "message": {"message_id": 51, "from": {"id": 42}, "text": "https://link.coupang.com/a/zz", "reply_to_message": NT}}]
sent.clear(); H.tg = lambda method, **p: sent.append((method, p)) or (UP if method == "getUpdates" and "offset" not in p else {"message_id": 1})
H.publish_approved()
ed = [p for m, p in sent if m == "editMessageText"]
n = len(H.DISCLOSURE.encode("utf-16-le")) // 2
assert [(p["chat_id"], p["message_id"]) for p in ed] == [("@ch", 102), (42, 50)]
assert ed[0]["text"].startswith(H.DISCLOSURE + "\n\n🔥") and ed[0]["entities"][1]["offset"] == 3 + n + 2
assert ed[0]["reply_markup"]["inline_keyboard"] == [[{"text": "🛒 구매하러 가기", "url": "https://link.coupang.com/a/zz"}]]
pj = {p.get("mid"): p for p in json.load(open("posts.json"))}
assert pj[102]["url"] == "https://link.coupang.com/a/zz" and pj[102]["text"].startswith(H.DISCLOSURE) and pj[100]["url"] == D("")["url"]
assert H.post_url(5) == "https://t.me/ch/5"
# 3-5-2) 답장 없이 제휴 링크만 보내도 됨: 같은 몰(쿠팡·토스) 사본 중 아직 안 바꾼 가장 최근 채널 글이 바뀜, 없으면 안내
H.tg = ch_tg; sent.clear()
H.post_or_draft(D("[쿠팡] 물티슈 100매"), "싸요", 8); H.post_or_draft(D("[토스] 사과 5kg"), "싸요", 8)  # 채널 103(쿠팡), 104(토스)
msg = lambda i, text: {"update_id": i, "message": {"message_id": 60 + i, "from": {"id": 42}, "text": text}}
UP = [msg(1, "https://link.coupang.com/a/yy"), msg(2, "https://toss.im/_m/abc"), msg(3, "https://link.coupang.com/a/zz2")]
sent.clear(); H.tg = lambda method, **p: sent.append((method, p)) or (UP if method == "getUpdates" and "offset" not in p else {"message_id": 1})
H.publish_approved()
ed = [(p["chat_id"], p["message_id"], p["reply_markup"]["inline_keyboard"][0][0]["url"]) for m, p in sent if m == "editMessageText"]
assert ed == [("@ch", 103, "https://link.coupang.com/a/yy"), ("42", 1, "https://link.coupang.com/a/yy"),
              ("@ch", 104, "https://toss.im/_m/abc"), ("42", 1, "https://toss.im/_m/abc")]  # 쿠팡 링크는 쿠팡 글(103)에, 토스는 토스 글(104)에
assert [p["text"] for m, p in sent if m == "sendMessage"][0].startswith("첫 줄에 제목")  # 바꿀 쿠팡 글이 더 없음(102·103 교체 끝) -> 안내
pj = {p.get("mid"): p for p in json.load(open("posts.json"))}
assert pj[103]["url"] == "https://link.coupang.com/a/yy" and pj[104]["text"].startswith(H.TOSS_NOTE) and H.pending_copy("https://toss.im/_m/x") is None
# 3-6) 상품 주소가 있는 딜(루리웹·클리앙): 채널 버튼은 상품 페이지 / 사본에 '상품 열기' / 옥션도 상품 페이지 딥링크
H.tg = ch_tg; sent.clear(); H.store_link = lambda u: "https://smartstore.naver.com/s/products/1"
H.post_or_draft(D("땅콩버터 파우더 3개"), "싸요", 8)  # 클리앙처럼 [몰]이 없어도 주소로 네이버 판단 -> 사본
kb = [p for m, p in sent if m == "copyMessage"][0]["reply_markup"]["inline_keyboard"]
assert kb[1] == [{"text": "📋 상품명 복사", "copy_text": {"text": H.keyword("땅콩버터 파우더 3개")}}, {"text": "🔗 쇼핑커넥트 열기", "url": H.NAVER_SC}]  # 네이버: 상품명 복사 + 쇼핑커넥트(자동 발급 금지)
assert kb[2][0]["text"].startswith("💰 네이버") and not any("상품 열기" in b["text"] for r in kb for b in r)
sent.clear(); H.post_or_draft(D("[네이버] 밀크티 베이스 1L"), "싸요", 8, q="광동 밀크티 베이스")  # Claude 검색어가 있으면 그걸 복사
assert [p for m, p in sent if m == "copyMessage"][0]["reply_markup"]["inline_keyboard"][1][0]["copy_text"] == {"text": "광동 밀크티 베이스"}
assert sent[0][1]["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://smartstore.naver.com/s/products/1"
sent.clear(); H.store_link = lambda u: "https://itempage3.auction.co.kr/DetailView.aspx?itemno=F1"
H.post_or_draft(D("[옥션] 마사지패드"), "싸요", 8)  # 옥션: 검색 딥링크는 안 되지만 상품 주소가 있으면 상품 페이지 딥링크
b = sent[0][1]["reply_markup"]["inline_keyboard"][0][0]
assert b["text"] == "🛒 구매하러 가기" and parse_qs(urlsplit(b["url"]).query)["m"] == ["auction"] and len(sent) == 1
assert sent[0][1]["text"].startswith(f"<i>{H.AFF_NOTE}</i>")
H.store_link = sl; H.tg = fake_tg

# 4) 전체 흐름: 30분 미만 글 제외, 점수 컷, 본 글 저장
sent.clear()
H.ai_pick = lambda prompt, lines: [{"i": 0, "score": 8, "comment": "좋음"}] if len(lines) == 1 else []
H.main()
drafts = [p for m, p in sent if m == "sendMessage" and "🔥" in p["text"]]  # (21시 이후엔 📋 모아보기 초안도 같이 나감)
assert len(drafts) == 1 and "휴지" in drafts[0]["text"] and {k for k in json.load(open("seen.json")) if k.startswith("ppomppu_")} == {"ppomppu_101"}
assert drafts[0]["chat_id"] == "@ch"  # ✅ 없이 채널에 바로
assert not [p for m, p in sent if m == "copyMessage" and p["chat_id"] == "42"]  # 이미 제휴 링크(자동 변환)면 관리자 사본 안 보냄
sent.clear(); H.main()  # 재실행: 같은 글 다시 안 보냄
assert not [p for m, p in sent if m == "sendMessage" and "🔥" in p["text"]]
# 4-6) Claude 답 처리(10/8 11:12 KeyError 'picks'로 실행 전체 실패, 15분 뒤 같은 목록에서 7점 2개): 도구 입력에 picks가 없으면(빈 입력·잘린 답) 예외 = 다음 실행에 다시 /
#      도구를 안 부르면 고른 게 없는 것([]) / 정상은 점수순·범위 밖 제외
#      main은 Claude가 실패해도 죽지 않음: 딜은 '본 글'로 안 남겨 다음 실행에 다시, 토스·Threads·리포트 단계는 그대로 돌아감
H.E["ANTHROPIC_API_KEY"], ph6 = "k", H.http
claude = lambda resp: (lambda url, body=None, headers=None, method=None: json.dumps(resp))
H.http = claude({"content": [{"type": "text", "text": "고를 게 없어요"}], "stop_reason": "end_turn"}); assert AI_PICK("p", ["a"]) == []
for stop in ("tool_use", "max_tokens"):
    H.http = claude({"content": [{"type": "tool_use", "name": "pick", "input": {}}], "stop_reason": stop})
    try:
        AI_PICK("p", ["a"]); raise AssertionError("picks 없는 답은 예외")
    except RuntimeError as e:
        assert stop in str(e)
H.http = claude({"content": [{"type": "text", "text": "x"}, {"type": "tool_use", "name": "pick", "input": {"picks": [{"i": 0, "score": 6, "comment": "a"},
                 {"i": 1, "score": 8, "comment": "b"}, {"i": 5, "score": 9, "comment": "범위 밖"}]}}], "stop_reason": "tool_use"})
assert [p["i"] for p in AI_PICK("p", ["a", "b"])] == [1, 0]
def ai_down(prompt, lines):
    raise RuntimeError("Claude 답 잘림(max_tokens)")
fd6, rp6, pa6, ran = H.fetch_deals, H.report, H.ai_pick, []
H.fetch_deals = lambda: [{"id": "ppomppu_999", "board": "뽐뿌", "title": "[쿠팡] 새 딜 (1,000원)", "hits": "", "age": 40, "desc": "", "url": "https://x"}]
H.report, H.ai_pick, H.http = lambda s: ran.append(1), ai_down, ph6
sent.clear(); H.main()
assert ran and "ppomppu_999" not in json.load(open("seen.json")) and not [p for m, p in sent if "새 딜" in str(p.get("text"))]
H.fetch_deals, H.report, H.ai_pick = fd6, rp6, pa6; del H.E["ANTHROPIC_API_KEY"]

# 4-2) 같은 딜이 여러 커뮤니티에: 이미 판단한 딜은 다른 곳에서 또 안 봄 / 동시에 올라오면 루리웹(상품 주소 있음)만 / 최근 올린 딜을 Claude에게 알려줌
it = lambda t, link, m, extra="": f"<item><title>{t}</title><link>{link}</link><pubDate>{ago(m)}</pubDate>{extra}</item>"
PP = '<rss><channel>' + it("[G마켓] 코카콜라 190ml 30캔 (19,000원/무료)", "http://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&amp;no=301", 45, "<hits> [1|50|1|0]</hits>") + '</channel></rss>'
RU = ('<rss><channel>' + it("[쿠팡] 휴지 30롤 / 9,900원", "https://bbs.ruliweb.com/market/board/1020/read/1", 45)
      + it("[G마켓] 코카콜라 190ml 30캔 / 19,000원", "https://bbs.ruliweb.com/market/board/1020/read/2", 45) + '</channel></rss>')
H.http = lambda url, *a, **k: PP if "rss.php" in url else RU if url == H.RULIWEB_RSS else ""
got = []; H.ai_pick = lambda prompt, lines: got.append((prompt, lines)) or []
H.main()
sj = json.load(open("seen.json"))
assert len(got) == 1 and got[0][1] == ["[루리웹] [G마켓] 코카콜라 190ml 30캔 / 19,000원 |  | 45분 전 | 분류: "]  # 휴지는 이미 판단(뽐뿌) -> 제외
assert "ruliweb_1" in sj and "ppomppu_301" in sj and H.dkey("[G마켓] 코카콜라 190ml 30캔") in sj
assert "최근 24시간에 이미 올린 딜" in got[0][0] and "휴지 30롤" in got[0][0].split("이미 올린 딜")[1]
json.dump({H.dkey("[쿠팡] 휴지 30롤"): time.time() - 2 * 86400}, open("seen.json", "w")); got.clear(); H.main()  # 24시간 지난 같은 상품은 새 딜로 판단
assert any("휴지 30롤" in l for l in got[0][1])
# 4-3) 한 번에 1개만 게시(꾸준히), 넘친 좋은 딜은 Claude 판단 그대로 보관 -> 다음 실행에 다시 묻지 않고 점수 높은 것부터 / 3시간 지나면 버림
#      (10/8 17:21 갈비·MSI 7점을 다시 물었더니 15분 뒤 둘 다 5점 미만 -> 못 올림) / 루리웹은 15분 지나면 판단(반응 수치가 없어서)
RU3 = '<rss><channel>' + "".join(it(f"[G마켓] 상품{n}번 특가 묶음 / {n},000원", f"https://bbs.ruliweb.com/market/board/1020/read/9{n}", 20) for n in range(3)) + '</channel></rss>'
H.http = lambda url, *a, **k: RU3 if url == H.RULIWEB_RSS else ""
posted, pod, asked = [], H.post_or_draft, []
H.post_or_draft = lambda d, c, sc, *a, **k: posted.append((d["id"], sc, c))
H.ai_pick = lambda prompt, lines: (asked.append(lines) if lines[0].startswith("[루리웹]") else None) or [{"i": i, "score": (8, 7, 9)[i], "comment": f"c{i}"} for i in range(len(lines))]  # 딜 판단만 셈(21시 넘으면 릴스 재료 채우기도 ai_pick 호출)
json.dump({}, open("seen.json", "w")); H.main()
sj = json.load(open("seen.json"))
assert posted == [("ruliweb_90", 8, "c0")] and len(asked) == 1 and len(asked[0]) == 3  # 20분 된 루리웹 글도 판단
assert {k for k in sj if k.startswith("hold_")} == {"hold_ruliweb_91", "hold_ruliweb_92"} and "ruliweb_91" in sj and H.dkey("[G마켓] 상품2번 특가 묶음") in sj
posted.clear(); H.main(); assert posted == [("ruliweb_92", 9, "c2")] and len(asked) == 1  # 다시 안 묻고, 높은 점수부터
posted.clear(); H.main(); assert posted == [("ruliweb_91", 7, "c1")] and len(asked) == 1
posted.clear(); H.main(); assert posted == [] and not [k for k in json.load(open("seen.json")) if k.startswith("hold_")]
sj = json.load(open("seen.json")); sj["hold_ruliweb_91"] = {"t": time.time() - 3 * 3600 - 60, "d": {"id": "ruliweb_91", "title": "x"}, "p": {"score": 9, "comment": "c"}}
json.dump(sj, open("seen.json", "w")); H.main()
assert posted == [] and "hold_ruliweb_91" not in json.load(open("seen.json"))  # 3시간 넘은 보관 딜은 식은 딜
sj = json.load(open("seen.json")); sj["hold_ruliweb_91"] = {"t": time.time() - 600, "d": {"id": "ruliweb_91", "title": "x"}, "p": {"score": 7, "comment": "c1"}}
json.dump(sj, open("seen.json", "w")); RU3 = RU3.replace("</channel>", it("[G마켓] 새상품 특가 묶음 / 3,000원", "https://bbs.ruliweb.com/market/board/1020/read/93", 20) + "</channel>")
H.main(); sj = json.load(open("seen.json"))  # 보관 딜이 있으면 그게 먼저, 새로 고른 좋은 딜은 보관
assert posted == [("ruliweb_91", 7, "c1")] and len(asked) == 2 and "hold_ruliweb_93" in sj and "hold_ruliweb_91" not in sj
# 4-5) 꾸준히(MIN_SCORE를 7로 올렸을 때): 8~24시에 마지막 딜 글이 45분 넘으면 7점이 없어도 6점 최고 1개 / 45분 안이거나 밤(0~8시)이거나 최고가 5점이면 안 올림
assert H.MIN_SCORE == 6 and H.FILL_SCORE == 6  # 10/8 진우: 기본은 6점도 바로
H.MIN_SCORE = 7
H.ai_pick = lambda prompt, lines: [{"i": 0, "score": 5, "comment": "c"}, {"i": 1, "score": 6, "comment": "c"}, {"i": 2, "score": 6, "comment": "c"}][:len(lines)]
tq, kfmt, pa2 = time.time, lambda s: time.strftime("%Y-%m-%d %H:%M", time.gmtime(s + 9 * 3600)), H.publish_approved
H.publish_approved = lambda: None  # 앞 테스트의 텔레그램 입력(✅)이 글을 기록하지 않게
for now, last, picks5, want in ((1791248400, 1791248400 - 3600, False, ["ruliweb_91"]), (1791248400, 1791248400 - 1200, False, []),
                                (1791223200, 1791223200 - 7200, False, []), (1791248400, 1791248400 - 3600, True, [])):  # 10/6 10:00 / 03:00 KST
    time.time = lambda n=now: n
    feed = '<rss><channel>' + "".join(it(f"[G마켓] 상품{k}번 특가 묶음 / {k},000원", f"https://bbs.ruliweb.com/market/board/1020/read/9{k}", 20) for k in range(3)) + '</channel></rss>'
    H.http = lambda url, *a, f=feed, **k: f if url == H.RULIWEB_RSS else ""
    json.dump([{"t": kfmt(last), "text": "🔥 예전 딜", "url": "https://x"}], open("posts.json", "w"))
    if picks5:
        H.ai_pick = lambda prompt, lines: [{"i": 0, "score": 5, "comment": "c"}]
    posted.clear(); json.dump({}, open("seen.json", "w")); H.main()
    assert [p[0] for p in posted] == want, (now, last, posted)
# 기본(6점): 빈틈과 상관없이(마지막 글 20분 전) 6점 최고 1개는 바로·나머지 6점은 보관, 5점은 절대 안 올림
H.MIN_SCORE, time.time = 6, lambda: 1791248400
H.ai_pick = lambda prompt, lines: [{"i": 0, "score": 5, "comment": "c"}, {"i": 1, "score": 6, "comment": "c"}, {"i": 2, "score": 6, "comment": "c"}][:len(lines)]
json.dump([{"t": kfmt(1791248400 - 1200), "text": "🔥 예전 딜", "url": "https://x"}], open("posts.json", "w"))
posted.clear(); json.dump({}, open("seen.json", "w")); H.main()
sj = json.load(open("seen.json"))
assert [p[0] for p in posted] == ["ruliweb_91"] and "hold_ruliweb_92" in sj and "hold_ruliweb_90" not in sj, (posted, [k for k in sj if k.startswith("hold_")])
time.time, H.publish_approved = tq, pa2
# 4-4) 바쁜 시간 뽐뿌 RSS(15개가 32분치): 다음 실행 전에 밀려날 글(32-20=12분↑)은 지금 판단 / 한가하면(목록 50분치) 그대로 30분↑만
BUSY = lambda ages: "<rss><channel>" + "".join(it(f"[G마켓] 바쁜상품{m}호 묶음 (1,000원)", f"http://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&amp;no={500 + m}", m, "<hits> [0|10|0|0]</hits>") for m in ages) + "</channel></rss>"
H.ai_pick = lambda prompt, lines: got.append(lines) or []
for ages, want in (([3, 10, 14, 25, 32], {514, 525, 532}), ([3, 14, 25, 32, 50], {532, 550})):
    H.http = lambda url, *a, x=BUSY(ages), **k: x if "rss.php" in url else ""
    got.clear(); json.dump({}, open("seen.json", "w")); H.main()
    assert {int(re.search(r"바쁜상품(\d+)호", l).group(1)) + 500 for l in got[0]} == want, (ages, got)
H.post_or_draft = pod
H.http = fake_http

# 5) 골드박스(최종 승인 후 API): 7시 이후 하루 1번 TOP5를 ✅ 없이 채널에 바로, 대가성 문구 맨 앞, 고른 순서대로
GB = [{"productName": f"상품{i}", "productPrice": 1000.0 * (i + 1), "productUrl": f"https://link.coupang.com/{i}"} for i in range(8)]
H.http = lambda url, *a, **k: json.dumps({"data": GB})
H.ai_pick = lambda prompt, lines: [{"i": 3, "score": 9, "comment": "a"}, {"i": 0, "score": 8, "comment": "b"}]
seen, sent[:], tt = {}, [], time.time
time.time = lambda: 1791235800; H.goldbox(seen); assert not sent  # 10/6 06:30 KST: 아직
time.time = lambda: 1791241200; H.goldbox(seen)  # 10/6 08:00 KST
m, p = sent[-1]; t = p["text"]
assert m == "sendMessage" and p["chat_id"] == "@ch" and p["reply_markup"]["inline_keyboard"][0][0]["url"] == H.GOLDBOX  # 초안(관리자) 아님
assert t.startswith("<i>" + H.DISCLOSURE) and "TOP2" in t and t.index("상품3") < t.index("상품0") and "4,000원" in t
assert json.load(open("posts.json"))[-1]["url"] == H.GOLDBOX  # 사이트·모아보기에도 기록
sent.clear(); H.goldbox(seen); assert not sent  # 같은 날 재실행 시 안 보냄
gp = []  # 살 만한 것만(10/7 진우): Claude가 하나도 안 고르면 안 올리고, 그날은 다시 안 고름(15분마다 Claude 호출 안 함)
H.ai_pick = lambda prompt, lines: gp.append(prompt) or []
seen.clear(); H.goldbox(seen); H.goldbox(seen); assert not sent and len(gp) == 1 and "억지로 5개 채우지 말고" in gp[0] and "goldbox_20261006" in seen
time.time = tt
# 5-5) 예약 게시(행사 알림): 시각 됐고 6시간 안이면 채널에 1번, 쿠팡 파트너스 링크면 대가성 문구 맨 앞 + 버튼, 지난 지 오래됐거나 아직이면 안 올림
json.dump([{"at": "2026-10-06 01:00", "text": "옛날", "button": "b", "url": "https://link.coupang.com/a/old"},
           {"at": "2026-10-06 09:30", "text": "⚡ <b>쿠가세</b>", "button": "🔔 알림 신청", "url": "https://link.coupang.com/a/x"},
           {"at": "2026-10-06 09:40", "text": "일반", "button": "b", "url": "https://example.com"},
           {"at": "2026-10-06 11:00", "text": "아직", "button": "b", "url": "https://link.coupang.com/a/y"}], open("events.json", "w"))
seen, sent[:], tt3 = {}, [], time.time
time.time = lambda: 1791248400; H.events(seen)  # 10/6 10:00 KST
assert [p["text"] for m, p in sent] == [f"<i>{H.DISCLOSURE}</i>\n\n⚡ <b>쿠가세</b>", "일반"] and sent[0][1]["chat_id"] == "@ch"
assert sent[0][1]["reply_markup"] == {"inline_keyboard": [[{"text": "🔔 알림 신청", "url": "https://link.coupang.com/a/x"}]]}
sent.clear(); H.events(seen); assert not sent  # 1번만
time.time = tt3; os.remove("events.json"); H.events({})  # 파일 없으면 아무것도 안 함
# 5-2) 최종 승인(API) 전: 아침 7시 이후 하루 1번 골드박스 파트너스 링크를 채널에 바로 (7시 전엔 안 보냄)
H.HAS_CP, tt = False, time.time
sent.clear(); seen = {}
time.time = lambda: 1791235800; H.goldbox(seen); assert not sent  # 10/6 06:30 KST: 아직
time.time = lambda: 1791241200; H.goldbox(seen)  # 10/6 08:00 KST
m, p = sent[-1]
assert m == "sendMessage" and p["chat_id"] == "@ch" and p["text"].startswith("<i>" + H.DISCLOSURE) and p["reply_markup"]["inline_keyboard"][0][0]["url"] == H.GOLDBOX
sent.clear(); H.goldbox(seen); assert not sent  # 같은 날 1번만
time.time, H.HAS_CP = tt, True
# 5-4) Threads 실패 알림: 개발자 계정 잠김(API access blocked)이면 '계정 확인' 안내, 그 외엔 토큰 재발급 안내
eb = Exception("400"); eb.body = '{"error": {"message": "API access blocked.", "code": 200}}'
assert "계정 확인" in H.threads_hint(eb) and "토큰" in H.threads_hint(Exception("x"))
# 5-3) 토스 쉐어링크 Open API: 토스 상품 주소 -> 쉐어링크(tacaId), 토큰은 toss.json에 두고 재사용, 발급 실패면 주소 그대로(사본으로 수동)
#      하루특가: 9시 이후 하루 1번 채널에 바로(품절·발급 실패 상품 빼고), posts.json(사이트)엔 안 남김
H.E.update(TOSS_ACCESS_KEY="ak", TOSS_SECRET_KEY="sk", TOSS_PUBLISHER_ID="pub-1"); H.HAS_TOSS, ph, pa = True, H.http, H.ai_pick
tcalls = []
def toss_http(url, body=None, headers=None, method=None):
    tcalls.append(url)
    if url == "https://oauth2.cert.toss.im/token":
        assert method == "POST" and b"grant_type=client_credentials" in body and b"client_secret=sk" in body and b"sharelink%3Awrite" in body
        return json.dumps({"access_token": "TK", "expires_in": 31535999})
    assert url.startswith(H.TOSS_API) and headers["Authorization"] == "Bearer TK"
    if url.endswith("/links"):
        assert body["publisherId"] == "pub-1"
        n = body.get("tacaId") or body.get("tacaItemId")
        return json.dumps({"resultType": "SUCCESS", "success": {"shortUrl": f"https://toss.im/_m/{n}"}} if n in (123, 1, 3)
                          else {"resultType": "FAIL", "error": {"reason": "발급 제한 상품"}})
    if url.endswith("/products/today-deals?size=30"):
        return json.dumps({"resultType": "SUCCESS", "success": {"items": [{"tacaItemId": i, "displayName": f"토스상품{i}",
                          "displayPrice": 1000 * (i + 1), "discountRate": 10 * i, "isSoldOut": i == 2} for i in range(4)]}})
    raise AssertionError(url)
H.http = toss_http
if os.path.exists("toss.json"): os.remove("toss.json")
assert H.affiliate("https://toss.shopping/t/123") == ("https://toss.im/_m/123", True) and H.aff_note("https://toss.im/_m/123") == H.TOSS_NOTE
assert H.affiliate("https://toss.shopping/t/999") == ("https://toss.shopping/t/999", False)  # 발급 제한 -> 주소 그대로(사본)
assert H.aff_note("https://toss.shopping/t/999") == "" and H.aff_note("https://toss.shopping/_m/Pe9kaNsx") == H.TOSS_NOTE  # 상품 주소엔 대가성 문구 X, 진우가 붙인 단축 쉐어링크(10/7 트레비)엔 O
assert tcalls.count("https://oauth2.cert.toss.im/token") == 1 and json.load(open("toss.json"))["token"] == "TK"  # 토큰은 1번만 발급
offered = []
H.ai_pick = lambda prompt, lines: offered.extend(lines) or [{"i": 0, "score": 9, "comment": "가"}, {"i": 2, "score": 8, "comment": "나"}, {"i": 1, "score": 7, "comment": "다"}]
seen, sent[:], n0 = {}, [], len(json.load(open("posts.json")))
time.time = lambda: 1791241200; H.toss_deals(seen); assert not sent and not offered  # 10/6 08:00 KST: 9시 전
time.time = lambda: 1791248400; H.toss_deals(seen)  # 10:00 KST
m, p = sent[-1]; t = p["text"]
assert m == "sendMessage" and p["chat_id"] == "@ch" and t.startswith(f"<i>{H.TOSS_NOTE}</i>") and "TOP2" in t
assert not [l for l in offered if "토스상품2" in l] and "토스상품0" not in t  # 품절은 후보에서 빼고, 발급 실패(0)는 글에서 뺌
assert t.index('href="https://toss.im/_m/3"') < t.index('href="https://toss.im/_m/1"') and "4,000원</b> (30%↓)" in t
sent.clear(); H.toss_deals(seen); assert not sent  # 하루 1번
assert len(json.load(open("posts.json"))) == n0  # API 상품은 사이트에 안 남김
th = []  # 하루특가는 Threads에도 1개(신청서 서비스 = 텔레그램 채널 + 스레드 자동 게시): 대가성 문구 맨 앞, 500자 안, 채널과 같은 순서, HTML 태그 없음
def toss_th(url, body=None, headers=None, method=None):
    if not url.startswith(H.THREADS):
        return toss_http(url, body, headers, method)
    th.append(url)
    return '{"id": "c1"}'
H.http, H.E["THREADS_TOKEN"], sl, H.time.sleep = toss_th, "tk", H.time.sleep, lambda s: None
seen.clear(); sent.clear(); H.toss_deals(seen)
txt = parse_qs(urlsplit([u for u in th if "/threads?" in u][0]).query)["text"][0]
assert txt.startswith(H.TOSS_NOTE) and "TOP2" in txt and txt.index("https://toss.im/_m/3") < txt.index("https://toss.im/_m/1") and "4,000원" in txt and "<" not in txt and len(txt) <= 500
assert any("threads_publish" in u for u in th) and [m for m, p in sent] == ["sendMessage"]
def th_fail(url, *a, **k):  # Threads가 막혀도(10/6 같은 계정 잠김) 채널 글은 이미 올라갔으니 다음 실행에 또 안 올림
    if url.startswith(H.THREADS):
        raise Exception("blocked")
    return toss_http(url, *a, **k)
H.http = th_fail; seen.clear(); sent.clear()
try:
    H.toss_deals(seen)
except Exception:
    pass
sent.clear(); H.toss_deals(seen); assert not sent
del H.E["THREADS_TOKEN"]; H.time.sleep = sl
# 5-3b) 토스 베스트(지금 많이 팔리는 상품, 10/7 진우 제안): 10~20시 2시간마다 1번씩(10/9 '쿠팡·토스 주력' 6번), Claude가 '진짜 싼' 것만(없으면 안 올림), 리뷰를 판단 재료로, 3일 안에 올린 상품 제외, 사이트 미기록
def best_http(url, body=None, headers=None, method=None):
    if url.endswith("/products/best-selling?size=30"):
        return json.dumps({"resultType": "SUCCESS", "success": {"items": [{"tacaItemId": i, "displayName": f"베스트{i}", "displayPrice": 6930,
                          "discountRate": 88, "isSoldOut": i == 4, "reviewScore": 4.8, "reviewCount": 1523} for i in (1, 3, 4, 5)]}})
    return toss_http(url, body, headers, method)
offered.clear(); H.http = best_http
H.ai_pick = lambda prompt, lines: offered.extend(lines) or ([{"i": 0, "score": 8, "comment": "개당 99원"}, {"i": 1, "score": 7, "comment": "나"}]
                                                           if "할인율은 정가를 부풀린" in prompt and len(lines) == 3 else [])
seen.clear(); sent.clear(); time.time = lambda: 1791248340; H.toss_deals(seen, True); assert not sent and not offered  # 09:59 KST: 10시 전
time.time = lambda: 1791257400; H.toss_deals(seen, True)  # 12:30
t = sent[-1][1]["text"]
assert t.startswith(f"<i>{H.TOSS_NOTE}</i>") and "살 만한 2개" in t and 'href="https://toss.im/_m/1"' in t and "개당 99원" in t and "하루특가" not in t
assert len(offered) == 3 and "베스트4" not in str(offered) and "리뷰 4.8점 1,523개" in offered[0] and "tb_1" in seen and "tb_3" in seen
sent.clear(); H.toss_deals(seen, True); assert not sent  # 같은 회차 1번
offered.clear(); time.time = lambda: 1791271800; H.toss_deals(seen, True)  # 16:30 회차(10/8 하루 3번): 1·3 빠지고 5만 -> 안 고르면 안 올림
assert offered == ["베스트5 | 6,930원 (88% 할인) | 리뷰 4.8점 1,523개"] and not sent and "tossbest_20261006_16" in seen
offered.clear(); time.time = lambda: 1791285000; H.toss_deals(seen, True)  # 20:10: 낮에 올린 1·3은 후보에서 빠짐 -> 5만 남음 -> Claude가 안 고르면 안 올림
assert offered == ["베스트5 | 6,930원 (88% 할인) | 리뷰 4.8점 1,523개"] and not sent and "tossbest_20261006_20" in seen
sent.clear(); H.toss_deals(seen, True); assert not sent and not offered[1:]
assert H.TOSS_BEST_HOURS == (10, 12, 14, 16, 18, 20)
for hh, ts in ((10, 1791248700), (14, 1791263100), (18, 1791277500)):  # 10:05·14:05·18:05 회차도 1번씩
    s2 = {}; time.time = lambda ts=ts: ts; H.toss_deals(s2, True); assert f"tossbest_20261006_{hh}" in s2, (hh, s2)
# 오늘 하루특가에 올린 상품도 베스트에서 빠짐 (10/7 12시 첫 베스트 글에 9시 하루특가의 초정 탄산수가 또 나왔음)
seen.clear(); sent.clear(); offered.clear(); time.time = lambda: 1791248400
H.ai_pick = lambda prompt, lines: offered.extend(lines) or ([{"i": 0, "score": 9, "comment": "가"}, {"i": 2, "score": 8, "comment": "나"}, {"i": 1, "score": 7, "comment": "다"}]
                                                           if "하루특가" in prompt else [])
H.toss_deals(seen); offered.clear(); time.time = lambda: 1791257400; H.toss_deals(seen, True)
assert offered == ["베스트5 | 6,930원 (88% 할인) | 리뷰 4.8점 1,523개"]
# 5-3c) 토스 카테고리 베스트(10/8 진우: 베스트 랭킹 페이지): 17시 1번, 카테고리 트리에서 이름으로 식품·생활용품 ID를 찾아 그 베스트만(패션 X),
#       두 카테고리에 겹친 상품은 1번, 3일 안에 올린 상품 제외, 베스트와 같은 판단 기준, 이름이 바뀌어 못 찾으면 예외(로그에 실제 이름)
cats_called, prompts = [], []
def cat_http(url, body=None, headers=None, method=None):
    if url.endswith("/categories"):
        return json.dumps({"resultType": "SUCCESS", "success": {"categories": [{"categoryId": 100, "level": 1, "displayName": "패션", "children": []},
                          {"categoryId": 200, "level": 1, "displayName": "식품", "children": []}, {"categoryId": 300, "level": 1, "displayName": "생활용품", "children": []},
                          {"categoryId": 400, "level": 1, "displayName": "뷰티", "children": []}]}})
    if "/products/best-categories/" in url:
        assert url.endswith("?size=30"); cid = int(url.split("/best-categories/")[1].split("?")[0]); cats_called.append(cid)
        return json.dumps({"resultType": "SUCCESS", "success": {"items": [{"tacaItemId": i, "displayName": f"카테{i}", "displayPrice": 7900, "discountRate": 0,
                          "isSoldOut": False} for i in {200: (1, 21), 300: (21, 22), 400: (), 100: ()}[cid]]}})  # 1 = 이미 올린 상품, 21 = 두 카테고리에 다 있음
    if url.endswith("/links"):
        return json.dumps({"resultType": "SUCCESS", "success": {"shortUrl": f"https://toss.im/_m/{body['tacaItemId']}"}})
    raise AssertionError(url)
offered.clear(); H.http = cat_http
H.ai_pick = lambda prompt, lines: prompts.append(prompt) or offered.extend(lines) or [{"i": 0, "score": 8, "comment": "단위가격 좋음"}, {"i": 1, "score": 7, "comment": "나"}]
seen, sent[:] = {"tb_1": 1791241200}, []
time.time = lambda: 1791273000; H.toss_deals(seen, "cat"); assert not sent and not cats_called  # 10/6 16:50 KST: 17시 전
time.time = lambda: 1791274200; H.toss_deals(seen, "cat")  # 17:10
t = sent[-1][1]["text"]
assert cats_called == [200, 300, 400] and t.startswith(f"<i>{H.TOSS_NOTE}</i>") and "식품·생활용품·뷰티 베스트 중 살 만한 2개" in t and 'href="https://toss.im/_m/21"' in t  # 10/6 = 279일째 -> 다른 카테고리 [패션, 뷰티] 중 279 % 2 = 1번(뷰티)
assert offered == ["카테21 | 7,900원 (0% 할인)", "카테22 | 7,900원 (0% 할인)"] and prompts == [H.BEST_PROMPT]
assert "tosscat_20261006_17" in seen and "tb_21" in seen and "tb_22" in seen
sent.clear(); H.toss_deals(seen, "cat"); assert not sent  # 하루 1번
time.time, cats_called[:] = (lambda: 1791274200 + 86400), []; H.toss_deals(seen, "cat"); assert cats_called == [200, 300, 100]  # 다음 날은 패션(날마다 돌아감)
def cat_renamed(url, *a, **k):
    if url.endswith("/categories"):
        return json.dumps({"resultType": "SUCCESS", "success": {"categories": [{"categoryId": 9, "level": 1, "displayName": "푸드", "children": []}]}})
    return cat_http(url, *a, **k)
H.http, seen = cat_renamed, {}
try:
    H.toss_deals(seen, "cat"); raise AssertionError("카테고리 이름을 못 찾으면 예외")
except RuntimeError as e:
    assert "푸드" in str(e) and not seen and not sent
import inspect; assert 'toss_deals(s, "cat")' in inspect.getsource(H.main)  # 실행 순서에 들어 있음
assert len(json.load(open("posts.json"))) == n0
# 5-3d) 토스 딜 목록 대조(10/9 진우 '토스 딜 직접 추출' -> '하루 기록 먼저'): 쉐어링크 없는 최근 3일 [토스] 딜만, 토스 API 목록(하루특가·카테고리 베스트·베스트)에서
#       이름 겹침 2개 이상 후보 -> Claude 확인 8점 이상만 '찾음', 실행 로그에만(채널 글·posts.json 그대로), 같은 딜은 1번, 목록은 seen에 저장(카테고리 하루·베스트 1시간)
import io, contextlib
mcalls, mprompts = [], []
def match_http(url, *a, **k):
    mcalls.append(url.split("/openapi")[-1])
    it = lambda *xs: json.dumps({"resultType": "SUCCESS", "success": {"items": [{"tacaItemId": i, "displayName": n, "displayPrice": p} for i, n, p in xs]}})
    if url.endswith("/categories"):
        return json.dumps({"resultType": "SUCCESS", "success": {"categories": [{"categoryId": 200, "displayName": "식품"}, {"categoryId": 300, "displayName": "생활용품"}]}})
    if "/best-categories/300" in url:
        assert url.endswith("?size=100"); return it((31, "모나리자 에코 미용티슈 300매, 12개", 11990), (32, "깨끗한나라 화장지 30롤", 15900))
    if "/best-categories/200" in url:
        return it((41, "제주 극조생 감귤 5kg", 9900))
    if url.endswith("/products/today-deals?size=30"):
        return it((51, "광동 비타500 100ml 20병", 9900))
    if url.endswith("/products/best-selling?size=100"):
        return it((31, "모나리자 에코 미용티슈 300매, 12개", 11990), (61, "삼다수 2L 12병", 9000))
    raise AssertionError(url)
def match_pick(prompt, lines):
    mprompts.append((prompt, lines))
    return [{"i": 0, "score": 9 if "모나리자" in lines[0] else 6, "comment": "같은 상품"}]
H.http, H.ai_pick, pj0 = match_http, match_pick, open("posts.json").read()
now = 1791259200  # 10/6 13:00 KST
time.time = lambda: now
kt = lambda h: time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 9 * 3600 - h * 3600))
mp = [{"t": kt(2), "text": "🔥 [토스] 모나리자 에코 미용티슈 300매 12입 (10,990원/무배)", "url": "https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&no=1"},
      {"t": kt(1), "text": "🔥 [토스] 제주 극조생감귤 10kg (12,900원/무배)", "url": "https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&no=2"},
      {"t": kt(1), "text": "🔥 [토스] 이미 링크 붙은 딜 (1,000원)", "url": "https://toss.shopping/_m/abc"},
      {"t": kt(1), "text": "🔥 [쿠팡] 쿠팡 딜 모나리자 에코 (1,000원)", "url": "https://www.coupang.com/vp/products/1"},
      {"t": kt(80), "text": "🔥 [토스] 모나리자 에코 오래된 딜 (1,000원)", "url": "https://www.ppomppu.co.kr/x"},
      {"t": kt(1), "text": "🔥 [토스] 아무거나 전혀 다른 상품 (1,000원)", "url": "https://www.ppomppu.co.kr/y"}]
json.dump(mp, open("posts.json", "w"), ensure_ascii=False)
seen, out = {}, io.StringIO()
with contextlib.redirect_stdout(out): H.toss_match_log(seen)
log = out.getvalue()
assert "toss match" in log and "모나리자 에코 미용티슈 300매 12입 (10,990원/무배) -> 모나리자 에코 미용티슈 300매, 12개 11,990원 (id 31, 9점)" in log, log
assert "제주 극조생감귤 10kg (12,900원/무배) -> 없음" in log and "아무거나 전혀 다른 상품 (1,000원) -> 없음 | 후보 0/" in log  # 감귤 5kg = 용량 달라 Claude 6점 -> 없음, 겹침 없으면 Claude 안 부름
assert "이미 링크" not in log and "쿠팡 딜" not in log and "오래된" not in log and len(mprompts) == 2  # 쉐어링크 있는 딜·다른 몰·3일 지난 딜 제외
assert mprompts[0][1][0] == "모나리자 에코 미용티슈 300매, 12개 | 11,990원" and "깨끗한나라" not in str(mprompts[0][1]) and "모나리자 에코 미용티슈 300매 12입" in mprompts[0][0]
assert sorted(mcalls) == sorted(["/products/today-deals?size=30", "/categories", "/products/best-categories/200?size=100", "/products/best-categories/300?size=100", "/products/best-selling?size=100"])
assert json.load(open("posts.json")) == mp and seen["tosslist_cat"]["items"][0] == [51, "광동 비타500 100ml 20병", 9900]  # 기록만(글 그대로), 목록은 저장
mcalls.clear(); mprompts.clear(); H.toss_match_log(seen); assert not mcalls and not mprompts  # 같은 딜은 1번
mp.append({"t": kt(0), "text": "🔥 [토스쇼핑] 삼다수 2L 12병 (8,500원)", "url": "https://www.ppomppu.co.kr/z"}); json.dump(mp, open("posts.json", "w"), ensure_ascii=False)
H.toss_match_log(seen); assert mcalls == [] and len(mprompts) == 1  # 같은 시간대 새 딜 -> 저장해 둔 목록 그대로(API 다시 안 부름)
time.time = lambda: now + 3600; mp.append({"t": kt(-1), "text": "🔥 [토스] 비타500 100ml 20병 (8,900원)", "url": "https://www.ppomppu.co.kr/w"}); json.dump(mp, open("posts.json", "w"), ensure_ascii=False)
H.toss_match_log(seen); assert mcalls == ["/products/best-selling?size=100"]  # 1시간 지나면 베스트만 다시(카테고리·하루특가는 하루 1번)
H.HAS_TOSS = False; mcalls.clear(); json.dump(mp + [{"t": kt(-1), "text": "🔥 [토스] 새 딜 (1원)", "url": "https://www.ppomppu.co.kr/v"}], open("posts.json", "w"), ensure_ascii=False)
H.toss_match_log({}); assert not mcalls; H.HAS_TOSS = True  # 토스 API 키 없으면 아무것도 안 함
assert "toss_match_log, lambda s: digest" in inspect.getsource(H.main)
open("posts.json", "w").write(pj0)
os.remove("toss.json"); time.time, H.HAS_TOSS, H.http, H.ai_pick = tt, False, ph, pa

# 6) 사이트 생성: 이모지(UTF-16 2유닛) 뒤 링크 오프셋, 제목 추출, 페이지/사이트맵 생성
import build_site as S
assert 'href="' + S.GOLDBOX + '"' in S.page("t", "") and S.GOLDBOX.startswith("https://link.coupang.com/a/")  # 사이트 위쪽 골드박스 버튼(파트너스 링크)
assert S.to_html("🔥 a <b> 뽐뿌", [{"type": "text_link", "offset": 9, "length": 2, "url": "https://x"}]) == \
    '🔥 a &lt;b&gt; <a href="https://x" rel="nofollow noopener" target="_blank">뽐뿌</a>'
assert S.title_of("이 포스팅은 쿠팡 파트너스 활동의 일환으로, 수수료\n\n⏰ 오늘의 골드박스 TOP5") == "오늘의 골드박스 TOP5"
assert S.title_of("🔥 [롯데온] 파스타 (14,490원)") == "[롯데온] 파스타 (14,490원)"
n = S.build(posts, "docs")
idx = open("docs/index.html").read()
grid = idx.split('class="grid"')[1]  # 홈 격자(맨 위 카드 딜 칸은 앞 테스트가 오늘 카드를 만들었으면 따로 있음)
assert n == 1 and grid.count('class="g"') == 1 and "<h3><a href=\"https://hotdealpick.kr/p/0.html\">휴지</a></h3>" in grid and "쿠팡 · " in grid and 'href="https://buy"' in grid
assert os.path.exists("docs/p/0.html") and os.path.exists("docs/.nojekyll") and open("docs/CNAME").read() == "hotdealpick.kr" and os.path.exists("docs/all.html")
assert '<a href="https://src" rel="nofollow noopener" target="_blank">뽐뿌</a>' in open("docs/p/0.html").read()  # 딜 페이지: 제목 줄 잘라낸 뒤에도 링크 위치 정확
assert "p/0.html" in open("docs/sitemap.xml").read() and "all.html" in open("docs/sitemap.xml").read() and "쿠팡 파트너스" in open("docs/p/0.html").read()
assert S.build([], "docs2") == 0 and "준비 중" in open("docs2/index.html").read()
# 6-2) 홈 맨 위 '카드 딜': 가장 최근 카드 날짜의 딜을 카드와 같은 번호로, 누르면 바로 구매(구매 주소 없으면 딜 페이지), 모아보기 글 제외,
#      큰 터치 버튼(.pick)·aria-label, 카드가 없으면 안 보임 (10/8 진우: 인스타 캡션 링크가 안 눌려서 프로필 링크 → 한 번에 구매)
os.makedirs("docs3/cards", exist_ok=True)
for d in ("2026-10-07", "2026-10-08"):
    open(f"docs3/cards/{d}.png", "wb").write(b"x")
pp = [{"t": "2026-10-07 21:00", "text": "🔥 [쿠팡] 어제딜 (1,000원)", "url": "https://old"},
      {"t": "2026-10-08 09:00", "text": "🔥 [G마켓] 첫딜 (2,000원)", "url": "https://a1"},
      {"t": "2026-10-08 12:00", "text": "📋 오늘의 딜 모아보기", "url": "https://x"},
      {"t": "2026-10-08 15:00", "text": "🔥 [토스쇼핑] 둘째 <딜> (3,000원)"},
      {"t": "2026-10-08 16:00", "text": "🔥 [우리동네gs]김치라면 대컵1+1(1,850원/픽업)", "url": "https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&no=7"}]
S.build(pp, "docs3"); idx = open("docs3/index.html").read()
top = idx.split('id="today"')[1].split("</section>")[0]
assert "10월 8일 카드 딜" in top and "어제딜" not in top and "모아보기" not in top and top.count('class="pick"') == 3
# 커뮤니티 원글로 가는 딜(뽐뿌·루리웹·클리앙): 이름을 정확히('원글'), 원글이 지워져도 '같은 상품 찾기'(네이버쇼핑, [몰]·가격 뺀 이름) — 쇼핑몰 링크 딜엔 안 붙음 (10/8 01번 원글 삭제)
import html, urllib.parse
find = "https://search.shopping.naver.com/search/all?query=" + urllib.parse.quote("김치라면 대컵1+1")
assert top.count('class="alt"') == 1 and f'<a class="alt" href="{html.escape(find)}"' in top and "3번 원글이 안 열리면 같은 상품 찾기" in top
assert "<b>03</b><span>[우리동네gs]김치라면 대컵1+1(1,850원/픽업)</span><em>원글 →</em>" in top and "원글에서 구매 링크 보기" in top and top.count("구매 →") == 2
deal = open("docs3/p/4.html").read()
assert "📄 원글에서 구매 링크 보기" in deal and 'class="btn2"' in deal and "🛒 구매하러 가기" not in deal and 'class="btn2"' not in open("docs3/p/1.html").read()
assert S.find_url("[쿠팡] 듀라셀 AA 20개입 1개/ 9,730원").endswith(urllib.parse.quote("듀라셀 AA 20개입 1개")) and not S.community("https://click.linkprice.com/x") and not S.community(None)
assert top.index("<b>01</b><span>[G마켓] 첫딜") < top.index("<b>02</b><span>[토스쇼핑] 둘째 &lt;딜&gt;") and 'href="https://a1"' in top
assert 'href="https://hotdealpick.kr/p/3.html"' in top and 'aria-label="1번 [G마켓] 첫딜 (2,000원) 구매하러 가기"' in top and idx.index('id="today"') < idx.index("어제딜")
S.build(pp, "docs4"); assert 'id="today"' not in open("docs4/index.html").read()  # 카드 폴더 없으면 안 보임
# 6-3) 카드 순서(10/8 진우 '쿠팡·토스 잘 팔리게'): 점수 높은 순, 같은 점수면 제휴 링크(쿠팡·토스 등) 먼저, 그다음 게시 순, 모아보기·다른 날 제외
#      카드·인스타 캡션·릴스·사이트 맨 위 카드 딜 번호가 모두 이 순서(day_deals 하나)
dd = [{"t": "2026-10-09 09:00", "text": "🔥 A 7점 원글", "url": "https://www.ppomppu.co.kr/x", "s": 7},
      {"t": "2026-10-09 10:00", "text": "🔥 B 8점", "url": "https://x.com", "s": 8},
      {"t": "2026-10-09 11:00", "text": "🔥 C 7점 쿠팡", "url": "https://link.coupang.com/a/x", "s": 7},
      {"t": "2026-10-09 12:00", "text": "🔥 D 7점 토스", "url": "https://toss.im/_m/x", "s": 7},
      {"t": "2026-10-09 13:00", "text": "📋 모아보기", "url": "https://x", "s": 9},
      {"t": "2026-10-08 13:00", "text": "🔥 어제", "s": 9}]
assert [i for i, _ in S.day_deals(dd, "2026-10-09")] == [1, 2, 3, 0] and S.aff("https://link.coupang.com/a/x") and S.aff("https://toss.im/_m/x") and not S.aff("https://www.ppomppu.co.kr/x") and not S.aff(None)
assert S.toss_share("https://toss.shopping/_m/x") and S.toss_share("https://toss.im/_m/x") and S.toss_share("https://toss.shopping/t/9?k=1&referrer=affiliate")
assert not S.toss_share("https://toss.shopping/t/9") and not S.aff("https://toss.shopping/t/9") and not S.toss_share(None)  # 발급 실패로 남은 상품 주소는 제휴 아님(사이트 제휴 먼저·토스 칸 X)
pj = open("posts.json").read(); json.dump(dd, open("posts.json", "w"))
assert [r.split(". ")[1][0] for r in H.card_caption("2026-10-09")[0]] == ["B", "C", "D", "A"]
os.makedirs("docs/cards", exist_ok=True); json.dump([3, 0], open("docs/cards/2026-10-09.json", "w"))  # 카드를 만들 때 고정한 순서가 있으면 그대로(뒤에 딜이 더 올라와도 번호 유지)
assert [r.split(". ")[1][0] for r in H.card_caption("2026-10-09")[0]] == ["D", "A"] and [i for i, _ in S.card_order(dd, "2026-10-09")] == [3, 0]
os.remove("docs/cards/2026-10-09.json")
open("posts.json", "w").write(pj)
# 6-4) 모바일 격자(10/8 진우 '스크롤 길어 보기 힘듦 → 2열 격자 + 날짜 탭', '쿠팡·토스 먼저'): 홈 = 맨 위 카드 딜(카드·캡션의 6개만) + 날짜 탭(최근 2일·지난 딜 전체)
#      + 최근 2일 격자(날짜 안에서 제휴 링크 딜 먼저, 그다음 최신 순), 지난 딜은 all.html. 칸 = 몰·이름·가격·단위가격·버튼(구매 / 원글+같은 상품 찾기 / 자세히)
g = [{"t": "2026-10-09 08:00", "text": "🔥 [토스쇼핑] 생수 40병 (5,900원/무배)", "url": "https://toss.im/_m/w", "s": 6, "unit": "병당 148원"},
     {"t": "2026-10-09 12:00", "text": "🔥 [뽐뿌몰] 라면 (1,850원/픽업)", "url": "https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&no=9", "s": 7},
     {"t": "2026-10-09 13:00", "text": "🔥 [G마켓] 주소없는딜 (3,000원)", "s": 6},
     {"t": "2026-10-08 20:00", "text": "🔥 [쿠팡] 어제딜 (1,000원)", "url": "https://link.coupang.com/a/z", "s": 9},
     {"t": "2026-10-07 20:00", "text": "🔥 [11번가] 그제딜 (1,000원)", "url": "https://x.com/y", "s": 9}] + \
    [{"t": f"2026-10-09 14:0{k}", "text": f"🔥 [G마켓] 추가딜{k} (1,000원)", "url": f"https://g{k}", "s": 5} for k in range(5)]
os.makedirs("docs5/cards", exist_ok=True); open("docs5/cards/2026-10-09.png", "wb").write(b"x")
S.build(g, "docs5"); idx, allp = open("docs5/index.html").read(), open("docs5/all.html").read()
assert idx.split('id="today"')[1].split("</section>")[0].count('class="pick"') == 6  # 맨 위 카드 딜은 6개만(그날 딜 8개)
json.dump([6, 2, 1], open("docs5/cards/2026-10-09.json", "w")); S.build(g, "docs5")  # 카드 순서 파일이 있으면 그 순서·개수 그대로
top5 = open("docs5/index.html").read().split('id="today"')[1].split("</section>")[0]
assert top5.count('class="pick"') == 3 and top5.index("<b>01</b><span>[G마켓] 추가딜1") < top5.index("<b>02</b><span>[G마켓] 주소없는딜") < top5.index("<b>03</b><span>[뽐뿌몰] 라면")
os.remove("docs5/cards/2026-10-09.json"); S.build(g, "docs5")
tabs = idx.split('<nav class="tabs"')[1].split("</nav>")[0]
assert '>10/9</a>' in tabs and '>10/8</a>' in tabs and "10/7" not in tabs and 'href="https://hotdealpick.kr/all.html">지난 딜 전체' in tabs
d0 = idx.split('id="d0"')[1].split("</section>")[0]
assert "10월 9일 딜 8개" in d0 and d0.count('class="g"') == 8 and "그제딜" not in idx.split('<nav class="tabs"')[1] and 'id="d1"' in idx and "어제딜" in idx and 'id="d2"' not in idx
assert d0.index("생수 40병") < d0.index("추가딜4") < d0.index("추가딜0") < d0.index("라면")  # 토스(제휴)는 오래됐어도 맨 앞, 나머지는 최신 순
assert '<div class="s">토스쇼핑 · 08:00</div>' in d0 and '<div class="pr">5,900원</div>' in d0 and '<div class="u">병당 148원</div>' in d0 and 'href="https://toss.im/_m/w" rel="nofollow sponsored noopener"' in d0
assert 'class="o" href="https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&amp;no=9"' in d0 and '🔎 같은 상품 찾기' in d0 and 'aria-label="라면 원글에서 구매 링크 보기"' in d0
assert f'class="o" href="https://hotdealpick.kr/p/2.html" aria-label="주소없는딜 자세히 보기">자세히 →' in d0
assert all(f"{w}" in allp for w in ("10월 9일 딜 8개", "10월 8일 딜 1개", "10월 7일 딜 1개")) and 'id="today"' not in allp
# 6-5) 토스 칸(10/9 진우 '쿠팡·토스 주력'): 홈 맨 위 카드 딜 다음 = 최근 2일 커뮤니티 딜 중 토스 쉐어링크 딜(최신 6개) + 텔레그램 토스 추천 버튼,
#      탭 맨 앞 '💙 토스'. 토스 API 상품은 사이트에 안 올림(승인 범위 = 채널·Threads) -> 버튼은 채널 웹 보기로. 지난 딜 전체엔 토스 칸 없음
tsec = idx.split('id="toss"')[1].split("</section>")[0]
assert idx.index('id="today"') < idx.index('id="toss"') < idx.index('<nav class="tabs"') and "💙 토스 딜 1개" in tsec and tsec.count('class="g"') == 1 and "생수 40병" in tsec
assert f'href="{S.CHANNEL_WEB}"' in tsec and S.CHANNEL_WEB == "https://t.me/s/hotdeal_pick" and 'id="toss"' not in allp
assert '"날짜별 딜"><a href="https://hotdealpick.kr/#toss">💙 토스</a><a href="https://hotdealpick.kr/#d0">10/9</a>' in tabs
tt = [{"t": f"2026-10-0{d} 1{k}:00", "text": f"🔥 [토스] 토스{d}{k} (1,000원)", "url": f"https://toss.im/_m/{d}{k}", "s": 6} for d in (7, 8, 9) for k in range(4)]
tt += [{"t": "2026-10-09 15:00", "text": "🔥 [토스] 원글토스 (1,000원)", "url": "https://www.ppomppu.co.kr/x", "s": 7},
       {"t": "2026-10-09 15:30", "text": "🔥 [토스] 상품주소토스 (1,000원)", "url": "https://toss.shopping/t/77", "s": 7}]  # 발급 실패로 남은 상품 주소(쉐어링크 아님)
S.build(tt, "docs6"); ts6 = open("docs6/index.html").read().split('id="toss"')[1].split("</section>")[0]
assert ts6.count('class="g"') == 6 and "토스 딜 6개" in ts6 and ts6.index("토스93") < ts6.index("토스90") < ts6.index("토스83") < ts6.index("토스82")
assert "토스81" not in ts6 and "토스7" not in ts6 and "원글토스" not in ts6 and "상품주소토스" not in ts6  # 최신 6개만, 2일 지난 딜·쉐어링크 없는 토스 딜 제외
S.build([{"t": "2026-10-07 15:00", "text": "🔥 [토스] 그제토스 (1,000원)", "url": "https://toss.im/_m/z", "s": 7},
         {"t": "2026-10-08 15:00", "text": "🔥 [G마켓] 어제 (1,000원)", "url": "https://g", "s": 7},
         {"t": "2026-10-09 15:00", "text": "🔥 [쿠팡] 휴지 (1,000원)", "url": "https://buy", "s": 7}], "docs6")
ts0 = open("docs6/index.html").read().split('id="toss"')[1].split("</section>")[0]
assert 'class="grid"' not in ts0 and "💙 토스 딜</h2>" in ts0 and S.CHANNEL_WEB in ts0  # 최근 2일엔 토스 딜이 없음(그제 딜은 제외) -> 추천 버튼만

# 7) 일일 모아보기: 21시 이후 1회, 오늘 글만, 모아보기 자신은 제외
H.draft = lambda text, **k: sent.append(("draft", text)) or {"message_id": 9}
today = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600))
P = [{"t": f"{today} 10:00", "text": "🔥 A딜", "url": "https://a", "s": 7}, {"t": "2000-01-01 10:00", "text": "🔥 옛날딜", "url": "https://o", "s": 10},
     {"t": f"{today} 11:00", "text": "📋 오늘의 딜 모아보기", "url": None},
     {"t": f"{today} 12:00", "text": "🔥 [G마켓] B딜 (9,900원/무료)\n\n맛있어요\n\n출처: 뽐뿌", "url": "https://b", "s": 9,
      "e": "🥛", "hook": "B딜 개당 99원", "pts": ["개당 99원", "쿠폰 10%"]}]
H._tv_real, H.tg_video = H.tg_video, lambda path, cap: sent.append(("video", {"path": path, "caption": cap}))
fills = []  # 릴스 재료(e·hook·pts) 없는 TOP 글만 Claude에게 채워달라고 함
H.ai_pick = lambda prompt, lines: fills.append((prompt, lines)) or [{"i": 0, "score": 0, "comment": "", "e": "🍎", "hook": "A딜 훅", "pts": ["이유"]}]
seen, sent[:] = {}, []
H.digest(seen, P)
if time.gmtime(time.time() + 9 * 3600).tm_hour >= 21:
    t = [x for m, x in sent if m == "draft"][-1]
    assert "A딜" in t and "옛날딜" not in t and t.count("모아보기") == 1 and "hotdealpick.kr" in t and "blog.naver.com" in t and list(seen)[0].startswith("digest_")
    blog = [x for m, x in sent if m == "sendMessage"][-1]["text"]  # 블로그용은 버튼 없는 일반 메시지로 뒤따라옴
    assert "제목: " in blog and "A딜" in blog and "https://a" in blog and "옛날딜" not in blog and "쿠팡 파트너스" in blog
    v = [x for m, x in sent if m == "video"]  # 릴스: 점수 높은 순, 오늘 글만, 모아보기 제외, 캡션에 대가성 문구·해시태그
    assert len(v) == 1 and os.path.getsize(v[0]["path"]) > 10000 and v[0]["caption"].startswith("B딜 개당 99원 · ") and "가성비 TOP2" in v[0]["caption"]
    assert v[0]["caption"].index("1. [G마켓] B딜") < v[0]["caption"].index("2. A딜") and "옛날딜" not in v[0]["caption"]
    assert "제휴 링크" in v[0]["caption"] and "#핫딜" in v[0]["caption"] and len(v[0]["caption"]) <= 1024
    assert fills == [(H.REEL_PROMPT, ["A딜 | "])] and "B딜" not in str(fills)  # B딜은 이미 hook·pts 있음
    sent.clear(); H.digest(seen, P); assert not sent
    seen.pop("blog_" + list(seen)[0][7:]); sent.clear(); H.digest(seen, P)  # 블로그용 글만 실패했던 날: 초안·릴스 없이 블로그용 글만 다시
    assert [m for m, x in sent] == ["sendMessage"] and "제목: " in sent[0][1]["text"] and any(k.startswith("blog_") for k in seen)
assert "og:title" in idx and "naver-site-verification" in idx and "blog.naver.com/hotdeal_pick" in idx and "instagram.com/hotdealpick.kr" in idx and "threads.com/@hotdealpick.kr" in idx

# 8) 카드 이미지: 제목 파싱(중첩 괄호·뒤 꼬리말), 6개 넘어도 하단 박스 안 침범, PNG 생성
import cards
assert cards.parse("[네이버] 화장지 3겹(30m 30롤) 2팩 (18,900원/무료)") == ("네이버", "화장지 3겹(30m 30롤) 2팩", "18,900원/무료")
assert cards.parse("[G마켓] 버짠3 (189,000원/무료) 카드할인") == ("G마켓", "버짠3 카드할인", "189,000원/무료")
assert cards.parse("제목만") == ("", "제목만", "")
assert cards.parse("[쿠팡] 듀라셀 AA 건전지 20개입 1개/ 9,730원") == ("쿠팡", "듀라셀 AA 건전지 20개입 1개", "9,730원")  # 루리웹식 꼬리(10/8 카드 03번)
assert cards.parse("[지마켓] 1+1/무료 상품") == ("지마켓", "1+1/무료 상품", "")
assert cards.make([f"[쿠팡] 상품{i} 아주 긴 이름을 가진 상품입니다 정말로 길어요 {i} (1,000원/무료)" for i in range(9)], "10월 5일", "docs/cards/t.png") == "docs/cards/t.png"
assert os.path.getsize("docs/cards/t.png") > 10000
from PIL import Image as _I; _j = _I.open("docs/cards/t.jpg"); assert _j.format == "JPEG" and _j.size == (1080, 1350)  # 인스타용 JPEG도 같이(API는 JPEG만)
assert cards.make([{"title": "[G마켓] 우유 (23,740원/무료)", "unit": "팩당 495원"}, "[쿠팡] 휴지 (9,900원/무료)"], "10월 5일", "docs/cards/t2.png") == "docs/cards/t2.png"
from PIL import Image, ImageDraw
_d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
assert cards.wrap(_d, "건국 멸균우유 200ml 48팩", cards.font("bold", 84), 880, 3) == ["건국 멸균우유 200ml", "48팩"]  # 띄어쓰기 단위
assert len(cards.wrap(_d, "가" * 100, cards.font("bold", 84), 880, 2)) == 2  # 띄어쓰기 없어도 글자 단위로 2줄 + …
# 8-2) 릴스 영상: 1080x1920 · 30fps · H.264 · 딜 3개면 15초
import subprocess
rv = cards.reel([{"title": "[G마켓] 건국 멸균우유 200ml 48팩 (23,740원/무료)", "comment": "쿠폰가예요", "e": "🥛", "hook": "우유 팩당 495원",
                  "pts": ["팩당 약 495원", "무료배송", "상온 보관 가능"], "unit": "팩당 약 495원", "warn": "카드할인 적용가"},
                 {"title": "[카카오] 고구마 3kg (7,600원/무료)", "comment": "맛있어요. 무료배송입니다."},  # e·hook·pts 없으면 제목·코멘트로
                 {"title": "제목만 있는 딜", "comment": "", "e": "x"}], "10월 5일", "docs/reel_t.mp4")  # 못 그리는 이모지 -> 🛒
pr = subprocess.run([cards.ffmpeg().replace("ffmpeg", "ffprobe"), "-v", "error", "-show_entries", "stream=width,height,codec_name,r_frame_rate:format=duration",
                     "-of", "default=nw=1", rv], capture_output=True, text=True).stdout if os.path.exists(cards.ffmpeg().replace("ffmpeg", "ffprobe")) else ""
assert os.path.getsize(rv) > 10000 and (not pr or all(s in pr for s in ["codec_name=h264", "width=1080", "height=1920", "r_frame_rate=30/1", "duration=15.0"]))
assert cards.emoji("🥛", 200).size[1] == 200 and cards.emoji("x", 100).width > 50  # 정사각형 안에 맞춤, 실패하면 🛒
subprocess.run([cards.ffmpeg(), "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=3", "docs/bgm_t.m4a"], check=True)
rm = cards.reel([{"title": "[G마켓] 우유 (1,000원/무료)", "comment": "싸요"}], "10월 7일", "docs/reel_m.mp4", "docs/bgm_t.m4a")  # 3초 음악 -> 영상 길이만큼 반복
au = subprocess.run([cards.ffmpeg(), "-i", rm], capture_output=True, text=True).stderr
dur = lambda s: sum(float(x) * m for x, m in zip(re.search(r"Duration: (\d+):(\d+):([\d.]+)", s).groups(), (3600, 60, 1)))
assert "Audio: aac" in au and "Video: h264" in au and abs(dur(au) - dur(subprocess.run([cards.ffmpeg(), "-i", cards.reel([{"title": "[G마켓] 우유 (1,000원/무료)", "comment": "싸요"}], "10월 7일", "docs/reel_n.mp4")], capture_output=True, text=True).stderr)) < 0.3
# 8-3) 영상 업로드는 multipart (chat_id·caption·video 파일)
import urllib.request
class _R:
    def __init__(self, req): self.req = req
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def read(self): return b'{"result": {"message_id": 5}}'
_got = []
_uo, urllib.request.urlopen = urllib.request.urlopen, lambda req, timeout=None: _got.append(req) or _R(req)
_tv = H._tv_real
assert _tv(rv, "캡션") == {"message_id": 5}
_b = _got[0].data
assert _got[0].full_url.endswith("/sendVideo") and _got[0].headers["Content-type"].startswith("multipart/form-data; boundary=")
assert b'name="chat_id"\r\n\r\n42' in _b and "캡션".encode() in _b and b'filename="reel.mp4"' in _b and open(rv, "rb").read() in _b
urllib.request.urlopen = _uo

# 9) Threads: 카드 미배포(404)면 대기, 배포되면 me -> 컨테이너 -> 30초 -> 발행 -> 사진 전송, 하루 1회
H.E["THREADS_TOKEN"] = "tk"; H.time.sleep = lambda s: None
today = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600))
open(f"docs/cards/{today}.png", "wb").write(b"png")
json.dump([{"t": f"{today} 10:00", "text": "🔥 A딜 (15,480원/무료)", "url": "https://a"}], open("posts.json", "w"))
live, calls[:] = False, []
def th_http(url, body=None, headers=None, method=None):
    calls.append((method or "GET", url))
    if url.endswith(".png"):
        if not live: raise OSError("404")
        return ""
    if "/me?" in url: return json.dumps({"id": "777"})
    if "/threads?" in url or "/threads_publish?" in url: return json.dumps({"id": "c1"})
    raise AssertionError(url)
H.http = th_http
seen, sent[:] = {}, []
H.threads(seen); assert not seen and len(calls) == 1  # 404 -> 다음 실행에
live = True; calls.clear(); H.threads(seen)
assert [m for m, _ in calls] == ["HEAD", "GET", "POST", "POST"] and "/777/threads?" in calls[2][1] and "creation_id=c1" in calls[3][1]
assert "image_url=https%3A%2F%2Fhotdealpick.kr%2Fcards%2F" in calls[2][1] and "A%EB%94%9C" in calls[2][1] and "15%2C480" not in calls[2][1]  # 카드 주소 + 제목 포함, 가격 꼬리는 뺌(카드에 있음)
assert H.clip("코카콜라 190ml 30캔 + 스프라이트 제로 위드 티 350ml 24캔", 34) == "코카콜라 190ml 30캔 + 스프라이트 제로 위드 티…" and H.clip("짧은 제목", 34) == "짧은 제목"  # 단어 중간에서 안 끊김
assert sent[-1][0] == "sendPhoto" and list(seen)[0].startswith("threads_")
calls.clear(); H.threads(seen); assert not calls  # 같은 날 재실행 시 안 올림
del H.E["THREADS_TOKEN"]; seen, sent[:], calls[:] = {}, [], []
H.threads(seen)  # 토큰 없으면: 사진만 보내고 Threads 호출 없음
assert [m for m, _ in calls] == ["HEAD"] and sent[-1][0] == "sendPhoto" and "Threads" not in sent[-1][1]["caption"] and list(seen)[0].startswith("threads_")
# 9-1b) 인스타 카드 자동 게시(10/8 진우 '자동으로 올리게'): IG 토큰 있으면 같은 카드의 .jpg로 이미지 컨테이너(캡션 = 오늘 딜 목록·제휴 안내·해시태그, 가격 꼬리 뺌)
#        -> 발행은 ig_publish / 관리자 사진 캡션 '인스타·Threads 자동 게시 중' / 인스타가 실패해도 Threads는 올라가고 관리자에게 '직접 올려줘'
ig_calls, fail_ig = [], [False]
def igc_http(url, body=None, headers=None, method=None):
    if url.startswith(H.IG):
        ig_calls.append((url, body, headers, method))
        if fail_ig[0]: raise OSError("ig down")
        return json.dumps({"id": "IMG1"})
    return th_http(url, body, headers, method)
H.E.update(IG_TOKEN="pt", IG_USER_ID="178", THREADS_TOKEN="tk"); H.http, seen, sent[:], calls[:] = igc_http, {}, [], []
H.threads(seen)
u, b, h, m = ig_calls[0]
assert u == H.IG + "/178/media" and m == "POST" and h["Authorization"] == "Bearer pt" and b["image_url"] == f"https://hotdealpick.kr/cards/{today}.jpg"
assert "오늘의 핫딜 모음" in b["caption"] and "1. A딜" in b["caption"] and "제휴 링크" in b["caption"] and "#핫딜" in b["caption"] and "15,480" not in b["caption"]
assert "igc_IMG1" in seen and "인스타·Threads 자동 게시 중" in sent[0][1]["caption"] and "그대로 올리면" not in sent[0][1]["caption"]
assert any("/threads_publish?" in u for _, u in calls)  # Threads도 그대로
fail_ig[0], seen, sent[:], calls[:] = True, {}, [], []
H.threads(seen)
assert any("인스타 카드 게시 실패" in str(p.get("text")) for _, p in sent) and any("/threads_publish?" in u for _, u in calls) and not [k for k in seen if k.startswith("igc_")]
del H.E["IG_TOKEN"], H.E["IG_USER_ID"], H.E["THREADS_TOKEN"]; H.http = th_http
# 9-1c) 인스타 카드 다시 게시(10/8 진우 '다시 업로드'): ig_repost.txt 날짜 = 오늘일 때만 / 1번째 실행 = 새 카드(docs/cards/re/, 지금 코드)만 저장,
#        다음 실행 = 사이트에 뜨면 새 주소 .jpg + 새 캡션으로 컨테이너(발행은 ig_publish) / 하루 1번, 지난 날짜·토큰 없음이면 아무것도 안 함 / 실행 순서 ig_publish 앞
import shutil; shutil.rmtree("docs/cards/re", ignore_errors=True)
H.E.update(IG_TOKEN="pt", IG_USER_ID="178"); ig_calls[:], fail_ig[0], seen, dep = [], False, {}, [False]
def re_http(url, body=None, headers=None, method=None):
    if method == "HEAD":
        assert url == f"https://hotdealpick.kr/cards/re/{today}.jpg", url
        if not dep[0]: raise OSError("404")
        return ""
    return igc_http(url, body, headers, method)
H.http = re_http
open("ig_repost.txt", "w").write("2020-01-01\n"); H.ig_repost(seen); assert not ig_calls and not os.path.isdir("docs/cards/re")  # 지난 날짜면 새 카드도 안 만듦
open("ig_repost.txt", "w").write(today + "\n"); H.ig_repost(seen)
assert os.path.exists(f"docs/cards/re/{today}.png") and os.path.exists(f"docs/cards/re/{today}.jpg") and not ig_calls and not seen
H.ig_repost(seen); assert not ig_calls and not seen  # 사이트 배포 전
dep[0] = True; H.ig_repost(seen)
u, b, h, m = ig_calls[0]
assert u == H.IG + "/178/media" and m == "POST" and b["image_url"] == f"https://hotdealpick.kr/cards/re/{today}.jpg" and "카드 번호를 누르면 바로 구매" in b["caption"] and "1. A딜" in b["caption"]
assert "igc_IMG1" in seen and f"igre_{today}" in seen
H.ig_repost(seen); assert len(ig_calls) == 1  # 하루 1번
del H.E["IG_TOKEN"]; H.ig_repost({}); assert len(ig_calls) == 1  # 토큰 없으면 안 함
os.remove("ig_repost.txt"); del H.E["IG_USER_ID"]; H.http = th_http
assert "ig_repost, ig_publish" in inspect.getsource(H.main)
# 9-1d) 쿠팡 링크 다시 알림(10/8 진우 '쿠팡 링크 공유 쉽게'): 13·19시 1번씩, 오늘 쿠팡 딜 중 아직 파트너스 링크가 아닌 글만 사본을 다시(채널 글 링크·파트너스 검색 버튼),
#        새 사본 번호로 cp 갱신(링크만 보내도 그 사본에 '교체됨'), 제휴 링크로 바뀐 글·토스·다른 날 글은 제외, 없으면 아무것도 안 보냄
pj, tg0, tt5 = open("posts.json").read(), H.tg, time.time
cps = iter(range(500, 600))
H.tg = lambda method, **p: sent.append((method, p)) or ({"message_id": next(cps)} if method == "copyMessage" else {"message_id": 1})
day0 = time.strftime("%Y-%m-%d", time.gmtime(1791259200 + 9 * 3600))  # 10/6 13:00 KST
json.dump([{"t": f"{day0} 10:00", "text": "🔥 [쿠팡] 듀라셀 건전지 20개입 (9,730원)", "url": "https://www.coupang.com/vp/products/1", "mid": 5, "cp": 77},
           {"t": f"{day0} 11:00", "text": "🔥 [쿠팡] 이미 바꾼 딜 (1,000원)", "url": "https://link.coupang.com/a/x", "mid": 6, "cp": 78},
           {"t": f"{day0} 11:30", "text": "🔥 [토스] 토스 딜 (1,000원)", "url": "https://www.ppomppu.co.kr/x", "mid": 7, "cp": 79},
           {"t": "2026-10-05 10:00", "text": "🔥 [쿠팡] 어제 딜 (1,000원)", "url": "https://www.coupang.com/vp/products/2", "mid": 4, "cp": 70}], open("posts.json", "w"), ensure_ascii=False)
seen, sent[:] = {}, []
time.time = lambda: 1791259200 - 60; H.coupang_remind(seen); assert not sent and not seen  # 12:59
time.time = lambda: 1791259200 + 300; H.coupang_remind(seen)  # 13:05
cm = [p for m, p in sent if m == "copyMessage"]
assert len(cm) == 1 and cm[0]["message_id"] == 5 and cm[0]["chat_id"] == "42" and "쿠팡 링크 아직 안 만든 오늘 딜 1개" in sent[0][1]["text"]
kb = cm[0]["reply_markup"]["inline_keyboard"]
assert kb[0][0]["url"] == "https://t.me/ch/5" and kb[1][0]["url"] == H.CP_SEARCH + urllib.parse.quote("듀라셀 건전지 20개입")
assert json.load(open("posts.json"))[0]["cp"] == 500 and json.load(open("posts.json"))[1]["cp"] == 78 and "cprem_20261006_13" in seen
sent.clear(); H.coupang_remind(seen); assert not sent  # 같은 회차 1번
time.time = lambda: 1791259200 + 6 * 3600 + 300; H.coupang_remind(seen); assert len([1 for m, _ in sent if m == "copyMessage"]) == 1  # 19:05 다시
pp2 = json.load(open("posts.json")); pp2[0]["url"] = "https://link.coupang.com/a/y"; json.dump(pp2, open("posts.json", "w"))
sent.clear(); time.time = lambda: 1791259200 + 86400 + 300; H.coupang_remind({}); assert not sent  # 다음 날: 오늘 쿠팡 딜 없음
assert "coupang_remind, report" in inspect.getsource(H.main)
open("posts.json", "w").write(pj); H.tg, time.time = tg0, tt5
# 9-2) 딜마다 Threads: 사이트 페이지 링크, 제휴 링크면 대가성 문구 맨 앞, 3시간 지난 딜·모아보기 제외, 1회 3개, 미배포면 다음에, 두 번 안 올림
kt = lambda h: time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - h * 3600))
json.dump([{"t": kt(4), "text": "🔥 [옛날] 딜", "url": "https://a"},
           {"t": kt(0), "text": "📋 모아보기", "url": None},
           {"t": kt(1), "text": f"{H.DISCLOSURE}\n\n🔥 [쿠팡] 휴지 30롤\n\n싸요\n\n출처: 뽐뿌", "url": "https://link.coupang.com/a/x"},
           {"t": kt(0.5), "text": "🔥 [카카오] 고구마 3kg\n\n맛있음\n\n출처: 뽐뿌", "url": "https://www.ppomppu.co.kr/1"},
           {"t": kt(0.2), "text": "🔥 [G마켓] 우유\n\n좋음\n\n출처: 뽐뿌", "url": "https://x"},
           {"t": kt(0.1), "text": "🔥 [옥션] 라면\n\n좋음\n\n출처: 뽐뿌", "url": "https://y"}], open("posts.json", "w"))
live_pages = {2, 3}
def td_http(url, body=None, headers=None, method=None):
    calls.append((method or "GET", url))
    if "/p/" in url:
        if int(url.rsplit("/", 1)[1].split(".")[0]) not in live_pages: raise OSError("404")
        return ""
    if "/me?" in url: return json.dumps({"id": "777"})
    if "/threads?" in url or "/threads_publish?" in url: return json.dumps({"id": "c1"})
    raise AssertionError(url)
H.http, calls[:] = td_http, []
H.E["THREADS_TOKEN"] = "tk"; H.threads_deals({})
from urllib.parse import parse_qs, urlsplit
made = [parse_qs(urlsplit(u).query) for m, u in calls if "/777/threads?" in u]
assert [m for m, _ in calls] == ["GET", "HEAD", "POST", "POST", "HEAD", "POST", "POST", "HEAD"]  # 4번 페이지 404 -> 멈춤
assert [q["link_attachment"][0] for q in made] == ["https://hotdealpick.kr/p/2.html", "https://hotdealpick.kr/p/3.html"]
t2, t3 = made[0]["text"][0], made[1]["text"][0]
assert t2.startswith(H.DISCLOSURE + "\n\n🔥 [쿠팡] 휴지 30롤\n\n싸요\n\n👉 https://hotdealpick.kr/p/2.html") and "출처" not in t2
assert t3.startswith("🔥 [카카오] 고구마 3kg\n\n맛있음") and "이 포스팅은" not in t3 and t3.endswith("t.me/hotdeal_pick")
assert made[0]["media_type"] == ["TEXT"] and made[0]["topic_tag"] == ["핫딜"] and max(len(t2.encode()), len(t3.encode())) < 500
assert [bool(p.get("th")) for p in json.load(open("posts.json"))] == [False, False, True, True, False, False]
live_pages, calls[:] = {2, 3, 4, 5}, []; H.threads_deals({})  # 재실행: 올린 건 건너뛰고 남은 것만
assert [parse_qs(urlsplit(u).query)["link_attachment"][0][-8:] for m, u in calls if "/777/threads?" in u] == ["p/4.html", "p/5.html"]
calls[:] = []; H.threads_deals({}); assert not calls  # 더 올릴 게 없으면 API 호출 없음
# 9-2b) Threads가 링크 미리보기를 못 만들면(Invalid Link Attachment·4279047, 10/7 15:51 버거킹 딜): 링크 첨부 없이 1번 더(본문 주소 그대로), 다른 오류는 그대로 예외
import urllib.error
def pub_fail(body, only_first):
    def f(url, b=None, headers=None, method=None):
        if "/threads_publish?" in url and (not only_first or sum("/777/threads?" in u for m, u in calls) == 1):
            e = urllib.error.HTTPError(url, 400, "Bad Request", {}, None); e.body = body; raise e
        return td_http(url, b, headers, method)
    return f
sl2, H.time.sleep, live_pages = H.time.sleep, lambda s: None, {0}
json.dump([{"t": kt(0), "text": "🔥 [11번가] 버거킹\n\n싸요\n\n출처: 뽐뿌", "url": "https://w"}], open("posts.json", "w"))
H.http, calls[:] = pub_fail('{"error": {"message": "Fatal", "type": "OAuthException", "error_subcode": 4279047}}', True), []; H.threads_deals({})
made = [parse_qs(urlsplit(u).query) for m, u in calls if "/777/threads?" in u]
assert [q.get("link_attachment") for q in made] == [["https://hotdealpick.kr/p/0.html"], None] and "👉 https://hotdealpick.kr/p/0.html" in made[1]["text"][0]
assert sum("/threads_publish?" in u for m, u in calls) == 1  # 두 번째(첨부 없음)는 발행됨
json.dump([{"t": kt(0), "text": "🔥 [G마켓] 우유\n\n좋음", "url": "https://x"}], open("posts.json", "w")); H.http, calls[:] = pub_fail('{"error": {"message": "expired"}}', False), []
try:
    H.threads_deals({}); raise AssertionError("다른 오류는 예외로 올라가야 함(main이 알림)")
except urllib.error.HTTPError:
    pass
assert sum("/777/threads?" in u for m, u in calls) == 1  # 다른 오류면 다시 안 만듦
H.time.sleep, H.http, calls[:] = sl2, td_http, []
del H.E["THREADS_TOKEN"]; json.dump([{"t": kt(0), "text": "🔥 새 딜", "url": "https://z"}], open("posts.json", "w"))
H.threads_deals({}); assert not calls  # 토큰 없으면 아무것도 안 함
# 9-3) 인스타 릴스 자동 게시: 컨테이너(REELS·resumable·캡션) -> rupload에 영상 파일(OAuth 헤더·offset 0·file_size) -> 다음 실행에 처리 끝났으면 발행
#      처리 중이면 기다림, 실패(ERROR)면 예외(main이 하루 1번 알림), 업로드 실패해도 영상은 봇 채팅으로(직접 올리기), 토큰 없으면 아무것도 안 함
H.E.update(IG_TOKEN="pt", IG_USER_ID="178"); ic, st, ph2, ig0 = [], ["IN_PROGRESS"], H.http, H.IG
H.IG = "https://graph.facebook.com/v25.0"  # 릴스 파일 업로드는 페이스북 페이지 토큰일 때만
def ig_http(url, body=None, headers=None, method=None):
    ic.append((url, body, headers, method))
    if url.endswith("/178/media"):
        return '{"id": "C1", "uri": "https://rupload.facebook.com/ig-api-upload/v25.0/C1"}'
    if "rupload" in url:
        return '{"success": true}'
    if "status_code" in url:
        return json.dumps({"status_code": st[0]})
    if url.endswith("/178/media_publish"):
        return '{"id": "M1"}'
    raise AssertionError(url)
H.http = ig_http; open("r.mp4", "wb").write(b"0" * 1234); seen = {}
H.ig_upload("r.mp4", "캡션 #핫딜", seen)
assert ic[0][1] == {"media_type": "REELS", "upload_type": "resumable", "caption": "캡션 #핫딜", "share_to_feed": True} and ic[0][2]["Authorization"] == "Bearer pt"
assert ic[1][0] == "https://rupload.facebook.com/ig-api-upload/v25.0/C1" and ic[1][1] == b"0" * 1234 and ic[1][2] == {"Authorization": "OAuth pt", "offset": "0", "file_size": "1234"}
assert list(seen) == ["igc_C1"]
sent.clear(); H.ig_publish(seen); assert "igc_C1" in seen and not sent and not any("media_publish" in c[0] for c in ic)  # 처리 중 -> 다음 실행에
st[0] = "FINISHED"; H.ig_publish(seen)
assert ic[-1][0].endswith("/178/media_publish") and ic[-1][1] == {"creation_id": "C1"} and not seen and "자동 게시 완료" in sent[-1][1]["text"]
st[0], seen = "ERROR", {"igc_C2": 1}
try:
    H.ig_publish(seen); assert False
except RuntimeError as e:
    assert "ERROR" in str(e) and not seen  # 실패한 컨테이너는 다시 안 봄
def ig_down(url, *a, **k):
    raise RuntimeError("down")
H.http, vids, tt2 = ig_down, [], time.time
H.tg_video, H.draft, time.time = lambda path, cap: vids.append(cap), lambda text, **k: {"message_id": 9}, lambda: 1791291600  # 10/6 22:00 KST
json.dump([{"url": "https://cdn.pixabay.com/s.mp3", "name": "테스트곡 — 작가"}], open("music.json", "w")); bg = H.bgm; H.bgm = lambda kst: "docs/bgm_t.m4a"
sent.clear(); H.digest({}, [{"t": "2026-10-06 10:00", "text": "🔥 [G마켓] 우유 (1,000원/무료)\n\n싸요", "url": "https://a", "s": 7, "e": "🥛", "hook": "우유 개당 100원", "pts": ["싸요"]}])
assert any("업로드 실패" in p["text"] for m, p in sent if m == "sendMessage") and len(vids) == 1 and vids[0].startswith("우유 개당 100원")
assert "🎵 테스트곡 — 작가 (Pixabay)" in vids[0]  # 캡션에 오늘 곡명
H.IG, vids[:] = "https://graph.instagram.com/v25.0", []  # 인스타 토큰(Instagram 로그인)이면 릴스 업로드 시도 안 함(실패 알림 없음), 영상은 봇 채팅으로
sent.clear(); H.http = lambda *a, **k: (_ for _ in ()).throw(AssertionError("인스타 토큰이면 릴스 업로드 호출 없음"))
H.digest({}, [{"t": "2026-10-06 10:00", "text": "🔥 [G마켓] 우유 (1,000원/무료)\n\n싸요", "url": "https://a", "s": 7, "e": "🥛", "hook": "우유 개당 100원", "pts": ["싸요"]}])
assert len(vids) == 1 and not any("업로드 실패" in p.get("text", "") for m, p in sent if m == "sendMessage")
H.IG = ig0
H.bgm = bg; os.remove("music.json")
del H.E["IG_TOKEN"]; ic[:] = []; H.http = ig_http; H.ig_publish({"igc_C3": 1}); assert not ic  # 토큰 없으면 호출 없음
time.time, H.http = tt2, ph2
# 9-4) 성과 리포트(10/8 진우 '토스 정산금 들어오기 시작' → '1일 4회'): 10·14·18·22시 회차마다 1번 관리자에게(밀리면 최근 회차만) — 토스 오늘·이번 달 실적(이번 달 상품 TOP3, 간접 구매 표시)
#      + Threads 오늘 글 조회수 합·TOP3(대가성 문구 줄 빼고 제목)·링크 클릭·팔로워 / 인사이트 권한 없으면 '권한 필요' 한 줄 / 전송 실패면 다음 실행에 다시
from urllib.error import HTTPError
H.E.update(TOSS_ACCESS_KEY="ak", TOSS_SECRET_KEY="sk", TOSS_PUBLISHER_ID="pub-1", THREADS_TOKEN="tk"); H.HAS_TOSS, rc, perm = True, [], [True]
json.dump({"token": "TK", "exp": 1e10}, open("toss.json", "w"))
NOW = 1791292800  # 10/6 22:20 KST
def rep_http(url, body=None, headers=None, method=None):
    rc.append(url)
    q = parse_qs(urlsplit(url).query)
    if url.startswith(H.TOSS_API + "/performance?"):
        assert headers["Authorization"] == "Bearer TK" and q["toDate"] == ["2026-10-06"]
        month = q["fromDate"] == ["2026-10-01"]
        assert month or q["fromDate"] == ["2026-10-06"]
        return json.dumps({"resultType": "SUCCESS", "success": {"summary": {"clickCount": 340 if month else 12, "soldQuantity": 9 if month else 1,
                          "expectedCommissionAmount": 4150 if month else 350, "confirmedCommissionAmount": 1200 if month else 0, "lastUpdatedAt": "2026-10-06T21:30:00"},
                          "items": [{"productId": 7, "productName": "할리스 미니 130개", "attribution": "DIRECT", "soldQuantity": 3, "expectedCommissionAmount": 2100},
                                    {"productId": 8, "productName": "", "attribution": "INDIRECT", "soldQuantity": 1, "expectedCommissionAmount": 900},
                                    {"productId": 9, "productName": "생수", "attribution": "DIRECT", "soldQuantity": 4, "expectedCommissionAmount": 600},
                                    {"productId": 10, "productName": "넷째", "attribution": "DIRECT", "soldQuantity": 1, "expectedCommissionAmount": 100}] if month else []}})
    assert url.startswith(H.THREADS) and q["access_token"] == ["tk"]
    if "/me?" in url: return '{"id": "777"}'
    if "/777/threads?" in url:
        assert q["since"] == [str(NOW - 22 * 3600 - 20 * 60)] and q["fields"] == ["id,text"]  # 오늘 0시(KST)부터 올린 글
        return json.dumps({"data": [{"id": "a", "text": f"{H.DISCLOSURE}\n\n🔥 [쿠팡] 휴지 30롤\n\n싸요"}, {"id": "b", "text": "🔥 [G마켓] 우유\n\n좋음"},
                                    {"id": "c", "text": f"{H.TOSS_NOTE}\n\n⏰ 오늘의 토스 하루특가 TOP5\n\n1. 가"}, {"id": "d", "text": "남의 글 리포스트"}]})
    if "/insights?" in url:
        if not perm[0]:
            e = HTTPError(url, 400, "Bad Request", {}, None); e.body = '{"error": {"message": "Application does not have permission for this action", "code": 10}}'; raise e
        v = {"a": 120, "b": 45, "c": 300, "d": None}[url.rsplit("/", 2)[-2]]
        return json.dumps({"data": [] if v is None else [{"name": "views", "period": "lifetime", "values": [{"value": v}]}]})
    if "/777/threads_insights?" in url:
        if q["metric"] == ["clicks"]:
            assert q["since"] == [str(NOW - 22 * 3600 - 20 * 60)] and q["until"] == [str(int(time.time()))]
            return json.dumps({"data": [{"name": "clicks", "link_total_values": [{"value": 11, "link_url": "https://hotdealpick.kr/p/1.html"}, {"value": 4, "link_url": "https://t.me/hotdeal_pick"}]}]})
        assert q["metric"] == ["followers_count"] and "since" not in q  # 팔로워는 since 안 받음
        return json.dumps({"data": [{"name": "followers_count", "total_value": {"value": 87}}]})
    raise AssertionError(url)
H.http, seen = rep_http, {}
time.time = lambda: NOW - 12 * 3600 - 30 * 60; sent.clear(); H.report(seen); assert not sent and not rc  # 09:50: 첫 회차(10시) 전
time.time = lambda: NOW - 8 * 3600 - 15 * 60; H.report(seen)  # 14:05
assert sent[-1][1]["text"].startswith("📊 10/6 14:05 성과 리포트") and "report_20261006_14" in seen
sent.clear(); H.report(seen); assert not sent  # 같은 회차 1번
time.time = lambda: NOW; H.report(seen)  # 22:20 (18시 회차는 실행이 없어 건너뜀 -> 22시 회차 1번만)
m, p = sent[-1]; t = p["text"]
assert len(sent) == 1 and m == "sendMessage" and p["chat_id"] == "42" and t.startswith("📊 10/6 22:20 성과 리포트") and "report_20261006_22" in seen and "report_20261006_18" not in seen
assert "💰 토스 오늘: 클릭 12 · 판매 1개 · 예상 수익 350원 (구매확정 0원)" in t and "💰 토스 이번 달: 클릭 340 · 판매 9개 · 예상 수익 4,150원 (구매확정 1,200원)" in t
assert t.index("할리스 미니 130개 3개 2,100원") < t.index("· 8 1개 900원 (링크 타고 다른 상품)") < t.index("생수 4개 600원") and "넷째" not in t
assert "10-06 21:30 집계 · 잠정" in t
assert "🧵 Threads 오늘: 글 4개 · 조회 465 · 링크 클릭 15 · 팔로워 87" in t
assert t.index("300 — ⏰ 오늘의 토스 하루특가 TOP5") < t.index("120 — 🔥 [쿠팡] 휴지 30롤") < t.index("45 — 🔥 [G마켓] 우유") and "이 포스팅은" not in t and "이 콘텐츠는" not in t
rc.clear(); sent.clear(); H.report(seen); assert not sent and not rc  # 같은 회차 1번
perm[0], seen = False, {}; sent.clear(); H.report(seen)  # 인사이트 권한 없음(지금 토큰): 토스는 그대로, Threads는 안내 한 줄
t = sent[-1][1]["text"]
assert "threads_manage_insights 권한 필요" in t and "💰 토스 이번 달" in t and "조회 465" not in t and "report_20261006_22" in seen
H.tg, seen = lambda method, **p: None, {}; H.report(seen); assert not seen  # 텔레그램 실패 -> 다음 실행에 다시
H.tg = fake_tg; os.remove("toss.json"); del H.E["THREADS_TOKEN"]; time.time, H.http, H.HAS_TOSS = tt2, ph2, False
# 인스타 주소: Instagram 로그인 토큰(IGAA…) = graph.instagram.com, 페이스북 페이지 토큰(EAA…) = graph.facebook.com (10/8 앱이 Instagram 로그인 방식)
import subprocess, sys
for tok, host in (("IGAAx", "https://graph.instagram.com/v25.0"), ("EAAx", "https://graph.facebook.com/v25.0"), ("", "https://graph.instagram.com/v25.0")):
    r = subprocess.run([sys.executable, "-c", "import hotdeal; print(hotdeal.IG)"], env={**os.environ, "IG_TOKEN": tok}, cwd=os.path.dirname(os.path.abspath(H.__file__)), capture_output=True, text=True)
    assert r.stdout.strip() == host, (tok, r.stdout, r.stderr[-300:])
print("OK: 모든 셀프체크 통과")
