# ⚠️ CRITICAL CONFIGURATION REQUIREMENTS

## Zhipu (Z.ai) API Configuration

### DO NOT MODIFY THESE SETTINGS

The Zhipu integration requires **EXACT** configuration values. Changing these will break the API connection.

#### Model Name
```yaml
model: glm-4.5v
```
- ✅ **CORRECT**: `glm-4.5v` (the vision model)
- ❌ **WRONG**: `glm-4.6` (text-only model, no vision)
- ❌ **WRONG**: `glm-4.5` (doesn't exist)
- ❌ **WRONG**: `glm-4v-plus` (wrong naming convention)

#### Base URL
```python
base_url = "https://api.z.ai/api/coding/paas/v4"
```
- ✅ **CORRECT**: `https://api.z.ai/api/coding/paas/v4`
- ❌ **WRONG**: `https://api.z.ai/api/paas/v4` (missing `/coding/`)
- ❌ **WRONG**: Any other variation

**The `/coding/` path segment is REQUIRED** - this is a special endpoint that provides access to the vision API. The standard `/api/paas/v4` endpoint will fail with authentication or format errors.

### Where These Settings Live

1. **agent/model.py** - `ZhipuAdapter.__init__()` line ~100
   ```python
   base_url = os.environ.get("ZHIPU_BASE_URL", "https://api.z.ai/api/coding/paas/v4")
   ```

2. **config.yaml** - Model configuration section
   ```yaml
   provider: zhipu
   model: glm-4.5v
   ```

3. **.env** - API key (base URL should NOT be set here)
   ```bash
   ZHIPU_API_KEY=your_key_here
   # DO NOT SET: ZHIPU_BASE_URL
   ```

### Symptoms of Incorrect Configuration

- **Wrong base URL**: `Error code: 401` (authentication error) or `Error code: 400` (format error)
- **Wrong model name**: `Error code: 400` with message about invalid parameters
- **Missing vision support**: Model returns text responses but can't see screenshots

### Testing the Configuration

Run this test to verify Zhipu vision is working:
```bash
python test_zhipu_vision.py
```

Expected output:
```
Testing Zhipu vision support with glm-4.5v...
SUCCESS! Vision works!
Response: {...}
```

If you see errors, **revert to the documented configuration above**.

## Why This Matters

The DesktopOps Agent requires vision capabilities to see screenshots and make decisions about where to click/type. Using the wrong configuration will result in:
- Blind operation (model can't see the screen)
- Authentication failures
- API errors that appear to be "out of credits" but are actually configuration issues

**When in doubt, do NOT modify the Zhipu configuration.**
