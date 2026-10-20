import os

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

st.set_page_config(page_title="챗봇")
st.title("챗봇")

# .env 에서 Gemini 키를 읽음 — 키 값은 화면에 보이지 않고, 채워졌는지만 알려 줌
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL = "gemini-3.8-flash"  # 공식 문서(ai.google.dev/gemini-api/docs/models)의 권장 Flash 모델

if GEMINI_API_KEY:
    st.success(".env 의 GEMINI_API_KEY 가 채워져 있어요.")
else:
    st.error(".env 의 GEMINI_API_KEY 가 비어 있어요. 값을 넣어 주세요.")
    st.stop()


def ask_gemini(text):  # 한 번 묻고 답 전체(글자·토큰 수)를 돌려받음 (Interactions API)
    # 서버가 바쁠 때 끝없이 기다리지 않도록 한 번에 최대 60초, 다시 시도는 2번까지
    client = genai.Client(
        api_key=GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=60_000, retry_options=types.HttpRetryOptions(attempts=2)),
    )
    return client.interactions.create(model=MODEL, input=text)


def token_line(usage):  # 응답의 usage(사용량) → "토큰 278개 (질문 8 · 생각 259 · 답 11)"
    if usage is None or usage.total_tokens is None:
        return "이번 요청의 토큰 수는 알 수 없어요."
    parts = [
        f"질문 {usage.total_input_tokens or 0}",
        f"생각 {usage.total_thought_tokens or 0}",  # 답하기 전 모델이 속으로 생각하는 데 쓴 몫
        f"답 {usage.total_output_tokens or 0}",
    ]
    return f"이번 요청에 쓴 토큰 {usage.total_tokens}개 ({' · '.join(parts)})"


with st.form("ask"):
    text = st.text_area("물어볼 말")
    if st.form_submit_button("보내기"):
        if text.strip():
            try:
                with st.spinner("답을 기다리는 중…"):
                    interaction = ask_gemini(text.strip())
                st.markdown(interaction.output_text)
                st.caption(token_line(interaction.usage))
            except Exception as error:
                status = getattr(error, "status_code", None)  # Gemini 서버가 돌려준 상태 번호 (인터넷이 끊기면 없음)
                if status in (429, 503):  # 너무 자주 물었거나 Gemini 서버가 붐빔
                    st.warning("지금 Gemini 가 붐벼요. 잠시 뒤 다시 보내 주세요.")
                elif status:
                    st.error("답을 받지 못했어요. .env 의 키가 맞는지 확인해 주세요.")
                else:
                    st.error("답을 받지 못했어요. 인터넷 연결을 확인하고 잠시 뒤 다시 해 주세요.")
        else:
            st.warning("물어볼 말을 적어 주세요.")
