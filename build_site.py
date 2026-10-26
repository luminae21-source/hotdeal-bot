#!/usr/bin/env python3
"""posts.json(채널에 게시된 딜) -> docs/ 정적 사이트. GitHub Pages로 서빙. 외부 패키지 없음."""
import calendar, collections, hashlib, html, itertools, json, os, re, shutil, time, urllib.parse

BASE = "https://hotdealpick.kr/"
GC_CODE = "hotdealpick"  # GoatCounter 사이트 코드(10/11 진우 결정 '측정 붙이기' — 10/23 진우 가입, hotdealpick.goatcounter.com). 비어 있으면 측정 X · 진우 본인 방문 빼기 = hotdealpick.kr/#toggle-goatcounter
GC_JS = ("document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a[rel~=\"nofollow\"]:not([data-gc^=\"promo/\"])');"  # 구매 링크(바깥 몰) 클릭 = 이벤트 buy/몰 주소+경로(10/24 E — 상품마다 셈, 쿼리 X)
         "if(!a||!window.goatcounter||!goatcounter.count)return;var h;try{h=new URL(a.href);h=h.hostname+h.pathname}catch(x){return}"
         "goatcounter.count({path:'buy/'+h,title:(a.getAttribute('aria-label')||a.textContent||'').trim().slice(0,80),event:true});var L,N;try{L=sessionStorage.getItem('hp_lv');N=sessionStorage.getItem('hp_l3')}catch(x){}if(L)goatcounter.count({path:'layout/'+L+'/buy',title:'화면 '+L+' 구매 클릭',event:true});if(L&&N)goatcounter.count({path:'layout3/'+L+'/buy',title:'화면 '+L+' 구매 클릭(3안 배정)',event:true})});"  # 화면 꼬리표 = 이 탭 방문을 센 화면(중간에 바꿔도 — 방문·구매가 같은 쪽, 방문 안 셌으면 X) · buy/는 그대로(gc_top·cp_score가 읽음)
         "document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('a[data-ev],[data-gc]');"  # 기획전 배너 = 이벤트 banner/행사 · 칸별(data-gc) = mall/몰·top/N·deadline/글·drop/글·changes/종류(10/24 Cowork — 어느 칸을 누르는지)
         "if(b&&window.goatcounter&&goatcounter.count)goatcounter.count({path:b.getAttribute('data-gc')||'banner/'+b.getAttribute('data-ev'),title:(b.getAttribute('aria-label')||b.textContent||'').trim().slice(0,80),event:true})});"
         "function hpL(){var c=document.documentElement.classList;return c.contains('lay-b')?'B':c.contains('lay-c')?'C':'A'}"  # 화면 고르기(10/24 Cowork·진우 · C 혼합형 10/25): layout/A·B·C = 방문(탭 세션 1번 · 저장소 막혀 무작위가 안 된 사람 = 실험 밖) · layout/A/buy·B/buy = 구매 클릭 · layout/switch = 바꾸기 버튼(data-gc)
         "addEventListener('load',function(){var g=window.goatcounter;if(!g||!g.count)return;try{if(localStorage.getItem('hp_layout')!==hpL().toLowerCase()||sessionStorage.getItem('hp_lv'))return;sessionStorage.setItem('hp_lv',hpL());var n=localStorage.getItem('hp_lc')==='3';if(n)sessionStorage.setItem('hp_l3','1')}catch(x){return}g.count({path:'layout/'+hpL(),title:'화면 '+hpL()+' 방문',event:true});if(n)g.count({path:'layout3/'+hpL(),title:'화면 '+hpL()+' 방문(3안 배정)',event:true})});")  # layout3/ = C를 연 뒤(10/25) 무작위 1/3로 배정된 사람만 — A·B·C 공정 비교(예전 A·B 사람 = 다시 오는 사람이라 따로)


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
CAT_ICON = {  # 품목 선 아이콘(10/24 진우 — 사진 없을 때 이모지 대신, 아래 메뉴 선 아이콘과 같은 모양 · 틀린 그림 X: 뷰티 = 펌프 병·제철 = 잎·패션 = 옷걸이)
    "life": '<circle cx="8" cy="9" r="5"/><circle cx="8" cy="9" r="1.25"/><path d="M8 4h8a5 5 0 0 1 5 5v11l-1.5-1-1.5 1-1.5-1-1.5 1v-6H8"/>',  # 휴지 롤
    "food": '<path d="M3 12a9 9 0 0 0 18 0Z"/><path d="M5.5 12a6.5 5 0 0 1 13 0"/><path d="M9 21.5h6"/>',  # 밥그릇
    "beauty": '<rect x="7" y="10" width="10" height="12" rx="2"/><path d="M10 10V7.5h4V10"/><path d="M12 7.5V4"/><path d="M9.5 4H15l1.5 1.5"/><path d="M10 15h4"/>',  # 펌프 병(립스틱 X)
    "kitchen": '<path d="M2 12h20"/><path d="M20 12v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8"/><path d="m4 8 16-4"/><path d="m8.86 6.78-.45-1.81a2 2 0 0 1 1.45-2.43l1.94-.48a2 2 0 0 1 2.43 1.46l.45 1.8"/>',  # Lucide cooking-pot
    "laundry": '<path d="M3 8h18"/><path d="m4.5 8 1.4 11.3A2 2 0 0 0 7.9 21h8.2a2 2 0 0 0 2-1.7L19.5 8"/><path d="M6.2 12.5h11.6"/><path d="M6.7 16.5h10.6"/><path d="M8 8a4 3 0 0 1 8 0"/>',  # 빨래 바구니
    "snack": '<path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"/><path d="M8.5 8.5v.01"/><path d="M16 15.5v.01"/><path d="M12 12v.01"/><path d="M11 17v.01"/><path d="M7 14v.01"/>',  # Lucide cookie
    "women": '<circle cx="12" cy="12" r="3"/><path d="M12 16.5A4.5 4.5 0 1 1 7.5 12 4.5 4.5 0 1 1 12 7.5a4.5 4.5 0 1 1 4.5 4.5 4.5 4.5 0 1 1-4.5 4.5"/><path d="M12 7.5V9"/><path d="M7.5 12H9"/><path d="M16.5 12H15"/><path d="M12 16.5V15"/><path d="m8 8 1.88 1.88"/><path d="M14.12 9.88 16 8"/><path d="m8 16 1.88-1.88"/><path d="M14.12 14.12 16 16"/>',  # Lucide flower
    "heat": '<path d="M12 2 12 22M20.66 7 3.34 17M20.66 17 3.34 7"/><path d="M14.6 2.7 12 5.2 9.4 2.7M5.25 5.1 6.11 8.6 2.65 9.6M2.65 14.4 6.11 15.4 5.25 18.9M9.4 21.3 12 18.8 14.6 21.3M18.75 18.9 17.89 15.4 21.35 14.4M21.35 9.6 17.89 8.6 18.75 5.1"/>',  # 눈송이
    "season": '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>',  # Lucide leaf(고구마 X)
    "home": '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V9"/><path d="M10 21v-6h4v6"/>',  # 집
    "fashion": '<path d="M10 5.5a2 2 0 1 1 2 2V9"/><path d="M12 9 2.8 15.6a1 1 0 0 0 .6 1.8h17.2a1 1 0 0 0 .6-1.8Z"/>',  # 옷걸이(양말 X)
    "digital": '<path d="M12 22v-5"/><path d="M9 8V2"/><path d="M15 8V2"/><path d="M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z"/>',  # Lucide plug
    "car": '<path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2"/><circle cx="7" cy="17" r="2"/><path d="M9 17h6"/><circle cx="17" cy="17" r="2"/>',  # Lucide car(10/26 Cowork 자동차 칸)
    "": '<path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/>',  # Lucide shopping-bag(품목 없음)
}

CSS = """*{box-sizing:border-box}[hidden]{display:none!important}
:root{--bg:#F6F7F9;--card:#fff;--ink:#14161B;--sub:#6B7180;--line:#ECEEF2;--acc:#E5303F;--chip:#F1F3F6;--btn:#14161B;--btnt:#fff;--pk:#E8435A;--pkbg:linear-gradient(160deg,#FFE3E8,#FFF1E6);--pkln:rgba(232,67,90,.14);--pkt:#B3202F;--accf:#E5303F;--cpb:linear-gradient(160deg,#FFE5E3,#FFF2EE);--cpt:#C2202C;--tsb:linear-gradient(160deg,#E3EEFF,#EEF5FF);--tst:#1B64DA;--nvb:linear-gradient(160deg,#E2F7EA,#F0FAF3);--nvt:#00703A;color-scheme:light}
@media(prefers-color-scheme:dark){:root{--bg:#0F1013;--card:#1A1C21;--ink:#ECEEF2;--sub:#9AA0AC;--line:#262931;--acc:#FF5A66;--chip:#24272E;--btn:#ECEEF2;--btnt:#14161B;--pkbg:linear-gradient(160deg,#3A1E27,#33261F);--pkln:rgba(255,92,114,.18);--pkt:#FF9AA6;--cpb:linear-gradient(160deg,#3A1E22,#2E2224);--cpt:#FF8A8F;--tsb:linear-gradient(160deg,#1B2A44,#1E2633);--tst:#6AA5FF;--nvb:linear-gradient(160deg,#17332A,#1D2B26);--nvt:#3DDC84;color-scheme:dark}}
@font-face{font-family:"HDP Sans";src:url(/fonts/hdpsans-v1.woff2) format("woff2");font-weight:400 800;font-display:swap}
body{margin:0;font:15px/1.5 "HDP Sans",-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;letter-spacing:-.2px;background:var(--bg);color:var(--ink);-webkit-font-smoothing:antialiased;word-break:keep-all;overflow-wrap:anywhere}
a{color:inherit}main{max-width:560px;margin:0 auto;padding:0 calc(16px + env(safe-area-inset-right)) calc(88px + env(safe-area-inset-bottom)) calc(16px + env(safe-area-inset-left))}
a:focus-visible,button:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid var(--acc);outline-offset:2px}
html{scroll-padding:calc(72px + env(safe-area-inset-top)) 0 calc(76px + env(safe-area-inset-bottom))}html.inapp{scroll-padding:128px 0 16px}
.hd{position:sticky;top:-48px;z-index:10;margin:0 -16px;padding:env(safe-area-inset-top) 16px 0;background:var(--bg);box-shadow:0 1px 0 var(--line)}
.hr{display:flex;align-items:center;gap:8px;height:48px}.hr .lg{flex:1;min-width:0;display:flex;align-items:center;gap:8px;text-decoration:none;color:var(--ink)}
.logo{display:grid;place-items:center;width:32px;height:32px;border-radius:10px;background:linear-gradient(135deg,#FF6860,#DC2230);color:#fff;font-weight:900;font-size:15px;letter-spacing:-.8px}
.lg b,.lg h1{margin:0;font-size:19px;font-weight:900;letter-spacing:-.7px;line-height:1}
.ib::before{content:"";position:absolute;inset:-3px}.ib{position:relative;display:grid;place-items:center;width:38px;height:38px;border-radius:12px;background:var(--card);border:1px solid var(--line);color:var(--ink);text-decoration:none}
.ib svg,.nav svg,.sb svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.ib b{position:absolute;top:-4px;right:-4px;min-width:17px;height:17px;padding:0 4px;border-radius:9px;background:var(--accf);color:#fff;font-size:10.5px;line-height:17px;text-align:center}.ib b:empty{display:none}
.sb{position:relative;display:block;padding:0 0 6px}.sb svg{position:absolute;left:12px;top:11px;color:var(--acc)}.sb input{width:100%;height:42px;border:2px solid var(--acc);border-radius:12px;padding:0 10px 0 38px;font:inherit;font-size:16px;letter-spacing:-.3px;background:var(--card);color:var(--ink)}.sb input::placeholder{color:var(--sub)}
.dis{font-size:11.5px;line-height:1.5;color:var(--sub);margin:10px 2px 0}
.t{color:var(--sub);font-size:12.5px}
.tp{margin:16px 0 0;padding:20px 16px 6px;border-radius:24px;background:var(--pkbg)}
.ev{flex:0 0 88%;min-width:0;scroll-snap-align:start;display:flex;align-items:center;gap:12px;min-height:64px;padding:10px 14px;border-radius:18px;background:var(--pkbg);box-shadow:inset 0 0 0 1px var(--pkln);text-decoration:none;color:var(--ink)}
.ev .em{font-size:24px;line-height:1}.ev .tx{display:flex;flex-direction:column;flex:1;min-width:0}.ev b{font-size:15.5px;font-weight:800;letter-spacing:-.4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ev small{color:var(--sub);font-size:12.5px;letter-spacing:-.2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ev .go{flex:none;color:var(--pkt);font-size:13.5px;font-weight:800}
.evn{margin:10px 0 0;padding:12px 14px;border-radius:14px;background:var(--pkbg);font-size:13.5px;font-weight:600;letter-spacing:-.3px}.dd{color:var(--acc);font-weight:800}
.tp .pn{margin:0 0 6px;font-size:11px;line-height:1.5;color:var(--sub)}.tp .k{color:var(--acc);font-size:12px;font-weight:800;letter-spacing:.2px}.tp h2{margin:6px 0 2px;font-size:23px;line-height:1.3;font-weight:800;letter-spacing:-.8px}.tp .d{color:var(--sub);font-size:13px;margin:0 0 6px}
.pk{display:grid;grid-template-columns:16px 64px minmax(0,1fr) auto;align-items:center;gap:10px;padding:14px 0;border-top:1px solid var(--pkln)}.pk:first-of-type{border-top:0}
.pk .rk{color:var(--acc);font-size:17px;font-weight:800;text-align:center}.pk .im{width:64px;height:64px;border-radius:16px;font-size:30px}
.pk h3{margin:3px 0 2px;font-size:14.5px;line-height:1.35;font-weight:600;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.pk h3 a{text-decoration:none}
.pk .pr{font-size:18px;font-weight:800;letter-spacing:-.6px;line-height:1.3}.pk .go{display:flex;align-items:center;height:44px;padding:0 14px;border-radius:12px;background:var(--pk);color:#fff;font-size:14px;font-weight:700;text-decoration:none;white-space:nowrap}
.mc{display:inline-block;padding:1px 6px;border-radius:6px;background:var(--chip);color:var(--sub);font-size:11.5px;font-weight:600;letter-spacing:-.2px}
.ex{color:var(--acc);font-size:12px;font-weight:700}.u{color:var(--sub);font-size:12px;line-height:1.45}
.im{position:relative;display:grid;place-items:center;overflow:hidden;background:var(--c,var(--chip));text-decoration:none}.im img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:#fff}.ci{display:block;width:1em;height:1em;background:var(--ci,var(--sub));-webkit-mask:var(--m) center/contain no-repeat;mask:var(--m) center/contain no-repeat}.deal .im .ci{width:.7em;height:.7em}
.tiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:12px 0 0}
.tile{display:flex;flex-direction:column;align-items:center;gap:6px;padding:12px 2px 10px;border-radius:18px;background:var(--card);box-shadow:0 1px 0 var(--line);text-decoration:none;font-size:13px;font-weight:600;letter-spacing:-.4px;white-space:nowrap}
.tile i{display:grid;place-items:center;width:40px;height:40px;border-radius:12px;background:var(--c);font-style:normal;font-size:22px}
.sec{margin:28px 0 0}.sec>h2{display:flex;align-items:baseline;justify-content:space-between;gap:8px;margin:0 2px 2px;font-size:19px;font-weight:800;letter-spacing:-.6px}.sec>h2 small{color:var(--sub);font-size:13px;font-weight:600;letter-spacing:-.2px}.sec>.t{margin:0 2px}
.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:12px}
.g{position:relative;display:flex;flex-direction:column;min-width:0;padding:8px 8px 12px;border-radius:20px;background:var(--card);box-shadow:0 1px 0 var(--line)}
.g .im{height:118px;border-radius:14px;font-size:46px}.g .bdg{position:absolute;top:8px;left:8px;padding:3px 7px;border-radius:8px;font-size:11px;font-weight:800;letter-spacing:-.2px;background:var(--card);color:var(--ink)}.g .bdg.f{background:var(--accf);color:#fff}.g .bdg.w{background:rgba(20,22,27,.72);color:#fff}
.g .mc{margin:9px 2px 0;align-self:flex-start}.g h3{margin:5px 2px 4px;font-size:14px;line-height:1.4;font-weight:600;letter-spacing:-.3px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.g h3 a{text-decoration:none}.g h3 a::after{content:"";position:absolute;inset:0;border-radius:20px}
.g .pr{margin:0 2px;font-size:17px;font-weight:800;letter-spacing:-.6px;line-height:1.3}.g .u,.g .ex{margin:1px 2px 0}
.like{position:absolute;z-index:2;top:12px;right:12px;display:grid;place-items:center;width:34px;height:34px;padding:0;border:0;border-radius:17px;background:rgba(255,255,255,.86);color:#6B7180;cursor:pointer}.like::before{content:"";position:absolute;inset:-5px}.like svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.like[aria-pressed=true]{color:var(--acc)}.like[aria-pressed=true] svg{fill:currentColor}
.g .s,.g .bd,.g .go,.g .rx,.g .sv{margin:2px 2px 0;font-size:12px;color:var(--sub)}.g .go{position:relative;z-index:1}.g:not(:has(.im)) h3{padding-right:36px}.g .go a{display:block;margin-top:8px;padding:9px 0;border-radius:10px;background:var(--chip);text-align:center;text-decoration:none;font-weight:700}
.all{display:flex;align-items:center;justify-content:center;min-height:52px;margin:12px 0 0;border-radius:14px;background:var(--btn);color:var(--btnt);text-decoration:none;font-weight:700;font-size:15px;letter-spacing:-.3px}
.btn{display:flex;align-items:center;justify-content:center;min-height:54px;margin-top:14px;padding:10px 12px;border-radius:14px;background:var(--accf);color:#fff;text-decoration:none;font-weight:800;font-size:17px;letter-spacing:-.4px;text-align:center}
.btn2{display:flex;align-items:center;justify-content:center;min-height:48px;margin-top:8px;padding:8px 12px;border-radius:14px;background:var(--card);border:1px solid var(--line);text-decoration:none;font-weight:700;text-align:center}
.chips{display:flex;gap:6px;margin:14px -16px 0;padding:0 16px 2px;overflow-x:auto;scrollbar-width:none}.chips::-webkit-scrollbar{display:none}.chips a{flex:none}.chips a{display:flex;align-items:center;min-height:40px;padding:0 12px;border-radius:18px;background:var(--card);border:1px solid var(--line);text-decoration:none;font-size:13.5px;font-weight:600}.chips a[aria-current=page]{background:var(--btn);border-color:var(--btn);color:var(--btnt)}
.pg{display:flex;gap:8px;margin:16px 0 0}.pg a{flex:1}
h1.h{margin:18px 2px 2px;font-size:22px;font-weight:800;letter-spacing:-.8px;line-height:1.3}
.nav{position:fixed;left:0;right:0;bottom:0;z-index:9;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));padding:4px calc(4px + env(safe-area-inset-right)) calc(6px + env(safe-area-inset-bottom)) calc(4px + env(safe-area-inset-left));background:var(--card);border-top:1px solid var(--line)}
.nav a{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;min-height:52px;color:var(--sub);text-decoration:none;font-size:11.5px;font-weight:600}.nav a[aria-current=page]{color:var(--ink)}.nav a[aria-current=page] svg{stroke-width:2.4}
.inapp .nav{position:static;margin:10px -16px 0;padding:0;background:none;border:0}.inapp .hr .ib{display:none}.inapp main{padding-bottom:calc(32px + env(safe-area-inset-bottom))}
.card,.deal{background:var(--card);border-radius:20px;padding:16px;margin:14px 0;box-shadow:0 1px 0 var(--line)}.card h2{margin:0 0 8px;font-size:18px;letter-spacing:-.5px}
.deal .im{height:220px;border-radius:16px;font-size:80px;margin:-4px -4px 12px}.deal .dn{margin:6px 0 10px;font-size:20px;line-height:1.4;letter-spacing:-.6px}.deal .dn a{text-decoration:none}.hero{display:flex;align-items:baseline;flex-wrap:wrap;gap:2px 8px}.hero .pr{font-size:28px;font-weight:800;letter-spacing:-.8px}.ship{font-size:13px;color:var(--sub)}
.deal .note{font-size:12px;color:var(--sub);text-align:center;margin:8px 0 0}.why{font-size:14px;color:var(--sub);font-weight:700;margin:18px 0 6px;padding-top:16px;border-top:1px solid var(--line)}.deal p{margin:0;font-size:15px;line-height:1.65}.deal p a{color:var(--acc)}
.bd{display:flex;flex-wrap:wrap;gap:4px;margin:6px 0 2px}.bd b{font-size:11px;font-weight:700;padding:2px 7px;border-radius:6px;line-height:1.5;background:var(--chip);color:var(--sub)}.b1{color:#15803d!important}.b2{color:var(--acc)!important}.b4{color:#d9480f!important}
.pick{display:flex;align-items:center;gap:12px;min-height:56px;padding:12px 14px;margin:8px 0;border-radius:14px;background:var(--card);box-shadow:0 1px 0 var(--line);text-decoration:none;font-weight:600}.pick b{color:var(--acc);font-size:19px;min-width:28px}.pick span{flex:1;line-height:1.35;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.pick em i{display:block;font-style:normal;color:var(--ink);font-weight:800;text-align:right}.pick .pt{width:40px;height:40px;margin:-4px 0;flex:none;border-radius:8px;object-fit:contain;background:#fff}.pick em{font-style:normal;color:var(--acc);font-size:14px;white-space:nowrap}.alt{display:block;margin:-4px 0 8px 54px;font-size:14px;padding:10px 0}#today details{margin-top:10px}#today summary,.mo summary{cursor:pointer;min-height:44px;padding:10px 0;font-weight:700;color:var(--sub)}
.recs{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0 4px}.recs h3{width:100%;margin:4px 2px 2px;font-size:15px}.recs a{display:flex;align-items:center;min-height:38px;padding:0 12px;border-radius:19px;background:var(--card);border:1px solid var(--line);text-decoration:none;font-size:13.5px}
.rec h3{font-size:16px;margin:18px 2px 2px}.stat{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0}.stat div{background:var(--card);border-radius:14px;padding:12px;font-size:12px;color:var(--sub);box-shadow:0 1px 0 var(--line)}.stat b{display:block;font-size:20px;font-weight:800;color:var(--ink);letter-spacing:-.4px}
.tw{overflow-x:auto;margin:14px 0 8px;background:var(--card);border-radius:14px;box-shadow:0 1px 0 var(--line)}.tw table{width:100%;border-collapse:collapse;font-size:13px}.tw th,.tw td{padding:9px 6px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}.tw th{color:var(--sub);font-weight:600;white-space:nowrap}.tw td:nth-child(-n+2),.tw td:nth-child(n+4){white-space:nowrap}.tw tr.min td{background:rgba(255,212,59,.18)}
.inst{position:fixed;z-index:8;left:0;right:0;bottom:calc(70px + env(safe-area-inset-bottom));display:flex;align-items:center;gap:4px;max-width:528px;margin:0 auto;padding:2px 0 2px 12px;min-height:48px;border-radius:14px;background:var(--card);border:1px solid var(--line);box-shadow:0 6px 20px rgba(20,22,27,.14);font-size:13px;line-height:1.35}@media(max-width:560px){.inst{left:10px;right:10px}}.inapp .inst{bottom:calc(10px + env(safe-area-inset-bottom))}main:has(>#inst:not([hidden])){padding-bottom:calc(150px + env(safe-area-inset-bottom))}.inst span{flex:1;min-width:0}.inst button{min-height:44px;border:0;border-radius:10px;font:inherit;font-weight:700;cursor:pointer;white-space:nowrap}#instb{background:var(--accf);color:#fff;padding:0 12px;font-size:14px}#instx{min-width:44px;background:none;color:var(--sub);font-size:16px}
footer{font-size:12px;color:var(--sub);text-align:center;padding:24px 44px 8px}footer a{color:var(--sub)}
#sr .t{margin:12px 2px 0}
@media(max-width:359px){main{padding-left:12px;padding-right:12px}.hd{margin:0 -12px;padding-left:12px;padding-right:12px}.tile{font-size:12px}.tp h2{font-size:21px}.pk{grid-template-columns:14px 56px minmax(0,1fr) auto;gap:8px}.pk .im{width:56px;height:56px}.pk .go{padding:0 10px}}
.mb{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(0,1fr);gap:6px;margin:10px 0 0}.m{display:flex;align-items:center;justify-content:center;height:36px;border-radius:12px;text-decoration:none;font-size:13.5px;font-weight:700;letter-spacing:-.3px;white-space:nowrap}
.coupang.m,.coupang.mt{background:var(--cpb);color:var(--cpt)}.toss.m,.toss.mt{background:var(--tsb);color:var(--tst)}.naver.m,.naver.mt{background:var(--nvb);color:var(--nvt)}.m.evt{background:var(--pkbg);color:var(--pkt)}
.lb,html.lay-b .la,html.lay-c .la{display:none}html.lay-b .lb,html.lay-c .lb{display:block}.qr .qc,html.lay-c .qr+.qr{display:none}html.lay-c .qr .qc{display:flex}
html:not(.lay-b) .hd{top:0}html:not(.lay-b) .hr{height:56px}html:not(.lay-b) .hr .lg{flex:none}html:not(.lay-b) .lg b,html:not(.lay-b) .lg h1{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
html:not(.lay-b) .hr .ib{margin-left:auto}html:not(.lay-b) .hr .ib+.ib{display:none}html:not(.lay-b) .sb{position:absolute;top:calc(env(safe-area-inset-top) + 8px);left:56px;right:62px;padding:0}html.inapp:not(.lay-b) .sb{right:16px}
html:not(.lay-b) .sb svg{top:10px;color:var(--sub)}html:not(.lay-b) .sb input{height:40px;border:1px solid var(--line);text-overflow:ellipsis}
.lsw{display:flex;align-items:center;justify-content:center;gap:6px;margin:18px 0 0;color:var(--sub);font-size:12.5px;font-weight:600}.lsw button{min-height:44px;padding:0 12px;border:1px solid var(--line);border-radius:12px;background:var(--card);color:var(--sub);font:inherit;letter-spacing:-.3px;cursor:pointer}html:not(.lay-b):not(.lay-c) .lsw [data-l=a],html.lay-b .lsw [data-l=b],html.lay-c .lsw [data-l=c]{background:var(--btn);border-color:var(--btn);color:var(--btnt)}
.tb{position:fixed;z-index:8;right:calc(10px + env(safe-area-inset-right));bottom:calc(80px + env(safe-area-inset-bottom));display:flex;flex-direction:column;gap:8px}main:has(>#inst:not([hidden]))+.tb{bottom:calc(128px + env(safe-area-inset-bottom))}.inapp .tb{bottom:calc(96px + env(safe-area-inset-bottom))}@media(min-width:680px){.tb{right:calc(50% - 336px)}}.tb button{display:flex;flex-direction:column;align-items:center;justify-content:center;width:44px;height:44px;padding:0;border:1px solid var(--line);border-radius:22px;background:color-mix(in srgb,var(--card) 86%,transparent);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px);box-shadow:0 2px 8px rgba(20,22,27,.16);color:var(--ink);font:inherit;font-size:8.5px;font-weight:800;letter-spacing:.2px;line-height:1;cursor:pointer}.tb svg{width:16px;height:16px}
.mk{flex:none;margin-right:5px;font-weight:800;color:var(--sub)}.mk.coupang{color:var(--cpt)}.mk.toss{color:var(--tst)}.mk.naver{color:var(--nvt)}
.tiles.t6{grid-template-columns:repeat(var(--n,6),minmax(0,1fr));gap:8px 2px;margin:12px 0 0}.t6 .tile{gap:4px;padding:0;background:none;box-shadow:none;border-radius:0;font-size:11px;letter-spacing:-.5px}.t6 .tile i{width:38px;height:38px;font-size:21px}
.sec>h2>span{display:flex;align-items:baseline;gap:6px;min-width:0}.sec>h2 .more{flex:none;color:var(--sub);font-size:13px;font-weight:700;text-decoration:none}
.tabs{display:flex;gap:6px;margin:10px -16px 0;padding:0 16px 2px;overflow-x:auto;scrollbar-width:none}.tabs::-webkit-scrollbar{display:none}
.tabs button,.mf button{flex:none;min-height:36px;padding:0 12px;border-radius:18px;border:1px solid var(--line);background:var(--card);color:var(--ink);font:inherit;font-size:13px;font-weight:600;cursor:pointer}.tabs button[aria-selected=true],.mf button[aria-pressed=true]{background:var(--btn);border-color:var(--btn);color:var(--btnt)}
.rows{list-style:none;margin:8px 0 0;padding:0 12px;background:var(--card);border-radius:18px;box-shadow:0 1px 0 var(--line)}.r a{display:grid;grid-template-columns:52px minmax(0,1fr);align-items:center;gap:10px;min-height:68px;padding:8px 0;border-top:1px solid var(--line);text-decoration:none}.r:first-child a{border-top:0}
.r .im{width:52px;height:52px;border-radius:12px;font-size:26px}.rt{display:flex;flex-direction:column;gap:1px;min-width:0}.l1{overflow:hidden;white-space:nowrap;text-overflow:ellipsis;font-size:14px;font-weight:600;letter-spacing:-.3px}
.l2{display:flex;align-items:baseline;gap:0 6px;overflow:hidden;white-space:nowrap;font-size:12px;color:var(--sub)}.l2 b{font-size:15.5px;font-weight:800;color:var(--ink);letter-spacing:-.5px}.l2 i{flex:none;font-style:normal;font-weight:700;color:var(--pkt)}.l2 small{overflow:hidden;text-overflow:ellipsis;font-size:12px}.tl{margin:6px 2px 0;font-size:11.5px}
.t10{list-style:none;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));grid-template-rows:repeat(5,auto);grid-auto-flow:column;gap:0 12px;margin:8px 0 0;padding:6px 12px;background:var(--card);border-radius:18px;box-shadow:0 1px 0 var(--line)}
.t10 a{display:flex;align-items:center;gap:6px;min-width:0;min-height:34px;text-decoration:none;font-size:13px;font-weight:600;letter-spacing:-.3px}.t10 span{overflow:hidden;white-space:nowrap;text-overflow:ellipsis}.t10 .n{flex:none;width:16px;text-align:center;font-weight:800;color:var(--sub)}.t10 .n.r{color:var(--acc)}.t10 .mk{margin:0;font-size:11.5px}
.more2{display:block;margin:8px 2px 0;text-align:right;color:var(--sub);font-size:13px;font-weight:700;text-decoration:none}
.hs{display:flex;gap:10px;margin:10px -16px 0;padding:0 16px 4px;overflow-x:auto;scroll-snap-type:x proximity;scrollbar-width:none}.hs::-webkit-scrollbar{display:none}.hs>.g,.hs>.hc{flex:0 0 150px;min-width:0;scroll-snap-align:start}.hs .g .im{height:96px;font-size:40px}#pick .hs>.g{flex-basis:132px}#pick .hs .g .im{height:88px}
.hc{display:flex;flex-direction:column;gap:6px}.hc .cd{color:var(--pkt);font-size:11.5px;font-weight:800;letter-spacing:-.3px}.hc>.g{flex:1}.evc{gap:4px;padding:12px;border-radius:20px;background:var(--pkbg);color:var(--ink);text-decoration:none}.evc .em{font-size:30px}.evc small{color:var(--sub);font-size:12px}
.ch{margin:22px 2px 0;font-size:17px;font-weight:800;letter-spacing:-.5px}.mt3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:10px 0 0}.mt{display:flex;flex-direction:column;justify-content:center;gap:1px;height:96px;padding:0 12px;border-radius:18px;text-decoration:none}.mt b{font-size:16px;font-weight:800;letter-spacing:-.4px}.mt small{font-size:11.5px;font-weight:600}.mt>i{font-style:normal;font-size:11.5px}
.nav a{position:relative}.nav b{position:absolute;top:4px;left:calc(50% + 6px);min-width:16px;height:16px;padding:0 4px;border-radius:8px;background:var(--accf);color:#fff;font-size:10px;line-height:16px;text-align:center}.nav b:empty{display:none}.nav .dot{position:absolute;top:7px;left:calc(50% + 7px);width:8px;height:8px;border-radius:4px;background:var(--accf)}
.chgs{margin:10px 0 0;padding:12px 14px;border-radius:14px;background:var(--pkbg);font-size:14px;font-weight:700}.g .chg{align-self:flex-start;margin:6px 2px 0;padding:2px 7px;border-radius:7px;background:var(--accf);color:#fff;font-size:11.5px;font-weight:800}
.chgb>.btn2{margin-top:14px}.chgb ul{list-style:none;margin:6px 0 0;padding:0}.chgb li a{display:flex;align-items:center;justify-content:space-between;min-height:48px;margin:6px 0 0;padding:0 14px;border-radius:14px;background:var(--card);box-shadow:0 1px 0 var(--line);text-decoration:none;font-weight:700}.chgb li b{color:var(--acc)}
@media(max-width:359px){.t6 .tile{font-size:10.5px}.t6 .tile i{width:34px;height:34px;font-size:19px}.m{font-size:12.5px}html:not(.lay-b) .sb{left:52px;right:58px}html.inapp:not(.lay-b) .sb{right:12px}}
html.lay-c:not(.inapp) .hr .ib+.ib{display:grid;margin-left:0}html.lay-c .sb{right:108px}html.lay-c .sb input{border:2px solid var(--acc)}html.lay-c .sb svg{color:var(--acc)}@media(max-width:359px){html.lay-c .sb{right:104px}}html.lay-c .evb{margin-top:6px}html.lay-c .qk{margin-top:6px}html.lay-c .q{gap:2px}html.lay-c .q i{width:42px;height:42px;font-size:20px}html.lay-c .lb~.dis{margin-top:4px!important;line-height:1.35}html.lay-c #fire{margin-top:8px}html.lay-c #fire .tabs{margin-top:6px}html.lay-c #fire .rows{margin-top:4px}html.lay-c #fire .r a{grid-template-columns:48px minmax(0,1fr);min-height:64px;padding:6px 0}html.lay-c #fire .r .im{width:48px;height:48px;font-size:24px}  /* C 혼합형(10/25): 헤더 1줄(A — 로고·검색 빨강·🔔·♡) + B 배너 + 바로가기 1줄 + 🔥 조금 촘촘히 — 390×660 첫 화면 = 배너 + 아이콘 1줄 + 🔥 4줄(아래 메뉴 위) */
.deal .s{margin:2px 0 0;font-size:12.5px;color:var(--sub)}.deal h2 a{text-decoration:none}.hero .sv,.g .sv{color:var(--acc);font-size:14px;font-weight:700}
.evb{position:relative;display:block;margin:8px 0 0}.evs{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;scrollbar-width:none;border-radius:16px}.evs::-webkit-scrollbar{display:none}.evs .ev{flex:0 0 100%;height:84px;min-height:0;border-radius:16px}.evn{position:absolute;right:10px;bottom:8px;padding:0 7px;border-radius:9px;background:rgba(20,22,27,.65);color:#fff;font-size:11px;font-weight:700;line-height:18px}.evs .ev:focus-visible,.qr .q:focus-visible,.myr .mi:focus-visible{outline-offset:-3px}
.qk{margin:10px -16px 0}.qr{display:flex;gap:4px;overflow-x:auto;padding:0 16px;scrollbar-width:none}.qr::-webkit-scrollbar{display:none}.qr+.qr{margin-top:6px}#fire{margin-top:12px}#fire .tabs{margin-top:8px}#fire .rows{margin-top:6px}
.q{position:relative;flex:0 0 max(50px,calc((min(100vw,560px) - 40px)/6.5));display:flex;flex-direction:column;align-items:center;gap:3px;min-width:0;padding-top:4px;color:var(--ink);text-decoration:none;font-size:11.5px;font-weight:600;letter-spacing:-.5px;white-space:nowrap}
.q i{display:grid;place-items:center;width:46px;height:46px;border-radius:50%;background:var(--c,var(--card));box-shadow:inset 0 0 0 1px var(--line);font-style:normal;font-size:22px;line-height:1}.q.coupang i{background:var(--cpb)}.q.toss i{background:var(--tsb)}.q.naver i{background:var(--nvb)}.q.evt i{background:var(--pkbg)}
.qb{position:absolute;top:0;left:50%;transform:translateX(-50%);padding:0 5px;border-radius:8px;background:var(--accf);color:#fff;font-size:9.5px;font-weight:800;line-height:15px;white-space:nowrap}
.myr{display:flex;gap:12px;margin:10px -16px 0;padding:2px 16px 4px;overflow-x:auto;scrollbar-width:none}.myr::-webkit-scrollbar{display:none}.mi{position:relative;flex:0 0 52px;display:flex;flex-direction:column;align-items:center;gap:4px;min-width:0;text-decoration:none}.mi .im{width:46px;height:46px;border-radius:50%;font-size:22px}.me .im{border:2px solid var(--acc);background:var(--card);color:var(--acc);font-size:13px;font-weight:800}.mi small{max-width:58px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;font-size:11.5px;color:var(--sub)}.mi b{position:absolute;top:34px;left:50%;transform:translateX(-50%);padding:0 5px;border-radius:8px;background:var(--accf);color:#fff;font-size:9.5px;font-weight:800;line-height:15px;white-space:nowrap}.mi b.d{background:#15803D}
@media(prefers-color-scheme:dark){.im,.tile i,.q i{background:color-mix(in srgb,var(--c,var(--chip)) 32%,var(--card))}.ci{--ci:#C9CED8}.like{background:rgba(26,28,33,.8);color:#9AA0AC}}
.lw{display:inline-grid;place-items:center;flex:none;width:var(--s,20px);height:var(--s,20px);margin-right:5px;border-radius:50%;background:#fff!important;box-shadow:inset 0 0 0 1px rgba(0,0,0,.1);font-style:normal;vertical-align:-5px}.lw{font-size:calc(var(--s,20px)*.56);line-height:1}.lw img{width:64%;height:64%;object-fit:contain}.lw svg{width:44%;height:44%}.q i.lw{width:46px;height:46px;margin:0}.h .lw{--s:30px;margin-right:7px;vertical-align:middle}.mt b .lw{--s:24px;vertical-align:-6px}.mt b,.tabs button{display:inline-flex;align-items:center}.tabs button .lw,.mt b .lw{vertical-align:0}
.mlg{display:inline-grid;place-items:center;flex:none;width:18px;height:18px;border-radius:50%;background:#fff;color:var(--m);font-style:normal;font-size:9.5px;font-weight:900;letter-spacing:-.5px;overflow:hidden}.mlg img{width:12px;height:12px;object-fit:contain}
.pvs{flex:none;padding:0 6px;border-radius:6px;font-size:10.5px;font-weight:800;line-height:17px;white-space:nowrap}.pvs.end{background:#E5303F;color:#fff}.pvs.on{background:#DDF5C9;color:#2F6B0F}.pvs.soon{background:#14161B;color:#fff}.pvs.past{background:var(--chip);color:var(--sub)}
.pb{margin:10px 0 0}.pbt{display:flex;justify-content:space-between;align-items:baseline;margin:0 2px 8px}.pbt h2{margin:0;font-size:16px;font-weight:800}.pbt a{font-size:12.5px;font-weight:700;color:var(--sub);text-decoration:none}
.pbs{display:flex;gap:8px;overflow-x:auto;scroll-snap-type:x mandatory;scrollbar-width:none;margin:0 -16px;padding:0 16px;scroll-padding:0 16px}.pbs::-webkit-scrollbar{display:none}
.pbi{position:relative;flex:0 0 250px;height:112px;box-sizing:border-box;display:flex;flex-direction:column;padding:11px 13px;border-radius:16px;background:var(--m);color:var(--mf);text-decoration:none;overflow:hidden;scroll-snap-align:start}
.pbi::after{content:"";position:absolute;right:-30px;top:-34px;width:104px;height:104px;border-radius:50%;border:16px solid currentColor;opacity:.12;pointer-events:none}
.pbh{display:flex;align-items:center;gap:5px;font-size:11.5px;font-weight:800;min-width:0}.pbh b:first-of-type{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pbw{margin-top:7px;font-size:25px;font-weight:900;line-height:1.05;letter-spacing:-.6px;white-space:nowrap}.pbn{margin-top:4px;font-size:13.5px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.pbx .pbn{max-width:132px}.pbi .pvs.end{background:#fff;color:#E5303F}
.pbp{position:absolute;right:12px;bottom:11px;display:flex;flex-direction:row-reverse}.pbp img{width:38px;height:38px;margin-left:-10px;border-radius:50%;border:2px solid var(--m);background:#fff;object-fit:contain}
.pbd{display:flex;justify-content:center;gap:5px;margin-top:8px}.pbd i{width:6px;height:6px;border-radius:3px;background:var(--line);transition:width .2s}.pbd i.on{width:14px;background:var(--ink)}
.pcal{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;margin:12px -16px 0;padding:0 16px}.pcal::-webkit-scrollbar{display:none}
.pcd{flex:none;display:flex;flex-direction:column;gap:1px;min-width:78px;max-width:128px;padding:7px 10px;border-radius:12px;background:var(--card);box-shadow:inset 0 0 0 1px var(--line);color:var(--ink);text-decoration:none}
.pcd b{font-size:12.5px;font-weight:800;white-space:nowrap}.pcd span{font-size:11px;color:var(--sub);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.pcd i{font-style:normal;font-size:10.5px;font-weight:800;color:var(--acc)}
.pcd.k{background:#14161B;box-shadow:none;color:#fff}.pcd.k span{color:#C9CED8}.pcd.k i{color:#FF8A8F}
.pf{display:flex;gap:6px;margin:12px 0 10px}.pf button{font:inherit;font-size:12.5px;font-weight:700;padding:6px 12px;border-radius:16px;border:0;box-shadow:inset 0 0 0 1px var(--line);background:var(--card);color:var(--ink);cursor:pointer}.pf button[aria-pressed=true]{background:var(--btn);color:var(--btnt);box-shadow:none}
.pv{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;align-items:center;min-height:110px;box-sizing:border-box;margin:0 0 8px;padding:11px 12px;border-radius:16px;background:var(--mb,color-mix(in srgb,var(--m) 7%,var(--card)))}
.pvh{display:flex;align-items:center;gap:5px;min-width:0}.pvm{font-size:11.5px;font-weight:800;color:var(--mt);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pvn{margin:5px 0 0;font-size:15.5px;font-weight:800;line-height:1.3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.pvi{margin:2px 0 0;font-size:11.5px;color:var(--sub);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pvc{display:inline-block;margin-top:6px;font-size:11.5px;font-weight:800;color:var(--mt);text-decoration:none}.pvr{display:flex;gap:5px}
.pvp{display:flex;flex-direction:column;align-items:center;gap:2px;width:48px}.pvp>span{display:grid;place-items:center;width:48px;height:48px;border-radius:10px;background:#fff;overflow:hidden}.pvp img{width:44px;height:44px;object-fit:contain}.pvp small{font-size:10px;font-weight:700;color:var(--ink);white-space:nowrap}
.pvd{min-width:84px;padding:8px 10px;border-radius:12px;background:#fff;text-align:center}.pvd b{display:block;font-size:17px;font-weight:800;color:var(--mt);white-space:nowrap}.pvd small{display:block;margin-top:2px;font-size:10px;color:#6B7180;white-space:nowrap}
.pvx summary{padding:8px 2px;font-size:13px;color:var(--sub);cursor:pointer}.pvx .pv{opacity:.72}.pvnote{margin-top:14px}
@media(prefers-color-scheme:dark){.pv{background:color-mix(in srgb,var(--m) 14%,var(--card))}.pvm,.pvc,.pvd b{color:color-mix(in srgb,var(--m) 62%,#fff)}.pvd{background:var(--chip)}.pvd small{color:var(--sub)}.pcd.k{background:#ECEEF2;color:#14161B}.pcd.k span{color:#4B5260}.pcd.k i{color:#C2202C}}"""
MASK = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.75' stroke-linecap='round' stroke-linejoin='round'>%s</svg>"
CSS += "".join('.ci%s{--m:url("data:image/svg+xml,%s")}' % ("-" + k if k else ",.ci-x", urllib.parse.quote(MASK % v.replace('"', "'"), safe="")) for k, v in sorted(CAT_ICON.items(), key=lambda kv: kv[0] != ""))  # 모르는 .ci-키(옛 검색 색인 이모지 등) = 쇼핑백(회색 네모 X)  # 품목 선 아이콘 = s.css 마스크 1번(쪽마다 SVG X — 홈 크기)
CV = "?v=" + hashlib.md5(CSS.encode()).hexdigest()[:8]  # /s.css 주소에 내용 해시 — CSS 바뀐 배포만 새로 받음(서비스워커 = .css 캐시 먼저)
FONT_HEAD = '<link rel="preload" href="/fonts/hdpsans-v1.woff2" as="font" type="font/woff2" crossorigin>'  # 10/24 개편 글꼴 = Pretendard 줄인 판 'HDP Sans'(docs/fonts, OFL.txt — 이름은 OFL 예약 이름 규칙대로 바꿈) 1개 파일(317KB, 굵기 400~800) — 바꾸면 v2로(서비스워커 글꼴 캐시는 이름이 안 바뀌면 그대로 씀)

