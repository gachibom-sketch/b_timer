import math
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from goals import star_fill

# 화면3 카드 그림 — 9:16(1080×1920) PNG 를 파이썬에서 그림 (PRD 6판, 스티치 시안 3D·3E)
# 진행 카드: 차오른 별과 희미한 남은 자리(선 없음) · 완성 카드: 선으로 이어진 별자리와 덤 별
# 미리보기와 "이미지 저장"으로 내려받는 파일이 같은 그림이 되도록 둘 다 이 그림을 씀
# 배포할 서버에는 한글 글꼴이 없을 수 있어 Noto Sans KR 을 fonts 폴더에 함께 둠 (SIL Open Font License, fonts/OFL.txt)

WIDTH, HEIGHT = 1080, 1920
FONT_PATH = Path(__file__).with_name("fonts") / "NotoSansKR.ttf"
SKY_TOP, SKY_BOTTOM = (14, 20, 48), (28, 38, 80)  # 화면2 밤하늘과 같은 #0E1430 → #1C2650
BOARD_LEFT, BOARD_TOP, BOARD_SIDE = 110, 190, 860  # 별자리 판 — 카드 위쪽 가운데 정사각형 (constellations.py 의 자리 값이 판 기준 %)
LINE_COLOR = (255, 239, 77)  # 달빛 노랑 #FFEF4D — 완성 선
TEXT_COLORS = {"title": (255, 255, 255), "record": (255, 233, 166), "footer": (174, 180, 198), "address": (135, 144, 166)}
ZOOM = 2  # 두 배 크기로 그린 뒤 줄여 가장자리를 매끈하게


def font(size, weight):  # 이 글꼴은 굵기를 정하지 않으면 가장 가는 굵기(Thin)로 그려짐
    face = ImageFont.truetype(FONT_PATH, size)
    face.set_variation_by_name(weight)
    return face


def sky_background():  # 위에서 아래로 짙은 남색 → 남색
    column = Image.new("RGB", (1, HEIGHT))
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        column.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(SKY_TOP, SKY_BOTTOM)))
    return column.resize((WIDTH, HEIGHT))


def sparkle(cx, cy, r):  # 네 갈래로 빛나는 별 모양 — 화면2 밤하늘 별과 같은 모양
    points = []
    for i in range(16):
        angle = math.pi / 8 * i - math.pi / 2
        reach = r if i % 4 == 0 else r * (0.32 if i % 2 == 0 else 0.22)
        points.append((cx + reach * math.cos(angle), cy + reach * math.sin(angle)))
    return points


