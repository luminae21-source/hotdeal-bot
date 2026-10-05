#!/usr/bin/env python3
"""핫딜봇: 뽐뿌 RSS -> Claude 선별/코멘트 -> 채널 바로 게시(링크프라이스 몰은 검색 제휴 링크 자동).
쿠팡 등 수동 몰은 관리자에게 사본 -> 제휴 링크로 답장하면 채널 글 교체(뽐뿌가 GitHub IP 차단 -> 쇼핑몰 주소 자동 추출 불가). 쿠팡 API 키가 있으면 매일 골드박스 TOP5 초안.
GitHub Actions에서 30분마다 실행(tick.yml 타이머가 workflow_dispatch로 실행 + 예약 보조). 외부 패키지 없음(파이썬 표준 라이브러리만)."""
import base64, hashlib, hmac, html, json, os, re, tempfile, time, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from build_site import BASE as SITE, BLOG, title_of, split_title

E = {k: "".join(v.split()) for k, v in os.environ.items()}  # 시크릿 붙여넣을 때 섞인 공백·줄바꿈 전부 제거
ADMIN, CHANNEL = E.get("TG_ADMIN_ID", ""), E.get("TG_CHANNEL", "")
MODEL = E.get("MODEL") or "claude-sonnet-5-5"
MIN_SCORE = int(E.get("MIN_SCORE") or 7)
HAS_CP = bool(E.get("COUPANG_ACCESS_KEY") and E.get("COUPANG_SECRET_KEY"))
MAX_DRAFTS = 5                 # 1회 실행당 검수 요청 최대 개수
MIN_AGE, MAX_AGE = 30, 360     # 분: 반응이 쌓인 뒤 판단, 너무 오래된 글은 무시
FEEDS = {"ppomppu": "뽐뿌"}  # 보드 추가: {"rss id": "표시명"}
SEEN, POSTS = "seen.json", "posts.json"  # posts.json: 채널에 게시된 딜 -> build_site.py가 웹사이트로 만듦
CP_HOST, CP_BASE = "https://api-gateway.coupang.com", "/v2/providers/affiliate_open_api/apis/openapi/v1"
DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
AFF_NOTE = "이 포스팅은 제휴 마케팅 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
TOSS_NOTE = "이 포스팅은 토스쇼핑 쉐어링크 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."  # 토스 권장 문구
TOSS_HOSTS = ("toss.im", "toss.shopping")  # 쉐어링크 단축(toss.im/_m/..)·원본(toss.shopping/t/..)
LP = "💰 링크프라이스 최대 {} · 딥링크 만들어 답장"
STORES = {"쿠팡": "💰 쿠팡 파트너스 · 링크 만들어 답장", "토스": "💰 토스 쉐어링크 · 링크 만들어 답장",  # 뽐뿌 제목 [쇼핑몰] -> 초안 안내 버튼
          "g마켓": LP.format("0.6%"), "지마켓": LP.format("0.6%"), "옥션": LP.format("0.6%"), "롯데온": LP.format("1.4%"),
          "롯데on": LP.format("1.4%"), "이마트": LP.format("1%"), "11번가": LP.format("1.05%"), "알리": LP.format("6.3%")}
# ponytail: 수수료율은 2026-10-05 링크프라이스 화면 기준 고정값. 바뀌면 여기만 고치면 됨
LP_AID = "A100708461"  # 링크프라이스 사이트 코드 (모든 링크프라이스 링크에 그대로 보이는 공개 값)
LP_SEARCH = {  # 링크프라이스 승인 몰: 제목 [쇼핑몰] -> (머천트, 표시 이름, 검색 주소). 상품 주소는 뽐뿌 차단으로 못 얻어서 검색 결과로 연결
    "g마켓": ("gmarket", "G마켓", "https://www.gmarket.co.kr/n/search?keyword="),
    "지마켓": ("gmarket", "G마켓", "https://www.gmarket.co.kr/n/search?keyword="),
    "옥션": ("auction", "옥션", "https://www.auction.co.kr/n/search?keyword="),
    "롯데온": ("lotteon", "롯데온", "https://www.lotteon.com/csearch/search/search?render=search&platform=pc&q="),
    "롯데on": ("lotteon", "롯데온", "https://www.lotteon.com/csearch/search/search?render=search&platform=pc&q=")}