def to_html(text, entities):
    """텔레그램 text + text_link 엔티티(UTF-16 오프셋) -> HTML."""
    u, out, pos = text.encode("utf-16-le"), [], 0
    for e in sorted((e for e in entities or [] if e.get("type") == "text_link"), key=lambda e: e["offset"]):
        s, n = e["offset"] * 2, (e["offset"] + e["length"]) * 2
        out.append(html.escape(u[pos:s].decode("utf-16-le")))
        out.append(f'<a href="{html.escape(e["url"])}" rel="nofollow {"sponsored " if aff(e["url"]) else ""}noopener" target="_blank">'
                   f'{html.escape(u[s:n].decode("utf-16-le"))}</a>')
        pos = n
    out.append(html.escape(u[pos:].decode("utf-16-le")))
    return "".join(out).replace("\n", "<br>")


NOTE_STARTS = ("이 포스팅은", "이 콘텐츠는", "[광고]")  # 대가성 문구 줄 시작(쿠팡·링크프라이스·네이버 = 이 포스팅은, 토스 = 이 콘텐츠는)
MALL_HEAD = re.compile(r"(💙 토스(?: 특가)?|🚀 쿠팡(?: 로켓)?|📦 쿠팡)(?: · [^\n]*)? ([🔥🛒👍])$")  # 👍 = 꾸준템(10/22 20:0x 진우) · 10/22 진우 '토스·쿠팡 한눈에': 몰별 개별 글 머리 줄 -> 다음 줄 상품명, 그다음 줄 가격  # 10/24 17:5x 진우: 토스 꾸준템(👍, 특가 아님) = '💙 토스 · 꾸준히 팔리는 상품 👍'(특가 글은 '💙 토스 특가 · …' 그대로)
MALL_TAG = {"💙 토스 특가": "토스", "💙 토스": "토스", "🚀 쿠팡 로켓": "쿠팡", "🚀 쿠팡": "쿠팡", "📦 쿠팡": "쿠팡"}  # 로켓 근거 없는 쿠팡 딜 = '📦 쿠팡'(10/22 진우 '사실 아닌 표기 X' · 10/23 🚀 -> 📦, 그 전 글 '🚀 쿠팡'도 읽음)


def mall_title(lines, i):
    """lines[i]가 몰별 머리 줄이면 '[몰] 상품명 (가격)'(예전 제목 모양 — 사이트·카드·리스트가 그대로 읽게), 아니면 None.
    가격 = 셋째 줄 금액(' → 1개 …'·' (60%↓)' 앞) + 나머지 ' · ' 조각(쿠폰가·회원가 등, ⭐ 평점 X) + 배송 조각(' · 무료' -> '/무료', 카드 배송 칸) = 예전 제목 가격 그대로."""
    m = MALL_HEAD.fullmatch(lines[i])
    if not m or len(lines) < i + 3 or not lines[i + 1].strip():
        return None
    seg = [s.strip() for s in lines[i + 2].split(" · ")]
    ship = next((s for s in seg[1:] if re.search(r"무료|무배|배송", s) and not s.startswith("⭐")), "")
    price = " · ".join([re.split(r" → | \(\d+%↓\)| \(\d{1,2}/\d{1,2} \d{1,2}시 확인\)", seg[0])[0].strip()] + [s for s in seg[1:] if s and s != ship and not s.startswith("⭐") and not re.match(r"(?:한 달|리뷰) ", s)]) + (f"/{ship}" if ship else "")
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


MY = '<section class="sec" id="my" aria-labelledby="myh" hidden><h2 id="myh"><span>♡ 내가 찜·본 딜</span></h2><div class="myr" id="myr"></div></section>'  # 홈 🔥 아래(포털형 2차 ④) — 비면 숨김, MY_JS가 채움
MY_JS = """<script>(function(){var r=document.getElementById('myr'),A=[];try{A=(JSON.parse(localStorage.getItem('likes'))||[]).concat(JSON.parse(localStorage.getItem('seen'))||[])}catch(e){}if(!r||!A.length)return;
function draw(j){var C=j&&j.items||{},a=j&&j.a||{},u={},o=[],t=document.createElement('template');A.forEach(function(x){var k=x&&(a[x.i]||x.i),c=k&&C[k],b=!c?'':c.k.indexOf('deadline')>=0?'⏰ 오늘':c.k.indexOf('drop')>=0?'▼'+c.p+'%':c.k.indexOf('rehot')>=0?'🔁':'',m,e,s;if(!k||u[k])return;
t.innerHTML=x.h||x.im||'';m=t.content.querySelector('.im');if(!m)return;u[k]=1;[].forEach.call(m.querySelectorAll('.bdg'),function(z){z.remove()});
e=document.createElement('a');e.className='mi';e.href='/p/'+k+'.html';e.setAttribute('data-gc','my/'+(b?'chg':'p'));e.appendChild(m);if(b){s=document.createElement('b');s.textContent=b;if(b[0]==='▼')s.className='d';e.appendChild(s)}
s=document.createElement('small');s.textContent=x.n||(t.content.querySelector('h3')||{}).textContent||'';e.appendChild(s);o.push([b?0:1,o.length,e])});
o.sort(function(p,q){return p[0]-q[0]||p[1]-q[1]});r.innerHTML='<a class="mi me" href="/saved/" data-gc="my/saved"><span class="im">MY</span><small>찜 전체</small></a>';o.slice(0,12).forEach(function(x){r.appendChild(x[2])});if(!r.parentNode.dataset.sh)r.parentNode.hidden=!o.length}
draw();window.hdpMy=draw})()</script>"""  # ♡ 내가 찜·본 딜: likes(카드 HTML)·seen(딜 쪽 썸네일) — 바뀐 것(⏰ 오늘·▼N%·🔁, changes.json은 DOT_JS가 받아 hdpMy(j)) 먼저, 12개 · 저장소 막힘·비었음 = 숨김
SEEN_JS = """<script>(function(){try{var d=document.querySelector('.deal'),i=(location.pathname.match(/(\\d+)(?:\\.html)?$/)||[])[1],S;if(!d||!i)return;S=JSON.parse(localStorage.getItem('seen'))||[];
localStorage.setItem('seen',JSON.stringify([{i:i,n:d.querySelector('.dn').textContent,im:d.querySelector('.im').outerHTML}].concat(S.filter(function(x){return x&&x.i!==i})).slice(0,20)))}catch(e){}})()</script>"""  # 딜 쪽 본 기록(최근 20개 — 홈 ♡ 내가 찜·본 딜)


