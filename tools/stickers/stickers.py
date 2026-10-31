# tools/stickers/stickers.py — 핫딜픽 귀여운 스티커 8장(1080×1080 — 품목) 원본 (Cowork 10/26, 진우 '귀여운 그림이나 사진 있음 좋겠다')
# 사용: python3 tools/stickers/stickers.py out.html → playwright로 section#<키> 스크린샷 → docs/img/stk/<키>.png
# 키 = PRICE_ITEMS 품목(ramen·water·toilet-paper·coffee-mix·wet-wipes·eggs·rice·milk) — 수다 글 기본 chat·chat-1~5.png = 진우 그림(10/31)이라 여기서 안 그림(덮어쓰기 X)

def sparkle(x, y, s, c='#FFD84D'):
    return f'<path d="M{x} {y-s} Q{x} {y} {x+s} {y} Q{x} {y} {x} {y+s} Q{x} {y} {x-s} {y} Q{x} {y} {x} {y-s}Z" fill="{c}"/>'

def heart(x, y, s, c='#FF9DB5'):
    return (f'<path transform="translate({x} {y}) scale({s})" d="M0 6 C-10 -4 -20 6 -10 14 L0 22 L10 14 C20 6 10 -4 0 6Z" fill="{c}"/>')

def paw(x, y, s, c='#F3C9A8', o=.7):
    return (f'<g transform="translate({x} {y}) scale({s})" fill="{c}" opacity="{o}"><ellipse cx="0" cy="8" rx="11" ry="9"/>'
            '<circle cx="-12" cy="-6" r="5"/><circle cx="-4" cy="-12" r="5"/><circle cx="4" cy="-12" r="5"/><circle cx="12" cy="-6" r="5"/></g>')

def tag(x, y, rot, size=1):
    return (f'<g transform="translate({x} {y}) rotate({rot}) scale({size})"><path d="M-70 -32 H42 a14 14 0 0 1 14 14 V18 a14 14 0 0 1 -14 14 H-70 L-96 0 Z" fill="#F0384A"/>'
            '<circle cx="-70" cy="0" r="7" fill="#FFF4E0"/><text x="-12" y="17" text-anchor="middle" font-family="PX" font-weight="800" font-size="48" fill="#fff">딜</text></g>')

def eye(cx, cy, r=24):
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#2A1C14"/><circle cx="{cx+7}" cy="{cy-8}" r="{r*0.36:.1f}" fill="#fff"/>'
            f'<circle cx="{cx-8}" cy="{cy+8}" r="{r*0.15:.1f}" fill="#fff" opacity=".85"/>')

# 골든 리트리버 '물어왔멍' (512 박스, 배경 없음)
DOG = (
    # 처진 귀
    '<path d="M118 196 C70 230 64 330 108 372 C140 400 176 368 172 322 C168 270 168 226 150 196Z" fill="#D48A2E"/>'
    '<path d="M394 196 C442 230 448 330 404 372 C372 400 336 368 340 322 C344 270 344 226 362 196Z" fill="#D48A2E"/>'
    # 머리 + 정수리 털
    '<ellipse cx="256" cy="268" rx="150" ry="136" fill="#F2B457"/>'
    '<path d="M236 136 q14 -22 22 -2 q10 -20 20 4" stroke="#F2B457" stroke-width="14" fill="none" stroke-linecap="round"/>'
    # 크림색 얼굴
    '<ellipse cx="256" cy="312" rx="98" ry="74" fill="#FFE6B8"/>'
    '<ellipse cx="200" cy="246" rx="40" ry="36" fill="#F8C774" opacity=".55"/><ellipse cx="312" cy="246" rx="40" ry="36" fill="#F8C774" opacity=".55"/>'
    + eye(204, 252) + eye(308, 252) +
    '<ellipse cx="166" cy="304" rx="26" ry="15" fill="#FF8FA8" opacity=".55"/><ellipse cx="346" cy="304" rx="26" ry="15" fill="#FF8FA8" opacity=".55"/>'
    # 코·입·혀
    '<path d="M236 286 Q256 276 276 286 Q276 304 256 308 Q236 304 236 286Z" fill="#3A2416"/><ellipse cx="250" cy="287" rx="6" ry="3.5" fill="#fff" opacity=".55"/>'
    '<path d="M256 308 v8 M256 316 q-16 14 -30 2 M256 316 q16 14 30 2" stroke="#3A2416" stroke-width="5.5" fill="none" stroke-linecap="round"/>'
    '<path d="M246 326 q10 22 20 0 Z" fill="#FF7E95"/>'
    + tag(318, 392, -12, 0.92)
)

