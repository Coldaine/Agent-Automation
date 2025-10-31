#!/usr/bin/env python
"""Test if Zhipu API is actually working."""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Test Zhipu API connection
api_key = os.environ.get("ZHIPU_API_KEY")
print(f"API Key found: {api_key[:20]}..." if api_key else "NO API KEY!")

base_url = os.environ.get("ZHIPU_BASE_URL", "https://api.z.ai/api/coding/paas/v4")
print(f"Base URL: {base_url}")

try:
    client = OpenAI(api_key=api_key, base_url=base_url)
    print("\nCalling Zhipu API...")
    
    resp = client.chat.completions.create(
        model="glm-4.6",
        temperature=0.2,
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Reply with JSON only."},
            {"role": "user", "content": "Say hello in JSON format with a 'message' key."}
        ],
        max_tokens=100,
        timeout=30,
    )
    
    print(f"SUCCESS! Response: {resp.choices[0].message.content}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