def page(title, body, desc="", canonical="", note="", top="", head="", cur="", og="", noindex=False, kind="website", lead="", dis="", ogt=""):
    """모든 쪽 틀(10/24 진우 개편 A → 포털형 2차 N+스토어): 헤더 = 로고 + 핫딜픽 + 🔔 + ♡(위로 밀리면 사라짐) / 검색칸(빨강 2px — 위에 붙어 있음) + lead(홈 = 기획전 넘김 배너·둥근 바로가기 2줄) + 대가성 문구(dis = 홈 짧은 문구) + 본문 + 아래 메뉴 5개(🔔 = 찜 변경 빨간 점 — 선 아이콘 그대로)."""
    t, d = html.escape(title), html.escape(desc[:150])
    nav = '<nav class="nav" aria-label="메뉴">' + "".join(f'<a href="{u}"' + (' aria-label="찜한 딜 보기"' if k == "saved" else "") + (' aria-current="page"' if k == cur else "") + f">{svg(k)}{n}"
                                                       + ('<b id="lc"></b>' if k == "saved" else '<i class="dot" id="adot" role="img" aria-label="찜한 딜 바뀜" hidden></i>' if k == "alarm" else "") + "</a>" for k, n, u in NAV) + "</nav>"
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{t}</title><meta name="description" content="{d}">{'<meta name="robots" content="noindex,follow">' if noindex else ''}
{"".join(f'<meta name="naver-site-verification" content="{v}">' for v in NAVER_VERIFY)}{f'<meta name="google-site-verification" content="{html.escape(GOOGLE_VERIFY)}">' if GOOGLE_VERIFY else ""}
<meta property="og:site_name" content="{TITLE}"><meta property="og:title" content="{html.escape(ogt) if ogt else t}"><meta property="og:description" content="{d}"><meta property="og:type" content="{kind}"><meta property="og:locale" content="ko_KR"><meta property="og:image" content="{html.escape(og or BASE + 'og.png')}">{'' if og else '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'}<meta name="twitter:card" content="summary_large_image">
{f'<meta property="og:url" content="{canonical}"><link rel="canonical" href="{canonical}">' if canonical else ''}<link rel="alternate" type="application/rss+xml" title="{TITLE}" href="{BASE}rss.xml">{PWA_HEAD}<link rel="stylesheet" href="/s.css{CV}">{FONT_HEAD}{INAPP_JS}{LAYOUT_JS}{gc_tag()}{head}</head><body><main>
<header class="hd"><div class="hr"><a class="lg" href="{BASE}" aria-label="{TITLE} 홈"><span class="logo" aria-hidden="true">딜</span>{"<b>" + TITLE + "</b>" if "<h1" in body else "<h1>" + TITLE + "</h1>"}</a><a class="ib" href="{BASE}alarm/" aria-label="알림 받기" data-gc="hd/alarm">{svg("alarm")}</a><a class="ib" href="{BASE}saved/" aria-label="찜 목록 열기" data-gc="hd/saved">{svg("saved")}</a></div><form class="sb" role="search" action="{BASE}">{svg("search")}<input id="q" name="q" type="search" placeholder="상품명 또는 브랜드 — 휴지, 라면, 가습기" aria-label="딜 검색" autocomplete="off" enterkeyhint="search"></form>{nav}</header>
{top}{lead}<p class="dis"{' style="font-size:10.5px;margin-top:6px"' if dis else ""}>{html.escape(note) + "<br>" if note else ""}{dis or DISCLOSURE}</p>{body}
<footer>딜 정보는 게시 시점 기준이며 가격·재고는 변동될 수 있어요.<br><a href="{BLOG}">네이버 블로그</a> · <a href="{INSTA}">인스타그램</a> · <a href="{THREADS}">Threads</a> · <a href="{CHANNEL}">텔레그램</a></footer></main>{TB}{LIKE_JS}{SEARCH_JS}{END_JS}{DOT_JS}</body></html>"""


SEARCH_JS = """<script>(function(){var q=document.getElementById('q');if(!q)return;var D=null,sr=null,tm=0,M=document.querySelector('main'),H='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>';
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function card(x){return "<article class='g'><button class='like' type='button' data-i='"+x.i+"' aria-pressed='false' aria-label='"+esc(x.n)+" 찜'>"+H+"</button><div class='im' style='--c:"+esc(x.c)+"'><i class='ci ci-"+esc(x.m||'x')+"' aria-hidden='true'></i>"+(x.g?"<img src='"+esc(x.g)+"' alt='' loading='lazy' referrerpolicy='no-referrer' onerror='this.remove()'>":"")+(x.b||"")+"</div><span class='mc'>"+esc(x.s)+"</span><h3><a href='/p/"+x.i+".html'>"+esc(x.n)+"</a></h3>"+(x.p?"<div class='pr'>"+esc(x.p)+"</div>":"")+(x.e?"<div class='ex'>"+esc(x.e)+"</div>":"")+(x.u?"<div class='u'>"+esc(x.u)+"</div>":"")+"</article>"}
function hide(on){[].forEach.call(M.children,function(e){if(/^(HEADER|FOOTER|SCRIPT)$/.test(e.tagName)||e.id==='sr'||e.className==='dis')return;if(on){if(!e.hidden){e.hidden=true;e.dataset.sh=1}}else if(e.dataset.sh){e.hidden=false;delete e.dataset.sh}})}
function go(v){return /가격\\s*내림|내려간|^내림$/.test(v)?'/c/drop/':/마감/.test(v)?'/c/today/':''}
function run(){var v=q.value.trim().toLowerCase();if(!v){if(sr){sr.remove();sr=null}hide(false);return}
if(!D){fetch('/search.json').then(function(r){return r.json()}).then(function(j){D=j;run()}).catch(function(){});return}
var w=v.split(/\\s+/),r=D.filter(function(x){return w.every(function(k){return x.k.indexOf(k)>=0})});
if(!sr){sr=document.createElement('section');sr.id='sr';sr.className='sec';M.querySelector('.dis').insertAdjacentElement('afterend',sr);scrollTo(0,0)}hide(true);
var g=go(v);sr.innerHTML="<h2>검색 결과</h2>"+(g?"<a class='btn2' href='"+g+"'>"+(g==='/c/drop/'?'📉 가격 내려간 상품 보기 →':'⏰ 오늘 마감 보기 →')+"</a>":'')+"<p id='qn' class='t' role='status'>"+(r.length?r.length+'개 찾았어요':'찾는 딜이 없어요 · 다른 말로 찾아보세요')+"</p>"+(r.slice(0,60).some(function(x){return x.s==='토스'})?"<p class='t'>토스 가격 = 올린 날 가격 · 지금 가격은 링크에서 확인</p>":'')+(r.length?"<div class='cards'>"+r.slice(0,60).map(card).join('')+"</div>":'');if(window.hdpLike)hdpLike()}
q.addEventListener('input',function(){clearTimeout(tm);tm=setTimeout(run,120)});q.form.addEventListener('submit',function(e){e.preventDefault();q.blur();var g=go(q.value.trim().toLowerCase());if(g)return location.assign(g);run()});
var u=new URLSearchParams(location.search).get('q');if(u){q.value=u;run()}})()</script>"""  # 10/24 개편: 홈이 TOP 4만 담아서 검색은 사이트 색인(search.json, 진열 상품 전부 — 처음 입력 때 1번 받음) — 🔥 먼저(목록 순서 그대로)·같은 상품 1번, 결과는 그 쪽 본문 자리에(지우면 그대로)


ALIAS = lambda name: " ".join(w for r, w in ((r"화장지|두루마리|키친타[월올]|각티슈|미용티슈", "휴지"), (r"세제|섬유유연제", "빨래"), (r"햇반|즉석밥", "밥")) if re.search(r, name))  # 검색 다른 말(검색칸 예시 '휴지' = 상품 이름은 화장지)


PWA_BG, PWA_DARK = "#F6F7F9", "#0F1013"  # 사이트 바탕(CSS body·다크) = 앱 실행 화면·상단 줄 색
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
SW_JS = r"""var V='hdp-%s',F='hdp-font-1',PRE=['/','/s.css{CV}','/icons/icon-192.png{IV}','/icons/icon-512.png{IV}','/icons/apple-touch-icon.png{IV}','/favicon.ico{IV}'];
self.addEventListener('install',function(e){e.waitUntil(caches.open(V).then(function(c){return c.addAll(PRE)}).then(function(){return self.skipWaiting()}))});
self.addEventListener('activate',function(e){e.waitUntil(caches.keys().then(function(ks){return Promise.all(ks.filter(function(k){return k!==V&&k!==F}).map(function(k){return caches.delete(k)}))}).then(function(){return self.clients.claim()}))});
self.addEventListener('fetch',function(e){var r=e.request,u=new URL(r.url);
if(r.method!=='GET'||u.origin!==location.origin)return;
if(/^\/icons\/|^\/favicon\.ico$|\.(css|woff2?|otf|ttf)$/.test(u.pathname)){e.respondWith(caches.match(r).then(function(c){return c||fetch(r).then(function(res){if(res.ok){var x=res.clone();caches.open(/\.woff2?$/.test(u.pathname)?F:V).then(function(k){k.put(r,x)})}return res})}));return}
e.respondWith(fetch(r).then(function(res){if(res.ok&&r.mode==='navigate'){var x=res.clone();caches.open(V).then(function(k){k.put(r,x)})}return res}).catch(function(){return caches.match(r).then(function(c){return c||(r.mode==='navigate'?caches.match('/'):Response.error())})}))});
""".replace("{IV}", IV).replace("{CV}", CV)  # 웹앱 서비스워커(최소): 같은 출처 GET만 — 쿠팡·토스·네이버·제휴 리다이렉트·GoatCounter는 안 건드림 · 아이콘·폰트·CSS = 캐시 먼저 · HTML·딜 데이터 = 네트워크 먼저(옛 가격 X, 오프라인일 때만 저장해 둔 쪽) · V = 배포(홈 내용)마다 바뀜 -> 옛 캐시 지움
INSTALL = ('<div class="inst" id="inst" hidden><span id="instt"></span><button type="button" id="instb">📲 앱으로 설치</button><button type="button" id="instx" aria-label="닫기">✕</button></div>'
           "<script>(function(){var b=document.getElementById('inst'),t=document.getElementById('instt'),ok=document.getElementById('instb'),ev=null,ua=navigator.userAgent,ios=/iPhone|iPad|iPod/.test(ua)||/Macintosh/.test(ua)&&navigator.maxTouchPoints>1;"
           "if(matchMedia('(display-mode: standalone)').matches||navigator.standalone)return;try{if(Date.now()-(+localStorage.getItem('instx')||0)<6048e5)return}catch(e){}"
           "var v=0;try{if(!sessionStorage.getItem('hv')){sessionStorage.setItem('hv','1');localStorage.setItem('hv',(+localStorage.getItem('hv')||0)+1)}v=+localStorage.getItem('hv')||0}catch(e){}if(v<2)return;"  # 10/24 Cowork: 첫 방문엔 X, 두 번째 방문부터 아래쪽 얇은 띠
           "function show(m,btn){t.innerHTML=m;ok.hidden=!btn;if(!scrollY&&location.pathname=='/')return addEventListener('scroll',function(){show(m,btn)},{once:true});b.hidden=false}"  # 홈 첫 화면(🔥 2줄↑ — 390×660)은 안 가림 -> 처음 밀 때 띠(2차 리뷰)
           "document.getElementById('instx').onclick=function(){b.hidden=true;try{localStorage.setItem('instx',Date.now())}catch(e){}};"
           "if(document.documentElement.classList.contains('inapp')||/Telegram|; wv\\)/.test(ua)||ios&&!/Safari\\//.test(ua))return show('📲 크롬·사파리에서 열면 앱으로 설치할 수 있어요',0);"
           "if(ios)return show('📲 앱으로 설치: <b>공유</b>(⬆︎ · 안 보이면 <b>···</b> 안)<br>→ <b>홈 화면에 추가</b>',0);"
           "addEventListener('beforeinstallprompt',function(e){e.preventDefault();ev=e;show('홈 화면에서 바로 열기',1)});"
           "ok.onclick=function(){if(!ev)return;ev.prompt();ev.userChoice.then(function(){ev=null;b.hidden=true})};addEventListener('appinstalled',function(){b.hidden=true;show=function(){}})})()</script>")  # 홈 맨 위 작게: 안드로이드 크롬 = 바로 설치, 아이폰·아이패드 = 2줄 안내(공유 위치는 브라우저마다 달라 안 씀), 앱 안 브라우저(.inapp·텔레그램·안드로이드 WebView·사파리 아닌 iOS 앱) = 브라우저 안내만, 설치됨 = 숨김, 닫으면 7일 X
LAYOUT_JS = "<script>(function(){var l;try{l=localStorage.getItem('hp_layout');if(!/^[abc]$/.test(l)){l='abc'.charAt(Math.floor(Math.random()*3));localStorage.setItem('hp_layout',l);localStorage.setItem('hp_lc','3')}}catch(e){l='a'}document.documentElement.classList.add('lay-'+l)})();addEventListener('pageshow',function(e){if(e.persisted)try{var l=localStorage.getItem('hp_layout'),d=document.documentElement;if(/^[abc]$/.test(l)){d.classList.remove('lay-a','lay-b','lay-c');d.classList.add('lay-'+l)}}catch(x){}})</script>"  # 홈 윗부분 A 목록형(1차)·B 아이콘형(2차)·C 혼합형(10/25 진우 '둘의 장점을 합친 화면' = B 헤더·배너 + 바로가기 1줄 + A 🔥) — 첫 방문 무작위 1/3(이미 고른·배정된 A·B는 그대로), 저장소 막힘 = A(10/24 Cowork·진우 '고객이 선택')
LSW = '<div class="lsw" role="group" aria-label="화면 고르기">화면:' + "".join(f'<button type="button" data-l="{l}" data-gc="layout/switch/{l.upper()}" aria-pressed="false">{n}</button>' for l, n in (("a", "목록형"), ("b", "아이콘형"), ("c", "혼합형"))) + "</div>"
LSW_JS = """<script>(function(){var B=document.querySelectorAll('.lsw button');function cur(){var c=document.documentElement.classList;return c.contains('lay-b')?'b':c.contains('lay-c')?'c':'a'}
function sync(){[].forEach.call(B,function(b){b.setAttribute('aria-pressed',b.dataset.l===cur())})}sync();addEventListener('pageshow',sync);
[].forEach.call(B,function(b){b.addEventListener('click',function(e){var d=document.documentElement,n=b.dataset.l;if(n===cur())return e.stopPropagation();d.classList.remove('lay-a','lay-b','lay-c');d.classList.add('lay-'+n);try{localStorage.setItem('hp_layout',n)}catch(e){}sync();
if(document.querySelector('main > .la'))scrollTo(0,0)})})})()</script>"""  # 화면: 목록형 · 아이콘형 · 혼합형(지금 화면 = 눌림) — 고르면 기억(막히면 이 쪽에서만) · 홈 = 윗부분이 바뀌니 맨 위로 · GoatCounter layout/switch/A·B·C
TB = ('<div class="tb" hidden><button type="button" data-gc="nav/top" aria-label="맨 위로"><svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M6 14l6-6 6 6"/></svg>TOP</button>'
      '<button type="button" data-gc="nav/end" aria-label="맨 아래로"><svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M6 10l6 6 6-6"/></svg>END</button></div>'
      "<script>(function(){var b=document.querySelector('.tb'),u=b.children[0],d=b.children[1],R=matchMedia('(prefers-reduced-motion: reduce)'),E=document.documentElement;"
      "function f(){var y=scrollY,h=innerHeight,i=document.getElementById('inst'),t;b.hidden=y<h;d.style.visibility=y+h>E.scrollHeight-160?'hidden':'';b.style.bottom='';"
      "if(!b.hidden&&i&&!i.hidden&&(t=i.getBoundingClientRect().top)<b.getBoundingClientRect().bottom+8)b.style.bottom=(h-t+8)+'px'}"  # 설치 띠가 글자 크기 등으로 높아도 그 위로(10/25 리뷰)
      "addEventListener('scroll',f,{passive:true});addEventListener('resize',f);f();"
      "function go(t){scrollTo({top:t,behavior:R.matches?'auto':'smooth'})}u.onclick=function(){go(0);var l=document.querySelector('.lg');if(l)l.focus({preventScroll:true})};d.onclick=function(){go(E.scrollHeight);u.focus({preventScroll:true})}})()</script>")  # TOP/END(10/25 진우 '맨 위로 올라가는 버튼 — 있으면 의외로 좋더라'): 모든 쪽 오른쪽 아래(아래 메뉴·설치 띠 위 · 앱 안 브라우저 = 앱 툴바 위) · 100vh 넘게 내렸을 때만 · 맨 아래 근처 = ↓ 숨김(자리는 그대로 — 두 번 눌러 ↑로 X) · 누른 뒤 초점 = ↑·로고 · 움직임 줄이기 = 바로 · GoatCounter nav/top·nav/end
INAPP_JS = "<script>if(/Barcelona|Instagram|FBAN|FBAV|KAKAOTALK|NAVER\\(inapp|Line\\/|DaumApps/i.test(navigator.userAgent))document.documentElement.classList.add('inapp')</script>"  # 10/13 진우: 앱 안 브라우저(Threads=Barcelona·인스타·페북·카톡·네이버 등)는 아래 고정 바가 앱 툴바에 가려서 -> 검색창 아래 한 줄 메뉴 + 아래 여백
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


SITE_AFF_ONLY = True  # 10/26 SS 진우 '수익 안 주는 제품은 과감하게 빼고'(10/25 '품목은 무조건 다 올려'보다 먼저) = 수수료 링크만 — False = 예전처럼 모든 딜(셀프체크 옛 가짜 주소용)
SITE_KEEP_HOSTS = ("coupang.com", "auction.co.kr", "gmarket.co.kr", "lotteon.com", "emart.ssg.com",  # 기획전 몰 바로 가기(promo_link) = 수수료 길이 있는 몰 주소 — 딜 카드는 site_ok(수수료 링크만)
                   "ppomppu.co.kr", "shopping.naver.com", "brand.naver.com", "smartstore.naver.com")


def keep_host(url):
    """SITE_KEEP_HOSTS 주소(하위 도메인 포함)인지."""
    h = urllib.parse.urlsplit(url or "").netloc.lower()
    return any(h == k or h.endswith("." + k) for k in SITE_KEEP_HOSTS)


def site_ok(p):
    """사이트(목록·칸·검색·RSS·사이트맵)에 보일 딜 = 수수료 링크만(aff — 쿠팡 파트너스·토스 쉐어링크·네이버 쇼핑커넥트 naver.me·올리브영 oy.run·링크프라이스, 10/26 SS)
    / 그 밖(쿠팡 변환 전·400 생 주소·네이버 직접·뽐뿌 원글·11번가 등) = 사이트 X — 데이터 그대로(빌드에서만 숨김: 나중에 수수료 링크로 바뀌면 다시 보임) · 채널 옛 글 그대로."""
    return not p.get("nosite") and (not SITE_AFF_ONLY or aff(p.get("url")))  # nosite = link_swap 'none'(진우가 쇼핑커넥트 '참여 안 함' 확인, 10/25 21:4x)


CARD_N = 5  # 카드 한 장에 들어가는 딜 수 = 인스타 캡션·사이트 맨 위 번호 수(10/11 — 카드 5·캡션 6·사이트 6으로 어긋나던 것)
STEM = re.compile(r"(\d{4}-\d{2}-\d{2})(?:_(\d{2}))?")  # 카드 이름: 하루 카드 = 날짜, 시간대 카드(10/11~ · 10/23 11·13·15·17·19시) = 날짜_시(두 자리)
SLOT_NAMES = {"09": "오전 9시", "11": "오전 11시", "13": "낮 1시", "15": "오후 3시", "17": "오후 5시", "19": "저녁 7시", "12": "낮 12시", "18": "저녁 6시"}  # 시간대 카드 이름(hotdeal.IG_SLOTS와 같은 시각 + 10/23 전 칸 이름)


def day_deals(posts, day):
    """그날 딜의 카드 순서 [(posts 번호, 글)]: 점수 높은 순, 같은 점수면 제휴 링크 딜 먼저(10/8 진우 '쿠팡·토스 잘 팔리게'), 그다음 게시 순.
    카드·인스타 캡션·사이트 맨 위 카드 딜(앞 CARD_N개)·릴스(앞 3개) 번호가 모두 이 순서."""
    ds = [(i, p) for i, p in enumerate(posts) if p["t"].startswith(day) and not p["text"].startswith("📋") and not p.get("shelf") and parse(title_of(p["text"]))[2]]  # 사이트 진열(shelf) = 카드·인스타·릴스·Threads X · HH: 가격 못 읽은 딜 = 카드 X(다음 딜로)
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


CARD_NAMES = "docs/cards/names.json"  # 인스타 피드 카드 이름(hotdeal.card_names_put — 10/26 H·L: 테마·형식 제목 · c/칸 slug)


def card_names():
    try:
        m = json.load(open(CARD_NAMES))
        return m if isinstance(m, dict) else {}
    except (OSError, ValueError):
        return {}


def card_name(stem):
    """사이트 맨 위 카드 칸 이름 '10월 12일 낮 12시 카드 딜' / 하루 카드 '10월 12일 카드 딜' / 인스타 피드 카드(names.json) '10월 26일 {제목}' — 인스타·Threads 캡션이 이 이름 그대로 가리킴."""
    t = (card_names().get(stem) or {}).get("title")
    return f"{int(stem[5:7])}월 {int(stem[8:10])}일 " + (t if t else (SLOT_NAMES.get(stem[11:], stem[11:] + "시") + " " if len(stem) > 10 else "") + "카드 딜")


def ig_top(posts, out, now_ts):
    """I-2(10/26): IG_TOP 채움 — c/칸 맨 위 = 그 칸 최근 인스타 구매 링크 게시물(theme·one·top · 가격 맞히기는 정답 뒤) 1~N번(인스타 번호 = 사이트 번호) ·
    인스타에 올린(ig.json) 어제·오늘 피드 카드, 칸마다 최근 3개 따로(최근 것 위 — 앞 글 댓글 번호도 그대로)."""
    IG_TOP.clear()
    live, since = (set(json.load(open(f"{out}/cards/ig.json"))) if os.path.exists(f"{out}/cards/ig.json") else set()), time.strftime("%Y-%m-%d", time.gmtime(now_ts + 9 * 3600 - 86400))
    for x, v in sorted(card_names().items(), reverse=True):
        if isinstance(v, dict) and v.get("slug") and (v.get("kind") in ("theme", "one", "top") or v.get("ans")) and x in live and x[:10] >= since and (ps := card_order(posts, x, out)[:CARD_N]):
            xs = IG_TOP.setdefault(v["slug"], [])
            if len(xs) < 3:
                xs.append((card_name(x), ps))


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


def pick_name(p):
    """카드 딜 줄 이름 '[몰] 상품명'(가격은 오른쪽 칸 — 이름은 2줄까지만, 사진이 들어가도 줄 높이 그대로 · 10/25 진우 '칸 더 안 잡아먹게')."""
    st, nm, _ = parse(title_of(p["text"]))
    return (f"[{st}] " if st else "") + nm if nm else title_of(p["text"])


def pick_rows(picks):
    """카드 딜 번호 버튼들(누르면 구매 주소 바로, 원글 딜은 같은 상품 찾기도) · 사이트에서 뺀 딜(site_ok X — 10/25 리뷰) = 번호·이름만(링크 X — 카드 번호는 그대로) · sponsored = 제휴 링크만."""
    return "".join((f'<a class="pick" aria-disabled="true"><b>{n:02d}</b><span>{html.escape(title_of(p["text"]))}</span><em>채널에서</em></a>' if not site_ok(p) else
                    f'<a class="pick" href="{html.escape(f"{BASE}p/{i}.html" if urllib.parse.urlsplit(p.get("url") or "").netloc in OY_HOSTS else p.get("url") or f"{BASE}p/{i}.html")}" rel="nofollow {"sponsored " if aff(p.get("url")) else ""}noopener" target="_blank" '
                   f'aria-label="{n}번 {html.escape(title_of(p["text"]))} {"원글에서 구매 링크 보기" if community(p.get("url")) else "구매하러 가기"}">'
                   f'<b>{n:02d}</b>' + (f'<img class="pt" src="{html.escape(u)}" alt="" width="40" height="40" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="this.remove()">' if (u := img_of(p)) else "")  # 10/25 진우 '사진도 작게, 칸 더 안 잡아먹게'(사진 없으면 번호만)
                   + f'<span>{html.escape(pick_name(p))}</span><em>' + (f'<i>{html.escape(pr)}</i>' if (pr := parse(title_of(p["text"]))[2].split("/")[0].strip()) else "") + f'{"원글 →" if community(p.get("url")) else "구매 →"}</em></a>'
                   + (f'<a class="alt" href="{html.escape(find_url(title_of(p["text"])))}" rel="nofollow noopener" target="_blank">🔎 {n}번 원글이 안 열리면 같은 상품 찾기</a>'
                      if community(p.get("url")) else ""))
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
    return ([("b4", "🏆 인기")] if p.get("hot") else []) + ([("b1", "✅ 본사 정품")] if p.get("tag") == "정품" else []) + ([("b2", "⏰ 오늘 밤 12시 마감")] if day_end(p, today) else []) \
        + ([("b3", "🛒 약한 딜")] if "특가로는 약한 제품" in p["text"] else [])


def day_end(p, today):
    """오늘 밤 12시에 끝나는 딜(10/24 Cowork '오늘 마감'): 오늘 올린 글 중 '밤 12시까지' 또는 토스 하루특가·선착순(커뮤니티 '선착순 쿠폰' 같은 다른 몰 X) — 확인 뒤 대기(st wait·out)면 X."""
    return p.get("t", "")[:10] == today and p.get("st", "hot") == "hot" and ("밤 12시까지" in p["text"] or shop_of(p) == "toss" and bool(re.search(DAY_ONLY, p["text"])))


def end_at(p):
    """토스 선착순특가 마감 = 올린 날 밤 12시(KST) -> epoch 초 (배지가 '마감까지 1시간 25분'으로 줄어듦, END_JS)."""
    return calendar.timegm(time.strptime(p["t"][:10], "%Y-%m-%d")) + 86400 - 9 * 3600


def badge_html(p, skip=()):
    return "".join(f'<b class="{c}"' + (f' data-end="{end_at(p)}"' if c == "b2" else "") + f">{t}</b>" for c, t in badges(p) if c not in skip)


END_JS = """<script>(function(){function f(){var n=Date.now()/1000;[].forEach.call(document.querySelectorAll('[data-end]'),function(b){var s=b.dataset.end-n,h=Math.floor(s/3600),m=Math.floor(s%3600/60),k=b.dataset.k,c=k&&b.closest('.hc');
if(c&&s<=0){c.hidden=true;delete c.dataset.sh;var x=c.closest('section');if(x&&!x.querySelector('.hc:not([hidden])')){x.hidden=true;delete x.dataset.sh}return}
b.textContent=k?'⏰ '+(s<60?'곧 마감':(h?h+'시간 ':'')+m+'분 남음')+' · '+k:s<=0?'⏰ 마감됐어요':s<60?'⏰ 곧 마감':'⏰ 마감까지 '+(h?h+'시간 ':'')+m+'분'});[].forEach.call(document.querySelectorAll('[data-qend]'),function(b){if(n>+b.dataset.qend)b.remove()})}f();setInterval(f,30000)})()</script>"""  # 오늘 마감 칸(data-k) = 남은 시간 · 종류, 자정 지나면 카드·빈 칸·⏰ 'N개 남음'(data-qend) 숨김(10/24 Cowork — 빌드 시각 X, 브라우저 시계)
DOT_JS = """<script>(function(){var L,s=0;try{L=JSON.parse(localStorage.getItem('likes'))||[];s=+localStorage.getItem('chgseen')||0}catch(e){return}if(!L.length&&!window.hdpMy||/^\\/alarm\\//.test(location.pathname))return;
function on(j){if(window.hdpMy)hdpMy(j);if(L.some(function(x){var c=j.items[j.a[x.i]||x.i];return c&&c.d*1000>s&&c.k.some(function(k){return k!=='new'})})){var d=document.getElementById('adot');if(d)d.hidden=false}}
try{var c=JSON.parse(sessionStorage.getItem('chg'));if(c&&Date.now()-c.t<6e5)return on(c.j)}catch(e){}
fetch('/changes.json').then(function(r){return r.json()}).then(function(j){try{sessionStorage.setItem('chg',JSON.stringify({t:Date.now(),j:j}))}catch(e){}on(j)}).catch(function(){})})()</script>"""  # 아래 메뉴 🔔 빨간 점 = 마지막으로 알림 탭 본 뒤 찜한 상품이 바뀜(changes.json, 10분 한 번 받음 · 찜 0개·저장소 막힘 = 아무것도 안 함)


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


DAY_ONLY = r"하루\s*특가|선착순|밤 12시까지"  # 토스 하루특가·선착순특가 = 올린 날 밤 12시 마감
TOSS_LINE = "토스 가격 = 올린 날 가격 · 지금 가격은 링크에서 확인"  # 토스 카드 1줄('M/D 가격') 안내 — 칸 머리에 한 번(10/24 Cowork)
EVENTS = "events.json"
CP_LINKS = "cp_links.json"  # {쿠팡 상품 주소: 파트너스 링크} — 봇이 딥링크 API로 만듦(쿠팡 키 있을 때만 생김, 10/23 hotdeal.cp_links). events 그 주소 대신 씀
CP_PROD = r"https://(?:www\.|m\.)?coupang\.com/vp/products/(\d+)"  # 쿠팡 상품 주소(번호 = pid). 진우 단축 링크(link.coupang.com)는 그대로
CP_SHORT = ("link.coupang.com", "coupa.ng")  # 쿠팡 파트너스 링크 도메인(딥링크 API 단축 주소 = coupa.ng일 수도 — 공식 샘플)


def ev_list(path=None):
    """events.json(Cowork 예약) 그대로 — 쿠팡 상품 주소만 cp_links.json의 파트너스 링크로(pid 없으면 주소의 상품 번호 · 행사 목록 글 items도). 깨진 파일 = []."""
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
        for x in [e] + (e["items"] if isinstance(e, dict) and isinstance(e.get("items"), list) else []):  # items = 행사 목록 글(list)의 상품들
            if isinstance(x, dict) and isinstance(x.get("url"), str) and isinstance(cl.get(x["url"]), str) and (m := re.match(CP_PROD, x["url"])):
                x.setdefault("pid", m[1])
                x["url"] = cl[x["url"]]
    return evs


def ev_info():
    """events.json 진우 항목 -> {url: {now, chk, end, why, target, pid, item, img}}(같은 url 여러 항목이면 뒤 항목이 덮음, 글자 칸만 — img = 상품 사진 주소, 글에 넣는 건 hotdeal.own_end·쓰는 건 img_of 허용 목록만). 깨진 파일 = {}(사이트 빌드가 멈추면 그 실행의 기록·커밋이 안 남음)."""
    evs, out = ev_list(), {}
    for e in evs if isinstance(evs, list) else []:
        if isinstance(e, dict) and isinstance(e.get("url"), str):
            out.setdefault(e["url"], {}).update({k: e[k] for k in ("now", "chk", "end", "why", "target", "pid", "item", "img") if isinstance(e.get(k), str)})
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
    return (1 if p.get("stdy") else 2), (now or ("" if tgt else None)), (f"지금 가격{f' ({chk} 확인)' if chk else ''} · {wait}" if now else wait if toss else f"{wait} · 지금 가격은 링크에서 확인"), bd + [("b3", "⏳ 특가 대기")], False


def shelf_gone(posts):
    """같은 url 진우 글이 뒤에 또 올라온 사이트 진열(shelf) 글 번호 — 사이트엔 글 하나로(10/24 진우 '합치기' — home_pool과 같은 기준: url마다 최신 진우 글)."""
    last = {p.get("url"): i for i, p in enumerate(posts) if p.get("own")}
    return {i for i, p in enumerate(posts) if p.get("shelf") and (last.get(p.get("url"), i) != i or not site_ok(p))}  # 수수료 없는 진열 글(쿠팡 생 주소 — 10/25 20시 진우 '빼자') = 같이 보기·목록·사이트맵 X


def home_pool(posts, days, ok=None):
    """홈 몰·품목·브랜드 칸에 둘 딜 -> {posts 번호: shelf 상태}(10/23 진우 '우리가 업로드한 제품들을 리스트에서 그냥 빼지 않기' · '진열 = 기본 유지'):
    커뮤니티 딜 = 최근 3일 그대로(판매 확인 방법 없음), 진우 상품(own) = 날짜 상관없이 같은 url 최신 글 1개(같은 url 커뮤니티 글이 더 새로 칸에 있으면 그것만) — 빼는 건 shelf가 None인 것뿐."""
    today, ev = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600)), ev_info()
    recent = lambda p: p["t"][:10] in days[:3] and not p["text"].startswith("📋")
    last = {p.get("url"): i for i, p in enumerate(posts) if p.get("own")}
    newer = {p.get("url"): i for i, p in enumerate(posts) if not p.get("own") and recent(p)}  # 같은 url 커뮤니티 글이 더 새로 칸에 있으면 그것만(같은 상품 두 번 X)
    out = {}
    for i, p in enumerate(posts):
        if p["text"].startswith("📋") or (last.get(p.get("url")) != i or newer.get(p.get("url"), -1) > i if p.get("own") else not recent(p)) or not (ok or site_ok)(p):  # ok = 사이트 규칙 대신(SS 하루 로그 — 숨긴 수)
            continue  # 사이트 = 제휴 링크 딜(+ 당분간 뽐뿌·네이버 검색) — 쿠팡 생 주소 진열은 바뀌면 그때(site_ok)
        if (s := shelf(p, ev, today)) is not None:
            out[i] = s
    return out


CATS = (("life", "🧻 생필품", r"휴지|화장지|티슈|키친타[월올]|세제|유연제|퍼실|다우니|피죤|스너글|샴푸|린스|컨디셔너|트리트먼트|바디워시|핸드워시|손세정|비누|치약|칫솔|가글"
                              r"|리스테린|생리대|(?<!아이)라이너|기저귀|면도|마스크(?!팩)|KF\d|크린랩|위생[백랩장]|니트릴|지퍼백|쿠킹호일|종량제|쓰레기봉투|수세미|고무장갑|행주|탈취|방향제"
                              r"|페브리즈|제습제|건전지|락스|세정제"),
        ("beauty", "💄 화장품", r"화장품|올리브영|스킨케어|토너|에센스(?!웨어)|세럼|앰플|로션|[수영]분크림|아이크림|선크림|핸드크림|바디크림|재생크림|선케어|선스틱|선쿠션|자외선"
                               r"|클렌징|클렌저|폼클렌|마스크팩|시트팩|토너패드|각질|화장솜|립스틱|립밤|립글로|틴트|쿠션팩트|에어쿠션|파운데이션|컨실러|미스트|향수|메이크업"
                               r"|마스카라|아이섀도|네일|올인원|헤어\s*(?:스프레이|왁스|오일|에센스|미스트)|슬리핑\s*마스크|립\s*마스크|모공\S*\s*마스크|크림\s*\+\s*마스크"))  # 제목 키워드(10/9 실제 딜 121개로 맞춤 — 크림·팩·쿠션·립·패드 단독은 음식·가구랑 겹쳐서 뺌)


HEAT = r"핫팩|손난로|발난로|보온대|온열|전기\s*(?:요|매트|장판|담요|방석)|온수\s*매트|난로|히터|발열\s*(?:내의|조끼)|방한|온풍기|라디에이터|컨벡(?:터|션)|찜질기|스토브"  # 10/25 21시 Cowork 난방 진열 115개(전기담요 USB = 가전 X)
HOME_RX = (r"모기|살충|홈키파|에프킬라|킨칸|퇴치|샤워기|샤워\s*헤드|수전|조리\s*도구|프라이팬|후라이팬|냄비|도마|주방|수저|젓가락|텀블러|밀폐\s*용기|보관\s*용기|정수|필터|수납|정리함|옷걸이|빨래|건조대|"
           r"청소포|물걸레|밀대|청소\s*(?:솔|도구)|매트(?!리스)|러그|이불|베개|커튼|전구|LED|가위|집게|휴지통|분리수거|화분|방충|문풍지|단열")
FASHION = (r"양말|스타킹|레깅스|팬티|속옷|브라(?!운)|티셔츠|셔츠|바지|청바지|후드|맨투맨|패딩|자켓|재킷|코트|모자|비니|장갑|목도리|머플러|운동화|슬리퍼|신발|가방|백팩|지갑|벨트|우산|내의|잠옷|파자마|조끼"
           r"|가디건|(?<![가-힣])니트(?!릴)|스웨터|후리스|플리스|실내화|타이즈|점퍼")  # 여성 가을·겨울 옷 = 패션(여성용품 칸 = 생리대 등만 — 10/25 21시 Cowork)
WEAR_FIRST = r"양말|가디건|(?<![가-힣])니트(?!릴)|스웨터|후리스|플리스|실내화|타이즈"  # 옷 낱말이 분명하면 식품·간식보다 먼저(10/25 '파스텔 과일 플라워 수면 양말'이 '과일'로 식품 칸에) — 난방(온열 양말 등)은 그대로 먼저
DIGI = (r"충전기|케이블|보조\s*배터리|이어폰|헤드폰|헤드셋|블루투스|마우스|키보드|모니터|노트북|태블릿|아이패드|갤럭시|스마트\s*워치|SSD|USB|메모리|카메라|청소기|에어\s*프라이어|전기\s*포트|드라이기|"
        r"가습기|공기\s*청정|선풍기|제습기|밥솥|믹서|블렌더|토스터|면도기|멀티탭|스피커|TV|프린터|전동")
FOOD7 = FOOD + (r"|잡곡|현미|귀리|오트|돼지|돈육|소고기|우삼겹|차돌|불고기|닭가슴살|볶음밥|주먹밥|도시락|동그랑땡|떡갈비|돈까스|돈가스|너겟|간식|젤리|사탕|쿠키|비스킷|빵|베이글|두유|녹차|홍차|티백|보리차|"
                r"옥수수|참치|스팸|(?<!폴)햄(?!스터)|소시지|피자|떡볶이|어묵|곤약|요거트|요구르트|치즈|버터|꿀|잼|시리얼|그래놀라|두부|고구마|감자(?!탕)|토마토|딸기(?!향)|귤|포도|키위|블루베리|아몬드|호두|땅콩|"
                r"김밥|라떼|아메리카노|원두|탄산수|콜라(?!겐)|사이다|식혜|국수|우동|냉면|파스타|소면|당면|밀키트|밀가루|설탕|식용유|참기름|간장|된장|고추장|케첩|마요|분유|이유식")
KITCHEN = (r"프라이팬|후라이팬|냄비|도마|칼\s*세트|식칼|주방|조리\s*도구|뒤집개|국자|수저|숟가락|젓가락|식기|그릇|접시|머그|컵\s*세트|밀폐\s*용기|보관\s*용기|유리\s*용기|내열\s*유리|곰솥|락앤락|글라스락|"
           r"크린랩|위생[백랩장]|지퍼백|쿠킹\s*호일|종이\s*호일|키친타[월올]|수세미|고무장갑|행주|설거지|퐁퐁|자연퐁|트리오|텀블러|보온병|물병")
LAUNDRY = (r"세탁(?!기)|세탁조|세제|유연제|퍼실|다우니|피죤|스너글|표백|과탄산|옥시크린|빨래|건조대|드라이\s*시트|건조기\s*시트|얼룩\s*제거|울샴푸|리큐|(?:테크|비트)\s*(?:액체|세제|파워)|옷걸이")
WOMEN = r"생리|탐폰|(?<!아이)라이너|오버\s*나이트|위생\s*팬티|여성\s*(?:청결|세정|용품)|쏘피|좋은\s*느낌|위스퍼|순수한면|템포|시크릿\s*데이|입는\s*오버"
SNACK = (r"과자|초코|쵸코|견과|간식|젤리|사탕|캔디|쿠키|비스킷|스낵(?!면)|칩(?!셋)|웨하스|크래커|양갱|(?<![가-힣])껌|마시멜로|프레첼|팝콘|아이스크림|빼빼로|오예스|"
         r"새우깡|허니버터|에너지\s*바|단백질\s*바|약과|강정|육포|쥐포")
SEASON = (r"감귤|(?<![가-힣])귤|한라봉|천혜향|레드향|고구마|단감|홍시|(?<![가-힣])반시|대봉|곶감|햇밤|군밤|(?<![가-힣])밤\s*\d|햅쌀|사과|부사|샤인\s*머스캣|생굴|석화|(?<![가-힣])굴(?!비|소스)|방어|꼬막|"
          r"과메기|대게|홍게|전어|유자|호빵|김장|절임\s*배추|배추|(?<![가-힣])무\s*\d|동치미|딸기(?!향|맛)|붕어빵|호떡|팥죽")
CAR = r"요소수|워셔액|엔진|차량용|자동차|타이어|와이퍼|콘솔\s*(?:쿠션|박스|트레이)|헤드레스트|블랙박스|불스원|유막|햇빛\s*가리개|[선썬]\s*쉐이드"  # 10/26 Cowork 자동차 칸 — 콘솔 = 차 콘솔만(게임기 X) · 방향제 단독 X(집 방향제 = 생필품, 차 방향제는 '차량용'으로)
SHELF_CATS = (("life", "🧻 생필품", CATS[0][2]), ("kitchen", "🍳 주방", KITCHEN), ("laundry", "🧺 세탁", LAUNDRY), ("women", "🌸 여성용품", WOMEN), ("beauty", "💄 화장품·뷰티", CATS[1][2]),
              ("food", "🍚 식품·음료", FOOD7), ("snack", "🍪 과자·간식", SNACK), ("season", "🍠 제철 먹거리", SEASON), ("home", "🏠 생활·살림", HOME_RX),
              ("fashion", "🧦 패션·잡화", FASHION), ("digital", "🔌 가전·디지털", DIGI), ("heat", "🔥 겨울 난방", HEAT), ("car", "🚗 자동차", CAR))  # 10/23 진우 7칸 -> 10/24 '수백 개로 늘어나니 세분(주방·세탁·여성용품·과자·계절음식)' 12칸 — 이 순서로 보임(겨울 난방·제철 = 계절 칸, 없으면 안 보임)
CAT_ORDER = ("heat", "car", "women", "beauty", "kitchen", "laundry", "life", "snack", "season", "food", "home", "fashion", "digital")  # 제목이 여러 칸에 맞으면 이 순서(핫팩 = 난방, 생리대 = 여성용품, 크림·클렌징 = 화장품, 주방 세제·크린랩 = 주방, 세제 = 세탁, 휴지 = 생필품, 과자 > 제철 > 식품)


HOME_FIRST = r"모기|홈매트|훈증|살충|킨칸|에프킬라"  # 모기향 '히터'(리퀴드 훈증기)는 겨울 난방 X -> 생활·주방(10/23 리뷰)
SEASON_ITEMS = (("summer", r"선풍기|서큘레이터|서큐레이터|써큘레이터|쿨\s*매트|아이스\s*(?:박스|팩|쿨|매트|조끼|넥|머플러|토시)|모기|홈매트|선크림.*대용량|대용량.*선크림"),
                ("winter", HEAT + r"|가습기|기모(?![듬둠])|패딩"), ("between", r"가디건|카디건|제습제"))  # Z(10/26 진우 '우리나라는 4계절'): 여름템(모기향 '히터'도 — 먼저 봄)·겨울템·환절기템
SEASON_NOT = r"오븐|프라이어|캠핑|안대"  # 겨울템 아님(HEAT의 컨벡션 오븐·캠핑 스토브·온열 안대 = 사철)


def season_item(name):
    """상품 이름 -> 'summer'·'winter'·'between'·None(계절 상품 아님). '써큘레이터형 온풍기'·'서큘레이터 히터' = 겨울(AA 리뷰 — 모기향 히터는 여름 그대로)."""
    heat = re.search(r"온풍|히터|난로", name or "") and not re.search(HOME_FIRST, name or "")
    return next((k for k, rx in SEASON_ITEMS if re.search(rx, name or "") and not (k == "winter" and re.search(SEASON_NOT, name)) and not (k == "summer" and heat)), None)


def season_off(kind, m, tmin=None, tmax=None):
    """Z 계절 상품이 지금 철 지났는지 — 금지어와 같은 기준: 여름템 = 10~3월 또는 최고 22도 아래 · 겨울템 = 5~8월 또는 최저 15도 위(기온 없으면 달만)."""
    return kind == "summer" and (m in (10, 11, 12, 1, 2, 3) or tmax is not None and tmax < 22) or kind == "winter" and (m in (5, 6, 7, 8) or tmin is not None and tmin > 15)


def cat_of(p):
    """품목 칸 1개: 제목 정규식(HOME_FIRST -> CAT_ORDER 순) -> 안 맞으면 글 cat(hotdeal.cat_fill이 Claude 한 단어로 채움 — etc = 칸 없음) -> ''."""
    t, rx = title_of(p["text"]), {k: r for k, _, r in SHELF_CATS}
    return ("home" if re.search(HOME_FIRST, t) else "fashion" if re.search(WEAR_FIRST, t) and not re.search(HEAT, t)
            else next((k for k in CAT_ORDER if re.search(rx[k], t)), p.get("cat") if p.get("cat") in rx else ""))


PRICE_ITEMS = (  # 10/17 진우 '유입 늘리기 ② 최저가 기록 페이지'(/c/주소.html): (주소, 품목, 제목 낱말, 비교 단위, 그 단위로 보는 '…당' 낱말 — 1L당 = 'l') — 같은 단위끼리만
    ("ramen", "라면", r"라면|너구리|짜파게티|안성탕면|컵누들|사발면", "개당", ("개", "봉", "봉지")),
    ("water", "생수", r"생수|샘물|삼다수|아이시스|백산수", "1L당", ("l",)),  # 병당·개당은 병 크기(500ml·2L)가 달라서 X
    ("toilet-paper", "화장지", r"화장지|두루마리|휴지(?!통)", "롤당", ("롤",)),
    ("detergent", "세탁세제", r"세탁\s*세제|액체\s*세제|퍼실|리큐|(?:테크|비트)\s*(?:액체|세제|파워)", "1L당", ("l",)),
    ("coffee-mix", "커피믹스", r"커피\s*믹스|모카\s*골드|화이트\s*골드", "개당", ("개", "개입", "t", "스틱")),
    ("wet-wipes", "물티슈", r"물티슈", "팩당", ("팩",)),
    ("eggs", "계란", r"(?:계란|달걀)(?!\s*(?:말이|과자|빵|스낵|찜|장조림))|특란|왕란|대란|구운란|반숙란|완숙란|맥반석(?=.*(?:란|달걀))|유정란|훈제란", "개당", ("개", "구", "알")),  # NN(10/26) 바로 먹는 계란(반숙란·완숙란·맥반석)·유정란도 — 계란말이·계란과자·맥반석 오징어 X
    ("instant-rice", "즉석밥", r"햇반|즉석밥|오뚜기\s*(?:밥|흑미밥|잡곡밥)", "개당", ("개",)),
    ("shampoo", "샴푸", r"샴푸", "100ml당", ("100ml",)),
    ("milk", "우유", r"(?:멸균|바나나|커피|흰|저지방|무지방|딸기|초코)\s*(?:맛\s*)?우유|우유\s*\d+\s*(?:ml|mL|L)", "100ml당", ("100ml",)),  # NN(10/26 Cowork) 멸균·바나나·커피·흰 우유 — 우유식빵·우유맛 과자 X
    ("rice", "쌀", r"햅쌀|백미|쌀\s*\d+\s*kg|\d+\s*kg\s*쌀", "1kg당", ("kg",)))
PRICE_NOT = r"냄비|그릇|용기|포트|머신|거치대|케이스|홀더|디스펜서|정리함|브러시|브러쉬|의자"  # 품목 낱말이 들어도 그 품목 아님(라면 냄비·샴푸 의자 등)
PRICE_MIN = 3  # 기록이 이보다 적으면 페이지·투표 X
PAIR = re.compile(r"((?:\d+(?:\.\d+)?\s*)?[^\d\s(),·~/]+?)\s*당\s*(?:약\s*|평균\s*)?(\d[\d,]*(?:\.\d+)?)\s*원")  # '개당 약 496원 (1L당 248원)' -> ('개','496'), ('1L','248')


def price_item(p):
    """이 딜의 최저가 기록 품목(PRICE_ITEMS 줄) — 토스 딜은 None(토스 요청 '타 쇼핑몰과의 가격 비교 없이': 다른 몰과 한 표에 놓는 것도 비교)."""
    title = title_of(p["text"])
    if p["text"].startswith("📋") or shop_of(p) == "toss" or re.search(PRICE_NOT, title):
        return None
    return next((it for it in PRICE_ITEMS if re.search(it[2], title)), None)


def price_records(posts, shelf=True, skip=()):
    """최저가 기록 {주소: (품목, 단위, [(단위가격, '1L당 248원', i, p), …] 싼 순)} — 품목 딜 중 💡 단위가격에 그 단위가 있는 것만, PRICE_MIN개↑ 품목만.
    같은 상품이 같은 단위가격으로 다시 올라오면 최근 1개(숫자는 글에 적힌 그대로 — 단위 바꿔 셈 X)."""
    rows = {}
    for i, p in enumerate(posts):
        it = (shelf or not p.get("shelf")) and i not in skip and price_item(p)  # shelf=False = 채널 글만(Threads 투표) · skip = 사이트에서 뺀 비제휴 딜
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
            + (f'<h3>🔥 지금 올라온 {name} 딜</h3><div class="t">최근 24시간 · 가격·재고는 바뀔 수 있어요</div><div class="cards">{"".join(card(r[2], r[3], st0(r[3])) for r in now)}</div>' if now else "")
            + f'<div class="stat"><div><b>{html.escape(low[1].split()[-1])}</b>기록 최저 · {md(low[3])} {html.escape(parse(title_of(low[3]["text"]))[0])}</div><div><b>{avg:,}원</b>평균 · 기록 {len(rows)}개</div></div>'
            + f'<div class="tw"><table><thead><tr><th>날짜</th><th>몰</th><th>상품</th><th>가격</th><th>{unit}</th></tr></thead><tbody>{tr}</tbody></table></div>'
            + f'<p class="t">💙 토스 특가는 이 표에 넣지 않아요 — <a href="{BASE}c/toss/">토스 특가 모음 보기</a></p>{rec_nav(recs, k) or ""}</section>')
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


SAVED = ('<h1 class="h">♡ 찜한 딜</h1><div class="t">이 폰(브라우저)에만 저장돼요<span id="savn"> · 가격은 올린 때 기준이라 바뀌었을 수 있어요</span></div><p class="chgs" id="chgsum" hidden></p>'
         '<section id="saved" aria-label="찜한 딜"><div class="cards" id="savedg"></div><p id="saved0" class="t">아직 찜한 딜이 없어요. 상품 카드의 ♡를 누르면 여기 모여요.</p></section>')  # 10/24 개편: /saved/ 쪽(아래 메뉴 ♡ 찜·헤더 ♡) — 옛 카드 HTML도 그대로 보임
ALARM = (f'<h2 class="ch">📲 새 특가 알림 받기</h2><div class="t">새 특가·다시 특가를 바로 받아 보세요</div><a class="btn" href="{CHANNEL}">📲 텔레그램 채널에서 실시간 알림 받기</a>'
         f'<a class="btn2" href="{THREADS}">Threads에서 팔로우</a><a class="btn2" href="{INSTA}">인스타그램에서 팔로우</a>')  # 아래 메뉴 🔔(웹 푸시 전까지 텔레그램 채널)
HOME_DIS = "쿠팡 파트너스·토스 쉐어링크·네이버 쇼핑 커넥트 등 제휴로 수수료를 받을 수 있어요."  # 홈 대가성 문구 1~2줄(10/24 Cowork 포털형 — 몰 바로 가는 링크 옆엔 그 몰 문구 그대로)
CHG_JS = """<script>document.addEventListener('DOMContentLoaded',function(){var L=[];try{L=JSON.parse(localStorage.getItem('likes'))||[]}catch(e){}
var g=document.getElementById('savedg'),sum=document.getElementById('chgsum'),cn=document.getElementById('chgn'),al=/^\\/alarm\\//.test(location.pathname);
function lab(c){var k=c.k;return k.indexOf('gone')>=0?'판매 종료':k.indexOf('deadline')>=0?'⏰ 오늘 밤 마감':k.indexOf('drop')>=0?'▼ '+c.p+'% 내림 · '+(c.t.split(' ')[0]||'')+' 확인':k.indexOf('rehot')>=0?'🔁 다시 특가':k.indexOf('ended')>=0?'⏳ 특가 끝남':''}
function deco(j){var n={drop:0,deadline:0,rehot:0,ended:0,gone:0},m=0;
if(g){var C=[].slice.call(g.querySelectorAll('.g')),ch=[];C.forEach(function(c){var b=c.querySelector('.like'),i=b&&b.dataset.i,x=i&&j.items[j.a[i]||i],t=x&&lab(x),o=c.querySelector('.chg');if(o)o.remove();if(!t)return;
var d=document.createElement('div');d.className='chg';d.textContent=t;var h=c.querySelector('h3');if(h)h.parentNode.insertBefore(d,h);ch.push(c);x.k.forEach(function(k){if(k in n)n[k]++})});
ch.concat(C.filter(function(c){return ch.indexOf(c)<0})).forEach(function(c){g.appendChild(c)});m=ch.length;
var w=[['drop','가격 내려간'],['deadline','오늘 마감'],['rehot','다시 특가'],['ended','특가 끝난'],['gone','판매 종료']].filter(function(x){return n[x[0]]}).map(function(x){return x[1]+' '+n[x[0]]+'개'});
if(sum){sum.textContent=w.length?'찜한 딜 중 '+w.join(' · '):'';sum.hidden=!w.length}}
else{m=L.filter(function(x){var c=j.items[j.a[x.i]||x.i];return c&&lab(c)}).length}
if(cn)cn.textContent=m;if(al){try{localStorage.setItem('chgseen',Date.now())}catch(e){}var d=document.getElementById('adot');if(d)d.hidden=true}}
function get(){fetch('/changes.json').then(function(r){return r.json()}).then(deco).catch(function(){})}
get();if(g)document.addEventListener('click',function(e){if(e.target.closest&&e.target.closest('.like'))setTimeout(get,0)})})</script>"""  # 찜 쪽 = 바뀐 카드에 배지·맨 위 요약·바뀐 것 먼저(안내 문구는 바뀐 게 없을 때만) · 알림 탭 = '내 찜 변경 N' + 본 시각(빨간 점 끔) — 찜 0개·변경 0개·저장소 막힘 = 그대로


def alarm_body(ch):
    """알림 탭(10/24 Cowork '변경 찾기'): 맨 위 '♡ 내 찜 변경 N'(CHG_JS) + '오늘 바뀐 것' 줄(📉 가격 내려감·⏰ 오늘 마감·🔁 다시 특가 → 그 쪽, GoatCounter changes/종류) + 아래 텔레그램·SNS(ALARM)."""
    n = ch.get("n") or {}
    rows = [(c_url("drop"), "drop", "📉 가격 내려감"), (c_url("today"), "deadline", "⏰ 오늘 마감"), (c_url("rehot"), "rehot", "🔁 다시 특가")]
    return ('<h1 class="h">🔔 알림</h1><section class="chgb" aria-label="바뀐 것">'
            f'<a class="btn2" href="{BASE}saved/" data-gc="changes/saved"><span>♡ 내 찜 변경 <b id="chgn">0</b>개 보기 →</span></a><h2 class="ch">오늘 바뀐 것</h2><ul>'
            + "".join(f'<li><a href="{u}" data-gc="changes/{k}"><span>{t}</span><b>{n.get(k, 0)}개 →</b></a></li>' for u, k, t in rows) + "</ul></section>" + ALARM)

LIKE_JS = """<script>(function(){var L;try{L=JSON.parse(localStorage.getItem('likes'))||[]}catch(e){L=[]}
function has(i){return L.some(function(x){return x.i===i})}
function sync(){[].forEach.call(document.querySelectorAll('.like'),function(b){b.setAttribute('aria-pressed',has(b.dataset.i)?'true':'false')});
var c=document.getElementById('lc'),g=document.getElementById('savedg');if(c)c.textContent=L.length?' '+L.length:'';
if(g){g.innerHTML=L.map(function(x){return x.h}).join('');document.getElementById('saved0').hidden=L.length>0;[].forEach.call(g.querySelectorAll('.like'),function(b){b.setAttribute('aria-pressed','true')})}}
window.hdpLike=sync;document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('.like');if(!b)return;var i=b.dataset.i;
L=has(i)?L.filter(function(x){return x.i!==i}):[{i:i,h:b.closest('.g').outerHTML}].concat(L).slice(0,50);try{localStorage.setItem('likes',JSON.stringify(L))}catch(e){}sync()});sync()})()</script>"""

CAT_META = {  # 10/24 진우 개편: 품목 칸 -> (쪽 주소 /c/slug/, 이름, 이모지, 파스텔 바탕) — 홈 타일 8칸 = TILES(4×2), 나머지 4칸은 /c/ 카테고리 쪽에 · 주소는 영문(Threads 글에서 한글 주소가 링크로 안 이어질 수 있어서)
    "life": ("life", "생필품", "🧻", "#FFEFE6"), "food": ("food", "식품", "🍚", "#EAF6EE"), "beauty": ("beauty", "뷰티", "💄", "#FDEBF1"), "kitchen": ("kitchen", "주방", "🍳", "#EEF1FB"),
    "laundry": ("laundry", "세탁", "🧺", "#E9F5F8"), "snack": ("snack", "간식", "🍪", "#FFF6DD"), "women": ("women", "여성용품", "🌸", "#F3ECFB"), "heat": ("winter", "겨울템", "❄️", "#E8F1FF"),
    "season": ("season", "제철 먹거리", "🍠", "#FFF1E6"), "home": ("home", "생활·살림", "🏠", "#F1F3F6"), "fashion": ("fashion", "패션·잡화", "🧦", "#F5EFEA"), "digital": ("digital", "가전·디지털", "🔌", "#EEF2F7"),
    "car": ("car", "자동차", "🚗", "#EEF1F4")}  # 자동차 = 맨 끝(10/26 Cowork — /c/ 칸·홈 품목 줄)
TILES = ("life", "food", "beauty", "kitchen", "laundry", "snack", "women", "heat")
MALLS = (("coupang", "쿠팡", "🚀"), ("toss", "토스", "💙"), ("naver", "네이버", "💚"))
PER = 20  # 목록 쪽 한 쪽 상품 수(10/24 진우 '카테고리·전체 페이지는 20개씩') — 다음 쪽 = /c/이름/2/
PICK_N, PICK_HOUR = 3, 10  # 오늘의 픽 3개 · 하루 1번(KST 10시 뒤 첫 빌드 — Cowork 9:10 가격 확인 반영 뒤) 고정, 그 전엔 전날 픽
PICKS = "today/picks.json"  # docs/ 아래 {날짜: [글 번호]} — 하루 동안 픽이 안 바뀌게(빌드는 15분마다)
c_url = lambda slug, n=1: f"{BASE}c/{slug}/" + (f"{n}/" if n > 1 else "")
NAV = (("home", "홈", BASE), ("fire", "특가", f"{BASE}c/hot/"), ("cats", "카테고리", f"{BASE}c/"), ("saved", "찜", f"{BASE}saved/"), ("alarm", "알림", f"{BASE}alarm/"))
UI = {  # Lucide(ISC) 선 아이콘 — 아래 메뉴·헤더
    "home": '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "fire": '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
    "cats": '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>',
    "saved": '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>',
    "alarm": '<path d="M10.268 21a2 2 0 0 0 3.464 0"/><path d="M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>'}
svg = lambda k: f'<svg viewBox="0 0 24 24" aria-hidden="true">{UI[k]}</svg>'
ICON_FIX = ((r"가습기|보조\s*배터리|충전기|이어폰|드라이기|선풍기|멀티탭|모니터", "digital"), (r"사료|강아지|고양이|애견|펫", ""))  # 10/26: 차량용·자동차·워셔액·요소수·햇빛 가리개 = 자동차 칸(CAR)으로  # 품목이 틀리게 잡히는 이름(미스트 가습기 필터 = 뷰티 X · 고양이 사료 = 식품 X · 차량용 = 쇼핑백)


def icon_key(p):
    """썸네일 선 아이콘 키(search.json m): ICON_FIX(이름) -> 품목(cat_of) -> '' (쇼핑백)."""
    c = cat_of(p)
    k = next((k for r, k in ICON_FIX if re.search(r, parse(title_of(p["text"]))[1]) and not (k == "" and c in ("heat", "fashion"))), c)  # 펫 낱말이어도 난방·패션 칸이면 그 칸(10/26 온수매트 강아지·고양이 털 슬리퍼)
    return k if k in CAT_ICON else ""


ci = lambda p: f'<i class="ci ci-{icon_key(p) or "x"}" aria-hidden="true"></i>'  # 품목 선 아이콘(CSS 마스크 .ci-품목 · 없으면 x = 쇼핑백)


def chip_of(p):
    """몰 칩: '쿠팡 · 로켓'(글 머리 줄 🚀 = API isRocket 근거 있을 때만 — 10/22 진우 '사실 아닌 표기 X') · '토스' · '네이버' · 그 밖 [몰] 이름."""
    s = shop_of(p)
    return {"coupang": "쿠팡 · 로켓" if re.search(r"^🚀 쿠팡", p["text"], re.M) else "쿠팡", "toss": "토스", "naver": "네이버"}.get(s) or parse(title_of(p["text"]))[0] or "핫딜"


def img_of(p):
    """상품 사진 주소(글 img): 쿠팡 = 파트너스 API productImage(hotdeal.cp_price) — https + 쿠팡 사진 주소만(HTML에 들어가는 값이라 허용 목록), 토스·네이버·그 밖 = ''(토스 = API 데이터 사이트 전시 X · 네이버 쇼핑 검색 API는 2026-07-31 종료)."""
    u, s = p.get("img") or "", shop_of(p)
    host = urllib.parse.urlsplit(u).netloc
    return u if u.startswith("https://") and (s == "coupang" and (host == "coupang.com" or host.endswith((".coupang.com", ".coupangcdn.com")))) else ""


def thumb(p, inner=""):
    """썸네일: 품목 파스텔 네모 + 품목 선 아이콘(CAT_ICON), 쿠팡 사진이 있으면 그 위에(정사각 흰 배경 contain · 못 불러오면 사진만 지워져 선 아이콘이 보임)."""
    c, u = CAT_META.get(cat_of(p)), img_of(p)
    bg = f' style="--c:{c[3]}"' if c else ""
    pic = f'<img src="{html.escape(u)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="this.remove()">' if u else ""
    return f'<div class="im"{bg}>{ci(p)}{pic}{inner}</div>'


def price_bits(p, sh):
    """(보이는 가격, 빨강 작은 줄, 회색 줄들): 가격 = 확인 가격(now) 또는 올린 가격 첫 조각, 빨강 = 쿠폰가·와우가·할인(올린 가격 보일 때만)·다른 몰보다 싼 금액·마감, 회색 = 단위가·진열 줄."""
    _, now, note, _, _ = sh
    main, _, _ = parse(title_of(p["text"]))[2].partition("/")
    seg = [s.strip() for s in main.split(" · ") if s.strip()]
    m = now and re.match(r"([\d,]+원)\s*(\S.*)", now)  # '13,910원 쿠폰가' -> 가격 + 빨강 '쿠폰가'(10/24 진우 '가격 800 + 쿠폰·할인 빨강 줄')
    shown = (seg[0] if seg else "") if now is None else m[1] if m else now
    sv = now is None and saving(p["text"])
    ex = (seg[1:] if now is None else [m[2]] if m else []) + ([f"{sv[0]}보다 {sv[1]}↓"] if sv else [])
    toss = shop_of(p) == "toss"
    old = not note and (p.get("own") or toss or p.get("api")) and f'{int(p["t"][5:7])}/{int(p["t"][8:10])} 가격' + ((f' · {p["chk"]} 다시 확인' if sh[4] and p.get("chk") else "") if toss else " · 지금 가격은 링크에서 확인")  # 토스 = 1줄(10/24 Cowork — '지금 가격은 링크에서 확인'은 칸 머리 TOSS_LINE 한 번)
    grey = [x for x in (note or old, unit_of(p) if now is None else "") if x]  # 날짜·상태 줄 먼저(픽 줄·검색은 첫 줄만 — 토스 = 게시 시점 표기 필수)
    return shown, ex, grey


def badge(p, sh):
    """카드 왼쪽 위 배지 1개: 🔁 다시 특가·🔥 특가(빨강) · 👍 꾸준템(흰) · ⏳ 대기·일시 품절(어두운) — 커뮤니티 딜은 🔥만."""
    st, rehot = sh[0], sh[4]
    if st == 0:
        return '<b class="bdg f">🔁 다시 특가</b>' if rehot else '<b class="bdg f">🔥 특가</b>'
    if not p.get("own"):
        return ""
    out = next((t for _, t in sh[3] if t.startswith("일시 품절")), "일시 품절")  # 'M/D 확인'까지
    return {1: '<b class="bdg">👍 꾸준템</b>', 2: '<b class="bdg w">⏳ 대기</b>', 3: f'<b class="bdg w">{html.escape(out)}</b>'}.get(st, "")


def card(i, p, sh, more=(), attrs="", plain=False):
    """상품 카드(10/24 진우 개편 A): 흰 r20 · 위 118px 썸네일(+ 배지·♡) · 몰 칩 · 이름 2줄 · 가격 800 17px · 빨강 줄 · 회색 줄. 카드 전체 = 딜 쪽(구매 버튼·왜 골랐나요).
    .g + .like data-i = 찜(LIKE_JS가 카드째 저장)·검색 그대로. sh = shelf 상태, more = 회색 줄 더(행사 쪽 단위가).
    plain = 📉 가격 내려간 쪽(10/24 Cowork C): 상태 배지 X(▼N%만) · 회색 = 'M/D H시 확인' + 대기면 '목표가 N원'."""
    name = parse(title_of(p["text"]))[1]
    shown, ex, grey = price_bits(p, sh)
    end = [f'<div class="ex" data-end="{end_at(p)}">⏰ 오늘 밤 12시 마감</div>'] if any(c == "b2" for c, _ in badges(p)) else []
    ex = ([f"▼ {DROPS[i][0]}% 내림 ({DROPS[i][1]} 기록 대비)"] if i in DROPS else []) + ex  # 📉 같은 구성 내림(10/24 Cowork '카드에서도 바로')
    if plain:
        tg = re.match(r"[\d,]+원", p.get("tgt") or "")
        grey = [x for x in (p.get("chk") and f"{p['chk']} 확인", sh[0] in (1, 2) and tg and f"목표가 {tg[0]}") if x]
    return (f'<article class="g"{attrs}><button class="like" type="button" data-i="{i}" aria-pressed="false" aria-label="{html.escape(name)} 찜">{svg("saved")}</button>'
            + thumb(p, "" if plain else badge(p, sh)) + f'<span class="mc">{html.escape(chip_of(p))}</span>'
            + f'<h3><a href="{BASE}p/{i}.html">{html.escape(name)}</a></h3>' + (f'<div class="pr">{html.escape(shown)}</div>' if shown else "")
            + "".join(f'<div class="ex">{html.escape(x)}</div>' for x in ex[:2]) + "".join(end) + "".join(f'<div class="u">{html.escape(x)}</div>' for x in [*grey, *(m for m in more if m not in grey)]) + "</article>")


def go_url(i, p):
    """'보기'·구매 버튼 주소: 제휴·쇼핑몰 링크 바로(올리브영 = 딜 쪽 거쳐 — 사이트 규칙), 커뮤니티 원글·주소 없음 = 딜 쪽."""
    u = p.get("url") or ""
    return u if u and not community(u) and urllib.parse.urlsplit(u).netloc not in OY_HOSTS else f"{BASE}p/{i}.html"


def pick_row(n, i, p, sh):
    """오늘의 픽 한 줄: 순위 · 64px 썸네일 · 몰 칩 · 이름 2줄 · 가격 800 18px + 빨강 줄 · 회색 줄 · '보기'(핑크, 몰로 바로)."""
    name = parse(title_of(p["text"]))[1]
    shown, ex, grey = price_bits(p, sh)
    return (f'<li class="pk"><b class="rk">{n}</b>{thumb(p)}<div><span class="mc">{html.escape(chip_of(p))}</span><h3><a href="{BASE}p/{i}.html">{html.escape(name)}</a></h3>'
            + (f'<div class="pr">{html.escape(shown)}</div>' if shown else "") + "".join(f'<div class="ex">{html.escape(x)}</div>' for x in ex[:1])
            + "".join(f'<div class="u">{html.escape(x)}</div>' for x in grey[:1]) + "</div>"
            + f'<a class="go" href="{html.escape(go_url(i, p))}" rel="nofollow {"sponsored " if aff(p.get("url")) else ""}noopener" target="_blank" aria-label="{html.escape(name)} 보러 가기">보기</a></li>')  # 쿠팡 생 주소(딥링크 전 진열 — 10/25) = 제휴 X


def items(posts, days, home=None):
    """사이트 진열 목록 [(i, p, 상태)] = home_pool 전부: 🔥 특가(🔁 다시 특가 먼저) → ⏳ 👍 꾸준템 → ⏳ 대기 → 일시 품절, 같은 단계는 진우 상품 먼저, 그다음 최신(같은 시간대 = 사진 있는 것 먼저)."""
    home = home_pool(posts, days) if home is None else home
    ds = [(i, posts[i]) for i in sorted(home, reverse=True)]
    ds.sort(key=lambda x: (home[x[0]][0], not home[x[0]][4], not x[1].get("own")))
    g = itertools.groupby(((i, p, home[i]) for i, p in ds), key=lambda x: (x[2][0], x[2][4], bool(x[1].get("own")), x[1]["t"][:13]))
    return [x for _, xs in g for x in sorted(xs, key=lambda x: not img_of(x[1]))]  # 같은 단계·같은 시간대(이웃) 안에서 사진 있는 상품 먼저(10/24 Cowork A④ — 날 단위면 새 글이 🔥 줄에서 밀림)


def steady_of(x):
    """👍 꾸준히 주문 들어오는 것(KK② 10/26 — 예전 '꾸준히 팔리는 것'): 진우 상품 중 👍 글(꾸준템 머리)·stdy(own_end — 토스 리뷰·쿠팡 👍), 일시 품절 X."""
    i, p, sh = x
    return p.get("own") and sh[0] != 3 and (p.get("stdy") or icon_of(p["text"]) == "👍")


def wait_order(xs):
    """⏳ 대기 목록: 특가 때 가격과 차이 작은 순(쿠팡·네이버 = 지금 확인가 now / 목표가 tgt, 토스는 지금 가격을 안 써서 뒤 — 👍 먼저, 최신)."""
    won = lambda s: int(re.sub(r"\D", "", (s or "").split("·")[0]) or 0)
    gap = lambda p: won(p.get("now")) / won(p.get("tgt")) if won(p.get("now")) and won(p.get("tgt")) else None
    return sorted(xs, key=lambda x: (gap(x[1]) is None, gap(x[1]) or 0, x[2][0]))


def lists(posts, days, home=None):
    """목록 쪽 {주소 이름: (제목, 한 줄 설명, [(i, p, 상태)], 대가성 몰 문구 키)} — /c/이름/ 20개씩(PER). 빈 목록은 쪽 X(특가·카테고리 쪽은 늘)."""
    it, today = items(posts, days, home), time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600))
    out = {"hot": ("🔥 지금 특가", "핫딜픽이 고른 상품 중 지금 특가 가격대인 것 · 🔁 = 특가 가격으로 다시 돌아온 상품", trust8([x for x in it if x[2][0] == 0], today), ""),
           "steady": ("👍 꾸준히 주문 들어오는 것", "최저가는 아니어도 주문이 꾸준한 것", [(i, p, (1,) + sh[1:]) for i, p, sh in it if steady_of((i, p, sh))], ""),  # 배지 = 👍 꾸준템(흰) — 🔥 칸과 구분
           "wait": ("⏳ 특가 기다리는 상품", "지금은 특가가 아닌 추천 상품 · 특가 때 가격으로 돌아오면 🔁 다시 특가로 올려요", wait_order([x for x in it if x[1].get("own") and x[2][0] in (1, 2)]), "")}
    for k in CAT_META:
        slug, name, emo, _ = CAT_META[k]
        out[slug] = (f"{emo} {name} 특가 모음", f"{name} 특가·핫딜을 매일 골라 정리해요 · 🔥 특가 중인 것 먼저", trust8([x for x in it if cat_of(x[1]) == k], today), "")
    for k, name, emo in MALLS:
        xs = [x for x in it if shop_of(x[1]) == k and (k != "toss" or toss_share(x[1].get("url")))]
        out[k] = (f"{emo} {name} 특가 모음", f"{name} 특가만 모았어요", trust8(xs, today, key=(lambda x: (x[2][0], cat_of(x[1]) != "digital")) if k == "naver" else None), k)  # 네이버 = 가전·디지털 먼저(같은 단계 안 — 10/24 진우 v3 ⑥)
    return out


def pick_score(x, recs):
    """오늘의 픽 순서(10/24 진우 '🔁 다시 특가 > 🔥 중 단위가 좋은 것'): 🔁 → 가격이 새것 → 단위가 좋음(최저가 기록 싼 3위 안·30일 최저가·다른 몰보다 쌈) → 진우 상품 → 최신."""
    i, p, sh = x
    low = {r[2] for _, _, rows in recs.values() for r in rows[:3]}
    good = i in low or re.search(r"30일\s*(?:내\s*)?최저가", p["text"]) or saving(p["text"])
    fresh = sh[1] is not None or p["t"][:10] >= time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600 - 2 * 86400))  # 지금 가격 확인됨 또는 사흘 안 글(옛 가격만 있는 픽 X)
    m, k = time.gmtime(time.time() + 9 * 3600).tm_mon, season_item(title_of(p["text"]))
    insea = k and not season_off(k, m) and (k != "between" or m in (3, 4, 9, 10, 11))  # 제철(Z +1 — hotdeal season_adj와 같은 달 기준, 철 지난 건 pick_off)
    return (not sh[4], not fresh, not good, not insea, not p.get("own"), not img_of(p), -i)  # 같은 점수 = 제철 -> 사진 있는 것 먼저(10/24 Cowork A④)


def pick_off(x):
    """픽에서 뺄 상품(Z 10/26): 철 지난 계절 상품(달 기준 — 사이트 진열은 그대로) · 오늘 확인 안 된 토스(게시 시점 가격·1일 원칙 — 10/26 픽의 10/24 토스 가격: 오늘 글도 오늘 API 확인(own_end chk)도 아님)."""
    k = time.gmtime(time.time() + 9 * 3600)
    return season_off(season_item(title_of(x[1]["text"])), k.tm_mon) or shop_of(x[1]) == "toss" and x[1]["t"][:10] != time.strftime("%Y-%m-%d", k) \
        and not (x[1].get("chk") or "").startswith(f"{k.tm_mon}/{k.tm_mday} ") \
        or ev_old(x[1], k)


PICK_EVENT = r"체험(?!팩)|이벤트|응모|추첨"  # Y-3(10/26 픽 '유순 센텔라 크림 100원(10/25 21시 글)'): 이벤트·체험가 = 그날 지나면(오늘 확인 없으면) 픽 X


def ev_old(p, k):
    """이벤트·체험가 글(이름에 체험·이벤트·응모·추첨 또는 1,000원 안 가격)이 어제 이전 글(KST 날짜 — 24시간 넘은 것 + 어제 밤 글도: 픽은 아침에 고정)이고 오늘 확인(chk)도 없음 -> True (k = 지금 KST struct_time)."""
    t = p.get("t") or ""
    if t[:10] >= time.strftime("%Y-%m-%d", k) or (p.get("chk") or "").startswith(f"{k.tm_mon}/{k.tm_mday} "):
        return False
    _, name, price = parse(title_of(p["text"]))
    w = re.search(r"(\d[\d,.]*)\s*원", price or "")  # '31.170원' = 31,170원(점으로 쓴 글)
    return bool(re.search(PICK_EVENT, name or "") or w and int(re.sub(r"[,.]", "", w[1])) < 1000)


def choose_picks(it, recs, n=PICK_N, avoid=()):
    """🔥 상품에서 n개: 몰 섞기(쿠팡·토스·네이버 한 개씩 먼저 — 가격 새것만, 모자라면 순서대로). avoid = 전날 픽 주소(하루 1번 바뀜 — 다른 후보가 모자랄 때만 다시)."""
    key = lambda x: (x[1].get("url") in avoid, pick_score(x, recs))
    it = [x for x in it if not pick_off(x)]
    cand = sorted((x for x in it if x[2][0] == 0 and x[1].get("own") and aff(x[1].get("url"))), key=key) or sorted((x for x in it if x[2][0] == 0 and not x[1].get("own")), key=key)  # 진우 상품 = 제휴 링크만(쿠팡 생 주소 진열 X — 픽 = Threads '🎯 오늘의 픽'에도 나감, 10/25 리뷰)
    out, malls = [], set()
    for x in cand:
        if len(out) < n and shop_of(x[1]) not in malls and not pick_score(x, recs)[1]:  # 몰 섞기는 가격이 새것끼리만(옛 가격 몰 상품을 억지로 X)
            out.append(x)
            malls.add(shop_of(x[1]))
    return (out + [x for x in cand if x not in out])[:n]


def today_picks(posts, it, recs, out):
    """오늘의 픽 (날짜, [(i, p, 상태)]): docs/today/picks.json에 날짜마다 1번 고정(PICK_HOUR 뒤 첫 빌드) — 그 전엔 가장 최근 날짜 것.
    그날 안에 진열에서 빠지거나 일시 품절이 된 픽은 그 자리를 다음 후보로(저장은 그대로)."""
    kst = time.gmtime(time.time() + 9 * 3600)
    today, f = time.strftime("%Y-%m-%d", kst), f"{out}/{PICKS}"
    try:
        saved = json.load(open(f))
    except (OSError, ValueError):
        saved = {}
    by = {x[0]: x for x in it}
    prev = max((d for d in saved if d < today), default=None)
    avoid = {posts[i].get("url") for i in saved.get(prev, []) if i < len(posts)} - {None}
    if today not in saved and kst.tm_hour >= PICK_HOUR and (ch := choose_picks(it, recs, avoid=avoid)):
        saved[today] = [x[0] for x in ch]
        os.makedirs(os.path.dirname(f), exist_ok=True)
        json.dump(saved, open(f, "w"))
    day = max((d for d in saved if d <= today), default=None)
    if not day:
        return None, []
    keep = [by[i] for i in saved[day] if i in by and by[i][2][0] != 3 and not pick_off(by[i])]
    return day, (keep + [x for x in choose_picks(it, recs, PICK_N + len(keep), avoid) if x not in keep])[:PICK_N]  # 10시 전(전날 픽)도 빠진 자리 채움 — 날짜 쪽은 저장 목록대로(build)


def pick_section(day, ps, page=False):
    """오늘의 픽 칸(핑크 — 10/24 진우 'A 기본 + B 포인트'): 'TODAY'S PICK · M/D' + '고민은 줄이고, 오늘은 이 3개만 보세요' + 3줄. 날짜 쪽 링크."""
    if not ps:
        return ""
    md = f"{int(day[5:7])}/{int(day[8:10])}"
    return (f'<section class="tp" id="pick" aria-labelledby="tph"><div class="k">TODAY\'S PICK · {md}</div><h2 id="tph">고민은 줄이고, 오늘은 이 {len(ps)}개만 보세요</h2>'
            f'<p class="d">특가 중인 것 중 단위가격 좋은 것·다시 특가로 돌아온 것을 몰마다 골랐어요</p><ol style="list-style:none;margin:0;padding:0">'
            + "".join(pick_row(n, i, p, sh) for n, (i, p, sh) in enumerate(ps, 1)) + "</ol>" + (f'<p class="pn">{TOSS_LINE}</p>' if any(shop_of(p) == "toss" for _, p, _ in ps) else "")
            + (lambda n: f'<p class="pn">{n}</p>' if n else "")(" ".join(dict.fromkeys(SHOP_NOTES[shop_of(p)] for _, p, _ in ps if shop_of(p) in SHOP_NOTES and aff(p.get("url")))))  # '보기'가 몰로 바로 -> 바로 아래 그 몰 대가성 문구 그대로(옛 홈 = 몰 칸 맨 위) — 맨 위 회색 덩어리는 사이트 공통 1개 그대로
            + ("" if page else f'<a class="u" style="display:block;padding:4px 0 10px;text-align:right;text-decoration:none" href="{BASE}today/{day}/">{md} 오늘의 픽 쪽 →</a>') + "</section>")