# 삼색이 '득템냥' (512 박스, 배경 없음)
CAT = (
    '<defs><clipPath id="hc2"><ellipse cx="256" cy="276" rx="146" ry="126"/></clipPath>'
    '<clipPath id="el"><path d="M136 222 L156 84 L248 168 Z"/></clipPath><clipPath id="er"><path d="M376 222 L356 84 L264 168 Z"/></clipPath></defs>'
    # 귀: 왼쪽 주황, 오른쪽 검정
    '<path d="M136 222 L156 84 L248 168 Z" fill="#FFFDF8"/><g clip-path="url(#el)"><rect x="120" y="70" width="140" height="80" fill="#F39A45"/></g>'
    '<path d="M162 194 L170 122 L222 168 Z" fill="#FFB3C6"/>'
    '<path d="M376 222 L356 84 L264 168 Z" fill="#FFFDF8"/><g clip-path="url(#er)"><rect x="250" y="70" width="140" height="90" fill="#33302F"/></g>'
    '<path d="M350 194 L342 122 L290 168 Z" fill="#FFB3C6"/>'
    # 머리 + 삼색 무늬
    '<ellipse cx="256" cy="276" rx="146" ry="126" fill="#FFFDF8"/>'
    '<g clip-path="url(#hc2)"><path d="M96 150 C150 130 236 150 238 210 C240 250 190 262 150 250 C110 240 92 200 96 150Z" fill="#F39A45"/>'
    '<path d="M300 150 C350 136 420 170 414 236 C376 246 330 232 312 206 C300 188 296 168 300 150Z" fill="#33302F"/></g>'
    + eye(204, 266, 23) + eye(308, 266, 23) +
    '<ellipse cx="170" cy="312" rx="24" ry="14" fill="#FF8FA8" opacity=".5"/><ellipse cx="342" cy="312" rx="24" ry="14" fill="#FF8FA8" opacity=".5"/>'
    '<path d="M245 300 h22 l-11 11 Z" fill="#FF8FA8" stroke="#FF8FA8" stroke-width="4" stroke-linejoin="round"/>'
    '<path d="M256 312 q-10 13 -22 4 M256 312 q10 13 22 4" stroke="#3A2A25" stroke-width="5" fill="none" stroke-linecap="round"/>'
    '<path d="M146 300 l44 6 M150 322 l42 -4 M366 300 l-44 6 M362 322 l-42 -4" stroke="#CDBFB5" stroke-width="4" stroke-linecap="round"/>'
    # '딜' 쇼핑백 + 앞발
    '<g transform="translate(316 330)"><path d="M16 20 q0 -32 30 -32 q30 0 30 32" stroke="#B3122C" stroke-width="7" fill="none"/>'
    '<rect x="0" y="16" width="92" height="84" rx="16" fill="#F0384A"/><text x="46" y="76" text-anchor="middle" font-family="PX" font-weight="800" font-size="46" fill="#fff">딜</text></g>'
    '<ellipse cx="318" cy="372" rx="26" ry="22" fill="#FFFDF8" stroke="#EADFD5" stroke-width="3"/>'
    '<path d="M308 362 v10 M318 360 v12 M328 362 v10" stroke="#E6D8CC" stroke-width="3" stroke-linecap="round"/>'
)

# 핫딜픽 귀여운 스티커(1080×1080) — 물어왔멍(골든 리트리버) · 득템냥(삼색이) + 품목 소품 + 말풍선
# 캐릭터 SVG는 kakao2/gen.py(10/26 카톡방 시안)에서 가져옴. 출력: stickers.html(섹션 id = 품목 키) → shot.js로 PNG
import os, sys
F = 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'fonts')) + '/'  # 저장소 fonts/ (Pretendard·NotoColorEmoji)

