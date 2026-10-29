import streamlit as st

# 브라우저 저장 칸(localStorage)을 읽고 쓰는 보이지 않는 부품 — 별모도로 기록의 브라우저 사본
# 저장 이름 "byeoldoro." 는 서비스 이름을 바꾸기 전(별도로) 그대로 둠 — 바꾸면 이미 쌓인 기록을 찾지 못함
# 처음에는 읽어서 파이썬에 알려 주고, 그 뒤로는 파이썬이 정한 값을 씀
STORE_JS = """
export default function (component) {
  const { data, setStateValue } = component;
  if (!data || !data.key) return;  // 시연 모드처럼 브라우저에 남기지 않을 때
  const name = "byeoldoro." + data.key;

  if (data.snapshot) {  // 파이썬이 정한 값을 씀
    try { localStorage.setItem(name, JSON.stringify(data.snapshot)); } catch (e) {}
    return;
  }

  let values = {};  // 아직 읽지 않았으면 읽어서 알림 (저장 칸을 쓸 수 없는 브라우저면 빈 기록)
  try { values = JSON.parse(localStorage.getItem(name) || "{}") || {}; } catch (e) {}
  setStateValue("saved", { key: data.key, values });
}
"""


def browser_store(key, snapshot):  # key: 기록 이름(None 이면 아무것도 안 함) · snapshot: 쓸 값(None 이면 읽기) → 읽은 값
    # 부품은 쓸 때마다 등록함 — 같은 내용이면 Streamlit 이 조용히 넘어감 (timer_parts.py 와 같은 방식)
    store = st.components.v2.component("browser_store", js=STORE_JS)
    result = store(key="browser_store", data={"key": key, "snapshot": snapshot}, on_saved_change=lambda: None)
    return getattr(result, "saved", None)
