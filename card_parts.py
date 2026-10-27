import math
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# 화면3 카드 그림 — 9:16(1080×1920) PNG 를 파이썬에서 그림 (와이어프레임 3-A)
# 미리보기와 "이미지 저장"으로 내려받는 파일이 같은 그림이 되도록 둘 다 이 그림을 씀
# 배포할 서버에는 한글 글꼴이 없을 수 있어 Noto Sans KR 을 fonts 폴더에 함께 둠 (SIL Open Font License, fonts/OFL.txt)

WIDTH, HEIGHT = 1080, 1920
SCALE = 4  # 화면 미리보기(270×480) 기준 크기를 카드 크기로 키우는 배수
FONT_PATH = Path(__file__).with_name("fonts") / "NotoSansKR.ttf"
BACKGROUND = (31, 31, 36)  # 화면2 밤하늘과 같은 #1f1f24
TEXT_COLORS = {"title": (255, 255, 255), "subtitle": (204, 204, 204), "name": (153, 153, 153), "date": (119, 119, 119)}


def font(size, weight):  # 이 글꼴은 굵기를 정하지 않으면 가장 가는 굵기(Thin)로 그려짐
    face = ImageFont.truetype(FONT_PATH, size)
    face.set_variation_by_name(weight)
    return face


def star_points(cx, cy, radius):  # 꼭짓점 하나가 위를 향한 별(★)의 바깥·안쪽 꼭짓점 10개
    points = []
    for i in range(10):
        r = radius if i % 2 == 0 else radius * 0.4
        angle = math.pi / 5 * i - math.pi / 2
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return points


def draw_stars(layers, counts):  # 별 모양만 흰색으로 칠한 판 — 두 배 크기로 그린 뒤 줄여 가장자리를 매끈하게
    big = Image.new("L", (WIDTH * 2, HEIGHT * 2), 0)
    pen = ImageDraw.Draw(big)
    for layer, n in zip(layers, counts):
        size = layer["size"] * SCALE * 2
        for left, top in layer["slots"][:n]:
            cx, cy = left / 100 * WIDTH * 2, top / 100 * HEIGHT * 2
            if layer["mark"] == "●":  # 작은별은 동그란 점
                r = size * 0.35
                pen.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
            else:
                pen.polygon(star_points(cx, cy, size * 0.5), fill=255)
    return big.resize((WIDTH, HEIGHT), Image.LANCZOS)


def draw_watermark():  # 시연 모드 카드의 "DEMO" 글자만 칠한 판 — 가운데에 비스듬히, 옅게(25%)
    mark = Image.new("L", (WIDTH, HEIGHT), 0)
    ImageDraw.Draw(mark).text((WIDTH / 2, HEIGHT / 2), "DEMO", font=font(280, "Bold"), fill=64, anchor="mm")
    return mark.rotate(30, resample=Image.BICUBIC)  # 카드 가운데를 축으로 왼쪽 아래 → 오른쪽 위로 기울임


def card_png(layers, counts, title, subtitle, date, demo=False):
    # layers: 작은별부터 대왕별까지 모양·크기·10자리(왼쪽 %, 위 %) · counts: 종류마다 그릴 개수
    # title: "23세트" · subtitle: "총 9시간 35분 집중" · date: "2026.10.27 기준" · demo: 시연 모드면 "DEMO" 워터마크를 얹음
    card = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    white = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
    stars = draw_stars(layers, counts)
    glow = stars.filter(ImageFilter.GaussianBlur(14)).point(lambda v: v * 7 // 10)  # 별 둘레의 은은한 빛
    card.paste(white, mask=glow)
    card.paste(white, mask=stars)

    pen = ImageDraw.Draw(card)
    middle = WIDTH / 2
    pen.text((middle, 1523), title, font=font(104, "Bold"), fill=TEXT_COLORS["title"], anchor="mm")
    pen.text((middle, 1641), subtitle, font=font(52, "Regular"), fill=TEXT_COLORS["subtitle"], anchor="mm")
    pen.text((middle, 1772), "별도로", font=font(48, "Regular"), fill=TEXT_COLORS["name"], anchor="mm")
    pen.text((middle, 1838), date, font=font(40, "Regular"), fill=TEXT_COLORS["date"], anchor="mm")  # 누적 수가 어느 날까지인지
    if demo:  # 시연으로 만든 카드가 실제 기록 카드로 오해받지 않게
        card.paste(white, mask=draw_watermark())

    buffer = BytesIO()
    card.save(buffer, "PNG")
    return buffer.getvalue()