def tiles(keys=TILES, six=False):
    """카테고리 타일(4×2, 옆으로 밀기 X): 흰 r18 + 40px 파스텔 네모 이모지 -> /c/slug/ · six = 2줄(칸 13개 = 7칸씩 — 10/26 자동차 칸 뒤 3줄째 1개 X)."""
    return (f'<nav class="tiles{" t6" if six else ""}"' + (f' style="--n:{-(-len(keys) // 2)}"' if six else "") + ' aria-label="카테고리">' + "".join(f'<a class="tile" href="{c_url(CAT_META[k][0])}"><i style="--c:{CAT_META[k][3]}" aria-hidden="true">{CAT_META[k][2]}</i>{CAT_META[k][1].split("·")[0].split()[0]}</a>'
                                                              for k in keys) + "</nav>")


def top4(sid, slug, head, xs, skip=()):
    """홈 섹션: TOP 4(2×2) + '… 전체 보기 →' 큰 버튼. skip = 바로 위 오늘의 픽 글 번호(같은 상품 두 번 X — 개수는 전체)."""
    return "" if not xs else (f'<section class="sec" id="{sid}" aria-labelledby="{sid}h"><h2 id="{sid}h">{head}<small>{len(xs)}개</small></h2><div class="cards">'
                   + "".join(card(i, p, sh) for i, p, sh in [x for x in xs if x[0] not in skip][:4]) + f'</div><a class="all" href="{c_url(slug)}">{head.split(" ", 1)[1]} 전체 보기 →</a></section>')


def chips_html(cur):
    """목록 쪽 칩(링크): 상태(특가·꾸준템·대기) · 품목 12칸 · 몰 3곳 — 몰 구분은 탭 대신 칩으로(10/24 진우)."""
    ks = [("hot", "🔥 특가"), ("steady", "👍 꾸준템"), ("wait", "⏳ 대기")] + [(m[0], f"{m[2]} {m[1]}") for m in CAT_META.values()] + [(k, f"{e} {n}") for k, n, e in MALLS]
    return ('<nav class="chips" aria-label="목록">' + "".join(f'<a href="{c_url(s)}"' + (' aria-current="page"' if s == cur else "") + f">{t}</a>" for s, t in ks) + "</nav>"
            + "<script>(function(a){if(a)a.parentNode.scrollLeft=a.offsetLeft-16})(document.querySelector('.chips [aria-current]'))</script>" * bool(cur))  # 옆으로 밀기 한 줄 — 지금 칸이 보이게


