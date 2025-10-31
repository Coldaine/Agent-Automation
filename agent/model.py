from __future__ import annotations
# Environment: managed with 'uv' (https://github.com/astral-sh/uv). See README for setup.
import os
from typing import Any, Dict, List, Optional
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

class BaseModelAdapter:
    def step(self, instruction: str, last_observation: str, recent_steps: List[Dict[str, Any]],
             image_b64_jpeg: Optional[str]) -> Dict[str, Any]:
        raise NotImplementedError



class OpenAIAdapter(BaseModelAdapter):
    def __init__(self, model: str, temperature: float, max_output_tokens: int):
        from openai import OpenAI
        base_url = os.environ.get("OPENAI_BASE_URL")
        self.client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=base_url if base_url else None
        )
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens

    def step(self, instruction: str, last_observation: str, recent_steps, image_b64_jpeg):
        system_prompt = (
            "You are DesktopOps: a careful, step-by-step desktop operator. "
            "Return ONLY a single JSON object with keys: plan, say, next_action, args, done. No prose or code fences. "
            "next_action must be one of: MOVE, CLICK, DOUBLE_CLICK, RIGHT_CLICK, TYPE, HOTKEY, SCROLL, DRAG, WAIT, NONE, CLICK_TEXT, UIA_INVOKE, UIA_SET_VALUE. "
            "If the task is complete, you MUST set {\"next_action\":\"NONE\",\"done\":true}. Do not use DONE. "
            "If OCR is not available, do not use CLICK_TEXT. "
            "Keep 'plan' concise (<=80 chars). Use absolute screen coordinates for pointer actions when needed."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": f"Instruction: {instruction}\nLast observation: {last_observation}\nRecent steps: {recent_steps[-6:] if recent_steps else []}\nRespond with required JSON only."}
            ]}
        ]
        if image_b64_jpeg:
            messages[1]["content"].append({"type": "image_url", "image_url": {"url": image_b64_jpeg}})

        schema = {
            "name": "desktop_step",
            "schema": {
                "type": "object",
                "properties": {
                    "plan": {"type": "string"},
                    "say": {"type": "string"},
                    "next_action": {"type": "string",
                        "enum": [
                            "MOVE","CLICK","DOUBLE_CLICK","RIGHT_CLICK","TYPE","HOTKEY",
                            "SCROLL","DRAG","WAIT","NONE",
                            "CLICK_TEXT","UIA_INVOKE","UIA_SET_VALUE"
                        ]},
                    "args": {"type": "object"},
                    "done": {"type": "boolean"}
                },
                "required": ["plan","next_action","args","done"],
                "additionalProperties": False
            }
        }
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=messages,
            response_format={"type": "json_schema", "json_schema": schema},
            max_tokens=self.max_output_tokens,
        )
        m = resp.choices[0].message
        return getattr(m, "parsed", None) or m.content

class AnthropicAdapter(BaseModelAdapter):
    def __init__(self, model: str, temperature: float, max_output_tokens: int):
        import anthropic
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens

    def step(self, instruction: str, last_observation: str, recent_steps, image_b64_jpeg):
        content = [{"type": "text", "text": (
            "Return ONLY a single JSON object with keys: plan,say,next_action,args,done. No prose. "
            "If done, set next_action:'NONE' and done:true. Do not use DONE. If OCR is not available, do not use CLICK_TEXT."
        )}]
        if image_b64_jpeg:
            import base64
            content.append({"type":"image", "source": {"type":"base64","media_type":"image/jpeg","data": image_b64_jpeg.split(",")[1]}})
        content.append({"type":"text","text": f"Instruction: {instruction}\nLast observation: {last_observation}\nRecent steps: {recent_steps[-6:] if recent_steps else []}"})
        msg = self.client.messages.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_output_tokens,
            system="You are DesktopOps, return strictly the specified JSON.",
            messages=[{"role":"user","content": content}],
        )
        return msg.content[0].text

