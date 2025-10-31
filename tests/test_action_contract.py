import pytest
from agent.parser import parse_step


def test_done_contract_ok():
    payload = parse_step('{"next_action":"NONE","done":true}', ocr_enabled=False)
    assert payload["done"] is True
    assert payload["next_action"] == "NONE"


def test_done_legacy_rejected():
    with pytest.raises(ValueError) as ex:
        parse_step('{"next_action":"DONE","done":true}', ocr_enabled=False)
    assert "Invalid next_action: DONE" in str(ex.value)


def test_click_text_gated_when_ocr_off():
    with pytest.raises(ValueError) as ex:
        parse_step('{"next_action":"CLICK_TEXT","args":{"text":"OK"}}', ocr_enabled=False)
    assert "CLICK_TEXT not allowed" in str(ex.value)
