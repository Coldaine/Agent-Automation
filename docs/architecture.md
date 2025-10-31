# Architecture

## Components & dataflow
```
User chat -> TUI (ui/console)
    -> Stepper (agent/loop)
    -> Screen.capture()        # tools/screen (Windows: ImageGrab; fallback mss with warning)
    -> ModelAdapter.step()     # agent/model (OpenAI/Zhipu/Claude/Gemini/Dummy)
    <- {plan,next_action,args,done} JSON (no chain-of-thought)
    -> InputController         # tools/input (Windows: win32; fallback pyautogui)
    -> Overlay (optional)      # tools/overlay (always-on warns on failure)
        -> Log JSONL + screenshot  # /runs/<ts>/
```

## State machine (minimal stepper)
1. Capture screenshot (full screen, optional region).
2. Send `{instruction, last_observation, recent_steps, screenshot}` to model.
3. Parse structured JSON → dispatch to input tool.
    - New actions: CLICK_TEXT (OCR), UIA_INVOKE/UIA_SET_VALUE (Windows UIA)
    - Non-silent fallbacks: OCR/UIA errors surface in step observations
4. Log `{plan, action, args, observation}` to console and JSONL.
5. Repeat until `done:true` or user stops.

## Latency budget (target < 2s/step)
- Screen capture via MSS: ~10–40 ms on HD.
- JPEG resize/compress (1280w, q70): ~20–80 ms CPU.
- Model round-trip: variable; mitigate with smaller images & concise prompts.
- Input execution: ~1–30 ms typical.
- Total: **~< 1s on LAN**, with room for network/model latency.

**Optimizations**
- Send downscaled JPEG only.
- Cache last screenshot hash; skip sending if unchanged. (planned)
- Tune `loop.min_interval_ms` for stability.
*Windows-specific*
- Prefer native ImageGrab and win32 input. Fallbacks emit warnings rather than failing silently.

## Framework choices (Windows-first rationale)
The DesktopOps Agent prioritizes Windows with native optimizations while providing cross-platform fallbacks for compatibility. While the project uses cross-platform libraries, **Windows is the primary and supported platform**.

**Primary Platform (Windows):**
- **pywin32**: Native win32 API for faster mouse/keyboard input
- **PIL.ImageGrab**: Native Windows screenshot (faster than mss)
- **pywinauto**: Windows UI Automation for semantic element control
- **pytesseract**: OCR text recognition (requires Tesseract binary)

**Cross-platform fallbacks (for macOS/Linux compatibility):**
- **PyAutoGUI**: Simple, cross‑platform mouse/keyboard input when native APIs unavailable
- **MSS**: Fast, pure‑Python screenshots when native Windows capture unavailable
- **Structured outputs**: OpenAI JSON Schema / similar patterns
- **Provider flexibility**: Stubs for Anthropic/Gemini
## Framework choices (rationale)
- **PyAutoGUI**: simple, cross‑platform mouse/keyboard.
- **MSS**: fast, pure‑Python screenshots.
- **Structured outputs**: OpenAI JSON Schema / similar patterns.
- **Provider flexibility**: Stubs for Anthropic/Gemini.
