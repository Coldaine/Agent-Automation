from __future__ import annotations
import threading


def show_crosshair(x: int, y: int, duration_ms: int = 250, radius: int = 20) -> None:
    """Best-effort transient overlay using tkinter; gracefully no-op if unavailable."""
    try:
        import tkinter as tk
    except Exception:
        return

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


class _CursorHalo:
    def __init__(self, radius: int = 18, poll_ms: int = 80):
        self.radius = max(10, int(radius))
        self.poll_ms = max(33, int(poll_ms))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

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
            import pyautogui as pg  # type: ignore
        except Exception:
            return

        root = tk.Tk()
        root.overrideredirect(True)
        root.wm_attributes("-topmost", True)
        root.wm_attributes("-alpha", 0.35)

        size = self.radius
        canvas = tk.Canvas(root, width=size, height=size, highlightthickness=0, bg="")
        canvas.pack()
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


_halo_singleton: _CursorHalo | None = None


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
