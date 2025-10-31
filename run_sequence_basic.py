from __future__ import annotations
import time
from tools.input import InputController

def run_basic_sequence():
    """Runs a basic sequence of input actions to test the input controller."""
    print("Running basic input sequence...")
    input_controller = InputController(dry_run=False)

    # 1. Move to a starting position
    input_controller.move(100, 100, duration=0.5)
    print("Moved to (100, 100)")
    time.sleep(1)

    # 2. Click
    input_controller.click(200, 200, button="left")
    print("Clicked at (200, 200)")
    time.sleep(1)

    # 3. Right-click
    input_controller.click(300, 300, button="right")
    print("Right-clicked at (300, 300)")
    time.sleep(1)

    # 4. Double-click
    input_controller.click(400, 400, clicks=2)
    print("Double-clicked at (400, 400)")
    time.sleep(1)

    # 5. Type
    input_controller.type_text("Hello, world!", interval=0.1)
    print("Typed 'Hello, world!'")
    time.sleep(1)

    # 6. Scroll
    input_controller.scroll(-300)
    print("Scrolled down")
    time.sleep(1)

    print("Basic input sequence complete.")

if __name__ == "__main__":
    run_basic_sequence()