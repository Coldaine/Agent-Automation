import json
from agent.parser import parse_structured_output


def test_new_actions_allowed():
    for action in ["CLICK_TEXT", "UIA_INVOKE", "UIA_SET_VALUE"]:
        payload = {"plan": "x", "next_action": action, "args": {}, "done": False}
        raw = json.dumps(payload)
        data, err = parse_structured_output(raw)
        assert not err, f"unexpected error for action {action}: {err}"
        assert data["next_action"] == action
