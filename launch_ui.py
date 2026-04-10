from __future__ import annotations

import threading
import webbrowser

from job_alert.ui import create_app


HOST = "127.0.0.1"
PORT = 5000
URL = f"http://{HOST}:{PORT}"

app = create_app()


def open_browser() -> None:
    try:
        webbrowser.open(URL)
    except Exception:
        pass


if __name__ == "__main__":
    threading.Timer(1.0, open_browser).start()
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