EV_KINDS = (("쌀", r"쌀|현미|찹쌀|잡곡"), ("수산", r"새우|꽃게|홍게|대게|킹크랩|갈치|고등어|오징어|굴비|조기|전복|굴(?=[\s\d(]|$)|연어|광어|대하|낙지|문어|멸치|과메기|꼬막|홍합|가리비|생선"),
            ("고구마·땅콩", r"고구마|감자|땅콩|밤(?=[\s\d(]|$)|호두|잣(?=[\s\d(]|$)|견과"), ("김·김장", r"김(?=[\s\d,()]|$)|김장|절임배추|배추|무(?=[\s\d(]|$)|고춧가루|젓갈|표고|버섯"),
            ("과일", r"감귤|귤(?=[\s\d(]|$)|사과|배(?=[\s\d(]|$)|샤인머스[캣켓]|포도|단감|홍시|키위|딸기|한라봉|레드향|천혜향|곶감|자두|복숭아|참외|수박|멜론"))  # 행사 쪽 소제목(이 순서로 찾음 — 배추·꿀밤고구마가 과일로 안 가게)
EV_ORDER = ("쌀", "과일", "고구마·땅콩", "수산", "김·김장")  # 쪽 순서(10/24 Cowork) — 못 찾은 것 = '그 밖'(맨 뒤), events "kind"가 있으면 그것
MALL_KO = {"coupang": "쿠팡", "toss": "토스", "naver": "네이버"}
MICONS = set()  # V: out/icons/mall/에 있는 몰 로고(build가 채움 — 봇 mall_icons가 공식 앱 아이콘·파비콘을 1번 받아 둠)


def mall_logo(k, cls="lw"):
    """몰 로고(V 10/26 Cowork): 흰 동그라미 안 + 여백(그림 64% · 네이버 N = 44%(W — 토스 그림과 눈으로 같은 크기) — 자르기·늘리기·색 바꾸기 X, object-fit contain) · alt = 몰 이름(늘 옆에 몰 글자가 있어 감싼 칸은 aria-hidden — 화면 읽기 두 번 X).
    네이버 = si/naver.svg 모양 그대로 + 브랜드 색 #03C75A · 쿠팡·토스 = icons/mall/<몰>.png · 없으면 지금 이모지(🚀·💙)를 같은 흰 동그라미에(W — 쇼핑몰 흰 동그라미 묶음)."""
    nm = MALL_KO[k]
    if k == "naver":
        d = re.search(r'<path d="([^"]+)"', open(f"{SI_DIR}/naver.svg").read())[1]
        return f'<i class="{cls}" aria-hidden="true"><svg viewBox="0 0 24 24" role="img" aria-label="{nm}"><path fill="#03C75A" d="{d}"/></svg></i>'
    return f'<i class="{cls}" aria-hidden="true">' + (f'<img src="/icons/mall/{k}.png" alt="{nm}">' if k in MICONS else {e: x for e, _, x in MALLS}[k]) + "</i>"


def mall_label(k, n):
    """'🚀 쿠팡' -> 흰 동그라미(로고·없으면 이모지) + '쿠팡'(글자 그대로)."""
    return mall_logo(k) + n.split(" ", 1)[1]


def ev_day(u, today):
    """events until -> 'YYYY-MM-DD'(없는 날짜·다른 모양 = '' — 손으로 쓴 값 하나가 빌드를 멈추거나 행사 전체를 내리지 않게) · 'M/D'·'~10/25' = 올해."""
    m = re.fullmatch(r"~?\s*(?:(\d{4})[-/.])?(\d{1,2})[-/.](\d{1,2})", str(u or "").strip()[:16].split(" ")[0])
    d = m and f"{m[1] or today[:4]}-{int(m[2]):02d}-{int(m[3]):02d}"
    try:
        return d if d and time.strptime(d, "%Y-%m-%d") else ""
    except ValueError:
        return ""


def events_on(it, today):
    """진행 중 기획전(10/24 Cowork '기획전 = 배너 + 행사 쪽' — 진우 '홈을 도배하지 말고 배너로'): events "tag"(정품 X)마다 마감 = 그 tag 항목 중 가장 늦은 "until"(YYYY-MM-DD) ≥ 오늘이고
    진열 중인 상품(같은 url) 1개↑ -> [{"tag", "slug", "until", "chk", "mall", "urls": {url: kind}, "xs": [(i, p, 상태)]}] 마감 빠른 순. until 없는 tag = 행사 아님(배너 X).
    slug = events "slug"(영문 소문자·숫자·-) 또는 tag 해시('e' + 6자 — 같은 tag면 늘 같은 주소)."""
    evs, gs = ev_list(), {}
    for e in evs if isinstance(evs, list) else []:
        if isinstance(e, dict) and isinstance(e.get("tag"), str) and e["tag"].strip() and e["tag"] != "정품" and isinstance(e.get("url"), str):
            g = gs.setdefault(e["tag"], {"tag": e["tag"].strip(), "until": "", "chk": "", "slug": "", "urls": {}})
            g["until"], g["chk"] = max(g["until"], ev_day(e.get("until"), today)), max(g["chk"], str(e.get("chk") or "")[:16])
            g["slug"] = g["slug"] or (e["slug"] if re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}", str(e.get("slug") or "")) else "")
            g["urls"][e["url"]] = str(e.get("kind") or g["urls"].get(e["url"]) or "")
    out = []
    for g in gs.values():
        xs = [x for x in it if x[1].get("url") in g["urls"]]
        if xs and g["until"] >= today:
            ms = {shop_of(p) for _, p, _ in xs}
            out.append({**g, "slug": g["slug"] or "e" + hashlib.md5(g["tag"].encode()).hexdigest()[:6], "xs": xs, "mall": MALL_KO.get(ms.pop(), "") if len(ms) == 1 else ""})
    return sorted(out, key=lambda g: (g["until"], g["tag"]))


def ev_n(g):
    """행사 상품 수(일시 품절 뺌)."""
    return sum(x[2][0] != 3 for x in g["xs"])


def ev_name(g):
    """'쿠팡 햇상품 기획전'(상품이 한 몰이면 몰 이름 앞에 — tag에 이미 있으면 그대로)."""
    return g["tag"] if not g["mall"] or g["tag"].startswith(g["mall"]) else f"{g['mall']} {g['tag']}"


EV_JS = """<script>(function(){var b=document.querySelector('.evb'),s=b&&b.querySelector('.evs'),n=b&&b.querySelector('.evn span');if(!s||!n)return;var k=s.children.length,p=0,cur=function(){return Math.round(s.scrollLeft/(s.clientWidth||1))};
s.addEventListener('scroll',function(){n.textContent=Math.min(k,cur()+1)},{passive:true});['pointerdown','touchstart','focusin','mouseenter'].forEach(function(e){b.addEventListener(e,function(){p=1},{passive:true})});
if(!(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches))setInterval(function(){if(!p&&!document.hidden)s.scrollTo({left:(cur()+1)%k*s.clientWidth,behavior:'smooth'})},4000)})()</script>"""  # 기획전 넘김: 4초마다 다음(손대면·포커스·숨은 탭·움직임 줄이기 = 멈춤) · 밀면 '1/3' 따라감


def ev_banner(evs):
    """홈 기획전 넘김 배너(포털형 2차 ② — 헤더 바로 아래 84px, 행사마다 1장 → e/slug.html · 2개↑ = 4초 넘김 + '1/3'): '🎉 쿠팡 햇상품 기획전' / '핫딜픽이 고른 N개 · ~M/D' + '보기 →'.
    클릭 = GoatCounter 이벤트 'banner/slug'(GC_JS) — 팝업은 X(10/24 Cowork: 모바일 첫 화면 가리면 이탈↑·구글 '방해되는 전면 광고') · 아래쪽 띠 줄은 없음(진우 v3 ①)."""
    md = lambda d: f"{int(d[5:7])}/{int(d[8:10])}"
    return "" if not evs else ('<nav class="evb" aria-label="기획전"><div class="evs">' + "".join(
        f'<a class="ev" href="{BASE}e/{g["slug"]}.html" data-ev="{g["slug"]}"><span class="em" aria-hidden="true">🎉</span><span class="tx"><b>{html.escape(ev_name(g))}</b>'
        f'<small>핫딜픽이 고른 {ev_n(g)}개 · ~{md(g["until"])}</small></span><span class="go">보기 →</span></a>' for g in evs) + "</div>"
        + (f'<b class="evn" aria-hidden="true"><span>1</span>/{len(evs)}</b></nav>{EV_JS}' if len(evs) > 1 else "</nav>"))


PROMO_LP_NOTE = "이 포스팅은 제휴마케팅이 포함된 광고로 커미션을 지급 받습니다."  # 링크프라이스 머천트 문구 그대로(hotdeal.AFF_NOTE — 셀프체크로 맞춤)
PROMO_OY_NOTE = "이 포스팅은 올리브영 쇼핑 큐레이터 활동의 일환으로, 구매 시 일정 금액의 수수료를 제공받습니다."  # hotdeal.OY_NOTE 그대로
PROMOS, PROMO_LINKS, PROMO_SOON, PROMO_PAST = "promos.json", "promo_links.json", 7, 3  # 쇼핑몰 기획전(10/25 진우 '스스로 여러 기획전 찾아서 깔끔하고 이쁘게' — Cowork 매일 17:30 기사 근거) · 봇이 만든 링크프라이스 딥링크(hotdeal.promo_links) · 홈 띠 '곧 시작' = 7일 안 · /events/ 지난 행사 3개
MALL_C = {"coupang": ("#D9402A", "#fff", "#C2362A", "쿠"), "11st": ("#E8264A", "#fff", "#D11F40", "11"), "ssg": ("#FFC72C", "#14161B", "#8A6200", "S"), "gmarket": ("#13924A", "#fff", "#0F7A3D", "G"),
          "auction": ("#E51E25", "#fff", "#C8191F", "A"), "lotteon": ("#E3262E", "#fff", "#C8202A", "L"), "oliveyoung": ("#7FB82E", "#14161B", "#4E7A12", "올"), "emart": ("#FFC72C", "#14161B", "#8A6200", "e")}  # 몰 색(바탕·바탕 위 글자·연한 바탕 위 글자·로고 없을 때 글자) — 10/25 Cowork 토큰 · 모르는 몰 = 회색
PROMO_DATE = r"\d{4}-\d{2}-\d{2}"


def promo_list(today):
    """promos.json -> [(항목, 상태, 첫날)] 상태 순(오늘 마감 'end' → 진행 중 'on'(사전 행사 중도) → 곧 시작 'soon' → 지난 'past'). 깨진 파일 = [](칸 숨김) · 모양이 틀린 항목 = 뺌
    (HTML·주소·파일 이름에 들어가는 값: id·mall = 영문 소문자·숫자, 주소 = https, 색 = #hex, 날짜 = YYYY-MM-DD)."""
    try:
        d = json.load(open(PROMOS))
    except (OSError, ValueError):
        return []
    def day(v):  # 형식 + 진짜 날짜(11-31 = 뺌 — 빌드가 멈추면 그 실행 게시가 다음 실행에 또 나감)
        try:
            return v is None or isinstance(v, str) and re.fullmatch(PROMO_DATE, v) and time.strptime(v, "%Y-%m-%d")
        except ValueError:
            return False
    https = lambda v: v is None or isinstance(v, str) and v.startswith("https://") and not re.search(r"\s", v)
    out = []
    for p in (d.get("promos") if isinstance(d, dict) and isinstance(d.get("promos"), list) else []):
        if not (isinstance(p, dict) and isinstance(p.get("id"), str) and isinstance(p.get("mall"), str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}", p["id"]) and re.fullmatch(r"[a-z0-9]{1,20}", p["mall"])  # 숫자 id·mall = 뺌(정렬·글자 자르기에서 빌드가 멈춤 — 10/25 리뷰)
                and isinstance(p.get("name"), str) and p["name"].strip() and day(p.get("start")) and day(p.get("end")) and https(p.get("url"))
                and (p.get("pre") is None or isinstance(p["pre"], dict) and day(p["pre"].get("start")) and day(p["pre"].get("end")))
                and (p.get("cta") is None or isinstance(p["cta"], dict) and https(p["cta"].get("href"))) and (p.get("color") is None or re.fullmatch(r"#[0-9A-Fa-f]{6}", str(p["color"])))
                and all(p.get(k) is None or isinstance(p[k], str) for k in ("tag", "kw", "mall_name", "sub", "benefit")) and (p.get("cta") is None or p["cta"].get("text") is None or isinstance(p["cta"]["text"], str))):
            continue
        first = (p.get("pre") or {}).get("start") if promo_pre(p, today) else p.get("start")
        st = "past" if p.get("end") and p["end"] < today else "end" if p.get("end") == today else "soon" if first and first > today else "on"
        out.append((p, st, first or ""))
    rank = {"end": 0, "on": 1, "soon": 2, "past": 3}
    return sorted(out, key=lambda x: (rank[x[1]], x[2] if x[1] == "soon" else "", (x[0].get("end") or "9999") if x[1] != "past" else "", x[0]["id"]))


def promo_pre(p, today):
    """사전 행사가 아직 남음(끝나지 않았고 본 행사 전) — 끝난 사전 행사 = 본 행사 첫날까지 '곧 시작'(10/25 리뷰)."""
    pre = p.get("pre") or {}
    return bool(pre.get("start")) and not (pre.get("end") and pre["end"] < today) and not (p.get("start") and p["start"] <= today)


def promo_span(a, b, short=False):
    """기간 글자: '11.1–11.11' · '10.12~'(끝 미발표) · '~10.25' · short = 같은 달이면 '10.26–31'(사전 행사)."""
    md = lambda d: f"{int(d[5:7])}.{int(d[8:10])}"
    return (f"{md(a)}–{int(b[8:10]) if short and a[:7] == b[:7] else md(b)}" if a and b else f"{md(a)}~" if a else f"~{md(b)}" if b else "")


def promo_chip(p, st, today):
    """상태 칩: 오늘 마감(빨강) · 진행 중/사전 행사 중(연두) · D-n(검정 — 첫날까지)."""
    if st == "soon":
        return f'<b class="pvs soon">D-{promo_days(today, (p.get("pre") or {}).get("start") if promo_pre(p, today) else p["start"])}</b>'
    return {"end": '<b class="pvs end">오늘 마감</b>', "past": '<b class="pvs past">끝남</b>'}.get(st) or \
        f'<b class="pvs on">{"사전 행사 중" if promo_pre(p, today) else "진행 중"}</b>'


def promo_days(a, b):
    """a -> b 날 수(YYYY-MM-DD)."""
    return (calendar.timegm(time.strptime(b, "%Y-%m-%d")) - calendar.timegm(time.strptime(a, "%Y-%m-%d"))) // 86400


def promo_mall(p, icons):
    """(style 변수, 로고 HTML, 몰 이름): 로고 = docs/icons/mall/<몰>.png(봇이 1번 받아 둠 — 바깥 주소 실시간 X), 없으면 흰 칸에 몰 글자."""
    c, fg, tx, ch = MALL_C.get(p["mall"], ("#4B5563", "#fff", "#4B5563", (p.get("mall_name") or p["mall"])[:1]))
    if p.get("color"):
        c, fg, tx = p["color"], "#fff", p["color"]
    sty = f"--m:{c};--mf:{fg};--mt:{tx}" + (";--mb:#FFF8E3" if p["mall"] in ("ssg", "emart") and not p.get("color") else "")
    mn = str(p.get("mall_name") or p["mall"]).strip()
    lg = f'<img src="/icons/mall/{p["mall"]}.png" width="12" height="12" alt="{html.escape(mn)}">' if p["mall"] in icons else html.escape(ch)  # V: 흰 동그라미 · alt = 몰 이름
    name = " ".join(x for x in (mn, str(p.get("sub") or "").strip()) if x)
    return sty, f'<i class="mlg" aria-hidden="true">{lg}</i>', name  # 옆에 몰 이름 글자 = 화면 읽기 1번


def promo_goods(p, it, tagged):
    """그 행사 상품(일시 품절 뺌 · it = 사이트 진열 = site_ok만): tag = events·posts 그 tag 상품 + kw = 이름에 검색어 낱말이 다 든 진열 상품(둘 다 있으면 합침 — AA 쿠가세)."""
    us = tagged.get(str(p["tag"]), set()) if p.get("tag") else set()
    kw = p["kw"].split() if isinstance(p.get("kw"), str) else []
    return [x for x in it if x[2][0] != 3 and (x[1].get("url") in us or kw and all(k in parse(title_of(x[1]["text"]))[1] for k in kw))]


def promo_go(p, xs, slugs, links, past=False):
    """(주소, rel·target 붙일 바깥 링크?): tag 상품 = 행사 쪽(e/slug.html) · kw 상품 = 홈 검색(?q=) · 아니면 행사 주소(url·cta.href)를 봇이 링크프라이스 딥링크로 바꾼 것(promo_links.json),
    아직·실패면 몰 홈 그대로(수수료 길이 있는 몰 = SITE_KEEP_HOSTS — 10/25 20:3x 최종 규칙 ②) · 그 밖(11번가 등) = ('', False)."""
    if xs and p.get("tag") in slugs:
        return f"{BASE}e/{slugs[p['tag']]}.html", False
    q = p.get("kw") if past else p.get("tag") or p.get("kw")  # 행사 쪽 없는 tag = tag 낱말 홈 검색(search_index가 행사 상품에 tag 낱말 — kw 상품까지) · 지난 행사 = kw만(tag 낱말은 검색에 X)
    if xs and q:
        return f"{BASE}?q={urllib.parse.quote(q)}", False
    us = [u for u in (p.get("url"), (p.get("cta") or {}).get("href")) if u]
    v = next((links[u] for u in us if isinstance(links.get(u), str) and links[u].startswith(("https://", "http://")) and aff(links[u])), "") or next((u for u in us if aff(u) or keep_host(u)), "")
    return (v, True) if v else ("", False)


def promo_shown(ps, it, tagged, links):
    """사이트에 보일 행사 = 진열 상품(tag·kw)이 있거나 행사 주소가 제휴 링크·수수료 길이 있는 몰(promo_go) — 수수료 길이 없는 몰만 있는 행사 = 숨김."""
    return [x for x in ps if promo_goods(x[0], it, tagged) or promo_go(x[0], [], {}, links)[0]]


def promo_a(href, ext, gc, inner, cls, extra=""):
    """링크: 바깥 = 새 창 + nofollow(제휴 링크면 sponsored) · GoatCounter 이벤트 promo/<id>(GC_JS data-gc)."""
    rel = f' rel="nofollow {"sponsored " if aff(href) else ""}noopener" target="_blank"' if ext else ""
    return f'<a class="{cls}" href="{html.escape(href)}"{rel} data-gc="{gc}"{extra}>{inner}</a>'


def promo_won(x):
    m = re.search(r"[\d,]+원", price_bits(x[1], x[2])[0] or "")
    return m[0] if m else ""


def promo_card(p, st, xs, go, icons, today):
    """/events/ 카드(시안 A 작게 — 10/25 진우): 연한 몰 색 바탕 r16 · [글 | 오른쪽] — 로고·몰 이름·상태 칩 / 행사명 한 줄 / 기간 · 혜택 한 줄 / CTA,
    오른쪽 = 행사 상품 중 사진 있는 🔥 3개(48px + 가격) · 없으면 흰 날짜 칸(본 기간 + '사전 …')."""
    sty, lg, mall = promo_mall(p, icons)
    pre, href, ext = p.get("pre") or {}, *go
    pics = [x for x in xs if x[2][0] == 0 and img_of(x[1])][:3]
    right = ("".join(f'<span class="pvp"><span><img src="{html.escape(img_of(x[1]))}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="this.remove()"></span><small>{promo_won(x)}</small></span>' for x in pics) if pics
             else f'<span class="pvd"><b>{promo_span(p.get("start"), p.get("end")) or "진행 중"}</b>' + (f'<small>사전 {promo_span(pre.get("start"), pre.get("end"), True)}</small>' if pre.get("start") else "") + "</span>")
    info = " · ".join(x for x in (promo_span(p.get("start"), p.get("end")), str(p.get("benefit") or "").strip()) if x)
    cta = promo_a(href, ext, f"promo/{p['id']}", f"핫딜픽이 고른 {len(xs)}개 →" if not ext else "행사 보러 가기 →", "pvc") if href else ""
    return (f'<article class="pv" id="{p["id"]}" data-s="{st}" style="{sty}"><div class="pvt"><div class="pvh">{lg}<b class="pvm">{html.escape(mall)}</b>{promo_chip(p, st, today)}</div>'
            f'<h2 class="pvn">{html.escape(p["name"].strip())}</h2>' + (f'<p class="pvi">{html.escape(info)}</p>' if info else "") + f'{cta}</div><div class="pvr">{right}</div></article>')


PROMO_DOTS_JS = """<script>(function(){var s=document.querySelector('.pbs'),d=document.querySelectorAll('.pbd i');if(!s||d.length<2)return;s.addEventListener('scroll',function(){var w=(s.firstElementChild.offsetWidth||250)+8,k=s.scrollLeft+s.clientWidth>=s.scrollWidth-4?d.length-1:Math.round(s.scrollLeft/w);
[].forEach.call(d,function(x,j){x.className=j===k?'on':''})},{passive:true})})()</script>"""  # 홈 기획전 띠 아래 점 = 지금 보이는 칸
PROMO_FILTER_JS = """<script>(function(){var b=document.querySelectorAll('.pf button');[].forEach.call(b,function(x){x.addEventListener('click',function(){var f=x.getAttribute('data-f');
[].forEach.call(b,function(y){y.setAttribute('aria-pressed',y===x?'true':'false')});[].forEach.call(document.querySelectorAll('.pvl .pv'),function(c){var s=c.getAttribute('data-s');c.hidden=!(f==='all'||f===s||f==='on'&&s==='end')})})})})()</script>"""  # /events/ 칩 = 화면 안에서만 거름(JS 꺼짐 = 전부 보임)


def promo_now(ps, today):
    """홈 띠에 나오는 행사 [(항목, 상태)] = 오늘 마감·진행 중 + PROMO_SOON일 안에 시작."""
    lim = time.strftime("%Y-%m-%d", time.gmtime(calendar.timegm(time.strptime(today, "%Y-%m-%d")) + PROMO_SOON * 86400))
    return [(p, st) for p, st, first in ps if st in ("end", "on") or st == "soon" and first <= lim]


def promo_band(ps, it, tagged, slugs, links, icons, today):
    """홈 맨 위 띠 '🎉 지금 하는 기획전'(시안 B 작게 — 10/25 진우): 오늘 마감 → 진행 중 → 곧 시작(PROMO_SOON일 안) 칸 250×112 · 진한 몰 색(쓱 = 글자 검정) · 링 장식 ·
    로고·몰·상태 칩 / 큰 날짜 / 행사명 / 상품 사진 동그라미 3개 · 옆으로 밀기 + 점 · 오른쪽 '전체 N →'(/events/) · 칸 누르면 = 그 행사 CTA(없으면 /events/#id) · GoatCounter promo/<id>."""
    show = promo_now(ps, today)
    if not show:
        return ""
    cells = []
    for p, st in show:
        xs = promo_goods(p, it, tagged)
        sty, lg, mall = promo_mall(p, icons)
        href, ext = promo_go(p, xs, slugs, links)
        pics = [x for x in xs if x[2][0] == 0 and img_of(x[1])][:3]
        when = promo_span(p.get("start"), p.get("end")) or promo_span((p.get("pre") or {}).get("start"), (p.get("pre") or {}).get("end")) or "진행 중"
        inner = (f'<span class="pbh">{lg}<b>{html.escape(mall)}</b>{promo_chip(p, st, today)}</span><b class="pbw">{html.escape(when)}</b><b class="pbn">{html.escape(p["name"].strip())}</b>'
                 + ('<span class="pbp" aria-hidden="true">' + "".join(f'<img src="{html.escape(img_of(x[1]))}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="this.remove()">' for x in pics) + "</span>" if pics else ""))
        cells.append(promo_a(href or f"{BASE}events/#{p['id']}", ext, f"promo/{p['id']}", inner, "pbi pbx" if pics else "pbi", f' style="{sty}" aria-label="{html.escape(mall + " " + p["name"].strip())}"'))  # pbx = 사진 동그라미 자리만큼 이름 줄임
    n = sum(st != "past" for _, st, _ in ps)
    return (f'<section class="pb" aria-labelledby="pbh"><div class="pbt"><h2 id="pbh">🎉 지금 하는 기획전</h2><a href="{BASE}events/" data-gc="promo/all">전체 {n} →</a></div><div class="pbs">{"".join(cells)}</div>'
            + (f'<div class="pbd" aria-hidden="true">{"".join("<i" + (" class=on" if k == 0 else "") + "></i>" for k in range(len(cells)))}</div>{PROMO_DOTS_JS}' if len(cells) > 1 else "") + "</section>")


def promo_page(ps, it, tagged, slugs, links, icons, today, updated=""):
    """/events/ '기획전 모음'(시안 A 작게 — 10/25 진우): 쇼핑 달력 줄(날짜·행사·D-day, 오늘 마감 = 검정 칸) → 칩(전체·진행 중·곧 시작) → 카드 → 지난 행사(접힘 PROMO_PAST개)
    + 맨 아래 대가성 문구(쿠팡 상품 칸이 있으면 쿠팡 파트너스 · 링크프라이스 링크가 있으면 그 문구 — 사실대로). -> (제목, 설명, 본문)."""
    live, past = [x for x in ps if x[1] != "past"], sorted((x for x in ps if x[1] == "past"), key=lambda x: x[0].get("end") or "", reverse=True)[:PROMO_PAST]
    dd = lambda p, st, first: ("오늘 마감" if st == "end" else f"D-{promo_days(today, first)}" if st == "soon"
                        else f"마감 D-{promo_days(today, p['end'])}" if p.get("end") else "진행 중")
    cal = ('<nav class="pcal" aria-label="쇼핑 달력">' + "".join(
        f'<a class="pcd{" k" if st == "end" else ""}" href="#{p["id"]}"><b>{promo_span(p.get("start") or (p.get("pre") or {}).get("start"), p.get("end"))}</b><span>{html.escape(p["name"].strip())}</span><i>{dd(p, st, first)}</i></a>'
        for p, st, first in sorted(live, key=lambda x: (x[2] or "0000", x[0]["id"]))) + "</nav>") if live else ""
    cards, gos = [], []
    for p, st, _ in live + past:
        xs = promo_goods(p, it, tagged)
        go = promo_go(p, xs, slugs, links, st == "past")
        gos.append((go, xs, p))
        cards.append(promo_card(p, st, xs, go, icons, today))
    n_on, n_soon = sum(st in ("end", "on") for _, st, _ in live), sum(st == "soon" for _, st, _ in live)
    chips = (f'<nav class="pf" aria-label="기획전 거르기"><button type="button" data-f="all" aria-pressed="true">전체 {len(live)}</button>'
             f'<button type="button" data-f="on" aria-pressed="false">진행 중 {n_on}</button><button type="button" data-f="soon" aria-pressed="false">곧 시작 {n_soon}</button></nav>') if live else ""
    def note(h, ext, xs):  # 링크 프로그램마다 그 문구 그대로(hotdeal.aff_note와 같은 나눔) · 안쪽(e/·검색) = 그 칸 쿠팡 상품이 제휴 링크일 때만(생 주소 = 수수료 X)
        host = urllib.parse.urlsplit(h or "").netloc
        if not ext:
            return SHOP_NOTES["coupang"] if any(shop_of(q) == "coupang" and aff(q.get("url")) for _, q, _ in xs) else ""
        return (SHOP_NOTES["coupang"] if host in CP_SHORT else SHOP_NOTES["toss"] if toss_share(h) else SHOP_NOTES["naver"] if host in NAVER_HOSTS
                else PROMO_OY_NOTE if host in OY_HOSTS else PROMO_LP_NOTE if aff(h) else "")
    notes = [n for n in dict.fromkeys(note(h, ext, xs) for (h, ext), xs, _ in gos) if n]
    mm = int(today[5:7])
    body = (f'<h1 class="h">🎉 쇼핑 기획전 모음</h1><div class="t">쇼핑몰 진행 중·곧 시작하는 행사{" · " + html.escape(updated) + " 확인" if updated else ""} · 기간·혜택은 기사 기준이라 바뀔 수 있어요</div>'
            + cal + chips + (f'<div class="pvl">{"".join(cards[:len(live)])}</div>' if live else '<p class="t">지금 정리된 기획전이 없어요. 매일 저녁 새로 찾아 올려요.</p>')
            + (f'<details class="pvx"><summary>지난 행사 {len(past)}</summary>{"".join(cards[len(live):])}</details>' if past else "")
            + (f'<p class="t pvnote">{" ".join(notes)}</p>' if notes else "") + PROMO_FILTER_JS)
    desc = f"{mm}월 쇼핑몰 기획전 기간·혜택 정리 — " + " · ".join(f"{(p.get('mall_name') or p['mall']).split(' · ')[0]} {p['name'].strip()}" for p, _, _ in live)
    return f"쇼핑 기획전 모음 ({mm}월) | {TITLE}", desc[:150], body


def unit_line(p):
    """글의 단위가 줄 조각('💰 100g당 339원꼴 · 와우 할인 중' -> '100g당 339원꼴', 없으면 unit_of)."""
    return re.sub(r"^단위\s*가격:?\s*", "", next((x for l in p["text"].split("\n") if l.startswith(("💰", "💡")) for x in l[1:].strip().split(" · ") if PAIR.search(x)), "") or unit_of(p))


def per_unit(p):
    """단위가 비교 값 (단위, 1단위 값) — '100g당 339원' -> ('g', 3.39) · '1kg당' = g, 'L' = ml로 · 못 읽으면 None(맨 뒤)."""
    m = PAIR.search(unit_line(p))
    q = m and re.fullmatch(r"(\d+(?:\.\d+)?)?\s*([^\d\s]+)", m[1].strip())
    if not q:
        return None
    k, f = {"kg": ("g", 1000), "l": ("ml", 1000)}.get(q[2].lower(), (q[2].lower(), 1))
    return k, float(m[2].replace(",", "")) / (float(q[1] or 1) * f)


def ev_page(g, today):
    """행사 쪽 docs/e/slug.html: 제목·N개·마감 D-day + '같은 종류 쿠팡 검색에서 단위가 하위 20%만 골랐어요 (M/D H시)' + 몰 대가성 문구 + 소제목(EV_ORDER, 그 밖 = 맨 뒤)마다 카드 — 단위가 싼 순(같은 단위끼리, 못 읽으면 뒤).
    -> (제목, 설명, 본문, JSON-LD)."""
    kind = lambda p: g["urls"].get(p.get("url")) or next((k for k, rx in EV_KINDS if re.search(rx, parse(title_of(p["text"]))[1])), "그 밖")
    grp = {}
    for x in g["xs"]:
        grp.setdefault(kind(x[1]), []).append(x)
    order = sorted(grp, key=lambda k: (k not in EV_ORDER, EV_ORDER.index(k) if k in EV_ORDER else 0, k == "그 밖", k))
    key = lambda x: (lambda u: (x[2][0] == 3, u is None, u or ("", 0)))(per_unit(x[1]))  # 일시 품절 = 칸 맨 뒤
    n, md, name, chk = ev_n(g), f"{int(g['until'][5:7])}/{int(g['until'][8:10])}", ev_name(g), g["chk"] and f" ({md_h(g['chk'])})"
    left = (calendar.timegm(time.strptime(g["until"], "%Y-%m-%d")) - calendar.timegm(time.strptime(today, "%Y-%m-%d"))) // 86400
    notes = " ".join(dict.fromkeys(SHOP_NOTES[shop_of(p)] for _, p, _ in g["xs"] if shop_of(p) in SHOP_NOTES and aff(p.get("url"))))  # 제휴 링크 상품만(쿠팡 생 주소 = 수수료 X — 10/25)
    body = (f'<h1 class="h">🎉 {html.escape(name)}</h1><div class="t">핫딜픽이 고른 {n}개 · ~{md} 마감 · <b class="dd">{"오늘 마감" if left <= 0 else f"D-{int(left)}"}</b></div>'
            + f'<p class="evn">같은 종류 {g["mall"] + " " if g["mall"] else ""}검색에서 단위가 하위 20%만 골랐어요{chk}</p>'
            + (f'<p class="t">{notes}</p>' if notes else "")
            + ('<nav class="chips" aria-label="종류">' + "".join(f'<a href="#k{j}">{html.escape(k)} {len(grp[k])}</a>' for j, k in enumerate(order)) + "</nav>" if len(order) > 1 else "")
            + "".join(f'<section class="sec" id="k{j}" aria-labelledby="k{j}h"><h2 id="k{j}h">{html.escape(k)}<small>{len(grp[k])}개</small></h2><div class="cards">'
                      + "".join(card(i, p, sh, [unit_line(p)]) for i, p, sh in sorted(grp[k], key=key)) + "</div></section>" for j, k in enumerate(order))
            + f'<a class="all" href="{BASE}">🏠 홈으로</a>')
    li = [{"@type": "ListItem", "position": m, "url": f"{BASE}p/{i}.html", "name": parse(title_of(p["text"]))[1], "image": img_of(p)} for m, (i, p) in enumerate(((i, p) for k in order for i, p, _ in sorted(grp[k], key=key) if img_of(p)), 1)]
    return (f"{name} — 핫딜픽이 고른 {n}개 (~{md}) | {TITLE}", f"{name} 상품 중 같은 종류 단위가 싼 것만 {n}개 골랐어요 · {' · '.join(order)} · ~{md} 마감", body,
            len(li) >= 3 and {"@context": "https://schema.org", "@type": "ItemList", "name": f"{name} (~{md})", "itemListElement": li})


IG_TOP = {}  # build()가 채움: {c/칸 slug: [(카드 이름, [(i, p)]) — 최근 것 먼저, 3개까지]} — 인스타 피드 게시물 번호 그대로(I-2)


