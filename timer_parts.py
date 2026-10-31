import math

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

# 원형 타이머: 한 바퀴 = 한 세트, 집중 조각 300°(12시→10시) + 휴식 조각 60°(10시→12시), 남은 부분이 12시 쪽으로 줄어듦
# 지나간 시간은 시곗바늘처럼 12시에서 시계 방향으로 자람 (2026-10-31 바꿈 — 와이어프레임 1-B 는 반대 방향이었음)
# 색은 "남은 시간만 색" — 지나간 부분은 흰색, 남은 집중·휴식은 남색 두 톤 + 원 바깥 옅은 남색 고리
# (2026-10-31 스티치 안 1 · 밤하늘 두 톤, idea/screens/토스판/원판_안_1031/ · 규칙은 idea/screens/토스판/DESIGN.md)
# 노랑은 흰 바탕과 1.30:1 이라 원판에 쓰지 않음 · 대기 때만 원 아래에 집중·휴식 범례
# 눈금은 60° 마다 6개 = 한 칸 5분(시연 모드는 12초) — 휴식은 10시~12시 한 칸, 집중은 다섯 칸. 12개면 한 칸 2.5분이라 벽시계처럼 5분으로 잘못 읽힘
TICKS = "".join(  # 고리 위의 짧은 선 — 12시(시작이자 끝)만 조금 길고 굵게
    f'<line x1="{120 + r1 * s:.1f}" y1="{120 - r1 * c:.1f}" x2="{120 + r2 * s:.1f}" y2="{120 - r2 * c:.1f}" stroke-width="{w}"></line>'
    for a, r1, r2, w in ((a, *((104, 116, 2.5) if a == 0 else (106, 114, 2))) for a in range(0, 360, 60))
    for s, c in [(math.sin(math.radians(a)), math.cos(math.radians(a)))]
)

DIAL_HTML = f"""
<div class="dial">
  <span class="chip"></span>
  <svg class="face" viewBox="0 0 240 240" role="img" aria-label="원형 타이머">
    <circle class="track" cx="120" cy="120" r="100"></circle>
    <path class="focus"></path>
    <path class="rest"></path>
    <circle class="ring" cx="120" cy="120" r="110"></circle>
    <g class="ticks">{TICKS}</g>
    <circle class="hub" cx="120" cy="120" r="9"></circle>
    <circle class="pin" cx="120" cy="120" r="3.5"></circle>
  </svg>
  <div class="legend"><span class="key focus-key"></span><span class="focus-text"></span><span class="sep">·</span><span class="key rest-key"></span><span class="rest-text"></span></div>
  <div class="time"></div>
</div>
"""

DIAL_CSS = """
.dial { display: flex; flex-direction: column; align-items: center; gap: 18px; padding: 8px 0; }
.chip { display: inline-flex; align-items: center; gap: 8px; padding: 6px 16px; border-radius: 999px; background: #1C2650; color: #FFE14D; font-size: 15px; font-weight: 700; }
.chip::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: #FFE14D; }
.chip[hidden] { display: none; }
.face { width: 240px; height: 240px; }
.track { fill: #FFFFFF; }
.focus { fill: #101838; }
.rest { fill: #5064B8; }
.ring { fill: none; stroke: #E8EDF8; stroke-width: 8; }
.ticks line { stroke: #94A6D4; stroke-linecap: round; }
.legend { display: flex; align-items: center; gap: 6px; font-size: 14px; color: #6B7684; }
.legend[hidden] { display: none; }
.key { width: 10px; height: 10px; border-radius: 50%; }
.focus-key { background: #101838; }
.rest-key { background: #5064B8; }
.sep { margin: 0 4px; }
.hub { fill: #FFFFFF; stroke: #191F28; stroke-width: 3; }
.pin { fill: #191F28; }
.time { font-size: 60px; line-height: 1.1; font-weight: 700; color: #191F28; font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
"""

DIAL_JS = """
function point(deg) {  // 12시에서 시계 방향으로 deg 도 돈 파이 둘레(반지름 100) 위의 점
  const r = (deg * Math.PI) / 180;
  return [120 + 100 * Math.sin(r), 120 - 100 * Math.cos(r)];
}

function sector(from, to) {  // from 도에서 to 도까지 시계 방향 부채꼴
  if (to - from < 0.01) return "";
  const [x1, y1] = point(from);
  const [x2, y2] = point(to);
  return `M120,120 L${x1},${y1} A100,100 0 ${to - from > 180 ? 1 : 0} 1 ${x2},${y2} Z`;
}

function span(seconds) {  // 단계 길이 → "25분" · 시연 모드(…/?demo=1)의 휴식 12초는 "12초"
  return seconds % 60 ? `${seconds}초` : `${seconds / 60}분`;
}

function clock(seconds) {  // 남은 초 → "12:30"
  const s = Math.max(0, Math.ceil(seconds));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

export default function (component) {
  const { data, parentElement } = component;
  parentElement.__stop?.();  // 값이 바뀌어 다시 불리면 앞의 시계를 치움
  unlockSound();

  const [chip, focus, rest, time, legend] = [".chip", ".focus", ".rest", ".time", ".legend"].map((s) => parentElement.querySelector(s));
  legend.hidden = data.phase !== "대기";  // 범례는 대기 때만 — 밝은 휴식 조각을 "지나간 시간"으로 읽지 않게
  parentElement.querySelector(".focus-text").textContent = `집중 ${span(data.focus)}`;
  parentElement.querySelector(".rest-text").textContent = `휴식 ${span(data.rest)}`;
  const total = data.focus + data.rest;
  const focusEnd = (data.focus / total) * 360;  // 집중 조각이 끝나는 자리(10시) — 그 뒤 12시까지가 휴식 조각
  const mountedAt = Date.now();

  const draw = () => {
    const left = data.phase === "대기" ? total : Math.max(0, data.remaining - (Date.now() - mountedAt) / 1000);
    const passed = 360 - (left / total) * 360;  // 12시에서 시계 방향으로 지나간 만큼
    const inFocus = left > data.rest;
    focus.setAttribute("d", sector(passed, focusEnd));
    rest.setAttribute("d", sector(Math.max(passed, focusEnd), 360));
    chip.hidden = data.phase === "대기";  // 대기에는 꼬리표 없음 (토스판 1A)
    chip.textContent = inFocus ? "집중 중" : "휴식 중";
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
