from __future__ import annotations
# Environment: managed with 'uv' (https://github.com/astral-sh/uv). See README for setup.
import json
import re
from typing import Any, Dict, Tuple

# Public action set used across the app; OCR/Text actions are gated at runtime
ALLOWED_ACTIONS = {
    "NONE",
    "MOVE",
    "CLICK",
    "DOUBLE_CLICK",
    "RIGHT_CLICK",
    "TYPE",
    "HOTKEY",
    "SCROLL",
    "DRAG",
    "WAIT",
    # Phase 2 / optional features (guarded)
    "CLICK_TEXT",
    "UIA_INVOKE",
    "UIA_SET_VALUE",
}

# Known wrappers and prefaces frequently produced by providers
WRAPPER_PATTERNS = [
    r"^<\|begin_of_box\|>\s*", r"\s*<\|end_of_box\|>$",  # GLM wrapper
    r"^```(?:json)?\s*", r"\s*```$",                      # fences
    r"^\s*(?:Here is the JSON:?|Output:?|Result:?)[\s\n]*",  # prefaces
]
ZERO_WIDTH = r"[\u200B-\u200D\uFEFF]"  # BOM/zero-width chars


def clean_model_text(s: str) -> str:
    """Remove provider wrappers, code fences, zero-width chars; trim to first {...} block."""
    s = re.sub(ZERO_WIDTH, "", s or "")
    for pat in WRAPPER_PATTERNS:
        s = re.sub(pat, "", s, flags=re.IGNORECASE | re.DOTALL)
    # Trim to first JSON object if extra prose remains
    m = re.search(r"\{.*\}", s, flags=re.DOTALL)
    return m.group(0) if m else s.strip()


def _validate_schema_root(d: Any) -> Dict[str, Any]:
    if not isinstance(d, dict):
        raise ValueError("Root must be a JSON object")
    # Minimal required keys for the loop; plan/say are optional
    if "next_action" not in d or "done" not in d:
        raise ValueError("Missing required keys: next_action, done")
    if "args" in d and not isinstance(d.get("args"), dict):
        raise ValueError("args must be an object if provided")
    d.setdefault("args", {})
    return d


def validate_payload(d: Dict[str, Any], *, ocr_enabled: bool) -> Dict[str, Any]:
    """Contract checks independent of provider; raises ValueError with crisp messages."""
    d = _validate_schema_root(d)

    # Legacy keyword should be rejected loudly so it shows in logs/tests
    if d.get("next_action") == "DONE":
        raise ValueError('Invalid next_action: DONE (use {"next_action":"NONE","done":true})')

    if d.get("done") is True:
        if d.get("next_action") != "NONE":
            raise ValueError('When done:true, next_action must be "NONE"')
        return d

    na = str(d.get("next_action")) if d.get("next_action") is not None else None
    if na not in ALLOWED_ACTIONS:
        raise ValueError(f"Invalid next_action: {na}")

    # Feature gating
    if not ocr_enabled and na == "CLICK_TEXT":
        raise ValueError("CLICK_TEXT not allowed when OCR is disabled")

    return d


def parse_step(raw_text: str, *, ocr_enabled: bool) -> Dict[str, Any]:
    """Clean and parse a model response and enforce action contract. Raises ValueError on failure."""
    cleaned = clean_model_text(raw_text)
    try:
        data = json.loads(cleaned)
    except Exception as e:
        raise ValueError(f"Invalid JSON after cleaning: {e}; first 120={cleaned[:120]!r}")
    return validate_payload(data, ocr_enabled=ocr_enabled)


# Back-compat helper used by older tests and code paths. Returns (payload, err).
def parse_structured_output(raw_text: str) -> Tuple[Dict[str, Any], str]:
    try:
        payload = parse_step(raw_text, ocr_enabled=True)
        # Ensure plan/say keys exist for downstream consumers
        payload.setdefault("plan", str(payload.get("plan", "")))
        payload.setdefault("say", payload.get("say"))
        return payload, ""
    except Exception as e:
        return {}, str(e)
