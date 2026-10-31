import html

import streamlit as st

# 화면2 밤하늘 부품 — 지금 기간의 목표 별자리만 그림 (PRD 6판, 스티치 시안 2E·2F)
# 달성률만큼 앞 별부터 차오름: 다 켜진 별은 빛나는 별 모양, 차오르는 중인 별은 같은 모양을 작고 옅게, 아직 안 찬 자리는 희미한 점과 고리
# 100% 가 되면 노란 선이 별을 차례로 잇고, 넘긴 세트는 선 없는 작은 흰 덤 별(10개까지)이 됨
# 세트를 마치고 넘어오면 별똥별이 그 별 자리로 떨어짐 · 별은 늘 은은하게 반짝임
# 컴퓨터의 "동작 줄이기" 설정이 켜져 있으면 반짝임·별똥별·선 긋기 없이 바뀐 별만 천천히 나타남

SKY_HTML = '<div class="sky" role="img"></div>'

SKY_CSS = """
.sky { position: relative; width: 100%; border-radius: 12px; overflow: hidden; background: linear-gradient(180deg, #0E1430 0%, #1C2650 100%); }
.board { position: absolute; overflow: visible; }
.board g.pop { transform-box: fill-box; transform-origin: center; }
.lit .shape { animation: twinkle var(--twinkle) ease-in-out var(--delay) infinite alternate; }
@keyframes twinkle { to { opacity: 0.62; } }
.empty { position: absolute; left: 0; right: 0; bottom: 16px; text-align: center; color: #C9CEDC; font-size: 14px; }
.meteor {
    position: absolute; width: 120px; height: 2px; margin-top: -1px; border-radius: 2px; transform-origin: 0 50%;
    background: linear-gradient(to right, #fff, rgba(255, 255, 255, 0.5) 15%, transparent);
}
@media (prefers-reduced-motion: reduce) { .lit .shape { animation: none; } }
"""

