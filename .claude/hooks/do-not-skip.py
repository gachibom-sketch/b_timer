"""do-not-skip 훅.

PreToolUse(Edit|Write|MultiEdit) 때 실행된다. idea/ 아래 코드 파일에
일시정지·휴식 건너뛰기를 넣으려 하면 1) 동작을 막고 2) 맨 앞 경고창을 띄우고
3) AI에게 이유를 돌려보낸다.
근거: CLAUDE.md 절대 규칙 3, PRD.md 비목표.
.md 같은 문서는 비목표를 설명하느라 이 낱말을 쓰므로 보지 않는다.
"""
import ctypes
import json
import ntpath
import os
import re
import subprocess
import sys

CODE_EXTS = (".html", ".htm", ".js", ".mjs", ".cjs", ".ts", ".jsx", ".tsx",
             ".css", ".vue", ".svelte")
BANNED = re.compile(r"일시\s*정지|건너뛰|pause|skip", re.IGNORECASE)
# 일시정지 버튼이 아닌 정해진 웹 낱말은 통과시킨다
ALLOWED = re.compile(r"skipWaiting|animation-play-state\s*:\s*paused", re.IGNORECASE)
REASON = (
    "do-not-skip: 일시정지와 휴식 건너뛰기는 PRD.md 비목표라 화면에도 코드에도 넣지 않는다"
    "(CLAUDE.md 절대 규칙 3). 걸린 낱말: {words}. 설명 줄에도 쓰지 말고, "
    "버튼이 아닌 다른 뜻이 꼭 필요하면 사용자에게 먼저 물어라."
)
TITLE = "do-not-skip"
MESSAGE = "[일시정지·휴식 건너뛰기는 만들지 않아요]\n\n걸린 낱말: {words}\n파일: {file}"

# MessageBoxW 옵션: 확인 버튼 + 경고 아이콘 + 시스템 모달 + 항상 맨 앞 + 앞으로 가져오기
MB_OK = 0x0
MB_ICONWARNING = 0x30
MB_SYSTEMMODAL = 0x1000
MB_SETFOREGROUND = 0x10000
MB_TOPMOST = 0x40000


def show_popup(text):
    ctypes.windll.user32.MessageBoxW(
        None, text, TITLE,
        MB_OK | MB_ICONWARNING | MB_SYSTEMMODAL | MB_SETFOREGROUND | MB_TOPMOST,
    )


def launch_popup_detached(text):
    # 훅이 확인 버튼을 기다리지 않도록 경고창은 따로 떨어진 프로세스로 띄운다.
    exe = sys.executable
    pythonw = ntpath.join(ntpath.dirname(exe), "pythonw.exe")
    if os.path.exists(pythonw):
        exe = pythonw
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    subprocess.Popen(
        [exe, os.path.abspath(__file__), "--popup", text],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
    )


def new_text(tool_name, tool_input):
    # 새로 들어갈 글만 본다 (이미 있던 글은 보지 않는다)
    if tool_name == "Write":
        return tool_input.get("content") or ""
    if tool_name == "Edit":
        return tool_input.get("new_string") or ""
    if tool_name == "MultiEdit":
        return "\n".join(e.get("new_string") or "" for e in tool_input.get("edits") or [])
    return ""


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--popup":
        show_popup(sys.argv[2])
        return

    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except Exception:
        return  # 입력을 못 읽으면 막지 않는다

    tool_input = data.get("tool_input") or {}
    path = (tool_input.get("file_path") or "").replace("\\", "/").lower()
    if "/idea/" not in path and not path.startswith("idea/"):
        return  # idea/ 밖은 통과
    if not path.endswith(CODE_EXTS):
        return  # 코드 파일이 아니면 통과

    text = ALLOWED.sub("", new_text(data.get("tool_name"), tool_input))
    words = sorted({m.group(0) for m in BANNED.finditer(text)})
    if not words:
        return  # 걸린 낱말이 없으면 통과

    if os.environ.get("DO_NOT_SKIP_NO_POPUP") != "1":  # 시험할 때만 경고창을 끈다
        try:
            file_name = ntpath.basename(tool_input.get("file_path") or "")
            launch_popup_detached(MESSAGE.format(words=", ".join(words), file=file_name))
        except Exception:
            pass  # 경고창이 실패해도 막는 것은 그대로 한다

    sys.stdout.buffer.write(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": REASON.format(words=", ".join(words)),
        }
    }, ensure_ascii=False).encode("utf-8"))


if __name__ == "__main__":
    main()
