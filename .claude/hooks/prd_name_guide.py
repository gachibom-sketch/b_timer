"""PRD 이름 안내 훅.

UserPromptSubmit 때 실행된다. my_service 에서는 기획서 이름이 PRD.md 라서
사용자 글에 예전 이름 PRD2.md 가 나오면
1) 맨 앞 경고창을 띄우고 2) AI에게 PRD.md 로 진행하라고 알린다.
글은 막지 않는다. PRD.md 만 나온 글에는 아무것도 하지 않는다.
"""
import ctypes
import json
import ntpath
import os
import re
import subprocess
import sys

OLD_NAME = re.compile(r"prd2\.md", re.IGNORECASE)  # prd.md 는 걸리지 않는다
TITLE = "PRD 이름 안내"
MESSAGE = "[PRD2.md 가 아니라 PRD.md 로 진행합니다]"
CONTEXT = (
    "사용자가 PRD2.md 를 언급했지만 이 폴더(my_service)에서는 기획서 이름이 PRD.md 다. "
    "PRD2.md 대신 PRD.md 를 기준으로 작업을 진행하고, 답에 그렇게 바꿔 진행했다고 한 줄 적어라."
)

# MessageBoxW 옵션: 확인 버튼 + 정보 아이콘 + 시스템 모달 + 항상 맨 앞 + 앞으로 가져오기
MB_OK = 0x0
MB_ICONINFORMATION = 0x40
MB_SYSTEMMODAL = 0x1000
MB_SETFOREGROUND = 0x10000
MB_TOPMOST = 0x40000


def show_popup():
    ctypes.windll.user32.MessageBoxW(
        None, MESSAGE, TITLE,
        MB_OK | MB_ICONINFORMATION | MB_SYSTEMMODAL | MB_SETFOREGROUND | MB_TOPMOST,
    )


def launch_popup_detached():
    # 훅이 확인 버튼을 기다리지 않도록 경고창은 따로 떨어진 프로세스로 띄운다.
    exe = sys.executable
    pythonw = ntpath.join(ntpath.dirname(exe), "pythonw.exe")
    if os.path.exists(pythonw):
        exe = pythonw
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    subprocess.Popen(
        [exe, os.path.abspath(__file__), "--popup"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
    )


def main():
    if "--popup" in sys.argv:
        show_popup()
        return

    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except Exception:
        return  # 입력을 못 읽으면 넘어간다

    prompt = data.get("prompt") or ""
    if not OLD_NAME.search(prompt):
        return  # PRD2.md 언급이 없으면 통과

    if os.environ.get("PRD_GUIDE_NO_POPUP") != "1":  # 시험할 때만 경고창을 끈다
        try:
            launch_popup_detached()
        except Exception:
            pass  # 경고창이 실패해도 안내는 그대로 한다

    sys.stdout.buffer.write(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": CONTEXT,
        }
    }, ensure_ascii=False).encode("utf-8"))


if __name__ == "__main__":
    main()
