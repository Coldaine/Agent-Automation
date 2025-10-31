# Coordinate Scaling Analysis Request

## Context
I'm building a desktop automation agent that captures screenshots, sends them to a vision model (Zhipu GLM-4.5V), and executes mouse clicks based on coordinates returned by the model.

## The Setup
- **Actual screen resolution**: 2400×1600 pixels
- **Screenshot sent to model**: Downscaled to 1280×853 pixels (maintains aspect ratio)
- **Model provider**: Zhipu AI (GLM-4.5V vision model)
- **System prompt**: "You are DesktopOps: a careful, step-by-step desktop operator. Use absolute screen coordinates for pointer actions when needed."

## Recent Test Results

### Test 1: Calibration Test (Direct Click API)
- Created a fullscreen 2400×1600 calibration pattern with 9 marked points
- Used Python's `InputController` to click coordinates directly
- **Result**: 9/9 clicks with 0.0px error - perfect accuracy
- **Conclusion**: The click API (`win32api.SetCursorPos` and `pyautogui.click`) works perfectly

### Test 2: Agent Mouse Movement to Center
- Command: "move mouse to center of screen"
- Screenshot sent to model: 1280×853 pixels
- **Model returned**: `{"x": 1200, "y": 800}`
- **Expected if model uses screenshot coords**: `{"x": 640, "y": 426}` (center of 1280×853)
- **Expected if model uses screen coords**: `{"x": 1200, "y": 800}` (center of 2400×1600) ✓
- **Result**: Mouse moved correctly to screen center
- **Observation**: Model returned coordinates matching ACTUAL SCREEN (2400×1600), not the downscaled screenshot (1280×853)

### Test 3: Previous Failing Run (Gmail Navigation)
- Screenshots: 1280×853 pixels
- Model attempted to click Chrome icon in taskbar
- Model returned: `{"x": 244, "y": 958}` multiple times
- **Issue**: Y=958 exceeds the screenshot height of 853 pixels
- **Observation**: Agent kept clicking wrong location, got stuck in loop

## Current Implementation
```python
# In agent/loop.py - Coordinate scaling logic
actual_width = 2400  # Full screen width
actual_height = 1600  # Full screen height
pil_img.width = 1280  # Screenshot width sent to model
pil_img.height = 853  # Screenshot height sent to model

scale_x = actual_width / pil_img.width   # 2400/1280 = 1.875
scale_y = actual_height / pil_img.height  # 1600/853 = 1.876

def scale_coord(x, y):
    if x is None or y is None:
        return x, y
    return int(x * scale_x), int(y * scale_y)

# Before clicking, we scale model coordinates:
x_raw, y_raw = args.get("x"), args.get("y")  # From model
x_scaled, y_scaled = scale_coord(x_raw, y_raw)  # Apply scaling
self.input.click(x_scaled, y_scaled)  # Execute click
```

## The Question

**Which of these hypotheses is correct?**

### Hypothesis A: Model Returns Screenshot Coordinates (Needs Scaling)
- Model analyzes 1280×853 image and returns coordinates relative to that image
- Coordinates must be scaled up by 1.875x before clicking
- Test 2 success was luck/coincidence
- Test 3 failure (y=958 > 853) suggests model is confused or hallucinating

### Hypothesis B: Model Returns Screen Coordinates (No Scaling Needed)
- Model somehow infers or is aware of actual screen resolution (2400×1600)
- Model returns coordinates in absolute screen space
- Current scaling logic is WRONG - it's scaling already-correct coordinates
- Test 2 success proves this (1200,800 = exact center of 2400×1600)
- Test 3 failure because coordinates were being scaled incorrectly in that older version

### Hypothesis C: Model Behavior is Inconsistent
- Sometimes returns screenshot coords, sometimes screen coords
- Need detection logic to determine which system model is using
- Explains why some clicks work and others don't

## Request

Please analyze this situation and provide:

1. **Your assessment**: Which hypothesis (A, B, C, or other) is most likely correct?

2. **Evidence analysis**: 
   - How do you explain the Test 2 result (model returned 1200,800)?
   - How do you explain the Test 3 result (model returned 244,958 when image is 1280×853)?

3. **Recommendation**: Should I:
   - Keep coordinate scaling (Hypothesis A)
   - Remove coordinate scaling (Hypothesis B)
   - Add detection/fallback logic (Hypothesis C)
   - Something else?

4. **Testing strategy**: What test would definitively prove which coordinate system the model is using?

## Additional Context

- The system prompt mentions "absolute screen coordinates" but doesn't specify the screen resolution
- No screen resolution is sent to the model in the messages
- The image is base64-encoded JPEG with no EXIF metadata containing resolution
- Model has access to the image dimensions (1280×853) from the image itself
- Vision models typically analyze images in their native resolution

Please provide your analysis and reasoning.