def list_pages(slug, head, desc, xs, mall, recs):
    """목록 쪽들 [(주소, 쪽 번호, 제목, 설명, 본문, JSON-LD)]: 20개씩 + 다음·이전 쪽(검색 로봇이 따라감). 몰 쪽은 그 몰 대가성 문구 맨 위."""
    n = max(1, -(-len(xs) // PER))
    today = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600))
    md, name = f"{int(today[5:7])}/{int(today[8:10])}", head.split(" ", 1)[1]
    out = []
    for k in range(1, n + 1):
        part = xs[(k - 1) * PER:k * PER]
        url = c_url(slug, k)
        nav = ('<nav class="pg" aria-label="쪽">' + (f'<a class="btn2" href="{c_url(slug, k - 1)}" rel="prev">← 이전 20개</a>' if k > 1 else "")
               + (f'<a class="btn2" href="{c_url(slug, k + 1)}" rel="next">다음 20개 보기 →</a>' if k < n else "") + "</nav>") if n > 1 else ""
        body = (f'<h1 class="h">{html.escape(head)}{f" · {k}쪽" if k > 1 else ""}</h1><div class="t">{html.escape(desc)} · {len(xs)}개 · {md} 업데이트</div>'
                + ("".join(f'<section class="card" id="ig{j or ""}" aria-labelledby="igh{j or ""}"><h2 id="igh{j or ""}">📸 {html.escape(nm)}</h2><div class="t">인스타 게시물 번호와 같아요 · 누르면 바로 구매 페이지</div>{pick_rows(ps)}</section>'
                           for j, (nm, ps) in enumerate(IG_TOP.get(slug, []) if k == 1 else ())))
                + (f'<p class="t">{SHOP_NOTES[mall]}</p>' if mall else "") + (f'<p class="t">{TOSS_LINE}</p>' if any(shop_of(p) == "toss" for _, p, _ in part) else "") + (stat_chips(slug) if slug in dict(STAT_CHIPS) else chips_html(slug))
                + ('<nav class="chips" aria-label="몰">' + "".join(f'<a href="{c_url(k)}?s=h" data-gc="mall/{k}">{mall_label(k, n)}</a>' for k, n, _ in MALL_BTN) + "</nav>" if slug == "hot" else "")
                + (f'<div class="cards">{"".join(card(i, p, sh, plain=slug == "drop") for i, p, sh in part)}</div>' if part else '<p class="t" style="margin:18px 2px">지금은 이 목록에 상품이 없어요. 다른 칸을 둘러보세요.</p>')
                + nav + (rec_nav(recs) or "" if slug == "life" and k == 1 else "") + (f'<a class="btn2" href="{GOLDBOX}" rel="nofollow sponsored noopener" target="_blank">⏰ 쿠팡 골드박스</a>' if mall == "coupang" and k == 1 else ""))
        li = [{"@type": "ListItem", "position": m, "url": f"{BASE}p/{i}.html", "name": parse(title_of(p["text"]))[1], "image": img_of(p)} for m, (i, p) in enumerate(((i, p) for i, p, _ in part if img_of(p)), 1)]
        ld = len(li) >= 3 and {"@context": "https://schema.org", "@type": "ItemList", "name": f"{name} ({md})", "itemListElement": li}  # 네이버 캐러셀: 항목마다 진짜 상품 사진 필수(기본 그림 X) — 사진 있는 것만, 3개 미만이면 안 넣음
        out.append((url, k, f"{name}{f' {k}쪽' if k > 1 else ''} ({md}) | {TITLE}", f"{desc} — {name} {len(xs)}개, {md} 기준{f' · {k}쪽' if k > 1 else ''} · {TITLE}", body, ld))
    return out


st0 = lambda p: (4, None, "", [], False)  # 진열 목록 밖 딜(최저가 기록 쪽 '지금 올라온' 등) = 배지 X(글 아이콘은 그때 상태 — 지금 특가라고 안 함)


def search_index(it, tags={}):
    """search.json: 진열 상품 [(i, p, 상태)] 목록 순서(🔥 먼저) 그대로 — 카드 그리기 값 + 찾기 낱말(이름·몰·품목·[몰] + tags = {주소: 행사 tag} — 기획전 '핫딜픽이 고른 N개' 검색)."""
    out = []
    for i, p, sh in it:
        shown, ex, grey = price_bits(p, sh)
        c = CAT_META.get(cat_of(p))
        name = parse(title_of(p["text"]))[1]
        out.append({"i": i, "n": name, "s": chip_of(p), "p": shown, "e": (ex or [""])[0], "u": (grey or [""])[0], "b": badge(p, sh), "m": icon_key(p), "c": c[3] if c else "",
                    "g": img_of(p), "k": " ".join(x for x in (name, chip_of(p), parse(title_of(p["text"]))[0], c and c[1], ALIAS(name), tags.get(p.get("url"))) if x).lower()})
    return out


def related(i, p, pool, n=4):
    """딜 페이지 아래 '같이 보면 좋은 딜'(10/11 진우 '더 사고 싶게'): pool(최근 2일 제휴 링크 딜, 약한 딜 빼고) 중 같은 품목 먼저, 그다음 최신. 같은 이름 제외.
    쿠팡은 클릭 후 24시간 안 산 건 다 실적 -> 들어온 사람이 한 번 더 둘러보게."""
    me, k = title_of(p["text"]), set(keys(p).split()) - {"쿠팡", "토스", "네이버", "마감"}
    c = sorted(((j, q, ks) for j, q, ks in pool if j != i and title_of(q["text"]) != me), key=lambda x: x[1]["t"], reverse=True)
    return [(j, q) for j, q, _ in sorted(c, key=lambda x: -len(k & x[2]))[:n]]


def deal_card(i, p):
    """딜 쪽 본문(10/11 진우 '더 사고 싶게' · 10/24 개편): 썸네일 → 몰·시각 → 배지 → 이름 → 가격·얼마나 싼지·단위가격 → 큰 구매 버튼 → 왜 골랐나요(코멘트·확인할 점)."""
    title, rest, cut = split_title(p["text"])
    store, name, price = parse(title)
    body = to_html(rest, [{**e, "offset": e["offset"] - cut} for e in p.get("entities") or [] if e["offset"] >= cut])
    url, sv, u = f"{BASE}p/{i}.html", saving(p["text"]), " · ".join(x for x in (unit_of(p), steady_st(p["text"])) if x)  # 👍 = 한 달 구매·리뷰도
    if community(p.get("url")):  # 원글로 가는 버튼이면 이름을 정확히 + 원글이 지워져도 찾을 수 있게
        btn = (f'<a class="btn" href="{html.escape(p["url"])}" rel="nofollow noopener" target="_blank">📄 원글에서 구매 링크 보기</a>'
               f'<a class="btn2" href="{html.escape(find_url(title))}" rel="nofollow noopener" target="_blank">🔎 원글이 안 열리면 같은 상품 찾기</a>')
    elif p["text"].startswith("📋") and (p.get("url") or "").startswith("https://t.me/"):  # 행사 목록 글(url = 채널 글) = 구매 버튼 X
        btn = f'<a class="btn" href="{html.escape(p["url"])}" rel="noopener" target="_blank">📢 텔레그램에서 전체 목록 보기</a>'
    else:
        btn = f'<a class="btn" href="{html.escape(p["url"])}" rel="nofollow {"sponsored " if aff(p["url"]) else ""}noopener" target="_blank">{buy_label(title)}</a>' if p.get("url") else ""
    main, _, ship = price.partition("/")
    ship = {"무료": "무료배송", "무배": "무료배송"}.get(ship.strip(), ship.strip())
    hero = ((f'<div class="hero"><span class="pr">{html.escape(main.strip())}</span>' + (f'<span class="ship">{html.escape(ship.strip())}</span>' if ship.strip() else "")
             + (f'<span class="sv">{sv[0]}보다 {sv[1]}↓</span>' if sv else "") + "</div>") if price else "") + (f'<div class="u">{html.escape(u)}</div>' if u else "")
    bd = badge_html(p) + (f'<b class="b2">▼ {DROPS[i][0]}% 내림 · {DROPS[i][1]} 기록 대비</b>' if i in DROPS else "")
    return (f'<article class="card deal">{thumb(p)}<div class="s">{html.escape(store or "핫딜")} · {int(p["t"][5:7])}월 {int(p["t"][8:10])}일 {p["t"][11:16]}</div>'
            + (f'<div class="bd">{bd}</div>' if bd else "") + f'<h1 class="dn"><a href="{url}">{html.escape(name if price else title)}</a></h1>{hero}{btn}'
            + (f'<p class="note">가격·재고는 바뀔 수 있어요 · 결제 전 최종가 확인</p>' if btn else "") + f'<h3 class="why">왜 골랐나요</h3><p>{body}</p></article>')


NAVER_VERIFY = ("31caccebc9de97ffa6547f7d55966278daf9c469", "58af553d8879edfe3bc3a5189d9744ddc33bfcb9")  # 네이버 서치어드바이저 소유확인 — 값마다 meta 1줄(10/15 진우 'woori pd' 계정 = 두 번째, 첫 번째는 다른 계정일 수 있어 그대로)
GOOGLE_VERIFY = ""  # 구글 서치콘솔 'HTML 태그' content 값(10/14 진우 '검색 유입' — 진우 코드 오면 Cowork가 전달). 비면 출력 X


def seo(i, p):
    """딜 페이지 검색용 (제목, 설명, JSON-LD) — 10/14 진우 '검색 유입': '상품명 11,990원 (쿠팡) | 핫딜픽', '11,990원 · 개당 400원 · 쿠팡 · 10/14 게시 · 핫딜픽'
    (고지문·이모지 X), Product+Offer(가격 못 읽으면 X) — 판매처(몰)·쿠팡 사진(있으면)까지, 리뷰·별점은 안 넣음(지어내기 X)."""
    store, name, price = parse(title_of(p["text"]))
    if not re.search(r"\d원", price) and (m := re.search(r"\s*\((\d[\d,]{2,})\s*/[^()]*\)", name)):  # '(10,000/무료)'처럼 '원' 없는 가격
        price, name = m[1] + "원", (name[:m.start()] + name[m.end():]).strip()
    won = (re.search(r"\d[\d,]*원", price) or [""])[0]
    ld = won and json.dumps({"@context": "https://schema.org", "@type": "Product", "name": name, **({"image": img_of(p)} if img_of(p) else {}),
                             "offers": {"@type": "Offer", "price": won[:-1].replace(",", ""), "priceCurrency": "KRW", "url": f"{BASE}p/{i}.html", **({"seller": {"@type": "Organization", "name": store}} if store else {})}}, ensure_ascii=False).replace("</", "<\\/")
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
    head = d.get("head") or "👍 꾸준히 주문 들어오는 것 모음"  # 품목 모음 날 = '💄 화장품 스테디셀러 모음'(10/24)
    body = (f'<section class="day" aria-labelledby="sth"><h2 id="sth">{html.escape(head)}</h2><div class="t">최저가는 아니어도 주문이 꾸준한 것 · '
            f'{int(d["at"][5:7])}/{int(d["at"][8:10])} {d["at"][11:16]} 게시 시점 가격 · 가격·재고는 바뀔 수 있어요</div><ol>{rows}</ol></section>')
    open(f"{out}/steady.html", "w").write(page(f"{head.split(' ', 1)[-1]} | {TITLE}", body, "최저가는 아니어도 주문이 꾸준한 생필품·화장품 모음(매일 저녁 갱신)",
                                               f"{BASE}steady.html", cur="fire", note="\n".join(d.get("notes") or [])))
    return f"{BASE}steady.html", d["at"][:10]


HASH_JS = """<script>(function(){var m={wait:'c/wait/',life:'c/life/',toss:'c/toss/',coupang:'c/coupang/',naver:'c/naver/',cats:'c/',beauty:'c/beauty/',food:'c/food/',kitchen:'c/kitchen/',laundry:'c/laundry/',women:'c/women/',snack:'c/snack/',season:'c/season/',home:'c/home/',fashion:'c/fashion/',digital:'c/digital/',heat:'c/winter/',brand:'c/hot/',days:'all.html',saved:'saved/',hot:'#fire'};
function go(){var h=location.hash.slice(1),t=document.getElementById('today'),ig=/instagram|threads/i.test(document.referrer)||/[?&](fbclid|igsh|utm_source=(ig|threads)|ref=(ig|th))/.test(location.search)||/Instagram|Barcelona/.test(navigator.userAgent);try{h=decodeURIComponent(h)}catch(e){}
if(m[h]&&!document.getElementById(h)){if(m[h][0]==='#')location.replace(m[h]);else location.replace('/'+m[h]);return}if(t&&(ig||h==='today')){t.hidden=false;t.scrollIntoView()}}go();addEventListener('hashchange',go)})()</script>"""  # 10/24 개편 전 홈 #칸 주소(웹앱 바로가기·글 링크·프로필 #today) -> 새 쪽으로 · 인스타·Threads에서 오면 📸 카드 번호 칸을 맨 위에 보임(캡션 '맨 위 카드 딜에서 N번' 그대로)


ld_tag = lambda ld: '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>"  # 상품 이름에 '</script>'가 있어도 안 깨지게(seo()와 같게)


def write(out, rel, text):
    """docs/rel(…/ 로 끝나면 index.html) 쓰기 — 폴더 만들기."""
    f = f"{out}/{urllib.parse.unquote(rel)}" + ("index.html" if rel.endswith("/") or not rel else "")
    os.makedirs(os.path.dirname(f) or ".", exist_ok=True)
    open(f, "w").write(text)


MALL_BTN = (("coupang", "🚀 쿠팡", "로켓·와우 특가"), ("toss", "💙 토스", "하루특가·베스트"), ("naver", "💚 네이버", "쇼핑 특가"))  # 몰 버튼·쇼핑몰 칸(10/24 Cowork 포털형)
HOT_N, HOT_DAYS, DROP_MIN, DROP_BIG, DROP_N = 10, 3, 3, 30, 6  # 🔥 실시간 핫딜 탭마다 줄 수 · 가격 확인 n일 안만 · 📉 가격 내림 n%↑(30%↑ = 쿠팡 API로 옵션 맞을 때만) · 홈 줄 수
STAT_CHIPS = (("hot", "🔥 특가"), ("steady", "👍 꾸준템"), ("wait", "⏳ 대기"), ("drop", "📉 가격 내림"), ("today", "⏰ 오늘 마감"), ("top", "🏆 TOP 10"))  # 상태로 찾기(10/24 Cowork '변경 찾기')
DROPS = {}  # 글 번호 -> (▼%, 'M/D' 기록, 'M/D' 확인) — build가 채움(카드·딜 쪽 배지)


def won(s):
    """'10,430원 와우가' -> 10430(첫 'N원'), 없으면 0."""
    m = re.search(r"(\d[\d,]*)\s*원", s or "")
    return int(m[1].replace(",", "")) if m else 0


def md_of(d):
    """'YYYY-MM-DD…' -> 'M/D'."""
    return f"{int(d[5:7])}/{int(d[8:10])}"


def fresh_day(p, today):
    """가격 근거 날(YYYY-MM-DD): 진우 상품 = 확인 시각(chkt·chk 'M/D H시')·다시 특가 날, 그 밖 = 올린 날 — 가장 새것."""
    m = re.match(r"(\d{1,2})/(\d{1,2})", p.get("chk") or "")
    d = m and f"{today[:4]}-{int(m[1]):02d}-{int(m[2]):02d}"
    d = d and (d if d <= today else f"{int(today[:4]) - 1}{d[4:]}")  # 해 넘김(12/31 확인을 1/1에 봄)
    return max(x for x in ((p.get("chkt") or "")[:10], d or "", p.get("rehot") or "", p["t"][:10]) if x)


def price_day(p, today):
    """보이는 가격의 날(10/24 Cowork B — '🔁 10/13 가격' 토스가 🔥 2번째): 토스 = 올린 날(사이트엔 올린 가격만), 그 밖 = fresh_day."""
    return p["t"][:10] if shop_of(p) == "toss" else fresh_day(p, today)


def trust8(xs, today, n=8, key=None):
    """목록 위 n개에서 보이는 가격이 HOT_DAYS일 지난 🔥 빼기(홈 TOP 규칙을 목록에도 — 10/24 Cowork B '🔁 10/13 가격'): 위 n자리 = 그 밖 상품 순서대로, 옛 가격 🔥는 그 뒤(순서 그대로)."""
    since = time.strftime("%Y-%m-%d", time.gmtime(calendar.timegm(time.strptime(today, "%Y-%m-%d")) - (HOT_DAYS - 1) * 86400))
    ok = [x for x in xs if not (x[2][0] == 0 and price_day(x[1], today) < since)][:n]
    rest = [x for x in xs if x not in ok]
    return sorted(ok, key=key) + sorted(rest, key=key) if key else ok + rest  # key = 위 n자리·나머지 안에서만 다시 줄 세움(네이버 가전 먼저 — 옛 가격이 위로 X)


def brand(p):
    """같은 브랜드 판단 = 상품명 첫 낱말."""
    return (parse(title_of(p["text"]))[1].split() or [""])[0]


def mix(xs, n):
    """몰 섞기(쿠팡·토스·네이버·그 밖 돌아가며, 몰 안 순서 그대로) + 같은 브랜드 1개 -> 앞 n개(10/24 Cowork ② 신뢰)."""
    by = {}
    for x in xs:
        by.setdefault(shop_of(x[1]), []).append(x)
    its, out, seen = [iter(by[k]) for k in ("coupang", "toss", "naver", "") if k in by], [], set()
    while its and len(out) < n:
        for g in its[:]:
            x = next((x for x in g if brand(x[1]) not in seen), None)  # 같은 브랜드면 그 몰 다음 것(차례 안 잃게)
            if x is None:
                its.remove(g)
            elif len(out) < n:
                out.append(x)
                seen.add(brand(x[1]))
    return out


def cap2(xs, *shown):
    """같은 상품 홈에 최대 2번(10/24 진우 v3 ② — 블루나 물티슈 4번): 앞 칸들(shown — 우선순위 오늘 마감 > 🔥 > 📉 > 픽 > 꾸준템)에 이미 2번 나온 상품은 뺌 · 같은 상품 = 같은 주소(없으면 글 번호) · TOP 10·찜/본 줄은 셈 X."""
    n = collections.Counter(k for s in shown for k in {x[1].get("url") or x[0] for x in s})
    return [x for x in xs if n[x[1].get("url") or x[0]] < 2]


def uniq(xs, n):
    """같은 브랜드 1개 -> 앞 n개(순서 그대로)."""
    out, seen = [], set()
    for x in xs:
        if len(out) < n and brand(x[1]) not in seen:
            out.append(x)
            seen.add(brand(x[1]))
    return out


def short_note(p, sh, today):
    """목록형 줄 2줄째 회색: 단위가 > 확인 시각('19시 확인'·'10/23 확인') > 'M/D 가격'(토스 = 올린 날 가격)."""
    u = "" if sh[1] else unit_line(p)  # 지금가(확인가)가 있으면 글의 단위가 = 옛 가격 기준 -> X(카드 price_bits와 같음)
    if shop_of(p) == "toss":  # 토스 = 올린 날 표기 필수(단위가보다 먼저 — 말줄임에 안 잘리게)
        return f"{md_of(p['t'])} 가격" + (f" · {u}" if u else "")
    if u:
        return u
    if sh[1] and p.get("chk"):
        d, _, h = p["chk"].partition(" ")
        return f"{h} 확인" if h and d == md_of(today) else f"{p['chk']} 확인"
    return f"{md_of(p['t'])} 가격"


def row(i, p, sh, today, gc="", extra=""):
    """목록형 한 줄(68px — 10/24 Cowork 포털형): 썸네일 52 · 1줄 = 몰 글자(몰 색) + 🔁/⏰/▼ + 이름 말줄임 · 2줄 = 가격 굵게 + 빨강 라벨 + 회색(단위가·확인 시각·M/D 가격). 누르면 딜 쪽."""
    name = parse(title_of(p["text"]))[1]
    shown, ex, _ = price_bits(p, sh)
    k = shop_of(p)
    flag = "" if extra else "🔁 " if sh[4] else "⏰ " if day_end(p, today) else {1: "👍 ", 2: "⏳ "}.get(sh[0], "") if p.get("own") else ""  # 🆕 탭 대기 상품 = 카드 badge()처럼 · 📉 줄(extra) = 상태 표시 X(▼N%만 — 10/24 Cowork C)
    d = DROPS.get(i)
    return (f'<li class="r"><a href="{BASE}p/{i}.html"' + (f' data-gc="{gc}"' if gc else "") + f'>{thumb(p)}<span class="rt"><span class="l1"><b class="mk {k}">{html.escape(chip_of(p).split(" ")[0])}</b>{flag}{html.escape(name)}</span>'
            + f'<span class="l2">' + (extra or ((f"<b>{html.escape(shown)}</b>" if shown else "") + (f"<i>{html.escape(ex[0])}</i>" if ex else "") + (f'<i>▼{d[0]}%</i>' if d else "")
                                                 + f"<small>{html.escape(short_note(p, sh, today))}</small>")) + "</span></span></a></li>")


Q_CATS = ("life", "food", "beauty", "digital", "kitchen", "laundry", "snack", "women", "heat", "season", "home", "fashion", "car")  # 둥근 바로가기 2줄째 순서(진우 v3 — 가전 4번째)


def quick_nav(evs, dl_n, dl_end, top_live, evh=""):
    """둥근 바로가기 2줄(포털형 2차 ③ — N+스토어 참고: 46px 동그라미 + 11.5px 이름, 6개 + 7번째 반쯤 보이게 옆으로 밀기):
    1줄 ⏰ 오늘 마감('N개 남음' — 0개면 X, 자정 지나면 숨김) · 🏆 많이 본(GoatCounter 진짜 조회일 때만 — 아니면 'TOP 10') · 📉 가격 내림 · 🔁 다시 특가 · 🚀 쿠팡 · 💙 토스 · 💚 네이버 · 🎉 기획전(진행 중만)
    2줄 품목 12칸(Q_CATS) + ▦ 전체보기 · GoatCounter q/·mall/·cat/. C 혼합형(10/25) = 1줄만 + 끝에 ▦ 품목 전체(/c/)."""
    a = lambda href, e, n, gc, cls="", extra="", c="": f'<a class="q{cls}" href="{href}" data-gc="{gc}"><i aria-hidden="true"' + (f' style="--c:{c}"' if c else "") + f">{e}</i>{n}{extra}</a>"
    r1 = [a(c_url("today"), "⏰", "오늘 마감", "q/today", extra=f'<b class="qb" data-qend="{dl_end}">{dl_n}개 남음</b>' if dl_n else ""), a(c_url("top"), "🏆", "많이 본" if top_live else "TOP 10", "q/top"),
          a(c_url("drop"), "📉", "가격 내림", "q/drop"), a(c_url("rehot"), "🔁", "다시 특가", "q/rehot")] \
        + [f'<a class="q {k}" href="{c_url(k)}" data-gc="mall/{k}">{mall_logo(k)}{n.split()[1]}</a>' for k, n, _ in MALL_BTN] \
        + ([f'<a class="q evt" href="{evh or BASE + "e/" + evs[0]["slug"] + ".html"}" data-gc="mall/event"><i class="lw" aria-hidden="true">🎉</i>기획전</a>'] if evs or evh else []) + [a(f"{BASE}c/", "▦", "품목 전체", "cat/all", " qc")]  # W: 쇼핑몰·기획전 = 흰 동그라미 · ▦ = C 혼합형만(2줄 품목 대신)
    r2 = [a(c_url(CAT_META[k][0]), CAT_META[k][2], CAT_META[k][1].split("·")[0].split()[0], f"cat/{CAT_META[k][0]}", c=CAT_META[k][3]) for k in Q_CATS] + [a(f"{BASE}c/", "▦", "전체보기", "cat/all")]
    return f'<nav class="qk" aria-label="바로가기"><div class="qr">{"".join(r1)}</div><div class="qr">{"".join(r2)}</div></nav>'


def mall_nav(evs, evh=""):
    """홈 몰 버튼 1줄(A 목록형 = 1차 — 10/24 Cowork 포털형): 🚀 쿠팡 · 💙 토스 · 💚 네이버 (+ 🎉 기획전 = 진행 중일 때만) -> 몰 쪽 · GoatCounter mall/몰."""
    return ('<nav class="mb" aria-label="쇼핑몰">' + "".join(f'<a class="m {k}" href="{c_url(k)}" data-gc="mall/{k}">{mall_label(k, n)}</a>' for k, n, _ in MALL_BTN)
            + (f'<a class="m evt" href="{evh or BASE + "e/" + evs[0]["slug"] + ".html"}" data-gc="mall/event"><i class="lw" aria-hidden="true">🎉</i>기획전</a>' if evs or evh else "") + "</nav>")  # evh = /events/(기획전 모음 — 10/25)


def hot_section(it, evi, today):
    """🔥 실시간 핫딜(10/24 Cowork 포털형 ⑤ + ② 신뢰): 🔥 상품 중 가격 근거(fresh_day)가 HOT_DAYS일 안 · 기획전 상품 X(배너로만) -> 탭 전체(몰 섞기)·몰별·🆕 새로 올라온(올린 순) 10줄씩, 같은 브랜드 1개.
    -> (HTML, 전체 탭 글 번호들)."""
    since = time.strftime("%Y-%m-%d", time.gmtime(calendar.timegm(time.strptime(today, "%Y-%m-%d")) - (HOT_DAYS - 1) * 86400))
    xs = [x for x in it if x[2][0] == 0 and x[0] not in evi and fresh_day(x[1], today) >= since]
    ys = [x for x in xs if price_day(x[1], today) >= since]  # 줄 = 보이는 가격도 3일 안(토스 = 올린 날 — 10/24 Cowork B)
    tabs = [("all", "전체", mix(ys, HOT_N))] + [(k, n, uniq(sorted((x for x in ys if shop_of(x[1]) == k), key=lambda x: k == "naver" and cat_of(x[1]) != "digital"), HOT_N)) for k, n, _ in MALL_BTN] \
        + [("new", "🆕 새로 올라온", uniq(sorted((x for x in it if x[2][0] != 3 and x[0] not in evi), key=lambda x: x[1]["t"], reverse=True), HOT_N))]
    tabs = [t for t in tabs if t[2]]
    if not tabs:
        return "", []
    toss = any(shop_of(p) == "toss" for _, _, ys in tabs for _, p, _ in ys)
    return (f'<section class="sec" id="fire" aria-labelledby="fireh"><h2 id="fireh"><span>🔥 실시간 핫딜<small>{len(xs)}개</small></span><a class="more" href="{c_url("hot")}">전체 →</a></h2>'
            + '<div class="tabs" role="tablist" aria-label="몰">' + "".join(f'<button type="button" role="tab" aria-selected="{"true" if not j else "false"}" aria-controls="fp-{k}" data-t="{k}">{mall_label(k, n) if k in MALL_KO else n}</button>' for j, (k, n, _) in enumerate(tabs)) + "</div>"
            + "".join(f'<ol class="rows" role="tabpanel" id="fp-{k}" data-p="{k}"' + (" hidden" if j else "") + ">" + "".join(row(i, p, sh, today) for i, p, sh in ys) + "</ol>" for j, (k, _, ys) in enumerate(tabs))
            + (f'<p class="t tl">{TOSS_LINE}</p>' if toss else "") + f'<a class="all" href="{c_url("hot")}">실시간 핫딜 더 보기 →</a></section>'), [x[0] for k, _, ys in tabs if k == "all" for x in ys]  # 👍 칸에서 뺄 = 전체 탭 줄만


def top_list(posts, it, evi, gc_file="gc_top.json", top_file="top.json"):
    """🏆 TOP 10(10/24 Cowork): GoatCounter 최근 24시간 많이 본 순(hotdeal.gc_top -> gc_top.json, 3시간 안) — 10개 안 되면 반응 좋은 순(top.json Threads 조회 · 커뮤니티 pop)으로 채우고 머리를 '👍 반응 좋은 딜'로('많이 본' = 진짜 조회 데이터일 때만).
    품절·기획전 X, 같은 상품(주소·이름) 1번. -> (머리, 작은 글, [(i, p, sh)])."""
    pool = [x for x in it if x[2][0] != 3 and x[0] not in evi and not x[1]["text"].startswith("📋")]
    n = collections.Counter(u.split("?")[0] for u in {x[1].get("url") for x in it if x[1].get("url")})
    key = lambda u: u.split("?")[0] if n[u.split("?")[0]] == 1 else u  # 검색·클릭 주소(search/all·click.php)는 ?뒤가 상품 -> 그대로
    by = {key(x[1]["url"]): x for x in pool if x[1].get("url")}
    out, seen = [], set()
    def add(x):
        k = (x[1].get("url"), parse(title_of(x[1]["text"]))[1])
        if len(out) < 10 and not seen & set(k):
            out.append(x)
            seen.update(k)
    try:
        g = json.load(open(gc_file))
        ok = isinstance(g, dict) and g.get("at", "") >= time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600 - 3 * 3600))
    except (OSError, ValueError):
        g, ok = {}, False
    for u in (g.get("urls") or [])[:60] if ok else []:
        if isinstance(u, str) and key(u) in by:
            add(by[key(u)])
    if len(out) >= 10:
        return "🏆 많이 본 딜 TOP 10", f"최근 24시간 · {int(g['at'][11:13])}시 기준", out
    try:
        tj = json.load(open(top_file)).get("items") or []
    except (OSError, ValueError, AttributeError):
        tj = []
    a = [by[key(t.get("url") or "")] for t in tj if isinstance(t, dict) and key(t.get("url") or "") in by]
    b = sorted((x for x in pool if x[1].get("pop")), key=lambda x: -x[1]["pop"])
    for x in (x for t in itertools.zip_longest(a, b) for x in t if x):
        add(x)
    return "👍 반응 좋은 딜 TOP 10", "Threads 조회·커뮤니티 반응", out


def top_section(head, small, xs):
    """🏆/👍 TOP 10 칸: 2열 번호 목록(왼 1~5 · 오른 6~10, 1~3 빨강) — 몰 글자 색 + 이름 1줄 말줄임 · GoatCounter top/N."""
    return "" if not xs else (f'<section class="sec" id="t10" aria-labelledby="t10h"><h2 id="t10h"><span>{head}</span><small>{small}</small></h2><ol class="t10">'
                              + "".join(f'<li><a href="{BASE}p/{i}.html" data-gc="top/{n}"><b class="n{" r" if n <= 3 else ""}">{n}</b><b class="mk {shop_of(p)}">{html.escape(chip_of(p).split(" ")[0])}</b>'
                                        f'<span>{html.escape(parse(title_of(p["text"]))[1])}</span></a></li>' for n, (i, p, sh) in enumerate(xs, 1)) + f'</ol><a class="more2" href="{c_url("top")}">TOP 10 카드로 보기 →</a></section>')


def deadline_list(it, evi, today):
    """⏰ 오늘 마감(10/24 Cowork): 진열 🔥 중 오늘 밤 12시 끝(day_end — 토스 하루특가·선착순·'밤 12시까지') · 기획전 X(마지막 날은 행사 카드 1장) -> 할인 큰 순."""
    dr = lambda p: max([int(x) for x in re.findall(r"(\d{1,2})\s*%\s*(?:할인|↓)", p["text"])] or [0])
    return sorted((x for x in it if x[2][0] == 0 and x[0] not in evi and day_end(x[1], today)), key=lambda x: (-dr(x[1]), not img_of(x[1])))


def dl_card(i, p, sh, today):
    """오늘 마감 가로 카드(150px): 카드 + 위 '⏰ 3시간 12분 남음 · 하루특가'(END_JS가 자정까지 셈, 지나면 카드·칸 숨김)."""
    k = "하루특가" if re.search(r"하루\s*특가", p["text"]) else "선착순" if "선착순" in p["text"] else "오늘 마감"
    c = card(i, p, sh).replace(f'<div class="ex" data-end="{end_at(p)}">⏰ 오늘 밤 12시 마감</div>', "")  # 카드 안 '마감까지' 줄 = 위 한 줄과 겹침
    c = c.replace(f'<a href="{BASE}p/{i}.html">', f'<a href="{BASE}p/{i}.html" data-gc="deadline/{i}">', 1)  # 상품 링크만 셈(♡ 찜 X)
    return f'<div class="hc"><b class="cd" data-end="{end_at(p)}" data-k="{k}">⏰ 오늘 밤 12시 마감 · {k}</b>{c}</div>'


def deadline_section(xs, evs, today):
    """⏰ 오늘 마감 칸(머리 옆 '밤 12시까지', 없으면 칸 X): 가로 카드 + 기획전 마지막 날 = 행사 카드 1장."""
    end = calendar.timegm(time.strptime(today, "%Y-%m-%d")) + 86400 - 9 * 3600
    evc = [f'<a class="hc evc" href="{BASE}e/{g["slug"]}.html" data-gc="deadline/event"><b class="cd" data-end="{end}" data-k="기획전">⏰ 오늘 밤 12시 마감 · 기획전</b><span class="em" aria-hidden="true">🎉</span>'
           f'<b>{html.escape(ev_name(g))}</b><small>핫딜픽이 고른 {ev_n(g)}개 · 오늘 마감</small></a>' for g in evs if g["until"] == today]
    return "" if not (xs or evc) else (f'<section class="sec" id="dl" aria-labelledby="dlh"><h2 id="dlh"><span>⏰ 오늘 마감<small>{len(xs) + len(evc)}개</small></span><small>밤 12시까지</small></h2>'
                                       + f'<div class="hs">{"".join(evc)}{"".join(dl_card(i, p, sh, today) for i, p, sh in xs[:12])}</div>'
                                       + (f'<a class="more2" href="{c_url("today")}">오늘 마감 전체 →</a>' if len(xs) > 12 else "") + (f'<p class="t">{TOSS_LINE}</p>' if any(shop_of(p) == "toss" for _, p, _ in xs[:12]) else "") + "</section>")


