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
- `tests/test_parser_new_actions.py` — ensures the parser accepts Windows Phase 2 actions.
- `tests/test_loop_new_actions.py` — exercises new actions via fakes in dry-run.

Guidelines for new tests:
- Prefer unit tests with deterministic inputs; avoid real OS control.
- Use the `dry_run` mode and mock/fake `Screen.capture_and_encode` like `test_loop_dryrun.py` does.
- For provider adapters, mock SDK clients to avoid network calls.
- If you add optional integration tests, gate them behind env flags (e.g., `ZHIPU_E2E=1`) and skip by default.

## Live Windows integration tests (opt-in, no mocks)

We include two Windows-only integration tests that exercise real UI Automation (UIA), OCR, and input. They are disabled by default and require an explicit opt-in to avoid unsafe runs on CI.

Prerequisites:
- Windows host with desktop session (not headless)
- Tesseract OCR installed and on PATH (winget: `UB-Mannheim.TesseractOCR`)
- Environment variable `RUN_LIVE_TESTS=1`

Tests:
- `tests/integration/test_live_uia_notepad.py`
   - Launches Notepad, finds the Edit control via UIA, sets text, and cleans up.
- `tests/integration/test_live_ocr_tk.py`
   - Renders a Tk window with visible text, captures the screen, detects the text via Tesseract, and performs a real click at the detected location.

Run (opt-in):
```powershell
$env:RUN_LIVE_TESTS = "1"
uv run -m pytest -q tests/integration
```
Notes:
- Tests will skip with a clear reason unless all prerequisites are met.
- These tests avoid mocks and will fail loudly if a dependency is missing at runtime (e.g., Tesseract missing).

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
## Platform Support

**Windows is the primary supported platform** for full testing and development. Cross-platform support (macOS/Linux) is not a priority and testing on these platforms may have limited functionality or require additional setup.

### Testing Scope
- **Windows**: Full functionality including Windows-only integration tests
- **macOS/Linux**: Limited testing with cross-platform fallbacks; not a priority
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