SKY_JS = """
const NS = "http://www.w3.org/2000/svg";
const ANGLE = 35;  // 별똥별이 오른쪽 위에서 떨어지는 기울기(도)
const wait = (ms) => new Promise((done) => setTimeout(done, ms));

function whenVisible() {  // 다른 탭에 있는 동안 세트가 끝났으면, 돌아와 볼 때까지 연출을 미룸
  return new Promise((done) => {
    if (document.visibilityState === "visible") return done();
    const on = () => {
      if (document.visibilityState !== "visible") return;
      document.removeEventListener("visibilitychange", on);
      done();
    };
    document.addEventListener("visibilitychange", on);
  });
}

function fill(count, target, stars) {  // goals.py star_fill 과 같은 셈 — 다 켜진 별 수 · 다음 별 밝기 · 덤 별 수 · 완성
  const ratio = Math.min(count / target, 1);
  const lit = Math.floor(ratio * stars + 1e-9);
  return { lit, part: lit >= stars ? 0 : ratio * stars - lit, bonus: Math.min(Math.max(count - target, 0), 10), done: count >= target };
}

function sparkle(r) {  // 네 갈래로 빛나는 별 모양
  const c = r * 0.2;
  return `M0 ${-r} C ${c} ${-c} ${c} ${-c} ${r} 0 C ${c} ${c} ${c} ${c} 0 ${r} C ${-c} ${c} ${-c} ${c} ${-r} 0 C ${-c} ${-c} ${-c} ${-c} 0 ${-r} Z`;
}

function el(tag, attrs, parent) {
  const node = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (parent) parent.append(node);
  return node;
}

export default function (component) {
  const { data, parentElement } = component;
  parentElement.__stop?.();  // 값이 바뀌어 다시 불리면 앞의 연출을 치움

  const sky = parentElement.querySelector(".sky");
  sky.replaceChildren();
  sky.style.height = `${data.height}px`;
  sky.setAttribute("aria-label", data.label);

  let stopped = false;
  const moves = [];
  parentElement.__stop = () => { stopped = true; moves.forEach((m) => m.cancel()); };
  const check = () => { if (stopped) throw new Error("stopped"); };
  const move = (node, frames, options) => {
    const m = node.animate(frames, { fill: "none", ...options });
    moves.push(m);
    return m.finished;
  };

  // 별자리 판 — 하늘 가운데 정사각형 (constellations.py 의 자리 값이 판 기준 %)
  const width = sky.clientWidth || 358;
  const side = Math.min(width, data.height) * 0.9;
  const [boardLeft, boardTop] = [(width - side) / 2, (data.height - side) / 2];  // svg 에는 offsetLeft 가 없어서 직접 셈
  const board = el("svg", { class: "board", viewBox: "0 0 100 100", "aria-hidden": "true" });
  board.style.cssText = `width:${side}px; height:${side}px; left:${boardLeft}px; top:${boardTop}px;`;
  sky.append(board);
  const defs = el("defs", {}, board);
  const glowGradient = el("radialGradient", { id: "star-glow" }, defs);
  el("stop", { offset: "0", "stop-color": "#fff", "stop-opacity": "0.55" }, glowGradient);
  el("stop", { offset: "1", "stop-color": "#fff", "stop-opacity": "0" }, glowGradient);

  const stars = data.stars;
  const radius = (s) => 1.3 + 1.5 * s.size;  // 오리온 허리띠 세 별이 판 5% 간격이라 별 반지름은 판 2% 안팎

  const draw = (count) => {  // 그 세트 수의 모습을 새로 그림 → 바뀐 것을 찾을 수 있게 부분을 돌려줌
    board.querySelectorAll("g.layer").forEach((g) => g.remove());
    const state = fill(count, data.target, stars.length);
    const lines = el("g", { class: "layer", stroke: "#FFEF4D", "stroke-width": "0.6", "stroke-linecap": "round", opacity: "0.85" }, board);
    const spots = el("g", { class: "layer" }, board);
    const shine = el("g", { class: "layer" }, board);
    const parts = { lines: [], stars: [], bonus: [], state };
    if (state.done) {
      for (const [a, b] of data.lines) {
        const [x1, y1] = stars[a].pos, [x2, y2] = stars[b].pos;
        parts.lines.push(el("line", { x1, y1, x2, y2 }, lines));
      }
    }
    stars.forEach((s, i) => {
      const at = el("g", { transform: `translate(${s.pos[0]} ${s.pos[1]})` }, spots);
      el("circle", { r: "0.7", fill: "rgba(255,255,255,0.35)" }, at);  // 아직 안 찬 자리: 희미한 점과 고리
      el("circle", { r: "2.2", fill: "none", stroke: "rgba(255,255,255,0.22)", "stroke-width": "0.35" }, at);
      const amount = i < state.lit ? 1 : i === state.lit ? state.part : 0;
      if (amount <= 0.001) return;
      const holder = el("g", { transform: `translate(${s.pos[0]} ${s.pos[1]})` }, shine);
      const pop = el("g", { class: amount === 1 ? "pop lit" : "pop" }, holder);
      const r = radius(s) * (amount === 1 ? 1 : 0.45 + 0.4 * amount);
      el("circle", { r: r * 2.4, fill: "url(#star-glow)", opacity: amount === 1 ? 0.9 : 0.4 * amount }, pop);
      const shape = el("path", { class: "shape", d: sparkle(r), fill: s.color, opacity: amount === 1 ? 1 : 0.35 + 0.5 * amount }, pop);
      shape.style.cssText = `--twinkle:${2.4 + (i * 7 % 10) * 0.3}s; --delay:-${(i * 1.37) % 4}s;`;
      parts.stars[i] = pop;
    });
    data.bonus.slice(0, state.bonus).forEach((pos, i) => {  // 덤 별 — 선 없는 작은 흰 점
      const holder = el("g", { transform: `translate(${pos[0]} ${pos[1]})` }, shine);
      const pop = el("g", { class: "pop lit" }, holder);
      el("circle", { r: "2", fill: "url(#star-glow)" }, pop);
      el("circle", { class: "shape", r: "0.8", fill: "#fff" }, pop);
      parts.bonus[i] = pop;
    });
    return parts;
  };
  const addEmpty = () => {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = data.empty;
    sky.append(empty);
    return empty;
  };

  const seen = (window.__byeoldoroArrivals ??= new Set());  // 같은 세트의 연출은 한 번만 — 화면을 옮겨 다시 와도 되풀이하지 않음
  const fresh = data.arrival != null && !seen.has(data.arrival) && data.before != null;
  if (!fresh) {
    draw(data.count);
    if (data.count === 0) addEmpty();
    return () => parentElement.__stop();
  }
  seen.add(data.arrival);

  const toPixel = ([x, y]) => [boardLeft + (x / 100) * side, boardTop + (y / 100) * side];
  const meteor = async (pos) => {  // 오른쪽 위에서 비스듬히 떨어져 그 별 자리에서 멈춤
    const [ex, ey] = toPixel(pos);
    const run = Math.max(sky.clientWidth, sky.clientHeight) * 0.7;
    const rad = (ANGLE * Math.PI) / 180;
    const streak = document.createElement("div");
    streak.className = "meteor";
    streak.style.transform = `rotate(${-ANGLE}deg)`;  // 꼬리는 날아온 쪽(오른쪽 위)으로
    sky.append(streak);
    await move(streak, [
      { left: `${ex + run * Math.cos(rad)}px`, top: `${ey - run * Math.sin(rad)}px`, opacity: 0 },
      { opacity: 1, offset: 0.2 },
      { left: `${ex}px`, top: `${ey}px`, opacity: 1 },
    ], { duration: 1200, easing: "cubic-bezier(0.3, 0.1, 0.6, 1)", fill: "forwards" });
    streak.remove();
  };
  const pop = (node, peak) => move(node, [
    { transform: "scale(0)", opacity: 0 },
    { transform: `scale(${peak})`, opacity: 1, offset: 0.55 },
    { transform: "scale(1)", opacity: 1 },
  ], { duration: 650, easing: "ease-out" });

  const arrive = async () => {
    const before = draw(data.before);
    const empty = data.before === 0 ? addEmpty() : null;
    await whenVisible();
    await wait(500);  // 밤하늘을 먼저 잠깐 보여 준 뒤 떨어짐
    check();

    const after = fill(data.count, data.target, stars.length);
    const gotBonus = after.bonus > before.state.bonus;
    const target = gotBonus ? data.bonus[after.bonus - 1] : stars[Math.min(after.part > 0.001 ? after.lit : after.lit - 1, stars.length - 1)].pos;
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!reduce) await meteor(target);
    check();
    if (empty) move(empty, [{ opacity: 1 }, { opacity: 0 }], { duration: 400, fill: "forwards" });

    const now = draw(data.count);
    const changed = [];  // 밝아진 별과 새 덤 별
    now.stars.forEach((node, i) => {
      const was = i < before.state.lit ? 1 : i === before.state.lit ? before.state.part : 0;
      const is = i < after.lit ? 1 : i === after.lit ? after.part : 0;
      if (node && is > was + 0.001) changed.push(node);
    });
    for (let i = before.state.bonus; i < after.bonus; i++) changed.push(now.bonus[i]);  // 새 덤 별 (시연에서 한꺼번에 늘면 여럿)
    await Promise.all(changed.map((node) => reduce
      ? move(node, [{ opacity: 0 }, { opacity: 1 }], { duration: 900 })
      : pop(node, 1.8)));
    check();

    if (after.done && !before.state.done) {  // 방금 완성 — 별 사이에 선이 차례로 이어짐
      for (const [i, line] of now.lines.entries()) {
        const length = Math.hypot(line.x2.baseVal.value - line.x1.baseVal.value, line.y2.baseVal.value - line.y1.baseVal.value);
        line.style.strokeDasharray = `${length}`;
        line.style.strokeDashoffset = reduce ? "0" : `${length}`;
        if (reduce) { move(line, [{ opacity: 0 }, { opacity: 1 }], { duration: 900 }); continue; }
        move(line, [{ strokeDashoffset: length }, { strokeDashoffset: 0 }], { duration: 420, delay: i * 220, easing: "ease-in-out", fill: "forwards" });
      }
    }
  };
  arrive().catch(() => {});  // 치워서 멈춘 연출은 조용히 끝냄

  return () => parentElement.__stop();
}
"""