def draw_constellation(constellation, set_count, target):  # 별자리 판만 그린 투명한 층 (빛 번짐 포함)
    size = (WIDTH * ZOOM, HEIGHT * ZOOM)
    shapes = Image.new("RGBA", size, (0, 0, 0, 0))
    lines = Image.new("RGBA", size, (0, 0, 0, 0))
    halos = Image.new("RGBA", size, (0, 0, 0, 0))  # 별 둘레에 번질 둥근 빛
    pen, line_pen, halo_pen = ImageDraw.Draw(shapes), ImageDraw.Draw(lines), ImageDraw.Draw(halos)

    def at(pos):
        return (BOARD_LEFT + pos[0] / 100 * BOARD_SIDE) * ZOOM, (BOARD_TOP + pos[1] / 100 * BOARD_SIDE) * ZOOM

    stars = constellation["stars"]
    lit, part, bonus = star_fill(set_count, target, len(stars))
    done = set_count >= target
    if done:
        for a, b in constellation["lines"]:
            line_pen.line([at(stars[a]["pos"]), at(stars[b]["pos"])], fill=LINE_COLOR + (215,), width=5 * ZOOM)
    unit = BOARD_SIDE / 100 * ZOOM  # 판 1% 의 크기
    for i, star in enumerate(stars):
        x, y = at(star["pos"])
        amount = 1 if i < lit else part if i == lit else 0
        if amount < 1:  # 아직 다 차지 않은 자리 — 희미한 점과 고리
            ring, dot = 2.2 * unit, 0.7 * unit
            pen.ellipse([x - ring, y - ring, x + ring, y + ring], outline=(255, 255, 255, 60), width=round(0.35 * unit))
            pen.ellipse([x - dot, y - dot, x + dot, y + dot], fill=(255, 255, 255, 95))
        if amount > 0.001:
            color = tuple(int(star["color"][k:k + 2], 16) for k in (1, 3, 5))
            r = 1.35 * (1.3 + 1.5 * star["size"]) * unit * (1 if amount == 1 else 0.45 + 0.4 * amount)  # 카드는 화면보다 조금 크게
            alpha = 1 if amount == 1 else 0.35 + 0.5 * amount
            pen.polygon(sparkle(x, y, r), fill=color + (round(255 * alpha),))
            halo = r * 0.75
            halo_pen.ellipse([x - halo, y - halo, x + halo, y + halo], fill=color + (round(170 * alpha),))
    for pos in [b["pos"] for b in constellation["bonus"]][:bonus]:  # 덤 별 — 선 없는 작은 흰 점
        x, y = at(pos)
        r = 1.0 * unit
        pen.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 235))
        halo_pen.ellipse([x - 1.6 * r, y - 1.6 * r, x + 1.6 * r, y + 1.6 * r], fill=(255, 255, 255, 120))

    glow = halos.filter(ImageFilter.GaussianBlur(14 * ZOOM))  # 별 둘레의 은은한 빛
    layer = Image.alpha_composite(Image.alpha_composite(lines, glow), shapes)
    return layer.resize((WIDTH, HEIGHT), Image.LANCZOS)


def draw_watermark():  # 시연 모드 카드의 "DEMO" 글자만 칠한 판 — 가운데에 비스듬히, 옅게(25%)
    mark = Image.new("L", (WIDTH, HEIGHT), 0)
    ImageDraw.Draw(mark).text((WIDTH / 2, HEIGHT / 2), "DEMO", font=font(280, "Bold"), fill=64, anchor="mm")
    return mark.rotate(30, resample=Image.BICUBIC)  # 카드 가운데를 축으로 왼쪽 아래 → 오른쪽 위로 기울임


def card_png(constellation, set_count, target, title, record, address, demo=False):
    # constellation: constellations.py 의 별자리 하나 · set_count / target: 그 기간의 세트 수 / 목표 세트 수
    # title: "북두칠성 · 별 3개" · "북두칠성 완성" · record: "10월 넷째 주 · 3/7세트" · address: 배포 주소
    # demo: 시연 모드면 "DEMO" 워터마크를 얹음
    card = sky_background().convert("RGBA")
    card = Image.alpha_composite(card, draw_constellation(constellation, set_count, target))

    pen = ImageDraw.Draw(card)
    middle = WIDTH / 2
    title_size = 84
    while title_size > 48 and pen.textlength(title, font=font(title_size, "Bold")) > WIDTH - 160:  # 긴 제목은 카드 폭에 맞게 줄임
        title_size -= 4
    pen.text((middle, 1300), title, font=font(title_size, "Bold"), fill=TEXT_COLORS["title"], anchor="mm")
    pen.text((middle, 1410), record, font=font(48, "Regular"), fill=TEXT_COLORS["record"], anchor="mm")
    pen.line([(140, 1610), (WIDTH - 140, 1610)], fill=(255, 255, 255, 40), width=2)
    pen.text((middle, 1700), "별모도로 · 별자리를 완성하는 집중 타이머", font=font(42, "Regular"), fill=TEXT_COLORS["footer"], anchor="mm")
    pen.text((middle, 1770), address, font=font(40, "Regular"), fill=TEXT_COLORS["address"], anchor="mm")
    if demo:  # 시연으로 만든 카드가 실제 기록 카드로 오해받지 않게
        white = Image.new("RGBA", (WIDTH, HEIGHT), (255, 255, 255, 255))
        card.paste(white, mask=draw_watermark())

    buffer = BytesIO()
    card.convert("RGB").save(buffer, "PNG")
    return buffer.getvalue()
