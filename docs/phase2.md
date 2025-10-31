# DesktopOps Agent Phase 2 Features (Windows-Optimized)

**Note: Windows is the primary supported platform for these features. Cross-platform support (macOS/Linux) is not a priority and may have limited functionality.**
What you’re getting (quick map)
Module	File	Purpose	New actions (optional)
Overlay visualizer (always-on cursor tracker)	tools/overlay.py (updated)	transient click indicator and optional always-on halo that follows the cursor	(none)
Windows UIA	tools/win_uia.py (new)	semantic Windows automation (find/invoke/set value by selector)	UIA_INVOKE, UIA_SET_VALUE
OCR-assisted targeter	tools/ocr.py (new)	text → region finding on screenshots; click by label	CLICK_TEXT

Also included:

agent/parser.py: allows the new actions.

agent/model.py: updates the action enum in the system schema.

agent/loop.py: dispatch logic for the new actions + optional always-on overlay lifecycle.

requirements.txt: adds pytesseract and pywinauto (Windows).

config.yaml: adds flags/knobs for overlay.always_on, windows_uia, and ocr.

1) Code changes
A) requirements.txt (append these)
pytesseract>=0.3.10
pywinauto>=0.6.8 ; platform_system == "Windows"


pytesseract needs the system Tesseract binary (install steps below).

B) config.yaml (add/extend these blocks)
overlay:
  enabled: true          # shows transient indicator on clicks
  duration_ms: 250
  always_on:
    enabled: false       # set true to show an always-on cursor halo
    radius: 18           # halo diameter in px
    poll_ms: 80          # refresh rate (ms)

windows_uia:
  enabled: false         # Windows-only; uses pywinauto under the hood
  timeout_ms: 1500       # how long to wait for selector matches

ocr:
  enabled: false
  language: eng          # Tesseract language code(s), e.g. "eng+osd"
  min_score: 0.70        # fuzzy match threshold
  psm: 6                 # Tesseract page segmentation mode
  oem: 3                 # Tesseract engine mode
  region: null           # optional [left,top,width,height]; null = full screen

C) tools/overlay.py (replace file)
from __future__ import annotations
import threading
import time
from typing import Optional

# --- transient indicator (already used by click actions) ---

def show_crosshair(x: int, y: int, duration_ms: int = 250, radius: int = 20) -> None:
    """Best-effort transient overlay using tkinter; gracefully no-op if unavailable."""
    try:
        import tkinter as tk
    except Exception:
        return  # degrade quietly

    def _run():
        root = tk.Tk()
        root.overrideredirect(True)
        root.wm_attributes("-topmost", True)
        root.wm_attributes("-alpha", 0.55)
        size = max(12, int(radius))
        canvas = tk.Canvas(root, width=size, height=size, highlightthickness=0, bg="")
        canvas.pack()
        root.geometry(f"+{max(0, x - size // 2)}+{max(0, y - size // 2)}")
        canvas.create_oval(2, 2, size - 2, size - 2)
        root.after(duration_ms, root.destroy)
        root.mainloop()

    threading.Thread(target=_run, daemon=True).start()


# --- always-on cursor tracker (optional) ---

class _CursorHalo:
    def __init__(self, radius: int = 18, poll_ms: int = 80):
        self.radius = max(10, int(radius))
        self.poll_ms = max(33, int(poll_ms))
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        try:
            import tkinter as tk
            import pyautogui as pg
        except Exception:
            return  # no overlay support or pyautogui

        root = tk.Tk()
        root.overrideredirect(True)
        root.wm_attributes("-topmost", True)
        root.wm_attributes("-alpha", 0.35)

        size = self.radius
        canvas = tk.Canvas(root, width=size, height=size, highlightthickness=0, bg="")
        canvas.pack()
        # draw once; we'll just move the window
        canvas.create_oval(2, 2, size - 2, size - 2)

        def tick():
            if self._stop.is_set():
                try:
                    root.destroy()
                except Exception:
                    pass
                return
            try:
                x, y = pg.position()
                root.geometry(f"+{max(0, x - size // 2)}+{max(0, y - size // 2)}")
            finally:
                root.after(self.poll_ms, tick)

        root.after(self.poll_ms, tick)
        try:
            root.mainloop()
        except Exception:
            pass


_halo_singleton: Optional[_CursorHalo] = None

def start_always_on(radius: int = 18, poll_ms: int = 80):
    global _halo_singleton
    if _halo_singleton is None:
        _halo_singleton = _CursorHalo(radius, poll_ms)
    _halo_singleton.start()

