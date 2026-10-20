import streamlit as st

# 화면1 타이머 부품 — 브라우저 안에서 도는 원형 타이머와, 세트 동안 소리·화면 꺼짐 막기를 맡는 보이지 않는 부품

# 두 부품이 함께 쓰는 소리 — 소리 파일 없이 브라우저에서 종소리를 만듦
# 브라우저는 사용자가 한 번 누른 뒤에야 소리를 내 주므로, 아무 데나 처음 누를 때("시작" 등) 소리를 미리 깨워 둠
SOUND_JS = """
function audio() {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return null;
  window.__byeoldoroAudio ??= new Ctx();
  return window.__byeoldoroAudio;
}

function unlockSound() {
  if (window.__byeoldoroUnlock) return;
  window.__byeoldoroUnlock = true;
  document.addEventListener("pointerdown", () => audio()?.resume(), { capture: true });
}

function chime(name, notes) {
  (window.__byeoldoroChimes ??= []).push(name);  // 시험할 때 소리가 났는지 보려고 남김
  const ctx = audio();
  if (!ctx) return;
  ctx.resume();
  notes.forEach((freq, i) => {
    const at = ctx.currentTime + i * 0.35;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.0001, at);
    gain.gain.exponentialRampToValueAtTime(0.3, at + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + 1.2);
    osc.connect(gain).connect(ctx.destination);
    osc.start(at);
    osc.stop(at + 1.3);
  });
}
"""

# 원형 타이머: 한 바퀴 = 한 세트, 12시 옆 휴식 조각 60° + 집중 조각 300°, 남은 부분이 12시 쪽으로 줄어듦 (와이어프레임 1-A·1-B·1-C)
DIAL_HTML = """
<div class="dial">
  <span class="chip"></span>
  <svg class="face" viewBox="0 0 240 240" role="img" aria-label="원형 타이머">
    <defs>
      <pattern id="rest-hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="8" height="8" fill="#ffffff"></rect>
        <line x1="0" y1="0" x2="0" y2="8" stroke="#33354a" stroke-width="2.5"></line>
      </pattern>
    </defs>
    <circle class="track" cx="120" cy="120" r="110"></circle>
    <path class="focus"></path>
    <path class="rest"></path>
    <circle class="ring" cx="120" cy="120" r="110"></circle>
  </svg>
  <div class="time"></div>
</div>
"""

DIAL_CSS = """
.dial { display: flex; flex-direction: column; align-items: center; gap: 14px; padding: 8px 0; }
.chip { font-size: 13px; padding: 2px 12px; border: 1px solid #c9ccd6; border-radius: 6px; color: #31333f; }
.face { width: 240px; height: 240px; }
.track { fill: #ffffff; }
.focus { fill: #33354a; }
.rest { fill: url(#rest-hatch); }
.ring { fill: none; stroke: #33354a; stroke-width: 1.5; }
.time { font-size: 44px; font-weight: 700; color: #31333f; font-variant-numeric: tabular-nums; }
"""

DIAL_JS = """
function point(deg) {  // 12시에서 시계 방향으로 deg 도 돈 테두리 위의 점
  const r = (deg * Math.PI) / 180;
  return [120 + 110 * Math.sin(r), 120 - 110 * Math.cos(r)];
}

function sector(from, to) {  // from 도에서 to 도까지 시계 방향 부채꼴
  if (to - from < 0.01) return "";
  const [x1, y1] = point(from);
  const [x2, y2] = point(to);
  return `M120,120 L${x1},${y1} A110,110 0 ${to - from > 180 ? 1 : 0} 1 ${x2},${y2} Z`;
}

function clock(seconds) {  // 남은 초 → "12:30"
  const s = Math.max(0, Math.ceil(seconds));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

export default function (component) {
  const { data, parentElement } = component;
  parentElement.__stop?.();  // 값이 바뀌어 다시 불리면 앞의 시계를 치움
  unlockSound();

  const [chip, focus, rest, time] = [".chip", ".focus", ".rest", ".time"].map((s) => parentElement.querySelector(s));
  const total = data.focus + data.rest;
  const restAngle = (data.rest / total) * 360;
  const mountedAt = Date.now();

  const draw = () => {
    const left = data.phase === "대기" ? total : Math.max(0, data.remaining - (Date.now() - mountedAt) / 1000);
    const angle = (left / total) * 360;
    const inFocus = left > data.rest;
    focus.setAttribute("d", sector(restAngle, Math.max(restAngle, angle)));
    rest.setAttribute("d", sector(0, Math.min(restAngle, angle)));
    chip.textContent = data.phase === "대기" ? "대기" : inFocus ? "집중" : "휴식";
    time.textContent = clock(data.phase === "대기" ? data.focus : inFocus ? left - data.rest : left);
  };

  draw();
  const timer = data.phase === "대기" ? null : setInterval(draw, 250);
  parentElement.__stop = () => clearInterval(timer);
  return () => parentElement.__stop();
}
"""