def bowl():  # 라면 그릇(일반 그림)
    return ('<g fill="none" stroke="#fff" stroke-width="12" stroke-linecap="round" opacity=".85"><path d="M150 40 q-20 -30 0 -60 q20 -30 0 -60"/><path d="M230 34 q-20 -30 0 -60 q20 -30 0 -60"/><path d="M310 40 q-20 -30 0 -60 q20 -30 0 -60"/></g>'
            '<rect x="300" y="-60" width="18" height="250" rx="9" fill="#9A5B2E" transform="rotate(28 309 65)"/><rect x="334" y="-56" width="18" height="250" rx="9" fill="#B86E3A" transform="rotate(36 343 69)"/>'
            '<ellipse cx="230" cy="130" rx="210" ry="52" fill="#F0A33A"/>'
            '<g fill="none" stroke="#FFD45A" stroke-width="11" stroke-linecap="round"><path d="M50 130 q24 -24 48 0 t48 0 t48 0 t48 0 t48 0 t48 0 t48 0 t48 0"/><path d="M76 112 q24 -22 48 0 t48 0 t48 0 t48 0 t48 0 t48 0 t48 0"/><path d="M84 150 q24 -22 48 0 t48 0 t48 0 t48 0 t48 0 t48 0 t48 0"/></g>'
            '<ellipse cx="150" cy="108" rx="50" ry="32" fill="#fff"/><circle cx="155" cy="108" r="19" fill="#FF9F1C"/>'
            '<g fill="none" stroke="#2FAE4E" stroke-width="6"><circle cx="240" cy="100" r="10"/><circle cx="270" cy="124" r="8"/><circle cx="330" cy="140" r="8"/></g>'
            '<path d="M20 130 Q28 310 230 310 Q432 310 440 130 Z" fill="#FFF4DC"/><path d="M34 186 Q230 226 426 186 L420 212 Q230 254 40 212 Z" fill="#E8332A"/>'
            '<rect x="160" y="304" width="140" height="26" rx="12" fill="#E8D6B4"/>')

def bottle():  # 생수병
    return ('<rect x="150" y="-40" width="70" height="40" rx="10" fill="#4FA3E8"/>'
            '<path d="M140 0 h90 q30 30 30 70 v260 q0 30 -30 30 h-90 q-30 0 -30 -30 v-260 q0 -40 30 -70Z" fill="#D6EEFF" stroke="#9CCBF2" stroke-width="6"/>'
            '<path d="M110 130 h150 v90 h-150Z" fill="#7FC1F5" opacity=".7"/><path d="M135 60 v220" stroke="#fff" stroke-width="14" stroke-linecap="round" opacity=".7"/>'
            '<path d="M330 120 q22 34 0 46 q-22 -12 0 -46Z" fill="#7FC1F5"/><path d="M40 200 q16 26 0 34 q-16 -8 0 -34Z" fill="#7FC1F5"/>')

def roll():  # 화장지 롤
    return ('<defs><linearGradient id="rl" x1="0" x2="1"><stop offset="0" stop-color="#F1ECE6"/><stop offset=".35" stop-color="#fff"/><stop offset="1" stop-color="#EDE6DE"/></linearGradient></defs><rect x="40" y="40" width="300" height="260" fill="url(#rl)" stroke="#E5DED6" stroke-width="6"/>'
            '<ellipse cx="190" cy="300" rx="150" ry="46" fill="#F4EFEA" stroke="#E5DED6" stroke-width="6"/>'
            '<ellipse cx="190" cy="40" rx="150" ry="46" fill="#fff" stroke="#E5DED6" stroke-width="6"/><ellipse cx="190" cy="40" rx="48" ry="16" fill="#D9CFC4"/>'
            '<path d="M340 120 q40 10 30 70 q-6 40 20 70 l-30 10 q-26 -40 -20 -80 q6 -40 0 -60Z" fill="#fff" stroke="#E5DED6" stroke-width="5"/>'
            '<g fill="#FFC7D4"><path d="M110 140 l8 -8 l8 8 l-8 8Z"/><path d="M182 190 l8 -8 l8 8 l-8 8Z"/><path d="M254 140 l8 -8 l8 8 l-8 8Z"/><path d="M146 240 l8 -8 l8 8 l-8 8Z"/><path d="M218 240 l8 -8 l8 8 l-8 8Z"/></g>')

