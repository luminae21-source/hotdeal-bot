#!/usr/bin/env python3
"""posts.json(채널에 게시된 딜) -> docs/ 정적 사이트. GitHub Pages로 서빙. 외부 패키지 없음."""
import calendar, hashlib, html, json, os, re, time, urllib.parse

BASE = "https://hotdealpick.kr/"
GC_CODE = "hotdealpick"  # GoatCounter 사이트 코드(10/11 진우 결정 '측정 붙이기' — 10/23 진우 가입, hotdealpick.goatcounter.com). 비어 있으면 측정 X · 진우 본인 방문 빼기 = hotdealpick.kr/#toggle-goatcounter
GC_JS = ("document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a[rel~=\"nofollow\"]');"  # 구매 링크(바깥 몰) 클릭 = 이벤트 buy/몰 주소
         "if(!a||!window.goatcounter||!goatcounter.count)return;var h;try{h=new URL(a.href).hostname}catch(x){return}"
         "goatcounter.count({path:'buy/'+h,title:(a.getAttribute('aria-label')||a.textContent||'').trim().slice(0,80),event:true})});")


GC_APP = ("window.goatcounter={referrer:function(r){return /[?&]src=app(&|$)/.test(location.search)||matchMedia('(display-mode: standalone)').matches&&!document.referrer?'app':r},"
          "path:function(p){return p.replace(/([?&])src=app(&|$)/,function(m,a,b){return b?a:''})}};")  # 웹앱(start_url ?src=app·홈 화면에서 연 첫 화면) = 출처 'app', 경로는 ?src 빼고 같은 쪽


def gc_tag():
    """GoatCounter(무료·쿠키 없음): 방문 + 구매 링크 클릭(이벤트 'buy/몰 주소'). 채널 구분은 글 속 사이트 링크의 ?ref=th·tg·ig(GoatCounter가 출처로 셈), 웹앱 = 'app'(GC_APP)."""
    return f'<script>{GC_APP}</script><script data-goatcounter="https://{GC_CODE}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script><script>{GC_JS}</script>' if GC_CODE else ""
CHANNEL = "https://t.me/hotdeal_pick"
BLOG = "https://blog.naver.com/hotdeal_pick"
INSTA = "https://www.instagram.com/hotdealpick.kr/"
THREADS = "https://www.threads.com/@hotdealpick.kr"
GOLDBOX = "https://link.coupang.com/a/hBMtMDCxFY"  # 쿠팡 파트너스 간편 링크: 골드박스 페이지(coupang.com/np/goldbox), 10/6 생성. 클릭 후 24시간 안 쿠팡 구매가 실적
CHANNEL_WEB = "https://t.me/s/hotdeal_pick"  # 텔레그램 채널 웹 보기(앱 없이 열림)
TITLE = "핫딜픽"  # 브랜드 이름 (텔레그램·블로그·스레드·인스타·페이스북 모두 핫딜픽, 10/5 통일)
DISCLOSURE = "이 사이트는 쿠팡 파트너스·토스쇼핑 쉐어링크·네이버 쇼핑 커넥트·올리브영 쇼핑 큐레이터 등 제휴 마케팅 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받을 수 있습니다."
CSS = """*{box-sizing:border-box}[hidden]{display:none!important}body{margin:0;font:16px/1.55 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;background:#f4f5f7;color:#191f28;-webkit-font-smoothing:antialiased;word-break:keep-all;overflow-wrap:anywhere}
a{color:#1b64da}main{max-width:680px;margin:0 auto;padding:calc(12px + env(safe-area-inset-top)) calc(16px + env(safe-area-inset-right)) 16px calc(16px + env(safe-area-inset-left))}header{position:relative;padding:8px 0 0}header h1{margin:0;font-size:21px;font-weight:800;letter-spacing:-.3px}header h1 a{color:inherit;text-decoration:none}
.sub{color:#6b7684;font-size:13px;margin-top:1px}.lk{position:absolute;right:0;top:6px;display:flex;align-items:center;gap:4px;min-height:40px;padding:0 14px;border-radius:20px;background:#fff;border:1px solid #e8eaee;color:#e42939;text-decoration:none;font-weight:700;font-size:14px}.lk svg{width:18px;height:18px}
.dis{font-size:11px;line-height:1.5;color:#8b95a1;margin:8px 0}footer{font-size:12px;color:#8b95a1;text-align:center;padding:24px 0}
.gb{display:flex;align-items:center;justify-content:center;min-height:44px;padding:6px 12px;margin:6px 0 2px;border-radius:12px;background:#fff4e6;color:#c2410c;border:1px solid #ffd8a8;text-decoration:none;font-weight:700;font-size:15px}
.card{background:#fff;border-radius:16px;padding:18px 16px;margin:12px 0;border:1px solid #eef0f3;box-shadow:0 1px 2px rgba(25,31,40,.05)}.card h2{margin:0 0 8px;font-size:17px;line-height:1.4}.card h2 a{color:inherit;text-decoration:none}.t{color:#8b95a1;font-size:12px}
.btn{display:flex;align-items:center;justify-content:center;min-height:50px;padding:10px 12px;margin-top:12px;border-radius:12px;background:#1b64da;color:#fff;text-decoration:none;font-weight:700;font-size:16px;text-align:center}
.btn2{display:flex;align-items:center;justify-content:center;min-height:46px;padding:8px 12px;margin-top:8px;border-radius:12px;border:1.5px solid #1b64da;color:#1b64da;text-decoration:none;font-weight:700;text-align:center}
.top2{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:6px 0 2px}.top2 a{margin:0;min-height:46px;font-size:14px;padding:6px 8px;text-align:center}.tg2{display:flex;align-items:center;justify-content:center;border-radius:12px;background:#229ed9;color:#fff;text-decoration:none;font-weight:700}
.tg{display:flex;align-items:center;justify-content:center;min-height:50px;padding:10px;margin:16px 0;border-radius:12px;background:#229ed9;color:#fff;text-decoration:none;font-weight:700;text-align:center}
.pick{display:flex;align-items:center;gap:12px;min-height:56px;padding:12px 14px;margin:8px 0;border-radius:14px;background:#fff;border:1px solid #eef0f3;color:#191f28;text-decoration:none;font-weight:600}.alt{display:block;margin:-4px 0 8px 56px;font-size:15px;padding:12px 0}.pick b{color:#e8590c;font-size:20px;min-width:30px}.pick span{flex:1;line-height:1.35}.pick em{font-style:normal;color:#c2410c;font-size:14px;white-space:nowrap}#today details{margin-top:10px}#today summary{cursor:pointer;min-height:44px;padding:10px 0;font-weight:700;color:#4e5968}
a:focus-visible,button:focus-visible,input:focus-visible{outline:3px solid #1b64da;outline-offset:2px}
.bar{position:fixed;left:0;right:0;bottom:0;z-index:9;display:flex;flex-wrap:wrap;justify-content:center;gap:2px;background:rgba(255,255,255,.94);-webkit-backdrop-filter:saturate(180%) blur(12px);backdrop-filter:saturate(180%) blur(12px);border-top:1px solid #e8eaee;padding:6px calc(6px + env(safe-area-inset-right)) calc(6px + env(safe-area-inset-bottom)) calc(6px + env(safe-area-inset-left))}.bar a{flex:1 1 0;min-width:0;max-width:88px;white-space:nowrap;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;min-height:52px;border-radius:12px;color:#6b7684;text-decoration:none;font-size:12px;font-weight:600}.bar svg{width:22px;height:22px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.bar a[aria-current=true]{color:#1b64da;background:#e8f1fd}main:has(.bar){padding-bottom:calc(84px + env(safe-area-inset-bottom))}
.bar.top{display:none}.inapp .bar:not(.top){display:none}.inapp main,.inapp main:has(.bar){padding-bottom:calc(96px + env(safe-area-inset-bottom))}.k-hot{--c:#e03131}.k-toss{--c:#1b64da}.k-coupang{--c:#c2410c}.k-naver{--c:#087f5b}.k-life{--c:#0b7d3e}.k-cats{--c:#0b7d3e}.k-wait{--c:#b45309}.k-fire{--c:#e03131}.inapp .day{scroll-margin-top:130px}.mo{margin-top:10px}.mo summary{cursor:pointer;min-height:44px;padding:10px 0;font-weight:700;color:#4e5968}@media(prefers-color-scheme:dark){.mo summary{color:#a1a1aa}}.k-beauty{--c:#d6336c}.k-days{--c:#4e5968}.k-today{--c:#f59f00;--t:#191f28}.k-brand{--c:#7048e8}.bar i{display:flex;color:var(--c)}.inapp form.find,.inapp .bar.top{box-shadow:0 8px 10px -10px rgba(25,31,40,.35)}.inapp .bar.top{display:flex;position:sticky;top:env(safe-area-inset-top);z-index:8;flex-wrap:wrap;justify-content:center;gap:6px;padding:8px 0 4px;background:#f4f5f7;border:0;-webkit-backdrop-filter:none;backdrop-filter:none;scrollbar-width:none}.inapp .bar.top::-webkit-scrollbar{display:none}.inapp .bar.top a{flex:0 0 calc((100% - 24px)/5);max-width:none;flex-direction:column;min-height:52px;padding:5px 0 4px;gap:3px;border-radius:14px;background:#fff;border:1px solid #e1e4e8;color:#333d4b;font-size:14px;font-weight:700}.inapp .bar.top i{width:22px;height:22px;border-radius:11px;background:var(--c);color:#fff;align-items:center;justify-content:center}.inapp .bar.top svg{width:13px;height:13px;stroke-width:2.4}.inapp .bar.top a[aria-current=true]{background:var(--c);border-color:var(--c);color:var(--t,#fff)}.inapp .bar.top a[aria-current=true] i{background:rgba(255,255,255,.28);color:var(--t,#fff)}
.more{background:#eef4ff;border-radius:16px;padding:14px;margin:18px 0 0}.more h2{font-size:17px;font-weight:800;margin:0 2px 10px}.more div{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.more .k-days{grid-column:1/-1}.more a{display:flex;align-items:center;justify-content:center;gap:6px;min-height:52px;padding:0 4px;border-radius:12px;background:#fff;box-shadow:0 1px 2px rgba(25,31,40,.06);color:#191f28;text-decoration:none;font-size:15px;font-weight:700;min-width:0}.more i{flex:none;display:flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:14px;background:var(--c);color:#fff}.more svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
.day h2{font-size:18px;font-weight:800;letter-spacing:-.3px;margin:22px 2px 2px}.day>.t{margin:0 2px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:10px}
.g{position:relative;display:flex;flex-direction:column;background:#fff;border-radius:16px;padding:12px;border:1px solid #eef0f3;box-shadow:0 1px 2px rgba(25,31,40,.04);min-width:0}.g .s{min-height:22px;padding:2px 30px 0 0;font-size:12px;color:#8b95a1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.like{position:absolute;top:4px;right:2px;width:40px;height:40px;display:flex;align-items:center;justify-content:center;padding:0;border:0;border-radius:20px;background:none;color:#b0b8c1;cursor:pointer}.like svg,.lk svg{fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.like svg{width:20px;height:20px}.like[aria-pressed=true]{color:#e42939}.like[aria-pressed=true] svg,.lk svg{fill:currentColor}
.g h3{margin:4px 0 6px;font-size:15px;line-height:1.4;font-weight:600;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}.g h3 a{color:inherit;text-decoration:none}
.g .pr{font-weight:800;font-size:18px;letter-spacing:-.3px;line-height:1.3}.sv{color:#e42939;font-size:13px;font-weight:700;line-height:1.45}.g .u{font-size:12px;color:#6b7684}.g .rx{font-size:12px;color:#8b95a1}
.g .go{margin-top:auto;padding-top:10px}.g .go a{display:flex;align-items:center;justify-content:center;min-height:44px;border-radius:10px;background:#1b64da;color:#fff;text-decoration:none;font-weight:700;font-size:15px}.g .go a.o{background:#f2f4f6;color:#333d4b}.g .go a.f{min-height:40px;font-size:13px;background:none;color:#6b7684;font-weight:600}
.find{background:#f4f5f7;padding:8px 0 4px}form.find{position:sticky;top:env(safe-area-inset-top);z-index:8}.find input{width:100%;min-height:46px;border:1px solid #e1e4e8;border-radius:12px;padding:0 14px;font:inherit;font-size:16px;background:#fff;color:inherit}.chips{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;padding:8px 0 2px}.chips::-webkit-scrollbar{display:none}.chips button{min-height:36px;padding:0 4px;white-space:nowrap;border-radius:18px;border:1px solid #e1e4e8;background:#fff;color:#333d4b;font:inherit;font-size:14px;font-weight:600;cursor:pointer}.chips button[aria-pressed=true]{background:#191f28;border-color:#191f28;color:#fff}#qn{margin:6px 2px 0}
.bd{display:flex;flex-wrap:wrap;gap:4px;margin:2px 0 4px}.bd b{font-size:11px;font-weight:700;padding:2px 7px;border-radius:6px;line-height:1.5}.b1{background:#e7f6ec;color:#15803d}.b2{background:#fdecec;color:#c62828}.b3{background:#f2f4f6;color:#6b7684}.b4{background:#fff4e6;color:#d9480f}
.deal .s{font-size:13px;color:#8b95a1}.deal h2{font-size:20px;letter-spacing:-.3px;margin:4px 0 12px}.hero{display:flex;align-items:baseline;flex-wrap:wrap;gap:2px 8px}.hero .pr{font-size:30px;font-weight:800;letter-spacing:-.6px;line-height:1.2}.ship{font-size:13px;color:#6b7684}.hero .sv{font-size:15px}.deal .u{font-size:14px;color:#6b7684;margin-top:2px}
.deal .btn{min-height:56px;font-size:18px;margin-top:16px}.deal .note{font-size:12px;color:#8b95a1;text-align:center;margin:8px 0 0}.why{font-size:14px;color:#6b7684;font-weight:700;margin:18px 0 6px;padding-top:16px;border-top:1px solid #f2f4f6}.deal p{margin:0;font-size:15px;line-height:1.65;color:#333d4b}
@media(prefers-color-scheme:dark){body{background:#101012;color:#ececf0}.card,.g,.pick,.lk{background:#1c1c1f;border-color:#2b2b30;box-shadow:none}.pick{color:#ececf0}.sub,.t,.dis,footer,.g .s,.deal .s,.deal .note,.g .rx{color:#8e8e96}a{color:#6ea8ff}.gb{background:#2a1f17;border-color:#7c2d12;color:#fdba74}.pick em{color:#fdba74}
.bar{background:rgba(28,28,31,.94);border-color:#2b2b30}.bar a{color:#a1a1aa}.bar a[aria-current=true]{color:#6ea8ff;background:#1f2a3a}.inapp .bar.top{background:#101012}.inapp .bar.top a,.more a{background:#1c1c1f;border-color:#2b2b30;color:#ececf0}.inapp .bar.top a[aria-current=true]{background:var(--c);border-color:var(--c);color:var(--t,#fff)}.inapp form.find,.inapp .bar.top{box-shadow:0 8px 10px -10px rgba(0,0,0,.8)}.more{background:#15233a}.more a{box-shadow:none}.bar .k-toss i{color:#6ea8ff}.bar .k-days i{color:#a1a1aa}.bar .k-brand i{color:#9775fa}.inapp .bar.top i{color:#fff}.like{color:#71717a}.btn,.g .go a{background:#2b6fd6;color:#fff}.btn2{border-color:#6ea8ff;color:#6ea8ff}.find{background:#101012}.find input,.chips button{background:#1c1c1f;border-color:#2b2b30;color:#ececf0}.chips button[aria-pressed=true]{background:#ececf0;border-color:#ececf0;color:#101012}
.b1{background:#12301c;color:#86efac}.b2{background:#3a1616;color:#fca5a5}.b3{background:#2b2b30;color:#a1a1aa}.b4{background:#2a1f17;color:#fdba74}.g .go a.o{background:#2b2b30;color:#ececf0}.g .go a.f{background:none;color:#a1a1aa}.sv{color:#ff6b78}.g .u,.deal .u,.ship,.why{color:#a1a1aa}.why{border-color:#2b2b30}.deal p{color:#d4d4d8}}
.rec h3{font-size:16px;margin:18px 2px 2px}.stat{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0}.stat div{background:#fff;border:1px solid #eef0f3;border-radius:14px;padding:12px;font-size:12px;color:#6b7684}.stat b{display:block;font-size:20px;font-weight:800;color:#191f28;letter-spacing:-.3px}
.tw{overflow-x:auto;margin:14px 0 8px;background:#fff;border:1px solid #eef0f3;border-radius:14px}.tw table{width:100%;border-collapse:collapse;font-size:13px}.tw th,.tw td{padding:9px 6px;border-bottom:1px solid #f2f4f6;text-align:left;vertical-align:top}.tw th{color:#6b7684;font-weight:600;white-space:nowrap}.tw td:nth-child(-n+2),.tw td:nth-child(n+4){white-space:nowrap}.tw tr.min td{background:#fff9db}
.recs{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0 4px}.recs h3{width:100%;margin:4px 2px 2px;font-size:15px}.recs a{display:flex;align-items:center;min-height:40px;padding:0 12px;border-radius:20px;background:#fff;border:1px solid #e1e4e8;text-decoration:none;font-size:14px;color:#333d4b}
@media(prefers-color-scheme:dark){.stat div,.tw,.recs a{background:#1c1c1f;border-color:#2b2b30;color:#ececf0}.stat b{color:#ececf0}.tw th,.tw td{border-color:#2b2b30}.tw tr.min td{background:#2a2614}}
.inst{display:flex;align-items:center;gap:4px;margin:8px 0 0;padding:2px 0 2px 12px;min-height:48px;border-radius:12px;background:#fff;border:1px solid #e1e4e8;font-size:13px;line-height:1.35}.inst span{flex:1;min-width:0}.inst button{min-height:44px;border:0;border-radius:10px;font:inherit;font-weight:700;cursor:pointer;white-space:nowrap}#instb{background:#e03131;color:#fff;padding:0 12px;font-size:14px}#instx{min-width:44px;background:none;color:#6b7684;font-size:16px}@media(prefers-color-scheme:dark){.inst{background:#1c1c1f;border-color:#2b2b30}}
@media(max-width:419px){.bar a{flex:0 0 calc((100% - 8px)/5);min-height:46px}main:has(.bar){padding-bottom:calc(124px + env(safe-area-inset-bottom))}.chips button,.inapp .bar.top a{font-size:13px}}@media(max-width:359px){.chips button,.inapp .bar.top a{font-size:12px}}"""


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