# 세트 엔진: 세트 동안 화면1·2·3 어디에 있든 붙어서 ① 화면이 꺼지지 않게 하고 ② 집중·세트가 끝날 때 종을 울리고
# ③ 그 순간 파이썬에 알려 화면을 다시 그리게 함 (휴식으로 바뀜 · 세트 완료 → 화면2)
ENGINE_JS = """
export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  parentElement.__stop?.();
  unlockSound();

  const marks = ((window.__byeoldoroSets ??= {})[data.set_id] ??= { focus: false, end: false });  // 같은 세트에서 종이 두 번 울리지 않게
  const mountedAt = Date.now();
  const ends = [
    ["focus", mountedAt + (data.remaining - data.rest) * 1000, [660]],
    ["end", mountedAt + data.remaining * 1000, [660, 880]],
  ];

  // when: "tick"(시계가 돌다 끝남 — 알림) · "mount"(처음 붙을 때 — 세트 끝만 알림) · "leave"(사라질 때 — 알리지 않음)
  const settle = (now, when) => {
    for (const [name, at, notes] of ends) {
      if (marks[name] || now < at) continue;
      marks[name] = true;
      if (now - at < 3000) chime(name, notes);  // 막 끝났으면 다른 탭에 있어도 종 — 컴퓨터가 잠들었다 깨는 등 늦게 알았으면 울리지 않음
      if (when === "tick" || (when === "mount" && name === "end")) setTriggerValue("boundary", now);
    }
  };

  let lock = null;
  const keepAwake = async () => {  // 세트 동안 화면이 꺼지지 않게 함 — 다른 탭에 갔다 오면 다시 요청
    if (lock || document.visibilityState !== "visible" || !("wakeLock" in navigator)) return;
    try {
      lock = await navigator.wakeLock.request("screen");
      window.__byeoldoroAwake = true;
      lock.addEventListener("release", () => { lock = null; window.__byeoldoroAwake = false; });
    } catch (e) {
      window.__byeoldoroAwake = false;
    }
  };

  const onVisible = () => {
    if (document.visibilityState !== "visible") return;
    keepAwake();
    settle(Date.now(), "tick");
  };

  settle(mountedAt, "mount");  // 이미 지난 집중 끝은 파이썬도 알고 있으므로 알리지 않음
  keepAwake();
  // 끝나는 시각에 맞춘 알람 — 다른 탭에 오래 있으면 브라우저가 반복 시계를 1분에 한 번까지 늦추므로 따로 걸어 둠
  const alarms = ends.map(([, at]) => setTimeout(() => settle(Date.now(), "tick"), Math.max(0, at - mountedAt) + 50));
  const timer = setInterval(() => settle(Date.now(), "tick"), 1000);
  document.addEventListener("visibilitychange", onVisible);

  parentElement.__stop = () => {
    alarms.forEach(clearTimeout);
    clearInterval(timer);
    document.removeEventListener("visibilitychange", onVisible);
    lock?.release();
  };
  return () => {
    settle(Date.now(), "leave");  // 파이썬이 먼저 세트를 끝내 이 부품이 사라질 때도 막 끝난 종은 울림
    parentElement.__stop();
  };
}
"""

# 부품은 쓸 때마다 등록함 — 같은 내용이면 Streamlit 이 조용히 넘어가고, 시험 도구처럼 Streamlit 을 새로 띄워도 빠지지 않음
def timer_dial(phase, remaining, length):  # 화면1 원형 타이머 — phase 는 "대기"·"집중"·"휴식", remaining 은 세트가 끝날 때까지 남은 초
    dial = st.components.v2.component("timer_dial", html=DIAL_HTML, css=DIAL_CSS, js=SOUND_JS + DIAL_JS)
    dial(key="timer_dial", data={"phase": phase, "remaining": remaining, "focus": length["집중"], "rest": length["휴식"]})


def set_engine(set_id, remaining, rest):  # 세트 동안 어느 화면에나 붙는 보이지 않는 부품 — set_id 는 세트 시작 시각
    engine = st.components.v2.component("set_engine", js=SOUND_JS + ENGINE_JS)
    engine(key="set_engine", data={"set_id": set_id, "remaining": remaining, "rest": rest}, on_boundary_change=lambda: None)
