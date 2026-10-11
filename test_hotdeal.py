"""셀프체크: python test_hotdeal.py  (네트워크·키 불필요)"""
import base64, hashlib, hmac, io, json, os, re, tempfile, time
from urllib.parse import parse_qs, quote, urlsplit
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
# 1-1a) 상품 주소를 못 꺼낸 딜(뽐뿌 차단) -> 원글 대신 그 몰 검색 결과(10/10 진우 '쇼핑몰로 바로'), 원글은 본문 '출처' 링크로. 토스·모르는 몰은 원글 그대로
sl0, pp = H.store_link, "https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&no=9"
H.store_link = lambda u: None
ms = {tt: H.deal_post({"board": "뽐뿌", "url": pp, "title": tt}, "싸다", q)[1:] for tt, q in
      [("[11번가] 호텔컬렉션 수건 10장 (26,520원/무료)", "호텔컬렉션 40수 수건"), ("[톡딜] 한돈 뒷고기 (9,900원)", None), ("[카카오톡] 사과 5kg (1원)", None),
       ("[네이버] 대한떡볶이 1팩 (1,990원/무료)", None), ("[토스] 김 (1원)", None), ("[스팀] 게임 (1원)", None)]}
assert ms["[11번가] 호텔컬렉션 수건 10장 (26,520원/무료)"] == ("https://search.11st.co.kr/Search.tmall?kwd=" + quote("호텔컬렉션 40수 수건"), "🔎 11번가에서 찾기")  # Claude 검색어
assert ms["[톡딜] 한돈 뒷고기 (9,900원)"] == ("https://store.kakao.com/search/result/product?q=" + quote("한돈 뒷고기"), "🔎 카카오에서 찾기")  # 검색어 없으면 제목에서 몰·가격 뗀 이름
assert ms["[카카오톡] 사과 5kg (1원)"][1] == "🔎 카카오에서 찾기" and ms["[네이버] 대한떡볶이 1팩 (1,990원/무료)"] == ("https://search.shopping.naver.com/search/all?query=" + quote("대한떡볶이 1팩"), "🔎 네이버쇼핑에서 찾기")
assert ms["[토스] 김 (1원)"] == ms["[스팀] 게임 (1원)"] == (pp, "🛒 1원 구매하기")  # 토스(쉐어링크 자동 교체가 원글 기준)·모르는 몰은 원글
assert f'출처: <a href="{H.esc(pp)}">뽐뿌</a>' in H.deal_post({"board": "뽐뿌", "url": pp, "title": "[11번가] 수건 (1원)"}, "싸다")[0]  # 원글은 출처 링크로 남음
H.store_link = lambda u: "https://www.11st.co.kr/products/1"
assert H.deal_post({"board": "뽐뿌", "url": pp, "title": "[11번가] 수건 (1원)"}, "싸다")[1:] == ("https://www.11st.co.kr/products/1", "🛒 1원 구매하기")  # 상품 주소가 있으면 검색보다 상품 페이지
assert H.buy_label("[쿠팡] 휴지 (9,900원/무료)") == "🛒 9,900원 구매하기" and H.buy_label("[쿠팡] 휴지") == "🛒 구매하러 가기" and H.buy_label("[G마켓] 초코 (16830원 무배 개당 약 140원)") == "🛒 16830원 구매하기"  # 10/10 버튼에 가격
H.store_link = sl0
# 1-1b) 커뮤니티 반응 좋은 딜 강조(10/9 진우): 게시판별 분당 조회수 3위 안(20회 이상) 또는 추천 3개 이상 -> 제목 바로 아래 '🏆 인기', 사이트 칸에도
hd = [{"board": "뽐뿌", "hits": f"댓글0·조회{v}·추천{r}·비추0", "age": a, "title": n} for n, v, r, a in
      [("a", 3000, 0, 60), ("b", 2400, 0, 40), ("c", 900, 0, 30), ("d", 1000, 0, 60), ("e", 500, 4, 50), ("f", 4000, 0, 3), ("g", 1500, 0, 60)]]
hd += [{"board": "루리웹", "hits": "", "age": 30, "title": "r"}, {"board": "클리앙", "hits": "댓글3·조회900·추천1", "age": 30, "title": "k"}]
H.mark_hot(hd); hot = {d["title"]: d.get("hot") for d in hd}
assert hot == {"a": "뽐뿌에서 지금 많이 보는 글 2위", "b": "뽐뿌에서 지금 많이 보는 글 1위", "c": "뽐뿌에서 지금 많이 보는 글 3위", "d": None, "e": "뽐뿌 추천 4",
               "f": None, "g": None, "r": None, "k": "클리앙에서 지금 많이 보는 글 1위"}, hot  # 분당 50·60·30 = 3위 안, 16.7·25(4위)·5분 미만·25(4위 밖)·루리웹 = 없음
th = H.deal_post({**d, "hot": "뽐뿌에서 지금 많이 보는 글 1위"}, "싸다")[0]
assert "</b>\n🏆 <b>인기</b> · 뽐뿌에서 지금 많이 보는 글 1위\n\n싸다" in th and "🏆" not in H.deal_post(d, "싸다")[0]
assert H.title_of(re.sub("<[^>]+>", "", th)) == d["title"]  # 배지가 있어도 사이트 제목은 그대로
assert H.comment_of(re.sub("<[^>]+>", "", th)) == "싸다" == H.comment_of(re.sub("<[^>]+>", "", H.deal_post(d, "싸다")[0]))  # 배지 줄은 코멘트 아님(릴스·Threads·블로그·TOP5)
assert {d["title"]: d.get("pop") for d in hd} == {"a": 50.0, "b": 60.0, "c": 30.0, "d": 16.7, "e": 30.0, "f": None, "g": 25.0, "r": None, "k": 35.0}  # 반응 = 분당 조회 + 추천×5(5분 미만·수치 없음 X)
assert [(d.get("vpm"), d.get("rec")) for d in hd if d["title"] in "ekf"] == [(10.0, 4), (None, None), (30.0, 1)]  # 보여 줄 땐 분당 조회·추천 따로(10/9 '분당 조회 18.5회'가 추천×5까지 합친 값이던 것 고침)
assert H.react({"vpm": 10.0, "rec": 4, "pop": 30}) == "분당 조회 10회 · 추천 4" and H.react({"vpm": 13.5, "pop": 13.5}) == "분당 조회 13.5회" and H.react({"pop": 18.5}) == "반응 18.5" and H.react({}) == ""
import inspect; assert "mark_hot(deals)" in inspect.getsource(H.main)

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
hops["https://oy.run/other"] = "https://m.oliveyoung.co.kr/m/goods/getGoodsDetail.do?goodsNo=A000000223414&dispCatNo=9&trackingCd=Best_Sellingbest&t_page=x"
assert H.plain("https://oy.run/other") == H.plain("https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000223414&trackingCd=Today_Special") == "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000223414"  # 남의 큐레이터 링크·추적값 -> 상품 번호만
assert H.plain("https://토스") is None and H.plain("https://toss") is None and H.plain("https://www.11st.co.kr:443/p/1") == "https://www.11st.co.kr:443/p/1"  # 글자만 적힌 출처 = 주소 아님(10/9 22:40 버튼 400)
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
hl = "\n\n".join(f'<a href="https://example.com/{"y" * 300}">딜 {i}</a>' for i in range(20))  # HTML: 주소 때문에 4096자 넘어도 보이는 글자는 짧음 -> 한 번에(자르면 태그가 깨져 400)
H.tg("sendMessage", chat_id="42", text=long); H.tg("sendMessage", chat_id="42", text=long, reply_markup={"inline_keyboard": []}); H.tg("sendMessage", chat_id="42", text=hl, parse_mode="HTML")
assert len(bodies) == 6 and all(len(b["text"]) <= 4096 for b in bodies[:4]) and "\n\n".join(b["text"] for b in bodies[:4]) == long and bodies[4]["text"] == long and bodies[5]["text"] == hl and len(hl) > 4096
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
pa33, H.ai_pick = H.ai_pick, lambda prompt, lines: []  # Claude 응답 없음 -> 지금처럼 초안(3-3b가 자동 게시)
H.publish_approved()
ms = [p for m, p in sent if m == "sendMessage"]
assert len(ms) == 3, ms
assert ms[0]["reply_markup"]["inline_keyboard"][-1][0]["text"].startswith("🤖 자동 게시 실패") and len(ms[2]["reply_markup"]["inline_keyboard"]) == 2  # 제휴 링크 아니면 안내 버튼 없음
assert ms[0]["chat_id"] == "42" and ms[0]["text"] == f"<i>{H.AFF_NOTE}</i>\n\n🔥 <b>[G마켓] 러닝화 (39,910원/무료)</b>\n\n쿠폰 &lt;필수&gt;"
assert ms[0]["reply_markup"]["inline_keyboard"][0][0] == {"text": "🛒 39,910원 구매하기", "url": LP} and ms[0]["text"].count("이 포스팅은") == 1  # 초안도 채널 글과 같은 가격 버튼(10/11)
assert ms[1]["reply_parameters"] == {"message_id": 31} and "제목" in ms[1]["text"]  # 링크만 -> 안내
assert ms[2]["text"] == "🔥 <b>[G마켓] 일반</b>"  # 일반 쇼핑몰 주소: 문구 없음
assert sent[-1] == ("getUpdates", {"offset": 24})
# 3-3b) 제휴 링크 + '상품명 가격' -> Claude 코멘트·단위가격·확인할 점 달아 채널에 바로 + posts.json(10/10 진우 '봇에 링크+가격 보내면 자동'),
#       몰 태그 없으면 링크로 [쿠팡], 점수 컷 미만이면 🛒 + '특가로는 약한 제품'(진우 '특가로는 약한 제품이라고 써 보자'), 같은 링크 다시 보내면 안 올림, iframe 코드는 안내, Claude 오류면 초안
CPL, asked3 = "https://link.coupang.com/a/new1", []
H.ai_pick = lambda prompt, lines: asked3.append((prompt, lines)) or (1 / 0 if "에러" in lines[0] else
    [{"i": 0, "score": 4, "comment": "평소 가격"}] if "약한" in lines[0] else [{"i": 0, "score": 5, "comment": "괜찮음"}] if "오점" in lines[0] else [{"i": 0, "score": 7, "comment": "27인치 100Hz가 10만 원대", "unit": "1인치당 3,843원", "warn": "휴일특가 끝나면 오름", "e": "🖥️"}])
UP = [{"update_id": 50, "message": {"message_id": 70, "from": {"id": 42}, "text": f"이트로이 27인치 모니터 103,770원\n휴일특가\n{CPL}"}},
      {"update_id": 51, "message": {"message_id": 71, "from": {"id": 42}, "text": f"이트로이 27인치 모니터 103,770원\n{CPL}"}},
      {"update_id": 52, "message": {"message_id": 72, "from": {"id": 42}, "text": '<iframe src="https://coupa.ng/cp3ajH" width="120"></iframe>'}},
      {"update_id": 53, "message": {"message_id": 73, "from": {"id": 42}, "text": "[쿠팡] 에러 상품 1,000원\nhttps://link.coupang.com/a/new2"}},
      {"update_id": 54, "message": {"message_id": 74, "from": {"id": 42}, "text": "[G마켓] 일반2\nhttps://item.gmarket.co.kr/Item?goodscode=2"}},
      {"update_id": 55, "message": {"message_id": 75, "from": {"id": 42}, "text": "채널실패 상품 2,000원\nhttps://link.coupang.com/a/new3"}},
      {"update_id": 56, "message": {"message_id": 76, "from": {"id": 42}, "text": "약한 키보드 77,900원\nhttps://link.coupang.com/a/new4"}},
      {"update_id": 57, "message": {"message_id": 77, "from": {"id": 42}, "text": "오점 계란 7,990원\nhttps://link.coupang.com/a/new5"}}]
sent.clear(); H.tg = lambda method, **p: sent.append((method, p)) or (UP if method == "getUpdates" and "offset" not in p else
    None if p.get("chat_id") == "@ch" and "채널실패" in p.get("text", "") else {"message_id": 300, "text": "글", "entities": []})
