#!/usr/bin/env python
"""Test if Zhipu API supports vision/images."""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Use actual image URL (from Z.ai docs example)
image_url = "https://cloudcovert-1305175928.cos.ap-guangzhou.myqcloud.com/%E5%9B%BE%E7%89%87grounding.PNG"

api_key = os.environ.get("ZHIPU_API_KEY")
# CRITICAL: Must use /api/coding/paas/v4 endpoint (DO NOT change to /api/paas/v4)
base_url = os.environ.get("ZHIPU_BASE_URL", "https://api.z.ai/api/coding/paas/v4")

try:
    client = OpenAI(api_key=api_key, base_url=base_url)
    print("Testing Zhipu vision support with glm-4.5v...")
    
    resp = client.chat.completions.create(
        model="glm-4.5v",
        temperature=0.2,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": [
                 {"type": "image_url", "image_url": {"url": image_url}},
                 {"type": "text", "text": "What do you see in this image? Reply in JSON with a 'description' key."}
            ]}
        ],
        max_tokens=100,
        timeout=30,
    )
    
    print(f"SUCCESS! Vision works!")
    print(f"Response: {resp.choices[0].message.content}")
    
except Exception as e:
    print(f"VISION NOT SUPPORTED: {e}")
    print("\nZhipu may not support multimodal yet. Need to use OpenAI or another provider for vision.")
