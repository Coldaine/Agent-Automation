from agent.parser import parse_structured_output
def test_parse_valid_json():
    raw = '{"plan":"do","next_action":"WAIT","args":{"seconds":0.1},"done":false}'
    data, err = parse_structured_output(raw)
    assert not err
    assert data["next_action"] == "WAIT"
    assert data["args"]["seconds"] == 0.1
def test_parse_fenced_json():
    raw = """```json
{"plan":"x","next_action":"NONE","args":{},"done":true}
```"""
    data, err = parse_structured_output(raw)
    assert not err
    assert data["done"] is True
def test_parse_invalid_json():
    raw = '{"plan":1}'
    data, err = parse_structured_output(raw)
    assert err
