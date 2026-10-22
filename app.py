import math
import os
import random
import re
import time
from datetime import datetime, timedelta, timezone

import requests
import streamlit as st
from dotenv import load_dotenv

from browser_store import browser_store
from chatbot import chatbot
from timer_parts import set_engine, timer_dial

st.set_page_config(page_title="별도로")
st.sidebar.write("집중 25분과 휴식 5분을 마칠 때마다 밤하늘에 별을 띄워 줍니다.")

# 누적 세트 수는 Supabase 의 progress 표에 테스터마다 한 줄씩 저장함
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error(".env 에 SUPABASE_URL 과 SUPABASE_KEY 를 넣어 주세요.")
    st.stop()

PROGRESS_URL = f"{SUPABASE_URL}/rest/v1/progress"
EVENT_URL = f"{SUPABASE_URL}/rest/v1/event_log"  # 분석 이벤트 4개 — 날짜·시각·테스터·이벤트 (판정 지표 ①~④ 를 셈)
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
KST = timezone(timedelta(hours=9))  # 이벤트 날짜·시각은 한국 시각으로 남김
DEMO_TESTER = "0"  # 시연 모드 전용 줄 — 실제 테스터 줄과 섞이지 않음 (수용 기준 19번)

# 한 세트의 단계별 길이(초) — 시연 모드(…/?demo=1)는 집중 1분 + 휴식 12초
SET_LENGTH = {"집중": 25 * 60, "휴식": 5 * 60}
DEMO_SET_LENGTH = {"집중": 60, "휴식": 12}

# 테스터 링크(…/?t=07)의 번호 — 다른 화면으로 옮겨도 주소에 남겨 둠
tester = st.query_params.get("t", st.session_state.get("tester"))
if tester and re.fullmatch(r"[0-9]{1,4}", tester) and tester != DEMO_TESTER:
    st.session_state.tester = tester
    st.query_params["t"] = tester

# 시연 모드 — 시연 링크(…/?demo=1)로 들어오거나 화면2의 "시연 모드" 단추로 켬, 켜진 동안 주소에 ?demo=1 을 남겨 둠
if "demo" not in st.session_state:
    st.session_state.demo = st.query_params.get("demo") == "1"
if st.session_state.demo:
    st.query_params["demo"] = "1"
elif "demo" in st.query_params:
    del st.query_params["demo"]

# 별 크기 범례: 별 종류마다 그리는 글자와 크기(px)
STAR_LOOK = {
    "대왕별": ("★", 34),
    "큰별": ("★", 22),
    "중간별": ("★", 13),
    "작은별": ("●", 5),
}


def star_counts(count):  # 10개씩 모이면 한 단계 큰 별로 합쳐짐
    return {
        "대왕별": count // 1000,
        "큰별": count // 100 % 10,
        "중간별": count // 10 % 10,
        "작은별": count % 10,
    }


def focus_time_text(count):  # 끝까지 마친 세트 × 25분
    hours, minutes = divmod(count * 25, 60)
    if hours and minutes:
        return f"{hours}시간 {minutes}분"
    if hours:
        return f"{hours}시간"
    return f"{minutes}분"


def parse_count(text):  # 0 이상의 정수만 받고, 아니면 None
    text = text.strip()
    if not text.isdecimal():
        return None
    try:
        return int(text)
    except ValueError:  # 너무 길어서 숫자로 바꿀 수 없음
        return None


def load_count(tester):  # progress 표에서 그 테스터의 누적 세트 수, 줄이 없으면 0
    response = requests.get(
        PROGRESS_URL,
        headers=HEADERS,
        params={"select": "set_count", "tester": f"eq.{tester}"},
        timeout=10,
    )
    response.raise_for_status()
    rows = response.json()
    return rows[0]["set_count"] if rows else 0


def save_count(tester, count):  # 그 테스터 줄이 있으면 고치고, 없으면 새로 만듦
    response = requests.post(
        PROGRESS_URL,
        headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"},
        json={"tester": tester, "set_count": count},
        timeout=10,
    )
    response.raise_for_status()


def stored_count(owner):  # Supabase 에 저장된 그 줄의 누적 세트 수
    try:
        return load_count(owner)
    except requests.RequestException:
        st.error("저장된 기록을 불러오지 못했어요. 잠시 뒤 다시 열어 주세요.")
        st.stop()


