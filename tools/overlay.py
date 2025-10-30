from __future__ import annotations
import threading

def show_crosshair(x: int, y: int, duration_ms: int = 250) -> None:
    try:
        import tkinter as tk
    except Exception:
        return
    def _run():
        root = tk.Tk()
        root.overrideredirect(True)
        root.wm_attributes("-topmost", True)
        root.wm_attributes("-alpha", 0.6)
        size = 40
        canvas = tk.Canvas(root, width=size, height=size, highlightthickness=0, bg="")
        canvas.pack()
        root.geometry(f"+{max(0, x-size//2)}+{max(0, y-size//2)}")
        canvas.create_oval(2, 2, size-2, size-2)
        root.after(duration_ms, root.destroy)
        root.mainloop()
    threading.Thread(target=_run, daemon=True).start()
