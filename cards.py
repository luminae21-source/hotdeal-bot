#!/usr/bin/env python3
"""오늘의 딜 모아보기 -> Threads/인스타용 카드 이미지(1080x1350 PNG). Pillow 필요 (워크플로에서 설치)."""
import os, re
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
ORANGE, RED, INK, GRAY, BG = (255, 90, 40), (225, 40, 40), (28, 30, 33), (120, 120, 120), (246, 247, 249)
FONTS = {  # 러너: fonts/ (워크플로가 Google Fonts 저장소에서 내려받음) / 로컬: Noto CJK
    "bold": ["fonts/NanumGothic-ExtraBold.ttf", "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"],
    "reg": ["fonts/NanumGothic-Regular.ttf", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"],
}


def font(kind, size):
    for p in FONTS[kind]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    raise FileNotFoundError("한글 폰트 없음: " + ", ".join(FONTS[kind]))


def parse(title):
    """'[롯데온] 삼양 파스타 32봉 (14,490원/무료)' -> ('롯데온', '삼양 파스타 32봉', '14,490원/무료')"""
    store = re.match(r"\s*\[(.+?)\]", title)
    prices = re.findall(r"\(([^()]*원[^()]*)\)", title)  # 괄호 안에 '원' 들어간 마지막 묶음 = 가격
    name = title[store.end():] if store else title
    if prices:
        name = name.replace(f"({prices[-1]})", " ")
    return (store.group(1) if store else "", re.sub(r"\s+", " ", name).strip() or title, prices[-1] if prices else "")


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


def make(titles, date_label, out):
    """titles: 딜 제목 리스트(최대 6개 사용). date_label: '10월 5일'. out: 저장 경로. -> out"""
    im = Image.new("RGB", (W, H), BG)
    px = im.load()
    for y in range(230):  # 상단 그라데이션 띄
        for x in range(W):
            t = x / W * 0.6 + y / 230 * 0.4
            px[x, y] = (int(255 - 30 * t), int(90 - 50 * t), int(40 + 10 * t))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((60, 55, 180, 175), radius=26, fill="white")
    f = font("bold", 78); d.text((120 - d.textlength("딜", font=f) / 2, 52), "딜", font=f, fill=ORANGE)
    f = font("bold", 30); d.text((120 - d.textlength("pick", font=f) / 2, 128), "pick", font=f, fill=ORANGE)
    d.text((215, 62), f"{date_label} 핫딜 모음", font=font("bold", 58), fill="white")
    d.text((218, 140), "오늘의 딜 pick이 고른 살 만한 딜", font=font("reg", 30), fill=(255, 230, 220))

    y, fb, fr, fs, fp = 270, font("bold", 38), font("reg", 26), font("bold", 24), font("bold", 32)
    for n, t in enumerate(titles[:6], 1):
        store, name, price = parse(t)
        lines = wrap(d, name, fb, 760)
        h = 70 + 48 * len(lines) + (46 if price else 0)
        if y + h > H - 230:  # 하단 박스 침범하면 그만
            break
        d.rounded_rectangle((60, y, W - 60, y + h), radius=22, fill="white")
        d.ellipse((90, y + 30, 150, y + 90), fill=ORANGE)
        d.text((120 - d.textlength(str(n), font=fp) / 2, y + 40), str(n), font=fp, fill="white")
        ty = y + 26
        if store:
            d.text((180, ty), store, font=fs, fill=ORANGE); ty += 36
        for ln in lines:
            d.text((180, ty), ln, font=fb, fill=INK); ty += 48
        if price:
            d.text((180, ty + 4), price.replace("/", " · "), font=fr, fill=RED)
        y += h + 18

    d.rounded_rectangle((60, H - 200, W - 60, H - 70), radius=22, fill=INK)
    d.text((100, H - 178), "전체 딜 · 구매 링크  →  hotdealpick.kr", font=font("bold", 36), fill="white")
    d.text((100, H - 122), "실시간 알림  t.me/hotdeal_pick   |   네이버 블로그  blog.naver.com/hotdeal_pick", font=font("reg", 24), fill=(200, 200, 200))
    d.text((60, H - 52), "쿠팡 파트너스 활동의 일환으로 일정 수수료를 받을 수 있습니다. 가격·재고는 게시 시점 기준.", font=font("reg", 20), fill=GRAY)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    im.save(out, optimize=True)
    return out


RW, RH, FPS = 1080, 1920, 30  # 릴스 세로 영상
DARK = (20, 21, 24)


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


def _gradient():
    im = Image.new("RGB", (RW, RH))
    px = im.load()
    for y in range(RH):
        c = (int(255 - 25 * y / RH), int(100 - 55 * y / RH), int(40 + 10 * y / RH))
        for x in range(RW):
            px[x, y] = c
    return im


def _text(s, f, fill):
    """글자 한 줄 -> 딱 맞는 RGBA 이미지"""
    w, h = int(f.getlength(s)) + 8, int(f.size * 1.35)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4, 0), s, font=f, fill=fill)
    return im


