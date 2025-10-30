# DesktopOps Agent — chat + act on my real desktop

A minimal, **local-first** agent that you can chat with while it controls your *actual* desktop using native mouse & keyboard events. Works across apps, windows, and browsers you already have open.

> **Anchors:** This project implements the ANCHORS from the spec. See `/docs/visions.md` for the ✓ mapping.

---

## Quickstart

```bash
# 1) Python 3.10+ recommended
make setup

# 2) Configure provider & options
cp .env.sample .env              # add your API keys
# edit config.yaml if desired (provider/model, dry_run, overlay, hotkeys)

# 3) Run the agent
make run
```

A `runs/<timestamp>/` folder will be created with JSONL logs and screenshots.

### Example session (dry-run)

```
>> open a new browser tab and search for "site:docs.python.org dataclass"
STEP 1
┌────────────────┬───────────────────────────────────────────────┐
│ plan           │ open browser tab, focus omnibox, type query   │
├────────────────┼───────────────────────────────────────────────┤
│ next_action    │ HOTKEY                                        │
│ args           │ {"keys": ["ctrl","t"]}                        │
│ observation    │ (dry-run) hotkey ctrl+t                       │
└────────────────┴───────────────────────────────────────────────┘
...
```

---

## Features
- **Live conversational loop (R1)** — you type instructions, agent replies and acts step-by-step.
- **Visibility (R2)** — every step streams `{plan, next_action, args, observation}` to the console and to JSONL.
- **Real OS input (R3/R4/R8)** — uses native mouse/keyboard across windows; no sandbox assumptions.
- **Model-flex (R5)** — default OpenAI GPT‑5 Thinking; drop-in config for Claude/Gemini; swap with no code edits.
- **Composable tools (R6)** — `tools/` has tiny, replaceable modules: `screen.py`, `input.py`, `overlay.py`.
- **Responsive loop (R7)** — screenshot downscaling + JPEG compression + frame caching.
- **Local-first UX (R8)** — runs against your *real* apps and Chrome profile.
- **Docs-as-product (R9)** — see `/docs` for vision, architecture, testing, dependencies, changelog.

---

## Make targets

```bash
make setup   # venv + pip install -r requirements.txt
make run     # python -m agent.main
make test    # pytest -q
make lint    # ruff
make format  # ruff --fix && black
```

---

## Config

See `config.yaml`:
- `provider`: `openai` (default), `anthropic`, `gemini`, or `dummy` (for tests)
- `model`: e.g., `gpt-5.1-thinking` (OpenAI), `claude-3-7-sonnet`, `gemini-2.0-flash`
- `dry_run`: `true` to avoid touching the OS (tests/smoke)
- `overlay.enabled`: transient crosshair at click position (best-effort)
- `loop.max_steps`, `loop.min_interval_ms`
- `screenshot.width`, `screenshot.quality`

---

## Limitations
- Wayland Linux may restrict synthetic input; X11 or compositor permissions may be required.
- macOS requires **Accessibility** and **Screen Recording** permission for OS control and screenshots. See `/docs/dependencies.md`.
- The default model adapter uses OpenAI’s structured outputs. Swap providers via config with matching credentials.

---

## Roadmap
- Windows UIA integration (pywinauto) for semantic control (optional, Windows only).
- Cursor semantic grounding (OCR + small vision model) for robust element targeting.
- On-device small vision model fallback for privacy/offline smoke tests.
- Task graphs (macro recording + replay with parameterization).

---

## Sample run artifacts
After a real run, check `runs/<timestamp>/steps.jsonl` and `runs/<timestamp>/step_0001.png`. A short sample log snippet is embedded in `/docs/testing.md`.
