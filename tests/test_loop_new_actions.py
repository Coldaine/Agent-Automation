import os
import json
from rich.console import Console
from agent.loop import Stepper


class AdapterSeq:
    """Returns a predefined sequence of actions on each step."""
    def __init__(self, steps):
        self.steps = steps
        self.i = 0

    def step(self, instruction, last_observation, recent_steps, image_b64_jpeg):
        if self.i >= len(self.steps):
            return {"plan": "finish", "next_action": "NONE", "args": {}, "done": True}
        out = self.steps[self.i]
        self.i += 1
        return out


def test_loop_click_text_and_uia(monkeypatch, tmp_path):
    cfg = {
        "dry_run": True,
        "loop": {"max_steps": 3, "min_interval_ms": 0},
        "screenshot": {"width": 400, "quality": 50},
        "overlay": {"enabled": False},
        "ocr": {"language": "eng", "min_score": 0.0},
        "windows_uia": {"timeout_ms": 1},
    }
    run_dir = tmp_path / "run"
    os.makedirs(run_dir, exist_ok=True)

    # Fake screenshot to avoid OS dependency
    from tools.screen import Screen

    def fake_capture_and_encode(self, width=1280, quality=70):
        from PIL import Image
        img = Image.new("RGB", (width, int(width * 0.6)), color=(240, 240, 240))
        import base64, io
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{b64}", img

    Screen.capture_and_encode = fake_capture_and_encode

    # Monkeypatch OCR to return a known region
    import tools.ocr as ocr_mod

    class FakeOCR(ocr_mod.OCRTargeter):
        def find_text(self, img, query, min_score=0.0, region=None):
            return [ocr_mod.Region(x=10, y=10, w=10, h=10, text=query, score=1.0)]

    ocr_mod.OCRTargeter = FakeOCR

    # Monkeypatch UIA to always succeed
    import tools.win_uia as uia_mod

    class FakeUIA(uia_mod.WinUIA):
        def __init__(self, timeout_ms=0):
            pass

        def find(self, selector, scope="active_window"):
            return [{"rect": [0, 0, 20, 20], "handle": 1, "control_type": "Button"}]

        def invoke(self, element_ref):
            return True

        def set_value(self, element_ref, value):
            return True

    uia_mod.WinUIA = FakeUIA

    steps = [
        {"plan": "click text", "next_action": "CLICK_TEXT", "args": {"text": "Settings"}, "done": False},
        {"plan": "uia invoke", "next_action": "UIA_INVOKE", "args": {"selector": {"name": "OK", "control_type": "Button"}}, "done": False},
        {"plan": "finish", "next_action": "NONE", "args": {}, "done": True},
    ]

    adapter = AdapterSeq(steps)
    stepper = Stepper(cfg, str(run_dir), adapter, Console())
    stepper.run_instruction("test phase2 actions")
    stepper.close()

    log_path = run_dir / "steps.jsonl"
    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    # At least two steps should be logged
    assert len(lines) >= 2
    rec1 = json.loads(lines[0])
    assert rec1["next_action"] in ("CLICK_TEXT", "UIA_INVOKE", "NONE")