def drops(posts, it, now_ts):
    """📉 가격 내려간 상품(10/24 Cowork): 쿠팡·네이버 진우 상품(진열 중, 일시 품절 X) 중 지금 확인가(now — 확인 chkt 24시간 안)가 처음 올린 가격(같은 링크 = 같은 구성, 첫 진우 글) 대비 DROP_MIN%↑ 내림.
    DROP_BIG%↑는 쿠팡 검색 API 가격(own_end cpp·cpt — 옵션 itemId 또는 이름 수량·용량 토큰이 맞은 것, 48시간 안)이 지금가 ±5% 또는 기록가×0.7 밑일 때만(아니면 hotdeal.drop_check가 관리자에게 — 옵션 바뀜 의심).
    토스 X(사람마다 가격 다름·API 가격 사이트 X). -> [(i, p, sh, 기록가, 지금가, ▼%, 'M/D' 기록, 'M/D' 확인)] 내림 큰 순."""
    first, out = {}, []
    for p in posts:
        if p.get("own") and p.get("url") and not p["text"].startswith("📋"):
            first.setdefault(p["url"], p)
    day = lambda h: time.strftime("%Y-%m-%d %H:%M", time.gmtime(now_ts + 9 * 3600 - h * 3600))
    for i, p, sh in it:
        if not p.get("own") or shop_of(p) not in ("coupang", "naver") or sh[0] == 3 or p["url"] not in first:
            continue
        f = first[p["url"]]
        base, nw = won(parse(title_of(f["text"]))[2]), won(p.get("now"))
        if not (base and nw and re.fullmatch(r"\d{4}-\d\d-\d\d ([01]\d|2[0-3]):[0-5]\d", p.get("chkt") or "") and p["chkt"] >= day(24)):  # 손으로 쓴 chk 모양 틀림 -> 빌드 멈춤 X
            continue
        pct = round((base - nw) * 100 / base)
        cpp = p.get("cpp") or 0
        if pct < DROP_MIN or pct >= DROP_BIG and not (cpp and (p.get("cpt") or "") >= day(48) and (abs(cpp - nw) <= nw * 0.05 or cpp <= base * 0.7)):
            continue
        rec = re.search(r"\((\d{1,2}/\d{1,2}) \d{1,2}시 (?:확인|가격)\)", f["text"])  # 첫 글 '(M/D H시 가격)' 줄 = 기록 날, 없으면 올린 날
        out.append((i, p, sh, base, nw, pct, rec[1] if rec else md_of(f["t"]), md_of(p["chkt"])))
    return sorted(out, key=lambda d: (-d[5], not img_of(d[1])))


def drop_section(ds, today, n=None):
    """📉 가격 내려간 상품 칸(머리 옆 '같은 구성 · 우리 기록 대비', 없으면 X): 줄 DROP_N개 — 취소선 기록가 → 지금가 + ▼N% + 'M/D 기록 대비 · M/D 확인'('N원 쌈' X) · GoatCounter drop/글."""
    lab = lambda p: (re.match(r"[\d,]+원\s*(\S.*)", p.get("now") or "") or ["", ""])[1]
    return "" if not ds else (f'<section class="sec" id="drop" aria-labelledby="droph"><h2 id="droph"><span>📉 가격 내려간 상품<small>{n or len(ds)}개</small></span><small>같은 구성 · 우리 기록 대비</small></h2><ol class="rows">'
                              + "".join(row(i, p, sh, today, f"drop/{i}", f"<s>{b:,}원</s> → <b>{n:,}원</b>" + (f"<i>{html.escape(lab(p))}</i>" if lab(p) else "") + f"<i>▼{d}%</i><small>{r} 기록 대비 · {c} 확인</small>")
                                        for i, p, sh, b, n, d, r, c in ds[:DROP_N]) + f'</ol><a class="more2" href="{c_url("drop")}">가격 내려간 상품 전체 →</a></section>')


def hs_section(sid, head, small, xs, more="", cls="hs"):
    """가로 카드 줄(오늘의 픽 118px·꾸준템): 카드(♡ 찜 그대로) 옆으로 밀기 + '전체 →'."""
    return "" if not xs else (f'<section class="sec" id="{sid}" aria-labelledby="{sid}h"><h2 id="{sid}h"><span>{head}' + (f"<small>{small}</small>" if small else "") + "</span>"
                              + (f'<a class="more" href="{more}">전체 →</a>' if more else "") + f'</h2><div class="{cls}">{"".join(card(i, p, sh) for i, p, sh in xs)}</div>'
                              + (f'<p class="t">{TOSS_LINE}</p>' if any(shop_of(p) == "toss" for _, p, _ in xs) else "") + "</section>")


def stat_chips(cur):
    """상태로 찾기 칩 6개(🔥 특가 · 👍 꾸준템 · ⏳ 대기 · 📉 가격 내림 · ⏰ 오늘 마감 · 🏆 TOP 10 — 10/24 Cowork '변경 찾기')."""
    return '<nav class="chips" aria-label="상태">' + "".join(f'<a href="{c_url(s)}"' + (' aria-current="page"' if s == cur else "") + f">{t}</a>" for s, t in STAT_CHIPS) + "</nav>"


def mall_page(slug, head, desc, xs, recs):
    """몰 쪽(/c/coupang/ 등 — 10/24 Cowork '쇼핑몰 위주로 찾을 수 있게'): 한 쪽에 그 몰 전부 + 품목 칩(있는 품목만)·상태 탭(🔥 특가·👍 꾸준템·⏳ 대기 — 없는 건 X)으로 좁히기 + 20개씩 '더 보기'(MALL_JS — 스크립트 없으면 전부 보임).
    -> [(주소, 1, 제목, 설명, 본문, JSON-LD)]."""
    today = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600))
    st = lambda x: " ".join(t for t, ok in (("h", x[2][0] == 0), ("s", steady_of(x)), ("w", x[1].get("own") and x[2][0] in (1, 2))) if ok)
    ma = lambda x: ' data-c="%s" data-s="%s"' % ((CAT_META.get(cat_of(x[1])) or ("etc",))[0], st(x))  # 카드 = 품목·상태(좁히기)
    cs = collections.Counter(cat_of(p) or "etc" for _, p, _ in xs)
    ss = collections.Counter(t for x in xs for t in st(x).split())
    name = head.split(" ", 1)[1]
    body = (f'<h1 class="h">{mall_label(slug, html.escape(head))}</h1><div class="t">{html.escape(desc)} · {len(xs)}개 · {md_of(today)} 업데이트</div><p class="t">{SHOP_NOTES[slug]}</p>'
            + (f'<p class="t">{TOSS_LINE}</p>' if slug == "toss" else "")
            + '<div class="tabs" role="tablist" aria-label="상태"><button type="button" role="tab" aria-selected="true" data-s="">전체</button>'
            + "".join(f'<button type="button" role="tab" aria-selected="false" data-s="{t}">{n} {ss[t]}</button>' for t, n in (("h", "🔥 특가"), ("s", "👍 꾸준템"), ("w", "⏳ 대기")) if ss[t]) + "</div>"
            + '<nav class="chips mf" aria-label="품목"><button type="button" aria-pressed="true" data-c="">전체</button>'
            + "".join(f'<button type="button" aria-pressed="false" data-c="{CAT_META[k][0]}">{CAT_META[k][2]} {CAT_META[k][1].split("·")[0]} {cs[k]}</button>' for k in CAT_META if cs[k]) + "</nav>"
            + (f'<div class="cards" id="mg">{"".join(card(i, p, sh, attrs=ma((i, p, sh))) for i, p, sh in xs)}</div>'
               f'<p class="t" id="m0" hidden>이 조건에 맞는 상품이 없어요.</p><button type="button" class="btn2 mm" id="mm" hidden>더 보기</button>' if xs else '<p class="t" style="margin:18px 2px">지금은 이 목록에 상품이 없어요. 다른 칸을 둘러보세요.</p>')
            + (f'<a class="btn2" href="{GOLDBOX}" rel="nofollow sponsored noopener" target="_blank">⏰ 쿠팡 골드박스</a>' if slug == "coupang" else "") + MALL_JS)
    li = [{"@type": "ListItem", "position": m, "url": f"{BASE}p/{i}.html", "name": parse(title_of(p["text"]))[1], "image": img_of(p)} for m, (i, p) in enumerate(((i, p) for i, p, _ in xs[:20] if img_of(p)), 1)]
    return [(c_url(slug), 1, f"{name} ({md_of(today)}) | {TITLE}", f"{desc} — {name} {len(xs)}개, {md_of(today)} 기준 · {TITLE}", body, len(li) >= 3 and {"@context": "https://schema.org", "@type": "ItemList", "name": f"{name} ({md_of(today)})", "itemListElement": li})]


MALL_JS = """<script>(function(){var g=document.getElementById('mg');if(!g)return;var C=[].slice.call(g.children),s=(location.search.match(/[?&]s=([hsw])/)||['',''])[1],c='',n=20,mm=document.getElementById('mm'),z=document.getElementById('m0');
function run(){var k=0;C.forEach(function(e){var ok=(!s||(' '+e.dataset.s+' ').indexOf(' '+s+' ')>=0)&&(!c||e.dataset.c===c);e.hidden=!ok||k>=n;if(ok)k++});mm.hidden=k<=n;z.hidden=k>0}
document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('[data-s],[data-c],#mm');if(!b||b.tagName!=='BUTTON')return;if(b.id==='mm'){n+=20;return run()}
if(b.hasAttribute('data-s')){s=b.dataset.s;[].forEach.call(document.querySelectorAll('[data-s][role=tab]'),function(x){x.setAttribute('aria-selected',x===b?'true':'false')})}
else{c=b.dataset.c;[].forEach.call(document.querySelectorAll('.mf [data-c]'),function(x){x.setAttribute('aria-pressed',x===b?'true':'false')})}n=20;run()});
[].forEach.call(document.querySelectorAll('[data-s][role=tab]'),function(x){x.setAttribute('aria-selected',x.dataset.s===s?'true':'false')});run()})()</script>"""  # 몰 쪽 좁히기·더 보기(10/24 Cowork) — 스크립트 없으면 전부 보임
TAB_JS = """<script>document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('.tabs [data-t]');if(!b)return;var s=b.closest('section');
[].forEach.call(s.querySelectorAll('.tabs [data-t]'),function(x){x.setAttribute('aria-selected',x===b?'true':'false')});[].forEach.call(s.querySelectorAll('[data-p]'),function(x){x.hidden=x.dataset.p!==b.dataset.t;delete x.dataset.sh})})</script>"""  # 🔥 실시간 핫딜 탭(전체·몰별·새로 올라온)


def changes_json(posts, it, ds, dl, now_ts, prev=None):
    """docs/changes.json(10/24 Cowork '변경 찾기' — 찜 배지·알림 탭·🔔 빨간 점이 읽음): 최근 3일 바뀐 상품
    {"at", "n": {종류: 수}, "items": {글 번호: {m 몰, n 이름, r 기록가, c 지금가(쿠팡·네이버만 — 토스 API 가격 X), t 확인('M/D H시'), k [종류], d 바뀐 때(epoch 초), p ▼%}}, "a": {같은 상품 옛 글 번호: 지금 글 번호}}.
    종류 = drop(같은 구성 3%↑ 내림 — 📉 칸과 같음) · deadline(오늘 밤 12시) · rehot(🔁 다시 특가) · ended(특가 끝 → ⏳ — own_end std·stp) · gone(판매 종료) + n.new(오늘 올라온 수 — 상품 칸 X).
    d = 이 변경이 처음 보인 빌드 시각(prev = 지난 changes.json — std·rehot은 날짜만, chkt는 다시 확인마다 바뀜 -> 🔔 점이 늦거나 매일 다시 X)."""
    kst = lambda d: calendar.timegm(time.strptime(d[:16] if len(d) > 10 else d[:10] + " 00:00", "%Y-%m-%d %H:%M")) - 9 * 3600
    today, since = time.strftime("%Y-%m-%d", time.gmtime(now_ts + 9 * 3600)), time.strftime("%Y-%m-%d", time.gmtime(now_ts + 9 * 3600 - 2 * 86400))
    items, idx, new = {}, {}, 0
    for j, p in enumerate(posts):
        if p.get("url") and not p["text"].startswith("📋"):
            idx.setdefault(p["url"], []).append(j)
    def put(i, q, k, d, **x):
        e = items.setdefault(str(i), {"m": shop_of(q) or "", "n": parse(title_of(q["text"]))[1][:60], "r": parse(title_of(q["text"]))[2].split("/")[0].strip()[:30],
                                      "c": (q.get("now") or "") if shop_of(q) != "toss" else "", "t": q.get("chk") or "", "k": [], "d": 0})
        e["k"].append(k)
        e["d"] = max(e["d"], int(d))
        e.update(x)
    for i, p, sh, b, n, pct, r, c in ds:
        put(i, p, "drop", kst(p["chkt"]), p=pct, r=f"{b:,}원")
    for i, p, sh in dl:
        put(i, p, "deadline", kst(p["t"]))
    last = {p.get("url"): j for j, p in enumerate(posts) if p.get("own") and not p["text"].startswith("📋")}
    for i, p, sh in it:
        if sh[4]:
            put(i, p, "rehot", kst(p.get("rehot") or today))
        if p.get("own") and p.get("st") == "wait" and p.get("stp") == "hot" and (p.get("std") or "") >= since:
            put(i, p, "ended", kst(p["std"]))
        new += p["t"][:10] == today  # new = 수만(찜한 상품은 늘 옛것 — 파일 작게) · 오늘 날짜로(24시간 창이면 빌드마다 파일이 바뀜)
    for u, j in last.items():
        p = posts[j]
        if p.get("st") == "gone" and (p.get("std") or "") >= since:
            put(j, p, "gone", kst(p["std"]))
    alias = {str(j): k for k in items for j in idx.get(posts[int(k)].get("url"), []) if str(j) != k}
    po = (prev or {}).get("items") or {}
    for i, e in items.items():
        o = po.get(i)
        if isinstance(o, dict) and set(e["k"]) <= set(o.get("k") or []) and e.get("p") == o.get("p") and isinstance(o.get("d"), int):
            e["d"] = o["d"]  # 같은 변경 = 처음 본 때 그대로
        elif prev is not None:
            e["d"] = int(now_ts)
    return {"at": today, "n": {**collections.Counter(k for e in items.values() for k in e["k"]), "new": new}, "items": items, "a": alias}  # at = 날짜만(분까지 쓰면 빌드마다 파일이 바뀌어 15분 실행마다 docs 커밋)


LINK_STYLE = "ab"  # /link/ 프로필 링크 쪽(10/25 진우): 'ab' = 시안 A·B 반반(방문자마다 50:50 · 그 브라우저는 계속 같은 쪽 · 주소 v=a/v=b = 고정 보기) · 'a'|'b' = 그 시안만 — 다른 시안 미리보기 = /link/b/(LINK_STYLE 'b'면 /link/a/, noindex)
LINK_AB = ("2026-10-26", "2026-11-08")  # A·B 비교 기간(홈 레이아웃 비교와 같은 날 마감) — 하루 집계 = hotdeal.link_ab -> link_ab.json · 자동으로 한쪽으로 몰지 않음(결과 판단 = Cowork·진우)
KAKAO_OPENCHAT_URL = ""  # 카톡 특가방(오픈채팅) 주소 — 진우가 방 만들면 Cowork가 전달 · 비거나 https://open.kakao.com/ 아니면 /link 카톡 버튼·줄 숨김
LINK_N, LINK_PER_CAT, LINK_MALLS = 12, 2, ("coupang", "toss", "naver")  # /link 지금 특가 칸 수(칩마다) · MM(10/26 — 12칸 중 10칸 히터 ❄️) 앞 12칸 = 품목 칸마다 2개까지·몰 돌림
LINK_TABS = (("all", "전체"), ("life", "생필품"), ("beauty", "뷰티"), ("food", "식품"), ("women", "여성용품"))  # 칩 = 화면 안에서만 거름(품목 = cat_of)
LINK_CH = (("blog", "블로그", BLOG, "naver", "background:#03C75A", "네이버 블로그", "가격 비교 글"), ("threads", "Threads", THREADS, "threads", "background:#000", "Threads", "실시간 딜"),
           ("instagram", "인스타", INSTA, "instagram", "background:radial-gradient(circle at 30% 107%,#fdf497 0%,#fdf497 5%,#fd5949 45%,#d6249f 60%,#285AEB 90%)", "인스타그램", "카드 딜 · 번호로 찾기"),
           ("telegram", "텔레그램", CHANNEL, "telegram", "background:#fff;color:#26A5E4", "텔레그램", "새 특가 바로 받기"))  # 주소 = 사이트 아래 채널 줄 · GoatCounter link/첫 칸 · 텔레그램 = 아이콘 자체가 파란 원(흰 비행기)이라 원 크기 그대로
SI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "si")  # Simple Icons(CC0) SVG 원본 — si/README.md


def si(k, cls="si"):
    """브랜드 아이콘(si/k.svg, Simple Icons) -> 인라인 SVG: 모양(path)은 파일 그대로, 색은 CSS(currentColor) — 외부 CDN X."""
    d = re.search(r'<path d="([^"]+)"', open(f"{SI_DIR}/{k}.svg").read())[1]
    return f'<svg class="{cls}" viewBox="0 0 24 24" aria-hidden="true"><path d="{d}"/></svg>'


LINK_CSS = """*{box-sizing:border-box}[hidden]{display:none!important}
:root{--bg:#fff;--ink:#1C1C1E;--sub:#55555B;--mut:#6B7180;--line:#E6E6EA;--chip:#F4F4F6;--tile:#F6F6F8;--pk:#E8436B;--pke:#D6365E;color-scheme:light}
@media(prefers-color-scheme:dark){:root{--bg:#0F1013;--ink:#ECEEF2;--sub:#B4B9C4;--mut:#9AA0AC;--line:#262931;--chip:#24272E;--tile:#24272E;--pk:#FF5C72;--pke:#FF9AA6;color-scheme:dark}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;letter-spacing:-.2px;-webkit-font-smoothing:antialiased;word-break:keep-all;overflow-wrap:anywhere}
main{max-width:480px;margin:0 auto;padding:22px calc(18px + env(safe-area-inset-right)) calc(28px + env(safe-area-inset-bottom)) calc(18px + env(safe-area-inset-left))}a{color:inherit;text-decoration:none}
a:focus-visible,button:focus-visible,summary:focus-visible{outline:3px solid var(--pk);outline-offset:2px}
.si{display:block;fill:currentColor}.disc{font-size:11.5px;color:var(--sub);line-height:1.5;margin:6px 2px 0}
.sec{display:flex;justify-content:space-between;align-items:baseline;margin:20px 2px 8px}.sec h2{margin:0;font-size:19px;font-weight:800;line-height:1.35}.sec h2 span{color:var(--pk)}.sec small{font-size:12px;color:var(--mut)}
.cd .sec{margin:16px 2px 6px}.cd h2{font-size:15px}.cd h2 small{font-weight:600;margin-left:4px}
.cr{display:flex;gap:6px;overflow-x:auto;padding:4px 3px 6px;margin:0 -3px;scrollbar-width:none}.cr::-webkit-scrollbar{display:none}.cr a{flex:none;max-width:180px;display:flex;align-items:center;gap:6px;font-size:12.5px;font-weight:600;padding:7px 11px 7px 7px;border-radius:999px;background:var(--chip);white-space:nowrap}.cr span{min-width:0;overflow:hidden;text-overflow:ellipsis}.cr b{flex:none;font-size:11px;font-weight:800;background:var(--ink);color:var(--bg);border-radius:999px;padding:1px 6px}
.cd details{margin-top:2px}.cd summary{font-size:12.5px;color:var(--sub);cursor:pointer;padding:4px 2px}.cd small.cn{display:block;font-size:12px;color:var(--mut);margin:6px 2px 0}
.chips{display:flex;gap:6px;margin:0 -3px 8px;padding:4px 3px;overflow-x:auto;scrollbar-width:none}.chips::-webkit-scrollbar{display:none}.chips button{flex:none;font:inherit;font-size:13px;font-weight:600;padding:7px 12px;border:0;border-radius:999px;background:var(--chip);color:var(--sub);cursor:pointer}.chips button[aria-pressed=true]{background:var(--ink);color:var(--bg)}
.g{display:grid;grid-template-columns:repeat(3,1fr);gap:10px 8px}.g a{min-width:0}.im{position:relative;aspect-ratio:1;border-radius:14px;overflow:hidden;background:var(--tile)}
.im i{position:absolute;inset:0;display:grid;place-items:center;font-size:30px;font-style:normal}.im img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;mix-blend-mode:multiply;background:#fff}
@media(prefers-color-scheme:dark){.im img{mix-blend-mode:normal}}
.nm{font-size:12px;line-height:1.38;height:33px;overflow:hidden;margin:7px 2px 2px;color:var(--sub);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}.pr{font-size:14px;font-weight:800;margin:0 2px}.pr em{font-style:normal;font-size:10.5px;font-weight:700;color:var(--pke);margin-left:4px}.ck{font-size:10.5px;color:var(--mut);margin:0 2px}
.mb{display:flex;gap:6px;flex:none}.mb a{font-weight:700;font-size:12.5px;padding:5px 10px;border-radius:999px;background:var(--chip);white-space:nowrap}.sec:has(.mb){flex-wrap:wrap;gap:6px;align-items:center}
.all{display:block;text-align:center;font-weight:700;font-size:15px;margin:22px 0 0;padding:13px;border-radius:14px;background:var(--chip)}.ft{font-size:11px;color:var(--mut);line-height:1.5;margin:10px 2px 0;text-align:center}
.vb,.eb2{display:none}.lb .vb,.lb .eb2{display:block}.lb .va{display:none}
.hd{display:flex;align-items:center;gap:8px}.lgi{width:32px;height:32px;border-radius:9px}.wm{font-size:17px;font-weight:800}
.ad{margin-left:auto;font:inherit;font-size:12px;color:var(--sub);background:none;border:1px solid var(--line);border-radius:999px;padding:3px 9px;cursor:pointer}.adw{font-size:11.5px;color:var(--sub);line-height:1.5;background:var(--chip);border-radius:12px;padding:10px 12px;margin:10px 0 0}
.va h1{font-size:23px;line-height:1.38;font-weight:800;margin:18px 0 14px;letter-spacing:-.6px}.va h1 span{color:var(--pk)}
.main{display:flex;justify-content:center;align-items:center;gap:6px;background:#FEE500;color:#191919;font-weight:700;font-size:15.5px;border-radius:14px;padding:14px}.main .si{width:20px;height:20px;margin-right:4px}
.ch{display:flex;justify-content:space-between;margin:16px 2px 8px}.ch a{display:flex;flex-direction:column;align-items:center;gap:6px;font-size:12px;color:var(--sub);width:62px}
.ch i{width:54px;height:54px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;overflow:hidden}.ch i .si{width:24px;height:24px}.ch i .fl{width:54px;height:54px}.ch .hm{background:#fff;box-shadow:inset 0 0 0 1px var(--line)}.ch .hm img{width:30px;height:30px;border-radius:8px}
@media(prefers-color-scheme:dark){.ch i,.bi{box-shadow:0 0 0 1px var(--line)}}
html.lb body{background:#FBFAF7}@media(prefers-color-scheme:dark){html.lb body{background:var(--bg)}}.eb{font-size:11px;letter-spacing:3px;color:#6E6E6E;font-weight:600}@media(prefers-color-scheme:dark){.eb{color:var(--mut)}}
.vb h1{display:flex;align-items:center;gap:10px;font-size:30px;font-weight:800;margin:4px 0 6px;letter-spacing:-.8px}.lgb{width:38px;height:38px;border-radius:10px}.tg{font-size:13.5px;color:var(--mut);margin:0}
.list{margin:18px 0 8px;border-top:1px solid var(--ink)}.list a{display:flex;align-items:center;gap:10px;padding:13px 2px;border-bottom:1px solid #E4E2DC}@media(prefers-color-scheme:dark){.list a{border-color:var(--line)}}
.bi{flex:none;width:28px;height:28px;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#fff}.bi .si{width:16px;height:16px}.list b{display:block;font-size:15.5px;font-weight:700;line-height:1.3}.list small{font-size:12.5px;color:var(--mut)}.list i{margin-left:auto;font-style:normal;color:var(--mut)}
.lb .sec{align-items:flex-end}.lb .sec h2{font-size:19px}.lb .cd h2{font-size:15px}.sec h2 .eb2{font-size:10.5px;letter-spacing:2.5px;color:#C43B3B;font-weight:600;margin-bottom:2px}.lb .im{border-radius:4px;background:#fff}.lb .pr em{color:#C43B3B}
@media(prefers-color-scheme:dark){.lb .im{background:var(--tile)}.lb .pr em,.sec h2 .eb2{color:var(--pke)}}"""
LINK_V = ("(function(){var f=(location.search.match(/[?&]v=([ab])(?:&|$)/)||[])[1],v=f;if(!v){try{v=localStorage.getItem('hp_link')}catch(e){}"  # A·B 반반: 주소 v= 고정(저장·집계 X) > 이 브라우저에 정해진 쪽 > 50:50 무작위(저장 안 되면 이번만)
          "if(v!=='a'&&v!=='b'){v=Math.random()<.5?'a':'b';try{localStorage.setItem('hp_link',v)}catch(e){}}}document.documentElement.className='l'+v;window.hpLV=v;window.hpLF=!!f;"
          "var g=window.goatcounter||(window.goatcounter={});if(f)g.no_onload=true;else g.path=function(){return 'link-'+v}})()")  # 보기 = 가상 경로 link-a·link-b(들어온 ?ref 출처 그대로)
LINK_GC = ("document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a[data-gc],a[rel~=\"sponsored\"]');if(!a||!window.goatcounter||!goatcounter.count||window.hpLF)return;"  # 채널 = link-a/채널(미리보기 쪽 = link/채널) · 상품 = buy/link-a/몰 주소+경로 · v= 고정 보기 = 집계 X
           "var v=window.hpLV,g=a.getAttribute('data-gc');if(g){if(v)g=g.replace(/^link\\//,'link-'+v+'/')}else{try{var h=new URL(a.href);g='buy/'+(v?'link-'+v+'/':'')+h.hostname+h.pathname}catch(x){return}}"
           "goatcounter.count({path:g,title:(a.textContent||'').trim().slice(0,80),event:true})})")
LINK_JS = """<script>(function(){var G=document.getElementById('lg'),N=document.getElementById('dn'),B=document.querySelectorAll('.chips button');
[].forEach.call(B,function(b){b.addEventListener('click',function(){var k=b.getAttribute('data-k'),n=0;[].forEach.call(B,function(x){x.setAttribute('aria-pressed',x===b?'true':'false')});
[].forEach.call(G.children,function(t){var on=(' '+t.getAttribute('data-k')+' ').indexOf(' '+k+' ')>=0;t.hidden=!on;if(on)n++});N.textContent=n})});
var a=document.querySelector('.ad');if(a)a.addEventListener('click',function(){var p=document.getElementById('adw'),o=p.hidden;p.hidden=!o;a.setAttribute('aria-expanded',o?'true':'false')})})()</script>"""


LINK_PRICE = re.compile(r"\s*(?:[/,(\[]\s*)?(?:쿠폰가|와우가|할인가|정가|최저가|첫구매)?\s*\d[\d,]*\d\s*원(?![가-힣A-Za-z0-9])|\s*[(\[]\s*\d[\d,]{2,}\s*/[^)\]]*[)\]]")  # 이름 속 가격 조각('22,900원/무료'·'(8900/무배)'·'/쿠폰가 16,830원')


def link_name(p):
    """칸·번호 줄 상품 이름: 이름 속 첫 가격 조각부터 뒤는 뺌('… 22,900원 (무배)' · '…(8900/무배)' · '…/쿠폰가 16,830원, 첫구매 …') — 시각 없는 가격 X(가격은 칸 아래 줄에 기준 시각과 같이). '1000원샵'처럼 이름인 것은 그대로."""
    n = parse(title_of(p["text"]))[1]
    m = LINK_PRICE.search(n)
    return n[:m.start()].rstrip(" ,/·([") if m and m.start() > 0 else n


def link_when(p, sh):
    """칸 가격의 기준 시각(작은 회색 — 10/25 리뷰 '시각 없는 가격 X'): 다시 확인한 가격 = 'M/D H시 확인' · 토스·그 밖 = 'M/D 가격'(올린 날)."""
    return f'{p["chk"]} 확인' if shop_of(p) != "toss" and sh[1] and p.get("chk") else f'{int(p["t"][5:7])}/{int(p["t"][8:10])} 가격'


def link_pool(it, today):
    """/link 지금 특가 후보(10/25 리뷰): 🔥 특가 중만(⏳ 대기·👍·품절 X) · 보이는 가격이 HOT_DAYS일 안(홈 🔥 칸과 같은 규칙) · 쿠팡·토스·네이버 수수료 링크만(대가성 문구 = SHOP_NOTES 3사)
    · 가격 있는 것만 — 사진 있는 것 먼저(같은 칸 = 사이트 진열 순서 그대로)."""
    since = time.strftime("%Y-%m-%d", time.gmtime(calendar.timegm(time.strptime(today, "%Y-%m-%d")) - (HOT_DAYS - 1) * 86400))
    xs = [x for x in it if x[2][0] == 0 and shop_of(x[1]) in SHOP_NOTES and aff(x[1].get("url")) and price_day(x[1], today) >= since and price_bits(x[1], x[2])[0]]
    return link_mix(sorted(xs, key=lambda x: not img_of(x[1])), today)


def link_mix(xs, today):
    """/link 앞 LINK_N칸(MM 10/26 Cowork — 진우 '링크만 보면 살 만한 상품이 너무 적다', 12칸 중 10칸이 히터): 품목 칸(cat_of — 히터·온풍기 = ❄️ 한 칸)마다 LINK_PER_CAT개까지 ·
    몰 돌림(쿠팡 → 토스 → 네이버, 그 몰에 넣을 게 없으면 다음 몰) · 확인 2일 넘은 가격(price_day가 그저께)은 뒤로(HOT_DAYS 그대로 — 순서만). 나머지 = 그 뒤에 원래 순서(품목 칩 칸)."""
    old = time.strftime("%Y-%m-%d", time.gmtime(calendar.timegm(time.strptime(today, "%Y-%m-%d")) - 86400))
    front, n = [], {}
    for q in ([x for x in xs if price_day(x[1], today) >= old], [x for x in xs if price_day(x[1], today) < old]):  # 어제·오늘 가격 먼저 돌리고, 12칸이 안 차면 그저께 가격
        while len(front) < LINK_N:
            got = [x for m in LINK_MALLS for x in [next((x for x in q if shop_of(x[1]) == m and x not in front and n.get(cat_of(x[1]), 0) < LINK_PER_CAT), None)] if x]
            if not got:
                break
            for x in got[:LINK_N - len(front)]:
                if n.get(cat_of(x[1]), 0) < LINK_PER_CAT:  # 같은 돌림 안에서 몰이 달라도 같은 칸 2개까지
                    front.append(x)
                    n[cat_of(x[1])] = n.get(cat_of(x[1]), 0) + 1
    return front + [x for x in xs if x not in front]


def link_front(pool):
    """전체 칩 칸 = pool 순서로 품목 칸(cat_of)마다 LINK_PER_CAT개까지 LINK_N개(link_mix가 앞에 둔 것 그대로 — 그 뒤는 칸이 찬 품목뿐이라 12칸이 안 차면 그만큼만)."""
    n, out = {}, []
    for x in pool:
        if len(out) < LINK_N and n.get(cat_of(x[1]), 0) < LINK_PER_CAT:
            out.append(x)
            n[cat_of(x[1])] = n.get(cat_of(x[1]), 0) + 1
    return out


def link_tabs(pool):
    """칩마다 앞 LINK_N개 -> [(i, p, 상태, 들어가는 칩들)], {칩: 개수} — 칸은 한 번만 그리고(쪽 가볍게) data-k로 거름, 순서 = pool 순서(앞 = 전체 칩 1~12번)."""
    on = {k: {x[0] for x in (link_front(pool) if k == "all" else [x for x in pool if cat_of(x[1]) == k][:LINK_N])} for k, _ in LINK_TABS}
    return [(*x, [k for k, _ in LINK_TABS if x[0] in on[k]]) for x in pool if any(x[0] in s for s in on.values())], {k: len(s) for k, s in on.items()}


def link_tile(i, p, sh, ks):
    """상품 칸: 정사각 사진(없으면 품목 이모지 — 번호 배지 X: 인스타 번호는 카드 딜 줄 01·02…, 10/25 Cowork) + 이름 2줄 + 가격 800·작은 분홍(와우가·쿠폰가) + 기준 시각(link_when) — 누르면 바로 몰."""
    shown, ex, _ = price_bits(p, sh)
    em = ex[0] if shop_of(p) != "toss" and ex and len(ex[0]) <= 8 else ""
    c, u = CAT_META.get(cat_of(p)), img_of(p)
    pic = f'<img src="{html.escape(u)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="this.remove()">' if u else ""
    return (f'<a href="{html.escape(go_url(i, p))}" rel="nofollow sponsored noopener" target="_blank" data-k="{" ".join(ks)}"' + ("" if "all" in ks else " hidden")
            + f'><div class="im"><i aria-hidden="true">{c[2] if c else "🛍️"}</i>{pic}</div><div class="nm">{html.escape(link_name(p))}</div>'
            + f'<div class="pr">{html.escape(shown)}' + (f'<em>{html.escape(em)}</em>' if em else "") + f'</div><div class="ck">{html.escape(link_when(p, sh))}</div></a>')


