from __future__ import annotations
from typing import List, Optional
import platform

class InputController:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self._pg = None
        self._win32 = None
        self._is_windows = platform.system().lower() == "windows"
        
        if not self.dry_run:
            # Prefer win32api for speed on Windows; fallback to pyautogui
            if self._is_windows:
                try:
                    import win32api  # type: ignore
                    import win32con  # type: ignore
                    self._win32 = (win32api, win32con)
                except Exception:
                    pass

            # Always initialize pyautogui for typing and hotkeys (win32 SendInput is complex)
            try:
                import pyautogui as pg
                pg.FAILSAFE = True
                pg.PAUSE = 0
                self._pg = pg
            except Exception as e:
                if self._win32 is None:
                    raise RuntimeError(f"Input library not available: {e}")

    def _obs(self, text: str) -> str:
        return f"(dry-run) {text}" if self.dry_run else text

    def move(self, x: int, y: int, duration: float = 0.0) -> str:
        if self.dry_run:
            return self._obs(f"move to {x},{y} ({duration}s)")
        
        if self._win32:
            win32api, _ = self._win32
            win32api.SetCursorPos((int(x), int(y)))
            if duration > 0:
                import time
                time.sleep(duration)
            return "moved"
        
        self._pg.moveTo(x, y, duration=max(0.0, duration))
        return "moved"

    def click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left", clicks: int = 1, interval: float = 0.1) -> str:
        if self.dry_run:
            return self._obs(f"click {button} {clicks}x at {x},{y}")
        
        if self._win32:
            win32api, win32con = self._win32
            if x is not None and y is not None:
                win32api.SetCursorPos((int(x), int(y)))
            
            # Map button names to win32 constants
            if button == "left":
                down_flag = win32con.MOUSEEVENTF_LEFTDOWN
                up_flag = win32con.MOUSEEVENTF_LEFTUP
            elif button == "right":
                down_flag = win32con.MOUSEEVENTF_RIGHTDOWN
                up_flag = win32con.MOUSEEVENTF_RIGHTUP
            elif button == "middle":
                down_flag = win32con.MOUSEEVENTF_MIDDLEDOWN
                up_flag = win32con.MOUSEEVENTF_MIDDLEUP
            else:
                down_flag = win32con.MOUSEEVENTF_LEFTDOWN
                up_flag = win32con.MOUSEEVENTF_LEFTUP
            
            for _ in range(clicks):
                win32api.mouse_event(down_flag, 0, 0, 0, 0)
                win32api.mouse_event(up_flag, 0, 0, 0, 0)
                if interval > 0 and clicks > 1:
                    import time
                    time.sleep(interval)
            return "clicked"
        
        self._pg.click(x=x, y=y, button=button, clicks=clicks, interval=interval)
        return "clicked"

    def type_text(self, text: str, interval: float = 0.02) -> str:
        if self.dry_run:
            return self._obs(f"type '{text}'")
        
        if self._win32:
            # For now, fallback to pyautogui for typing; win32 SendInput requires more complex setup
            if self._pg:
                self._pg.typewrite(text, interval=interval)
                return "typed"
        
        if self._pg:
            self._pg.typewrite(text, interval=interval)
            return "typed"
        return "type failed"

    def hotkey(self, keys: List[str]) -> str:
        if self.dry_run:
            return self._obs("hotkey "+"+".join(keys))
        
        # Use pyautogui for hotkeys as it handles key combinations well
        if self._pg:
            self._pg.hotkey(*keys)
            return "hotkey pressed"
        return "hotkey failed"

    def scroll(self, amount: int) -> str:
        if self.dry_run:
            return self._obs(f"scroll {amount}")
        
        if self._win32:
            win32api, win32con = self._win32
            # win32 scroll uses WHEEL_DELTA units (typically 120 per notch)
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, amount, 0)
            return "scrolled"
        
        if self._pg:
            self._pg.scroll(amount)
            return "scrolled"
        return "scroll failed"

    def drag(self, x: int, y: int, duration: float = 0.2) -> str:
        if self.dry_run: return self._obs(f"drag to {x},{y} ({duration}s)")
        self._pg.dragTo(x, y, duration=duration); return "dragged"

    def wait(self, seconds: float) -> str:
        import time
        time.sleep(seconds if not self.dry_run else 0)
        return self._obs(f"wait {seconds}s")
