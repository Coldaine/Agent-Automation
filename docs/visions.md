# PROJECT VISION & ANCHORS

This document lists the ANCHORS verbatim and how v0.1.0 meets them.

| Anchor | Text | Status | How we satisfy it |
|---|---|---|---|
| R1 | Live conversational interface | ✓ | `ui/console.py` chat loop; `agent/main.py` reads commands interactively. |
| R2 | Visibility of `{plan, next_action, args, observation}` | ✓ | Step table in console; JSONL in `/runs/<ts>/steps.jsonl`; screenshots per step. |
| R3 | Real OS input | ✓ | `tools/input.py` via PyAutoGUI for native mouse/keyboard. |
| R4 | Works across windows/apps | ✓ | No sandbox; acts on active desktop; vision from full-screen screenshots. |
| R5 | Reasoning model swappable | ✓ | `agent/model.py` adapters; config selects provider/model; no code edits. |
| R6 | Composable tools | ✓ | `tools/screen.py`, `tools/input.py`, `tools/overlay.py` are thin, replaceable. |
| R7 | Low-latency loop | △ | Resize/compress screenshots; caching path reserved; budget in `architecture.md`. |
| R8 | Local-first UX | ✓ | Uses your running sessions and profiles; no special browser container. |
| R9 | Docs-as-product | ✓ | This file + `architecture.md`, `testing.md`, `dependencies.md`, `changelog.md`. |

**Near-term roadmap**
- Cache previous screenshot hash to skip sending identical frames (improve R7).
- Optional Windows UIA (pywinauto) and macOS AX UI queries for semantic targets.
- Overlay improvements (GPU-accelerated overlay).
- Optional OCR to align text targets without coordinates.

**Research & prior art snapshot** (what we borrow vs skip)

| Tool / Framework | Borrow | Depend | Skip | Why |
|---|:--:|:--:|:--:|---|
| PyAutoGUI | ✓ | ✓ |  | Cross‑platform mouse/keyboard. |
| MSS | ✓ | ✓ |  | Ultra‑fast screenshots. |
| pynput | ✓ |  |  | Alternative input control/hotkeys if needed. |
| SikuliX | ✓ |  |  | Inspiration for vision‑driven clicks; heavy Java dep so not default. |
| TagUI (RPA) |  |  | ✓ | We want minimal agent+tools, not full RPA stack. |
| pywinauto (Windows) | ✓ |  |  | Optional backend for semantic UIA targeting on Windows. |
