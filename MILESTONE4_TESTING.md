# Milestone 4 Testing Guide
## Dynamic Mode Switching with Tool Calling

This guide shows how to test the hybrid system that switches between **Inline Mode** (Base64 PDF) and **RAG Mode** (Vector Search with Tool Calling) based on file ingestion status.

## Prerequisites

1. **Server Running**: Make sure your FastAPI server is running on `http://localhost:8000`
2. **File Uploaded**: You need a file with `file_id` that has been ingested
3. **File Status**: Check if your file has `ingestion_status="completed"` (for RAG mode) or `"uploaded"` (for inline mode)

## Test File Status

First, check your file's ingestion status:

```bash
curl -X GET "http://localhost:8000/files/500107f2-4445-4be2-9a5e-aca7144780d2" | python3 -m json.tool
```

Look for `"ingestion_status": "completed"` or `"uploaded"`.

## Test 1: RAG Mode (File Status = "completed")

When a file has `ingestion_status="completed"`, the system should:
1. Enable the `semantic_search` tool
2. LLM calls the tool to search for relevant chunks
3. System retrieves chunks from Upstash Vector
4. LLM generates response using retrieved context
5. Response includes `retrieval_mode="rag"` and `retrieved_chunks`

### Test Command:

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What technologies and skills are mentioned in this document?",
    "file_id": "500107f2-4445-4be2-9a5e-aca7144780d2"
  }' | python3 -m json.tool
```

### Expected Response:

```json
{
  "conversation_id": "...",
  "response": "... (response using retrieved chunks)",
  "retrieval_mode": "rag",
  "retrieved_chunks": [
    {
      "chunk_text": "...",
      "similarity_score": 0.85
    }
  ]
}
```

### What to Check:

✅ `retrieval_mode` should be `"rag"`  
✅ `retrieved_chunks` should contain chunks with similarity scores  
✅ Response should reference content from the document  
✅ Check server logs for: `"RAG mode enabled"` and `"LLM called X tool(s)"`

## Test 2: Inline Mode (File Status = "uploaded")

When a file has `ingestion_status="uploaded"` (not yet ingested), the system should:
1. Download PDF from S3
2. Convert PDF pages to images (Base64)
3. Send images to LLM via Vision API
4. Response includes `retrieval_mode="inline"` and empty `retrieved_chunks`

### Setup: Reset File Status (if needed)

If your file is already completed, you can test inline mode by:
1. Manually setting the file status to `"uploaded"` in the database, OR
2. Upload a new file and test before ingestion completes

### Test Command:

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is this document about?",
    "file_id": "YOUR-FILE-ID-WITH-UPLOADED-STATUS"
  }' | python3 -m json.tool
```

### Expected Response:

```json
{
  "conversation_id": "...",
  "response": "... (response from vision API)",
  "retrieval_mode": "inline",
  "retrieved_chunks": []
}
```

### What to Check:

✅ `retrieval_mode` should be `"inline"`  
✅ `retrieved_chunks` should be empty array  
✅ Response should reference content from the PDF images  
✅ Check server logs for: `"Using inline mode"` and `"Attached X PDF pages as images"`

## Test 3: Tool Calling Flow

Test that the LLM actually calls the `semantic_search` tool:

### Test with Explicit Query:

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Search for information about Python and FastAPI in the document",
    "file_id": "500107f2-4445-4be2-9a5e-aca7144780d2"
  }' | python3 -m json.tool
```

### Check Server Logs:

Look for these log messages:
- `"RAG mode enabled: X file(s) with completed ingestion"`
- `"LLM called 1 tool(s)"`
- `"Executing semantic_search: query='...', top_k=5"`
- `"Retrieved X chunks from vector database"`

## Test 4: Conversation History with Mode Switching

Test that the same conversation can handle multiple messages:

### Step 1: First Message (RAG Mode)

```bash
CONV_ID=$(curl -s -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What technologies are mentioned?",
    "file_id": "500107f2-4445-4be2-9a5e-aca7144780d2"
  }' | python3 -c "import sys, json; print(json.load(sys.stdin)['conversation_id'])")

echo "Conversation ID: $CONV_ID"
```

### Step 2: Follow-up Message (Same Conversation)

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": \"Tell me more about the first technology you mentioned\",
    \"conversation_id\": \"$CONV_ID\"
  }" | python3 -m json.tool
```