AFF_HOSTS = ("click.linkprice.com", "lpweb.kr", "linkmoa.kr", "lase.kr", "bestmore.net", "newtip.net", "s.click.aliexpress.com")  # 쿠팡(link.coupang.com) 외 제휴 링크 도메인
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
esc = html.escape

DEAL_PROMPT = """너는 한국 핫딜 텔레그램 채널 편집자야. 아래 딜 중 구독자가 실제로 살 만한 것만 골라 pick 도구로 반환해.
점수(1~10) 기준: 가격 매력, 생필품/대중성, 커뮤니티 반응(조회 대비 추천·댓글). 비추천이 많거나 품절·종료·가격오류 언급이 있으면 제외.
comment: 구독자용 1~2줄. 핵심 조건(쿠폰·카드할인·무배 등)을 사실대로. 과장 금지, 확인 안 된 '역대최저' 금지, 건강식품 효능 언급 금지, 이모지 최대 1개.
q: 쇼핑몰 검색창에 넣을 짧은 검색어(브랜드+상품명+핵심 용량, 수량·가격·쿠폰 문구 빼고 20자 안팎).
5점 미만은 반환하지 마.
"""
GOLD_PROMPT = """쿠팡 골드박스(오늘 하루 특가) 목록이야. 대중적으로 많이 살 만한 상품 5개를 골라 pick 도구로 반환해.
comment: 1줄, 사실 위주, 과장 금지, 건강식품 효능 언급 금지.
"""


def http(url, body=None, headers=None, method=None):
    h = {"User-Agent": UA, **(headers or {})}
    if body is not None:
        body, h["Content-Type"] = json.dumps(body).encode(), "application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, body, h, method=method), timeout=30) as r:
            return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")
    except urllib.error.HTTPError as e:
        e.body = e.read().decode("utf-8", "replace")[:300]  # 로그에서 원인 바로 보이게
        print("HTTP", e.code, url.split("/bot")[0], e.body)
        raise