NOTE_STARTS = ("이 포스팅은", "이 콘텐츠는", "[광고]")  # 대가성 문구 줄 시작(쿠팡·링크프라이스·네이버 = 이 포스팅은, 토스 = 이 콘텐츠는)
MALL_HEAD = re.compile(r"(💙 토스 특가|🚀 쿠팡(?: 로켓)?|📦 쿠팡)(?: · [^\n]*)? ([🔥🛒👍])$")  # 👍 = 꾸준템(10/22 20:0x 진우) · 10/22 진우 '토스·쿠팡 한눈에': 몰별 개별 글 머리 줄 -> 다음 줄 상품명, 그다음 줄 가격
MALL_TAG = {"💙 토스 특가": "토스", "🚀 쿠팡 로켓": "쿠팡", "🚀 쿠팡": "쿠팡", "📦 쿠팡": "쿠팡"}  # 로켓 근거 없는 쿠팡 딜 = '📦 쿠팡'(10/22 진우 '사실 아닌 표기 X' · 10/23 🚀 -> 📦, 그 전 글 '🚀 쿠팡'도 읽음)


def mall_title(lines, i):
    """lines[i]가 몰별 머리 줄이면 '[몰] 상품명 (가격)'(예전 제목 모양 — 사이트·카드·리스트가 그대로 읽게), 아니면 None.
    가격 = 셋째 줄 금액(' → 1개 …'·' (60%↓)' 앞) + 나머지 ' · ' 조각(쿠폰가·회원가 등, ⭐ 평점 X) + 배송 조각(' · 무료' -> '/무료', 카드 배송 칸) = 예전 제목 가격 그대로."""
    m = MALL_HEAD.fullmatch(lines[i])
    if not m or len(lines) < i + 3 or not lines[i + 1].strip():
        return None
    seg = [s.strip() for s in lines[i + 2].split(" · ")]
    ship = next((s for s in seg[1:] if re.search(r"무료|무배|배송", s) and not s.startswith("⭐")), "")
    price = " · ".join([re.split(r" → | \(\d+%↓\)", seg[0])[0].strip()] + [s for s in seg[1:] if s and s != ship and not s.startswith("⭐") and not re.match(r"(?:한 달|리뷰) ", s)]) + (f"/{ship}" if ship else "")
    return f"[{MALL_TAG[m[1]]}] {lines[i + 1].strip()}" + (f" ({price})" if price else "")


def steady_st(text):
    """👍 꾸준템 가격 줄의 '한 달 N명+ 구매 · 리뷰 N' — 제목(mall_title)엔 안 넣으니 딜 페이지·설명에 따로(10/22 리뷰)."""
    m = re.search(r"^(?:🚀|📦) 쿠팡[^\n]* 👍\n[^\n]*\n([^\n]*)", text, re.M)
    return " · ".join(s.strip() for s in m[1].split(" · ") if re.match(r"(?:한 달|리뷰) ", s.strip())) if m else ""


def split_title(text):
    """(제목, 제목 아래 본문, 잘라낸 UTF-16 길이). 본문에 제목이 한 번 더 나오지 않게 제목 줄까지 잘라냄.
    몰별 글(💙 토스 특가 · … / 🚀 쿠팡 로켓 · …)은 머리·상품명·가격 세 줄 = 제목 '[몰] 상품명 (가격)'."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        t = re.sub(r"^[^\w가-ퟣ\[]+", "", line).strip()  # 앞 이모지 제거
        if t and not t.startswith(NOTE_STARTS):  # 대가성 문구 줄(쿠팡·토스·기타 제휴)은 제목이 아님
            mt = mall_title(lines, i)
            t, i = (mt, i + 2) if mt else (t, i)
            rest = "\n".join(lines[i + 1:]).lstrip("\n")
            return t, rest, (len(text.encode("utf-16-le")) - len(rest.encode("utf-16-le"))) // 2
    return TITLE, text, 0


def title_of(text):
    return split_title(text)[0]


def page(title, body, desc="", canonical="", gb=True, note="", top=""):
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{html.escape(title)}</title><meta name="description" content="{html.escape(desc[:150])}">
{"".join(f'<meta name="naver-site-verification" content="{v}">' for v in NAVER_VERIFY)}{f'<meta name="google-site-verification" content="{html.escape(GOOGLE_VERIFY)}">' if GOOGLE_VERIFY else ""}
<meta property="og:title" content="{html.escape(title)}"><meta property="og:description" content="{html.escape(desc[:150])}"><meta property="og:type" content="website">
{f'<meta property="og:url" content="{canonical}"><link rel="canonical" href="{canonical}">' if canonical else ''}<link rel="alternate" type="application/rss+xml" title="{TITLE}" href="{BASE}rss.xml">{PWA_HEAD}<style>{CSS}</style>{INAPP_JS}{gc_tag()}</head><body><main>
<header><h1><a href="{BASE}">🔥 {TITLE}</a></h1><a class="lk" href="{BASE}#saved" aria-label="찜한 딜 보기"><svg viewBox="0 0 24 24" aria-hidden="true">{ICONS["saved"]}</svg>찜<b id="lc"></b></a><div class="sub">매일 살 만한 핫딜만 골라드려요</div></header>{top}
<p class="dis">{html.escape(note) + "<br>" if note else ""}{DISCLOSURE}</p>{GB_LINK if gb else ""}{body}
<a class="tg" href="{CHANNEL}">📲 텔레그램에서 실시간으로 받기</a>
<footer>딜 정보는 게시 시점 기준이며 가격·재고는 변동될 수 있어요.<br><a href="{BLOG}">네이버 블로그</a> · <a href="{INSTA}">인스타그램</a> · <a href="{THREADS}">Threads</a> · <a href="{CHANNEL}">텔레그램</a></footer></main></body></html>"""


PWA_BG, PWA_DARK = "#f4f5f7", "#101012"  # 사이트 바탕(CSS body·다크) = 앱 실행 화면·상단 줄 색
IV, SV = "?v=2", "?v=1"  # 앱 아이콘(IV)·바로가기 아이콘(SV, sc-*) 그림 바꾸면 올림(cards.app_icons) -> 주소가 바뀌어 폰·크롬·서비스워커가 새 파일로 받음 · 2 = 10/23 'A 레드'
MANIFEST = {"id": "/", "name": "핫딜픽 — 매일 살 만한 핫딜", "short_name": "핫딜픽", "description": "매일 살 만한 핫딜만 골라드려요", "lang": "ko", "dir": "ltr",  # 10/23 진우 '웹앱으로'(앱스토어 X)
            "start_url": "/?src=app", "scope": "/", "display": "standalone", "background_color": PWA_BG, "theme_color": PWA_BG, "categories": ["shopping"],
            "icons": [{"src": f"/icons/icon-192.png{IV}", "sizes": "192x192", "type": "image/png", "purpose": "any"}, {"src": f"/icons/icon-512.png{IV}", "sizes": "512x512", "type": "image/png", "purpose": "any"},
                      {"src": f"/icons/icon-512-maskable.png{IV}", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}],
            "shortcuts": [{"name": n, "short_name": n[2:], "url": f"/#{k}", "icons": [{"src": f"/icons/sc-{k}-96.png{SV}", "sizes": "96x96", "type": "image/png", "purpose": "any"},
                                                                             {"src": f"/icons/sc-{k}.png{SV}", "sizes": "192x192", "type": "image/png", "purpose": "any"}]}
                          for n, k in (("🔥 지금 특가", "fire"), ("⏳ 특가 대기", "wait"), ("🧻 생필품", "life"))]}  # 바로가기 아이콘 = cards.SC_ICONS(10/24 진우 'V1 파스텔 이모지')
PWA_HEAD = (f'<link rel="manifest" href="/manifest.webmanifest"><link rel="icon" href="/favicon.ico{IV}" sizes="any"><link rel="icon" type="image/png" sizes="32x32" href="/icons/favicon-32.png{IV}">'
            f'<link rel="icon" type="image/png" sizes="16x16" href="/icons/favicon-16.png{IV}"><link rel="apple-touch-icon" href="/icons/apple-touch-icon.png{IV}">'
            f'<meta name="theme-color" content="{PWA_BG}" media="(prefers-color-scheme: light)"><meta name="theme-color" content="{PWA_DARK}" media="(prefers-color-scheme: dark)">'
            '<meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="핫딜픽">'
            '<meta name="apple-mobile-web-app-status-bar-style" content="default">'
            "<script>if('serviceWorker'in navigator)addEventListener('load',function(){if(!document.documentElement.classList.contains('inapp'))navigator.serviceWorker.register('/sw.js').catch(function(){})})</script>")  # 앱 안 브라우저는 설치 X -> 미리 받기(약 150KB)도 X
