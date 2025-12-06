#!/usr/bin/env python3
"""
Test script for all chat endpoints using a specific file_id.
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000"
FILE_ID = "500107f2-4445-4be2-9a5e-aca7144780d2"

def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_response(response, label="Response"):
    """Print formatted response."""
    print(f"\n{label}:")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(f"Status: {response.status_code}")
        print(f"Text: {response.text}")

def test_chat_endpoints():
    """Test all chat endpoints."""
    
    print_section("Testing Chat Endpoints")
    print(f"Using file_id: {FILE_ID}")
    print(f"Base URL: {BASE_URL}")
    
    # Test 1: POST /chat - Start new conversation with file
    print_section("1. POST /chat - Start new conversation with file_id")
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={
                "message": "What is this document about?",
                "file_id": FILE_ID
            },
            headers={"Content-Type": "application/json"}
        )
        print(f"Status Code: {response.status_code}")
        print_response(response)
        
        if response.status_code == 200:
            data = response.json()
            conversation_id = data.get("conversation_id")
            print(f"\n✅ Conversation created: {conversation_id}")
            
            # Test 2: POST /chat - Continue conversation
            print_section("2. POST /chat - Continue conversation")
            response2 = requests.post(
                f"{BASE_URL}/chat",
                json={
                    "message": "Tell me more about the main topics",
                    "conversation_id": conversation_id
                },
                headers={"Content-Type": "application/json"}
            )
            print(f"Status Code: {response2.status_code}")
            print_response(response2, "Continue Conversation Response")
            
            # Test 3: GET /chats - List all conversations
            print_section("3. GET /chats - List all conversations")
            response3 = requests.get(f"{BASE_URL}/chats?limit=20&offset=0")
            print(f"Status Code: {response3.status_code}")
            print_response(response3, "Conversations List")
            
            # Test 4: GET /chats/{conversation_id} - Get conversation details
            print_section("4. GET /chats/{conversation_id} - Get conversation details")
            response4 = requests.get(f"{BASE_URL}/chats/{conversation_id}")
            print(f"Status Code: {response4.status_code}")
            print_response(response4, "Conversation Details")
            
            if response4.status_code == 200:
                conv_data = response4.json()
                print(f"\n✅ Conversation has {len(conv_data.get('messages', []))} messages")
                for i, msg in enumerate(conv_data.get('messages', []), 1):
                    print(f"  Message {i}: {msg.get('role')} - {msg.get('content')[:50]}...")
                    if msg.get('file_id'):
                        print(f"    File ID: {msg.get('file_id')}")
                    if msg.get('retrieval_mode'):
                        print(f"    Retrieval Mode: {msg.get('retrieval_mode')}")
        else:
            print(f"\n❌ Failed to create conversation. Status: {response.status_code}")
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to server.")
        print("   Make sure the server is running: uvicorn main:app --reload")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_chat_endpoints()
    print_section("Testing Complete")

