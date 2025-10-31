#!/usr/bin/env python
"""
Run a short live sequence of desktop actions via the agent using the current config.
Actions are chosen to be safe and observable:
  1) Move to center and click
  2) Right-click near center
  3) Double-click near center
  4) Type 'hello world' then press enter
  5) Scroll down, then up

Note: This honors config.yaml but forces overlay.always_on.enabled=True for visibility.
"""
import os
import yaml
from rich.console import Console
from datetime import datetime, timezone
from agent.model import get_adapter
from agent.loop import Stepper

CENTER_INSTR = "move mouse to the exact center of the screen and click once, then say done"
RIGHT_CLICK_CENTER = "right click at the center of the screen, then say done"
DOUBLE_CLICK_CENTER = "double-click at the center of the screen, then say done"
TYPE_HELLO = "type 'hello world' then press enter, then say done"
SCROLL_DOWN = "scroll down the page, then say done"
SCROLL_UP = "scroll up the page, then say done"

if __name__ == "__main__":
    console = Console()
    with open("config.yaml", "r", encoding="utf-8") as fp:
        cfg = yaml.safe_load(fp)

    # Make the halo overlay visible for this run only
    cfg.setdefault("overlay", {})
    cfg["overlay"].setdefault("always_on", {})
    cfg["overlay"]["always_on"]["enabled"] = True

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_dir = os.path.join("runs", ts)
    os.makedirs(run_dir, exist_ok=True)

    adapter = get_adapter(cfg.get("provider"), cfg.get("model"), float(cfg.get("temperature",0.2)), int(cfg.get("max_output_tokens",800)))
    stepper = Stepper(cfg, run_dir, adapter, console)

    try:
        console.print("[bold green]Live sequence: basic actions[/bold green]")
        for instr in [CENTER_INSTR, RIGHT_CLICK_CENTER, DOUBLE_CLICK_CENTER, TYPE_HELLO, SCROLL_DOWN, SCROLL_UP]:
            console.print("[dim]Instruction:[/dim] ", instr)
            stepper.run_instruction(instr)
    finally:
        stepper.close()
        console.print(f"[dim]Logs at {run_dir}[/dim]")
