#!/usr/bin/env python3
"""핫딜봇: 뽐뿌 RSS -> Claude 선별/코멘트 -> 텔레그램 관리자 검수(✅/❌) -> 채널 게시.
쿠팡파트너스 키가 있으면 쿠팡 링크 자동 변환 + 매일 골드박스 TOP5 초안.
GitHub Actions에서 30분마다 실행. 외부 패키지 없음(파이썬 표준 라이브러리만)."""
import base64, hashlib, hmac, html, json, os, re, time, urllib.error, urllib.parse, urllib.request
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
AFF_HOSTS = ("click.linkprice.com", "lpweb.kr", "linkmoa.kr", "lase.kr", "bestmore.net", "newtip.net", "s.click.aliexpress.com")  # 쿠팡(link.coupang.com) 외 제휴 링크 도메인
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
esc = html.escape

DEAL_PROMPT = """너는 한국 핫딜 텔레그램 채널 편집자야. 아래 딜 중 구독자가 실제로 살 만한 것만 골라 pick 도구로 반환해.
점수(1~10) 기준: 가격 매력, 생필품/대중성, 커뮤니티 반응(조회 대비 추천·댓글). 비추천이 많거나 품절·종료·가격오류 언급이 있으면 제외.
comment: 구독자용 1~2줄. 핵심 조건(쿠폰·카드할인·무배 등)을 사실대로. 과장 금지, 확인 안 된 '역대최저' 금지, 건강식품 효능 언급 금지, 이모지 최대 1개.
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
            "properties": {"i": {"type": "integer"}, "score": {"type": "integer"}, "comment": {"type": "string"}}}}}}}
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
    tag = re.match(r"\s*\[([^\]]+)\]", title)
    tag = tag.group(1).lower().replace(" ", "") if tag else ""
    return next((v for k, v in STORES.items() if k in tag), "💸 제휴 없는 쇼핑몰 · 수수료 0")


def draft(text, buy_url=None, score=None, info=None):
    """관리자에게 검수용 초안 전송. ✅ 누르면 다음 실행 때 채널에 그대로 복사됨.
    info: 관리자만 보는 안내 버튼(채널엔 링크 버튼만 복사되므로 안 나감)."""
    kb = [[{"text": "🛒 구매하러 가기", "url": buy_url}]] if buy_url else []
    kb.append([{"text": f"✅ 게시 ({score}점)" if score else "✅ 게시", "callback_data": "ok"},
               {"text": "❌ 패스", "callback_data": "no"}])
    if info:
        kb.append([{"text": info, "callback_data": "-"}])
    return tg("sendMessage", chat_id=ADMIN, text=text, parse_mode="HTML",
              link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": kb})


def deal_post(d, comment):
    link, aff = affiliate(store_link(d["url"]))
    head = f"<i>{DISCLOSURE}</i>\n\n" if aff else ""  # 공정위·쿠팡 규정: 대가성 문구는 첫 부분에
    text = f"{head}🔥 <b>{esc(d['title'])}</b>\n\n{esc(comment)}\n\n출처: <a href=\"{esc(d['url'])}\">{d['board']}</a>"
    return text, link or d["url"]


def aff_note(url):
    """제휴 링크면 그 프로그램의 대가성 문구, 일반 쇼핑몰 주소면 ''."""
    host = urllib.parse.urlsplit(url).netloc
    return DISCLOSURE if host == "link.coupang.com" else TOSS_NOTE if host in TOSS_HOSTS else AFF_NOTE if host in AFF_HOSTS else ""


def relink(m, url):
    """초안 m의 구매 버튼을 url로 교체(제휴 링크면 대가성 문구를 맨 앞에) -> (text, entities, 버튼 rows)."""
    text, ents = m.get("text", ""), m.get("entities", [])
    note = aff_note(url)
    if note and not text.startswith("이 포스팅은"):
        n = len(note.encode("utf-16-le")) // 2  # 텔레그램 오프셋은 UTF-16 단위
        text = f"{note}\n\n{text}"
        ents = [{"type": "italic", "offset": 0, "length": n}] + [{**e, "offset": e["offset"] + n + 2} for e in ents]
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
            fixed[m["reply_to_message"]["message_id"]] = relink(m["reply_to_message"], url.group(0))
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
            if not tg("copyMessage", chat_id=CHANNEL, from_chat_id=chat, message_id=mid,  # 복사는 수정된 현재 내용 기준
                      reply_markup={"inline_keyboard": rows}):
                tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": mid},
                   text="⚠️ 채널 게시 실패: 봇이 채널 관리자인지, TG_CHANNEL 값이 맞는지 확인 후 ✅ 다시 눌러줘")
                continue  # 버튼 유지 -> 재시도 가능
            posts = load(POSTS, [])
            posts.append({"t": time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600)), "text": text,
                          "entities": ents, "url": rows[0][0]["url"] if rows else None})
            json.dump(posts, open(POSTS, "w"), ensure_ascii=False)
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
        try:  # Threads/인스타용 카드 -> docs/cards/ (워크플로가 커밋 -> 사이트에 공개 -> 다음 실행 때 threads()가 올림)
            import cards
            cards.make([title_of(p["text"]) for p in todays], f"{kst.tm_mon}월 {kst.tm_mday}일", f"docs/cards/{today}.png")
        except Exception as e:
            print("card", repr(e))


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


THREADS = "https://graph.threads.net/v1.0"


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
        for p in [p for p in picks if p["score"] >= MIN_SCORE][:MAX_DRAFTS]:
            draft(*deal_post(new[p["i"]], p["comment"]), score=p["score"], info=store_info(new[p["i"]]["title"]))
    for step in (goldbox, lambda s: digest(s, load(POSTS, [])), threads):
        try:
            step(seen)
        except Exception as e:
            print(step.__name__, repr(e))
            if step is threads:
                tg("sendMessage", chat_id=ADMIN, text=f"⚠️ Threads 게시 실패: {e!r}"[:300] + "\n토큰 만료(60일)면 THREADS_TOKEN 시크릿 재발급해줘")
    cutoff = time.time() - 3 * 86400
    json.dump({k: v for k, v in seen.items() if v > cutoff}, open(SEEN, "w"))
    print(f"new={len(new)} seen={len(seen)}")


if __name__ == "__main__":
    main()