n3 = len(json.load(open("posts.json")))
H.publish_approved()
ch = [p for m, p in sent if m == "sendMessage" and p["chat_id"] == "@ch"]
ad = [p for m, p in sent if m == "sendMessage" and p["chat_id"] == "42"]
assert len(ch) == 4 and ch[3]["text"].endswith("🔥 <b>[쿠팡] 오점 계란 (7,990원)</b>\n\n괜찮음") and "채널실패" in ch[1]["text"] and ch[2]["text"] == f"<i>{H.DISCLOSURE}</i>\n\n🛒 <b>[쿠팡] 약한 키보드 (77,900원)</b>\n\n🤔 솔직히 특가로는 약한 제품\n평소 가격" and ch[0]["text"] == f"<i>{H.DISCLOSURE}</i>\n\n🔥 <b>[쿠팡] 이트로이 27인치 모니터 (103,770원)</b>\n\n27인치 100Hz가 10만 원대\n💡 단위가격 1인치당 3,843원\n⚠️ 확인할 점 휴일특가 끝나면 오름", ch
assert ch[0]["reply_markup"]["inline_keyboard"] == [[{"text": "🛒 103,770원 구매하기", "url": CPL}]]  # 끝 가격을 (가격)으로 묶어 버튼·사이트가 가격을 읽음(10/11)
assert asked3[0] == (H.ADMIN_PROMPT, ["[운영자] [쿠팡] 이트로이 27인치 모니터 (103,770원) |  | 0분 전 | 휴일특가"]) and len(asked3) == 5 and "지어내지 마" in H.ADMIN_PROMPT and "반드시 반환" in H.ADMIN_PROMPT and "5점 미만은 반환하지 마" not in H.ADMIN_PROMPT
pj3 = json.load(open("posts.json"))
assert len(pj3) == n3 + 3 and pj3[-2]["s"] == 4 and pj3[-2]["url"].endswith("new4") and pj3[-3]["url"] == CPL and pj3[-3]["mid"] == 300 and pj3[-3]["s"] == 7 and pj3[-3]["e"] == "🖥️" and pj3[-3]["unit"] == "1인치당 3,843원"
assert [x.get("reply_parameters", {}).get("message_id") for x in ad] == [70, 71, 72, None, None, None, 76, 77] and ad[6]["text"] == "✅ 채널에 올림 (Claude 4점 · 특가로는 약함 표시)"  # 올림 안내·이미 올림·iframe 안내·오류/일반 주소/채널 실패 -> 초안
assert ad[0]["text"] == "✅ 채널에 올림 (Claude 7점)" and ad[0]["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://t.me/ch/300" and "이미" in ad[1]["text"] and ad[2]["text"].startswith("iframe 말고")
assert ad[4]["text"] == "🔥 <b>[G마켓] 일반2</b>" and "채널실패" in ad[5]["text"]   # 제휴 링크 아니면 Claude 안 부름
assert ad[3]["text"] == f"<i>{H.DISCLOSURE}</i>\n\n🔥 <b>[쿠팡] 에러 상품 (1,000원)</b>" and ad[3]["reply_markup"]["inline_keyboard"][1][0]["callback_data"] == "ok"
H.tg, H.ai_pick = fake_tg, pa33

# 3-3c) 네이버 쇼핑커넥트(naver.me) 진우 딜 끝까지(10/11 점검): 봇에 '상품명 가격 + naver.me 링크' -> [네이버]·(가격/배송)·네이버 문구 맨 앞·1점 완화(5점도 🔥)
#       -> ① 채널 글 ② posts.json(own) ③ Threads(문구 맨 앞, 사이트 딜 페이지) ④ 21시 블로그용 글(문구 맨 위·코멘트) + 사이트 딜 페이지(문구 그대로 맨 앞)
#       링크는 서버에서 안 엶(자동 발급·열기 X), 같은 링크 다시 = 안 올림, (링크)·사진 캡션·[단독기획] 올영 제목도
import shutil, html
NV, OYL, asked4, opened4 = "https://naver.me/AbCd1234", "https://oy.run/Tor1", [], []
def no_open(url, *a, **k):
    opened4.append(url); raise AssertionError(url)
H.http, H.ai_pick = no_open, (lambda prompt, lines: asked4.append(lines) or [{"i": 0, "score": 5, "comment": "2L 24병 무료배송" if "삼다수" in lines[0] else "1+1 구성", "unit": "1L당 269원" if "삼다수" in lines[0] else ""}])
UP = [{"update_id": 60, "message": {"message_id": 80, "from": {"id": 42}, "text": f"삼다수 2L 24병 12,900원/무료\n({NV})"}},
      {"update_id": 61, "message": {"message_id": 81, "from": {"id": 42}, "text": f"삼다수 2L 24병 12,900원/무료\n{NV}/"}},
      {"update_id": 62, "message": {"message_id": 82, "from": {"id": 42}, "photo": [{"file_id": "P"}], "caption": f"[단독기획] 토리든 세럼 50ml 1+1 (19,900원/무료)\n{OYL}"}}]
pj4 = open("posts.json").read(); json.dump([], open("posts.json", "w"))
sent.clear(); H.tg = lambda method, **p: sent.append((method, p)) or (UP if method == "getUpdates" and "offset" not in p else {"message_id": 500 + len(sent), "text": re.sub(r"<[^>]+>", "", p.get("text", "")), "entities": []})
H.publish_approved()
ch = [p for m, p in sent if m == "sendMessage" and p["chat_id"] == "@ch"]
ad = [p for m, p in sent if m == "sendMessage" and p["chat_id"] == "42"]
assert not opened4 and len(ch) == 2  # ① 채널: 네이버 문구 그대로 맨 앞, [네이버] + 가격 괄호, 5점이어도 수수료 링크라 🔥(약한 제품 X), 버튼 = 진우 링크 그대로·가격
assert ch[0]["text"] == f"<i>{H.NAVER_NOTE}</i>\n\n🔥 <b>[네이버] 삼다수 2L 24병 (12,900원/무료)</b>\n\n2L 24병 무료배송\n💡 단위가격 1L당 269원"
assert ch[0]["reply_markup"]["inline_keyboard"] == [[{"text": "🛒 12,900원 구매하기", "url": NV}]] and asked4[0] == ["[운영자] [네이버] 삼다수 2L 24병 (12,900원/무료) |  | 0분 전 | "]
assert ad[1]["reply_parameters"] == {"message_id": 81} and ad[1]["text"] == "이미 채널에 올린 링크야"  # 같은 링크(끝 / 달라도) 다시 -> 안 올림
assert ch[1]["text"].startswith(f"<i>{H.OY_NOTE}</i>\n\n🔥 <b>[올리브영] [단독기획] 토리든 세럼 50ml 1+1 (19,900원/무료)</b>") and ch[1]["reply_markup"]["inline_keyboard"][0][0]["url"] == OYL  # 사진 캡션·몰 아닌 대괄호 제목도 [올리브영](올영 문구 규칙)
assert H.admin_title("⚡[네이버] 다시다 6,900원", NV) == "[네이버] 다시다 (6,900원)" and H.admin_title("[G마켓] x (1원)", NV) == "[G마켓] x (1원)" and H.admin_title("삼다수 12,900원 무료배송", "https://x.com") == "삼다수 (12,900원 무료배송)"
pjn = json.load(open("posts.json"))  # ② posts.json: 진우 딜(own) = 사이트·모아보기·Threads 엄선에서 안 빠짐
assert [(p["url"], p["own"], p["s"]) for p in pjn] == [(NV, 1, 5), (OYL, 1, 5)] and pjn[0]["text"].startswith(H.NAVER_NOTE + "\n\n🔥 [네이버] 삼다수") and H.store_info(H.title_of(pjn[0]["text"]), NV).startswith("💰 네이버")
th4 = []
def th4_http(url, body=None, headers=None, method=None):
    if method == "HEAD": return ""
    if "/me?" in url: return '{"id": "me"}'
    if "/threads?" in url: th4.append(parse_qs(urlsplit(url).query)["text"][0]); return '{"id": "c"}'
    if "threads_publish" in url: return '{"id": "p"}'
    raise AssertionError(url)
H.http, H.E["THREADS_TOKEN"], sl4, H.time.sleep = th4_http, "tk", H.time.sleep, lambda s: None
H.threads_deals({})  # ③ Threads: 진우 딜은 점수와 상관없이, 문구 맨 앞, 링크 = 사이트 딜 페이지(구매 버튼·문구 있음)
assert len(th4) == 2 and th4[0].startswith(H.NAVER_NOTE + "\n\n") and "🔥 [네이버] 삼다수 2L 24병 (12,900원/무료)" in th4[0] and f"{H.SITE}p/0.html" in th4[0] and th4[1].startswith(H.OY_NOTE + "\n\n")
del H.E["THREADS_TOKEN"]; H.time.sleep = sl4
pjn = json.load(open("posts.json")) + [{"t": pjn[0]["t"], "text": f"{H.NAVER_NOTE}\n\n🛒 [네이버] 약한 생수 (9,900원)\n\n🤔 솔직히 특가로는 약한 제품\n평소 가격", "url": "https://naver.me/Weak", "own": 1, "s": 3}]
bt = H.blog_text(pjn, time.gmtime(time.time() + 9 * 3600))  # ④ 블로그용 글: 네이버·올영 문구 본문 맨 위, 진우 링크 그대로, 약한 딜도 코멘트(🤔 줄 말고)
assert bt.split("\n\n")[2] == H.NAVER_NOTE + "\n" + H.OY_NOTE and f"1. [네이버] 삼다수 2L 24병 (12,900원/무료)\n2L 24병 무료배송\n👉 {NV}" in bt and "3. [네이버] 약한 생수 (9,900원)\n평소 가격\n👉 https://naver.me/Weak" in bt
site4 = tempfile.mkdtemp(); day4 = pjn[0]["t"][:10]; os.makedirs(f"{site4}/cards"); open(f"{site4}/cards/{day4}.png", "w").close(); json.dump([1, 0], open(f"{site4}/cards/{day4}.json", "w"))
S4 = __import__("build_site"); S4.build(pjn, site4)  # 사이트: 네이버·올영 딜 페이지에 그 문구 그대로 맨 앞(일반 안내보다 먼저), 몰 이름, 올영은 홈 카드 딜에서도 사이트 딜 페이지로(링크만 나열 금지)
p0, p1, home = (open(f"{site4}/{f}").read() for f in ("p/0.html", "p/1.html", "index.html"))
assert p0.index(html.escape(H.NAVER_NOTE)) < p0.index(S4.DISCLOSURE) < p0.index(f'href="{NV}"') and ">네이버 · " in p0 and html.escape(H.OY_NOTE) in p1 and html.escape(H.NAVER_NOTE) not in p1
assert "네이버 쇼핑 커넥트·올리브영 쇼핑 큐레이터" in S4.DISCLOSURE and f'class="pick" href="{S4.BASE}p/1.html"' in home and f'class="pick" href="{NV}"' in home and "식품" not in S4.keys(pjn[1]) and "식품" in S4.keys({"text": "🔥 [G마켓] 올리브유 1L (1원)", "url": "https://g"})
shutil.rmtree(site4)
# 답장 흐름: '✅ 채널에 올림' 안내에 새 링크로 답장 -> 채널 글은 posts.json 본문 그대로(안내 문구로 안 바뀜) / 쿠팡 문구 초안에 네이버 링크로 답장 -> 쿠팡 문구 떼고 네이버 문구로
CF = {"message_id": 600, "chat": {"id": 42}, "text": "✅ 채널에 올림 (Claude 5점)", "reply_markup": {"inline_keyboard": [[{"text": "📢 채널 글", "url": f"https://t.me/ch/{pjn[0]['mid']}"}]]}}
UP = [{"update_id": 70, "message": {"message_id": 90, "from": {"id": 42}, "text": "https://naver.me/NEW2", "reply_to_message": CF}}]
sent.clear(); H.publish_approved(); ed = [p for m, p in sent if m == "editMessageText" and p["chat_id"] == "@ch"]
assert len(ed) == 1 and ed[0]["text"].startswith(H.NAVER_NOTE + "\n\n🔥 [네이버] 삼다수") and "채널에 올림" not in ed[0]["text"] and ed[0]["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://naver.me/NEW2"
n4, nn = len(H.DISCLOSURE.encode("utf-16-le")) // 2, len(H.NAVER_NOTE.encode("utf-16-le")) // 2
t4, e4 = H.with_note(f"{H.DISCLOSURE}\n\n🔥 상품", [{"type": "italic", "offset": 0, "length": n4}, {"type": "bold", "offset": n4 + 4, "length": 2}], NV)
assert t4 == f"{H.NAVER_NOTE}\n\n🔥 상품" and e4 == [{"type": "italic", "offset": 0, "length": nn}, {"type": "bold", "offset": nn + 4, "length": 2}]
UP = [{"update_id": 71, "message": {"message_id": 91, "from": {"id": 42}, "text": "CJ 비비고 왕교자 1.05kg 2개 (15,900원/무료)\nhttps://smartstore.naver.com/cj/products/1\nhttps://naver.me/Two"}}]
sent.clear(); H.publish_approved(); ch = [p for m, p in sent if m == "sendMessage" and p["chat_id"] == "@ch"]  # 상품 주소 + naver.me 같이 보냄 -> 제휴 링크로, 본문에 다른 링크 안 남김
assert len(ch) == 1 and ch[0]["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://naver.me/Two" and ch[0]["text"].startswith(f"<i>{H.NAVER_NOTE}</i>") and "smartstore" not in ch[0]["text"] + str(asked4[-1])
open("posts.json", "w").write(pj4); H.tg, H.ai_pick, H.http = fake_tg, pa33, fake_http

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
assert sent[0][1]["reply_markup"]["inline_keyboard"] == [[{"text": "🛒 18,700원 구매하기", "url": D("")["url"]}]]
lp = json.load(open("posts.json"))[-1]
assert lp["mid"] == 100 and lp["s"] == 8 and lp["e"] == "🫐" and lp["hook"] == "1kg 6,233원" and lp["pts"] == ["kg당 6,233원"] and "x" not in lp  # 릴스 재료 저장
assert lp["unit"] == "kg당 6,233원" and "warn" not in lp and "💡 단위가격 kg당 6,233원" in sent[0][1]["text"]  # 빈 값은 저장 안 함
assert "hot" not in lp
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
sm = [p for m, p in sent if m == "sendMessage"]  # 바꾼 글마다 어느 글인지 답장(10/11: 새 딜인데 제목을 빠뜨리면 다른 글 버튼이 조용히 바뀌던 것), 바꿀 쿠팡 글이 더 없음(102·103 교체 끝) -> 안내
assert [x["text"][:1] for x in sm] == ["🔁", "🔁", "첫"] and "[쿠팡] 물티슈 100매" in sm[0]["text"] and sm[0]["reply_parameters"] == {"message_id": 61} and sm[0]["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://t.me/ch/103"
UP = [msg(4, "https://link.coupang.com/a/yy")]; sent.clear(); H.publish_approved()  # 같은 링크만 또 보냄 -> 다른 글 버튼을 또 바꾸지 않음
assert not [1 for m, p in sent if m == "editMessageText"] and [p["text"] for m, p in sent if m == "sendMessage"][0].startswith("이미 채널 글에 붙인 링크야")
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
sent.clear(); H.post_or_draft({**D("[롯데온] 신라면 40봉 (19,900원/무료)"), "hot": "뽐뿌 추천 5", "pop": 42.5, "vpm": 17.5, "rec": 5}, "싸요", 8)
assert {k: json.load(open("posts.json"))[-1].get(k) for k in ("hot", "pop", "vpm", "rec")} == {"hot": "뽐뿌 추천 5", "pop": 42.5, "vpm": 17.5, "rec": 5}  # 사이트 배지·인기 칸·TOP5·리포트용
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
json.dump({"tb_7": {"t": time.time() - 3600, "n": "케라시스 샴푸 980ml 3개"}, "tb_8": {"t": time.time() - 2 * 86400, "n": "옛날 베스트"}, "tb_9": time.time()}, open("seen.json", "w")); got.clear(); H.main()
assert "케라시스 샴푸 980ml 3개" in got[0][0].split("이미 올린 딜")[1] and "옛날 베스트" not in got[0][0]  # 토스 하루특가·베스트로 24시간 안에 올린 상품도 '이미 올린 딜'(예전 숫자 기록은 건너뜀)
# 4-3) 한 번에 1개만 게시(꾸준히), 넘친 좋은 딜은 Claude 판단 그대로 보관 -> 다음 실행에 다시 묻지 않고 점수 높은 것부터 / 3시간 지나면 버림
#      (10/8 17:21 갈비·MSI 7점을 다시 물었더니 15분 뒤 둘 다 5점 미만 -> 못 올림) / 루리웹은 15분 지나면 판단(반응 수치가 없어서)
RU3 = '<rss><channel>' + "".join(it(f"[G마켓] 상품{n}번 특가 묶음 / {n},000원", f"https://bbs.ruliweb.com/market/board/1020/read/9{n}", 20) for n in range(3)) + '</channel></rss>'
H.http = lambda url, *a, **k: RU3 if url == H.RULIWEB_RSS else ""
posted, pod, asked = [], H.post_or_draft, []
H.post_or_draft = lambda d, c, sc, *a, **k: posted.append((d["id"], sc, c))
H.ai_pick = lambda prompt, lines: (asked.append(lines) if lines[0].startswith("[루리웹]") else None) or [{"i": i, "score": (8, 7, 9)[i], "comment": f"c{i}"} for i in range(len(lines))]  # 딜 판단만 셈(21시 넘으면 릴스 재료 채우기도 ai_pick 호출)
json.dump({}, open("seen.json", "w")); H.main()
sj = json.load(open("seen.json"))
assert posted == [("ruliweb_92", 9, "c2")] and len(asked) == 1 and len(asked[0]) == 3  # 20분 된 루리웹 글도 판단, 높은 점수부터(10/10~ 새 딜도 정렬)
assert {k for k in sj if k.startswith("hold_")} == {"hold_ruliweb_90", "hold_ruliweb_91"} and "ruliweb_91" in sj and H.dkey("[G마켓] 상품2번 특가 묶음") in sj
posted.clear(); H.main(); assert posted == [("ruliweb_90", 8, "c0")] and len(asked) == 1  # 다시 안 묻고, 높은 점수부터
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
    feed = '<rss><channel>' + "".join(it(f"[11번가] 상품{k}번 특가 묶음 / {k},000원", f"https://bbs.ruliweb.com/market/board/1020/read/9{k}", 20) for k in range(3)) + '</channel></rss>'  # 수수료 없는 몰(수수료 몰은 1점 낮춤 -> 4-6)
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
# 4-6) 수수료 되는 몰(10/10 진우 '수수료 되는 딜 꼭 챙겨'): 5점도 올림(수수료 없는 몰 5점은 X), 같은 점수면 수수료 딜 먼저
assert H.earns("[G마켓]동원 참치") and H.earns("[롯데ON] 파스타") and H.earns("[토스쇼핑] 삼겹살") and H.earns("[쿠팡] 휴지") and H.earns("[올영] 립밤")
assert not H.earns("[11번가] 호빵") and not H.earns("[카카오톡딜] 뒷고기") and not H.earns("[네이버]토스트기") and not H.earns("[옥션] 라면") and not H.earns("토스 딜")
feed = '<rss><channel>' + "".join(it(f"[{m}] 상품{k}번 특가 묶음 / {k},000원", f"https://bbs.ruliweb.com/market/board/1020/read/9{k}", 20) for k, m in enumerate(("11번가", "지마켓", "롯데온", "11번가"))) + '</channel></rss>'
H.http = lambda url, *a, **k: feed if url == H.RULIWEB_RSS else ""
H.ai_pick = lambda prompt, lines: [{"i": i, "score": (6, 6, 5, 5)[i], "comment": "c"} for i in range(len(lines))]  # 실제 ai_pick처럼 점수순
posted.clear(); json.dump({}, open("seen.json", "w")); H.main(); sj = json.load(open("seen.json"))
assert [p[0] for p in posted] == ["ruliweb_91"] and {k for k in sj if k.startswith("hold_")} == {"hold_ruliweb_90", "hold_ruliweb_92"}, (posted, [k for k in sj if k.startswith("hold_")])
posted.clear(); H.main(); assert [p[0] for p in posted] == ["ruliweb_90"]  # 보관 딜도 점수순(6점 11번가가 5점 롯데온보다 먼저)
sj = json.load(open("seen.json")); sj["hold_ruliweb_95"] = {"t": time.time() - 600, "d": {"id": "ruliweb_95", "title": "[11번가] 수건"}, "p": {"score": 6, "comment": "c"}}
sj["hold_ruliweb_96"] = {"t": time.time() - 600, "d": {"id": "ruliweb_96", "title": "[G마켓] 참치"}, "p": {"score": 6, "comment": "c"}}
json.dump(sj, open("seen.json", "w")); posted.clear(); H.main(); assert [p[0] for p in posted] == ["ruliweb_96"]  # 보관 딜도 같은 점수면 수수료 딜 먼저
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
           {"at": "2026-10-06 09:50", "text": "📌 사용법", "button": "📤 공유", "url": "https://t.me/share/url?url=https%3A%2F%2Ft.me%2Fhotdeal_pick", "pin": True},
           {"at": "2026-10-06 09:55", "text": "🔥 <b>[쿠팡] 계란</b>", "button": "🛒", "url": "https://link.coupang.com/a/egg", "deal": True, "tag": "정품"},
           {"at": "2026-10-06 11:00", "text": "아직", "button": "b", "url": "https://link.coupang.com/a/y"}], open("events.json", "w"))
seen, sent[:], tt3, npj = {}, [], time.time, len(json.load(open("posts.json")))
time.time = lambda: 1791248400; H.events(seen)  # 10/6 10:00 KST
assert [p["text"] for m, p in sent if m == "sendMessage"] == [f"<i>{H.DISCLOSURE}</i>\n\n⚡ <b>쿠가세</b>", "일반", "📌 사용법", f"<i>{H.DISCLOSURE}</i>\n\n🔥 <b>[쿠팡] 계란</b>"] and sent[0][1]["chat_id"] == "@ch"
pje = json.load(open("posts.json")); assert len(pje) == npj + 1 and pje[-1]["url"] == "https://link.coupang.com/a/egg" and pje[-1]["mid"] == 1 and pje[-1]["tag"] == "정품"  # "deal": true만 딜로 기록(사이트·모아보기·Threads, 10/10)
assert [(m, p) for m, p in sent if m != "sendMessage"] == [("pinChatMessage", {"chat_id": "@ch", "message_id": 1, "disable_notification": True})]  # "pin": true만 고정, 알림 없이
assert sent[0][1]["reply_markup"] == {"inline_keyboard": [[{"text": "🔔 알림 신청", "url": "https://link.coupang.com/a/x"}]]}
sent.clear(); H.events(seen); assert not sent  # 1번만
time.time = tt3; os.remove("events.json"); H.events({})  # 파일 없으면 아무것도 안 함
# 5-5b) 쿠팡 행사 자동 게시(10/9 진우 '로켓프레시데이 등 각종 데이 띄워줘' -> 공용 링크로 바로): 뉴시스 산업 RSS의 쿠팡 기사(2일 안)만 Claude에 -> 고른 행사(6점 이상)만 채널에 바로
#       (파트너스 문구·행사명·기간·혜택 3개까지·검색어·버튼 = 쿠팡 홈 링크, 프레시 행사는 로켓프레시 링크), 관리자 사본(채널 글 링크 먼저 -> 답장하면 버튼 교체), 1번만, Claude·채널 실패면 다음에 다시
import inspect
rss = lambda *xs: '<?xml version="1.0"?><rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>' + "".join(
    f"<item><title>{t}</title><link>https://news.coupang.com/archives/{n}/</link><pubDate>{d}</pubDate><description><![CDATA[<p>{b}</p>\n<p>둘째 줄</p>]]></description></item>"
    for n, t, d, b in xs) + "</channel></rss>"
cn = [(1, "[보도자료] 쿠팡, 와우회원 위한 '뷰티풀데이' 개최", "Thu, 08 Oct 2026 23:30:00 +0000", "18일까지 &amp; 5,000원 쿠폰"),
      (2, "[보도자료] 쿠팡, 물류센터 채용", "Thu, 08 Oct 2026 05:00:00 +0000", "채용"),
      (3, "[보도자료] 쿠팡 로켓프레시데이 (지난 글)", "Mon, 05 Oct 2026 01:00:00 +0000", "지난 행사"),
      (5, "가을은 마케팅의 계절…유통가 할인 행사", "Thu, 08 Oct 2026 23:00:00 +0000", "다른 회사")]  # 제목에 쿠팡 없음 -> Claude에 안 보냄
eprompts, efail, ph5, pa5, tt5, tg5b = [], [], H.http, H.ai_pick, time.time, H.tg
def ev_http(url, *a, **k):
    assert url == H.CP_NEWS; return rss(*cn)
def ev_pick(prompt, lines):
    eprompts.append((prompt, lines))
    if efail: raise RuntimeError("Claude 답에 picks 없음")
    return [p for p in [{"i": 0, "score": 9, "q": "뷰티풀데이&위크", "hook": "10/18(일)까지 · 와우회원", "e": "💄", "comment": "c",
                         "pts": ["2만 원 이상 5,000원 쿠폰", "매일 7시 골드박스 <뷰티>", "16개 브랜드", "4번째는 안 씀"]},
                        {"i": 1, "score": 3, "q": "채용", "comment": "c"}] if p["i"] < len(lines)]
H.http, H.ai_pick, seen = ev_http, ev_pick, {}
time.time = lambda: 1791504000  # 10/9 09:00 KST
sent.clear(); H.cp_events(seen)
assert len(eprompts) == 1 and "오늘은 2026-10-09" in eprompts[0][0] and len(eprompts[0][1]) == 2  # 2일 지난 글·쿠팡 아닌 기사는 Claude에 안 보냄
assert eprompts[0][1][0] == "[보도자료] 쿠팡, 와우회원 위한 '뷰티풀데이' 개최 | 10/09 | 18일까지 & 5,000원 쿠폰 둘째 줄"  # 본문 태그·줄바꿈 정리, 게시일 KST
assert [m for m, p in sent] == ["sendMessage", "copyMessage"]  # 3점(채용)은 안 올림
p = sent[0][1]
assert p["chat_id"] == "@ch" and p["text"] == (f"<i>{H.DISCLOSURE}</i>\n\n💄 <b>쿠팡 뷰티풀데이&amp;위크</b>\n10/18(일)까지 · 와우회원\n\n• 2만 원 이상 5,000원 쿠폰\n"
                                                 "• 매일 7시 골드박스 &lt;뷰티&gt;\n• 16개 브랜드\n\n👉 쿠팡 앱 검색창에 <b>뷰티풀데이&amp;위크</b>")  # Claude 글은 HTML 이스케이프
assert p["reply_markup"]["inline_keyboard"] == [[{"text": "🛒 쿠팡 바로가기", "url": H.CP_HOME}]] and H.CP_HOME.startswith("https://link.coupang.com/a/")
c = sent[1][1]
assert c["chat_id"] == H.ADMIN and c["from_chat_id"] == "@ch" and c["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://t.me/ch/1"  # 답장 -> 이 채널 글 교체
assert sorted(seen) == ["cn_https://news.coupang.com/archives/1/", "cn_https://news.coupang.com/archives/2/"]
sent.clear(); H.cp_events(seen); assert not sent and len(eprompts) == 1  # 1번만(Claude도 다시 안 부름)
cn.insert(0, (4, "[보도자료] 쿠팡 로켓프레시데이", "Fri, 09 Oct 2026 00:00:00 +0000", "26일까지"))
efail.append(1)
try:
    H.cp_events(seen); assert False
except RuntimeError:
    pass
assert "cn_https://news.coupang.com/archives/4/" not in seen and not sent  # Claude 실패 -> 기록 안 함(다음 실행에 다시)
efail.clear(); H.tg = lambda method, **p: sent.append((method, p)) and None
H.cp_events(seen); assert "cn_https://news.coupang.com/archives/4/" not in seen and [m for m, p in sent] == ["sendMessage"]  # 채널 게시 실패 -> 다음에 다시
H.tg = tg5b; sent.clear(); H.cp_events(seen); assert "cn_https://news.coupang.com/archives/4/" in seen and len(sent) == 2
cn.insert(0, (6, "[보도자료] 쿠팡 로켓프레시데이", "Fri, 09 Oct 2026 00:10:00 +0000", "20일부터"))
H.ai_pick = lambda prompt, lines: [{"i": 0, "score": 8, "q": "로켓프레시데이", "hook": "20일부터", "comment": "c"}]
sent.clear(); H.cp_events(seen); assert sent[0][1]["reply_markup"]["inline_keyboard"][0][0]["url"] == H.CP_FRESH != H.CP_HOME  # 프레시 행사 = 로켓프레시 링크
pjb = open("posts.json").read(); json.dump([{"t": "2026-10-09 08:00", "text": "🔥 [쿠팡] 이미 딜로 올린 쿠팡 위크 쿠폰 (1원)", "url": "u"}], open("posts.json", "w"), ensure_ascii=False)
cdeals = [{"id": "ppomppu_9", "url": "https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&no=9", "title": "[쿠팡] 로켓프레시 데이 최대 50% (10/20~26)", "desc": "와우 회원 쿠폰", "age": 5},
          {"id": "ppomppu_10", "url": "https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&no=10", "title": "[쿠팡] 신라면 40봉 (19,900원)", "desc": "", "age": 5},
          {"id": "ruliweb_1", "url": "https://bbs.ruliweb.com/market/board/1020/read/1", "title": "[G마켓] 빅스마일데이 시작", "desc": "", "age": 5},
          {"id": "ppomppu_11", "url": "https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&no=11", "title": "[쿠팡] 이미 딜로 올린 쿠팡 위크 쿠폰 (1원)", "desc": "", "age": 5},
          {"id": "ppomppu_12", "url": "https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&no=12", "title": "[쿠팡] 사흘 전 브랜드데이", "desc": "", "age": 4000}]  # 2일 지난 글 제외
eprompts.clear(); H.ai_pick = lambda prompt, lines: eprompts.append(lines) or [{"i": 0, "score": 8, "q": "로켓프레시데이", "hook": "10/20~26", "comment": "c"}]
sent.clear(); H.cp_events(seen, cdeals)
assert eprompts == [["[쿠팡] 로켓프레시 데이 최대 50% (10/20~26) | 10/09 | 와우 회원 쿠폰"]]  # 기사 없는 행사: 커뮤니티 글(쿠팡+행사 낱말, 딜로 안 올라간 것)만
assert sent[0][1]["reply_markup"]["inline_keyboard"][0][0]["url"] == H.CP_FRESH and "ppomppu_9" in seen and "ppomppu_10" not in seen  # 행사로 올린 글은 딜로 또 안 올림
open("posts.json", "w").write(pjb)
assert "goldbox, lambda s: cp_events(s, deals), top_deals, toss_deals" in inspect.getsource(H.main)
H.http, H.ai_pick, time.time = ph5, pa5, tt5
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
assert t.endswith("TOP2</b>\n<i>밤 12시까지 선착순 · 일부 고객에게만 보이고 수량 제한이 있을 수 있어요</i>\n\n1️⃣ <a href=\"https://toss.im/_m/3\"><b>토스상품3</b></a>\n💰 <b>4,000원</b> (30%↓)\n👉 나\n\n2️⃣ <a href=\"https://toss.im/_m/1\"><b>토스상품1</b></a>\n💰 <b>2,000원</b> (10%↓)\n👉 다")
assert p["reply_markup"]["inline_keyboard"] == [[{"text": "1️⃣ 토스상품3", "url": "https://toss.im/_m/3"}], [{"text": "2️⃣ 토스상품1", "url": "https://toss.im/_m/1"}]]  # 번호 버튼(10/9 TOP 모양)
tp, kb = H.top_post("H", [("A&B", "https://x?a=1&b=2", ["💰 <b>1원</b>", "", "👉 c"])])
assert tp == 'H\n\n1️⃣ <a href="https://x?a=1&amp;b=2"><b>A&amp;B</b></a>\n💰 <b>1원</b>\n👉 c' and kb == [[{"text": "1️⃣ A&B", "url": "https://x?a=1&b=2"}]]
sent.clear(); H.toss_deals(seen); assert not sent  # 하루 1번
assert len(json.load(open("posts.json"))) == n0  # API 상품은 사이트에 안 남김
pk = H.ai_pick; H.ai_pick = lambda prompt, lines: offered.extend(lines) or [{"i": 0, "score": 9, "comment": "가"}]  # 10/10 하루특가 9·13·17시
offered.clear(); time.time = lambda: 1791248400 + 3 * 3600; H.toss_deals(seen)  # 13:00 회차: 9시에 올린 상품(tb_)·품절은 빼고 다시 고름
assert [l.split(" |")[0] for l in offered] == ["토스상품0"] and not sent  # 남은 건 발급 실패 상품뿐 -> 글 없음
offered.clear(); H.toss_deals(seen); assert not offered  # 같은 회차 1번
offered.clear(); time.time = lambda: 1791248400 + 10 * 3600 + 1800; H.toss_deals(seen); assert not offered  # 20:30: 17시 회차 3시간 지남 -> 안 올림
H.ai_pick, time.time = pk, lambda: 1791248400
H.EVENTS, ev0 = "ev_toss.json", H.EVENTS; json.dump([{"at": "2026-10-06 21:00", "name": "토스상품1,"}, {"at": "2026-10-05 21:00", "name": "토스상품3"}], open(H.EVENTS, "w"))
offered.clear(); H.ai_pick = lambda prompt, lines: offered.extend(lines) or []; H.toss_deals({})  # 10/11: 진우 링크로 오늘 예약한 상품(name, 기호 무시)은 하루특가 자동 글 후보에서 뺌, 어제 예약은 상관없음
assert [l.split(" |")[0] for l in offered] == ["토스상품0", "토스상품3"]; H.EVENTS, H.ai_pick = ev0, pk
th = []  # 하루특가는 Threads에도 1개(신청서 서비스 = 텔레그램 채널 + 스레드 자동 게시): 대가성 문구 맨 앞, 500자 안, 채널과 같은 순서, HTML 태그 없음
def toss_th(url, body=None, headers=None, method=None):
    if not url.startswith(H.THREADS):
        return toss_http(url, body, headers, method)
    th.append(url)
    return '{"id": "c1"}'
H.http, H.E["THREADS_TOKEN"], sl, H.time.sleep = toss_th, "tk", H.time.sleep, lambda s: None
seen.clear(); sent.clear(); H.toss_deals(seen)
txt = parse_qs(urlsplit([u for u in th if "/threads?" in u][0]).query)["text"][0]
assert "TOP2\n밤 12시까지 선착순 · 일부 고객에게만 보이고 수량 제한이 있을 수 있어요\n\n1️⃣ 토스상품3 — 4,000원\nhttps://toss.im/_m/3\n\n2️⃣ 토스상품1 — 2,000원\nhttps://toss.im/_m/1" in txt
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
assert "<b>베스트1</b></a>\n💰 <b>6,930원</b> (88%↓) · ⭐ 4.8 (리뷰 1,523)\n👉 개당 99원" in t and len(sent[-1][1]["reply_markup"]["inline_keyboard"]) == 2
assert len(offered) == 3 and "베스트4" not in str(offered) and "리뷰 4.8점 1,523개" in offered[0] and "tb_1" in seen and "tb_3" in seen
assert seen["tb_1"]["n"] == "베스트1" and seen["tb_1"]["t"] == 1791257400  # 이름도 남김 -> 커뮤니티 딜 판단 때 '이미 올린 딜'(10/10 케라시스 중복)
sent.clear(); H.toss_deals(seen, True); assert not sent  # 같은 회차 1번
offered.clear(); time.time = lambda: 1791271800; H.toss_deals(seen, True)  # 16:30 회차(10/8 하루 3번): 1·3 빠지고 5만 -> 안 고르면 안 올림
assert offered == ["베스트5 | 6,930원 (88% 할인) | 리뷰 4.8점 1,523개"] and not sent and "tossbest_20261006_16" in seen
offered.clear(); time.time = lambda: 1791285000; H.toss_deals(seen, True)  # 20:10: 낮에 올린 1·3은 후보에서 빠짐 -> 5만 남음 -> Claude가 안 고르면 안 올림
assert offered == ["베스트5 | 6,930원 (88% 할인) | 리뷰 4.8점 1,523개"] and not sent and "tossbest_20261006_20" in seen
sent.clear(); H.toss_deals(seen, True); assert not sent and not offered[1:]
assert H.TOSS_BEST_HOURS == (10, 11, 12, 14, 16, 18, 20) and H.TOSS_BEAUTY_HOURS == (15, 19)  # 10/11 '회차 늘리기': 묶음 글 없는 11시(베스트)·19시(뷰티)
for hh, ts in ((10, 1791248700), (11, 1791252300), (14, 1791263100), (18, 1791277500)):  # 10:05·11:05·14:05·18:05 회차도 1번씩
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
sent.clear(); cats_called[:] = []; time.time = lambda: 1791265800; H.toss_deals(seen, "beauty"); assert not sent and not cats_called  # 10/11 '화장품도': 10/6 14:50 = 15시 전
H.http = lambda url, *a, **k: (cats_called.append(400) or json.dumps({"resultType": "SUCCESS", "success": {"items": [{"tacaItemId": 41, "displayName": "뷰티41", "displayPrice": 9900, "isSoldOut": False}]}})
                               if "/best-categories/400" in url else cat_http(url, *a, **k))
pk2, H.ai_pick = H.ai_pick, (lambda prompt, lines: prompts.append(prompt) or [{"i": 0, "score": 8, "comment": "단위가격 좋음"}])
time.time = lambda: 1791267000; H.toss_deals(seen, "beauty"); t = sent[-1][1]["text"]; H.http, H.ai_pick = cat_http, pk2  # 15:10: 뷰티 카테고리만(식품·생활용품·돌아가는 칸 X)
assert cats_called == [400] and "💄 <b>토스 뷰티 베스트 중 살 만한" in t and "tossbeauty_20261006_15" in seen and "화장품 효능" in prompts[-1]
sent.clear(); H.toss_deals(seen, "beauty"); assert not sent and "lambda s: toss_deals(s, \"beauty\")" in inspect.getsource(H.main); time.time = lambda: 1791274200 + 86400  # 하루 1번, main에 들어 있음 (시각은 앞 테스트 그대로 되돌림)
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
# 5-3e) 반응 좋은 딜 TOP5 묶음(10/9 진우 '사람들이 사는 제품을 보기 좋고 사고 싶게'): 12시 = 0~12시, 18시 = 12~18시에 채널에 올린 딜 중 pop 높은 순 5개,
#       3개 미만이면 안 올림, 회차마다 1번, 제휴 프로그램별 대가성 문구 맨 앞(중복 없이), 배지 줄·단위가격 줄은 이유에서 빠짐, 번호 버튼
bak, cn = open("posts.json").read(), H.aff_note("https://link.coupang.com/a/x")
json.dump([{"t": "2026-10-05 23:00", "text": "🔥 [G마켓] 어제딜 (1,000원)", "url": "https://g0", "mid": 9, "pop": 99},
           {"t": "2026-10-06 09:00", "text": "🔥 [G마켓] 우유 24팩 (12,900원/무료)\n🏆 인기 · 뽐뿌 추천 5\n\n싸다 우유\n💡 단위가격 개당 537원\n\n출처: 뽐뿌",
            "url": "https://www.ppomppu.co.kr/v?no=1", "mid": 1, "pop": 10, "hot": "뽐뿌 추천 5", "unit": "개당 537원"},
           {"t": "2026-10-06 10:00", "text": f"{cn}\n\n🔥 [쿠팡] 휴지 30롤 (19,900원/무료)\n\n휴지 최저가\n\n출처: 클리앙", "url": "https://link.coupang.com/a/x", "mid": 2, "pop": 50, "vpm": 45.0, "rec": 1},
           {"t": "2026-10-06 11:00", "text": f"{H.TOSS_NOTE}\n\n🔥 [토스] 계란 30구 (6,900원)\n\n한 판 230원", "url": "https://toss.im/_m/5", "mid": 3, "pop": 30},
           {"t": "2026-10-06 11:10", "text": f"{cn}\n\n🔥 [쿠팡] 라면 (9,000원)\n\n싸다", "url": "https://link.coupang.com/a/y", "mid": 4, "pop": 1},
           {"t": "2026-10-06 11:20", "text": "🔥 [G마켓] 사본만 (1,000원)", "url": "https://g1", "mid": None, "pop": 80},  # 채널에 안 나감
           {"t": "2026-10-06 11:30", "text": "🔥 [쿠팡] 골드박스 (1,000원)", "url": "https://link.coupang.com/a/z", "mid": 5},  # 반응 수치 없음
           {"t": "2026-10-06 12:30", "text": "🔥 [G마켓] 오후1 (1,000원)", "url": "https://g2", "mid": 6, "pop": 70},
           {"t": "2026-10-06 13:00", "text": "🔥 [G마켓] 오후2 (2,000원)", "url": "https://g3", "mid": 7, "pop": 5},
           {"t": "2026-10-06 14:00", "text": "🔥 [G마켓] 오후3 (3,000원)", "url": "https://g4", "mid": 8, "pop": 6},
           {"t": "2026-10-06 18:00", "text": "🔥 [G마켓] 저녁 (3,000원)", "url": "https://g5", "mid": 10, "pop": 90}], open("posts.json", "w"))  # 18시 글은 18시 회차 밖
seen, sent[:] = {}, []
time.time = lambda: 1791252000; H.top_deals(seen); assert not sent and not seen  # 11:00 KST: 12시 전
time.time = lambda: 1791255900; H.top_deals(seen)  # 12:05
m, p = sent[-1]; t = p["text"]
assert m == "sendMessage" and p["chat_id"] == "@ch" and "top_20261006_12" in seen and t.startswith(f"<i>{cn}</i>\n<i>{H.TOSS_NOTE}</i>\n\n🏆 <b>지금 반응 좋은 딜 TOP4</b> (12시)")
assert t.index("<b>휴지 30롤</b>") < t.index("<b>계란 30구</b>") < t.index("<b>우유 24팩</b>") < t.index("<b>라면</b>") and "어제딜" not in t and "사본만" not in t and "골드박스" not in t and "오후" not in t
assert '1️⃣ <a href="https://link.coupang.com/a/x"><b>휴지 30롤</b></a>\n💰 <b>19,900원</b>\n👀 분당 조회 45회 · 추천 1\n👉 휴지 최저가' in t and "\n👀 반응 30\n" in t  # 반응 수치: 분당 조회·추천 따로, 따로 값이 없는 10/9 첫 배포분은 합친 값
assert '<b>우유 24팩</b></a>\n💰 <b>12,900원</b> · 개당 537원\n👀 뽐뿌 추천 5\n👉 싸다 우유\n\n4️⃣' in t and t.count(cn) == 1
assert [r[0]["text"] for r in p["reply_markup"]["inline_keyboard"]] == ["1️⃣ 휴지 30롤", "2️⃣ 계란 30구", "3️⃣ 우유 24팩", "4️⃣ 라면"]
sent.clear(); time.time = lambda: 1791256800; H.top_deals(seen); assert not sent  # 같은 회차 1번
time.time = lambda: 1791277800; H.top_deals(seen); t = sent[-1][1]["text"]  # 18:10 -> 12~18시만
assert "TOP3</b> (18시)" in t and t.index("오후1") < t.index("오후3") < t.index("오후2") and "저녁" not in t and "휴지" not in t and not t.startswith("<i>") and "👉" not in t  # 코멘트 없으면 👉 줄 X
json.dump([{"t": f"2026-10-07 1{k}:00", "text": f"🔥 [G마켓] 다음날{k} (1,000원)", "url": "https://g", "mid": 20 + k, "pop": 9} for k in (2, 3)], open("posts.json", "w"))
sent.clear(); time.time = lambda: 1791281400 + 86400; H.top_deals(seen); assert not sent and "top_20261007_18" in seen  # 다음 날 19:10(12시 회차 놓침): 12~18시 2개 -> 3개 미만이라 안 올림, 회차는 끝
open("posts.json", "w").write(bak)
# 5-3d) 토스 딜 자동 링크(10/9 진우 '토스 딜 직접 추출' -> 기록만 -> '수정하자' -> '수수료 링크 안 붙은 것도 자동으로'): 쉐어링크 없는 최근 3일 [토스] 채널 딜만,
#       ① 루리웹·클리앙 = 처음 1번 글의 상품 주소를 다시 읽어 발급 ② 토스 API 목록(1일치 모음, 쉐어링크 FAQ 권장)에서 이름 겹침 후보 -> Claude 8점 이상만 발급 -> 채널 글 버튼·대가성 문구·
#       사본 '교체됨'·posts.json 교체(진우 답장과 같은 relink_channel). 못 찾으면 새 후보가 목록에 들어올 때만 다시(본 후보는 다시 안 물음), 찾으면(발급 실패 포함) 끝,
#       목록 호출은 카테고리·하루특가 하루 1번·베스트 1시간 1번
import io, contextlib
mcalls, mprompts, medits = [], [], []
ml = {"today": [(51, "광동 비타500 100ml 20병", 9900)], 200: [(41, "제주 극조생 감귤 5kg", 9900)], 210: [(81, "씨없는 청도반시 2.5kg", 12800)],
      300: [(31, "모나리자 에코 미용티슈 300매, 12개", 11990), (32, "깨끗한나라 화장지 30롤", 15900)],
      "best": [(31, "모나리자 에코 미용티슈 300매, 12개", 11990), (61, "삼다수 2L 12병", 9000), (71, "아빠표 구운계란 중란 30구 2판", 16900)]}
rb = "https://bbs.ruliweb.com/market/board/1020/read/"
def match_http(url, body=None, headers=None, method=None):
    mcalls.append(url.split("/openapi")[-1])
    it = lambda k: json.dumps({"resultType": "SUCCESS", "success": {"items": [{"tacaItemId": i, "displayName": n, "displayPrice": p} for i, n, p in ml[k]]}})
    if url.startswith("https://service.toss.im/shopping-discovery/c/"):  # 토스 앱 공유 주소 -> 상품 페이지(canonical = /t/번호, 본문엔 다른 상품 링크도)
        return '<a href="https://toss.shopping/t/1"><link rel="canonical" href="https://toss.shopping/t/889"/>'
    if url.startswith(rb):  # 루리웹 글: 1 = 출처에 토스 상품 주소, 2 = 토스 주소 없음
        return '<div class="source_url"><a href="https://toss.shopping/t/777">' if url.endswith("/1") else '<div class="view_content">본문</article>'
    if url.endswith("/links"):
        assert body["publisherId"] == "pub-1"
        i = body.get("tacaItemId") or body["tacaId"]
        return json.dumps({"resultType": "SUCCESS", "success": {"shortUrl": f"https://toss.shopping/_m/L{i}"}} if i != 61
                          else {"resultType": "FAIL", "error": {"reason": "발급 제한 상품"}})
    if url.endswith("/categories"):
        return json.dumps({"resultType": "SUCCESS", "success": {"categories": [{"categoryId": 200, "displayName": "식품", "children": [{"categoryId": 210, "displayName": "과일"}, {"categoryId": 999, "displayName": "안됨"}]},
                                                                               {"categoryId": 300, "displayName": "생활용품", "children": [{"categoryId": 310, "displayName": "세제"}]}]}})
    if "/best-categories/999" in url:
        raise RuntimeError("HTTP 400")  # 하위 카테고리 베스트가 안 되는 ID
    if "/best-categories/" in url:
        assert url.endswith("?size=100"); return it(int(url.rsplit("/", 1)[1][:3]))
    if url.endswith("/products/today-deals?size=30"):
        return it("today")
    if url.endswith("/products/best-selling?size=100"):
        return it("best")
    raise AssertionError(url)
def match_pick(prompt, lines):
    mprompts.append((prompt, lines))
    return [{"i": 0, "score": 9 if re.search("모나리자|삼다수|계란|감귤 10kg|풍천장어", lines[0]) else 6, "comment": "같은 상품"}]
def relink_run():
    mcalls.clear(); mprompts.clear(); medits.clear(); out = io.StringIO()
    with contextlib.redirect_stdout(out): H.toss_relink(seen)
    return out.getvalue()
tg5 = H.tg
H.http, H.ai_pick, H.tg, pj0 = match_http, match_pick, (lambda method, **p: medits.append((method, p)) or {"message_id": 1}), open("posts.json").read()
now = 1791259200  # 10/6 13:00 KST
time.time = lambda: now
kt = lambda h: time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - h * 3600))
pp = "https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&no="
mp = [{"t": kt(2), "text": "🔥 [토스] 모나리자 에코 미용티슈 300매 12입 (10,990원/무배)\n\n코멘트", "entities": [{"type": "bold", "offset": 3, "length": 10}], "url": pp + "1", "mid": 11, "cp": 111},
      {"t": kt(1), "text": "🔥 [토스] 제주 극조생감귤 10kg (12,900원/무배)", "url": pp + "2", "mid": 12, "cp": 112},
      {"t": kt(1), "text": "🔥 [토스] 이미 링크 붙은 딜 (1,000원)", "url": "https://toss.shopping/_m/abc", "mid": 13},
      {"t": kt(1), "text": "🔥 [쿠팡] 쿠팡 딜 모나리자 에코 (1,000원)", "url": "https://www.coupang.com/vp/products/1", "mid": 14, "cp": 114},
      {"t": kt(80), "text": "🔥 [토스] 모나리자 에코 오래된 딜 (1,000원)", "url": pp + "5", "mid": 15, "cp": 115},
      {"t": kt(1), "text": "🔥 [토스] 아무거나 전혀 다른 상품 (1,000원)", "url": pp + "6", "mid": 16, "cp": 116},
      {"t": kt(1), "text": "🔥 [토스] 모나리자 에코 채널 실패 딜 (1,000원)", "url": pp + "7"},  # 채널에 안 올라간 글(mid 없음)
      {"t": kt(1), "text": "🔥 [토스] 핫식스 더킹 애플홀릭 355ml 24개 17,000원", "url": rb + "1", "mid": 20, "cp": 120},
      {"t": kt(1), "text": "🔥 [토스] 오뚜기 진라면 매운맛 40봉 (19,900원)", "url": rb + "2", "mid": 21, "cp": 121},
      {"t": kt(1), "text": "🔥 [토스] 펩시제로 제로카페인 355ml 48캔 (25,832원)", "url": "https://service.toss.im/shopping-discovery/c/888", "mid": 25, "cp": 125}]
json.dump(mp, open("posts.json", "w"), ensure_ascii=False)
seen = {}
log = relink_run()
pj = {p.get("mid"): p for p in json.load(open("posts.json"))}
assert "모나리자 에코 미용티슈 300매 12입 (10,990원/무배) -> 모나리자 에코 미용티슈 300매, 12개 11,990원 (id 31, 9점) | 링크 교체 | 후보" in log, log
assert seen["tb_31"] == {"t": now, "n": "모나리자 에코 미용티슈 300매, 12개"} and not any(k.startswith("tb_") and k != "tb_31" for k in seen)  # 찾은 상품만 -> 3일 동안 토스 베스트에 다시 안 나감(10/10 삼겹살)
assert "핫식스 더킹 애플홀릭 355ml 24개 17,000원 -> 글의 상품 주소 https://toss.shopping/t/777 | 링크 교체" in log  # 루리웹 글을 다시 읽어 발급(tacaId)
assert "제주 극조생감귤 10kg (12,900원/무배) -> 없음" in log and "아무거나 전혀 다른 상품 (1,000원) -> 없음 | 후보 0/" in log  # 감귤 5kg = 용량 달라 6점 -> 없음, 겹침 없으면 Claude 안 부름
assert "진라면 매운맛 40봉 (19,900원) -> 없음" in log  # 루리웹 글에 토스 주소 없음 -> 목록 대조
assert "펩시제로 제로카페인 355ml 48캔 (25,832원) -> 글의 상품 주소 https://toss.shopping/t/889 | 링크 교체" in log  # 토스 앱 공유 주소 -> 상품 페이지 canonical -> 발급
assert "이미 링크" not in log and "쿠팡 딜" not in log and "오래된" not in log and "채널 실패" not in log and len(mprompts) == 2  # 쉐어링크 딜·다른 몰·3일 지난 딜·채널 글 아닌 것 제외
assert mprompts[0][1][0] == "모나리자 에코 미용티슈 300매, 12개 | 11,990원" and "깨끗한나라" not in str(mprompts[0][1]) and "모나리자 에코 미용티슈 300매 12입" in mprompts[0][0]
assert [81, "씨없는 청도반시 2.5kg", 12800, now] in [x[:4] for x in seen["tosscache"]["items"]] and "toss sub 안됨 RuntimeError('HTTP 400')" in log  # 식품 하위 베스트도 목록에(10/10 청도반시), 안 되는 ID는 그것만 건너뜀
assert sorted(mcalls) == sorted(["/products/today-deals?size=30", "/categories", "/products/best-categories/200?size=100", "/products/best-categories/300?size=100",
                                 "/products/best-categories/210?size=100", "/products/best-categories/999?size=100",  # 식품 하위만(생활용품 하위 310은 안 받음)
                                 "/products/best-selling?size=100", "/links", "/links", "/links", rb + "1", rb + "2",
                                 "https://service.toss.im/shopping-discovery/c/888"])  # 뽐뿌 글은 안 읽음(서버 차단, 우회 안 함)
ch = {p["message_id"]: p for m, p in medits if m == "editMessageText" and p["chat_id"] == H.CHANNEL}
ad = {p["message_id"]: p for m, p in medits if m == "editMessageText" and p["chat_id"] == H.ADMIN}
assert sorted(ch) == [11, 20, 25] and ch[11]["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://toss.shopping/_m/L31" and ch[11]["text"].startswith(H.TOSS_NOTE)
assert ch[20]["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://toss.shopping/_m/L777"
assert ch[11]["entities"][1]["offset"] == 3 + len(H.TOSS_NOTE.encode("utf-16-le")) // 2 + 2  # 대가성 문구만큼 굵은 글씨 위치를 밂
assert sorted(ad) == [111, 120, 125] and "채널 글 교체됨" in str(ad[111]["reply_markup"])
assert pj[11]["url"] == "https://toss.shopping/_m/L31" and pj[11]["text"].startswith(H.TOSS_NOTE) and pj[20]["url"] == "https://toss.shopping/_m/L777"
assert pj[25]["url"] == "https://toss.shopping/_m/L889"
assert {k: p["url"] for k, p in pj.items() if k not in (11, 20, 25)} == {p.get("mid"): p["url"] for p in mp if p.get("mid") not in (11, 20, 25)}  # 찾은 딜만 교체
H.http = lambda url, *a, **k: '<a href="https://toss.shopping/t/5">'; assert H.plain("https://toss.shopping/i/5") is None; H.http = match_http  # canonical 없으면 None(남의 상품 안 씀)
assert [51, "광동 비타500 100ml 20병", 9900, now] in [x[:4] for x in seen["tosscache"]["items"]] and seen["tr_12"]["ids"] == [41] and seen["tr_11"]["done"] and seen["tr_20"]["done"]
assert not relink_run() and not mcalls and not mprompts and not medits  # 같은 시간대·새 후보 없음 -> API·Claude·루리웹 다시 안 부르고 로그도 없음
seen["tr_26"] = {"t": now, "ids": []}; mp = json.load(open("posts.json")) + [{"t": kt(1), "text": "🔥 [토스] 펩시 제로 라임 355ml 48캔 (25,000원)", "url": "https://service.toss.im/shopping-discovery/c/890", "mid": 26, "cp": 126}]
json.dump(mp, open("posts.json", "w"), ensure_ascii=False)
assert "-> 글의 상품 주소 https://toss.shopping/t/889 | 링크 교체" in relink_run() and seen["tr_26"]["done"]  # 배포 전부터 못 찾고 있던 딜(src 표시 없음)도 주소 풀기 1번
mp = json.load(open("posts.json"))
mp = json.load(open("posts.json")) + [{"t": kt(0), "text": "🔥 [토스쇼핑] 삼다수 2L 12병 (8,500원)", "url": pp + "8", "mid": 17, "cp": 117}]
json.dump(mp, open("posts.json", "w"), ensure_ascii=False)
log = relink_run()
assert mcalls == ["/links"] and len(mprompts) == 1 and not medits and "삼다수 2L 12병 9,000원 (id 61, 9점) | 발급 실패" in log  # 같은 시간대 = 저장 목록 재사용, 발급 실패 = 그대로
assert json.load(open("posts.json"))[-1]["url"] == pp + "8" and seen["tr_17"]["done"]
assert not relink_run() and not mcalls  # 발급 실패한 딜은 끝(다시 안 함)
time.time = lambda: now + 3600
ml["best"] = [(42, "제주 극조생 감귤 10kg", 12900), (62, "제주 삼다수 2L 12병", 8800)]  # 1시간 뒤 베스트: 계란은 빠지고 감귤 10kg·다른 삼다수가 들어옴(삼다수 딜은 끝났으니 안 물음)
mp.append({"t": kt(0), "text": "🔥 [토스] 아빠표 구운계란 중란 30구 2판(16,900원/무료)", "url": pp + "9", "mid": 22, "cp": 122}); json.dump(mp, open("posts.json", "w"), ensure_ascii=False)
log = relink_run()
assert mcalls == ["/products/best-selling?size=100", "/links", "/links"], mcalls  # 베스트만 다시(카테고리·하루특가는 하루 1번)
assert "제주 극조생감귤 10kg (12,900원/무배) -> 제주 극조생 감귤 10kg 12,900원 (id 42, 9점) | 링크 교체 | 다시 · 후보 1/" in log, log  # 못 찾은 딜 = 새 후보만 다시 물음
assert [x[1] for x in mprompts] == [["제주 극조생 감귤 10kg | 12,900원"], ["아빠표 구운계란 중란 30구 2판 | 16,900원"]]  # 본 후보(5kg)는 다시 안 물음
assert "(id 71, 9점) | 링크 교체" in log and sorted(p["message_id"] for m, p in medits if m == "editMessageText" and p["chat_id"] == H.CHANNEL) == [12, 22]  # 베스트에서 빠진 계란도 1일 모음에서 찾음
assert "진라면" not in log and "전혀 다른" not in log  # 새 후보 없는 딜 = 조용히
time.time = lambda: now + 86400 + 7200
for k in ml: ml[k] = []
mp.append({"t": kt(0), "text": "🔥 [토스] 모나리자 에코 미용티슈 300매 12입 (9,990원)", "url": pp + "10", "mid": 23, "cp": 123}); json.dump(mp, open("posts.json", "w"), ensure_ascii=False)
assert "후보 0/0" in relink_run() and seen["tosscache"]["items"] == []  # 1일 지난 목록 상품은 버림(쉐어링크 FAQ '가능한 한 1일 이내')
H.EVENTS, ev0 = "ev_relink.json", H.EVENTS  # 10/11: 진우가 예약한 토스 링크도 후보 -> 뽐뿌 [토스] 딜이 같은 상품이면 발급 없이 그 링크로 교체(뽐뿌 민물장어 = 진우 링크 풍천장어)
json.dump([{"at": kt(-3), "name": "고창 풍천장어 자포니카 민물장어+소스, 손질 후, 700g, 2-4미, 1개", "button": "🛒 18,900원 구매하기", "url": "https://toss.shopping/_m/DFe30tws"},
           {"at": kt(80), "name": "민물장어 오래된 예약", "button": "🛒 1원 구매하기", "url": "https://toss.shopping/_m/OLD"}, {"at": kt(1), "name": "민물장어 쿠팡 예약", "url": "https://link.coupang.com/a/x"}], open(H.EVENTS, "w"))
mp.append({"t": kt(0), "text": "🔥 [토스] 민물장어 1kg(손질 후 700g) (18,900원/무배)", "url": pp + "12", "mid": 27, "cp": 127}); json.dump(mp, open("posts.json", "w"), ensure_ascii=False)
log = relink_run(); ch = [p for m, p in medits if m == "editMessageText" and p["chat_id"] == H.CHANNEL]
assert "(id ev:https://toss.shopping/_m/DFe30tws, 9점) | 링크 교체" in log and "/links" not in mcalls and not any("DFe30tws" in k for k in seen if k.startswith("tb_")), log
assert [p["message_id"] for p in ch] == [27] and ch[0]["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://toss.shopping/_m/DFe30tws" and ch[0]["text"].startswith(H.TOSS_NOTE)
assert mprompts[-1][1] == ["고창 풍천장어 자포니카 민물장어+소스, 손질 후, 700g, 2-4미, 1개 | 18,900원"]  # 3일 지난 예약·쉐어링크 아닌 예약은 후보 X
H.EVENTS = ev0
H.HAS_TOSS = False; mcalls.clear(); json.dump(mp + [{"t": kt(-1), "text": "🔥 [토스] 새 딜 (1원)", "url": pp + "11", "mid": 24}], open("posts.json", "w"), ensure_ascii=False)
H.toss_relink({}); assert not mcalls; H.HAS_TOSS = True  # 토스 API 키 없으면 아무것도 안 함
assert "toss_relink, toss_picks, toss_soldout, toss_reopen, lambda s: digest" in inspect.getsource(H.main)
open("posts.json", "w").write(pj0); H.tg = tg5
os.remove("toss.json"); time.time, H.HAS_TOSS, H.http, H.ai_pick = tt, False, ph, pa

# 5-3e) 토스 품절 표시(10/11 진우 '품절 뜨는 경우는 속상해 — 구매하는 사람이 알 수 있게, 알람도'): 오늘 올린 토스 글(진우 예약 = 게시 때 글 번호·본문 저장 + 이름으로 API id, API 묶음 = 게시 때 id 저장)을
#       매 실행 상품 상세 1번(최대 30개, 오래 안 본 것부터)으로 다시 봄 -> 품절이면 채널 글에 ⛔ 줄 + 버튼 글자만(링크 그대로), 밤 12시 지나 다시 열리면(올린 가격 이하) 답글 🔔 + 줄 지움,
#       1시 넘어도 안 열리면 '특가 끝'으로 바꾸고 그만 봄. 품절된 하루특가는 낮엔 다시 안 봄(일 상한). 상태는 글 수정이 성공해야 바꿈
import calendar
T = lambda s: calendar.timegm(time.strptime(s, "%Y-%m-%d %H:%M")) - 9 * 3600  # KST 시각 -> epoch
H.E.update(TOSS_ACCESS_KEY="ak", TOSS_SECRET_KEY="sk", TOSS_PUBLISHER_ID="pub-1"); H.E.pop("THREADS_TOKEN", None)
H.HAS_TOSS, ph3, tg6, pa3, pj3, ev3 = True, H.http, H.tg, H.ai_pick, open("posts.json").read(), H.EVENTS
so_out, so_price, so_calls, so_sent, so_fail = set(), {}, [], [], {"edit": 0, "page2": 0}
SO_DAY = [(901 + k, f"하루특가{k}", 1000 * (k + 1)) for k in range(35)] + [(950, "CJ제일제당 쇠고기 진한다시 1kg", 6900), (951, "같은 링크 두 번", 4800)]
def so_http(url, body=None, headers=None, method=None):
    if url == "https://oauth2.cert.toss.im/token":
        return json.dumps({"access_token": "TK", "expires_in": 31535999})
    so_calls.append(url.split("/openapi")[-1])
    if url.endswith("/links"):
        return json.dumps({"resultType": "SUCCESS", "success": {"shortUrl": f"https://toss.shopping/_m/A{body['tacaItemId']}"}})
    if "/products/today-deals?size=30" in url:  # 커서 페이징: 1쪽 30개 + 2쪽 7개(진한다시는 2쪽)
        if "cursor=" in url and so_fail["page2"]:
            so_fail["page2"] -= 1; raise OSError("tunnel down")
        page = SO_DAY[30:] if "cursor=c%2F2" in url else SO_DAY[:30]
        return json.dumps({"resultType": "SUCCESS", "success": {"items": [{"tacaItemId": i, "displayName": n, "displayPrice": pr, "isSoldOut": False} for i, n, pr in page],
                                                                "nextCursor": None if "cursor=" in url else "c/2", "hasNext": "cursor=" not in url}})
    if "/products/detail?tacaItemIds=" in url:
        ids = [int(x) for x in url.split("=")[1].split(",")]
        assert len(ids) <= 30 and len(set(ids)) == len(ids), ids
        return json.dumps({"resultType": "SUCCESS", "success": {"items": [{"tacaItemId": i, "displayName": f"상품{i}", "displayPrice": so_price.get(i, 6900), "isSoldOut": i in so_out}
                                                                          for i in ids if i != 999], "notFoundIds": [i for i in ids if i == 999]}})
    raise AssertionError(url)
def so_tg(method, **p):
    so_sent.append((method, p))
    if method == "editMessageText" and so_fail["edit"]:
        so_fail["edit"] -= 1; return None  # 429·지운 글 등
    return {"message_id": 700 + len(so_sent), "text": p.get("text", "")}
def so_run(at):
    so_calls.clear(); so_sent.clear(); time.time = lambda: T(at); out = io.StringIO()
    with contextlib.redirect_stdout(out): H.toss_soldout(seen)
    return out.getvalue()
H.http, H.tg = so_http, so_tg
JIN, BODY = "https://toss.shopping/_m/lGFCZsRq", "🛒 <b>[토스] CJ제일제당 쇠고기 진한다시 1kg (6,900원)</b>\n\n토스 하루특가 · 30일 내 최저가"
H.EVENTS = "ev_sold.json"
json.dump([{"at": "2026-10-11 11:50", "name": "CJ제일제당 쇠고기 진한다시 1kg", "button": "🛒 6,900원 구매하기", "url": JIN, "deal": True, "text": BODY},
           {"at": "2026-10-11 11:40", "name": "API 목록에 없는 상품", "button": "🛒 1,000원 구매하기", "url": "https://toss.shopping/_m/NoApi", "deal": True, "text": "🛒 없음"},
           {"at": "2026-10-11 11:30", "name": "쿠팡 예약", "button": "🛒 1원", "url": "https://link.coupang.com/a/x", "deal": True, "text": "쿠팡"},
           {"at": "2026-10-11 11:20", "name": "같은 링크 두 번", "button": "🛒 구매하러 가기", "url": "https://toss.shopping/_m/Twice", "deal": True, "text": "아침 글 (4,800원)"},
           {"at": "2026-10-11 11:52", "name": "같은 링크 두 번", "button": "🛒 4,500원 구매하기", "url": "https://toss.shopping/_m/Twice", "deal": True, "text": "점심 글 가격 내림"}], open(H.EVENTS, "w"))
seen = {}; time.time = lambda: T("2026-10-11 11:55"); H.events(seen)
mids = {p["text"].split("\n")[-1]: p["mid"] for p in json.load(open("posts.json")) if "mid" in p and p["t"] == "2026-10-11 11:55"}
mid, m_am, m_pm = mids["토스 하루특가 · 30일 내 최저가"], mids["아침 글 (4,800원)"], mids["점심 글 가격 내림"]
assert sorted(k for k in seen if k.startswith("sold_")) == sorted(f"sold_{m}" for m in (mid, m_am, m_pm, mids["🛒 없음"]))  # 진우 토스 예약만(쿠팡 X), 글마다 따로(같은 링크 두 번도)
assert seen[f"sold_{m_am}"]["body"] == "아침 글 (4,800원)" and seen[f"sold_{m_am}"]["p"] == 4800 and seen[f"sold_{m_pm}"]["p"] == 4500  # 버튼에 가격 없으면 본문 첫 'N원'
sv = seen; seen = {k: v for k, v in sv.items() if not k.startswith("sold_")}; so_run("2026-10-11 11:56")  # 배포 전에 나간 예약 글(지켜보기 없음): 링크가 오늘 예약·글 모두 1개인 것만 posts.json 글 번호로
assert sorted(k for k in seen if k.startswith("sold_")) == sorted(f"sold_{m}" for m in (mid, mids["🛒 없음"])); seen = sv  # 같은 링크 두 번은 어느 글인지 몰라서 X
assert so_run("2026-10-11 11:58") and so_calls[:2] == ["/products/today-deals?size=30", "/products/today-deals?size=30&cursor=c%2F2"] and len(so_calls) == 3, so_calls
assert not so_sent and seen["soldmap"]["d"] == "2026-10-11" and seen[f"sold_{mid}"]["it"][0][:5] == [950, "CJ제일제당 쇠고기 진한다시 1kg", 6900, 1, 0]
assert "| 진우 예약 id 3/4" in so_run("2026-10-11 12:12") and len(so_calls) == 1 and so_calls[0].startswith("/products/detail?") and not so_sent  # 목록은 2시간 안엔 다시 안 받음
so_out.update({950, 951}); log = so_run("2026-10-11 12:26")
ed = {p["message_id"]: p for m, p in so_sent if m == "editMessageText"}
assert set(ed) == {mid, m_am, m_pm} and "3 out" in log and not [m for m, p in so_sent if m == "sendMessage"]
assert ed[mid]["chat_id"] == H.CHANNEL and ed[mid]["parse_mode"] == "HTML" and ed[mid]["text"] == f"<i>{H.TOSS_NOTE}</i>\n\n⛔ <b>품절</b> — 밤 12시부터 다시 살 수 있어요\n\n{BODY}"  # 대가성 문구는 그대로 맨 앞, 그 바로 아래 품절 줄
assert ed[mid]["reply_markup"]["inline_keyboard"] == [[{"text": "품절 · 밤 12시 재오픈", "url": JIN}]]  # 진우 링크 그대로, 글자만
assert ed[m_am]["text"].endswith("아침 글 (4,800원)") and ed[m_pm]["text"].endswith("점심 글 가격 내림")  # 같은 링크 두 번 예약해도 글마다 자기 본문
assert not so_run("2026-10-11 12:40") and not so_calls and not so_sent  # 품절된 하루특가는 밤 12시 전엔 다시 안 봄(일 상한)
night = json.loads(json.dumps(seen))
so_run("2026-10-12 00:05"); assert so_calls == ["/products/detail?tacaItemIds=950,951"] and not so_sent, so_calls  # 밤 12시 지남: 아직 품절 -> 그대로
so_out.discard(950); so_price[950] = 9900; so_run("2026-10-12 00:19"); assert not so_sent and seen[f"sold_{mid}"]["it"][0][4] == 1  # 열렸지만 올린 가격(6,900원)보다 비쌈 = 특가 끝 -> 다시 열림 아님
so_price[950] = 6900; so_fail["edit"] = 1; so_run("2026-10-12 00:33")
assert [m for m, p in so_sent] == ["editMessageText"] and seen[f"sold_{mid}"]["it"][0][4] == 1  # 글 수정 실패(429 등) -> 상태 그대로, 답글 X -> 다음 실행에 다시
log = so_run("2026-10-12 00:47")
ed = [p for m, p in so_sent if m == "editMessageText"]; rp = [p for m, p in so_sent if m == "sendMessage"]
assert len(ed) == 1 and ed[0]["text"] == f"<i>{H.TOSS_NOTE}</i>\n\n{BODY}" and ed[0]["reply_markup"]["inline_keyboard"] == [[{"text": "🛒 6,900원 구매하기", "url": JIN}]]  # 품절 줄 지우고 원래대로
assert len(rp) == 1 and rp[0]["reply_parameters"] == {"message_id": mid} and rp[0]["chat_id"] == H.CHANNEL and "1 reopen" in log  # 그 글에 답글 = 알림(원글이 지워졌으면 안 올라감)
assert rp[0]["text"] == f"<i>{H.TOSS_NOTE}</i>\n\n🔔 <b>다시 열렸어요!</b> CJ제일제당 쇠고기 진한다시 1kg — 6,900원" and rp[0]["reply_markup"]["inline_keyboard"] == [[{"text": "🛒 6,900원 구매하기", "url": JIN}]]
assert f"sold_{mid}" not in seen and f"sold_{m_am}" in seen  # 다 열린 글은 그만 봄(토스 데이터 1일 이내)
so_run("2026-10-12 01:05"); ed = {p["message_id"]: p for m, p in so_sent if m == "editMessageText"}  # 1시 넘어도 안 열림(951) -> '특가 끝', 그만 봄(API 안 부름)
assert not so_calls and set(ed) == {m_am, m_pm} and ed[m_am]["text"].startswith(f"<i>{H.TOSS_NOTE}</i>\n\n⛔ <b>특가 끝</b> — 이 가격으로는 다시 안 열렸어요\n\n아침 글")
assert ed[m_am]["reply_markup"]["inline_keyboard"] == [[{"text": "특가 끝", "url": "https://toss.shopping/_m/Twice"}]] and not any(k.startswith("sold_") for k in seen)
seen = night; so_out.add(950); so_run("2026-10-12 01:10")  # 밤 12~1시 실행이 없었음 -> 바로 '끝'이 아니라 한 번은 확인
assert so_calls == ["/products/detail?tacaItemIds=950,951"] and not so_sent and f"sold_{mid}" in seen
so_run("2026-10-12 01:24"); assert not so_calls and len([1 for m, p in so_sent if m == "editMessageText"]) == 3 and not any(k.startswith("sold_") for k in seen)
# API 묶음 글(하루특가 13시 회차): 게시 때 상품 id 저장 -> 품절된 상품만 그 줄·그 번호 버튼, 다른 상품·링크는 그대로
seen, so_out = {}, set(); H.ai_pick = lambda prompt, lines: [{"i": 0, "score": 9, "comment": "가"}, {"i": 1, "score": 8, "comment": "나"}]
time.time = lambda: T("2026-10-11 13:10"); so_sent.clear(); H.toss_deals(seen)
(m, p), = so_sent; bid = 701; w = seen[f"sold_{bid}"]
assert w["k"] == "top" and [x[0] for x in w["it"]] == [901, 902] and [x[3] for x in w["it"]] == [1, 1] and p["text"].startswith(f"<i>{H.TOSS_NOTE}</i>")
so_fail["page2"] = 9; so_out.add(902); log = so_run("2026-10-11 13:24"); (m, e), = so_sent  # 진우 예약이 없으니 목록은 안 받음
assert m == "editMessageText" and e["message_id"] == bid and e["text"] == p["text"].replace("👉 나", "👉 나\n⛔ <b>품절</b> — 밤 12시부터 다시 살 수 있어요") and "/products/today-deals" not in str(so_calls)
assert e["reply_markup"]["inline_keyboard"] == [p["reply_markup"]["inline_keyboard"][0], [{"text": "2️⃣ 품절 · 밤 12시 재오픈", "url": "https://toss.shopping/_m/A902"}]]
seen[f"sold_{bid + 1}"] = H.sold_ev({"name": "CJ제일제당 쇠고기 진한다시 1kg", "button": "🛒 6,900원 구매하기", "url": JIN, "text": BODY}, "2026-10-11")
log = so_run("2026-10-11 13:38")  # 목록 2쪽이 실패해도(터널 끊김) 품절 확인은 계속, 받은 만큼 저장하고 2시간 뒤에 다시(하루 최대 3번)
assert so_calls == ["/products/today-deals?size=30", "/products/today-deals?size=30&cursor=c%2F2", "/products/detail?tacaItemIds=901"] and seen["soldmap"]["n"] == 1 and "toss soldout list" in log
so_run("2026-10-11 14:00"); assert so_calls == ["/products/detail?tacaItemIds=901"]
so_run("2026-10-11 15:40"); so_run("2026-10-11 17:41"); so_run("2026-10-11 19:42"); assert seen["soldmap"]["n"] == 3 and so_calls == ["/products/detail?tacaItemIds=901"]  # 3번 넘으면 그날은 그만
# 30개 넘으면 오래 안 본 것부터(상세 조회 한 번에 최대 30개), 조회 안 되는 상품(notFoundIds)은 2시간 뒤에, 하루특가 아닌 상품은 품절이어도 낮에 계속 봄
seen = {f"sold_{800 + j}": {"t": T("2026-10-11 10:00"), "d": "2026-10-11", "k": "top", "pre": "", "head": "H", "rows": [[f"n{5 * j + i}", f"https://toss.shopping/_m/R{5 * j + i}", ["💰 <b>100원</b>"]] for i in range(5)],
                               "it": [[1000 + 5 * j + i, f"n{5 * j + i}", 100, 0, 0, 0] for i in range(5)]} for j in range(7)}  # 베스트 묶음 7개 x 5 = 35개 + 조회 안 되는 상품 1개
seen["sold_807"] = {"t": T("2026-10-11 10:00"), "d": "2026-10-11", "k": "top", "pre": "", "head": "H", "rows": [["없어진 상품", "https://toss.shopping/_m/G", []]], "it": [[999, "없어진 상품", 100, 0, 0, 0]]}
so_price.update({1000 + i: 100 for i in range(35)})
so_run("2026-10-11 14:00"); a = [int(x) for x in so_calls[0].split("=")[1].split(",")]
lb = so_run("2026-10-11 14:14"); b = [int(x) for x in so_calls[0].split("=")[1].split(",")]
assert len(a) == len(b) == 30 and set(a) | set(b) == {1000 + i for i in range(35)} | {999} and not set(b[:6]) & set(a) and not so_sent and "1 notfound" in lb
for at in ("2026-10-11 14:28", "2026-10-11 14:42", "2026-10-11 14:56", "2026-10-11 15:10"):
    so_run(at); assert "999" not in so_calls[0]  # 조회 안 되는 상품은 2시간 동안 안 물음
so_run("2026-10-11 16:20"); so_run("2026-10-11 16:34"); assert "999" in so_calls[0] or "999" in str(so_calls)
so_out.add(1001); so_run("2026-10-11 16:48"); so_run("2026-10-11 17:02")
assert seen["sold_800"]["it"][1][4] == 1
so_out.discard(1001); so_price[1001] = 120; got = []  # 조금 비싸져서 다시 들어옴 -> 품절 줄은 지우되 '올린 가격 이하'가 아니라 답글은 안 함
for at in ("2026-10-11 17:16", "2026-10-11 17:30"):
    so_run(at); got += so_sent
assert seen["sold_800"]["it"][1][4] == 0 and not [1 for m, p in got if m == "sendMessage"] and [p["reply_markup"]["inline_keyboard"][1][0] for m, p in got if m == "editMessageText"] == [{"text": "2️⃣ n1", "url": "https://toss.shopping/_m/R1"}]
so_price[1001] = 100; got = []  # 품절 <-> 입고가 반복돼도 '다시 열렸어요' 답글은 상품당 하루 1번
for at, o in (("2026-10-11 17:44", 1), ("2026-10-11 17:58", 1), ("2026-10-11 18:12", 0), ("2026-10-11 18:26", 0), ("2026-10-11 18:40", 1), ("2026-10-11 18:54", 1), ("2026-10-11 19:08", 0), ("2026-10-11 19:22", 0)):
    (so_out.add if o else so_out.discard)(1001); so_run(at); got += so_sent
assert [p["text"].endswith("🔔 <b>다시 열렸어요!</b> n1 — 100원") for m, p in got if m == "sendMessage"] == [True] and seen["sold_800"]["it"][1][4] == 0
seen["sold_800"]["it"][1][4] = 1; t1 = H.sold_render(seen["sold_800"])
assert "n1</b></a>\n💰 <b>100원</b>\n⛔ <b>품절</b> — 다시 들어오면 답글로 알려드릴게요" in t1[0] and t1[1][1][0] == {"text": "2️⃣ 품절", "url": "https://toss.shopping/_m/R1"}
seen = {f"sold_{900 + j}": H.sold_ev({"name": f"n{j}", "button": "🛒 100원 구매하기", "url": f"https://toss.shopping/_m/E{j}", "text": f"글{j}"}, "2026-10-11") for j in range(10)}
for j in range(10): seen[f"sold_{900 + j}"]["it"] = [[1100 + j, f"n{j}", 100, 1, 0, 0]]
so_out.update(1100 + j for j in range(10)); so_run("2026-10-11 20:00"); n1 = len(so_sent); so_run("2026-10-11 20:14")  # 한꺼번에 10개 품절 -> 이번 실행 8개, 나머지 다음 실행(텔레그램 분당 제한)
assert n1 == H.SOLD_EDITS == 8 and len(so_sent) == 2 and all(w["it"][0][4] == 1 for w in seen.values())
so_fail["edit"] = 3; so_out.discard(1100); so_price[1100] = 100; seen["sold_900"]["d"] = "2026-10-10"  # 지운 글 등으로 3번 실패 -> 그만 봄(다음 날 지움)
for at in ("2026-10-11 00:05", "2026-10-11 00:19", "2026-10-11 00:33"): so_run(at)
assert seen["sold_900"].get("off") and seen["sold_900"]["it"][0][4] == 1 and not so_run("2026-10-11 00:47") and "sold_900" not in seen
H.HAS_TOSS = False; so_run("2026-10-11 15:38"); assert not so_calls and not so_sent; H.HAS_TOSS = True  # 토스 API 키 없으면 아무것도 안 함
assert "toss_relink, toss_picks, toss_soldout, toss_reopen, lambda s: digest" in inspect.getsource(H.main) and H.SOLD[1][1] == ("⛔ <b>품절</b> — 밤 12시부터 다시 살 수 있어요", "품절 · 밤 12시 재오픈")
open("posts.json", "w").write(pj3); H.EVENTS, H.http, H.tg, H.ai_pick, H.HAS_TOSS = ev3, ph3, tg6, pa3, False
if os.path.exists("toss.json"): os.remove("toss.json")
time.time = tt

# 5-3f) 봇 자동 글 회차 늘리기 + 몰림 방지 + 화장품 발굴(10/11 진우 '회차 늘리기, 너무 자주 올리면 역효과 — 적절하게', '화장품도 발굴'): 7일 표(README)에서 묶음 글 없는 11시(베스트)·19시(뷰티) 추가,
#       묶음 글(토스 회차·TOP5·모아보기)은 앞 묶음 글과 10분 이상 띄우고, 토스 회차는 최근 1시간 글 8개 이상이면 미룸(API도 안 부름), 화장품 딜은 어느 몰이든 1점 완화(효능 문구 금지는 그대로)
H.HAS_TOSS, ph5, tg7, pa5, pj5 = True, H.http, H.tg, H.ai_pick, open("posts.json").read()
c_calls, c_sent = [], []
def c_http(url, body=None, headers=None, method=None):
    if url == "https://oauth2.cert.toss.im/token":
        return json.dumps({"access_token": "TK", "expires_in": 31535999})
    c_calls.append(url.split("/openapi")[-1])
    if url.endswith("/links"):
        return json.dumps({"resultType": "SUCCESS", "success": {"shortUrl": f"https://toss.shopping/_m/C{body['tacaItemId']}"}})
    if url.endswith("/categories"):
        return json.dumps({"resultType": "SUCCESS", "success": {"categories": [{"categoryId": 400, "displayName": "뷰티"}, {"categoryId": 200, "displayName": "식품"}]}})
    if "/products/best-selling" in url or "/best-categories/400" in url:
        return json.dumps({"resultType": "SUCCESS", "success": {"items": [{"tacaItemId": 700 + k + ("400" in url) * 50, "displayName": f"상품C{k}", "displayPrice": 5000, "isSoldOut": False} for k in range(5)]}})
    raise AssertionError(url)
H.http, H.tg, H.ai_pick = c_http, (lambda method, **p: c_sent.append((method, p)) or {"message_id": 900 + len(c_sent)}), (lambda prompt, lines: [{"i": 0, "score": 8, "comment": "가"}])
json.dump([], open("posts.json", "w"))
seen = {"bundles": {"t": T("2026-10-12 11:02"), "ts": [T("2026-10-12 11:02")]}}  # 11:02에 다른 묶음 글이 나감
out = io.StringIO(); time.time = lambda: T("2026-10-12 11:05")
with contextlib.redirect_stdout(out): H.toss_deals(seen, True)
assert not c_calls and not c_sent and "toss_best 미룸" in out.getvalue() and "tossbest_20261012_11" not in seen  # 10분 안 -> API도 안 부르고 다음 실행에
time.time = lambda: T("2026-10-12 11:16"); H.toss_deals(seen, True)
assert [m for m, p in c_sent] == ["sendMessage"] and "tossbest_20261012_11" in seen and seen["bundles"]["ts"] == [T("2026-10-12 11:02"), T("2026-10-12 11:16")]  # 11시 새 회차
json.dump([{"t": "2026-10-12 13:%02d" % (10 + k), "text": "x", "url": "u"} for k in range(7)], open("posts.json", "w"))  # 시간당 상한: 최근 1시간 글(딜 + 묶음 글) 8개 이상이면 토스 회차 미룸
seen = {}; time.time = lambda: T("2026-10-12 14:05"); assert not H.busy(seen)  # 딜 7개 = 평소 수준 -> 그대로
seen = {"bundles": {"t": T("2026-10-12 13:20"), "ts": [T("2026-10-12 13:20")]}}; assert H.busy(seen) and not H.busy(seen, cap=False)  # 딜 7 + 묶음 1 = 8 -> 토스 회차는 미룸, TOP5·모아보기는 간격만 봄
c_calls.clear(); c_sent.clear(); out = io.StringIO()
with contextlib.redirect_stdout(out): H.toss_deals(seen, True)
assert not c_calls and not c_sent and "미룸" in out.getvalue()
time.time = lambda: T("2026-10-12 14:21"); assert not H.busy(seen)  # 1시간 지난 글은 안 셈
json.dump([{"t": "2026-10-12 11:%02d" % (10 + k), "text": f"🔥 [G마켓] 딜{k} (1원)", "url": f"https://g/{k}", "mid": 50 + k, "pop": 9 - k} for k in range(3)], open("posts.json", "w"))
seen, c_sent[:] = {"bundles": {"t": T("2026-10-12 12:01"), "ts": [T("2026-10-12 12:01")]}}, []; time.time = lambda: T("2026-10-12 12:05"); H.top_deals(seen); assert not c_sent and "top_20261012_12" not in seen  # TOP5도 10분 안 묶음 글이면 다음 실행에
seen, c_sent[:] = {}, []; time.time = lambda: T("2026-10-12 12:05"); H.top_deals(seen); H.toss_deals(seen, True)  # 12시: TOP5가 먼저 나가면 같은 실행의 베스트는 다음 실행으로(10/10·10/11 12시 두 글이 18초 간격이던 것)
assert len(c_sent) == 1 and "반응 좋은 딜 TOP3" in c_sent[0][1]["text"] and "tossbest_20261012_12" not in seen
time.time = lambda: T("2026-10-12 12:19"); H.toss_deals(seen, True); assert len(c_sent) == 2 and "tossbest_20261012_12" in seen and "많이 팔리는" in c_sent[1][1]["text"]
seen, c_sent[:] = {}, []; time.time = lambda: T("2026-10-12 19:10"); H.toss_deals(seen, "beauty")  # 19시 뷰티 저녁 회차
assert "tossbeauty_20261012_19" in seen and "💄 <b>토스 뷰티 베스트 중 살 만한 1개</b>" in c_sent[0][1]["text"]
seen = {"bundles": {"t": T("2026-10-12 21:01"), "ts": [T("2026-10-12 21:01")]}}; c_sent.clear(); time.time = lambda: T("2026-10-12 21:05")  # 모아보기도 10분 안 묶음 글이면 다음 실행에
H.digest(seen, [{"t": "2026-10-12 20:00", "text": "🔥 [G마켓] 딜 (1원)", "url": "https://g"}]); assert not c_sent and "digest_20261012" not in seen
assert H.earns("[11번가] 토리든 다이브인 세럼 50ml (19,900원)") and H.earns("[네이버] 라운드랩 독도 토너 500ml (15,900원)") and not H.earns("[11번가] 삼다수 2L 12병 (9,900원)") and H.earns("[쿠팡] 휴지")  # 화장품은 어느 몰이든 1점 완화
assert all("화장품 효능(미백·주름·탄력 개선 등) 언급 금지" in x for x in (H.DEAL_PROMPT, H.ADMIN_PROMPT, H.GOLD_PROMPT, H.BEST_PROMPT))  # 효능 문구 금지는 그대로(커뮤니티·하루특가 글에도)
open("posts.json", "w").write(pj5); H.http, H.tg, H.ai_pick, H.HAS_TOSS = ph5, tg7, pa5, False
if os.path.exists("toss.json"): os.remove("toss.json")
time.time = tt

# 5-3g) 토스 품절 -> 밤 12시 지나 다시 열리면 Threads에도(10/11 진우 '품절 풀리면 다시 쓰레드에 시간 맞춰서, 자정 + 아침 8시 둘 다'): 채널 답글은 그대로 + Threads 새 글(대가성 문구 맨 앞·상품명·지금 가격·진우 링크 그대로),
#       8~11시엔 같은 상품을 다시 확인해 아직 살 수 있으면 '아침 재알림'(다른 문구) 1번 더, 품절·비싸짐이면 안 올림. '하루특가·선착순'은 오늘 목록에 있을 때만, 쿠팡 비교 줄은 가격이 그대로일 때만.
#       재게시끼리 10분(실행당 1개)·1시간 3개·토스 묶음 글과 10분 -> 넘친 건 다음 실행에. 4279047은 첨부 없이 1번 더, 다른 오류는 예외(main이 알림)·같은 글 다시 안 올림
import urllib.error
H.E.update(TOSS_ACCESS_KEY="ak", TOSS_SECRET_KEY="sk", TOSS_PUBLISHER_ID="pub-1", THREADS_TOKEN="tk")
H.HAS_TOSS, ph6, tg8, sl6 = True, H.http, H.tg, H.time.sleep
ro_out, ro_price, ro_calls, ro_th, ro_sent, ro_fail = set(), {}, [], [], [], {"pub": None}
RO_DAY = [(950, "탑프룻 망고젤리, 망고맛, 320g, 3개", 8900), (951, "CJ제일제당 쇠고기 진한다시, 1kg, 1개", 6900), (960, "토스 하루특가 API 상품", 1000)]  # 바나나칩(952)은 오늘 목록에 없음
def ro_http(url, body=None, headers=None, method=None):
    if url == "https://oauth2.cert.toss.im/token":
        return json.dumps({"access_token": "TK", "expires_in": 31535999})
    if url.startswith(H.THREADS):
        ro_calls.append(url)
        if "/me?" in url: return '{"id": "me7"}'
        if "/me7/threads?" in url: ro_th.append(parse_qs(urlsplit(url).query)); return '{"id": "c"}'
        if "/threads_publish?" in url:
            if ro_fail["pub"] and (ro_fail["pub"][1] or "link_attachment" in ro_th[-1]):
                e = urllib.error.HTTPError(url, 400, "Bad Request", {}, None); e.body = ro_fail["pub"][0]; raise e
            return '{"id": "p"}'
    ro_calls.append(url.split("/openapi")[-1])
    if "/products/today-deals?size=30" in url:
        return json.dumps({"resultType": "SUCCESS", "success": {"items": [{"tacaItemId": i, "displayName": n, "displayPrice": p, "isSoldOut": False} for i, n, p in RO_DAY], "hasNext": False}})
    if "/products/detail?tacaItemIds=" in url:
        if ro_fail.get("detail"):
            ro_fail["detail"] -= 1; raise OSError("tunnel down")
        ids = [int(x) for x in url.split("=")[1].split(",")]
        return json.dumps({"resultType": "SUCCESS", "success": {"items": [{"tacaItemId": i, "displayName": f"상품{i}", "displayPrice": ro_price[i], "isSoldOut": i in ro_out} for i in ids], "notFoundIds": []}})
    raise AssertionError(url)
H.http, H.tg, H.time.sleep = ro_http, (lambda method, **p: ro_sent.append((method, p)) or {"message_id": 800 + len(ro_sent)}), lambda s: None
def ro_run(at, steps=("toss_soldout", "toss_reopen")):
    ro_calls.clear(); ro_th.clear(); ro_sent.clear(); time.time = lambda: T(at); out = io.StringIO()
    with contextlib.redirect_stdout(out):
        for s in steps: getattr(H, s)(seen)
    return out.getvalue()
MANGO, DASHI, BANANA = "https://toss.shopping/_m/3NnboSsc", "https://toss.shopping/_m/lGFCZsRq", "https://toss.shopping/_m/FCYKrPn4"
EVS = [(950, MANGO, 8900, "🔥 <b>[토스] 탑프룻 망고젤리 망고맛 320g 3개 (8,900원)</b>\n\n토스 하루특가 · ⭐ 4.7 (리뷰 4,193)\n💡 쿠팡 같은 상품(탑프루츠 주시 젤리 망고 320g 3개 10,700원)보다 1,800원 쌈\n⚠️ 확인할 점: 오늘 밤 12시까지"),
       (951, DASHI, 6900, "🛒 <b>[토스] CJ제일제당 쇠고기 진한다시 1kg (6,900원)</b>\n\n🤔 솔직히 특가로는 약한 제품 — 쿠팡 같은 상품(이츠웰(CJ) 쇠고기 진한다시 1kg)이 6,430원으로 470원 더 쌈\n토스 하루특가"),
       (952, BANANA, 10000, "🔥 <b>[토스] 사바나나 바나나칩 100g 5봉 (10,000원)</b>\n\n💡 단위가격: 100g당 2,000원 — 쿠팡 같은 상품 8봉(23,650원, 100g당 2,956원)보다 g당 32% 쌈")]
seen = {}
for j, (i, u, p, body) in enumerate(EVS):  # 어제(10/11) 진우 예약 글 3개 + API 하루특가 묶음 1개가 품절인 채로 밤 12시
    seen[f"sold_{101 + j}"] = {**H.sold_ev({"name": dict((a, b) for a, b, c in RO_DAY).get(i, "사바나나 바나나칩, 100g, 5봉"), "button": f"🛒 {p:,}원 구매하기", "url": u, "text": body}, "2026-10-11"), "it": [[i, "", p, 1, 1, 0]]}
    seen[f"sold_{101 + j}"]["it"][0][1] = seen[f"sold_{101 + j}"]["n"]
seen["sold_104"] = {"t": T("2026-10-11 13:10"), "d": "2026-10-11", "k": "top", "pre": f"<i>{H.TOSS_NOTE}</i>\n\n", "head": "⏰ <b>오늘의 토스 하루특가 TOP1</b>",
                    "rows": [["토스 하루특가 API 상품", "https://toss.shopping/_m/A960", ["💰 <b>1,000원</b>", "👉 가"]]], "it": [[960, "토스 하루특가 API 상품", 1000, 1, 1, 0]]}
ro_price.update({950: 8900, 951: 6500, 952: 10000, 960: 1000})  # 진한다시는 밤 12시에 더 싸게(6,900 -> 6,500원) 열림
log = ro_run("2026-10-12 00:05")
assert len([1 for m, p in ro_sent if m == "sendMessage"]) == 4 and len([1 for m, p in ro_sent if m == "editMessageText"]) == 4  # 채널: 답글·품절 줄 지우기는 지금 그대로
assert [e["id"] for e in seen["reopen"]["q"]] == [950, 951, 952, 960] and len(ro_th) == 1 and "toss reopen 밤" in log  # ① 자정 첫 실행: Threads 새 글 1개(나머지는 10분 간격으로)
assert seen["reopen"]["q"][1]["cmp"].startswith("🤔 솔직히 특가로는 약한 제품 — 쿠팡") and seen["reopen"]["q"][3]["cmp"] == ""  # 약한 딜 줄도(가격 그대로면 Threads에도 솔직하게), API 묶음 글은 비교 줄 없음
t0 = ro_th[0]["text"][0]
assert t0 == f"{H.TOSS_NOTE}\n\n🔔 다시 열렸어요 · 선착순\n🔥 탑프룻 망고젤리, 망고맛, 320g, 3개\n💰 8,900원 · 토스 하루특가(밤 12시까지)\n💡 쿠팡 같은 상품(탑프루츠 주시 젤리 망고 320g 3개 10,700원)보다 1,800원 쌈\n\n👉 {MANGO}\n📲 실시간 알림 t.me/hotdeal_pick", t0
assert ro_th[0]["link_attachment"] == [MANGO] and ro_th[0]["topic_tag"] == ["핫딜"] and len(t0) <= 500  # 진우 링크 그대로(미리보기도)
assert sum("/products/today-deals" in c for c in ro_calls) == 1  # 오늘 하루특가 목록(밤 12시 새 목록)은 1번만
assert not ro_run("2026-10-12 00:12") and not ro_th and not [c for c in ro_calls if "detail" in c and "952" in c]  # 10분 안 -> 다음 실행에(상세 조회도 안 함)
ro_fail["pub"] = ('{"error": {"message": "Fatal", "type": "OAuthException", "error_subcode": 4279047}}', False)  # 링크 미리보기 실패(4279047) -> 첨부 없이 1번 더
ro_run("2026-10-12 00:19"); ro_fail["pub"] = None
assert [q.get("link_attachment") for q in ro_th] == [[DASHI], None] and ro_th[0]["text"] == ro_th[1]["text"] and sum("threads_publish" in c for c in ro_calls) == 2
t1 = ro_th[1]["text"][0]  # 가격 바뀜(6,900 -> 6,500원) -> 지금 가격, 쿠팡 비교 줄(🤔) 빠짐, 약한 딜 아이콘 🛒 그대로
assert "🛒 CJ제일제당 쇠고기 진한다시, 1kg, 1개\n💰 6,500원 · 토스 하루특가(밤 12시까지)\n\n👉 " + DASHI in t1 and "쿠팡" not in t1 and "6,900" not in t1 and t1.startswith(H.TOSS_NOTE)
ro_run("2026-10-12 00:33"); t2 = ro_th[0]["text"][0]  # 오늘 하루특가 목록에 없음 -> '하루특가·선착순' 빠짐, 가격 그대로면 쿠팡 비교 줄은 있음
assert t2 == f"{H.TOSS_NOTE}\n\n🔔 다시 열렸어요\n🔥 사바나나 바나나칩, 100g, 5봉\n💰 10,000원\n💡 단위가격: 100g당 2,000원 — 쿠팡 같은 상품 8봉(23,650원, 100g당 2,956원)보다 g당 32% 쌈\n\n👉 {BANANA}\n📲 실시간 알림 t.me/hotdeal_pick", t2
assert not [c for c in ro_calls if "today-deals" in c]  # 목록에 없는 상품이어도 2시간 안엔 목록 다시 안 받음
assert not ro_run("2026-10-12 00:47") and not ro_th and not ro_calls  # 1시간 3개(00:05·00:19·00:33) -> 넘친 건 다음 실행에(API도 안 부름)
ro_run("2026-10-12 01:06"); t3 = ro_th[0]["text"][0]
assert "🔔 다시 열렸어요 · 선착순\n🔥 토스 하루특가 API 상품\n💰 1,000원 · 토스 하루특가(밤 12시까지)\n\n👉 https://toss.shopping/_m/A960" in t3  # API 묶음 글 상품 = 그 글의 쉐어링크, 쿠팡 비교 없음
assert not ro_run("2026-10-12 03:00") and not ro_th and not ro_calls  # 밤에 다 올렸으면 아침까지 조용
ro_fail["detail"] = 1; assert "toss reopen detail" in ro_run("2026-10-12 08:02", ("toss_reopen",)) and not ro_th and len(seen["reopen"]["q"]) == 4  # 상세 조회 실패(터널) -> 다음 실행에(Threads 실패 알림 아님)
ro_out.add(951); ro_price[952] = 12000  # 아침: 진한다시 다시 품절, 바나나칩은 올린 가격(10,000원)보다 비싸짐(특가 끝)
seen["bundles"] = {"t": T("2026-10-12 08:01"), "ts": [T("2026-10-12 08:01")]}  # 08:01에 토스 묶음 글(채널·Threads) -> 10분 띄움
assert not ro_run("2026-10-12 08:05", ("toss_reopen",)) and not ro_th
ro_run("2026-10-12 08:15", ("toss_reopen",)); t4 = ro_th[0]["text"][0]  # ② 8시 지나 첫 실행: 같은 상품 다시 확인 -> 아직 살 수 있으면 '아침 재알림'(밤 글과 다른 문구)
assert t4 == f"{H.TOSS_NOTE}\n\n☀️ 아침 재알림 — 밤사이 다시 열렸고 아직 살 수 있어요\n🔥 탑프룻 망고젤리, 망고맛, 320g, 3개\n💰 지금 8,900원 · 토스 하루특가(밤 12시까지)\n💡 쿠팡 같은 상품(탑프루츠 주시 젤리 망고 320g 3개 10,700원)보다 1,800원 쌈\n\n👉 {MANGO}\n📲 실시간 알림 t.me/hotdeal_pick", t4
assert t4 != t0 and [e["id"] for e in seen["reopen"]["q"]] == [960]  # 품절(진한다시)·비싸짐(바나나칩)은 아침 글 없이 끝
ro_run("2026-10-12 08:29", ("toss_reopen",)); assert len(ro_th) == 1 and ro_th[0]["text"][0].startswith(f"{H.TOSS_NOTE}\n\n☀️ 아침 재알림") and "A960" in ro_th[0]["text"][0] and not seen["reopen"]["q"]
assert not ro_run("2026-10-12 08:43", ("toss_reopen",)) and not ro_calls  # 다 올림 -> 아무것도 안 함
seen["reopen"]["q"] = [{"id": 950, "n": "n", "url": MANGO, "p0": 8900, "icon": "🔥", "cmp": "", "day": "2026-10-12", "st": 1}, {"id": 960, "n": "m", "url": "u", "p0": 1, "icon": "🔥", "cmp": "", "day": "2026-10-11", "st": 0}]
assert "버림" in ro_run("2026-10-12 11:05", ("toss_reopen",)) and not ro_th and not seen["reopen"]["q"]  # 아침 회차(8~11시)를 놓쳤거나 어제 것 -> 낮에 몰아 안 올리고 버림(토스 데이터 그날만)
seen["reopen"]["q"] = [{"id": 950, "n": "n", "url": MANGO, "p0": 8900, "icon": "🔥", "cmp": "", "day": "2026-10-13", "st": 0}]; ro_fail["pub"] = ('{"error": {"message": "expired"}}', True)
try:
    ro_run("2026-10-13 00:20", ("toss_reopen",)); raise AssertionError("다른 오류는 예외로 올라가야 함(main이 Threads 실패 알림)")
except urllib.error.HTTPError:
    pass
ro_fail["pub"] = None; assert len(ro_th) == 1 and seen["reopen"]["q"][0]["st"] == 1 and not ro_run("2026-10-13 00:40", ("toss_reopen",)) and not ro_th  # 먼저 표시 -> 밤 글 다시 안 올림(스팸 방지), 아침에 다시 확인
bw = {"t": T("2026-10-12 09:05"), "d": "2026-10-12", "k": "top", "pre": "", "head": "H", "rows": [["망고젤리", "https://toss.shopping/_m/BOT950", ["💰 <b>8,900원</b>"]]], "it": [[950, "탑프룻 망고젤리", 8900, 1, 1, 0]]}
ew = {**H.sold_ev({"name": "탑프룻 망고젤리, 망고맛, 320g, 3개", "button": "🛒 8,900원 구매하기", "url": MANGO, "text": EVS[0][3]}, "2026-10-12"), "it": [[950, "탑프룻 망고젤리, 망고맛, 320g, 3개", 8900, 1, 1, 0]]}
ro_out.clear(); ro_price[950] = 8900; seen = {"sold_201": bw, "sold_202": ew}; ro_run("2026-10-13 00:05", ("toss_soldout",))  # 같은 상품이 봇 묶음 글(먼저)과 진우 예약 글에 둘 다 -> Threads는 1번, 진우 링크·비교 줄로
(q,) = seen["reopen"]["q"]; assert q["url"] == MANGO and q["k"] == "ev" and q["cmp"].startswith("💡 쿠팡 같은 상품") and q["st"] == 0
WEAK = "🛒 <b>[토스] 생수 (9,900원)</b>\n\n🤔 솔직히 특가로는 약한 제품 — 오늘 오전엔 9,900원이었는데 18시엔 20,000원"
seen = {"sold_203": {**H.sold_ev({"name": "생수", "button": "🛒 9,900원 구매하기", "url": "https://toss.shopping/_m/W", "text": WEAK}, "2026-10-12"), "it": [[960, "생수", 9900, 1, 1, 0]]},
        "sold_204": {**H.sold_ev({"name": "휴지", "button": "🛒 1,000원 구매하기", "url": "https://toss.shopping/_m/V", "text": "🔥 x\n\n💡 오늘 14시 토스 베스트 휴지보다도 매당 쌈"}, "2026-10-12"), "it": [[951, "휴지", 6500, 1, 1, 0]]}}
ro_price[951] = 6500; ro_run("2026-10-13 00:05", ("toss_soldout",))  # '오늘·18시엔'처럼 날·시각이 든 비교 줄은 다음 날 글에선 틀림 -> 빼고, 약한 딜이면 표시만 남김
assert [(e["id"], e["cmp"]) for e in seen["reopen"]["q"]] == [(960, "🤔 솔직히 특가로는 약한 제품"), (951, "")]
ev4 = H.EVENTS; H.EVENTS = "ev_reopen.json"; json.dump([{"at": "2026-10-13 08:20", "name": "탑프룻 망고젤리, 망고맛, 320g, 3개", "url": MANGO, "text": "x"}], open(H.EVENTS, "w"))
seen = {"reopen": {"t": T("2026-10-13 00:05"), "ts": [], "q": [dict(q, st=0)]}}; ro_run("2026-10-13 00:20", ("toss_reopen",))
assert len(ro_th) == 1 and MANGO in ro_th[0]["text"][0] and "🔔 다시 열렸어요" in ro_th[0]["text"][0]  # 밤 글은 선착순이라 진우 예약(08:20)이 있어도 그대로
seen = {"reopen": {"t": T("2026-10-13 00:05"), "ts": [], "q": [dict(q, st=1), {"id": 960, "n": "토스 하루특가 API 상품", "url": "https://toss.shopping/_m/A960", "p0": 1000, "icon": "🔥", "cmp": "", "k": "top", "day": "2026-10-13", "st": 1}]}}
ro_price[960] = 1000; log = ro_run("2026-10-13 08:05", ("toss_reopen",))  # 진우가 오늘 같은 상품을 다시 예약 -> 아침 재알림은 진우 글이 대신(같은 상품 두 번 X), 다른 상품은 그대로
assert "진우 오늘 예약" in log and len(ro_th) == 1 and "A960" in ro_th[0]["text"][0] and not seen["reopen"]["q"]
H.EVENTS = ev4
sw = lambda d, it: {**H.sold_ev({"name": "n", "button": "🛒 1,000원 구매하기", "url": "https://toss.shopping/_m/Z", "text": "🔥 x"}, d), "it": [it]}
seen = {"sold_106": sw("2026-10-13", [960, "n", 1000, 0, 1, 0])}; ro_run("2026-10-13 15:00", ("toss_soldout",))  # 낮에 다시 들어온 베스트 상품 = 채널 답글만(Threads는 밤 12시 재오픈만)
assert [m for m, p in ro_sent] == ["editMessageText", "sendMessage"] and "reopen" not in seen
seen = {"sold_107": sw("2026-10-12", [960, "n", 1000, 1, 1, 0]), "sold_108": sw("2026-10-12", [960, "n", 1000, 1, 1, 0])}; ro_run("2026-10-13 00:05", ("toss_soldout",))
assert [e["id"] for e in seen["reopen"]["q"]] == [960]  # 같은 상품이 두 글에 있어도 Threads 줄은 1번
del H.E["THREADS_TOKEN"]; seen = {"sold_105": {**H.sold_ev({"name": "n", "button": "🛒 1,000원 구매하기", "url": "https://toss.shopping/_m/Z", "text": "🔥 x"}, "2026-10-12"), "it": [[960, "n", 1000, 1, 1, 0]]}}
ro_run("2026-10-13 00:05"); assert [m for m, p in ro_sent] == ["editMessageText", "sendMessage"] and "reopen" not in seen and not ro_th  # Threads 토큰 없으면 채널 답글만(줄 안 세움)
H.E["THREADS_TOKEN"] = "tk"; H.HAS_TOSS = False; seen = {"reopen": {"t": T("2026-10-13 00:00"), "q": [{"id": 950, "n": "n", "url": "u", "p0": 1, "icon": "🔥", "cmp": "", "day": "2026-10-13", "st": 0}], "ts": []}}
assert not ro_run("2026-10-13 00:10", ("toss_reopen",)) and not ro_calls; H.HAS_TOSS = True  # 토스 키 없으면 아무것도 안 함
assert "toss_soldout, toss_reopen, lambda s: digest" in inspect.getsource(H.main) and "(threads, threads_deals, toss_picks, toss_reopen, preview, ig_cards, ig_publish)" in inspect.getsource(H.main)  # Threads 실패 알림(하루 1번)에 포함
assert (H.TH_REOPEN_GAP, H.TH_REOPEN_HOUR, H.TH_REOPEN_AM) == (600, 3, (8, 11))
del H.E["THREADS_TOKEN"]; H.http, H.tg, H.time.sleep, H.HAS_TOSS = ph6, tg8, sl6, False
if os.path.exists("toss.json"): os.remove("toss.json")
time.time = tt

# 5-3h) 토스 '특가' 자동(10/11 진우 '특가 탭 추천 자동으로 찾아줘'·'뺀 것도 자동으로'): API엔 특가 탭·개당 수익·30일 최저가가 없음(문서 확인) ->
#       ① 이름 예약(events.json {"at","name","api": true}): 8시간 전부터 1일 목록(+ Claude가 고른 하위 카테고리 베스트)에서 이름 겹침 -> Claude 8점↑ -> 자동 발급, 못 찾거나 발급 막히면 진우에게 1번 요청,
#          예약 시각에 상세로 지금 가격·품절 재확인 -> 채널(대가성 문구 맨 앞·효능·쿠팡 비교 없음) + Threads, posts.json X, 품절 지켜보기·3일 중복·자동 회차에서 빠짐
#       ② 특가 회차(toss_deals "special", 8·22시 3시간 안): 1일 목록 중 할인 40%↑·리뷰 50개↑ -> 할인 높은 순 30개 상세로 재확인 -> Claude 7점↑ 중 점수 × 가격(수수료 8% = 개당 수익) 높은 순 3개
H.E.update(TOSS_ACCESS_KEY="ak", TOSS_SECRET_KEY="sk", TOSS_PUBLISHER_ID="pub-1", THREADS_TOKEN="tk")
H.HAS_TOSS, ph7, tg9, pa7, sl7, ev7, pj7 = True, H.http, H.tg, H.ai_pick, H.time.sleep, H.EVENTS, open("posts.json").read()
sp_calls, sp_sent, sp_th, sp_ai, sp_out, sp_fail, sp_det = [], [], [], [], set(), {"link": set(), "tg": 0, "net": 0}, {}
TREE = [{"categoryId": 400, "displayName": "뷰티", "children": [{"categoryId": 410, "displayName": "선케어"}, {"categoryId": 411, "displayName": "스킨케어", "children": [{"categoryId": 4111, "displayName": "패치"}]}]},
        {"categoryId": 200, "displayName": "식품", "children": [{"categoryId": 210, "displayName": "간편식"}]}]
it = lambda i, n, p, dr=10, rc=100, rs=4.7: {"tacaItemId": i, "displayName": n, "displayPrice": p, "discountRate": dr, "reviewScore": rs, "reviewCount": rc, "isSoldOut": i in sp_out}
LISTS = {"/products/best-selling?size=100": [it(501, "에이지랩 달팽이 뮤신 올인원 크림, 50g, 3개 + 선크림 증정", 19900, 62, 812), it(502, "특가 비싼 상품 전기요", 89000, 55, 300),
                                             it(503, "특가 싼 상품 휴지", 9900, 70, 900), it(504, "리뷰 적은 특가", 5000, 80, 10), it(505, "할인 적은 상품", 5000, 20, 900),
                                             it(507, "한경희 카본히터 Q1000 다른 모델", 39000, 10, 50), it(508, "특가 이미 올린 상품", 7000, 60, 500), it(510, "어제 하루특가 끝난 상품", 8000, 65, 300)],
         "/products/best-categories/400?size=100": [it(506, "특가 중간 상품 샴푸", 30000, 45, 120)], "/products/best-categories/200?size=100": [], "/products/best-categories/210?size=100": [],
         "/products/best-categories/410?size=100": [it(511, "에이지랩 스네일 뮤신 브라이트닝 선크림, 70ml, 4개", 15900, 50, 222)], "/products/best-categories/411?size=100": [],
         "/products/best-categories/4111?size=100": [it(512, "화이트벨라 마이크로 니들 패치, 12매, 1개", 9900, 30, 80)]}
DAY = [it(503, "특가 싼 상품 휴지", 9900, 70, 900), it(509, "미미네 오리지널 국물떡볶이, 570g, 10개", 21900, 30, 400)]  # 휴지는 오늘 하루특가에도, 떡볶이는 하루특가 목록에만
def sp_http(url, body=None, headers=None, method=None):
    if url == "https://oauth2.cert.toss.im/token":
        return json.dumps({"access_token": "TK", "expires_in": 31535999})
    if url.startswith(H.THREADS):
        if "/me?" in url: return '{"id": "me9"}'
        if "/me9/threads?" in url: sp_th.append(parse_qs(urlsplit(url).query)); return '{"id": "c"}'
        return '{"id": "p"}'
    path = url.split("/openapi")[-1]; sp_calls.append(path)
    ok = lambda x: json.dumps({"resultType": "SUCCESS", "success": x})
    if path == "/categories": return ok({"categories": TREE})
    if path.startswith("/products/today-deals"):  # 2쪽(커서): 떡볶이는 2쪽에만 = 1일 목록(1쪽)엔 없고 오늘 하루특가 전체에만
        return ok({"items": DAY[1:], "hasNext": False}) if "cursor=" in path else ok({"items": DAY[:1], "nextCursor": "p2", "hasNext": True})
    if path in LISTS: return ok({"items": LISTS[path]})
    if path.startswith("/products/detail?tacaItemIds="):
        ids = [int(x) for x in path.split("=")[1].split(",")]; assert len(ids) <= 30
        alls = {x["tacaItemId"]: x for l in list(LISTS.values()) + [DAY] for x in l}
        return ok({"items": [dict(alls[i], isSoldOut=i in sp_out, displayPrice=alls[i]["displayPrice"] - (1000 if i == 501 else 0), **sp_det.get(i, {})) for i in ids if i in alls], "notFoundIds": [i for i in ids if i not in alls]})
    if path == "/links":
        if body["tacaItemId"] in sp_fail["link"]: return json.dumps({"resultType": "FAIL", "error": {"reason": "발급 제한"}})
        if sp_fail["net"]: sp_fail["net"] -= 1; raise OSError("tunnel down")
        if sp_fail.get("deny"): sp_fail["deny"] -= 1; return json.dumps({"resultType": "FAIL", "error": {"errorCode": "ACCESS_DENIED", "reason": "IP"}})
        return ok({"shortUrl": f"https://toss.shopping/_m/P{body['tacaItemId']}"})
    raise AssertionError(url)
def sp_pick(prompt, lines):
    sp_ai.append((prompt, lines))
    if prompt.startswith("커뮤니티 핫딜 글 제목"):  # 같은 상품 확인: 에이지랩 크림·선크림만 같은 상품
        want = "올인원 크림" if "올인원 크림" in prompt else "브라이트닝 선크림" if "브라이트닝 선크림" in prompt else "니들 패치" if "니들 패치" in prompt else "국물떡볶이" if "국물떡볶이" in prompt else "없는"
        if "카본히터" in prompt:  # 비슷한 다른 모델(Q1000) = 6점 -> 같은 상품 아님, 같은 모델(Q2000)이면 9점
            return sorted([{"i": i, "score": 9 if "Q2000" in l else 6, "comment": "c"} for i, l in enumerate(lines) if "카본히터" in l], key=lambda p: -p["score"])[:1]
        return [{"i": i, "score": 9, "comment": "같음"} for i, l in enumerate(lines) if want in l][:1]
    if prompt.startswith("아래는 토스쇼핑 하위 카테고리"): return [{"i": i, "score": 8, "comment": "c"} for i, l in enumerate(lines) if ("> 패치" in l and "니들" in prompt) or ("선케어" in l and "선크림" in prompt)]
    if prompt.startswith("토스쇼핑 상품 1개야"): return [{"i": 0, "score": 8, "comment": "50g 3개 + 선크림 증정, 리뷰 812개"}]
    if prompt.startswith("토스쇼핑 특가 후보"):
        sc = {"특가 비싼 상품 전기요": 7, "특가 싼 상품 휴지": 9, "특가 중간 상품 샴푸": 8, "할인 적은 상품": 9, "리뷰 적은 특가": 9, "에이지랩": 6, "특가 이미 올린 상품": 9}
        return sorted([{"i": i, "score": v, "comment": "c" + str(i)} for i, l in enumerate(lines) for k, v in sc.items() if l.startswith(k)], key=lambda p: -p["score"])
    raise AssertionError(prompt[:30])
def sp_tg(method, **p):
    sp_sent.append((method, p))
    if method == "sendMessage" and p.get("chat_id") == H.CHANNEL and sp_fail["tg"]:
        sp_fail["tg"] -= 1; return None
    return {"message_id": 600 + len(sp_sent), "text": p.get("text", "")}
def sp_run(at, step=None):
    sp_calls.clear(); sp_sent.clear(); sp_th.clear(); sp_ai.clear(); time.time = lambda: T(at); out = io.StringIO()
    with contextlib.redirect_stdout(out): (step or H.toss_picks)(seen)
    return out.getvalue()
H.http, H.tg, H.ai_pick, H.time.sleep, H.EVENTS = sp_http, sp_tg, sp_pick, lambda s: None, "ev_picks.json"
json.dump([{"at": "2026-10-11 23:30", "name": "에이지랩 달팽이 뮤신 올인원 크림 50g 3개 + 선크림 증정", "api": True},
           {"at": "2026-10-11 23:40", "name": "에이지랩 스네일 뮤신 브라이트닝 선크림 70ml 4개", "api": True},
           {"at": "2026-10-11 23:50", "name": "한경희 2단 자동회전 나노 카본히터 Q2000", "api": True},
           {"at": "2026-10-12 07:30", "name": "화이트벨라 마이크로 니들 패치 12매", "api": True},
           {"at": "2026-10-11 23:55", "name": "미미네 오리지널 국물떡볶이 570g 10개", "api": True},
           {"at": "2026-10-11 23:20", "name": "케어존 립앤아이 리무버", "button": "🛒 10,500원 구매하기", "url": "https://toss.shopping/_m/LXEUUUvn", "deal": True, "text": "진우 예약"}], open(H.EVENTS, "w"))
json.dump([], open("posts.json", "w")); seen = {}
log = sp_run("2026-10-11 18:00")  # ① 8시간 전: 1일 목록에서 크림 찾고 자동 발급, 선크림·히터는 아직(처음엔 1일 목록만), 내일 07:30은 아직 안 봄
assert seen["pk_2026-10-11 23:30"]["id"] == 501 and seen["pk_2026-10-11 23:30"]["link"] == "https://toss.shopping/_m/P501" and "pk_2026-10-12 07:30" not in seen
assert seen["pk_2026-10-11 23:55"]["id"] == 509 and not seen["pk_2026-10-11 23:50"].get("id")  # 하루특가 목록(커서 전체)에만 있는 상품도 / 비슷한 다른 모델(6점)은 같은 상품 아님
assert not seen["pk_2026-10-11 23:40"].get("id") and not [m for m, p in sp_sent] and "-> 없음" in log and "/categories" in sp_calls and "/products/best-categories/410?size=100" not in sp_calls
assert not [c for c in sp_ai if "니들" in str(c)]  # 8시간 밖 예약은 Claude에도 안 물음
log = sp_run("2026-10-11 18:14")  # 못 찾은 예약 -> Claude가 고른 하위 카테고리(선케어) 베스트 더 받음 -> 선크림 찾음, 히터는 끝까지 없음 -> 진우에게 1번 요청
assert "/products/best-categories/410?size=100" in sp_calls and seen["pk_2026-10-11 23:40"]["id"] == 511 and seen["pickscan"]["plan"] == [410]
ask = [p["text"] for m, p in sp_sent if p["chat_id"] == H.ADMIN]
assert len(ask) == 1 and "23:50 '한경희 2단 자동회전 나노 카본히터 Q2000'" in ask[0] and "못 찾았어" in ask[0] and not [p for m, p in sp_sent if p["chat_id"] == H.CHANNEL]
sp_run("2026-10-11 18:28"); assert not sp_sent and not [c for c in sp_calls if "best-categories/41" in c]  # 다시 안 물음·하위 카테고리도 다 봄(하루 PICK_SCAN 안)
assert not [a for a, l in sp_ai if "카본히터" in a]  # 진우에게 요청한 상품은 그만 찾음(나중에 찾아 올리면 진우 링크 예약과 두 번)
LISTS["/products/best-selling?size=100"].append(it(520, "한경희 2단 자동회전 나노 카본히터, Q2000", 59000))  # 요청 뒤에 베스트에 들어와도(19시 새 베스트) 안 찾음 -> 진우 링크 예약만
sp_run("2026-10-11 19:05"); assert not seen["pk_2026-10-11 23:50"].get("id") and not [p for m, p in sp_sent if p["chat_id"] == H.CHANNEL]; LISTS["/products/best-selling?size=100"].pop()
sp_run("2026-10-11 23:20", H.events); assert [p["text"] for m, p in sp_sent] == [f"<i>{H.TOSS_NOTE}</i>\n\n진우 예약"]
sv9 = json.loads(json.dumps(seen)); sp_run("2026-10-11 23:36", H.events); assert not sp_sent; seen = sv9  # 23:30 api 행이 시각이 돼도 events()는 안 올림(url·text 없음 -> toss_picks가)  # events()는 api 행을 안 올림(진우 예약만)
log = sp_run("2026-10-11 23:33")  # ② 예약 시각: 상세로 지금 가격(1,000원 내림)·품절 재확인 -> 채널 + Threads
(m, p), = [(m, p) for m, p in sp_sent if p["chat_id"] == H.CHANNEL]
assert p["text"] == f"<i>{H.TOSS_NOTE}</i>\n\n🔥 <b>[토스] 에이지랩 달팽이 뮤신 올인원 크림, 50g, 3개 + 선크림 증정</b>\n\n💰 <b>18,900원</b> (62%↓) · ⭐ 4.7 (리뷰 812)\n👉 50g 3개 + 선크림 증정, 리뷰 812개", p["text"]
assert p["reply_markup"]["inline_keyboard"] == [[{"text": "🛒 18,900원 구매하기", "url": "https://toss.shopping/_m/P501"}]] and "쿠팡" not in p["text"]
assert len(sp_th) == 1 and sp_th[0]["text"][0].startswith(H.TOSS_NOTE + "\n\n🔥 에이지랩") and "🛒 https://toss.shopping/_m/P501" in sp_th[0]["text"][0] and sp_th[0]["link_attachment"] == ["https://toss.shopping/_m/P501"]
w = [v for k, v in seen.items() if k.startswith("sold_")][0]
assert w["k"] == "ev" and w["it"] == [[501, w["n"], 18900, 0, 0, 0]] and w["url"] == "https://toss.shopping/_m/P501" and "tb_501" in seen and seen["bundles"]["ts"]  # 품절 지켜보기·3일 중복·묶음 간격
assert [x["url"] for x in json.load(open("posts.json"))] == ["https://toss.shopping/_m/LXEUUUvn"] and seen["pk_2026-10-11 23:30"]["st"] == "done"  # 사이트·posts.json X(API 상품, 진우 예약 글만)
assert any("토스쇼핑 상품 1개야" in a for a, _ in sp_ai) and "효능" in H.PICK_PROMPT and "쿠팡 등 다른 쇼핑몰 가격 비교 언급 금지" in H.PICK_PROMPT  # 효능·쿠팡 비교 금지
sp_out.add(511); log = sp_run("2026-10-11 23:47")  # 품절이면 안 올림
assert not [p for m, p in sp_sent if p["chat_id"] == H.CHANNEL] and seen["pk_2026-10-11 23:40"]["st"] == "skip" and "품절" in log
assert seen["pk_2026-10-12 07:30"]["id"] == 512 and seen["pickscan"]["plan"] == [410, 4111] and "/products/best-categories/4111?size=100" in sp_calls  # 23:30에 8시간 안에 들어온 내일 예약 = 새 이름만 Claude에 물어 3단계 하위 카테고리까지
assert seen["pickscan"]["names"] == ["에이지랩 스네일 뮤신 브라이트닝 선크림 70ml 4개", "한경희 2단 자동회전 나노 카본히터 Q2000", "화이트벨라 마이크로 니들 패치 12매"]  # 이미 물은 이름은 다시 안 물음
sp_run("2026-10-12 00:01"); (p,) = [p for m, p in sp_sent if p["chat_id"] == H.CHANNEL]  # 못 찾은 히터는 안 올라감(진우에게 이미 요청), 23:55 떡볶이는 00:01 실행에
assert "국물떡볶이" in p["text"] and "토스 하루특가 · 밤 12시까지" in p["text"] and next(v for k, v in seen.items() if k == f"sold_{600 + sp_sent.index(('sendMessage', p)) + 1}")["it"][0][3] == 1  # 오늘 하루특가 목록에 있으면 표시·품절 땐 '밤 12시 재오픈'
seen = {}; json.dump([{"at": "2026-10-12 01:00", "name": "에이지랩 달팽이 뮤신 올인원 크림 50g 3개 + 선크림 증정", "api": True}], open(H.EVENTS, "w")); sp_fail["link"].add(501)
sp_run("2026-10-12 00:10"); ask = [p["text"] for m, p in sp_sent if p["chat_id"] == H.ADMIN]  # 찾았지만 발급이 막힌 상품 -> 진우에게 1번
assert len(ask) == 1 and "발급이 막힌" in ask[0] and seen["pk_2026-10-12 01:00"]["id"] == 501 and not seen["pk_2026-10-12 01:00"]["link"]
sp_fail["link"].clear(); seen = {}; sp_fail["tg"] = 1; sp_run("2026-10-12 01:05"); assert seen["pk_2026-10-12 01:00"]["st"] is None and "tb_501" not in seen  # 채널 실패 -> 다음 실행에 다시
sp_run("2026-10-12 01:19"); assert seen["pk_2026-10-12 01:00"]["st"] == "done" and len([p for m, p in sp_sent if p["chat_id"] == H.CHANNEL]) == 1
seen = {}; assert not sp_run("2026-10-12 04:30") and not sp_sent and not sp_calls  # 예약 3시간 지남 -> 안 올림
seen = {"pk_2026-10-11 01:00": {"t": T("2026-10-11 00:00"), "id": 1, "n": "x"}, "pk_2026-10-11 05:00": {"t": T("2026-10-11 00:00"), "id": 2, "n": "y"}}; sp_run("2026-10-12 04:30")
assert list(seen) == ["pk_2026-10-11 05:00"]  # 이름 예약 기록(토스 상품명·id)은 1일 지나면 지움
def sp_down(url, *a, **k):
    if "/openapi/" in url: raise OSError("tunnel down")
    return sp_http(url, *a, **k)
H.http = sp_down; seen = {}; assert "toss pick list OSError" in sp_run("2026-10-12 00:10") and not sp_sent and seen == {}; H.http = sp_http  # 터널 끊김 -> 예외 없이(Threads 실패 알림 X) 다음 실행에
seen = {}; sp_fail["net"] = 1; sp_run("2026-10-12 00:10"); assert not seen["pk_2026-10-12 01:00"].get("id") and not sp_sent  # 발급 때 터널 끊김 = 막힌 상품 아님 -> 진우에게 안 물음, 다음 실행에 다시
sp_run("2026-10-12 00:24"); assert seen["pk_2026-10-12 01:00"]["link"] == "https://toss.shopping/_m/P501"
seen = {}; sp_fail["deny"] = 1; sp_run("2026-10-12 00:10"); assert not seen["pk_2026-10-12 01:00"].get("id") and not sp_sent  # 터널 실패로 직접 호출 = ACCESS_DENIED -> 막힌 상품 아님(진우에게 안 물음)
sp_run("2026-10-12 00:24"); assert seen["pk_2026-10-12 01:00"]["link"] == "https://toss.shopping/_m/P501"
seen["tb_501"] = {"t": T("2026-10-12 00:30"), "n": "x"}; sp_run("2026-10-12 01:05"); assert seen["pk_2026-10-12 01:00"]["st"] == "skip" and not [p for m, p in sp_sent if p["chat_id"] == H.CHANNEL]  # 오늘 이미 나간 상품(특가 회차 등) -> 같은 날 두 번 X
seen = {"pk_2026-10-12 01:00": {"t": T("2026-10-12 00:00"), "ids": [501], "n0": "옛 이름", "id": 501, "n": "x", "link": "L"}}; sp_run("2026-10-12 00:10")
assert seen["pk_2026-10-12 01:00"]["n0"] == "에이지랩 달팽이 뮤신 올인원 크림 50g 3개 + 선크림 증정" and seen["pk_2026-10-12 01:00"]["link"] == "https://toss.shopping/_m/P501"  # 같은 시각 행 이름이 바뀌면 처음부터
json.dump([{"at": "2026-10-12 01:00", "name": "에이지랩 달팽이 뮤신 올인원 크림 50g 3개 + 선크림 증정", "api": True, "url": "https://toss.shopping/_m/Jin", "button": "🛒 구매", "text": "진우 글"}], open(H.EVENTS, "w"))
seen = {}; sp_run("2026-10-12 01:05"); assert not sp_calls and not sp_sent  # api 표시가 남아 있어도 url이 있으면 진우 예약 -> toss_picks는 안 건드림
sp_run("2026-10-12 01:05", H.events); assert [p["reply_markup"]["inline_keyboard"][0][0]["url"] for m, p in sp_sent] == ["https://toss.shopping/_m/Jin"]  # events()가 진우 링크로
json.dump([{"at": "2026-10-12 01:00", "name": "에이지랩 달팽이 뮤신 올인원 크림 50g 3개 + 선크림 증정", "url": "https://toss.shopping/_m/Jin", "button": "🛒", "text": "진우", "name2": 1}], open(H.EVENTS, "w"))
seen = {}; sp_run("2026-10-12 00:10"); assert not sp_calls and not sp_sent  # 진우 링크로 바꾼 행(api 없음) -> toss_picks는 아무것도 안 함
H.HAS_TOSS = False; json.dump([{"at": "2026-10-12 01:00", "name": "x", "api": True}], open(H.EVENTS, "w")); sp_run("2026-10-12 00:10"); assert not sp_calls; H.HAS_TOSS = True
# ② 특가 회차: 8시(3시간 안)·22시, 할인 40%↑·리뷰 50개↑·3일 안 X·오늘 이름 예약 X -> 상세 재확인 -> Claude 7점↑ 중 점수 × 가격 높은 순 3개
json.dump([{"at": "2026-10-12 12:30", "name": "샴푸(진우가 쓴 다른 이름)", "api": True}], open(H.EVENTS, "w"))  # 오늘 이름 예약으로 찾은 상품 = 이름이 달라도 id로 자동 회차에서 뺌
sp_det[510] = {"discountRate": 5}  # 1일 된 목록엔 65%였지만 지금은 하루특가가 끝나 5% -> 상세 값으로 다시 거름
seen = {"tb_508": {"t": T("2026-10-12 07:00"), "n": "x"}, "pk_2026-10-12 12:30": {"t": T("2026-10-12 07:00"), "id": 506, "n": "특가 중간 상품 샴푸"}}; log = sp_run("2026-10-12 08:05", lambda s: H.toss_deals(s, "special"))
det = [c for c in sp_calls if c.startswith("/products/detail")]
assert len(det) == 1 and set(det[0].split("=")[1].split(",")) == {"501", "502", "503", "506", "510"}, det  # 리뷰 적은 것·할인 적은 것·3일 안에 올린 것(508) X(이름 예약 상품은 상세 뒤 후보에서)
(m, p), = [(m, p) for m, p in sp_sent if p["chat_id"] == H.CHANNEL]
assert p["text"].startswith(f"<i>{H.TOSS_NOTE}</i>\n\n🔥 <b>토스 특가 중 살 만한 2개</b>") and "샴푸" not in p["text"] and "toss_special 3 items 2 picks 2 links" in log, log
assert p["text"].index("전기요") < p["text"].index("휴지")  # 7점 × 89,000원 > 9점 × 9,900원(개당 수익 = 가격 × 8%)
assert "휴지</b></a>\n⏰ 토스 하루특가 · 밤 12시까지\n💰" in p["text"] and "전기요</b></a>\n💰" in p["text"]  # 오늘 하루특가 상품만 '밤 12시까지'
assert "끝난 상품" not in str(sp_ai) and not [a for a, l in sp_ai if H.TOSS_EASE in a]  # 끝난 하루특가 X · 쿠팡 언급 있는 TOSS_EASE X(진우 '쿠팡 안 씀')
w = next(v for k, v in seen.items() if k.startswith("sold_") and v["k"] == "top")
assert [x[0] for x in w["it"]] == [502, 503] and [x[3] for x in w["it"]] == [0, 1] and "tossspecial_20261012_8" in seen  # 하루특가 목록에 있는 휴지만 품절 땐 '밤 12시 재오픈'
assert len(sp_th) == 1 and sp_th[0]["text"][0].startswith(H.TOSS_NOTE + "\n\n🔥 토스 특가 중 살 만한 2개") and "휴지 — 9,900원 (하루특가·밤 12시까지)" in sp_th[0]["text"][0] and "전기요 — 89,000원\n" in sp_th[0]["text"][0] and "샴푸" not in str(sp_ai)  # Threads도, 이름 예약 상품은 Claude 후보에도 없음
seen = {}; assert not sp_run("2026-10-12 11:05", lambda s: H.toss_deals(s, "special")) and not sp_calls  # 8시 회차는 3시간 안에만(놓치면 낮에 몰아 안 올림)
seen = {"bundles": {"t": T("2026-10-12 22:01"), "ts": [T("2026-10-12 22:01")]}}; assert "toss_special 미룸" in sp_run("2026-10-12 22:05", lambda s: H.toss_deals(s, "special")) and not sp_calls
seen = {"tb_501": 1, "tb_502": 1, "tb_503": 1, "tb_506": 1, "tb_508": 1, "tb_510": 1}; sp_run("2026-10-12 22:20", lambda s: H.toss_deals(s, "special")); assert "tossspecial_20261012_22" in seen and not sp_sent and not [c for c in sp_calls if "detail" in c]  # 후보 0 -> 회차 끝
seen = {"tossget_cat": {"t": T("2026-10-12 10:00"), "d": "20261012"}, "tosscache": {"t": 0, "items": [[1, "옛 목록", 100, T("2026-10-12 10:00")]]}}; time.time = lambda: T("2026-10-12 10:30"); sp_calls.clear(); H.toss_pool(seen)
assert "/categories" in sp_calls and seen["tossget_cat"]["v"] == 2 and [x for x in seen["tosscache"]["items"] if x[0] == 503][0][4:] == [70, 4.7, 900]  # 예전(할인율·리뷰 없는) 목록이면 1번 다시 받음
sp_calls.clear(); H.toss_pool(seen); assert "/categories" not in sp_calls  # 그다음부터는 하루 1번 그대로
seen = {}; time.time = lambda: T("2026-10-12 10:00"); sp_ai.clear(); H.pick_scan(seen, ["에이지랩 스네일 뮤신 브라이트닝 선크림"]); H.pick_scan(seen, ["에이지랩 스네일 뮤신 브라이트닝 선크림"])
assert len([a for a, l in sp_ai if a.startswith("아래는")]) == 1 and seen["pickscan"]["names"] == ["에이지랩 스네일 뮤신 브라이트닝 선크림"]  # 이미 물은 이름은 Claude에 다시 안 물음
ps9 = H.PICK_SCAN; H.PICK_SCAN = 1; seen = {}; time.time = lambda: T("2026-10-12 10:00"); H.pick_scan(seen, ["에이지랩 스네일 뮤신 브라이트닝 선크림", "화이트벨라 마이크로 니들 패치"])
assert len(seen["pickscan"]["plan"]) == 1 and len(seen["pickscan"]["done"]) == 1  # 하위 카테고리는 하루 PICK_SCAN개까지(일 상한)
assert not H.pick_scan(seen, ["새 상품 이름"]) and "새 상품 이름" not in seen["pickscan"]["names"]  # 상한이 차서 못 고른 이름 -> False(진우에게 아직 안 물음)
time.time = lambda: T("2026-10-13 00:10"); assert H.pick_scan(seen, ["에이지랩 스네일 뮤신 브라이트닝 선크림"]) is not None and seen["pickscan"]["d"] == "20261013"; H.PICK_SCAN = ps9  # 밤 12시(KST)에 상한 새로
assert 'lambda s: toss_deals(s, "special"), toss_relink, toss_picks, toss_soldout' in inspect.getsource(H.main) and H.TOSS_SPECIAL_HOURS == (8, 22) and "효능" in H.SPECIAL_PROMPT and "쿠팡 등 다른 쇼핑몰 가격 비교 언급 금지" in H.SPECIAL_PROMPT
del H.E["THREADS_TOKEN"]; open("posts.json", "w").write(pj7); H.http, H.tg, H.ai_pick, H.time.sleep, H.EVENTS, H.HAS_TOSS = ph7, tg9, pa7, sl7, ev7, False
if os.path.exists("toss.json"): os.remove("toss.json")
time.time = tt

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
hg = S.grid_item(0, {**posts[0], "hot": "뽐뿌 추천 5"})  # 커뮤니티 인기 딜 = 사이트 칸에도 배지(10/11~ 배지 줄 — 몰·시각 줄은 한 줄로), '반응 좋은 딜' 칸(rx)에선 겹쳐서 뺌
assert "🏆" not in grid and '<div class="s">쿠팡 · ' in hg and '<div class="bd"><b class="b4">🏆 인기</b></div>' in hg and hg.index('class="bd"') < hg.index("<h3>") and "🏆" not in S.grid_item(0, {**posts[0], "hot": "x"}, True)
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
os.path.exists("docs/cards/2026-10-09.json") and os.remove("docs/cards/2026-10-09.json")  # 실제 날짜가 10/9면 앞 테스트(모아보기 카드)가 남긴 순서 파일과 겹침
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
assert idx.split('id="today"')[1].split("</section>")[0].count('class="pick"') == 5 == S.CARD_N  # 맨 위 카드 딜은 카드에 든 5개만(그날 딜 8개 — 카드·캡션·사이트 번호 같게, 10/11)
json.dump([6, 2, 1], open("docs5/cards/2026-10-09.json", "w")); S.build(g, "docs5")  # 카드 순서 파일이 있으면 그 순서·개수 그대로
top5 = open("docs5/index.html").read().split('id="today"')[1].split("</section>")[0]
assert top5.count('class="pick"') == 3 and top5.index("<b>01</b><span>[G마켓] 추가딜1") < top5.index("<b>02</b><span>[G마켓] 주소없는딜") < top5.index("<b>03</b><span>[뽐뿌몰] 라면")
os.remove("docs5/cards/2026-10-09.json"); S.build(g, "docs5")
bar = idx.split('<nav class="bar"')[1].split("</nav>")[0]
assert re.findall(r'<a href="([^"]*)"><svg viewBox="0 0 24 24" aria-hidden="true">.*?</svg>([^<]+)</a>', bar) == [("#today", "카드"), ("#toss", "토스"), ("#days", "전체")]  # 반응 딜·품목 딜 없음 -> 그 버튼 없음, 홈 안에선 #칸만, 아이콘 = 선 아이콘(이모지 X)
assert "fbclid" in S.PANE_JS and "ig&&t&&t.parentNode||ps[0]" in S.PANE_JS  # 인스타·Threads에서 오면 첫 칸 = 카드 딜(캡션 '맨 위에서 카드 번호')
assert '<nav class="bar" aria-label="바로가기"><a href="https://hotdealpick.kr/#today">' in allp  # 지난 딜 전체에선 홈 칸으로
assert idx.count('<div class="pane">') == 3 and idx.index('<div class="pane"><section class="card" id="today"') < idx.index('<div class="pane"><div id="days">') < idx.index('<nav class="bar"') < idx.index("<script>")
assert 'href="https://hotdealpick.kr/all.html">지난 딜 전체 보기' in idx.split('id="days"')[1]  # 날짜 탭 대신 '📅 전체' 칸 끝에 지난 딜 링크
d0 = idx.split('id="d0"')[1].split("</section>")[0]
assert "10월 9일 딜 8개" in d0 and d0.count('class="g"') == 8 and "그제딜" not in idx and 'id="d1"' in idx and "어제딜" in idx and 'id="d2"' not in idx
assert d0.index("생수 40병") < d0.index("추가딜4") < d0.index("추가딜0") < d0.index("라면")  # 토스(제휴)는 오래됐어도 맨 앞, 나머지는 최신 순
assert '<div class="s">토스쇼핑 · 08:00</div>' in d0 and '<div class="pr">5,900원</div>' in d0 and '<div class="u">병당 148원</div>' in d0 and 'href="https://toss.im/_m/w" rel="nofollow sponsored noopener"' in d0
assert 'class="o" href="https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&amp;no=9"' in d0 and '🔎 같은 상품 찾기' in d0 and 'aria-label="라면 원글에서 구매 링크 보기"' in d0
assert f'class="o" href="https://hotdealpick.kr/p/2.html" aria-label="주소없는딜 자세히 보기">자세히 →' in d0
assert all(f"{w}" in allp for w in ("10월 9일 딜 8개", "10월 8일 딜 1개", "10월 7일 딜 1개")) and 'id="today"' not in allp
# 6-5) 토스 칸(10/9 진우 '쿠팡·토스 주력'): 홈 맨 위 카드 딜 다음 = 최근 2일 커뮤니티 딜 중 토스 쉐어링크 딜(최신 6개) + 텔레그램 토스 추천 버튼,
#      탭 맨 앞 '💙 토스'. 토스 API 상품은 사이트에 안 올림(승인 범위 = 채널·Threads) -> 버튼은 채널 웹 보기로. 지난 딜 전체엔 토스 칸 없음
tsec = idx.split('id="toss"')[1].split("</section>")[0]
assert idx.index('id="today"') < idx.index('id="toss"') < idx.index('id="days"') and "💙 토스 딜 1개" in tsec and tsec.count('class="g"') == 1 and "생수 40병" in tsec
assert f'href="{S.CHANNEL_WEB}"' in tsec and S.CHANNEL_WEB == "https://t.me/s/hotdeal_pick" and 'id="toss"' not in allp
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

# 6-6) 홈 '🏆 지금 반응 좋은 딜'(최근 2일, pop 높은 6개, 2개 이상일 때만, 맨 위) + 품목별 칸 '🧻 생필품'·'💄 화장품'(10/9 진우: 최근 3일, 제목 키워드, 최신 6개, 없으면 칸·탭 없음)
hp = [{"t": "2026-10-06 10:00", "text": "🔥 [G마켓] 오래된 휴지 (9,900원)", "url": "https://g4", "s": 6, "pop": 99},  # posts.json = 게시 순
      {"t": "2026-10-07 10:00", "text": "🔥 [G마켓] 퍼실 세제 2L (9,900원)", "url": "https://g3", "s": 6, "pop": 77},
      {"t": "2026-10-08 10:00", "text": "🔥 [G마켓] 뷰카 샴푸 3개 (12,900원)", "url": "https://g2", "s": 6},
      {"t": "2026-10-09 10:00", "text": "🔥 [G마켓] 크린랩 위생백 (3,000원)", "url": "https://g1", "s": 6, "pop": 12.5, "hot": "뽐뿌 추천 3"},
      {"t": "2026-10-09 11:00", "text": "🔥 [네이버] 퓨어그램 폼클렌징 120ml (2,990원)", "url": "https://n1", "s": 6, "pop": 40, "vpm": 25.0, "rec": 3},
      {"t": "2026-10-09 12:00", "text": "🔥 [쿠팡] 아이스크림 24개 (9,900원)", "url": "https://link.coupang.com/a/i", "s": 7},  # '크림'이지만 음식
      {"t": "2026-10-09 13:00", "text": "🔥 [옥션] 마스크팩 30매 (9,900원)", "url": "https://a1", "s": 6},
      {"t": "2026-10-09 13:30", "text": "🔥 [옥션] KF94 마스크 100매 (7,700원)", "url": "https://a2", "s": 6},
      {"t": "2026-10-09 14:00", "text": "📋 오늘의 딜 모아보기 휴지", "url": None}]
S.build(hp, "docs7"); i7, a7 = open("docs7/index.html").read(), open("docs7/all.html").read()
hot7, life7, beauty7 = (i7.split(f'id="{k}"')[1].split("</section>")[0] for k in ("hot", "life", "beauty"))
assert i7.index('id="hot"') < i7.index('id="toss"') < i7.index('id="life"') < i7.index('id="beauty"') < i7.index('id="d0"') < i7.index('<nav class="bar"')
assert hot7.count('class="g"') == 2 and hot7.index("폼클렌징") < hot7.index("위생백") and 'class="b4"' not in hot7 and '<b class="b4">🏆 인기</b>' in life7  # 세제(3일 전)·휴지(4일 전) 제외, 🏆 배지는 인기 칸에선 빼고(제목이 이미 반응 좋은 딜) 다른 칸에선 보임
assert '<div class="rx">👀 분당 25회 · 추천 3</div>' in hot7 and '<div class="rx">👀 반응 12.5</div>' in hot7 and 'class="rx"' not in i7.split('id="hot"')[1].split("</section>", 1)[1]  # 반응 수치는 인기 칸에만(10/9 진우 '반응 수치 확인')
assert life7.count('class="g"') == 4 and life7.index("KF94") < life7.index("위생백") < life7.index("샴푸") < life7.index("세제") and "마스크팩" not in life7 and "휴지" not in life7
assert beauty7.count('class="g"') == 2 and beauty7.index("마스크팩") < beauty7.index("폼클렌징") and "아이스크림" not in beauty7 and "🧻 생필품</h2>" in life7
assert re.findall(r'<a href="([^"]*)"><svg[^>]*>.*?</svg>([^<]+)</a>', i7.split('<nav class="bar"')[1].split("</nav>")[0]) == [("#hot", "인기"), ("#toss", "토스"), ("#life", "생필품"), ("#beauty", "화장품"), ("#days", "전체")]
assert i7.count('<div class="pane">') == 5 and i7.index('<div class="pane"><section class="day" id="hot"') < i7.index('<div class="pane"><section class="day" id="toss"')  # 첫 칸(인기) = 처음 보이는 칸(10/9 진우 '한 칸씩만')
assert all(i7.count(f'#{k}"') == 1 and i7.index(f'<div class="pane"><section class="day" id="{k}"') < i7.index('<nav class="bar"') for k in ("hot", "toss", "life", "beauty"))  # 바 버튼마다 칸이 있음
assert 'id="life"' not in a7 and 'id="hot"' not in a7 and "#life" in a7 and S.PANE_JS not in a7 and 'class="pane"' not in a7  # 지난 딜 전체엔 칸 없음(바는 홈 칸으로)
# 6-7) 찜(10/9 진우 '핫딜도 장바구니처럼'): 격자 카드마다 하트(번호·이름), 맨 위 '찜' -> 홈 숨은 '찜한 딜' 칸(바에는 없음), 저장은 브라우저(JS)
assert hot7.count('<button class="like" type="button" data-i="') == 2 and 'data-i="4" aria-pressed="false" aria-label="퓨어그램 폼클렌징 120ml 찜"' in hot7
assert i7.count('<div class="pane" hidden><section class="day" id="saved"') == 1 and 'id="savedg"' in i7 and "#saved" not in i7.split('<nav class="bar"')[1].split("</nav>")[0]
assert all(S.LIKE_JS in x and f'<a class="lk" href="{S.BASE}#saved"' in x for x in (i7, a7)) and "localStorage" in S.LIKE_JS and ".slice(0,50)" in S.LIKE_JS
# 6-8) 검색·칩·배지·정품·브랜드 칸(10/10 진우 'UI 편하게', '브랜딩 파워 있는 제품도 꼭, 정품도')
td = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600))
bp = [{"t": td + " 20:00", "text": "🔥 [토스] 설화수 자음 2종 세트 (114,000원/무료)\n\n본사 정품", "url": "https://toss.shopping/_m/a", "tag": "정품"},
      {"t": td + " 20:10", "text": "🔥 [토스] 땡큐파머스 구운란 대란 30구 (10,490원)\n\n⚠️ 확인할 점: 오늘 밤 12시까지 토스 선착순특가", "url": "https://toss.shopping/_m/b"},
      {"t": td + " 20:20", "text": "🛒 [토스] 설화수 탄력 3종 (146,070원)\n\n🤔 솔직히 특가로는 약한 제품 — 본사 정품보다는 쌈", "url": "https://toss.shopping/_m/c"},
      {"t": td + " 20:30", "text": "🔥 [쿠팡] 코멧 화장지 30롤 (10,990원)", "url": "https://link.coupang.com/a/d"},
      {"t": "2020-01-01 20:40", "text": "🔥 [토스] 구운란 30구 (9,000원)\n\n오늘 밤 12시까지 선착순", "url": "https://toss.shopping/_m/e"},
      {"t": td + " 20:50", "text": "🔥 [쿠팡] 피죤 써니가든 6L (16,940원)", "url": "https://link.coupang.com/a/f", "tag": "정품"}]  # 브랜드 목록에 없어도 정품 표시면 칸에
assert S.keys(bp[0]) == "토스 브랜드" and S.keys(bp[1]) == "토스 식품 마감" and S.keys(bp[3]) == "쿠팡 생필품" and "마감" not in S.keys(bp[4])  # 마감 = 오늘 올린 선착순만
assert [c for c, _ in S.badges(bp[0])] == ["b1"] and [c for c, _ in S.badges(bp[2])] == ["b3"] and S.badges(bp[3]) == [] and S.badges(bp[4]) == []  # '본사 정품' 글자만으로는 정품 배지 X(약한 딜 글)
S.build(bp, "docs8"); i8, a8 = open("docs8/index.html").read(), open("docs8/all.html").read()
br8 = i8.split('id="brand"')[1].split("</section>")[0]
assert br8.count('class="g"') == 3 and br8.index("피죤") < br8.index("탄력") < br8.index("자음") and S.keys(bp[5]) == "쿠팡 생필품 브랜드" and "구운란" not in br8 and '<b class="b1">✅ 본사 정품</b>' in br8 and '<b class="b3">🛒 약한 딜</b>' in br8
assert f'<b class="b2" data-end="{S.end_at(bp[1])}">⏰ 오늘 밤 12시 마감</b>' in i8 and 'data-k="토스 식품 마감"' in i8 and ("#brand", "브랜드") in re.findall(r'<a href="([^"]*)"><svg[^>]*>.*?</svg>([^<]+)</a>', i8.split('<nav class="bar"')[1].split("</nav>")[0])
assert all(S.FIND in x and S.FIND_JS in x for x in (i8, a8)) and i8.index('id="q"') < i8.index('class="pane"') and 'data-c="마감"' in S.FIND and "[hidden]{display:none!important}" in S.CSS
assert '<a class="lk" href="https://hotdealpick.kr/#saved"' in open("docs7/p/4.html").read() and S.LIKE_JS in open("docs7/p/4.html").read()  # 딜 페이지 = 찜 목록 링크 + '같이 보면 좋은 딜' 하트(10/11~)
# 6-9) 더 사고 싶게(10/11 진우 '홈페이지·Threads 먼저, 디자인도 좋게'): 얼마나 싼지(비교 문장 -> '쿠팡보다 N원↓')·단위가격(없으면 글에서)·토스 선착순 남은 시간,
#      딜 페이지 = 가격·절약 -> 큰 구매 버튼(가격) -> 왜 골랐나요 -> 같이 보면 좋은 딜 4개(최근 2일 제휴 딜, 같은 품목 먼저, 약한 딜·제휴 아님·같은 이름·자기 자신 빼고) -> 골드박스
assert S.saving("💡 단위가격: 10매당 31원 — 쿠팡 같은 상품(18,200원, 10매당 51원)보다 7,210원 쌈") == ("쿠팡", "7,210원") and S.saving("싸요") is None
assert S.unit_of({"text": "x\n💡 단위가격: 10매당 31원 — 쿠팡보다 쌈"}) == "10매당 31원" and S.unit_of({"text": "x", "unit": "롤당 1원"}) == "롤당 1원" and S.unit_of({"text": "x"}) == ""
assert S.buy_label("[쿠팡] 휴지 (9,900원/무료)") == "🛒 9,900원 구매하기" and H.buy_label is S.buy_label and S.end_at({"t": "2026-10-10 21:35"}) == 1791644400  # 10/11 0시 KST
mp = [{"t": td + " 09:00", "text": "🔥 [토스] 모나리자 미용티슈 300매 12입 (10,990원/무료)\n\n토스 9위\n💡 단위가격: 10매당 31원 — 쿠팡 같은 상품(18,200원)보다 7,210원 쌈\n⚠️ 확인할 점: 오늘 밤 12시까지", "url": "https://toss.shopping/_m/m"},
      {"t": td + " 09:10", "text": "🔥 [쿠팡] 코멧 화장지 30롤 (10,990원)", "url": "https://link.coupang.com/a/1", "s": 7},
      {"t": td + " 09:20", "text": "🔥 [쿠팡] 신라면 40개 (26,000원)", "url": "https://link.coupang.com/a/2", "s": 6},
      {"t": td + " 09:30", "text": "🛒 [토스] 키친타월 (16,500원)\n\n🤔 솔직히 특가로는 약한 제품", "url": "https://toss.shopping/_m/w"},
      {"t": td + " 09:40", "text": "🔥 [G마켓] 크리넥스 각티슈 (9,900원)", "url": "https://gmarket/x", "s": 6},
      {"t": td + " 09:50", "text": "🔥 [쿠팡] 깨끗한나라 물티슈 (6,980원)", "url": "https://link.coupang.com/a/3", "s": 6},
      {"t": td + " 10:00", "text": "🔥 [쿠팡] 햇반 36개 (39,680원)", "url": "https://link.coupang.com/a/4", "s": 6},
      {"t": td + " 10:10", "text": "🔥 [토스] 모나리자 미용티슈 300매 12입 (10,990원/무료)", "url": "https://toss.shopping/_m/m2"}]
S.build(mp, "docs9"); i9, d9 = open("docs9/index.html").read(), open("docs9/p/0.html").read(); g9 = S.grid_item(0, mp[0])
assert '<div class="pr">10,990원</div><div class="sv">쿠팡보다 7,210원↓</div><div class="u">10매당 31원</div>' in g9 and f'<b class="b2" data-end="{S.end_at(mp[0])}">' in g9 and S.END_JS in i9
assert d9.index('<span class="pr">10,990원</span><span class="ship">무료배송</span><span class="sv">쿠팡보다 7,210원↓</span>') < d9.index("🛒 10,990원 구매하기") < d9.index("왜 골랐나요") < d9.index("같이 보면 좋은 딜") < d9.index('class="tg"')
assert d9.index(S.DISCLOSURE) < d9.index('class="card deal"') and d9.count(S.GB_LINK) == 1 and S.LIKE_JS in d9 and S.END_JS in d9 and i9.index(S.GB_LINK) < i9.index('id="q"') and d9.index(S.DISCLOSURE) < d9.index(S.GO_FIND) < d9.index(S.GB_LINK) < d9.index('class="card deal"') and 'class="tg2" href="https://t.me/' in S.GB_LINK and "get('q');if(u){q.value=u;run()}" in S.FIND_JS  # 홈·딜 페이지 모두 골드박스·텔레그램이 위(10/11~ 딜 페이지는 검색 → 골드박스·텔레그램 → 딜)
rel9 = d9.split("같이 보면 좋은 딜")[1]
assert rel9.count('class="g"') == 4 and rel9.index("물티슈") < rel9.index("화장지") < rel9.index("햇반") < rel9.index("신라면") and all(w not in rel9 for w in ("키친타월", "각티슈", "모나리자"))
# 6-8) 검색 노출(10/9 진우 '구글·네이버에서 조회가 잘 안 돼'): robots.txt(사이트맵 위치), rss.xml(네이버 RSS 제출용 최근 30개), sitemap lastmod, 딜 페이지 설명 = 코멘트(대가성 문구·제목 반복 X), 홈 구조화 데이터
import xml.etree.ElementTree as ET
sp = [{"t": f"2026-10-0{1 + k % 9} 1{k % 10}:0{k % 6}", "text": f"{H.AFF_NOTE}\n\n🔥 [쿠팡] 휴지{k} 30롤 (19,900원/무료)\n\n싸요 & 좋아요\n💡 단위가격 롤당 663원\n\n출처: 클리앙", "url": f"https://c/{k}"} for k in range(33)] + \
     [{"t": "2026-10-09 23:00", "text": "📋 오늘의 딜 모아보기", "url": None}]
sp.sort(key=lambda p: p["t"]); S.build(sp, "docs8")
assert open("docs8/robots.txt").read() == "User-agent: *\nAllow: /\n\nSitemap: https://hotdealpick.kr/sitemap.xml\n"
rs = ET.parse("docs8/rss.xml").getroot().find("channel").findall("item")
assert len(rs) == 30 and all("모아보기" not in i.findtext("title") for i in rs) and rs[0].findtext("pubDate").endswith(" +0900") and rs[0].findtext("link").startswith("https://hotdealpick.kr/p/")
assert rs[0].findtext("description") == "싸요 & 좋아요 💡 단위가격 롤당 663원" and rs[0].findtext("title").startswith("[쿠팡] 휴지")
sm = ET.parse("docs8/sitemap.xml").getroot(); ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
assert len(sm) == 36 and all(u.findtext(ns + "lastmod") for u in sm) and sm[0].findtext(ns + "lastmod") == "2026-10-09"
d8 = open("docs8/p/0.html").read()
assert '<meta name="description" content="싸요 &amp; 좋아요 💡 단위가격 롤당 663원">' in d8 and 'href="https://hotdealpick.kr/rss.xml"' in d8
i8 = open("docs8/index.html").read(); ld8 = json.loads(i8.split('<script type="application/ld+json">')[1].split("</script>")[0])
assert ld8["@graph"][1]["sameAs"] == [S.INSTA, S.THREADS, S.BLOG, S.CHANNEL] and "<title>핫딜픽 - 오늘의 핫딜·특가 모음 (쿠팡·네이버·토스)</title>" in i8
assert S.summary("🔥 [G마켓] 우유 (1원)") == "" and '<meta name="description" content="[G마켓] 우유 (1원)">' in (S.build([{"t": "2026-10-09 10:00", "text": "🔥 [G마켓] 우유 (1원)", "url": "https://g"}], "docs8") and open("docs8/p/0.html").read())  # 코멘트 없으면 제목
os.makedirs("docs7/cards", exist_ok=True); open("docs7/cards/2026-10-09.png", "wb").write(b"x"); S.build(hp, "docs7"); i7c = open("docs7/index.html").read(); os.remove("docs7/cards/2026-10-09.png")
assert i7c.index('<div class="pane"><section class="day" id="hot"') < i7c.index('<div class="pane"><section class="card" id="today"') < i7c.index('<div class="pane"><section class="day" id="toss"')  # 처음 보이는 칸 = 인기(10/9 진우 선택), 카드 딜은 그다음
S.build(hp[2:3] + hp[5:6] + [{**hp[4], "text": "🔥 [네이버] 우유 (2,990원)"}], "docs7"); i7 = open("docs7/index.html").read()
assert 'id="hot"' not in i7 and 'id="beauty"' not in i7 and "#beauty" not in i7 and 'id="life"' in i7  # 반응 딜 1개·화장품 0개 -> 칸·탭 없음

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
    t = [x["text"] for m, x in sent if m == "sendMessage" and x["chat_id"] == "@ch"][-1]  # 10/10~ ✅ 없이 채널에 바로
    assert not [m for m, x in sent if m == "draft"] and "A딜" in t and "옛날딜" not in t and t.count("모아보기") == 1 and "hotdealpick.kr" in t and "blog.naver.com" in t and any(k.startswith("digest_") for k in seen) and "bundles" in seen  # 모아보기도 묶음 글로 기록(10/11 간격)
    blog = [x for m, x in sent if m == "sendMessage"][-1]["text"]  # 블로그용은 버튼 없는 일반 메시지로 뒤따라옴
    assert "제목: " in blog and "A딜" in blog and "https://a" in blog and "옛날딜" not in blog and "쿠팡 파트너스" in blog
    v = [x for m, x in sent if m == "video"]  # 릴스: 점수 높은 순, 오늘 글만, 모아보기 제외, 캡션에 대가성 문구·해시태그
    assert len(v) == 1 and os.path.getsize(v[0]["path"]) > 10000 and v[0]["caption"].split("\n\n")[1].startswith("B딜 개당 99원 · ") and "가성비 TOP2" in v[0]["caption"]
    assert v[0]["caption"].split("\n\n")[0] == H.ig_notes([]) and "맨 위 '" + S.card_name(today) + "'에서 1~2번" in v[0]["caption"]  # 대가성 문구 맨 앞(릴스도), 사이트 칸 이름 그대로
    assert v[0]["caption"].index("1. [G마켓] B딜") < v[0]["caption"].index("2. A딜") and "옛날딜" not in v[0]["caption"]
    assert "제휴 링크" in v[0]["caption"] and "#핫딜" in v[0]["caption"] and len(v[0]["caption"]) <= 1024
    assert fills == [(H.REEL_PROMPT, ["A딜 | "])] and "B딜" not in str(fills)  # B딜은 이미 hook·pts 있음
    sent.clear(); H.digest(seen, P); assert not sent
    seen.pop("blog_" + next(k for k in seen if k.startswith("digest_"))[7:]); sent.clear(); H.digest(seen, P)  # 블로그용 글만 실패했던 날: 초안·릴스 없이 블로그용 글만 다시
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
th9 = lambda: urllib.parse.parse_qs(urllib.parse.urlsplit(calls[2][1]).query)["text"][0]
seen, calls[:] = {}, []; H.threads(seen); assert th9().startswith("일부 링크는 제휴 링크로 수수료를 받을 수 있어요.\n\n📋 ")  # 하루 카드 글도 대가성 문구 맨 앞(카드 캡션과 같게)
pj8, oj8 = open("posts.json").read(), f"docs/cards/{today}.json"; os.path.exists(oj8) and os.rename(oj8, "oj8.json")  # 21시 이후면 모아보기 절이 만든 순서 파일 -> 잠깐 치움
json.dump([{"t": f"{today} 1{n}:00", "text": f"🔥 [{m}] 아주 긴 상품 이름 {n}번 대용량 기획 세트 묶음 구성 (9,900원/무료)", "url": u, "s": 8} for n, (m, u) in enumerate(
    [("네이버", "https://naver.me/a"), ("올리브영", "https://oy.run/b"), ("쿠팡", "https://link.coupang.com/a/c"), ("토스", "https://toss.shopping/_m/d"), ("G마켓", "https://click.linkprice.com/x")])], open("posts.json", "w"), ensure_ascii=False)
seen, calls[:] = {}, []; H.threads(seen); t8 = th9()
assert len(t8) <= 480 and t8.startswith(H.NAVER_NOTE + "\n" + H.OY_NOTE + "\n" + H.DISCLOSURE + "\n" + H.TOSS_NOTE + "\n" + H.AFF_NOTE + "\n\n📋 ") and t8.endswith("https://t.me/hotdeal_pick") and 1 <= t8.count("번 대용량") < 5  # 길면 문구 말고 번호 줄을 줄임
open("posts.json", "w").write(pj8); seen = {"threads_" + today.replace("-", ""): 1}; os.path.exists("oj8.json") and os.rename("oj8.json", oj8)
del H.E["THREADS_TOKEN"]; seen, sent[:], calls[:] = {}, [], []
H.threads(seen)  # 토큰 없으면: 사진만 보내고 Threads 호출 없음
assert [m for m, _ in calls] == ["HEAD"] and sent[-1][0] == "sendPhoto" and "Threads" not in sent[-1][1]["caption"] and list(seen)[0].startswith("threads_")
# 9-1b) 인스타 하루 3번(10/11 진우 '인스타 업그레이드 1번'): 12시 = 0~12시 딜·18시 = 12~18시 딜 시간대 카드 + 21시 하루 카드 -> 인스타(ig_cards), Threads는 하루 카드 그대로(threads)
#        시간대 카드: 그 시각 첫 실행에 JPEG·번호 순서만 만들고(HTTP 없음) 다음 실행에 사이트에 뜨면 컨테이너, 3시간 안에만, 딜 3개 미만이면 건너뜀, 회차마다 1번
#        캡션: 대가성 문구 맨 앞(카드 딜의 제휴 프로그램마다) · 몇 시 카드 · 번호 줄 5개(가격 꼬리 뺌) · 사이트 맨 위 어느 카드인지 · 해시태그 5개(#최저가 X, 카테고리 태그)
#        발행(ig_publish) 뒤 docs/cards/ig.json -> 사이트 맨 위 카드 딜 = 인스타에 올라간 가장 최근 카드(앞 카드는 접어서), 하루 5개 상한·스팸 의심 24시간 쉼·이미 발행됨(PUBLISHED)은 기록만
import calendar, shutil
TK = lambda s: calendar.timegm(time.strptime(s, "%Y-%m-%d %H:%M")) - 9 * 3600
D9 = "2026-10-12"; tt9, pj9 = time.time, open("posts.json").read()
cards9 = "docs/cards9"; shutil.rmtree(cards9, ignore_errors=True); os.rename("docs/cards", cards9); os.makedirs("docs/cards")  # 앞 절(실제 오늘 날짜) 카드와 안 섞이게 -> 끝나고 되돌림
for f in os.listdir("docs/cards"):
    if f.startswith(D9) or f == "ig.json": os.remove(f"docs/cards/{f}")
json.dump([{"t": f"{D9} 08:00", "text": "🔥 [쿠팡] 휴지 30롤 (9,900원/무료)", "url": "https://link.coupang.com/a/h", "s": 7},
           {"t": f"{D9} 09:00", "text": "🔥 [G마켓] 토리든 세럼 50ml (19,900원/무료)", "url": "https://click.linkprice.com/click.php?m=gmarket&a=x", "s": 8},
           {"t": f"{D9} 10:00", "text": "🔥 [11번가] 삼다수 2L 12병 (9,900원/무료)", "url": "https://www.11st.co.kr/p/1", "s": 6},
           {"t": f"{D9} 11:59", "text": "🔥 [네이버] 햇반 24개 (22,000원/무료)", "url": "https://naver.me/abc", "s": 6},
           {"t": f"{D9} 12:00", "text": "🔥 [옥션] 12시 딜 (1,000원)", "url": "https://www.auction.co.kr/p", "s": 9},
           {"t": f"{D9} 13:00", "text": "🔥 [옥션] 오후 딜 (2,000원)", "url": "https://www.auction.co.kr/q", "s": 7},
           {"t": "2026-10-11 23:00", "text": "🔥 [쿠팡] 어제 딜 (1,000원)", "url": "https://link.coupang.com/a/y", "s": 9}], open("posts.json", "w"), ensure_ascii=False)
ig9, live9, st9 = [], set(), {"v": "FINISHED"}
def ig9_http(url, body=None, headers=None, method=None):
    ig9.append((method or "GET", url, body))
    if method == "HEAD":
        if url.rsplit("/", 1)[-1] not in live9: raise OSError("404")
        return ""
    if url.startswith(H.IG):
        if "?fields=status_code" in url: return json.dumps({"status_code": st9["v"]})
        if url.endswith("/media_publish"):
            if st9.get("spam"): e = urllib.error.HTTPError(url, 400, "x", {}, None); e.body = '{"error":{"error_subcode":2207051}}'; raise e
            return json.dumps({"id": "P1"})
        st9["n"] = st9.get("n", 0) + 1; return json.dumps({"id": "IMG%d" % st9["n"]})
    raise AssertionError(url)
H.E.update(IG_TOKEN="pt", IG_USER_ID="178"); H.http, seen, sent[:] = ig9_http, {}, []
def at9(t, step=None):
    ig9.clear(); sent.clear(); time.time = lambda: TK(f"{D9} {t}"); (step or H.ig_cards)(seen)
at9("11:50"); assert not ig9 and not seen and not os.path.exists(f"docs/cards/{D9}_12.jpg")  # 12시 전
at9("12:05"); assert not ig9 and open(f"docs/cards/{D9}_12.jpg", "rb").read(2) == b"\xff\xd8" and not os.path.exists(f"docs/cards/{D9}_12.png")  # 만들기만(HTTP 없음), 진짜 JPEG만
assert json.load(open(f"docs/cards/{D9}_12.json")) == [1, 0, 3, 2] and "igs_" + D9 + "_12" not in seen  # 0~12시 딜만(12:00·어제 딜 X), 점수·제휴 먼저
at9("12:19"); assert [m for m, u, b in ig9] == ["HEAD"] and "igs_" + D9 + "_12" not in seen  # 사이트 배포 전 -> 다음 실행에
live9.add(f"{D9}_12.jpg"); at9("12:33")
(m, u, b), = [x for x in ig9 if x[0] == "POST"]
assert u == H.IG + "/178/media" and b["image_url"] == f"https://hotdealpick.kr/cards/{D9}_12.jpg" and seen["igc_IMG1"]["card"] == f"{D9}_12" and "igs_" + D9 + "_12" in seen
import build_site as S9
assert list(json.load(open(H.IG_LIVE))) == [f"{D9}_12"] and S9.card_stems("docs") == [f"{D9}_12"]  # 사이트 맨 위에 먼저(이번 실행 배포)
at9("12:34", H.ig_publish); assert [m for m, u, b in ig9] == ["GET"] and "igc_IMG1" in seen  # 만든 실행엔 발행 X(사이트 먼저) -> 다음 실행에
cap = b["caption"]
assert cap.startswith(H.NAVER_NOTE + "\n" + H.DISCLOSURE + "\n" + H.AFF_NOTE + "\n\n10월 12일 낮 12시 핫딜\n\n1. [G마켓] 토리든 세럼 50ml\n2. [쿠팡] 휴지 30롤\n"), cap  # 대가성 문구 맨 앞(프로그램마다, 네이버·올영 먼저), 번호 줄 = 카드 순서·가격 꼬리 뺌
assert "맨 위 '10월 12일 낮 12시 카드 딜'에서 번호를 누르면 바로 구매 페이지" in cap and cap.endswith("#핫딜 #특가 #핫딜픽 #생필품 #화장품") and "#최저가" not in cap and len(cap) <= 2200
at9("12:47"); assert not ig9  # 회차마다 1번
sv9 = seen; seen = {}; at9("12:47"); assert not ig9; seen = sv9  # seen 캐시를 잃어도 기록(ig.json, 커밋됨)에 있으면 다시 안 올림
seen9 = dict(seen); seen = {}; at9("15:01"); assert not ig9 and not seen; seen = seen9  # 3시간 지나면 그 회차는 안 함(낮에 몰아 X)
at9("18:05"); assert not ig9 and seen["igs_" + D9 + "_18"]["skip"] == 2 and not os.path.exists(f"docs/cards/{D9}_18.jpg")  # 12~18시 딜 2개 -> 건너뜀
shutil.copy(f"docs/cards/{D9}_12.jpg", f"docs/cards/{D9}.jpg"); open(f"docs/cards/{D9}.png", "wb").write(b"p"); live9.add(f"{D9}.jpg")
json.dump([4, 1, 0, 5, 2, 3], open(f"docs/cards/{D9}.json", "w"))  # 21시 하루 카드(모아보기가 만듦)
at9("20:59"); assert not [x for x in ig9 if x[0] == "POST"]
at9("21:20"); (m, u, b), = [x for x in ig9 if x[0] == "POST"]
assert b["image_url"] == f"https://hotdealpick.kr/cards/{D9}.jpg" and "10월 12일 오늘의 핫딜 모음\n\n1. [옥션] 12시 딜\n" in b["caption"] and "맨 위 '10월 12일 카드 딜'에서 번호를 누르면" in b["caption"]
assert b["caption"].count("\n") and b["caption"].split("\n\n")[2].count("\n") == 4  # 번호 줄은 카드에 든 5개만(CARD_N)
# 발행: 사이트 맨 위 카드 = 인스타에 올라간 카드
assert S9.card_stems("docs") == [f"{D9}_12", D9] and "📸 10월 12일 카드 딜" in S9.card_picks(json.load(open("posts.json")), "docs")  # 발행 전에도 사이트 먼저(컨테이너 만든 실행)
at9("21:34", H.ig_publish)
assert [u.rsplit("/", 1)[-1] for m, u, b in ig9 if u.endswith("media_publish")] == ["media_publish"] * 2 and set(json.load(open(H.IG_LIVE))) == {f"{D9}_12", D9}
assert [p["text"] for m, p in sent] == ["📸 인스타 자동 게시 완료 — 낮 12시 카드 (instagram.com/hotdealpick.kr)", "📸 인스타 자동 게시 완료 — 오늘 카드 (instagram.com/hotdealpick.kr)"]
pk9 = S9.card_picks(json.load(open("posts.json")), "docs")
assert S9.card_stems("docs") == [f"{D9}_12", D9] and "📸 10월 12일 카드 딜" in pk9 and "<details><summary>10월 12일 낮 12시 카드 딜</summary>" in pk9  # 최근 카드 펼침 + 앞 카드 접어서
assert pk9.split("<details>")[0].count('class="pick"') == 5 and pk9.split("<details>")[1].count('class="pick"') == 4  # 하루 카드 5개(CARD_N) · 12시 카드 4개
open(f"docs/cards/{D9}_18.jpg", "wb").write(b"j"); json.dump([5], open(f"docs/cards/{D9}_18.json", "w")); assert S9.card_stems("docs") == [f"{D9}_12", D9]  # 인스타에 안 올라간 카드는 사이트에 안 보임
seen.update({"igc_A": {"t": 1, "card": f"{D9}_18"}}); st9["v"] = "PUBLISHED"; at9("21:48", H.ig_publish)
assert not [1 for m, u, b in ig9 if u.endswith("media_publish")] and "igc_A" not in seen and f"{D9}_18" in json.load(open(H.IG_LIVE)) and not sent  # 이미 발행됨 -> 기록만(알림 X)
st9["v"] = "FINISHED"; seen.update({"igpub_20261012": {"t": 1, "n": 5}, "igc_B": {"t": 1}}); at9("22:00", H.ig_publish); assert "igc_B" in seen and not sent  # 하루 5개 상한 -> 다음 날
seen["igpub_20261012"]["n"], st9["spam"] = 0, True
try:
    at9("22:14", H.ig_publish); raise AssertionError("스팸 의심 오류는 예외(main이 알림)")
except urllib.error.HTTPError:
    pass
assert seen["ig_hold"] > TK(f"{D9} 22:14") + 86000 and "igc_B" not in seen; at9("22:28"); assert not ig9  # 24시간 인스타 쉼(카드 만들기·올리기 X), 그 컨테이너는 버림
sv9 = seen; seen = {"ig_hold": TK(f"{D9} 22:14") + 86400}; os.rename(f"docs/cards/{D9}_12.jpg", "h9.jpg"); at9("12:05"); assert not ig9 and not os.path.exists(f"docs/cards/{D9}_12.jpg"); os.rename("h9.jpg", f"docs/cards/{D9}_12.jpg"); seen = sv9  # 쉬는 동안엔 시간대 카드도 안 만듦
assert S9.card_order(json.load(open("posts.json")), f"{D9}_15") == [] and len(S9.card_order(json.load(open("posts.json")), "2026-10-11")) == 1  # 순서 파일 없는 시간대 카드 = 번호 없음(하루 카드는 그날 딜 순서)
st9.pop("spam"); del seen["ig_hold"]
# 리뷰(10/11) 고침: 발행 오류(인스타 5xx·응답 끊김)는 컨테이너 그대로 -> 다음 실행에 상태 다시(사실 올라갔으면 기록만, 아니면 다시 발행), 다른 컨테이너는 계속
def ig9e_http(url, body=None, headers=None, method=None):
    if (url.endswith("/media_publish") and st9.get("e500")) or (url.endswith("/178/media") and method == "POST" and st9.get("mk500")):
        ig9.append((method, url, body)); e = urllib.error.HTTPError(url, 500, "x", {}, None); e.body = '{"error":{"is_transient":true}}'; raise e
    return ig9_http(url, body, headers, method)
H.http, st9["e500"] = ig9e_http, True
json.dump({}, open(H.IG_LIVE, "w")); seen = {"igc_C": {"t": 1, "card": f"{D9}_18"}, "igc_R": 1.0}
try:
    at9("22:30", H.ig_publish); raise AssertionError("발행 오류는 예외(main이 알림)")
except urllib.error.HTTPError:
    pass
assert set(seen) == {"igc_C", "igc_R"} and len([1 for m, u, b in ig9 if u.endswith("media_publish")]) == 2 and not sent  # 둘 다 시도, 컨테이너 그대로
st9.pop("e500"); st9["v"] = "PUBLISHED"; at9("22:44", H.ig_publish)
assert not seen and list(json.load(open(H.IG_LIVE))) == [f"{D9}_18"] and not sent  # 사실 올라갔음 -> 기록만(알림 X)
st9.update(v="FINISHED", e500=True); seen = {"igc_D": {"t": 1, "card": f"{D9}_18"}}
try:
    at9("22:50", H.ig_publish); raise AssertionError("발행 오류는 예외")
except urllib.error.HTTPError:
    pass
st9.pop("e500"); at9("23:04", H.ig_publish); assert not seen.get("igc_D") and sent[-1][1]["text"].startswith("📸 인스타 자동 게시 완료 — 저녁 6시 카드")  # 안 올라갔음 -> 다시 발행
st9["v"], seen = "ERROR", {"igc_E": {"t": 1, "card": f"{D9}_18"}}
try:
    at9("23:10", H.ig_publish); raise AssertionError("처리 실패는 예외")
except RuntimeError as e:
    assert f"https://hotdealpick.kr/cards/{D9}_18.jpg 카드를 직접 올려줘" in str(e) and not seen  # 시간대 카드는 봇 채팅에 안 옴 -> 카드 주소
# 컨테이너 만들기 실패(인스타 일시 오류): 회차 안에서 IG_TRIES번까지 다음 실행에 다시(안 올라간 컨테이너는 안 보여서 두 번 안 올라감), 마지막엔 카드 주소
st9.update(v="FINISHED", mk500=True); seen = {}; json.dump({}, open(H.IG_LIVE, "w"))
for k, t in enumerate(["12:40", "12:54", "13:08"], 1):
    try:
        at9(t); raise AssertionError("만들기 실패는 예외")
    except RuntimeError as e:
        assert seen["igs_" + D9 + "_12"]["fail"] == k and (f"https://hotdealpick.kr/cards/{D9}_12.jpg 카드를 직접 올려줘" in str(e)) == (k == H.IG_TRIES), str(e)
at9("13:22"); assert not ig9 and not json.load(open(H.IG_LIVE))  # 3번 실패 -> 그 회차 끝
st9.pop("mk500"); seen = {"igs_" + D9 + "_12": {"t": 1, "fail": 1}}; at9("13:36")
assert len([1 for m, u, b in ig9 if m == "POST"]) == 1 and seen["igs_" + D9 + "_12"] == {"t": TK(f"{D9} 13:36")} and list(json.load(open(H.IG_LIVE))) == [f"{D9}_12"]  # 다시 해서 성공 = 회차 끝
# 사이트 맨 위 카드 = 가장 최근 카드부터 24시간 안(다음 날 낮 12시 카드가 올라가도 어제 저녁·밤 카드는 접어서, 딱 24시간 된 어제 낮 12시는 빠짐)
H.ig_live("2026-10-13_12", TK(f"{D9} 23:00")); assert json.load(open(H.IG_LIVE)) == {f"{D9}_12": TK(f"{D9} 13:36"), "2026-10-13_12": TK(f"{D9} 23:00")}  # 기록 = 만든 시각
json.dump({"2026-10-01": TK(f"{D9} 23:00") - 8 * 86400, f"{D9}_12": 1}, open(H.IG_LIVE, "w")); H.ig_live(f"{D9}_18", TK(f"{D9} 23:00")); assert list(json.load(open(H.IG_LIVE))) == [f"{D9}_18"]  # 7일 지난 기록 정리
json.dump({f"{D9}_12": 1, f"{D9}_18": 1, "2026-10-13_12": 1}, open(H.IG_LIVE, "w"))
assert S9.card_stems("docs") == [f"{D9}_18", D9, "2026-10-13_12"]
# 캡션 대가성 문구는 늘 맨 앞: 제휴 링크 없는 카드 = 일반 안내 1줄, 토스·쿠팡 딜 = 올린 뒤 제휴 링크로 바뀔 수 있어서(toss_relink·진우 파트너스 링크) 그 문구 미리
pj = json.load(open("posts.json")); pj.append({"t": f"{D9} 13:30", "text": "🔥 [토스] 김 20봉 (5,000원/무료)", "url": "https://www.ppomppu.co.kr/zboard/view.php?no=9", "s": 7})
json.dump(pj, open("posts.json", "w"), ensure_ascii=False); o9 = next(i for i, p in enumerate(pj) if "오후 딜" in p["text"])
json.dump([o9], open(f"docs/cards/{D9}_18.json", "w"))
assert H.card_caption(f"{D9}_18")[1].startswith("일부 링크는 제휴 링크로 수수료를 받을 수 있어요.\n\n10월 12일 저녁 6시 핫딜\n\n1. [옥션] 오후 딜\n")
json.dump([o9, len(pj) - 1], open(f"docs/cards/{D9}_18.json", "w"))
assert H.card_caption(f"{D9}_18")[1].startswith(H.TOSS_NOTE + "\n\n10월 12일 저녁 6시 핫딜\n") and "제휴 링크로 수수료" not in H.card_caption(f"{D9}_18")[1]
shutil.rmtree("docs/cards"); os.rename(cards9, "docs/cards")
open("posts.json", "w").write(pj9); H.E["THREADS_TOKEN"] = "tk"; seen, sent[:] = {}, []; time.time = tt9; H.http = th_http; live = True; calls.clear(); H.threads(seen)  # Threads 카드는 그대로, 인스타는 threads()에서 안 올림(ig_cards)
assert not [c for c in calls if H.IG in c[1]] and any("/threads_publish?" in u for _, u in calls) and "인스타·Threads 자동 게시 중" in sent[-1][1]["caption"]
assert "threads, threads_deals, ig_cards, ig_repost, ig_publish" in inspect.getsource(H.main) and "ig = step in (ig_cards, ig_publish)" in inspect.getsource(H.main)
for f in os.listdir("docs/cards"):
    if f.startswith(D9) or f == "ig.json": os.remove(f"docs/cards/{f}")
del H.E["IG_TOKEN"], H.E["IG_USER_ID"], H.E["THREADS_TOKEN"]; H.http, time.time = th_http, tt9
ig_calls, fail_ig = [], [False]
def igc_http(url, body=None, headers=None, method=None):
    if url.startswith(H.IG):
        ig_calls.append((url, body, headers, method))
        if fail_ig[0]: raise OSError("ig down")
        return json.dumps({"id": "IMG1"})
    return th_http(url, body, headers, method)
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
assert u == H.IG + "/178/media" and m == "POST" and b["image_url"] == f"https://hotdealpick.kr/cards/re/{today}.jpg" and "카드 딜'에서 번호를 누르면 바로 구매" in b["caption"] and "1. A딜" in b["caption"]
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
assert "coupang_remind, oy_claim, report" in inspect.getsource(H.main)
# 9-6) 올리브영 쇼핑 큐레이터(10/10 진우 가입): oy.run = 공식 광고 문구 맨 앞, 사본 안내, 매달 21일~말일 10시 이후 정산 신청 알림 1번
assert H.OY_NOTE == "이 포스팅은 올리브영 쇼핑 큐레이터 활동의 일환으로, 구매 시 일정 금액의 수수료를 제공받습니다." and H.aff_note("https://oy.run/RGwi61ygSEUlAk") == H.OY_NOTE
assert H.with_note("🔥 [올리브영] 세럼", [], "https://oy.run/x")[0].startswith(H.OY_NOTE + "\n\n🔥") and S.aff("https://oy.run/x") and S.title_of(H.OY_NOTE + "\n\n🔥 [올리브영] 세럼") == "[올리브영] 세럼"
assert H.store_info("[올리브영]메디힐 세럼 1+1 (24,200원/무료)") == H.STORES["올리브영"] and H.store_info("세럼", "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A1") == H.STORES["올리브영"]
assert H.store_info("[네이버][올리브영기프트카드] 5만원권") == H.STORES["네이버"] and H.is_oy("[올영] 립밤") and not H.is_oy("[네이버]올리브영 초콜렛")
assert "[올리브영] 딜 comment는" in H.DEAL_PROMPT and "'추천'" in H.DEAL_PROMPT and "MIN_SCORE - earns(" in inspect.getsource(H.main) and H.earns("[올리브영] 세럼")  # 사실만·1점 낮춤(10/10~ 수수료 몰 전체, 4-6)
oyh = [{"board": "뽐뿌", "hits": "댓글0·조회3000·추천5·비추0", "age": 60, "title": t} for t in ("[올리브영] 세럼", "[G마켓] 우유")]
H.mark_hot(oyh); assert not any(k in oyh[0] for k in ("hot", "pop", "vpm", "rec")) and oyh[1]["hot"] and oyh[1]["pop"]  # 올영은 추천·반응 표시 X
sent.clear(); H.post_or_draft({"title": "[올리브영]다슈 립밤 4g (8,820원)", "url": "https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&no=1", "board": "뽐뿌"}, "8,820원, 2만 원 이상 무료배송", 6, "다슈 립밤")
cm = [p for m, p in sent if m == "copyMessage"][0]["reply_markup"]["inline_keyboard"]
assert cm[1] == [{"text": "📋 상품명 복사", "copy_text": {"text": "다슈 립밤"}}] and cm[2][0]["text"].startswith("💰 올리브영 쇼핑 큐레이터")
pjo = json.load(open("posts.json")); pjo[-1]["text"] = "🔥 [올리브영]다슈 립밤 4g (8,820원)"; json.dump(pjo, open("posts.json", "w"), ensure_ascii=False)  # 가짜 tg는 글 내용을 안 돌려줌
assert H.pending_copy("https://oy.run/abc") == pjo[-1] and H.pending_copy("https://naver.me/x") is None  # 답장 없이 링크만 보내도 그 올영 사본으로(다른 프로그램 링크는 X)
seen, sent[:] = {}, []
for dt, want in ((14 * 86400, 0), (15 * 86400 - 4 * 3600, 0), (15 * 86400, 1), (15 * 86400 + 3600, 1)):  # 10/20 13시·10/21 9시·13시·14시(같은 달 1번)
    time.time = lambda dt=dt: 1791259200 + dt; H.oy_claim(seen); assert len(sent) == want, (dt, sent)
assert sent[0][1]["text"] == H.OY_CLAIM and "oyclaim_202610" in seen
sent.clear(); time.time = lambda: 1791259200 + 20 * 86400; H.oy_claim({}); assert len(sent) == 1  # 10/26 = 아직 기간
sent.clear(); time.time = lambda: 1791259200 + 26 * 86400; H.oy_claim({}); assert not sent  # 11/1 = 다음 기간 전
time.time = lambda: 1791291600  # 10/6 22:00 KST
oyp = [{"t": "2026-10-06 10:00", "text": f"{H.OY_NOTE}\n\n🔥 [올리브영] 세럼 (1원)\n\n1+1 구성", "url": "https://oy.run/x"}, {"t": "2026-10-06 11:00", "text": "🔥 [G마켓] 우유 (1원)\n\n싸요", "url": "https://a"}]
d0 = H.draft; H.draft = lambda text, **k: sent.append(("draft", text)) or {"message_id": 9}; sent.clear(); H.digest({}, oyp)
dg = [p["text"] for m, p in sent if m == "sendMessage" and p["chat_id"] == "@ch"][0]
assert not [m for m, p in sent if m == "draft"] and dg.startswith("📋 <b>오늘의 딜 모아보기 (10/6)</b>")  # 10/10 진우 '✅ 없이 자동 게시' -> 채널에 바로, 제휴 링크 없으면 문구 없음
LPU = "https://click.linkprice.com/click.php?m=gmarket&a=x"
lpp = [{"t": "2026-10-06 10:00", "text": f"{H.aff_note(LPU)}\n\n🔥 [G마켓] 우유 (1원)", "url": LPU}, {"t": "2026-10-06 11:00", "text": "🔥 [토스] 김 (2원)", "url": "https://toss.shopping/_m/a"},
       {"t": "2026-10-06 12:00", "text": "🔥 [G마켓] 두유 (3원)", "url": LPU}]
sent.clear(); H.digest({}, lpp); dl = [p["text"] for m, p in sent if m == "sendMessage" and p["chat_id"] == "@ch"][0]
assert dl.startswith(f"<i>{H.aff_note(LPU)}</i>\n<i>{H.aff_note('https://toss.shopping/_m/a')}</i>\n\n📋 ") and dl.count("<i>") == 2  # 프로그램마다 1줄, 맨 위
tg9 = H.tg; H.tg = lambda method, **p: sent.append((method, p)) or (None if p.get("chat_id") == "@ch" else {"message_id": 1})
sent.clear(); sk = {}; H.digest(sk, lpp); H.tg = tg9
assert [x for m, x in sent if m == "draft"][0] == dl and any(k.startswith("digest_") for k in sk)  # 채널 게시 실패 -> 예전처럼 ✅ 초안
big = [{"t": "2026-10-06 10:00", "text": f"🔥 [G마켓] 아주 긴 상품 이름 {n} " + "가" * 60 + " (1,000원/무료)", "url": f"https://a/{n}"} for n in range(80)]
sent.clear(); H.digest({}, big); db = [p["text"] for m, p in sent if m == "sendMessage" and p["chat_id"] == "@ch"][0]; H.draft = d0
vis = H.html.unescape(re.sub(r"<[^>]+>", "", db)); kept = db.count('<a href="https://a/')
assert len(vis) <= 4000 and 1 < kept < 80 and f"… 외 {80 - kept}개는 사이트에서" in db and db.endswith("https://t.me/hotdeal_pick")  # 딜이 아주 많은 날: 4096자 안으로, 뒤쪽은 '외 N개'
assert f'href="{H.SITE}p/0.html">[올리브영] 세럼' in dg and "oy.run" not in dg and 'href="https://a"' in dg  # 모아보기 = 링크만 나열 -> 올영은 사이트로
bt = H.blog_text(oyp, time.gmtime(1791291600 + 9 * 3600))
assert bt.split("\n\n")[2] == H.OY_NOTE and "👉 https://oy.run/x" in bt  # 블로그: 올영 문구 본문 맨 위(코멘트 있는 글이라 링크 그대로)
open("posts.json", "w").write(pj); H.tg, time.time = tg0, tt5
# 9-2) 딜마다 Threads: 사이트 페이지 링크, 제휴 링크면 대가성 문구 맨 앞, 3시간 지난 딜·모아보기 제외, 1회 3개, 미배포면 다음에, 두 번 안 올림
kt = lambda h: time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - h * 3600))
json.dump([{"t": kt(4), "text": "🔥 [옛날] 딜", "url": "https://a"},
           {"t": kt(0), "text": "📋 모아보기", "url": None},
           {"t": kt(1), "text": f"{H.DISCLOSURE}\n\n🔥 [쿠팡] 휴지 30롤\n\n싸요\n\n출처: 뽐뿌", "url": "https://link.coupang.com/a/x"},
           {"t": kt(0.5), "text": "🔥 [카카오] 고구마 3kg\n\n맛있음\n\n출처: 뽐뿌", "url": "https://www.ppomppu.co.kr/1"},
           {"t": kt(0.2), "text": "🔥 [G마켓] 우유\n\n좋음\n\n출처: 뽐뿌", "url": "https://x"},
           {"t": kt(0.1), "text": "🛒 [옥션] 라면\n\n🤔 솔직히 특가로는 약한 제품\n좋음\n\n출처: 뽐뿌", "url": "https://y"}], open("posts.json", "w"))
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
assert t3.startswith("🔥 [카카오] 고구마 3kg\n\n맛있음") and "이 포스팅은" not in t3 and t3.endswith("t.me/hotdeal_pick") and all("🙋 팔로우하면" in t for t in (t2, t3))
assert made[0]["media_type"] == ["TEXT"] and made[0]["topic_tag"] == ["핫딜"] and max(len(t2.encode()), len(t3.encode())) < 500
assert [bool(p.get("th")) for p in json.load(open("posts.json"))] == [False, False, True, True, False, False]
live_pages, calls[:] = {2, 3, 4, 5}, []; H.threads_deals({})  # 재실행: 올린 건 건너뛰고 남은 것만
assert [parse_qs(urlsplit(u).query)["link_attachment"][0][-8:] for m, u in calls if "/777/threads?" in u] == ["p/4.html", "p/5.html"]
assert [parse_qs(urlsplit(u).query)["text"][0] for m, u in calls if "/777/threads?" in u][1].startswith("🛒 [옥션] 라면\n\n🤔 솔직히 특가로는 약한 제품\n좋음")  # 약한 딜은 🛒(채널 글과 같게)
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
# 9-2b) Threads 엄선·훅(10/11 진우): 둘째 줄 '💸 쿠팡보다 N원 싸요'(비교 문장 있을 때), 봇 딜은 7점↑ 전부 + 6점 제휴 딜만 하루 TH_BOT_MAX까지, 5점·제휴 없는 6점은 채널에만, 진우 링크(own)는 점수 상관없이
t0, mx0 = time.time, H.TH_BOT_MAX; time.time, H.TH_BOT_MAX, H.E["THREADS_TOKEN"] = (lambda: 1791687600), 2, "tk"  # 10/11 12:00 KST(자정 걸침 방지)
json.dump([{"t": kt(1), "text": "🔥 [G마켓] 6점제휴아님\n\n좋음", "url": "https://x", "s": 6}, {"t": kt(0.9), "text": "🔥 [쿠팡] 5점\n\n좋음", "url": "https://link.coupang.com/a/5", "s": 5}]
          + [{"t": kt(0.8 - k / 10), "text": f"🔥 [쿠팡] {n}\n\n좋음", "url": f"https://link.coupang.com/a/{k}", "s": s} for k, (n, s) in enumerate((("6점A", 6), ("6점B", 6), ("8점", 8), ("6점C", 6)))]
          + [{"t": kt(0.3), "text": "🔥 [토스] 진우링크 (10,990원)\n\n💡 단위가격: 10매당 31원 — 쿠팡 같은 상품(18,200원)보다 7,210원 쌈", "url": "https://toss.shopping/_m/j", "s": 5, "own": 1}], open("posts.json", "w"))
