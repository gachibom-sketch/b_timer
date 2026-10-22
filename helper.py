import os

import openai
import streamlit as st
from dotenv import load_dotenv

st.set_page_config(page_title="챗봇")
st.title("챗봇")

# .env 에서 OpenAI 키를 읽음 — 키 값은 화면에 보이지 않고, 채워졌는지만 알려 줌
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
MODEL = "gpt-6-astra"  # 공식 문서(developers.openai.com/api/docs)의 시작 안내서가 쓰는 모델

if OPENAI_API_KEY:
    st.success(".env 의 OPENAI_API_KEY 가 채워져 있어요.")
else:
    st.error(".env 의 OPENAI_API_KEY 가 비어 있어요. 값을 넣어 주세요.")
    st.stop()


def ask_openai(text):  # 한 번 묻고 답 전체(글자·토큰 수)를 돌려받음 (Responses API)
    # 서버가 바쁠 때 끝없이 기다리지 않도록 한 번에 최대 60초, 다시 시도는 2번까지
    client = openai.OpenAI(api_key=OPENAI_API_KEY, timeout=60.0, max_retries=2)
    return client.responses.create(model=MODEL, input=text)


def token_line(usage):  # 응답의 usage(사용량) → "토큰 278개 (질문 8 · 생각 259 · 답 11)"
    if usage is None or usage.total_tokens is None:
        return "이번 요청의 토큰 수는 알 수 없어요."
    thought = (usage.output_tokens_details.reasoning_tokens or 0) if usage.output_tokens_details else 0
    parts = [
        f"질문 {usage.input_tokens or 0}",
        f"생각 {thought}",  # 답하기 전 모델이 속으로 생각하는 데 쓴 몫 (OpenAI 는 답 토큰 안에 들어 있어 따로 뺌)
        f"답 {(usage.output_tokens or 0) - thought}",
    ]
    return f"이번 요청에 쓴 토큰 {usage.total_tokens}개 ({' · '.join(parts)})"


with st.form("ask"):
    text = st.text_area("물어볼 말")
    if st.form_submit_button("보내기"):
        if text.strip():
            try:
                with st.spinner("답을 기다리는 중…"):
                    response = ask_openai(text.strip())
                st.markdown(response.output_text)
                st.caption(token_line(response.usage))
            except openai.AuthenticationError:
                st.error("답을 받지 못했어요. .env 의 OPENAI_API_KEY 가 맞는지 확인해 주세요.")
            except openai.RateLimitError as error:
                if "insufficient_quota" in (getattr(error, "type", None), getattr(error, "code", None)):  # 크레딧·결제 한도를 다 씀
                    st.error("OpenAI 크레딧을 다 썼어요. OpenAI 결제 화면에서 크레딧을 충전해 주세요.")
                else:  # 너무 자주 물음
                    st.warning("지금 너무 자주 물었어요. 잠시 뒤 다시 보내 주세요.")
            except openai.InternalServerError:  # OpenAI 서버가 붐빔
                st.warning("지금 OpenAI 가 붐벼요. 잠시 뒤 다시 보내 주세요.")
            except openai.APIConnectionError:  # 인터넷이 끊겼거나 60초 안에 답이 오지 않음
                st.error("답을 받지 못했어요. 인터넷 연결을 확인하고 잠시 뒤 다시 해 주세요.")
            except openai.APIStatusError as error:
                st.error(f"답을 받지 못했어요. (OpenAI 응답 {error.status_code})")
        else:
            st.warning("물어볼 말을 적어 주세요.")