SW_JS = r"""var V='hdp-%s',PRE=['/','/icons/icon-192.png{IV}','/icons/icon-512.png{IV}','/icons/apple-touch-icon.png{IV}','/favicon.ico{IV}'];
self.addEventListener('install',function(e){e.waitUntil(caches.open(V).then(function(c){return c.addAll(PRE)}).then(function(){return self.skipWaiting()}))});
self.addEventListener('activate',function(e){e.waitUntil(caches.keys().then(function(ks){return Promise.all(ks.filter(function(k){return k!==V}).map(function(k){return caches.delete(k)}))}).then(function(){return self.clients.claim()}))});
self.addEventListener('fetch',function(e){var r=e.request,u=new URL(r.url);
if(r.method!=='GET'||u.origin!==location.origin)return;
if(/^\/icons\/|^\/favicon\.ico$|\.(css|woff2?|otf|ttf)$/.test(u.pathname)){e.respondWith(caches.match(r).then(function(c){return c||fetch(r).then(function(res){if(res.ok){var x=res.clone();caches.open(V).then(function(k){k.put(r,x)})}return res})}));return}
e.respondWith(fetch(r).then(function(res){if(res.ok&&r.mode==='navigate'){var x=res.clone();caches.open(V).then(function(k){k.put(r,x)})}return res}).catch(function(){return caches.match(r).then(function(c){return c||(r.mode==='navigate'?caches.match('/'):Response.error())})}))});
""".replace("{IV}", IV)  # 웹앱 서비스워커(최소): 같은 출처 GET만 — 쿠팡·토스·네이버·제휴 리다이렉트·GoatCounter는 안 건드림 · 아이콘·폰트·CSS = 캐시 먼저 · HTML·딜 데이터 = 네트워크 먼저(옛 가격 X, 오프라인일 때만 저장해 둔 쪽) · V = 배포(홈 내용)마다 바뀜 -> 옛 캐시 지움
INSTALL = ('<div class="inst" id="inst" hidden><span id="instt"></span><button type="button" id="instb">📲 앱으로 설치</button><button type="button" id="instx" aria-label="닫기">✕</button></div>'
           "<script>(function(){var b=document.getElementById('inst'),t=document.getElementById('instt'),ok=document.getElementById('instb'),ev=null,ua=navigator.userAgent,ios=/iPhone|iPad|iPod/.test(ua)||/Macintosh/.test(ua)&&navigator.maxTouchPoints>1;"
           "if(matchMedia('(display-mode: standalone)').matches||navigator.standalone)return;try{if(Date.now()-(+localStorage.getItem('instx')||0)<6048e5)return}catch(e){}"
           "function show(m,btn){t.innerHTML=m;ok.hidden=!btn;b.hidden=false}"
           "document.getElementById('instx').onclick=function(){b.hidden=true;try{localStorage.setItem('instx',Date.now())}catch(e){}};"
           "if(document.documentElement.classList.contains('inapp')||/Telegram|; wv\\)/.test(ua)||ios&&!/Safari\\//.test(ua))return show('📲 크롬·사파리에서 열면 앱으로 설치할 수 있어요',0);"
           "if(ios)return show('📲 앱으로 설치: <b>공유</b>(⬆︎ · 안 보이면 <b>···</b> 안)<br>→ <b>홈 화면에 추가</b>',0);"
           "addEventListener('beforeinstallprompt',function(e){e.preventDefault();ev=e;show('홈 화면에서 바로 열기',1)});"
           "ok.onclick=function(){if(!ev)return;ev.prompt();ev.userChoice.then(function(){ev=null;b.hidden=true})};addEventListener('appinstalled',function(){b.hidden=true})})()</script>")  # 홈 맨 위 작게: 안드로이드 크롬 = 바로 설치, 아이폰·아이패드 = 2줄 안내(공유 위치는 브라우저마다 달라 안 씀), 앱 안 브라우저(.inapp·텔레그램·안드로이드 WebView·사파리 아닌 iOS 앱) = 브라우저 안내만, 설치됨 = 숨김, 닫으면 7일 X
INAPP_JS = "<script>if(/Barcelona|Instagram|FBAN|FBAV|KAKAOTALK|NAVER\\(inapp|Line\\/|DaumApps/i.test(navigator.userAgent))document.documentElement.classList.add('inapp')</script>"  # 10/13 진우: 앱 안 브라우저(Threads=Barcelona·인스타·페북·카톡·네이버 등)는 아래 고정 바가 앱 툴바에 가려서 -> 검색창 아래 한 줄 메뉴 + 아래 여백
GB_LINK = (f'<div class="top2"><a class="gb" href="{GOLDBOX}" rel="nofollow sponsored noopener" target="_blank">⏰ 쿠팡 골드박스</a>'  # 골드박스 + 텔레그램 한 줄(10/11 진우 '검색창+골드박스+텔레그램을 위에')
           f'<a class="tg2" href="{CHANNEL}">📲 텔레그램 알림받기</a></div>')
TOSS_HOSTS = ("toss.im", "toss.shopping")  # 쉐어링크 단축(toss.shopping/_m/.. — API·앱 발급 모두 이 모양, toss.im/_m/..)·원본(toss.shopping/t/..?k=)
NAVER_HOSTS = ("naver.me",)  # 쇼핑커넥트 '링크 발급' 주소 (naver.me 단축)
OY_HOSTS = ("oy.run",)  # 올리브영 쇼핑 큐레이터 링크(10/10 진우 가입, 앱에서 발급)
AFF_HOSTS = ("click.linkprice.com", "lpweb.kr", "linkmoa.kr", "lase.kr", "bestmore.net", "newtip.net", "s.click.aliexpress.com")  # 쿠팡(link.coupang.com) 외 제휴 링크 도메인


def parse(title):
    """'[롯데온] 삼양 파스타 32봉 (14,490원/무료)' -> ('롯데온', '삼양 파스타 32봉', '14,490원/무료')"""
    store = re.match(r"\s*\[(.+?)\]", title)
    prices = re.findall(r"\(([^()]*원[^()]*)\)", title)  # 괄호 안에 '원' 들어간 마지막 묶음 = 가격
    name = title[store.end():] if store else title
    if prices:
        name = name.replace(f"({prices[-1]})", " ")
    elif tail := re.search(r"\s*/\s*(\d[\d,]*\s*원.*)$", name):  # 루리웹식 '…1개/ 9,730원' 꼬리(10/8 카드 03번에 가격이 제목에 붙어 나옴)
        prices, name = [tail.group(1)], name[:tail.start()]
    return (store.group(1) if store else "", re.sub(r"\s+", " ", name).strip() or title, prices[-1] if prices else "")


SAVE_STORES = r"쿠팡|네이버|G마켓|지마켓|11번가|이마트|롯데온|올리브영|오늘의집|컬리|토스"


OTHER_STORES = r"쿠팡|네이버|G마켓|지마켓|11번가|이마트|롯데온|올리브영|오늘의집|컬리|다이소|옥션|위메프|티몬"  # 토스 딜 글에서 빼는 다른 몰 이름(10/12 토스 비즈니스 '타 쇼핑몰과의 가격 비교 없이')


CMP_WORDS = r"보다|대비|차이|같은 상품|더 싸|더 쌈|비싸|최저가는"  # 다른 몰 비교 말


def strip_cmp(text, ents=()):
    """토스 딜 글에서 다른 쇼핑몰 가격 비교를 뺀 (text, entities): 다른 몰 이름 + 비교 말(보다·대비·차이·같은 상품 등)이 든 줄을 지움 — '🤔 솔직히 특가로는 약한 제품 — …'·'💡 단위가격: … — …'는
    ' — ' 앞만 남기고, '[광고] …' 첫 줄은 훅만 뺌. entities(텔레그램 UTF-16 오프셋)는 지운 만큼 당기고 바뀐 줄 안의 것은 뺌."""
    u = lambda s: len(s.encode("utf-16-le")) // 2
    out, spans, pos, lines = [], [], 0, text.split("\n")
    heads = [i for i in range(len(lines)) if mall_title(lines, i)]
    keep = {i + k for i in heads for k in (1, 2)}  # 몰별 글 상품명·가격 줄 = 제목(상품명에 몰 이름이 있어도 그대로)
    for i, line in enumerate(lines):
        new = line
        if i in heads:  # 머리 줄 '· …' 칸에 다른 몰(예 '쿠팡 판매 1위')이면 칸만 뺌(머리 줄은 남겨야 제목이 읽힘)
            m = MALL_HEAD.fullmatch(line)
            new = f"{m[1]} {m[2]}" if re.search(OTHER_STORES, line) else line
        elif i in keep:
            pass
        elif line.startswith("[광고]") and re.search(OTHER_STORES, line) and re.search(CMP_WORDS, line):
            new = re.sub(rf"\s*—\s*({OTHER_STORES})보다 [\d,]+원 쌈", "", re.sub(rf"💸 ({OTHER_STORES})보다 [\d,]+원 (싼 |쌈 · )", "🔥 ", line))
        elif re.search(OTHER_STORES, line) and not re.match(r"(?:🔥|🛒) (?:<b>)?\[|출처:|\[광고\]", line) and not line.startswith(NOTE_STARTS):  # 10/13 진우 '토스 글 전부 다른 몰 이름·가격 비교 없이'(제목·고지문·출처 줄은 그대로)
            m = re.match(r"((?:💡|🤔|⚠️|👉|💰)\s*(?:[가-힣 ]{1,8}:\s*)?)(.*)$", line)
            if m and not line.startswith("💡 참고"):  # 💡·🤔·⚠️ 줄 = ' — '·' · ' 조각 중 다른 몰 이름이 든 조각과 비교만 남는 조각(절반·비교·차이 등)을 빼고, 남는 게 없으면 줄째
                tok = re.split(r"( — | · )", m[2])
                kept = [(tok[i - 1] if i else "", tok[i]) for i in range(0, len(tok), 2) if tok[i].strip() and not re.search(OTHER_STORES, tok[i]) and not re.search(CMP_WORDS + "|절반|비교", tok[i])]
                new = m[1] + kept[0][1] + "".join(sep + p for sep, p in kept[1:]) if kept else None
            else:  # '💡 참고: 쿠팡 …'·다른 몰 이름이 든 다른 줄 = 줄째
                new = None
        if new != line:
            spans.append((pos, u(line) + 1, 0 if new is None else u(new) + 1))
        if new is not None:
            out.append(new)
        pos += u(line) + 1
    if not spans:
        return text, list(ents or [])
    res = []
    for e in ents or []:
        o = e["offset"]
        if any(s <= o < s + old for s, old, _ in spans):
            continue
        res.append({**e, "offset": o - sum(old - new for s, old, new in spans if s + old <= o)})
    return "\n".join(out), res


def saving(text):
    """글의 비교 문장 -> ('쿠팡', '7,210원'): '쿠팡 같은 상품(18,200원)보다 7,210원 쌈'(진우 링크 글·Claude 코멘트). 없으면 None (10/11 진우 '얼마나 싼지')."""
    m = re.search(rf"({SAVE_STORES})[^\n—]*?보다\s*([\d,]+원)\s*쌈", text)
    return m and (m.group(1), m.group(2))


def unit_of(p):
    """단위가격: Claude가 매긴 unit, 없으면 글의 '💡 단위가격: 10매당 31원 — …' 줄 앞부분."""
    m = re.search(r"💡 단위가격:?\s*([^—\n]+)", p["text"])
    return p.get("unit") or (m.group(1).strip() if m else "")


def buy_label(title):
    """구매 버튼에 가격(10/10 진우 'UI 편하게' → 가격·구매 먼저): '[쿠팡] 휴지 (9,900원/무료)' -> '🛒 9,900원 구매하기'. 가격 모르면 예전 문구."""
    m = re.search(r"\d[\d,]*\s*원", parse(title)[2])
    return f"🛒 {m.group(0).replace(' ', '')} 구매하기" if m else "🛒 구매하러 가기"


def toss_share(url):
    """토스 쉐어링크(수수료)인지: 단축(/_m/) 또는 원본(/t/번호?k=). k= 없는 상품 주소(/t/번호)는 아님 — 발급 실패로 사본용으로 남은 주소(10/9 확인)."""
    p = urllib.parse.urlsplit(url or "")
    return p.netloc in TOSS_HOSTS and (p.path.startswith("/_m/") or "k" in urllib.parse.parse_qs(p.query))


def aff(url):
    """제휴(수수료) 링크인지: 쿠팡 파트너스·토스 쉐어링크·네이버 쇼핑커넥트·링크프라이스 등."""
    host = urllib.parse.urlsplit(url or "").netloc
    return host in CP_SHORT or toss_share(url) or host in NAVER_HOSTS + AFF_HOSTS + OY_HOSTS


CARD_N = 5  # 카드 한 장에 들어가는 딜 수 = 인스타 캡션·사이트 맨 위 번호 수(10/11 — 카드 5·캡션 6·사이트 6으로 어긋나던 것)
STEM = re.compile(r"(\d{4}-\d{2}-\d{2})(?:_(\d{2}))?")  # 카드 이름: 하루 카드 = 날짜, 시간대 카드(10/11~ · 10/23 11·13·15·17·19시) = 날짜_시(두 자리)
SLOT_NAMES = {"11": "오전 11시", "13": "낮 1시", "15": "오후 3시", "17": "오후 5시", "19": "저녁 7시", "12": "낮 12시", "18": "저녁 6시"}  # 시간대 카드 이름(hotdeal.IG_SLOTS와 같은 시각 + 10/23 전 칸 이름)


def day_deals(posts, day):
    """그날 딜의 카드 순서 [(posts 번호, 글)]: 점수 높은 순, 같은 점수면 제휴 링크 딜 먼저(10/8 진우 '쿠팡·토스 잘 팔리게'), 그다음 게시 순.
    카드·인스타 캡션·사이트 맨 위 카드 딜(앞 CARD_N개)·릴스(앞 3개) 번호가 모두 이 순서."""
    ds = [(i, p) for i, p in enumerate(posts) if p["t"].startswith(day) and not p["text"].startswith("📋")]
    return sorted(ds, key=lambda x: (-x[1].get("s", 0), not aff(x[1].get("url")), x[1]["t"]))


def card_order(posts, stem, out="docs"):
    """카드 번호 순서: 카드를 만들 때 정해 둔 순서(docs/cards/카드이름.json = posts 번호 목록)가 있으면 그대로 — 카드가 나간 뒤 딜이 더 올라오거나
    점수가 바뀌어도 인스타 카드·캡션과 사이트 번호가 안 어긋남. 없으면 하루 카드는 day_deals, 시간대 카드는 없음."""
    f = f"{out}/cards/{stem}.json"
    if os.path.exists(f):
        return [(i, posts[i]) for i in json.load(open(f)) if i < len(posts)]
    return day_deals(posts, stem) if len(stem) == 10 else []


def card_stems(out):
    """사이트 맨 위 카드: 인스타에 올리는 카드(docs/cards/ig.json — 컨테이너 만든 실행에 기록, 다음 실행에 발행 -> 사이트가 먼저) + 하루 카드(.png — 인스타 없이도 Threads·봇 채팅용)
    -> 가장 최근 카드부터 24시간 안 카드들, 시각 순(하루 카드 = 21시). 만들기만 하고 인스타에 안 올리는 시간대 카드는 안 보임(인스타 번호와 어긋나지 않게)."""
    d = f"{out}/cards"
    if not os.path.isdir(d):
        return []
    live = list(json.load(open(f"{d}/ig.json"))) if os.path.exists(f"{d}/ig.json") else []
    daily = [f[:-4] for f in os.listdir(d) if f.endswith(".png") and re.fullmatch(r"\d{4}-\d{2}-\d{2}", f[:-4])]
    at = lambda x: calendar.timegm(time.strptime(x[:10], "%Y-%m-%d")) + 3600 * int(STEM.fullmatch(x).group(2) or 21)
    stems = sorted({x for x in live + daily if STEM.fullmatch(x)}, key=at)
    return [x for x in stems if at(stems[-1]) - at(x) < 86400]  # 가장 최근 카드부터 24시간 안 카드(어제 저녁·밤 카드도 다음 날 낮까지 접어서 — 늦게 본 사람도 같은 번호)

