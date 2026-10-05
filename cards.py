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


def _slide(bg, draw_fn):
    """배경색/그라데이션 + 내용(RGBA 레이어) -> (배경, 내용)"""
    base = Image.new("RGB", (RW, RH), DARK)
    if bg == "orange":
        px = base.load()
        for y in range(RH):
            c = (int(255 - 25 * y / RH), int(100 - 55 * y / RH), int(40 + 10 * y / RH))
            for x in range(RW):
                px[x, y] = c
    layer = Image.new("RGBA", (RW, RH), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    box = layer.getbbox()  # 내용 덩어리를 화면 가운데(인스타 UI 안 덮는 곳)로
    if box:
        moved = Image.new("RGBA", (RW, RH), (0, 0, 0, 0))
        moved.paste(layer, (0, int(RH * 0.46 - (box[1] + box[3]) / 2)))
        layer = moved
    return base, layer


def _center(d, y, text, f, fill):
    d.text(((RW - d.textlength(text, font=f)) / 2, y), text, font=f, fill=fill)


def reel(items, date_label, out):
    """items: [(딜 제목, 한 줄 코멘트)] 최대 3개. 15초 내외 1080x1920 MP4 (소리 없음 -> 인스타에서 음악 추가). -> out
    화면 위·아래(인스타 UI가 덮는 곳)는 비우고 가운데에만 글자."""
    import subprocess
    items = items[:3]
    slides = []  # (배경, 내용, 초)

    def intro(d):
        _center(d, 560, date_label, font("reg", 60), "white")
        _center(d, 680, "오늘 놓치면 아까운", font("bold", 84), "white")
        _center(d, 820, f"핫딜 TOP {len(items)}", font("bold", 170), "white")
        _center(d, 1080, "딜 pick이 골랐어요", font("reg", 52), (255, 228, 215))
    slides.append((*_slide("orange", intro), 2.0))

    for n, (title, comment) in enumerate(items, 1):
        store, name, price = parse(title)
        main, _, ship = price.partition("/")
        ship = "무료배송" if ship.strip() in ("무료", "무배", "무료배송") else ship.strip()

        def deal(d, n=n, store=store, name=name, main=main, ship=ship, comment=comment):
            d.ellipse((90, 330, 230, 470), fill=ORANGE)
            f = font("bold", 90); d.text((160 - d.textlength(str(n), font=f) / 2, 342), str(n), font=f, fill="white")
            if store:
                d.text((260, 365), store, font=font("bold", 64), fill=ORANGE)
            y, fb = 540, font("bold", 84)
            for ln in wrap(d, name, fb, 880, 3):
                d.text((90, y), ln, font=fb, fill="white"); y += 108
            if main:
                d.text((90, y + 40), main.strip(), font=font("bold", 150), fill=(255, 210, 60)); y += 230
            if ship:
                d.text((96, y), ship, font=font("bold", 56), fill=(170, 230, 170)); y += 90
            fr = font("reg", 46)
            for ln in wrap(d, comment, fr, 880, 3):
                d.text((90, y + 30), ln, font=fr, fill=(200, 200, 205)); y += 64
        slides.append((*_slide("dark", deal), 3.5))

    def outro(d):
        _center(d, 600, "전체 딜 · 구매 링크는", font("bold", 80), "white")
        _center(d, 720, "프로필 링크에서", font("bold", 80), "white")
        _center(d, 900, "hotdealpick.kr", font("bold", 72), (255, 236, 160))
        _center(d, 1040, "텔레그램 실시간 알림 @hotdeal_pick", font("reg", 48), "white")
        _center(d, 1120, "팔로우하면 매일 골라드려요", font("reg", 48), "white")
        _center(d, 1300, "일부 링크는 제휴 링크로 수수료를 받을 수 있어요", font("reg", 34), (255, 220, 205))
    slides.append((*_slide("orange", outro), 2.5))

    total = sum(s for *_, s in slides)
    cmd = [ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{RW}x{RH}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-preset", "veryfast", "-movflags", "+faststart", out]
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    proc, t0 = subprocess.Popen(cmd, stdin=subprocess.PIPE), 0.0
    for base, layer, sec in slides:
        done = None
        for i in range(int(sec * FPS)):
            t = i / FPS
            if t >= 0.35 and done:
                frame = done.copy()
            else:  # 처음 0.35초: 아래에서 살짝 올라오며 나타남
                k = min(1.0, t / 0.35)
                lay = layer.copy()
                lay.putalpha(layer.getchannel("A").point(lambda a, k=k: int(a * k)))
                frame = base.copy()
                frame.paste(lay, (0, int(60 * (1 - k) ** 2)), lay)
                if k == 1.0:
                    done = frame.copy()
            d = ImageDraw.Draw(frame)  # 위쪽 진행 막대 (스토리처럼)
            d.rounded_rectangle((60, 150, RW - 60, 160), radius=5, fill=(90, 90, 95))
            d.rounded_rectangle((60, 150, 60 + (RW - 120) * (t0 + t) / total, 160), radius=5, fill="white")
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