# 기록을 남기는 곳 — 테스터 링크: Supabase 가 기준이고 브라우저에 사본 · 그냥 주소: 브라우저에만 ·
# 시연 모드: Supabase 시연 줄에만 · 진행 중 세트의 시작 시각: 브라우저에만 (탭을 닫았다 열어도 이어지게)
def owner_key():  # 이 브라우저에 남기는 기록의 이름 — 테스터 번호마다 따로, 그냥 주소는 guest, 시연 모드는 남기지 않음
    if st.session_state.get("demo"):
        return None
    tester = st.session_state.get("tester")
    return f"t{tester}" if tester else "guest"


def local_record():  # 이 브라우저의 기록 — 누적 수, Supabase 에 올렸는지, 진행 중 세트의 시작 시각
    blank = {"count": 0, "synced": True, "started_at": None}
    return {**blank, **st.session_state.setdefault("local_records", {}).get(owner_key(), {})}


def keep_local(**changes):  # 브라우저 기록을 고침 — 다음에 화면을 그릴 때 브라우저 부품이 실제로 씀
    key = owner_key()
    if key is not None:
        st.session_state.setdefault("local_records", {})[key] = {**local_record(), **changes}


def sync_browser():  # 화면을 그리기 전에 브라우저 기록을 한 번 읽어 오고, 그 뒤로는 바뀐 값을 씀
    key = owner_key()
    records = st.session_state.setdefault("local_records", {})
    if key is None or key in records:
        browser_store(key, records.get(key))
        return
    saved = browser_store(key, None)
    if not saved or saved.get("key") != key:  # 브라우저가 아직 알려 주지 않음 — 0세트 화면이 깜빡이지 않게 잠깐 기다림
        st.caption("기록을 불러오는 중…")
        st.stop()
    values = saved.get("values") or {}
    records[key] = {
        "count": int(values.get("count") or 0),
        "synced": values.get("synced") is not False,
        "started_at": values.get("started_at"),
    }
    if st.session_state.get("set_started_at") is None and records[key]["started_at"]:  # 탭을 닫기 전 진행 중이던 세트를 이어 감
        st.session_state.set_started_at = float(records[key]["started_at"])


def tester_count(tester):  # 테스터는 Supabase 가 기준 — 브라우저 사본을 맞추고, 저번에 못 올린 세트가 있으면 올림
    local = local_record()
    try:
        remote = load_count(tester)
        if not local["synced"] and local["count"] > remote:
            save_count(tester, local["count"])
            remote = local["count"]
    except requests.RequestException:  # Supabase 가 안 되면 이 브라우저의 기록으로 보여 줌
        if not st.session_state.get("offline_noticed"):
            st.toast("인터넷이 불안정해 이 PC 에 남은 기록으로 보여 드려요.")
            st.session_state.offline_noticed = True
        return local["count"]
    if (local["count"], local["synced"]) != (remote, True):
        keep_local(count=remote, synced=True)
    return remote


def current_count():  # 화면에 보일 누적 세트 수
    if st.session_state.get("demo"):
        return stored_count(DEMO_TESTER)  # 시연 줄 — 브라우저에는 남기지 않음
    tester = st.session_state.get("tester")
    if tester is None:
        return local_record()["count"]  # 그냥 주소 — 이 브라우저에만 남김
    return tester_count(tester)


def set_length():  # 지금 쓰는 단계별 길이(초) — 시연 모드면 집중 1분 + 휴식 12초
    return DEMO_SET_LENGTH if st.session_state.get("demo") else SET_LENGTH


def set_phase():  # 진행 중인 세트의 (단계, 남은 초), 대기면 None — 남은 시간은 시작 시각 기준으로 계산
    started_at = st.session_state.get("set_started_at")
    if started_at is None:
        return None
    length = set_length()
    elapsed = time.time() - started_at
    if elapsed < length["집중"]:
        return "집중", length["집중"] - elapsed
    if elapsed < length["집중"] + length["휴식"]:
        return "휴식", length["집중"] + length["휴식"] - elapsed
    return "완료", 0


def set_left():  # 진행 중인 세트가 끝날 때까지 남은 초 (휴식까지)
    length = set_length()
    return length["집중"] + length["휴식"] - (time.time() - st.session_state.set_started_at)