COMMUNITY = ("ppomppu.co.kr", "ruliweb.com", "clien.net")  # 구매 버튼이 커뮤니티 원글인 딜(상품 주소를 못 꺼냄) -> 원글이 지워지면 안 열림(10/8 01번)


def community(url):
    return urllib.parse.urlsplit(url or "").netloc.endswith(COMMUNITY)


def find_url(title):
    """원글이 지워져도 살 길: 네이버쇼핑 검색('[몰]'·가격 괄호·'/ 가격' 꼬리 뺀 상품명)."""
    q = " ".join(re.sub(r"\[[^\]]*\]|\([^()]*\)|/\s*\d[\d,]*\s*원.*$", " ", title).split())
    return "https://search.shopping.naver.com/search/all?query=" + urllib.parse.quote(q[:60])


def card_name(stem):
    """사이트 맨 위 카드 칸 이름 '10월 12일 낮 12시 카드 딜' / 하루 카드 '10월 12일 카드 딜' — 인스타·Threads 캡션이 이 이름 그대로 가리킴."""
    return f"{int(stem[5:7])}월 {int(stem[8:10])}일 " + (SLOT_NAMES.get(stem[11:], stem[11:] + "시") + " " if len(stem) > 10 else "") + "카드 딜"


def card_picks(posts, out):
    """홈 맨 위: 가장 최근 인스타·Threads 카드의 딜을 카드와 같은 번호로, 누르면 바로 구매 페이지(인스타 캡션 링크는 안 눌려서 프로필 링크 -> 여기서 한 번에, 10/8 진우).
    인스타 하루 3번(10/11~): 가장 최근 카드는 펼치고, 24시간 안 앞선 카드(어제 밤·오늘 낮 12시 등)는 접어서 — 앞 게시물을 보고 온 사람도 같은 번호로."""
    stems = card_stems(out)
    blocks = [(x, card_order(posts, x, out)[:CARD_N]) for x in reversed(stems)]  # 카드·캡션에 나온 CARD_N개만(나머지는 아래 격자) — 스크롤 짧게
    blocks = [(x, ps) for x, ps in blocks if ps]
    if not blocks:
        return ""
    name = card_name
    first = f'<div class="t">번호를 누르면 바로 구매 페이지로 가요 · 인스타·Threads 카드 번호와 같아요</div>{pick_rows(blocks[0][1])}'
    more = "".join(f'<details><summary>{html.escape(name(x))}</summary>{pick_rows(ps)}</details>' for x, ps in blocks[1:])
    return f'<section class="card" id="today" aria-labelledby="today-h"><h2 id="today-h">📸 {name(blocks[0][0])}</h2>{first}{more}</section>'


def pick_rows(picks):
    """카드 딜 번호 버튼들(누르면 구매 주소 바로, 원글 딜은 같은 상품 찾기도)."""
    return "".join(f'<a class="pick" href="{html.escape(f"{BASE}p/{i}.html" if urllib.parse.urlsplit(p.get("url") or "").netloc in OY_HOSTS else p.get("url") or f"{BASE}p/{i}.html")}" rel="nofollow sponsored noopener" target="_blank" '
                   f'aria-label="{n}번 {html.escape(title_of(p["text"]))} {"원글에서 구매 링크 보기" if community(p.get("url")) else "구매하러 가기"}">'
                   f'<b>{n:02d}</b><span>{html.escape(title_of(p["text"]))}</span><em>{"원글 →" if community(p.get("url")) else "구매 →"}</em></a>'
                   + (f'<a class="alt" href="{html.escape(find_url(title_of(p["text"])))}" rel="nofollow noopener" target="_blank">🔎 {n}번 원글이 안 열리면 같은 상품 찾기</a>'
                      if community(p.get("url")) else "")
                   for n, (i, p) in enumerate(picks, 1))


def react(p):
    """반응 수치 글자(게시 때 뽐뿌·클리앙 수치, 10/9~): '분당 조회 13.5회 · 추천 1'. 10/9 이 표시 배포 전 글은 합친 값(pop)만 있어서 '반응 18.5'."""
    if p.get("vpm") is not None:
        return f"분당 조회 {p['vpm']:g}회" + (f" · 추천 {p['rec']}" if p.get("rec") else "")
    return f"반응 {p['pop']:g}" if p.get("pop") else ""


BRAND = r"설화수|더\s?후|헤라|라네즈|아이오페|이니스프리|에스티\s?로더|랑콤|키엘|SK-?II|디올|샤넬|조말론|라로슈포제|아벤느|피지오겔|세타필|닥터지|다이슨|필립스|브라운|나이키|아디다스"  # 이름 있는 브랜드(10/10 진우 '브랜딩 파워 있는 제품도 꼭')
FOOD = r"쌀|라면|햇반|생수|샘물|우유|계란|달걀|구운란|특란|삼겹|목살|한우|갈비|닭|족발|감귤|사과|망고|바나나|단감|반시|양파|과일|김치|만두|떡|커피|콜드브루|음료|(?<!워싱)(?<!과탄산)소다|주스|과자|초코|견과|새우|오징어|감자탕|소스|올리브(?!영)|파운드"


def badges(p):
    """카드 배지(10/10 진우 'UI 편하게'): 🏆 인기(커뮤니티 반응, 10/11 몰·시각 줄에서 옮김 — 좁은 칸에서 시각이 잘려서) · 본사 정품(예약 글 tag) · 오늘 밤 12시 마감(토스 선착순특가, 오늘 올린 글만) · 약한 딜."""
    today = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600))
    return ([("b4", "🏆 인기")] if p.get("hot") else []) + ([("b1", "✅ 본사 정품")] if p.get("tag") == "정품" else []) + ([("b2", "⏰ 오늘 밤 12시 마감")] if "밤 12시까지" in p["text"] and p["t"][:10] == today else []) \
        + ([("b3", "🛒 약한 딜")] if "특가로는 약한 제품" in p["text"] else [])


def end_at(p):
    """토스 선착순특가 마감 = 올린 날 밤 12시(KST) -> epoch 초 (배지가 '마감까지 1시간 25분'으로 줄어듦, END_JS)."""
    return calendar.timegm(time.strptime(p["t"][:10], "%Y-%m-%d")) + 86400 - 9 * 3600


def badge_html(p, skip=()):
    return "".join(f'<b class="{c}"' + (f' data-end="{end_at(p)}"' if c == "b2" else "") + f">{t}</b>" for c, t in badges(p) if c not in skip)


END_JS = """<script>(function(){function f(){var n=Date.now()/1000;[].forEach.call(document.querySelectorAll('[data-end]'),function(b){var s=b.dataset.end-n,h=Math.floor(s/3600),m=Math.floor(s%3600/60);
b.textContent=s<=0?'⏰ 마감됐어요':s<60?'⏰ 곧 마감':'⏰ 마감까지 '+(h?h+'시간 ':'')+m+'분'})}f();setInterval(f,30000)})()</script>"""


def keys(p):
    """검색 칩 필터용 키(data-k): 몰(쿠팡·토스) · 생필품·식품·화장품 · 브랜드 · 마감."""
    title = title_of(p["text"])
    return " ".join([{"toss": "토스", "coupang": "쿠팡", "naver": "네이버"}[k] for k in [shop_of(p)] if k] + [n.split()[-1] for _, n, rx in CATS if re.search(rx, title)]
                    + (["식품"] if re.search(FOOD, title) else []) + (["브랜드"] if p.get("tag") == "정품" or re.search(BRAND, title) else [])
                    + (["마감"] if any(c == "b2" for c, _ in badges(p)) else []))


def price_won(title):
    """제목 가격(원): '(1,950원 · 5천원 쿠폰가)' -> 1950, '(10,000/무료)' -> 10000, 못 읽으면 None."""
    m = re.search(r"(\d[\d,]*)\s*원", parse(title)[2]) or re.search(r"\((\d{1,3}(?:,\d{3})+)\s*/", title)
    return m and int(m[1].replace(",", ""))


def conds(p):
    """검색 칩 '조건' 키(10/15 진우 '중복 메뉴니까 다른 메뉴' — 몰·품목은 탭으로): 1만원 이하 · 30일 최저가 · 1+1·증정 · 무료배송 (제목·본문 그대로)."""
    title, w = title_of(p["text"]), price_won(title_of(p["text"]))
    return " ".join(k for k, ok in (("1만원", w is not None and w <= 10000), ("최저가", re.search(r"30일\s*(?:내\s*)?최저가", p["text"])),
                                    ("증정", re.search(r"\d\s*\+\s*\d|증정|사은품", title)), ("무배", re.search("무료|무배", title))) if ok)


def grid_item(i, p, rx=False, old=False, sh=None):
    """격자 칸 1개: 몰·이름(3줄까지)·가격·단위가격·(rx면 반응 수치)·버튼(제휴·쇼핑몰 = 구매, 원글 = 원글 + 같은 상품 찾기, 주소 없음 = 자세히).
    sh = 진열 상태(shelf: 단계, 가격, 가격 아래 줄, 배지) — 가격 None = 올린 때 가격, '' = 가격 숨김(토스 특가 끝남), 'N원' = 마지막 확인 가격.
    old = 3일 지난 진우 상품이고 확인 기록 없음 -> 'M/D 가격 · 지금 가격은 링크에서 확인'(옛 가격이 지금 가격처럼 안 보이게)."""
    title = title_of(p["text"])
    store, name, price = parse(title)
    _, now, note, bds, _ = sh or (0, None, "", [], False)
    shown = price.split("/")[0].strip() if now is None else now
    page_url, url = f"{BASE}p/{i}.html", p.get("url")
    if community(url):
        go = (f'<a class="o" href="{html.escape(url)}" rel="nofollow noopener" target="_blank" aria-label="{html.escape(name)} 원글에서 구매 링크 보기">원글 →</a>'
              f'<a class="f" href="{html.escape(find_url(title))}" rel="nofollow noopener" target="_blank" aria-label="{html.escape(name)} 같은 상품 찾기">🔎 같은 상품 찾기</a>')
    elif url:
        go = f'<a href="{html.escape(url)}" rel="nofollow sponsored noopener" target="_blank" aria-label="{html.escape(name)} 구매하러 가기">구매 →</a>'
    else:
        go = f'<a class="o" href="{page_url}" aria-label="{html.escape(name)} 자세히 보기">자세히 →</a>'
    bd = badge_html(p, ("b4",) if rx else ()) + "".join(f'<b class="{c}">{html.escape(t)}</b>' for c, t in bds)  # '반응 좋은 딜' 칸에선 🏆 배지가 겹쳐서 뺌
    sv, u = (saving(p["text"]), unit_of(p)) if now is None else (None, "")  # 올린 때 가격 기준 줄은 그 가격을 보일 때만
    return (f'<article class="g" data-k="{html.escape(" ".join(filter(None, (keys(p), conds(p)))))}"><button class="like" type="button" data-i="{i}" aria-pressed="false" aria-label="{html.escape(name)} 찜"><svg viewBox="0 0 24 24" aria-hidden="true">{ICONS["saved"]}</svg></button><div class="s">{html.escape(store) or "핫딜"} · {p["t"][11:16]}</div>'
            + (f'<div class="bd">{bd}</div>' if bd else "") + f'<h3><a href="{page_url}">{html.escape(name)}</a></h3>' + (f'<div class="pr">{html.escape(shown)}</div>' if shown else "")
            + (f'<div class="u">{html.escape(note)}</div>' if note else f'<div class="u">{int(p["t"][5:7])}/{int(p["t"][8:10])} 가격 · 지금 가격은 링크에서 확인</div>' if old else "")
            + (f'<div class="sv">{sv[0]}보다 {sv[1]}↓</div>' if sv else "") + (f'<div class="u">{html.escape(u)}</div>' if u else "")
            + (f'<div class="rx">👀 {html.escape(react(p).replace("분당 조회 ", "분당 "))}</div>' if rx and react(p) else "") + f'<div class="go">{go}</div></article>')


DAY_ONLY = r"하루\s*특가|선착순|밤 12시까지"  # 토스 하루특가·선착순특가 = 올린 날 밤 12시 마감
EVENTS = "events.json"
CP_LINKS = "cp_links.json"  # {쿠팡 상품 주소: 파트너스 링크} — 봇이 딥링크 API로 만듦(쿠팡 키 있을 때만 생김, 10/23 hotdeal.cp_links). events 그 주소 대신 씀
CP_PROD = r"https://(?:www\.|m\.)?coupang\.com/vp/products/(\d+)"  # 쿠팡 상품 주소(번호 = pid). 진우 단축 링크(link.coupang.com)는 그대로
CP_SHORT = ("link.coupang.com", "coupa.ng")  # 쿠팡 파트너스 링크 도메인(딥링크 API 단축 주소 = coupa.ng일 수도 — 공식 샘플)


def ev_list(path=None):
    """events.json(Cowork 예약) 그대로 — 쿠팡 상품 주소만 cp_links.json의 파트너스 링크로(pid 없으면 주소의 상품 번호). 깨진 파일 = []."""
    path = path or EVENTS
    try:
        evs = json.load(open(path)) if os.path.exists(path) else []
    except ValueError:
        evs = []
    try:
        cl = json.load(open(CP_LINKS)) if os.path.exists(CP_LINKS) else {}
    except ValueError:
        cl = {}
    for e in evs if isinstance(evs, list) and isinstance(cl, dict) else []:
        if isinstance(e, dict) and isinstance(e.get("url"), str) and isinstance(cl.get(e["url"]), str) and (m := re.match(CP_PROD, e["url"])):
            e.setdefault("pid", m[1])
            e["url"] = cl[e["url"]]
    return evs


def ev_info():
    """events.json 진우 항목 -> {url: {now, chk, end, why, target, pid, item}}(같은 url 여러 항목이면 뒤 항목이 덮음, 글자 칸만). 깨진 파일 = {}(사이트 빌드가 멈추면 그 실행의 기록·커밋이 안 남음)."""
    evs, out = ev_list(), {}
    for e in evs if isinstance(evs, list) else []:
        if isinstance(e, dict) and isinstance(e.get("url"), str):
            out.setdefault(e["url"], {}).update({k: e[k] for k in ("now", "chk", "end", "why", "target", "pid", "item") if isinstance(e.get(k), str)})
    return out


