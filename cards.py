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


def reel(items, date_label, out, music=None):
    """깔끔·세련되게, 그러면서 '사고 싶고 합리적인 소비'로 느껴지게: 15초 1080x1920 MP4. music(음악 파일 경로) 있으면 배경음악(짧으면 반복·앞뒤 페이드), 없으면 무음. -> out
    items: [{"title", "comment", "e": 이모지, "hook": 첫 화면 한 줄, "pts": 합리적인 이유 2~3개}] 최대 3개 (e·hook·pts 없으면 제목·코멘트로 대신)
    디자인: 크림색 바탕 + 먹색 글자 + 포인트색은 숫자에만, 왼쪽 정렬 한 기준선, 프리텐다드, 흰 타일 위 이모지,
    은은한 페이드·떠오름 + 장면 사이 0.2초 디졸브. 마지막은 어두운 바탕에 저장·공유 유도.
    글자는 인스타 UI가 덮는 위(~250px)·아래(~420px)를 피해서 배치."""
    import subprocess
    items = [_norm(it) for it in items[:3]]
    for it in items:
        it["hook"] = it.get("hook") or f"{it['name'][:12]} {it['main']}".strip()
    cream, night = Image.new("RGB", (RW, RH), CREAM), Image.new("RGB", (RW, RH), NIGHT)
    scenes = []  # (배경, 초, 그리기(frame, t), 진행 막대 색)

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
    scenes.append((cream, 2.0, intro, INK2))

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
            _in(fr, lab, X0, 300, t, 0.0)
            _in(fr, tile, X0 - 40, 362, t, 0.05)
            y = 700
            _in(fr, name, X0, y, t, 0.12)
            y += name.height + 8
            if price:
                _in(fr, price, X0, y, t, 0.22)
                if pill:  # 가격 오른쪽, 글자 아래쪽에 맞춤
                    _in(fr, pill, X0 + price.width + 20, y + price.height - pill.height - 22, t, 0.32)
                y += price.height + 10
            elif pill:
                _in(fr, pill, X0, y, t, 0.32)
                y += 90
            if unit:  # 비교 근거: 단위가격
                _in(fr, unit, X0, y - 14, t, 0.36)
                y += 80
            if checks or warn:
                _rule(fr, y, t, 0.42)
                _in(fr, why, X0, y + 36, t, 0.5)
                for k, c in enumerate(checks):
                    _in(fr, c, X0, y + 104 + 84 * k, t, 0.6 + 0.15 * k)
                if warn:
                    _in(fr, warn, X0, y + 104 + 84 * len(checks) + 6, t, 0.6 + 0.15 * len(checks))
        scenes.append((cream, 3.5, deal, INK2))

    light, dim = (172, 176, 184), (112, 116, 124)
    o = [(_text("저장해두고", pf("Bold", 84), "white"), 500, 0.0), (_text("장보기 전에 꺼내보세요", pf("Bold", 84), "white"), 604, 0.06),
         (_text("필요한 친구에게 보내줘도 좋아요", pf("Medium", 44), light), 740, 0.16),
         (_text("매일 밤 9시  ·  가성비 TOP3", pf("SemiBold", 44), "white"), 920, 0.3),
         (_text("hotdealpick.kr", pf("Bold", 58), ACCENT), 990, 0.36),
         (_text("프로필 링크에서 전체 딜 · 구매 링크", pf("Regular", 40), light), 1075, 0.42),
         (_text("텔레그램 실시간 알림  @hotdeal_pick", pf("Regular", 40), light), 1135, 0.48),
         (_text("일부 링크는 제휴 링크로, 구매 시 수수료를 받을 수 있어요.", pf("Regular", 30), dim), 1380, 0.55)]

    def outro(fr, t):
        for im, y, dl in o:
            _in(fr, im, X0, y, t, dl)
        _rule(fr, 860, t, 0.24, (58, 61, 68))
    scenes.append((night, 2.5, outro, "white"))

    total, n_sc = sum(s for _, s, _, _ in scenes), len(scenes)
    seg = (XW - 12 * (n_sc - 1)) / n_sc
    cmd = [ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{RW}x{RH}", "-r", str(FPS), "-i", "-"]
    if music:
        cmd += ["-stream_loop", "-1", "-i", music, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "128k", "-shortest",
                "-af", f"afade=t=in:d=0.5,afade=t=out:st={total - 1.5}:d=1.5"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "veryfast", "-movflags", "+faststart", "-use_editlist", "0", out]  # 인스타 릴스 규격: edit list 없음·moov 앞
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    proc, last = subprocess.Popen(cmd, stdin=subprocess.PIPE), None
    for si, (bg, sec, draw, bar) in enumerate(scenes):
        frames = int(sec * FPS)
        for i in range(frames):
            frame = bg.copy()
            draw(frame, i / FPS)
            d = ImageDraw.Draw(frame)  # 위쪽 장면별 진행 막대 (스토리처럼)
            for k in range(n_sc):
                x = X0 + k * (seg + 12)
                d.rounded_rectangle((x, 150, x + seg, 155), radius=3, fill=LINE if bg is cream else (58, 61, 68))
                fill = 1.0 if k < si else (i + 1) / frames if k == si else 0
                if fill:
                    d.rounded_rectangle((x, 150, x + seg * fill, 155), radius=3, fill=bar)
            if last is not None and i < 6:  # 장면 사이 0.2초 디졸브
                frame = Image.blend(last, frame, (i + 1) / 6)
            proc.stdin.write(frame.tobytes())
        last = frame
    proc.stdin.close()
    if proc.wait():
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
NAVY, NAVY2, ORANGE, PAPER, BROWN, INKB, RUST, HIGHLIGHT = (29, 39, 64), (43, 55, 87), (255, 138, 61), (246, 241, 231), (138, 123, 102), (43, 36, 27), (217, 72, 15), (255, 216, 77)


def _hex(c):
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


def _photo(it, w, h, radius, bg=(227, 231, 239), ink=NAVY):
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
            f = pf("ExtraBold", max(26, int(min(w, h) * 0.11)))
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


def ig_cover(design, items, date_text, title, out, sub="", note="넘겨서 보기 → · 일부 제휴 링크(수수료) · 가격은 게시 시점 기준"):
    """인스타 표지(1080x1350 JPEG). design 'A' = 매거진형(남색·큰 제목 3줄·상품 알약 칩), 'B' = 일상 스티커형(크림·형광펜 제목 2줄·2x2 기울인 타일).
    title = 줄바꿈(\\n)으로 나눈 제목(숫자는 포인트색), sub = 부제(👍 꾸준템이 있을 때 등, A만). date_text: A '10월 22일 목요일' / B '10.22 목'. -> out"""
    if design == "A":
        im = Image.new("RGBA", (W, H), NAVY + (255,))
        d, P = ImageDraw.Draw(im), 88
        d.text((P, P), date_text, font=pf("SemiBold", 32), fill=_hex("#aab4c8"))
        f = pf("Bold", 32); d.text((W - P - f.getlength("핫딜픽"), P), "핫딜픽", font=f, fill=ORANGE)
        y, ft = 176, pf("ExtraBold", 104)
        for line in title.split("\n")[:3]:
            x = P
            for tok in re.findall(r"\S+\s*", _fit(ft, line, W - 2 * P)):
                d.text((x, y), tok, font=ft, fill=ORANGE if re.search(r"\d", tok) else "white")
                x += d.textlength(tok, font=ft)
            y += 122
        if sub:
            d.text((P, y + 22), sub, font=pf("Medium", 36), fill=_hex("#c9d1e0"))
        fc, fp = pf("SemiBold", 34), pf("Bold", 34)
        rows, row, rw = [], [], 0
        for it in items:
            name = _fit(fc, it.get("short") or it["name"], 420)
            w = int(fc.getlength(name + "  ") + fp.getlength(it.get("price") or "") + 56)
            if row and rw + w > W - 2 * P:
                rows.append(row); row, rw = [], 0
            row.append((name, it.get("price") or "", w)); rw += w + 16
        rows += [row] if row else []
        y = H - 150 - len(rows) * 88
        for row in rows:
            x = P
            for name, price, w in row:
                d.rounded_rectangle((x, y, x + w, y + 70), radius=35, fill=NAVY2)
                d.text((x + 28, y + 15), name + "  ", font=fc, fill="white")
                d.text((x + 28 + fc.getlength(name + "  "), y + 15), price, font=fp, fill=ORANGE)
                x += w + 16
            y += 88
        d.text((P, H - P - 30), note, font=pf("Regular", 26), fill=_hex("#7f8aa3"))
        return _save(im, out)
    im = Image.new("RGBA", (W, H), PAPER + (255,))
    d, P = ImageDraw.Draw(im), 76
    d.text((P, 74), f"{date_text} · 핫딜픽 일상 장보기", font=pf("SemiBold", 30), fill=BROWN)
    ft, y = pf("ExtraBold", 84), 138
    for k, line in enumerate(title.split("\n")[:2]):
        line = _fit(ft, line, W - 2 * P)
        if k == 1:  # 둘째 줄 형광펜 밑줄(글자 아래 42%)
            bb = d.textbbox((P, y), line, font=ft)
            d.rectangle((bb[0] - 6, bb[3] - int((bb[3] - bb[1]) * 0.42), bb[2] + 6, bb[3] + 4), fill=HIGHLIGHT)
        d.text((P, y), line, font=ft, fill=INKB)
        y += 104
    from PIL import ImageFilter
    tw, th, gx, gy = 440, 392, 44, 40
    x0, y0 = (W - 2 * tw - gx) // 2, 392
    for k, it in enumerate(items[:4]):
        card = Image.new("RGBA", (tw + 40, th + 50), (0, 0, 0, 0))
        cd = ImageDraw.Draw(card)
        cd.rounded_rectangle((20, 26, 20 + tw, 26 + th), radius=26, fill=_hex("#e6dccb"))  # 아래 그림자 6px
        cd.rounded_rectangle((20, 20, 20 + tw, 20 + th), radius=26, fill="white")
        card.alpha_composite(_photo(it, tw - 36, 230, 18, bg=(244, 238, 226), ink=INKB), (38, 38))
        f1, f2 = pf("SemiBold", 27), pf("ExtraBold", 38)
        cd.text((38, 284), _fit(f1, it.get("short") or it["name"], tw - 36), font=f1, fill=INKB)
        cd.text((38, 326), _fit(f2, it.get("price") or "", tw - 36), font=f2, fill=RUST)
        card = card.rotate((-2, 1.5, 1, -1.5)[k], resample=Image.BICUBIC, expand=True)
        cx, cy = x0 + (k % 2) * (tw + gx) + tw // 2, y0 + (k // 2) * (th + gy) + th // 2
        im.alpha_composite(card, (cx - card.width // 2, cy - card.height // 2))
    more = len(items) - 4
    if more > 0:
        f = pf("Bold", 30); s = f"+{more}개 더 →"; w = int(f.getlength(s)) + 56
        d.rounded_rectangle((W - P - w, H - 128, W - P, H - 64), radius=32, fill=INKB)
        d.text((W - P - w + 28, H - 117), s, font=f, fill="white")
    d.text((P, H - 108), "제휴 링크 수수료 · 게시 시점 가격", font=pf("Regular", 24), fill=BROWN)
    return _save(im, out)


def ig_slide(design, it, n, total, out):
    """인스타 상품 장(1080x1350 JPEG, 표지 다음 장들). A = 위 700px 사진(몰 배지·n/total 알약) + 상품명·큰 가격·칩·한 줄 멘트,
    B = 기울인 폴라로이드 사진 + 노란 원 스티커(가격·단위가격) + 말풍선 멘트 + 몰·배송 줄. 사진 없으면 상품 종류 글자 칸. -> out"""
    when = f"{it['when']} 가격" if it.get("when") else "게시 시점 가격"
    if design == "A":
        im = Image.new("RGBA", (W, H), _hex("#f4f5f8") + (255,))
        d, P = ImageDraw.Draw(im), 60
        im.alpha_composite(_photo(it, W - 2 * P, 700, 28), (P, P))
        fb = pf("SemiBold", 30)
        if it.get("badge"):
            w = _pill_w(fb, it["badge"], 24)
            d.rounded_rectangle((P + 24, P + 24, P + 24 + w, P + 84), radius=30, fill=NAVY)
            _em_text(d, im, (P + 48, P + 35), it["badge"], fb, "white")
        s = f"{n:02d} / {total:02d}"; w = int(fb.getlength(s)) + 48
        d.rounded_rectangle((W - P - 24 - w, P + 24, W - P - 24, P + 84), radius=30, fill="white")
        d.text((W - P - 24 - w + 24, P + 35), s, font=fb, fill=NAVY)
        X, y = 80, 800
        fn = pf("SemiBold", 44)
        for line in wrap(d, it["name"], fn, W - 2 * X, 2):
            d.text((X, y), line, font=fn, fill=NAVY); y += 56
        y += 10
        fpz = next((z for z in (96, 84, 72, 60) if pf("ExtraBold", z).getlength(it.get("price") or "") <= W - 2 * X - (260 if it.get("chip") else 0)), 60)
        fp = pf("ExtraBold", fpz)
        d.text((X, y), it.get("price") or "", font=fp, fill=NAVY)
        if it.get("chip"):
            fc = pf("SemiBold", 34); c = _fit(fc, it["chip"], W - 2 * X - fp.getlength(it.get("price") or "") - 70)
            cx, cw = X + fp.getlength(it.get("price") or "") + 24, int(fc.getlength(c)) + 40
            cy = y + fpz - 62
            d.rounded_rectangle((cx, cy, cx + cw, cy + 56), radius=28, fill=_hex("#ffe7d6"))
            d.text((cx + 20, cy + 8), c, font=fc, fill=_hex("#e8590c"))
        y += int(fpz * 1.18) + 12
        if it.get("line"):
            fl = pf("Medium", 36)
            for line in wrap(d, f"“{it['line']}”", fl, W - 2 * X, 2):
                d.text((X, y), line, font=fl, fill=_hex("#4a5568")); y += 48
        d.text((X, H - 70), f"핫딜픽 · 제휴 링크로 수수료를 받을 수 있음 · {when}", font=pf("Regular", 24), fill=_hex("#9aa3b2"))
        return _save(im, out)
    from PIL import ImageFilter
    im = Image.new("RGBA", (W, H), PAPER + (255,))
    d = ImageDraw.Draw(im)
    pw, b, bb = 640, 26, 90
    pol = Image.new("RGBA", (pw + 2 * b + 60, pw + b + bb + 60), (0, 0, 0, 0))
    sh = Image.new("RGBA", pol.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((30, 42, 30 + pw + 2 * b, 42 + pw + b + bb), fill=(80, 60, 30, 70))
    pol.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    pd = ImageDraw.Draw(pol)
    pd.rectangle((30, 30, 30 + pw + 2 * b, 30 + pw + b + bb), fill="white")
    pol.alpha_composite(_photo(it, pw, pw, 6, bg=(244, 238, 226), ink=INKB), (30 + b, 30 + b))
    fn = pf("SemiBold", 34)
    pd.text((30 + b, 30 + b + pw + 24), _fit(fn, it.get("short") or it["name"], pw), font=fn, fill=INKB)
    pol = pol.rotate(-2, resample=Image.BICUBIC, expand=True)
    im.alpha_composite(pol, (36, 40))
    st = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    sd = ImageDraw.Draw(st)
    sd.ellipse((25, 25, 275, 275), fill=HIGHLIGHT)
    price = it.get("price") or ""
    fpz = next((z for z in (52, 46, 40, 34) if pf("ExtraBold", z).getlength(price) <= 210), 34)
    fp = pf("ExtraBold", fpz)
    unit = it.get("chip") or ""
    fu = pf("SemiBold", 28); unit = _fit(fu, unit, 200)
    top = 150 - (fpz + (36 if unit else 0)) // 2
    sd.text((150 - fp.getlength(price) / 2, top), price, font=fp, fill=INKB)
    if unit:
        sd.text((150 - fu.getlength(unit) / 2, top + fpz + 8), unit, font=fu, fill=INKB)
    st = st.rotate(-8, resample=Image.BICUBIC)
    im.alpha_composite(st, (W - 340, 150))
    y = 900
    if it.get("line"):
        fl = pf("SemiBold", 38)
        rows = wrap(d, it["line"], fl, W - 2 * 76 - 80, 2)
        bh = 52 * len(rows) + 56
        d.rounded_rectangle((76, y, W - 76, y + bh), radius=28, fill="white")
        d.polygon([(150, y), (190, y), (160, y - 30)], fill="white")
        for k, line in enumerate(rows):
            _em_text(d, im, (116, y + 28 + 52 * k), line, fl, INKB)
        y += bh + 34
    else:
        y += 20
    meta = " · ".join(x for x in (it.get("badge"), it.get("ship")) if x)
    if meta:
        _em_text(d, im, (80, y), meta, pf("SemiBold", 28), BROWN)
    d.text((80, H - 70), f"{when} · 제휴 링크로 수수료를 받을 수 있음 · 핫딜픽", font=pf("Regular", 24), fill=BROWN)
    return _save(im, out)
