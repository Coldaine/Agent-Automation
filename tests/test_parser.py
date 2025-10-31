from __future__ import annotations
import pytest
from agent.parser import clean_model_text

@pytest.mark.parametrize("raw_text, expected_cleaned_text", [
    ('```json\n{"key": "value"}\n```', '{"key": "value"}'),
    ('<|begin_of_box|>{"key": "value"}<|end_of_box|>', '{"key": "value"}'),
    ('Here is the JSON: { "key": "value" }', '{"key": "value"}'),
    ('{"key": "value"} some extra text', '{"key": "value"}'),
])
def test_clean_model_text(raw_text, expected_cleaned_text):
    assert clean_model_text(raw_text).replace(" ", "") == expected_cleaned_text.replace(" ", "")