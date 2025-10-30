# Changelog

## v0.1.0 — initial release
- Minimal stepper loop with visibility of `{plan, next_action, args, observation}`.
- OpenAI provider with structured outputs; adapters for Anthropic/Gemini; Dummy model for tests.
- Native input (PyAutoGUI) + fast screenshots (MSS).
- TUI console with per-step table.
- JSONL logs + screenshots in `/runs/<ts>/`.
- Unit tests for parser + dry-run smoke test.
- Docs: vision & anchors, architecture, testing, dependencies.