### What to Check:

✅ Both messages should use RAG mode (if file is completed)  
✅ Conversation history should be maintained  
✅ Second message should reference the first message's context

## Test 5: Direct Retrieval Endpoint

Test the `/retrieve` endpoint independently:

```bash
curl -X POST "http://localhost:8000/retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What technologies are mentioned?",
    "file_ids": ["500107f2-4445-4be2-9a5e-aca7144780d2"],
    "top_k": 5
  }' | python3 -m json.tool
```

### Expected Response:

```json
{
  "results": [
    {
      "chunk_id": "...",
      "file_id": "500107f2-4445-4be2-9a5e-aca7144780d2",
      "chunk_text": "...",
      "similarity_score": 0.85
    }
  ]
}
```

## Test 6: View Conversation History

Check that messages are stored with correct retrieval mode:

```bash
# Get conversation ID from previous test
CONV_ID="YOUR-CONVERSATION-ID"

curl -X GET "http://localhost:8000/chats/$CONV_ID" | python3 -m json.tool
```

### Expected Response:

```json
{
  "conversation_id": "...",
  "created_at": "...",
  "messages": [
    {
      "role": "user",
      "content": "...",
      "file_id": "500107f2-4445-4be2-9a5e-aca7144780d2",
      "created_at": "..."
    },
    {
      "role": "assistant",
      "content": "...",
      "retrieval_mode": "rag",
      "retrieved_chunks": [
        {
          "chunk_text": "...",
          "similarity_score": 0.85
        }
      ],
      "created_at": "..."
    }
  ]
}
```

## Troubleshooting

### Issue: RAG Mode Not Triggering

**Symptoms**: `retrieval_mode` is always `"inline"` even when file is completed

**Check**:
1. Verify file status: `curl -X GET "http://localhost:8000/files/YOUR-FILE-ID"`
2. Check server logs for: `"Collected X file_id(s), has_completed=True"`
3. Ensure file ingestion completed successfully

### Issue: Tool Not Being Called

**Symptoms**: RAG mode enabled but no tool calls in logs

**Check**:
1. Verify tool is enabled: Look for `"RAG mode enabled"` in logs
2. Check if LLM is calling the tool: Look for `"LLM called X tool(s)"`
3. Try a more explicit query that requires search

### Issue: No Retrieved Chunks

**Symptoms**: `retrieved_chunks` is empty array

**Check**:
1. Verify vectors are in Upstash: Test `/retrieve` endpoint directly
2. Check file_ids match: Ensure the file_id in conversation matches the file_id in vector metadata
3. Check Upstash namespace configuration

## Quick Test Script

Save this as `test_milestone4.sh`:

```bash
#!/bin/bash

FILE_ID="500107f2-4445-4be2-9a5e-aca7144780d2"
BASE_URL="http://localhost:8000"

echo "=== Milestone 4 Testing ==="
echo ""

echo "1. Checking file status..."
curl -s -X GET "$BASE_URL/files/$FILE_ID" | python3 -m json.tool | grep -E "(file_id|ingestion_status)"
echo ""

echo "2. Testing RAG mode (if file is completed)..."
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What technologies are mentioned?\", \"file_id\": \"$FILE_ID\"}" \
  | python3 -m json.tool | head -20
echo ""

echo "3. Testing /retrieve endpoint..."
curl -s -X POST "$BASE_URL/retrieve" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"technologies\", \"file_ids\": [\"$FILE_ID\"], \"top_k\": 3}" \
  | python3 -m json.tool | head -15
echo ""

echo "=== Testing Complete ==="
```

Make it executable and run:

```bash
chmod +x test_milestone4.sh
./test_milestone4.sh
```

## Expected Behavior Summary

| File Status | Mode | Tool Calling | Retrieved Chunks |
|------------|------|-------------|------------------|
| `completed` | RAG | ✅ Yes | ✅ Yes |
| `uploaded` | Inline | ❌ No | ❌ No |
| No file | Text | ❌ No | ❌ No |

## Next Steps

1. Test with different queries to see tool calling in action
2. Test with multiple files in the same conversation
3. Test mode switching within a conversation (upload file → chat → ingest → chat again)
4. Monitor server logs to see the full flow

