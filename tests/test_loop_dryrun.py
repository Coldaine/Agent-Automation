import os, json
from rich.console import Console
from agent.loop import Stepper
from agent.model import DummyAdapter
def test_dryrun_creates_logs(tmp_path):
    cfg = {"dry_run": True, "loop": {"max_steps": 2, "min_interval_ms": 0}, "screenshot": {"width": 400, "quality": 50}, "overlay": {"enabled": False}}
    run_dir = tmp_path / "run"
    os.makedirs(run_dir, exist_ok=True)
    stepper = Stepper(cfg, str(run_dir), DummyAdapter(), Console())
    # Monkeypatch Screen.capture_and_encode to avoid real screenshots
    from tools.screen import Screen
    def fake_capture_and_encode(self, width=1280, quality=70):
        from PIL import Image
        img = Image.new("RGB", (width, int(width*0.6)), color=(240,240,240))
        import base64, io
        buf = io.BytesIO(); img.save(buf, format="JPEG"); b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{b64}", img
    Screen.capture_and_encode = fake_capture_and_encode
    stepper.run_instruction("type hello world")
    stepper.close()
    log_path = run_dir / "steps.jsonl"
    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    rec = json.loads(lines[0])
    assert "plan" in rec and "next_action" in rec