def link_cards(posts, out):
    """오늘 카드 딜 번호 줄(가로): 홈 '📸 … 카드 딜'과 같은 카드·같은 번호(card_stems·card_order, CARD_N개) — 인스타·Threads 캡션 '프로필 링크 → … 카드 딜 N번'.
    24시간 안 앞 카드는 접힌 한 줄로(첫 화면에 지금 특가 — 10/25 리뷰) · 쿠팡·토스·네이버 밖 제휴 링크(링크프라이스·올리브영)는 딜 쪽으로(그 쪽에 그 문구)."""
    blocks = [(x, ps) for x in reversed(card_stems(out)) if (ps := card_order(posts, x, out)[:CARD_N])]
    go = lambda i, p: f"{BASE}p/{i}.html" if aff(p.get("url")) and shop_of(p) not in SHOP_NOTES else go_url(i, p)
    row = lambda ps: '<div class="cr">' + "".join((f'<a aria-disabled="true"' if not site_ok(p) else f'<a href="{html.escape(go(i, p))}"' + (f' rel="nofollow {"sponsored " if aff(p.get("url")) else ""}noopener" target="_blank"' if go(i, p).startswith("http") and not go(i, p).startswith(BASE) else ""))
                                                  + f'><b>{n:02d}</b><span>{html.escape(link_name(p))}</span></a>' for n, (i, p) in enumerate(ps, 1)) + "</div>"  # 사이트에서 뺀 딜 = 번호·이름만(10/25 리뷰) · sponsored = 제휴 링크만
    return blocks and (f'<section class="cd" aria-labelledby="cdh"><div class="sec"><h2 id="cdh">📸 {html.escape(card_name(blocks[0][0]))}<small>번호 그대로</small></h2></div>{row(blocks[0][1])}'
                       + (f'<details><summary>앞 카드 딜 {len(blocks) - 1}개</summary>' + "".join(f'<small class="cn">{html.escape(card_name(x))}</small>{row(ps)}' for x, ps in blocks[1:]) + "</details>" if blocks[1:] else "")
                       + "</section>") or ""


def link_top(style, kakao):
    """머리 블록: a = 로고 머리 줄·2줄 문구·카톡 버튼(노랑)·채널 동그라미 5개 · b = HOTDEALPICK·로고 38 + 핫딜픽 30px·목록 줄(카톡·블로그·Threads·인스타)."""
    logo = lambda c, w: f'<img class="{c}" src="/icons/icon-192.png{IV}" alt="" width="{w}" height="{w}">'
    if style == "b":
        return (f'<div class="vb"><div class="eb">HOTDEALPICK</div><h1>{logo("lgb", 38)}{TITLE}</h1><p class="tg">매일 고른 생활 특가 · 목록은 매시간 갱신</p><nav class="list" aria-label="{TITLE} 채널">'
                + (f'<a href="{kakao}" data-gc="link/kakao"><span class="bi" style="background:#FEE500;color:#191919">{si("kakaotalk")}</span><span><b>카톡 특가방</b><small>하루 한 번 오늘의 픽</small></span><i aria-hidden="true">→</i></a>' if kakao else "")
                + "".join(f'<a href="{u}" data-gc="link/{k}"><span class="bi" style="{bg}">{si(ic)}</span><span><b>{nm}</b><small>{d}</small></span><i aria-hidden="true">→</i></a>'
                          for k, _, u, ic, bg, nm, d in LINK_CH if k != "telegram") + "</nav></div>")
    return (f'<div class="va"><header class="hd">{logo("lgi", 32)}<b class="wm">{TITLE}</b><button class="ad" type="button" aria-expanded="false" aria-controls="adw">제휴 안내</button></header>'
            f'<p class="adw" id="adw" hidden>{DISCLOSURE}</p><h1>오늘 살 만한 생활템,<br><span>매일</span> 골라 드려요</h1>'
            + (f'<a class="main" href="{kakao}" data-gc="link/kakao">{si("kakaotalk")}카톡 특가방 들어가기 →</a>' if kakao else "")
            + f'<nav class="ch" aria-label="{TITLE} 채널">' + "".join(f'<a href="{u}" data-gc="link/{k}"><i style="{bg}">{si(ic, "si fl" if k == "telegram" else "si")}</i>{s}</a>' for k, s, u, ic, bg, _, _ in LINK_CH)
            + f'<a href="{BASE}?ref=link" data-gc="link/home"><i class="hm">{logo("", 30)}</i>전체 특가</a></nav></div>')


def link_page(style, posts, it, out, alt=False, today=None):
    """/link 프로필 링크 한 장(10/25 진우 — 인스타는 글·댓글 링크가 안 눌려서 프로필 링크 하나에 채널 + 지금 특가, 외부 서비스 X): 인스타·Threads·카톡방 공지·블로그 끝에 이 주소.
    style 'ab' = 머리 블록 A·B 둘 다 넣고 JS(LINK_V)가 하나만(html.la/.lb — JS 꺼짐 = A, 리다이렉트 X) · 'a'|'b' = 그 시안만. 아래는 공용(B는 클래스로 모양만): 3사 대가성 문구 → 오늘 카드 딜 번호 줄 → 지금 특가 12(칩) → 전체 특가 보기.
    가볍게(사이트 CSS·검색·메뉴·서비스워커·사이트 글꼴 X — 시스템 글꼴(10/25 Cowork, 인스타 앱 안 첫 방문 317KB X), 쪽 안 CSS·아이콘) · 측정 = GoatCounter(ab = 가상 경로 link-a·link-b + link-a/채널·buy/link-a/몰, 미리보기 = 그 쪽 경로) · alt = 미리보기(noindex)."""
    today = today or time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600))
    rows, n = link_tabs(link_pool(it, today))
    kakao = html.escape(KAKAO_OPENCHAT_URL) if re.match(r"https://open\.kakao\.com/", KAKAO_OPENCHAT_URL) else ""
    deals = rows and (f'<section aria-labelledby="dh"><div class="sec"><h2 id="dh"><span class="eb2">TODAY</span>지금 특가 <span id="dn">{n["all"]}</span></h2><nav class="mb" aria-label="몰별 모음"><a href="{BASE}c/coupang/?ref=link" data-gc="link/coupang">🚀 쿠팡 모음</a><a href="{BASE}c/toss/?ref=link" data-gc="link/toss">💙 토스 모음</a></nav></div><div class="chips" role="group" aria-label="품목 고르기">'
                      + "".join(f'<button type="button" data-k="{k}" aria-pressed="{"true" if k == "all" else "false"}">{nm}</button>' for k, nm in LINK_TABS if n[k])
                      + '</div><div class="g" id="lg">' + "".join(link_tile(*x) for x in rows) + "</div></section>") or ""
    url = f"{BASE}link/" + (f"{style}/" if alt else "")
    t, d = f"{TITLE} — 채널·지금 특가 한 번에", "카톡 특가방·블로그·Threads·인스타·텔레그램과 지금 특가 12개를 한 곳에. 쿠팡·토스·네이버 생활 특가를 매일 골라요."
    kst = time.gmtime(time.time() + 9 * 3600)
    gc = (f'<script>{GC_APP}' + (LINK_V if style == "ab" else "") + f'</script><script data-goatcounter="https://{GC_CODE}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script><script>{LINK_GC}</script>') if GC_CODE \
        else (f"<script>{LINK_V}</script>" if style == "ab" else "")
    return (f'<!doctype html><html lang="ko"' + (f' class="l{style}"' if style != "ab" else "") + '><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<title>{t}</title><meta name="description" content="{d}">' + ('<meta name="robots" content="noindex,follow">' if alt else "")
            + f'<link rel="canonical" href="{url}"><meta property="og:site_name" content="{TITLE}"><meta property="og:title" content="{t}"><meta property="og:description" content="{d}"><meta property="og:type" content="website">'
            f'<meta property="og:url" content="{url}"><meta property="og:image" content="{BASE}og.png"><meta property="og:locale" content="ko_KR">'
            f'<link rel="icon" href="/favicon.ico{IV}" sizes="any"><link rel="apple-touch-icon" href="/icons/apple-touch-icon.png{IV}">'
            f'<meta name="theme-color" content="{"#FBFAF7" if style == "b" else "#ffffff"}" media="(prefers-color-scheme: light)"><meta name="theme-color" content="{PWA_DARK}" media="(prefers-color-scheme: dark)">'
            f'<style>{LINK_CSS}</style>{gc}</head><body><main>' + "".join(link_top(s, kakao) for s in ("a", "b") if s in style)
            + f'<p class="disc">{" ".join(SHOP_NOTES.values())}</p>{link_cards(posts, out)}{deals}'
            f'<a class="all" href="{BASE}?ref=link" data-gc="link/home">전체 특가 보기 →</a><p class="ft">칸마다 가격 아래 = 확인·게시 시각(토스 = 올린 날 가격) · 결제 전 최종가를 꼭 확인하세요 · 목록 {kst.tm_mon}/{kst.tm_mday} {kst.tm_hour:02d}:{kst.tm_min:02d} 갱신</p>'
            f'</main>{LINK_JS}</body></html>')


def build(posts, out="docs"):
    global MICONS
    os.makedirs(f"{out}/p", exist_ok=True)
    MICONS = {f[:-4] for f in os.listdir(f"{out}/icons/mall") if f.endswith(".png")} if os.path.isdir(f"{out}/icons/mall") else set()  # V 몰 로고(있는 것만)
    open(f"{out}/.nojekyll", "w").close()
    open(f"{out}/CNAME", "w").write(BASE.split("/")[2])  # GitHub Pages 커스텀 도메인 (재생성 때 안 날아가게)
    open(f"{out}/s.css", "w").write(CSS)
    latest = posts[-1]["t"][:10] if posts else ""
    urls = [(BASE, latest)]
    days = sorted({p["t"][:10] for p in posts if not p["text"].startswith("📋")}, reverse=True)
    noaff = {i for i, p in enumerate(posts) if not p["text"].startswith("📋") and not site_ok(p)}  # 사이트에서 뺀 비제휴 딜(site_ok) = 새 p/ 쪽 X · 있는 쪽은 그대로(목록·사이트맵·RSS·같이 보기·지난 딜·최저가 기록 X)
    gone = shelf_gone(posts) | noaff  # 채널 글로 이어진 진열 글 = 같이 보기·목록·사이트맵 X(페이지는 그대로)
    home = home_pool(posts, days)
    it = items(posts, days, home)
    now_ts = time.time()
    today = time.strftime("%Y-%m-%d", time.gmtime(now_ts + 9 * 3600))
    ds = drops(posts, it, now_ts)
    DROPS.clear()
    DROPS.update({i: (pct, r, c) for i, _, _, _, _, pct, r, c in ds})
    evs = events_on(it, today)
    evi = {i for g in evs for i, _, _ in g["xs"]}  # 진행 중 기획전 상품 = 홈 오늘의 픽·🔥·👍·TOP 10·오늘 마감 칸 X(배너로만 — 품목 칸·검색·목록 쪽은 그대로)
    dl = deadline_list(it, evi, today)
    cur = {posts[j].get("url"): j for j in sorted(home) if posts[j].get("url")}  # 주소 -> 지금 진열 글(같은 상품 최신)
    st = lambda i, p: home.get(i) or (p.get("own") and p.get("url") in cur and home[cur[p["url"]]]) or (4, None, f'{int(p["t"][5:7])}/{int(p["t"][8:10])} 게시' if p["t"][:10] not in days[:3] else "", [], False)  # 목록 밖 = 같은 상품 지금 상태, 없으면 배지 X(지난 딜을 🔥 특가라고 X) + 게시 날짜
    pool = [(j, q, set(keys(q).split())) for j, q in enumerate(posts) if q["t"][:10] in days[:2] and not q["text"].startswith("📋") and j not in gone
            and aff(q.get("url")) and "특가로는 약한 제품" not in q["text"]]
    recs = price_records(posts, skip=noaff)
    os.makedirs(f"{out}/c", exist_ok=True)
    for f in os.listdir(f"{out}/c"):  # 품목에서 빠진 옛 기록 페이지(c/*.html)만 지움 — 목록 쪽 폴더(c/life/ 등)는 그대로
        if f.endswith(".html") and f[:-5] not in recs:
            os.remove(f"{out}/c/{f}")
    for k, rec in recs.items():
        body, desc, note = record_page(k, rec, recs)
        open(f"{out}/c/{k}.html", "w").write(page(f"{rec[0]} 최저가 기록 — {rec[1]} 가격 | {TITLE}", body, desc, f"{BASE}c/{k}.html", note=note, cur="cats"))
        urls.append((f"{BASE}c/{k}.html", max(r[3]["t"][:10] for r in rec[2])))
    for i, p in reversed(list(enumerate(posts))):
        if i in noaff:  # 비제휴 딜 = 새 쪽 X(있는 쪽은 그대로 둠 — 목록·사이트맵에서만 빠짐)
            continue
        url, rel = f"{BASE}p/{i}.html", related(i, p, pool)
        more = rel and f'<section class="sec" aria-labelledby="relh"><h2 id="relh">같이 보면 좋은 딜</h2><div class="cards">{"".join(card(j, q, st(j, q)) for j, q in rel)}</div>' + (f'<p class="t">{TOSS_LINE}</p>' if any(shop_of(q) == "toss" for _, q in rel) else "") + '</section>'
        note = p["text"].split("\n", 1)[0] if urllib.parse.urlsplit(p.get("url") or "").netloc in NAVER_HOSTS + OY_HOSTS and p["text"].startswith(NOTE_STARTS) else ""  # 네이버·올영: 그 프로그램 문구 그대로 맨 앞(변형·누락 시 패널티)
        ti, sd, ld = seo(i, p)
        it_ = price_item(p)
        rl = it_ and it_[0] in recs and f'<a class="btn2" href="{BASE}c/{it_[0]}.html">📈 {it_[1]} {it_[3]} 최저가 기록 보기</a>'  # 그 품목 기록 페이지로(내부 링크 — 검색 로봇이 찾게)
        c = CAT_META.get(cat_of(p))
        back = f'<a class="btn2" href="{c_url(c[0] if c else "hot")}">{c[2] + " " + c[1] if c else "🔥 지금 특가"} 더 보기 →</a>'
        open(f"{out}/p/{i}.html", "w").write(page(ti, deal_card(i, p) + (rl or "") + (more or "") + back + SEEN_JS, sd, url, note=note, head=ld or "", og=img_of(p)))
        if i not in gone:
            urls.append((url, p["t"][:10]))
    ls = lists(posts, days, home)
    ig_top(posts, out, now_ts)
    tops = top_list(posts, it, evi)
    ls.update(drop=("📉 가격 내려간 상품", f"같은 구성(같은 링크) 처음 올린 가격보다 {DROP_MIN}%↑ 내린 쿠팡·네이버 상품 · 우리 기록 대비", [(i, p, sh) for i, p, sh, *_ in ds], ""),
              today=("⏰ 오늘 마감", "오늘 밤 12시에 끝나는 특가(토스 하루특가·선착순 등)", dl, ""), rehot=("🔁 다시 특가", "특가 가격으로 다시 돌아온 상품", [x for x in it if x[2][0] == 0 and x[2][4]], ""), top=(tops[0], f"{tops[1]} 순위", tops[2], ""))  # 10/24 Cowork '변경 찾기' 상태 쪽(사이트맵)
    for slug, (head, desc, xs, mall) in ls.items():
        for u, k, ti, sd, body, ld in (mall_page(slug, head, desc, xs, recs) if mall else list_pages(slug, head, desc, xs, mall, recs)):
            write(out, u[len(BASE):], page(ti, body, sd, u, cur="fire" if slug in dict(STAT_CHIPS) else "cats", head=ld and ld_tag(ld) or ""))
            urls.append((u, latest))
        n = 1 if mall else max(1, -(-len(xs) // PER))
        for d in os.listdir(f"{out}/c/{slug}"):  # 목록이 줄면 뒤쪽 옛 쪽(c/이름/N/) 지움 — 남으면 옛 카드·자기 canonical로 검색에 남음
            if d.isdigit() and int(d) > n:
                shutil.rmtree(f"{out}/c/{slug}/{d}")
    for d in os.listdir(f"{out}/c"):  # 없어진 목록 이름 폴더도
        if os.path.isdir(f"{out}/c/{d}") and d not in ls:
            shutil.rmtree(f"{out}/c/{d}")
    mc = collections.Counter(shop_of(p) for _, p, _ in it)
    write(out, "c/", page(f"카테고리 | {TITLE}", '<h1 class="h">🗂️ 카테고리</h1><div class="t">쇼핑몰·상태·품목으로 골라 보세요</div><h2 class="ch">🛍 쇼핑몰로 찾기</h2><nav class="mt3" aria-label="쇼핑몰">'
                          + "".join(f'<a class="mt {k}" href="{c_url(k)}" data-gc="mall/{k}"><b>{mall_label(k, n)}</b><small>{sub}</small><i>{mc[k]}개</i></a>' for k, n, sub in MALL_BTN) + "</nav>"
                          + stat_chips("") + '<h2 class="ch">🗂 품목으로 찾기</h2>' + tiles(tuple(CAT_META), True) + (rec_nav(recs) or "") + LSW + LSW_JS,
                         "생필품·식품·뷰티·주방·세탁·간식·여성용품·겨울템 — 품목별 특가 모음", f"{BASE}c/", cur="cats"))
    urls.append((f"{BASE}c/", latest))
    top = lambda xs: [x for x in xs if x[0] not in evi]
    day, ps = today_picks(posts, top(it), recs, out)
    os.makedirs(f"{out}/e", exist_ok=True)
    for f in os.listdir(f"{out}/e"):  # 마감 지난(또는 없어진) 행사 쪽 = 내림(상품 카드는 품목 칸에 그대로)
        if f.endswith(".html") and f[:-5] not in {g["slug"] for g in evs}:
            os.remove(f"{out}/e/{f}")
    for g in evs:
        ti, sd, body, ld = ev_page(g, today)
        open(f"{out}/e/{g['slug']}.html", "w").write(page(ti, body, sd, f"{BASE}e/{g['slug']}.html", cur="fire", head=ld and ld_tag(ld) or ""))
        urls.append((f"{BASE}e/{g['slug']}.html", latest))
    try:
        saved_picks = json.load(open(f"{out}/{PICKS}"))
    except (OSError, ValueError):
        saved_picks = {}
    pdays = sorted(saved_picks)
    today = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600))
    for n_, d in enumerate(pdays):  # 날짜 쪽 /today/YYYY-MM-DD/ — 오늘 = 홈과 같은 픽, 지난날 = 저장 목록 중 지금도 진열된 것(빠진 상품·문제 상품 X)만 지금 상태로 · 앞뒤 날짜 링크
        dps = ps if d == day == today else [(cur[u], posts[cur[u]], home[cur[u]]) for i in saved_picks[d] if i < len(posts) and (u := posts[i].get("url")) in cur]
        md, mdk = f"{int(d[5:7])}/{int(d[8:10])}", f"{int(d[5:7])}월 {int(d[8:10])}일"
        names = " · ".join(parse(title_of(p["text"]))[1] + (f" {price_bits(p, sh)[0]}" if price_bits(p, sh)[0] and shop_of(p) != "toss" else "") for _, p, sh in dps)  # 토스 = 설명에 가격 X(게시 시점 표기가 쪽에만)
        ld = {"@context": "https://schema.org", "@type": "ItemList", "name": f"오늘의 픽 {md}", "itemListElement": [{"@type": "ListItem", "position": n, "url": f"{BASE}p/{i}.html", "name": parse(title_of(p["text"]))[1], **({"image": img_of(p)} if img_of(p) else {})}
                                                                                                    for n, (i, p, _) in enumerate(dps, 1)]}
        malls = "·".join(dict.fromkeys(n for k, n, _ in MALLS for _, p, _ in dps if shop_of(p) == k)) or "핫딜"
        nav = '<nav class="pg" aria-label="날짜">' + (f'<a class="btn2" href="{BASE}today/{pdays[n_ - 1]}/" rel="prev">← {int(pdays[n_ - 1][5:7])}/{int(pdays[n_ - 1][8:10])} 픽</a>' if n_ else "") \
            + (f'<a class="btn2" href="{BASE}today/{pdays[n_ + 1]}/" rel="next">{int(pdays[n_ + 1][5:7])}/{int(pdays[n_ + 1][8:10])} 픽 →</a>' if n_ + 1 < len(pdays) else "") + "</nav>"
        nav = "" if nav.endswith('"날짜"></nav>') else nav  # 앞뒤 날짜 없음(첫날) = 빈 칸 X(16:00 점검)
        write(out, f"today/{d}/", page(f"오늘의 픽 — {mdk} {malls} 특가 | {TITLE}", f'<h1 class="h">오늘의 픽 · {mdk}</h1>' + (pick_section(d, dps, True) or '<p class="t">이날 고른 상품은 지금 진열에서 빠졌어요.</p>') + nav
                                       + top4("fire", "hot", "🔥 지금 특가", top(ls["hot"][2]), {i for i, _, _ in dps}), f"{mdk} 핫딜픽 오늘의 픽 — {names}"[:150], f"{BASE}today/{d}/",
                                       head=ld_tag(ld), kind="article", cur="home"))  # og = 기본 og.png(인스타 카드는 다른 5개 딜이라 X)
        urls.append((f"{BASE}today/{d}/", d))
    try:
        plinks = json.load(open(PROMO_LINKS))
    except (OSError, ValueError):
        plinks = {}
    plinks = plinks if isinstance(plinks, dict) else {}
    icons = MICONS
    tagged, slugs = {}, {g["tag"]: g["slug"] for g in evs}
    for e in ev_list() + [p for p in posts if p.get("tag") not in slugs]:  # posts tag = 봇이 진열한 글(AA 쿠가세 저녁 가전 — events에 없음) · 행사 쪽(e/) 있는 tag = events 상품만(카드 개수 = 행사 쪽 상품)
        if isinstance(e, dict) and isinstance(e.get("tag"), str) and isinstance(e.get("url"), str):
            tagged.setdefault(e["tag"], set()).add(e["url"])
    ps_ = promo_shown(promo_list(today), it, tagged, plinks)  # 기획전 모음(10/25 Cowork·진우 — promos.json, 제휴 되는 것만): 홈 띠 + /events/
    band = promo_band(ps_, it, tagged, slugs, plinks, icons, today)
    ptags = {p.get("tag") for p, _ in promo_now(ps_, today)} if band else set()  # 옛 기획전 넘김 배너(events tag) = 기획전 띠에 없는 행사만(같은 행사 두 번 X)
    evh = f"{BASE}events/" if any(st != "past" for _, st, _ in ps_) else ""
    ti, sd, pbody = promo_page(ps_, it, tagged, slugs, plinks, icons, today)
    write(out, "events/", page(ti, pbody, sd, f"{BASE}events/", cur="fire", noindex=not evh, ogt=f"기획전 모음 · {TITLE}"))  # og 그림 = 기본 og.png(로고 카드 — Threads 정보 글 링크 카드)
    if evh:
        urls.append((f"{BASE}events/", today))
    cp = card_picks(posts, out)
    cp = cp.replace('<div class="t">번호를 누르면', f'<p class="t">{" ".join(SHOP_NOTES.values())}</p><div class="t">번호를 누르면', 1)  # 카드 번호 칸도 몰로 바로 -> 3사 문구
    hot, hot_ids = hot_section(it, evi, today)
    fx = [x for x in it if f'href="{BASE}p/{x[0]}.html"' in hot]  # 🔥 = 탭 전부 합쳐 1번
    dsh = cap2(ds, dl[:12], fx)  # 같은 상품 홈 최대 2번: 오늘 마감 > 🔥 > 📉 > 픽 > 꾸준템(10/24 진우 v3 ② · TOP 10·찜/본·숨은 #today X)
    psh = cap2(ps, dl[:12], fx, dsh[:DROP_N])  # 홈 픽만(날짜 쪽·RSS는 저장 목록 그대로)
    stx = mix(cap2([x for x in top(ls["steady"][2]) if x[0] not in hot_ids], dl[:12], fx, dsh[:DROP_N], psh), 10)  # 👍 = 몰 섞기(10/24 Cowork '쿠팡 꾸준템도') · 🔥 줄에 나온 건 X
    body = (cp.replace('<section class="card" id="today"', '<section class="card" id="today" hidden', 1) + hot + MY + MY_JS + top_section(*tops) + deadline_section(dl, evs, today) + drop_section(dsh, today, len(ds))
            + hs_section("pick", "⭐ 오늘의 픽", md_of(day) if day else "", psh, f"{BASE}today/{day}/" if day else "")
            + hs_section("steady", "👍 꾸준히 주문 들어오는 것", f"{len(top(ls['steady'][2]))}개", stx, c_url("steady")) + (rec_nav(recs) or "")
            + ('<a class="u" style="display:block;padding:10px 2px 0;text-decoration:none" href="#today">📸 인스타·Threads 카드 번호로 찾기 →</a>' if 'id="today"' in cp else "")
            + f'<a class="btn2" href="{BASE}all.html">지난 딜 전체 보기 →</a>' + TAB_JS + LSW + LSW_JS) if posts else "<p>첫 딜을 준비 중이에요.</p>"
    ld = json.dumps({"@context": "https://schema.org", "@graph": [{"@type": "WebSite", "name": TITLE, "url": BASE, "inLanguage": "ko"},
                                                                  {"@type": "Organization", "name": TITLE, "url": BASE, "logo": f"{BASE}icons/icon-512.png", "sameAs": [INSTA, THREADS, BLOG, CHANNEL]}]}, ensure_ascii=False)
    open(f"{out}/index.html", "w").write(page(f"{TITLE} - 오늘의 핫딜·특가 모음 (쿠팡·네이버·토스)", body + HASH_JS,
                                              "쿠팡·토스·네이버 생필품·식품·화장품 특가를 매일 골라 정리해요. 오늘의 픽 3개, 지금 특가, 꾸준히 주문 들어오는 것까지.", BASE, top=INSTALL,
                                              head=f'<script type="application/ld+json">{ld}</script>', cur="home", lead=band + f'<div class="la">{mall_nav(evs, evh)}{tiles(tuple(CAT_META), True)}</div><div class="lb">' + ev_banner([g for g in evs if g["tag"] not in ptags]) + quick_nav(evs, len(dl) + sum(g["until"] == today for g in evs), calendar.timegm(time.strptime(today, "%Y-%m-%d")) + 86400 - 9 * 3600, tops[0].startswith("🏆"), evh) + "</div>" if posts else "", dis=HOME_DIS))
    json.dump(search_index(it, {x[1].get("url"): p["tag"] for p, st, _ in ps_ if st != "past" and p.get("tag") for x in promo_goods(p, it, tagged)}), open(f"{out}/search.json", "w"), ensure_ascii=False, separators=(",", ":"))
    try:
        prev = json.load(open(f"{out}/changes.json"))
        prev = prev if isinstance(prev, dict) else None
    except (OSError, ValueError):
        prev = None
    ch = changes_json(posts, it, ds, dl, now_ts, prev)
    json.dump(ch, open(f"{out}/changes.json", "w"), ensure_ascii=False, separators=(",", ":"))  # 10/24 Cowork '변경 찾기'(찜·알림 탭·🔔 점) — 나중 푸시(OneSignal)도 이것으로
    write(out, "saved/", page(f"찜한 딜 | {TITLE}", SAVED + CHG_JS, "이 폰에 찜해 둔 딜", f"{BASE}saved/", cur="saved", noindex=True))
    write(out, "alarm/", page(f"알림 받기 | {TITLE}", alarm_body(ch) + CHG_JS, "새 특가를 바로 받아 보는 방법", f"{BASE}alarm/", cur="alarm", noindex=True, top=INSTALL))
    open(f"{out}/manifest.webmanifest", "w").write(json.dumps(MANIFEST, ensure_ascii=False, indent=1))  # 웹앱(10/23 진우) — 아이콘은 cards.app_icons(docs/icons, 한 번 만들어 커밋)
    open(f"{out}/sw.js", "w").write(SW_JS % hashlib.md5(open(f"{out}/index.html", "rb").read() + open(f"{out}/manifest.webmanifest", "rb").read()).hexdigest()[:10])  # 홈·manifest(아이콘 주소)가 바뀐 배포마다 캐시 이름 바뀜(같으면 그대로 — 실행마다 커밋 X)
    hist = sorted(((i, p) for i, p in enumerate(posts) if not p["text"].startswith("📋") and i not in gone), key=lambda x: (x[1]["t"][:10], bool(shop_of(x[1])), x[1]["t"]), reverse=True)  # 날짜 최신 -> 그날 3사 먼저 -> 최신
    n = max(1, -(-len(hist) // PER))
    for k in range(1, n + 1):
        part, u = hist[(k - 1) * PER:k * PER], f"{BASE}all.html" if k == 1 else f"{BASE}all/{k}/"
        grp = {}
        for i, p in part:
            grp.setdefault(p["t"][:10], []).append((i, p))
        nav = '<nav class="pg" aria-label="쪽">' + (f'<a class="btn2" href="{BASE}all.html" rel="prev">← 처음</a>' if k == 2 else f'<a class="btn2" href="{BASE}all/{k - 1}/" rel="prev">← 이전 20개</a>' if k > 2 else "") \
            + (f'<a class="btn2" href="{BASE}all/{k + 1}/" rel="next">다음 20개 보기 →</a>' if k < n else "") + "</nav>"
        body = (f'<h1 class="h">지난 딜 전체{f" · {k}쪽" if k > 1 else ""}</h1><div class="t">핫딜픽에 올라온 딜 {len(hist)}개 · 최신 순</div>' + (f'<p class="t">{TOSS_LINE}</p>' if any(shop_of(p) == "toss" for _, p in part) else "")
                + "".join(f'<section class="sec day" id="d{m}" aria-labelledby="d{m}h"><h2 id="d{m}h">{int(d[5:7])}월 {int(d[8:])}일 딜</h2><div class="cards">{"".join(card(i, p, st(i, p)) for i, p in g)}</div></section>'
                          for m, (d, g) in enumerate(grp.items())) + nav)
        write(out, u[len(BASE):], page(f"지난 딜 전체{f' {k}쪽' if k > 1 else ''} | {TITLE}", body, f"핫딜픽에 올라온 딜 전체{f' · {k}쪽' if k > 1 else ''}", u))
    if os.path.isdir(f"{out}/all"):
        for d in os.listdir(f"{out}/all"):  # 줄어든 뒤쪽 옛 쪽 지움
            if d.isdigit() and int(d) > n:
                shutil.rmtree(f"{out}/all/{d}")
    urls.append((f"{BASE}all.html", latest))
    urls += [u for u in [steady_page(out)] if u]
    alt = "a" if LINK_STYLE == "b" else "b"  # /link/ = LINK_STYLE('ab' = A·B 반반) · 다른 시안 미리보기 = /link/<글자>/(noindex — 사이트맵 X)
    write(out, "link/", link_page(LINK_STYLE, posts, it, out, today=today))
    write(out, f"link/{alt}/", link_page(alt, posts, it, out, alt=True, today=today))
    for d in {"a", "b"} - {alt}:  # 시안을 바꾸면 옛 미리보기 쪽 지움
        if os.path.isdir(f"{out}/link/{d}"):
            shutil.rmtree(f"{out}/link/{d}")
    urls.append((f"{BASE}link/", latest))
    open(f"{out}/sitemap.xml", "w").write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                           + "".join(f"<url><loc>{u}</loc>{d and f'<lastmod>{d}</lastmod>'}</url>" for u, d in urls) + "</urlset>")
    open(f"{out}/robots.txt", "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}sitemap.xml\n")  # 검색 로봇에게 사이트맵 위치(10/9) — '*' = 네이버 Yeti도 허용
    rss = [(f"오늘의 픽 {int(day[5:7])}월 {int(day[8:10])}일 — " + " · ".join(parse(title_of(p["text"]))[1] for _, p, _ in ps), f"{BASE}today/{day}/",
            "핫딜픽이 고른 오늘의 특가 " + " / ".join(f"{n}. [{chip_of(p)}] {parse(title_of(p['text']))[1]} {'' if shop_of(p) == 'toss' else price_bits(p, sh)[0]}".strip() for n, (_, p, sh) in enumerate(ps, 1)),
            f"{day} {PICK_HOUR:02d}:00", "")] if ps and day else []  # 10/24 N1: 오늘의 픽 날짜 쪽 = RSS 첫 글(매일 새 글, 설명 = 3개 전부)
    md = f"{int(today[5:7])}/{int(today[8:10])}"
    rss += [(f"{CAT_META[k][1]} 특가 모음 ({md})", c_url(CAT_META[k][0]), f"{CAT_META[k][1]} 특가 {len(ls[CAT_META[k][0]][2])}개 — " + " · ".join(parse(title_of(p["text"]))[1] for _, p, _ in ls[CAT_META[k][0]][2][:3]),
             f"{today} 00:00", f"c-{CAT_META[k][0]}-{today}") for k in TILES if ls[CAT_META[k][0]][2]]  # 10/24 N1 '품목 쪽 사이트맵·RSS에': 타일 8칸 1쪽 = 날마다 새 글(guid에 날짜)
    rss += [(title_of(p["text"]), f"{BASE}p/{i}.html", summary(p["text"]), p["t"][:16], "") for i, p in [(i, p) for i, p in enumerate(posts) if not p["text"].startswith("📋") and i not in noaff][-(30 - len(rss)):][::-1]]  # 합쳐 30개  # 네이버 서치어드바이저 'RSS 제출'용 최근 딜 30개
    open(f"{out}/rss.xml", "w").write(
        f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{TITLE}</title><link>{BASE}</link><description>쿠팡·토스·네이버 생필품·식품·화장품 특가를 매일 골라 정리해요</description><language>ko</language>'
        + "".join(f'<item><title>{html.escape(t)}</title><link>{u}</link>' + (f'<guid isPermaLink="false">{g}</guid>' if g else f"<guid>{u}</guid>") + f'<description>{html.escape(d)}</description>'
                  f'<pubDate>{time.strftime("%a, %d %b %Y %H:%M:00 +0900", time.strptime(w, "%Y-%m-%d %H:%M"))}</pubDate></item>' for t, u, d, w, g in rss) + "</channel></rss>")
    return len(posts)


if __name__ == "__main__":
    posts = json.load(open("posts.json")) if os.path.exists("posts.json") else []
    print("site:", build(posts), "posts")

