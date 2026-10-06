"""셀프체크: python test_hotdeal.py  (네트워크·키 불필요)"""
import base64, hashlib, hmac, io, json, os, re, tempfile, time
from urllib.parse import parse_qs, urlsplit
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
H.publish_approved()
assert [(x["id"], x["name"]) for x in json.load(open("music.json"))] == [("F1", "Happy"), ("F3", "b.wav")]
assert [p["reply_parameters"]["message_id"] for m, p in sent if m == "sendMessage" and "배경음악" in p["text"]] == [50, 51, 54] and sent[-1] == ("getUpdates", {"offset": 45})
got_url, uo = [], H.urllib.request.urlopen
H.urllib.request.urlopen = lambda url, timeout=None: got_url.append(url) or io.BytesIO(b"ID3-music")
bp = H.bgm(time.gmtime(86400 * 2))  # tm_yday 3 -> 3 % 2곡 = 두 번째 곡
assert open(bp, "rb").read() == b"ID3-music" and got_url == ["https://api.telegram.org/file/bott/music/f.mp3"] and ("getFile", {"file_id": "F3"}) in sent
os.remove("music.json"); assert H.bgm(time.gmtime(0)) is None  # 등록된 곡 없으면 무음
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
# 4-3) 한 번에 최대 2개만 게시, 넘친 좋은 딜은 다음 실행(15분 뒤)에 다시 / 루리웹은 15분 지나면 판단(반응 수치가 없어서)
RU3 = '<rss><channel>' + "".join(it(f"[G마켓] 상품{n}번 특가 묶음 / {n},000원", f"https://bbs.ruliweb.com/market/board/1020/read/9{n}", 20) for n in range(3)) + '</channel></rss>'
H.http = lambda url, *a, **k: RU3 if url == H.RULIWEB_RSS else ""
posted, pod = [], H.post_or_draft
H.post_or_draft = lambda d, *a, **k: posted.append(d["id"])
H.ai_pick = lambda prompt, lines: [{"i": i, "score": 8, "comment": "c"} for i in range(len(lines))]
json.dump({}, open("seen.json", "w")); H.main()
sj = json.load(open("seen.json"))
assert posted == ["ruliweb_90", "ruliweb_91"] and "ruliweb_92" not in sj and H.dkey("[G마켓] 상품2번 특가 묶음") not in sj  # 20분 된 루리웹 글도 판단
posted.clear(); H.main(); assert posted == ["ruliweb_92"]  # 다음 실행에 나머지
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
assert n == 1 and idx.count("[쿠팡] 휴지") == 1 and 'href="https://buy"' in idx and os.path.exists("docs/p/0.html") and os.path.exists("docs/.nojekyll") and open("docs/CNAME").read() == "hotdealpick.kr"
assert '<a href="https://src" rel="nofollow noopener" target="_blank">뽐뿌</a>' in idx  # 제목 줄 잘라낸 뒤에도 링크 위치 정확
assert "p/0.html" in open("docs/sitemap.xml").read() and "쿠팡 파트너스" in open("docs/p/0.html").read()
assert S.build([], "docs2") == 0 and "준비 중" in open("docs2/index.html").read()

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
assert cards.make([f"[쿠팡] 상품{i} 아주 긴 이름을 가진 상품입니다 정말로 길어요 {i} (1,000원/무료)" for i in range(9)], "10월 5일", "docs/cards/t.png") == "docs/cards/t.png"
assert os.path.getsize("docs/cards/t.png") > 10000
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
del H.E["THREADS_TOKEN"]; json.dump([{"t": kt(0), "text": "🔥 새 딜", "url": "https://z"}], open("posts.json", "w"))
H.threads_deals({}); assert not calls  # 토큰 없으면 아무것도 안 함
# 9-3) 인스타 릴스 자동 게시: 컨테이너(REELS·resumable·캡션) -> rupload에 영상 파일(OAuth 헤더·offset 0·file_size) -> 다음 실행에 처리 끝났으면 발행
#      처리 중이면 기다림, 실패(ERROR)면 예외(main이 하루 1번 알림), 업로드 실패해도 영상은 봇 채팅으로(직접 올리기), 토큰 없으면 아무것도 안 함
H.E.update(IG_TOKEN="pt", IG_USER_ID="178"); ic, st, ph2 = [], ["IN_PROGRESS"], H.http
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
sent.clear(); H.digest({}, [{"t": "2026-10-06 10:00", "text": "🔥 [G마켓] 우유 (1,000원/무료)\n\n싸요", "url": "https://a", "s": 7, "e": "🥛", "hook": "우유 개당 100원", "pts": ["싸요"]}])
assert any("업로드 실패" in p["text"] for m, p in sent if m == "sendMessage") and len(vids) == 1 and vids[0].startswith("우유 개당 100원")
del H.E["IG_TOKEN"]; ic[:] = []; H.http = ig_http; H.ig_publish({"igc_C3": 1}); assert not ic  # 토큰 없으면 호출 없음
time.time, H.http = tt2, ph2
print("OK: 모든 셀프체크 통과")