def time_text(seconds):  # 남은 초 → "12:30"
    minutes, seconds = divmod(math.ceil(seconds), 60)
    return f"{minutes:02d}:{seconds:02d}"


def log_event(event, at=None):  # 분석 이벤트를 event_log 에 남김 — 세트 시작·세트 완료·그만하기·카드 저장 (시연 모드는 남기지 않음)
    if st.session_state.get("demo"):
        return
    moment = datetime.fromtimestamp(at or time.time(), KST)  # 일어난 시각을 직접 적음 — 늦게 보내도 시각이 틀리지 않게
    waiting = st.session_state.setdefault("pending_events", [])  # 보내지 못한 이벤트는 모아 두었다가 다음에 함께 보냄
    waiting.append({
        "date": moment.date().isoformat(),
        "time": moment.strftime("%H:%M:%S"),
        "tester": st.session_state.get("tester"),  # 그냥 주소면 비워 둠
        "event": event,
    })
    try:
        response = requests.post(EVENT_URL, headers={**HEADERS, "Prefer": "return=minimal"}, json=waiting, timeout=5)
        response.raise_for_status()
        waiting.clear()
    except requests.HTTPError as error:
        status = error.response.status_code
        if 400 <= status < 500 and status != 429:  # 다시 보내도 안 될 오류 — 계속 막히지 않게 버림
            waiting.clear()
    except requests.RequestException:
        pass  # 인터넷이 끊김 — 모아 두었다가 다음 이벤트 때 다시 보냄, 타이머는 그대로 씀


def start_set():  # 시작 · 다음 세트 시작 — 지금 시각을 세트 시작 시각으로 두고 브라우저에도 남김
    st.session_state.set_started_at = time.time()
    keep_local(started_at=st.session_state.set_started_at)
    log_event("세트 시작")


def end_set():  # 세트를 끝내고 대기로 돌아감
    st.session_state.set_started_at = None
    st.session_state.confirming = False
    keep_local(started_at=None)


def complete_set():  # 휴식까지 마친 세트만 누적 +1 (그만둔 세트는 여기에 오지 않음)
    count = current_count() + 1
    length = set_length()
    log_event("세트 완료", at=st.session_state.set_started_at + length["집중"] + length["휴식"])  # 실제로 끝난 시각 — 탭을 닫아 둔 사이 끝났어도
    end_set()
    st.session_state.pop("count_input", None)  # 시연 모드 칸도 새 누적 수로 맞춤
    if st.session_state.get("demo"):
        owner = DEMO_TESTER
    else:
        owner = st.session_state.get("tester")
        if owner is None:  # 그냥 주소 — 브라우저에만 남김
            keep_local(count=count)
            return
    try:
        save_count(owner, count)  # 서버(Supabase progress 표)에 저장
        keep_local(count=count, synced=True)
    except requests.RequestException:
        keep_local(count=count, synced=False)  # 테스터면 브라우저에 남겨 두었다가 다음에 올림
        st.session_state.set_save_failed = True


def finish_if_done(current):  # 세트 시간이 다 지났으면 세트 완료로 치고 화면2로 — 다른 탭에 갔다 오거나 탭을 닫았다 열어도 같음
    phase = set_phase()
    if phase and phase[0] == "완료":
        complete_set()
        if current.url_path != sky_page.url_path:
            st.switch_page(sky_page)
        st.rerun()  # 바뀐 기록을 바로 브라우저에 쓰도록 한 번 더 그림 — 그 전에 탭을 닫아도 세트가 두 번 세어지지 않게


def night_sky(count, height, width="100%", footer=""):
    top_limit = 55 if footer else 85  # 카드는 별이 위 2/3에만 뜸 (3-A)
    parts = []
    for kind, n in star_counts(count).items():
        mark, size = STAR_LOOK[kind]
        spot = random.Random(kind)  # 종류마다 자리가 정해져 있어, 숫자를 바꿔도 있던 별은 그 자리에 있음
        for _ in range(min(n, 10)):  # 대왕별 다음 단계가 PRD.md 에 없어서 10개까지만 그림
            left, top = spot.uniform(6, 90), spot.uniform(6, top_limit)
            parts.append(
                f'<span style="position:absolute; left:{left:.1f}%; top:{top:.1f}%; '
                f'font-size:{size}px; line-height:1; color:#fff;">{mark}</span>'
            )
    if count == 0 and not footer:
        parts.append(
            '<div style="position:absolute; inset:0; display:flex; align-items:center; '
            'justify-content:center; color:#bbb;">첫 세트를 마치면 별이 떠요</div>'
        )
    st.markdown(
        f'<div style="position:relative; height:{height}px; width:{width}; margin:0 auto; '
        f'background:#1f1f24; border-radius:8px; overflow:hidden;">{"".join(parts)}{footer}</div>',
        unsafe_allow_html=True,
    )