def _fit(s, kind, size, width):
    """width 안에 들어갈 때까지 글자 크기 줄임"""
    while size > 30 and font(kind, size).getlength(s) > width:
        size -= 4
    return font(kind, size)


def _check_line(s):
    """✓ + 짧은 문장 (체크는 도형으로 그림: 나눔고딕에 ✓ 글리프 없음)"""
    fr = font("bold", 50)
    s = s if fr.getlength(s) <= 780 else s[:max(1, int(len(s) * 780 / fr.getlength(s)) - 1)] + "…"
    im = Image.new("RGBA", (880, 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 8, 60, 68), fill=(60, 190, 110))
    d.line([(14, 38), (26, 51), (47, 25)], fill="white", width=7, joint="curve")
    d.text((84, 6), s, font=fr, fill="white")
    return im


def _put(frame, img, cx, cy, scale=1.0, alpha=1.0):
    if alpha <= 0:
        return
    if scale != 1.0:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BILINEAR)
    if alpha < 1.0:
        img = img.copy()
        img.putalpha(img.getchannel("A").point(lambda a: int(a * alpha)))
    frame.paste(img, (int(cx - img.width / 2), int(cy - img.height / 2)), img)


def _ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def _back(x):  # 살짝 튀어나왔다 자리잡기
    x = max(0.0, min(1.0, x))
    return 1 + 2.7 * (x - 1) ** 3 + 1.7 * (x - 1) ** 2


