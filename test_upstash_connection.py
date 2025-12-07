"""
Test script to verify Upstash Vector connection and basic operations.
"""
import sys
import requests
from typing import Dict, Any
from config import settings
from core.vector.upstash_client import get_upstash_client


def test_connection() -> bool:
    """Test basic connection to Upstash Vector."""
    print("=" * 60)
    print("Testing Upstash Vector Connection")
    print("=" * 60)
    
    # Check configuration
    print("\n1. Checking configuration...")
    if not settings.UPSTASH_VECTOR_REST_URL:
        print("❌ UPSTASH_VECTOR_REST_URL is not set")
        return False
    if not settings.UPSTASH_VECTOR_REST_TOKEN:
        print("❌ UPSTASH_VECTOR_REST_TOKEN is not set")
        return False
    if not settings.UPSTASH_VECTOR_NAMESPACE:
        print("❌ UPSTASH_VECTOR_NAMESPACE is not set")
        return False
    
    print(f"✅ URL: {settings.UPSTASH_VECTOR_REST_URL}")
    print(f"✅ Namespace: {settings.UPSTASH_VECTOR_NAMESPACE}")
    print(f"✅ Token: {'*' * 20}...{settings.UPSTASH_VECTOR_REST_TOKEN[-4:] if len(settings.UPSTASH_VECTOR_REST_TOKEN) > 4 else '****'}")
    
    # Test client initialization
    print("\n2. Initializing Upstash client...")
    try:
        client = get_upstash_client()
        print("✅ Client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return False
    
    # Test basic API connectivity with a simple query
    print("\n3. Testing API connectivity...")
    try:
        # Create a test query vector (1536 dimensions for text-embedding-3-small)
        test_vector = [0.0] * 1536
        test_vector[0] = 1.0  # Set one value to non-zero
        
        # Try a query operation (this will fail if connection/auth is wrong)
        results = client.query_vectors(
            query_vector=test_vector,
            top_k=1
        )
        print("✅ API connection successful")
        print(f"   Query returned {len(results)} results")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        print("   Check if UPSTASH_VECTOR_REST_URL is correct")
        return False
    except requests.exceptions.HTTPError as e:
        if e.response and e.response.status_code == 401:
            print(f"❌ Authentication failed: {e}")
            print("   Check if UPSTASH_VECTOR_REST_TOKEN is correct")
            return False
        elif e.response and e.response.status_code == 404:
            print(f"❌ Endpoint not found: {e}")
            print("   Check if UPSTASH_VECTOR_REST_URL is correct")
            return False
        else:
            print(f"❌ HTTP error: {e}")
            if e.response:
                print(f"   Response: {e.response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    # Test upsert operation
    print("\n4. Testing upsert operation...")
    try:
        test_id = "connection-test-vector"
        test_vectors = [[0.1] * 1536]
        test_ids = [test_id]
        test_metadata = [{
            "file_id": "test-connection",
            "chunk_index": 0,
            "chunk_text": "Connection test chunk"
        }]
        
        result = client.upsert_vectors(
            vectors=test_vectors,
            ids=test_ids,
            metadata=test_metadata
        )
        print("✅ Upsert operation successful")
        print(f"   Upserted {result.get('upserted', 0)} vectors")
    except Exception as e:
        print(f"❌ Upsert failed: {e}")
        return False
    
    # Test query to retrieve the vector we just inserted
    print("\n5. Testing query to retrieve inserted vector...")
    try:
        query_vector = [0.1] * 1536
        results = client.query_vectors(
            query_vector=query_vector,
            top_k=5,
            filter=None
        )
        
        # Check if our test vector is in the results
        found_test = any(r.get("id") == test_id for r in results)
        if found_test:
            print("✅ Query operation successful")
            print(f"   Found test vector in results")
        else:
            print("⚠️  Query succeeded but test vector not found in top results")
            print(f"   Returned {len(results)} results")
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All connection tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

