#!/usr/bin/env python3
"""
Test script to find which OpenAI models are available with the current API key.
"""
import os
from openai import OpenAI
from config import settings

if not settings.OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY not set in .env")
    exit(1)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# List of models to try
models_to_test = [
    "gpt-4o-mini",
    "gpt-4.1-mini",
    "gpt-4o",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
]

print("Testing available OpenAI models...")
print("=" * 60)

available_models = []
for model in models_to_test:
    try:
        # Try a simple text completion
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5
        )
        available_models.append(model)
        print(f"✅ {model} - Available")
    except Exception as e:
        error_msg = str(e)
        if "model_not_found" in error_msg or "does not have access" in error_msg:
            print(f"❌ {model} - Not available")
        else:
            print(f"⚠️  {model} - Error: {error_msg[:50]}")

print("=" * 60)
print(f"\n✅ Available models: {', '.join(available_models) if available_models else 'None'}")

if available_models:
    print(f"\n💡 Recommended: Use '{available_models[0]}' in your .env file")
    print(f"   Set: OPENAI_MODEL={available_models[0]}")