H.http, live_pages, calls[:] = td_http, set(range(7)), []
for _ in range(3): H.threads_deals({})
made = [parse_qs(urlsplit(u).query)["text"][0] for m, u in calls if "/777/threads?" in u]
assert [p.get("th") for p in json.load(open("posts.json"))] == [None, None, 1, 1, 1, None, 1] and len(made) == 4  # 6점C = 봇 딜 하루 한도(2) 넘음 -> 채널에만
assert made[-1].startswith(H.TOSS_NOTE + "\n\n💸 쿠팡보다 7,210원 싸요\n🔥 [토스] 진우링크 (10,990원)\n\n") and all("💸" not in t for t in made[:-1])
time.time, H.TH_BOT_MAX = t0, mx0; del H.E["THREADS_TOKEN"]
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
assert ic[-1][0].endswith("/178/media_publish") and ic[-1][1] == {"creation_id": "C1"} and list(seen) == [time.strftime("igpub_%Y%m%d", time.gmtime(time.time() + 9 * 3600))] and "자동 게시 완료" in sent[-1][1]["text"]  # 발행 수(하루 상한)만 남음
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
assert any("업로드 실패" in p["text"] for m, p in sent if m == "sendMessage") and len(vids) == 1 and vids[0].split("\n\n")[1].startswith("우유 개당 100원") and vids[0].split("\n\n")[0] in (H.ig_notes([]), H.DISCLOSURE, H.AFF_NOTE, H.TOSS_NOTE)
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
pj_bak = open("posts.json").read()
json.dump([{"t": "2026-10-05 21:00", "text": "🔥 [G마켓] 어제 (1원)", "url": "https://y", "pop": 99},
           {"t": "2026-10-06 10:00", "text": f"{H.AFF_NOTE}\n\n🔥 [쿠팡] 휴지 30롤 (19,900원/무료)\n\n싸요", "url": "https://c", "pop": 22, "vpm": 17.0, "rec": 1, "hot": "뽐뿌 추천 3"},
           {"t": "2026-10-06 11:00", "text": "🔥 [G마켓] 우유 (9,900원)", "url": "https://g", "pop": 18.5}, {"t": "2026-10-06 12:00", "text": "🔥 [G마켓] 반응없음 (1원)", "url": "https://n"}]
          + [{"t": f"2026-10-06 13:0{k}", "text": f"🔥 [G마켓] 작은{k} (1원)", "url": "https://s", "pop": k + 1, "vpm": k + 1.0} for k in range(4)], open("posts.json", "w"), ensure_ascii=False)
