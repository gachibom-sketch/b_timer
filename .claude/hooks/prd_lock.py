# 아래 따옴표 세 개 묶음은 이 파일 전체 설명이다 (코드라서 안쪽은 그대로 둔다)
"""PRD.md 자물쇠 훅.

PreToolUse(Edit|Write) 때 실행된다. 고치려는 파일 이름이 PRD.md 이면
1) 동작을 막고 2) 맨 앞 경고창을 띄우고 3) AI에게 이유를 돌려보낸다.
다른 파일은 아무것도 하지 않고 통과시킨다.
"""
import ctypes  # 윈도우 기능(경고창)을 부르는 도구를 가져온다
import json  # Claude Code 와 주고받는 JSON 글을 읽고 쓰는 도구를 가져온다
import ntpath  # 윈도우 파일 경로를 나누는 도구를 가져온다
import os  # 파일이 있는지 보고 경로를 다루는 도구를 가져온다
import subprocess  # 다른 프로그램(경고창용 파이썬)을 따로 띄우는 도구를 가져온다
import sys  # 입력·출력과 실행 인자를 다루는 도구를 가져온다

LOCKED_NAME = "prd.md"  # 대소문자 무시
TITLE = "PRD 자물쇠"  # 경고창 제목
MESSAGE = "[기획서는 직접 고쳐 주세요]"  # 경고창 본문
REASON = "PRD.md 는 잠겨 있으니 고치지 말고 바꿀 내용을 제안만 하라"  # AI에게 돌려보낼 막은 이유

# MessageBoxW 옵션: 확인 버튼 + 경고 아이콘 + 시스템 모달 + 항상 맨 앞 + 앞으로 가져오기
MB_OK = 0x0  # 확인 버튼 하나만 둔다
MB_ICONWARNING = 0x30  # 노란 느낌표 경고 아이콘을 붙인다
MB_SYSTEMMODAL = 0x1000  # 다른 창보다 먼저 답해야 하는 창으로 만든다
MB_SETFOREGROUND = 0x10000  # 창을 앞으로 가져온다
MB_TOPMOST = 0x40000  # 다른 창에 가려지지 않게 항상 맨 위에 둔다


def show_popup():  # 경고창을 실제로 띄우는 함수
    ctypes.windll.user32.MessageBoxW(  # 윈도우 기본 경고창 함수를 부른다
        None, MESSAGE, TITLE,  # 주인 창 없음, 본문, 제목
        MB_OK | MB_ICONWARNING | MB_SYSTEMMODAL | MB_SETFOREGROUND | MB_TOPMOST,  # 위 옵션을 모두 합친다
    )  # 경고창 함수 부르기 끝


def launch_popup_detached():  # 경고창을 따로 떨어진 프로그램으로 띄우는 함수
    # 훅이 확인 버튼을 기다리지 않도록 경고창은 따로 떨어진 프로세스로 띄운다.
    exe = sys.executable  # 지금 돌고 있는 파이썬 프로그램 위치
    pythonw = ntpath.join(ntpath.dirname(exe), "pythonw.exe")  # 같은 폴더의 검은 창 없는 파이썬 위치
    if os.path.exists(pythonw):  # 검은 창 없는 파이썬이 있으면
        exe = pythonw  # 그것을 쓴다 (검은 창이 잠깐 뜨지 않게)
    DETACHED_PROCESS = 0x00000008  # 새 프로그램을 지금 창과 떼어 놓는 옵션
    CREATE_NEW_PROCESS_GROUP = 0x00000200  # 새 프로그램을 따로 된 묶음으로 만드는 옵션
    subprocess.Popen(  # 새 프로그램을 띄우고 끝나기를 기다리지 않는다
        [exe, os.path.abspath(__file__), "--popup"],  # 이 파일을 "--popup" 표시와 함께 다시 실행한다
        stdin=subprocess.DEVNULL,  # 입력은 받지 않는다
        stdout=subprocess.DEVNULL,  # 출력은 버린다
        stderr=subprocess.DEVNULL,  # 오류 출력도 버린다
        close_fds=True,  # 지금 열린 파일 연결을 넘겨주지 않는다
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,  # 위 두 옵션으로 완전히 떼어 띄운다
    )  # 새 프로그램 띄우기 끝


def main():  # 훅이 불리면 처음 실행되는 함수
    if "--popup" in sys.argv:  # 경고창용으로 다시 실행된 경우면
        show_popup()  # 경고창만 띄우고
        return  # 끝낸다

    try:  # 입력 읽기를 시도한다
        data = json.loads(sys.stdin.buffer.read().decode("utf-8"))  # Claude Code 가 보낸 JSON 을 읽는다
    except Exception:  # 읽다가 문제가 생기면
        return  # 입력을 못 읽으면 막지 않는다

    tool_input = data.get("tool_input") or {}  # AI가 도구에 넘긴 값(없으면 빈 묶음)
    if data.get("tool_name") in ("Bash", "PowerShell"):  # AI가 명령 줄 도구를 쓰려는 경우
        # 명령 줄 도구는 명령 문장에 PRD.md 가 들어 있으면 막는다
        command = tool_input.get("command") or ""  # 실행하려는 명령 문장
        if LOCKED_NAME not in command.lower():  # 소문자로 바꾼 명령에 prd.md 가 없으면
            return  # 다른 명령은 통과
    else:  # 파일을 고치는 도구(Edit·Write)를 쓰려는 경우
        file_path = tool_input.get("file_path") or ""  # 고치려는 파일 경로
        if ntpath.basename(file_path).lower() != LOCKED_NAME:  # 파일 이름이 prd.md 가 아니면
            return  # 다른 파일은 통과

    try:  # 경고창 띄우기를 시도한다
        launch_popup_detached()  # 경고창을 따로 띄운다
    except Exception:  # 띄우다가 문제가 생기면
        pass  # 경고창이 실패해도 막는 것은 그대로 한다

    print(json.dumps({  # Claude Code 에 돌려줄 답을 JSON 으로 출력한다
        "hookSpecificOutput": {  # 훅 전용 답 묶음
            "hookEventName": "PreToolUse",  # 도구를 쓰기 직전 훅이라는 표시
            "permissionDecision": "deny",  # 이 동작을 막는다
            "permissionDecisionReason": REASON,  # 막은 이유를 AI에게 알려 준다
        }  # 훅 전용 답 묶음 끝
    }))  # 출력 끝


if __name__ == "__main__":  # 이 파일을 직접 실행했을 때만
    main()  # main 함수를 부른다
