from __future__ import annotations
import base64, io, os
from datetime import datetime, timezone
from typing import Optional, Tuple
from PIL import Image
try:
    import mss
except Exception:
    mss = None

class Screen:
    def __init__(self, run_dir: str):
        self.run_dir = run_dir
        os.makedirs(self.run_dir, exist_ok=True)

    def capture(self, region: Optional[Tuple[int,int,int,int]] = None) -> Image.Image:
        if mss is None:
            raise RuntimeError("python-mss not installed. `pip install mss`")
        with mss.mss() as sct:
            if region:
                left, top, width, height = region
                mon = {"left": left, "top": top, "width": width, "height": height}
                raw = sct.grab(mon)
            else:
                raw = sct.grab(sct.monitors[1])
        img = Image.frombytes("RGB", raw.size, raw.rgb)
        return img

    def capture_and_encode(self, width: int = 1280, quality: int = 70):
        img = self.capture()
        if width and img.width > width:
            h = int(img.height * (width / img.width))
            img = img.resize((width, h))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{b64}", img

    def save_step_image(self, pil_img, step_index: int) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        path = os.path.join(self.run_dir, f"step_{step_index:04d}_{ts}.png")
        pil_img.save(path, format="PNG")
        return path
