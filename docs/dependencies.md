# Dependencies & Setup

## Python & environment
- Python 3.10+ recommended
- Environment managed with [uv](https://github.com/astral-sh/uv)

### Setup (Windows)
```powershell
# 1. Install uv (one time)
winget install --id Astral.UV -e    # or: pipx install uv

# 2. Install Tesseract OCR (required for CLICK_TEXT)
winget install --id UB-Mannheim.TesseractOCR -e
# Add to PATH if needed:
$env:Path += ";C:\Program Files\Tesseract-OCR"
[Environment]::SetEnvironmentVariable("Path", $env:Path, "User")

# 3. Create/refresh virtual env and sync deps
uv sync || (uv venv; uv pip install -r requirements.txt)
```

### Windows-Specific Optimizations
- **pywin32**: Native win32 API for faster mouse/keyboard input
- **PIL.ImageGrab**: Native Windows screenshot (faster than mss)
- **pywinauto**: Windows UI Automation for semantic element control
- **pytesseract**: OCR text recognition (requires Tesseract binary)

## Runtime libraries
- **PyAutoGUI** — native input for mouse/keyboard (permissions may be required).
- **MSS** — fast screenshots (pure Python).
- **Pillow** — image I/O and JPEG compression.
- **rich** — console tables.

## Provider SDKs (optional)
- **OpenAI** — structured outputs + multimodal via Chat Completions.
- **Anthropic** — Claude SDK.
- **Google Gemini** — image understanding.

## OS Support

**Windows is the primary supported platform** with full functionality and optimizations. Cross-platform support for macOS and Linux is not a priority and may have limited functionality or require additional setup.
## OS permissions
### macOS
- **Accessibility** (keyboard & mouse control)
- **Screen Recording** (for screenshots)

### Windows
- Optional UIA (pywinauto) for semantic automation.

### Linux
- Prefer X11 for synthetic input; Wayland compositors may restrict it.
