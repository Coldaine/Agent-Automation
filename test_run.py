#!/usr/bin/env python
"""Quick test script to run the agent with a simple instruction."""
import yaml
from rich.console import Console
from agent.model import get_adapter
from agent.loop import Stepper
import os
from datetime import datetime, timezone

def main():
    # Load config
    with open("config.yaml", "r", encoding="utf-8") as fp:
        cfg = yaml.safe_load(fp)
    
    # Create run directory
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_dir = os.path.join("runs", ts)
    os.makedirs(run_dir, exist_ok=True)
    
    # Create adapter and stepper
    console = Console()
    provider = cfg.get("provider", "zhipu")
    model = cfg.get("model", "glm-4.6")
    adapter = get_adapter(
        provider,
        model,
        float(cfg.get("temperature", 0.2)),
        int(cfg.get("max_output_tokens", 800))
    )
    stepper = Stepper(cfg, run_dir, adapter, console)
    
    # Run a simple test instruction
    console.print(f"[bold green]Testing DesktopOps Agent with {provider} provider[/bold green]")
    console.print("[yellow]Instruction:[/yellow] type hello world")
    stepper.run_instruction("type hello world")
    
    # Cleanup
    stepper.close()
    console.print(f"\n[dim]✓ Test complete! Logs at {run_dir}[/dim]")

if __name__ == "__main__":
    main()