time.time = lambda: NOW; H.report(seen)  # 22:20 (18시 회차는 실행이 없어 건너뜀 -> 22시 회차 1번만)
open("posts.json", "w").write(pj_bak)
assert "\n\n🏆 오늘 반응 TOP5 (게시 때 뽐뿌·클리앙)\n  · 분당 조회 17회 · 추천 1 — 휴지 30롤 🏆\n  · 반응 18.5 — 우유\n  · 분당 조회 4회 — 작은3\n" in sent[-1][1]["text"]  # 오늘 딜만, 반응 높은 순 5개(10/9 진우 '반응 수치 한눈에')
assert "작은0" not in sent[-1][1]["text"] and "어제" not in sent[-1][1]["text"] and "반응없음" not in sent[-1][1]["text"]
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
# 9-7) 밤 미리보기(10/11 진우 '묶음 리스트도, 꾸준함이 중요'): 매일 밤 10시 '🌙 오늘 밤 특가 미리보기' 1번 — 진우 예약 딜(링크 있는 deal)만, 지금~다음 날 8시, 이미 나간 것·토스 API 이름 예약·딜 아닌 예약 X,
#      시간표(시각·아이콘·짧은 이름 링크·가격·'같은 상품' 쿠팡 차이만), 대가성 문구 맨 앞, 묶음 간격(BUNDLE_GAP)·시간당 상한은 안 봄, 23시 넘으면 X, 3개 미만이면 21시 모아보기에 합침
#      Threads = 앞 5개(약한 딜 뒤로) + 전체 목록 링크(채널 글), 500자
D7 = "2026-10-14"
EV7 = [{"at": f"{D7} 21:50", "text": "🔥 <b>[토스] 지난 딜 (1,000원)</b>", "url": "https://toss.shopping/_m/p0", "button": "b", "deal": True},
       {"at": f"{D7} 22:20", "text": "🔥 <b>[토스] 메르헨트 어성초 히알루론산 폼클렌징 500ml 2개 (11,900원)</b>\n\n토스 최대할인가\n💡 쿠팡 같은 상품(15,350원)보다 3,450원 쌈", "url": "https://toss.shopping/_m/a", "button": "b", "deal": True},
       {"at": f"{D7} 22:30", "text": "🔥 <b>[토스] 선크림 70ml 2개 (8,300원)</b>\n\n💡 단위가격: 10ml당 593원 — 쿠팡 톤업 선크림(12,300원)보다 ml당 33% 쌈 (다른 이름이라 참고)", "url": "https://toss.shopping/_m/b", "button": "b", "deal": True},
       {"at": f"{D7} 22:40", "text": "🔥 <b>[토스] 쿠팡 비슷한 히터 (39,900원)</b>\n\n💡 쿠팡 비슷한 상품(49,900원)보다 10,000원 쌈", "url": "https://toss.shopping/_m/c", "button": "b", "deal": True},
       {"at": f"{D7} 23:00", "text": "🛒 <b>[토스] 약한 리무버 (12,900원)</b>\n\n🤔 솔직히 특가로는 약한 제품", "url": "https://toss.shopping/_m/d", "button": "b", "deal": True},
       {"at": f"{D7} 23:10", "text": "🔥 <b>[쿠팡] 휴지 30롤 (9,900원/무료)</b>", "url": "https://link.coupang.com/a/e", "button": "b", "deal": True},
       {"at": f"{D7} 23:20", "text": "🔥 <b>[토스] 여섯째 (5,000원)</b>", "url": "https://toss.shopping/_m/f", "button": "b", "deal": True},
       {"at": f"{D7} 23:30", "name": "토스 API 이름 예약", "api": True},
       {"at": f"{D7} 23:35", "text": "🔥 <b>[토스] API 링크 붙은 예약 (1,000원)</b>", "url": "https://toss.shopping/_m/api", "button": "b", "deal": True, "api": True},
       {"at": f"{D7} 22:45", "text": "🔥 <b>[토스] 이미 나간 예약 (1,000원)</b>", "url": "https://toss.shopping/_m/gone", "button": "b", "deal": True},
       {"at": f"{D7} 23:40", "text": "📢 행사 안내", "url": "https://x", "button": "b"},
       {"at": "2026-10-15 07:50", "text": "🔥 <b>[토스] 아침 딜 (3,000원)</b>", "url": "https://toss.shopping/_m/g", "button": "b", "deal": True},
       {"at": "2026-10-15 08:00", "text": "🔥 <b>[토스] 8시 딜 (3,000원)</b>", "url": "https://toss.shopping/_m/h", "button": "b", "deal": True}]
