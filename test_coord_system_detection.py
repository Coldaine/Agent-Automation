#!/usr/bin/env python
"""
Coordinate System Detection Harness (live-model friendly, safe in dry-run)
- Runs two sub-runs with different screenshot widths
- Asks model to click exact center
- Compares returned raw coords across runs
- Emits a verdict: SCREEN_COORDS or IMAGE_COORDS

Usage:
  - Ensure provider is set (e.g., zhipu) and ZHIPU_API_KEY is available
  - Keep dry_run: true in config.yaml for safety
"""
import os
import yaml
from rich.console import Console
from agent.model import get_adapter
from agent.loop import Stepper
from datetime import datetime, timezone

PROMPT = "move mouse to the exact center of the screen and click once, then say done"


def run_once(cfg, width):
    cfg_local = dict(cfg)
    cfg_local.setdefault("screenshot", {})
    cfg_local["screenshot"] = dict(cfg.get("screenshot", {}))
    cfg_local["screenshot"]["width"] = int(width)
    cfg_local["dry_run"] = True

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_dir = os.path.join("runs", f"detect_{width}_{ts}")
    os.makedirs(run_dir, exist_ok=True)

    console = Console()
    adapter = get_adapter(cfg_local.get("provider"), cfg_local.get("model"), float(cfg_local.get("temperature", 0.2)), int(cfg_local.get("max_output_tokens", 800)))
    stepper = Stepper(cfg_local, run_dir, adapter, console)
    stepper.run_instruction(PROMPT)
    stepper.close()

    # Parse steps.jsonl and return last step meta coords.raw
    steps_path = os.path.join(run_dir, "steps.jsonl")
    raw_xy = None
    try:
        with open(steps_path, "r", encoding="utf-8") as fp:
            for line in fp:
                obj = yaml.safe_load(line)
                if obj.get("next_action") in {"CLICK", "MOVE", "DOUBLE_CLICK"}:
                    meta = obj.get("meta") or {}
                    coords = meta.get("coords") or {}
                    raw_xy = coords.get("raw")
    except Exception as e:
        console.print(f"[red]Error reading steps: {e}[/red]")
    return raw_xy


if __name__ == "__main__":
    console = Console()
    with open("config.yaml", "r", encoding="utf-8") as fp:
        cfg = yaml.safe_load(fp)

    w1, w2 = 1280, 960
    console.print(f"[bold]Running detection at widths {w1} and {w2}[/bold]")
    xy1 = run_once(cfg, w1)
    xy2 = run_once(cfg, w2)

    console.print(f"width {w1} raw coords: {xy1}")
    console.print(f"width {w2} raw coords: {xy2}")

    verdict = "UNKNOWN"
    if xy1 and xy2:
        if xy1 == xy2:
            verdict = "SCREEN_COORDS (absolute)"
        else:
            verdict = "IMAGE_COORDS (relative to screenshot)"
    console.print(f"[bold green]Verdict: {verdict}[/bold green]")
