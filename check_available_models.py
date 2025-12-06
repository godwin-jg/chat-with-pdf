#!/usr/bin/env python3
"""
Check which OpenAI models are available with the current API key.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from openai import OpenAI

if not settings.OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY not set in .env")
    sys.exit(1)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Comprehensive list of models to test
models_to_test = [
    # GPT-4o series
    "gpt-4o",
    "gpt-4o-2024-08-06",
    "gpt-4o-2024-05-13",
    "gpt-4o-mini",
    "gpt-4o-mini-2024-07-18",
    # GPT-4 Turbo series
    "gpt-4-turbo",
    "gpt-4-turbo-preview",
    "gpt-4-turbo-2024-04-09",
    "gpt-4-0125-preview",
    "gpt-4-1106-preview",
    # GPT-4 base
    "gpt-4",
    "gpt-4-0613",
    "gpt-4-32k",
    # GPT-3.5 series
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-16k",
    "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo-0125",
]

print("=" * 70)
print("Testing OpenAI Models Availability")
print("=" * 70)
print(f"API Key: {settings.OPENAI_API_KEY[:10]}...{settings.OPENAI_API_KEY[-4:]}")
print()

available_models = []
unavailable_models = []

for model in models_to_test:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        available_models.append(model)
        print(f"✅ {model:35} - AVAILABLE")
    except Exception as e:
        error_msg = str(e)
        if "model_not_found" in error_msg or "does not have access" in error_msg:
            unavailable_models.append(model)
            print(f"❌ {model:35} - Not available")
        else:
            # Other error might mean model exists but has other issues
            print(f"⚠️  {model:35} - Error: {error_msg[:40]}")

print()
print("=" * 70)
if available_models:
    print(f"✅ FOUND {len(available_models)} AVAILABLE MODEL(S):")
    for model in available_models:
        print(f"   - {model}")
    print()
    print("💡 Update your .env file:")
    print(f"   OPENAI_MODEL={available_models[0]}")
    
    # Check which ones support vision/PDFs
    vision_models = [m for m in available_models if "gpt-4o" in m or "gpt-4-turbo" in m or "gpt-4" in m]
    if vision_models:
        print()
        print("📄 Models that likely support PDFs (vision API):")
        for model in vision_models:
            print(f"   - {model}")
else:
    print("❌ NO MODELS AVAILABLE")
    print()
    print("This could mean:")
    print("1. API key is invalid")
    print("2. API key has no model access")
    print("3. Network/connection issue")
    print()
    print("Please check:")
    print("- API key is correct in .env")
    print("- You have internet connection")
    print("- Contact API provider for model access")

print("=" * 70)