ev7 = open("events.json").read() if os.path.exists("events.json") else None
json.dump(EV7, open("events.json", "w"), ensure_ascii=False)
sent7, th7 = [], []
H.tg = lambda m, **p: sent7.append((m, p)) or {"message_id": 777}
def http7(url, body=None, headers=None, method=None):
    th7.append(url)
    if "/me?" in url: return json.dumps({"id": "9"})
    if "/threads?" in url or "/threads_publish?" in url: return json.dumps({"id": "c7"})
    raise AssertionError(url)
H.http, H.E["THREADS_TOKEN"], H.time.sleep, tt7 = http7, "tk", (lambda s: None), time.time
at7 = lambda t, step=None, sv=None: (time.__setattr__("time", lambda: TK(f"{D7} {t}")), sent7.clear(), th7.clear(), (step or H.preview)(sv if sv is not None else seen7))
seen7 = {f"ev_{D7} 21:50": 1, f"ev_{D7} 22:45": 1}
at7("21:59"); assert not sent7 and not seen7.get(f"preview_{D7.replace('-', '')}")  # 10시 전
seen7["bundles"] = {"t": TK(f"{D7} 21:55"), "ts": [TK(f"{D7} 21:55")]}; at7("22:03"); assert not sent7  # 묶음 글 10분 안 -> 다음 실행에
json.dump([{"t": f"{D7} 22:0{k}", "text": f"🔥 글{k}", "url": ""} for k in range(9)], open("posts.json", "w"))  # 최근 1시간 글 9개(HOUR_CAP 넘음)도
H.tg = lambda m, **p: sent7.append((m, p)) or None; at7("22:05"); assert len(sent7) == 1 and f"preview_{D7.replace('-', '')}" not in seen7 and not th7  # 전송 실패 -> 다음 실행에 다시
H.tg = lambda m, **p: sent7.append((m, p)) or {"message_id": 777}
at7("22:07"); (m, p), = sent7; t7 = p["text"]
assert m == "sendMessage" and p["chat_id"] == H.CHANNEL and p["link_preview_options"] == {"is_disabled": True}  # 시간당 상한 안 봄(하루 1번 고정 글)
assert t7.startswith(f"<i>{H.TOSS_NOTE}</i>\n<i>{H.DISCLOSURE}</i>\n\n🌙 <b>오늘 밤 특가 미리보기</b> (10/14 · 7개)\n"), t7  # 대가성 문구 맨 앞(프로그램마다)
rows7 = t7.split("\n\n")[2].split("\n")
assert [r[:5] for r in rows7] == ["22:20", "22:30", "22:40", "23:00", "23:10", "23:20", "07:50"]  # 시각 순, 지난 것·API 이름 예약·딜 아닌 예약·8시 이후 X
assert rows7[0] == '22:20 🔥 <a href="https://toss.shopping/_m/a">메르헨트 어성초 히알루론산 폼클렌징 500ml…</a> 11,900원 · 💡 쿠팡 같은 상품보다 3,450원 쌈'
assert "쌈" not in rows7[1] and "쌈" not in rows7[2] and rows7[3].startswith("23:00 🛒 ") and rows7[4].endswith("휴지 30롤</a> 9,900원")  # '같은 상품' 비교만 · 약한 딜 🛒 · 배송 꼬리 뺌
assert t7.endswith("🔔 매일 밤 10시 미리보기 · 알림 켜두면 안 놓쳐요") and seen7[f"preview_{D7.replace('-', '')}"]["mid"] == 777 and seen7["bundles"]["ts"][-1] == TK(f"{D7} 22:07")
q7 = urllib.parse.parse_qs(urllib.parse.urlsplit([u for u in th7 if "/9/threads?" in u][0]).query)
tt = q7["text"][0]
assert tt.startswith(H.TOSS_NOTE + "\n" + H.DISCLOSURE + "\n\n🌙 오늘 밤 특가 미리보기 (7개)\n\n22:20 🔥 메르헨트") and len(tt) <= 480 and "toss.shopping" not in tt  # 상품 링크 X
assert [l[:5] for l in tt.split("\n\n")[2].split("\n")] == ["22:20", "22:30", "22:40", "23:10", "23:20", "… 외 2"] and tt.endswith(f"전체 7개·구매 링크 👉 {H.post_url(777)}") and q7["link_attachment"] == [H.post_url(777)]  # 약한 딜 빼고 앞 5개
at7("22:21"); assert not sent7 and not th7  # 하루 1번
json.dump([{"at": f"{D7} 22:{10 + k}", "text": f"🔥 <b>[토스] 아주 긴 상품 이름 {k}번 대용량 기획 세트 묶음 (19,900원)</b>\n\n💡 쿠팡 같은 상품(29,900원)보다 10,000원 쌈", "url": f"https://toss.shopping/_m/L{k}", "deal": True, "button": "b"} for k in range(12)], open("events.json", "w"), ensure_ascii=False)
H.PREVIEW_TH = 20; at7("22:05", sv={}); tl = urllib.parse.parse_qs(urllib.parse.urlsplit([u for u in th7 if "/9/threads?" in u][0]).query)["text"][0]
assert len(tl) <= 480 and tl.endswith(f"전체 12개·구매 링크 👉 {H.post_url(777)}") and tl.startswith(H.TOSS_NOTE) and 1 <= len(re.findall(r"\n22:\d\d ", tl)) < 12; H.PREVIEW_TH = 5  # 길면 줄을 줄여 480자(문구·전체 링크는 그대로)
json.dump(EV7, open("events.json", "w"), ensure_ascii=False)
seen7 = {}; at7("23:01"); assert not sent7  # 23시 넘으면 X(이미 나가기 시작)
json.dump(EV7[:3], open("events.json", "w"), ensure_ascii=False); seen7 = {f"ev_{D7} 21:50": 1}
at7("22:05"); assert not sent7 and seen7[f"preview_{D7.replace('-', '')}"]["n"] == 2  # 3개 미만 -> 21시 모아보기에 합침
json.dump([{"t": f"{D7} 10:00", "text": "🔥 A딜 (15,480원/무료)", "url": "https://a", "s": 7}], open("posts.json", "w"))
H.draft = lambda *a, **k: {"message_id": 1}; dg7 = {}; time.time = lambda: TK(f"{D7} 21:05")
import sys; cm7 = sys.modules.get("cards"); sys.modules["cards"] = type(sys)("cards"); sys.modules["cards"].make = lambda *a, **k: None; sys.modules["cards"].reel = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x"))
H.digest(dg7, json.load(open("posts.json"))); d7 = [p["text"] for m, p in sent7 if m == "sendMessage" and p["chat_id"] == H.CHANNEL][0]
assert "\n\n🌙 <b>오늘 밤 예약 특가</b>\n22:20 🔥 <a href=\"https://toss.shopping/_m/a\">메르헨트" in d7 and "22:30 🔥 " in d7 and "_m/p0" not in d7 and d7.index("🌙") < d7.index("🔎 지난 딜 전체 보기")
sent7.clear(); json.dump(EV7, open("events.json", "w"), ensure_ascii=False); dg7 = {}; H.digest(dg7, json.load(open("posts.json")))
assert "🌙" not in [p["text"] for m, p in sent7 if m == "sendMessage" and p["chat_id"] == H.CHANNEL][0]  # 3개 이상이면 모아보기엔 안 넣음(밤 10시 미리보기)
sys.modules.pop("cards"); cm7 and sys.modules.__setitem__("cards", cm7)
assert "for step in (events, preview, playlist," in inspect.getsource(H.main) and "toss_reopen, preview, ig_cards" in inspect.getsource(H.main)  # 토스 22시 회차보다 먼저 · 실패 알림(Threads)
time.time = tt7; del H.E["THREADS_TOKEN"]
if ev7 is not None: open("events.json", "w").write(ev7)
else: os.remove("events.json")
import subprocess, sys
for tok, host in (("IGAAx", "https://graph.instagram.com/v25.0"), ("EAAx", "https://graph.facebook.com/v25.0"), ("", "https://graph.instagram.com/v25.0")):
    r = subprocess.run([sys.executable, "-c", "import hotdeal; print(hotdeal.IG)"], env={**os.environ, "IG_TOKEN": tok}, cwd=os.path.dirname(os.path.abspath(H.__file__)), capture_output=True, text=True)
    assert r.stdout.strip() == host, (tok, r.stdout, r.stderr[-300:])
print("OK: 모든 셀프체크 통과")