def stop_always_on():
    global _halo_singleton
    if _halo_singleton:
        _halo_singleton.stop()
        _halo_singleton = None

D) tools/win_uia.py (new file)
from __future__ import annotations
from typing import Any, Dict, List, Optional

def _on_windows() -> bool:
    import platform
    return platform.system().lower() == "windows"

class WinUIA:
    """
    Thin Windows UI Automation adapter (pywinauto).
    Selectors: {"name": "...", "control_type": "Button", "automation_id": "OKButton"}
    Scope: "active_window" (default) or "desktop"
    """
    def __init__(self, timeout_ms: int = 1500):
        if not _on_windows():
            raise RuntimeError("Windows UIA is only available on Windows")
        try:
            from pywinauto import Desktop
        except Exception as e:
            raise RuntimeError(f"pywinauto not available: {e}")
        self.Desktop = Desktop
        self.timeout_s = max(0.2, timeout_ms / 1000.0)

    def _scope_root(self, scope: str):
        if scope == "desktop":
            return self.Desktop(backend="uia")
        # active window (focused) tree
        return self.Desktop(backend="uia").window(handle=self.Desktop(backend="uia").get_active().handle)

    def find(self, selector: Dict[str, Any], scope: str = "active_window") -> List[Dict[str, Any]]:
        root = self._scope_root(scope)
        kwargs = {}
        if "name" in selector:
            kwargs["title"] = selector["name"]
        if "automation_id" in selector:
            kwargs["automation_id"] = selector["automation_id"]
        if "control_type" in selector:
            kwargs["control_type"] = selector["control_type"]

        try:
            matches = root.descendants(**kwargs)
        except Exception:
            matches = []
        results = []
        for el in matches[:30]:  # cap
            try:
                rect = el.rectangle()
                results.append({
                    "name": getattr(el, "friendly_class_name", lambda: "")() or getattr(el, "window_text", lambda:"")(),
                    "control_type": getattr(el, "control_type", None),
                    "automation_id": getattr(el, "automation_id", None),
                    "rect": [rect.left, rect.top, rect.width(), rect.height()],
                    "handle": el.handle,
                })
            except Exception:
                continue
        return results

    def invoke(self, element_ref: Dict[str, Any]) -> bool:
        from pywinauto.controls.uia_controls import ButtonWrapper, EditWrapper
        try:
            # using handle is the most stable
            handle = element_ref.get("handle")
            if not handle:
                return False
            # Recreate wrapper from handle
            wrapper = ButtonWrapper(handle=handle) if element_ref.get("control_type") == "Button" else None
            if wrapper:
                wrapper.click_input()
                return True
        except Exception:
            pass
        # fallback: click center of rect
        rect = element_ref.get("rect")
        if rect:
            x = rect[0] + rect[2] // 2
            y = rect[1] + rect[3] // 2
            try:
                import pyautogui as pg
                pg.click(x=x, y=y)
                return True
            except Exception:
                return False
        return False

    def set_value(self, element_ref: Dict[str, Any], value: str) -> bool:
        try:
            from pywinauto.controls.uia_controls import EditWrapper
            handle = element_ref.get("handle")
            if not handle:
                return False
            wrapper = EditWrapper(handle=handle)
            wrapper.set_edit_text(value)
            return True
        except Exception:
            # fallback: click + type
            rect = element_ref.get("rect")
            if rect:
                import pyautogui as pg
                x = rect[0] + rect[2] // 2
                y = rect[1] + rect[3] // 2
                pg.click(x=x, y=y)
                pg.typewrite(value, interval=0.02)
                return True
        return False

E) tools/ocr.py (new file)
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
import io, base64, hashlib

from PIL import Image, ImageOps, ImageFilter
import pytesseract

@dataclass
class Region:
    x: int
    y: int
    w: int
    h: int
    text: str
    score: float

