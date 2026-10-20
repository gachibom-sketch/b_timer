import os
from datetime import datetime

import requests
import streamlit as st
from dotenv import load_dotenv

st.set_page_config(page_title="방명록")
st.title("방명록")

# .env 에서 Supabase 주소와 키를 읽음
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error(".env 에 SUPABASE_URL 과 SUPABASE_KEY 를 넣어 주세요.")
    st.stop()

TABLE_URL = f"{SUPABASE_URL}/rest/v1/guestbook"
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}


def load_messages():  # 최근 글 50개를 새 글부터
    response = requests.get(
        TABLE_URL,
        headers=HEADERS,
        params={"select": "message,created_at", "order": "created_at.desc", "limit": 50},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def add_message(text):  # 한 줄을 guestbook 표에 쌓음
    response = requests.post(TABLE_URL, headers=HEADERS, json={"message": text}, timeout=10)
    response.raise_for_status()


def written_time_text(created_at):  # 2026-10-13T11:22:28.96+00:00 → 10월 13일 20:22 (내 컴퓨터 시간대)
    written = datetime.fromisoformat(created_at).astimezone()
    return f"{written.month}월 {written.day}일 {written:%H:%M}"


with st.form("write", clear_on_submit=True):
    text = st.text_input("한 줄 남기기", max_chars=100)
    if st.form_submit_button("남기기"):
        if text.strip():
            try:
                add_message(text.strip())
            except requests.RequestException:
                st.error("글을 남기지 못했어요. 잠시 뒤 다시 해 주세요.")
        else:
            st.warning("글을 한 줄 적어 주세요.")

try:
    messages = load_messages()
except requests.RequestException:
    st.error("방명록을 불러오지 못했어요. .env 의 주소와 키를 확인해 주세요.")
    st.stop()

if not messages:
    st.caption("아직 남긴 글이 없어요.")
for row in messages:
    st.write(f"{row['message']}  ·  {written_time_text(row['created_at'])}")
