# Comprehensive Testing Guide
## Based on Assignment Requirements

This guide covers all testing scenarios required by the assignment, including multi-file RAG, mode switching, and edge cases.

## Prerequisites

- Server running on `http://localhost:8000`
- Two PDF files uploaded and ingested:
  - `minecraft.pdf` (file_id: `9f2d89bf-18b4-4bf4-a55c-3475db992210`)
  - `SamplePDF.pdf` (file_id: `fc952142-4b8a-401f-80f1-ddf5c11e90af`)

## Test Scenarios

### 1. Single File RAG Mode ✅

**Requirement**: When file has `ingestion_status="completed"`, use RAG mode with tool calling.

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the main theme?",
    "file_id": "9f2d89bf-18b4-4bf4-a55c-3475db992210"
  }' | python3 -m json.tool
```

**Expected**:
- `retrieval_mode: "rag"`
- `retrieved_chunks` with similarity scores
- Response references document content

### 2. Multi-File RAG Mode ✅

**Requirement**: Collect all `file_ids` from conversation history and search across all completed files.

**Test Flow**:
1. Start conversation with `minecraft.pdf`
2. Add message with `SamplePDF.pdf` in same conversation
3. Ask question that requires both files

```bash
# Step 1: Start with minecraft.pdf
CONV_ID=$(curl -s -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What does this document say about Minecraft?",
    "file_id": "9f2d89bf-18b4-4bf4-a55c-3475db992210"
  }' | python3 -c "import sys, json; print(json.load(sys.stdin)['conversation_id'])")

# Step 2: Add SamplePDF.pdf to same conversation
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": \"Compare the information about Minecraft in both documents\",
    \"conversation_id\": \"$CONV_ID\",
    \"file_id\": \"fc952142-4b8a-401f-80f1-ddf5c11e90af\"
  }" | python3 -m json.tool
```

**Expected**:
- `retrieval_mode: "rag"`
- `retrieved_chunks` from BOTH files
- Response synthesizes information from both documents

### 3. Direct Multi-File Retrieval ✅

**Requirement**: `/retrieve` endpoint supports multiple `file_ids` with metadata filtering.

```bash
curl -X POST "http://localhost:8000/retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Minecraft?",
    "file_ids": [
      "9f2d89bf-18b4-4bf4-a55c-3475db992210",
      "fc952142-4b8a-401f-80f1-ddf5c11e90af"
    ],
    "top_k": 5
  }' | python3 -m json.tool
```

**Expected**:
- Results from both files
- Each result shows which `file_id` it came from
- Results sorted by similarity score

### 4. Mode Switching (Uploaded → Completed) ✅

**Requirement**: System should switch from inline to RAG when file ingestion completes.

**Test Flow**:
1. Upload new file (status: `uploaded`)
2. Chat with file (should use inline mode)
3. Trigger ingestion (status: `completed`)
4. Chat again (should use RAG mode)

```bash
# Step 1: Upload and chat (inline mode)
# ... upload file ...
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is this about?",
    "file_id": "NEW-FILE-ID"
  }' | python3 -m json.tool
# Expected: retrieval_mode: "inline"

# Step 2: After ingestion completes
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is this about?",
    "file_id": "NEW-FILE-ID"
  }' | python3 -m json.tool
# Expected: retrieval_mode: "rag"
```

### 5. Tool Calling Verification ✅

**Requirement**: LLM should call `semantic_search` tool when RAG mode is enabled.

**Check Server Logs For**:
- `"RAG mode enabled: X file(s) with completed ingestion"`
- `"LLM called 1 tool(s)"`
- `"Executing semantic_search: query='...', top_k=5"`
- `"Retrieved X chunks from vector database"`

### 6. Metadata Filtering ✅

**Requirement**: Only retrieve chunks from `file_ids` in conversation history.

**Test**: 
- Start conversation with `file_id_1`
- Add message with `file_id_2`
- Ask question
- Verify retrieved chunks only come from these two files

### 7. Conversation History Persistence ✅

**Requirement**: Messages stored with correct `retrieval_mode` and `retrieved_chunks`.

```bash
CONV_ID="YOUR-CONVERSATION-ID"
curl -X GET "http://localhost:8000/chats/$CONV_ID" | python3 -m json.tool
```

**Expected**:
- All messages stored correctly
- Assistant messages have `retrieval_mode: "rag"` or `"inline"`
- `retrieved_chunks` stored for RAG mode messages

### 8. Edge Cases

#### 8.1 No File in Message
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how are you?",
    "conversation_id": "EXISTING-CONV-ID"
  }' | python3 -m json.tool
```
**Expected**: Normal chat without file context