def set_count(value):  # D-1 빠른 값 단추 — 시연 전용 줄에 저장
    try:
        save_count(DEMO_TESTER, value)
    except requests.RequestException:
        st.session_state.save_failed = True
        st.session_state.pop("count_input", None)  # 칸을 저장된 값으로 되돌림
        return
    st.session_state.count_input = str(value)


def apply_count_input():  # D-1 누적 세트 수 칸에서 완료(엔터)를 눌렀을 때
    value = parse_count(st.session_state.count_input)
    if value is None or value > 2147483647:  # set_count 열(int4)에 담을 수 있는 가장 큰 수
        st.session_state.count_notice = True
        st.session_state.pop("count_input", None)  # 칸을 저장된 값으로 되돌림
    else:
        set_count(value)


@st.dialog("누적 세트 수를 숫자로 넣어 주세요", dismissible=False)
def count_notice():  # D-1E 누적 세트 수 안내 창
    if st.button("확인"):
        st.rerun()


@st.dialog("이번 세트는 별이 되지 않아요", dismissible=False)
def stop_confirm():  # 1-D 그만하기 확인 창 — 창이 떠 있는 동안에도 시간은 흐름
    left, right = st.columns(2)
    if left.button("그만하기", width="stretch"):
        log_event("그만하기")
        end_set()
        st.rerun()
    if right.button("계속하기", type="primary", width="stretch"):
        st.session_state.confirming = False
        st.rerun()


def ask_stop():  # 집중·휴식 중 "그만하기" — 바로 멈추지 않고 확인 창을 띄움
    st.session_state.confirming = True


@st.fragment(run_every=1)
def running_button(shown):  # 2-D 세트 진행 중 — "다음 세트 시작" 대신 남은 시간 단추, 누르면 진행 중인 화면1로
    phase = set_phase()
    if phase is None or phase[0] != shown:
        st.rerun()
    if st.button(f"{shown} 중 · {time_text(phase[1])} 남음", key="running_button", type="primary"):
        st.switch_page(timer_page)  # 새 세트는 시작하지 않음


def waiting():  # 1-A 대기(0세트) · 1-E 대기(1세트 이상)
    with st.popover("?"):
        st.write("**뽀모도로 타이머란?**")
        st.write("25분 집중과 5분 휴식을 반복하여 집중력을 높이는 시간 관리 도구입니다.")

    timer_dial("대기", 0, set_length())  # 꽉 찬 원과 집중 길이(25:00)
    count = current_count()
    if count == 0:
        st.write("25분 집중하고 5분 쉬면 밤하늘에 별이 떠요")
    else:
        st.write(f"누적 {count}세트")

    st.button("시작", type="primary", on_click=start_set)


def timer_screen():  # 화면1 — 대기 · 집중(1-B) · 휴식(1-C) · 그만하기 확인 창(1-D)이 한 화면 안에서 바뀜
    st.title("별도로")

    phase = set_phase()
    if phase is None:
        waiting()
        return

    timer_dial(phase[0], set_left(), set_length())  # 원형 타이머는 브라우저 안에서 스스로 줄어듦
    st.button("그만하기", on_click=ask_stop)
    if st.session_state.get("confirming"):
        stop_confirm()


def toggle_demo():  # 화면2 "시연 모드" 단추 — 켜면 시연 줄과 D-1 칸, 끄면 원래 기록으로 돌아감
    st.session_state.demo = not st.session_state.demo
    st.session_state.pop("count_input", None)  # D-1 칸을 새로 켤 때 시연 줄의 누적 수로 맞춤


def demo_box(count):  # D-1 시연 모드 칸 — 누적 세트 수 바꾸기 (시연 전용 줄에만 저장)
    with st.container(border=True):
        st.caption("시연 모드")
        st.session_state.setdefault("count_input", str(count))
        cols = st.columns([2, 1, 1, 1, 1])
        cols[0].text_input(
            "누적 세트 수",
            key="count_input",
            on_change=apply_count_input,
            placeholder="누적 세트 수",
            label_visibility="collapsed",
        )
        for col, quick in zip(cols[1:], [9, 23, 150, 1000]):
            col.button(str(quick), on_click=set_count, args=(quick,))