def tg_video(path, caption):
    """관리자에게 영상 파일 업로드 (sendVideo, multipart). -> 보낸 메시지"""
    b = "hotdeal" + os.urandom(8).hex()
    fields = {"chat_id": ADMIN, "caption": caption, "supports_streaming": "true", "width": "1080", "height": "1920"}
    body = ("".join(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n' for k, v in fields.items())
            + f'--{b}\r\nContent-Disposition: form-data; name="video"; filename="reel.mp4"\r\nContent-Type: video/mp4\r\n\r\n').encode() \
        + open(path, "rb").read() + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{E['TG_TOKEN']}/sendVideo", body,
                                 {"Content-Type": f"multipart/form-data; boundary={b}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())["result"]


def tg(method, **params):
    """텔레그램 API. 실패해도 전체 실행은 멈추지 않고 None 반환."""
    try:
        return json.loads(http(f"https://api.telegram.org/bot{E['TG_TOKEN']}/{method}", params))["result"]
    except urllib.error.HTTPError as e:
        print("TG", method, e.code, e.body)


def fetch_deals():
    deals = []
    for board, name in FEEDS.items():
        try:
            items = ET.fromstring(http(f"https://www.ppomppu.co.kr/rss.php?id={board}")).iter("item")
            for it in items:
                url = it.findtext("link", "").replace("http://", "https://")
                no = re.search(r"no=(\d+)", url).group(1)
                h = (it.findtext("hits") or "").strip(" []").split("|")
                deals.append({
                    "id": f"{board}_{no}", "url": url, "board": name,
                    "title": it.findtext("title", "").strip(),
                    "desc": html.unescape(it.findtext("description", "")).replace("\xa0", " ").strip()[:200],
                    "hits": "댓글{}·조회{}·추천{}·비추{}".format(*h) if len(h) == 4 else "",
                    "age": (time.time() - parsedate_to_datetime(it.findtext("pubDate")).timestamp()) / 60,
                })
        except Exception as e:  # 피드 하나가 죽어도 나머지는 진행
            print("feed", board, repr(e))
    return deals


def ai_pick(prompt, lines):
    """Claude가 고른 [{i, score, comment}] (점수 내림차순)."""
    tool = {"name": "pick", "description": "게시할 항목", "input_schema": {
        "type": "object", "required": ["picks"], "properties": {"picks": {"type": "array", "items": {
            "type": "object", "required": ["i", "score", "comment"],
            "properties": {"i": {"type": "integer"}, "score": {"type": "integer"}, "comment": {"type": "string"},
                           "q": {"type": "string"}}}}}}}
    r = json.loads(http("https://api.anthropic.com/v1/messages", {
        "model": MODEL, "max_tokens": 4000, "tools": [tool], "tool_choice": {"type": "auto"},
        "messages": [{"role": "user", "content": prompt + "\n" + "\n".join(f"{i}. {l}" for i, l in enumerate(lines))}],
    }, {"x-api-key": E["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"}))
    picks = next((c["input"]["picks"] for c in r["content"] if c["type"] == "tool_use"), [])
    return sorted((p for p in picks if 0 <= p["i"] < len(lines)), key=lambda p: -p["score"])


def store_link(post_url):
    """뽐뿌 글 상단의 실제 쇼핑몰 링크 (s.ppomppu.co.kr/?...&target=<base64 원본주소>&encode=on -> 원본 주소).
    ponytail: 뽐뿌가 GitHub 서버 IP를 PC·모바일 글 모두 403 차단(2026-10-05 linkcheck) -> 지금은 None,
    그동안은 관리자가 초안에 링크로 답장하면 relink()가 교체. 차단 풀리면 이 함수가 그대로 다시 동작."""
    try:
        m = re.search(r'topTitle-link.*?href="https://s\.ppomppu\.co\.kr/\?([^"]+)"', http(post_url), re.S)
    except Exception as e:
        print("link", post_url, repr(e))
        return None
    if not m:
        return None
    q = "&" + html.unescape(m.group(1))
    t = urllib.parse.unquote(re.search(r"&target=([^&]*)", q + "&target=").group(1))  # unquote_plus 쓰면 base64의 +가 깨짐
    return (base64.b64decode(t + "=" * (-len(t) % 4)).decode() if "&encode=on" in q else t) or None


def coupang(method, path, body=None):
    dt = time.strftime("%y%m%dT%H%M%SZ", time.gmtime())
    p, _, q = (CP_BASE + path).partition("?")
    sig = hmac.new(E["COUPANG_SECRET_KEY"].encode(), (dt + method + p + q).encode(), hashlib.sha256).hexdigest()
    auth = f"CEA algorithm=HmacSHA256, access-key={E['COUPANG_ACCESS_KEY']}, signed-date={dt}, signature={sig}"
    return json.loads(http(CP_HOST + CP_BASE + path, body, {"Authorization": auth}, method))["data"]


def affiliate(url):
    """쿠팡 링크면 파트너스 링크로 변환 -> (링크, 제휴여부)."""
    if HAS_CP and url and urllib.parse.urlsplit(url).netloc.endswith("coupang.com"):
        try:
            return coupang("POST", "/deeplink", {"coupangUrls": [url]})[0]["shortenUrl"], True
        except Exception as e:
            print("deeplink", repr(e))
    return url, False


def store_info(title):
    """뽐뿌 제목의 [쇼핑몰]로 수익 안내 문구. 제휴 없는 몰은 수수료 0 표시."""
    tag = store_tag(title)
    return next((v for k, v in STORES.items() if k in tag), "💸 제휴 없는 쇼핑몰 · 수수료 0")


def draft(text, buy_url=None, score=None, info=None, label="🛒 구매하러 가기"):
    """관리자에게 검수용 초안 전송. ✅ 누르면 다음 실행 때 채널에 그대로 복사됨.
    info: 관리자만 보는 안내 버튼(채널엔 링크 버튼만 복사되므로 안 나감)."""
    kb = [[{"text": label, "url": buy_url}]] if buy_url else []
    kb.append([{"text": f"✅ 게시 ({score}점)" if score else "✅ 게시", "callback_data": "ok"},
               {"text": "❌ 패스", "callback_data": "no"}])
    if info:
        kb.append([{"text": info, "callback_data": "-"}])
    return tg("sendMessage", chat_id=ADMIN, text=text, parse_mode="HTML",
              link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": kb})


def comment_of(text):
    """채널 글(posts.json text) -> 제목 아래 코멘트 (출처 줄 제외)."""
    return split_title(text)[1].rsplit("\n\n출처:", 1)[0].strip()


def store_tag(title):
    """뽐뿌 제목 맨 앞 [쇼핑몰] -> 비교용 소문자·공백 제거 ('[G마켓]메디폴미' -> 'g마켓')."""
    tag = re.match(r"\s*\[([^\]]+)\]", title)
    return tag.group(1).lower().replace(" ", "") if tag else ""


def keyword(title):
    """Claude 검색어가 없을 때: 제목에서 [쇼핑몰]·끝의 (가격/배송) 떼고 40자."""
    t = re.sub(r"^\s*\[[^\]]*\]\s*", "", title)
    return re.sub(r"\s*\([^()]*(원|무료|무배|배송)[^()]*\)\s*$", "", t).strip()[:40]


def lp_search(title, q=None):
    """링크프라이스 승인 몰이면 그 몰 검색 결과로 가는 제휴 링크 -> (링크, 몰 이름), 아니면 (None, None)."""
    hit = next((v for k, v in LP_SEARCH.items() if k in store_tag(title)), None)
    if not hit:
        return None, None
    m, name, base = hit
    tu = urllib.parse.quote(base + urllib.parse.quote(q or keyword(title)), safe="")
    return f"https://click.linkprice.com/click.php?m={m}&a={LP_AID}&l=9999&l_cd1=3&l_cd2=0&tu={tu}", name


def deal_post(d, comment, q=None):
    """-> (본문, 버튼 링크, 버튼 이름). 쿠팡 자동 변환 > 링크프라이스 검색 링크 > 뽐뿌 글. 제휴 링크면 대가성 문구를 맨 앞에."""
    link, aff = affiliate(store_link(d["url"]))
    label = "🛒 구매하러 가기"
    if not aff:
        lp, name = lp_search(d["title"], q)
        if lp:
            link, label = lp, f"🔎 {name}에서 찾기"
    note = aff_note(link or "")
    head = f"<i>{note}</i>\n\n" if note else ""  # 공정위 지침: 대가성 문구는 첫 부분에
    text = f"{head}🔥 <b>{esc(d['title'])}</b>\n\n{esc(comment)}\n\n출처: <a href=\"{esc(d['url'])}\">{d['board']}</a>"
    return text, link or d["url"], label


def record(text, ents, url, mid=None, score=None):
    """채널에 올라간 글 -> posts.json (웹사이트·모아보기·카드·릴스 재료). mid = 채널 메시지 번호(나중에 링크 교체용), s = Claude 점수(릴스 TOP3)."""
    posts = load(POSTS, [])
    posts.append({"t": time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600)), "text": text,
                  "entities": ents, "url": url, **({"mid": mid} if mid else {}), **({"s": score} if score else {})})
    json.dump(posts, open(POSTS, "w"), ensure_ascii=False)


def post_url(mid):
    """채널 글 주소 (@공개채널 또는 -100… 숫자 id)."""
    return f"https://t.me/{CHANNEL[1:]}/{mid}" if CHANNEL.startswith("@") else f"https://t.me/c/{CHANNEL.removeprefix('-100')}/{mid}"


def post_or_draft(d, comment, score, q=None):
    """✅ 없이 채널에 바로 게시. 링크프라이스 몰은 검색 제휴 링크가 자동으로 붙음.
    쿠팡처럼 링크를 손으로 만들어야 하는 몰은 관리자에게 채널 글 사본을 보냄 -> 원하면 제휴 링크로 답장 -> 채널 글 교체(선택).
    채널 게시가 실패하면 초안으로 보내서 딜을 놓치지 않음."""
    text, url, label = deal_post(d, comment, q)
    info = store_info(d["title"])
    m = tg("sendMessage", chat_id=CHANNEL, text=text, parse_mode="HTML", link_preview_options={"is_disabled": True},
           reply_markup={"inline_keyboard": [[{"text": label, "url": url}]]})
    if not m:
        return draft(text, url, score=score, info=info, label=label)
    record(m.get("text", ""), m.get("entities", []), url, m.get("message_id"), score)
    if info.startswith("💰") and not aff_note(url):
        tg("copyMessage", chat_id=ADMIN, from_chat_id=CHANNEL, message_id=m["message_id"], reply_markup={"inline_keyboard": [
            [{"text": "📢 채널에 올라간 글", "url": post_url(m["message_id"])}],
            [{"text": info.split(" · ")[0] + " · 링크로 답장하면 채널 글 교체(선택)", "callback_data": "-"}]]})


def aff_note(url):
    """제휴 링크면 그 프로그램의 대가성 문구, 일반 쇼핑몰 주소면 ''."""
    host = urllib.parse.urlsplit(url).netloc
    return DISCLOSURE if host == "link.coupang.com" else TOSS_NOTE if host in TOSS_HOSTS else AFF_NOTE if host in AFF_HOSTS else ""


def with_note(text, ents, url):
    """제휴 링크면 대가성 문구를 맨 앞에 붙인 (text, entities). 텔레그램 오프셋은 UTF-16 단위라 그만큼 뒤로 밂."""
    note = aff_note(url)
    if note and not text.startswith("이 포스팅은"):
        n = len(note.encode("utf-16-le")) // 2
        return f"{note}\n\n{text}", [{"type": "italic", "offset": 0, "length": n}] + [{**e, "offset": e["offset"] + n + 2} for e in ents]
    return text, ents


def relink_channel(notice, mid, url):
    """이미 올라간 채널 글(mid)의 버튼을 url로 교체 + 대가성 문구. 관리자 사본과 posts.json도 같이 고침."""
    text, ents = with_note(notice.get("text", ""), notice.get("entities", []), url)
    kb = [[{"text": "🛒 구매하러 가기", "url": url}]]
    if not tg("editMessageText", chat_id=CHANNEL, message_id=mid, text=text, entities=ents,
              link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": kb}):
        return
    tg("editMessageText", chat_id=notice["chat"]["id"], message_id=notice["message_id"], text=text, entities=ents,
       link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": kb + [[{"text": "✅ 채널 글 교체됨", "callback_data": "-"}]]})
    posts = load(POSTS, [])
    for p in posts:
        if p.get("mid") == mid:
            p.update(text=text, entities=ents, url=url)
    json.dump(posts, open(POSTS, "w"), ensure_ascii=False)


def relink(m, url):
    """초안 m의 구매 버튼을 url로 교체(제휴 링크면 대가성 문구를 맨 앞에) -> (text, entities, 버튼 rows)."""
    text, ents = with_note(m.get("text", ""), m.get("entities", []), url)
    rows = [[{"text": "🛒 구매하러 가기", "url": url}]]
    rest = [r for r in m.get("reply_markup", {}).get("inline_keyboard", []) if "url" not in r[0]] or \
        [[{"text": "✅ 게시", "callback_data": "ok"}, {"text": "❌ 패스", "callback_data": "no"}]]
    tg("editMessageText", chat_id=m["chat"]["id"], message_id=m["message_id"], text=text, entities=ents,
       link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": rows + rest})
    return text, ents, rows


def publish_approved():
    """관리자 입력 처리. 텔레그램이 입력을 24시간 보관하므로 30분 주기로 충분.
    1) 초안에 링크로 답장 -> 구매 버튼 교체  2) 봇에게 '제목 줄 + 링크' 새로 보내기 -> 그 딜 초안 생성
    3) ✅/❌ -> 채널 게시/패스 (답장하고 바로 ✅ 눌러도 교체된 링크로 게시)"""
    ups = tg("getUpdates", allowed_updates=["callback_query", "message"]) or []
    fixed = {}
    for u in ups:
        m = u.get("message") or {}
        url = re.search(r"https?://\S+", m.get("text", ""))
        if not url or str(m.get("from", {}).get("id")) != ADMIN:
            continue
        if m.get("reply_to_message"):
            rm = m["reply_to_message"]
            ch = next((b["url"] for r in rm.get("reply_markup", {}).get("inline_keyboard", []) for b in r
                       if b.get("url", "").startswith("https://t.me/")), None)
            if ch:  # 채널에 이미 올라간 글의 사본 -> 채널 글 교체
                relink_channel(rm, int(ch.rsplit("/", 1)[1]), url.group(0))
            else:   # 아직 초안 -> 초안 버튼 교체(✅ 때 반영)
                fixed[rm["message_id"]] = relink(rm, url.group(0))
            continue
        lines = [l.strip().lstrip("🔥").strip() for l in m["text"].replace(url.group(0), "").split("\n")]
        lines = [l for l in lines if l and not l.startswith("이 포스팅은")]  # 붙여넣은 대가성 문구는 빼고 링크 기준으로 다시 붙임
        if not lines:
            tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": m["message_id"]},
               text="첫 줄에 제목을 같이 보내줘. 예)\n[G마켓] 상품명 (39,910원/무료)\n한 줄 코멘트\n링크")
            continue
        note, body = aff_note(url.group(0)), "\n".join(lines[1:])
        draft((f"<i>{note}</i>\n\n" if note else "") + f"🔥 <b>{esc(lines[0])}</b>" + (f"\n\n{esc(body)}" if body else ""),
              url.group(0))
    handled = set()
    for u in ups:
        q = u.get("callback_query") or {}
        m = q.get("message")
        if not m or str(q["from"]["id"]) != ADMIN or q.get("data") not in ("ok", "no") or m["message_id"] in handled:
            continue
        handled.add(m["message_id"])
        chat, mid = m["chat"]["id"], m["message_id"]
        if q["data"] == "ok":
            text, ents, rows = fixed.get(mid) or (m.get("text", ""), m.get("entities", []),
                                                  [r for r in m.get("reply_markup", {}).get("inline_keyboard", []) if "url" in r[0]])
            cp = tg("copyMessage", chat_id=CHANNEL, from_chat_id=chat, message_id=mid,  # 복사는 수정된 현재 내용 기준
                    reply_markup={"inline_keyboard": rows})
            if not cp:
                tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": mid},
                   text="⚠️ 채널 게시 실패: 봇이 채널 관리자인지, TG_CHANNEL 값이 맞는지 확인 후 ✅ 다시 눌러줘")
                continue  # 버튼 유지 -> 재시도 가능
            record(text, ents, rows[0][0]["url"] if rows else None, cp.get("message_id"))
        mark = "✅ 게시됨" if q["data"] == "ok" else "❌ 패스"
        tg("editMessageReplyMarkup", chat_id=chat, message_id=mid,
           reply_markup={"inline_keyboard": [[{"text": mark, "callback_data": "-"}]]})
    if ups:
        tg("getUpdates", offset=ups[-1]["update_id"] + 1)  # 처리한 입력 확인(삭제)


def goldbox(seen):
    kst = time.gmtime(time.time() + 9 * 3600)
    key = time.strftime("goldbox_%Y%m%d", kst)
    if not HAS_CP or key in seen or kst.tm_hour < 9:
        return
    items = coupang("GET", "/products/goldbox")[:40]
    picks = ai_pick(GOLD_PROMPT, [f"{x['productName']} | {int(x['productPrice']):,}원" for x in items])[:5]
    rows = [f"{n}. <a href=\"{esc(x['productUrl'])}\">{esc(x['productName'])}</a> — <b>{int(x['productPrice']):,}원</b>\n"
            f"   {esc(p['comment'])}" for n, p in enumerate(picks, 1) for x in [items[p["i"]]]]
    if rows and draft(f"<i>{DISCLOSURE}</i>\n\n⏰ <b>오늘의 쿠팡 골드박스 TOP{len(rows)}</b>\n\n" + "\n\n".join(rows)):
        seen[key] = time.time()


def digest(seen, posts):
    """매일 21시(KST) 이후 1회: 오늘 게시한 딜 모아보기 초안 -> ✅ 누르면 채널 게시. 블로그에 그대로 붙여넣어도 되는 형식."""
    kst = time.gmtime(time.time() + 9 * 3600)
    key, today = time.strftime("digest_%Y%m%d", kst), time.strftime("%Y-%m-%d", kst)
    todays = [p for p in posts if p["t"].startswith(today) and not p["text"].startswith("📋")]
    if key in seen or kst.tm_hour < 21 or not todays:
        return
    rows = [f"{n}. <a href=\"{esc(p['url'])}\">{esc(title_of(p['text']))}</a>" for n, p in enumerate(todays, 1)]
    text = (f"📋 <b>오늘의 딜 모아보기 ({kst.tm_mon}/{kst.tm_mday})</b>\n\n" + "\n".join(rows)
            + f"\n\n🔎 지난 딜 전체 보기: {SITE}\n📝 블로그: {BLOG}\n📲 실시간 알림: https://t.me/hotdeal_pick")
    if draft(text):
        seen[key] = time.time()
        tg("sendMessage", chat_id=ADMIN, text=blog_text(todays, kst), link_preview_options={"is_disabled": True})
        import cards
        try:  # Threads/인스타용 카드 -> docs/cards/ (워크플로가 커밋 -> 사이트에 공개 -> 다음 실행 때 threads()가 올림)
            cards.make([title_of(p["text"]) for p in todays], f"{kst.tm_mon}월 {kst.tm_mday}일", f"docs/cards/{today}.png")
        except Exception as e:
            print("card", repr(e))
        try:  # 인스타 릴스용 15초 영상 -> 관리자에게 바로 전송 (저장소엔 안 올림). 점수 높은 순 TOP3
            top = sorted(todays, key=lambda p: -p.get("s", 0))[:3]
            path = cards.reel([(title_of(p["text"]), comment_of(p["text"])) for p in top], f"{kst.tm_mon}월 {kst.tm_mday}일",
                              os.path.join(tempfile.gettempdir(), f"reel_{today}.mp4"))
            tg_video(path, (f"{kst.tm_mon}월 {kst.tm_mday}일 오늘의 핫딜 TOP{len(top)}\n\n"
                            + "\n".join(f"{n}. {title_of(p['text'])}" for n, p in enumerate(top, 1))
                            + "\n\n전체 딜·구매 링크는 프로필 링크(hotdealpick.kr)에서\n일부 링크는 제휴 링크로 수수료를 받을 수 있어요."
                            + "\n\n#핫딜 #오늘의핫딜 #특가 #최저가 #살림템 #쇼핑정보")[:1024])
        except Exception as e:
            print("reel", repr(e))


def blog_text(todays, kst):
    """네이버 블로그에 그대로 복붙할 제목+본문 (일반 텍스트, 링크 그대로 노출, 대가성 문구 포함)."""
    title = f"{kst.tm_mon}월 {kst.tm_mday}일 핫딜 모음 | {title_of(todays[0]['text'])}" + (f" 외 {len(todays) - 1}건" if len(todays) > 1 else "")
    items = []
    for n, p in enumerate(todays, 1):
        t, rest, _ = split_title(p["text"])
        items.append(f"{n}. {t}\n{rest.split(chr(10))[0]}\n👉 {p['url'] or SITE}")
    return (f"📝 블로그용 (제목·본문 그대로 복붙)\n\n제목: {title}\n\n" + "\n\n".join(items)
            + f"\n\n더 많은 핫딜 👉 {SITE}\n실시간 알림 👉 https://t.me/hotdeal_pick\n\n"
            + "이 포스팅은 쿠팡 파트너스·토스쇼핑 쉐어링크 등 제휴 마케팅 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받을 수 있습니다.")


THREADS = "https://graph.threads.com/v1.0"  # 공식 문서 기준 도메인


def threads(seen):
    """오늘 카드가 사이트에 올라와 있으면 관리자에게 인스타용으로 1회 보내고, THREADS_TOKEN 있으면 Threads에도 게시.
    토큰은 60일마다 만료 -> 실패하면 main()이 관리자에게 알림."""
    kst = time.gmtime(time.time() + 9 * 3600)
    today, key = time.strftime("%Y-%m-%d", kst), time.strftime("threads_%Y%m%d", kst)
    if key in seen or not os.path.exists(f"docs/cards/{today}.png"):
        return
    url = f"{SITE}cards/{today}.png"
    try:
        http(url, method="HEAD")  # 아직 배포 전(404)이면 다음 실행에 다시
    except Exception:
        return
    tok = E.get("THREADS_TOKEN")
    tg("sendPhoto", chat_id=ADMIN, photo=url, caption="📸 오늘의 카드 (인스타에 그대로 올리면 돼)" + (" · Threads는 자동 게시 중" if tok else ""))
    seen[key] = time.time()  # 사진은 1번만. Threads 실패는 아래서 관리자에게 알리고 재시도 안 함(스팸 방지)
    if not tok:
        return
    todays = [p for p in load(POSTS, []) if p["t"].startswith(today) and not p["text"].startswith("📋")]
    rows = [f"{n}. {title_of(p['text'])[:40]}" for n, p in enumerate(todays[:6], 1)]
    text = (f"📋 {kst.tm_mon}/{kst.tm_mday} 오늘의 핫딜 모음\n\n" + "\n".join(rows)
            + f"\n\n전체 딜·구매 링크 👉 {SITE}\n실시간 알림 👉 https://t.me/hotdeal_pick")[:480]
    me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
    q = urllib.parse.urlencode({"media_type": "IMAGE", "image_url": url, "text": text, "topic_tag": "핫딜", "access_token": tok})
    cid = json.loads(http(f"{THREADS}/{me}/threads?{q}", method="POST"))["id"]
    time.sleep(30)  # 미디어 처리 대기 (공식 권장값)
    json.loads(http(f"{THREADS}/{me}/threads_publish?creation_id={cid}&access_token={tok}", method="POST"))


def threads_deals(seen):
    """채널에 올라간 딜을 Threads에도 하나씩 (링크 = 사이트 딜 페이지: 구매 버튼·대가성 문구 있음).
    사이트 반영 전(404)이면 다음 실행에. posts.json에 th 표시 -> 두 번 안 올림. 3시간 지난 딜은 안 올림(식은 딜), 1회 최대 3개(도배 방지)."""
    tok, posts = E.get("THREADS_TOKEN"), load(POSTS, [])
    since = time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - 3 * 3600))
    todo = [i for i, p in enumerate(posts) if not p.get("th") and p["t"] >= since and not p["text"].startswith("📋")][:3]
    if not tok or not todo:
        return
    me = json.loads(http(f"{THREADS}/me?fields=id&access_token={tok}"))["id"]
    for i in todo:
        url = f"{SITE}p/{i}.html"
        try:
            http(url, method="HEAD")
        except Exception:
            return
        note = aff_note(posts[i].get("url") or "")
        text = (f"{note}\n\n" if note else "") + f"🔥 {title_of(posts[i]['text'])}\n\n{comment_of(posts[i]['text'])}"[:250] \
            + f"\n\n👉 {url}\n📲 실시간 알림 t.me/hotdeal_pick"  # Threads 500자 제한(이모지는 바이트로 셈)
        posts[i]["th"] = 1  # 먼저 표시: 실패해도 같은 딜 반복 시도 안 함(스팸 방지), 실패는 main()이 알림
        json.dump(posts, open(POSTS, "w"), ensure_ascii=False)
        q = urllib.parse.urlencode({"media_type": "TEXT", "text": text, "link_attachment": url, "topic_tag": "핫딜", "access_token": tok})
        cid = json.loads(http(f"{THREADS}/{me}/threads?{q}", method="POST"))["id"]
        time.sleep(10)
        json.loads(http(f"{THREADS}/{me}/threads_publish?creation_id={cid}&access_token={tok}", method="POST"))


def load(path, default):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return default


def main():
    seen = load(SEEN, {})
    publish_approved()
    new = [d for d in fetch_deals() if d["id"] not in seen and MIN_AGE <= d["age"] <= MAX_AGE]
    if new:
        picks = ai_pick(DEAL_PROMPT, [f"[{d['board']}] {d['title']} | {d['hits']} | {d['age']:.0f}분 전 | {d['desc']}"
                                      for d in new])
        for d in new:  # AI 판단 성공한 뒤에만 '본 글'로 기록 -> 실패 시 다음 실행에서 재시도
            seen[d["id"]] = time.time()
        print("점수", [(p["score"], new[p["i"]]["title"][:30]) for p in picks] or "5점 이상 없음")  # 컷 조절용 근거
        for p in [p for p in picks if p["score"] >= MIN_SCORE][:MAX_DRAFTS]:
            post_or_draft(new[p["i"]], p["comment"], p["score"], p.get("q"))
    for step in (goldbox, lambda s: digest(s, load(POSTS, [])), threads, threads_deals):
        try:
            step(seen)
        except Exception as e:
            print(step.__name__, repr(e))
            alert = time.strftime("th_alert_%Y%m%d", time.gmtime(time.time() + 9 * 3600))
            if step in (threads, threads_deals) and alert not in seen:  # 토큰 만료 등: 하루 1번만 알림
                seen[alert] = time.time()
                tg("sendMessage", chat_id=ADMIN, text=f"⚠️ Threads 게시 실패: {e!r}"[:300] + "\n토큰 만료(60일)면 THREADS_TOKEN 시크릿 재발급해줘")
    cutoff = time.time() - 3 * 86400
    json.dump({k: v for k, v in seen.items() if v > cutoff}, open(SEEN, "w"))
    print(f"new={len(new)} seen={len(seen)}")


if __name__ == "__main__":
    main()