def md_h(chk):
    """'YYYY-MM-DD HH:MM' -> 'M/D H시'(못 읽으면 그대로)."""
    m = re.match(r"\d{4}-(\d\d)-(\d\d) (\d\d)", chk)
    return f"{int(m[1])}/{int(m[2])} {int(m[3])}시" if m else chk


def icon_of(text):
    """글 아이콘: 몰별 틀 머리 줄 끝(🔥·🛒·👍) 또는 예전 틀 제목 줄 앞('🔥 [몰] …'), 없으면 ''."""
    for l in text.split("\n"):
        if m := MALL_HEAD.fullmatch(l):
            return m[2]
        if m := re.match(r"([🔥🛒👍]) \[", l):
            return m[1]
    return ""


REHOT_DAYS = 3  # 🔁 다시 특가 배지 기간(⏳ -> 🔥 된 날부터)


def shelf(p, ev, today):
    """진열 상태(10/23 진우 '진열 = 기본 유지' · '지금 특가가 아닌 제품은 특가를 기다릴 제품으로 알려주고, 나중에 특가가 되면 다시 특가 제품으로'):
    -> (단계 0 🔥 특가 중 · 1 ⏳ 특가 대기 중 👍 꾸준템 · 2 ⏳ 특가 대기 · 3 일시 품절, 가격(None = 올린 때 · '' = 숨김 · 'N원' = 마지막 확인), 가격 아래 줄, 배지들, 🔁 다시 특가?)
    / None = 목록에서 뺌(진우 상품만 — 글 st gone: 토스 조회 안 됨 서로 다른 날 3번 · events end + why gone/issue).
    진우 상품 상태는 hotdeal.own_end가 글에 씀(st·tgt·now·chk·stdy·rehot) — 아직 안 본 글은 아이콘대로(🔥 = 특가 중, 토스 하루특가·선착순 날 지남·🛒·👍 = 대기).
    토스 지금 가격은 사이트에 안 씀(API 신청 범위 — 10/23 Cowork 정정): 토스 카드 = 올린 가격 + 'M/D 가격 · 지금 가격은 링크에서 확인', 대기면 가격 숨기고 '특가 때 M원 · 특가 기다리는 중'.
    쿠팡·네이버 = events now·chk(Cowork 확인 가격)로 '지금 N원 (M/D H시 확인)'. 커뮤니티 딜 = 🔥면 0 아니면 2(표시 그대로)."""
    ic = icon_of(p["text"])
    if not p.get("own"):
        return (0 if ic == "🔥" else 2), None, "", [], False
    toss = shop_of(p) == "toss" and toss_share(p.get("url"))
    st = p.get("st") or ("hot" if ic == "🔥" and not (toss and re.search(DAY_ONLY, p["text"]) and p["t"][:10] < today) else "wait")
    e = ev.get(p.get("url"), {})
    if st == "gone" or e.get("end", "") >= p["t"][:10] and e.get("why", "gone") in ("gone", "issue"):  # events end는 봇이 st로 옮기기 전에도 바로
        return None
    tgt, now, chk = p.get("tgt", ""), p.get("now", ""), p.get("chk", "")
    since = time.strftime("%Y-%m-%d", time.gmtime(calendar.timegm(time.strptime(today, "%Y-%m-%d")) - (REHOT_DAYS - 1) * 86400))
    rehot = st == "hot" and p.get("rehot", "") >= since
    bd = [("b2", "🔁 다시 특가")] * rehot + [("b1", "👍 꾸준템")] * bool(p.get("stdy") and st == "wait")
    md = f"{int(p['t'][5:7])}/{int(p['t'][8:10])}"
    if st == "out":
        return 3, None, f"{md} 가격 · 다시 들어오면 링크에서 확인", bd + [("b3", f"일시 품절 ({chk.split()[0] if chk else md} 확인)")], False
    if st == "hot":
        return 0, now or None, (f"지금 가격 ({chk} 확인)" if chk else "지금 가격") if now else "", bd, rehot
    wait = f"특가 때 {tgt} · 특가 기다리는 중" if tgt else f"{md} 가격 · 특가 기다리는 중"  # 목표가 없으면 올린 가격을 날짜와 같이(지금 가격처럼 안 보이게)
    return (1 if p.get("stdy") else 2), (now or ("" if tgt else None)), (f"지금 가격{f' ({chk} 확인)' if chk else ''} · {wait}" if now else f"{wait} · 지금 가격은 링크에서 확인"), bd + [("b3", "⏳ 특가 대기")], False


def home_pool(posts, days):
    """홈 몰·품목·브랜드 칸에 둘 딜 -> {posts 번호: shelf 상태}(10/23 진우 '우리가 업로드한 제품들을 리스트에서 그냥 빼지 않기' · '진열 = 기본 유지'):
    커뮤니티 딜 = 최근 3일 그대로(판매 확인 방법 없음), 진우 상품(own) = 날짜 상관없이 같은 url 최신 글 1개(같은 url 커뮤니티 글이 더 새로 칸에 있으면 그것만) — 빼는 건 shelf가 None인 것뿐."""
    today, ev = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600)), ev_info()
    recent = lambda p: p["t"][:10] in days[:3] and not p["text"].startswith("📋")
    last = {p.get("url"): i for i, p in enumerate(posts) if p.get("own")}
    newer = {p.get("url"): i for i, p in enumerate(posts) if not p.get("own") and recent(p)}  # 같은 url 커뮤니티 글이 더 새로 칸에 있으면 그것만(같은 상품 두 번 X)
    out = {}
    for i, p in enumerate(posts):
        if p["text"].startswith("📋") or (last.get(p.get("url")) != i or newer.get(p.get("url"), -1) > i if p.get("own") else not recent(p)):
            continue
        if (s := shelf(p, ev, today)) is not None:
            out[i] = s
    return out


def cap(ds, n):
    """칸 개수 제한 n은 커뮤니티 딜에만 — 진우 상품(own)은 안 밀려남(10/23)."""
    out, k = [], 0
    for i, p in ds:
        if p.get("own") or k < n:
            out.append((i, p))
            k += not p.get("own")
    return out


SHOW_MIN = 6  # 칸마다 처음 보이는 카드 수(🔥 목표 특가가 더 많으면 🔥 전부) — 나머지는 '더 보기'로 접음(10/23 진우 '🔥 강점 유지')


def shelf_grid(ds, home, n, days):
    """칸 격자(최신 순 ds): 🔥 특가 중(🔁 다시 특가 먼저) → ⏳ 특가 대기(👍 꾸준템 먼저) → 일시 품절(같은 단계는 진우 상품 먼저, 그다음 최신), 커뮤니티 딜은 n개까지(cap).
    🔥는 다 보이고 나머지는 SHOW_MIN칸까지 보인 뒤 '더 보기 N개'(접힘, 삭제 X). -> (카드 수, HTML)"""
    ds = cap(sorted(ds, key=lambda x: (home[x[0]][0], not home[x[0]][4], not x[1].get("own"))), n)  # 🔥 안에선 🔁 다시 특가 맨 위
    k = max(SHOW_MIN, sum(home[i][0] == 0 for i, _ in ds))
    g = [grid_item(i, p, old=bool(p.get("own")) or p["t"][:10] not in days[:3], sh=home[i]) for i, p in ds]
    return len(g), f'<div class="grid">{"".join(g[:k])}</div>' + (f'<details class="mo"><summary>더 보기 {len(g) - k}개</summary><div class="grid">{"".join(g[k:])}</div></details>' if g[k:] else "")


def hot_section(posts, days):
    """홈 맨 위 '지금 반응 좋은 딜'(10/9 진우): 최근 2일 커뮤니티 딜 중 반응(pop = 게시 때 분당 조회수 + 추천×5) 높은 6개. 반응 수치가 쌓이기 전엔 안 보임."""
    ds = sorted(((i, p) for i, p in enumerate(posts) if p["t"][:10] in days[:2] and p.get("pop")), key=lambda x: -x[1]["pop"])[:6]
    return (f'<section class="day" id="hot" aria-labelledby="hoth"><h2 id="hoth">🏆 지금 반응 좋은 딜</h2><div class="t">뽐뿌·클리앙 조회수·추천 기준</div>'
            f'<div class="grid">{"".join(grid_item(i, p, True) for i, p in ds)}</div></section>') if len(ds) >= 2 else ""


CATS = (("life", "🧻 생필품", r"휴지|화장지|티슈|키친타[월올]|세제|유연제|퍼실|다우니|피죤|스너글|샴푸|린스|컨디셔너|트리트먼트|바디워시|핸드워시|손세정|비누|치약|칫솔|가글"
                              r"|리스테린|생리대|라이너|기저귀|면도|마스크(?!팩)|KF\d|크린랩|위생[백랩장]|니트릴|지퍼백|쿠킹호일|종량제|쓰레기봉투|수세미|고무장갑|행주|탈취|방향제"
                              r"|페브리즈|제습제|건전지|락스|세정제"),
        ("beauty", "💄 화장품", r"화장품|올리브영|스킨케어|토너|에센스(?!웨어)|세럼|앰플|로션|[수영]분크림|아이크림|선크림|핸드크림|바디크림|재생크림|선케어|선스틱|선쿠션|자외선"
                               r"|클렌징|클렌저|폼클렌|마스크팩|시트팩|토너패드|각질|화장솜|립스틱|립밤|립글로|틴트|쿠션팩트|에어쿠션|파운데이션|컨실러|미스트|향수|메이크업"
                               r"|마스카라|아이섀도|네일|올인원|헤어\s*(?:스프레이|왁스|오일|에센스|미스트)|슬리핑\s*마스크|립\s*마스크|모공\S*\s*마스크|크림\s*\+\s*마스크"))  # 제목 키워드(10/9 실제 딜 121개로 맞춤 — 크림·팩·쿠션·립·패드 단독은 음식·가구랑 겹쳐서 뺌)


HEAT = r"핫팩|손난로|발난로|보온대|온열|전기\s*(?:요|매트|장판)|온수\s*매트|난로|히터|발열\s*(?:내의|조끼)|방한"
HOME_RX = (r"모기|살충|홈키파|에프킬라|킨칸|퇴치|샤워기|샤워\s*헤드|수전|조리\s*도구|프라이팬|후라이팬|냄비|도마|주방|수저|젓가락|텀블러|밀폐\s*용기|보관\s*용기|정수|필터|수납|정리함|옷걸이|빨래|건조대|"
           r"청소포|물걸레|밀대|청소\s*(?:솔|도구)|매트(?!리스)|러그|이불|베개|커튼|전구|LED|가위|집게|휴지통|분리수거|화분|방충|문풍지|단열")
FASHION = r"양말|스타킹|레깅스|팬티|속옷|브라(?!운)|티셔츠|셔츠|바지|청바지|후드|맨투맨|패딩|자켓|재킷|코트|모자|비니|장갑|목도리|머플러|운동화|슬리퍼|신발|가방|백팩|지갑|벨트|우산|내의|잠옷|파자마|조끼"
DIGI = (r"충전기|케이블|보조\s*배터리|이어폰|헤드폰|헤드셋|블루투스|마우스|키보드|모니터|노트북|태블릿|아이패드|갤럭시|스마트\s*워치|SSD|USB|메모리|카메라|청소기|에어\s*프라이어|전기\s*포트|드라이기|"
        r"가습기|공기\s*청정|선풍기|제습기|밥솥|믹서|블렌더|토스터|면도기|멀티탭|스피커|TV|프린터|전동")
FOOD7 = FOOD + (r"|잡곡|현미|귀리|오트|돼지|돈육|소고기|우삼겹|차돌|불고기|닭가슴살|볶음밥|주먹밥|도시락|동그랑땡|떡갈비|돈까스|돈가스|너겟|간식|젤리|사탕|쿠키|비스킷|빵|베이글|두유|녹차|홍차|티백|보리차|"
                r"옥수수|참치|스팸|(?<!폴)햄(?!스터)|소시지|피자|떡볶이|어묵|곤약|요거트|요구르트|치즈|버터|꿀|잼|시리얼|그래놀라|두부|고구마|감자(?!탕)|토마토|딸기(?!향)|귤|포도|키위|블루베리|아몬드|호두|땅콩|"
                r"김밥|라떼|아메리카노|원두|탄산수|콜라(?!겐)|사이다|식혜|국수|우동|냉면|파스타|소면|당면|밀키트|밀가루|설탕|식용유|참기름|간장|된장|고추장|케첩|마요|분유|이유식")
SHELF_CATS = (("food", "🍚 식품·음료", FOOD7), ("life", "🧻 생필품", CATS[0][2]), ("beauty", "💄 화장품·뷰티", CATS[1][2]), ("home", "🏠 생활·주방", HOME_RX),
              ("fashion", "🧦 패션·잡화", FASHION), ("digital", "🔌 가전·디지털", DIGI), ("heat", "🔥 겨울 난방", HEAT))  # 10/23 진우 '사이트에도 제품 카테고리 구분' — 홈 '품목' 탭 한 칸 안에 7칸(겨울 난방 = 계절 칸, 없으면 안 보임)
CAT_ORDER = ("heat", "beauty", "life", "food", "home", "fashion", "digital")  # 제목이 여러 칸에 맞으면 이 순서(핫팩 = 난방, 크림·클렌징 = 화장품, 세제·휴지 = 생필품)


HOME_FIRST = r"모기|홈매트|훈증|살충|킨칸|에프킬라"  # 모기향 '히터'(리퀴드 훈증기)는 겨울 난방 X -> 생활·주방(10/23 리뷰)


def cat_of(p):
    """품목 칸 1개: 제목 정규식(HOME_FIRST -> CAT_ORDER 순) -> 안 맞으면 글 cat(hotdeal.cat_fill이 Claude 한 단어로 채움 — etc = 칸 없음) -> ''."""
    t, rx = title_of(p["text"]), {k: r for k, _, r in SHELF_CATS}
    return "home" if re.search(HOME_FIRST, t) else next((k for k in CAT_ORDER if re.search(rx[k], t)), p.get("cat") if p.get("cat") in rx else "")


