from pathlib import Path

import streamlit as st
from dotenv import dotenv_values

st.set_page_config(page_title="Claude 키 확인")
st.title("Claude 키 확인")

# .env 파일 안의 ANTHROPIC_API_KEY 만 봄 — 키 값은 화면에 보이지 않고, 채워졌는지만 알려 줌
# (컴퓨터 환경 변수에 같은 이름이 따로 있어도 섞이지 않게 load_dotenv 대신 파일 값만 읽음)
ENV_PATH = Path(__file__).with_name(".env")
key = (dotenv_values(ENV_PATH).get("ANTHROPIC_API_KEY") or "").strip()

if key:
    st.success(".env 의 ANTHROPIC_API_KEY 가 채워져 있어요.")
else:
    st.error(".env 의 ANTHROPIC_API_KEY 가 비어 있어요. 값을 넣어 주세요.")
