#!/bin/bash

# Test script for SamplePDF.pdf
# This script tests the complete flow: upload -> ingest -> chat with RAG

FILE_ID="fc952142-4b8a-401f-80f1-ddf5c11e90af"
BASE_URL="http://localhost:8000"
BUCKET="swe-test-godwin-j-uploads"

echo "=========================================="
echo "Testing SamplePDF.pdf with RAG System"
echo "=========================================="
echo ""

echo "=== 1. Check File Status ==="
curl -s -X GET "$BASE_URL/files/$FILE_ID" | python3 -m json.tool | grep -E "(file_id|ingestion_status)"
echo ""

echo "=== 2. Test Direct Retrieval ==="
curl -s -X POST "$BASE_URL/retrieve" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"What is Minecraft?\", \"file_ids\": [\"$FILE_ID\"], \"top_k\": 3}" \
  | python3 -m json.tool | head -20
echo ""

echo "=== 3. Test Chat with RAG Mode ==="
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What is Minecraft and what are MCPACK files?\", \"file_id\": \"$FILE_ID\"}" \
  | python3 -m json.tool | head -20
echo ""

echo "=== 4. Test Follow-up Question ==="
CONV_ID=$(curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What are the game modes?\", \"file_id\": \"$FILE_ID\"}" \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['conversation_id'])")

echo "Conversation ID: $CONV_ID"
echo ""

curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Tell me more about Survival Mode\", \"conversation_id\": \"$CONV_ID\", \"file_id\": \"$FILE_ID\"}" \
  | python3 -m json.tool | head -20
echo ""

echo "=== 5. View Conversation History ==="
curl -s -X GET "$BASE_URL/chats/$CONV_ID" | python3 -m json.tool | head -30
echo ""

echo "=========================================="
echo "Testing Complete!"
echo "=========================================="