def cat_sections(posts, days, nav=""):
    """홈 품목 칸 7개(SHELF_CATS — 10/9 생필품·화장품 2칸 -> 10/23 진우 '제품 카테고리 구분' 7칸): home_pool(커뮤니티 최근 3일 + 진우 상품 진열) 중 cat_of가 그 칸인 것,
    shelf_grid 순서(🔥 → 👍 → 판매 중 → 일시 품절, 커뮤니티 딜 6개까지). 없는 칸은 빈 값. nav = 생필품 칸 아래 최저가 기록 링크. -> [(id, 이름, 칸 HTML 또는 빈 값)]"""
    out, home = [], home_pool(posts, days)
    for key, name, _ in SHELF_CATS:
        n, g = shelf_grid([(i, p) for i, p in reversed(list(enumerate(posts))) if i in home and cat_of(p) == key], home, 6, days)
        out.append((key, name, n and f'<section class="day" id="{key}" aria-labelledby="{key}h"><h2 id="{key}h">{name} {n}개</h2><div class="t">🔥 특가 중 먼저 · 최근 3일 딜 + 핫딜픽 추천 상품</div>'
                                   f'{g}{nav if key == "life" else ""}</section>'))
    return out


def fire_section(posts, days):
    """홈 첫 칸 맨 위 '🔥 지금 특가 중'(10/23 진우 '홈 첫 칸은 늘 🔥 목표 특가 — 팔리는 강점 유지'): 진우 상품 🔥 전부(🔁 다시 특가 먼저, 최신 순), 6칸 뒤 '더 보기'. 없으면 빈 값."""
    home = home_pool(posts, days)
    ds = sorted(((i, p) for i, p in reversed(list(enumerate(posts))) if i in home and p.get("own") and home[i][0] == 0), key=lambda x: not home[x[0]][4])
    g = [grid_item(i, p, old=True, sh=home[i]) for i, p in ds]
    return g and (f'<section class="day" id="fire" aria-labelledby="fireh"><h2 id="fireh">🔥 지금 특가 중 {len(g)}개</h2><div class="t">핫딜픽이 고른 상품 중 지금도 특가 가격대인 것 · 🔁 = 특가 가격으로 다시 돌아온 상품</div>'
                  f'<div class="grid">{"".join(g[:SHOW_MIN])}</div>' + (f'<details class="mo"><summary>더 보기 {len(g) - SHOW_MIN}개</summary><div class="grid">{"".join(g[SHOW_MIN:])}</div></details>' if g[SHOW_MIN:] else "") + "</section>")


def wait_section(posts, days):
    """홈 '⏳ 특가 기다리는 상품' 탭(10/23 진우 '지금 특가가 아닌 제품은 나중에 특가를 기다릴 제품으로'): 진우 상품 중 ⏳ 전부 —
    특가 때 가격과 차이 작은 순(쿠팡·네이버 = Cowork 확인 가격 now / 목표가 tgt, 토스는 지금 가격을 사이트에 안 써서 그 뒤 — 👍 꾸준템 먼저, 최신)."""
    home, won = home_pool(posts, days), lambda s: int(re.sub(r"\D", "", (s or "").split("·")[0]) or 0)
    gap = lambda p: won(p.get("now")) / won(p.get("tgt")) if won(p.get("now")) and won(p.get("tgt")) else None
    ds = sorted(((i, p) for i, p in reversed(list(enumerate(posts))) if i in home and p.get("own") and home[i][0] in (1, 2)),
                key=lambda x: (gap(x[1]) is None, gap(x[1]) or 0, home[x[0]][0]))
    g = [grid_item(i, p, old=True, sh=home[i]) for i, p in ds]
    return g and (f'<section class="day" id="wait" aria-labelledby="waith"><h2 id="waith">⏳ 특가 기다리는 상품 {len(g)}개</h2><div class="t">지금은 특가가 아닌 핫딜픽 추천 상품 · 특가 때 가격으로 돌아오면 🔁 다시 특가로 맨 위에 올려요</div>'
                  f'<div class="grid">{"".join(g[:12])}</div>' + (f'<details class="mo"><summary>더 보기 {len(g) - 12}개</summary><div class="grid">{"".join(g[12:])}</div></details>' if g[12:] else "") + "</section>")


def cats_pane(secs):
    """홈 '품목' 탭(바 1칸 — 7칸을 바에 다 넣으면 폰에서 3줄이 돼서): 맨 위 칸 바로가기 + 칸들(감싼 div — PANE_JS가 칸으로 스크롤)."""
    secs = [(k, n, h) for k, n, h in secs if h]
    return secs and (f'<section class="day" id="cats" aria-labelledby="catsh"><h2 id="catsh">🗂 품목별 딜</h2><div class="recs">'
                     + "".join(f'<a href="#{k}">{n} {h.count(chr(60) + "article")}</a>' for k, n, h in secs) + f'</div></section><div class="cats">{"".join(h for _, _, h in secs)}</div>')


PRICE_ITEMS = (  # 10/17 진우 '유입 늘리기 ② 최저가 기록 페이지'(/c/주소.html): (주소, 품목, 제목 낱말, 비교 단위, 그 단위로 보는 '…당' 낱말 — 1L당 = 'l') — 같은 단위끼리만
    ("ramen", "라면", r"라면|너구리|짜파게티|안성탕면|컵누들|사발면", "개당", ("개", "봉", "봉지")),
    ("water", "생수", r"생수|샘물|삼다수|아이시스|백산수", "1L당", ("l",)),  # 병당·개당은 병 크기(500ml·2L)가 달라서 X
    ("toilet-paper", "화장지", r"화장지|두루마리|휴지(?!통)", "롤당", ("롤",)),
    ("detergent", "세탁세제", r"세탁\s*세제|액체\s*세제|퍼실|리큐|(?:테크|비트)\s*(?:액체|세제|파워)", "1L당", ("l",)),
    ("coffee-mix", "커피믹스", r"커피\s*믹스|모카\s*골드|화이트\s*골드", "개당", ("개", "개입", "t", "스틱")),
    ("wet-wipes", "물티슈", r"물티슈", "팩당", ("팩",)),
    ("eggs", "계란", r"계란|달걀|특란|왕란|구운란", "개당", ("개", "구", "알")),
    ("instant-rice", "즉석밥", r"햇반|즉석밥|오뚜기\s*(?:밥|흑미밥|잡곡밥)", "개당", ("개",)),
    ("shampoo", "샴푸", r"샴푸", "100ml당", ("100ml",)),
    ("rice", "쌀", r"햅쌀|백미|쌀\s*\d+\s*kg|\d+\s*kg\s*쌀", "1kg당", ("kg",)))
PRICE_NOT = r"냄비|그릇|용기|포트|머신|거치대|케이스|홀더|디스펜서|정리함|브러시|의자"  # 품목 낱말이 들어도 그 품목 아님(라면 냄비·샴푸 의자 등)
PRICE_MIN = 3  # 기록이 이보다 적으면 페이지·투표 X
PAIR = re.compile(r"((?:\d+(?:\.\d+)?\s*)?[^\d\s(),·~/]+?)\s*당\s*(?:약\s*|평균\s*)?(\d[\d,]*(?:\.\d+)?)\s*원")  # '개당 약 496원 (1L당 248원)' -> ('개','496'), ('1L','248')


def price_item(p):
    """이 딜의 최저가 기록 품목(PRICE_ITEMS 줄) — 토스 딜은 None(토스 요청 '타 쇼핑몰과의 가격 비교 없이': 다른 몰과 한 표에 놓는 것도 비교)."""
    title = title_of(p["text"])
    if p["text"].startswith("📋") or shop_of(p) == "toss" or re.search(PRICE_NOT, title):
        return None
    return next((it for it in PRICE_ITEMS if re.search(it[2], title)), None)


def price_records(posts):
    """최저가 기록 {주소: (품목, 단위, [(단위가격, '1L당 248원', i, p), …] 싼 순)} — 품목 딜 중 💡 단위가격에 그 단위가 있는 것만, PRICE_MIN개↑ 품목만.
    같은 상품이 같은 단위가격으로 다시 올라오면 최근 1개(숫자는 글에 적힌 그대로 — 단위 바꿔 셈 X)."""
    rows = {}
    for i, p in enumerate(posts):
        it = price_item(p)
        lab = it and next(((float(v.replace(",", "")), f"{it[3]} {v}원") for lb, v in PAIR.findall(unit_of(p)) if re.sub(r"^1(?=\D)|\s", "", lb).lower() in it[4]), None)
        if lab:
            rows.setdefault(it[0], {})[(parse(title_of(p["text"]))[1], lab[0])] = (*lab, i, p)
    return {k: (it[1], it[3], sorted(rows[k].values(), key=lambda r: (r[0], -r[2]))) for it in PRICE_ITEMS for k in [it[0]] if len(rows.get(k, ())) >= PRICE_MIN}


def rec_nav(recs, skip=""):
    """최저가 기록 페이지 링크 줄(홈 생필품 칸·기록 페이지 아래) — 검색 로봇이 /c/ 페이지를 찾게."""
    ls = [f'<a href="{BASE}c/{k}.html">{n} {u}</a>' for k, (n, u, _) in recs.items() if k != skip]
    return ls and f'<nav class="recs" aria-label="최저가 기록"><h3>📈 {"다른 " * bool(skip)}최저가 기록</h3>{"".join(ls)}</nav>'


def record_page(k, rec, recs):
    """/c/{k}.html 본문·설명: 지금(24시간 안) 올라온 딜(맨 위) → 기록 최저·평균 → 표(날짜·몰·상품·가격·단위가격, 상품 = 딜 페이지 링크) → 토스 탭 → 다른 기록.
    날짜 = 실제 게시 날짜, 숫자 = 글에 적힌 단위가격 그대로(평균만 계산)."""
    name, unit, rows = rec
    md = lambda p: f'{int(p["t"][5:7])}/{int(p["t"][8:10])}'
    low, avg, first = rows[0], round(sum(r[0] for r in rows) / len(rows)), min(r[3]["t"][:10] for r in rows)
    since = time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - 86400))
    now = sorted((r for r in rows if r[3]["t"] >= since), key=lambda r: r[3]["t"], reverse=True)[:4]
    tr = "".join(f'<tr{" class=min" if r is low else ""}><td>{md(r[3])}</td><td>{html.escape(parse(title_of(r[3]["text"]))[0] or "-")}</td>'
                 f'<td><a href="{BASE}p/{r[2]}.html">{html.escape(parse(title_of(r[3]["text"]))[1])}</a></td>'
                 f'<td>{f"{w:,}원" if (w := price_won(title_of(r[3]["text"]))) else ""}</td><td>{html.escape(r[1].split()[-1])}</td></tr>' for r in rows)
    body = (f'<section class="day rec" aria-labelledby="rech"><h2 id="rech">📈 {name} 최저가 기록 — {unit} 가격</h2>'
            f'<div class="t">핫딜픽이 {md({"t": first})}부터 올린 {name} 딜 {len(rows)}개를 {unit} 가격으로 모았어요. 단위가 다른 기록은 섞지 않아요 · 날짜 = 게시 날짜</div>'
            + (f'<h3>🔥 지금 올라온 {name} 딜</h3><div class="t">최근 24시간 · 가격·재고는 바뀔 수 있어요</div><div class="grid">{"".join(grid_item(r[2], r[3]) for r in now)}</div>' if now else "")
            + f'<div class="stat"><div><b>{html.escape(low[1].split()[-1])}</b>기록 최저 · {md(low[3])} {html.escape(parse(title_of(low[3]["text"]))[0])}</div><div><b>{avg:,}원</b>평균 · 기록 {len(rows)}개</div></div>'
            + f'<div class="tw"><table><thead><tr><th>날짜</th><th>몰</th><th>상품</th><th>가격</th><th>{unit}</th></tr></thead><tbody>{tr}</tbody></table></div>'
            + f'<p class="t">💙 토스 특가는 이 표에 넣지 않아요 — <a href="{BASE}#toss">토스 탭에서 보기</a></p>{rec_nav(recs, k) or ""}</section>')
    note = " ".join(dict.fromkeys(r[3]["text"].split("\n", 1)[0] for r in now if urllib.parse.urlsplit(r[3].get("url") or "").netloc in NAVER_HOSTS + OY_HOSTS and r[3]["text"].startswith(NOTE_STARTS)))  # 네이버·올영 링크 = 그 문구 맨 앞(딜 페이지와 같게)
    return body, f"{name} {unit} 가격 기록 {len(rows)}개 · 최저 {low[1].split()[-1]} ({md(low[3])}) · 평균 {avg:,}원 · {TITLE}", note


SHOP_NOTES = {  # 몰 칸 맨 위 대가성 문구 — hotdeal.py DISCLOSURE·TOSS_NOTE·NAVER_NOTE와 같은 글자(변형 금지, 셀프체크로 맞춤)
    "toss": "이 콘텐츠는 토스쇼핑 쉐어링크 활동의 일환으로, 링크를 통한 구매가 발생하면 일정 수수료를 지급받습니다.",
    "coupang": "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.",
    "naver": "이 포스팅은 네이버 쇼핑 커넥트 활동의 일환으로, 판매 발생 시 수수료를 제공받습니다."}


def shop_of(p):
    """3사 몰('toss'·'coupang'·'naver', 아니면 ''): 제목 [몰] 또는 구매 링크 주소(토스 = 쉐어링크)."""
    tag, url = parse(title_of(p["text"]))[0], p.get("url") or ""
    host = urllib.parse.urlsplit(url).netloc
    return ("toss" if toss_share(url) or "토스" in tag else "coupang" if "쿠팡" in tag or host in ("link.coupang.com", "coupa.ng")
            else "naver" if re.search("네이버|스마트스토어", tag) or host in NAVER_HOSTS + ("smartstore.naver.com", "brand.naver.com") else "")


