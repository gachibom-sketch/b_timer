-- 목표 표 goal_log — 한 줄 = 한 사람의 한 기간 (PRD 6판 "구현 필수 조건"의 목표 표)
-- Supabase 관리 화면 > SQL Editor 에 이 파일 전체를 붙여 넣고 Run 을 한 번 누르면 됨
-- 앱 키(anon)는 읽기 · 넣기 · 고치기만 하고 지우지는 못함 (progress 표와 같음)
-- 구조 설명: idea/목표 기록 구조.md

create table public.goal_log (
  id            bigint generated always as identity primary key,
  tester        text    not null,  -- 테스터 번호(…/?t=07 의 07), 시연 모드는 '0'
  constellation text    not null,  -- 별자리 — cassiopeia · orion · big_dipper (constellations.py 의 key)
  period        text    not null check (period in ('하루', '한 주')),  -- 기간 종류
  period_start  date    not null,  -- 기간 시작일(한국 시각) — 하루는 그날, 한 주는 그 주 월요일
  target        integer not null check (target > 0),                -- 목표 세트 수
  set_count     integer not null default 0 check (set_count >= 0),  -- 이번 기간 세트 수
  completed     boolean generated always as (set_count >= target) stored,  -- 완성 여부 — 저절로 계산됨
  source        text    not null check (source in ('추천', '이어서', '고름')),  -- 정한 방법 — 처음 추천 · 지난번 별자리 이어서 · 화면0 에서 고름
  created_at    timestamptz not null default now(),
  unique (tester, period, period_start)  -- 한 사람이 같은 기간에 두 줄을 갖지 않음
);

alter table public.goal_log enable row level security;
create policy "goal_log 읽기"   on public.goal_log for select to anon using (true);
create policy "goal_log 넣기"   on public.goal_log for insert to anon with check (true);
create policy "goal_log 고치기" on public.goal_log for update to anon using (true) with check (true);

-- 판정할 때 쓸 셈 (지금은 실행하지 않아도 됨 — 시연 줄 '0' 과 세트 0개인 기간은 뺌)
-- ⑤ 목표 달성률:
--   select round(100.0 * count(*) filter (where completed) / nullif(count(*), 0), 1) as 달성률
--   from goal_log where tester <> '0' and set_count > 0;
-- ⑥ 목표를 채운 뒤에도 세트를 더 한 사람 수:
--   select count(distinct tester) from goal_log where tester <> '0' and set_count > target;
-- 11/5 시험 — 오리온자리 말고 다른 별자리를 고른 사람 수:
--   select count(distinct tester) from goal_log where tester <> '0' and source = '고름' and constellation <> 'orion';
