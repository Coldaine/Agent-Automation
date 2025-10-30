# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DesktopOps Agent** is a minimal, local-first conversational AI agent that controls your real desktop using native mouse and keyboard input. It operates in a simple loop: capture screenshot → send to AI model → parse JSON response → execute action → log results. The agent works across any open application or browser window.

**Key constraint:** All actions must be executable via PyAutoGUI synthetic input or safe logging. No dependencies on browser automation frameworks, RPA suites, or OS-specific APIs (except where optional/fallback).

---

## Development Commands

Use these Make targets for common tasks:

```bash
make setup      # Create venv + install requirements.txt
make run        # Launch interactive agent (python -m agent.main)
make test       # Run pytest suite (unit + integration tests)
make lint       # Check code style with ruff
make format     # Auto-format with ruff --fix && black
```

**Run a single test:**
```bash
.venv/Scripts/activate   # or: source .venv/bin/activate (macOS/Linux)
pytest tests/test_parser.py::test_parse_valid_json -v
pytest tests/test_loop_dryrun.py -v -s
```

**Testing safely (dry-run mode):**
```bash
# Set dry_run: true in config.yaml, then run normally
make run
# Try: "open a new browser tab"  ← No actual mouse/keyboard events will execute
```

---

## Architecture & Design

### High-Level Flow

```
User Input (chat)
    ↓
[Stepper Loop] agent/loop.py
    ├→ Capture screenshot (MSS) → tools/screen.py
    ├→ Send to model adapter → agent/model.py
    ├→ Parse JSON response → agent/parser.py
    ├→ Execute action → tools/input.py
    ├→ Log step to JSONL + save screenshot
    └→ Display in console → ui/console.py
    ↓
[Repeat until done:true or max_steps]
```

### Core Modules

| Module | Role | Key Details |
|--------|------|-------------|
| `agent/main.py` | Entry point, config loader, CLI loop | Loads `config.yaml`, creates timestamped run directory, orchestrates interactive user → stepper → display |
| `agent/loop.py` (Stepper class) | Step orchestrator | Per-step: screenshot → model → action dispatch → logging. Enforces `max_steps` and `min_interval_ms` |
| `agent/model.py` | Model adapters (factory pattern) | `BaseModelAdapter` + 4 implementations: OpenAIAdapter, AnthropicAdapter, GeminiAdapter, DummyAdapter. Each wraps provider API and structured output parsing |
| `agent/parser.py` | JSON validation | Extracts & validates `{plan, next_action, args, done}` from model output. Handles markdown-fenced JSON |
| `agent/state.py` | Data model | `Step` dataclass for serialization: index, plan, action, args, observation, screenshot_path |
| `tools/screen.py` | Screenshot capture | Uses MSS for speed; downscales (default 1280px width), JPEG-compresses (q70), encodes base64 for models. Saves full PNG locally |
| `tools/input.py` | OS automation | PyAutoGUI wrapper. 9 actions: MOVE, CLICK, DOUBLE_CLICK, RIGHT_CLICK, TYPE, HOTKEY, SCROLL, DRAG, WAIT. Dry-run mode returns descriptions instead |
| `tools/overlay.py` | Visual feedback (optional) | Transient crosshair at click position. Tkinter-based; gracefully degrades if unavailable |
| `ui/console.py` | Terminal output | Rich library for ASCII step tables and formatted messages |

### Configuration (config.yaml)

```yaml
provider: openai              # Model provider: openai | anthropic | gemini | dummy
model: gpt-5.1-thinking      # Model name (swappable without code edits)
temperature: 0.2             # Model creativity (0-1, low = deterministic)
max_output_tokens: 800       # Output size limit
dry_run: true                # Simulate actions without OS events
overlay:
  enabled: false             # Visual feedback at click positions
  duration_ms: 250           # Crosshair display time
loop:
  max_steps: 50              # Max steps per instruction
  min_interval_ms: 400       # Min delay between steps (prevents thrashing)
screenshot:
  width: 1280                # Downscale width for model (preserves aspect)
  quality: 70                # JPEG compression (0-95; lower = smaller/faster)
hotkeys:
  pause: "ctrl+alt+p"        # Reserved for future
  stop: "ctrl+alt+s"         # Reserved for future
```