# 부품은 쓸 때마다 등록함 — 같은 내용이면 Streamlit 이 조용히 넘어감 (timer_parts.py 와 같음)
def sky_view(constellation, count, target, height, label, empty, arrival=None, before=None):
    # constellation: constellations.py 의 별자리 하나 · count: 이번 기간 세트 수 · target: 목표 세트 수
    # arrival: 방금 마친 세트의 번호(세트 시작 시각) — 있으면 before(그 세트 전의 세트 수)에서 count 로 연출함
    sky = st.components.v2.component("night_sky", html=SKY_HTML, css=SKY_CSS, js=SKY_JS)
    sky(
        key="night_sky",
        data={
            "stars": [{"pos": s["pos"], "size": s["size"], "color": s["color"]} for s in constellation["stars"]],
            "lines": constellation["lines"],
            "bonus": [b["pos"] for b in constellation["bonus"]],
            "count": count,
            "target": target,
            "height": height,
            "label": label,
            "empty": empty,
            "arrival": arrival,
            "before": before,
        },
    )


PAST_CSS = """
.past-list { display: flex; flex-direction: column; gap: 10px; }
.past-row { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border: 1px solid #E5E8EB; border-radius: 14px; }
.past-pic { width: 44px; height: 44px; flex-shrink: 0; border-radius: 10px; }
.past-text { display: flex; flex-direction: column; gap: 2px; flex: 1; min-width: 0; }
.past-name { font-weight: 700; font-size: 15px; color: #31333F; }
.past-sub { font-size: 13px; color: #5C6270; }
.past-state { font-size: 13px; color: #31333F; white-space: nowrap; }
.past-state.done { padding: 2px 8px; border-radius: 999px; background: #33354A; color: #FFFFFF; font-weight: 600; }
"""

