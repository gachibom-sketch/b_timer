import streamlit as st

# 화면2 밤하늘 부품 — 별이 늘 은은하게 반짝이고, 세트를 마치고 넘어오면 별똥별이 떨어져 새 별 자리에 박히며,
# 10·100·1000번째 세트에서는 별 10개가 빨려 들어가듯 모여 한 단계 큰 별이 됨 (와이어프레임 2-B·2-C)
# 컴퓨터의 "동작 줄이기" 설정이 켜져 있으면 반짝임·별똥별·모여들기 없이 새 별만 천천히 나타남

EMPTY_TEXT = "첫 세트를 마치면 별이 떠요"  # 0세트(2-A)

SKY_HTML = '<div class="sky" role="img"></div>'

SKY_CSS = """
.sky { position: relative; width: 100%; background: #1f1f24; border-radius: 8px; overflow: hidden; }
.star {
    position: absolute; transform: translate(-50%, -50%); line-height: 1; color: #fff;
    text-shadow: 0 0 6px rgba(255, 255, 255, 0.6); pointer-events: none; user-select: none;
    animation: twinkle var(--twinkle) ease-in-out var(--delay) infinite alternate;
}
@keyframes twinkle { to { opacity: 0.45; } }
.empty { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: #bbb; }
.meteor {
    position: absolute; width: 120px; height: 2px; margin-top: -1px; border-radius: 2px; transform-origin: 0 50%;
    background: linear-gradient(to right, #fff, rgba(255, 255, 255, 0.5) 15%, transparent);
}
.glow {
    position: absolute; width: 64px; height: 64px; border-radius: 50%; transform: translate(-50%, -50%);
    background: radial-gradient(circle, rgba(255, 255, 255, 0.5), transparent 70%); opacity: 0;
}
@media (prefers-reduced-motion: reduce) { .star { animation: none; } }
"""

