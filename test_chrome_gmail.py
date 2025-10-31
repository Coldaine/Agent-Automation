#!/usr/bin/env python
"""Test script: Open Chrome and navigate to Gmail."""
import yaml
from rich.console import Console
from agent.model import get_adapter
from agent.loop import Stepper
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    # Load config
    with open("config.yaml", "r", encoding="utf-8") as fp:
        cfg = yaml.safe_load(fp)
    
    # Create run directory
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_dir = os.path.join("runs", ts)
    os.makedirs(run_dir, exist_ok=True)
    
    # Create adapter and stepper
    console = Console()
    console.print(f"[bold green]Using {cfg['provider']} - {cfg['model']}[/bold green]")
    console.print(f"[bold red]LIVE MODE: dry_run = {cfg['dry_run']}[/bold red]")
    
    adapter = get_adapter(
        cfg.get("provider"),
        cfg.get("model"),
        float(cfg.get("temperature", 0.2)),
        int(cfg.get("max_output_tokens", 800))
    )
    stepper = Stepper(cfg, run_dir, adapter, console)
    
    # Run the instruction
    console.print("\n[bold yellow]Instruction:[/bold yellow] Open Chrome and go to gmail.com")
    console.print("[dim]The agent will take screenshots and decide what to click/type...[/dim]\n")
    
    stepper.run_instruction("Open Chrome browser and navigate to gmail.com")
    
    # Cleanup
    stepper.close()
    console.print(f"\n[dim]✓ Complete! Logs at {run_dir}[/dim]")

if __name__ == "__main__":
    main()
