# Testing

## Unit tests
Run `make test` to execute:
- `tests/test_parser.py` — validates model JSON parsing and error handling.
- `tests/test_loop_dryrun.py` — runs a dry-run stepper loop using the Dummy model (no OS actions).

## Smoke scenarios
### Dry-run (safe)
1. Ensure `dry_run: true` in `config.yaml`.
2. `make run`
3. Try commands like:
   - `open a new tab and search for "python dataclasses"`
   - `type hello world and press enter`

### Real mode (be careful)
1. Grant required OS permissions (see `/docs/dependencies.md`).
2. Set `dry_run: false` and provider credentials.
3. `make run`, then:
   - `open a new tab (hotkey ctrl+t), type "news", press enter`
   - `scroll down`

**Sample JSONL line**
```json
{"step_index":1,"plan":"type the instruction as text","next_action":"TYPE","args":{"text":"type hello world"},"say":"Focusing text field and typing your instruction.","observation":"(dry-run) type 'type hello world'","screenshot_path":"runs/20250101T120000/step_0001_20250101T120000.png"}
```
