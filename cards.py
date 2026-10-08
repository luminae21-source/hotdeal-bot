#!/usr/bin/env python3
"""오늘의 딜 카드 이미지(1080x1350 PNG) + 인스타 릴스 영상(1080x1920 MP4). Pillow 필요 (워크플로에서 설치)."""
import os, re
from PIL import Image, ImageDraw, ImageFont
from build_site import parse  # 제목 -> (몰, 이름, 가격): 사이트 격자와 같이 씀

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


def make(items, date_label, out):
    """오늘의 딜 카드(1080x1350, 릴스와 같은 크림·먹색·숫자 포인트색 디자인). items: 딜 제목 문자열 또는 {"title", "unit"} (최대 5개). -> out"""
    im = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(im)
    d.text((X0, 84), f"{date_label}  ·  오늘의 가성비 딜", font=pf("SemiBold", 34), fill=SUB)
    f = pf("Bold", 34); d.text((W - X0 - d.textlength("핫딜픽", font=f), 84), "핫딜픽", font=f, fill=ACCENT)
    d.text((X0, 136), "오늘 살 만한 딜", font=pf("ExtraBold", 76), fill=INK2)
    d.rectangle((X0, 262, W - X0, 264), fill=LINE)
    y = 292
    for n, it in enumerate([{"title": i} if isinstance(i, str) else i for i in items][:5], 1):
        store, name, price = parse(it["title"])
        d.text((X0, y), f"{n:02d}", font=pf("ExtraBold", 34), fill=ACCENT)
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
                d.text((x, y + 112), unit, font=fs, fill=ACCENT)
                x += d.textlength(unit + "  ", font=fs)
            if ship:
                d.text((x, y + 112), ("·  " if unit else "") + ship, font=fs, fill=SUB)
        y += 170
        if n < min(len(items), 5):
            d.rectangle((X0, y - 14, W - X0, y - 13), fill=LINE)
    d.rectangle((X0, H - 200, W - X0, H - 198), fill=LINE)
    d.text((X0, H - 170), "전체 딜 · 구매 링크", font=pf("SemiBold", 32), fill=INK2)
    f = pf("Bold", 40); d.text((W - X0 - d.textlength("hotdealpick.kr", font=f), H - 176), "hotdealpick.kr", font=f, fill=ACCENT)
    d.text((X0, H - 112), "실시간 알림 t.me/hotdeal_pick  ·  블로그 blog.naver.com/hotdeal_pick", font=pf("Regular", 26), fill=SUB)
    d.text((X0, H - 66), "일부 링크는 제휴 링크로, 구매 시 수수료를 받을 수 있어요. 가격·재고는 게시 시점 기준.", font=pf("Regular", 22), fill=SUB)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
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


def reel(items, date_label, out, music=None):
    """깔끔·세련되게, 그러면서 '사고 싶고 합리적인 소비'로 느껴지게: 15초 1080x1920 MP4. music(음악 파일 경로) 있으면 배경음악(짧으면 반복·앞뒤 페이드), 없으면 무음. -> out
    items: [{"title", "comment", "e": 이모지, "hook": 첫 화면 한 줄, "pts": 합리적인 이유 2~3개}] 최대 3개 (e·hook·pts 없으면 제목·코멘트로 대신)
    디자인: 크림색 바탕 + 먹색 글자 + 포인트색은 숫자에만, 왼쪽 정렬 한 기준선, 프리텐다드, 흰 타일 위 이모지,
    은은한 페이드·떠오름 + 장면 사이 0.2초 디졸브. 마지막은 어두운 바탕에 저장·공유 유도.
    글자는 인스타 UI가 덮는 위(~250px)·아래(~420px)를 피해서 배치."""
    import subprocess
    items = [dict(it) for it in items[:3]]
    for it in items:
        store, name, price = parse(it["title"])
        main, _, ship = price.partition("/")
        ship = "무료배송" if ship.strip() in ("무료", "무배", "무료배송") else ship.strip()
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", it.get("comment") or "") if s.strip() and not s.lstrip().startswith(("💡", "⚠"))]
        unit, warn = (it.get("unit") or "").strip(), (it.get("warn") or "").strip()
        it.update(store=store, name=name, main=main.strip(), ship=ship, unit=unit, warn=warn,  # 배송·단위가격은 따로 표시 -> 이유 목록에서 뺌
                  pts=[p for p in (it.get("pts") or sents) if p.replace(" ", "") not in (ship.replace(" ", ""), unit.replace(" ", ""))][:3 - bool(warn)],
                  hook=it.get("hook") or f"{name[:12]} {main.strip()}".strip())
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
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "veryfast", "-movflags", "+faststart", out]
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
