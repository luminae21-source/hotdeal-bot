"""셀프체크: python test_hotdeal.py  (네트워크·키 불필요)"""
import base64, hashlib, hmac, io, json, os, re, tempfile, time
from urllib.parse import parse_qs, quote, urlsplit
from email.utils import formatdate

os.environ.update(TG_TOKEN="t", TG_ADMIN_ID="42", TG_CHANNEL="@ch", COUPANG_ACCESS_KEY="ak", COUPANG_SECRET_KEY="sk")
import hotdeal as H
tg_real = H.tg  # 진짜 tg(채널 실패 감시 셀프체크 9-7c용)
H.TH_SOLO_MAX, H.TH_SOLO_GAP, H.TH_SOLO_RUN, H.TH_LIST_HOURS, H.TH_TOSS_KINDS, th_strong0 = 99, 0, 3, tuple(range(24)), ("day", "best", "cat", "beauty", "special"), H.th_strong; tlh0 = (12, 15, 18); tbm0, (H.TH_BEAUTY_MIN, H.TH_BEAUTY_MAX) = (H.TH_BEAUTY_MIN, H.TH_BEAUTY_MAX), (0, 99); trn0, (H.TH_REOPEN_NIGHT, H.TH_REOPEN_MORN, H.TH_REOPEN_DAY) = (H.TH_REOPEN_NIGHT, H.TH_REOPEN_MORN, H.TH_REOPEN_DAY), (99, 99, 99); tfill0, H.TH_SOLO_FILL = H.TH_SOLO_FILL, False; tnc0, H.TOSS_NO_CMP = H.TOSS_NO_CMP, False; ttf0, H.TH_TOSS_FILL = H.TH_TOSS_FILL, (); tsh0, H.TOSS_SOLO_HOURS = H.TOSS_SOLO_HOURS, (); tof0, (H.OTHER_MIN, H.OTHER_MAX) = (H.OTHER_MIN, H.OTHER_MAX), (0, 99); mh0, H.METRICS_HOUR = H.METRICS_HOUR, 99; wx0, (H.WEATHER_HOUR, H.SNACK_HOUR, H.DAILY_LOG_HOUR, H.WEATHER_DM, H.WEATHER_BONUS) = (H.WEATHER_HOUR, H.SNACK_HOUR, H.DAILY_LOG_HOUR, H.WEATHER_DM, H.WEATHER_BONUS), (None, None, None, None, 0); H.th_strong = lambda plain: "특가로는 약한 제품" not in plain  # 예전 Threads 셀프체크는 하루·간격 제한 없이 — 리스트 중심(10/11 진우 결정)은 맨 아래 9-9에서
pl0, H.POLL_HOUR = H.POLL_HOUR, None  # 가격 투표(12:30)는 맨 아래 9-13에서만
iga0, H.IG_AUTO = H.IG_AUTO, True  # 예전 인스타 셀프체크는 켠 채로 — 10/17 23시 멈춤(꺼짐)은 맨 아래 9-14에서
sc0, H.SEEN_COLD = H.SEEN_COLD, True  # 예전 셀프체크는 seen.json 없이도 실행 — 캐시 못 받으면 건너뛰기(10/23)는 맨 아래 9-42에서
lab0, H.TH_LINK_AB = H.TH_LINK_AB, False  # 예전 Threads 셀프체크는 링크 위치 A만 — A/B 시험(10/18 18:30)은 맨 아래 9-17에서
vc0, (H.TH_VOICE, H.TH_GAP_JITTER) = (H.TH_VOICE, H.TH_GAP_JITTER), (False, 0)  # 예전 Threads 셀프체크는 지금 틀·45분 그대로 — 사람 느낌 글·간격 흔들기(10/21 밤)는 맨 아래 9-24에서
H.AD_FIRST = ""  # 예전 모양(고지문 첫 줄) 셀프체크는 그대로 — [광고] 첫 줄(10/11 진우 결정)은 맨 아래 9-8에서
AI_PICK = H.ai_pick  # 진짜 함수(아래에서 대부분 가짜로 바꿔 씀)
CPT = lambda s: re.sub(r"⚠️ 결제 전 최종가 \(\d{1,2}/\d{1,2} \d{1,2}시\)", "⚠️ 결제 전 최종가 (시각)", s)  # 쿠팡 몰별 틀 끝 줄 시각(10/22) = 지금 시각이라 비교용으로 감춤

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
assert "📦 쿠팡 🔥\n<b>휴지 30롤</b>\n9,900원 → 100g당 990원 · 무료\n싸다\n⚠️ 확인할 점 쿠폰 &lt;1인 1회&gt;\n⚠️ 결제 전 최종가 (시각)\n\n출처:" in CPT(t2) and "x" not in t2.split("싸다")[1].split("출처")[0].replace("확인", ""), t2  # 10/22 쿠팡 = 몰별 틀(단위가격 -> 가격 줄 '→', 결제 전 줄)
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
assert ms["[토스] 김 (1원)"] == (pp, "💙 토스에서 1원") and ms["[스팀] 게임 (1원)"] == (pp, "🛒 1원 구매하기")  # 토스(쉐어링크 자동 교체가 원글 기준)·모르는 몰은 원글 · 토스 버튼 = 💙(10/22)
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
assert "<b>휴지 30롤</b>\n9,900원 · 무료\n🏆 <b>인기</b> · 뽐뿌에서 지금 많이 보는 글 1위\n싸다" in th and "🏆" not in H.deal_post(d, "싸다")[0], th  # 쿠팡 몰별 틀 = 가격 줄 아래
assert H.title_of(re.sub("<[^>]+>", "", th)) == d["title"]  # 배지가 있어도 사이트 제목은 그대로
assert H.comment_of(re.sub("<[^>]+>", "", th)).split("\n")[0] == "싸다" == H.comment_of(re.sub("<[^>]+>", "", H.deal_post(d, "싸다")[0])).split("\n")[0]  # 배지 줄은 코멘트 아님(릴스·Threads·블로그·TOP5) — 쿠팡 몰별 틀은 아래 ⚠️ 결제 전 줄
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
assert cp["reply_markup"]["inline_keyboard"] == [[{"text": "📦 쿠팡에서 보기", "url": "https://link.coupang.com/a/xyz"}]]  # 쿠팡 링크 = 🚀 버튼(가격 모름 = 보기, 10/22)
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
assert len(ch) == 4 and "📦 쿠팡 🔥\n<b>오점 계란</b>\n7,990원\n괜찮음\n⚠️ 결제 전 최종가 (시각)" in CPT(ch[3]["text"]) and "채널실패" in ch[1]["text"] and CPT(ch[2]["text"]) == f"<i>{H.DISCLOSURE}</i>\n\n📦 쿠팡 🛒\n<b>약한 키보드</b>\n77,900원\n🤔 솔직히 특가로는 약한 제품\n평소 가격\n⚠️ 결제 전 최종가 (시각)" and CPT(ch[0]["text"]) == f"<i>{H.DISCLOSURE}</i>\n\n📦 쿠팡 🔥\n<b>이트로이 27인치 모니터</b>\n103,770원 → 1인치당 3,843원\n27인치 100Hz가 10만 원대\n⚠️ 확인할 점 휴일특가 끝나면 오름\n⚠️ 결제 전 최종가 (시각)", ch  # 10/22 쿠팡 몰별 틀
assert ch[0]["reply_markup"]["inline_keyboard"] == [[{"text": "📦 쿠팡에서 103,770원", "url": CPL}]]  # 끝 가격을 (가격)으로 묶어 버튼·사이트가 가격을 읽음(10/11) · 쿠팡 = 🚀 버튼(10/22)
assert asked3[0][0].startswith(H.ADMIN_PROMPT) and "comment·who·use 말투 — 말투 = " in asked3[0][0] and asked3[0][1] == ["[운영자] [쿠팡] 이트로이 27인치 모니터 (103,770원) |  | 0분 전 | 휴일특가"] and len(asked3) == 5 and "지어내지 마" in H.ADMIN_PROMPT and "반드시 반환" in H.ADMIN_PROMPT and "5점 미만은 반환하지 마" not in H.ADMIN_PROMPT
pj3 = json.load(open("posts.json"))
assert len(pj3) == n3 + 3 and pj3[-2]["s"] == 4 and pj3[-2]["url"].endswith("new4") and pj3[-3]["url"] == CPL and pj3[-3]["mid"] == 300 and pj3[-3]["s"] == 7 and pj3[-3]["e"] == "🖥️" and pj3[-3]["unit"] == "1인치당 3,843원"
assert [x.get("reply_parameters", {}).get("message_id") for x in ad] == [70, 71, 72, None, None, None, 76, 77] and ad[6]["text"] == "✅ 채널에 올림 (Claude 4점 · 특가로는 약함 표시)"  # 올림 안내·이미 올림·iframe 안내·오류/일반 주소/채널 실패 -> 초안
assert ad[0]["text"] == "✅ 채널에 올림 (Claude 7점)" and ad[0]["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://t.me/ch/300" and "이미" in ad[1]["text"] and ad[2]["text"].startswith("iframe 말고")
assert ad[4]["text"] == "🔥 <b>[G마켓] 일반2</b>" and "채널실패" in ad[5]["text"]   # 제휴 링크 아니면 Claude 안 부름
assert CPT(ad[3]["text"]) == f"<i>{H.DISCLOSURE}</i>\n\n📦 쿠팡 🔥\n<b>에러 상품</b>\n1,000원\n⚠️ 결제 전 최종가 (시각)" and ad[3]["reply_markup"]["inline_keyboard"][0][0]["text"] == "📦 쿠팡에서 1,000원" and ad[3]["reply_markup"]["inline_keyboard"][1][0]["callback_data"] == "ok", ad[3]
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
H.threads_deals({})  # ③ Threads: 진우 딜은 점수와 상관없이, 문구 맨 앞, 링크 = 텔레그램 버튼과 같은 진우 링크(10/19 진우 '경유 말고 직접')
assert len(th4) == 2 and th4[0].startswith(H.NAVER_NOTE + "\n\n") and "🔥 [네이버] 삼다수 2L 24병 (12,900원/무료)" in th4[0] and f"👉 {NV}\n" in th4[0] and th4[1].startswith(H.OY_NOTE + "\n\n") and f"👉 {OYL}\n" in th4[1] and not any("/p/" in t for t in th4)
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
assert ed[0]["reply_markup"]["inline_keyboard"] == [[{"text": "📦 쿠팡에서 보기", "url": "https://link.coupang.com/a/zz"}]]  # 쿠팡 = 🚀 버튼(10/22, 예전 틀 글은 본문 그대로)
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
bd6, ok6 = [], H.http; H.http = lambda url, body=None, headers=None, method=None: bd6.append(body) or ok6(url, body, headers, method)
AI_PICK("p", ["a", "b"]); assert bd6[0]["max_tokens"] == 8000  # 10/19 17:23 커뮤니티 글 많은 회차에 4000으로 picks 잘림 -> 8000
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
# 4-5) 꾸준히(MIN_SCORE를 7로 올렸을 때): 마지막 딜 글이 45분(0~8시는 90분 — 10/22 진우 '새벽에도') 넘으면 7점이 없어도 6점 최고 1개 / 그 안이거나 최고가 5점이면 안 올림
assert H.MIN_SCORE == 6 and H.FILL_SCORE == 6  # 10/8 진우: 기본은 6점도 바로
H.MIN_SCORE = 7
H.ai_pick = lambda prompt, lines: [{"i": 0, "score": 5, "comment": "c"}, {"i": 1, "score": 6, "comment": "c"}, {"i": 2, "score": 6, "comment": "c"}][:len(lines)]
tq, kfmt, pa2 = time.time, lambda s: time.strftime("%Y-%m-%d %H:%M", time.gmtime(s + 9 * 3600)), H.publish_approved
H.publish_approved = lambda seen=None: None  # 앞 테스트의 텔레그램 입력(✅)이 글을 기록하지 않게
for now, last, picks5, want in ((1791248400, 1791248400 - 3600, False, ["ruliweb_91"]), (1791248400, 1791248400 - 1200, False, []),
                                (1791223200, 1791223200 - 7200, False, ["ruliweb_91"]), (1791223200, 1791223200 - 3600, False, []), (1791248400, 1791248400 - 3600, True, [])):  # 10/6 10:00 / 03:00 KST(밤 2시간 = 1개 · 1시간 = 아직)
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
# 4-7) 3사 위주(10/14 23:55 진우 '토스·쿠팡·네이버 위주'): 3사 = 예전 규칙(6점↑), 그 밖의 몰 = 8점↑·KST 하루 3개(진우 예약 글은 안 셈), 못 미치면 보관도 X(보관 중이던 것도)
H.OTHER_MIN, H.OTHER_MAX = tof0
assert H.focus("[쿠팡] 휴지") and H.focus("[네이버스마트스토어] 귤") and H.focus("[토스쇼핑] 삼겹살") and H.focus("[스마트스토어] 쌀") and not H.focus("[G마켓] 참치") and not H.focus("[올리브영] 립밤") and not H.focus("토스 딜")
H.ai_pick = lambda prompt, lines: [{"i": i, "score": int(re.search(r"점수(\d)", l)[1]), "comment": "c"} for i, l in enumerate(lines)]
feed = '<rss><channel>' + "".join(it(f"[{m}] 상품{k}번 점수{sc} 묶음 / {k},000원", f"https://bbs.ruliweb.com/market/board/1020/read/9{k}", 20) for k, (m, sc) in enumerate((("G마켓", 7), ("G마켓", 8), ("쿠팡", 6)))) + '</channel></rss>'
H.http = lambda url, *a, **k: feed if url == H.RULIWEB_RSS else ""
p47 = [{"t": kfmt(time.time() - 3600 * h), "text": f"🔥 [{m}] 예전{h} (1,000원)", "url": "https://x", **o} for h, m, o in ((1, "G마켓", {}), (2, "롯데온", {}), (3, "G마켓", {"own": 1}), (4, "쿠팡", {}))]
json.dump(p47, open("posts.json", "w"), ensure_ascii=False)  # 오늘 3사 아닌 딜 2개(진우 예약 글·쿠팡은 안 셈) -> 1개 남음
posted.clear(); json.dump({}, open("seen.json", "w")); H.main(); sj = json.load(open("seen.json"))
assert posted == [("ruliweb_91", 8, "c")] and {k for k in sj if k.startswith("hold_")} == {"hold_ruliweb_92"}, (posted, [k for k in sj if k.startswith("hold_")])  # 8점 = 올림 · 3사 6점 = 보관(다음 차례) · 3사 아님 7점 = 버림
json.dump(p47 + [{"t": kfmt(time.time() - 60), "text": "🔥 [G마켓] 상품1번 (1,000원)", "url": "https://y"}], open("posts.json", "w"), ensure_ascii=False)  # 방금 올린 것 = 오늘 3개째
feed = feed.replace("</channel>", it("[롯데온] 상품3번 점수8 묶음 / 3,000원", "https://bbs.ruliweb.com/market/board/1020/read/93", 20) + "</channel>")
sj["hold_ruliweb_97"] = {"t": time.time() - 600, "d": {"id": "ruliweb_97", "title": "[11번가] 수건"}, "p": {"score": 7, "comment": "c"}}  # 예전 규칙으로 보관돼 있던 3사 아닌 7점
json.dump(sj, open("seen.json", "w")); posted.clear(); H.main(); sj = json.load(open("seen.json"))
assert posted == [("ruliweb_92", 6, "c")] and not [k for k in sj if k.startswith("hold_")], (posted, [k for k in sj if k.startswith("hold_")])  # 같은 날 4번째 8점 = 버림 · 보관 7점 = 버림 · 3사 6점 = 올림
H.OTHER_MIN, H.OTHER_MAX = 0, 99
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
assert p["reply_markup"]["inline_keyboard"] == [[{"text": "📦 쿠팡 바로가기", "url": H.CP_HOME}]] and H.CP_HOME.startswith("https://link.coupang.com/a/")  # 쿠팡 행사 버튼 = 📦(로켓프레시 행사만 🚀 — 10/23)
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
assert sent[0][1]["reply_markup"]["inline_keyboard"][0][0] == {"text": "🚀 쿠팡 바로가기", "url": H.CP_FRESH} and "ppomppu_9" in seen and "ppomppu_10" not in seen  # 행사로 올린 글은 딜로 또 안 올림
open("posts.json", "w").write(pjb)
assert "goldbox, lambda s: cp_events(s, deals), top_deals, steady_list, weather_post, snack_post, poll_post, toss_deals" in inspect.getsource(H.main)
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
assert offered == ["카테21 | 7,900원 (0% 할인)", "카테22 | 7,900원 (0% 할인)"] and len(prompts) == 1 and prompts[0].startswith(H.BEST_PROMPT) and "말투 — " in prompts[0]
assert "tosscat_20261006_17" in seen and "tb_21" in seen and "tb_22" in seen
sent.clear(); H.toss_deals(seen, "cat"); assert not sent  # 하루 1번
time.time, cats_called[:] = (lambda: 1791274200 + 86400), []; H.toss_deals(seen, "cat"); assert cats_called == [200, 300, 100]  # 다음 날은 패션(날마다 돌아감)
sent.clear(); cats_called[:] = []; time.time = lambda: 1791265800; H.toss_deals(seen, "beauty"); assert not sent and not cats_called  # 10/11 '화장품도': 10/6 14:50 = 15시 전
H.http = lambda url, *a, **k: (cats_called.append(400) or json.dumps({"resultType": "SUCCESS", "success": {"items": [{"tacaItemId": 41, "displayName": "뷰티41", "displayPrice": 9900, "isSoldOut": False}]}})
                               if "/best-categories/400" in url else cat_http(url, *a, **k))
pk2, H.ai_pick = H.ai_pick, (lambda prompt, lines: prompts.append(prompt) or [{"i": 0, "score": 8, "comment": "단위가격 좋음"}])
time.time = lambda: 1791267000; H.toss_deals(seen, "beauty"); t = sent[-1][1]["text"]; H.http, H.ai_pick = cat_http, pk2  # 15:10: 뷰티 카테고리만(식품·생활용품·돌아가는 칸 X)
assert cats_called == [400] and "💙 <b>토스 뷰티 베스트 중 살 만한" in t and "tossbeauty_20261006_15" in seen and "화장품 효능" in prompts[-1]
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
           {"t": "2026-10-06 11:10", "text": f"{cn}\n\n🔥 [쿠팡] 라면 (9,000원)\n\n네이버 멤버십 무배 · 1인 1개", "url": "https://link.coupang.com/a/y", "mid": 4, "pop": 1},
           {"t": "2026-10-06 11:20", "text": "🔥 [G마켓] 사본만 (1,000원)", "url": "https://g1", "mid": None, "pop": 80},  # 채널에 안 나감
           {"t": "2026-10-06 11:30", "text": "🔥 [쿠팡] 골드박스 (1,000원)", "url": "https://link.coupang.com/a/z", "mid": 5},  # 반응 수치 없음
           {"t": "2026-10-06 12:30", "text": "🔥 [G마켓] 오후1 (1,000원)", "url": "https://g2", "mid": 6, "pop": 70},
           {"t": "2026-10-06 13:00", "text": "🔥 [G마켓] 오후2 (2,000원)", "url": "https://g3", "mid": 7, "pop": 5},
           {"t": "2026-10-06 14:00", "text": "🔥 [G마켓] 오후3 (3,000원)", "url": "https://g4", "mid": 8, "pop": 6},
           {"t": "2026-10-06 18:00", "text": "🔥 [G마켓] 저녁 (3,000원)", "url": "https://g5", "mid": 10, "pop": 90}], open("posts.json", "w"))  # 18시 글은 18시 회차 밖
seen, sent[:] = {}, []
time.time = lambda: 1791252000; H.top_deals(seen); assert not sent and not seen  # 11:00 KST: 12시 전
H.TOSS_NO_CMP = True; time.time = lambda: 1791255900; H.top_deals(seen); H.TOSS_NO_CMP = False  # 12:05
m, p = sent[-1]; t = p["text"]
assert m == "sendMessage" and p["chat_id"] == "@ch" and "top_20261006_12" in seen and t.startswith(f"<i>{cn}</i>\n<i>{H.TOSS_NOTE}</i>\n\n🏆 <b>지금 살 만한 딜 TOP4</b> (12시)")
assert t.index("<b>휴지 30롤</b>") < t.index("<b>계란 30구</b>") < t.index("<b>라면</b>") < t.index("<b>우유 24팩</b>") and "어제딜" not in t and "사본만" not in t and "골드박스" not in t and "오후" not in t
assert '1️⃣ <a href="https://link.coupang.com/a/x"><b>휴지 30롤</b></a>\n💰 <b>19,900원</b>\n👀 분당 조회 45회 · 추천 1\n👉 휴지 최저가' in t and "\n👀 반응 30\n" in t  # 반응 수치: 분당 조회·추천 따로, 따로 값이 없는 10/9 첫 배포분은 합친 값
assert '4️⃣ <a href="https://www.ppomppu.co.kr/v?no=1"><b>우유 24팩</b></a>\n💰 <b>12,900원</b> · 개당 537원\n👀 뽐뿌 추천 5\n👉 싸다 우유\n\n⚠️' in t and t.count(cn) == 1  # 수수료 링크 아닌 딜(뽐뿌 원글) = Threads에 나간 딜처럼 뒤로(10/19 밤)
assert [r[0]["text"] for r in p["reply_markup"]["inline_keyboard"]] == ["1️⃣ 휴지 30롤", "2️⃣ 계란 30구", "3️⃣ 라면", "4️⃣ 우유 24팩"]
assert f"(12시)\n{H.TOP_SUB_TOSS}, 그다음" in t and "쿠팡보다" not in t  # 토스 딜이 든 리스트 = 부제에 다른 몰 이름 X(10/14)
assert "<b>라면</b></a>\n💰 <b>9,000원</b>\n👀 반응 1\n👉 1인 1개" in t and "네이버" not in t and t.endswith("\n\n⚠️ 10/6 12:05 게시 시점 가격")  # 토스 딜이 든 리스트 = 👉 줄 다른 몰 이름 조각 빼고, 끝에 게시 시점 줄(10/19 12:30 점검)
sent.clear(); time.time = lambda: 1791256800; H.top_deals(seen); assert not sent  # 같은 회차 1번
time.time = lambda: 1791267000; H.top_deals(seen); t = sent[-1][1]["text"]  # 15:10 -> 12~15시만(10/12 진우 '중간에 리스트도' = 12·15·18시)
sent.clear(); time.time = lambda: 1791277800; H.top_deals(seen); assert not sent and "top_20261006_18" in seen  # 18:10 -> 15~18시 글 없음(18시 글은 다음 회차) -> 안 올림
assert f"(15시)\n{H.TOP_SUB}, 그다음" in t and "TOP3</b> (15시)" in t and t.index("오후1") < t.index("오후3") < t.index("오후2") and "저녁" not in t and "휴지" not in t and not t.startswith("<i>") and "👉" not in t and "게시 시점" not in t  # 코멘트 없으면 👉 줄 X, 토스 딜 없으면 게시 시점 줄 X
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
assert "toss_relink, toss_picks, toss_solo, toss_soldout, toss_fix_channel, lambda s: digest" in inspect.getsource(H.main)
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
BODY2 = H.mall_view(BODY, JIN); assert BODY2 == "💙 토스 특가 🛒\n<b>CJ제일제당 쇠고기 진한다시 1kg</b>\n6,900원\n토스 하루특가 · 30일 내 최저가", BODY2  # 예전 틀 진우 토스 예약 = 보낼 때 몰별 틀(10/22)
assert seen[f"sold_{[p for p in json.load(open('posts.json')) if p.get('t') == '2026-10-11 11:55' and '진한다시' in p['text']][0]['mid']}"]["btn"] == "💙 토스에서 6,900원"  # 품절 지켜보기 = 나간 본문·버튼
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
assert ed[mid]["chat_id"] == H.CHANNEL and ed[mid]["parse_mode"] == "HTML" and ed[mid]["text"] == f"<i>{H.TOSS_NOTE}</i>\n\n⛔ <b>품절</b> — 밤 12시부터 다시 살 수 있어요\n\n{BODY2}"  # 대가성 문구는 그대로 맨 앞, 그 바로 아래 품절 줄
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
assert len(ed) == 1 and ed[0]["text"] == f"<i>{H.TOSS_NOTE}</i>\n\n{BODY2}" and ed[0]["reply_markup"]["inline_keyboard"] == [[{"text": "💙 토스에서 6,900원", "url": JIN}]]  # 품절 줄 지우고 원래대로
assert len(rp) == 1 and rp[0]["reply_parameters"] == {"message_id": mid} and rp[0]["chat_id"] == H.CHANNEL and "1 reopen" in log  # 그 글에 답글 = 알림(원글이 지워졌으면 안 올라감)
assert rp[0]["text"] == f"<i>{H.TOSS_NOTE}</i>\n\n🔔 <b>다시 열렸어요!</b> CJ제일제당 쇠고기 진한다시 1kg — 6,900원" and rp[0]["reply_markup"]["inline_keyboard"] == [[{"text": "💙 토스에서 6,900원", "url": JIN}]]  # 토스 버튼 = 💙(10/22)
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
assert "toss_relink, toss_picks, toss_solo, toss_soldout, toss_fix_channel, lambda s: digest" in inspect.getsource(H.main) and H.SOLD[1][1] == ("⛔ <b>품절</b> — 밤 12시부터 다시 살 수 있어요", "품절 · 밤 12시 재오픈")
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
c_calls.clear(); c_sent.clear(); out = io.StringIO(); tlh_, H.TH_LIST_HOURS = H.TH_LIST_HOURS, tlh0
with contextlib.redirect_stdout(out): H.toss_deals(seen, True)
assert not c_calls and not c_sent and "미룸" in out.getvalue()
assert "busy(seen, cap=not (best is True and \"best\" in TH_TOSS_KINDS and hrs[-1] in TH_LIST_HOURS))" in inspect.getsource(H.toss_deals); H.TH_LIST_HOURS = tlh_  # 12·15·18시 Threads 베스트 리스트는 시간당 상한에 안 막힘(10/12 진우 '묶음 글은 반드시')
time.time = lambda: T("2026-10-12 14:21"); assert not H.busy(seen)  # 1시간 지난 글은 안 셈
json.dump([{"t": "2026-10-12 11:%02d" % (10 + k), "text": f"🔥 [G마켓] 딜{k} (1원)", "url": f"https://g/{k}", "mid": 50 + k, "pop": 9 - k} for k in range(3)], open("posts.json", "w"))
seen, c_sent[:] = {"bundles": {"t": T("2026-10-12 12:01"), "ts": [T("2026-10-12 12:01")]}}, []; time.time = lambda: T("2026-10-12 12:05"); H.top_deals(seen); assert not c_sent and "top_20261012_12" not in seen  # TOP5도 10분 안 묶음 글이면 다음 실행에
seen, c_sent[:] = {}, []; time.time = lambda: T("2026-10-12 12:05"); H.top_deals(seen); H.toss_deals(seen, True)  # 12시: TOP5가 먼저 나가면 같은 실행의 베스트는 다음 실행으로(10/10·10/11 12시 두 글이 18초 간격이던 것)
assert len(c_sent) == 1 and "살 만한 딜 TOP3" in c_sent[0][1]["text"] and "tossbest_20261012_12" not in seen
time.time = lambda: T("2026-10-12 12:19"); H.toss_deals(seen, True); assert len(c_sent) == 2 and "tossbest_20261012_12" in seen and "많이 팔리는" in c_sent[1][1]["text"]
seen, c_sent[:] = {}, []; time.time = lambda: T("2026-10-12 19:10"); H.toss_deals(seen, "beauty")  # 19시 뷰티 저녁 회차
assert "tossbeauty_20261012_19" in seen and "💙 <b>토스 뷰티 베스트 중 살 만한 1개</b>" in c_sent[0][1]["text"]
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
assert seen["reopen"]["q"][1]["cmp"].startswith("🤔 솔직히 특가로는 약한 제품 — 쿠팡") and seen["reopen"]["q"][3]["cmp"] == ""
assert [(e["title"], e["warn"]) for e in seen["reopen"]["q"]] == [("탑프룻 망고젤리 망고맛 320g 3개", "⚠️ 확인할 점: 오늘 밤 12시까지"), ("CJ제일제당 쇠고기 진한다시 1kg", ""), ("사바나나 바나나칩 100g 5봉", ""), ("", "")]  # 재오픈 글 제목·⚠️ = 진우 예약 글(줄 세울 때 저장 — 품절 기록은 다시 열리면 지워짐), API 묶음 글은 없음  # 약한 딜 줄도(가격 그대로면 Threads에도 솔직하게), API 묶음 글은 비교 줄 없음
t0 = ro_th[0]["text"][0]
assert t0 == f"{H.TOSS_NOTE}\n\n💙 토스 특가 · 🔔 다시 열렸어요 🔥\n탑프룻 망고젤리 망고맛 320g 3개\n8,900원\n💸 쿠팡보다 1,800원 싸요\n토스 하루특가 · 밤 12시 재오픈\n💡 쿠팡 같은 상품(탑프루츠 주시 젤리 망고 320g 3개 10,700원)보다 1,800원 쌈\n{H.REOPEN_WARN}\n\n👉 {MANGO}\n👋 팔로우하면 매일 이런 가격 비교가 피드에 떠요\n📲 실시간 알림 t.me/hotdeal_pick", t0  # 10/12 00:40 진우: 일반 글과 같은 틀+ 00:55 맨 위 🔔(고지문 → 🔔 다시 열렸어요 → 💸 → 🔥 [토스] 제목 (가격) → 정보 줄 → 💡 → ⚠️ → 👉 → 🙋 → 📲), 예약 글 ⚠️ 줄 ‘오늘 밤 12시까지’는 다음 날 틀려서 기본 문구로
assert ro_th[0]["link_attachment"] == [MANGO] and ro_th[0]["topic_tag"] == ["장보기"] and len(t0) <= 500  # 진우 링크 그대로(미리보기도) · 주제 = 품목 칸(망고젤리 = 식품 -> 장보기, 10/23 진우)
assert sum("/products/today-deals" in c for c in ro_calls) == 1  # 오늘 하루특가 목록(밤 12시 새 목록)은 1번만
assert not ro_run("2026-10-12 00:12") and not ro_th and not [c for c in ro_calls if "detail" in c and "952" in c]  # 10분 안 -> 다음 실행에(상세 조회도 안 함)
ro_fail["pub"] = ('{"error": {"message": "Fatal", "type": "OAuthException", "error_subcode": 4279047}}', False)  # 링크 미리보기 실패(4279047) -> 첨부 없이 1번 더
ro_run("2026-10-12 00:19"); ro_fail["pub"] = None
assert [q.get("link_attachment") for q in ro_th] == [[DASHI], None] and ro_th[0]["text"] == ro_th[1]["text"] and sum("threads_publish" in c for c in ro_calls) == 2
t1 = ro_th[1]["text"][0]  # 가격 바뀜(6,900 -> 6,500원) -> 지금 가격, 쿠팡 비교 줄(🤔) 빠짐, 약한 딜 아이콘 🛒 그대로
assert t1.startswith(f"{H.TOSS_NOTE}\n\n💙 토스 특가 · 🔔 다시 열렸어요 🛒\nCJ제일제당 쇠고기 진한다시 1kg\n6,500원\n토스 하루특가 · 밤 12시 재오픈\n{H.REOPEN_WARN}\n\n👉 " + DASHI) and "💸" not in t1 and "쿠팡" not in t1 and "6,900" not in t1 and t1.startswith(H.TOSS_NOTE)
ro_run("2026-10-12 00:33"); t2 = ro_th[0]["text"][0]  # 오늘 하루특가 목록에 없음 -> '하루특가·선착순' 빠짐, 가격 그대로면 쿠팡 비교 줄은 있음
assert t2 == f"{H.TOSS_NOTE}\n\n💙 토스 특가 · 🔔 다시 열렸어요 🔥\n사바나나 바나나칩 100g 5봉\n10,000원\n밤 12시 재오픈\n💡 단위가격: 100g당 2,000원 — 쿠팡 같은 상품 8봉(23,650원, 100g당 2,956원)보다 g당 32% 쌈\n{H.REOPEN_WARN}\n\n👉 {BANANA}\n👋 팔로우하면 매일 이런 가격 비교가 피드에 떠요\n📲 실시간 알림 t.me/hotdeal_pick", t2  # 원 단위 차이가 없으면 💸 줄 없음
assert not [c for c in ro_calls if "today-deals" in c]  # 목록에 없는 상품이어도 2시간 안엔 목록 다시 안 받음
assert not ro_run("2026-10-12 00:47") and not ro_th and not ro_calls  # 1시간 3개(00:05·00:19·00:33) -> 넘친 건 다음 실행에(API도 안 부름)
ro_run("2026-10-12 01:06"); t3 = ro_th[0]["text"][0]
assert f"{H.TOSS_NOTE}\n\n💙 토스 특가 · 🔔 다시 열렸어요 🔥\n토스 하루특가 API 상품\n1,000원\n토스 하루특가 · 밤 12시 재오픈\n{H.REOPEN_WARN}\n\n👉 https://toss.shopping/_m/A960" in t3  # API 묶음 글 상품 = 그 글의 쉐어링크, 쿠팡 비교 없음
assert not ro_run("2026-10-12 03:00") and not ro_th and not ro_calls  # 밤에 다 올렸으면 아침까지 조용
ro_fail["detail"] = 1; assert "toss reopen detail" in ro_run("2026-10-12 08:02", ("toss_reopen",)) and not ro_th and len(seen["reopen"]["q"]) == 4  # 상세 조회 실패(터널) -> 다음 실행에(Threads 실패 알림 아님)
ro_out.add(951); ro_price[952] = 12000  # 아침: 진한다시 다시 품절, 바나나칩은 올린 가격(10,000원)보다 비싸짐(특가 끝)
seen["bundles"] = {"t": T("2026-10-12 08:01"), "ts": [T("2026-10-12 08:01")]}  # 08:01에 토스 묶음 글(채널·Threads) -> 10분 띄움
assert not ro_run("2026-10-12 08:05", ("toss_reopen",)) and not ro_th
ro_run("2026-10-12 08:15", ("toss_reopen",)); t4 = ro_th[0]["text"][0]  # ② 8시 지나 첫 실행: 같은 상품 다시 확인 -> 아직 살 수 있으면 '아침 재알림'(밤 글과 다른 문구)
assert t4 == f"{H.TOSS_NOTE}\n\n💙 토스 특가 · 🔔 다시 열렸어요 · 아침 재알림 🔥\n탑프룻 망고젤리 망고맛 320g 3개\n8,900원\n💸 쿠팡보다 1,800원 싸요\n토스 하루특가 · 밤 12시 재오픈 · 아침에도 살 수 있어요\n💡 쿠팡 같은 상품(탑프루츠 주시 젤리 망고 320g 3개 10,700원)보다 1,800원 쌈\n{H.REOPEN_WARN}\n\n👉 {MANGO}\n👋 팔로우하면 매일 이런 가격 비교가 피드에 떠요\n📲 실시간 알림 t.me/hotdeal_pick", t4  # 아침 8시 재알림도 같은 틀(같은 상품 두 번째 글이라 🔔·정보 줄 끝만 다르게 — 스팸 표시 위험)
rt9 = {}; json.dump([{"t": "2026-10-11 21:10", "url": "https://toss.shopping/_m/W", "own": 1, "text": f"{H.TOSS_NOTE}\n\n🔥 [토스] 해피달링 온오프 필터 샤워기 헤드 + 필터 5개 세트 (7,620원)\n\n토스 하루특가 · 무료배송\n💡 쿠팡 같은 상품(14,900원)보다 7,280원 쌈\n⚠️ 확인할 점: 1인 1개 · 필터 규격 확인"}], open("posts.json", "w"), ensure_ascii=False)
rt = H.reopen_text(rt9, {"url": "https://toss.shopping/_m/W", "n": "해피달링 온오프 필터 샤워기 헤드 + 필터 5개, 1세트", "icon": "🔥", "cmp": "💡 쿠팡 같은 상품(14,900원)보다 7,280원 쌈", "p0": 7620}, 7620, False, False)  # 배포 전에 줄 선 것(제목·⚠️ 없음) = posts.json 진우 글에서
assert rt == f"{H.TOSS_NOTE}\n\n💙 토스 특가 · 🔔 다시 열렸어요 🔥\n해피달링 온오프 필터 샤워기 헤드 + 필터 5개 세트\n7,620원\n💸 쿠팡보다 7,280원 싸요\n밤 12시 재오픈\n💡 쿠팡 같은 상품(14,900원)보다 7,280원 쌈\n⚠️ 확인할 점: 1인 1개 · 필터 규격 확인\n\n👉 https://toss.shopping/_m/W\n👋 팔로우하면 매일 이런 가격 비교가 피드에 떠요\n📲 실시간 알림 t.me/hotdeal_pick", rt  # 진우 0:02 글을 새 틀로(예약 글 ⚠️ 줄 그대로)
assert not rt.startswith("[광고]") and H.th_tier(rt) == 1  # 고지문 첫 줄([광고] 접두 없이, 10/12 00:40), 💡 같은 상품 = ①
rt = H.reopen_text(rt9, {"url": "https://toss.shopping/_m/W", "n": "x", "title": "해피달링 샤워기", "warn": "⚠️ 확인할 점: 1인 1개", "icon": "🔥", "cmp": "💡 쿠팡 같은 상품(14,900원)보다 7,280원 쌈", "p0": 7620}, 6900, True, True)
assert rt.startswith(f"{H.TOSS_NOTE}\n\n💙 토스 특가 · 🔔 다시 열렸어요 · 아침 재알림 🔥\n해피달링 샤워기\n6,900원\n토스 하루특가 · 밤 12시 재오픈 · 아침에도 살 수 있어요\n⚠️ 확인할 점: 1인 1개") and "💸" not in rt and "💡" not in rt  # 가격 바뀜 -> 💸·💡 빠짐, 지금 가격
rt = H.reopen_text(rt9, {"url": "https://toss.shopping/_m/P", "n": "y", "title": "아주 긴 이름 " * 12, "warn": "", "icon": "🔥", "cmp": "💡 " + "가" * 118, "p0": 9}, 9, False, True)
assert len(rt) <= 500 and "\n9원\n" in rt and rt.endswith("📲 실시간 알림 t.me/hotdeal_pick")  # 긴 이름·비교 줄도 500자 안(가운데만 자름), ⚠️ 없으면 기본 문구
assert t4 != t0 and [e["id"] for e in seen["reopen"]["q"]] == [960]  # 품절(진한다시)·비싸짐(바나나칩)은 아침 글 없이 끝
ro_run("2026-10-12 08:29", ("toss_reopen",)); assert len(ro_th) == 1 and ro_th[0]["text"][0].startswith(f"{H.TOSS_NOTE}\n\n💙 토스 특가 · 🔔 다시 열렸어요 · 아침 재알림 🔥\n토스 하루특가 API 상품\n1,000원") and "A960" in ro_th[0]["text"][0] and not seen["reopen"]["q"]
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
assert len(ro_th) == 1 and MANGO in ro_th[0]["text"][0] and "\n\n💙 토스 특가 · 🔔 다시 열렸어요 🔥\n" in ro_th[0]["text"][0]  # 밤 글은 선착순이라 진우 예약(08:20)이 있어도 그대로
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
assert "toss_soldout, toss_fix_channel, lambda s: digest(s, load(POSTS, [])), cat_fill, threads, threads_deals, daily_post, daily_log, wx_dm, toss_reopen, ig_cards" in inspect.getsource(H.main) and {"threads", "threads_deals", "toss_picks", "toss_reopen", "preview", "th_retry", "ig_cards", "ig_reel", "ig_publish"} <= set(H.ALERT_STEPS) and "step_alert(seen, step, e)" in inspect.getsource(H.main)  # Threads 실패 알림(하루 1번)에 포함
assert (H.TH_REOPEN_GAP, H.TH_REOPEN_HOUR, H.TH_REOPEN_AM) == (600, 3, (6, 11)) and trn0 == (2, 2, 4)  # 10/12 진우: 아침 재알림 6시부터, 재오픈 한도 밤 2·아침 2·하루 4
del H.E["THREADS_TOKEN"]; H.http, H.tg, H.time.sleep, H.HAS_TOSS = ph6, tg8, sl6, False
if os.path.exists("toss.json"): os.remove("toss.json")
time.time = tt

# 5-3h) 토스 '특가' 자동(10/11 진우 '특가 탭 추천 자동으로 찾아줘'·'뺀 것도 자동으로'): API엔 특가 탭·개당 수익·30일 최저가가 없음(문서 확인) ->
#       ① 이름 예약(events.json {"at","name","api": true}): 8시간 전부터 1일 목록(+ Claude가 고른 하위 카테고리 베스트)에서 이름 겹침 -> Claude 8점↑ -> 자동 발급, 못 찾거나 발급 막히면 진우에게 1번 요청,
#          예약 시각에 상세로 지금 가격·품절 재확인 -> 채널(대가성 문구 맨 앞·효능·쿠팡 비교 없음) + Threads, posts.json X, 품절 지켜보기·3일 중복·자동 회차에서 빠짐
#       ② 특가 회차(toss_deals "special", 8·22시 3시간 안): 1일 목록 중 할인 40%↑·리뷰 50개↑ -> 할인 높은 순 30개 상세로 재확인 -> Claude 7점↑ 중 점수 × 개당 수익(가격 × 수수료: 일괄 8%, 11/5~ 5%·하루특가 3%) 높은 순 3개
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
assert p["text"] == f"<i>{H.TOSS_NOTE}</i>\n\n💙 토스 특가 🔥\n<b>에이지랩 달팽이 뮤신 올인원 크림, 50g, 3개 + 선크림 증정</b>\n18,900원 (62%↓) · ⭐ 4.7 (812)\n👉 50g 3개 + 선크림 증정, 리뷰 812개", p["text"]  # 10/22 토스 몰별 틀(출처 모름 = 칸 없이, 🙋·👍 없으면 Claude 한 줄)
assert p["reply_markup"]["inline_keyboard"] == [[{"text": "💙 토스에서 18,900원", "url": "https://toss.shopping/_m/P501"}]] and "쿠팡" not in p["text"]
assert len(sp_th) == 1 and sp_th[0]["text"][0].startswith(H.TOSS_NOTE + "\n\n💙 토스 특가 🔥\n에이지랩") and "🛒 https://toss.shopping/_m/P501" in sp_th[0]["text"][0] and sp_th[0]["link_attachment"] == ["https://toss.shopping/_m/P501"]
w = [v for k, v in seen.items() if k.startswith("sold_")][0]
assert w["k"] == "ev" and w["it"] == [[501, w["n"], 18900, 0, 0, 0]] and w["url"] == "https://toss.shopping/_m/P501" and "tb_501" in seen and seen["bundles"]["ts"]  # 품절 지켜보기·3일 중복·묶음 간격
assert [x["url"] for x in json.load(open("posts.json"))] == ["https://toss.shopping/_m/LXEUUUvn"] and seen["pk_2026-10-11 23:30"]["st"] == "done"  # 사이트·posts.json X(API 상품, 진우 예약 글만)
assert any("토스쇼핑 상품 1개야" in a for a, _ in sp_ai) and "효능" in H.PICK_PROMPT and "쿠팡 등 다른 쇼핑몰 가격 비교 언급 금지" in H.PICK_PROMPT  # 효능·쿠팡 비교 금지
sp_out.add(511); log = sp_run("2026-10-11 23:47")  # 품절이면 안 올림
assert not [p for m, p in sp_sent if p["chat_id"] == H.CHANNEL] and seen["pk_2026-10-11 23:40"]["st"] == "skip" and "품절" in log
assert seen["pk_2026-10-12 07:30"]["id"] == 512 and seen["pickscan"]["plan"] == [410, 4111] and "/products/best-categories/4111?size=100" in sp_calls  # 23:30에 8시간 안에 들어온 내일 예약 = 새 이름만 Claude에 물어 3단계 하위 카테고리까지
assert seen["pickscan"]["names"] == ["에이지랩 스네일 뮤신 브라이트닝 선크림 70ml 4개", "한경희 2단 자동회전 나노 카본히터 Q2000", "화이트벨라 마이크로 니들 패치 12매"]  # 이미 물은 이름은 다시 안 물음
sp_run("2026-10-12 00:01"); (p,) = [p for m, p in sp_sent if p["chat_id"] == H.CHANNEL]  # 못 찾은 히터는 안 올라감(진우에게 이미 요청), 23:55 떡볶이는 00:01 실행에
assert "국물떡볶이" in p["text"] and "💙 토스 특가 · 하루특가 · 밤 12시까지 🔥" in p["text"] and next(v for k, v in seen.items() if k == f"sold_{600 + sp_sent.index(('sendMessage', p)) + 1}")["it"][0][3] == 1  # 오늘 하루특가 목록에 있으면 표시·품절 땐 '밤 12시 재오픈'
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
assert p["text"].startswith(f"<i>{H.TOSS_NOTE}</i>\n\n💙 <b>토스 특가 중 살 만한 2개</b>") and "샴푸" not in p["text"] and "toss_special 3 items 2 picks 2 links" in log, log
assert p["text"].index("전기요") < p["text"].index("휴지")  # 7점 × 89,000원 > 9점 × 9,900원(개당 수익 = 가격 × 일괄 8%)
assert "휴지</b></a>\n⏰ 토스 하루특가 · 밤 12시까지\n💰" in p["text"] and "전기요</b></a>\n💰" in p["text"]  # 오늘 하루특가 상품만 '밤 12시까지'
assert "끝난 상품" not in str(sp_ai) and not [a for a, l in sp_ai if H.TOSS_EASE in a]  # 끝난 하루특가 X · 쿠팡 언급 있는 TOSS_EASE X(진우 '쿠팡 안 씀')
w = next(v for k, v in seen.items() if k.startswith("sold_") and v["k"] == "top")
assert [x[0] for x in w["it"]] == [502, 503] and [x[3] for x in w["it"]] == [0, 1] and "tossspecial_20261012_8" in seen  # 하루특가 목록에 있는 휴지만 품절 땐 '밤 12시 재오픈'
assert len(sp_th) == 1 and sp_th[0]["text"][0].startswith(H.TOSS_NOTE + "\n\n💙 토스 특가 중 살 만한 2개") and "휴지 — 9,900원 (하루특가·밤 12시까지)" in sp_th[0]["text"][0] and "전기요 — 89,000원\n" in sp_th[0]["text"][0] and "샴푸" not in str(sp_ai)  # Threads도, 이름 예약 상품은 Claude 후보에도 없음
e502 = next(x for x in LISTS["/products/best-selling?size=100"] if x["tacaItemId"] == 502); e502["displayPrice"] = 12000  # 11/5~(TOSS_FEE_DAY) 개당 수익 = 기본 5%·하루특가(선착순특가) 3%: 전기요 7 × 12,000 × 5% > 휴지 9 × 9,900 × 3% (일괄 8%면 휴지 먼저)
for fd, first in (("2026-11-05", "휴지"), ("2026-10-12", "전기요")):
    H.TOSS_FEE_DAY = fd; seen = {"tb_508": {"t": T("2026-10-12 07:00"), "n": "x"}, "pk_2026-10-12 12:30": {"t": T("2026-10-12 07:00"), "id": 506, "n": "x"}}; sp_run("2026-10-12 08:05", lambda s: H.toss_deals(s, "special"))
    (m, p), = [(m, p) for m, p in sp_sent if p["chat_id"] == H.CHANNEL]; assert p["text"].index(first) < p["text"].index({"휴지": "전기요", "전기요": "휴지"}[first]), (fd, p["text"])
H.TOSS_FEE_DAY = "2026-11-05"; e502["displayPrice"] = 89000
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
assert 'lambda s: toss_deals(s, "special"), toss_wait, toss_relink, toss_picks, toss_solo, toss_soldout' in inspect.getsource(H.main) and H.TOSS_SPECIAL_HOURS == (8, 22) and "효능" in H.SPECIAL_PROMPT and "쿠팡 등 다른 쇼핑몰 가격 비교 언급 금지" in H.SPECIAL_PROMPT
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
assert 'href="https://hotdealpick.kr/p/3.html"' in top and 'aria-label="1번 [G마켓] 첫딜 (2,000원) 구매하러 가기"' in top and idx.index('id="today"') < idx.index('id="d0"')
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
assert re.findall(r'<a href="([^"]*)" class="k-\w+"><i><svg viewBox="0 0 24 24" aria-hidden="true">.*?</svg></i>([^<]+)</a>', bar) == [("#toss", "토스"), ("#coupang", "쿠팡"), ("#cats", "품목"), ("#today", "카드"), ("#days", "전체")]  # (10/23 품목 = 7칸을 한 탭에 — 생수·라면 = 식품) 반응 딜·네이버 딜 없음 -> 그 버튼 없음, 홈 안에선 #칸만, 아이콘 = 선 아이콘(이모지 X)
assert "fbclid" in S.PANE_JS and "ig&&t&&t.parentNode||ps[0]" in S.PANE_JS  # 인스타·Threads에서 오면 첫 칸 = 카드 딜(캡션 '맨 위에서 카드 번호')
assert '<nav class="bar" aria-label="바로가기"><a href="https://hotdealpick.kr/#toss" class="k-toss">' in allp  # 지난 딜 전체에선 홈 칸으로
assert idx.count('<div class="pane">') == 5 and idx.index('<div class="pane"><section class="card" id="today"') < idx.index('<div class="pane"><div id="days">') < idx.index('<nav class="bar"') < idx.index(S.PANE_JS)
assert 'href="https://hotdealpick.kr/all.html">지난 딜 전체 보기' in idx.split('id="days"')[1]  # 날짜 탭 대신 '📅 전체' 칸 끝에 지난 딜 링크
d0 = idx.split('id="d0"')[1].split("</section>")[0]
assert "10월 9일 딜 8개" in d0 and d0.count('class="g"') == 8 and "그제딜" not in idx and 'id="d1"' in idx and "어제딜" in idx and 'id="d2"' not in idx
assert d0.index("생수 40병") < d0.index("추가딜4") < d0.index("추가딜0") < d0.index("라면")  # 3사(토스)는 오래됐어도 맨 앞, 나머지는 최신 순(10/15~ 링크프라이스 G마켓도 3사 뒤)
assert '<div class="s">토스쇼핑 · 08:00</div>' in d0 and '<div class="pr">5,900원</div>' in d0 and '<div class="u">병당 148원</div>' in d0 and 'href="https://toss.im/_m/w" rel="nofollow sponsored noopener"' in d0
assert 'class="o" href="https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&amp;no=9"' in d0 and '🔎 같은 상품 찾기' in d0 and 'aria-label="라면 원글에서 구매 링크 보기"' in d0
assert f'class="o" href="https://hotdealpick.kr/p/2.html" aria-label="주소없는딜 자세히 보기">자세히 →' in d0
assert all(f"{w}" in allp for w in ("10월 9일 딜 8개", "10월 8일 딜 1개", "10월 7일 딜 1개")) and 'id="today"' not in allp
# 6-5) 토스 칸(10/9 진우 '쿠팡·토스 주력'): 홈 맨 위 카드 딜 다음 = 최근 2일 커뮤니티 딜 중 토스 쉐어링크 딜(최신 6개) + 텔레그램 토스 추천 버튼,
#      탭 맨 앞 '💙 토스'. 토스 API 상품은 사이트에 안 올림(승인 범위 = 채널·Threads) -> 버튼은 채널 웹 보기로. 지난 딜 전체엔 토스 칸 없음
tsec = idx.split('id="toss"')[1].split("</section>")[0]
assert idx.index('id="toss"') < idx.index('id="today"') < idx.index('id="days"') and "💙 토스 딜 1개" in tsec and S.SHOP_NOTES["toss"] in tsec and tsec.count('class="g"') == 1 and "생수 40병" in tsec
assert f'href="{S.CHANNEL_WEB}"' in tsec and S.CHANNEL_WEB == "https://t.me/s/hotdeal_pick" and 'id="toss"' not in allp
tt = [{"t": f"2026-10-0{d} 1{k}:00", "text": f"🔥 [토스] 토스{d}{k} (1,000원)", "url": f"https://toss.im/_m/{d}{k}", "s": 6} for d in (7, 8, 9) for k in range(4)]
tt += [{"t": "2026-10-09 15:00", "text": "🔥 [토스] 원글토스 (1,000원)", "url": "https://www.ppomppu.co.kr/x", "s": 7},
       {"t": "2026-10-09 15:30", "text": "🔥 [토스] 상품주소토스 (1,000원)", "url": "https://toss.shopping/t/77", "s": 7}]  # 발급 실패로 남은 상품 주소(쉐어링크 아님)
S.build(tt, "docs6"); ts6 = open("docs6/index.html").read().split('id="toss"')[1].split("</section>")[0]
assert ts6.count('class="g"') == 12 and "토스 딜 12개" in ts6 and ts6.index("토스93") < ts6.index("토스90") < ts6.index("토스83") < ts6.index("토스70")  # 10/15: 최근 3일·최대 24개
assert "원글토스" not in ts6 and "상품주소토스" not in ts6  # 쉐어링크 없는 토스 딜 제외
S.build([{"t": "2026-10-06 15:00", "text": "🔥 [토스] 그제토스 (1,000원)", "url": "https://toss.im/_m/z", "s": 7}, {"t": "2026-10-07 15:00", "text": "🔥 [G마켓] 그제 (1,000원)", "url": "https://g", "s": 7},
         {"t": "2026-10-08 15:00", "text": "🔥 [G마켓] 어제 (1,000원)", "url": "https://g", "s": 7},
         {"t": "2026-10-09 15:00", "text": "🔥 [쿠팡] 휴지 (1,000원)", "url": "https://buy", "s": 7}], "docs6")
ts0 = open("docs6/index.html").read().split('id="toss"')[1].split("</section>")[0]
assert 'class="grid"' not in ts0 and "💙 토스 딜</h2>" in ts0 and S.CHANNEL_WEB in ts0  # 최근 3일엔 토스 딜이 없음(나흘 전 딜은 제외) -> 추천 버튼만

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
hot7, life7, beauty7, kit7, lau7 = (i7.split(f'id="{k}"')[1].split("</section>")[0] for k in ("hot", "life", "beauty", "kitchen", "laundry"))
assert i7.index('id="hot"') < i7.index('id="toss"') < i7.index('id="life"') < i7.index('id="beauty"') < i7.index('id="d0"') < i7.index('<nav class="bar"')
assert hot7.count('class="g"') == 2 and hot7.index("폼클렌징") < hot7.index("위생백") and 'class="b4"' not in hot7 and '<b class="b4">🏆 인기</b>' in kit7  # 세제(3일 전)·휴지(4일 전) 제외, 🏆 배지는 인기 칸에선 빼고(제목이 이미 반응 좋은 딜) 다른 칸에선 보임
assert '<div class="rx">👀 분당 25회 · 추천 3</div>' in hot7 and '<div class="rx">👀 반응 12.5</div>' in hot7 and 'class="rx"' not in i7.split('id="hot"')[1].split("</section>", 1)[1]  # 반응 수치는 인기 칸에만(10/9 진우 '반응 수치 확인')
assert life7.count('class="g"') == 2 and life7.index("KF94") < life7.index("샴푸") and "마스크팩" not in life7 and "휴지" not in life7 and "위생백" in kit7 and "세제" in lau7  # 10/24 세분: 위생백 = 주방, 세제 = 세탁
assert beauty7.count('class="g"') == 2 and beauty7.index("마스크팩") < beauty7.index("폼클렌징") and "아이스크림" not in beauty7 and "🧻 생필품 2개</h2>" in life7 and "💄 화장품·뷰티 2개</h2>" in beauty7
assert re.findall(r'<a href="([^"]*)" class="k-\w+"><i><svg[^>]*>.*?</svg></i>([^<]+)</a>', i7.split('<nav class="bar"')[1].split("</nav>")[0]) == [("#hot", "인기"), ("#toss", "토스"), ("#coupang", "쿠팡"), ("#naver", "네이버"), ("#cats", "품목"), ("#days", "전체")]  # 10/23 품목 7칸 = 한 탭(맨 위 칸 바로가기)
assert i7.count('<div class="pane">') == 6 and i7.index('<div class="pane"><section class="day" id="hot"') < i7.index('<div class="pane"><section class="day" id="toss"')  # 첫 칸(인기) = 처음 보이는 칸(10/9 진우 '한 칸씩만')
assert all(i7.count(f'#{k}"') == 2 and i7.index(f'<div class="pane"><section class="day" id="{k}"') < i7.index('<nav class="bar"') for k in ("hot", "toss", "coupang", "naver", "cats"))  # 바 버튼마다 칸이 있음(아래 바 + 앱 안 브라우저 한 줄)
# 6-6b) 3사 탭(10/15 진우 '토스·쿠팡·네이버 탭'): 쿠팡·네이버 칸 = 제목 [몰] 또는 구매 링크 · 최근 3일 · 최신 24개 · 맨 위 그 몰 대가성 문구(hotdeal.py와 같은 글자) · 쿠팡 칸 = 골드박스 버튼
assert S.SHOP_NOTES == {"toss": H.TOSS_NOTE, "coupang": H.DISCLOSURE, "naver": H.NAVER_NOTE}
cp7, nv7 = (i7.split(f'id="{k}"')[1].split("</section>")[0] for k in ("coupang", "naver"))
assert "🚀 쿠팡 딜 1개" in cp7 and "아이스크림" in cp7 and S.SHOP_NOTES["coupang"] in cp7 and f'href="{S.GOLDBOX}"' in cp7 and not re.search("옥션|G마켓|네이버", cp7)
assert "💚 네이버 딜 1개" in nv7 and "폼클렌징" in nv7 and S.SHOP_NOTES["naver"] in nv7 and "아이스크림" not in nv7
assert [S.shop_of({"text": f"🔥 [{m}] x (1원)", "url": u}) for m, u in (("쿠팡와우", ""), ("G마켓", "https://coupa.ng/x"), ("스마트스토어", ""), ("G마켓", "https://smartstore.naver.com/x"), ("토스", ""), ("G마켓", "https://g"))] == ["coupang", "coupang", "naver", "naver", "toss", ""]
assert S.keys({"t": "2026-10-09 10:00", "text": "🔥 [네이버멤버쉽] 휴지 (1원)"}).startswith("네이버 ")
# 10/15 진우 '중복 메뉴니까 다른 메뉴': 검색 칩 = 조건 필터(몰·품목은 탭), 결과 0개 칩은 안 보임
assert [n for _, n in S.CHIPS] == ["💸 1만원 이하", "📉 30일 최저가", "🎁 1+1·증정", "🚚 무료배송", "🍚 식품", "⏰ 오늘 마감"]
assert S.conds({"text": "🔥 [토스] 땅콩버터 (1,950원 · 5천원 쿠폰가)\n\n토스 하루특가 · 30일 내 최저가"}) == "1만원 최저가" and S.conds({"text": "🔥 [롯데온] 생수 (10,000/무료)"}) == "1만원 무배"
assert S.conds({"text": "🔥 [옥션] 잠옷 2+1 (10,010원)"}) == "증정" and S.conds({"text": "🔥 [G마켓] 귤 +500g 증정 (12,000원/무배)\n\n30일 무료반품 · 최저가보상"}) == "증정 무배" and S.price_won("[쿠팡] 휴지 (19,900원/무료)") == 19900
bar0 = S.CSS.split(".bar{", 1)[1].split("}", 1)[0]  # 10/15 진우 '오른쪽으로 밀지 않아도 한 화면에': 가로 스크롤 X — 아래 바 = 넓으면 한 줄·420px 미만 2줄(5+4), 앱 안 위 메뉴 = 5칸씩 2줄(아이콘 위·이름 아래), 칩 = 3열 2줄
assert "overflow-x" not in bar0 and "flex-wrap:wrap;justify-content:center" in bar0 and "white-space:nowrap" in S.CSS and "@media(max-width:419px){.bar a{flex:0 0 calc((100% - 8px)/5);min-height:46px}main:has(.bar){padding-bottom:calc(124px + env(safe-area-inset-bottom))}" in S.CSS
assert ".inapp .bar.top{display:flex;position:sticky;top:env(safe-area-inset-top);z-index:8;flex-wrap:wrap;justify-content:center" in S.CSS and ".find{background:#f4f5f7;padding:8px 0 4px}form.find{position:sticky;top:env(safe-area-inset-top);z-index:8}" in S.CSS  # 10/15 '탭만 고정': 홈 검색창·칩은 스크롤, 딜 페이지 검색창(form)은 고정 그대로 and ".inapp .bar.top a{flex:0 0 calc((100% - 24px)/5);max-width:none;flex-direction:column;min-height:52px" in S.CSS and ".chips{display:grid;grid-template-columns:repeat(3,minmax(0,1fr))" in S.CSS and "overflow-x" not in S.CSS.split(".chips{", 1)[1].split("}", 1)[0]
# 10/13 진우: 앱 안 브라우저(Threads·인스타·페북·카톡·네이버 등)는 아래 고정 바가 앱 툴바에 가림 -> 검색창 아래 sticky 한 줄(같은 아이콘·이름, 가로 스크롤) + 아래 여백, 일반 브라우저는 아래 바 그대로
top7 = i7.split('<nav class="bar top" aria-label="바로가기">')[1].split("</nav>")[0]; bot7 = i7.split('<nav class="bar"')[1].split("</nav>")[0]
assert top7 == bot7.split(">", 1)[1] and i7.index('<div class="find"') < i7.index('<nav class="bar top"') < i7.index('<div class="pane">')  # 같은 메뉴, 검색창(sticky) 안
assert S.INAPP_JS in i7.split("</head>")[0] and all(x in S.INAPP_JS for x in ("Barcelona", "Instagram", "FBAN", "KAKAOTALK", "NAVER\\(inapp")) and "classList.add('inapp')" in S.INAPP_JS
assert ".bar.top{display:none}.inapp .bar:not(.top){display:none}.inapp main,.inapp main:has(.bar){padding-bottom:calc(96px + env(safe-area-inset-bottom))}" in S.CSS and ".inapp .bar.top{display:flex;position:sticky" in S.CSS  # 기본 = 아래 바만, 앱 안 = 위 한 줄만 + 여백
assert 'id="life"' not in a7 and 'id="hot"' not in a7 and "#cats" in a7 and S.PANE_JS not in a7 and 'class="pane"' not in a7  # 지난 딜 전체엔 칸 없음(바는 홈 칸으로)
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
assert br8.count('class="g"') == 3 and br8.index("피죤") < br8.index("자음") < br8.index("탄력") and S.keys(bp[5]) == "쿠팡 생필품 브랜드" and "구운란" not in br8 and '<b class="b1">✅ 본사 정품</b>' in br8 and '<b class="b3">🛒 약한 딜</b>' in br8
assert f'<b class="b2" data-end="{S.end_at(bp[1])}">⏰ 오늘 밤 12시 마감</b>' in i8 and 'data-k="토스 식품 마감"' in i8 and 'data-k="토스 브랜드 무배"' in i8 and ("#brand", "브랜드") in re.findall(r'<a href="([^"]*)" class="k-\w+"><i><svg[^>]*>.*?</svg></i>([^<]+)</a>', i8.split('<nav class="bar"')[1].split("</nav>")[0])
assert all('<div id="qn" class="t" hidden></div></div><nav class="bar top"' in x and S.FIND_JS in x for x in (i8, a8)) and 'data-c="마감"' in i8 and 'data-c="최저가"' not in i8 and f'<nav class="bar top" aria-label="바로가기"><a href="{S.BASE}#' in a8 and i8.index('id="q"') < i8.index('class="pane"') and 'data-c="마감"' in S.FIND and "[hidden]{display:none!important}" in S.CSS
d7m = open("docs7/p/4.html").read()
# 10/13 09:40 진우 '눈에 더 띄게'(구매 버튼은 1순위 그대로): 카테고리 색(인기·토스·생필품·화장품·전체·카드·브랜드) — 딜 페이지 = 연한 박스·3열·색 원 28px, 앱 안 위 줄 = 색 원 22px·40px·선택 칸 꽉 채움, 아래 바 = 아이콘만 색
assert all(f".k-{k}{{--c:{c}" in S.CSS for k, c in (("hot", "#e03131"), ("toss", "#1b64da"), ("life", "#0b7d3e"), ("beauty", "#d6336c"), ("days", "#4e5968"), ("today", "#f59f00"), ("brand", "#7048e8")))
assert ".more{background:#eef4ff;border-radius:16px;padding:14px" in S.CSS and "grid-template-columns:repeat(3,minmax(0,1fr))" in S.CSS and "min-height:52px" in S.CSS and "width:28px;height:28px;border-radius:14px;background:var(--c)" in S.CSS and ".more{background:#15233a}" in S.CSS
assert ".inapp .bar.top i{width:22px;height:22px" in S.CSS and ".inapp .bar.top a[aria-current=true]{background:var(--c);border-color:var(--c);color:var(--t,#fff)}" in S.CSS and ".bar i{display:flex;color:var(--c)}" in S.CSS
assert ".k-today{--c:#f59f00;--t:#191f28}" in S.CSS and ".bar .k-days i{color:#a1a1aa}" in S.CSS  # 대비: 카드 선택 칸 = 어두운 글씨(흰 글씨 2.1), 다크 아래 바 '전체' 아이콘 = 밝게(2.4 -> 7)
assert ".btn{display:flex;align-items:center;justify-content:center;min-height:50px;padding:10px 12px;margin-top:12px;border-radius:12px;background:#1b64da;color:#fff" in S.CSS  # 구매 버튼(파랑) 그대로
assert d7m.index('id="relh"') < d7m.index('<nav class="more" aria-labelledby="moreh"><h2 id="moreh">🔥 다른 특가도 둘러보세요</h2>') < d7m.index('<a class="tg"') and '<nav class="bar' not in d7m  # 딜 페이지 = '같이 보면 좋은 딜' 아래 페이지 안 메뉴(고정 X), 텔레그램 버튼은 그 아래
assert re.findall(r'<a href="([^"]*)" class="k-\w+"><i><svg[^>]*>.*?</svg></i>([^<]+)</a>', d7m.split('<nav class="more"')[1].split("</nav>")[0]) == [(f"{S.BASE}#{k}", n) for k, n in (("hot", "인기"), ("toss", "토스"), ("coupang", "쿠팡"), ("naver", "네이버"), ("life", "생필품"), ("beauty", "화장품"), ("days", "전체 딜 보기"))] and ".more .k-days{grid-column:1/-1}" in S.CSS  # 10/15: 6개 3열 2줄 + 전체 한 줄
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
assert len(sm) == 37 and all(u.findtext(ns + "lastmod") for u in sm) and sm[0].findtext(ns + "lastmod") == "2026-10-09" and sm[1].findtext(ns + "loc") == "https://hotdealpick.kr/c/toilet-paper.html"  # +1 = 화장지 최저가 기록(10/17)
d8 = open("docs8/p/0.html").read()
assert '<meta name="description" content="19,900원 · 롤당 663원 · 쿠팡 · 10/1 게시 · 핫딜픽">' in d8 and "<title>휴지0 30롤 19,900원 (쿠팡) | 핫딜픽</title>" in d8 and 'href="https://hotdealpick.kr/rss.xml"' in d8  # 10/14 '검색 유입': 상품명 가격 (몰), 가격·단위가격·몰·날짜
ld0 = json.loads(d8.split('<script type="application/ld+json">')[1].split("</script>")[0])
assert ld0 == {"@context": "https://schema.org", "@type": "Product", "name": "휴지0 30롤", "offers": {"@type": "Offer", "price": "19900", "priceCurrency": "KRW", "url": "https://hotdealpick.kr/p/0.html"}} and "google-site-verification" not in d8
gv0, S.GOOGLE_VERIFY = S.GOOGLE_VERIFY, "ab\"c"; assert '<meta name="google-site-verification" content="ab&quot;c">' in S.page("t", ""); S.GOOGLE_VERIFY = gv0
assert S.seo(3, {"t": "2026-10-05 09:00", "text": "🔥 [롯데온] 생수 2L 24개 (10,000/무료)\n\n싸요"})[:2] == ("생수 2L 24개 10,000원 (롯데온) | 핫딜픽", "10,000원 · 롯데온 · 10/5 게시 · 핫딜픽")  # '원' 없는 가격
assert S.seo(3, {"t": "2026-10-05 09:00", "text": f"{S.NOTE_STARTS[1]} x\n\n🔥 [토스] 젤리 (</script>)"}) == ("젤리 (</script>) (토스) | 핫딜픽", "토스 · 10/5 게시 · 핫딜픽", "")  # 고지문 X, 가격 못 읽으면 JSON-LD X
i8 = open("docs8/index.html").read(); ld8 = json.loads(i8.split('<script type="application/ld+json">')[1].split("</script>")[0])
assert ld8["@graph"][1]["sameAs"] == [S.INSTA, S.THREADS, S.BLOG, S.CHANNEL] and "<title>핫딜픽 - 오늘의 핫딜·특가 모음 (쿠팡·네이버·토스)</title>" in i8
assert S.summary("🔥 [G마켓] 우유 (1원)") == "" and '<meta name="description" content="1원 · G마켓 · 10/9 게시 · 핫딜픽">' in (S.build([{"t": "2026-10-09 10:00", "text": "🔥 [G마켓] 우유 (1원)", "url": "https://g"}], "docs8") and open("docs8/p/0.html").read())  # 코멘트 없으면 제목
os.makedirs("docs7/cards", exist_ok=True); open("docs7/cards/2026-10-09.png", "wb").write(b"x"); S.build(hp, "docs7"); i7c = open("docs7/index.html").read(); os.remove("docs7/cards/2026-10-09.png")
assert i7c.index('<div class="pane"><section class="day" id="hot"') < i7c.index('<div class="pane"><section class="day" id="toss"') < i7c.index('<div class="pane"><section class="card" id="today"')  # 처음 보이는 칸 = 인기(10/9 진우 선택), 카드 딜은 그다음
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
assert all(f'<meta name="naver-site-verification" content="{v}">' in idx for v in ("31caccebc9de97ffa6547f7d55966278daf9c469", "58af553d8879edfe3bc3a5189d9744ddc33bfcb9"))  # 10/15 네이버 소유확인 2개
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
# 8-1b) 딜 한 장 카드(10/11 진우 '인스타 업그레이드 2번' 넘기기): 1080x1350 JPEG·200KB 미만, 제일 긴 경우(이름 2줄·단위·이유·확인할 점)도 아래 사이트 줄 안 침범,
#       재료(이모지·이유) 없어도 그려짐, 배송비만 있으면 '배송비 N원', 이유 대신 코멘트 문장(🤔 약한 딜 줄 빼고)
from PIL import ImageChops as _C
_long = {"title": "[올리브영] 토리든 다이브인 저분자 히알루론산 세럼 50ml 1+1 기획 세트 아주 긴 이름 (19,900원/3,000원)", "comment": "", "e": "💧",
         "pts": ["1+1 구성이라 개당 9,950원", "평소 단품 가격대보다 낮음", "리뷰 많은 기본 세럼"], "unit": "개당 9,950원", "warn": "기획 구성은 재고 소진 시 종료"}
for _k, _it in enumerate([_long, dict(_long, warn=""), {"title": "[쿠팡] 휴지 (9,900원/무료)"}], 1):
    assert cards.deal_card(_it, _k, 5, f"docs/cards/d{_k}.jpg", why="체크 포인트") == f"docs/cards/d{_k}.jpg"
    _j = _I.open(f"docs/cards/d{_k}.jpg"); assert _j.format == "JPEG" and _j.size == (1080, 1350) and os.path.getsize(f"docs/cards/d{_k}.jpg") < 200_000
    assert not _C.difference(_j.crop((0, 1110, 1080, 1196)), _I.new("RGB", (1080, 86), cards.CREAM)).point(lambda v: 255 if v > 40 else 0).getbbox()  # 내용 끝 ~ 아래 줄(1200) 사이 빈칸
for _t in ("[11번가] 신라면 120g 40개 (티멤 카카오 23,470원/무료)", "[11번가] 신라면 40개 (와우회원 쿠폰적용 카드할인 최종 23,470원/무료)"):  # 앞말 붙은 긴 가격: 가격·알약이 오른쪽 여백 안에(안 되면 알약 아랫줄)
    cards.deal_card({"title": _t}, 1, 5, "docs/cards/dw.jpg"); _j = _I.open("docs/cards/dw.jpg")
    assert not _C.difference(_j.crop((990, 0, 1080, 1180)), _I.new("RGB", (90, 1180), cards.CREAM)).point(lambda v: 255 if v > 40 else 0).getbbox(), _t
assert cards._norm({"title": "[네이버] 햇반 (22,000원/3,000원)"})["ship"] == "배송비 3,000원" and cards._norm({"title": "[쿠팡] 휴지 (9,900원/무료)"})["ship"] == "무료배송"
assert cards._norm({"title": "[쿠팡] 휴지 (9,900원/무료)", "comment": "롤당 330원이에요.\n🤔 다른 날도 비슷한 가격"})["pts"] == ["롤당 330원이에요."]
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
for _m in (rv, rm):  # 인스타 릴스 규격(10/11 릴스 자동): edit list(elst) 없음 · moov가 mdat 앞(바로 재생)
    _b = open(_m, "rb").read(); assert b"elst" not in _b and _b.index(b"moov") < _b.index(b"mdat")
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
json.dump([{"t": f"{today} 10:00", "text": "🔥 A딜 (15,480원/무료)", "url": "https://link.coupang.com/a/A"}], open("posts.json", "w"))
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
seen, calls[:] = {}, []; H.threads(seen); assert th9().startswith(H.DISCLOSURE + "\n\n📋 ")  # 하루 카드 글도 대가성 문구 맨 앞(카드 캡션과 같게)
pj8, oj8 = open("posts.json").read(), f"docs/cards/{today}.json"; os.path.exists(oj8) and os.rename(oj8, "oj8.json")  # 21시 이후면 모아보기 절이 만든 순서 파일 -> 잠깐 치움
json.dump([{"t": f"{today} 1{n}:00", "text": f"🔥 [{m}] 아주 긴 상품 이름 {n}번 대용량 기획 세트 묶음 구성 (9,900원/무료)", "url": u, "s": 8} for n, (m, u) in enumerate(
    [("네이버", "https://naver.me/a"), ("올리브영", "https://oy.run/b"), ("쿠팡", "https://link.coupang.com/a/c"), ("토스", "https://toss.shopping/_m/d"), ("G마켓", "https://click.linkprice.com/x")])], open("posts.json", "w"), ensure_ascii=False)
seen, calls[:] = {}, []; H.threads(seen); t8 = th9()
assert len(t8) <= 480 and t8.startswith(H.NAVER_NOTE + "\n" + H.OY_NOTE + "\n" + H.DISCLOSURE + "\n" + H.TOSS_NOTE + "\n" + H.AFF_NOTE + "\n\n📋 ") and t8.endswith("https://t.me/hotdeal_pick") and 1 <= t8.count("번 대용량") < 5  # 길면 문구 말고 번호 줄을 줄임
ps8 = [{**p, "url": "https://www.ppomppu.co.kr/1"} if k in (0, 2) else p for k, p in enumerate(json.load(open("posts.json")))]; json.dump(ps8, open("posts.json", "w"), ensure_ascii=False)
seen, calls[:] = {}, []; H.threads(seen); t8 = th9()  # 10/19 밤 진우 'Threads는 수수료 딜만': 카드 줄도 수수료 링크 딜만(카드 번호 그대로), 사진·인스타는 그대로
assert re.findall(r"^\d\. .*$", t8, re.M) == [r for r, (_, p) in zip(H.card_caption(today)[0], H.card_order(ps8, today)) if "ppomppu" not in p["url"]] and "[네이버] 아주" not in t8 and "[쿠팡] 아주" not in t8 and "[토스] 아주" in t8
json.dump([{**p, "url": "https://www.ppomppu.co.kr/1"} for p in ps8], open("posts.json", "w"), ensure_ascii=False); seen, calls[:], sent[:], o8 = {}, [], [], io.StringIO()
with contextlib.redirect_stdout(o8): H.threads(seen)
assert [m for m, _ in calls] == ["HEAD"] and sent[-1][0] == "sendPhoto" and "threads skip (수수료 링크 아님) card 묶음 | 항목 0개\n" in o8.getvalue()  # 0개 = Threads 카드 X(관리자 사진은 그대로)
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
           {"t": f"{D9} 10:59", "text": "🔥 [네이버] 햇반 24개 (22,000원/무료)", "url": "https://naver.me/abc", "s": 6},
           {"t": f"{D9} 11:00", "text": "🔥 [옥션] 12시 딜 (1,000원)", "url": "https://www.auction.co.kr/p", "s": 9},
           {"t": f"{D9} 13:00", "text": "🔥 [옥션] 오후 딜 (2,000원)", "url": "https://www.auction.co.kr/q", "s": 7},
           {"t": "2026-10-11 23:00", "text": "🔥 [쿠팡] 어제 딜 (1,000원)", "url": "https://link.coupang.com/a/y", "s": 9},
           *({"t": f"{D9} {h}:00", "text": f"🔥 [옥션] 저녁 딜 {h} (3,000원)", "url": f"https://www.auction.co.kr/e{h}", "s": 5} for h in (16, 17, 18))], open("posts.json", "w"), ensure_ascii=False)
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
H.IG_CAROUSEL, ig9h = False, H.IG_HUMAN; H.IG_HUMAN = False  # 9-1b = 한 장 카드(넘기기 끈 상태 — 되돌리기 스위치), 넘기기는 9-1e · 사람처럼(IG_HUMAN 새 디자인·지연)은 9-33
def at9(t, step=None):
    ig9.clear(); sent.clear(); time.time = lambda: TK(f"{D9} {t}"); (step or H.ig_cards)(seen)
at9("10:50"); assert not ig9 and not seen and not os.path.exists(f"docs/cards/{D9}_11.jpg")  # 첫 칸(11시) 전
at9("11:05"); assert not ig9 and open(f"docs/cards/{D9}_11.jpg", "rb").read(2) == b"\xff\xd8" and not os.path.exists(f"docs/cards/{D9}_11.png") and not os.path.exists(f"docs/cards/{D9}_11")  # 만들기만(HTTP 없음), 진짜 JPEG만, 넘기기 끄면 딜 카드 X
assert json.load(open(f"docs/cards/{D9}_11.json")) == [1, 0, 3, 2] and "igs_" + D9 + "_11" not in seen  # 0~11시 딜만(11:00·어제 딜 X — 10/23 진우 '11시 = 0~11시'), 점수·제휴 먼저
at9("11:19"); assert [m for m, u, b in ig9] == ["HEAD"] and "igs_" + D9 + "_11" not in seen  # 사이트 배포 전 -> 다음 실행에
live9.add(f"{D9}_11.jpg"); at9("11:33")
(m, u, b), = [x for x in ig9 if x[0] == "POST"]
assert u == H.IG + "/178/media" and b["image_url"] == f"https://hotdealpick.kr/cards/{D9}_11.jpg" and seen["igc_IMG1"]["card"] == f"{D9}_11" and "igs_" + D9 + "_11" in seen
import build_site as S9
assert list(json.load(open(H.IG_LIVE))) == [f"{D9}_11"] and S9.card_stems("docs") == [f"{D9}_11"]  # 사이트 맨 위에 먼저(이번 실행 배포)
at9("11:34", H.ig_publish); assert not ig9 and "igc_IMG1" in seen  # 만든 실행엔 발행 X(사이트 먼저) — 상태 조회도 그 뒤(10/23 그래프 API 호출 줄이기) -> 다음 실행에
cap = b["caption"]
assert cap.startswith(H.NAVER_NOTE + "\n" + H.DISCLOSURE + "\n" + H.AFF_NOTE + "\n\n10월 12일 오전 11시 핫딜\n\n1. [G마켓] 토리든 세럼 50ml\n2. [쿠팡] 휴지 30롤\n"), cap  # 대가성 문구 맨 앞(프로그램마다, 네이버·올영 먼저), 번호 줄 = 카드 순서·가격 꼬리 뺌
assert "맨 위 '10월 12일 오전 11시 카드 딜'에서 번호를 누르면 바로 구매 페이지" in cap and cap.endswith("#핫딜 #핫딜픽 #생필품 #화장품 #쟁여템") and "#최저가" not in cap and len(cap) <= 2200
assert H.ig_tags([], 4) == "#핫딜 #핫딜픽 #가성비템 #쟁여템 #장바구니" and len({H.ig_tags([], h // 2) for h in (*H.IG_SLOTS, H.IG_DAY_HOUR)}) == 6  # 10/23 진우 '해시태그 세트도 칸마다 조금씩 다르게' — 기본 2 + 카테고리 + 칸마다 돌린 채움
at9("11:47"); assert not ig9  # 회차마다 1번
sv9 = seen; seen = {}; at9("11:47"); assert not ig9; seen = sv9  # seen 캐시를 잃어도 기록(ig.json, 커밋됨)에 있으면 다시 안 올림
seen9 = dict(seen); seen = {}; at9("12:01"); assert not ig9 and not seen; seen = seen9  # 2시간 지나면 그 회차는 안 함(낮에 몰아 X)
at9("15:05"); assert not ig9 and seen["igs_" + D9 + "_15"]["skip"] == 2 and not os.path.exists(f"docs/cards/{D9}_15.jpg")  # 11~15시 딜 2개 -> 건너뜀(억지로 안 채움)
shutil.copy(f"docs/cards/{D9}_11.jpg", f"docs/cards/{D9}.jpg"); open(f"docs/cards/{D9}.png", "wb").write(b"p"); live9.add(f"{D9}.jpg")
json.dump([4, 1, 0, 5, 2, 3], open(f"docs/cards/{D9}.json", "w"))  # 21시 하루 카드(모아보기가 만듦)
at9("21:59"); assert not [x for x in ig9 if x[0] == "POST"]  # 인스타엔 22시에(10/23 진우)
at9("22:20"); (m, u, b), = [x for x in ig9 if x[0] == "POST"]
assert b["image_url"] == f"https://hotdealpick.kr/cards/{D9}.jpg" and "10월 12일 오늘의 핫딜 모음\n\n1. [옥션] 12시 딜\n" in b["caption"] and "맨 위 '10월 12일 카드 딜'에서 번호를 누르면" in b["caption"]
assert b["caption"].count("\n") and b["caption"].split("\n\n")[2].count("\n") == 4  # 번호 줄은 카드에 든 5개만(CARD_N)
# 발행: 사이트 맨 위 카드 = 인스타에 올라간 카드
assert S9.card_stems("docs") == [f"{D9}_11", D9] and "📸 10월 12일 카드 딜" in S9.card_picks(json.load(open("posts.json")), "docs")  # 발행 전에도 사이트 먼저(컨테이너 만든 실행)
at9("22:34", H.ig_publish)
assert [u.rsplit("/", 1)[-1] for m, u, b in ig9 if u.endswith("media_publish")] == ["media_publish"] * 2 and set(json.load(open(H.IG_LIVE))) == {f"{D9}_11", D9}
assert [p["text"] for m, p in sent] == ["📸 인스타 자동 게시 완료 — 오전 11시 카드 (instagram.com/hotdealpick.kr)", "📸 인스타 자동 게시 완료 — 오늘 카드 (instagram.com/hotdealpick.kr)"]
pk9 = S9.card_picks(json.load(open("posts.json")), "docs")
assert S9.card_stems("docs") == [f"{D9}_11", D9] and "📸 10월 12일 카드 딜" in pk9 and "<details><summary>10월 12일 오전 11시 카드 딜</summary>" in pk9  # 최근 카드 펼침 + 앞 카드 접어서
assert pk9.split("<details>")[0].count('class="pick"') == 5 and pk9.split("<details>")[1].count('class="pick"') == 4  # 하루 카드 5개(CARD_N) · 12시 카드 4개
open(f"docs/cards/{D9}_19.jpg", "wb").write(b"j"); json.dump([5], open(f"docs/cards/{D9}_19.json", "w")); assert S9.card_stems("docs") == [f"{D9}_11", D9]  # 인스타에 안 올라간 카드는 사이트에 안 보임
seen.update({"igc_A": {"t": 1, "card": f"{D9}_19"}}); st9["v"] = "PUBLISHED"; at9("21:48", H.ig_publish)
assert not [1 for m, u, b in ig9 if u.endswith("media_publish")] and "igc_A" not in seen and f"{D9}_19" in json.load(open(H.IG_LIVE)) and sent[-1][1]["text"].startswith("📸 인스타 자동 게시 완료 — 저녁 7시 카드")  # 이미 발행됨 = 게시 완료(다시 발행 X)
st9["v"] = "FINISHED"; seen.update({"igpub_20261012": {"t": 1, "n": 5}, "igc_B": {"t": 1}}); at9("22:00", H.ig_publish); assert "igc_B" in seen and not sent and H.ig_day_max(seen) == 5  # 하루 상한 = 단계 횟수 4 + 1(10/23 진우) -> 다음 날
seen["igpub_20261012"]["n"], st9["spam"] = 0, True  # 10/23 진우: 발행 오류(2207051 포함) -> ig_landed 확인 -> 안 올라감 = 다음 실행에 상태만(다시 발행 X) · 예외·쉼 X
at9("22:14", H.ig_publish); assert seen["igc_B"]["fail"] and "ig_hold" not in seen and len([1 for m, u, b in ig9 if u.endswith("media_publish")]) == 1 and not sent
at9("22:28", H.ig_publish); assert not [1 for m, u, b in ig9 if u.endswith("media_publish")] and "igc_B" not in seen and "ig_hold" not in seen and len(seen["igfail"]["f"]) == 1 and not sent  # 그래도 FINISHED = 진짜 실패 1번 = 그 회차만 건너뜀
seen["igc_B2"] = {"t": 1, "card": f"{D9}_19", "fail": "x"}; seen["igk_K"] = {"t": 1, "kids": ["k1"]}; at9("22:42", H.ig_publish)  # 진짜 실패 하루 2번 = 24시간 쉼 + 관리봇 알림, 남은 컨테이너·조각은 버림
assert seen["ig_hold"] > TK(f"{D9} 22:42") + 86000 and not [k for k in seen if k.startswith(("igc_", "igk_"))] and sent[-1][1]["text"].startswith("⚠️ 인스타 진짜 실패(게시 안 됨) 오늘 2번 — 24시간 쉼, 다시 시도 X"), sent
at9("22:56"); assert not ig9  # 24시간 인스타 쉼(카드 만들기·올리기 X)
sv9 = seen; seen = {"ig_hold": TK(f"{D9} 22:14") + 86400}; os.rename(f"docs/cards/{D9}_11.jpg", "h9.jpg"); at9("11:05"); assert not ig9 and not os.path.exists(f"docs/cards/{D9}_11.jpg"); os.rename("h9.jpg", f"docs/cards/{D9}_11.jpg"); seen = sv9  # 쉬는 동안엔 시간대 카드도 안 만듦
assert S9.card_order(json.load(open("posts.json")), f"{D9}_15") == [] and len(S9.card_order(json.load(open("posts.json")), "2026-10-11")) == 1  # 순서 파일 없는 시간대 카드 = 번호 없음(하루 카드는 그날 딜 순서)
st9.pop("spam"); del seen["ig_hold"]
# 10/23 진우 '다시 시도 X': 발행 오류(인스타 5xx·응답 끊김)도 안 올라갔으면 다음 실행에 상태만 — PUBLISHED = 게시 완료(늦게 올라감), 아니면 진짜 실패(다시 발행 X), 다른 컨테이너는 계속
def ig9e_http(url, body=None, headers=None, method=None):
    if (url.endswith("/media_publish") and st9.get("e500")) or (url.endswith("/178/media") and method == "POST" and st9.get("mk500")):
        ig9.append((method, url, body)); e = urllib.error.HTTPError(url, 500, "x", {}, None); e.body = '{"error":{"is_transient":true}}'; raise e
    return ig9_http(url, body, headers, method)
H.http, st9["e500"] = ig9e_http, True
json.dump({}, open(H.IG_LIVE, "w")); seen = {"igc_C": {"t": 1, "card": f"{D9}_19"}, "igc_R": 1.0}
at9("22:30", H.ig_publish)
assert seen["igc_C"]["fail"] and seen["igc_R"]["fail"] and seen["igc_R"]["t"] == 1.0 and len([1 for m, u, b in ig9 if u.endswith("media_publish")]) == 2 and not sent  # 둘 다 시도(예외 X), 다음 실행에 상태만
st9.pop("e500"); st9["v"] = "PUBLISHED"; at9("22:44", H.ig_publish)
assert not [k for k in seen if k.startswith("igc_")] and not [1 for m, u, b in ig9 if u.endswith("media_publish")] and list(json.load(open(H.IG_LIVE))) == [f"{D9}_19"]
assert [p["text"] for m, p in sent] == ["📸 인스타 자동 게시 완료 — 저녁 7시 카드 (instagram.com/hotdealpick.kr)", "📸 인스타 자동 게시 완료 (instagram.com/hotdealpick.kr)"]  # 늦게 올라감 = 게시 완료(예전 릴스 기록 = 시각만)
st9.update(v="FINISHED", e500=True); seen = {"igc_D": {"t": 1, "card": f"{D9}_19"}}
at9("22:50", H.ig_publish); st9.pop("e500"); at9("23:04", H.ig_publish)
assert "igc_D" not in seen and not [1 for m, u, b in ig9 if u.endswith("media_publish")] and len(seen["igfail"]["f"]) == 1 and "발행" in seen["igfail"]["f"][0] and not sent  # 그래도 안 올라감 = 진짜 실패(다시 발행 X)
st9["v"], seen = "ERROR", {"igc_E": {"t": 1, "card": f"{D9}_19"}}
at9("23:10", H.ig_publish); assert not [k for k in seen if k.startswith("igc_")] and "처리 ERROR" in seen["igfail"]["f"][0] and not sent  # 처리 실패 = 진짜 실패(예외 X, 1번째는 알림 X)
# 컨테이너 만들기 실패: 다시 시도 X(10/23 진우) — 진짜 실패, 그 회차 끝(안 올라간 컨테이너는 안 보임)
st9.update(v="FINISHED", mk500=True); seen = {}; json.dump({}, open(H.IG_LIVE, "w"))
at9("11:40"); assert seen["igs_" + D9 + "_11"]["fail"] == H.IG_TRIES and len(seen["igfail"]["f"]) == 1 and "컨테이너" in seen["igfail"]["f"][0] and not sent
at9("11:54"); assert not ig9 and not json.load(open(H.IG_LIVE))
st9.pop("mk500"); seen = {}; at9("12:36")
assert len([1 for m, u, b in ig9 if m == "POST"]) == 1 and seen["igs_" + D9 + "_11"] == {"t": TK(f"{D9} 12:36")} and list(json.load(open(H.IG_LIVE))) == [f"{D9}_11"]  # 실패 없으면 그대로 1번
# 사이트 맨 위 카드 = 가장 최근 카드부터 24시간 안(다음 날 오전 11시 카드가 올라가도 어제 저녁·밤 카드는 접어서, 딱 24시간 된 어제 오전 11시는 빠짐)
H.ig_live("2026-10-13_11", TK(f"{D9} 23:00")); assert json.load(open(H.IG_LIVE)) == {f"{D9}_11": TK(f"{D9} 12:36"), "2026-10-13_11": TK(f"{D9} 23:00")}  # 기록 = 만든 시각
json.dump({"2026-10-01": TK(f"{D9} 23:00") - 8 * 86400, f"{D9}_11": 1}, open(H.IG_LIVE, "w")); H.ig_live(f"{D9}_19", TK(f"{D9} 23:00")); assert list(json.load(open(H.IG_LIVE))) == [f"{D9}_19"]  # 7일 지난 기록 정리
json.dump({f"{D9}_11": 1, f"{D9}_19": 1, "2026-10-13_11": 1}, open(H.IG_LIVE, "w"))
assert S9.card_stems("docs") == [f"{D9}_19", D9, "2026-10-13_11"]
# 캡션 대가성 문구는 늘 맨 앞: 제휴 링크 없는 카드 = 일반 안내 1줄, 토스·쿠팡 딜 = 올린 뒤 제휴 링크로 바뀔 수 있어서(toss_relink·진우 파트너스 링크) 그 문구 미리
pj = json.load(open("posts.json")); pj.append({"t": f"{D9} 13:30", "text": "🔥 [토스] 김 20봉 (5,000원/무료)", "url": "https://www.ppomppu.co.kr/zboard/view.php?no=9", "s": 7})
json.dump(pj, open("posts.json", "w"), ensure_ascii=False); o9 = next(i for i, p in enumerate(pj) if "오후 딜" in p["text"])
json.dump([o9], open(f"docs/cards/{D9}_19.json", "w"))
assert H.card_caption(f"{D9}_19")[1].startswith("일부 링크는 제휴 링크로 수수료를 받을 수 있어요.\n\n10월 12일 저녁 7시 핫딜\n\n1. [옥션] 오후 딜\n")
json.dump([o9, len(pj) - 1], open(f"docs/cards/{D9}_19.json", "w"))
assert H.card_caption(f"{D9}_19")[1].startswith(H.TOSS_NOTE + "\n\n10월 12일 저녁 7시 핫딜\n") and "제휴 링크로 수수료" not in H.card_caption(f"{D9}_19")[1]
# 9-1e) 인스타 넘기기(10/11 진우 '인스타 업그레이드 2번'): 카드 만들 때 딜마다 1장(docs/cards/날짜_시/01.jpg… = 표지·캡션·사이트 번호 순서, 재료 없는 딜은 Claude로 1번에)
#       -> 올릴 때 표지 + 딜 카드 조각(캡션 X) -> 다 처리되면 묶음(CAROUSEL·캡션·순서 그대로) -> 사이트 먼저 -> 다음 실행에 묶음만 1번 발행
#       조각 처리 중 = 다음 실행에 묶음 / 조각 실패·1시간 넘음 = 버리고 카드 주소 알림 / 올리브영 딜 = '체크 포인트' / 2일 지난 딜 카드 폴더 정리
import cards as C9
dc9, real_dc9, ap9 = [], C9.deal_card, H.ai_pick
C9.deal_card = lambda it, n, total, out, why="살 만한 이유": dc9.append((it["title"], n, total, why, it.get("e"))) or real_dc9(it, n, total, out, why)
fills9 = []; H.ai_pick = lambda prompt, lines: fills9.append((prompt, lines)) or [{"i": 0, "e": "🧴", "hook": "세럼 1+1", "pts": ["50ml 2개"]}]
H.IG_CAROUSEL, H.http, seen, st9["v"] = True, ig9e_http, {}, "FINISHED"
json.dump({}, open(H.IG_LIVE, "w")); [os.remove(f"docs/cards/{D9}_11.{x}") for x in ("jpg", "json")]
at9("11:05"); assert not ig9 and sorted(os.listdir(f"docs/cards/{D9}_11")) == ["01.jpg", "02.jpg", "03.jpg", "04.jpg"]
o12 = [p for _, p in S9.card_order(json.load(open("posts.json")), f"{D9}_11")]
assert [(t, n, tot) for t, n, tot, w, e in dc9] == [(H.title_of(p["text"]), n, 4) for n, p in enumerate(o12, 1)] and dc9[0][4] == "🧴"  # 번호 = 표지 순서, 채운 재료로 그림
assert fills9 == [(H.REEL_PROMPT, [f"{H.title_of(p['text'])} | {H.comment_of(p['text'])}" for p in o12])]  # 재료 없는 딜 한 번에
live9.add(f"{D9}_11.jpg"); at9("11:19"); assert [m for m, u, b in ig9] == ["HEAD", "HEAD"] and "igs_" + D9 + "_11" not in seen  # 마지막 딜 카드가 배포 전 -> 다음 실행에
live9.add("04.jpg"); n0 = st9.get("n", 0); at9("11:33")
pb9 = [b for m, u, b in ig9 if m == "POST"]
assert [b["image_url"].split("cards/")[1] for b in pb9] == [f"{D9}_11.jpg"] + [f"{D9}_11/0{n}.jpg" for n in range(1, 5)] and all(b["is_carousel_item"] and "caption" not in b for b in pb9)
assert len(ig9) == 7 and seen["igk_" + D9 + "_11"]["kids"] == [f"IMG{n0 + n}" for n in range(1, 6)] and not [k for k in seen if k.startswith("igc_")]  # 10/23 진우 '폴링 간격 늘려 호출 줄이기': 조각 만든 실행엔 상태 X(HEAD 2 + 조각 5 — 그래프 API 5번, 예전 13번)
assert list(json.load(open(H.IG_LIVE))) == [f"{D9}_11"]  # 사이트 먼저
at9("11:47"); g9 = [(m, u.split("?")[0].rsplit("/", 1)[-1]) for m, u, b in ig9 if u.startswith(H.IG)]
assert g9 == [("GET", f"IMG{n0 + 5}"), ("POST", "media")] and ig9[-1][2] == {"media_type": "CAROUSEL", "children": ",".join(f"IMG{n0 + n}" for n in range(1, 6)), "caption": H.card_caption(f"{D9}_11")[1]}, g9  # 다음 실행: 마지막 조각 상태 1번 + 묶음(캡션은 묶음에만)
assert seen["igc_IMG%d" % (n0 + 6)] == {"t": TK(f"{D9} 11:47"), "card": f"{D9}_11"} and not [k for k in seen if k.startswith("igk_")]  # 발행은 다음 실행(묶은 실행 seen이 안 남아도 두 번 X — 10/23 리뷰)
at9("11:47", H.ig_publish); assert not ig9  # 묶은 실행엔 발행 X(상태도 안 봄)
at9("12:01", H.ig_publish); assert [b for m, u, b in ig9 if u.endswith("media_publish")] == [{"creation_id": "IMG%d" % (n0 + 6)}] and len(ig9) == 2 and "오전 11시 카드" in sent[-1][1]["text"]  # 묶음 상태 1번 + 발행(묶음만 1번)
at9("12:15"); assert not ig9  # 회차 끝
# 마지막 조각 처리 중 -> 묶음은 다음 실행에(시간 창 지나도) / 조각 실패·1시간 넘게 처리 중 = 진짜 실패(버림, 다시 X, 예외 X)
seen, st9["v"] = {}, "IN_PROGRESS"; json.dump({}, open(H.IG_LIVE, "w")); n0 = st9.get("n", 0); at9("12:50")
assert len([1 for m, u, b in ig9 if m == "POST"]) == 5 and seen["igk_" + D9 + "_11"]["kids"] == [f"IMG{n0 + n}" for n in range(1, 6)] and not [k for k in seen if k.startswith("igc_")]
at9("13:04"); assert not [1 for m, u, b in ig9 if m == "POST"] and "igk_" + D9 + "_11" in seen  # 처리 중 = 기다림(다음 칸 시간이어도)
st9["v"] = "FINISHED"; at9("13:18"); assert [b["media_type"] for m, u, b in ig9 if m == "POST"] == ["CAROUSEL"] and "igk_" + D9 + "_11" not in seen and "igc_IMG%d" % (n0 + 6) in seen
for st, t in (("ERROR", "15:30"), ("IN_PROGRESS", "16:11")):
    seen, st9["v"] = {"igk_" + D9 + "_11": {"t": TK(f"{D9} 15:10"), "kids": ["K1", "K2"]}}, st
    at9(t); assert not [k for k in seen if k.startswith("igk_")] and not [1 for m, u, b in ig9 if m == "POST"] and len(seen["igfail"]["f"]) == 1 and "넘기기" in seen["igfail"]["f"][0] and not sent, seen
seen, st9["v"] = {"igk_" + D9 + "_11": {"t": TK(f"{D9} 15:10"), "kids": ["K1"]}}, "IN_PROGRESS"; at9("16:09"); assert "igk_" + D9 + "_11" in seen  # 1시간 안이면 기다림
def ig9k_http(url, body=None, headers=None, method=None):  # 조각마다 다른 상태
    if "?fields=status_code" in url and url.split("?")[0].rsplit("/", 1)[-1] in st9.get("per", {}):
        ig9.append((method or "GET", url, body)); return json.dumps({"status_code": st9["per"][url.split("?")[0].rsplit("/", 1)[-1]]})
    return ig9e_http(url, body, headers, method)
H.http, st9["per"], st9["v"] = ig9k_http, {"K1": "FINISHED", "K2": "IN_PROGRESS"}, "FINISHED"
seen = {"igk_" + D9 + "_11": {"t": TK(f"{D9} 16:00"), "kids": ["K1", "K2"]}}; at9("16:20"); assert not [1 for m, u, b in ig9 if m == "POST"] and "igk_" + D9 + "_11" in seen  # 하나라도 처리 중이면 묶음 X
st9.pop("per"); [os.remove(f"docs/cards/{D9}_19.{x}") for x in ("jpg", "json") if os.path.exists(f"docs/cards/{D9}_19.{x}")]
at9("19:05"); assert [b["media_type"] for m, u, b in ig9 if m == "POST"] == ["CAROUSEL"] and os.path.exists(f"docs/cards/{D9}_19.jpg") and os.path.isdir(f"docs/cards/{D9}_19")  # 카드 만드는 실행에도 지난 조각 묶음
H.IG_CAROUSEL, seen = False, {}; json.dump({}, open(H.IG_LIVE, "w")); live9.add(f"{D9}_19.jpg"); at9("19:40")
assert [(b.get("is_carousel_item"), b.get("media_type"), b["image_url"].split("cards/")[1]) for m, u, b in ig9 if m == "POST"] == [(None, None, f"{D9}_19.jpg")]; H.IG_CAROUSEL = True  # 끄면 딜 카드가 있어도 한 장
# 올리브영 딜 = '체크 포인트'(권유 문구 X), 딜 카드 하나라도 실패하면 폴더째 지움(-> 한 장 카드), 2일 지난 딜 카드 폴더 정리(json·표지·다른 폴더는 그대로)
H.deal_slides(f"{D9}_oy", [{"text": "🔥 [올리브영] 선크림 50ml (9,900원/무료)", "url": "https://oy.run/x", "hook": "h", "pts": ["SPF50"]}, {"text": "🔥 [쿠팡] 휴지 (9,900원/무료)", "url": "", "hook": "h", "pts": ["30롤"]}])
assert [w for *_, w, e in dc9[-2:]] == ["체크 포인트", "살 만한 이유"] and sorted(os.listdir(f"docs/cards/{D9}_oy")) == ["01.jpg", "02.jpg"]
rc9, cap9 = C9.deal_card, []; C9.deal_card = lambda it, *a, **k: cap9.append(it)
H.deal_slides(f"{D9}_oy2", [{"text": "🔥 [올리브영] 선크림 50ml (9,900원/무료)\n\n후기가 좋아요", "url": "https://oy.run/x", "hook": "h", "pts": ["후기 반응 좋음", "50ml 2개 구성", "미백 기능성", "추천 6·댓글 10"]},
                            {"text": "🔥 [쿠팡] 휴지 (9,900원/무료)\n\n후기 많아요", "url": "", "hook": "h", "pts": ["후기 많음"]}])
assert H.card_item({"text": "🔥 [올리브영] 크림 (9,900원)\n\n좋아요", "url": "https://oy.run/y", "hook": "후기 대박 크림", "pts": ["리뷰 1만", "50ml"]})[0] == {"title": "[올리브영] 크림 (9,900원)", "comment": "", "e": None, "hook": "", "unit": None, "warn": None, "pts": ["50ml"]}  # 릴스도 같은 거르기
assert cap9[0]["pts"] == ["50ml 2개 구성"] and cap9[0]["comment"] == "" and cap9[1]["pts"] == ["후기 많음"] and cap9[1]["comment"] == "후기 많아요"; C9.deal_card = rc9  # 올리브영만 후기·추천·반응·효능 문장 빼고 코멘트도 X
C9.deal_card = lambda *a, **k: 1 / 0; H.deal_slides(f"{D9}_x", [{"text": "🔥 [쿠팡] 휴지 (9,900원/무료)", "url": "", "hook": "h", "pts": ["30롤"]}]); assert not os.path.exists(f"docs/cards/{D9}_x")
for x in ("2026-10-09_11", "2026-10-10", "re"):
    os.makedirs(f"docs/cards/{x}", exist_ok=True)
open("docs/cards/2026-10-09_11.json", "w").write("[]"); seen = {}; at9("08:00")  # 정리는 ig_cards가 실행마다
assert not os.path.exists("docs/cards/2026-10-09_11") and os.path.isdir("docs/cards/2026-10-10") and os.path.isdir("docs/cards/re") and os.path.exists("docs/cards/2026-10-09_11.json")
# 21시 하루 카드: 모아보기가 표지와 같이 딜 카드도(인스타 토큰 있을 때) -> 릴스는 같은 재료
C9.deal_card, ds9 = real_dc9, []
rl9, tv9, sd9 = C9.reel, H.tg_video, H.deal_slides
C9.reel, H.tg_video, H.deal_slides = (lambda items, d, out, music=None: ds9.append(("reel", [i.get("e") for i in items])) or out), (lambda path, cap: None), (lambda stem, ps: ds9.append((stem, len(ps))) or sd9(stem, ps))
seen, sent[:] = {}, []; time.time = lambda: TK(f"{D9} 21:05"); H.digest(seen, json.load(open("posts.json")))
assert ds9[0] == (D9, 5) and sorted(os.listdir(f"docs/cards/{D9}")) == ["01.jpg", "02.jpg", "03.jpg", "04.jpg", "05.jpg"] and ds9[1][0] == "reel" and ds9[1][1][0] == "🧴"  # 딜 카드 때 채운 재료를 릴스도
H.E.pop("IG_TOKEN"); shutil.rmtree(f"docs/cards/{D9}"); seen, ds9[:] = {}, []; H.digest(seen, json.load(open("posts.json"))); assert ds9[0][0] == "reel" and ds9[0][1][0] == "🧴" and not os.path.exists(f"docs/cards/{D9}")  # 인스타 없으면 딜 카드 X, 릴스 재료는 그대로 채움
H.E["IG_TOKEN"] = "pt"; C9.reel, H.tg_video, H.deal_slides, H.ai_pick = rl9, tv9, sd9, ap9
shutil.rmtree("docs/cards"); os.rename(cards9, "docs/cards")
H.IG_HUMAN = ig9h
open("posts.json", "w").write(pj9); H.E["THREADS_TOKEN"] = "tk"; seen, sent[:] = {}, []; time.time = tt9; H.http = th_http; live = True; calls.clear(); H.threads(seen)  # Threads 카드는 그대로, 인스타는 threads()에서 안 올림(ig_cards)
assert not [c for c in calls if H.IG in c[1]] and any("/threads_publish?" in u for _, u in calls) and "인스타·Threads 자동 게시 중" in sent[-1][1]["caption"]
assert "threads, threads_deals, daily_post, daily_log, wx_dm, toss_reopen, ig_cards, ig_reel, ig_repost, ig_publish, ig_stage" in inspect.getsource(H.main) and 'ch = "ig" if name.startswith("ig_")' in inspect.getsource(H.step_alert)
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
assert "[올리브영] 딜 comment·hook·pts·warn은" in H.DEAL_PROMPT and "[올리브영] 딜은 가격·용량·구성·조건만" in H.REEL_PROMPT and "'추천'" in H.DEAL_PROMPT and "MIN_SCORE - earns(" in inspect.getsource(H.main) and H.earns("[올리브영] 세럼")  # 사실만·1점 낮춤(10/10~ 수수료 몰 전체, 4-6)
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
assert f'href="{H.SITE}p/0.html?ref=tg">[올리브영] 세럼' in dg and "oy.run" not in dg and 'href="https://a"' in dg  # 모아보기 = 링크만 나열 -> 올영은 사이트로
bt = H.blog_text(oyp, time.gmtime(1791291600 + 9 * 3600))
assert bt.split("\n\n")[2] == H.OY_NOTE and "👉 https://oy.run/x" in bt  # 블로그: 올영 문구 본문 맨 위(코멘트 있는 글이라 링크 그대로)
open("posts.json", "w").write(pj); H.tg, time.time = tg0, tt5
# 9-2) 딜마다 Threads: 텔레그램 버튼과 같은 링크(10/19~, 예전엔 사이트 딜 페이지), 제휴 링크면 대가성 문구 맨 앞, 3시간 지난 딜·모아보기 제외, 1회 3개, 미배포면 다음에, 두 번 안 올림
kt = lambda h: time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - h * 3600))
LP9 = "https://click.linkprice.com/click.php?m=gmarket&a=A1&l=9999&l_cd1=3&l_cd2=0&tu=" + "https%3A%2F%2Fwww.gmarket.co.kr%2Fn%2Fsearch%3Fkeyword%3D" + "%EC%9A%B0%EC%9C%A0" * 30  # 링크프라이스 딥링크(~450자) = Threads 500자에 못 들어감 -> 사이트 딜 페이지
json.dump([{"t": kt(4), "text": "🔥 [옛날] 딜", "url": "https://a"},
           {"t": kt(0), "text": "📋 모아보기", "url": None},
           {"t": kt(1), "text": f"{H.DISCLOSURE}\n\n🔥 [쿠팡] 휴지 30롤\n\n싸요\n\n출처: 뽐뿌", "url": "https://link.coupang.com/a/x"},
           {"t": kt(0.5), "text": "🔥 [카카오] 고구마 3kg\n\n맛있음\n\n출처: 뽐뿌", "url": "https://www.ppomppu.co.kr/1"},
           {"t": kt(0.2), "text": "🔥 [G마켓] 우유\n\n좋음\n\n출처: 뽐뿌", "url": LP9},
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
H.E["THREADS_TOKEN"] = "tk"; out9 = io.StringIO()
with contextlib.redirect_stdout(out9): H.threads_deals({})
from urllib.parse import parse_qs, urlsplit
made = [parse_qs(urlsplit(u).query) for m, u in calls if "/777/threads?" in u]
assert [m for m, _ in calls] == ["GET", "POST", "POST", "HEAD"]  # 직접 링크 = 사이트 확인 X · 4번(링크프라이스 450자 -> 사이트 딜 페이지)만 HEAD, 404 -> 멈춤
assert [q["link_attachment"][0] for q in made] == ["https://link.coupang.com/a/x"]  # 10/19 진우 '경유 말고 직접': 텔레그램 버튼과 같은 링크 · 10/19 밤 'Threads는 수수료 딜만': 3번(뽐뿌 원글) X
t2 = made[0]["text"][0]
assert t2.startswith(H.DISCLOSURE + "\n\n🔥 [쿠팡] 휴지 30롤\n\n싸요\n\n👉 https://link.coupang.com/a/x\n") and "출처" not in t2 and "hotdealpick.kr/p/" not in t2 and "👋 팔로우하면" in t2
assert made[0]["media_type"] == ["TEXT"] and made[0]["topic_tag"] == ["생필품"] and len(t2.encode()) < 500  # 주제 = 품목 칸(휴지 = 생필품, 10/23 진우)
assert [p.get("th") for p in json.load(open("posts.json"))] == [None, None, 1, 0, None, 0]  # 수수료 링크 아닌 3·5번 = th 0(로그 1번 표시, 거짓값이라 리스트 셈은 그대로)
assert "threads skip (수수료 링크 아님) [카카오] 고구마 3kg | direct\n" in out9.getvalue() and "threads skip (수수료 링크 아님) [옥션] 라면 | direct\n" in out9.getvalue() and "· 수수료 링크 아님 2" in out9.getvalue()
live_pages, calls[:], out9 = {2, 3, 4, 5}, [], io.StringIO()
with contextlib.redirect_stdout(out9): H.threads_deals({})  # 재실행: 올린 건 건너뛰고 남은 것만
assert [parse_qs(urlsplit(u).query)["link_attachment"][0][-15:-7] for m, u in calls if "/777/threads?" in u] == ["p/4.html"] and "threads skip" not in out9.getvalue()  # 건너뜀 로그는 딜마다 1번
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
json.dump([{"t": kt(0), "text": "🔥 [11번가] 버거킹\n\n싸요\n\n출처: 뽐뿌", "url": "https://link.coupang.com/a/w"}], open("posts.json", "w"))
H.http, calls[:] = pub_fail('{"error": {"message": "Fatal", "type": "OAuthException", "error_subcode": 4279047}}', True), []; H.threads_deals({})
made = [parse_qs(urlsplit(u).query) for m, u in calls if "/777/threads?" in u]
assert [q.get("link_attachment") for q in made] == [["https://link.coupang.com/a/w"], None] and "👉 https://link.coupang.com/a/w\n" in made[1]["text"][0]
assert sum("/threads_publish?" in u for m, u in calls) == 1  # 두 번째(첨부 없음)는 발행됨
json.dump([{"t": kt(0), "text": "🔥 [G마켓] 우유\n\n좋음", "url": "https://link.coupang.com/a/x9"}], open("posts.json", "w")); H.http, calls[:] = pub_fail('{"error": {"message": "expired"}}', False), []
try:
    H.threads_deals({}); raise AssertionError("다른 오류는 예외로 올라가야 함(main이 알림)")
except urllib.error.HTTPError:
    pass
assert sum("/777/threads?" in u for m, u in calls) == 1  # 다른 오류면 다시 안 만듦
H.time.sleep, H.http, calls[:] = sl2, td_http, []
del H.E["THREADS_TOKEN"]; json.dump([{"t": kt(0), "text": "🔥 새 딜", "url": "https://z"}], open("posts.json", "w"))
H.threads_deals({}); assert not calls  # 토큰 없으면 아무것도 안 함
# 9-2b) Threads 리스트 중심(10/11 진우 결정 '나누지 말고 묶기, 꾸준하게' — 2주 동결 ~10/25) + 10/11 23:40 '이 방식 유지하면서 경과 보기'(개별 글 기준 못 박음):
#       개별 글 = ① 쿠팡 같은 상품 대비 N원 쌈이 확실한 🔥(금액 상관없이, 💸 훅) 먼저 ② 30일 최저가·순위 1~3위 ③ 🛒·단위가격 참고만·일반 딜은 리스트로(18시 채움 없음),
#       1회 1개·45분 간격·하루 5개 / 본문 틀(고지문 → 💸 훅 → 🔥 제목 → …)은 그대로 / 토스 회차는 12·18시 베스트만 Threads / 재오픈·토스 이름 예약도 같이 셈
sv9b = (H.TH_SOLO_MAX, H.TH_SOLO_GAP, H.TH_SOLO_RUN, H.th_strong, H.TH_LIST_HOURS, H.TH_TOSS_KINDS)
H.TH_SOLO_MAX, H.TH_SOLO_GAP, H.TH_SOLO_RUN, H.th_strong, H.E["THREADS_TOKEN"] = 5, 45 * 60, 1, th_strong0, "tk"
assert (H.TH_SOLO_MIN, H.TH_SOLO_SAVE, H.TH_SOLO_RANK) == (0, 1, 3)  # 기본값: 채움 없음 · 같은 상품 차이 금액 상관없이 · 순위 1~3위
D9b, t0 = "2026-10-11", time.time
P9b = [("11:10", "🔥 [토스] 진우링크 (10,990원)\n\n💡 단위가격: 10매당 31원 — 쿠팡 같은 상품(18,200원)보다 7,210원 쌈", "https://toss.shopping/_m/j", {"own": 1}),
       ("11:15", "🔥 [토스] 최저가 (5,000원)\n\n토스 하루특가 · 30일 내 최저가", "https://toss.shopping/_m/k", {"s": 6}),
       ("11:20", "🔥 [쿠팡] 작은차이 (9,000원)\n\n💡 쿠팡 같은 상품(10,000원)보다 1,000원 쌈", "https://link.coupang.com/a/1", {"s": 8}),
       ("11:35", "🔥 [토스] 순위2위 (11,900원)\n\n토스 최대할인가 · 클렌징 폼 2위 · 내일 출발", "https://toss.shopping/_m/r2", {"own": 1}),
       ("11:40", "🛒 [토스] 약한딜 (58,900원)\n\n🤔 솔직히 특가로는 약한 제품 — 쿠팡 같은 상품보다 10,000원 쌈", "https://toss.shopping/_m/w", {"own": 1}),
       ("11:45", "🔥 [토스] 순위4위 (8,300원)\n\n토스 최대할인가 · 선블록·선크림·선로션 4위 · 무료배송\n💡 단위가격: 10ml당 593원 — 쿠팡 톤업 선크림(12,300원)보다 ml당 33% 쌈 (같은 브랜드 다른 이름이라 참고)", "https://toss.shopping/_m/r4", {"own": 1}),
       ("11:50", "🔥 [쿠팡] 일반8점 (3,000원)\n\n좋음", "https://link.coupang.com/a/2", {"s": 8}),
       ("17:50", "🔥 [쿠팡] 저녁8점 (3,000원)\n\n좋음", "https://link.coupang.com/a/3", {"s": 8})]
json.dump([{"t": f"{D9b} {t}", "text": x, "url": u, **e} for t, x, u, e in P9b], open("posts.json", "w"), ensure_ascii=False)
H.http, live_pages, seen9b = td_http, set(range(8)), {}
def th9b(hm):
    calls.clear(); time.time = lambda: TK(f"{D9b} {hm}"); H.threads_deals(seen9b)
    return [parse_qs(urlsplit(u).query)["text"][0] for m, u in calls if "/777/threads?" in u]
m9 = th9b("12:00"); assert len(m9) == 1 and "진우링크" in m9[0] and m9[0].startswith(H.TOSS_NOTE + "\n\n💸 쿠팡보다 7,210원 싸요\n🔥 [토스] 진우링크")  # 1회 1개, ① 먼저, 본문 틀 그대로
assert th9b("12:30") == []  # 45분 간격
m9 = th9b("12:46"); assert len(m9) == 1 and "작은차이" in m9[0]  # ①(같은 상품 1,000원 쌈 — 금액 상관없이)이 먼저 올라온 ②(30일 최저가)보다 먼저
m9 = th9b("13:32"); assert len(m9) == 1 and "최저가" in m9[0]  # ② 30일 최저가
m9 = th9b("14:18"); assert len(m9) == 1 and "순위2위" in m9[0] and seen9b["thsolo_20261011"]["n"] == 4  # ② 순위 1~3위
assert th9b("15:04") == [] and th9b("18:10") == [] and th9b("19:00") == []  # 🛒·4위·단위가격 참고만·일반 딜은 리스트로(18시 채움도 없음)
assert [bool(p.get("th")) for p in json.load(open("posts.json"))] == [True, True, True, True, False, False, False, False]
seen9b["thsolo_20261011"] = {"t": 1, "n": 5, "last": 0}; json.dump([{"t": f"{D9b} 19:30", "text": P9b[0][1], "url": P9b[0][2], "own": 1}], open("posts.json", "w"), ensure_ascii=False)
assert th9b("20:00") == []  # 하루 5개 찼으면 ① 딜도 채널에만
assert [H.th_tier(x) for _, x, _, _ in P9b] == [1, 2, 1, 2, 0, 0, 0, 0] and H.th_tier("🔥 x\n💡 쿠팡 비슷한 상품(9,000원)보다 3,000원 쌈") == 0 and H.th_tier("올인원 1위") == 2 and H.th_tier("TOP 10위") == 0
time.time = lambda: TK(f"{D9b} 18:30")
assert not H.th_solo({}, "🔥 x", fill=True)  # 기본값(TH_SOLO_MIN 0) = 18시 채움 없음
H.TH_SOLO_MIN = 3  # 채움을 다시 켜면(10/25 조정용 설정값): 18시 넘어 3개 미만일 때 7점↑·진우 링크 🔥만, 🛒 X, 3개 차면 X
assert not H.th_solo({}, "🛒 x\n🤔 솔직히 특가로는 약한 제품", fill=True) and H.th_solo({}, "🔥 x", fill=True) and not H.th_solo({"thsolo_20261011": {"t": 1, "n": 3, "last": 0}}, "🔥 x", fill=True)
json.dump([{"t": f"{D9b} 18:00", "text": "🔥 [카카오] 5점만 (3,000원)\n\n좋음", "url": "https://x", "s": 5}], open("posts.json", "w"), ensure_ascii=False)
seen9b = {}; assert th9b("18:30") == []; H.TH_SOLO_MIN = 0  # 채움은 7점↑·진우 링크만(5점 X)
assert "th_solo(seen, text, fill=True, reopen=mode)" in inspect.getsource(H.toss_reopen) and "th_solo(seen, plain_of(body), fill=True, beauty=" in inspect.getsource(H.toss_picks)  # 재오픈·토스 이름 예약도 하루 5개에 셈
assert (tlh0, sv9b[5]) == ((12, 15, 18), ("day", "best", "cat", "beauty", "special")) and 'kind in TH_TOSS_KINDS and (hrs[-1] in TH_LIST_HOURS or kind == "cat")' in inspect.getsource(H.toss_deals)
assert H.TH_TOSS_KINDS != ("best",) and "TH_LIST_HOURS, TH_TOSS_KINDS = 99, 0, 45 * 60, 1, 1, (12, 15, 18), (\"best\", \"cat\")" in inspect.getsource(H) and H.TH_SLOTS is None  # 기본값: 개별 글 하루 한도 없음(99)·45분 간격(슬롯 X, 10/12 01:20), 리스트 12·15·18시, 토스 리스트 = 베스트 + 17시 생필품(10/12 22:45)
# 12·18시 '지금 살 만한 딜' 리스트는 Threads에도(대가성 문구 맨 앞·번호·이름·가격·텔레그램 버튼과 같은 링크(10/19~)·480자), 다른 시각엔 채널만
H.TH_LIST_HOURS = (12, 18); sent[:] = []
tg9b = H.tg; H.tg = lambda m, **p: sent.append((m, p)) or {"message_id": 1}
json.dump([{"t": f"{D9b} 0{k + 5}:00", "text": f"{H.DISCLOSURE}\n\n🔥 [쿠팡] 리스트상품{k} 아주 긴 이름 대용량 기획 (9,900원/무료)\n\n좋음", "url": f"https://link.coupang.com/a/L{k}", "mid": 10 + k, "pop": 10 - k} for k in range(5)], open("posts.json", "w"), ensure_ascii=False)
calls.clear(); time.time = lambda: TK(f"{D9b} 12:05"); H.top_deals({})
tl9 = [parse_qs(urlsplit(u).query) for m, u in calls if "/777/threads?" in u]
assert len(tl9) == 1 and tl9[0]["text"][0].startswith(H.DISCLOSURE + "\n\n🏆 지금 살 만한 딜 TOP") and "👉 https://link.coupang.com/a/L0\n" in tl9[0]["text"][0] and "/p/" not in tl9[0]["text"][0] and len(tl9[0]["text"][0]) <= 480 and "🏆 <b>지금 살 만한 딜 TOP5</b> (12시)" in sent[-1][1]["text"]
lk9 = set(re.findall(r"https?://\S+|t\.me/\S+", tl9[0]["text"][0])) | set(tl9[0].get("link_attachment", []))
assert len(lk9) <= 5 and "t.me" not in tl9[0]["text"][0] and tl9[0]["link_attachment"] == ["https://link.coupang.com/a/L0"]  # Threads 글 하나에 서로 다른 링크 5개까지(4279111 — 10/12 12·15·18시 리스트 실패): 딜 링크만, 미리보기 = 1번 딜
assert "게시 시점" not in tl9[0]["text"][0]  # 토스 딜 없는 리스트 = 게시 시점 줄 X
ps9 = json.load(open("posts.json")); ps9[0].update(text=f"{H.TOSS_NOTE}\n\n🔥 [토스] 리스트상품0 아주 긴 이름 대용량 기획 (9,900원)\n\n좋음", url="https://toss.shopping/_m/L0"); json.dump(ps9, open("posts.json", "w"), ensure_ascii=False)
H.TOSS_NO_CMP = True; calls.clear(); H.top_deals({}); H.TOSS_NO_CMP = False
tl9 = [parse_qs(urlsplit(u).query)["text"][0] for m, u in calls if "/777/threads?" in u]
assert len(tl9) == 1 and tl9[0].endswith("\n\n⚠️ 10/11 12:05 게시 시점 가격") and len(tl9[0]) <= 480 and sent[-1][1]["text"].endswith("\n\n⚠️ 10/11 12:05 게시 시점 가격")  # 토스 딜이 든 리스트 = Threads·채널 끝에 게시 시점 줄(480자 안)
SR9 = "https://search.shopping.naver.com/search/all?query=" + "%EC%82%BC%EB%8B%A4%EC%88%98" * 4  # 아직 검색 링크인 딜(~160자) = 검색 링크 그대로, 길어서 480자 안에 들어가는 만큼만
json.dump([{**p, "url": SR9 + str(k)} for k, p in enumerate(ps9)], open("posts.json", "w"), ensure_ascii=False); calls.clear(); out9 = io.StringIO()
with contextlib.redirect_stdout(out9): H.top_deals({})
assert not [u for m, u in calls if "/777/threads?" in u] and "TOP5" in sent[-1][1]["text"] and SR9 + "4" in sent[-1][1]["text"] and "threads skip (수수료 링크 아님) top12 리스트 | 항목 0개\n" in out9.getvalue()  # 10/19 밤 진우 'Threads는 수수료 딜만': 검색 링크뿐이면 Threads 리스트 X, 텔레그램은 그대로
json.dump([{**p, "url": SR9 + str(k) if k % 2 else p["url"]} for k, p in enumerate(ps9)], open("posts.json", "w"), ensure_ascii=False); calls.clear(); H.top_deals({})
tl9 = [parse_qs(urlsplit(u).query) for m, u in calls if "/777/threads?" in u]
assert len(tl9) == 1 and "TOP3 (12시)" in tl9[0]["text"][0] and "TOP5" in sent[-1][1]["text"] and SR9 not in tl9[0]["text"][0] and tl9[0]["link_attachment"] == ["https://toss.shopping/_m/L0"]  # 섞이면 수수료 링크 딜만(토스·쿠팡 파트너스), 검색 링크 항목 X
assert tl9[0]["text"][0].startswith(H.TOSS_NOTE + "\n" + H.DISCLOSURE + "\n\n🏆") and [l for l in re.findall(r"👉 (\S+)", tl9[0]["text"][0])] == ["https://toss.shopping/_m/L0", "https://link.coupang.com/a/L2", "https://link.coupang.com/a/L4"]
H.TH_LIST_HOURS = (18,); calls.clear(); H.top_deals({}); assert not [u for m, u in calls if "/777/threads?" in u]  # 리스트 시각 아니면 채널만
H.tg = tg9b; time.time = t0; del H.E["THREADS_TOKEN"]; H.TH_SOLO_MAX, H.TH_SOLO_GAP, H.TH_SOLO_RUN, H.th_strong, H.TH_LIST_HOURS, H.TH_TOSS_KINDS = sv9b
# 9-2c) 화장품 매일 1~2개(10/11 23:50 진우 '화장품은 꾸준하게 올리자, 소모량이 많을 거라 생각해' + '우선 관찰'): Threads 개별 글 3~5개 중 화장품 1~2개 —
#       화장품이 1개 안 찼으면 마지막 자리는 화장품 몫(다른 글은 4개까지), 화장품은 하루 2개까지. 자리 채우는 순서: ①② 화장품(소모품 먼저) > 진우 화장품 링크·이름 예약(🛒 X)
#       > 오늘 진우 화장품 링크가 더 없으면 15·19시 토스 뷰티 회차 1개(소모품 먼저). 시간·본문 틀은 그대로
sv9c = (H.TH_SOLO_MAX, H.TH_SOLO_GAP, H.TH_SOLO_RUN, H.th_strong, H.TH_LIST_HOURS, H.TH_TOSS_KINDS)
H.TH_SOLO_MAX, H.TH_SOLO_GAP, H.TH_SOLO_RUN, H.th_strong, H.TH_LIST_HOURS, H.TH_TOSS_KINDS, H.E["THREADS_TOKEN"] = 5, 45 * 60, 1, th_strong0, tlh0, ("best",), "tk"
H.TH_BEAUTY_MIN, H.TH_BEAUTY_MAX = 1, 2; assert tbm0 == (1, 7) and "TH_BEAUTY_MIN, TH_BEAUTY_MAX = 1, 7" in inspect.getsource(H)  # 기본값 1·7(10/12 20:00 진우 2 -> 4 -> 7) — 아래 한도 검사는 2로  # 기본값(예전 셀프체크는 화장품 자리 없이 0, 99)
assert [H.th_beauty(n) for n in ("[토스] 메르헨트 미셀라 클렌징워터 500ml", "아스파시아 립앤아이 리무버", "에이지랩 선크림 70ml", "토너패드 70매", "콜라겐 에센스 마스크팩 100개입", "화이트벨라 마이크로 니들 패치 12매")] == [2] * 6  # 소모품
assert [H.th_beauty(n) for n in ("레이데이 살몬퓨어 리페어 비비크림 50ml 3개", "앙쥬 365 썬BB크림 1+1", "에이지랩 달팽이 뮤신 올인원 크림", "오에스알 EGF 리페어 크림 70ml", "토리든 세럼 50ml")] == [1] * 5  # 다른 화장품(BB크림 = 10/12 진우 링크)
assert [H.th_beauty(n) for n in ("한경희 카본히터 Q2000", "로지텍 마우스패드", "서울우유 생크림 500ml", "배스킨라빈스 아이스크림", "쿠션 방석", "커밍글 노워시 트리트먼트")] == [0] * 6  # 화장품 아님(크림·패드·쿠션 단독 X)
# 10/12 리뷰 고침: 화장품 판별(썬·선 표기·흔적 패드·세라마이드 크림·기초 N종 / 충전기·재생 토너·살균기·세제·스티커·욕실·몰 이름 [올리브영]은 X)
assert [H.th_beauty(n) for n in ("닥터지 그린 마일드 업 썬크림 50ml", "라운드랩 수분 선블럭", "넘버즈인 썬스틱", "메디힐 흔적 패드 100매", "이니스프리 선로션", "키스미 마스카라 리무버")] == [2] * 6
assert [H.th_beauty(n) for n in ("토리든 솔리드인 세라마이드 크림", "설화수 탄력 3종 기초 세트", "AHC 기초 5종 선물세트")] == [1] * 3
assert [H.th_beauty(n) for n in ("[토스] 에센스웨어 GaN 65W 멀티 충전기", "삼성 호환 재생 토너 카트리지", "자외선 칫솔 살균기", "올인원 캡슐세제", "쿨링 미스트 선풍기", "스티커 리무버", "욕실 클렌저", "[올리브영] 오리온 초코파이")] == [0] * 8
# 순위: 토스 카테고리 이름의 '·'도(②), 봇 '🏆 인기 · 뽐뿌에서 지금 많이 보는 글 N위'는 커뮤니티 조회 순위라 X, '10위'·'13위'를 1~3위로 안 읽음, '30일 최저가는 아니지만' X
assert [H.th_tier(x) for x in ("🔥 a\n\n토스 최대할인가 · 선블록·선크림·선로션 2위 · 무료배송", "🔥 a\n\n토스 건강·발패치 1위", "🔥 a\n🏆 인기 · 뽐뿌에서 지금 많이 보는 글 1위\n\n좋음",
                               "🔥 a\n🏆 인기 · 클리앙에서 지금 많이 보는 글 2위", "🔥 a\n\n토스 최대할인가 · BB크림 10위", "🔥 a\n\n토스 · 13위", "🔥 a\n\n30일 최저가는 아니지만 괜찮음")] == [2, 2, 0, 0, 0, 0, 0]
# 🛒 = 문구 없이 제목만 🛒여도 약한 딜(10/11 로로보아·삭스팡·후드 필터가 ②로 읽혀 Threads에 🔥로 나가던 것), 토스 Threads 글 끝 '🛒 https://' 링크 줄은 아님
assert H.th_weak("🛒 [토스] 삭스팡 양말 (9,900원)\n\n30일 내 최저가 · 쿠팡에선 같은 상품을 못 찾아") and H.th_tier("🛒 [토스] 삭스팡 양말 (9,900원)\n\n30일 내 최저가") == 0
assert H.th_weak(f"[광고] x\n{H.TOSS_NOTE}\n\n🛒 [토스] y") and not H.th_weak("🔥 x\n\n🛒 https://toss.im/_m/1") and not H.th_weak("🔥 [토스] 립앤아이 리무버")
S9c, W9c = "🔥 x\n💡 쿠팡 같은 상품(10,000원)보다 1,000원 쌈", "🛒 x\n🤔 솔직히 특가로는 약한 제품"
time.time = lambda: TK("2026-10-12 10:00"); s9c = {}
assert H.th_solo(s9c, "🔥 x", beauty=1, slot=True) and not H.th_solo(s9c, "🔥 x", beauty=1) and not H.th_solo(s9c, "🔥 x", slot=True)  # 화장품 자리: 진우 화장품은 ①② 아니어도 O, 봇 화장품·화장품 아닌 진우 링크는 ①②만
assert not H.th_solo(s9c, W9c, beauty=2, slot=True)  # 🛒는 화장품 자리에도 X
H.th_mark(s9c, 2); assert s9c["thsolo_20261012"] == {"t": TK("2026-10-12 10:00"), "n": 1, "b": 1, "last": TK("2026-10-12 10:00")}
time.time = lambda: TK("2026-10-12 10:46")
assert not H.th_solo(s9c, "🔥 x", beauty=1, slot=True) and H.th_solo(s9c, S9c, beauty=1)  # 1개 찼으면 진우 화장품도 ①②만
H.th_mark(s9c, 1); H.th_mark(s9c); assert (s9c["thsolo_20261012"]["n"], s9c["thsolo_20261012"]["b"]) == (3, 2)
s9c["thsolo_20261012"]["last"] = 0; assert not H.th_solo(s9c, S9c, beauty=2, slot=True) and H.th_solo(s9c, S9c)  # 화장품은 하루 2개까지(①이어도), 다른 글은 됨
assert H.th_day({"thsolo_20261012": {"t": 1, "n": 1, "last": 5}}, time.time()) == {"t": 1, "n": 1, "b": 0, "last": 5} and H.th_day({}, time.time()) == {"n": 0, "b": 0, "last": 0}  # b 없는 기록(배포 전 = 0:02 재오픈 샤워기 헤드) = 화장품 0개
s9c = {"thsolo_20261011": {"t": 1, "n": 3, "b": 0, "last": TK("2026-10-11 23:33")}}; time.time = lambda: TK("2026-10-12 00:02")  # 45분 간격은 밤 12시를 넘어서도(10/11 23:33 글 -> 10/12 0:02 재오픈이 29분 만에 나가던 것)
assert H.th_day(s9c, time.time())["last"] == TK("2026-10-11 23:33") and not H.th_solo(s9c, S9c) and not H.th_solo(s9c, "🔥 x", beauty=2, slot=True)
time.time = lambda: TK("2026-10-12 00:18"); assert H.th_solo(s9c, S9c); H.th_mark(s9c); assert s9c["thsolo_20261012"] == {"t": TK("2026-10-12 00:18"), "n": 1, "b": 0, "last": TK("2026-10-12 00:18")}
time.time = lambda: TK("2026-10-12 10:00")
s9c = {"thsolo_20261012": {"t": 1, "n": 4, "b": 0, "last": 0}}  # 화장품 0개 + 다른 글 4개 -> 마지막 자리는 화장품 몫
assert not H.th_solo(s9c, S9c) and H.th_solo(s9c, S9c, beauty=1) and H.th_solo(s9c, "🔥 x", beauty=2, slot=True)
assert H.th_solo({"thsolo_20261012": {"t": 1, "n": 4, "b": 1, "last": 0}}, S9c) and not H.th_solo({"thsolo_20261012": {"t": 1, "n": 5, "b": 1, "last": 0}}, S9c, beauty=1, slot=True)  # 화장품 찼으면 5개까지, 5개면 끝
# 10/12 밤 진우 BB크림처럼 화장품 ①이 몰려도 Threads 개별 글은 화장품 2개까지 -> 나머지 자리는 다른 ①②에(채널엔 전부 그대로)
D9c = "2026-10-12"
P9c = [("00:05", "🔥 [쿠팡] 휴지 30롤 (19,900원)\n\n💡 쿠팡 같은 상품(22,900원)보다 3,000원 쌈\n🎁 클렌징폼 증정", "https://link.coupang.com/a/h", {"s": 8}),
       ("00:10", "🔥 [토스] 레이데이 살몬퓨어 리페어 비비크림 50ml 3개 (19,900원)\n\n💡 쿠팡 같은 상품(30,400원)보다 10,500원 쌈", "https://toss.shopping/_m/b1", {"own": 1}),
       ("00:20", "🔥 [토스] 파스쿠찌 쌩얼톤업 SUN 비비크림 1+1 (17,900원)\n\n💡 쿠팡 같은 상품(23,900원)보다 6,000원 쌈", "https://toss.shopping/_m/b2", {"own": 1}),
       ("00:30", "🔥 [토스] 앙쥬 24K 골드 비비크림 50g 2개 (14,900원)\n\n💡 쿠팡 같은 상품(20,460원)보다 5,560원 쌈", "https://toss.shopping/_m/b3", {"own": 1}),
       ("00:35", "🔥 [토스] 에이지랩 올인원 크림 (9,900원)\n\n토스 최대할인가", "https://toss.shopping/_m/b4", {"own": 1}),
       ("00:40", "🔥 [토스] 메르헨트 클렌징워터 (11,900원)\n\n토스 최대할인가", "https://toss.shopping/_m/b5", {"own": 1}),
       ("01:00", "🛒 [토스] 디오프러스 매직 비비크림 (12,900원)\n\n🤔 솔직히 특가로는 약한 제품 — 쿠팡 같은 상품과 1,689원 차이", "https://toss.shopping/_m/b6", {"own": 1})]
json.dump([{"t": f"{D9c} {t}", "text": x, "url": u, **e} for t, x, u, e in P9c], open("posts.json", "w"), ensure_ascii=False)
H.http, live_pages, seen9b = td_http, set(range(10)), {}
def th9c(hm):
    calls.clear(); time.time = lambda: TK(f"{D9c} {hm}"); H.threads_deals(seen9b)
    return [parse_qs(urlsplit(u).query)["text"][0] for m, u in calls if "/777/threads?" in u]
m9 = th9c("00:45"); assert len(m9) == 1 and "휴지" in m9[0] and "클렌징폼" in m9[0]  # 10/12 01:10 진우 순서: ① 쿠팡 같은 상품 차이(먼저 올라온 휴지) > 화장품 > ② — 휴지 본문 '클렌징폼 증정'은 화장품으로 안 셈(제목만 봄)
m9 = th9c("01:31"); assert len(m9) == 1 and "레이데이" in m9[0] and "💸 쿠팡보다 10,500원 싸요\n🔥 [토스] 레이데이" in m9[0]  # 그다음 ①(화장품), 본문 틀 그대로
m9 = th9c("02:17"); assert len(m9) == 1 and "파스쿠찌" in m9[0] and seen9b["thsolo_20261012"]["b"] == 2  # 화장품 2번째
assert th9c("03:03") == [] and th9c("03:50") == []  # 화장품 2개 찼음 -> 앙쥬 ①도 채널에만, 일반 🔥·🛒도 X
assert [bool(p.get("th")) for p in json.load(open("posts.json"))] == [True, True, True, False, False, False, False] and (seen9b["thsolo_20261012"]["n"], seen9b["thsolo_20261012"]["b"]) == (3, 2)
seen9b = {}; json.dump([{"t": f"{D9c} {t}", "text": x, "url": u, **e} for t, x, u, e in P9c[4:]], open("posts.json", "w"), ensure_ascii=False)
m9 = th9c("00:50"); assert len(m9) == 1 and "클렌징워터" in m9[0]  # ①② 화장품이 없으면 진우 화장품 링크가 자리 채움 — 소모품 먼저
assert th9c("01:40") == []  # 채운 뒤엔 일반 🔥 진우 화장품도 리스트로
seen9b = {}; json.dump([{"t": f"{D9c} 00:40", "text": f"{H.TOSS_NOTE}\n\n🛒 [토스] 앙쥬 비비크림 (9,900원)\n\n30일 내 최저가 · 쿠팡에선 같은 상품을 못 찾아", "url": "https://toss.shopping/_m/w2", "own": 1}], open("posts.json", "w"), ensure_ascii=False)
assert th9c("00:50") == []  # 🛒(문구 없이 제목만)인 진우 화장품 = 화장품 자리에도 X(리스트로)
seen9b = {}; json.dump([{"t": f"{D9c} 00:40", "text": "🔥 [쿠팡] 봇 클렌징폼 (5,900원)\n\n좋음", "url": "https://link.coupang.com/a/c", "s": 8}], open("posts.json", "w"), ensure_ascii=False)
assert th9c("00:50") == []  # 봇 딜은 화장품이어도 ①②만
assert "beauty=bt, slot=True" in inspect.getsource(H.toss_picks) and "th_mark(seen, bt)" in inspect.getsource(H.toss_picks)  # 토스 이름 예약 = 진우 화장품(자리 채움), 재오픈은 화장품 수에만 셈
# 15·19시 토스 뷰티 회차: 오늘 화장품 자리가 비었고 진우 화장품 링크(오늘 남은 것·🛒 X)가 없으면 1개를 Threads 개별 글로(소모품 먼저), 채널 글은 그대로
def toss9c(path, body=None):
    if path == "/categories": return {"categories": [{"displayName": "뷰티", "categoryId": 400}, {"displayName": "식품", "categoryId": 200}]}
    if path.startswith("/products/best-categories/400"):
        return {"items": [{"tacaItemId": 91, "displayName": names9c[0], "displayPrice": 9900, "isSoldOut": False},
                          {"tacaItemId": 92, "displayName": names9c[1], "displayPrice": 11900, "discountRate": 30, "reviewScore": 4.8, "reviewCount": 1200, "isSoldOut": False}]}
    if path == "/links": return {"shortUrl": f"https://toss.im/_m/{body['tacaItemId']}"}
    raise AssertionError(path)
names9c = ["에이지랩 올인원 크림 50ml", "메르헨트 미셀라 클렌징워터 500ml"]
sv9c2 = (H.toss, H.ai_pick, H.tg, H.HAS_TOSS, H.EVENTS, H.E.get("TOSS_PUBLISHER_ID"))
H.toss, H.HAS_TOSS, H.EVENTS, H.E["TOSS_PUBLISHER_ID"] = toss9c, True, "ev9c.json", "pub"
H.ai_pick = lambda prompt, lines: [{"i": 0, "score": 8, "comment": "올인원 하나로 끝"}, {"i": 1, "score": 7, "comment": "500ml 대용량 <싸다>"}]
H.tg = lambda m, **p: sent.append((m, p)) or {"message_id": 7}
def beauty9c(hm, seen, ev=()):
    json.dump(list(ev), open(H.EVENTS, "w"), ensure_ascii=False); calls.clear(); sent.clear(); time.time = lambda: TK(f"{D9c} {hm}"); H.toss_deals(seen, "beauty")
    return [parse_qs(urlsplit(u).query) for m, u in calls if "/777/threads?" in u]
b9 = beauty9c("15:05", {})
assert len(sent) == 1 and "💙 <b>토스 뷰티 베스트 중 살 만한 2개</b>" in sent[0][1]["text"] and len(b9) == 1  # 채널 글 그대로 + Threads 개별 글 1개
t9 = b9[0]["text"][0]
assert t9.startswith(H.TOSS_NOTE + "\n\n💙 토스 특가 · 뷰티 베스트 ") and "위 🔥\n메르헨트 미셀라 클렌징워터 500ml\n11,900원 (30%↓) · ⭐ 4.8 (1,200)\n👉 500ml 대용량 <싸다>\n\n🛒 https://toss.im/_m/92" in t9, t9 and b9[0]["link_attachment"] == ["https://toss.im/_m/92"]  # 소모품 먼저, 토스 이름 예약 글 틀, 쉐어링크
assert "hotdealpick.kr" not in t9 and "쿠팡" not in t9  # API 상품 = 사이트·쿠팡 비교 X
s9c = {}; beauty9c("15:05", s9c); assert s9c["thsolo_20261012"]["b"] == 1
for k in [k for k in s9c if k.startswith("tb_")]: del s9c[k]  # 같은 상품도 다시 후보로(19시 회차가 채널 글은 올리게)
assert beauty9c("19:05", s9c) == [] and len(sent) == 1  # 채웠으면 19시엔 채널만(채널 글은 그대로)
assert beauty9c("15:05", {"thsolo_20261012": {"t": 1, "n": 1, "b": 1, "last": 0}}) == []  # 오늘 화장품 이미 1개(진우 아침 이름 예약 등) -> 채널만
assert beauty9c("15:05", {}, [{"at": f"{D9c} 22:20", "name": "메르헨트 폼클렌징 500ml 2개", "url": "https://toss.shopping/_m/n", "deal": True, "text": "🔥 <b>[토스] 메르헨트 폼클렌징</b>"}]) == []  # 밤에 진우 화장품 링크 -> 그게 채움
assert beauty9c("15:05", {}, [{"at": f"{D9c} 22:20", "name": "레이데이 비비크림 3개", "api": True}]) == []  # 진우 화장품 이름 예약도
json.dump([{"t": f"{D9c} 18:40", "text": f"{H.TOSS_NOTE}\n\n🔥 [토스] 에이지랩 선크림 70ml 2개 (8,300원)\n\n토스 최대할인가 · 4위", "url": "https://toss.shopping/_m/s", "own": 1}], open("posts.json", "w"), ensure_ascii=False)
assert beauty9c("19:05", {}) == []  # 18:40 진우 화장품 링크가 채널엔 나갔고 Threads 차례 대기(45분 간격 등) -> 뷰티 회차가 자리 안 뺏음(10/12 리뷰)
json.dump([{"t": f"{D9c} 18:40", "text": f"{H.TOSS_NOTE}\n\n🔥 [토스] 에이지랩 선크림 70ml 2개 (8,300원)\n\n토스 최대할인가 · 4위", "url": "https://toss.shopping/_m/s", "own": 1, "th": 1}], open("posts.json", "w"), ensure_ascii=False)
assert len(beauty9c("19:05", {})) == 1; json.dump([], open("posts.json", "w"))  # 이미 Threads에 나갔으면 기다릴 것 없음(b는 그 글이 셈 — 여기선 기록 없이 회차만 봄)
assert beauty9c("19:05", {}, [{"at": f"{D9c} 19:00", "name": "니들 패치 12매", "api": True}]) == []  # 19:00 이름 예약 = 같은 실행 뒤 순서 toss_picks가 올림 -> 기다림
assert len(beauty9c("19:05", {"pk_2026-10-12 19:00": {"st": "done"}}, [{"at": f"{D9c} 19:00", "name": "니들 패치 12매", "api": True}])) == 1  # 이미 처리됨 -> 안 기다림
assert len(beauty9c("15:05", {}, [{"at": f"{D9c} 22:20", "name": "올리브영 클렌징 세일", "url": "https://oy.run/x", "text": "📢 <b>올리브영 클렌징 행사</b>"}])) == 1  # 링크 있어도 상품 딜(deal) 아니면 안 셈
assert len(beauty9c("19:05", {}, [{"at": f"{D9c} 07:30", "name": "니들 패치 12매", "api": True}, {"at": f"{D9c} 22:20", "name": "한경희 카본히터", "url": "https://toss.shopping/_m/h", "deal": True},
                                    {"at": f"{D9c} 23:00", "name": "디오프러스 비비크림", "url": "https://toss.shopping/_m/d", "deal": True, "text": "🛒 <b>[토스] 디오프러스</b>\n\n🤔 솔직히 특가로는 약한 제품"},
                                    {"at": "2026-10-13 22:20", "name": "레이데이 비비크림", "api": True}])) == 1  # 지난 예약·화장품 아님·🛒·내일 것은 안 셈 -> 뷰티 회차가 채움
assert len(beauty9c("15:05", {}, [{"at": f"{D9c} 22:20", "text": "📢 <b>올리브영 클렌징 행사</b>"}])) == 1  # 링크 없는 행사 글은 진우 화장품 링크 아님
names9c[:] = ["달팽이 뮤신 50g", "콜라겐 100ml"]; b9 = beauty9c("15:05", {}); names9c[:] = ["에이지랩 올인원 크림 50ml", "메르헨트 미셀라 클렌징워터 500ml"]
assert len(b9) == 1 and "🔥\n달팽이 뮤신 50g\n" in b9[0]["text"][0]  # 뷰티 카테고리 상품은 화장품 낱말이 없어도 화장품(소모품 없으면 Claude 1순위)
H.TH_SOLO_GAP = 45 * 60; assert beauty9c("15:05", {"thsolo_20261012": {"t": 1, "n": 1, "last": TK(f"{D9c} 14:40")}}) == []  # 45분 간격은 그대로(채널만)
# 재오픈 한도(10/12 진우 (나)+(다)+'6시부터, 한도 관리'): 개별 5개·화장품 수와 따로 밤(0~6시) 2·아침(6시~) 2·하루 4, ①②만, 45분 간격은 같이, 일반 딜이 먼저(main 순서)
H.TH_REOPEN_NIGHT, H.TH_REOPEN_MORN, H.TH_REOPEN_DAY = trn0; rq9 = {}
time.time = lambda: TK(f"{D9c} 00:10"); assert H.th_solo(rq9, S9c, reopen="night") and not H.th_solo(rq9, "🔥 x", reopen="night")  # ①②만
H.th_mark(rq9, reopen="night"); assert (rq9["thsolo_20261012"]["n"], rq9["thsolo_20261012"]["b"], rq9["thsolo_20261012"]["rn"]) == (0, 0, 1)  # 개별 5개·화장품 수에 안 셈
time.time = lambda: TK(f"{D9c} 00:40"); assert not H.th_solo(rq9, S9c, reopen="night") and not H.th_solo(rq9, S9c)  # 45분 간격은 같이(일반 딜도)
time.time = lambda: TK(f"{D9c} 00:56"); H.th_mark(rq9, beauty=1); time.time = lambda: TK(f"{D9c} 01:42"); H.th_mark(rq9, reopen="night")
time.time = lambda: TK(f"{D9c} 02:30"); assert not H.th_solo(rq9, S9c, reopen="night") and H.th_solo(rq9, S9c)  # 밤 2개 찼음, 일반 딜은 그대로
assert rq9["thsolo_20261012"] == {"t": TK(f"{D9c} 01:42"), "n": 1, "b": 1, "rn": 2, "ra": 0, "last": TK(f"{D9c} 01:42")}
time.time = lambda: TK(f"{D9c} 06:10"); assert H.th_solo(rq9, S9c, reopen="am"); H.th_mark(rq9, reopen="am"); time.time = lambda: TK(f"{D9c} 07:00"); H.th_mark(rq9, reopen="am")
time.time = lambda: TK(f"{D9c} 07:50"); assert not H.th_solo(rq9, S9c, reopen="am") and H.th_solo(rq9, S9c)  # 아침 2개 찼음
H.TH_REOPEN_MORN = 3; assert not H.th_solo(rq9, S9c, reopen="am"); H.TH_REOPEN_MORN = trn0[1]  # 하루 4개(밤 2 + 아침 2)도
assert H.TH_REOPEN_AM == (6, 11) and "threads, threads_deals, daily_post, daily_log, wx_dm, toss_reopen, ig_cards" in inspect.getsource(H.main)  # 아침 재알림 6시부터, 재오픈은 일반 딜 뒤
# 줄 맨 앞이 약한 글(🛒)이어도 뒤 ① 재오픈이 나감(4d9271a1부터 있던 막힘, 10/12 리뷰) — 약한 글은 줄에 남음
H.toss = lambda path, body=None: {"items": [{"tacaItemId": i, "displayPrice": p, "isSoldOut": False} for i, p in ((71, 12900), (72, 7620))]} if path.startswith("/products/detail") else {"items": [], "hasNext": False}
rq9 = {"reopen": {"t": TK(f"{D9c} 00:00"), "ts": [], "q": [{"id": 71, "n": "약한 크림", "url": "https://toss.shopping/_m/q1", "p0": 12900, "icon": "🛒", "cmp": "🤔 솔직히 특가로는 약한 제품", "k": "ev", "day": D9c, "st": 0, "title": "약한 크림", "warn": ""},
                                                                   {"id": 72, "n": "해피달링 샤워기", "url": "https://toss.shopping/_m/q2", "p0": 7620, "icon": "🔥", "cmp": "💡 쿠팡 같은 상품(14,900원)보다 7,280원 쌈", "k": "ev", "day": D9c, "st": 0, "title": "해피달링 샤워기", "warn": ""}]}}
calls.clear(); time.time = lambda: TK(f"{D9c} 00:20"); H.toss_reopen(rq9)
r9 = [parse_qs(urlsplit(u).query)["text"][0] for m, u in calls if "/777/threads?" in u]
assert len(r9) == 1 and "해피달링 샤워기\n7,620원\n" in r9[0] and [e["st"] for e in rq9["reopen"]["q"]] == [0, 1] and rq9["thsolo_20261012"]["rn"] == 1
H.toss, H.ai_pick, H.tg, H.HAS_TOSS, H.EVENTS = sv9c2[:5]; H.E["TOSS_PUBLISHER_ID"] = sv9c2[5]
if sv9c2[5] is None: del H.E["TOSS_PUBLISHER_ID"]
time.time = t0; del H.E["THREADS_TOKEN"]; H.TH_SOLO_MAX, H.TH_SOLO_GAP, H.TH_SOLO_RUN, H.th_strong, H.TH_LIST_HOURS, H.TH_TOSS_KINDS = sv9c; H.TH_BEAUTY_MIN, H.TH_BEAUTY_MAX = 0, 99

# 9-2d) 10/12 진우 '묶음 글은 반드시' + '좋은 딜은 묶어서 중간에 리스트도': 묶음 글 Threads 실패 -> 같은 날 다음 실행에 1번만 더 / 리스트 12·15·18시, 🔥 좋은 딜(①②) 먼저 그다음 반응 순
pt9, tt9, tg9d, tries9 = H.th_post, time.time, H.tg, []
def bad9(tok, text, link=None, image=None, tag=None): tries9.append(text); raise OSError("5xx")
H.th_post, H.E["THREADS_TOKEN"] = bad9, "tk"; time.time = lambda: TK("2026-10-12 12:05"); sb9 = {}
for f9 in (lambda: H.th_bundle(sb9, "top12", "리스트", "https://x"), lambda: H.th_retry(sb9)):
    try:
        f9(); raise AssertionError("실패는 예외로(main 알림)")
    except OSError:
        pass
H.th_retry(sb9); assert len(tries9) == 2 and sb9["thretry_20261012_top12"]["done"] == 1  # 1번만 더(세 번째 X)
H.th_post = lambda tok, text, link=None, image=None, tag=None: tries9.append(("ok", text)); H.tg = lambda m, **p: sent.append((m, p)) or {"message_id": 9}; sent.clear()
json.dump([{"t": "2026-10-12 13:00", "text": "🔥 [G마켓] 인기1 (1,000원)", "url": "https://g1", "mid": 1, "pop": 50}, {"t": "2026-10-12 13:10", "text": "🔥 [G마켓] 인기2 (2,000원)", "url": "https://g2", "mid": 2, "pop": 40},
           {"t": "2026-10-12 14:00", "text": "🔥 [토스] 좋은딜 (3,000원)\n\n💡 쿠팡 같은 상품(9,000원)보다 6,000원 쌈", "url": "https://toss.shopping/_m/a", "mid": 3, "own": 1},
           {"t": "2026-10-12 14:10", "text": "🛒 [토스] 약한딜 (3,000원)\n\n🤔 솔직히 특가로는 약한 제품", "url": "https://toss.shopping/_m/b", "mid": 4, "own": 1}], open("posts.json", "w"), ensure_ascii=False)
H.TH_LIST_HOURS = tlh0; time.time = lambda: TK("2026-10-12 15:05"); H.top_deals({})
t9d = sent[-1][1]["text"]; assert "TOP3</b> (15시)" in t9d and t9d.index("좋은딜") < t9d.index("인기1") < t9d.index("인기2") and "약한딜" not in t9d and tries9[-1][0] == "ok"  # 15시 = 12~15시, 좋은 딜 먼저, 🛒(반응 수치 없음) X, Threads에도
H.th_post, H.tg, time.time = pt9, tg9d, tt9; del H.E["THREADS_TOKEN"]; json.dump([], open("posts.json", "w"))
# 9-2e) 상위 딜로 채우기(10/12 18:55 진우, TH_SOLO_FILL): 45분이 됐는데 ①·화장품·② 후보가 없으면 최근 3시간 채널 딜 중 점수 높은 것 1개(같은 점수면 제휴 링크 먼저, 그다음 최근 것) —
#       Threads에 나간 것·🛒·품절(품절 지켜보기 기록) X, ①② 있으면 그게 먼저, 글 틀 그대로(비교 줄 없으면 💸 줄 없음)
assert tfill0 is True
sv9e = (H.TH_SOLO_MAX, H.TH_SOLO_GAP, H.TH_SOLO_RUN, H.th_strong, H.TH_SOLO_FILL, H.http)
H.TH_SOLO_MAX, H.TH_SOLO_GAP, H.TH_SOLO_RUN, H.th_strong, H.TH_SOLO_FILL, H.E["THREADS_TOKEN"], H.http, live_pages = 99, 45 * 60, 1, th_strong0, True, "tk", td_http, set(range(10))
D9e = "2026-10-12"
P9e = [("17:00", "🔥 [롯데온] 오래된 9점 (1,000원)\n\n좋음", "https://x/old", {"s": 9, "mid": 1}),  # 3시간 지남
       ("19:00", "🔥 [카카오] 일반 8점 (2,000원)\n\n좋음", "https://x/k", {"s": 8, "mid": 2}),
       ("19:10", "🔥 [G마켓] 제휴 8점 (3,000원)\n\n좋음\n💡 단위가격: 100g당 300원", "https://link.coupang.com/a/g", {"s": 8, "mid": 3}),
       ("19:20", "🛒 [토스] 약한 9점 (4,000원)\n\n🤔 솔직히 특가로는 약한 제품", "https://toss.shopping/_m/w", {"s": 9, "mid": 4}),
       ("19:25", "🔥 [토스] 품절 9점 (5,000원)\n\n좋음", "https://toss.shopping/_m/o", {"s": 9, "mid": 5}),
       ("19:30", "🔥 [쿠팡] 나간 9점 (6,000원)\n\n좋음", "https://link.coupang.com/a/t", {"s": 9, "mid": 6, "th": 1})]
json.dump([{"t": f"{D9e} {t}", "text": x, "url": u, **e} for t, x, u, e in P9e], open("posts.json", "w"), ensure_ascii=False)
s9e = {"sold_5": {"t": 1, "k": "ev", "it": [[55, "품절 9점", 5000, 1, 1, 0]]}}
def th9e(hm):
    calls.clear(); time.time = lambda: TK(f"{D9e} {hm}"); H.threads_deals(s9e)
    return [parse_qs(urlsplit(u).query)["text"][0] for m, u in calls if "/777/threads?" in u]
m9 = th9e("20:05"); assert len(m9) == 1 and "제휴 8점" in m9[0] and "💸" not in m9[0] and m9[0].startswith(H.DISCLOSURE + "\n\n🔥 [G마켓] 제휴 8점 (3,000원)\n\n좋음\n💡 단위가격") and "👋 팔로우" in m9[0]  # 같은 8점이면 제휴 링크 먼저(🛒·품절·나간 것·3시간 지난 것 X), 틀 그대로
assert th9e("20:30") == [] and th9e("20:51") == []  # 45분 간격 그대로 · 남은 일반 8점(카카오 원글)은 수수료 링크 아님 -> Threads X(10/19 밤 진우)
json.dump([{"t": f"{D9e} 21:00", "text": "🔥 [카카오] 다른 9점 (1,000원)\n\n좋음", "url": "https://link.coupang.com/a/k9", "s": 9, "mid": 7}, {"t": f"{D9e} 21:05", "text": "🔥 [토스] 최저가 5점 (1,000원)\n\n토스 하루특가 · 30일 내 최저가", "url": "https://toss.shopping/_m/z", "s": 5, "mid": 8}], open("posts.json", "w"), ensure_ascii=False)
m9 = th9e("21:40"); assert len(m9) == 1 and "최저가 5점" in m9[0]  # ①② 후보가 있으면 그게 먼저(점수 낮아도)
H.TH_SOLO_FILL = False; json.dump([{"t": f"{D9e} 21:50", "text": "🔥 [카카오] 끔 9점 (1,000원)\n\n좋음", "url": "https://link.coupang.com/a/kf", "s": 9, "mid": 9}], open("posts.json", "w"), ensure_ascii=False)
assert th9e("22:30") == []  # 끄면 예전처럼(①② 없으면 안 올림)
# 변경 전후 채널 게시 수 같음(10/12 19:15 진우 '올리지 마라는 게 아니야, 지금처럼 그대로'): 채움을 켜도 끄도 채널 글(12시 리스트 + 딜 글)은 똑같이 나가고, Threads 쪽만 더해짐
pt9e, tg9e2 = H.th_post, H.tg
def chan9e(fill):
    H.TH_SOLO_FILL, sb, sent9e = fill, {}, []
    H.tg, H.th_post = (lambda m, **p: sent9e.append(m) or {"message_id": 1}), (lambda *a, **k: None)
    json.dump([{"t": f"{D9e} 0{k + 5}:00", "text": f"🔥 [G마켓] 반응{k} (1,000원)\n\n좋음", "url": f"https://g/{k}", "mid": 30 + k, "pop": 9 - k, "s": 8} for k in range(4)]
              + [{"t": "2026-10-11 22:00", "text": "🔥 [토스] 어젯밤 좋은딜 (1,000원)\n\n💡 쿠팡 같은 상품(3,000원)보다 2,000원 쌈", "url": "https://toss.shopping/_m/n", "mid": 40, "own": 1}], open("posts.json", "w"), ensure_ascii=False)
    time.time = lambda: TK(f"{D9e} 12:05"); H.top_deals(sb); H.threads_deals(sb)
    return sent9e, [m for m, u in calls if "/777/threads?" in u]
calls.clear(); c_off = chan9e(False); calls.clear(); c_on = chan9e(True)
assert c_off[0] == c_on[0] == ["sendMessage"]  # 채널 글 수 같음(리스트 1개, threads_deals는 채널에 안 올림)
H.TH_SOLO_FILL = True; sent9e2 = []; H.tg = lambda m, **p: sent9e2.append((m, p)) or {"message_id": 1}; time.time = lambda: TK(f"{D9e} 12:05"); H.top_deals({})
assert "어젯밤 좋은딜" in sent9e2[0][1]["text"] and sent9e2[0][1]["text"].index("어젯밤 좋은딜") < sent9e2[0][1]["text"].index("반응0") and "TOP5" in sent9e2[0][1]["text"]  # 누락 없이: 어젯밤(18시 뒤) Threads에 못 나간 ①②도 12시 리스트에, 먼저
# 💄 화장품 칸(10/12 19:50 진우 '리스트로 만들어도 좋아'): 개별 글이 못 된 화장품 🔥를 12·15·18시 Threads 리스트에 더함 — 기존 딜·링크 그대로, 링크 합쳐 5개까지(넘으면 이름·가격만), 🛒·Threads에 나간 것 X
thp9 = []; H.th_post = lambda tok, text, link=None, image=None, tag=None: thp9.append((text, link)); H.tg = lambda m, **p: {"message_id": 1}; H.E["THREADS_TOKEN"] = "tk"
json.dump([{"t": f"{D9e} 12:{10 + k}", "text": f"🔥 [G마켓] 반응{k} (1,000원)\n\n좋음", "url": f"https://link.coupang.com/a/g{k}", "mid": 50 + k, "pop": 9 - k} for k in range(3)]
          + [{"t": f"{D9e} 13:{10 + k}", "text": f"{H.TOSS_NOTE}\n\n🔥 [토스] 클렌징폼{k} (9,900원)\n\n토스 최대할인가", "url": f"https://toss.shopping/_m/c{k}", "mid": 60 + k, "own": 1} for k in range(3)]
          + [{"t": f"{D9e} 13:20", "text": f"{H.TOSS_NOTE}\n\n🛒 [토스] 약한 선크림 (9,900원)\n\n🤔 솔직히 특가로는 약한 제품", "url": "https://toss.shopping/_m/w", "mid": 70, "own": 1},
             {"t": f"{D9e} 13:30", "text": f"{H.TOSS_NOTE}\n\n🔥 [토스] 나간 리무버 (9,900원)\n\n토스 최대할인가", "url": "https://toss.shopping/_m/t", "mid": 71, "own": 1, "th": 1}], open("posts.json", "w"), ensure_ascii=False)
time.time = lambda: TK(f"{D9e} 15:05"); H.top_deals({}); (t9b, l9b), = thp9
assert t9b.index("반응0") < t9b.index("반응2") < t9b.index("\n\n💄 화장품\n· 클렌징폼0 9,900원\n👉 ") and "클렌징폼1" in t9b and "약한 선크림" not in t9b and "나간 리무버" not in t9b  # 기존 딜 그대로 + 화장품 칸
assert len(set(re.findall(r"https?://\S+", t9b)) | {l9b}) <= 5 and t9b.count("👉") == 5 and "· 클렌징폼2 9,900원" in t9b and len(t9b) <= 480  # 링크 5개까지(3번째 화장품은 이름·가격만)
H.TH_LIST_HOURS = tlh0
H.th_post, H.tg = pt9e, tg9e2
H.TH_SOLO_MAX, H.TH_SOLO_GAP, H.TH_SOLO_RUN, H.th_strong, H.TH_SOLO_FILL, H.http = sv9e; del H.E["THREADS_TOKEN"]; json.dump([], open("posts.json", "w")); time.time = t0
# 9-2f) 토스 딜 = 다른 쇼핑몰 가격 비교 없이 + 게시 시점 가격(10/12 21:05 토스 비즈니스 답변 -> 진우): 채널 새 글·posts.json(사이트·카드·리스트)·Threads·미리보기·재오픈, 토스 아닌 몰은 그대로
assert tnc0 is True and H.TH_TOSS_DR == 30
H.TOSS_NO_CMP, tt9f = True, time.time; time.time = lambda: TK("2026-10-12 21:30")
T9f = f"{H.TOSS_NOTE}\n\n🔥 [토스] 레이데이 비비크림 (10,000원)\n\n토스 최대할인가 · BB크림 4위\n💡 쿠팡 같은 상품(20,500원)보다 10,500원 쌈 · 1개 3,333원꼴\n💡 단위가격: 10ml당 600원 — 쿠팡 같은 상품보다 g당 32% 쌈\n⚠️ 확인할 점: 결제 전 최종가 확인"
c9f, _ = H.strip_cmp(T9f); assert "쿠팡" not in c9f and "💡 단위가격: 10ml당 600원" in c9f and "BB크림 4위" in c9f and H.saving(c9f) is None
assert H.strip_cmp("🛒 [토스] x (1원)\n\n🤔 솔직히 특가로는 약한 제품 — 쿠팡이 470원 더 쌈")[0].endswith("🤔 솔직히 특가로는 약한 제품")  # 🛒 표시는 남김(리스트 메모·🛒 판별)
assert H.th_tier(c9f) == 0 and H.th_tier(c9f.replace("(10,000원)", "(10,000원)\n💰 10,000원 (45%↓)")) == 2 and H.th_tier("🔥 [쿠팡] y (1원)\n\n💰 1원 (45%↓)") == 0  # 토스 = 할인율 30%↑도 ②, 다른 몰은 그대로
json.dump([{"t": "2026-10-12 21:00", "text": T9f, "url": "https://toss.shopping/_m/r", "own": 1, "entities": [{"type": "text_link", "offset": len(T9f.encode("utf-16-le")) // 2 - 2, "length": 2, "url": "https://toss.shopping/_m/r"}]},
           {"t": "2026-10-12 21:05", "text": "🔥 [쿠팡] 휴지 (9,900원)\n\n💡 쿠팡 같은 상품(12,900원)보다 3,000원 쌈", "url": "https://link.coupang.com/a/h"}], open("posts.json", "w"), ensure_ascii=False)
H.toss_clean_posts(); p9f = json.load(open("posts.json"))
assert "쿠팡" not in p9f[0]["text"] and p9f[0]["text"].endswith("⚠️ 확인할 점: 결제 전 최종가 확인") and p9f[0]["entities"][0]["offset"] == len(p9f[0]["text"].encode("utf-16-le")) // 2 - 2 and "3,000원 쌈" in p9f[1]["text"]  # 토스만, 링크 위치 맞게
H.record(T9f, [], "https://toss.shopping/_m/r2"); assert "쿠팡" not in json.load(open("posts.json"))[-1]["text"]  # 새로 기록하는 토스 딜도
# 10/13 08:30 '토스 글 전부 다른 몰 이름 없이'(2차 28개): 💡·🤔·⚠️ 줄은 다른 몰 조각·비교만 남는 조각(절반·비교·차이)만 빼고, '💡 참고: 쿠팡…'·다른 몰 이름 든 다른 줄은 줄째, 제목·고지문·출처 줄은 그대로
for a9, b9 in (("⚠️ 확인할 점: 88% 할인율은 정가 기준이라 쿠팡 가격 비교가 더 정확 · 토스 앱 가격(10/10 18시) 기준", "⚠️ 확인할 점: 토스 앱 가격(10/10 18시) 기준"),
               ("💡 단위가격: 100g당 798원 — 쿠팡 미국산 삼겹살 4kg(63,720원 와우가, 100g당 1,593원)의 절반 값", "💡 단위가격: 100g당 798원"),
               ("💡 쿠팡에선 같은 모델을 못 찾아 비교 못 함 — 토스 30일 내 최저가 기준", "💡 토스 30일 내 최저가 기준"), ("💡 참고: 쿠팡 다른 판매자 전라도 파김치 1kg 14,900원 — 거의 절반 값", None),
               ("💡 참고: 쿠팡 애슐리 크림빠네 756g 2개 21,880원 — 이 세트는 4종", None), ("🤔 솔직히 특가로는 약한 제품 — 100ml당 430원인데 쿠팡이 조금 쌈", "🤔 솔직히 특가로는 약한 제품"),
               ("💡 1개 1,750원꼴 — 쿠팡 애슐리 케이준 볶음밥 6개(다른 맛) 15,890원", "💡 1개 1,750원꼴"), ("올리브영보다 싸요", None)):
    r9 = H.strip_cmp(f"{H.TOSS_NOTE}\n\n🔥 [토스] 쿠팡 없는 제목 (1원)\n\n{a9}\n\n출처: 뽐뿌")[0]
    assert r9 == f"{H.TOSS_NOTE}\n\n🔥 [토스] 쿠팡 없는 제목 (1원)\n\n" + (f"{b9}\n\n" if b9 else "\n") + "출처: 뽐뿌", (a9, r9)
# Threads 개별 글: 토스 = 💸 쿠팡 줄 X·게시 시점 가격, 토스 아님 = 그대로
s9f, live_pages, H.E["THREADS_TOKEN"], h9f, f9f = {}, set(range(5)), "tk", H.http, H.TH_SOLO_FILL
H.http, H.TH_SOLO_FILL = td_http, True
json.dump([{"t": "2026-10-12 21:00", "text": c9f.replace("BB크림 4위", "BB크림 1위"), "url": "https://toss.shopping/_m/r", "own": 1}], open("posts.json", "w"), ensure_ascii=False)
calls.clear(); H.threads_deals(s9f); th9f = [parse_qs(urlsplit(u).query)["text"][0] for m, u in calls if "/777/threads?" in u][0]
assert "💸" not in th9f and "쿠팡" not in th9f and "⚠️ 10/12 21:00 게시 시점 가격" in th9f and th9f.startswith(H.TOSS_NOTE)
assert "👋 팔로우하면 매일 이런 특가가 피드에 떠요" in th9f and "가격 비교" not in th9f and H.th_follow(False) == "👋 팔로우하면 매일 이런 가격 비교가 피드에 떠요"  # 10/13 00:35 진우: 팔로우 줄도 토스 글만 '특가', 다른 몰은 그대로
# 미리보기: 토스 = 같은 상품 쿠팡 차이·'쿠팡과 N원 차이' X
evf, H.EVENTS = H.EVENTS, "ev9f.json"; json.dump([{"at": "2026-10-12 22:20", "url": "https://toss.shopping/_m/a", "deal": True, "name": "a", "text": "🔥 <b>[토스] 앙쥬 (9,900원)</b>\n\n💡 쿠팡 같은 상품(15,460원)보다 5,560원 쌈"},
                                                  {"at": "2026-10-12 22:30", "url": "https://toss.shopping/_m/b", "deal": True, "name": "b", "text": "🛒 <b>[토스] 미샤 (10,800원)</b>\n\n🤔 솔직히 특가로는 약한 제품 — 쿠팡과 1,000원 차이"}], open(H.EVENTS, "w"), ensure_ascii=False)
nd9 = H.night_deals({}, "2026-10-12 22:00", "2026-10-13 08:00"); assert [(d["sv"], d["weak"]) for d in nd9] == [(None, False), (None, "특가로는 약함")] and "쿠팡" not in "".join(H.night_line(d) for d in nd9)
H.EVENTS = evf
# 재오픈: 비교 줄 X, 게시 시점 가격
rt9f = H.reopen_text({}, {"url": "https://toss.shopping/_m/W", "n": "x", "title": "해피달링 샤워기", "warn": "⚠️ 확인할 점: 1인 1개", "icon": "🔥", "cmp": "💡 쿠팡 같은 상품(14,900원)보다 7,280원 쌈", "p0": 7620}, 7620, False, False)
assert "쿠팡" not in rt9f and "💸" not in rt9f and "⚠️ 10/12 21:30 게시 시점 가격" in rt9f and "이런 특가가 피드" in rt9f
H.http, H.TH_SOLO_FILL, H.TOSS_NO_CMP, time.time = h9f, f9f, False, tt9f; del H.E["THREADS_TOKEN"]; json.dump([], open("posts.json", "w"))
# 9-2g) 10/12 22:45·22:50 진우 '토스 인기 생필품·많이 팔리는 제품 꾸준하게': 17시 생필품(식품·생활용품) 리스트도 Threads(대가성 문구·게시 시점 가격·링크 5개·비교 X),
#       토스 회차(하루특가·베스트·생필품) 픽 = Threads 채움 후보 — 45분 칸이 비었고 ①·화장품·② 없으면 토스 픽 먼저(회차 1순위·생필품 먼저), 품절 X, 사이트·posts.json X
#       + 채널 옛 토스 글 비교 줄 빼기(tossfix.json 번호, 버튼 글자·링크 그대로, 품절 줄 그대로, 한 실행 8개) + Threads·인스타 비교 글 목록(로그, 하루 1번, 읽기만)
assert ttf0 == ("day", "best", "cat") and H.TOSS_FIX_RUN == 8 and H.CMP_REPORT is True
H.TH_TOSS_FILL, H.TH_TOSS_KINDS, H.TOSS_NO_CMP, H.TH_SOLO_GAP, H.TH_SOLO_MAX, H.TH_SOLO_FILL = ttf0, ("best", "cat"), True, 45 * 60, 99, True
H.TH_BEAUTY_MIN, H.TH_BEAUTY_MAX, H.TH_LIST_HOURS, H.th_strong, H.TH_SOLO_RUN = 1, 7, tlh0, th_strong0, 1
sv9g = (H.http, H.tg, H.ai_pick, H.time.sleep, H.EVENTS, time.time, H.HAS_TOSS)
g_calls, g_sent = [], []
def g_http(url, body=None, headers=None, method=None):
    g_calls.append((method or "GET", url))
    if url.startswith(H.THREADS):
        if "/me?" in url: return json.dumps({"id": "777"})
        return json.dumps({"id": "c1"})
    if "/p/" in url: return ""
    if url == "https://oauth2.cert.toss.im/token": return json.dumps({"access_token": "TK", "expires_in": 31535999})
    return cat_http(url, body, headers, method)
H.http, H.tg, H.time.sleep, H.EVENTS, H.HAS_TOSS, H.E["THREADS_TOKEN"] = g_http, (lambda m, **p: g_sent.append((m, p)) or {"message_id": 900 + len(g_sent)}), (lambda s: None), "ev9g.json", True, "tk"
json.dump([], open("ev9g.json", "w")); json.dump([], open("posts.json", "w"))
H.ai_pick = lambda prompt, lines: [{"i": 1, "score": 9, "comment": "1순위"}, {"i": 0, "score": 8, "comment": "2순위"}]
s9g = {}; time.time = lambda: TK("2026-10-13 17:10"); H.toss_deals(s9g, "cat")
gt = lambda: [parse_qs(urlsplit(u).query)["text"][0] for m, u in g_calls if "/777/threads?" in u]
l9g = gt()
assert len(l9g) == 1 and l9g[0].startswith(H.TOSS_NOTE) and "베스트 중 살 만한 2개" in l9g[0] and "⚠️ 10/13 17:10 게시 시점 가격" in l9g[0] and "쿠팡" not in l9g[0]  # 17시 생필품 리스트 Threads
assert len(set(re.findall(r"https?://\S+", l9g[0]))) <= 5 and len(l9g[0]) <= 500 and "thretry_20261013_toss17" not in s9g
assert [v.get("tail") for k, v in s9g.items() if k.startswith("sold_")] == ["\n\n⚠️ 10/13 17:10 게시 시점 가격"]  # 품절 고칠 때도 게시 시점 줄 그대로(10/22 — 예전엔 빠짐)
q9g = s9g["thtoss"]["q"]; assert [(x["r"], x["k"], x["s"], x["link"]) for x in q9g] == [(0, "cat", 9, "https://toss.im/_m/21"), (1, "cat", 8, "https://toss.im/_m/1")]
assert q9g[0]["text"].startswith(H.TOSS_NOTE + "\n\n💙 토스 특가 · 생필품 베스트 ") and "위 🔥\n카테21\n7,900원" in q9g[0]["text"] and "👉 1순위" in q9g[0]["text"] and "⚠️ 10/13 17:10 게시 시점 가격" in q9g[0]["text"] and q9g[0]["text"].endswith("🛒 https://toss.im/_m/21\n📲 실시간 알림 t.me/hotdeal_pick")
assert json.load(open("posts.json")) == []  # API 상품은 posts.json(사이트) X
# 채움: 45분 칸 + ①·화장품·② 없음 -> 토스 픽 먼저(채널 일반 딜보다), 1회 1개, 줄에서 빠짐, 다음은 45분 뒤
json.dump([{"t": "2026-10-13 17:00", "text": "🔥 [쿠팡] 일반9점 (3,000원)\n\n좋음", "url": "https://link.coupang.com/a/9", "s": 9, "mid": 1}], open("posts.json", "w"), ensure_ascii=False)
g_calls.clear(); time.time = lambda: TK("2026-10-13 17:20"); H.threads_deals(s9g); f9g = gt(); assert len(f9g) == 1 and "일반9점" in f9g[0]  # Threads 리스트로 막 나간 상품은 45분 뒤부터(같은 상품 연달아 X)
s9g["thsolo_20261013"]["last"] = 0; json.dump([{"t": "2026-10-13 17:50", "text": "🔥 [쿠팡] 다른9점 (3,000원)\n\n좋음", "url": "https://link.coupang.com/a/7", "s": 9, "mid": 4}], open("posts.json", "w"), ensure_ascii=False)  # 채움: 토스 픽이 채널 일반 딜보다 먼저
g_calls.clear(); time.time = lambda: TK("2026-10-13 17:56"); H.threads_deals(s9g)
f9g = gt(); assert len(f9g) == 1 and "카테21" in f9g[0] and [x["id"] for x in s9g["thtoss"]["q"]] == [1] and s9g["thsolo_20261013"]["n"] == 2
g_calls.clear(); time.time = lambda: TK("2026-10-13 18:20"); H.threads_deals(s9g); assert gt() == []  # 45분 간격 그대로
s9g["sold_950"] = {"t": 1, "d": "2026-10-13", "k": "top", "it": [[1, "카테1", 7900, 0, 1, 0]]}  # 2순위가 품절 -> 채움에서 빠지고 채널 일반 딜로
json.dump([{"t": "2026-10-13 18:30", "text": "🔥 [쿠팡] 저녁9점 (3,000원)\n\n좋음", "url": "https://link.coupang.com/a/8", "s": 9, "mid": 3}], open("posts.json", "w"), ensure_ascii=False)
g_calls.clear(); time.time = lambda: TK("2026-10-13 18:42"); H.threads_deals(s9g); f9g = gt(); assert len(f9g) == 1 and "저녁9점" in f9g[0]
# ①② 좋은 딜이 있으면 그게 먼저(토스 픽은 채움 때만)
s9g.pop("sold_950"); json.dump([{"t": "2026-10-13 18:30", "text": "🔥 [쿠팡] 휴지 (9,000원)\n\n💡 쿠팡 같은 상품(10,000원)보다 1,000원 쌈", "url": "https://link.coupang.com/a/1", "s": 8, "mid": 2}], open("posts.json", "w"), ensure_ascii=False)
s9g["thsolo_20261013"]["last"] = 0; g_calls.clear(); time.time = lambda: TK("2026-10-13 18:52"); H.threads_deals(s9g); f9g = gt(); assert len(f9g) == 1 and "휴지" in f9g[0] and [x["id"] for x in s9g["thtoss"]["q"]] == [1]
g_calls.clear(); time.time = lambda: TK("2026-10-13 20:20"); H.threads_deals(s9g); assert gt() == []  # 3시간 지난 토스 픽은 안 올림(식은 글)
H.TH_TOSS_FILL = (); s9g = {"tb_1": 1}; g_calls.clear(); time.time = lambda: TK("2026-10-13 17:10"); H.toss_deals(s9g, "cat"); assert "thtoss" not in s9g and len(gt()) == 1  # 끄면 줄 X(리스트는 그대로)
H.TH_TOSS_FILL = ttf0; s9g = {}; g_calls.clear(); H.ai_pick = lambda prompt, lines: [{"i": 0, "score": 8, "comment": "가"}]
time.time = lambda: TK("2026-10-13 15:10"); H.toss_deals(s9g, "beauty"); assert "thtoss" not in s9g  # 뷰티 회차는 예전 그대로(화장품 자리 채움)
# 재업로드(10/12 23:05 진우, events "re": true): 같은 진우 링크로 전에 나간 상품도 Threads 개별 글로 — 다음 45분 칸 맨 먼저, 화장품 하루 한도에서 뺌(세지도 않음)
json.dump([{"at": "2026-10-13 09:00", "url": "https://toss.shopping/_m/NT", "deal": True, "re": True, "button": "b", "text": "x"}], open("ev9g.json", "w"))
json.dump([{"t": "2026-10-13 09:00", "text": f"{H.TOSS_NOTE}\n\n🔥 [토스] 비비크림 (10,000원)\n\n토스 할인가 · 86% 할인 · BB크림 1위", "url": "https://toss.shopping/_m/NT", "own": 1, "mid": 5},
           {"t": "2026-10-13 09:02", "text": "🔥 [쿠팡] 휴지 (9,000원)\n\n💡 쿠팡 같은 상품(10,000원)보다 1,000원 쌈", "url": "https://link.coupang.com/a/1", "s": 8, "mid": 6}], open("posts.json", "w"), ensure_ascii=False)
s9g = {"thsolo_20261013": {"t": 1, "n": 9, "b": 7, "last": 0}}; g_calls.clear(); time.time = lambda: TK("2026-10-13 09:10"); H.threads_deals(s9g)
f9g = gt(); assert len(f9g) == 1 and "비비크림" in f9g[0] and s9g["thsolo_20261013"]["b"] == 7 and s9g["thsolo_20261013"]["n"] == 10  # 화장품 7개 찼어도, ① 휴지보다 먼저
# 채널 옛 토스 글 비교 줄 빼기
json.dump({"mids": [31, 32, 33]}, open("tossfix.json", "w"))
P9g = [{"t": "2026-10-10 20:00", "text": f"{H.TOSS_NOTE}\n\n🔥 [토스] 생수 (5,000원)\n\n싸요", "entities": [{"type": "bold", "offset": 0, "length": 3}], "url": "https://toss.shopping/_m/A", "mid": 31},
       {"t": "2026-10-11 09:00", "text": f"{H.TOSS_NOTE}\n\n🔥 [토스] 젤리 (8,900원)\n\n좋음", "entities": [], "url": "https://toss.shopping/_m/B", "mid": 32, "own": 1}]
json.dump(P9g, open("posts.json", "w"), ensure_ascii=False)
json.dump([{"at": "2026-10-11 08:00", "url": "https://toss.shopping/_m/B", "button": "🛒 8,900원 구매하기", "text": "x"}, {"at": "2026-10-12 08:00", "url": "https://toss.shopping/_m/B", "button": "나중 글", "text": "y"}], open("ev9g.json", "w"), ensure_ascii=False)
s9g = {"sold_33": {"t": 1, "d": "2026-10-11", "k": "ev", "pre": f"<i>{H.TOSS_NOTE}</i>\n\n", "body": "🔥 <b>[토스] 사과 (8,730원)</b>\n\n💡 쿠팡 같은 상품(17,900원)보다 9,170원 쌈\n👉 맛있음",
                    "btn": "🛒 8,730원 구매하기", "url": "https://toss.shopping/_m/C", "n": "사과", "p": 8730, "it": [[5, "사과", 8730, 1, 2, 0]]}}
H.TOSS_FIX_RUN, g_sent[:] = 2, []; H.toss_fix_channel(s9g)
assert [(m, p["message_id"]) for m, p in g_sent] == [("editMessageText", 31), ("editMessageText", 32)] and s9g["tossfix"]["done"] == [31, 32]
assert g_sent[0][1]["text"] == P9g[0]["text"] and g_sent[0][1]["entities"] == P9g[0]["entities"] and g_sent[0][1]["reply_markup"] == {"inline_keyboard": [[{"text": H.buy_label("[토스] 생수 (5,000원)"), "url": "https://toss.shopping/_m/A"}]]}
assert g_sent[1][1]["reply_markup"] == {"inline_keyboard": [[{"text": "🛒 8,900원 구매하기", "url": "https://toss.shopping/_m/B"}]]}  # 예약 버튼 글자 그대로(그 글 전 예약)
assert "쿠팡" not in s9g["sold_33"]["body"]  # 품절 지켜보기 기록도 비교 X(품절 줄 고칠 때 돌아오지 않게)
g_sent[:] = []; H.toss_fix_channel(s9g); (m9, p9), = g_sent
assert p9["message_id"] == 33 and p9["parse_mode"] == "HTML" and "⛔ <b>특가 끝</b>" in p9["text"] and "쿠팡" not in p9["text"] and p9["reply_markup"]["inline_keyboard"][0][0] == {"text": "특가 끝", "url": "https://toss.shopping/_m/C"}  # 품절 줄·버튼 글자 그대로
g_sent[:] = []; H.toss_fix_channel(s9g); assert not g_sent  # 글마다 1번만
json.dump({"v": 2, "mids": [31]}, open("tossfix.json", "w")); g_sent[:] = []; H.toss_fix_channel(s9g); assert [p["message_id"] for m, p in g_sent] == [31] and s9g["tossfix2"]["done"] == [31]  # 목록 v2 = 처음부터(2차 28개)
# 묶음 글(posts.json에 없음, 10/14): 관리자 방에 전달해 읽고 비교 조각만 바꿈 -> 엔티티 오프셋 맞춤·버튼 그대로·전달본 지움, 번호 버튼을 못 읽으면 안 고침
pv = f"{H.TOSS_NOTE}\n\n🌙 오늘 밤 특가 미리보기 (10/11 · 2개)\n\n22:20 🔥 폼클렌징 11,900원 · 💡 쿠팡 같은 상품보다 3,450원 쌈\n22:30 🔥 크림 8,000원\n\n🔔 매일"
i1, i2 = pv.index("폼클렌징"), pv.index("크림 8")
u9 = lambda s: len(s.encode("utf-16-le")) // 2
e9 = [{"type": "italic", "offset": 0, "length": u9(H.TOSS_NOTE)}, {"type": "text_link", "offset": u9(pv[:i1]), "length": 4, "url": "https://toss.shopping/_m/X"}, {"type": "text_link", "offset": u9(pv[:i2]), "length": 2, "url": "https://toss.shopping/_m/Y"}]
t9, n9 = H.cut_cmp(pv, e9)
assert "쿠팡" not in t9 and "폼클렌징 11,900원\n22:30" in t9 and n9[:2] == e9[:2] and [t9_ for t9_ in [(lambda e: t9.encode("utf-16-le")[2 * e["offset"]:2 * (e["offset"] + e["length"])].decode("utf-16-le"))(n9[2])]] == ["크림"]
tp = f"{H.TOSS_NOTE}\n\n🏆 지금 살 만한 딜 TOP2 (12시)\n{H.TOP_SUB}, 그다음 뽐뿌·클리앙 조회수·추천 순\n\n1️⃣ 비비크림"
t9, n9 = H.cut_cmp(tp, [{"type": "bold", "offset": u9(tp[:tp.index("비비")]), "length": 4}, {"type": "bold", "offset": u9(tp[:tp.index(H.TOP_SUB) - 1]) - 3, "length": 50}])
assert H.TOP_SUB_TOSS in t9 and "쿠팡" not in t9 and t9.encode("utf-16-le")[2 * n9[0]["offset"]:2 * (n9[0]["offset"] + 4)].decode("utf-16-le") == "비비크림" and n9[1]["length"] == 50 + u9(H.TOP_SUB_TOSS) - u9(H.TOP_SUB)
fw = {481: {"message_id": 77, "text": pv, "entities": e9}, 565: {"message_id": 78, "text": tp, "entities": [], "reply_markup": {"inline_keyboard": [[{"text": "1️⃣ 비비크림", "url": "https://toss.shopping/_m/Z"}]]}},
      566: {"message_id": 79, "text": tp, "entities": []}, 567: {"message_id": 80, "text": "그대로 1️⃣", "entities": []}}
tgf = H.tg; H.tg = lambda m, **p: g_sent.append((m, p)) or (fw.get(p["message_id"]) if m == "forwardMessage" else {"message_id": 1})
json.dump({"v": 3, "mids": [481, 565, 566, 567]}, open("tossfix.json", "w")); H.TOSS_FIX_RUN, g_sent[:] = 8, []; s9h = {}; H.toss_fix_channel(s9h); H.tg = tgf
assert [(m, p["message_id"]) for m, p in g_sent if m != "forwardMessage"] == [("editMessageText", 481), ("deleteMessage", 77), ("editMessageText", 565), ("deleteMessage", 78), ("deleteMessage", 79), ("deleteMessage", 80)] and s9h["tossfix3"]["done"] == [481, 565, 566, 567]
ed = [p for m, p in g_sent if m == "editMessageText"]
assert "reply_markup" not in ed[0] and "쿠팡" not in ed[0]["text"] and ed[1]["reply_markup"] == fw[565]["reply_markup"] and H.TOP_SUB_TOSS in ed[1]["text"] and all(p["chat_id"] == H.ADMIN for m, p in g_sent if m == "forwardMessage")
H.TOSS_FIX_RUN = 8
# Threads·인스타 비교 글 목록(로그): 토스 글 + 비교 있는 것만, 출처·하루특가·지금 목록 가격
json.dump([{"t": "2026-10-11 09:00", "text": "x", "url": "https://toss.shopping/_m/B"}], open("posts.json", "w"))
TH9g = [{"id": "1", "timestamp": "2026-10-11T00:20:00+0000", "permalink": "https://threads.net/p/1", "text": f"{H.TOSS_NOTE}\n\n💸 쿠팡보다 1,800원 싸요\n🔥 [토스] 탑프룻 망고젤리 (8,900원)\n\n토스 하루특가 · 30일 최저가\n\n👉 {H.SITE}p/0.html?ref=th"},
        {"id": "2", "timestamp": "2026-10-12T00:20:00+0000", "permalink": "https://threads.net/p/2", "text": f"{H.DISCLOSURE}\n\n💸 쿠팡보다 1,000원 싸요\n🔥 [G마켓] 휴지 (9,000원)"},
        {"id": "3", "timestamp": "2026-10-12T01:20:00+0000", "permalink": "https://threads.net/p/3", "text": f"{H.TOSS_NOTE}\n\n🔥 카테21\n💰 7,900원\n\n🛒 https://toss.im/_m/21"},
        {"id": "4", "timestamp": "2026-10-12T02:20:00+0000", "permalink": "https://threads.net/p/4", "text": f"{H.TOSS_NOTE}\n\n🔔 다시 열렸어요\n💸 쿠팡보다 7,280원 싸요\n🔥 [토스] 해피달링 샤워기 (7,620원)\n\n🛒 https://toss.im/_m/77"}]
def cmp_http(url, body=None, headers=None, method=None):
    if "/me?" in url: return json.dumps({"id": "777"})
    if "/777/threads?" in url: return json.dumps({"data": TH9g[:2], "paging": {"next": "https://graph.threads.net/v1.0/777/threads?after=x"}} if "after=" not in url else {"data": TH9g[2:]})
    if "/media?" in url: return json.dumps({"data": [{"id": "9", "timestamp": "2026-10-11T09:00:00+0000", "permalink": "https://ig/p/9", "caption": f"{H.TOSS_NOTE}\n\n1. 생수"}]})
    raise AssertionError(url)
import io, contextlib
H.http, s9g = cmp_http, {"tosscache": {"t": 1, "items": [[77, "해피달링 샤워기", 7300, TK("2026-10-13 09:00")]]}}
H.E.update(IG_TOKEN="pt", IG_USER_ID="178"); time.time = lambda: TK("2026-10-13 10:00")
with contextlib.redirect_stdout(io.StringIO()) as o9:
    H.cmp_report(s9g); H.cmp_report(s9g)
r9 = [l for l in o9.getvalue().split("\n") if l.startswith("cmp ")]
assert len(r9) == 3 and r9[-1].startswith("cmp 끝 · Threads 글 4 · 인스타 글 1") and "threads_delete 없음" in r9[-1]  # 하루 1번, 토스 아닌 글·비교 없는 글·인스타 캡션(제목만) X
assert r9[0].startswith("cmp th 10-11 09:20 | 진우 쉐어링크 | 하루특가 끝남(재업로드 X) | 🔥 [토스] 탑프룻 망고젤리 (8,900원) | 💸 쿠팡보다 1,800원 싸요 | 지금 목록에 같은 이름 없음 | https://threads.net/p/1")
assert r9[1].startswith("cmp th 10-12 11:20 | 토스 API | - | 🔥 [토스] 해피달링 샤워기 (7,620원) | 💸 쿠팡보다 7,280원 싸요 | 지금 토스 목록 7,300원 |")
del H.E["IG_TOKEN"], H.E["IG_USER_ID"], H.E["THREADS_TOKEN"]
H.http, H.tg, H.ai_pick, H.time.sleep, H.EVENTS, time.time, H.HAS_TOSS = sv9g
H.TH_TOSS_FILL, H.TH_TOSS_KINDS, H.TOSS_NO_CMP, H.TH_SOLO_GAP, H.TH_SOLO_MAX, H.TH_SOLO_FILL, H.TH_BEAUTY_MIN, H.TH_BEAUTY_MAX = (), ("day", "best", "cat", "beauty", "special"), False, 0, 99, False, 0, 99
H.th_strong, H.TH_SOLO_RUN = (lambda plain: "특가로는 약한 제품" not in plain), 3; json.dump([], open("posts.json", "w"))
# 9-2i) 10/13 22:30 진우 '토스 쇼핑에서 추출해서 자동으로 — 매시 1개': 8~23시 매시 첫 실행에 토스 API 상품 개별 글 1개(진우 예약 시각은 건너뜀), 출처 돌아가며(순위·화장품·생필품·하루특가),
#       품절·3일 안 게시·오늘 진우 예약 이름·이름 예약 id 빼고 7점↑ 최고점, 진우 예약 글 틀(문구·제목·정보 줄·💡·⚠️ 게시 시점·버튼), 품절 지켜보기·Threads 채움 후보, posts.json X
assert tsh0 == range(0, 24) and H.TOSS_SOLO_MIN == 7  # 10/22 진우 '새벽에도' -> 0~23시
sv9i = (H.http, H.tg, H.ai_pick, H.EVENTS, time.time, H.HAS_TOSS, H.TOSS_SOLO_HOURS)
i_calls, i_sent, i_prompts = [], [], []; tgm0, H.TOSS_GAP_MIN = H.TOSS_GAP_MIN, 0  # 매시 1개만 먼저(빈틈 채움은 9-2j)
LST9 = {"best-selling": [{"tacaItemId": k, "displayName": f"베스트{k}", "displayPrice": 9900, "discountRate": 40, "reviewScore": 4.8, "reviewCount": 1234, "isSoldOut": k == 3} for k in (1, 2, 3, 4)],
        "today-deals": [{"tacaItemId": 50, "displayName": "하루특가50", "displayPrice": 5000, "isSoldOut": False}], "best-categories/400": [{"tacaItemId": 41, "displayName": "뷰티41", "displayPrice": 12000, "isSoldOut": False}]}
def i_http(url, body=None, headers=None, method=None):
    i_calls.append(url)
    if url == "https://oauth2.cert.toss.im/token": return json.dumps({"access_token": "TK", "expires_in": 31535999})
    if url.endswith("/categories"): return json.dumps({"resultType": "SUCCESS", "success": {"categories": [{"categoryId": 200, "displayName": "식품"}, {"categoryId": 300, "displayName": "생활용품"}, {"categoryId": 400, "displayName": "뷰티"}]}})
    if url.endswith("/links"): return json.dumps({"resultType": "SUCCESS", "success": {"shortUrl": f"https://toss.im/_m/S{body['tacaItemId']}"}})
    k = next(k for k in LST9 if f"/products/{k}?" in url) if any(f"/products/{k}?" in url for k in LST9) else None
    if k: return json.dumps({"resultType": "SUCCESS", "success": {"items": LST9[k]}})
    if "/products/best-categories/" in url: return json.dumps({"resultType": "SUCCESS", "success": {"items": []}})
    raise AssertionError(url)
H.http, H.HAS_TOSS, H.TOSS_SOLO_HOURS, H.EVENTS, nc9i, H.TOSS_NO_CMP = i_http, True, tsh0, "ev9i.json", H.TOSS_NO_CMP, True
H.tg = lambda m, **p: i_sent.append((m, p)) or {"message_id": 700 + len(i_sent)}
H.ai_pick = lambda prompt, lines: i_prompts.append((prompt, lines)) or [{"i": 0, "score": 8, "comment": "1개 9,900원 · 10개입"}, {"i": 1, "score": 9, "comment": "롤당 330원"}]
json.dump([{"at": "2026-10-14 11:30", "url": "https://toss.shopping/_m/j", "deal": True, "name": "베스트1", "text": "x", "button": "b"}], open("ev9i.json", "w"), ensure_ascii=False)
json.dump([], open("posts.json", "w")); H.E["THREADS_TOKEN"] = "tk"
s9i = {"tb_4": {"t": 1, "n": "베스트4"}}; time.time = lambda: TK("2026-10-14 12:05"); H.toss_solo(s9i)  # 12시 = 순위(12 % 4 = 0)
(m9i, p9i), = i_sent
assert [l.split(" |")[0] for l in i_prompts[0][1]] == ["베스트2"]  # 품절(3)·3일 안 게시(4)·오늘 진우 예약 이름(1) 빼고
assert H.TOSS_NOTE in p9i["text"].split("🔥")[0]  # 대가성 문구 맨 앞(진우 예약 글과 같은 머리)
assert "💙 토스 특가 · 많이 팔린 순위 2위 🔥\n<b>베스트2</b>\n9,900원 (40%↓) · ⭐ 4.8 (1,234)\n👉 1개 9,900원 · 10개입\n⚠️ 10/14 12:05 게시 시점 가격" in p9i["text"] and "쿠팡" not in p9i["text"], p9i["text"]  # 10/22 토스 몰별 틀(💙 머리 줄 출처 · 가격 (할인) · ⭐ · 🙋/👍 없으면 Claude 한 줄 · 게시 시점)
assert p9i["reply_markup"] == {"inline_keyboard": [[{"text": "💙 토스에서 9,900원", "url": "https://toss.im/_m/S2"}]]} and p9i["chat_id"] == H.CHANNEL and p9i["parse_mode"] == "HTML"
assert "tb_2" in s9i and s9i["sold_701"]["it"] == [[2, "베스트2", 9900, 0, 0, 0]] and s9i["sold_701"]["btn"] == "💙 토스에서 9,900원" and "tsolo_20261014_12" in s9i  # 품절 지켜보기·묶음 회차에서 빠짐
q9i = s9i["thtoss"]["q"][-1]; assert q9i["k"] == "solo" and q9i["link"] == "https://toss.im/_m/S2" and q9i["text"].startswith(H.TOSS_NOTE) and "많이 팔린 순위 2위" in q9i["text"] and "게시 시점 가격" in q9i["text"]  # Threads 채움 후보
assert json.load(open("posts.json")) == []  # TOSS_SITE False(10/24 10시 보류) = 사이트 X — 켜면 사이트 전용 진열(9-47)
assert i_prompts[0][0].startswith(H.SOLO_PROMPT) and "말투 — " in i_prompts[0][0] and "쿠팡 등 다른 쇼핑몰 가격 비교 언급 금지" in H.SOLO_PROMPT and "사실 한 줄" in H.SOLO_PROMPT
i_sent.clear(); i_calls.clear(); H.toss_solo(s9i); assert not i_sent and not i_calls  # 그 시각 1번
s9e = {}; time.time = lambda: TK("2026-10-14 11:40"); H.toss_solo(s9e); assert not i_sent and not i_calls and s9e == {}  # 진우 예약 11:30 앞뒤 10분 = 쉼(API도 안 부름, 기록 X -> 다음 실행에 다시)
time.time = lambda: TK("2026-10-14 11:20"); H.toss_solo(s9e); assert not i_sent and not i_calls and s9e == {}  # 10분 앞도 쉼
time.time = lambda: TK("2026-10-14 07:59"); H.toss_solo({}); assert i_calls and len(i_sent) == 1; i_sent.clear(); i_calls.clear()  # 10/22~ 0~8시도 매시 1개(밤 무음은 tg가 — 9-26)
time.time = lambda: TK("2026-10-14 11:41"); H.toss_solo(s9e); assert len(i_sent) == 1 and "tsolo_20261014_11" in s9e  # 예약 있는 시각도 앞뒤 10분 밖이면 올림(10/15 — 예전엔 그 시각 통째로 건너뜀)
i_sent.clear(); i_calls.clear()
H.ai_pick = lambda prompt, lines: i_prompts.append((prompt, lines)) or ([{"i": 0, "score": 6, "comment": "x"}] if "하루특가50" in lines[0] else [{"i": 0, "score": 8, "comment": "롤당 330원"}])
i_sent.clear(); i_calls.clear(); time.time = lambda: TK("2026-10-14 15:05"); s9j = {}; H.toss_solo(s9j)  # 15시 = 하루특가(15 % 4 = 3) 6점 -> 다음 출처(순위)
assert len(i_sent) == 1 and "베스트1" not in i_sent[0][1]["text"] and "💙 토스 특가 · 많이 팔린 순위" in i_sent[0][1]["text"] and sum("/products/" in u and "/links" not in u for u in i_calls) == 2  # 출처 2곳까지
H.ai_pick = lambda prompt, lines: [{"i": 0, "score": 5, "comment": "x"}]; i_sent.clear(); time.time = lambda: TK("2026-10-14 13:05"); s9k = {}; H.toss_solo(s9k)
assert not i_sent and "tsolo_20261014_13" in s9k  # 7점↑ 없으면 그 시각은 끝(다시 안 물음)
time.time = lambda: TK("2026-10-14 08:05"); H.ai_pick = lambda prompt, lines: [{"i": 0, "score": 9, "comment": "개당 사실"}]; i_sent.clear(); H.toss_solo({})  # 8시 = 순위 · 하루특가는 9시 전 X
assert "💙 토스 특가 · 많이 팔린 순위" in i_sent[0][1]["text"]
assert "toss_relink, toss_picks, toss_solo, toss_soldout" in inspect.getsource(H.main) and H.ALERT_STEPS["toss_solo"] == "토스 자동 개별 글"
# 9-2j) 10/15 진우 '꾸준하게': 8~23시 채널 딜 글이 마지막 글 뒤 TOSS_GAP_MIN(30)분 넘게 없으면 그 실행에 토스 1개 더(같은 후보·틀·거르기) — 못 찾으면 30분 뒤 다시(API·Claude 아낌),
#       진우 예약 앞뒤 10분은 쉼, 마지막 글 = tg() 채널 올리기 기록(재오픈 답장·📋 모아보기 X, 다른 채팅 X) · seen(지난 실행) · posts.json
assert tgm0 == 30 and H.TOSS_EV_PAD == 600; H.TOSS_GAP_MIN, H.RUN["ch_last"] = tgm0, 0
json.dump([{"t": "2026-10-14 13:20", "text": "🔥 [쿠팡] 휴지 (9,000원)"}, {"t": "2026-10-14 13:40", "text": "📋 모아보기"}], open("posts.json", "w"), ensure_ascii=False)
assert H.ch_last({}) == TK("2026-10-14 13:20") and H.ch_last({"ch_last": {"t": TK("2026-10-14 13:30")}}) == TK("2026-10-14 13:30")  # posts.json 📋 X
H.ai_pick = lambda prompt, lines: [{"i": 0, "score": 8, "comment": "롤당 330원"}]; s9g = {"tsolo_20261014_13": 1}; i_sent.clear(); i_calls.clear()
for at, n in (("13:45", 0), ("13:52", 1), ("14:07", 2), ("14:22", 2)):  # 25분 = 아직 · 32분 = 빈틈 1개 · 14시 = 매시 1개 · 그 뒤 15분(빈틈 시도 기록부터) = 아직
    time.time = lambda: TK("2026-10-14 " + at); H.toss_solo(s9g); assert len(i_sent) == n, (at, len(i_sent))
assert "tsolo_20261014_14" in s9g and s9g["tgap"]["t"] == TK("2026-10-14 13:52") and all(p["chat_id"] == H.CHANNEL and "💙 토스 특가" in p["text"] and "게시 시점 가격" in p["text"] for _, p in i_sent)
s9g["ch_last"] = {"t": TK("2026-10-14 14:07")}; i_sent.clear(); s9g.pop("tb_50")  # 실제론 tg()가 기록 · 14시 출처(생필품 빈 목록 -> 하루특가)에 후보 다시
for at, n in (("14:37", 0), ("14:52", 1)):  # 30분 = 아직(넘어야) · 45분 = 1개
    time.time = lambda: TK("2026-10-14 " + at); H.toss_solo(s9g); assert len(i_sent) == n, (at, len(i_sent))
H.ai_pick = lambda prompt, lines: [{"i": 0, "score": 6, "comment": "x"}]; i_sent.clear(); i_calls.clear(); s9g["ch_last"] = {"t": TK("2026-10-14 14:00")}; s9g.pop("tgap")
time.time = lambda: TK("2026-10-14 14:52"); H.toss_solo(s9g); assert not i_sent and i_calls and s9g["tgap"]["t"] == TK("2026-10-14 14:52")  # 7점↑ 없음 -> 기록
i_calls.clear(); time.time = lambda: TK("2026-10-14 15:07"); s9g["tsolo_20261014_15"] = 1; H.toss_solo(s9g); assert not i_calls  # 15분 뒤 = 다시 안 찾음
time.time = lambda: TK("2026-10-14 15:23"); H.toss_solo(s9g); assert i_calls  # 31분 뒤 = 다시 찾음
json.dump([{"at": "2026-10-14 16:00", "name": "x", "api": True}], open("ev9i.json", "w")); i_calls.clear(); s9g.pop("tgap")
time.time = lambda: TK("2026-10-14 15:52"); H.toss_solo(s9g); assert not i_calls and "tgap" not in s9g  # 빈틈이어도 진우 예약 8분 전 = 쉼
H.TOSS_GAP_MIN = 0; i_calls.clear(); H.toss_solo({"tsolo_20261014_15": 1, "ch_last": {"t": 0}}); assert not i_calls; H.TOSS_GAP_MIN = tgm0  # 0 = 끔
H.ai_pick = lambda prompt, lines: [{"i": 0, "score": 8, "comment": "c"}]; json.dump([{"at": "2026-10-14 21:30", "deal": True}, {"at": "2026-10-14T21:10"}, {"at": "2026-10-14 24:00"}], open("ev9i.json", "w"))
s9l = {"ev_2026-10-14 21:30": TK("2026-10-14 21:43")}; i_sent.clear(); time.time = lambda: TK("2026-10-14 21:43"); H.toss_solo(s9l); assert not i_sent  # 21:30 예약이 21:43에 나감 -> 실제 게시 뒤 10분도 쉼
time.time = lambda: TK("2026-10-14 21:54"); H.toss_solo(s9l); assert len(i_sent) == 1  # 11분 뒤 = 올림 · 모양 틀린 예약 시각('T'·24시)은 건너뜀(멈추지 않음)
assert 'seen["ev_" + e["at"]] = now' in inspect.getsource(H.toss_picks)  # 토스 이름 예약(api)도 실제 게시 시각을 남김 -> 같은 규칙으로 쉼
i_sent.clear(); i_calls.clear(); time.time = lambda: TK("2026-10-14 23:40"); H.toss_solo({"tsolo_20261014_23": 1, "ch_last": {"t": TK("2026-10-14 23:00")}})
assert len(i_sent) == 1 and "많이 팔린 순위" in i_sent[0][1]["text"] and not any("today-deals" in u for u in i_calls)  # 23:30 넘으면 하루특가('밤 12시까지') 출처 X
tg9j, tg9s = tg_real, []; H.http = lambda url, body=None, headers=None, method=None: tg9s.append(body) or json.dumps({"ok": True, "result": {"message_id": 5}})
H.RUN["ch_last"] = 0; time.time = lambda: TK("2026-10-14 16:10")
tg9j("sendMessage", chat_id=H.CHANNEL, text="<i>n</i>\n\n📋 <b>오늘의 딜 모아보기</b>"); tg9j("sendMessage", chat_id=H.CHANNEL, text="🔔 다시 열렸어요", reply_parameters={"message_id": 3}); tg9j("sendMessage", chat_id=H.ADMIN, text="x")
assert len(tg9s) == 3 and H.RUN["ch_last"] == 0  # 모아보기·재오픈 답장·관리자 방 = 딜 글 아님
tg9j("sendMessage", chat_id=H.CHANNEL, text="🔥 <b>[토스] x</b>"); assert H.RUN["ch_last"] == TK("2026-10-14 16:10")
tg9j("copyMessage", chat_id=H.CHANNEL, from_chat_id=1, message_id=2); assert H.RUN["ch_last"] == TK("2026-10-14 16:10")  # 승인 복사도 딜 글
assert 'if RUN["ch_last"]:\n        seen["ch_last"] = {"t": RUN["ch_last"]}' in inspect.getsource(H.main) and "ch_last=0" in inspect.getsource(H.main); H.RUN["ch_last"] = 0
H.http, H.tg, H.ai_pick, H.EVENTS, time.time, H.HAS_TOSS, H.TOSS_SOLO_HOURS = sv9i; del H.E["THREADS_TOKEN"]; H.TOSS_NO_CMP = nc9i
# 9-3) 인스타 릴스 자동(10/11 진우 '인스타 업그레이드 3번'): REEL_PUBLIC이면 모아보기가 영상을 docs/reels/날짜.mp4(공개)에 + 캡션 저장, 봇 채팅엔 '자동 게시돼요' 확인용
#      -> 22시(REEL_HOUR) 넘고 사이트에 뜨면(HEAD) REELS 컨테이너(video_url·캡션·피드·표지 1.5초) 1번 -> ig_publish가 처리 끝나면 발행('오늘 릴스')
#      처리 중이면 기다림, 실패(ERROR)면 예외(알림), 만들기 실패는 3번까지 다시, 꺼져 있으면(기본) 예전처럼 봇 채팅 영상만(공개 X), 토큰 없으면 아무것도 안 함
H.E.update(IG_TOKEN="pt", IG_USER_ID="178"); ic, st, ph2, rp0 = [], ["IN_PROGRESS"], H.http, H.REEL_PUBLIC
def ig_http(url, body=None, headers=None, method=None):
    ic.append((url, body, headers, method))
    if method == "HEAD":
        if st[-1] == "404": raise OSError("404")
        return ""
    if url.endswith("/178/media"):
        if st[-1] == "500": raise RuntimeError("500")
        return '{"id": "R1"}'
    if "status_code" in url:
        return json.dumps({"status_code": st[0]})
    if url.endswith("/178/media_publish"):
        return '{"id": "M1"}'
    raise AssertionError(url)
H.http, vids, tt2 = ig_http, [], time.time
H.tg_video, H.draft, time.time = lambda path, cap: vids.append((path, cap)), lambda text, **k: {"message_id": 9}, lambda: 1791291600  # 10/6 22:00 KST
json.dump([{"url": "https://cdn.pixabay.com/s.mp3", "name": "테스트곡 — 작가"}], open("music.json", "w")); bg = H.bgm; H.bgm = lambda kst: "docs/bgm_t.m4a"
P3 = [{"t": "2026-10-06 10:00", "text": "🔥 [G마켓] 우유 (1,000원/무료)\n\n싸요", "url": "https://a", "s": 7, "e": "🥛", "hook": "우유 개당 100원", "pts": ["싸요"]}]
seen = {}; H.REEL_PUBLIC = False; sent.clear(); H.digest(seen, P3)  # 기본(꺼짐): 공개 X, 봇 채팅 영상만(예전 그대로)
assert len(vids) == 1 and not vids[0][0].startswith("docs/") and not os.path.exists("docs/reels") and "reel_2026-10-06" not in seen and not ic
assert vids[0][1].split("\n\n")[1].startswith("우유 개당 100원") and vids[0][1].split("\n\n")[0] == H.ig_notes([]) and "🎵 테스트곡 — 작가 (Pixabay)" in vids[0][1]  # 문구 맨 앞·곡명
H.REEL_PUBLIC, seen, vids[:] = True, {}, []; H.digest(seen, P3)
assert vids[0][0] == "docs/reels/2026-10-06.mp4" and os.path.getsize(vids[0][0]) > 10000 and vids[0][1].startswith("🎬 22시에 인스타 자동 게시돼요(직접 올리지 마세요)")
assert seen["reel_2026-10-06"]["cap"] == vids[0][1].split("\n\n", 1)[1] and not ic  # 모아보기는 HTTP 없음(올리기는 ig_reel)
time.time = lambda: 1791291600 - 60; H.ig_reel(seen); assert not ic  # 21:59 -> 아직
st[-1] = "404"; time.time = lambda: 1791291600; H.ig_reel(seen); assert [c[3] for c in ic] == ["HEAD"] and "igr_2026-10-06" not in seen  # 배포 전 -> 다음 실행에
st[-1] = "500"; ic[:] = []
for k in range(1, 4):
    try:
        H.ig_reel(seen); raise AssertionError("만들기 실패는 예외")
    except RuntimeError as e:
        assert seen["igr_2026-10-06"]["fail"] == k and ("봇 채팅에 온 영상을 직접" in str(e)) == (k == 3)
ic[:] = []; H.ig_reel(seen); assert not ic  # 3번 실패 -> 끝
st[-1], seen["igr_2026-10-06"] = "IN_PROGRESS", {"t": 1, "fail": 1}; ic[:] = []; H.ig_reel(seen)
(u, b, h, m), = [c for c in ic if c[3] == "POST"]
assert u == H.IG + "/178/media" and b == {"media_type": "REELS", "video_url": "https://hotdealpick.kr/reels/2026-10-06.mp4", "caption": seen["reel_2026-10-06"]["cap"], "share_to_feed": True, "thumb_offset": 1500}
assert seen["igc_R1"] == {"t": 1791291600, "kind": "reel"} and seen["igr_2026-10-06"] == {"t": 1791291600}
ic[:] = []; H.ig_reel(seen); assert not ic  # 하루 1번
sent.clear(); H.ig_publish(seen); assert "igc_R1" in seen and not sent and not any("media_publish" in c[0] for c in ic)  # 처리 중 -> 다음 실행에
st[0] = "FINISHED"; H.ig_publish(seen)
assert ic[-1][0].endswith("/178/media_publish") and ic[-1][1] == {"creation_id": "R1"} and "igc_R1" not in seen and sent[-1][1]["text"] == "📸 인스타 자동 게시 완료 — 오늘 릴스 (instagram.com/hotdealpick.kr)"
st[0], seen = "ERROR", {"igc_C2": {"t": 1, "kind": "reel"}}; sent.clear()
H.ig_publish(seen); assert not [k for k in seen if k.startswith("igc_")] and "릴스 처리 ERROR" in seen["igfail"]["f"][0] and not sent  # 처리 실패 = 진짜 실패(다시 안 봄·예외 X, 1번째는 알림 X — 10/23)
seen = {"reel_2026-10-06": {"t": 1, "cap": "x"}, "ig_hold": 1791291600 + 3600}; ic[:] = []; st[:] = ["FINISHED"]; H.ig_reel(seen); assert not ic  # 스팸 의심 쉼
open("docs/reels/2026-10-03.mp4", "wb").write(b"0"); H.prune_slides(1791291600); assert sorted(os.listdir("docs/reels")) == ["2026-10-06.mp4"]  # 2일 지난 영상 정리
H.bgm = bg; os.remove("music.json"); shutil.rmtree("docs/reels")
del H.E["IG_TOKEN"]; ic[:] = []; H.ig_publish({"igc_C3": 1}); H.ig_reel({"reel_2026-10-06": {"t": 1, "cap": "x"}}); assert not ic  # 토큰 없으면 호출 없음
time.time, H.http, H.REEL_PUBLIC = tt2, ph2, rp0
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
seen7 = {f"ev_{D7} 21:50": 1, f"ev_{D7} 22:45": 1, "threply": {"t": TK(f"{D7} 21:00"), "ok": 0}}  # 댓글 권한 없음 -> 댓글 없이(아래 9-7b에서 댓글)
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
assert "쌈" not in rows7[1] and "쌈" not in rows7[2] and rows7[3].startswith("23:00 🛒 ") and rows7[3].endswith(" · 🤔 특가로는 약함") and rows7[4].endswith("휴지 30롤</a> 9,900원")  # '같은 상품' 비교만 · 약한 딜 🛒 · 배송 꼬리 뺌
assert t7.endswith("🔔 매일 밤 10시 미리보기 · 알림 켜두면 안 놓쳐요") and seen7[f"preview_{D7.replace('-', '')}"]["mid"] == 777 and seen7["bundles"]["ts"][-1] == TK(f"{D7} 22:07")
q7 = urllib.parse.parse_qs(urllib.parse.urlsplit([u for u in th7 if "/9/threads?" in u][0]).query)
tt = q7["text"][0]
assert tt.startswith(H.TOSS_NOTE + "\n" + H.DISCLOSURE + "\n\n🌙 오늘 밤 특가 미리보기 (7개)\n\n22:20 🔥 메르헨트") and len(tt) <= 480 and "toss.shopping" not in tt  # 상품 링크 X
assert [l[:5] for l in tt.split("\n\n")[2].split("\n")] == ["22:20", "22:30", "22:40", "23:10", "23:20"] and tt.endswith("\n\n나머지 2개도 시간 되면 여기 하나씩 올라와요" + H.PREVIEW_LINKS)  # 약한 딜 빼고 앞 5개
assert q7["link_attachment"] == [f"{H.SITE}?ref=th"] and "외 " not in tt and "전체" not in tt and "t.me/s" not in tt and not [u for u in th7 if "reply_to_id" in u]  # 10/13 진우: 텔레그램 카드·'외 N개'·전체 링크 X, 댓글 권한 없으면 댓글 X
at7("22:21"); assert not sent7 and not th7  # 하루 1번
json.dump([{"at": f"{D7} 22:{10 + k}", "text": f"🔥 <b>[토스] 아주 긴 상품 이름 {k}번 대용량 기획 세트 묶음 (19,900원)</b>\n\n💡 쿠팡 같은 상품(29,900원)보다 10,000원 쌈", "url": f"https://toss.shopping/_m/L{k}", "deal": True, "button": "b"} for k in range(12)], open("events.json", "w"), ensure_ascii=False)
H.PREVIEW_TH = 20; at7("22:05", sv={"threply": {"t": 1, "ok": 0}}); tl = urllib.parse.parse_qs(urllib.parse.urlsplit([u for u in th7 if "/9/threads?" in u][0]).query)["text"][0]
assert len(tl) <= 480 and tl.endswith("개도 시간 되면 여기 하나씩 올라와요" + H.PREVIEW_LINKS) and tl.startswith(H.TOSS_NOTE) and len(re.findall(r"\n22:\d\d ", tl)) == 1; H.PREVIEW_TH = 5  # 같은 브랜드('아주')는 본문에 1개만
# 9-7b) 10/13 00:50 진우 '타래 + 브랜드 섞기': Threads 미리보기 본문 = 🔥 먼저·브랜드 1개씩 5개(시각 순) + '나머지 N개는 댓글에 👇' + '🔔 시간 되면…' + 📲 한 줄,
#       나머지 = 댓글(시각 순, 댓글마다 대가성 문구 맨 앞·480자 이하, 본문 -> 댓글1 -> 댓글2 reply_to_id로 이어서), 토스 = 다른 몰 비교 X, 댓글 권한은 발행 없이 1번 확인
B7 = ["메르헨트", "메르헨트", "레이데이", "파스쿠찌", "한경희", "스파클", "맥콜", "수뜰리에", "베라", "모나리자", "킬로", "올리", "땡큐파머스", "예진원", "웨이크비", "과일꾼", "포천이동", "배스킨라빈스", "맘스케이크", "푸드앳홈"]
json.dump([{"at": f"{D7} 22:{10 + 2 * k}", "text": f"🔥 <b>[토스] {b} 상품 {k}번 대용량 세트 (9,900원)</b>\n\n💡 쿠팡 같은 상품(19,900원)보다 10,000원 쌈", "url": f"https://toss.shopping/_m/B{k}", "deal": True, "button": "b"} for k, b in enumerate(B7)]
          + [{"at": f"{D7} 23:59", "text": "🔥 <b>[쿠팡] 휴지 30롤 (9,900원/무료)</b>\n\n💡 쿠팡 같은 상품(12,900원)보다 3,000원 쌈", "url": "https://link.coupang.com/a/z", "deal": True, "button": "b"}], open("events.json", "w"), ensure_ascii=False)
rp7, nc7 = [], [0]
def http7b(url, body=None, headers=None, method=None):
    th7.append(url)
    if "/me?" in url: return json.dumps({"id": "9"})
    if "fields=id&limit=1" in url: return json.dumps({"data": [{"id": "p0"}]})
    if "/threads?" in url:
        nc7[0] += 1
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query); rp7.append((q.get("reply_to_id", [None])[0], q["text"][0], q.get("link_attachment", [None])[0], nc7[0]))
        return json.dumps({"id": f"c{nc7[0]}"})
    if "/threads_publish?" in url: return json.dumps({"id": "m" + url.split("creation_id=c")[1].split("&")[0]})
    raise AssertionError(url)
H.http, H.TOSS_NO_CMP = http7b, True; at7("22:05", sv={"threply": {"t": 1, "ok": 1}})
(_, b7, l7, _), *r7 = rp7
assert l7 == f"{H.SITE}?ref=th" and len(b7) <= 480 and b7.startswith(H.TOSS_NOTE + "\n" + H.DISCLOSURE + "\n\n🌙 오늘 밤 특가 미리보기 (21개)\n\n22:10 🔥 메르헨트 상품 0번")
assert b7.endswith("\n\n나머지 16개는 댓글에 👇\n🔔 시간 되면 이 계정에 하나씩 올라와요" + H.PREVIEW_LINKS)  # 10/13 01:25 진우: 끝 블록 = 댓글 안내 + 사이트·텔레그램 링크(장점 설명)
assert H.PREVIEW_LINKS == f"\n\n🛍 지금 살 수 있는 딜 한눈에(앱 설치 없이) 👉 {H.SITE}?ref=th\n📲 텔레그램 쓰는 분은 올라오는 순간 알림 👉 t.me/hotdeal_pick" and b7.count("http") == 1 and "실시간 알림 t.me" not in b7
assert b7.count("메르헨트") == 1 and "쌈" not in b7 and "외 " not in b7  # 토스 = 쿠팡 비교 X
assert len(r7) >= 2 and r7[0][0] == "m1" and all(r7[k][0] == f"m{r7[k - 1][3]}" for k in range(1, len(r7))) and all(x[2] is None for x in r7)  # 본문 -> 댓글1 -> 댓글2(이어서), 링크 첨부 X
assert all(len(x[1]) <= 480 and x[1].startswith(H.TOSS_NOTE) for x in r7) and "쿠팡 같은 상품보다 3,000원 쌈" in r7[-1][1] and H.DISCLOSURE in r7[-1][1]  # 댓글마다 대가성 문구, 토스 아닌 몰(쿠팡)은 그대로
rl7 = [l for x in r7 for l in x[1].split("\n\n", 1)[1].split("\n")]
assert [l[:5] for l in rl7] == sorted(l[:5] for l in rl7) and len(rl7) == 16 and sum("쌈" in l for l in rl7) == 1 and "휴지" in rl7[-1]  # 나머지 16개 전부·시각 순, 비교는 쿠팡 딜만
rp7.clear(); pk7 = {}; at7("22:05", sv=pk7); pr7 = [x[3] for x in rp7 if x[0] == "p0"]
assert pk7["threply"]["ok"] == 1 and len(pr7) == 1 and not any(f"creation_id=c{pr7[0]}&" in u for u in th7) and sum(x[0] not in (None, "p0") for x in rp7) >= 2  # 권한 확인 = 내 최근 글에 컨테이너만(발행 X, 안 보임) -> 되면 댓글까지
th7.clear(); H.th_reply_ok(pk7); assert not th7  # 결과는 seen에(3일) — 다시 안 부름
def http7c(url, body=None, headers=None, method=None):
    if "reply_to_id" in url:
        e = urllib.error.HTTPError(url, 400, "Bad", None, None); e.body = '{"error": {"message": "Application does not have permission for this action", "code": 10}}'; raise e
    return http7b(url, body, headers, method)
H.http, pk7 = http7c, {}; at7("22:05", sv=pk7)
assert pk7["threply"]["ok"] == 0 and "permission" in pk7["threply"]["err"] and rp7[-1][1].endswith("나머지 16개도 시간 되면 여기 하나씩 올라와요" + H.PREVIEW_LINKS)  # 안 되면 댓글 없이 끝 문구
def http7d(url, body=None, headers=None, method=None):
    if "threads_publish" in url: raise urllib.error.HTTPError(url, 500, "x", None, None)
    return http7b(url, body, headers, method)
H.http, pk7 = http7d, {"threply": {"t": 1, "ok": 1}}
try:
    at7("22:05", sv=pk7); raise AssertionError("본문 실패는 예외(main 알림)")
except urllib.error.HTTPError:
    assert pk7[f"thretry_{D7.replace('-', '')}_preview"]["text"].endswith("나머지 16개도 시간 되면 여기 하나씩 올라와요" + H.PREVIEW_LINKS)  # 재시도는 댓글 없이 -> '댓글에 👇' X
H.http, H.TOSS_NO_CMP = http7, False
# 9-7c) 10/13 01:50 진우 '업로드 안 되면 바로 알람': ① 미리보기 댓글 실패 -> 관리자에게 바로(못 올린 댓글 본문 그대로) ② 업로드 단계 실패 -> 바로(같은 단계·오류는 3시간에 1번),
#       텔레그램 채널 글 실패도, 다시 올라가면 '✅ 다시 올라감' ③ 8~24시 Threads 2시간 글 없음 -> '⏸' 1번 · 예약 글 시각 + 20분 안 나감 -> 예약마다 1번
def http7e(url, body=None, headers=None, method=None):
    if "reply_to_id" in url and sum("reply_to_id" in u for u in th7) >= 1:  # 둘째 댓글에서 실패
        e = urllib.error.HTTPError(url, 400, "Bad", None, None); e.body = '{"error": {"message": "Service temporarily unavailable", "code": 2}}'; raise e
    return http7b(url, body, headers, method)
H.http, H.TOSS_NO_CMP, rp7[:] = http7e, True, []; at7("22:05", sv={"threply": {"t": 1, "ok": 1}})
a7 = [p["text"] for m, p in sent7 if p.get("chat_id") == H.ADMIN]; np7 = len([x for x in rp7 if x[0] not in (None, "p0")]) - 1  # 올라간 댓글 수(마지막 1개는 실패)
assert len(a7) == 1 and a7[0].startswith("⚠️ 22시 미리보기 댓글 실패 — 본문은 나갔고 댓글 ") and "개 중 " in a7[0] and "Service temporarily unavailable" in a7[0] and "Threads 앱에서 댓글로 붙여넣거나 본문 삭제" in a7[0]
pa7 = a7[0].split("본문 삭제\n\n", 1)[1]
assert pa7.startswith(H.TOSS_NOTE) and "휴지 30롤" in pa7 and rp7[-1][1] not in pa7 and "댓글 2개 중 1개 못 올림" in a7[0]  # 못 올린 댓글(둘째)만 본문 그대로(붙여넣기용)
H.http, H.TOSS_NO_CMP = http7, False
al7, tt7c, tg7c = [], time.time, H.tg
H.tg = lambda m, **p: al7.append(p.get("text")) or {"message_id": 1}
e7 = urllib.error.HTTPError("https://graph.threads.com/v1.0/9/threads_publish", 400, "x", None, None); e7.body = '{"error": {"message": "Fatal", "error_subcode": 4279009}}'
s7c = {}; time.time = lambda: TK(f"{D7} 14:00"); H.RUN.update(ok=set(), fail={}, failch=set(), th_last=0, th_why="", tg_err="")
H.step_alert(s7c, H.threads_deals, e7); H.step_alert(s7c, H.threads_deals, e7)
assert len(al7) == 1 and al7[0].startswith("⚠️ Threads 개별 글 (Threads) 게시 실패: 400 Fatal") and "alert_threads_deals_HTTPError_400_4279009" in s7c  # 바로, 같은 단계·오류는 3시간에 1번
H.step_alert(s7c, lambda s: H.toss_deals(s, "cat"), RuntimeError("toss 500")); H.step_alert(s7c, H.report, RuntimeError("x"))
assert len(al7) == 2 and al7[1].startswith("⚠️ 토스 회차 글 게시 실패: RuntimeError('toss 500')") and "다음 실행" in al7[1]  # 채널 글 단계도, 업로드 아닌 단계(리포트)는 X
time.time = lambda: TK(f"{D7} 17:01"); H.step_alert(s7c, H.threads_deals, e7); assert len(al7) == 3  # 3시간 지나면 다시
def tg7t(m, **p): raise TimeoutError("The read operation timed out")
H.tg = tg7t; H.step_alert(s7c, H.toss_deals, TimeoutError("x")); assert "alert_toss_deals_TimeoutError" not in s7c  # 알림 전송이 시간 초과여도 실행은 안 죽음(10/17 10:11 run 1207), 다음 실행에 다시 알림
H.tg = lambda m, **p: al7.append(p.get("text")) or {"message_id": 1}
H.RUN.update(ok={"th"}, failch=set()); H.watch(s7c); assert al7[-1] == "✅ 다시 올라감: Threads 개별 글 (Threads)" and not s7c["alert_open"]["v"]  # 다시 올라가면 1줄
H.watch(s7c); assert al7[-1].startswith("✅") and len(al7) == 4  # 1번만
def http7f(url, body=None, headers=None, method=None):
    e = urllib.error.HTTPError(url, 400, "x", None, None); e.body = '{"ok": false, "description": "Bad Request: message is too long"}'; raise e
H.http, H.RUN["ok"] = http7f, set()
assert tg_real("sendMessage", chat_id=H.CHANNEL, text="x") is None and tg_real("editMessageText", chat_id=H.CHANNEL, message_id=1, text="x") is None and list(H.RUN["fail"]) == ["sendMessage 400"]  # 채널 '올리기'만(수정 X)
H.watch(s7c); assert al7[-1].startswith("⚠️ 텔레그램 채널 게시 실패: sendMessage 400 Bad Request: message is too long")
H.RUN.update(ok={"tg"}, fail={}, failch=set()); H.watch(s7c); assert al7[-1] == "✅ 다시 올라감: 텔레그램 채널"
# Threads 2시간 글 없음(8~24시, 밤은 안 셈) · 예약 글 20분 늦음
H.E["THREADS_TOKEN"], H.RUN["ok"] = "tk", set(); json.dump([{"t": f"{D7} 13:30", "text": "🔥 [쿠팡] 휴지 (9,900원)", "url": "https://link.coupang.com/a/q7"}, {"t": f"{D7} 13:31", "text": "🔥 [쿠팡] 검색 링크 (9,900원)", "url": "https://www.coupang.com/np/search?q=a"}], open("posts.json", "w"), ensure_ascii=False)  # 수수료 링크 아닌 딜은 대기로 안 셈(10/19 밤)
json.dump([{"at": f"{D7} 13:30", "text": "🔥 <b>[토스] 늦은 예약 (1,000원)</b>", "url": "https://toss.shopping/_m/q", "deal": True, "button": "b"},
           {"at": f"{D7} 13:35", "text": "🔥 <b>[토스] 나간 예약 (1,000원)</b>", "url": "https://toss.shopping/_m/r", "deal": True, "button": "b"},
           {"at": f"{D7} 13:36", "name": "이름 예약 끝남", "api": True}, {"at": f"{D7} 13:37", "name": "이름 예약 못 찾음", "api": True},
           {"at": f"{D7} 13:50", "text": "🔥 아직 20분 안 됨", "url": "https://x", "button": "b"}, {"at": f"{D7} 07:00", "text": "🔥 6시간 넘은 예약", "url": "https://x", "button": "b"}], open("events.json", "w"), ensure_ascii=False)
s7d = {"th_last": {"t": TK(f"{D7} 02:00")}, f"ev_{D7} 13:35": 1, f"pk_{D7} 13:36": {"t": 1, "st": "done"}, f"pk_{D7} 13:37": {"t": 1, "st": None}}
al7.clear(); H.RUN["th_why"] = "threads 후보 3 · ①② 0 · 간격 열림"; time.time = lambda: TK(f"{D7} 09:59"); H.watch(s7d)
assert not [a for a in al7 if a.startswith("⏸ Threads")] and len(al7) == 1 and al7[0].startswith("⏸ 텔레그램 예약 글 안 나감 — 10-14 07:00 🔥 6시간 넘은 예약 (예약 + 20분 지남)"); al7.clear()  # 밤 글 없음은 안 셈(8시부터 2시간) · 07:00 예약은 6시간 안이라 알림
time.time = lambda: TK(f"{D7} 13:58"); H.watch(s7d)
assert al7[0].startswith("⏸ Threads 5시간째 글 없음 — 마지막 글 02:00, 대기 중 1개, 이유: threads 후보 3 · ①② 0 · 간격 열림") and "quiet_th" in s7d
ev7c = sorted(a for a in al7 if a.startswith("⏸ 텔레그램 예약 글 안 나감"))
assert len(ev7c) == 2 and "13:30 🔥 [토스] 늦은 예약 (1,000원)" in ev7c[0] and "13:37 이름 예약 못 찾음" in ev7c[1] and "토스 이름 예약" in ev7c[1]  # 나간 것·끝난 이름 예약·20분 안 됨·6시간 넘은 것 X
al7.clear(); H.watch(s7d); assert not al7  # 다시 올라가기 전까지 반복 X
H.RUN["th_last"] = TK(f"{D7} 14:05"); time.time = lambda: TK(f"{D7} 14:05"); H.watch(s7d); assert "quiet_th" not in s7d and s7d["th_last"]["t"] == TK(f"{D7} 14:05")  # 올라가면 감시 다시
H.tg, H.http, time.time = tg7c, http7, tt7c; del H.E["THREADS_TOKEN"]; H.RUN.update(ok=set(), fail={}, failch=set(), th_last=0, th_why="", tg_err=""); json.dump(EV7, open("events.json", "w"), ensure_ascii=False)
H.E["THREADS_TOKEN"] = "tk"
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
json.dump([{"t": f"{D7} 10:{k % 60:02d}", "text": f"🔥 딜{k} (1,000원)", "url": f"https://oy.run/{k}" if k % 2 else f"https://link.coupang.com/a/{k}", "s": 7} for k in range(130)], open("posts.json", "w"))
sent7.clear(); dg7 = {}; H.digest(dg7, json.load(open("posts.json"))); d7 = [p["text"] for m, p in sent7 if m == "sendMessage" and p["chat_id"] == H.CHANNEL][0]
assert len(re.findall(r"<(?:a|b|i)[ >]", d7)) + html.unescape(re.sub(r"<[^>]+>", "", d7)).count("http") <= 90 and "개는 사이트에서" in d7 and any(k.startswith("digest_") for k in dg7)
json.dump([{"t": f"{D7} 10:{k % 60:02d}", "text": f"🔥 [G마켓] 딜{k} (1,000원)", "url": "https://click.linkprice.com/click.php?m=gmarket&a=A&l=" + "%EC%9A%B0" * 40 + str(k), "s": 7} for k in range(60)], open("posts.json", "w"))
sent7.clear(); dg7 = {}; H.digest(dg7, json.load(open("posts.json"))); d7 = [p["text"] for m, p in sent7 if m == "sendMessage" and p["chat_id"] == H.CHANNEL][0]
hr7 = re.findall(r'href="([^"]*)"', d7); assert sum(map(len, hr7)) <= 5000 and len(hr7) == 60 and all(h.startswith(H.SITE + "p/") for h in hr7)  # 긴 주소(400자) 60개 -> 사이트 딜 페이지로(다 들어감, 10/11 21:39 ENTITIES_TOO_LONG)  # 딜 130개: 텔레그램 서식 100개 한도 안으로 줄임(10/11 21시 ENTITIES_TOO_LONG)
sys.modules.pop("cards"); cm7 and sys.modules.__setitem__("cards", cm7)
assert "for step in (cp_links, shelf_posts, toss_shelf, events, preview, playlist," in inspect.getsource(H.main) and "preview" in H.ALERT_STEPS  # 토스 22시 회차보다 먼저 · 실패 알림(바로)
time.time = tt7; del H.E["THREADS_TOKEN"]
if ev7 is not None: open("events.json", "w").write(ev7)
else: os.remove("events.json")
# 9-8) 첫 줄 '[광고] + 훅 + 상품 + 가격'(10/11 진우 결정 — 조회는 되는데 구매가 적음): 개별 딜 글(채널·Threads) 1줄 [광고]…, 2줄 제휴 고지문 그대로(공정위: 첫 부분),
#      훅 = 같은 상품 쿠팡 차이 > 단위가격 > 30일 최저가·순위 > 할인율(토스 API 상품은 쿠팡 비교 없음), 틀 3가지(제목으로 — 같은 글은 고쳐도 같은 틀), 제휴 아니면 [광고] 없음, AD_FIRST=False면 예전
assert H.AD_FIRST == "" and H.ad_on() is False
assert '\nAD_FIRST = ""  # 10/12 00:40 진우 결정' in inspect.getsource(H)  # 기본값 = 꺼짐(10/12 00:40 진우 '첫 줄 변경 취소' — 고지문 첫 줄 예전 형식, 2주 동결)
H.AD_FIRST = "2000-01-01"
assert H.ad_hook("💡 쿠팡 같은 상품(14,000원)보다 6,060원 쌈") == ("💸", "쿠팡보다 6,060원 싼", "쿠팡보다 6,060원 쌈")
assert H.ad_hook("💡 쿠팡 비슷한 상품(14,000원)보다 6,060원 쌈") is None and H.ad_hook("💡 단위가격: 10ml당 593원 — 쿠팡 톤업(…)보다 ml당 33% 쌈")[0] == "📏"  # 같은 상품만 💸
assert H.ad_hook("x", "개당 약 496원 (1L당 248원)") == ("📏", "개당 약 496원꼴", "개당 약 496원") and H.ad_hook("토스 하루특가 · ⭐ 4.7 · 30일 내 최저가")[0] == "📉"
assert H.ad_hook("토스 최대할인가 · 클렌징 폼 2위 · 내일 출발") == ("🏆", "클렌징 폼 2위", "클렌징 폼 2위") and H.ad_hook("💰 18,900원 (45%↓) · ⭐ 4.8")[1] == "45% 할인" and H.ad_hook("그냥 글") is None
forms8 = {H.ad_line(f"🔥 [쿠팡] 배스킨라빈스 {n}병 (7,900원/무료)\n\n💡 쿠팡 같은 상품(13,960원)보다 6,060원 쌈") for n in range(4, 30)}
assert {re.sub(r"\d+병", "N병", x) for x in forms8} == {"[광고] 💸 쿠팡보다 6,060원 싼 배스킨라빈스 N병 7,900원", "[광고] 배스킨라빈스 N병 7,900원 — 쿠팡보다 6,060원 쌈", "[광고] 💸 쿠팡보다 6,060원 쌈 · 배스킨라빈스 N병 7,900원"}  # 틀 3가지(제목에 따라)
assert H.ad_line("🔥 [쿠팡] 배스킨라빈스 12병 (7,900원/무료)\n\n💡 쿠팡 같은 상품(13,960원)보다 6,060원 쌈") == "[광고] 💸 쿠팡보다 6,060원 싼 배스킨라빈스 12병 7,900원"  # 진우 예시 그대로
assert H.ad_line("🔥 [쿠팡] 휴지 30롤 (9,900원/무료)\n\n싸요") == "[광고] 🔥 휴지 30롤 9,900원"  # 훅 없으면 🔥
assert H.ad_line("🛒 [토스] 한경희 카본 전기히터 HAAN-Q3500 그레이 (58,900원)\n\n🤔 솔직히 특가로는 약한 제품 — 쿠팡 같은 상품(HAAN-Q3500 그레이)이 59,900원이라 1,000원 차이\n토스 최대할인가 · 2위") == "[광고] 🛒 한경희 카본 전기히터 HAAN-Q3500… 58,900원"  # 🛒 약한 딜 = 🔥·훅 없이(10/12 0시 Q3500 '[광고] 🔥' 고침)
assert H.ad_line("🛒 [토스] 약한딜 (9,000원)\n\n🤔 솔직히 특가로는 약한 제품 — 쿠팡 같은 상품(10,000원)보다 1,000원 쌈") == "[광고] 🛒 약한딜 9,000원"  # 같은 상품 차이가 있어도 💸 훅 X
d8 = {"title": "[쿠팡] 우유 48팩 (23,740원/무료)", "url": "https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&no=8", "board": "뽐뿌", "hot": None}
af8, sl8, lp8 = H.affiliate, H.store_link, H.lp_search
H.store_link, H.lp_search, H.affiliate = (lambda u: u), (lambda t, q=None: (None, None)), (lambda u: ("https://naver.me/u8", True))
t8, l8, _ = H.deal_post(dict(d8, title="[네이버] 우유 48팩 (23,740원/무료)"), "<싸다>", extra={"unit": "팩당 495원"})
assert t8.startswith("[광고] ") and "\n<i>" + H.NAVER_NOTE + "</i>\n\n🔥 <b>[네이버] 우유 48팩" in t8 and t8.split("\n")[0] in ("[광고] 📏 팩당 495원꼴 우유 48팩 23,740원", "[광고] 우유 48팩 23,740원 — 팩당 495원", "[광고] 📏 팩당 495원 · 우유 48팩 23,740원")
assert S.title_of(H.plain_of(t8)) == "[네이버] 우유 48팩 (23,740원/무료)" and not S.title_of(H.plain_of(t8)).startswith("[광고]")  # 사이트 제목·코멘트는 그대로([광고] 줄은 고지문처럼 건너뜀)
H.affiliate = lambda u: ("https://www.coupang.com/vp/1", False); t8, _, _ = H.deal_post(d8, "싸다"); assert not t8.startswith("[광고]") and t8.startswith("📦 쿠팡 🔥"), t8  # 제휴 링크 아니면 [광고] X(쿠팡 = 몰별 틀, 로켓 근거 없으면 '📦 쿠팡' — 10/23)
H.affiliate, H.store_link, H.lp_search = af8, sl8, lp8
wt, we = H.with_note("🔥 [쿠팡] 휴지 30롤 (9,900원/무료)\n\n💡 쿠팡 같은 상품(15,000원)보다 5,100원 쌈", [{"type": "bold", "offset": 2, "length": 3}], "https://link.coupang.com/a/w8")
a8 = wt.split("\n")[0]; la8 = len(a8.encode("utf-16-le")) // 2
assert a8.startswith("[광고] ") and "5,100원" in a8 and wt.split("\n")[1] == H.DISCLOSURE and we[0] == {"type": "italic", "offset": la8 + 1, "length": len(H.DISCLOSURE.encode("utf-16-le")) // 2}
assert we[1]["offset"] == 2 + la8 + 1 + len(H.DISCLOSURE.encode("utf-16-le")) // 2 + 2 and H.with_note(wt, we, "https://link.coupang.com/a/w8") == (wt, we)  # 굵게 위치 그대로 밀림, 같은 링크로 또 = 그대로
nt, ne = H.with_note(wt, we, "https://naver.me/w8"); assert nt.count("[광고]") == 1 and nt.split("\n")[1] == H.NAVER_NOTE and H.DISCLOSURE not in nt and ne[-1]["type"] == "bold"  # 다른 프로그램 링크 = 머리 다시
ev8 = {"at": "2026-10-14 22:20", "text": "🔥 <b>[토스] 크림 50g 2개 (17,900원)</b>\n\n💡 쿠팡 같은 상품(23,900원)보다 6,000원 쌈", "url": "https://toss.shopping/_m/e8", "button": "b", "deal": True, "name": "크림"}
assert H.ev_head(ev8).startswith("[광고] ") and H.ev_head(ev8).endswith(f"\n<i>{H.TOSS_NOTE}</i>\n\n") and "6,000원" in H.ev_head(ev8) and H.sold_ev(ev8, "2026-10-14")["pre"] == H.ev_head(ev8)
assert H.ev_head(dict(ev8, deal=False)) == f"<i>{H.TOSS_NOTE}</i>\n\n" and H.ev_head(dict(ev8, url="https://x.com")) == ""  # 행사 알림 = 고지문만, 제휴 아님 = 없음
assert H.ad_head(H.TOSS_NOTE, H.plain_of("🔥 <b>[토스] 샴푸 (9,900원)</b>\n\n💰 <b>9,900원</b> (45%↓)")).split("\n")[0] in ("[광고] 🔻 45% 할인 샴푸 9,900원", "[광고] 샴푸 9,900원 — 45% 할인", "[광고] 🔻 45% 할인 · 샴푸 9,900원")  # 토스 API = 할인율(쿠팡 X)
assert "ad_head(TOSS_NOTE, plain_of(body))" in inspect.getsource(H.toss_picks) and 'text = toss_th(info, r["n"], toss_price(x), lines, r["link"])' in inspect.getsource(H.toss_picks) and "th_note(TOSS_NOTE)" in inspect.getsource(H.toss_th) and "th_note(TOSS_NOTE)" in inspect.getsource(H.reopen_text) and "reopen_text(seen, e, price, am, hot)" in inspect.getsource(H.toss_reopen) and "ev_head(ev)" in inspect.getsource(H.events)  # 채널 = [광고] 첫 줄, Threads = [광고] + 고지문 + 예전 본문
pj8 = open("posts.json").read(); calls[:] = []; kt8 = lambda h: time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - h * 3600))
json.dump([{"t": kt8(1), "text": f"{H.DISCLOSURE}\n\n🔥 [쿠팡] 휴지 30롤 (9,900원/무료)\n\n💡 쿠팡 같은 상품(15,000원)보다 5,100원 쌈\n\n출처: 뽐뿌", "url": "https://link.coupang.com/a/x", "s": 8, "own": 1},
           {"t": kt8(0.5), "text": "🔥 [카카오] 고구마 3kg\n\n💡 쿠팡 같은 상품(9,000원)보다 1,000원 쌈", "url": "https://www.ppomppu.co.kr/1", "s": 8, "own": 1}], open("posts.json", "w"), ensure_ascii=False)
live_pages = {0, 1}; H.http = td_http; H.E["THREADS_TOKEN"] = "tk"; H.threads_deals({})
m8 = [parse_qs(urlsplit(u).query)["text"][0] for m, u in calls if "/777/threads?" in u]
assert m8[0].startswith("[광고] " + H.DISCLOSURE + "\n\n💸 쿠팡보다 5,100원 싸요\n🔥 [쿠팡] 휴지 30롤 (9,900원/무료)\n\n")  # Threads = [광고]만 맨 앞, 본문 틀(고지문 → 💸 훅 → 🔥 제목 → …) 그대로(10/11 23:40 진우)
assert len(m8) == 1 and len(m8[0]) < 500 and json.load(open("posts.json"))[1]["th"] == 0  # 제휴 아니면(뽐뿌 원글) Threads X(10/19 밤 진우 'Threads는 수수료 딜만' — 텔레그램은 그대로)
open("posts.json", "w").write(pj8); del H.E["THREADS_TOKEN"]
assert H.th_note(H.TOSS_NOTE) == "[광고] " + H.TOSS_NOTE + "\n\n" and H.th_note("") == ""  # Threads 머리 = [광고] + 고지문(켜짐), 제휴 아니면 없음
H.AD_FIRST = ""; assert H.th_note(H.TOSS_NOTE) == H.TOSS_NOTE + "\n\n" and H.ad_head(H.TOSS_NOTE, "x") == f"<i>{H.TOSS_NOTE}</i>\n\n" and H.with_note("🔥 a", [], "https://link.coupang.com/a/1")[0] == H.DISCLOSURE + "\n\n🔥 a"  # 끄면 예전
tt8 = time.time; H.AD_FIRST = "2026-10-12"
time.time = lambda: TK("2026-10-11 23:59"); assert not H.ad_on() and H.ad_head(H.TOSS_NOTE, "x").startswith("<i>")
time.time = lambda: TK("2026-10-12 00:00"); assert H.ad_on() and H.ad_head(H.TOSS_NOTE, "🔥 [토스] a (1원)").startswith("[광고]")  # 10/12 0시(KST)부터 저절로
time.time = tt8; H.AD_FIRST = ""
# 9-10) 측정(10/11 진우 결정 — 집중 모드 2번): GoatCounter 코드가 있을 때만 모든 페이지에 스크립트 + 구매 링크(nofollow) 클릭 = 이벤트 'buy/몰 주소',
#       채널 구분 = 글 속 사이트 링크에 ?ref=th(Threads)·tg(텔레그램)·blog(블로그) — 인스타는 프로필 링크(진우가 ?ref=ig로)
gc10, S.GC_CODE = S.GC_CODE, ""; assert S.gc_tag() == "" and "goatcounter" not in S.page("t", "<p>b</p>"); S.GC_CODE = gc10  # 코드 없으면 없음
assert S.GC_CODE == "hotdealpick"  # 10/23 진우 가입(hotdealpick.goatcounter.com)
pg = S.page("t", "<p>b</p>")
assert '<script data-goatcounter="https://hotdealpick.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>' in pg and "path:'buy/'+h" in pg and "event:true" in pg and pg.index("goatcounter") < pg.index("</head>")
src10 = inspect.getsource(H)
assert 'f"{SITE}p/{i}.html?ref={ref}"' in src10 and 'def th_url(p, i, ref="th")' in src10 and "지난 딜 전체 보기: {SITE}?ref=tg" in src10 and "전체 딜·구매 링크 👉 {SITE}?ref=th" in src10 and "더 많은 핫딜 👉 {SITE}?ref=blog" in src10
# 9-11) 10/15 진우 '데이터 계획 1단계': 매일 5시 넘은 첫 실행에 어제 글별 성과 -> metrics.json(날짜·채널·글 id·몰·품목·가격대·시각·조회·반응), 수동 실행 METRICS_DAY면 그날 바로
#       텔레그램 = 채널 웹(?before= 로 그날 처음까지, posts.json 글은 그 글·링크로), Threads = 글 목록 + insights, 인스타 = 목록(좋아요·댓글) + insights(views), 권한 없으면 빈 칸 + 이유(miss)
assert mh0 == 5 and not os.path.exists(H.METRICS); H.METRICS_HOUR = mh0  # 앞 셀프체크(main 실행)에선 꺼 둠(99)
sv10, m10 = (H.http, time.time, H.POSTS), []
def tme10(mid, utc, text, views, btn="", react="", pre=""):
    return (f'<div class="tgme_widget_message_wrap js-widget_message_wrap"><div class="tgme_widget_message" data-post="hotdeal_pick/{mid}">{pre}<div class="tgme_widget_message_text js-message_text" dir="auto">{text}</div>'
            f'{react}<span class="tgme_widget_message_views">{views}</span><time datetime="{utc}" class="time">x</time></div>' + (f'<a class="tgme_widget_message_inline_button url_button" href="{btn}">b</a>' if btn else "") + "</div>")
P10 = {"https://t.me/s/hotdeal_pick": tme10(901, "2026-10-14T14:50:00+00:00", "<b>[토스] 다음날 글</b>", "3") + tme10(902, "2026-10-14T15:10:00+00:00", "x", "1"),  # 10/14 23:50 · 10/15 00:10(KST)
       "https://t.me/s/hotdeal_pick?before=901": tme10(899, "2026-10-14T01:00:00+00:00", "<b>[광고] 훅</b><br><i>이 콘텐츠는 토스</i><br><br>🔥 <b>[토스] 크리넥스 3겹 휴지 30롤 (21,900원)</b><br>💡 롤당 730원", "1.2K", "https://toss.im/_m/A",
                                                     '<div class="tgme_widget_message_reactions"><span class="tgme_reaction"><i class="emoji"><b>👍</b></i>12</span><span class="tgme_reaction tgme_reaction_paid"><i class="emoji">⭐</i>3</span>'
                                                     '<span class="tgme_reaction"><tg-emoji emoji-id="5"><span class="tg-emoji-wrap"><i class="emoji"><b>❤</b></i></span></tg-emoji>2</span></div>')
       + tme10(900, "2026-10-14T03:00:00+00:00", "🏆 리스트", "40")
       + tme10(903, "2026-10-14T05:00:00+00:00", "🔔 <b>다시 열렸어요!</b> 크리넥스 휴지 30롤 — 21,900원", "7", pre='<div class="tgme_widget_message_reply"><div class="tgme_widget_message_text js-message_reply_text">🔥 [쿠팡] 프라이팬 (55,000원)</div></div>'),
       "https://t.me/s/hotdeal_pick?before=899": tme10(897, "2026-10-13T14:00:00+00:00", "그제", "9") + tme10(898, "2026-10-13T14:59:00+00:00", "어제", "9")}
json.dump([{"t": "2026-10-14 12:00", "mid": 900, "text": "🏆 지금 살 만한 딜 TOP5 (12시)\n1️⃣ a\n2️⃣ b", "url": None},
           {"t": "2026-10-14 23:50", "mid": 901, "text": "🔥 [쿠팡] 피지오겔 페이셜 로션 150ml (21,670원)", "url": "https://link.coupang.com/a/x"}], open("posts.json", "w"), ensure_ascii=False)
TH10 = [{"id": "t1", "text": "이 콘텐츠는 토스\n🔥 [토스] 비비고 왕만두 1.05kg 2개 (12,900원)", "timestamp": "2026-10-14T03:00:00+0000"}, {"id": "t2", "text": "🔥 샴푸 (55,000원)\n\n👉 https://link.coupang.com/a/abc\n📲 실시간 알림 t.me/hotdeal_pick", "timestamp": "2026-10-14T09:00:00+0000"}]
def http10(url, body=None, headers=None, method=None):
    m10.append(url)
    if url in P10: return P10[url]
    if "/me/threads?" in url:
        assert "since=1791903600&until=1791990000" in url and "access_token=tk" in url  # 10/14 0시~24시 KST
        return json.dumps({"data": TH10 if "after=" not in url else [], "paging": {"next": url + "&after=c"}})
    if url.endswith("/t1/insights?metric=views,likes,replies,reposts,quotes&access_token=tk"):
        return json.dumps({"data": [{"name": "views", "values": [{"value": 340}]}, {"name": "likes", "values": [{"value": 5}]}, {"name": "replies", "values": [{"value": 0}]},
                                    {"name": "reposts", "values": [{"value": 1}]}, {"name": "quotes", "total_value": {"value": 0}}]})
    if url.endswith("/t2/insights?metric=views,likes,replies,reposts,quotes&access_token=tk"): return json.dumps({"data": [{"name": n, "values": [{"value": 0}]} for n in ("views", "likes", "replies", "reposts", "quotes")]})
    if "/178/media?fields=id,caption,timestamp,like_count,comments_count" in url:
        assert headers == {"Authorization": "Bearer pt"}
        return json.dumps({"data": [{"id": "g1", "caption": "📌 오늘의 딜", "timestamp": "2026-10-14T12:00:00+0000", "like_count": 4, "comments_count": 1},
                                    {"id": "g0", "caption": "x", "timestamp": "2026-10-13T12:00:00+0000", "like_count": 1, "comments_count": 0}]})
    if "/g1/insights?metric=views" in url:
        e = H.urllib.error.HTTPError(url, 403, "x", {}, None); e.body = '{"error":{"message":"(#10) Application does not have permission for this action","code":10}}'; raise e
    raise AssertionError(url)
H.http, H.E["THREADS_TOKEN"] = http10, "tk"; H.E.update(IG_TOKEN="pt", IG_USER_ID="178"); H.E.pop("METRICS_DAY", None)
s10 = {}; time.time = lambda: TK("2026-10-15 04:52"); H.metrics(s10); assert not m10 and not s10  # 5시 전 X
time.time = lambda: TK("2026-10-15 05:07"); H.metrics(s10)
d10 = json.load(open(H.METRICS)); r10 = d10["2026-10-14"]["rows"]
assert list(d10) == ["2026-10-14"] and "mt_2026-10-14" in s10 and d10["2026-10-14"]["at"] == "2026-10-15 05:07"
assert [(r["ch"], r["id"]) for r in r10] == [("tg", 899), ("tg", 900), ("tg", 903), ("tg", 901), ("th", "t1"), ("th", "t2"), ("ig", "g1")]  # 그날 것만(00:10·전날 X), 쪽 넘김은 그날 처음 지나면 멈춤, 채널별 시각 순
r10 = [r10[i] for i in (3, 0, 1, 2, 4, 5, 6)]
assert r10[0] == {"date": "2026-10-14", "ch": "tg", "id": 901, "shop": "coupang", "cat": "화장품", "price": "1~3만", "at": "23:50", "views": 3, "react": 0,
                  "kind": "deal", "name": "피지오겔 페이셜 로션 150ml", "url": "https://link.coupang.com/a/x"}  # posts.json 글 = 그 글·링크로 · 상품 칸(10/22 Cowork — kind·상품명·제휴 링크)
assert r10[1] == {"date": "2026-10-14", "ch": "tg", "id": 899, "shop": "toss", "cat": "생필품", "price": "1~3만", "at": "10:00", "views": 1200, "react": 17, "kind": "deal", "name": "크리넥스 3겹 휴지 30롤", "url": "https://toss.im/_m/A"}  # 채널 웹 글(토스 API) = 본문·버튼 링크로, 1.2K·반응 합(맞춤 이모지 포함)
assert r10[2]["cat"] == "묶음" and r10[2]["price"] == "" and r10[2]["views"] == 40 and r10[2]["kind"] == "etc"  # (상품 링크 없는 묶음 = etc)
assert (r10[3]["cat"], r10[3]["shop"], r10[3]["price"]) == ("생필품", "기타", "")  # 재오픈 답장 = 인용(원글 쿠팡 프라이팬 55,000원) 말고 답장 본문(괄호 없는 가격은 못 읽음 = 사이트 price_won 그대로)
r10 = [r for r in r10 if r["id"] != 903]
assert r10[3] == {"date": "2026-10-14", "ch": "th", "id": "t1", "shop": "toss", "cat": "식품", "price": "1~3만", "at": "12:00", "views": 340, "react": 6, "likes": 5, "replies": 0, "kind": "etc"}
assert r10[4]["price"] == "5~10만" and r10[4]["react"] == 0 and r10[4]["views"] == 0 and r10[4]["shop"] == "coupang" and (r10[4]["kind"], r10[4]["name"], r10[4]["url"]) == ("deal", "샴푸", "https://link.coupang.com/a/abc")  # 0 = 빈 칸 아님 · [몰] 없는 Threads 글 = 글 속 구매 링크로 몰
assert r10[5] == {"date": "2026-10-14", "ch": "ig", "id": "g1", "shop": "기타", "cat": "기타", "price": "", "at": "21:00", "views": None, "react": 5, "likes": 4, "replies": 1}
assert d10["2026-10-14"]["miss"] == {"ig": "조회수 권한 없음(토큰 권한 instagram_business_manage_insights 확인): 403 (#10) Application does not have permission for this action"}
assert sum(1 for l in open(H.METRICS, encoding="utf-8") if l.startswith('{"date"')) == 7  # 글 1개 = 1줄
m10.clear(); time.time = lambda: TK("2026-10-15 05:22"); H.metrics(s10); assert not m10  # 하루 1번
i10 = []
def http10b(url, body=None, headers=None, method=None):  # Threads insights 권한 없음 -> 첫 글에서 멈추고 이유만
    if "/insights?metric=views,likes" in url:
        i10.append(url); e = H.urllib.error.HTTPError(url, 400, "x", {}, None); e.body = '{"error":{"message":"Application does not have permission for this action","code":10}}'; raise e
    if "t.me/s/" in url: raise H.urllib.error.URLError("blocked")
    return http10(url, body, headers, method)
H.http, H.E["METRICS_DAY"] = http10b, "2026-10-14"; m10.clear(); H.metrics(s10); s10b = {}; H.metrics(s10b); assert s10b == {}  # 수동 실행 = 이미 모은 날도 다시, 기록 X(오늘치 점검 뒤 다음 날 5시에 전체 다시)
d10 = json.load(open(H.METRICS)); r10 = d10["2026-10-14"]["rows"]
assert len(i10) == 2 and [r["views"] for r in r10 if r["ch"] == "th"] == [None, None] and [r["react"] for r in r10 if r["ch"] == "th"] == [None, None]  # 실행마다 첫 글에서 멈춤(2번 실행 = 2번)
assert d10["2026-10-14"]["miss"]["th"].startswith("insights 권한 없음(토큰 권한 threads_manage_insights 확인): 400 Application does not have permission") and d10["2026-10-14"]["miss"]["tg"].startswith("채널 웹 못 읽음: ")
del H.E["METRICS_DAY"]
def http10d(url, body=None, headers=None, method=None):  # 지운 글(400 code 100)·빈 insights = 그 글만 빈 칸, 나머지는 계속 물음
    if url.endswith("/t1/insights?metric=views,likes,replies,reposts,quotes&access_token=tk"):
        e = H.urllib.error.HTTPError(url, 400, "x", {}, None); e.body = '{"error":{"message":"Object does not exist","code":100}}'; raise e
    if "/g1/insights?metric=views" in url: return json.dumps({"data": []})
    return http10(url, body, headers, method)
H.http = http10d; s10d = {}; time.time = lambda: TK("2026-10-15 05:37"); H.metrics(s10d); r10 = json.load(open(H.METRICS))["2026-10-14"]
assert [(r["views"], r["react"]) for r in r10["rows"] if r["ch"] != "tg"] == [(None, None), (0, 0), (None, 5)] and set(r10["miss"]) == {"th_part", "ig_part"} and r10["miss"]["th_part"] == "일부 글 insights 못 읽음: 400 Object does not exist"
assert "mt_2026-10-14" in s10d  # 4xx·빈 응답은 다시 해도 같음 -> 끝
def http10e(url, body=None, headers=None, method=None): raise H.urllib.error.URLError("timed out")
H.http = http10e; s10e = {}; H.metrics(s10e); assert s10e == {}  # 네트워크 오류 = 8시까지 다음 실행에 다시
time.time = lambda: TK("2026-10-15 08:07"); H.metrics(s10e); assert "mt_2026-10-14" in s10e and json.load(open(H.METRICS))["2026-10-14"]["miss"]["tg"] == "채널 웹 못 읽음: URLError('timed out')"
u10 = []; H.http = lambda url, body=None, headers=None, method=None: u10.append(url) or json.dumps({"data": []}); H.E["METRICS_DAY"] = "2026-10-15"; time.time = lambda: TK("2026-10-15 15:30"); H.metrics({})
assert any(f"&until={TK('2026-10-15 15:30')}&" in u for u in u10); del H.E["METRICS_DAY"]; m10x = json.load(open(H.METRICS)); m10x.pop("2026-10-15"); json.dump(m10x, open(H.METRICS, "w"))  # 오늘치(수동) = 지금까지 — 미래 until은 Threads가 거절(10/15 실행 점검: 500 'Timestamp must be less than or equal to')
del H.E["THREADS_TOKEN"], H.E["IG_TOKEN"], H.E["IG_USER_ID"]; time.time = lambda: TK("2026-10-17 06:00"); H.http = http10; H.metrics({})  # 토큰 없음 = 이유만, 14일만 남김·최신 맨 위
d10 = json.load(open(H.METRICS)); assert list(d10) == ["2026-10-16", "2026-10-14"] and d10["2026-10-16"]["miss"] == {"tg": "채널 웹에서 그날 글 0개(페이지 모양 바뀜?)", "th": "THREADS_TOKEN 없음", "ig": "IG_TOKEN·IG_USER_ID 없음"}
json.dump({f"2026-09-{d:02d}": {"at": "", "miss": {}, "rows": []} for d in range(1, 21)}, open(H.METRICS, "w")); H.metrics({})
assert list(json.load(open(H.METRICS)))[:2] == ["2026-10-16", "2026-09-20"] and len(json.load(open(H.METRICS))) == H.METRICS_KEEP == 14
assert H.tg_num("1.2K") == 1200 and H.tg_num("15") == 15 and H.tg_num("2M") == 2000000 and "th_reply_ok, th_verify, metrics, cp_price, own_end, toss_roster):" in inspect.getsource(H.main)
wf10 = open(os.path.join(os.path.dirname(os.path.abspath(H.__file__)), ".github/workflows/hotdeal.yml"), encoding="utf-8").read(); assert "git add metrics.json" in wf10 and "METRICS_DAY: ${{ inputs.metrics_day }}" in wf10 and "metrics_day:" in wf10
os.remove(H.METRICS); json.dump([], open("posts.json", "w")); H.http, time.time, H.POSTS = sv10
# 9-12) 10/15 23:40 진우 '날씨·계절 추천 · 간식 · 일상(정직하게)': Open-Meteo 하루 1번 캐시 → 7:30 날씨 글·15:30 간식 3(채널 + Threads), 20:30 운영 일지(Threads, 사실만·금지어 X),
#       일요일 20시 시즌 키워드 DM, TOP5·Threads 개별 날씨 가점(🔥·30일 최저가 순서는 그대로), '#일상' 사진 = 사이트 주소로 Threads(텔레그램 파일 주소 X)
assert wx0 == ((7, 30), (15, 30), (20, 30), (6, 20), 5) and (H.WEATHER_LAT, H.WEATHER_LON) == (37.57, 126.98)
H.WEATHER_HOUR, H.SNACK_HOUR, H.DAILY_LOG_HOUR, H.WEATHER_DM, H.WEATHER_BONUS = wx0
sv12 = (H.http, H.tg, H.th_post, H.toss, H.HAS_TOSS, time.time, H.busy); tnc12, H.TOSS_NO_CMP = H.TOSS_NO_CMP, True  # 지금 규칙(토스 = 게시 시점 가격)
W12 = lambda lo, hi, rain=0, hum=60, pm=10, day="2026-10-16": {"date": day, "tmin": lo, "tmax": hi, "rain": rain, "hum": hum, "pm": pm}
names = lambda w: [r[1] for r in H.wx_rules(w)]
assert "우산" in [k for r in H.wx_rules(W12(15, 20, rain=78)) for k in r[2]] and "라면" in [k for r in H.wx_rules(W12(15, 20, rain=78)) for k in r[3]]  # 강수 78% -> 우산·라면
assert "핫팩" in [k for r in H.wx_rules(W12(2, 9)) for k in r[2]] and names(W12(2, 9)) == ["많이 추움", "쌀쌀함"]  # 최저 2도 -> 핫팩(+ 10도 이하 규칙도)
assert "가습기" in [k for r in H.wx_rules(W12(15, 20, hum=30)) for k in r[2]] and names(W12(15, 24)) == []  # 습도 30 -> 가습기 · 9도 차·맑음 = 없음
assert names(W12(13, 25)) == ["일교차 큼"] and names(W12(22, 29, pm=40)) == ["더움", "초미세먼지 나쁨"] and "김장철" in names(W12(8, 15, day="2026-11-05")) and "빼빼로데이" in names(W12(8, 15, day="2026-11-05"))
assert "수능 주간" in names(W12(8, 15, day="2026-11-13")) and "수능 주간" not in names(W12(8, 15, day="2026-11-12")) and "수능 주간" not in names(W12(8, 15, day="2026-11-20"))
assert H.wx_hit("오뚜기 진라면 매운맛 20개", ["라면"]) and H.wx_hit("3M 공기청정기 필터 2개", ["공기청정기 필터"]) and H.wx_hit("공기청정기필터 2개", ["공기청정기 필터"]) and not H.wx_hit("휴지 30롤", ["우산"])
assert not H.wx_hit("소고기 모듬 1.2kg", ["기모"]) and H.wx_hit("융기모 레깅스", ["기모"]) and H.wx_hit("kf94 마스크", ["KF94"])  # 제목 띄어쓰기는 그대로(뒷고기 모듬 ≠ 기모)
FC12 = {"daily": {"time": ["2026-10-16", "2026-10-17", "2026-10-18"], "temperature_2m_min": [14.6, 2.2, 9.0], "temperature_2m_max": [23.8, 9.4, 15.0],
                  "precipitation_probability_max": [78, 3, 10], "relative_humidity_2m_min": [52, 30, 60]}}
AQ12 = {"hourly": {"time": ["2026-10-16T00:00", "2026-10-16T01:00", "2026-10-17T00:00"], "pm2_5": [30.0, 44.0, None]}}
c12 = []
def http12(url, body=None, headers=None, method=None):
    c12.append(url)
    if "air-quality-api.open-meteo.com" in url: return json.dumps(AQ12)
    if "api.open-meteo.com/v1/forecast" in url:
        assert "latitude=37.57&longitude=126.98" in url and "relative_humidity_2m_min" in url and "forecast_days=8" in url
        return json.dumps(FC12)
    if method == "HEAD": return ""
    raise AssertionError(url)
H.http, s12 = http12, {}; time.time = lambda: TK("2026-10-16 06:10")
w12 = H.weather(s12); H.weather(s12)
assert len(c12) == 2 and w12[0] == {"date": "2026-10-16", "tmin": 15, "tmax": 24, "rain": 78, "hum": 52, "pm": 37} and w12[1]["pm"] is None  # 하루 1번(캐시) · 초미세먼지 하루 평균
assert H.wx_line(w12[0]) == "오늘 서울 15~24도, 일교차 9도 · 비 올 확률 78% · 초미세먼지 37㎍"
H.http = lambda *a, **k: (_ for _ in ()).throw(OSError("down")); s12b = {}
assert H.weather(s12b) is None and H.wx_words(s12b) == [] and H.wx_bonus(s12b)("우산") == 0  # 예보 못 받음 -> 날씨 X(가점도 X)
s12r = {}; H.weather(s12r); c12.clear(); H.http = http12; assert H.weather(s12r) is None and not c12  # 1시간 안엔 다시 안 받음
time.time = lambda: TK("2026-10-16 07:11"); assert H.weather(s12r)[0]["tmin"] == 15 and len(c12) == 2; H.http = lambda *a, **k: (_ for _ in ()).throw(OSError("down"))  # 1시간 뒤 다시 받음(0시 실패 하나로 하루 종일 X)
out12 = []
H.tg = lambda m, **p: out12.append((m, p)) or {"message_id": 1}
H.th_post = lambda tok, text, link=None, image=None, tag="핫딜": out12.append(("th", {"text": text, "link": link, "image": image, "tag": tag})) or {"id": "1"}
H.E["THREADS_TOKEN"], H.busy = "tk", (lambda seen, cap=True: False)
time.time = lambda: TK("2026-10-16 07:35"); H.weather_post(s12b)
assert not out12 and "wxpost_20261016" in s12b  # 날씨 없으면 그날 날씨 글 건너뜀
P12 = [{"t": "2026-10-15 10:00", "text": "🔥 [쿠팡] 3단 자동 장우산 (12,900원)\n\n좋아요", "url": "https://link.coupang.com/a/u1", "mid": 1},
       {"t": "2026-10-15 11:00", "text": "🛒 [G마켓] 투명 우비 (3,000원)\n\n🤔 솔직히 특가로는 약한 제품", "url": "https://www.ppomppu.co.kr/x", "mid": 2},
       {"t": "2026-10-15 12:00", "text": "🔥 [네이버] 제습제 18개 (9,900원)\n\n좋아요", "url": "https://naver.me/abc", "mid": 3},
       {"t": "2026-10-15 13:00", "text": "🔥 [옥션] 실내건조 세제 3L (8,800원)\n\n좋아요", "url": "https://www.ppomppu.co.kr/y", "mid": 4},
       {"t": "2026-10-11 13:00", "text": "🔥 [쿠팡] 우산 꽂이 (5,000원)\n\n좋아요", "url": "https://link.coupang.com/a/old", "mid": 5},
       {"t": "2026-10-15 14:00", "text": "🔥 [쿠팡] 오리온 초코파이 24개 (6,900원)\n\n좋아요", "url": "https://link.coupang.com/a/c1", "mid": 6},
       {"t": "2026-10-15 15:00", "text": "🔥 [G마켓] 캡슐 커피머신 (59,000원)\n\n좋아요", "url": "https://www.ppomppu.co.kr/z", "mid": 7}]
json.dump(P12, open("posts.json", "w"), ensure_ascii=False)
s12["sold_901"] = {"t": TK("2026-10-15 20:00"), "k": "ev", "url": "https://toss.im/_m/T1", "n": "토스 우산", "p": 9000, "it": [[71, "토스 자동 우산 1개", 9000, 0, 0, 0]]}
s12["sold_902"] = {"t": TK("2026-10-15 21:00"), "k": "top", "rows": [["품절 우비", "https://toss.im/_m/T2", []], ["우비 판초", "https://toss.im/_m/T3", []]],
                   "it": [[72, "품절 우비", 3000, 0, 1, 0], [73, "우비 판초", 4500, 0, 0, 0]]}
H.HAS_TOSS, H.toss = True, lambda path, body=None: {"items": [{"tacaItemId": 71, "displayPrice": 8500, "isSoldOut": False}, {"tacaItemId": 73, "displayPrice": 4500, "isSoldOut": True}]}
time.time = lambda: TK("2026-10-16 07:20"); H.weather_post(s12); assert not out12  # 7:30 전 X
time.time = lambda: TK("2026-10-16 07:35"); H.weather_post(s12)
(m12, p12), th12 = out12[0], out12[1][1]
assert m12 == "sendMessage" and p12["chat_id"] == "@ch" and p12["parse_mode"] == "HTML" and "wxpost_20261016" in s12
t12 = p12["text"]
assert t12.index(H.DISCLOSURE) < t12.index("☁️") and H.NAVER_NOTE in t12 and H.TOSS_NOTE in t12  # 링크 있는 몰의 대가성 문구 맨 앞
assert "<b>☁️ 오늘 서울 15~24도, 일교차 9도 · 비 올 확률 78% · 초미세먼지 37㎍ — 이런 날 필요한 것</b>" in t12
rows12 = [l for l in t12.split("\n") if l.startswith(("🔥", "🛒"))]
assert rows12 == ['🔥 <a href="https://toss.im/_m/T1">토스 자동 우산 1개</a> 8,500원', '🔥 <a href="https://naver.me/abc">제습제 18개</a> 9,900원',
                  '🔥 <a href="https://link.coupang.com/a/u1">3단 자동 장우산</a> 12,900원'], rows12  # 3사 먼저 · 🔥 먼저 · 최근 먼저, 3개까지 · 토스 = 지금 가격 · 품절(73)·품절 표시(72)·3일 지난 딜 X
assert t12.rstrip().endswith("게시 시점 가격") and not re.search(H.OTHER_STORES + r"|보다|대비|차이|같은 상품", rows12[0])  # 토스 줄 = 다른 몰 이름·비교 X, 게시 시점 가격 줄
assert th12["text"].startswith(H.TOSS_NOTE) and "🔥 토스 자동 우산 1개 8,500원\n👉 https://toss.im/_m/T1" in th12["text"] and th12["link"] == "https://toss.im/_m/T1" and len(th12["text"]) <= 500
assert "🔥 제습제 18개 9,900원\n👉 https://naver.me/abc" in th12["text"] and H.NAVER_NOTE in th12["text"] and "hotdealpick.kr/p/" not in th12["text"]  # Threads = 텔레그램 버튼과 같은 링크(10/19 진우 '경유 말고 직접'), 대가성 문구는 그 링크 기준
out12.clear(); time.time = lambda: TK("2026-10-16 07:50"); H.weather_post(s12); assert not out12  # 하루 1번
L12 = [{"n": "아주아주 긴 상품 이름 " * 4, "p": "12,900원", "u": f"https://toss.im/_m/{'x' * 100}{k}", "hot": True, "toss": 1} for k in range(3)]
H.wx_post({}, "k", "🍪 출출할 때 간식 {n}", L12, "", "snack", lo=2); th12b = out12[-1][1]
assert "<b>🍪 출출할 때 간식 3</b>" in out12[0][1]["text"] and th12b["text"].count("👉") == 2 and "🍪 출출할 때 간식 2\n" in th12b["text"] and len(th12b["text"]) <= 480 and th12b["link"] == L12[0]["u"]; out12.clear()  # Threads 500자 넘으면 뒤 딜부터 뺌 · 머리 수도 같이
H.wx_post({}, "k", "🍪 출출할 때 간식 {n}", L12, "", "snack", lo=3); assert [m for m, p in out12] == ["sendMessage"]; out12.clear()  # lo개로도 넘으면 Threads X(500자 넘는 글 안 보냄)
L12b = [{"n": "롯데 빼빼로 오리지널 12갑", "p": "9,900원", "u": "https://click.linkprice.com/click.php?m=lotteon&a=A100&l=9999&u_id=" + "z" * 400, "i": 5, "hot": True}]
H.wx_post({}, "k", "☁️ 오늘", L12b, "", "wx"); th12c = out12[-1][1]
assert th12c["text"].startswith(H.AFF_NOTE) and th12c["link"] == "https://hotdealpick.kr/p/5.html?ref=th" and "linkprice" not in th12c["text"] and "linkprice" in out12[0][1]["text"]; out12.clear()  # 채널 = 제휴 링크, Threads = 500자에 못 들어가는 긴 링크(TH_LINK_MAX 넘음)만 사이트 딜 페이지
s12c = {"wx_20261016": {"t": 1, "w": [W12(16, 24)]}}; H.weather_post(s12c)
assert [p["text"] for m, p in out12 if m == "sendMessage"] == ["☁️ 오늘 서울 16~24도, 일교차 8도\n오늘은 뭐 챙기셨어요?"] and out12[1][1]["text"] == "☁️ 오늘 서울 16~24도, 일교차 8도\n오늘은 뭐 챙기셨어요?" and out12[1][1]["link"] is None  # 맞는 딜 0개 = 날씨 + 질문(링크 X)
out12.clear(); s12d = {"wx_20261016": {"t": 1, "w": [W12(15, 20, rain=78)]}}; H.busy = lambda seen, cap=True: True; H.weather_post(s12d); assert not out12 and "wxpost_20261016" not in s12d  # 묶음 간격·시간당 상한 -> 다음 실행에
time.time = lambda: TK("2026-10-16 09:31"); H.busy = lambda seen, cap=True: False; H.weather_post(s12d); assert not out12  # 2시간 지나면 안 올림
H.HAS_TOSS = False; time.time = lambda: TK("2026-10-16 15:35"); s12e = {"wx_20261016": {"t": 1, "w": [W12(15, 20)]}}; H.snack_post(s12e)
assert not out12 and "snack_20261016" in s12e  # 간식 딜 1개(초코파이 — 커피머신은 간식 아님) -> 안 올림
P12.append({"t": "2026-10-15 16:00", "text": "🔥 [토스] 하리보 젤리 10봉 (7,900원)\n\n좋아요", "url": "https://toss.im/_m/J", "mid": 8})
P12.append({"t": "2026-10-15 17:00", "text": "🔥 [쿠팡] 진라면 매운맛 20개 (13,900원)\n\n좋아요", "url": "https://link.coupang.com/a/r1", "mid": 9}); json.dump(P12, open("posts.json", "w"), ensure_ascii=False)
s12f = {"wx_20261016": {"t": 1, "w": [W12(15, 20, rain=78)]}}; H.snack_post(s12f)  # 비 -> 라면도 간식 · 토스 커뮤니티 딜(posts.json)은 지금 가격을 못 봐서 X
t12s = out12[0][1]["text"]
assert all(re.search(H.SNACK_NOT, t) for t in ("한돈 갈빗살 떡갈비 20개", "투명 젤리 케이스", "칼리타 커피 필터", "메가커피 금액권 10% 할인", "홈블리 과탄산소다 5kg")) and not re.search(H.SNACK_NOT, "슬림떡볶이 로제맛 4개 64%할인")  # 간식 아님
assert "<b>🍪 출출할 때 간식 2</b>" in t12s and "진라면 매운맛 20개" in t12s and "초코파이" in t12s and "커피머신" not in t12s and "하리보" not in t12s and t12s.startswith(f"<i>{H.DISCLOSURE}</i>")
json.dump(P12 + [{"t": "2026-10-15 18:00", "text": "🔥 [G마켓] 마이핫 보온대 핫팩 150g (30개) (12,900원/무료)\n\n좋아요", "url": "u", "mid": 10},
                 {"t": "2026-10-15 18:30", "text": "🔥 [쿠팡] 3단 자동 우산 (1+1) (21,920/무료)\n\n좋아요", "url": "u", "mid": 11},
                 {"t": "2026-10-15 18:40", "text": "🔥 [쿠팡] 신라면 5개 (2,400원) (무료)\n\n좋아요", "url": "u", "mid": 12}], open("posts.json", "w"), ensure_ascii=False)
assert [(c["n"], c["p"]) for c in H.wx_deals(s12f, ["핫팩", "자동 우산", "신라면"])] == [("신라면 5개", "2,400원"), ("3단 자동 우산 (1+1)", "21,920원"), ("마이핫 보온대 핫팩 150g (30개)", "12,900원")]  # 가격 괄호만 빼고 수량·1+1은 그대로
out12.clear()
J12 = {"t": TK("2026-10-16 01:00")}
s12g = {"wx_20261016": {"t": 1, "w": [W12(8, 15)]}, "ppomppu_1": TK("2026-10-16 01:00"), "ppomppu_2": TK("2026-10-16 02:00"), "clien_3": TK("2026-10-16 03:00"),
        "ruliweb_4": TK("2026-10-16 04:00"), "ppomppu_old": TK("2026-10-15 23:00"), "k:abc": TK("2026-10-16 05:00")}
json.dump([{"t": "2026-10-16 09:00", "text": "🔥 [쿠팡] 휴지 30롤 (19,900원)", "url": "u", "vpm": 3.1}, {"t": "2026-10-16 10:00", "text": "🔥 [쿠팡] 핫팩 30개 (9,900원)", "url": "u", "vpm": 9.5},
           {"t": "2026-10-16 11:00", "text": "🔥 [토스] 진우 예약", "url": "u", "own": 1}], open("posts.json", "w"), ensure_ascii=False)
time.time = lambda: TK("2026-10-16 20:35"); H.daily_log(s12g)
assert out12 == [("th", {"text": "📝 핫딜픽 운영 일지 · 10/16\n오늘 핫딜픽이 본 커뮤니티 딜 4개 중 2개만 골랐어요.\n커뮤니티 반응이 제일 빨랐던 딜: 핫팩 30개\n\n다들 전기요 꺼냈어요?",
                          "link": None, "image": None, "tag": "핫딜"})], out12  # 사실만(오늘 본 딜·고른 딜·조회 1등) + 날씨 질문 · 링크 X · Threads만
assert s12g["bundles"]["ts"] and "cap=False" in inspect.getsource(H.daily_log)  # 묶음 간격 기록 · 채널 시간당 상한은 안 셈(Threads만이라)
out12.clear(); H.LOG_DENY, ld0 = H.LOG_DENY + ("핫팩",), H.LOG_DENY; s12g.pop("dlog_20261016"); H.daily_log(s12g); assert not out12 and "dlog_20261016" in s12g; H.LOG_DENY = ld0  # 금지어 -> 안 올림
json.dump([{"t": "2026-10-16 09:00", "text": "🔥 [쿠팡] 써봤는데 좋은 휴지 (9,900원)", "url": "u", "vpm": 2.0}], open("posts.json", "w"), ensure_ascii=False)
assert H.log_text(s12g) is None and all(w in H.LOG_DENY for w in ("써봤", "써보니", "사용해보니", "제가 직접", "내돈내산", "우리 집"))  # 일지에 '써봤' -> 안 올림
s12h = {"wx_20261018": {"t": 1, "w": [W12(9, 16, day=f"2026-10-{d}", rain=70 if d in (19, 20) else 0) for d in range(18, 26)]}}
time.time = lambda: TK("2026-10-17 20:05"); H.wx_dm({"wx_20261017": s12h["wx_20261018"]}); assert not out12  # 토요일 X
time.time = lambda: TK("2026-10-18 19:55"); H.wx_dm(s12h); assert not out12  # 20시 전 X
time.time = lambda: TK("2026-10-18 20:05"); H.wx_dm({"wx_20261018": {"t": time.time(), "w": []}}); assert not out12  # 날씨 못 받으면 안 보냄(키도 안 남김 -> 다음 실행에 다시)
s12k = {"wx_20261018": {"t": time.time() - 4000, "w": []}}; H.http = http12; H.wx_dm(s12k); assert "wxdm_20261018" in s12k and len(out12) == 1; out12.clear(); H.http = lambda *a, **k: (_ for _ in ()).throw(OSError("down"))
H.wx_dm(s12h); H.wx_dm(s12h)
(m12, p12), = out12
d12 = p12["text"]
assert p12["chat_id"] == H.ADMIN and p12["link_preview_options"] == {"is_disabled": True} and d12.startswith("🗓 다음 7일 서울 예보(10/19~10/25) — 쿠팡 링크 만들 시즌 키워드")
k12 = [l for l in d12.split("\n") if re.match(r"\d+\. ", l)]
assert len(k12) == 15 and k12[0] == "1. 전기요 (7일) " + H.CP_SEARCH + "%EC%A0%84%EA%B8%B0%EC%9A%94" and "4. 우산 (2일) " in k12[3] and k12[7].startswith("8. 휴지 ") and k12[9].startswith("10. 세제 ") and k12[10].startswith("1. 호빵 (7일)")
assert ". 가습기 (1일) " in H.wx_dm_text([W12(2, 9, hum=30)]) and ". 어묵 (1일) " in H.wx_dm_text([W12(2, 9, rain=80)])  # 규칙 두 개에 든 키워드도 그날 1번
out12.clear(); H.http = http12
UP = [{"update_id": 9, "message": {"message_id": 77, "from": {"id": 42}, "chat": {"id": 42}, "photo": [{"file_id": "small"}, {"file_id": "big"}],
                                   "caption": "#일상 오늘 저녁은 집밥 🍚 https://link.coupang.com/a/rice"}}]
real_open12 = H.urllib.request.urlopen
class R12:
    def __init__(s, d): s.d = d
    def read(s): return s.d
    def __enter__(s): return s
    def __exit__(s, *a): pass
got12 = []
H.urllib.request.urlopen = lambda url, timeout=None: got12.append(url) or R12(b"JPEGDATA")
H.tg = lambda m, **p: out12.append((m, p)) or (UP if m == "getUpdates" and "offset" not in p else {"file_path": "photos/f.jpg"} if m == "getFile" else {"message_id": 1})
s12i = {}; time.time = lambda: TK("2026-10-16 19:00"); H.publish_approved(s12i)
H.urllib.request.urlopen = real_open12
assert got12 == ["https://api.telegram.org/file/bott/photos/f.jpg"] and open("docs/daily/20261016_77.jpg", "rb").read() == b"JPEGDATA"  # 사진 = 가장 큰 것, 사이트 폴더에 저장
assert s12i["dly_77"] == {"t": TK("2026-10-16 19:00"), "text": "#일상 오늘 저녁은 집밥 🍚 https://link.coupang.com/a/rice", "img": "https://hotdealpick.kr/daily/20261016_77.jpg"}
assert ("getFile", {"file_id": "big"}) in out12 and not any(m == "sendMessage" and p.get("chat_id") == "@ch" for m, p in out12)  # 채널·딜 초안으로 안 감
out12.clear(); H.tg = lambda m, **p: out12.append((m, p)) or {"message_id": 1}
H.http = lambda url, body=None, headers=None, method=None: (_ for _ in ()).throw(OSError("404")) if method == "HEAD" else http12(url)
H.daily_post(s12i); assert not out12  # 사이트 반영 전 -> 기다림
H.http = http12; time.time = lambda: TK("2026-10-16 19:16"); H.daily_post(s12i); H.daily_post(s12i)
th12 = [p for m, p in out12 if m == "th"]
assert len(th12) == 1 and th12[0] == {"text": H.th_note(H.DISCLOSURE) + "#일상 오늘 저녁은 집밥 🍚 https://link.coupang.com/a/rice", "link": None, "image": "https://hotdealpick.kr/daily/20261016_77.jpg", "tag": "일상"}
assert "api.telegram.org" not in json.dumps(th12) and ("sendMessage", {"chat_id": H.ADMIN, "reply_parameters": {"message_id": 77}, "text": "✅ Threads에 올렸어요"}) in out12  # 사이트 주소만 · '올렸어요' 답장
out12.clear(); s12j = {"dly_78": {"t": TK("2026-10-16 18:00"), "text": "#일상 산책", "img": "https://hotdealpick.kr/daily/x.jpg"}}
H.http = lambda url, body=None, headers=None, method=None: (_ for _ in ()).throw(OSError("404")); H.daily_post(s12j)
assert s12j["dly_78"]["done"] and not [p for m, p in out12 if m == "th"] and "못 올렸어요" in out12[0][1]["text"]  # 1시간 넘게 안 뜨면 알리고 그만
UP[0]["update_id"] = 10; out12.clear(); H.tg = lambda m, **p: out12.append((m, p)) or (UP if m == "getUpdates" and "offset" not in p else {"message_id": 1}); H.publish_approved(s12i)
assert not [m for m, p in out12 if m == "getFile"] and s12i["dly_77"]["done"]  # 같은 메시지가 다시 와도 1번
UP[:] = [{"update_id": 11, "message": {"message_id": 79, "from": {"id": 42}, "chat": {"id": 42}, "text": "#일상 오늘 비 와요"}},
         {"update_id": 12, "message": {"message_id": 80, "from": {"id": 42}, "chat": {"id": 42}, "photo": [{"file_id": "p80"}],
                                       "caption": "#일상 간식 https://link.coupang.com/a/s1 https://toss.im/_m/T9."}},
         {"update_id": 13, "message": {"message_id": 81, "from": {"id": 42}, "chat": {"id": 42}, "document": {"file_id": "doc", "mime_type": "image/jpeg"}, "caption": "#일상 원본"}},
         {"update_id": 14, "message": {"message_id": 82, "from": {"id": 42}, "chat": {"id": 42}, "photo": [{"file_id": "p82"}], "caption": "#일상 " + "가" * 440 + " https://link.coupang.com/a/z"}},
         {"update_id": 15, "message": {"message_id": 83, "from": {"id": 42}, "chat": {"id": 42}, "photo": [{"file_id": "p83"}], "caption": "#일상 [https://hotdealpick.kr]에서 봐요"}},
         {"update_id": 16, "message": {"message_id": 84, "from": {"id": 42}, "chat": {"id": 42}, "photo": [{"file_id": "p84"}], "caption": "#일상 " + "😀" * 130}},
         {"update_id": 17, "message": {"message_id": 85, "from": {"id": 42}, "chat": {"id": 42}, "photo": [{"file_id": "p85"}], "caption": "#일상 장 봤어요\n쿠팡보다 3,000원 싸서 https://toss.im/_m/abc"}}]
out12.clear(); H.tg = lambda m, **p: out12.append((m, p)) or (UP if m == "getUpdates" and "offset" not in p else {"file_path": "photos/f.jpg"} if m == "getFile" else {"message_id": 1})
H.urllib.request.urlopen = lambda url, timeout=None: R12(b"JPG"); H.publish_approved(s12i); H.urllib.request.urlopen = real_open12
rp12 = {p["reply_parameters"]["message_id"]: p["text"] for m, p in out12 if m == "sendMessage" and p.get("reply_parameters")}
assert "dly_79" not in s12i and "사진과 같이" in rp12[79]  # 사진 없으면 답장만(글만은 안 올림)
assert [p["file_id"] for m, p in out12 if m == "getFile"] == ["p80"] and s12i["dly_80"]["img"] == "https://hotdealpick.kr/daily/20261016_80.jpg"
assert "dly_81" not in s12i and "사진으로 보내줘" in rp12[81]  # 파일(원본)로 보내면 X — 원본엔 위치(GPS) 정보가 남아 사이트에 공개됨
assert "dly_83" not in s12i and "못 받았어요" in rp12[83]  # 깨진 주소 -> 답장만(예외로 실행 전체가 멈추지 않음)
assert "dly_84" not in s12i and rp12[84].startswith("✂️ 글이 52") and "dly_85" not in s12i and "토스 규칙" in rp12[85]  # 이모지 = 바이트로 셈 · 토스 링크 글에 다른 몰 비교 X
assert "dly_82" not in s12i and rp12[82].startswith("✂️ 글이 ") and len(H.daily_text("#일상 " + "가" * 440 + " https://link.coupang.com/a/z")) > 480  # 대가성 문구 포함 480자 넘으면 답장만(잘린 글 X)
out12.clear(); H.tg = lambda m, **p: out12.append((m, p)) or {"message_id": 1}; H.busy = lambda seen, cap=True: True; H.daily_post(s12i); assert not out12  # 묶음 간격 -> 다음 실행에
H.http, H.busy = http12, (lambda seen, cap=True: False); H.daily_post(s12i); th12d = [p for m, p in out12 if m == "th"][0]["text"]
assert th12d == H.th_note(H.DISCLOSURE + "\n" + H.TOSS_NOTE) + "#일상 간식 https://link.coupang.com/a/s1 https://toss.im/_m/T9.\n\n" + H.toss_when() and s12i["bundles"]["ts"]  # 프로그램마다 대가성 문구 · 토스 = 게시 시점 줄
out12.clear()
H.WEATHER_BONUS = 5; bs12 = {"wx_20261016": {"t": 1, "w": [W12(15, 20, rain=78)]}}
assert H.wx_bonus(bs12)("3단 자동 장우산") == 5 and H.wx_bonus(bs12)("휴지") == 0 and H.wx_bonus(bs12)("진라면 20개") == 5  # 아이템·간식 키워드
H.WEATHER_BONUS = 0; assert H.wx_bonus(bs12)("우산") == 0; H.WEATHER_BONUS = wx0[4]
assert "-(p.get(\"pop\") or 0), -wb(title_of(p[\"text\"]))" in inspect.getsource(H.top_deals) and "th_tier(c[1]) or 3, -wb(title_of(c[1])), c[3]" in inspect.getsource(H.threads_deals)  # 가점 = 반응 점수·같은 등급 안에서만
assert "top_deals, steady_list, weather_post, snack_post, poll_post, toss_deals" in inspect.getsource(H.main) and "threads_deals, daily_post, daily_log, wx_dm, toss_reopen" in inspect.getsource(H.main) and "publish_approved(seen)" in inspect.getsource(H.main)
H.http, H.tg, H.th_post, H.toss, H.HAS_TOSS, time.time, H.busy = sv12; del H.E["THREADS_TOKEN"]; H.TOSS_NO_CMP = tnc12
H.WEATHER_HOUR, H.SNACK_HOUR, H.DAILY_LOG_HOUR, H.WEATHER_DM, H.WEATHER_BONUS = None, None, None, None, 0; json.dump([], open("posts.json", "w"))
# 9-13) 10/17 진우 '유입 늘리기': ① Threads 가격 투표(12:30, 다음 날 결과 답글) ② 최저가 기록 페이지(/c/) — 같은 단위만·토스 X·3개 미만 X·7일 안 쓴 품목만
import build_site as S13
assert pl0 == (21, 40) and H.POLL_REUSE == 7 and S13.PRICE_MIN == 3  # 10/22~ 21:40(이 셀프체크는 예전 12:30으로 회차 동작만 — Claude 투표 글·21:40은 9-27)
def p13(t, title, unit, url="https://link.coupang.com/a/x", mid=1):
    return {"t": t, "text": f"🔥 {title}\n\n좋아요\n\n💡 단위가격 {unit}", "url": url, "mid": mid}
P13 = [p13("2026-10-10 10:00", "[쿠팡] 신라면 40개 (23,480원)", "개당 587원"), p13("2026-10-12 10:00", "[쿠팡] 신라면 5개 (2,400원)", "개당 480원"),
       p13("2026-10-13 10:00", "[지마켓] 안성탕면 20봉 (13,400원)", "봉당 약 670원"), p13("2026-10-14 10:00", "[네이버] 컵누들 12개 (9,400원)", "100g당 1,910원"),  # 100g당 = 다른 단위 -> X
       p13("2026-10-14 11:00", "[토스] 진라면 30개 (12,000원)", "개당 400원", "https://toss.shopping/_m/T1"),  # 토스 = 기록 X(더 싸도)
       p13("2026-10-15 10:00", "[쿠팡] 라면 냄비 2개 (9,000원)", "개당 4,500원"),  # 품목 아님
       p13("2026-10-11 10:00", "[네이버] 풀무원생수 2L 24개 (11,900원)", "개당 약 496원 (1L당 248원)"), p13("2026-10-12 10:00", "[쿠팡] 삼다수 500ml 40병 (16,000원)", "병당 400원"),
       p13("2026-10-13 10:00", "[네이버] 삼다수 2L 6개 (6,040원)", "1L당 503원"),  # 생수 1L당 2개 = 기록 2개 품목 -> 페이지·투표 X
       {"t": "2026-10-13 11:00", "text": "📋 진우 메모 신라면 개당 1원", "url": None}]
json.dump(P13, open("posts.json", "w"), ensure_ascii=False)
r13 = S13.price_records(P13)
assert list(r13) == ["ramen"] and [x[1] for x in r13["ramen"][2]] == ["개당 480원", "개당 587원", "개당 670원"]  # 같은 단위만(봉당 = 개당, 100g당 X)·싼 순, 토스·냄비·📋 X, 생수(1L당 2개) = 3개 미만 X
assert S13.price_records(P13[6:9] + [p13("2026-10-14 10:00", "[네이버] 삼다수 2L 12개 (12,000원)", "1L당 500원")])["water"][2][0][1] == "1L당 248원"  # 한 줄에 두 단위 -> 품목 단위(1L당)만
assert S13.price_records(P13 + [p13("2026-10-16 10:00", "[쿠팡] 신라면 5개 (2,400원)", "개당 480원")])["ramen"][2][0][2] == len(P13)  # 같은 상품·같은 단위가격 다시 = 최근 1개
d13 = tempfile.mkdtemp(); os.makedirs(f"{d13}/c"); open(f"{d13}/c/old.html", "w").write("x"); S13.build(P13, d13)
assert sorted(os.listdir(f"{d13}/c")) == ["ramen.html"]  # 기록 3개↑ 품목만 · 옛 페이지 지움
c13, sm13, ix13 = (open(f"{d13}/{f}").read() for f in ("c/ramen.html", "sitemap.xml", "index.html"))
assert "<title>라면 최저가 기록 — 개당 가격 | 핫딜픽</title>" in c13 and '<link rel="canonical" href="https://hotdealpick.kr/c/ramen.html">' in c13 and S13.NAVER_VERIFY[1] in c13
assert "진라면" not in c13 and "toss.shopping" not in c13 and "컵누들" not in c13 and "냄비" not in c13 and 'href="https://hotdealpick.kr/#toss">토스 탭에서 보기' in c13  # 토스 행 X(링크 한 줄만)
assert c13.count("<tr") == 4 and "<td>10/12</td><td>쿠팡</td>" in c13 and 'href="https://hotdealpick.kr/p/1.html">신라면 5개</a></td><td>2,400원</td><td>480원</td>' in c13 and "평균 · 기록 3개" in c13 and "<b>579원</b>" in c13
assert sm13.count("/c/") == 1 and "<loc>https://hotdealpick.kr/c/ramen.html</loc><lastmod>2026-10-13</lastmod>" in sm13  # lastmod = 마지막 기록 날짜
assert ('id="life"' in ix13) == ('href="https://hotdealpick.kr/c/ramen.html">라면 개당</a>' in ix13)  # 홈 생필품 칸 링크(칸이 있으면)
assert 'href="https://hotdealpick.kr/c/ramen.html">📈 라면 개당 최저가 기록 보기' in open(f"{d13}/p/0.html").read() and "c/ramen.html" in open(f"{d13}/p/3.html").read()  # 그 품목 딜 페이지 -> 기록(단위 다른 컵누들도)
assert "c/ramen.html" not in open(f"{d13}/p/4.html").read() and "c/ramen.html" not in open(f"{d13}/p/6.html").read()  # 토스 딜·다른 품목 페이지엔 X
assert {k: h for k, _, h in S13.cat_sections([p13("2026-10-16 10:00", "[쿠팡] 크리넥스 휴지 30롤 (19,900원)", "롤당 663원")], ["2026-10-16"], "<nav>R</nav>")}["life"].endswith("<nav>R</nav></section>")
assert H.poll_opts(480) == ["500원 이하", "600원까지", "700원까지", "더 줘도 사요"] and H.poll_opts(120)[:2] == ["120원 이하", "140원까지"] and H.poll_opts(2590)[0] == "2,500원 이하" and H.poll_opts(4.7)[0] == "10원 이하"
assert H.poll_text(r13["ramen"]) == ("🗳️ 라면 개당 얼마면 '싸다' 싶어요?\n\n내일 이 글 답글로 핫딜픽 기록 최저가 알려드릴게요", H.poll_opts(480))
c13h = []
def http13(url, body=None, headers=None, method=None):
    c13h.append((url, body, headers, method))
    if "/me?fields=id" in url: return json.dumps({"id": "me"})
    if "/me/threads?" in url and method == "POST": return json.dumps({"id": "c1"})
    if "/threads_publish?" in url: return json.dumps({"id": "pol1"})
    if "/pol1?fields=poll_attachment{" in url:
        return json.dumps({"id": "pol1", "poll_attachment": {"option_a": "500원 이하", "option_b": "600원까지", "option_c": "700원까지", "option_d": "더 줘도 사요", "option_a_votes_percentage": 0.25,
                                                             "option_b_votes_percentage": 0.5, "option_c_votes_percentage": 0.25, "option_d_votes_percentage": 0, "total_votes": 8}})
    raise AssertionError(url)
sv13 = (H.http, H.th_reply, H.th_reply_ok, H.busy, H.time.sleep, time.time, H.tg, H.TH_SOLO_GAP); H.TH_SOLO_GAP = 45 * 60
rp13, al13 = [], []
H.http, H.time.sleep, H.busy, H.E["THREADS_TOKEN"], H.POLL_HOUR = http13, (lambda s: None), (lambda seen, cap=True: False), "tk", (12, 30)  # Claude 없음(API 키 X) = 지금 틀(poll_text)로
H.th_reply, H.th_reply_ok, H.tg = (lambda tok, to, text: rp13.append((to, text)) or "r1"), (lambda seen: True), (lambda m, **p: al13.append(p.get("text")) or {"message_id": 1})
try: H.th_poll("tk", "x", ["가" * 26, "b"]); raise AssertionError("26자 보기")
except ValueError: assert not c13h  # 보기 25자 넘으면 안 올림(API 안 부름)
try: H.th_poll("tk", "x", ["a"]); raise AssertionError("보기 1개")
except ValueError: pass
s13 = {}; time.time = lambda: TK("2026-10-17 12:20"); H.poll_post(s13); assert not c13h and not s13  # 12:30 전 X
time.time = lambda: TK("2026-10-17 12:34"); H.poll_post(s13)
q13 = [x for x in c13h if "/me/threads?" in x[0]][0]
assert parse_qs(urlsplit(q13[0]).query)["text"] == [H.poll_text(r13["ramen"])[0]] and parse_qs(urlsplit(q13[0]).query)["media_type"] == ["TEXT"] and "link_attachment" not in q13[0]
assert json.loads(parse_qs(q13[1].decode())["poll_attachment"][0]) == {"option_a": "500원 이하", "option_b": "600원까지", "option_c": "700원까지", "option_d": "더 줘도 사요"}  # 문서 예시처럼 본문(-d)
assert s13["poll_20261017"] and s13["polls"]["open"]["id"] == "pol1" and s13["polls"]["used"] == {"ramen": TK("2026-10-17 12:34")} and s13["thsolo_20261017"]["last"] == TK("2026-10-17 12:34") and s13["thsolo_20261017"]["n"] == 0  # 45분 간격만 같이(개수 X)
c13h.clear(); H.poll_post(s13); assert not c13h  # 하루 1번
s13b = {"thsolo_20261018": {"n": 1, "last": TK("2026-10-18 12:10")}}; time.time = lambda: TK("2026-10-18 12:31"); H.poll_post(s13b); assert not c13h and "poll_20261018" not in s13b  # Threads 45분 간격 -> 다음 실행에
H.busy = lambda seen, cap=True: True; H.poll_post({}); assert not c13h; H.busy = lambda seen, cap=True: False  # 묶음 간격·시간당 상한 -> 다음 실행에
H.poll_post(s13); assert "poll_20261018" in s13 and s13["polls"]["used"] == {"ramen": TK("2026-10-17 12:34")}  # 다음 날: 기록 3개↑ 품목(라면뿐)이 7일 안에 쓰임 -> 투표 X(답글은 먼저)
assert len(rp13) == 1 and rp13[0][0] == "pol1" and '📊 어제 1등은 "600원까지" 50% ㅋㅋ\n쟁일 거면 이 가격은 알아두자 → 핫딜픽 기록 최저 라면 개당 480원 (10/12)' in rp13[0][1] and "👉 https://hotdealpick.kr/c/ramen.html?ref=th" in rp13[0][1] and "\n👋 팔로우하면 매일 이런 가격 비교가 피드에 떠요\n" in rp13[0][1] and "🙋" not in rp13[0][1]  # 투표 결과 답글 팔로우 줄 = 👋(10/21)
assert rp13[0][1].startswith(H.th_note(H.DISCLOSURE)) and s13["polls"]["open"] is None  # 사이트 링크 글 규칙(그 딜들 대가성 문구 맨 앞) · 답글 1번
rp13.clear(); del s13["poll_20261018"]; H.poll_post(s13); assert not rp13  # 답글은 1번만
s13["polls"]["open"] = {"id": "pol1", "slug": "ramen", "t": TK("2026-10-17 12:34")}; del s13["poll_20261018"]; H.th_reply_ok = lambda seen: False; s13["threply"] = {"t": 1, "ok": 0, "err": "(#10) no permission"}
H.poll_post(s13); assert not rp13 and len(al13) == 1 and "가격 투표 결과 답글 못 달았어요" in al13[0] and "(#10) no permission" in al13[0] and s13["polls"]["open"] is None  # 댓글 권한 X -> 건너뜀·알림
z13 = H.poll_reply_text("ramen", r13["ramen"], {"option_a": "500원 이하", "option_b": "600원까지", "total_votes": 0, "option_a_votes_percentage": 0, "option_b_votes_percentage": 0})
assert "1등" not in z13 and "📊 어제는 아무도 안 찍음 ㅋㅋ 그래도 알려줌\n쟁일 거면 이 가격은 알아두자 → 핫딜픽 기록 최저 라면 개당 480원 (10/12)" in z13 and H.poll_reply_text("ramen", r13["ramen"], None) == z13  # 투표 0명(못 읽음)
assert '1등은 "600원까지" 50%' in H.poll_reply_text("ramen", r13["ramen"], {"option_a": "500원 이하", "option_b": "600원까지", "total_votes": 4, "option_a_votes_percentage": 50, "option_b_votes_percentage": 50.0001})  # 0~100으로 와도
H.th_reply_ok = lambda seen: True; u13 = {"t": 1, "used": {"ramen": TK("2026-10-15 12:30")}, "open": None}; P13b = P13 + [p13(f"2026-10-1{d} 10:00", f"[쿠팡] 크리넥스 화장지 30롤 {d} (19,900원)", f"롤당 {600 + d}원") for d in (1, 2, 3)]
json.dump(P13b, open("posts.json", "w"), ensure_ascii=False); c13h.clear(); time.time = lambda: TK("2026-10-19 12:31"); s13c = {"polls": u13}; H.poll_post(s13c)
assert s13c["polls"]["used"] == {"ramen": TK("2026-10-15 12:30"), "toilet-paper": TK("2026-10-19 12:31")} and "🗳️ 화장지 롤당" in parse_qs(urlsplit([x for x in c13h if "/me/threads?" in x[0]][0][0]).query)["text"][0]  # 7일 안 쓴 품목만(라면 = 4일 전에 씀 -> 화장지)
os.path.exists("docs/cards/2026-10-22.png") and os.remove("docs/cards/2026-10-22.png")  # 앞 셀프체크가 남긴 카드(21시 카드가 아직 안 나간 걸로 보여 투표가 기다림 — 9-27)
time.time = lambda: TK("2026-10-22 12:31"); rp13.clear(); H.poll_post(s13c); assert s13c["polls"]["used"] == {"toilet-paper": TK("2026-10-19 12:31"), "ramen": TK("2026-10-22 12:31")} and len(rp13) == 1  # 7일 지난 라면 다시(어제 투표 답글 먼저)
H.E["METRICS_DAY"] = "2026-10-16"; th13 = [{"id": "v1", "text": H.poll_text(r13["ramen"])[0], "timestamp": "2026-10-16T03:30:00+0000"}, {"id": "w1", "text": "☁️ 오늘 서울 13~24도\n겉옷 챙기셨어요?", "timestamp": "2026-10-15T22:30:00+0000"}]
H.http = lambda url, body=None, headers=None, method=None: json.dumps({"data": th13} if "/me/threads?" in url else {"data": []}) if "threads" in url else ""
H.metrics({}); m13 = {r["id"]: r["cat"] for r in json.load(open(H.METRICS))["2026-10-16"]["rows"]}; assert m13 == {"v1": "투표", "w1": "날씨"}, m13  # 투표 글·날씨 글 따로(딜 글과 조회 비교)
del H.E["METRICS_DAY"], H.E["THREADS_TOKEN"]; (H.http, H.th_reply, H.th_reply_ok, H.busy, H.time.sleep, time.time, H.tg, H.TH_SOLO_GAP), H.POLL_HOUR = sv13, None; json.dump([], open("posts.json", "w"))
# 9-14) 10/17 23시 진우 '인스타 자동 게시 멈춤'(IG_AUTO 꺼짐 기본): 카드·넘기기·릴스·다시 올리기·발행 인스타 API 0번, 남은 컨테이너는 발행 없이 지움, 2207051 알림 = 스팸 의심(토큰 X)
assert iga0 is True  # 10/23 진우 다시 켬(10/17~10/23 꺼 둠 — 끄면 아래처럼 인스타 API 0번)
c14 = []
def http14(url, body=None, headers=None, method=None):
    c14.append(url)
    if "graph.instagram.com" in url or "graph.facebook.com" in url:
        return json.dumps({"status_code": "FINISHED", "id": "pub1"})
    if method == "HEAD": return ""
    raise AssertionError(url)
sv14 = (H.http, time.time, H.tg); H.http, H.tg = http14, (lambda m, **p: {"message_id": 1})
H.E.update(IG_TOKEN="pt", IG_USER_ID="178"); time.time = lambda: TK("2026-10-17 22:40"); os.makedirs("docs/cards", exist_ok=True)
open("docs/cards/2026-10-17.jpg", "wb").write(b"J"); open(H.REPOST, "w").write("2026-10-17"); os.makedirs("docs/cards/re", exist_ok=True); open("docs/cards/re/2026-10-17.png", "wb").write(b"P")  # 다시 올리기 카드는 이미 그려 둠(켜져 있으면 바로 컨테이너)
s14 = {"igc_111": {"t": TK("2026-10-17 21:10"), "card": "2026-10-17"}, "igc_222": TK("2026-10-17 22:10"), "igk_2026-10-17_18": {"t": TK("2026-10-17 18:05"), "kids": ["k1", "k2"]},
       "reel_2026-10-17": {"t": 1, "cap": "릴스"}, "igpub_20261017": {"t": 1, "n": 0}}
H.IG_AUTO = True; H.ig_publish(dict(s14)); assert any("graph.instagram.com" in u for u in c14); c14.clear()  # 켜면 그대로 부름(아래 '0번'이 꺼짐 덕분인지 확인)
H.IG_AUTO = False
for f14 in (H.ig_cards, H.ig_reel, H.ig_repost, H.ig_publish):
    f14(s14)
assert not [u for u in c14 if "graph.instagram.com" in u or "graph.facebook.com" in u] and not any(k.startswith(("igc_", "igk_")) for k in s14)  # 인스타 API 0번 · 남은 컨테이너 발행 없이 지움
assert "igr_2026-10-17" not in s14 and "igre_2026-10-17" not in s14 and "igs_2026-10-17" not in s14 and s14["igpub_20261017"]["n"] == 0  # 릴스·다시 올리기·카드 회차 안 건드림
os.remove(H.REPOST)
e14 = urllib.error.HTTPError("https://graph.instagram.com/v25.0/178/media_publish", 403, "x", None, None); e14.body = '{"error":{"message":"Application request limit reached","code":4,"error_subcode":2207051}}'
al14 = []; H.tg = lambda m, **p: al14.append(p.get("text")) or {"message_id": 1}; s14b = {}
H.step_alert(s14b, H.ig_publish, e14); assert "인스타 스팸 의심 차단(토큰 문제 아님)" in al14[0] and "IG_TOKEN 만료" not in al14[0], al14
e14b = urllib.error.HTTPError("https://graph.instagram.com/v25.0/178/media", 400, "x", None, None); e14b.body = '{"error":{"message":"Invalid OAuth access token","code":190}}'
H.step_alert(s14b, H.ig_cards, e14b); assert "IG_TOKEN 만료(60일)" in al14[-1]  # 토큰 오류는 예전 안내 그대로
(H.http, time.time, H.tg) = sv14; del H.E["IG_TOKEN"], H.E["IG_USER_ID"]
e14c = urllib.error.HTTPError("https://api.anthropic.com/v1/messages", 400, "x", None, None); e14c.body = '{"type":"error","error":{"type":"invalid_request_error","message":"Your credit balance is too low to access the Anthropic API."}}'
al14.clear(); H.tg = lambda m, **p: al14.append(p.get("text")) or {"message_id": 1}; H.step_alert({}, lambda s: H.toss_deals(s, True), e14c)
assert H.CREDIT_HINT in al14[0] and "다음 실행(14분 뒤)" not in al14[0]  # 크레딧 바닥 = 충전 안내(10/18 03시 — '다음 실행에 다시'로 읽혀서)
assert 'alert(seen, "alert_credit", "⚠️ 커뮤니티 딜 판단 멈춤 — " + CREDIT_HINT)' in inspect.getsource(H.main) and '"credit balance" in (getattr(e, "body", "") or "")' in inspect.getsource(H.main); H.tg = sv14[2]
# 9-15) 10/18 진우 '나머지 토스 링크는 뽐뿌 말고 바로 연결': ① 쉐어링크 못 찾은 토스 커뮤니티 딜은 뽐뿌 링크로 안 올림(tw_ 보관) -> 실행마다 다시 찾아 찾으면 그때 게시(대가성 문구 맨 앞·게시 시점 가격),
#       2시간 지나도 없으면 진우에게 링크 요청 1번 -> 답장 오면 그 링크로 게시 ② 뽐뿌 버튼으로 남은 옛 글(TOSS_BACKFILL) = 1번 새로 찾아 교체(게시 시점 줄 = 그 글 시각),
#       하루 넘은 글이 지금 15% 넘게 비싸면 특가 끝·못 찾으면 진우에게 요청(답장 = 교체) ③ Claude 오류면 후보를 '본 후보'로 안 넘김(10/18 크레딧 바닥 1204)
sv15 = (H.http, H.ai_pick, H.tg, time.time, H.HAS_TOSS, H.fetch_deals, H.EVENTS, H.TOSS_NO_CMP)
H.E.update(TOSS_ACCESS_KEY="ak", TOSS_SECRET_KEY="sk", TOSS_PUBLISHER_ID="pub-1"); H.HAS_TOSS = H.TOSS_NO_CMP = True
json.dump({"token": "TK", "exp": 9e9}, open(H.TOSS_TOKEN, "w")); H.EVENTS = "ev15.json"; json.dump([], open(H.EVENTS, "w"))
L15, s15, U15 = [(501, "CJ 비비고 왕교자 1.05kg 2개", 15900)], [], []
def http15(url, body=None, headers=None, method=None):
    ok = lambda x: json.dumps({"resultType": "SUCCESS", "success": x})
    if url.endswith("/links"): return ok({"shortUrl": f"https://toss.shopping/_m/W{body['tacaItemId']}"})
    if url.endswith("/categories"): return ok({"categories": []})
    if "today-deals" in url: return ok({"items": []})
    if "best-selling" in url: return ok({"items": [{"tacaItemId": i, "displayName": n, "displayPrice": p} for i, n, p in L15]})
    raise OSError("down")  # 그 밖(뽐뿌·RSS·Threads 등) = 막힘
def tg15(method, **p):
    if method == "getUpdates": return [] if "offset" in p else U15
    s15.append((method, p)); return {"message_id": 700 + len(s15), "text": p.get("text", ""), "entities": p.get("entities", [])}
def pick15(prompt, lines):
    if prompt.startswith("커뮤니티 핫딜 글 제목"):  # MATCH_PROMPT
        return [{"i": 0, "score": 9 if "비비고" in lines[0] else 5, "comment": "같은 상품"}]
    return [{"i": i, "score": 8, "comment": "싸요"} for i, l in enumerate(lines) if "[토스]" in l]
pp15 = "https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&no="
H.fetch_deals = lambda: [{"id": f"ppomppu_{n}", "board": "뽐뿌", "title": t, "hits": "", "age": 40, "desc": "", "url": pp15 + str(n)}
                         for n, t in ((915, "[토스] 비비고 왕교자 1.05kg 2봉 (13,900원/무료)"), (916, "[토스] 없는 상품 김치 10kg (19,900원/무료)"))]
json.dump({}, open("seen.json", "w")); json.dump([], open("posts.json", "w"))
H.http, H.ai_pick, H.tg = http15, pick15, tg15; time.time = lambda: TK("2026-10-18 14:00")
H.main(); H.main()  # 1번째: 비비고 -> 보관 -> 같은 실행 toss_wait가 찾아 게시 / 2번째: 넘쳐 보관된 김치 -> 못 찾음 -> 기다림
chm = [p for m, p in s15 if m == "sendMessage" and p["chat_id"] == "@ch" and "💙 토스 특가" in p["text"]]  # 10/22 토스 몰별 틀
assert len(chm) == 1 and chm[0]["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://toss.shopping/_m/W501", [p["text"][:60] for p in chm]
assert chm[0]["text"].startswith(f"<i>{H.TOSS_NOTE}</i>") and "⚠️ 10/18 14:00 게시 시점 가격" in chm[0]["text"] and "비비고" in chm[0]["text"]  # 대가성 문구 맨 앞 + 게시 시점 가격
assert not [p for m, p in s15 if pp15 in json.dumps(p.get("reply_markup", {}))]  # 뽐뿌 링크 버튼으로 올라간 글 0
sj15 = json.load(open("seen.json")); assert "tw_ppomppu_915" not in sj15 and "tw_ppomppu_916" in sj15 and not sj15["tw_ppomppu_916"].get("ask") and "tb_501" in sj15
assert json.load(open("posts.json"))[-1]["url"] == "https://toss.shopping/_m/W501"
s15.clear(); time.time = lambda: TK("2026-10-18 15:59"); H.toss_wait(sj15); assert not s15  # 2시간 안 = 조용히 다시 찾기만
time.time = lambda: TK("2026-10-18 16:01"); H.toss_wait(sj15)
assert len(s15) == 1 and s15[0][1]["chat_id"] == "42" and "토스 링크 필요 — [토스] 없는 상품 김치 10kg" in s15[0][1]["text"] and pp15 + "916" in s15[0][1]["text"]
ask15 = sj15["tw_ppomppu_916"]["ask"]; assert ask15 == 701; H.toss_wait(sj15); assert len(s15) == 1  # 1번만 물음
s15.clear(); U15[:] = [{"update_id": 1, "message": {"message_id": 900, "from": {"id": 42}, "chat": {"id": 42}, "text": "https://toss.shopping/_m/JW1",
                                                   "reply_to_message": {"message_id": ask15, "chat": {"id": 42}, "text": s15 and "" or "🔗 토스 링크 필요"}}}]
H.publish_approved(sj15)
chm = [p for m, p in s15 if m == "sendMessage" and p["chat_id"] == "@ch"]
assert len(chm) == 1 and chm[0]["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://toss.shopping/_m/JW1" and chm[0]["text"].startswith(f"<i>{H.TOSS_NOTE}</i>")
assert "⚠️ 10/18 16:01 게시 시점 가격" in chm[0]["text"] and "김치" in chm[0]["text"] and "tw_ppomppu_916" not in sj15 and "올렸어" in s15[-1][1]["text"]  # 진우 링크 = 그때 게시
# ② 옛 글 백필
u16 = lambda s, e: s.encode("utf-16-le")[2 * e["offset"]:2 * (e["offset"] + e["length"])].decode("utf-16-le")
t59 = "🔥 [토스] 비비고 왕교자 1.05kg 2봉 (14,900원/무료)\n\n코멘트\n\n출처: 뽐뿌"
P15 = [{"t": "2026-10-07 20:15", "text": t59, "entities": [{"type": "bold", "offset": 3, "length": 4}, {"type": "text_link", "offset": len(t59.encode("utf-16-le")) // 2 - 2, "length": 2, "url": pp15 + "59"}], "url": pp15 + "59", "mid": 59, "cp": 159},
       {"t": "2026-10-08 10:00", "text": "🔥 [토스] 비비고 왕교자 1.05kg 2봉 (9,900원)\n\n출처: 뽐뿌", "url": pp15 + "88", "mid": 88},
       {"t": "2026-10-09 10:00", "text": "🔥 [토스] 아무도 모르는 상품 (1,000원)\n\n출처: 뽐뿌", "url": pp15 + "97", "mid": 97},
       {"t": "2026-10-07 21:00", "text": "🔥 [토스] 비비고 왕교자 1.05kg 2봉 (14,900원)", "url": pp15 + "60", "mid": 60},  # 목록에 없는 옛 글 = 그대로
       {"t": "2026-10-18 01:17", "text": "🔥 [토스] 비비고 왕교자 1.05kg 2봉 (13,900원)\n⚠️ 10/18 01:17 게시 시점 가격\n\n출처: 뽐뿌", "url": pp15 + "1204", "mid": 1204, "cp": 1300}]
json.dump(P15, open("posts.json", "w"), ensure_ascii=False)
s15.clear(); sb15 = {"tr_1204": {"t": TK("2026-10-18 01:20"), "ids": [501], "src": 1}}  # 크레딧 바닥 때 Claude 없이 '본 후보'가 된 1204
time.time = lambda: TK("2026-10-18 16:30"); out15 = io.StringIO()
with contextlib.redirect_stdout(out15): H.toss_relink(sb15)
log15, pj15 = out15.getvalue(), {p["mid"]: p for p in json.load(open("posts.json"))}
ed = {p["message_id"]: p for m, p in s15 if m == "editMessageText" and p["chat_id"] == "@ch"}
assert sorted(ed) == [59, 1204] and all(ed[k]["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://toss.shopping/_m/W501" for k in ed), log15
t = ed[59]["text"]; assert t.startswith(H.TOSS_NOTE) and "\n⚠️ 10/7 20:15 게시 시점 가격\n\n출처: 뽐뿌" in t and t.count("게시 시점 가격") == 1
assert [u16(t, e) for e in ed[59]["entities"]] == [H.TOSS_NOTE, "[토스]", "뽐뿌"]  # 문구·게시 시점 줄만큼 오프셋 밂(UTF-16)
assert ed[1204]["text"].count("게시 시점 가격") == 1 and "10/18 01:17 게시 시점 가격" in ed[1204]["text"]  # 이미 있으면 그대로
assert pj15[59]["url"] == pj15[1204]["url"] == "https://toss.shopping/_m/W501" and pj15[59]["text"] == t and pj15[60]["url"] == pp15 + "60"
assert "(9,900원) -> CJ 비비고 왕교자 1.05kg 2개 15,900원 (id 501, 9점) | 특가 끝" in log15, log15  # 하루 넘은 글 + 지금 15% 넘게 비쌈 = 연결 X
asks = {p["text"].split(" — ")[1].split("\n")[0]: p for m, p in s15 if m == "sendMessage" and p["chat_id"] == "42"}
assert sorted(asks) == ["[토스] 비비고 왕교자 1.05kg 2봉 (9,900원)", "[토스] 아무도 모르는 상품 (1,000원)"] and asks["[토스] 아무도 모르는 상품 (1,000원)"]["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://t.me/ch/97"
assert pj15[97]["ask"] == 1 and pj15[97]["cp"] and pj15[88]["ask"] == 1 and "ask" not in pj15[59] and "toss ask [88, 97]" in log15
s15.clear(); H.toss_relink(sb15); assert not s15  # 1번만 물음
amsg = asks["[토스] 아무도 모르는 상품 (1,000원)"]
s15.clear(); U15[:] = [{"update_id": 2, "message": {"message_id": 901, "from": {"id": 42}, "chat": {"id": 42}, "text": "https://toss.shopping/_m/JW97",
                                                   "reply_to_message": {"message_id": pj15[97]["cp"], "chat": {"id": 42}, "text": amsg["text"], "reply_markup": amsg["reply_markup"]}}}]
H.publish_approved(sb15)
ed = {p["message_id"]: p for m, p in s15 if m == "editMessageText" and p["chat_id"] == "@ch"}
assert list(ed) == [97] and ed[97]["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://toss.shopping/_m/JW97" and ed[97]["text"].startswith(H.TOSS_NOTE) and "⚠️ 10/9 10:00 게시 시점 가격" in ed[97]["text"]
assert json.load(open("posts.json"))[2]["url"] == "https://toss.shopping/_m/JW97"  # 답장 = 그 글 교체(사본 답장과 같은 길)
r15 = {}; H.ai_pick = lambda p, l: (_ for _ in ()).throw(RuntimeError("credit balance"))
try:
    H.toss_match({}, r15, "[토스] 비비고 왕교자 1.05kg 2봉 (13,900원)", pp15 + "1", [[501, "CJ 비비고 왕교자 1.05kg 2개", 15900, 0]]); raise AssertionError
except RuntimeError:
    assert r15["ids"] == []  # Claude가 답 못 하면 후보를 넘기지 않음 -> 다음 실행에 다시 물음
(H.http, H.ai_pick, H.tg, time.time, H.HAS_TOSS, H.fetch_deals, H.EVENTS, H.TOSS_NO_CMP) = sv15; os.remove(H.TOSS_TOKEN); json.dump([], open("posts.json", "w")); U15.clear()
# 9-16) 10/18 13시 '[토스쇼핑]도 토스': 제목 판정 공용(TOSS_TAG) -> 보류 흐름(쉐어링크 없으면 뽐뿌로 안 올림 → 2시간 뒤 진우 요청 → 답장 링크로 게시)·다른 몰 비교 X·게시 시점 줄·대가성 문구 맨 앞,
#       posts.json 정리(toss_clean_posts)·Threads 비교 목록(cmp_report)도 같은 규칙
assert H.is_toss("", "🔥 [토스쇼핑] 삼겹살 (1원)") and H.is_toss("", "[광고] 🔥 삼겹살\n🔥 [토스쇼핑]삼겹살 (1원)") and H.is_toss("", "🔥 [토스] 삼겹살") and not H.is_toss("", "🔥 [G마켓] 토스쇼핑 아님")
sv16 = (H.http, H.ai_pick, H.tg, time.time, H.HAS_TOSS, H.fetch_deals, H.EVENTS, H.TOSS_NO_CMP)
H.HAS_TOSS = H.TOSS_NO_CMP = True; json.dump({"token": "TK", "exp": 9e9}, open(H.TOSS_TOKEN, "w")); H.EVENTS = "ev16.json"; json.dump([], open(H.EVENTS, "w"))
L15[:] = [(601, "전혀 다른 상품", 1000)]; s15.clear(); U15.clear()
pick16 = lambda prompt, lines: [{"i": i, "score": 8, "comment": "쿠팡 같은 상품보다 2,000원 싸요\n순대국 3팩이에요"} for i, l in enumerate(lines) if "[토스쇼핑]" in l] if not prompt.startswith("커뮤니티 핫딜 글 제목") else []
H.fetch_deals = lambda: [{"id": "ppomppu_984", "board": "뽐뿌", "title": "[토스쇼핑] 토종순대 얼큰술국 1KG x 3팩 (18,840원/무배)", "hits": "", "age": 40, "desc": "", "url": pp15 + "984"}]
json.dump({}, open("seen.json", "w")); json.dump([], open("posts.json", "w"))
H.http, H.ai_pick, H.tg = http15, pick16, tg15; time.time = lambda: TK("2026-10-18 13:00")
H.main()
assert not [p for m, p in s15 if p.get("chat_id") == "@ch" and "토종순대" in str(p.get("text"))] and not [p for m, p in s15 if pp15 in json.dumps(p.get("reply_markup", {}))]  # 뽐뿌 버튼으로 안 올림
sj16 = json.load(open("seen.json")); assert "tw_ppomppu_984" in sj16 and not sj16["tw_ppomppu_984"].get("ask")  # 보류
s15.clear(); time.time = lambda: TK("2026-10-18 15:01"); H.toss_wait(sj16)
assert len(s15) == 1 and "토스 링크 필요 — [토스쇼핑] 토종순대" in s15[0][1]["text"] and sj16["tw_ppomppu_984"]["ask"]  # 2시간 뒤 진우에게
U15[:] = [{"update_id": 3, "message": {"message_id": 902, "from": {"id": 42}, "chat": {"id": 42}, "text": "https://toss.shopping/_m/SD1",
                                       "reply_to_message": {"message_id": sj16["tw_ppomppu_984"]["ask"], "chat": {"id": 42}, "text": "🔗"}}}]
s15.clear(); H.publish_approved(sj16); U15.clear()
ch16 = [p for m, p in s15 if m == "sendMessage" and p["chat_id"] == "@ch"]
assert len(ch16) == 1 and ch16[0]["text"].startswith(f"<i>{H.TOSS_NOTE}</i>") and "⚠️ 10/18 15:01 게시 시점 가격" in ch16[0]["text"] and "쿠팡" not in ch16[0]["text"] and "순대국 3팩이에요" in ch16[0]["text"]
assert ch16[0]["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://toss.shopping/_m/SD1"  # 대가성 문구 맨 앞 · 게시 시점 줄 · 다른 몰 비교 줄 없음
H.HAS_TOSS = False; t16 = H.deal_post({"title": "[토스쇼핑] 토종순대 3팩 (18,840원)", "url": pp15 + "985", "board": "뽐뿌"}, "쿠팡보다 2,000원 싸요\n맛있어요")[0]
assert "게시 시점 가격" in t16 and "쿠팡" not in t16 and "맛있어요" in t16; H.HAS_TOSS = True  # 토스 API 없을 때(제목만)도 같은 규칙
json.dump([{"t": "2026-10-08 21:36", "text": "🔥 [토스쇼핑]광동제약 비타500 40병(15,700원)\n\n💸 쿠팡 같은 상품보다 3,000원 쌈\n맛있어요", "entities": [], "url": pp15 + "102", "mid": 102}], open("posts.json", "w"), ensure_ascii=False)
H.toss_clean_posts(); assert json.load(open("posts.json"))[0]["text"] == "🔥 [토스쇼핑]광동제약 비타500 40병(15,700원)\n\n맛있어요"  # 사이트·카드·Threads 재료도 비교 X
H.E["THREADS_TOKEN"] = "tk"; TH16 = [{"id": "5", "timestamp": "2026-10-18T03:00:00+0000", "permalink": "https://threads.net/p/5", "text": "💸 쿠팡보다 2,000원 싸요\n🔥 [토스쇼핑] 토종순대 (18,840원)\n\n👉 https://hotdealpick.kr/p/0.html"}]
H.http = lambda url, *a, **k: json.dumps({"id": "777"}) if "/me?" in url else json.dumps({"data": TH16})
with contextlib.redirect_stdout(io.StringIO()) as o16: H.cmp_report({})
assert "cmp th 10-18 12:00 | " in o16.getvalue() and "[토스쇼핑] 토종순대" in o16.getvalue(), o16.getvalue()  # 토스 문구·링크 없는 [토스쇼핑] Threads 글도 목록에
del H.E["THREADS_TOKEN"]; (H.http, H.ai_pick, H.tg, time.time, H.HAS_TOSS, H.fetch_deals, H.EVENTS, H.TOSS_NO_CMP) = sv16; os.remove(H.TOSS_TOKEN); json.dump([], open("posts.json", "w"))
# 9-17) 10/18 18:30 진우 'Threads 개별 딜 글 링크 위치 A/B — 절반만 시험'(10/25 비교): 개별 딜 글(th_deal로 나가는 것 전부)이 A(본문 👉 링크 + 미리보기)·B(본문 주소 없이 + 첫 댓글 링크) 번갈아,
#       대가성 문구는 A·B 모두 본문 첫 줄(공정위 — 댓글 X), 토스 B 글도 게시 시점 가격 줄, 댓글 권한 없으면 A, 댓글 실패 = 알림 + 다음 실행 1번 더, metrics.json 줄에 ab·rv·48시간 v48·rv48
assert lab0 is True  # 기본 켜짐(예전 셀프체크만 A로 돌림)
sv17 = (H.http, H.tg, time.time, H.time.sleep, H.TOSS_NO_CMP, H.TH_LINK_AB); H.time.sleep = lambda s: None; H.TOSS_NO_CMP = H.TH_LINK_AB = True
U = H.TH_AB_URL
tA = H.th_note(H.TOSS_NOTE) + "🔥 [토스] 비비고 왕교자 (13,900원)\n\n맛있어요\n⚠️ 10/18 19:00 게시 시점 가격\n\n👉 " + H.SITE + "p/5.html?ref=th\n" + H.th_follow(True) + "\n📲 실시간 알림 t.me/hotdeal_pick"
bB, rB = H.th_ab(tA, H.SITE + "p/5.html?ref=th")
assert not re.search(r"http|t\.me|\.kr", bB) and bB.startswith(H.TOSS_NOTE + "\n\n🔥 [토스] 비비고") and bB.endswith("\n\n" + H.TH_AB_MARK) and "⚠️ 10/18 19:00 게시 시점 가격" in bB and H.th_follow(True) in bB
assert rB == f"{H.TOSS_NOTE}\n\n👉 {H.SITE}p/5.html?ref=thc\n📲 실시간 알림 t.me/hotdeal_pick"  # 첫 댓글 = 대가성 문구 + 링크(사이트 ?ref=thc) + 📲
tT = H.toss_th("", "에브리워터 무라벨 500ml 20개", "4,445원", ["👉 병당 약 222원"], "https://toss.shopping/_m/W1")
bT, rT = H.th_ab(tT, "https://toss.shopping/_m/W1")
assert not re.search(r"http|t\.me|\.kr", bT) and "게시 시점 가격" in bT and "👉 병당 약 222원" in bT and bT.startswith(H.TOSS_NOTE) and rT.endswith("👉 https://toss.shopping/_m/W1\n📲 실시간 알림 t.me/hotdeal_pick")  # 링크 없는 👉 코멘트 줄은 그대로
c17, al17, n17, fail17, v17 = [], [], [0], [False], {}
def http17(url, body=None, headers=None, method=None):
    if "/me?fields=id" in url: return json.dumps({"id": "777"})
    if "/777/threads?" in url and method == "POST":
        q = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}; c17.append(q)
        if "reply_to_id" in q and fail17[0]: raise OSError("reply down")
        return json.dumps({"id": "c%d" % len(c17)})
    if "/threads_publish?" in url:
        n17[0] += 1; return json.dumps({"id": "p%d" % n17[0]})
    if "/insights?" in url:
        i = url.split(H.THREADS + "/")[1].split("/")[0]; return json.dumps({"data": [{"name": "views", "values": [{"value": v17.get(i, 0)}]}, {"name": "likes", "values": [{"value": 1}]}]})
    raise AssertionError(url)
H.http, H.tg = http17, (lambda m, **p: al17.append(p.get("text")) or {"message_id": 1}); now17 = TK("2026-10-18 19:00"); time.time = lambda: now17
s17 = {"threply": {"t": now17, "ok": 1}}
ids17 = [H.th_deal(s17, "tk", "777", tA, H.SITE + "p/5.html?ref=th") for _ in range(4)]
posts17 = [q for q in c17 if "reply_to_id" not in q]; reps17 = [q for q in c17 if "reply_to_id" in q]
assert ["link_attachment" in q for q in posts17] == [True, False, True, False] and [s17["thab"]["m"][i]["ab"] for i in ids17] == ["A", "B", "A", "B"]  # 번갈아
assert posts17[0]["text"] == tA and posts17[1]["text"] == bB and all(q["text"].startswith(H.TOSS_NOTE) for q in posts17)  # A·B 둘 다 첫 줄 대가성 문구
assert [q["reply_to_id"] for q in reps17] == [ids17[1], ids17[3]] and reps17[0]["text"] == rB and "topic_tag" not in reps17[0]  # B만 바로 첫 댓글(링크)
assert s17["thab"]["m"][ids17[1]]["r"] and "r" not in s17["thab"]["m"][ids17[0]]
c17.clear(); s17b = {"threply": {"t": now17, "ok": 0}, "thab": {"t": now17, "last": "A", "m": {}}}; H.th_deal(s17b, "tk", "777", tA, "https://x")
assert "link_attachment" in c17[0] and len(c17) == 1 and s17b["thab"]["last"] == "A"  # 댓글 권한 없음 = A
c17.clear(); H.TH_LINK_AB = False; s17c = {"threply": {"t": now17, "ok": 1}, "thab": {"t": now17, "last": "A", "m": {}}}; H.th_deal(s17c, "tk", "777", tA, "https://x"); H.TH_LINK_AB = True
assert "link_attachment" in c17[0] and len(c17) == 1  # 상수 끄면 A만
c17.clear(); fail17[0] = True; s17d = {"threply": {"t": now17, "ok": 1}, "thab": {"t": now17, "last": "A", "m": {}}}; pd = H.th_deal(s17d, "tk", "777", tA, H.SITE + "p/5.html?ref=th")
assert "링크 댓글 실패" in al17[-1] and "?ref=thc" in al17[-1] and s17d[f"thabq_{pd}"]["text"] == rB  # 댓글 실패 -> 알림 + 다음 실행에 1번 더
c17.clear(); H.th_retry(s17d); assert [q["reply_to_id"] for q in c17] == [pd] and "2번째도 실패" in al17[-1] and not any(k.startswith("thabq_") for k in s17d)
c17.clear(); H.th_retry(s17d); assert not c17  # 3번째는 안 함
fail17[0] = False; s17d[f"thabq_{pd}"] = {"t": now17, "id": pd, "text": rB}; c17.clear(); H.th_retry(s17d)
assert [q["reply_to_id"] for q in c17] == [pd] and s17d["thab"]["m"][pd]["r"] and not any(k.startswith("thabq_") for k in s17d)  # 다시 달리면 댓글 id 기록
v17.update({ids17[0]: 40, ids17[1]: 55, s17["thab"]["m"][ids17[1]]["r"]: 9})
json.dump({}, open(H.METRICS, "w")); H.E.update(THREADS_TOKEN="tk", METRICS_DAY="2026-10-18"); ph17 = H.http
H.http = lambda url, *a, **k: json.dumps({"data": [{"id": i, "text": t, "timestamp": "2026-10-18T10:00:00+0000"} for i, t in ((ids17[0], tA), (ids17[1], bB))]}) if "/me/threads?" in url else ph17(url, *a, **k)
H.metrics(s17); m17 = {r["id"]: r for r in json.load(open(H.METRICS))["2026-10-18"]["rows"] if r["ch"] == "th"}
assert m17[ids17[0]]["ab"] == "A" and "rv" not in m17[ids17[0]] and m17[ids17[1]]["ab"] == "B" and m17[ids17[1]]["rv"] == 9 and m17[ids17[1]]["views"] == 55, m17  # 줄마다 A/B, B는 링크 댓글 조회
H.http = ph17; del H.E["METRICS_DAY"]; v17.update({ids17[0]: 140, ids17[1]: 150, s17["thab"]["m"][ids17[1]]["r"]: 30}); time.time = lambda: now17 + 49 * 3600  # 다음 날 metrics 실행(그날 모으기는 따로)
H.metrics(s17); m17 = {r["id"]: r for r in json.load(open(H.METRICS))["2026-10-18"]["rows"] if r["ch"] == "th"}
assert (m17[ids17[0]]["v48"], m17[ids17[1]]["v48"], m17[ids17[1]]["rv48"]) == (140, 150, 30) and "rv48" not in m17[ids17[0]]  # 48시간 조회(B는 링크 댓글도)
c17.clear(); H.http = lambda *a, **k: (_ for _ in ()).throw(AssertionError("다시 묻지 않음")); H.th_ab_48(s17)  # 1번만
c17.clear(); H.http = http17; s17t = {"threply": {"t": now17, "ok": 1}, "thab": {"t": now17, "last": "A", "m": {}}}; pt = H.th_deal(s17t, "tk", "777", tT, "https://toss.shopping/_m/W1")  # 토스 픽 B(제목에 [토스] 없음)
H.E["METRICS_DAY"] = "2026-10-20"; H.http = lambda url, *a, **k: json.dumps({"data": [{"id": pt, "text": bT, "timestamp": "2026-10-20T10:00:00+0000"}]}) if "/me/threads?" in url else http17(url, *a, **k)
H.metrics(s17t); r17 = [r for r in json.load(open(H.METRICS))["2026-10-20"]["rows"] if r["ch"] == "th"]; del H.E["METRICS_DAY"]
assert r17[0]["ab"] == "B" and r17[0]["shop"] == "toss", r17  # B 본문엔 주소가 없어도 올린 링크로 몰(10/19 점검: B 줄 몰이 '기타'로 찍히던 것)
assert all(src.count("th_deal(seen, tok, me,") == 1 for src in map(inspect.getsource, (H.toss_picks, H.toss_reopen))) and inspect.getsource(H.threads_deals).count("th_deal(seen, tok, me,") == 2 \
    and "th_deal(seen, tok, me, text, link)" in inspect.getsource(H.toss_deals) and "th_text(" not in inspect.getsource(H.threads_deals)  # 개별 딜 글 5곳 전부 A/B, 묶음(th_post)은 그대로
del H.E["THREADS_TOKEN"]; (H.http, H.tg, time.time, H.time.sleep, H.TOSS_NO_CMP, H.TH_LINK_AB) = sv17
# 9-18) 10/19 17시 진우 '경유 링크 말고 직접 링크로': ① Threads 딜 링크 = 텔레그램 버튼과 같은 링크(개별 A·B 첫 댓글·리스트·간식/날씨 — 아직 검색 링크인 딜은 검색 링크 그대로,
#       500자에 못 들어가는 TH_LINK_MAX 넘는 링크만 사이트 딜 페이지), 500자 안(링크가 길면 코멘트를 줄임), metrics.json Threads 줄 = 링크 종류(lk: direct·search·site)
#       ② 네이버 매칭은 10/19 밤 취소(쇼핑 검색 API 2026-07-31 종료) -> [네이버] 딜 = 검색 링크 그대로 + 진우 naver.me 답장(관리자 사본 흐름)
#       (10/19 밤 진우 'Threads는 수수료 딜만' 뒤: 검색 링크 딜은 Threads X — 직접 링크·A/B는 수수료 링크 딜로 봄, 9-19)
sv18 = (H.http, H.tg, time.time, H.time.sleep, H.TH_LINK_AB, H.ai_pick, H.POSTS, H.th_solo, {k: H.E.get(k) for k in ("THREADS_TOKEN",)})
H.time.sleep, H.POSTS, H.TH_LINK_AB, H.th_solo = (lambda s: None), "posts18.json", True, (lambda *a, **k: True)
assert [H.link_kind(u) for u in ("https://link.coupang.com/a/x", "https://naver.me/A", "https://smartstore.naver.com/main/products/1", "https://search.shopping.naver.com/catalog/123",
        "https://search.shopping.naver.com/search/all?query=a", "https://www.coupang.com/np/search?q=a", H.SITE + "p/1.html?ref=th", H.lp_link("gmarket", "https://www.gmarket.co.kr/n/search?keyword=a"),
        H.lp_link("gmarket", "https://item.gmarket.co.kr/Item?goodscode=1"), "")] == ["direct", "direct", "direct", "direct", "search", "search", "site", "search", "direct", "direct"]
assert m17[ids17[0]]["lk"] == "site" and r17[0]["lk"] == "direct"  # metrics.json Threads 줄 = 링크 종류(10/25: 바뀐 뒤 글끼리 비교)
SR18 = "https://search.shopping.naver.com/search/all?query=" + "%EC%84%9C%EC%9A%B8%EC%9A%B0%EC%9C%A0%20%EB%94%B8%EA%B8%B0" * 3  # 아직 검색 링크인 [네이버] 딜(~220자)
P18 = [{"t": kt(0), "text": "🔥 [네이버] 서울우유 딸기우유 200ml 24팩 (13,900원/무료)\n\n" + "딸기우유 24팩이 13,900원, 무료배송이에요. " * 12 + "\n💡 단위가격 개당 579원\n\n출처: 뽐뿌", "url": SR18, "mid": 1297, "own": 1, "s": 7},
       {"t": kt(0), "text": f"{H.DISCLOSURE}\n\n🔥 [쿠팡] 휴지 30롤 (19,900원/무료)\n\n싸요\n\n출처: 뽐뿌", "url": "https://link.coupang.com/a/Z18", "mid": 1298, "own": 1, "s": 6}]
c18, now18 = [], time.time()
def http18(url, body=None, headers=None, method=None):
    if method == "HEAD": raise AssertionError("직접 링크는 사이트 확인 X: " + url)
    if "/me?fields=id" in url: return json.dumps({"id": "777"})
    if "/777/threads?" in url: c18.append({k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}); return json.dumps({"id": "c%d" % len(c18)})
    if "/threads_publish?" in url: return json.dumps({"id": "p%d" % len(c18)})
    raise AssertionError(url)
H.http, H.E["THREADS_TOKEN"], s18 = http18, "tk", {"threply": {"t": now18, "ok": 1}}
json.dump(P18[:1], open(H.POSTS, "w"), ensure_ascii=False); out18 = io.StringIO()
with contextlib.redirect_stdout(out18): H.threads_deals(s18)  # 10/19 밤 진우 'Threads는 수수료 딜만': 아직 검색 링크인 [네이버] 딜 = Threads X(텔레그램·사이트는 그대로)
assert c18 == [] and re.search(r"^threads skip \(수수료 링크 아님\) \[네이버\] 서울우유 딸기우유.* \| search$", out18.getvalue(), re.M) and json.load(open(H.POSTS))[0]["th"] == 0 and "thab" not in s18
LPD18 = H.lp_link("gmarket", "https://item.gmarket.co.kr/Item?goodscode=" + "1234567890" * 6)  # 300자 안 링크프라이스 상품 링크(수수료 O) = 직접 링크 그대로
assert 200 < len(LPD18) <= H.TH_LINK_MAX and H.aff_note(LPD18) == H.AFF_NOTE
json.dump([{**P18[0], "url": LPD18}], open(H.POSTS, "w"), ensure_ascii=False); H.threads_deals(s18)  # A(직전 없음): 본문 👉 같은 링크 + 미리보기
a18 = c18[0]["text"]
assert c18[0]["link_attachment"] == LPD18 and f"\n\n👉 {LPD18}\n" in a18 and len(a18) <= 480 and "/p/" not in a18 and a18.startswith(H.th_note(H.AFF_NOTE) + "🔥 [네이버] 서울우유 딸기우유") and a18.endswith("📲 실시간 알림 t.me/hotdeal_pick")  # 500자 안: 링크 길면 코멘트를 줄임
assert s18["thab"]["m"]["p1"] == {"ab": "A", "ts": s18["thab"]["m"]["p1"]["ts"], "u": LPD18, "n": H.title_of(a18)} and H.link_kind(LPD18) == "direct" and H.link_kind(SR18) == "search"
json.dump([{**P18[0], "th": 1}, P18[1]], open(H.POSTS, "w"), ensure_ascii=False); c18.clear(); H.threads_deals(s18)  # B: 본문 주소 X, 첫 댓글 = 같은 제휴 링크(?ref=thc X)
b18, r18 = c18[0], c18[1]
assert "link_attachment" not in b18 and not re.search(r"http|/p/", b18["text"]) and b18["text"].startswith(H.th_note(H.DISCLOSURE)) and b18["text"].endswith(H.TH_AB_MARK)
assert r18["reply_to_id"] == "p1" and r18["text"] == f"{H.th_note(H.DISCLOSURE)}👉 https://link.coupang.com/a/Z18\n📲 실시간 알림 t.me/hotdeal_pick" and "ref=thc" not in r18["text"]  # 대가성 문구는 본문·댓글 첫 줄
LP18 = H.lp_link("gmarket", "https://www.gmarket.co.kr/n/search?keyword=" + "%EC%9A%B0%EC%9C%A0" * 40)  # TH_LINK_MAX 넘는 링크프라이스 = 500자에 못 들어감 -> 사이트 딜 페이지(사이트에 올라온 뒤)
assert len(LP18) > H.TH_LINK_MAX and H.th_url({"url": LP18}, 7) == H.SITE + "p/7.html?ref=th" and H.th_url({"url": SR18}, 7) == SR18 and H.th_url({"url": None}, 7) == H.SITE + "p/7.html?ref=th"
# ② [네이버] 딜 = 검색 링크 그대로(10/19 밤 정정: 네이버 쇼핑 검색 API 2026-07-31 종료라 상품 매칭 취소) + 관리자 사본 -> 진우 naver.me 답장으로 교체
D18 = {"title": "[네이버] 서울우유 딸기우유 200ml 24팩 (13,900원/무료)", "url": "https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&no=1297", "board": "뽐뿌"}
H.http = lambda url, *a, **k: (_ for _ in ()).throw(OSError("403")) if "ppomppu" in url else (_ for _ in ()).throw(AssertionError(url))
H.ai_pick = lambda prompt, lines: (_ for _ in ()).throw(AssertionError("[네이버] 딜에 상품 매칭 X"))
SR18n = "https://search.shopping.naver.com/search/all?query=" + quote("서울우유 딸기 200ml 24팩")
with contextlib.redirect_stdout(io.StringIO()):
    t18, l18, lb18 = H.deal_post(D18, "딸기우유 24팩", "서울우유 딸기 200ml 24팩")
assert (l18, lb18) == (SR18n, "🔎 네이버쇼핑에서 찾기") and H.aff_note(l18) == "" and not t18.startswith(("<i>", "[광고]"))
tg18 = []
H.tg = lambda m, **p: tg18.append((m, p)) or ({"message_id": 1297, "text": "🔥 [네이버] 서울우유 딸기우유 200ml 24팩 (13,900원/무료)\n\n딸기우유 24팩", "entities": []} if m == "sendMessage" else {"message_id": 77})
json.dump([], open(H.POSTS, "w"))
with contextlib.redirect_stdout(io.StringIO()):
    H.post_or_draft(D18, "딸기우유 24팩", 7, "서울우유 딸기 200ml 24팩")
ch18 = [p for m, p in tg18 if m == "sendMessage"][0]; cp18 = [p for m, p in tg18 if m == "copyMessage"]
assert ch18["reply_markup"]["inline_keyboard"] == [[{"text": "🔎 네이버쇼핑에서 찾기", "url": SR18n}]] and json.load(open(H.POSTS))[0]["url"] == SR18n
assert len(cp18) == 1 and "쇼핑커넥트" in json.dumps(cp18[0]["reply_markup"], ensure_ascii=False) and H.pending_copy("https://naver.me/Jw18")["cp"] == 77  # 관리자 사본 그대로 -> 진우 naver.me 답장이 교체
(H.http, H.tg, time.time, H.time.sleep, H.TH_LINK_AB, H.ai_pick, H.POSTS, H.th_solo, e18) = sv18
for k, v in e18.items():
    H.E.pop(k, None) if v is None else H.E.update({k: v})
# 9-19) 10/19 밤 진우 'Threads는 수수료 딜만'(3개 안 중 이것만 — A/B·네이버 답장 흐름은 그대로): 판단 = 대가성 문구가 붙는 링크(aff_note)
#       개별 글 = 수수료 링크 딜만(아니면 Threads 건너뜀 + 로그 'threads skip (수수료 링크 아님) 제목 | 링크 종류' 딜마다 1번, 텔레그램·사이트는 그대로 — 9-18 ②)
#       묶음(TOP 9-2b·22시 미리보기·간식) 항목도 수수료 링크만, 0개면 그 회차 Threads 묶음 X · 날씨 글은 그대로 · 진우 naver.me 답장으로 바뀐 딜은 그 뒤에 자연히
sv19 = (H.http, H.tg, time.time, H.time.sleep, H.TH_LINK_AB, H.POSTS, H.th_solo, H.TOSS_NO_CMP, H.E.get("THREADS_TOKEN"))
ev19 = open(H.EVENTS).read() if os.path.exists(H.EVENTS) else None
H.time.sleep, H.POSTS, H.TH_LINK_AB, H.th_solo, H.TOSS_NO_CMP, H.E["THREADS_TOKEN"] = (lambda s: None), "posts19.json", True, (lambda *a, **k: True), True, "tk"
c19 = []
def http19(url, body=None, headers=None, method=None):
    if method == "HEAD": raise AssertionError("직접 링크는 사이트 확인 X: " + url)
    if "/me?fields=id" in url: return json.dumps({"id": "777"})
    if "/777/threads?" in url: c19.append({k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}); return json.dumps({"id": "c%d" % len(c19)})
    if "/threads_publish?" in url: return json.dumps({"id": "p%d" % len(c19)})
    raise AssertionError(url)
H.http, s19 = http19, {"threply": {"t": time.time(), "ok": 1}}
N19 = [("[네이버] 검색 링크 딜 (9,900원)", "https://search.shopping.naver.com/search/all?query=a", "search"), ("[쿠팡] 검색 링크 딜 (9,900원)", "https://www.coupang.com/np/search?q=a", "search"),
       ("[쿠팡] 일반 상품 딜 (9,900원)", "https://www.coupang.com/vp/products/1", "direct"), ("[네이버] 일반 상품 딜 (9,900원)", "https://smartstore.naver.com/main/products/1", "direct")]
json.dump([{"t": kt(0), "text": f"🔥 {t}\n\n💡 쿠팡 같은 상품(12,900원)보다 3,000원 쌈", "url": u, "mid": 1900 + k, "s": 9} for k, (t, u, _) in enumerate(N19)], open(H.POSTS, "w"), ensure_ascii=False)
o19 = io.StringIO()
with contextlib.redirect_stdout(o19): H.threads_deals(s19)
assert c19 == [] and [p["th"] for p in json.load(open(H.POSTS))] == [0, 0, 0, 0] and "· 수수료 링크 아님 4" in o19.getvalue()  # 네이버·쿠팡 검색 링크·일반 상품 링크 = Threads X(①등급 💸 딜이어도)
assert [l for l in o19.getvalue().split("\n") if l.startswith("threads skip")] == [f"threads skip (수수료 링크 아님) {t} | {k}" for t, _, k in N19]  # 딜마다 로그 1줄
o19 = io.StringIO()
with contextlib.redirect_stdout(o19): H.threads_deals(s19)
assert c19 == [] and "threads skip (" not in o19.getvalue()  # 다음 실행엔 로그 다시 X
ps19 = json.load(open(H.POSTS)); ps19[0].update(url="https://naver.me/x19", text=f"{H.NAVER_NOTE}\n\n" + ps19[0]["text"]); json.dump(ps19, open(H.POSTS, "w"), ensure_ascii=False)  # 진우 naver.me 답장 = 링크 교체(p.update(url=…))
H.threads_deals(s19)
assert len(c19) == 1 and c19[0]["link_attachment"] == "https://naver.me/x19" and c19[0]["text"].startswith(H.th_note(H.NAVER_NOTE)) and [bool(p.get("th")) for p in json.load(open(H.POSTS))] == [True, False, False, False]  # 바뀐 딜은 그 뒤에 자연히(따로 흐름 X)
assert "p.update(text=text, entities=ents, url=url)" in inspect.getsource(H.relink_channel)  # 진우 링크 답장 = posts.json url도 교체 -> 위처럼 다음 실행에 후보
C19 = [("[토스] 토스 딜 (9,900원)", "https://toss.shopping/_m/T19"), ("[네이버] 쇼핑커넥트 딜 (9,900원)", "https://naver.me/N19"), ("[쿠팡] 파트너스 딜 (9,900원)", "https://link.coupang.com/a/C19")]
json.dump([{"t": kt(0), "text": f"{H.aff_note(u)}\n\n🔥 {t}\n\n좋음", "url": u, "mid": 1910 + k, "s": 9} for k, (t, u) in enumerate(C19)], open(H.POSTS, "w"), ensure_ascii=False)
c19.clear(); s19 = {"threply": {"t": time.time(), "ok": 1}}
for _ in C19:
    H.threads_deals(s19)
assert [m["ab"] for m in s19["thab"]["m"].values()] == ["A", "B", "A"] and len(c19) == 4 and c19[2]["reply_to_id"] == "p2"  # 토스·naver.me·쿠팡 파트너스 = Threads O, A/B 그대로(B = 본문 + 첫 댓글 링크)
assert c19[0]["link_attachment"] == "https://toss.shopping/_m/T19" and "게시 시점" in c19[0]["text"] and "link_attachment" not in c19[1] and c19[2]["text"].startswith(H.th_note(H.NAVER_NOTE) + "👉 https://naver.me/N19\n") and c19[3]["link_attachment"] == "https://link.coupang.com/a/C19"
assert [x["text"].split("\n")[0] for x in c19] == [H.th_note(n).split("\n")[0] for n in (H.TOSS_NOTE, H.NAVER_NOTE, H.NAVER_NOTE, H.DISCLOSURE)]  # Threads 글·B 댓글 모두 첫 줄 대가성 문구([광고] 켜지면 그 앞)
assert all(t in inspect.getsource(f) for f, t in ((H.toss_th, "th_note(TOSS_NOTE)"), (H.toss_picks, "toss_th("), (H.reopen_text, "th_note(TOSS_NOTE)")))  # 나머지 개별 글(토스 픽·뷰티 채움·이름 예약·재오픈) = 늘 토스 쉐어링크 + 고지문
# TOP 리스트 💄 화장품 칸도 수수료 링크만(10/12 '리스트로 만들어도 좋아' 칸)
D19, tg19 = "2026-10-20", []
H.tg = lambda m, **p: tg19.append((m, p)) or {"message_id": 1919}
json.dump([{"t": f"{D19} 0{k + 5}:00", "text": f"{H.DISCLOSURE}\n\n🔥 [쿠팡] 휴지{k} (9,900원)\n\n좋음", "url": f"https://link.coupang.com/a/T{k}", "mid": 1930 + k, "pop": 9 - k} for k in range(3)]
          + [{"t": f"{D19} 09:00", "text": "🔥 [네이버] 검색 선크림 (9,900원)\n\n좋음", "url": "https://search.shopping.naver.com/search/all?query=sun", "mid": 1940},
             {"t": f"{D19} 09:10", "text": f"{H.NAVER_NOTE}\n\n🔥 [네이버] 커넥트 선크림 (9,900원)\n\n좋음", "url": "https://naver.me/S19", "mid": 1941}], open(H.POSTS, "w"), ensure_ascii=False)
c19.clear(); time.time = lambda: TK(f"{D19} 12:05"); H.top_deals({})
assert len(c19) == 1 and "\n\n💄 화장품\n· 커넥트 선크림 9,900원\n👉 https://naver.me/S19" in c19[0]["text"] and "검색 선크림" not in c19[0]["text"] and "search.shopping" not in c19[0]["text"]
assert c19[0]["text"].startswith(H.DISCLOSURE + "\n" + H.NAVER_NOTE + "\n\n🏆 지금 살 만한 딜 TOP3") and "게시 시점" not in c19[0]["text"]  # 💄 링크도 그 프로그램 대가성 문구 맨 앞(10/19 밤 점검: 리스트 딜 문구만 있던 것)
ps19 = json.load(open(H.POSTS)); ps19[-1].update(url="https://toss.shopping/_m/S19", text=ps19[-1]["text"].replace(H.NAVER_NOTE, H.TOSS_NOTE).replace("[네이버]", "[토스]")); json.dump(ps19, open(H.POSTS, "w"), ensure_ascii=False)
c19.clear(); H.top_deals({})
assert c19[0]["text"].startswith(H.DISCLOSURE + "\n" + H.TOSS_NOTE + "\n\n🏆") and c19[0]["text"].endswith("\n\n⚠️ 10/20 12:05 게시 시점 가격") and len(c19[0]["text"]) <= 480 and "👉 https://toss.shopping/_m/S19" in c19[0]["text"]  # 💄 토스 = 게시 시점 줄
json.dump([{"t": f"{D19} 0{k + 5}:00", "text": f"{H.DISCLOSURE}\n\n🔥 [쿠팡] 휴지{k} (9,900원)\n\n좋음", "url": f"https://link.coupang.com/a/T{k}", "mid": 1930 + k, "pop": 9 - k} for k in range(3)]
          + [{"t": "2026-10-19 20:00", "text": "🔥 [네이버] 어젯밤 원글 (9,900원)\n\n💡 쿠팡 같은 상품(12,900원)보다 3,000원 쌈", "url": "https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&no=20", "mid": 1944, "th": 0},
             {"t": "2026-10-19 20:10", "text": f"{H.NAVER_NOTE}\n\n🔥 [네이버] 어젯밤 커넥트 (9,900원)\n\n💡 쿠팡 같은 상품(12,900원)보다 3,000원 쌈", "url": "https://naver.me/Y19", "mid": 1945}], open(H.POSTS, "w"), ensure_ascii=False)
c19.clear(); tg19.clear(); H.top_deals({})
assert "어젯밤 커넥트" in tg19[-1][1]["text"] and "어젯밤 원글" not in tg19[-1][1]["text"]  # 12시 '누락 없이'(개별 글로 못 나간 ①②) = 수수료 링크 딜만(아닌 딜은 원래 Threads에 안 나감 — 채널 순서 그대로 두려고)
json.dump([{"t": f"{D19} 0{k + 5}:00", "text": f"{H.DISCLOSURE}\n\n🔥 [쿠팡] 휴지{k} (9,900원)\n\n좋음", "url": f"https://link.coupang.com/a/T{k}", "mid": 1930 + k, "pop": 9 - k} for k in range(3)]
          + [{"t": f"{D19} 09:00", "text": "🔥 [토스] 원글 토스 딜 (9,900원)\n\n좋음", "url": "https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&no=19", "mid": 1942, "pop": 99}], open(H.POSTS, "w"), ensure_ascii=False)
c19.clear(); tg19.clear(); H.top_deals({})
assert tg19[-1][1]["text"].endswith("게시 시점 가격") and "원글 토스 딜" in tg19[-1][1]["text"] and len(c19) == 1 and "원글 토스 딜" not in c19[0]["text"] and "게시 시점" not in c19[0]["text"]  # 게시 시점 줄 = Threads에 든 토스 딜 기준(채널은 그대로)
json.dump([{"t": f"{D19} 11:00", "text": "🔥 [네이버] 진우 선크림 (9,900원)\n\n좋음", "url": "https://search.shopping.naver.com/search/all?query=sun", "own": 1, "mid": 1943}], open(H.POSTS, "w"), ensure_ascii=False)
json.dump([], open(H.EVENTS, "w"))  # events.json은 9-19 끝에서 되돌림
assert not H.jw_beauty({}, TK(f"{D19} 12:05"))  # 수수료 링크 아닌 진우 화장품 링크는 Threads에 안 나가니 화장품 자리를 안 막음(토스 뷰티 채움 그대로)
json.dump([{"t": f"{D19} 11:00", "text": "🔥 [네이버] 진우 선크림 (9,900원)\n\n좋음", "url": "https://naver.me/J19", "own": 1, "mid": 1943}], open(H.POSTS, "w"), ensure_ascii=False)
assert H.jw_beauty({}, TK(f"{D19} 12:05"))
json.dump([], open(H.POSTS, "w")); jv19 = {"at": f"{D19} 21:00", "text": "🔥 <b>[쿠팡] 클렌징폼 (9,900원)</b>", "url": "https://www.coupang.com/vp/products/9", "deal": True, "button": "b"}
json.dump([jv19], open(H.EVENTS, "w"), ensure_ascii=False); assert not H.jw_beauty({}, TK(f"{D19} 12:05"))  # 수수료 링크 아닌 진우 화장품 예약도 자리 안 막음
json.dump([dict(jv19, url="https://link.coupang.com/a/J19")], open(H.EVENTS, "w"), ensure_ascii=False); assert H.jw_beauty({}, TK(f"{D19} 12:05"))
# 22시 미리보기: 수수료 링크 예약만 Threads(채널은 그대로), 0개면 Threads X
E19 = [("22:20", "[토스] 토스 예약 (9,900원)", "https://toss.shopping/_m/P1"), ("22:30", "[네이버] 쇼핑커넥트 예약 (8,900원)", "https://naver.me/P2"), ("22:40", "[쿠팡] 일반 상품 예약 (7,900원)", "https://www.coupang.com/vp/products/3")]
json.dump([{"at": f"{D19} {a}", "text": f"🔥 <b>{t}</b>", "url": u, "button": "b", "deal": True} for a, t, u in E19], open(H.EVENTS, "w"), ensure_ascii=False); json.dump([], open(H.POSTS, "w"))
c19.clear(); time.time = lambda: TK(f"{D19} 22:05"); H.preview({"threply": {"t": TK(f"{D19} 21:00"), "ok": 0}})
assert "(10/20 · 3개)" in tg19[-1][1]["text"] and "일반 상품 예약" in tg19[-1][1]["text"] and len(c19) == 1  # 채널 = 3개 그대로
assert c19[0]["text"].startswith(H.TOSS_NOTE + "\n" + H.NAVER_NOTE + "\n\n🌙 오늘 밤 특가 미리보기 (2개)\n\n22:20 🔥 토스 예약") and "일반 상품 예약" not in c19[0]["text"] and "이 포스팅은 쿠팡" not in c19[0]["text"]
json.dump([{"at": f"{D19} {a}", "text": f"🔥 <b>[쿠팡] 일반 {k} (7,900원)</b>", "url": f"https://www.coupang.com/vp/products/{k}", "button": "b", "deal": True} for k, (a, _, _) in enumerate(E19)], open(H.EVENTS, "w"), ensure_ascii=False)
c19.clear(); tg19.clear(); o19 = io.StringIO()
with contextlib.redirect_stdout(o19): H.preview({"threply": {"t": 1, "ok": 0}})
assert len(tg19) == 1 and c19 == [] and "threads skip (수수료 링크 아님) preview 묶음 | 항목 0개\n" in o19.getvalue()  # 수수료 0개 = Threads 미리보기 X, 채널은 그대로
json.dump([{"at": f"{D19} 22:20", "text": "👍 <b>[쿠팡] 꾸준 핸드크림 (25,800원)</b>\n\n한 달 1,000명+ 구매", "url": "https://link.coupang.com/a/PV1", "button": "b", "deal": True},
           {"at": f"{D19} 22:25", "text": "🛒 <b>[쿠팡] 약한 샴푸 (7,900원)</b>\n\n🤔 솔직히 특가로는 약한 제품", "url": "https://link.coupang.com/a/PV2", "button": "b", "deal": True},
           {"at": f"{D19} 22:30", "text": "🔥 <b>[쿠팡] 센 휴지 (9,900원)</b>\n\n30일 최저가", "url": "https://link.coupang.com/a/PV3", "button": "b", "deal": True}], open(H.EVENTS, "w"), ensure_ascii=False)
pth19, H.PREVIEW_TH = H.PREVIEW_TH, 1; c19.clear(); tg19.clear(); H.preview({"threply": {"t": 1, "ok": 0}}); H.PREVIEW_TH = pth19
assert "\n\n22:30 🔥 센 휴지" in c19[0]["text"] and "👍 꾸준" not in c19[0]["text"] and "나머지 2개" in c19[0]["text"], c19  # 9-31 본문 자리 = 🔥 -> 👍 -> 🛒(👍가 먼저 올라와도 🔥 먼저)
# 간식(묶음): 수수료 링크 딜만(사이트 딜 페이지로 가던 제휴 아닌 딜 X), 0개면 Threads X · 날씨 글은 그대로
S19 = [{"n": "빼빼로", "p": "1,000원", "u": "https://link.coupang.com/a/S1", "i": 1, "hot": True}, {"n": "초코파이", "p": "2,000원", "u": None, "i": 2, "hot": True},
       {"n": "칸쵸", "p": "3,000원", "u": "https://naver.me/S3", "i": 3, "hot": True}]
c19.clear(); tg19.clear(); time.time = lambda: TK(f"{D19} 15:35"); H.wx_post({}, "k", "🍪 출출할 때 간식 {n}", S19, "", "snack", lo=2)
assert "<b>🍪 출출할 때 간식 3</b>" in tg19[0][1]["text"] and len(c19) == 1 and c19[0]["text"].startswith(H.DISCLOSURE + "\n" + H.NAVER_NOTE + "\n\n🍪 출출할 때 간식 2\n") and "초코파이" not in c19[0]["text"] and "/p/" not in c19[0]["text"]
c19.clear(); tg19.clear(); H.wx_post({}, "k", "🍪 출출할 때 간식 {n}", [S19[0], S19[1], dict(S19[2], u=None)], "", "snack", lo=2)
assert "<b>🍪 출출할 때 간식 3</b>" in tg19[0][1]["text"] and len(c19) == 1 and c19[0]["text"].startswith(H.DISCLOSURE + "\n\n🍪 출출할 때 간식 1\n\n🔥 빼빼로 1,000원\n👉 https://link.coupang.com/a/S1")  # 1개만 남아도 Threads(0개일 때만 X)
c19.clear(); tg19.clear(); o19 = io.StringIO()
with contextlib.redirect_stdout(o19): H.wx_post({}, "k", "🍪 출출할 때 간식 {n}", [dict(x, u=None) for x in S19], "", "snack", lo=2)
assert len(tg19) == 1 and c19 == [] and "threads skip (수수료 링크 아님) snack 묶음 | 항목 0개\n" in o19.getvalue()
c19.clear(); tg19.clear(); H.wx_post({}, "k", "☁️ 오늘", S19[1:2], "☁️ 오늘\n질문", "wx")
assert len(c19) == 1 and "초코파이" in c19[0]["text"] and c19[0]["link_attachment"] == H.SITE + "p/2.html?ref=th"  # 날씨 글은 그대로(10/19 밤 Cowork '날씨 그대로')
if ev19 is None: os.remove(H.EVENTS)
else: open(H.EVENTS, "w").write(ev19)
os.remove("posts19.json")
(H.http, H.tg, time.time, H.time.sleep, H.TH_LINK_AB, H.POSTS, H.th_solo, H.TOSS_NO_CMP, tk19) = sv19
H.E.pop("THREADS_TOKEN", None) if tk19 is None else H.E.update(THREADS_TOKEN=tk19)
# 9-20) 10/20 저녁 진우 '토스 글 멘트 사고 싶게 — 간단하게, 사고 싶은 맘이 들게, 필요한 사람이 살 수 있게'(시안 3개 OK): 토스 쉐어링크 개별 글(토스 API 개별·토스 픽 채움·뷰티 채움·
#       이름 예약·쉐어링크 커뮤니티 [토스] 딜·진우 토스 링크) 💡 한 줄 -> 💰 단위가격 · 🙋 누가(30자 안, 2개까지) · 👍 언제(40자 안, 한 가지) — 💰 가격 줄이 이미 있으면(하루특가·이름 예약 틀) 단위가격은
#       그 줄 끝에(💰 줄 하나), 금지어(써 본 척·효능·다른 몰·과장·클릭 유도)·너무 긴 줄 = 그 줄만 뺌(글은 나감), Threads 480자 넘으면 👍 -> 🙋 순서로 뺌. 묶음 글·쿠팡·네이버 딜은 그대로
assert all(k in H.BEST_PROMPT and k in H.SPECIAL_PROMPT and k in H.SOLO_PROMPT and k in H.PICK_PROMPT and k in H.DEAL_PROMPT and k in H.ADMIN_PROMPT for k in ("who:", "use:", "30자 안", "40자 안", "먹어보니", "클릭"))
assert "토스 상품(제목 [토스]·[토스쇼핑]이거나 본문에 토스·토스쇼핑 링크)일 때만" in H.DEAL_PROMPT and "토스 링크 글에만" in H.ADMIN_PROMPT and "who" in H.TOSS_WU and "다른 쇼핑몰 이름·비교 없이" in H.TOSS_WU
sv20 = (H.http, H.tg, H.ai_pick, H.EVENTS, time.time, H.HAS_TOSS, H.TOSS_SOLO_HOURS, H.TOSS_GAP_MIN, H.TOSS_NO_CMP, H.E.get("THREADS_TOKEN"))
F20 = [({"tacaItemId": 901, "displayName": "웅진식품 애사비 오리지널, 500ml, 24개", "displayPrice": 12850, "discountRate": 55, "reviewScore": 4.9, "reviewCount": 2303},
        {"unit": "병당 약 535원 (24병)", "who": "새콤한 음료 좋아하는 분 · 사무실 냉장고", "use": "차갑게 해서 식후 한 병"}),
       ({"tacaItemId": 902, "displayName": "맘스럽 라임 주방세제, 4L, 2개", "displayPrice": 9400, "discountRate": 27, "reviewScore": 4.7, "reviewCount": 5057},
        {"unit": "1L당 약 1,175원 (총 8L)", "who": "설거지 많은 집 · 사무실 탕비실", "use": "펌프 통에 덜어 쓰고 나머지는 보관"}),
       ({"tacaItemId": 903, "displayName": "14Brix 초고당도 제주 감귤, 5kg, 1박스", "displayPrice": 10900, "discountRate": 71, "reviewScore": 4.8, "reviewCount": 25},
        {"unit": "kg당 약 2,180원 (배송비 포함)", "who": "귤 박스로 두는 집 · 아이 간식 찾는 분", "use": "눌린 귤 골라내고 서늘한 곳에 펼쳐 두기"})]
cur20, sent20 = [None], []
def http20(url, body=None, headers=None, method=None):
    if url == "https://oauth2.cert.toss.im/token": return json.dumps({"access_token": "TK", "expires_in": 31535999})
    if url.endswith("/links"): return json.dumps({"resultType": "SUCCESS", "success": {"shortUrl": f"https://toss.shopping/_m/F{body['tacaItemId']}"}})
    if "/products/best-selling?" in url: return json.dumps({"resultType": "SUCCESS", "success": {"items": [cur20[0][0]]}})
    raise AssertionError(url)
json.dump([], open("ev20.json", "w"))
H.http, H.HAS_TOSS, H.TOSS_SOLO_HOURS, H.EVENTS, H.TOSS_GAP_MIN, H.TOSS_NO_CMP, H.E["THREADS_TOKEN"] = http20, True, range(8, 24), "ev20.json", 0, True, "tk"
H.tg = lambda m, **p: sent20.append(p) or {"message_id": 2000 + len(sent20)}
ch20, th20 = [], []
for h20, f20 in zip((12, 16, 20), F20):  # 순위 출처 시각(12·16·20 % 4 = 0) — 시안 3개를 토스 API 개별 글로(채널 + Threads 채움 후보, 실제 게시 X)
    cur20[0], s20 = f20, {}
    H.ai_pick = lambda prompt, lines: [{"i": 0, "score": 9, "comment": "사실 한 줄", **cur20[0][1]}]
    time.time = lambda: TK(f"2026-10-21 {h20}:05"); H.toss_solo(s20)
    ch20.append(sent20[-1]["text"]); th20.append(s20["thtoss"]["q"][-1]["text"])
for (x20, p20), c20, t20 in zip(F20, ch20, th20):
    assert c20.split("\n")[0].startswith("<i>" + H.TOSS_NOTE) or c20.split("\n")[1].startswith("<i>" + H.TOSS_NOTE)  # 대가성 문구 맨 앞([광고] 켜지면 그 다음 줄)
    assert f"💙 토스 특가 · 많이 팔린 순위 1위 🔥\n{x20['displayName']}\n{x20['displayPrice']:,}원 ({x20['discountRate']}%↓) · ⭐ {x20['reviewScore']} ({x20['reviewCount']:,})\n🙋 {p20['who']}\n👍 {p20['use']}\n⚠️ 10/21 " in H.html.unescape(re.sub("</?b>", "", c20)) and "💡" not in c20 and "사실 한 줄" not in c20 and "💰" not in c20, c20  # 10/22 몰별 틀: 단위가격 줄 X(시안), 🙋·👍 그대로
    assert t20.startswith(H.th_note(H.TOSS_NOTE) + "💙 토스 특가 · 많이 팔린 순위 1위 🔥\n") and f"\n🙋 {p20['who']}\n👍 {p20['use']}\n⚠️ 10/21 " in t20 and "게시 시점 가격" in t20 and len(t20) <= 480 and t20.endswith("📲 실시간 알림 t.me/hotdeal_pick"), t20
# 금지어·너무 긴 줄 = 그 줄만 뺌(글은 나감)
assert H.wu({"who": "제가 써보니 좋아요", "use": "차갑게 해서 한 병"}) == ["👍 차갑게 해서 한 병"] and H.wu({"who": "🙋 설거지 많은 집", "use": "👍 덜어 쓰기"}) == ["🙋 설거지 많은 집", "👍 덜어 쓰기"]
assert [H.wu({"who": w}) for w in ("다이어트 하는 분", "피부 미백 원하는 분", "쿠팡보다 싸게 사고 싶은 분", "역대급 가격 노리는 분", "클릭해서 확인할 분", "먹어보니 맛있어요", "면역 챙기는 분", "가" * 41)] == [[]] * 8
assert H.wu({"use": "무조건 지금 사세요"}) == [] and H.wu({"use": "마지막 기회예요"}) == [] and H.wu({"use": "다" * 50}) == ["👍 " + "다" * 50] and H.wu({"use": "다" * 51}) == [] and H.wu(None) == []
cur20[0] = (F20[0][0], {"unit": "병당 약 535원 (24병)", "who": "제가 먹어보니 좋아요", "use": "차갑게 해서 식후 한 병"}); s20 = {}; time.time = lambda: TK("2026-10-21 12:05"); H.toss_solo(s20)
assert "(2,303)\n👍 차갑게 해서 식후 한 병\n⚠️" in sent20[-1]["text"] and "🙋" not in sent20[-1]["text"] and "🙋" not in s20["thtoss"]["q"][-1]["text"]  # 🙋만 빠지고 글은 나감
# 리뷰 보강: 생활 문장은 안 걸림(세제가·펌프 눌러·곰팡이 예방·추위 대비·먹어 보세요), 써 본 척 모양(봤·본·마셔)·탈모 등·비교 말은 걸림 · 단위가격도 다른 몰·비교면 버림
assert [H.wu({"who": w}) for w in ("주방세제가 금방 떨어지는 집", "펌프 한 번 눌러 덜어 쓰기", "장마철 곰팡이 예방", "겨울 추위 대비용", "한 번 먹어 보세요")] == [["🙋 " + w] for w in ("주방세제가 금방 떨어지는 집", "펌프 한 번 눌러 덜어 쓰기", "장마철 곰팡이 예방", "겨울 추위 대비용", "한 번 먹어 보세요")]
assert [H.wu({"use": w}) for w in ("먹어봤는데 맛있음", "써 본 사람은 재구매", "마셔 보니 시원", "탈모 고민인 분", "마트보다 싸게 쟁이기", "코스트코 대용량 부담인 집", "눌러 보세요")] == [[]] * 7
assert H.toss_lines({"comment": "x", "who": "탄산 좋아하는 집"}) == ["🙋 탄산 좋아하는 집"] and H.toss_lines({"comment": "롤당 330원"}) == ["👉 롤당 330원"] and H.toss_lines({"comment": "쿠팡보다 쌈"}) == [] and H.toss_lines(None) == []  # 10/22: 🙋·👍 없으면 Claude 한 줄(다른 몰·금지어 X)
assert 'l.startswith("💰") and "<b>" not in l' in inspect.getsource(H.toss_soldout)  # 재오픈 글 = 토스 단독 글의 💰 단위가격 줄(💡 대신)
# Threads 480자 넘으면 👍 -> 🙋 순서로 뺌(머리 줄·가격·대가성 문구·게시 시점·링크는 그대로)
N20 = "아주 긴 상품 이름 " * 6
for a20, keep20 in ((20, ("🙋",)), (27, ())):
    t20 = H.toss_th("하루특가 · 밤 12시까지", N20, "18,900원 · " + "라마바 " * 30, ["👉 " + "가나다 " * a20, "🙋 " + "나" * 28, "👍 " + "다" * 38], "https://toss.shopping/_m/XWQOcF6x")
    assert len(t20) <= 480 and "👍" not in t20 and ("🙋" in t20) == bool(keep20) and "\n18,900원" in t20 and t20.startswith(H.th_note(H.TOSS_NOTE) + "💙 토스 특가 · 하루특가 · 밤 12시까지 🔥\n") and "게시 시점 가격" in t20 and "🛒 https://toss.shopping/_m/XWQOcF6x" in t20, (a20, t20)
# 커뮤니티 [토스] 딜(쉐어링크 버튼)·진우 토스 링크 = 💡 단위가격 아래 🙋·👍 → ⚠️ / 쿠팡·네이버·쉐어링크 아닌 [토스] 딜 = 안 나옴
X20 = {"unit": "개당 413원", "who": "탄산 좋아하는 집 · 캠핑 가는 분", "use": "냉장고에 넣어 두고 손님 오면 한 캔", "warn": "배송비 확인"}
assert H.facts_of(X20, True) == "\n💡 단위가격 개당 413원\n🙋 탄산 좋아하는 집 · 캠핑 가는 분\n👍 냉장고에 넣어 두고 손님 오면 한 캔\n⚠️ 확인할 점 배송비 확인" and H.facts_of(X20) == "\n💡 단위가격 개당 413원\n⚠️ 확인할 점 배송비 확인"
sl20, af20 = H.store_link, H.affiliate
H.store_link = lambda u: None
D20 = {"title": "[토스] 썬키스트 오렌지소다 355ml 24입 (9,900원/무료)", "url": "https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&no=2020", "board": "뽐뿌"}
with contextlib.redirect_stdout(io.StringIO()):
    tt20, lt20, _ = H.deal_post({**D20, "toss": "https://toss.shopping/_m/C20"}, "24입 9,900원", None, X20)
    H.affiliate = lambda u: (None, False); tn20, ln20, _ = H.deal_post(D20, "24입 9,900원", None, X20)  # 쉐어링크 아닌 [토스] 딜(원글)
    tv20, lv20, _ = H.deal_post({**D20, "title": "[네이버] 썬키스트 오렌지소다 355ml 24입 (9,900원/무료)"}, "24입 9,900원", None, X20)
    H.affiliate = lambda u: ("https://link.coupang.com/a/C20", True); tc20, lc20, _ = H.deal_post({**D20, "title": "[쿠팡] 썬키스트 오렌지소다 355ml 24입 (9,900원/무료)"}, "24입 9,900원", None, X20)
assert lt20 == "https://toss.shopping/_m/C20" and "\n💡 단위가격 개당 413원\n🙋 탄산 좋아하는 집 · 캠핑 가는 분\n👍 냉장고에 넣어 두고 손님 오면 한 캔\n⚠️ 확인할 점 배송비 확인" in tt20 and "게시 시점 가격" in tt20
assert all("🙋" not in t and "👍" not in t for t in (tn20, tv20, tc20)) and "💡 단위가격 개당 413원" in tn20 + tv20 and "9,900원 → 1개 413원 · 무료" in tc20 and lc20 == "https://link.coupang.com/a/C20" and "search.shopping.naver.com" in lv20  # 쿠팡 몰별 틀 = 단위가격은 가격 줄 '→'(10/22)
H.store_link, H.affiliate = sl20, af20
# 묶음 글(토스 베스트·하루특가 리스트·TOP·미리보기·간식·카드)은 그대로: 👉 코멘트 줄 그대로, 🙋·👍 X
assert '"👉 " + esc(p["comment"])' in inspect.getsource(H.toss_deals) and all("wu(" not in inspect.getsource(f) and "toss_lines(" not in inspect.getsource(f) for f in (H.top_post, H.top_deals, H.preview, H.wx_post, H.threads))
assert inspect.getsource(H.toss_deals).count("toss_lines(") == 2 and "toss_th(info, name, toss_price(x), lines, link, icon)" in inspect.getsource(H.toss_solo)  # 개별 글(토스 픽 채움·뷰티 채움·단독)만
# Threads 개별 글(posts.json 커뮤니티 토스 딜) = 480자 넘으면 👍 -> 🙋 순서로 뺌, 게시 시점 줄은 남김
c20 = []
def http20b(url, body=None, headers=None, method=None):
    if "/me?fields=id" in url: return json.dumps({"id": "777"})
    if "/777/threads?" in url: c20.append(parse_qs(urlsplit(url).query)["text"][0]); return json.dumps({"id": "c%d" % len(c20)})
    if "/threads_publish?" in url: return json.dumps({"id": "p%d" % len(c20)})
    raise AssertionError(url)
sv20b = (H.POSTS, H.th_solo, H.TH_LINK_AB, H.time.sleep)
H.http, H.POSTS, H.th_solo, H.TH_LINK_AB, H.time.sleep = http20b, "posts20.json", (lambda *a, **k: True), False, (lambda s: None)
T20 = f"{H.TOSS_NOTE}\n\n🔥 [토스] 썬키스트 오렌지소다 355ml 24입 (9,900원/무료)\n\n" + "탄산 24캔 구성이에요. " * 16 + "\n💡 단위가격 개당 413원\n🙋 탄산 좋아하는 집 · 캠핑 가는 분\n👍 냉장고에 넣어 두고 손님 오면 한 캔\n⚠️ 10/21 12:05 게시 시점 가격\n\n출처: 뽐뿌"
json.dump([{"t": kt(0), "text": T20, "url": "https://toss.shopping/_m/C20", "mid": 2020, "s": 8}], open(H.POSTS, "w"), ensure_ascii=False); H.threads_deals({})
(t20,) = c20
assert len(t20) <= 480 and "👍" not in t20 and "🙋 탄산 좋아하는 집 · 캠핑 가는 분" in t20 and "⚠️ 10/21 12:05 게시 시점 가격" in t20 and t20.startswith(H.th_note(H.TOSS_NOTE)), (len(t20), t20)
assert t20.count("🙋") == 1 and t20.count("👋") == 1 and "\n👋 팔로우하면 매일 이런 특가가 피드에 떠요\n📲 실시간 알림 t.me/hotdeal_pick" in t20, t20  # 10/21 진우: 🙋 = 누가 줄만, 팔로우 줄 = 👋
# 진우 토스 링크(관리자 딜) = 🙋·👍 O / 진우 쿠팡 링크 = X · 커뮤니티 딜 게시 경로(main·toss_post)가 who·use를 넘김
a20 = []; H.tg = lambda m, **p: a20.append((m, p)) or {"message_id": 3000 + len(a20), "text": p.get("text", ""), "entities": []}
H.ai_pick = lambda prompt, lines: [{"i": 0, "score": 8, "comment": "24입 9,900원", **X20}]
json.dump([], open(H.POSTS, "w"))
for l20, yes20 in (("https://toss.shopping/_m/A20", True), ("https://link.coupang.com/a/A20", False)):
    a20.clear(); assert H.admin_deal(["[토스] 썬키스트 오렌지소다 355ml 24입 9,900원"], l20, 77)
    c20 = [p["text"] for m, p in a20 if p.get("chat_id") == H.CHANNEL][0]
    assert ("\n🙋 탄산 좋아하는 집 · 캠핑 가는 분\n👍 냉장고에 넣어 두고 손님 오면 한 캔\n" in c20) == yes20 and "💡 단위가격 개당 413원" in c20, (l20, c20)
assert all(re.search(r'"warn", "who", "use"(?:, "tone")?\)', inspect.getsource(f)) for f in (H.main, H.toss_post, H.admin_deal))
c20 = []; json.dump([{"t": kt(0), "text": T20.replace("탄산 24캔 구성이에요. " * 16, "탄산 24캔 구성이에요. " * 17), "url": "https://toss.shopping/_m/C21", "mid": 2021, "s": 8}], open(H.POSTS, "w"), ensure_ascii=False); H.threads_deals({})
assert len(c20) == 1 and len(c20[0]) <= 480 and "⚠️ 10/21 12:05 게시 시점 가격" in c20[0] and "💡 단위가격 개당 413원" in c20[0], c20  # 🙋·👍가 빠져도 게시 시점 줄은 그대로
assert "🙋" not in c20[0] and "👍" not in c20[0] and c20[0].count("👋") == 1 and "\n👋 팔로우하면 매일 이런 특가가 피드에 떠요\n" in c20[0], c20  # 👍 -> 🙋를 빼도 👋 팔로우 줄은 남음
os.remove("posts20.json"); os.remove("ev20.json")
(H.POSTS, H.th_solo, H.TH_LINK_AB, H.time.sleep) = sv20b
(H.http, H.tg, H.ai_pick, H.EVENTS, time.time, H.HAS_TOSS, H.TOSS_SOLO_HOURS, H.TOSS_GAP_MIN, H.TOSS_NO_CMP, tk20) = sv20
H.E.pop("THREADS_TOKEN", None) if tk20 is None else H.E.update(THREADS_TOKEN=tk20)
# 9-21 (10/21 진우 '번갈아'): Threads 채움 칸 = 토스 픽 ↔ 진우 🔥 딜 번갈아(직전 채움 종류 seen thfill), 진우 딜끼리는 먼저 올라온 것부터 ·
#       진우 대기 없으면 토스 연속 · 토스 대기 없으면 진우 연속 · ①② 좋은 딜은 그대로 먼저 · 🛒 진우 딜은 개별 X · 45분 간격 그대로
import io, contextlib
sv21 = (H.http, H.POSTS, H.TH_LINK_AB, H.time.sleep, time.time, H.E.get("THREADS_TOKEN"), H.TH_SOLO_MAX, H.TH_SOLO_GAP, H.TH_SOLO_RUN, H.th_strong, H.TH_SOLO_FILL)
H.TH_SOLO_MAX, H.TH_SOLO_GAP, H.TH_SOLO_RUN, H.th_strong, H.TH_SOLO_FILL = 99, 45 * 60, 1, th_strong0, True  # 실제 값(45분·1회 1개·진짜 ①② 판단·채움 켬)
p21 = []
def http21(url, body=None, headers=None, method=None):
    if "/me?fields=id" in url: return json.dumps({"id": "777"})
    if "/777/threads?" in url: p21.append(parse_qs(urlsplit(url).query)["text"][0]); return json.dumps({"id": "c%d" % len(p21)})
    if "/threads_publish?" in url: return json.dumps({"id": "p%d" % len(p21)})
    raise AssertionError(url)
H.http, H.POSTS, H.TH_LINK_AB, H.time.sleep, H.E["THREADS_TOKEN"] = http21, "posts21.json", False, (lambda s: None), "tk"
tq21 = lambda n, at, r: {"t": TK("2026-10-21 " + at), "text": f"{H.TOSS_NOTE}\n\n🔥 토스{n}\n💰 7,900원\n⚠️ 10/21 {at} 게시 시점 가격\n\n🛒 https://toss.shopping/_m/T{n}",
                         "link": f"https://toss.shopping/_m/T{n}", "bt": 0, "id": 2100 + n, "r": r, "k": "best", "s": 8}
def post21(mid, name, at, own=True, weak=False, body="쿠팡 평균가보다 낮아요", url=None, s=None):
    p = {"t": "2026-10-21 " + at, "url": url or f"https://link.coupang.com/a/J{mid}", "mid": mid,
         "text": f"{H.DISCLOSURE}\n\n" + (f"🛒 [쿠팡] {name} (10,370원)\n\n🤔 솔직히 특가로는 약한 제품 — 평소 가격" if weak else f"🔥 [쿠팡] {name} (16,940원)\n\n{body}")}
    return {**p, **({"own": 1} if own else {}), **({"s": s} if s else {})}
def run21(s21, at):
    p21.clear(); time.time = lambda: TK("2026-10-21 " + at); o = io.StringIO()
    with contextlib.redirect_stdout(o): H.threads_deals(s21)
    return [re.search(r"[🔥🛒👍] (?:\[\S+\] )?(\S+)", x).group(1) for x in p21], o.getvalue()
def seq21(s21, times):
    out = []
    for at in times:
        got, log = run21(s21, at); out.append((at, got, s21.get("thfill", {}).get("k"), log))
    return out
# 토스 대기 3 + 진우 🔥 2(+ 🛒 1) -> toss·own·toss·own·toss, 진우 딜은 먼저 올라온 것부터, 45분 안엔 아무것도 X(직전 채움 종류도 그대로)
json.dump([post21(2111, "진우A", "20:31"), post21(2112, "진우약함", "20:32", weak=True), post21(2113, "진우B", "20:35")], open(H.POSTS, "w"), ensure_ascii=False)
s21 = {"thtoss": {"t": TK("2026-10-21 22:00"), "q": [tq21(1, "20:30", 0), tq21(2, "21:00", 1), tq21(3, "22:00", 2)]}}
r21 = seq21(s21, ("20:40", "21:26", "21:46", "22:12", "22:58", "23:44"))
assert [x[:3] for x in r21] == [("20:40", ["토스1"], "toss"), ("21:26", ["진우A"], "own"), ("21:46", [], "own"), ("22:12", ["토스2"], "toss"), ("22:58", ["진우B"], "own"), ("23:44", ["토스3"], "toss")], [x[:3] for x in r21]
assert "threads fill turn toss (대기 own 2·toss 1)" in r21[0][3] and "threads fill turn own (대기 own 2·toss 1)" in r21[1][3] and "fill turn" not in r21[2][3], [x[3] for x in r21]
assert [(p["mid"], p.get("th")) for p in json.load(open(H.POSTS))] == [(2111, 1), (2112, None), (2113, 1)] and s21["thtoss"]["q"] == []  # 🛒 진우 딜은 개별 X
assert {k: v for k, v in s21.items() if (v["t"] if isinstance(v, dict) else v) > 0}.get("thfill") == s21["thfill"]  # seen 정리(main 끝)에 걸려도 안 깨짐(t 있음)
# 진우 대기 없으면 토스 연속(직전이 토스여도) · 토스 대기 없으면 진우 연속(먼저 올라온 것부터) -> 둘 다 없으면 예전처럼 점수 순 다른 수수료 딜
json.dump([post21(2121, "진우약함", "20:32", weak=True)], open(H.POSTS, "w"), ensure_ascii=False)
s21 = {"thfill": {"t": 1, "k": "toss"}, "thtoss": {"t": 1, "q": [tq21(4, "20:30", 0), tq21(5, "20:31", 1)]}}
assert [x[:3] for x in seq21(s21, ("20:40", "21:26"))] == [("20:40", ["토스4"], "toss"), ("21:26", ["토스5"], "toss")]
json.dump([post21(2131, "진우C", "20:35"), post21(2132, "링크프라이스9점", "20:33", own=False, s=9, url="https://click.linkprice.com/click.php?m=gmarket&a=A1&l=9999&tu=x"), post21(2133, "진우D", "20:34")], open(H.POSTS, "w"), ensure_ascii=False)
s21 = {"thfill": {"t": 1, "k": "own"}}
r21 = seq21(s21, ("20:40", "21:26", "22:12"))
assert [x[:3] for x in r21] == [("20:40", ["진우D"], "own"), ("21:26", ["진우C"], "own"), ("22:12", ["링크프라이스9점"], "post")], [x[:3] for x in r21]
assert "threads fill turn own (대기 own 2·toss 0)" in r21[0][3] and "threads fill turn post (대기 own 0·toss 0)" in r21[2][3]
# ①② 좋은 딜(strong)은 그대로 먼저 — 채움 칸이 아니라 직전 채움 종류는 안 바뀜 -> 다음 채움 칸은 진우 딜
json.dump([post21(2141, "진우E", "20:35"), post21(2142, "같은상품차이", "20:36", own=False, s=8, body="💡 쿠팡 같은 상품(20,000원)보다 3,060원 쌈")], open(H.POSTS, "w"), ensure_ascii=False)
s21 = {"thfill": {"t": 1, "k": "toss"}, "thtoss": {"t": 1, "q": [tq21(6, "20:30", 0)]}}
assert [x[:3] for x in seq21(s21, ("20:40", "21:26", "22:12"))] == [("20:40", ["같은상품차이"], "toss"), ("21:26", ["진우E"], "own"), ("22:12", ["토스6"], "toss")]
# 채움 끄면(TH_SOLO_FILL False) 진우 🔥 딜도 토스 픽도 채움 X — 예전 그대로
fill21, H.TH_SOLO_FILL = H.TH_SOLO_FILL, False
json.dump([post21(2151, "진우F", "20:35")], open(H.POSTS, "w"), ensure_ascii=False)
s21 = {"thtoss": {"t": 1, "q": [tq21(7, "20:30", 0)]}}
assert [x[:3] for x in seq21(s21, ("20:40",))] == [("20:40", [], None)]
H.TH_SOLO_FILL = fill21
os.remove("posts21.json")
(H.http, H.POSTS, H.TH_LINK_AB, H.time.sleep, time.time, tk21, H.TH_SOLO_MAX, H.TH_SOLO_GAP, H.TH_SOLO_RUN, H.th_strong, H.TH_SOLO_FILL) = sv21
H.E.pop("THREADS_TOKEN", None) if tk21 is None else H.E.update(THREADS_TOKEN=tk21)
# 9-22 (10/21 22:30 점검): 토스 딜이 든 하루 리스트(21시 모아보기·카드 이미지·Threads 카드 글·블로그 초안) = [몰] 태그·다른 몰 이름 X + 게시 시점 줄
#       (10/14 22:30 TOP 리스트와 같은 규칙 — 10/21 모아보기에 [토스]와 [네이버]·[쿠팡]이 같이 나감) · 토스 딜 없으면 예전 그대로
import cards as C22
sv22 = (H.tg, H.POSTS, time.time, C22.make, C22.reel, H.fill_reel, H.tg_video, H.TOSS_NO_CMP, H.E.get("IG_TOKEN"), H.E.get("THREADS_TOKEN"), H.http, H.th_bundle)
D22, sent22, made22, tb22 = "2026-10-22", [], [], []
P22 = [{"t": f"{D22} 09:20", "text": f"{H.TOSS_NOTE}\n\n🔥 [토스] 웅진식품 애사비 파인애플맛 500ml 24병 (13,070원/무배)\n\n선착순 3,000개예요\n💡 단위가격 병당 545원", "url": "https://toss.shopping/_m/A22", "mid": 2201, "s": 7},
       {"t": f"{D22} 10:31", "text": "🔥 [네이버] 포크밸리 한돈 삼겹살 1kg (네멤18,900원/네멤무료)\n\n쿠팡보다 싸요 · 100g당 1,890원", "url": "https://search.shopping.naver.com/search/all?query=x", "mid": 2202, "s": 8},
       {"t": f"{D22} 19:43", "text": f"{H.DISCLOSURE}\n\n🔥 [쿠팡] 코멧 포켓형 손난로 핫팩 100g, 30개 (8,860원)\n\n1개당 295원이에요", "url": "https://link.coupang.com/a/K22", "mid": 2203, "own": 1, "s": 6}]
H.tg = lambda m, **p: sent22.append((m, p)) or {"message_id": 7000 + len(sent22)}
C22.make, C22.reel, H.fill_reel, H.tg_video, H.TOSS_NO_CMP = (lambda items, *a, **k: made22.append([i["title"] for i in items])), (lambda *a, **k: "reel22.mp4"), (lambda ps: None), (lambda *a, **k: None), True
H.E.pop("IG_TOKEN", None); time.time = lambda: TK(f"{D22} 21:05")
plain22 = lambda x: H.html.unescape(re.sub(r"<[^>]+>", "", x))
names22 = lambda txt: [plain22(l) for l in txt.split("\n") if re.match(r"\d+\. ", plain22(l))]
assert H.toss_list(P22) and not H.toss_list(P22[1:]) and H.list_name(P22[1], True) == "포크밸리 한돈 삼겹살 1kg (네멤18,900원)" and H.list_name(P22[1], False) == H.title_of(P22[1]["text"])
for ps22, toss22 in ((P22, True), (P22[1:], False)):
    sent22.clear(); made22.clear(); H.digest({}, ps22)
    ch22 = next(p["text"] for m, p in sent22 if p.get("chat_id") == H.CHANNEL)
    bl22 = next(p["text"] for m, p in sent22 if p.get("chat_id") == H.ADMIN and "블로그용" in p.get("text", ""))
    rows22 = names22(ch22)
    assert len(rows22) == len(ps22) and ("게시 시점 가격" in ch22) == toss22, ch22
    assert (not any(re.search(H.OTHER_STORES + r"|\[", r) for r in rows22)) == toss22 and ("1. 웅진식품 애사비 파인애플맛 500ml 24병 (13,070원)" in rows22) == toss22, rows22
    assert (H.TOSS_NOTE in ch22.split("📋")[0]) == toss22 and H.DISCLOSURE in ch22.split("📋")[0], ch22[:200]  # 대가성 문구는 맨 위 그대로(목록 앞)
    assert (not any(re.search(r"\[(?:토스|네이버|쿠팡)\]", t) for t in made22[0])) == toss22 and len(made22[0]) == len(ps22), made22  # 카드 이미지 = 몰 이름 칸 X
    body22 = [l for l in bl22.split("\n") if l and not l.startswith(H.NOTE_STARTS + ("이 포스팅은", "👉 http", "더 많은 핫딜", "실시간 알림"))]
    assert (not any(re.search(H.OTHER_STORES + r"|\[토스\]", l) for l in body22)) == toss22, body22  # 블로그 초안도(제목·코멘트 줄 — 다른 몰 이름 조각 뺌)
    assert ("100g당 1,890원" in bl22) and (("쿠팡보다 싸요" in bl22) != toss22) and ("게시 시점 가격" in bl22) == toss22, bl22  # 블로그 초안도 게시 시점 줄
    assert ("포크밸리 한돈 삼겹살 1kg (네멤18,900원/네멤무료)" in made22[0]) == toss22, made22  # 카드 이미지 배송 칸('/무료')은 그대로
# 21시 모아보기에 합친 '🌙 오늘 밤 예약 특가' 줄(PREVIEW_MIN개 미만)도 같은 글: 토스 딜이 든 모아보기 = 밤 줄 쿠팡 비교 X · 토스 딜이 밤 줄에만 있어도 규칙 · 밤 줄 링크의 대가성 문구도 맨 위
ev22 = H.EVENTS; H.EVENTS = "ev22.json"
NE22 = {"at": f"{D22} 23:10", "deal": True, "url": "https://link.coupang.com/a/N22", "text": "🔥 <b>[쿠팡] 메르헨트 폼클렌징 500ml 2개 (11,900원)</b>\n\n💡 쿠팡 같은 상품(17,900원)보다 6,000원 쌈"}
NT22 = {"at": f"{D22} 23:20", "deal": True, "url": "https://toss.shopping/_m/N22", "text": "🔥 <b>[토스] 밤 토스 특가 우유 24팩 (12,000원)</b>\n\n좋아요"}
for ps22, evs22, toss22 in (([P22[0], P22[1]], [NE22], True), ([P22[1]], [NE22], False), ([P22[1]], [NT22], True)):
    json.dump(evs22, open(H.EVENTS, "w"), ensure_ascii=False); sent22.clear(); time.time = lambda: TK(f"{D22} 21:05"); H.digest({}, ps22)
    ch22 = next(p["text"] for m, p in sent22 if p.get("chat_id") == H.CHANNEL)
    assert "🌙" in ch22 and ("쿠팡 같은 상품보다 6,000원 쌈" in ch22) == (not toss22 and evs22 == [NE22]) and ("게시 시점 가격" in ch22) == toss22, ch22
    assert (not any(re.search(H.OTHER_STORES + r"|\[", r) for r in names22(ch22))) == toss22 and (H.DISCLOSURE in ch22.split("📋")[0]) == (evs22 == [NE22]), ch22  # 밤 줄 쿠팡 링크 = 쿠팡 대가성 문구
os.remove(H.EVENTS); H.EVENTS = ev22
# Threads 21시 카드 글: 줄 = 몰 이름 X, 토스 딜이 든 카드 = 게시 시점 줄 · 토스 딜 없으면 예전 그대로
H.POSTS, H.http, H.th_bundle, H.E["THREADS_TOKEN"] = "posts22.json", (lambda url, body=None, headers=None, method=None: ""), (lambda seen, kind, text, link=None, image=None: tb22.append(text)), "tk"
os.makedirs("docs/cards", exist_ok=True); open(f"docs/cards/{D22}.png", "wb").write(b"png"); os.path.exists(f"docs/cards/{D22}.json") and os.remove(f"docs/cards/{D22}.json")  # 번호 순서 파일은 posts22 기준으로 새로
PT22 = {**P22[0], "url": "https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&no=22", "text": P22[0]["text"].replace(H.TOSS_NOTE + "\n\n", "")}  # [토스] 제목 + 쉐어링크 아님 = 수수료 줄 X, 카드 이미지엔 나옴
for ps22, toss22 in ((P22, True), (P22[1:], False), ([PT22] + P22[1:], True)):
    json.dump(ps22, open(H.POSTS, "w"), ensure_ascii=False); tb22.clear(); time.time = lambda: TK(f"{D22} 21:30"); H.threads({})
    (th22,) = tb22; rows22 = names22(th22)
    assert ("게시 시점 가격" in th22) == toss22 and (not any(re.search(H.OTHER_STORES + r"|\[", r) for r in rows22)) == toss22 and len(rows22) == len([p for p in ps22 if H.aff_note(p["url"])]), th22
    assert (not any(re.search(r"\[", r) for r in H.card_caption(D22)[0])) == toss22  # 인스타 캡션 줄도 같은 줄
for f in (f"docs/cards/{D22}.png", f"docs/cards/{D22}.json", "posts22.json"):
    os.path.exists(f) and os.remove(f)
(H.tg, H.POSTS, time.time, C22.make, C22.reel, H.fill_reel, H.tg_video, H.TOSS_NO_CMP, ig22, tk22, H.http, H.th_bundle) = sv22
H.E.pop("IG_TOKEN", None) if ig22 is None else H.E.update(IG_TOKEN=ig22)
H.E.pop("THREADS_TOKEN", None) if tk22 is None else H.E.update(THREADS_TOKEN=tk22)
# 9-23 (10/21 밤 Cowork): Threads 개별 글이 250자에 줄 중간에서 잘려 '⚠️ 확인할 점:'·'⚠️'만 남던 것 -> 줄 단위로 줄이고 ⚠️ 줄은 끝에 남김
#       (넘치면 마지막 조각 '결제 전 최종가 확인 (M/D H시 가격)'만, 그래도 안 되면 줄째 뺌) — 빈 ⚠️ 줄 X
K23 = "🔥 [쿠팡] 코멧 포켓형 손난로 핫팩 100g, 30개 (8,860원)\n\n로켓배송 100g 손난로 중 1개당 가장 싸요 — 오늘 쿠팡 검색 상위 기준 1개당 295원(참고: 충성 100g 317원·해피데이 100g 373원)\n⭐ 리뷰 1,419 · 한 달 2,000명 이상 구매 · 손난로/핫팩 구매 8위 · 🚀 로켓배송 · 무료반품 30일\n💡 150개 40,310원이면 1개당 269원 · 최고 70도·18시간 이하(포장 표기)\n⚠️ 확인할 점: '22% 할인'은 정가 기준이라 참고만 · 결제 전 최종가 확인 (10/21 19:12 가격)"
G23 = "🔥 [쿠팡] 하루온 군인핫팩 포켓용 대용량 160g, 30개 (13,520원)\n\n로켓배송 160g 대형 핫팩 중 1개당 가장 싸요 — 오늘 쿠팡 검색 상위 기준 1개당 451원(참고: 충성 160g 60개 469원·마이핫 160g 750원)\n⭐ 리뷰 10,548 · 한 달 4,000명 이상 구매 · 손난로/핫팩 구매 2위 · 🚀 로켓배송(새벽) · 무료반품 30일\n💡 최고 70도·20시간 지속(포장 표기) · 대형이라 야외 활동·출퇴근용\n⚠️ 확인할 점: '30% 할인'은 정가 기준이라 참고만 · 결제 전 최종가 확인 (10/21 19:15 가격)"
EMPTY23 = r"(?m)^⚠️\s*(?:확인할 점:?)?\s*$"
def ok23(src, out, lim):  # lim 안 · 빈 ⚠️ 줄 X · 줄 = 원래 줄 그대로 / '…'로 줄인 앞부분 / ⚠️ 줄의 마지막 조각
    org = src.split("\n")
    return len(out) <= lim and not re.search(EMPTY23, out) and all(l in org or (l.endswith("…") and any(o.startswith(l[:-1]) for o in org))
                                                                 or (l.startswith("⚠️") and any(o.startswith("⚠️") and o.endswith(l.split(": ", 1)[-1]) for o in org)) for l in out.split("\n"))
for src23, at23 in ((K23, "19:12"), (G23, "19:15")):
    for lim23 in (250, 200, 160):
        o23 = H.th_fit(src23, lim23)
        assert ok23(src23, o23, lim23) and o23.endswith(f"⚠️ 확인할 점: 결제 전 최종가 확인 (10/21 {at23} 가격)") and o23.startswith(src23.split("\n")[0]), (lim23, o23)
    assert H.th_fit(src23, 400) == src23  # 들어가면 그대로
assert "\n💡 150개 40,310원이면…\n" in H.th_fit(K23, 250), H.th_fit(K23, 250)  # 처음 넘치는 줄은 띄어쓰기에서 '…'(그 뒤 줄은 뺌, ⚠️ 줄은 끝에)
o23 = H.th_fit(K23, len(K23) - 1); assert ok23(K23, o23, len(K23) - 1) and K23.split("\n")[-2] in o23.split("\n") and o23.endswith("⚠️ 확인할 점: 결제 전 최종가 확인 (10/21 19:12 가격)"), o23  # 1자 넘침 = 다른 줄은 그대로, ⚠️ 줄만 마지막 조각
tiny23 = H.th_fit(K23, 60); assert ok23(K23, tiny23, 60) and "⚠️" not in tiny23 and tiny23.startswith("🔥 [쿠팡] 코멧")  # 제목만 겨우 = ⚠️ 줄째 뺌(빈 줄 X)
two23 = "🔥 [토스] 탄산 24캔 (9,900원)\n\n" + "탄산 24캔 구성이에요. " * 20 + "\n💡 단위가격 개당 413원\n⚠️ 확인할 점 배송비 확인\n⚠️ 10/21 12:05 게시 시점 가격"
o23 = H.th_fit(two23, 200); assert ok23(two23, o23, 200) and o23.endswith("⚠️ 확인할 점 배송비 확인\n⚠️ 10/21 12:05 게시 시점 가격"), o23  # ⚠️ 줄 여럿(토스 게시 시점 줄)도 끝에 그대로
# Threads 글 전체(threads_deals): 진우 쿠팡 핫팩 글 = 빈 ⚠️ 줄 X, 끝 ⚠️ 줄 = 결제 전 최종가 확인 (가격 시각)
c23, sv23 = [], (H.http, H.POSTS, H.th_solo, H.TH_LINK_AB, H.time.sleep, H.E.get("THREADS_TOKEN"))
def http23(url, body=None, headers=None, method=None):
    if "/me?fields=id" in url: return json.dumps({"id": "777"})
    if "/777/threads?" in url: c23.append(parse_qs(urlsplit(url).query)["text"][0]); return json.dumps({"id": "c%d" % len(c23)})
    if "/threads_publish?" in url: return json.dumps({"id": "p%d" % len(c23)})
    raise AssertionError(url)
H.http, H.POSTS, H.th_solo, H.TH_LINK_AB, H.time.sleep, H.E["THREADS_TOKEN"] = http23, "posts23.json", (lambda *a, **k: True), False, (lambda s: None), "tk"
for n23, src23 in enumerate((K23, G23)):
    c23.clear(); json.dump([{"t": kt(0), "text": f"{H.DISCLOSURE}\n\n{src23}", "url": f"https://link.coupang.com/a/H{n23}", "mid": 2300 + n23, "own": 1}], open(H.POSTS, "w"), ensure_ascii=False); H.threads_deals({})
    (t23,) = c23
    assert not re.search(EMPTY23, t23) and re.search(r"\n⚠️ 확인할 점: 결제 전 최종가 확인 \(10/21 19:1\d 가격\)\n\n👉 https://link\.coupang\.com/a/H", t23) and len(t23) <= 500 and t23.startswith(H.th_note(H.aff_note(f"https://link.coupang.com/a/H{n23}")).split("\n")[0]), t23
os.remove("posts23.json")
(H.http, H.POSTS, H.th_solo, H.TH_LINK_AB, H.time.sleep, tk23) = sv23
H.E.pop("THREADS_TOKEN", None) if tk23 is None else H.E.update(THREADS_TOKEN=tk23)
# 9-24 (10/21 밤 진우 'Threads 개별 딜 글 사람이 올리는 느낌' -> '너무 AI 같다' -> 두 시안 섞어서): th_deal로 가는 글 = 대가성 문구 첫 줄 → Claude 문장(글마다 무작위 A 반말 / B 음슴체, 해요체 X,
#       둘째 줄까지 상품명 · 가격은 어딘가에) → 가격 기준 줄(토스 = '⚠️ M/D HH:MM 게시 시점 가격' 그대로) → A일 때만 3개에 1개쯤 질문 → 👉 링크. 이모지 0~1개.
#       라벨 줄·써 본 척·효능·과장·클릭 유도(토스 + 다른 몰·비교)·재료에 없는 원 금액 문장은 빠짐, 상품명·가격 빠짐·~요 줄/같은 첫 문장 2번·480자 못 넣음·Claude 실패 = 지금 틀
#       · 개별 글 간격 35~55분(앞 글 시각으로 정함)
import inspect
sv24 = (H.http, H.POSTS, H.th_solo, H.TH_LINK_AB, H.time.sleep, H.E.get("THREADS_TOKEN"), H.TOSS_NO_CMP, H.ai_voice, H.TH_SOLO_GAP, time.time, H.random)
c24, p24, a24, n24, ST24 = [], [], [], [0], []  # Threads 글 · Claude에 간 프롬프트 · 가짜 Claude 답(차례대로) · 글 id · 말투(차례대로)
def http24(url, body=None, headers=None, method=None):
    if "/me?fields=id" in url: return json.dumps({"id": "777"})
    if "/777/threads?" in url: c24.append(parse_qs(urlsplit(url).query)["text"][0]); return json.dumps({"id": "c%d" % len(c24)})
    if "/threads_publish?" in url: n24[0] += 1; return json.dumps({"id": "p%d" % n24[0]})
    raise AssertionError(url)
def voice24(prompt):
    p24.append(prompt); a = a24.pop(0)
    if isinstance(a, Exception): raise a
    return a
class R24:  # 말투 무작위 = 차례대로(셀프체크용)
    choice = staticmethod(lambda xs: ST24.pop(0))
H.http, H.POSTS, H.th_solo, H.TH_LINK_AB, H.time.sleep, H.E["THREADS_TOKEN"] = http24, "posts24.json", (lambda *a, **k: True), False, (lambda s: None), "tk"
H.TH_VOICE, H.TOSS_NO_CMP, H.ai_voice, H.random, time.time = True, True, voice24, R24, lambda: TK("2026-10-21 21:00")
YO24, EMO24 = H.VOICE_YO, H.VOICE_EMOJI
S24 = "🔥 [토스] 웅진식품 애사비 파인애플맛500ml*24(13070원/무배) 외 2\n\n웅진식품 애사비 파인애플맛 500ml 24병이 13,070원, 무료배송입니다. 선착순 3,000개 한정이고 다른 맛 옵션은 가격이 다를 수 있어요.\n💡 단위가격 병당 545원\n🙋 음료 박스로 사는 집 · 사무실 탕비실\n👍 냉장고에 넣어 두고 차갑게 한 병씩\n⚠️ 확인할 점 선착순 3,000개 한정\n⚠️ 10/21 09:20 게시 시점 가격\n\n출처: 뽐뿌"
# 10/23 진우 'Threads 딜 글 가독성 — 보기 좋게, 깔끔하게': th_voice = 고정 레이아웃 + Claude 말투 한 줄(TONES 4가지 돌림) — 대가성 문구 / 몰 머리 줄 · 짧은 상품명 · 💰 가격 (단가)
#   / ✔ 리뷰·구매 수(반올림) · ✔ 원문 사실 2개 · 💡 한 줄(토스 X) / 말투 한 줄(숫자 X · 이모지 0~1) / ⏰ 시점(쿠폰가) · 결제 전 확인(토스 = 게시 시점 줄 그대로) + 링크
#   · 블록 사이 빈 줄 · 줄마다 폭 22(th_w) · 숫자 5개까지 · 시점 한 번 · 말투 줄이 규칙에 안 맞으면 1번 다시 -> 그래도면 말투별 기본 한 줄 · 대가성 문구 없음·가격 못 읽음 = 지금 틀
def deal24(seen, src, url, ans, style, own=1):
    c24.clear(); a24[:] = ans; ST24[:] = [style]
    json.dump([{"t": "2026-10-21 19:43", "text": src, "url": url, "mid": 2400, "own": own}], open(H.POSTS, "w"), ensure_ascii=False); H.threads_deals(seen)
    (t,) = c24
    return t
seen24, KU24, GU24, TU24 = {"thvoice": {"t": TK("2026-10-21 20:00")}}, "https://link.coupang.com/a/h1NpZ1ygAT", "https://link.coupang.com/a/h1Nvu1bRx6", "https://toss.shopping/_m/5DR27WGo"
k24 = deal24(seen24, f"{H.DISCLOSURE}\n\n{K23}", KU24, [{"line": "이 가격 실화? 장바구니각이다✨"}], 2)  # 말투 2 발랄한 반말
assert k24 == f"""{H.DISCLOSURE}

🚀 쿠팡 로켓 · 1개당 최저 🔥
코멧 포켓형 손난로 핫팩 100g × 30개
💰 8,860원 (1개당 295원)

✔ 리뷰 1,400+ · 한 달 2,000명+ 구매
✔ 무료반품 30일
💡 150개짜리는 1개당 269원

이 가격 실화? 장바구니각이다✨

⏰ 10/21 19시 가격 · 결제 전 확인
👉 {KU24}""", k24
g24 = deal24(seen24, f"{H.DISCLOSURE}\n\n{G23}", GU24, [{"line": "출퇴근용으로 쟁여 둘 만함"}], 4)  # 말투 4 짧고 깔끔한 음슴체(꾸밈말 '대용량' X)
assert g24 == f"""{H.DISCLOSURE}

🚀 쿠팡 로켓 · 1개당 최저 🔥
하루온 군인핫팩 포켓용 160g × 30개
💰 13,520원 (1개당 451원)

✔ 리뷰 1만+ · 한 달 4,000명+ 구매
✔ 무료반품 30일

출퇴근용으로 쟁여 둘 만함

⏰ 10/21 19시 가격 · 결제 전 확인
👉 {GU24}""", g24
t24 = deal24(seen24, f"{H.TOSS_NOTE}\n\n{S24}", TU24, [{"line": "냉장고에 쟁여 두기 좋아요"}], 1, own=None)  # 토스(커뮤니티 토스 딜) 말투 1 단정한 해요체 — 💡 X · 게시 시점 줄 그대로 · '외 2' X
assert t24 == f"""{H.TOSS_NOTE}

💙 토스 특가 🔥
웅진식품 애사비 파인애플맛500ml × 24
💰 13,070원 (병당 545원)

✔ 무료배송

냉장고에 쟁여 두기 좋아요

⚠️ 10/21 09:20 게시 시점 가격
👉 {TU24}""", t24
for t in (k24, g24, t24):
    assert all(H.th_w(l) <= H.TH_W for l in t.split("\n")[1:] if not l.startswith(("👉", "🚀", "💙"))) and len(t) <= 480 and "👋" not in t and "📲" not in t, t  # 줄마다 폭 22 안(대가성 문구·머리·링크 줄 빼고)
    assert len(re.findall(H.TH_NUM, "\n\n".join(t.split("\n\n")[1:3]))) <= H.TH_NUMS and t.count("⏰") + t.count("게시 시점") == 1 and "\n\n\n" not in t, t  # 숫자 5개까지 · 시점은 한 줄에 한 번
assert "말투 = 발랄한 반말" in p24[0] and "말투 = 짧고 깔끔한 음슴체" in p24[1] and "말투 = 단정한 해요체" in p24[2] and all("이모지 0~1개" in p and "숫자 없이" in p for p in p24)
assert "상품명: 코멧 포켓형 손난로 핫팩 100g, 30개\n가격: 8,860원\n재료:\n" in p24[0] and "150개 40,310원이면 1개당 269원" in p24[0] and "토스 딜:" not in p24[0] and "토스 딜:" in p24[2], p24[0]  # 재료 = 줄이기 전 글
assert "최근 줄: 이 가격 실화? 장바구니각이다✨" in p24[1] and "물음표 쓰지 않기" in p24[1] and "물음표" not in p24[0] and "👋" not in p24[0] and "link.coupang" not in p24[0]  # 물음표는 발랄한 반말만
v24 = seen24["thvoice"]; assert v24["s"] == 1 and len(v24["f"]) == 3 and v24["b"] == ["이 가격 실화? 장바구니각이다✨", "출퇴근용으로 쟁여 둘 만함", "냉장고에 쟁여 두기 좋아요"], v24
# Claude 실패 = 말투별 기본 한 줄(레이아웃은 그대로)
f24 = deal24(seen24, f"{H.DISCLOSURE}\n\n{K23}", KU24, [RuntimeError("api")], 4)
assert f24 == k24.replace("이 가격 실화? 장바구니각이다✨", H.TH_TONE_POOL[4][0]) and seen24["thvoice"]["b"][-1] == H.TH_TONE_POOL[4][0], f24
m24 = seen24["thab"]["m"]; assert m24["p1"]["n"] == m24["p4"]["n"] == "[쿠팡] 코멧 포켓형 손난로 핫팩 100g, 30개 (8,860원)" and [m24[p]["tone"] for p in ("p1", "p2", "p3", "p4")] == [2, 4, 1, 4], m24  # 지금 틀 제목 · 말투
json.dump({}, open(H.METRICS, "w")); H.E["METRICS_DAY"] = "2026-10-21"  # metrics.json: 분류·가격대는 지금 틀 제목으로 + tone = 말투
H.http = lambda url, *a, **k: json.dumps({"data": [{"id": i, "text": t, "timestamp": "2026-10-21T10:43:00+0000"} for i, t in (("p1", k24), ("p2", g24), ("p4", f24))]}) if "/me/threads?" in url \
    else json.dumps({"data": [{"name": "views", "values": [{"value": 7}]}]}) if "/insights?" in url else http24(url)
H.metrics(seen24); r24 = {r["id"]: r for r in json.load(open(H.METRICS))["2026-10-21"]["rows"] if r["ch"] == "th"}
assert r24["p1"]["price"] == r24["p4"]["price"] == "~1만" and r24["p2"]["price"] == "1~3만" and r24["p1"]["cat"] == r24["p4"]["cat"] and r24["p1"]["shop"] == "coupang" and [r24[p]["tone"] for p in ("p1", "p2", "p4")] == [2, 4, 4], r24
del H.E["METRICS_DAY"]; H.http = http24
# 바로 부르기(th_voice): 채널 글 그대로(👋·📲 줄 X)
F24 = f"{H.DISCLOSURE}\n\n{K23}\n\n👉 {KU24}\n{H.th_follow(False)}\n📲 실시간 알림 t.me/hotdeal_pick"
def tv24(ans, seen=None, link=KU24, text=F24, style=2):
    a24[:] = ans; p24.clear(); ST24[:] = [style]; s = seen if seen is not None else {}
    return H.th_voice(s, text, link), s
assert tv24([{"line": "이 가격 실화? 장바구니각이다✨"}])[0] == k24
for bad, style in (("30개 8,860원이면 쟁일 만함", 4), ("제가 써보니 따뜻함", 4), ("역대급 가격이라 무조건", 2), ("지금 바로 클릭", 2), ("링크는 댓글에 있음", 4), ("핫팩 쟁일 때 됐어요", 2), ("핫팩 쟁일 때죠", 4),
                   ("핫팩 몇 개 쟁여?", 4), ("바람 차가워져서 손난로 쟁여 두기 딱 좋은 날씨가 계속되는 중", 4), ("🔥 오늘 핫팩", 4), ("", 4)):
    o24 = tv24([{"line": bad}, {"line": bad}], style=style)[0]  # 숫자·써 본 척·과장·재촉·링크·~요(해요체 말투 아니면)·물음표(발랄한 반말만)·폭·라벨 줄·빈 답 -> 1번 다시 -> 기본 한 줄
    assert (not bad or bad not in o24) and f"\n\n{H.TH_TONE_POOL[style][0]}\n\n" in o24 and len(p24) == 2 and "다시:" in p24[1], (bad, o24)
o24 = tv24([{"line": "핫팩 쟁일 때 됐어요"}], style=1)[0]; assert "\n\n핫팩 쟁일 때 됐어요\n\n" in o24 and len(p24) == 1  # 해요체 말투(1·3) = ~요 OK
o24 = tv24([{"line": "핫팩 몇 개 쟁여?"}], style=2)[0]; assert "\n\n핫팩 몇 개 쟁여?\n\n" in o24 and len(p24) == 1  # 물음표 = 발랄한 반말만
o24 = tv24([{"line": "제가 써보니 따뜻함"}, {"line": "주머니에 하나씩 넣어 두기 좋음"}], style=4)[0]; assert "\n\n주머니에 하나씩 넣어 두기 좋음\n\n" in o24 and len(p24) == 2  # 1번 다시 쓰면 그 줄
o24 = tv24([{"line": "핫팩 쟁이기 좋은 날 🧤✨"}], style=4)[0]; assert "\n\n핫팩 쟁이기 좋은 날\n\n" in o24, o24  # 이모지 2개↑ = 다 뺌
assert "\n\n핫팩 쟁이기 좋은 날 ✨\n\n" in tv24([{"line": "핫팩 쟁이기 좋은 날 ✨"}], style=4)[0]  # 1개까지는 그대로
o24, s24 = tv24([{"line": "주머니에 하나씩 넣어 두기 좋음"}] * 2, {"thvoice": {"t": 1, "f": [re.sub(r"[\W_]+", "", "주머니에 하나씩 넣어 두기 좋음")]}}, style=4)
assert f"\n\n{H.TH_TONE_POOL[4][0]}\n\n" in o24 and len(p24) == 2 and s24["thvoice"]["f"][-1] == re.sub(r"[\W_]+", "", H.TH_TONE_POOL[4][0]), o24  # 최근 10개와 같은 줄 = 다시 -> 기본 한 줄
o24, s24 = tv24([RuntimeError("x")], {"thvoice": {"t": 1, "f": [re.sub(r"[\W_]+", "", H.TH_TONE_POOL[4][0])]}}, style=4); assert f"\n\n{H.TH_TONE_POOL[4][1]}\n\n" in o24  # 기본 한 줄도 최근 것 빼고
o24 = tv24([{"line": "요기요 쿠폰 쓸 데 있으면 쟁여 둘 만함"}], None, "https://link.coupang.com/a/YG", f"{H.DISCLOSURE}\n\n🔥 [쿠팡] 요기요 상품권 2만원권 (18,000원)\n\n10% 할인\n\n👉 https://link.coupang.com/a/YG", 4)[0]
assert "\n\n요기요 쿠폰 쓸 데 있으면 쟁여 둘 만함\n\n" in o24 and len(p24) == 1 and o24.split("\n\n")[1] == "📦 쿠팡 · 10% 할인 🔥\n요기요 상품권 2만원권\n💰 18,000원", o24  # 상품명 속 '요'는 해요체 아님 · 예전 틀 = mall_head(로켓 근거 없으면 📦 쿠팡)
assert tv24([], None, KU24, "🔥 [쿠팡] 대가성 문구 없는 글")[0] == "🔥 [쿠팡] 대가성 문구 없는 글" and not p24  # 대가성 문구 없는 글 = 그대로(Claude 안 부름)
X24 = f"{H.DISCLOSURE}\n\n🔥 [쿠팡] 가격 없는 글\n\n싸다"; assert tv24([], None, KU24, X24)[0] == X24 and not p24  # 가격 못 읽음 = 지금 틀(Claude 안 부름)
LONG24 = "https://link.coupang.com/a/" + "x" * 273  # 300자 링크(TH_LINK_MAX) -> 480자 넘으면 💡 -> ✔ -> 말투 줄 순서로 뺌(대가성 문구·머리·상품명·💰·시점·링크는 그대로)
o24 = tv24([{"line": "주머니에 하나씩 넣어 두기 좋음"}], None, LONG24, F24.replace(KU24, LONG24), 4)[0]
assert len(o24) <= 480 and "💡" not in o24 and "주머니에" in o24 and o24.startswith(H.DISCLOSURE) and o24.endswith(f"⏰ 10/21 19시 가격 · 결제 전 확인\n👉 {LONG24}"), o24
x24 = F24.replace(KU24, LONG24 + "y" * 120); assert tv24([{"line": "쟁여 둘 만함"}], None, LONG24 + "y" * 120, x24, 4)[0] == x24  # 그래도 480자 넘음 = 지금 틀
# 토스 API 개별 글(toss_th) -> 게시 시점 줄 그대로 · 다른 몰·비교 말 X(1번 다시) · 💡 X
tt24 = H.toss_th("", "웅진식품 애사비 파인애플맛 500ml 24병", "13,070원 (20%↓)", ["🙋 음료 박스로 사는 집"], "https://toss.shopping/_m/T24")
o24 = tv24([{"line": "다른 곳보다 쌈"}, {"line": "시원하게 쟁여 두기 좋음"}], None, "https://toss.shopping/_m/T24", tt24, 4)[0]
assert o24 == f"{H.TOSS_NOTE}\n\n💙 토스 특가 🔥\n웅진식품 애사비 파인애플맛 500ml × 24병\n💰 13,070원 (20%↓)\n\n시원하게 쟁여 두기 좋음\n\n⚠️ 10/21 21:00 게시 시점 가격\n👉 https://toss.shopping/_m/T24", o24
assert "13,070원 (20%↓)" in p24[0] and "🙋 음료 박스로 사는 집" in p24[0] and "🛒" not in p24[0] and "다른 쇼핑몰 이름" in p24[0], p24[0]
# 셀프체크(10/23 진우 캡처 글): 카밀 핸드크림 10/22 20:59 쿠팡 글 -> 고정 레이아웃
CAMIL24 = (f"{H.DISCLOSURE}\n\n🚀 쿠팡 로켓 🔥\n카밀 핸드 앤 네일 크림 클래식 100ml 3개\n8,630원\n쿠팡 검색 상위 핸드크림 중 단위가격 최저 — 1개 2,877원, 10ml당 288원(10/22 17시 검색 · 참고: 카밀 화이트 머스크 75ml 2개 10ml당 411원)\n"
           "⭐ 리뷰 51,181 · 한 달 2,000명 이상 구매 · 🚀 로켓배송(내일 새벽 7시 전 도착) · 30일 무료반품\n💡 독일 제조 · 캐모마일 향 · 많이 쓰면 6개(15,860원)가 1개 2,643원으로 더 쌈\n"
           "⚠️ 확인할 점: 100원 쿠폰 적용가(쿠폰 없으면 8,730원) · 결제 전 최종가 확인 (10/22 19시 가격)\n\n👉 https://link.coupang.com/a/h3vwTUbaGi\n📲 실시간 알림 t.me/hotdeal_pick")
o24 = tv24([{"line": "오늘 이 가격이면 쟁여 두기 좋아요"}], None, "https://link.coupang.com/a/h3vwTUbaGi", CAMIL24, 1)[0]
assert o24 == f"""{H.DISCLOSURE}

🚀 쿠팡 로켓 🔥
카밀 핸드 앤 네일 크림 클래식 100ml × 3개
💰 8,630원 (1개 2,877원)

✔ 리뷰 5만+ · 한 달 2,000명+ 구매
✔ 독일 제조 · 캐모마일 향
💡 6개짜리는 1개 2,643원

오늘 이 가격이면 쟁여 두기 좋아요

⏰ 10/22 19시 100원 쿠폰가 · 결제 전 확인
👉 https://link.coupang.com/a/h3vwTUbaGi""", o24
print("th voice 카밀 셀프체크\n" + o24)
b24, r24 = H.th_ab(o24, "https://link.coupang.com/a/h3vwTUbaGi")  # 링크 B(첫 댓글): ⏰ 줄 바로 아래 👇(10/23 시안), 첫 댓글 = 대가성 문구 + 👉 링크 + 📲
assert b24.endswith("⏰ 10/22 19시 100원 쿠폰가 · 결제 전 확인\n" + H.TH_AB_MARK) and "http" not in b24 and r24 == f"{H.DISCLOSURE}\n\n👉 https://link.coupang.com/a/h3vwTUbaGi\n📲 실시간 알림 t.me/hotdeal_pick", (b24, r24)
assert [H.th_round(n) for n in (51181, 10548, 2000, 1419, 357, 12)] == ["5만+", "1만+", "2,000+", "1,400+", "350+", "12"]  # 리뷰·구매 수 = 아래로(부풀리지 않게)
assert [H.th_name(n) for n in ("스파클 생수 2LX30병 (10/21~)", "깨끗한나라 순수 시그니처 천연펄프 3겹 롤화장지 27m 30롤", "하루온 붙이는 핫팩 50g 10매 × 4개", "해태제과 홈런볼 옥수수콘크림맛 39g x 4개")] == \
    ["스파클 생수 2L × 30병", "깨끗한나라 3겹 롤화장지 27m × 30롤", "하루온 붙이는 핫팩 50g 10매 × 4개", "해태제과 홈런볼 옥수수콘크림맛 39g × 4개"]  # 폭 넘으면 브랜드 바로 뒤 꾸밈말부터
assert len(re.findall(r"(?<!def )\bth_voice\(", inspect.getsource(H))) == 1 and "vt = th_voice(seen, text, link, src) if TH_VOICE else text" in inspect.getsource(H.th_deal)  # th_deal(Threads 개별 딜 글)만 — 채널·묶음 글 X
assert H.TH_VOICE is True and vc0 == (True, 10 * 60)  # 기본값: 켬 · ±10분
aq24, ar24 = [], [{"stop_reason": "end_turn", "content": [{"type": "thinking", "thinking": ""}, {"type": "text", "text": '{"line": "a"}'}]}, {"stop_reason": "refusal", "content": []}]
H.E["ANTHROPIC_API_KEY"], H.http = "k", lambda url, body=None, headers=None, method=None: aq24.append(body) or json.dumps(ar24.pop(0))  # 진짜 ai_voice: 구조화 출력(JSON) — 강제 tool_choice는 이 모델에서 400(10/22 08:00)
assert sv24[7]("p") == {"line": "a"} and "tool_choice" not in aq24[0] and aq24[0]["output_config"]["format"]["schema"]["required"] == ["line"] and aq24[0]["model"] == H.MODEL
try: sv24[7]("p"); raise AssertionError("refusal")
except RuntimeError as e: assert "refusal" in str(e)
H.http = http24; H.E.pop("ANTHROPIC_API_KEY")
H.random = sv24[10]; sty24 = []  # 진짜 무작위: 말투 4가지 다 나옴
for n in range(40):
    s = {}; a24[:] = [{"line": "핫팩 쟁이기 좋은 날"}]; H.th_voice(s, F24, KU24); sty24.append(s["thvoice"]["s"])
assert set(sty24) == {1, 2, 3, 4}, sty24
# 개별 글 간격 35~55분: 앞 글 시각으로 정함(같은 글 뒤엔 실행마다 같은 값), 글마다 다름
H.th_solo, H.TH_SOLO_GAP, H.TH_GAP_JITTER = sv24[2], 45 * 60, 10 * 60
gp24 = [H.th_gap(TK("2026-10-21 12:00") + k * 137) for k in range(300)]
assert 35 * 60 <= min(gp24) < 37 * 60 and 53 * 60 < max(gp24) <= 55 * 60 and len(set(gp24)) > 200 and H.th_gap(TK("2026-10-21 12:00") + 137) == gp24[1], (min(gp24), max(gp24))
gq24 = [H.th_gap(TK("2026-10-21 12:00") + k * 3420) // 60 for k in range(40)]  # 실제 글 간격(~57분 = 실행 4번)마다: 글마다 고르게 흔들림(앞 글과 거의 같은 값 X)
assert min(gq24) < 40 and max(gq24) > 50 and len({b - a for a, b in zip(gq24, gq24[1:])}) >= 12, gq24  # 앞 글 값에서 일정하게 밀리는 것 X
for k in range(5):
    last = TK("2026-10-21 20:00") + 997 * k; g = H.th_gap(last); s = {"thsolo_20261021": {"t": last, "n": 1, "b": 0, "last": last}}
    time.time = lambda: last + g - 1; assert not H.th_solo(s, "x") and not H.th_solo(s, "", reopen="night", gate=True)
    time.time = lambda: last + g; assert H.th_solo(s, "x") and H.th_solo(s, "", reopen="night", gate=True)
os.remove("posts24.json")
(H.http, H.POSTS, H.th_solo, H.TH_LINK_AB, H.time.sleep, tk24, H.TOSS_NO_CMP, H.ai_voice, H.TH_SOLO_GAP, time.time, H.random) = sv24
H.TH_VOICE = False  # 뒤 셀프체크는 지금 틀(9-28 등 — 레이아웃은 th_voice 바로 불러 봄)
H.E.pop("THREADS_TOKEN", None) if tk24 is None else H.E.update(THREADS_TOKEN=tk24)
H.TH_VOICE, H.TH_GAP_JITTER = False, 0
# 9-25 (10/22 00:15 진우 '끝나가는 🔥 먼저'): 채움 칸 — 기다리는 진우 🔥 딜 중 다음 칸(간격 최대 55분 + 다음 실행 RUN_GAP 20분)까지 기다리면 3시간 창이 지나는 것
#       = 차례와 상관없이 이번 칸(창이 먼저 끝나는 것부터, thfill = own -> 다음 칸 토스) · 진우 딜 없거나 창 여유 있으면 예전 번갈아 그대로
sv25 = (H.http, H.POSTS, H.TH_LINK_AB, H.time.sleep, time.time, H.E.get("THREADS_TOKEN"), H.TH_SOLO_MAX, H.TH_SOLO_GAP, H.TH_SOLO_RUN, H.th_strong, H.TH_SOLO_FILL, H.TH_GAP_JITTER)
H.TH_SOLO_MAX, H.TH_SOLO_GAP, H.TH_SOLO_RUN, H.th_strong, H.TH_SOLO_FILL, H.TH_GAP_JITTER = 99, 45 * 60, 1, th_strong0, True, 10 * 60  # 실제 값(간격 흔들기 켬)
H.http, H.POSTS, H.TH_LINK_AB, H.time.sleep, H.E["THREADS_TOKEN"] = http21, "posts25.json", False, (lambda s: None), "tk"
HB25 = "🔥 [쿠팡] 하루온 붙이는 핫팩 50g 10매 × 4개 (40매, 13,370원)\n\n와우 할인 1,600원 → 1매당 334원 — 같은 상품 다른 구성보다 싸요(10매 490원 · 20매 390원 · 30매 와우 359원)\n⭐ 리뷰 52,427 · 한 달 600명 이상 구매 · 🚀 로켓배송(새벽) · 최고 63도·15시간(포장 표기)\n⚠️ 확인할 점: 와우 회원가(와우 아니면 14,970원·1매 374원) · 결제 전 최종가 확인 (10/21 19:19 가격)"
own25 = lambda mid, at, src: {"t": "2026-10-21 " + at, "url": f"https://link.coupang.com/a/W{mid}", "mid": mid, "own": 1, "text": f"{H.DISCLOSURE}\n\n{src}"}
def night25(rule_runs):  # 10/21 밤 재현: 19:43 진우 🔥 2(코멧 · 하루온 군인 = 구매 2위 ② strong) + 19:57 진우 🔥 1(하루온 붙이는) + 토스 대기 3
    json.dump([own25(2501, "19:43", K23), own25(2502, "19:43", G23), own25(2503, "19:57", HB25)], open(H.POSTS, "w"), ensure_ascii=False)
    s = {"thsolo_20261021": {"t": 1, "n": 5, "b": 0, "last": TK("2026-10-21 19:26")}, "thfill": {"t": 1, "k": "toss"},
         "thtoss": {"t": 1, "q": [tq21(1, "19:50", 0), tq21(2, "20:50", 0), tq21(3, "21:50", 0)]}}
    got, logs = {}, []
    for at in rule_runs:
        names, log = run21(s, at); logs.append((at, log))
        got.update({n: at for n in names if n.startswith("토스")})
        got.update({p["mid"]: at for p in json.load(open(H.POSTS)) if p.get("th") and p["mid"] not in got})
    return got, logs, s
runs25 = [time.strftime("%H:%M", time.gmtime(TK("2026-10-21 19:57") + 9 * 3600 + 14 * 60 * k)) for k in range(18)]  # 그날처럼 ~14분마다(19:57·20:11·…·23:55), 간격 흔들기 없음(배포 전)
H.TH_GAP_JITTER = 0; got25, logs25, s25 = night25(runs25); H.TH_GAP_JITTER = 10 * 60
assert (got25[2502], got25[2501], got25[2503]) == ("20:11", "21:07", "22:03") and all(m in got25 and got25[m] < ("22:43" if m < 2503 else "22:57") for m in (2501, 2502, 2503)), got25  # 진우 🔥 3개 다 3시간 안에(예전 = 22:03 토스 -> 22:59엔 창 끝남)
when25 = sorted(got25.values()); assert all(TK(f"2026-10-21 {b}") - TK(f"2026-10-21 {a}") >= 35 * 60 for a, b in zip(when25, when25[1:])), got25  # 개별 글 간격 35분↑ 그대로
due25 = [(at, l) for at, log in logs25 for l in log.splitlines() if "창 끝남" in l]
assert due25 == [("22:03", "threads fill turn own(창 끝남 54분 전) (대기 own 1·toss 3)")], (due25, got25)
nxt25 = min(at for at in got25.values() if at > got25[2503]) if any(at > got25[2503] for at in got25.values()) else None
assert nxt25 is None or [k for k, v in got25.items() if v == nxt25][0] in ("토스1", "토스2", "토스3"), got25  # 다음 칸 = 토스(thfill own)
assert got25[2502] == min(got25.values()), got25  # strong(② 구매 2위)은 그대로 먼저
gj25, _, _ = night25(runs25); assert all(m in gj25 and gj25[m] < ("22:43" if m < 2503 else "22:57") for m in (2501, 2502, 2503)), gj25  # 간격 흔들기 켜도 3개 다
json.dump([own25(2514, "19:50", K23)], open(H.POSTS, "w"), ensure_ascii=False)
s25 = {"thfill": {"t": 1, "k": "toss"}, "thtoss": {"t": 1, "q": [tq21(8, "21:40", 0)]}}
g25, log25 = run21(s25, "22:00"); assert g25 == ["코멧"] and "threads fill turn own (대기 own 1·toss 1)" in log25 and "창 끝남" not in log25, log25  # 원래 진우 차례면 '창 끝남' 로그 X(규칙이 차례를 바꿀 때만)
# 창 여유 있음 = 예전 번갈아 그대로(직전 채움 own -> 토스) · 진우 딜 없음 = 토스
json.dump([own25(2511, "21:30", K23)], open(H.POSTS, "w"), ensure_ascii=False)
s25 = {"thfill": {"t": 1, "k": "own"}, "thtoss": {"t": 1, "q": [tq21(4, "21:40", 0)]}}
g25, log25 = run21(s25, "22:00"); assert g25 == ["토스4"] and "threads fill turn toss (대기 own 1·toss 1)" in log25 and "창 끝남" not in log25, (g25, log25)  # 21:30 진우 딜 = 창 00:30, 22:00 + 75분 = 23:15 < 00:30
s25 = {"thfill": {"t": 1, "k": "own"}, "thtoss": {"t": 1, "q": [tq21(5, "21:40", 0)]}}
json.dump([own25(2512, "20:16", K23)], open(H.POSTS, "w"), ensure_ascii=False)
g25, log25 = run21(s25, "22:00"); assert g25 == ["토스5"] and "창 끝남" not in log25, log25  # 창 23:16 = 22:00 + 76분 > 75분 -> 아직 차례대로
s25 = {"thfill": {"t": 1, "k": "own"}, "thtoss": {"t": 1, "q": [tq21(6, "21:40", 0)]}}
json.dump([own25(2513, "20:14", K23)], open(H.POSTS, "w"), ensure_ascii=False)
g25, log25 = run21(s25, "22:00"); assert g25 == ["코멧"] and "threads fill turn own(창 끝남 74분 전) (대기 own 1·toss 1)" in log25 and s25["thfill"]["k"] == "own", log25  # 74분 < 75분 -> 이번 칸
# 여러 개 = 창이 먼저 끝나는 것부터(직전 채움이 own이어도)
json.dump([own25(2521, "19:40", G23.replace("구매 2위", "구매 9위")), own25(2522, "19:30", K23), own25(2523, "21:50", HB25)], open(H.POSTS, "w"), ensure_ascii=False)
s25 = {"thfill": {"t": 1, "k": "own"}, "thtoss": {"t": 1, "q": [tq21(7, "21:40", 0)]}}
g25, log25 = run21(s25, "22:00"); assert g25 == ["코멧"] and "threads fill turn own(창 끝남 30분 전) (대기 own 3·toss 1)" in log25, (g25, log25)
# 10/22 Cowork(실제 — 14:37 re 깨끗한나라(채널 12:29, 창 15:29)가 먼저 나가 11:47 진우 🔥 홈키파(창 14:47) Threads 못 나감): 끝나가는 진우 🔥 = re·①②·화장품보다도 먼저
#       (strong 단계 — grp -1 re보다 먼저) · re도 끝나가면 그 안에서 먼저 올라온 순 · 창 여유 있으면 re 먼저 그대로
ev25, H.EVENTS = H.EVENTS, "ev25.json"; H.TH_GAP_JITTER = 0
re25 = own25(2531, "12:29", HB25); json.dump([{"at": "2026-10-21 12:29", "url": re25["url"], "re": True, "deal": True, "text": "x"}], open("ev25.json", "w"), ensure_ascii=False)
json.dump([own25(2530, "11:47", K23), re25], open(H.POSTS, "w"), ensure_ascii=False)
s25 = {"thsolo_20261021": {"t": 1, "n": 5, "b": 0, "last": TK("2026-10-21 13:40")}, "thfill": {"t": 1, "k": "toss"}, "thtoss": {"t": 1, "q": [tq21(9, "14:00", 0)]}}
g25, log25 = run21(s25, "14:37"); assert g25 == ["코멧"] and "threads turn own(창 끝남 10분 전) — re·①②·화장품 1개 앞" in log25 and s25["thfill"]["k"] == "own", (g25, log25)  # 진우 🔥(창 10분 남음) 먼저
g25, log25 = run21(s25, "15:22"); assert g25 == ["하루온"], (g25, log25)  # 다음 칸 = re(창 15:29 — 끝나기 전에 나감)
json.dump([own25(2532, "13:30", K23), own25(2533, "13:00", HB25)], open(H.POSTS, "w"), ensure_ascii=False); json.dump([{"at": "2026-10-21 13:00", "url": "https://link.coupang.com/a/W2533", "re": True}], open("ev25.json", "w"))
s25 = {"thsolo_20261021": {"t": 1, "n": 5, "b": 0, "last": TK("2026-10-21 13:40")}, "thfill": {"t": 1, "k": "toss"}}
g25, log25 = run21(s25, "14:37"); assert g25 == ["하루온"] and "창 끝남" not in log25 and s25["thfill"]["k"] == "toss", (g25, log25)  # 진우 🔥 창 16:30(113분)·re 창 16:00(83분) 둘 다 여유 = re 먼저 그대로(채움 차례도 그대로)
json.dump([own25(2538, "13:30", K23), own25(2539, "12:29", HB25)], open(H.POSTS, "w"), ensure_ascii=False); json.dump([{"at": "2026-10-21 12:29", "url": "https://link.coupang.com/a/W2539", "re": True}], open("ev25.json", "w"))
s25 = {"thsolo_20261021": {"t": 1, "n": 5, "b": 0, "last": TK("2026-10-21 13:40")}, "thfill": {"t": 1, "k": "toss"}}
g25, log25 = run21(s25, "14:37"); assert g25 == ["하루온"] and "창 끝남" not in log25 and s25["thfill"]["k"] == "toss", (g25, log25)  # re만 끝나감(창 15:29) = 원래도 맨 먼저 -> 순서 그대로면 로그·채움 차례 X
json.dump([own25(2534, "11:47", K23), own25(2535, "11:40", HB25)], open(H.POSTS, "w"), ensure_ascii=False); json.dump([{"at": "2026-10-21 11:40", "url": "https://link.coupang.com/a/W2535", "re": True}], open("ev25.json", "w"))
s25 = {"thsolo_20261021": {"t": 1, "n": 5, "b": 0, "last": TK("2026-10-21 13:40")}}
g25, log25 = run21(s25, "14:30"); assert g25 == ["하루온"] and "창 끝남" not in log25, (g25, log25)  # re도 끝나감(창 14:40) = 먼저 올라온 순(re 11:40 → 진우 🔥 11:47 — re가 원래도 맨 먼저라 로그 X)
g25, log25 = run21(s25, "15:15"); assert g25 == [], (g25, log25)  # (진우 🔥 창 14:47 이미 지남 — 이 경우 둘 다 못 살림: 같은 칸 1개)
json.dump([own25(2536, "11:47", K23), own25(2537, "11:50", G23)], open(H.POSTS, "w"), ensure_ascii=False); json.dump([], open("ev25.json", "w"))
s25 = {"thsolo_20261021": {"t": 1, "n": 5, "b": 0, "last": TK("2026-10-21 13:40")}}
g25, log25 = run21(s25, "14:37"); assert g25 == ["코멧"] and "re·①②·화장품 1개 앞" in log25, (g25, log25)  # ②(구매 2위) 진우 딜도 창 14:50 — 먼저 올라온 진우 🔥(14:47)부터
json.dump([own25(2540, "13:00", G23), own25(2541, "11:40", K23)], open(H.POSTS, "w"), ensure_ascii=False); json.dump([{"at": "2026-10-21 11:40", "url": "https://link.coupang.com/a/W2541", "re": True}, {"at": "2026-10-21 13:00", "url": "https://link.coupang.com/a/W2540", "re": True}], open("ev25.json", "w"))
s25 = {"thsolo_20261021": {"t": 1, "n": 5, "b": 0, "last": TK("2026-10-21 13:40")}, "thfill": {"t": 1, "k": "toss"}}
g25, log25 = run21(s25, "14:30"); assert g25 == ["코멧"] and "창 끝남 10분 전" in log25 and s25["thfill"]["k"] == "toss", (g25, log25)  # 끝나가는 re(11:40)가 다른 re(②) 앞으로 = 채움 차례(진우 🔥 다음)는 그대로(리뷰)
json.dump([own25(2542, "11:47", K23), own25(2543, "11:47", G23)], open(H.POSTS, "w"), ensure_ascii=False); json.dump([], open("ev25.json", "w"))
s25 = {"thsolo_20261021": {"t": 1, "n": 5, "b": 0, "last": TK("2026-10-21 13:40")}}
g25, log25 = run21(s25, "14:37"); assert g25 == ["하루온"] and "창 끝남" not in log25, (g25, log25)  # 같은 분에 끝나가는 진우 딜 2개 = 강한 후보(② 구매 2위) 먼저(posts.json 순서 상관없이 — 리뷰)
# 9-31 👍 꾸준템 Threads: 개별 글 O(수수료 링크만 — 그대로) · 🔥(강한 후보·채움) 다 나간 뒤 · 끝나가는 칸 X(👍는 놓치면 다음 날) · 강한 후보(②·화장품 자리) X
ST25 = "👍 [쿠팡] 록시땅 시어 버터 핸드크림 75ml (25,800원)\n\n한 달 1,000명+ 구매 · 리뷰 1,969 · 손/발 크림 판매 2위\n🎁 백화점 선물 포장"
json.dump([own25(2550, "13:00", ST25), own25(2551, "13:30", K23)], open(H.POSTS, "w"), ensure_ascii=False); json.dump([], open("ev25.json", "w"))
s25 = {"thsolo_20261021": {"t": 1, "n": 5, "b": 0, "last": TK("2026-10-21 13:40")}, "thfill": {"t": 1, "k": "toss"}}
g25, log25 = run21(s25, "14:37"); assert g25 == ["코멧"] and "창 끝남" not in log25, (g25, log25)  # 👍(먼저 올라옴·'판매 2위'·화장품)보다 🔥 먼저
g25, log25 = run21(s25, "15:30"); assert g25 == ["록시땅"] and p21[0].startswith(H.th_note(H.DISCLOSURE) + "👍 [쿠팡] 록시땅"), (g25, p21)  # 🔥 다 나간 뒤 = 👍(진우 채움 칸)
json.dump([own25(2552, "12:00", ST25)], open(H.POSTS, "w"), ensure_ascii=False)
s25 = {"thsolo_20261021": {"t": 1, "n": 5, "b": 0, "last": TK("2026-10-21 13:40")}, "thfill": {"t": 1, "k": "own"}, "thtoss": {"t": 1, "q": [tq21(10, "14:00", 0)]}}
g25, log25 = run21(s25, "14:37"); assert g25 == ["토스10"] and "창 끝남" not in log25, (g25, log25)  # 👍 창 15:00(23분 남음)이어도 끝나가는 칸 X -> 차례대로 토스
os.remove("ev25.json"); H.EVENTS = ev25
os.remove("posts25.json")
(H.http, H.POSTS, H.TH_LINK_AB, H.time.sleep, time.time, tk25, H.TH_SOLO_MAX, H.TH_SOLO_GAP, H.TH_SOLO_RUN, H.th_strong, H.TH_SOLO_FILL, H.TH_GAP_JITTER) = sv25
H.E.pop("THREADS_TOKEN", None) if tk25 is None else H.E.update(THREADS_TOKEN=tk25)
# 9-26 (10/22 07:2x 진우 '핫딜은 새벽에도 올라가게, 밤에 안 올리니까 너무 조용해'): 0~8시도 토스 매시 개별 1개(TOSS_SOLO_HOURS 0~23) · 토스 빈틈 채움 밤 60분(낮 30분 그대로)
#       · 커뮤니티 6점 빈틈 채움(quiet) 밤 GAP_FILL × 2 · 밤 발송 무음 그대로 · Threads 개별 글은 밤에도 간격대로 후보 꺼냄
assert tsh0 == range(0, 24) and (tgm0, H.TOSS_GAP_NIGHT, H.GAP_FILL) == (30, 60, 45)
sv26 = (H.http, H.tg, H.ai_pick, H.EVENTS, time.time, H.HAS_TOSS, H.POSTS, H.TOSS_NO_CMP, H.TOSS_SOLO_HOURS, H.TOSS_GAP_MIN)
H.TOSS_SOLO_HOURS, H.TOSS_GAP_MIN = tsh0, tgm0  # 실제 값
tg26 = []
def http26(url, body=None, headers=None, method=None):
    if "api.telegram.org" in url: tg26.append((url.rsplit("/", 1)[-1], body)); return json.dumps({"ok": True, "result": {"message_id": 800 + len(tg26)}})
    return i_http(url, body, headers, method)
H.http, H.tg, H.HAS_TOSS, H.EVENTS, H.POSTS, H.TOSS_NO_CMP = http26, tg_real, True, "ev26.json", "posts26.json", True
H.ai_pick = lambda prompt, lines: [{"i": 0, "score": 8, "comment": "롤당 330원"}]
json.dump([], open("ev26.json", "w")); json.dump([], open("posts26.json", "w"))
def solo26(at, last, hourly_done=True):  # 마지막 채널 딜 글 last분 전 · 그 시각 매시 1개는 이미(빈틈 채움만 봄)
    tg26.clear(); H.RUN["ch_last"] = 0; time.time = lambda: TK("2026-10-22 " + at)
    s = {"ch_last": {"t": TK("2026-10-22 " + at) - last * 60}, **({f"tsolo_20261022_{at[:2]}": 1} if hourly_done else {})}
    H.toss_solo(s); return [b for m, b in tg26 if m == "sendMessage" and b.get("chat_id") == H.CHANNEL]
for at, last, n in (("03:00", 70, 1), ("05:30", 70, 1), ("03:00", 40, 0), ("03:00", 59, 0), ("14:07", 35, 1), ("14:07", 25, 0)):  # 밤 60분 · 낮 30분 그대로
    got = solo26(at, last); assert len(got) == n, (at, last, got)
    assert all(b["disable_notification"] is True for b in got) if at < "08" else all("disable_notification" not in b for b in got), got  # 밤 글 = 무음 그대로
got = solo26("02:05", 10, hourly_done=False); assert len(got) == 1 and got[0]["disable_notification"] is True and "💙 토스 특가" in got[0]["text"]  # 0~8시도 매시 1개(무음)
for ev_at, want in (("2026-10-22 23:40", "베스트2"), ("2026-10-21 23:00", "베스트1")):  # 밤 12시 넘어도 지난 24시간 진우 예약 상품은 뺌(10/22 리뷰) — 24시간 넘은 예약은 그대로 후보
    json.dump([{"at": ev_at, "deal": True, "name": "베스트1", "url": "https://toss.shopping/_m/j"}], open("ev26.json", "w"), ensure_ascii=False)
    tg26.clear(); H.RUN["ch_last"] = 0; time.time = lambda: TK("2026-10-23 00:05"); H.toss_solo({})
    got = [b for m, b in tg26 if m == "sendMessage" and b.get("chat_id") == H.CHANNEL]; assert len(got) == 1 and f"<b>{want}</b>" in got[0]["text"], (ev_at, got)
json.dump([], open("ev26.json", "w"))
for at, ago, want in (("03:00", 80, False), ("03:00", 100, True), ("14:00", 40, False), ("14:00", 50, True)):  # 커뮤니티 6점 빈틈 채움: 밤 90분 · 낮 45분 그대로
    time.time = lambda: TK("2026-10-22 " + at)
    json.dump([{"t": time.strftime("%Y-%m-%d %H:%M", time.gmtime(TK("2026-10-22 " + at) + 9 * 3600 - ago * 60)), "text": "🔥 [쿠팡] 휴지"}], open("posts26.json", "w"), ensure_ascii=False)
    assert H.quiet() is want, (at, ago)
# Threads 개별 글: 밤에도 간격대로 토스 픽 대기 줄에서 꺼냄(시각 제한 없음)
sv26b = (H.http, H.POSTS, H.TH_LINK_AB, H.time.sleep, H.E.get("THREADS_TOKEN"), H.TH_SOLO_MAX, H.TH_SOLO_GAP, H.TH_SOLO_RUN, H.th_strong, H.TH_SOLO_FILL)
H.TH_SOLO_MAX, H.TH_SOLO_GAP, H.TH_SOLO_RUN, H.th_strong, H.TH_SOLO_FILL = 99, 45 * 60, 1, th_strong0, True
H.http, H.TH_LINK_AB, H.time.sleep, H.E["THREADS_TOKEN"] = http21, False, (lambda s: None), "tk"; json.dump([], open("posts26.json", "w"))
s26 = {"thsolo_20261021": {"t": 1, "n": 3, "b": 0, "last": TK("2026-10-21 02:10")}, "thtoss": {"t": 1, "q": [tq21(9, "02:30", 0)]}}
assert run21(s26, "02:40")[0] == [] and run21(s26, "03:00")[0] == ["토스9"], s26  # 02:10 글 뒤 30분 = 아직 · 50분 = 꺼냄
trn26, (H.TH_REOPEN_NIGHT, H.TH_REOPEN_MORN, H.TH_REOPEN_DAY) = (H.TH_REOPEN_NIGHT, H.TH_REOPEN_MORN, H.TH_REOPEN_DAY), trn0  # 실제 재오픈 한도
for at, rn, st, want in (("00:50", 0, 0, []), ("00:50", 0, 1, ["토스10"]), ("00:50", 2, 0, ["토스10"]), ("06:50", 0, 0, ["토스10"])):  # 밤 재오픈이 기다리면 토스 픽 칸은 비워 둠(10/22 리뷰) — 다 봤거나·밤 한도 찼거나·아침이면 예전 그대로
    s26 = {"thsolo_20261021": {"t": 1, "n": 1, "b": 0, "rn": rn, "last": TK(f"2026-10-21 {at}") - 50 * 60}, "thtoss": {"t": 1, "q": [tq21(10, f"{at[:2]}:20", 0)]}, "reopen": {"q": [{"id": 1, "st": st, "day": "2026-10-21"}]}}
    assert run21(s26, at)[0] == want, (at, rn, st)
(H.TH_REOPEN_NIGHT, H.TH_REOPEN_MORN, H.TH_REOPEN_DAY) = trn26
(H.http, H.POSTS, H.TH_LINK_AB, H.time.sleep, tk26, H.TH_SOLO_MAX, H.TH_SOLO_GAP, H.TH_SOLO_RUN, H.th_strong, H.TH_SOLO_FILL) = sv26b
H.E.pop("THREADS_TOKEN", None) if tk26 is None else H.E.update(THREADS_TOKEN=tk26)
def http26r(url, body=None, headers=None, method=None):  # 재오픈 상품 상세(살 수 있음·같은 가격)
    if "/products/detail?" in url: return json.dumps({"resultType": "SUCCESS", "success": {"items": [{"tacaItemId": 77, "displayName": "리오픈77", "displayPrice": 9000, "isSoldOut": False}], "notFoundIds": []}})
    return http26(url, body, headers, method)
H.http, H.E["THREADS_TOKEN"], ths26, H.th_strong = http26r, "tk", H.th_strong, th_strong0; time.time = lambda: TK("2026-10-22 00:30"); tg26.clear()  # 진짜 ①② 판단
s26 = {"reopen": {"q": [{"id": 77, "day": "2026-10-22", "st": 0, "p0": 9000, "url": "https://toss.shopping/_m/R77", "n": "리오픈77", "title": "리오픈77", "icon": "🔥", "cmp": "", "warn": ""}], "ts": []}}
H.toss_reopen(s26); assert s26["reopen"]["q"][0]["st"] == 1 and not any("threads" in m for m, _ in tg26), s26  # 밤 ①② 아님 = 아침에 다시(밤새 토스 픽 칸을 막지 않게)
H.http, H.th_strong = http26, ths26; H.E.pop("THREADS_TOKEN", None) if tk26 is None else H.E.update(THREADS_TOKEN=tk26)
os.remove("ev26.json"); os.remove("posts26.json")
(H.http, H.tg, H.ai_pick, H.EVENTS, time.time, H.HAS_TOSS, H.POSTS, H.TOSS_NO_CMP, H.TOSS_SOLO_HOURS, H.TOSS_GAP_MIN) = sv26
# 9-27 (10/22 진우 '투표 재미있게' + 저녁 9시대): Claude가 품목 투표 질문·보기 4개를 반말로(글마다 무작위 가 생활형 / 나 가격형 — 가격 숫자는 poll_opts 구간 값만),
#       검사(질문 60자·보기 4개 1~25자·~요 X·몰·브랜드·링크 X·없는 금액 X) 실패 -> 1번 다시 -> 그래도면 지금 틀 · 결과 답글 '어제 1등은 "…" N% ㅋㅋ'(0표 = '아무도 안 찍음') · 21:40
assert pl0 == (21, 40)
P27 = P13b + [p13("2026-10-16 10:00", "[쿠팡] 삼다수 2L 12개 (12,000원)", "1L당 500원")]
r27 = S13.price_records(P27); assert set(r27) == {"ramen", "toilet-paper", "water"}, list(r27)
a27, pr27, ST27 = [], [], []
class R27:
    choice = staticmethod(lambda xs: ST27.pop(0))
sv27 = (H.ai_json, H.random)
H.ai_json, H.random = (lambda prompt, props: pr27.append((prompt, props)) or (lambda a: (_ for _ in ()).throw(a) if isinstance(a, Exception) else a)(a27.pop(0))), R27
def poll27(k, kind, *ans):
    a27[:], ST27[:] = list(ans), [kind]; pr27.clear(); return H.poll_ai(r27[k])
TAIL27 = "\n\n내일 이 시간에 답글로 핫딜픽 기록 최저가 알려줌"
o1 = poll27("ramen", "life", {"q": "라면 쟁이는 스타일 골라봐", "opts": ["박스째 쌓아둠", "5개입 하나면 충분", "땡길 때 편의점 직행", "라면 끊음 (진짜임)"]})
assert o1 == ("🗳️ 라면 쟁이는 스타일 골라봐" + TAIL27, ["박스째 쌓아둠", "5개입 하나면 충분", "땡길 때 편의점 직행", "라면 끊음 (진짜임)"]) and "생활형" in pr27[0][0] and "품목: 라면" in pr27[0][0], (o1, pr27)
oa = H.poll_opts(r27["toilet-paper"][2][0][0]); n27 = [re.match(r"[\d,]+원", x)[0] for x in oa[:3]]
o2 = poll27("toilet-paper", "price", {"q": "화장지 롤당, 얼마면 \"오 싸다\" 해?", "opts": [f"{n27[0]}이면 바로 삼", f"{n27[1]}까진 OK", f"{n27[2]} 넘으면 고민", "가격 안 보고 집음"]})
assert o2[0] == "🗳️ 화장지 롤당, 얼마면 \"오 싸다\" 해?" + TAIL27 and o2[1][0] == f"{n27[0]}이면 바로 삼" and "가격형" in pr27[0][0] and ", ".join(oa[:3]) in pr27[0][0], (o2, pr27[0][0])
assert f"예: 화장지 롤당, 얼마면 \"오 싸다\" 해? / {n27[0]}이면 바로 삼 · {n27[1]}까진 OK · {n27[2]} 넘으면 고민" in pr27[0][0] and "까지까진" not in pr27[0][0], pr27[0][0]  # 예시 = 숫자만(10/22 리뷰)
o3 = poll27("water", "life", {"q": "물 떨어지면 어떻게 함?", "opts": ["2L 6개 바로 주문", "수돗물 끓여 먹음", "편의점 생수로 버팀", "콜라로 대체 (진짜임)"]})
assert o3[0] == "🗳️ 물 떨어지면 어떻게 함?" + TAIL27 and len(o3[1]) == 4
for t, opts in (o1, o2, o3):  # 보기 4개·25자 이하·~요 0·대가성 문구·링크 X
    assert len(opts) == 4 and all(1 <= len(o) <= 25 for o in opts) and not any(re.search(H.VOICE_YO, x) for x in opts + [t]) and "http" not in t and not t.startswith(H.NOTE_STARTS), (t, opts)
assert pr27[0][1] == {"q": {"type": "string"}, "opts": {"type": "array", "items": {"type": "string"}}}
GOOD27 = {"q": "라면 쟁이는 스타일 골라봐", "opts": ["박스째 쌓아둠", "5개입 하나면 충분", "땡길 때 편의점 직행", "라면 끊음 (진짜임)"]}
o4 = poll27("ramen", "life", {"q": "라면 쟁이는 스타일 골라봐요", "opts": GOOD27["opts"]}, GOOD27)
assert o4[1] == GOOD27["opts"] and len(pr27) == 2 and "다시: '라면 쟁이는 스타일 골라봐요' ~요로 끝남" in pr27[1][0], pr27  # ~요 -> 걸린 말 알려 주고 1번 다시
poll27("ramen", "life", {"q": "라면 쟁이는 스타일 골라봐", "opts": ["신라면 박스째", "b", "c", "d"]}, GOOD27); assert "'신라면' 쓰면 안 됨" in pr27[1][0], pr27[1][0]
FP27 = {"q": "라면 먹는 스타일 골라봐", "opts": ["국내산 김치랑 먹음", "계란 토스트랑 먹음", "참치마요 섞어 먹음", "요 정도면 이건 아니다"]}
assert poll27("ramen", "life", FP27)[1] == FP27["opts"] and len(pr27) == 1  # 흔한 말(국내산·토스트·참치마요·요 정도·아니다)은 통과(10/22 리뷰)
OLD27 = H.poll_text(r27["ramen"])
for bad in ({"q": "라면 쟁이는 스타일 골라봐", "opts": ["가" * 26, "b", "c", "d"]}, {"q": "라면 쟁이는 스타일 골라봐", "opts": ["a", "b", "c"]},  # 26자 · 보기 3개
            {"q": "라면 쟁이는 스타일 골라봐", "opts": ["신라면 박스째", "b", "c", "d"]}, {"q": "쿠팡에서 라면 사는 스타일", "opts": ["a", "b", "c", "d"]},  # 브랜드(기록 딜 상품명) · 몰
            {"q": "라면 쟁이는 스타일 골라봐", "opts": ["a", "b", "c", "hotdealpick.kr 봄"]}, {"q": "라면 쟁이는 스타일 골라봐", "opts": ["500원이면 삼", "b", "c", "d"]},  # 링크 · 생활형에 금액
            {"q": "라" * 61, "opts": ["a", "b", "c", "d"]}, {"q": "라면 쟁이는 스타일 골라봐", "opts": ["박스째 쌓아둬요", "b", "c", "d"]}):  # 질문 61자 · ~요
    assert poll27("ramen", "life", bad, bad) == OLD27 and len(pr27) == 2, bad  # 2번 다 = 지금 틀
assert poll27("ramen", "price", {"q": "라면 개당 얼마면 오 싸다 해?", "opts": ["450원이면 삼", "b", "c", "d"]}, {"q": "x", "opts": ["450원", "b", "c", "d"]}) == OLD27  # 가격형 = 구간 값만(450원 X)
assert poll27("ramen", "price", {"q": "라면 개당 얼마면 오 싸다 해?", "opts": ["500원 이하면 바로 삼", "600원까진 OK", "700원 넘으면 고민", "가격 안 봄"]})[1][0] == "500원 이하면 바로 삼"  # 구간 값 = OK
assert poll27("ramen", "life", RuntimeError("api")) == OLD27  # Claude 실패 = 지금 틀
assert H.wons("5천원대면 바로 삼 · 1만2천원 · 1,500원 · 30개") == {5000, 12000, 1500}
H.random = sv27[1]; k27 = set()  # 진짜 무작위: 가·나 둘 다
for n in range(30):
    a27[:] = [GOOD27]; pr27.clear(); H.poll_ai(r27["ramen"]); k27.add("life" if "생활형" in pr27[0][0] else "price")
assert k27 == {"life", "price"}, k27
# 결과 답글: 1표 / 0표
R1 = H.poll_reply_text("ramen", r27["ramen"], {"option_a": "박스째 쌓아둠", "option_b": "5개입 하나면 충분", "option_a_votes_percentage": 1.0, "option_b_votes_percentage": 0, "total_votes": 1})
assert R1.startswith(H.th_note(H.DISCLOSURE) + '📊 어제 1등은 "박스째 쌓아둠" 100% ㅋㅋ\n쟁일 거면 이 가격은 알아두자 → 핫딜픽 기록 최저 라면 개당 480원 (10/12)\n\n👉 https://hotdealpick.kr/c/ramen.html?ref=th'), R1
R0 = H.poll_reply_text("ramen", r27["ramen"], {"option_a": "박스째 쌓아둠", "option_a_votes_percentage": 0, "total_votes": 0})
assert '📊 어제는 아무도 안 찍음 ㅋㅋ 그래도 알려줌\n쟁일 거면 이 가격은 알아두자 → 핫딜픽 기록 최저 라면 개당 480원 (10/12)\n' in R0 and H.poll_reply_text("ramen", r27["ramen"], None) == R0 and len(R0) <= 480
# 21:40 회차: 21:35 X · 21:41 투표(Claude 글) · 다음 날 21:41 결과 답글 먼저
json.dump(P27, open("posts.json", "w"), ensure_ascii=False); H.random = R27
sv27b = (H.http, H.th_reply, H.th_reply_ok, H.busy, H.time.sleep, time.time, H.TH_SOLO_GAP, H.POLL_HOUR); H.TH_SOLO_GAP, H.POLL_HOUR = 45 * 60, pl0
H.http, H.time.sleep, H.busy, H.E["THREADS_TOKEN"] = http13, (lambda s: None), (lambda seen, cap=True: False), "tk"; rp13.clear()
H.th_reply, H.th_reply_ok = (lambda tok, to, text: rp13.append((to, text)) or "r1"), (lambda seen: True)
c13h.clear(); s27 = {}; time.time = lambda: TK("2026-10-22 21:35"); H.poll_post(s27); assert not c13h and not s27
H.busy = lambda seen, cap=True: cap  # 채널 시간당 상한에만 걸린 저녁 = 그래도 투표(묶음 간격 10분은 봄)
os.makedirs("docs/cards", exist_ok=True); open("docs/cards/2026-10-22.png", "wb").close(); a27[:], ST27[:] = [GOOD27], ["life"]; time.time = lambda: TK("2026-10-22 21:41")
H.poll_post(s27); assert not [x for x in c13h if "/me/threads?" in x[0]] and "poll_20261022" not in s27  # 21시 카드가 아직 Threads에 안 나감 = 기다림
s27["threads_20261022"] = TK("2026-10-22 21:36"); H.poll_post(s27); assert not [x for x in c13h if "/me/threads?" in x[0]]  # 카드 5분 뒤 = 아직(10분)
s27 = {"threads_20261022": TK("2026-10-22 21:30")}; os.remove("docs/cards/2026-10-22.png")
a27[:], ST27[:] = [GOOD27], ["life"]; time.time = lambda: TK("2026-10-22 21:41"); H.poll_post(s27)
q27 = [x for x in c13h if "/me/threads?" in x[0]][0]
assert parse_qs(urlsplit(q27[0]).query)["text"] == ["🗳️ 라면 쟁이는 스타일 골라봐" + TAIL27] and json.loads(parse_qs(q27[1].decode())["poll_attachment"][0]) == dict(zip(H.POLL_KEYS, GOOD27["opts"])) and s27["polls"]["open"]["slug"] == "ramen"
c13h.clear(); a27[:], ST27[:] = [GOOD27], ["life"]; time.time = lambda: TK("2026-10-23 21:41"); H.poll_post(s27)
assert len(rp13) == 1 and rp13[0][0] == "pol1" and '📊 어제 1등은 "600원까지" 50% ㅋㅋ' in rp13[0][1], rp13  # 다음 날 같은 회차에 결과 답글(가짜 API 결과 = 600원까지 50%)
del H.E["THREADS_TOKEN"]; (H.http, H.th_reply, H.th_reply_ok, H.busy, H.time.sleep, time.time, H.TH_SOLO_GAP, H.POLL_HOUR) = sv27b; (H.ai_json, H.random) = sv27; json.dump([], open("posts.json", "w"))
# 9-28 (10/22 10:3x 진우 '토스 글과 쿠팡 글을 한눈에 — 색·내용 둘 다'): 토스 = 💙 '오늘의 토스 특가'(머리 줄 출처 → 상품명 → 가격 (할인%↓) · ⭐ → 🙋 → 게시 시점, 버튼 '💙 토스에서 N원'),
#       쿠팡 = 🚀 '로켓 가격 비교'(머리 줄 각도 → 상품명 → 가격 → 단위가격 → 📊 참고 · 🚚 도착 · ⚠️ 결제 전 최종가, 버튼 '🚀 쿠팡에서 N원'·'… 보기'), 토스 목록 머리 💙,
#       Threads = 대가성 문구 다음 같은 머리 줄(th_voice도 고정 줄, 몰별 결). 저장 글(posts.json)도 새 틀 -> split_title이 '[몰] 상품명 (가격)'으로 읽음(사이트·카드·리스트 그대로)
sv28 = (H.tg, H.EVENTS, time.time, H.TOSS_NO_CMP, H.toss, H.ai_pick, H.HAS_TOSS, H.TOSS_SOLO_HOURS, H.TOSS_GAP_MIN, H.E.get("THREADS_TOKEN"))
H.TOSS_NO_CMP, s28 = True, []
TOSS28 = H.mall_body("toss", "생필품 베스트 3위", "🔥", "더건강플러스 올리브오일 1L", H.toss_price({"displayPrice": 15580, "discountRate": 60, "reviewScore": 4.7, "reviewCount": 11683}), ["🙋 집밥 자주 하는 집", H.toss_when("2026-10-22 09:54")])
assert TOSS28 == "💙 토스 특가 · 생필품 베스트 3위 🔥\n<b>더건강플러스 올리브오일 1L</b>\n15,580원 (60%↓) · ⭐ 4.7 (11,683)\n🙋 집밥 자주 하는 집\n⚠️ 10/22 09:54 게시 시점 가격", TOSS28  # 진우 시안 그대로
assert H.mall_btn("toss", "15,580원") == "💙 토스에서 15,580원" and H.mall_btn("coupang", "8,860원/무료") == "🚀 쿠팡에서 8,860원" and H.mall_btn("coupang", "") == "🚀 쿠팡에서 보기"
CP28 = "🚀 쿠팡 로켓 · 1개당 최저 🔥\n<b>코멧 손난로 100g 30개</b>\n8,860원 → 1개 295원\n📊 참고: 충성 317원 · 해피데이 373원\n🚚 내일(금) 도착 · 무료반품\n⚠️ 결제 전 최종가 (10/22 10시)"  # Cowork가 쓸 새 틀(진우 시안)
for body, mall, title in ((TOSS28, "토스", "[토스] 더건강플러스 올리브오일 1L (15,580원)"), (CP28, "쿠팡", "[쿠팡] 코멧 손난로 100g 30개 (8,860원)")):
    pl = H.plain_of(f"<i>{H.TOSS_NOTE}</i>\n\n{body}")
    assert H.title_of(pl) == title and H.parse(title)[0] == mall and not H.th_weak(pl) and H.buy_btn(title, "x") == ("💙 토스에서 15,580원" if mall == "토스" else "🚀 쿠팡에서 8,860원"), (pl, H.title_of(pl))
    assert H.comment_of(pl).split("\n")[0] in ("🙋 집밥 자주 하는 집", "📊 참고: 충성 317원 · 해피데이 373원")  # 제목 세 줄 아래 = 본문
assert H.is_toss("", H.plain_of(TOSS28)) and not H.is_toss("", H.plain_of(CP28)) and H.th_tier(H.plain_of(TOSS28)) == 2  # 머리 줄 출처 '생필품 베스트 3위' = ②(순위 3위 안)
W28 = H.plain_of(H.mall_body("coupang", "", "🛒", "약한 키보드", "77,900원", ["🤔 솔직히 특가는 아니에요"]))
assert H.th_weak(W28) and H.title_of(W28) == "[쿠팡] 약한 키보드 (77,900원)" and not H.th_weak("💙 토스 특가 🔥\n이름\n1원") and H.MALL_HEAD.fullmatch("💙 토스 특가 · 🔔 다시 열렸어요 🔥")
# 가격 줄 배송 조각은 제목 '/배송'으로(카드 배송 칸) · 셋째 줄이 없으면 예전처럼 첫 줄이 제목 · 상품명에 다른 몰 이름이 있어도 토스 비교 빼기(strip_cmp)가 제목 세 줄은 안 건드림
assert H.title_of("🚀 쿠팡 로켓 🔥\n휴지\n9,900원 → 1롤 330원 · 무료") == "[쿠팡] 휴지 (9,900원/무료)" and H.title_of("🚀 쿠팡 로켓 🔥\n휴지") == "쿠팡 로켓 🔥"
OY28 = "💙 토스 특가 🔥\n<b>올리브영 단독 기획 크림</b>\n9,900원\n💡 쿠팡 같은 상품보다 1,000원 쌈\n⚠️ 확인할 점 쿠팡 대비 싸요"
assert H.strip_cmp(OY28)[0] == "💙 토스 특가 🔥\n<b>올리브영 단독 기획 크림</b>\n9,900원", H.strip_cmp(OY28)  # 비교 줄만 빠짐
# 머리 줄 칸(글로만 아는 딜): 쿠팡 = 같은 상품 최저 > 1개당 최저 > 와우 할인 > 30일 최저가 > 순위 > 할인('정가 기준' X) · 토스 = 순위 > 하루특가 > 30일 최저가 > 할인
assert [H.mall_src("coupang", t, ti) for t, ti in (("네이버 같은 상품보다 2,000원 쌈", ""), ("로켓 100g 중 1개당 가장 싸요", ""), ("와우 회원 기준", ""), ("x", "[쿠팡와우] 우유"),
                                                   ("30일 내 최저가", ""), ("손난로/핫팩 구매 8위", ""), ("22% 할인", ""), ("'22% 할인'은 정가 기준", ""), ("그냥 좋음", ""))] == \
    ["같은 상품 최저", "1개당 최저", "와우 할인", "와우 할인", "30일 최저가", "손난로/핫팩 구매 8위", "22% 할인", "", ""]
assert [H.mall_src("toss", t) for t in ("10/13 밤 토스 많이 팔린 순위 3위 · 30일 내 최저가", "토스 하루특가 딜", "30일 최저가", "61% 할인", "뽐뿌에서 지금 많이 보는 글 1위")] == \
    ["30일 최저가", "하루특가", "30일 최저가", "61% 할인", ""]  # 커뮤니티 조회 순위는 상품 순위 아님 · 지난 날('10/13 밤') 순위는 X(10/22 리뷰)
# 진우 예약(events.json): Cowork 새 틀 = 그대로 + 🛒 버튼은 몰별로 · 예전 틀 = 보낼 때 몰별 틀로(mall_view) · 네이버·딜 아닌 글 = 그대로
H.EVENTS = "ev28.json"; json.dump([], open("posts.json", "w"))
json.dump([{"at": "2026-10-22 10:00", "button": "🛒 구매하러 가기", "url": "https://link.coupang.com/a/c28", "deal": True, "text": CP28},
           {"at": "2026-10-22 10:05", "button": "🛒 구매하러 가기", "url": "https://link.coupang.com/a/o28", "deal": True,
            "text": "🔥 <b>[쿠팡] 하루온 군인핫팩 160g, 30개 (13,520원)</b>\n\n로켓배송 160g 중 1개당 가장 싸요\n⭐ 리뷰 10,548 · 🚀 로켓배송(새벽)\n⚠️ 확인할 점: 결제 전 최종가 확인 (10/22 10시 가격)"},
           {"at": "2026-10-22 10:10", "button": "🛒 15,580원 구매하기", "url": "https://toss.shopping/_m/t28", "deal": True, "name": "더건강플러스 올리브오일 1L", "text": TOSS28},
           {"at": "2026-10-22 10:15", "button": "🛒 구매하러 가기", "url": "https://naver.me/n28", "deal": True, "text": "🔥 <b>[네이버] 샴푸 (9,000원)</b>\n\n좋음"},
           {"at": "2026-10-22 10:16", "button": "🛒 쿠팡 바로가기", "url": "https://link.coupang.com/a/e28", "text": "🎉 <b>쿠팡 행사</b>"}], open(H.EVENTS, "w"), ensure_ascii=False)
H.tg = lambda m, **p: s28.append((m, p)) or {"message_id": 2800 + len(s28), "text": H.plain_of(p.get("text", "")), "entities": []}
seen28 = {}; time.time = lambda: TK("2026-10-22 10:20"); H.events(seen28)
e28 = [p for m, p in s28 if m == "sendMessage"]
assert [p["reply_markup"]["inline_keyboard"][0][0]["text"] for p in e28] == ["🚀 쿠팡에서 8,860원", "🚀 쿠팡에서 13,520원", "💙 토스에서 15,580원", "🛒 구매하러 가기", "🛒 쿠팡 바로가기"], e28
assert e28[0]["text"] == f"<i>{H.DISCLOSURE}</i>\n\n{CP28}" and e28[2]["text"] == f"<i>{H.TOSS_NOTE}</i>\n\n{TOSS28}" and e28[3]["text"].endswith("🔥 <b>[네이버] 샴푸 (9,000원)</b>\n\n좋음")
assert e28[1]["text"] == f"<i>{H.DISCLOSURE}</i>\n\n🚀 쿠팡 로켓 · 1개당 최저 🔥\n<b>하루온 군인핫팩 160g, 30개</b>\n13,520원\n로켓배송 160g 중 1개당 가장 싸요\n⭐ 리뷰 10,548 · 🚀 로켓배송(새벽)\n⚠️ 확인할 점: 결제 전 최종가 확인 (10/22 10시 가격)", e28[1]["text"]  # 예전 틀 -> 몰별 틀(결제 전 줄이 이미 있으면 안 더함)
assert seen28["sold_2803"]["body"] == TOSS28 and seen28["sold_2803"]["btn"] == "💙 토스에서 15,580원" and seen28["sold_2803"]["p"] == 15580  # 품절 지켜보기 = 나간 본문·버튼(품절 고칠 때 예전 틀로 안 돌아감)
pj28 = json.load(open("posts.json"))
assert [H.title_of(p["text"]) for p in pj28] == ["[쿠팡] 코멧 손난로 100g 30개 (8,860원)", "[쿠팡] 하루온 군인핫팩 160g, 30개 (13,520원)", "[토스] 더건강플러스 올리브오일 1L (15,580원)", "[네이버] 샴푸 (9,000원)"]
nd28 = H.night_deals({}, "2026-10-22 09:00", "2026-10-22 11:00")  # 22시 미리보기도 새 틀에서 이름·가격
assert [(d["name"], d["price"], d["icon"]) for d in nd28][:3] == [("코멧 손난로 100g 30개", "8,860원", "🔥"), ("하루온 군인핫팩 160g, 30개", "13,520원", "🔥"), ("더건강플러스 올리브오일 1L", "15,580원", "🔥")], nd28
assert H.ev_view({"deal": True, "url": "https://link.coupang.com/a/w", "button": "🛒 구매하러 가기", "text": "🛒 <b>[쿠팡] 약한 상품 (1,000원)</b>\n\n🤔 솔직히 특가로는 약한 제품"})[0].startswith("📦 쿠팡 🛒\n<b>약한 상품</b>\n1,000원\n🤔")  # 약한 딜 = 각도 칸 없이 🛒
# 9-31 (10/22 20:0x 진우 '최저가 아니어도 꾸준히 팔리는 제품' -> 👍 꾸준템): 예약 글 첫 글자 👍 = '🚀 쿠팡 · 꾸준히 팔리는 상품 👍'(로켓 근거면 '🚀 쿠팡 로켓 · …') / 상품명 /
#       '가격 · 한 달 N명+ 구매 · 리뷰 N'(글에 있는 숫자만, 그 숫자만 있던 줄은 뺌) · 참고 줄 그대로 · 버튼 🚀 쿠팡에서 N원 · 토스 👍 = 그대로 · 제목·약한 딜·[광고] 첫 줄·미리보기
ST31 = {"deal": True, "url": "https://link.coupang.com/a/ROX", "button": "🛒 25,800원 구매하기", "at": "2026-10-22 10:30",
        "text": "👍 <b>[쿠팡] 록시땅 시어 버터 핸드크림 75ml (25,800원)</b>\n\n📊 한 달 1,000명+ 구매 · 리뷰 1,969\n🎁 백화점 선물 포장·쇼핑백\n참고: 내가 쓸 거면 150ml가 10ml당 더 쌈\n⚠️ 롯데택배 10/24(토) 도착"}
b31, k31 = H.ev_view(ST31)
assert b31.startswith("📦 쿠팡 · 꾸준히 팔리는 상품 👍\n<b>록시땅 시어 버터 핸드크림 75ml</b>\n25,800원 · 한 달 1,000명+ 구매 · 리뷰 1,969\n🎁 백화점 선물 포장·쇼핑백\n참고: 내가 쓸 거면 150ml가 10ml당 더 쌈\n⚠️ 롯데택배 10/24(토) 도착") and k31 == "📦 쿠팡에서 25,800원", b31
p31 = H.plain_of(b31)
assert H.title_of(p31) == "[쿠팡] 록시땅 시어 버터 핸드크림 75ml (25,800원)" and H.th_steady(p31) and H.th_steady(H.plain_of(ST31["text"])) and not H.th_weak(p31) and "특가로는 약한" not in p31  # 제목엔 구매·리뷰 숫자 X
assert H.ad_line(H.plain_of(ST31["text"])) == "[광고] 👍 록시땅 시어 버터 핸드크림 75ml 25,800원" and H.th_beauty("👍 [쿠팡] 록시땅 시어 버터 핸드크림 75ml") > 0
assert H.ev_view({**ST31, "text": ST31["text"].replace("롯데택배", "로켓배송")})[0].startswith("🚀 쿠팡 로켓 · 꾸준히 팔리는 상품 👍\n")
assert H.ev_view({**ST31, "text": ST31["text"].replace("📊 한 달 1,000명+ 구매 · 리뷰 1,969\n", "")})[0].split("\n")[2] == "25,800원"  # 숫자 없으면 가격만
assert H.ev_view({**ST31, "url": "https://toss.shopping/_m/X", "text": ST31["text"].replace("[쿠팡]", "[토스]")})[0].startswith("👍 <b>[토스]")  # 토스 👍 = 범위 밖(그대로)
assert not H.th_steady("💙 토스 특가 🔥\n휴지\n9,900원\n👍 리뷰 4.8점 많이 삼")
for a31, b31x in (("📊 한 달 1만명+ 구매 · 리뷰 1.6만", "25,800원 · 한 달 1만명+ 구매 · 리뷰 1.6만"), ("📊 한 달 1,000명+ 구매 · 리뷰 1,969개", "25,800원 · 한 달 1,000명+ 구매 · 리뷰 1,969"),
                  ("📊 한 달 2만 명 이상 구매 · ⭐ 4.5 (리뷰 93만)", "25,800원 · 한 달 2만명+ 구매 · 리뷰 93만")):  # 만 단위·'개'(10/22 리뷰 '리뷰 1.6만'이 '리뷰 1'로) · 숫자만 있던 줄은 뺌
    l31 = H.ev_view({**ST31, "text": ST31["text"].replace("📊 한 달 1,000명+ 구매 · 리뷰 1,969", a31)})[0].split("\n")
    assert l31[2] == b31x and (l31[3] == "🎁 백화점 선물 포장·쇼핑백" or "⭐ 4.5" in l31[3]), l31
assert H.ev_view({**ST31, "text": ST31["text"].replace("롯데택배", "로켓배송 아님 · 롯데택배")})[0].startswith("📦 쿠팡 · 꾸준히")  # '로켓배송 아님' = 로켓 X
assert H.th_tier(p31.replace("🎁", "손/발 크림 판매 2위 · 🎁")) == 0 and H.th_tier(p31.replace("🎁", "손/발 크림 판매 2위 · 🎁").replace("상품 👍", "상품 🔥")) == 2  # 👍 = 순위 있어도 강한 딜 X(TOP 앞자리 X)
assert S.steady_st(p31) == "한 달 1,000명+ 구매 · 리뷰 1,969" and S.summary(p31).startswith("한 달 1,000명+ 구매 · 리뷰 1,969 ") and S.steady_st("🚀 쿠팡 로켓 🔥\n휴지\n9,900원 · 리뷰 3") == ""  # 사이트 딜 페이지·설명에 숫자
ev31, H.EVENTS = H.EVENTS, "ev31.json"; json.dump([{**ST31, "at": "2026-10-22 10:40", "text": ST31["text"].replace("75ml", "150ml")}, {**ST31, "at": "2026-10-22 10:50", "url": "https://link.coupang.com/a/W1", "text": "🛒 <b>[쿠팡] 약한 것 (1,000원)</b>\n\n🤔 솔직히 특가로는 약한 제품"},
                                                         {**ST31, "at": "2026-10-22 10:55", "url": "https://link.coupang.com/a/F1", "text": "🔥 <b>[쿠팡] 센 것 (2,000원)</b>\n\n30일 최저가"}], open("ev31.json", "w"), ensure_ascii=False)
nd31 = H.night_deals({}, "2026-10-22 09:00", "2026-10-22 11:00")
pj31, H.POSTS = H.POSTS, "posts31.json"; json.dump([], open("posts31.json", "w")); json.dump([{**ST31, "at": "2026-10-22 23:00"}], open("ev31.json", "w"), ensure_ascii=False)
jb31 = H.jw_beauty({}, TK("2026-10-22 20:00")); json.dump([{**ST31, "at": "2026-10-22 23:00", "text": ST31["text"].replace("👍", "🔥", 1)}], open("ev31.json", "w"), ensure_ascii=False)
assert not jb31 and H.jw_beauty({}, TK("2026-10-22 20:00")); os.remove("posts31.json"); H.POSTS = pj31  # 👍 화장품 예약 = 화장품 자리 안 막음(🔥는 막음)
os.remove("ev31.json"); H.EVENTS = ev31
assert [d["icon"] for d in nd31] == ["👍", "🛒", "🔥"] and [d["icon"] for d in sorted(nd31, key=lambda d: "🔥👍🛒".index(d["icon"]))] == ["🔥", "👍", "🛒"], nd31  # 미리보기: 🔥 -> 👍 -> 🛒
# Threads 개별 글(지금 틀 = th_voice 꺼짐): 대가성 문구 다음 줄 = 채널 글과 같은 머리 줄, 본문 그대로(출처·🏆 줄 X)
os.makedirs("docs/p", exist_ok=True)
c28 = []
H.http = lambda url, body=None, headers=None, method=None: c28.append((url, method)) or (json.dumps({"id": "777"}) if "/me?fields=id" in url else json.dumps({"id": "c1"}) if "/777/threads?" in url else json.dumps({"id": "p1"}) if "threads_publish" in url else "")
H.E["THREADS_TOKEN"], H.time.sleep = "tk", (lambda s: None)
seen28 = {}; time.time = lambda: TK("2026-10-22 10:25"); H.threads_deals(seen28)
th28 = [parse_qs(urlsplit(u).query)["text"][0] for u, m in c28 if "/777/threads?" in u]
assert len(th28) == 3 and th28[0].startswith(f"{H.TOSS_NOTE}\n\n{H.plain_of(TOSS28)}\n\n👉 https://toss.shopping/_m/t28\n"), th28  # 실행당 3개(셀프체크 TH_SOLO_RUN) — 토스 진우 예약도 같은 머리 줄
th28 = [t for t in th28 if "코멧" in t]
assert len(th28) == 1 and th28[0].startswith(f"{H.DISCLOSURE}\n\n🚀 쿠팡 로켓 · 1개당 최저 🔥\n코멧 손난로 100g 30개\n8,860원 → 1개 295원\n📊 참고: 충성 317원 · 해피데이 373원\n🚚 내일(금) 도착 · 무료반품\n⚠️ 결제 전 최종가 (10/22 10시)\n\n👉 https://link.coupang.com/a/c28\n"), th28
assert "💸" not in th28[0] and "[쿠팡]" not in th28[0]
# th_voice: 머리 줄 = 고정 줄(대가성 문구 바로 다음, 이모지 셈 X) · 상품명·가격 = 머리 아래 두 줄 · 몰별 결(쿠팡 = 비교, 토스 = 오늘 특가 소식)
# th_voice(10/23 고정 레이아웃): 몰별 틀 = 머리 줄 그대로 · 상품명·가격 = 머리 아래 두 줄 · 🚚 도착·반품 = ✔ · 📊 참고 = 💡 · ⏰ 시각 = 글의 '(10/22 10시)'(지금 13시 아님)
pv28, vv28 = [], [{"line": "주머니에 하나씩 넣어 두기 좋음"}]
sv28b = (H.ai_voice, H.random); H.ai_voice, H.random = (lambda prompt: pv28.append(prompt) or vv28.pop(0)), type("R", (), {"choice": staticmethod(lambda xs: 4)})
time.time = lambda: TK("2026-10-22 13:05"); o28 = H.th_voice({}, th28[0], "https://link.coupang.com/a/c28")
assert o28 == f"{H.DISCLOSURE}\n\n🚀 쿠팡 로켓 · 1개당 최저 🔥\n코멧 손난로 100g × 30개\n💰 8,860원 (1개 295원)\n\n✔ 무료반품 · 내일(금) 도착\n💡 참고: 충성 317원 · 해피데이 373원\n\n주머니에 하나씩 넣어 두기 좋음\n\n⏰ 10/22 10시 가격 · 결제 전 확인\n👉 https://link.coupang.com/a/c28", o28
assert "상품명: 코멧 손난로 100g 30개\n가격: 8,860원" in pv28[0] and "토스 딜:" not in pv28[0], pv28[0]
TT28 = H.toss_th("생필품 베스트 3위", "더건강플러스 올리브오일 1L", "15,580원 (60%↓) · ⭐ 4.7 (11,683)", ["🙋 집밥 자주 하는 집"], "https://toss.shopping/_m/t28")
assert TT28.startswith(H.th_note(H.TOSS_NOTE) + "💙 토스 특가 · 생필품 베스트 3위 🔥\n더건강플러스 올리브오일 1L\n15,580원 (60%↓) · ⭐ 4.7 (11,683)\n🙋 집밥 자주 하는 집\n⚠️ ") and H.title_of(TT28) == "[토스] 더건강플러스 올리브오일 1L (15,580원)", TT28
vv28[:] = [{"line": "집밥 자주 하는 집이면 쟁여 둘 만함"}]; pv28.clear()
o28 = H.th_voice({}, TT28, "https://toss.shopping/_m/t28")
assert re.fullmatch(rf"{re.escape(H.TOSS_NOTE)}\n\n💙 토스 특가 · 생필품 베스트 3위 🔥\n더건강플러스 올리브오일 1L\n💰 15,580원 \(60%↓\)\n\n✔ 평점 4\.7 · 리뷰 1만\+\n\n집밥 자주 하는 집이면 쟁여 둘 만함\n\n⚠️ \d+/\d+ \d\d:\d\d 게시 시점 가격\n👉 https://toss\.shopping/_m/t28", o28) and "토스 딜:" in pv28[0], o28  # 토스 = 평점·리뷰(반올림) ✔ · 💡 X · 게시 시점 줄 그대로
ST28 = f"{H.DISCLOSURE}\n\n🚀 쿠팡 · 꾸준히 팔리는 상품 👍\n록시땅 시어 버터 핸드크림 75ml\n25,800원 · 한 달 1,000명+ 구매 · 리뷰 1,969\n🎁 백화점 선물 포장\n⚠️ 결제 전 최종가 (10/22 20시)\n\n👉 https://link.coupang.com/a/st28"
vv28[:] = [{"line": "오늘 특가로 싸게 나옴"}, {"line": "선물용으로 하나쯤 두기 좋음"}]; pv28.clear()
o28 = H.th_voice({}, ST28, "https://link.coupang.com/a/st28")  # 9-31 👍 꾸준템: 말투 줄에 특가·최저·할인 X(1번 다시)
assert o28 == f"{H.DISCLOSURE}\n\n🚀 쿠팡 · 꾸준히 팔리는 상품 👍\n록시땅 시어 버터 핸드크림 75ml\n💰 25,800원\n\n✔ 리뷰 1,900+ · 한 달 1,000명+ 구매\n\n선물용으로 하나쯤 두기 좋음\n\n⏰ 10/22 20시 가격 · 결제 전 확인\n👉 https://link.coupang.com/a/st28", o28
assert "'꾸준히 팔리는 상품'" in pv28[0] and len(pv28) == 2, pv28[0]
H.ai_voice, H.random = sv28b
# 토스 목록: 하루특가 TOP5·17시 생필품 등 머리 = 💙 · 품절 고칠 때 게시 시점 줄(꼬리)도 남김
assert '"💙 <b>오늘의 토스 하루특가 TOP{}</b>' in inspect.getsource(H.toss_deals) and 'head = "💙 <b>토스 "' in inspect.getsource(H.toss_deals) and "⏰ <b>오늘의 토스" not in inspect.getsource(H.toss_deals)
assert H.sold_render({"k": "top", "pre": "P\n\n", "head": "💙 <b>오늘의 토스 하루특가 TOP1</b>", "tail": "\n\n⚠️ 10/22 09:05 게시 시점 가격", "rows": [["a", "u", ["💰 <b>1원</b>"]]], "it": [[1, "a", 1, 1, 1, 0]]})[0].endswith("⛔ <b>품절</b> — 밤 12시부터 다시 살 수 있어요\n\n⚠️ 10/22 09:05 게시 시점 가격")
# 커뮤니티 [쿠팡] 글이 진우 링크로 바뀌면(relink_channel): 몰별 틀 그대로 + 대가성 문구 맨 앞 + 🚀 버튼(가격)
NT28 = {"chat": {"id": 42}, "message_id": 9, "text": "🚀 쿠팡 로켓 🔥\n휴지 30롤\n9,900원 · 무료\n싸다\n\n출처: 뽐뿌", "entities": []}
json.dump([{"t": "2026-10-22 10:00", "mid": 77, "url": "https://www.coupang.com/vp/1", "text": NT28["text"], "entities": []}], open("posts.json", "w")); s28.clear()
assert H.relink_channel(NT28, 77, "https://link.coupang.com/a/r28")
ed28 = [p for m, p in s28 if m == "editMessageText" and p["chat_id"] == H.CHANNEL][0]
assert ed28["text"] == f"{H.DISCLOSURE}\n\n{NT28['text']}" and ed28["reply_markup"]["inline_keyboard"] == [[{"text": "🚀 쿠팡에서 9,900원", "url": "https://link.coupang.com/a/r28"}]] and H.title_of(json.load(open("posts.json"))[0]["text"]) == "[쿠팡] 휴지 30롤 (9,900원/무료)"
# 예전 틀 토스 글(진우 예약)의 할인·평점은 가격 줄로(정보 줄은 그대로)
assert H.mall_view("🔥 <b>[토스] 수뜰리에 탈취제 310g 2개 (6,930원)</b>\n\n10/13 밤 토스 많이 팔린 순위 3위 · 61% 할인 · ⭐ 4.7 (리뷰 3,327)", "https://toss.shopping/_m/s") == \
    "💙 토스 특가 · 61% 할인 🔥\n<b>수뜰리에 탈취제 310g 2개</b>\n6,930원 (61%↓) · ⭐ 4.7 (3,327)\n10/13 밤 토스 많이 팔린 순위 3위 · 61% 할인 · ⭐ 4.7 (리뷰 3,327)"  # 지난 날 순위는 머리 줄 X(정보 줄엔 날짜와 같이 남음)
# th_voice: 재료에 날짜가 붙은 숫자(10/21 쿠팡 검색 기준 …)는 그 날짜와 같이만(10/22 Cowork — 하루온 글이 어제 비교 숫자를 '오늘 10시 기준'처럼) · 기준 시각 = 글의 가격 시각(지금 아님)
HO28 = f"{H.DISCLOSURE}\n\n🚀 쿠팡 로켓 · 1개당 최저 🔥\n하루온 군인핫팩 160g, 30개\n13,520원\n로켓배송 160g 대형 핫팩 중 1개당 가장 싸요 — 10/21 쿠팡 검색 상위 기준 1개당 451원(참고: 충성 160g 60개 469원·마이핫 160g 750원)\n⚠️ 확인할 점: '22% 할인'은 정가 기준이라 참고만 · 결제 전 최종가 확인 (10/22 10시 가격)\n\n👉 https://link.coupang.com/a/h28"
vv28[:] = [{"line": "출퇴근길 주머니에 넣어 두기 좋음"}]
sv28d = (H.ai_voice, H.random); H.ai_voice, H.random = (lambda prompt: pv28.append(prompt) or vv28.pop(0)), type("R", (), {"choice": staticmethod(lambda xs: 4)})
time.time = lambda: TK("2026-10-22 13:05"); o28 = H.th_voice({}, HO28, "https://link.coupang.com/a/h28"); H.ai_voice, H.random = sv28d
assert o28 == f"{H.DISCLOSURE}\n\n🚀 쿠팡 로켓 · 1개당 최저 🔥\n하루온 군인핫팩 160g × 30개\n💰 13,520원 (1개당 451원)\n\n출퇴근길 주머니에 넣어 두기 좋음\n\n⏰ 10/22 10시 가격 · 결제 전 확인\n👉 https://link.coupang.com/a/h28", o28  # 날짜 붙은 참고 숫자(10/21 검색)는 💡로 안 씀 · 정가 기준 할인 X · 말투 줄엔 숫자 X
# 리뷰 보강(10/22): 가격 줄 쿠폰가 조각도 제목으로(예전 제목 그대로) · 단위가격 특수문자 이스케이프 1번 · 토스 머리 줄에 다른 몰 순위 X(strip_cmp도 칸만 뺌)
#   · 토스 Claude 한 줄은 비교 말 X · 진우가 봇에 보낸 토스 링크 글(admin_deal·초안) = 비교 빼고 게시 시점 줄
assert H.title_of(H.plain_of(H.mall_view("🔥 <b>[토스] 쏘울너츠 2개 (1,950원 · 5천원 쿠폰가)</b>\n\n토스 90% 할인", "https://toss.shopping/_m/q"))) == "[토스] 쏘울너츠 2개 (1,950원 · 5천원 쿠폰가)"
assert "\n8,860원 → 1개 295원 (P&amp;G 기준)\n" in H.mall_view("🔥 <b>[쿠팡] 핫팩 (8,860원)</b>\n\n싸다\n💡 단위가격 1개당 295원 (P&amp;G 기준)", "https://link.coupang.com/a/u")
assert H.mall_src("toss", "쿠팡 판매 1위 올리브오일") == H.mall_src("toss", "쿠팡 베스트 1위 올리브오일") == "" and H.mall_src("toss", "토스 생활용품 베스트 2위") == "생활용품 베스트 2위" and H.mall_src("coupang", "손난로/핫팩 구매 8위") == "손난로/핫팩 구매 8위"
assert H.strip_cmp("💙 토스 특가 · 쿠팡 판매 1위 🔥\n올리브영 크림\n1원\n쿠팡보다 쌈")[0] == "💙 토스 특가 🔥\n올리브영 크림\n1원"
assert [H.toss_lines({"comment": c}) for c in ("시중가 대비 40% 저렴", "다른 곳보다 3천원 쌈", "마트 가격이랑 비교하면 절반", "1L 대용량 15,580원")] == [[], [], [], ["👉 1L 대용량 15,580원"]]
assert H.toss_body("🔥 <b>[토스] 오일 (1원)</b>\n\n쿠팡 판매 1위 오일\n좋음", "https://toss.shopping/_m/x").startswith("🔥 <b>[토스] 오일 (1원)</b>\n\n좋음\n⚠️ ") and "게시 시점 가격" in H.toss_body("🔥 <b>[토스] 오일 (1원)</b>", "https://toss.shopping/_m/x")
assert H.toss_body("🔥 <b>[쿠팡] 오일 (1원)</b>\n\n쿠팡 판매 1위", "https://link.coupang.com/a/x") == "🔥 <b>[쿠팡] 오일 (1원)</b>\n\n쿠팡 판매 1위"  # 쿠팡 = 그대로
dp28 = H.mall_view("🔥 <b>[쿠팡] 삼양라면 120g 10개 (4,920원/무료)</b>\n\n개당 492원 계산\n💡 단위가격 개당 492원\n\n출처: <a href=\"x\">루리웹</a>", "https://www.coupang.com/vp/1")
assert CPT(dp28) == "📦 쿠팡 🔥\n<b>삼양라면 120g 10개</b>\n4,920원 → 1개 492원 · 무료\n개당 492원 계산\n⚠️ 결제 전 최종가 (시각)\n\n출처: <a href=\"x\">루리웹</a>", dp28  # 단위가격 줄만 빠지고 출처 앞 빈 줄 그대로(⚠️는 출처 위)
assert H.sold_render({"k": "top", "t": TK("2026-10-22 09:05"), "pre": "", "head": "H", "rows": [["a", "u", []]], "it": [[1, "a", 1, 1, 0, 0]]})[0].endswith("\n\n⚠️ 10/22 09:05 게시 시점 가격")  # 배포 전 묶음 기록(꼬리 없음) = 그 글 시각
assert "mall_view(toss_body(" in inspect.getsource(H.admin_deal) and "mall_view(toss_body(" in inspect.getsource(H.publish_approved)
# 몰별 틀 약한 딜(머리 줄 끝 🛒)도 예전 🛒 제목처럼: 22시 미리보기 🛒 · 재오픈 Threads 🛒 · 진우 화장품 예약 셈(새 틀 제목)
json.dump([{"at": "2026-10-22 22:20", "button": "🛒 구매하러 가기", "url": "https://link.coupang.com/a/w28", "deal": True, "text": "🚀 쿠팡 로켓 🛒\n<b>약한 휴지</b>\n9,900원\n🤔 솔직히 특가는 아니에요"},
           {"at": "2026-10-22 22:30", "button": "🛒 구매하러 가기", "url": "https://link.coupang.com/a/b28", "deal": True, "text": "🚀 쿠팡 로켓 · 와우 할인 🔥\n<b>닥터지 레드 블레미쉬 선크림 50ml</b>\n12,000원"}], open(H.EVENTS, "w"), ensure_ascii=False)
assert [(d["icon"], d["name"]) for d in H.night_deals({}, "2026-10-22 22:00", "2026-10-23 08:00")] == [("🛒", "약한 휴지"), ("🔥", "닥터지 레드 블레미쉬 선크림 50ml")]
time.time = lambda: TK("2026-10-22 21:00"); assert H.jw_beauty({}, time.time())  # 이름 칸 없는 새 틀 쿠팡 화장품 예약 = 진우 화장품 링크로 셈(제목 = 머리 아래 상품명)
WT28 = "💙 토스 특가 🛒\n<b>생수 2L 12개</b>\n9,900원\n🤔 솔직히 특가로는 약한 제품"
H.toss, H.HAS_TOSS, H.E["THREADS_TOKEN"], s28[:] = (lambda path, body=None: {"items": [{"tacaItemId": 77, "displayPrice": 9900, "isSoldOut": False, "displayName": "생수"}], "hasNext": False}), True, "tk", []
sr28 = {"sold_901": {"t": TK("2026-10-21 20:00"), "d": "2026-10-21", "k": "ev", "pre": f"<i>{H.TOSS_NOTE}</i>\n\n", "body": WT28, "btn": "💙 토스에서 9,900원", "url": "https://toss.shopping/_m/w28", "n": "생수", "p": 9900, "it": [[77, "생수", 9900, 1, 1, 0]]}}
json.dump([], open(H.EVENTS, "w")); time.time = lambda: TK("2026-10-22 00:05")
with contextlib.redirect_stdout(io.StringIO()): H.toss_soldout(sr28)
assert [(e["icon"], e["title"]) for e in sr28["reopen"]["q"]] == [("🛒", "생수 2L 12개")], sr28.get("reopen")  # 머리 줄 🛒 = 약한 딜(재오픈 Threads 안 나감 — th_weak), 제목 = 머리 아래 상품명
assert [p["reply_markup"]["inline_keyboard"][0][0]["text"] for m, p in s28 if m == "sendMessage"] == ["💙 토스에서 9,900원"]  # 채널 답글 '다시 열렸어요' 버튼 = 💙
# Threads(몰별 틀 글): 💸 훅 줄은 안 붙임(머리 줄이 대가성 문구 바로 다음) · th_voice가 💙 머리 줄 흉내 낸 줄은 뺌
json.dump([{"t": "2026-10-22 10:00", "mid": 5, "url": "https://link.coupang.com/a/s28", "own": 1, "text": f"{H.DISCLOSURE}\n\n🚀 쿠팡 로켓 · 같은 상품 최저 🔥\n휴지 30롤\n9,900원\n💡 네이버 같은 상품보다 2,000원 쌈", "entities": []}], open("posts.json", "w"), ensure_ascii=False)
c28.clear(); time.time = lambda: TK("2026-10-22 10:25"); H.threads_deals({})
(ts28,) = [parse_qs(urlsplit(u).query)["text"][0] for u, m in c28 if "/777/threads?" in u]
assert ts28.startswith(f"{H.DISCLOSURE}\n\n🚀 쿠팡 로켓 · 같은 상품 최저 🔥\n휴지 30롤\n9,900원\n💡 네이버 같은 상품보다 2,000원 쌈\n\n👉 ") and "💸" not in ts28, ts28
# Cowork 예전 틀 쿠팡 '💡 1개당 373원 · …' = 맨 앞 단위가격만 가격 줄 '→'로(나머지 조각은 💡에 남김) · 지난 날 순위('10/12 밤 … 1위')는 머리 줄로 X
mv28 = lambda b: H.mall_view(f"🛒 <b>[쿠팡] 핫팩 40개 (14,930원)</b>\n\n🤔 솔직히 특가는 아니고\n{b}", "https://link.coupang.com/a/u").split("\n")
assert mv28("💡 1개당 373원 · 다른 수량은 옵션에서")[2:5] == ["14,930원 → 1개 373원", "🤔 솔직히 특가는 아니고", "💡 다른 수량은 옵션에서"] and mv28("💡 1개당 750원")[2:4] == ["14,930원 → 1개 750원", "🤔 솔직히 특가는 아니고"]
assert mv28("💡 1개당 148원(2p × 60개) · 13시간")[2] == "14,930원 → 1개 148원(2p × 60개)" and mv28("💡 1롤 517원꼴 · 10m당 191원")[2:5:2] == ["14,930원 → 1롤 517원꼴", "💡 10m당 191원"] and mv28("💡 최고 70도·18시간 이하")[2] == "14,930원"
assert mv28("💡 단위가격: 100g당 2,000원 — 네이버보다 쌈")[2:5:2] == ["14,930원 → 100g당 2,000원", "💡 네이버보다 쌈"] and len(mv28("💡 1개당 750원")) == 5  # (예전 '💡 단위가격' 틀도)
time.time = lambda: TK("2026-10-22 13:05")
assert H.mall_src("toss", "10/12 밤 토스 많이 팔린 순위 1위 · 44% 할인") == "44% 할인" and H.mall_src("toss", "10/22 9시 토스 많이 팔린 순위 2위") == "많이 팔린 순위 2위" and H.mall_src("coupang", "어제 핫팩 구매 3위") == ""
LT28 = f"{H.TOSS_NOTE}\n\n💙 토스 특가 · 하루특가 🔥\n비로르 스텐 주방 가위 20.5cm 2개\n4,990원 · ⭐ 4.4 (7,705)\n⭐ 4.4 (리뷰 7,705) · 내일출발 · " + "가" * 80 + "\n💡 " + "나" * 80 + "\n⚠️ 확인할 점: 10/14 00:35 게시 시점 가격 · 어젯밤 품절 → 밤 12시부터 다시 판매라 선착순 · 사람마다 가격이 다를 수 있음 · 결제 전 최종가 확인"
json.dump([{"t": "2026-10-22 13:00", "mid": 6, "url": "https://toss.shopping/_m/v28", "own": 1, "text": LT28, "entities": []}], open("posts.json", "w"), ensure_ascii=False)
c28.clear(); H.threads_deals({})
(tl28,) = [parse_qs(urlsplit(u).query)["text"][0] for u, m in c28 if "/777/threads?" in u]
assert tl28.startswith(f"{H.TOSS_NOTE}\n\n💙 토스 특가 · 하루특가 🔥\n비로르") and "\n⚠️ 10/22 13:00 게시 시점 가격\n\n👉 https://toss.shopping/_m/v28" in tl28 and len(tl28) <= 500, tl28  # 줄이다 게시 시점 조각이 빠지면 끝에 다시(10/22 리뷰)
assert H.mall_dr("토스 61% 할인\n⚠️ 88% 할인율보다 쿠팡 가격 비교가 정확") == ("", "61") and H.mall_dr("⚠️ 88% 할인율보다 쿠팡 가격 비교가 정확\n📊 참고 30% 할인") == ("", "")  # 단서·비교 줄의 %는 머리·가격 줄로 X
# 10/22 Cowork: 조건 붙은 할인은 조건째('와우 쿠폰 44% 할인' — 가격 줄 (N%↓)엔 X) · 쿠팡 '로켓'은 글에 로켓·새벽 도착 근거 있을 때만(없으면 '🚀 쿠팡')
assert [H.mall_src("coupang", t) for t in ("로켓배송 · 와우 쿠폰 44% 할인", "카드 즉시 10% 할인", "멤버십 15% 할인", "22% 할인")] == ["와우 쿠폰 44% 할인", "카드 즉시 10% 할인", "멤버십 15% 할인", "22% 할인"]
KK28 = H.mall_view("🔥 <b>[쿠팡] 깨끗한나라 30롤 (15,500원)</b>\n\n로켓배송 · 와우 쿠폰 44% 할인 · 내일 새벽 도착\n💡 1롤 517원꼴 · 10m당 191원", "https://link.coupang.com/a/k")
assert KK28.split("\n")[:3] == ["🚀 쿠팡 로켓 · 와우 쿠폰 44% 할인 🔥", "<b>깨끗한나라 30롤</b>", "15,500원 → 1롤 517원꼴"], KK28  # 12:29 실제 글(머리 '44% 할인'만이던 것)
assert H.mall_view("🔥 <b>[쿠팡] 핫팩 (8,860원)</b>\n\n판매자로켓 배송", "https://link.coupang.com/a/k").startswith("🚀 쿠팡 로켓 🔥") and H.mall_view("🔥 <b>[쿠팡] 핫팩 (8,860원)</b>\n\n내일 새벽 도착", "https://link.coupang.com/a/k").startswith("🚀 쿠팡 로켓 🔥")
assert H.mall_view("🔥 <b>[쿠팡] 핫팩 (8,860원)</b>\n\n판매자 배송", "https://link.coupang.com/a/k").startswith("📦 쿠팡 🔥") and H.title_of("🚀 쿠팡 · 22% 할인 🔥\n핫팩\n8,860원") == "[쿠팡] 핫팩 (8,860원)" and H.th_weak("🚀 쿠팡 🛒\n핫팩\n1원") and H.th_weak("📦 쿠팡 🛒\n핫팩\n1원") and H.title_of("📦 쿠팡 · 22% 할인 🔥\n핫팩\n8,860원") == "[쿠팡] 핫팩 (8,860원)"
GB28 = H.mall_view("🔥 <b>[쿠팡] 기가바이트 GS24F14A 144Hz 모니터 (89,890/무료)</b>\n\n싸다", "https://www.coupang.com/np/search?q=x")  # 10/22 13:26 '원' 없는 가격 = 예전 틀로 남던 것
assert GB28.split("\n")[:3] == ["📦 쿠팡 🔥", "<b>기가바이트 GS24F14A 144Hz 모니터</b>", "89,890원 · 무료"] and H.title_of(H.plain_of(GB28)) == "[쿠팡] 기가바이트 GS24F14A 144Hz 모니터 (89,890원/무료)", GB28
assert H.mall_view("🔥 <b>[쿠팡] 우유 (7,890, 무배)</b>\n\n싸다", "https://www.coupang.com/vp/1").split("\n")[2] == "7,890원 · 무배" and H.mall_view("🔥 <b>[쿠팡] 우유 (2개)</b>", "https://www.coupang.com/vp/1") == "🔥 <b>[쿠팡] 우유 (2개)</b>"  # 숫자 아닌 괄호 = 그대로
TQ28 = H.mall_view("🔥 <b>[토스] 오일 (1,000원)</b>\n\n쿠폰 적용 61% 할인", "https://toss.shopping/_m/q").split("\n")
assert TQ28[0] == "💙 토스 특가 · 쿠폰 적용 61% 할인 🔥" and TQ28[2] == "1,000원", TQ28  # 토스는 '로켓' 상관없이 💙 · 조건 붙은 %는 가격 줄 (N%↓) X
assert H.mall_view("🔥 <b>[토스] 수뜰리에 2.5L 4개 (4,620원)</b>\n\n토스 하루특가\n⚠️ 88% 할인율보다 쿠팡 가격 비교가 정확", "https://toss.shopping/_m/x").split("\n")[:3] == ["💙 토스 특가 · 하루특가 🔥", "<b>수뜰리에 2.5L 4개</b>", "4,620원"]
vv28[:] = [{"line": "💙 토스 특가 오늘만"}, {"line": "집밥용으로 쟁여 둘 만함"}]
sv28c = (H.ai_voice, H.random); H.ai_voice, H.random = (lambda prompt: vv28.pop(0)), type("R", (), {"choice": staticmethod(lambda xs: 4)})
o28 = H.th_voice({}, TT28, "https://toss.shopping/_m/t28"); H.ai_voice, H.random = sv28c
assert "토스 특가 오늘만" not in o28 and o28.count("💙") == 1 and "\n\n집밥용으로 쟁여 둘 만함\n\n" in o28, o28  # 라벨 줄(💙) = 문장 아님 -> 1번 다시
(H.tg, H.EVENTS, time.time, H.TOSS_NO_CMP, H.toss, H.ai_pick, H.HAS_TOSS, H.TOSS_SOLO_HOURS, H.TOSS_GAP_MIN) = sv28[:9]; H.E.pop("THREADS_TOKEN", None); H.http = fake_http; json.dump([], open("posts.json", "w"))
# 9-29 (10/22 15:3x Cowork·진우 '점검 기간에도 토스 글 채널·Threads 둘 다 계속(수익 0이어도)'): 토스 쉐어링크 점검 10/30 00:00~11/4 23:59(KST) = 새 링크 X·만들어 둔 링크(tlink) 재사용,
#      점검 때문인 실패는 바로 안 알리고 하루 1번 요약, 11/5 첫 실행에 링크 1개 만들어 보고 되면 보통 모드 + 알림 1번, 10/28~29 미리 만들기(toss_stock)
sv29 = (H.http, H.tg, H.ai_pick, H.EVENTS, time.time, H.HAS_TOSS, H.TOSS_SOLO_HOURS, H.TOSS_GAP_MIN, H.TOSS_NO_CMP)
c29, s29m, lk29, LF29, BAD29 = [], [], [], [], set()  # API 호출 · 관리자 알림 · 링크 발급(tacaItemId) · 비어 있지 않으면 발급 FAIL · 이 상품만 발급 FAIL(발급 제한)
L29 = {"best-selling": [{"tacaItemId": k, "displayName": f"베스트{k}", "displayPrice": 9900, "discountRate": 40, "reviewScore": 4.8, "reviewCount": 1234, "isSoldOut": k == 3} for k in (1, 2, 3, 4)],
       "today-deals": [{"tacaItemId": 50, "displayName": "하루특가50", "displayPrice": 5000, "isSoldOut": False}]}
D29 = {7: {"tacaItemId": 7, "displayName": "보관7", "displayPrice": 7700, "discountRate": 30, "reviewScore": 4.5, "reviewCount": 99, "isSoldOut": False}}
def h29(url, body=None, headers=None, method=None):
    c29.append(url)
    if url == "https://oauth2.cert.toss.im/token": return json.dumps({"access_token": "TK", "expires_in": 31535999})
    if url.endswith("/categories"): return json.dumps({"resultType": "SUCCESS", "success": {"categories": [{"categoryId": 200, "displayName": "식품"}, {"categoryId": 400, "displayName": "뷰티"}, {"categoryId": 900, "displayName": "가전"}]}})
    if url.endswith("/links"):
        lk29.append(body["tacaItemId"])
        return json.dumps({"resultType": "FAIL", "error": {"reason": "점검"}} if LF29 or body["tacaItemId"] in BAD29 else {"resultType": "SUCCESS", "success": {"shortUrl": f"https://toss.im/_m/N{body['tacaItemId']}"}})
    if "/products/detail?" in url: return json.dumps({"resultType": "SUCCESS", "success": {"items": [D29[int(i)] for i in parse_qs(urlsplit(url).query)["tacaItemIds"][0].split(",") if int(i) in D29]}})
    for k, v in L29.items():
        if f"/products/{k}?" in url: return json.dumps({"resultType": "SUCCESS", "success": {"items": v}})
    if "/products/best-categories/" in url: return json.dumps({"resultType": "SUCCESS", "success": {"items": [{"tacaItemId": int(url.split("/")[-1].split("?")[0]) + 1, "displayName": "카테", "displayPrice": 1000, "isSoldOut": False}]}})
    raise AssertionError(url)
H.http, H.HAS_TOSS, H.tg = h29, True, lambda m, **p: s29m.append(p.get("text", "")) or {"message_id": 900 + len(s29m)}
H.E.update(TOSS_ACCESS_KEY="ak", TOSS_SECRET_KEY="sk", TOSS_PUBLISHER_ID="pub-1")
assert H.TOSS_PAUSE == ("2026-10-30 00:00", "2026-11-04 23:59") and H.TOSS_STOCK_DAYS == ("2026-10-28", "2026-10-29") and "toss_mode(seen)" in inspect.getsource(H.main) and "ig_publish, ig_stage, ig_test, toss_stock, coupang_remind" in inspect.getsource(H.main)
# ① 경계: 10/29 23:59 보통 · 10/30 00:00 재사용(시작 알림 1번) · 11/4 23:59 재사용(날 바뀌면 전날 요약 1번) · 11/5 00:00 링크 1개 만들어 봄 -> 되면 보통 + '끝' 1번
s29 = {"tlink": {"t": 1, "m": {"7": ["https://toss.im/_m/K7", TK("2026-10-28 10:00")], "2": ["https://toss.im/_m/K2", TK("2026-10-29 10:00")]}}, "tb_7": {"t": TK("2026-10-29 12:00")}}
H.toss_mode(s29, TK("2026-10-29 23:59")); assert H.RUN["treuse"] is False and not s29m and "tpause" not in s29 and not lk29
H.toss_mode(s29, TK("2026-10-30 00:00")); assert H.RUN["treuse"] is True and len(s29m) == 1 and s29m[0].startswith("🔧 토스 쉐어링크 점검 모드 시작(10/30~11/4) — 새 링크 안 만들고 보관 링크 2개(3일 안 올린 것 빼면 1개)를 재사용") and not lk29, s29m
H.toss_mode(s29, TK("2026-10-30 00:14")); assert H.RUN["treuse"] is True and len(s29m) == 1  # 시작 알림은 1번
H.tnote(s29, "ok", "베스트2"); H.tnote(s29, "miss", "이름 예약 장어"); H.tnote(s29, "err", "토스 회차 글 RuntimeError"); H.tnote(s29, "err", "토스 회차 글 RuntimeError")
H.toss_mode(s29, TK("2026-10-30 23:59")); assert len(s29m) == 1  # 같은 날 = 요약 X
H.toss_mode(s29, TK("2026-10-31 00:00")); assert H.RUN["treuse"] is True and len(s29m) == 2 and s29m[1] == "🔧 토스 점검 모드 10/30 요약 — 보관 링크 꺼내 씀 1번 · 링크 없어 못 올림 1개(이름 예약 장어) · 토스 단계 오류 2번(토스 회차 글 RuntimeError) · 남은 보관 링크 2개(3일 안 올린 것 빼면 1개)", s29m
H.toss_mode(s29, TK("2026-11-04 23:59")); assert H.RUN["treuse"] is True and len(s29m) == 3 and "10/31 요약 — 보관 링크 꺼내 씀 0번 · 링크 없어 못 올림 0개 · 남은" in s29m[2] and not lk29  # 끝 분까지 점검(새 링크 X)
H.toss_mode(s29, TK("2026-11-05 00:00")); assert H.RUN["treuse"] is False and lk29 == [1] and len(s29m) == 5 and "11/4 요약" in s29m[3] and s29m[4].startswith("✅ 토스 쉐어링크 점검 끝 — 링크 새로 만들기 확인, 보통 모드로") and "토스 5%·선착순특가 3%" in s29m[4] and "오늘 재사용" not in s29m[4]
assert s29["tlink"]["m"]["1"][0] == "https://toss.im/_m/N1" and s29["tpause"]["back"] == 1  # 지금 베스트 중 품절 아닌 첫 상품(1)으로 만들어 봄(보관 상품은 그사이 발급 제한일 수 있음)
H.toss_mode(s29, TK("2026-11-05 00:14")); H.toss_mode(s29, TK("2026-11-06 09:00")); assert H.RUN["treuse"] is False and lk29 == [1] and len(s29m) == 5  # 복귀 뒤 = 확인·요약·알림 X
H.toss_mode({}, TK("2026-11-05 00:00")); assert H.RUN["treuse"] is False and len(s29m) == 5 and lk29 == [1]  # 점검 중 한 번도 안 돈 seen(새로 시작) = 보통
s29b = {"tlink": {"t": 1, "m": {"7": ["https://toss.im/_m/K7", TK("2026-10-28 10:00")]}}, "tpause": {"t": 1, "d": "2026-11-04"}}; s29m.clear(); lk29.clear(); LF29.append(1)
H.toss_mode(s29b, TK("2026-11-05 00:00")); assert H.RUN["treuse"] is True and lk29 == [1, 2, 4] and len(s29m) == 2 and s29m[1].startswith("⚠️ 토스 쉐어링크 점검 기간(11/4까지)이 끝났는데 링크 새로 만들기가 아직 안 돼요"), s29m  # 안 되면 재사용 그대로 + 알림 1번
H.toss_mode(s29b, TK("2026-11-05 00:30")); assert H.RUN["treuse"] is True and lk29 == [1, 2, 4] and len(s29m) == 2  # 1시간 안 = 다시 안 해 봄 (막히면 베스트 3개까지 해 봄)
H.toss_mode(s29b, TK("2026-11-05 01:01")); assert H.RUN["treuse"] is True and lk29 == [1, 2, 4] * 2 and len(s29m) == 2  # 또 안 됨 = 알림 X
H.tnote(s29b, "miss", "이름 예약 장어"); LF29.clear(); BAD29.add(1); H.toss_mode(s29b, TK("2026-11-05 02:02")); BAD29.clear(); assert H.RUN["treuse"] is False and lk29 == [1, 2, 4] * 2 + [1, 2] and len(s29m) == 3 and s29m[2].startswith("✅") and "(오늘 재사용 모드 동안: 보관 링크 꺼내 씀 0번 · 링크 없어 못 올림 1개(이름 예약 장어))" in s29m[2], s29m  # 복귀 날 메모도 '끝' 알림에
assert H.toss_mode(s29b, TK("2026-11-24 00:00")) is None and "7" not in s29b["tlink"]["m"]  # 보관 14일 지나면 정리
def tg29x(m, **p): raise TimeoutError("read")  # 텔레그램 시간 초과(tg는 HTTPError만 잡음)여도 tpause에 t(seen 정리 KeyError X)·모드 그대로
H.tg = tg29x; s29x = {}; H.toss_mode(s29x, TK("2026-10-30 00:07")); assert H.RUN["treuse"] is True and s29x["tpause"]["t"] == TK("2026-10-30 00:07")
H.tg = lambda m, **p: s29m.append(p.get("text", "")) or {"message_id": 900 + len(s29m)}
# ② toss_link·toss_ok: 재사용 모드 = 발급 X·보관 링크(없으면 None) + 요약 · 보통 = 발급하고 보관
H.RUN["treuse"] = True; s29c = {"tlink": {"t": 1, "m": {"7": ["https://toss.im/_m/K7", 1e12]}}, "tpause": {"t": 1, "d": "2026-10-30"}}; lk29.clear()
assert H.toss_link(s29c, 7, "보관7") == "https://toss.im/_m/K7" and H.toss_link(s29c, 8, "없음8") is None and not lk29 and s29c["tpause"]["ok"] == ["보관7"] and s29c["tpause"]["miss"] == ["없음8"]
assert H.toss_ok(s29c, 7) and H.toss_ok(s29c, "7") and not H.toss_ok(s29c, 8) and H.toss_ok(s29c, "ev:https://toss.im/_m/j")
c29.clear(); assert H.affiliate("https://toss.shopping/t/123") == ("https://toss.shopping/t/123", False) and not c29  # 상품 주소 발급(tacaId)도 점검 땐 안 부름
assert H.aff_note("https://toss.im/_m/K7") == H.TOSS_NOTE  # 재사용 링크도 쉐어링크 = Threads '수수료 딜만'에 안 걸림(대가성 첫 줄 그대로 — Cowork ② 점검 중 예외)
H.RUN["treuse"] = False; assert H.toss_link(s29c, 8) == "https://toss.im/_m/N8" and lk29 == [8] and s29c["tlink"]["m"]["8"][0] == "https://toss.im/_m/N8" and H.toss_ok(s29c, 9)
# ③ 재사용 모드 토스 개별 글(toss_solo): 보관 링크 있는 상품만 Claude에 · 발급 X · 틀 그대로(대가성 첫 줄·💙 머리·게시 시점·💙 버튼 = 보관 링크) · 목록에 없으면 보관 상품(상세로 지금 가격, 머리 출처 X)
ch29 = []; H.tg = lambda m, **p: ch29.append(p) or {"message_id": 950 + len(ch29)}
H.ai_pick = lambda prompt, lines: c29.append(("ai", lines)) or [{"i": 0, "score": 8, "comment": "1개 9,900원"}]
H.EVENTS, H.TOSS_SOLO_HOURS, H.TOSS_GAP_MIN, H.TOSS_NO_CMP = "ev29.json", range(24), 0, True; json.dump([], open("ev29.json", "w")); H.E["THREADS_TOKEN"] = "tk"
s29d = {"tlink": {"t": 1, "m": {"2": ["https://toss.im/_m/K2", 1e12], "7": ["https://toss.im/_m/K7", 1e12 - 1]}}, "tpause": {"t": 1, "d": "2026-10-31"}}
time.time = lambda: TK("2026-10-31 12:05"); H.RUN["treuse"] = True; lk29.clear(); c29.clear(); H.toss_solo(s29d)
(p29,) = ch29
assert not lk29 and [l.split(" |")[0] for l in next(x[1] for x in c29 if x[0] == "ai")] == ["베스트2"]  # 1·4 = 보관 링크 없음, 3 = 품절
assert H.TOSS_NOTE in p29["text"].split("💙")[0] and "💙 토스 특가 · 많이 팔린 순위 2위 🔥\n<b>베스트2</b>\n9,900원 (40%↓) · ⭐ 4.8 (1,234)\n👉 1개 9,900원\n⚠️ 10/31 12:05 게시 시점 가격" in p29["text"], p29["text"]
assert p29["reply_markup"] == {"inline_keyboard": [[{"text": "💙 토스에서 9,900원", "url": "https://toss.im/_m/K2"}]]} and "tb_2" in s29d and s29d["tpause"]["ok"] == ["베스트2"]
q29 = s29d["thtoss"]["q"][-1]; assert q29["link"] == "https://toss.im/_m/K2" and q29["text"].startswith(H.TOSS_NOTE) and "💙 토스 특가 · 많이 팔린 순위 2위 🔥" in q29["text"] and "게시 시점 가격" in q29["text"]  # Threads 채움 후보도 보관 링크
ch29.clear(); c29.clear(); time.time = lambda: TK("2026-10-31 13:05"); H.toss_solo(s29d)  # 13시 = 뷰티·생필품 목록엔 보관 링크 없음 -> 보관 상품(7)
(p29b,) = ch29
assert "💙 토스 특가 🔥\n<b>보관7</b>\n7,700원 (30%↓) · ⭐ 4.5 (99)\n👉 1개 9,900원\n⚠️ 10/31 13:05 게시 시점 가격" in p29b["text"] and p29b["reply_markup"]["inline_keyboard"][0][0] == {"text": "💙 토스에서 7,700원", "url": "https://toss.im/_m/K7"} and not lk29, p29b["text"]
assert any("/products/detail?tacaItemIds=7" in u for u in c29 if isinstance(u, str)) and H.TOSS_NOTE in p29b["text"].split("💙")[0]
ch29.clear(); time.time = lambda: TK("2026-10-31 14:05"); H.toss_solo(s29d); assert not ch29 and not lk29 and "tsolo_20261031_14" in s29d  # 다 3일 안에 올림 -> 안 올림(같은 상품 3일 규칙 그대로)
# ④ 재사용 모드 토스 목록(하루특가 TOP): 보관 링크 있는 것만 · 대가성 첫 줄·💙 머리·게시 시점 끝 줄 · 발급 X
H.E.pop("THREADS_TOKEN", None); s29e = {"tlink": {"t": 1, "m": {"50": ["https://toss.im/_m/K50", 1e12]}}, "tpause": {"t": 1, "d": "2026-10-31"}}; ch29.clear()
time.time = lambda: TK("2026-10-31 10:00"); H.toss_deals(s29e)
(p29c,) = ch29
assert p29c["text"].startswith(f"<i>{H.TOSS_NOTE}</i>\n\n💙 <b>오늘의 토스 하루특가 TOP1</b>") and p29c["text"].endswith("\n\n⚠️ 10/31 10:00 게시 시점 가격") and "https://toss.im/_m/K50" in json.dumps(p29c["reply_markup"]) and not lk29, p29c
# ⑤ 알림 폭탄 X: 점검 중 토스 단계 오류 = 요약으로(보통 땐 바로 알림) · 커뮤니티 토스 딜·이름 예약 = 진우에게 안 물음(진우도 새 링크 못 만듦)
def boom29(s): raise RuntimeError("x")
boom29.__name__ = "toss_solo"; s29f = {"tpause": {"t": 1, "d": "2026-10-31"}}; ch29.clear()
H.step_alert(s29f, boom29, RuntimeError("점검")); assert not ch29 and s29f["tpause"]["err"] == ["토스 자동 개별 글 RuntimeError"]
H.step_alert(s29f, boom29, KeyError("x")); assert len(ch29) == 1 and "토스 자동 개별 글 게시 실패" in ch29[0]["text"] and len(s29f["tpause"]["err"]) == 1  # 토스 API 오류 아님(코드·Claude 등) = 점검 중에도 바로
ch29.clear(); H.RUN["treuse"] = False; H.step_alert(s29f, boom29, RuntimeError("점검")); assert len(ch29) == 1 and "토스 자동 개별 글 게시 실패" in ch29[0]["text"]
H.RUN["treuse"] = True; ch29.clear(); s29g = {"tw_x": {"t": TK("2026-10-31 08:00"), "d": {"title": "[토스] 삼겹살 1kg (9,900원)", "url": "https://www.ppomppu.co.kr/x"}, "p": {"comment": "c", "score": 7}}, "tpause": {"t": 1, "d": "2026-10-31"}}
time.time = lambda: TK("2026-10-31 10:30"); H.toss_wait(s29g); assert not ch29 and s29g["tw_x"]["ask"] == -1 and s29g["tpause"]["miss"][0].startswith("커뮤니티 [토스] 삼겹살")
H.toss_wait(s29g); assert not ch29  # 그만 찾음
json.dump([{"at": "2026-10-31 11:00", "name": "없는상품 500g", "api": True}], open("ev29.json", "w"), ensure_ascii=False); s29h = {"tpause": {"t": 1, "d": "2026-10-31"}}
H.toss_picks(s29h); assert not ch29 and s29h["pk_2026-10-31 11:00"]["asked"] == 1 and s29h["pk_2026-10-31 11:00"]["st"] == "skip" and s29h["tpause"]["miss"] == ["이름 예약 없는상품 500g"]  # st skip = watch '예약 글 안 나감' 알림 X
json.dump([{"at": "2026-11-05 07:00", "name": "없는상품 500g", "api": True}], open("ev29.json", "w"), ensure_ascii=False); s29k = {"tpause": {"t": 1, "d": "2026-11-04"}}
time.time = lambda: TK("2026-11-04 23:30"); H.toss_picks(s29k); r29k = s29k["pk_2026-11-05 07:00"]
assert not ch29 and "asked" not in r29k and "st" not in r29k and "miss" not in s29k["tpause"]  # 점검 뒤(11/5 07:00) 예약 = 안 묻고 끝내지도 않음 -> 복귀 뒤 다시 찾음(10/22 리뷰)
sl29, H.store_link = H.store_link, lambda u: c29.append(("store", u)) or ""; c29.clear(); r29m = {}
H.toss_match(s29k, r29m, "[토스] 휴지 (1원)", "https://bbs.ruliweb.com/market/board/1020/read/1", []); assert ("store", "https://bbs.ruliweb.com/market/board/1020/read/1") not in c29 and "src" not in r29m  # 상품 주소 1번 읽기는 점검 뒤로 아껴 둠
H.store_link = sl29
# ⑥ 미리 만들기(10/28~29, 4시간마다): 베스트·하루특가·생필품·뷰티 중 품절 아닌 새 상품(이미 보관 X) · 다른 날·재사용 모드 = X
H.RUN["treuse"] = False; s29i = {"tlink": {"t": 1, "m": {"2": ["https://toss.im/_m/K2", 1]}}}; lk29.clear(); json.dump([], open("ev29.json", "w"))
time.time = lambda: TK("2026-10-27 23:59"); H.toss_stock(s29i); assert not lk29
time.time = lambda: TK("2026-10-28 00:10"); H.toss_stock(s29i); assert sorted(lk29) == [1, 4, 50, 201, 401] and s29i["tlink"]["m"]["4"][0] == "https://toss.im/_m/N4", lk29  # 품절(3)·보관(2)·가전(900) X
lk29.clear(); time.time = lambda: TK("2026-10-28 04:09"); H.toss_stock(s29i); assert not lk29 and not any("best-selling" in u for u in c29[-1:])  # 4시간 안 = API도 안 부름
L29["best-selling"].append({"tacaItemId": 6, "displayName": "베스트6", "displayPrice": 1, "isSoldOut": False}); time.time = lambda: TK("2026-10-29 23:00"); H.toss_stock(s29i); assert lk29 == [6]
LF29.append(1); L29["best-selling"].append({"tacaItemId": 8, "displayName": "베스트8", "displayPrice": 1, "isSoldOut": False}); s29i["tstock"]["t"] = 0; lk29.clear(); H.toss_stock(s29i); assert lk29 == [8] and "8" not in s29i["tlink"]["m"] and s29i["tstockbad"]["ids"] == [8]  # 막힌 상품은 빼 둠
s29i["tstock"]["t"] = 0; lk29.clear(); H.toss_stock(s29i); assert not lk29  # (다시 안 함)
LF29.clear(); H.RUN["treuse"] = True; s29i["tstock"]["t"] = 0; lk29.clear(); H.toss_stock(s29i); assert not lk29
H.RUN["treuse"], tsr29, H.TOSS_STOCK_RUN = False, H.TOSS_STOCK_RUN, 2; s29j = {}; lk29.clear()  # 한 실행 발급 수 제한(실행 6분 한도) — 남으면 다음 실행에 이어서
H.toss_stock(s29j); assert len(lk29) == 2; H.toss_stock(s29j); assert len(lk29) == 4; H.toss_stock(s29j); assert len(lk29) == 6; H.toss_stock(s29j); assert len(lk29) == 8; H.toss_stock(s29j); assert len(lk29) == 8 and len(set(lk29)) == 8 and tsr29 == 30  # 8개 = 2·2·2·2 -> 다 했으면 4시간 쉼
H.TOSS_STOCK_RUN = tsr29
LF29.clear(); BAD29.update({1}); s29l = {}; lk29.clear(); H.toss_stock(s29l); assert lk29[0] == 1 and len(lk29) == 8 and "1" not in s29l["tlink"]["m"] and len(s29l["tlink"]["m"]) == 7  # 발급 제한 1개 = 그것만 빼고 계속(10/22 리뷰 — 예전엔 맨 앞에서 매번 멈춤)
BAD29.update({2, 4}); s29l = {}; lk29.clear(); H.toss_stock(s29l); assert lk29 == [1, 2, 4] and s29l["tstock"]["q"][:1] == [6]  # 3번 연달아 막힘 = 이번 실행 멈춤(남은 줄은 다음 실행)
c29.clear(); BAD29.clear(); lk29.clear(); H.toss_stock(s29l); assert len(lk29) == 5 and not any("best-selling" in u for u in c29 if isinstance(u, str))  # 이어서(목록 다시 안 읽음 — 조회 상한)
H.RUN["treuse"] = False; L29["best-selling"][-2:] = []
(H.http, H.tg, H.ai_pick, H.EVENTS, time.time, H.HAS_TOSS, H.TOSS_SOLO_HOURS, H.TOSS_GAP_MIN, H.TOSS_NO_CMP) = sv29; H.E.pop("THREADS_TOKEN", None); json.dump([], open("posts.json", "w"))
# 9-30 (10/22 15:5x Cowork·진우 '잘 되는 제품은 꾸준하게'): ① metrics 줄 상품 칸(kind deal·list·etc, 상품명·제휴 링크·토스 상품 id, 목록 = urls)
#      ② 잘 된 상품 표 top.json(지난 14일 Threads 개별 글 조회 v48(없으면 views) 상위 20% ∪ 답글 상위 20%(1개↑), 상품별, 하루 1번 — 예전 줄은 Threads 글을 다시 읽어 채움)
#      ③ 토스 개별·토스 픽 채움 후보 = 표의 토스 상품이면 +1점·먼저(하루 2번)
A30, C30 = "https://toss.im/_m/A", "https://link.coupang.com/a/b"
assert H.prod_cols("🏆 리스트", "묶음", [None, A30, C30, "https://www.ppomppu.co.kr/zboard/view.php?id=1", A30], {}) == {"kind": "list", "name": "🏆 리스트", "urls": [A30, C30]}  # 출처(커뮤니티) 링크 X, 같은 링크 1번
assert H.prod_cols("[토스] 휴지 30롤 (9,900원)", "생필품", [A30, "https://bbs.ruliweb.com/x"], {A30: 7}) == {"kind": "deal", "name": "휴지 30롤", "url": A30, "tid": 7}  # 우리 쉐어링크 = 토스 상품 id
assert H.prod_cols("🗳️ 투표", "투표", [C30], {}) == {"kind": "etc"} and H.prod_cols("x", "기타", ["https://t.me/hotdeal_pick"], {}) == {"kind": "etc"} and H.prod_cols("[쿠팡] 샴푸 (1원)", "묶음", [C30, A30], {}, deal=True)["kind"] == "deal"
assert [H.prod_cols("오늘 밤 특가 미리보기 (5개)", "기타", [u], {}) for u in ("https://hotdealpick.kr/?ref=th", H.GOLDBOX, H.CP_HOME, H.BLOG + "/1")] == [{"kind": "etc"}] * 4  # 사이트 첫 화면·골드박스·쿠팡 홈·블로그 = 상품 X(리뷰)
assert H.prod_cols("x", "기타", ["https://hotdealpick.kr/p/12.html?ref=th"], {})["url"] == "https://hotdealpick.kr/p/12.html?ref=th" and H.prod_cols("📋 모음", "기타", [C30], {}, deal=False) == {"kind": "etc"}  # 사이트 딜 페이지 = 상품 · Threads 개별 딜 아님(10/18~ ab 없음) = 링크 1개여도 X
assert H.prod_cols("[쿠팡] 물티슈 (5,000원)", "생필품", [], {}, deal=True) == {"kind": "deal", "name": "물티슈"}  # B 글 링크를 못 읽어도 이름으로
assert "[ ! -f top.json ] || git add top.json" in open(os.path.join(os.path.dirname(os.path.abspath(H.__file__)), ".github/workflows/hotdeal.yml")).read()  # Actions가 top.json도 커밋
sv30 = (H.http, time.time, H.METRICS_HOUR, H.E.get("THREADS_TOKEN")); H.METRICS_HOUR, H.E["THREADS_TOKEN"] = 5, "tk"; c30 = []
th30 = lambda i, d, v, url=None, name="", tid=None, rep=0, v48=None, **kw: {"date": d, "ch": "th", "id": i, "shop": "toss" if tid else "coupang", "cat": "생필품", "price": "", "at": "12:00", "views": v, "react": 0, "likes": 0, "replies": rep,
                                                                              **({"v48": v48} if v48 else {}), **({"kind": "deal", "name": name, "url": url, **({"tid": tid} if tid else {})} if url else {}), **kw}
R30 = {"2026-10-07": [th30("old", "2026-10-07", 5000, "https://link.coupang.com/a/OLD", "옛날")],  # 14일 전 = X
       "2026-10-15": [th30("a", "2026-10-15", 900, "https://link.coupang.com/a/U1", "쿠팡A")] + [th30(f"f{k}", "2026-10-15", 10 + k * 10, f"https://link.coupang.com/a/F{k}", f"채움{k}") for k in range(5)],
       "2026-10-18": [th30("c", "2026-10-18", 1000, "https://toss.im/_m/T7a", "토스7", tid=7), th30("o1", "2026-10-18", 700, ab="A"), th30("o2", "2026-10-18", 5, ab="B", rep=1), th30("o3", "2026-10-18", 3),
                      th30("bb", "2026-10-18", 2, "https://link.coupang.com/a/BB", "B 글", rep=1, ab="B")],  # B 글 답글 1 = 우리 링크 댓글(리뷰) -> 답글 상위 X
       "2026-10-20": [th30("b", "2026-10-20", 300, "https://link.coupang.com/a/U1", "쿠팡A 다시"), th30("f", "2026-10-20", 100, "https://link.coupang.com/a/U3", "쿠팡B", v48=850),
                      th30("r", "2026-10-20", 20, "https://link.coupang.com/a/U4", "답글 많은 것", rep=5)],
       "2026-10-21": [th30("d", "2026-10-21", 50, "https://toss.im/_m/T7b", "토스7", tid=7),
                      {"date": "2026-10-21", "ch": "tg", "id": 1500, "shop": "coupang", "cat": "생필품", "price": "", "at": "22:00", "views": 9, "react": 0, "kind": "deal", "name": "쿠팡A", "url": "https://link.coupang.com/a/U1"}]}
json.dump({d: {"at": "", "miss": {}, "rows": rs} for d, rs in R30.items()}, open(H.METRICS, "w"), ensure_ascii=False)
def h30(url, body=None, headers=None, method=None):
    c30.append(url)
    if "/o1?fields=text" in url: return json.dumps({"text": f"{H.DISCLOSURE}\n\n🔥 [쿠팡] 휴지 (9,900원)\n\n👉 https://link.coupang.com/a/O1\n📲 실시간 알림 t.me/hotdeal_pick"})
    if "/o2?fields=text" in url: return json.dumps({"text": f"{H.DISCLOSURE}\n\n🔥 [쿠팡] 물티슈 (5,000원)"})
    if "/o2/replies?fields=text" in url: return json.dumps({"data": [{"text": "👉 https://link.coupang.com/a/O2"}]})
    if "/o3?fields=text" in url: return json.dumps({"text": "🗳️ 오늘 투표"})
    raise AssertionError(url)
H.http, s30 = h30, {"mt_2026-10-21": 1}; os.path.exists(H.TOP) and os.remove(H.TOP)  # (앞 9-11 metrics가 만든 표)
time.time = lambda: TK("2026-10-22 04:59"); H.top_build(s30); assert not c30 and not os.path.exists(H.TOP)  # 5시 전 X
time.time = lambda: TK("2026-10-22 06:00"); H.top_build({}); assert not c30 and not os.path.exists(H.TOP)  # 어제 줄 아직(8시 전) X
time.time = lambda: TK("2026-10-22 16:30"); H.top_build(s30)
T30 = json.load(open(H.TOP)); M30 = {r["id"]: r for d in json.load(open(H.METRICS)).values() for r in d["rows"]}
assert (M30["o1"]["kind"], M30["o1"]["url"], M30["o1"]["name"], M30["o2"]["url"], M30["o3"]["kind"]) == ("deal", "https://link.coupang.com/a/O1", "휴지", "https://link.coupang.com/a/O2", "etc"), M30  # 예전 줄 채움(B = 링크 댓글)
assert T30["d"] == "2026-10-22" and T30["posts"] == 14 and T30["days"] == 14 and "상위 20%" in T30["rule"]  # 개별 글 14개(14일 전·투표 X) -> 상위 3개 + 답글
assert [(x["key"], x["best"], x["n"], x["last"]) for x in T30["items"]] == [("toss:7", 1000, 2, "2026-10-21 12:00"), ("https://link.coupang.com/a/U1", 900, 2, "2026-10-21 22:00"),
                                                                            ("https://link.coupang.com/a/U3", 850, 1, "2026-10-20 12:00"), ("https://link.coupang.com/a/U4", 20, 1, "2026-10-20 12:00")], T30["items"]  # 토스 = 상품 id로 묶음(링크 달라도) · v48 먼저 · 답글 5개 · 마지막 게시 = tg 포함
assert T30["items"][1] == {"key": "https://link.coupang.com/a/U1", "name": "쿠팡A", "url": "https://link.coupang.com/a/U1", "mall": "coupang", "best": 900, "replies": 0, "n": 2, "last": "2026-10-21 22:00"}
assert sum(1 for l in open(H.TOP, encoding="utf-8") if l.startswith('{"key"')) == 4  # 상품 1개 = 1줄
c30.clear(); H.top_build(s30); assert not c30 and json.load(open(H.TOP))["at"] == T30["at"]  # 하루 1번
json.dump({d: {"at": "", "miss": {}, "rows": rs} for d, rs in R30.items()}, open(H.METRICS, "w"), ensure_ascii=False); os.remove(H.TOP); ft30, H.TOP_FILL = H.TOP_FILL, 2
H.top_build(s30); assert json.load(open(H.TOP))["d"] == "" and len(c30) == 3; H.top_build(s30); assert json.load(open(H.TOP))["d"] == "2026-10-22" and len(c30) == 4  # 한 실행 2개씩 — 다 채운 뒤에 그날 끝
H.TOP_FILL = ft30
def h30b(url, body=None, headers=None, method=None):  # 댓글 권한 없음(code 10) · o3 = 서버 오류(500)
    c30.append(url)
    if "/replies?" in url or "/o3?" in url:
        e = H.urllib.error.HTTPError(url, 500 if "/o3?" in url else 403, "x", {}, None); e.body = '{"error":{"code":10}}'; raise e
    return h30(url)
json.dump({d: {"at": "", "miss": {}, "rows": rs} for d, rs in R30.items()}, open(H.METRICS, "w"), ensure_ascii=False); os.remove(H.TOP); H.http = h30b; c30.clear()
H.top_build(s30); M30 = {r["id"]: r for d in json.load(open(H.METRICS)).values() for r in d["rows"]}
assert M30["o2"]["kind"] == "deal" and M30["o2"]["name"] == "물티슈" and "url" not in M30["o2"] and "kind" not in M30["o3"] and json.load(open(H.TOP))["d"] == ""  # 댓글 권한 없음 = 이름으로 · 500 = 그 줄부터 다음 실행에
# 사이트 딜 페이지 링크(10/19 전 Threads 글) = posts.json 그 글의 구매 링크·상품명·몰 · 💸 훅 첫 줄은 상품명 X
json.dump([{"t": "2026-10-14 12:00", "text": "x", "url": None}] * 3 + [{"t": "2026-10-14 12:00", "text": "🔥 [쿠팡] 펩시 제로 라임 48캔 (26,550원)", "url": "https://link.coupang.com/a/PEP"}], open(H.POSTS, "w"), ensure_ascii=False)
R30c = {"2026-10-20": [th30("s1", "2026-10-20", 900, "https://hotdealpick.kr/p/3.html?ref=th", "쿠팡보다 260원 싸요"), th30("s2", "2026-10-20", 5, "https://hotdealpick.kr/p/1.html?ref=th", "y"), th30("s3", "2026-10-20", 4, ab="A")]}
def h30d(url, body=None, headers=None, method=None):
    c30.append(url); return json.dumps({"text": f"{H.DISCLOSURE}\n\n💸 쿠팡보다 500원 싸요\n🔥 [쿠팡] 휴지 (9,900원)\n\n👉 https://link.coupang.com/a/S3"})
json.dump({d: {"at": "", "miss": {}, "rows": rs} for d, rs in R30c.items()}, open(H.METRICS, "w"), ensure_ascii=False); os.remove(H.TOP); H.http = h30d; H.top_build(s30)
M30 = {r["id"]: r for d in json.load(open(H.METRICS)).values() for r in d["rows"]}
assert (M30["s1"]["url"], M30["s1"]["name"], M30["s1"]["shop"]) == ("https://link.coupang.com/a/PEP", "펩시 제로 라임 48캔", "coupang") and M30["s2"]["url"] == "https://hotdealpick.kr/p/1.html?ref=th" and M30["s3"]["name"] == "휴지", M30  # (구매 링크 없는 글 = 그대로)
assert json.load(open(H.TOP))["items"][0]["url"] == "https://link.coupang.com/a/PEP" and os.path.exists(H.POSTS); json.dump([], open(H.POSTS, "w"))
H.http = h30b
# 토스 글 id 없음(10/22 전 링크) = 같은 이름끼리(토스 = tname, id 있는 글이 있으면 그 id로) · 쿠팡 링크 모르는 글 = 같은 이름 글의 링크
R30b = {"2026-10-20": [th30("t1", "2026-10-20", 900, "https://toss.im/_m/OLD1", "토스 휴지 30롤", shop="toss"), th30("t2", "2026-10-20", 10, "https://toss.im/_m/OLD2", "토스 휴지 30롤", shop="toss"),
                       th30("t3", "2026-10-20", 800, "https://toss.im/_m/OLD3", "토스7 상품", shop="toss"), th30("t4", "2026-10-21", 5, "https://toss.im/_m/NEW", "토스7 상품", tid=7)] + [th30(f"z{k}", "2026-10-20", 1, f"https://link.coupang.com/a/Z{k}", f"z{k}") for k in range(6)]}
json.dump({d: {"at": "", "miss": {}, "rows": rs} for d, rs in R30b.items()}, open(H.METRICS, "w"), ensure_ascii=False); os.remove(H.TOP); H.top_build(s30)
assert [(x["key"], x["n"]) for x in json.load(open(H.TOP))["items"]] == [("tname:토스휴지30롤", 2), ("toss:7", 2)] and H.top_toss({}, TK("2026-10-22 16:30")) == ({7}, {"토스휴지30롤"})
assert H.top_hit(({7}, {"토스휴지30롤"}), 99, "토스 휴지 30롤") and not H.top_hit(({7}, set()), 99, "x")
# ③ 토스 개별 글: 표의 토스 상품(id 2) = +1점(6점 -> 7점 = 올림) · 하루 2번까지 · 표 없으면 6점 X
json.dump({"d": "2026-10-23", "items": [{"key": "toss:2", "name": "베스트2"}, {"key": "https://link.coupang.com/a/U1"}]}, open(H.TOP, "w"), ensure_ascii=False)
ch30 = []; sv30b = (H.tg, H.ai_pick, H.EVENTS, H.TOSS_SOLO_HOURS, H.TOSS_GAP_MIN, H.TOSS_NO_CMP, H.HAS_TOSS)
H.HAS_TOSS, H.http, H.tg, H.EVENTS, H.TOSS_SOLO_HOURS, H.TOSS_GAP_MIN, H.TOSS_NO_CMP = True, h29, (lambda m, **p: ch30.append(p) or {"message_id": 990 + len(ch30)}), "ev29.json", range(24), 0, True
H.ai_pick = lambda prompt, lines: [{"i": 1, "score": 6, "comment": "c"}]; H.RUN["treuse"] = False; json.dump([], open("ev29.json", "w")); H.E.pop("THREADS_TOKEN", None)
assert H.top_toss({}, TK("2026-10-23 12:05")) == ({2}, set())
s30b = {}; time.time = lambda: TK("2026-10-23 12:05"); H.E["THREADS_TOKEN"] = "tk"; H.toss_solo(s30b); H.E.pop("THREADS_TOKEN")
assert len(ch30) == 1 and "베스트2" in ch30[0]["text"] and s30b["topb"]["ids"] == [2] and "tb_2" in s30b and s30b["thtoss"]["q"][-1]["s"] == 6 and s30b["thtoss"]["q"][-1]["n"] == "베스트2"  # 줄엔 원래 점수(가산은 채움에서 따로)
ch30.clear(); s30c = {"topb": {"t": 1, "d": "2026-10-23", "ids": [1, 99]}}; H.toss_solo(s30c); assert not ch30 and s30c["topb"]["ids"] == [1, 99]  # 하루 2개 다 씀 = 가산 X(6점 그대로)
os.remove(H.TOP); H.toss_solo({}); assert not ch30  # 표 없음 = 6점 X
# 토스 픽 채움(Threads): 표의 토스 상품 먼저(대기 순서 상관없이) + 횟수
json.dump({"d": "2026-10-21", "items": [{"key": "toss:2109"}]}, open(H.TOP, "w")); json.dump([], open("posts30.json", "w"))
sv30c = (H.POSTS, H.TH_SOLO_FILL); H.http, H.POSTS, H.TH_SOLO_FILL, H.E["THREADS_TOKEN"] = http21, "posts30.json", True, "tk"
s30d = {"thtoss": {"t": 1, "q": [tq21(5, "20:00", 0), tq21(9, "20:05", 1)]}}
g30, log30 = run21(s30d, "20:40"); assert g30 == ["토스9", "토스5"] and s30d["topb"]["ids"] == [2109], (g30, log30)  # (셀프체크는 한 실행 3개) 표의 9 = 순위 한 칸·점수 +1 -> 바로 앞 순위(5)보다 먼저, 횟수는 9만
s30e = {"topb": {"t": 1, "d": "2026-10-21", "ids": [2109]}, "thtoss": {"t": 1, "q": [tq21(9, "20:05", 1)]}}; run21(s30e, "20:40"); assert s30e["topb"]["ids"] == [2109]  # 같은 상품(채널 글로 이미 셈) = 1번만(리뷰)
s30f = {"thtoss": {"t": 1, "q": [tq21(5, "20:00", 0), tq21(9, "20:05", 3)]}}; g30, _ = run21(s30f, "20:40"); assert g30 == ["토스5", "토스9"]  # 순위 3칸 뒤 = 한 칸만 당겨져서 5 먼저(점수 +1, 맨 앞 고정 X — 리뷰)
def h30c(url, body=None, headers=None, method=None):  # 10/18~ Threads 글: th_deal 기록(thab) 없는 링크 1개 글(카드 모음 등) = 개별 딜 아님
    if url.startswith(H.CHANNEL_WEB): return ""
    if "/me/threads?" in url: return json.dumps({"data": [{"id": "x1", "text": "📋 10/20 오늘의 핫딜 모음\n1. 휴지\n👉 https://link.coupang.com/a/Q1", "timestamp": "2026-10-20T03:00:00+0000"},
                                                          {"id": "x2", "text": "B 글 본문(주소 없음)", "timestamp": "2026-10-20T04:00:00+0000"}]})
    if "/insights?" in url: return json.dumps({"data": [{"name": n, "values": [{"value": 1}]} for n in ("views", "likes", "replies", "reposts", "quotes")]})
    raise AssertionError(url)
H.http, H.E["METRICS_DAY"], H.E["THREADS_TOKEN"] = h30c, "2026-10-20", "tk"; H.E.pop("IG_TOKEN", None)
H.metrics_rows({"thab": {"m": {"x2": {"ab": "B", "ts": 1, "u": "https://toss.im/_m/Q2", "n": "[토스] 휴지 30롤 (9,900원)"}}}, "tlink": {"t": 1, "r": {"https://toss.im/_m/Q2": [5, 1]}}})
K30 = {r["id"]: r for r in json.load(open(H.METRICS))["2026-10-20"]["rows"]}; H.E.pop("METRICS_DAY")
assert K30["x1"]["kind"] == "etc" and (K30["x2"]["kind"], K30["x2"]["name"], K30["x2"]["url"], K30["x2"]["tid"]) == ("deal", "휴지 30롤", "https://toss.im/_m/Q2", 5), K30  # B 글 = thab 링크 · 토스 링크 -> 상품 id
(H.POSTS, H.TH_SOLO_FILL) = sv30c; (H.tg, H.ai_pick, H.EVENTS, H.TOSS_SOLO_HOURS, H.TOSS_GAP_MIN, H.TOSS_NO_CMP, H.HAS_TOSS) = sv30b
(H.http, time.time, H.METRICS_HOUR, tk30) = sv30; H.E.pop("THREADS_TOKEN", None) if tk30 is None else H.E.update(THREADS_TOKEN=tk30)
for f30 in (H.TOP, H.METRICS, "posts30.json"):
    os.path.exists(f30) and os.remove(f30)
# 9-32 (10/22 20:0x 진우 '꾸준템 리스트도'): 하루 1번 19:50(KST, 21시 전) 채널·Threads '👍 꾸준히 팔리는 것 모음' 최대 5개 —
#       후보 = ① 14일 진우 👍 글(최근 것부터·품절 표시 X) → ② top.json(수수료 링크, 토스 = 상세 API 가격·리뷰·품절) → ③ 진우 🛒 중 한 달 1,000명+ 구매, 같은 링크·이름 1번
#       대가성 문구 맨 앞·게시 시점 줄 · 묶음 글 10분 안 = 다음 실행 · 후보 0개 = 그 회차 생략 · 사이트 steady.html
sv32 = (H.tg, H.POSTS, H.TOP, H.HAS_TOSS, H.STEADY_FILE, time.time, H.toss, H.th_post, H.E.get("THREADS_TOKEN"))
ch32, th32, tc32 = [], [], []
H.tg = lambda method, **p: ch32.append(p) or {"message_id": 1}
H.th_post = lambda tok, text, link=None, image=None, tag="핫딜": th32.append((text, link)) or "t1"
def toss32(path, body=None):
    tc32.append(path); ids = path.split("=")[1].split(",")
    return {"items": [{"tacaItemId": int(i), "displayName": f"토스{i}", "displayPrice": 12900, "reviewCount": 5432, "isSoldOut": i == "78"} for i in ids]}
H.toss, H.HAS_TOSS, H.POSTS, H.TOP, H.STEADY_FILE, H.E["THREADS_TOKEN"] = toss32, True, "posts32.json", "top32.json", "steady32/steady.json", "tk"
cp32 = lambda mid, at, body, url=None, own=1: {"t": at, "url": url or f"https://link.coupang.com/a/S{mid}", "mid": mid, **({"own": 1} if own else {}), "text": f"{H.DISCLOSURE}\n\n{body}"}
STD32 = "🚀 쿠팡 · 꾸준히 팔리는 상품 👍\n{n}\n{p} · 한 달 1,000명+ 구매 · 리뷰 1,969\n🎁 선물 포장"
P32 = [cp32(3101, "2026-10-22 20:30", STD32.format(n="록시땅 시어 버터 핸드크림 75ml", p="25,800원")),
       cp32(3102, "2026-10-22 18:00", "🛒 [쿠팡] 해피데이 핫팩 100g 30개 (9,900원)\n\n🤔 솔직히 특가로는 약한 제품\n⭐ 리뷰 3,210 · 한 달 2,000명 이상 구매"),
       cp32(3103, "2026-10-22 18:10", "🛒 [쿠팡] 적게 팔린 것 (5,000원)\n\n🤔 솔직히 특가로는 약한 제품\n한 달 500명 이상 구매"),
       cp32(3104, "2026-10-22 18:20", STD32.format(n="네이버 꾸준템", p="7,000원"), url="https://search.shopping.naver.com/search/all?query=x"),  # 수수료 링크 아님
       cp32(3105, "2026-10-01 18:20", STD32.format(n="오래된 꾸준템", p="7,000원")),  # 14일 지남
       cp32(3106, "2026-10-22 18:30", STD32.format(n="토스 꾸준템", p="7,000원"), url="https://toss.shopping/_m/T3106"),  # 토스 채널 글 = 후보 X(품절 기록이 그날만 — 토스는 API로만)
       cp32(3107, "2026-10-22 12:00", "🔥 [쿠팡] 펩시 제로 라임 48캔 (26,550원)\n\n쿠팡보다 싸요", own=0),
       cp32(3108, "2026-10-23 10:00", STD32.format(n="꾸준 세제 3L", p="15,900원").replace("한 달 1,000명+ 구매 · 리뷰 1,969", "한 달 1만명+ 구매 · 리뷰 1.6만")),
       cp32(3109, "2026-10-22 13:00", "🔥 [쿠팡] 제휴 아님 상품 (3,000원)\n\n좋음", url="https://www.coupang.com/vp/products/1", own=0),  # top.json에 있어도 수수료 링크 아님
       cp32(3110, "2026-10-22 17:00", "🛒 [쿠팡] 만명 핫팩 (8,800원)\n\n🤔 솔직히 특가로는 약한 제품\n⭐ 리뷰 17.9만 · 한 달 3만명+ 구매"),  # 만 단위 = 3만 > 2,000
       cp32(3111, "2026-10-21 13:00", "🔥 [토스] 토스 옛 글 (1,000원)\n\n좋음", url="https://toss.shopping/_m/T80", own=0)]  # id 못 찾는 토스 표 상품 = 옛 채널 글 가격 X
json.dump(P32, open("posts32.json", "w"), ensure_ascii=False)
json.dump({"d": "2026-10-22", "items": [{"key": "toss:77", "name": "베베앙 물티슈 10팩", "url": "https://toss.shopping/_m/T77"}, {"key": "toss:78", "name": "품절 토스", "url": "https://toss.shopping/_m/T78"},
                                        {"key": "https://link.coupang.com/a/S3107", "name": "펩시", "url": "https://link.coupang.com/a/S3107"}, {"key": "x", "name": "제휴 아님", "url": "https://www.coupang.com/vp/products/1"},
                                        {"key": "https://link.coupang.com/a/S3101", "name": "록시땅", "url": "https://link.coupang.com/a/S3101"},
                                        {"key": "tname:토스물티슈79", "name": "토스 물티슈79", "url": "https://toss.shopping/_m/T79"},  # id = 우리 쉐어링크 기록(tlink)
                                        {"key": "tname:캐시이름", "name": "캐시 상품", "url": "https://toss.shopping/_m/T81"},  # id = 1일 목록 이름
                                        {"key": "tname:토스옛글", "name": "토스 옛 글", "url": "https://toss.shopping/_m/T80"}]}, open("top32.json", "w"), ensure_ascii=False)
s32 = {"tlink": {"t": 1, "r": {"https://toss.shopping/_m/T79": [79, 1]}}, "tosscache": {"t": 1, "items": [[81, "캐시 이름", 1000, 1]]}}
time.time = lambda: TK("2026-10-23 19:49"); H.steady_list(s32); assert not ch32 and "steady_20261023" not in s32  # 19:50 전 X
time.time = lambda: TK("2026-10-23 19:52"); o32 = io.StringIO()
with contextlib.redirect_stdout(o32): H.steady_list(s32)
(c32,) = ch32; x32 = c32["text"]
assert x32.startswith(f"<i>{H.DISCLOSURE}</i>\n<i>{H.TOSS_NOTE}</i>\n\n👍 <b>꾸준히 팔리는 것 모음</b>\n최저가는 아니어도 꾸준히 많이 사는 것\n\n1️⃣ <a href=\"https://link.coupang.com/a/S3108\"><b>꾸준 세제 3L</b></a>\n💰 <b>15,900원</b> · 한 달 1만명+ 구매\n\n2️⃣ "), x32
assert [b[0]["text"][:4] for b in c32["reply_markup"]["inline_keyboard"]] == [f"{n} " for n in H.NUM] and [b[0]["url"] for b in c32["reply_markup"]["inline_keyboard"]] == \
    ["https://link.coupang.com/a/S3108", "https://link.coupang.com/a/S3101", "https://toss.shopping/_m/T77", "https://link.coupang.com/a/S3107", "https://toss.shopping/_m/T79"], c32  # 👍 최근 순 → 표(토스·링크 순서 그대로)
assert "💰 <b>25,800원 (10/22 글 가격)</b> · 한 달 1,000명+ 구매" in x32 and "💰 <b>12,900원</b> · 리뷰 5,432" in x32 and "💰 <b>26,550원 (10/22 글 가격)</b>\n" in x32 and x32.endswith("\n\n⚠️ 10/23 19:52 게시 시점 가격"), x32  # 지난 글 가격 = 그 글 날짜
assert not re.search("적게 팔린|네이버 꾸준템|오래된|토스 꾸준템|제휴 아님|토스78|품절 토스|토스 옛 글", x32) and tc32 == ["/products/detail?tacaItemIds=77,78,79,81"] and "steady 5 items" in o32.getvalue(), (x32, tc32)
(tx32, tl32), = th32; assert tx32.startswith(f"{H.DISCLOSURE}\n{H.TOSS_NOTE}\n\n👍 꾸준히 팔리는 것 모음\n\n1️⃣ 꾸준 세제 3L 15,900원 · 한 달 1만명+ 구매\n👉 https://link.coupang.com/a/S3108\n") and len(tx32) <= 480 and tl32 == "https://link.coupang.com/a/S3108", tx32
tc32.clear(); H.steady_cands({**s32, "tossid": {"t": 1, "m": {"https://toss.shopping/_m/T80": [8000, 1, 1, "ok", [], 1000, False, 80]}}}, TK("2026-10-23 19:52"))
assert tc32 == ["/products/detail?tacaItemIds=77,78,79,81,80"], tc32  # 10/23 Cowork 확인: 상세 id = 전부 옵션 id(tacaItemId) — 진우 쉐어링크는 tossid 8칸째(own_end가 tacaIds로 확인), 주소 /t/번호(그룹 id) X
H.STEADY_N = 9; n32 = [x["n"] for x in H.steady_cands(s32, TK("2026-10-23 19:52"))]; H.STEADY_N = 5
assert n32 == ["꾸준 세제 3L", "록시땅 시어 버터 핸드크림 75ml", "베베앙 물티슈 10팩", "펩시 제로 라임 48캔", "토스 물티슈79", "캐시 상품", "만명 핫팩", "해피데이 핫팩 100g 30개"], n32  # 상한 없이: 🛒 = 한 달 3만 > 2,000 순(500명·수수료 아님·14일·토스 글·id 없는 토스 X)
assert "steady_20261023" in s32 and s32["bundles"]["ts"]; ch32.clear(); th32.clear(); H.steady_list(s32); assert not ch32  # 하루 1번
sj32 = json.load(open("steady32/steady.json")); assert sj32["at"] == "2026-10-23 19:52" and len(sj32["items"]) == 5 and sj32["notes"] == [H.DISCLOSURE, H.TOSS_NOTE]
assert all(not x["p"] and not x["st"] for x in sj32["items"] if x["i"] is None and "toss.shopping" in x["u"]) and any(x["i"] is None and "toss.shopping" in x["u"] for x in sj32["items"])  # 토스 API 가격·리뷰 = 사이트 파일 X(10/23 Cowork 정정 — 채널·Threads 목록엔 그대로)
su32 = S.steady_page("steady32"); hp32 = open("steady32/steady.html").read()
assert su32 == (f"{S.BASE}steady.html", "2026-10-23") and "👍 꾸준히 팔리는 것 모음" in hp32 and 'href="https://toss.shopping/_m/T77" rel="nofollow sponsored noopener"' in hp32 and "10/23 19:52 게시 시점 가격" in hp32 and html.escape(H.TOSS_NOTE) in hp32 and "💰 가격은 링크에서 확인" in hp32
assert S.steady_page("없는폴더32") is None  # 리스트 전 = 페이지 X
s32 = {"bundles": {"t": 1, "ts": [TK("2026-10-24 19:45")]}}; time.time = lambda: TK("2026-10-24 19:52"); H.steady_list(s32); assert not ch32 and "steady_20261024" not in s32  # 다른 묶음 글 10분 안 = 다음 실행
json.dump([], open("posts32.json", "w")); json.dump({"items": []}, open("top32.json", "w")); s32 = {}; o32 = io.StringIO()
with contextlib.redirect_stdout(o32): H.steady_list(s32)
assert not ch32 and not th32 and "steady_20261024" in s32 and "steady 후보 0개 — 이번 회차 생략" in o32.getvalue()  # 후보 0개 = 그 회차 생략
time.time = lambda: TK("2026-10-25 21:00"); H.steady_list({}); assert not ch32  # 21시 넘으면 그날은 X
assert (H.STEADY_AT, H.STEADY_END, H.STEADY_N, H.STEADY_DAYS, H.STEADY_MIN_BUY) == ("19:50", "21:00", 5, 14, 1000) and "steady_list" in H.ALERT_STEPS
(H.tg, H.POSTS, H.TOP, H.HAS_TOSS, H.STEADY_FILE, time.time, H.toss, H.th_post, tk32) = sv32; H.E.pop("THREADS_TOKEN", None) if tk32 is None else H.E.update(THREADS_TOKEN=tk32)
for f32 in ("posts32.json", "top32.json"):
    os.remove(f32)
shutil.rmtree("steady32")
# 9-33 (10/22 22시 진우 '인스타 자동게시 테스트 1건 — 시간 오차 15~20분·카드 수정·사람 멘트'): 인스타만(텔레그램·Threads X), IG_AUTO 정기 게시는 그대로 꺼짐,
#       ig_test.txt 날짜 = 그날 하루 카드를 변주로 다시 그림 -> 15~20분 무작위 뒤 컨테이너(캡션 = 대가성 문구 + 사람 멘트 2~3줄) -> 발행 -> 관리봇 1번, 실패면 다시 X
#       정기 게시 스위치 IG_HUMAN = IG_AUTO(10/23 진우 다시 켬)
assert ig9h is True and iga0 is True and H.REEL_PUBLIC is False and H.IG_JITTER == (900, 1200) and "ig_publish, ig_stage, ig_test, toss_stock" in inspect.getsource(H.main)
s33 = {}
for _ in range(300):  # 변주: 직전 회차와 1~2개(표지 문구·배치·색) 다름, 지난주 막힌 기본 모양 X
    pv33 = dict(s33.get("igvar") or {"pal": 0, "head": 0, "band": 0}); v33 = H.ig_variant(s33)
    assert 1 <= sum(v33[k] != pv33[k] for k in ("pal", "head", "band")) <= 2 and v33 != {"pal": 0, "head": 0, "band": 0}, (pv33, v33)
for _ in range(100):
    a33 = H.ig_due(s33, f"d{_}", 1000.0); assert 1900 <= a33 <= 2200 and H.ig_due(s33, f"d{_}", 9999.0) == a33  # 15~20분, 회차마다 1번 정하면 그대로
ps33 = [{"t": f"2026-10-29 1{k}:00", "text": f"{H.DISCLOSURE}\n\n🔥 [쿠팡] {n} ({p})\n\n좋음", "url": f"https://link.coupang.com/a/I{k}", "mid": 3300 + k}
        for k, (n, p) in enumerate((("휴지 30롤", "9,900원"), ("세제 3L", "12,900원"), ("물티슈 10팩", "8,900원"), ("핫팩 30개", "8,860원")))]
sv33 = (H.ai_json, H.http, H.tg, H.POSTS, H.IG_TEST, H.IG_TEST_DIR, time.time, H.time.sleep, {k: H.E.get(k) for k in ("IG_TOKEN", "IG_USER_ID")})
pr33 = []
H.ai_json = lambda prompt, props: pr33.append(prompt) or {"lines": ["휴지 떨어진 집 손 ㅋㅋ", "이거 진짜 좋아요", "링크 눌러봐", "샀는데 좋음", "99,000원이면 개이득", "오늘 밤엔 이 정도면 살 만한 듯"]}
nt33 = lambda: {"tone_ig": {"t": 1, "l": [1, 3]}}  # 직전 2개 = 해요체 -> 이번 = 반말·음슴체(2·4)
l33 = H.ig_human(nt33(), ps33); assert l33 == ["휴지 떨어진 집 손 ㅋㅋ", "오늘 밤엔 이 정도면 살 만한 듯"] and "휴지 30롤 (9,900원)" in pr33[0], (l33, pr33)  # ~요·클릭 유도·써 본 척·없는 금액 X
H.ai_json = lambda prompt, props: {"lines": ["휴지 쟁여둘 타이밍 🔥", "세제도 같이 보면 좋음 🧺", "물티슈도 체크 ✨"]}; assert H.ig_human(nt33(), ps33) == ["휴지 쟁여둘 타이밍", "세제도 같이 보면 좋음", "물티슈도 체크"]  # 이모지 3개↑ = 다 뺌(0~2)
H.ai_json = lambda prompt, props: pr33.append(prompt) or {"lines": ["이거 진짜 좋아요", "오늘 밤엔 이 정도면 살 만한 듯"]}; s33t = {"tone_ig": {"t": 1, "l": [2, 4]}}
assert H.ig_human(s33t, ps33) == ["이거 진짜 좋아요", "오늘 밤엔 이 정도면 살 만한 듯"] and s33t["ighum"]["tone"] in (1, 3) and "해요체" in pr33[-1] and "~요'로 끝나는 말 쓰지 않기" not in pr33[-1]  # 해요체 말투(1·3) = ~요 OK
def aj33(prompt, props): raise RuntimeError("x")
H.ai_json, h33 = aj33, {}
l33a, l33b = H.ig_human(h33, ps33), H.ig_human(h33, ps33)
assert len(l33a) == len(l33b) == 2 and not set(l33a) & set(l33b) and set(l33a + l33b) <= set(H.IG_HUMAN_POOL)  # Claude 실패 = 기본 멘트(매번 다른 문장)
assert all(not re.search(H.VOICE_YO, x) and not re.search(H.VOICE_BAN, x) for x in H.IG_HUMAN_POOL)
# 1건 테스트: 카드(변주) -> 15~20분 대기 -> 컨테이너·발행 -> 관리봇 1번, 인스타 외 채널 X
H.ai_json = lambda prompt, props: {"lines": ["오늘 밤엔 이 정도면 살 만한 듯", "휴지 떨어진 집 손 ㅋㅋ"]}
json.dump(ps33, open("posts33.json", "w"), ensure_ascii=False); open("igt33.txt", "w").write("2026-10-29\n")
H.POSTS, H.IG_TEST, H.IG_TEST_DIR, H.time.sleep = "posts33.json", "igt33.txt", "igt33", (lambda s: None)
H.E.update(IG_TOKEN="pt", IG_USER_ID="178")
c33, t33, cap33 = [], [], []
class E33(Exception): pass
f33 = {"post": None}
def http33(url, body=None, headers=None, method=None):
    c33.append((url, method))
    if method == "HEAD": assert url.startswith(f"{H.SITE}cards/igt33/2026-10-"); return ""
    if url.endswith("/178/media"):
        if f33["post"]: e = E33("HTTP 400"); e.body = f33["post"]; raise e
        cap33.append(body["caption"]); assert body["image_url"] == f"{H.SITE}cards/igt33/2026-10-29.jpg"; return json.dumps({"id": "c33"})
    if "status_code" in url: return json.dumps({"status_code": "FINISHED"})
    if url.endswith("/178/media_publish"): assert body == {"creation_id": "c33"}; return json.dumps({"id": "m33"})
    raise AssertionError(url)
H.http, H.tg = http33, (lambda method, **p: t33.append((method, p)) or {"message_id": 1})
s33 = {}; time.time = lambda: TK("2026-10-29 22:40"); H.ig_test(s33)
r33 = json.load(open("docs/cards/igt33/2026-10-29.json"))
assert os.path.exists("docs/cards/igt33/2026-10-29.jpg") and not os.path.exists("docs/cards/igt33/2026-10-29.png") and not c33 and not t33  # 카드만(인스타 API X)
assert TK("2026-10-29 22:40") + 900 <= r33["at"] <= TK("2026-10-29 22:40") + 1200 and r33["v"] == {k: s33["igvar"][k] for k in ("pal", "head", "band")}
th33, hd33 = H.ig_theme(r33["v"]); im33 = __import__("PIL.Image", fromlist=["Image"]).open("docs/cards/igt33/2026-10-29.jpg").convert("RGB")
assert max(abs(a - b) for a, b in zip(im33.getpixel((8, 8)), th33["accent"] if th33["band"] else th33["bg"])) < 12, (im33.getpixel((8, 8)), th33)  # 카드에 변주 색·띠
time.time = lambda: TK("2026-10-29 22:54"); H.ig_test(s33); assert not c33 and not t33  # 14분 = 아직(15~20분)
time.time = lambda: r33["at"] + 60; H.ig_test(s33)
assert [m for _, m in c33] == ["HEAD", "POST", None, "POST"] and len(t33) == 1 and t33[0][1]["chat_id"] == H.ADMIN and t33[0][1]["text"].startswith("📸 인스타 테스트 1건 게시 완료 — 변주 "), (c33, t33)
assert all(u.startswith((H.IG, H.SITE)) for u, _ in c33)  # 인스타·사이트 확인만(텔레그램 채널·Threads X)
(cp33,) = cap33; L33 = cp33.split("\n")
assert L33[0] == H.DISCLOSURE and L33[1] == "" and L33[2:4] == ["오늘 밤엔 이 정도면 살 만한 듯", "휴지 떨어진 집 손 ㅋㅋ"] and L33[4] == "" and "10월 29일 오늘의 핫딜 모음" in cp33, cp33  # 대가성 문구 첫 줄 → 사람 멘트 → 원래 캡션
assert len(re.findall(r"#", cp33)) <= 5 and not any(re.search(H.VOICE_YO, x) for x in L33[2:4])
assert json.load(open("docs/cards/igt33/2026-10-29.json"))["st"] == "done" and s33["igt_2026-10-29"]["id"] == "m33"
c33.clear(); t33.clear(); H.ig_test(s33); H.ig_test({}); assert not c33 and not t33  # 1건만(seen을 잃어도 커밋된 기록으로)
# 실패(code 4·2207051) = 관리봇 1번, 다시 시도 X · 지난 날짜 X
open("igt33.txt", "w").write("2026-10-30\n"); json.dump([dict(p, t=p["t"].replace("10-29", "10-30")) for p in ps33], open("posts33.json", "w"), ensure_ascii=False)
f33["post"] = '{"error":{"message":"spam","code":4,"error_subcode":2207051}}'
s33 = {}; time.time = lambda: TK("2026-10-30 21:10"); H.ig_test(s33); time.time = lambda: TK("2026-10-30 21:40"); H.ig_test(s33)
assert len(t33) == 1 and t33[0][1]["text"].startswith("⚠️ 인스타 테스트 실패(다시 시도 X) — 컨테이너 ") and "2207051" in t33[0][1]["text"] and json.load(open("docs/cards/igt33/2026-10-30.json"))["st"] == "fail", t33
c33.clear(); t33.clear(); time.time = lambda: TK("2026-10-30 22:40"); H.ig_test(s33); H.ig_test({}); assert not c33 and not t33  # 다시 X
time.time = lambda: TK("2026-11-02 21:40"); H.ig_test({}); assert not c33 and not t33  # 지난 날짜 = 아무것도 X
del H.E["IG_TOKEN"]; time.time = lambda: TK("2026-10-30 21:40"); open("igt33.txt", "w").write("2026-10-30\n"); shutil.rmtree("docs/cards/igt33"); H.ig_test({}); assert not os.path.exists("docs/cards/igt33")  # 토큰 없으면 X
# 10/22 정정(Cowork): #1804 발행 응답 code 4·2207051인데 실제로 게시됨(오탐) -> 발행 오류면 컨테이너 상태·최근 게시물(캡션·시각)로 확인 뒤에만 실패, 다시 시도 X
H.E["IG_TOKEN"] = "pt"; open("igt33.txt", "w").write("2026-10-31\n"); json.dump([dict(p, t=p["t"].replace("10-29", "10-31")) for p in ps33], open("posts33.json", "w"), ensure_ascii=False)
f33["post"], g33 = None, {"pub": '{"error":{"message":"Application request limit reached","code":4,"error_subcode":2207051}}', "cap": None, "st": "FINISHED"}
def http33b(url, body=None, headers=None, method=None):
    if url.endswith("/178/media_publish"):
        c33.append((url, method)); g33["st"] = "PUBLISHED" if g33["cap"] else "FINISHED"; e = E33("HTTP 403"); e.body = g33["pub"]; raise e
    if "/178/media?fields=id,caption,timestamp&limit=1" in url:
        c33.append((url, method)); return json.dumps({"data": [{"id": "M31", "caption": g33["cap"] or "다른 글", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+0000", time.gmtime(time.time()))}]})
    if "status_code" in url and "c33" in url:
        c33.append((url, method)); return json.dumps({"status_code": g33["st"]})
    return http33(url.replace("2026-10-31", "2026-10-29") if method == "HEAD" else url, body, headers, method)
H.http = http33b; c33.clear(); t33.clear(); cap33.clear(); s33 = {}
time.time = lambda: TK("2026-10-31 21:10"); H.ig_test(s33); r33b = json.load(open("docs/cards/igt33/2026-10-31.json")); g33["cap"] = "x"
time.time = lambda: r33b["at"] + 60; H.ig_test(s33)
g33["cap"] = cap33[0]; s33.pop("igt_2026-10-31"); json.dump({**r33b, "c": "c33", "ct": r33b["at"], "cap": cap33[0][:80]}, open("docs/cards/igt33/2026-10-31.json", "w")); c33.clear(); t33.clear()
H.ig_test(s33)  # 컨테이너 있음 -> 상태 FINISHED -> 발행 오류 -> 최근 게시물 캡션·시각이 같음 = 게시됨
r33c = json.load(open("docs/cards/igt33/2026-10-31.json"))
assert r33c["st"] == "done" and r33c["id"] == "M31" and "2207051" in r33c["warn"] and len(t33) == 1 and t33[0][1]["text"].startswith("📸 인스타 테스트 1건 게시 완료 — (API는 오류 응답 — 게시 확인됨) "), (r33c, t33)
assert [m for _, m in c33].count("POST") == 1  # 발행 1번만(다시 시도 X)
c33.clear(); t33.clear(); H.ig_test(s33); assert not c33 and not t33
open("igt33.txt", "w").write("2026-11-01\n"); json.dump([dict(p, t=p["t"].replace("10-29", "11-01")) for p in ps33], open("posts33.json", "w"), ensure_ascii=False)
g33["cap"], g33["st"] = None, "FINISHED"; s33 = {}; time.time = lambda: TK("2026-11-01 21:10"); H.ig_test(s33); r33d = json.load(open("docs/cards/igt33/2026-11-01.json"))
json.dump({**r33d, "c": "c33", "ct": r33d["at"], "cap": "내 캡션"}, open("docs/cards/igt33/2026-11-01.json", "w")); s33.pop("igt_2026-11-01"); c33.clear(); t33.clear()
time.time = lambda: r33d["at"] + 60; H.ig_test(s33)  # 최근 게시물 캡션이 다르고 컨테이너도 PUBLISHED 아님 = 실패(다시 X)
assert json.load(open("docs/cards/igt33/2026-11-01.json"))["st"] == "fail" and t33[0][1]["text"].startswith("⚠️ 인스타 테스트 실패(다시 시도 X) — 발행 ") and [m for _, m in c33].count("POST") == 1, t33
# 정기 발행(ig_publish, IG_AUTO 켰을 때): 2207051인데 컨테이너가 PUBLISHED = 성공 처리(24시간 쉼 X·다시 발행 X), 아니면 예전처럼 쉼 + 알림
sv33b = (H.IG_AUTO, H.IG_LIVE); H.IG_AUTO, H.IG_LIVE = True, "igl33/ig.json"; os.makedirs("igl33", exist_ok=True)
g33["cap"], g33["st"] = "x", "FINISHED"
def http33c(url, body=None, headers=None, method=None):
    return http33b(url.replace("/K1?", "/c33?"), body, headers, method)
H.http = http33c; s33 = {"igc_K1": {"t": TK("2026-11-01 21:00"), "card": "2026-11-01"}}; t33.clear(); c33.clear(); time.time = lambda: TK("2026-11-01 21:30")
H.ig_publish(s33)
assert "igc_K1" not in s33 and "ig_hold" not in s33 and s33["igpub_20261101"]["n"] == 1 and t33[0][1]["text"].startswith("📸 인스타 자동 게시 완료") and "2026-11-01" in json.load(open("igl33/ig.json")), (s33, t33)
g33["cap"], g33["st"] = None, "FINISHED"; s33 = {"igc_K1": {"t": TK("2026-11-01 21:00"), "card": "2026-11-01"}}; t33.clear()
H.ig_publish(s33); assert "2207051" in s33["igc_K1"]["fail"] and "ig_hold" not in s33 and not t33, s33  # 10/23: 안 올라간 2207051 = 쉼·예외 X, 다음 실행에 상태만(다시 발행 X)
c33.clear(); time.time = lambda: TK("2026-11-01 21:44"); H.ig_publish(s33)
assert "igc_K1" not in s33 and "ig_hold" not in s33 and [m for _, m in c33].count("POST") == 0 and len(s33["igfail"]["f"]) == 1 and not t33, (s33, c33)  # 그래도 안 올라감 = 진짜 실패 1번(그 회차만 건너뜀)
H.IG_AUTO, H.IG_LIVE = sv33b; shutil.rmtree("igl33")
# 인스타 그래프 API 호출 수(실행마다 로그 'ig api N calls'): 진짜 http()가 인스타 주소만 셈
class R33:
    headers = type("HH", (), {"get_content_charset": lambda self: "utf-8"})()
    def read(self): return b"{}"
    def __enter__(self): return self
    def __exit__(self, *a): return False
import importlib.util as iu33
sp33 = iu33.spec_from_file_location("hd33", H.__file__); hd33 = iu33.module_from_spec(sp33); sp33.loader.exec_module(hd33)  # 하네스가 바꾼 http 말고 진짜 http
uo33 = urllib.request.urlopen; urllib.request.urlopen = lambda req, timeout=30: R33()
hd33.http(hd33.IG + "/178/media?fields=id&limit=1"); hd33.http("https://api.telegram.org/botx/getMe"); hd33.http(hd33.IG + "/c1?fields=status_code")
urllib.request.urlopen = uo33; assert hd33.RUN["igc"] == 2 and 'print("ig api", RUN["igc"], "calls · 오늘", d["n"])' in inspect.getsource(H.main) and 'time.strftime("igapi_%Y%m%d"' in inspect.getsource(H.main)  # 실행당 + 하루 합계(KST, README 점검 표)
shutil.rmtree("docs/cards/igt33")
(H.ai_json, H.http, H.tg, H.POSTS, H.IG_TEST, H.IG_TEST_DIR, time.time, H.time.sleep, ie33) = sv33
for k33, v33 in ie33.items():
    H.E.pop(k33, None) if v33 is None else H.E.update({k33: v33})
for f33x in ("posts33.json", "igt33.txt"):
    os.remove(f33x)
# 9-34 (10/22 22:3x 진우 '인스타 카드 디자인 업그레이드' — 시안 A 매거진형 · B 일상 스티커형, 날마다 번갈아): 인스타 카드만(cards.ig_cover·ig_slide, 1080x1350),
#       텔레그램·Threads·사이트 카드는 그대로 · 사진 = 몰 상품 이미지만(없으면 상품 종류 글자 칸) · 표지 문구·칩 순서 회차마다 · IG_HUMAN(= IG_AUTO, 지금 꺼짐) 때 docs/cards/igv/에 한 벌
import cards as C34
from PIL import Image as I34
assert [H.ig_design(f"2026-10-{d}") for d in (22, 23, 24, 25)] == ["A", "B", "P", "A"]  # 10/23 진우 '파스텔 A 표지도 좋다' — A 남색 -> B 핑크 -> P 파스텔
assert "".join(H.ig_design("2026-10-23", k) for k in range(4)) == "BPAB"  # 10/23 진우 '칸마다 다르게': 오늘 몇 번째 칸만큼 돌림(붙은 칸끼리 같은 표지 X), 날마다 첫 칸이 밀림
assert (H.ig_kind("도브 바디워시 1000ml 3개"), H.ig_kind("카누 미니 마일드/다크 아메리카노 240T"), H.ig_kind("휴지"), H.ig_kind("1000ml")) == ("바디워시", "아메리카노", "휴지", "")
L34 = "아주 아주 긴 상품 이름 프리미엄 대용량 고농축 세탁세제 리필 3.2L 4개 + 계량컵 증정 한정 기획 세트 구성"
os.makedirs("t34", exist_ok=True); I34.new("RGB", (300, 500), (200, 210, 230)).save("t34/ph.jpg"); open("t34/bad.jpg", "w").write("x")
it34 = [{"name": L34, "short": L34, "price": "1,234,567,890원", "chip": "1L당 9,999원 · 아주 긴 칩 문구까지 붙음", "badge": "🚀 쿠팡 로켓", "ship": "내일(금) 도착", "photo": None, "e": "🧴",
         "kind": "세탁세제", "line": "세제 떨어진 집이면 이참에 쟁여도 됨, 그리고 아주 긴 멘트가 두 줄로 넘어가도 괜찮은지 보는 줄 🧺", "when": "10/22 21시"},
        {"name": "휴지 30롤", "short": "휴지", "price": "9,900원", "chip": "", "badge": "💙 토스 특가", "ship": "", "photo": "t34/ph.jpg", "e": "🧻", "kind": "휴지", "line": "", "when": ""},
        {"name": "깨진 사진", "short": "깨진 사진", "price": "", "chip": "47%↓", "badge": "", "ship": "무료배송", "photo": "t34/bad.jpg", "e": None, "kind": "", "line": "", "when": "10/22 9시"}]
# 10/22 진우 '눈에 잘 들어와야(폰 피드 1초)': 제목 2줄 · 보조 글자 40px↑(그린 글꼴 크기 전부 기록) · 글자·바탕 대비 4.5:1↑(WCAG, 큰 글자 기준 3:1보다 높게) · 1/3 크기로도 렌더
assert all(C34.contrast(a, b) >= 4.5 for a, b in C34.IG_PAIRS.values()), sorted((round(C34.contrast(a, b), 2), k) for k, (a, b) in C34.IG_PAIRS.items())[:3]
assert all(len(x.split("\n")) == 2 for xs in H.IG_TITLES.values() for x in xs) and round(C34.contrast("white", "black"), 1) == 21.0 and round(C34.contrast("#777777", "white"), 2) == 4.48
sz34, pf34 = [], C34.pf
C34.pf = lambda w, z: sz34.append(z) or pf34(w, z)
for d34 in "ABP":
    for n34 in (1, 3, 5):  # 5개 미만·1개도(타일·칩 자리만큼)
        o34 = C34.ig_cover(d34, (it34 * 2)[:n34], "10월 22일 목요일" if d34 in "AP" else "10.22 목", "오늘 밤\n장바구니에\n넣을 만한 5개" if d34 in "AP" else "퇴근길에 골라 둔\n살 만한 거 5개",
                           f"t34/{d34}{n34}.jpg", sub="최저가 아니어도 꾸준히 팔리는 것까지" * (n34 == 5))
        assert I34.open(o34).size == (1080, 1350)
    for k34, x34 in enumerate(it34, 1):  # 긴 이름·긴 가격·긴 칩·이모지 멘트·사진(있음·없음·깨짐)
        assert I34.open(C34.ig_slide(d34, x34, k34, 3, f"t34/{d34}s{k34}.jpg")).size == (1080, 1350)
C34.pf = pf34
assert min(sz34) >= 40, sorted(set(sz34))[:5]  # 보조 글자까지 40px↑
for f34 in os.listdir("t34"):  # 1/3 크기(폰 피드 썸네일 정도)
    if f34[0] in "ABP" and f34.endswith(".jpg"):
        I34.open(f"t34/{f34}").resize((360, 450), I34.LANCZOS).save(f"t34/{f34[:-4]}_small.png")
assert len([f for f in os.listdir("t34") if f.endswith("_small.png")]) == 18
im34 = I34.open("t34/P3.jpg").convert("RGB")  # P 표지 = 파스텔(540ba9f69): 둥근 모서리 밖 라벤더 안개 · 왼쪽 위 라벤더 -> 오른쪽 아래 핑크
assert [max(abs(a - b) for a, b in zip(im34.getpixel(xy), c)) < 10 for xy, c in (((6, 6), C34.LMIST), ((60, 60), C34.LAV), ((1020, 1290), C34.BLUSH))] == [True] * 3
assert all(C34.contrast(c, tuple(a + (b - a) * t / 10 for a, b in zip(C34.LAV, C34.BLUSH))) >= 4.5 for c in (C34.INKA, C34.BERRY, C34.SUBA) for t in range(11))  # 그라데이션 중간색 위에서도
px34 = I34.open("t34/A3.jpg").convert("RGB").getpixel((20, 20)); assert max(abs(a - b) for a, b in zip(px34, C34.NAVY)) < 10, px34  # A 표지 = 남색(10/22 진우 A 최종 '남색 쪽이 시인성이 더 좋다')
px34 = I34.open("t34/As3.jpg").convert("RGB").getpixel((20, 20)); assert max(abs(a - b) for a, b in zip(px34, C34.LMIST)) < 10, px34  # A 상품 장 = 파스텔(라벤더 안개)
assert C34.contrast(*C34.IG_PAIRS["A 칩 가격"]) >= 5  # 표지 칩 가격(전 4.51 제일 낮음) 5:1↑
px34 = I34.open("t34/B3.jpg").convert("RGB").getpixel((20, 20)); assert max(abs(a - b) for a, b in zip(px34, C34.PAPER)) < 10, px34  # B 표지 = 크림
px34 = I34.open("t34/As2.jpg").convert("RGB").getpixel((540, 400)); assert max(abs(a - b) for a, b in zip(px34, (200, 210, 230))) < 12, px34  # A 상품 장 = 위 사진
shutil.rmtree("t34")
# ig_items: 몰 배지(채널 머리 줄 규칙)·칩(단위가격 > 와우 할인 > N%↓)·배송·가격 시각, 사진 끄기
sv34 = (H.ai_json, H.http, H.tg, H.POSTS, H.IG_AUTO, H.IG_HUMAN, H.IG_LIVE, H.prune_slides, time.time, H.E.get("IG_TOKEN"), H.E.get("IG_USER_ID"))
H.ai_json = lambda prompt, props: {"lines": ["휴지 떨어진 집이면 지금 쟁여도 됨", "이거 진짜 좋아요", "커피 매일 마시면 개당 가격 보고 고르기"]}
P34 = [{"t": "2026-11-07 10:00", "url": "https://link.coupang.com/a/A1", "mid": 3401, "unit": "1롤당 330원", "e": "🧻", "text": f"{H.DISCLOSURE}\n\n🚀 쿠팡 로켓 🔥\n깨끗한나라 휴지 30롤\n9,900원\n로켓배송 · 내일(토) 도착"},
       {"t": "2026-11-07 11:00", "url": "https://link.coupang.com/a/A2", "mid": 3402, "text": f"{H.DISCLOSURE}\n\n🚀 쿠팡 · 와우 할인 🔥\n맥심 커피믹스 180개\n21,000원\n와우 쿠폰 10% 할인 · 로켓배송 아님"},
       {"t": "2026-11-07 12:00", "url": "https://toss.shopping/_m/A3", "mid": 3403, "text": f"{H.TOSS_NOTE}\n\n💙 토스 특가 · 하루특가 🔥\n물티슈 10팩\n8,900원 (47%↓)\n47% 할인"},
       {"t": "2026-11-07 13:00", "url": "https://naver.me/A4", "mid": 3404, "text": f"{H.NAVER_NOTE}\n\n🔥 [네이버] 생수 2L 12병 (5,720원/무료)\n\n좋음"}]
i34 = H.ig_items({"tone_ig": {"t": 1, "l": [1, 3]}}, P34, photos=False)  # 말투 = 반말·음슴체 차례(~요 줄 X)
assert [(x["badge"], x["chip"], x["ship"]) for x in i34] == [("🚀 쿠팡 로켓", "1롤당 330원", "내일(토) 도착"), ("📦 쿠팡", "와우 할인", ""), ("💙 토스 특가", "47%↓", ""), ("네이버", "", "무료배송")], i34
assert [x["line"] for x in i34] == ["휴지 떨어진 집이면 지금 쟁여도 됨", "", "커피 매일 마시면 개당 가격 보고 고르기", ""] and i34[0]["when"] == "11/7 10시" and i34[3]["kind"] == "생수" and i34[0]["photo"] is None
# IG_HUMAN(10/31 IG_AUTO 켤 때): 21시 = 새 디자인 한 벌(igv) 만든 실행 -> 회차 + 15~20분 뒤 -> igv 표지·상품 장으로 넘기기 컨테이너 + 사람 멘트 캡션
c34 = []
def http34(url, body=None, headers=None, method=None):
    c34.append((url, body, method))
    if method == "HEAD": return ""
    if url.endswith("/178/media"): return json.dumps({"id": f"K{len(c34)}"})
    if "status_code" in url: return json.dumps({"status_code": "FINISHED"})
    raise AssertionError(url)
json.dump(P34, open("posts34.json", "w"), ensure_ascii=False); os.makedirs("docs/cards", exist_ok=True); I34.new("RGB", (10, 10)).save("docs/cards/2026-11-07.jpg")
H.http, H.POSTS, H.IG_AUTO, H.IG_HUMAN, H.IG_LIVE, H.prune_slides = http34, "posts34.json", True, True, "ig34/ig.json", (lambda now: None)
H.E.update(IG_TOKEN="pt", IG_USER_ID="178")
s34 = {}; time.time = lambda: TK("2026-11-07 22:05"); H.ig_cards(s34)
assert sorted(os.listdir("docs/cards/igv/2026-11-07")) == ["01.jpg", "02.jpg", "03.jpg", "04.jpg", "cover.jpg"] and not c34  # 이번 실행 = 한 벌만(인스타 X)
cv34 = I34.open("docs/cards/igv/2026-11-07/cover.jpg").convert("RGB").getpixel((20, 20)); assert H.ig_design("2026-11-07", 3) == "B" and max(abs(a - b) for a, b in zip(cv34, C34.PAPER)) < 10  # 11/7 22시 칸 = 10/22에서 16일 + 4번째 칸(단계 0) = B
time.time = lambda: TK("2026-11-07 22:12"); H.ig_cards(s34); assert not c34  # 22:00 + 15~20분 전(하루 카드 = 인스타 22시, 10/23 진우)
time.time = lambda: TK("2026-11-07 22:25"); H.ig_cards(s34)
imgs34 = [b["image_url"] for u, b, m in c34 if m == "POST" and b.get("is_carousel_item")]
assert imgs34 == [f"{H.SITE}cards/igv/2026-11-07/{f}" for f in ("cover.jpg", "01.jpg", "02.jpg", "03.jpg", "04.jpg")], imgs34  # 사이트 하루 카드(cards/2026-11-07.jpg) X
assert not [1 for u, b, m in c34 if b and b.get("media_type") == "CAROUSEL"] and s34["igday"]["d"] == "2026-11-07" and len(s34["igday"]["ti"]) == 1  # 묶음은 다음 실행에(조각 만든 실행엔 상태 X) · 표지 제목 = 그날 기록(안 겹치게)
c34.clear(); time.time = lambda: TK("2026-11-07 22:39"); H.ig_cards(s34)
cap34 = next(b["caption"] for u, b, m in c34 if m == "POST" and b.get("media_type") == "CAROUSEL")
assert cap34.split("\n\n")[0].startswith(H.NAVER_NOTE) and cap34.split("\n\n")[1].split("\n")[0] in ("휴지 떨어진 집이면 지금 쟁여도 됨", "커피 매일 마시면 개당 가격 보고 고르기") or len(cap34.split("\n\n")[1].split("\n")) in (2, 3), cap34  # 대가성 문구 -> 사람 멘트
(H.ai_json, H.http, H.tg, H.POSTS, H.IG_AUTO, H.IG_HUMAN, H.IG_LIVE, H.prune_slides, time.time, tk34, uid34) = sv34
H.E.pop("IG_TOKEN", None) if tk34 is None else H.E.update(IG_TOKEN=tk34); H.E.pop("IG_USER_ID", None) if uid34 is None else H.E.update(IG_USER_ID=uid34)
shutil.rmtree("docs/cards/igv"); os.remove("docs/cards/2026-11-07.jpg"); os.remove("posts34.json"); shutil.rmtree("ig34", ignore_errors=True)
assert ig9h is True and iga0 is True and H.REEL_PUBLIC is False  # (기본값) 10/23 진우 '인스타 꾸준하게' — 릴스는 꺼 둠
import subprocess, sys
for tok, host in (("IGAAx", "https://graph.instagram.com/v25.0"), ("EAAx", "https://graph.facebook.com/v25.0"), ("", "https://graph.instagram.com/v25.0")):
    r = subprocess.run([sys.executable, "-c", "import hotdeal; print(hotdeal.IG)"], env={**os.environ, "IG_TOKEN": tok}, cwd=os.path.dirname(os.path.abspath(H.__file__)), capture_output=True, text=True)
    assert r.stdout.strip() == host, (tok, r.stdout, r.stderr[-300:])
# 9-35 (10/23 진우 '사이트에서 기존에 있던 제품은 판매 중이면 없애버리지 마'): 홈 몰·품목·브랜드 칸 = 커뮤니티 딜 최근 3일 그대로 + 진우 상품(own)은 날짜 상관없이
#       (같은 url 최신 글 1개) 판매 종료 표시 없으면 남음 — 종료 = 글 end(토스 own_end) · events.json end(쿠팡·네이버, 글 날짜 이후) · 토스 하루특가·선착순 날 지남 ·
#       3일 지난 진우 상품 = 'M/D 가격 · 지금 가격은 링크에서 확인' · 칸 개수 제한은 커뮤니티 딜만(진우 상품 안 밀려남)
import build_site as S35
ev35, S35.EVENTS = S35.EVENTS, "ev35.json"
json.dump([{"at": "2026-10-10 10:00", "url": "https://link.coupang.com/a/END", "end": "2026-10-12"}, {"at": "2026-10-10 10:00", "url": "https://link.coupang.com/a/RE", "end": "2026-10-12"}], open("ev35.json", "w"))
q35 = lambda t, title, url, **k: {"t": t, "text": f"🔥 {title}\n\n좋아요", "url": url, "mid": 1, **k}
P35 = [q35("2026-10-10 10:00", "[쿠팡] 크리넥스 휴지 30롤 (19,900원)", "https://link.coupang.com/a/OLD", own=1),  # 0: 같은 url 옛 글 -> X(1이 최신)
       q35("2026-10-11 10:00", "[쿠팡] 크리넥스 휴지 30롤 (18,900원)", "https://link.coupang.com/a/OLD", own=1),  # 1: 3일 지난 진우 쿠팡 -> 남음 + 'M/D 가격'
       q35("2026-10-10 11:00", "[쿠팡] 도브 바디워시 1L (9,900원)", "https://link.coupang.com/a/END", own=1),  # 2: events end(10/12 ≥ 글 날) -> X
       q35("2026-10-10 12:00", "[쿠팡] 오래된 커뮤니티 휴지 (5,000원)", "https://www.ppomppu.co.kr/x"),  # 3: 커뮤니티 3일 지남 -> X
       q35("2026-10-10 13:00", "[쿠팡] 휴지 끝난 글 (9,000원)", "https://link.coupang.com/a/GONE", own=1, end="2026-10-11"),  # 4: 글 end -> X
       {**q35("2026-10-10 14:00", "[토스] 물티슈 10팩 (8,900원)", "https://toss.shopping/_m/D1", own=1), "text": "💙 토스 특가 · 하루특가 🔥\n물티슈 10팩\n8,900원"},  # 5: 하루특가 날 지남 -> X
       q35("2026-10-10 15:00", "[토스] 폼클렌징 2개 (11,900원)", "https://toss.shopping/_m/T2", own=1),  # 6: 토스 진우 상품(종료 표시 없음) -> 남음
       q35("2026-10-10 16:00", "[쿠팡] 바디워시 다시 (8,900원)", "https://link.coupang.com/a/RE", own=1),  # 7: 옛 글(8이 최신)
       q35("2026-10-15 16:00", "[쿠팡] 바디워시 다시 (8,900원)", "https://link.coupang.com/a/RE", own=1)]  # 8: end(10/12) 뒤 다시 올린 글 -> 남음
P35 += [q35(f"2026-10-16 {h:02d}:00", f"[쿠팡] 커뮤니티 딜 {h} (1,000원)", f"https://www.ppomppu.co.kr/{h}") for h in range(25)]  # 9~33: 최근 커뮤니티 25개(칸 24개 제한)
P35 += [q35("2026-10-10 17:00", "[토스] 선크림 2개 (11,900원)", "https://toss.shopping/_m/V1", own=1),  # 34: 보통 글 -> 남음(뒤 재게시가 끝난 선착순특가)
        {**q35("2026-10-11 17:00", "[토스] 선크림 2개 (8,390원)", "https://toss.shopping/_m/V1", own=1), "text": "🔥 [토스] 선크림 2개 (8,390원)\n\n토스 선착순특가 · 오늘 자정쯤 끝날 수 있음"},  # 35: X
        q35("2026-10-10 18:00", "[토스] 볶음밥 10개 (12,900원)", "https://toss.shopping/_m/W1", own=1),  # 36: 같은 url 커뮤니티 글(37)이 더 새로 칸에 있음 -> X
        q35("2026-10-15 18:00", "[토스] 볶음밥 10개 (11,900원)", "https://toss.shopping/_m/W1")]  # 37: 커뮤니티 최근 -> 남음
d35 = ["2026-10-16", "2026-10-15", "2026-10-14"]
h35 = S35.home_pool(P35, d35)
assert set(h35) == {1, 4, 5, 6, 8, 35, 37} | set(range(9, 34)), sorted(h35)  # 10/23 진우 '진열 = 기본 유지': 0·7·34 = 같은 url 최신 글이 따로 · 2 = events end(why 없음 = gone) · 3 = 커뮤니티 3일 지남 · 36 = 같은 url 커뮤니티 글이 더 새로
#   4 = 예전 규칙의 글 end는 안 봄 · 5·35 = 토스 하루특가·선착순 날 지남 = ⏳ 특가 대기(남음) · 8 = end(10/12) 뒤 다시 올린 글 — 봇(own_end)이 아직 안 본 글 = 아이콘대로
assert h35[5] == (2, None, "10/10 가격 · 특가 기다리는 중 · 지금 가격은 링크에서 확인", [("b3", "⏳ 특가 대기")], False) and h35[1] == (0, None, "", [], False) and h35[37][0] == 0, (h35[5], h35[1])
co35 = S35.shop_section(P35, d35, "coupang")
assert "🚀 쿠팡 딜 27개" in co35 and all(f'{S35.BASE}p/{i}.html"' in co35 for i in (1, 4, 8)) and f'{S35.BASE}p/9.html"' not in co35  # 커뮤니티 24개 + 진우 3개(밀려나지 않음)
assert co35.index('p/8.html"') < co35.index('p/4.html"') < co35.index('p/1.html"') < co35.index('p/33.html"')  # 같은 🔥면 진우 상품 먼저(그다음 최신)
assert co35.count("지금 가격은 링크에서 확인") == 3 and "10/11 가격 · 지금 가격은 링크에서 확인" in co35 and "10/15 가격 · 지금 가격은 링크에서 확인" in co35  # 진우 상품(확인 기록 없음)은 날짜와 상관없이 'M/D 가격'
to35 = S35.shop_section(P35, d35, "toss"); assert f'{S35.BASE}p/6.html"' in to35 and f'{S35.BASE}p/35.html"' in to35 and to35.index('p/6.html"') < to35.index('p/35.html"')  # 🔥 먼저, ⏳ 뒤
li35 = {k: h for k, _, h in S35.cat_sections(P35, d35)}["life"]; assert re.findall(r'p/(\d+)\.html"', li35) == ["8", "4", "1", "5"], re.findall(r'p/(\d+)\.html"', li35)
# own_end(쿠팡·네이버): events 진우 항목 now·chk(Cowork 아침 확인) -> 글 st·tgt·now·chk — 목표가 = 처음 🔥로 소개한 글 가격, 🔥 = 지금가 ≤ 목표가 +5% · end + why gone/issue만 뺌 · ⏳ -> 🔥 = 🔁 다시 특가
sv35 = (H.toss, H.plain, H.POSTS, H.HAS_TOSS, time.time)
json.dump([{"url": "https://link.coupang.com/a/OLD", "now": "21,500원", "chk": "2026-10-23 08:30"}, {"url": "https://link.coupang.com/a/GONE", "end": "2026-10-20", "why": "issue"},
           {"url": "https://link.coupang.com/a/END", "end": "2026-10-12", "why": "soldout"}], open("ev35.json", "w"))
json.dump(P35, open("posts35.json", "w"), ensure_ascii=False); H.POSTS, H.HAS_TOSS, time.time = "posts35.json", False, lambda: TK("2026-10-23 09:00")
H.own_end({}); g35 = json.load(open("posts35.json"))
f35 = lambda i: {k: g35[i].get(k) for k in ("st", "tgt", "now", "chk", "rehot") if g35[i].get(k)}
assert f35(1) == f35(0) == {"st": "wait", "tgt": "19,900원", "now": "21,500원", "chk": "10/23 8시"} and f35(4) == {"st": "gone", "tgt": "9,000원"} and f35(2)["st"] == "hot", (f35(1), f35(4), f35(2))  # 21,500 > 19,900 +5%
assert f35(5) == {"st": "wait", "tgt": "8,900원"} and f35(6) == {"st": "hot", "tgt": "11,900원"} and "st" not in g35[37] and not any(k in g35[4] for k in ("end", "tst"))  # 확인 전 토스 = 아이콘대로 · 커뮤니티 X · 예전 end 지움
S35.EVENTS = "ev35.json"; h35 = S35.home_pool(g35, d35)
assert 4 not in h35 and 2 in h35 and h35[1] == (2, "21,500원", "지금 가격 (10/23 8시 확인) · 특가 때 19,900원 · 특가 기다리는 중", [("b3", "⏳ 특가 대기")], False), h35[1]
g1 = S35.grid_item(1, g35[1], old=True, sh=h35[1]); assert '<div class="pr">21,500원</div>' in g1 and "18,900" not in g1 and "가격 · 지금 가격은" not in g1 and "⏳ 특가 대기" in g1
json.dump([{"url": "https://link.coupang.com/a/OLD", "now": "20,500원", "chk": "2026-10-24 08:10"}], open("ev35.json", "w")); time.time = lambda: TK("2026-10-24 09:00")
H.own_end({}); g35 = json.load(open("posts35.json")); assert f35(1) == {"st": "hot", "tgt": "19,900원", "now": "20,500원", "chk": "10/24 8시", "rehot": "2026-10-24"}, f35(1)  # 20,500 ≤ 20,895 = 🔁 다시 특가
h35 = S35.home_pool(g35, d35); co35 = S35.shop_section(g35, d35, "coupang")
assert h35[1][0] == 0 and h35[1][4] and ("b2", "🔁 다시 특가") in h35[1][3] and co35.index('p/1.html"') < co35.index('p/8.html"'), h35[1]  # 🔥 맨 위 + 🔁 배지(3일)
H.own_end({}); assert json.load(open("posts35.json"))[1]["rehot"] == "2026-10-24"  # 그대로 🔥면 날짜 그대로
open("ev35.json", "w").write('[{"url": "https://link.coupang.com/a/END", "end": "2026-10-12"},'); assert 2 in S35.home_pool(P35, d35)  # 깨진 events.json = 표시 없음(빌드 안 멈춤)
json.dump([{"url": "https://link.coupang.com/a/END", "end": True}], open("ev35.json", "w")); assert 2 in S35.home_pool(P35, d35)
os.remove("ev35.json"); S35.EVENTS = ev35
wt35 = S35.wait_section(g35, d35); assert 'id="wait"' in wt35 and "⏳ 특가 기다리는 상품" in wt35 and f'{S35.BASE}p/5.html"' in wt35 and f'{S35.BASE}p/1.html"' not in wt35  # ⏳ 칸 = ⏳만
# own_end(토스): 진우 쉐어링크 전부 -> 단축 링크 id(1번) -> 상세 API(지금가는 seen 안에만 — posts·사이트 X): 🔥 지금가 ≤ 목표가(쿠폰가는 쿠폰만큼 더해) +5% · ⏳ 그보다 비쌈(👍 = 리뷰 1,000↑ 또는 4.7점·300↑)
#   · 일시 품절 = 품절 또는 조회 안 됨(서로 다른 날 3번 전) · gone = 조회 안 됨 서로 다른 날 연속 3번(빼는 건 이것뿐) · 확인 뒤 다시 올린 글 = 바로 다시 확인 · ⏳ -> 🔥 = seen rehot 줄(채널·Threads 🔁)
tq35 = lambda t, n, pr, **k: {"t": t, "text": f"🔥 [토스] {n} ({pr})", "url": f"https://toss.shopping/_m/{n}", "own": 1, **k}
json.dump([tq35("2026-10-10 10:00", "A", "9,000원"), tq35("2026-10-11 10:00", "B", "10,000원", end="2026-10-20"),
           {**tq35("2026-10-11 11:00", "C", "8,000원"), "text": "💙 토스 특가 · 하루특가 🔥\nC\n8,000원", "tst": "10/23 1시"}, tq35("2026-10-12 10:00", "D", "1,000원"), tq35("2026-10-12 11:00", "E", "1,000원"),
           tq35("2026-10-12 12:00", "F", "5,000원"), tq35("2026-10-12 13:00", "G", "5,000원"), {**tq35("2026-10-12 14:00", "A", "9,000원"), "own": None},
           tq35("2026-10-12 15:00", "H", "1,950원 · 5천원 쿠폰가")], open("posts35.json", "w"), ensure_ascii=False)
c35, id35 = [], {"A": 11, "B": 22, "C": 44, "D": None, "E": 33, "F": 55, "G": 66, "H": 77}
H.plain = lambda u, hops=4: c35.append(u) or (id35[u[-1]] and f"https://toss.shopping/t/{id35[u[-1]]}")
X35 = {11: {"isSoldOut": True, "displayPrice": 9000}, 22: {"displayPrice": 10000, "reviewCount": 5}, 44: {"displayPrice": 9000, "reviewCount": 2000, "reviewScore": 4.1},
       55: {"displayPrice": 7000, "reviewCount": 100, "reviewScore": 4.9}, 66: {"displayPrice": 7000, "reviewCount": 400, "reviewScore": 4.8}, 77: {"displayPrice": 6950, "reviewCount": 10}}
def tox35(path, body=None):  # 진짜 API 모양(10/23 공식 문서): 상품 그룹 id(tacaId = 주소 /t/번호) ≠ 대표 옵션 id(tacaItemId) — 여기선 옵션 id = 그룹 id × 10
    c35.append(path); q, ids = path.split("?")[1].split("=")
    g = [i // 10 if q == "tacaItemIds" else i for i in map(int, ids.split(","))]
    return {"items": [{"tacaId": i, "tacaItemId": i * 10, **X35[i]} for i in g if i in X35], "notFoundIds": [33] if q == "tacaIds" else []}
H.toss = tox35
H.HAS_TOSS, time.time = True, lambda: TK("2026-10-23 10:00")
s35 = {}; H.own_end(s35)
st35 = lambda: [(p.get("st"), p.get("chk"), p.get("stdy"), p.get("end"), p.get("tst")) for p in json.load(open("posts35.json"))]
k35 = "10/23 10시"
assert st35() == [("out", k35, None, None, None), ("hot", k35, None, None, None), ("wait", k35, 1, None, None), ("hot", None, None, None, None), ("out", k35, None, None, None),
                  ("wait", k35, None, None, None), ("wait", k35, 1, None, None), (None, None, None, None, None), ("hot", k35, None, None, None)], st35()
# A 품절 = 일시 품절 · B 10,000 = 목표가 = 🔥(예전 end 지움) · C 9,000 > 8,400(하루특가 날 지남 — 가격으로) + 리뷰 2,000 = ⏳👍(예전 tst 지움) · D 못 풂 = 아이콘대로 🔥 · E 조회 안 됨 1번 = 일시 품절
#   F 7,000 > 5,250 = ⏳ · G = ⏳👍 · H '1,950원 · 5천원 쿠폰가' -> 6,950 ≤ (1,950 + 5,000) +5% = 🔥
g35 = json.load(open("posts35.json")); assert "displayPrice" not in json.dumps(g35) and "now" not in g35[1] and "6,950" not in json.dumps(g35)  # 토스 API 가격은 posts.json에 안 남김
assert c35[-1] == "/products/detail?tacaIds=11,22,44,33,55,66,77" and len(c35) == 9, c35  # 진우 글 url 8개 풀기(하루특가 C도) + 상세 1번
X35[55]["displayPrice"] = 7000; json.dump(json.load(open("posts35.json")) + [tq35("2026-10-23 12:00", "F", "7,000원")], open("posts35.json", "w"), ensure_ascii=False)  # 진우가 F를 7,000원에 다시 올림
c35.clear(); time.time = lambda: TK("2026-10-23 12:10"); H.own_end(s35); assert c35 == ["/products/detail?tacaIds=55"] and [x[0] for x in st35()][5::4] == ["wait", "wait"], (c35, st35())  # 바로 다시 확인 · 목표가 = 처음 🔥 글(5,000원)
c35.clear(); time.time = lambda: TK("2026-10-23 21:00"); H.own_end(s35); assert not c35  # 12시간 안·새 id 없음 = 안 물음(D 못 푼 건 하루 뒤 다시)
X35[55]["displayPrice"] = 5100; time.time = lambda: TK("2026-10-24 11:00"); H.own_end(s35); assert c35 == ["https://toss.shopping/_m/D", "/products/detail?tacaIds=11,22,44,33,66,77,55"], c35  # 오래 안 본 것부터
g35 = json.load(open("posts35.json")); assert (g35[9]["st"], g35[9]["rehot"], g35[5]["rehot"]) == ("hot", "2026-10-24", "2026-10-24") and s35["rehot"]["q"] == [{"id": 550, "g": 55, "u": "https://toss.shopping/_m/F", "tgt": "5,000원", "d": "2026-10-24", "n": "F"}], s35["rehot"]  # 5,100 ≤ 5,250 = 🔁
assert st35()[4][0] == "out" and s35["tossid"]["m"]["https://toss.shopping/_m/E"][4] == ["2026-10-23", "2026-10-24"]  # 조회 안 됨 2일째 = 아직 일시 품절
time.time = lambda: TK("2026-10-25 11:00"); H.own_end(s35); assert [x[0] for x in st35()] == ["out", "hot", "wait", "hot", "gone", "hot", "wait", None, "hot", "hot"], st35()  # 3일째 = gone(품절 A는 계속 일시 품절)
# 사이트: gone만 빠지고 나머지는 진열 — 🔥(🔁 먼저) → ⏳(👍 먼저) → 일시 품절, 토스 카드엔 API 가격 X(올린 가격 + 'M/D 가격', ⏳는 가격 숨기고 '특가 때 M원')
S35.EVENTS = "ev35x.json"; g35 = json.load(open("posts35.json")); d35b = ["2026-10-25", "2026-10-24", "2026-10-23"]; h35 = S35.home_pool(g35, d35b)
assert set(h35) == {0, 1, 2, 3, 6, 8, 9}, sorted(h35)  # E = gone만 빠짐 · F는 다시 올린 글(9)로
to35 = S35.shop_section(g35, d35b, "toss"); assert [int(x) for x in re.findall(r'p/(\d+)\.html"', to35)] == [9, 8, 3, 1, 6, 2, 0], re.findall(r'p/(\d+)\.html"', to35)
ga35, gb35, gc35, gf35 = (S35.grid_item(i, g35[i], old=True, sh=h35[i]) for i in (0, 1, 2, 9))
assert "일시 품절 (10/25 확인)" in ga35 and "10/10 가격 · 다시 들어오면 링크에서 확인" in ga35  # 그 자리 그대로 + 배지
assert "10,000원" in gb35 and "10/11 가격 · 지금 가격은 링크에서 확인" in gb35 and "👍" not in gb35  # 토스 🔥 = 올린 가격 + 날짜(API 가격 X)
assert "특가 때 8,000원 · 특가 기다리는 중 · 지금 가격은 링크에서 확인" in gc35 and "👍 꾸준템" in gc35 and "⏳ 특가 대기" in gc35 and 'class="pr"' not in gc35 and "9,000" not in gc35  # ⏳ = 옛 특가 가격 X
assert "🔁 다시 특가" in gf35 and "7,000원" in gf35  # 다시 특가(3일) — 토스는 올린 가격
fi35 = S35.fire_section(g35, d35b); assert re.findall(r'p/(\d+)\.html"', fi35) == ["9", "8", "3", "1"] and "🔥 지금 특가 중 4개" in fi35, re.findall(r'p/(\d+)\.html"', fi35)  # 홈 첫 칸 = 진우 🔥 전부(🔁 먼저) · ⏳·일시 품절 X
S35.EVENTS = ev35
# 채널·Threads(10/23 진우 '꾸준하게 제품 올라오는 게 좋지'): TOSS_STEADY_HOURS 매시 글은 진우 토스 ⏳👍(own_end) 먼저 — 상세로 지금 가격·품절·꾸준템 다시, 링크 = 진우 쉐어링크, 머리 줄 👍,
#   '지금은 특가 아님 · 특가 때 M원'(정직하게), 3일 tb_ · 🔁 다시 특가(own_end ⏳ -> 🔥 줄) = 빈틈 채움엔 먼저(목표가 +5% 안일 때만, Claude 점수 없이)
sv35b, t35 = (H.tg, H.ai_pick, H.EVENTS, H.TOSS_SOLO_HOURS), []
H.tg, H.ai_pick, H.EVENTS, H.TOSS_SOLO_HOURS = (lambda m, **p: t35.append(p) or {"message_id": 990}), (lambda prompt, lines: [{"i": 0, "score": 8, "comment": "구성 그대로"}]), "ev35s.json", range(24)
json.dump([], open("ev35s.json", "w")); X35[44]["displayName"], X35[66]["displayName"] = "C 상품", "G 상품"
assert H.TOSS_STEADY_HOURS == (10, 15, 20); time.time = lambda: TK("2026-10-25 15:05"); H.toss_solo(s35)
(p35,) = t35; u35 = p35["reply_markup"]["inline_keyboard"][0][0]["url"]
assert u35 in ("https://toss.shopping/_m/C", "https://toss.shopping/_m/G") and "💙 토스 특가 · 꾸준히 팔리는 상품 👍" in p35["text"] and p35["text"].startswith(f"<i>{H.TOSS_NOTE}") and "쿠팡" not in p35["text"], p35
assert ("지금은 특가 아님 · 특가 때 8,000원" if u35.endswith("C") else "지금은 특가 아님 · 특가 때 5,000원") in p35["text"], p35["text"]
assert f"tb_{id35[u35[-1]] * 10}" in s35 and H.th_steady(H.plain_of(p35["text"].split("\n\n", 1)[1]))  # 3일 간격 · 👍 꾸준템(Threads 순서 규칙)
t35.clear(); H.toss_solo(s35); assert not t35  # 그 시각 1번
s35["rehot"] = {"t": 1, "q": [{"id": 550, "g": 55, "u": "https://toss.shopping/_m/F", "tgt": "5,000원", "d": "2026-10-25", "n": "F"}]}; X35[55].update(displayName="F 상품", displayPrice=5100)
s35["tsolo_20261025_16"], s35["ch_last"] = 1, {"t": TK("2026-10-25 15:00")}; time.time = lambda: TK("2026-10-25 16:40"); H.toss_solo(s35)  # 매시 글은 이미 = 빈틈 채움
(r35,) = t35; assert "💙 토스 특가 · 🔁 다시 특가 🔥" in r35["text"] and "🔁 특가 때(5,000원) 가격 근처로 다시 내려왔어요" in r35["text"] and r35["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://toss.shopping/_m/F", r35["text"]
assert "tb_550" in s35 and s35["rehot"]["q"] == [] and r35["text"].startswith(f"<i>{H.TOSS_NOTE}")  # 대가성 첫 줄 · 줄에서 뺌
H.tg, H.ai_pick, H.EVENTS, H.TOSS_SOLO_HOURS = sv35b; os.remove("ev35s.json")
# 상세 호출 = 실행마다 1번, 12시간 지난 id 30개까지(오래 안 본 것부터) · 단축 링크 풀기 20개까지
json.dump([{"t": "2026-10-12 10:00", "text": f"🔥 [토스] R{k} (1,000원)", "url": f"https://toss.shopping/_m/R{k:02d}", "own": 1} for k in range(32)], open("posts35.json", "w"), ensure_ascii=False)
H.plain = lambda u, hops=4: f"https://toss.shopping/t/{1000 + int(u[-2:])}"
H.toss = lambda path, body=None: c35.append(path) or {"items": [{"tacaId": i, "tacaItemId": i + 5000, "displayPrice": 1000} for i in map(int, path.split("=")[1].split(","))], "notFoundIds": []}
c35.clear(); s35r = {}
for t35 in ("10:00", "10:00", "10:15", "22:30", "22:31"):
    time.time = lambda: TK(f"2026-10-23 {t35}"); H.own_end(s35r)
q35 = [x.split("=")[1].split(",") for x in c35]
assert [len(x) for x in q35] == [20, 12, 30, 2] and q35[3] == ["1030", "1031"], q35  # 20 푼 것 -> 다음 12 -> 15분 뒤 X -> 12시간 지나 30 + 남은 2
# toss_roster(10/23 진우 '토스도 리스트 관리 잘하고 꾸준하게'): 매일 아침 7~8시 1번 toss_list.json — 진우 토스 상품 전부(상태·목표가·확인 시각·👍·마지막 채널 게시일), 저장소가 공개라 토스 API 가격·리뷰 X
json.dump([tq35("2026-10-22 10:00", "A", "9,000원", st="hot", tgt="9,000원", chk="10/23 6시"), tq35("2026-10-21 10:00", "B", "5,000원", st="wait", tgt="5,000원", stdy=1, chk="10/23 6시"),
           tq35("2026-10-20 10:00", "C", "3,000원", st="hot", tgt="3,000원", rehot="2026-10-22"), tq35("2026-10-19 10:00", "E", "1,000원", st="gone"),
           {**tq35("2026-10-22 11:00", "Z", "1,000원"), "own": None}], open("posts35.json", "w"), ensure_ascii=False)
sv35t, H.TOSS_LIST = H.TOSS_LIST, "tl35.json"; time.time = lambda: TK("2026-10-23 07:40")
s35t = {"tossid": {"t": 1, "m": {"https://toss.shopping/_m/B": [22, 1, 1, "ok", [], 5500, False, 220]}}, "tb_220": {"t": TK("2026-10-22 15:00"), "n": "B"}, "tb_99": {"t": TK("2026-10-22 18:00"), "n": "Q"}}
H.toss_roster(s35t); tl35 = json.load(open("tl35.json"))
assert tl35["n"] == {"hot": 2, "wait": 1, "gone": 1} and tl35["rehot"] == ["C"] and tl35["gone"] == ["E"] and tl35["new"] == {"2026-10-22": 3}, tl35  # 어제 = 토스 API 글 2(tb_) + 진우 토스 글 1
assert [x["n"] for x in tl35["items"]] == ["A", "C", "B", "E"] and tl35["items"][2] == {"n": "B", "st": "wait", "tgt": "5,000원", "chk": "10/23 6시", "stdy": True, "last": "2026-10-22", "url": "https://toss.shopping/_m/B"}
assert "5,500" not in json.dumps(tl35) and "5500" not in json.dumps(tl35)  # 토스 API 가격 X
os.remove("tl35.json"); H.toss_roster(s35t); assert not os.path.exists("tl35.json")  # 하루 1번
time.time = lambda: TK("2026-10-23 09:00"); H.toss_roster({}); assert not os.path.exists("tl35.json"); H.TOSS_LIST = sv35t  # 7~8시만
# 하루특가 글 날 지남 + 밤 12시 전 확인뿐 = 상세 못 받아도 ⏳(stl) — 다음 확인에 🔥여도 🔁 X · 쿠팡 events why out = 일시 품절 · 다시 올린 글보다 옛 events now = 안 씀
S35.EVENTS = "ev35.json"; json.dump([{"url": "https://link.coupang.com/a/OUT", "end": "2026-10-25", "why": "out"}, {"url": "https://link.coupang.com/a/NEW", "now": "9,000원", "chk": "2026-10-24 08:00"}], open("ev35.json", "w"))
json.dump([{**tq35("2026-10-24 10:00", "S01", "8,000원"), "text": "🔥 [토스] S (8,000원)\n\n토스 하루특가"}, {"t": "2026-10-24 11:00", "text": "🔥 [쿠팡] 휴지 (9,000원)", "url": "https://link.coupang.com/a/OUT", "own": 1},
           {"t": "2026-10-24 12:00", "text": "🔥 [쿠팡] 물티슈 (5,000원)", "url": "https://link.coupang.com/a/NEW", "own": 1}], open("posts35.json", "w"), ensure_ascii=False)
s35s = {"tossid": {"t": 1, "m": {"https://toss.shopping/_m/S01": [1001, 1, TK("2026-10-24 20:00"), "ok", [], 8000, False, 10010]}}}
H.toss, time.time = (lambda path, body=None: 1 / 0), lambda: TK("2026-10-25 09:00"); H.own_end(s35s)
g35 = json.load(open("posts35.json")); assert (g35[0]["st"], g35[0].get("stl"), g35[1]["st"], g35[1]["chk"], g35[2]["st"], "now" in g35[2]) == ("wait", 1, "out", "10/25", "hot", False), g35
H.toss = lambda path, body=None: {"items": [{"tacaId": 1001, "tacaItemId": 10010, "displayPrice": 1000}], "notFoundIds": []}; H.own_end(s35s)
g35 = json.load(open("posts35.json")); assert g35[0]["st"] == "hot" and not any(k in g35[0] for k in ("rehot", "stl")) and not s35s["rehot"]["q"], g35[0]
os.remove("ev35.json"); S35.EVENTS = ev35
H.toss, H.plain, H.POSTS, H.HAS_TOSS, time.time = sv35; os.remove("posts35.json")
# 품목 12칸(10/23 진우 '사이트에도 제품 카테고리 구분' 7칸 -> 10/24 '주방·세탁·여성용품·과자·계절음식 세분'): 제목 정규식(CAT_ORDER: 겨울 난방 > 여성용품 > 화장품 > 주방 > 세탁 > 생필품 > 과자 > 제철 > 식품 > 생활 > 패션 > 가전) -> 안 맞으면 cat_fill이 Claude 한 단어로 글 cat(한 번만, etc = 칸 없음)
ct35 = lambda t, **k: {"t": "2026-10-12 10:00", "text": f"🔥 [쿠팡] {t} (1,000원)", "url": "https://link.coupang.com/a/" + t, "own": 1, **k}
assert [S35.cat_of(ct35(t)) for t in ("하루온 핫팩 30개", "메르헨트 폼클렌징 2개", "깨끗한나라 휴지 30롤", "햇반 24개", "홈키파 에어졸", "양말 10켤레", "보조배터리 10000", "애터미 비비크림")] == \
    ["heat", "beauty", "life", "food", "home", "fashion", "digital", ""]
assert [S35.cat_of(ct35(t)) for t in ("킨칸 모기 패치", "옥시크린 워싱소다", "햄스터 베딩", "폴햄 맨투맨", "설향 딸기 1kg", "콜라겐 젤리", "에센스웨어 브라", "헤어 에센스 2개", "립 마스크")] == \
    ["home", "laundry", "", "fashion", "season", "snack", "fashion", "beauty", "beauty"]  # 리뷰에서 잘못 들어가던 이름들(모기 = 생활 먼저, 워싱소다·햄스터 = 식품 X)
assert [S35.cat_of(ct35(t)) for t in ("코멧 위생백 200매", "주방세제 퐁퐁 1L", "다우니 섬유유연제 2L", "LG 세탁기 21kg", "쏘피 생리대 중형 36개", "롬앤 아이라이너", "프라엘 멜라빔 디바이스", "가그린 구강청결제 1.2L",
                                     "포카칩 66g 6개", "파이토메이드 두유 24개", "오뚜기 스낵면 10개", "제주 감귤 5kg", "생굴 1kg", "굴소스 500g", "크리스찬딘 어반시크 향수", "뽀로로 딸기맛 음료", "와이파이 공유기")] == \
    ["kitchen", "kitchen", "laundry", "", "women", "", "", "", "snack", "food", "", "season", "season", "food", "beauty", "food", ""]  # 10/24 세분 칸 + 실제 진열 제목에서 잘못 들어가던 것(프라엘 = 라엘 X, 아이라이너·구강청결제 = 생필품·여성용품 X, 어반시크 = 반시 X, 딸기맛·두유·스낵면 = 과자·제철 X — 칸 없음은 cat_fill이 Claude로)
assert [k for k, _, _ in S35.SHELF_CATS] == ["life", "kitchen", "laundry", "women", "beauty", "food", "snack", "season", "home", "fashion", "digital", "heat"] and set(S35.CAT_ORDER) == {k for k, _, _ in S35.SHELF_CATS} and set(H.TH_TOPICS) == set(S35.CAT_ORDER)  # 칸 = 정렬 순서 = Threads 주제 빠짐없이
assert all(f"{k} = " in H.CAT_PROMPT for k in S35.CAT_ORDER)  # Claude 품목 칸 설명도 12칸 다
assert S35.cat_of(ct35("애터미 비비크림", cat="beauty")) == "beauty" and S35.cat_of(ct35("사다리", cat="etc")) == "" and S35.cat_of(ct35("햇반", cat="beauty")) == "food"  # 정규식 먼저
sv35c, a35 = (H.ai_json, H.POSTS, H.E.get("ANTHROPIC_API_KEY")), []
json.dump([ct35("애터미 비비크림"), ct35("국내산 표고버섯 1kg"), ct35("햇반 24개"), ct35("사다리", cat="etc"), {**ct35("옛 커뮤니티 이름없음"), "own": None}], open("posts35.json", "w"), ensure_ascii=False)
H.POSTS, H.E["ANTHROPIC_API_KEY"] = "posts35.json", "k"
H.ai_json = lambda prompt, props: a35.append(prompt) or {"cats": ["beauty"]}  # 개수 다름 = 안 씀(다음 실행에 다시)
H.cat_fill({}); assert all("cat" not in p for p in json.load(open("posts35.json"))[:3]) and "1. 애터미 비비크림\n2. 국내산 표고버섯 1kg" in a35[0] and "햇반" not in a35[0] and "사다리" not in a35[0] and "이름없음" not in a35[0]
H.ai_json = lambda prompt, props: {"cats": ["beauty", "food"]}; H.cat_fill({}); assert [p.get("cat") for p in json.load(open("posts35.json"))] == ["beauty", "food", None, "etc", None]
a35.clear(); H.ai_json = lambda prompt, props: a35.append(prompt); H.cat_fill({}); assert not a35  # 다 채웠으면 안 부름
H.ai_json, H.POSTS = sv35c[:2]; H.E.pop("ANTHROPIC_API_KEY") if sv35c[2] is None else H.E.update(ANTHROPIC_API_KEY=sv35c[2]); os.remove("posts35.json")
cp35 = S35.cats_pane([("food", "🍚 식품·음료", '<section id="food"><article class="g"></article><article class="g"></article></section>'), ("life", "🧻 생필품", "")])
assert 'id="cats"' in cp35 and '<a href="#food">🍚 식품·음료 2</a>' in cp35 and "#life" not in cp35 and '<div class="cats"><section id="food">' in cp35  # 빈 칸은 바로가기·칸 X, 칸들은 감싼 div 안(바로가기 = 그 칸으로 스크롤)
# 9-36 (10/23 리뷰 고침 + 진우 '인스타 다시 켬'): own_end 확인 전 하루특가 날 지남 = ⏳ + stl(첫 확인에 🔥여도 🔁 X) · stale = 글 날짜 밤 12시 기준(매일 밤 다시 ⏳·강제 재확인 X)
sv36 = (H.toss, H.plain, H.POSTS, H.HAS_TOSS, time.time, H.tg, H.ai_json)
json.dump([{"t": "2026-10-20 10:00", "text": "🔥 [토스] D (8,000원)\n\n토스 하루특가", "url": "https://toss.shopping/_m/D36", "own": 1}], open("posts36.json", "w"), ensure_ascii=False)
H.POSTS, H.HAS_TOSS, time.time = "posts36.json", False, lambda: TK("2026-10-22 10:00"); s36 = {}; H.own_end(s36)
g36 = json.load(open("posts36.json"))[0]; assert (g36["st"], g36.get("stl")) == ("wait", 1), g36
c36 = []; H.HAS_TOSS, H.plain = True, lambda u, hops=4: "https://toss.shopping/t/3601"
H.toss = lambda path, body=None: c36.append(path) or {"items": [{"tacaId": 3601, "tacaItemId": 36010, "displayPrice": 8000}], "notFoundIds": []}
time.time = lambda: TK("2026-10-22 13:00"); H.own_end(s36); g36 = json.load(open("posts36.json"))[0]
assert g36["st"] == "hot" and "rehot" not in g36 and not s36["rehot"]["q"] and len(c36) == 1, (g36, s36.get("rehot"))  # 날짜 규칙 ⏳ -> 첫 확인 🔥 = 🔁 X
c36.clear(); time.time = lambda: TK("2026-10-23 00:07"); H.own_end(s36); assert not c36 and json.load(open("posts36.json"))[0]["st"] == "hot", c36  # 10/22 확인 = 글 날(10/20) 밤 12시 뒤 -> 안 물음·🔥 그대로
# 10/23 토스 id 바로잡기(공식 문서: 주소 /t/번호 = 상품 그룹 id tacaId ≠ 옵션 id tacaItemId): 상세는 tacaIds로 · 예전(tacaItemIds로 잘못 물은) 7칸 기록은 안 믿고 바로 다시 확인
#   · 그 첫 확인에 🔥여도 🔁 X · 조회 안 됨 날짜도 처음부터 · 옵션 id(v[7]) = 꾸준템·🔁·품절 지켜보기·같은 상품 거르기
json.dump([{"t": "2026-10-20 10:00", "text": "🔥 [토스] M (8,000원)", "url": "https://toss.shopping/_m/M36", "own": 1, "st": "wait"}], open("posts36.json", "w"), ensure_ascii=False)
s36m = {"tossid": {"t": 1, "m": {"https://toss.shopping/_m/M36": [3602, 1, TK("2026-10-23 03:00"), "out", ["2026-10-22", "2026-10-23"], None, False]}}}
c36.clear(); H.toss = lambda path, body=None: c36.append(path) or {"items": [{"tacaId": 3602, "tacaItemId": 36020, "displayPrice": 8000}], "notFoundIds": []}
time.time = lambda: TK("2026-10-23 04:00"); H.own_end(s36m); g36 = json.load(open("posts36.json"))[0]; v36 = s36m["tossid"]["m"]["https://toss.shopping/_m/M36"]
assert c36 == ["/products/detail?tacaIds=3602"] and g36["st"] == "hot" and "rehot" not in g36 and not s36m["rehot"]["q"] and v36[7] == 36020 and v36[4] == [], (c36, g36, v36)
H.HAS_TOSS = False; json.dump([dict(g36, st="out")], open("posts36.json", "w"), ensure_ascii=False); s36m["tossid"]["m"]["https://toss.shopping/_m/M36"] = v36[:7]
H.own_end(s36m); assert json.load(open("posts36.json"))[0]["st"] == "hot"  # 7칸 기록 = 아이콘대로(잘못된 '일시 품절' X)
assert "ti[w[\"url\"]][7]" in inspect.getsource(H.toss_soldout) and "ti[u][7]: (u," in inspect.getsource(H.toss_solo) and '("g", x.get("tacaId")) not in booked_id' in inspect.getsource(H.toss_deals)
H.toss, H.plain, H.POSTS, H.HAS_TOSS, time.time = sv36[:5]; os.remove("posts36.json")
assert "toss_steady(x) and not near(x)" in inspect.getsource(H.toss_solo)  # 다시 특가 가격이면 꾸준템 글 X(own_end 🔁로)
assert re.search(r"record\(re\.sub\(r\" · ⭐", inspect.getsource(H.toss_site)) and "toss_site(" in inspect.getsource(H.toss_solo)  # TOSS_SITE 켜도 리뷰 수·평점은 posts.json X
# 말투 기록 = 게시한 글만(채널 tone_ask는 안 씀 -> tone_keep) · 보관했다 올린 딜 = 코멘트 쓴 회차 말투 · admin_deal = seen 기록 · metrics 채널 줄 tone · 인스타 한 게시물 = 말투 하나
s36t = {}; t36 = H.tone_ask(s36t, "ch")[0]; assert "tone_ch" not in s36t; H.tone_keep(s36t, "ch", t36); H.tone_keep(s36t, "ch", 0); assert s36t["tone_ch"]["l"] == [t36]
assert "이모지 최대 1개" in H.tone_ask({}, "ch")[1] and "이모지 0~2개" not in H.tone_ask({}, "ch")[1]  # 채널 프롬프트 이모지 규칙 하나(DEAL_PROMPT와 같게)
assert '"tone": tone}} for p in good' in inspect.getsource(H.main) and 'tone_keep(seen, "ch", p.get("tone"))' in inspect.getsource(H.main) and 'admin_deal(lines, link, m["message_id"], seen)' in inspect.getsource(H.publish_approved)
assert '**({"tone": p["tone"]} if p and p.get("tone") else {})' in inspect.getsource(H.metrics_rows)
s36i = {}; H.ai_json = lambda prompt, props: {"lines": []}; H.ig_lines(s36i, []); n36 = s36i["ighum"]["next"]; H.ig_human(s36i, [])
assert s36i["ighum"]["tone"] == n36 and "next" not in s36i["ighum"], s36i  # 상품 장 멘트·캡션 같은 말투(다음 게시물은 다시 뽑음)
# 인스타 하루 4번부터(10/23 진우 '너무 자주 말고' + 단계적 늘리기): 단계 0 = 11·15·19 + 22시, 1 = +13시, 2 = +17시, 하루 상한 = 횟수 + 1 · 진짜 실패 = 그 회차만 건너뜀 · 하루 2번 = 24시간 쉼 + 알림
assert [H.ig_hours({"igstage": {"s": k}} if k else {}) for k in range(3)] == [(11, 15, 19, 22), (11, 13, 15, 19, 22), (11, 13, 15, 17, 19, 22)] and [H.ig_day_max({"igstage": {"s": k}}) for k in range(3)] == [5, 6, 7]
assert set(S.SLOT_NAMES) >= {f"{h:02d}" for h in H.IG_SLOTS} and not hasattr(H, "IG_SLOW") and not hasattr(H, "ig_fill") and not hasattr(H, "IG_DAY_MAX")
s36g = {}; al36 = []; H.tg = lambda m, **p: al36.append(p["text"]) or {"message_id": 1}
H.ig_fail(s36g, TK("2026-10-26 12:30"), "2026-10-26_12 컨테이너 x")
assert "ig_hold" not in s36g and not al36 and s36g["igfail"]["f"] == ["2026-10-26 2026-10-26_12 컨테이너 x"]  # 1번째 = 그 회차만 건너뜀(알림 X)
s36g.update(igc_X={"t": 1}, igk_Y={"t": 1, "kids": ["k"]}); H.ig_fail(s36g, TK("2026-10-26 21:30"), "2026-10-26 발행 y")
assert s36g["ig_hold"] == TK("2026-10-26 21:30") + 86400 and not [k for k in s36g if k.startswith(("igc_", "igk_"))] and "오늘 2번 — 24시간 쉼" in al36[0], al36
H.ig_fail(s36g, TK("2026-10-27 12:30"), "z"); assert len(s36g["igfail"]["f"]) == 1 and len(al36) == 1 and "느린 시작" not in al36[0]  # 날이 바뀌면 다시 셈
assert H.ig_err(type("E", (Exception,), {"body": '{"error":{"message":"spam","code":4,"error_subcode":2207051}}'})()) == "spam (4/2207051)"
H.tg, H.ai_json = sv36[5:]
# db939ec93 리뷰 고침: 상품명 = 개수 지킴(6개+·1+1·괄호 속 30롤)·모델명·천 단위 쉼표 그대로, 낱말 임의로 안 뺌 · ⏰ 조건 = 카드·페이·와우쿠폰도, 길면 짧게, 적립·배송 조건 X
#   · ✔ 리뷰 수 = 이 상품 것(참고 상품 X) · '1개당 N원 추가 할인'은 단가 X · 말투 줄 = 써 본 척·'지금 바로' X · 올리브영 = 큐레이터 정책(맞는 줄 없으면 말투 줄 없이) · 말투 기록 = 쓴 줄만
assert [H.th_name(n) for n in ("센소다인 민감성 치약 100g 6개+미니치약 증정", "[1+1] 메디힐 마스크 100매", "로얄라이프 3겹(30m 30롤) 2팩", "뉴클 보조배터리 20,000mAh", "싸이닉 썬크림 EX 50ml 1+1+1", "삼성 오디세이 IPX500A 모니터")] == \
    ["센소다인 민감성 치약 100g 6개+미니치약", "1+1 메디힐 마스크 100매", "로얄라이프 3겹 30m × 30롤 2팩", "뉴클 보조배터리 20,000mAh", "싸이닉 썬크림 EX 50ml 1+1+1", "삼성 오디세이 IPX500A 모니터"]
sv36v = (H.ai_voice, H.random, H.TOSS_NO_CMP); q36 = []; H.ai_voice, H.TOSS_NO_CMP = (lambda p: {"line": q36.pop(0) if q36 else ""}), True
H.random = type("R", (), {"choice": staticmethod(lambda xs: 4 if 4 in xs else xs[0])})
def tv36(t, link="https://link.coupang.com/a/c", lines=("주머니에 넣어 두기 좋음",)):
    q36[:] = list(lines); return [l for l in H.th_voice({}, t, link).split("\n") if l.startswith(("⏰", "✔"))]
C36 = CAMIL24.split("\n\n👉")[0]
assert tv36(C36.replace("100원 쿠폰 적용가", "2,000원 쿠폰 적용가"))[-1] == "⏰ 10/22 19시 쿠폰가 · 결제 전 확인"  # 길면 짧은 이름(조건은 남김)
assert tv36(C36.replace("100원 쿠폰 적용가(쿠폰 없으면 8,730원)", "삼성카드 할인 적용가"))[-1] == "⏰ 10/22 19시 카드할인가 · 결제 전 확인"
assert tv36(C36.replace("100원 쿠폰 적용가(쿠폰 없으면 8,730원)", "적립은 멤버십 조건 확인"))[-1] == "⏰ 10/22 19시 가격 · 결제 전 확인"  # 적립 조건 = 가격 조건 아님
assert tv36(C36.replace("100원 쿠폰 적용가(쿠폰 없으면 8,730원)", "향 옵션 선택 · 100원 쿠폰 적용가"))[-1] == "⏰ 10/22 19시 100원 쿠폰가 · 결제 전 확인"  # 옵션 조각이 앞이어도 쿠폰
assert tv36(C36.replace("쿠팡 검색 상위 핸드크림 중", "참고: 아트릭스 핸드크림 3개 리뷰 312 · 쿠팡 검색 상위 핸드크림 중"))[0] == "✔ 리뷰 5만+ · 한 달 2,000명+ 구매"  # 참고 상품 리뷰 X
assert not re.search(H.TH_UNIT, "1개당 500원 추가 할인") and re.search(H.TH_UNIT, "1개당 500원")
s36v = {}; q36[:] = ["나도 하나 샀음", "지금 바로 담아 둘 만함"]; assert H.th_voice(s36v, C36, "https://link.coupang.com/a/c").split("\n\n")[3] == H.TH_TONE_POOL[4][0] and s36v["tone_th"]["l"] == [4]  # 써 본 척·재촉 X -> 기본 한 줄(쓴 말투 기록)
H.random = type("R", (), {"choice": staticmethod(lambda xs: 1 if 1 in xs else xs[0])}); s36v = {}; q36[:] = ["추천해요", "강추해요"]
o36 = H.th_voice(s36v, f"{H.OY_NOTE}\n\n🔥 [올리브영] 토리든 세럼 50ml (19,900원)\n\n50ml 2개", "https://oy.run/x")
assert o36.split("\n\n")[2].startswith("⏰") and "tone_th" not in s36v and "s" not in s36v["thvoice"], (o36, s36v)  # 올리브영 + 맞는 기본 줄 없음 = 말투 줄 없이(기록 X)
H.ai_voice, H.random, H.TOSS_NO_CMP = sv36v
assert 'if k not in seen:' in inspect.getsource(H.ig_publish) and 'if k not in seen:' in inspect.getsource(H.ig_carousel) and '"t": now, "card": stem}  # 발행은 다음 실행' in inspect.getsource(H.ig_carousel)
# 9-37) 인스타 하루 4번(10/23 진우 정정): 칸 = 오늘 앞 칸 ~ 그 시각(11 = 0~11, 15 = 11~15, 19 = 15~19), 다른 칸 카드에 든 딜 X, 19시 = 진우 쿠팡 🔥·👍 먼저,
#       3개 밑 = 건너뜀(억지로 안 채움) · 첫날 10/23은 15시부터 · 그날 표지 제목 안 겹침(밤·퇴근 말은 18시부터)
D37 = "2026-11-20"
P37 = [{"t": "2026-11-19 23:30", "text": "🔥 [쿠팡] 어제 밤 딜 (1,000원)", "url": "https://link.coupang.com/a/1", "s": 5},
       {"t": f"{D37} 07:00", "text": "🔥 [쿠팡] 아침 딜 (1,000원)", "url": "https://link.coupang.com/a/3", "s": 6},
       {"t": f"{D37} 10:30", "text": "🔥 [쿠팡] 오전 딜 (1,000원)", "url": "https://link.coupang.com/a/4", "s": 4},
       {"t": f"{D37} 11:00", "text": "🔥 [옥션] 11시 딜 (1,000원)", "url": "https://www.auction.co.kr/a", "s": 5},
       {"t": f"{D37} 16:00", "text": "🔥 [옥션] 오후 딜 (1,000원)", "url": "https://www.auction.co.kr/b", "s": 9},
       {"t": f"{D37} 17:00", "text": f"{H.DISCLOSURE}\n\n🚀 쿠팡 로켓 🔥\n진우 상품\n9,900원", "url": "https://link.coupang.com/a/o1", "own": 1, "s": 1},
       {"t": f"{D37} 18:00", "text": f"{H.DISCLOSURE}\n\n🚀 쿠팡 로켓 🛒\n진우 약한 상품\n9,900원", "url": "https://link.coupang.com/a/o2", "own": 1, "s": 1},
       {"t": f"{D37} 18:30", "text": "🔥 [옥션] 저녁 딜 (1,000원)", "url": "https://www.auction.co.kr/c", "s": 7}]
for f in [f for f in os.listdir("docs/cards") if f.startswith(D37)]: os.remove(f"docs/cards/{f}")
assert [[i for i, _ in H.slot_deals(P37, D37, h)] for h in (11, 15, 19)] == [[1, 2], [3], [5, 4, 7, 6]]  # 어제 딜 X · 19시 = 진우 쿠팡 🔥 먼저(🛒는 그대로 순서)
assert [i for i, _ in H.slot_deals(P37, D37, 15, H.IG_STAGES[1])] == [] and [i for i, _ in H.slot_deals(P37, D37, 13, H.IG_STAGES[1])] == [3]  # 5번 단계: 13시 = 11~13시, 15시 = 13~15시
json.dump([1], open(f"docs/cards/{D37}_11.json", "w")); assert [i for i, _ in H.slot_deals(P37, D37, 11)] == [2] and H.ig_used(D37) == {1}  # 다른 칸 카드에 든 딜 X
sv37 = (H.POSTS, H.IG_LIVE, H.IG_CAROUSEL, H.IG_AUTO, H.prune_slides, time.time, H.E.get("IG_TOKEN"), H.E.get("IG_USER_ID"))
json.dump(P37, open("posts37.json", "w"), ensure_ascii=False)
H.POSTS, H.IG_LIVE, H.IG_CAROUSEL, H.IG_AUTO, H.prune_slides = "posts37.json", "ig37/ig.json", False, True, (lambda now: None)
H.E.update(IG_TOKEN="pt", IG_USER_ID="178")
s37 = {}; time.time = lambda: TK(f"{D37} 15:05"); H.ig_cards(s37); assert s37 == {f"igs_{D37}_15": {"t": TK(f"{D37} 15:05"), "skip": 1}} and not os.path.exists(f"docs/cards/{D37}_15.jpg")  # 딜 1개 = 건너뜀(채움 X)
time.time = lambda: TK(f"{D37} 19:05"); H.ig_cards(s37); assert json.load(open(f"docs/cards/{D37}_19.json")) == [5, 4, 7, 6] and f"igs_{D37}_19" not in s37
s37 = {}; time.time = lambda: TK("2026-10-23 11:30"); H.ig_cards(s37); assert not s37  # 첫날 10/23 = 15시부터(11시 칸 X)
time.time = lambda: TK("2026-10-23 15:05"); H.ig_cards(s37); assert s37 == {"igs_2026-10-23_15": {"t": TK("2026-10-23 15:05"), "skip": 0}}
assert "\n\n11월 20일 저녁 7시 핫딜\n\n1. " in H.ig_caption(s37, f"{D37}_19") and "맨 위 '11월 20일 저녁 7시 카드 딜'" in H.card_caption(f"{D37}_19")[1]
ti37, rc37 = [], (H.ig_items, C34.ig_cover, C34.ig_slide)
H.ig_items, C34.ig_cover, C34.ig_slide = (lambda seen, ps, photos=True: [{}] * len(ps)), (lambda design, chips, date_text, title, out, sub="": ti37.append((design, title))), (lambda *a: None)
s37 = {}
for h in H.ig_hours(s37): H.ig_set(s37, D37, P37[:3], "x37", h=h)
assert len({t for _, t in ti37}) == 4 and not [t for (_, t), h in zip(ti37, H.ig_hours(s37)) if h < 18 and re.search("밤|자기 전|퇴근", t)] and "".join(d for d, _ in ti37) == "PABP", ti37  # 그날 제목 안 겹침 · 표지 칸마다
H.ig_set(s37, "2026-11-21", P37[:3], "x37", h=11); assert s37["igday"]["d"] == "2026-11-21" and len(s37["igday"]["ti"]) == 1  # 날이 바뀌면 다시
assert ti37[4][0] != ti37[3][0] == "P" and ti37[4][0] == "A"  # 리뷰: 밤 22시(P) -> 다음 날 11시도 직전 표지 다음 것(5번 단계 날짜·칸 계산이면 같은 표지)
json.dump(P37, open("posts37.json", "w"), ensure_ascii=False); open(f"docs/cards/{D37}.jpg", "wb").write(b"j"); json.dump([1, 2], open(f"docs/cards/{D37}.json", "w"))
s37 = {}; time.time = lambda: TK(f"{D37} 22:05"); H.ig_cards(s37); assert s37 == {f"igs_{D37}": {"t": TK(f"{D37} 22:05"), "skip": 2}} and not os.path.exists(f"docs/cards/igv/{D37}")  # 리뷰: 하루 카드도 딜 3개 밑 = 건너뜀
json.dump([3, 4, 7], open(f"docs/cards/{D37}_13.json", "w")); open(f"docs/cards/{D37}_13.jpg", "wb").write(b"j")  # 5번 단계 13시 카드를 만든 뒤 진짜 실패로 단계 0(11·15·19)이 됨
s37 = {"igstage": {"s": 0}}; time.time = lambda: TK(f"{D37} 13:40"); n37 = len(ti37); H.ig_cards(s37); assert len(ti37) == n37 + 1 and s37["igday"]["d"] == D37, ti37  # 만든 칸 카드는 단계가 내려가도 마저(새 디자인 한 벌 만듦 -> 다음 실행에 올림)
assert [i for i, _ in H.slot_deals(P37, D37, 15, (11, 13, 15, 19))] == []  # 15시 = 13~15시(13시 카드 딜은 13시 카드로)
shutil.rmtree(f"docs/cards/igv", ignore_errors=True)
(H.ig_items, C34.ig_cover, C34.ig_slide), (H.POSTS, H.IG_LIVE, H.IG_CAROUSEL, H.IG_AUTO, H.prune_slides, time.time, tk37, uid37) = rc37, sv37
H.E.pop("IG_TOKEN", None) if tk37 is None else H.E.update(IG_TOKEN=tk37); H.E.pop("IG_USER_ID", None) if uid37 is None else H.E.update(IG_USER_ID=uid37)
for f in [f for f in os.listdir("docs/cards") if f.startswith(D37)]: os.remove(f"docs/cards/{f}")
os.remove("posts37.json"); shutil.rmtree("ig37", ignore_errors=True)
# 9-38) 인스타 단계적 늘리기(10/23 진우 확정): 10/23~25 하루 4번 -> 10/26 5번(+13시, 앞 3일 진짜 실패 0) -> 10/29 6번(+17시, + 글당 조회 평균 >= 앞 단계)
#       · 진짜 실패 = 그날 한 단계 내림(그날부터 다시 셈, 같은 날 두 번 X) · 판정은 매일 0시 1번 · 기록 = ig_stage.json(seen을 잃어도 단계 그대로) · 판정 줄 = log
sv38, al38, m38 = (H.METRICS, H.tg, time.time, H.IG_AUTO), [], {}
os.path.exists(H.IG_STAGE_FILE) and os.remove(H.IG_STAGE_FILE)  # 앞 절 ig_fail이 남긴 기록
H.METRICS, H.IG_AUTO, H.tg = "metrics38.json", True, (lambda m, **p: al38.append(p["text"]) or {"message_id": 1})
def day38(d, s38=None, t="00:05"):
    time.time = lambda: TK(f"{d} {t}"); s38 = {} if s38 is None else s38; H.ig_stage(s38); return s38
for d, v in (("2026-10-23", 100), ("2026-10-24", 80), ("2026-10-25", 120)): m38[d] = {"rows": [{"ch": "ig", "views": v}, {"ch": "th", "views": 999}, {"ch": "ig", "views": None}]}
json.dump(m38, open("metrics38.json", "w"))
s38 = day38("2026-10-23", t="12:10"); assert s38["igstage"]["s"] == 0 and H.ig_hours(s38) == (11, 15, 19, 22) and H.ig_day_max(s38) == 5
r38 = json.load(open(H.IG_STAGE_FILE)); assert r38["since"] == "2026-10-23" and r38["j"] == "2026-10-23" and r38["log"][-1].startswith("2026-10-23 단계 0(하루 4번) · 앞 3일 진짜 실패 0")
day38("2026-10-23", s38, "23:50"); assert len(json.load(open(H.IG_STAGE_FILE))["log"]) == 1  # 하루 1번
for d in ("2026-10-24", "2026-10-25"): day38(d, s38); assert s38["igstage"]["s"] == 0 and not al38  # 3일 안 됨
day38("2026-10-26", s38); assert s38["igstage"]["s"] == 1 and H.ig_hours(s38) == (11, 13, 15, 19, 22) and H.ig_day_max(s38) == 6 and "하루 5번(11·13·15·19·22시)" in al38[-1], al38  # 앞 3일 실패 0 -> 5번
assert json.load(open(H.IG_STAGE_FILE))["log"][-1] == "2026-10-26 단계 1(하루 5번 — 올림) · 앞 3일 진짜 실패 0 · 글당 조회 100.0 (앞 단계 None)"
s38 = day38("2026-10-26", {}, "09:00"); assert s38["igstage"]["s"] == 1  # seen을 잃어도 기록(ig_stage.json)대로
for d, v in (("2026-10-26", 90), ("2026-10-27", 110)): m38[d] = {"rows": [{"ch": "ig", "views": v}]}
json.dump(m38, open("metrics38.json", "w"))
for d in ("2026-10-27", "2026-10-28"): day38(d, s38)
r38 = json.load(open(H.IG_STAGE_FILE)); json.dump(r38, open("st38.json", "w"))
m38["2026-10-27"]["rows"][0]["views"] = 50; json.dump(m38, open("metrics38.json", "w")); day38("2026-10-29", s38)
assert s38["igstage"]["s"] == 1 and "글당 조회 70.0 (앞 단계 100.0)" in json.load(open(H.IG_STAGE_FILE))["log"][-1]  # 조회 평균이 떨어짐 -> 그대로 5번
shutil.copy("st38.json", H.IG_STAGE_FILE); m38["2026-10-27"]["rows"][0]["views"] = 110; json.dump(m38, open("metrics38.json", "w")); day38("2026-10-29", s38)
assert s38["igstage"]["s"] == 2 and H.ig_hours(s38) == (11, 13, 15, 17, 19, 22) and H.ig_day_max(s38) == 7 and "하루 6번" in al38[-1]  # 100.0 >= 100.0 -> 6번(+17시)
day38("2026-10-30", s38); time.time = lambda: TK("2026-10-30 13:20"); H.ig_fail(s38, TK("2026-10-30 13:20"), "x"); H.ig_fail(s38, TK("2026-10-30 15:20"), "y")
r38 = json.load(open(H.IG_STAGE_FILE)); assert s38["igstage"]["s"] == 1 and r38["since"] == "2026-10-30" and r38["fd"] == ["2026-10-30"] * 2 and "진짜 실패 -> 단계 1(하루 5번)" in r38["log"][-1]  # 그날 한 단계만 내림
del s38["ig_hold"]
for d in ("2026-10-31", "2026-11-01", "2026-11-02"): day38(d, s38); assert s38["igstage"]["s"] == 1, d  # 실패 난 날이 앞 3일 안 = 안 올림
day38("2026-11-03", s38); assert s38["igstage"]["s"] == 1 and "글당 조회 None" in json.load(open(H.IG_STAGE_FILE))["log"][-1]  # 이번 5번 기간 조회 숫자 없음 -> 안 올림
for d in ("2026-10-30", "2026-10-31"): m38[d] = {"rows": [{"ch": "ig", "views": 101}]}
json.dump(m38, open("metrics38.json", "w")); day38("2026-11-04", s38); assert s38["igstage"]["s"] == 2  # 101 >= 앞 단계(4번) 100
# 리뷰: 앞 단계(4번) 날이 14일보다 오래돼도 적어 둔 평균(b)으로 다시 6번 · 판정을 건너뛴 날(인스타 꺼짐)은 실패 0이어도 세지 않음
r38 = json.load(open(H.IG_STAGE_FILE)); assert r38["b"]["0"] == 100.0 and r38["s"] == 2
day38("2026-11-25", s38); r38 = json.load(open(H.IG_STAGE_FILE)); assert r38["since"] == "2026-11-25" and r38["s"] == 2  # 11/5~24 판정 없음 -> 다시 셈(올림 X)
time.time = lambda: TK("2026-11-25 13:00"); H.ig_fail(s38, TK("2026-11-25 13:00"), "z")
m38 = {d: {"rows": [{"ch": "ig", "views": 100}]} for d in ("2026-11-25", "2026-11-26", "2026-11-27")}; json.dump(m38, open("metrics38.json", "w"))
for d in ("2026-11-26", "2026-11-27", "2026-11-28"): day38(d, s38); assert s38["igstage"]["s"] == 1, d
day38("2026-11-29", s38); assert s38["igstage"]["s"] == 2 and "(앞 단계 100.0)" in json.load(open(H.IG_STAGE_FILE))["log"][-1]  # 4번 날(10/23~25)은 metrics에 없음 -> b로
assert "ig_publish, ig_stage" in inspect.getsource(H.main)  # 리뷰: 판정은 발행 뒤(0시 넘어 확인된 전날 22시 실패 -> 올림 알림 뒤 바로 내림 X)
H.METRICS, H.tg, time.time, H.IG_AUTO = sv38
for f in ("metrics38.json", "st38.json", H.IG_STAGE_FILE): os.remove(f)
# 9-39) Threads 주제 태그(10/23 진우 '주제 하나씩 자동으로 — 그 주제 보는 사람에게도'): topic_tag 파라미터(공식 문서 — 글당 1개, 1~50자, '.'·'&' X)
#       딜 글 = 품목 칸(식품 장보기·생필품·화장품·살림템·가전·패션·겨울준비), 묶음·리스트·운영 일지·날씨·투표·칸 없음 = 핫딜 · 같은 주제 연달아 3번 넘게 X(핫딜, 핫딜이면 특가)
assert all(1 <= len(v) <= 50 and not re.search(r"[.&]", v) for v in [*H.TH_TOPICS.values(), "핫딜", "특가", "일상"])
s39, tp39 = {}, lambda t: H.th_topic(s39, f"{H.DISCLOSURE}\n\n🚀 쿠팡 로켓 🔥\n{t}\n9,900원")
assert [tp39(n) for n in ("깨끗한나라 휴지 30롤", "세타필 로션 591ml", "햇반 210g 24개", "락앤락 밀폐용기 10개", "보조배터리 20000mAh", "등산 양말 10켤레", "핫팩 10개")] == \
       ["생필품", "화장품", "장보기", "살림템", "가전", "패션", "겨울준비"], s39
assert H.th_topic(s39) == "핫딜" and H.th_topic(s39, "🔥 [옥션] 무언가 특별한 것 (1,000원)") == "핫딜" and H.th_topic(s39, base="일상") == "일상"  # 묶음·칸 없음 = 핫딜 · #일상은 그대로
s39 = {}; assert [tp39("휴지 30롤") for _ in range(5)] == ["생필품"] * 3 + ["핫딜", "생필품"]  # 4번째 연달아 = 핫딜
s39 = {}; assert [H.th_topic(s39) for _ in range(5)] == ["핫딜"] * 3 + ["특가", "핫딜"] and len(s39["thtopic"]["l"]) == 5
s39 = {"thtopic": {"t": 1, "l": ["가전"] * 12}}; tp39("휴지"); assert len(s39["thtopic"]["l"]) == 10  # 최근 10개만
src39 = inspect.getsource
assert 'th_post(E.get("THREADS_TOKEN"), text, link, image, th_topic(seen))' in src39(H.th_bundle) and "th_topic(seen))" in src39(H.th_retry) and "th_topic(seen))" in src39(H.poll_post)
assert 'tag=th_topic(seen, base="일상")' in src39(H.daily_post) and "th_topic(seen, text, cat=cat)" in src39(H.th_deal) and "link, topic)" in src39(H.th_deal) and '"topic_tag": tag' in src39(H.th_text) and '"topic_tag": tag' in src39(H.th_poll)
assert H.th_topic({}, "🔥 [쿠팡] Apple 2026 에어팟 5 (199,000원)", cat="digital") == "가전" and H.th_topic({}, "🔥 [쿠팡] Apple 2026 에어팟 5 (199,000원)") == "핫딜"  # 리뷰: 글 cat(Claude)도 = 사이트 품목 칸
assert H.th_topic({}, f"{H.TOSS_NOTE}\n\n💙 토스 특가 🔥\n애터미 비비크림 40ml\n9,900원") == "화장품" and H.th_topic({}, "🔥 [쿠팡] 햇반 24개", cat="beauty") == "장보기"  # 칸 없음 -> 화장품 낱말 · 제목 칸이 먼저(사이트와 같게)
assert 'posts[i].get("cat"))' in src39(H.threads_deals) and "cat_fill, threads, threads_deals" in src39(H.main)  # 같은 실행에 올린 글도 cat 채운 뒤 Threads
assert "fields=id,text,timestamp,topic_tag" in src39(H.metrics_rows) and '{"topic": x["topic_tag"]}' in src39(H.metrics_rows)  # metrics th 줄 topic(주제별 조회 비교)
assert 'print("ig publish", card(v) or "릴스", pid or "(게시됨 확인)")' in inspect.getsource(H.ig_publish) and "pid = None" in inspect.getsource(H.ig_publish)  # 10/23 점검: 게시 id를 로그에(성공은 그전엔 줄 없음)
# 9-40) 웹앱(PWA, 10/23 진우 '웹앱으로 진행'): 모든 페이지 head(manifest·아이콘·theme-color·애플 웹앱·SW 등록) · manifest 필드 · sw.js(같은 출처 GET만, HTML 네트워크 먼저, 아이콘 캐시 먼저,
#       홈 내용마다 캐시 이름) · 홈 맨 위 설치 버튼(홈만) · GoatCounter 웹앱 출처 · 아이콘 크기·'A 레드' 그림(브라우저 확인은 node test_pwa.js — 설치 가능·SW·오프라인·설치 버튼·캡처)
import build_site as S40, cards as C40
d40 = tempfile.mkdtemp(); S40.build([{"t": "2026-10-23 10:00", "text": "🔥 [쿠팡] 휴지 30롤 (9,900원/무료)", "url": "https://link.coupang.com/a/x", "s": 7}], d40)
m40, sw40, ix40 = json.load(open(f"{d40}/manifest.webmanifest")), open(f"{d40}/sw.js").read(), open(f"{d40}/index.html").read()
assert (m40["name"], m40["short_name"], m40["start_url"], m40["scope"], m40["display"], m40["lang"], m40["background_color"], m40["theme_color"]) == ("핫딜픽 — 매일 살 만한 핫딜", "핫딜픽", "/?src=app", "/", "standalone", "ko", "#f4f5f7", "#f4f5f7")
assert [(i["sizes"], i["purpose"]) for i in m40["icons"]] == [("192x192", "any"), ("512x512", "any"), ("512x512", "maskable")] and [x["url"] for x in m40["shortcuts"]] == ["/#fire", "/#wait", "/#life"]
for f40 in ("index.html", "all.html", "p/0.html"):
    h40 = open(f"{d40}/{f40}").read().split("</head>")[0]
    assert all(x in h40 for x in ('rel="manifest" href="/manifest.webmanifest"', 'rel="apple-touch-icon"', 'href="/favicon.ico?v=2"', 'name="theme-color" content="#f4f5f7"', 'content="#101012" media="(prefers-color-scheme: dark)"',
                                  'apple-mobile-web-app-capable', 'apple-mobile-web-app-title" content="핫딜픽"', 'apple-mobile-web-app-status-bar-style', "serviceWorker.register('/sw.js')")), f40
assert 'id="inst"' in ix40 and ix40.index('id="inst"') < ix40.index('class="dis"') and 'id="inst"' not in open(f"{d40}/all.html").read()  # 설치 버튼 = 홈 맨 위만
assert "u.origin!==location.origin)return" in sw40 and "r.method!=='GET'" in sw40 and "fetch(r).then(function(res){if(res.ok&&r.mode==='navigate')" in sw40 and ".catch(function(){return caches.match(r)" in sw40  # 외부 몰·제휴 X · HTML 네트워크 먼저
assert re.search(r"var V='hdp-([0-9a-f]{10})'", sw40)[1] == hashlib.md5((ix40 + open(f"{d40}/manifest.webmanifest").read()).encode()).hexdigest()[:10] and "caches.delete(k)" in sw40  # 배포(홈·manifest 내용)마다 캐시 이름 -> 옛 캐시 지움
S40.build([{"t": "2026-10-23 10:00", "text": "🔥 [쿠팡] 휴지 30롤 (9,900원/무료)", "url": "https://link.coupang.com/a/x", "s": 7}], d40); assert open(f"{d40}/sw.js").read() == sw40  # 홈이 같으면 sw.js도 그대로(실행마다 커밋 X)
g40, S40.GC_CODE = S40.GC_CODE, "hdp"; assert S40.gc_tag().index(S40.GC_APP) < S40.gc_tag().index("count.js") and "'app'" in S40.GC_APP; S40.GC_CODE = g40  # count.js 전에(GoatCounter 문서)
assert S40.gc_tag() == "" if not g40 else True
ic40 = C40.app_icons(f"{d40}/icons", d40); from PIL import Image as I40
assert [I40.open(f).size for f in ic40[:6]] == [(192, 192), (512, 512), (512, 512), (180, 180), (32, 32), (16, 16)] and I40.open(f"{d40}/icons/apple-touch-icon.png").mode == "RGB"  # 애플 = 투명 X
# 'A 레드'(10/23 진우 — 원 아이콘은 런처가 확대해 '딜'이 잘림): any·maskable·애플 = 같은 꽉 찬 그라데이션 정사각(투명 X), 파비콘 = '딜'만 둥근 네모
assert open(f"{d40}/icons/icon-512.png", "rb").read() == open(f"{d40}/icons/icon-512-maskable.png", "rb").read() and all(I40.open(f).mode == "RGB" for f in ic40[:4])
near40 = lambda a, b, t=4: all(abs(x - y) <= t for x, y in zip(a, b))
for f40 in ic40[:4]:
    i40 = I40.open(f40); n40 = i40.width - 1
    assert near40(i40.getpixel((0, 0)), C40.LOGO_GRAD[0]) and near40(i40.getpixel((n40, n40)), C40.LOGO_GRAD[1]) and near40(i40.getpixel((n40, 0)), i40.getpixel((0, n40)), 6), f40  # 왼쪽 위 -> 오른쪽 아래
mk40 = I40.open(f"{d40}/icons/icon-512.png"); px40 = [(x, y) for x in range(512) for y in range(512) if min(mk40.getpixel((x, y))) > 200]  # 흰색 = '딜'·알약
bb40 = lambda ps: (min(x for x, _ in ps) / 512, min(y for _, y in ps) / 512, (max(x for x, _ in ps) + 1) / 512, (max(y for _, y in ps) + 1) / 512)
dl40, pl40 = bb40([p for p in px40 if p[1] < 0.6 * 512]), bb40([p for p in px40 if p[1] >= 0.6 * 512])
assert abs((dl40[0] + dl40[2]) / 2 - 0.5) < 0.01 and abs((dl40[1] + dl40[3]) / 2 - 0.42) < 0.01 and 0.27 < dl40[3] - dl40[1] < 0.40, dl40  # '딜' 가운데 x · 글자 상자 가운데 y 0.42
assert all(abs(a - b) < 0.006 for a, b in zip(pl40, (0.31, 0.625, 0.69, 0.765))), pl40  # 알약 0.38 × 0.14, 가운데 (0.5, 0.695)
assert all(0.2 <= v <= 0.8 for v in dl40 + pl40) and all((x - 255.5) ** 2 + (y - 255.5) ** 2 <= (0.4 * 512) ** 2 for x, y in px40)  # 가운데 60% 안 = maskable 안전 영역(지름 80%)·원·둥근 네모로 깎아도 안 잘림
pk40 = [mk40.getpixel((x, y)) for x in range(int(0.36 * 512), int(0.64 * 512)) for y in range(int(0.63 * 512), int(0.76 * 512))]
assert sum(near40(c, C40.PICK_RED, 6) for c in pk40) > 300  # 알약 안 빨간 'pick'
for f40 in (f"{d40}/icons/favicon-32.png", f"{d40}/icons/favicon-16.png"):
    i40 = I40.open(f40); n40 = i40.width
    assert i40.getpixel((0, 0))[3] == 0 and i40.getpixel((n40 // 2, n40 - 2))[3] == 255 and max(min(i40.getpixel((x, y))[:3]) for x in range(n40) for y in range(n40)) > 200, f40  # 둥근 네모(모서리 투명) + 흰 '딜'
assert "/icons/icon-192.png?v=2" in sw40 and "/favicon.ico?v=2" in sw40 and all(i["src"].endswith("?v=2") for i in m40["icons"]) and 'href="/icons/apple-touch-icon.png?v=2"' in ix40  # 새 그림 = 새 주소(폰·SW가 새로 받음)
# 바로가기 아이콘 'V1 파스텔 이모지'(10/24 진우): 🔥·⏳·🧻 각자 파일(96·192 any — 크롬은 바로가기에 any만 씀, ?v=) · 위 -> 아래 파스텔 꽉 찬 정사각 · 이모지 가운데, 긴 변 = 0.5n
assert [[(i["src"], i["sizes"], i["purpose"]) for i in x["icons"]] for x in m40["shortcuts"]] == [[(f"/icons/sc-{k}-96.png{S40.SV}", "96x96", "any"), (f"/icons/sc-{k}.png{S40.SV}", "192x192", "any")] for k in ("fire", "wait", "life")]
assert S40.SV.startswith("?v=") and [x["url"] for x in m40["shortcuts"]] == ["/#fire", "/#wait", "/#life"] and [C40.SC_ICONS[k][0] for k in ("fire", "wait", "life")] == ["🔥", "⏳", "🧻"]
sc40 = {}
for k40, (e40, t40, b40) in C40.SC_ICONS.items():
    for n40 in (192, 96):
        i40 = I40.open(f"{d40}/icons/sc-{k40}{'' if n40 == 192 else '-96'}.png"); c40 = n40 // 2
        assert i40.size == (n40, n40) and i40.mode == "RGB" and near40(i40.getpixel((0, 0)), t40, 2) and near40(i40.getpixel((n40 - 1, n40 - 1)), b40, 2) and near40(i40.getpixel((0, n40 - 1)), b40, 2), (k40, n40)  # 위 -> 아래(가로는 같은 색)
        bg40 = lambda x, y: near40(i40.getpixel((x, y)), tuple(round(a + (b - a) * y / (n40 - 1)) for a, b in zip(t40, b40)), 3)
        em40 = [(x, y) for x in range(n40) for y in range(n40) if not bg40(x, y)]
        bx40 = bb40([(x * 512 / n40, y * 512 / n40) for x, y in em40])
        assert abs(max(bx40[2] - bx40[0], bx40[3] - bx40[1]) - 0.5) < 0.03 and abs((bx40[0] + bx40[2]) / 2 - 0.5) < 0.02 and abs((bx40[1] + bx40[3]) / 2 - 0.5) < 0.02, (k40, n40, bx40)  # 긴 변 50%, 가운데
        assert all((x + 0.5 - c40) ** 2 + (y + 0.5 - c40) ** 2 <= (0.4 * n40) ** 2 for x, y in em40), (k40, n40)  # 원·둥근 네모로 깎아도 안 잘림
        sc40[k40, n40] = round(bx40[2] - bx40[0], 2)
assert len({v for (k, n), v in sc40.items() if n == 192}) == 3 and all(v < 0.45 for v in sc40.values()), sc40  # 셋 다 다른 이모지(폭 🔥 0.40·⏳ 0.34·🧻 0.38 — 못 그려 🛒(0.49)로 바뀌면 걸림)
assert set(I40.open(f"{d40}/favicon.ico").info["sizes"]) == {(16, 16), (32, 32), (48, 48)}
# 9-41) 쿠팡 파트너스 API(10/23 최종 승인 — 진우가 키를 Secrets에 넣기 전 준비): 키 없으면 아무것도 안 바뀜 ·
#       ① events·관리자 쿠팡 상품 주소 -> 딥링크(cp_links.json, events.json 그대로, 진우 단축 링크 그대로, coupa.ng도 대가성 문구) ② pid 하루 1번 검색 API -> seen cpq -> own_end
#       ③ 골드박스 🚀(isRocket만)·게시 시점 가격 · 호출 상한(실행마다 검색 1·전체 6 + 최근 1시간 검색 6·전체 25) · rCode 400(HTTP 200) = ValueError, 그 밖 = RuntimeError
#       · 검색 결과는 같은 옵션(수량·용량)만 · Cowork 쿠폰·와우 가격은 그대로 · 6시간 지난 예약은 안 바꿈(리뷰 10/23)
sv41 = (H.http, H.tg, H.ai_pick, time.time, H.HAS_CP, H.EVENTS, H.POSTS, H.draft)
H.EVENTS, H.POSTS, c41 = "events.json", "posts.json", []
EG41, P222, P333 = "https://link.coupang.com/a/egg", "https://www.coupang.com/vp/products/222?itemId=5", "https://www.coupang.com/vp/products/333"
ev41 = [{"at": "2026-10-06 09:50", "deal": True, "url": P222, "text": "🔥 <b>[쿠팡] 새 상품 (5,000원)</b>\n\n좋음", "button": "🛒 구매하러 가기"},
        {"at": "2026-10-06 09:55", "deal": True, "url": P333, "text": "🔥 <b>[쿠팡] 안 되는 상품 (1,000원)</b>", "button": "🛒 구매하러 가기"},
        {"at": "2026-10-05 10:00", "deal": True, "url": EG41, "pid": "111", "now": "8,990원", "chk": "2026-10-06 09:30", "text": "🔥 <b>[쿠팡] 곰곰 특란 30구 (7,990원/무료)</b>", "button": "x"},
        {"at": "2026-10-06 03:59", "deal": True, "url": "https://www.coupang.com/vp/products/666", "text": "🔥 <b>[쿠팡] 지난 예약 (1원)</b>", "button": "x"}]  # 6시간 지남 = 안 올라감 -> 안 바꿈
po41 = [{"t": "2026-10-05 10:00", "text": "🔥 [쿠팡] 곰곰 특란 30구 (7,990원/무료)", "url": EG41, "own": 1, "mid": 1}]
def http41(url, body=None, headers=None, method=None):
    c41.append((url, body))
    if url.endswith("/deeplink"):
        us = body["coupangUrls"]  # 묶음 변환(10/24) — 안 되는 주소가 끼면 묶음 전체 rCode 400
        return json.dumps({"rCode": "400", "rMessage": "url convert failed"} if any("/333" in u for u in us) else {"rCode": "0", "data": [{"originalUrl": u, "shortenUrl": "https://coupa.ng/b" + re.search(r"/products/(\d+)", u)[1]} for u in us]})
    if "/products/search?" in url:
        return json.dumps({"rCode": "0", "data": {"productData": [{"productId": 999, "productName": "곰곰 특란, 30구, 1개", "productPrice": 1}, {"productId": 111, "productName": "곰곰 특란, 30구, 2개", "productPrice": 14000},
                                                                 {"productId": 111, "productName": "곰곰 무항생제 신선한 특란, 30구, 1개", "productPrice": 7490}] if quote("곰곰 특란 30구") in url else []}})  # 같은 pid 2개 묶음 옵션은 X
    if "linkprice" in url:
        return json.dumps({"result": "F", "url": ""})
    raise AssertionError(url)
tg41 = lambda m, **p: sent.append((m, p)) or {"message_id": 90 + len(sent), "text": re.sub(r"<[^>]+>", "", p.get("text", "")), "entities": []}
def reset41(keys):
    json.dump(ev41, open("events.json", "w")); json.dump(po41, open("posts.json", "w")); [os.path.exists(f) and os.remove(f) for f in ("cp_links.json",)]
    H.HAS_CP, H.http, H.tg, time.time = keys, http41, tg41, lambda: 1791248400  # 10/6 10:00 KST
    H.RUN.pop("cpu", None); H.RUN.pop("cpn", None); c41.clear(); sent.clear(); return {}
# 키 없음 = 지금과 같음: API 안 부르고 seen·파일 그대로, 상품 주소 예약은 그 주소로(예전처럼), 가격은 events now
seen41 = reset41(False); raw41 = json.load(open("events.json"))
H.cp_links(seen41); H.cp_price(seen41)
assert seen41 == {} and not os.path.exists("cp_links.json") and not c41 and H.load(H.EVENTS, []) == raw41 and "cpu" not in H.RUN
assert H.affiliate("https://www.coupang.com/vp/products/222") == ("https://www.coupang.com/vp/products/222", False) and not any("coupang.com/v2" in u for u, _ in c41)
H.events(seen41); ch41 = [p for m, p in sent if m == "sendMessage" and p["chat_id"] == "@ch"]
assert [p["reply_markup"]["inline_keyboard"][0][0]["url"] for p in ch41] == [P222, P333] and not any(H.DISCLOSURE in p["text"] for p in ch41)
H.own_end(seen41); e41 = next(p for p in json.load(open("posts.json")) if p["url"] == EG41)
assert (e41["now"], e41["chk"]) == ("8,990원", "10/6 9시") and not any(k.startswith("cp") for k in seen41)
assert 'if HAS_CP:  # 쿠팡 API 최근 1시간 호출 시각' in inspect.getsource(H.main) and 'RUN["cpu"] = seen.setdefault("cpuse", {"t": 0})' in inspect.getsource(H.main)
# ① 키 있음: 상품 주소 -> 파트너스 링크(1번만, cp_links.json), 안 되는 상품 = 관리자 알림 + 그 예약은 안 올림(하루 뒤 다시), events.json은 Cowork 것 그대로
seen41 = reset41(True)
H.cp_links(seen41)
assert json.load(open("cp_links.json")) == {P222: "https://coupa.ng/b222"} and P333 in seen41["cpdl"]["x"] and [u for u, _ in c41] == [H.CP_HOST + H.CP_BASE + "/deeplink"] * 3 and [len(b["coupangUrls"]) for _, b in c41] == [2, 1, 1]
assert any(p["chat_id"] == "42" and "쿠팡 링크 변환 안 됨" in p["text"] and P333 in p["text"] for m, p in sent)
n41 = len(c41); H.cp_links(seen41); assert len(c41) == n41  # 바꾼 건 다시 안 부름 · 안 되는 건 하루 뒤
ld41 = H.load(H.EVENTS, [])
assert (ld41[0]["url"], ld41[0]["pid"], ld41[1]["url"], ld41[2]["url"]) == ("https://coupa.ng/b222", "222", P333, EG41) and json.load(open("events.json")) == raw41
assert S40.ev_info()["https://coupa.ng/b222"]["pid"] == "222" and S40.aff("https://coupa.ng/b222") and H.aff_note("https://coupa.ng/b222") == H.DISCLOSURE  # 사이트도 같은 링크·제휴
sent.clear(); H.events(seen41); ch41 = [p for m, p in sent if m == "sendMessage" and p["chat_id"] == "@ch"]
assert len(ch41) == 1 and ch41[0]["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://coupa.ng/b222" and H.DISCLOSURE in ch41[0]["text"] and "ev_2026-10-06 09:55" not in seen41
assert json.load(open("posts.json"))[-1]["url"] == "https://coupa.ng/b222"  # 사이트·Threads도 파트너스 링크
assert H.affiliate("https://www.coupang.com/vp/products/444") == ("https://coupa.ng/b444", True)  # 커뮤니티 쿠팡 딜(예전 그대로 + 응답 검사)
H.http = lambda url, *a, **k: json.dumps({"rCode": "0", "data": [{"shortenUrl": "https://evil.example/x"}]}) if "deeplink" in url else http41(url, *a, **k)
assert H.affiliate("https://www.coupang.com/vp/products/444") == ("https://www.coupang.com/vp/products/444", False); H.http = http41  # 파트너스 도메인 아니면 안 씀(대가성 문구 빠짐 방지)
# ① 관리자(진우)가 봇에 보낸 쿠팡 상품 주소도(추적값 빼고) -> 파트너스 링크 / 키 없으면 그대로
UP41 = [{"update_id": 90, "message": {"message_id": 91, "from": {"id": 42}, "text": "[쿠팡] 휴지 30롤 9,900원\nhttps://www.coupang.com/vp/products/555?itemId=1&vendorItemId=2&lptag=x"}}]
for k41 in (True, False):
    reset41(k41); H.ai_pick = lambda prompt, lines: []
    H.tg = lambda m, **p: sent.append((m, p)) or (UP41 if m == "getUpdates" and "offset" not in p else {"message_id": 95, "text": "", "entities": []})
    dr41, H.draft = [], lambda text, link, **k: dr41.append((text, link)) or {"message_id": 1}
    H.publish_approved({})
    dl41 = [b for u, b in c41 if u.endswith("/deeplink")]
    assert dl41 == ([{"coupangUrls": ["https://www.coupang.com/vp/products/555?itemId=1&vendorItemId=2"]}] if k41 else []), (k41, dl41)
    assert len(dr41) == 1 and (dr41[0][1] == "https://coupa.ng/b555") == k41 and dr41[0][0].startswith("<i>" + H.DISCLOSURE) == k41, dr41  # 키 없으면 예전처럼 상품 주소·문구 없음
# ② 가격 확인: 시작 시각 전 X · 실행마다 1개 · 글(url)마다 하루 1번(검색 결과 중 pid(productId·pageKey) 같고 같은 옵션만) · own_end = 더 새것(봇 vs Cowork chk), 쿠폰·와우는 Cowork 그대로
#   · 가장 오래전에 확인한 글 먼저 · 오류 = 오늘은 건너뜀(어제 가격 그대로) · 못 찾으면 로그에 pid·검색어·결과 위 3개(pid 있음 = 옵션 다름 / pid 없음)
seen41 = reset41(True); H.cp_links(seen41); H.events(seen41); c41.clear()
ch0, H.CP_CHK_HOUR = H.CP_CHK_HOUR, 11; H.cp_price(seen41); assert "cpq" not in seen41 and not c41; H.CP_CHK_HOUR = ch0  # 10시 < 11시
H.cp_price(seen41); assert seen41["cpq"]["m"] == {EG41: [7490, "2026-10-06 10:00"]} and len(c41) == 1  # 실행마다 검색 1번
H.RUN.pop("cpn"); o41 = io.StringIO(); import contextlib
with contextlib.redirect_stdout(o41): H.cp_price(seen41)
assert seen41["cpq"]["m"] == {EG41: [7490, "2026-10-06 10:00"], "https://coupa.ng/b222": [0, "2026-10-06 10:00"]} and [u.split("?")[0] for u, _ in c41] == [H.CP_HOST + H.CP_BASE + "/products/search"] * 2
assert "cp price 못 찾음 pid 222 · 검색어 '새 상품' · pid 없음 · 결과 0개" in o41.getvalue() and "sk" not in o41.getvalue().replace("검색", ""), o41.getvalue()  # 원인 찾기 로그(키·주소 쿼리 X)
assert any(quote("곰곰 특란 30구") in u and u.endswith("&limit=10") for u, _ in c41)
c41.clear(); H.RUN.pop("cpn"); H.cp_price(seen41); assert not c41  # 오늘은 끝
assert H.cp_same("햇반 24개", "햇반 백미밥, 210g, 24개") and H.cp_same("리큐 리필 2.1L 4개", "리큐 진한겔 리필, 2.1L, 4개") and not H.cp_same("곰곰 특란 30구", "곰곰 특란, 30구, 2개") and not H.cp_same("에어팟 5", "에어팟 5, 2개")
H.own_end(seen41); e41 = next(p for p in json.load(open("posts.json")) if p["url"] == EG41)
assert (e41["now"], e41["chk"], e41["st"]) == ("7,490원", "10/6 10시", "hot")  # 사이트 ⏳/🔥 = 같은 값
seen41["cpq"]["m"][EG41][1] = "2026-10-06 09:00"; H.own_end(seen41); e41 = next(p for p in json.load(open("posts.json")) if p["url"] == EG41)
assert (e41["now"], e41["chk"]) == ("8,990원", "10/6 9시")  # Cowork 확인(09:30)이 더 새것이면 그것
seen41["cpq"]["m"][EG41][1] = "2026-10-06 10:00"; json.dump([{**e, "now": "8,990원 와우가"} if e["url"] == EG41 else e for e in ev41], open("events.json", "w"))
H.own_end(seen41); e41 = next(p for p in json.load(open("posts.json")) if p["url"] == EG41); assert e41["now"] == "8,990원 와우가"  # 검색 가격엔 와우·쿠폰 없음 -> Cowork 값
json.dump(ev41, open("events.json", "w"))
# 호출 상한: 이번 실행(검색 1·전체 6 — 실패한 실행의 호출은 다음 실행에 안 보여도 1시간 합 ≤ 실행 수) · 최근 1시간(시계 시각 경계에서 두 배 안 되게) · rCode
def lim41(*a):
    try: H.coupang(*a)
    except H.CpLimit: return True
H.RUN["cpu"] = {}; H.RUN.pop("cpn", None); c41.clear()
H.coupang("GET", "/products/search?keyword=a&limit=10"); assert lim41("GET", "/products/search?keyword=b&limit=10")  # 실행마다 검색 1
for _ in range(5): H.coupang("POST", "/deeplink", {"coupangUrls": [P222]})
assert lim41("POST", "/deeplink", {"coupangUrls": [P222]}) and len(c41) == 6  # 실행마다 전체 6
H.RUN.pop("cpn"); H.RUN["cpu"] = {"s": [1791248400 - 100] * 6, "a": [1791248400 - 100] * 6}; assert lim41("GET", "/products/search?keyword=a&limit=10")  # 최근 1시간 검색 6
time.time = lambda: 1791248400 + 3501; H.coupang("GET", "/products/search?keyword=a&limit=10")  # 1시간 지나면 다시
H.RUN.pop("cpn"); H.RUN["cpu"] = {"a": [time.time()] * 25}; assert lim41("POST", "/deeplink", {"coupangUrls": [P222]})  # 최근 1시간 전체 25
H.RUN.pop("cpn"); H.RUN["cpu"] = {}
try: H.coupang("POST", "/deeplink", {"coupangUrls": [P333]}); raise AssertionError("rCode 400")
except ValueError: pass
for body41 in (json.dumps({"rCode": "500", "rMessage": "x"}), "<html>502</html>"):  # 그 밖 rCode·JSON 아님 = 상품 탓 X(다음 실행에)
    H.http = lambda url, *a, b=body41, **k: b
    try: H.coupang("POST", "/deeplink", {"coupangUrls": [P222]}); raise AssertionError(body41)
    except ValueError: raise AssertionError("상품 실패로 보면 안 됨 " + body41)
    except RuntimeError: pass
seen41 = reset41(True); H.http = lambda url, *a, **k: json.dumps({"rCode": "500"}); H.cp_links(seen41)
assert seen41["cpdl"]["x"] == {} and not sent and not os.path.exists("cp_links.json")  # 게이트웨이 오류 = 알림·하루 쉼 X, 다음 실행에
seen41["cpq"] = {"m": {EG41: [7490, "2026-10-05 10:00"]}}; H.cp_price(seen41)
assert seen41["cpq"]["m"] == {EG41: [7490, "2026-10-05 10:00"]} and seen41["cpq"]["e"] == {EG41: "2026-10-06"}  # 검색 오류 = 오늘은 그 글 건너뜀(어제 가격 그대로, 줄을 막지 않음)
c41.clear(); H.RUN.pop("cpn"); H.cp_price(seen41); assert not c41  # 오늘 다시 X
# 가장 오래전에 확인한 글 먼저 · 결과에 pid는 있는데 옵션이 다름 = 'pid 있음' 로그 + 위 3개 · pageKey(파트너스 링크의 상품 번호)로도 같은 상품
seen41 = reset41(True); json.dump(po41 + [{"t": "2026-10-05 11:00", "text": "🔥 [쿠팡] 새 상품 (5,000원)", "url": "https://coupa.ng/b222", "own": 1, "mid": 2}], open("posts.json", "w")); H.cp_links(seen41)
seen41["cpq"] = {"m": {EG41: [7490, "2026-10-05 10:00"], "https://coupa.ng/b222": [0, "2026-10-04 10:00"]}}; c41.clear(); H.RUN.pop("cpn")
H.http = lambda url, *a, **k: c41.append((url, None)) or json.dumps({"rCode": "0", "data": {"productData": [{"productId": 9, "productName": "다른 상품", "productPrice": 1}, {"productId": 777, "productName": "새 상품, 2개", "productPrice": 9000, "productUrl": "https://link.coupang.com/re/AFFSDP?lptag=x&pageKey=222&itemId=1"}]}})
o41 = io.StringIO()
with contextlib.redirect_stdout(o41): H.cp_price(seen41)
assert quote("새 상품") in c41[0][0] and seen41["cpq"]["m"]["https://coupa.ng/b222"][0] == 0, c41  # 10/4 확인 글이 먼저
assert "pid 222 · 검색어 '새 상품' · pid 있음 1개 = 옵션 다름(cp_same) — events에 item(옵션 itemId)을 넣으면 그 옵션으로 · 결과 2개" in o41.getvalue() and "  9 다른 상품\n" in o41.getvalue() and "  777 새 상품, 2개 ← 같은 pid · item 1" in o41.getvalue(), o41.getvalue()
H.http = lambda url, *a, **k: json.dumps({"rCode": "0", "data": {"productData": [{"productId": 777, "productName": "새 상품, 1개", "productPrice": 5100, "productUrl": "https://link.coupang.com/re/AFFSDP?pageKey=222"}]}})
seen41["cpq"]["m"]["https://coupa.ng/b222"][1] = "2026-10-04 10:00"; H.RUN.pop("cpn"); H.cp_price(seen41); assert seen41["cpq"]["m"]["https://coupa.ng/b222"][0] == 5100  # productId가 달라도 pageKey = pid면 같은 상품
# events item(옵션 itemId)이 있으면 이름 대신 그 옵션(10/23 고려은단 '180정' — 쿠팡 이름엔 옵션이 없고 같은 pid 4개 이름이 같음) · 없는 item이면 못 찾음 로그
json.dump([{**e, "item": "55"} if e["url"] == P222 else e for e in ev41], open("events.json", "w"))
GO41 = [{"productId": 222, "productName": "새 상품", "productPrice": p, "productUrl": f"https://link.coupang.com/re/AFFSDP?pageKey=222&itemId={i}"} for p, i in ((9800, 54), (5300, 55), (15000, 56))]
H.http = lambda url, *a, **k: json.dumps({"rCode": "0", "data": {"productData": GO41}})
seen41["cpq"]["m"]["https://coupa.ng/b222"][1] = "2026-10-04 10:00"; H.RUN.pop("cpn"); H.cp_price(seen41); assert seen41["cpq"]["m"]["https://coupa.ng/b222"][0] == 5300
json.dump([{**e, "item": "99"} if e["url"] == P222 else e for e in ev41], open("events.json", "w")); o41 = io.StringIO()
seen41["cpq"]["m"]["https://coupa.ng/b222"][1] = "2026-10-04 10:00"; H.RUN.pop("cpn")
with contextlib.redirect_stdout(o41): H.cp_price(seen41)
assert seen41["cpq"]["m"]["https://coupa.ng/b222"][0] == 0 and "pid 있음 3개 = item 99 없음" in o41.getvalue() and "← 같은 pid · item 55" in o41.getvalue(), o41.getvalue()
o41 = io.StringIO(); H.RUN["cpu"] = {"s": [time.time()] * 6, "a": [time.time()] * 6}; H.RUN.pop("cpn"); seen41["cpq"]["m"]["https://coupa.ng/b222"][1] = "2026-10-04 10:00"
with contextlib.redirect_stdout(o41): H.cp_price(seen41)
assert "cp price 상한(실행 1·시간 6)" in o41.getvalue(); H.RUN["cpu"] = {}; json.dump(ev41, open("events.json", "w"))  # 1시간 상한으로 하나도 못 하면 로그 1줄
assert H.cp_same("칠성사이다 190ml 30캔", "칠성사이다, 190ml, 30개") and H.cp_same("도브 뷰티 크림바 90g 12개입", "도브 뷰티 크림바, 90g, 12개") and not H.cp_same("칠성사이다 190ml 30캔", "칠성사이다, 190ml, 60개")
assert not H.cp_same("리스테린 쿨민트 1L 2+1", "리스테린 쿨민트, 1L, 1개") and not H.cp_same("비비고 왕교자 1.05kg x2", "비비고 왕교자, 1.05kg, 1개") and not H.cp_same("수면양말 6켤레", "수면양말, 12켤레")
assert H.cp_same("맥스웰하우스 커피믹스 오리지날 180개입 × 2개", "맥스웰하우스 커피믹스 오리지날, 180개입, 2개") and H.cp_same("IPX500A 청소기", "IPX500A 무선 청소기")
# ③ 골드박스(API): 🚀 = isRocket true인 것만, 끝에 게시 시점 가격
reset41(True); H.ai_pick = lambda prompt, lines: [{"i": 0, "score": 9, "comment": "a"}, {"i": 1, "score": 8, "comment": "b"}]
H.http = lambda url, *a, **k: json.dumps({"rCode": "0", "data": [{"productName": "로켓상품", "productPrice": 1000.0, "productUrl": "https://link.coupang.com/re/1", "isRocket": True},
                                                                    {"productName": "일반상품", "productPrice": 2000.0, "productUrl": "https://link.coupang.com/re/2", "isRocket": False}]})
H.goldbox({}); t41 = sent[-1][1]["text"]
assert t41.startswith("<i>" + H.DISCLOSURE) and "1. 🚀 <a" in t41 and "2. <a" in t41 and t41.endswith("⚠️ 10/6 10:00 게시 시점 가격"), t41
os.path.exists("cp_links.json") and os.remove("cp_links.json"); H.RUN.pop("cpu", None); H.RUN.pop("cpn", None)
H.http, H.tg, H.ai_pick, time.time, H.HAS_CP, H.EVENTS, H.POSTS, H.draft = sv41
# 9-42) seen.json(Actions 캐시)을 못 받으면 실행 건너뜀(10/23 16:22 KST 캐시 받기가 85%에서 멈춤 -> 빈 seen으로 골드박스·간식 또 게시): 아무것도 안 올리고·안 쓰고(posts·seen),
#       관리자 알림 1줄, 실패(종료 코드 1)로 끝나 캐시가 안 덮임 -> 다음 실행이 다시 받음. 깨진 seen.json도 같음. Run workflow의 cold_start(COLD_START=true)면 예전처럼 처음부터
class Past42(BaseException): pass
def stop42(*a, **k): raise Past42()
sv42, H.SEEN_COLD = (H.tg, H.http, H.publish_approved, H.toss_clean_posts), False
H.tg, H.http = lambda m, **p: sent.append((m, p)) or {"message_id": 1}, lambda *a, **k: (_ for _ in ()).throw(AssertionError("네트워크 X"))
H.publish_approved = H.toss_clean_posts = stop42
pj42 = open("posts.json").read() if os.path.exists("posts.json") else None
for bad in (None, '{"goldbox_20261023": 1'):
    os.path.exists("seen.json") and os.remove("seen.json")
    if bad: open("seen.json", "w").write(bad)
    sent.clear()
    try: H.main(); raise AssertionError("안 멈춤")
    except SystemExit as e: assert e.code == 1
    assert [(m, p["chat_id"]) for m, p in sent] == [("sendMessage", "42")] and "seen.json" in sent[0][1]["text"] and "cold_start" in sent[0][1]["text"], sent
    assert (open("seen.json").read() == bad if bad else not os.path.exists("seen.json")) and (open("posts.json").read() if os.path.exists("posts.json") else None) == pj42
H.SEEN_COLD = True; os.remove("seen.json")
try: H.main(); raise AssertionError("안 지나감")
except Past42: pass  # cold_start = 기억 없이 다음 단계로
json.dump({"x": time.time()}, open("seen.json", "w")); H.SEEN_COLD = False
try: H.main(); raise AssertionError("안 지나감")
except Past42: pass  # 평소(받은 seen) = 그대로
wf42 = open(os.path.join(os.path.dirname(os.path.abspath(H.__file__)), ".github/workflows/hotdeal.yml"), encoding="utf-8").read()
assert "cold_start:" in wf42 and "type: boolean" in wf42 and "COLD_START: ${{ inputs.cold_start }}" in wf42 and "    seen = load(SEEN, {})" not in inspect.getsource(H.main)
# 캐시 복구(1번, Run workflow restore_seen = 예전 캐시 key): 같은 경로 목록으로 받아(fail-on-cache-miss) 지금 seen과 합침 — 같은 칸은 지금 값, 예전에만 있는 칸은 되살림
assert "restore_seen:" in wf42 and wf42.count("            seen.json\n            fonts\n            toss.json\n            music\n") == 2 and "fail-on-cache-miss: true" in wf42 and "key: ${{ inputs.restore_seen }}" in wf42
import subprocess; m42, d42 = re.search(r'python3 -c "(import json; o, n = .*?)"\n', wf42)[1], tempfile.mkdtemp(); os.makedirs(f"{d42}/.seen_now")
json.dump({"tsolo_20261023_16": 1, "b": 1}, open(f"{d42}/seen.json", "w")); json.dump({"b": 2, "c": 2}, open(f"{d42}/.seen_now/seen.json", "w"))
assert "seen 합침 2 + 2 -> 3" in subprocess.run([sys.executable, "-c", m42], cwd=d42, capture_output=True, text=True).stdout and json.load(open(f"{d42}/seen.json")) == {"tsolo_20261023_16": 1, "b": 2, "c": 2}
(H.tg, H.http, H.publish_approved, H.toss_clean_posts), H.SEEN_COLD = sv42, sc0
# 9-43) Threads 게시 확인(10/23 저녁 Cowork: 18:16 뒤 프로필에 글이 안 보임 — 봇은 올렸다고 기록·오류 0): 글(댓글 X) publish id를 기록·로그,
#       실행마다 계정 글 목록(/me/threads 최근 25개) 위 3개 로그 + 올린 지 10분~24시간 된 우리 글이 목록에 없으면 관리자 알림(3시간 1번). 목록 밖 옛 글은 안 셈
sv43, tk43 = (H.http, H.tg, time.time), H.E.get("THREADS_TOKEN"); H.E["THREADS_TOKEN"] = "x"; sent.clear(); H.RUN["thids"] = []
H.th_ok({"id": "111"}); H.th_ok({"id": "c9"}, top=False); assert [i for _, i in H.RUN["thids"]] == ["111"]  # 댓글은 계정 글 목록에 없음 -> 안 셈
t43 = 1792745000; seen43 = {"thids": {"t": t43, "l": [[t43 - 3600, "111"], [t43 - 1800, "222"], [t43 - 60, "333"], [t43 - 90000, "old"]]}}; H.RUN["thids"] = []
c43 = []
def http43(url, *a, **k):
    c43.append(url); return json.dumps({"data": [{"id": "111", "timestamp": "2026-11-11T09:00:00+0000", "permalink": "https://www.threads.com/@x/post/A", "text": "첫 글\n둘째 줄"}]})
H.http, H.tg, time.time = http43, (lambda m, **p: sent.append((m, p)) or {"message_id": 1}), (lambda: t43)
o43 = io.StringIO()
with contextlib.redirect_stdout(o43): H.th_verify(seen43)
assert len(c43) == 1 and "/me/threads?fields=id,timestamp,permalink,text&limit=25" in c43[0] and "th 계정 최근 글 11/11 18:00 https://www.threads.com/@x/post/A 첫 글 둘째 줄" in o43.getvalue(), o43.getvalue()
assert "th 계정 목록에 없음 1 개:" in o43.getvalue() and " 222" in o43.getvalue() and "333" not in o43.getvalue().split("목록에 없음")[1] and [x[1] for x in seen43["thids"]["l"]] == ["111", "222", "333"]  # 10분 안 = 아직, 24시간 지난 건 버림
assert len(sent) == 1 and sent[0][1]["chat_id"] == "42" and "계정 글 목록에 없음" in sent[0][1]["text"] and "계정 상태" in sent[0][1]["text"]
sent.clear(); H.th_verify(seen43); assert not sent  # 같은 알림 3시간에 1번
H.http = lambda url, *a, **k: json.dumps({"data": [{"id": str(n), "timestamp": "2026-11-11T09:00:00+0000"} for n in range(25)]})
seen43 = {"thids": {"l": [[t43 - 3600, "222"]]}}; o43 = io.StringIO()
with contextlib.redirect_stdout(o43): H.th_verify(seen43)
assert "목록에 없음" not in o43.getvalue()  # 목록 25개가 다 그보다 새 글 = 밀려난 것(안 셈)
assert "th_reply_ok, th_verify, metrics" in inspect.getsource(H.main) and "top=False)[\"id\"]" in inspect.getsource(H.th_reply)
H.http, H.tg, time.time = sv43; H.RUN["thids"] = []
if tk43 is None: H.E.pop("THREADS_TOKEN")
else: H.E["THREADS_TOKEN"] = tk43
# 9-44) 로켓 근거 없는 쿠팡 = 📦(10/23 22:3x 진우): 채널 머리 줄 '📦 쿠팡'·구매 버튼 '📦 쿠팡에서 …' · 로켓 = '🚀 쿠팡 로켓'·'🚀 쿠팡에서' 그대로 ·
#       예약에 써 둔 '🚀 쿠팡 · …' 머리 줄·'🚀 쿠팡에서' 버튼도 근거대로(이미 올라간 글은 안 고침) · 인스타 배지·사이트(제목·꾸준템 줄)·Threads 예전 틀 머리 줄도 같은 기준
sv44, s44 = (H.tg, time.time, H.EVENTS), []
H.tg = lambda m, **p: s44.append((m, p)) or {"message_id": 4400 + len(s44), "text": H.plain_of(p.get("text", "")), "entities": []}
H.EVENTS = "ev44.json"; json.dump([], open("posts.json", "w"))
json.dump([{"at": "2026-10-23 23:00", "button": "🛒 구매하러 가기", "url": "https://link.coupang.com/a/r44", "deal": True, "text": "🔥 <b>[쿠팡] 곰곰 특란 30구 (7,990원)</b>\n\n로켓프레시 · 내일 새벽 도착 보장"},
           {"at": "2026-10-23 23:01", "button": "🛒 구매하러 가기", "url": "https://link.coupang.com/a/n44", "deal": True, "text": "🔥 <b>[쿠팡] 해남 호박고구마 3kg (12,900원)</b>\n\n산지 직송 · 판매자 배송"},
           {"at": "2026-10-23 23:02", "button": "🚀 쿠팡에서 9,900원", "url": "https://link.coupang.com/a/c44", "deal": True, "text": "🚀 쿠팡 · 와우 할인 🔥\n<b>제주 감귤 5kg</b>\n9,900원\n산지 발송"},
           {"at": "2026-10-23 23:03", "button": "🚀 쿠팡에서 8,860원", "url": "https://link.coupang.com/a/k44", "deal": True, "text": "🚀 쿠팡 로켓 · 1개당 최저 🔥\n<b>코멧 손난로 30개</b>\n8,860원\n🚚 내일 도착"}],
          open(H.EVENTS, "w"), ensure_ascii=False)
time.time = lambda: TK("2026-10-23 23:05"); H.events({})
e44 = [p for m, p in s44 if m == "sendMessage" and p["chat_id"] == "@ch"]
hd44 = [next(l for l in H.plain_of(p["text"]).split("\n") if H.MALL_HEAD.fullmatch(l)) for p in e44]
assert hd44 == ["🚀 쿠팡 로켓 🔥", "📦 쿠팡 🔥", "📦 쿠팡 · 와우 할인 🔥", "🚀 쿠팡 로켓 · 1개당 최저 🔥"], hd44
assert [p["reply_markup"]["inline_keyboard"][0][0]["text"] for p in e44] == ["🚀 쿠팡에서 7,990원", "📦 쿠팡에서 12,900원", "📦 쿠팡에서 9,900원", "🚀 쿠팡에서 8,860원"], e44
print("미리보기(로켓):\n" + H.plain_of(e44[0]["text"]) + "\n[" + e44[0]["reply_markup"]["inline_keyboard"][0][0]["text"] + "]")
print("미리보기(로켓 아님):\n" + H.plain_of(e44[1]["text"]) + "\n[" + e44[1]["reply_markup"]["inline_keyboard"][0][0]["text"] + "]")
assert [H.cp_rocket(H.plain_of(p["text"])) for p in e44] == [True, False, False, True] and not H.cp_rocket("🚀 쿠팡 · 와우 할인 🔥\n옛 글\n1원")  # 10/23 전 '🚀 쿠팡' 머리 줄 = 로켓 아님
assert [H.title_of(H.plain_of(p["text"])) for p in e44][1] == "[쿠팡] 해남 호박고구마 3kg (12,900원)" and S40.steady_st("📦 쿠팡 · 꾸준히 팔리는 상품 👍\n휴지\n9,900원 · 리뷰 1,969") == "리뷰 1,969"  # 사이트 제목·꾸준템 줄
assert H.mall_head("coupang", "", "🔥", False) == "📦 쿠팡 🔥" and H.mall_btn("coupang", "1,000원", False) == "📦 쿠팡에서 1,000원" and H.mall_btn("toss", "1,000원", False) == "💙 토스에서 1,000원"
assert H.buy_btn("[쿠팡] 고구마 (1,000원)", "https://link.coupang.com/a/x", "그냥 좋음") == "📦 쿠팡에서 1,000원" and H.buy_btn("[쿠팡] 고구마 (1,000원)", "https://link.coupang.com/a/x", "로켓배송 아님") == "📦 쿠팡에서 1,000원"
NO44 = ["로켓배송은 아니지만 무료배송", "로켓 아님 · 판매자 배송", "비로켓 상품", "로켓배송이 아니라 업체 직배송", "로켓배송 미적용", "로켓배송이 아닌 판매자 상품", "로켓배송 아님", "로켓와우 할인"]
assert not [x for x in NO44 if H.cp_rocket(x)] and all(H.cp_rocket(x) for x in ("로켓배송 · 57% 할인", "로켓프레시 새벽 도착", "로켓배송 내일 도착"))  # 리뷰: '아닌·미적용·비로켓·로켓와우(멤버십)' = 근거 X
OLD44 = "이 포스팅은 …\n\n🚀 쿠팡 · 와우 할인 🔥\n제주 감귤 5kg\n9,900원"
assert H.buy_btn("[쿠팡] 제주 감귤 5kg (9,900원)", "https://link.coupang.com/a/x", OLD44) == "🚀 쿠팡에서 9,900원"  # 10/23 전 글 링크 교체 = 머리 줄(🚀 쿠팡)과 같은 버튼
assert re.sub(H.CP_OLD, H.CP_PLAIN[0], OLD44, flags=re.M).split("\n")[2] == "📦 쿠팡 · 와우 할인 🔥" and re.sub(H.CP_OLD, H.CP_PLAIN[0], "🚀 쿠팡 로켓 · 1개당 최저 🔥", flags=re.M) == "🚀 쿠팡 로켓 · 1개당 최저 🔥"
assert 're.sub(CP_OLD, CP_PLAIN[0], posts[i]["text"], flags=re.M).split' in inspect.getsource(H.threads_deals)  # 10/23 전 채널 글이 새 Threads 글로 갈 때 = 📦
sl44 = (H.store_link, H.affiliate); H.store_link, H.affiliate = (lambda u: "https://www.coupang.com/vp/products/1"), (lambda u: ("https://link.coupang.com/a/AFF", True))
D44 = {"title": "[쿠팡] 휴지 30롤 (9,900원/무료)", "url": "https://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&no=101", "board": "뽐뿌"}
assert [H.deal_post(D44, c)[2] for c in ("싸다", "로켓배송 내일 도착")] == ["📦 쿠팡에서 9,900원", "🚀 쿠팡에서 9,900원"]  # 커뮤니티 쿠팡 딜 버튼 = 머리 줄과 같은 근거
H.store_link, H.affiliate = sl44
H.tg, time.time, H.EVENTS = sv44
# 9-45) 사이트 진열 전용(10/24 02:1x 진우 '생필품·화장품은 사이트에 먼저 빠르게'): events "shelf": true -> 채널·Threads·인스타 X, 사이트만(품목 칸·🔥/⏳·상품 페이지·사이트맵) ·
#       쿠팡 상품 주소 = 딥링크로 바뀐 뒤(6시간 조건 X) · 같은 url 채널 예약이 나중에 오면 채널엔 평소대로, 사이트 글은 하나 · 19:50 꾸준템 = shelf 👍도(날짜 상관없이), 가끔 품목 모음
#       · 채널 쪽 계산(시간당 상한·마지막 글 시각·관리자 중복·미리보기·모아보기·카드·Threads 후보)에 안 섞임
import build_site as S45
sv45 = (H.http, H.tg, time.time, H.HAS_CP, H.EVENTS, H.POSTS, H.CP_LINKS if hasattr(H, "CP_LINKS") else None)
d45 = tempfile.mkdtemp(); cwd45 = os.getcwd(); os.chdir(d45)
H.EVENTS, H.POSTS, H.HAS_CP, sent45, c45 = "events.json", "posts.json", True, [], []
import calendar; T45 = calendar.timegm(time.strptime("2026-10-24 19:55", "%Y-%m-%d %H:%M")) - 9 * 3600  # KST 10/24 19:55 (1년 중 297일 = 3의 배수 -> 품목 모음 날)
time.time = lambda: T45
P45 = "https://www.coupang.com/vp/products/45"
SH45 = lambda u, n, at, ic="👍", **k: {"at": at, "shelf": True, "url": u, "button": "🛒 구매하러 가기", "text": f"{ic} <b>[쿠팡] {n} (12,900원/무료)</b>\n\n꾸준히 잘 팔리는 생필품", **k}
ev45 = [SH45(P45, "크리넥스 화장지 30롤", "2026-10-20 09:00", pid="45", now="12,500원", chk="2026-10-24 09:10", target="11,900원"),  # 6시간 지난 shelf도 딥링크·진열
        SH45("https://link.coupang.com/a/sh2", "깨끗한나라 물티슈 100매 10팩", "2026-10-24 19:00"),
        SH45("https://link.coupang.com/a/sh3", "페리오 치약 120g 10개", "2026-10-24 19:10"),
        SH45("https://link.coupang.com/a/sh4", "다우니 섬유유연제 1L", "2026-10-24 23:00"),  # 아직 시각 전 = 진열 X
        SH45("https://link.coupang.com/a/sh5", "피죤 세탁세제 3L", "2026-10-24 19:20", ic="🔥"),
        {"at": "2026-10-24 19:50", "deal": True, "url": "https://link.coupang.com/a/ch1", "button": "🛒 구매하러 가기", "text": "🔥 <b>[쿠팡] 채널 예약 상품 (5,000원)</b>"}]
json.dump(ev45, open("events.json", "w")); json.dump([{"t": "2026-10-24 19:30", "text": "🔥 [쿠팡] 예전 채널 글 (1원)", "url": "https://link.coupang.com/a/old", "mid": 7}], open("posts.json", "w"))
def http45(url, body=None, headers=None, method=None):
    c45.append(url)
    if url.endswith("/deeplink"):
        return json.dumps({"rCode": "0", "data": [{"originalUrl": u, "shortenUrl": "https://link.coupang.com/a/b" + re.search(r"/products/(\d+)", u)[1]} for u in body["coupangUrls"]]})
    return "{}"
def tg45(method, **p):
    sent45.append((method, p))
    return {"message_id": 900 + len(sent45), "text": H.plain_of(p.get("text", "")), "entities": []}
H.http, H.tg, seen45 = http45, tg45, {}; H.RUN.pop("cpu", None); H.RUN.pop("cpn", None); H.RUN["ch_last"] = 0
assert [e["url"] for e in H.load(H.EVENTS, [])] == ["https://link.coupang.com/a/ch1"]  # 채널 쪽(events·미리보기·토스 쉼·알림)은 shelf를 아예 못 봄
H.shelf_posts(seen45); assert [p["url"][-3:] for p in json.load(open("posts.json"))] == ["old", "sh2", "sh3", "sh5"]  # 딥링크 전 쿠팡 상품 주소 = 진열 X(생 주소 X) · 시각 전(sh4) X
json.dump(ev45 + [SH45(f"https://www.coupang.com/vp/products/9{k}", f"진열 {k}", "2026-10-20 09:00") for k in range(8)]
          + [{"at": "2026-10-24 21:00", "deal": True, "url": "https://www.coupang.com/vp/products/99999", "button": "x", "text": "🔥 <b>[쿠팡] 채널 상품 (1원)</b>"}], open("events.json", "w"))
nc45 = len(c45); H.cp_links(seen45); cl45 = json.load(open(H.CP_LINKS))
assert "https://www.coupang.com/vp/products/99999" in cl45 and len(cl45) == 10 and sum(u.endswith("/deeplink") for u in c45[nc45:]) == 1, (cl45, c45[nc45:])  # 10/24 진우 '수량 제한 X': 한 호출에 묶어 다(채널 예약 먼저)
json.dump(ev45 + [SH45(f"https://www.coupang.com/vp/products/8{k:02d}", f"진열 {k}", "2026-10-20 09:00") for k in range(45)], open("events.json", "w")); os.remove(H.CP_LINKS); H.RUN.pop("cpn", None); H.RUN.pop("cpu", None)
nc45 = len(c45); H.cp_links(seen45); assert len(json.load(open(H.CP_LINKS))) == 46 and sum(u.endswith("/deeplink") for u in c45[nc45:]) == 3  # 46개 = 20·20·6 세 번 호출(진열만 = 실행마다 CP_RUN-2번까지)
json.dump(ev45, open("events.json", "w")); os.remove(H.CP_LINKS); H.RUN.pop("cpn", None); H.RUN.pop("cpu", None); seen45.pop("cpdl", None)
H.cp_links(seen45); DL45 = json.load(open(H.CP_LINKS))[P45]
assert DL45 == "https://link.coupang.com/a/b45" and any(u.endswith("/deeplink") for u in c45)  # at 6시간 지났어도 shelf는 변환
H.shelf_posts(seen45); po45 = json.load(open("posts.json"))
sh45 = [p for p in po45 if p.get("shelf")]
assert [S45.parse(S45.title_of(p["text"]))[1] for p in sh45] == ["깨끗한나라 물티슈 100매 10팩", "페리오 치약 120g 10개", "피죤 세탁세제 3L", "크리넥스 화장지 30롤"], sh45  # 시각 지난 것만
assert all(p["own"] == 1 and "mid" not in p and p["t"] == "2026-10-24 19:55" and p["text"].startswith("이 포스팅은 쿠팡 파트너스") for p in sh45) and sh45[3]["url"] == DL45  # 대가성 문구 맨 앞 · 채널 글 번호 X
assert "📦 쿠팡" in sh45[0]["text"] and "결제 전 최종가" in sh45[0]["text"], sh45[0]["text"]  # 채널과 같은 몰별 틀
assert not sent45  # 채널·관리자 아무것도 안 보냄
H.shelf_posts(seen45); assert len(json.load(open("posts.json"))) == len(po45)  # 같은 url = 1번만
t45, ents45 = H.html_ents('<i>고지</i>\n\n🔥 <b>[쿠팡] 이름</b> <a href="https://x.y/?a=1&amp;b=2">링크</a> 😀 <a href="https://z">끝</a>')
assert t45 == "고지\n\n🔥 [쿠팡] 이름 링크 😀 끝" and [(t45.encode("utf-16-le")[e["offset"] * 2:(e["offset"] + e["length"]) * 2].decode("utf-16-le"), e["url"]) for e in ents45] == [("링크", "https://x.y/?a=1&b=2"), ("끝", "https://z")]  # UTF-16 오프셋(😀 = 2)
# 채널 쪽 계산에 안 섞임: 시간당 상한·마지막 채널 글 시각·관리자 중복 링크·카드·모아보기·Threads 후보·날씨/간식
bk45 = open("posts.json").read(); json.dump(po45 + [{**sh45[0], "url": f"https://link.coupang.com/a/z{k}"} for k in range(80 + H.HOUR_CAP)], open("posts.json", "w"))  # 한 번에 많이 진열해도
assert not H.busy(seen45) and H.ch_last(seen45) == T45 - 25 * 60  # 시간당 상한·'방금 채널 글'로 안 셈
assert H.admin_deal(["[쿠팡] 예전 채널 글 (1원)"], "https://link.coupang.com/a/old", 5, seen45) and sent45[-1][1]["text"] == "이미 채널에 올린 링크야"; sent45.clear()  # 관리자 중복 확인 = 채널 글 80개(진열 글이 자리 X)
open("posts.json", "w").write(bk45)
import inspect
assert 'not p.get("shelf") and p["t"] >= since' in inspect.getsource(H.threads_deals) and 'and not p.get("shelf")]  # 사이트 진열(shelf) = 모아보기' in inspect.getsource(H.digest)  # Threads 개별 후보·21시 모아보기·블로그 X
assert [i for i, _ in S45.day_deals(po45, "2026-10-24")] == [0]  # 카드·인스타·릴스·Threads 카드 = 채널 글만
H.events(seen45); assert [p["reply_markup"]["inline_keyboard"][0][0]["url"] for m, p in sent45 if m == "sendMessage"] == ["https://link.coupang.com/a/ch1"]  # 채널 = 보통 예약만
# 사이트: 품목 칸(🧻 생필품)·상태(own_end: Cowork now·chk)·상품 페이지·사이트맵
H.own_end(seen45); po45 = json.load(open("posts.json")); i45 = next(i for i, p in enumerate(po45) if p.get("url") == DL45)
assert po45[i45]["now"] == "12,500원" and po45[i45]["st"] == "wait" and po45[i45]["chk"] == "10/24 9시", po45[i45]  # 진열 글 = events now·chk 그대로(글 시각보다 옛 확인이어도)
S45.build(po45, "site"); ix45, sm45 = open("site/index.html").read(), open("site/sitemap.xml").read()
lf45 = ix45.split('id="life"')[1].split("</section>")[0]
assert f"p/{i45}.html" in lf45 and "지금 가격 (10/24 9시 확인)" in lf45 and f"/p/{i45}.html" in sm45 and os.path.exists(f"site/p/{i45}.html")
pg45 = open(f"site/p/{i45}.html").read(); assert "제휴 마케팅 활동의 일환으로" in pg45 and f'href="{DL45}"' in pg45  # 상품 페이지 = 채널 글 페이지와 같은 대가성 문구·구매 버튼(딥링크)
# 같은 url 채널 예약이 나중에 오면: 채널엔 평소대로 · 사이트 카드는 채널 글 하나(진열 글은 칸·날짜 목록·사이트맵에서 빠짐, 페이지는 그대로)
time.time = lambda: T45 + 3600
json.dump(ev45 + [{"at": "2026-10-24 20:50", "deal": True, "url": P45, "button": "🛒 구매하러 가기", "text": "🔥 <b>[쿠팡] 크리넥스 화장지 30롤 (11,500원/무료)</b>"}], open("events.json", "w"))
sent45.clear(); H.events(seen45); po45 = json.load(open("posts.json"))
assert [p["reply_markup"]["inline_keyboard"][0][0]["url"] for m, p in sent45 if m == "sendMessage"] == [DL45]  # 같은 상품 채널 예약 = 그대로 채널에(딥링크)
j45 = max(i for i, p in enumerate(po45) if p.get("url") == DL45); assert j45 > i45 and po45[j45].get("mid") and not po45[j45].get("shelf")
assert S45.shelf_gone(po45) == {i45}
S45.build(po45, "site"); ix45, al45, sm45 = open("site/index.html").read(), open("site/all.html").read(), open("site/sitemap.xml").read()
assert f"p/{i45}.html" not in ix45 and f"p/{i45}.html" not in al45 and f"/p/{i45}.html<" not in sm45 and f"p/{j45}.html" in ix45 and os.path.exists(f"site/p/{i45}.html")
assert H.admin_deal is not None and not any(H.link_key(x.get("url")) == H.link_key("https://link.coupang.com/a/sh2") for x in json.load(open("posts.json"))[-80:] if not x.get("shelf"))  # 관리자 중복 확인은 채널 글만
# 19:50 꾸준템: shelf 👍 = 날짜 상관없이 · 생필품 3개+ & 품목 모음 날 = '🧻 생필품 스테디셀러 모음'(채널·Threads·사이트 페이지 같은 제목)
po45 = json.load(open("posts.json"))
for p in po45:
    if p.get("shelf"):
        p["t"] = "2026-09-01 10:00"  # 한 달 전 진열이어도
json.dump(po45, open("posts.json", "w"))
time.time = lambda: T45 - 5 * 60
os.makedirs("docs", exist_ok=True); sent45.clear()
po45 += [{**sh45[0], "text": sh45[0]["text"].replace("깨끗한나라 물티슈 100매 10팩", "품절 물티슈"), "url": "https://link.coupang.com/a/so", "st": "out"},
          {**sh45[0], "text": sh45[0]["text"].replace("깨끗한나라 물티슈 100매 10팩", "많이 산 진열").replace("👍", "🛒") + "\n한 달 3만명+ 구매", "url": "https://link.coupang.com/a/bu"}]
assert [(H.th_steady(p["text"]), H.th_weak(p["text"]), S45.parse(S45.title_of(p["text"]))[1]) for p in po45[-2:]] == [(True, False, "품절 물티슈"), (False, True, "많이 산 진열")]  # 일시 품절 👍 진열 · 많이 산 🛒 진열
json.dump(po45, open("posts.json", "w"))
cd45 = H.steady_cands(seen45, time.time(), 99)
assert {x["n"] for x in cd45} >= {"깨끗한나라 물티슈 100매 10팩", "페리오 치약 120g 10개"} and not {x["n"] for x in cd45} & {"피죤 세탁세제 3L", "품절 물티슈", "많이 산 진열"}, cd45  # 👍 진열만(🔥·🛒·일시 품절 진열 X)
H.steady_list(seen45); st45 = [p for m, p in sent45 if m == "sendMessage"]
assert len(st45) == 1 and "🧻 <b>생필품 스테디셀러 모음</b>" in st45[0]["text"] and "12,500원 (10/24 9시 확인)" in st45[0]["text"] and json.load(open(H.STEADY_FILE))["head"] == "🧻 생필품 스테디셀러 모음", st45
S45.steady_page("docs"); assert "<h2 id=\"sth\">🧻 생필품 스테디셀러 모음</h2>" in open("docs/steady.html").read()
H.http, H.tg, time.time, H.HAS_CP, H.EVENTS, H.POSTS = sv45[:6]
os.chdir(cwd45)
# 9-47) 토스 대량 사이트 진열(10/24 09:4x 진우 '웹사이트엔 최대한 많은 수량' — TOSS_SITE True): 실행마다 목록 1곳(하루특가 -> 많이 팔린 순위 -> 카테고리 베스트) 돌아가며
#       사이트에 없는·판매 중 상품 -> 쉐어링크(있으면 재사용) -> 사이트 전용 글(own·shelf·tid, 채널·Threads X, 리뷰 X, 대가성 문구·게시 시점 가격) · 링크 오류 = 그 상품 하루 쉬고 실행 멈춤
sv47 = (H.toss, H.HAS_TOSS, H.tg, time.time, dict(H.RUN), H.POSTS, H.TOSS_SITE); d47 = tempfile.mkdtemp(); cwd47 = os.getcwd(); os.chdir(d47)
H.TOSS_SITE = True  # 10/24 10시 보류(False)지만 켰을 때 동작은 그대로 확인
H.HAS_TOSS, H.POSTS, sent47, calls47 = True, "posts.json", [], []
H.RUN.pop("treuse", None); time.time = lambda: 1793000000.0
X47 = lambda i, g, n, p, so=False: {"tacaItemId": i, "tacaId": g, "displayName": n, "displayPrice": p, "discountRate": 30, "reviewScore": 4.9, "reviewCount": 1234, "isSoldOut": so}
def toss47(path, body=None):
    calls47.append(path)
    if path == "/categories":
        return {"categories": [{"categoryId": 5, "displayName": "생활용품"}]}
    if path == "/links":
        if body["tacaItemId"] == 21:
            raise RuntimeError("발급 제한 상품")
        return {"shortUrl": f"https://toss.im/_m/L{body['tacaItemId']}"}
    return {"items": {"/products/today-deals?size=30": [X47(10, 100, "하루 물티슈", 5900), X47(11, 110, "이미 있는 것", 1000), X47(12, 120, "품절 상품", 1000, True)],
                      "/products/best-selling?size=30": [X47(20, 200, "베스트 세제", 12900), X47(21, 210, "링크 안 됨", 1000), X47(22, 220, "베스트 휴지", 15900)],
                      "/products/best-categories/5?size=30": [X47(30, 300, "생활 수세미", 3900)]}[path]}
H.toss, H.tg = toss47, lambda m, **p: sent47.append((m, p)) or {"message_id": 1}
json.dump([{"t": "2026-10-20 10:00", "text": "💙 토스 특가 🔥\n이미 있는 것\n1,000원", "url": "https://toss.im/_m/OLD", "own": 1, "tid": 11}], open("posts.json", "w"))
s47 = {"tlink": {"m": {"20": ["https://toss.im/_m/MADE20", 1]}}}
names47 = lambda: [S40.parse(S40.title_of(p["text"]))[1] for p in json.load(open("posts.json")) if p.get("shelf")]
H.toss_shelf(s47); assert names47() == ["하루 물티슈"]  # 하루특가 목록: 품절·이미 사이트에 있는 것 X
p47 = json.load(open("posts.json"))[-1]
assert (p47["own"], p47["shelf"], p47["tid"], p47["url"], "mid" in p47) == (1, 1, 10, "https://toss.im/_m/L10", False) and p47["text"].startswith(H.TOSS_NOTE), p47
assert "💙 토스 특가 · 하루특가 · 밤 12시까지 🔥\n하루 물티슈\n5,900원 (30%↓)\n⚠️" in p47["text"] and "⭐" not in p47["text"] and "게시 시점 가격" in p47["text"] and "쿠팡" not in p47["text"], p47["text"]
assert s47["tossid"]["m"]["https://toss.im/_m/L10"][0] == 100 and not sent47  # own_end가 상품 그룹 id로 바로 확인(단축 링크 안 풂) · 채널·관리자 X
H.toss_shelf(s47); assert names47() == ["하루 물티슈", "베스트 세제"] and "https://toss.im/_m/MADE20" in [p["url"] for p in json.load(open("posts.json"))] and "21" in s47["tshelf"]["x"]  # 만든 링크 재사용 · 링크 오류 = 그 상품 쉬고 멈춤(22는 다음에)
H.toss_shelf(s47); assert names47()[-1] == "생활 수세미" and "생활용품 베스트 1위" in json.load(open("posts.json"))[-1]["text"]  # 카테고리 베스트
H.toss_shelf(s47); H.toss_shelf(s47); assert names47() == ["하루 물티슈", "베스트 세제", "생활 수세미", "베스트 휴지"] and calls47.count("/links") == 4  # 다시 돌아옴: 있는 것 X · 오류 난 21은 하루 쉼(발급 10·21 실패·30·22)
H.RUN["treuse"] = True; n47 = len(calls47); H.toss_shelf(s47); assert len(calls47) == n47; H.RUN.pop("treuse")  # 토스 점검(재사용 모드) = X
H.TOSS_SITE = False; H.toss_shelf(s47); assert len(calls47) == n47; H.TOSS_SITE = True
po47 = json.load(open("posts.json")); assert not [i for i, _ in S40.day_deals(po47, time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600)))] and not sent47  # 카드·인스타 X · 채널 X
S40.build(po47, "site"); tz47 = open("site/index.html").read().split('id="toss"')[1].split("</section>")[0]
assert all(f"p/{i}.html" in tz47 for i in range(1, 5)) and "⭐" not in tz47  # 사이트 💙 토스 칸에 진열(리뷰 X)
H.toss, H.HAS_TOSS, H.tg, time.time = sv47[:4]; H.RUN.clear(); H.RUN.update(sv47[4]); H.POSTS, H.TOSS_SITE = sv47[5:7]; os.chdir(cwd47)
assert H.TOSS_SITE is False  # 보류 중(10/24 10시 Cowork — API 신청 범위)
# 9-48) 쿠팡 진열 링크 변환 실패(10/24 10시 Cowork — 약 110개 중 9개 rCode 400): 진열 실패는 상품마다 DM 말고 하루 1번 묶어서(9시~, 상품 번호만) ·
#       서로 다른 날 2번 실패한 진열 상품은 다음부터 변환 시도 X(events는 그대로) · 채널 예약 실패는 지금처럼 바로 알림
import calendar
sv48 = (H.http, H.tg, time.time, H.HAS_CP, H.EVENTS, dict(H.RUN)); d48 = tempfile.mkdtemp(); cwd48 = os.getcwd(); os.chdir(d48)
H.EVENTS, H.HAS_CP, dm48, dl48 = "events.json", True, [], []
G48, B48 = "https://www.coupang.com/vp/products/5001", "https://www.coupang.com/vp/products/77777"
json.dump([{"at": "2026-10-24 09:00", "shelf": True, "url": u, "text": f"👍 <b>[쿠팡] {n} (1,000원)</b>"} for u, n in ((G48, "좋은 세제"), (B48, "제휴 안 되는 세제"))], open("events.json", "w"))
def http48(url, body=None, headers=None, method=None):
    us = body["coupangUrls"]; dl48.append(list(us))
    return json.dumps({"rCode": "400", "rMessage": "url convert failed"} if B48 in us else {"rCode": "0", "data": [{"originalUrl": u, "shortenUrl": "https://link.coupang.com/a/g" + u[-4:]} for u in us]})
H.http, H.tg = http48, lambda m, **p: dm48.append(p.get("text", "")) or {"message_id": 1}
at48 = lambda d: (lambda t: [H.RUN.pop(k, None) for k in ("cpu", "cpn")] and None or setattr(time, "time", lambda: t))(calendar.timegm(time.strptime(d, "%Y-%m-%d %H:%M")) - 9 * 3600)
s48 = {}; at48("2026-10-24 10:00"); H.cp_links(s48)
assert json.load(open(H.CP_LINKS)) == {G48: "https://link.coupang.com/a/g5001"} and len(dm48) == 1 and "진열 링크 변환 안 됨 1개" in dm48[0] and "제휴 안 되는 세제 (pid 77777) — 내일 1번 더 시도" in dm48[0] and B48 not in dm48[0], dm48  # 묶음 오류 -> 나눠서 좋은 건 변환 · 알림 1번(주소 X)
at48("2026-10-24 11:00"); H.cp_links(s48); assert len(dm48) == 1 and len(dl48) == 3  # 같은 날 = 다시 시도 X·알림 X
at48("2026-10-25 09:30"); H.cp_links(s48); assert len(dm48) == 1 and len(dl48) == 3  # 24시간 안 = 아직
at48("2026-10-25 10:30"); H.cp_links(s48); assert len(dm48) == 2 and "제휴 안 되는 세제 (pid 77777) — 2번째(다른 날) · 다음부터 진열 시도 X" in dm48[1] and dl48[-1] == [B48], dm48  # 다음 날 1번 더(실패) -> 알림 1번
at48("2026-10-27 10:00"); H.cp_links(s48); assert len(dl48) == 4 and len(dm48) == 2  # 2번 실패한 진열 = 다시 안 부름
H.http, H.tg, time.time, H.HAS_CP, H.EVENTS = sv48[:5]; H.RUN.clear(); H.RUN.update(sv48[5]); os.chdir(cwd48)
# 9-49) (10/24 리뷰 blocker) 묶음 오류를 반씩 나누다 실행 호출 상한에 걸리면 나눈 조각을 다음 실행으로 — 안 그러면 매 실행 같은 20개를 처음부터 나눠 나쁜 주소 1개에 진열 변환이 멈춤
sv49 = (H.http, H.tg, time.time, H.HAS_CP, H.EVENTS, dict(H.RUN)); d49 = tempfile.mkdtemp(); cwd49 = os.getcwd(); os.chdir(d49)
H.EVENTS, H.HAS_CP, dl49 = "events.json", True, []
U49 = [f"https://www.coupang.com/vp/products/{9000 + k}" for k in range(45)]; B49 = U49[0]  # 정렬 맨 앞 = 첫 묶음에 나쁜 주소
json.dump([{"at": "2026-10-24 09:00", "shelf": True, "url": u, "text": f"👍 <b>[쿠팡] 상품{k} (1,000원)</b>"} for k, u in enumerate(U49)], open("events.json", "w"))
def http49(url, body=None, headers=None, method=None):
    us = body["coupangUrls"]; dl49.append(len(us))
    return json.dumps({"rCode": "400", "rMessage": "url convert failed"} if B49 in us else {"rCode": "0", "data": [{"originalUrl": u, "shortenUrl": "https://link.coupang.com/a/g" + u[-4:]} for u in us]})
H.http, H.tg, s49 = http49, lambda m, **p: {"message_id": 1}, {}
for k49 in range(3):
    at48(f"2026-10-24 1{k49}:00"); H.cp_links(s49)
    assert len(dl49) <= 4 * (k49 + 1), dl49  # 진열만 = 실행마다 CP_RUN-2번까지
cl49 = json.load(open(H.CP_LINKS))
assert len(cl49) == 44 and B49 not in cl49 and s49["cpdl"]["f"][B49] == ["2026-10-24"] and not s49["cpdl"]["pq"] and dl49 == [20, 10, 5, 2, 1, 1, 3, 5, 10, 5, 20], (len(cl49), dl49, s49["cpdl"].get("pq"))  # 3번 실행에 좋은 44개 다 + 나쁜 1개 찾음(진열 실패 날짜 → 하루 1번 알림) · 남은 조각 X
H.http, H.tg, time.time, H.HAS_CP, H.EVENTS = sv49[:5]; H.RUN.clear(); H.RUN.update(sv49[5]); os.chdir(cwd49)
print("OK: 모든 셀프체크 통과")
