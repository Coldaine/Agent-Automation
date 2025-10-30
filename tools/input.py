from __future__ import annotations
from typing import List, Optional

class InputController:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self._pg = None
        if not self.dry_run:
            try:
                import pyautogui as pg
                pg.FAILSAFE = True
                pg.PAUSE = 0
                self._pg = pg
            except Exception as e:
                raise RuntimeError(f"pyautogui not available: {e}")

    def _obs(self, text: str) -> str:
        return f"(dry-run) {text}" if self.dry_run else text

    def move(self, x: int, y: int, duration: float = 0.0) -> str:
        if self.dry_run: return self._obs(f"move to {x},{y} ({duration}s)")
        self._pg.moveTo(x, y, duration=max(0.0, duration)); return "moved"

    def click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left", clicks: int = 1, interval: float = 0.1) -> str:
        if self.dry_run: return self._obs(f"click {button} {clicks}x at {x},{y}")
        self._pg.click(x=x, y=y, button=button, clicks=clicks, interval=interval); return "clicked"

    def type_text(self, text: str, interval: float = 0.02) -> str:
        if self.dry_run: return self._obs(f"type '{text}'")
        self._pg.typewrite(text, interval=interval); return "typed"

    def hotkey(self, keys: List[str]) -> str:
        if self.dry_run: return self._obs("hotkey "+"+".join(keys))
        self._pg.hotkey(*keys); return "hotkey pressed"

    def scroll(self, amount: int) -> str:
        if self.dry_run: return self._obs(f"scroll {amount}")
        self._pg.scroll(amount); return "scrolled"

    def drag(self, x: int, y: int, duration: float = 0.2) -> str:
        if self.dry_run: return self._obs(f"drag to {x},{y} ({duration}s)")
        self._pg.dragTo(x, y, duration=duration); return "dragged"

    def wait(self, seconds: float) -> str:
        import time
        time.sleep(seconds if not self.dry_run else 0)
        return self._obs(f"wait {seconds}s")
