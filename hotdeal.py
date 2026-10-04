#!/usr/bin/env python3
"""핫딜봇: 뽐뿌 RSS -> Claude 선별/코멘트 -> 텔레그램 관리자 검수(✅/❌) -> 채널 게시.
쿠팡파트너스 키가 있으면 쿠팡 링크 자동 변환 + 매일 골드박스 TOP5 초안.
GitHub Actions에서 30분마다 실행. 외부 패키지 없음(파이썬 표준 라이브러리만)."""
import hashlib, hmac, html, json, os, re, time, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

E = {k: v.strip() for k, v in os.environ.items()}  # 시크릿 붙여넣을 때 섞인 공백·줄바꿈 제거
ADMIN, CHANNEL = E.get("TG_ADMIN_ID", ""), E.get("TG_CHANNEL", "")
MODEL = E.get("MODEL") or "claude-sonnet-5-5"
MIN_SCORE = int(E.get("MIN_SCORE") or 7)
HAS_CP = bool(E.get("COUPANG_ACCESS_KEY") and E.get("COUPANG_SECRET_KEY"))
MAX_DRAFTS = 5                 # 1회 실행당 검수 요청 최대 개수
MIN_AGE, MAX_AGE = 30, 360     # 분: 반응이 쌓인 뒤 판단, 너무 오래된 글은 무시
FEEDS = {"ppomppu": "뽐뿌"}  # 보드 추가: {"rss id": "표시명"}
SEEN = "seen.json"
CP_HOST, CP_BASE = "https://api-gateway.coupang.com", "/v2/providers/affiliate_open_api/apis/openapi/v1"
DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
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
    with urllib.request.urlopen(urllib.request.Request(url, body, h, method=method), timeout=30) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")


def tg(method, **params):
    """텔레그램 API. 실패해도 전체 실행은 멈추지 않고 None 반환."""
    try:
        return json.loads(http(f"https://api.telegram.org/bot{E['TG_TOKEN']}/{method}", params))["result"]
    except urllib.error.HTTPError as e:
        print("TG", method, e.code, e.read().decode()[:300])


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
        "model": MODEL, "max_tokens": 4000, "tools": [tool], "tool_choice": {"type": "tool", "name": "pick"},
        "messages": [{"role": "user", "content": prompt + "\n" + "\n".join(f"{i}. {l}" for i, l in enumerate(lines))}],
    }, {"x-api-key": E["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"}))
    picks = next(c["input"]["picks"] for c in r["content"] if c["type"] == "tool_use")
    return sorted((p for p in picks if 0 <= p["i"] < len(lines)), key=lambda p: -p["score"])


def store_link(post_url):
    """뽐뿌 글 상단의 실제 쇼핑몰 링크."""
    try:
        m = re.search(r'topTitle-link.*?<a [^>]*>\s*(https?://[^<\s]+)', http(post_url), re.S)
        return html.unescape(m.group(1)) if m else None
    except Exception as e:
        print("link", post_url, repr(e))


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


def draft(text, buy_url=None, score=None):
    """관리자에게 검수용 초안 전송. ✅ 누르면 다음 실행 때 채널에 그대로 복사됨."""
    kb = [[{"text": "🛒 구매하러 가기", "url": buy_url}]] if buy_url else []
    kb.append([{"text": f"✅ 게시 ({score}점)" if score else "✅ 게시", "callback_data": "ok"},
               {"text": "❌ 패스", "callback_data": "no"}])
    return tg("sendMessage", chat_id=ADMIN, text=text, parse_mode="HTML",
              link_preview_options={"is_disabled": True}, reply_markup={"inline_keyboard": kb})


def deal_post(d, comment):
    link, aff = affiliate(store_link(d["url"]))
    head = f"<i>{DISCLOSURE}</i>\n\n" if aff else ""  # 공정위·쿠팡 규정: 대가성 문구는 첫 부분에
    text = f"{head}🔥 <b>{esc(d['title'])}</b>\n\n{esc(comment)}\n\n출처: <a href=\"{esc(d['url'])}\">{d['board']}</a>"
    return text, link or d["url"]


def publish_approved():
    """관리자가 누른 ✅/❌ 처리. 텔레그램이 버튼 입력을 24시간 보관하므로 30분 주기로 충분."""
    ups = tg("getUpdates", allowed_updates=["callback_query"]) or []
    handled = set()
    for u in ups:
        q = u.get("callback_query") or {}
        m = q.get("message")
        if not m or str(q["from"]["id"]) != ADMIN or q.get("data") not in ("ok", "no") or m["message_id"] in handled:
            continue
        handled.add(m["message_id"])
        chat, mid = m["chat"]["id"], m["message_id"]
        if q["data"] == "ok":
            rows = [r for r in m.get("reply_markup", {}).get("inline_keyboard", []) if "url" in r[0]]
            if not tg("copyMessage", chat_id=CHANNEL, from_chat_id=chat, message_id=mid,
                      reply_markup={"inline_keyboard": rows}):
                tg("sendMessage", chat_id=ADMIN, reply_parameters={"message_id": mid},
                   text="⚠️ 채널 게시 실패: 봇이 채널 관리자인지, TG_CHANNEL 값이 맞는지 확인 후 ✅ 다시 눌러줘")
                continue  # 버튼 유지 -> 재시도 가능
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


def main():
    try:
        seen = json.load(open(SEEN))
    except (OSError, ValueError):
        seen = {}
    publish_approved()
    new = [d for d in fetch_deals() if d["id"] not in seen and MIN_AGE <= d["age"] <= MAX_AGE]
    if new:
        picks = ai_pick(DEAL_PROMPT, [f"[{d['board']}] {d['title']} | {d['hits']} | {d['age']:.0f}분 전 | {d['desc']}"
                                      for d in new])
        for d in new:  # AI 판단 성공한 뒤에만 '본 글'로 기록 -> 실패 시 다음 실행에서 재시도
            seen[d["id"]] = time.time()
        for p in [p for p in picks if p["score"] >= MIN_SCORE][:MAX_DRAFTS]:
            draft(*deal_post(new[p["i"]], p["comment"]), score=p["score"])
    try:
        goldbox(seen)
    except Exception as e:
        print("goldbox", repr(e))
    cutoff = time.time() - 3 * 86400
    json.dump({k: v for k, v in seen.items() if v > cutoff}, open(SEEN, "w"))
    print(f"new={len(new)} seen={len(seen)}")


if __name__ == "__main__":
    main()
