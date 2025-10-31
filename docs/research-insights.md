# Research Insights & Implementation Status

## Overview
This document tracks insights from external research on GUI automation reliability and their implementation status in the DesktopOps Agent.

## Key Research Findings & Our Response

### 1. Visual Delta Zero False Negatives ✅ IMPLEMENTED
**Research Finding:**
- Visual deltas can be zero despite real pointer movement when clicking uniform backgrounds
- GUI frames may redraw without visible change
- Mitigations: jitter + retry, larger regions, post-action delays, SSIM/perceptual hashing

**Our Implementation:**
- ✅ Configurable retry logic with jitter in `config.yaml` (`verify.retry.enabled`, `max_retries`, `jitter_px`)
- ✅ Jitter strategy: small pointer movement (±3px), recapture, recompute delta
- ✅ Region expansion strategy with `enlarge_factor` (default 1.5x)
- ✅ Configurable post-action delay (`verify.wait_ms`, default 180ms)
- ✅ Multi-modal verification: cursor telemetry (before/after) as secondary signal
- ✅ Retry metadata tracked in `meta.verify.retry` with attempts and reason

**Evidence:**
```yaml
# config.yaml
verify:
  retry:
    enabled: true
    max_retries: 1
    jitter_px: 3
    enlarge_factor: 1.5
```

**Next Steps:**
- 🔲 Add SSIM comparison as alternative to mean absolute difference (more robust to minor variations)
- 🔲 Implement adaptive ROI selection based on action type

---

### 2. Screen Capture Optimization ✅ VALIDATED
**Research Finding:**
- mss offers fast, pure Python capture
- Multi-monitor: be mindful of coordinate spaces and DPI scaling
- PNG for verification regions (lossless) vs JPEG for speed

**Our Implementation:**
- ✅ Using `mss` via `tools/screen.py` for fast region capture
- ✅ All verification crops saved as PNG (lossless): `verify_step_{idx:04d}_before.png`
- ✅ Main screenshots use JPEG with configurable quality (`screenshot.quality: 75`)
- ✅ Coordinate space handling: absolute screen coords with clamping to actual screen bounds

**Evidence:**
```python
# loop.py lines 463-464
before_img.save(before_path)  # Path ends in .png → Pillow uses PNG
after_img.save(after_path)
```

**Next Steps:**
- 🔲 Document DPI scaling considerations for multi-monitor setups
- 🔲 Add monitor selection utilities for explicit target monitor specification

---

### 3. Interaction Library Performance ✅ ALREADY HYBRID
**Research Finding:**
- pyautogui: cross-platform but slower for high-frequency ops; DPI scaling issues
- win32api/win32gui: faster, more direct control, Windows-specific
- Recommendation: use native APIs for performance-critical paths, keep pyautogui as fallback