def reel(items, date_label, out):
    """'사고 싶고, 합리적인 소비라고 느껴지게' 15초 1080x1920 MP4 (소리 없음 -> 인스타에서 음악 추가). -> out
    items: [{"title", "comment", "e": 이모지, "hook": 첫 화면 한 줄, "pts": 합리적인 이유 2~3개}] 최대 3개 (e·hook·pts 없으면 제목·코멘트로 대신)
    흐름: 1위 딜 숫자 훅 2초 -> 딜마다 3.5초(이모지 등장 -> 가격 도장 -> 이유 체크 하나씩) -> 저장·공유 유도 2.5초.
    글자는 인스타 UI가 덮는 위(~250px)·아래(~420px)를 피해서 배치."""
    import subprocess
    items = [dict(it) for it in items[:3]]
    for it in items:
        store, name, price = parse(it["title"])
        main, _, ship = price.partition("/")
        ship = "무료배송" if ship.strip() in ("무료", "무배", "무료배송") else ship.strip()
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", it.get("comment") or "") if s.strip()]
        it.update(store=store, name=name, main=main.strip(), ship=ship,
                  pts=[p for p in (it.get("pts") or sents) if p.replace(" ", "") != ship.replace(" ", "")][:3],  # 배송은 따로 표시
                  hook=it.get("hook") or f"{name[:12]} {main.strip()}".strip())
    dark = Image.new("RGB", (RW, RH), DARK)
    glow = Image.new("RGBA", (RW, RH), (0, 0, 0, 0))  # 이모지 뒤 은은한 빛
    ImageDraw.Draw(glow).ellipse((290, 275, 790, 775), fill=(255, 110, 40, 120))
    from PIL import ImageFilter
    dark.paste(glow.filter(ImageFilter.GaussianBlur(90)), (0, 0), glow.filter(ImageFilter.GaussianBlur(90)))
    orange = _gradient()
    scenes = []  # (배경, 초, 그리기 함수(frame, t))

    top = items[0] if items else {"hook": "오늘의 핫딜", "e": "🛒"}
    i_emo, i_hook = emoji(top.get("e"), 280), _text(top["hook"], _fit(top["hook"], "bold", 120, 940), "white")
    i_t1, i_t2 = _text(f"{date_label} 가성비 1위", font("bold", 56), (255, 232, 220)), _text(f"살 만한 딜 TOP {len(items)}  끝까지 보기", font("reg", 48), "white")

    def intro(fr, t):
        _put(fr, i_t1, RW / 2, 400, alpha=_ease(t / 0.3))
        _put(fr, i_emo, RW / 2, 650, scale=0.4 + 0.6 * _back(t / 0.45) + 0.04 * t)
        _put(fr, i_hook, RW / 2, 950, scale=1.35 - 0.35 * _ease((t - 0.35) / 0.25), alpha=_ease((t - 0.35) / 0.2))
        _put(fr, i_t2, RW / 2, 1110, alpha=_ease((t - 0.9) / 0.3))
    scenes.append((orange, 2.0, intro))

    for n, it in enumerate(items, 1):
        head = Image.new("RGBA", (940, 110), (0, 0, 0, 0))
        d = ImageDraw.Draw(head)
        d.rounded_rectangle((0, 10, 150, 100), radius=45, fill=ORANGE)
        f = font("bold", 56); d.text((75 - d.textlength(f"{n}위", font=f) / 2, 20), f"{n}위", font=f, fill="white")
        if it["store"]:
            d.text((180, 22), it["store"], font=font("bold", 56), fill=(255, 150, 110))
        fb = font("bold", 66)
        name = Image.new("RGBA", (940, 200), (0, 0, 0, 0))
        for k, ln in enumerate(wrap(ImageDraw.Draw(name), it["name"], fb, 930, 2)):
            ImageDraw.Draw(name).text((0, k * 88), ln, font=fb, fill="white")
        price = _text(it["main"], _fit(it["main"], "bold", 150, 900), (255, 214, 60)) if it["main"] else None
        ship = _text(it["ship"], font("bold", 50), (150, 225, 160)) if it["ship"] else None
        emo, checks = emoji(it.get("e"), 280), [_check_line(p) for p in it["pts"]]
        box_h = 106 + 84 * len(checks)  # '이 가격이 괜찮은 이유' + 체크 줄
        box = Image.new("RGBA", (960, box_h), (0, 0, 0, 0))
        ImageDraw.Draw(box).rounded_rectangle((0, 0, 959, box_h - 1), radius=28, fill=(255, 255, 255, 28))
        ImageDraw.Draw(box).text((40, 26), "이 가격이 괜찮은 이유", font=font("bold", 42), fill=(255, 190, 150))

        def deal(fr, t, head=head, name=name, price=price, ship=ship, emo=emo, checks=checks, box_h=box_h, box=box):
            a, dy = _ease(t / 0.3), 40 * (1 - _ease(t / 0.3))
            _put(fr, head, RW / 2, 280 + dy, alpha=a)
            _put(fr, emo, RW / 2, 525, scale=0.5 + 0.5 * _back(t / 0.45) + 0.015 * t)
            _put(fr, name, RW / 2, 820 + dy, alpha=a)
            if price:
                _put(fr, price, RW / 2, 990, scale=1.4 - 0.4 * _ease((t - 0.45) / 0.25), alpha=_ease((t - 0.45) / 0.15))
            if ship:
                _put(fr, ship, RW / 2, 1105, alpha=_ease((t - 0.65) / 0.2))
            if checks and t > 0.8:
                _put(fr, box, RW / 2, 1165 + box_h / 2, alpha=_ease((t - 0.8) / 0.2))
            for k, c in enumerate(checks):
                tk = (t - 0.95 - 0.3 * k) / 0.2
                _put(fr, c, RW / 2 + 30 * (1 - _ease(tk)), 1261 + 84 * k + 40, alpha=_ease(tk))
        scenes.append((dark, 3.5, deal))

    o = [(_text("필요한 친구에게 보내주세요", font("bold", 70), "white"), 600),
         (_text("저장해두고 장보기 전에 확인", font("bold", 70), "white"), 700),
         (_text("매일 밤 9시 가성비 TOP3", font("reg", 52), (255, 232, 220)), 840),
         (_text("전체 딜 · 구매 링크는 프로필 링크", font("bold", 62), "white"), 1000),
         (_text("hotdealpick.kr", font("bold", 72), (255, 236, 160)), 1100),
         (_text("텔레그램 실시간 알림 @hotdeal_pick", font("reg", 46), "white"), 1210),
         (_text("일부 링크는 제휴 링크로 수수료를 받을 수 있어요", font("reg", 34), (255, 220, 205)), 1360)]

    def outro(fr, t):
        for k, (im, y) in enumerate(o):
            _put(fr, im, RW / 2, y + 30 * (1 - _ease((t - 0.08 * k) / 0.3)), alpha=_ease((t - 0.08 * k) / 0.3))
    scenes.append((orange, 2.5, outro))

    total = sum(s for _, s, _ in scenes)
    cmd = [ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{RW}x{RH}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "veryfast", "-movflags", "+faststart", out]
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    proc, t0 = subprocess.Popen(cmd, stdin=subprocess.PIPE), 0.0
    for bg, sec, draw in scenes:
        for i in range(int(sec * FPS)):
            frame = bg.copy()
            draw(frame, i / FPS)
            d = ImageDraw.Draw(frame)  # 위쪽 진행 막대 (스토리처럼)
            d.rounded_rectangle((60, 150, RW - 60, 160), radius=5, fill=(90, 90, 95))
            d.rounded_rectangle((60, 150, 60 + (RW - 120) * (t0 + i / FPS) / total, 160), radius=5, fill="white")
            proc.stdin.write(frame.tobytes())
        t0 += sec
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
