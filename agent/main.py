from __future__ import annotations
import argparse, os, sys, yaml
from datetime import datetime, timezone
from dotenv import load_dotenv
from rich.console import Console
from agent.model import get_adapter
from agent.loop import Stepper

# Load environment variables from .env file
load_dotenv()

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fp:
        return yaml.safe_load(fp)

def create_run_dir() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_dir = os.path.join("runs", ts)
    os.makedirs(run_dir, exist_ok=True)
    return run_dir

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()
    console = Console()
    cfg = load_config(args.config)
    adapter = get_adapter(cfg.get("provider","openai"), cfg.get("model","gpt-5.1-thinking"), float(cfg.get("temperature",0.2)), int(cfg.get("max_output_tokens",800)))
    run_dir = create_run_dir()
    stepper = Stepper(cfg, run_dir, adapter, console)
    console.print("[bold green]DesktopOps Agent[/bold green] — type instructions. Use /stop to end.")
    try:
        while True:
            console.print("[bold]>></bold] ", end="")
            instruction = sys.stdin.readline()
            if not instruction: break
            instruction = instruction.strip()
            if instruction in ("/stop","/exit","/quit"): break
            if not instruction: continue
            stepper.run_instruction(instruction)
    finally:
        stepper.close()
        console.print(f"[dim]Logs at {run_dir}[/dim]")

if __name__ == "__main__":
    main()