PAST_JS = """
export default function (component) {  // 파이썬이 만든 목록을 그대로 넣음 (st.html 은 svg 그림을 지워서 부품으로 그림)
  const { data, parentElement } = component;
  parentElement.querySelector(".past-list").innerHTML = data.html;
}
"""


def past_picture(constellation, lit, part, done):  # 지난 별자리 작은 그림 — 그 기간에 그린 만큼 (완성이면 선까지)
    stars = constellation["stars"]
    lines = ""
    if done:
        lines = "".join(
            f'<line x1="{stars[a]["pos"][0]}" y1="{stars[a]["pos"][1]}" x2="{stars[b]["pos"][0]}" y2="{stars[b]["pos"][1]}" />'
            for a, b in constellation["lines"]
        )
    dots = []
    for i, s in enumerate(stars):
        x, y = s["pos"]
        amount = 1 if i < lit else part if i == lit else 0
        if amount > 0:
            dots.append(f'<circle cx="{x}" cy="{y}" r="{3 + 3 * s["size"]}" fill="{s["color"]}" opacity="{0.35 + 0.65 * amount:.2f}" />')
        else:
            dots.append(f'<circle cx="{x}" cy="{y}" r="2" fill="rgba(255,255,255,0.3)" />')
    return (
        '<svg class="past-pic" viewBox="0 0 100 100" aria-hidden="true">'
        '<defs><linearGradient id="past-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0E1430"/><stop offset="1" stop-color="#1C2650"/></linearGradient></defs>'
        '<rect width="100" height="100" fill="url(#past-sky)"/>'
        f'<g stroke="#FFEF4D" stroke-width="1.6" opacity="0.85">{lines}</g>{"".join(dots)}</svg>'
    )


def past_list(rows):  # 화면2 아래 "지난 별자리" — rows: {constellation, name, sub, state, done, lit, part}, 최근 것부터
    items = []
    for row in rows:
        picture = past_picture(row["constellation"], row["lit"], row["part"], row["done"])
        state = f'<span class="past-state{" done" if row["done"] else ""}">{html.escape(row["state"])}</span>'
        items.append(
            f'<div class="past-row" role="listitem">{picture}<div class="past-text"><span class="past-name">{html.escape(row["name"])}</span>'
            f'<span class="past-sub">{html.escape(row["sub"])}</span></div>{state}</div>'
        )
    view = st.components.v2.component(
        "past_list", html='<div class="past-list" role="list" aria-label="지난 별자리"></div>', css=PAST_CSS, js=PAST_JS
    )
    view(key="past_list", data={"html": "".join(items)})