**API credentials:** Set `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `GOOGLE_API_KEY` via environment or `.env` file.

### Important Architectural Patterns

**1. Adapter Pattern (Model Flexibility)**
- New providers are added by extending `BaseModelAdapter` and implementing `async def step()`.
- Factory function `get_adapter()` selects implementation at runtime.
- **This allows swapping models in config without touching code.**

**2. Structured Outputs**
- OpenAI uses JSON Schema to enforce response format.
- Other providers (Claude, Gemini) parse text JSON internally to a standard format.
- **Parser ensures all adapters return identical `{plan, next_action, args, done}` structure.**

**3. Dry-Run Mode**
- All actions support safe simulation: return human-readable strings instead of executing.
- Enables testing without OS permissions or side effects.
- **Set `dry_run: true` in config for smoke tests.**

**4. Step-Level Observability**
- Every step is logged to JSONL with full context: instruction, plan, action, args, observation, screenshot path.
- Console displays ASCII table for immediate feedback.
- **This enables debugging and audit trails.**

**5. Minimal Dependencies**
- No heavy RPA frameworks (TagUI, UiPath) or browser automation (Selenium, Playwright).
- Only essential: PyAutoGUI, MSS, Pillow, Rich, provider SDKs.
- **Easier to maintain, debug, and extend.**

### Latency & Performance Notes

**Target: < 2s per step**
- Screen capture (MSS): ~10–40 ms
- JPEG downscale + compress: ~20–80 ms
- Model round-trip: variable (dominant cost; mitigate with smaller images)
- Input execution: ~1–30 ms
- **Optimizations in backlog:** screenshot hash caching, optional OCR grounding

---

## When Adding Features

### Adding a New Model Provider

1. Create a new adapter class in `agent/model.py` extending `BaseModelAdapter`:
   ```python
   class MyProviderAdapter(BaseModelAdapter):
       async def step(self, instruction, last_observation, steps, image_data):
           # Call your provider's API
           # Parse response to {plan, next_action, args, done}
           # Return Step dataclass
   ```

2. Update `get_adapter()` factory function to recognize the provider.
3. Document the new provider in `config.yaml` example.
4. Add environment variable for API key (e.g., `MY_PROVIDER_API_KEY`).

### Adding a New Action Type

1. Update `tools/input.py`:
   - Add action to the 9 supported types (MOVE, CLICK, HOTKEY, etc.)
   - Implement PyAutoGUI call + dry-run description
2. Update `agent/parser.py` validation to allow the new action name.
3. Add test case in `tests/test_parser.py`.

### Modifying the Step Loop

The stepper is tightly controlled by:
- `agent/loop.py:Stepper.run_instruction()` — the main loop
- `loop.max_steps` config — prevents runaway loops
- `loop.min_interval_ms` — prevents thrashing

**Do not** add blocking I/O or significant latency inside the loop. If adding a feature that needs multiple steps, consider whether it should be batched into a single model call.

### Improving Screenshot Capture

`tools/screen.py` handles image encoding. Tuning knobs:
- `screenshot.width` — lower = faster/smaller, but less detail for model
- `screenshot.quality` — lower = faster/smaller, but more JPEG artifacts
- **Backlog:** implement hash-based caching to skip sending identical frames

---

## Testing Strategy

**Unit tests** (`tests/test_parser.py`):
- JSON parsing edge cases (valid, invalid, markdown-fenced)
- Schema validation (required keys, allowed actions)

**Integration tests** (`tests/test_loop_dryrun.py`):
- Full stepper loop with mocked screen + Dummy model
- Validates action dispatch and logging
- **No OS side effects**

**Smoke test** (manual):
1. Set `dry_run: true`
2. Run `make run`
3. Type: `"open a new browser tab and search for 'python dataclasses'"`
4. Observe step table + JSONL in `runs/<timestamp>/`

**Real-world test** (careful):
1. Grant OS permissions (see `/docs/dependencies.md`)
2. Set `dry_run: false` and provider credentials
3. Start with simple commands: `"open calculator"`, `"scroll down"`

---

## Output & Artifacts

Each run creates a timestamped directory in `runs/<timestamp>/`:
- **steps.jsonl** — line-delimited JSON, one per step with full context
- **step_0001_*.png** — screenshot after step 1 (PNG, full resolution)
- **step_0002_*.png** — screenshot after step 2
- etc.

Example JSONL line:
```json
{"step_index":1,"plan":"open browser","next_action":"HOTKEY","args":{"keys":["ctrl","t"]},"say":"Opening new tab.","observation":"(dry-run) hotkey ctrl+t","screenshot_path":"runs/20250101T120000/step_0001.png"}
```

---

## Known Limitations

- **Wayland on Linux:** PyAutoGUI may not work without X11 or compositor permissions.
- **macOS:** Requires **Accessibility** and **Screen Recording** permissions. See `/docs/dependencies.md`.
- **Provider-specific:** OpenAI structured outputs (JSON Schema) are stricter than others. Claude/Gemini adapters parse text JSON.
- **No semantic UI queries (yet):** Actions are pixel-based (mouse coords). OCR/accessibility tree integration is a future enhancement.

---

## Roadmap (Backlog)

- Screenshot hash caching (skip redundant frames).
- Windows UIA integration (pywinauto) for semantic control.
- OCR + small vision model for robust element targeting.
- Task graphs (macro recording + replay with parameters).

---

## Code Style & Standards

- **Formatter:** `ruff` + `black` (run `make format`)
- **Linter:** `ruff` (run `make lint`)
- **Python:** 3.10+
- **Async:** Used in model adapters (via `asyncio`); sync elsewhere.
- **Logging:** JSONL for step artifacts; console output via Rich.

---

## References

- `/docs/architecture.md` — detailed component dataflow & latency budget
- `/docs/visions.md` — ANCHOR mapping & prior art comparison
- `/docs/testing.md` — testing modes & examples
- `/docs/dependencies.md` — OS permissions & environment setup
- `/docs/changelog.md` — version history
