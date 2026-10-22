import math
import os

import altair as alt
import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

st.set_page_config(page_title="맛집 대시보드", layout="wide")

# 카카오 로컬 API "키워드로 장소 검색하기" — 공식 문서(developers.kakao.com/docs/latest/ko/local/dev-guide) 기준
load_dotenv()
KAKAO_KEY = os.getenv("KAKAO_REST_API_KEY", "").strip()
SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
FOOD = "FD6"  # 카테고리 그룹 코드: 음식점
DEFAULT_AREA = "김제시청"  # 처음 기준 지역
PAGE_SIZE = 15  # 한 번에 받을 수 있는 최대 개수 (1~15)
BAR_COLOR = "#2563eb"  # 차트는 값이 한 가지라 한 색만 씀

# 구글 Places API (New) "Text Search" — 카카오에는 별점이 없어 별점만 구글 지도에서 가져옴
# rating·userRatingCount 를 받으면 Enterprise 요금 항목(매달 1,000번 무료)이라 "검색"을 누를 때 한 번만 부름
GOOGLE_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()
GOOGLE_URL = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_FIELDS = "places.displayName,places.rating,places.userRatingCount,places.formattedAddress,places.googleMapsUri,places.location"
MIN_REVIEWS = 10  # 리뷰가 몇 개뿐인 5점짜리가 1등이 되지 않게, 리뷰 10개 이상인 곳을 먼저 고름

if not KAKAO_KEY:
    st.error(".env 의 KAKAO_REST_API_KEY 가 비어 있어요. 값을 넣어 주세요.")
    st.stop()


