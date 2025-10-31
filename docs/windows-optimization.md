# Windows Optimization Guide

## Overview
The DesktopOps Agent is optimized for Windows with native APIs for maximum performance.

## Performance Optimizations

### Input (Mouse & Keyboard)
- **Native win32 API**: Uses `win32api.SetCursorPos()` and `win32api.mouse_event()` directly
- Falls back to pyautogui if pywin32 not available (with an explicit warning in logs if a feature can't start)
- Low-latency cursor movement with `SetCursorPos`

### Screenshot Capture
- **PIL.ImageGrab**: Native Windows GDI+ capture
- Direct memory access to screen buffer
- Falls back to mss for cross-platform compatibility (with a one-time warning)

### UI Automation
- **Windows UIA**: Semantic element targeting via pywinauto
- Access controls by name, automation_id, control_type
- More reliable than pixel-based clicking
- Enabled by default in config.yaml

### OCR Text Recognition
- **Tesseract OCR**: Fast text detection and clicking
- CLICK_TEXT action for "click the Settings button" commands
- Enabled by default; install via: `winget install --id UB-Mannheim.TesseractOCR -e`

## Configuration Tuning

### High-Performance Settings
```yaml
loop:
  max_steps: 50
  min_interval_ms: 100    # Faster loop for native APIs

screenshot:
  width: 1920             # Higher res for better OCR
  quality: 80             # Balance quality/speed

windows_uia:
  enabled: true
  prefer_uia: true        # Prefer semantic over pixel clicks

ocr:
  enabled: true
  min_score: 0.75         # Stricter matching for accuracy
```

### Low-Latency Settings
```yaml
loop:
  min_interval_ms: 50     # Minimal delay between steps

screenshot:
  width: 1280             # Lower res for speed
  quality: 70

overlay:
  enabled: false          # Disable visual feedback for speed
```

## Installation

### Quick Setup (Recommended)
```powershell
# Install everything needed
winget install --id Astral.UV -e
winget install --id UB-Mannheim.TesseractOCR -e

# Setup environment
uv venv
uv pip install -r requirements.txt

# Verify installations
python -c "import win32api; print('win32: OK')"
python -c "import pywinauto; print('UIA: OK')"
tesseract --version
```

### Verify Windows Optimizations
```powershell
# Run this to confirm native APIs are active
uv run python -c "from tools.input import InputController; import platform; ic = InputController(dry_run=False); print(f'Windows: {platform.system()}'); print(f'win32 active: {ic._win32 is not None}')"

uv run python -c "from tools.screen import Screen; s = Screen('test'); print(f'Native capture: {s._use_native}')"
```

## Troubleshooting

### pywin32 Issues
```powershell
# Reinstall pywin32
uv pip uninstall pywin32
uv pip install --force-reinstall pywin32

# Run post-install script
python Scripts/pywin32_postinstall.py -install
```

### Tesseract Not Found
```powershell
# Add to PATH manually
$tesseractPath = "C:\Program Files\Tesseract-OCR"
[Environment]::SetEnvironmentVariable("Path", "$env:Path;$tesseractPath", "User")

# Verify
tesseract --version
```

### UIA Access Denied
- Some apps require admin privileges to automate
- Run PowerShell as Administrator if targeting elevated apps
- Or use OCR/pixel clicking as fallback

## Performance Notes

These optimizations reduce latency on Windows by using native APIs. Actual performance varies by hardware, display configuration, and background load. Use the live tests and run artifacts in `runs/<timestamp>/steps.jsonl` to observe timings on your machine.

## Best Practices

1. **Enable UIA first**: Semantic control is more reliable than pixels
2. **Use OCR for text**: "click Settings" is more maintainable than coordinates
3. **Test in dry-run**: Verify actions before enabling real control
4. **Monitor performance**: Check `runs/<timestamp>/steps.jsonl` for timings
5. **Fallback gracefully**: Code automatically falls back to cross-platform methods if native APIs unavailable

## Additional Resources
- pywin32 docs: https://github.com/mhammond/pywin32
- pywinauto guide: https://pywinauto.readthedocs.io/
- Tesseract install: https://github.com/UB-Mannheim/tesseract/wiki
