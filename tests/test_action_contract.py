from __future__ import annotations
import pytest
from agent.parser import parse_step

def test_rejects_legacy_done():
    with pytest.raises(ValueError, match="Invalid next_action: DONE"):
        parse_step('{"next_action": "DONE", "done": false}', ocr_enabled=True)

def test_enforces_none_on_done():
    with pytest.raises(ValueError, match="When done:true, next_action must be"):
        parse_step('{"next_action": "CLICK", "done": true}', ocr_enabled=True)

def test_accepts_valid_done():
    payload = parse_step('{"next_action": "NONE", "done": true}', ocr_enabled=True)
    assert payload["done"] is True
    assert payload["next_action"] == "NONE"

def test_click_text_gating():
    with pytest.raises(ValueError, match="CLICK_TEXT not allowed when OCR is disabled"):
        parse_step('{"next_action": "CLICK_TEXT", "args": {"text": "hello"}, "done": false}', ocr_enabled=False)

def test_pointer_action_requires_coords():
    for action in ["MOVE", "CLICK", "DOUBLE_CLICK", "RIGHT_CLICK", "DRAG"]:
        with pytest.raises(ValueError, match="requires usable coordinates"):
            parse_step(f'{{"next_action": "{action}", "args": {{}}, "done": false}}', ocr_enabled=True)

@pytest.mark.parametrize("coord_arg", [
    '{"x": 100, "y": 200}',
    '{"cx": 100, "cy": 200}',
    '{"coordinates": [100, 200]}',
    '{"point": [100, 200]}',
    '{"position": {"x": 100, "y": 200}}',
    '{"center": {"x": 100, "y": 200}}',
    '{"target": [100, 200]}',
    '{"location": [100, 200]}',
    '{"bbox": [100, 200, 300, 400]}'
])
def test_pointer_action_accepts_valid_coords(coord_arg):
    for action in ["MOVE", "CLICK", "DOUBLE_CLICK", "RIGHT_CLICK", "DRAG"]:
        payload = parse_step(f'{{"next_action": "{action}", "args": {coord_arg}, "done": false}}', ocr_enabled=True)
        assert payload["next_action"] == action