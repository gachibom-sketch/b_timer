import os
import re
from datetime import datetime

import requests
import streamlit as st
from dotenv import load_dotenv

st.set_page_config(page_title="진행 기록")
st.title("진행 기록")
st.caption("progress 표에 테스터 번호와 누적 세트 수를 넣고 다시 보여 줍니다. 0번은 시연 전용 줄입니다.")

# .env 에서 Supabase 주소와 키를 읽음
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error(".env 에 SUPABASE_URL 과 SUPABASE_KEY 를 넣어 주세요.")
    st.stop()

TABLE_URL = f"{SUPABASE_URL}/rest/v1/progress"
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
MAX_SET_COUNT = 2147483647  # set_count 열(int4)에 담을 수 있는 가장 큰 수


def load_rows():  # 테스터 번호 순으로 모든 줄
    response = requests.get(
        TABLE_URL,
        headers=HEADERS,
        params={"select": "tester,set_count,updated_at", "order": "tester.asc"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def save_row(tester, set_count):  # 그 테스터 줄이 있으면 고치고, 없으면 새로 만듦 — 저장된 줄을 돌려줌
    response = requests.post(
        TABLE_URL,
        headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=representation"},
        json={"tester": tester, "set_count": set_count},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()[0]


def updated_time_text(updated_at):  # 2026-10-13T12:30:00+00:00 → 10월 13일 21:30 (내 컴퓨터 시간대)
    if not updated_at:
        return "시각 없음"
    updated = datetime.fromisoformat(updated_at).astimezone()
    return f"{updated.month}월 {updated.day}일 {updated:%H:%M}"


with st.form("write", clear_on_submit=True):
    tester = st.text_input("테스터 번호", max_chars=4, placeholder="07")
    set_count = st.number_input("누적 세트 수", min_value=0, max_value=MAX_SET_COUNT, step=1)
    if st.form_submit_button("넣기"):
        tester = tester.strip()
        if not re.fullmatch(r"[0-9]{1,4}", tester):
            st.warning("테스터 번호는 숫자 1~4자리로 적어 주세요.")
        else:
            try:
                saved = save_row(tester, int(set_count))
            except requests.RequestException:
                st.error("넣지 못했어요. 이미 있는 번호라면 Supabase 에서 줄 고치기가 허용됐는지 확인해 주세요.")
            else:
                if saved["set_count"] != set_count:  # 숫자가 줄어들지 않게 막는 규칙이 큰 값을 지킴
                    st.info(f"{tester}번은 이미 {saved['set_count']}세트라서 더 작은 숫자로 바뀌지 않았어요.")

try:
    rows = load_rows()
except requests.RequestException:
    st.error("진행 기록을 불러오지 못했어요. .env 의 주소와 키를 확인해 주세요.")
    st.stop()

if not rows:
    st.caption("아직 넣은 기록이 없어요.")
for row in rows:
    st.write(f"{row['tester']}번  ·  {row['set_count']}세트  ·  {updated_time_text(row['updated_at'])}")