#### 8.2 File Not Found
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Test",
    "file_id": "00000000-0000-0000-0000-000000000000"
  }' | python3 -m json.tool
```
**Expected**: 400 error with "File not found"

#### 8.3 File Ingestion Failed
```bash
# Check file with status="failed"
curl -X GET "http://localhost:8000/files/FAILED-FILE-ID" | python3 -m json.tool
```
**Expected**: File status shows `"failed"`, system should handle gracefully

## Requirements Checklist

### From `.cursorrules`:
- ✅ NO High-Level AI Frameworks (LangChain, LlamaIndex, etc.)
- ✅ Naming Convention: `swe-test-godwin-j` prefix
- ✅ Tech Stack: FastAPI, Pydantic, SQLAlchemy (Async), OpenAI SDK, Upstash Vector, AWS S3
- ✅ Hybrid System: Inline + RAG modes
- ✅ State Management: Track ingestion status
- ✅ Separation of Concerns: routers → services → dao
- ✅ Type Safety: Pydantic models

### From `assignment_requirements.md`:
- ✅ Milestone 1: File Upload & CRUD APIs
- ✅ Milestone 2: Inline Chat with Base64 PDF
- ✅ Milestone 3: RAG Pipeline & Retrieval
- ✅ Milestone 4: Dynamic Mode Switching with Tool Calling
  - ✅ Tool definition without `file_ids` parameter
  - ✅ Collect `file_ids` from conversation history
  - ✅ Metadata filtering in vector search
  - ✅ Manual tool calling loop
  - ✅ Store `retrieval_mode` and `retrieved_chunks`

### From `technical-setup.md`:
- ✅ Upstash Vector namespace: `swe-test-godwin-j`
- ✅ AWS S3 bucket: `swe-test-godwin-j-uploads`
- ✅ OpenAI models: `gpt-4.1-mini` or `gpt-4o-mini`, `text-embedding-3-small`
- ✅ Manual chunking (no frameworks)
- ✅ Manual tool calling (no frameworks)

## Quick Test Script

```bash
#!/bin/bash

MINECRAFT_FILE="9f2d89bf-18b4-4bf4-a55c-3475db992210"
SAMPLE_FILE="fc952142-4b8a-401f-80f1-ddf5c11e90af"
BASE_URL="http://localhost:8000"

echo "=== Comprehensive Testing ==="
echo ""

echo "1. Single File RAG (minecraft.pdf)"
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What is the main theme?\", \"file_id\": \"$MINECRAFT_FILE\"}" \
  | python3 -m json.tool | grep -E "(retrieval_mode|retrieved_chunks)" | head -5
echo ""

echo "2. Multi-File RAG"
CONV_ID=$(curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What is Minecraft?\", \"file_id\": \"$MINECRAFT_FILE\"}" \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['conversation_id'])")

curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Compare both documents\", \"conversation_id\": \"$CONV_ID\", \"file_id\": \"$SAMPLE_FILE\"}" \
  | python3 -m json.tool | grep -E "(retrieval_mode|retrieved_chunks)" | head -5
echo ""

echo "3. Direct Multi-File Retrieval"
curl -s -X POST "$BASE_URL/retrieve" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"Minecraft\", \"file_ids\": [\"$MINECRAFT_FILE\", \"$SAMPLE_FILE\"], \"top_k\": 3}" \
  | python3 -m json.tool | head -20
echo ""

echo "=== Testing Complete ==="
```

