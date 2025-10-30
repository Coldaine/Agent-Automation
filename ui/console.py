from __future__ import annotations
from rich.console import Console
from rich.table import Table
console = Console()
def print_step_table(step_dict):
    table = Table(show_header=True, header_style="bold")
    table.add_column("plan", ratio=3)
    table.add_column("next_action", ratio=1)
    table.add_column("args", ratio=3)
    table.add_column("observation", ratio=3)
    table.add_row(str(step_dict.get("plan","")), str(step_dict.get("next_action","")), str(step_dict.get("args",{})), str(step_dict.get("observation","")))
    console.print(table)
def say_to_user(text: str):
    if text: console.print(f"[bold cyan]Agent:[/bold cyan] {text}")
