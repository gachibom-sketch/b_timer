import streamlit as st

# 화면0 별자리 카드 — 큰 별자리 그림 · 이름 · 목표 한 줄, 누르면 그 별자리를 고름 (스티치 시안 0A, PRD 6판 화면 0)
# 고른 별자리는 이 화면에 머무는 동안 브라우저가 기억하고, 파이썬에는 {key, token} 으로 알려 줌
# token 은 "목표 바꾸기"로 들어올 때마다 새로 정함 — 지난번에 고른 값이 남아 있어도 섞이지 않게
CARDS_HTML = '<div class="cards" role="radiogroup" aria-label="목표 별자리"></div>'

CARDS_CSS = """
.cards { display: flex; flex-direction: column; gap: 12px; }
.card {
  display: flex; align-items: center; gap: 14px; width: 100%; padding: 13px; margin: 0;
  border: 1px solid #E5E8EB; border-radius: 16px; background: #FFFFFF; color: #31333F;
  font: inherit; text-align: left; cursor: pointer;
}
.card:hover { border-color: #B6BAC2; }
.card:focus-visible { outline: 3px solid #8C93A8; outline-offset: 2px; }
.card[aria-checked="true"] { border: 2px solid #33354A; padding: 12px; }
.pic { width: 104px; height: 104px; flex-shrink: 0; border-radius: 12px; background: linear-gradient(180deg, #0E1430 0%, #1C2650 100%); }
.text { display: flex; flex-direction: column; gap: 5px; flex: 1; min-width: 0; }
.name { font-size: 18px; font-weight: 700; white-space: nowrap; }
.tag { align-self: flex-start; padding: 2px 8px; border-radius: 6px; background: #F0F2F6; font-size: 12px; font-weight: 600; }
.goal { font-size: 14px; color: #5C6270; white-space: nowrap; }
.check {
  width: 26px; height: 26px; flex-shrink: 0; border-radius: 50%; border: 2px solid #D5D8DE;
  display: flex; align-items: center; justify-content: center;
}
.card[aria-checked="true"] .check { border-color: #33354A; background: #33354A; }
.card[aria-checked="true"] .check::after { content: ""; width: 10px; height: 5px; margin-top: -3px; border: solid #FFFFFF; border-width: 0 0 2px 2px; transform: rotate(-45deg); }
"""

CARDS_JS = """
function picture(card) {  // 정사각형 밤하늘에 별자리 — 별 자리는 판 기준 (왼쪽 %, 위 %)
  const lines = card.lines.map(([a, b]) => {
    const [x1, y1] = card.stars[a].pos, [x2, y2] = card.stars[b].pos;
    return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" />`;
  }).join("");
  const stars = card.stars.map((s) => {
    const r = 1.6 + 2.4 * s.size;
    return `<circle cx="${s.pos[0]}" cy="${s.pos[1]}" r="${r * 2.2}" fill="${s.color}" opacity="0.18" />` +
           `<circle cx="${s.pos[0]}" cy="${s.pos[1]}" r="${r}" fill="${s.color}" />`;
  }).join("");
  return `<svg class="pic" viewBox="0 0 100 100" aria-hidden="true">` +
         `<g stroke="rgba(255,255,255,0.5)" stroke-width="1.1" stroke-linecap="round">${lines}</g>${stars}</svg>`;
}

export default function (component) {
  const { data, parentElement, setStateValue } = component;
  if (parentElement.__token !== data.token) {  // 이번에 새로 들어옴 — 지금 목표의 별자리부터 골라 둠
    parentElement.__token = data.token;
    parentElement.__picked = data.selected;
  }
  const box = parentElement.querySelector(".cards");
  box.replaceChildren();
  for (const card of data.cards) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "card";
    button.setAttribute("role", "radio");
    button.setAttribute("aria-checked", String(card.key === parentElement.__picked));
    button.setAttribute("aria-label", `${card.name}, ${card.goal}${card.tag ? ", " + card.tag : ""}`);
    button.innerHTML = picture(card) +
      `<span class="text"><span class="name">${card.name}</span>` +
      (card.tag ? `<span class="tag">${card.tag}</span>` : "") +
      `<span class="goal">${card.goal}</span></span><span class="check"></span>`;
    button.addEventListener("click", () => {
      parentElement.__picked = card.key;
      for (const other of box.children) other.setAttribute("aria-checked", String(other === button));
      setStateValue("picked", { key: card.key, token: data.token });
    });
    box.append(button);
  }
}
"""


# 부품은 쓸 때마다 등록함 — 같은 내용이면 Streamlit 이 조용히 넘어감 (timer_parts.py 와 같음)
def goal_cards(cards, selected, token):  # cards: 쉬운 것부터 {key, name, goal, tag, stars, lines} · selected: 처음 골라 둘 별자리 → 고른 별자리 key
    picker = st.components.v2.component("goal_cards", html=CARDS_HTML, css=CARDS_CSS, js=CARDS_JS)
    result = picker(key="goal_cards", data={"cards": cards, "selected": selected, "token": token}, on_picked_change=lambda: None)
    picked = getattr(result, "picked", None)
    if picked and picked.get("token") == token:
        return picked["key"]
    return selected
