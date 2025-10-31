#!/usr/bin/env python
"""Live-model (Zhipu) dry-run validation: ask to click screen center and log meta.
Safe: dry_run should be true in config.
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

    # Ensure we are in dry-run for safety
    cfg["dry_run"] = True

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_dir = os.path.join("runs", ts)
    os.makedirs(run_dir, exist_ok=True)

    console = Console()
    adapter = get_adapter(cfg.get("provider"), cfg.get("model"), float(cfg.get("temperature", 0.2)), int(cfg.get("max_output_tokens", 800)))
    stepper = Stepper(cfg, run_dir, adapter, console)

    console.print("[bold green]Zhipu live-model dry-run: center click[/bold green]")
    instruction = "move mouse to the exact center of the screen and click once, then say done"
    stepper.run_instruction(instruction)
    stepper.close()

    console.print(f"[dim]Logs at {run_dir} (inspect steps.jsonl for meta coords)\n[/dim]")
