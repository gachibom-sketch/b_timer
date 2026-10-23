import os
import uuid
from datetime import datetime

import requests
import streamlit as st
from dotenv import load_dotenv

st.set_page_config(page_title="사진 보관함")
st.title("사진 보관함")
st.caption("Supabase Storage 의 photos 버킷에 그림을 올리고, 올라와 있는 그림을 모두 보여 줍니다.")

# .env 에서 Supabase 주소와 키를 읽음
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error(".env 에 SUPABASE_URL 과 SUPABASE_KEY 를 넣어 주세요.")
    st.stop()

BUCKET = "photos"
STORAGE_URL = f"{SUPABASE_URL}/storage/v1"
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
PICTURE_TYPES = ["png", "jpg", "jpeg", "gif", "webp"]
MAX_MB = 5  # 한 장의 크기 한도 — SQL 로 만든 photos 버킷의 한도(5MB)와 같음
PAGE_SIZE = 100  # 목록은 100개씩 나눠 불러옴
LINK_SECONDS = 3600  # 그림 주소(서명된 주소)를 쓸 수 있는 시간 — 공개·비공개 버킷 모두에서 그림이 보이게 이 주소를 씀


def stored_name(file_name):  # 버킷에 넣을 이름 — 올린 시각 + 무작위 6글자 + 확장자
    # 덮어쓰기는 허용하지 않아 이름이 겹치면 안 되고, 한글 같은 글자는 Storage 가 파일 이름으로 받지 않을 수 있어 원래 이름은 쓰지 않음
    extension = os.path.splitext(file_name)[1].lower()
    return f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}{extension}"


def upload_picture(file):  # 그림 한 장을 photos 버킷에 올림
    response = requests.post(
        f"{STORAGE_URL}/object/{BUCKET}/{stored_name(file.name)}",
        headers={**HEADERS, "Content-Type": file.type or "application/octet-stream", "x-upsert": "false"},
        data=file.getvalue(),
        timeout=30,
    )
    response.raise_for_status()


def upload_error_text(response):  # Storage 가 알려 준 까닭을 사람이 읽을 말로
    try:
        message = response.json().get("message", "")
    except ValueError:
        message = ""
    if "row-level security" in message:
        return '올리기가 허용되지 않았어요. SQL Editor 에서 "photos 올리기" 허용을 넣어 주세요.'
    if "Bucket not found" in message:
        return "photos 버킷이 없어요. SQL Editor 에서 버킷을 만드는 SQL 을 실행해 주세요."
    if "mime type" in message.lower():
        return "이 버킷에는 그림 파일만 올릴 수 있어요."
    if "maximum allowed size" in message or response.status_code == 413:
        return "버킷의 크기 한도보다 커서 올리지 못했어요."
    return f"올리지 못했어요. (Storage 응답 {response.status_code} {message})"


def load_pictures():  # photos 버킷 맨 위 칸의 그림 전부, 새것부터
    pictures, offset = [], 0
    while True:
        response = requests.post(
            f"{STORAGE_URL}/object/list/{BUCKET}",
            headers=HEADERS,
            json={"prefix": "", "limit": PAGE_SIZE, "offset": offset, "sortBy": {"column": "created_at", "order": "desc"}},
            timeout=10,
        )
        response.raise_for_status()
        page = response.json()
        # 폴더(id 없음)와 그림이 아닌 파일은 빼고 보여 줌
        pictures += [row for row in page if row.get("id") and (row.get("metadata") or {}).get("mimetype", "").startswith("image/")]
        if len(page) < PAGE_SIZE:
            return pictures
        offset += PAGE_SIZE


@st.cache_data(ttl=LINK_SECONDS - 600)  # 주소가 끝나기 10분 전까지는 같은 주소를 다시 써서, 화면을 다시 그릴 때마다 그림을 새로 받지 않게
def picture_links(names):  # 그림 이름들 → {이름: 그림 주소}
    response = requests.post(
        f"{STORAGE_URL}/object/sign/{BUCKET}",
        headers=HEADERS,
        json={"expiresIn": LINK_SECONDS, "paths": list(names)},
        timeout=10,
    )
    response.raise_for_status()
    return {row["path"]: f"{STORAGE_URL}{row['signedURL']}" for row in response.json() if row.get("signedURL")}


def uploaded_time_text(created_at):  # 2026-10-23T11:22:28.960Z → 10월 23일 20:22 (내 컴퓨터 시간대)
    uploaded = datetime.fromisoformat(created_at).astimezone()
    return f"{uploaded.month}월 {uploaded.day}일 {uploaded:%H:%M}"


with st.form("upload", clear_on_submit=True):
    files = st.file_uploader("올릴 그림", type=PICTURE_TYPES, accept_multiple_files=True, max_upload_size=MAX_MB)  # 한도보다 큰 그림은 고르는 칸에서 바로 막음
    if st.form_submit_button("올리기"):
        if not files:
            st.warning("올릴 그림을 골라 주세요.")
        uploaded = 0
        for file in files:
            try:
                upload_picture(file)
            except requests.HTTPError as error:
                st.error(f"{file.name}: {upload_error_text(error.response)}")
            except requests.RequestException:
                st.error(f"{file.name}: 올리지 못했어요. 인터넷 연결을 확인하고 다시 해 주세요.")
            else:
                uploaded += 1
        if uploaded:
            st.success(f"{uploaded}장을 올렸어요.")

try:
    pictures = load_pictures()
except requests.RequestException:
    st.error("그림 목록을 불러오지 못했어요. .env 의 주소와 키, photos 버킷이 있는지 확인해 주세요.")
    st.stop()

if not pictures:
    st.caption('아직 올라온 그림이 없어요. 올렸는데 안 보이면 SQL Editor 에서 "photos 목록 보기" 허용을 넣었는지 확인해 주세요.')
    st.stop()

st.caption(f"모두 {len(pictures)}장")
try:
    links = picture_links(tuple(picture["name"] for picture in pictures))
except requests.RequestException:
    st.error("그림 주소를 만들지 못했어요. 잠시 뒤 다시 열어 주세요.")
    st.stop()

columns = st.columns(3)
for index, picture in enumerate(pictures):
    with columns[index % 3]:
        link = links.get(picture["name"])
        if link:
            st.image(link, caption=uploaded_time_text(picture["created_at"]), width="stretch")
        else:
            st.caption(f"{picture['name']} 은 보여 주지 못했어요.")