def kakao_search(params):  # 키워드 검색 한 번 — 헤더에 "KakaoAK {REST API 키}"
    response = requests.get(
        SEARCH_URL,
        headers={"Authorization": f"KakaoAK {KAKAO_KEY}"},
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def find_center(area):  # 기준 지역의 좌표(경도 x, 위도 y) — 지역마다 한 번만 찾아 기억해 둠
    known = st.session_state.setdefault("centers", {})
    if area not in known:
        places = kakao_search({"query": area, "size": 1})["documents"]
        if not places:
            raise LookupError(f"'{area}' 위치를 찾지 못했어요. 시청·역·동 이름처럼 다르게 적어 보세요.")
        known[area] = places[0]
    return known[area]


def search_food(area, query, radius, limit):  # 기준 지역 반경 안 음식점을 가까운 순으로 limit 개까지
    center = find_center(area)
    rows = []
    for page in range(1, math.ceil(limit / PAGE_SIZE) + 1):
        result = kakao_search({
            "query": query,
            "category_group_code": FOOD,
            "x": center["x"],
            "y": center["y"],
            "radius": radius,  # 미터, 0~20000
            "sort": "distance",
            "page": page,  # 1~45
            "size": PAGE_SIZE,
        })
        rows += result["documents"]
        if result["meta"]["is_end"]:
            break
    return center, pd.DataFrame(
        [
            {
                "이름": place["place_name"],
                "분류": (place["category_name"].split(" > ") + ["", ""])[1] or "기타",  # "음식점 > 한식 > 국밥" → "한식"
                "세부 분류": place["category_name"].split(" > ")[-1],
                "거리(m)": int(place["distance"] or 0),
                "주소": place["road_address_name"] or place["address_name"],
                "전화": place["phone"],
                "카카오맵": place["place_url"],
            }
            for place in rows[:limit]
        ]
    )


def distance_m(lat1, lon1, lat2, lon2):  # 두 좌표 사이 거리(m)
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371000 * 2 * math.asin(math.sqrt(a))


def google_top_rated(center, query, radius):  # 기준 지역 반경 안에서 구글 지도 별점이 높은 식당 3곳
    response = requests.post(
        GOOGLE_URL,
        headers={"X-Goog-Api-Key": GOOGLE_KEY, "X-Goog-FieldMask": GOOGLE_FIELDS},
        json={
            "textQuery": query,
            "includedType": "restaurant",
            "languageCode": "ko",
            "regionCode": "KR",
            "pageSize": 20,  # 한 번에 받을 수 있는 최대 개수
            "locationBias": {"circle": {"center": {"latitude": float(center["y"]), "longitude": float(center["x"])}, "radius": float(radius)}},
        },
        timeout=10,
    )
    response.raise_for_status()
    rows = []
    for place in response.json().get("places", []):
        meters = distance_m(float(center["y"]), float(center["x"]), place["location"]["latitude"], place["location"]["longitude"])
        if "rating" not in place or meters > radius:  # 별점이 없거나 반경 밖이면 뺌 (locationBias 는 반경 밖도 섞여 옴)
            continue
        rows.append({
            "이름": place["displayName"]["text"],
            "별점": place["rating"],
            "리뷰 수": place.get("userRatingCount", 0),
            "거리(m)": round(meters),
            "주소": place.get("formattedAddress", ""),
            "구글 지도": place.get("googleMapsUri", ""),
        })
    if not rows:
        return pd.DataFrame()
    found = pd.DataFrame(rows)
    found["리뷰 충분"] = found["리뷰 수"] >= MIN_REVIEWS
    return found.sort_values(["리뷰 충분", "별점", "리뷰 수"], ascending=False).head(3)


def google_error_text(error):  # 구글이 돌려준 까닭을 사람이 읽을 말로
    status = getattr(error.response, "status_code", None) if isinstance(error, requests.HTTPError) else None
    if status in (400, 403):
        return "구글이 요청을 받아 주지 않았어요. 키가 맞는지, 구글 클라우드에서 Places API (New) 사용 설정과 결제 계정이 켜져 있는지 확인해 주세요."
    if status == 429:
        return "구글 검색 횟수 한도를 넘었어요. 잠시 뒤 다시 해 주세요."
    if status:
        return f"구글 별점을 가져오지 못했어요. (구글 응답 {status})"
    return "구글 별점을 가져오지 못했어요. 인터넷 연결을 확인해 주세요."


def error_text(error):  # 카카오가 돌려준 까닭을 사람이 읽을 말로
    status = getattr(error.response, "status_code", None) if isinstance(error, requests.HTTPError) else None
    detail = ""
    if status:
        try:
            detail = error.response.json().get("message", "")
        except ValueError:
            pass
    if status == 401:
        return "카카오가 키를 받아 주지 않았어요. .env 의 KAKAO_REST_API_KEY 가 REST API 키인지 확인해 주세요."
    if status == 403:
        return f"권한이 없다고 해요({detail}). 카카오 개발자 콘솔에서 [카카오맵] 사용 설정이 ON 인지 확인해 주세요."
    if status == 429:
        return "오늘 쓸 수 있는 검색 횟수를 넘었어요. 내일 다시 해 주세요."
    if status:
        return f"검색하지 못했어요. (카카오 응답 {status} {detail})"
    if isinstance(error, LookupError):
        return str(error)
    return "검색하지 못했어요. 인터넷 연결을 확인해 주세요."


# 왼쪽 위 검색 칸 — "검색"을 눌렀을 때만 카카오를 부름 (칸을 바꾸는 것만으로는 부르지 않음)
with st.sidebar.form("search"):
    area = st.text_input("지역", value=DEFAULT_AREA, help="기준이 될 곳. 예: 김제시청, 전주역, 김제시 요촌동")
    query = st.text_input("검색어", value="음식점", help="예: 국밥, 짜장면, 칼국수")
    radius = st.slider("기준 지역에서 반경 (m)", 200, 5000, 1000, step=100)
    limit = st.selectbox("최대 개수", [15, 30, 45], index=2)
    searched = st.form_submit_button("검색", type="primary", width="stretch")

if searched:
    if not area.strip() or not query.strip():
        st.sidebar.warning("지역과 검색어를 모두 적어 주세요.")
    else:
        try:
            with st.spinner("카카오에서 찾는 중…"):
                center, found = search_food(area.strip(), query.strip(), radius, limit)
            st.session_state.result = {"center": center, "places": found, "query": query.strip(), "radius": radius}
        except (requests.RequestException, LookupError) as error:
            st.sidebar.error(error_text(error))
        else:
            top_rated = None  # 구글 별점 3곳 — 구글이 안 되어도 카카오 결과는 그대로 보여 줌
            if GOOGLE_KEY:
                try:
                    with st.spinner("구글 지도 별점을 가져오는 중…"):
                        top_rated = google_top_rated(center, query.strip(), radius)
                except requests.RequestException as error:
                    top_rated = google_error_text(error)
            st.session_state.result["top_rated"] = top_rated

result = st.session_state.get("result")
if result is None:
    st.title("맛집 대시보드")
    st.info("왼쪽 위에 지역과 검색어를 적고 '검색'을 눌러 주세요.")
    st.stop()

center, places, word, meters = result["center"], result["places"], result["query"], result["radius"]
st.title(f"{center['place_name']} 근처 맛집 대시보드")
if places.empty:
    st.warning("조건에 맞는 음식점이 없어요. 반경을 넓히거나 검색어를 바꿔 보세요.")
    st.stop()
st.caption(f"기준: {center['place_name']} ({center['road_address_name'] or center['address_name']}) · 검색어 '{word}' · 반경 {meters:,}m")

st.subheader("별점 높은 식당 3곳")
top_rated = result.get("top_rated")
if not GOOGLE_KEY:
    st.info("별점은 구글 지도에서 가져와요. .env 에 GOOGLE_PLACES_API_KEY 를 넣고 다시 검색해 주세요.")
elif isinstance(top_rated, str):
    st.warning(top_rated)
elif top_rated is None or top_rated.empty:
    st.info("반경 안에서 별점이 있는 식당을 구글 지도에서 찾지 못했어요.")
else:
    for col, (_, place) in zip(st.columns(3), top_rated.iterrows()):
        with col.container(border=True):
            st.markdown(f"**{place['이름']}**")
            st.markdown(f"★ {place['별점']:.1f} · 리뷰 {place['리뷰 수']:,}개")
            st.caption(f"{place['주소']} · 기준에서 {place['거리(m)']:,}m")
            st.link_button("구글 지도에서 보기", place["구글 지도"], width="stretch")
    st.caption(f"구글 지도 별점 기준 · 리뷰 {MIN_REVIEWS}개 이상인 곳을 먼저 고름 · 아래 목록(카카오)과는 따로 찾은 결과예요")

# 정렬·분류 고르기 — 받아 둔 결과로만 하므로 카카오를 다시 부르지 않음
left, right = st.columns([1, 2])
order = left.selectbox("정렬", ["가까운 순", "먼 순", "이름순", "분류순"])
kinds = sorted(places["분류"].unique())
chosen = right.multiselect("분류", kinds, default=kinds)

shown = places[places["분류"].isin(chosen)]
by, ascending = {
    "가까운 순": (["거리(m)"], True),
    "먼 순": (["거리(m)"], False),
    "이름순": (["이름"], True),
    "분류순": (["분류", "거리(m)"], True),
}[order]
shown = shown.sort_values(by, ascending=ascending).reset_index(drop=True)

if shown.empty:
    st.warning("고른 분류가 없어요. 분류를 하나 이상 골라 주세요.")
    st.stop()

a, b, c = st.columns(3)
a.metric("찾은 음식점", f"{len(shown)}곳")
b.metric("평균 거리", f"{shown['거리(m)'].mean():,.0f}m")
nearest = shown.loc[shown["거리(m)"].idxmin()]
c.metric(f"가장 가까운 곳 · {nearest['거리(m)']:,}m", nearest["이름"])

chart_left, chart_right = st.columns(2)

with chart_left:
    st.subheader("분류별 음식점 수")
    counts = shown.groupby("분류").size().reset_index(name="음식점 수")
    st.altair_chart(
        alt.Chart(counts)
        .mark_bar(color=BAR_COLOR, cornerRadiusEnd=4)
        .encode(
            x=alt.X("음식점 수:Q", title="음식점 수", axis=alt.Axis(tickMinStep=1)),
            y=alt.Y("분류:N", sort="-x", title=None),
            tooltip=["분류", "음식점 수"],
        ),
        width="stretch",
    )

with chart_right:
    st.subheader("거리별 음식점 수")
    step = max(100, int(round(meters / 5, -2)))  # 반경을 다섯 구간쯤으로 나눔 (100m 단위)
    bands = (shown["거리(m)"] // step * step).astype(int)
    by_distance = (
        bands.value_counts()
        .reindex(range(0, int(bands.max()) + step, step), fill_value=0)
        .rename_axis("시작")
        .reset_index(name="음식점 수")
    )
    by_distance["거리"] = by_distance["시작"].map(lambda s: f"{s:,}~{s + step:,}m")
    st.altair_chart(
        alt.Chart(by_distance)
        .mark_bar(color=BAR_COLOR, cornerRadiusEnd=4)
        .encode(
            x=alt.X("거리:N", sort=None, title=f"{center['place_name']}에서 거리", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("음식점 수:Q", title="음식점 수", axis=alt.Axis(tickMinStep=1)),
            tooltip=["거리", "음식점 수"],
        ),
        width="stretch",
    )

st.subheader("음식점 목록")
st.dataframe(
    shown,
    hide_index=True,
    width="stretch",
    column_config={
        "거리(m)": st.column_config.NumberColumn(format="%d m"),
        "카카오맵": st.column_config.LinkColumn(display_text="열기"),
    },
)