def sky_screen():  # 화면2 — 0세트(2-A) · 1세트 이상(2-B) · 세트 진행 중(2-D) · 시연 모드 칸(D-1)
    st.title("별도로")

    count = current_count()
    demo = st.session_state.get("demo", False)
    night_sky(count, height=280 if demo else 360)  # 시연 모드는 넣는 칸 자리만큼 하늘이 조금 낮아짐
    if demo:
        demo_box(count)
    st.write(f"누적 {count}세트 · 총 {focus_time_text(count)} 집중")

    phase = set_phase()
    if phase is None:
        if st.button("다음 세트 시작", type="primary"):
            start_set()
            st.switch_page(timer_page)  # 화면1로 가면서 바로 집중이 시작됨
    else:
        running_button(phase[0])
    if st.button("카드 만들기", disabled=count == 0):  # 0세트면 누를 수 없음
        st.switch_page(card_page)
    if st.session_state.get("tester") is None:  # 테스터 링크로 들어온 화면에는 두지 않음 — 테스터 기록이 시연과 섞이지 않게
        st.button(
            "시연 모드 끄기" if demo else "시연 모드",
            key="demo_toggle",
            on_click=toggle_demo,
            disabled=phase is not None,  # 세트 진행 중에 바꾸면 25분 세트가 시연 길이로 바뀌어 바로 끝나 버림
            help="세트가 끝난 뒤에 바꿀 수 있어요" if phase else None,
        )

    if st.session_state.pop("set_save_failed", False):
        st.error("이번 세트를 Supabase 에 저장하지 못했어요. 이 PC 에 남겨 두었다가 다음에 열 때 다시 올릴게요.")
    if st.session_state.pop("save_failed", False):
        st.error("저장하지 못했어요. 잠시 뒤 다시 넣어 주세요.")
    if st.session_state.pop("count_notice", False):
        count_notice()


def card_screen():  # 화면3 — 카드 미리보기(3-A)
    count = current_count()
    if count == 0:  # 0세트면 카드를 만들 수 없음 — 주소로 바로 들어와도 밤하늘로 돌려보냄
        st.switch_page(sky_page)

    st.title("별도로")
    if st.button("←"):
        st.switch_page(sky_page)

    footer = (
        '<div style="position:absolute; left:0; right:0; bottom:28px; text-align:center; color:#fff;">'
        f'<div style="font-size:26px; font-weight:700;">{count}세트</div>'
        f'<div style="font-size:13px; color:#ccc;">총 {focus_time_text(count)} 집중</div>'
        '<div style="font-size:12px; color:#999; margin-top:14px;">별도로</div>'
        "</div>"
    )
    night_sky(count, height=480, width="270px", footer=footer)  # 9:16
    st.caption("9:16 카드 미리보기")

    if st.button("이미지 저장"):  # 누르면 PNG 파일로 내려받기 — 카드 순서(4번)에서 만듦
        log_event("카드 저장")  # PRD 측정 한계대로 "이미지 저장"을 누른 것까지 셈
        st.write("[만들어졌습니다]")


timer_page = st.Page(timer_screen, title="타이머", default=True)
sky_page = st.Page(sky_screen, title="밤하늘", url_path="sky")
card_page = st.Page(card_screen, title="카드 미리보기", url_path="card", visibility="hidden")  # 탭에는 없고 "카드 만들기"로만 들어옴

page = st.navigation([timer_page, sky_page, card_page], position="top")  # 위쪽 탭: 타이머 · 밤하늘
sync_browser()  # 브라우저 기록을 먼저 읽어야 탭을 닫기 전 진행 중이던 세트를 이어 갈 수 있음
finish_if_done(page)
chatbot()  # 오른쪽 아래 상담 챗봇 — 화면 1·2·3 모두에 뜸
page.run()
if set_phase():  # 세트 동안은 어느 화면이든 세트 엔진을 붙임 — 종소리·화면 꺼짐 막기·단계가 바뀌면 다시 그리기
    set_engine(st.session_state.set_started_at, set_left(), set_length()["휴식"])