def shop_section(posts, days, key):
    """홈 몰 칸(10/15 진우 '토스·쿠팡·네이버 탭'): home_pool(최근 3일 + 판매 중 진우 상품) 중 그 몰 딜 최신 순(커뮤니티 딜 24개까지) + 맨 위 그 몰 대가성 문구. 쿠팡·네이버는 0개면 칸·탭 없음,
    토스는 텔레그램 추천 버튼 때문에 늘 있음 — 토스 API 상품(베스트·하루특가)은 사이트에 안 올림(API 승인 범위 = 채널·Threads, '사이트 전시·가격 비교 안 함')."""
    head, extra = {"toss": ("💙 토스", f'<a class="btn2" href="{CHANNEL_WEB}" rel="noopener" target="_blank">🧺 토스 베스트·하루특가 추천 보기 (텔레그램)</a>'),
                   "coupang": ("🚀 쿠팡", f'<a class="btn2" href="{GOLDBOX}" rel="nofollow sponsored noopener" target="_blank">⏰ 쿠팡 골드박스</a>'),
                   "naver": ("💚 네이버", "")}[key]
    home = home_pool(posts, days)
    n, g = shelf_grid([(i, p) for i, p in reversed(list(enumerate(posts))) if i in home and shop_of(p) == key and (key != "toss" or toss_share(p.get("url")))], home, 24, days)  # 토스 칸 = 쉐어링크 딜만(예전 그대로)
    return (n or key == "toss") and (f'<section class="day" id="{key}" aria-labelledby="{key}h"><h2 id="{key}h">{head} 딜{f" {n}개" if n else ""}</h2>'
                                     f'<div class="t">{SHOP_NOTES[key]}</div>' + (g if n else "") + f'{extra}</section>')


def brand_section(posts, days):
    """홈 '✨ 정품·브랜드' 칸(10/10 진우 '브랜딩 파워 있는 제품도 꼭, 정품도'): home_pool(최근 3일 + 판매 중 진우 상품) 중 본사 정품 표시(tag)·이름 있는 브랜드(BRAND) 최신 순(커뮤니티 딜 8개까지)."""
    home = home_pool(posts, days)
    n, g = shelf_grid([(i, p) for i, p in reversed(list(enumerate(posts))) if i in home and (p.get("tag") == "정품" or re.search(BRAND, title_of(p["text"])))], home, 8, days)
    return n and (f'<section class="day" id="brand" aria-labelledby="brandh"><h2 id="brandh">✨ 정품·브랜드 딜</h2><div class="t">최근 3일 + 핫딜픽 추천 상품 · 판매자(본사 정품 여부)는 배지·상세에서 확인</div>'
                  f'{g}</section>')


def day_grids(posts, days):
    """날짜별 2열 격자. 날짜 안에서는 3사(토스·쿠팡·네이버) 딜 먼저, 그다음 최신 순(10/8 진우 '쿠팡·토스 먼저', '모바일 격자' · 10/15 3사 먼저)."""
    out = []
    for n, day in enumerate(days):
        ds = sorted(((i, p) for i, p in enumerate(posts) if p["t"].startswith(day) and not p["text"].startswith("📋")),
                    key=lambda x: (not shop_of(x[1]), [-ord(c) for c in x[1]["t"]]))
        out.append(f'<section class="day" id="d{n}" aria-labelledby="d{n}h"><h2 id="d{n}h">{int(day[5:7])}월 {int(day[8:])}일 딜 {len(ds)}개</h2>'
                   f'<div class="grid">{"".join(grid_item(i, p) for i, p in ds)}</div></section>')
    return "".join(out)


# 홈 = 한 칸씩(10/9 진우 '홈페이지가 정신이 없네' → 아래 고정 바 + 누른 칸만). 주소 #id가 든 칸만 보이고, 없으면 첫 칸(인스타·Threads에서 왔으면 카드 딜). JS가 꺼져 있으면 전부 보임(예전처럼)
ICONS = {  # 아래 바 아이콘 = Lucide(ISC 라이선스) 선 아이콘 — 이모지는 기기마다 모양·색이 달라 산만해서(10/9 진우 '심플하고 이쁘게')
    "hot": '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
    "today": '<path d="M10 12h11"/><path d="M10 18h11"/><path d="M10 6h11"/><path d="M4 10h2"/><path d="M4 6h1v4"/><path d="M6 18H4c0-1 2-2 2-3s-1-1.5-2-1"/>',
    "toss": '<path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/>',
    "coupang": '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>',
    "naver": '<path d="m2 7 4.41-4.41A2 2 0 0 1 7.83 2h8.34a2 2 0 0 1 1.42.59L22 7"/><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><path d="M15 22v-4a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2v4"/><path d="M2 7h20"/><path d="M22 7v3a2 2 0 0 1-2 2a2.7 2.7 0 0 1-1.59-.63.7.7 0 0 0-.82 0A2.7 2.7 0 0 1 16 12a2.7 2.7 0 0 1-1.59-.63.7.7 0 0 0-.82 0A2.7 2.7 0 0 1 12 12a2.7 2.7 0 0 1-1.59-.63.7.7 0 0 0-.82 0A2.7 2.7 0 0 1 8 12a2.7 2.7 0 0 1-1.59-.63.7.7 0 0 0-.82 0A2.7 2.7 0 0 1 4 12a2 2 0 0 1-2-2V7"/>',
    "cats": '<path d="M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z"/><path d="M12 22V12"/><path d="m3.3 7 7.703 4.734a2 2 0 0 0 1.994 0L20.7 7"/><path d="m7.5 4.27 9 5.15"/>',
    "wait": '<path d="M5 22h14"/><path d="M5 2h14"/><path d="M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22"/><path d="M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2"/>',
    "life": '<path d="M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z"/><path d="M12 22V12"/><path d="m3.3 7 7.703 4.734a2 2 0 0 0 1.994 0L20.7 7"/><path d="m7.5 4.27 9 5.15"/>',
    "beauty": '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/><path d="M20 3v4"/><path d="M22 5h-4"/><path d="M4 17v2"/><path d="M5 18H3"/>',
    "brand": '<path d="M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z"/><path d="m9 12 2 2 4-4"/>',
    "saved": '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>',
    "days": '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/><path d="M8 14h.01"/><path d="M12 14h.01"/><path d="M16 14h.01"/><path d="M8 18h.01"/><path d="M12 18h.01"/><path d="M16 18h.01"/>'}
ICONS["fire"] = ICONS["hot"]  # 반응 칸이 없을 땐 첫 칸 id가 fire
PANE_JS = """<script>(function(){var ps=[].slice.call(document.querySelectorAll('.pane'));if(!ps.length)return;
function show(){var e=location.hash&&document.getElementById(decodeURIComponent(location.hash.slice(1))),t=document.getElementById('today'),ig=/instagram|threads/i.test(document.referrer)||/[?&](fbclid|igsh|utm_source=(ig|threads))/.test(location.search),
p=e&&e.closest('.pane')||ig&&t&&t.parentNode||ps[0];
ps.forEach(function(x){x.hidden=x!==p});[].forEach.call(document.querySelectorAll('.bar a'),function(a){a.setAttribute('aria-current',p.contains(document.getElementById(a.hash.slice(1)))?'true':'false')});
if(e&&e.parentNode!==p)e.scrollIntoView();else scrollTo(0,0)}addEventListener('hashchange',show);show()})()</script>"""

# 찜(10/9 진우 '핫딜도 장바구니처럼' → 쇼핑몰마다 결제가 달라 한 번에 결제는 안 되고 모아 두기만): 카드 하트 -> 이 브라우저(localStorage)에 카드째 저장(최대 50개),
# 맨 위 '찜 N' -> 홈 '찜한 딜' 칸. 로그인·서버 저장 없음(다른 기기와 공유 X). 저장이 막힌 브라우저(사생활 모드 등)에선 그 화면에서만 유지
SAVED = ('<section class="day" id="saved" aria-labelledby="savedh"><h2 id="savedh">❤️ 찜한 딜</h2><div class="t">이 폰(브라우저)에만 저장돼요 · 가격은 올린 때 기준이라 바뀌었을 수 있어요</div>'
         '<div class="grid" id="savedg"></div><p id="saved0">아직 찜한 딜이 없어요. 딜 카드의 하트를 누르면 여기 모여요.</p></section>')
LIKE_JS = """<script>(function(){var L;try{L=JSON.parse(localStorage.getItem('likes'))||[]}catch(e){L=[]}
function has(i){return L.some(function(x){return x.i===i})}
function sync(){[].forEach.call(document.querySelectorAll('.like'),function(b){b.setAttribute('aria-pressed',has(b.dataset.i)?'true':'false')});
var c=document.getElementById('lc'),g=document.getElementById('savedg');if(c)c.textContent=L.length?' '+L.length:'';
if(g){g.innerHTML=L.map(function(x){return x.h}).join('');document.getElementById('saved0').hidden=L.length>0;[].forEach.call(g.querySelectorAll('.like'),function(b){b.setAttribute('aria-pressed','true')})}}
document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('.like');if(!b)return;var i=b.dataset.i;
L=has(i)?L.filter(function(x){return x.i!==i}):[{i:i,h:b.closest('.g').outerHTML}].concat(L).slice(0,50);try{localStorage.setItem('likes',JSON.stringify(L))}catch(e){}sync()});sync()})()</script>"""

# 검색·필터(10/10 진우 'UI 편하게'): 맨 위 고정 검색창 + 칩. 홈은 '전체' 칸(최근 2일), all.html은 전체 딜에서 걸러 보여 줌. JS가 꺼져 있으면 그냥 안 걸러짐
CHIPS = (("1만원", "💸 1만원 이하"), ("최저가", "📉 30일 최저가"), ("증정", "🎁 1+1·증정"), ("무배", "🚚 무료배송"), ("식품", "🍚 식품"), ("마감", "⏰ 오늘 마감"))  # 10/15 몰·품목 칩은 탭과 겹쳐서 조건 칩으로
find_box = lambda chips: ('<div class="find" role="search"><input id="q" type="search" placeholder="🔎 딜 검색 (예: 휴지, 설화수)" aria-label="딜 검색" autocomplete="off">'
                          '<div class="chips">' + "".join(f'<button type="button" data-c="{k}" aria-pressed="false">{n}</button>' for k, n in chips) + '</div><div id="qn" class="t" hidden></div></div>')
FIND = find_box(CHIPS)
FIND_JS = """<script>(function(){var q=document.getElementById('q');if(!q)return;var cs=[].slice.call(document.querySelectorAll('.chips button')),c='',qn=document.getElementById('qn'),host=document.getElementById('days')||document.body;
function run(){var v=q.value.trim().toLowerCase(),on=!!(v||c),n=0;if(on)[].forEach.call(document.querySelectorAll('.pane'),function(p){p.hidden=!p.contains(host)});
[].forEach.call(host.querySelectorAll('.g'),function(g){var ok=!on||(!v||g.textContent.toLowerCase().indexOf(v)>=0)&&(!c||(' '+g.dataset.k+' ').indexOf(' '+c+' ')>=0);g.hidden=!ok;if(ok&&on)n++});
[].forEach.call(host.querySelectorAll('.day'),function(s){s.hidden=on&&!s.querySelector('.g:not([hidden])')});qn.hidden=!on;qn.textContent=n?n+'개 찾았어요':'찾는 딜이 없어요 · 다른 말로 찾아보세요';
if(!on)dispatchEvent(new HashChangeEvent('hashchange'))}
q.addEventListener('input',run);cs.forEach(function(b){b.addEventListener('click',function(){c=c===b.dataset.c?'':b.dataset.c;cs.forEach(function(x){x.setAttribute('aria-pressed',x.dataset.c===c?'true':'false')});run()})});
addEventListener('hashchange',function(){if(q.value||c){q.value='';c='';cs.forEach(function(x){x.setAttribute('aria-pressed','false')});run()}});
var u=new URLSearchParams(location.search).get('q');if(u){q.value=u;run()}})()</script>"""
GO_FIND = ('<form class="find" role="search" action="../index.html"><input name="q" type="search" placeholder="🔎 다른 딜 검색 (예: 휴지, 설화수)"'
           ' aria-label="딜 검색" autocomplete="off" enterkeyhint="search"></form>')  # 딜 페이지 -> 홈에서 검색(10/11 진우 '딜 검색은 있었으면')


MORE = ('<nav class="more" aria-labelledby="moreh"><h2 id="moreh">🔥 다른 특가도 둘러보세요</h2><div>'  # 10/13 09:40 진우 '눈에 더 띄게'(연한 박스·3열·카테고리 색 원, 구매 버튼보다는 덜) · 딜 페이지(10/13 진우): '같이 보면 좋은 딜' 아래 페이지 안 메뉴 줄(고정 X — 앱 안 브라우저 툴바에 안 가림), 홈 칸으로
        + "".join(f'<a href="{BASE}#{k}" class="k-{k}"><i><svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[k]}</svg></i>{n}</a>' for k, n in (("hot", "인기"), ("toss", "토스"), ("coupang", "쿠팡"), ("naver", "네이버"), ("life", "생필품"), ("beauty", "화장품"), ("days", "전체 딜 보기")))
        + "</div></nav>")  # 10/15 진우 '요것도 손 봐줘': 6개 = 3열 2줄 꽉 차게 + 전체는 아래 한 줄 전체 폭(.k-days)


def related(i, p, pool, n=4):
    """딜 페이지 아래 '같이 보면 좋은 딜'(10/11 진우 '더 사고 싶게'): pool(최근 2일 제휴 링크 딜, 약한 딜 빼고) 중 같은 품목 먼저, 그다음 최신. 같은 이름 제외.
    쿠팡은 클릭 후 24시간 안 산 건 다 실적 -> 들어온 사람이 한 번 더 둘러보게."""
    me, k = title_of(p["text"]), set(keys(p).split()) - {"쿠팡", "토스", "네이버", "마감"}
    c = sorted(((j, q, ks) for j, q, ks in pool if j != i and title_of(q["text"]) != me), key=lambda x: x[1]["t"], reverse=True)
    return [(j, q) for j, q, _ in sorted(c, key=lambda x: -len(k & x[2]))[:n]]


