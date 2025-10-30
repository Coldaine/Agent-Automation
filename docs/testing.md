# Testing and Linting

This project uses pytest for tests and Ruff for linting/auto-fix. Our linter/formatter selection is Ruff-only (Black removed).

## Unit tests
Run tests with uv:

```powershell
uv run -m pytest -q
# or
make test
```

Current tests:
- `tests/test_parser.py` — validates model JSON parsing and error handling.
- `tests/test_loop_dryrun.py` — runs a dry-run stepper loop using the Dummy model (no OS actions) and a fake screenshot to avoid OS dependencies.

Guidelines for new tests:
- Prefer unit tests with deterministic inputs; avoid real OS control.
- Use the `dry_run` mode and mock/fake `Screen.capture_and_encode` like `test_loop_dryrun.py` does.
- For provider adapters, mock SDK clients to avoid network calls.
- If you add optional integration tests, gate them behind env flags (e.g., `ZHIPU_E2E=1`) and skip by default.

## Linting and formatting (Ruff-only)

Ruff is the sole linter/formatter. We enable autofix and allow a compact code style via `.ruff.toml`.

Common commands:
```powershell
# Check lints
uv run ruff check .

# Autofix style issues
uv run ruff check . --fix

# Or use Make targets
make lint
make format
```

Key configuration (see `.ruff.toml`):
- `fix = true`, `line-length = 100`, `target-version = "py310"`.
- We ignore some stylistic rules to preserve compact code (e.g., multiple statements/imports per line).
- Black is intentionally removed from the workflow.

## Smoke scenarios

### Dry-run (safe)
1. Ensure `dry_run: true` in `config.yaml`.
2. `uv run -m agent.main`  (or `make run`)
3. Try commands like:
   - `open a new tab and search for "python dataclasses"`
   - `type hello world and press enter`

### Real mode (use caution)
1. Grant required OS permissions (see `/docs/dependencies.md`).
2. Set `dry_run: false` and configure provider credentials.
3. `uv run -m agent.main`, then:
   - `open a new tab (hotkey ctrl+t), type "news", press enter`
   - `scroll down`

Artifacts:
- Each run creates `runs/<timestamp>/steps.jsonl` and step screenshots for visibility.

**Sample JSONL line**
```json
{"step_index":1,"plan":"type the instruction as text","next_action":"TYPE","args":{"text":"type hello world"},"say":"Focusing text field and typing your instruction.","observation":"(dry-run) type 'type hello world'","screenshot_path":"runs/20250101T120000/step_0001_20250101T120000.png"}
```