class OCRTargeter:
    def __init__(self, language: str = "eng", psm: int = 6, oem: int = 3):
        self.language = language
        self.psm = psm
        self.oem = oem
        self._last_hash = None
        self._last_regions: List[Region] = []

    def _hash_img(self, img: Image.Image) -> str:
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return hashlib.sha1(buf.getvalue()).hexdigest()

    def _preprocess(self, img: Image.Image) -> Image.Image:
        g = ImageOps.grayscale(img)
        # light unsharp/contrast to aid OCR; keep it fast
        g = g.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
        return g

    def extract(self, img: Image.Image) -> List[Region]:
        h = self._hash_img(img)
        if h == self._last_hash:
            return self._last_regions

        proc = self._preprocess(img)
        custom = f"--psm {self.psm} --oem {self.oem}"
        data = pytesseract.image_to_data(proc, lang=self.language, config=custom, output_type=pytesseract.Output.DICT)
        regs: List[Region] = []
        n = len(data["text"])
        for i in range(n):
            txt = (data["text"][i] or "").strip()
            if not txt:
                continue
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            regs.append(Region(x=x, y=y, w=w, h=h, text=txt, score=1.0))
        self._last_hash = h
        self._last_regions = regs
        return regs

    @staticmethod
    def _score(query: str, candidate: str) -> float:
        q = query.strip().lower()
        c = (candidate or "").strip().lower()
        if not q or not c:
            return 0.0
        if q == c:
            return 1.0
        if q in c:
            return min(0.95, (len(q) / (len(c) + 1e-5)))
        # very light fuzzy
        import difflib
        return difflib.SequenceMatcher(None, q, c).ratio()

    def find_text(self, img: Image.Image, query: str, min_score: float = 0.7, region: Optional[Tuple[int,int,int,int]] = None) -> List[Region]:
        crop = img
        offset_x = offset_y = 0
        if region:
            l, t, w, h = region
            crop = img.crop((l, t, l + w, t + h))
            offset_x, offset_y = l, t

        regs = self.extract(crop)
        scored: List[Region] = []
        for r in regs:
            s = self._score(query, r.text)
            if s >= min_score:
                scored.append(Region(x=r.x + offset_x, y=r.y + offset_y, w=r.w, h=r.h, text=r.text, score=s))
        # sort best-first, larger boxes slightly preferred to avoid tiny glyph matches
        scored.sort(key=lambda r: (r.score, r.w * r.h), reverse=True)
        return scored

F) agent/parser.py (expand valid actions)
# add to VALID_ACTIONS set:
VALID_ACTIONS = {
    "MOVE","CLICK","DOUBLE_CLICK","RIGHT_CLICK","TYPE","HOTKEY",
    "SCROLL","DRAG","WAIT","NONE",
    "CLICK_TEXT","UIA_INVOKE","UIA_SET_VALUE"
}

G) agent/model.py (update action enum in adapters)

Find both places where the enum is defined and append the same three actions:

# In OpenAIAdapter.schema["schema"]["properties"]["next_action"]["enum"]
["MOVE","CLICK","DOUBLE_CLICK","RIGHT_CLICK","TYPE","HOTKEY","SCROLL","DRAG","WAIT","NONE","CLICK_TEXT","UIA_INVOKE","UIA_SET_VALUE"]


And update any hardcoded description strings accordingly (mention the new actions and that selectors/text are allowed).

H) agent/loop.py (new dispatch + overlay lifecycle)

Start/stop always-on overlay:

In Stepper.__init__ after reading cfg:

from tools import overlay
self._overlay_always_on = False
ao_cfg = self.cfg.get("overlay", {}).get("always_on", {})
if bool(ao_cfg.get("enabled", False)):
    try:
        overlay.start_always_on(radius=int(ao_cfg.get("radius", 18)),
                                poll_ms=int(ao_cfg.get("poll_ms", 80)))
        self._overlay_always_on = True
    except Exception:
        self._overlay_always_on = False


In Stepper.close():

try:
    if self._overlay_always_on:
        overlay.stop_always_on()
except Exception:
    pass


Dispatch additions (inside run_instruction, after existing branches):

elif act == "CLICK_TEXT":
    # resolve text to coords via OCR, then click
    from tools.ocr import OCRTargeter
    shot_img = pil_img  # reuse the just-captured PIL image
    ocrc = self.cfg.get("ocr", {})
    targeter = getattr(self, "_ocr_targeter", None)
    if targeter is None:
        targeter = self._ocr_targeter = OCRTargeter(language=ocrc.get("language","eng"),
                                                    psm=int(ocrc.get("psm",6)),
                                                    oem=int(ocrc.get("oem",3)))
    query = str(args.get("text", "")).strip()
    min_score = float(ocrc.get("min_score", 0.70))
    region = ocrc.get("region", None)  # [l,t,w,h] or None
    matches = targeter.find_text(shot_img, query, min_score=min_score, region=tuple(region) if region else None)
    if matches:
        top = matches[0]
        cx = top.x + top.w // 2
        cy = top.y + top.h // 2
        observation = self.input.click(cx, cy, button="left", clicks=1, interval=0.1)
        if overlay_enabled:
            overlay.show_crosshair(int(cx), int(cy), overlay_ms)
    else:
        observation = f"no match for text '{query}' (min_score={min_score})"

