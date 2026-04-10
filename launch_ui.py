from __future__ import annotations

import socket
import subprocess
import sys
import threading
import time
import webbrowser
from ctypes import windll

from werkzeug.serving import make_server

from job_alert.ui import create_app, ui_runtime_state


HOST = "127.0.0.1"
PORT = 5000
URL = f"http://{HOST}:{PORT}"
STARTUP_GRACE_SECONDS = 30
IDLE_SHUTDOWN_SECONDS = 15
MONITOR_INTERVAL_SECONDS = 3

app = create_app()


def listener_pid(port: int) -> int | None:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        f"$conn = Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1; if ($conn) {{ Write-Output $conn.OwningProcess }}",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    raw = result.stdout.strip()
    return int(raw) if raw.isdigit() else None


def process_command_line(pid: int) -> str:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        f"$proc = Get-CimInstance Win32_Process -Filter \"ProcessId = {pid}\"; if ($proc) {{ Write-Output $proc.CommandLine }}",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    return result.stdout.strip()


def ensure_port_available(host: str, port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        in_use = sock.connect_ex((host, port)) == 0
    if not in_use:
        return

    pid = listener_pid(port)
    if pid is None:
        raise RuntimeError(f"Port {port} is already in use.")

    command_line = process_command_line(pid)
    if "launch_ui.py" in command_line:
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True)
        return

    raise RuntimeError(f"Port {port} is already in use by another program (PID {pid}).")


def open_browser() -> None:
    try:
        webbrowser.open(URL)
    except Exception:
        pass


def show_error_message(message: str) -> None:
    try:
        windll.user32.MessageBoxW(0, message, "Job Alert UI", 0x10)
    except Exception:
        pass


def monitor_ui_idle(server) -> None:
    startup_deadline = time.monotonic() + STARTUP_GRACE_SECONDS
    idle_started_at: float | None = None

    while True:
        time.sleep(MONITOR_INTERVAL_SECONDS)
        state = ui_runtime_state()
        has_session = int(state.get("active_session_count", 0)) > 0
        has_active_run = bool(state.get("has_active_run"))

        if has_session or has_active_run:
            idle_started_at = None
            continue

        now = time.monotonic()
        if now < startup_deadline:
            continue

        if idle_started_at is None:
            idle_started_at = now
            continue

        if now - idle_started_at >= IDLE_SHUTDOWN_SECONDS:
            try:
                server.shutdown()
            except Exception:
                pass
            return


if __name__ == "__main__":
    try:
        ensure_port_available(HOST, PORT)
    except RuntimeError as exc:
        print(exc)
        show_error_message(str(exc))
        sys.exit(1)

    try:
        server = make_server(HOST, PORT, app, threaded=True)
        threading.Timer(1.0, open_browser).start()
        threading.Thread(target=monitor_ui_idle, args=(server,), daemon=True).start()
        server.serve_forever()
    except Exception as exc:
        show_error_message(f"Job Alert UI failed to start.\n\n{exc}")
        raise
