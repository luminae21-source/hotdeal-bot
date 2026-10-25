#!/usr/bin/env python3
"""오늘의 딜 카드 이미지(1080x1350 PNG) + 인스타 릴스 영상(1080x1920 MP4). Pillow 필요 (워크플로에서 설치)."""
import os, re
from PIL import Image, ImageDraw, ImageFont
from build_site import parse, CARD_N  # 제목 -> (몰, 이름, 가격): 사이트 격자와 같이 씀 · 카드 딜 수(캡션·사이트 번호와 같게)

W, H = 1080, 1350
FONTS = {  # 러너: fonts/ (워크플로가 Google Fonts 저장소에서 내려받음) / 로컬: Noto CJK
    "bold": ["fonts/NanumGothic-ExtraBold.ttf", "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"],
    "reg": ["fonts/NanumGothic-Regular.ttf", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"],
}


def font(kind, size):
    for p in FONTS[kind]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    raise FileNotFoundError("한글 폰트 없음: " + ", ".join(FONTS[kind]))


def wrap(d, text, f, width, max_lines=2):
    """띄어쓰기 단위로 줄바꿈('48팩'이 '4/8팩'으로 안 갈리게). 한 단어가 한 줄보다 길 때만 글자 단위. 넘치면 마지막 줄 …"""
    lines, cur = [], ""
    for word in re.findall(r"\S+\s*", text):
        for piece in ([word] if d.textlength(word.rstrip(), font=f) <= width else list(word)):
            if cur and d.textlength((cur + piece).rstrip(), font=f) > width:
                lines.append(cur.rstrip())
                cur = piece.lstrip()
                if len(lines) == max_lines:
                    lines[-1] = lines[-1][:-1] + "…"
                    return lines
            else:
                cur += piece
    return lines + ([cur.rstrip()] if cur.strip() else [])


def make(items, date_label, out, head="오늘 살 만한 딜", label="오늘의 가성비 딜", png=True, theme=None):
    """오늘의 딜 카드(1080x1350, 릴스와 같은 크림·먹색·숫자 포인트색 디자인). items: 딜 제목 문자열 또는 {"title", "unit"} (최대 CARD_N개). -> out
    시간대 카드(인스타 하루 3번, 10/11~)는 head·label만 다르고 png=False(인스타는 JPEG만 — 사이트 카드 칸은 하루 카드 .png만 봄).
    theme = 인스타 카드 변주(10/22 진우 '같은 템플릿 반복 X'): {"bg": 바탕색, "accent": 포인트색, "band": 머리 칸을 포인트색 띠로(글자 흰색)} — 없으면 기본."""
    th = theme or {}
    bg, accent = tuple(th.get("bg") or CREAM), tuple(th.get("accent") or ACCENT)
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    top, ink, sub = (accent, (255, 255, 255), (255, 255, 255)) if th.get("band") else (None, INK2, SUB)
    if top:
        d.rectangle((0, 0, W, 270), fill=top)
    d.text((X0, 84), f"{date_label}  ·  {label}", font=pf("SemiBold", 34), fill=sub)
    f = pf("Bold", 34); d.text((W - X0 - d.textlength("핫딜픽", font=f), 84), "핫딜픽", font=f, fill=ink if top else accent)
    d.text((X0, 136), head, font=pf("ExtraBold", 76), fill=ink)
    d.rectangle((X0, 262, W - X0, 264), fill=top or LINE)
    ACC = accent
    y = 292
    for n, it in enumerate([{"title": i} if isinstance(i, str) else i for i in items][:CARD_N], 1):
        store, name, price = parse(it["title"])
        d.text((X0, y), f"{n:02d}", font=pf("ExtraBold", 34), fill=ACC)
        if store:
            d.text((X0 + 68, y + 4), store, font=pf("SemiBold", 28), fill=SUB)
        d.text((X0, y + 44), wrap(d, name, pf("Bold", 40), W - 2 * X0, 1)[0] if name else "", font=pf("Bold", 40), fill=INK2)
        if price:
            main, _, ship = price.partition("/")
            fp = pf("ExtraBold", 44)
            d.text((X0, y + 100), main.strip(), font=fp, fill=INK2)
            x = X0 + d.textlength(main.strip(), font=fp) + 18
            fs, unit = pf("SemiBold", 30), (it.get("unit") or "").strip()
            ship = "무료배송" if ship.strip() in ("무료", "무배", "무료배송") else ship.strip()
            if unit:  # 단위가격은 포인트색, 배송은 회색
                d.text((x, y + 112), unit, font=fs, fill=ACC)
                x += d.textlength(unit + "  ", font=fs)
            if ship:
                d.text((x, y + 112), ("·  " if unit else "") + ship, font=fs, fill=SUB)
        y += 170
        if n < min(len(items), CARD_N):
            d.rectangle((X0, y - 14, W - X0, y - 13), fill=LINE)
    d.rectangle((X0, H - 200, W - X0, H - 198), fill=LINE)
    d.text((X0, H - 170), "전체 딜 · 구매 링크", font=pf("SemiBold", 32), fill=INK2)
    f = pf("Bold", 40); d.text((W - X0 - d.textlength("hotdealpick.kr", font=f), H - 176), "hotdealpick.kr", font=f, fill=ACC)
    d.text((X0, H - 112), "실시간 알림 t.me/hotdeal_pick  ·  블로그 blog.naver.com/hotdeal_pick", font=pf("Regular", 26), fill=SUB)
    d.text((X0, H - 66), "일부 링크는 제휴 링크로, 구매 시 수수료를 받을 수 있어요. 가격·재고는 게시 시점 기준.", font=pf("Regular", 22), fill=SUB)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    if png:
        im.save(out, optimize=True)
    im.save(os.path.splitext(out)[0] + ".jpg", quality=92)  # 인스타 API는 JPEG만 받음 -> 같은 카드를 .jpg로도(사이트에 같이 공개)
    return out


RW, RH, FPS = 1080, 1920, 30  # 릴스 세로 영상


def ffmpeg():
    """ffmpeg 경로. GitHub 러너엔 기본 설치가 없어서 imageio-ffmpeg 휠(정적 빌드)에서 꺼내 씀 (sudo·pip 설치 불필요)."""
    import glob, shutil, subprocess, sys, tempfile, zipfile
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    d = os.path.join(tempfile.gettempdir(), "ffwheel")
    if not glob.glob(f"{d}/imageio_ffmpeg-*.whl"):
        subprocess.run([sys.executable, "-m", "pip", "download", "-q", "--no-deps", "--only-binary=:all:", "-d", d, "imageio-ffmpeg"], check=True)
    whl = zipfile.ZipFile(glob.glob(f"{d}/imageio_ffmpeg-*.whl")[0])
    exe = whl.extract(next(n for n in whl.namelist() if "/binaries/ffmpeg" in n), d)
    os.chmod(exe, 0o755)
    return exe


EMOJI_URL = "https://raw.githubusercontent.com/googlefonts/noto-emoji/v2.047/fonts/NotoColorEmoji.ttf"  # 비트맵(CBDT)판, OFL


def emoji(ch, size):
    """컬러 이모지 -> RGBA 이미지(size x size 안에 맞춤). 폰트가 fonts/에 없으면 1회 내려받음(워크플로 캐시에 같이 남음). 못 그리면 🛒"""
    path = next((p for p in ["fonts/NotoColorEmoji.ttf", "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"] if os.path.exists(p)), None)
    if not path:
        import urllib.request
        os.makedirs("fonts", exist_ok=True)
        urllib.request.urlretrieve(EMOJI_URL, "fonts/NotoColorEmoji.ttf")
        path = "fonts/NotoColorEmoji.ttf"
    f = ImageFont.truetype(path, 109)  # CBDT는 109px 고정 -> 그린 뒤 크기 조절
    for c in (ch or "", "🛒"):
        im = Image.new("RGBA", (300, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((10, 10), c[:2], font=f, embedded_color=True)
        box = im.getbbox()
        if box and box[2] - box[0] > 40:
            im = im.crop(box)
            k = size / max(im.width, im.height)
            return im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    raise ValueError("이모지 렌더 실패")


PRETENDARD = "https://raw.githubusercontent.com/orioncactus/pretendard/v1.3.9/packages/pretendard/dist/public/static/Pretendard-{}.otf"
CREAM, INK2, SUB, LINE, ACCENT, NIGHT = (246, 244, 239), (22, 24, 29), (128, 133, 142), (224, 220, 212), (255, 84, 28), (22, 24, 29)
X0, XW = 96, 888  # 왼쪽 여백·글자 폭 (한 줄 기준선에 맞춘 정돈된 배치)


def pf(weight, size):
    """프리텐다드(OFL) 글꼴. fonts/에 없으면 1회 내려받음(워크플로 캐시에 남음), 못 받으면 나눔고딕."""
    path = f"fonts/Pretendard-{weight}.otf"
    if not os.path.exists(path):
        try:
            import urllib.request
            os.makedirs("fonts", exist_ok=True)
            urllib.request.urlretrieve(PRETENDARD.format(weight), path + ".part")
            os.replace(path + ".part", path)
        except Exception:
            return font("reg" if weight in ("Regular", "Medium") else "bold", size)
    return ImageFont.truetype(path, size)


def _text(s, f, fill):
    """글자 한 줄 -> 딱 맞는 RGBA 이미지"""
    im = Image.new("RGBA", (int(f.getlength(s)) + 8, int(f.size * 1.3)), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((0, 0), s, font=f, fill=fill)
    return im


def _rich(s, f, width, lines=1, fill=INK2, lh=1.18, accent=True):
    """숫자 들어간 단어만 포인트 색(예: '팩당 약 495원'의 495원). 넘치면 줄바꿈·…"""
    rows = wrap(ImageDraw.Draw(Image.new("RGB", (1, 1))), s, f, width, lines)
    step = int(f.size * lh)
    im = Image.new("RGBA", (width + 10, step * len(rows) + int(f.size * 0.3)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for k, row in enumerate(rows):
        x = 0
        for tok in re.findall(r"\S+\s*", row):
            d.text((x, k * step), tok, font=f, fill=ACCENT if accent and re.search(r"\d", tok) else fill)
            x += d.textlength(tok, font=f)
    return im


def _tile(e, size):
    """흰 둥근 타일 + 부드러운 그림자 + 이모지 (그림자 여백 40px 포함)"""
    from PIL import ImageFilter
    pad = 40
    im = Image.new("RGBA", (size + pad * 2, size + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 12, pad + size, pad + size + 12), radius=size // 4, fill=(60, 40, 20, 46))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(20)))
    ImageDraw.Draw(im).rounded_rectangle((pad, pad, pad + size, pad + size), radius=size // 4, fill="white")
    em = emoji(e, int(size * 0.6))
    im.alpha_composite(em, (pad + (size - em.width) // 2, pad + (size - em.height) // 2))
    return im


def _check(s):
    """얇은 포인트색 체크 + 이유 한 줄"""
    f = pf("Medium", 50)
    row = _rich(s, f, 790)
    im = Image.new("RGBA", (XW, max(70, row.height)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 12, 48, 60), outline=ACCENT, width=4)
    d.line([(12, 36), (21, 46), (37, 26)], fill=ACCENT, width=5, joint="curve")
    im.alpha_composite(row, (78, 2))
    return im


def _pill(s):
    f = pf("SemiBold", 36)
    w = int(f.getlength(s)) + 48
    im = Image.new("RGBA", (w, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, 63), radius=32, outline=SUB, width=3)
    d.text((24, 10), s, font=f, fill=SUB)
    return im


def _ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def _in(frame, img, x, y, t, delay=0.0, dur=0.45, rise=26):
    """왼쪽 위 기준으로 놓기 + delay초 뒤 은은하게 떠오르며 나타남"""
    k = _ease((t - delay) / dur)
    if k <= 0:
        return
    if k < 1:
        img = img.copy()
        img.putalpha(img.getchannel("A").point(lambda a: int(a * k)))
    frame.paste(img, (int(x), int(y + rise * (1 - k))), img)


def _rule(frame, y, t, delay, color=LINE):
    """왼쪽부터 그어지는 얇은 구분선"""
    k = _ease((t - delay) / 0.5)
    if k > 0:
        ImageDraw.Draw(frame).rectangle((X0, y, X0 + XW * k, y + 2), fill=color)


def _norm(it):
    """딜 재료 정리(릴스·딜 카드 같이): 제목 -> 몰·이름·가격·배송, 단위가격·확인할 점, 이유 2~3개(없으면 코멘트 문장 — 배송·단위가격과 같은 건 따로 표시라 뺌)."""
    it = dict(it)
    store, name, price = parse(it["title"])
    main, _, ship = price.partition("/")
    ship = "무료배송" if ship.strip() in ("무료", "무배", "무료배송") else ship.strip()
    ship = "배송비 " + ship if re.fullmatch(r"[\d,]+원", ship) else ship  # '3,000원'만 있으면 가격처럼 보임
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", it.get("comment") or "") if s.strip() and not s.lstrip().startswith(("💡", "⚠", "🤔"))]
    unit, warn = (it.get("unit") or "").strip(), (it.get("warn") or "").strip()
    it.update(store=store, name=name, main=main.strip(), ship=ship, unit=unit, warn=warn,
              pts=[p for p in (it.get("pts") or sents) if p.replace(" ", "") not in (ship.replace(" ", ""), unit.replace(" ", ""))][:3 - bool(warn)])
    return it


def deal_card(it, n, total, out, why="살 만한 이유"):
    """딜 한 장 카드(인스타 넘기기 2~6장째, 10/11 진우 '인스타 업그레이드 2번'): 1080x1350 JPEG, 릴스 딜 장면과 같은 디자인(움직임 없이).
    번호(= 표지·캡션·사이트 번호)·몰·이모지·이름·가격·배송·단위가격·이유·확인할 점 + 아래 사이트·번호/전체·제휴 안내.
    it: {"title", "comment", "e", "pts", "unit", "warn"}. why: 이유 제목(올리브영은 '체크 포인트' — 큐레이터 정책상 권유 문구 X). -> out"""
    it = _norm(it)
    im = Image.new("RGBA", (W, H), CREAM + (255,))
    d = ImageDraw.Draw(im)
    d.text((X0, 84), f"{n:02d}", font=pf("ExtraBold", 48), fill=ACCENT)
    if it["store"]:
        d.text((X0 + 96, 90), it["store"], font=pf("SemiBold", 40), fill=SUB)
    f = pf("Bold", 34); d.text((W - X0 - d.textlength("핫딜픽", font=f), 92), "핫딜픽", font=f, fill=ACCENT)
    tile = _tile(it.get("e"), 190)
    im.alpha_composite(tile, (X0 - 40, 150))
    y = 150 + tile.height - 30
    if it["name"]:
        nm = _rich(it["name"], pf("Bold", 60), XW, 2, fill=INK2, lh=1.22, accent=False)
        im.alpha_composite(nm, (X0, y)); y += nm.height + 6
    pill = _pill(it["ship"]) if it["ship"] else None
    if it["main"]:
        side = pill.width + 20 if pill else 0  # 배송 알약을 가격 오른쪽에 둘 자리
        size = next((z for z in (120, 104, 92) if pf("ExtraBold", z).getlength(it["main"]) + 8 + side <= XW), None)
        if size is None:  # '티멤 카카오 23,470원'처럼 앞말 붙은 가격: 가격만 한 줄에 맞추고 알약은 아랫줄(그래도 길면 2줄)
            size, side = next((z for z in (92, 80, 68) if pf("ExtraBold", z).getlength(it["main"]) + 8 <= XW), None), 0
        pr = _text(it["main"], pf("ExtraBold", size), INK2) if size else _rich(it["main"], pf("ExtraBold", 68), XW, 2, fill=INK2, accent=False)
        im.alpha_composite(pr, (X0, y))
        if pill and side:  # 가격 오른쪽, 글자 아래쪽에 맞춤
            im.alpha_composite(pill, (X0 + pr.width + 20, y + pr.height - pill.height - 20))
        y += pr.height + 4
        if pill and not side:
            im.alpha_composite(pill, (X0, y)); y += 84
    elif pill:
        im.alpha_composite(pill, (X0, y)); y += 84
    if it["unit"]:
        u = _rich(it["unit"], pf("SemiBold", 46), XW); im.alpha_composite(u, (X0, y - 6)); y += 70
    if it["pts"] or it["warn"]:
        d.rectangle((X0, y + 10, X0 + XW, y + 12), fill=LINE)
        d.text((X0, y + 34), why, font=pf("SemiBold", 36), fill=SUB)
        y += 96
        for p in it["pts"]:
            im.alpha_composite(_check(p), (X0, y)); y += 80
        if it["warn"]:  # 단점·조건까지(광고 계정과의 차이)
            d.text((X0, y + 8), "확인할 점", font=pf("SemiBold", 36), fill=SUB)
            d.text((X0 + 180, y + 4), wrap(d, it["warn"], pf("Medium", 40), XW - 180, 1)[0], font=pf("Medium", 40), fill=INK2)
    d.rectangle((X0, H - 150, W - X0, H - 148), fill=LINE)
    d.text((X0, H - 124), "hotdealpick.kr", font=pf("Bold", 40), fill=ACCENT)
    s = f"{n:02d} / {total:02d}"; f = pf("SemiBold", 36); d.text((W - X0 - d.textlength(s, font=f), H - 120), s, font=f, fill=SUB)
    d.text((X0, H - 62), "프로필 링크 → 맨 위 카드 번호로 구매 · 일부 링크는 제휴 링크(수수료)", font=pf("Regular", 26), fill=SUB)
    im.convert("RGB").save(out, quality=85)
    return out


LEAD, TAIL, XF, KB, DUCK = 0.3, 0.25, 9, 0.06, 0.251  # 나레이션 앞뒤 여백(초) · 장 사이 크로스페이드 9프레임(0.3초) · 켄번스 줌 6% · 나레이션 동안 음악 -12dB
SUB_Y = RH - 430  # 자막 아래 끝(인스타 아래 UI ~420px 위 — 안전 영역)


def reel_plan(segs, n):
    """장면 길이(초) = 표지·딜 n개·끝 3초씩(10/24 Cowork 대본 틀 0~3·3~12·12~15초 — 딜이 적어도 15초), 나레이션 있으면 그 장 = 앞 여백 + 나레이션 + 뒤 여백.
    segs = 장마다 나레이션 초(없으면 None). -> [초…] (합이 20초 넘으면 부르는 쪽이 더 빠르게 다시 읽힘·안 되면 나레이션 X)"""
    durs = [max(3.0, LEAD + s + TAIL) if s else 3.0 for s in (segs or [None] * (n + 2))]
    return [d * 15 / sum(durs) for d in durs] if sum(durs) < 15 else durs


def duck_expr(wins, r=0.15):
    """음악 볼륨 식(ffmpeg volume eval=frame): 나레이션 구간(wins = [(시작, 끝)…])만 -12dB, 앞뒤 r초 부드럽게."""
    w = [f"clip(min((t-{a - r:.3f})/{r},({b + r:.3f}-t)/{r}),0,1)" for a, b in wins]
    while len(w) > 1:
        w = [f"max({w[0]},{w[1]})"] + w[2:]
    return f"1-{1 - DUCK:.3f}*{w[0]}" if w else "1"


def _sub(s):
    """자막(나레이션 글자): 어두운 둥근 띠 + 흰 글자 최대 2줄, 가운데."""
    f = pf("SemiBold", 46)
    rows = wrap(ImageDraw.Draw(Image.new("RGB", (1, 1))), s, f, 820, 2)
    w = int(max(f.getlength(r) for r in rows)) + 64
    im = Image.new("RGBA", (w, 58 * len(rows) + 34), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, im.height - 1), radius=26, fill=(22, 24, 29, 214))
    for k, r in enumerate(rows):
        d.text(((w - f.getlength(r)) / 2, 14 + 58 * k), r, font=f, fill="white")
    return im


def _wav(b):
    """WAV bytes -> (16bit PCM 프레임, 샘플레이트, 채널, 초)"""
    import io, wave
    with wave.open(io.BytesIO(b)) as w:
        if w.getsampwidth() != 2:
            raise ValueError("16bit WAV만")
        fr = w.readframes(w.getnframes())
        return fr, w.getframerate(), w.getnchannels(), w.getnframes() / w.getframerate()


def reel(items, date_label, out, music=None, say=None):
    """깔끔·세련되게, 그러면서 '사고 싶고 합리적인 소비'로 느껴지게: 1080x1920 MP4(15~20초). -> out
    items: [{"title", "comment", "e": 이모지, "hook": 첫 화면 한 줄, "pts": 합리적인 이유 2~3개}] 최대 3개 (e·hook·pts 없으면 제목·코멘트로 대신)
    music(음악 파일): 배경음악(짧으면 반복·앞뒤 페이드) · say(10/24 Cowork·진우 릴스 업그레이드): [(자막, WAV bytes)] 표지·딜·끝 장마다 나레이션
    -> 그 장은 나레이션 길이에 맞추고(합 15~20초) 아래 안전 영역에 자막, 나레이션 동안 음악 -12dB(덕킹). 없거나 20초 넘으면 글자 + 음악만(15초).
    디자인: 크림색 바탕 + 먹색 글자 + 포인트색은 숫자에만, 왼쪽 정렬 한 기준선, 프리텐다드, 흰 타일 위 이모지,
    장마다 켄번스(1.00→1.06 줌인·줌아웃 번갈아 — 소수점 확대라 글자 안 떨림) + 장 사이 0.3초 크로스페이드, 가격은 이름보다 0.2초 늦게 떠오름.
    첫 장 위 작게 '광고·제휴'. 마지막은 어두운 바탕에 저장·공유 유도. 글자는 인스타 UI가 덮는 위(~250px)·아래(~420px)를 피해서 배치."""
    import subprocess, tempfile, wave
    items = [_norm(it) for it in items[:3]]
    for it in items:
        it["hook"] = it.get("hook") or f"{it['name'][:12]} {it['main']}".strip()
    n_sc = len(items) + 2
    try:
        say = [(s, _wav(b)) for s, b in say] if say and len(say) == n_sc and all(b for _, b in say) else None
        if say and len({(w[1], w[2]) for _, w in say}) > 1:
            raise ValueError("나레이션 형식이 장마다 다름")
    except Exception as e:  # 깨진 음성 = 글자 + 음악만
        print("reel narration", repr(e))
        say = None
    durs = reel_plan([w[3] for _, w in say] if say else None, len(items))
    if say and sum(durs) > 20.05:
        print("reel narration 20초 넘음", round(sum(durs), 1))
        say, durs = None, reel_plan(None, len(items))
    low = SUB_Y - 58 * 2 - 34 - 26 if say else RH - 450  # 장 내용 아래 끝(자막 띠 위)
    cream, night = Image.new("RGB", (RW, RH), CREAM), Image.new("RGB", (RW, RH), NIGHT)
    scenes = []  # (배경, 그리기(frame, t), 진행 막대 색)

    top = items[0] if items else {"hook": "오늘의 핫딜", "e": "🛒"}
    i_lab = _text(f"{date_label}  ·  오늘의 가성비 1위", pf("SemiBold", 40), SUB)
    i_tile = _tile(top.get("e"), 260)
    hf = 132
    while hf > 70 and len(wrap(ImageDraw.Draw(Image.new("RGB", (1, 1))), top["hook"], pf("ExtraBold", hf), XW, 3)) > 2:
        hf -= 8
    i_hook = _rich(top["hook"], pf("ExtraBold", hf), XW, 2, lh=1.12)
    i_next = _text(f"오늘 살 만한 딜 {len(items)}가지  →", pf("SemiBold", 46), INK2)

    def intro(fr, t):
        _in(fr, i_lab, X0, 300, t, 0.0)
        _in(fr, i_tile, X0 - 40, 360, t, 0.05)
        _in(fr, i_hook, X0, 720, t, 0.18)
        y = 720 + i_hook.height + 50
        _rule(fr, y, t, 0.45)
        _in(fr, i_next, X0, y + 44, t, 0.6)
    scenes.append((cream, intro, INK2))

    for n, it in enumerate(items, 1):
        lab = Image.new("RGBA", (XW, 70), (0, 0, 0, 0))
        d = ImageDraw.Draw(lab)
        d.text((0, 0), f"{n:02d}", font=pf("ExtraBold", 48), fill=ACCENT)
        if it["store"]:
            d.text((96, 6), it["store"], font=pf("SemiBold", 40), fill=SUB)
        tile = _tile(it.get("e"), 250)
        name = _rich(it["name"], pf("Bold", 66), XW, 2, fill=INK2, lh=1.25, accent=False)
        name = Image.new("RGBA", name.size, (0, 0, 0, 0)) if not it["name"] else name
        price = _text(it["main"], pf("ExtraBold", 140 if pf("ExtraBold", 140).getlength(it["main"]) < XW - 260 else 108), INK2) if it["main"] else None
        pill = _pill(it["ship"]) if it["ship"] else None
        unit = _rich(it["unit"], pf("SemiBold", 50), XW) if it["unit"] else None
        warn = None
        if it["warn"]:  # 단점·조건까지 말해주는 게 광고 계정과의 차이
            warn = Image.new("RGBA", (XW, 70), (0, 0, 0, 0))
            ImageDraw.Draw(warn).text((0, 8), "확인할 점", font=pf("SemiBold", 40), fill=SUB)
            ImageDraw.Draw(warn).text((200, 4), it["warn"], font=pf("Medium", 44), fill=INK2)
        why = _text("살 만한 이유", pf("SemiBold", 38), SUB)
        checks = [_check(p) for p in it["pts"]]

        def deal(fr, t, lab=lab, tile=tile, name=name, price=price, pill=pill, why=why, checks=checks, unit=unit, warn=warn):
            _in(fr, lab, X0, 300, t, 0.05)
            _in(fr, tile, X0 - 40, 362, t, 0.1)
            y = 700
            _in(fr, name, X0, y, t, 0.18)
            y += name.height + 8
            if price:
                _in(fr, price, X0, y, t, 0.38)  # 가격 = 이름보다 0.2초 늦게(10/24 Cowork)
                if pill:  # 가격 오른쪽, 글자 아래쪽에 맞춤
                    _in(fr, pill, X0 + price.width + 20, y + price.height - pill.height - 22, t, 0.48)
                y += price.height + 10
            elif pill:
                _in(fr, pill, X0, y, t, 0.48)
                y += 90
            if unit:  # 비교 근거: 단위가격
                _in(fr, unit, X0, y - 14, t, 0.52)
                y += 80
            rows = ([warn] if warn else []) + checks if low < RH - 450 else checks + ([warn] if warn else [])  # 자리가 좁으면(자막) 확인할 점(가격 조건) 먼저
            hd = 104 if y + 104 + 70 <= low else 36  # 한 줄도 안 들어가면 '살 만한 이유' 머리 없이
            k = 0
            while k < len(rows) and y + hd + 84 * k + 70 <= low:  # 자막 띠와 안 겹치게
                k += 1
            if k:
                _rule(fr, y, t, 0.56)
                if hd == 104:
                    _in(fr, why, X0, y + 36, t, 0.62)
                for j, c in enumerate(rows[:k]):
                    _in(fr, c, X0, y + hd + 84 * j + (6 if c is warn else 0), t, 0.72 + 0.15 * j)
        scenes.append((cream, deal, INK2))

    light, dim = (172, 176, 184), (112, 116, 124)
    o = [(_text("저장해두고", pf("Bold", 84), "white"), 500, 0.0), (_text("장보기 전에 꺼내보세요", pf("Bold", 84), "white"), 604, 0.06),
         (_text("필요한 친구에게 보내줘도 좋아요", pf("Medium", 44), light), 740, 0.16),
         (_text("매일 밤 9시  ·  가성비 TOP3", pf("SemiBold", 44), "white"), 920, 0.3),
         (_text("hotdealpick.kr", pf("Bold", 58), ACCENT), 990, 0.36),
         (_text("프로필 링크에서 전체 딜 · 구매 링크", pf("Regular", 40), light), 1075, 0.42),
         (_text("텔레그램 실시간 알림  @hotdeal_pick", pf("Regular", 40), light), 1135, 0.48),
         (_text("일부 링크는 제휴 링크로, 구매 시 수수료를 받을 수 있어요.", pf("Regular", 30), dim), 1210 if say else 1380, 0.55)]

    def outro(fr, t):
        for im, y, dl in o:
            _in(fr, im, X0, y, t, dl)
        _rule(fr, 860, t, 0.24, (58, 61, 68))
    scenes.append((night, outro, "white"))

    ad = _pill("광고·제휴")  # 첫 장 위 작게(대가성 — 캡션 맨 앞 문구와 같이)
    subs = [_sub(s) for s, _ in say] if say else []
    starts = [sum(durs[:k]) for k in range(n_sc)]
    total, seg = sum(durs), (XW - 12 * (n_sc - 1)) / n_sc
    AX, AY = RW / 2, 820  # 켄번스 기준점(글자 덩어리 가운데 — 가장자리 글자가 덜 움직이게)

    def shot(si, t):
        """장면 si의 t초 그림(켄번스까지) — 크로스페이드 때 앞 장면은 t가 길이를 넘어도 그대로 이어 그림."""
        bg, draw, _ = scenes[si]
        fr = bg.copy()
        draw(fr, t)
        k = min(1.0, max(0.0, t / durs[si]))
        z = 1 + KB * (k if si % 2 == 0 else 1 - k)  # 줌인·줌아웃 번갈아
        if z > 1.0005:
            fr = fr.resize((RW, RH), Image.BILINEAR, box=(AX - AX / z, AY - AY / z, AX - AX / z + RW / z, AY - AY / z + RH / z))
        return fr

    tmp = tempfile.mkdtemp()
    cmd = [ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{RW}x{RH}", "-r", str(FPS), "-i", "-"]
    fade = f"afade=t=in:d=0.5,afade=t=out:st={total - 1.5:.3f}:d=1.5"
    if say:  # 나레이션 한 줄(장마다 시작 + LEAD초에) -> WAV
        rate, ch = say[0][1][1], say[0][1][2]
        buf = bytearray(int(total * rate) * 2 * ch)
        for k, (_, (frames, *_x)) in enumerate(say):
            at = int((starts[k] + LEAD) * rate) * 2 * ch
            part = frames[:max(0, len(buf) - at)]
            buf[at:at + len(part)] = part
        nar = os.path.join(tmp, "say.wav")
        with wave.open(nar, "wb") as w:
            w.setnchannels(ch); w.setsampwidth(2); w.setframerate(rate); w.writeframes(bytes(buf))
        wins = [(starts[k] + LEAD, starts[k] + LEAD + w[3]) for k, (_, w) in enumerate(say)]
        if music:
            cmd += ["-stream_loop", "-1", "-i", music, "-i", nar, "-filter_complex",
                    f"[1:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,aresample=48000,volume=0.8,volume='{duck_expr(wins)}':eval=frame,{fade}[m];"
                    f"[2:a]aresample=48000,volume=1.6[v];[m][v]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89:level=0[a]", "-map", "0:v", "-map", "[a]"]
        else:
            cmd += ["-i", nar, "-map", "0:v", "-map", "1:a", "-af", "aresample=48000,volume=1.6,alimiter=limit=0.89:level=0"]
        cmd += ["-c:a", "aac", "-b:a", "128k"]
    elif music:
        cmd += ["-stream_loop", "-1", "-i", music, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "128k", "-af", fade]
    cmd += ["-t", f"{total:.3f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "veryfast", "-movflags", "+faststart", "-use_editlist", "0", out]  # 인스타 릴스 규격: edit list 없음·moov 앞
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for si in range(n_sc):
            frames = round((starts[si] + durs[si]) * FPS) - round(starts[si] * FPS)  # 누적 경계로(장면 컷·나레이션·자막이 같은 시각)
            for i in range(frames):
                t = i / FPS
                frame = shot(si, t)
                if si and i < XF:  # 장 사이 0.3초 크로스페이드(앞 장면은 계속 움직임)
                    frame = Image.blend(shot(si - 1, durs[si - 1] + t), frame, (i + 1) / (XF + 1))
                d = ImageDraw.Draw(frame)  # 위쪽 장면별 진행 막대 (스토리처럼)
                for k in range(n_sc):
                    x = X0 + k * (seg + 12)
                    d.rounded_rectangle((x, 150, x + seg, 155), radius=3, fill=LINE if scenes[si][0] is cream else (58, 61, 68))
                    fill = 1.0 if k < si else (i + 1) / frames if k == si else 0
                    if fill:
                        d.rounded_rectangle((x, 150, x + seg * fill, 155), radius=3, fill=scenes[si][2])
                if si == 0:
                    frame.paste(ad, (RW - X0 - ad.width, 296), ad)
                if say:  # 자막 = 나레이션 하는 동안(앞뒤 0.15초 페이드)
                    a = min(1.0, (t - LEAD + 0.15) / 0.15, (LEAD + say[si][1][3] + 0.2 - t) / 0.15)
                    if a > 0:
                        sb = subs[si] if a >= 1 else subs[si].copy()
                        if a < 1:
                            sb.putalpha(sb.getchannel("A").point(lambda v: int(v * a)))
                        frame.paste(sb, ((RW - sb.width) // 2, SUB_Y - sb.height), sb)
                proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        rc = proc.wait()
    except BaseException:
        proc.kill()
        proc.wait()
        raise
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    if rc:
        raise RuntimeError("ffmpeg 실패")
    return out


if __name__ == "__main__":
    import json, sys, time
    from build_site import title_of
    posts = json.load(open("posts.json")) if os.path.exists("posts.json") else []
    kst = time.gmtime(time.time() + 9 * 3600)
    print(make([title_of(p["text"]) for p in posts], f"{kst.tm_mon}월 {kst.tm_mday}일", sys.argv[1] if len(sys.argv) > 1 else "card.png"))


# ── 인스타 카드 새 디자인(10/22 22:3x 진우 '디자인 업그레이드' — 시안 A·B 번갈아, 인스타만: 텔레그램·Threads·사이트 카드는 위 make·deal_card 그대로) ──
# it(상품 1개) = {"name", "short"(칩·타일용 짧은 이름), "price", "chip"(단위가격·'와우 할인'·'47%↓'), "badge"('🚀 쿠팡 로켓'·'💙 토스 특가'·'네이버' — 채널 머리 줄 규칙),
#                 "ship"('내일 도착'·'무료배송'), "photo"(몰 상품 이미지 경로, 없으면 None -> 상품 종류 글자 칸), "e"(이모지), "kind"(상품 종류 낱말), "line"(한 줄 멘트), "when"('10/22 21시')}
NAVY, NAVY2, PINK, PINK2, MIST = (29, 39, 64), (43, 55, 87), (255, 111, 163), (255, 143, 184), (201, 209, 224)
INKA, SUBA, PLUM, PAPER, BROWN, INKB, BERRY, MARK, STICKER = (31, 26, 46), (74, 64, 96), (45, 36, 64), (255, 241, 244), (74, 63, 48), (26, 26, 26), (176, 18, 79), (255, 194, 214), (255, 143, 179)
LMIST, CHIPBG, LAV, BLUSH = (247, 243, 255), (255, 227, 238), (236, 230, 255), (255, 230, 239)  # LAV·BLUSH = 파스텔 표지(design P, 540ba9f69 — 10/23 진우 '이것도 좋다')
ATILES = [(255, 227, 238), (255, 230, 217), (223, 245, 236), (232, 228, 255)]  # 10/22 진우 A 최종 '남색 쪽이 시인성이 더 좋다' = 혼합: 표지 남색 + 핑크 강조·흰 제목(칩 가격만 더 밝은 핑크 PINK2, 칩 위 5:1↑), 상품 장 파스텔(라벤더 안개·종류 칸 핑크·피치·민트·라벤더 번갈아·자두 먹색 글자·진한 자두 알약)
TILES, SHADOW, EDGE = [(239, 230, 255), (255, 230, 217), (255, 227, 238)], (240, 196, 210), (247, 212, 223)  # 10/22 진우 '분홍색 들어가게': A = 남색 + 핑크 강조, B = 블러시 핑크 톤(종류 칸 라벤더·피치·핑크 번갈아) — 흰 글자는 중간 핑크 위 X  # 10/22 진우 '눈에 잘 들어와야': 크림 위 회색 X — 글자는 먹색·진한 갈색, 보조 글자 40px↑


def _hex(c):
    c = {"white": "#ffffff", "black": "#000000"}.get(c, c)
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) if isinstance(c, str) else c


def _fit(f, s, width):
    """한 줄 말줄임(넘치면 …)."""
    if f.getlength(s) <= width:
        return s
    while s and f.getlength(s + "…") > width:
        s = s[:-1]
    return s.rstrip() + "…"


def _em_text(d, im, xy, s, f, fill):
    """'🚀 쿠팡 로켓'처럼 맨 앞 이모지는 컬러 이모지 그림으로, 나머지는 글자로 -> 끝 x."""
    x, y = xy
    m = re.match(r"([^\w\s\[\]()·.,%+-]{1,2})\s*", s)
    if m and not re.match(r"[가-힣A-Za-z0-9]", m[1]):
        try:
            e = emoji(m[1], int(f.size * 1.05))
            im.alpha_composite(e, (int(x), int(y + f.size * 0.12)))
            x, s = x + e.width + int(f.size * 0.3), s[m.end():]
        except Exception:
            pass
    d.text((x, y), s, font=f, fill=fill)
    return x + d.textlength(s, font=f)


def _pill_w(f, s, padx, emo=True):
    m = re.match(r"([^\w\s\[\]()·.,%+-]{1,2})\s*", s) if emo else None
    w = f.getlength(s[m.end():] if m and not re.match(r"[가-힣A-Za-z0-9]", m[1]) else s)
    return int(w + (f.size * 1.35 if m and not re.match(r"[가-힣A-Za-z0-9]", m[1]) else 0) + padx * 2)


def _photo(it, w, h, radius, bg=LMIST, ink=INKA):
    """상품 사진(꽉 차게 잘라 넣음) — 없으면 상품 종류 글자 칸(이모지 + 종류 낱말). 둥근 모서리 RGBA."""
    tile = Image.new("RGBA", (w, h), bg + (255,))
    ph = None
    if it.get("photo"):
        try:
            ph = Image.open(it["photo"]).convert("RGB")
        except Exception:
            ph = None
    if ph:
        k = max(w / ph.width, h / ph.height)
        ph = ph.resize((max(w, int(ph.width * k + 0.5)), max(h, int(ph.height * k + 0.5))), Image.LANCZOS)
        l, t = (ph.width - w) // 2, (ph.height - h) // 2
        tile.paste(ph.crop((l, t, l + w, t + h)), (0, 0))
    else:
        d = ImageDraw.Draw(tile)
        es = int(min(w, h) * 0.34)
        try:
            e = emoji(it.get("e") or "🛒", es)
            tile.alpha_composite(e, ((w - e.width) // 2, int(h * 0.5 - e.height * 0.8)))
        except Exception:
            pass
        kind = it.get("kind") or ""
        if kind:
            f = pf("ExtraBold", max(40, int(min(w, h) * 0.11)))  # 보조 글자 40px↑
            s = _fit(f, kind, w - 40)
            d.text(((w - f.getlength(s)) / 2, h * 0.5 + es * 0.35), s, font=f, fill=ink)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    tile.putalpha(mask)
    return tile


def _save(im, out):
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    im.convert("RGB").save(out, quality=90)
    return out




def luminance(c):
    """WCAG 상대 휘도."""
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (f(x / 255) for x in _hex(c)[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    """WCAG 대비(1~21) — 보통 글자 4.5 이상, 큰 글자(24px↑ 또는 굵은 19px↑) 3 이상."""
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


IG_PAIRS = {  # 인스타 새 카드에 쓰는 글자색·바탕색 전부(셀프체크가 4.5:1 이상인지 봄 — 글자는 모두 40px↑라 큰 글자 기준 3:1보다 높게). 10/22 핑크 톤(진우)
    "A 표지 제목": ("white", NAVY), "A 표지 숫자·핫딜픽·넘겨 보기": (PINK, NAVY), "A 표지 날짜·부제·안내": (MIST, NAVY), "A 칩 이름": ("white", NAVY2), "A 칩 가격": (PINK2, NAVY2),
    "A 상품명·가격·멘트": (INKA, LMIST), "A 하단 줄": (SUBA, LMIST), "A 몰 배지·번호 알약": ("white", PLUM), "A 단위가격 칩": (BERRY, CHIPBG),
    "P 표지 제목(라벤더 끝)": (INKA, LAV), "P 표지 제목(핑크 끝)": (INKA, BLUSH), "P 표지 숫자·핫딜픽·넘겨 보기(라벤더 끝)": (BERRY, LAV), "P 표지 숫자·핫딜픽·넘겨 보기(핑크 끝)": (BERRY, BLUSH),
    "P 표지 날짜·부제·안내(라벤더 끝)": (SUBA, LAV), "P 표지 날짜·부제·안내(핑크 끝)": (SUBA, BLUSH), "P 칩 이름": (INKA, "white"), "P 칩 가격": (BERRY, "white"),
    "A 종류 칸 핑크": (INKA, ATILES[0]), "A 종류 칸 피치": (INKA, ATILES[1]), "A 종류 칸 민트": (INKA, ATILES[2]), "A 종류 칸 라벤더": (INKA, ATILES[3]),
    "B 제목·가격(먹색)": (INKB, PAPER), "B 형광펜 위": (INKB, MARK), "B 타일·폴라로이드 글자": (INKB, "white"), "B 날짜·안내·몰 줄(갈색)": (BROWN, PAPER), "B 더보기 알약": ("white", INKB),
    "B 종류 칸 라벤더": (INKB, TILES[0]), "B 종류 칸 피치": (INKB, TILES[1]), "B 종류 칸 핑크": (INKB, TILES[2]), "B 가격 스티커": (INKB, STICKER), "B 말풍선": (INKB, "white")}


def _sized(text, weight, sizes, width):
    """여러 줄(\n) 글자가 width 안에 들어가는 가장 큰 크기."""
    return next((z for z in sizes if all(pf(weight, z).getlength(l) <= width for l in text.split("\n"))), sizes[-1])


def _marker(d, xy, s, f, fill, mark):
    """형광펜 밑줄(글자 아래 42%) 위에 글자."""
    bb = d.textbbox(xy, s, font=f)
    d.rectangle((bb[0] - 6, bb[3] - int((bb[3] - bb[1]) * 0.42), bb[2] + 6, bb[3] + 4), fill=mark)
    d.text(xy, s, font=f, fill=fill)


def _sparkle(d, cx, cy, r, fill):
    """✦ 반짝이(네 갈래 별) — 장식만, 글자 위에는 X."""
    k = r * 0.28
    d.polygon([(cx, cy - r), (cx + k, cy - k), (cx + r, cy), (cx + k, cy + k), (cx, cy + r), (cx - k, cy + k), (cx - r, cy), (cx - k, cy - k)], fill=fill)


def ig_cover(design, items, date_text, title, out, sub="", note="제휴 링크(수수료) · 게시 시점 가격", swipe=True):
    """인스타 표지(1080x1350 JPEG) — 폰 피드에서 1초 안에 읽히게(10/22 진우): 제목 2줄(크게, 숫자 1개만 포인트색), 보조 글자 40px↑, 대비 4.5:1↑(IG_PAIRS).
    design 'A' = 매거진형(남색·흰 제목·핑크 숫자·상품 알약 칩·✦ 1개 — 상품 장은 파스텔), 'P' = 파스텔 매거진 표지(라벤더→핑크 대각선·자두 먹색 제목·흰 칩 — 상품 장은 A), 'B' = 일상 스티커형(크림·형광펜 제목·2x2 기울인 타일). title = 2줄(\n). date_text: A '10월 22일 목요일' / B '10.22 목'. -> out"""
    lines = title.split("\n")[:2]
    if design == "P":  # 파스텔 매거진 표지(10/23 진우 '파스텔 A 표지도 이것도 좋다' — A 남색 -> B 핑크 -> P 파스텔 날마다 돌림, 상품 장은 A와 같은 파스텔)
        from PIL import ImageChops, ImageFilter
        g = Image.linear_gradient("L")
        m = ImageChops.add(g.rotate(90).resize((W, H)), g.resize((W, H)), scale=2)  # 왼쪽 위 0 -> 오른쪽 아래 255
        im = Image.new("RGBA", (W, H), LMIST + (255,))
        card = Image.new("L", (W, H), 0)
        ImageDraw.Draw(card).rounded_rectangle((24, 24, W - 25, H - 25), radius=56, fill=255)  # 감성 포인트 ① 둥근 모서리
        im.paste(Image.composite(Image.new("RGBA", (W, H), BLUSH + (255,)), Image.new("RGBA", (W, H), LAV + (255,)), m), (0, 0), card)
        d, P = ImageDraw.Draw(im), 88
        f = pf("SemiBold", 40); d.text((P, P), date_text, font=f, fill=SUBA)
        f = pf("ExtraBold", 40); d.text((W - P - 100 - f.getlength("핫딜픽"), P), "핫딜픽", font=f, fill=BERRY)
        _buddy(im, sum(map(ord, date_text)), W - P - 84, P - 22)  # 귀여운 동물 1마리(10/25 진우 — 제목·칩과 안 겹치는 오른쪽 위)
        z = _sized("\n".join(lines), "ExtraBold", (128, 120, 112, 104, 96, 88), W - 2 * P)
        ft, y = pf("ExtraBold", z), 196
        for line in lines:
            x = P
            for tok in re.findall(r"\S+\s*", _fit(ft, line, W - 2 * P)):
                x = _em_text(d, im, (x, y), tok, ft, BERRY if re.search(r"\d", tok) else INKA)  # 맨 앞 이모지(📉 가격 내려간 상품) = 컬러 그림
            y += int(z * 1.2)
        if sub:
            d.text((P, y + 16), _fit(pf("SemiBold", 40), sub, W - 2 * P), font=pf("SemiBold", 40), fill=SUBA)
            y += 16 + 56
        fc, fp = pf("SemiBold", 40), pf("Bold", 40)
        rows, row, rw = [], [], 0
        for it in items:
            name = _fit(fc, it.get("short") or it["name"], 470)
            w = int(fc.getlength(name + "  ") + fp.getlength(it.get("price") or "") + 64)
            if row and rw + w > W - 2 * P:
                rows.append(row); row, rw = [], 0
            row.append((name, it.get("price") or "", w)); rw += w + 16
        rows += [row] if row else []
        y0 = H - P - 60 - 30 - len(rows) * 100
        if y0 - y >= 150:  # 감성 포인트 ② ✦ 반짝이 — 제목과 칩 사이 빈 곳 오른쪽에만(글자와 안 겹치게)
            cy = (y + y0) // 2
            _sparkle(d, W - P - 48, cy + 14, 40, PINK); _sparkle(d, W - P - 128, cy - 44, 20, BERRY)
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
        for k, row in enumerate(rows):
            x = P
            for name, price, w in row:
                sd.rounded_rectangle((x, y0 + k * 100 + 6, x + w, y0 + k * 100 + 90), radius=42, fill=(61, 44, 110, 34))
                x += w + 16
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))  # 아주 옅은 그림자
        for k, row in enumerate(rows):
            x, y = P, y0 + k * 100
            for name, price, w in row:
                d.rounded_rectangle((x, y, x + w, y + 84), radius=42, fill="white")
                d.text((x + 32, y + 18), name + "  ", font=fc, fill=INKA)
                d.text((x + 32 + fc.getlength(name + "  "), y + 18), price, font=fp, fill=BERRY)
                x += w + 16
        f = pf("SemiBold", 40)
        d.text((P, H - P - 48), _fit(f, note, W - 2 * P - 260), font=f, fill=SUBA)
        if swipe:  # 넘길 사진 장이 있을 때만(10/25 리뷰 — 표지 한 장 글에 '넘겨 보기' X)
            d.text((W - P - f.getlength("넘겨 보기 →"), H - P - 48), "넘겨 보기 →", font=f, fill=BERRY)
        return _save(im, out)
    if design == "A":
        im = Image.new("RGBA", (W, H), NAVY + (255,))
        d, P = ImageDraw.Draw(im), 88
        f = pf("SemiBold", 40); d.text((P, P), date_text, font=f, fill=MIST)
        f = pf("ExtraBold", 40); d.text((W - P - 100 - f.getlength("핫딜픽"), P), "핫딜픽", font=f, fill=PINK)
        _buddy(im, sum(map(ord, date_text)), W - P - 84, P - 22)
        z = _sized("\n".join(lines), "ExtraBold", (128, 120, 112, 104, 96, 88), W - 2 * P)
        ft, y = pf("ExtraBold", z), 196
        for line in lines:
            x = P
            for tok in re.findall(r"\S+\s*", _fit(ft, line, W - 2 * P)):
                x = _em_text(d, im, (x, y), tok, ft, PINK if re.search(r"\d", tok) else "white")
            y += int(z * 1.2)
        if sub:
            d.text((P, y + 16), _fit(pf("SemiBold", 40), sub, W - 2 * P), font=pf("SemiBold", 40), fill=MIST)
            y += 16 + 56
        fc, fp = pf("SemiBold", 40), pf("Bold", 40)
        rows, row, rw = [], [], 0
        for it in items:
            name = _fit(fc, it.get("short") or it["name"], 470)
            w = int(fc.getlength(name + "  ") + fp.getlength(it.get("price") or "") + 64)
            if row and rw + w > W - 2 * P:
                rows.append(row); row, rw = [], 0
            row.append((name, it.get("price") or "", w)); rw += w + 16
        rows += [row] if row else []
        y, top = H - P - 60 - 30 - len(rows) * 100, y
        if y - top >= 120:  # ✦ 핑크 1개 작게 — 제목과 칩 사이 빈 곳 오른쪽(글자와 안 겹치게)
            _sparkle(d, W - P - 40, (top + y) // 2, 26, PINK)
        for row in rows:
            x = P
            for name, price, w in row:
                d.rounded_rectangle((x, y, x + w, y + 84), radius=42, fill=NAVY2)
                d.text((x + 32, y + 18), name + "  ", font=fc, fill="white")
                d.text((x + 32 + fc.getlength(name + "  "), y + 18), price, font=fp, fill=PINK2)
                x += w + 16
            y += 100
        f = pf("SemiBold", 40)
        d.text((P, H - P - 48), _fit(f, note, W - 2 * P - 260), font=f, fill=MIST)
        if swipe:
            d.text((W - P - f.getlength("넘겨 보기 →"), H - P - 48), "넘겨 보기 →", font=f, fill=PINK)
        return _save(im, out)
    im = Image.new("RGBA", (W, H), PAPER + (255,))
    d, P = ImageDraw.Draw(im), 76
    d.text((P, 64), _fit(pf("Bold", 40), f"{date_text} · 핫딜픽 일상 장보기", W - 2 * P - 100), font=pf("Bold", 40), fill=BROWN)
    _buddy(im, sum(map(ord, date_text)), W - P - 84, 40)
    z = _sized("\n".join(lines), "ExtraBold", (96, 88, 80, 72), W - 2 * P)
    ft, y = pf("ExtraBold", z), 132
    for k, line in enumerate(lines):
        line = _fit(ft, line, W - 2 * P)
        (_marker(d, (P, y), line, ft, INKB, MARK) if k == 1 else _em_text(d, im, (P, y), line, ft, INKB))
        y += int(z * 1.18)
    tw, th, gx, gy = 452, 372, 32, 34
    x0, y0 = (W - 2 * tw - gx) // 2, y + 26
    fn, fpr = pf("Bold", 40), pf("ExtraBold", 54)
    for k, it in enumerate(items[:4]):
        card = Image.new("RGBA", (tw + 40, th + 50), (0, 0, 0, 0))
        cd = ImageDraw.Draw(card)
        cd.rounded_rectangle((20, 27, 20 + tw, 27 + th), radius=26, fill=SHADOW)  # 아래 그림자
        cd.rounded_rectangle((20, 20, 20 + tw, 20 + th), radius=26, fill="white", outline=EDGE, width=2)
        card.alpha_composite(_photo(it, tw - 36, 186, 18, bg=TILES[k % 3], ink=INKB), (38, 38))  # 종류 칸 라벤더·피치·핑크 번갈아
        cd.text((38, 240), _fit(fn, it.get("short") or it["name"], tw - 36), font=fn, fill=INKB)
        _marker(cd, (38, 300), _fit(fpr, it.get("price") or "", tw - 36), fpr, INKB, MARK)
        card = card.rotate((-2, 1.5, 1, -1.5)[k], resample=Image.BICUBIC, expand=True)
        cx, cy = x0 + (k % 2) * (tw + gx) + tw // 2, y0 + (k // 2) * (th + gy) + th // 2
        im.alpha_composite(card, (cx - card.width // 2, cy - card.height // 2))
    f = pf("Bold", 40)
    more = len(items) - 4
    if more > 0:
        s = f"+{more}개 더" + (" →" if swipe else ""); w = int(f.getlength(s)) + 64  # 넘길 장 없음 = 화살표 X(나머지는 캡션 목록)
        d.rounded_rectangle((W - P - w, H - 112, W - P, H - 36), radius=38, fill=INKB)
        d.text((W - P - w + 32, H - 98), s, font=f, fill="white")
    d.text((P, H - 96), _fit(pf("SemiBold", 40), note, W - 2 * P - (300 if more > 0 else 0)), font=pf("SemiBold", 40), fill=BROWN)
    return _save(im, out)


def ig_slide(design, it, n, total, out):
    """인스타 상품 장(1080x1350 JPEG) — 핵심 숫자 = 가격 1개만 크게, 보조 글자 40px↑, 사진 위 글자는 단색 알약 위(묻히지 않게), 대비 4.5:1↑(IG_PAIRS).
    A = 위 사진(몰 배지·n/total 알약) + 상품명·큰 가격·칩·멘트, B = 기울인 폴라로이드 + 진한 테두리 원 가격 스티커 + 말풍선 멘트 + 몰·배송 줄. 사진 없으면 상품 종류 글자 칸. -> out"""
    when = f"{it['when']} 가격" if it.get("when") else "게시 시점 가격"
    price = it.get("price") or ""
    if design in "AP":
        im = Image.new("RGBA", (W, H), LMIST + (255,))
        d, P = ImageDraw.Draw(im), 56
        im.alpha_composite(_photo(it, W - 2 * P, 680, 28, bg=ATILES[(n - 1) % 4], ink=INKA), (P, P))
        fb = pf("ExtraBold", 44)
        if it.get("badge"):
            w = _pill_w(fb, it["badge"], 30)
            d.rounded_rectangle((P + 24, P + 24, P + 24 + w, P + 112), radius=44, fill=PLUM)
            _em_text(d, im, (P + 54, P + 42), it["badge"], fb, "white")
        fn_ = pf("Bold", 40); s = f"{n:02d} / {total:02d}"; w = int(fn_.getlength(s)) + 56
        d.rounded_rectangle((W - P - 24 - w, P + 24, W - P - 24, P + 112), radius=44, fill=PLUM)
        d.text((W - P - 24 - w + 28, P + 46), s, font=fn_, fill="white")
        X, y = 76, P + 680 + 34
        fn = pf("Bold", 44)
        for line in wrap(d, it["name"], fn, W - 2 * X, 2):
            d.text((X, y), line, font=fn, fill=INKA); y += 56
        fpz = _sized(price, "ExtraBold", (128, 116, 104, 92, 80, 68), W - 2 * X)
        fp = pf("ExtraBold", fpz)
        d.text((X, y), price, font=fp, fill=INKA)
        pb = d.textbbox((X, y), price or "0", font=fp)  # 실제 글자 상자(큰 글자는 위아래 여백이 커서 — 아래 줄과 안 겹치게)
        chip = it.get("chip") or ""
        fc = pf("Bold", 40)
        side = chip and fp.getlength(price) + 24 + fc.getlength(chip) + 48 <= W - 2 * X
        y = pb[3] + 26
        if chip:
            cx, cy = (X + fp.getlength(price) + 24, (pb[1] + pb[3]) // 2 - 32) if side else (X, y)
            c = _fit(fc, chip, W - 2 * X - 48)
            d.rounded_rectangle((cx, cy, cx + fc.getlength(c) + 48, cy + 64), radius=32, fill=CHIPBG)
            d.text((cx + 24, cy + 10), c, font=fc, fill=BERRY)
            y += 0 if side else 86
        if it.get("line"):
            fl = pf("SemiBold", 40)
            for line in wrap(d, f"“{it['line']}”", fl, W - 2 * X, 2 if y < H - 260 else 1):
                d.text((X, y), line, font=fl, fill=INKA); y += 52
        f = pf("SemiBold", 40)
        d.text((X, H - 92), _fit(f, f"제휴 링크(수수료) · {when}", W - 2 * X), font=f, fill=SUBA)
        return _save(im, out)
    from PIL import ImageFilter
    im = Image.new("RGBA", (W, H), PAPER + (255,))
    d = ImageDraw.Draw(im)
    pw, b, bb = 640, 26, 100
    pol = Image.new("RGBA", (pw + 2 * b + 60, pw + b + bb + 60), (0, 0, 0, 0))
    sh = Image.new("RGBA", pol.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((30, 42, 30 + pw + 2 * b, 42 + pw + b + bb), fill=(70, 50, 20, 90))
    pol.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    pd = ImageDraw.Draw(pol)
    pd.rectangle((30, 30, 30 + pw + 2 * b, 30 + pw + b + bb), fill="white")
    pol.alpha_composite(_photo(it, pw, pw, 6, bg=TILES[(n - 1) % 3], ink=INKB), (30 + b, 30 + b))
    fn = pf("Bold", 40)
    pd.text((30 + b, 30 + b + pw + 26), _fit(fn, it.get("short") or it["name"], pw), font=fn, fill=INKB)
    pol = pol.rotate(-2, resample=Image.BICUBIC, expand=True)
    im.alpha_composite(pol, (30, 30))
    st = Image.new("RGBA", (420, 420), (0, 0, 0, 0))
    sd = ImageDraw.Draw(st)
    sd.ellipse((24, 24, 396, 396), fill=STICKER, outline=INKB, width=8)
    fpz = _sized(price, "ExtraBold", (80, 72, 64, 56, 48, 40), 310)
    fp, unit, fu = pf("ExtraBold", fpz), it.get("chip") or "", pf("Bold", 40)
    unit = _fit(fu, unit, 310)
    top = 210 - (fpz + (54 if unit else 0)) // 2 - 8
    sd.text((210 - fp.getlength(price) / 2, top), price, font=fp, fill=INKB)
    if unit:
        sd.text((210 - fu.getlength(unit) / 2, top + fpz + 12), unit, font=fu, fill=INKB)
    st = st.rotate(-8, resample=Image.BICUBIC)
    im.alpha_composite(st, (W - 430, 96))
    y = 870
    if it.get("line"):
        fl = pf("Bold", 44)
        rows = wrap(d, it["line"], fl, W - 2 * 70 - 80, 2)
        bh = 58 * len(rows) + 56
        d.rounded_rectangle((70, y, W - 70, y + bh), radius=28, fill="white", outline=EDGE, width=2)
        d.polygon([(150, y + 1), (192, y + 1), (160, y - 30)], fill="white")
        for k, line in enumerate(rows):
            _em_text(d, im, (110, y + 28 + 58 * k), line, fl, INKB)
        y += bh + 36
    else:
        y += 20
    meta = " · ".join(x for x in (it.get("badge"), it.get("ship")) if x)
    if meta:
        _em_text(d, im, (76, y), _fit(pf("Bold", 40), meta, W - 160), pf("Bold", 40), BROWN)
    f = pf("SemiBold", 40)
    d.text((76, H - 92), _fit(f, f"{when} · 제휴 링크(수수료)", W - 152), font=f, fill=BROWN)
    return _save(im, out)


BUDDIES = ("🐻", "🐰", "🐱", "🐶", "🐹", "🐥", "🐼", "🦊")  # 인스타 카드 귀여운 동물(10/25 진우 — Noto 컬러 이모지, 음식 그림과 같은 글꼴 · 알려진 캐릭터 X) · 카드 번호대로 돌림
BUDDY_WORDS = ("득템!", "찜 각", "가성비 굿", "장바구니 GO", "쟁여두기")  # 말풍선(효능·가격 단정 X)


def _buddy(im, k, x, y, word=""):
    """동물 이모지(84px) 1마리를 (x, y)에 + word가 있으면 그 왼쪽에 말풍선(흰 바탕·자두 테두리·꼬리 = 동물 쪽) — 못 그리면 건너뜀(카드는 그대로)."""
    try:
        e = emoji(BUDDIES[k % len(BUDDIES)], 84)
    except Exception:
        return
    im.alpha_composite(e, (x + (84 - e.width) // 2, y + (84 - e.height) // 2))
    if word:
        d, f = ImageDraw.Draw(im), pf("Bold", 40)
        w, bx = int(f.getlength(word)) + 44, x - 14
        d.rounded_rectangle((bx - w, y + 10, bx, y + 74), radius=30, fill="white", outline=PLUM, width=3)
        d.polygon([(bx - 2, y + 30), (bx + 12, y + 42), (bx - 2, y + 54)], fill="white")
        d.line([(bx - 1, y + 30), (bx + 12, y + 42), (bx - 1, y + 54)], fill=PLUM, width=3)
        d.text((bx - w + 22, y + 18), word, font=f, fill=INKA)


def ig_photo_card(it, n, out):
    """인스타 상품 사진 장(1080x1350 JPEG, 10/25 Cowork ② — 넘기기 2장부터 카드 번호 순): 판매 페이지 사진은 줄이고·키우기만(자르기 X — 비율 그대로 흰 칸 가운데, 위에 글자 X),
    글자는 사진 밖 여백에 — 위 'N번' 알약·핫딜픽, 아래 짧은 이름·가격·'프로필 링크 → N번'(토스 사진이면 같은 줄 오른쪽 '사진: 토스쇼핑')·제휴 링크·가격 시각. 보조 글자 40px↑ · 대비 = A 상품 장 짝(IG_PAIRS).
    it['was'] = 📉 가격 내려간 상품 장(10/25 진우 D): 알약 '▼N%' · 기록가 취소선 → 지금가 · '프로필 링크' 줄 대신 기준 it['basis'](같은 구성 · M/D 기록 대비). -> out"""
    im = Image.new("RGBA", (W, H), LMIST + (255,))
    d, P = ImageDraw.Draw(im), 56
    fb = pf("ExtraBold", 48); s = f"▼{it['pct']}%" if it.get("was") else f"{n}번"; w = int(fb.getlength(s)) + 64
    d.rounded_rectangle((P, 48, P + w, 136), radius=44, fill=PLUM)
    d.text((P + 32, 60), s, font=fb, fill="white")
    f = pf("ExtraBold", 40); d.text((P + w + 20, 70), "핫딜픽", font=f, fill=BERRY)
    _buddy(im, n - 1, W - P - 84, 46, BUDDY_WORDS[(n - 1) % len(BUDDY_WORDS)])  # 동물 + 말풍선 = 사진 칸 위 오른쪽 모서리(사진·가격 안 가림)
    x0, y0, x1, y1 = P, 164, W - P, 964  # 사진 칸(흰 바탕) 968x800 — 안쪽 24px 여백
    d.rounded_rectangle((x0, y0, x1, y1), radius=28, fill="white")
    ph = Image.open(it["photo"])
    ph.load()
    if ph.mode in ("RGBA", "LA", "P") or "transparency" in ph.info:  # 투명 = 흰 바탕
        ph = ph.convert("RGBA"); bg = Image.new("RGB", ph.size, "white"); bg.paste(ph, mask=ph.split()[3]); ph = bg
    ph = ph.convert("RGB")
    k = min((x1 - x0 - 48) / ph.width, (y1 - y0 - 48) / ph.height)
    ph = ph.resize((max(1, round(ph.width * k)), max(1, round(ph.height * k))), Image.LANCZOS)
    im.paste(ph, ((x0 + x1 - ph.width) // 2, (y0 + y1 - ph.height) // 2))
    X, y = 76, 994
    fn = pf("Bold", 44)
    d.text((X, y), _fit(fn, it.get("short") or it["name"], W - 2 * X), font=fn, fill=INKA)
    price, x = it.get("price") or "", X
    if it.get("was"):  # 기록가(취소선) → 지금가 — 'N원 쌈'·'최저가' X
        fw, was = pf("SemiBold", 52), f"{it['was']:,}원"
        x = X + int(fw.getlength(was + " → ")) + 8
    fp = pf("ExtraBold", _sized(price, "ExtraBold", (88, 80, 72, 64, 56, 48), W - X - x))
    d.text((x, y + 60), price, font=fp, fill=INKA)
    if it.get("was"):  # 지금가와 같은 글자 밑선
        base = y + 60 + fp.getmetrics()[0]
        b = d.textbbox((X, base), was, font=fw, anchor="ls")
        d.text((X, base), was + " →", font=fw, fill=SUBA, anchor="ls")
        d.line([(b[0] - 4, (b[1] + b[3]) // 2), (b[2] + 4, (b[1] + b[3]) // 2)], fill=SUBA, width=5)
    yb = d.textbbox((x, y + 60), price or "0", font=fp)[3] + 20
    fl, fs = pf("Bold", 44), pf("SemiBold", 40)
    credit = "사진: 토스쇼핑" if it.get("src") == "toss" else ""
    d.text((X, yb), _fit(fl, it.get("basis") or f"프로필 링크 → {n}번", W - 2 * X - (fs.getlength(credit) + 24 if credit else 0)), font=fl, fill=BERRY)
    if credit:
        d.text((W - X - fs.getlength(credit), yb + 4), credit, font=fs, fill=SUBA)
    when = f"{it['when']} 가격" if it.get("when") else "게시 시점 가격"
    d.text((X, H - 84), _fit(fs, f"제휴 링크(수수료) · {when}", W - 2 * X), font=fs, fill=SUBA)
    return _save(im, out)


LOGO_GRAD, PICK_RED = ((255, 104, 96), (220, 34, 48)), (222, 38, 52)  # 웹앱 아이콘 'A 레드'(10/23 진우): 왼쪽 위 -> 오른쪽 아래 그라데이션 · 알약 안 'pick' 색


def app_logo(n, mini=False):
    """웹앱 아이콘 1장(n×n) 'A 레드'(10/23 진우 — 원 아이콘은 런처가 확대해 '딜'이 잘림): 꽉 찬 정사각 대각선 그라데이션(any·maskable·애플 같은 그림, 모양은 런처가 깎음)
    + 흰 '딜'(Black, 0.40n, 가운데 y 0.42n) + 흰 알약(0.38n×0.14n, 가운데 y 0.695n) 안 빨간 'pick'(Bold, 0.095n, 자간 0.006n, 가운데 y 0.69n) — 다 가운데 60% 안(maskable 안전 영역 안 — 원·둥근 네모로 깎아도 안 잘림).
    shortcut: 크롬 '바로가기'(배지) = 픽셀 런처 배지(아이콘 0.444)가 알약 오른쪽 끝·k를 가림 — 앱 설치(WebAPK)는 배지 X, 바로가기도 피하려면 진우 결정.
    mini = 파비콘(16·32·48): '딜'만, 같은 그라데이션 둥근 네모(모서리 투명). 4배로 그려 줄여서 가장자리를 매끈하게."""
    k = 4
    N = n * k
    g = Image.linear_gradient("L").resize((N, N), Image.BILINEAR)
    im = Image.composite(Image.new("RGBA", (N, N), LOGO_GRAD[1] + (255,)), Image.new("RGBA", (N, N), LOGO_GRAD[0] + (255,)),
                         Image.blend(g, g.transpose(Image.TRANSPOSE), 0.5))  # (x + y) / 2 = 대각선
    if mini:
        m = Image.new("L", (N, N), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, N - 1, N - 1), radius=N * 0.22, fill=255)
        im.putalpha(m)
    d = ImageDraw.Draw(im)
    f = pf("Black", int(N * (0.7 if mini else 0.40)))
    b = d.textbbox((0, 0), "딜", font=f)
    d.text((N / 2 - (b[0] + b[2]) / 2, N * (0.5 if mini else 0.42) - (b[1] + b[3]) / 2), "딜", font=f, fill="white")
    if not mini:
        w, h, cy = N * 0.38, N * 0.14, N * 0.695
        d.rounded_rectangle((N / 2 - w / 2, cy - h / 2, N / 2 + w / 2, cy + h / 2), radius=h / 2, fill="white")
        f, sp = pf("Bold", int(N * 0.095)), N * 0.006
        xs = [sum(f.getlength(c) + sp for c in "pick"[:i]) for i in range(4)]
        x0, x1 = xs[0] + f.getbbox("p")[0], xs[3] + f.getbbox("k")[2]  # 글자 잉크 기준 가운데
        b = d.textbbox((0, 0), "pick", font=f)
        for x, c in zip(xs, "pick"):
            d.text((N / 2 - (x0 + x1) / 2 + x, N * 0.69 - (b[1] + b[3]) / 2), c, font=f, fill=PICK_RED)
    return im.resize((n, n), Image.LANCZOS)


SC_ICONS = {"fire": ("🔥", (255, 230, 218), (255, 186, 164)), "wait": ("⏳", (255, 246, 210), (255, 222, 140)), "life": ("🧻", (224, 248, 238), (166, 228, 206))}  # 웹앱 바로가기 'V1 파스텔 이모지'(10/24 진우): 이모지·위·아래 색


def sc_icon(ch, top, bottom, n):
    """웹앱 바로가기(아이콘 길게 누르기 메뉴) 아이콘 n×n: 위 -> 아래 파스텔 그라데이션 꽉 찬 정사각 + 가운데 컬러 이모지(긴 변 = 0.5n).
    shortcut: 크롬은 바로가기에 'any' 아이콘만 그대로(비트맵) 넘김 -> 픽셀 런처는 안 깎고 흰 원 안에 약 0.56로 줄여 둠(이모지 ≈ 원의 28%) — 더 크게는 진우 결정."""
    im = Image.composite(Image.new("RGB", (n, n), bottom), Image.new("RGB", (n, n), top), Image.linear_gradient("L").resize((n, n), Image.BILINEAR))
    e = emoji(ch, n // 2)
    im.paste(e, ((n - e.width) // 2, (n - e.height) // 2), e)
    return im


def app_icons(d="docs/icons", root="docs"):
    """웹앱(PWA) 아이콘(10/23 진우 '웹앱으로', 'A 레드') -> d/: icon-192·512(any)·icon-512-maskable·apple-touch-icon(180) = 같은 꽉 찬 그림(투명 X — 런처·iOS가 모양을 깎음),
    favicon-32·16('딜'만, 둥근 네모) + root/favicon.ico(16·32·48) + 바로가기 sc-fire·wait·life(192·96). 바꾸면 build_site.IV 올림(폰이 새 파일로 알게). -> 만든 파일 목록"""
    os.makedirs(d, exist_ok=True)
    big = app_logo(512).convert("RGB")
    out = {f"{d}/icon-192.png": app_logo(192).convert("RGB"), f"{d}/icon-512.png": big, f"{d}/icon-512-maskable.png": big,
           f"{d}/apple-touch-icon.png": app_logo(180).convert("RGB"), f"{d}/favicon-32.png": app_logo(32, mini=True), f"{d}/favicon-16.png": app_logo(16, mini=True)}
    for k, (ch, a, b) in SC_ICONS.items():  # 바로가기 sc-{k}.png(192) · sc-{k}-96.png
        out[f"{d}/sc-{k}.png"], out[f"{d}/sc-{k}-96.png"] = sc_icon(ch, a, b, 192), sc_icon(ch, a, b, 96)
    for p, im in out.items():
        im.save(p, optimize=True)
    app_logo(256, mini=True).save(f"{root}/favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    return [*out, f"{root}/favicon.ico"]

def og_image(path="docs/og.png"):
    """사이트 대표 공유 그림 1200×630(10/24 진우 개편 'A 클린 화이트' + 핑크 포인트 — og:image 기본값, 쿠팡 사진·그날 카드가 없을 때): 앱 아이콘 + 핫딜픽 + 한 줄 + 핑크 알약 3개. 한 번 만들어 커밋."""
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), (246, 247, 249))
    d = ImageDraw.Draw(im)
    logo = app_logo(220).convert("RGB")
    m = Image.new("L", (220, 220), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, 219, 219), radius=58, fill=255)
    im.paste(logo, (96, 118), m)
    d.text((360, 128), "핫딜픽", font=pf("ExtraBold", 112), fill=(20, 22, 27))
    d.text((364, 272), "쿠팡·토스·네이버 특가를 매일 골라드려요", font=pf("SemiBold", 40), fill=(107, 113, 128))
    x, f = 96, pf("Bold", 36)
    for t in ("오늘의 픽 3", "지금 특가", "꾸준히 팔리는 것"):
        w = d.textlength(t, font=f) + 64
        d.rounded_rectangle((x, 420, x + w, 500), radius=40, fill=(255, 227, 232))
        d.text((x + 32, 460), t, font=f, fill=(232, 67, 90), anchor="lm")
        x += w + 20
    d.text((96, 560), "hotdealpick.kr", font=pf("Bold", 30), fill=(229, 48, 63))
    im.save(path, optimize=True)
    return path