elif act == "UIA_INVOKE":
    # invoke a control by selector (Windows only)
    try:
        from tools.win_uia import WinUIA
        uia = getattr(self, "_uia", None)
        if uia is None:
            uia = self._uia = WinUIA(timeout_ms=int(self.cfg.get("windows_uia",{}).get("timeout_ms",1500)))
        selector = args.get("selector", {})
        scope = args.get("scope", "active_window")
        found = uia.find(selector, scope=scope)
        observation = "UIA_INVOKE: no matches"
        if found:
            ok = uia.invoke(found[0])
            observation = f"UIA_INVOKE: {'ok' if ok else 'failed'}"
    except Exception as e:
        observation = f"UIA error: {e}"

elif act == "UIA_SET_VALUE":
    try:
        from tools.win_uia import WinUIA
        uia = getattr(self, "_uia", None)
        if uia is None:
            uia = self._uia = WinUIA(timeout_ms=int(self.cfg.get("windows_uia",{}).get("timeout_ms",1500)))
        selector = args.get("selector", {})
        value = str(args.get("value", ""))
        scope = args.get("scope", "active_window")
        found = uia.find(selector, scope=scope)
        observation = "UIA_SET_VALUE: no matches"
        if found:
            ok = uia.set_value(found[0], value)
            observation = f"UIA_SET_VALUE: {'ok' if ok else 'failed'}"
    except Exception as e:
        observation = f"UIA error: {e}"


That’s it—core loop remains minimal; these features light up only when configured or when the model chooses those actions.

2) Provider prompt nudge (optional but helpful)

Add one line to the adapter system prompts (in agent/model.py) to hint at the new choices:

You may also use CLICK_TEXT {text,min_score?} (OCR), and UIA_INVOKE/UIA_SET_VALUE with a selector on Windows.
Prefer UIA when available; otherwise CLICK_TEXT; otherwise pixel coords.


This keeps the model’s strategy sane without long instructions.

3) How to install the extras
A) Tesseract OCR (for pytesseract)

macOS (Homebrew):

brew install tesseract


Ubuntu/Debian:

sudo apt-get update
sudo apt-get install -y tesseract-ocr
# Optional language packs, e.g.:
# sudo apt-get install -y tesseract-ocr-eng tesseract-ocr-spa


Windows (Scoop or Chocolatey):

# Scoop
scoop install tesseract
# or Chocolatey
choco install tesseract


If Tesseract isn’t on PATH, set:

macOS/Linux: usually automatic.

Windows example:

setx TESSDATA_PREFIX "C:\Program Files\Tesseract-OCR\tessdata"
setx PATH "%PATH%;C:\Program Files\Tesseract-OCR"

B) Windows UIA

Ensure you’re on Windows and install dependencies:

# In the project venv
pip install pywinauto


Give the app normal foreground access; UIA typically works without extra permissions.

Some apps running as Administrator may require your Python process to run elevated too.

4) Turning features on

Edit config.yaml:

Overlay (transient)

overlay:
  enabled: true
  duration_ms: 250


Always-on cursor halo

overlay:
  enabled: true
  duration_ms: 250
  always_on:
    enabled: true
    radius: 18
    poll_ms: 80


Windows UIA

windows_uia:
  enabled: true
  timeout_ms: 1500


OCR

ocr:
  enabled: true
  language: eng
  min_score: 0.75
  psm: 6
  oem: 3


You can keep OCR/UIA enabled and still operate normally; the model (or you) only uses those actions when needed.

5) How to use the new actions (dry-run demo)

You can force an action by switching to the dummy provider and issuing instructions that your adapter will pass through, or by using the OpenAI adapter and prompting clearly:

Click by text (OCR):

Click the "Settings" text.


The model should return:

{"plan":"click Settings","next_action":"CLICK_TEXT","args":{"text":"Settings","min_score":0.75},"done":false}


Invoke a Windows control (UIA):

Press the OK button in the active window using UIA.


Expected:

{"plan":"invoke OK","next_action":"UIA_INVOKE","args":{"selector":{"name":"OK","control_type":"Button"},"scope":"active_window"},"done":false}


Set value in a field (UIA):

{"plan":"type into field","next_action":"UIA_SET_VALUE","args":{"selector":{"automation_id":"SearchTextBox"},"value":"hello world"},"done":false}


Every step still logs {plan, next_action, args, observation} and a screenshot to /runs/<ts>/.