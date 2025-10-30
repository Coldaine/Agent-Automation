from __future__ import annotations
import os, json
from typing import Any, Dict, List, Optional

class BaseModelAdapter:
    def step(self, instruction: str, last_observation: str, recent_steps: List[Dict[str, Any]],
             image_b64_jpeg: Optional[str]) -> Dict[str, Any]:
        raise NotImplementedError

class DummyAdapter(BaseModelAdapter):
    def step(self, instruction: str, last_observation: str, recent_steps, image_b64_jpeg):
        if not recent_steps:
            return {
                "plan": "type the instruction as text",
                "say": "Focusing text field and typing your instruction.",
                "next_action": "TYPE",
                "args": {"text": instruction[:80]},
                "done": False
            }
        else:
            return {
                "plan": "finish",
                "say": "Done.",
                "next_action": "NONE",
                "args": {},
                "done": True
            }

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
            "Return ONLY a JSON object with keys: plan, say, next_action, args, done. "
            "next_action ∈ {MOVE, CLICK, DOUBLE_CLICK, RIGHT_CLICK, TYPE, HOTKEY, SCROLL, DRAG, WAIT, NONE}. "
            "Keep 'plan' concise (<=80 chars). Use absolute screen coordinates for pointer actions when needed. "
            "If you need the user, set next_action:'NONE' and done:false with a clear 'say'."
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
                        "enum": ["MOVE","CLICK","DOUBLE_CLICK","RIGHT_CLICK","TYPE","HOTKEY","SCROLL","DRAG","WAIT","NONE"]},
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
        content = [{"type": "text", "text": "Return ONLY JSON with keys: plan,say,next_action,args,done."}]
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
    """Z.ai (Zhipu) adapter using OpenAI-compatible coding plan endpoint."""
    def __init__(self, model: str, temperature: float, max_output_tokens: int):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=os.environ.get("ZHIPU_API_KEY"),
            base_url="https://api.z.ai/api/coding/paas/v4"
        )
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens

    def step(self, instruction: str, last_observation: str, recent_steps, image_b64_jpeg):
        system_prompt = (
            "You are DesktopOps: a careful, step-by-step desktop operator. "
            "Return ONLY a JSON object with keys: plan, say, next_action, args, done. "
            "next_action ∈ {MOVE, CLICK, DOUBLE_CLICK, RIGHT_CLICK, TYPE, HOTKEY, SCROLL, DRAG, WAIT, NONE}. "
            "Keep 'plan' concise (<=80 chars). Use absolute screen coordinates for pointer actions when needed. "
            "If you need the user, set next_action:'NONE' and done:false with a clear 'say'."
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
                        "enum": ["MOVE","CLICK","DOUBLE_CLICK","RIGHT_CLICK","TYPE","HOTKEY","SCROLL","DRAG","WAIT","NONE"]},
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

class GeminiAdapter(BaseModelAdapter):
    def __init__(self, model: str, temperature: float, max_output_tokens: int):
        import google.generativeai as genai
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel(model_name=model)
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens

    def step(self, instruction: str, last_observation: str, recent_steps, image_b64_jpeg):
        parts = [
            "Return ONLY JSON with keys: plan,say,next_action,args,done.",
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

def get_adapter(provider: str, model: str, temperature: float, max_output_tokens: int) -> BaseModelAdapter:
    if provider == "openai": return OpenAIAdapter(model, temperature, max_output_tokens)
    if provider == "anthropic": return AnthropicAdapter(model, temperature, max_output_tokens)
    if provider == "gemini": return GeminiAdapter(model, temperature, max_output_tokens)
    if provider == "zhipu": return ZhipuAdapter(model, temperature, max_output_tokens)
    if provider == "dummy": return DummyAdapter()
    raise ValueError(f"Unknown provider: {provider}")