def deal_card(i, p):
    """딜 페이지 본문(10/11 진우 '더 사고 싶게'): 몰·시각 -> 배지 -> 이름 -> 가격·얼마나 싼지·단위가격 -> 큰 구매 버튼 -> 왜 골랐나요(코멘트·확인할 점)."""
    title, rest, cut = split_title(p["text"])
    store, name, price = parse(title)
    body = to_html(rest, [{**e, "offset": e["offset"] - cut} for e in p.get("entities") or [] if e["offset"] >= cut])
    url, sv, u = f"{BASE}p/{i}.html", saving(p["text"]), " · ".join(x for x in (unit_of(p), steady_st(p["text"])) if x)  # 👍 = 한 달 구매·리뷰도
    if community(p.get("url")):  # 원글로 가는 버튼이면 이름을 정확히 + 원글이 지워져도 찾을 수 있게
        btn = (f'<a class="btn" href="{html.escape(p["url"])}" rel="nofollow noopener" target="_blank">📄 원글에서 구매 링크 보기</a>'
               f'<a class="btn2" href="{html.escape(find_url(title))}" rel="nofollow noopener" target="_blank">🔎 원글이 안 열리면 같은 상품 찾기</a>')
    else:
        btn = f'<a class="btn" href="{html.escape(p["url"])}" rel="nofollow sponsored noopener" target="_blank">{buy_label(title)}</a>' if p.get("url") else ""
    main, _, ship = price.partition("/")
    ship = {"무료": "무료배송", "무배": "무료배송"}.get(ship.strip(), ship.strip())
    hero = ((f'<div class="hero"><span class="pr">{html.escape(main.strip())}</span>' + (f'<span class="ship">{html.escape(ship.strip())}</span>' if ship.strip() else "")
             + (f'<span class="sv">{sv[0]}보다 {sv[1]}↓</span>' if sv else "") + "</div>") if price else "") + (f'<div class="u">{html.escape(u)}</div>' if u else "")
    bd = badge_html(p)
    return (f'<article class="card deal"><div class="s">{html.escape(store or "핫딜")} · {int(p["t"][5:7])}월 {int(p["t"][8:10])}일 {p["t"][11:16]}</div>'
            + (f'<div class="bd">{bd}</div>' if bd else "") + f'<h2><a href="{url}">{html.escape(name if price else title)}</a></h2>{hero}{btn}'
            + (f'<p class="note">가격·재고는 바뀔 수 있어요 · 결제 전 최종가 확인</p>' if btn else "") + f'<h3 class="why">왜 골랐나요</h3><p>{body}</p></article>')


NAVER_VERIFY = ("31caccebc9de97ffa6547f7d55966278daf9c469", "58af553d8879edfe3bc3a5189d9744ddc33bfcb9")  # 네이버 서치어드바이저 소유확인 — 값마다 meta 1줄(10/15 진우 'woori pd' 계정 = 두 번째, 첫 번째는 다른 계정일 수 있어 그대로)
GOOGLE_VERIFY = ""  # 구글 서치콘솔 'HTML 태그' content 값(10/14 진우 '검색 유입' — 진우 코드 오면 Cowork가 전달). 비면 출력 X


def seo(i, p):
    """딜 페이지 검색용 (제목, 설명, JSON-LD) — 10/14 진우 '검색 유입': '상품명 11,990원 (쿠팡) | 핫딜픽', '11,990원 · 개당 400원 · 쿠팡 · 10/14 게시 · 핫딜픽'
    (고지문·이모지 X), Product+Offer(가격 못 읽으면 X)."""
    store, name, price = parse(title_of(p["text"]))
    if not re.search(r"\d원", price) and (m := re.search(r"\s*\((\d[\d,]{2,})\s*/[^()]*\)", name)):  # '(10,000/무료)'처럼 '원' 없는 가격
        price, name = m[1] + "원", (name[:m.start()] + name[m.end():]).strip()
    won = (re.search(r"\d[\d,]*원", price) or [""])[0]
    ld = won and json.dumps({"@context": "https://schema.org", "@type": "Product", "name": name, "offers": {"@type": "Offer", "price": won[:-1].replace(",", ""), "priceCurrency": "KRW",
                                                                                                         "url": f"{BASE}p/{i}.html"}}, ensure_ascii=False).replace("</", "<\\/")
    return (" ".join(x for x in (name, won, store and f"({store})") if x) + f" | {TITLE}",
            " · ".join(x for x in (won, unit_of(p), store, f"{int(p['t'][5:7])}/{int(p['t'][8:10])} 게시", TITLE) if x),
            ld and f'<script type="application/ld+json">{ld}</script>')


def summary(text):
    """검색 결과·RSS에 보일 설명: 제목 아래 코멘트 줄들(출처·🏆 배지 줄 빼고 한 줄로). 대가성 문구·제목 반복은 안 넣음(10/9 '구글·네이버 조회가 잘 안 돼')."""
    return " ".join([steady_st(text)] * bool(steady_st(text)) + [l.strip() for l in split_title(text)[1].split("\n") if l.strip() and not l.startswith(("출처:", "🏆 인기"))])[:150]


def steady_page(out):
    """👍 꾸준템 페이지(steady.html, 10/22 진우 '꾸준템 리스트'): 마지막 19:50 리스트(steady.json — hotdeal.steady_list가 씀) 그대로. 리스트가 아직 없으면 안 만듦 -> (주소, 날짜) 또는 None."""
    try:
        d = json.load(open(f"{out}/steady.json"))
    except (OSError, ValueError):
        return None
    link = lambda x: f"{BASE}p/{x['i']}.html" if x.get("i") is not None and urllib.parse.urlsplit(x["u"]).netloc in OY_HOSTS else x["u"]  # 올영 = 딜 페이지 거쳐(사이트 규칙 그대로)
    rows = "".join(f'<li><b>{html.escape(x["n"])}</b><br>💰 {html.escape(x["p"] or "가격은 링크에서 확인")}{" · " + html.escape(x["st"]) if x.get("st") else ""}<br>'
                   f'<a class="btn2" href="{html.escape(link(x))}" rel="nofollow sponsored noopener" target="_blank">구매하러 가기 →</a></li>' for x in d["items"])
    body = (f'<section class="day" aria-labelledby="sth"><h2 id="sth">👍 꾸준히 팔리는 것 모음</h2><div class="t">최저가는 아니어도 꾸준히 많이 사는 것 · '
            f'{int(d["at"][5:7])}/{int(d["at"][8:10])} {d["at"][11:16]} 게시 시점 가격 · 가격·재고는 바뀔 수 있어요</div><ol>{rows}</ol></section>')
    open(f"{out}/steady.html", "w").write(page(f"꾸준히 팔리는 것 모음 | {TITLE}", body + MORE + END_JS, "최저가는 아니어도 꾸준히 많이 사는 생필품·화장품 모음(매일 저녁 갱신)",
                                               f"{BASE}steady.html", gb=False, note="\n".join(d.get("notes") or [])))
    return f"{BASE}steady.html", d["at"][:10]


def build(posts, out="docs"):
    os.makedirs(f"{out}/p", exist_ok=True)
    open(f"{out}/.nojekyll", "w").close()
    open(f"{out}/CNAME", "w").write(BASE.split("/")[2])  # GitHub Pages 커스텀 도메인 (재생성 때 안 날아가게)
    latest = posts[-1]["t"][:10] if posts else ""
    urls = [(BASE, latest)]
    days = sorted({p["t"][:10] for p in posts if not p["text"].startswith("📋")}, reverse=True)
    pool = [(j, q, set(keys(q).split())) for j, q in enumerate(posts) if q["t"][:10] in days[:2] and not q["text"].startswith("📋")
            and aff(q.get("url")) and "특가로는 약한 제품" not in q["text"]]
    recs = price_records(posts)
    os.makedirs(f"{out}/c", exist_ok=True)
    for f in os.listdir(f"{out}/c"):  # 품목에서 빠진 옛 기록 페이지는 지움(사이트맵과 맞게)
        if f[:-5] not in recs:
            os.remove(f"{out}/c/{f}")
    for k, rec in recs.items():
        body, desc, note = record_page(k, rec, recs)
        open(f"{out}/c/{k}.html", "w").write(page(f"{rec[0]} 최저가 기록 — {rec[1]} 가격 | {TITLE}", GO_FIND + body + MORE + LIKE_JS + END_JS, desc, f"{BASE}c/{k}.html", gb=False, note=note))
        urls.append((f"{BASE}c/{k}.html", max(r[3]["t"][:10] for r in rec[2])))
    for i, p in reversed(list(enumerate(posts))):
        title, url, rel = title_of(p["text"]), f"{BASE}p/{i}.html", related(i, p, pool)
        more = rel and f'<section class="day rel" aria-labelledby="relh"><h2 id="relh">같이 보면 좋은 딜</h2><div class="grid">{"".join(grid_item(j, q) for j, q in rel)}</div></section>'
        note = p["text"].split("\n", 1)[0] if urllib.parse.urlsplit(p.get("url") or "").netloc in NAVER_HOSTS + OY_HOSTS and p["text"].startswith(NOTE_STARTS) else ""  # 네이버·올영: 그 프로그램 문구 그대로 맨 앞(변형·누락 시 패널티)
        st, sd, ld = seo(i, p)
        it = price_item(p)
        rl = it and it[0] in recs and f'<a class="btn2" href="{BASE}c/{it[0]}.html">📈 {it[1]} {it[3]} 최저가 기록 보기</a>'  # 그 품목 기록 페이지로(내부 링크 — 검색 로봇이 찾게)
        open(f"{out}/p/{i}.html", "w").write(page(st, (ld or "") + GO_FIND + GB_LINK + deal_card(i, p) + (rl or "") + (more or "") + MORE + LIKE_JS + END_JS, sd, url, gb=False, note=note))
        urls.append((url, p["t"][:10]))
    fire, react = fire_section(posts, days), hot_section(posts, days)
    panes = [("hot" if react else "fire", "🏆 인기", (fire or "") + (react or "")), *((k, n, shop_section(posts, days, k)) for k, n in (("toss", "💙 토스"), ("coupang", "🚀 쿠팡"), ("naver", "💚 네이버"))),
             ("cats", "🗂 품목", cats_pane(cat_sections(posts, days, rec_nav(recs) or ""))), ("wait", "⏳ 대기", wait_section(posts, days)), ("brand", "✨ 브랜드", brand_section(posts, days)), ("today", "📸 카드", card_picks(posts, out)), ("days", "📅 전체", f'<div id="days">{day_grids(posts, days[:2]) or "<p>첫 딜을 준비 중이에요.</p>"}'
                                                          f'<a class="btn2" href="{BASE}all.html">지난 딜 전체 보기 →</a></div>'), ("saved", "❤️ 찜", SAVED)]
    panes = [p for p in panes if p[2]]
    bar = lambda home, cls="bar": (f'<nav class="{cls}" aria-label="바로가기">' + "".join(f'<a href="{home}#{k}" class="k-{k}"><i><svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[k]}</svg></i>{n.split()[-1]}</a>' for k, n, _ in panes if k != "saved") + "</nav>")  # 찜은 맨 위 '찜' 버튼으로
    find = lambda home, ps: find_box([(k, n) for k, n in CHIPS if any(k in (keys(p) + " " + conds(p)).split() for p in ps)]) + bar(home, "bar top")  # 10/15 진우 '탭만 고정': 검색창·칩은 같이 스크롤, 앱 안 탭 줄만 sticky(.find 밖이어야 끝까지 붙음)  # 결과 0개 칩은 안 보임  # 앱 안 브라우저 = 검색창 아래 한 줄(가로 스크롤, 같은 아이콘·이름 — 아래 바는 숨김, CSS .inapp)
    ld = json.dumps({"@context": "https://schema.org", "@graph": [{"@type": "WebSite", "name": TITLE, "url": BASE, "inLanguage": "ko"},
                                                                  {"@type": "Organization", "name": TITLE, "url": BASE, "sameAs": [INSTA, THREADS, BLOG, CHANNEL]}]}, ensure_ascii=False)
    open(f"{out}/index.html", "w").write(page(f"{TITLE} - 오늘의 핫딜·특가 모음 (쿠팡·네이버·토스)", f'<script type="application/ld+json">{ld}</script>' + find("", [p for p in posts if p["t"][:10] in days[:2] and not p["text"].startswith("📋")]) + "".join(f'<div class="pane"{" hidden" * (k == "saved")}>{h}</div>' for k, _, h in panes) + bar("") + PANE_JS + LIKE_JS + FIND_JS + END_JS,  # 홈에선 #칸만(인스타 ?fbclid 붙어 와도 새로 안 불러옴)
                                              "뽐뿌·클리앙·루리웹에 올라온 핫딜 중 살 만한 것만 매일 골라 정리해요. 지금 반응 좋은 딜, 생필품·화장품, 토스 특가까지 한눈에.", BASE, top=INSTALL))
    open(f"{out}/manifest.webmanifest", "w").write(json.dumps(MANIFEST, ensure_ascii=False, indent=1))  # 웹앱(10/23 진우) — 아이콘은 cards.app_icons(docs/icons, 한 번 만들어 커밋)
    open(f"{out}/sw.js", "w").write(SW_JS % hashlib.md5(open(f"{out}/index.html", "rb").read() + open(f"{out}/manifest.webmanifest", "rb").read()).hexdigest()[:10])  # 홈·manifest(아이콘 주소)가 바뀐 배포마다 캐시 이름 바뀜(같으면 그대로 — 실행마다 커밋 X)
    open(f"{out}/all.html", "w").write(page(f"지난 딜 전체 | {TITLE}", find(BASE, [p for p in posts if not p["text"].startswith("📋")]) + bar(BASE) + day_grids(posts, days) + LIKE_JS + FIND_JS + END_JS, "핫딜픽에 올라온 딜 전체", f"{BASE}all.html"))
    urls.append((f"{BASE}all.html", latest))
    urls += [u for u in [steady_page(out)] if u]
    open(f"{out}/sitemap.xml", "w").write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                           + "".join(f"<url><loc>{u}</loc>{d and f'<lastmod>{d}</lastmod>'}</url>" for u, d in urls) + "</urlset>")
    open(f"{out}/robots.txt", "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}sitemap.xml\n")  # 검색 로봇에게 사이트맵 위치(10/9)
    items = [(i, p) for i, p in enumerate(posts) if not p["text"].startswith("📋")][-30:][::-1]  # 네이버 서치어드바이저 'RSS 제출'용 최근 딜 30개
    open(f"{out}/rss.xml", "w").write(
        f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{TITLE}</title><link>{BASE}</link><description>매일 살 만한 핫딜만 골라드려요</description><language>ko</language>'
        + "".join(f'<item><title>{html.escape(title_of(p["text"]))}</title><link>{BASE}p/{i}.html</link><guid>{BASE}p/{i}.html</guid>'
                  f'<description>{html.escape(summary(p["text"]))}</description><pubDate>{time.strftime("%a, %d %b %Y %H:%M:00 +0900", time.strptime(p["t"][:16], "%Y-%m-%d %H:%M"))}</pubDate></item>'
                  for i, p in items) + "</channel></rss>")
    return len(posts)


if __name__ == "__main__":
    posts = json.load(open("posts.json")) if os.path.exists("posts.json") else []
    print("site:", build(posts), "posts")
