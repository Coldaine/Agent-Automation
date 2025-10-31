import os
import platform
import threading
import time

import pytest


WINDOWS = platform.system().lower() == "windows"
RUN_LIVE = os.environ.get("RUN_LIVE_TESTS") == "1"


pytestmark = [
    pytest.mark.skipif(not WINDOWS, reason="Windows-only integration test"),
    pytest.mark.skipif(not RUN_LIVE, reason="Set RUN_LIVE_TESTS=1 to enable live integration tests"),
]


def _ensure_tesseract():
    try:
        import pytesseract  # type: ignore
        # This will raise if Tesseract binary is not found
        _ = pytesseract.get_tesseract_version()  # type: ignore[attr-defined]
    except Exception as e:  # pragma: no cover
        pytest.skip(f"Tesseract not available: {e}")


def _show_tk_label(text: str = "Hello Integration", duration_s: float = 2.5):
    import tkinter as tk
    root = tk.Tk()
    root.title("OCR Test Window")
    root.configure(bg="white")
    # Place near top-left to avoid occlusion
    root.geometry("400x180+50+50")
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    label = tk.Label(root, text=text, font=("Arial", 28, "bold"), bg="white", fg="black")
    label.pack(expand=True, fill="both")
    root.update()
    t0 = time.time()
    while time.time() - t0 < duration_s:
        root.update()
        time.sleep(0.05)
    try:
        root.destroy()
    except Exception:
        pass


def test_ocr_find_text_and_click(tmp_path):
    _ensure_tesseract()

    # Show a Tk window with clear text in a background thread
    th = threading.Thread(target=_show_tk_label, kwargs={"text": "Hello Integration", "duration_s": 3.0})
    th.daemon = True
    th.start()

    # Give it a moment to appear
    time.sleep(0.6)

    from tools.screen import Screen
    from tools.ocr import OCRTargeter
    from tools.input import InputController

    screen = Screen(run_dir=str(tmp_path))
    # Capture and search for the text
    img = screen.capture()
    ocr = OCRTargeter(language="eng", psm=6, oem=3)
    matches = ocr.find_text(img, "Integration", min_score=0.8)
    assert matches, "OCR did not detect expected text 'Integration'"

    # Click roughly at the first match center (verifies live input path). This should be harmless.
    top = matches[0]
    cx, cy = top.x + top.w // 2, top.y + top.h // 2
    ic = InputController(dry_run=False)
    obs = ic.click(cx, cy, button="left", clicks=1)
    assert obs == "clicked"

    # Wait for window thread to finish
    th.join(timeout=5)