def mug():  # 커피 머그 + 스틱 봉지
    return ('<g fill="none" stroke="#C9A27C" stroke-width="11" stroke-linecap="round" opacity=".8"><path d="M130 10 q-18 -28 0 -56 q18 -28 0 -56"/><path d="M200 4 q-18 -28 0 -56 q18 -28 0 -56"/></g>'
            '<path d="M60 40 h260 v190 q0 90 -90 90 h-80 q-90 0 -90 -90Z" fill="#FFF7EE" stroke="#E7D3C0" stroke-width="6"/>'
            '<path d="M320 90 q70 0 70 60 q0 60 -70 60" fill="none" stroke="#E7D3C0" stroke-width="22"/>'
            '<ellipse cx="190" cy="42" rx="128" ry="22" fill="#8B5A3C"/><path d="M120 150 q20 -20 40 0 q20 20 40 0 q20 -20 40 0" fill="none" stroke="#FF9DB5" stroke-width="10" stroke-linecap="round"/>'
            '<g transform="rotate(24 400 30)"><rect x="380" y="-80" width="44" height="210" rx="10" fill="#FFC83A"/><rect x="380" y="-80" width="44" height="40" rx="10" fill="#F39A45"/>'
            '<path d="M392 20 h20 M392 50 h20" stroke="#fff" stroke-width="6" stroke-linecap="round"/></g>')

def wipes():  # 물티슈 팩
    return ('<rect x="30" y="60" width="360" height="230" rx="60" fill="#CDEBFF" stroke="#9CCBF2" stroke-width="6"/>'
            '<rect x="130" y="40" width="160" height="70" rx="30" fill="#7FC1F5"/><rect x="150" y="56" width="120" height="38" rx="18" fill="#fff" opacity=".8"/>'
            '<path d="M170 60 q40 -70 90 -20 q-30 0 -50 30Z" fill="#fff" stroke="#E5EEF5" stroke-width="4"/>'
            '<g fill="#fff"><circle cx="110" cy="200" r="14"/><circle cx="210" cy="230" r="10"/><circle cx="310" cy="200" r="14"/></g>'
            '<path d="M150 180 q60 40 120 0" stroke="#fff" stroke-width="12" fill="none" stroke-linecap="round"/>')

def eggs():  # 계란 판
    egg = lambda x, y, r=0: f'<ellipse cx="{x}" cy="{y}" rx="46" ry="58" fill="#FFF3DF" stroke="#EADBC4" stroke-width="5" transform="rotate({r} {x} {y})"/>'
    return ('<path d="M10 200 h400 l-30 110 h-340Z" fill="#E9D3B5"/><g fill="#DCC29E">' + ''.join(f'<ellipse cx="{70+i*92}" cy="214" rx="38" ry="14"/>' for i in range(4)) + '</g>'
            + egg(70, 150, -8) + egg(162, 140, 4) + egg(254, 148, -4) + egg(346, 142, 8) +
            '<ellipse cx="162" cy="140" rx="20" ry="10" fill="#fff" opacity=".7" transform="rotate(-30 150 120)"/>'
            '<path d="M200 60 q30 -40 60 0" fill="none" stroke="#FFB3C6" stroke-width="10" stroke-linecap="round"/>')

def rice():  # 쌀 포대 + 밥그릇
    return ('<path d="M60 40 q130 -40 260 0 l30 280 q-160 40 -320 0Z" fill="#FFF8E8" stroke="#E7D7B8" stroke-width="6"/>'
            '<path d="M70 40 q120 30 240 0" fill="none" stroke="#C9A27C" stroke-width="10"/><rect x="110" y="120" width="160" height="110" rx="20" fill="#7CC37E"/>'
            '<text x="190" y="200" text-anchor="middle" font-family="PX" font-weight="800" font-size="64" fill="#fff">쌀</text>'
            '<path d="M300 250 q0 80 80 80 q80 0 80 -80Z" fill="#fff" stroke="#E7D7B8" stroke-width="6"/><ellipse cx="380" cy="240" rx="80" ry="34" fill="#fff" stroke="#EEE6D6" stroke-width="6"/>'
            '<g fill="#F2EBDD"><ellipse cx="350" cy="232" rx="10" ry="6"/><ellipse cx="384" cy="224" rx="10" ry="6"/><ellipse cx="410" cy="238" rx="10" ry="6"/></g>')

def milk():  # 우유팩
    return ('<path d="M100 60 l60 -70 h140 l60 70 v270 q0 20 -20 20 h-220 q-20 0 -20 -20Z" fill="#fff" stroke="#BFDDF5" stroke-width="6"/>'
            '<path d="M100 60 h260" stroke="#BFDDF5" stroke-width="6"/><path d="M160 -10 l40 70 M300 -10 l-40 70" stroke="#BFDDF5" stroke-width="5"/>'
            '<rect x="100" y="140" width="260" height="120" fill="#6FB4F0"/><text x="230" y="222" text-anchor="middle" font-family="PX" font-weight="800" font-size="62" fill="#fff">우유</text>'
            '<g fill="#fff"><circle cx="140" cy="300" r="10"/><circle cx="320" cy="300" r="10"/></g>')

