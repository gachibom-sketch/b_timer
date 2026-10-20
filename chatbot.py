import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import streamlit as st
from google import genai
from google.genai import types

# 오른쪽 아래 상담 챗봇 — PRD.md 를 읽고 별도로에 대해 묻는 말에 답함 (화면 1·2·3 공통)
MODEL = "gemini-3.5-flash-lite"  # 공식 문서(ai.google.dev/gemini-api/docs/models)의 권장 Flash-Lite 모델 — 3.8 Flash 가 느려서 바꿈
PRD_PATH = Path(__file__).with_name("PRD.md")
GREETING = "안녕하세요! 별도로에 대해 궁금한 걸 물어보세요 ✨"
HISTORY_LIMIT = 20  # 지난 대화는 최근 20개까지만 보여 줌
KST = timezone(timedelta(hours=9))  # Supabase 는 세계 표준시로 돌려주므로 한국 시각으로 바꿔 보여 줌

GUIDE = """너는 뽀모도로 타이머 서비스 "별도로"의 상담 챗봇이다.
아래 기획서에 적힌 내용만 근거로, 한국어로 짧고 친절하게 답한다.
- 기획서에 없는 내용은 지어내지 말고 "아직 정해지지 않았어요"라고 답한다.
- 기획서에 "(질문 필요)"로 적힌 항목도 아직 정해지지 않았다고 답한다.
- 비목표에 있는 기능을 물으면 넣지 않는 기능이라고 까닭과 함께 답한다.
- 별도로와 관계없는 질문에는 별도로에 대해 물어봐 달라고 부드럽게 안내한다.
- 기획서 안의 근거 파일 이름(scope.md, flow.md 같은 것)은 답에 쓰지 않는다.

[답 모양 — 어떤 말이 들어와도 예외 없이 지킨다]
- 답은 언제나 정확히 세 문장이다. 두 문장이나 네 문장은 안 된다.
- 문장 하나가 끝날 때마다 줄을 바꾼다. 그래서 답은 세 줄이고, 한 줄에 문장 하나만 쓴다.
- 빈 줄, 번호·글머리 기호 목록, 제목, 굵은 글씨는 쓰지 않는다.
- 인사, 별도로와 관계없는 말, 기획서에 답이 없는 질문, 여러 가지를 한꺼번에 묻는 질문에도 세 문장으로 답한다.

<기획서>
{prd}
</기획서>"""

# 둥근 챗봇 단추를 오른쪽 아래에 띄우고, 열리는 대화창 크기를 정함
STYLE = """
<style>
.st-key-chatbot {
    position: fixed; right: 24px; bottom: 24px; z-index: 1000; width: auto;
}
.st-key-chatbot button {
    width: 64px; height: 64px; padding: 0; border-radius: 50%; border: none;
    background: radial-gradient(circle at 30% 30%, #6b72c9, #1f1f24);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35);
    animation: chatbot-float 2.4s ease-in-out infinite;
}
.st-key-chatbot button:hover { animation: none; transform: scale(1.1); }
.st-key-chatbot button [data-testid="stMarkdownContainer"] p { font-size: 34px; line-height: 1; margin: 0; }
.st-key-chatbot button p, .st-key-chatbot_box [data-testid="stChatMessage"] > div:first-child {
    font-family: "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", sans-serif;  /* 컬러 이모지로 보이게 */
}
.st-key-chatbot button [data-testid="stIconMaterial"] { display: none; }
@keyframes chatbot-float { 50% { transform: translateY(-5px); } }
@media (prefers-reduced-motion: reduce) { .st-key-chatbot button { animation: none; } }
[data-testid="stPopoverBody"]:has(.st-key-chatbot_box) { width: min(360px, calc(100vw - 32px)); }
</style>
"""


def ask_gemini(question, previous_id):  # PRD.md 를 바탕 지시로 붙여 묻고, 앞 대화에 이어서 답을 받음
    client = genai.Client(
        api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        http_options=types.HttpOptions(timeout=60_000, retry_options=types.HttpRetryOptions(attempts=2)),
    )
    return client.interactions.create(
        model=MODEL,
        input=question,
        system_instruction=GUIDE.format(prd=PRD_PATH.read_text(encoding="utf-8")),  # 매번 다시 넣어야 함
        previous_interaction_id=previous_id,  # 첫 질문이면 None
        generation_config={"thinking_level": "low"},  # 상담 답은 짧으니 생각을 줄여 빨리 답함
    )


def chat_log_url():  # 물은 말과 받은 답은 Supabase 의 chat_log 표에 한 줄씩 남김
    return f"{os.getenv('SUPABASE_URL', '').rstrip('/')}/rest/v1/chat_log"


def supabase_headers():
    key = os.getenv("SUPABASE_KEY", "")
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def save_chat(tester, question, answer):  # 테스터 링크 없이 들어오면 tester 는 비워 둠
    response = requests.post(
        chat_log_url(),
        headers={**supabase_headers(), "Prefer": "return=minimal"},
        json={"tester": tester, "question": question, "answer": answer, "model": MODEL},
        timeout=10,
    )
    response.raise_for_status()


