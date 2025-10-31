from __future__ import annotations
# Environment: managed with 'uv' (https://github.com/astral-sh/uv). See README for setup.
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Optional

@dataclass
class Step:
    step_index: int
    plan: str
    next_action: str
    args: Dict[str, Any]
    say: Optional[str]
    observation: str
    screenshot_path: Optional[str]
    # Optional per-step telemetry for debugging/analysis (non-breaking)
    meta: Optional[Dict[str, Any]] = field(default=None)

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)
