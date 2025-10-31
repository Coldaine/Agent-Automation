#!/usr/bin/env python
"""Live run: move to center and click once using current config (may interact with your mouse!).
"""
import os
import yaml
from rich.console import Console
from agent.model import get_adapter
from agent.loop import Stepper
from datetime import datetime, timezone

if __name__ == "__main__":
    with open("config.yaml", "r", encoding="utf-8") as fp:
        cfg = yaml.safe_load(fp)

    # Honor current config; do NOT force dry_run
    run_live = not bool(cfg.get("dry_run", True))
    console = Console()
    if not run_live:
        console.print("[yellow]Config has dry_run: true. This script will not perform real clicks.[/yellow]")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_dir = os.path.join("runs", ts)
    os.makedirs(run_dir, exist_ok=True)

    adapter = get_adapter(cfg.get("provider"), cfg.get("model"), float(cfg.get("temperature",0.2)), int(cfg.get("max_output_tokens",800)))
    stepper = Stepper(cfg, run_dir, adapter, console)

    instruction = "move mouse to the exact center of the screen and click once, then say done"
    console.print("[bold green]Live run: center click[/bold green]")
    console.print("[dim]Instruction:[/dim] ", instruction)
    try:
        stepper.run_instruction(instruction)
    finally:
        stepper.close()
        console.print(f"[dim]Logs at {run_dir}[/dim]")
