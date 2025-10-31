from __future__ import annotations
# Environment: managed with 'uv' (https://github.com/astral-sh/uv). See README for setup.
import json
from typing import Any, Dict, Tuple

REQUIRED_KEYS = {"plan", "next_action", "args", "done"}

VALID_ACTIONS = {
    "MOVE","CLICK","DOUBLE_CLICK","RIGHT_CLICK","TYPE","HOTKEY",
    "SCROLL","DRAG","WAIT","NONE",
    # Phase 2 actions (disabled - need implementation fixes)
    # "CLICK_TEXT","UIA_INVOKE","UIA_SET_VALUE"
}

def parse_structured_output(raw_text: str) -> Tuple[Dict[str, Any], str]:
    """Accepts either pure JSON or markdown fenced JSON. Returns (payload, err)."""
    txt = raw_text.strip()
    if "```" in txt:
        start = txt.find("```")
        end = txt.find("```", start + 3)
        if end != -1:
            txt = txt[start+3:end].strip()
            if txt.startswith("json"):
                txt = txt[4:].strip()
    try:
        data = json.loads(txt)
    except Exception as e:
        return {}, f"Invalid JSON from model: {e}"

    missing = REQUIRED_KEYS - set(data.keys())
    if missing:
        return {}, f"Missing keys: {missing}"

    if data["next_action"] not in VALID_ACTIONS:
        return {}, f"Invalid next_action: {data['next_action']}"

    if not isinstance(data["args"], dict):
        return {}, "args must be an object"

    data.setdefault("say", None)
    data.setdefault("plan", str(data["plan"]))
    return data, ""