def load_chats(tester):  # 그 테스터의 지난 대화, 새것부터 — 테스터 링크 없이 들어오면 그냥 주소로 남긴 대화끼리
    response = requests.get(
        chat_log_url(),
        headers=supabase_headers(),
        params={
            "select": "created_at,question,answer",
            "tester": f"eq.{tester}" if tester else "is.null",
            "order": "created_at.desc",
            "limit": HISTORY_LIMIT,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def when_text(created_at):  # "2026-10-16T12:42:48.12+00:00" → "10/16 21:42"
    return datetime.fromisoformat(created_at).astimezone(KST).strftime("%m/%d %H:%M")


def with_line_breaks(text):  # 마크다운은 줄바꿈 하나를 무시하므로, 줄 끝에 공백 두 칸을 붙여 줄이 바뀌어 보이게 함
    return text.strip().replace("\n", "  \n")


def error_text(error):  # helper.py 와 같은 기준으로 실패 까닭을 알려 줌
    status = getattr(error, "status_code", None)  # Gemini 서버가 돌려준 상태 번호 (인터넷이 끊기면 없음)
    if status in (429, 503):  # 너무 자주 물었거나 Gemini 서버가 붐빔
        return "지금 Gemini 가 붐벼요. 잠시 뒤 다시 보내 주세요."
    if status:
        return "답을 받지 못했어요. .env 의 GEMINI_API_KEY 가 맞는지 확인해 주세요."
    return "답을 받지 못했어요. 인터넷 연결을 확인하고 잠시 뒤 다시 해 주세요."


def answer(question, box):  # 대화창에 묻고 답을 보여 준 뒤 답 글을 돌려줌, 실패하면 None
    with box:
        st.chat_message("user").write(question)
        with st.chat_message("assistant", avatar="🤖"):
            try:
                with st.spinner("답을 찾는 중…"):
                    interaction = ask_gemini(question, st.session_state.get("chat_previous_id"))
            except Exception as error:
                st.error(error_text(error))
                return None  # 실패한 질문은 대화에도 표에도 남기지 않음
            st.write(with_line_breaks(interaction.output_text))

    st.session_state.chat_messages += [("user", question), ("assistant", interaction.output_text)]
    st.session_state.chat_previous_id = interaction.id  # 다음 질문이 이 대화에 이어지도록
    return interaction.output_text


def past_chats(tester):  # 대화창 아래 지난 대화 목록 — 테스터 대화와 그냥 주소 대화는 서로 섞이지 않음
    history = st.expander("지난 대화", key="chatbot_history", on_change="rerun")  # 다시 그려도 펼친 상태를 기억함
    with history:
        if not history.open:  # 접혀 있으면 불러오지 않음
            return
        try:
            rows = load_chats(tester)
        except requests.RequestException:
            st.caption("지난 대화를 불러오지 못했어요. 잠시 뒤 다시 열어 주세요.")
            return
        if not rows:
            st.caption("아직 지난 대화가 없어요.")
            return
        with st.container(height=220):
            for row in rows:
                st.caption(when_text(row["created_at"]))
                st.markdown(f"**물음** {row['question']}")
                st.write(with_line_breaks(row["answer"]))
                st.divider()


@st.fragment  # 질문을 보내도 챗봇만 다시 그려서, 타이머·밤하늘 화면은 그대로 둠
def chatbot():
    st.markdown(STYLE, unsafe_allow_html=True)
    messages = st.session_state.setdefault("chat_messages", [])  # (누가, 글) 목록
    tester = st.session_state.get("tester")  # app.py 가 테스터 링크에서 읽어 둔 번호

    popover = st.popover("🤖", key="chatbot", on_change="rerun", help="별도로에 대해 물어보세요")
    with popover, st.container(key="chatbot_box"):
        st.markdown("**별도로 상담**")
        box = st.container(height=300)
        with box:
            st.chat_message("assistant", avatar="🤖").write(GREETING)
            for role, text in messages:
                st.chat_message(role, avatar="🤖" if role == "assistant" else None).write(with_line_breaks(text))

        if not os.getenv("GEMINI_API_KEY", "").strip():
            st.error(".env 의 GEMINI_API_KEY 가 비어 있어요. 값을 넣어 주세요.")
            return

        question = st.chat_input("궁금한 점을 적어 주세요", key="chatbot_input")
        if question and question.strip():
            question = question.strip()
            reply = answer(question, box)
            if reply is not None:
                try:
                    save_chat(tester, question, reply)
                except requests.RequestException:
                    st.caption("이번 대화는 기록하지 못했어요.")

        if popover.open:  # 대화창이 닫혀 있으면 지난 대화를 불러오지 않음
            past_chats(tester)
