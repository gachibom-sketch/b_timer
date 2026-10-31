# 목표 별자리 계산 — 기간 시작일 · 지금 목표 찾기 · 저절로 정하기 · 진행 줄 (저장은 app.py 가 함, 구조는 idea/목표 기록 구조.md)
# 목표 한 줄: {"constellation": "orion", "period": "하루", "period_start": "2026-10-31", "target": 3, "set_count": 0, "source": "추천"}
import math
from datetime import date, timedelta

from constellations import BONUS_COUNT, BY_KEY, FIRST

PERIOD_WORD = {"하루": "오늘", "한 주": "이번 주"}  # 진행 줄 끝말
WEEK_ORDER = ["첫째", "둘째", "셋째", "넷째", "다섯째"]


def star_fill(set_count, target, stars):  # 달성률만큼 앞 별부터 차오름 → (다 켜진 별 수, 다음 별 밝기 0~1, 덤 별 수)
    # 예: 오리온자리(별 7개) 하루 3세트에 1세트 → 7 × 1/3 = 2.33 → 별 2개와 셋째 별 33% (PRD 6판)
    ratio = min(set_count / target, 1)
    lit = math.floor(ratio * stars + 1e-9)  # 3/3 × 7 처럼 딱 맞을 때 7.0 이 6.999… 로 모자라지 않게
    part = 0 if lit >= stars else ratio * stars - lit
    return lit, round(part, 3), min(max(set_count - target, 0), BONUS_COUNT)


def period_label(goal):  # 지난 별자리 · 카드의 기간 — 하루: "10월 29일", 한 주: "10월 넷째 주" (그 주 월요일이 그달 몇째 월요일인지)
    start = date.fromisoformat(goal["period_start"])
    if goal["period"] == "하루":
        return f"{start.month}월 {start.day}일"
    return f"{start.month}월 {WEEK_ORDER[(start.day - 1) // 7]} 주"


def period_start(period, day):  # 그날이 든 기간의 시작일 — 하루는 그날, 한 주는 그 주 월요일 (달력 한 주)
    return day if period == "하루" else day - timedelta(days=day.weekday())


def new_goal(key, day, source):  # 그 별자리에 붙은 목표로 그날이 든 기간의 새 목표 — source 는 추천 · 이어서 · 고름
    constellation = BY_KEY[key]
    return {
        "constellation": key,
        "period": constellation["period"],
        "period_start": period_start(constellation["period"], day).isoformat(),
        "target": constellation["goal"],
        "set_count": 0,
        "source": source,
    }


def covers(goal, day):  # 그 목표의 기간이 그날을 품는지
    return goal["period_start"] == period_start(goal["period"], day).isoformat()


def same_period(goal, key):  # key = [기간 종류, 기간 시작일] — 세트를 시작할 때 기억해 둔 목표인지
    return [goal["period"], goal["period_start"]] == list(key)


def find_current(goals, day):  # 목표 줄(오래된 것부터) 가운데 그날을 품는 마지막 줄, 없으면 None
    return next((goal for goal in reversed(goals) if covers(goal, day)), None)


def next_goal(goals, day):  # 지금 기간 목표가 없을 때 저절로 정하는 목표 — 처음이면 추천, 그 뒤에는 지난번 별자리와 같은 목표
    if not goals:
        return new_goal(FIRST, day, "추천")
    return new_goal(goals[-1]["constellation"], day, "이어서")


def progress_text(goal):  # "오리온자리 · 1/3세트 · 오늘"
    name = BY_KEY[goal["constellation"]]["name"]
    return f"{name} · {goal['set_count']}/{goal['target']}세트 · {PERIOD_WORD[goal['period']]}"


def locked_text(goal):  # 화면0 — 이번 기간에 마친 세트가 있어 목표를 바꿀 수 없을 때 "오늘 마친 세트가 있어서 목표는 내일 바꿀 수 있어요"
    later = {"하루": "내일", "한 주": "다음 주에"}[goal["period"]]
    return f"{PERIOD_WORD[goal['period']]} 마친 세트가 있어서 목표는 {later} 바꿀 수 있어요"


def sky_text(goal):  # 화면2 진행 줄 — 완성 전에는 progress_text, 완성 뒤에는 "오리온자리 완성 · 덤 별 1개 · 오늘" (시안 2F)
    extra = goal["set_count"] - goal["target"]
    if extra < 0:
        return progress_text(goal)
    name, when = BY_KEY[goal["constellation"]]["name"], PERIOD_WORD[goal["period"]]
    return f"{name} 완성 · 덤 별 {extra}개 · {when}" if extra else f"{name} 완성 · {when}"


def focus_time_text(count):  # 끝까지 마친 세트 × 25분 → "2시간 55분"
    hours, minutes = divmod(count * 25, 60)
    if hours and minutes:
        return f"{hours}시간 {minutes}분"
    if hours:
        return f"{hours}시간"
    return f"{minutes}분"


def card_words(goal):  # 화면3 카드의 (제목, 기록 줄) — PRD 6판
    constellation = BY_KEY[goal["constellation"]]
    count, target = goal["set_count"], goal["target"]
    if count >= target:  # 완성 카드 — "북두칠성 완성", "10월 넷째 주 · 7세트 · 집중 2시간 55분"
        return f"{constellation['name']} 완성", f"{period_label(goal)} · {count}세트 · 집중 {focus_time_text(count)}"
    lit, _, _ = star_fill(count, target, len(constellation["stars"]))  # 진행 카드 — "북두칠성 · 별 3개", "10월 넷째 주 · 3/7세트"
    title = f"{constellation['name']} · 별 {lit}개" if lit else f"{constellation['name']} · 첫 별이 차오르는 중"
    return title, f"{period_label(goal)} · {count}/{target}세트"


def past_text(goal):  # 지난 별자리 한 줄의 설명 — 실패라는 말 없이 (PRD 6판: "카시오페이아자리를 별 3개까지 그렸어요")
    if goal["set_count"] >= goal["target"]:
        return "완성했어요"
    lit, _, _ = star_fill(goal["set_count"], goal["target"], len(BY_KEY[goal["constellation"]]["stars"]))
    return f"별 {lit}개까지 그렸어요" if lit else "첫 별을 그리기 시작했어요"
