"""
Direct test of Upstash Vector API to verify format.
"""
import requests
import json
from config import settings

# Test with minimal payload
test_payload = {
    "vectors": [
        {
            "id": "test-1",
            "vector": [0.1] * 1536,  # 1536 dimensions for text-embedding-3-small
            "metadata": {
                "file_id": "test-file",
                "chunk_index": 0,
                "chunk_text": "test"
            }
        }
    ]
}

url = f"{settings.UPSTASH_VECTOR_REST_URL.rstrip('/')}/upsert"
params = {"namespace": settings.UPSTASH_VECTOR_NAMESPACE}
headers = {
    "Authorization": f"Bearer {settings.UPSTASH_VECTOR_REST_TOKEN}",
    "Content-Type": "application/json",
}

print(f"Testing Upstash Vector API:")
print(f"URL: {url}")
print(f"Namespace: {params['namespace']}")
print(f"Payload size: {len(json.dumps(test_payload))} bytes")
print(f"Payload structure: {json.dumps(test_payload, indent=2)[:500]}")

try:
    response = requests.post(url, json=test_payload, headers=headers, params=params, timeout=30)
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    if response.status_code == 200:
        print("✅ SUCCESS! Upstash Vector API format is correct.")
    else:
        print(f"❌ FAILED: {response.text}")
except Exception as e:
    print(f"❌ ERROR: {e}")

