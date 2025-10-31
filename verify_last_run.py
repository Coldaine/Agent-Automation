#!/usr/bin/env python
"""
Summarize the last run's step verification:
- Shows per-step action, coords, center distance (if applicable), and visual delta/pass (if available)
- Exits with code 0 if all available verifications passed; 1 otherwise

Usage:
  uv run python verify_last_run.py [runs/<timestamp>]
"""
import json
import math
import os
import sys
from typing import Any, Dict, Optional, Tuple

from rich.console import Console
from rich.table import Table


def _latest_run_dir() -> Optional[str]:
    runs_dir = os.path.join(os.getcwd(), "runs")
    if not os.path.isdir(runs_dir):
        return None
    latest: Tuple[float, Optional[str]] = (0.0, None)
    for name in os.listdir(runs_dir):
        p = os.path.join(runs_dir, name)
        if not os.path.isdir(p):
            continue
        steps_path = os.path.join(p, "steps.jsonl")
        if os.path.isfile(steps_path):
            try:
                mt = os.path.getmtime(steps_path)
            except Exception:
                mt = 0.0
        else:
            try:
                mt = os.path.getmtime(p)
            except Exception:
                mt = 0.0
        if mt >= latest[0]:
            latest = (mt, p)
    return latest[1]


def _load_steps(run_dir: str):
    steps_path = os.path.join(run_dir, "steps.jsonl")
    with open(steps_path, "r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                # skip malformed lines
                continue


def _center_distance(meta: Dict[str, Any]) -> Optional[Tuple[float, float, float]]:
    try:
        screen = meta.get("screen", {})
        w = int(screen.get("width"))
        h = int(screen.get("height"))
        coords = meta.get("coords", {})
        fx, fy = coords.get("final", [None, None])
        if fx is None or fy is None:
            return None
        cx, cy = w // 2, h // 2
        dx = float(fx) - float(cx)
        dy = float(fy) - float(cy)
        dist = math.hypot(dx, dy)
        return float(cx), float(cy), float(dist)
    except Exception:
        return None


def main():
    console = Console()
    run_dir = sys.argv[1] if len(sys.argv) > 1 else _latest_run_dir()
    if not run_dir:
        console.print("[red]No runs found.[/red]")
        sys.exit(1)
    steps = list(_load_steps(run_dir))
    if not steps:
        console.print(f"[red]No steps found in {run_dir}[/red]")
        sys.exit(1)

    table = Table(title=f"Verification summary for {run_dir}")
    table.add_column("#", justify="right")
    table.add_column("action")
    table.add_column("coords(final)")
    table.add_column("center_dist(px)")
    table.add_column("verify.delta")
    table.add_column("verify.pass")

    all_pass = True
    for s in steps:
        meta = s.get("meta") or {}
        verify = meta.get("verify") or {}
        coords = meta.get("coords", {})
        final = coords.get("final")
        dist = _center_distance(meta)
        center_dist = f"{dist[2]:.1f}" if dist else ""
        vdelta = verify.get("delta")
        vpass = verify.get("pass")
        table.add_row(
            str(s.get("step_index")),
            str(s.get("next_action")),
            str(final) if final else "",
            center_dist,
            f"{vdelta:.4f}" if isinstance(vdelta, (int, float)) else "",
            str(vpass) if vpass is not None else "",
        )
        # Consider a step verified if verify.pass is True when present; otherwise ignore
        if vpass is False:
            all_pass = False

    console.print(table)

    if not all_pass:
        console.print("[red]One or more steps failed visual verification.[/red]")
        sys.exit(1)
    else:
        console.print("[green]All available verifications passed.[/green]")
        sys.exit(0)


if __name__ == "__main__":
    main()
