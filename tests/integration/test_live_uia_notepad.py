import os
import platform
import time

import pytest


WINDOWS = platform.system().lower() == "windows"
RUN_LIVE = os.environ.get("RUN_LIVE_TESTS") == "1"


pytestmark = [
    pytest.mark.skipif(not WINDOWS, reason="Windows-only integration test"),
    pytest.mark.skipif(not RUN_LIVE, reason="Set RUN_LIVE_TESTS=1 to enable live integration tests"),
]


def _launch_notepad():
    try:
        from pywinauto.application import Application  # type: ignore
    except Exception as e:  # pragma: no cover
        pytest.skip(f"pywinauto not available: {e}")
    app = Application(backend="uia").start("notepad.exe")
    # Wait for main window
    win = app.window(class_name="Notepad")
    win.wait("ready", timeout=5)
    return app, win


def _cleanup_notepad(app):
    try:
        app.kill()
    except Exception:
        pass


def test_uia_set_value_in_notepad():
    # Launch Notepad and set text in the edit area using our WinUIA wrapper
    app, win = _launch_notepad()
    try:
        time.sleep(0.5)
        from tools.win_uia import WinUIA

        uia = WinUIA(timeout_ms=2000)
        # Limit search to active window, look for Edit control
        found = uia.find({"control_type": "Edit"}, scope="active_window")
        assert isinstance(found, list)
        assert len(found) > 0, "Edit control not found in Notepad window"

        ok = uia.set_value(found[0], "Hello from live UIA test")
        assert ok, "UIA_SET_VALUE failed"

        # Try invoking the Format menu via UIA if present (non-fatal)
        menus = uia.find({"name": "Format"}, scope="active_window")
        if menus:
            uia.invoke(menus[0])
        time.sleep(0.3)
    finally:
        _cleanup_notepad(app)
