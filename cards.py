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
    lines, cur = [], ""
    for ch in text:
        if d.textlength(cur + ch, font=f) > width:
            lines.append(cur)
            cur = ch
            if len(lines) == max_lines:
                lines[-1] = lines[-1][:-1] + "…"
                return lines
        else:
            cur += ch
    return lines + ([cur] if cur else [])


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


if __name__ == "__main__":
    import json, sys, time
    from build_site import title_of
    posts = json.load(open("posts.json")) if os.path.exists("posts.json") else []
    kst = time.gmtime(time.time() + 9 * 3600)
    print(make([title_of(p["text"]) for p in posts], f"{kst.tm_mon}월 {kst.tm_mday}일", sys.argv[1] if len(sys.argv) > 1 else "card.png"))