class ZhipuAdapter(BaseModelAdapter):
    """Z.ai (Zhipu) adapter - use GLM-4.5V for vision support.
    
    CRITICAL: Base URL MUST be https://api.z.ai/api/coding/paas/v4
    DO NOT change this to /api/paas/v4 - the /coding/ path is required!
    """
    def __init__(self, model: str, temperature: float, max_output_tokens: int):
        from openai import OpenAI
        # DO NOT MODIFY: This specific endpoint is required for Z.ai API access
        base_url = os.environ.get("ZHIPU_BASE_URL", "https://api.z.ai/api/coding/paas/v4")
        self.client = OpenAI(
            api_key=os.environ.get("ZHIPU_API_KEY"),
            base_url=base_url,
        )
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        # Provider-level structured logging to current run dir if available
        self._provider_log_path = None
        self._call_seq = 0
        try:
            debug_dir = os.environ.get("DESKTOPOPS_DEBUG_DIR")
            if debug_dir:
                os.makedirs(debug_dir, exist_ok=True)
                self._provider_log_path = os.path.join(debug_dir, "provider_zhipu.jsonl")
        except Exception:
            self._provider_log_path = None

    def set_debug_dir(self, debug_dir: str):
        """Optional hook called by Stepper to set the current run directory."""
        try:
            if debug_dir:
                os.makedirs(debug_dir, exist_ok=True)
                self._provider_log_path = os.path.join(debug_dir, "provider_zhipu.jsonl")
        except Exception:
            pass

    def _log_provider(self, obj: Dict[str, Any]):
        try:
            if not self._provider_log_path:
                return
            import json as _json
            with open(self._provider_log_path, "a", encoding="utf-8") as fp:
                fp.write(_json.dumps(obj, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def step(self, instruction: str, last_observation: str, recent_steps, image_b64_jpeg):
        system_prompt = (
            "You are DesktopOps: a careful, step-by-step desktop operator. "
            "Return ONLY a valid JSON object (no markdown fences) with these exact keys: plan, say, next_action, args, done. "
            "next_action must be one of: MOVE, CLICK, DOUBLE_CLICK, RIGHT_CLICK, TYPE, HOTKEY, SCROLL, DRAG, WAIT, NONE, CLICK_TEXT, UIA_INVOKE, UIA_SET_VALUE. "
            "If the task is complete, you MUST set {\"next_action\":\"NONE\",\"done\":true}. Do not use DONE. "
            "args must be a JSON object. done must be boolean. Keep 'plan' concise (<=80 chars). "
            "IMPORTANT: Only use CLICK_TEXT if OCR is explicitly available in the user's message. If OCR is not available, never use CLICK_TEXT; instead, use CLICK with explicit absolute screen coordinates. "
            "When using pointer actions (MOVE/CLICK/DOUBLE_CLICK/RIGHT_CLICK/DRAG), you must return ABSOLUTE screen coordinates in the current screen space."
        )

        user_content = f"Instruction: {instruction}\nLast observation: {last_observation}\nRecent steps: {recent_steps[-6:] if recent_steps else []}\nRespond with the required JSON object."

        # Z.ai API - use GLM-4.5V for vision support
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        # GLM-4.5V supports multimodal vision
        if image_b64_jpeg:
            messages[1]["content"] = [
                {"type": "text", "text": user_content},
                {"type": "image_url", "image_url": {"url": image_b64_jpeg}}
            ]

        # Simple retry loop with bounded attempts + diagnostics
        import time as _time
        import traceback as _tb
        self._call_seq += 1
        for attempt in range(3):
            try:
                t0 = _time.perf_counter()
                # Input diagnostics (redacted)
                has_img = bool(image_b64_jpeg)
                img_len = len(image_b64_jpeg) if has_img else 0
                img_b64_bytes = 0
                try:
                    if has_img and "," in image_b64_jpeg:
                        img_b64_bytes = len(image_b64_jpeg.split(",", 1)[1])
                except Exception:
                    img_b64_bytes = 0
                self._log_provider({
                    "type": "provider_call",
                    "provider": "zhipu",
                    "seq": self._call_seq,
                    "attempt": attempt + 1,
                    "endpoint_base": getattr(self.client, "base_url", None) or os.environ.get("ZHIPU_BASE_URL"),
                    "model": self.model,
                    "temperature": self.temperature,
                    "max_tokens": self.max_output_tokens,
                    "has_image": has_img,
                    "image_b64_len": img_len,
                    "image_b64_payload_bytes": img_b64_bytes,
                    "instruction_preview": (instruction or "")[:300],
                    "recent_steps_count": len(recent_steps) if recent_steps else 0,
                })
                resp = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    messages=messages,
                    max_tokens=self.max_output_tokens,
                    timeout=30,
                )
                dt_ms = int((_time.perf_counter() - t0) * 1000)
                m = resp.choices[0].message
                # Extract optional usage and ids if present
                usage = None
                try:
                    usage = getattr(resp, "usage", None)
                    if usage and not isinstance(usage, dict):
                        usage = usage.model_dump() if hasattr(usage, "model_dump") else dict(usage)
                except Exception:
                    usage = None
                finish_reason = None
                try:
                    finish_reason = getattr(resp.choices[0], "finish_reason", None)
                except Exception:
                    finish_reason = None
                self._log_provider({
                    "type": "provider_resp",
                    "provider": "zhipu",
                    "seq": self._call_seq,
                    "attempt": attempt + 1,
                    "duration_ms": dt_ms,
                    "id": getattr(resp, "id", None),
                    "model": getattr(resp, "model", self.model),
                    "created": getattr(resp, "created", None),
                    "choices": len(getattr(resp, "choices", []) or []),
                    "finish_reason": finish_reason,
                    "usage": usage,
                    "message_preview": (m.content if isinstance(m.content, str) else str(m.content))[:800],
                })
                # If the model hit the length limit or appears truncated, reissue once with a compact JSON constraint
                try:
                    content_str = m.content if isinstance(m.content, str) else str(m.content)
                except Exception:
                    content_str = ""
                is_truncated = (finish_reason == "length") or (content_str and not content_str.strip().endswith("}"))
                if is_truncated and attempt == 0:
                    compact_system = (
                        system_prompt
                        + "\nReturn a COMPACT JSON object: no markdown, no prose, no newlines, no spaces after colons/commas. "
                        + "Only keys: plan,say,next_action,args,done. Keep plan<=40 chars. Use integers for coordinates."
                    )
                    compact_messages = [
                        {"role": "system", "content": compact_system},
                        {"role": "user", "content": user_content},
                    ]
                    if image_b64_jpeg:
                        compact_messages[1]["content"] = [
                            {"type": "text", "text": user_content},
                            {"type": "image_url", "image_url": {"url": image_b64_jpeg}},
                        ]
                    # Slightly increase max tokens but keep bounded
                    compact_max = min(int(self.max_output_tokens) + 512, 2048)
                    compact_temp = max(0.0, float(self.temperature) - 0.1)
                    t1 = _time.perf_counter()
                    resp2 = self.client.chat.completions.create(
                        model=self.model,
                        temperature=compact_temp,
                        messages=compact_messages,
                        max_tokens=compact_max,
                        timeout=30,
                    )
                    dt_ms2 = int((_time.perf_counter() - t1) * 1000)
                    m2 = resp2.choices[0].message
                    fr2 = None
                    try:
                        fr2 = getattr(resp2.choices[0], "finish_reason", None)
                    except Exception:
                        fr2 = None
                    self._log_provider({
                        "type": "provider_resp_compact_retry",
                        "provider": "zhipu",
                        "seq": self._call_seq,
                        "attempt": attempt + 1,
                        "duration_ms": dt_ms2,
                        "finish_reason": fr2,
                        "max_tokens": compact_max,
                        "temperature": compact_temp,
                        "message_preview": (m2.content if isinstance(m2.content, str) else str(m2.content))[:800],
                    })
                    return m2.content
                return content_str
            except Exception:  # network/timeouts/rate limits
                err_txt = _tb.format_exc(limit=2)
                self._log_provider({
                    "type": "provider_error",
                    "provider": "zhipu",
                    "seq": self._call_seq,
                    "attempt": attempt + 1,
                    "error": err_txt[:1200],
                })
                _time.sleep(0.5 * (attempt + 1))
        # Fallback payload if all attempts failed
        self._log_provider({
            "type": "provider_fallback",
            "provider": "zhipu",
            "seq": self._call_seq,
            "attempts": 3,
        })
        return (
            '{"plan":"handle provider error","say":"Temporary provider error; please retry.",'
            '"next_action":"NONE","args":{},"done":false}'
        )

class GeminiAdapter(BaseModelAdapter):
    def __init__(self, model: str, temperature: float, max_output_tokens: int):
        import google.generativeai as genai
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel(model_name=model)
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens

    def step(self, instruction: str, last_observation: str, recent_steps, image_b64_jpeg):
        parts = [
            "Return ONLY a single JSON object with keys: plan,say,next_action,args,done. No prose. If done, set next_action:'NONE' and done:true. Do not use DONE. If OCR is not available, do not use CLICK_TEXT.",
            f"Instruction: {instruction}",
            f"Last observation: {last_observation}",
            f"Recent steps: {recent_steps[-6:] if recent_steps else []}",
        ]
        imgs = []
        if image_b64_jpeg:
            import base64
            imgs = [{"mime_type":"image/jpeg","data": base64.b64decode(image_b64_jpeg.split(",")[1])}]
        resp = self.model.generate_content(parts + imgs, generation_config={"temperature": self.temperature, "max_output_tokens": self.max_output_tokens})
        return resp.text

class DummyAdapter(BaseModelAdapter):
    """A minimal adapter for offline/dry-run testing without provider keys.
    Returns deterministic actions to exercise the loop without network calls.
    """
    def __init__(self):
        pass

    def step(self, instruction: str, last_observation: str, recent_steps, image_b64_jpeg):
        # Simple heuristic: if the instruction mentions 'type', return TYPE
        inst = (instruction or "").lower()
        if "type" in inst:
            return {
                "plan": "type the requested text",
                "say": "Typing as requested.",
                "next_action": "TYPE",
                "args": {"text": instruction.replace("type", "").strip() or "hello world"},
                "done": True,
            }
        # Otherwise, return a CLICK at a fixed absolute coordinate for testing
        return {
            "plan": "click a known absolute coordinate",
            "say": "Clicking test point.",
            "next_action": "CLICK",
            "args": {"x": 1200, "y": 800, "button": "left"},
            "done": True,
        }

def get_adapter(provider: str, model: str, temperature: float, max_output_tokens: int) -> BaseModelAdapter:
    if provider == "dummy":
        return DummyAdapter()
    if provider == "openai":
        return OpenAIAdapter(model, temperature, max_output_tokens)
    if provider == "anthropic":
        return AnthropicAdapter(model, temperature, max_output_tokens)
    if provider == "gemini":
        return GeminiAdapter(model, temperature, max_output_tokens)
    if provider == "zhipu":
        return ZhipuAdapter(model, temperature, max_output_tokens)
    raise ValueError(f"Unknown provider: {provider}")