**Our Implementation:**
- ✅ Cursor position: prefer `win32api.GetCursorPos()`, fallback to `pyautogui.position()`
- ✅ Input actions: currently via pyautogui (works well for current use cases)
- ✅ Screen capture: using `mss` (not pyautogui's screenshot)

**Evidence:**
```python
# loop.py _cursor_pos() helper
try:
    import win32api
    x, y = win32api.GetCursorPos()
    return int(x), int(y)
except Exception:
    import pyautogui as _pg
    x, y = _pg.position()
    return int(x), int(y)
```

**Next Steps:**
- 🔲 Benchmark pyautogui vs win32 mouse_event for clicks; optimize if needed
- 🔲 Add DPI awareness API calls for coordinate translation

---

### 4. LLM JSON Structured Output ✅ HARDENED
**Research Finding:**
- LLMs wrap JSON in fences, add prefatory text, produce slightly malformed JSON
- Mitigation: response_format schema mode (OpenAI), robust cleaning, first-object extraction

**Our Implementation:**
- ✅ Robust pre-cleaning in `agent/parser.py`: `clean_model_text` strips wrappers, BOM, fences
- ✅ First-JSON-object extraction with fallback parsing
- ✅ OpenAI uses `response_format={"type": "json_object"}`
- ✅ Schema validation: reject DONE, enforce NONE/done:true, gate CLICK_TEXT when OCR disabled
- ✅ Detailed parse error logging in `debug.jsonl` with raw/cleaned text

**Evidence:**
```python
# parser.py clean_model_text()
text = re.sub(r"<\|begin_of_box\|>.*?<\|end_of_box\|>", "", text, flags=re.DOTALL)
text = re.sub(r"```(?:json)?\s*", "", text)
# ... (full wrapper stripping)
```

**Next Steps:**
- 🔲 Add retry-on-parse-fail: send error back to model, request corrected JSON
- 🔲 Experiment with few-shot prompting examples in provider adapters

---

### 5. Coordinate System Handling ✅ COMPREHENSIVE
**Research Finding:**
- Models propose normalized coords (0-1 or 0-1000); automation needs absolute pixels
- Support multiple representations: x,y | [x,y] | {x,y} | bbox center
- Explicitly instruct for absolute coords; enforce at parse time

**Our Implementation:**
- ✅ Tolerant coordinate extraction: `_extract_xy` supports x,y, cx,cy, coordinates/point/position/center/target/location as list or dict
- ✅ Bbox center conversion for [x1,y1,x2,y2] inputs
- ✅ Normalized coord mapping: `normalized_1000` (0-1000) and `unit_normalized` (0.0-1.0) → absolute pixels
- ✅ Prompt augmentation: "Return ABSOLUTE screen coordinates in this {W}x{H} space"
- ✅ Parse-time validation: clamp to screen bounds, record `meta.clamped` and `meta.coord_source`
- ✅ Detailed error messages when coords missing: lists accepted shapes and actual arg keys

**Evidence:**
```python
# loop.py _extract_xy() - tolerates multiple shapes
for k in ("coordinates", "point", "position", "center", "target", "location"):
    v = args_ref.get(k)
    if isinstance(v, (list, tuple)) and len(v) == 2:
        return v[0], v[1], k
```

**Next Steps:**
- 🔲 Add explicit validation test cases for each coord representation
- 🔲 Heuristic improvement: detect image-space coords (>screen_width) and warn

---

## Summary of Research Value

### What We Already Had Right ✅
1. **Retry logic with jitter** — implemented and configurable
2. **PNG for verification crops** — lossless format prevents compression artifacts
3. **Hybrid pyautogui/win32 approach** — uses native APIs where it matters
4. **Robust JSON parsing** — comprehensive cleaning and validation
5. **Flexible coordinate extraction** — handles normalized and absolute, multiple representations
6. **Cursor telemetry** — secondary verification signal

### What the Research Validates 🎯
- Our zero-delta mitigation strategy is industry best practice
- PNG vs JPEG choice for verification is correct
- Coordinate system flexibility is essential for LLM-based agents
- Multi-modal verification (visual + cursor) reduces false negatives

### New Opportunities 🚀
1. **SSIM comparison** — more robust than mean absolute difference for complex UIs
2. **DPI awareness docs** — help users with multi-monitor/high-DPI setups
3. **Adaptive ROI** — adjust verification regions based on action type
4. **Performance profiling** — benchmark pyautogui vs win32 for optimization opportunities

## Conclusion

The research document is **highly valuable** because it:
1. **Validates** our existing architecture decisions (retry, PNG, hybrid approach)
2. **Explains the why** behind issues we've seen (zero deltas on neutral surfaces)
3. **Provides actionable next steps** (SSIM, DPI docs, adaptive ROI)
4. **Confirms industry alignment** — we're implementing recognized best practices

**Bottom line:** We're already implementing most of the recommended strategies. The research gives us confidence we're on the right track and identifies specific enhancements (SSIM, DPI docs) to further harden the system.