def bubble(x, y, w, lines, tail="left"):
    h = 70 + 74 * len(lines)
    tx = x + (70 if tail == "left" else w - 110)
    t = ''.join(f'<text x="{x + w/2}" y="{y + 90 + 74*i}" text-anchor="middle" font-family="PX" font-weight="800" font-size="60" fill="#33302F">{l}</text>' for i, l in enumerate(lines))
    return (f'<g filter="url(#sh)"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="56" fill="#fff"/>'
            f'<path d="M{tx} {y+h-4} l{40 if tail=="left" else 0} 0 l{-30 if tail=="left" else 30} 56Z" fill="#fff"/></g>' + t)

BGS = {"warm": ("#FFF3CF", "#FFDCCB"), "lilac": ("#EEE8FF", "#FFE2EC"), "mint": ("#E3F8EE", "#E6F0FF"), "peach": ("#FFE9DD", "#FFF6CF")}
def sticker(key, who, prop, lines, bg):
    a, b = BGS[bg]
    pet = DOG if who == "dog" else CAT
    return (f'<section id="{key}"><svg viewBox="0 0 1080 1080" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="g{key}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>'
            '<filter id="sh" x="-10%" y="-10%" width="120%" height="140%"><feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#000" flood-opacity=".08"/></filter></defs>'
            f'<rect width="1080" height="1080" fill="url(#g{key})"/>'
            f'<g transform="scale(2.1)">{sparkle(36, 250, 14)}{sparkle(480, 240, 12)}{heart(240, 236, 1.1)}{paw(40, 482, 1.0, "#F3C9A8", .55)}</g>'
            + bubble(90, 80, 900, lines) +
            f'<g transform="translate(-40 360) scale(1.4)">{pet}</g>'
            f'<g transform="translate(620 570) scale(1.0)">{prop()}</g>'
            '<g transform="translate(860 1000)"><rect x="-10" y="-40" width="200" height="56" rx="28" fill="#fff" opacity=".85"/>'
            '<rect x="2" y="-32" width="40" height="40" rx="11" fill="#F0384A"/><text x="22" y="-3" text-anchor="middle" font-family="PX" font-weight="800" font-size="24" fill="#fff">딜</text>'
            '<text x="110" y="-1" text-anchor="middle" font-family="PX" font-weight="800" font-size="30" fill="#33302F">핫딜픽</text></g></svg></section>')

# (키, 캐릭터, 소품, 말풍선 줄, 배경) — 가격 숫자 없음(날마다 다시 씀) · 효능·최저가 X
ITEMS = [
    ("ramen", "dog", bowl, ["라면은 몇 개 있어야", "마음이 편한가멍? 🍜"], "warm"),
    ("water", "cat", bottle, ["물은 1L당으로", "비교해 왔다냥 💧"], "mint"),
    ("toilet-paper", "dog", roll, ["마지막 한 롤 전에", "미리 물어왔멍 🧻"], "peach"),
    ("coffee-mix", "cat", mug, ["쌀쌀해지면", "커피 한 잔 하자냥 ☕"], "lilac"),
    ("wet-wipes", "dog", wipes, ["물티슈는 팩당으로", "보는 거다멍 ✨"], "mint"),
    ("eggs", "cat", eggs, ["계란은 개당", "얼마일까냥? 🥚"], "warm"),
    ("rice", "dog", rice, ["햅쌀 철이다멍!", "1kg당으로 보자 🍚"], "peach"),
    ("milk", "cat", milk, ["우유는 100ml당", "비교했다냥 🥛"], "lilac"),
]
body = ''.join(sticker(*x) for x in ITEMS)
open(sys.argv[1], 'w').write(f'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:PX;src:url({F}Pretendard-ExtraBold.otf);font-weight:800}}
*{{margin:0}}body{{font-family:PX,'Noto Color Emoji'}}section{{width:1080px;height:1080px}}svg{{width:1080px;height:1080px;display:block}}text{{font-family:PX,'Noto Color Emoji'}}
</style></head><body>{body}</body></html>''')
print(len(ITEMS), "stickers")
