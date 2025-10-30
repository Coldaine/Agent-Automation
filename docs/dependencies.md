# Dependencies & Setup

## Python
- Python 3.10+ recommended
- Install via `make setup`

## Runtime libraries
- **PyAutoGUI** — native input for mouse/keyboard (permissions may be required).
- **MSS** — fast screenshots (pure Python).
- **Pillow** — image I/O and JPEG compression.
- **rich** — console tables.

## Provider SDKs (optional)
- **OpenAI** — structured outputs + multimodal via Chat Completions.
- **Anthropic** — Claude SDK.
- **Google Gemini** — image understanding.

## OS permissions
### macOS
- **Accessibility** (keyboard & mouse control)
- **Screen Recording** (for screenshots)

### Windows
- Optional UIA (pywinauto) for semantic automation.

### Linux
- Prefer X11 for synthetic input; Wayland compositors may restrict it.