SKY_JS = """
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

export default function (component) {
  const { data, parentElement } = component;
  parentElement.__stop?.();  // 값이 바뀌어 다시 불리면 앞의 연출을 치움

  const sky = parentElement.querySelector(".sky");
  sky.replaceChildren();
  sky.style.height = `${data.height}px`;
  sky.setAttribute("aria-label", data.label);

  let stopped = false;
  const moves = [];
  parentElement.__stop = () => {
    stopped = true;
    moves.forEach((m) => m.cancel());
  };
  const check = () => {  // 치운 뒤에는 하던 연출이 새 하늘에 별을 더하지 않게 멈춤
    if (stopped) throw new Error("stopped");
  };
  const move = (el, frames, options) => {
    const m = el.animate(frames, { fill: "none", ...options });
    moves.push(m);
    return m.finished;
  };
  const scale = (n) => `translate(-50%, -50%) scale(${n})`;

  const layers = data.layers;  // 작은별 → 중간별 → 큰별 → 대왕별, 종류마다 모양·크기·10자리
  const stars = layers.map(() => []);
  const place = (tier, index) => {
    const { mark, size, slots } = layers[tier];
    const [left, top] = slots[Math.min(index, 9)];
    const star = document.createElement("span");
    star.className = "star";
    star.textContent = mark;
    // 별마다 반짝이는 빠르기와 때를 조금씩 다르게 — 자리로 정해 두어 다시 그려도 같음
    star.style.cssText = `left:${left}%; top:${top}%; font-size:${size}px;`
      + ` --twinkle:${2.4 + ((tier * 7 + index * 13) % 10) * 0.3}s; --delay:-${(index * 1.37 + tier) % 4}s;`;
    sky.append(star);
    stars[tier].push(star);
    return star;
  };
  const draw = (counts) => counts.forEach((n, tier) => { for (let i = 0; i < n; i++) place(tier, i); });
  const addEmpty = () => {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = data.empty;
    sky.append(empty);
    return empty;
  };

  const seen = (window.__byeoldoroArrivals ??= new Set());  // 같은 세트의 연출은 한 번만 — 화면을 옮겨 다시 와도 되풀이하지 않음
  const fresh = data.arrival != null && !seen.has(data.arrival);
  if (!fresh) {
    draw(data.counts);
    if (data.counts.every((n) => n === 0)) addEmpty();
    return () => parentElement.__stop();
  }
  seen.add(data.arrival);

  const pop = (star, peak) => move(star, [
    { transform: scale(0), opacity: 0 },
    { transform: scale(peak), opacity: 1, offset: 0.55 },
    { transform: scale(1), opacity: 1 },
  ], { duration: 650, easing: "ease-out" });

  const meteor = async (left, top) => {  // 오른쪽 위에서 비스듬히 떨어져 새 별 자리에서 멈춤
    const w = sky.clientWidth;
    const h = sky.clientHeight;
    const [ex, ey] = [(left / 100) * w, (top / 100) * h];
    const run = Math.max(w, h) * 0.7;
    const rad = (ANGLE * Math.PI) / 180;
    const [sx, sy] = [ex + run * Math.cos(rad), ey - run * Math.sin(rad)];
    const streak = document.createElement("div");
    streak.className = "meteor";
    streak.style.transform = `rotate(${-ANGLE}deg)`;  // 꼬리는 날아온 쪽(오른쪽 위)으로
    sky.append(streak);
    await move(streak, [
      { left: `${sx}px`, top: `${sy}px`, opacity: 0 },
      { opacity: 1, offset: 0.2 },
      { left: `${ex}px`, top: `${ey}px`, opacity: 1 },
    ], { duration: 1200, easing: "cubic-bezier(0.3, 0.1, 0.6, 1)", fill: "forwards" });
    streak.remove();
  };

  const gather = async (tier, next, index) => {  // tier 별 10개가 next 별 자리로 빨려 들어감
    const [left, top] = layers[next].slots[Math.min(index, 9)];
    const glow = document.createElement("div");
    glow.className = "glow";
    glow.style.cssText = `left:${left}%; top:${top}%;`;
    sky.append(glow);
    move(glow, [{ opacity: 0, transform: scale(0.2) }, { opacity: 1, transform: scale(1) }], { duration: 1200, fill: "forwards" });
    await Promise.all(stars[tier].map((star, i) => move(star, [
      { left: star.style.left, top: star.style.top, opacity: 1, transform: scale(1) },
      { left: `${left}%`, top: `${top}%`, opacity: 0, transform: scale(0.3) },
    ], { duration: 1100, delay: i * 40, easing: "cubic-bezier(0.6, 0, 0.9, 0.4)", fill: "forwards" })));
    check();
    stars[tier].forEach((star) => star.remove());
    stars[tier] = [];
    return glow;
  };

  const arrive = async () => {
    draw(data.before);
    const empty = data.before.every((n) => n === 0) ? addEmpty() : null;
    await whenVisible();
    await wait(500);  // 밤하늘을 먼저 잠깐 보여 준 뒤 떨어짐
    check();

    if (matchMedia("(prefers-reduced-motion: reduce)").matches) {  // 동작 줄이기 — 바뀐 하늘을 그리고 새 별만 천천히 나타남
      sky.replaceChildren();
      stars.forEach((group) => { group.length = 0; });
      draw(data.counts);
      const tier = data.counts.findLastIndex((n, t) => n !== data.before[t]);
      if (tier >= 0 && data.counts[tier] > 0) {
        move(stars[tier][data.counts[tier] - 1], [{ opacity: 0 }, { opacity: 1 }], { duration: 900 });
      }
      return;
    }

    await meteor(...layers[0].slots[data.before[0]]);
    check();
    if (empty) move(empty, [{ opacity: 1 }, { opacity: 0 }], { duration: 400, fill: "forwards" });
    await pop(place(0, data.before[0]), 1.8);

    // 10개가 차면 한 단계 큰 별로 — 100·1000번째는 이어서 한 번 더
    for (let tier = 0; tier < layers.length - 1 && stars[tier].length === 10; tier++) {
      await wait(300);
      check();
      const next = tier + 1;
      const index = data.before[next];
      const glow = await gather(tier, next, index);
      if (stars[next].length < 10) await pop(place(next, index), 2.2);  // 대왕별은 10개까지만 그림
      check();
      move(glow, [{ opacity: 1 }, { opacity: 0 }], { duration: 600, fill: "forwards" }).then(() => glow.remove(), () => {});
    }
  };
  arrive().catch(() => {});  // 치워서 멈춘 연출은 조용히 끝냄

  return () => parentElement.__stop();
}
"""


# 부품은 쓸 때마다 등록함 — 같은 내용이면 Streamlit 이 조용히 넘어감 (timer_parts.py 와 같음)
def sky_view(layers, counts, height, label, arrival=None, before=None):
    # layers: 작은별부터 대왕별까지 모양·크기·10자리 · counts: 종류마다 그릴 개수
    # arrival: 방금 마친 세트의 번호(세트 시작 시각) — 있으면 before(그 세트 전의 개수)에서 counts 로 연출함
    sky = st.components.v2.component("night_sky", html=SKY_HTML, css=SKY_CSS, js=SKY_JS)
    sky(
        key="night_sky",
        data={
            "layers": layers,
            "counts": counts,
            "height": height,
            "label": label,
            "empty": EMPTY_TEXT,
            "arrival": arrival,
            "before": before,
        },
    )
