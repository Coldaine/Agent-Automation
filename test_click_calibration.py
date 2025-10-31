#!/usr/bin/env python
"""Visual test to verify click coordinates are accurate.

This test displays a simple GUI with numbered targets.
Click on each target to verify coordinate accuracy.
"""
import tkinter as tk
from tools.input import InputController

def create_calibration_window():
    """Create a window with click targets for manual verification."""
    root = tk.Tk()
    root.title("Click Calibration Test")
    root.geometry("800x600")

    canvas = tk.Canvas(root, width=800, height=600, bg="white")
    canvas.pack()

    # Draw crosshairs at known coordinates
    targets = [
        (100, 100, "Target 1"),
        (400, 300, "Target 2 (Center)"),
        (700, 500, "Target 3"),
        (200, 400, "Target 4"),
    ]

    for x, y, label in targets:
        # Draw crosshair
        canvas.create_line(x-20, y, x+20, y, fill="red", width=2)
        canvas.create_line(x, y-20, x, y+20, fill="red", width=2)
        canvas.create_oval(x-5, y-5, x+5, y+5, outline="red", width=2)

        # Label
        canvas.create_text(x, y-30, text=f"{label}\n({x}, {y})", fill="blue", font=("Arial", 10))

    instructions = """
CALIBRATION TEST

1. Note the coordinates of each target
2. Run manual click test with InputController
3. Verify mouse moves to exact center of crosshairs

Press 'q' to quit
"""

    canvas.create_text(400, 50, text=instructions, font=("Arial", 12), justify=tk.CENTER)

    def on_key(event):
        if event.char == 'q':
            root.destroy()

    root.bind('<Key>', on_key)

    print("\n=== CALIBRATION TEST ===")
    print("Targets visible on screen at these coordinates:")
    for x, y, label in targets:
        print(f"  {label}: ({x}, {y})")

    print("\n--- Manual Test ---")
    print("Now testing InputController clicks...")
    input("Press Enter to test clicking Target 1 (100, 100)...")

    # Test actual clicking
    ctrl = InputController(dry_run=False)

    for x, y, label in targets:
        input(f"\nPress Enter to click {label} at ({x}, {y})...")
        result = ctrl.move(x, y)
        print(f"Move result: {result}")
        import time
        time.sleep(0.5)  # Let you see the cursor position
        result = ctrl.click(x, y)
        print(f"Click result: {result}")
        print("Did the cursor move to the CENTER of the crosshair? (Check visually)")

    print("\n=== TEST COMPLETE ===")
    print("If cursor did NOT hit center of crosshairs, there's a coordinate scaling issue!")

    root.mainloop()

if __name__ == "__main__":
    import sys
    import platform

    print(f"Platform: {platform.system()}")
    print(f"Python: {sys.version}")

    # Get screen resolution
    if platform.system().lower() == "windows":
        import ctypes
        user32 = ctypes.windll.user32
        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)
        print(f"Screen Resolution: {screen_width}x{screen_height}")

    create_calibration_window()
